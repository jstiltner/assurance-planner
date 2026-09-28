# Predeclaration: the repetition study

Written before any API call. Nothing in this document reports a result, and no judgment
has been purchased. It exists to be committed *before* the analysis it governs, for the
reason `docs/agent_reward_bench_findings.md` §1 makes concrete: the last predeclaration
in this repository cost us the flattering answer, which is what a predeclaration is for.

## 0. Why this study, and why not the one proposed three weeks of work ago

`docs/agent_reward_bench_findings.md` §7 proposed: current judge, all 1,106 cases, R = 3,
frozen model and prompt, real cost and latency captured. The directional analysis in
`docs/agent_reward_bench_directional.md` changes three things about that design and
leaves the budget roughly where it was.

**The proposed primary cannot be repeated.** Tier A's primary is `functional`, a
programmatic verifier. It has no sampling distribution. Repeating it R times produces R
identical verdicts by construction and measures nothing. The study must run on a
stochastic judge, and the natural one is **`aer`** — Tier A's alternate, Tier B's primary,
priced at a measured $0.0105/judgment, and the only source in the corpus that is both
stochastic and cost-measured.

**The question has sharpened.** The original framing was "what fraction of judge error is
stochastic variance that repetition can resolve versus stable systematic error". The
consensus analysis (`directional` §10) found a category the framing does not name: five
of the primary's 32 missed failures survive a programmatic verifier *and* eight LLM judges
across five backbones and three prompt lineages, and 18 of 32 are reached by two or fewer
of the eight. Error stable across *mechanism* is neither variance nor ordinary bias —
neither repetition nor a ninth evaluator reaches it. The study should therefore produce a
2×2, not a 1×2: stability under repetition crossed with stability across mechanism.

**The estimand has changed.** "Fraction of error that is stochastic" is not directly
estimable at small R, because a case with a per-draw flip probability of 0.1 looks stable
in three draws 73% of the time. What is cleanly estimable at any R is the **ceiling on
what repetition could recover**, and that is the quantity declared in §2.

**Is this still the highest-value next experiment?** Yes, and the directional pass
strengthened the case rather than weakening it. The brief's three deferral conditions were
that the cached analysis might show the primary should plainly be replaced (it did not —
the replacement gate does not fire, `directional` §5), that alternate evidence adds
essentially nothing (it does not show that either — Tier B produces the repository's first
positive escalation signal, `directional` §9), or that the missed-failure stratum needs
more labels first (true against the `functional` primary at n = 32, but *not* against
`aer`, whose missed-failure stratum is n = 101 on the same cases). None of the three
deferral conditions is met. Repetition is also now the **only remaining untested lever**:
adjudication is contraindicated, escalation is conditional on the primary's operating
point, and neither can be evaluated without knowing how much of the error they are aimed
at is merely noise.

## 1. Design, fixed in advance

| | declared value |
| --- | --- |
| judge under study | `aer` prompt (Pan et al. 2024), as transcribed in `scripts/arb_extract.py` |
| backbone | pinned to a dated snapshot, recorded in the run header; **not** `gpt-4o-2024-11-20` unless it is still served at study time |
| corpus | all 1,106 cases of `data/REAL_arb_functional_x_aer.yaml`, no subsampling |
| R | **5** |
| sampling | temperature and seed set to the *judge's deployed configuration*, not to 0.0/0 — see §5 |
| per-draw capture | verdict, raw response, prompt/completion tokens, wall-clock latency, USD cost |
| reference labels | unchanged, upstream primary annotator, as imported |
| arms | one. This is a single-arm study and is not poolable with the cached judgments |

**R = 5, not 3.** The detection probability for a case with per-draw flip probability `p`
is `1 − (p^R + (1−p)^R)`:

| p | R = 3 | R = 5 |
| --- | --- | --- |
| 0.1 | 0.270 | 0.410 |
| 0.2 | 0.480 | 0.672 |
| 0.3 | 0.630 | 0.830 |
| 0.5 | 0.750 | 0.938 |

R = 3 would misclassify most mildly unstable cases as stable and would bias the headline
toward "error is systematic" — the conclusion the project's thesis is already inclined
to. R = 5 is not enough to estimate `p` per case and is not claimed to be; it is enough
that the direction of the residual bias is stated here in advance.

**Why the whole corpus rather than the 324-case stratified subset from
`findings.md` §7.** 1,106 × 5 × $0.0105 ≈ **$58**, against ≈ $32 for the subset at R = 5.
The $26 difference does not buy a design advantage worth the risk of a subsampling
argument, and the earlier conclusion stands: the absence of repetition data in this field
is not a cost problem.

**Cost is an estimate for a different endpoint.** $0.0105/judgment is what upstream paid
in March 2025. It is used here to establish the order of magnitude only. Actual cost is a
measured output of this study, not an input to it.

## 2. Primary estimand, declared before collection

> **`P(at least one draw correct | at least one draw wrong)`**, computed per case and
> reported separately for the two error directions.

This is the ceiling on what any best-of-R or sequential-stopping policy could recover from
repetition alone: a case where every draw is wrong cannot be fixed by drawing again, at
any budget. It is the repetition analogue of `P(alternate correct | primary wrong)`, and
it is deliberately chosen to be the quantity the existing `Conditional` machinery already
reports with a Wilson interval and a thin-denominator marker.

**Stratification, fixed now:**

1. cases where the majority verdict is a **missed failure** (reference fail);
2. cases where the majority verdict is a **false alarm** (reference pass);
3. cases where every draw is correct (the stability floor — reported for completeness,
   and as the denominator that says how much of the corpus is uninteresting).

Reporting a pooled figure across (1) and (2) is forbidden by this predeclaration. That
pooling is the exact defect `directional` §12.1 identified in the Phase 2 analysis, and
repeating it here would reproduce it in a study designed after the correction.

**Secondary estimands, also declared now:**

- the three-way decomposition **stable-correct / unstable / stable-wrong**, per stratum,
  with the R = 5 detection probabilities above attached to every "stable" count;
- the **2×2 of repetition-stability against mechanism-stability**, joining on `case_id`
  to the eight-judge consensus counts in `data/REAL_arb_directional.csv`. The cell that
  matters is *stable under repetition **and** missed by all mechanisms*: it is the share
  of error that neither of the project's two levers reaches;
- **measured cost and latency per judgment**, which are the two UNMEASURED inputs every
  economic statement in this repository is currently blocked on;
- inference saved by sequential stopping versus fixed R = 5, computed retrospectively on
  the collected draws. Declared as secondary because it is an efficiency question and the
  study is not powered to be about it.

## 3. What each outcome would mean, declared before seeing any of it

| outcome | reading | consequence for the project |
| --- | --- | --- |
| recoverable-by-repetition **high** on missed failures | judge error is substantially noise | repetition is the right lever; the escalation architecture is competing with a cheaper fix and must be justified against it, not against doing nothing |
| recoverable-by-repetition **low** on missed failures | judge error is stable | repetition cannot deliver assurance; the case for genuinely different evidence strengthens, and `directional` §9's Tier B escalation signal becomes the thing to pursue |
| **high on false alarms, low on missed failures** | the two error directions have different stability | the planner's single replication count is the wrong control; repetition budget should be directional, which nothing in the codebase currently expresses |
| stable-wrong **and** mechanism-unreachable is a large cell | a floor exists that neither lever clears | the honest output of the planner on such cases is an admission, not a plan, and the residual-error model needs a term for it |

Every row is written before collection so that none of them can be selected afterwards.
No `r*` appears in this table and none will be inferred from the results: this study
measures a quantity, it does not decide anything, and absent a declared `r*` the correct
output remains `NOT DECISION-SUFFICIENT`.

## 4. The conceptual error this study must not commit

**Stable agreement among repeated judgments is not correctness.** A judge that returns
the same wrong verdict five times has zero measured variance and maximal systematic error,
and a naive "repeatability" headline would score it as excellent. Every table produced by
this study must therefore report stability and correctness as two axes, never collapsed:
the three-way decomposition in §2 exists precisely so that `stable-wrong` cannot hide
inside a high agreement rate.

The project's framing stands and this study is the test of its second half:

> Repetition attacks variance. Genuinely different evidence is required to attack stable
> bias. Neither reaches error that is stable across both.

## 5. Threats, and what is being given up

**Temperature.** Upstream ran at `temperature: 0.0, seed: 0`. Repeating *that* measures
provider-side nondeterminism only, which is a real but different and much smaller
quantity than the one the planner's replication machinery is built for. This study runs at
the judge's deployed sampling configuration and records it in the run header. The
consequence is stated up front: **the result is not comparable to the cached judgments**
and may not be pooled with them, which was already true for endpoint reasons.

**Endpoint drift.** The backbone is not the March 2025 snapshot. Any comparison between
this study's marginal accuracy and the cached `aer` accuracy is confounded by model
version and must be reported as such rather than as drift or as agreement.

**One judge, one failure mode, one benchmark population.** The same limitations that ride
on `data/REAL_arb_*` ride on this, and they must be copied onto the run file verbatim
rather than summarised.

**Peeking.** The 1,106 cases are collected in one batch before any statistic is computed.
No stopping rule is applied during collection; the sequential-stopping question in §2 is
answered retrospectively on the complete draws, which is the only way to answer it without
the stopping rule contaminating the estimand.

## 6. Order of operations

1. This document is committed as its own commit, before any collection code runs.
2. The importer writes a run file in the existing paired representation, with
   `synthetic: false`, the limitations list, and the sampling configuration in the header.
3. Only then is the analysis written.

If a result cannot be obtained without deviating from §§1–2, the deviation is recorded in
the analysis document under "Retractions and corrections", and this predeclaration is left
as written.
