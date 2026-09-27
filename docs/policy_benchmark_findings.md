# Synthetic policy benchmark: what the fixtures show

Every number here comes from `assurance-plan benchmark-policies` on a fixture in `data/`,
at the default cost model, with the default 5-fold slice-stratified held-out split. The
fixtures are synthetic. Nothing in this document is evidence about a real judge; it is
evidence about which comparisons are worth running against a real judge, and which are
already answered well enough that a real study would be spending money to confirm
arithmetic.

Read this alongside [`real_experiment_protocol.md`](real_experiment_protocol.md). That
document is what these results argue for.

## The headline, stated against our own interest

On the fixture built specifically to make the candidate policy look good, a
two-observation probe that knows nothing about heterogeneity at all captures most of the
error reduction the candidate policy captures, at two thirds of the cost. The candidate
policy's advantage over it on the mixed fixture is 1.2 false negatives and 3.95 false
positives out of 76 cases, and it pays $7.56 more for them. The advantage is real and it
survives the held-out split, but it is not the order of magnitude that would justify
adding planner machinery on synthetic evidence alone.

Separately, and more robustly: repetition cannot reach a case the judge is confidently
wrong about, and no amount of it ever will. That result is not close, and it is the one
that makes the escalation half of the design worth keeping.

## Fixture 1: the mixed population (`judge_runs_mixed.yaml`)

76 cases, 4 slices, pooled sensitivity 0.761, pooled FPR 0.279, run
`1f0d79915c952835`. The planner would choose n=12 from those two pooled numbers alone.

Held-out comparison:

| policy | FN | FP | unres | esc | calls | mean | p95 | cost | wall |
|---|---|---|---|---|---|---|---|---|---|
| fixed_n_1 | 10.00 | 10.00 | 0 | 0 | 76 | 1.00 | 1 | $4.75 | 2m |
| fixed_n_3 | 9.00 | 11.00 | 0 | 0 | 220 | 2.89 | 3 | $13.75 | 6m |
| fixed_n_5 | 7.00 | 9.00 | 0 | 0 | 356 | 4.68 | 5 | $22.25 | 10m |
| fixed_n_8 | 7.00 | 8.00 | 1 | 0 | 560 | 7.37 | 8 | $35.00 | 16m |
| early_stop_8 | 7.00 | 8.00 | 1 | 0 | 403 | 5.30 | 8 | $25.19 | 16m |
| confidence_stop_8 | 7.00 | 8.00 | 1 | 0 | 309 | 4.07 | 8 | $19.31 | 16m |
| probe_2_escalate_alternate | 6.50 | 8.25 | 0 | 15 | 152 | 2.00 | 2 | $20.75 | 8m |
| heterogeneity_triage | 5.30 | 4.30 | 1 | 12 | 309 | 4.07 | 8 | $28.31 | 16m |

Fractional error counts mean the policy escalated: an escalated case contributes
*expected* error from the declared alternate rates rather than an observed outcome. That
visible fraction is the marker for "this part was modelled, not measured."

Three things to take from the table.

**Early stopping is free.** `early_stop_8` returns exactly `fixed_n_8`'s verdict on every
case and spends 403 calls instead of 560 — a 28% reduction with provably zero effect on
the answer. `confidence_stop_8` goes further, to 309 calls, and on this fixture still
returns the same errors. **The honest baseline for any claim about cost savings is
therefore early stopping, not fixed-N.** Measuring against `fixed_n_8` would credit the
candidate policy with a saving that a fifteen-line stopping rule already collects.
`fixed_n_5`, `fixed_n_8` and `early_stop_8` are all dominated on the four-axis test.

**The pooled sensitivity describes nothing.** 0.761 is an average over a slice whose
majority verdict agrees with the reference on 23 of 24 cases and a slice where it agrees
on 10 of 20. Planning n=12 from the pooled pair is planning for a population that does
not exist.

**Latency is not cost.** `fixed_n_8` is 18.7 hours of evaluator occupancy and 16 minutes
of wall clock under unlimited case concurrency. Both figures are reported and neither is
used in the dominance test, because picking one silently picks a parallelism assumption.

### Where the advantage lives

The diagnostic that matters most, because it is the one that catches a policy for
noticing that easy cases are easy:

| policy | uncontested calls | uncontested errors | contested calls | contested errors | esc |
|---|---|---|---|---|---|
| early_stop_8 | 191 | 9.00 | 212 | 6.00 | 0 |
| probe_2_escalate_alternate | 86 | 9.00 | 66 | 5.75 | 15 |
| heterogeneity_triage | 151 | 7.20 | 158 | 2.40 | 8 |

43 uncontested cases (the judge never disagreed with itself), 33 contested.

The candidate policy reduces error in **both** columns. That rules out the cheapest
explanation of its advantage — averaging over easy cases — and it is the strongest result
in this document in the candidate's favour. But note the second row: `probe_2` gets 5.75
contested errors for 66 contested calls. Most of the gap between it and the candidate is
on uncontested cases (9.00 vs 7.20), which is to say: on cases where the judge was
unanimous and wrong, reached only because the slice was known to be untrustworthy.
**Escalation is doing the work. Heterogeneity knowledge is doing the targeting.** Those
are separable, and the protocol's kill criterion 7 exists to test whether the targeting
is worth anything over escalating the same number of cases at random.

## Fixture 2: the systematically wrong judge (`judge_runs_systematic.yaml`)

50 cases, 2 slices, pooled sensitivity 0.682, FPR 0.096, run `ede2501277c6d4a7`. The
`rubric-blind` slice is 10 cases whose majority verdict agrees with the reference **zero**
times, 5 of them unanimously wrong at 8 repetitions.

Marginal value of repetition, comparing like with like (odd n only, since even n
introduces ties):

| n | FN | FP |
|---|---|---|
| 1 | 7.0 | 3.0 |
| 3 | 7.0 | 2.0 |
| 5 | 7.0 | 2.0 |
| 7 | 7.0 | 2.0 |

**False negatives are pinned at 7.0 from the first observation to the eighth.** 350 calls
buy one false positive. Every repetition-only policy in the table lands on FN=7.00:
`fixed_n_1`, `fixed_n_3`, `fixed_n_5`, `fixed_n_8`, `early_stop_8` and
`confidence_stop_8`, at costs from $3.12 to $25.00. The candidate policy reaches FN=0.35
with 10 escalations at $21.19, where 0.35 is 7 escalated positives times the declared 0.05
alternate miss rate — a modelled number, not an observed one.

This is the cleanest result in the set, and it is a result about escalation, not about
triage. Any policy willing to route a case to a second source would find these cases;
what the slice structure provides is knowing *which* cases to route without spending the
reference label to find out. **Repetition of a stochastic evaluator measures the
evaluator's self-consistency. It does not measure correctness, and on this fixture the two
are anti-correlated on a subset.**

## Fixture 3: the well-behaved noisy judge (`judge_runs_noisy.yaml`)

50 cases, one slice, sensitivity 0.672, FPR 0.087, run `b95bb1f05d0c7f92`. This is the
control, and its job is to catch the candidate policy crying wolf.

Odd-n marginal value:

| n | FN | FP |
|---|---|---|
| 1 | 10.0 | 4.0 |
| 3 | 8.0 | 2.0 |
| 5 | 6.0 | 0.0 |
| 7 | 7.0 | 1.0 |

Repetition works here: 14 errors down to 6 by n=5. (The uptick at n=7 is 50 cases of
sampling noise, not a trend; the fixture is not large enough to distinguish them, which is
itself an argument for the sample sizes in the protocol.)

And the control holds. `heterogeneity_triage` fires **zero** escalations and produces
numbers identical to `early_stop_8` — FN 4.00, FP 0.00, 302 calls, $18.88. Given a judge
whose disagreement is informative rather than systematic, the candidate policy correctly
declines to do anything, and costs nothing extra for the privilege. `probe_2` by contrast
escalates 10 cases here and *increases* false positives from 0.00 to 2.10 by handing clean
cases to a less specific source. Unconditional escalation is not free; that is the one
place the candidate policy clearly beats the simpler baseline.

## The statistical comparator does not earn a dependency

Beta-Binomial by method of moments, fitted **per reference label** (pooling the labels
makes the per-case flag proportions bimodal by construction, so the Beta absorbs the
labels rather than the judge's variability — a real error made and corrected during this
pass, pinned by a test):

| fixture | label | n | mean | alpha | rho | unanimous obs vs pred |
|---|---|---|---|---|---|---|
| mixed | pos | 34 | 0.768 | 0.924 | 0.454 | 16 vs 17.7 |
| mixed | neg | 34 | 0.279 | 0.187 | 0.599 | 19 vs 20.3 |
| noisy | pos | 24 | 0.672 | 6.378 | 0.095 | 3 vs 2.5 |
| noisy | neg | 26 | 0.087 | 0.730 | 0.106 | 16 vs 15.4 |
| systematic | pos | 24 | 0.682 | 0.139 | 0.831 | 16 vs 19.5 |
| systematic | neg | 26 | 0.096 | 0.174 | 0.355 | 18 vs 18.5 |

Two findings, one of them negative.

**What works:** rho separates the noisy judge (0.095 / 0.106) from the systematically
wrong one (0.831 / 0.355) while their pooled means differ by less than 0.01. That is the
distinction the whole design rests on, and the model does detect it.

**What does not:** it is the same signal the Pearson dispersion statistic already reports
by a cheaper route, and the unanimity-ratio goodness-of-fit check — built expecting a
single Beta-Binomial to visibly misfit a mixture — lands between 0.83 and 1.22 on every
fixture in `data/`, *including the one constructed to be a mixture*. It was not replaced
with a diagnostic that works. It is recorded as a negative result in the code and pinned
by `test_the_unanimity_check_fails_to_detect_the_mixed_population`.

So: the answer to "does the statistical model justify its complexity" is **no, not on this
data**. It stays as a comparator and a second opinion. It does not become an architectural
dependency. `judge_runs_small_sample.yaml` produces no fit at all (one observation per
case), which is the correct behaviour and a reminder that the comparator needs the data
the protocol specifies before it says anything.

## The threshold instability, which is the most damaging finding here

`HeterogeneityTriage` routes on two thresholds. Per fold, on the mixed fixture:

- `verbatim-readback` stable_wrong: 0.375, 0.312, 0.312, 0.25, 0.25 against
  `escalate_above=0.30`. **Folds 4 and 5 do not escalate it.**
- `explicit-restatement` stable_correct: 0.79 against `trust_above=0.80`. **"Trust" fires
  in 2 of 5 folds.**

Both thresholds sit *inside* the fold-to-fold noise on a 76-case fixture. The held-out
advantage reported above is therefore partly an artifact of which side of a knife edge
each fold happened to land on.

These were not tuned away, and they must not be. Re-fitting the thresholds so the folds
agree would be fitting to the evaluation set — the exact leakage the fold machinery
exists to prevent. This is documented as a disclosed weakness in the protocol (§11) and as
kill criterion 4: if the real study shows the same fragility under a ±0.05 perturbation,
the routing rule is fitting noise and the candidate contribution does not survive.

## What these fixtures cannot tell us

- Whether real judge slices behave consistently enough for a threshold to mean anything.
  Synthetic slices predict regime imperfectly *by construction* — a fixture where
  `slice_id` identified the stable-wrong cases exactly would let the candidate policy win
  by definition — but "imperfectly" here is a parameter someone chose, not a measurement.
- Whether the alternate source has the declared 0.95 / 0.05 rates. Every fractional error
  count above is downstream of an assumption. If the real alternate is no better than the
  primary on the cases that matter, escalation collapses and most of this document with
  it.
- Whether the cost ratios are near reality. Changing only the prices changes which policy
  is cheapest inside a fixed error budget (pinned by a test), and it does not change the
  qualification counts at all. So the economics are load-bearing for the decision and not
  for the measurement — which is the separation we wanted, but it also means a wrong price
  produces a confidently wrong recommendation.
- Anything about how often characterization must be refreshed. Every fixture is a single
  timestamp.

## The one thing this document is for

Three of the four questions the candidate contribution needs answered are answered here,
and two of the answers are unfavourable: the statistical model does not earn its keep, and
a simple probe-and-escalate rule with no heterogeneity knowledge gets most of the way. The
fourth question — does slice-level behaviour transfer to cases the calibration never saw,
stably enough to route on — cannot be answered by fixtures at all, because the fixtures'
slice structure is something we wrote.

That is the question the real study exists to answer, and the reason the protocol demands
50 cases at 8 repetitions rather than a deployment plan.
