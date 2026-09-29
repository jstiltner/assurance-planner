"""Freeze the discovery/validation split for the candidate-repair experiment.

The 15 cases in `data/shared_unresolved_case_review.csv` were read in depth to
derive the candidate rules. They are DISCOVERY data and may not be used to argue
that those rules work.

Leakage is not only case-level. A rule derived from case X on task T under agent A
has effectively seen task T: the goal text is identical, the application is
identical, and in several instances the trajectory is near-identical across agents.
So the quarantine is at TASK level, not case level: every (benchmark, task_id) that
appears in discovery is removed entirely, along with all of its same-task siblings
under other agents.

Emits `data/REAL_arb_discovery_validation_split.json`. Contains no outcomes.

Usage:
  python scripts/arb_discovery_validation_split.py
"""

import collections
import csv
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.expanduser(
    "~/.cache/huggingface/hub/datasets--McGill-NLP--agent-reward-bench/"
    "snapshots/b6d17e646009d6cb63d5dd7be78807b680693f61"
)
REVIEW_CSV = os.path.join(REPO, "data", "shared_unresolved_case_review.csv")
ANNOTATIONS = os.path.join(SNAPSHOT, "data", "annotations.csv")
OUT = os.path.join(REPO, "data", "REAL_arb_discovery_validation_split.json")


def corpus():
    """Every annotated case, first-annotator dedup, as the study defines it."""
    seen = set()
    out = []
    with open(ANNOTATIONS, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (row["benchmark"], row["model_name"], row["task_id"])
            if key in seen:
                continue
            seen.add(key)
            out.append(key)
    return out


def main():
    with open(REVIEW_CSV, newline="", encoding="utf-8") as fh:
        discovery = [r["case_id"] for r in csv.DictReader(fh)]

    discovery_tasks = set()
    for cid in discovery:
        benchmark, _agent, task = cid.split("/")
        discovery_tasks.add((benchmark, task))

    all_cases = corpus()
    by_task = collections.defaultdict(list)
    for benchmark, agent, task in all_cases:
        by_task[(benchmark, task)].append(agent)

    quarantined, validation = [], []
    for benchmark, agent, task in all_cases:
        cid = f"{benchmark}/{agent}/{task}"
        if (benchmark, task) in discovery_tasks:
            quarantined.append(cid)
        else:
            validation.append(cid)

    siblings = [c for c in quarantined if c not in set(discovery)]

    # Sensitivity arm: the R1 mechanism was found on a workarena infeasible-* task.
    # The family shares construction, so a stricter arm removes all of it.
    infeasible_family = [c for c in validation if "infeasible" in c.split("/")[2]]
    validation_strict = [c for c in validation if c not in set(infeasible_family)]

    split = {
        "frozen": "2026-09-29",
        "corpus_n": len(all_cases),
        "discovery_n": len(discovery),
        "discovery_tasks_n": len(discovery_tasks),
        "sibling_n": len(siblings),
        "quarantined_n": len(quarantined),
        "validation_n": len(validation),
        "validation_strict_n": len(validation_strict),
        "infeasible_family_in_validation_n": len(infeasible_family),
        "discovery": sorted(discovery),
        "siblings": sorted(siblings),
        "validation": sorted(validation),
        "validation_strict": sorted(validation_strict),
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(split, fh, indent=2)

    print(f"corpus                       {len(all_cases)}")
    print(f"discovery cases              {len(discovery)}  over {len(discovery_tasks)} tasks")
    print(f"same-task siblings removed   {len(siblings)}")
    print(f"total quarantined            {len(quarantined)}")
    print(f"VALIDATION (primary)         {len(validation)}")
    print(f"VALIDATION (strict arm)      {len(validation_strict)}"
          f"   [-{len(infeasible_family)} infeasible-* family]")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
