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
    MIN_ERRORS_FOR_CONDITIONAL,
    MIN_PAIRED_CASES,
    ComplementarityAnalysis,
    Conditional,
    PairedErrors,
    required_paired_cases,
)
from .constraints import _hms
from .rationale import _interval

BANNER = "=" * 78

#: Printed in place of every empirical decision cell.  One spelling, so that grepping
#: for it finds all of them and a reader cannot mistake a blank for a measurement.
UNMEASURED = "UNMEASURED"


def _conditional(conditional: Conditional, prefix: str = "") -> str:
    """One proportion line, with its denominator and whether it supports anything."""
    if conditional.trials == 0:
        return f"  {prefix}{conditional.label:44} {UNMEASURED} (no cases in denominator)"
    point = conditional.point
    interval = conditional.interval
    support = (
        ""
        if conditional.supported
        else f"  << denominator {conditional.trials} < {MIN_ERRORS_FOR_CONDITIONAL}: "
        f"cannot be placed against 0.5"
    )
    assert point is not None and interval is not None
    return (
        f"  {prefix}{conditional.label:44} {point:.3f}  {_interval(interval)}  "
        f"n={conditional.trials}{support}"
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
        "",
    ]
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
        f"  needs {MIN_ERRORS_FOR_CONDITIONAL} primary errors of its own before its "
        f"figure can be distinguished from"
    )
    lines.append(
        "  the population figure. Slices are not folds: these are descriptive, and "
        "using them to"
    )
    lines.append(
        "  choose a routing threshold would fit the threshold on the data it is "
        "later scored on."
    )
    lines.append("")
    return lines


def _short(conditional: Conditional) -> str:
    """A slice cell.  Denominator-starved cells say so instead of printing a number."""
    if conditional.trials == 0:
        return "-"
    if not conditional.supported:
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
            "recovery rate above 0.5 with an interval that excludes it, joint error "
            "rate well below the primary's error rate, and phi near or below 0",
        ),
        (
            "Reject the alternate",
            "recovery rate indistinguishable from 0, or joint error rate close to the "
            "primary's error rate, or phi strongly positive",
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
    if analysis.unsupported_conditionals:
        lines.append("  Denominators too small to act on:")
        for label in analysis.unsupported_conditionals:
            lines.append(f"    {label}")
    lines.append("")
    return lines


def _shortfall(analysis: ComplementarityAnalysis) -> list[str]:
    """What it would take to fill the table in, computed from this study's own rates."""
    table = analysis.overall
    error_rate = table.primary_errors / table.decided if table.decided else 0.0
    needed = required_paired_cases(error_rate)
    lines = ["To unlock the decision:"]
    lines.append(
        f"  primary error rate on decided pairs     {error_rate:.3f} "
        f"({table.primary_errors} of {table.decided}, majority verdict vs reference)"
    )
    if needed is None:
        lines.append(
            "  The primary makes no errors here, so there is nothing for an alternate "
            "to recover and"
        )
        lines.append("  the routing question does not arise on this population.")
        lines.append("")
        return lines

    lines.append(
        f"  paired cases for {MIN_ERRORS_FOR_CONDITIONAL} primary errors     {needed}  "
        f"(this study has {table.decided}; shortfall "
        f"{max(0, needed - table.decided)})"
    )
    lines.append(
        f"  {MIN_ERRORS_FOR_CONDITIONAL} errors is a floor, and only sufficient if the "
        f"recovery rate comes out at 0.75 or better."
    )
    lines.append("  What the same error rate implies at less favourable recovery rates:")
    for rate, errors in ((0.70, 21), (0.60, 91)):
        lines.append(
            f"    recovery {rate:.2f}  needs {errors:>3} primary errors  "
            f"= {ceil(errors / error_rate)} paired cases"
        )
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
    lines += _per_slice(analysis)
    lines += _economics(analysis.run)
    lines += _stochasticity(analysis)
    lines += _shortfall(analysis)
    lines += _decision_table(analysis)
    return "\n".join(lines)
