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

---
---

# Amendment 1 — 2026-09-27, before inference

**Everything above this line is left exactly as it was committed.** Nothing in §§0–6 is
edited, and the original primary estimand is not erased. This amendment adds estimands,
demotes one, and fixes estimators that §2 left underspecified. Where it conflicts with
§2, the amendment governs, and §2 remains visible as the record of what was declared
first.

> **The study was predeclared before inference, but this amendment was made before
> inference after a zero-cost audit identified that the original primary estimand detects
> stochasticity without measuring whether repetition actually corrects the decision.**

That is the whole of the defect. `P(at least one draw correct | at least one draw wrong)`
is a ceiling on an oracle that can recognise a correct draw when it sees one. No
deployable policy can do that. A case that goes 1/5 correct counts as fully "recoverable"
under §2 and is wrong under every majority rule anyone would actually run. §2's estimand
measures whether the judge *wobbles*; the question the project needs answered is whether
spending money *fixes the verdict*. Those come apart precisely where the money is.

This is the same defect, in a different costume, that
`docs/agent_reward_bench_directional.md` §12.1 found in the Phase 2 analysis: a quantity
that conditions on something a running system does not know. It was caught there and
reintroduced here, in a document written after the correction. Recorded that way.

## A1.0 What the zero-cost audit did and did not change

`docs/agent_reward_bench_conditional.md` was the audit. It found **no contradiction that
makes this study invalid**, so per the governing brief the parameters are untouched:

| | declared in §1 | after this amendment |
| --- | --- | --- |
| judge under study | `aer` | **`aer`, unchanged** |
| corpus | all 1,106 cases | **all 1,106, unchanged** |
| R | 5 | **5, unchanged** |
| arms | one | **one, unchanged** |

It did strengthen the premise, and the strengthening is recorded here so it cannot later
be presented as a result of this study. Conditional on the reference label, every one of
the eight alternate evaluators misses the primary's missed failures at 2.8×–5.1× its own
base rate, with odds ratios in a narrow 5.08–11.11 band across five backbones and three
prompt lineages. "Buy a different evaluator" is therefore a weaker lever on the
missed-failure stratum than the pooled figures implied, which raises — not lowers — the
value of knowing how much of that error is merely noise.

It also reinforces §2's prohibition on pooled reporting. That prohibition is now doubled:
pooling across reference labels is forbidden here for the same reason it produced a
confounded phi there.

## A1.1 Revised primary representation — the full count, always stratified

The per-case unit of analysis is the **complete count of correct judgments out of five**,
`k ∈ {0, 1, 2, 3, 4, 5}`, reported as a six-bucket distribution and **always stratified by
reference label**. Pooling reference-success and reference-failure cases is forbidden for
every primary conclusion, exactly as in §2.

| k | reading |
| --- | --- |
| 0/5 | no correct draw observed in five |
| 1/5 | correct is the minority outcome; wrong under every majority rule |
| 2/5 | correct is the minority outcome; recoverable by some 3-subsets, not by majority-of-5 |
| 3/5 | correct is the majority outcome, with observed contrary draws |
| 4/5 | correct is the majority outcome, with one observed contrary draw |
| 5/5 | no contrary outcome observed in five |

**Wording that is binding on every table and sentence this study produces:**

> **`0/5` does not prove deterministic or systematic error. `5/5` does not prove true
> stability. They mean that no contrary outcome was observed in five draws.**

The §1 detection table quantifies this and must be reprinted adjacent to any count of
`0/5` or `5/5`: at a per-draw flip probability of 0.1, five draws fail to show the flip
59% of the time. Any noun phrase implying a latent property of the case — "deterministic
errors", "truly stable", "irreducible" — is prohibited in favour of the observational
form "repetition-consistent over R = 5".

## A1.2 Primary estimands are policy estimands

> **How much actual classification error can executable repetition policies remove, and at
> what inference cost?**

Four policies, each an estimator fixed here in full. Every one is reported **separately
for missed failures and false alarms**; see A1.3.

**(a) Single draw.** No draw is privileged as "the real one". The estimator is the
unweighted mean over cases of `(5 − k)/5`, which equals total wrong draws over total
draws. It is the expected error rate of a policy that buys one judgment.

**(b) Majority-of-3, averaged symmetrically over all ten 3-subsets.** There are
`C(5,3) = 10` triplets and **no triplet is chosen**. For a case with `k` correct of five,
the exact proportion of triplets whose majority is correct is hypergeometric:

`P(correct | k) = [ C(k,2)·C(5−k,1) + C(k,3) ] / 10`

| k | 0 | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- | --- |
| `P(correct)` | 0 | 0 | 0.3 | 0.7 | 1.0 | 1.0 |

The estimator is the mean of `1 − P(correct | k)` over cases. This is majority-of-3 drawn
without replacement from the five purchased draws. The with-replacement analogue
(binomial plug-in, `k/5` as the per-draw success probability) is declared **secondary**
and reported as a sensitivity only; it targets a slightly different policy and may not be
substituted if it looks better.

**An identity precommitted so that neither result can be spun.** Majority-of-3 and
majority-of-5 differ by exactly `0.3·[P(k=3) − P(k=2)]`. Majority-of-3 has the lower
error rate **if and only if** the 2/5 bucket is more populated than the 3/5 bucket.
Whichever way it falls, it is one comparison of two bucket frequencies and will be
reported as such rather than as a finding about aggregation.

**(c) Majority-of-5.** Correct iff `k ≥ 3`. No tie rule is needed; R is odd, and that is
why R is odd.

**(d) Sequential stopping — first verdict to reach 3.** Draw until one verdict has
occurred three times, then stop. This terminates at 3, 4 or 5 draws and **its verdict is
identical to majority-of-5 on every case, by construction**. It is therefore declared as a
**cost estimand, not an error estimand**: its error rate is majority-of-5's and will not
be reported as an independent improvement.

Ordering is predeclared two ways, both reported:

1. **As collected.** Each draw is written with a `repetition_index` of 0–4 assigned at
   collection time and never reassigned. The as-collected order is the single realisation
   that actually happened and is reported first.
2. **Order-free.** The exact mean over all distinct arrangements of the five draws,
   enumerated exhaustively (at most ten per case). This removes any possibility that
   reordering could improve the stopping statistic, because every order is used.

Reordering observations to improve stopping behaviour is prohibited; the order-free
estimator exists so that the temptation has no purchase.

**Reported for every policy, per direction:**

| quantity | definition |
| --- | --- |
| error rate | with Wilson interval |
| mean calls | per case |
| p50 / p95 calls | per case |
| total calls | over the corpus |
| measured API cost | summed from the per-call costs of A1.5, never from a price list |
| measured wall-clock latency | mean and p95, per case |

For the symmetric estimators (b) and (d)-order-free, cost and latency are the case's
measured per-call mean times the expected call count, which is stated in the table
footnote rather than left for a reader to reconstruct.

## A1.3 Error-direction stratification is not optional

Every primary outcome in A1.2 is reported separately for **missed failures** (reference
label = failure) and **false alarms** (reference label = success).

> **No pooled "repetition improvement" headline may be emitted without both directional
> figures presented adjacent to it in the same table or sentence.**

The stratification is on the **reference label**, which is fixed and known, not on the
majority verdict. §2 stratified on the majority verdict; that is a property of the
outcome being measured and would make the strata themselves a function of the result.
This is a correction to §2 and is recorded as one.

## A1.4 Secondary estimands

`P(at least one draw correct | at least one draw wrong)` is **retained and demoted to a
secondary stochasticity statistic.** It is a valid description of within-case variability
and an oracle ceiling. It may not be called "recoverable error", "recoverable by
repetition", or anything of that form unless an executable policy from A1.2 is named in
the same sentence.

Also reported, per stratum:

- fraction of cases with **any** within-case variation (`1 ≤ k ≤ 4`);
- fraction at `k = 0`;
- fraction at `k = 5`;
- fraction majority-wrong but variable (`k ∈ {1, 2}`);
- fraction majority-correct but variable (`k ∈ {3, 4}`).

The last two are the buckets where a repetition policy's behaviour is actually decided,
and the A1.2(b) identity is read directly off them.

## A1.5 Cost and latency are measured outputs, and the only ones this repository has

Latency is `UNMEASURED` for every source in `data/REAL_arb_*`, and cost is a March 2025
figure for a different endpoint. **The historical AgentRewardBench costs may not be used
for this study, for any purpose other than the order-of-magnitude sanity check in §1.**

Captured per call, written at collection time, never reconstructed:

- model identifier and dated version string, as returned by the provider
- prompt identifier, version, and a hash of the exact rendered prompt
- request timestamp
- prompt tokens and completion tokens
- per-call API cost in USD
- wall-clock latency
- provider-side cache indicators, if the provider reports them

Aggregated per case: total cost, total tokens, total wall-clock. Recorded per run:
failures, retries and timeouts, with the transport/verdict distinction of A1.7.

Provider-side prompt caching is a live threat to this study specifically: five near-identical
requests for the same case are exactly the pattern a cache serves, and a cached completion
is not an independent draw. If the provider reports cache hits, they are recorded and the
affected cases flagged. If cache control is available, caching is disabled and that is
recorded in the run header.

The three cost states of `docs/agent_reward_bench_findings.md` remain distinct: measured
USD, structurally absent, and unpriced-because-self-hosted. This study should produce only
the first, and any call that produces another is an anomaly to be reported, not smoothed.

## A1.6 Repetition stability against cross-evaluator stability — neutral names only

The 2×2 join to `data/REAL_arb_directional.csv` on `case_id` is retained from §2. The
category names are fixed here, and only these names may be used:

| axis | categories |
| --- | --- |
| cross-evaluator | **cross-evaluator unresolved** / **cross-evaluator recovered** |
| repetition | **repetition-consistent wrong over R = 5** / **repetition-variable** |

Cases wrong under the primary and unresolved by all eight cached alternates *and*
repetition-consistent over five draws are to be called **shared unresolved errors** —
and nothing else — until they have been individually inspected. They are not
"irreducible", not "genuinely hard", not "ground-truth errors", and not "a floor". Each
of those is a hypothesis about a cause, and the count is not evidence for any of them.

> **The study may discover relationships among these four categories. It must not assume
> them.** In particular, it may not be assumed that repetition-consistent errors are
> disproportionately cross-evaluator unresolved. That is the interesting cell and
> therefore the one most at risk of being asserted.

The comparison also carries a standing confound, stated now: the eight cached alternates
were run once each at temperature 0.0 on a March 2025 endpoint, and this study runs one
judge five times at its deployed configuration on a different endpoint. Agreement across
eight judges is not the same object as agreement across five draws of one, and the join
is a descriptive cross-tabulation, not a decomposition of error into two sources.

## A1.7 Execution safeguards

1. **Incremental checkpointing.** Every completed call is written to durable storage
   before the next is issued.
2. **Resumable without duplicating paid calls.** Resume is keyed on `(case_id,
   repetition_index)`; an existing record is never re-purchased.
3. **Raw responses retained** verbatim, alongside the parsed verdict, for every call.
4. **Unique identity per draw.** `(case_id, repetition_index)` is unique and append-only.
   No record is ever overwritten. A correction is a new record with the reason.
5. **Transport failure is not a verdict.** Network errors, rate limits, timeouts and
   malformed responses are recorded as transport events with their own identity.
   **Retries for transport failure do not count as independent judge repetitions** and do
   not consume a `repetition_index`. A case reaches five *verdicts* or it is reported as
   incomplete; it is never topped up from a retry.
6. **No peeking.** All 1,106 × 5 verdicts are collected before any statistic in A1.2 or
   A1.4 is computed. Partial aggregate results are not inspected, and the study is not
   altered mid-collection. Monitoring is restricted to call counts, spend, and transport
   error rates — quantities that cannot reveal the result.

## A1.8 Post-collection analysis, in order

1. Run header: model version, prompt hash, sampling configuration, dates, and the
   pre-inference commit hash.
2. Completeness: cases with five verdicts, cases short, transport events, spend.
3. Cache-hit audit per A1.5.
4. The six-bucket `k` distribution, per stratum.
5. Single-draw error rate, per stratum, with interval.
6. Majority-of-3 (symmetric), per stratum, with interval.
7. Majority-of-5, per stratum, with interval.
8. The A1.2(b) identity: `P(k=2)` against `P(k=3)`, per stratum.
9. Sequential stopping: call distribution as-collected and order-free; verdict identity
   with majority-of-5 verified programmatically, not asserted.
10. Cost and latency table per policy per stratum, from measured values only.
11. Secondary statistics of A1.4, including the demoted §2 estimand.
12. The A1.6 cross-tabulation, with the confound restated in the same section.
13. Outcome classification per A1.9, and the corrections section.

## A1.9 Outcomes, precommitted

The classification variable is the **absolute reduction in error rate from single draw
(A1.2a) to majority-of-5 (A1.2c), computed separately per stratum**, as a fraction of the
single-draw error rate in that stratum. Bands:

| band | reduction | and |
| --- | --- | --- |
| **substantial** | ≥ 1/3 | Wilson interval on the paired difference excludes 0 |
| **slight** | ≥ 1/10 | anything else |
| **negligible** | < 1/10 | — |

These bands are **descriptive and decide nothing.** They are not `r*`. No `r*` is declared
by this study and none will be inferred from it; absent a declared `r*` the planner's
correct output remains `NOT DECISION-SUFFICIENT`. The bands exist only so that the outcome
label cannot be chosen after the numbers are known.

| outcome | fires when | consequence |
| --- | --- | --- |
| **A** | missed-failure reduction is **substantial** | repetition is a real lever on the stratum that matters; the escalation architecture must be justified against it, not against doing nothing |
| **B** | false-alarm and missed-failure bands **differ** | the two error directions have different stability; the planner's single replication count is the wrong control, and a directional repetition budget is something nothing in the codebase currently expresses |
| **C** | both directions **negligible** | repetition does not deliver assurance here; combined with `conditional.md` §6, both of the project's levers are measured and weak, which is a finding and not a failure |
| **D** | missed-failure reduction is **substantial or slight** but sequential stopping does not bring mean calls below 4 | the correction exists and is not cheap; the economics move to the foreground and the cost model needs the measured numbers this study produces |
| **E** | the shared-unresolved-errors cell exceeds half the missed-failure errors that are repetition-consistent | a floor exists that neither lever clears; the honest planner output on such cases is an admission, and the residual-error model needs a term for it |
| **F** | fewer than 1,050 cases reach five verdicts, or a cache-hit rate above 5% is detected, or the `aer` prompt could not be reproduced | insufficient evidence; report what was collected and what failed, and draw no conclusion about repetition |

A and B and D are not mutually exclusive and may fire together; C excludes A; F excludes
all others and is checked first. Nothing here is a threshold for a decision — each is a
threshold for which paragraph gets written.

## A1.10 The gate before any money is spent

1. This amendment is committed. The working tree is clean. **The commit hash immediately
   preceding inference is reported to the user and written into the run header.**
2. `aer` reproducibility is verified against `scripts/arb_extract.py`: the prompt text, the
   parse rule, and the label polarity (`reference_label` True = failure present;
   `outcomes` True = evaluator flagged failure), checked by re-deriving a cached verdict
   from a cached raw response.
3. The model endpoint and its dated version string are confirmed available and recorded.
4. Credentials and spend limits are confirmed against the ≈$58 order of magnitude from §1.

> **If reproducing `aer` exactly is impossible, no other judge is substituted. The run
> stops and reports what could not be reproduced.** A modern reimplementation of the same
> prompt against a different backbone is a different evaluator and therefore a different
> study, and would need its own predeclaration rather than inheriting this one.

## A1.11 The question, restated

> **When the judge is wrong, how often is that error actually removable by purchasing
> additional samples, and what does that correction cost?**

And the two sentences that this amendment exists to enforce:

> **Observed variability is not the same thing as recoverability. Observed consistency is
> not the same thing as correctness.**
