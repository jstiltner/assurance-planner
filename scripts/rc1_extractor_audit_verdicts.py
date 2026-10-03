"""Write the A3 audit's per-case verdicts into the case artifact, and verify the A3 figures.

Why this script exists
----------------------
`docs/rc1_extractor_audit.md` recorded 30 case-by-case judgments in prose and a summary table
counted by hand. A3's headline -- 28/30 -- was therefore a number a reader had to trust, and the
out-of-sample correction found on 2026-10-02 (that cases 02, 06 and 16 are the very cases Commit
A2 had already repaired, so 28/30 is not out-of-sample) was itself a hand count of a hand count.

This moves the verdicts into `audit_verdict` on each case in the artifact, so both figures are
computed from data and checked against the ledger. The verdicts are transcribed from the
document, not re-derived: only the auditor can issue them. What is mechanical is the counting,
and the counting is what was wrong.

`--write` annotates the artifact. The default is read-only verification, which is what belongs
in a test run.

Usage:
  python scripts/rc1_extractor_audit_verdicts.py --write    # annotate, then verify
  python scripts/rc1_extractor_audit_verdicts.py            # verify only
"""

import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from public_claim_ledger import CANONICAL  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(REPO, "data", "rc1_extractor_audit_cases_final.json")

# Transcribed from docs/rc1_extractor_audit.md, "Case-by-case judgments (post-A2 patterns)".
# CORRECT is every case not named here; naming only the exceptions keeps this list short enough
# to check against the document by eye, which is how a transcription error gets caught.
NOT_CORRECT = {9: "MISS", 19: "INCORRECT"}

# Case 12 was scored CORRECT off an explicit "AMBIGUOUS -> scored CORRECT" judgment. It counts in
# the 28, and the fact that it is a judgment call rather than a clean pass is recorded instead of
# being flattened into the verdict.
AMBIGUOUS = {12}

# Commit A2's three precision fixes were made on these cases, in pass 1, before pass 2 scored
# them CORRECT. They are passes, and they are not out-of-sample. CANONICAL carries the same list
# as strings; the two are cross-checked below rather than kept in step by hand.
A2_REPAIRED = {2, 6, 16}


def annotate(cases):
    for case in cases:
        n = case["case_num"]
        case["audit_verdict"] = NOT_CORRECT.get(n, "CORRECT")
        case["audit_ambiguous"] = n in AMBIGUOUS
        case["a2_repaired"] = n in A2_REPAIRED
        case["out_of_sample"] = n not in A2_REPAIRED
    return cases


def verify(cases):
    """Recompute A3 from the artifact and check it against the ledger. True if everything agrees."""
    missing = [c["case_num"] for c in cases if "audit_verdict" not in c]
    if missing:
        print(f"FAIL: {len(missing)} cases carry no audit_verdict: {missing}")
        print("Run with --write to annotate the artifact.")
        return False

    verdicts = collections.Counter(c["audit_verdict"] for c in cases)
    passes = [c for c in cases if c["audit_verdict"] == "CORRECT"]
    oos = [c for c in passes if c["out_of_sample"]]
    oos_total = [c for c in cases if c["out_of_sample"]]
    repaired = sorted(c["case_num"] for c in cases if c["a2_repaired"])

    print(f"A3 extractor audit - recomputed from {os.path.relpath(CASES, REPO)}\n")
    print(f"  cases scored                {len(cases):3d}")
    for v in ("CORRECT", "INCORRECT", "MISS"):
        print(f"  {v:27s} {verdicts[v]:3d}")
    amb = [c["case_num"] for c in cases if c.get("audit_ambiguous")]
    print(f"  of which judgment calls     {len(amb):3d}   cases {amb}")
    print()
    print(f"  as scored                   {len(passes):3d}/{len(cases)}"
          f"   = {len(passes) / len(cases):.1%}")
    print(f"  A2-repaired, so not fresh   {len(repaired):3d}   cases {repaired}")
    print(f"  held strictly out of sample {len(oos):3d}/{len(oos_total)}"
          f"   = {len(oos) / len(oos_total):.1%}")
    print()

    checks = [
        ("pass count as scored", len(passes), CANONICAL["rc1_extractor_pass"]),
        ("total as scored", len(cases), CANONICAL["rc1_extractor_total"]),
        ("pass count out of sample", len(oos), CANONICAL["rc1_extractor_pass_out_of_sample"]),
        ("total out of sample", len(oos_total), CANONICAL["rc1_extractor_total_out_of_sample"]),
        ("A2-repaired case list", tuple(f"{n:02d}" for n in repaired),
         tuple(CANONICAL["rc1_extractor_a2_repaired_cases"])),
    ]
    ok = True
    for label, got, want in checks:
        agree = got == want
        ok &= agree
        print(f"  [{'ok' if agree else 'FAIL'}] {label:28s} artifact={got}  ledger={want}")

    # A3's bar is a count, not a rate -- the distinction the 2026-10-02 correction turns on.
    bar = CANONICAL["rc1_extractor_total"] - 3
    print()
    print(f"  A3 bar (preregistered, a count): >= {bar}/{CANONICAL['rc1_extractor_total']}")
    print(f"    as scored      {len(passes)}/{len(cases)} "
          f"-> {'PASS' if len(passes) >= bar else 'FAIL'}")
    print(f"    out of sample  {len(oos)}/{len(oos_total)} "
          f"-> {'below the bar as a count' if len(oos) < bar else 'PASS'}"
          f", {len(oos) / len(oos_total):.1%} as a rate")
    print("\n  A3 is precision only. Recall is unmeasured; see the second limit in")
    print("  docs/rc1_extractor_audit.md. These counts cannot speak to what the extractor missed.")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="annotate the artifact with audit_verdict before verifying")
    args = ap.parse_args()

    with open(CASES, encoding="utf-8") as fh:
        cases = json.load(fh)
    if args.write:
        annotate(cases)
        with open(CASES, "w", encoding="utf-8") as fh:
            json.dump(cases, fh, indent=2)
            fh.write("\n")
        print(f"annotated {len(cases)} cases in {os.path.relpath(CASES, REPO)}\n")
    sys.exit(0 if verify(cases) else 1)


if __name__ == "__main__":
    main()
