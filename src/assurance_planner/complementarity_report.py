"""The alternate-source report.

Two rules, and the second is the reason this file is separate from
``benchmark_report.py``.

**Report the numbers, refuse the conclusion.**  Inherited from the benchmark report and
applied harder here.  The decision this analysis feeds -- replace the primary, keep both,
or reject the alternate -- is a choice between architectures, and the table at the bottom
of this report ships with every empirical cell reading ``UNMEASURED``.  There is no code
path in this module that writes anything else into those cells, because at the time of
writing there is no measured alternate source in this repository and a branch for the
case where there is would be a guess about what the evidence will look like.

**Sufficiency is relative to a declared threshold, never to a constant.**  Added after
the corpus red-team, which found that this report's support rule -- compare the recovery
rate to 0.5 -- was an economic assertion with no derivation, printed in the register of a
statistical one.  Where the break-even recovery actually sits is set by what the recovered
failure costs, how often it happens, and what the alternate charges to look; it can land
anywhere in [0, 1], and the sample size needed swings thirtyfold across that range.  The
report now prints the observation, the uncertainty, the declared threshold and the decision
as four separate lines, and when no threshold has been declared it says the evidence is not
decision-sufficient rather than falling back on one.

**Synthetic input is announced, not footnoted.**  A 2x2 built from generated verdicts
renders identically to one built from collected verdicts.  When the run is marked
synthetic the report opens with a banner, every rate line is prefixed, and the
interpretation section is replaced with a statement that the numbers describe the
generator.  The cost of this being loud is that it looks alarmist; the cost of it being
quiet is that a table gets pasted into a decision.
"""

from __future__ import annotations

from math import ceil
from statistics import fmean

from .characterization import Characterization, CharacterizationRun
from .complementarity import (
    MIN_PAIRED_CASES,
    POINT_ESTIMATE_FLOOR,
    ComplementarityAnalysis,
    Conditional,
    PairedErrors,
    Sufficiency,
    errors_to_decide,
    required_paired_cases,
)
from .constraints import _hms
from .rationale import _interval

BANNER = "=" * 78

#: Printed in place of every empirical decision cell.  One spelling, so that grepping
#: for it finds all of them and a reader cannot mistake a blank for a measurement.
UNMEASURED = "UNMEASURED"


def _conditional(conditional: Conditional, prefix: str = "") -> str:
    """One proportion line: the estimate, its interval, and its denominator.

    Carries no sufficiency claim.  Whether a denominator is large enough depends on the
    threshold the number is being read against, which is not this function's business
    and for most of these statistics does not exist.
    """
    if conditional.trials == 0:
        return f"  {prefix}{conditional.label:44} {UNMEASURED} (no cases in denominator)"
    point = conditional.point
    interval = conditional.interval
    warning = (
        f"  << n < {POINT_ESTIMATE_FLOOR}: quote the interval, not the point"
        if conditional.thin_denominator
        else ""
    )
    assert point is not None and interval is not None
    return (
        f"  {prefix}{conditional.label:44} {point:.3f}  {_interval(interval)}  "
        f"n={conditional.trials}{warning}"
    )


def _identity(run: CharacterizationRun) -> list[str]:
    return [
        "Sources:",
        f"  primary    {run.evaluator_version}",
        f"  alternate  {run.alternate_version or UNMEASURED + ' (none named)'}",
        f"  failure mode        {run.failure_mode}",
        f"  population          {run.population_id}",
        f"  measured against    {run.distribution_id}",
        f"  measured on         {run.measured_on or UNMEASURED}",
        "",
    ]


def _coverage(analysis: ComplementarityAnalysis) -> list[str]:
    """How much of the population actually has a paired observation."""
    table, run = analysis.overall, analysis.run
    lines = [
        "Pairing coverage:",
        f"  cases in study                 {len(run.cases)}",
        f"  paired with the alternate      {len(run.paired_cases)}",
        f"  never sent to the alternate    {table.unpaired}",
        f"  dropped: a source tied         {table.undecided}",
        f"  in the error table             {table.decided}",
    ]
    if table.unpaired:
        lines.append(
            "  Unpaired cases are excluded, not counted as agreement. A partially "
            "paired study measures"
        )
        lines.append(
            "  complementarity on whatever subset was sent, which is only the "
            "population if the subset"
        )
        lines.append("  was chosen without reference to the primary's behaviour.")
    if table.is_thin:
        lines.append(
            f"  THIN: fewer than {MIN_PAIRED_CASES} decided pairs; every rate below "
            f"is noise."
        )
    lines.append("")
    return lines


def _marginals(
    primary: Characterization, alternate: Characterization | None
) -> list[str]:
    """Each source scored on its own, over the paired cases only.

    Necessary but not sufficient, and printed above the 2x2 rather than below it so
    that a reader meets the aggregate first and then sees what it failed to say.
    """
    lines = ["Marginal accuracy, each source alone (paired cases only):"]
    lines.append("  source     sensitivity          false-positive rate")
    for label, analysis in (("primary", primary), ("alternate", alternate)):
        if analysis is None:
            lines.append(f"  {label:10} {UNMEASURED}")
            continue
        sens, fpr = analysis.sensitivity, analysis.false_positive_rate
        lines.append(
            f"  {label:10} {sens.point:.3f} {_interval(sens.naive_interval)}  "
            f"{fpr.point:.3f} {_interval(fpr.naive_interval)}"
        )
    lines.append(
        "  Intervals are i.i.d. Wilson over observations. A source with better "
        "marginals can still"
    )
    lines.append(
        "  be useless for routing, and a source with worse marginals can still be "
        "valuable; that is"
    )
    lines.append("  what the table below is for.")
    lines.append("")
    return lines


def _table(table: PairedErrors) -> list[str]:
    return [
        "Paired error table:",
        "                            alternate correct   alternate wrong",
        f"  primary correct           {table.neither_wrong:>13}   "
        f"{table.alternate_only_wrong:>15}",
        f"  primary wrong             {table.primary_only_wrong:>13}   "
        f"{table.both_wrong:>15}",
        f"  primary errors {table.primary_errors}, alternate errors "
        f"{table.alternate_errors}, over {table.decided} decided pairs",
        "",
    ]


def _statistics(analysis: ComplementarityAnalysis) -> list[str]:
    table = analysis.overall
    phi = table.error_association_phi
    lines = [
        "Complementarity statistics:",
        _conditional(table.alternate_correct_given_primary_wrong),
        _conditional(table.primary_correct_given_alternate_wrong),
        _conditional(table.joint_error_rate),
        _conditional(table.primary_errors_shared),
        _conditional(table.alternate_errors_shared),
        _conditional(table.disagreement_rate),
        f"  {'error association (Pearson phi)':44} "
        + (f"{phi:+.3f}" if phi is not None else f"{UNMEASURED} (a margin is empty)"),
        "  phi is a description of one table and carries no p-value. 0 means the two "
        "sources' errors",
        "  are unassociated, which is the favourable case for routing and is also what "
        "a two-source",
        "  system assumes when it multiplies error rates. Positive means errors "
        "co-occur, so the pair",
        "  is worth less than the marginals suggest.",
        "  'primary errors also made by alternate' is 1 minus the recovery rate on the "
        "same denominator.",
        "  Both are printed because both get quoted; they are one number, not two.",
        #: A disclosed gap, not a check.  Nothing in the schema records how the cases
        #: were sampled, and no arithmetic can recover it: a corpus of hand-picked
        #: primary failures and a representative corpus of a bad primary produce the
        #: same table.  So the warning is unconditional.  Printing it only above some
        #: error-rate threshold would be the mistake this report was just corrected for
        #: -- an unjustified constant deciding what the reader is told.
        "  Two figures above assume the cases were sampled without reference to either "
        "source's outcome,",
        "  and the instrument cannot verify that. Phi is not invariant to "
        "outcome-dependent sampling, so",
        "  on a corpus enriched with known primary failures -- or on one pooled from an "
        "enriched corpus",
        "  and a representative one -- it estimates nothing. And where every case has "
        "the primary wrong,",
        "  the sources disagree exactly when the alternate is right, so the "
        "disagreement rate and the",
        "  recovery rate become the same number under two names. See section 9.3 of",
        "  docs/alternate_source_collection_protocol.md.",
        "",
    ]
    return lines


#: What each outcome means, kept next to the enum rather than inline so the four
#: branches are readable side by side.
_SUFFICIENCY_TEXT = {
    Sufficiency.NO_DATA: (
        "no primary errors in the table, so there is nothing for the alternate to "
        "recover and nothing to decide"
    ),
    Sufficiency.UNDECLARED: (
        "NOT DECISION-SUFFICIENT. The statistics above are descriptive only. No "
        "break-even recovery was declared, so nothing states what this study would have "
        "to show to change a decision, and an interval cannot be decisive about a "
        "question nobody asked"
    ),
    Sufficiency.ABOVE: (
        "the whole interval lies above the declared break-even: at this break-even the "
        "recovery evidence is decisive in favour"
    ),
    Sufficiency.BELOW: (
        "the whole interval lies below the declared break-even: at this break-even the "
        "recovery evidence is decisive against"
    ),
    Sufficiency.INCONCLUSIVE: (
        "the interval spans the declared break-even, so this study does not settle it "
        "either way"
    ),
}


def _sufficiency(analysis: ComplementarityAnalysis) -> list[str]:
    """Observation, uncertainty, declared threshold, decision -- four separate lines.

    They are separated because they are four different kinds of thing, and collapsing
    them is how an economic threshold gets mistaken for a statistical one.  The first
    two are measurements.  The third is a policy input and is labelled as one.  Only the
    fourth is a claim, and it is a claim *relative to* the third rather than an absolute.
    """
    recovery = analysis.overall.alternate_correct_given_primary_wrong
    threshold = analysis.break_even_recovery
    verdict = analysis.recovery_sufficiency
    point, interval = recovery.point, recovery.interval

    lines = ["Is the recovery evidence sufficient to decide?"]
    lines.append(
        f"  observed recovery              "
        + (f"{point:.3f}" if point is not None else UNMEASURED)
    )
    lines.append(
        f"  statistical uncertainty        "
        + (
            f"{_interval(interval)} 95% Wilson, n={recovery.trials} primary errors"
            if interval is not None
            else f"{UNMEASURED} (no primary errors)"
        )
    )
    lines.append(
        f"  declared break-even r*         "
        + (
            f"{threshold:.3f}  (POLICY INPUT, not measured here)"
            if threshold is not None
            #: Deliberately not UNMEASURED.  r* is never measured by anyone; it is
            #: declared or it is missing, and calling it unmeasured would file a policy
            #: input under the same heading as an empirical gap.
            else "UNDECLARED  (none supplied; this is an input, not a measurement)"
        )
    )
    lines.append(f"  decision support               {_SUFFICIENCY_TEXT[verdict]}")
    lines.append(
        "  r* is where escalating to the alternate begins to pay for itself. It is set "
        "by the"
    )
    lines.append(
        "  consequence of the failure recovered, how often it occurs, what the "
        "alternate costs to"
    )
    lines.append(
        "  invoke, what its own false alarms cost, and the latency budget. It is not a "
        "statistical"
    )
    lines.append(
        "  quantity and this module does not compute it. An earlier version of this "
        "report compared"
    )
    lines.append(
        "  the recovery rate to 0.5 and called that a support rule; 0.5 was an "
        "undeclared economic"
    )
    lines.append(
        "  assumption, and it has been removed rather than replaced with a different "
        "constant."
    )
    lines.append("")
    return lines


def _per_slice(analysis: ComplementarityAnalysis) -> list[str]:
    lines = [
        "Per slice:",
        "  slice                      pairs  P(alt ok | pri wrong)  joint err  disagree",
    ]
    for table in analysis.per_slice:
        recovery = table.alternate_correct_given_primary_wrong
        joint = table.joint_error_rate
        disagree = table.disagreement_rate
        lines.append(
            f"  {table.slice_id or '(unsliced)':26} {table.decided:>5}  "
            f"{_short(recovery):>21}  {_short(joint):>9}  {_short(disagree):>8}"
        )
    lines.append(
        "  A slice-level recovery rate is what a routing selector would key on, and "
        "every slice here"
    )
    lines.append(
        "  needs enough primary errors of its own to be distinguished from the "
        "population figure --"
    )
    lines.append(
        "  how many depends on the declared r* and on how far the slice sits from it, "
        "not on a"
    )
    lines.append(
        "  constant. Slices are not folds: these are descriptive, and using them to "
        "choose a routing"
    )
    lines.append("  threshold would fit the threshold on the data it is later scored on.")
    lines.append("")
    return lines


def _short(conditional: Conditional) -> str:
    """A slice cell.  Parenthesised when the point estimate must not travel alone."""
    if conditional.trials == 0:
        return "-"
    if conditional.thin_denominator:
        return f"({conditional.point:.2f} n={conditional.trials})"
    return f"{conditional.point:.3f} n={conditional.trials}"


def _economics(run: CharacterizationRun) -> list[str]:
    """Observed cost and latency, or the word UNKNOWN.

    Deliberately not backed by a default.  The cost model in ``policies.py`` carries a
    placeholder price for the alternate, and reading it here would produce a cost
    comparison that looks measured and is not.
    """
    lines = ["Cost and latency, as recorded by the harness:"]
    for label, costs, latencies in (
        (
            "primary",
            [v for c in run.paired_cases for v in c.costs_usd],
            [v for c in run.paired_cases for v in c.latencies_ms],
        ),
        (
            "alternate",
            [v for c in run.paired_cases for v in c.alternate_costs_usd],
            [v for c in run.paired_cases for v in c.alternate_latencies_ms],
        ),
    ):
        cost_text = (
            f"${fmean(costs):.4f}/observation over {len(costs)} observations"
            if costs
            else f"{UNMEASURED}: no per-observation cost recorded"
        )
        latency_text = (
            f"{_hms(fmean(latencies) / 1000.0)} mean, "
            f"{_hms(max(latencies) / 1000.0)} worst"
            if latencies
            else f"{UNMEASURED}: no per-observation latency recorded"
        )
        lines.append(f"  {label:10} cost     {cost_text}")
        lines.append(f"  {label:10} latency  {latency_text}")
    lines.append(
        "  No figure here is filled in from a declared price. An escalation policy "
        "priced from a"
    )
    lines.append(
        "  placeholder is a policy whose cost advantage is a property of the "
        "placeholder."
    )
    lines.append("")
    return lines


def _stochasticity(analysis: ComplementarityAnalysis) -> list[str]:
    """Whether the alternate was observed more than once, and what that bought.

    Repetition reduces the variance of a stochastic source.  It does not move a source
    off a case it is systematically wrong about, and the point of separating the two
    here is that a source with a high recovery rate driven by noise will not hold it
    under repetition, while one driven by a genuinely different failure boundary will.
    """
    paired = analysis.run.paired_cases
    repeated = [c for c in paired if c.alternate_runs >= 2]
    lines = ["Alternate stochasticity:"]
    if not paired:
        lines += ["  " + UNMEASURED + ": no paired observations", ""]
        return lines
    runs = fmean([c.alternate_runs for c in paired])
    lines.append(f"  observations per case          {runs:.2f} mean")
    if not repeated:
        lines.append(
            "  SINGLE OBSERVATION: within-alternate variance is unmeasured. Every "
            "figure above treats"
        )
        lines.append(
            "  one draw as the alternate's verdict, so an alternate that is merely "
            "noisy and one that"
        )
        lines.append(
            "  is reliably different from the primary are indistinguishable in this "
            "study."
        )
    else:
        unstable = [c for c in repeated if c.alternate_disagreement_rate > 0.0]
        lines.append(
            f"  cases with >=2 observations    {len(repeated)} of {len(paired)}"
        )
        lines.append(
            f"  mean within-case disagreement  "
            f"{fmean(c.alternate_disagreement_rate for c in repeated):.3f}"
        )
        lines.append(
            f"  cases the alternate answered inconsistently   {len(unstable)}"
        )
        lines.append(
            "  Repetition can shrink the uncertainty in these rates. It cannot repair "
            "a systematic"
        )
        lines.append(
            "  disagreement with the reference label, and the cases in the "
            "both-wrong cell are"
        )
        lines.append("  evidence about the second thing, not the first.")
    lines.append("")
    return lines


def _decision_table(analysis: ComplementarityAnalysis) -> list[str]:
    """The three-way decision, with every empirical cell unfilled.

    The rows are the decision; the middle column is what would have to be true; the
    last column is the state of the evidence.  Every cell in that column is
    ``UNMEASURED`` and no code here can write anything else into it.
    """
    rows = (
        (
            "Replace the primary",
            "alternate dominates on both marginals, and "
            "P(primary correct | alternate wrong) is near 0",
        ),
        (
            "Keep both, route selectively",
            "a declared break-even recovery r*, an interval lying entirely above it, "
            "joint error rate well below the primary's error rate, and phi near or "
            "below 0",
        ),
        (
            "Reject the alternate",
            "an interval lying entirely below the declared r*, or joint error rate "
            "close to the primary's error rate, or phi strongly positive",
        ),
    )
    lines = ["Decision:"]
    for decision, condition in rows:
        lines.append(f"  {decision:30} {UNMEASURED}")
        lines.append(f"    requires: {condition}")
    lines.append("")
    lines.append(
        f"  Every cell reads {UNMEASURED} because this run is not backed by an "
        f"alternate qualification"
    )
    lines.append(
        "  artifact derived from collected observations. That is a statement about the "
        "evidence, not"
    )
    lines.append(
        "  a hedge: the three outcomes are equally acceptable and none of them has "
        "support yet."
    )
    if not analysis.decisive:
        lines.append(
            f"  Recovery evidence: {analysis.recovery_sufficiency.value}. A decisive "
            f"result here would"
        )
        lines.append(
            "  fill one row and not the others; it would not fill them all, and it "
            "would still need"
        )
        lines.append("  the marginals and the economics to reach a decision.")
    if analysis.thin_denominators:
        lines.append(
            f"  Denominators under {POINT_ESTIMATE_FLOOR}; do not quote these point "
            f"estimates without their intervals:"
        )
        for label in analysis.thin_denominators:
            lines.append(f"    {label}")
    lines.append("")
    return lines


def _shortfall(analysis: ComplementarityAnalysis) -> list[str]:
    """What it would take to fill the table in, computed from this study's own rates."""
    table = analysis.overall
    error_rate = table.primary_errors / table.decided if table.decided else 0.0
    lines = ["To unlock the decision:"]
    lines.append(
        f"  primary error rate on decided pairs     {error_rate:.3f} "
        f"({table.primary_errors} of {table.decided}, majority verdict vs reference)"
    )
    if error_rate <= 0.0:
        lines.append(
            "  The primary makes no errors here, so there is nothing for an alternate "
            "to recover and"
        )
        lines.append("  the routing question does not arise on this population.")
        lines.append("")
        return lines

    recovery = table.alternate_correct_given_primary_wrong.point
    threshold = analysis.break_even_recovery
    if threshold is None or recovery is None:
        lines.append(
            "  The sample size needed cannot be computed, because it is a function of "
            "the gap between"
        )
        lines.append(
            "  the observed recovery and the break-even recovery, and no break-even "
            "has been declared."
        )
        lines.append(
            "  Declare one and this section will size the study. The gap dominates: at "
            "an observed"
        )
        lines.append(
            "  recovery of 0.60, clearing a break-even of 0.20 takes 3 primary errors "
            "and clearing"
        )
        lines.append(
            "  0.50 takes 91 -- a thirtyfold difference in study cost set entirely by "
            "an input this"
        )
        lines.append("  study has not been given.")
        lines.append("  See docs/alternate_source_collection_protocol.md.")
        lines.append("")
        return lines

    errors = errors_to_decide(recovery, threshold)
    if errors is None:
        lines.append(
            f"  The observed recovery {recovery:.3f} sits on the declared break-even "
            f"{threshold:.3f}. No sample"
        )
        lines.append(
            "  size resolves that: an interval cannot exclude the point it is centred "
            "on. The study"
        )
        lines.append(
            "  cannot be made decisive by collecting more of the same; the break-even "
            "has to move,"
        )
        lines.append("  which is an economic question and not one this report can answer.")
        lines.append("  See docs/alternate_source_collection_protocol.md.")
        lines.append("")
        return lines

    needed = required_paired_cases(error_rate, errors)
    assert needed is not None
    direction = "above" if recovery > threshold else "below"
    lines.append(
        f"  to place {recovery:.3f} {direction} r*={threshold:.3f}      "
        f"{errors} primary errors"
    )
    lines.append(
        f"  representative cases for {errors} errors      {needed}  "
        f"(this study has {table.decided}; shortfall "
        f"{max(0, needed - table.decided)})"
    )
    lines.append(
        "  Both figures move with r*. What the same observed recovery would cost "
        "against other"
    )
    lines.append("  break-evens, at this study's primary error rate:")
    for candidate in (0.10, 0.20, 0.30, 0.50):
        alternative = errors_to_decide(recovery, candidate)
        if alternative is None:
            continue
        cases = required_paired_cases(error_rate, alternative)
        lines.append(
            f"    r*={candidate:.2f}  {alternative:>4} primary errors  "
            f"= {cases} representative cases"
        )
    lines.append(
        "  Those are illustrations of the sensitivity, not candidate thresholds. Only "
        "the declared"
    )
    lines.append("  r* above is the one this study is being read against.")
    lines.append("  See docs/alternate_source_collection_protocol.md.")
    lines.append("")
    return lines


def render_complementarity(
    analysis: ComplementarityAnalysis,
    primary: Characterization,
    alternate: Characterization | None,
) -> str:
    lines: list[str] = []
    if analysis.run.synthetic:
        lines += [
            BANNER,
            "SYNTHETIC DATA. These observations were generated, not collected.",
            "",
            "Every rate, interval and table below describes the generator that produced "
            "this file.",
            "None of it is evidence about any real alternate source, and no number here "
            "may be quoted",
            "as a measured property of one. The file exists to exercise the analysis "
            "code on input whose",
            "structure is known in advance; that is the only claim it supports.",
            BANNER,
            "",
        ]
    if not analysis.has_paired_data:
        lines += [
            "No paired observations.",
            "",
            "This study contains verdicts from one source only, so there is no error "
            "table to build.",
            "Complementarity is not low here and it is not high; it is unmeasured, and "
            "the difference",
            "matters because an unmeasured quantity cannot be improved by a better "
            "policy.",
            "",
        ]
        lines += _identity(analysis.run)
        lines += _decision_table(analysis)
        return "\n".join(lines)

    lines += _identity(analysis.run)
    lines += _coverage(analysis)
    lines += _marginals(primary, alternate)
    lines += _table(analysis.overall)
    lines += _statistics(analysis)
    lines += _sufficiency(analysis)
    lines += _per_slice(analysis)
    lines += _economics(analysis.run)
    lines += _stochasticity(analysis)
    lines += _shortfall(analysis)
    lines += _decision_table(analysis)
    return "\n".join(lines)
