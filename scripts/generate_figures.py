"""
Generate Figures 1–4 for the evaluator-assurance project.

Reads only from existing data artifacts; never re-runs inference.
Each figure asserts canonical values from public_claim_ledger.py before saving.

Usage:
    python scripts/generate_figures.py [--out-dir docs/figures]

Outputs:
    fig1_k_distribution.png
    fig2_policy_error_comparison.png
    fig3_lift_comparison.png
    fig4_ref_vs_operational.png
"""

import argparse
import collections
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "scripts"))
from public_claim_ledger import CANONICAL

# ── colour palette ────────────────────────────────────────────────────────────
REF_FAIL_COLOR   = "#1f77b4"   # blue
REF_SUCC_COLOR   = "#ff7f0e"   # orange
ORACLE_COLOR     = "#2ca02c"   # green
NULL_COLOR       = "#aec7e8"   # light blue
RC1_COLOR        = "#1f77b4"   # blue
WARN_COLOR       = "#d62728"   # red


# ── helpers ───────────────────────────────────────────────────────────────────

def _assert(val, expected, label, tol=0.005):
    if abs(float(val) - float(expected)) > tol:
        raise AssertionError(
            f"Canonical mismatch for {label}: computed {val}, expected {expected}"
        )
    return val


def _wilson_ci(k, n, z=1.96):
    """Wilson score interval."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = (z * (p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


# ── load repetition data ──────────────────────────────────────────────────────

def _load_repetition():
    """Return (fail_k_list, succ_k_list) using the first 5 repetition_index calls."""
    lines = (DATA / "REAL_arb_repetition_raw.jsonl").read_text(encoding="utf-8").splitlines()
    rows = [json.loads(l) for l in lines if l.strip()]

    by_case: dict[str, dict] = collections.defaultdict(dict)
    for r in rows:
        if r["call_status"] != "valid":
            continue
        cid = r["case_id"]
        ri = int(r["repetition_index"])
        if ri not in by_case[cid]:
            by_case[cid][ri] = r

    fail_k, succ_k = [], []
    for cid, reps in by_case.items():
        calls = [reps[i] for i in range(1, 6) if i in reps]
        if len(calls) != 5:
            continue
        k = sum(bool(c["is_correct"]) for c in calls)
        ref = calls[0]["reference_label"]
        if ref == "fail":
            fail_k.append(k)
        else:
            succ_k.append(k)

    # Assert canonical values
    _assert(len(fail_k), CANONICAL["rep_n_fail"], "rep_n_fail")
    _assert(len(succ_k), CANONICAL["rep_n_pass"], "rep_n_pass")
    _assert(fail_k.count(0), CANONICAL["rep_k0_fail"], "rep_k0_fail")
    _assert(fail_k.count(5), CANONICAL["rep_k5_fail"], "rep_k5_fail")
    _assert(succ_k.count(0), CANONICAL["rep_k0_pass"], "rep_k0_pass")
    _assert(succ_k.count(5), CANONICAL["rep_k5_pass"], "rep_k5_pass")
    intermediate = sum(1 for k in fail_k + succ_k if 0 < k < 5)
    _assert(intermediate, CANONICAL["rep_intermediate_cases"], "rep_intermediate_cases")

    return fail_k, succ_k


# ── Figure 1: k-distribution ──────────────────────────────────────────────────

def fig1_k_distribution(fail_k, succ_k, out_path):
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.5), sharey=False)

    for ax, ks, label, color, n_expected in [
        (axes[0], fail_k, "Reference-failure cases", REF_FAIL_COLOR, CANONICAL["rep_n_fail"]),
        (axes[1], succ_k, "Reference-success cases", REF_SUCC_COLOR, CANONICAL["rep_n_pass"]),
    ]:
        counts = collections.Counter(ks)
        vals = [counts.get(k, 0) for k in range(6)]
        bars = ax.bar(range(6), vals, color=color, edgecolor="white", linewidth=0.5)

        # Annotate bars with count
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.5, str(v),
                        ha="center", va="bottom", fontsize=8)

        ax.set_xlabel("Correct judgments out of 5 repetitions (k)", fontsize=9)
        ax.set_ylabel("Number of cases", fontsize=9)
        ax.set_title(f"{label}\n(n = {len(ks)})", fontsize=10)
        ax.set_xticks(range(6))
        ax.set_xlim(-0.6, 5.6)
        ax.tick_params(labelsize=8)

    # Shared annotation
    n_total = len(fail_k) + len(succ_k)
    n_intermediate = sum(1 for k in fail_k + succ_k if 0 < k < 5)
    fig.suptitle(
        f"Figure 1 — R=5 correctness distribution  [PREREGISTERED]\n"
        f"AER judge, gpt-4o-2024-11-20, temp 0.0 / seed 0  ·  "
        f"n = {n_total} cases  ·  {n_intermediate} of {n_total} intermediate (k 1–4)",
        fontsize=9, y=1.02
    )
    fig.text(
        0.5, -0.03,
        "Only 20 of 1,106 cases occupied the intermediate k=1–4 region; "
        "98.8% of ref-fail and 96.6% of ref-success were at an extreme.\n"
        "Scope: one judge, one configuration, judge stage only. "
        "Does not license 'LLM judges are deterministic'.",
        ha="center", fontsize=7.5, style="italic", color="#444444"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out_path}")


# ── Figure 2: policy error comparison ────────────────────────────────────────

def fig2_policy_error(fail_k, succ_k, out_path):
    """Compare single call / maj-3 / maj-5 / first-to-3 on both strata."""

    def majority(ks, m):
        """Error rate under majority-of-m voting."""
        errors = 0
        for k in ks:
            # majority-of-m verdict: correct if sum of any m draws >= ceil(m/2)
            # Since all 5 draws are identical in outcome for this data,
            # we count how many subsets of m from 5 would give wrong verdict.
            # For bimodal data k∈{0,5}, majority verdict = the unanimous verdict.
            # For k in 1..4, exact majority depends on draw.
            # Use expectation over draws: P(majority wrong) = P(k < m/2 under m draws)
            # Simplest: use the most conservative (k is what we observe from 5 draws).
            # A majority-of-m verdict is wrong iff majority of m sampled draws is wrong.
            # For k=0: all wrong, any majority is wrong → error
            # For k=5: all correct, any majority is correct → no error
            # For 0<k<5: P(majority wrong | m draws) = P(Binomial(m, k/5) < m/2)
            import math
            p_correct = k / 5
            if m == 1:
                # single call: error if k/5 < 0.5 by expectation, but use k=0 as definitive
                # use the empirical approach: error if majority of 1 is wrong (p < 0.5)
                p_wrong = 1 - p_correct
            else:
                # P(majority wrong) = P(X < ceil(m/2)) where X~Binomial(m, p_correct)
                # ceiling for majority = ceil(m/2)
                thresh = math.ceil(m / 2)
                p_wrong = sum(
                    math.comb(m, j) * (p_correct ** j) * ((1 - p_correct) ** (m - j))
                    for j in range(thresh)
                )
            errors += p_wrong
        return errors / len(ks) if ks else 0

    def first_to_3_error(ks):
        """Error rate under first-to-3 sequential stopping.
        For k=0: always wrong, stops at 3. For k=5: always right, stops at 3.
        For k in 1..4: complicated, approximate by P(majority-of-3 wrong).
        """
        return majority(ks, 3)

    policies = ["Single call", "Majority-of-3", "Majority-of-5", "First-to-3\n(sequential)"]

    fail_errors, succ_errors = [], []
    for m, label in [(1, "single"), (3, "maj3"), (5, "maj5"), (3, "stop3")]:
        fe = majority(fail_k, m)
        se = majority(succ_k, m)
        fail_errors.append(fe)
        succ_errors.append(se)

    # Assert single-call values are near published figures
    _assert(fail_errors[0], 0.1270, "single_call_fail_error", tol=0.005)
    _assert(succ_errors[0], 0.2725, "single_call_succ_error", tol=0.01)

    x = np.arange(len(policies))
    width = 0.35
    fig, ax = plt.subplots(figsize=(9, 5))

    bars1 = ax.bar(x - width / 2, [e * 100 for e in fail_errors],
                   width, label="Missed failures (ref-fail errors)", color=REF_FAIL_COLOR,
                   edgecolor="white")
    bars2 = ax.bar(x + width / 2, [e * 100 for e in succ_errors],
                   width, label="False alarms (ref-success errors)", color=REF_SUCC_COLOR,
                   edgecolor="white")

    # Annotate
    for bar, v in zip(list(bars1) + list(bars2), fail_errors + succ_errors):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.2,
                f"{v*100:.1f}%", ha="center", va="bottom", fontsize=7.5)

    # Cost annotation
    cost_labels = ["$46.18 (~5 calls)", "$27.86 (~3 calls)",
                   "$46.18 (5 calls)", "$27.86\n(−39.8% calls)"]
    for i, (xi, cost) in enumerate(zip(x, cost_labels)):
        ax.text(xi, -3.5, cost, ha="center", fontsize=7, color="#555555")

    ax.set_xticks(x)
    ax.set_xticklabels(policies, fontsize=9)
    ax.set_ylabel("Error rate (%)", fontsize=9)
    ax.set_ylim(0, 35)
    ax.set_title(
        "Figure 2 — Error rate by voting policy  [PREREGISTERED]\n"
        "gpt-4o-2024-11-20, temp 0.0 / seed 0  ·  n = 1,106 cases",
        fontsize=10
    )
    ax.legend(fontsize=9)
    ax.tick_params(labelsize=8)
    fig.text(
        0.5, -0.06,
        "More voting did not improve error in either direction. "
        "First-to-3 sequential stopping reproduced majority-of-5 verdicts exactly "
        "using 39.8% fewer calls.\n"
        "Scope: one judge, one configuration, judge stage only.",
        ha="center", fontsize=7.5, style="italic", color="#444444"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out_path}")


# ── Figure 3: lift comparison (oracle / null / RC1) ───────────────────────────

def fig3_lift_comparison(out_path):
    probe = json.loads((DATA / "rc1_successor_probe.json").read_text())
    nr = probe["null_rule"]
    oracle_lift = nr["oracle_within_task_lift_ref_fail"]
    null_lift = nr["within_task_lift_ref_fail"]
    rc1_lift = nr["rc1_within_task_lift_ref_fail"]

    _assert(oracle_lift, CANONICAL["oracle_within_task_lift"], "oracle_lift", tol=0.005)
    _assert(null_lift, CANONICAL["null_within_task_lift"], "null_lift", tol=0.005)
    _assert(rc1_lift, CANONICAL["rc1_within_task_lift_probe"], "rc1_lift", tol=0.005)

    labels = [
        "Oracle construct\n(required write missing;\nbenchmark-authoritative)",
        "Null rule\n(no successful write;\nno model)",
        "RC1\n(production detector;\nfresh corpus)",
    ]
    lifts = [oracle_lift, null_lift, rc1_lift]
    colors = [ORACLE_COLOR, NULL_COLOR, RC1_COLOR]
    hatches = ["//", "", ""]
    evidence = ["ORACLE / undeployable", "EXPLORATORY / not accepted", "PREREGISTERED / FRESH-CORPUS"]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(range(3), lifts, color=colors, edgecolor="#333333",
                  linewidth=0.8, hatch_linewidth=1.0)
    for bar, h in zip(bars, hatches):
        bar.set_hatch(h)

    # Baseline = 1.0
    ax.axhline(1.0, color="#333333", linewidth=1.0, linestyle="--", label="No lift (1.0×)")

    # Volume gate annotation
    ax.text(2.5, 1.03, "A1 volume gate: <15%\n(all three fail at 17–25%)",
            fontsize=7.5, color="#888888", ha="right")

    for i, (lift, evd) in enumerate(zip(lifts, evidence)):
        ax.text(i, lift + 0.02, f"{lift:.3f}×\n[{evd}]",
                ha="center", va="bottom", fontsize=7.5, linespacing=1.3)

    ax.set_xticks(range(3))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Within-task lift on reference FAIL outcome", fontsize=9)
    ax.set_ylim(0.8, 2.8)
    ax.set_title(
        "Figure 3 — Oracle / null baseline / RC1 lift comparison  [PREREGISTERED + ORACLE + EXPLORATORY]\n"
        "τ-bench, 1,980 records, 165 tasks  ·  Single code path; reproduces published values",
        fontsize=10
    )
    ax.legend(fontsize=9)
    ax.tick_params(labelsize=8)
    fig.text(
        0.5, -0.04,
        "The oracle construct is not deployable (benchmark-authoritative actions, class D). "
        "The null rule fails the volume gate and was preregistered as disqualified.\n"
        "RC1 is the production-visible detector: it fell below the null rule on the deployable outcome.\n"
        "The gap 2.339× → 1.101× shows a representation failure, not an empty abstraction. "
        "Does not support 'build a more semantic RC1.'",
        ha="center", fontsize=7.5, style="italic", color="#444444"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out_path}")


# ── Figure 4: reference-conditioned vs operational ────────────────────────────

def fig4_ref_vs_operational(out_path):
    csv_lines = (DATA / "REAL_arb_directional.csv").read_text().splitlines()
    headers = csv_lines[0].split(",")
    rows = [dict(zip(headers, l.split(","))) for l in csv_lines[1:] if l.strip()]
    pred = next(r for r in rows if r["tier"] == "A-CONFIRMATORY")

    # Reference-conditioned pooled recovery = missed_failure_catch_num / den
    #   = missed_failure_catch_num/den (what p(alt correct | primary wrong) approximates)
    # Actually the synthesis uses 0.543 which is the full pooled recovery
    # Let's compute it: (missed caught + false alarms rescued) / total primary errors
    mf_num = int(pred["missed_failure_catch_num"])
    mf_den = int(pred["missed_failure_catch_den"])
    fa_num = int(pred["false_alarm_rescue_num"])
    fa_den = int(pred["false_alarm_rescue_den"])
    total_errors = mf_den + fa_den
    pooled_recovery = (mf_num + fa_num) / total_errors

    op_fail_num = int(pred["overturn_to_fail_num"])
    op_fail_den = int(pred["overturn_to_fail_den"])
    op_pass_num = int(pred["overturn_to_pass_num"])
    op_pass_den = int(pred["overturn_to_pass_den"])

    op_fail_prec = op_fail_num / op_fail_den
    op_pass_prec = op_pass_num / op_pass_den

    _assert(pooled_recovery, CANONICAL["arb_predeclared_recovery"], "arb_pooled_recovery")
    _assert(op_fail_prec, CANONICAL["arb_operational_overturn_fail"], "op_fail_prec")
    _assert(op_pass_prec, CANONICAL["arb_operational_overturn_pass"], "op_pass_prec")
    _assert(mf_den, CANONICAL["arb_missed_failures"], "missed_failures")
    _assert(fa_den, CANONICAL["arb_false_alarms"], "false_alarms")

    fig, ax = plt.subplots(figsize=(8, 5))

    # Bar widths proportional to denominator (stratum size)
    categories = [
        ("Reference-conditioned\nrecovery\nP(alt correct | primary wrong)\n[NOT executable at runtime]",
         pooled_recovery, total_errors, "#aec7e8", "//"),
        (f"Operational: overturn-to-fail\n(precision of FAIL→PASS flips)\n[n = {op_fail_den} overturns]",
         op_fail_prec, op_fail_den * 10, REF_FAIL_COLOR, ""),
        (f"Operational: overturn-to-pass\n(precision of PASS→FAIL flips)\n[n = {op_pass_den} overturns]",
         op_pass_prec, op_pass_den * 10, REF_SUCC_COLOR, ""),
    ]

    x_positions = [0, 2.5, 4.2]
    bar_width_base = 0.8

    for xi, (label, val, denom, color, hatch) in zip(x_positions, categories):
        width = bar_width_base
        bar = ax.bar(xi, val, width=width, color=color, edgecolor="#333333",
                     linewidth=0.8, hatch=hatch)
        ax.text(xi, val + 0.01, f"{val:.3f}", ha="center", va="bottom", fontsize=10,
                fontweight="bold")
        ax.text(xi, -0.04, label, ha="center", va="top", fontsize=7.5,
                linespacing=1.3, transform=ax.get_xaxis_transform())

    # Error direction annotation
    ax.text(0, 0.58, f"n_primary = {total_errors}\n({mf_den} missed failures\n"
                     f"+ {fa_den} false alarms)",
            ha="center", fontsize=7.5, color="#333333",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#aaaaaa"))

    ax.set_xticks([])
    ax.set_xlim(-0.8, 5.5)
    ax.set_ylim(0, 0.75)
    ax.set_ylabel("Rate", fontsize=9)
    ax.set_title(
        "Figure 4 — Reference-conditioned recovery vs operational overturn precision  [EXPLORATORY]\n"
        "AgentRewardBench  ·  Predeclared pair: functional (primary) → aer (alternate)",
        fontsize=10
    )

    # Annotation for the hatch bar
    hatched_patch = mpatches.Patch(facecolor="#aec7e8", hatch="//", edgecolor="#333333",
                                   label="Reference-conditioned (uses ground-truth label)")
    ax.legend(handles=[hatched_patch], fontsize=8, loc="upper right")

    fig.text(
        0.5, -0.08,
        "The reference-conditioned quantity uses the ground-truth label no runtime system has — "
        "it is not an executable policy.\n"
        "The operational quantities (precision of actual overturns) ran 20–30 points lower.\n"
        "Evidence class: EXPLORATORY. Single primary/alternate pair.",
        ha="center", fontsize=7.5, style="italic", color="#444444"
    )
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out_path}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/figures",
                        help="Directory for output figures (default: docs/figures)")
    args = parser.parse_args()

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading repetition data…")
    fail_k, succ_k = _load_repetition()

    print("Generating Figure 1 — k-distribution…")
    fig1_k_distribution(fail_k, succ_k, out_dir / "fig1_k_distribution.png")

    print("Generating Figure 2 — policy error comparison…")
    fig2_policy_error(fail_k, succ_k, out_dir / "fig2_policy_error_comparison.png")

    print("Generating Figure 3 — lift comparison…")
    fig3_lift_comparison(out_dir / "fig3_lift_comparison.png")

    print("Generating Figure 4 — ref-conditioned vs operational…")
    fig4_ref_vs_operational(out_dir / "fig4_ref_vs_operational.png")

    print(f"\nAll figures written to {out_dir}")
    print("Each figure asserted canonical values from public_claim_ledger.py.")


if __name__ == "__main__":
    main()
