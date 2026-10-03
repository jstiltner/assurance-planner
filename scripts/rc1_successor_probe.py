"""EXPLORATORY mechanism probe for the successor-hypothesis gate.

NOT a rule. NOT a detector. NOT validation. No thresholds are fit here.
This script answers three mechanism questions on already-burned tau-bench data:

  Phase 4  What production-visible EVENT would have told an obligation-tracking
           system that RC1's frozen action class had stopped being the right one?
  Phase 6/7 What distinguishes RC1's 118 right-for-the-right-reason firings from
           its 383 wrong-reason firings -- and is that distinction principled or
           incidental?
  Phase 9  How much of the corrective signal lives in STRUCTURED events (tool
           results) versus UNSTRUCTURED events (user utterances)?  This bounds the
           semantic burden of any successor.

Reads info.task.actions (ORACLE) only to partition cases for inspection.
"""
import json
import math
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "scripts")
from tau_bench_ingest import ALL_WRITE_TOOLS, load_corpus

DIR = "data/tau_bench_trajectories"
FILES = [
    ("gpt-4o-airline.json",        "airline", "gpt-4o"),
    ("gpt-4o-retail.json",         "retail",  "gpt-4o"),
    ("sonnet-35-new-airline.json", "airline", "sonnet-3.5-new"),
    ("sonnet-35-new-retail.json",  "retail",  "sonnet-3.5-new"),
]

# ---- load ---------------------------------------------------------------
ora = {}
for fname, dom, ag in FILES:
    with open(f"{DIR}/{fname}", encoding="utf-8") as fh:
        for r in json.load(fh):
            task = (r.get("info") or {}).get("task") or {}
            gt = {a["name"] for a in (task.get("actions") or [])
                  if a["name"] in ALL_WRITE_TOOLS}
            did = set()
            for msg in r.get("traj") or []:
                for tc in msg.get("tool_calls") or []:
                    n = (tc.get("function") or {}).get("name", "")
                    if n in ALL_WRITE_TOOLS:
                        did.add(n)
            ora[(r["task_id"], r["trial"], dom, ag)] = {
                "gt": gt, "did": did, "missing": gt - did}

pre = {(p["task_id"], p["trial"], p["domain"], p["agent"]): p
       for p in json.load(open("data/rc1_pre_outcome_firings.json", encoding="utf-8"))}
rec = {(r.task_id, r.trial, r.domain, r.agent): r
       for r in load_corpus(DIR)}
joined = json.load(open("data/rc1_outcome_joined.json", encoding="utf-8"))


def claimed_classes(p):
    c = set()
    for i in p["never_attempted_indices"]:
        c |= set(p["obligations"][i]["action_class"])
    return c


def right_reason(k):
    o, p = ora[k], pre[k]
    return bool(o["missing"]) and bool(claimed_classes(p) & o["missing"])


fires = [x for x in joined if x["fires"]]
keys = [(x["task_id"], x["trial"], x["domain"], x["agent"]) for x in fires]
RIGHT = [k for k in keys if right_reason(k)]
WRONG = [k for k in keys if not right_reason(k)]

print("=" * 76)
print("PHASE 6/7 -- what separates the 118 right-reason firings from the 383?")
print("=" * 76)
print(f"  right-reason: {len(RIGHT)}   wrong-reason: {len(WRONG)}")


def feat(k):
    """Production-visible features only. No reward, no info.task."""
    r, p = rec[k], pre[k]
    writes = [tc for tc in r.tool_calls if tc.name in ALL_WRITE_TOOLS]
    ok_writes = [tc for tc in writes if tc.succeeded]
    return {
        "any_write": bool(writes),
        "any_successful_write": bool(ok_writes),
        "n_write": len(writes),
        "n_tool": len(r.tool_calls),
        "n_user_turns": len(r.user_turns),
        "n_obligations": len(p["obligations"]),
        "n_unfired_obl": len(p["never_attempted_indices"]),
        # did the agent write something OTHER than what RC1 demanded?
        "wrote_other_class": bool({tc.name for tc in ok_writes} - claimed_classes(p)),
    }


print(f"\n  {'feature':<28} {'right(118)':>12} {'wrong(383)':>12}   separation")
print("  " + "-" * 70)
for f in ["any_write", "any_successful_write", "wrote_other_class"]:
    a = sum(feat(k)[f] for k in RIGHT) / len(RIGHT)
    b = sum(feat(k)[f] for k in WRONG) / len(WRONG)
    print(f"  {f:<28} {100*a:11.1f}% {100*b:11.1f}%   {a-b:+.3f}")
for f in ["n_write", "n_tool", "n_user_turns", "n_obligations", "n_unfired_obl"]:
    a = sum(feat(k)[f] for k in RIGHT) / len(RIGHT)
    b = sum(feat(k)[f] for k in WRONG) / len(WRONG)
    print(f"  {f:<28} {a:12.2f} {b:12.2f}   {a-b:+.2f}")

print("\n  -- incidental-feature check (must NOT separate, or construct is unprincipled) --")
for label, sel in (("domain", lambda k: k[2]), ("agent", lambda k: k[3])):
    ra = Counter(sel(k) for k in RIGHT)
    wa = Counter(sel(k) for k in WRONG)
    print(f"  {label}: right={dict(ra)}  wrong={dict(wa)}")
rt = len({(k[2], k[0]) for k in RIGHT})
wt = len({(k[2], k[0]) for k in WRONG})
print(f"  distinct tasks: right={rt}  wrong={wt}  "
      f"overlap={len({(k[2],k[0]) for k in RIGHT} & {(k[2],k[0]) for k in WRONG})}")

# The candidate general distinction
print("\n" + "=" * 76)
print("CANDIDATE DISTINCTION: 'no successful write of ANY class anywhere in trace'")
print("=" * 76)
nw_r = sum(1 for k in RIGHT if not feat(k)["any_successful_write"])
nw_w = sum(1 for k in WRONG if not feat(k)["any_successful_write"])
print(f"  right-reason with NO successful write: {nw_r}/{len(RIGHT)} ({100*nw_r/len(RIGHT):.1f}%)")
print(f"  wrong-reason with NO successful write: {nw_w}/{len(WRONG)} ({100*nw_w/len(WRONG):.1f}%)")
print(f"  If this rule replaced RC1's class-matching, it would fire on "
      f"{nw_r+nw_w} of RC1's 501 firings,")
print(f"  retaining {nw_r} of the 118 useful ones ({100*nw_r/len(RIGHT):.0f}% recall of the good part)")
print(f"  and {nw_w} of the 383 bad ones ({100*nw_w/len(WRONG):.0f}% of the harmful part).")

# ---- Phase 4: what event would have corrected the frozen class? ---------
print("\n" + "=" * 76)
print("PHASE 4/9 -- corrective-event channel for the F6 harm cases")
print("=" * 76)
mech = json.load(open("data/rc1_mechanism_audit.json", encoding="utf-8"))
f6 = [c for c in mech["cards"] if c["mech"] == "F6_alt_tool"]
f4 = [c for c in mech["cards"] if c["mech"] == "F4_true_revoc"]
print(f"  F6 cases: {len(f6)}   F4 cases: {len(f4)}")

READ_PREFIX = ("get_", "search_", "list_", "calculate", "think")
for c in f6 + f4:
    k = tuple(c["key"])
    r = rec[k]
    reads_before_write = []
    seen_write = False
    for tc in r.tool_calls:
        if tc.name in ALL_WRITE_TOOLS:
            seen_write = True
            break
        if tc.name.startswith(READ_PREFIX):
            reads_before_write.append(tc.name)
    # Does any read response expose the structured state field that determines
    # which write class is legal?  Retail: order status.  Airline: cabin /
    # flight_type on the reservation.  (Retail-only string matching would score
    # every airline case False for the wrong reason.)
    state_fields = (('"status"',) if k[2] == "retail"
                    else ('"cabin"', '"flight_type"'))
    status_evidence = any(
        s in tc.response
        for tc in r.tool_calls if tc.name not in ALL_WRITE_TOOLS
        for s in state_fields
    )
    print(f"\n  [{c['mech']}] {k[2]} task={k[0]} trial={k[1]} {k[3]}")
    print(f"    rc1_froze : {c['rc1_claimed_not_called']}")
    print(f"    oracle_gt : {c['oracle_gt']}")
    print(f"    reads before first write: {len(reads_before_write)}")
    print(f"    class-determining STATE field visible in a read response: {status_evidence}")
    print(f"    user turns: {len(r.user_turns)}")

# ---- the null rule, evaluated standalone on the whole corpus --------------
# The candidate distinction above is only meaningful if it needs RC1's
# obligation extractor at all.  Evaluate it with the extractor REMOVED.
print("\n" + "=" * 76)
print("NULL RULE -- 'no successful write anywhere', no obligation model at all")
print("=" * 76)


def oracle_miss(k):
    return bool(ora[k]["missing"])


def no_write(k):
    return not any(tc.name in ALL_WRITE_TOOLS and tc.succeeded
                   for tc in rec[k].tool_calls)


allk = list(rec)
nfire = [k for k in allk if no_write(k)]
nright = [k for k in nfire if oracle_miss(k)]
base = sum(oracle_miss(k) for k in allk)
print(f"  volume   : {len(nfire)}/{len(allk)} = {100*len(nfire)/len(allk):.1f}% of records")
print(f"  precision: {len(nright)}/{len(nfire)} = {100*len(nright)/len(nfire):.1f}%")
print(f"  base rate: {base}/{len(allk)} = {100*base/len(allk):.1f}%   "
      f"corpus lift = {(len(nright)/len(nfire))/(base/len(allk)):.3f}x")

def within_task(fire, outcome, label):
    """Within-task lift, one code path, so comparisons are like-for-like.

    Reproduces the published RC1 1.101x and oracle 2.339x when given those
    (rule, outcome) pairs -- which is the point: a lift is only comparable to
    another lift if BOTH the rule and the outcome match.
    """
    grp = defaultdict(lambda: [0, 0, 0, 0])
    for k in allk:
        b = grp[(k[2], k[0])]
        if fire(k):
            b[0] += outcome(k); b[1] += 1
        else:
            b[2] += outcome(k); b[3] += 1
    use = [b for b in grp.values() if b[1] and b[3]]
    fm, fn = sum(b[0] for b in use), sum(b[1] for b in use)
    um, un = sum(b[2] for b in use), sum(b[3] for b in use)
    lift = (fm / fn) / (um / un)
    print(f"  {label:<44} tasks={len(use):3d}  fired {fm:3d}/{fn:3d}="
          f"{100*fm/fn:5.1f}%  unfired {um:3d}/{un:3d}={100*um/un:5.1f}%  "
          f"lift={lift:.3f}x")
    return lift


jmap = {(x["task_id"], x["trial"], x["domain"], x["agent"]): x for x in joined}
ref_fail = {k: float(jmap[k]["reward"]) < 1.0 for k in allk}
rc1_fires = {k: bool(jmap[k]["fires"]) for k in allk}


# ---- uncertainty, added 2026-10-02 ---------------------------------------
# `within_task` returns a bare point estimate, and the three rules are evaluated on three
# DIFFERENT task sets (94 / 80 / 109) because `use` keeps only tasks where that rule both
# fires and does not. Comparing two such point estimates supported the published claim that
# RC1 "fell below a no-model baseline". Neither the sampling error nor the differing strata
# were quantified. Both are quantified here.

PAIRS = [("NULL", "RC1"), ("ORACLE", "NULL")]


def _strata(fire, outcome, keys):
    """Per-task 2x2 cells: (fired_outcome, fired_n, unfired_outcome, unfired_n)."""
    grp = defaultdict(lambda: [0, 0, 0, 0])
    for k in keys:
        b = grp[(k[2], k[0])]
        if fire(k):
            b[0] += outcome(k); b[1] += 1
        else:
            b[2] += outcome(k); b[3] += 1
    return [b for b in grp.values() if b[1] and b[3]]


def _lift(cells):
    fm, fn = sum(b[0] for b in cells), sum(b[1] for b in cells)
    um, un = sum(b[2] for b in cells), sum(b[3] for b in cells)
    if not fn or not un or not um:
        return None
    return (fm / fn) / (um / un)


def mantel_haenszel(cells):
    """MH-pooled risk ratio with the Greenland-Robins variance for its log.

    The pooled lift weights every task equally regardless of size; MH weights each stratum
    by its information and is the standard estimator for exactly this design. It also keeps
    each rule inside its own strata rather than pooling across a set that differs per rule.
    """
    num = den = var_num = 0.0
    for a, n1, b, n0 in cells:
        n = n1 + n0
        num += a * n0 / n
        den += b * n1 / n
        var_num += (n1 * n0 * (a + b) - a * b * n) / (n * n)
    if num <= 0 or den <= 0:
        return None, None, None
    rr = num / den
    se = math.sqrt(var_num / (num * den))
    return rr, rr * math.exp(-1.96 * se), rr * math.exp(1.96 * se)


def bootstrap_lifts(rules, outcome, n_boot=2000, seed=20261002):
    """Resample TASKS with replacement; recompute each rule's lift on each resample.

    Tasks are the resampling unit because they are the stratum and because trials within a
    task are not independent. All rules share each resample, so differences are paired.
    """
    rng = random.Random(seed)
    by_task = defaultdict(list)
    for k in allk:
        by_task[(k[2], k[0])].append(k)
    tasks = sorted(by_task)
    draws = {name: [] for name, _ in rules}
    # Every ordering this study has published between two of these rules is a paired
    # difference and must be reported as one. ORACLE-NULL is here for the same reason
    # NULL-RC1 is: §4 of the synthesis asserted it from two point estimates.
    for pair in PAIRS:
        draws[pair] = []
    for _ in range(n_boot):
        picked = [tasks[rng.randrange(len(tasks))] for _ in tasks]
        keys = [k for t in picked for k in by_task[t]]
        vals = {}
        for name, fire in rules:
            lift = _lift(_strata(fire, outcome, keys))
            vals[name] = lift
            if lift is not None:
                draws[name].append(lift)
        for pair in PAIRS:
            a, b = pair
            if vals.get(a) is not None and vals.get(b) is not None:
                draws[pair].append(vals[a] - vals[b])
    return draws


def bootstrap_mh(rules, outcome, n_boot=2000, seed=20261002):
    """Same task-level cluster resampling, applied to the MH estimator.

    This is the interval to quote for MH. The Greenland-Robins closed form assumes the
    observations inside a stratum are independent; here they are repeated trials of one task,
    so GR understates the width by enough to change whether the interval covers 1.
    """
    rng = random.Random(seed)
    by_task = defaultdict(list)
    for k in allk:
        by_task[(k[2], k[0])].append(k)
    tasks = sorted(by_task)
    draws = {name: [] for name, _ in rules}
    for _ in range(n_boot):
        picked = [tasks[rng.randrange(len(tasks))] for _ in tasks]
        keys = [k for t in picked for k in by_task[t]]
        for name, fire in rules:
            rr, _, _ = mantel_haenszel(_strata(fire, outcome, keys))
            if rr is not None:
                draws[name].append(rr)
    return draws


def pct(xs, p):
    xs = sorted(xs)
    return xs[max(0, min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1)))))]

print("\n  -- predicting the DEPLOYABLE outcome (reference FAIL) --")
l_oracle = within_task(oracle_miss, lambda k: ref_fail[k],
                       "ORACLE construct (a required write missing)")
l_null = within_task(no_write, lambda k: ref_fail[k],
                     "NULL rule (no successful write)")
l_rc1 = within_task(lambda k: rc1_fires[k], lambda k: ref_fail[k],
                    "RC1 (production detector)")
print("\n  -- predicting the ORACLE outcome (a required write missing) --")
within_task(no_write, oracle_miss, "NULL rule -> oracle miss")
print("     ^ NOT comparable to the 2.339x above: different outcome variable,")
print("       and 'no write' partly CONSTITUTES 'a required write is missing'.")

# ---- how much of that ordering is real? ----------------------------------
print("\n" + "=" * 76)
print("UNCERTAINTY ON THE THREE LIFTS  (added 2026-10-02)")
print("=" * 76)

RULES = [
    ("ORACLE", oracle_miss),
    ("NULL", no_write),
    ("RC1", lambda k: rc1_fires[k]),
]

print("\n  Task sets are NOT the same across rules -- `use` keeps only tasks where the")
print("  rule both fires and does not, so each lift is computed on its own stratum set:")
for name, fire in RULES:
    print(f"    {name:<8} tasks = {len(_strata(fire, lambda k: ref_fail[k], allk)):3d}")

print("\n  Task-level bootstrap, 2,000 resamples, 95% percentile interval:")
boot = bootstrap_lifts(RULES, lambda k: ref_fail[k])
for name, _ in RULES:
    d = boot[name]
    print(f"    {name:<8} {_lift(_strata(dict(RULES)[name], lambda k: ref_fail[k], allk)):.3f}"
          f"  [{pct(d, 2.5):.3f}, {pct(d, 97.5):.3f}]")
print("\n  Paired differences on the SAME task resamples (the only valid way to order two")
print("  of these rules, since their own strata sets differ: 94 / 80 / 109):")
# Two different quantities get printed on each line and they are labelled now. The first
# column is the MEAN of the 2,000 paired resample differences; the full-sample difference of
# the two point estimates above it is not the same number (NULL - RC1 is +0.070 there, +0.078
# here) and the published figure has always been the bootstrap mean. An external reproduction
# asked which one +0.078 was on 2026-10-02 and the output did not say.
print("    rule pair      boot mean (point diff)  95% percentile interval")
for pair in PAIRS:
    d = boot[pair]
    lo, hi = pct(d, 2.5), pct(d, 97.5)
    verdict = "straddles 0; not distinguishable" if lo <= 0 <= hi else "excludes 0"
    point = (_lift(_strata(dict(RULES)[pair[0]], lambda k: ref_fail[k], allk))
             - _lift(_strata(dict(RULES)[pair[1]], lambda k: ref_fail[k], allk)))
    print(f"    {pair[0] + ' - ' + pair[1]:<14} {sum(d)/len(d):+.3f} ({point:+.3f})"
          f"         [{lo:+.3f}, {hi:+.3f}]   <- {verdict}")

print("\n  Mantel-Haenszel risk ratio, stratified by task.")
print("  Primary interval is a task-level cluster bootstrap. Greenland-Robins is shown")
print("  beside it but is NOT the interval to quote: GR assumes independent observations")
print("  within a stratum, and the observations within a task are repeated trials of that")
print("  same task. GR is materially too narrow here, and narrow enough to flip the")
print("  conclusion -- it excludes 1 for both NULL and RC1 where the cluster interval")
print("  does not.")
mh_boot = bootstrap_mh(RULES, lambda k: ref_fail[k])
for name, fire in RULES:
    rr, glo, ghi = mantel_haenszel(_strata(fire, lambda k: ref_fail[k], allk))
    d = mh_boot[name]
    print(f"    {name:<8} {rr:.3f}  cluster [{pct(d, 2.5):.3f}, {pct(d, 97.5):.3f}]"
          f"   (GR [{glo:.3f}, {ghi:.3f}])")

print("\n  Mantel-Haenszel, stratified by task AND agent:")
mh_agent = {}
for name, fire in RULES:
    grp = defaultdict(lambda: [0, 0, 0, 0])
    for k in allk:
        b = grp[(k[2], k[0], k[3])]
        if fire(k):
            b[0] += ref_fail[k]; b[1] += 1
        else:
            b[2] += ref_fail[k]; b[3] += 1
    rr, lo, hi = mantel_haenszel([b for b in grp.values() if b[1] and b[3]])
    mh_agent[name] = rr
    print(f"    {name:<8} {rr:.3f}  (GR [{lo:.3f}, {hi:.3f}])")

# Serialised so figure 3 can draw the intervals from this code path instead of carrying
# its own copies of them. Figure 3 drew three bare bars until 2026-10-02, which made the
# one comparison the data does not support (null height vs RC1 height) the only one a
# reader could make.
UNCERTAINTY = {
    name: {
        "tasks": len(_strata(fire, lambda k: ref_fail[k], allk)),
        "lift": _lift(_strata(fire, lambda k: ref_fail[k], allk)),
        "lift_ci": [pct(boot[name], 2.5), pct(boot[name], 97.5)],
        "mh": mantel_haenszel(_strata(fire, lambda k: ref_fail[k], allk))[0],
        "mh_cluster_ci": [pct(mh_boot[name], 2.5), pct(mh_boot[name], 97.5)],
        "mh_gr_ci": list(mantel_haenszel(_strata(fire, lambda k: ref_fail[k], allk))[1:]),
        "mh_by_task_and_agent": mh_agent[name],
    }
    for name, fire in RULES
}
UNCERTAINTY["paired_differences"] = {
    f"{a}_minus_{b}": {
        # `mean` is the published figure and `point` is the difference of the two full-sample
        # lifts. They differ in the third decimal and are not interchangeable; the key names say
        # which is which so a citation cannot pick up one while meaning the other.
        "mean": sum(boot[(a, b)]) / len(boot[(a, b)]),
        "point": (_lift(_strata(dict(RULES)[a], lambda k: ref_fail[k], allk))
                  - _lift(_strata(dict(RULES)[b], lambda k: ref_fail[k], allk))),
        "ci": [pct(boot[(a, b)], 2.5), pct(boot[(a, b)], 97.5)],
    }
    for a, b in PAIRS
}
UNCERTAINTY["method"] = (
    "Task-level cluster bootstrap, 2000 resamples, seed 20261002. Quote mh_cluster_ci, "
    "never mh_gr_ci: Greenland-Robins assumes independence within strata that are repeated "
    "trials of one task and excludes 1 for NULL and RC1 where the cluster interval does not."
)

print("\n  Reading: the ORACLE construct separates under every estimator. NULL and RC1 do")
print("  not separate from each other, and neither is distinguishable from 1 under the")
print("  cluster interval. The published claim that RC1 'fell below a no-model baseline'")
print("  rested on the ordering of two point estimates whose difference straddles zero,")
print("  computed on two different task sets (80 vs 109).")

with open("data/rc1_successor_probe.json", "w", encoding="utf-8") as fh:
    json.dump({
        "right_reason_keys": [list(k) for k in RIGHT],
        "wrong_reason_keys": [list(k) for k in WRONG],
        "right_no_write": nw_r, "wrong_no_write": nw_w,
        "null_rule": {
            "volume": len(nfire), "n_records": len(allk),
            "precision_num": len(nright),
            "base_rate_num": base,
            "within_task_lift_ref_fail": l_null,
            "oracle_within_task_lift_ref_fail": l_oracle,
            "rc1_within_task_lift_ref_fail": l_rc1,
        },
        "uncertainty": UNCERTAINTY,
    }, fh, indent=2)
print("\nSaved: data/rc1_successor_probe.json")
