"""Firing distribution and within-slice error contrast, for all four held-out rules.

Why this script exists
----------------------
arb_r3_slice_check.py answered the question an external reproduction audit asked about R3:
all 133 of its firings are visualwebarena, so its pooled error-rate contrast was largely a
benchmark contrast. But R1's escalation half and R4's comparison are *the same kind of
claim*, computed the same pooled way, and nobody had checked them either. Finding one
instance of a defect and not sweeping for the rest of its class is how the first one got
published.

So this is the sweep. For each of R1-R4 it reports where the rule fires across benchmarks,
then the judge's error rate on fired vs unfired cases both pooled and conditioned on slice.
A rule whose pooled separation collapses under conditioning was measuring which benchmark
it was in.

Read-only re-analysis of the same cached judgments the validation run uses. No model is
called and no reference label reaches a rule.

Usage:
  python scripts/arb_rule_slice_audit.py
"""

import collections
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arb_repair_validation import SPLIT, evaluate, load_reference  # noqa: E402

try:
    from scipy.stats import fisher_exact
except ImportError:  # pragma: no cover - reported rather than guessed
    fisher_exact = None

# Minimum cases on each side before a within-slice contrast is worth printing a p-value for.
MIN_ARM = 20


def error_rate(rows):
    """AER baseline wrong vs the first-annotator reference. (errors, n)."""
    return sum(1 for r in rows if r["baseline"] != r["reference"]), len(rows)


def contrast(label, fired, unfired):
    """Print the fired/unfired error contrast. Returns the separation as a fraction, or None."""
    a, an = error_rate(fired)
    c, cn = error_rate(unfired)
    if an == 0 or cn == 0:
        print(f"  {label:26s} not computable (one arm is empty)")
        return None
    pa, pc = a / an, c / cn
    line = (f"  {label:26s} {a:3d}/{an:<4d} = {pa:5.1%}   vs   "
            f"{c:3d}/{cn:<4d} = {pc:5.1%}   diff {100 * (pa - pc):+5.1f} pp")
    if fisher_exact is not None and min(an, cn) >= MIN_ARM:
        _, p = fisher_exact([[a, an - a], [c, cn - c]])
        line += f"   Fisher p = {p:.4f}"
    elif min(an, cn) < MIN_ARM:
        line += f"   (arm < {MIN_ARM}, no test)"
    print(line)
    return pa - pc


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    with open(SPLIT, encoding="utf-8") as fh:
        split = json.load(fh)
    rows = evaluate(split["validation"], load_reference())
    cases_by = collections.Counter(r["benchmark"] for r in rows)
    rules = sorted(rows[0]["fires"])

    print(f"held-out arm, scored cases: {len(rows)}")
    print("benchmarks: " + ", ".join(f"{b} (n={cases_by[b]})" for b in sorted(cases_by)))
    print("\njudge error by slice, ignoring every rule:")
    for bench in sorted(cases_by):
        e, n = error_rate([r for r in rows if r["benchmark"] == bench])
        print(f"  {bench:18s} {e:3d}/{n:<4d} = {e / n:5.1%}")

    for rule in rules:
        fired = [r for r in rows if r["fires"][rule]]
        unfired = [r for r in rows if not r["fires"][rule]]
        print(f"\n{'=' * 78}\n{rule}  —  {len(fired)} firings")
        if not fired:
            print("  never fires on the held-out arm")
            continue

        fires_by = collections.Counter(r["benchmark"] for r in fired)
        for bench in sorted(cases_by):
            n_fire = fires_by.get(bench, 0)
            print(f"  fires in {bench:18s} {n_fire:4d} / {cases_by[bench]:4d}"
                  f"   {n_fire / cases_by[bench]:5.1%}")
        slices_firing = [b for b in sorted(cases_by) if fires_by.get(b, 0)]
        concentrated = len(slices_firing) == 1

        pooled = contrast("pooled", fired, unfired)
        for bench in slices_firing:
            contrast(
                f"within {bench}",
                [r for r in fired if r["benchmark"] == bench],
                [r for r in unfired if r["benchmark"] == bench],
            )

        if concentrated and pooled is not None:
            bench = slices_firing[0]
            f = [r for r in fired if r["benchmark"] == bench]
            u = [r for r in unfired if r["benchmark"] == bench]
            a, an = error_rate(f)
            c, cn = error_rate(u)
            residual = a / an - c / cn if an and cn else None
            print(f"  -> fires in {bench} only. pooled {100 * pooled:+.1f} pp, "
                  f"within-slice {100 * residual:+.1f} pp, "
                  f"slice-attributable {100 * (pooled - residual):+.1f} pp")
        elif not concentrated:
            print(f"  -> fires across {len(slices_firing)} slices, so the pooled contrast is "
                  "not a single-slice artefact")


if __name__ == "__main__":
    main()
