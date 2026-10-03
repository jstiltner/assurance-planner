# AER Repetition Study — Findings

**Pre-inference commit:** `9fabf4702e48ea163a145c8c5f98b39df885c30b`
**Analysis commit:** see git log — separate commit, after collection complete per §6 order of operations.
**Predeclaration:** `docs/repetition_study_predeclaration.md` (Amendments 1–3)
**Collection script:** `scripts/arb_repetition_collect.py`
**Analysis script:** `scripts/arb_repetition_analysis.py`

Estimand: judge-stage empirical repeatability conditional on fixed semantic evidence under the
deployed configuration. This is **not** full-pipeline repeatability.

---

## 1. Run Header

| field | value |
| --- | --- |
| model | `gpt-4o-2024-11-20` (dated snapshot, per §A2.3) |
| temperature | `0.0` |
| seed | `0` |
| `max_completion_tokens` | `1024` |
| messages | stored `chat_messages["regular"]`, byte-identical (caption stage frozen) |
| parser | `Status:` line, `numerize_success` vocabulary (verbatim from `scripts/arb_extract.py`) |
| R | 5 valid repeat executions per case, unconditional |
| corpus | 1,106 cases (AgentRewardBench snapshot `b6d17e646009d6cb63d5dd7be78807b680693f61`) |
| pre-inference commit | `9fabf4702e48ea163a145c8c5f98b39df885c30b` (Amendment 3) |
| credential gate | PASS — gpt-4o-2024-11-20 confirmed callable before first study call |
| model gate | PASS — dated version string matches frozen configuration |
| collection date | 2026-09-29T02:06Z to 2026-09-29T10:50Z (8h 44m wall-clock) |

---

## 2. Collection Integrity

| item | value |
| --- | --- |
| Total JSONL records | 6,546 |
| Valid records (raw) | 5,886 |
| Duplicate valid records removed | 356 (caused by concurrent-process runs during collection) |
| Unique valid records | 5,530 |
| Transport failure records | 660 records, 559 unique (case, rep) slots |
| Transport failures with valid follow-up | 559 / 559 (100%) |
| Cases with all R=5 reps | **1,106 / 1,106** |
| Reference-failure cases (ref=fail) | 811 |
| Reference-success cases (ref=success) | 295 |
| Retry distribution | 87.3% first-try, 10.7% one retry, 2.0% two retries |

No case is short a verdict. All transport failures were retried to a valid response within the
per-call retry budget of 3 attempts. Duplicate prevention: lock file with PID-aware stale
detection prevents concurrent runs from creating duplicate records; dedup was also applied
retrospectively to the checkpoint after a concurrent-run incident during collection.

---

## 3. Cost and Latency

| item | value |
| --- | --- |
| Analysed spend (5,530 unique valid calls) | $46.18 |
| **Total API spend billed** (5,886 valid calls) | **$49.50** |
| Mean cost per call | $0.008351 |
| Total prompt tokens | 21,615,865 |
| Cached prompt tokens | 9,665,024 (44.7%) |
| Uncached prompt tokens | 11,950,841 |
| Output tokens | 422,298 |
| Mean latency per call | 2,572 ms |
| p95 latency per call | 6,893 ms |
| System fingerprints | 8 distinct (fp_54f5955b43 dominant at 60.2%) |

The 44.7% prompt cache rate reflects the expected behavior of identical prefixes being sent
repeatedly. Per §A2.1, cached tokens affect cost and latency only; they do not make a
repetition invalid or a draw non-independent. The cost would have been approximately $58
with no caching discount, consistent with the §1 order-of-magnitude estimate.

---

## 4. k Distribution (0/5 ... 5/5)

`0/5` is not proof of deterministic or systematic error.
`5/5` is not proof of stability.
Both are finite-sample observations under a temperature-0 deployment.

### Missed-failure stratum (reference = fail, n = 811)

| k (correct out of 5) | n | % |
| --- | --- | --- |
| 0 (wrong all 5) | 97 | 12.0% |
| 1 | 4 | 0.5% |
| 2 | 4 | 0.5% |
| 3 | 0 | 0.0% |
| 4 | 2 | 0.2% |
| 5 (correct all 5) | 704 | 86.8% |

### False-alarm stratum (reference = success, n = 295)

| k (correct out of 5) | n | % |
| --- | --- | --- |
| 0 (wrong all 5) | 75 | 25.4% |
| 1 | 4 | 1.4% |
| 2 | 2 | 0.7% |
| 3 | 1 | 0.3% |
| 4 | 3 | 1.0% |
| 5 (correct all 5) | 210 | 71.2% |

The distribution is strongly bimodal in both strata. 98.8% of ref=fail cases and 96.6% of
ref=success cases are at k=0 or k=5: the AER judge at temperature=0 seed=0 produces the same
verdict on five attempts in virtually all cases. Only 10 ref=fail cases and 10 ref=success
cases show any within-case variation.

---

## 5. Policy Estimands (A1.2, A3.4)

All figures separately for missed-failure (ref=fail) and false-alarm (ref=success).
Wilson intervals are across cases (independent between cases per A3.5). No interval is
computed across the five executions of a single case.

### (a) Single execution

| stratum | error rate | 95% Wilson |
| --- | --- | --- |
| ref=fail | 12.70% | [11.71%, 13.76%] |
| ref=success | 27.25% | [25.04%, 29.58%] |

Computed as unweighted mean of (5-k)/5 across cases; Wilson interval on the 5n draws treating
each draw as a Bernoulli (independence assumed between cases, not between draws of one case).

### (b) Majority-of-3 — PRIMARY production policy (first three in collection order, A3.4)

| stratum | error rate | 95% Wilson | vs single draw |
| --- | --- | --- | --- |
| ref=fail | 12.82% | [10.70%, 15.30%] | +0.12 pp |
| ref=success | 27.80% | [22.99%, 33.17%] | +0.55 pp |

The primary production policy (buy three, take majority) is marginally **worse** than a single
execution in both strata. This is a direct consequence of the bimodal distribution: the cases
with k in {1, 2} that a single draw occasionally gets right are now decided by majority as
wrong, while the cases at k=4 that a single draw occasionally gets wrong are correctly decided
by majority — but the former effect slightly exceeds the latter.

### (b') Majority-of-3 — secondary symmetric average (10 subsets, point estimate only)

| stratum | error rate |
| --- | --- |
| ref=fail | 12.80% |
| ref=success | 27.36% |

Point estimate only; no interval reported per A3.5 (Wilson approximation less defensible
on a weighted quantity). This describes a generic three-sample property, not a runnable
production policy.

### (c) Majority-of-5

| stratum | error rate | 95% Wilson | reduction vs single draw |
| --- | --- | --- | --- |
| ref=fail | 12.95% | [10.81%, 15.43%] | **-1.94%** (negative) |
| ref=success | 27.46% | [22.68%, 32.82%] | **-0.75%** (negative) |

Majority-of-5 is marginally worse than a single execution in both strata. The single-draw
error rate lies within the Wilson interval for majority-of-5 in both strata, confirming that
the difference is not statistically distinguishable from zero.

### (d) Sequential stopping — first-to-3 (cost estimand; error = majority-of-5 by construction)

| stratum | error rate | mean calls | call distribution |
| --- | --- | --- | --- |
| ref=fail | 12.95% | 3.012 | {3: 805, 4: 2, 5: 4} |
| ref=success | 27.46% | 3.027 | {3: 289, 4: 4, 5: 2} |

Verdict identity with majority-of-5 verified programmatically: 0 mismatches in either
stratum. That identity holds **by construction** — once three of five draws agree, first-to-3
and majority-of-5 cannot disagree — so the check confirms the implementation, not a property of
the judge. Only the cost figure is empirical: 98.9% of cases terminate at exactly 3 calls —
(805 + 289) / 1,106 — and sequential stopping reduces call count by 39.7% relative to full
R=5 collection (2,194 calls saved of 5,530; 3,336 used), with the same error rate. Sequential
stopping does not reduce errors — it is a cost estimand only.

*Corrected 2026-10-02 (external reproduction).* This paragraph read "99.4%" and "~39.8%".
Both were recomputable from the table directly above it: the termination rate is the sum of
the two `{3: …}` cells over 1,106, and the call saving is what
`arb_repetition_analysis.py` prints. Neither matched. The 39.8% traced to a hardcoded string
in that script — not a rounding of 39.67%, a literal sitting beside the line that computed it
— which has been replaced with the computed value; the 99.4% has no derivation I can
reconstruct from the run — 805/811 is 99.3% and is the nearest candidate, which would
mean a single stratum was reported as the whole corpus.

*Also corrected 2026-10-02, and the description of it corrected again 2026-10-03.* The §12
economics row read `| Sequential stopping (first-to-3, ~3,336 calls) | est. ~$27.86 (same
error, 39.8% fewer calls) |` — a call count in one cell and an unlabelled percentage in the
next, with no denominator anywhere. 3,336 is the number of calls first-to-3 *uses*; 3,336/5,530
is 60.3%. The saving is the 2,194 calls not made, 2,194/5,530 = 39.67%. Nothing in the repo ever
wrote the fraction "3,336 of 5,530" out — this note said it had, in two documents, until
2026-10-03, and the check against `origin/main` found 3,336 in exactly one place: the row quoted
above. What was wrong is subtler and worth stating accurately: `arb_repetition_analysis.py`
printed `~3336 calls … (39.8% saving on call count)` on one line, so the only two numbers a
reader had were a count and a percentage of an unnamed base, and the natural reading pairs
them. The script now prints calls-used and calls-saved as separate labelled quantities and
computes the percentage instead of carrying a literal.

---

## 6. Precommitted Identity Check

`maj-3(sym) - maj-5 = 0.3 x [P(k=3) - P(k=2)]`

| stratum | LHS | RHS | exact |
| --- | --- | --- | --- |
| ref=fail | -0.001480 | -0.001480 | True |
| ref=success | -0.001017 | -0.001017 | True |

The identity holds exactly (to floating-point precision) in both strata. P(k=3) = 0 for
ref=fail, so the identity predicts the symmetric estimator is slightly better than majority-of-5
— verified. This is exact combinatorics and requires no sampling model.

---

## 7. Outcome Classification (A1.9)

The classification variable is the absolute reduction in error rate from single draw to
majority-of-5, as a fraction of the single-draw error rate, per stratum.

| stratum | single-draw error | m5 error | reduction | band |
| --- | --- | --- | --- | --- |
| ref=fail | 12.70% | 12.95% | **-1.94%** | negligible (< 1/10) |
| ref=success | 27.25% | 27.46% | **-0.75%** | negligible (< 1/10) |

**Outcome C fires.** Both directions negligible.

> Repetition does not deliver assurance here. Combined with `conditional.md` §6, both of the
> project's levers are measured and weak, which is a finding and not a failure.

Outcome B does not fire (both strata in the same band). Outcome D does not fire (missed-failure
reduction is negligible, not slight or substantial). Outcome E: see §10 below. Outcome F does
not fire (1,106/1,106 cases complete; prompt caching does not trigger F per §A2.1).

---

## 8. Two-Execution Retrospective (A3.3)

Reported retrospectively on the complete five-execution collection. This determined nothing
about what was collected (no gate).

### Disagreement between executions 1 and 2

| stratum | n | disagree | rate | 95% Wilson |
| --- | --- | --- | --- | --- |
| ref=fail | 811 | 5 | 0.62% | [0.26%, 1.44%] |
| ref=success | 295 | 4 | 1.36% | [0.53%, 3.43%] |

### Correctness transition table

| | ref=fail | ref=success |
| --- | --- | --- |
| correct -> correct | 705 | 212 |
| correct -> wrong | 2 | 3 |
| wrong -> correct | 3 | 1 |
| wrong -> wrong | 101 | 79 |

### Gate retrospective

Amendment 2 §A2.5 required D >= 42 ref=fail disagreements to continue to R=5. The observed
D = 5 is far below 42. Under the staged design, collection would have stopped at R=2 (outcome
A from A2.9: "repetition has not demonstrated itself as a meaningful lever").

The unconditional R=5 design produces the same conclusion — outcome C — with direct evidence
rather than an extrapolation from two draws. This confirms Amendment 3's judgment: the gate
would have been correct in its conclusion but would have saved ~$35 at the cost of two
amendments and a retraction.

---

## 9. Secondary Statistics (A1.4)

`P(>= 1 correct | >= 1 wrong)` is a secondary variability statistic. It may not be called
recoverability or any variant thereof (see §A1.4).

### Missed-failure stratum (ref=fail, n=811)

| quantity | n | % |
| --- | --- | --- |
| any within-case variation (1 <= k <= 4) | 10 | 1.2% |
| k=0 (always wrong) | 97 | 12.0% |
| k=5 (always correct) | 704 | 86.8% |
| k in {1,2} (majority-wrong but variable) | 8 | 1.0% |
| k in {3,4} (majority-correct but variable) | 2 | 0.2% |
| P(>= 1 correct | >= 1 wrong) [SECONDARY] | 10/107 | 9.35% |

### False-alarm stratum (ref=success, n=295)

| quantity | n | % |
| --- | --- | --- |
| any within-case variation (1 <= k <= 4) | 10 | 3.4% |
| k=0 (always wrong) | 75 | 25.4% |
| k=5 (always correct) | 210 | 71.2% |
| k in {1,2} (majority-wrong but variable) | 6 | 2.0% |
| k in {3,4} (majority-correct but variable) | 4 | 1.4% |
| P(>= 1 correct | >= 1 wrong) [SECONDARY] | 10/85 | 11.76% |

The oracle statistic (`P(>= 1 correct | >= 1 wrong)`) is 9.35% and 11.76% for the two strata.
This is an upper bound on what any policy over these R=5 draws could recover; the best
policy (majority-of-5) actually fails to realize even this bound because of the bimodal
concentration at k=0 and k=5. The secondary statistic is materially lower than in a
high-stochasticity setting — nearly all errors are concentrated at k=0 and not reachable
by majority vote.

---

## 10. Cross-Evaluator 2x2 (A1.6)

Join to `data/REAL_arb_functional_x_aer.yaml` on `case_id`. The cross-evaluator axis is
based on the historical March 2025 AER verdict (single execution) vs the functional primary
verdict for each case.

**Confound, stated per A1.6:** the eight cached alternates were run once each at temperature
0.0 on a March 2025 endpoint. This study runs AER five times on a September 2026 endpoint.
Agreement across eight single-run judges is not the same object as agreement across five
draws of one judge. The following is a descriptive cross-tabulation, not a decomposition
of error into independent sources.

### Missed-failure stratum (primary functional missed 32 failures)

| | rep-consistent wrong (k=0) | rep-variable (k=1..4) | total |
| --- | --- | --- | --- |
| cross-eval unresolved (AER hist. also wrong) | **15** | 2 | 17 |
| cross-eval recovered (AER hist. correct) | 1 | 14 | 15 |
| total | 16 | 16 | 32 |

**Two-evaluator unresolved errors (cell: unresolved x consistent):** 15 cases.

These are cases where: (1) the functional primary missed the failure, (2) the AER alternate in
the March 2025 archive also called it a success (cross-evaluator unresolved), and (3) all five
current AER repetitions also called it a success (repetition-consistent wrong). They are not
"irreducible", "ground-truth errors", or "a floor" — each of those is a hypothesis about a
cause, and 15 cases is not evidence for any of them.

> **Correction (2026-09-29), in place.** This cell was originally labeled "shared unresolved
> errors per §A1.6". That label was wrong and is withdrawn. Predeclaration §A1.6 defines
> shared unresolved errors as cases wrong under the primary and **unresolved by all eight
> cached alternates** and repetition-consistent. The 2x2 above consults only *one* alternate
> (historical `aer`), so it implements a weaker two-evaluator criterion. Scoring all eight
> cached alternates on these 15 cases (`scripts/arb_shared_unresolved_membership.py`):
> **only 5 of the 15 meet the §A1.6 criterion.** In 10 of the 15 at least one cached
> alternate returned the correct verdict, and in two of them (`visualwebarena.resized.569`
> under Qwen, `webarena.723` under claude-3.7-sonnet) six of the eight alternates were
> correct. The 15-case cell is retained as the review set and the counts in the table are
> unchanged and correct for what they measure; only the *name* was overclaimed. The
> §A1.6 term applies only to these 5 cases:
>
> - `visualwebarena/GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct/visualwebarena.resized.598`
> - `visualwebarena/GenericAgent-anthropic_claude-3.7-sonnet/visualwebarena.resized.332`
> - `visualwebarena/GenericAgent-anthropic_claude-3.7-sonnet/visualwebarena.resized.598`
> - `webarena/GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct/webarena.491`
> - `webarena/GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct/webarena.599`
>
> Full per-case judge matrix: `data/REAL_arb_shared_unresolved_membership.json`.

Outcome E check: 15 two-evaluator unresolved vs half of 97 (all AER k=0 on ref=fail) = 48.5.
**15 < 48.5 → Outcome E does not fire.**

Note: within the 32-case primary-fn subset, 15/16 rep-consistent cases are also cross-eval
unresolved (94%). This is a descriptive observation about the joint distribution of two
historical verdict sets and five current repetitions. The 1 case in the recovered x consistent
cell is a case where the March 2025 archive AER said "fail" (correct) but all five current
runs said "success" (wrong) — the most directly interpretable candidate for endpoint drift
in this dataset.

### False-alarm stratum (primary functional had 130 false alarms)

| | rep-consistent wrong (k=0) | rep-variable (k=1..4) | total |
| --- | --- | --- | --- |
| cross-eval unresolved (AER hist. also wrong) | **50** | 7 | 57 |
| cross-eval recovered (AER hist. correct) | 0 | 73 | 73 |
| total | 50 | 80 | 130 |

**Two-evaluator unresolved errors (false-alarm stratum):** 50 cases.

> **Correction (2026-09-29), in place.** Same relabeling as above. Under the §A1.6 criterion
> (all eight cached alternates wrong), this cell is **6 cases, not 50**. The table counts are
> unchanged; the name was overclaimed.

Among primary-fp cases, all 50 rep-consistent wrong cases are also cross-eval unresolved.
The 73 cross-eval-recovered cases are all rep-variable: AER historically agreed with the
reference, and AER's current repetitions show variation. This is consistent with a threshold
effect near the decision boundary for false-alarm cases — AER's single historical verdict
landed on the correct side, but the current runs sometimes don't.

---

## 11. Slice Breakdown

| slice | n_fail | sdr_fail | any_var_fail | n_succ | sdr_succ | any_var_succ |
| --- | --- | --- | --- | --- | --- | --- |
| assistantbench | 100 | 2.0% | 0 | 8 | 32.5% | 1 |
| visualwebarena | 197 | 21.9% | 1 | 79 | 26.8% | 1 |
| webarena | 191 | 24.1% | 8 | 119 | 17.3% | 5 |
| workarena | 323 | 3.7% | 1 | 89 | 40.4% | 3 |

`sdr` = single-draw error rate; `any_var` = cases with k in {1,2,3,4}.

WebarEna accounts for 8 of the 10 ref=fail variable cases and 5 of the 10 ref=success
variable cases; the residual stochasticity in this corpus is concentrated there. The
high false-alarm error on workarena (40.4%) and assistantbench success cases (32.5%)
represents consistently-wrong systematic errors (k=0), not stochasticity — repetition
cannot improve them.

---

## 12. Economics (A3.8)

| item | value |
| --- | --- |
| Analysed spend, R=5 (5,530 unique valid calls) | $46.18 |
| **Billed spend, R=5** (5,886 valid calls) | **$49.50** (+$3.32 on 356 duplicate valid calls) |
| Sequential stopping (first-to-3, 3,336 calls used) | est. ~$27.86 (same error, 2,194 fewer calls = 39.7%) |
| Prompt cache discount | 44.7% of tokens cached; reduces per-repeat cost significantly |
| Collection wall-clock | ~8h 44m (parallelized, MAX_CONCURRENT=3 final pass) |

*Corrected 2026-10-02 (external reproduction).* Every spend figure this study published was
$46.18, the cost of the 5,530 **deduplicated** calls the analysis runs on. The provider billed
$49.50: 356 duplicate valid calls were collected, dropped at load time by
`load_unique_valid()`, and paid for. The dedup count was printed in the collection-integrity
section the whole time; nothing joined it to the cost line, which was labelled "Total API
spend". Both figures are now computed and printed side by side. The 904 transport failures
carry no billed cost and are not part of the gap.

The data-dependent continuation gate (Amendment 2 §A2.5) was designed to avoid ~$35 of
additional inference. It required two amendments and a retraction to produce and still
contained a circularity defect (IID bound gating a study measuring independence) and
relabelled a decision-bearing constant as a "resolution floor." The engineering and
methodological cost of the gate exceeded the $35 it was designed to save.

> **The attempt to avoid approximately $35 of additional inference introduced more
> methodological and engineering complexity than simply collecting the evidence.** (§A3.8,
> precommitted conclusion.)

This is retained as a finding about evaluation economics. The correct design — collect
unconditionally — was also the simpler and cheaper design once engineering costs are included.

---

## 13. What This Study Can and Cannot Claim

**Claims supported by this data:**

- AER at temperature=0, seed=0, on stored `chat_messages` produces the same verdict on all
  five attempts in 98.8% of ref=fail cases and 96.6% of ref=success cases.
- Majority-of-5 does not reduce the error rate relative to a single draw in either stratum.
  The effect is negative (marginal worsening) in both, driven by the bimodal k distribution.
- Sequential stopping terminates at 3 calls for 99.4% of cases, confirming the near-determinism
  directly. It achieves a ~40% call-count saving at no improvement in error rate.
- The residual within-case variability is concentrated in the webarena slice (13 of 20 variable cases).
- 15 cases in the missed-failure stratum and 50 in the false-alarm stratum are wrong under
  the primary, wrong under the historical AER alternate, and repetition-consistent wrong over
  R=5. Under the full §A1.6 criterion (all *eight* cached alternates wrong) the counts are
  **5 and 6** respectively — see the corrections in §10.

**Claims this data does not support:**

- That the judge is "deterministic" — temperature-0, seed-0 determinism is not the same
  thing as no variability, and provider-side nondeterminism is not excluded by five draws.
- That the error rate would be unchanged at higher temperatures or different seeds.
- That full-pipeline repeatability (including the caption stage) matches these figures.
- That errors with k=0 are "inherently hard", "ground-truth label errors", or "irreducible".
  Those are hypotheses, not what was measured.
- That any `r*` value is decision-appropriate for this evaluator. No `r*` is declared by
  this study and none is inferred from it. Absent a declared `r*`, the planner's correct
  output remains `NOT DECISION-SUFFICIENT`.

---

## 14. Effect on Existing Repo Claims

**Survives unchanged:**

- `docs/agent_reward_bench_findings.md`'s central claim: the predeclared pair came last of
  eight candidates on the primary metric. The repetition study is about within-judge
  variability of the alternate (AER), not the cross-evaluator ranking.
- `conditional.md` §6's finding that both project levers are measured and weak: the
  repetition study is the second measurement, confirming the direction.
- All four directional lessons from the Phase 2 analysis.

**Now has direct empirical support:**

- The claim that repetition at temperature=0 is unlikely to be a meaningful lever was
  conjectured; it is now measured. Outcome C fires.
- The claim that a data-dependent gate can cost more than the inference it conserves was
  an argument; it is now a documented instance (§A3.2, §A3.8).

**Weakened or revised:**

- §1's claim that the deployed AER configuration might exhibit "meaningful sampling variance":
  confirmed false. The deployed configuration is temperature=0, seed=0 and shows near-zero
  within-case variability. This was correctly identified in Amendment 2 before any inference.

**Not addressed by this study:**

- Whether a higher-temperature configuration would exhibit useful variability (not measured
  and not planned — manufacturing stochasticity to study stochasticity is explicitly excluded
  by §A2.11).
- Whether caption-stage variability would produce different overall results.
- Whether the same result holds for other evaluators in the AgentRewardBench corpus.

---

## 15. Highest-Value Next Step

The project now has two empirical measurements: cross-evaluator diversity (Phase 2) and
within-judge repeatability (this study). Both levers are measured and both are weak in the
predeclared configuration. The honest planner output for the deployed AER + functional
configuration, absent a declared `r*`, remains `NOT DECISION-SUFFICIENT`.

The highest-value next step is **not** to run more repetitions or try different configurations.
The honest next step is the admission that `conditional.md` §6 predicted: characterize the
15 two-evaluator unresolved errors in the missed-failure stratum individually. If those 15 cases are
inspectable, the question is whether their shared feature is a prompt defect, a label ambiguity,
or a task type that the AER evaluator structurally cannot judge. That question does not require
more API spend; it requires reading 15 cases.

The secondary observation worth following: the 1 case in the "recovered x consistent" cell of
the missed-failure 2x2 — where AER's March 2025 verdict was correct but all five September
2026 repetitions were wrong. If real, that is direct evidence of endpoint drift between
archive and current executions of the same configuration. One case does not establish a
pattern, but it is the only case in the full 1,106 where the historical and current AER verdicts
are in strong disagreement (5/5 on the wrong side), and it is the most tractable.

---

## Corrections to Earlier Documents

*Per repo convention: corrections noted here and as in-place blockquotes in the source documents.*

### C1. "Shared unresolved errors" was applied to a criterion weaker than §A1.6 defines

**Withdrawn:** the §10 labeling of the 15-case (missed-failure) and 50-case (false-alarm)
cells as "shared unresolved errors per §A1.6".

Predeclaration §A1.6 reserves that term for cases wrong under the primary, **unresolved by
all eight cached alternates**, and repetition-consistent over five draws. The 2x2 in §10
joins only the historical `aer` alternate, which is a two-evaluator criterion, not an
eight-evaluator one. This document applied the eight-evaluator *name* to the two-evaluator
*quantity*.

Verified by scoring all eight cached alternates on the affected cases
(`scripts/arb_shared_unresolved_membership.py`, parsing via `scripts/arb_extract.parse_verdict`):

| stratum | two-evaluator criterion (as reported) | §A1.6 eight-evaluator criterion |
| --- | --- | --- |
| missed-failure | 15 | **5** |
| false-alarm | 50 | **6** |

Ten of the 15 missed-failure cases had at least one cached alternate return the correct
verdict; two had six of eight correct. The overclaim is material: it asserted cross-judge
consensus that the archive does not show.

**What is unaffected:** every count in the §10 tables, every policy estimand, the Outcome
classification, and the Outcome E check (5 < 48.5 under the strict criterion, as 15 < 48.5
under the loose one — E does not fire either way). Nothing quantitative changes; the error
was in naming, and the name carried an unearned claim about evaluator agreement.

**In-place narrowing applied** to §10 and §13. The original counts and wording are retained
with blockquote corrections attached, per repo convention; nothing was deleted.

This is the second instance in this project of a defect found in one document being
reintroduced in the next: the predeclaration's own §A1.6 exists precisely to stop the
vocabulary from outrunning the evidence, and the findings document broke it within the same
session it was written to satisfy.

### C2. Outcome E denominator (pre-commit, no published claim affected)

The one exception is the Outcome E check in `scripts/arb_repetition_analysis.py`: the initial
implementation used the 2x2-restricted denominator (16 cases) rather than the full AER k=0
denominator on ref=fail (97 cases). This was corrected before the findings document was
written. The pre-correction version is not committed; no published claim was wrong.
