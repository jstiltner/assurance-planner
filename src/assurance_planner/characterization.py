"""Empirical characterization of a stochastic evaluator.

Deliberately outside the planner's decision path.  Nothing in ``planner.py`` imports
this module and nothing here returns a plan.  The planner consumes two numbers per
qualification row; this module exists to ask whether those two numbers are a fair
summary of what a judge actually does, and it is allowed to conclude that they are not.

The unit of record is a **case with repeated outcomes**, never an aggregate.  That is
the whole design: sensitivity 0.70 measured as "every case flags about 7 times in 10"
and sensitivity 0.70 measured as "70% of cases always flag, 30% never do" are the same
aggregate and completely different evidence, and only per-case records can tell them
apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean

from .domain import FailureModeRef, SourceVersionRef
from .statistics import prob_at_least, prob_fewer_than, procedure_for, wilson_interval

#: Below this many cases the dispersion statistic has too few degrees of freedom to
#: mean anything -- with two clusters a single disagreement dominates chi-square.
MIN_CASES_FOR_DISPERSION = 5

#: Below this many runs per case there is no within-case variation to measure at all.
MIN_RUNS_FOR_DISPERSION = 2


# --------------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CaseRun:
    """One reference case and every verdict the evaluator gave it, in order."""

    case_id: str
    #: The human/reference judgement: is the failure genuinely present in this case?
    reference_label: bool
    #: One boolean per repetition.  True means the evaluator flagged the failure.
    outcomes: tuple[bool, ...]
    #: Optional continuous score per repetition, kept but not yet used in any
    #: statistic.  Present because discarding it at ingest would be irreversible.
    scores: tuple[float, ...] = ()
    note: str = ""

    @property
    def runs(self) -> int:
        return len(self.outcomes)

    @property
    def flags(self) -> int:
        return sum(self.outcomes)

    @property
    def flag_rate(self) -> float:
        return self.flags / self.runs if self.runs else 0.0

    @property
    def correct_rate(self) -> float:
        """Fraction of repetitions that agreed with the reference label."""
        if not self.runs:
            return 0.0
        return sum(o == self.reference_label for o in self.outcomes) / self.runs

    @property
    def disagreement_rate(self) -> float:
        """Probability two randomly chosen repetitions of this case disagree.

        Zero for a case the evaluator always calls the same way, right or wrong.  This
        is the quantity that separates "noisy" from "confidently mistaken", and it is
        invisible in any aggregate.
        """
        n = self.runs
        if n < 2:
            return 0.0
        flags = self.flags
        return 2.0 * flags * (n - flags) / (n * (n - 1))


@dataclass(frozen=True, slots=True)
class CharacterizationRun:
    """Everything one evaluator did to one population of one failure mode."""

    evaluator_version: SourceVersionRef
    failure_mode: FailureModeRef
    population_id: str
    distribution_id: str
    cases: tuple[CaseRun, ...]
    note: str = ""

    @property
    def positives(self) -> tuple[CaseRun, ...]:
        return tuple(c for c in self.cases if c.reference_label)

    @property
    def negatives(self) -> tuple[CaseRun, ...]:
        return tuple(c for c in self.cases if not c.reference_label)


# --------------------------------------------------------------------------------
# Rate estimates, with and without the independence assumption
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Dispersion:
    """How far repeated outcomes depart from independent Bernoulli trials.

    ``phi`` is the Pearson chi-square dispersion statistic: observed variance in
    per-case flag counts divided by the variance a binomial model predicts.  One means
    the model fits.  Much greater than one means the outcomes cluster by case, so each
    extra repetition is worth less than the model thinks.  Less than one means they are
    more uniform than chance, which in practice means the evaluator is near-saturated
    at 0 or 1 on most cases.

    Not a random-effects model.  A single number, computable by hand, that says whether
    a random-effects model would be worth building.
    """

    cases: int
    runs_per_case: float
    pooled_rate: float
    phi: float
    #: Intra-class correlation implied by ``phi``.  Clipped at zero: a negative ICC is
    #: real but means "less clustered than chance", which does not reduce evidence.
    icc: float
    #: Runs that carry as much information as the raw run count claims to.
    effective_runs: float

    @property
    def is_implausible(self) -> bool:
        """Is the i.i.d. Bernoulli assumption not credible for this data?

        The threshold is a reporting convention, not a hypothesis test.  Two is chosen
        because at phi=2 the planner's replication count is already understating the
        runs needed by roughly a factor of two, which is large enough to change a
        decision and small enough to catch it before it does.
        """
        return self.phi >= 2.0


def _dispersion(cases: tuple[CaseRun, ...]) -> Dispersion | None:
    """Pearson dispersion over per-case flag counts.  ``None`` when undefined."""
    usable = tuple(c for c in cases if c.runs >= MIN_RUNS_FOR_DISPERSION)
    if len(usable) < MIN_CASES_FOR_DISPERSION:
        return None

    total_runs = sum(c.runs for c in usable)
    total_flags = sum(c.flags for c in usable)
    pooled = total_flags / total_runs
    if pooled in (0.0, 1.0):
        #: No variance to explain.  A perfectly consistent evaluator is not
        #: over-dispersed; it is simply not stochastic on this data.
        return Dispersion(
            cases=len(usable),
            runs_per_case=total_runs / len(usable),
            pooled_rate=pooled,
            phi=0.0,
            icc=0.0,
            effective_runs=float(total_runs),
        )

    chi_square = sum(
        (c.flags - c.runs * pooled) ** 2 / (c.runs * pooled * (1.0 - pooled))
        for c in usable
    )
    phi = chi_square / (len(usable) - 1)
    mean_runs = total_runs / len(usable)
    icc = max(0.0, (phi - 1.0) / (mean_runs - 1.0)) if mean_runs > 1.0 else 0.0
    design_effect = max(1.0, phi)
    return Dispersion(
        cases=len(usable),
        runs_per_case=mean_runs,
        pooled_rate=pooled,
        phi=phi,
        icc=icc,
        effective_runs=total_runs / design_effect,
    )


@dataclass(frozen=True, slots=True)
class RateEstimate:
    """One rate, three ways: point, naive interval, cluster-corrected interval."""

    label: str
    cases: int
    runs: int
    flags: int
    point: float
    #: Wilson over every run, treating each as an independent trial.  This is what the
    #: planner's inputs implicitly assume, and reporting it alongside the corrected
    #: interval is how the assumption is made visible rather than argued about.
    naive_interval: tuple[float, float]
    #: Wilson at the effective sample size implied by the dispersion statistic.
    corrected_interval: tuple[float, float]
    dispersion: Dispersion | None

    @property
    def naive_width(self) -> float:
        return self.naive_interval[1] - self.naive_interval[0]

    @property
    def corrected_width(self) -> float:
        return self.corrected_interval[1] - self.corrected_interval[0]


def _rate_estimate(label: str, cases: tuple[CaseRun, ...]) -> RateEstimate:
    runs = sum(c.runs for c in cases)
    flags = sum(c.flags for c in cases)
    point = flags / runs if runs else 0.0
    dispersion = _dispersion(cases)
    effective = dispersion.effective_runs if dispersion else float(runs)
    return RateEstimate(
        label=label,
        cases=len(cases),
        runs=runs,
        flags=flags,
        point=point,
        naive_interval=wilson_interval(flags, runs),
        corrected_interval=wilson_interval(point * effective, effective),
        dispersion=dispersion,
    )


# --------------------------------------------------------------------------------
# What another repetition is actually worth
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReplicationPoint:
    """The planner's prediction and the empirical answer at one replication count."""

    replications: int
    threshold_k: int
    #: What the binomial model says, from the pooled rates -- the planner's own number.
    model_miss: float
    model_false_alarm: float
    #: What the per-case rates say, averaging each case's own miss probability.  A
    #: case the evaluator reliably gets wrong contributes ~1 here and is invisible in
    #: the model figure.
    empirical_miss: float
    empirical_false_alarm: float

    @property
    def model_is_optimistic(self) -> bool:
        return self.empirical_miss > self.model_miss


def replication_curve(
    run: CharacterizationRun, max_error: float, max_replications: int = 12
) -> tuple[ReplicationPoint, ...]:
    """Walk n, choosing k exactly as the planner does, and score both ways.

    The planner picks ``k`` from the pooled rates because pooled rates are all it has.
    Holding that choice fixed and re-scoring it against the per-case rates isolates the
    cost of the aggregation, which is the question this experiment exists to answer.
    """
    positives = run.positives
    negatives = run.negatives
    if not positives or not negatives:
        return ()

    pooled_sensitivity = sum(c.flags for c in positives) / sum(
        c.runs for c in positives
    )
    pooled_fpr = sum(c.flags for c in negatives) / sum(c.runs for c in negatives)

    points: list[ReplicationPoint] = []
    for n in range(1, max_replications + 1):
        procedure = procedure_for(n, pooled_sensitivity, pooled_fpr, max_error)
        #: No k meets the target at this n.  Score the best available k anyway -- the
        #: curve is more informative than a gap, and the planner would simply have
        #: moved on to a larger n.
        k = procedure.threshold_k if procedure else _best_threshold(n, pooled_sensitivity, pooled_fpr)
        points.append(
            ReplicationPoint(
                replications=n,
                threshold_k=k,
                model_miss=prob_fewer_than(n, pooled_sensitivity, k),
                model_false_alarm=prob_at_least(n, pooled_fpr, k),
                empirical_miss=fmean(
                    prob_fewer_than(n, c.flag_rate, k) for c in positives
                ),
                empirical_false_alarm=fmean(
                    prob_at_least(n, c.flag_rate, k) for c in negatives
                ),
            )
        )
    return tuple(points)


def _best_threshold(n: int, sensitivity: float, false_positive_rate: float) -> int:
    """The k minimising the larger of the two error probabilities."""
    return min(
        range(1, n + 1),
        key=lambda k: max(
            prob_fewer_than(n, sensitivity, k), prob_at_least(n, false_positive_rate, k)
        ),
    )


@dataclass(frozen=True, slots=True)
class CaseVerdict:
    """What repetition can and cannot do for one case."""

    case: CaseRun
    #: ``resolved_by_one``   -- one run already meets the error target.
    #: ``helped_by_repetition`` -- more runs drive the case's error below the target.
    #: ``repetition_cannot_fix`` -- the evaluator is on the wrong side of the coin for
    #:   this case, so more runs converge on the wrong answer, not the right one.
    verdict: str
    #: Smallest n at which this case alone clears the target, or None.
    replications_needed: int | None


def classify_cases(
    run: CharacterizationRun, max_error: float, max_replications: int = 12
) -> tuple[CaseVerdict, ...]:
    """Per-case answer to "how much does another repetition actually buy?".

    Each case is scored on its own empirical rate against the best threshold available
    at each n.  Note that a real plan must use one shared k, so these are upper bounds
    on what repetition could do -- if a case cannot be fixed even with a k chosen for
    it alone, no shared-k procedure will fix it either.
    """
    verdicts: list[CaseVerdict] = []
    for case in run.cases:
        rate = case.flag_rate
        needed: int | None = None
        for n in range(1, max_replications + 1):
            best = min(
                (
                    prob_fewer_than(n, rate, k)
                    if case.reference_label
                    else prob_at_least(n, rate, k)
                )
                for k in range(1, n + 1)
            )
            if best <= max_error:
                needed = n
                break
        if needed == 1:
            verdict = "resolved_by_one"
        elif needed is not None:
            verdict = "helped_by_repetition"
        else:
            verdict = "repetition_cannot_fix"
        verdicts.append(CaseVerdict(case, verdict, needed))
    return tuple(verdicts)


# --------------------------------------------------------------------------------
# The whole analysis
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Characterization:
    run: CharacterizationRun
    sensitivity: RateEstimate
    false_positive_rate: RateEstimate
    curve: tuple[ReplicationPoint, ...]
    verdicts: tuple[CaseVerdict, ...]
    max_error: float

    @property
    def mean_agreement(self) -> float:
        """Mean probability that two repetitions of the same case agree."""
        repeated = [c for c in self.run.cases if c.runs >= 2]
        if not repeated:
            return 1.0
        return 1.0 - fmean(c.disagreement_rate for c in repeated)

    @property
    def independence_is_implausible(self) -> bool:
        return any(
            estimate.dispersion is not None and estimate.dispersion.is_implausible
            for estimate in (self.sensitivity, self.false_positive_rate)
        )

    @property
    def has_repeated_cases(self) -> bool:
        """Was any case evaluated more than once?

        If not, every per-case flag rate is 0 or 1 and the per-case analysis below
        degenerates: it will report that repetition buys nothing, when the truth is
        that this study cannot see what repetition buys.  The two are not the same
        finding and must not print the same sentence.
        """
        return any(c.runs >= 2 for c in self.run.cases)

    @property
    def unfixable_cases(self) -> tuple[CaseVerdict, ...]:
        return tuple(v for v in self.verdicts if v.verdict == "repetition_cannot_fix")

    def planner_replications(self) -> int | None:
        """What the planner would derive from the pooled point estimates alone."""
        for point in self.curve:
            if (
                point.model_miss <= self.max_error
                and point.model_false_alarm <= self.max_error
            ):
                return point.replications
        return None

    def empirical_replications(self) -> int | None:
        """The smallest n at which the *per-case* error rates meet the same target."""
        for point in self.curve:
            if (
                point.empirical_miss <= self.max_error
                and point.empirical_false_alarm <= self.max_error
            ):
                return point.replications
        return None


def characterize(
    run: CharacterizationRun, max_error: float, max_replications: int = 12
) -> Characterization:
    return Characterization(
        run=run,
        sensitivity=_rate_estimate("sensitivity", run.positives),
        false_positive_rate=_rate_estimate("false-positive rate", run.negatives),
        curve=replication_curve(run, max_error, max_replications),
        verdicts=classify_cases(run, max_error, max_replications),
        max_error=max_error,
    )
