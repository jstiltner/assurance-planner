"""Parts 6-9 and the rest of Part 15: the comparison, and what it is allowed to claim.

The tests that matter most here are the ones that could have gone the other way.  Three
of them nearly did:

* ``test_repetition_does_not_repair_a_systematically_wrong_judge`` -- if repetition had
  helped on that fixture, the whole premise of allocating effort by case behaviour would
  be unnecessary;
* ``test_triage_does_not_fire_on_the_well_behaved_judge`` -- a triage policy that
  escalates on a judge repetition already fixes is a policy that cries wolf;
* ``test_changing_only_the_prices_changes_the_preferred_policy`` -- if it did not, the
  cost model would be decoration.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from assurance_planner.benchmark import (
    allocation_diagnostic,
    compare,
    fit_beta_binomial,
    fit_by_reference_label,
    held_out_outcomes,
    leakage_report,
    marginal_value,
    matched_control,
    pareto_front,
    sample_size_warnings,
    score,
    slice_diagnostics,
)
from assurance_planner.characterization import characterize
from assurance_planner.loader import load_characterization
from assurance_planner.policies import (
    ALTERNATE,
    BLIND_PREFIX,
    HUMAN,
    Calibration,
    CaseOutcome,
    ConfidenceStop,
    CostModel,
    EarlyStopMajority,
    FixedN,
    HeterogeneityTriage,
    ProbeThenEscalate,
    UntargetedEscalation,
    default_policies,
    stratified_folds,
)

DATA = Path(__file__).resolve().parents[1] / "data"
COST = CostModel()


@pytest.fixture
def mixed():
    return load_characterization(DATA / "judge_runs_mixed.yaml")


@pytest.fixture
def noisy():
    return load_characterization(DATA / "judge_runs_noisy.yaml")


@pytest.fixture
def systematic():
    return load_characterization(DATA / "judge_runs_systematic.yaml")


@pytest.fixture
def small_sample():
    return load_characterization(DATA / "judge_runs_small_sample.yaml")


def _results(run, cost=COST):
    results, _ = compare(run, default_policies(), cost)
    return {r.policy: r for r in results}


# --------------------------------------------------------------------------------
# Part 6: metrics with explicit denominators
# --------------------------------------------------------------------------------


def test_abstention_is_not_folded_into_accuracy():
    """A policy that answers nothing must not score as a perfect one.

    This is the arithmetic that makes escalation look free if nobody checks it.
    """
    abstained = [
        CaseOutcome("A", "s", True, None, 3),
        CaseOutcome("B", "s", False, None, 3),
    ]
    result = score("abstain_always", abstained, COST)

    assert result.unresolved == 2
    assert result.false_negatives == 0.0
    assert result.sensitivity is None, "sensitivity over an empty denominator is not 1.0"
    assert result.sensitivity_interval_judge_only is None


def test_escalation_error_is_expected_not_observed():
    """Escalating to a declared-0.95 alternate costs 0.05 expected false negatives.

    Fractional error counts are the visible signal that part of this number was modelled
    rather than measured, because no alternate observations exist in any dataset here.
    """
    outcomes = [
        CaseOutcome("A", "s", True, None, 1, escalated_to=ALTERNATE),
        CaseOutcome("B", "s", False, None, 1, escalated_to=ALTERNATE),
    ]
    result = score("escalate_always", outcomes, COST)

    assert result.false_negatives == pytest.approx(1.0 - COST.alternate_sensitivity)
    assert result.false_positives == pytest.approx(COST.alternate_false_positive_rate)
    assert result.unresolved == 0, "an escalated case was answered by someone"
    assert result.escalations == 2
    #: No sample behind an escalated case, so no interval is offered for one.
    assert result.sensitivity_interval_judge_only is None


def test_human_escalation_is_treated_as_the_reference_label_and_says_so():
    """An assumption about the reference, not a measurement of humans.

    It is the most flattering assumption in the harness, so it is pinned where a reader
    will trip over it.
    """
    outcomes = [CaseOutcome("A", "s", True, None, 1, escalated_to=HUMAN)]
    result = score("human", outcomes, COST)

    assert result.false_negatives == 0.0
    assert result.human_reviews == 1
    assert result.cost_usd == pytest.approx(COST.judge_cost_usd + COST.human_cost_usd)


def test_the_two_time_figures_are_not_the_same_number():
    """Summed latency is not wall clock, and calling it that flatters fixed-N."""
    outcomes = [CaseOutcome(f"C{i}", "s", True, True, 8) for i in range(10)]
    serial = score("serial", outcomes, CostModel(judge_parallelism=1))
    parallel = score("parallel", outcomes, CostModel(judge_parallelism=4))

    assert serial.evaluator_seconds == parallel.evaluator_seconds
    assert parallel.wall_clock_seconds < serial.wall_clock_seconds
    assert serial.evaluator_seconds > serial.wall_clock_seconds


def test_p95_calls_is_reported_and_exceeds_the_mean_when_the_budget_varies(mixed):
    result = _results(mixed)["confidence_stop_8"]
    assert result.p95_calls >= result.mean_calls
    assert result.max_calls >= result.p95_calls


# --------------------------------------------------------------------------------
# Part 15: what repetition does and does not buy
# --------------------------------------------------------------------------------


def test_repetition_helps_the_noisy_judge(noisy):
    """The control. If the diagnostics cried wolf here they would be worthless.

    Compared at odd n only: at even n a tie is unresolved, so errors and abstentions
    trade against each other and the two are not comparable.
    """
    points = {p.observations: p for p in marginal_value(noisy, COST)}
    at_1 = points[1].false_negatives + points[1].false_positives
    at_5 = points[5].false_negatives + points[5].false_positives

    assert points[1].unresolved == points[5].unresolved == 0
    assert at_5 < at_1
    assert at_5 <= at_1 / 2


def test_repetition_does_not_repair_a_systematically_wrong_judge(systematic):
    """Seven false negatives at one observation, and seven at eight.

    This is the finding the whole pass is built on: the cases the judge is confidently
    wrong about are not noisy, so averaging cannot reach them. If this test ever went
    green by repetition improving, the candidate contribution would be unnecessary.
    """
    points = {p.observations: p for p in marginal_value(systematic, COST)}
    assert points[1].false_negatives == points[8].false_negatives == 7.0
    assert all(points[n].false_negatives == 7.0 for n in (3, 5, 7))


def test_escalation_beats_repetition_on_a_systematically_wrong_judge(systematic):
    """And it is the *only* thing that does.

    Every repetition-only policy is stuck at seven false negatives regardless of budget.
    Triage reaches the same cases by handing them to a different source.
    """
    results = _results(systematic)
    repetition_only = [
        results[name]
        for name in ("fixed_n_1", "fixed_n_3", "fixed_n_5", "fixed_n_8",
                     "early_stop_8", "confidence_stop_8")
    ]
    assert all(r.false_negatives == 7.0 for r in repetition_only)

    triage = results["heterogeneity_triage"]
    assert triage.escalations > 0
    assert triage.false_negatives < 1.0
    assert triage.false_negatives < min(r.false_negatives for r in repetition_only)


def test_triage_does_not_fire_on_the_well_behaved_judge(noisy):
    """The anti-cry-wolf control, and the one that makes the previous test mean anything.

    On a judge whose errors repetition actually fixes, triage must be indistinguishable
    from early stopping: no slice earns an escalate route, so it falls through.
    """
    results = _results(noisy)
    triage, early = results["heterogeneity_triage"], results["early_stop_8"]

    assert triage.escalations == 0
    assert triage.judge_calls == early.judge_calls
    assert triage.false_negatives == early.false_negatives
    assert triage.cost_usd == early.cost_usd


def test_the_marginal_value_of_repetition_collapses_on_the_benchmark(mixed):
    """Where the money stops buying anything.

    Twenty errors at one observation, sixteen at five, fifteen at six, and fifteen at
    every budget after that. The last three observations of the historical eight buy
    nothing at all and cost 136 extra calls. Reported as a table rather than a single
    'information gain' figure precisely so this flat tail stays visible instead of being
    averaged into a slope.
    """
    points = {p.observations: p for p in marginal_value(mixed, COST)}
    errors = {
        n: points[n].false_negatives + points[n].false_positives for n in points
    }
    assert errors[6] == errors[7] == errors[8]
    assert errors[1] > errors[5] > errors[6]
    #: Five observations to six removes one error; six to eight removes none.
    assert errors[5] - errors[6] == 1.0
    #: And the three that bought nothing were not free.
    assert points[8].judge_calls - points[5].judge_calls == 204


# --------------------------------------------------------------------------------
# Part 15: dominance and economics
# --------------------------------------------------------------------------------


def test_equal_assurance_at_lower_cost_dominates(mixed):
    """Early stopping gives fixed-N's answer for less money, so fixed-N is dominated.

    The dominance test is the only ranking this module performs, and it performs it on
    exactly the four axes a reader is trading off.
    """
    results = _results(mixed)
    early, fixed = results["early_stop_8"], results["fixed_n_8"]

    assert early.false_negatives == fixed.false_negatives
    assert early.false_positives == fixed.false_positives
    assert early.unresolved == fixed.unresolved
    assert early.cost_usd < fixed.cost_usd
    assert early.dominates(fixed)
    assert not fixed.dominates(early)
    assert "fixed_n_8" not in pareto_front(tuple(results.values()))


def test_a_policy_does_not_dominate_itself(mixed):
    result = _results(mixed)["early_stop_8"]
    assert not result.dominates(result)


def test_changing_only_the_prices_changes_the_preferred_policy(mixed):
    """The cost model has to be load-bearing or it is decoration.

    Nothing about the evaluator's measured behaviour changes between these two runs.
    The same observations, the same verdicts, the same errors -- only the price of an
    escalation. Under a cheap alternate, escalating is on the frontier; under an
    expensive one it is bought out of it.
    """
    cheap = CostModel(alternate_cost_usd=0.10)
    dear = CostModel(alternate_cost_usd=40.0)

    cheap_results, _ = compare(mixed, default_policies(), cheap)
    dear_results, _ = compare(mixed, default_policies(), dear)

    #: Identical error structure: the prices did not touch the measurement.
    for a, b in zip(cheap_results, dear_results):
        assert a.policy == b.policy
        assert a.false_negatives == b.false_negatives
        assert a.false_positives == b.false_positives
        assert a.judge_calls == b.judge_calls

    def cheapest_within(results, error_budget: float) -> str:
        affordable = [
            r
            for r in results
            if r.false_negatives + r.false_positives <= error_budget
        ]
        return min(affordable, key=lambda r: r.cost_usd).policy

    #: Note this is *not* the Pareto front, which barely moves: a policy with the
    #: lowest error on some axis stays non-dominated at any price. The decision that
    #: actually moves is "cheapest way to hit an error budget", and it moves entirely.
    assert cheapest_within(cheap_results, 15.0) == "probe_2_escalate_alternate"
    assert cheapest_within(dear_results, 15.0) == "confidence_stop_8"


def test_the_qualification_counts_do_not_move_when_the_prices_do(mixed):
    """Measurement and economics are separate layers, and this is the seam.

    The four counts the planner reads come from the study. No cost model appears
    anywhere in their derivation, so a price change cannot launder itself into a
    sensitivity claim.
    """
    before = characterize(mixed, 0.05).qualification_counts()
    compare(mixed, default_policies(), CostModel(judge_cost_usd=99.0))
    after = characterize(mixed, 0.05).qualification_counts()
    assert before == after


# --------------------------------------------------------------------------------
# Part 8: is the improvement allocation, or easy cases?
# --------------------------------------------------------------------------------


def test_the_diagnostic_separates_contested_cases_from_easy_ones(mixed):
    folds = stratified_folds(mixed, k=5)
    row = allocation_diagnostic(mixed, EarlyStopMajority(8), COST, folds)

    assert row.uncontested_cases + row.contested_cases == len(mixed.cases)
    assert row.contested_cases > 0
    #: Uncontested cases are cheap by construction: early stopping locks a majority
    #: after the win threshold is reached and never wavers.
    assert row.uncontested_calls / row.uncontested_cases < (
        row.contested_calls / row.contested_cases
    )


def test_triage_earns_its_advantage_on_the_contested_cases_too(mixed):
    """The question red-team item 4 exists to ask, answered on the benchmark.

    If triage's advantage lived entirely in the uncontested column it would be doing
    nothing that early stopping does not already do. It does not: the contested-column
    error falls as well, and that is where escalation is actually being spent.
    """
    folds = stratified_folds(mixed, k=5)
    triage = allocation_diagnostic(mixed, HeterogeneityTriage(), COST, folds)
    early = allocation_diagnostic(mixed, EarlyStopMajority(8), COST, folds)

    assert triage.contested_errors < early.contested_errors
    assert triage.contested_escalations > 0


@pytest.mark.parametrize("fixture", ["mixed", "systematic", "noisy"])
def test_disagreement_triggered_escalation_targets_the_wrong_cases(fixture, request):
    """Red-team item 5, and it came out the opposite way to how it was first written.

    The first version of this test asserted that a two-observation probe "captures much
    of what triage captures", because escalation is the strongest lever and the probe
    escalates. It does not. Measured against early stopping it gains 0.25 errors on the
    mixed fixture and *loses* 0.15 and 2.50 on the other two.

    The mechanism is the point. ``probe_2`` escalates when two observations disagree, so
    it selects the *noisy* cases -- exactly the ones a majority of eight already
    resolves -- and it can never select a confidently-wrong case, because those are
    unanimous by definition. It pays for a second opinion on cases that did not need one
    and skips the ones that did. Escalating is not the same as escalating the right
    cases, and disagreement is the wrong trigger for finding them.
    """
    results = _results(request.getfixturevalue(fixture))
    probe, early = results["probe_2_escalate_alternate"], results["early_stop_8"]
    probe_errors = probe.false_negatives + probe.false_positives
    early_errors = early.false_negatives + early.false_positives

    assert probe.escalations > 0
    assert probe_errors > early_errors - 0.5, (
        "a probe that escalates on disagreement does not meaningfully beat plain early "
        "stopping; if this ever fails, the claim in the findings doc must be rewritten"
    )


def test_triage_beats_the_probe_it_is_most_often_compared_to(mixed, systematic):
    """The comparison from kill criterion 2, on the fixtures where slices carry signal."""
    for run in (mixed, systematic):
        results = _results(run)
        triage, probe = (
            results["heterogeneity_triage"],
            results["probe_2_escalate_alternate"],
        )
        assert (
            triage.false_negatives + triage.false_positives
            < probe.false_negatives + probe.false_positives
        )


# --------------------------------------------------------------------------------
# Kill criterion 7: is the *targeting* worth anything, or just the escalating?
# --------------------------------------------------------------------------------


def _blind(results):
    return next(r for r in results.values() if r.policy.startswith(BLIND_PREFIX))


def test_the_blind_control_cannot_be_left_out_of_a_comparison(mixed):
    """It is appended by ``compare`` itself, not by a caller who remembered to.

    A control that has to be requested is a control that will be quietly dropped the
    first time it embarrasses the policy it is controlling.
    """
    results = _results(mixed)
    control = _blind(results)
    targeted = max(
        r.escalations for r in results.values() if not r.policy.startswith(BLIND_PREFIX)
    )
    assert control.escalations > 0
    #: Sized to the most escalation-heavy real policy, and not exactly equal to it --
    #: a hash-selected subset of a fold is close to the target rate, not on it.
    assert control.escalations == pytest.approx(targeted, abs=3)


def test_sizing_the_control_is_idempotent(mixed):
    """Re-deriving a control from results that already contain one must not ratchet.

    The first version did: the control escalated more than the policy it was controlling,
    so re-deriving it produced a larger control, and the CLI and the report disagreed
    about which rate they were reporting.
    """
    results, _ = compare(mixed, default_policies(), COST)
    assert matched_control(results, len(mixed.cases)) == matched_control(
        tuple(r for r in results if not r.policy.startswith(BLIND_PREFIX)),
        len(mixed.cases),
    )
    #: Nothing escalated, so there is nothing to control; the early-stopping baseline is
    #: already in the table under its own name.
    assert matched_control((), len(mixed.cases)) is None


def test_the_control_selection_ignores_everything_about_the_case(mixed):
    """It keys on a hash of the id, so it provably did not consult the evidence."""
    control = UntargetedEscalation(rate=0.5)
    chosen = {case.case_id: control.selects(case.case_id) for case in mixed.cases}

    assert all(control.selects(cid) is picked for cid, picked in chosen.items())
    #: And it does not select whole slices, which would make it a triage policy wearing
    #: a control's name.
    by_slice: dict[str, set] = {}
    for case in mixed.cases:
        by_slice.setdefault(case.slice_id, set()).add(chosen[case.case_id])
    assert all(len(values) == 2 for values in by_slice.values())


@pytest.mark.parametrize("fixture", ["mixed", "systematic"])
def test_targeting_beats_blind_escalation_where_the_slices_mean_something(
    fixture, request
):
    """The result that keeps candidate E alive, on the two fixtures where it should.

    Triage escalates *fewer* cases than the size-matched blind control, makes fewer
    errors doing it, and spends less money. That is the whole of what the candidate
    contribution claims: failure-slice behaviour tells you which cases are worth a
    second opinion.
    """
    results = _results(request.getfixturevalue(fixture))
    triage = results["heterogeneity_triage"]
    control = _blind(results)

    assert (
        triage.false_negatives + triage.false_positives
        < control.false_negatives + control.false_positives
    )
    assert triage.escalations < control.escalations
    assert triage.cost_usd < control.cost_usd


def test_blind_escalation_beats_triage_on_the_well_behaved_judge(noisy):
    """The unflattering half, and the more informative one.

    On a judge whose errors are unbiased noise, triage correctly declines to escalate --
    and is then *dominated* by a control that escalates an arbitrary fifth of the
    population, because the declared alternate (0.95/0.05) is simply better than the
    judge (0.672/0.087). Nothing about heterogeneity is being rewarded there. The
    alternate's price is buying accuracy directly.

    This is the finding that most threatens the design, so it is pinned rather than
    described: whenever the alternate source is that much better than the primary, the
    optimal policy is to stop using the primary, and no planner is needed to work that
    out. The real study has to establish the alternate's true rates before any of these
    comparisons mean anything.
    """
    results = _results(noisy)
    triage = results["heterogeneity_triage"]
    control = _blind(results)

    assert triage.escalations == 0
    assert (
        control.false_negatives + control.false_positives
        < triage.false_negatives + triage.false_positives
    )
    assert control.cost_usd > triage.cost_usd
    assert "heterogeneity_triage" not in pareto_front(tuple(results.values()))


# --------------------------------------------------------------------------------
# Part 10: the pooled rate describes nothing
# --------------------------------------------------------------------------------


def test_the_pooled_sensitivity_describes_no_slice_in_the_mixed_population(mixed):
    """The property the benchmark fixture exists to have.

    Pooled sensitivity sits in the middle of a population where one slice is nearly
    always right and another is wrong more often than not. Planning from the pooled
    number allocates the same effort to both.
    """
    analysis = characterize(mixed, 0.05)
    pooled = analysis.sensitivity.point
    rows = {row.slice_id: row for row in slice_diagnostics(mixed)}

    agreement = {
        slice_id: row.majority_agrees / row.cases for slice_id, row in rows.items()
    }
    assert agreement["explicit-restatement"] > 0.9
    assert agreement["verbatim-readback"] < 0.6
    #: No slice's agreement rate is anywhere near the pooled rate it was averaged into.
    assert all(abs(rate - pooled) > 0.05 for rate in agreement.values())


def test_all_three_regimes_coexist_in_the_mixed_population(mixed):
    rows = {row.slice_id: row for row in slice_diagnostics(mixed)}

    #: Stable and correct.
    assert rows["explicit-restatement"].contested < rows["explicit-restatement"].cases / 2
    #: Noisy but informative.
    assert rows["implicit-correction"].mean_disagreement > 0.25
    #: Stable and wrong.
    assert rows["verbatim-readback"].unanimous_and_wrong > 0
    #: Barely measured.
    assert rows["escalation-handoff"].mean_repetitions == 2.0


def test_the_slices_do_not_identify_the_wrong_cases_exactly(mixed):
    """Deliberate: a fixture where ``slice_id`` were a lookup table for the answer key
    would let a triage policy win by construction and would prove nothing."""
    rows = {row.slice_id: row for row in slice_diagnostics(mixed)}
    bad = rows["verbatim-readback"]

    assert 0 < bad.unanimous_and_wrong < bad.cases
    assert bad.majority_agrees > 0, "the bad slice still contains correctly-judged cases"


# --------------------------------------------------------------------------------
# Part 3: the leakage report is computed, not asserted
# --------------------------------------------------------------------------------


def test_the_leakage_report_is_clean_on_the_benchmark(mixed):
    folds = stratified_folds(mixed, k=5)
    report = leakage_report(folds, mixed)

    assert report.clean
    assert report.overlapping_case_ids == ()
    assert report.untested_case_ids == ()
    assert report.folds == 5
    #: Not leakage, but the other way a held-out number can be meaningless.
    assert "escalation-handoff" in report.thin_calibration_slices


def test_the_leakage_report_would_catch_a_contaminated_fold(mixed):
    """A guard nobody has tested against a positive case is not a guard."""
    folds = stratified_folds(mixed, k=5)
    contaminated = type(folds[0])(
        index=0, calibration=mixed, held_out=folds[0].held_out
    )
    report = leakage_report((contaminated,), mixed)

    assert not report.clean
    assert report.overlapping_case_ids


def test_scoring_a_contaminated_fold_raises_rather_than_reporting(mixed):
    folds = stratified_folds(mixed, k=5)
    contaminated = type(folds[0])(
        index=0, calibration=mixed, held_out=folds[0].held_out
    )
    with pytest.raises(AssertionError, match="both the calibration and held-out"):
        held_out_outcomes(mixed, HeterogeneityTriage(), (contaminated,))


# --------------------------------------------------------------------------------
# Part 9: the statistical comparator, including where it fails
# --------------------------------------------------------------------------------


def test_the_beta_binomial_separates_the_two_judges_by_correlation(noisy, systematic):
    """What the fit is actually good for, and it is not much more than this.

    The intra-case correlation is high on the judge that is confidently wrong and low on
    the one that is merely noisy -- the same signal the Pearson dispersion statistic
    already reports more cheaply. That is the answer to 'does the model justify its
    complexity': on this data, no. It is a second opinion.
    """
    noisy_fit = fit_beta_binomial(
        tuple(c for c in noisy.cases if c.reference_label)
    )
    systematic_fit = fit_beta_binomial(
        tuple(c for c in systematic.cases if c.reference_label)
    )

    assert noisy_fit.intraclass_correlation < 0.2
    assert systematic_fit.intraclass_correlation > 0.6
    #: And the pooled means are close enough to be useless for telling them apart.
    assert abs(noisy_fit.mean - systematic_fit.mean) < 0.05


def test_the_unanimity_check_fails_to_detect_the_mixed_population(mixed):
    """A recorded negative result, kept because it was a real prediction that was wrong.

    ``fit_quality`` was built expecting a single Beta-Binomial to visibly misfit a
    deliberately mixed population. It does not: the ratio sits near 1 on the adversarial
    fixture just as it does on the well-behaved one. The check is retained so a reader
    can see it was tried, not as evidence that the population is homogeneous.
    """
    for fit in fit_by_reference_label(mixed):
        assert fit.reproduces_unanimity
        assert 0.8 <= fit.fit_quality <= 1.25


def test_the_fit_refuses_rather_than_reporting_a_negative_shape(small_sample):
    """One observation per case: no within-case spread exists to fit."""
    positives, negatives = fit_by_reference_label(small_sample)
    assert positives.alpha is None
    assert negatives.alpha is None
    assert positives.fit_quality is None


def test_the_fit_is_pooled_over_labels_only_if_someone_asks_for_it(mixed):
    """Pooling the labels makes the Beta absorb the labels instead of the judge.

    The pooled fit is bimodal by construction -- positives sit high, negatives sit low --
    so its mean lands near 0.5 and means nothing. Pinned so that nobody reintroduces the
    pooled call as a convenience.
    """
    pooled = fit_beta_binomial(mixed.cases)
    positives, negatives = fit_by_reference_label(mixed)

    assert 0.45 < pooled.mean < 0.55
    assert positives.mean > pooled.mean > negatives.mean


# --------------------------------------------------------------------------------
# Sample-size honesty
# --------------------------------------------------------------------------------


def test_a_pilot_sized_dataset_is_warned_about(small_sample):
    warnings = sample_size_warnings(small_sample)
    joined = " ".join(warnings)

    assert warnings
    assert "40-case floor" in joined
    assert "observations per case" in joined


def test_the_benchmark_fixture_is_not_warned_about(mixed):
    """The warning has to be able to stay silent, or it means nothing when it fires."""
    assert sample_size_warnings(mixed) == ()


def test_truncated_cases_are_reported_rather_than_hidden(mixed):
    """Eight cases recorded two observations. A policy that wanted eight got two.

    Not an error -- it is what a fixed-N policy does on a sparsely sampled slice -- but
    the result is answering a slightly different question and the report says so.
    """
    results = _results(mixed)
    assert results["fixed_n_8"].truncated_cases == 8
    assert results["fixed_n_1"].truncated_cases == 0
