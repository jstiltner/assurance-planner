"""R3's preregistered test, conditioned on benchmark slice.

Why this script exists
----------------------
The preregistered R3 test (`report_abstention` in arb_repair_validation.py) compares the
AER judge's error rate on cases R3 escalates against its error rate on everything else,
pooled across all four benchmarks. R3 passed it: 25.6% vs 14.4%, Fisher p = 0.0015.

docs/repair_validation_preregistration.md anticipated the hole in that test in one line —
"any rule that escalates hard cases passes this test" — and then nobody ran the check that
would have closed it. An external reproduction audit (2026-10-02) raised it as the open
threat to the project's one clearly-positive result.

The check: R3 fires on 133 cases, **all 133 of them visualwebarena**, which is also the
slice where the judge is weakest. So the pooled comparison is largely visualwebarena
against three easier benchmarks, not escalated-against-unescalated. Conditioning on slice
is the whole test.

This is a read-only re-analysis of the same cached judgments the validation run uses. No
model is called, no reference label reaches a rule. It reproduces the published pooled
numbers first, so a drift in either direction is visible in one run.

Usage:
  python scripts/arb_r3_slice_check.py
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

R3 = "R3_unverifiable_image_premise"


def error_rate(rows):
    """AER baseline wrong vs the first-annotator reference. (errors, n)."""
    return sum(1 for r in rows if r["baseline"] != r["reference"]), len(rows)


def contrast(label, fired, unfired):
    a, an = error_rate(fired)
    c, cn = error_rate(unfired)
    pa, pc = a / an, c / cn
    line = (f"  {label:24s} {a:3d}/{an:<4d} = {pa:5.1%}   vs   "
            f"{c:3d}/{cn:<4d} = {pc:5.1%}   diff {100 * (pa - pc):+5.1f} pp")
    if fisher_exact is not None:
        _, p = fisher_exact([[a, an - a], [c, cn - c]])
        line += f"   Fisher p = {p:.4f}"
    print(line)
    return pa - pc


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    with open(SPLIT, encoding="utf-8") as fh:
        split = json.load(fh)
    rows = evaluate(split["validation"], load_reference())

    fired = [r for r in rows if r["fires"][R3]]
    unfired = [r for r in rows if not r["fires"][R3]]

    print(f"held-out arm, scored cases: {len(rows)}\n")

    print("1. The preregistered test, as published")
    pooled = contrast("pooled (all benchmarks)", fired, unfired)

    print("\n2. Where R3 fires")
    fires_by = collections.Counter(r["benchmark"] for r in fired)
    cases_by = collections.Counter(r["benchmark"] for r in rows)
    for bench in sorted(cases_by):
        n_fire, n_case = fires_by.get(bench, 0), cases_by[bench]
        print(f"  {bench:18s} {n_fire:4d} / {n_case:4d} cases   {n_fire / n_case:5.1%}")
    slices_firing = [b for b in cases_by if fires_by.get(b, 0)]
    if len(slices_firing) == 1:
        print(f"  -> fires in exactly one slice: {slices_firing[0]}")

    print("\n3. Judge error by slice, ignoring R3 entirely")
    for bench in sorted(cases_by):
        e, n = error_rate([r for r in rows if r["benchmark"] == bench])
        print(f"  {bench:18s} {e:3d}/{n:<4d} = {e / n:5.1%}")

    print("\n4. The same test, conditioned on slice")
    within = {}
    for bench in slices_firing:
        f = [r for r in fired if r["benchmark"] == bench]
        u = [r for r in unfired if r["benchmark"] == bench]
        within[bench] = contrast(f"within {bench}", f, u)

    print("\n5. Reading")
    if len(slices_firing) == 1:
        bench = slices_firing[0]
        residual = within[bench]
        print(f"  pooled separation      {100 * pooled:+5.1f} pp")
        print(f"  survives conditioning  {100 * residual:+5.1f} pp")
        print(f"  attributable to slice  {100 * (pooled - residual):+5.1f} pp")
        print()
        print("  R3 fires in one slice only, so the pooled contrast compares that slice")
        print("  against the rest of the corpus. The within-slice residual is the part")
        print("  that is about the evidence gap rather than about which benchmark it is.")


if __name__ == "__main__":
    main()
