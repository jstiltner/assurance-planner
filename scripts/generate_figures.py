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

    # Cost annotation, derived rather than typed. Corrected 2026-10-02: these were four hardcoded
    # strings, and two of them were wrong in the same way -- "Single call" carried "$46.18 (~5
    # calls)", which is the majority-of-5 cost, so the figure showed one call and five calls at the
    # same price and invited the reader to conclude voting was free. The fourth also overprinted
    # the two-line tick label beneath it.
    # Both strata -- fail_k and succ_k are the two halves of the 1,106-case population.
    n_cases = len(fail_k) + len(succ_k)
    _assert(n_cases, CANONICAL["rep_n_cases"], "fig2_n_cases", tol=0.5)
    per_call = CANONICAL["rep_cost_usd"] / CANONICAL["rep_n_calls"]
    policy_calls = [
        n_cases,                              # one call per case
        n_cases * 3,                          # majority-of-3 always draws 3
        CANONICAL["rep_n_calls"],             # majority-of-5 is the full 5,530
        CANONICAL["rep_stopping_calls"],      # first-to-3 stops at 3, 4 or 5
    ]
    _assert(policy_calls[2] / n_cases, 5.0, "maj5_calls_per_case", tol=0.01)
    saving = 1 - CANONICAL["rep_stopping_calls"] / CANONICAL["rep_n_calls"]
    _assert(saving, CANONICAL["rep_stopping_call_reduction"], "stopping_saving", tol=0.0005)
    cost_labels = [
        f"${c * per_call:,.2f}\n({c:,} calls)" for c in policy_calls
    ]
    # The saving names its own numerator and denominator here. Until 2026-10-03 this appended a
    # bare "−39.7%" to a label reading "(3,336 calls)", which is the same count-beside-percentage
    # pairing with no denominator that the prose was corrected for -- 3,336 is the count USED and
    # 3,336/5,530 is 60.3%. A correction that stops at the prose leaves the figure asserting the
    # thing the prose retracted.
    cost_labels[-1] = (f"${policy_calls[-1] * per_call:,.2f}\n"
                       f"({policy_calls[-1]:,} calls used)\n"
                       f"−{saving * 100:.1f}% = {CANONICAL['rep_stopping_calls_saved']:,} "
                       f"saved of {CANONICAL['rep_stopping_calls_full']:,}")

    ax.set_xticks(x)
    ax.set_xticklabels(policies, fontsize=9)
    # Offset in points below the tick labels, so a two-line policy name cannot be overprinted.
    for xi, cost in zip(x, cost_labels):
        ax.annotate(cost, xy=(xi, 0), xycoords=("data", "axes fraction"),
                    xytext=(0, -34), textcoords="offset points",
                    ha="center", va="top", fontsize=7, color="#555555", linespacing=1.3)
    ax.set_ylabel("Error rate (%)", fontsize=9)
    ax.set_ylim(0, 35)
    ax.set_title(
        "Figure 2 — Error rate by voting policy  [PREREGISTERED]\n"
        "gpt-4o-2024-11-20, temp 0.0 / seed 0  ·  n = 1,106 cases",
        fontsize=10
    )
    ax.legend(fontsize=9)
    ax.tick_params(labelsize=8)
    # y is -0.13, not -0.06: the cost annotation under the last tick runs to three lines now and
    # the caption overprinted its third line at the old offset.
    fig.text(
        0.5, -0.13,
        "More voting did not improve error in either direction. First-to-3 stopping used "
        f"{saving * 100:.1f}% fewer calls at verdicts\n"
        "identical to majority-of-5 BY CONSTRUCTION — the two cannot disagree once three of "
        "five agree, so the call\n"
        "saving is the only empirical part. This read \"reproduced majority-of-5 verdicts "
        "exactly\" until 2026-10-03.\n"
        f"Costs are the {CANONICAL['rep_n_calls']:,} analysed calls priced per call; "
        f"${CANONICAL['rep_billed_cost_usd']:.2f} was billed, including "
        f"{CANONICAL['rep_duplicate_valid_calls']} valid calls that never entered the analysis.\n"
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

    # Until 2026-10-02 this figure was three bare bars. The only comparison it afforded a
    # reader was null-height vs RC1-height, which is the one comparison the data does not
    # support: the bars sit on different task sets (94 / 80 / 109) and their difference
    # straddles zero. Intervals and task counts are therefore not decoration here.
    unc = probe["uncertainty"]
    _assert(unc["NULL"]["tasks"], CANONICAL["null_within_task_tasks"], "null_tasks", tol=0.5)
    _assert(unc["RC1"]["tasks"], CANONICAL["rc1_within_task_tasks"], "rc1_tasks", tol=0.5)
    _assert(unc["ORACLE"]["tasks"], CANONICAL["oracle_within_task_tasks"], "oracle_tasks", tol=0.5)
    diff = unc["paired_differences"]["NULL_minus_RC1"]
    _assert(diff["mean"], CANONICAL["null_minus_rc1_lift"], "null_minus_rc1", tol=0.005)
    for key, canon in [("ORACLE", "mh_oracle_lift"), ("NULL", "mh_null_lift"),
                       ("RC1", "mh_rc1_lift")]:
        _assert(unc[key]["mh"], CANONICAL[canon], canon, tol=0.005)
        _assert(unc[key]["mh_cluster_ci"][0], CANONICAL[canon + "_ci"][0], canon + "_lo", tol=0.005)
        _assert(unc[key]["mh_cluster_ci"][1], CANONICAL[canon + "_ci"][1], canon + "_hi", tol=0.005)

    order = ["ORACLE", "NULL", "RC1"]
    labels = [
        f"Oracle construct\n(required write missing;\nbenchmark-authoritative)\n{unc['ORACLE']['tasks']} tasks",
        f"Null rule\n(no successful write;\nno model)\n{unc['NULL']['tasks']} tasks",
        f"RC1\n(production detector;\nfresh corpus)\n{unc['RC1']['tasks']} tasks",
    ]
    lifts = [oracle_lift, null_lift, rc1_lift]
    lift_err = [[lifts[i] - unc[k]["lift_ci"][0] for i, k in enumerate(order)],
                [unc[k]["lift_ci"][1] - lifts[i] for i, k in enumerate(order)]]
    mh = [unc[k]["mh"] for k in order]
    mh_err = [[mh[i] - unc[k]["mh_cluster_ci"][0] for i, k in enumerate(order)],
              [unc[k]["mh_cluster_ci"][1] - mh[i] for i, k in enumerate(order)]]
    colors = [ORACLE_COLOR, NULL_COLOR, RC1_COLOR]
    hatches = ["//", "", ""]
    evidence = ["ORACLE / undeployable", "EXPLORATORY / not accepted", "PREREGISTERED / FRESH-CORPUS"]

    x = list(range(3))
    fig, ax = plt.subplots(figsize=(9, 5.6))
    bars = ax.bar([i - 0.19 for i in x], lifts, width=0.38, color=colors,
                  edgecolor="#333333", linewidth=0.8, hatch_linewidth=1.0,
                  yerr=lift_err, capsize=4,
                  error_kw={"ecolor": "#222222", "elinewidth": 1.2})
    for bar, h in zip(bars, hatches):
        bar.set_hatch(h)
    # MH is the estimator that keeps each rule inside its own strata and weights them by
    # information; it is shown beside the pooled lift so no single bar height is the story.
    ax.bar([i + 0.19 for i in x], mh, width=0.38, color="white",
           edgecolor=colors, linewidth=1.4, yerr=mh_err, capsize=4,
           error_kw={"ecolor": "#222222", "elinewidth": 1.2},
           label="Mantel–Haenszel, stratified by task")

    ax.axhline(1.0, color="#333333", linewidth=1.0, linestyle="--", label="No lift (1.0×)")
    ax.axhspan(0.8, 1.0, color="#cccccc", alpha=0.35, zorder=0)

    ax.text(2.48, 2.28, "A1 volume gate: <15%\n(all three fail at 17–25%)",
            fontsize=7.5, color="#888888", ha="right")

    for i, (lift, evd) in enumerate(zip(lifts, evidence)):
        ax.text(i - 0.19, unc[order[i]]["lift_ci"][1] + 0.03, f"{lift:.3f}×\n[{evd}]",
                ha="center", va="bottom", fontsize=7, linespacing=1.3)
    for i, v in enumerate(mh):
        ax.text(i + 0.19, unc[order[i]]["mh_cluster_ci"][1] + 0.03, f"MH {v:.3f}×",
                ha="center", va="bottom", fontsize=7, color="#444444")

    # The withdrawn comparison, drawn as withdrawn. A reader who reaches for the
    # null-vs-RC1 height difference should meet the interval that forbids it.
    ax.annotate("", xy=(1.0, 1.75), xytext=(2.0, 1.75),
                arrowprops={"arrowstyle": "<->", "color": "#b00020", "linewidth": 1.1})
    ax.text(1.5, 1.79,
            # Says which quantity it is. A reader differencing the two bars gets +0.070, not
            # +0.078, and until 2026-10-03 nothing on this figure said the quoted number was the
            # mean of the 2,000 paired resample differences.
            f"NULL − RC1 = {diff['mean']:+.3f}  "
            f"[{diff['ci'][0]:+.3f}, {diff['ci'][1]:+.3f}]\n"
            f"mean of 2,000 paired task resamples (differencing the bars: {diff['point']:+.3f})\n"
            "straddles 0 — NO ordering supported",
            ha="center", va="bottom", fontsize=7.5, color="#b00020")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("Within-task lift on reference FAIL outcome", fontsize=9)
    ax.set_ylim(0.8, 3.45)
    ax.set_title(
        "Figure 3 — Oracle / null baseline / RC1 lift comparison  [PREREGISTERED + ORACLE + EXPLORATORY]\n"
        "τ-bench, 1,980 records, 165 tasks  ·  95% task-level cluster bootstrap, 2,000 resamples",
        fontsize=10
    )
    ax.legend(fontsize=8, loc="upper right")
    ax.tick_params(labelsize=8)
    # The x tick labels are four lines tall; -0.04 put this on top of them.
    fig.text(
        0.5, -0.22,
        "The oracle construct is not deployable (benchmark-authoritative actions, class D). "
        "The null rule fails the volume gate and was preregistered as disqualified.\n"
        "The three bars are NOT computed on the same tasks: the within-task filter keeps only tasks where a given rule both fires and does not.\n"
        "RC1 is the production-visible detector: it did not outperform the null rule on the deployable outcome, and did not fall below it either —\n"
        "neither RC1 nor the null rule is distinguishable from 1.0×. Only the oracle separates. "
        "Corrected 2026-10-02; the previous version of this figure drew three bare bars\n"
        "and its caption read \u0022it fell below the null rule\u0022, an ordering the intervals do not support.\n"
        "The oracle/RC1 gap shows the latent construct carries signal RC1 did not recover. "
        "It does not show a production-valid representation exists.\n"
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

    # Direction-matched reference-conditioned rates. Added 2026-10-02: until then this figure
    # showed pooled recovery beside the two direction-specific precisions and nothing else, so
    # the only subtraction it invited was the across-direction one that produced the withdrawn
    # "20-30 points". Each operational bar now stands next to its own matched comparator.
    catch = mf_num / mf_den
    rescue = fa_num / fa_den

    _assert(pooled_recovery, CANONICAL["arb_predeclared_recovery"], "arb_pooled_recovery")
    _assert(op_fail_prec, CANONICAL["arb_operational_overturn_fail"], "op_fail_prec")
    _assert(op_pass_prec, CANONICAL["arb_operational_overturn_pass"], "op_pass_prec")
    _assert(catch, CANONICAL["arb_catch_missed_failure"], "arb_catch_missed_failure")
    _assert(rescue, CANONICAL["arb_rescue_false_alarm"], "arb_rescue_false_alarm")
    _assert((catch - op_fail_prec) * 100, CANONICAL["arb_gap_missed_failure_pp"],
            "arb_gap_missed_failure_pp", tol=0.05)
    _assert((rescue - op_pass_prec) * 100, CANONICAL["arb_gap_false_alarm_pp"],
            "arb_gap_false_alarm_pp", tol=0.05)
    _assert(mf_den, CANONICAL["arb_missed_failures"], "missed_failures")
    _assert(fa_den, CANONICAL["arb_false_alarms"], "false_alarms")

    fig, ax = plt.subplots(figsize=(8, 5))

    # Grouped in matched pairs: each operational rate beside the reference-conditioned rate
    # for the SAME error direction. The pooled 0.543 is kept on the left, labelled as the
    # quantity that is not comparable to either, because removing it would hide what the
    # published claim was computed from.
    categories = [
        ("Reference-conditioned\nPOOLED recovery\nP(alt correct | primary wrong)\n"
         f"[NOT executable; not comparable\nto either pair — n = {total_errors}]",
         pooled_recovery, "#aec7e8", "//"),
        (f"Ref-conditioned:\nmissed-failure catch\n[{mf_num}/{mf_den}]",
         catch, "#aec7e8", "//"),
        (f"Operational:\noverturn-to-fail\n[{op_fail_num}/{op_fail_den}]",
         op_fail_prec, REF_FAIL_COLOR, ""),
        (f"Ref-conditioned:\nfalse-alarm rescue\n[{fa_num}/{fa_den}]",
         rescue, "#aec7e8", "//"),
        (f"Operational:\noverturn-to-pass\n[{op_pass_num}/{op_pass_den}]",
         op_pass_prec, REF_SUCC_COLOR, ""),
    ]

    x_positions = [0, 1.8, 2.7, 4.3, 5.2]
    bar_width_base = 0.8

    for xi, (label, val, color, hatch) in zip(x_positions, categories):
        ax.bar(xi, val, width=bar_width_base, color=color, edgecolor="#333333",
               linewidth=0.8, hatch=hatch)
        ax.text(xi, val + 0.01, f"{val:.3f}", ha="center", va="bottom", fontsize=10,
                fontweight="bold")
        ax.text(xi, -0.04, label, ha="center", va="top", fontsize=7,
                linespacing=1.3, transform=ax.get_xaxis_transform())

    # Label each matched gap on the figure, so the only subtraction the figure suggests is
    # the within-direction one.
    for lo, hi, top, gap_pp, name in [
        (1.8, 2.7, max(catch, op_fail_prec), (catch - op_fail_prec) * 100, "missed failures"),
        (4.3, 5.2, max(rescue, op_pass_prec), (rescue - op_pass_prec) * 100, "false alarms"),
    ]:
        y = top + 0.07
        ax.plot([lo, lo, hi, hi], [y - 0.02, y, y, y - 0.02], color="#333333", linewidth=0.8)
        ax.text((lo + hi) / 2, y + 0.008, f"−{gap_pp:.1f} pp\n({name})", ha="center",
                va="bottom", fontsize=7.5, fontweight="bold", color="#333333",
                linespacing=1.2)

    # Error direction annotation
    ax.text(0, 0.62, f"n_primary = {total_errors}\n({mf_den} missed failures\n"
                     f"+ {fa_den} false alarms)",
            ha="center", fontsize=7.5, color="#333333",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#aaaaaa"))

    ax.set_xticks([])
    ax.set_xlim(-0.8, 6.0)
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
        "The reference-conditioned quantities use the ground-truth label no runtime system has — "
        "they are not executable policies.\n"
        "Matched by error direction, the operational quantities ran 10.3 and 9.7 points lower. "
        "Across all eight alternates the false-alarm-side\ngap is always positive "
        "(+9.7 to +46.0 pp); the missed-failure-side gap ranges −14.7 to +23.1 pp and is "
        "negative for two.\n"
        "Evidence class: EXPLORATORY. Single primary/alternate pair. "
        "Caption corrected 2026-10-02: read \"20–30 points lower\", which\n"
        "subtracted the pooled bar on the left from the direction-specific bars on the right.",
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
