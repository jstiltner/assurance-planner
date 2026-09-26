"""Human-readable rationale.

Rejections are grouped: thousands of candidates differing only in replication count
are not thousands of insights.  One line per (source, population, constraint), ordered
by how far the family got before failing, because the family that failed latest is the
one a human was most likely to have expected to win.
"""

from __future__ import annotations

from .constraints import _hms
from .domain import (
    AssuranceProfile,
    DevelopmentContext,
    EvidencePlan,
    FailureMode,
    PlanningResult,
    PlanStep,
    PopulationKind,
    StepRole,
)
from .ranking import RANK_KEY_DESCRIPTION, explain_loss
from .registry import World

_CONSTRAINT_STAGE = {
    "execution_profile_known": 1,
    "source_available": 1,
    "qualification_exists": 2,
    "qualification_sufficient": 3,
    "error_bound_met": 4,
    "goal_source_capability": 5,
    "goal_population_coverage": 6,
    "goal_cadence": 7,
    "goal_execution_mode": 7,
    "prove_red_sufficient": 8,
    "policy_sampling": 9,
    "policy_synchronous": 10,
    "policy_authoritative": 11,
    "policy_human_confirmation": 12,
    "policy_escalation_target": 13,
    "budget_feedback": 14,
    "cadence_window": 15,
    "human_capacity": 16,
}


def render(
    result: PlanningResult,
    context: DevelopmentContext,
    failure_mode: FailureMode,
    profile: AssuranceProfile,
    world: World,
    max_rejections: int = 6,
    max_runners_up: int = 3,
) -> str:
    lines: list[str] = []
    lines.append(f"Failure mode   {failure_mode.ref}  ({failure_mode.description})")
    lines.append(
        f"Intent         {context.intent}   "
        f"feedback budget {_hms(context.feedback_budget_seconds)}"
    )
    lines.append(
        f"Assurance      {profile.profile_ref}   "
        f"max error {profile.maximum_error_requirement:g}   "
        f"sampling={'yes' if profile.sampling_allowed else 'no'}   "
        f"human_confirmation={'yes' if profile.human_confirmation_required else 'no'}   "
        f"authoritative={'yes' if profile.authoritative_source_required else 'no'}   "
        f"sync={'yes' if profile.synchronous_requirement else 'no'}"
    )
    lines.append("")

    if result.selected is None:
        lines.append("No admissible plan")
        lines.append("")
        lines.append(f"  {result.no_plan_reason}")
        lines.append("")
        lines.extend(_render_rejections(result, max_rejections))
        return "\n".join(lines)

    lines.append("Selected plan")
    lines.append("")
    lines.extend(_render_plan(result.selected, failure_mode, world))
    lines.append("")
    lines.extend(_render_runners_up(result, max_runners_up))
    lines.extend(_render_rejections(result, max_rejections))
    return "\n".join(lines)


def _render_plan(
    plan: EvidencePlan, failure_mode: FailureMode, world: World
) -> list[str]:
    lines: list[str] = []
    for step in plan.steps:
        lines.extend(_render_step(step, failure_mode, world))
        lines.append("")
    e = plan.economics
    lines.append("  Whole plan")
    lines.append(
        f"    direct cost:        ${e.monetary_cost_usd:.4f} per run  "
        f"x {e.runs_per_window} run(s)/day = "
        f"${e.monetary_cost_per_window_usd:.4f}/day"
    )
    lines.append(f"    invocations:        {e.total_invocations} per run")
    if e.blocking_feedback_seconds > 0:
        lines.append(
            f"    blocking feedback:  {_hms(e.blocking_feedback_seconds)}"
        )
    if e.background_wall_clock_seconds > 0:
        lines.append(
            f"    background runtime: {_hms(e.background_wall_clock_seconds)} "
            f"(does not block the developer)"
        )
    if e.conditional_interaction_latency_seconds > 0:
        #: Reported as a pair.  Never collapsed into an amortised average.
        lines.append(
            f"    added latency:      "
            f"{e.conditional_interaction_latency_seconds * 1000:.0f}ms on "
            f"{e.conditional_interaction_fraction * 100:g}% of interactions "
            f"(not amortised)"
        )
    if e.human_minutes > 0:
        lines.append(
            f"    human burden:       {e.human_minutes:.0f} min per run, "
            f"{e.human_minutes_per_window:.0f} min/day"
        )
    lines.append("    assurance:          all constraints satisfied")
    return lines


def _render_step(step: PlanStep, failure_mode: FailureMode, world: World) -> list[str]:
    label = {
        StepRole.PRIMARY: "Primary evidence",
        StepRole.ESCALATION: "Escalation",
        StepRole.HUMAN_CONFIRMATION: "Human confirmation",
    }[step.role]
    lines = [f"  {label}"]
    lines.append(f"    source:       {step.source} ({step.source.kind})")
    lines.append(f"    scope:        {step.scope_phrase()}")
    lines.append(f"    denominator:  {step.denominator}")
    if not step.is_conditional:
        lines.append(f"    replications: {step.replications}")
        lines.append(
            f"    decision:     fail at >={step.threshold_k} of "
            f"{step.replications} flags"
        )
        if step.escalation_band is not None:
            lo, hi = step.escalation_band
            lines.append(
                f"    escalate:     {lo}-{hi} flags -> "
                f"{step.escalation_target or 'unresolved'}"
            )
        else:
            lines.append("    escalate:     n/a (no inconclusive band at this n)")
        lines.append(
            f"    error bound:  P(miss)={step.miss_probability:.2e}  "
            f"P(false alarm)={step.false_alarm_probability:.2e}"
        )
    lines.append(f"    cadence:      {step.cadence} / {step.execution_mode}")
    kind = (
        "corpus"
        if step.population.kind is PopulationKind.ENUMERABLE_CORPUS
        else "live stream"
    )
    lines.append(f"    population:   {step.population.population_id} ({kind})")
    #: Provenance of the measurement the decision procedure above was derived from.
    #: A reader who cannot see how old the evidence is, or what its authors said it
    #: does not cover, cannot audit the plan.
    evidence = world.qualification_for(step.source, failure_mode, step.population)
    if evidence is not None:
        lines.append(
            f"    evidence:     sensitivity {evidence.sensitivity:g} / "
            f"FPR {evidence.false_positive_rate:g} from "
            f"{evidence.observation_count} observation(s), measured "
            f"{evidence.evidence_date.isoformat()}"
        )
        for limitation in evidence.known_limitations:
            lines.append(f"    caveat:       {limitation}")
    return lines


def _render_runners_up(result: PlanningResult, limit: int) -> list[str]:
    if not result.runners_up or result.selected is None:
        return []
    lines = [f"Admissible but not selected (ranked by {RANK_KEY_DESCRIPTION})", ""]
    seen: set[tuple[str, str]] = set()
    shown = 0
    for candidate in result.runners_up:
        key = (
            str(candidate.primary.source.ref),
            candidate.primary.population.population_id,
        )
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"  Rejected: {candidate.plan_id}")
        lines.append(f"    reason: {explain_loss(result.selected, candidate)}")
        shown += 1
        if shown >= limit:
            break
    lines.append("")
    return lines


def _render_rejections(result: PlanningResult, limit: int) -> list[str]:
    if not result.rejections:
        return []
    #: Variants of the family that won are not insights -- a more-replicated version
    #: of the selected source failing its own prove-red bar tells a reader nothing.
    won = (
        (
            str(result.selected.primary.source.ref),
            result.selected.primary.population.population_id,
        )
        if result.selected is not None
        else None
    )
    #: One representative per (source, population, constraint).
    grouped: dict[tuple[str, str, str], tuple[int, str, str]] = {}
    suppressed = 0
    for rejection in result.rejections:
        source, population = rejection.plan_id.split("|")[:2]
        if won is not None and (source, population) == won:
            suppressed += 1
            continue
        key = (source, population, rejection.constraint)
        stage = _CONSTRAINT_STAGE.get(rejection.constraint, 99)
        if key not in grouped:
            grouped[key] = (stage, rejection.plan_id, rejection.reason)
    #: Latest-failing families first: those are the near misses.
    ordered = sorted(grouped.items(), key=lambda kv: (-kv[1][0], kv[0]))
    if not ordered:
        return []

    lines = ["Inadmissible", ""]
    for (source, population, constraint), (_, _, reason) in ordered[:limit]:
        lines.append(f"  Rejected: {source} on {population}")
        lines.append(f"    constraint: {constraint}")
        lines.append(f"    reason: {_truncate(reason)}")
    remaining = len(ordered) - limit
    if remaining > 0:
        lines.append(f"  ... and {remaining} further rejected families")
    if suppressed:
        lines.append(
            f"  ({suppressed} further rejections were other configurations of the "
            f"selected source and population)"
        )
    lines.append("")
    return lines


def _truncate(text: str, limit: int = 300) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."
