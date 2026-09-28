# AgentRewardBench: what the real paired evidence shows

The analysis the predeclaration in `docs/agent_reward_bench_gate1.md` committed us to.
That document was committed at `9fdaaf1`, the importer and the two run files at `594918f`,
and no statistic in this document was computed before either. Read the Gate 1 record
first: it fixes the population, the label rule, the polarity, and the pair choice, and it
lists what this corpus cannot answer.

Reproduce with:

```
python scripts/arb_extract.py && python scripts/arb_import.py --tier-c
python -m assurance_planner.cli characterize-alternate data/REAL_arb_functional_x_aer.yaml
```

No break-even recovery `r*` was supplied, because none has been declared for any real
deployment. **Everything below is descriptive.** The report says
`NOT DECISION-SUFFICIENT` on both arms and that is the correct reading, not a hedge.

## 1. Headline: the predeclaration cost us the flattering answer, and that is the point

> **Narrowed by `docs/agent_reward_bench_directional.md` §6.** This section is correct on
> pooled recovery and misleading as a summary. On the missed-failure stratum — the one the
> escalation story is about — the same predeclared pair is **tied first of the eight**, and
> post-hoc selection would have bought +0.216 of pooled recovery and *exactly zero* there.
> The table below is left as published.

Tier A was predeclared as `functional` → `aer` on independence and cost-measurability
grounds. Scored against the other seven `HIGH`-independence pairs — same primary, same
1,106 cases, same reference labels — it comes **last on every complementarity statistic**:

| alternate (primary = `functional`) | n | recovery | 95% Wilson | joint err | phi | disagree |
| --- | --- | --- | --- | --- | --- | --- |
| gpt-4o-mini (axtree) | 1105 | 0.759 | [0.688, 0.819] | 0.035 | +0.064 | 0.257 |
| qwen-2.5-vl (axtree) | 1106 | 0.759 | [0.688, 0.819] | 0.035 | +0.091 | 0.236 |
| gpt-4o-mini (neither) | 1106 | 0.716 | [0.642, 0.780] | 0.042 | +0.090 | 0.260 |
| nnetnav (llama-3.3-70b) | 1106 | 0.704 | [0.629, 0.769] | 0.043 | +0.048 | 0.306 |
| llama-3.3-70b (axtree) | 1106 | 0.667 | [0.591, 0.735] | 0.049 | +0.202 | 0.205 |
| claude-3.7-sonnet (axtree) | 1100 | 0.665 | [0.589, 0.733] | 0.049 | +0.218 | 0.196 |
| gpt-4o (axtree) | 1106 | 0.660 | [0.585, 0.729] | 0.050 | +0.236 | 0.188 |
| **`aer` — Tier A, predeclared** | **1106** | **0.543** | **[0.466, 0.618]** | **0.067** | **+0.323** | **0.179** |

Post-hoc selection would have produced recovery 0.759 with phi +0.064 — a pair whose
errors look nearly unassociated. Predeclaring produced 0.543 with phi +0.323. The gap
between those two numbers is the size of the bias that pair-shopping would have
introduced into a report that would otherwise have looked identical, written in the same
register, with the same intervals.

> **"Look nearly unassociated" was exactly the illusion.** Narrowed by
> `docs/agent_reward_bench_conditional.md` §6: conditional on the reference label, the
> post-hoc pair's missed-failure odds ratio is 5.08 against the predeclared pair's 9.38 —
> the same order of magnitude, neither near independence — while their pooled phis differ
> fivefold. The sentence stands as written because the pooled phi is what a post-hoc
> report would have quoted, which is the point being made.

**A provenance argument for independence failed its one within-tier prediction.** Gate 1
argued `aer` was the strongest alternate partly because its prompt is externally authored
(Pan et al. 2024) rather than sharing this paper's template. Measured error association
puts `aer` at the *most* correlated end of the eight. Whatever drives error overlap here,
prompt lineage is not it, and the a priori reasoning that picked Tier A is not supported by
the outcome it was used to predict. That is recorded as a miss, not reframed.

> **Narrowed, and this one cuts in Gate 1's favour.** "Most correlated end of the eight"
> is a pooled-phi statement. On the reference-failure stratum `aer` ranks **fourth of
> eight** by both phi and odds ratio (`conditional.md` §4). The correct narrower statement
> is that the provenance argument was *not supported* — it made no prediction that the
> conditional evidence confirms — rather than that it ranked backwards. Recorded here
> because the original sentence was harsher on the pre-outcome reasoning than the evidence
> now supports, and correcting only in the flattering direction is not a correction.

## 2. Tier A in full — `functional` → `aer`, n = 1,106

```
                            alternate correct   alternate wrong
  primary correct                     834               110
  primary wrong                        88                74
```

| statistic | value | 95% Wilson | n |
| --- | --- | --- | --- |
| P(alternate correct \| primary wrong) — recovery | 0.543 | [0.466, 0.618] | 162 |
| P(primary correct \| alternate wrong) | 0.598 | [0.526, 0.666] | 184 |
| joint error rate | 0.067 | [0.054, 0.083] | 1106 |
| primary errors also made by alternate | 0.457 | [0.382, 0.534] | 162 |
| alternate errors also made by primary | 0.402 | [0.334, 0.474] | 184 |
| verdict disagreement | 0.179 | [0.158, 0.203] | 1106 |
| error association (Pearson phi) | +0.323 | — (no p-value) | 1106 |

Marginals on the same paired cases, in failure polarity: primary sensitivity 0.961
[0.945, 0.972] with FPR 0.441 [0.385, 0.498]; alternate sensitivity 0.875 [0.851, 0.896]
with FPR 0.281 [0.233, 0.335].

Cost: alternate $0.0105/observation measured over 1,106 observations. Primary UNMEASURED —
and note the report cannot distinguish the primary's *structural* absence of cost (no
model call) from an unrecorded measurement. Latency UNMEASURED for both. These are the
inputs an escalation policy would need and two of the three are missing.

## 3. The qualification that matters more than the headline

Recovery pools two error types with opposite economic meaning, and on this corpus the
pooling is doing almost all the work. Decomposing the primary's 162 errors:

| | count | recovery within stratum |
| --- | --- | --- |
| primary **missed a real failure** (ref = failure, `functional` said pass) | **32** | 0.469 |
| primary **false-alarmed** (ref = success, `functional` said failure) | **130** | 0.562 |

**Eighty percent of the primary's errors are false alarms.** The assurance planner's
escalation story is about recovering *missed failures* — the residual error a plan must
bound is undetected failure, not over-flagging. On that stratum the denominator is 32
cases in the entire test split, and across all eight `HIGH` pairs recovery on it is:

| alternate | recovery on the 32 missed failures | recovery on the 130 false alarms |
| --- | --- | --- |

| gpt-4o-mini (axtree) | 0.469 | 0.831 |
| gpt-4o-mini (neither) | 0.469 | 0.777 |
| aer (Tier A) | 0.469 | 0.562 |
| gpt-4o (axtree) | 0.438 | 0.715 |
| llama-3.3-70b (axtree) | 0.438 | 0.723 |
| claude-3.7-sonnet (axtree) | 0.406 | 0.729 |
| qwen-2.5-vl (axtree) | 0.375 | 0.854 |
| nnetnav (llama-3.3-70b) | 0.281 | 0.808 |

(`claude-3.7-sonnet`'s false-alarm stratum is 129, not 130: one of its six unparseable
judgments falls there and is dropped rather than scored as wrong.)

Three things follow, and the third is the one that matters:

1. **No alternate recovers even half of the primary's missed failures.** The range is
   0.281–0.469 and every point estimate is below 0.5. The apparent spread in headline
   recovery (0.543–0.759) is almost entirely a spread in how well each alternate *clears
   false alarms*, which is a different product.
2. **The ranking reverses.** `nnetnav` is fourth-best on headline recovery and worst on
   missed failures. Ranking alternates by pooled recovery would pick a different judge
   than ranking them by the quantity the planner actually needs. *(Understated — narrowed
   by `docs/agent_reward_bench_directional.md` §13.2. The two rankings do not merely
   differ: the pooled ranking is a ranking on the false-alarm stratum, which supplies 80%
   of its denominator, and shares almost no information with the directional one.)*
3. **These are eight readings of the same 32 cases.** Same primary, same population, so
   the eight columns are not eight independent estimates and none of them gains
   credibility from the others agreeing. Nine successes out of 32 (`nnetnav`) to fifteen
   out of 32 (`gpt-4o-mini`) is a range that ~30 cases cannot separate.

The Gate 1 table certified "adequate paired support" on marginal error counts of 153–272,
all far above the 16-error presentation floor. That certification was right about the
statistic it was checking and **wrong about the study**: the binding denominator is not
the primary's error count, it is the primary's error count *of the type the decision turns
on*, and that is 32. Gate 1 should have had a column for it. The rule was applied
correctly to the wrong quantity, which is the failure mode a predeclaration protocol is
least able to catch.

## 4. Tier B — `aer` → `nnetnav`, n = 1,106, the stochastic arm

Tier A's primary is a deterministic verifier, so it cannot speak to the two-stochastic-judges
case at all. Tier B is the most independent stochastic pair available.

```
                            alternate correct   alternate wrong
  primary correct                     743               179
  primary wrong                        91                93
```

| statistic | value | 95% Wilson | n |
| --- | --- | --- | --- |
| recovery | 0.495 | [0.423, 0.566] | 184 |
| P(primary correct \| alternate wrong) | 0.658 | [0.600, 0.712] | 272 |
| joint error rate | 0.084 | [0.069, 0.102] | 1106 |
| verdict disagreement | 0.244 | [0.220, 0.270] | 1106 |
| error association (Pearson phi) | +0.269 | — | 1106 |

Cost is unrecoverable on this arm by construction — primary $0.0105/observation measured,
alternate UNMEASURED because it is vllm-hosted and records a literal 0.0. **No cost-aware
statement may be drawn from Tier B**, as Gate 1 stated in advance.

Two stochastic judges with different backbones *and* different prompt lineages still show
phi +0.269 and recover under half of each other's misses. Whatever "independent evaluator"
means operationally, it is not achieved by varying the model and the prompt author.

## 5. Per-slice behaviour, and why it is not a routing result

Tier A recovery by benchmark: `assistantbench` (0.70, n=10), `visualwebarena` 0.512
(n=41), `webarena` 0.681 (n=72), `workarena` 0.282 (n=39).

The `workarena`–`webarena` spread (0.282 vs 0.681) is the largest slice effect in either
arm and it is the shape a slice-keyed router would want to exploit. It must not be used
that way from here: these are descriptive, the denominators are 39 and 72, the
`assistantbench` figure rests on 10 errors and is parenthesised by the instrument for that
reason, and choosing a routing threshold on these numbers would fit the threshold on the
data it would later be scored on. Architecture §10.2 item 3 is the claim this bears on,
and it is not tested by it.

## 6. Which of the six permitted outcomes this is

> **Superseded for the Tier A arm by `docs/agent_reward_bench_directional.md` §11**, which
> lands on *insufficient evidence* once the recovery rate is split by error direction. The
> disposition below was correct on the evidence available to it and was computed on a
> pooled statistic that `directional` §12.1 identifies as the wrong conditional: recovery
> conditions on the reference label, and the rate a policy would actually run at is 20–30
> points lower. Left as written.

Of the six the brief allowed, this is closest to **"complementarity is real but weaker
than the marginals suggest, and the evidence is not decision-sufficient."** Precisely:

- Complementarity is **not zero**. The alternate is right on 54.3% of the primary's errors
  and the joint error rate (0.067) is well below the primary's own (0.146).
- It is **materially weaker than independence would give**. phi is +0.323, not ~0. A
  two-source system that multiplied 0.146 by 0.166 would predict a joint error rate of
  0.024 and observe 0.067 — nearly three times higher. That is the specific arithmetic the
  planner would launder if it assumed independence, and here it is measured, not argued.
  **Narrowed by `docs/agent_reward_bench_conditional.md`:** correct for this pair, and it
  must not be read comparatively. A pair with a *lower* pooled phi is not closer to
  independent — pooled phi is dominated by the reference-success stratum, which carries
  80% of this primary's errors. On the missed-failure stratum all eight alternates run at
  odds ratio 5.08–11.11 and are not distinguishable in this way.
- It is **not decision-sufficient**, and not because the sample is small. No `r*` has been
  declared, so there is no statement of what would change a decision. The Wilson interval
  [0.466, 0.618] is narrow enough to settle many questions and settles none that has been
  asked.
- The one quantity the planner most needs — recovery of missed failures — is
  **under-powered at n=32** and no pair's point estimate reaches 0.5.

It is *not* the "methodologically compromised" outcome. Labels are uncontaminated, the
label rule is upstream's own and reproduces upstream's published numbers exactly, and the
pair was fixed before the 2×2 was computed.

## 7. Stochasticity: what this cannot measure, and the study that would

**Explicitly: nothing in this document measures same-input stochastic noise.** Every
judgment is a single draw at `temperature: 0.0, seed: 0`. Both arms treat one draw as the
judge's verdict, so a judge that is merely noisy and one that is reliably different from
its partner are indistinguishable here. Between-case variation is not between-repeat
variation and no repeatability figure may be inferred from any table above. This matters
directly to the repository's own framing: the planner's replication machinery exists
because stochastic evaluators are unstable, and **this corpus contains no evidence about
that instability at all.**

A repetition study cannot be built by adding draws to this corpus. The judgments were
produced 2025-03-13 to 2025-03-18 against endpoints (`gpt-4o-2024-11-20`, a self-hosted
Llama-3.3-70B) that cannot be restored to that state, so fresh draws would be a different
judge and pooling them with these verdicts would manufacture variance out of version
drift. Any repetition study is a **new single-arm study**, not an extension.

### The smallest subset that would answer it

> **Superseded by `docs/repetition_study_predeclaration.md`.** The design below names
> Tier A's primary, which is a *deterministic* programmatic verifier and cannot be
> repeated at all — repeating it R times returns R identical verdicts by construction.
> The predeclared study runs on `aer` instead, at R = 5 rather than 3, over the full
> corpus rather than the 324-case subset. The cost conclusion in the last paragraph of
> this section survives unchanged and is the reason the subset was dropped.

No API calls were made for this. The design, and the binding constraint:

- **Stratify on the primary's error type, not just on benchmark.** The quantity whose
  stability actually matters is recovery on missed failures, so its denominator must be
  covered in full: **all 32 missed-failure cases**. This stratum cannot be subsampled —
  it is already the whole population of it in the test split, and it is the reason the
  study is design-limited rather than budget-limited.
- Add the **130 false-alarm cases** in full (cheap, and the stratum where the pooled
  recovery figure is actually determined), and a **benchmark-proportional random sample of
  162 of the 944 cases where the primary was correct**, which is what the joint error rate
  and phi need. Total **324 cases**.
- **R = 3 draws minimum**, which detects instability without pretending to estimate a flip
  rate; R = 5 if the question is the rate rather than its existence.
- Sample the non-error stratum **without reference to either judge's verdict**. An
  enriched-on-disagreement sample would find noise faster and could not be pooled for phi,
  for the reason in §9.3 of `docs/alternate_source_collection_protocol.md`.

At `aer`'s observed $0.0105/judgment, 324 cases × 3 draws ≈ **$10.20**, and re-running all
1,106 cases × 3 draws ≈ **$34.80**. Worth stating plainly: **the absence of repetition data
in this field is not a cost problem.** Thirty-five dollars would have answered it on this
corpus. The subset above is the smallest *representative* one; given the price, the honest
recommendation is to run the full 1,106 and not economise on a $25 difference.

The self-hosted judges are the exception — their cost is genuinely unknown, so no figure
like the above can be given for `nnetnav`, `llama-3.3-70b-noscreen` or
`qwen-2.5-vl-noscreen`, and none will be estimated.

## 8. What this does and does not license

It licenses: describing correlated evaluator errors on real agent trajectories with real
expert labels, with a measured phi, at a stated revision. It licenses the claim that
assuming evaluator independence overstates a two-source system's joint accuracy by
roughly threefold *on this population, for this pair*.

It does not license: any statement about stochastic judge repeatability; any cost-aware
escalation conclusion (two of three economic inputs are UNMEASURED); any routing policy
keyed on the slice table; any claim that a recovery rate clears or fails a threshold, since
no threshold has been declared; or any generalisation from a benchmark population with an
811/1,106 failure rate to deployment traffic.

## 9. Corrections to earlier documents

Three claims made before this pass. None is retracted outright; two are narrowed and one
is a gap in a list that let a stronger claim stand elsewhere.

**(1) "Nobody has these." — Narrowed.** `docs/architecture.md` §9 item 2 said no one holds
per-(source × failure-mode × population) sensitivity and FPR, and that the model "depends
entirely on an experiment nobody currently runs". AgentRewardBench ran a version of that
experiment: 15 evaluators against six human experts on 1,302 real agent trajectories, with
per-judgment cost. The narrowed concern is that it covers one failure mode, on benchmark
populations, with no latency, no cost for self-hosted judges, and single-shot judgments.
Applied in place at `docs/architecture.md` §9 item 2. The unrun experiment is the
**repetition** study (§7), not the qualification study, and that relocation is the
substantive part of the correction rather than a softening of it.

**(2) §10.1's prior-work list was missing two entries. — Corrected.** Evaluator
benchmarking against human reference labels with cost accounting, and paired significance
testing between two evaluators on the same cases (McNemar's test, which ATFD implements).
Their absence is what let (1) stand as wide as it did. Both added in place.

**(3) Gate 1's "adequate paired support" certification. — Narrowed, by this document.**
`docs/agent_reward_bench_gate1.md` §5 certified support from marginal error counts of
153–272 against a 16-error floor and concluded that support "did not select anything". The
check was correct and applied to the wrong quantity: the decision turns on recovery of
*missed failures*, whose denominator is 32, not 162 (§3). The Gate 1 table should carry a
column for the primary's error count broken down by error type. That predeclaration is
left as written — it is the record of what was decided in advance, and editing it now would
destroy the only thing it is for — and this is the correction that attaches to it.
