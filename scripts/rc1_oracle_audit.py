"""Post-outcome oracle audit of RC1.  EXPLORATORY -- not a rule, not confirmatory.

Separates two questions that RC1's rejection conflates:

  Q(a)  Is RC1 a good DETECTOR of the construct it was written to detect?
  Q(b)  Is that CONSTRUCT itself predictive of reference failure?

The construct is reconstructed from `info.task.actions` -- the reference solution's action
list.  THAT IS ORACLE DATA.  It is read here only to audit a frozen, already-rejected rule
after the fact.  It is not available in production, nothing derived from it may enter a
successor rule, and the resulting figures are a CEILING on the construct, never a forecast
for any deployable detector.

Nothing in this file modifies, reruns, or tunes RC1.

Reproduces sections 1, 3, 4 and 6 of docs/rc1_post_outcome_decomposition.md.
"""
import json
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "scripts")
from tau_bench_ingest import ALL_WRITE_TOOLS

TRAJ_DIR = "data/tau_bench_trajectories"
FILES = [
    ("gpt-4o-airline.json", "airline", "gpt-4o"),
    ("gpt-4o-retail.json", "retail", "gpt-4o"),
    ("sonnet-35-new-airline.json", "airline", "sonnet-3.5-new"),
    ("sonnet-35-new-retail.json", "retail", "sonnet-3.5-new"),
]


def load_oracle():
    """Per trajectory: write classes the reference required, and which the agent called."""
    out = {}
    for fname, domain, agent in FILES:
        with open(f"{TRAJ_DIR}/{fname}", encoding="utf-8") as fh:
            raw = json.load(fh)
        for r in raw:
            task = (r.get("info") or {}).get("task") or {}
            gt = {a["name"] for a in (task.get("actions") or [])
                  if a["name"] in ALL_WRITE_TOOLS}
            did = set()
            for msg in r.get("traj") or []:
                for tc in msg.get("tool_calls") or []:
                    name = (tc.get("function") or {}).get("name", "")
                    if name in ALL_WRITE_TOOLS:
                        did.add(name)
            out[(r["task_id"], r["trial"], domain, agent)] = {
                "gt": gt, "did": did, "missing": gt - did,
                "reward": float(r["reward"]),
            }
    return out


oracle = load_oracle()
pre = {(p["task_id"], p["trial"], p["domain"], p["agent"]): p
       for p in json.load(open("data/rc1_pre_outcome_firings.json", encoding="utf-8"))}
joined = json.load(open("data/rc1_outcome_joined.json", encoding="utf-8"))
assert len(oracle) == len(pre) == len(joined) == 1980

for x in joined:
    k = (x["task_id"], x["trial"], x["domain"], x["agent"])
    x["oracle_never"] = bool(oracle[k]["missing"])

n = len(joined)
base = sum(1 for x in joined if x["reference_fail"]) / n


def within_task_lift(flag):
    """Lift with task identity controlled -- the only quantity a deployed system can act on.

    Restricted to tasks having BOTH flagged and unflagged trials; a task where every trial
    is flagged carries no within-task contrast.
    """
    t = defaultdict(lambda: [0, 0, 0, 0])  # n, flagged, flagged_fail, fail
    for x in joined:
        d = t[(x["domain"], x["task_id"])]
        d[0] += 1
        d[3] += x["reference_fail"]
        if x[flag]:
            d[1] += 1
            d[2] += x["reference_fail"]
    mixed = [k for k, d in t.items() if 0 < d[1] < d[0]]
    ff = sum(t[k][2] for k in mixed)
    fn = sum(t[k][1] for k in mixed)
    uf = sum(t[k][3] - t[k][2] for k in mixed)
    un = sum(t[k][0] - t[k][1] for k in mixed)
    return len(mixed), ff, fn, uf, un, (ff / fn) / (uf / un)


print("=" * 74)
print("SECTION 1 -- within-task discrimination (task identity controlled)")
print("=" * 74)
for flag, label in (("fires", "RC1 (Level 0, tool-name matching)"),
                    ("oracle_never", "construct, perfectly detected (ORACLE)")):
    m, ff, fn, uf, un, lift = within_task_lift(flag)
    print(f"\n  {label}")
    print(f"    informative tasks (both flagged+unflagged trials): {m}")
    print(f"    fail rate |   flagged trials : {ff}/{fn} = {100*ff/fn:.1f}%")
    print(f"    fail rate | unflagged, same task: {uf}/{un} = {100*uf/un:.1f}%")
    print(f"    WITHIN-TASK LIFT: {lift:.3f}x")

print()
print("=" * 74)
print("SECTION 3 -- is RC1 right for the RIGHT REASON?")
print("=" * 74)


def classify(x):
    k = (x["task_id"], x["trial"], x["domain"], x["agent"])
    o, p = oracle[k], pre[k]
    claimed = set()
    for i in p["never_attempted_indices"]:
        claimed |= set(p["obligations"][i]["action_class"])
    if not o["gt"]:
        return "reference required no write at all"
    if not o["missing"]:
        return "every required write WAS performed"
    if claimed & o["missing"]:
        return "RIGHT REASON: named class genuinely missing"
    return "something missing, but not what RC1 named"


right = 0
for label, sel in (("true positives (fired, reference FAIL)",
                    lambda x: x["fires"] and x["reference_fail"]),
                   ("harms (fired, reference PASS)",
                    lambda x: x["fires"] and x["reference_pass"])):
    rows = [x for x in joined if sel(x)]
    c = Counter(classify(x) for x in rows)
    print(f"\n  {label}: n={len(rows)}")
    for k, v in c.most_common():
        print(f"    {v:4d} ({100*v/len(rows):5.1f}%)  {k}")
    right += c["RIGHT REASON: named class genuinely missing"]

rr = [x for x in joined if x["fires"]
      and classify(x) == "RIGHT REASON: named class genuinely missing"]
rrf = sum(1 for x in rr if x["reference_fail"])
print(f"\n  RC1 right-for-the-right-reason: {len(rr)}/501 = {100*len(rr)/501:.1f}% of firings")
print(f"  Restricted to those firings ONLY (diagnostic, NOT a proposed rule):")
print(f"    volume      : {len(rr)}/{n} = {100*len(rr)/n:.1f}%   (A1 <15%)")
print(f"    fail rate   : {rrf}/{len(rr)} = {100*rrf/len(rr):.1f}%")
print(f"    lift        : {(rrf/len(rr))/base:.3f}x           (A2 >=1.50x)")
print(f"    harm rate   : {100*(1-rrf/len(rr)):.1f}%")
print(f"    veto net    : {rrf-(len(rr)-rrf):+d}")

print()
print("=" * 74)
print("SECTION 4 -- Q(a) detector quality vs Q(b) construct validity")
print("=" * 74)
tp = sum(1 for x in joined if x["fires"] and x["oracle_never"])
fp = sum(1 for x in joined if x["fires"] and not x["oracle_never"])
fneg = sum(1 for x in joined if not x["fires"] and x["oracle_never"])
print(f"\n  Q(a) RC1 as a detector of the construct:")
print(f"    precision {tp}/{tp+fp} = {100*tp/(tp+fp):.1f}%   "
      f"recall {tp}/{tp+fneg} = {100*tp/(tp+fneg):.1f}%")
on = [x for x in joined if x["oracle_never"]]
onf = sum(1 for x in on if x["reference_fail"])
print(f"\n  Q(b) the construct itself (ORACLE ceiling -- NOT deployable):")
print(f"    volume    : {len(on)}/{n} = {100*len(on)/n:.1f}%   "
      f"(A1 <15% -> {'PASS' if len(on)/n < .15 else 'FAIL'})")
print(f"    fail rate : {onf}/{len(on)} = {100*onf/len(on):.1f}%  (base {100*base:.1f}%)")
print(f"    lift      : {(onf/len(on))/base:.3f}x   "
      f"(A2 >=1.50x -> {'PASS' if (onf/len(on))/base >= 1.5 else 'FAIL'})")
print(f"    harm rate : {100*(1-onf/len(on)):.1f}%    veto net: {onf-(len(on)-onf):+d}")

print()
print("=" * 74)
print("SECTION 6 -- reference-label reliability floor")
print("=" * 74)
bad = [k for k, o in oracle.items() if o["gt"] and not o["did"] and o["reward"] >= 1.0]
fired = {(x["task_id"], x["trial"], x["domain"], x["agent"]) for x in joined if x["fires"]}
print(f"\n  reference requires a write AND agent performed none AND reward=1.0:")
print(f"    {len(bad)}/{n} = {100*len(bad)/n:.1f}% of records, "
      f"{len({(k[2], k[0]) for k in bad})} distinct tasks")
print(f"    by domain: {dict(Counter(k[2] for k in bad))}")
print(f"    RC1 fires on {sum(1 for k in bad if k in fired)} of them "
      f"({100*sum(1 for k in bad if k in fired)/266:.1f}% of RC1's 266 harms)")
print("\n  Reported as a noise floor.  NOT applied as a correction: removing cases to")
print("  improve a rejected rule's headline is precisely what this post-mortem must not do.")

print()
print("=" * 74)
print("A2-TASK GATE CEILING")
print("=" * 74)
t = defaultdict(lambda: [0, 0])
for x in joined:
    d = t[(x["domain"], x["task_id"])]
    d[0] += 1
    d[1] += x["reference_fail"]
anyfail = sum(1 for d in t.values() if d[1] > 0) / len(t)
print(f"\n  tasks with >=1 reference FAIL : {sum(1 for d in t.values() if d[1]>0)}/{len(t)} "
      f"= {100*anyfail:.1f}%")
print(f"  max achievable A2-task lift   : {1/anyfail:.4f}x")
print(f"  preregistered threshold       : 1.2500x")
print(f"  => gate was {'UNPASSABLE BY ANY RULE' if 1/anyfail < 1.25 else 'passable'}")
