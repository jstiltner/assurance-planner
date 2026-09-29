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
| 11 | Pooled complementarity result (`07c19c6`) | Does the alternate recover the primary's errors? | PRE | Recovery **0.543** [0.466, 0.618], φ **+0.323** — **last of the eight** candidates; post-hoc best would have been **0.759**, φ **+0.064** | The predeclaration's cost is measured: 21.6 points of headline |
| 12 | Directional decomposition (`2c8479d`) | Do the two error directions behave the same? | EXP | **No.** 162 primary errors = 32 missed failures + 130 false alarms. Recovery 0.469 on misses vs 0.562 on false alarms. Pooled recovery was dominated by the false-alarm stratum | Predeclared pair is *tied first of eight* on missed failures — pooled ranking was the wrong metric |
| 13 | Operational vs reference-conditioned | Is recovery a policy quantity? | EXP | **No.** `P(alt correct \| primary wrong)` = 0.543; deployable overturn precision = **0.366** (to-fail) / **0.465** (to-pass) — 20–30 points lower | "The single most consequential thing found in this pass, and it is a defect in the framing, not in the data" |
| 14 | Conditional association / pooled-φ (`e66f364`) | Is φ a mechanism-diversity indicator? | EXP | **No.** φ spread across 8 alternates collapses from **6.7×** pooled to **1.6×** conditioned on the reference label; pooled OR below the ref-fail OR for all 8, below *both* strata in 3 of 8 | φ withdrawn as a diversity proxy; it may be measuring threshold alignment |
| 15 | Repetition predeclaration (`10a8776`, `1c03e46`, `608c4ce`) | Does repeating the judge help? | PRE | Gate verification found the deployed config is `gpt-4o-2024-11-20`, **temperature 0.0, seed 0**, no variation — discovered *before any API call* | Study reframed from "measure the wobble" to "measure the fix" |
| 16 | Prompt-caching correction | Does caching invalidate a repetition? | — | **No.** "A cached completion is not an independent draw" describes a mechanism that does not exist; caching reuses prompt-prefix state, not completions | Instruction to disable caching withdrawn; caching becomes a measurement |
| 17 | Staged R=2→R=5 gate withdrawn (`9fabf47`) | Can we avoid ~$35 of inference? | — | **Gate retracted.** Two defects: it revived the disavowed constant 16 as a "resolution floor", and its bound needed conditionally-IID draws while claiming only exchangeability — an IID bound gating the study that existed to measure independence | "The engineering and methodological cost of the gate exceeded the $35 it was designed to save" |
| 18 | R=5 repetition study (`f1bc7d2`, `2b430cb`) | Does repeated execution recover errors? | PRE | **Outcome C — both directions negligible.** 5,530 calls, $46.18. 98.8% / 96.6% of cases at k∈{0,5}. Majority-3 and majority-5 both marginally *worse* than one call | Repetition killed as a lever for this configuration |
| 19 | "Shared unresolved" label withdrawn (`2ccd08b`) | Were 15 cases wrong under all judges? | — | **No — only 5 were.** The label named 15 cases that 8 judges did not share | Term restricted to the 5-case subset; correction applied in place |
| 20 | 15-case qualitative review (`5b79493`, `48fd0ab`) | Where do judge failures actually originate? | QUAL | Earliest failed layer: 1 reference · 0 observation · **5 representation** · **4 specification** · **5 evaluator reasoning** · 0 decision. **Only 5 of 15 fail first at the evaluator** | Richer judges are the wrong lever for 10 of 15 |
| 21 | Oracle-leakage audit (`db0975d`) | Are the candidate rule inputs production-visible? | — | **Infeasibility flag rejected**: 84/1302 workarena task IDs contain `infeasible`; telling the judge the task is impossible hands it the verdict | Leakage class (A/B) assigned to every rule input before validation |
| 22 | Held-out rule validation (`1bdab61`, `af10543`) | Do deterministic pre-checks survive a quarantined split? | HO | 1302 = 1260 validation + 42 quarantined. **R1 REJECTED** (lift **0.51×**, inverted; withheld veto would have been 6 helped / 14 harmed). **R2 ACCEPTED but UNDERPOWERED** (6/0, but lift 1.06×, harm bound 39.3%). **R3 ACCEPTED** (25.6% vs 14.4% evaluator error). **R4 REJECTED** (1.20× lift but 16.1% vs 15.5% evaluator error — 0.6 pt) | Two of four frozen rules fail; the counterfactual of the veto R1 was denied becomes the most valuable number produced |
| 23 | RC1 freeze + τ-bench preregistration (`086f0c6`, `3dc3a85`) | Does required-conjunct matching enrich failures on a fresh corpus? | PRE/FRESH | 1,980 records, 165 tasks, 2 domains, 2 agents, programmatic reward, never touched. Gates: A1 <15% volume, A2 ≥1.50× traj / ≥1.25× task, A3 ≥27/30 extractor | Three-commit chronology (freeze → preregister → report) becomes repo standard |
| 24 | Label-blind extractor audit (`8197c5a`) | Are firings attributable to the rule or the extractor? | PRE | **A3 PASSES 28/30.** Three false positives found and fixed pre-reward | Rule failure cannot be blamed on extraction |
| 25 | RC1 rejected (`404174f`, `226ee57`) | Did RC1 pass? | FRESH | **REJECTED.** Volume 25.3%, lift 1.165× | Both binding gates failed |
| 26 | Join-collision discovery (`c43cdea`) | Why is there an impossible row in the harm sample? | — | **660 gpt-4o records (33.3%) scored against sonnet's rewards.** Detected by tracing one row the classifier cannot emit | Six published figures corrected; §18 harm decomposition fully replaced |
| 27 | Forensic audit (`2d19e22`) | Which conclusions survive the corrected join? | ORA/EXP | A2-task gate **INVALID** — 81.8% of tasks hold a failing trial, capping achievable lift at 1.222× below its own 1.25× bar. F4-dominant mechanism claim withdrawn; **F6 dominant (~242 firings)**. H2 narrowed to **H2a** | Nine claims withdrawn or narrowed in one table |
| 28 | Oracle/construct diagnostic | Is the detector bad, or the construct empty? | ORA | **Construct is real, detector is not.** Oracle volume 17.0%, within-task lift **2.339×**; RC1 recovers it at **33.1% precision / 49.3% recall**; right-for-right-reason on **118/501 = 23.6%** of firings. Even the oracle fails A1 (17.0% > 15%) | Construct carries signal; a production-valid representation of it is not established (H2a) |
| 29 | Successor probe + null-rule comparison (today) | Is a successor warranted? | EXP | **No.** On the deployable outcome, within-task: oracle **2.339×**, null rule (no successful write, no model) **1.171×**, **RC1 1.101×**. RC1 falls below a no-model baseline. Corrective state visible in structured tool results in **12/12** harm cases | Null-baseline check added as a standing gate |
| 30 | Correction to the probe (today, pre-publication) | Was the null-rule headline valid? | — | **No — withdrawn.** First draft claimed "null 7.189× vs construct 2.339×", comparing two different outcome variables where "no write" partly *constitutes* "a required write is missing" | Construct's 2.339× **upheld**, not narrowed; the damage lands on RC1 instead |
| 31 | Branch closed | — | — | Stop experimenting; synthesize | This document |

The shape of the ledger is the point: of 31 stages, **12 removed or narrowed a claim the
project had already made.** It did not accumulate support.

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
| valid executions | 5,530 |
| cost | **$46.18** (≈$58 without the 44.7% prompt-cache discount) |
| deployed config | `gpt-4o-2024-11-20`, temperature 0.0, seed 0, `max_completion_tokens` 1024 |
| k=0 / k=5 (ref-fail) | 97 (12.0%) / 704 (86.8%) |
| k=0 / k=5 (ref-success) | 75 (25.4%) / 210 (71.2%) |
| at an extreme | **98.8%** ref-fail, **96.6%** ref-success |
| any within-case variation | 10 cases per stratum — **20 of 1,106** |
| first-two disagreement | 0.62% ref-fail [0.26, 1.44]; 1.36% ref-success [0.53, 3.43] |
| single-execution error | 12.70% missed-failure; 27.25% false-alarm |
| majority-of-3 | 12.82% / 27.80% — **worse in both strata** |
| majority-of-5 | 12.95% / 27.46% — **worse in both strata** |
| sequential first-to-3 | identical verdicts to majority-of-5 (0 mismatches); 99.4% terminate at 3 calls; **−39.8% calls**; ≈$27.86 |

**Precise conclusion:** *repeated execution of the deployed AER judge under its actual
configuration exhibited very little useful variability and did not improve either error
direction.* It does **not** license "LLM judges are deterministic" — the findings doc
itself forbids that, noting temperature-0 determinism is not the same as no variability and
provider-side nondeterminism is not excluded by five draws.

### 3.2 Alternate-evaluator evidence — classes A and B

| quantity | value | class |
|---|---|---|
| predeclared pair (`functional`→`aer`) pooled recovery | **0.543** [0.466, 0.618], φ +0.323 | A |
| rank among 8 candidates on pooled recovery | **last of eight** | A |
| post-hoc best pair (`functional`→`gpt-4o-mini` axtree) | **0.759** [0.688, 0.819], φ +0.064 | B (oracle selection) |
| gap the predeclaration cost the headline | **+0.216 recovery** | — |
| primary error decomposition | 162 = **32 missed failures** + **130 false alarms** | A |
| missed-failure recovery | 0.469 [0.309, 0.636], 15/32 — **tied first of eight** | B |
| false-alarm rescue | 0.562 [0.476, 0.644], 73/130 | B |
| **operational** overturn-to-fail precision | **0.366** (15/41) | B |
| **operational** overturn-to-pass precision | **0.465** (73/157) | B |
| gap: reference-conditioned vs operational | **20–30 points** | B |
| blanket adjudication on primary FAIL | 73 correct / 84 wrong = **−11 net**; non-positive for all 8 pairs | B |
| φ spread across 8 alternates, pooled → ref-conditioned | **6.7× → 1.6×** | B |
| pooled OR below *both* strata | **3 of 8** | B |
| swapping to the other predeclared primary (`aer`) | missed failures **32 → 101** on the same 1,106 cases | B |

**The distinction that must survive into any write-up:** reference-conditioned recovery is
not an executable production policy. Nothing selects the primary's errors at runtime.

### 3.3 Held-out rule validation — class A

Split: 1302 annotated = **1260 validation** + **42 quarantined** (15 discovery + 27 same-task
siblings). Strict arm 1180.

| rule | fires | key held-out number | disposition |
|---|---|---|---|
| **R1** self-contradictory infeasibility claim | 27 (2.1%) | lift **0.51×** — *inverted*; counterfactual veto **6 helped / 14 harmed, net −8** | evidence half **REJECTED**; escalation half survives |
| **R2** negative self-report on imperative goal | 13 eligible, 6 changed | **6 helped / 0 harmed**; but firing precision **1.06×** and rule-of-three harm bound **39.3%** at n=6 | **ACCEPTED**, simultaneously UNDERPOWERED-REGARDLESS |
| **R3** unverifiable image premise | 133 (10.6%) | evaluator error **25.6%** on escalated vs **14.4%** on remainder; removes 22 E1 + 12 E2 from authority; **99 of 133 escalated were already correct** | **ACCEPTED** |
| **R4** terminal search-results route | 118 (9.4%) | lift 1.20× on the *agent's* outcome, but evaluator wrong on **16.1%** of firings vs **15.5%** elsewhere — 0.6 pt | **REJECTED** — tells you about the agent, not the evaluation; also application-specific |

### 3.4 τ-bench RC1 — class A/FRESH, corrected values only

| gate / quantity | value | verdict |
|---|---|---|
| A1 firing volume | **25.3%** (501/1980) vs <15% | **FAIL** |
| A2 trajectory lift | **1.165×** vs ≥1.50× | **FAIL** |
| A2 task lift (1.25×) | 0.906× | **GATE INVALID** — 135/165 tasks (81.8%) hold a failing trial, so max achievable lift is 1.0/0.818 = **1.222× < 1.25×**. Unpassable by construction |
| within-task lift | **1.101×** | pooled 1.165× was partly restating task difficulty |
| harm rate | **53.1%** (266/501) | — |
| counterfactual veto net | **−31** (235 helped, 266 harmed) | veto correctly never granted |
| A3 extractor precision | **28/30** | **PASS** — failure is the rule's, not the extractor's |
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
suppressor rather than the source of signal, and RC1 landed below a no-model behavioural
check. The *construct* is not reducible to that check (2.339× vs 1.171×), so the failure is
recovery, not abstraction.

### 3.6 Mechanism dispositions — the audited denominator

This table exists because an earlier draft of this document compressed the project into
*"five mechanisms were frozen and tested; four failed"* without ever enumerating the five.
That arithmetic is **withdrawn**; see the note below the table.

Every candidate mechanism that could plausibly enter the denominator:

| # | mechanism | preregistered? | frozen pass/fail threshold? | evaluation surface | disposition |
|---|---|---|---|---|---|
| M1 | Repeated execution (R=5) | **Yes** — outcome space A–F frozen pre-spend (`repetition_study_predeclaration.md`) | **No.** The bands are explicitly *"thresholds for which paragraph gets written"*, not for a decision; no `r*` declared (§A1.9, lines 477–498) | Fresh inference (5,530 new calls) on an already-analysed corpus | **FAIL for the deployed configuration** — predeclared Outcome C fired ("both directions negligible") |
| M2 | Alternate-evaluator pairing / escalation | **Yes** — *pair selection* frozen on five pre-outcome criteria (`agent_reward_bench_gate1.md` §5) | **No.** Support was adequate for all 36 pairs, so it disqualified nothing; no recovery threshold and no `r*` were declared | Same corpus; selection frozen pre-outcome, analysis not held out | **WEAKENED / NO BINARY GATE** — 0.543 pooled (last of eight); operational analogue 0.366 / 0.465 |
| M3 | **R1** self-contradictory infeasibility claim | Yes | Yes | Held out (1260 validation, 42 quarantined) | **FAIL (partial)** — evidence half REJECTED (0.51× inverted); escalation half survives |
| M4 | **R2** negative self-report on imperative goal | Yes | Yes | Held out | **ACCEPTED BUT UNDERPOWERED** — 6 helped / 0 harmed, but lift 1.06× and harm bound 39.3% at n=6 |
| M5 | **R3** unverifiable image premise | Yes | Yes | Held out | **PASS** — both preregistered tests pass, both arms |
| M6 | **R4** terminal search-results route | Yes | Yes | Held out | **FAIL** — REJECTED; 1.20× on the agent's outcome, 0.6 pt on the evaluator's |
| M7 | **RC1** static required-conjunct / tool-class matching | Yes — `required_conjunct_preregistration.md` | Yes — A1 <15%, A2 ≥1.50× traj / ≥1.25× task, A3 ≥27/30 | **Fresh corpus**, never touched | **FAIL** on A1 (25.3%) and A2-traj (1.165×); A2-task is an **INVALID GATE** (ceiling 1.222× < 1.25×); **A3 PASSES** 28/30 |
| M8 | Null rule ("no successful write anywhere") | Preregistered as **disqualified**, label-blind (`required_conjunct_scoping.md` §6.4) | Never granted a gate | Exploratory re-cut of the burned τ-bench data | **EXPLORATORY ONLY** — reported as a floor; fails volume on its own at 24.1% |

**Explicitly excluded from the denominator, with reasons:**
- *"A generic deterministic pre-check architecture"* (F5) is not a ninth mechanism — it is the
  class {M3…M6}. Counting it alongside its own members double-counts.
- Sequential stopping, adaptive allocation, and the blind escalation control are **class C
  synthetic** (§2). They were never tested against a real judge and cannot enter a count of
  empirical dispositions.
- The staged R=2→R=5 continuation gate was retracted before execution; it has no disposition.

**Why "four of five / sole survivor" is withdrawn.** Three independent defects:

1. **The five was never enumerated.** No five-item list exists in the repo. The only natural
   five-item denominator is the set carrying frozen numeric gates on held-out or fresh data —
   {R1, R2, R3, R4, RC1} — and on that set the count is **three failures, not four**.
2. **"Sole survivor" contradicts this document's own §2 boundary rule 3.** R2's preregistered
   disposition is ACCEPTED and was deliberately *kept* accepted when a post-hoc metric
   undermined it. Two rules survived, not one. (RC1's extractor also passed its own A3 gate.)
3. **It converts underpowered into failed.** R2 is underpowered by its own harm bound, which
   is a statement about n=6, not a refutation.

**The replacement summary, mechanically traceable to the table above:**

> Seven candidate assurance mechanisms were tested on real data. Five carried frozen numeric
> pass/fail gates evaluated on held-out or fresh corpora: **three failed** — R1's evidence
> half on an inverted signal, R4 as uninformative about the evaluator, and RC1 on two of its
> three τ-bench gates — **one was accepted but is underpowered by its own harm bound** (R2,
> 39.3% at n=6), and **one passed** (R3, as an escalation signal that corrects nothing
> itself). The remaining two were preregistered without numeric gates: repeated execution
> fired its predeclared negative outcome for the deployed configuration, and generic
> alternate-evaluator escalation had no gate to fail but weakened substantially once the
> operational conditional replaced the reference-conditioned one.

---

## 4. What the research killed

**F1 — Repetition as a production recovery mechanism.** *Killed, for this configuration.*
Majority-3 and majority-5 are both marginally worse than one call; 20 of 1,106 cases showed
any variation at all. **Scope: one judge (`aer`), one deployed config (temp 0.0 / seed 0),
one corpus, judge stage only — not full-pipeline, not other temperatures, not other judges.**

**F2 — Generic alternate-judge escalation.** *Heavily weakened.* Pooled recovery 0.543 was
dominated by the false-alarm stratum (130 of 162 errors). Missed-failure recovery is 0.469
on n=32. The operational analogue — the precision of overturns a policy would actually
perform — is 0.366 / 0.465, twenty to thirty points below. Blanket adjudication on the
primary's FAIL verdict is non-positive against all eight candidates. And post-hoc evaluator
choice would have produced a 0.759 headline, a prettier and less honest story.

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
both binding gates on a fresh, untouched corpus while its extractor passed at 28/30 — so the
rule, not the parsing, is what failed. Dominant mechanism F6_alt_tool (~242 firings): the
agent performed every required write using an action class RC1 had not frozen.

**F8 — "Right for the right reason" as evidence for obligation modeling.** *Rejected as
causal evidence.* The 118-firing subset looks excellent in isolation (volume 6.0%, lift
2.02×, veto net +74) but it is oracle-selected, its obligation-derived features are flat, and
it is confounded by agent identity and task identity.

**F9 — More semantic machinery necessarily produces more useful assurance.** *Not supported,
with a caveat.* RC1's extraction pipeline landed below a one-line behavioural check on the
deployable outcome. **But the caveat is load-bearing:** the *oracle* construct beats the null
rule 2.339× to 1.171×, so richer semantics are not worthless here — they were merely not
recoverable from production-visible inputs by this mechanism.

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

**S4 — An explicit missing-evidence / UNVERIFIABLE state.** *Supported, narrowly.* R3 has
held-out support **as an escalation signal**: it identifies a 133-case subset where the
evaluator errs at 25.6% against 14.4% elsewhere. Phrase with all four qualifiers: it
identified a higher-error subset; it **did not autonomously correct** any case; **99 of the
133 it escalated were already correct**; its value therefore depends entirely on review cost.
It is not a general assurance architecture. Note also that R3 survived partly because its
claim is the weakest of the four — it asserts an evidence gap rather than a verdict, which
is a lower bar to clear.

**S5 — Evidence availability matters before evaluator sophistication.** *Well supported
qualitatively, n=15.* Only 5 of 15 unresolved cases fail first at the evaluator's reasoning;
5 fail at representation (an image premise the judge was never shown), 4 at specification, 1
at the reference label. A better judge is the wrong lever for two-thirds of them.
Independent support comes from R3 (§3.3), which is the same phenomenon in preregistered,
held-out form: a 133-case subset defined by an absent image premise, where the evaluator errs
at 25.6% against 14.4% elsewhere.

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

**S6 — Cheap baselines must precede semantic machinery.** *Strong, newly sharpened.* Three
independent instances: a fifteen-line stopping rule captured 100% of the available cost
saving that allocation was built to capture (synthetic); a blind hash-based escalation
control dominated the candidate policy on one fixture (synthetic); and a no-model "did the
agent write anything" check out-performed RC1's extraction pipeline on real fresh data
(1.171× vs 1.101×). The synthetic two are class C and cannot carry weight alone — the third
is what makes this a finding rather than a fixture artefact.

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
*Neither, exactly — they are partly constitutive.* The task-difficulty version of this attack
fails: the null rule's advantage is measured *within task*, so it is not restating which task
was drawn. But a deeper version lands: "the agent performed no state-changing action" and
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
> frozen and tested on real data. Of the five carrying numeric pass/fail gates on held-out or
> fresh corpora, three failed, one was accepted but is underpowered by its own harm bound,
> and one passed; of the two preregistered without gates, repeated execution fired its
> predeclared negative outcome and alternate-evaluator escalation weakened substantially. In
> every failure a cheaper measurement — a single judge call, a verdict-conditioned rate, or a
> check requiring no inference at all — accounted for as much of the signal as the mechanism
> did. The rule that passed most cleanly was the cheapest, and the only one that reported an
> evidence gap instead of asserting a verdict.**

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
more judging cannot repair missing evidence. (c) The null rule carried more of the deployable
signal than RC1's extraction pipeline at zero inference cost. (d) R3's entire content is
"the required evidence is absent", and it is one of the two rules that survived held-out
validation — the stronger of the two.

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
   (20–30 points) on the same data.
4. A null-baseline comparison showing a semantic detector landing below a no-model check on
   the deployable outcome.

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
| C2 | Sequential stopping gets the same verdicts cheaper | first-to-3: 0 verdict mismatches, −39.8% calls | A | same corpus | textbook method, not ours | "First-to-3 stopping reproduced majority-of-5 verdicts exactly while using 39.8% fewer calls." | ~~"we developed an adaptive evaluation method"~~ |
| C3 | Predeclaration changed the result | 0.543 vs 0.759 | A vs B | 8 candidate pairs, one corpus | post-hoc figure is oracle selection by construction | "The pair chosen on preregistered criteria ranked last of eight on pooled recovery (0.543); post-hoc selection would have reported 0.759 in a document that read identically." | ~~"post-hoc evaluator selection inflates results by 22 points"~~ (n=1 corpus) |
| C4 | Reference-conditioned recovery is not operational | 0.543 vs 0.366 / 0.465 | B | one primary, 8 alternates | exploratory | "P(alternate correct \| primary wrong) was 0.543, while the precision of the overturns a policy would actually perform was 0.366 and 0.465 — the deployable quantity ran 20–30 points lower." | ~~"escalation policies overstate benefit by 30%"~~ |
| C5 | Error directions must be separated | 32 vs 130; 0.469 vs 0.562; pooled φ 6.7×→1.6× | B | one corpus | exploratory | "False alarms outnumbered missed failures 130 to 32, recovery differed by direction, and conditioning φ on the reference label collapsed the spread across eight alternates from 6.7× to 1.6×." | ~~"pooled metrics are invalid"~~ |
| C6 | Deterministic pre-checks did not generalize as a class | R1–R4 held out on 1260 | A | 4 rules, one corpus | n=4; R2 underpowered at n=6 | "Of four deterministic pre-checks frozen before validation, two failed held-out evaluation, one passed but was underpowered by its own harm bound (39.3% at n=6), and one passed as an escalation signal." | ~~"deterministic guards don't work"~~ |
| C7 | A denied veto is worth logging | R1: lift 0.51×, counterfactual 6 helped / 14 harmed | A | one rule | single instance | "R1's signal inverted on held-out data (0.51× lift); the veto it had been deliberately denied would have helped 6 cases and harmed 14." | ~~"never let rules veto"~~ |
| C8 | Evidence-gap escalation has held-out support | R3: 25.6% vs 14.4% | A | one rule, visualwebarena-only firings | 99/133 escalated were already correct; corrects nothing itself | "R3 identified a 133-case subset where the evaluator erred at 25.6% against 14.4% elsewhere; it escalates rather than corrects, and 99 of the 133 were already right." | ~~"UNVERIFIABLE states improve evaluation"~~ |
| C9 | Static tool-class matching failed on a fresh corpus | RC1: 25.3% volume, 1.165× lift, extractor 28/30 | A/FRESH | one rule, 2 domains | 28-record reference noise floor | "On the fresh τ-bench validation, static required-conjunct/tool-class matching did not meaningfully enrich failures within tasks (1.101× within-task), while its extractor passed a label-blind audit at 28/30." | ~~"obligation tracking does not work"~~ |
| C10 | The detector, not the construct, failed | oracle 2.339× vs RC1 1.101×, precision 33.1% / recall 49.3% | D + A | τ-bench | oracle ceiling forecasts nothing about any detector; oracle itself fails the volume gate at 17.0% | "Reconstructed with benchmark-authoritative actions, the target construct carried a 2.339× within-task lift that the production rule recovered at 33.1% precision and 49.3% recall. The oracle establishes that the latent construct carries signal; it does not establish that a production-valid representation of it exists." | ~~"the construct is validated"~~ / ~~"2.339× is achievable"~~ / ~~"representation failure, not an empty abstraction"~~ |
| C11 | The rule fell below a no-model baseline | 1.101× vs null 1.171×, same code path | B | τ-bench | null rule itself fails volume at 24.1% and was preregistered as disqualified; partly constitutive of the outcome | "A check requiring no obligation model — 'did the agent successfully write anything?' — reached 1.171× within-task where the extraction-based rule reached 1.101×." | ~~"semantic machinery is useless"~~ / ~~"the null rule is a better detector"~~ |
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
`scripts/check_synthesis_counts.py` parses this table and asserts the totals in the prose
below, so the two cannot drift apart again.

| # | error | how detected | caught | effect on conclusions | safeguard |
|---|---|---|---|---|---|
| 1 | Alternate-evaluator performance assumed from two float literals (0.95 / 0.05) | Red team asked where the numbers came from | BEFORE — no real data yet | Every synthetic escalation economic result was modelled, not measured | Type is unconstructible without a named artifact or explicit `assumed_because`; refusal fires at point of use |
| 2 | `MIN_ERRORS_FOR_CONDITIONAL = 16` presented as derived | Two-corpus red team traced the derivation to an undeclared 0.5 | BEFORE | Sample-size guidance was wrong by up to 30× (3 errors vs 91, depending on `r*`) | Constant demoted to a presentation warning carrying no verdict |
| 3 | The 0.50 sufficiency rule | Same red team | BEFORE | An economic assumption was printed in the register of a statistical convention | `r*` declared by the caller; no default; absent it, output is NOT DECISION-SUFFICIENT |
| 4 | Pooled recovery used as the headline | Directional decomposition | AFTER | Published in the pooled complementarity report, then corrected. The metric conditioned on a label no runtime system has; it ranked the predeclared pair last on a stratum that was 80% false alarms | Always decompose by error direction before reporting a pooled rate |
| 5 | Pooled φ read as mechanism diversity | Conditional analysis | AFTER | Ranked eight alternates on the stratum where the question does not arise | Check whether one margin dominates one stratum before trusting any 2×2 |
| 6 | Prompt-caching assumed to invalidate repetitions | Re-reading the caching mechanism | BEFORE — pre-inference | Would have disabled caching and raised cost ~26% for no reason | Verify the mechanism before writing a constraint that depends on it |
| 7 | Staged R=2→R=5 continuation gate | Third amendment red team | BEFORE — pre-inference | Would have stopped collection at R=2 and reached the same conclusion by extrapolation instead of measurement | Prefer the unconditional design; keep screens as retrospective analysis, never as control flow |
| 8 | Infeasibility flag nearly used as a rule input | Oracle-leakage audit | BEFORE — pre-validation | Would have produced a rule that "worked" by being told the answer | Leakage class assigned to every input before freezing |
| 9 | A2-task gate preregistered at an unreachable threshold | Post-outcome ceiling computation | AFTER | Published in the first RC1 report as a binding gate. A binding gate could not have been passed by any rule; also inverted the direction of the "fired tasks are easier" reading | **Compute a metric's ceiling before preregistering its threshold**; prefer non-saturating statistics |
| 10 | τ-bench join-key collision | One impossible row in a qualitative sample | AFTER | **The most consequential of the thirteen: already published in the first RC1 report.** 33.3% of records scored against the wrong agent; six published figures wrong | Assert the join is 1:1 on the full identity tuple; a row your own classifier cannot emit is never an edge case |
| 11 | F4 named dominant harm mechanism | Forensic re-audit on corrected data | AFTER | Published in the post-outcome decomposition. An overcorrection drawn from the collided sample; F6 is dominant | Re-derive every mechanism claim after a data-integrity fix, not just the headline metrics |
| 12 | "Right for the right reason" read as support for obligation modeling | Null-rule probe + confound check | AFTER | Caught before it was published as support. Would have licensed a successor on an oracle-selected, agent-confounded subset | Run the null baseline before crediting a mechanism |
| 13 | **Null-rule headline compared two different outcome variables** | Like-for-like recomputation during this synthesis | AFTER | Caught pre-publication. Would have published "null rule beats the construct 7.189× to 2.339×" — false, and it would have wrongly narrowed a correct finding | **Recompute every compared statistic in one code path and prove the path by reproducing an independently published number first** |

Item 13 deserves emphasis because of what it repeats. The probe document had *already listed*
"these were not recomputed side-by-side from a single code path" in its own limitations
section — and then headlined the comparison anyway. This is the same class of error as items
4 and 5 (a rate compared against the wrong conditional), committed immediately after
documenting it. The project's own recurring lesson is that **naming an error does not
inoculate you against it**; only re-auditing the new work against the last correction does.

**Candidate theme wording.** *"Assurance research itself needs assurance"* is accurate but
too cute, and it overclaims by implying a general programme. The defensible version:

> Thirteen process errors were found across 62 commits. **Six** were caught before the
> outcomes they would have affected were visible — by red teams, freezes and pre-inference
> gate checks. **Seven** were caught only afterwards, and the most damaging of those had
> already been published: a join-key collision that scored a third of the records against
> the wrong agent. The mechanisms that caught them are the ordinary ones: predeclaration,
> quarantine, negative controls, and recomputing a comparison in a single code path.

The ratio is itself a finding, and it is not flattering: **fewer than half the process errors
were caught by the safeguards that ran ahead of the data.** The majority were caught by
re-auditing results that had already been computed, and in several cases already written up.
Preregistration and quarantine did the work they were designed for; they did not substitute
for reading the output again.

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
| **A** assurance economics | Weak — the economics are class C synthetic; the only verified spend is $46.18 | Low | Medium | Medium | **High** — invites invented ROI | Poor |
| **B** falsification study | **Strong** — 7 mechanisms tested on real corpora; 3 gated failures, 1 ungated negative outcome, 1 substantial weakening | Medium | **High** | High | Low | **Excellent** — matches the ledger exactly |
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
   −39.8% calls from stopping. The synthetic cost tables stay in the appendix, labelled.

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
| Killing own work | Seven mechanisms proposed and tested; three failed their own gates, one fired its predeclared negative outcome, one weakened; the successor branch closed rather than extended |

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
  single thing most worth auditing. Quote the disposition table, not a fraction.
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
- **"Nine process errors were caught before outcomes; four afterwards"** — the count is
  **6 / 7**, now derived from the table by `scripts/check_synthesis_counts.py`.
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
| 3 | **Three-lift comparison** — oracle 2.339× / null 1.171× / RC1 1.101× on the deployable outcome, with the 15% volume gate drawn as a vertical line all three cross | C10 + C11 — the construct is real, the detector is not, and even the ceiling is unaffordable | **Yes, now.** Single code path; reproduces published values | Main text |
| 4 | **Reference-conditioned vs operational** — 0.543 against overturn precisions 0.366 / 0.465, with stratum sizes (32 vs 130) shown as bar widths | C4 + C5 — the most transferable finding | **Yes.** Exploratory, must be labelled so | Main text |
| 5 | **Claim lifecycle timeline** — 31 stages on an axis, marking the 12 withdrawals/narrowings and the 13 process errors, colour-split by caught-before vs caught-after outcomes | The primary narrative (B through D) | **Yes**, from §1 and §10 | Main text, as the opener |

**Appendix candidates, not main text:** predeclared-vs-post-hoc pair scatter across all eight
(folds into figure 4); held-out R1–R4 results (the table is clearer than a chart at n=4);
evidence-layer diagram for the 15 cases (n=15 does not justify a figure).

**Explicitly rejected:** a cost-versus-assurance-gain plot. The cost axis would be almost
entirely synthetic, and the one real point ($46.18 for zero gain) is a sentence, not a curve.

---

## 16. Is the research branch finished?

**Yes. Stop experimenting and publish.**

Against the stated bar for another experiment — it must materially affect the central claim,
have a clean fresh validation surface, not merely rescue a failed mechanism, and offer enough
information gain to justify delaying synthesis:

- A successor detector **fails criteria 1 and 3**: it would exist to rescue F7/F8, and §5
  of the successor probe shows the corrective state→class mapping is per-domain policy that
  would still have to clear a 1.171× floor.
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
directions. Sequential first-to-3 stopping reproduced majority-of-5 verdicts exactly using
39.8% fewer calls. *Class A. Scope: one judge, one configuration, judge stage only.*

**T1.2** The quantity that makes escalation look attractive is not the quantity a policy can
run on: `P(alternate correct | primary wrong)` was 0.543, while the precision of the
overturns a deployed policy would actually perform was 0.366 and 0.465 — 20 to 30 points
lower on the same cases. *Class B. The most transferable finding in the project.*

**T1.3** Preregistration changed the reported result by a measurable margin: the pair chosen
on frozen pre-outcome criteria ranked last of eight on pooled recovery (0.543 vs 0.759 for
the post-hoc best), in a report that would have read identically — and the pooled metric was
itself later shown to be the wrong conditional, on which the same pair ranks tied first.
*Class A vs B.*

**T1.4** On a fresh, previously untouched corpus (τ-bench, 1,980 records), a static
required-conjunct rule failed both binding preregistered gates (25.3% volume against <15%;
1.165× trajectory lift against ≥1.50×) while its extractor passed a label-blind audit at
28/30 — and on the deployable outcome it landed *below* a baseline requiring no model at all
(1.101× vs 1.171× within-task). The target construct itself was not empty (2.339× via
benchmark-authoritative actions), so this is a recovery failure, not an abstraction failure.
*Classes A/FRESH, B and D.*

### Tier 2 — supported but scoped

- **T2.1** Of four deterministic pre-checks frozen before held-out validation on 1,260
  quarantined-split cases, two failed, one passed but is underpowered by its own harm bound
  (39.3% at n=6), and one passed as an escalation signal. *n=4.*
- **T2.2** R1's signal *inverted* on held-out data (0.51× lift), and the veto it had been
  deliberately denied would have helped 6 and harmed 14. Log the counterfactual of any
  authority you withhold. *Single instance, but decisive within it.*
- **T2.3** An explicit evidence-gap state has held-out support as an *escalation* signal
  (25.6% vs 14.4% evaluator error), with the rider that it corrects nothing and that 99 of
  the 133 cases it escalated were already correct. Its value is entirely a function of review
  cost.
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
> annotated agent trajectories; τ-bench, 1,980 trajectories over 165 tasks). Of the five
> carrying numeric pass/fail gates on held-out or fresh data, three failed, one was accepted
> but is underpowered by its own harm bound, and one passed. Five repeated executions of a deployed LLM judge —
> 5,530 calls, $46.18 — produced intermediate correctness on only 20 of 1,106 cases, and
> majority voting was marginally worse than a single call in both error directions;
> sequential stopping reproduced identical verdicts using 39.8% fewer calls. An alternate
> evaluator appeared to recover 54.3% of the primary's errors, but the precision of the
> overturns a deployed policy would actually perform was 20 to 30 points lower, because the
> attractive statistic conditions on a ground-truth label no runtime system has. Two of four
> frozen deterministic pre-checks failed held-out validation, one with an inverted signal
> whose withheld veto would have harmed more cases than it helped. On a fresh corpus, a
> rule that tracked user-stated obligations against executed tool classes fell below a
> baseline requiring no model at all. What survived is narrower and cheaper than what was
> proposed: the cleanest result is an explicit "required evidence is absent" state, which
> earned held-out support as an escalation signal while asserting no verdict of its own,
> though it corrects nothing itself and 99 of the 133 cases it escalated were already
> correct. The negative results matter
> because each mechanism was plausible enough to ship, and the instruments that killed them —
> preregistration, held-out quarantine, negative controls, and recomputing comparisons in a
> single code path — cost far less than the mechanisms would have. Thirteen process errors
> in the research itself are documented alongside the findings, including one that survived
> into a published report.

---

## 19. Thesis

**One sentence, strongest defensible:**

> Across two public agent-evaluation corpora, most of seven preregistered evaluator-assurance
> mechanisms did not survive their own validation — three failed numeric gates outright, one
> fired its predeclared negative outcome, and one weakened substantially — and in each case a
> cheaper measurement carried as much of the signal; the rule that survived most cleanly was
> the one that reported missing evidence instead of asserting a verdict.

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
construct: the oracle reconstruction beat the null rule 2.339× to 1.171×. Only the
*production detector* lost.

A fifth reason applies to an earlier version of the defensible thesis itself, not just the
overclaim. It read:

> ~~"Across two public agent-evaluation corpora, four of five preregistered evaluator-assurance mechanisms failed their own thresholds … with the sole survivor being the mechanism that reported missing evidence."~~

That arithmetic had **no enumerated denominator**, counted an underpowered
acceptance as a failure, and contradicted this document's own §2 boundary rule by ignoring
R2's preregistered ACCEPTED status. It is withdrawn in favour of the disposition table at
§3.6. The lesson generalises: **a synthesis about catching attractive errors cannot contain
attractive arithmetic that is itself unaudited.** A clean ratio is the most repeatable
sentence in any write-up and therefore the one most worth checking last.

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

Five things, and nothing larger:

1. **That this deployed temperature-0 / seed-0 judge had too little useful repeat-execution
   variability for repetition to pay — and that they should measure their own deployed
   configuration before assuming repeated sampling will help.** The scope is one judge, one
   corpus, the judge stage only. The measurement on cached judgments is free; confirming it
   with 5,530 fresh executions cost $46.18.
2. **That "the second evaluator catches X% of the first one's errors" is the wrong number,**
   and that the right one — the precision of the overturns actually performed — is
   materially lower. They will recompute their own.
3. **That evaluator-pair and rule selection must be frozen before outcomes are visible,**
   because here it moved the headline by 21.6 points in a document that would have read
   identically either way.
4. **That a new assurance mechanism should be required to beat a no-inference baseline
   before its machinery is credited** — and that this gate is cheap enough that there is no
   excuse for skipping it.
5. **That preserving corrections, failed gates and data-integrity defects makes the
   evidentiary trail auditable** — every figure here can be traced to the commit that
   produced it and to any later commit that revised it, including a join bug that corrupted
   a third of the records and survived into a published report. This is a property of the
   artifact, not a measured result: the project ran no comparison between artifacts that
   disclose their failures and artifacts that do not, and cannot claim one is more trusted
   than the other. What it can claim is that a reader is able to check.

What they should *not* believe: that any of this generalizes to other judges, other
configurations, or other corpora. It has not been tested, and this project's own record is
that untested generalizations are where the errors live.
