"""Acceptance scenario B -- known full-duplex silence defect.

The judge in this fixture is qualified for the failure mode, has twelve prove-red
observations, and is available.  It is not disqualified; it is out-competed.  The test
that matters is that the *reason* is economic, and that no planner code mentions this
scenario, this failure mode, or the word "judge".
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from assurance_planner.domain import Cadence, ExecutionMode, SourceKind
from assurance_planner.ranking import explain_loss
from conftest import run

SRC = Path(__file__).resolve().parents[1] / "src" / "assurance_planner"


def test_verify_selects_the_machine_verifiable_oracle(duplex_silence):
    result = run(duplex_silence, "verify")
    step = result.selected.primary

    assert str(step.source.ref) == "state_machine_assertion@v2"
    assert step.source.kind is SourceKind.DETERMINISTIC
    assert step.population.population_id == "focused_repro"
    assert step.replications == 1
    assert step.threshold_k == 1
    assert result.selected.economics.blocking_feedback_seconds == 120.0
    assert result.selected.economics.monetary_cost_usd == 0.0


def test_one_red_and_one_green_suffice_for_a_deterministic_evaluator(duplex_silence):
    evidence = duplex_silence.world.qualification[
        next(
            key
            for key in duplex_silence.world.qualification
            if key.source_version.source_id == "state_machine_assertion"
            and key.population_id == "focused_repro"
        )
    ]
    assert evidence.prove_red_runs == 1
    assert evidence.prove_green_runs == 1
    assert run(duplex_silence, "verify").selected.primary.replications == 1


def test_the_judge_is_admissible_and_loses_on_economics_not_on_being_a_judge(
    duplex_silence,
):
    result = run(duplex_silence, "verify")
    winner = result.selected

    judges = [
        p
        for p in result.runners_up
        if p.primary.source.kind is SourceKind.STOCHASTIC_JUDGE
    ]
    assert judges, "the judge should be admissible here, merely more expensive"

    for judge_plan in judges:
        reason = explain_loss(winner, judge_plan)
        assert "dominated on cost" in reason or "more developer waiting" in reason
        assert judge_plan.economics.monetary_cost_per_window_usd > 0.0


def test_the_planner_explains_why_a_better_judge_is_not_worth_buying(duplex_silence):
    """frontier_judge has higher sensitivity than the oracle needs.  It adds nothing."""
    result = run(duplex_silence, "verify")
    frontier = next(
        p
        for p in result.runners_up
        if p.primary.source.source_id == "frontier_judge"
    )
    # The oracle already bounds both error directions at zero; extra sensitivity buys
    # no assurance, so the comparison collapses to price.
    assert result.selected.primary.miss_probability == 0.0
    assert frontier.primary.miss_probability >= 0.0
    assert "dominated on cost" in explain_loss(result.selected, frontier)


def test_blast_radius_buys_the_broad_suite_once_not_per_iteration(duplex_silence):
    result = run(duplex_silence, "blast_radius")
    step = result.selected.primary

    assert step.population.population_id == "duplex_regression_corpus"
    assert step.units_selected == 20
    assert step.cadence is Cadence.PER_CHECKPOINT
    assert step.cadence is not Cadence.PER_CHANGE
    assert step.execution_mode is ExecutionMode.SYNCHRONOUS
    assert result.selected.economics.blocking_feedback_seconds == 20 * 120.0


def test_focused_then_broad_is_a_scope_change_not_a_mechanism_change(duplex_silence):
    verify = run(duplex_silence, "verify").selected.primary
    broad = run(duplex_silence, "blast_radius").selected.primary
    assert verify.source.ref == broad.source.ref
    assert verify.units_selected == 1
    assert broad.units_selected == 20
    assert verify.replications == broad.replications == 1


def test_no_planner_module_is_aware_of_any_scenario(duplex_silence):
    """Guards against the scenarios being special-cased by name."""
    forbidden = [
        "silence",
        "duplex",
        "laterality",
        "clinical",
        "voice",
        "VFD-",
        "HCF-",
        "state_machine_assertion",
        "transcript_judge",
        "frontier_judge",
        "record_reconciliation",
    ]
    for path in SRC.glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token.lower() not in text, f"{path.name} references '{token}'"


def test_cli_runs_the_scenario_end_to_end():
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "assurance_planner.cli",
            str(root / "scenarios" / "duplex_silence.yaml"),
            "--context",
            "verify",
        ],
        capture_output=True,
        text=True,
        cwd=root,
    )
    assert completed.returncode == 0
    assert "Selected plan" in completed.stdout
    assert "state_machine_assertion@v2" in completed.stdout
    assert "Rejected" in completed.stdout
