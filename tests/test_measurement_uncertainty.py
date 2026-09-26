"""Acceptance tests for estimate uncertainty and the estimator policy.

Split from ``test_measurement.py`` only for length; the numbering continues.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from assurance_planner import plan
from assurance_planner.domain import Estimator, QualificationEvidence, QualificationKey
from assurance_planner.domain import SourceVersionRef
from assurance_planner.statistics import minimal_procedure, wilson_interval

from test_measurement import _evidence


# --------------------------------------------------------------------------------
# 2. Sample size is visible, and can be made load-bearing
# --------------------------------------------------------------------------------


def test_the_same_point_estimate_at_two_sample_sizes_is_not_the_same_evidence():
    """Acceptance 2.  The whole reason rates stopped being storable.

    Before counts, both of these rows read ``sensitivity: 0.80`` and nothing in the
    planner could tell them apart.
    """
    large = _evidence(500, 400, 500, 50)
    small = _evidence(10, 8, 10, 1)

    assert large.sensitivity == small.sensitivity == 0.80

    large_lo, large_hi = large.sensitivity_interval
    small_lo, small_hi = small.sensitivity_interval
    assert (small_hi - small_lo) > 3 * (large_hi - large_lo)
    #: The ten-case study is consistent with a judge barely better than a coin flip.
    assert small_lo < 0.50 < large_lo


def test_counts_and_rates_cannot_disagree():
    """No field holds a rate, so no count can be contradicted by one."""
    fields = set(QualificationEvidence.__dataclass_fields__)
    assert not fields & {"sensitivity", "false_positive_rate", "observation_count"}
    assert {
        "positive_cases",
        "true_positives",
        "negative_cases",
        "false_positives",
    } <= fields

    with pytest.raises(ValueError):
        _evidence(10, 11, 10, 0)
    with pytest.raises(ValueError):
        _evidence(10, 5, 10, 11)


# --------------------------------------------------------------------------------
# 6. Conservative planning
# --------------------------------------------------------------------------------


def test_conservative_planning_can_demand_more_evidence(voice_early):
    """Acceptance 6, measured on the repository's own headline plan.

    The judge's 84-of-120 study is an ordinary size and still moves the answer from 7
    replications to 12 -- a 71% cost increase bought by nothing but declining to
    round the interval down to its midpoint.
    """
    request = voice_early.request("nightly")

    def selected(estimator):
        return plan(
            request.context,
            voice_early.failure_mode,
            replace(request.profile, estimator=estimator),
            voice_early.world,
        ).selected

    point = selected(Estimator.POINT)
    conservative = selected(Estimator.CONSERVATIVE)

    assert point.primary.replications == 7
    assert conservative.primary.replications == 12
    assert (
        conservative.economics.monetary_cost_per_window_usd
        > point.economics.monetary_cost_per_window_usd
    )
    #: Same source, same population, same price list.  Only the estimator moved.
    assert conservative.primary.source.ref == point.primary.source.ref
    assert conservative.primary.population == point.primary.population


def test_conservative_planning_is_free_when_the_study_is_large(clinical_factual):
    """The pressure falls on small studies specifically, not on caution generally.

    Scenario C's reconciliation check is qualified on 5,400 observations and its
    interval is tight enough that both estimators select the identical plan.  That is
    the property that makes the policy usable rather than merely expensive.
    """
    request = clinical_factual.request("production_guard")

    def selected(estimator):
        return plan(
            request.context,
            clinical_factual.failure_mode,
            replace(request.profile, estimator=estimator),
            clinical_factual.world,
        ).selected

    point = selected(Estimator.POINT)
    conservative = selected(Estimator.CONSERVATIVE)
    assert conservative is not None
    assert conservative.plan_id == point.plan_id
    assert conservative.economics == point.economics


def test_point_estimates_remain_the_default_everywhere(
    voice_early, duplex_silence, clinical_factual
):
    """Adding the field must not have silently repriced the repository."""
    for scenario in (voice_early, duplex_silence, clinical_factual):
        for request in scenario.requests:
            assert request.profile.estimator is Estimator.POINT


def test_a_deterministic_oracle_is_not_exempt_from_its_own_sample_size(duplex_silence):
    """The uncomfortable result, kept because it is uncomfortable.

    Scenario B's oracle reports sensitivity 1.0 and FPR 0.0 from 30 observations and
    the planner has always bought it at n=1 for $0.  The same row supports only
    [0.796, 1.0], which needs 7 runs, which does not fit the 600-second budget -- so
    under conservative planning the free certain oracle becomes inadmissible.

    Whether that is right is genuinely unclear.  A deterministic assertion's
    correctness is an argument about its code, not a sampling question, and a Wilson
    interval cannot distinguish "we only ran it 30 times" from "it is wrong a fifth of
    the time".  See docs/measurement_review.md.  The test exists so the behaviour is
    noticed here rather than discovered in production.
    """
    request = duplex_silence.request("verify")
    result = plan(
        request.context,
        duplex_silence.failure_mode,
        replace(request.profile, estimator=Estimator.CONSERVATIVE),
        duplex_silence.world,
    )
    assert result.selected is None

    oracle = duplex_silence.world.qualification[
        QualificationKey(
            SourceVersionRef("state_machine_assertion", "v2"),
            duplex_silence.failure_mode.ref,
            "focused_repro",
            duplex_silence.world.system_under_test.distribution_id,
        )
    ]
    assert oracle.sensitivity == 1.0
    assert oracle.sensitivity_interval[0] < 0.80


def test_conservative_never_asks_for_fewer_runs_than_point(voice_early):
    """Monotonicity of the policy, over a grid rather than one fixture."""
    for positive_cases in (10, 30, 120, 500):
        for rate in (0.6, 0.7, 0.8, 0.9):
            evidence = _evidence(
                positive_cases,
                round(rate * positive_cases),
                positive_cases,
                round(0.1 * positive_cases),
            )
            point = minimal_procedure(*evidence.planning_rates(Estimator.POINT), 0.05)
            cautious = minimal_procedure(
                *evidence.planning_rates(Estimator.CONSERVATIVE), 0.05
            )
            if point is None:
                continue
            assert cautious is None or cautious.replications >= point.replications


# --------------------------------------------------------------------------------
# The interval method itself
# --------------------------------------------------------------------------------


def test_wilson_does_not_claim_certainty_at_the_boundary():
    """Why Wilson and not the normal approximation.

    ``p +- z*sqrt(p(1-p)/n)`` has zero width at p=0 and p=1, so a 30-for-30 oracle
    would report a lower bound of exactly 1.0 and conservative planning would be
    indistinguishable from point planning for precisely the sources where the
    distinction bites hardest.
    """
    low, high = wilson_interval(30, 30)
    assert high == pytest.approx(1.0)
    assert 0.80 < low < 0.92

    low, high = wilson_interval(0, 30)
    assert low == pytest.approx(0.0)
    assert 0.08 < high < 0.13


def test_no_observations_means_no_information():
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_the_interval_narrows_monotonically_with_sample_size():
    widths = {
        trials: (lambda bounds: bounds[1] - bounds[0])(
            wilson_interval(int(0.8 * trials), trials)
        )
        for trials in (5, 20, 100, 1000)
    }
    assert sorted(widths, key=lambda n: widths[n], reverse=True) == [5, 20, 100, 1000]
    for trials, width in widths.items():
        low, high = wilson_interval(int(0.8 * trials), trials)
        assert low <= 0.8 <= high, trials
