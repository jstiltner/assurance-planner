"""Post-outcome correction: recompute every reward-conditioned figure in the RC1 report.

WHY THIS EXISTS
---------------
The original Commit D join keyed rewards on (task_id, trial, domain).  That key is not
unique: both agents cover the same task_ids, and gpt-4o's trials 0-3 are a subset of
sonnet's 0-7.  Because DEFAULT_FILES lists sonnet last, sonnet's rewards overwrote all
660 gpt-4o entries -- 33.3% of the corpus was paired with the wrong agent's outcome.

This script recomputes the report's tables from the corrected join.  It does NOT touch
RC1, the preregistration, or the pre-outcome firing artifact.  A1 (volume) reads no
reward and is unaffected; the REJECTED disposition is unchanged.

Run after scripts/rc1_validation.py has regenerated data/rc1_outcome_joined.json.
"""
import json
import random
import sys
from collections import defaultdict

sys.path.insert(0, "scripts")
from tau_bench_ingest import load_corpus

SEED = 20260929

with open("data/rc1_outcome_joined.json", encoding="utf-8") as f:
    joined = json.load(f)

with open("data/rc1_pre_outcome_firings.json", encoding="utf-8") as f:
    pre = json.load(f)

# Index the pre-outcome artifact on the FULL key so the qualitative sample pulls the
# trajectory that actually fired, not a same-task/same-trial record from the other agent.
pre_idx = {(p["task_id"], p["trial"], p["domain"], p["agent"]): p for p in pre}
assert len(pre_idx) == len(pre), "pre-outcome artifact key is not 1:1"

rec_idx = {(r.task_id, r.trial, r.domain, r.agent): r
           for r in load_corpus("data/tau_bench_trajectories")}
assert len(rec_idx) == len(pre), "corpus key is not 1:1"

n = len(joined)
fires = [x for x in joined if x["fires"]]
base_fail_n = sum(1 for x in joined if x["reference_fail"])
base_rate = base_fail_n / n
fire_fail_n = sum(1 for x in fires if x["reference_fail"])
fire_pass_n = len(fires) - fire_fail_n

print("=" * 72)
print("RC1 REPORT CORRECTION -- reward-conditioned figures, corrected join key")
print("=" * 72)

print("\n-- sec 6: trajectory enrichment --")
print(f"  All trajectories : {n:5d}  fail={base_fail_n:4d}  ({100*base_rate:.1f}%)")
print(f"  Fires            : {len(fires):5d}  fail={fire_fail_n:4d}  "
      f"({100*fire_fail_n/len(fires):.1f}%)")
print(f"  Lift = {(fire_fail_n/len(fires))/base_rate:.3f}x")

print("\n-- sec 7: task enrichment --")
task = defaultdict(lambda: {"fires": 0, "fail_fires": 0, "fail_total": 0, "total": 0})
for x in joined:
    k = (x["domain"], x["task_id"])
    task[k]["total"] += 1
    if x["reference_fail"]:
        task[k]["fail_total"] += 1
    if x["fires"]:
        task[k]["fires"] += 1
        if x["reference_fail"]:
            task[k]["fail_fires"] += 1
fired = {k for k, v in task.items() if v["fires"] > 0}
all_anyfail = sum(1 for v in task.values() if v["fail_total"] > 0)
fired_anyfail = sum(1 for k in fired if task[k]["fail_fires"] > 0)
print(f"  All tasks        : {len(task):5d}  any-fail={all_anyfail:4d}  "
      f"({100*all_anyfail/len(task):.1f}%)")
print(f"  Fired tasks      : {len(fired):5d}  any-fail-fire={fired_anyfail:4d}  "
      f"({100*fired_anyfail/len(fired):.1f}%)")
print(f"  Lift = {(fired_anyfail/len(fired))/(all_anyfail/len(task)):.3f}x")

print("\n-- sec 9/10: harm and counterfactual veto --")
print(f"  Help (fire on fail): {fire_fail_n}")
print(f"  Harm (fire on pass): {fire_pass_n}  ({100*fire_pass_n/len(fires):.1f}% of fires)")
print(f"  Net: {fire_fail_n - fire_pass_n:+d}")

print("\n-- sec 11/17: state distribution and per-state fail rate --")
by_state = defaultdict(list)
for x in joined:
    by_state[x["state"]].append(x)
for st in sorted(by_state, key=lambda s: -len(by_state[s])):
    rows = by_state[st]
    fr = sum(1 for x in rows if x["reference_fail"]) / len(rows)
    print(f"  {st:32s} n={len(rows):4d} ({100*len(rows)/n:5.1f}%)  "
          f"fail={100*fr:5.1f}%  lift={fr/base_rate:.3f}x")

print("\n-- sec 13: by domain --")
for d in ("airline", "retail"):
    rows = [x for x in joined if x["domain"] == d]
    fd = [x for x in rows if x["fires"]]
    br = sum(1 for x in rows if x["reference_fail"]) / len(rows)
    fr = sum(1 for x in fd if x["reference_fail"]) / len(fd)
    print(f"  {d:8s} n={len(rows):4d} fires={len(fd):4d} ({100*len(fd)/len(rows):.1f}%) "
          f"fail-in-fires={100*fr:.1f}% base={100*br:.1f}% lift={fr/br:.3f}x")

print("\n-- sec 14: by agent --")
for a in ("gpt-4o", "sonnet-3.5-new"):
    rows = [x for x in joined if x["agent"] == a]
    fd = [x for x in rows if x["fires"]]
    br = sum(1 for x in rows if x["reference_fail"]) / len(rows)
    fr = sum(1 for x in fd if x["reference_fail"]) / len(fd)
    print(f"  {a:16s} n={len(rows):4d} fires={len(fd):4d} ({100*len(fd)/len(rows):.1f}%) "
          f"fail-in-fires={100*fr:.1f}% base={100*br:.1f}% lift={fr/br:.3f}x")

print("\n-- sec 15: concentration --")
universal = sorted(k for k, v in task.items() if v["fires"] == v["total"] and v["fires"] > 0)
mixed = [k for k, v in task.items() if 0 < v["fires"] < v["total"]]
never = [k for k, v in task.items() if v["fires"] == 0]
print(f"  Universal-fire tasks: {len(universal)}")
for k in universal:
    v = task[k]
    print(f"    {k[0]} {k[1]}: {v['fires']}/{v['total']} fire, "
          f"{v['fail_fires']} fail-fires, {v['fail_total']}/{v['total']} reference fail")
print(f"  Mixed tasks: {len(mixed)}   Never-fire tasks: {len(never)} "
      f"({100*len(never)/len(task):.1f}%)")
fracs = sorted(task[k]["fires"] / task[k]["total"] for k in fired)
mean = sum(fracs) / len(fracs)
var = sum((x - mean) ** 2 for x in fracs) / (len(fracs) - 1)
print(f"  Fire fraction among fired tasks: mean={mean:.2f} "
      f"median={fracs[len(fracs)//2]:.2f} stdev={var**0.5:.2f}")

# ---- sec 18: re-draw the harm sample against the corrected index ----
print("\n-- sec 18: harm-case sample (seed %d), corrected trajectory lookup --" % SEED)
harm = sorted(
    (x for x in fires if x["reference_pass"]),
    key=lambda x: (x["domain"], x["task_id"], x["trial"], x["agent"]),
)
rng = random.Random(SEED)
sample = rng.sample(harm, 15)
out = []
for x in sample:
    k = (x["task_id"], x["trial"], x["domain"], x["agent"])
    p = pre_idx[k]
    r = rec_idx[k]
    rec = {
        "key": list(k),
        "obligations": p["obligations"],
        "never_attempted_indices": p["never_attempted_indices"],
        "called_write_tools": p["called_write_tools"],
        "all_tools_in_order": [tc.name for tc in r.tool_calls],
        "reason": p["reason"],
        "user_turns": list(r.user_turns),
    }
    out.append(rec)
    ob = "; ".join(f"{o['action_class']}~{o['object_phrase']}" for o in rec["obligations"])
    print(f"\n  {x['domain']} task={x['task_id']} trial={x['trial']} agent={x['agent']}")
    print(f"    obligation  : {ob}")
    print(f"    write calls : {rec['called_write_tools']}")
    turn = (r.user_turns[0] if r.user_turns else "")[:200]
    print("    user turn 1 : " + turn.replace("\n", " ").encode("ascii", "replace").decode())

with open("data/rc1_harm_sample_corrected.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("\nHarm sample written: data/rc1_harm_sample_corrected.json")
