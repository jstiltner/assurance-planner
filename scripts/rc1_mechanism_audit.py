"""Oracle-grounded mechanism audit of RC1 harm-sample cases.

Classifies each of the 15 sampled harm (fired, reference PASS) trajectories
by comparing RC1's claimed unfired obligation against the oracle GT action list.

Three oracle-grounded mechanism categories:
  F6_alt_tool      -- oracle GT was fully performed; RC1 extracted wrong action class
  F4_true_revoc    -- oracle GT is empty; reference solution required no write
  construct_mismatch -- oracle GT requires write, none performed, reward=1.0

NOTE: This script reads info.task.actions, which is oracle / undeployable.
Used post-hoc to audit a frozen rejected rule only.
"""
import json
import sys
sys.path.insert(0, "scripts")
from tau_bench_ingest import ALL_WRITE_TOOLS

DIR = "data/tau_bench_trajectories"
FILES = [
    ("gpt-4o-airline.json",       "airline", "gpt-4o"),
    ("gpt-4o-retail.json",        "retail",  "gpt-4o"),
    ("sonnet-35-new-airline.json","airline", "sonnet-3.5-new"),
    ("sonnet-35-new-retail.json", "retail",  "sonnet-3.5-new"),
]

ora = {}
for fname, dom, ag in FILES:
    with open(f"{DIR}/{fname}", encoding="utf-8") as fh:
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
        ora[(r["task_id"], r["trial"], dom, ag)] = {
            "gt": gt, "did": did, "missing": gt - did,
            "reward": float(r["reward"]),
        }

pre = {(p["task_id"], p["trial"], p["domain"], p["agent"]): p
       for p in json.load(open("data/rc1_pre_outcome_firings.json", encoding="utf-8"))}
sample = json.load(open("data/rc1_harm_sample_corrected.json", encoding="utf-8"))

counts = {"F6_alt_tool": 0, "F4_true_revoc": 0, "construct_mismatch": 0}
cards = []
for s in sample:
    k = tuple(s["key"])
    o = ora[k]
    p = pre[k]
    claimed = set()
    for i in p["never_attempted_indices"]:
        claimed |= set(p["obligations"][i]["action_class"])

    if not o["gt"]:
        mech = "F4_true_revoc"
        rationale = (
            "oracle GT empty: reference solution required no write. "
            "RC1 extracted an obligation from an early user turn that was never "
            "actually owed -- the conversation concluded without any write being needed."
        )
    elif not o["missing"]:
        mech = "F6_alt_tool"
        rationale = (
            f"oracle GT fully performed ({sorted(o['did'])} vs GT {sorted(o['gt'])}). "
            f"RC1 claimed {sorted(claimed)} was never called. "
            "The agent resolved the task correctly under a different action class "
            "than RC1 extracted from the initial user statement."
        )
    else:
        mech = "construct_mismatch"
        rationale = (
            f"oracle GT={sorted(o['gt'])}, none performed, reward=1.0. "
            "Reference required an action that was not performed, yet the task passed. "
            "Possible explanations: reward not conditioned on this action, state "
            "already satisfied, or benchmark scoring inconsistency."
        )
    counts[mech] += 1
    cards.append({"key": list(k), "mech": mech, "rationale": rationale,
                  "oracle_gt": sorted(o["gt"]), "oracle_did": sorted(o["did"]),
                  "oracle_missing": sorted(o["missing"]),
                  "rc1_claimed_not_called": sorted(claimed)})

print("=" * 74)
print("ORACLE-GROUNDED MECHANISM AUDIT: 15 harm-sample cases (seed 20260929)")
print("=" * 74)
print()
for c in cards:
    k = c["key"]
    print(f"  {c['mech']:<22}  {k[2]:8s} task={k[0]:3d} trial={k[1]} {k[3]}")
    print(f"    oracle_gt    : {c['oracle_gt']}")
    print(f"    oracle_did   : {c['oracle_did']}")
    print(f"    oracle_miss  : {c['oracle_missing']}")
    print(f"    rc1_claimed  : {c['rc1_claimed_not_called']}")
    print()

print("=" * 74)
print("COUNTS")
print("=" * 74)
for k, v in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"  {v:2d}/15  {k}")

print()
print("=" * 74)
print("CORRECTION vs prior decomposition doc (commit c43cdea)")
print("=" * 74)
print()
print("  Prior doc claimed: F4=9/15 dominant, F6=5/15, label_error=1/15")
print(f"  Oracle audit shows: F6={counts['F6_alt_tool']}/15 dominant, "
      f"F4={counts['F4_true_revoc']}/15, construct_mismatch={counts['construct_mismatch']}/15")
print()
print("  WITHDRAWAL: 'F4 is the dominant mechanism' was itself an overcorrection.")
print()
print("  SOURCE OF ERROR: The decomposition doc read 'user revised their stated")
print("  request' as F4 (obligation revocation). But in most of those cases,")
print("  the agent correctly adapted to the revised request and the oracle GT")
print("  reflects that final resolution. RC1 is locked to the first-stated")
print("  action class; the oracle grades the resolved one.")
print()
print("  The failure is still F6 -- wrong action class -- not F4 -- dropped")
print("  obligation. The *reason* the action class is wrong differs from the")
print("  original report: not purely state-disambiguation (pending vs delivered),")
print("  but 'RC1 extracted from turn 1 and never updated as the conversation")
print("  revealed the actual resolution'.")
print()
print("  This does not change the H2a verdict: representation failure,")
print("  not abstraction failure. It changes what kind of representation is needed:")
print("  not 'read tool arguments for order state' but 'read the full conversation")
print("  to know what action class was actually resolved'.")

with open("data/rc1_mechanism_audit.json", "w", encoding="utf-8") as f:
    json.dump({"counts": counts, "cards": cards}, f, indent=2)
print("\nFull cards saved: data/rc1_mechanism_audit.json")
