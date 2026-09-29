"""Investigate the 28 cases where oracle GT requires a write, agent performed none, reward=1.0.

Characterises possible explanations; does NOT relabel or subtract cases.
"""
import json
import sys
from collections import Counter
sys.path.insert(0, "scripts")
from tau_bench_ingest import ALL_WRITE_TOOLS

DIR = "data/tau_bench_trajectories"
FILES = [
    ("gpt-4o-airline.json",        "airline", "gpt-4o"),
    ("gpt-4o-retail.json",         "retail",  "gpt-4o"),
    ("sonnet-35-new-airline.json", "airline", "sonnet-3.5-new"),
    ("sonnet-35-new-retail.json",  "retail",  "sonnet-3.5-new"),
]

cases = []
for fname, dom, ag in FILES:
    with open(f"{DIR}/{fname}", encoding="utf-8") as fh:
        raw = json.load(fh)
    for r in raw:
        task = (r.get("info") or {}).get("task") or {}
        gt = [a for a in (task.get("actions") or [])
              if a["name"] in ALL_WRITE_TOOLS]
        did = set()
        for msg in r.get("traj") or []:
            for tc in msg.get("tool_calls") or []:
                name = (tc.get("function") or {}).get("name", "")
                if name in ALL_WRITE_TOOLS:
                    did.add(name)
        ri = r.get("reward_info") or {}
        ri_info = ri.get("info") or {}
        if gt and not did and float(r["reward"]) >= 1.0:
            cases.append({
                "task_id": r["task_id"], "trial": r["trial"],
                "domain": dom, "agent": ag,
                "reward": float(r["reward"]),
                "gt_actions": [a["name"] for a in gt],
                "gt_instruction": (task.get("instruction") or "")[:500],
                "gt_outputs": task.get("outputs") or [],
                # reward_info breakdown
                "r_actions": ri_info.get("r_actions"),
                "r_outputs": ri_info.get("r_outputs"),
                "reward_info_actions": [a["name"] for a in (ri.get("actions") or [])],
            })

print("=" * 74)
print(f"28 WRITE/REWARD CONTRADICTIONS  (oracle GT requires write, "
      f"agent did none, reward=1.0)")
print(f"Total found: {len(cases)}  (expected 28)")
print("=" * 74)

print(f"\nGT action distribution:")
for k, v in Counter(a for c in cases for a in c["gt_actions"]).most_common():
    print(f"  {v:3d}  {k}")

print(f"\nr_actions breakdown:")
for k, v in Counter(c["r_actions"] for c in cases).most_common():
    print(f"  {v:3d}  r_actions={k}")

print(f"\nCases with gt_outputs (text/info tasks): "
      f"{sum(1 for c in cases if c['gt_outputs'])}")

print(f"\nAll 28 cases:")
for c in cases:
    print(f"  task={c['task_id']:3d} t={c['trial']} {c['domain']:8s} {c['agent']:16s}"
          f"  r_actions={c['r_actions']}  gt_acts={c['gt_actions']}")

print()
print("=" * 74)
print("INTERPRETATION")
print("=" * 74)
ra0 = [c for c in cases if c["r_actions"] == 0.0]
ra1 = [c for c in cases if c["r_actions"] == 1.0]
rana = [c for c in cases if c["r_actions"] is None]
print(f"\n  r_actions=1.0 (action component of reward is 1.0): {len(ra1)}")
print(f"  r_actions=0.0 (action component of reward is 0.0): {len(ra0)}")
print(f"  r_actions=None (not in reward_info.info):           {len(rana)}")

print(f"""
  r_actions is tau-bench's action-accuracy sub-score (whether the recorded
  agent actions match the reference).  reward_info.info.r_actions=1.0 means
  the benchmark's own action scorer agreed that the agent satisfied the
  reference actions -- even though the raw trajectory shows no write tool call.

  Possible explanations (not mutually exclusive):
  (a) r_actions=1.0 is computed on reward_info.actions, not on traj tool_calls.
      If reward_info.actions lists an action the agent performed through a
      different path (or if reward_info is populated from the reference rather
      than the agent), the score can be 1.0 while the traj shows no write.
  (b) The benchmark may count satisfying the task as-is (state already correct)
      as action-accuracy 1.0 without requiring a write.
  (c) The benchmark may count certain text outputs as equivalent to a write for
      scoring purposes (e.g., informing the user of an impossibility).
  (d) Benchmark scoring inconsistency: the reference solution lists an action
      that was never executed and the scorer misgraded.

  Of the {len(ra1)} cases with r_actions=1.0: these are most likely (b) or (c).
  The task instruction probably describes a conditional: 'if X is possible,
  do Y; otherwise inform the user'.  The agent handled the 'otherwise' branch
  without writing, and the benchmark scored that as correct.
""")

# Show r_actions=0 cases -- these may be the genuine scoring errors
if ra0:
    print(f"  r_actions=0.0 cases ({len(ra0)}) -- more likely genuine scoring issues:")
    for c in ra0:
        print(f"    task={c['task_id']} t={c['trial']} {c['domain']} {c['agent']}")
        print(f"      gt_actions={c['gt_actions']}")
        print(f"      instruction: {c['gt_instruction'][:200].encode('ascii','replace').decode()}")

print(f"""
  CONSERVATIVE TREATMENT: report this set as a reference-reliability noise
  floor of {len(cases)}/{1980} = {100*len(cases)/1980:.1f}% of records ({len(set((c['domain'],c['task_id']) for c in cases))} distinct tasks).
  Do NOT subtract from any metric.
  Do NOT relabel.
  The true rate of scoring inconsistency is unknown without manual review.
""")
