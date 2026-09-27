"""The policy-comparison report.

Kept separate from ``rationale.py`` because it renders a different kind of thing.
``rationale`` explains one plan the planner chose; this explains a comparison the
planner took no part in, and the two should not grow into each other.

One rule governs everything below: **report the numbers, refuse the conclusion.**
There is no "recommended policy" line.  Choosing inside the Pareto set requires a
price for a missed failure, and nothing in this package knows that price.  Every
assumption that could flatter a policy -- escalation accuracy, call latency,
parallelism -- is printed next to the numbers it produced.
"""

from __future__ import annotations

from .benchmark import (
    AllocationDiagnostic,
    BetaBinomialFit,
    LeakageReport,
    MarginalPoint,
    PolicyResult,
    SliceDiagnostic,
    pareto_front,
)
from .characterization import Characterization, CharacterizationRun
from .constraints import _hms
from .policies import CostModel
from .rationale import _interval


def _rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _bounds(bounds: tuple[float, float] | None) -> str:
    return "[n/a]" if bounds is None else _interval(bounds)


def _identity(run: CharacterizationRun) -> list[str]:
    positives = sum(1 for c in run.cases if c.reference_label)
    return [
        "Dataset and evaluator identity:",
        f"  evaluator            {run.evaluator_version}",
        f"  failure mode         {run.failure_mode}",
        f"  population           {run.population_id}",
        f"  behaviour            {run.distribution_id}",
        f"  measured on          {run.measured_on or 'undated'}",
        f"  characterization run {run.run_id}",
        f"  cases                {len(run.cases)} ({positives} reference-positive, "
        f"{len(run.cases) - positives} reference-negative)",
        "",
    ]


def _characterization(analysis: Characterization) -> list[str]:
    sensitivity, fpr = analysis.sensitivity, analysis.false_positive_rate
    planner_n = analysis.planner_replications()
    return [
        "Characterization summary (pooled, and therefore describing no individual case):",
        f"  sensitivity          {sensitivity.point:.3f}  "
        f"iid {_interval(sensitivity.naive_interval)}  "
        f"clustered {_interval(sensitivity.corrected_interval)}",
        f"  false-positive rate  {fpr.point:.3f}  "
        f"iid {_interval(fpr.naive_interval)}  "
        f"clustered {_interval(fpr.corrected_interval)}",
        (
            f"  planner would choose n={planner_n} from these two numbers alone"
            if planner_n
            else "  planner would choose  no n meets the target"
        ),
        "",
    ]


def _slices(rows: tuple[SliceDiagnostic, ...]) -> list[str]:
    lines = [
        "Heterogeneity by slice:",
        "  slice                  cases  reps  disagree  maj.agrees  contested  "
        "unanimous+wrong",
    ]
    for row in rows:
        lines.append(
            f"  {row.slice_id:22} {row.cases:5d}  {row.mean_repetitions:4.1f}  "
            f"{row.mean_disagreement:8.3f}  {row.majority_agrees:10d}  "
            f"{row.contested:9d}  {row.unanimous_and_wrong:15d}"
        )
    lines.append(
        "  'unanimous+wrong' is the column that matters. Those cases look maximally "
        "certain and are"
    )
    lines.append(
        "  wrong, so every repetition spent on them buys confidence and no accuracy. No "
        "run-time signal"
    )
    lines.append("  separates them from the unanimous-and-right ones.")
    lines.append("")
    return lines


def _design(leakage: LeakageReport) -> list[str]:
    lines = [
        "Held-out design:",
        f"  {leakage.folds}-fold slice-stratified split; every case is scored by a "
        f"policy calibrated without it",
    ]
    if leakage.overlapping_case_ids:
        lines.append(
            f"  LEAKAGE: {len(leakage.overlapping_case_ids)} case(s) appear on both "
            f"sides of a fold. These results are invalid."
        )
    else:
        lines.append(
            "  no case appears on both sides of any fold (recomputed here, not assumed)"
        )
    if leakage.untested_case_ids:
        lines.append(
            f"  {len(leakage.untested_case_ids)} case(s) were never held out, and so "
            f"were never tested"
        )
    if leakage.thin_calibration_slices:
        lines.append(
            "  too little calibration to route on, in at least one fold: "
            + ", ".join(leakage.thin_calibration_slices)
        )
        lines.append(
            "  a triage policy falls through to the standard rule on those, by design"
        )
    lines.append("")
    return lines


def _costs(cost: CostModel) -> list[str]:
    return [
        "Cost model (assumptions, not measurements):",
        f"  judge      ${cost.judge_cost_usd:.4f}/call, "
        f"{_hms(cost.judge_latency_seconds)}/call, parallelism {cost.judge_parallelism}",
        f"  alternate  ${cost.alternate_cost_usd:.4f}/case, "
        f"{_hms(cost.alternate_latency_seconds)}/case, sensitivity "
        f"{cost.alternate.sensitivity:.2f}, FPR "
        f"{cost.alternate.false_positive_rate:.2f}",
        f"             {cost.alternate.provenance}",
        f"  human      ${cost.human_cost_usd:.2f}/case, "
        f"{_hms(cost.human_latency_seconds)}/case, treated as the reference label",
        "  No human observations exist in this dataset. An escalated case contributes",
        "  *expected* error from the rates above, which is why error counts can be "
        "fractional.",
        "",
    ]


def _comparison(results: tuple[PolicyResult, ...]) -> list[str]:
    lines = [
        "Policy comparison (held out):",
        "  policy                         FN     FP  unres   esc  human   calls  mean "
        "  p95      cost  eval-time   wall",
    ]
    for r in results:
        lines.append(
            f"  {r.policy:26} {r.false_negatives:6.2f} {r.false_positives:6.2f} "
            f"{r.unresolved:6d} {r.escalations:5d} {r.human_reviews:6d} "
            f"{r.judge_calls:7d} {r.mean_calls:5.2f} {r.p95_calls:5.0f} "
            f"{r.cost_usd:9.2f}  {_hms(r.evaluator_seconds):>9}  "
            f"{_hms(r.wall_clock_seconds):>5}"
        )
    lines.extend(
        [
            "  FN and FP denominators are the reference positives and negatives *that "
            "were answered*.",
            "  'unres' is cases nobody answered; it is deliberately not folded into an "
            "accuracy figure.",
            "  'blind_escalation_*' is a control, not a proposal. It escalates as many "
            "cases as the most",
            "  escalation-heavy policy above, chosen by a hash of the case id, so it "
            "knows nothing about the",
            "  case. If it matches a policy that targets its escalations, that targeting "
            "is buying nothing.",
            "  'eval-time' is total evaluator occupancy. 'wall' is the slowest single "
            "case, assuming cases run",
            "  concurrently. Real elapsed time lies between them and depends on "
            "infrastructure not modelled here.",
            "",
            "  Rates over answered cases; intervals over judge-decided cases only, "
            "because escalated cases",
            "  have no sample behind them:",
        ]
    )
    for r in results:
        lines.append(
            f"    {r.policy:26} sensitivity {_rate(r.sensitivity):>7} "
            f"{_bounds(r.sensitivity_interval_judge_only):>16}   "
            f"specificity {_rate(r.specificity):>7} "
            f"{_bounds(r.specificity_interval_judge_only):>16}"
        )
    truncated = [r for r in results if r.truncated_cases]
    if truncated:
        lines.append("")
        for r in truncated:
            lines.append(
                f"  {r.policy}: {r.truncated_cases} case(s) recorded fewer observations "
                f"than this policy wanted to spend"
            )
    lines.append("")
    return lines


def _pareto(results: tuple[PolicyResult, ...]) -> list[str]:
    front = pareto_front(results)
    lines = ["Pareto set on (false negatives, false positives, unresolved, cost):"]
    lines.extend(f"  {name}" for name in front)
    dominated = [r.policy for r in results if r.policy not in front]
    if dominated:
        lines.append(
            f"  dominated: {', '.join(dominated)} -- some other policy is at least as "
            f"good on all four axes"
        )
    lines.extend(
        [
            "  Latency is excluded from the dominance test on purpose: with two "
            "defensible time figures,",
            "  including either would silently pick a parallelism assumption.",
            "  No policy is recommended. Choosing inside this set requires a price for a "
            "missed failure,",
            "  which is policy, not measurement.",
            "",
        ]
    )
    return lines


def _marginal(points: tuple[MarginalPoint, ...]) -> list[str]:
    lines = [
        "Marginal value of repetition (majority vote at n, every case, no held-out "
        "split needed):",
        "    n     FN     FP  unres   calls   errors avoided by the nth   extra calls",
    ]
    for point in points:
        lines.append(
            f"  {point.observations:3d}  {point.false_negatives:5.1f}  "
            f"{point.false_positives:5.1f}  {point.unresolved:5d}  "
            f"{point.judge_calls:6d}   {point.errors_avoided:+22.1f}   "
            f"{point.incremental_calls:11d}"
        )
    lines.extend(
        [
            "  At even n an exact tie is unresolved, so errors fall and abstentions "
            "rise. Odd and even rows are",
            "  not directly comparable, and the zig-zag is the vote rule rather than "
            "noise in the data.",
            "",
        ]
    )
    return lines


def _allocation(rows: tuple[AllocationDiagnostic, ...]) -> list[str]:
    lines = [
        "Where the saving comes from (held out):",
        "  'contested' means the judge disagreed with itself at least once on that "
        "case. A policy whose",
        "  advantage lives entirely in the uncontested column has not allocated "
        "anything; it has noticed",
        "  that easy cases are easy, which early stopping already does.",
        "  policy                     uncontested: calls  errors | contested: calls  "
        "errors  escalations",
    ]
    for row in rows:
        lines.append(
            f"  {row.policy:26}             {row.uncontested_calls:5d}  "
            f"{row.uncontested_errors:6.2f} |            {row.contested_calls:5d}  "
            f"{row.contested_errors:6.2f}  {row.contested_escalations:11d}"
        )
    if rows:
        lines.append(
            f"  ({rows[0].uncontested_cases} uncontested cases, "
            f"{rows[0].contested_cases} contested)"
        )
    lines.append("")
    return lines


def _fits(fits: tuple[BetaBinomialFit, BetaBinomialFit]) -> list[str]:
    lines = [
        "Beta-Binomial comparator (method of moments, fitted per reference label):"
    ]
    for label, fit in zip(("reference-positive", "reference-negative"), fits):
        if fit.alpha is None or fit.beta is None or fit.intraclass_correlation is None:
            lines.append(
                f"  {label:20} no fit: {fit.cases} usable case(s), or observed spread "
                f"at or below independent trials"
            )
            continue
        quality = fit.fit_quality
        lines.append(
            f"  {label:20} cases {fit.cases:3d}  mean {fit.mean:.3f}  "
            f"alpha {fit.alpha:.3f}  beta {fit.beta:.3f}  intra-case correlation "
            f"{fit.intraclass_correlation:.3f}"
        )
        lines.append(
            f"  {'':20} unanimous cases: {fit.unanimous_observed} observed vs "
            f"{fit.unanimous_predicted:.1f} predicted"
            + ("" if quality is None else f" (ratio {quality:.2f})")
        )
    lines.extend(
        [
            "  The correlation figure is a second opinion on the same clustering the "
            "dispersion statistic already",
            "  reports more cheaply. The unanimity ratio was built to detect a mixed "
            "population and does not:",
            "  it sits near 1 on every fixture in data/, including the one constructed "
            "to be a mixture. That is",
            "  recorded as a negative result, not as evidence of homogeneity.",
            "  Neither figure distinguishes confidently-right from confidently-wrong. "
            "Only the reference label does.",
        ]
    )
    return lines


def render_benchmark(
    run: CharacterizationRun,
    analysis: Characterization,
    results: tuple[PolicyResult, ...],
    leakage: LeakageReport,
    marginal: tuple[MarginalPoint, ...],
    slices: tuple[SliceDiagnostic, ...],
    allocation: tuple[AllocationDiagnostic, ...],
    fits: tuple[BetaBinomialFit, BetaBinomialFit],
    warnings: tuple[str, ...],
    cost: CostModel,
) -> str:
    lines: list[str] = []
    lines.extend(_identity(run))
    lines.extend(_characterization(analysis))
    lines.extend(_slices(slices))
    lines.extend(_design(leakage))
    lines.extend(_costs(cost))
    lines.extend(_comparison(results))
    lines.extend(_pareto(results))
    lines.extend(_marginal(marginal))
    lines.extend(_allocation(allocation))
    lines.extend(_fits(fits))
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in warnings)
    if run.note:
        lines.append("")
        lines.append(f"Data note: {run.note}")
    return "\n".join(lines)
