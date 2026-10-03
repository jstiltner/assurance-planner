# Findings

*Evaluator-assurance falsification study. Closed 2026-09-29.*

Evidence-class key used throughout:
**[PRE]** Preregistered · **[HO]** Held-out · **[FRESH]** Fresh corpus, read **label-blind**
until the freeze · **[EXP]** Exploratory · **[QUAL]** Qualitative, n=15 ·
**[ORA]** Oracle/benchmark-authoritative

> **Correction 2026-10-02.** `[FRESH]` was defined as ~~"fresh corpus, never touched"~~.
> That overstates the blinding. The τ-bench trajectory files **were** read during scoping,
> before the rule was frozen — record counts, task and trial ids, message roles and
> tool-call names (`required_conjunct_scoping.md` §8.4). What was withheld, and withheld
> *by code* rather than by discipline, was the `reward` and `info` fields, so no
> reference-conditioned quantity was visible until the freeze. "Label-blind" is the accurate
> word; "untouched" claims a stronger protocol than was run.

---

## 1. Scope

Two real corpora; no synthetic evidence enters any finding below.

| corpus | n | evidence quality |
|---|---|---|
| AgentRewardBench (rev `b6d17e6`) | 1,106 annotated agent trajectories | Preregistered pair selection; held-out rule validation |
| τ-bench (`historical_trajectories/`) | 1,980 trajectories, 165 tasks, 2 domains, 2 agents | Fresh corpus: never accessed before the RC1 preregistration commit |

Both corpora are class-A/fresh evidence for the claims below. The 25 documents of prior
analysis in `docs/` are the audit trail, not additional evidence.

---

## 2. Tier-1 findings

### T1.1 — Repeating this judge did not help **[PRE]**

| quantity | value |
|---|---|
| cases | 1,106 (811 reference-fail / 295 reference-success) |
| repetitions | R = 5 unconditional |
| calls / cost | 5,530 analysed / $46.18 — **$49.50 billed** across 5,886 valid calls (44.7% prompt-cache discount applied) |
| deployed config | `gpt-4o-2024-11-20`, temperature 0.0, seed 0 |
| cases with intermediate correctness (k = 1–4) | **20** of 1,106 |
| fraction at an extreme (k = 0 or k = 5) | 98.8% ref-fail · 96.6% ref-success |
| majority-of-3 vs single call | marginally *worse* in both error directions |
| majority-of-5 vs single call | marginally *worse* in both error directions |
| first-to-3 stopping vs majority-of-5 | **identical verdicts — by construction**, not a finding: first-to-3 is the same decision rule evaluated lazily. 39.7% fewer calls (2,194 saved of 5,530; 3,336 used), ≈$27.86 — the call saving is the only empirical part |

![Figure 1](figures/fig1_k_distribution.png)

**What this licenses:** for this deployed configuration, repeated execution had too little
useful variability for majority voting to pay. First-to-3 stopping recovered all available
savings without any voting benefit.

**What this does not license:** "LLM judges are deterministic" — provider-side nondeterminism
is not excluded by five draws, and temperature-0 is not the same as no variability.
Scope: one judge, one corpus, judge stage only.

![Figure 2](figures/fig2_policy_error_comparison.png)

---

### T1.2 — The attractive recovery statistic was not the deployable quantity **[EXP]**

| quantity | value |
|---|---|
| predeclared pair recovery `P(alt correct \| primary wrong)` | **0.543** [0.466, 0.618] |
| operational overturn-to-fail precision | **0.366** (15/41) |
| operational overturn-to-pass precision | **0.465** (73/157) |
| direction-matched reference-conditioned values | catch **0.469** (15/32) · rescue **0.562** (73/130) |
| gap: reference-conditioned vs operational, direction-matched | **10.3 pp** missed-failure · **9.7 pp** false-alarm |
| same gap across all 8 alternates | false-alarm side **+9.7 to +46.0 pp** (always positive) · missed-failure side **−14.7 to +23.1 pp** (negative for 2) |
| blanket adjudication on primary FAIL | 73 correct / 84 wrong = −11 net; raw-count loss for **5 of 8** pairs; non-positive for all 8 only if a missed failure is weighted ≥ **1.057×** a false alarm |

The reference-conditioned quantity `P(alt correct | primary wrong)` conditions on a
ground-truth label no runtime system has. A policy overturns verdicts based on what two
judges say, not on which one is right — which is why operational precision ran about 10
points lower in each direction on the same data.

**Corrected 2026-10-02 (external reproduction).** This table claimed a ~~"20–30 point"~~ gap and
~~"non-positive for all 8 pairs"~~. Both overstated:

1. The ~~20–30 points~~ came from subtracting the two *direction-specific* overturn precisions
   (0.366, 0.465) from 0.543, which is recovery *pooled* over both error directions. Matching
   directions, the gap is 10.3 pp and 9.7 pp. The finding holds; the magnitude was inflated by
   the same kind of pooling error the project documents elsewhere.
2. Splitting by direction also changes what the finding generalises to, and this is the more
   important half of the correction. The false-alarm-side gap is positive for every alternate.
   The missed-failure-side gap is *negative* for `gpt-4o-noscreen` (−8.1 pp) and
   `qwen-2.5-vl-noscreen` (−14.7 pp) — for those, the deployable quantity is **better** than
   the reference-conditioned one. "The operational number is always lower" is not true.
3. The net raw-count exchange is positive for `claude-3.7-sonnet-noscreen` (+4),
   `gpt-4o-noscreen` (+5) and `llama-3.3-70b-noscreen` (+1). ~~"Non-positive for all 8"~~ is a
   claim about an error-cost weighting that was never stated; the weighting it needs is
   ≥ 1.057×, which is defensible but belongs in the sentence.

Reproduce with `scripts/arb_directional.py` → `data/REAL_arb_directional.csv`.

Primary errors: 162 = **32 missed failures** + **130 false alarms**. The pooled metric was
dominated by the false-alarm stratum.

![Figure 4](figures/fig4_ref_vs_operational.png)

**Evidence class:** EXPLORATORY — the analysis of what the deployed policy would actually
do was conducted after outcomes were visible. The predeclared pair selection is class A.

---

### T1.3 — Predeclaration changed the reported result **[PRE vs B]**

| pair selection | pooled recovery | evidence class |
|---|---|---|
| Predeclared (5 pre-outcome criteria) | **0.543** | **[PRE]** |
| Post-hoc best — **tied**, `gpt-4o-mini` axtree *and* `qwen-2.5-vl`, both 123/162 | **0.759** | **[EXP]** oracle selection |

The predeclared pair ranked **last of eight** candidates on pooled recovery — a 21.6-point gap
in a report that would have read structurally identically either way. The same predeclared
pair ranks **tied first of eight** on missed-failure recovery (0.469), the operationally
relevant stratum. Both errors are visible only because the choice was locked before
outcomes.

*Corrected 2026-10-02 (external reproduction).* This row named `gpt-4o-mini` (axtree) as "the"
post-hoc best. There is no unique argmax: it and `qwen-2.5-vl` both score exactly 123/162. The
tie matters beyond pedantry, because the two are not interchangeable — their φ differ (+0.064
vs +0.091), so naming one silently selects which φ gets reported next to the 0.759. A document
arguing that post-hoc selection is a degree of freedom should not exercise an undisclosed one
while making the argument.

---

### T1.4 — Static obligation matching failed fresh-corpus validation; the construct was not empty **[PRE/FRESH + ORA]**

| gate / quantity | value | verdict |
|---|---|---|
| A1: firing volume | 25.3% (501/1,980) vs <15% ceiling | **FAIL** |
| A2: trajectory lift | 1.165× vs ≥1.50× bar | **FAIL** |
| A2: task-level gate (1.25×) | ceiling 1.222× < threshold | **INVALID — unpassable by construction** |
| A3: extractor precision (label-blind) | 28/30 — **25/27** strictly out-of-sample; precision only, recall unmeasured | **PASS** |
| Within-task lift, deployable outcome | 1.101× | — |

The task-level gate was mathematically unpassable: 81.8% of tasks held a failing trial,
capping any any-fail indicator at 1.222× — below the 1.25× threshold. It is
non-decision-bearing and not treated as a failure gate.

**The construct diagnostic (oracle only, class D):**

| rule | tasks | within-task lift [95% CI] | MH, stratified by task [95% CI] | evidence class |
|---|---|---|---|---|
| Oracle construct (benchmark-authoritative actions) | 94 | **2.339×** [1.927, 2.927] | **2.054×** [1.752, 2.530] | **[ORA]** — undeployable |
| Null rule (no successful write; no model) | 80 | 1.171× [0.802, 1.652] | 1.237× [0.904, 1.650] | **[EXP]** — exploratory, preregistered as disqualified |
| RC1 (production detector) | 109 | **1.101×** [0.903, 1.360] | **1.150×** [0.979, 1.352] | **[PRE/FRESH]** |

Intervals are task-level cluster bootstraps (2,000 resamples) — trials within a task are
repeated measures, so an interval assuming independence within strata is too narrow.

The target construct contained real signal that RC1 failed to recover. The oracle
establishes that the latent construct carries signal; it does not establish that a
production-valid representation of it exists. RC1 **did not outperform** a null rule
requiring no obligation model, and that is the whole of what the comparison shows: paired
on the same task resamples, NULL − RC1 = **+0.078 [−0.327, +0.575]** — the mean of 2,000
paired differences, where differencing the two point estimates gives +0.070 — and neither rule
is distinguishable from 1. Only the oracle separates. The oracle is not a forecast; the null
rule fails the volume gate at 24.1% and was preregistered as disqualified before any
computation.

> **Correction applied 2026-10-02 (external reproduction).** This section previously read
> "RC1 also fell below a null baseline requiring no obligation model" and published the
> three lifts bare. Two defects: the three lifts are computed on **different task sets**
> (94 / 80 / 109, because the within-task filter keeps only tasks where a given rule both
> fires and does not), and the 1.171 > 1.101 ordering is far inside sampling error. The
> verdict of §"no successor is warranted" does not change — it never rested on the
> ordering — but the deficit claim is withdrawn. The superseded wording is quoted verbatim
> in the first sentence of this note rather than deleted.

![Figure 3](figures/fig3_lift_comparison.png)

---

## 3. Major negative results

**F1 — Repetition as a production recovery mechanism.** *Killed for this configuration.*
Scope: one judge (`aer`), temp 0.0 / seed 0, one corpus, judge stage only.

**F2 — Generic alternate-judge escalation.** *Heavily weakened.* Pooled recovery dominated
by the false-alarm stratum (130 of 162 errors). Operational overturn precision ~10 points
below the direction-matched reference-conditioned figure, and reliably so only on the
false-alarm side (see T1.2). Blanket FAIL adjudication is a raw-count loss for 5 of 8 pairs,
and non-positive for all 8 only at an error-cost weighting of ≥ 1.057×.

**F3 — Structural independence implies error independence.** *Not supported.* Eight
alternates ordered by pooled φ the same way as their own sensitivity; the a-priori
independence argument did not predict measured correlation.

**F4 — A generic deterministic pre-check architecture.** *Not supported at n=4.* R1 (fires when
the agent calls `report_infeasible` while asserting the task was completed): rejected as
evidence against success — 0.51× lift, inverted, and 17 of 27 firings are true successes. Had
it been given veto power it would have helped 6 and harmed 14; it never was. Its escalation
half survives, narrowly: 33.3% evaluator error on firings against 15.2% elsewhere, and is post
hoc. R4 (fires when the trajectory ends on a search-results page): the 1.20× enrichment for
reference-fail is real, but evaluator error is 16.1% on firings against 15.5% elsewhere, a
0.6-point difference (p = 0.89). R4 tells you about the agent, not the evaluation.

*Correction 2026-10-02 (external reproduction) — neither R1 nor R4 had a numeric gate.* §7 of
`repair_validation_preregistration.md` gives both of them firing enrichment against base rate
as a *direction* with no threshold: *"No accept/reject on accuracy, since they change no
verdict."* R1 fails that direction (0.51×, inverted — the no-information case §7 names). **R4
meets it** (1.20×), so R4's ~~REJECTED~~ label is post hoc: it rests on the evaluator-error
contrast, which §7 never made a criterion, and on application-specificity, which §9 declared in
advance. F4 is unaffected as a *finding* — two of the four rules are uninformative about the
evaluator and a third is underpowered — but the arithmetic behind it is now 3 gated + 2
directional, not 4 gated. See `research_synthesis.md` §3.3.3.

**F5 — Static required-conjunct/tool-class matching.** *Rejected cross-corpus.* RC1 failed
both binding gates on fresh τ-bench data while its extractor passed 28/30 — the rule, not
parsing, failed. *Two limits on that second clause, disclosed 2026-10-02:* three of the 28
passes (cases 02, 06, 16) are cases whose defects pass 1 of the same audit found and Commit A2
fixed, so strictly out-of-sample the figure is **25/27**; and A3 is a **precision** gate with
unmeasured recall — case 30 scores CORRECT while containing two missed obligations. Parsing is
exonerated against false positives, not against under-extraction.

---

## 4. The result that passed its test and then failed reproduction

**S4 — Evidence-gap escalation (R3): confounded with benchmark slice. [HO]**

R3 fires when the evaluator received a goal that references an image it cannot observe.
On the 1,260-case held-out arm it passed its preregistered test:

- Evaluator error: **25.6%** on R3-fired cases vs **14.4%** elsewhere (Fisher p = 0.0015)
- Fires on: 133 cases (10.6% of the validation arm)
- Already-correct escalations: **99 of 133**

This section called that the project's positive result until 2026-10-02, when an external
reproduction audit asked which benchmarks R3 fires in. The answer is one:

| benchmark | R3 fires | cases | judge error (R3 ignored) |
|---|---|---|---|
| visualwebarena | **133** | 290 | 22.4% |
| assistantbench | 0 | 128 | 3.9% |
| webarena | 0 | 373 | 19.8% |
| workarena | 0 | 468 | 11.1% |

The pooled comparison is therefore visualwebarena — the highest judge-error point estimate of
the four — against the other three. The gap over the next-highest is 2.6 points (22.4% vs
19.8% on webarena), which at n = 290 against n = 373 is a rank and not a separation; only
workarena and assistantbench are clearly lower. ~~"against three slices the judge finds
easier"~~: corrected 2026-10-03. Conditioned on slice it is **25.6% vs 19.7% (34/133 vs 31/157), Fisher p = 0.26** —
roughly half the separation, no longer significant. Of +11.2 pp pooled, +5.8 pp survives
conditioning and +5.4 pp is slice identity.
Reproduce: `python scripts/arb_r3_slice_check.py`.

Not a refutation. The residual runs in the predicted direction and the test is underpowered
at n=133 vs 157, so this is a rule left unproven, not one shown not to work. Settling it
needs a corpus where the evidence gap occurs outside a single benchmark.

**The disposition does not move; the reading does.** R3's preregistered disposition stays
ACCEPTED, because it met its criterion and the test ran as specified. Downgrading a
disposition after the fact on the strength of an analysis the preregistration never named
would be the same post-hoc move this document criticises elsewhere. What is withdrawn is what
the pass was taken to mean: R3 passed a test that, as specified, could not distinguish it from
a proxy for the highest-error environment, so it is no longer quotable as a positive result of
this study.

R3 remains an escalation signal rather than a corrector, and its value remains a function of
human review cost. Both were true before and are unaffected.

**Why this was missed.** The hazard was stated in one line — *"Any rule that escalates the
cases a judge finds hard will pass a test of the form 'is the judge worse on the escalated
subset'. That test is necessary, not sufficient, and the preregistration should have said so."*
That line is **not** in the preregistration, as this document previously said. It is a
post-results caveat in `repair_validation_results.md`, written after R3's numbers were in and
followed two paragraphs later by *Disposition: ACCEPTED*. (Corrected 2026-10-02; the earlier
attribution flattered the project by implying the hazard had been foreseen at freeze time.)
`research_synthesis.md` separately records "visualwebarena-only firings" in a scope column. The
risk and the fact that triggers it were both written down, in different documents, and the
conditioning was never run. The rule's
defence at the time was that its condition is structural and frozen in advance: true, and
irrelevant. Freezing a rule does not control for a covariate the test omits.

---

## 5. What these findings support and don't support

### Claim-scope table

| # | claim | evidence | class | scope | key limitation | allowed wording |
|---|---|---|---|---|---|---|
| C1 | Repeating this judge did not help | R=5, 1,106 cases | **[PRE]** | One judge, one config, judge stage | Not full-pipeline; provider nondeterminism not excluded | "On 1,106 trajectories, five repetitions produced intermediate correctness on only 20 cases; majority voting was marginally worse than a single call." |
| C2 | Stopping captures available savings | First-to-3: 0 mismatches, −39.7% calls (2,194 saved of 5,530; 3,336 used) | **[PRE]** | Same | Textbook method; the 0 mismatches hold **by construction** — first-to-3 and majority-of-5 cannot disagree when the first three agree — so only the call saving is empirical | "First-to-3 stopping used 39.7% fewer calls at verdicts identical to majority-of-5 **by construction** — the two cannot disagree once three of five agree, so only the call saving is empirical." (~~"reproduced majority-of-5 verdicts exactly using 39.7% fewer calls"~~: corrected 2026-10-03, after the by-construction label was found only in the caveat column) |
| C3 | Predeclaration changed the headline | 0.543 vs 0.759 | **[PRE vs EXP]** | One corpus, 8 pairs | Post-hoc figure is oracle selection, and is a two-way tie (123/162) rather than a unique best | "The predeclared pair ranked last of eight (0.543); post-hoc selection would have reported 0.759 — tied between two alternates — in an identical report." |
| C4 | Reference-conditioned recovery ≠ deployable | 0.543 vs 0.366/0.465; direction-matched 0.469 vs 0.366 and 0.562 vs 0.465 | **[EXP]** | One pair, one corpus | Exploratory; the gap is general on the false-alarm side only — it reverses sign on the missed-failure side for 2 of 8 alternates | "P(alt correct \| primary wrong) = 0.543; operational overturn precision 0.366 / 0.465. Direction-matched the deployable quantity ran 10.3 and 9.7 points lower." · forbidden: ~~"20–30 points lower"~~ (crosses error directions; corrected 2026-10-02) |
| C5 | Error directions must be separated | 32 vs 130; pooled φ 6.7×→1.6× | **[EXP]** | One corpus | Exploratory | "False alarms outnumbered missed failures 130 to 32; pooled metrics were dominated by the false-alarm stratum." |
| C6 | Deterministic pre-checks: mixed results | R1–R4 on 1,260 held-out (1,259 scored) | **[HO]** | 4 rules, one corpus | n=4; **only two of the four carried numeric accept/reject gates** (R2, R3) — §7 gives R1 and R4 a direction and no threshold (corrected 2026-10-02); R2 (negative self-report on an imperative modification goal) had 13 eligible cases and 6 verdict changes — its 39.3% harm bound is rule-of-three at n=6, not a firing count | "Of four rules, two carried numeric gates: one was accepted but is underpowered (rule-of-three harm bound 39.3% at n=6) and one passed as an escalation signal. The other two carried a direction and no threshold: R1's firing enrichment inverted (0.51×) and R4's met its direction (1.20×) while showing no evaluator-level signal." |
| C7 | ~~Evidence-gap escalation has held-out support~~ **Narrowed 2026-10-02 — confounded with slice** | R3: 25.6% vs 14.4% pooled; 25.6% vs 19.7% within visualwebarena (p = 0.26) | **[HO]** | One rule, and all 133 firings in one benchmark | 99/133 already correct; corrects nothing; pooled test does not control for slice difficulty | "R3 identified a 133-case subset with 25.6% evaluator error against 14.4% elsewhere, but it fires only on visualwebarena; within that slice the contrast is 25.6% vs 19.7% (p = 0.26) and the preregistered test cannot separate the rule from the benchmark. The residual is positive and underpowered, so the claim is narrowed to unproven, not refuted." |
| C8 | RC1 failed fresh-corpus validation | 25.3% vol, 1.165× lift, 28/30 extractor (25/27 out-of-sample) | **[PRE/FRESH]** | One rule, two domains | 1.4% reference noise floor; A3 is a **precision** gate with unmeasured recall, and 3 of its 28 passes are cases the same audit fixed in pass 1 | "RC1 failed both binding gates on τ-bench while its extractor passed a label-blind precision audit at 28/30 — rule failure, not *false-positive* parsing failure. Recall was not measured." |
| C9 | The construct was not empty | Oracle 2.339× vs RC1 1.101× | **[ORA + PRE]** | τ-bench | Oracle is undeployable; oracle itself fails volume gate | "Reconstructed with benchmark-authoritative actions, the construct carried 2.339× lift; the production detector recovered it at 33.1% precision / 49.3% recall." |
| C10 | RC1 did not outperform a no-model baseline | NULL − RC1 = +0.078 [−0.327, +0.575], paired task resamples; MH null 1.237 [0.904, 1.650] vs RC1 1.150 [0.979, 1.352] | **[EXP]** | τ-bench | Null rule preregistered as disqualified; volume 24.1%; partly constitutive of outcome; **no ordering is supported in either direction** | "A check requiring no obligation model ('did the agent write anything?') did no worse than RC1; neither is distinguishable from no effect." ~~"RC1 fell below a no-model baseline \| 1.101× vs 1.171× null"~~ (superseded 2026-10-02) |

**Claims not supported by this evidence:**
- Unscoped claims about repetition — findings are scoped to one judge and one configuration
- "Obligation tracking doesn't work" (the construct is real; the detector failed)
- "Evaluator pairs don't help" (the operational quantity is underpowered at n=32)
- Any generalization to judges, configurations, or corpora not studied here

---

## 6. Process failures found in the research itself

Two counts, kept apart, because they measure different things.

**Internal — 13 process errors** found by this project across 62 commits. **6** were caught
before the outcomes of the affected experiment were visible. **7** were caught only afterward —
including a join-key collision affecting 33% of τ-bench records that had already appeared in a
published report. *This triple is unchanged by the correction below;* it was never wrong about
what the project's own safeguards found.

**External — 11 more process errors** found on 2026-10-02 by an independent end-to-end
reproduction reading this repo's published output: ten wrong or over-strong summary figures and
protocol descriptions, plus a benchmark confound in R3's escalation reading. None was caught by
any safeguard here, and all eleven had already been published.

So: **13 found during the study, 11 more by external reproduction**, 24 rows in the §10 table.

> ~~**24** process errors are now recorded. **6** were caught before the outcomes of the
> affected experiment were visible. **18** were caught only afterward.~~ Superseded
> 2026-10-02 — within hours of being written. Every figure in it is arithmetically correct and
> the framing is not: a single 24/6/18 triple reads as though the project's own audit had grown
> to 24, when what the project caught about itself is 13. The two populations are now counted
> separately above.

The counts are asserted by `scripts/check_synthesis_counts.py` against the structured table
in `docs/research_synthesis.md` §10, internal and external separately.

Notable findings from the process audit:

- A preregistered gate (A2-task, 1.25×) was mathematically unpassable by any rule — computed
  only after outcomes, so it was preregistered at an unreachable threshold.
- A direct measurement comparison (oracle vs null lift) compared two different outcome
  variables, inflating one by 6×. Caught and corrected before publication.
- The same error class (comparing rates across incompatible conditionals) recurred ~~three~~
  **six** times, each instance immediately after the prior one was corrected and documented.
  Three of the six were found externally: the 20–30-point escalation gap, the RC1-vs-null
  ordering computed on different task sets, and R3's pooled escalation test.
- **The reading of the project's one clean numeric pass was narrowed by reproduction.** R3
  passed its preregistered test and its disposition is unchanged; all 133 of its firings are in
  one of four environments, and conditioning on that environment leaves +5.8 of the +11.2
  points, p = 0.26. The residual is positive and in the predicted direction, so the rule is
  unproven at this power rather than refuted. (This read ~~"did not survive reproduction as a
  reading"~~ until 2026-10-03, which is stronger than +5.8 pp supports in either direction.
  R2 was also accepted, underpowered, so "single" was never a count of accepted mechanisms —
  it is a count of clean gate passes.)
- **Nothing in the external eleven required new data.** Every one was recomputable from
  artefacts already committed here, which means the failure was not of evidence but of
  re-reading the output against the claim.

---

## 7. Links to full technical record

| document | what it contains |
|---|---|
| [`docs/research_synthesis.md`](research_synthesis.md) | Full 21-section synthesis; disposition table for all 7 mechanisms (§3.6); claim ledger with forbidden wordings (§9); process-failure audit (§10) |
| [`docs/repetition_study_predeclaration.md`](repetition_study_predeclaration.md) | Preregistration with three amendments — the retracted gate is evidence, not embarrassment |
| [`docs/repetition_study_findings.md`](repetition_study_findings.md) | Full repetition results |
| [`docs/agent_reward_bench_gate1.md`](agent_reward_bench_gate1.md) | AER pair predeclaration and evidence audit |
| [`docs/agent_reward_bench_directional.md`](agent_reward_bench_directional.md) | Operational vs reference-conditioned decomposition |
| [`docs/repair_validation_preregistration.md`](repair_validation_preregistration.md) | R1–R4 preregistration |
| [`docs/repair_validation_results.md`](repair_validation_results.md) | R1–R4 held-out results with counterfactuals |
| [`docs/required_conjunct_preregistration.md`](required_conjunct_preregistration.md) | RC1 preregistration and gate definition |
| [`docs/rc1_forensic_audit.md`](rc1_forensic_audit.md) | RC1 post-outcome analysis and six-figure correction chain |
| [`docs/rc1_successor_probe.md`](rc1_successor_probe.md) | Null-baseline comparison; branch closure |
| [`docs/production_signal_audit.md`](production_signal_audit.md) | Oracle-leakage classification of every rule input |

Reproducible scripts: `scripts/generate_figures.py`, `scripts/check_public_claims.py`,
`scripts/check_synthesis_counts.py`, `scripts/rc1_successor_probe.py`.
