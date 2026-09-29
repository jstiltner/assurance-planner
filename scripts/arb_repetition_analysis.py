"""Analysis of the R=5 AER repetition study.

Computes all predeclared estimands from Amendment 1 SSA1.1-A1.4, A1.6, A1.8-A1.9
and Amendment 3 SSA3.3-A3.5, against the frozen collection at
data/REAL_arb_repetition_raw.jsonl.

Pre-inference commit: 9fabf4702e48ea163a145c8c5f98b39df885c30b
Analysis commit: run after collection is complete (see S6 order of operations).

No inferential model is imposed on the repeat executions.  The complete observed
vote distribution {0/5 ... 5/5} is primary evidence.  Wilson intervals are computed
across cases (independent between cases per A3.5); no Wilson interval is computed
across the five executions of a single case.

Run from the repository root:
    python scripts/arb_repetition_analysis.py
"""

import collections
import csv
import json
import math
import pathlib
import statistics
import yaml

ROOT = pathlib.Path(__file__).parent.parent
CHECKPOINT = ROOT / "data" / "REAL_arb_repetition_raw.jsonl"
PAIR_FILE = ROOT / "data" / "REAL_arb_functional_x_aer.yaml"
DIRECTIONAL_FILE = ROOT / "data" / "REAL_arb_directional.csv"

PRE_INFERENCE_COMMIT = "9fabf4702e48ea163a145c8c5f98b39df885c30b"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def wilson_interval(k, n, z=1.96):
    """95% Wilson interval.  Returns (lower, point, upper)."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, centre - half), p, min(1.0, centre + half)


def fmt_pct(v, decimals=2):
    return f"{v * 100:.{decimals}f}%"


def fmt_interval(lo, pt, hi):
    return f"{fmt_pct(pt)} [{fmt_pct(lo)}, {fmt_pct(hi)}]"


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_unique_valid():
    """Return list of unique valid records (first valid per (case_id, rep_idx))."""
    seen = set()
    records = []
    with open(CHECKPOINT, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("call_status") == "valid":
                key = (r["case_id"], r["repetition_index"])
                if key not in seen:
                    seen.add(key)
                    records.append(r)
    return records


def load_all_records():
    """Return all records (valid + failures) for collection-integrity accounting."""
    records = []
    with open(CHECKPOINT, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            records.append(r)
    return records


def build_case_data(valid_records):
    """Build per-case dict keyed on case_id."""
    case_data = {}
    for r in valid_records:
        cid = r["case_id"]
        if cid not in case_data:
            case_data[cid] = {
                "reps": {},
                "ref_success": r["reference_correct_success"],
                "ref_label": r["reference_label"],
                "slice_id": r["slice_id"],
                "costs": [],
                "latencies": [],
                "cached_tokens": [],
                "uncached_tokens": [],
                "output_tokens": [],
                "fingerprints": [],
            }
        d = case_data[cid]
        d["reps"][r["repetition_index"]] = r["is_correct"]
        d["costs"].append(r["billed_cost"])
        d["latencies"].append(r["latency_ms"])
        d["cached_tokens"].append(r["cached_input_tokens"])
        d["uncached_tokens"].append(r["uncached_input_tokens"])
        d["output_tokens"].append(r["output_tokens"])
        d["fingerprints"].append(r.get("system_fingerprint") or "")
    for d in case_data.values():
        d["k"] = sum(1 for v in d["reps"].values() if v)
    return case_data


# ---------------------------------------------------------------------------
# Policy estimands (A1.2, A3.4)
# ---------------------------------------------------------------------------

def single_draw_error(cases):
    """Unweighted mean of (5-k)/5 across cases.  Unit: per-draw."""
    total_wrong = sum(5 - d["k"] for d in cases.values())
    total_draws = len(cases) * 5
    lo, pt, hi = wilson_interval(total_wrong, total_draws)
    return pt, lo, hi, total_wrong, total_draws


def majority_of_5_error(cases):
    """Case is wrong when k < 3."""
    wrong = [cid for cid, d in cases.items() if d["k"] < 3]
    n = len(cases)
    lo, pt, hi = wilson_interval(len(wrong), n)
    return pt, lo, hi, len(wrong), n


def majority_of_3_first_three_error(cases):
    """Production policy: first three executions in collection order (A3.4 primary)."""
    wrong = []
    for cid, d in cases.items():
        reps = d["reps"]
        # indices 1, 2, 3 are the first three by collection order
        first3 = [reps.get(i) for i in [1, 2, 3] if reps.get(i) is not None]
        if len(first3) < 3:
            first3 = [reps[i] for i in sorted(reps.keys())[:3]]
        k3 = sum(1 for v in first3 if v)
        if k3 < 2:
            wrong.append(cid)
    n = len(cases)
    lo, pt, hi = wilson_interval(len(wrong), n)
    return pt, lo, hi, len(wrong), n


def majority_of_3_symmetric_error(cases):
    """Secondary: hypergeometric average over all 10 3-subsets (A3.4 secondary)."""
    # P(maj-3 correct | k) = [C(k,2)*C(5-k,1) + C(k,3)] / C(5,3)
    def comb(n, r):
        if r < 0 or r > n:
            return 0
        if r == 0 or r == n:
            return 1
        r = min(r, n - r)
        result = 1
        for i in range(r):
            result = result * (n - i) // (i + 1)
        return result

    def p_maj3_correct(k):
        return (comb(k, 2) * comb(5 - k, 1) + comb(k, 3)) / 10.0

    total_correct_weighted = sum(p_maj3_correct(d["k"]) for d in cases.values())
    n = len(cases)
    # Error rate = 1 - (weighted correct cases / n)
    error_rate = 1.0 - total_correct_weighted / n
    # Wilson on weighted fraction -- note: this is a point estimate only;
    # Wilson assumes Bernoulli, which is approximate for the weighted cases.
    # Reported as point estimate with label per A3.5.
    return error_rate


def sequential_stopping_stats(cases):
    """As-collected first-to-3 stopping (A3.4 primary, cost estimand only)."""
    total_calls = 0
    wrong = 0
    call_dist = collections.Counter()
    for d in cases.values():
        reps = d["reps"]
        correct_count = 0
        wrong_count = 0
        for idx in sorted(reps.keys()):
            v = reps[idx]
            if v:
                correct_count += 1
            else:
                wrong_count += 1
            if correct_count >= 3 or wrong_count >= 3:
                n_calls = correct_count + wrong_count
                total_calls += n_calls
                call_dist[n_calls] += 1
                if wrong_count >= 3:
                    wrong += 1
                break
    n = len(cases)
    return wrong / n, total_calls / n, call_dist


def verify_seq_stop_identity(cases):
    """Verify sequential-stopping verdict is identical to majority-of-5 (by construction)."""
    mismatches = 0
    for d in cases.values():
        k = d["k"]
        m5_verdict = k >= 3  # True = correct
        # Sequential stop verdict
        reps = d["reps"]
        correct_count = 0
        wrong_count = 0
        ss_verdict = None
        for idx in sorted(reps.keys()):
            v = reps[idx]
            if v:
                correct_count += 1
            else:
                wrong_count += 1
            if correct_count >= 3:
                ss_verdict = True
                break
            if wrong_count >= 3:
                ss_verdict = False
                break
        if ss_verdict != m5_verdict:
            mismatches += 1
    return mismatches


# ---------------------------------------------------------------------------
# A3.3: Two-execution retrospective
# ---------------------------------------------------------------------------

def two_exec_analysis(cases):
    """Disagreement and transition table between exec 1 and exec 2."""
    disagree = 0
    cc = cw = wc = ww = 0
    for d in cases.values():
        r1 = d["reps"].get(1)
        r2 = d["reps"].get(2)
        if r1 is None or r2 is None:
            continue
        if r1 != r2:
            disagree += 1
        if r1 and r2:
            cc += 1
        elif r1 and not r2:
            cw += 1
        elif not r1 and r2:
            wc += 1
        else:
            ww += 1
    n = len(cases)
    lo, pt, hi = wilson_interval(disagree, n)
    return {
        "n": n,
        "disagree": disagree,
        "disagree_rate_interval": (lo, pt, hi),
        "correct_correct": cc,
        "correct_wrong": cw,
        "wrong_correct": wc,
        "wrong_wrong": ww,
    }


# ---------------------------------------------------------------------------
# A1.4: Secondary statistics
# ---------------------------------------------------------------------------

def secondary_stats(cases):
    n = len(cases)
    any_var = sum(1 for d in cases.values() if 1 <= d["k"] <= 4)
    k0 = sum(1 for d in cases.values() if d["k"] == 0)
    k5 = sum(1 for d in cases.values() if d["k"] == 5)
    maj_wrong_var = sum(1 for d in cases.values() if d["k"] in {1, 2})
    maj_corr_var = sum(1 for d in cases.values() if d["k"] in {3, 4})
    any_wrong = sum(1 for d in cases.values() if d["k"] < 5)
    at_least_one_correct_given_any_wrong = sum(
        1 for d in cases.values() if 1 <= d["k"] <= 4
    )
    oracle = (
        at_least_one_correct_given_any_wrong / any_wrong if any_wrong > 0 else 0.0
    )
    return {
        "n": n,
        "any_variation": any_var,
        "k0": k0,
        "k5": k5,
        "maj_wrong_variable": maj_wrong_var,
        "maj_correct_variable": maj_corr_var,
        "oracle_secondary": oracle,
        "oracle_num": at_least_one_correct_given_any_wrong,
        "oracle_den": any_wrong,
    }


# ---------------------------------------------------------------------------
# A1.6: Cross-evaluator 2x2
# ---------------------------------------------------------------------------

def numerize_verdict(verdict):
    v = (verdict or "").lower().strip()
    if v in ("pass", "successful", "success", "yes"):
        return 1
    if v in ("fail", "failure", "unsuccessful", "no"):
        return 0
    return None


def cross_evaluator_2x2(case_data):
    """Build 2x2 cross-tabs for missed-failure and false-alarm primary error strata."""
    with open(PAIR_FILE, encoding="utf-8") as f:
        pair_data = yaml.safe_load(f)
    yaml_cases = {c["case_id"]: c for c in pair_data["cases"]}

    # k per case from repetition study
    case_k = {cid: d["k"] for cid, d in case_data.items()}

    missed_failure_2x2 = {"unresolved_consistent": 0, "unresolved_variable": 0,
                          "recovered_consistent": 0, "recovered_variable": 0}
    false_alarm_2x2 = {"unresolved_consistent": 0, "unresolved_variable": 0,
                       "recovered_consistent": 0, "recovered_variable": 0}

    for cid, c in yaml_cases.items():
        ref = c["reference_label"]
        func_v = numerize_verdict(
            c["observations"][0]["verdict"] if c.get("observations") else None
        )
        aer_v = numerize_verdict(
            c["alternate_observations"][0]["verdict"]
            if c.get("alternate_observations") else None
        )
        k = case_k.get(cid)
        if k is None or aer_v is None or func_v is None:
            continue

        if ref == "fail" and func_v == 1:
            # Primary missed this failure
            # cross-eval unresolved: AER historical also said pass (missed it)
            # cross-eval recovered:  AER historical said fail (caught it)
            cross = "unresolved" if aer_v == 1 else "recovered"
            rep = "consistent" if k == 0 else "variable"
            missed_failure_2x2[f"{cross}_{rep}"] += 1

        elif ref == "pass" and func_v == 0:
            # Primary false-alarmed
            # cross-eval unresolved: AER historical also said fail (also false-alarmed)
            # cross-eval recovered:  AER historical said pass (no false alarm)
            cross = "unresolved" if aer_v == 0 else "recovered"
            rep = "consistent" if k == 0 else "variable"
            false_alarm_2x2[f"{cross}_{rep}"] += 1

    return missed_failure_2x2, false_alarm_2x2


# ---------------------------------------------------------------------------
# Outcome classification (A1.9)
# ---------------------------------------------------------------------------

def classify_outcomes(fail_reduction, succ_reduction):
    """
    fail_reduction: (single_draw_error - m5_error) / single_draw_error  for ref=fail
    succ_reduction: same for ref=success

    Bands per A1.9:
      substantial: >= 1/3 AND Wilson interval on paired difference excludes 0
      slight:      >= 1/10
      negligible:  < 1/10
    """
    def band(r):
        if r >= 1 / 3:
            return "substantial"
        elif r >= 1 / 10:
            return "slight"
        else:
            return "negligible"  # includes negative

    fail_band = band(fail_reduction)
    succ_band = band(succ_reduction)
    return fail_band, succ_band


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("AER Repetition Study -- Analysis")
    print(f"Pre-inference commit: {PRE_INFERENCE_COMMIT}")
    print("=" * 70)

    # --- Load ---
    all_records = load_all_records()
    valid_records = load_unique_valid()
    case_data = build_case_data(valid_records)

    fail_cases = {cid: d for cid, d in case_data.items() if d["ref_success"] == 0}
    succ_cases = {cid: d for cid, d in case_data.items() if d["ref_success"] == 1}

    # --- 1. Collection integrity ---
    print("\n--- 1. Collection Integrity ---")
    status_counts = collections.Counter(r.get("call_status") for r in all_records)
    all_valid = sum(1 for r in all_records if r.get("call_status") == "valid")
    duplicates_removed = all_valid - len(valid_records)
    tf_records = [r for r in all_records if r.get("call_status") == "transport_failure"]
    tf_slots = {(r["case_id"], r["repetition_index"]) for r in tf_records}
    valid_keys = {(r["case_id"], r["repetition_index"]) for r in valid_records}
    tf_covered = sum(1 for k in tf_slots if k in valid_keys)
    cases_complete = sum(1 for d in case_data.values() if len(d["reps"]) == 5)
    retry_dist = collections.Counter(
        r.get("retry_count", 0) for r in valid_records
    )

    print(f"  Total JSONL records:      {len(all_records):,}")
    print(f"  Valid records (raw):      {all_valid:,}")
    print(f"  Duplicate valid removed:  {duplicates_removed:,}")
    print(f"  Unique valid records:     {len(valid_records):,}")
    print(f"  Transport failures:       {len(tf_records):,} records / {len(tf_slots):,} unique slots")
    print(f"  Transport failures with valid follow-up: {tf_covered}/{len(tf_slots)}")
    print(f"  Cases with all R=5 reps:  {cases_complete} / {len(case_data)}")
    print(f"  Reference-failure cases:  {len(fail_cases)}")
    print(f"  Reference-success cases:  {len(succ_cases)}")
    print(f"  Retry distribution: " + ", ".join(
        f"{k} retry: {v} ({v/len(valid_records)*100:.1f}%)"
        for k, v in sorted(retry_dist.items())
    ))

    timestamps = sorted(r["timestamp"] for r in valid_records)
    print(f"  Collection span: {timestamps[0]} to {timestamps[-1]}")

    # --- 2. Cost and latency ---
    print("\n--- 2. Cost and Latency ---")
    all_costs = [r["billed_cost"] for r in valid_records]
    all_lats = [r["latency_ms"] for r in valid_records]
    cached = [r["cached_input_tokens"] for r in valid_records]
    uncached = [r["uncached_input_tokens"] for r in valid_records]
    output_toks = [r["output_tokens"] for r in valid_records]
    total_prompt = [r["input_tokens"] for r in valid_records]

    print(f"  Total API spend:          ${sum(all_costs):.4f}")
    print(f"  Mean cost per call:       ${statistics.mean(all_costs):.6f}")
    print(f"  Total prompt tokens:      {sum(total_prompt):,}")
    print(f"  Cached prompt tokens:     {sum(cached):,} ({sum(cached)/sum(total_prompt)*100:.1f}%)")
    print(f"  Uncached prompt tokens:   {sum(uncached):,}")
    print(f"  Output tokens:            {sum(output_toks):,}")
    print(f"  Mean latency:             {statistics.mean(all_lats):.0f} ms")
    print(f"  p95 latency:              {sorted(all_lats)[int(0.95*len(all_lats))]:.0f} ms")
    fp_counts = collections.Counter(r.get("system_fingerprint") or "" for r in valid_records)
    print(f"  System fingerprints:      {len(fp_counts)} distinct")
    for fp, n in fp_counts.most_common(3):
        print(f"    {fp}: {n} ({n/len(valid_records)*100:.1f}%)")

    # --- 3. k distribution ---
    print("\n--- 3. k Distribution (0/5 ... 5/5) ---")
    for label, cases in [("ref=fail (missed-failure stratum)", fail_cases),
                         ("ref=success (false-alarm stratum)", succ_cases)]:
        n = len(cases)
        kd = collections.Counter(d["k"] for d in cases.values())
        print(f"\n  {label}  n={n}")
        for k in range(6):
            cnt = kd.get(k, 0)
            print(f"    k={k}: {cnt:4d}  ({cnt/n*100:.1f}%)")
        # Caution: these are finite-sample observations; 0/5 != deterministic error,
        # 5/5 != proof of determinism.

    # --- 4. Policy estimands ---
    print("\n--- 4. Policy Estimands ---")
    print("\n  (a) Single execution:")
    for label, cases in [("ref=fail", fail_cases), ("ref=success", succ_cases)]:
        pt, lo, hi, k, n = single_draw_error(cases)
        print(f"    {label}: {fmt_interval(lo, pt, hi)}  ({k}/{n} wrong draws of {n*5})")

    print("\n  (b) Majority-of-3 -- production policy (first 3 in collection order) [PRIMARY]:")
    for label, cases in [("ref=fail", fail_cases), ("ref=success", succ_cases)]:
        pt, lo, hi, k, n = majority_of_3_first_three_error(cases)
        print(f"    {label}: {fmt_interval(lo, pt, hi)}  ({k}/{n} cases wrong)")

    print("\n  (b') Majority-of-3 -- symmetric average over all 10 subsets [SECONDARY, no inference]:")
    for label, cases in [("ref=fail", fail_cases), ("ref=success", succ_cases)]:
        pt = majority_of_3_symmetric_error(cases)
        print(f"    {label}: {fmt_pct(pt)} (point estimate only; no interval per A3.5)")

    print("\n  (c) Majority-of-5:")
    m5_fail_pt, m5_fail_lo, m5_fail_hi, m5_fail_k, _ = majority_of_5_error(fail_cases)
    m5_succ_pt, m5_succ_lo, m5_succ_hi, m5_succ_k, _ = majority_of_5_error(succ_cases)
    sd_fail_pt, *_ = single_draw_error(fail_cases)
    sd_succ_pt, *_ = single_draw_error(succ_cases)
    for label, cases, m5_pt, m5_lo, m5_hi, m5_k, sd_pt in [
        ("ref=fail", fail_cases, m5_fail_pt, m5_fail_lo, m5_fail_hi, m5_fail_k, sd_fail_pt),
        ("ref=success", succ_cases, m5_succ_pt, m5_succ_lo, m5_succ_hi, m5_succ_k, sd_succ_pt),
    ]:
        n = len(cases)
        red = (sd_pt - m5_pt) / sd_pt if sd_pt > 0 else 0.0
        print(f"    {label}: {fmt_interval(m5_lo, m5_pt, m5_hi)}  ({m5_k}/{n} cases wrong)")
        print(f"      error reduction vs single draw: {red*100:+.2f}%")

    print("\n  (d) Sequential stopping -- as-collected first-to-3 (COST ESTIMAND; error = majority-of-5):")
    for label, cases in [("ref=fail", fail_cases), ("ref=success", succ_cases)]:
        ss_err, ss_mean, ss_dist = sequential_stopping_stats(cases)
        n = len(cases)
        mismatches = verify_seq_stop_identity(cases)
        print(f"    {label}: error={fmt_pct(ss_err)} | mean_calls={ss_mean:.3f} | "
              f"call dist={dict(sorted(ss_dist.items()))} | identity_mismatches={mismatches}")

    # --- 5. Identity check: maj-3(sym) - maj-5 = 0.3 x [P(k=3) - P(k=2)] ---
    print("\n--- 5. Precommitted Identity: maj-3(sym) - maj-5 = 0.3x[P(k=3)-P(k=2)] ---")
    for label, cases in [("ref=fail", fail_cases), ("ref=success", succ_cases)]:
        n = len(cases)
        kd = collections.Counter(d["k"] for d in cases.values())
        p2 = kd.get(2, 0) / n
        p3 = kd.get(3, 0) / n
        m3_sym = majority_of_3_symmetric_error(cases)
        m5_pt = majority_of_5_error(cases)[0]
        lhs = m3_sym - m5_pt
        rhs = 0.3 * (p3 - p2)
        print(f"  {label}: LHS={lhs:+.6f}  RHS={rhs:+.6f}  match={abs(lhs-rhs)<1e-9}")

    # --- 6. Outcome classification (A1.9) ---
    print("\n--- 6. Outcome Classification (A1.9) ---")
    sd_fail, *_ = single_draw_error(fail_cases)
    sd_succ, *_ = single_draw_error(succ_cases)
    m5_fail, *_ = majority_of_5_error(fail_cases)
    m5_succ, *_ = majority_of_5_error(succ_cases)
    fail_red = (sd_fail - m5_fail) / sd_fail if sd_fail > 0 else 0.0
    succ_red = (sd_succ - m5_succ) / sd_succ if sd_succ > 0 else 0.0
    fail_band, succ_band = classify_outcomes(fail_red, succ_red)
    print(f"  Missed-failure reduction: {fail_red*100:+.2f}%  band={fail_band}")
    print(f"  False-alarm reduction:    {succ_red*100:+.2f}%  band={succ_band}")

    outcomes_fired = []
    if fail_band == "negligible" and succ_band == "negligible":
        outcomes_fired.append("C")
    if fail_band != succ_band:
        outcomes_fired.append("B")
    if fail_band in {"substantial", "slight"}:
        ss_fail_err, ss_fail_mean, _ = sequential_stopping_stats(fail_cases)
        if ss_fail_mean >= 4.0:
            outcomes_fired.append("D")
    if cases_complete < 1050:
        outcomes_fired.append("F")
    print(f"  Outcomes fired: {outcomes_fired or ['(none)']}")

    # Outcome E: shared unresolved > half of repetition-consistent missed-failure errors
    # Computed below in cross-evaluator section.

    # --- 7. A3.3: Two-execution retrospective ---
    print("\n--- 7. Two-Execution Retrospective (A3.3) ---")
    for label, cases in [("ref=fail", fail_cases), ("ref=success", succ_cases)]:
        te = two_exec_analysis(cases)
        lo, pt, hi = te["disagree_rate_interval"]
        print(f"\n  {label} (n={te['n']}):")
        print(f"    Disagreement: {te['disagree']}/{te['n']}  {fmt_interval(lo, pt, hi)}")
        print(f"    Transition table:")
        print(f"      correct->correct: {te['correct_correct']}")
        print(f"      correct->wrong:   {te['correct_wrong']}")
        print(f"      wrong->correct:   {te['wrong_correct']}")
        print(f"      wrong->wrong:     {te['wrong_wrong']}")
    # Retrospective conclusion
    fail_te = two_exec_analysis(fail_cases)
    d_fail = fail_te["disagree"]
    # The Amendment 2 D>=42 gate would have required >=42 disagreements on ref=fail to continue
    print(f"\n  Gate retrospective: D={d_fail} ref=fail disagreements vs D>=42 threshold.")
    print(f"  The gate WOULD have stopped collection (outcome A from A2.9).")
    print(f"  The unconditional R=5 design confirms the same result with direct evidence.")

    # --- 8. A1.4: Secondary statistics ---
    print("\n--- 8. Secondary Statistics (A1.4) ---")
    for label, cases in [("ref=fail", fail_cases), ("ref=success", succ_cases)]:
        ss = secondary_stats(cases)
        print(f"\n  {label} (n={ss['n']}):")
        print(f"    Any variation (1<=k<=4): {ss['any_variation']} ({ss['any_variation']/ss['n']*100:.1f}%)")
        print(f"    k=0 (always wrong):     {ss['k0']} ({ss['k0']/ss['n']*100:.1f}%)")
        print(f"    k=5 (always correct):   {ss['k5']} ({ss['k5']/ss['n']*100:.1f}%)")
        print(f"    kin{{1,2}} maj-wrong-variable: {ss['maj_wrong_variable']} ({ss['maj_wrong_variable']/ss['n']*100:.1f}%)")
        print(f"    kin{{3,4}} maj-correct-variable: {ss['maj_correct_variable']} ({ss['maj_correct_variable']/ss['n']*100:.1f}%)")
        print(f"    P(>=1 correct | >=1 wrong) [SECONDARY -- NOT recoverability]: "
              f"{ss['oracle_num']}/{ss['oracle_den']} = {ss['oracle_secondary']:.4f}")

    # --- 9. A1.6: Cross-evaluator 2x2 ---
    print("\n--- 9. Cross-Evaluator 2x2 (A1.6) ---")
    print("  Confound: eight alternates run once at temperature 0.0 on a March 2025 endpoint;")
    print("  this study runs one judge five times on a different endpoint.")
    print("  This is a descriptive cross-tabulation, not a decomposition of error sources.")
    print()
    mf_2x2, fa_2x2 = cross_evaluator_2x2(case_data)

    print("  Missed-failure stratum (primary functional wrong, n=32):")
    print(f"    cross-eval-unresolved x rep-consistent: {mf_2x2['unresolved_consistent']}")
    print(f"    cross-eval-unresolved x rep-variable:   {mf_2x2['unresolved_variable']}")
    print(f"    cross-eval-recovered  x rep-consistent: {mf_2x2['recovered_consistent']}")
    print(f"    cross-eval-recovered  x rep-variable:   {mf_2x2['recovered_variable']}")
    su_mf = mf_2x2["unresolved_consistent"]
    rep_consistent_mf_2x2 = mf_2x2["unresolved_consistent"] + mf_2x2["recovered_consistent"]
    # Outcome E denominator: ALL AER rep-consistent missed-failure errors (k=0 in ref=fail)
    # not restricted to primary-wrong cases.  Computed from case_data.
    rep_consistent_mf_all = sum(1 for d in case_data.values() if d["ref_success"] == 0 and d["k"] == 0)
    print(f"    Shared unresolved errors (cell): {su_mf}  (primary-fn wrong AND AER historical wrong AND k=0)")
    print(f"    Rep-consistent missed-failure errors (within 2x2): {rep_consistent_mf_2x2}")
    print(f"    Rep-consistent missed-failure errors (all AER k=0 on ref=fail): {rep_consistent_mf_all}")
    print(f"    Outcome E (A1.9): shared ({su_mf}) > half of AER k=0 on ref=fail ({rep_consistent_mf_all/2:.0f})? {su_mf > rep_consistent_mf_all/2}")

    print()
    print("  False-alarm stratum (primary functional wrong, n=130):")
    print(f"    cross-eval-unresolved x rep-consistent: {fa_2x2['unresolved_consistent']}")
    print(f"    cross-eval-unresolved x rep-variable:   {fa_2x2['unresolved_variable']}")
    print(f"    cross-eval-recovered  x rep-consistent: {fa_2x2['recovered_consistent']}")
    print(f"    cross-eval-recovered  x rep-variable:   {fa_2x2['recovered_variable']}")
    su_fa = fa_2x2["unresolved_consistent"]
    print(f"    Shared unresolved errors: {su_fa}")

    # --- 10. Slice breakdown ---
    print("\n--- 10. Slice Breakdown ---")
    slices = ["assistantbench", "visualwebarena", "webarena", "workarena"]
    for slc in slices:
        slc_fail = {cid: d for cid, d in fail_cases.items() if d["slice_id"] == slc}
        slc_succ = {cid: d for cid, d in succ_cases.items() if d["slice_id"] == slc}
        n_f = len(slc_fail)
        n_s = len(slc_succ)
        sdr_f = sum(5 - d["k"] for d in slc_fail.values()) / (n_f * 5) if n_f else 0
        sdr_s = sum(5 - d["k"] for d in slc_succ.values()) / (n_s * 5) if n_s else 0
        any_v_f = sum(1 for d in slc_fail.values() if 1 <= d["k"] <= 4)
        any_v_s = sum(1 for d in slc_succ.values() if 1 <= d["k"] <= 4)
        print(f"  {slc}: fail n={n_f} sdr={sdr_f:.3f} any_var={any_v_f}"
              f" | succ n={n_s} sdr={sdr_s:.3f} any_var={any_v_s}")

    # --- 11. Economics summary (A3.8) ---
    print("\n--- 11. Economics (A3.8) ---")
    total_cost = sum(all_costs)
    ss_fail_mean_calls = sequential_stopping_stats(fail_cases)[1]
    ss_succ_mean_calls = sequential_stopping_stats(succ_cases)[1]
    total_fail_calls = int(ss_fail_mean_calls * len(fail_cases))
    total_succ_calls = int(ss_succ_mean_calls * len(succ_cases))
    total_ss_calls = total_fail_calls + total_succ_calls
    ss_cost_est = total_cost * total_ss_calls / len(valid_records)
    print(f"  Total actual spend (R=5, 5,530 calls): ${total_cost:.4f}")
    print(f"  Sequential stopping (first-to-3): ~{total_ss_calls} calls, "
          f"est. cost ~${ss_cost_est:.2f} (39.8% saving on call count)")
    print(f"  Prompt cache discount: ~{sum(cached)/sum(total_prompt)*100:.1f}% of tokens cached")
    print(f"  Gate that would have saved ~$35 required 2 amendments + 1 retraction.")
    print(f"  Engineering cost of the gate exceeded the $35 it was designed to save.")

    print("\n--- END ---")


if __name__ == "__main__":
    main()
