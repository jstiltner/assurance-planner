"""Acceptance tests 3, 4 and 5: does repetition buy information?

These tests exist to make the diagnostics falsifiable in both directions.  It is easy
to write a warning that always fires; the homogeneous control below is the test that
proves this one does not.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from assurance_planner.characterization import (
    CaseRun,
    CharacterizationRun,
    characterize,
)
from assurance_planner.domain import FailureModeRef, SourceVersionRef
from assurance_planner.loader import load_characterization
from assurance_planner.statistics import minimal_procedure

DATA = Path(__file__).resolve().parents[1] / "data"

#: The same policy number the CLI defaults to.  Stated here as an input, never derived
#: from any of the data below -- see docs/measurement_review.md on the separation.
MAX_ERROR = 0.05


def _run(cases: tuple[CaseRun, ...]) -> CharacterizationRun:
    return CharacterizationRun(
        evaluator_version=SourceVersionRef("synthetic_judge", "v1"),
        failure_mode=FailureModeRef("SYNTHETIC", "v1"),
        population_id="unit-test",
        distribution_id="unit-test-distribution",
        cases=cases,
    )


def _pattern(case_id: str, label: bool, bits: str) -> CaseRun:
    return CaseRun(
        case_id=case_id,
        reference_label=label,
        outcomes=tuple(b == "1" for b in bits),
    )


@pytest.fixture
def noisy():
    return load_characterization(DATA / "judge_runs_noisy.yaml")


@pytest.fixture
def systematic():
    return load_characterization(DATA / "judge_runs_systematic.yaml")


@pytest.fixture
def small_sample():
    return load_characterization(DATA / "judge_runs_small_sample.yaml")


# --------------------------------------------------------------------------------
# The premise of the whole experiment
# --------------------------------------------------------------------------------


def test_pooled_rates_cannot_tell_the_two_evaluators_apart(noisy, systematic):
    """The planner's two inputs give the identical answer for opposite evaluators.

    A is stochastic around the right label and repetition genuinely helps.  B is
    near-deterministic, wrong on a quarter of its positives, and repetition helps not
    at all.  Both reach the planner as a sensitivity and a false-positive rate, and
    from those it derives the same plan.  This is the finding, not a fixture artefact:
    everything else in this file is about what the planner would need to see instead.
    """
    a = characterize(noisy, MAX_ERROR)
    b = characterize(systematic, MAX_ERROR)

    procedure_a = minimal_procedure(
        a.sensitivity.point, a.false_positive_rate.point, MAX_ERROR
    )
    procedure_b = minimal_procedure(
        b.sensitivity.point, b.false_positive_rate.point, MAX_ERROR
    )
    assert procedure_a is not None and procedure_b is not None
    assert (procedure_a.replications, procedure_a.threshold_k) == (
        procedure_b.replications,
        procedure_b.threshold_k,
    )
    assert a.planner_replications() == b.planner_replications()

    #: And the per-case records, which the planner never sees, are not close.
    assert len(a.unfixable_cases) == 0
    assert len(b.unfixable_cases) >= 5


# --------------------------------------------------------------------------------
# Acceptance 3: a noisy-but-useful judge benefits from repetition
# --------------------------------------------------------------------------------


def test_a_noisy_judge_benefits_from_repetition(noisy):
    analysis = characterize(noisy, MAX_ERROR)

    #: Every case fluctuates; none is stuck on the wrong answer.
    assert analysis.unfixable_cases == ()

    #: Most cases need more than one run and are fixed by having them.  That is what
    #: "repetition buys information" means at the case level.
    helped = [v for v in analysis.verdicts if v.verdict == "helped_by_repetition"]
    assert len(helped) > len(analysis.run.cases) // 2

    #: And the aggregate error falls monotonically as n grows, at the planner's own k.
    misses = [p.empirical_miss for p in analysis.curve]
    assert misses[-1] < misses[0] / 2


def test_a_noisy_judge_is_not_flagged_for_clustering(noisy):
    """Acceptance 5, negative half: the warning does not fire on the control."""
    analysis = characterize(noisy, MAX_ERROR)
    assert not analysis.independence_is_implausible
    assert analysis.sensitivity.dispersion is not None
    assert analysis.sensitivity.dispersion.phi < 2.0


# --------------------------------------------------------------------------------
# Acceptance 4: a systematically wrong judge is not fixed by repetition
# --------------------------------------------------------------------------------


def test_repetition_does_not_rescue_a_systematically_wrong_judge(systematic):
    analysis = characterize(systematic, MAX_ERROR)

    unfixable = analysis.unfixable_cases
    assert len(unfixable) >= 5
    #: Not merely unresolved: the evaluator is confident and wrong on these.  Zero
    #: disagreement across eight runs means repetition is sampling the same mistake.
    for verdict in unfixable:
        assert verdict.case.disagreement_rate < 0.4
        assert verdict.case.correct_rate < 0.5

    #: The empirical miss rate does not improve with n.  Twelve runs buy what one buys.
    misses = [p.empirical_miss for p in analysis.curve]
    assert misses[-1] > 0.2
    assert misses[-1] > misses[0] * 0.8

    #: So no replication count in range satisfies the target, though the model claims
    #: one does.
    assert analysis.planner_replications() is not None
    assert analysis.empirical_replications() is None


def test_higher_agreement_does_not_mean_a_better_judge(noisy, systematic):
    """Same-case agreement is a trap read on its own.

    B agrees with itself *more* than A does, because being reliably wrong is a form of
    reliability.  Any report that shows repeatability without showing correctness
    alongside it is actively misleading, which is why render_characterization prints
    the consistently-and-confidently-wrong list separately.
    """
    a = characterize(noisy, MAX_ERROR)
    b = characterize(systematic, MAX_ERROR)
    assert b.mean_agreement > a.mean_agreement
    assert len(b.unfixable_cases) > len(a.unfixable_cases)


# --------------------------------------------------------------------------------
# Acceptance 5: the i.i.d. binomial assumption is flagged on clustered data
# --------------------------------------------------------------------------------


def test_clustered_data_is_flagged_as_implausible(systematic):
    analysis = characterize(systematic, MAX_ERROR)

    assert analysis.independence_is_implausible

    dispersion = analysis.sensitivity.dispersion
    assert dispersion is not None
    assert dispersion.phi > 2.0
    assert dispersion.icc > 0.5
    #: The count of runs the data actually supports, versus the count claimed.
    assert dispersion.effective_runs < analysis.sensitivity.runs / 4


def test_clustering_widens_the_interval_it_should_widen(systematic):
    analysis = characterize(systematic, MAX_ERROR)
    assert analysis.sensitivity.corrected_width > analysis.sensitivity.naive_width * 2


def test_a_homogeneous_judge_is_not_flagged(noisy):
    """The control for the control: perfectly i.i.d. data must come out clean.

    Constructed rather than sampled, so the assertion cannot be a seed accident.  Every
    case shares one flag rate, so the only variation is within-case, which is exactly
    what the binomial model assumes.  phi lands near one and nothing warns.
    """
    positives = tuple(
        _pattern(f"P{i}", True, bits)
        for i, bits in enumerate(["11111100", "11110110", "11011110", "01111110"] * 4)
    )
    negatives = tuple(
        _pattern(f"N{i}", False, bits)
        for i, bits in enumerate(["00000010", "00100000", "01000000", "00001000"] * 4)
    )
    analysis = characterize(_run(positives + negatives), MAX_ERROR)

    assert not analysis.independence_is_implausible
    assert analysis.sensitivity.dispersion is not None
    assert analysis.sensitivity.dispersion.phi < 1.5
    assert analysis.sensitivity.dispersion.icc < 0.1
    #: With no heterogeneity left, model and empirical curves agree.
    for point in analysis.curve:
        assert point.empirical_miss == pytest.approx(point.model_miss, abs=0.02)


def test_the_illustrative_contrast_is_separated(noisy):
    """The two patterns from the brief, side by side.

    Both pool to sensitivity 0.5 on positives.  The all-or-nothing version is pure
    between-case structure; the alternating version is pure within-case noise.  The
    aggregate cannot tell them apart and the consequence is total: repetition fixes
    every case in one and no case in the other.
    """
    split = _run(
        tuple(_pattern(f"P{i}", True, "11111111") for i in range(5))
        + tuple(_pattern(f"P{i + 5}", True, "00000000") for i in range(5))
        + tuple(_pattern(f"N{i}", False, "00000000") for i in range(10))
    )
    mixed = _run(
        tuple(_pattern(f"P{i}", True, "10100110") for i in range(5))
        + tuple(_pattern(f"P{i + 5}", True, "01101001") for i in range(5))
        + tuple(_pattern(f"N{i}", False, "00000000") for i in range(10))
    )

    split_analysis = characterize(split, MAX_ERROR)
    mixed_analysis = characterize(mixed, MAX_ERROR)

    assert split_analysis.sensitivity.point == mixed_analysis.sensitivity.point == 0.5
    assert split_analysis.independence_is_implausible
    assert not mixed_analysis.independence_is_implausible
    #: Five cases the split judge will never get right, and none in the mixed one --
    #: a coin flip per run converges, a fixed wrong answer does not.
    assert len(split_analysis.unfixable_cases) == 5
    assert split_analysis.empirical_replications() is None
    assert mixed_analysis.unfixable_cases == ()
    assert all(
        v.verdict == "helped_by_repetition"
        for v in mixed_analysis.verdicts
        if v.case.reference_label
    )


# --------------------------------------------------------------------------------
# Small samples
# --------------------------------------------------------------------------------


def test_a_good_point_estimate_on_twenty_cases_says_almost_nothing(small_sample):
    analysis = characterize(small_sample, MAX_ERROR)

    assert analysis.sensitivity.point == 0.9
    low, high = analysis.sensitivity.naive_interval
    assert high - low > 0.35

    #: One run per case, so there is no within-case variation to measure at all.  The
    #: analysis must say so rather than reporting a dispersion of one.
    assert analysis.sensitivity.dispersion is None
    assert analysis.false_positive_rate.dispersion is None
    assert not analysis.independence_is_implausible


def test_single_run_cases_report_no_disagreement_rather_than_agreement(small_sample):
    for case in small_sample.cases:
        assert case.runs == 1
        assert case.disagreement_rate == 0.0
