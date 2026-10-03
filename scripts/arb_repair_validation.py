"""Held-out evaluation of the frozen repair rules. Commit 3 of 3.

Runs the protocol preregistered in docs/repair_validation_preregistration.md
against the split frozen in data/REAL_arb_discovery_validation_split.json.

The oracle boundary: reference labels enter this script ONLY through `score()`,
after a rule has already decided whether it fires. `extract_features` and the rule
functions in arb_production_signals never see them.

No model is called. Every number comes from cached judgments and annotations.

Usage:
  python scripts/arb_repair_validation.py --arm validation
  python scripts/arb_repair_validation.py --arm validation_strict
"""

import argparse
import collections
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arb_extract import parse_verdict  # noqa: E402
from arb_production_signals import JUDGMENTS, RULES, extract_features  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.expanduser(
    "~/.cache/huggingface/hub/datasets--McGill-NLP--agent-reward-bench/"
    "snapshots/b6d17e646009d6cb63d5dd7be78807b680693f61"
)
SPLIT = os.path.join(REPO, "data", "REAL_arb_discovery_validation_split.json")
ANNOTATIONS = os.path.join(SNAPSHOT, "data", "annotations.csv")

# The per-case export. Everything above this line needs the Hugging Face snapshot; everything
# downstream of this file does not, which is the point -- `arb_r3_slice_check.py` reproduces the
# stratified figures from here, so a reader without the 4 GB snapshot can still check the
# arithmetic that narrowed R3's reading. Committed, because a correction nobody can recompute is
# an assertion.
CASES_CSV = os.path.join(REPO, "data", "REAL_arb_repair_validation_cases.csv")
CASES_FIELDS = ["case_id", "benchmark", "agent", "task_id", "reference", "baseline"]

# Rules that change the emitted verdict. R1 and R4 are evidence only.
VETO_RULES = ["R2_negative_selfreport_modification"]
ABSTAIN_RULES = ["R3_unverifiable_image_premise"]


def load_reference():
    """(benchmark, agent, task) -> 1 success / 0 fail, FIRST annotator only."""
    ref, seen = {}, set()
    with open(ANNOTATIONS, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (row["benchmark"], row["model_name"], row["task_id"])
            if key in seen:
                continue
            seen.add(key)
            if row["trajectory_success"] == "Successful":
                ref[key] = 1
            elif row["trajectory_success"] == "Unsuccessful":
                ref[key] = 0
    return ref


def evaluate(case_ids, reference):
    """Per-case: baseline AER verdict, reference, and which rules fired."""
    rows = []
    for cid in case_ids:
        benchmark, agent, task = cid.split("/")
        path = os.path.join(JUDGMENTS, benchmark, agent, "aer", task + ".json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            judgment = json.load(fh)
        ref = reference.get((benchmark, agent, task))
        if ref is None:
            continue
        base, ok = parse_verdict("aer", judgment)
        if not ok or base is None:
            continue
        features = extract_features(judgment)
        fires = {name: fn(features)[0] for name, (fn, _) in RULES.items()}
        rows.append({"case_id": cid, "benchmark": benchmark,
                     "reference": ref, "baseline": base, "fires": fires})
    return rows


def export_cases(rows, path=CASES_CSV):
    """Write one row per scored case: identity, both verdicts, and every rule's firing.

    These are exactly the fields `evaluate` produces, so a consumer of the CSV sees what the
    validation run saw and nothing more. No obligation text, no judgment prose, no annotator
    identity -- the snapshot's terms of use cover the trajectories, and this export deliberately
    carries only the derived booleans needed to recompute the published contrasts.
    """
    rule_names = sorted(RULES)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CASES_FIELDS + rule_names)
        writer.writeheader()
        for r in rows:
            benchmark, agent, task = r["case_id"].split("/")
            writer.writerow({"case_id": r["case_id"], "benchmark": benchmark, "agent": agent,
                             "task_id": task, "reference": r["reference"],
                             "baseline": r["baseline"],
                             **{n: int(r["fires"][n]) for n in rule_names}})
    return path


def load_cases(path=CASES_CSV):
    """Read the export back into the shape `evaluate` returns. The inverse of export_cases."""
    rule_names = sorted(RULES)
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append({"case_id": r["case_id"], "benchmark": r["benchmark"],
                         "reference": int(r["reference"]), "baseline": int(r["baseline"]),
                         "fires": {n: bool(int(r[n])) for n in rule_names}})
    return rows


def verify_export(rows, path=CASES_CSV):
    """Prove the CSV is a faithful stand-in for the snapshot, then show what it contains.

    A round-trip check is the whole point: if this prints OK, every downstream number computed
    from the CSV is the number the snapshot would have given. It is checked rather than asserted
    because the export exists so that a reader need not trust the export.
    """
    back = load_cases(path)
    print(f"\n--- export verification: {os.path.relpath(path, REPO)}")
    print(f"    rows written          {len(back):5d}   (scored cases in memory {len(rows):5d})")
    if len(back) != len(rows):
        print("    MISMATCH in row count")
        return False
    diffs = [a["case_id"] for a, b in zip(rows, back)
             if (a["case_id"], a["benchmark"], a["reference"], a["baseline"], a["fires"])
             != (b["case_id"], b["benchmark"], b["reference"], b["baseline"], b["fires"])]
    print(f"    round-trips identical {'yes' if not diffs else 'NO: ' + ', '.join(diffs[:5])}")

    nfail = sum(1 for r in back if r["reference"] == 0)
    err = sum(1 for r in back if r["baseline"] != r["reference"])
    print(f"    reference fail/success {nfail:4d} / {len(back) - nfail}")
    print(f"    baseline AER errors   {err:5d}  = {err / len(back):.1%}")
    print("    per benchmark:")
    for b in sorted({r["benchmark"] for r in back}):
        sub = [r for r in back if r["benchmark"] == b]
        e = sum(1 for r in sub if r["baseline"] != r["reference"])
        print(f"      {b:18s} {len(sub):4d} cases   judge error {e:3d} = {e / len(sub):5.1%}")
    print("    firings per rule:")
    for n in sorted(RULES):
        f = [r for r in back if r["fires"][n]]
        slices = sorted({r["benchmark"] for r in f})
        print(f"      {n:36s} {len(f):4d}  ({len(f) / len(back):5.1%})  "
              f"slices: {', '.join(slices) if slices else 'none'}")
    print("    Reproduce the stratified R3 figures from this file alone:")
    print("      python scripts/arb_r3_slice_check.py")
    return not diffs


def apply_rules(row, veto=(), abstain=()):
    """Return the post-rule disposition: 1 success, 0 fail, or 'UNVERIFIABLE'."""
    if any(row["fires"][r] for r in abstain):
        return "UNVERIFIABLE"
    if any(row["fires"][r] for r in veto):
        return 0
    return row["baseline"]


def error_counts(rows, dispositions):
    """E1 = says SUCCESS but ref fail. E2 = says FAIL but ref success."""
    e1 = e2 = agree = scored = 0
    for row, d in zip(rows, dispositions):
        if d == "UNVERIFIABLE":
            continue
        scored += 1
        if d == 1 and row["reference"] == 0:
            e1 += 1
        elif d == 0 and row["reference"] == 1:
            e2 += 1
        else:
            agree += 1
    return {"scored": scored, "E1": e1, "E2": e2, "agree": agree}


def report_rule(rows, name, veto=(), abstain=()):
    base = [r["baseline"] for r in rows]
    post = [apply_rules(r, veto, abstain) for r in rows]
    b, p = error_counts(rows, base), error_counts(rows, post)

    helped = harmed = changed = 0
    ref_class = collections.Counter()
    for row, d0, d1 in zip(rows, base, post):
        if d0 == d1:
            continue
        changed += 1
        ref_class["ref=fail" if row["reference"] == 0 else "ref=success"] += 1
        if d1 == "UNVERIFIABLE":
            continue
        was_right, now_right = (d0 == row["reference"]), (d1 == row["reference"])
        helped += int(now_right and not was_right)
        harmed += int(was_right and not now_right)

    n = len(rows)
    eligible = sum(1 for r in rows if any(r["fires"][x] for x in list(veto) + list(abstain)))
    print(f"\n--- {name}")
    print(f"    eligible (fires)      {eligible:5d}  ({eligible / n:.1%} of {n})")
    print(f"    verdicts changed      {changed:5d}   by reference class: {dict(ref_class)}")
    print(f"    helped                {helped:5d}")
    print(f"    harmed                {harmed:5d}")
    print(f"    E1 says-SUCCESS/ref-fail   {b['E1']:5d} -> {p['E1']:5d}"
          f"   ({b['E1'] / max(b['scored'], 1):.1%} -> {p['E1'] / max(p['scored'], 1):.1%})")
    print(f"    E2 says-FAIL/ref-success   {b['E2']:5d} -> {p['E2']:5d}"
          f"   ({b['E2'] / max(b['scored'], 1):.1%} -> {p['E2'] / max(p['scored'], 1):.1%})")
    print(f"    cases still scored    {b['scored']:5d} -> {p['scored']:5d}")
    print(f"    accuracy (not a decision input)  "
          f"{b['agree'] / max(b['scored'], 1):.1%} -> {p['agree'] / max(p['scored'], 1):.1%}")
    return {"eligible": eligible, "changed": changed, "helped": helped,
            "harmed": harmed, "before": b, "after": p}


def report_evidence_rule(rows, name):
    """R1/R4: change no verdict. Measured as enrichment for reference-fail."""
    fired = [r for r in rows if r["fires"][name]]
    n = len(rows)
    base_rate = sum(1 for r in rows if r["reference"] == 0) / n
    if not fired:
        print(f"\n--- {name} (evidence only)\n    never fires")
        return
    prec = sum(1 for r in fired if r["reference"] == 0) / len(fired)
    aer_wrong_fired = sum(1 for r in fired if r["baseline"] != r["reference"]) / len(fired)
    rest = [r for r in rows if not r["fires"][name]]
    aer_wrong_rest = sum(1 for r in rest if r["baseline"] != r["reference"]) / max(len(rest), 1)
    print(f"\n--- {name} (evidence only, changes no verdict)")
    print(f"    fires                 {len(fired):5d}  ({len(fired) / n:.1%})")
    print(f"    ref=fail among firings     {prec:.1%}   vs corpus base rate {base_rate:.1%}"
          f"   (lift {prec / base_rate:.2f}x)")
    print(f"    AER wrong on firings       {aer_wrong_fired:.1%}"
          f"   vs on non-firings {aer_wrong_rest:.1%}")


def _err(rows):
    """(errors, n) for the baseline AER verdict against the reference."""
    return sum(1 for r in rows if r["baseline"] != r["reference"]), len(rows)


def report_abstention(rows, name):
    fired = [r for r in rows if r["fires"][name]]
    rest = [r for r in rows if not r["fires"][name]]
    if not fired:
        return
    err_f = sum(1 for r in fired if r["baseline"] != r["reference"]) / len(fired)
    err_r = sum(1 for r in rest if r["baseline"] != r["reference"]) / max(len(rest), 1)
    print(f"\n    [preregistered R3 test] AER error rate on escalated {err_f:.1%}"
          f"  vs on remainder {err_r:.1%}"
          f"   -> {'PASS' if err_f > err_r else 'FAIL'}")
    print(f"    [preregistered R3 test] escalation volume {len(fired) / len(rows):.1%}"
          f"   -> {'PASS' if len(fired) / len(rows) < 0.15 else 'FAIL'} (threshold 15%)")

    # The preregistered test above pools across benchmarks.  The hazard was written down -- but
    # in docs/repair_validation_results.md, as a caveat added *after* these numbers existed, not
    # in the preregistration: "Any rule that escalates the cases a judge finds hard will pass a
    # test of the form 'is the judge worse on the escalated subset'.  That test is necessary, not
    # sufficient, and the preregistration should have said so."  (This comment credited the
    # preregistration until 2026-10-02.  It should not: the caveat's own closing clause says the
    # preregistration was silent, and ACCEPTED was published two paragraphs below it.)  The check
    # was never run; an external reproduction found on 2026-10-02 that all of R3's firings are
    # visualwebarena, the slice with the highest judge error.  Printing the stratification here,
    # inside the preregistered test's own output, is the cheapest way to stop the pooled
    # pair from being read alone again.  The pooled PASS above is unchanged and remains the
    # disposition; what follows qualifies the reading, not the verdict.
    benches = sorted({r["benchmark"] for r in rows})
    firing = [b for b in benches if any(r["benchmark"] == b for r in fired)]
    print(f"\n    [NOT preregistered — added 2026-10-02] stratified by benchmark. "
          f"R3 fires in {len(firing)} of {len(benches)} slices: {', '.join(firing)}")
    for b in benches:
        a, an = _err([r for r in fired if r["benchmark"] == b])
        c, cn = _err([r for r in rest if r["benchmark"] == b])
        if not an:
            print(f"      {b:18s} no firings; judge error {c}/{cn} = {c / max(cn, 1):5.1%}")
            continue
        print(f"      {b:18s} {a:3d}/{an:<4d} = {a / an:5.1%}  vs  {c:3d}/{cn:<4d} = "
              f"{c / max(cn, 1):5.1%}   diff {100 * (a / an - c / max(cn, 1)):+5.1f} pp")
    if len(firing) == 1:
        b = firing[0]
        f_in = [r for r in fired if r["benchmark"] == b]
        u_in = [r for r in rest if r["benchmark"] == b]
        print(f"      -> pooled separation is partly slice identity, not escalation. "
              f"Within-slice split by error direction:")
        for label, ref in (("missed-failure (ref=fail)  ", 0),
                           ("false-alarm   (ref=success)", 1)):
            a, an = _err([r for r in f_in if r["reference"] == ref])
            c, cn = _err([r for r in u_in if r["reference"] == ref])
            if not an or not cn:
                continue
            print(f"      {label} {a:3d}/{an:<4d} = {a / an:5.1%}  vs  {c:3d}/{cn:<4d} = "
                  f"{c / cn:5.1%}   diff {100 * (a / an - c / cn):+5.1f} pp")
        print("      Fisher p-values and the full decomposition: scripts/arb_r3_slice_check.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="validation",
                    choices=["validation", "validation_strict", "discovery"])
    ap.add_argument("--export-cases", action="store_true",
                    help=f"write the per-case table to {os.path.relpath(CASES_CSV, REPO)} "
                         "and verify the round-trip")
    args = ap.parse_args()

    with open(SPLIT, encoding="utf-8") as fh:
        split = json.load(fh)
    reference = load_reference()
    rows = evaluate(split[args.arm], reference)

    print(f"ARM: {args.arm}   scored cases: {len(rows)}")
    nfail = sum(1 for r in rows if r["reference"] == 0)
    print(f"reference base rate: fail {nfail} ({nfail / len(rows):.1%}), "
          f"success {len(rows) - nfail}")
    b = error_counts(rows, [r["baseline"] for r in rows])
    print(f"baseline AER: E1={b['E1']} E2={b['E2']} agree={b['agree']} "
          f"accuracy={b['agree'] / b['scored']:.1%}")

    for name in ["R1_contradictory_infeasibility", "R4_terminal_search_route"]:
        report_evidence_rule(rows, name)

    report_rule(rows, "R2 veto (alone)", veto=VETO_RULES)
    report_rule(rows, "R3 UNVERIFIABLE (alone)", abstain=ABSTAIN_RULES)
    report_abstention(rows, "R3_unverifiable_image_premise")
    report_rule(rows, "COMPOSITE R2+R3", veto=VETO_RULES, abstain=ABSTAIN_RULES)

    if args.export_cases:
        # Only the validation arm is committed. Exporting the discovery arm would put the
        # quarantined 42 in the repo next to a file the slice check reads by default, which is
        # how a held-out split stops being held out.
        if args.arm != "validation":
            print(f"\n--- export skipped: --export-cases is validation-only, got {args.arm}")
            return
        export_cases(rows)
        if not verify_export(rows):
            sys.exit(1)


if __name__ == "__main__":
    main()
