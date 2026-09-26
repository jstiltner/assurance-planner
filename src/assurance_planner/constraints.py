"""Admissibility.

All domain content lives here.  Ranking (ranking.py) is pure least-cost, so anything
that makes one plan *better* rather than merely *cheaper* has to be expressed as a
constraint.  That is deliberate: it keeps "least-cost admissible" literally true and
stops intent from degenerating into hand-tuned scoring weights.

Two families of constraint:

* **goal** constraints, derived from ``DevelopmentContext.intent`` -- what claim must
  this plan be able to support?
* **policy** constraints, supplied externally in ``AssuranceProfile`` -- what is the
  organisation willing to accept?

Nothing here inspects a failure mode's description, a scenario name, or a source id.
"""

from __future__ import annotations

from dataclasses import dataclass

from .domain import (
    AssuranceProfile,
    Cadence,
    DevelopmentContext,
    EvaluationPopulation,
    EvidenceSourceVersion,
    ExecutionMode,
    ExecutionProfile,
    FailureMode,
    Intent,
    PopulationKind,
    QualificationEvidence,
    SourceKind,
    StepRole,
    UncertaintyDisposition,
)
from .registry import World
from .statistics import DecisionProcedure


@dataclass(frozen=True, slots=True)
class EvidenceGoal:
    """What ``intent`` requires of a plan, independent of cost."""

    #: The population must contain the failure mode's own case.
    requires_target_case: bool
    #: Every currently known regression case must actually be executed.
    requires_regression_coverage: bool
    #: Only a mechanism that can surface an unanticipated failure will do.
    requires_open_ended_source: bool
    #: The verification claim needs prior RED observations under this same source.
    requires_prove_red: bool
    #: The result must gate the change, so it must block and run on the change.
    must_gate_change: bool
    allowed_cadences: frozenset[Cadence]


#: The whole intent model.  Five booleans and a cadence set per intent; if this table
#: ever needs a sixth column to make a scenario come out right, that is evidence the
#: abstraction is failing and should be reported rather than accommodated.
GOALS: dict[Intent, EvidenceGoal] = {
    Intent.VERIFY_FIX: EvidenceGoal(
        requires_target_case=True,
        requires_regression_coverage=False,
        requires_open_ended_source=False,
        requires_prove_red=True,
        must_gate_change=True,
        allowed_cadences=frozenset({Cadence.PER_CHANGE}),
    ),
    Intent.ASSESS_BLAST_RADIUS: EvidenceGoal(
        requires_target_case=False,
        requires_regression_coverage=True,
        requires_open_ended_source=False,
        requires_prove_red=False,
        must_gate_change=True,
        allowed_cadences=frozenset({Cadence.PER_CHANGE, Cadence.PER_CHECKPOINT}),
    ),
    Intent.RELEASE: EvidenceGoal(
        requires_target_case=False,
        requires_regression_coverage=True,
        requires_open_ended_source=False,
        requires_prove_red=False,
        must_gate_change=False,
        allowed_cadences=frozenset(
            {Cadence.PER_CHECKPOINT, Cadence.NIGHTLY, Cadence.CONTINUOUS}
        ),
    ),
    Intent.DISCOVER: EvidenceGoal(
        requires_target_case=False,
        #: Discovery searches for failures that are not yet characterised.  The set of
        #: behaviours you can observe is exactly the set you run, so searching a
        #: subset while claiming to have looked for unknown regressions is unsound.
        #: Without this, the ranker minimises discovery coverage to a single case --
        #: v0 has no model of the value of finding a defect to push back with.
        requires_regression_coverage=True,
        #: A fixed assertion cannot find a failure nobody has specified.  This is the
        #: rule that stops the planner being a deterministic-oracle maximalist, and
        #: the reason an expensive judge can be the *only* admissible mechanism.
        requires_open_ended_source=True,
        requires_prove_red=False,
        must_gate_change=False,
        allowed_cadences=frozenset(
            {Cadence.PER_CHECKPOINT, Cadence.NIGHTLY, Cadence.CONTINUOUS}
        ),
    ),
}


@dataclass(frozen=True, slots=True)
class Violation:
    constraint: str
    reason: str
    #: Lower runs first in rationale: the earliest stage a candidate family fails at
    #: is the most informative thing to tell a human.
    stage: int


# --------------------------------------------------------------------------------
# Stage 1-3: can this source speak to this failure mode on this population at all?
# --------------------------------------------------------------------------------


def check_source_usable(
    source: EvidenceSourceVersion,
    failure_mode: FailureMode,
    population: EvaluationPopulation,
    profile: AssuranceProfile,
    world: World,
) -> tuple[QualificationEvidence | None, ExecutionProfile | None, Violation | None]:
    economics = world.economics_for(source)
    if economics is None:
        return (
            None,
            None,
            Violation(
                "execution_profile_known",
                f"no execution profile registered for {source}",
                1,
            ),
        )
    if not economics.available:
        return (
            None,
            economics,
            Violation("source_available", f"{source} is currently unavailable", 1),
        )

    evidence = world.qualification_for(source, failure_mode, population)
    if evidence is None:
        return (
            None,
            economics,
            Violation(
                "qualification_exists",
                f"no qualification evidence for {source} x {failure_mode.ref} "
                f"x population '{population.population_id}'",
                2,
            ),
        )
    if evidence.observation_count < profile.minimum_observation_count:
        return (
            evidence,
            economics,
            Violation(
                "qualification_sufficient",
                f"qualification study for {source} has "
                f"{evidence.observation_count} observations, policy "
                f"'{profile.profile_ref}' requires "
                f"{profile.minimum_observation_count}",
                3,
            ),
        )
    return evidence, economics, None


# --------------------------------------------------------------------------------
# Stage 4: does the decision procedure meet the error bound?
# --------------------------------------------------------------------------------


def check_error_bound(
    source: EvidenceSourceVersion,
    procedure: DecisionProcedure | None,
    replications: int,
    profile: AssuranceProfile,
) -> Violation | None:
    if procedure is None:
        return Violation(
            "error_bound_met",
            f"{source} at {replications} replication(s) cannot bound both miss and "
            f"false-alarm probability at {profile.maximum_error_requirement:g}",
            4,
        )
    return None


# --------------------------------------------------------------------------------
# Stage 5-8: goal constraints
# --------------------------------------------------------------------------------


def check_goal(
    goal: EvidenceGoal,
    context: DevelopmentContext,
    source: EvidenceSourceVersion,
    population: EvaluationPopulation,
    sample_fraction: float,
    cadence: Cadence,
    execution_mode: ExecutionMode,
    failure_mode: FailureMode,
    evidence: QualificationEvidence,
    procedure: DecisionProcedure,
    world: World,
) -> Violation | None:
    if goal.requires_open_ended_source and not source.open_ended:
        return Violation(
            "goal_source_capability",
            f"intent '{context.intent}' needs a mechanism that can surface an "
            f"unanticipated failure; {source} checks a fixed criterion only",
            5,
        )

    if goal.requires_target_case and not population.contains_case(failure_mode.case_id):
        return Violation(
            "goal_population_coverage",
            f"intent '{context.intent}' targets case '{failure_mode.case_id}', "
            f"which population '{population.population_id}' does not contain",
            6,
        )

    if goal.requires_regression_coverage:
        if not world.population_covers_blast_radius(population):
            return Violation(
                "goal_population_coverage",
                f"intent '{context.intent}' requires every known regression case to "
                f"run; population '{population.population_id}' omits "
                f"{sorted(world.known_regression_cases - set(population.case_ids))}",
                6,
            )
        #: A finite corpus can be exhausted, so coverage means all of it.  A live
        #: stream cannot be exhausted at any rate, so a rate is the only available
        #: control and coverage is not a meaningful demand on it.
        if (
            population.kind is PopulationKind.ENUMERABLE_CORPUS
            and sample_fraction < 1.0
        ):
            return Violation(
                "goal_population_coverage",
                f"intent '{context.intent}' requires every known regression case to "
                f"run; {sample_fraction * 100:g}% of {population.denominator} does not",
                6,
            )

    if cadence not in goal.allowed_cadences:
        return Violation(
            "goal_cadence",
            f"intent '{context.intent}' does not admit '{cadence}' cadence",
            7,
        )

    if goal.must_gate_change and execution_mode is not ExecutionMode.SYNCHRONOUS:
        return Violation(
            "goal_execution_mode",
            f"intent '{context.intent}' must gate the change, so its result cannot "
            f"be asynchronous",
            7,
        )

    if goal.requires_prove_red:
        #: A single RED is adequate evidence only if a single run is an adequate
        #: decision.  For a noisy source the derived replication count is the number
        #: of REDs required, which is exactly why one judge observation is not proof.
        if evidence.prove_red_runs < procedure.replications:
            return Violation(
                "prove_red_sufficient",
                f"{source} needs {procedure.replications} RED observation(s) to "
                f"support a verification claim at this noise level; "
                f"{evidence.prove_red_runs} recorded",
                8,
            )
        if evidence.prove_green_runs < 1:
            return Violation(
                "prove_red_sufficient",
                f"{source} has no GREEN observation recorded against the fixed "
                f"implementation",
                8,
            )
    return None


# --------------------------------------------------------------------------------
# Stage 9-13: policy constraints
# --------------------------------------------------------------------------------


def check_policy(
    profile: AssuranceProfile,
    source: EvidenceSourceVersion,
    sample_fraction: float,
    execution_mode: ExecutionMode,
    has_human_confirmation: bool,
) -> Violation | None:
    if not profile.sampling_allowed and sample_fraction < 1.0:
        return Violation(
            "policy_sampling",
            f"policy '{profile.profile_ref}' forbids sampling; this plan covers "
            f"{sample_fraction * 100:g}%",
            9,
        )
    if profile.synchronous_requirement and execution_mode is not ExecutionMode.SYNCHRONOUS:
        return Violation(
            "policy_synchronous",
            f"policy '{profile.profile_ref}' requires synchronous evaluation",
            10,
        )
    if profile.authoritative_source_required and not source.consults_authoritative_source:
        return Violation(
            "policy_authoritative",
            f"policy '{profile.profile_ref}' requires reconciliation against a system "
            f"of record; {source} produces a judgement instead",
            11,
        )
    #: There is deliberately no `human_confirmation_required` branch here.  The
    #: planner attaches a qualified confirmer rather than discarding an otherwise good
    #: plan, and rejects only when no qualified human exists (planner._evaluate).
    #: Checking it again in this function would be unreachable code.
    assert has_human_confirmation or not profile.human_confirmation_required
    return None


def required_escalation(
    profile: AssuranceProfile, procedure: DecisionProcedure
) -> bool:
    """Escalation is derived, never enumerated.

    It is required exactly when the policy says unresolved uncertainty must be
    escalated *and* the decision procedure actually has an inconclusive band.  A
    single-run deterministic check has an empty band, so it never acquires an
    escalation hop -- that result is computed, not special-cased.
    """
    return (
        profile.uncertainty_disposition is UncertaintyDisposition.ESCALATE
        and procedure.escalation_band is not None
    )


def choose_escalation_target(
    primary: EvidenceSourceVersion,
    failure_mode: FailureMode,
    population: EvaluationPopulation,
    profile: AssuranceProfile,
    world: World,
) -> EvidenceSourceVersion | None:
    """Cheapest qualified source that adds *different* evidence than the primary.

    Different means open-ended or human: re-running the same fixed criterion resolves
    nothing about a case the criterion already found ambiguous.

    Policy applies to the whole decision path, not only to the primary.  Escalating an
    ambiguous high-consequence case to a mechanism that consults no system of record
    would route around the very constraint that picked the primary.
    """
    candidates = []
    for source in world.sources.values():
        if source.ref == primary.ref:
            continue
        if not (source.open_ended or source.kind is SourceKind.HUMAN):
            continue
        if (
            profile.authoritative_source_required
            and not source.consults_authoritative_source
        ):
            continue
        if world.qualification_for(source, failure_mode, population) is None:
            continue
        economics = world.economics_for(source)
        if economics is None or not economics.available:
            continue
        candidates.append((economics.cost_per_invocation_usd, str(source.ref), source))
    if not candidates:
        return None
    return min(candidates, key=lambda item: (item[0], item[1]))[2]


def choose_human_confirmer(
    failure_mode: FailureMode, population: EvaluationPopulation, world: World
) -> EvidenceSourceVersion | None:
    candidates = [
        (world.economics[s.ref].cost_per_invocation_usd, str(s.ref), s)
        for s in world.sources.values()
        if s.kind is SourceKind.HUMAN
        and world.qualification_for(s, failure_mode, population) is not None
        and world.economics_for(s) is not None
        and world.economics[s.ref].available
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda item: (item[0], item[1]))[2]


# --------------------------------------------------------------------------------
# Stage 14-16: budget, window and capacity
# --------------------------------------------------------------------------------


def check_budgets(
    context: DevelopmentContext,
    economics_summary: "PlanBudgetFacts",
) -> Violation | None:
    if economics_summary.blocking_feedback_seconds > context.feedback_budget_seconds:
        return Violation(
            "budget_feedback",
            f"blocking feedback {_hms(economics_summary.blocking_feedback_seconds)} "
            f"exceeds the {_hms(context.feedback_budget_seconds)} budget for intent "
            f"'{context.intent}'",
            14,
        )
    if (
        economics_summary.background_wall_clock_seconds
        > economics_summary.cadence_window_seconds
    ):
        return Violation(
            "cadence_window",
            f"background run {_hms(economics_summary.background_wall_clock_seconds)} "
            f"does not fit the {_hms(economics_summary.cadence_window_seconds)} "
            f"cadence window",
            15,
        )
    if economics_summary.human_capacity_exceeded:
        return Violation(
            "human_capacity",
            f"{economics_summary.human_units_per_window} human review(s) per window "
            f"exceeds capacity of {economics_summary.human_capacity_per_window}",
            16,
        )
    return None


@dataclass(frozen=True, slots=True)
class PlanBudgetFacts:
    blocking_feedback_seconds: float
    background_wall_clock_seconds: float
    cadence_window_seconds: float
    human_units_per_window: int
    human_capacity_per_window: int
    human_capacity_exceeded: bool


def _hms(seconds: float) -> str:
    if seconds == float("inf"):
        return "unbounded"
    if seconds < 90:
        return f"{seconds:.0f}s"
    if seconds < 5400:
        return f"{seconds / 60:.0f}m"
    return f"{seconds / 3600:.1f}h"


def structurally_coherent(
    population: EvaluationPopulation, cadence: Cadence, execution_mode: ExecutionMode
) -> bool:
    """Combinations that describe nothing physical.

    These are not preferences and are not policy; they are shapes that do not exist,
    so the enumerator does not emit them.  Keeping them out is what prevents the
    ranker from tie-breaking between a real plan and an incoherent one on plan id.
    """
    if cadence is Cadence.CONTINUOUS:
        #: A continuous cadence needs an arrival process to be continuous with.
        return population.kind is PopulationKind.LIVE_STREAM
    if population.kind is PopulationKind.LIVE_STREAM:
        if execution_mode is ExecutionMode.SYNCHRONOUS:
            #: An inline guard runs when the interaction happens.  "Synchronous, but
            #: nightly" does not describe anything.
            return False
        #: Offline evaluation of a captured window of traffic is legitimate; blocking
        #: a developer on a day of production traffic is not.
        return cadence is Cadence.NIGHTLY
    return True


__all__ = [
    "EvidenceGoal",
    "GOALS",
    "PlanBudgetFacts",
    "StepRole",
    "Violation",
    "check_budgets",
    "check_error_bound",
    "check_goal",
    "check_policy",
    "check_source_usable",
    "choose_escalation_target",
    "choose_human_confirmer",
    "required_escalation",
    "structurally_coherent",
]
