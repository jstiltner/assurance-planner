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

from dataclasses import dataclass, replace
from datetime import date
from hashlib import sha256
from statistics import fmean

from .domain import FailureModeRef, MeasurementProvenance, SourceVersionRef
from .statistics import prob_at_least, prob_fewer_than, procedure_for, wilson_interval

#: Below this many cases the dispersion statistic has too few degrees of freedom to
#: mean anything -- with two clusters a single disagreement dominates chi-square.
MIN_CASES_FOR_DISPERSION = 5

#: Below this many runs per case there is no within-case variation to measure at all.
MIN_RUNS_FOR_DISPERSION = 2


# --------------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------------


def _majority(flags: int, runs: int) -> bool | None:
    """Majority verdict over ``runs`` observations, ``None`` on no data or a tie."""
    if not runs or flags * 2 == runs:
        return None
    return flags * 2 > runs


def _disagreement(flags: int, runs: int) -> float:
    """Probability two distinct observations of the same case disagree."""
    if runs < 2:
        return 0.0
    return 2.0 * flags * (runs - flags) / (runs * (runs - 1))


@dataclass(frozen=True, slots=True)
class CaseRun:
    """One reference case and every verdict the evaluator gave it, in order.

    A case may also carry observations from a *second* source on the same case.  That
    pairing is the whole point: two sources measured on two different case sets can be
    compared on aggregate accuracy and on nothing else, and aggregate accuracy cannot
    answer whether the second source is wrong where the first one is wrong.  Only
    paired observations can, so the pairing is a property of the case record rather
    than something reconstructed later by joining two files on ``case_id``.
    """

    case_id: str
    #: The human/reference judgement: is the failure genuinely present in this case?
    reference_label: bool
    #: One boolean per repetition.  True means the evaluator flagged the failure.
    outcomes: tuple[bool, ...]
    #: Optional continuous score per repetition, kept but not yet used in any
    #: statistic.  Present because discarding it at ingest would be irreversible.
    scores: tuple[float, ...] = ()
    #: A behavioural subtype this case belongs to.  This is the *only* handle a
    #: retrospective policy is allowed to generalise over: a policy that keys on
    #: ``case_id`` has memorised the answer, and a policy that keys on nothing cannot
    #: allocate effort at all.  Empty string means unsliced.
    slice_id: str = ""
    #: Per-observation measurements, when the harness recorded them.  Empty is normal
    #: for synthetic data and means "use the declared cost model".
    latencies_ms: tuple[float, ...] = ()
    costs_usd: tuple[float, ...] = ()
    #: Observations from the alternate source on *this same case*.  Empty means the
    #: case was never sent to the alternate, which is different from "the alternate
    #: said nothing" and is counted separately everywhere downstream.
    alternate_outcomes: tuple[bool, ...] = ()
    alternate_scores: tuple[float, ...] = ()
    alternate_latencies_ms: tuple[float, ...] = ()
    alternate_costs_usd: tuple[float, ...] = ()
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
    def majority_verdict(self) -> bool | None:
        """What an unlimited-budget majority vote over every repetition concludes.

        ``None`` on an exact tie, which is a real outcome and not a coin toss to be
        resolved here: a policy that ties has not reached a decision, and recording
        that honestly is what lets the benchmark count abstentions.
        """
        return _majority(self.flags, self.runs)

    @property
    def majority_agrees_with_reference(self) -> bool:
        return self.majority_verdict is self.reference_label

    # --- the alternate source, on this same case ---------------------------------

    @property
    def has_alternate(self) -> bool:
        return bool(self.alternate_outcomes)

    @property
    def alternate_runs(self) -> int:
        return len(self.alternate_outcomes)

    @property
    def alternate_flags(self) -> int:
        return sum(self.alternate_outcomes)

    @property
    def alternate_majority_verdict(self) -> bool | None:
        """Same rule as the primary, including ``None`` on a tie.

        Using the same rule matters more than which rule it is.  If the primary were
        scored on a majority and the alternate on "flagged at least once", every
        complementarity figure below would partly be measuring the difference between
        two decision rules rather than between two sources.
        """
        return _majority(self.alternate_flags, self.alternate_runs)

    @property
    def alternate_disagreement_rate(self) -> float:
        """Within-alternate instability.  Zero when the alternate was run once."""
        return _disagreement(self.alternate_flags, self.alternate_runs)

    @property
    def disagreement_rate(self) -> float:
        """Probability two randomly chosen repetitions of this case disagree.

        Zero for a case the evaluator always calls the same way, right or wrong.  This
        is the quantity that separates "noisy" from "confidently mistaken", and it is
        invisible in any aggregate.
        """
        return _disagreement(self.flags, self.runs)


@dataclass(frozen=True, slots=True)
class CharacterizationRun:
    """Everything one evaluator did to one population of one failure mode."""

    evaluator_version: SourceVersionRef
    failure_mode: FailureModeRef
    population_id: str
    distribution_id: str
    cases: tuple[CaseRun, ...]
    #: The source that produced ``CaseRun.alternate_outcomes``, when any case carries
    #: them.  Required in that case: an alternate whose version is not recorded cannot
    #: be qualified, because a qualification key without a source version is the exact
    #: silent substitution the key exists to prevent.
    alternate_version: SourceVersionRef | None = None
    #: Set by the data file.  Marks observations that were generated rather than
    #: collected.  Nothing in this package can infer it, and everything that turns a
    #: run into planner evidence refuses when it is true.
    synthetic: bool = False
    note: str = ""
    #: The date the observations were collected.  Supplied by the data file, never
    #: read from a clock -- this package is asserted to contain neither.
    measured_on: date | None = None
    #: Caveats the person who ran the study wants carried forward onto every planner
    #: input derived from it.
    limitations: tuple[str, ...] = ()
    #: Stable identifier for this study.  Defaults to a content hash so that two
    #: artifacts claiming the same provenance can be told apart, and so that an
    #: artifact regenerated from unchanged data keeps its id.
    run_id: str = ""

    def __post_init__(self) -> None:
        if self.alternate_version is None and any(c.has_alternate for c in self.cases):
            raise ValueError(
                "cases carry alternate observations but the run does not name the "
                "alternate source version; unattributed observations cannot be keyed "
                "to a qualification slot"
            )
        if not self.run_id:
            object.__setattr__(self, "run_id", self.content_digest())

    def content_digest(self) -> str:
        """A short deterministic fingerprint of identity plus every case outcome.

        Not a cryptographic commitment and not a substitute for storing the data --
        it exists so a reader can tell whether two artifacts came from the same
        observations, which is the question that actually gets asked when two
        qualification rows disagree.
        """
        material = "|".join(
            [
                str(self.evaluator_version),
                str(self.failure_mode),
                self.population_id,
                self.distribution_id,
            ]
            + [str(self.alternate_version or "")]
            + [
                f"{c.case_id}:{c.slice_id}:{int(c.reference_label)}:"
                f"{''.join('1' if o else '0' for o in c.outcomes)}:"
                f"{''.join('1' if o else '0' for o in c.alternate_outcomes)}"
                for c in self.cases
            ]
        )
        return sha256(material.encode("utf-8")).hexdigest()[:16]

    @property
    def positives(self) -> tuple[CaseRun, ...]:
        return tuple(c for c in self.cases if c.reference_label)

    @property
    def negatives(self) -> tuple[CaseRun, ...]:
        return tuple(c for c in self.cases if not c.reference_label)

    @property
    def slices(self) -> tuple[str, ...]:
        return tuple(sorted({c.slice_id for c in self.cases}))

    def in_slice(self, slice_id: str) -> tuple[CaseRun, ...]:
        return tuple(c for c in self.cases if c.slice_id == slice_id)

    @property
    def paired_cases(self) -> tuple[CaseRun, ...]:
        """Cases with observations from both sources.  The only comparable ones."""
        return tuple(c for c in self.cases if c.runs and c.has_alternate)

    def alternate_view(self) -> "CharacterizationRun":
        """The same study, read as a characterization *of the alternate source*.

        This is how the alternate gets its own sensitivity, false-positive rate,
        Wilson intervals, dispersion statistic and qualification artifact: not through
        a second implementation of all of that, but by presenting its observations in
        the shape the existing machinery already consumes.  A second implementation
        would be a second set of conventions to keep in agreement, and the first thing
        to drift would be the one that matters -- whether a tie counts as an error.

        Restricted to paired cases, because an alternate rate computed over a
        different case set than the primary's cannot be differenced against it.
        """
        if self.alternate_version is None:
            raise ValueError(
                f"run '{self.run_id}' has no alternate source to characterize"
            )
        cases = tuple(
            replace(
                case,
                outcomes=case.alternate_outcomes,
                scores=case.alternate_scores,
                latencies_ms=case.alternate_latencies_ms,
                costs_usd=case.alternate_costs_usd,
                alternate_outcomes=(),
                alternate_scores=(),
                alternate_latencies_ms=(),
                alternate_costs_usd=(),
            )
            for case in self.paired_cases
        )
        return replace(
            self,
            evaluator_version=self.alternate_version,
            cases=cases,
            alternate_version=None,
            run_id="",
        )

    def with_cases(self, cases: tuple[CaseRun, ...]) -> "CharacterizationRun":
        """Same study identity, a subset of its cases.  Used for fold splitting.

        ``run_id`` is recomputed rather than inherited, because a fold is not the
        study and an artifact emitted from one must not claim to be the other.
        """
        return replace(self, cases=cases, run_id="")


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

    def qualification_counts(self) -> tuple[int, int, int, int]:
        """``(positive_runs, true_positives, negative_runs, false_positives)``.

        **Observations, not cases.** The planner's model is ``Binomial(n, sensitivity)``
        over repeated runs of one case, so the rate it needs is a per-*run* flag
        probability and the denominator has to be runs.  Collapsing to a majority vote
        per case first would answer a different question and silently change what
        ``n`` means.

        The cost of that choice is that the raw denominator overstates the information
        present whenever outcomes cluster by case, which is exactly the effect the
        dispersion statistic measures.  Both numbers travel together in the
        provenance record so a reader can see the gap rather than having to suspect it.
        """
        positives, negatives = self.run.positives, self.run.negatives
        return (
            sum(c.runs for c in positives),
            sum(c.flags for c in positives),
            sum(c.runs for c in negatives),
            sum(c.flags for c in negatives),
        )

    def provenance(self, artifact_ref: str = "") -> MeasurementProvenance:
        cases = self.run.cases
        repetitions = fmean([c.runs for c in cases]) if cases else 0.0
        sensitivity_dispersion = self.sensitivity.dispersion
        return MeasurementProvenance(
            characterization_run_id=self.run.run_id,
            reference_positive_cases=len(self.run.positives),
            reference_negative_cases=len(self.run.negatives),
            repetitions_per_case=repetitions,
            effective_positive_runs=(
                sensitivity_dispersion.effective_runs
                if sensitivity_dispersion
                else float(self.sensitivity.runs)
            ),
            effective_negative_runs=(
                self.false_positive_rate.dispersion.effective_runs
                if self.false_positive_rate.dispersion
                else float(self.false_positive_rate.runs)
            ),
            dispersion_phi=(
                sensitivity_dispersion.phi if sensitivity_dispersion else None
            ),
            mean_same_case_agreement=self.mean_agreement,
            cases_repetition_cannot_fix=len(self.unfixable_cases),
            artifact_ref=artifact_ref,
        )

    def derived_limitations(self) -> tuple[str, ...]:
        """Caveats the study author wrote, plus the ones the data itself forces.

        These end up on the qualification row and are rendered in the planner's
        rationale.  The point is that a reader of a *plan* sees the warning, not only
        a reader of the characterization report -- the seam this pass exists to close
        runs in that direction too.
        """
        derived = list(self.run.limitations)
        positives, _, negatives, _ = self.qualification_counts()
        derived.append(
            f"counts are observations, not cases: {len(self.run.positives)} positive "
            f"and {len(self.run.negatives)} negative reference cases at "
            f"{self.provenance().repetitions_per_case:.1f} repetitions "
            f"({positives} and {negatives} runs)"
        )
        if self.independence_is_implausible:
            phi = self.sensitivity.dispersion
            derived.append(
                f"outcomes cluster by case (phi={phi.phi:.2f}); the run counts "
                f"overstate the evidence by roughly {phi.phi:.1f}x"
            )
        if self.unfixable_cases:
            derived.append(
                f"{len(self.unfixable_cases)} case(s) are decided wrong at every "
                f"replication count in the studied range; replication does not "
                f"bound their error"
            )
        if not self.has_repeated_cases:
            derived.append(
                "single-observation study: within-case variance is unmeasured, so no "
                "replication count derived from this row is empirically supported"
            )
        return tuple(derived)

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
