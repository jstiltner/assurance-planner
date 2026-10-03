# Evaluator Assurance: What Survived

This project investigated a practical question for teams deploying LLM-based evaluation
pipelines: which evaluator-assurance mechanisms actually work when tested against real data
with preregistered criteria?

It is a **falsification study**, not an architecture. Seven candidate mechanisms were
frozen and tested on two public corpora over a short research sprint (2026-09-26 →
2026-09-29, 62 commits). Most did not survive.

The full technical report is at [`docs/research_synthesis.md`](docs/research_synthesis.md).
The five-minute skeptical read is [`docs/FINDINGS.md`](docs/FINDINGS.md).

---

## What I tested

**Repeated execution** — run the same LLM judge R times; use majority voting to recover errors.

**Alternate-evaluator escalation** — route primary errors to a second, structurally different judge.

**Deterministic pre-checks (R1–R4)** — four frozen rules designed to detect specific structural
failure conditions before the primary judge runs. Evaluated on a quarantined held-out split.

| rule | fires when | criterion it was given |
|---|---|---|
| R1 | the agent calls `report_infeasible` while asserting the task was completed | **direction only** — firings more enriched for reference-fail than base rate |
| R2 | the agent reports it did not accomplish a goal phrased as an imperative modification | **numeric gate** — veto SUCCESS; `harmed ≤ helped / 3` |
| R3 | the goal names an image and the evaluator's input contains no image — structural and answer-independent | **numeric gate** — escalation volume <15%; evaluator error higher on escalated than on remainder |
| R4 | the trajectory ends on a search-results page | **direction only** — same as R1 |

Only R2 and R3 carry numeric accept/reject gates. R1 and R4 change no verdict, so §7 of
`docs/repair_validation_preregistration.md` gave them a direction and no threshold.
*Corrected 2026-10-02 — R4's published `REJECTED` label was post hoc: it met the only
criterion it was given (1.20×), and the evaluator-error contrast it was rejected on was never
a criterion.*

**Fresh-corpus static matching (RC1)** — a rule that extracts user-stated obligations and checks
whether executed tool calls satisfy them. Tested on τ-bench, a corpus not used for any earlier
result in this project. (*Corrected 2026-10-02:* earlier drafts said ~~"never touched"~~. The
τ-bench files were read during rule scoping with `reward` and `info` withheld by code — the
labels were blind, the corpus was not untouched.)

---

## What the experiments found

**Repeating this judge did not help.** Five repeated executions of the deployed
`gpt-4o-2024-11-20` judge (temperature 0.0, seed 0) on 1,106 AgentRewardBench trajectories
produced intermediate correctness (k between 1 and 4) in only 20 cases. Majority-of-3 and
majority-of-5 were marginally *worse* than a single call in both error directions. Sequential
first-to-3 stopping used 39.7% fewer calls (2,194 calls saved of 5,530; 3,336 were used) at
verdicts identical to majority-of-5 **by construction** — the two rules cannot disagree once
three of five draws agree, so the call saving is the only empirical part. This read "reproduced
majority-of-5 verdicts exactly" until 2026-10-03, which states an identity as a result.
Cost: 5,530 analysed calls, $46.18 — $49.50 billed, because 356 duplicate valid calls were
dropped before analysis and paid for regardless.

*Scope: one judge, one configuration, judge stage only.*

**The recovery statistic was not the operational quantity.** The predeclared
alternate-evaluator pair recovered 54.3% of the primary's errors — conditional on knowing
which cases were errors, a label no runtime system has. The precision of the overturns a
deployed policy would actually perform was 36.6% / 46.5%. Compared direction by direction,
that is about 10 points lower: catch 46.9% against overturn-to-fail 36.6% (10.3 pp), rescue
56.2% against overturn-to-pass 46.5% (9.7 pp). The gap is real and robust on the false-alarm
side — positive for all eight alternates, 9.7 to 46.0 pp — and is **not** general on the
missed-failure side, where it ranges −14.7 to +23.1 pp and reverses sign for two alternates.
Blanket adjudication on the primary's FAIL verdict is a raw-count loss for five of the eight
candidate pairs, and non-positive for all eight only if a missed failure is weighted at least
1.057× a false alarm.

*Corrected 2026-10-02 (external reproduction).* This paragraph said ~~"20–30 points lower"~~ and
~~"non-positive against all eight"~~. The first subtracted the two direction-specific overturn
precisions from 0.543, a figure pooled across both error directions; the direction-matched
gap is ~10 points. The second was true only under an unstated error-cost weighting. See
`docs/agent_reward_bench_directional.md` §12.

**Predeclaration changed the answer.** The predeclared pair ranked last of eight on pooled
recovery (0.543 vs 0.759 post-hoc best), in a report that would have read identically either
way. Post-hoc pair selection would have reported a 21.6-point higher headline on the same
data.

**Static tool-class matching failed fresh-corpus validation; the target construct was real.**
RC1 failed two binding preregistered gates on τ-bench (1,980 records, 165 tasks): volume
25.3% against a <15% ceiling; trajectory lift 1.165× against a ≥1.50× bar. The extractor
passed its label-blind **precision** audit at 28/30 — 25/27 held strictly out-of-sample, since
three of the 28 passes are cases the same audit's first pass found defective and fixed before
its second pass scored them; recall was not measured (disclosed 2026-10-02). On the deployable
outcome, within-task: oracle
construct 2.339× (94 tasks), null rule requiring no model 1.171× (80 tasks), RC1 1.101×
(109 tasks). The detector **did not outperform** a rule containing no obligation model —
but it did not fall below one either: paired on the same task resamples, NULL − RC1 =
+0.078 [−0.327, +0.575], and under Mantel–Haenszel stratification neither the null rule
(1.237 [0.904, 1.650]) nor RC1 (1.150 [0.979, 1.352]) is distinguishable from 1. Only the
oracle separates (2.054 [1.752, 2.530]). The oracle establishes that the latent construct
carries signal; it does not establish that a production-valid representation of it exists.
(Ordering claim corrected 2026-10-02 — see `docs/rc1_successor_probe.md` §1.)

**What was narrowed on reproduction (R3):** An explicit "required evidence is absent" state
passed its preregistered test as an escalation signal — 25.6% vs 14.4% evaluator error on a
133-case subset, Fisher p = 0.0015 — and this README called it the project's one clearly
positive result until 2026-10-02. (The heading said ~~"What did not survive reproduction"~~
until 2026-10-03. The disposition did survive: the test ran as specified and met its
criterion. What shrank is the reading.)

Most of the pooled separation is benchmark identity. All 133 firings are visualwebarena, which
carries the highest judge-error point estimate of the four slices (22.4%, against 19.8% on
webarena, 11.1% on workarena and 3.9% on assistantbench), so the pooled test compares one
slice against three others rather than escalated cases against unescalated ones. Within
visualwebarena the contrast is **25.6% vs 19.7%, Fisher p = 0.26** — about half the
separation, and not significant. The residual stays positive and in the predicted direction,
so the rule is unproven at this power, not refuted. Reproduce with
`scripts/arb_r3_slice_check.py`.

The paragraph this replaces argued R3 escaped circularity because its condition is
structural, answer-independent, and frozen before its error rate was known. All three are
still true and none of them help: "the goal names an image the evaluator cannot see" is
near-perfectly correlated with the benchmark built out of image-grounded tasks.
Preregistering a rule does not control for a covariate the test never measured.
The risk had already been written down — *"Any rule that escalates the cases a judge finds hard
will pass a test of the form 'is the judge worse on the escalated subset'. That test is
necessary, not sufficient, and the preregistration should have said so."* That is from
`docs/repair_validation_results.md`, a **post-results** caveat, not from the preregistration
(this README said "preregistration" until 2026-10-02, which gave the project credit for
foresight it did not have). It was written after R3's numbers were in, and *Disposition:
ACCEPTED* follows it two paragraphs later. `docs/research_synthesis.md` separately recorded
"visualwebarena-only firings" in a scope column. Both facts were on paper; nobody joined them.

R3 is not refuted, and its preregistered disposition does not move — it met its criterion and
the test ran as specified, so relabelling it now on an analysis the preregistration never
named would be the same post-hoc move criticised two sections above. What is withdrawn is the
reading. A +5.8 pp within-slice residual in the predicted direction at n=133 vs 157 is
underpowered, not absent, and settling it needs a corpus where the evidence gap occurs outside
one benchmark. It corrects nothing itself; 99 of 133 escalated cases were already correct. It
should not be cited as a positive result in the meantime.

---

## Why the negative results matter

Each mechanism was plausible enough to deploy. What stopped them was preregistration,
held-out quarantine, negative controls, and cheap-baseline benchmarking. The same discipline
caught 13 process errors in the research — including a join-key collision affecting 33%
of records, found by tracing a single anomalous row. The instruments that would have deployed
these errors are the same ones that prevented them.

**That is not the whole count, as of 2026-10-02.** An independent external reproduction found
**eleven more** — ten wrong or over-strong summary figures and protocol descriptions, and a
confound in R3's escalation reading (see above). The record is therefore **13 process errors
found during the study (6 before the relevant outcomes were visible, 7 afterwards) and 11 more
found by external reproduction**, 24 rows in total. The two are counted separately rather than
summed into one triple: the 13 is what this project's safeguards caught about themselves and it
did not change, and the 11 is the part no safeguard here caught. None of the eleven needed new
data; all were recomputable from artefacts already in this repository. The honest version of
this section is therefore that the safeguards caught what they were designed to catch and did
not substitute for an outside reader re-deriving the summary figures. Full table:
`docs/research_synthesis.md` §10.

The practitioner lesson: *before buying more inference, ask whether the evidence required
to make the decision exists and whether a cheaper observable already carries the signal —
then, if answering that question takes more machinery than the evidence costs, just buy
the evidence.*

---

## Corpora

| corpus | records | tasks | evidence class |
|---|---|---|---|
| [AgentRewardBench](https://github.com/McGill-NLP/agent-reward-bench) (rev `b6d17e6`, arXiv:2504.08942) | 1,106 annotated trajectories | — | Preregistered / held-out |
| [τ-bench](https://github.com/sierra-research/tau-bench) (Sierra Research; `historical_trajectories/`, MIT) | 1,980 trajectories | 165 | Fresh-corpus, read **label-blind** until the RC1 freeze |

*Corrected 2026-10-02.* The τ-bench row read ~~"never touched before RC1 test"~~. The files
were in fact read during scoping to establish that the rule's inputs exist — record counts,
task and trial ids, message roles, tool-call names — with the `reward` and `info` fields
programmatically withheld at inspection time (`docs/required_conjunct_scoping.md` §8.4). The
blinding that actually protected the test was label-blindness enforced in code, not an
untouched corpus. Stating it as "untouched" claims a stronger protocol than was run.

---

## Audit trail

| document | contents |
|---|---|
| [`docs/FINDINGS.md`](docs/FINDINGS.md) | Claim-scope table, Tier-1 findings, figures |
| [`docs/research_synthesis.md`](docs/research_synthesis.md) | Full 21-section technical report and internal-consistency audit |
| [`docs/repair_validation_results.md`](docs/repair_validation_results.md) | R1–R4 held-out results with counterfactuals |
| [`docs/repetition_study_findings.md`](docs/repetition_study_findings.md) | R=5 repetition study |
| [`docs/rc1_forensic_audit.md`](docs/rc1_forensic_audit.md) | RC1 post-outcome analysis and correction chain |
| [`docs/rc1_successor_probe.md`](docs/rc1_successor_probe.md) | Null-baseline comparison and branch closure |

Failed gates, withdrawn claims, and corrected figures are preserved in the commit record and
in-place in every document rather than deleted. That a preregistration and quarantine
materially change reported results is not asserted — it is evidenced here.

```
python scripts/generate_figures.py       # Figures 1–4 from source data
python scripts/check_public_claims.py    # Lint README and FINDINGS for superseded claims
python scripts/check_synthesis_counts.py # Assert table-derived totals in the synthesis
```

---

*The planner implementation and synthetic benchmark fixtures remain in this repo for
reproducibility. They are class-C synthetic infrastructure and are not findings.
See [`docs/research_synthesis.md`](docs/research_synthesis.md) §2 for the evidence-class taxonomy.*

> Given a specific AI failure mode, what a team is trying to accomplish right now, an
> organisational assurance requirement, and a set of evidence-producing mechanisms with
> *measured* reliability and *known* prices — what is the least-cost admissible way to
> get the evidence?

```
plan : (DevelopmentContext, FailureMode, AssuranceProfile, World) -> PlanningResult
```

No LLM, no network, no clock, no randomness inside the planner. The world it reasons
about is stochastic; the reasoning is not.

```bash
pip install -e .
assurance-plan scenarios/voice_early.yaml --context nightly
assurance-plan characterize-evaluator data/judge_runs_systematic.yaml
assurance-plan benchmark-policies data/judge_runs_mixed.yaml --assume-alternate-rates 0.95 0.05
assurance-plan characterize-alternate data/SYNTHETIC_paired_runs.yaml
```

The fourth command takes an optional `--break-even-recovery R`. It has no default and none
is suggested here, because any number printed in a README becomes the number people use.
Without it the command reports what it observed and declines to call it decision-sufficient.

The second command is the planner's own falsifier. See
[Are the inputs measurable?](#are-the-inputs-measurable) — the short answer is that on
one of the three shipped fixtures they are not, and the planner cannot tell.

The third asks whether a planner is needed at all. It replays every established
evaluation policy — fixed-N, majority-race early stopping, interval stopping, a
probe-and-escalate cascade — against the same recorded observations under one cost model,
on held-out folds, alongside a blind escalation control sized to match. It prints the
table and **refuses to name a preferred policy**, because choosing inside the Pareto set
requires a price for a missed failure, which is policy rather than measurement.

Results so far, on synthetic fixtures: repetition stops buying anything after six
observations; repetition cannot touch a case the judge is confidently wrong about; and on
one fixture the blind control beats the candidate policy outright. **What escalation does
instead is not a result here** — every escalation figure in those fixtures is computed from
an alternate source whose accuracy was declared rather than measured, and whether
escalating pays at all is a question about a break-even recovery nobody has declared. The
repetition half has been measured under this repository's assumptions; the escalation half
has been priced under them, which is a different verb.
See [`docs/policy_benchmark_findings.md`](docs/policy_benchmark_findings.md) for all of it
including the parts that argue against continuing,
[`docs/real_experiment_protocol.md`](docs/real_experiment_protocol.md) for the real-data study
and its ten kill criteria written before any real data exists, and
[`docs/experiment_red_team.md`](docs/experiment_red_team.md) for the pass that found the
protocol's original sample size could not test its own central claim.

The fourth command is the instrument for the question those documents said to ask next:
does a second, more expensive source get right what the primary gets wrong? **It has never
been run on real data, because there is no real alternate source and no human-labelled
corpus — every case in `data/` is generated.** The benchmark used to price escalation from
a hard-coded sensitivity of 0.95 and a false-positive rate of 0.05 that no study produced;
those literals are gone, and a policy that escalates now raises unless the caller supplies
a qualification artifact or says out loud that it is assuming. Hence
`--assume-alternate-rates` above, which is the only way to reproduce the published
benchmark table. Every cell of `characterize-alternate`'s decision table reads
`UNMEASURED`, and no code path can write anything else into one; the command **exits
non-zero** on a study that measured nothing — and also on one that measured something and
was never told what would count as success, so a pipeline cannot get a green result out of
either.

That second clause is a correction. The report used to compare the recovery rate to **0.5**
and call the comparison a support rule. 0.5 is not a statistical quantity; it encodes "the
alternate is right more often than not on the primary's mistakes", which is rhetorically
satisfying and economically empty. The threshold that matters is the break-even recovery
`r*` at which escalation starts to pay for itself; it is set by consequence, prevalence and
price rather than by arithmetic, and the sample size needed swings thirtyfold across its
plausible range. `r*` is now supplied with `--break-even-recovery`, on the same footing as
`--max-error`, and is never inferred from the data being analysed.

What would have to be collected first is in
[`docs/alternate_source_collection_protocol.md`](docs/alternate_source_collection_protocol.md).
The short version is that **under representative sampling** the denominator of the recovery
rate is *primary errors*, not cases, so an accurate primary makes that design expensive
rather than cheap. The qualifier is doing work:
[`docs/alternate_corpus_red_team.md`](docs/alternate_corpus_red_team.md) examines a
failure-enriched design for which it does not hold, and finds the design sound but not
applicable here — it buys alternate observations rather than labels, and labels are the
thing this project has none of.

## What it decides

Nothing in this list may be written into a scenario file. The loader rejects all nine
keys at any depth, and a test tampers with a real scenario to prove it.

| decision | derived from |
|---|---|
| which mechanism | least cost among the admissible |
| which population, and how much of it | goal coverage requirement + `sampling_allowed` |
| run percentage | always paired with its denominator; never a bare number |
| replication count `n` | measured sensitivity/FPR + `maximum_error_requirement` |
| decision threshold `k` | smallest `k` bounding both miss and false-alarm at `n` |
| escalation band | `1..k-1`; empty when `k=1`, so deterministic paths get no hop |
| escalation target | cheapest qualified source that adds *different* evidence and satisfies the same policy |
| cadence | cost per *day*, which is what makes nightly cheaper than per-change |
| sync vs async | whether the intent must gate the change |
| human allocation | `human_confirmation_required`, bounded by measured capacity |

## What it is not

- **Not an assurance authority.** It never decides how much risk is acceptable. That
  arrives as an `AssuranceProfile` and the planner obeys it.
- **Not an optimiser.** It enumerates, rejects, and sorts. No solver, no search
  heuristic, no tuned coefficients. If ranking ever needs a weight to make a scenario
  come out right, the abstraction has failed and that should be reported, not patched.
- **Not an executor.** It emits a plan. It does not run evaluations, call models, or
  orchestrate a prove-red cycle.
- **Not a governance DSL.** `AssuranceProfile` has eight structured fields and an opaque
  `profile_ref`. A field only exists if changing it can change which plans are
  admissible — there is a test that flips every one of them and asserts the outcome
  moves, and a second test asserting `profile_ref` changes nothing at all.
- **Not validated.** The qualification numbers in the three scenarios are plausible, not
  measured, and Scenario A's error requirements were reverse-engineered from the
  replication counts they were meant to produce — stated in the file itself, and
  asserted in a test so it stays stated. See `docs/red_team_review.md`.
  `data/REAL_arb_*` is the exception and a narrow one: two real evaluator pairs imported
  from AgentRewardBench, 1,106 expert-labelled agent trajectories each, marked
  `synthetic: false`. No scenario consumes them and none should yet — they cover one
  failure mode, carry no latency, and are single-shot, so they cannot qualify a source
  for a plan. What they do establish is that assuming evaluator independence overstates a
  two-source system's joint accuracy on that population: on the stratum that matters for
  assurance — reference failures, where both evaluators can only *miss* — the two err
  together at odds ratio **9.4** (φ **+0.250**, risk ratio **4.93×**, n=811). On the
  false-alarm stratum the dependence is weaker (OR 4.2, RR 2.78×, n=295).
  ~~"about threefold … measured phi +0.323"~~ was the **pooled** figure (RR 3.92×) and is
  superseded 2026-10-02: pooled φ is close to a restatement of the false-alarm stratum,
  because this primary puts almost all its errors there (FPR 0.441 vs FNR 0.040), and it
  orders the eight candidate alternates almost opposite to the failure stratum (1/8
  positional agreement — `aer` leads on pooled φ and is **4th of 8** on failure-stratum φ).
  Note also that failure-stratum dependence is **high for every alternate tested**, OR
  **5.08 to 11.11**, so this is a property of the corpus, not a discriminating measurement
  of any one pair. See `docs/agent_reward_bench_gate1.md` for the predeclaration,
  `docs/agent_reward_bench_findings.md` for the result, and
  `docs/agent_reward_bench_conditional.md` for the stratified analysis.
- **Not a measurement system.** It consumes sensitivity and false-positive rate. It
  does not produce them, and `characterize-evaluator` exists to argue that consuming
  only those two numbers is the planner's largest remaining assumption.
- **Not novel in its mechanisms.** Judge nondeterminism, adaptive sampling, early
  stopping, judge cascades, selective human escalation and uncertainty calibration are
  all established work, and `docs/architecture.md` §10.1 lists them so that none can be
  quietly renamed as a finding here. The only candidate claim is a systems one — §10.2 —
  and §10.3 says what would falsify it.

## The three scenarios

**A — `scenarios/voice_early.yaml`.** Early voice-agent development. One world, four
contexts, and the claim under test is that mechanism, scope, replications and cadence
are four separate dimensions rather than one:

| context | mechanism | scope | n | cadence | cost |
|---|---|---|---:|---|---:|
| inner_loop | deterministic simulator | 1 case | 1 | per change | 2.0 min, $0 |
| checkpoint | judge | 20 cases | 1 | per checkpoint | 40 min, $1.25 |
| nightly | judge | 20 cases | **7** | nightly, async | 4.7 h, $8.75 |
| discovery | judge | 20 cases | 1 | nightly, async | $1.25 |

The 2 min / 40 min / ~5 h / ~$10 hierarchy the real team lived is reproduced as
`cases × replications × 120s`, and none of those figures appears anywhere in the repo.
`discovery` is the context worth staring at: it buys the **expensive** judge over the
**free** simulator, because only an open-ended source can surface a failure its
criterion did not anticipate.

**B — `scenarios/duplex_silence.yaml`.** A known, machine-verifiable full-duplex
silence defect. The planner selects the deterministic oracle at n=1 for $0. The two
LLM judges are *admissible* — qualified, available, twelve prove-red observations each
— and lose on price:

```
frontier_judge   -> admissible but dominated on cost: $12.6000/window vs $0.0000/window
transcript_judge -> admissible but dominated on cost:  $3.7500/window vs $0.0000/window
```

That distinction is the whole point. No rule anywhere says "do not use a judge." The
oracle already reports `P(miss)=0`, so extra sensitivity buys no assurance and the
comparison collapses to price. A second call with `assess_blast_radius` buys the broad
20-case suite once at checkpoint cadence, not on every debugging iteration.

**C — `scenarios/clinical_factual.yaml`.** A hypothetical high-consequence factual
mismatch. Two contexts share a world, a set of mechanisms, a set of qualification
measurements and a set of prices. **Only the `AssuranceProfile` differs**, and the
answer moves six orders of magnitude:

| | strict | routine |
|---|---:|---:|
| cost | $740.48/day | $0.0004/day |
| human minutes | 480/day | 0 |
| replications | 3 | 1 |

`sampling_allowed=false` rejects every sampled plan; `human_confirmation_required=true`
rejects every fully automated one; `authoritative_source_required=true` rejects the
judge and also binds the *escalation* target, so an ambiguous case cannot be routed
around the constraint that selected the primary. No clinical vocabulary appears in any
planner module — there is a test that greps for it.

## Changing an input changes the plan

Take Scenario A's nightly release gate and make the judge **less noisy**, changing
nothing else — one measurement in the qualification registry, no price change, no
policy change:

| measured sensitivity | replications | threshold | wall clock | cost/day |
|---:|---:|---:|---:|---:|
| 0.70 | 7 | 3 of 7 | 4.7 h | $8.75 |
| 0.80 | 6 | 3 of 6 | 4.0 h | $7.50 |
| 0.90 | 3 | 2 of 3 | 2.0 h | $3.75 |
| 0.95 | 3 | 2 of 3 | 2.0 h | $3.75 |

Nothing in the repo maps sensitivity to a replication count. The planner searches for
the smallest `n` at which some threshold `k` bounds *both* the miss probability and the
false-alarm probability below the profile's `maximum_error_requirement` of 0.05. A
better judge is worth 2.7 hours of nightly wall clock and $5 a day — and the 0.90 → 0.95
row shows the improvement saturating, because at that point `n` is being held up by the
false-alarm side, not the miss side.

An economic input does the same. Repricing the judge with `parallelism=8` drops a
40-minute suite to 5 minutes and makes it admissible inside a 10-minute budget it
previously missed — without touching a single qualification row.

## Are the inputs measurable?

The planner reduces an evaluator to two numbers. Everything above assumes that
reduction is fair. `characterize-evaluator` exists to test it, and on the shipped
fixtures it does not survive.

**Qualification is now keyed by what it was measured against.** The key is
`evaluator version × failure-mode version × population × behaviour distribution`. The
`distribution_id` is a *declaration* by the system's owner, not something inferred from
a build hash — so a rebuild that changes nothing behavioural keeps every row, and
declaring a move orphans them all at once. A price change still invalidates nothing;
an evaluator version bump still invalidates everything. A miss is diagnosed as
`qualification_stale` rather than a bare absence, so the rationale can name the
distribution the evidence actually came from.

**Rates are no longer storable.** A qualification row carries counts —
`positive_cases`, `true_positives`, `negative_cases`, `false_positives` — and the rate
is derived. A scenario cannot assert a sensitivity its sample size does not support,
because there is nowhere to write one down. Each rate reports a **Wilson score
interval**, chosen over the normal approximation because the latter is zero-width at
p=0 and would let a 30-for-30 oracle claim certainty.

**Conservatism is a policy, not a default.** `AssuranceProfile.estimator` selects
`point` or `conservative` (lower bound on sensitivity, upper bound on FPR). It defaults
to `point`, so nothing was silently repriced. Its bite varies:

| scenario | point | conservative |
|---|---|---|
| A / nightly | n=7, $8.75/day | n=12, $15.00/day |
| B / verify (oracle, 15 for 15) | n=1, $0 | **no admissible plan at all** |
| C / production_guard (n=400) | n=3, $740.48/day | n=3, $740.48/day |

Row B is the uncomfortable one: a deterministic oracle measured 15 times is not exempt
from its own sample size, and under conservative planning the scenario has no answer.
That is either the correct conclusion or evidence the policy is too blunt; the repo
does not claim to know which.

**The two-number summary loses the thing that matters.** Three adversarial fixtures
live in `data/`. A and B were tuned to nearly the same pooled sensitivity from
structurally opposite evaluators:

| | A `judge_runs_noisy` | B `judge_runs_systematic` |
|---|---|---|
| pooled sensitivity | 0.672 | 0.682 |
| **planner's answer** | **n=7, k=3** | **n=7, k=3** |
| mean same-case agreement | 0.732 | **0.896** |
| dispersion φ | 1.67 | 6.82 |
| effective runs (of 192) | 115 | **28** |
| cases repetition cannot fix | 0 | 7 |
| empirical P(miss) at n=7 | 0.142, falling | 0.289, **flat** |

The planner cannot tell them apart. B agrees with itself *more* than A does, because
being reliably wrong is a form of reliability — which is why the report prints
"consistently and confidently wrong" as a separate list from the disagreement ranking.
B fires the independence warning and exits non-zero; A does not.

**But φ is necessary, not sufficient.** Fixture A passes the clustering check and
*still* fails the replication analysis: no n in 1..12 meets the 0.05 target on per-case
rates, while the model claims n=7 suffices. The cause is not clustering. Averaging
P(miss) over heterogeneous per-case rates is not P(miss) at the mean rate, so **case
heterogeneity, not within-case correlation, is the dominant error** — and the
empirical-versus-model curve, not the dispersion statistic, is the diagnostic that
catches it. A constructed homogeneous fixture in the test suite comes out clean on
both, which is the only reason the tooling can be said to discriminate rather than
always cry wolf.

Fixture C is the third failure: sensitivity 0.900 on twenty cases, one run each. It
has the best point estimate of the three and an interval of [0.596, 0.982], which is
to say it has told you nothing.

### Policy, measurement, planner

```
Policy       maximum acceptable residual error   asserted by someone accountable
Measurement  what the evaluator appears capable of, with its uncertainty
Planner      the cheapest admissible plan given exactly those two
```

`--max-error` on `characterize-evaluator` is a policy input and the report labels it
as one. It is never inferred from the data being characterised. Scenario A's `0.35`
and `0.05` were chosen after seeing which values produced n=1 and n=7 — the file says
so, and a test asserts that it keeps saying so.

## Reading the code

| file | contents |
|---|---|
| `statistics.py` | the binomial decision procedure and the Wilson interval |
| `domain.py` | typed domain objects, grouped by mutability class |
| `registry.py` | the world; two registries that are never merged |
| `candidates.py` | enumeration. Crosses source × population × fraction × n × cadence × mode |
| `constraints.py` | every rejection rule, staged. All domain content lives here |
| `economics.py` | cost, wall clock, human burden. Never averages a conditional latency |
| `ranking.py` | least cost. Deliberately dumb |
| `planner.py` | enumerate → reject → rank |
| `rationale.py` | why the winner won and why the losers lost |
| `characterization.py` | the falsifier. Imported by nothing in the planner's decision path |
| `complementarity.py` | the paired-error 2x2 and the statistics read off it. Emits no verdict |
| `complementarity_report.py` | renders those numbers and refuses the conclusion |

`docs/architecture.md` was written before the implementation and its wrong predictions
are marked `[REVISED]` rather than corrected. `docs/red_team_review.md` is the
post-implementation attempt to falsify the whole thing; start with its first table.
`docs/measurement_review.md` and `docs/measurement_red_team.md` are the second pass,
before and after, asking whether the quantities the planner optimises are measurable
well enough to deserve optimisation. The short answer is in the second document's first
paragraph and it is not a favourable one.

`scripts/make_fixtures.py` generates `data/`. It lives outside `src/` because the
planner package is asserted to contain no randomness, and because the committed YAML —
not the generator — is the artefact under review.

```bash
python -m pytest        # 119 tests
```
