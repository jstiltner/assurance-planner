"""Metamorphic tests.

A planner that emits plausible static plans has proved nothing.  These tests change
exactly one input and assert what must move -- and, just as importantly, what must
not.  Each test states the mechanism it believes is responsible, so that a test
passing for the wrong reason is visible.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from assurance_planner import plan
from assurance_planner.domain import (
    EvidenceSourceVersion,
    ExecutionProfile,
    Intent,
    QualificationEvidence,
    QualificationKey,
    SourceKind,
    SourceVersionRef,
)
from assurance_planner.statistics import minimal_procedure
from conftest import run


def _plan(scenario, context_name, world=None, profile=None, context=None):
    request = scenario.request(context_name)
    return plan(
        context or request.context,
        scenario.failure_mode,
        profile or request.profile,
        world or scenario.world,
    )


def _machine_verifiable_oracle_for_corpus(scenario) -> QualificationEvidence:
    """Someone writes an assertion covering the whole corpus and qualifies it."""
    return QualificationEvidence(
        key=_qual_key(scenario, "behavioral_simulation@v3", "scenario_corpus"),
        positive_cases=30,
        true_positives=30,
        negative_cases=30,
        false_positives=0,
        prove_red_runs=1,
        prove_green_runs=1,
        evidence_date=date(2026, 9, 25),
    )


def _qual_key(scenario, source: str, population: str) -> QualificationKey:
    source_id, _, version = source.partition("@")
    return QualificationKey(
        source_version=SourceVersionRef(source_id, version),
        failure_mode=scenario.failure_mode.ref,
        population_id=population,
        distribution_id=scenario.world.system_under_test.distribution_id,
    )


# --------------------------------------------------------------------------------
# 1. Judge becomes less noisy
# --------------------------------------------------------------------------------


def test_1_less_noisy_judge_needs_fewer_replications(voice_early):
    """Mechanism: the binomial bound, not a lookup table."""
    before = run(voice_early, "nightly").selected.primary
    assert before.replications == 7

    world = voice_early.world
    for population in ("affected_scenario", "scenario_corpus"):
        world = world.requalify(
            _qual_key(voice_early, "transcript_judge@v7", population),
            #: 0.90 sensitivity, 0.03 false-positive rate -- expressed as the study
            #: that would produce them, because rates are no longer storable.
            true_positives=108,
            negative_cases=100,
            false_positives=3,
        )

    after = _plan(voice_early, "nightly", world=world).selected.primary
    assert after.replications == 3
    assert after.replications < before.replications
    # Assurance did not weaken to buy the saving.
    assert after.miss_probability <= 0.05
    assert after.false_alarm_probability <= 0.05


@pytest.mark.parametrize("false_positive_rate", [0.02, 0.05, 0.10, 0.15, 0.20])
def test_1_replications_are_monotone_in_sensitivity(false_positive_rate):
    """Weak monotonicity is a property of the model, over a grid, not one fixture."""
    previous = None
    for sensitivity in (0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99):
        procedure = minimal_procedure(sensitivity, false_positive_rate, 0.05)
        assert procedure is not None
        if previous is not None:
            assert procedure.replications <= previous
        previous = procedure.replications


@pytest.mark.parametrize("sensitivity", [0.60, 0.70, 0.80, 0.90, 0.99])
def test_1_replications_are_monotone_in_false_positive_rate(sensitivity):
    previous = None
    for false_positive_rate in (0.02, 0.05, 0.08, 0.10, 0.15, 0.20):
        procedure = minimal_procedure(sensitivity, false_positive_rate, 0.05)
        assert procedure is not None
        if previous is not None:
            assert procedure.replications >= previous
        previous = procedure.replications


# --------------------------------------------------------------------------------
# 2. Judge becomes cheaper
# --------------------------------------------------------------------------------


def test_2_cheaper_judge_does_not_displace_evidence_that_already_dominates(
    duplex_silence,
):
    """A free judge still loses to a free oracle that is faster and less noisy.

    Price is not a reason to buy evidence you do not need.
    """
    before = run(duplex_silence, "verify").selected.primary
    world = duplex_silence.world.reprice(
        SourceVersionRef("transcript_judge", "v7"), cost_per_invocation_usd=0.0
    )
    after = _plan(duplex_silence, "verify", world=world).selected.primary

    assert after.source.ref == before.source.ref == SourceVersionRef(
        "state_machine_assertion", "v2"
    )
    assert after.replications == before.replications == 1


def test_2_cheaper_judge_is_adopted_when_it_economically_replaces_another_path(
    clinical_factual,
):
    """The other half: usage MAY increase when price makes it the cheapest route."""
    request = clinical_factual.request("production_guard_routine_policy")

    # Make reconciliation the expensive option so the two paths actually compete.
    world = clinical_factual.world.reprice(
        SourceVersionRef("record_reconciliation", "v1"),
        cost_per_invocation_usd=5.00,
    )
    expensive_judge = _plan(
        clinical_factual, "production_guard_routine_policy", world=world
    ).selected
    cheap_judge = _plan(
        clinical_factual,
        "production_guard_routine_policy",
        world=world.reprice(
            SourceVersionRef("frontier_judge", "v2"), cost_per_invocation_usd=0.0001
        ),
    ).selected

    assert expensive_judge.primary.source.source_id == "record_reconciliation"
    assert cheap_judge.primary.source.source_id == "frontier_judge"
    # Usage of the judge went from nothing to something on a pure price change.
    assert cheap_judge.economics.total_invocations > 0
    assert request.profile.sampling_allowed is True


def test_2_price_changes_do_not_touch_qualification(clinical_factual):
    """Red-team question 7, asserted structurally rather than promised in a doc."""
    before = dict(clinical_factual.world.qualification)
    world = clinical_factual.world.reprice(
        SourceVersionRef("frontier_judge", "v2"), cost_per_invocation_usd=99.0
    )
    assert world.qualification == before
    assert world.economics != clinical_factual.world.economics
    # And the derived replication count for that source is unchanged.
    key = _qual_key(clinical_factual, "frontier_judge@v2", "flagged_interactions")
    assert world.qualification[key] == before[key]


# --------------------------------------------------------------------------------
# 3. Failure becomes machine-verifiable
# --------------------------------------------------------------------------------


def test_3_a_new_qualified_oracle_displaces_stochastic_judgement(voice_early):
    """Someone writes a machine-verifiable assertion for the whole corpus.

    Nothing else changes -- same judge, same prices, same policy, same intent.
    """
    before = run(voice_early, "nightly").selected
    assert before.primary.source.kind is SourceKind.STOCHASTIC_JUDGE
    assert before.primary.replications == 7

    world = voice_early.world
    world.add_qualification(_machine_verifiable_oracle_for_corpus(voice_early))
    after = _plan(voice_early, "nightly", world=world).selected

    assert after.primary.source.kind is SourceKind.DETERMINISTIC
    assert after.primary.replications == 1
    # It dominates on all three: assurance, cost and time.
    assert after.primary.miss_probability <= before.primary.miss_probability
    assert (
        after.economics.monetary_cost_usd < before.economics.monetary_cost_usd
    )
    assert (
        after.economics.background_wall_clock_seconds
        < before.economics.background_wall_clock_seconds
    )


def test_3_the_oracle_does_not_displace_the_judge_for_discovery(voice_early):
    """Dominance is role-specific.  The same new oracle changes nothing here."""
    world = voice_early.world
    world.add_qualification(_machine_verifiable_oracle_for_corpus(voice_early))
    after = _plan(voice_early, "discovery", world=world).selected.primary
    assert after.source.kind is SourceKind.STOCHASTIC_JUDGE


# --------------------------------------------------------------------------------
# 4. Assurance policy tightens
# --------------------------------------------------------------------------------


def test_4_tightening_the_error_requirement_never_weakens_the_plan(voice_early):
    screen = voice_early.request("checkpoint").profile
    gate = voice_early.request("nightly").profile
    assert gate.maximum_error_requirement < screen.maximum_error_requirement

    loose = _plan(voice_early, "nightly", profile=screen).selected
    tight = _plan(voice_early, "nightly", profile=gate).selected

    assert tight.primary.replications >= loose.primary.replications
    assert tight.primary.miss_probability <= loose.primary.miss_probability
    assert tight.primary.false_alarm_probability <= loose.primary.false_alarm_probability
    assert tight.economics.total_invocations >= loose.economics.total_invocations


def test_4_tightening_policy_flags_makes_sampling_and_automation_inadmissible(
    clinical_factual,
):
    routine = run(clinical_factual, "production_guard_routine_policy").selected
    strict = run(clinical_factual, "production_guard").selected

    assert strict.primary.sample_fraction == 1.0
    assert strict.primary.sample_fraction >= routine.primary.sample_fraction
    assert any(s.source.kind is SourceKind.HUMAN for s in strict.steps)
    assert not any(s.source.kind is SourceKind.HUMAN for s in routine.steps)
    assert strict.primary.source.consults_authoritative_source
    assert strict.primary.miss_probability <= routine.primary.miss_probability


def test_4_tightening_one_flag_at_a_time_is_monotone(clinical_factual):
    """Each policy flag independently removes plans; none adds any."""
    request = clinical_factual.request("production_guard_routine_policy")
    base = request.profile
    baseline = _plan(
        clinical_factual, "production_guard_routine_policy", profile=base
    )
    baseline_count = len(baseline.runners_up) + 1

    for field, value in [
        ("sampling_allowed", False),
        ("authoritative_source_required", True),
        ("synchronous_requirement", True),
        ("human_confirmation_required", True),
        ("maximum_error_requirement", 0.001),
    ]:
        tightened = _plan(
            clinical_factual,
            "production_guard_routine_policy",
            profile=replace(base, **{field: value}),
        )
        count = (len(tightened.runners_up) + 1) if tightened.selected else 0
        assert count <= baseline_count, f"tightening {field} admitted more plans"


# --------------------------------------------------------------------------------
# 5. Development intent changes
# --------------------------------------------------------------------------------


def test_5_discover_to_verify_fix_moves_spend_from_broad_to_focused(voice_early):
    """Only `intent` changes.  Budget, policy, world and prices are held constant."""
    discovery_request = voice_early.request("discovery")
    verify_context = replace(
        discovery_request.context,
        intent=Intent.VERIFY_FIX,
        feedback_budget_seconds=600,
    )
    discover_context = replace(
        discovery_request.context, feedback_budget_seconds=600
    )

    discovering = _plan(
        voice_early, "discovery", context=discover_context
    ).selected
    verifying = _plan(voice_early, "discovery", context=verify_context).selected

    assert discovering.primary.units_selected == 20
    assert verifying.primary.units_selected == 1
    assert (
        verifying.economics.monetary_cost_per_window_usd
        < discovering.economics.monetary_cost_per_window_usd
    )
    assert verifying.economics.total_invocations < discovering.economics.total_invocations
    # And the mechanism changed, because the goal changed.
    assert discovering.primary.source.open_ended is True
    assert verifying.primary.source.open_ended is False


# --------------------------------------------------------------------------------
# 6. Feedback budget changes
# --------------------------------------------------------------------------------


def test_6_a_long_plan_rejected_in_the_inner_loop_is_admissible_nightly(voice_early):
    """The same 4.7-hour plan: inadmissible blocking, admissible out of band."""
    nightly = run(voice_early, "nightly").selected
    assert nightly.economics.background_wall_clock_seconds == 20 * 7 * 120.0

    inner = run(voice_early, "inner_loop")
    assert inner.selected.economics.blocking_feedback_seconds == 120.0
    assert not any(
        p.economics.background_wall_clock_seconds > 3600
        for p in [inner.selected, *inner.runners_up]
    )


def test_6_shrinking_the_budget_alone_removes_the_broad_plan(voice_early):
    """One field moves; the corpus run stops being purchasable."""
    request = voice_early.request("checkpoint")
    roomy = _plan(voice_early, "checkpoint", context=request.context).selected
    assert roomy.economics.blocking_feedback_seconds == 2400.0

    cramped = _plan(
        voice_early,
        "checkpoint",
        context=replace(request.context, feedback_budget_seconds=300),
    )
    assert cramped.selected is None
    assert any(r.constraint == "budget_feedback" for r in cramped.rejections)


def test_6_growing_the_budget_alone_restores_it(voice_early):
    request = voice_early.request("checkpoint")
    for seconds, expect_plan in [(300, False), (2400, True)]:
        result = _plan(
            voice_early,
            "checkpoint",
            context=replace(request.context, feedback_budget_seconds=seconds),
        )
        assert (result.selected is not None) is expect_plan
