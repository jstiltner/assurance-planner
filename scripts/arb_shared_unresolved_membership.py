"""Verify the membership criterion behind the "shared unresolved errors" label.

Predeclaration section A1.6 defines a shared unresolved error as a case that is (1) wrong
under the primary evaluator, (2) unresolved by ALL EIGHT cached alternates, and (3)
repetition-consistent wrong over the R=5 study draws.

`scripts/arb_repetition_analysis.py` builds its cross-evaluator 2x2 from only one alternate
(the historical `aer` verdict stored in the pair YAML), which is a weaker two-evaluator
criterion. This script scores all eight cached alternates so the two criteria can be
compared directly, and emits the per-case judge matrix used by the case review.

No model inference. Reads only the local HuggingFace snapshot and committed repo data.

Usage:  python scripts/arb_shared_unresolved_membership.py [--json OUT]
"""

import argparse
import collections
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arb_extract import parse_verdict  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.expanduser(
    "~/.cache/huggingface/hub/datasets--McGill-NLP--agent-reward-bench/"
    "snapshots/b6d17e646009d6cb63d5dd7be78807b680693f61"
)
PAIR_FILE = os.path.join(REPO, "data", "REAL_arb_functional_x_aer.yaml")
RAW_FILE = os.path.join(REPO, "data", "REAL_arb_repetition_raw.jsonl")

# The nine judges at full 1302-file coverage, minus `functional` (the primary).
# `aerv` is excluded: it has only 1 judgment file, so it is not a candidate alternate.
ALTERNATES = [
    "aer",
    "claude-3.7-sonnet-noscreen",
    "gpt-4o-mini-noscreen",
    "gpt-4o-mini-noscreen-noaxtree",
    "gpt-4o-noscreen",
    "llama-3.3-70b-noscreen",
    "nnetnav",
    "qwen-2.5-vl-noscreen",
]


def numerize(verdict):
    """1 = judge said SUCCESS, 0 = judge said FAIL."""
    return 1 if str(verdict).lower() in ("success", "pass", "1", "true") else 0


def load_repetition_k():
    """Per-case count of correct verdicts out of 5, deduped by (case_id, repetition_index)."""
    seen = set()
    correct = collections.Counter()
    n_valid = collections.Counter()
    with open(RAW_FILE, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("call_status") != "valid":
                continue
            key = (rec["case_id"], rec["repetition_index"])
            if key in seen:
                continue
            seen.add(key)
            n_valid[rec["case_id"]] += 1
            if rec["is_correct"]:
                correct[rec["case_id"]] += 1
    return correct, n_valid


def alternate_verdict(case_id, judge):
    """Return 1/0 for the cached judge's verdict, or None if absent or unparseable."""
    benchmark, agent, task = case_id.split("/")
    path = os.path.join(SNAPSHOT, "judgments", benchmark, agent, judge, task + ".json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        success, parse_ok = parse_verdict(judge, json.load(f))
    return success if parse_ok else None


def analyse(stratum):
    """stratum: 'missed_failure' (ref=fail, primary said success) or 'false_alarm'."""
    with open(PAIR_FILE, encoding="utf-8") as f:
        cases = {c["case_id"]: c for c in yaml.safe_load(f)["cases"]}
    correct, _ = load_repetition_k()

    want_fail = stratum == "missed_failure"
    primary_wrong_verdict = 1 if want_fail else 0

    loose, strict, matrix = [], [], {}
    for case_id, case in cases.items():
        is_fail = case["reference_label"] == "fail"
        if is_fail != want_fail:
            continue
        if numerize(case["observations"][0]["verdict"]) != primary_wrong_verdict:
            continue
        if correct.get(case_id, 0) != 0:  # not repetition-consistent wrong
            continue
        if numerize(case["alternate_observations"][0]["verdict"]) != primary_wrong_verdict:
            continue

        loose.append(case_id)
        verdicts = {j: alternate_verdict(case_id, j) for j in ALTERNATES}
        wrong = sorted(j for j, v in verdicts.items() if v == primary_wrong_verdict)
        right = sorted(j for j, v in verdicts.items() if v is not None and v != primary_wrong_verdict)
        unparsed = sorted(j for j, v in verdicts.items() if v is None)
        matrix[case_id] = {
            "reference_label": case["reference_label"],
            "alternates_wrong": wrong,
            "alternates_correct": right,
            "alternates_unparsed": unparsed,
            "k_of_5": correct.get(case_id, 0),
        }
        if len(wrong) == len(ALTERNATES):
            strict.append(case_id)
    return loose, strict, matrix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write the per-case judge matrix here")
    args = ap.parse_args()

    out = {}
    for stratum in ("missed_failure", "false_alarm"):
        loose, strict, matrix = analyse(stratum)
        out[stratum] = {"loose": loose, "strict": strict, "matrix": matrix}
        print(f"\n=== {stratum} ===")
        for case_id in loose:
            m = matrix[case_id]
            n_wrong = len(m["alternates_wrong"])
            mark = " [A1.6 STRICT]" if n_wrong == len(ALTERNATES) else ""
            print(f"{case_id}{mark}")
            print(f"    alternates wrong {n_wrong}/{len(ALTERNATES)}"
                  f" | correct: {m['alternates_correct'] or '-'}"
                  f" | unparsed: {m['alternates_unparsed'] or '-'}")
        print(f"  two-evaluator criterion (primary + historical aer): {len(loose)}")
        print(f"  A1.6 eight-alternate criterion:                     {len(strict)}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
