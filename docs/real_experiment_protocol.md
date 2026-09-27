# Real-data experiment protocol

Written **before** any real data is collected, and committed so that the bar cannot move
after the results are in. Its purpose is to make the next decision about this project
falsifiable: either the data supports allocating verification effort by case behaviour,
or it does not and this work should stop.

The synthetic results that motivate the design are in
[`docs/policy_benchmark_findings.md`](policy_benchmark_findings.md). The short version: on
a deliberately adversarial synthetic population, repetition stops buying anything after
six observations; escalation rather than repetition is what reaches the cases the judge is
confidently wrong about; *which* cases get escalated is what determines whether escalation
helps at all; and a plain interval-stopping rule is nonetheless the cheapest policy at
equal assurance, so everything the candidate policy adds is bought rather than saved.

That last point, plus a blind escalation control that dominates the candidate policy on one
of the three fixtures, is why this is a protocol rather than a deployment plan.

**Sections 2, 7, 12.1, 12.2 and 12.3 were revised after
[`experiment_red_team.md`](experiment_red_team.md)**, which found that the original sample
size could not test the claim in §1 and that two kill criteria were written so as not to fire
on the thing they were meant to catch. The revisions are marked and the original text is kept,
because in both cases the reason the first version was wrong is more useful than the
correction. The red-team document also argues that the study below should **not** be the next
action — measuring the alternate source's real sensitivity and false-positive rate should be,
and it is much cheaper.

---

## 1. The decision the experiment informs

Not "can we predict the best `n`". The question is:

> Given repeated observations from a stochastic evaluator, what evaluation policy reaches
> an acceptable assurance target at the lowest cost and wall-clock burden?

and behind it, the one that decides whether the planner deserves more sophistication:

> Is there a reusable, slice-level signal that tells us where repetition buys information
> and where it does not — one strong enough to beat simple early stopping and simple
> escalation on data neither of them was tuned on?

## 2. Minimum credible study

**[REVISED after the red-team pass. The original sizing is kept below because the reason it
was wrong is the useful part.]**

### 2.1 Originally specified, and inadequate

| | Minimum | Preferred |
|---|---|---|
| Cases | 40 | 50 |
| Repeated judgments per case | 5 | 8 |
| Behavioural subtypes (slices) | 3 | 4 |
| Cases per subtype | 10 | 12 |
| Total judge calls | 200 | 400 |

Eight repetitions was preferred because eight is the historical operating practice this
exercise exists to challenge, and the case count was set at whatever made the pooled
sensitivity interval tolerable.

**That sizes the study to characterize an evaluator, and it cannot test the routing claim in
§1, which is the claim the study exists to test.** The routing rule places a slice on one side
of a 0.30 threshold, and a Wilson interval on the slice's stable-wrong rate needs roughly 30
cases *per slice* to do that at all:

| cases per slice | interval at p=0.45 | resolves against 0.30? |
|---|---|---|
| 10 | [0.168, 0.687] | no |
| 15 | [0.248, 0.699] | no |
| 25 | [0.267, 0.629] | no |
| 30 | [0.302, 0.639] | yes, barely |
| 50 | [0.312, 0.577] | yes |

50 cases over 4 slices is 12.5 per slice: 10 for calibration and 2–3 held out per fold. The
threshold decision would rest on a rate with a ±0.25 interval, and the held-out cell meant to
validate it would hold two cases. That is not a measurement.

### 2.2 Specified instead

| | Minimum | Preferred |
|---|---|---|
| Behavioural subtypes (slices) | 3 | 3 |
| Cases per subtype | 30 | 40 |
| Cases | **90** | **120** |
| Repeated judgments per case | 4 | 4 |
| Total judge calls | 360 | **480** |
| Plus: repetition sub-study | 20 cases × 8 | 20 cases × 8 |

Fewer slices, far more cases per slice, and fewer repetitions. The justification for dropping
repetitions is measured rather than assumed: truncating each fixture's observations and
re-scoring shows the routing advantage surviving down to three repetitions, and on the
systematic fixture it is completely insensitive to repetition count.

| max repetitions | mixed: triage vs blind control | systematic: triage vs blind |
|---|---|---|
| 8 | 9.60 vs 12.85 | 0.50 vs 5.75 |
| 6 | 9.60 vs 12.85 | 0.50 vs 5.75 |
| 5 | 7.00 vs 14.15 | 0.50 vs 6.75 |
| 4 | 7.00 vs 14.15 | 0.50 vs 6.75 |
| 3 | 10.00 vs 16.15 | 0.50 vs 6.75 |

Four is chosen rather than three to keep a margin, and because a case that is unanimous across
four observations is meaningfully stronger evidence of stability than one unanimous across
three. Note the caveat visible in that table: at a cap of 5 the policy escalates 20 cases
rather than 12, because fewer observations make more cases *look* stable. Part of the apparent
improvement at low repetition counts is the cheap-and-good alternate source again, not better
routing — which is another reason not to go below four.

**The repetition question is answered separately and cheaply.** Whether observations six
through eight are wasted is a question about the marginal value curve, and that curve needs
depth on a few cases rather than breadth over many. 20 cases at 8 repetitions answers it for
160 calls. Paying for eight observations of all 120 cases would cost 960 calls to learn the
same thing.

Total: 480 + 160 = 640 calls against the original 400, for a study that can answer both
questions instead of neither.

### 2.3 The warning thresholds in the code

`benchmark-policies` warns and exits non-zero below 40 cases or 5 repetitions. Those bounds
are unchanged and are now *below* the specified minimum in both dimensions for cases and
above it for repetitions — they are a floor on "this comparison is not theatre", not an
endorsement of the sizing. A 90-case study at 4 repetitions will trip the repetition warning.
That is correct: it should be visible in the output that the repetition depth was traded away
on purpose.

## 3. Inclusion criteria

One failure mode, one evaluator version, one behaviour distribution. Mixing any of these
produces a dataset that cannot be qualified against anything, because the qualification
key is the quadruple `(evaluator version, failure mode version, population, behaviour
distribution)`.

The case set must contain all of:

1. **Obvious passes** — the behaviour is plainly correct. Roughly 25%.
2. **Obvious failures** — the behaviour plainly exhibits the failure mode. Roughly 25%.
3. **Borderline semantic cases** — two careful humans could reasonably disagree. Roughly
   30%. This is where repetition should earn its money if it earns it anywhere.
4. **Known-difficult judge cases** — cases where the evaluator has previously been
   observed to be confidently wrong, or where the rubric has a known blind spot. Roughly
   20%.

Category 4 must be identified from *prior* experience with the evaluator, not from the
repeated observations collected for this study. Selecting it from the study data would be
choosing the test set to contain the thing we want to find.

**Slices must be defined before any observations are collected**, from properties of the
input (the linguistic construction, the conversational position, the channel) and never
from the evaluator's behaviour. A slice defined by "cases the judge gets wrong" is the
answer key wearing a feature's clothing.

Record the slice on every case. `slice_id` is the only handle a triage policy is
permitted to generalise over; the harness refuses to route on an unlabelled case.

## 4. Labelling procedure

1. Two annotators label each case independently against a written rubric for the failure
   mode. The rubric is the *product's* definition of the failure, not the evaluator's
   prompt. If they are the same document, this study cannot measure evaluator error.
2. Disagreements are adjudicated by a third person. Record the adjudication.
3. Record inter-annotator agreement before adjudication and publish it. If raw agreement
   is below about 0.80, the reference labels are not stable enough to measure an
   evaluator against, and the rubric needs work before the study is worth running.
4. **Freeze the labels.** Write them to a file and commit it.

> **Reference labels must be established before anyone inspects the repeated-judge
> outcomes used for evaluation.** This is the single most important line in this
> document. A label revised after seeing the judge disagree converts evaluator error into
> reference error, and every number downstream becomes uninterpretable. There is no
> statistical correction for it.

If a label genuinely must change after the fact — the rubric was wrong, not the
annotator — record the change, the reason, and the date in the dataset's `limitations`,
and re-run the whole comparison. Do not silently edit.

## 5. Repetition procedure

- Exactly 8 independent calls per case, in the same configuration.
- Independent means a fresh call: no shared conversation state, no cache, no
  batching that lets one call see another's output.
- Temperature and every other decoding parameter identical across all calls and all
  cases. A study where some cases were sampled at a different temperature is measuring
  two evaluators.
- Record the observation order. The harness consumes observations in recorded order, so a
  sequential policy's call count depends on it. If order carries any systematic structure
  — for instance calls made after a model deployment — that is a limitation, and it must
  be recorded.
- Do not re-run a case because its results looked surprising. Surprising results are the
  data.
- Record failures to obtain an observation (timeouts, refusals) as such, not as a `pass`.
  A case with fewer than 8 usable observations is reported as truncated rather than
  padded.

## 6. Data format

Exactly the schema `benchmark-policies` already reads, so no code changes are needed:

```yaml
experiment:
  evaluator_version: correction_uptake_judge@v4
  failure_mode_version: VFD-CORRECTION-UPTAKE@v1
  population_id: correction-uptake-suite
  sut_distribution_id: voice-agent-turntaking-r4
  measured_on: 2026-10-15
  limitations:
    - collected over two days; a model deployment landed between them
cases:
  - case_id: CASE-real-001
    slice_id: implicit-correction
    reference_label: fail        # pass | fail
    observations:
      - verdict: fail            # pass | fail
        score: 0.91              # optional
        latency_ms: 1840         # optional
        cost: 0.0611             # optional
```

`score`, `latency_ms` and `cost` are all optional, and `slice_id` is optional at the
schema level. Nothing proprietary is required. The format is deliberately suitable for a
public corpus: if this study is worth running it is worth publishing, and a format that
only works inside one company is a format that gets rewritten.

## 7. Calibration / held-out split

5-fold slice-stratified cross-validation, which is what the harness does by default.

- Cases are sorted by id within each slice and assigned to fold `position % 5`. Sorting
  rather than shuffling keeps the split reproducible by inspection: a reader can work out
  which fold a case is in without running anything.
- Each fold's calibration set is the other four folds. Every case is scored exactly once,
  by a policy calibrated without it.
- Stratification matters because the entire premise is that slices differ. An
  unstratified split on a small slice can put every difficult case on one side.

At the revised sizing (§2.2) a 40-case slice yields 32 calibration and 8 held-out cases per
fold. That is the *point* of the resizing: at the original sizing the held-out cell was 2–3
cases, which is why the synthetic fixtures show held-out slice rates swinging 0.000 to 1.000
between folds and why no amount of care in the split could have rescued the measurement.

**Leakage risks, named:**

| Risk | Control |
|---|---|
| Calibrating on the case being scored | `leakage_report` recomputes fold disjointness; `held_out_outcomes` raises rather than reporting |
| A policy keying on `case_id` | `Calibration` holds three proportions and a count per slice, and no per-case structure at all |
| Slices defined from judge behaviour | Procedural, §3. Nothing in the code can detect this; it is the one control that depends on discipline |
| Labels revised after seeing outcomes | Procedural, §4. Same caveat |
| Thresholds tuned on the full dataset | The escalate/trust thresholds are fixed constants in `policies.py`, chosen before the benchmark was run, and **they sit close to the fold-to-fold noise on the synthetic data** — see §11 |
| Reading the generating regime | The synthetic fixtures record it in a per-case note; a test strips every note and asserts no policy's behaviour changes |

Cross-validation is the right choice over a single split at either sizing; a single held-out
set would be uninformative. Report the per-fold variation, not only the pooled number — the
per-fold spread is what decides kill criteria 2 and 4, and on the synthetic data it is larger
than the effect being measured.

## 8. Cost and latency collection

Collect per call, not per study:

- **Judge**: measured USD per call and measured wall-clock ms per call. Record the
  distribution, not just the mean; p95 latency is what a developer feels.
- **Repetition parallelism**: how many repetitions of one case can actually be in flight.
  This is the number that decides whether eight repetitions costs 2 minutes or 16.
- **Alternate evaluator**, if one is in scope: price, latency, and — separately — its own
  characterization study. Without one, its sensitivity is a declared number and every
  escalation result is conditional on it.
- **Human review**: measured minutes per case from the labelling exercise in §4, and a
  loaded hourly rate. The labelling exercise is itself the best available measurement of
  what human adjudication costs.

Report total evaluator occupancy and per-case critical path separately. Do not sum
per-call latency and call it wall clock.

## 9. Stopping conditions for the study

Stop collecting when all of:

- every case has 8 usable observations, or is recorded as truncated with a reason;
- every slice has at least 10 cases;
- labels are frozen and committed.

Stop the study early and do not report a policy comparison if:

- inter-annotator agreement before adjudication is below 0.80 (§4);
- fewer than 3 slices survive with 10 or more cases;
- the evaluator version changed mid-collection.

## 10. Metrics

Primary, per policy, over the held-out union:

| policy | FN | FP | unresolved | judge calls | mean/p95 calls | escalations | human reviews | cost | eval-time | wall |
|---|---|---|---|---|---|---|---|---|---|---|

Plus, and these are not optional:

- **Denominators.** FN and FP are over reference positives and negatives *that were
  answered*. Unresolved cases are reported separately and never folded into an accuracy
  figure.
- **Intervals.** Wilson intervals on sensitivity and specificity over judge-decided cases
  only. Escalated cases have no sample behind them and get no interval.
- **Per-fold spread.** Five numbers, not one, for each policy's error count.
- **Marginal value of repetition.** Errors at 1..8 observations, incremental errors
  avoided, incremental calls.
- **Allocation diagnostic.** Calls and errors split by whether the judge ever disagreed
  with itself on that case. A policy whose advantage lives entirely in the uncontested
  column has not allocated anything.
- **Per-slice heterogeneity.** Cases, mean disagreement, majority-agrees count, and the
  count of cases that are unanimous *and wrong*.

Accuracy as a single figure is reported nowhere. There is no composite quality score.

## 11. Comparison policies

Exactly the set already implemented, at a budget of 8:

- **A** `fixed_n_1`, `fixed_n_3`, `fixed_n_5`, `fixed_n_8` — majority vote, exact ties
  unresolved. `n=8` is included because it is the practice under test.
- **B** `early_stop_8` — stop when either side reaches `8//2 + 1 = 5`. Returns exactly
  `fixed_n_8`'s verdict with fewer calls, always. **This, not fixed-N, is the baseline
  any claimed saving must be measured against.**
- **C** `confidence_stop_8` — stop when a 90% Wilson interval on the flag rate excludes
  0.5. The confidence level materially changes this policy and 90% was chosen because 95%
  makes it strictly worse than fixed-N; that is a finding about the rule and it is stated
  rather than tuned.
- **D** `probe_2_escalate_alternate` — two observations; escalate if they disagree. The
  most important baseline for honesty, because escalation is the strongest lever in the
  comparison.
- **E** `heterogeneity_triage` — the candidate. Route on the slice's calibrated
  composition: escalate where unanimity has historically been unreliable, accept one call
  where it has been reliable, otherwise early-stop.
- **Control** `blind_escalation_<rate>` — escalates as many cases as the most
  escalation-heavy policy above, chosen by a hash of the case id. Not a proposal. It is
  appended by `compare` automatically so that it cannot be omitted, and it is the
  comparison E is most likely to lose: see kill criteria 7 and 8.

**A disclosed weakness in E.** Its thresholds (escalate above 0.30 historically
stable-wrong, trust above 0.80 historically stable-correct) sit close to the fold-to-fold
variation in the synthetic benchmark: the adversarial slice measures between 0.25 and
0.375 stable-wrong depending on the fold, so 2 of 5 folds do not escalate it, and the
"trust" branch fires in 2 of 5 folds and not the other 3. That knife-edge behaviour is a
real property of the policy and is one of the things the real study should measure. Do
not adjust the thresholds to fit the real data; if they need adjusting, that is result
§12.4.

Run also with `--judge-parallelism` set to the measured value, and with the measured
alternate and human prices. If the preferred policy changes when only prices change, say
so; that is information, not an inconsistency.

## 12. Kill criteria

Stated before the data exists. If any of these holds, the corresponding conclusion
follows and the work stops or narrows. No renegotiation.

1. **Sequential stopping captures essentially all of the saving.** If the cheapest *simple
   sequential* policy — `early_stop_n` or `confidence_stop_n`, whichever is cheaper — reaches
   within 5% of the cheapest policy overall at no worse error and no more unresolved cases,
   then the cost argument for allocation is dead. Ship the stopping rule, delete the triage
   policy, and do not add planner sophistication.

   **[REVISED.]** This originally read "if `early_stop_8` reaches within 5% of the best
   policy's cost". Naming one policy was the defect: on the synthetic data
   `confidence_stop_8` ($19.31) is the cheapest policy at error no worse than `fixed_n_8`'s,
   and `early_stop_8` ($25.19) is 30% above it — so the criterion did not fire even though
   the thing it was written to catch had happened. Allocation captured 0% of the available
   cost saving and bought assurance instead. Criteria that name a specific policy can be
   evaded by a different policy in the same family, so this one now names the family.

2. **Triage does not beat the size-matched blind control on held-out data.** If the
   candidate policy's error count is not lower at equal or lower escalation count — with the
   difference larger than the per-fold spread — then heterogeneity awareness is contributing
   nothing beyond "escalate sometimes". Escalate a fixed fraction and drop the triage.

   **[REVISED.]** This originally named `probe_2_escalate_alternate` as the baseline to beat.
   That was too easy a bar: measured against plain early stopping, disagreement-triggered
   escalation gains 0.25 errors on one synthetic fixture and *loses* 0.15 and 2.50 on the
   other two, because disagreement selects the noisy cases repetition already resolves and
   can never select a confidently-wrong one. Beating it proves very little. The blind
   escalation control (criterion 7) is the baseline with teeth, so this criterion now names
   it. `probe_2` remains in the comparison table as the obvious cascade a reader will expect.

3. **Slice-level behaviour does not transfer.** If a slice's calibrated stable-wrong rate on
   four folds does not predict its held-out stable-wrong rate — a rank correlation at or
   below zero across at least six slice × fold pairs, or fold-to-fold swings that cross the
   routing threshold in more than one fold in five — then there is no reusable signal, only
   memorised cases. The candidate contribution is falsified.

   This criterion is **not measurable at the originally specified sample size**, which is why
   §2 was resized. It requires at least 20 cases in each held-out slice cell; the original
   sizing gave 2–3, and on the synthetic fixtures the held-out rate of a small slice swings
   from 0.000 to 1.000 between folds. The synthetic rank correlations are +0.455 and +0.555 —
   positive, weak, and measured on cells too small to mean anything. Do not score this
   criterion on a study that cannot support it; report that it was unmeasurable instead,
   which is a different and more useful result than reporting a correlation of +0.455.

4. **The routing thresholds are not robust.** If the identity of the routed slices changes
   with a ±0.05 perturbation of either threshold, the policy is fitting noise. Report it
   as such; do not re-fit.

5. **Repetition never flatlines.** If errors continue to fall materially from 6 to 8
   observations, then the stable-wrong regime is rare in real data and the premise that
   motivated this work does not hold for this evaluator. Report `n` and stop.

6. **Repetition is useless everywhere.** If errors are flat from 1 to 8 observations, the
   evaluator is near-deterministic, the whole repetition question is moot, and the
   decision is a deterministic-source or human-review decision instead.

7. **Escalation does all the work regardless of targeting.** If escalating an arbitrarily
   chosen set of cases of the same size as the triage policy escalates achieves the same
   error reduction, then targeting is worthless and the answer is "escalate a fixed
   fraction".

   This control is implemented as `UntargetedEscalation` and is **appended by `compare`
   itself**, so a comparison cannot be scored without it. It selects cases by a hash of
   the case id: arbitrary with respect to the case's behaviour, reproducible without a
   random number generator. On the synthetic fixtures it does not fire on the two
   populations that have slice structure, and it does fire on the well-behaved one — which
   produced the criterion below.

8. **The alternate source is good enough that escalation wins unconditionally.** If blind
   escalation of an arbitrary fraction beats every repetition-only policy, then the
   alternate is a better evaluator than the primary and the correct action is to replace
   the primary, not to allocate between them. The candidate contribution only occupies the
   band where the alternate is good enough to be worth escalating *to* and not so good that
   it should be the default. **The alternate's sensitivity and false-positive rate must be
   measured on a subset of the same cases before the comparison is scored.** Without that,
   every fractional error count in the results is a restatement of an assumption. On the
   synthetic data this criterion fires: on `judge_runs_noisy.yaml` the candidate policy is
   dominated by the blind control, purely because the declared alternate (0.95/0.05) beats
   the judge (0.672/0.087) outright.

9. **The cost model does not change the answer.** If no plausible price vector changes
   which policy is preferred, the economics layer is decoration and should be deleted
   rather than maintained.

10. **The reference labels are not stable.** If inter-annotator agreement is below 0.80,
    nothing above is measurable and the study does not report a policy comparison.

## 13. What the study cannot tell us

Recorded so that the write-up does not overreach:

- **One evaluator, one failure mode.** Nothing about a different judge, a different
  rubric, or a different failure mode follows. Qualification is not transferable across
  any component of the key, by construction.
- **Alternate-source accuracy.** Unless the alternate is separately characterized, every
  escalation result is conditional on a declared number.
- **Human adjudication.** The harness treats human review as returning the reference
  label, which is true by construction and false in practice. The study measures what
  human review costs, not what it gets wrong.
- **Drift.** A single study is a snapshot. How often characterization must be refreshed
  is a separate longitudinal question, and the honest default until it is answered is to
  re-characterize on every evaluator version change and every behaviour-distribution
  change — which the qualification key already forces.
- **Whether the planner helps.** The planner allocates effort given qualification,
  intent, policy and economics. This study measures whether the qualification inputs
  carry a usable signal. It does not measure whether the planner's allocation is good,
  and no result here should be read as validating it.
