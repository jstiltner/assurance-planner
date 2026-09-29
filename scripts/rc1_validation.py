"""RC1 validation: joins pre-outcome firings with reward and computes preregistered metrics.

Run after Commit C (pre-outcome artifact exists).  This script is the reward unlock.
"""
import sys, json
sys.path.insert(0, 'scripts')
from tau_bench_ingest import load_corpus
from tau_bench_rc1 import run_corpus, AttemptState
from collections import Counter, defaultdict

TRAJ_DIR = "data/tau_bench_trajectories"
DEFAULT_FILES = [
    "gpt-4o-airline.json",
    "gpt-4o-retail.json",
    "sonnet-35-new-airline.json",
    "sonnet-35-new-retail.json",
]

# Outcome-free records
records = load_corpus(TRAJ_DIR)

# Load raw to extract reward (first reward read in this pipeline)
#
# The join key MUST include agent.  task_id/trial/domain collide across the two
# agents: both agent files cover the same task_ids, and gpt-4o's trials 0-3 are a
# subset of sonnet's 0-7.  Keying without agent silently overwrote all 660 gpt-4o
# rewards with sonnet's.  The collision assertion below makes a recurrence loud.
raw_by_key = {}
n_raw = 0
for fname in DEFAULT_FILES:
    path = f"{TRAJ_DIR}/{fname}"
    with open(path, encoding="utf-8") as f:
        raw_data = json.load(f)
    domain = "airline" if "airline" in fname else "retail"
    agent = "gpt-4o" if fname.startswith("gpt-4o") else "sonnet-3.5-new"
    for raw in raw_data:
        key = (int(raw["task_id"]), int(raw["trial"]), domain, agent)
        assert key not in raw_by_key, f"duplicate reward key: {key}"
        raw_by_key[key] = float(raw.get("reward", float("nan")))
        n_raw += 1
assert len(raw_by_key) == n_raw == len(records), (
    f"join key is not 1:1 -- keys={len(raw_by_key)} raw={n_raw} records={len(records)}"
)

# RC1 (no reward)
results = run_corpus(records)

# Join
joined = []
for r, res in zip(records, results):
    key = (r.task_id, r.trial, r.domain, r.agent)
    assert key in raw_by_key, f"unmatched record: {key}"
    reward = raw_by_key[key]
    joined.append({
        "task_id": r.task_id,
        "trial": r.trial,
        "domain": r.domain,
        "agent": r.agent,
        "state": res.state.value,
        "fires": res.fires,
        "reward": reward,
        "reference_pass": reward >= 1.0,
        "reference_fail": reward < 1.0,
    })

n = len(joined)
fires_all = [x for x in joined if x["fires"]]
fires_n = len(fires_all)
fires_frac = fires_n / n

base_fail_n = sum(1 for x in joined if x["reference_fail"])
base_fail_rate = base_fail_n / n

fire_fail_n = sum(1 for x in fires_all if x["reference_fail"])
fire_pass_n = sum(1 for x in fires_all if x["reference_pass"])
fire_fail_rate = fire_fail_n / fires_n if fires_n > 0 else 0
lift_traj = fire_fail_rate / base_fail_rate if base_fail_rate > 0 else float("inf")
harm_rate = fire_pass_n / fires_n if fires_n > 0 else 0

# Task-level
task_data = defaultdict(lambda: {"fires": 0, "total": 0, "fail_fires": 0, "fail_total": 0})
for x in joined:
    key = (x["domain"], x["task_id"])
    task_data[key]["total"] += 1
    if x["reference_fail"]:
        task_data[key]["fail_total"] += 1
    if x["fires"]:
        task_data[key]["fires"] += 1
        if x["reference_fail"]:
            task_data[key]["fail_fires"] += 1

task_fired = {k for k, v in task_data.items() if v["fires"] > 0}
tasks_fired_n = len(task_fired)
task_base_fail = sum(1 for k in task_data if task_data[k]["fail_total"] > 0) / len(task_data)
task_fire_fail = sum(1 for k in task_fired if task_data[k]["fail_fires"] > 0) / tasks_fired_n if tasks_fired_n > 0 else 0
lift_task = task_fire_fail / task_base_fail if task_base_fail > 0 else float("inf")

print("=" * 60)
print("RC1 VALIDATION RESULTS")
print("=" * 60)

print(f"\n--- Base rates ---")
print(f"Records: {n}")
print(f"Reference FAIL: {base_fail_n}/{n} ({100*base_fail_rate:.1f}%)")
print(f"Reference PASS: {n-base_fail_n}/{n} ({100*(1-base_fail_rate):.1f}%)")

print(f"\n--- State distribution ---")
state_counts = Counter(x["state"] for x in joined)
for state, count in sorted(state_counts.items()):
    print(f"  {state}: {count} ({100*count/n:.1f}%)")

print(f"\n--- A1: Volume ---")
print(f"Fires: {fires_n}/{n} ({100*fires_frac:.1f}%)")
print(f"Threshold: <15%. A1: {'PASS' if fires_frac < 0.15 else 'FAIL'}")

print(f"\n--- A2: Enrichment (trajectory level) ---")
print(f"Fail rate among fires: {fire_fail_n}/{fires_n} ({100*fire_fail_rate:.1f}%)")
print(f"Fail rate base: {100*base_fail_rate:.1f}%")
print(f"Lift: {lift_traj:.3f}x")
print(f"Threshold: >=1.50x. A2-traj: {'PASS' if lift_traj >= 1.50 else 'FAIL'}")

print(f"\n--- A2: Enrichment (task level) ---")
print(f"Tasks: {len(task_data)} total, {tasks_fired_n} fired")
print(f"Tasks with any fail among fired: {sum(1 for k in task_fired if task_data[k]['fail_fires']>0)}/{tasks_fired_n} ({100*task_fire_fail:.1f}%)")
print(f"Tasks with any fail, base: {sum(1 for k in task_data if task_data[k]['fail_total']>0)}/{len(task_data)} ({100*task_base_fail:.1f}%)")
print(f"Lift: {lift_task:.3f}x")
print(f"Threshold: >=1.25x. A2-task: {'PASS' if lift_task >= 1.25 else 'FAIL'}")

print(f"\n--- Harm rate ---")
print(f"Fires on reference PASS (harm): {fire_pass_n}/{fires_n} ({100*harm_rate:.1f}%)")

print(f"\n--- UNDERPOWERED-REGARDLESS ---")
print(f"Distinct tasks fired: {tasks_fired_n}")
print(f"Threshold: <30 distinct tasks = UNDERPOWERED.")
print(f"Result: {'ADEQUATE' if tasks_fired_n >= 30 else 'UNDERPOWERED'}")

print(f"\n--- Counterfactual veto (reported, never applied) ---")
print(f"Would help: {fire_fail_n} (fired on reference fail)")
print(f"Would harm: {fire_pass_n} (fired on reference pass)")
print(f"Net: {fire_fail_n - fire_pass_n:+d}")

print(f"\n--- By domain ---")
for domain in ["airline", "retail"]:
    rows = [x for x in joined if x["domain"] == domain]
    fires_d = [x for x in rows if x["fires"]]
    br = sum(1 for x in rows if x["reference_fail"]) / len(rows)
    fr = (sum(1 for x in fires_d if x["reference_fail"]) / len(fires_d)) if fires_d else 0
    lf = fr / br if br > 0 else float("inf")
    print(f"  {domain}: {len(fires_d)}/{len(rows)} fires ({100*len(fires_d)/len(rows):.1f}%), "
          f"fail-in-fires={100*fr:.1f}%, base={100*br:.1f}%, lift={lf:.3f}x")

print(f"\n--- By agent ---")
for agent in ["gpt-4o", "sonnet-3.5-new"]:
    rows = [x for x in joined if x["agent"] == agent]
    fires_a = [x for x in rows if x["fires"]]
    br = sum(1 for x in rows if x["reference_fail"]) / len(rows) if rows else 0
    fr = (sum(1 for x in fires_a if x["reference_fail"]) / len(fires_a)) if fires_a else 0
    lf = fr / br if br > 0 else float("inf")
    print(f"  {agent}: {len(fires_a)}/{len(rows)} fires ({100*len(fires_a)/len(rows):.1f}%), "
          f"fail-in-fires={100*fr:.1f}%, base={100*br:.1f}%, lift={lf:.3f}x")

a1 = fires_frac < 0.15
a2_traj = lift_traj >= 1.50
a2_task = lift_task >= 1.25
a3 = True  # Commit B: 28/30

print(f"\n{'=' * 60}")
print(f"DECISION (preregistration section 11)")
print(f"{'=' * 60}")
print(f"A1 volume <15%:          {'PASS' if a1 else 'FAIL'} ({100*fires_frac:.1f}%)")
print(f"A2 lift >=1.50x traj:    {'PASS' if a2_traj else 'FAIL'} ({lift_traj:.3f}x)")
print(f"A2 lift >=1.25x task:    {'PASS' if a2_task else 'FAIL'} ({lift_task:.3f}x)")
print(f"A3 extractor >=27/30:    PASS (28/30, Commit B)")
if tasks_fired_n < 30:
    print(f"\nRC1 is UNDERPOWERED-REGARDLESS ({tasks_fired_n} distinct tasks < 30).")
elif not a1 or not (a2_traj and a2_task):
    print(f"\nRC1 VERDICT: REJECTED")
    if not a1: print(f"  - A1 fails: volume {100*fires_frac:.1f}% exceeds 15% ceiling.")
    if not a2_traj: print(f"  - A2 fails: trajectory lift {lift_traj:.3f}x < 1.50x.")
    if not a2_task: print(f"  - A2 fails: task lift {lift_task:.3f}x < 1.25x.")
    print(f"  RC1 stays frozen in its failing form per preregistration section 13.")
else:
    print(f"\nRC1 VERDICT: ACCEPTED")

# Save
with open("data/rc1_outcome_joined.json", "w", encoding="utf-8") as f:
    json.dump(joined, f, indent=2)
print(f"\nJoined artifact saved: data/rc1_outcome_joined.json")
