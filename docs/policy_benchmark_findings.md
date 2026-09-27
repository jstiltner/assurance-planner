# Synthetic policy benchmark: what the fixtures show

Every number here comes from `assurance-plan benchmark-policies` on a fixture in `data/`,
at the default cost model, with the default 5-fold slice-stratified held-out split. The
fixtures are synthetic. Nothing in this document is evidence about a real judge; it is
evidence about which comparisons are worth running against a real judge, and which are
already answered well enough that a real study would be spending money to confirm
arithmetic.

Read this alongside [`real_experiment_protocol.md`](real_experiment_protocol.md). That
document is what these results argue for.

## The headline

**Corrected.** An earlier draft of this document claimed that a two-observation
probe-and-escalate rule "captures most of the error reduction the candidate policy
captures." That was wrong, and wrong in the candidate policy's disfavour. Measured against
early stopping, `probe_2_escalate_alternate` gains 0.25 errors on the mixed fixture and
*loses* 0.15 and 2.50 on the other two. The original claim was reasoning from "escalation
is the strongest lever, and this policy escalates" without doing the subtraction. The
correction is kept visible because the mechanism behind it is the most useful thing in
this document.

Total error against `early_stop_8`, held out, default prices:

| fixture | early_stop_8 | probe_2 | blind control | heterogeneity_triage |
|---|---|---|---|---|
| mixed | 15.00 | 14.75 *(+0.25)* | 12.85 *(+2.15)* | 9.60 *(+5.40)* |
| systematic | 8.00 | 8.15 *(−0.15)* | 5.75 *(+2.25)* | 0.50 *(+7.50)* |
| noisy | 4.00 | 6.50 *(−2.50)* | 1.75 *(+2.25)* | 4.00 *(0.00)* |

Three findings, in decreasing order of how much they survive scrutiny.

**1. Repetition cannot reach a case the judge is confidently wrong about, and no amount of
it ever will.** On the systematic fixture false negatives sit at 7.0 from the first
observation to the eighth. This is not close and it is what makes the escalation half of
the design worth keeping.

**2. Escalating is not the same as escalating the right cases, and disagreement is the
wrong trigger.** `probe_2` escalates when two observations disagree, so it selects the
*noisy* cases — exactly the ones a majority of eight already resolves — and it can never
select a confidently-wrong case, because those are unanimous by definition. It buys second
opinions on cases that did not need them and skips the ones that did. An escalation
policy's value is entirely in its selection rule, which is a better argument for the
candidate contribution than any number in this document.

**3. But the selection rule only has to beat a coin, and it barely does on one fixture.**
Against the size-matched blind control, targeting wins on mixed (+5.40 vs +2.15) and
systematic (+7.50 vs +2.25), and *loses outright* on noisy (0.00 vs +2.25), where the
candidate policy is dominated. See the noisy section for why that last one is the most
damaging result here.

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
| blind_escalation_0.20 *(control)* | 6.30 | 6.55 | 1 | 17 | 325 | 4.28 | 8 | $33.06 | 16m |

`blind_escalation_0.20` is the kill-criterion-7 control, not a proposal: it escalates as
many cases as the most escalation-heavy real policy, selected by a hash of the case id, so
it cannot have consulted any evidence. It is appended by `compare` itself rather than
requested by a caller, because a control that has to be asked for is a control that gets
dropped the first time it embarrasses the policy it controls.

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
in this document in the candidate's favour.

Note the second row. `probe_2` leaves the uncontested column completely untouched at 9.00,
identical to every repetition-only policy, because a case the judge never disagreed with
itself about is a case `probe_2` never escalates. All of its activity is in the contested
column, and the contested column is the one repetition was already handling. The candidate
policy's gain is 1.80 errors in the uncontested column — cases that looked unanimous and
certain, reached only because the slice was known to be untrustworthy. **That is the whole
mechanism, and it is a selection mechanism, not an escalation mechanism.**

The blind control separates those two. On the mixed fixture it escalates 17 cases to
triage's 12, and lands on 12.85 total error against triage's 9.60, for $4.75 more. So
targeting is worth something here: fewer escalations, fewer errors, less money, all three
at once. On the systematic fixture the gap is much larger — 0.50 total error from 10
escalations against 5.75 from 15.

That is the candidate contribution's only real win in this document, and it is worth being
precise about what it is not. It is not evidence that *our* thresholds are right; §"the
threshold instability" below shows they are not stable. It is evidence that *some*
slice-level signal exists in these fixtures and that a policy keyed on it does better than
one that isn't. The fixtures' slice structure is something we wrote, so this result cannot
travel further than that.

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

And the cry-wolf control holds. `heterogeneity_triage` fires **zero** escalations and
produces numbers identical to `early_stop_8` — FN 4.00, FP 0.00, 302 calls, $18.88. Given
a judge whose disagreement is informative rather than systematic, the candidate policy
correctly declines to do anything, and costs nothing extra for the privilege. `probe_2` by
contrast escalates 10 cases here and *increases* false positives from 0.00 to 2.10 by
handing clean cases to a less specific source.

### And then the blind control wins, which is the most damaging result in this document

| policy | FN | FP | unres | esc | calls | cost |
|---|---|---|---|---|---|---|
| heterogeneity_triage | 4.00 | 0.00 | 5 | 0 | 302 | $18.88 |
| blind_escalation_0.20 *(control)* | 1.35 | 0.40 | 3 | 15 | 224 | $25.25 |

Escalating an arbitrary fifth of the population — chosen by a hash of the case id, with no
knowledge of anything — cuts total error from 4.00 to 1.75. `heterogeneity_triage` is
**dominated** on this fixture, and the test that pins this asserts exactly that.

The reason is not subtle once stated: the declared alternate is 0.95 sensitivity / 0.05 FPR
and the judge is 0.672 / 0.087. The alternate is simply a better evaluator. On a population
with no structure to exploit, the optimal policy is *stop using the primary*, and no
planner is required to reach that conclusion. Any escalation at all buys accuracy directly,
in proportion to how much you spend.

Two consequences, and both are load-bearing for the real study.

1. **Every escalation result in this document is partly a statement about the alternate's
   assumed quality rather than about allocation.** The 0.95/0.05 figures are a guess in a
   default `CostModel`. If the real alternate is barely better than the primary, the
   escalation half of the design collapses; if it is dramatically better, the correct
   answer is to replace the primary and the allocation question disappears. **The
   candidate contribution only has room to exist in the band between those two.** That
   band is narrow and nobody has measured where it is.
2. **A benchmark must include a population where escalation is not the answer**, or it
   cannot distinguish "allocated well" from "spent more." The noisy fixture was supposed
   to be that population and is not, because the price of the alternate makes escalation
   worth it even at random. This is a fixture defect surfaced by the control, and it is
   recorded rather than patched: tuning the alternate's declared rates downward until
   triage wins would be constructing the result.

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

Four questions, and the synthetic answers are two against, one for, one unanswerable.

**Against.** The Beta-Binomial comparator does not earn a dependency; the dispersion
statistic already reports its one useful signal more cheaply. And on the mixed fixture a
plain interval-stopping rule (`confidence_stop_8`, $19.31) is the *cheapest policy at equal
assurance* — every policy that beats it on error costs more. So sequential stopping alone
captures 100% of the available cost saving, and everything the candidate policy adds is
bought, not saved.

**Also against, and worse.** Blind escalation beats the candidate policy outright on the
well-behaved fixture, because the alternate source's assumed quality means escalating
*anything* buys accuracy. Until the alternate's real rates are measured, none of the
escalation numbers here separate allocation from spending.

**For.** Where slices carry signal, targeting beats size-matched blind escalation on all
three axes at once — fewer escalations, fewer errors, less money — and it beats
disagreement-triggered escalation by a wide margin, because disagreement selects the cases
repetition already handles. The advantage lives in both the contested and uncontested
columns, so it is not easy-case averaging.

**Unanswerable by fixtures.** Whether real failure slices behave consistently enough for a
threshold to mean anything. The synthetic slices' predictive power is a parameter someone
chose, and the two thresholds currently sit inside the fold-to-fold noise.

That last one is the question the real study exists to answer, and it is why the protocol
specifies 50 cases at 8 repetitions and a set of kill criteria rather than a deployment
plan. On this evidence the planner has not earned another feature. It has earned one
experiment.
