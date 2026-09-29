"""Phase 0 evidence extraction for the 15-case qualitative review.

Assembles, per case, everything the local archive and this repo can supply, so that the
review can state precisely what evidence exists and what is missing. No model inference:
reads only the local HuggingFace snapshot and committed repo data.

Evidence items attempted per case (see docs/shared_unresolved_case_review.md Phase 0):
  1  case_id                            -- repo pair YAML
  2  benchmark / agent                  -- case_id + judgment JSON
  3  task instruction (goal)            -- judgment JSON `goal`
  4  reference label                    -- repo pair YAML / annotations.csv
  5  expert rationale + metadata        -- annotations.csv (structured only; NO free text)
  6  trajectory / action history        -- AER `chat_messages` (agent-reported, not raw)
  7  final state / screenshots          -- caption text only; raw screenshots NOT in snapshot
  8  caption given to AER               -- tail of the AER user message
  9  stored AER chat_messages           -- judgment JSON
  10 historical AER verdict + response  -- judgment JSON `response`
  11 five current AER verdicts          -- data/REAL_arb_repetition_raw.jsonl
  12 functional primary verdict         -- summary_info.cum_reward
  13 other cached judge verdicts        -- the other 7 alternates' judgment JSONs
  14 upstream programmatic verifier     -- summary_info.cum_reward / cum_raw_reward
  15 task-success signal vs expert label-- cum_reward vs annotations.trajectory_success

Usage:
  python scripts/arb_case_evidence.py --out evidence/           # write per-case bundles
  python scripts/arb_case_evidence.py --inventory               # availability matrix only
"""

import argparse
import collections
import csv
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arb_extract import parse_verdict  # noqa: E402
from arb_shared_unresolved_membership import ALTERNATES, analyse  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.expanduser(
    "~/.cache/huggingface/hub/datasets--McGill-NLP--agent-reward-bench/"
    "snapshots/b6d17e646009d6cb63d5dd7be78807b680693f61"
)
RAW_FILE = os.path.join(REPO, "data", "REAL_arb_repetition_raw.jsonl")
ANNOTATIONS = os.path.join(SNAPSHOT, "data", "annotations.csv")

CAPTION_MARKER = "The detailed final state of the webpage:"


def load_annotations():
    """Keyed by (benchmark, model_name, task_id) -> list of annotator rows."""
    out = collections.defaultdict(list)
    with open(ANNOTATIONS, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[(row["benchmark"], row["model_name"], row["task_id"])].append(row)
    return out


def load_repetitions():
    """case_id -> list of the deduped current AER executions."""
    seen = set()
    out = collections.defaultdict(list)
    with open(RAW_FILE, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("call_status") != "valid":
                continue
            key = (rec["case_id"], rec["repetition_index"])
            if key in seen:
                continue
            seen.add(key)
            out[rec["case_id"]].append(rec)
    for v in out.values():
        v.sort(key=lambda r: r["repetition_index"])
    return out


def judgment_path(case_id, judge):
    benchmark, agent, task = case_id.split("/")
    return os.path.join(SNAPSHOT, "judgments", benchmark, agent, judge, task + ".json")


def load_judgment(case_id, judge):
    path = judgment_path(case_id, judge)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def judge_response_text(judgment):
    try:
        return judgment["response"]["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None


def split_aer_input(user_content):
    """Split the AER user message into (action history, final-state caption)."""
    if CAPTION_MARKER in user_content:
        history, caption = user_content.split(CAPTION_MARKER, 1)
        return history, CAPTION_MARKER + caption
    return user_content, None


def build_case(case_id, annotations, repetitions):
    benchmark, agent, task = case_id.split("/")
    aer = load_judgment(case_id, "aer")
    if aer is None:
        return {"case_id": case_id, "error": "no aer judgment file"}

    summary = aer["trajectory_info"]["summary_info"]
    cum_reward = summary.get("cum_reward")

    user_msg = aer["chat_messages"]["regular"][1]["content"]
    history, caption = split_aer_input(user_msg)

    ann_rows = annotations.get((benchmark, agent, task), [])
    reps = repetitions.get(case_id, [])

    alternates = {}
    for judge in ALTERNATES:
        j = load_judgment(case_id, judge)
        if j is None:
            alternates[judge] = {"present": False}
            continue
        success, ok = parse_verdict(judge, j)
        alternates[judge] = {
            "present": True,
            "verdict_success": success if ok else None,
            "parse_ok": ok,
            "response": judge_response_text(j),
            "judge_args": j.get("judge_args"),
            "judge_model_name": j.get("judge_model_name"),
        }

    return {
        "case_id": case_id,
        "benchmark": benchmark,
        "agent": agent,
        "task_id": task,
        "goal": aer["goal"],
        "expert_annotations": ann_rows,
        "n_annotators": len(ann_rows),
        "trajectory": {
            "n_steps": summary.get("n_steps"),
            "cum_reward": cum_reward,
            "cum_raw_reward": summary.get("cum_raw_reward"),
            "terminated": summary.get("terminated"),
            "truncated": summary.get("truncated"),
            "err_msg": summary.get("err_msg"),
            "trajectory_dir": aer["trajectory_info"].get("trajectory_dir"),
        },
        "functional_primary_verdict_success": 1 if (cum_reward or 0) > 0.5 else 0,
        "aer_input": {
            "system": aer["chat_messages"]["regular"][0]["content"],
            "action_history": history,
            "final_state_caption": caption,
            "caption_present": caption is not None,
            "total_chars": len(user_msg),
            "judge_args": aer.get("judge_args"),
        },
        "aer_historical": {
            "verdict_success": parse_verdict("aer", aer)[0],
            "response": judge_response_text(aer),
            "model": aer.get("judge_model_name"),
            "completion_args": aer.get("completion_args"),
            "created": aer["response"].get("created"),
        },
        "aer_current_r5": [
            {
                "repetition_index": r["repetition_index"],
                "verdict_correct_success": r["verdict_correct_success"],
                "verdict_raw": r["verdict_raw"],
                "is_correct": r["is_correct"],
                "system_fingerprint": r.get("system_fingerprint"),
                "response_content": r.get("response_content"),
            }
            for r in reps
        ],
        "k_of_5": sum(1 for r in reps if r["is_correct"]),
        "alternates": alternates,
    }


def inventory_row(case):
    """Per-case evidence availability, for the Phase 0 inventory table."""
    ann = case["expert_annotations"]
    return {
        "case_id": case["case_id"],
        "goal": bool(case["goal"]),
        "expert_label": bool(ann),
        "expert_free_text_rationale": False,  # annotations.csv has no rationale column
        "expert_side_effect": bool(ann) and bool(ann[0].get("trajectory_side_effect")),
        "expert_looping": bool(ann) and bool(ann[0].get("trajectory_looping")),
        "expert_optimality": bool(ann) and bool(ann[0].get("trajectory_optimality")),
        "n_annotators": len(ann),
        "action_history_in_aer_input": bool(case["aer_input"]["action_history"]),
        "final_state_caption": case["aer_input"]["caption_present"],
        "raw_screenshots": False,  # not present in this snapshot
        "raw_axtree_or_dom": False,  # not present in this snapshot
        "aer_chat_messages": True,
        "aer_historical_response": bool(case["aer_historical"]["response"]),
        "aer_current_responses": len(case["aer_current_r5"]),
        "functional_cum_reward": case["trajectory"]["cum_reward"] is not None,
        "alternates_with_response": sum(
            1 for a in case["alternates"].values() if a.get("response")
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="directory to write per-case JSON bundles")
    ap.add_argument("--inventory", action="store_true", help="print availability matrix")
    ap.add_argument("--stratum", default="missed_failure",
                    choices=["missed_failure", "false_alarm"])
    args = ap.parse_args()

    loose, strict, _ = analyse(args.stratum)
    annotations = load_annotations()
    repetitions = load_repetitions()

    cases = [build_case(cid, annotations, repetitions) for cid in loose]

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        for case in cases:
            name = case["case_id"].replace("/", "__") + ".json"
            with open(os.path.join(args.out, name), "w", encoding="utf-8") as f:
                json.dump(case, f, indent=2)
        print(f"wrote {len(cases)} bundles to {args.out}")

    if args.inventory:
        rows = [inventory_row(c) for c in cases]
        keys = list(rows[0])
        print("\t".join(keys))
        for r in rows:
            print("\t".join(str(r[k]) for k in keys))

    print(f"\nstratum={args.stratum}  two-evaluator={len(loose)}  A1.6-strict={len(strict)}")


if __name__ == "__main__":
    main()
