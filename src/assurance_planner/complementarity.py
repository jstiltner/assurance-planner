"""Whether a second source is wrong where the first source is wrong.

This module exists because the routing hypothesis in this repository -- escalate the
cases the primary evaluator handles badly to a stronger source -- has a precondition
that no accuracy figure can check.  A second source can be *more accurate overall* and
still be useless for routing, if its errors land on the same cases.  It can be *less
accurate overall* and still be valuable, if they do not.  Aggregate sensitivity cannot
tell those apart, so it is the wrong instrument and always was.

The right instrument is a 2x2 over paired cases:

                        alternate correct   alternate wrong
    primary correct        neither_wrong    alternate_only_wrong
    primary wrong       primary_only_wrong  both_wrong

Everything below is read off that table.  Three properties of it govern the design.

**It requires the same cases.**  Two sources measured on two case sets have no table.
That is why pairing lives in ``CaseRun`` and why ``paired_cases`` is the denominator
here rather than ``cases``.

**The decision rule must be identical on both axes.**  Both sides use the majority
verdict, and a tie on either side removes the case from the table rather than being
resolved.  If the two axes used different rules the table would partly be measuring
the rules.

**Nothing here is a conclusion.**  ``P(alternate correct | primary wrong)`` near 1
is consistent with the alternate being a better replacement *and* with it being a
complement, and the two imply different systems.  Separating them needs the marginal
accuracies as well, and separating either from noise needs the intervals.  This module
computes the numbers and the intervals; it names no recommendation, because at the time
of writing there is no measured alternate source anywhere in this repository to make
one about.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, sqrt

from .characterization import CaseRun, CharacterizationRun
from .statistics import wilson_interval

#: Paired cases below which the whole table is labelled thin.  The same floor
#: ``benchmark.MIN_CASES_FOR_COMPARISON`` uses, for the same reason and deliberately
#: not a different number.
#:
#: This floor is about the joint error rate and the disagreement rate, which have the
#: case count as their denominator.  It says nothing about the conditional
#: probabilities, whose denominator is the *error* count -- a study can clear this floor
#: several times over and still not support them.  See ``required_paired_cases``.
MIN_PAIRED_CASES = 40

#: Errors below which a conditional probability is reported as unsupported.
#:
#: Derived, not chosen.  The recovery rate is used to decide whether the alternate
#: fixes more of the primary's mistakes than it leaves standing, so the question asked
#: of it is whether it exceeds 0.5.  At an observed 0.75 the 95% Wilson interval clears
#: 0.5 at a denominator of 16 ([0.505, 0.898]) and not at 12 ([0.468, 0.911]).
#:
#: Sixteen is therefore a floor at an *optimistic* recovery rate and is not a sufficient
#: sample size in general.  At an observed 0.70 the requirement is 21 errors; at 0.60 it
#: is 91.  A study that collects 16 primary errors and observes 0.62 has measured
#: nothing, and the report says so rather than printing the interval and moving on.
MIN_ERRORS_FOR_CONDITIONAL = 16


def required_paired_cases(primary_error_rate: float) -> int | None:
    """Paired cases needed before the recovery rate has a usable denominator.

    ``MIN_ERRORS_FOR_CONDITIONAL`` primary errors are needed, and the primary only
    produces errors at its own error rate, so a study of an accurate primary needs a
    large case set to say anything about complementarity at all.  A primary that is
    wrong on one case in ten needs 160 paired cases to accumulate 16 errors.

    This is the figure that makes the collection protocol expensive, and it is stated
    as a function rather than a constant so that it is computed from the primary's
    measured error rate instead of a hoped-for one.  ``None`` when the primary makes no
    errors, which is not "zero cases needed" -- it means the routing question does not
    arise, and if that is the measured result then the alternate has nothing to recover.
    """
    if primary_error_rate <= 0.0:
        return None
    return ceil(MIN_ERRORS_FOR_CONDITIONAL / primary_error_rate)


def _correct(verdict: bool | None, reference: bool) -> bool | None:
    """``None`` when the source did not reach a verdict.  A tie is not an answer."""
    if verdict is None:
        return None
    return verdict is reference


@dataclass(frozen=True, slots=True)
class Conditional:
    """One proportion, its denominator, and whether the denominator supports it."""

    label: str
    successes: int
    trials: int

    @property
    def point(self) -> float | None:
        return self.successes / self.trials if self.trials else None

    @property
    def interval(self) -> tuple[float, float] | None:
        return wilson_interval(self.successes, self.trials) if self.trials else None

    @property
    def supported(self) -> bool:
        """Is the denominator large enough for the interval to exclude anything?"""
        return self.trials >= MIN_ERRORS_FOR_CONDITIONAL


@dataclass(frozen=True, slots=True)
class PairedErrors:
    """The 2x2, the cases it had to drop, and every statistic derived from it."""

    #: Empty string for the whole population; a slice id for a per-slice table.
    slice_id: str
    both_wrong: int
    primary_only_wrong: int
    alternate_only_wrong: int
    neither_wrong: int
    #: Cases with observations from only one of the two sources.  Not comparable.
    unpaired: int
    #: Cases where at least one source tied and so did not answer.  Excluded rather
    #: than broken by a coin toss, because a tie is a real operational outcome and
    #: assigning it a side would invent agreement or disagreement that was not observed.
    undecided: int
    #: Cases where the two sources returned different verdicts, right or wrong.  Kept
    #: separately from the error table because disagreement is observable without any
    #: reference label, which makes it the one figure here that a production system
    #: could monitor continuously.
    verdict_disagreements: int

    @property
    def decided(self) -> int:
        """Cases in the table.  The denominator for every rate below."""
        return (
            self.both_wrong
            + self.primary_only_wrong
            + self.alternate_only_wrong
            + self.neither_wrong
        )

    @property
    def primary_errors(self) -> int:
        return self.both_wrong + self.primary_only_wrong

    @property
    def alternate_errors(self) -> int:
        return self.both_wrong + self.alternate_only_wrong

    # --- the two conditionals the routing decision rests on -----------------------

    @property
    def alternate_correct_given_primary_wrong(self) -> Conditional:
        """The recovery rate: of the primary's mistakes, how many does the alternate get?

        This is the number that decides whether escalation can work at all.  At 0 the
        alternate is wrong wherever the primary is and routing cannot help however
        cheap it is.  Note that it says nothing about *cost*: a recovery rate of 1.0
        on a source that also fires false alarms everywhere is not a usable router.
        """
        return Conditional(
            "P(alternate correct | primary wrong)",
            self.primary_only_wrong,
            self.primary_errors,
        )

    @property
    def primary_correct_given_alternate_wrong(self) -> Conditional:
        """The reverse: what the primary still contributes once the alternate is wrong.

        The asymmetry between this and the recovery rate is what distinguishes
        "replace the primary" from "keep both".  If the alternate is simply better
        everywhere, this is near 0 and the primary adds nothing.
        """
        return Conditional(
            "P(primary correct | alternate wrong)",
            self.alternate_only_wrong,
            self.alternate_errors,
        )

    # --- shared error structure ---------------------------------------------------

    @property
    def joint_error_rate(self) -> Conditional:
        """Cases both sources get wrong, over all decided cases.

        The floor on any two-source system's error rate.  No routing policy, no
        repetition count and no threshold reduces it, because on these cases there is
        no correct answer available from either source at any budget.
        """
        return Conditional("joint error rate", self.both_wrong, self.decided)

    @property
    def primary_errors_shared(self) -> Conditional:
        """Fraction of the primary's errors the alternate also makes.

        The exact complement of the recovery rate -- ``1 - point`` of it, on the same
        denominator.  Both are reported because both get quoted in practice and a
        reader who sees only one tends to assume the other is independent evidence.
        It is not: there is one number here, stated twice.
        """
        return Conditional(
            "primary errors also made by alternate", self.both_wrong, self.primary_errors
        )

    @property
    def alternate_errors_shared(self) -> Conditional:
        return Conditional(
            "alternate errors also made by primary",
            self.both_wrong,
            self.alternate_errors,
        )

    @property
    def disagreement_rate(self) -> Conditional:
        return Conditional(
            "verdict disagreement", self.verdict_disagreements, self.decided
        )

    @property
    def error_association_phi(self) -> float | None:
        """Pearson phi for the 2x2 of (primary wrong) x (alternate wrong).

        Zero means the two sources' errors are unassociated -- which is the *favourable*
        case for routing, and is also the assumption a two-source system silently makes
        when it multiplies error rates together.  Positive means errors co-occur more
        than independence predicts, so the pair is worth less than the marginals
        suggest.

        ``None`` when either margin is degenerate: with no primary errors, or no
        alternate errors, the association is undefined rather than zero, and reporting
        0.0 there would read as "reassuringly independent" when it means "no data".

        Phi is a description of one table, not a test.  It has no p-value attached and
        none should be inferred; with the sample sizes this experiment is likely to
        have, the sampling distribution of phi is wide.
        """
        a, b = self.both_wrong, self.primary_only_wrong
        c, d = self.alternate_only_wrong, self.neither_wrong
        denominator = (a + b) * (c + d) * (a + c) * (b + d)
        if denominator == 0:
            return None
        return (a * d - b * c) / sqrt(denominator)

    @property
    def is_thin(self) -> bool:
        return self.decided < MIN_PAIRED_CASES


def paired_errors(cases: tuple[CaseRun, ...], slice_id: str = "") -> PairedErrors:
    """Build the table from case records.  No case is imputed and none is dropped silently."""
    both = primary_only = alternate_only = neither = 0
    unpaired = undecided = disagreements = 0

    for case in cases:
        if not case.runs or not case.has_alternate:
            unpaired += 1
            continue
        primary = _correct(case.majority_verdict, case.reference_label)
        alternate = _correct(case.alternate_majority_verdict, case.reference_label)
        if primary is None or alternate is None:
            undecided += 1
            continue
        if case.majority_verdict is not case.alternate_majority_verdict:
            disagreements += 1
        if primary and alternate:
            neither += 1
        elif primary:
            alternate_only += 1
        elif alternate:
            primary_only += 1
        else:
            both += 1

    return PairedErrors(
        slice_id=slice_id,
        both_wrong=both,
        primary_only_wrong=primary_only,
        alternate_only_wrong=alternate_only,
        neither_wrong=neither,
        unpaired=unpaired,
        undecided=undecided,
        verdict_disagreements=disagreements,
    )


@dataclass(frozen=True, slots=True)
class ComplementarityAnalysis:
    """The population table plus one per slice, and nothing that resembles a verdict."""

    run: CharacterizationRun
    overall: PairedErrors
    per_slice: tuple[PairedErrors, ...]

    @property
    def has_paired_data(self) -> bool:
        return self.overall.decided > 0

    @property
    def measured(self) -> bool:
        """Is this analysis evidence about a real alternate source?

        False for synthetic input.  Everything that renders or exports this analysis
        branches on it, because a table computed from generated observations and a
        table computed from collected ones are visually identical and mean nothing
        alike.
        """
        return self.has_paired_data and not self.run.synthetic

    @property
    def unsupported_conditionals(self) -> tuple[str, ...]:
        """Names of the statistics whose denominators are too small to act on."""
        return tuple(
            conditional.label
            for conditional in (
                self.overall.alternate_correct_given_primary_wrong,
                self.overall.primary_correct_given_alternate_wrong,
            )
            if not conditional.supported
        )


def analyse_complementarity(run: CharacterizationRun) -> ComplementarityAnalysis:
    return ComplementarityAnalysis(
        run=run,
        overall=paired_errors(run.cases),
        per_slice=tuple(
            paired_errors(run.in_slice(slice_id), slice_id) for slice_id in run.slices
        ),
    )
