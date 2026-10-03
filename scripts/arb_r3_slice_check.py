"""R3's preregistered test, conditioned on benchmark slice.

Why this script exists
----------------------
The preregistered R3 test (`report_abstention` in arb_repair_validation.py) compares the
AER judge's error rate on cases R3 escalates against its error rate on everything else,
pooled across all four benchmarks. R3 passed it: 25.6% vs 14.4%, Fisher p = 0.0015.

The hole in that test was written down in one line — but *not* in the preregistration. It is
a caveat in docs/repair_validation_results.md ("The caveat this result needs"), added after
these numbers existed: "Any rule that escalates the cases a judge finds hard will pass a test
of the form 'is the judge worse on the escalated subset'. That test is necessary, not
sufficient, and the preregistration should have said so." That last clause is the point, and
this docstring credited the preregistration until 2026-10-02: the objection was raised while
writing up the result it applies to, and **Disposition: ACCEPTED** was published two
paragraphs below it. Nobody ran the check that would have closed it. An external reproduction
audit (2026-10-02) raised it as the open threat to the project's one clean numeric pass.

The check: R3 fires on 133 cases, **all 133 of them visualwebarena**, which also carries the
highest judge-error point estimate of the four slices -- 22.4%, against 19.8% on webarena,
11.1% on workarena and 3.9% on assistantbench. So the pooled comparison is largely
visualwebarena against the other three benchmarks, not escalated-against-unescalated.
Conditioning on slice is the whole test.

This docstring said "the slice where the judge is weakest ... against three easier
benchmarks" until 2026-10-03. At 22.4% against 19.8% with n=290 and n=373 that ordering is
not separated, and webarena is not an easier benchmark in any sense the data supports. The
defensible claim is the rank of a point estimate, and all four have to be quoted together --
naming only assistantbench and workarena turns a 2.6-point gap into an apparent 22.4-vs-11.1
contrast.

Sections 6 and 7 were added on the same day, for the same reason — a correction is not
finished until the shape of what survives is stated and the control that failed to catch it
is named:

  6. The within-slice residual split by error direction. "Evaluator error" pools missed
     failures and false alarms, which a reviewer acts on differently. The residual turns out
     to sit entirely on the missed-failure side.
  7. The overlap between the held-out arm and the pairing population. The quarantine could
     not have caught this confound: it partitioned cases, while the fact that exposes the
     confound is a property of the corpus the project had already tabulated.

This is a read-only re-analysis. No model is called, no reference label reaches a rule. It
reproduces the published pooled numbers first, so a drift in either direction is visible in
one run.

Input is `data/REAL_arb_repair_validation_cases.csv`, committed, rather than the 4 GB Hugging
Face snapshot the validation run reads. That is deliberate: this script is the arithmetic that
narrowed the project's one clearly-positive result, and a correction a reader cannot recompute
is just another assertion. Regenerate the CSV from the snapshot with
`arb_repair_validation.py --arm validation --export-cases`, which verifies the round-trip.

Section 7 additionally needs `arb_records.csv` from the pairing study's workdir and degrades
with a message if it is absent.

Usage:
  python scripts/arb_r3_slice_check.py
"""

import collections
import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arb_gate1 import WORKDIR  # noqa: E402
from arb_repair_validation import CASES_CSV, SPLIT, load_cases  # noqa: E402

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

    if not os.path.exists(CASES_CSV):
        print(f"missing {os.path.relpath(CASES_CSV, os.path.dirname(WORKDIR))}\n"
              "Regenerate it from the snapshot with:\n"
              "  python scripts/arb_repair_validation.py --arm validation --export-cases")
        sys.exit(1)
    rows = load_cases(CASES_CSV)

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

    # ---------------------------------------------------------------------
    # 6. The within-slice residual, split by error direction.
    #
    # "Evaluator error" pools two populations that a reviewer acts on differently.  On
    # reference-fail cases the only error available is a missed failure (judge said
    # SUCCESS); on reference-success cases it is a false alarm (judge said FAIL).  A
    # residual that lives entirely in one of them is a different claim from one spread
    # across both, and the preregistered test could not see the difference.
    # ---------------------------------------------------------------------
    if len(slices_firing) == 1:
        bench = slices_firing[0]
        print(f"\n6. The within-{bench} residual, split by error direction")
        f = [r for r in fired if r["benchmark"] == bench]
        u = [r for r in unfired if r["benchmark"] == bench]
        for label, ref in (("missed-failure side (ref=fail)", 0),
                           ("false-alarm side (ref=success)", 1)):
            contrast(label,
                     [r for r in f if r["reference"] == ref],
                     [r for r in u if r["reference"] == ref])

    # ---------------------------------------------------------------------
    # 7. Why the quarantine could not have caught this.
    #
    # The split held back the 15 discovery cases and their 27 same-task siblings, so no rule
    # was tested on the cases that suggested it.  That is a control on case-level outcome
    # leakage.  The confound above is a property of the corpus -- which benchmark this judge
    # errs on most -- and that property was already tabulated case by case in the pairing
    # study before R3 was validated.  Printed here so the two facts sit in one output.
    # ---------------------------------------------------------------------
    print("\n7. Overlap between the held-out arm and the already-analysed pairing population")
    records = os.path.join(WORKDIR, "arb_records.csv")
    if not os.path.exists(records):
        print(f"  {records} not present; run scripts/arb_import.py to reproduce this section")
        return
    with open(records, encoding="utf-8") as fh:
        pairing = {(r["benchmark"], r["agent"], r["task_id"]) for r in csv.DictReader(fh)
                   if r["split"] == "test" and r["ref_success"] != "Unsure"}
    with open(SPLIT, encoding="utf-8") as fh:
        split = json.load(fh)
    val = {tuple(c.split("/")) for c in split["validation"]}
    quar = {tuple(c.split("/")) for c in split["discovery"] + split["siblings"]}
    inside = val & pairing
    print(f"  pairing population (test split, primary annotator, non-Unsure)  {len(pairing):5d}")
    print(f"  held-out validation arm                                        {len(val):5d}")
    print(f"  validation cases already inside the pairing population          {len(inside):5d}"
          f"   ({len(inside) / len(val):.1%})")
    print(f"  validation cases outside it                                    "
          f"{len(val - pairing):5d}")
    print(f"  quarantined 42 inside the pairing population                   "
          f"{len(quar & pairing):5d}")
    print()
    print("  A held-out split controls for the analyst having seen the outcome of these")
    print("  cases. It does not control for the analyst having seen the structure of this")
    print("  corpus. A confound living in a covariate -- benchmark, domain, agent -- survives")
    print("  any split that does not stratify on it.")


if __name__ == "__main__":
    main()
