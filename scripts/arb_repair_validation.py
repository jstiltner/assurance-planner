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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="validation",
                    choices=["validation", "validation_strict", "discovery"])
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


if __name__ == "__main__":
    main()
