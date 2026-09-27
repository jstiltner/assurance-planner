"""Scoring the policies against each other on recorded observations.

This module answers one question and refuses to compress it into one number:

    at equal assurance, which evaluation policy costs least -- and is the saving
    real allocation, or just cheaper handling of cases that were never hard?

Four decisions here are load-bearing and are easy to get quietly wrong.

**Errors are counted against explicit denominators.**  A policy that abstains or
escalates has not answered, and folding non-answers into an accuracy figure makes
abstention look like success.  ``PolicyResult`` therefore carries the reference
positive and negative totals, the unresolved count and the escalation count
separately, and the rate properties state which denominator they used.

**Escalation error is expectation, not observation.**  No fixture contains
alternate-evaluator observations, so a case handed to the alternate contributes
``1 - alternate_sensitivity`` expected false negatives rather than a measured
outcome.  That makes error counts fractional, which is the point: it is visibly not
a count of things that happened.  Confidence intervals are computed over the
judge-decided cases only, because those are the only ones with a sample behind them.

**Two time figures, never one.**  Total evaluator seconds is what the evaluator
fleet is occupied for.  Wall clock is the slowest single case's critical path, on
the assumption that cases run concurrently.  The truth is between them and depends
on infrastructure this package knows nothing about, so both bounds are reported and
neither is labelled "the latency".

**The benchmark scores policies on cases their calibration never saw.**  Every
policy is replayed through ``stratified_folds``; the union of the held-out folds is
the whole population, so the numbers cover every case, but each case was decided by
a policy calibrated without it.  ``leakage_report`` re-derives the disjointness
rather than asserting it in a comment.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from statistics import fmean

from .characterization import CaseRun, CharacterizationRun
from .policies import (
    ALTERNATE,
    BLIND_PREFIX,
    HUMAN,
    Calibration,
    CaseOutcome,
    CostModel,
    FixedN,
    Fold,
    UntargetedEscalation,
    stratified_folds,
)
from .statistics import wilson_interval

#: Below this many cases a held-out comparison is theatre.  Not a hard error -- the
#: pilot fixture is deliberately smaller -- but every report says so out loud.
MIN_CASES_FOR_COMPARISON = 40

#: Below this many recorded repetitions per case, policies that want to spend eight
#: calls cannot be distinguished from policies that want to spend three.
MIN_REPETITIONS_FOR_COMPARISON = 5


# --------------------------------------------------------------------------------
# Per-policy results
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PolicyResult:
    """What one policy cost and what it got wrong.

    Error fields are floats because escalation contributes expected error.  See the
    module docstring; a fractional false-negative count is a deliberate signal that
    part of this number was modelled rather than observed.
    """

    policy: str
    cases: int
    reference_positives: int
    reference_negatives: int

    false_negatives: float
    false_positives: float
    #: Verdict withheld and *not* escalated: nobody answered.
    unresolved: int
    #: Handed to another source.  Counted separately because it is a real cost and a
    #: real operational burden, not a free way to avoid being wrong.
    escalations: int
    human_reviews: int

    judge_calls: int
    mean_calls: float
    p95_calls: float
    max_calls: int
    #: Cases where the policy wanted more repetitions than the study recorded.
    truncated_cases: int

    cost_usd: float
    evaluator_seconds: float
    wall_clock_seconds: float

    #: Judge-decided cases only, for intervals.  Escalated and unresolved cases are
    #: excluded because no sample exists for them.
    judge_positives: int
    judge_true_positives: int
    judge_negatives: int
    judge_false_positives: int

    @property
    def answered_positives(self) -> float:
        """Reference positives the policy took responsibility for."""
        return self.reference_positives - self._unresolved_positives

    @property
    def sensitivity(self) -> float | None:
        """Over reference positives that were answered by someone.

        ``None`` when nothing was answered, rather than 0.0, because "answered
        nothing" and "answered everything wrongly" are different failures.
        """
        answered = self.answered_positives
        if answered <= 0:
            return None
        return 1.0 - self.false_negatives / answered

    @property
    def specificity(self) -> float | None:
        answered = self.reference_negatives - self._unresolved_negatives
        if answered <= 0:
            return None
        return 1.0 - self.false_positives / answered

    @property
    def sensitivity_interval_judge_only(self) -> tuple[float, float] | None:
        if self.judge_positives == 0:
            return None
        return wilson_interval(self.judge_true_positives, self.judge_positives)

    @property
    def specificity_interval_judge_only(self) -> tuple[float, float] | None:
        if self.judge_negatives == 0:
            return None
        return wilson_interval(
            self.judge_negatives - self.judge_false_positives, self.judge_negatives
        )

    #: Filled in by the scorer; split out so the rate properties above can subtract it.
    _unresolved_positives: int = 0
    _unresolved_negatives: int = 0

    def dominates(self, other: "PolicyResult") -> bool:
        """Weakly better on every axis and strictly better on at least one.

        The axes are the four things a reader is actually trading off: missed
        failures, false alarms, cases nobody answered, and money.  Latency is left
        out deliberately -- with two defensible time figures, including either one
        here would silently pick a parallelism assumption.
        """
        mine = (
            self.false_negatives,
            self.false_positives,
            float(self.unresolved),
            self.cost_usd,
        )
        theirs = (
            other.false_negatives,
            other.false_positives,
            float(other.unresolved),
            other.cost_usd,
        )
        return all(a <= b for a, b in zip(mine, theirs)) and mine != theirs


def _percentile(values: list[int], fraction: float) -> float:
    """Nearest-rank percentile.  No interpolation: call counts are integers."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, ceil(fraction * len(ordered)) - 1))
    return float(ordered[index])


def _case_wall_clock(outcome: CaseOutcome, cost: CostModel) -> float:
    batches = ceil(outcome.judge_calls / max(1, cost.judge_parallelism))
    elapsed = batches * cost.judge_latency_seconds
    if outcome.escalated:
        elapsed += cost.escalation_latency(outcome.escalated_to)
    return elapsed


def score(
    policy_name: str, outcomes: list[CaseOutcome], cost: CostModel
) -> PolicyResult:
    """Turn per-case outcomes into one row of the comparison table."""
    positives = [o for o in outcomes if o.reference_label]
    negatives = [o for o in outcomes if not o.reference_label]

    false_negatives = 0.0
    false_positives = 0.0
    unresolved_positives = unresolved_negatives = 0
    escalations = human_reviews = 0
    judge_positives = judge_true_positives = 0
    judge_negatives = judge_false_positives = 0
    escalation_cost = 0.0

    for outcome in outcomes:
        if outcome.escalated:
            escalations += 1
            escalation_cost += cost.escalation_cost(outcome.escalated_to)
            if outcome.escalated_to == HUMAN:
                human_reviews += 1
                #: Human adjudication *is* the reference label, by construction.  That
                #: is an assumption about the reference, not a measurement of humans.
                continue
            if outcome.reference_label:
                false_negatives += 1.0 - cost.alternate_sensitivity
            else:
                false_positives += cost.alternate_false_positive_rate
            continue

        if outcome.verdict is None:
            if outcome.reference_label:
                unresolved_positives += 1
            else:
                unresolved_negatives += 1
            continue

        if outcome.reference_label:
            judge_positives += 1
            if outcome.verdict:
                judge_true_positives += 1
            else:
                false_negatives += 1.0
        else:
            judge_negatives += 1
            if outcome.verdict:
                judge_false_positives += 1
                false_positives += 1.0

    calls = [o.judge_calls for o in outcomes]
    total_calls = sum(calls)

    return PolicyResult(
        policy=policy_name,
        cases=len(outcomes),
        reference_positives=len(positives),
        reference_negatives=len(negatives),
        false_negatives=false_negatives,
        false_positives=false_positives,
        unresolved=unresolved_positives + unresolved_negatives,
        escalations=escalations,
        human_reviews=human_reviews,
        judge_calls=total_calls,
        mean_calls=fmean(calls) if calls else 0.0,
        p95_calls=_percentile(calls, 0.95),
        max_calls=max(calls) if calls else 0,
        truncated_cases=sum(1 for o in outcomes if o.truncated),
        cost_usd=total_calls * cost.judge_cost_usd + escalation_cost,
        evaluator_seconds=total_calls * cost.judge_latency_seconds
        + sum(
            cost.escalation_latency(o.escalated_to) for o in outcomes if o.escalated
        ),
        wall_clock_seconds=max(
            (_case_wall_clock(o, cost) for o in outcomes), default=0.0
        ),
        judge_positives=judge_positives,
        judge_true_positives=judge_true_positives,
        judge_negatives=judge_negatives,
        judge_false_positives=judge_false_positives,
        _unresolved_positives=unresolved_positives,
        _unresolved_negatives=unresolved_negatives,
    )


# --------------------------------------------------------------------------------
# Held-out evaluation
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LeakageReport:
    """Evidence that the comparison was not run on its own calibration data."""

    folds: int
    #: Case ids that appeared in both a fold's calibration set and its held-out set.
    #: Must be empty.  Recomputed from the folds rather than trusted.
    overlapping_case_ids: tuple[str, ...]
    #: Cases never held out by any fold, and so never actually tested.
    untested_case_ids: tuple[str, ...]
    #: Slices whose calibration fold was too thin to support triage.  Not leakage,
    #: but it is the other way a held-out result can be meaningless.
    thin_calibration_slices: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not self.overlapping_case_ids and not self.untested_case_ids


def leakage_report(folds: tuple[Fold, ...], run: CharacterizationRun) -> LeakageReport:
    overlaps: list[str] = []
    tested: set[str] = set()
    thin: set[str] = set()
    for fold in folds:
        held = {c.case_id for c in fold.held_out.cases}
        calibrated = {c.case_id for c in fold.calibration.cases}
        overlaps.extend(sorted(held & calibrated))
        tested |= held
        profiles = Calibration.from_run(fold.calibration).slices
        thin |= {s for s, p in profiles.items() if p.is_thin}
    return LeakageReport(
        folds=len(folds),
        overlapping_case_ids=tuple(overlaps),
        untested_case_ids=tuple(
            sorted(c.case_id for c in run.cases if c.case_id not in tested)
        ),
        thin_calibration_slices=tuple(sorted(thin)),
    )


def held_out_outcomes(
    run: CharacterizationRun, policy, folds: tuple[Fold, ...]
) -> list[CaseOutcome]:
    """Replay ``policy`` over every case, calibrated only on the other folds."""
    outcomes: list[CaseOutcome] = []
    for fold in folds:
        calibration = Calibration.from_run(fold.calibration)
        for case in fold.held_out.cases:
            if case.case_id in calibration.source_case_ids:
                raise AssertionError(
                    f"case '{case.case_id}' is in both the calibration and held-out "
                    f"set of fold {fold.index}; the comparison would be scoring the "
                    f"policy on data it was tuned on"
                )
            outcomes.append(policy.decide(case, calibration))
    return outcomes


def compare(
    run: CharacterizationRun,
    policies,
    cost: CostModel,
    k: int = 5,
) -> tuple[tuple[PolicyResult, ...], LeakageReport]:
    """Score every policy on cases its calibration never saw, plus the blind control.

    The blind escalation control is appended here rather than passed in, because it is
    the comparison that the candidate contribution is most likely to fail and there must
    be no way to run the benchmark without it.  Its size depends on the results, so it
    cannot be known before scoring; it is scored in a second pass over the same folds.
    """
    folds = stratified_folds(run, k=k)
    report = leakage_report(folds, run)
    results = tuple(
        score(policy.name, held_out_outcomes(run, policy, folds), cost)
        for policy in policies
    )
    control = matched_control(results, len(run.cases))
    if control is not None:
        results += (
            score(control.name, held_out_outcomes(run, control, folds), cost),
        )
    return results, report


def matched_control(
    results: tuple[PolicyResult, ...], cases: int, n_max: int = 8
) -> UntargetedEscalation | None:
    """A blind escalation control sized to the most escalation-heavy policy scored.

    Kill criterion 7 of the experiment protocol says: if escalating the same number of
    cases chosen arbitrarily does as well as escalating the cases the slice profile
    picked out, then the targeting is worth nothing and the slice machinery should go.

    Returns ``None`` when nothing escalated, because a zero-rate control is the
    early-stopping baseline that is already in the table under its own name.  Results
    from a previous control are ignored, so calling this on results that already include
    one gives the same answer -- otherwise a control would ratchet its own size upward.
    """
    if not cases:
        return None
    target = max(
        (r.escalations for r in results if not r.policy.startswith(BLIND_PREFIX)),
        default=0,
    )
    if target == 0:
        return None
    return UntargetedEscalation(n_max=n_max, rate=target / cases)


def pareto_front(results: tuple[PolicyResult, ...]) -> tuple[str, ...]:
    """Policies no other policy weakly beats on errors, abstentions and money."""
    return tuple(
        r.policy
        for r in results
        if not any(other.dominates(r) for other in results if other is not r)
    )


# --------------------------------------------------------------------------------
# Part 7: where the marginal value of repetition collapses
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MarginalPoint:
    observations: int
    cases_scored: int
    false_negatives: float
    false_positives: float
    unresolved: int
    judge_calls: int
    #: Errors avoided relative to ``observations - 1``.  Negative means the extra
    #: observation made things worse, which happens and is not a bug: one more vote
    #: can break a majority that happened to be right.
    errors_avoided: float
    incremental_calls: int


def marginal_value(
    run: CharacterizationRun, cost: CostModel, n_max: int = 8
) -> tuple[MarginalPoint, ...]:
    """Majority-vote performance at 1, 2, ... n_max observations.

    Deliberately reported as a table of the raw quantities rather than a single
    "information gain" figure.  The even-numbered rows are not noise: at even n a tie
    is unresolved, so errors fall and abstentions rise, and a scalar summary would
    average that structure away.
    """
    points: list[MarginalPoint] = []
    previous_errors: float | None = None
    previous_calls = 0
    for n in range(1, n_max + 1):
        result = score(
            f"fixed_n_{n}",
            [FixedN(n).decide(case, Calibration()) for case in run.cases],
            cost,
        )
        errors = result.false_negatives + result.false_positives
        points.append(
            MarginalPoint(
                observations=n,
                cases_scored=result.cases,
                false_negatives=result.false_negatives,
                false_positives=result.false_positives,
                unresolved=result.unresolved,
                judge_calls=result.judge_calls,
                errors_avoided=(
                    0.0 if previous_errors is None else previous_errors - errors
                ),
                incremental_calls=result.judge_calls - previous_calls,
            )
        )
        previous_errors = errors
        previous_calls = result.judge_calls
    return tuple(points)


# --------------------------------------------------------------------------------
# Part 8: is the saving allocation, or just easy cases?
# --------------------------------------------------------------------------------


def _contested(case: CaseRun) -> bool:
    """The judge disagreed with itself at least once on this case."""
    return case.runs >= 2 and 0 < case.flags < case.runs


@dataclass(frozen=True, slots=True)
class AllocationDiagnostic:
    """The answer to "is this real triage, or cheap handling of easy cases?".

    A policy that only saves money on cases where the judge never wavered has not
    allocated anything; it has noticed that unanimous cases are unanimous, which
    ``EarlyStopMajority`` already does.  The interesting column is the contested one.
    """

    policy: str
    uncontested_cases: int
    uncontested_calls: int
    uncontested_errors: float
    contested_cases: int
    contested_calls: int
    contested_errors: float
    contested_escalations: int


def allocation_diagnostic(
    run: CharacterizationRun,
    policy,
    cost: CostModel,
    folds: tuple[Fold, ...],
) -> AllocationDiagnostic:
    contested = {c.case_id for c in run.cases if _contested(c)}
    outcomes = held_out_outcomes(run, policy, folds)
    hot = [o for o in outcomes if o.case_id in contested]
    cold = [o for o in outcomes if o.case_id not in contested]
    hot_result = score(policy.name, hot, cost)
    cold_result = score(policy.name, cold, cost)
    return AllocationDiagnostic(
        policy=policy.name,
        uncontested_cases=len(cold),
        uncontested_calls=cold_result.judge_calls,
        uncontested_errors=cold_result.false_negatives + cold_result.false_positives,
        contested_cases=len(hot),
        contested_calls=hot_result.judge_calls,
        contested_errors=hot_result.false_negatives + hot_result.false_positives,
        contested_escalations=hot_result.escalations,
    )


@dataclass(frozen=True, slots=True)
class SliceDiagnostic:
    slice_id: str
    cases: int
    mean_repetitions: float
    mean_disagreement: float
    majority_agrees: int
    contested: int
    unanimous_and_wrong: int


def slice_diagnostics(run: CharacterizationRun) -> tuple[SliceDiagnostic, ...]:
    """Per-slice heterogeneity, which the pooled rates cannot show."""
    rows = []
    for slice_id in run.slices:
        cases = run.in_slice(slice_id)
        rows.append(
            SliceDiagnostic(
                slice_id=slice_id,
                cases=len(cases),
                mean_repetitions=fmean(c.runs for c in cases),
                mean_disagreement=fmean(c.disagreement_rate for c in cases),
                majority_agrees=sum(
                    1 for c in cases if c.majority_agrees_with_reference
                ),
                contested=sum(1 for c in cases if _contested(c)),
                unanimous_and_wrong=sum(
                    1
                    for c in cases
                    if not _contested(c) and not c.majority_agrees_with_reference
                ),
            )
        )
    return tuple(rows)


# --------------------------------------------------------------------------------
# Part 9: the established statistical comparator
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BetaBinomialFit:
    """A Beta-Binomial fitted to per-case flag counts by method of moments.

    Chosen over mixed-effects logistic regression, item-response models and
    hierarchical Bayes for one reason: it is the smallest model that can express the
    thing the whole project is arguing about -- that per-case flag rates vary, so the
    pooled rate is not any case's rate -- and it fits in closed form, with no
    optimiser, no sampler, no scipy, and no randomness.  The alternatives need an
    optimiser (mixed-effects), more data per case than 8 observations (IRT), or
    sampling (hierarchical Bayes), and none of them buys a different conclusion at
    this sample size.

    It is a *comparator*, not a component.  Nothing in the planner reads it.

    **Recorded negative result.**  ``fit_quality`` was built on the expectation that a
    single Beta-Binomial would visibly misfit a mixture of stable-correct, noisy and
    stable-wrong cases, and so would flag the adversarial fixture.  It does not.  Fit
    against the unanimity rate lands between 0.83 and 1.22 on every fixture in
    ``data/``, including the one constructed specifically to be a mixture.  The check
    is kept because a reader is entitled to see that it was run and did not work; it
    is not evidence that any of these populations is homogeneous.

    What the fit *does* separate is ``intraclass_correlation``: ~0.10 on the
    well-behaved judge against 0.36-0.83 on the systematically wrong one.  That is the
    same signal the Pearson dispersion statistic already reports by a cheaper route,
    which is the answer to "does the statistical model justify its complexity": on this
    data, no.  It is a second opinion, not a new dependency.

    Neither statistic can see the thing that actually matters.  Both are computed from
    flag rates alone, and a case the judge is unanimously *wrong* about is
    indistinguishable from one it is unanimously right about until the reference label
    is consulted.  No amount of model sophistication recovers that at run time.
    """

    cases: int
    #: None when the moments do not admit a Beta: observed spread at or below what
    #: independent Bernoulli trials would give.  Refusing beats reporting a negative
    #: shape parameter.
    alpha: float | None
    beta: float | None
    mean: float
    #: Beta-Binomial intra-case correlation, 1/(alpha+beta+1).  Comparable to the ICC
    #: the dispersion statistic reports, by a different route.
    intraclass_correlation: float | None
    #: Cases the judge was unanimous on, observed vs predicted by the fit.
    unanimous_observed: int
    unanimous_predicted: float

    @property
    def fit_quality(self) -> float | None:
        """Predicted unanimous cases over observed.  1.0 is perfect.

        See the class docstring: this discriminates nothing on the fixtures in
        ``data/``.  Read it as a sanity check on the arithmetic, not as a mixture test.
        """
        if self.unanimous_observed == 0:
            return None
        return self.unanimous_predicted / self.unanimous_observed

    @property
    def reproduces_unanimity(self) -> bool:
        """The fit gets the all-or-nothing rate roughly right.  Weak; see above."""
        quality = self.fit_quality
        return self.alpha is not None and quality is not None and 0.8 <= quality <= 1.25


def _beta_binomial_unanimous_probability(
    alpha: float, beta: float, runs: int
) -> float:
    """P(all flags) + P(no flags) under Beta-Binomial(runs, alpha, beta)."""
    all_flags = 1.0
    none_flags = 1.0
    for i in range(runs):
        all_flags *= (alpha + i) / (alpha + beta + i)
        none_flags *= (beta + i) / (alpha + beta + i)
    return all_flags + none_flags


def fit_beta_binomial(cases: tuple[CaseRun, ...]) -> BetaBinomialFit:
    """Method of moments on the per-case flag proportions.

    Only cases with the modal number of repetitions are used, because the moment
    equations assume a common trial count and silently mis-estimate the spread when
    a few cases contribute two observations and the rest contribute eight.

    Fit this to one reference label at a time -- see ``fit_by_reference_label``.
    Fitting the pooled population is meaningless: reference-positive cases sit near a
    high flag rate and reference-negative cases near a low one, so the pooled
    proportions are bimodal by construction and the Beta absorbs the *labels* rather
    than the judge's per-case variability.
    """
    repeated = [c for c in cases if c.runs >= 2]
    if not repeated:
        return BetaBinomialFit(0, None, None, 0.0, None, 0, 0.0)

    counts = [c.runs for c in repeated]
    modal_runs = max(set(counts), key=counts.count)
    sample = [c for c in repeated if c.runs == modal_runs]
    m = modal_runs
    n = len(sample)

    proportions = [c.flags / m for c in sample]
    mean = fmean(proportions)
    unanimous = sum(1 for c in sample if c.flags in (0, m))

    if n < 2 or mean in (0.0, 1.0):
        return BetaBinomialFit(n, None, None, mean, None, unanimous, 0.0)

    #: Sample variance of the observed proportions, and the variance those same
    #: proportions would have if every case shared the mean rate.  The excess is what
    #: the Beta has to account for.
    observed = sum((p - mean) ** 2 for p in proportions) / (n - 1)
    binomial = mean * (1.0 - mean) / m
    if observed <= binomial:
        return BetaBinomialFit(n, None, None, mean, None, unanimous, 0.0)

    #: rho solves observed = mean(1-mean)/m * (1 + (m-1)*rho)
    rho = (observed * m / (mean * (1.0 - mean)) - 1.0) / (m - 1)
    rho = min(max(rho, 0.0), 0.999)
    if rho <= 0.0:
        return BetaBinomialFit(n, None, None, mean, 0.0, unanimous, 0.0)

    total = (1.0 - rho) / rho
    alpha = mean * total
    beta = (1.0 - mean) * total
    predicted = n * _beta_binomial_unanimous_probability(alpha, beta, m)
    return BetaBinomialFit(
        cases=n,
        alpha=alpha,
        beta=beta,
        mean=mean,
        intraclass_correlation=rho,
        unanimous_observed=unanimous,
        unanimous_predicted=predicted,
    )


def fit_by_reference_label(
    run: CharacterizationRun,
) -> tuple[BetaBinomialFit, BetaBinomialFit]:
    """``(positives, negatives)``.  The only defensible way to read the fit.

    Two fits rather than one because the quantity the model is for -- how much the
    judge's flag rate varies *between cases that should get the same answer* -- is
    only defined within a label group.
    """
    return (
        fit_beta_binomial(tuple(c for c in run.cases if c.reference_label)),
        fit_beta_binomial(tuple(c for c in run.cases if not c.reference_label)),
    )


# --------------------------------------------------------------------------------
# Sample-size honesty
# --------------------------------------------------------------------------------


def sample_size_warnings(run: CharacterizationRun) -> tuple[str, ...]:
    warnings: list[str] = []
    if len(run.cases) < MIN_CASES_FOR_COMPARISON:
        warnings.append(
            f"{len(run.cases)} cases is below the {MIN_CASES_FOR_COMPARISON}-case "
            f"floor for a held-out policy comparison; differences between policies "
            f"here are not distinguishable from the fold split"
        )
    repetitions = fmean(c.runs for c in run.cases) if run.cases else 0.0
    if repetitions < MIN_REPETITIONS_FOR_COMPARISON:
        warnings.append(
            f"mean {repetitions:.1f} observations per case is below "
            f"{MIN_REPETITIONS_FOR_COMPARISON}; policies that would spend more than "
            f"that are truncated and are not being compared at their own budget"
        )
    for row in slice_diagnostics(run):
        if row.cases < 5:
            warnings.append(
                f"slice '{row.slice_id}' has {row.cases} cases; any policy that "
                f"routes on it is acting on noise"
            )
    return tuple(warnings)


__all__ = [
    "ALTERNATE",
    "HUMAN",
    "AllocationDiagnostic",
    "BetaBinomialFit",
    "LeakageReport",
    "MarginalPoint",
    "PolicyResult",
    "SliceDiagnostic",
    "allocation_diagnostic",
    "compare",
    "fit_beta_binomial",
    "fit_by_reference_label",
    "held_out_outcomes",
    "leakage_report",
    "marginal_value",
    "pareto_front",
    "sample_size_warnings",
    "score",
    "slice_diagnostics",
]
