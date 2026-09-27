"""Extract a compact per-(case, judge) record from the AgentRewardBench cache.

Reuses the upstream label-resolution and verdict-parsing semantics verbatim, from
McGill-NLP/agent-reward-bench @ 05899fcfe52c925978944a23920373b7a9c63740:

  - reference label  : annotations.csv, *primary* annotator only (first row for a
                       (benchmark, model_name, task_id) triple), "Unsure" dropped.
                       This is scripts/score_judgments.py's rule, not one invented here.
  - split filter     : splits.csv on the normalised task id (strip .resized/.improved).
  - functional judge : cum_reward > 0.5.
  - aer / aerv       : the "Status:" line.
  - nnetnav          : the "Reward:" Likert-5, binarised at >= 4.
  - everything else  : the <success> tag.
  - invalid judgment : upstream substitutes "n/a"; here it stays MISSING.

Writes ``$ARB_WORKDIR/arb_records.csv`` (default: the system temp directory) with one
row per (case, judge).  The intermediate stays outside the repository deliberately: it
is a ~2.3 MB derivative of a dataset whose Terms of Use must travel with every copy,
and nothing downstream needs it committed -- ``arb_gate1.py`` regenerates from it, and
the small artifacts that are committed carry the terms in their own headers.
"""

import csv
import glob
import json
import os
import tempfile

#: The upstream dataset revision.  Pinned rather than tracking main: every number in
#: docs/agent_reward_bench_gate1.md is a claim about this snapshot and no other.
REV = "b6d17e646009d6cb63d5dd7be78807b680693f61"
CACHE = os.path.join(
    os.path.expanduser("~"),
    ".cache", "huggingface", "hub",
    "datasets--McGill-NLP--agent-reward-bench", "snapshots", REV,
)
DATA = os.path.join(CACHE, "data")
JUDGMENTS = os.path.join(CACHE, "judgments")
WORKDIR = os.environ.get("ARB_WORKDIR") or tempfile.gettempdir()


# --- upstream semantics, transcribed ----------------------------------------------

def normalize_task_id(task_id):
    for remove in [".resized", ".improved"]:
        task_id = task_id.replace(remove, "")
    return task_id


def is_unsure(label):
    return label == "Unsure" or label is None


def get_content_inside_tag(tag, msg):
    start, end = f"<{tag}>", f"</{tag}>"
    i, j = msg.find(start), msg.find(end)
    if i == -1 or j == -1:
        return None
    return msg[i + len(start): j]


def clean_label(label):
    if label is None or label == "":
        return None
    return label.strip().lower().replace("'", "").replace('"', "")


def numerize_success(label):
    """Upstream numerize(), restricted to the binary success vocabulary.

    Returns 1 (successful), 0 (unsuccessful) or None (unparseable / n/a).
    Upstream maps "n/a" to -1 and an unparseable label to 0 with a warning; both of
    those silently become a *wrong prediction* rather than a missing one, so the
    divergence is deliberate and is recorded per row as parse_ok.
    """
    label = clean_label(label)
    if label is None or label == "n/a":
        return None
    if label in ("successful", "yes", "success"):
        return 1
    if label in ("unsuccessful", "no", "failure", "unsuccesful"):
        return 0
    return None


def parse_verdict(judge, judgment):
    """Return (success_1_0_or_None, parse_ok)."""
    if judge == "functional":
        cum = judgment["trajectory_info"]["summary_info"]["cum_reward"]
        return (1 if cum > 0.5 else 0), True

    resp = judgment.get("response")
    if not resp or not resp.get("choices"):
        return None, False
    msg = resp["choices"][0]["message"]["content"]
    if msg is None:
        return None, False

    if judge in ("aer", "aerv"):
        raw = None
        for line in msg.split("\n"):
            if line.startswith("Status:"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    raw = parts[1].strip()
        return numerize_success(raw), raw is not None

    if judge == "nnetnav":
        if "Reward:" not in msg:
            return None, False
        tail = msg.split("Reward:", 1)[1].strip()
        if not tail.isdigit():
            return None, False
        return (1 if int(tail) >= 4 else 0), True

    raw = get_content_inside_tag("success", msg)
    return numerize_success(raw), raw is not None


# --- load reference labels ---------------------------------------------------------

def load_reference():
    with open(os.path.join(DATA, "splits.csv"), newline="", encoding="utf-8") as f:
        splits = {r["task_id"]: r["split"] for r in csv.DictReader(f)}
    with open(os.path.join(DATA, "annotations.csv"), newline="", encoding="utf-8") as f:
        annotations = list(csv.DictReader(f))

    seen = set()
    ref = {}
    for a in annotations:
        key = (a["benchmark"], a["model_name"], a["task_id"])
        if key in seen:
            continue  # secondary annotator: IAA only, never the reference label
        seen.add(key)
        ref[key] = {
            "annotator": a["annotator_name"],
            "success": a["trajectory_success"],
            "side_effect": a["trajectory_side_effect"],
            "looping": a["trajectory_looping"],
            "split": splits[normalize_task_id(a["task_id"])],
        }
    return ref, annotations


def main():
    ref, annotations = load_reference()
    n_secondary = len(annotations) - len(ref)
    print(f"annotations rows={len(annotations)} primary={len(ref)} secondary={n_secondary}")

    rows = []
    paths = glob.glob(os.path.join(JUDGMENTS, "**", "*.json"), recursive=True)
    print(f"judgment files on disk: {len(paths)}")

    for p in paths:
        parts = p.split(os.sep)
        benchmark, agent, judge = parts[-4], parts[-3], parts[-2]
        task_id = os.path.basename(p)[:-len(".json")]
        key = (benchmark, agent, task_id)
        meta = ref.get(key)
        if meta is None:
            continue  # a judgment with no expert annotation

        with open(p, encoding="utf-8") as f:
            j = json.load(f)

        verdict, parse_ok = parse_verdict(judge, j)
        cost = j.get("cost")
        if isinstance(cost, dict):
            total_price = cost.get("total_price")
        elif isinstance(cost, (int, float)):
            total_price = None  # functional: literal 0, which is "no model call", not a price
        else:
            total_price = None

        usage = ((j.get("response") or {}).get("usage")) or {}

        rows.append({
            "benchmark": benchmark,
            "agent": agent,
            "task_id": task_id,
            "split": meta["split"],
            "judge": judge,
            "judge_model_name": j.get("judge_model_name", ""),
            "provider": j.get("provider", ""),
            "use_screenshot": (j.get("judge_args") or {}).get("use_screenshot", ""),
            "use_axtree": (j.get("judge_args") or {}).get("use_axtree", ""),
            "ref_success": meta["success"],
            "ref_annotator": meta["annotator"],
            "judge_success": "" if verdict is None else verdict,
            "parse_ok": int(parse_ok),
            "cum_reward": j["trajectory_info"]["summary_info"]["cum_reward"],
            "total_price_usd": "" if total_price is None else total_price,
            "prompt_tokens": usage.get("prompt_tokens", ""),
            "completion_tokens": usage.get("completion_tokens", ""),
            "response_created": (j.get("response") or {}).get("created", ""),
        })

    out = os.path.join(WORKDIR, "arb_records.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out}")

    #: Per-judge coverage, printed because a partially fetched judge is otherwise
    #: invisible downstream: it would enter a pair audit as a judge with adequate
    #: provenance and two cases of support.  Only judges at full coverage are
    #: candidates; arb_gate1.py enforces that with an explicit allow-list.
    counts = {}
    for r in rows:
        counts[r["judge"]] = counts.get(r["judge"], 0) + 1
    full = max(counts.values())
    for judge, n in sorted(counts.items()):
        flag = "" if n == full else "  <-- PARTIAL, not a candidate"
        print(f"  {judge:32s} {n:5d}{flag}")


if __name__ == "__main__":
    main()
