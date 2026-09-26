"""Acceptance scenario A -- early voice-agent development.

The load-bearing assertion in this file is not "the planner picks the focused run".
It is that the team's real 2-minute / 40-minute / ~5-hour / ~$10 hierarchy is
reproduced as arithmetic over (cases x replications x per-case latency), with the
replication count derived from measured noise and a stated error target.  If any of
those numbers had to be written into the fixture, the scenario would be worthless.
"""

from __future__ import annotations

from assurance_planner.domain import Cadence, ExecutionMode, Intent, SourceKind
from conftest import rejection_constraints, run

CASE_SECONDS = 120.0


def test_inner_loop_selects_focused_single_run(voice_early):
    result = run(voice_early, "inner_loop")
    step = result.selected.primary

    assert str(step.source.ref) == "behavioral_simulation@v3"
    assert step.population.population_id == "affected_scenario"
    assert step.units_selected == 1
    assert step.replications == 1
    assert step.cadence is Cadence.PER_CHANGE
    assert step.execution_mode is ExecutionMode.SYNCHRONOUS

    # ~2 minutes, as arithmetic.
    assert result.selected.economics.blocking_feedback_seconds == 1 * 1 * CASE_SECONDS
    assert result.selected.economics.monetary_cost_usd == 0.0


def test_inner_loop_rejects_the_judge_for_want_of_red_observations(voice_early):
    """A single RED from a noisy judge is not proof, and the planner says why.

    The judge needs 7 runs to meet the 0.05 bound, so it needs 7 RED observations to
    support a verification claim.  It has 3.  Nothing here knows that judges are
    noisy -- the requirement is the derived replication count.
    """
    result = run(voice_early, "inner_loop")
    constraints = rejection_constraints(
        result, "transcript_judge@v7", "affected_scenario"
    )
    assert "prove_red_sufficient" in constraints


def test_checkpoint_selects_whole_corpus_once_at_forty_minutes(voice_early):
    result = run(voice_early, "checkpoint")
    step = result.selected.primary

    assert str(step.source.ref) == "transcript_judge@v7"
    assert step.population.population_id == "scenario_corpus"
    assert step.units_selected == 20
    assert step.replications == 1
    # 20 x 1 x 120s = 40 minutes.
    assert result.selected.economics.blocking_feedback_seconds == 20 * 1 * CASE_SECONDS
    assert result.selected.economics.blocking_feedback_seconds / 60 == 40.0


def test_checkpoint_does_not_run_per_change(voice_early):
    """Buying the broad suite on all 20 changes a day is 13 hours of waiting."""
    result = run(voice_early, "checkpoint")
    assert result.selected.primary.cadence is Cadence.PER_CHECKPOINT


def test_nightly_derives_multiple_replications_and_the_five_hour_suite(voice_early):
    result = run(voice_early, "nightly")
    step = result.selected.primary
    economics = result.selected.economics

    assert str(step.source.ref) == "transcript_judge@v7"
    assert step.units_selected == 20
    # Derived from sensitivity 0.70 / FPR 0.10 against a 0.05 error requirement.
    # The team's empirical heuristic was 8 runs; nothing told the planner that.
    assert step.replications == 7
    assert step.threshold_k == 3

    # ~5 hours and ~$10, both as arithmetic.
    assert economics.total_invocations == 140
    assert economics.background_wall_clock_seconds == 20 * 7 * CASE_SECONDS
    assert 4.5 <= economics.background_wall_clock_seconds / 3600 <= 5.0
    assert economics.monetary_cost_usd == 8.75

    # It runs out of band, so it does not block anybody.
    assert step.cadence is Cadence.NIGHTLY
    assert step.execution_mode is ExecutionMode.ASYNCHRONOUS
    assert economics.blocking_feedback_seconds == 0.0


def test_the_three_tiers_are_a_strict_hierarchy(voice_early):
    """Mechanism, scope, replications and cadence move independently."""
    inner = run(voice_early, "inner_loop").selected.primary
    checkpoint = run(voice_early, "checkpoint").selected.primary
    nightly = run(voice_early, "nightly").selected.primary

    # scope grows
    assert inner.units_selected < checkpoint.units_selected
    assert checkpoint.units_selected == nightly.units_selected
    # replications grow only at the last step, where the error target tightened
    assert inner.replications == checkpoint.replications == 1
    assert nightly.replications > checkpoint.replications
    # cadence relaxes as the work grows
    assert (inner.cadence, checkpoint.cadence, nightly.cadence) == (
        Cadence.PER_CHANGE,
        Cadence.PER_CHECKPOINT,
        Cadence.NIGHTLY,
    )
    # mechanism changed between tier 1 and tier 2
    assert inner.source.kind is SourceKind.DETERMINISTIC
    assert checkpoint.source.kind is SourceKind.STOCHASTIC_JUDGE


def test_discovery_pays_for_the_judge_because_the_free_oracle_cannot_discover(
    voice_early,
):
    """The counterexample to 'it always prefers the cheapest deterministic check'.

    A free, fully qualified deterministic assertion is available and loses to a paid
    judge, because a fixed criterion cannot surface a failure nobody has specified.
    """
    result = run(voice_early, "discovery")
    step = result.selected.primary

    assert str(step.source.ref) == "transcript_judge@v7"
    assert step.source.open_ended is True
    assert result.selected.economics.monetary_cost_usd > 0.0

    constraints = rejection_constraints(
        result, "behavioral_simulation@v3", "affected_scenario"
    )
    assert "goal_source_capability" in constraints


def test_discovery_will_not_shrink_its_search_to_one_case(voice_early):
    result = run(voice_early, "discovery")
    assert result.selected.primary.units_selected == 20
    constraints = rejection_constraints(
        result, "transcript_judge@v7", "affected_scenario"
    )
    assert "goal_population_coverage" in constraints


def test_planning_is_deterministic(voice_early):
    for name in ("inner_loop", "checkpoint", "nightly", "discovery"):
        first = run(voice_early, name).selected
        second = run(voice_early, name).selected
        assert first.plan_id == second.plan_id
        assert first.economics == second.economics


def test_every_scope_carries_an_explicit_denominator(voice_early):
    for name in ("inner_loop", "checkpoint", "nightly", "discovery"):
        result = run(voice_early, name)
        for step in result.selected.steps:
            assert step.denominator
            assert step.denominator in step.scope_phrase()


def test_intent_is_the_only_thing_separating_release_from_discover(voice_early):
    """Same world, same profile family, same budget: different evidence goal."""
    nightly = run(voice_early, "nightly").selected.primary
    discovery = run(voice_early, "discovery").selected.primary
    assert nightly.source.ref == discovery.source.ref
    assert nightly.replications != discovery.replications
