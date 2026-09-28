"""Phase 1 of the pre-inference audit: is pooled phi an operating-point artifact?

`docs/agent_reward_bench_directional.md` §8 recorded that pooled Pearson phi orders the
eight alternates almost exactly as their own failure-sensitivity does, and raised the
possibility that phi is measuring threshold alignment rather than mechanism-level error
dependence.  That is a falsifiable claim about a statistic the repository leans on, and
it costs nothing to test, because conditioning on the reference label does not need new
judgments -- it needs the eight-cell table already written by ``arb_directional.py``.

Conditioning is the right test because within a reference class there is only one way to
be wrong.  On a reference-success case neither evaluator can miss a failure; both can only
false-alarm.  On a reference-failure case neither can false-alarm; both can only miss.  So
a within-class association is an association between two evaluators making *the same kind*
of mistake, which is what "do their errors co-occur" was always supposed to mean.  Pooled
phi mixes the two and additionally mixes in the fact that the two classes have wildly
different error rates, which is exactly the channel through which an operating point could
masquerade as a dependence.

Two association measures, reported side by side and for a reason:

  - **phi** is what the repository already quotes, so it has to appear or the comparison
    is not a comparison.  It is bounded by its margins: a 2x2 with a 4% marginal error
    rate cannot reach the phi that a 44% one can, even at identical odds.  Comparing phi
    across strata with different error rates is therefore partly comparing the strata.
  - **the odds ratio** is invariant to those margins, which is the whole reason for
    carrying a second statistic rather than one.  Where phi and the odds ratio disagree
    about which stratum is more associated, the disagreement is diagnostic rather than a
    nuisance, and it is reported rather than resolved by preferring one.

Undefined stays undefined.  An odds ratio with an empty cell is not "1.0" and a phi with
a degenerate margin is not "0.0"; both read as reassuring independence when they mean no
information.  Nothing here is continuity-corrected into existence.

Usage:
    python scripts/arb_import.py --tier-c
    python scripts/arb_conditional_association.py
"""

import csv
import os
import sys
import tempfile
from math import sqrt

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
WORKDIR = os.environ.get("ARB_WORKDIR") or tempfile.gettempdir()
sys.path.insert(0, os.path.join(REPO, "src"))

from assurance_planner.complementarity import Conditional  # noqa: E402

sys.path.insert(0, HERE)
from arb_directional import ALTERNATES, PRIMARY, Cells, fmt, load_pair, phi  # noqa: E402


def risk_ratio(both_wrong, primary_only, alternate_only, neither):
    """How much likelier the alternate is to err on a case the primary got wrong.

    Plain arithmetic on the same four cells, carried because it is the one number here
    that states the dependence without a reader having to know what a phi of +0.25 is
    worth: the alternate's error rate among the primary's errors, over its error rate
    among the cases the primary got right.  1.0 is independence; nothing is read into
    how far above 1.0 it lands beyond ordering.
    """
    a, b, c, d = both_wrong, primary_only, alternate_only, neither
    if (a + b) == 0 or (c + d) == 0 or c == 0:
        return None
    return (a / (a + b)) / (c / (c + d))


def association(both_wrong, primary_only, alternate_only, neither):
    """(phi, odds ratio, note).  Either may be undefined, and says so when it is.

    ``primary_only`` and ``alternate_only`` are the discordant cells: cases where exactly
    one of the two made the error.  The odds ratio is the odds of the alternate erring
    given the primary erred, divided by the same odds given it did not.
    """
    a, b, c, d = both_wrong, primary_only, alternate_only, neither
    margins = (a + b) * (c + d) * (a + c) * (b + d)
    phi_value = (a * d - b * c) / sqrt(margins) if margins else None
    if b == 0 or c == 0:
        odds = None
        note = "odds ratio undefined: an empty discordant cell, not independence"
    elif a == 0 or d == 0:
        odds = None
        note = "odds ratio undefined: an empty concordant cell, not independence"
    else:
        odds = (a * d) / (b * c)
        note = ""
    if phi_value is None:
        note = (note + "; " if note else "") + "phi undefined: degenerate margin"
    return phi_value, odds, note


def strata(cells):
    """The two within-class 2x2s, folded out of the eight cells.

    Reference-failure: the only available error is missing the failure, so "wrong" means
    the source said pass.  Reference-success: the only available error is the false
    alarm, so "wrong" means it said fail.  No case appears in both.
    """
    failure = (
        cells.both_miss,               # both missed it
        cells.alternate_only_detects,  # primary missed, alternate caught
        cells.primary_only_detects,    # alternate missed, primary caught
        cells.both_detect,             # neither missed
    )
    success = (
        cells.both_false_alarm,
        cells.primary_false_alarm_only,
        cells.alternate_false_alarm_only,
        cells.both_clear,
    )
    return failure, success


def describe(name, table, total):
    both, primary_only, alternate_only, neither = table
    phi_value, odds, note = association(*table)
    errors_primary = both + primary_only
    errors_alternate = both + alternate_only
    print(f"    {name}  n={total}")
    print(f"      2x2  both wrong={both}  primary only={primary_only}  "
          f"alternate only={alternate_only}  neither={neither}")
    print(f"      primary error rate   {fmt(Conditional('', errors_primary, total))}")
    print(f"      alternate error rate {fmt(Conditional('', errors_alternate, total))}")
    print(f"      joint error rate     {fmt(Conditional('', both, total))}")
    print(f"      phi {phi_value:+.3f}" if phi_value is not None else "      phi UNDEFINED")
    print(f"      odds ratio {odds:.2f}" if odds is not None else "      odds ratio UNDEFINED")
    if note:
        print(f"      note: {note}")
    #: Of the cases exactly one got wrong, the share that was the primary's.  Reads
    #: directly as "who carries this stratum's avoidable error" and needs no margin.
    discordant = primary_only + alternate_only
    print(f"      discordant {discordant}; primary's share "
          f"{fmt(Conditional('', primary_only, discordant))}")
    ratio = risk_ratio(*table)
    print(f"      alternate error rate among the primary's errors "
          f"{fmt(Conditional('', both, both + primary_only))} vs among its non-errors "
          f"{fmt(Conditional('', alternate_only, alternate_only + neither))}")
    print(f"      risk ratio {ratio:.2f}x" if ratio is not None
          else "      risk ratio UNDEFINED")
    return phi_value, odds, ratio


def main():
    rows = []
    print(f"CONDITIONAL ERROR ASSOCIATION  primary = {PRIMARY}")
    print("Pooled figures are descriptive context only; the two conditional strata are "
          "the analysis.\n")

    for alternate, tier in ALTERNATES:
        cells, by_slice, _, _, _, _ = load_pair(alternate)
        failure, success = strata(cells)
        n_failure, n_success = sum(failure), sum(success)
        pooled = (
            cells.both_miss + cells.both_false_alarm,
            cells.primary_false_alarm_only + cells.alternate_only_detects,
            cells.primary_only_detects + cells.alternate_false_alarm_only,
            cells.both_detect + cells.both_clear,
        )
        print(f"{tier}  {PRIMARY} -> {alternate}")
        pooled_phi, pooled_odds, _ = describe("POOLED (descriptive only)",
                                              pooled, cells.total)
        fail_phi, fail_odds, fail_rr = describe("REFERENCE FAILURE (both can only miss)",
                                                failure, n_failure)
        succ_phi, succ_odds, succ_rr = describe(
            "REFERENCE SUCCESS (both can only false-alarm)", success, n_success)
        print()

        q_tp, q_fn, q_fp, q_tn = cells.primary
        a_tp, a_fn, a_fp, a_tn = cells.alternate
        rows.append({
            "tier": tier,
            "alternate": alternate,
            "pooled_phi": f"{pooled_phi:+.4f}",
            "pooled_odds_ratio": f"{pooled_odds:.4f}" if pooled_odds else "UNDEFINED",
            "failure_stratum_n": n_failure,
            "failure_phi": f"{fail_phi:+.4f}" if fail_phi is not None else "UNDEFINED",
            "failure_odds_ratio": f"{fail_odds:.4f}" if fail_odds else "UNDEFINED",
            "failure_risk_ratio": f"{fail_rr:.4f}" if fail_rr else "UNDEFINED",
            "failure_both_wrong": failure[0],
            "failure_primary_only_wrong": failure[1],
            "failure_alternate_only_wrong": failure[2],
            "failure_neither_wrong": failure[3],
            "success_stratum_n": n_success,
            "success_phi": f"{succ_phi:+.4f}" if succ_phi is not None else "UNDEFINED",
            "success_odds_ratio": f"{succ_odds:.4f}" if succ_odds else "UNDEFINED",
            "success_risk_ratio": f"{succ_rr:.4f}" if succ_rr else "UNDEFINED",
            "success_both_wrong": success[0],
            "success_primary_only_wrong": success[1],
            "success_alternate_only_wrong": success[2],
            "success_neither_wrong": success[3],
            "primary_fnr": f"{q_fn / (q_tp + q_fn):.4f}",
            "primary_fpr": f"{q_fp / (q_fp + q_tn):.4f}",
            "alternate_fnr": f"{a_fn / (a_tp + a_fn):.4f}",
            "alternate_fpr": f"{a_fp / (a_fp + a_tn):.4f}",
            "alternate_sensitivity": f"{a_tp / (a_tp + a_fn):.4f}",
            "missed_failure_catch": f"{cells.missed_failure_catch.point:.4f}",
            "false_alarm_rescue": f"{cells.false_alarm_rescue.point:.4f}",
        })

    compact(rows)
    orderings(rows)

    dest = os.path.join(REPO, "data", "REAL_arb_conditional_association.csv")
    with open(dest, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {dest}")


def compact(rows):
    print("COMPACT TABLE  (phi / odds ratio)")
    head = (f"  {'alternate':32s} {'pooled':>15s} {'ref-failure':>15s} {'ref-success':>15s}"
            f" {'f.RR':>5s} {'s.RR':>5s}"
            f" {'p.FNR':>6s} {'p.FPR':>6s} {'a.FNR':>6s} {'a.FPR':>6s} "
            f"{'catch':>6s} {'rescue':>6s}")
    print(head)
    for r in rows:
        def cell(p, o):
            odds = r[o]
            return f"{float(r[p]):+.3f}/{'--' if odds == 'UNDEFINED' else f'{float(odds):.1f}'}"
        print(f"  {r['alternate']:32s} {cell('pooled_phi', 'pooled_odds_ratio'):>15s} "
              f"{cell('failure_phi', 'failure_odds_ratio'):>15s} "
              f"{cell('success_phi', 'success_odds_ratio'):>15s} "
              f"{float(r['failure_risk_ratio']):5.2f} "
              f"{float(r['success_risk_ratio']):5.2f} "
              f"{float(r['primary_fnr']):6.3f} {float(r['primary_fpr']):6.3f} "
              f"{float(r['alternate_fnr']):6.3f} {float(r['alternate_fpr']):6.3f} "
              f"{float(r['missed_failure_catch']):6.3f} "
              f"{float(r['false_alarm_rescue']):6.3f}")
    print()


def orderings(rows):
    """Does the sensitivity ordering survive conditioning?

    The §8 observation was about pooled phi.  If it is an operating-point artifact, the
    ordering should decay within a class, where prevalence is held fixed by construction.
    If it persists identically in both classes, the artifact explanation is the wrong one.
    Positional agreement is reported rather than a rank correlation: with eight points a
    coefficient invites a significance reading that eight points cannot support.
    """
    def order(key):
        return [r["alternate"] for r in sorted(rows, key=key, reverse=True)]

    by_sensitivity = order(lambda r: float(r["alternate_sensitivity"]))
    named = [
        ("pooled phi", order(lambda r: float(r["pooled_phi"]))),
        ("ref-failure phi", order(lambda r: float(r["failure_phi"]))),
        ("ref-success phi", order(lambda r: float(r["success_phi"]))),
        ("ref-failure odds", order(lambda r: float(r["failure_odds_ratio"]))),
        ("ref-success odds", order(lambda r: float(r["success_odds_ratio"]))),
    ]
    print("ORDERING AGREEMENT WITH THE ALTERNATE'S OWN FAILURE-SENSITIVITY")
    print(f"  by sensitivity: {' > '.join(by_sensitivity)}")
    for label, sequence in named:
        agree = sum(1 for a, b in zip(sequence, by_sensitivity) if a == b)
        print(f"  {label:18s} agrees on {agree}/8 positions")
        print(f"    {' > '.join(sequence)}")
    print()


if __name__ == "__main__":
    main()
