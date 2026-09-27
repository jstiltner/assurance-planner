"""Phase 1: import the predeclared AgentRewardBench pairs as characterization runs.

This is the smallest thing that turns the extract into the representation the existing
paired machinery already reads.  It computes no statistics.  What it is careful about:

  - upstream case identity survives.  ``case_id`` is
    ``<benchmark>/<agent-under-test>/<upstream task_id>``, so any row can be traced back
    to one file in the upstream judgments tree without consulting a mapping table.
  - the dataset revision rides on the evaluator identity itself
    (``arb-aer-c-gpt-4o-2024-11-20@b6d17e6``) rather than living only in a comment,
    because an evidence file that gets copied loses comments before it loses its header.
  - a judgment that could not be parsed stays missing.  A missing *alternate* verdict
    omits ``alternate_observations``, which the loader already treats as "never sent to
    the alternate" and excludes from paired statistics.  A missing *primary* verdict
    drops the case, and the count is reported.
  - cost is emitted only where it was measured.  ``functional`` makes no model call and
    vllm-hosted judges record a literal 0.0 that means "self-hosted, never priced"; both
    are left absent so the report prints UNMEASURED rather than inventing a free
    evaluator.  Token counts are not converted into money.
  - ``synthetic: false`` is written explicitly, and the limitations list says in the file
    that the evidence was collected by someone else.  Those two facts travel onto every
    planner input derived from it.

Usage:
    python scripts/arb_import.py           # Tier A and Tier B, into data/
    python scripts/arb_import.py --tier-c  # also the seven secondary pairs, into $ARB_WORKDIR
"""

import csv
import datetime
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
WORKDIR = os.environ.get("ARB_WORKDIR") or tempfile.gettempdir()

REV = "b6d17e646009d6cb63d5dd7be78807b680693f61"
SHORT_REV = REV[:7]

#: Our identity for each upstream judge.  Not upstream's key: `functional` records
#: `provider: openai, judge_model_name: judge` in its JSON as boilerplate despite making
#: no model call, and carrying that forward would describe a programmatic verifier as an
#: OpenAI evaluator.
EVALUATORS = {
    "functional":                    "arb-functional-verifier",
    "aer":                           "arb-aer-c-gpt-4o-2024-11-20",
    "nnetnav":                       "arb-nnetnav-llama-3.3-70b",
    "claude-3.7-sonnet-noscreen":    "arb-simplified-claude-3.7-sonnet-axtree",
    "gpt-4o-noscreen":               "arb-simplified-gpt-4o-axtree",
    "gpt-4o-mini-noscreen":          "arb-simplified-gpt-4o-mini-axtree",
    "gpt-4o-mini-noscreen-noaxtree": "arb-simplified-gpt-4o-mini-neither",
    "llama-3.3-70b-noscreen":        "arb-simplified-llama-3.3-70b-axtree",
    "qwen-2.5-vl-noscreen":          "arb-simplified-qwen-2.5-vl-axtree",
}

#: Judges whose recorded price is a measurement.  Everything else is absent-by-construction
#: (no model call) or unpriced-by-hosting (vllm records 0.0), and neither is a cost of 0.
PRICED = {"aer", "claude-3.7-sonnet-noscreen", "gpt-4o-noscreen", "gpt-4o-mini-noscreen",
          "gpt-4o-mini-noscreen-noaxtree"}

FAILURE_MODE = "ARB-TRAJECTORY-GOAL-NOT-ACHIEVED@v1"
FAILURE_DESCRIPTION = (
    "The agent's trajectory did not achieve the task goal, as judged by a human expert "
    "annotator on the full trajectory. Upstream's positive class is success; this is the "
    "inverse, so that the positive class is the failure being detected."
)
POPULATION = "arb-test-split-primary-annotator"
DISTRIBUTION = "arb-4agents-x-4benchmarks-2025-03"

TIER_A = ("functional", "aer")
TIER_B = ("aer", "nnetnav")
TIER_C = [("functional", alt) for alt in (
    "claude-3.7-sonnet-noscreen", "gpt-4o-noscreen", "gpt-4o-mini-noscreen",
    "gpt-4o-mini-noscreen-noaxtree", "llama-3.3-70b-noscreen", "nnetnav",
    "qwen-2.5-vl-noscreen",
)]


def cost_note(judge):
    if judge in PRICED:
        return "measured USD per judgment (cost.total_price)"
    if judge == "functional":
        return "no model call, therefore never priced -- NOT a measured cost of zero"
    return "self-hosted via vllm, records a literal 0.0 -- NOT a measured cost of zero"


def limitations(primary, alternate, dropped, alt_missing, measured_on):
    """The caveat list.  Every entry here travels onto derived planner inputs."""
    out = [
        "EXTERNALLY SOURCED REAL EVIDENCE. These are real expert labels and real judge "
        f"verdicts collected by McGill-NLP, not by this project: Hugging Face dataset "
        f"McGill-NLP/agent-reward-bench at revision {REV}. Nothing here was generated. "
        "Nothing here was collected under this project's protocol either, so the "
        "protocol's guarantees about sampling and repetition do not apply to it.",
        "Derivatives of this file must carry the upstream Terms of Use; see "
        "data/REAL_arb_TERMS_OF_USE.md.",
        "SINGLE-SHOT. Every judgment was produced once at temperature 0.0, seed 0. This "
        "file supports paired correctness and complementarity. It measures NOTHING about "
        "same-input stochastic noise, and variation between cases must not be read as "
        "variation between repeats.",
        "LATENCY UNMEASURED for both sources. Upstream records no judge timing at all; "
        "the elapsed time it does record belongs to the agent under test, not the judge.",
        f"COST for the primary ({primary}): {cost_note(primary)}.",
        f"COST for the alternate ({alternate}): {cost_note(alternate)}.",
        "BENCHMARK POPULATION, NOT DEPLOYMENT TRAFFIC. Four agent benchmarks. The "
        "reference-failure rate is a property of how hard these benchmarks are for these "
        "four agents, and is not a base rate to plan against. Every prevalence-dependent "
        "statistic inherits that.",
        "ONE FAILURE MODE. Trajectory success is the endpoint. Upstream also records side "
        "effects and looping; neither is used here.",
        "Reference labels are the upstream primary annotator's, resolved by upstream's own "
        "rule (first annotation for a (benchmark, model, task) triple). Second annotations "
        "measure agreement and never adjudicate. 'Unsure' is dropped, not coerced.",
        f"Judgments were produced upstream on or before {measured_on}; the model endpoints "
        "behind them have since changed and cannot be re-queried at that state.",
    ]
    if dropped:
        out.append(
            f"{dropped} cases dropped: the primary's judgment could not be parsed. "
            "Upstream would have scored these as wrong predictions; here an unparseable "
            "verdict is missing, not incorrect."
        )
    if alt_missing:
        out.append(
            f"{alt_missing} cases carry no alternate verdict for the same reason and are "
            "excluded from every paired statistic rather than counted as agreement."
        )
    return out


def yaml_quote(text):
    return "'" + text.replace("'", "''") + "'"


def wrap(text, width=94, indent="  "):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    lines.append(cur)
    return f"\n{indent}  ".join(lines)


def build(rows, primary, alternate):
    by_judge = {}
    for r in rows:
        by_judge.setdefault(r["judge"], {})[(r["benchmark"], r["agent"], r["task_id"])] = r

    jp, ja = by_judge[primary], by_judge[alternate]
    keys = sorted(set(jp) & set(ja))

    cases, dropped, alt_missing, dates = [], 0, 0, []
    for key in keys:
        rp, ra = jp[key], ja[key]
        if rp["judge_success"] == "":
            dropped += 1
            continue
        benchmark, agent, task_id = key
        #: Polarity inverted once, here: upstream 1 == success, our positive == failure.
        entry = {
            "case_id": f"{benchmark}/{agent}/{task_id}",
            "slice_id": benchmark,
            "reference_label": "fail" if rp["ref_success"] == "Unsuccessful" else "pass",
            "primary": "fail" if rp["judge_success"] == "0" else "pass",
            "primary_cost": rp["total_price_usd"] if primary in PRICED else "",
        }
        if ra["judge_success"] == "":
            alt_missing += 1
        else:
            entry["alternate"] = "fail" if ra["judge_success"] == "0" else "pass"
            entry["alternate_cost"] = ra["total_price_usd"] if alternate in PRICED else ""
        cases.append(entry)
        for r in (rp, ra):
            if r["response_created"] not in ("", "None"):
                dates.append(int(r["response_created"]))

    measured_on = (
        datetime.datetime.fromtimestamp(max(dates), datetime.UTC).date().isoformat()
        if dates else "unknown"
    )
    return cases, dropped, alt_missing, measured_on


def observation(verdict, cost):
    if cost:
        return f"[{{verdict: {verdict}, cost: {float(cost):.6f}}}]"
    return f"[{{verdict: {verdict}}}]"


def write_run(dest, primary, alternate, cases, dropped, alt_missing, measured_on):
    lines = [
        "# Generated by scripts/arb_import.py -- do not edit by hand.",
        "# Real evidence, collected by McGill-NLP and imported, not collected here.",
        f"# Upstream: McGill-NLP/agent-reward-bench @ {REV}",
        "# Terms of use: data/REAL_arb_TERMS_OF_USE.md",
        "experiment:",
        f"  evaluator_version: {EVALUATORS[primary]}@{SHORT_REV}",
        f"  alternate_version: {EVALUATORS[alternate]}@{SHORT_REV}",
        f"  failure_mode_version: {FAILURE_MODE}",
        f"  population_id: {POPULATION}",
        f"  sut_distribution_id: {DISTRIBUTION}",
        f"  measured_on: '{measured_on}'",
        f"  run_id: arb-{primary}-x-{alternate}-{SHORT_REV}",
        "synthetic: false",
        f"failure_description: {yaml_quote(FAILURE_DESCRIPTION)}",
        "limitations:",
    ]
    for item in limitations(primary, alternate, dropped, alt_missing, measured_on):
        #: Quoted rather than left as a plain scalar: several of these contain a colon
        #: followed by a space, which YAML reads as a mapping inside a sequence item.
        lines.append(f"- {wrap(yaml_quote(item))}")
    lines.append("cases:")
    for c in cases:
        lines.append(f"- case_id: {yaml_quote(c['case_id'])}")
        lines.append(f"  slice_id: {c['slice_id']}")
        lines.append(f"  reference_label: {c['reference_label']}")
        lines.append(f"  observations: {observation(c['primary'], c['primary_cost'])}")
        if "alternate" in c:
            lines.append(
                "  alternate_observations: "
                + observation(c["alternate"], c["alternate_cost"])
            )
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def main():
    path = os.path.join(WORKDIR, "arb_records.csv")
    rows = [
        r for r in csv.DictReader(open(path, encoding="utf-8"))
        if r["split"] == "test" and r["ref_success"] != "Unsure"
    ]

    pairs = [(TIER_A, "A", REPO), (TIER_B, "B", REPO)]
    if "--tier-c" in sys.argv:
        pairs += [(p, "C", WORKDIR) for p in TIER_C]

    for (primary, alternate), tier, root in pairs:
        cases, dropped, alt_missing, measured_on = build(rows, primary, alternate)
        name = f"REAL_arb_{primary}_x_{alternate}.yaml"
        dest = os.path.join(root, "data", name) if root == REPO else os.path.join(root, name)
        write_run(dest, primary, alternate, cases, dropped, alt_missing, measured_on)
        paired = sum(1 for c in cases if "alternate" in c)
        print(f"tier {tier}: {primary} x {alternate}  cases={len(cases)} paired={paired} "
              f"primary_dropped={dropped} alt_missing={alt_missing} -> {dest}")


if __name__ == "__main__":
    main()
