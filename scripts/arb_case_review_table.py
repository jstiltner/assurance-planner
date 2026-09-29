"""Emit the structured artifact for the 15-case qualitative review.

The JUDGMENTS dict below holds the analyst's per-case conclusions (Phases 1-6). Everything
else -- which systems were wrong, the reference label, the benchmark -- is joined from the
archive so it cannot drift from the data. No model inference.

Usage:  python scripts/arb_case_review_table.py --out data/shared_unresolved_case_review.csv
"""

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arb_case_evidence import build_case, load_annotations, load_repetitions  # noqa: E402
from arb_shared_unresolved_membership import ALTERNATES, analyse  # noqa: E402

AXTREE_TIER = {
    "claude-3.7-sonnet-noscreen", "gpt-4o-mini-noscreen", "gpt-4o-noscreen",
    "llama-3.3-70b-noscreen", "qwen-2.5-vl-noscreen",
}

# key = (task_id, agent-substring) because two task_ids recur under different agents
JUDGMENTS = {
    ("assistantbench.improved.validation.14", "gpt-4o"): dict(
        reference_confidence="CLEAR",
        evidence_full_trajectory="unknown -- raw trajectory not in snapshot",
        evidence_in_aer_input="yes -- the 4-action history shows a single search and an answer "
                              "sourced from Easyship, with no visit to FedEx/DHL/USPS",
        earliest_failed_layer="5 Evaluation",
        failure_mechanism="evidence-use failure (sufficiency). The goal requires comparing three "
                          "named carriers; the agent consulted one third-party aggregator. AER's "
                          "own rubric warns about action sufficiency and AER did not apply it.",
        deterministic_verifiability="PARTIALLY DETERMINISTIC",
        minimal_invariant="at least one visited URL per named carrier domain before an answer is emitted",
        prompt_fix_candidate="yes -- enforce the existing sufficiency clause on enumerated-source goals",
        richer_representation_candidate="no -- the deficiency is in the action history, already supplied",
        alternate_judge_candidate="weak -- 1 of 8 (nnetnav) correct",
        human_review_needed="no",
        confidence="high",
        notes="Primary cum_reward=0.852 is a continuous AssistantBench score binarised at 0.5 "
              "while cum_raw_reward=0. The 'primary missed a failure' framing is partly a "
              "thresholding artifact of the planner's >0.5 rule.",
    ),
    ("visualwebarena.resized.569", "Qwen"): dict(
        reference_confidence="CLEAR",
        evidence_full_trajectory="no -- the input image is the premise of the goal and is not in any judge input",
        evidence_in_aer_input="no -- goal cites 'this exact item' with an image URL AER cannot fetch",
        earliest_failed_layer="3 Representation",
        failure_mechanism="unseeable premise: item identity is defined by an image no judge receives. "
                          "Compounded by the rubric's abstention clause -- AER cited the agent's "
                          "'information is not available' report as satisfying the goal.",
        deterministic_verifiability="GENUINELY SEMANTIC",
        minimal_invariant="none available without the image; with it, visual item match",
        prompt_fix_candidate="partial -- removing the unconditional abstention clause would fix this instance",
        richer_representation_candidate="yes -- supply the input image to the judge",
        alternate_judge_candidate="strong -- 6 of 8 alternates correct",
        human_review_needed="yes -- visual item identity",
        confidence="high",
        notes="Both mechanisms are independently sufficient to produce the wrong verdict here.",
    ),
    ("visualwebarena.resized.598", "Qwen"): dict(
        reference_confidence="CLEAR",
        evidence_full_trajectory="no -- input image absent from every judge input",
        evidence_in_aer_input="no",
        earliest_failed_layer="3 Representation",
        failure_mechanism="unseeable premise + circular evidence. AER wrote that the agent "
                          "'correctly identified the brand (Sony) from the image'; AER never saw "
                          "the image and inferred the premise from the agent's own search query.",
        deterministic_verifiability="GENUINELY SEMANTIC",
        minimal_invariant="none available without the image",
        prompt_fix_candidate="partial -- forbid treating an agent's assertion about unobserved input as evidence",
        richer_representation_candidate="yes -- supply the input image",
        alternate_judge_candidate="none -- 8 of 8 alternates wrong",
        human_review_needed="yes -- brand identity from image",
        confidence="high",
        notes="Meets the strict A1.6 criterion. Same task under a different agent (#6) also 8/8 wrong.",
    ),
    ("visualwebarena.resized.730", "Qwen"): dict(
        reference_confidence="CLEAR",
        evidence_full_trajectory="no -- input image absent",
        evidence_in_aer_input="no",
        earliest_failed_layer="3 Representation",
        failure_mechanism="unseeable premise. The add-to-compare action genuinely succeeded and the "
                          "caption confirms 'Compare Products (1 item)', so every state signal "
                          "available to the judge is positive; only image similarity could refute it.",
        deterministic_verifiability="GENUINELY SEMANTIC",
        minimal_invariant="none available without the image",
        prompt_fix_candidate="no",
        richer_representation_candidate="yes -- supply the input image",
        alternate_judge_candidate="weak -- 1 of 8 correct, and for an incorrect reason "
                                  "(claimed the final action 'None' meant incompletion)",
        human_review_needed="yes -- visual similarity judgment",
        confidence="high",
        notes="Expert marked side_effect=Yes; the comparison list was modified with a wrong item.",
    ),
    ("visualwebarena.resized.332", "claude"): dict(
        reference_confidence="PLAUSIBLE BUT AMBIGUOUS",
        evidence_full_trajectory="yes",
        evidence_in_aer_input="yes -- the caption lists the comments section as a clickable "
                              "'89 comments' count, not as rendered comments",
        earliest_failed_layer="5 Evaluation",
        failure_mechanism="affordance mistaken for accomplishment. AER read the presence of a "
                          "'Comments Section' heading containing only a count link as evidence the "
                          "agent had navigated to the comments. 11 go_back loops were also ignored.",
        deterministic_verifiability="DETERMINISTICALLY VERIFIABLE",
        minimal_invariant="final URL is the post's comments permalink AND at least one comment body is rendered",
        prompt_fix_candidate="yes -- require a rendered-content check, not a link, for 'navigate to X'",
        richer_representation_candidate="no -- 5 axtree judges also wrong",
        alternate_judge_candidate="none -- 8 of 8 alternates wrong",
        human_review_needed="no",
        confidence="medium",
        notes="Ambiguity is in what 'the comments section' requires: the agent did reach the post "
              "page, which on Postmill shows comments below the fold. Meets strict A1.6.",
    ),
    ("visualwebarena.resized.598", "claude"): dict(
        reference_confidence="CLEAR",
        evidence_full_trajectory="no -- input image absent",
        evidence_in_aer_input="no",
        earliest_failed_layer="3 Representation",
        failure_mechanism="unseeable premise + circular evidence, identical to #3 on the same task "
                          "with a different agent. AER again attributed brand identification to the "
                          "agent's inference rather than to observed evidence.",
        deterministic_verifiability="GENUINELY SEMANTIC",
        minimal_invariant="none available without the image",
        prompt_fix_candidate="partial",
        richer_representation_candidate="yes -- supply the input image",
        alternate_judge_candidate="none -- 8 of 8 alternates wrong",
        human_review_needed="yes",
        confidence="high",
        notes="Meets strict A1.6. The task appears twice in the 15 and is 8/8 wrong both times, "
              "which is what a representation gap looks like -- it does not vary with the agent.",
    ),
    ("visualwebarena.resized.601", "claude"): dict(
        reference_confidence="CLEAR",
        evidence_full_trajectory="no -- input image absent",
        evidence_in_aer_input="partial -- the price constraint is checkable from the caption; the "
                              "brand constraint is not",
        earliest_failed_layer="3 Representation",
        failure_mechanism="unseeable premise on the brand half of a conjunctive goal. AER verified "
                          "the checkable half ($42.30 within $30-$50) and asserted the uncheckable half.",
        deterministic_verifiability="PARTIALLY DETERMINISTIC",
        minimal_invariant="displayed price within the stated range (checkable); brand match (not checkable)",
        prompt_fix_candidate="yes -- require the judge to flag unverifiable conjuncts rather than assume them",
        richer_representation_candidate="yes -- supply the input image",
        alternate_judge_candidate="weak -- 1 of 8 correct, and on a price argument that is wrong",
        human_review_needed="yes -- brand identity from image",
        confidence="high",
        notes="Best illustration of partial verifiability: half the goal is deterministic, half is not.",
    ),
    ("webarena.24", "Qwen"): dict(
        reference_confidence="POSSIBLY INCORRECT",
        evidence_full_trajectory="yes",
        evidence_in_aer_input="yes -- the axtree shows both reviews and neither mentions price fairness",
        earliest_failed_layer="1 Reference",
        failure_mechanism="contested reference. Two experts annotated this trajectory: the primary "
                          "(A) said Unsuccessful, the secondary (H) said Successful and Completely "
                          "Optimal. The repo keeps the first annotator and discards the second, so "
                          "the 'error' is a coin-flip between two human judgments that 9 of 9 "
                          "automated systems resolved the other way.",
        deterministic_verifiability="UNKNOWN",
        minimal_invariant="none -- the disagreement is about whether a true negative answer counts as completion",
        prompt_fix_candidate="no",
        richer_representation_candidate="no -- AER's caption contains the full text of both "
                                        "reviews, so its verdict was well supported by its input",
        alternate_judge_candidate="no -- 7 of 8 wrong, and the 1 'correct' verdict argued from "
                                  "optimality, not from the success criterion",
        human_review_needed="yes -- reference adjudication, not evaluator qualification",
        confidence="high",
        notes="This case should not be counted as an evaluator failure. It is the clearest instance "
              "in the set of the study measuring judges against a reference that is itself contested.",
    ),
    ("webarena.426", "Qwen"): dict(
        reference_confidence="CLEAR",
        evidence_full_trajectory="yes",
        evidence_in_aer_input="yes -- the final URL is a search-results URL and the axtree shows the "
                              "place link present but unclicked",
        earliest_failed_layer="5 Evaluation",
        failure_mechanism="affordance mistaken for accomplishment. The goal is to find the page of a "
                          "place; the agent ran a search and stopped. AER accepted 'the map is "
                          "centered on the correct location' as having reached the page.",
        deterministic_verifiability="DETERMINISTICALLY VERIFIABLE",
        minimal_invariant="final URL matches the place/detail route, not the search route",
        prompt_fix_candidate="yes -- for navigation goals, require terminal URL evidence",
        richer_representation_candidate="no -- the caption already contained the final search "
                                        "URL and a left panel headed 'Search Results'; the axtree "
                                        "judges were not better informed, only better reasoned",
        alternate_judge_candidate="weak -- 1 of 8 correct",
        human_review_needed="no",
        confidence="high",
        notes="Same task as #14 under a different agent, with the identical trajectory and the "
              "identical AER error -- a reproducible rubric gap, not a sampling accident.",
    ),
    ("webarena.491", "Qwen"): dict(
        reference_confidence="CLEAR",
        evidence_full_trajectory="yes",
        evidence_in_aer_input="yes -- the caption and the axtree both show the Comment textbox still "
                              "holding the message text and the adjacent history list empty",
        earliest_failed_layer="5 Evaluation",
        failure_mechanism="affordance mistaken for accomplishment. AER cited the persisting comment "
                          "text and checked notify box as confirmation that the notification was "
                          "sent; a populated form field is pre-submission state. The agent also "
                          "triggered a separate order-confirmation email (expert: side_effect=Yes) "
                          "and then misused report_infeasible to declare completion.",
        deterministic_verifiability="PARTIALLY DETERMINISTIC",
        minimal_invariant="after a submit action the bound input must be cleared, or a confirmation "
                          "row must appear in the history list",
        prompt_fix_candidate="yes -- teach the judge that a retained input value is evidence against submission",
        richer_representation_candidate="no -- all 5 axtree judges had the textbox value and still said success",
        alternate_judge_candidate="none -- 8 of 8 alternates wrong",
        human_review_needed="no",
        confidence="high",
        notes="Meets strict A1.6. The Comments History tab is collapsed in the axtree, so "
              "non-submission is strongly indicated but not conclusively observable -- a real "
              "observability limit sitting underneath a real reasoning failure.",
    ),
    ("webarena.599", "Qwen"): dict(
        reference_confidence="PLAUSIBLE BUT AMBIGUOUS",
        evidence_full_trajectory="yes",
        evidence_in_aer_input="yes -- the caption reports an activated (orange) upvote arrow and an "
                              "Unsubscribe button in the forum sidebar",
        earliest_failed_layer="4 Specification",
        failure_mechanism="entity binding plus an absent rubric dimension. The goal asks to open a "
                          "thread and subscribe; the evidence shows a forum-level subscription and "
                          "an unrequested upvote. AER's rubric asks only whether the task succeeded "
                          "and never asks about unintended state changes, so the side-effect "
                          "evidence in its own input had nowhere to land.",
        deterministic_verifiability="PARTIALLY DETERMINISTIC",
        minimal_invariant="subscription target id equals the thread id; no vote-state delta on any entity",
        prompt_fix_candidate="yes -- add a side-effect question to the AER rubric",
        richer_representation_candidate="no -- 8 of 8 wrong",
        alternate_judge_candidate="none -- 8 of 8 alternates wrong",
        human_review_needed="no",
        confidence="medium",
        notes="Meets strict A1.6. Ambiguous because 'subscribe' has a defensible forum-level reading; "
              "the unrequested upvote is the firmer ground for the expert's label. Note the 7 "
              "non-AER judges do emit a <side> tag, but the pipeline parses only <success>.",
    ),
    ("webarena.723", "claude"): dict(
        reference_confidence="CLEAR",
        evidence_full_trajectory="yes",
        evidence_in_aer_input="yes -- the action history ends in an abstention message and no like action occurs",
        earliest_failed_layer="4 Specification",
        failure_mechanism="rubric clause misapplied across task type. AER's prompt permits "
                          "'explicitly state that the information is not available' as success for "
                          "information-seeking tasks. This is a content-modification task ('Like all "
                          "submissions'), where abstention cannot be success. AER classified the "
                          "task type wrongly and then applied the clause faithfully.",
        deterministic_verifiability="DETERMINISTICALLY VERIFIABLE",
        minimal_invariant="for a modification goal, at least one state-changing action must have "
                          "occurred; a terminal abstention is automatically not success",
        prompt_fix_candidate="yes -- highest-value single prompt change in the set",
        richer_representation_candidate="no -- the caption-tier judges split; the deciding factor was the rubric",
        alternate_judge_candidate="strong -- 6 of 8 alternates correct, including all 5 axtree judges",
        human_review_needed="no",
        confidence="high",
        notes="With #13 this is the cleanest evidence that a rubric edit, not a better model, is the fix.",
    ),
    ("webarena.726", "gpt-4o"): dict(
        reference_confidence="CLEAR",
        evidence_full_trajectory="yes",
        evidence_in_aer_input="yes",
        earliest_failed_layer="4 Specification",
        failure_mechanism="same abstention-as-success clause as #12, on a dislike-all task. Both "
                          "experts who annotated this trajectory called it a Complete Failure.",
        deterministic_verifiability="DETERMINISTICALLY VERIFIABLE",
        minimal_invariant="same as #12",
        prompt_fix_candidate="yes",
        richer_representation_candidate="no",
        alternate_judge_candidate="moderate -- 3 of 8 correct",
        human_review_needed="no",
        confidence="high",
        notes="Two independent annotators agree here, which makes it a much firmer reference than #8.",
    ),
    ("webarena.426", "Llama"): dict(
        reference_confidence="CLEAR",
        evidence_full_trajectory="yes",
        evidence_in_aer_input="yes",
        earliest_failed_layer="5 Evaluation",
        failure_mechanism="affordance mistaken for accomplishment, identical to #9: the same task, "
                          "the same two-action trajectory, the same AER error.",
        deterministic_verifiability="DETERMINISTICALLY VERIFIABLE",
        minimal_invariant="final URL matches the place/detail route, not the search route",
        prompt_fix_candidate="yes",
        richer_representation_candidate="no -- same as #9; the discriminating evidence was in "
                                        "AER's own caption and final URL",
        alternate_judge_candidate="weak -- 2 of 8 correct",
        human_review_needed="no",
        confidence="high",
        notes="The duplication with #9 is informative: this mechanism reproduces across agents.",
    ),
    ("workarena.servicenow.infeasible-navigate-and-order-loaner-laptop-l2", "Qwen"): dict(
        reference_confidence="CLEAR",
        evidence_full_trajectory="yes",
        evidence_in_aer_input="partial -- the order actions are visible, but nothing in the judge's "
                              "input states that the task is designed to be impossible",
        earliest_failed_layer="4 Specification",
        failure_mechanism="withheld specification. The task family name encodes that the correct "
                          "behaviour is to recognise infeasibility (the required 'Exactly build' "
                          "configuration does not exist on the form). The judge is shown the steps "
                          "as though they were achievable and is never told the task is infeasible, "
                          "so it cannot know that placing the order is the failure. The agent also "
                          "submitted a real order for 5 laptops (expert: side_effect=Yes) and then "
                          "called report_infeasible with the reason 'successfully completed'.",
        deterministic_verifiability="DETERMINISTICALLY VERIFIABLE",
        minimal_invariant="for an infeasible-* task: no order-submission event occurred AND the "
                          "terminal report_infeasible reason asserts infeasibility",
        prompt_fix_candidate="yes -- pass the infeasibility flag that the benchmark already holds",
        richer_representation_candidate="no -- the gap is in the task specification, not the observation",
        alternate_judge_candidate="weak -- 1 of 8 correct",
        human_review_needed="no",
        confidence="high",
        notes="The benchmark knows this task is infeasible and the evaluation harness does not pass "
              "that fact along. The infeasible-* family is also heavily represented in the "
              "false-alarm stratum, so this specification gap is not confined to these 15.",
    ),
}

FIELDS = [
    "case_id", "benchmark", "reference_label", "reference_confidence", "systems_wrong",
    "evidence_full_trajectory", "evidence_in_aer_input", "earliest_failed_layer",
    "failure_mechanism", "deterministic_verifiability", "minimal_invariant",
    "prompt_fix_candidate", "richer_representation_candidate", "alternate_judge_candidate",
    "human_review_needed", "confidence", "notes",
]


def judgment_for(case):
    for (task, agent_part), val in JUDGMENTS.items():
        if case["task_id"] == task and agent_part in case["agent"]:
            return val
    raise KeyError(f"no judgment recorded for {case['case_id']}")


def systems_wrong(case):
    """Everything that returned the wrong verdict, named explicitly."""
    wrong = ["functional(primary)"]
    wrong += [f"aer-current(k=0/5)"]
    wrong += sorted(j for j, a in case["alternates"].items() if a.get("verdict_success") == 1)
    return "; ".join(wrong)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    loose, strict, _ = analyse("missed_failure")
    annotations, repetitions = load_annotations(), load_repetitions()

    rows = []
    for cid in loose:
        case = build_case(cid, annotations, repetitions)
        j = judgment_for(case)
        n_wrong_alt = sum(1 for a in case["alternates"].values() if a.get("verdict_success") == 1)
        rows.append({
            "case_id": cid,
            "benchmark": case["benchmark"],
            "reference_label": "fail",
            "systems_wrong": systems_wrong(case),
            **{k: j[k] for k in FIELDS if k in j},
            "notes": j["notes"] + f" [alternates wrong {n_wrong_alt}/8; "
                     f"meets strict A1.6: {'yes' if cid in strict else 'no'}]",
        })

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
