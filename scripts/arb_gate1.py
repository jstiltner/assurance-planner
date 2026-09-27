"""Gate 1: the per-candidate-pair audit table.

Every column here is a property of the *evidence*, not of the complementarity result.
The joint 2x2 (which is what would tell us whether a pair looks interesting) is
deliberately not computed in this file, so that the pair can be predeclared without
having seen it.  Marginal error counts are included because the brief asks for them,
and because a pair with two error counts of zero has no paired support regardless of
how the errors overlap.

Reads ``$ARB_WORKDIR/arb_records.csv`` from scripts/arb_extract.py and writes
data/REAL_arb_gate1_candidate_pairs.csv.  The predeclaration that this table supports,
and the reasons for it, are in docs/agent_reward_bench_gate1.md.
"""

import csv
import itertools
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
WORKDIR = os.environ.get("ARB_WORKDIR") or tempfile.gettempdir()

#: Provenance of each judge: (family, backbone model, prompt lineage, inputs).
#: "prompt lineage" is what decides independence, and it is not visible in the data --
#: it comes from the paper (sec. 4.1) and judge/args.py.  AER and NNetNav are prompts
#: authored in prior work; every "simplified" judge shares one prompt template
#: (Figures 5-6 of the paper) and differs only in backbone and input modality.
PROVENANCE = {
    "functional":                    ("programmatic", "none (benchmark verifier)", "none", "environment state"),
    "aer":                           ("AER-C",        "gpt-4o-2024-11-20",         "AER (Pan et al. 2024)",     "actions + caption"),
    "aerv":                          ("AER-V",        "gpt-4o-2024-11-20",         "AER (Pan et al. 2024)",     "actions + screenshot"),
    "nnetnav":                       ("NNetNav",      "Llama-3.3-70B-Instruct",    "NNetNav (Murty et al. 2025)", "obs summaries"),
    "gpt-4o-noscreen":               ("simplified",   "gpt-4o-2024-11-20",         "simplified (this paper)",   "axtree"),
    "gpt-4o-noaxtree":               ("simplified",   "gpt-4o-2024-11-20",         "simplified (this paper)",   "screenshot"),
    "gpt-4o-mini":                   ("simplified",   "gpt-4o-mini-2024-07-18",    "simplified (this paper)",   "axtree + screenshot"),
    "gpt-4o-mini-noscreen":          ("simplified",   "gpt-4o-mini-2024-07-18",    "simplified (this paper)",   "axtree"),
    "gpt-4o-mini-noaxtree":          ("simplified",   "gpt-4o-mini-2024-07-18",    "simplified (this paper)",   "screenshot"),
    "gpt-4o-mini-noscreen-noaxtree": ("simplified",   "gpt-4o-mini-2024-07-18",    "simplified (this paper)",   "neither"),
    "claude-3.7-sonnet-noscreen":    ("simplified",   "anthropic/claude-3.7-sonnet", "simplified (this paper)", "axtree"),
    "claude-3.7-sonnet-noaxtree":    ("simplified",   "anthropic/claude-3.7-sonnet", "simplified (this paper)", "screenshot"),
    "qwen-2.5-vl-noscreen":          ("simplified",   "Qwen2.5-VL-72B-Instruct",   "simplified (this paper)",   "axtree"),
    "qwen-2.5-vl-noaxtree":          ("simplified",   "Qwen2.5-VL-72B-Instruct",   "simplified (this paper)",   "screenshot"),
    "llama-3.3-70b-noscreen":        ("simplified",   "Llama-3.3-70B-Instruct",    "simplified (this paper)",   "axtree"),
}

#: The nine judges fetched, decided on bandwidth grounds *before* any pair was scored:
#: the six omitted variants embed base64 screenshots in chat_messages (~2.6 GB of the
#: 3.7 GB judgments tree) and every one of them is a screenshot-input sibling of a
#: backbone already present here, so each would have been rated LOW independence
#: against its partner anyway.  These nine still cover every distinct backbone
#: (gpt-4o, gpt-4o-mini, claude-3.7-sonnet, qwen-2.5-vl, llama-3.3-70b) and every
#: distinct prompt lineage (AER, NNetNav, simplified, programmatic).
#: Recorded here so the candidate set cannot be mistaken for the result of shopping.
FETCHED = {
    "functional", "aer", "nnetnav",
    "claude-3.7-sonnet-noscreen", "gpt-4o-noscreen", "gpt-4o-mini-noscreen",
    "gpt-4o-mini-noscreen-noaxtree", "llama-3.3-70b-noscreen", "qwen-2.5-vl-noscreen",
}

#: vllm-hosted judges record total_price 0.0.  That is "self-hosted, never priced",
#: not "free", and conflating the two would invent a cost advantage out of a missing
#: measurement.  The brief forbids backfilling historical API prices, so these stay
#: UNMEASURED.
UNPRICED_PROVIDERS = {"vllm"}


def independence(a, b):
    """A pre-outcome judgement about shared components, in the brief's terms."""
    fa, ma, pa, ia = PROVENANCE[a]
    fb, mb, pb, ib = PROVENANCE[b]
    if fa == "programmatic" or fb == "programmatic":
        return "HIGH: no shared model, no shared prompt, different mechanism"
    shared = []
    if ma == mb:
        shared.append("same backbone")
    if pa == pb:
        shared.append("same prompt")
    if not shared:
        return "MEDIUM: different backbone and different prompt lineage"
    if ma == mb and pa == pb:
        return "LOW: " + ", ".join(shared) + "; differs only in input modality"
    return "LOW-MEDIUM: " + ", ".join(shared)


#: Reproduced verbatim from the dataset card at revision
#: b6d17e646009d6cb63d5dd7be78807b680693f61.  Not paraphrased: the final clause makes
#: carrying it a condition of distributing anything derived from the dataset, and a
#: paraphrase of a licence term is not the term.
TERMS = """\
# Terms of use inherited from AgentRewardBench

Every `REAL_arb_*` file in this directory is derived from the Hugging Face dataset
`McGill-NLP/agent-reward-bench` at revision
`b6d17e646009d6cb63d5dd7be78807b680693f61`.  Its dataset card states:

> ## Terms of Use
>
> By downloading this Dataset, you agree to comply with the following terms of use:
> - Restrictions: You agree not to use the Dataset in any way that is unlawful or would
>   infringe upon the rights of others.
> - Acknowledgment: By using the Dataset, you acknowledge that the Dataset may contain
>   data derived from third-party sources, and you agree to abide by any additional
>   terms and conditions that may apply to such third-party data.
> - Fair Use Declaration: The Dataset may be used for research if it constitutes "fair
>   use" under copyright laws within your jurisdiction. You are responsible for ensuring
>   your use complies with applicable laws.
>
> Derivatives must also include the terms of use above.

The card declares no SPDX licence field, so the terms above are the only grant on
record.  This file is regenerated by `scripts/arb_gate1.py`; do not edit it by hand.
"""


def write_terms():
    with open(os.path.join(REPO, "data", "REAL_arb_TERMS_OF_USE.md"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(TERMS)


def main():
    rows = list(csv.DictReader(open(os.path.join(WORKDIR, "arb_records.csv"), encoding="utf-8")))
    #: The evaluation population, fixed before any pair is looked at: the upstream test
    #: split, primary annotator, reference label not "Unsure".
    rows = [r for r in rows if r["split"] == "test" and r["ref_success"] != "Unsure"]

    by_judge = {}
    for r in rows:
        by_judge.setdefault(r["judge"], {})[(r["benchmark"], r["agent"], r["task_id"])] = r

    judges = sorted(j for j in by_judge if j in PROVENANCE and j in FETCHED)
    #: Polarity: the failure mode is "the trajectory did not achieve the goal", so the
    #: positive class is the *failure*.  Upstream's positive class is success.  Every
    #: count below is in our polarity and the inversion is stated once, here.
    def ref_failure(r):
        return r["ref_success"] == "Unsuccessful"

    def judged_failure(r):
        if r["judge_success"] == "":
            return None
        return r["judge_success"] == "0"

    out = []
    for a, b in itertools.combinations(judges, 2):
        ja, jb = by_judge[a], by_judge[b]
        keys = sorted(set(ja) & set(jb))

        both, ref_pos, ref_neg = 0, 0, 0
        err_a, err_b, missing = 0, 0, 0
        slices = {}
        for k in keys:
            ra, rb = ja[k], jb[k]
            va, vb = judged_failure(ra), judged_failure(rb)
            if va is None or vb is None:
                missing += 1
                continue
            both += 1
            ref = ref_failure(ra)
            if ref:
                ref_pos += 1
            else:
                ref_neg += 1
            err_a += (va != ref)
            err_b += (vb != ref)
            slices[ra["benchmark"]] = slices.get(ra["benchmark"], 0) + 1

        pa = {r["provider"] for r in ja.values()}
        pb = {r["provider"] for r in jb.values()}
        cost_a = "UNMEASURED (self-hosted)" if pa & UNPRICED_PROVIDERS else (
            "none (no model call)" if a == "functional" else "measured USD")
        cost_b = "UNMEASURED (self-hosted)" if pb & UNPRICED_PROVIDERS else (
            "none (no model call)" if b == "functional" else "measured USD")

        out.append({
            "primary": a,
            "alternate": b,
            "paired_cases": both,
            "ref_labelled": both,
            "slices": " ".join(f"{k}={v}" for k, v in sorted(slices.items())),
            "ref_failure": ref_pos,
            "ref_success": ref_neg,
            "primary_errors": err_a,
            "alternate_errors": err_b,
            "independence": independence(a, b),
            "label_contamination": "none (6 human experts; no judge saw or set a label)",
            "cost": f"{cost_a} / {cost_b}",
            "latency": "UNMEASURED for both (no judge timing recorded upstream)",
            "repeats": "1 (single-shot, temperature 0, seed 0)",
            "unparsed_dropped": missing,
        })

    out.sort(key=lambda r: (r["primary"], r["alternate"]))
    dest = os.path.join(REPO, "data", "REAL_arb_gate1_candidate_pairs.csv")
    with open(dest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    #: Emitted next to the table rather than pasted into a doc by hand: the upstream
    #: terms require that derivatives carry them, and a requirement that depends on
    #: somebody remembering is one that eventually is not met.
    write_terms()
    print(f"{len(out)} candidate pairs -> {dest}")
    print(f"evaluation population: test split, primary annotator, non-Unsure = "
          f"{len({(r['benchmark'], r['agent'], r['task_id']) for r in rows})} trajectories")
    return out


if __name__ == "__main__":
    main()
