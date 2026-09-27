"""Retrospective evaluation policies, and the folds that keep them honest.

A *policy* consumes one case's recorded observations in order, decides when it has
seen enough, and either returns a verdict or escalates.  Replaying policies against
observations that were already collected is the cheapest way to ask the only question
that matters here:

    given repeated observations from a stochastic evaluator, what evaluation policy
    reaches an acceptable assurance target at the lowest cost?

None of these policies is novel and none is claimed to be.  Fixed-N with a vote,
majority-race early termination, confidence-interval stopping, and escalation to a
stronger source are all standard.  They are here because the candidate contribution
has to beat them, and it cannot be shown to beat them until they exist in the same
harness with the same cost model.

Two constraints shape every line below.

**No randomness.** This package is asserted to contain none, and the assertion is
worth more than a Monte-Carlo escalation model.  Where a policy escalates to an
imperfect alternate evaluator, the error contribution is accounted in *expectation*
from that evaluator's declared rates.  That makes false-negative counts fractional,
which is honest about the fact that no alternate observations were collected.

**No leakage.** A retrospective policy must never decide what to do with a case using
information it could not have had before spending the call.  The dangerous case is
policy E, which needs to know that some kinds of case do not benefit from repetition.
It learns that per *slice*, from a calibration fold, and is evaluated on cases that
fold never saw.  ``stratified_folds`` is the mechanism and
``tests/test_policies.py`` asserts the disjointness rather than trusting it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt

from .characterization import CaseRun, CharacterizationRun

#: Two-sided 90% normal quantile.  Used only by the confidence-stopping policy, where
#: 95% turns out to be so conservative that the rule never fires before n=5 and the
#: comparison stops being informative.  Stated as a constant because the choice
#: materially changes that policy's result and should be visible, not buried.
Z_90 = 1.6448536269514722

#: What an escalation resolves to.
HUMAN = "human"
ALTERNATE = "alternate"


# --------------------------------------------------------------------------------
# Economics
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CostModel:
    """Prices and latencies for every source a policy may spend.

    ``judge_parallelism`` is the number of repetitions of a *single case* that can be
    in flight at once.  It exists because summing per-call latency and calling the
    total "wall clock" is wrong in the one direction that flatters a fixed-N policy:
    eight sequential calls and eight parallel calls cost the same money and very
    different time, and a policy comparison that ignores that will recommend the wrong
    thing.  Both figures are reported; neither is presented as the other.

    The alternate evaluator's rates are **declared, not measured**.  No alternate-source
    observations exist in any fixture, so escalating to it contributes expected error
    rather than an observed one.  Setting both to a perfect oracle is how the harness
    models human adjudication, and that is itself an assumption: it treats the
    reference label as ground truth by definition.
    """

    judge_cost_usd: float = 0.0625
    judge_latency_seconds: float = 120.0
    judge_parallelism: int = 1

    alternate_cost_usd: float = 0.75
    alternate_latency_seconds: float = 240.0
    #: Declared, not measured.  See class docstring.
    alternate_sensitivity: float = 0.95
    alternate_false_positive_rate: float = 0.05

    human_cost_usd: float = 12.0
    human_latency_seconds: float = 900.0

    def escalation_cost(self, target: str) -> float:
        return self.human_cost_usd if target == HUMAN else self.alternate_cost_usd

    def escalation_latency(self, target: str) -> float:
        return (
            self.human_latency_seconds
            if target == HUMAN
            else self.alternate_latency_seconds
        )


# --------------------------------------------------------------------------------
# What a policy did to one case
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CaseOutcome:
    case_id: str
    slice_id: str
    reference_label: bool
    #: True = declared failing, False = declared passing, None = unresolved.
    verdict: bool | None
    judge_calls: int
    #: "" when the case was settled by the judge alone.
    escalated_to: str = ""
    #: The policy asked for more repetitions than the study recorded.  Not an error --
    #: it is what a fixed-N policy does on a sparsely sampled slice -- but a result
    #: computed over truncated cases is answering a slightly different question and
    #: the report says so.
    truncated: bool = False

    @property
    def escalated(self) -> bool:
        return bool(self.escalated_to)


def _majority(flags: int, seen: int) -> bool | None:
    if flags * 2 == seen:
        return None
    return flags * 2 > seen


# --------------------------------------------------------------------------------
# Calibration: what a policy is allowed to have learned in advance
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SliceProfile:
    """How cases in one behavioural subtype have historically behaved.

    Deliberately three proportions and a count.  Anything richer -- a per-case table,
    a fitted model with as many parameters as cases -- starts memorising individual
    cases, which is the failure mode question 2 of the red-team exists to catch.
    """

    slice_id: str
    cases: int
    #: Unanimous across repetitions, and the unanimous answer matches the reference.
    stable_correct: float
    #: Unanimous across repetitions, and unanimously wrong.  Repetition is worthless
    #: here and, worse, it is *convincing*: every extra call increases apparent
    #: certainty about the wrong answer.
    stable_wrong: float
    #: Not unanimous.  Repetition has something to average over.
    unstable: float
    #: Mean repetitions recorded per case in this slice.
    repetitions: float

    @property
    def is_thin(self) -> bool:
        """Too few calibration cases, or too few repetitions, to act on.

        Five is the same floor the dispersion statistic uses.  Two repetitions is the
        minimum at which "unanimous" carries any information at all, and a slice at
        exactly two will call almost everything stable, so the policy must not treat
        such a slice as evidence of stability.
        """
        return self.cases < 5 or self.repetitions < 3.0


def profile_slices(run: CharacterizationRun) -> dict[str, SliceProfile]:
    profiles: dict[str, SliceProfile] = {}
    for slice_id in run.slices:
        cases = run.in_slice(slice_id)
        repeated = [c for c in cases if c.runs >= 2]
        if not repeated:
            profiles[slice_id] = SliceProfile(slice_id, len(cases), 0.0, 0.0, 0.0, 1.0)
            continue
        stable_correct = stable_wrong = unstable = 0
        for case in repeated:
            if case.flags in (0, case.runs):
                if case.majority_agrees_with_reference:
                    stable_correct += 1
                else:
                    stable_wrong += 1
            else:
                unstable += 1
        total = len(repeated)
        profiles[slice_id] = SliceProfile(
            slice_id=slice_id,
            cases=total,
            stable_correct=stable_correct / total,
            stable_wrong=stable_wrong / total,
            unstable=unstable / total,
            repetitions=sum(c.runs for c in repeated) / total,
        )
    return profiles


@dataclass(frozen=True, slots=True)
class Calibration:
    """Everything a policy is permitted to know before it sees a held-out case."""

    slices: dict[str, SliceProfile] = field(default_factory=dict)
    #: Case ids the calibration was built from.  Carried so the harness can assert
    #: that no evaluated case appears here, which is the leakage check.
    source_case_ids: frozenset[str] = frozenset()

    @classmethod
    def from_run(cls, run: CharacterizationRun) -> "Calibration":
        return cls(
            slices=profile_slices(run),
            source_case_ids=frozenset(c.case_id for c in run.cases),
        )


EMPTY_CALIBRATION = Calibration()


# --------------------------------------------------------------------------------
# The policies
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FixedN:
    """Baseline A. Spend exactly ``n`` calls, flag at ``>= k``.

    The vote rule is a simple majority unless ``threshold_k`` is given: with ``n=8``
    the case is declared failing at five or more flags, and an exact four-four split
    is *unresolved* rather than silently rounded, because rounding it would hide the
    ties that a policy comparison should be paying for.

    ``n=8`` is included because it is the historical operating practice this whole
    exercise exists to challenge, not because anything recommends it.
    """

    n: int
    threshold_k: int | None = None

    @property
    def name(self) -> str:
        return f"fixed_n_{self.n}"

    def decide(self, case: CaseRun, calibration: Calibration) -> CaseOutcome:
        used = min(self.n, case.runs)
        flags = sum(case.outcomes[:used])
        if self.threshold_k is None:
            verdict = _majority(flags, used)
        else:
            verdict = flags >= self.threshold_k
        return CaseOutcome(
            case_id=case.case_id,
            slice_id=case.slice_id,
            reference_label=case.reference_label,
            verdict=verdict,
            judge_calls=used,
            truncated=used < self.n,
        )


@dataclass(frozen=True, slots=True)
class EarlyStopMajority:
    """Baseline B. Stop as soon as the remaining calls cannot change the majority.

    The exact rule, stated so it can be audited: with a budget of ``n_max`` and a
    majority threshold ``w = n_max // 2 + 1``, stop at the first observation where
    either the flag count or the clean count reaches ``w``.  No unseen observation can
    overturn a side that already holds a majority of the whole budget.

    Consequently this policy returns **exactly the verdict** ``FixedN(n_max)`` would
    return, on every case, while never making more calls and usually making fewer.
    That is a theorem about the rule, not a property of any fixture, and the test
    suite checks it over every case in every fixture.  It is also why the honest
    baseline for "did we save money" is this policy and not fixed-N: any harness that
    reports savings against fixed-N is partly reporting the savings of a rule that has
    been standard for decades.
    """

    n_max: int

    @property
    def name(self) -> str:
        return f"early_stop_{self.n_max}"

    def decide(self, case: CaseRun, calibration: Calibration) -> CaseOutcome:
        budget = min(self.n_max, case.runs)
        win = self.n_max // 2 + 1
        flags = clean = 0
        for index, outcome in enumerate(case.outcomes[:budget], start=1):
            flags += outcome
            clean += not outcome
            if flags >= win or clean >= win:
                return CaseOutcome(
                    case_id=case.case_id,
                    slice_id=case.slice_id,
                    reference_label=case.reference_label,
                    verdict=flags >= win,
                    judge_calls=index,
                    truncated=False,
                )
        return CaseOutcome(
            case_id=case.case_id,
            slice_id=case.slice_id,
            reference_label=case.reference_label,
            verdict=_majority(flags, budget),
            judge_calls=budget,
            truncated=budget < self.n_max,
        )


@dataclass(frozen=True, slots=True)
class ConfidenceStop:
    """Baseline C. Keep sampling until the flag rate is decisively above or below half.

    After each observation, a Wilson score interval is computed on the flag rate so
    far.  If the whole interval sits on one side of 0.5, the underlying rate is
    decisively one thing and sampling stops.  Otherwise another observation is bought,
    to a hard cap.

    This is not the same rule as ``EarlyStopMajority`` and can disagree with it: it is
    a statement about the *rate*, not about the vote, so it can stop before a majority
    is locked and can refuse to stop after one.  It is reported at 90% rather than 95%
    because at 95% the interval does not clear 0.5 until five consecutive agreeing
    observations, which makes the policy strictly worse than fixed-N in most of the
    comparisons and tells us nothing.  That sensitivity to the confidence level is a
    finding about the rule, and it is in the red-team notes rather than tuned away.
    """

    n_max: int
    z: float = Z_90

    @property
    def name(self) -> str:
        return f"confidence_stop_{self.n_max}"

    def _decisive(self, flags: int, seen: int) -> bool | None:
        p = flags / seen
        denominator = 1.0 + self.z * self.z / seen
        centre = (p + self.z * self.z / (2.0 * seen)) / denominator
        half = (
            self.z
            * sqrt(p * (1.0 - p) / seen + self.z * self.z / (4.0 * seen * seen))
        ) / denominator
        low, high = centre - half, centre + half
        if low > 0.5:
            return True
        if high < 0.5:
            return False
        return None

    def decide(self, case: CaseRun, calibration: Calibration) -> CaseOutcome:
        budget = min(self.n_max, case.runs)
        flags = 0
        for index, outcome in enumerate(case.outcomes[:budget], start=1):
            flags += outcome
            decisive = self._decisive(flags, index)
            if decisive is not None:
                return CaseOutcome(
                    case_id=case.case_id,
                    slice_id=case.slice_id,
                    reference_label=case.reference_label,
                    verdict=decisive,
                    judge_calls=index,
                )
        return CaseOutcome(
            case_id=case.case_id,
            slice_id=case.slice_id,
            reference_label=case.reference_label,
            verdict=_majority(flags, budget),
            judge_calls=budget,
            truncated=budget < self.n_max,
        )


@dataclass(frozen=True, slots=True)
class ProbeThenEscalate:
    """Baseline D. A short probe; escalate anything the probe did not settle.

    Buy ``probe`` observations.  If they agree, take that answer.  If they disagree,
    the judge is visibly uncertain, so hand the case to a stronger source rather than
    buying more of the same opinion.

    This is the cheapest sensible cascade and it is the baseline that matters most for
    honesty: escalation is the single most powerful lever in the whole comparison,
    because a perfect adjudicator fixes any case it touches.  If this policy matches
    heterogeneity-aware triage, then triage is contributing nothing beyond "escalate
    sometimes" and should not be built.
    """

    probe: int = 2
    target: str = ALTERNATE

    @property
    def name(self) -> str:
        return f"probe_{self.probe}_escalate_{self.target}"

    def decide(self, case: CaseRun, calibration: Calibration) -> CaseOutcome:
        used = min(self.probe, case.runs)
        flags = sum(case.outcomes[:used])
        if flags in (0, used):
            return CaseOutcome(
                case_id=case.case_id,
                slice_id=case.slice_id,
                reference_label=case.reference_label,
                verdict=flags == used,
                judge_calls=used,
                truncated=used < self.probe,
            )
        return CaseOutcome(
            case_id=case.case_id,
            slice_id=case.slice_id,
            reference_label=case.reference_label,
            verdict=None,
            judge_calls=used,
            escalated_to=self.target,
            truncated=used < self.probe,
        )


@dataclass(frozen=True, slots=True)
class HeterogeneityTriage:
    """Candidate E. Spend repetition only where repetition has historically paid.

    The whole proposition, and it is a small one: some kinds of case are settled by one
    call, some are genuinely noisy and reward averaging, and some are ones this judge
    is confidently wrong about -- where repetition buys *confidence* without buying
    *accuracy*, which is worse than buying nothing. Allocate accordingly.

    The hard part is that **a policy cannot tell stable-correct from stable-wrong at
    run time.** Both look like a unanimous verdict. The reference label is exactly what
    is unavailable when the decision is being made. So the only usable handle is the
    slice's historical composition, and the policy is a three-way branch on it:

    * slice is historically often confidently wrong -> do not trust unanimity here,
      escalate after a single probe call;
    * slice is historically almost always right -> one call and stop;
    * otherwise -> early-stop majority, the standard rule, up to the budget.

    A slice with too little calibration behind it falls through to the standard rule.
    Pretending to triage on four cases would be the same false precision this project
    spent the last pass documenting.

    Note what this cannot do: within the escalate-slice it pays for the cases it was
    going to get right anyway, and within the trust-slice it accepts the confidently
    wrong ones. It buys nothing at all unless slices differ, and the benchmark fixture
    is built with deliberately imperfect slices so that this is a real test.
    """

    n_max: int = 8
    probe: int = 1
    #: Above this historical rate of confident-and-wrong cases, unanimity in this slice
    #: is not evidence and repetition is throwing money at a fixed opinion.
    escalate_above: float = 0.30
    #: Above this historical rate of confident-and-right cases, one call is enough.
    trust_above: float = 0.80
    target: str = ALTERNATE

    @property
    def name(self) -> str:
        return "heterogeneity_triage"

    def route(self, slice_id: str, calibration: Calibration) -> str:
        #: An unlabelled case carries no subtype information, so there is nothing to
        #: triage on.  Routing the whole unlabelled population one way would be a
        #: population-level decision wearing a triage policy's name.
        if not slice_id:
            return "standard"
        profile = calibration.slices.get(slice_id)
        if profile is None or profile.is_thin:
            return "standard"
        if profile.stable_wrong >= self.escalate_above:
            return "escalate"
        if profile.stable_correct >= self.trust_above:
            return "trust"
        return "standard"

    def decide(self, case: CaseRun, calibration: Calibration) -> CaseOutcome:
        route = self.route(case.slice_id, calibration)

        if route == "escalate":
            used = min(self.probe, case.runs)
            return CaseOutcome(
                case_id=case.case_id,
                slice_id=case.slice_id,
                reference_label=case.reference_label,
                verdict=None,
                judge_calls=used,
                escalated_to=self.target,
            )

        if route == "trust":
            used = min(1, case.runs)
            return CaseOutcome(
                case_id=case.case_id,
                slice_id=case.slice_id,
                reference_label=case.reference_label,
                verdict=bool(case.outcomes[0]),
                judge_calls=used,
            )

        return EarlyStopMajority(self.n_max).decide(case, calibration)


#: The comparison set. Ordered cheapest-looking first so the report reads as a ladder.
def default_policies(n_max: int = 8) -> tuple:
    return (
        FixedN(1),
        FixedN(3),
        FixedN(5),
        FixedN(n_max),
        EarlyStopMajority(n_max),
        ConfidenceStop(n_max),
        ProbeThenEscalate(2),
        HeterogeneityTriage(n_max=n_max),
    )


# --------------------------------------------------------------------------------
# Folds
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Fold:
    index: int
    calibration: CharacterizationRun
    held_out: CharacterizationRun


def stratified_folds(run: CharacterizationRun, k: int = 5) -> tuple[Fold, ...]:
    """Deterministic slice-stratified k-fold split.

    Cases are sorted by id within each slice and assigned to fold ``position % k``.
    Sorting rather than shuffling keeps the package free of randomness and makes the
    split reproducible by inspection: a reader can work out which fold a case is in
    without running anything.

    Stratifying by slice matters because the whole point of the exercise is that
    slices behave differently. An unstratified split on a twenty-case slice can easily
    put every case of one regime in the calibration set, which would make the triage
    policy look either magical or useless depending on the draw.
    """
    if k < 2:
        raise ValueError(f"k-fold requires k >= 2, got {k}")

    assignment: dict[str, int] = {}
    for slice_id in run.slices:
        cases = sorted(run.in_slice(slice_id), key=lambda c: c.case_id)
        for position, case in enumerate(cases):
            assignment[case.case_id] = position % k

    folds = []
    for index in range(k):
        held_out = tuple(c for c in run.cases if assignment[c.case_id] == index)
        calibration = tuple(c for c in run.cases if assignment[c.case_id] != index)
        if held_out and calibration:
            folds.append(
                Fold(
                    index=index,
                    calibration=run.with_cases(calibration),
                    held_out=run.with_cases(held_out),
                )
            )
    return tuple(folds)
