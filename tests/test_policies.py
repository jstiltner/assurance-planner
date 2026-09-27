"""Parts 2, 3 and 15: what the baselines do, and that they are not cheating.

Two groups of tests here.  The first group pins the *rules*: what a fixed-N policy
spends, that early stopping is free, that confidence stopping is a different rule and
not a renaming of the first.  The second group is about leakage, and it is the more
important of the two, because a triage policy that peeks is not a weaker result -- it is
not a result at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from assurance_planner.characterization import CaseRun, CharacterizationRun
from assurance_planner.domain import FailureModeRef, SourceVersionRef
from assurance_planner.loader import load_characterization
from assurance_planner.policies import (
    ALTERNATE,
    Calibration,
    ConfidenceStop,
    CostModel,
    EarlyStopMajority,
    FixedN,
    HeterogeneityTriage,
    ProbeThenEscalate,
    default_policies,
    profile_slices,
    stratified_folds,
)

DATA = Path(__file__).resolve().parents[1] / "data"
EMPTY = Calibration()


@pytest.fixture
def mixed():
    return load_characterization(DATA / "judge_runs_mixed.yaml")


@pytest.fixture
def noisy():
    return load_characterization(DATA / "judge_runs_noisy.yaml")


@pytest.fixture
def systematic():
    return load_characterization(DATA / "judge_runs_systematic.yaml")


def _case(case_id: str, label: bool, bits: str, slice_id: str = "s") -> CaseRun:
    return CaseRun(
        case_id=case_id,
        reference_label=label,
        outcomes=tuple(b == "1" for b in bits),
        slice_id=slice_id,
    )


def _run(*cases: CaseRun) -> CharacterizationRun:
    return CharacterizationRun(
        evaluator_version=SourceVersionRef("judge", "v1"),
        failure_mode=FailureModeRef("MODE", "v1"),
        population_id="suite",
        distribution_id="release-1",
        cases=cases,
    )


# --------------------------------------------------------------------------------
# Baseline A: fixed N
# --------------------------------------------------------------------------------


def test_fixed_n_spends_exactly_n_calls_per_case(mixed):
    """The number a reader will check first, so it is checked here.

    Truncation is the only exception: eight cases in the benchmark recorded two
    observations, and no policy can spend what was never collected.
    """
    for n in (1, 3, 5, 8):
        outcomes = [FixedN(n).decide(case, EMPTY) for case in mixed.cases]
        for case, outcome in zip(mixed.cases, outcomes):
            assert outcome.judge_calls == min(n, case.runs)
            assert outcome.truncated is (case.runs < n)
        assert sum(o.judge_calls for o in outcomes) == sum(
            min(n, c.runs) for c in mixed.cases
        )


def test_an_exact_tie_is_unresolved_rather_than_rounded():
    """Four-four is not a verdict, and pretending it is hides the cases being paid for."""
    outcome = FixedN(8).decide(_case("C", True, "11110000"), EMPTY)
    assert outcome.verdict is None
    assert outcome.judge_calls == 8


def test_an_explicit_threshold_overrides_the_majority_rule():
    case = _case("C", True, "11000000")
    assert FixedN(8).decide(case, EMPTY).verdict is False
    assert FixedN(8, threshold_k=2).decide(case, EMPTY).verdict is True


# --------------------------------------------------------------------------------
# Baseline B: early stopping.  The theorem, not a fixture property.
# --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture",
    ["judge_runs_mixed", "judge_runs_noisy", "judge_runs_systematic"],
)
def test_early_stopping_returns_the_fixed_n_verdict_for_free(fixture):
    """Identical verdict on every case, never more calls.

    This is why the honest baseline for "did we save money" is early stopping and not
    fixed-N.  A harness that reported a triage policy's savings against fixed-N would
    be claiming credit for a rule that has been standard for decades.
    """
    run = load_characterization(DATA / f"{fixture}.yaml")
    saved = 0
    for case in run.cases:
        reference = FixedN(8).decide(case, EMPTY)
        early = EarlyStopMajority(8).decide(case, EMPTY)
        assert early.verdict == reference.verdict, case.case_id
        assert early.judge_calls <= reference.judge_calls, case.case_id
        saved += reference.judge_calls - early.judge_calls
    assert saved > 0, "early stopping that saves nothing is not the rule described"


def test_early_stopping_stops_the_moment_the_majority_is_locked():
    """Five flags out of an eight budget cannot be overturned by three more calls."""
    outcome = EarlyStopMajority(8).decide(_case("C", True, "11111000"), EMPTY)
    assert outcome.judge_calls == 5
    assert outcome.verdict is True


# --------------------------------------------------------------------------------
# Baseline C: confidence stopping is a different rule
# --------------------------------------------------------------------------------


def test_confidence_stopping_is_not_a_renaming_of_early_stopping(mixed):
    """If these two agreed everywhere, one of them would be redundant.

    They are statements about different things -- the underlying rate versus the vote --
    so they must be able to disagree on call count.  A test that only checked they gave
    the same verdicts would pass on a copy-paste.
    """
    differing = [
        case.case_id
        for case in mixed.cases
        if ConfidenceStop(8).decide(case, EMPTY).judge_calls
        != EarlyStopMajority(8).decide(case, EMPTY).judge_calls
    ]
    assert differing


def test_the_confidence_level_materially_changes_the_policy(mixed):
    """Recorded because the 90% choice is a tuning knob, and a visible one.

    At 95% the Wilson interval does not clear 0.5 until five consecutive agreeing
    observations, so the policy becomes strictly more expensive.  The report states the
    level it used; this test is what makes that statement checkable.
    """
    at_90 = sum(ConfidenceStop(8).decide(c, EMPTY).judge_calls for c in mixed.cases)
    at_95 = sum(
        ConfidenceStop(8, z=1.959963984540054).decide(c, EMPTY).judge_calls
        for c in mixed.cases
    )
    assert at_95 > at_90


# --------------------------------------------------------------------------------
# Baseline D and candidate E: escalation
# --------------------------------------------------------------------------------


def test_probe_escalation_escalates_exactly_the_cases_the_probe_split():
    policy = ProbeThenEscalate(probe=2)
    agreed = policy.decide(_case("A", True, "11111111"), EMPTY)
    split = policy.decide(_case("B", True, "10111111"), EMPTY)

    assert agreed.escalated is False
    assert agreed.verdict is True
    assert agreed.judge_calls == 2
    assert split.escalated_to == ALTERNATE
    assert split.verdict is None
    assert split.judge_calls == 2


def test_triage_escalates_a_slice_it_has_learned_not_to_trust():
    """The whole proposition, on data small enough to check by hand.

    Six of eight calibration cases in ``bad`` are unanimous and wrong, so unanimity in
    that slice is not evidence.  ``good`` is unanimous and right, so one call is enough.
    """
    bad = [_case(f"B{i}", True, "00000000", "bad") for i in range(6)]
    bad += [_case(f"B{i}", True, "11111111", "bad") for i in range(6, 8)]
    good = [_case(f"G{i}", True, "11111111", "good") for i in range(8)]
    calibration = Calibration.from_run(_run(*bad, *good))
    policy = HeterogeneityTriage()

    assert policy.route("bad", calibration) == "escalate"
    assert policy.route("good", calibration) == "trust"

    escalated = policy.decide(_case("new", True, "00000000", "bad"), calibration)
    trusted = policy.decide(_case("new", True, "11111111", "good"), calibration)
    assert escalated.escalated_to == ALTERNATE
    assert escalated.judge_calls == 1
    assert trusted.verdict is True
    assert trusted.judge_calls == 1


def test_triage_refuses_to_route_on_a_slice_it_has_barely_seen():
    """Four cases is not a behavioural profile, and pretending otherwise is the same
    false precision the previous pass spent its time documenting."""
    thin = _run(*[_case(f"T{i}", True, "00000000", "thin") for i in range(4)])
    calibration = Calibration.from_run(thin)

    assert calibration.slices["thin"].is_thin
    assert calibration.slices["thin"].stable_wrong == 1.0
    assert HeterogeneityTriage().route("thin", calibration) == "standard"


def test_triage_refuses_a_slice_measured_at_two_repetitions():
    """At two observations almost everything looks unanimous, so 'stable' means nothing."""
    sparse = _run(*[_case(f"S{i}", True, "00", "sparse") for i in range(12)])
    profile = profile_slices(sparse)["sparse"]

    assert profile.cases == 12
    assert profile.repetitions == 2.0
    assert profile.is_thin
    assert HeterogeneityTriage().route("sparse", Calibration.from_run(sparse)) == "standard"


def test_triage_falls_back_to_the_standard_rule_when_it_has_no_opinion(mixed):
    """On an unroutable slice it must be exactly early stopping, not something new."""
    policy = HeterogeneityTriage(n_max=8)
    for case in mixed.in_slice("implicit-correction"):
        triaged = policy.decide(case, EMPTY)
        standard = EarlyStopMajority(8).decide(case, EMPTY)
        assert triaged.judge_calls == standard.judge_calls
        assert triaged.verdict == standard.verdict


# --------------------------------------------------------------------------------
# Part 3: leakage
# --------------------------------------------------------------------------------


def test_folds_are_disjoint_and_cover_every_case(mixed):
    folds = stratified_folds(mixed, k=5)
    held_out: list[str] = []
    for fold in folds:
        held = {c.case_id for c in fold.held_out.cases}
        calibrated = {c.case_id for c in fold.calibration.cases}
        assert not held & calibrated
        assert held | calibrated == {c.case_id for c in mixed.cases}
        held_out.extend(held)

    assert len(held_out) == len(set(held_out)), "a case was tested twice"
    assert set(held_out) == {c.case_id for c in mixed.cases}


def test_folds_are_stratified_so_every_slice_appears_on_both_sides(mixed):
    """An unstratified split can put a whole regime in one fold, which would make the
    triage policy look magical or useless depending on the draw."""
    for fold in stratified_folds(mixed, k=5):
        for slice_id in mixed.slices:
            assert fold.held_out.in_slice(slice_id), (fold.index, slice_id)
            assert fold.calibration.in_slice(slice_id), (fold.index, slice_id)


def test_the_split_is_reproducible_without_running_anything(mixed):
    """Sorted, not shuffled: a reader can work out which fold a case is in by hand."""
    first = stratified_folds(mixed, k=5)
    second = stratified_folds(mixed, k=5)
    assert [
        [c.case_id for c in fold.held_out.cases] for fold in first
    ] == [[c.case_id for c in fold.held_out.cases] for fold in second]


def test_a_policy_cannot_see_the_case_it_is_deciding(mixed):
    """The leakage that would matter: calibrating on a case and then scoring it.

    A triage policy whose calibration included the case under test would be reading the
    reference label it is supposed to be predicting.  Asserted per fold rather than
    trusted, because this is the one defect that would invalidate every number.
    """
    for fold in stratified_folds(mixed, k=5):
        calibration = Calibration.from_run(fold.calibration)
        for case in fold.held_out.cases:
            assert case.case_id not in calibration.source_case_ids


def test_calibration_carries_slice_profiles_and_not_per_case_records(mixed):
    """The structural guarantee against memorising cases.

    A calibration holding a per-case table would let a policy look a case up by id.
    What it holds instead is three proportions and a count per slice, so the only thing
    a policy can key on is the subtype.
    """
    calibration = Calibration.from_run(mixed)
    assert set(calibration.slices) == set(mixed.slices)
    for profile in calibration.slices.values():
        assert 0.0 <= profile.stable_wrong <= 1.0
        assert profile.stable_correct + profile.stable_wrong + profile.unstable == pytest.approx(1.0)
    #: No case-level structure anywhere in a profile.
    assert not any(
        isinstance(value, (tuple, list, dict))
        for profile in calibration.slices.values()
        for value in (
            profile.stable_correct,
            profile.stable_wrong,
            profile.unstable,
            profile.repetitions,
        )
    )


def test_no_policy_reads_the_generated_regime_note(mixed):
    """The fixtures record the generating regime in a per-case note for the reader.

    A policy that read it would be scoring itself against the answer key.  Checked by
    stripping every note and asserting nothing changes.
    """
    stripped = mixed.with_cases(
        tuple(
            CaseRun(
                case_id=c.case_id,
                reference_label=c.reference_label,
                outcomes=c.outcomes,
                slice_id=c.slice_id,
                note="",
            )
            for c in mixed.cases
        )
    )
    assert any(c.note for c in mixed.cases)

    for policy in default_policies():
        original = [
            policy.decide(c, Calibration.from_run(mixed)) for c in mixed.cases
        ]
        without = [
            policy.decide(c, Calibration.from_run(stripped)) for c in stripped.cases
        ]
        assert [(o.verdict, o.judge_calls, o.escalated_to) for o in original] == [
            (o.verdict, o.judge_calls, o.escalated_to) for o in without
        ], policy.name


def test_fewer_than_two_folds_is_refused(mixed):
    with pytest.raises(ValueError, match="k >= 2"):
        stratified_folds(mixed, k=1)


# --------------------------------------------------------------------------------
# Cost model
# --------------------------------------------------------------------------------


def test_the_cost_model_prices_the_three_sources_separately():
    cost = CostModel()
    assert cost.escalation_cost(ALTERNATE) == cost.alternate_cost_usd
    assert cost.escalation_cost("human") == cost.human_cost_usd
    assert cost.human_cost_usd > cost.alternate_cost_usd > cost.judge_cost_usd
    assert cost.human_latency_seconds > cost.alternate_latency_seconds
