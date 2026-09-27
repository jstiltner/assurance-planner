# Red team: does the experimental pass justify continuing?

Ten questions, answered against the work rather than for it. Where a question could be
answered by running something, it was run; where it could not, the answer says so instead of
reasoning toward a preference. Numbers are from the fixtures in `data/` at the default cost
model, held out over 5 slice-stratified folds.

Two answers changed during this pass, and both changed in directions that mattered:
Q5 reversed an earlier claim outright, and Q4 turned out to undercut the project's original
motivation.

---

## Q1. Does the triage policy beat simple early stopping on held-out data, or only on fixtures designed to favour it?

**On error, yes. On cost, never. And the fixtures are ours.**

Total error against `early_stop_8`:

| fixture | early_stop | triage | gain |
|---|---|---|---|
| mixed | 15.00 | 9.60 | +5.40 |
| systematic | 8.00 | 0.50 | +7.50 |
| noisy | 4.00 | 4.00 | 0.00 |

It never costs less: $28.31 vs $25.19 on mixed, $21.19 vs $16.69 on systematic, identical on
noisy. So the candidate policy is not a cheaper way to reach the same assurance. It is a way
to buy more assurance, and Q4 is where that becomes a problem.

The one part of this that is *structurally* immune to fixture design: on the mixed fixture
1.80 of the 5.40 gain is in the **uncontested** column — cases where the judge never
disagreed with itself. No repetition policy of any budget can reach those, because the
evidence they produce is unanimous by construction. That is not a tuning artifact.

Everything else is fixture-dependent and the fixtures were written by us. The slice-to-regime
mapping is deliberately imperfect so the candidate cannot win by definition, but "how
imperfect" is a number someone chose. Q2 is the question that actually settles this, and it
is not settled.

## Q2. Is it learning reusable failure-slice behaviour, or memorising individual cases?

**It structurally cannot memorise. Whether it generalises is undetermined, and the current
fixtures cannot determine it.**

The "cannot memorise" half is real and enforced: `Calibration` holds three proportions and a
case count per slice and nothing else — no case ids, no per-case records — and
`HeterogeneityTriage.route` takes a `slice_id`, never a case. A test strips every generated
regime note from the fixtures and asserts no policy's output moves, so no policy is reading
the answer key. Held-out folds are recomputed for disjointness rather than assumed, and
scoring a contaminated fold raises instead of reporting.

The "does it generalise" half is weak. Calibrated vs held-out stable-wrong rate, over all
slice × fold pairs:

| fixture | Spearman (stable_wrong) | Spearman (stable_correct) | pairs |
|---|---|---|---|
| mixed | +0.455 | +0.544 | 20 |
| systematic | +0.555 | +0.852 | 10 |

Positive, but that is close to all that can be said, because the held-out cells contain 1 to
5 cases each. `escalation-handoff` has a held-out stable-wrong rate of 0.500, 0.500, 0.000,
1.000, 0.000 across the five folds on 1–2 cases per cell. A rate measured on two cases cannot
validate or refute a 0.30 threshold.

This is the single most important finding of the red-team pass, and it is about experimental
design rather than about the policy. See Q10.

## Q3. Does the statistical model justify its complexity?

**No.** It stays as a comparator and does not become a dependency.

What it gets right: the intraclass correlation separates the noisy judge (0.095 / 0.106) from
the systematically wrong one (0.831 / 0.355) while their pooled means differ by under 0.01.

Why that is not enough: the Pearson dispersion statistic already reports the same clustering
more cheaply, and the goodness-of-fit check — built expecting a single Beta-Binomial to
visibly misfit a mixture — lands between 0.83 and 1.22 on **every** fixture including the one
constructed to be a mixture. It was not replaced with a diagnostic that works; it is recorded
as a negative result and pinned by a test. A model whose only working output duplicates a
cheaper statistic, and whose diagnostic fails on the case it was designed for, has not earned
an architectural position.

One implementation note that is a finding in its own right: fitting the model pooled over
reference labels produces a meaningless result (mean 0.524, alpha 0.295), because pooling
cases the judge should flag with cases it should not makes the per-case flag proportion
bimodal by construction, and the Beta absorbs the *labels* instead of the judge's
variability. The fit must be per-label. This was a real error, caught by the numbers looking
wrong rather than by a test, and there is now a test.

## Q4. How much of the economic gain is just stopping early on obvious cases?

**All of it. This is the answer that most damages the project's original motivation.**

On the mixed fixture, walking down from the historical practice:

| policy | cost | error | note |
|---|---|---|---|
| fixed_n_8 | $35.00 | 15.00 | the practice under test |
| early_stop_8 | $25.19 | 15.00 | −28%, **provably identical verdicts** |
| confidence_stop_8 | $19.31 | 15.00 | −45%, identical errors on this fixture |
| heterogeneity_triage | $28.31 | 9.60 | costs *more* than early stopping |

`confidence_stop_8` is the cheapest policy in the table at error no worse than `fixed_n_8`'s.
Every policy that improves on its error costs more than it does.

So the split is clean and unflattering: **sequential stopping captures 100% of the available
cost saving; allocation captures 0% and buys assurance instead.** The pitch that motivated
this work — "we were running 8 repetitions and that was wasteful" — is entirely answered by a
fifteen-line stopping rule that is textbook sequential testing and is not ours.

This also reveals a defect in the project's own kill criterion 1, which was written over
`early_stop_8` specifically ("within 5% of the best policy's cost"). `early_stop_8` is $25.19
against `confidence_stop_8`'s $19.31, 30% off, so the criterion does not fire — while the
thing it was trying to catch has happened, because the policy that captures the saving is a
*different* simple sequential rule. The criterion should have been written over "the best
simple sequential policy". Recording the defect rather than silently reinterpreting it.

## Q5. Is escalation doing all the useful work?

**No — and this answer reverses what this project claimed a day ago.**

The earlier claim was that a two-observation probe with no heterogeneity knowledge captures
most of the benefit, on the reasoning that escalation is the strongest lever and the probe
escalates. The subtraction was never done. Measured against `early_stop_8`:

| fixture | probe_2 (disagreement trigger) | blind (hash trigger) | triage (slice trigger) |
|---|---|---|---|
| mixed | **+0.25** | +2.15 | +5.40 |
| systematic | **−0.15** | +2.25 | +7.50 |
| noisy | **−2.50** | +2.25 | 0.00 |

`probe_2` is *worse than not escalating at all* on two of three fixtures. The mechanism is the
useful part: escalating on disagreement selects the **noisy** cases, which are exactly the
ones a majority of eight already resolves, and it can **never** select a confidently-wrong
case, because those are unanimous by definition. It buys second opinions on cases that did not
need them and skips the ones that did.

So the value of an escalation policy is entirely in its selection rule, which is the most
direct support the candidate contribution has. Two caveats that keep it honest:

- A hash — which knows nothing — gets 40% and 30% of the available error reduction on the two
  structured fixtures. The bar for a selection rule is low.
- On the noisy fixture the hash **beats** the slice rule, and the candidate policy is
  dominated. Q6 explains why, and it is not to the candidate's credit.

## Q6. What would have to be known before this could be deployed?

Five things, in descending order of how much they invalidate the current results.

1. **The alternate source's real sensitivity and FPR, measured on the same cases.** The
   default 0.95 / 0.05 is a guess, and every fractional error count in every table above is
   downstream of it. On the noisy fixture, blind escalation beats the candidate policy purely
   because 0.95/0.05 beats the judge's 0.672/0.087 outright — which means the right action
   would be to replace the primary, not allocate between them. The candidate contribution
   only has room to exist in the band where the alternate is good enough to escalate *to* and
   not so good that it should be the default, and nobody has measured where that band is.
2. **Per-slice stable-wrong rates with intervals narrow enough to place a slice relative to a
   threshold.** Currently ±0.25 on ten cases. See Q10.
3. **Real prices, latencies, and the actual judge parallelism.** Changing only the prices
   changes which policy is cheapest within an error budget, and never changes the
   qualification counts. That separation is the design working — and it also means a wrong
   price produces a confidently wrong recommendation.
4. **A price for a missed failure.** Without one, the Pareto set cannot be reduced and the
   tool cannot recommend anything, which is why `benchmark-policies` prints the table and
   names no winner. That is correct behaviour and it is also a limit on usefulness.
5. **A refresh cadence.** See Q7.

## Q7. How often would characterization need refreshing?

**Unknown, and nothing in this repository can answer it.** Every fixture is a single
timestamp; there is no longitudinal data and no drift model.

What exists is a sound floor rather than an answer: the qualification key
`(source version, failure mode, population, behaviour distribution)` makes a lookup miss the
invalidation mechanism, so a change to any component forces re-characterization and cannot be
silently skipped. That covers version bumps and behaviour changes. It says nothing about drift
within a fixed quadruple — a provider silently changing a model behind a stable version
string is exactly the case it does not catch.

One observation that may make the question less urgent than it looks: re-characterizing at the
protocol's minimum is 400 judge calls, about $25 and 13 hours of evaluator occupancy at the
default prices. At that price a monthly refresh is affordable without any drift model at all,
and buying the data is cheaper than reasoning about when it goes stale.

## Q8. Does the planner still have a reason to exist if a simple sequential policy captures most of the savings?

It captures **all** of them (Q4), so the question is live rather than hypothetical.

**The replication-count feature specifically does not survive this.** The planner's output
includes a fixed `n` derived from a binomial model that the architecture note already records
as the wrong shape (§2.1: averaging miss probability over heterogeneous cases is not the miss
probability at the mean rate, off by 3× at n=7 on data with no detectable clustering). Early
stopping at budget `n` returns provably identical verdicts at strictly fewer calls. A fixed
`n` is dominated by a stopping rule with the same budget, always, on every input. **The
honest conclusion is that the planner should emit a budget and a stopping rule rather than a
fixed number**, and that this is a correction rather than a new feature — the technique is
textbook and the result is a theorem, not a measurement.

I have not made that change in this pass. It touches the planner, and the standing
instruction is that the planner stays frozen unless a change is required for clean
comparison; this one is not required for comparison, it is required for the planner to stop
being wrong. That is a judgement for the user, not for me, and it is the second item in Q10.

**What is left of the planner's reason to exist**, with the cost argument removed: it also
decides mechanism, population and scope, cadence, sync/async, escalation target and human
allocation, and it gates all of them on intent and assurance policy rather than on a weighted
score. Early stopping decides none of those. Whether that framing is worth anything is not
measured by anything in this repository, and §9.2 of the architecture note — "qualification
evidence is unobtainable, so the model is vacuous" — remains the top open problem after three
passes.

## Q9. What real result would falsify the candidate systems contribution?

The claim is: *treat deterministic tests, stochastic evaluators and humans as
failure-mode-specific evidence sources, then allocate verification effort according to
assurance policy, development intent, empirical qualification, and current economics.* Its
one empirically vulnerable component is that allocation can key on measured subtype behaviour.

It is falsified by either of these:

- **No transfer.** Held-out per-slice stable-wrong rates rank-correlating at or below zero
  with their calibrated rates, across at least six slice × fold pairs with at least 20 cases
  per held-out cell. There is then no reusable subtype signal, only noise, and routing on it
  is fitting.
- **Thresholds inside the noise.** The identity of the routed slices changing under a ±0.05
  threshold perturbation. This one **already fires on the synthetic data**:
  `verbatim-readback` calibrates at 0.375 / 0.312 / 0.312 / 0.250 / 0.250 against
  `escalate_above=0.30`, so two of five folds do not escalate it, and `explicit-restatement`
  sits at 0.79 against `trust_above=0.80`, so the trust branch fires in two of five folds.
  Both thresholds are inside the fold-to-fold noise. They were not tuned away — re-fitting
  them so the folds agree would be fitting to the evaluation set, which is the exact leakage
  the folds exist to prevent.

A third result would not falsify the claim but would make it moot: if the alternate source
turns out to be uniformly better than the primary, the correct action is to replace the
primary and there is no allocation problem.

## Q10. What is the single next action?

**Measure the alternate source's sensitivity and false-positive rate on cases that already
have reference labels.** Not the 50 × 8 repetition study.

Three reasons it goes first:

- It is the cheapest open question by a wide margin — one pass of a second evaluator over an
  already-labelled set, no new labelling, no repetition.
- Every escalation number in every document here is conditional on a guessed 0.95 / 0.05.
  Escalation is also the *only* mechanism separating the candidate policy from established
  baselines (Q5). So this one measurement gates the interpretation of everything else.
- It can kill the project cheaply and early. If the alternate is uniformly better, replace the
  primary and stop. If it is no better on the cases that matter, escalation collapses and the
  candidate policy collapses with it. Either outcome is worth more than a repetition study.

### And a correction to the protocol, because its sample size answers the wrong question

The protocol specifies 50 cases × 8 repetitions, with 8 chosen to match the historical
practice under test. That budget characterizes an evaluator adequately and **cannot test the
routing claim**, which is the claim the study exists to test.

Per-slice sample needed for a Wilson interval to place a rate on one side of the 0.30
threshold:

| cases per slice | interval at p=0.45 | resolves? |
|---|---|---|
| 10 | [0.168, 0.687] | no |
| 15 | [0.248, 0.699] | no |
| 25 | [0.267, 0.629] | no |
| **30** | [0.302, 0.639] | **yes, barely** |
| 50 | [0.312, 0.577] | yes |

50 cases across 4 slices is 12.5 per slice — 10 calibration, 2.5 held out per fold. The
threshold decision would be made on a rate with a ±0.25 interval, and the held-out cell used
to validate it would hold two or three cases. That is the situation already visible in Q2.

Meanwhile repetitions are nearly free to give up. Truncating the fixtures' observations and
re-scoring:

| max repetitions | mixed: triage vs blind | systematic: triage vs blind |
|---|---|---|
| 8 | 9.60 vs 12.85 | 0.50 vs 5.75 |
| 6 | 9.60 vs 12.85 | 0.50 vs 5.75 |
| 5 | 7.00 vs 14.15 | 0.50 vs 6.75 |
| 4 | 7.00 vs 14.15 | 0.50 vs 6.75 |
| 3 | 10.00 vs 16.15 | 0.50 vs 6.75 |

The routing advantage survives down to three repetitions on both fixtures, and on the
systematic fixture it is completely insensitive to repetition count. *(One caveat: at a cap of
5 the policy escalates 20 cases instead of 12, because fewer observations make more cases look
"stable" — so part of the apparent improvement there is the cheap-and-good alternate again,
not better routing.)*

So the budget is allocated backwards. **Roughly 120 cases across 3 slices at 4 repetitions —
480 judge calls — answers the question that 50 cases at 8 repetitions (400 calls) cannot**,
for 20% more money. If the repetition question must also be answered, answer it on a 20-case
subset at 8 repetitions rather than by paying for eight observations of all 120.

This does not change the kill criteria, which stand as written. It changes the study that
would be scored against them, and the protocol should be revised before any data is collected
rather than after.

---

## Summary

| | verdict |
|---|---|
| Sequential early stopping | **Keep.** Free, provably correct, captures 100% of the cost saving. Not ours. |
| Fixed replication count `n` | **Superseded.** Dominated by a stopping rule at the same budget, on every input. |
| Beta-Binomial comparator | **Keep as a comparator only.** Duplicates a cheaper statistic; its fit diagnostic fails. |
| Heterogeneity-aware triage | **Undetermined.** Beats every alternative selection rule where slices carry signal; loses to a hash where they do not; its thresholds sit inside the fold noise. |
| Qualification keying, intent gating, counts-as-primary | **Keep.** Cheap, and they are what stop the rest from laundering guesses into precision. |
| The candidate systems contribution | **Not yet earned, not yet falsified.** One measurement (the alternate's real rates) gates the interpretation of everything else. |

The data has not earned the planner a new feature. It has earned one measurement, and it has
identified one thing the planner currently gets wrong.
