# Evaluator assurance: what survived

*Research synthesis and adversarial review. Closes the evaluator-assurance branch.*
*Written 2026-09-29 over 62 commits spanning 2026-09-26 → 2026-09-29.*

Every figure in this document is cited to the source document that produced it. Where a
number was later corrected, both values appear and the superseded one is labelled.

The governing standard: **the contribution is whatever survived attempts to falsify it, not
the architecture that was hoped to survive.**

---

## 1. Chronological evidence ledger

Evidence classes: **SYN** synthetic · **EXP** exploratory · **PRE** preregistered ·
**HO** held-out · **FRESH** fresh corpus · **ORA** oracle-only · **QUAL** qualitative.

| # | stage | question | class | result | what changed after |
|---|---|---|---|---|---|
| 1 | Deterministic evidence planner v0 (`18f29a9`) | Is "least-cost admissible evaluation strategy" a real computation? | SYN | Planner built; admissibility, not selection, held the content | Architecture note written as a prediction to be falsified |
| 2 | Implementation falsifies the note (`8d41d5a`, `9e2a004`) | Did the design survive contact? | SYN | Multiple fields deleted; `change_scope` reached only a rationale header; `FrozenVerificationClaim` duplicated an existing mechanism | `[REVISED after implementation]` markers become repo convention |
| 3 | Measurement pass (`631657e`, `f6dacbe`, `3964a16`) | Can qualification be stored as rates? | SYN | No — rates erased n. Key became a **quadruple** `(source, failure_mode, population, distribution)`; rates replaced by counts | "0.80 from n=500 and 0.80 from n=10 are different objects" |
| 4 | Decision-procedure model checked | Does the binomial replication model hold per-case? | SYN | **Wrong shape.** Model says `P(miss)=0.042` at n=7; per-case average is `0.142`, and no n≤12 reaches the 0.05 target — a Jensen-type error | Fixed replication counts lose credibility |
| 5 | Policy benchmark + stopping vs allocation (`0ee9137`…`1f5b07d`) | Is adaptive allocation worth more than sequential stopping? | SYN | **No.** `fixed_n_8` $35.00 → `early_stop_8` $25.19 (−28%, provably identical verdicts) → `confidence_stop_8` $19.31 (−45%); `heterogeneity_triage` $28.31 — costs *more* than stopping | "Sequential stopping captures 100% of the available cost saving; allocation captures 0%" |
| 6 | Blind escalation control (`4392bf4`) | Does the candidate policy beat a control that knows nothing? | SYN | On the noisy fixture, escalating an arbitrary 1/5 by hash cuts error 4.00 → 1.75 and **dominates** the candidate | Kill criterion 7 fires; control appended automatically by `compare` so it cannot be omitted |
| 7 | Prior-art list written (`4e8b327`) | What here is actually ours? | — | 14 items conceded as established (stopping, cascades, judge nondeterminism, VOI, mutation testing, calibration…) | "If a future document describes any of these as a finding of this project, that document is wrong" |
| 8 | Alternate rates exposed (`c5a54f2`, `f5dd2aa`) | Where did alternate-evaluator performance come from? | SYN | **Two unsourced float literals** (`sensitivity 0.95`, `FPR 0.05`) in the cost model, consumed at one place in the scorer | `AlternateCharacteristics` unconstructible without a named artifact or explicit `assumed_because`; repro now requires `--assume-alternate-rates 0.95 0.05` |
| 9 | Two-corpus / enrichment red team (`929d142`, `9605ccf`, `a3a1277`) | Does the sample-size story hold? | — | **Four claims retracted or weakened**, incl. the `MIN_ERRORS_FOR_CONDITIONAL = 16` floor and the 0.50 sufficiency rule | `r*` (break-even recovery) becomes a caller-declared policy input with no default; absent it the output is `NOT DECISION-SUFFICIENT` |
| 10 | AgentRewardBench import + pair predeclaration (`9fdaaf1`, `594918f`) | Can we get real paired evaluator data? | PRE | 1,106 analysable trajectories (811 ref-fail / 295 ref-success); pair `functional`→`aer` chosen on five pre-outcome criteria | First real evidence in the repo |
| 11 | Pooled complementarity result (`07c19c6`) | Does the alternate recover the primary's errors? | PRE | Recovery **0.543** [0.466, 0.618], φ **+0.323** — **last of the eight** candidates; post-hoc best would have been **0.759** (a two-way tie, φ +0.064 or +0.091 depending which is picked) | The predeclaration's cost is measured: 21.6 points of headline |
| 12 | Directional decomposition (`2c8479d`) | Do the two error directions behave the same? | EXP | **No.** 162 primary errors = 32 missed failures + 130 false alarms. Recovery 0.469 on misses vs 0.562 on false alarms. Pooled recovery was dominated by the false-alarm stratum | Predeclared pair is *tied first of eight* on missed failures — pooled ranking was the wrong metric |
| 13 | Operational vs reference-conditioned | Is recovery a policy quantity? | EXP | **No.** `P(alt correct \| primary wrong)` = 0.543; deployable overturn precision = **0.366** (to-fail) / **0.465** (to-pass) — direction-matched, **10.3** / **9.7** points lower (§3.2.1; "20–30 points" withdrawn 2026-10-02) | "The single most consequential thing found in this pass, and it is a defect in the framing, not in the data" |
| 14 | Conditional association / pooled-φ (`e66f364`) | Is φ a mechanism-diversity indicator? | EXP | **No.** φ spread across 8 alternates collapses from **6.7×** pooled to **1.6×** conditioned on the reference label; pooled OR below the ref-fail OR for all 8, below *both* strata in 3 of 8 | φ withdrawn as a diversity proxy; it may be measuring threshold alignment |
| 15 | Repetition predeclaration (`10a8776`, `1c03e46`, `608c4ce`) | Does repeating the judge help? | PRE | Gate verification found the deployed config is `gpt-4o-2024-11-20`, **temperature 0.0, seed 0**, no variation — discovered *before any API call* | Study reframed from "measure the wobble" to "measure the fix" |
| 16 | Prompt-caching correction | Does caching invalidate a repetition? | — | **No.** "A cached completion is not an independent draw" describes a mechanism that does not exist; caching reuses prompt-prefix state, not completions | Instruction to disable caching withdrawn; caching becomes a measurement |
| 17 | Staged R=2→R=5 gate withdrawn (`9fabf47`) | Can we avoid ~$35 of inference? | — | **Gate retracted.** Two defects: it revived the disavowed constant 16 as a "resolution floor", and its bound needed conditionally-IID draws while claiming only exchangeability — an IID bound gating the study that existed to measure independence | "The engineering and methodological cost of the gate exceeded the $35 it was designed to save" |
| 18 | R=5 repetition study (`f1bc7d2`, `2b430cb`) | Does repeated execution recover errors? | PRE | **Outcome C — both directions negligible.** 5,530 analysed calls, $46.18 ($49.50 billed). 98.8% / 96.6% of cases at k∈{0,5}. Majority-3 and majority-5 both marginally *worse* than one call | Repetition killed as a lever for this configuration |
| 19 | "Shared unresolved" label withdrawn (`2ccd08b`) | Were 15 cases wrong under all judges? | — | **No — only 5 were.** The label named 15 cases that 8 judges did not share | Term restricted to the 5-case subset; correction applied in place |
| 20 | 15-case qualitative review (`5b79493`, `48fd0ab`) | Where do judge failures actually originate? | QUAL | Earliest failed layer: 1 reference · 0 observation · **5 representation** · **4 specification** · **5 evaluator reasoning** · 0 decision. **Only 5 of 15 fail first at the evaluator** | Richer judges are the wrong lever for 10 of 15 |
| 21 | Oracle-leakage audit (`db0975d`) | Are the candidate rule inputs production-visible? | — | **Infeasibility flag rejected**: 84/1302 workarena task IDs contain `infeasible`; telling the judge the task is impossible hands it the verdict | Leakage class (A/B) assigned to every rule input before validation |
| 22 | Held-out rule validation (`1bdab61`, `af10543`) | Do deterministic pre-checks survive a quarantined split? | HO | 1302 = 1260 validation + 42 quarantined. **R1 REJECTED** (lift **0.51×**, inverted; withheld veto would have been 6 helped / 14 harmed). **R2 ACCEPTED but UNDERPOWERED** (6/0, but lift 1.06×, harm bound 39.3%). **R3 ACCEPTED** (25.6% vs 14.4% evaluator error — pooled across benchmarks; superseded as a reading by row 33). ~~**R4 REJECTED**~~ → **R4 MET ITS DIRECTION** (1.20× lift; the 16.1% vs 15.5% evaluator-error contrast on which REJECTED was decided is not a §7 criterion — corrected 2026-10-02, §3.3.3) | ~~Two of four frozen rules fail~~ — only R2 and R3 carried numeric gates; R1 and R4 were directional (§7). The counterfactual of the veto R1 was denied becomes the most valuable number produced |
| 23 | RC1 freeze + τ-bench preregistration (`086f0c6`, `3dc3a85`) | Does required-conjunct matching enrich failures on a fresh corpus? | PRE/FRESH | 1,980 records, 165 tasks, 2 domains, 2 agents, programmatic reward, read label-blind during scoping with `reward`/`info` withheld in code (~~"never touched"~~ corrected 2026-10-02; §8.4 of the scoping doc). Gates: A1 <15% volume, A2 ≥1.50× traj / ≥1.25× task, A3 ≥27/30 extractor | Three-commit chronology (freeze → preregister → report) becomes repo standard |
| 24 | Label-blind extractor audit (`8197c5a`) | Are firings attributable to the rule or the extractor? | PRE | **A3 PASSES 28/30.** Three false positives found and fixed pre-reward — **on cases 02, 06 and 16 of this same 30-case sample**, which pass 2 then scored CORRECT; strictly out-of-sample, **25/27**. A3 is a precision gate only; recall is unmeasured | Rule failure cannot be blamed on extraction **in the false-positive direction**. An audit that both finds and scores its own fixes needs the out-of-sample figure stated beside the headline (disclosed 2026-10-02) |
| 25 | RC1 rejected (`404174f`, `226ee57`) | Did RC1 pass? | FRESH | **REJECTED.** Volume 25.3%, lift 1.165× | Both binding gates failed |
| 26 | Join-collision discovery (`c43cdea`) | Why is there an impossible row in the harm sample? | — | **660 gpt-4o records (33.3%) scored against sonnet's rewards.** Detected by tracing one row the classifier cannot emit | Six published figures corrected; §18 harm decomposition fully replaced |
| 27 | Forensic audit (`2d19e22`) | Which conclusions survive the corrected join? | ORA/EXP | A2-task gate **INVALID** — 81.8% of tasks hold a failing trial, capping achievable lift at 1.222× below its own 1.25× bar. F4-dominant mechanism claim withdrawn; **F6 dominant (~242 firings)**. H2 narrowed to **H2a** | Nine claims withdrawn or narrowed in one table |
| 28 | Oracle/construct diagnostic | Is the detector bad, or the construct empty? | ORA | **Construct is real, detector is not.** Oracle volume 17.0%, within-task lift **2.339×**; RC1 recovers it at **33.1% precision / 49.3% recall**; right-for-right-reason on **118/501 = 23.6%** of firings. Even the oracle fails A1 (17.0% > 15%) | Construct carries signal; a production-valid representation of it is not established (H2a) |
| 29 | Successor probe + null-rule comparison (today) | Is a successor warranted? | EXP | **No.** On the deployable outcome, within-task: oracle **2.339×**, null rule (no successful write, no model) **1.171×**, **RC1 1.101×**. ~~RC1 falls below a no-model baseline.~~ **Withdrawn — see row 32.** Corrective state visible in structured tool results in **12/12** harm cases | Null-baseline check added as a standing gate |
| 30 | Correction to the probe (today, pre-publication) | Was the null-rule headline valid? | — | **No — withdrawn.** First draft claimed "null 7.189× vs construct 2.339×", comparing two different outcome variables where "no write" partly *constitutes* "a required write is missing" | Construct's 2.339× **upheld**, not narrowed; the damage lands on RC1 instead |
| 31 | Branch closed | — | — | Stop experimenting; synthesize | This document |
| 32 | Second correction to the probe (2026-10-02, **external reproduction, post-publication**) | Does RC1 actually sit below the null rule? | EXP | **No — the ordering is withdrawn.** The three lifts are computed on **different task sets** (oracle 94, null 80, RC1 109) because the within-task filter keeps only tasks where a rule both fires and does not. Paired on the same task resamples, NULL − RC1 = **+0.078 [−0.327, +0.575]**; under Mantel–Haenszel stratification by task, null **1.237 [0.904, 1.650]** and RC1 **1.150 [0.979, 1.352]** — neither distinguishable from 1. Only the oracle separates (**2.054 [1.752, 2.530]**) | Row 29's verdict ("no successor is warranted") **stands**; it never rested on the ordering. Two point estimates on non-identical strata were published as a comparison with no interval on either |
| 33 | R3 conditioned on benchmark slice (2026-10-02, **external reproduction, post-freeze**) | Which benchmarks does R3 fire in? | HO | **All 133 firings are visualwebarena**, the slice with the highest judge-error point estimate of the four (22.4%, vs **19.8% webarena** / 11.1% workarena / 3.9% assistantbench). The preregistered test pooled, so it compared one slice against the other three. ~~"(22.4%, vs 3.9% assistantbench / 11.1% workarena)"~~ and ~~"one hard slice against three easier ones"~~: corrected 2026-10-03 — this row listed three of the four slices and dropped the one that nearly matches visualwebarena, which inflates the apparent gap; 22.4 against 19.8 at n = 290 and n = 373 is a rank, not a separation. Within slice: **25.6% vs 19.7%, Fisher p = 0.26**, against 25.6% vs 14.4%, p = 0.0015 pooled — **+5.8 of the +11.2 pp survives**, +5.4 pp is slice identity. Split by error direction, the residual is **entirely on the missed-failure side** (25.3% / 22-of-87 vs 15.8% / 18-of-114, +9.5 pp, p = 0.1099); the false-alarm side **reverses** (26.1% / 12-of-46 vs 30.2% / 13-of-43, −4.1 pp, p = 0.8139). The held-out split could not have caught the confound: **1,064 of the 1,260 validation cases (84.4%)** were already inside the pairing population the project had tabulated by benchmark | R3's **disposition stays ACCEPTED** (it met its criterion; the test ran as specified) and its *reading* is **narrowed**, not withdrawn: the residual stays positive and in the predicted direction, so the claim shrinks rather than inverting -- unproven, not refuted. The reproduction's own split (25.9% vs 14.8%, p = 0.065; 25.0% vs 32.4%) was computed on the 266 VWA cases also in the paired functional x aer file; the full 290-case arm above is canonical and the two agree on the reading. A `CONFOUNDED` label was introduced and reverted the same day. `scripts/arb_r3_slice_check.py` added (sections 6–7 compute the direction split and the overlap); the stratification is now printed inside the preregistered test's own output in `arb_repair_validation.py`. §3.3.1 |
| 34 | R1/R4 gate audit (2026-10-02, **external reproduction, post-freeze**) | What thresholds did R1 and R4 actually have? | HO | **None.** §7 of the repair preregistration: *"No accept/reject on accuracy, since they change no verdict"* — a direction only. R1 **fails** it (0.51×, inverted). **R4 meets it** (1.20×), so R4's published `REJECTED` was decided after the fact on an evaluator-error contrast §7 never named | Gated denominator drops from **five to three** (R2, R3, RC1); R1/R4 recorded as **directional**. The 3 + 2 split is now asserted by `scripts/check_synthesis_counts.py`. RC1's A2 anchor loses its "rejected precedent" endpoint (threshold not revised). §3.3.3 |

The shape of the ledger is the point: of 34 stages, **17 removed or narrowed a claim the
project had already made** — rows 2, 4, 6, 8, 9, 13, 14, 16, 17, 19, 21, 26, 27, 30, 32, 33
and 34. It did not accumulate support. (The figure given here until 2026-10-02 was ~~12 of
31~~, hand-typed and undercounted; the row list is enumerated so the count can be checked
rather than trusted.)

---

## 2. Evidence-class taxonomy

Nothing below may borrow strength from a class above it.

| class | what it is | what it licenses | members |
|---|---|---|---|
| **A. Preregistered / held-out** | Criteria and split frozen in a commit before outcomes were readable | Claims about *this* configuration on *this* corpus | AER pair predeclaration (§11); R=5 repetition study (§18); held-out R1–R4 on the 1260-case quarantined arm (§22); τ-bench RC1 with gates and extractor audit frozen pre-reward (§23–25) |
| **B. Exploratory** | Analysis conducted after outcomes were visible | Hypotheses, mechanism explanations, "reasons to lower your prior" | Directional decomposition (§12); operational-precision analysis (§13); conditional φ (§14); forensic mechanism reclassification (§27); right-reason/wrong-reason split and the successor probe (§28–29) |
| **C. Synthetic** | Generated by `scripts/make_fixtures.py` from a seeded RNG; labels are the generator's inputs | Claims about the *planner's arithmetic*. **Nothing about any real judge** | Planner v0 (§1–4); policy benchmark and stopping-vs-allocation (§5); blind escalation control (§6); every cost figure priced from the 0.95/0.05 literals (§8) |
| **D. Oracle-only** | Uses benchmark-authoritative metadata unavailable at production time | Ceilings and diagnostics. **Never a detector** | `info.task.actions` construct reconstruction (§28); right-for-right-reason partition (§29); the rejected infeasibility flag (§21) |
| **E. Qualitative** | Per-case human reading, n=15 | Mechanism vocabulary, hypothesis generation | 15-case unresolved review (§20); RC1 harm-sample cards (§27) |

Three boundary rules the project had to learn the hard way, each after a violation:

1. **A synthetic cost figure is not an economic finding.** Every `policy_benchmark_findings.md`
   number rests on `sensitivity 0.95 / FPR 0.05`, two literals with no study behind them.
2. **An oracle ceiling forecasts nothing about a production detector.** The 2.339× construct
   lift is class D; RC1's 1.101× is what a deployable rule actually achieved.
3. **An exploratory metric may not overturn a preregistered disposition.** R2 remains
   ACCEPTED as preregistered even though a post-hoc precision figure (1.06×) undermines it.
   The correct move is to lower the prior and say so, not to relabel the verdict.

---

## 3. Strongest quantitative findings

### 3.1 Repetition study — class A (preregistered, unconditional)

| quantity | value |
|---|---|
| cases | 1,106 (811 ref-fail / 295 ref-success) |
| repetitions | R = 5, unconditional |
| valid executions | 5,530 analysed (5,886 collected; 356 duplicates dropped at load) |
| cost | **$46.18** analysed · **$49.50 billed** (≈$58 without the 44.7% prompt-cache discount) |
| deployed config | `gpt-4o-2024-11-20`, temperature 0.0, seed 0, `max_completion_tokens` 1024 |
| k=0 / k=5 (ref-fail) | 97 (12.0%) / 704 (86.8%) |
| k=0 / k=5 (ref-success) | 75 (25.4%) / 210 (71.2%) |
| at an extreme | **98.8%** ref-fail, **96.6%** ref-success |
| any within-case variation | 10 cases per stratum — **20 of 1,106** |
| first-two disagreement | 0.62% ref-fail [0.26, 1.44]; 1.36% ref-success [0.53, 3.43] |
| single-execution error | 12.70% missed-failure; 27.25% false-alarm |
| majority-of-3 | 12.82% / 27.80% — **worse in both strata** |
| majority-of-5 | 12.95% / 27.46% — **worse in both strata** |
| sequential first-to-3 | identical verdicts to majority-of-5 (0 mismatches — **by construction**, not a finding); 98.9% terminate at 3 calls (1,094/1,106); **−39.7% calls** (2,194 saved of 5,530; 3,336 used); ≈$27.86 |

**Precise conclusion:** *repeated execution of the deployed AER judge under its actual
configuration exhibited very little useful variability and did not improve either error
direction.* It does **not** license "LLM judges are deterministic" — the findings doc
itself forbids that, noting temperature-0 determinism is not the same as no variability and
provider-side nondeterminism is not excluded by five draws.

### 3.2 Alternate-evaluator evidence — classes A and B

| quantity | value | class |
|---|---|---|
| predeclared pair (`functional`→`aer`) pooled recovery | **0.543** [0.466, 0.618], pooled φ +0.323 | A |
| rank among 8 candidates on pooled recovery | **last of eight** | A |
| error association, **missed-failure stratum** (n=811) | φ **+0.250**, OR **9.38**, RR **4.93×** | B |
| error association, **false-alarm stratum** (n=295) | φ +0.310, OR 4.17, RR 2.78× | B |
| `aer`'s rank on **failure-stratum** φ | **4th of 8** (1st on pooled φ) | B |
| failure-stratum φ / OR across **all eight** alternates | +0.171 to +0.273 / **5.08 to 11.11** | B |
| post-hoc best pair — **tied**: `functional`→`gpt-4o-mini` axtree (φ +0.064) and `functional`→`qwen-2.5-vl` (φ +0.091), both 123/162 | **0.759** [0.688, 0.819] | B (oracle selection) |
| gap the predeclaration cost the headline | **+0.216 recovery** | — |
| primary error decomposition | 162 = **32 missed failures** + **130 false alarms** | A |
| missed-failure recovery | 0.469 [0.309, 0.636], 15/32 — **tied first of eight** | B |
| false-alarm rescue | 0.562 [0.476, 0.644], 73/130 | B |
| **operational** overturn-to-fail precision | **0.366** (15/41) | B |
| **operational** overturn-to-pass precision | **0.465** (73/157) | B |
| gap, direction-matched: catch 0.469 → 0.366 | **10.3 pp** | B |
| gap, direction-matched: rescue 0.562 → 0.465 | **9.7 pp** | B |
| same gap across all 8 alternates | false-alarm side **+9.7 to +46.0 pp**; missed-failure side **−14.7 to +23.1 pp**, negative for 2 | B |
| blanket adjudication on primary FAIL | 73 correct / 84 wrong = **−11 net**; raw-count loss for **5 of 8** pairs; non-positive for all 8 iff a missed failure is weighted ≥ **1.057×** a false alarm | B |
| φ spread across 8 alternates, pooled → ref-conditioned | **6.7× → 1.6×** | B |
| pooled OR below *both* strata | **3 of 8** | B |
| swapping to the other predeclared primary (`aer`) | missed failures **32 → 101** on the same 1,106 cases | B |

**The distinction that must survive into any write-up:** reference-conditioned recovery is
not an executable production policy. Nothing selects the primary's errors at runtime.

#### 3.2.1 Correction, 2026-10-02 — the gap was pooled, and it is not general

*External reproduction.* Two rows above carried stronger claims than the data supports.

**"20–30 points" (now 10.3 pp / 9.7 pp).** The gap was computed by subtracting the two
direction-specific overturn precisions from **0.543**, which is recovery pooled over both
error directions. The direction-matched reference-conditioned values were already in this
same table, two rows up: catch **0.469** against overturn-to-fail **0.366** is 10.3 pp, and
rescue **0.562** against overturn-to-pass **0.465** is 9.7 pp. The arithmetic needed to catch
this required no new data and no new script — only subtracting the adjacent row instead of the
headline one. §3.2's own thesis is that pooling across error directions hides things; the
summary statistic for that thesis was itself pooled across error directions.

**"Non-positive for all 8" (now: a raw-count loss for 5 of 8).** Net raw-count exchange under
blanket FAIL adjudication is **positive** for `claude-3.7-sonnet-noscreen` (+4),
`gpt-4o-noscreen` (+5) and `llama-3.3-70b-noscreen` (+1). The original claim is recoverable
but only with its weighting stated: non-positive for every alternate iff a missed failure
costs at least **1.057×** a false alarm. That is a defensible weighting for most deployments
and it was not declared, so the sentence asserted as data what was partly a value judgement.

**Pooled φ was being quoted as the strength of evaluator dependence.** Same defect, third
instance. The number carried into the README, `agent_reward_bench_findings.md` §6 and §8,
and `agent_reward_bench_directional.md` §16 was **+0.323**, pooled. Pooled φ against this
primary is close to a restatement of the **false-alarm** stratum, because `functional` puts
almost all of its errors there (FPR 0.441 against FNR 0.040) — and the stratum assurance
turns on is the other one. Stated on the missed-failure stratum, the predeclared pair is
φ **+0.250**, OR **9.38**, RR **4.93×**, and the ordering of the eight alternates changes
almost completely: pooled φ agrees with failure-stratum φ on **1 of 8** positions, and `aer`
drops from 1st to **4th**. Worse for the figure's usefulness, **every** alternate sits
between OR **5.08 and 11.11** on that stratum, so failure-stratum dependence does not
discriminate between them at all — a fivefold spread in pooled φ (0.048 to 0.323) collapses
to a 1.6× spread once conditioned. This was already established inside
`agent_reward_bench_conditional.md`; what failed was that the documents citing a φ went on
citing the pooled one. A conditional analysis that does not reach back into the claims it
conditions is a document, not a correction.

**What the correction does to the finding.** It survives, and the direction split is what
makes it survive rather than what weakens it. The false-alarm-side gap is positive for all
eight alternates (**+9.7 to +46.0 pp**). The missed-failure-side gap ranges **−14.7 to
+23.1 pp** and is negative for `gpt-4o-noscreen` (−8.1) and `qwen-2.5-vl-noscreen` (−14.7) —
for those two the deployable quantity is *better* than the reference-conditioned one. So the
transferable claim is narrower than "the operational number is always lower": it is that the
two quantities differ, that the difference is systematic in the direction that dominates this
corpus's error mix, and that its sign on the other direction depends on the alternate.

Reproduce with `scripts/arb_directional.py` → `data/REAL_arb_directional.csv`
(`missed_failure_catch_*`, `false_alarm_rescue_*`, `overturn_to_*`,
`adjudication_cleared_correctly` / `adjudication_cleared_wrongly`).

### 3.3 Held-out rule validation — class A

Split: 1302 annotated = **1260 validation** + **42 quarantined** (15 discovery + 27 same-task
siblings). Strict arm 1180.

| rule | fires | key held-out number | disposition |
|---|---|---|---|
| **R1** self-contradictory infeasibility claim *(directional, no numeric gate — §7)* | 27 (2.1%) | lift **0.51×** — *inverted*; counterfactual veto **6 helped / 14 harmed, net −8** | evidence half **FAILS ITS DIRECTION** (the §7 no-information case); escalation half survives, post hoc |
| **R2** negative self-report on imperative goal | 13 eligible, 6 changed | **6 helped / 0 harmed**; but firing precision **1.06×** and rule-of-three harm bound **39.3%** at n=6 | **ACCEPTED**, simultaneously UNDERPOWERED-REGARDLESS |
| **R3** unverifiable image premise | 133 (10.6%), **all visualwebarena** | evaluator error **25.6%** on escalated vs **14.4%** on remainder (p = 0.0015) — but **25.6% vs 19.7% within visualwebarena, p = 0.26**; removes 22 E1 + 12 E2 from authority; **99 of 133 escalated were already correct** | **ACCEPTED** — disposition stands; the *reading* is narrowed, see §3.3.1 |
| **R4** terminal search-results route *(directional, no numeric gate — §7)* | 118 (9.4%) | lift 1.20× on the *agent's* outcome, but evaluator wrong on **16.1%** of firings vs **15.5%** elsewhere — 0.6 pt, p = 0.89 | **MEETS ITS DIRECTION** (1.20× > base rate). ~~REJECTED~~ **is post hoc** — corrected 2026-10-02, see §3.3.3. Tells you about the agent, not the evaluation; application-specificity was declared in §9 of the preregistration, not discovered |

#### 3.3.1 R3 conditioned on slice — correction of 2026-10-02

Found by external reproduction, after the canonical freeze. R3 fires 133 times and every
firing is visualwebarena; the other three benchmarks produce none. visualwebarena also carries
the highest judge-error point estimate of the four — though only 2.6 points above webarena,
which at n = 290 against n = 373 does not separate the two (~~"visualwebarena is also where the
judge is weakest"~~: corrected 2026-10-03; the claim is a rank, not a demonstrated ordering):

| benchmark | R3 fires | cases | judge error, R3 ignored |
|---|---|---|---|
| visualwebarena | **133** | 290 | 22.4% |
| assistantbench | 0 | 128 | 3.9% |
| webarena | 0 | 373 | 19.8% |
| workarena | 0 | 468 | 11.1% |

So the preregistered test contrasted one slice with the other three — a contrast whose largest
component, webarena at 19.8%, is barely below visualwebarena at all. Conditioning on
benchmark leaves **25.6% vs 19.7% (34/133 vs 31/157), Fisher p = 0.26** — +5.8 pp of the
+11.2 pp pooled separation, with +5.4 pp attributable to slice identity.
Reproduce: `scripts/arb_r3_slice_check.py`.

**Disposition: unchanged, ACCEPTED.** R3 met its preregistered criterion and the test ran as
specified. Re-labelling a disposition after the fact, on the strength of an analysis the
preregistration did not name, is the post-hoc move this project exists to catch — it was
briefly done here on 2026-10-02 (a `CONFOUNDED` value was added to the ledger) and reverted
the same day. The disposition records what the test returned; it is not a score.

**What is narrowed is the reading.** R3 passed a test that, as specified, could not
distinguish it from a proxy for the highest-error environment. The within-environment effect is
+5.8 pts and unresolved: the residual runs in the direction R3 predicts, and n=133 vs 157 is
underpowered, so the evidence does not show the rule fails — it fails to show the rule works.
"Narrowed" rather than "withdrawn" is the accurate word, and the distinction is not cosmetic:
the point estimate stays positive and in the predicted direction, so what shrank is the size of
the claim R3 supports, not its sign. R3 is no longer quotable as a *demonstrated* positive
result of this study. Settling it needs a corpus where the evidence gap occurs outside one
benchmark.

**The residual is on one side only.** "Evaluator error" pools two populations a reviewer acts
on differently: among reference-fail cases the only available error is a *missed failure*
(judge said SUCCESS), among reference-success cases a *false alarm*. Splitting the
within-visualwebarena contrast by that axis:

| side | escalated | not escalated | diff | Fisher p |
|---|---|---|---|---|
| missed-failure (ref=fail) | **25.3%** (22/87) | **15.8%** (18/114) | **+9.5 pp** | 0.1099 |
| false-alarm (ref=success) | 26.1% (12/46) | 30.2% (13/43) | **−4.1 pp** | 0.8139 |

So the whole of the +5.8 pp residual sits on the missed-failure side, and the false-alarm side
runs slightly the *wrong* way. Neither stratum reaches significance at n=87/114 and n=46/43 —
this sharpens the shape of the residual, it does not rescue it. Values from
`scripts/arb_r3_slice_check.py` section 6; the same split now prints inside the preregistered
test's own output in `scripts/arb_repair_validation.py`, so the pooled pair cannot be read
alone again.

The external reproduction reported this split as 25.9% vs 14.8% (p = 0.065) and 25.0% vs 32.4%,
on the 266 visualwebarena validation cases that also appear in the paired functional×aer file;
the table above is the full 290-case visualwebarena arm, which is canonical here. The two differ
only by population and support the same reading — residual on the missed-failure side,
false-alarm side reversed, neither resolved at this n.

Three readings this does **not** license. It does not make R3 a missed-failure detector: the
split was chosen after seeing the pooled residual fail, so it is exploratory, and a two-way
split of a non-significant residual will usually concentrate it somewhere. It does not raise
the claim's evidential class — the direction split is class B on a class A test. And it does
not change the disposition, for the reason given above.

**On how it was missed, and who said what when.** §22 of this document already recorded
"visualwebarena-only firings" in a scope column. The hazard was also written down — but *not*
in the preregistration, and the difference matters. It is a post-results caveat in
`docs/repair_validation_results.md` ("The caveat this result needs"), written after R3's
numbers were in:

> Any rule that escalates the cases a judge finds hard will pass a test of the form
> "is the judge worse on the escalated subset". That test is necessary, not sufficient,
> and the preregistration should have said so.

*"Should have said so"* — the caveat says the preregistration did not. An earlier version of
this section, and of five other documents, credited the sentence to the preregistration, which
made the project look as though it had foreseen the hazard and merely failed to act. It had
not: it noticed the hazard while writing up the result that the hazard applies to, said the
test it had already run was insufficient, and published the result anyway with
**Disposition: ACCEPTED** two paragraphs later. That is the less flattering and more accurate
account. Corrected 2026-10-02 after the same external reproduction.

So: the hazard and the fact that triggers it were both on paper, one document apart, and the
conditioning was never run. The defence recorded at the time — that R3's condition is
structural, answer-independent, and frozen before its error rate was known — is true of the
rule and silent on the confound. Freezing a rule does not control for a covariate the test
omits. This is the clearest instance in the project of
the failure mode the project is about: a preregistered test that measures something other
than what it is read as measuring.

**Methods note: the quarantine could not have prevented this.** The split protected against
one threat and was read as protecting against another. It held back 42 cases — the 15
discovery cases and their 27 same-task siblings — so that no rule was tested on the cases that
suggested it. It did nothing about this confound, and could not have, because the quarantine
partitioned *cases* while the information that would have exposed the confound is a *property
of the corpus*: which benchmark this judge errs on most.

That property was already tabulated. **1,064 of the 1,260 validation cases (84.4%) are inside
the 1,106-trajectory population whose AER correctness the pairing study had already scored
case by case** (§3.1–3.2); so are all 42 quarantined cases. By the time R3 was validated, this
judge's per-slice error rate was a derived quantity of data the project had been analysing for
weeks. Nobody derived it, because the quarantine made the arm feel unseen.

The generalisable form: **a held-out split controls for the analyst having seen the outcome of
these cases, not for the analyst having seen the structure of this corpus.** A confound that
lives in a covariate — benchmark, domain, agent, difficulty tier — survives any split that
does not stratify on it. Reproduce the overlap with `scripts/arb_r3_slice_check.py` and the
split file `data/REAL_arb_discovery_validation_split.json`; the counts are in
`scripts/public_claim_ledger.py` under `r3_validation_cases_in_pairing_population`.

#### 3.3.2 The same check applied to R1, R2 and R4 — class sweep, 2026-10-02

Correcting one instance of a defect and not sweeping for the rest of its class is how the R3
confound reached publication in the first place. R1's escalation half and R4's comparison are
the same kind of pooled error-rate claim, computed the same way. All four rules therefore got
the same treatment: `scripts/arb_rule_slice_audit.py`.

| rule | firings | slices it fires in | pooled error contrast | within-slice |
|---|---|---|---|---|
| R1 contradictory infeasibility | 27 | **3** (vwa 7, wa 10, work 10) | 33.3% vs 15.2%, p = 0.026 | +6.3, +10.4, +29.5 pp — positive in all three |
| R2 negative self-report | 13 | 2 (vwa 2, wa 11) | 69.2% vs 15.0% (n too small to test) | +27.8, +54.5 pp |
| **R3 unverifiable image premise** | 133 | **1** (vwa 133) | 25.6% vs 14.4%, p = 0.0015 | **+5.8 pp, p = 0.26** |
| R4 terminal search route | 118 | **3** (ab 42, vwa 21, wa 55) | 16.1% vs 15.5%, p = 0.89 | −2.3, −8.8, +8.7 pp |

**R3 is the only one of the four whose firings sit in a single slice**, so it is the only one
whose pooled contrast can be a slice artefact — the defect is specific, not pervasive. R1's
escalation half, the other claim on the project's "weak claims validate more easily" argument,
fires across three benchmarks and keeps a positive residual inside each one; its weakness is
power — the *fired* arms are 7, 10 and 10 cases, against unfired arms of 283, 363 and 458 — so
it is ~~"not confounded"~~ **not obviously confounded**, which is the weaker and accurate claim.
Three same-signed slices at fired n of 7–10 cannot establish that no slice effect is present;
they establish that none was found at the power available. (Both parts corrected 2026-10-02:
~~"every within-slice arm is n < 20"~~ is false of the comparison arms, and a reader takes it to
mean the test saw 20 cases when it saw 290, 373 and 468.) R4's within-slice residuals change
sign across slices (−2.3, −8.8, +8.7 pp), which is what a rule carrying no information about
evaluator reliability should look like. That is a statement about R4's evaluator-error
contrast only; R4's preregistered criterion was firing enrichment against base rate, which it
met at 1.20×, and nothing here changes that.

This sweep does not rescue R3 and is not offered as doing so. It establishes the scope of the
2026-10-02 correction: one rule, not the rule set.

#### 3.3.3 R1 and R4 never had numeric gates — correction of 2026-10-02

Also found by external reproduction. Every summary in this repo put all four held-out rules in
the frozen-numeric-gate column — §3.6 answered "Yes" to *"frozen pass/fail threshold?"* for R1
and R4, T2.1 and §18 counted "two of four failed" — and the abstract's denominator of five was
built on that. Section 7 of `docs/repair_validation_preregistration.md` says otherwise:

> **R1 and R4 (evidence, not vetoes).** No accept/reject on accuracy, since they change
> no verdict. Reported as firing precision against base rate. A rule whose firings are
> no more enriched for reference-fail than the corpus base rate carries no information
> and will be recorded as such.

That is a *direction* with no threshold. Against it:

| rule | §7 criterion | result | verdict against the criterion actually declared |
|---|---|---|---|
| R1 | firings more enriched for reference-fail than base rate | 37.0% vs 72.4% → **0.51×** | **FAILS** — inverted, which is the no-information case §7 names explicitly |
| R4 | same | 87.3% vs 72.4% → **1.20×** | **MEETS IT** |

So **R4's published `REJECTED` disposition is post hoc.** It was decided on the evaluator-error
contrast (16.1% on firings vs 15.5% elsewhere, 0.6 pt, p = 0.89) and on application-specificity
— the first a metric §7 never named, the second declared in advance in §9 (*"R4 is explicitly
application-specific"*) and therefore not an outcome. §8 of the same document committed that
*"thresholds in section 7 will not be revised after the fact"*; inventing one where §7 declined
to set one violates that commitment as squarely as moving a number would.

This is the same error as the `CONFOUNDED` label briefly placed on R3 on 2026-10-02 and reverted
the same day, pointing the other way: in both cases a disposition was moved on the strength of an
analysis the preregistration never named. It is recorded here to make the symmetry explicit — the
project caught the version that made a result look *worse* within hours, and did not catch the
version that made its own negative-result count look *larger* until an outside reader read §7.

**Consequences for every count in this document.** The gated denominator is **three** (R2, R3,
RC1), not five. Two rules (R1, R4) are **directional**. Two (repeated execution, alternate-judge
pairing) had no criterion of any kind. `scripts/check_synthesis_counts.py` asserts the 3 + 2 split
against §3.6 so the prose and the table cannot drift apart again. What does *not* change: R4 is
still weak evidence about the agent's outcome and no evidence about the evaluator, and is still
application-specific. The finding is intact; the label on it was not earned.

### 3.4 τ-bench RC1 — class A/FRESH, corrected values only

| gate / quantity | value | verdict |
|---|---|---|
| A1 firing volume | **25.3%** (501/1980) vs <15% | **FAIL** |
| A2 trajectory lift | **1.165×** vs ≥1.50× | **FAIL** |
| A2 task lift (1.25×) | 0.906× | **GATE INVALID** — 135/165 tasks (81.8%) hold a failing trial, so max achievable lift is 1.0/0.818 = **1.222× < 1.25×**. Unpassable by construction |
| within-task lift | **1.101×** | pooled 1.165× was partly restating task difficulty |
| harm rate | **53.1%** (266/501) | — |
| counterfactual veto net | **−31** (235 helped, 266 harmed) | veto correctly never granted |
| A3 extractor precision | **28/30** (25/27 strictly out-of-sample) | **PASS** — failure is the rule's, not the extractor's *in the false-positive direction only* |
| non-saturating task statistic | fired 0.463 vs unfired 0.275 = **1.682×** | fired tasks are *harder*; the "easier" reading was an artefact |

Superseded collided-key values, for the history section only: base fail 37.5% → **40.3%**;
traj lift 1.090× → **1.165×**; task lift 0.902× → **0.906×**; harm 59.1% → **53.1%**; veto
−91 → **−31**; ATTEMPTED_BUT_SUCCESS_UNKNOWN 55.6% → **83.3%**.

Reference noise floor: **28 records (1.4%, 12 tasks, retail only)** where the reference
requires a write, the trajectory shows none, and reward = 1.0. Not subtracted, not
relabelled. Crediting all 16 of these that RC1 fires on moves lift 1.165× → 1.202× — still
far below 1.50×.

### 3.5 Successor probe — class B/D

| rule | volume | within-task lift on the **deployable** outcome (reference FAIL) |
|---|---|---|
| ORACLE construct (a required write is missing) | 17.0% | **2.339×** |
| NULL rule (no successful write anywhere; no model) | 24.1% | **1.171×** |
| RC1 (the production detector) | 25.3% | **1.101×** |

Computed in one code path; the ORACLE and RC1 rows reproduce the independently published
figures, which is the check that the construction matches.

- The obligation extractor adds **0.2 precision points** over the null rule (40.2% → 40.4%
  at identifying a genuine oracle miss). Its measurable effect is volume suppression
  (24.1% → 8.4%): a sampler, not a detector.
- The obligation-derived features are **flat** across the right-reason/wrong-reason split
  (`n_obligations` −0.19, `n_unfired_obl` +0.05).
- The split is confounded: **agent identity** separates it (53.4% vs 33.4% gpt-4o) and it is
  mostly **between-task** (15 of 127 tasks appear on both sides).
- Corrective state was visible in a structured tool result before the first write in
  **12/12** oracle-confirmed harm cases.
- **The null rule was preregistered as disqualified**, not discovered here:
  `required_conjunct_scoping.md` §6.4 recorded label-blind that 22.1% of trajectories contain
  no write call and cited that volume as forbidding a veto.

**Conclusion, stated precisely:** the obligation extractor acted primarily as a traffic
suppressor rather than the source of signal, and RC1 **did not outperform** a no-model
behavioural check — ~~"landed below"~~, withdrawn 2026-10-02 (external reproduction): the
two lifts are computed on different task sets (80 vs 109) and NULL − RC1 = **+0.078
[−0.327, +0.575]** on paired task resamples, with neither rule distinguishable from 1.
The *construct* is not reducible to that check (oracle MH **2.054 [1.752, 2.530]** against
a null rule whose interval covers 1), so the failure is recovery, not abstraction — and
that part of the conclusion is the part the intervals support.

### 3.6 Mechanism dispositions — the audited denominator

This table exists because an earlier draft of this document compressed the project into
*"five mechanisms were frozen and tested; four failed"* without ever enumerating the five.
That arithmetic is **withdrawn**; see the note below the table.

Every candidate mechanism that could plausibly enter the denominator:

| # | mechanism | preregistered? | frozen pass/fail threshold? | evaluation surface | disposition |
|---|---|---|---|---|---|
| M1 | Repeated execution (R=5) | **Yes** — outcome space A–F frozen pre-spend (`repetition_study_predeclaration.md`) | **No.** The bands are explicitly *"thresholds for which paragraph gets written"*, not for a decision; no `r*` declared (§A1.9, lines 477–498) | Fresh inference (5,530 new calls) on an already-analysed corpus | **FAIL for the deployed configuration** — predeclared Outcome C fired ("both directions negligible") |
| M2 | Alternate-evaluator pairing / escalation | **Yes** — *pair selection* frozen on five pre-outcome criteria (`agent_reward_bench_gate1.md` §5) | **No.** Support was adequate for all 36 pairs, so it disqualified nothing; no recovery threshold and no `r*` were declared | Same corpus; selection frozen pre-outcome, analysis not held out | **WEAKENED / NO BINARY GATE** — 0.543 pooled (last of eight); operational analogue 0.366 / 0.465 |
| M3 | **R1** self-contradictory infeasibility claim | Yes | **No — directional only** (corrected 2026-10-02). §7: *"No accept/reject on accuracy, since they change no verdict… a rule whose firings are no more enriched for reference-fail than the corpus base rate carries no information and will be recorded as such."* No numeric bar, only a direction | Held out (1260 validation, 42 quarantined) | **FAILS ITS DIRECTIONAL CRITERION** — evidence half 0.51×, i.e. *inverted*: firings are less enriched for reference-fail than the base rate, the §7 no-information case stated explicitly; escalation half survives but is post hoc |
| M4 | **R2** negative self-report on imperative goal | Yes | Yes | Held out | **ACCEPTED BUT UNDERPOWERED** — 6 helped / 0 harmed, but lift 1.06× and harm bound 39.3% at n=6 |
| M5 | **R3** unverifiable image premise | Yes | Yes | Held out | **PASS** — both preregistered tests pass, both arms |
| M6 | **R4** terminal search-results route | Yes | **No — directional only** (corrected 2026-10-02), same §7 clause as M3 | Held out | **MET ITS DIRECTIONAL CRITERION** — 1.20× enrichment, above base rate. The ~~REJECTED~~ label this project published is **post hoc**: it rests on an evaluator-error contrast (16.1% on firings vs 15.5% elsewhere, p = 0.89) that §7 never named as a criterion. R4 is uninformative *about the evaluator* and application-specific; neither was a preregistered bar |
| M7 | **RC1** static required-conjunct / tool-class matching | Yes — `required_conjunct_preregistration.md` | Yes — A1 <15%, A2 ≥1.50× traj / ≥1.25× task, A3 ≥27/30 | **Fresh corpus**, read label-blind (~~"never touched"~~ — corrected 2026-10-02; files were read during scoping with `reward`/`info` withheld by code) | **FAIL** on A1 (25.3%) and A2-traj (1.165×); A2-task is an **INVALID GATE** (ceiling 1.222× < 1.25×); **A3 PASSES** 28/30 |
| M8 | Null rule ("no successful write anywhere") | Preregistered as **disqualified**, label-blind (`required_conjunct_scoping.md` §6.4) | Never granted a gate | Exploratory re-cut of the burned τ-bench data | **EXPLORATORY ONLY** — reported as a floor; fails volume on its own at 24.1% |

**Explicitly excluded from the denominator, with reasons:**
- *"A generic deterministic pre-check architecture"* (F5) is not a ninth mechanism — it is the
  class {M3…M6}. Counting it alongside its own members double-counts.
- Sequential stopping, adaptive allocation, and the blind escalation control are **class C
  synthetic** (§2). They were never tested against a real judge and cannot enter a count of
  empirical dispositions.
- The staged R=2→R=5 continuation gate was retracted before execution; it has no disposition.

**Why "four of five / sole survivor" is withdrawn.** Three independent defects:

1. **The five was never enumerated.** No five-item list exists in the repo. The nearest
   candidate denominator was *"the rules frozen before held-out or fresh validation"* —
   {R1, R2, R3, R4, RC1} — and on that set the count is **three failures, not four**.
   **Corrected 2026-10-02:** that set of five is not the set carrying *numeric gates* either.
   §7 of `repair_validation_preregistration.md` gives R1 and R4 no accept/reject threshold at
   all, only a direction. The gated set is **{R2, R3, RC1}, three rules**, and the two
   remaining Rs are directional. See item 4.
2. **"Sole survivor" contradicts this document's own §2 boundary rule 3.** R2's preregistered
   disposition is ACCEPTED and was deliberately *kept* accepted when a post-hoc metric
   undermined it. Two rules survived, not one. (RC1's extractor also passed its own A3 gate.)
3. **It converts underpowered into failed.** R2 is underpowered by its own harm bound, which
   is a statement about n=6, not a refutation.
4. **Two of the five were never gated** (added 2026-10-02, external reproduction). §7 of
   `repair_validation_preregistration.md` is explicit: *"**R1 and R4 (evidence, not vetoes).**
   No accept/reject on accuracy, since they change no verdict. Reported as firing precision
   against base rate."* Against that criterion R1 fails (0.51×, inverted — the §7
   no-information case) and **R4 passes** (1.20×, above base rate). R4's published
   ~~REJECTED~~ disposition came from an evaluator-error contrast the preregistration never
   named, which is the post-hoc move §2 boundary rule 3 forbids — the same error as the
   briefly-introduced `CONFOUNDED` label on R3, pointing the other way. The gated denominator
   is therefore **three, not five**, and ~~three~~ **four** of the seven rows above carry no
   numeric bar at all: M1, M2, and — added 2026-10-02 by the same §7 clause — M3 and M6.
   (Corrected 2026-10-03: the count said three while the parenthesis listed four rows, because
   M3/M6 were introduced together and got counted as the single edit that introduced them.
   They are two mechanisms, R1 and R4, and §3.6 gives them a row each. The 3 gated + 2
   directional + 2 ungated split that `check_synthesis_counts.py` derives from the table's own
   threshold column is unaffected — it never read this sentence.)

**The replacement summary, mechanically traceable to the table above:**

> Seven candidate assurance mechanisms were tested on real data. **Three** carried frozen
> numeric pass/fail gates evaluated on held-out or fresh corpora: **one failed** — RC1, on two
> of its three τ-bench gates — **one was accepted but is underpowered by its own harm bound**
> (R2, 39.3% at n=6), and **one passed** (R3, as an escalation signal that corrects nothing
> itself, and whose pooled reading was narrowed on 2026-10-02). **Two more (R1, R4) were
> preregistered with a direction but no threshold**: R1's firing enrichment came out inverted
> (0.51×) and R4's met its base-rate direction (1.20×) while carrying no evaluator-level
> signal. The remaining two had no criterion of any kind: repeated execution fired its
> predeclared negative outcome for the deployed configuration, and generic alternate-evaluator
> escalation had no gate to fail but weakened substantially once the operational conditional
> replaced the reference-conditioned one.

---

## 4. What the research killed

**F1 — Repetition as a production recovery mechanism.** *Killed, for this configuration.*
Majority-3 and majority-5 are both marginally worse than one call; 20 of 1,106 cases showed
any variation at all. **Scope: one judge (`aer`), one deployed config (temp 0.0 / seed 0),
one corpus, judge stage only — not full-pipeline, not other temperatures, not other judges.**

**F2 — Generic alternate-judge escalation.** *Heavily weakened.* Pooled recovery 0.543 was
dominated by the false-alarm stratum (130 of 162 errors). Missed-failure recovery is 0.469
on n=32. The operational analogue — the precision of overturns a policy would actually
perform — is 0.366 / 0.465, about ten points below the direction-matched figures (§3.2.1).
Blanket adjudication on the primary's FAIL verdict is a raw-count loss for five of the eight
candidates, and non-positive for all eight only at an error-cost weighting of ≥ 1.057×. And
post-hoc evaluator choice would have produced a 0.759 headline, a prettier and less honest
story.

**F3 — Structural diversity implies error diversity.** *Not supported.* The a-priori
independence argument (no shared model, no shared prompt lineage) did not predict measured
error correlation and ranked backwards. The eight alternates order by φ the same way they
order by their own sensitivity.

**F4 — Pooled φ as a mechanism-diversity indicator.** *Withdrawn.* Spread collapses 6.7× →
1.6× once conditioned on the reference label; the pooled odds ratio sits below the ref-fail
odds ratio for all eight and below *both* strata for three. Pooled φ was ordering alternates
on the stratum where the question does not arise.

**F5 — A generic deterministic pre-check architecture.** *Not supported.* Four rules, frozen
and held out: one rejected with an inverted signal, one rejected as uninformative about the
evaluator, one accepted but underpowered by its own bound, one accepted. A 50% held-out
failure rate at n=4 is not an architecture.

**F6 — Benchmark labels and metadata as deployable assurance inputs.** *Rejected where
oracle.* The `infeasible` substring in 84 workarena task IDs fully determines correct
behaviour; a judge scoring well with it demonstrates nothing. Class-A/B leakage assignment
became mandatory for every rule input.

**F7 — Static required-conjunct / tool-class matching.** *Rejected cross-corpus.* RC1 failed
both binding gates on a fresh corpus read label-blind, while its extractor passed at 28/30 — so
the rule, not the parsing, is what failed. Dominant mechanism F6_alt_tool (~242 firings): the
agent performed every required write using an action class RC1 had not frozen.

*Two qualifications on the "not the parsing" half, added 2026-10-02.* (a) Three of the 28
passing cases — 02, 06 and 16 — are cases whose extractor defects were found in pass 1 of the
same audit and fixed in Commit A2 before pass 2 scored them. Strictly out-of-sample the figure
is **25/27**. (b) A3 is a **precision** gate; its denominator is the 29 cases with extracted
obligations, and case 30 is scored CORRECT while containing two missed obligations. Recall is
unmeasured, so "not the parsing" is established against false positives and **not** against
under-extraction. F6_alt_tool is an execution-side mechanism and is unaffected by either
qualification; the general claim that parsing is exonerated is narrower than it reads.

**F8 — "Right for the right reason" as evidence for obligation modeling.** *Rejected as
causal evidence.* The 118-firing subset looks excellent in isolation (volume 6.0%, lift
2.02×, veto net +74) but it is oracle-selected, its obligation-derived features are flat, and
it is confounded by agent identity and task identity.

**F9 — More semantic machinery necessarily produces more useful assurance.** *Not supported,
with a caveat.* RC1's extraction pipeline **did not outperform** a one-line behavioural check
on the deployable outcome (~~"landed below"~~ withdrawn 2026-10-02: NULL − RC1 = **+0.078
[−0.327, +0.575]**, paired task resamples). **But the caveat is load-bearing, and unlike the
headline it survives being tested:** the *oracle* construct does beat the null rule, by
**+1.177 [+0.721, +1.687]** on the same paired resamples (2.339× vs 1.171× as point
estimates). So richer semantics are not worthless here — they were merely not recoverable
from production-visible inputs by this mechanism. Note that the oracle-vs-null ordering was
originally asserted from two bare point estimates on different task sets, exactly as the
withdrawn one was; it is kept only because the paired interval excludes zero.

---

## 5. What genuinely survived

**S1 — Predeclaration materially changes conclusions.** *Strong.* Measured, not asserted:
0.543 predeclared vs 0.759 post-hoc, a 21.6-point gap in a report that would have read
identically. The finding is doubly sharp because the *metric* was later shown to be the
wrong conditional too — the predeclared pair is tied first of eight on the stratum that
actually matters. Predeclaration is what made both errors visible. **This is one of the two
strongest findings in the project.**

**S2 — Separate the error directions.** *Strong.* False alarms and missed failures behaved
differently at every stage: 130 vs 32 in the stratum sizes, 0.562 vs 0.469 in recovery, and
opposite implications for whether adjudication pays. Pooled metrics obscured this three
separate times (pooled recovery, pooled φ, pooled lift). Durable production lesson.

**S3 — Measure the deployed configuration before designing around it.** *Strong.* The
repetition study was reframed at zero cost when gate verification showed all 1,106 cached
judgments carried temperature 0.0 / seed 0. Do not manufacture stochasticity in order to
study stochasticity.

**S4 — An explicit missing-evidence / UNVERIFIABLE state.** ~~*Supported, narrowly.*~~
**Downgraded to *supported only within one environment*, 2026-10-02.** R3 has held-out
support **as an escalation signal**: it identifies a 133-case subset where the evaluator errs
at ~~25.6% against 14.4% elsewhere~~ — superseded, that pair pools four benchmarks and all
133 firings are visualwebarena. Conditioned on slice the contrast is **25.6% vs 19.7%
(34/133 vs 31/157), Fisher p = 0.26**: +5.8 pp of the +11.2 pp survives, +5.4 pp was slice
identity (§3.3.1; `scripts/arb_r3_slice_check.py` sections 4–5). Phrase with **five**
qualifiers now: it identified a higher-error subset *within visualwebarena*; the separation
is not significant once stratified; it **did not autonomously correct** any case; **99 of the
133 it escalated were already correct**; its value therefore depends entirely on review cost.
It is not a general assurance architecture. Note also that R3 survived partly because its
claim is the weakest of the four — it asserts an evidence gap rather than a verdict, which
is a lower bar to clear.

The residual that survives conditioning sits on one side of the error axis. Among
reference-fail cases the only available judge error is a missed failure, and there R3's
firings err at **25.3% (22/87) vs 15.8% (18/114), +9.5 pp, Fisher p = 0.1099**; among
reference-success cases, where the only available error is a false alarm, the sign reverses:
**26.1% (12/46) vs 30.2% (13/43), −4.1 pp, p = 0.8139**
(`scripts/arb_r3_slice_check.py` section 6). So the surviving residual **sits on the
missed-failure side** (exploratory, p = 0.11) and reverses sign on the false-alarm side. That
is a statement about where the residual is, not about what S4 is supported for: neither stratum
is significant, and the split was chosen after the pooled reading failed. (This read ~~"what S4
is supported for is surfacing missed failures in an image-dependent environment"~~ until
2026-10-03, which converts an exploratory p = 0.11 into a licensed use — the same move, one
rung down, as the pooled reading this paragraph exists to replace.) See §3.3.1 for the three
readings it does not license.

**S5 — Evidence availability matters before evaluator sophistication.** *Well supported
qualitatively, n=15.* Only 5 of 15 unresolved cases fail first at the evaluator's reasoning;
5 fail at representation (an image premise the judge was never shown), 4 at specification, 1
at the reference label. A better judge is the wrong lever for two-thirds of them.
Independent support comes from R3 (§3.3), which is the same phenomenon in preregistered,
held-out form: a 133-case subset defined by an absent image premise, where the evaluator errs
at ~~25.6% against 14.4% elsewhere~~ **25.6% against 19.7% within visualwebarena, the slice
all 133 firings come from (p = 0.26; the pooled 14.4% comparison is superseded 2026-10-02,
§3.3.1)**. The direction split is the part that bears on S5: the residual is entirely on the
missed-failure side (25.3% vs 15.8%, +9.5 pp, p = 0.1099), which is what an absent image
premise should produce — the judge cannot see the evidence that would reveal the failure.
Both strata are underpowered and the split is exploratory;
see `scripts/arb_r3_slice_check.py` section 6.

> **Correction applied during this audit.** An earlier draft cited as independent support
> that *"the benchmark holds a task-type label and an infeasibility flag and passes neither to
> the judge,"* plus the unparsed `<side>` tags. All three legs fail against
> `production_signal_audit.md`: the benchmark holds **no task-type column** (§C2 — task type
> is class **C**, derivable from goal text imperfectly, and §4 shows the obvious lexical
> approach fails on noun/verb ambiguity); the infeasibility signal is class **D** authoring
> metadata that exists only as a substring of the task id, and passing it to a judge would be
> **oracle leakage** (§3, the recommendation is withdrawn there); and the `<side>` tags are
> class **E → rejected** for construct mismatch, being largely a restatement of the
> `<optimal>` tag from the same response (§7). This was a resurrection of a claim the repo had
> already corrected in place at `shared_unresolved_case_review.md` §10 and §13. **It is worth
> recording that the project searched for instances of "the evidence exists and is simply
> discarded" and its two most attractive candidates did not survive audit** — which is a
> constraint on §7's maxim, not support for it.

**S6 — Cheap baselines must precede semantic machinery.** ~~*Strong, newly sharpened.*~~
**Downgraded to *methodological, not empirical*, 2026-10-02.** Three instances were claimed:
a fifteen-line stopping rule captured 100% of the available cost saving that allocation was
built to capture (synthetic); a blind hash-based escalation control dominated the candidate
policy on one fixture (synthetic); and a no-model "did the agent write anything" check
~~out-performed~~ **matched** RC1's extraction pipeline on real fresh data (+0.078 within-task
lift [−0.327, +0.575], paired task resamples — **no ordering supported**).

The two synthetic instances are class C and cannot carry weight alone; the previous version of
this paragraph said so explicitly and rested the finding on the third. **That third instance
no longer orders the two rules.** What survives is weaker and differently shaped: a no-model
check *did as well as* a mechanism costing an extraction pipeline, on one corpus, with both
indistinguishable from no effect. That is a real reason to run the cheap baseline first — it
would have told you the expensive one was not needed — but it is a statement about what you
learn from running the baseline, not a measured win for the baseline. Stated as an empirical
claim about effect sizes, S6 has **one corpus and no significant comparison** behind it.

**S7 — Complexity must earn its cost.** *This is the candidate central thesis; see §6.*

---

## 6. Red-team: the central thesis

> **Candidate:** Sophisticated evaluator-control mechanisms repeatedly failed to earn their
> complexity; simpler evidence and behavioral checks often explained as much or more.

**Attack 1 — Is this a consequence of the chosen datasets?** *Partly yes, and it must be
conceded.* Two corpora. AgentRewardBench's nine "judges" are not nine mechanisms: `functional`
is not an LLM at all (verdict is `cum_reward > 0.5`), the eight LLM judges share only two
representation tiers, and none receives a screenshot. τ-bench is two domains and 165 tasks.
A corpus with genuinely diverse evaluators might show complementarity this one cannot.

**Attack 2 — Cherry-picking negatives?** *No, and the record defends itself.* R3 was accepted
on held-out data. R2 was accepted as preregistered and *kept* accepted even after a post-hoc
metric undermined it. The oracle construct was upheld today against a null rule that a
cherry-picking author would have let win. The dispositions were frozen before outcomes.

**Attack 3 — Did any sophisticated method actually help?** *No — and that is a problem for
the thesis, not support for it.* R3, which had the cleanest pass, is also the simplest:
two conditions and a configuration lookup. (R2 was accepted but remains underpowered.)
So the dataset contains **no instance of a sophisticated method helping**, which means
the project never observed the contrast its thesis asserts. It observed only that
several mechanisms failed and the simplest held-out rule cleared its threshold.

**Attack 4 — Is "complexity" defined after the fact?** *Yes. This is the fatal objection to
the thesis as worded.* Nothing in the repo operationalises complexity. R1, R3 and R4 are
comparable in implementation complexity — a few conditions over production-visible fields —
yet R1 and R4 were rejected and R3 accepted. Complexity does not separate them. What
separates them is **what they claim**: R3 asserts an evidence gap and escalates; R1, R2 and
R4 assert something about the outcome. A thesis about complexity is fitting the wrong
variable.

**Attack 5 — Are the simple baselines genuinely strong, or correlated with task difficulty?**
*Neither, exactly — they are partly constitutive, and on τ-bench not demonstrably strong at
all.* The task-difficulty version of this attack fails on its own terms: the null rule's lift
is measured *within task*, so it is not restating which task was drawn. But the premise is
weaker than it was: as of 2026-10-02 the null rule has **no measured advantage** over RC1
(+0.078 [−0.327, +0.575]) and its own lift does not separate from 1 (MH 1.237 [0.904, 1.650]),
so "genuinely strong" is not established for it either. And a deeper version of the attack
lands: "the agent performed no state-changing action" and
"the task requiring a state change was not completed" substantially overlap in meaning. The
null rule is best read as a **floor** that a detector must clear, not as a clever baseline.
That is exactly how the first draft of the successor probe went wrong, and the 7.189× figure
it produced has been withdrawn.

**Attack 6 — Does the null-rule result generalize beyond τ-bench?** *Unknown, and there is no
evidence for it.* One rule, one corpus, one construct.

**Attack 7 — "Failed to validate" vs "does not work"?** *The project repeatedly measured the
former and must not claim the latter.* R2's harm bound is 39.3% at n=6. The missed-failure
stratum is n=32. The RC1 harm sample is 15 cases. Several of these mechanisms are
underpowered rather than refuted.

### Rewritten at the narrowest defensible level

> **Across two public agent-evaluation corpora, seven candidate assurance mechanisms were
> frozen and tested on real data. Of the three carrying numeric pass/fail gates on held-out or
> fresh corpora, one failed (RC1, on two of three gates), one was accepted but is underpowered
> by its own harm bound (R2), and one passed (R3); of the two carrying a preregistered
> direction but no threshold, R1's firing enrichment came out inverted and R4's met its
> direction while carrying no evaluator-level signal; of the two preregistered without any
> criterion, repeated execution fired its predeclared negative outcome and alternate-evaluator
> escalation weakened substantially. In
> every failure a cheaper measurement — a single judge call, a verdict-conditioned rate, or a
> check requiring no inference at all — accounted for as much of the signal as the mechanism
> did. The one rule that passed its numeric gate cleanly — R2's acceptance was underpowered —
> was also the cheapest, and the only one that reported an
> evidence gap instead of asserting a verdict — but its pooled reading was narrowed on
> 2026-10-02 (all 133 firings are visualwebarena; within-slice 25.6% vs 19.7%, p = 0.26), so
> it is unproven rather than a positive result.**

That final clause is the part the evidence actually supports, and it is a claim about
**what a mechanism asserts**, not about how complex it is. "Complexity must earn its cost"
survives as a *heuristic the project adopted*, not as a finding it demonstrated.

---

## 7. Red-team: the production maxim

> **Candidate:** Before buying more inference, ask whether the required evidence exists and
> whether a cheaper observable already carries the signal.

**Supporting instances.** (a) The repetition study's entire premise was answerable for free:
inspecting 1,106 cached judgments showed temperature 0.0 / seed 0 with no variation, before
any API call. (b) 10 of 15 unresolved cases fail before the evaluator's reasoning — for those,
more judging cannot repair missing evidence. (c) The null rule carried ~~more of~~ **as much
of** the deployable signal as RC1's extraction pipeline, at zero inference cost — corrected
2026-10-02; the ordering is withdrawn (+0.078 [−0.327, +0.575]) but the maxim does not need
it, since "as much for free" is already the whole point. (d) R3's entire content is
"the required evidence is absent", and it is one of the two rules accepted on held-out
validation — ~~the stronger of the two~~ the one that cleared a numeric gate cleanly, R2 having
been accepted underpowered (corrected 2026-10-02; "stronger" compared a gate pass against an
underpowered acceptance as if they were two points on one scale, and it was written before the
slice audit cut R3's separation to +5.8 pp, p = 0.26). The maxim stands on the *content* of the
rule — that a cheap observable answers the question — not on the size of its separation.

**A supporting instance that was audited away, and should be recorded as such.** An earlier
draft listed as instance (e) that *"the benchmark withholds a task-type label and an
infeasibility flag from the judge — evidence that exists and is simply not passed."* Both
halves are false: there is no task-type field (it must be inferred from goal text, class C,
imperfectly), and the infeasibility signal is class-D authoring metadata whose use as a judge
input would be oracle leakage. The maxim's most quotable illustration — *free evidence is
lying around unused* — is the one thing this project looked for and **did not** find. What it
found instead was that the cheap observable usually has to be **derived**, and that deriving
it is where the cost reappears.

**Counterexample, and it is real.** The project tried to act on this maxim and it backfired:
the staged R=2→R=5 continuation gate existed precisely to avoid buying ~$35 of inference, and
it required two amendments and a full retraction, having smuggled a disavowed constant back
in and relied on an IID bound to gate the study that existed to measure independence. The
repo's own precommitted conclusion: *"the engineering and methodological cost of the gate
exceeded the $35 it was designed to save."*

**Verdict: survives, with a mandatory rider.**

> Before buying more inference, ask whether the evidence exists and whether a cheaper
> observable already carries the signal — **then, if the answer is unclear, just buy the
> evidence.** Asking is free; building machinery to avoid a small spend is not.

This should be the headline practitioner lesson. It is the one claim supported by every
phase of the project, including the phase where following it naively went wrong.

---

## 8. Novelty assessment

**Established prior art, conceded by the repo itself** (`architecture.md` §10.1, written
`4e8b327` before the real-data work): LLM-judge nondeterminism and verdict instability;
self-consistent wrong answers; item-level difficulty heterogeneity; correlated evaluator
errors; inefficiency of fixed-N evaluation; adaptive sampling and sequential stopping;
cheap-to-expensive evaluator cascades; selective human escalation; value-of-information and
sequential decision theory; mutation testing of evaluators; calibration and interval
estimation; benchmarking evaluators against human labels with per-judgment cost accounting
(AgentRewardBench itself, arXiv:2504.08942, and ATFD); and paired significance testing
between evaluators (McNemar's test). The note states: *"If a future document describes any of
these as a finding of this project, that document is wrong."*

**Novel empirical results (measured here).** Modest but real:
1. The k-distribution of a specific deployed judge at temperature 0 over 5 repetitions, with
   majority-3 and majority-5 both measured as *non-improving* in both error directions.
2. A measured effect size for evaluator-pair selection bias on a public corpus: 0.543
   predeclared vs 0.759 post-hoc.
3. A measured gap between reference-conditioned recovery and operational overturn precision
   on the same data: direction-matched, 10.3 pp on the missed-failure side and 9.7 pp on the
   false-alarm side for the predeclared pair; across eight alternates always positive on the
   false-alarm side (+9.7 to +46.0 pp) and sign-varying on the missed-failure side.
4. A null-baseline comparison showing a semantic detector **failing to outperform** a
   no-model check on the deployable outcome — NULL − RC1 = +0.078 [−0.327, +0.575] on paired
   task resamples, with neither rule distinguishable from 1 under Mantel–Haenszel
   stratification. ~~"landing below"~~ withdrawn 2026-10-02; the null result is the finding,
   the ordering was not.

None of these is a new *method*. Each is a number on a public corpus that, as far as the repo
records, had not been published — a claim about this repository's search, not an assertion
about the literature, and it should be worded that way.

**Novel synthesis (the actual contribution).** A disciplined sequence of production-shaped
experiments showing which evaluator-assurance mechanisms fail to earn their complexity under
realistic cost and data constraints — with the preregistration, quarantine, negative
controls, and corrections all preserved in the commit record. **This is a credible
contribution and it does not require inventing anything.** Its value is in the method and the
honesty of the trail, not the mechanisms.

**Not claimable:** any architectural novelty; any general result about LLM judges; the
planner as a research contribution.

---

## 9. Publishable claim ledger

| # | proposed claim | strongest evidence | class | scope | caveat | publishable wording | forbidden stronger wording |
|---|---|---|---|---|---|---|---|
| C1 | Repeating this judge does not help | R=5, 1,106 cases, 5,530 calls, outcome C | A | one judge, temp 0/seed 0, judge stage only | not full-pipeline; provider nondeterminism not excluded | "On 1,106 AgentRewardBench trajectories, five repeated executions of this deployed judge produced intermediate correctness on only 20 cases, and majority-of-3 and majority-of-5 were both marginally worse than a single execution." | ~~"LLM judges are deterministic"~~ / ~~"repetition doesn't work"~~ |
| C2 | Sequential stopping gets the same verdicts cheaper | first-to-3: 0 verdict mismatches (by construction), −39.7% calls (2,194 saved of 5,530; 3,336 used) | A | same corpus | textbook method, not ours; the 0 mismatches are an identity — first-to-3 and majority-of-5 cannot disagree once three of five agree — so only the call saving is empirical | "First-to-3 stopping used 39.7% fewer calls at verdicts identical to majority-of-5 by construction — the two cannot disagree once three of five agree, so only the call saving is empirical." (~~"reproduced majority-of-5 verdicts exactly while using 39.7% fewer calls"~~: corrected 2026-10-03. This cell's own caveat column said by-construction and its publishable wording did not) | ~~"we developed an adaptive evaluation method"~~ / ~~"39.8% fewer calls"~~ (a hardcoded literal, not a rounding; corrected 2026-10-02) / ~~"3,336 of 5,530 is 39.7%"~~ (inverted — 3,336 is the count *used*; the saving is 2,194/5,530. Prophylactic, not historical: `git grep` against `origin/main` finds that fraction in no document. It is barred because the count and the percentage were printed adjacently with no denominator, which is the derivation a reader was left to make) |
| C3 | Predeclaration changed the result | 0.543 vs 0.759 | A vs B | 8 candidate pairs, one corpus | post-hoc figure is oracle selection by construction, and 0.759 is tied between two alternates (123/162) with differing φ | "The pair chosen on preregistered criteria ranked last of eight on pooled recovery (0.543); post-hoc selection would have reported 0.759 — a figure two of the eight reach — in a document that read identically." | ~~"post-hoc evaluator selection inflates results by 22 points"~~ (n=1 corpus) / ~~"the post-hoc best pair"~~ (there are two) |
| C4 | Reference-conditioned recovery is not operational | direction-matched: 0.469 vs 0.366 (10.3 pp) and 0.562 vs 0.465 (9.7 pp) | B | one primary, 8 alternates | exploratory; general on the false-alarm side, sign-varying on the missed-failure side | "P(alternate correct \| primary wrong) was 0.543, while the precision of the overturns a policy would actually perform was 0.366 and 0.465; matched by error direction the deployable quantity ran 10.3 and 9.7 points lower." | ~~"escalation policies overstate benefit by 30%"~~ / ~~"the deployable quantity ran 20–30 points lower"~~ (pooled across error directions; corrected 2026-10-02) |
| C5 | Error directions must be separated | 32 vs 130; 0.469 vs 0.562; pooled φ 6.7×→1.6× | B | one corpus | exploratory | "False alarms outnumbered missed failures 130 to 32, recovery differed by direction, and conditioning φ on the reference label collapsed the spread across eight alternates from 6.7× to 1.6×." | ~~"pooled metrics are invalid"~~ |
| C6 | Deterministic pre-checks did not generalize as a class | R1–R4 held out on 1260 | A | 4 rules, one corpus | n=4; only R2 and R3 carried numeric gates (§3.3.3); R2 underpowered at n=6 | "Of four deterministic pre-checks frozen before validation, two carried numeric gates: one was accepted but underpowered by its own harm bound (39.3% at n=6) and one passed as an escalation signal. The other two carried a preregistered direction and no threshold: R1's firing enrichment inverted (0.51×), R4's met its direction (1.20×) with no evaluator-level signal." | ~~"deterministic guards don't work"~~, ~~"two of four failed"~~ |
| C7 | A denied veto is worth logging | R1: lift 0.51×, counterfactual 6 helped / 14 harmed | A | one rule | single instance | "R1's signal inverted on held-out data (0.51× lift); the veto it had been deliberately denied would have helped 6 cases and harmed 14." | ~~"never let rules veto"~~ |
| C8 | Evidence-gap escalation has held-out support **within one environment** | R3: within visualwebarena **25.6% vs 19.7% (34/133 vs 31/157), p = 0.26**; pooled 25.6% vs 14.4% (p = 0.0015) superseded as the headline 2026-10-02 | A (pooled test, preregistered) + B (the stratification and direction split, post-hoc) | one rule, **all 133 firings visualwebarena**, so the pooled comparison is largely one slice against three easier ones | 99/133 escalated were already correct; corrects nothing itself; the surviving separation is not significant, and the residual sits entirely on the missed-failure side (25.3% vs 15.8%, p = 0.11) while the false-alarm side reverses sign (26.1% vs 30.2%, p = 0.81) | "R3 identified a 133-case subset where the evaluator erred at 25.6% against 19.7% on the rest of the same benchmark (Fisher p = 0.26); it escalates rather than corrects, and 99 of the 133 were already right." Counts and p-values: `scripts/arb_r3_slice_check.py` | ~~"UNVERIFIABLE states improve evaluation"~~ / ~~"R3 identified a 133-case subset where the evaluator erred at 25.6% against 14.4% elsewhere"~~ (this row's own former wording — the pooled pair with no within-slice pair beside it; superseded 2026-10-02) |
| C9 | Static tool-class matching failed on a fresh corpus | RC1: 25.3% volume, 1.165× lift, extractor 28/30 | A/FRESH | one rule, 2 domains | 28-record reference noise floor | "On the fresh τ-bench validation, static required-conjunct/tool-class matching did not meaningfully enrich failures within tasks (1.101× within-task), while its extractor passed a label-blind precision audit at 28/30 — 25/27 held strictly out-of-sample, with recall unmeasured." | ~~"obligation tracking does not work"~~ / ~~"the parsing is exonerated"~~ (A3 bounds false positives only) |
| C10 | The detector, not the construct, failed | oracle 2.339× vs RC1 1.101×, precision 33.1% / recall 49.3% | D + A | τ-bench | oracle ceiling forecasts nothing about any detector; oracle itself fails the volume gate at 17.0% | "Reconstructed with benchmark-authoritative actions, the target construct carried a 2.339× within-task lift that the production rule recovered at 33.1% precision and 49.3% recall. The oracle establishes that the latent construct carries signal; it does not establish that a production-valid representation of it exists." | ~~"the construct is validated"~~ / ~~"2.339× is achievable"~~ / ~~"representation failure, not an empty abstraction"~~ |
| C11 | The rule did not outperform a no-model baseline | NULL − RC1 = **+0.078 [−0.327, +0.575]** on paired task resamples; MH by task, null **1.237 [0.904, 1.650]** vs RC1 **1.150 [0.979, 1.352]**; same code path | B | τ-bench | null rule itself fails volume at 24.1% and was preregistered as disqualified; partly constitutive of the outcome; the bare lifts sit on **different task sets** (80 vs 109) and support **no ordering in either direction** | "A check requiring no obligation model — 'did the agent successfully write anything?' — did no worse within-task than the extraction-based rule, and neither is distinguishable from no effect." | ~~"semantic machinery is useless"~~ / ~~"the null rule is a better detector"~~ / ~~"The rule fell below a no-model baseline — 1.101× vs null 1.171×"~~ (this row's own former wording, superseded 2026-10-02) |
| C12 | Most judge failures originate before the judge | 10 of 15 fail earlier | E | n=15, selected | qualitative, small, not random | "In a 15-case review, only 5 failed first at the evaluator's reasoning; 5 failed at representation and 4 at specification." | ~~"most evaluator errors are data problems"~~ |
| C13 | A join bug can survive into a published report | 660/1980 records (33.3%) mis-joined | — | one incident | self-reported | "A reward join keyed on three of four identity fields silently scored 33.3% of records against the wrong agent's outcomes; it was found by tracing a single row the classifier could not emit." | ~~"benchmark data is unreliable"~~ |

---

## 10. Research-process failure audit

**Counting rule, stated before the table.** The `caught` column has exactly two values.
**BEFORE** means the error was found while the outcomes of the experiment or analysis it
would have affected were still unavailable — before real data existed, before inference was
purchased, or before a validation arm was scored. **AFTER** means it was found only once
those results were in hand. This is a single axis. An earlier draft mixed it with a second
axis (*before or after publication*), which is how the aggregate count came out wrong; the
publication detail now lives in the effect column, where it cannot be counted twice.

**Second counting rule, added 2026-10-02.** The `origin` column is the other axis, and it is
kept separate for the same reason. **internal** means the error was found by this project — by
a red team, a freeze, a gate check, or one of its own audits. **external** means it was found
by the independent end-to-end reproduction of 2026-10-02, reading this repo's published
output. Rows 1–13 are internal, rows 14–24 external. Summing the two gives 24, but 24 is not a
number this document quotes on its own: *what the project caught about itself* is 13, and that
figure did not change when the reproduction landed. Any sentence that gives the sum has to
name both parts. `scripts/check_synthesis_counts.py` parses this table and asserts the
internal triple and the external count separately against the prose below, so none of the four
figures can drift.

| # | error | how detected | caught | origin | effect on conclusions | safeguard |
|---|---|---|---|---|---|---|
| 1 | Alternate-evaluator performance assumed from two float literals (0.95 / 0.05) | Red team asked where the numbers came from | BEFORE — no real data yet | internal | Every synthetic escalation economic result was modelled, not measured | Type is unconstructible without a named artifact or explicit `assumed_because`; refusal fires at point of use |
| 2 | `MIN_ERRORS_FOR_CONDITIONAL = 16` presented as derived | Two-corpus red team traced the derivation to an undeclared 0.5 | BEFORE | internal | Sample-size guidance was wrong by up to 30× (3 errors vs 91, depending on `r*`) | Constant demoted to a presentation warning carrying no verdict |
| 3 | The 0.50 sufficiency rule | Same red team | BEFORE | internal | An economic assumption was printed in the register of a statistical convention | `r*` declared by the caller; no default; absent it, output is NOT DECISION-SUFFICIENT |
| 4 | Pooled recovery used as the headline | Directional decomposition | AFTER | internal | Published in the pooled complementarity report, then corrected. The metric conditioned on a label no runtime system has; it ranked the predeclared pair last on a stratum that was 80% false alarms | Always decompose by error direction before reporting a pooled rate |
| 5 | Pooled φ read as mechanism diversity | Conditional analysis | AFTER | internal | Ranked eight alternates on the stratum where the question does not arise | Check whether one margin dominates one stratum before trusting any 2×2 |
| 6 | Prompt-caching assumed to invalidate repetitions | Re-reading the caching mechanism | BEFORE — pre-inference | internal | Would have disabled caching and raised cost ~26% for no reason | Verify the mechanism before writing a constraint that depends on it |
| 7 | Staged R=2→R=5 continuation gate | Third amendment red team | BEFORE — pre-inference | internal | Would have stopped collection at R=2 and reached the same conclusion by extrapolation instead of measurement | Prefer the unconditional design; keep screens as retrospective analysis, never as control flow |
| 8 | Infeasibility flag nearly used as a rule input | Oracle-leakage audit | BEFORE — pre-validation | internal | Would have produced a rule that "worked" by being told the answer | Leakage class assigned to every input before freezing |
| 9 | A2-task gate preregistered at an unreachable threshold | Post-outcome ceiling computation | AFTER | internal | Published in the first RC1 report as a binding gate. A binding gate could not have been passed by any rule; also inverted the direction of the "fired tasks are easier" reading | **Compute a metric's ceiling before preregistering its threshold**; prefer non-saturating statistics |
| 10 | τ-bench join-key collision | One impossible row in a qualitative sample | AFTER | internal | **The most consequential of the thirteen: already published in the first RC1 report.** 33.3% of records scored against the wrong agent; six published figures wrong | Assert the join is 1:1 on the full identity tuple; a row your own classifier cannot emit is never an edge case |
| 11 | F4 named dominant harm mechanism | Forensic re-audit on corrected data | AFTER | internal | Published in the post-outcome decomposition. An overcorrection drawn from the collided sample; F6 is dominant | Re-derive every mechanism claim after a data-integrity fix, not just the headline metrics |
| 12 | "Right for the right reason" read as support for obligation modeling | Null-rule probe + confound check | AFTER | internal | Caught before it was published as support. Would have licensed a successor on an oracle-selected, agent-confounded subset | Run the null baseline before crediting a mechanism |
| 13 | **Null-rule headline compared two different outcome variables** | Like-for-like recomputation during this synthesis | AFTER | internal | Caught pre-publication. Would have published "null rule beats the construct 7.189× to 2.339×" — false, and it would have wrongly narrowed a correct finding | **Recompute every compared statistic in one code path and prove the path by reproducing an independently published number first** |
| 14 | Call saving from first-to-3 stopping hard-coded as 39.8%, printed beside the count of calls *used* with no denominator | External reproduction recomputed it from the raw calls: majority-of-5 makes 5,530 calls, first-to-3 **uses** 3,336, so the saving is the 2,194 not made — 2,194 / 5,530 = 39.67% | AFTER — external reproduction, post-publication | external | 39.8% was published in five prose documents (`README.md`, `FINDINGS.md`, `canonical_copy.md`, `repetition_study_findings.md`, this file), three scripts and two site components. The 0.1 pp error changes no conclusion. The pairing is the worse half: `arb_repetition_analysis.py` printed `~3336 calls … (39.8% saving on call count)` on one line, and §12 of `repetition_study_findings.md` copied the pair into adjacent table cells, so the only two numbers a reader had were a count and a percentage of an unnamed base — and 3,336/5,530 is 60.3%. ~~"Several documents wrote '3,336 of 5,530 is 39.7%'"~~ and ~~"six repo documents"~~: corrected 2026-10-03, this row overstated its own defect. No document ever wrote that fraction out; `git grep` against `origin/main` finds 3,336 in exactly one file | A reported figure must be emitted by the script that computes it; `arb_repetition_analysis.py` now prints the saving rather than carrying a literal, and prints calls-used and calls-saved as separate labelled quantities. A percentage printed next to a count must name its own denominator |
| 15 | Cases terminating at 3 calls published as 99.4% | Same reproduction, from the script's own call distribution: (805 + 289) / 1,106 = 98.9% | AFTER — external reproduction, post-publication | external | Overstated how often sequential stopping terminated early. The correct value was already in the script's output and the prose did not match it | Same as 14. A distribution printed by the script and a percentage typed into prose are two numbers, and only one of them was checked |
| 16 | $46.18 reported as the study's cost | Reconciliation of analysed calls against billing | AFTER — external reproduction, post-publication | external | Understated spend by $3.32: 356 duplicate valid calls were billed but not analysed. "Cost of the study" and "cost of the analysed calls" are different quantities and the text used one word for both | Report billed and analysed spend as separate figures; never let the cheaper one stand in for the total |
| 17 | "Operational precision is 20–30 points lower" for the predeclared pair | Recomputation matched within each error direction | AFTER — external reproduction, post-publication | external | Published. Compared *pooled* recovery against *directional* precision — the same incompatible-conditional error as items 4, 5 and 13. Direction-matched, the gaps are 10.3 pp and 9.7 pp, and the missed-failure-side gap is **negative** for two of eight alternates | **Fourth instance of one error class in this project.** Never subtract two rates unless both condition on the same thing, and state the sign range across alternates rather than a single span |
| 18 | "Blanket adjudication is non-positive for all 8 pairs" | Raw-count exchange recomputed at equal error costs | AFTER — external reproduction, post-publication | external | False as stated: the raw exchange is positive for three alternates (+4, +5, +1). The claim holds only if a missed failure is weighted ≥ 1.057× a false alarm — a condition `FINDINGS.md` had dropped entirely | A claim that holds only under a cost weighting must carry the weighting in the same sentence, not in a neighbouring document |
| 19 | Post-hoc best recovery 0.759 attributed to a single alternate | Reproduction enumerated all eight | AFTER — external reproduction, post-publication | external | Two alternates reach 123/162, so "the post-hoc best pair" does not exist. The preregistration finding is unaffected; the figure was nonetheless presented as a unique maximum | Check whether an extremum is unique before naming it, especially when the point of the claim is that selection was arbitrary |
| 20 | "RC1 fell below a no-model baseline" | Paired task-resample and Mantel–Haenszel recomputation | AFTER — external reproduction, post-publication | external | Published. The three lifts were computed on **different task sets** (oracle 94, null 80, RC1 109). Paired, NULL − RC1 = +0.078 [−0.327, +0.575] and neither rule is distinguishable from 1. A tie was published as a loss — an error in the direction that made the project's own result look worse | Two point estimates are not a comparison. Pair or stratify, and publish an interval on each side before asserting an ordering |
| 21 | τ-bench described as "never touched" before the RC1 preregistration | Reproduction read §8.4 of the repo's own scoping document | AFTER — external reproduction, post-publication | external | The corpus was read label-blind during scoping with `reward`/`info` withheld in code — a weaker and accurate claim the repo had already written down. The protocol was sound; the description of it was not | Describe a blind by the artefact that enforced it, never by a superlative. The superlative is the part a reader cannot check |
| 22 | A3's 28/30 cited as proof that the rule, not the parsing, failed | Reproduction traced the three pass-1 fixes back into the audit sample | AFTER — external reproduction, post-publication | external | Cases 02, 06 and 16 were fixed during pass 1 and then scored CORRECT in that same 30-case sample. Strictly out-of-sample the figure is 25/27, and A3 bounds false positives only — recall is unmeasured | An audit that fixes what it finds must report the out-of-sample figure beside the headline, and a precision gate must not be cited as an exoneration |
| 23 | R1 and R4 counted as gated mechanisms; R4 labelled REJECTED | Reproduction read §7 of the repair preregistration | AFTER — external reproduction, post-publication | external | §7 gives R1 and R4 a direction and **no accept/reject bar**. R4 *met* its direction (1.20×); its published REJECTED label was decided after the fact on an evaluator-error contrast §7 never named. The project's own negative-result count was inflated from one gated failure to three | `check_synthesis_counts.py` now derives the 3 + 2 split from §3.6's own threshold column. A disposition may not be asserted without quoting the criterion it was judged against |
| 24 | **R3's preregistered escalation test pooled across benchmarks when all 133 of its firings sit in one** | Reproduction asked which slice the rule fires in | AFTER — external reproduction, post-publication | external | **The most consequential of the eleven: it was the project's one clearly positive held-out result.** +5.8 pp of the +11.2 pp separation survives conditioning on slice (p = 0.26), and the residual sits only on the missed-failure side. The hazard was named in a single line — in the **post-results** caveat in `repair_validation_results.md`, not in the preregistration, and that caveat says "the preregistration should have said so" — and the check was never run. Writing the objection down after the numbers, then publishing **ACCEPTED** two paragraphs later, is worse than not having seen it | Stratify every fired-vs-unfired contrast on the covariates that vary across the corpus. A held-out split does not control a confound that lives in a covariate — see the methods note in §3.3.1 |

Item 13 deserves emphasis because of what it repeats. The probe document had *already listed*
"these were not recomputed side-by-side from a single code path" in its own limitations
section — and then headlined the comparison anyway. This is the same class of error as items
4 and 5 (a rate compared against the wrong conditional), committed immediately after
documenting it. The project's own recurring lesson is that **naming an error does not
inoculate you against it**; only re-auditing the new work against the last correction does.

**Candidate theme wording.** *"Assurance research itself needs assurance"* is accurate but
too cute, and it overclaims by implying a general programme. The defensible version:

> ~~Thirteen process errors were found across 62 commits. **Six** were caught before the
> outcomes they would have affected were visible — by red teams, freezes and pre-inference
> gate checks. **Seven** were caught only afterwards, and the most damaging of those had
> already been published: a join-key collision that scored a third of the records against
> the wrong agent.~~ The mechanisms that caught them are the ordinary ones: predeclaration,
> quarantine, negative controls, and recomputing a comparison in a single code path.
>
> **Partly superseded 2026-10-02 — the strike is narrower than it looks.** The struck
> sentence's three figures are *still correct for the internal audit*, which is what it was
> counting; it is struck only because it read as the project's whole error record and no
> longer is. An external reproduction added eleven more (rows 14–24), every one of them in the
> "caught afterwards" column. The replacement below keeps the two populations apart rather
> than restating 13 / 6 / 7 as a larger triple.

**Current counts, derived from the table above — two figures, not one.**

**Internal: 13 process errors** found by this project's own safeguards and audits (rows 1–13).
**6** were caught before the outcomes they would have affected were visible — by red teams,
freezes and pre-inference gate checks. **7** were caught only afterwards, and the most damaging
of those had already been published: a join-key collision that scored a third of the records
against the wrong agent. This triple is unchanged by the reproduction, because the reproduction
did not find anything the project had already found.

**External: 11 process errors** found by an independent end-to-end reproduction on 2026-10-02
(rows 14–24), none of them caught by any safeguard in this repo, and **all eleven already
published** in its public documents when they were found.

Stated as a sum: **13 found during the study, 11 more by external reproduction**, 24 numbered
rows in the table. The sum is reported this way deliberately. "24 process errors, 6 before and
18 after" is arithmetically true and misleading in both directions — it inflates what the
project's own machinery detected and it buries the finding that nearly half the record came
from one outside reader. `scripts/check_synthesis_counts.py` recomputes the internal triple and
the external count separately from the `caught` and `origin` columns and fails if either
disagrees with this prose.

**What the external eleven have in common.** Three were restatements of a value the repo's
own scripts computed differently (rows 14, 15, 16). Three compared quantities that do not
share a conditional or a population (rows 17, 20, 24) — the same class as items 4, 5 and 13,
now at six instances. Two dropped a qualifying condition the repo had written down elsewhere
(rows 18, 21). Two asserted a disposition or an extremum without checking the criterion or
the ties behind it (rows 19, 23). One cited a precision audit as an exoneration (row 22).
**None required new data.** Every one of the eleven was reproducible from artefacts already
in the repository, which is the uncomfortable part: they were not caught because nobody
re-read the output against the claim, not because the evidence was unavailable.

Row 24 deserves separate emphasis for the same reason item 13 does. Every internal mechanism
listed above had already run over R3 and passed it. And the hazard was on paper — not in the
preregistration, as five documents including this one used to say, but in a *post-results*
caveat in `docs/repair_validation_results.md`: *"Any rule that escalates the cases a judge
finds hard will pass a test of the form 'is the judge worse on the escalated subset'. That
test is necessary, not sufficient, and the preregistration should have said so."* The caveat
was written after the numbers, named the test it had just run as insufficient, and was followed
two paragraphs later by **Disposition: ACCEPTED**. The honest reading is not that the process
worked; it is that a process can only catch the confounds it thought to test for, that writing
an objection down is not the same as acting on it, and that the step which caught this one was
an outside reader asking which slice the rule fires in. The held-out quarantine could not have substituted for
that question: 1,064 of the 1,260 validation cases were already inside a population this
project had tabulated benchmark by benchmark (§3.3.1).

The ratio is itself a finding, and it is not flattering. Taken on the internal audit alone,
**6 of the 13 errors this project found about itself were caught by safeguards that ran ahead
of the data** — close to half, which is the number the preregistration machinery can fairly
claim. Set the 11 external findings beside it and the picture changes: of the 24 rows above,
only 6 were caught before the relevant outcomes existed, and 11 were not caught by this repo
at all. Preregistration and quarantine did the work they were designed for; they did not
substitute for reading the output again, and this project's record is that it did not re-read
often enough on its own. Both framings are in the table; neither one alone is the record.

> **Correction applied during the final consistency audit.** This paragraph previously read
> *"nine were caught before outcomes were visible; four afterwards."* Recounting directly from
> the table gives **6 / 7**. The error was a taxonomy collision: the timing column mixed
> *before the relevant outcomes* with *before publication*, so rows caught after outcomes but
> before publication were silently counted as "before". The column is now single-axis and
> `scripts/check_synthesis_counts.py` derives the totals from it.

---

## 11. Recommended primary narrative

Four candidates, scored:

| narrative | evidence | novelty | staff/principal signal | practitioner use | overclaim risk | coherence |
|---|---|---|---|---|---|---|
| **A** assurance economics | Weak — the economics are class C synthetic; the only verified spend is $49.50 billed / $46.18 analysed | Low | Medium | Medium | **High** — invites invented ROI | Poor |
| **B** falsification study | **Strong** — 7 mechanisms tested on real corpora; 1 gated failure, 1 gated acceptance that is underpowered, 1 gated pass whose reading was narrowed, 1 inverted directional signal, 1 ungated negative outcome, 1 substantial weakening (corrected 2026-10-02, §3.3.3) | Medium | **High** | High | Low | **Excellent** — matches the ledger exactly |
| **C** evidence before intelligence | Medium — 10/15 qualitative, plus R3's held-out result; the "withheld benchmark fields" leg was audited away (§5) | Medium | High | **Highest** | Medium | Good |
| **D** research discipline | **Strong** — 13 documented process failures, 12 claim withdrawals | Low (method is known) | **High** | Medium | Low | Excellent, but it is a method not a result |

**Primary: B — the falsification study, told through D's machinery.**

B has the substance and D explains why anyone should believe it. B alone reads as "I failed
at several things." D alone is methodology with no findings. Together: *seven plausible
mechanisms were frozen and tested; most did not survive, and the specific instruments that
killed them — predeclaration, quarantine, negative controls, cheap baselines — are the
transferable part.* Use §3.6's disposition table for any count, never a compressed ratio.

**Secondary themes, in order:**
1. **C (evidence before intelligence)** — carries the most practitioner value and produces the
   headline maxim (§7). Supported by S4, S5 and the null-rule result.
2. **D (discipline)** — the spine, surfaced through the process-failure audit (§10) rather
   than as its own narrative.
3. **A (economics)** — demoted to a scoping note. Real numbers only: $46.18, 44.7% cache,
   −39.7% calls from stopping, $49.50 billed against $46.18 analysed. The synthetic cost
   tables stay in the appendix, labelled.

---

## 12. Portfolio positioning

**Concretely evidenced capabilities** (each tied to an artifact, not an adjective):

| capability | the evidence a reader can check |
|---|---|
| Experimental discipline | Three-commit chronology (freeze → preregister → report) used for two separate studies; outcomes A–F declared before spending |
| Data-integrity auditing | Found a join-key collision affecting 33.3% of records by tracing one row the classifier could not emit — in the author's own already-published report |
| Statistical skepticism | Identified a preregistered gate as mathematically unpassable (ceiling 1.222× vs threshold 1.25×); showed a saturating indicator inverted the direction of a result |
| Error decomposition | Separated false alarms from missed failures and showed the pooled statistic was ranking on the wrong stratum |
| Benchmark handling | Leakage classification of every rule input; rejected the infeasibility flag; quarantined 42 cases to protect a held-out arm |
| Preregistration | Measured what it cost: predeclared pair last of eight, 0.543 vs 0.759 |
| Cost-aware engineering | Retracted a cost-saving gate on the grounds that it cost more than it saved |
| Killing own work | Seven mechanisms proposed and tested; one failed its own gates, one accepted gate is underpowered, one passing gate's reading was narrowed, one directional signal inverted, one fired its predeclared negative outcome, one weakened; the successor branch closed rather than extended. Also: the project's own replacement arithmetic was audited and corrected a second time (§3.3.3) |

**What would make it look weaker** — each is a live risk in this specific repo:
- Presenting a **four-day** sequence (2026-09-26 → 2026-09-29) in the register of a research
  programme. State the timeframe plainly; the density is the story, not the duration.
- Academic voice. The findings are small and concrete; inflated language will invite the
  reader to check, and checking should reward them.
- Celebrating negative results as breakthroughs. "We discovered that complexity doesn't pay"
  is not supported (§6, attack 4).
- **Compressing the dispositions into a memorable ratio.** "Four of five failed" was written
  into an earlier draft of this document and had no enumerated denominator behind it (§3.6).
  A clean ratio is the single most likely thing to be repeated out of context, so it is the
  single thing most worth auditing. Quote the disposition table, not a fraction. **And audit
  the replacement as hard as the original:** the "three of five gated" ratio that replaced it
  was also wrong, because two of the five had no gate (§3.3.3). Enumerating a denominator is
  not the same as verifying each item belongs in it.
- Framework diagrams for a planner whose own architecture note is full of
  `[REVISED — this prediction was wrong]` markers.
- Publishing 25 documents and the raw chronology with no synthesis layer. A reader who lands
  on `repetition_study_predeclaration.md` (62.8K, three amendments) first will bounce.
- Over-attending to dead side branches. The synthetic planner phase is scaffolding, not
  content.

---

## 13. Repo content hierarchy

**KEEP PROMINENT** — the research artifact
- `docs/research_synthesis.md` (this document)
- `docs/repetition_study_findings.md` — the single strongest empirical result
- `docs/agent_reward_bench_directional.md` — operational-vs-reference-conditioned, the most
  transferable finding
- `docs/repair_validation_results.md` — the held-out R1–R4 sweep
- `docs/rc1_forensic_audit.md` — the correction chain, and the best evidence of rigour
- `docs/rc1_successor_probe.md` — the null-baseline result and the branch closure

**KEEP AS APPENDIX / AUDIT TRAIL** — reproducibility, not narrative
- `docs/agent_reward_bench_gate1.md`, `_findings.md`, `_conditional.md`
- `docs/repetition_study_predeclaration.md` (all three amendments — the withdrawn gate is
  evidence, not embarrassment)
- `docs/required_conjunct_preregistration.md`, `_scoping.md`
- `docs/rc1_final_report.md`, `docs/rc1_post_outcome_decomposition.md`,
  `docs/rc1_extractor_audit.md`
- `docs/production_signal_audit.md`, `docs/repair_validation_preregistration.md`
- `docs/shared_unresolved_case_review.md`
- All `scripts/` and `data/` artifacts

**KEEP BUT DE-EMPHASIZE** — historical scaffolding
- `docs/architecture.md` (46K) — valuable only for §10.1 prior art and the `[REVISED]`
  markers; both should be surfaced by the synthesis instead
- `docs/policy_benchmark_findings.md`, `docs/real_experiment_protocol.md`
- `docs/measurement_review.md`, `docs/measurement_red_team.md`,
  `docs/experiment_red_team.md`, `docs/red_team_review.md`
- `docs/alternate_corpus_red_team.md`, `docs/alternate_source_collection_protocol.md`

**REMOVE FROM PUBLIC-FACING CLAIMS** — superseded; retain in git and in-place corrections
- All six collided-key τ-bench figures (1.090×, 37.5%, 59.1%, −91, 0.902×, 55.6%)
- "F4 is the dominant harm mechanism (9/15)"
- "The 28 cases are reference label errors"
- "Fired tasks are easier" / "task lift below 1.0× is the most diagnostic finding"
- "Shared unresolved errors" applied to 15 cases (it is 5)
- Any synthetic cost figure quoted without the `--assume-alternate-rates` provenance
- "Null rule 7.189× vs construct 2.339×" (withdrawn today, pre-publication)
- **"Four of five mechanisms failed" / "the sole survivor"** — withdrawn in the final
  consistency audit; no enumerated denominator, and it converted R2's underpowered
  acceptance into a failure. Use the §3.6 disposition table.
- **"The benchmark holds a task-type label and an infeasibility flag and passes neither to
  the judge"** — withdrawn. No task-type column exists (class C, inferred from goal text);
  the infeasibility signal is class D oracle leakage. Already corrected at source in
  `production_signal_audit.md` §C2/§3 and `shared_unresolved_case_review.md`; the synthesis
  had resurrected it.
- **"Nine process errors were caught before outcomes; four afterwards"** — the counts are
  **13 found during the study (6 before outcomes, 7 after) and 11 more found by external
  reproduction**, derived from the §10 table by `scripts/check_synthesis_counts.py`.
  (~~**6 / 7**~~, then ~~**6 / 18 as of 2026-10-02**~~ — the second was wrong in the same way the
  abstract was: it folded eleven externally-found errors into this project's own after-the-fact
  count, so the ratio stopped describing the thing it was built to describe. The internal *before*
  count never changed, which is the point of the ratio, and that is only visible once the two
  origins are kept apart.)
- **"Repeating a temperature-0 judge is a waste of money"** unscoped, and **"an artifact
  documenting thirteen process failures is more trustworthy than one documenting none"** —
  the first must name the measured configuration; the second is an auditability property,
  not a measured comparison of trust.

Destroy no history. This is a documentation-hierarchy change only.

---

## 14. Recommended public artifacts

Smallest useful set — **three**:

1. **`README.md` research summary** (~400 words). Thesis, the four Tier-1 claims with
   numbers, the corpora, the timeframe, and a pointer into the hierarchy. This is the only
   thing most readers will finish.
2. **`docs/FINDINGS.md`** — one page: the claim ledger (§9) plus 4–5 figures. The artifact a
   skeptical engineer can check in five minutes.
3. **This synthesis**, as the full technical report.

Everything else already exists as the audit trail. **Do not create** a blog essay, an
experiment registry, a methodology timeline as a separate document (§1 is the timeline), or
an architecture diagram. A portfolio case study can be derived from (2) later, and should
reuse its numbers verbatim rather than restating them.

---

## 15. Recommended figures

Five, in priority order.

| # | figure | claim it supports | data clean? | placement |
|---|---|---|---|---|
| 1 | **k-distribution, both strata** — bars at k=0..5 showing the bimodal mass (704/97 and 210/75, 20 cases in between) | C1 — repetition has nothing to average over | **Yes.** Exact counts, preregistered | Main text |
| 2 | **Error rate by policy** — single / majority-3 / majority-5 / first-to-3, both strata, with Wilson bars, cost on a second axis ($46.18 → $27.86) | C1 + C2 — more calls did not help; stopping is the only real saving | **Yes.** Intervals published; overlap is the point | Main text |
| 3 | **Three-lift comparison** — oracle 2.339× / null 1.171× / RC1 1.101× on the deployable outcome, **with 95% task-level cluster-bootstrap intervals on every bar** and each bar's task count labelled (94 / 80 / 109, they are not the same tasks), with the 15% volume gate drawn as a vertical line all three cross | C10 + C11 — the construct is real, the detector is not, and even the ceiling is unaffordable | **Yes, now.** Single code path; reproduces published values | Main text |
| | *Revision 2026-10-02:* the intervals and task counts are **required**, not optional. The first version drew three bare bars; readers could only compare the bar heights, and the null/RC1 heights support no ordering. A chart that makes an unsupported comparison the only available one is the defect, not the caption. | | | |
| 4 | **Reference-conditioned vs operational** — 0.543 against overturn precisions 0.366 / 0.465, with stratum sizes (32 vs 130) shown as bar widths | C4 + C5 — the most transferable finding | **Yes.** Exploratory, must be labelled so | Main text |
| 5 | **Claim lifecycle timeline** — ~~31 stages~~ **34 stages** on an axis, marking the ~~12~~ **17** withdrawals/narrowings and the process errors — **13 internal + 11 external**, not a single run of 24 — colour-split by caught-before vs caught-after outcomes and by internal vs external origin | The primary narrative (B through D) | **Yes**, from §1 and §10 | Main text, as the opener |
| | *Revision 2026-10-02:* the counts above were stale in all three positions and are now stated as §1's row numbers and §10's row count, both of which `scripts/check_synthesis_counts.py` reads. The figure must also distinguish a third colour — **caught externally** — because 11 of the 24 were, and a two-colour chart would attribute them to this project's safeguards. | | | |

**Appendix candidates, not main text:** predeclared-vs-post-hoc pair scatter across all eight
(folds into figure 4); held-out R1–R4 results (the table is clearer than a chart at n=4);
evidence-layer diagram for the 15 cases (n=15 does not justify a figure).

**Explicitly rejected:** a cost-versus-assurance-gain plot. The cost axis would be almost
entirely synthetic, and the one real point ($49.50 billed for zero gain) is a sentence, not a
curve.

---

## 16. Is the research branch finished?

**Yes. Stop experimenting and publish.**

Against the stated bar for another experiment — it must materially affect the central claim,
have a clean fresh validation surface, not merely rescue a failed mechanism, and offer enough
information gain to justify delaying synthesis:

- A successor detector **fails criteria 1 and 3**: it would exist to rescue F7/F8, and §5
  of the successor probe shows the corrective state→class mapping is per-domain policy that
  would still have to clear a 1.171× floor — a floor whose own interval covers 1 ([0.802,
  1.652]), so the honest statement is that a successor would have to clear a baseline nobody
  has yet shown to work.
- A third corpus **fails criterion 4**. It would broaden C1 and C11, but both corpora are
  now burned, sourcing was expensive before, and the central claim is about what was
  falsified, not about coverage.
- Higher-temperature repetition **fails criterion 3**. Manufacturing stochasticity to study
  stochasticity is explicitly what S3 says not to do.
- Re-running the AER pairing with `aer` as primary (101 missed failures instead of 32)
  **is the only tempting one** — it triples the assurance-relevant denominator. But it is
  an exploratory re-cut of a burned corpus, not fresh evidence, and it cannot restore the
  preregistered status the Tier-1 claim depends on.

Two **correctness** tasks remained, neither an experiment, and both are now done:

1. Figure 3's numbers were recomputed in a single code path, and the corrected values
   propagated to `rc1_successor_probe.md` and `rc1_forensic_audit.md` §16.1 and §14. They
   must not be reintroduced from the superseded draft.
2. A final internal-consistency audit of this document found three defects in the synthesis
   layer itself — an unenumerated "four of five" ratio (§3.6), a resurrected claim that the
   benchmark stores a task-type label (§5, §7), and a process-error count that disagreed with
   its own table (§10). All three are corrected above, and the counts are now asserted by
   `scripts/check_synthesis_counts.py`. **None of them changed an empirical result**; all
   three were errors in how results were summarised, which is the failure mode a synthesis is
   most exposed to and the reason this pass was run.

---

## 17. Claims hierarchy

### Tier 1 — strongest defensible findings (four; resist adding a fifth)

**T1.1** On 1,106 AgentRewardBench trajectories, five repeated executions of the deployed AER
judge (temperature 0, seed 0) produced intermediate correctness on only 20 cases, and both
majority-of-3 and majority-of-5 were marginally *worse* than a single execution in both error
directions. Sequential first-to-3 stopping used 39.7% fewer calls at verdicts identical to
majority-of-5 **by construction** — the two rules cannot disagree once three of five draws
agree, so the call saving is the only empirical part of that sentence. ~~"reproduced
majority-of-5 verdicts exactly using 39.7% fewer calls"~~: corrected 2026-10-03; the caveat
column of §9 C2 carried the by-construction label but this publishable wording did not, which
is the half a reader quotes. *Class A. Scope: one judge, one configuration, judge stage only.*

**T1.2** The quantity that makes escalation look attractive is not the quantity a policy can
run on: `P(alternate correct | primary wrong)` was 0.543, while the precision of the
overturns a deployed policy would actually perform was 0.366 and 0.465. Matched by error
direction, the deployable quantity ran 10.3 points lower on missed failures (0.469 → 0.366)
and 9.7 points lower on false alarms (0.562 → 0.465) on the same cases. Across all eight
alternates the false-alarm-side gap is always positive (+9.7 to +46.0 pp); the
missed-failure-side gap ranges −14.7 to +23.1 pp and reverses for two, so the claim is that
the two quantities diverge, not that the operational one is always worse. *Class B. The most
transferable finding in the project. "20 to 30 points" withdrawn 2026-10-02 — see §3.2.1.*

**T1.3** Preregistration changed the reported result by a measurable margin: the pair chosen
on frozen pre-outcome criteria ranked last of eight on pooled recovery (0.543 vs 0.759 for
the post-hoc best), in a report that would have read identically — and the pooled metric was
itself later shown to be the wrong conditional, on which the same pair ranks tied first.
*Class A vs B.*

**T1.4** On a fresh corpus read label-blind (τ-bench, 1,980 records; ~~"previously untouched"~~
— corrected 2026-10-02, the files were read during scoping with `reward`/`info` withheld in
code), a static
required-conjunct rule failed both binding preregistered gates (25.3% volume against <15%;
1.165× trajectory lift against ≥1.50×) while its extractor passed a label-blind audit at
28/30 — and on the deployable outcome it ~~landed *below*~~ **did not outperform** a baseline
requiring no model at all (NULL − RC1 = +0.078 within-task lift [−0.327, +0.575] on paired
task resamples; neither rule distinguishable from 1). The target construct itself was not empty
(oracle 2.339×, and ORACLE − NULL = +1.177 [+0.721, +1.687]), so this is a recovery failure,
not an abstraction failure. *Classes A/FRESH, B and D.* (Ordering claim withdrawn 2026-10-02;
the two bare lifts were computed on 80 and 109 tasks respectively.)

### Tier 2 — supported but scoped

- **T2.1** Of four deterministic pre-checks frozen before held-out validation on 1,260
  quarantined-split cases, **only two carried numeric accept/reject gates** (R2, R3; §7 of the
  preregistration gives R1 and R4 a direction and no threshold — corrected 2026-10-02). Of
  those two, one was accepted but is underpowered by its own harm bound (39.3% at n=6) and one
  passed as an escalation signal. Of the two directional rules, R1's firing enrichment
  inverted (0.51×) and R4's met its direction (1.20×) while showing no evaluator-level signal;
  R4's published ~~REJECTED~~ label was post hoc. *n=4.*
- **T2.2** R1's signal *inverted* on held-out data (0.51× lift), and the veto it had been
  deliberately denied would have helped 6 and harmed 14. Log the counterfactual of any
  authority you withhold. *Single instance, but decisive within it.*
- **T2.3** An explicit evidence-gap state has held-out support as an *escalation* signal
  ~~(25.6% vs 14.4% evaluator error)~~ **within a single environment: all 133 firings are
  visualwebarena, and against the rest of that benchmark the contrast is 25.6% vs 19.7%
  (34/133 vs 31/157), Fisher p = 0.26 — +5.8 pp of the +11.2 pp pooled separation**, with the
  rider that it corrects nothing and that 99 of the 133 cases it escalated were already
  correct. The surviving separation is on the missed-failure side only (25.3% vs 15.8%,
  p = 0.11; the false-alarm side reverses to −4.1 pp, p = 0.81). Its value is entirely a
  function of review cost. *Scoped down 2026-10-02 — see §3.3.1; counts and p-values from
  `scripts/arb_r3_slice_check.py`.*
- **T2.4** Structural independence between evaluators did not predict measured error
  independence, and pooled φ ranked alternates on the stratum where the question does not
  arise (spread 6.7× → 1.6× once conditioned).
- **T2.5** Error directions must be reported separately; three separate pooled statistics in
  this project were dominated by the stratum that did not matter.
- **T2.6** A sample-size or support check can be correctly computed and applied to the wrong
  quantity — support was certified on 162 primary errors when the decision turned on 32.
- **T2.7** Compute a metric's ceiling before preregistering a threshold against it: a binding
  gate here was mathematically unpassable (1.222× max vs 1.25× required), and the saturating
  indicator behind it inverted the direction of the result.

### Tier 3 — exploratory observations and future work

- **T3.1** In a 15-case review, only 5 failed first at the evaluator's reasoning; 5 failed at
  representation and 4 at specification. *n=15, selected, qualitative.*
- **T3.2** The dominant RC1 failure mechanism was the agent performing every required write
  through an action class the rule had not frozen (~242 of 383 wrong-reason firings).
- **T3.3** In 12/12 oracle-confirmed harm cases, the state determining the correct action
  class was visible in a structured tool result before the agent's first write — but the
  state→class mapping is per-domain policy.
- **T3.4** τ-bench carries a reference noise floor of 28 records (1.4%) where a required
  write is absent yet reward is 1.0. Do not subtract it; use it to bound what counts as a
  real effect.
- **T3.5** Whether any of T1.1, T1.4 or T2.1 generalizes to other judges, configurations or
  corpora is **unknown and untested**.

---

## 18. Provisional abstract

> Production teams evaluating AI agents are routinely advised to buy more assurance —
> repeat the judge, escalate to a second evaluator, add deterministic guards. This project
> froze seven such mechanisms and tested them on two public corpora (AgentRewardBench, 1,106
> annotated agent trajectories; τ-bench, 1,980 trajectories over 165 tasks). Of the three
> carrying numeric pass/fail gates on held-out or fresh data, one failed, one was accepted
> but is underpowered by its own harm bound, and one passed; two more carried a preregistered
> direction without a threshold, and two no criterion at all. Five repeated executions of a deployed LLM judge —
> 5,530 analysed calls, $49.50 billed — produced intermediate correctness on only 20 of
> 1,106 cases, and
> majority voting was marginally worse than a single call in both error directions;
> sequential stopping used 39.7% fewer calls at verdicts identical by construction. An alternate
> evaluator appeared to recover 54.3% of the primary's errors, but the precision of the
> overturns a deployed policy would actually perform was about ten points lower in each error
> direction, because the attractive statistic conditions on a ground-truth label no runtime
> system has. Of four
> frozen deterministic pre-checks, one produced an inverted signal on held-out data whose
> withheld veto would have harmed more cases than it helped, and none produced a verdict-level
> correction that survived its own power analysis. On a fresh corpus, a
> rule that tracked user-stated obligations against executed tool classes **failed to
> outperform** a baseline requiring no model at all — the two differ by a mean +0.078 within-task
> lift [−0.327, +0.575] over 2,000 paired task resamples (+0.070 differencing the two point
> estimates), and neither is distinguishable from no effect. What survived is narrower and cheaper than what was
> proposed: the one rule that passed its numeric gate cleanly was an explicit "required evidence
> is absent" state (R2 was accepted too, underpowered), which
> earned held-out support as an escalation signal while asserting no verdict of its own,
> though it corrects nothing itself, 99 of the 133 cases it escalated were already
> correct, and all 133 fall in a single one of the four environments — conditioned on that
> environment its separation halves, from 11.2 to 5.8 percentage points, and is no longer
> significant (Fisher p = 0.26). The negative results matter
> because each mechanism was plausible enough to ship, and the instruments that killed them —
> preregistration, held-out quarantine, negative controls, and recomputing comparisons in a
> single code path — cost far less than the mechanisms would have. Process errors in the
> research itself are documented alongside the findings, in two counts kept apart: **13 found
> during the study** by its own safeguards (6 before the outcomes they affected were visible, 7
> after) and **11 more found by an independent reproduction** of this study, which no safeguard
> inside it caught. (~~"Twenty-four process errors … 18 of them caught only after"~~ — corrected
> 2026-10-02: the sum reads as though the project's own audit had found eighteen late errors,
> when eleven of them were not its own audit at all.)

---

## 19. Thesis

**One sentence, strongest defensible:**

> Across two public agent-evaluation corpora, most of seven preregistered evaluator-assurance
> mechanisms did not survive their own validation — **only three carried numeric gates and one
> of those failed**, one rule's directional signal came out inverted, one fired its predeclared
> negative outcome, and one weakened substantially — and in each case a cheaper measurement
> carried as much of the signal; the rule that came closest to surviving was the one that
> reported missing evidence instead of asserting a verdict, and even that reading was narrowed
> once its firings were conditioned on benchmark slice.

*(Corrected 2026-10-02. The sentence above previously read "three failed numeric gates
outright". Two of those three — R1 and R4 — had no numeric gate: §7 of their preregistration
gave them a direction and no threshold, and R4 met its direction. See §3.3.3.)*

**Strongest wording that is too strong, and why it cannot be claimed:**

> ~~Sophisticated evaluator assurance doesn't work: repetition, routing, and semantic
> tracking all lose to simple baselines, so teams should stop buying inference and start
> measuring what they already have.~~

Four reasons it fails. (1) *"Doesn't work"* overstates *"failed to validate"* — R2's harm
bound is 39.3% at n=6 and the missed-failure stratum is n=32; several mechanisms are
underpowered, not refuted. (2) *"Sophisticated"* is never operationalised, and the variable
that actually separated surviving from failing rules was **what they claimed**, not how
complex they were — R1, R3 and R4 are comparable in complexity with opposite dispositions.
(3) The claim generalizes from two corpora whose evaluators are not independent mechanisms
(`functional` is a threshold on a scalar; the eight LLM judges share two representation tiers
and none sees a screenshot). (4) *"Lose to simple baselines"* is false as stated for the
construct — the oracle reconstruction beat the null rule by **+1.177 [+0.721, +1.687]** on
paired task resamples (2.339× vs 1.171× as point estimates) — and, as of 2026-10-02, **false
as stated for the production detector too**: RC1 did not lose to the null rule, it tied with
it (+0.078 [−0.327, +0.575], neither distinguishable from 1). ~~"Only the *production detector*
lost."~~ The accurate statement is that the production detector **failed to beat** a simple
baseline, which refutes the overclaim without supporting its mirror image.

A fifth reason applies to an earlier version of the defensible thesis itself, not just the
overclaim. It read:

> ~~"Across two public agent-evaluation corpora, four of five preregistered evaluator-assurance mechanisms failed their own thresholds … with the sole survivor being the mechanism that reported missing evidence."~~

That arithmetic had **no enumerated denominator**, counted an underpowered
acceptance as a failure, and contradicted this document's own §2 boundary rule by ignoring
R2's preregistered ACCEPTED status. It is withdrawn in favour of the disposition table at
§3.6. The lesson generalises: **a synthesis about catching attractive errors cannot contain
attractive arithmetic that is itself unaudited.** A clean ratio is the most repeatable
sentence in any write-up and therefore the one most worth checking last.

**A sixth reason, added 2026-10-02 — the replacement arithmetic was wrong too.** The
"three failed / one underpowered / one passed, out of five gated" formulation that replaced
"four of five" shared the defect it was meant to fix: its denominator was asserted rather than
read off the preregistrations. Two of the five (R1, R4) were never gated, and R4 met the only
criterion it had. The corrected split is **three gated (R2 accepted-underpowered, R3 passed,
RC1 failed) plus two directional (R1 inverted, R4 met)**. The failure mode is worth naming
precisely because it recurred inside the correction: *checking* the count is not the same as
checking *what each item in it was actually promised*. §3.6's threshold column said "Yes" for
R1 and R4 for as long as the table existed, and nobody opened §7 to confirm it. The remedy is
mechanical, not editorial — `scripts/check_synthesis_counts.py` now asserts the 3 + 2 split
against that column, so a future draft cannot restate a gated count the table does not
support.

---

## 20. Next action

**The research branch is finished.** No further experiment is warranted.

**What should happen next — documentation consolidation, in this order:**

1. Commit the current working tree: the successor probe (script, data, doc), the forensic
   audit §16.1/§14 updates, and this synthesis. One commit, message framed as branch closure.
2. Write `docs/FINDINGS.md` — the §9 claim ledger as a standalone page, with the forbidden
   wordings retained as a visible column.
3. Rewrite `README.md` against §17's Tier 1 and §11's narrative. Four claims, the corpora,
   the four-day timeframe, and a map into §13's hierarchy.
4. Add a short `docs/README.md` index implementing §13's four tiers, so a reader does not
   land in a 62K predeclaration first.
5. Generate figures 1–3 from existing data (`data/REAL_arb_repetition_raw.jsonl`,
   `data/rc1_successor_probe.json`); figures 4–5 can follow.
6. Sweep for the superseded figures listed in §13 and confirm each is either corrected
   in-place or explicitly marked as history.

**Recommended model: Sonnet.** Steps 1–6 are execution against decisions this document has
already made; the numbers are verified and the wordings are fixed in §9. Escalate to Opus
only if step 6 surfaces a contradiction between documents that requires re-judging a claim.

---

## 21. The final question

> *After all corrections and failed mechanisms are accounted for, what would a skeptical
> senior AI engineer still believe because of this work?*

~~Five things~~ **Six things (a sixth added 2026-10-02)**, and nothing larger:

1. **That this deployed temperature-0 / seed-0 judge had too little useful repeat-execution
   variability for repetition to pay — and that they should measure their own deployed
   configuration before assuming repeated sampling will help.** The scope is one judge, one
   corpus, the judge stage only. The measurement on cached judgments is free; confirming it
   with 5,530 fresh executions cost $49.50.
2. **That "the second evaluator catches X% of the first one's errors" is the wrong number,**
   and that the right one — the precision of the overturns actually performed — is
   materially lower. They will recompute their own.
3. **That evaluator-pair and rule selection must be frozen before outcomes are visible,**
   because here it moved the headline by 21.6 points in a document that would have read
   identically either way.
4. **That a new assurance mechanism should be required to beat a no-inference baseline
   before its machinery is credited** — and that this gate is cheap enough that there is no
   excuse for skipping it. Note what the gate returned here, after the 2026-10-02 correction:
   a **tie**, not a loss (+0.078 [−0.327, +0.575]), with the baseline itself indistinguishable
   from no effect. A tie is already sufficient to withhold credit, so the gate did its job —
   but the gate must be run as a paired comparison with an interval, not as a glance at two
   point estimates, because this project published the glance and got the direction wrong.
5. **That preserving corrections, failed gates and data-integrity defects makes the
   evidentiary trail auditable** — every figure here can be traced to the commit that
   produced it and to any later commit that revised it, including a join bug that corrupted
   a third of the records and survived into a published report. This is a property of the
   artifact, not a measured result: the project ran no comparison between artifacts that
   disclose their failures and artifacts that do not, and cannot claim one is more trusted
   than the other. What it can claim is that a reader is able to check.
6. **That a pooled contrast between "cases the rule fired on" and "everything else" is not
   evidence about the rule until it is stratified on the covariates that vary across the
   corpus.** *(Added 2026-10-02, after an external reproduction.)* This project's one clearly
   positive held-out result passed a preregistered test comparing evaluator error on R3's 133
   firings against the remaining 1,126 cases (25.6% vs 14.4%, Fisher p = 0.0015). All 133
   firings are visualwebarena, which also carries the highest judge-error point estimate of the
   four slices — 22.4%, against **19.8% on webarena**, 11.1% on workarena and 3.9% on
   assistantbench — so the comparison was substantially one benchmark against the other three.
   ~~"the slice where this judge is weakest (22.4% error against 3.9% on assistantbench)"~~:
   corrected 2026-10-03. Quoting only the lowest slice turns a 2.6-point gap over the
   next-highest into an apparent 22.4-against-3.9 contrast, and at n = 290 against n = 373 the
   ordering against webarena is not separated — the claim is the rank of a point estimate and
   nothing stronger. Conditioned on slice: 25.6% vs 19.7%, p = 0.26 — +5.8 pp of +11.2 pp survives.
   The objection was already written down — in a post-results caveat in
   `repair_validation_results.md`, not in the preregistration ("Any rule that escalates the
   cases a judge finds hard will pass a test of the form 'is the judge worse on the escalated
   subset'... and the preregistration should have said so") — and the check was never run. Two further properties make this
   worth believing rather than filing: the **held-out split could not have caught it**, because
   1,064 of the 1,260 validation cases (84.4%) were already inside the pairing population the
   project had tabulated benchmark-by-benchmark, and a confound living in a covariate survives
   any split that does not stratify on it; and the residual **lives on one side of the error
   axis only** (missed failures 25.3% vs 15.8%, p = 0.11; false alarms reverse to 26.1% vs
   30.2%, p = 0.81), which a pooled "evaluator error" rate cannot show. Both computations:
   `scripts/arb_r3_slice_check.py`.

What they should *not* believe: that any of this generalizes to other judges, other
configurations, or other corpora. It has not been tested, and this project's own record is
that untested generalizations are where the errors live.
