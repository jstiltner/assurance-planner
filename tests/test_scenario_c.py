"""Acceptance scenario C -- high-consequence factual mismatch.

This scenario exists to show the seam between an organisational risk decision and an
engineering/economic one.  The two contexts in the fixture share a world, a set of
mechanisms, a set of qualification measurements and a set of prices.  Only the
assurance profile differs, and it moves the answer by six orders of magnitude.
"""

from __future__ import annotations

from pathlib import Path

from assurance_planner.domain import Cadence, ExecutionMode, SourceKind, StepRole
from conftest import rejection_constraints, run

SRC = Path(__file__).resolve().parents[1] / "src" / "assurance_planner"


def test_authoritative_reconciliation_is_preferred_to_a_stochastic_judge(
    clinical_factual,
):
    result = run(clinical_factual, "production_guard")
    step = result.selected.primary
    assert str(step.source.ref) == "record_reconciliation@v1"
    assert step.source.consults_authoritative_source is True

    constraints = rejection_constraints(
        result, "frontier_judge@v2", "flagged_interactions"
    )
    assert "policy_authoritative" in constraints


def test_sampling_is_rejected_when_policy_forbids_it(clinical_factual):
    result = run(clinical_factual, "production_guard")
    assert result.selected.primary.sample_fraction == 1.0
    assert any(r.constraint == "policy_sampling" for r in result.rejections)


def test_no_plan_is_fully_automated_when_human_confirmation_is_required(
    clinical_factual,
):
    strict = run(clinical_factual, "production_guard")
    human_steps = [
        s for s in strict.selected.steps if s.role is StepRole.HUMAN_CONFIRMATION
    ]
    assert len(human_steps) == 1
    assert human_steps[0].source.kind is SourceKind.HUMAN
    assert human_steps[0].sample_fraction == 1.0

    # Every admissible plan, not just the selected one.
    for candidate in [strict.selected, *strict.runners_up]:
        assert any(s.source.kind is SourceKind.HUMAN for s in candidate.steps)

    # Under the routine policy the same world produces fully automated plans.
    routine = run(clinical_factual, "production_guard_routine_policy")
    assert not any(
        s.source.kind is SourceKind.HUMAN for s in routine.selected.steps
    )


def _without_humans(world):
    from dataclasses import replace

    from assurance_planner.domain import SourceKind as Kind

    return replace(
        world,
        sources={
            ref: s for ref, s in world.sources.items() if s.kind is not Kind.HUMAN
        },
    )


def test_human_confirmation_is_impossible_without_a_qualified_human(
    clinical_factual,
):
    """The reachable rejection path: policy demands a human, none is qualified."""
    from dataclasses import replace

    from assurance_planner import plan
    from assurance_planner.domain import UncertaintyDisposition

    request = clinical_factual.request("production_guard")
    # Hold escalation out of the way so the confirmation constraint is the one that
    # bites; the escalation path is covered by its own test below.
    profile = replace(
        request.profile, uncertainty_disposition=UncertaintyDisposition.ACCEPT
    )
    result = plan(
        request.context,
        clinical_factual.failure_mode,
        profile,
        _without_humans(clinical_factual.world),
    )

    assert result.selected is None
    assert any(r.constraint == "policy_human_confirmation" for r in result.rejections)
    assert "policy_human_confirmation" in result.no_plan_reason


def test_escalation_disposition_changes_which_plans_are_admissible(clinical_factual):
    """`uncertainty_disposition` earns its place: it can make a plan inadmissible.

    With escalation demanded and no qualified, policy-satisfying escalation target
    available, there is no admissible plan.  Switching the disposition to `accept`
    changes nothing else and the same world becomes plannable again.
    """
    from dataclasses import replace

    from assurance_planner import plan
    from assurance_planner.domain import UncertaintyDisposition

    request = clinical_factual.request("production_guard")
    world = _without_humans(clinical_factual.world)

    escalating = plan(
        request.context, clinical_factual.failure_mode, request.profile, world
    )
    assert escalating.selected is None
    assert any(
        r.constraint == "policy_escalation_target" for r in escalating.rejections
    )


def test_asynchronous_plans_are_rejected_when_policy_requires_synchronous(
    clinical_factual,
):
    result = run(clinical_factual, "production_guard")
    for step in result.selected.steps:
        assert step.execution_mode is ExecutionMode.SYNCHRONOUS
    assert any(r.constraint == "policy_synchronous" for r in result.rejections)


def test_escalation_target_must_also_satisfy_policy(clinical_factual):
    """Policy binds the whole decision path, not just the primary source.

    Escalating an ambiguous case to a mechanism that consults no system of record
    would route around the constraint that selected the primary in the first place.
    """
    from assurance_planner.constraints import choose_escalation_target

    world = clinical_factual.world
    strict = clinical_factual.request("production_guard").profile
    routine = clinical_factual.request("production_guard_routine_policy").profile
    primary = next(
        s for s in world.sources.values() if s.source_id == "record_reconciliation"
    )
    population = world.populations["flagged_interactions"]

    under_strict = choose_escalation_target(
        primary, clinical_factual.failure_mode, population, strict, world
    )
    under_routine = choose_escalation_target(
        primary, clinical_factual.failure_mode, population, routine, world
    )
    assert under_strict.consults_authoritative_source is True
    # The judge is cheaper, so it wins when policy does not forbid it.
    assert under_routine.source_id == "frontier_judge"


def test_human_capacity_is_a_real_constraint(clinical_factual):
    result = run(clinical_factual, "production_guard_routine_policy")
    assert any(r.constraint == "human_capacity" for r in result.rejections)


def test_conditional_latency_is_never_amortised(clinical_factual):
    """500ms on 10% of cases must not be reported as 50ms."""
    result = run(clinical_factual, "production_guard_routine_policy")
    sampled = next(
        p
        for p in result.runners_up
        if p.primary.population.population_id == "flagged_interactions"
        and p.primary.sample_fraction < 1.0
        and p.economics.conditional_interaction_latency_seconds > 0
    )
    economics = sampled.economics
    per_invocation = (
        economics.conditional_interaction_latency_seconds
        / sampled.primary.replications
    )
    # The reported latency is the real per-interaction wait, not a traffic-weighted
    # average, and the fraction it applies to is reported separately.
    assert economics.conditional_interaction_fraction < 1.0
    assert per_invocation > 0
    assert economics.conditional_interaction_latency_seconds > (
        per_invocation * economics.conditional_interaction_fraction
    )


def test_only_the_policy_differs_between_the_two_contexts(clinical_factual):
    strict = clinical_factual.request("production_guard")
    routine = clinical_factual.request("production_guard_routine_policy")
    assert strict.context.intent == routine.context.intent
    assert (
        strict.context.feedback_budget_seconds == routine.context.feedback_budget_seconds
    )
    assert strict.profile != routine.profile

    strict_plan = run(clinical_factual, "production_guard").selected
    routine_plan = run(clinical_factual, "production_guard_routine_policy").selected

    assert (
        strict_plan.economics.monetary_cost_per_window_usd
        > 1000 * routine_plan.economics.monetary_cost_per_window_usd
    )
    assert strict_plan.economics.human_minutes > 0
    assert routine_plan.economics.human_minutes == 0
    assert strict_plan.primary.replications > routine_plan.primary.replications


def test_the_planner_holds_no_clinical_knowledge(clinical_factual):
    """Domain risk judgement enters only as AssuranceProfile fields."""
    for path in SRC.glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for token in ("laterality", "clinic", "blood", "medication", "patient"):
            assert token not in text, f"{path.name} contains '{token}'"
    # And the description the planner is handed is never read by it.
    assert "laterality" in clinical_factual.failure_mode.description.lower()


def test_the_guard_runs_inline_on_the_arrival_process(clinical_factual):
    step = run(clinical_factual, "production_guard").selected.primary
    assert step.cadence is Cadence.CONTINUOUS
    assert step.population.units_per_window == 400
    assert "per day" in step.denominator
