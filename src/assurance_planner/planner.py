"""The planner.

    enumerate -> reject inadmissible -> rank admissible -> explain

Deterministic and total: same inputs give byte-identical output, and an input with no
admissible plan yields an explanation rather than a degraded plan.
"""

from __future__ import annotations

from . import economics as econ
from .candidates import Candidate, enumerate_candidates
from .constraints import (
    GOALS,
    Violation,
    check_budgets,
    check_error_bound,
    check_goal,
    check_policy,
    check_source_usable,
    choose_escalation_target,
    choose_human_confirmer,
    required_escalation,
)
from .domain import (
    AssuranceProfile,
    DevelopmentContext,
    EvidencePlan,
    FailureMode,
    PlanStep,
    PlanningResult,
    Rejection,
    StepRole,
)
from .registry import World
from .ranking import rank
from .statistics import procedure_for


def plan(
    context: DevelopmentContext,
    failure_mode: FailureMode,
    profile: AssuranceProfile,
    world: World,
) -> PlanningResult:
    goal = GOALS[context.intent]
    admissible: list[EvidencePlan] = []
    rejections: list[Rejection] = []

    for candidate in enumerate_candidates(failure_mode, profile, world):
        outcome = _evaluate(candidate, context, failure_mode, profile, world, goal)
        if isinstance(outcome, Violation):
            rejections.append(
                Rejection(candidate.candidate_id, outcome.constraint, outcome.reason)
            )
        else:
            admissible.append(outcome)

    ordered = rank(admissible)
    if not ordered:
        return PlanningResult(
            selected=None,
            rejections=rejections,
            no_plan_reason=_no_plan_reason(context, failure_mode, rejections),
        )
    return PlanningResult(
        selected=ordered[0], runners_up=ordered[1:], rejections=rejections
    )


def _evaluate(
    candidate: Candidate,
    context: DevelopmentContext,
    failure_mode: FailureMode,
    profile: AssuranceProfile,
    world: World,
    goal,
) -> EvidencePlan | Violation:
    evidence, execution, violation = check_source_usable(
        candidate.source, failure_mode, candidate.population, profile, world
    )
    if violation is not None:
        return violation
    assert evidence is not None and execution is not None

    procedure = procedure_for(
        candidate.replications,
        evidence.sensitivity,
        evidence.false_positive_rate,
        profile.maximum_error_requirement,
    )
    violation = check_error_bound(
        candidate.source, procedure, candidate.replications, profile
    )
    if violation is not None:
        return violation
    assert procedure is not None

    violation = check_goal(
        goal,
        context,
        candidate.source,
        candidate.population,
        candidate.sample_fraction,
        candidate.cadence,
        candidate.execution_mode,
        failure_mode,
        evidence,
        procedure,
        world,
    )
    if violation is not None:
        return violation

    # --- derived steps -----------------------------------------------------------
    escalation_target = None
    if required_escalation(profile, procedure):
        escalation_target = choose_escalation_target(
            candidate.source, failure_mode, candidate.population, profile, world
        )
        if escalation_target is None:
            return Violation(
                "policy_escalation_target",
                f"policy '{profile.profile_ref}' escalates unresolved uncertainty, "
                f"but no qualified source offers evidence different from "
                f"{candidate.source}",
                13,
            )

    steps: list[PlanStep] = [
        PlanStep(
            role=StepRole.PRIMARY,
            source=candidate.source,
            population=candidate.population,
            sample_fraction=candidate.sample_fraction,
            replications=procedure.replications,
            threshold_k=procedure.threshold_k,
            escalation_band=procedure.escalation_band,
            escalation_target=(
                escalation_target.ref if escalation_target is not None else None
            ),
            cadence=candidate.cadence,
            execution_mode=candidate.execution_mode,
            miss_probability=procedure.miss_probability,
            false_alarm_probability=procedure.false_alarm_probability,
        )
    ]

    if escalation_target is not None:
        steps.append(
            PlanStep(
                role=StepRole.ESCALATION,
                source=escalation_target,
                population=candidate.population,
                sample_fraction=0.0,
                replications=1,
                threshold_k=1,
                escalation_band=None,
                escalation_target=None,
                cadence=candidate.cadence,
                execution_mode=candidate.execution_mode,
                miss_probability=0.0,
                false_alarm_probability=0.0,
            )
        )

    if profile.human_confirmation_required and not econ.has_human_confirmation(
        tuple(steps)
    ):
        confirmer = choose_human_confirmer(failure_mode, candidate.population, world)
        if confirmer is None:
            return Violation(
                "policy_human_confirmation",
                f"policy '{profile.profile_ref}' requires human confirmation, but no "
                f"human source is qualified for {failure_mode.ref} on population "
                f"'{candidate.population.population_id}'",
                12,
            )
        else:
            steps.append(
                PlanStep(
                    role=StepRole.HUMAN_CONFIRMATION,
                    source=confirmer,
                    population=candidate.population,
                    sample_fraction=candidate.sample_fraction,
                    replications=1,
                    threshold_k=1,
                    escalation_band=None,
                    escalation_target=None,
                    cadence=candidate.cadence,
                    execution_mode=candidate.execution_mode,
                    miss_probability=0.0,
                    false_alarm_probability=0.0,
                )
            )

    #: An escalation hop to a reviewer who already sees every case resolves nothing
    #: that is not already resolved.  Derived from the steps, not special-cased.
    confirmers = {
        s.source.ref
        for s in steps
        if s.role is StepRole.HUMAN_CONFIRMATION
        and s.sample_fraction >= candidate.sample_fraction
    }
    steps = [
        s
        for s in steps
        if not (s.role is StepRole.ESCALATION and s.source.ref in confirmers)
    ]

    violation = check_policy(
        profile,
        candidate.source,
        candidate.sample_fraction,
        candidate.execution_mode,
        has_human_confirmation=econ.has_human_confirmation(tuple(steps)),
    )
    if violation is not None:
        return violation

    plan_economics, facts = econ.compute(tuple(steps), context, world)
    violation = check_budgets(context, facts)
    if violation is not None:
        return violation

    return EvidencePlan(
        plan_id=candidate.candidate_id,
        steps=tuple(steps),
        economics=plan_economics,
    )


def _no_plan_reason(
    context: DevelopmentContext,
    failure_mode: FailureMode,
    rejections: list[Rejection],
) -> str:
    """Report the constraint that killed the most candidates, plus the runner-up.

    Deliberately not a suggestion engine: the planner says what blocked it and stops.
    """
    if not rejections:
        return "no candidate plans were generated; the world has no sources or populations"
    counts: dict[str, int] = {}
    for rejection in rejections:
        counts[rejection.constraint] = counts.get(rejection.constraint, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    top = ", ".join(f"{name} ({count})" for name, count in ordered[:3])
    return (
        f"no admissible plan for intent '{context.intent}' on {failure_mode.ref}: "
        f"all {len(rejections)} candidates rejected. Dominant constraints: {top}"
    )
