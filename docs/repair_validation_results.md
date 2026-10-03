# Held-out results for the frozen repair rules

Date: 2026-09-29. Commit 3 of 3. Protocol fixed in
`docs/repair_validation_preregistration.md`; rules fixed in
`scripts/arb_production_signals.py`. **No rule was modified after these numbers
were seen, and no rule was added.** Reproduce with
`python scripts/arb_repair_validation.py --arm {validation,validation_strict}`.

Zero inference. Every number comes from cached judgments and `annotations.csv`.

Polarity, as preregistered: **E1** = evaluator says SUCCESS but the reference says
fail (the error the rules target). **E2** = evaluator says FAIL but the reference
says success (the error the rules risk creating).

## Baseline

| arm | n scored | ref=fail | baseline E1 | baseline E2 | accuracy |
|---|---|---|---|---|---|
| primary (1260 allocated) | 1259 | 912 (72.4%) | 98 (7.8%) | 98 (7.8%) | 84.4% |
| strict (1180 allocated) | 1179 | 861 (73.0%) | 95 (8.1%) | 76 (6.4%) | 85.5% |

One allocated case in each arm had no parseable AER verdict and was dropped.

---

## R1 -- self-contradictory infeasibility claim: **FAILS as proposed**

| | primary | strict |
|---|---|---|
| fires | 27 (2.1%) | 20 (1.7%) |
| ref=fail among firings | **37.0%** | **45.0%** |
| corpus base rate ref=fail | 72.4% | 73.0% |
| lift | **0.51x** | **0.62x** |
| AER wrong on firings | 33.3% | 30.0% |
| AER wrong on non-firings | 15.2% | 14.2% |

R1 was specified as *evidence against success*. It points the other way. Sessions
where the agent calls `report_infeasible` while asserting completion are **enriched
for reference SUCCESS, not failure** -- 17 of 27 firings are true successes. The
agent that says "the task cannot be done -- it has been successfully completed" has,
more often than not, actually done it and simply reached for the wrong tool.

The lift is below 1.0 in both arms, so this is not a sampling artifact of the
`infeasible-*` family; removing the family entirely moves it from 0.51x to 0.62x,
still inverted.

### The counterfactual that matters

The audit specified R1 as escalation-plus-evidence and explicitly refused to make it
a veto, on the reasoning that "an agent may have completed the task and merely
misused the tool." Held-out data says that reasoning was right and the margin was
large. Breakdown of the 27 firings as (AER verdict, reference):

| | ref=success | ref=fail |
|---|---|---|
| AER says SUCCESS | 14 | 6 |
| AER says FAIL | 3 | 4 |

Had R1 been a success veto, it would have flipped the 20 AER-SUCCESS cases to FAIL:
**6 helped, 14 harmed, net -8.** The single most valuable number in this experiment
is one that a rule did not produce, because the rule was not given the power to
produce it.

**Disposition: R1 is REJECTED as evidence against success.** It survives, narrowly,
as an *escalation trigger only*: AER's error rate on its firings is 33.3% against
15.2% elsewhere, so the signal does identify cases the evaluator handles badly -- it
simply does not say in which direction. That is a real but much weaker claim than
the one the case review made for it, and it is worth 27 cases in 1259.

---

## R2 -- negative self-report on an imperative modification goal: **meets its criterion, UNDERPOWERED**

| | primary | strict |
|---|---|---|
| eligible | 13 (1.0%) | 13 (1.1%) |
| verdicts changed | 6 | 6 |
| reference class of changes | all 6 ref=fail | all 6 ref=fail |
| helped | 6 | 6 |
| harmed | **0** | **0** |
| E1 | 98 -> 92 | 95 -> 89 |
| E2 | 98 -> 98 (unchanged) | 76 -> 76 (unchanged) |

The preregistered criterion was: strictly reduces E1 **and** `harmed <= helped / 3`.
Both hold (6 > 0 reduction; 0 <= 2). Identical in both arms.

**Disposition: ACCEPTED, and simultaneously UNDERPOWERED-REGARDLESS**, exactly as
preregistered. Thirteen eligible cases out of 1259 cannot distinguish a good rule
from a lucky one, and this was declared before the numbers were computed precisely
so that a clean 6-0 could not be dressed up as validation. What the result licenses
is a larger test, not deployment. Note also that only 6 of 13 firings changed a
verdict -- on the other 7 AER had already said FAIL.

The honest summary: the rule did not harm anything, it corrected six real errors,
and the experiment was too small to have detected it doing otherwise.

---

## R3 -- unverifiable image premise: **PASSES both preregistered tests**

| | primary | strict |
|---|---|---|
| fires / escalated | 133 (10.6%) | 133 (11.3%) |
| escalation volume vs 15% threshold | **PASS** | **PASS** |
| AER error rate on escalated | **25.6%** | **25.6%** |
| AER error rate on remainder | 14.4% | 13.1% |
| preregistered comparison | **PASS** | **PASS** |
| E1 | 98 -> 76 | 95 -> 73 |
| E2 | 98 -> 86 | 76 -> 64 |
| cases still scored | 1259 -> 1126 | 1179 -> 1046 |

Both preregistered conditions are met: escalation is affordable, and the escalated
subset is one the evaluator was genuinely mishandling at nearly twice its error rate
elsewhere. R3 removes 22 E1 errors and 12 E2 errors from the evaluator's authority
in the primary arm -- it is the only rule here that reduces **both** error classes,
which follows from it asserting nothing.

Breakdown of the 133 firings as (AER verdict, reference): AER-SUCCESS/ref-success 34,
AER-SUCCESS/ref-fail 22, AER-FAIL/ref-fail 65, AER-FAIL/ref-success 12.

### The caveat this result needs

Any rule that escalates the cases a judge finds hard will pass a test of the form
"is the judge worse on the escalated subset". That test is necessary, not sufficient,
and the preregistration should have said so. What keeps R3 from being circular is
that its firing condition is **structural and answer-independent** -- the goal names
an image, the evaluator's input contains no image -- and was written before its
error rate was known. It is not selecting hard cases; it is selecting cases where a
material conjunct is unevaluable, and those turn out to be hard. If the rule had been
defined as "cases where AER looks uncertain", this result would mean nothing.

Note also that 34 of 133 escalated cases are ones AER got right by saying SUCCESS.
Escalation is not free: it converts 133 automated verdicts into 133 human decisions,
and 99 of those were already correct.

**Disposition: ACCEPTED.** ~~The strongest result in the set, and the only one whose
eligible population is large enough to mean much.~~

### Correction 2026-10-02 (external reproduction): the caveat above fires

The caveat one section up -- *"any rule that escalates the cases a judge finds hard will
pass a test of the form 'is the judge worse on the escalated subset'"* -- turns out to
describe this result and not just the risk of it. An external reproduction asked which
benchmarks R3 fires in. **All 133 firings are visualwebarena**, which also carries the
highest judge-error point estimate of the four — 2.6 points above webarena, which at
n = 290 against n = 373 does not separate them (~~"the slice where this judge is
weakest"~~: corrected 2026-10-03, that is a rank and not a demonstrated ordering):

| benchmark | R3 fires | cases | judge error, R3 ignored |
|---|---|---|---|
| visualwebarena | **133** | 290 | 22.4% |
| webarena | 0 | 373 | 19.8% |
| workarena | 0 | 468 | 11.1% |
| assistantbench | 0 | 128 | 3.9% |

So the preregistered comparison contrasted one slice against the other three, not escalated
cases against unescalated ones — and its largest component, webarena, is barely below
visualwebarena at all. Conditioned on slice:

| | escalated | not escalated | diff | Fisher p |
|---|---|---|---|---|
| pooled, as published | 25.6% (34/133) | 14.4% (162/1126) | +11.2 pp | 0.0015 |
| **within visualwebarena** | **25.6%** (34/133) | **19.7%** (31/157) | **+5.8 pp** | **0.26** |

+5.8 pp of the +11.2 pp survives; +5.4 pp is slice identity. Split by error direction --
on reference-fail cases the only available error is a missed failure, on
reference-success cases a false alarm -- the residual is one-sided:

| side | escalated | not escalated | diff | Fisher p |
|---|---|---|---|---|
| missed-failure (ref=fail) | **25.3%** (22/87) | **15.8%** (18/114) | **+9.5 pp** | 0.1099 |
| false-alarm (ref=success) | 26.1% (12/46) | 30.2% (13/43) | **-4.1 pp** | 0.8139 |

Neither stratum is significant, and the split was chosen after the pooled residual failed,
so it is exploratory. Reproduce all of it with `scripts/arb_r3_slice_check.py`, which reads
the committed `data/REAL_arb_repair_validation_cases.csv` rather than the Hugging Face
snapshot; the stratification also prints inside the preregistered test's own output in
`scripts/arb_repair_validation.py`.

**Two populations, same reading.** The external reproduction reported this split as 25.9% vs
14.8% (p = 0.065) and 25.0% vs 32.4%, computed on the 266 visualwebarena validation cases that
also appear in the paired functional×aer file; the table above is the full 290-case
visualwebarena validation arm. Both are correct on their own population and the full arm is
canonical here. They agree on what matters: the residual sits on the missed-failure side, the
false-alarm side reverses, and neither is resolved at this n.

**The disposition does not move: R3 stays ACCEPTED.** It met its preregistered criterion
and the test ran as specified. Downgrading it on an analysis the preregistration never
named would be the post-hoc move this document exists to prevent -- a `CONFOUNDED` label
was briefly introduced on 2026-10-02 and reverted the same day. What is withdrawn is the
sentence struck above. R3 is **unproven, not refuted**: the within-slice residual runs in
the predicted direction and n=133 vs 157 is underpowered, so the evidence fails to show
the rule works rather than showing it fails. Never quote the pooled pair without the
within-slice pair beside it. Settling it requires a corpus where the evidence gap occurs
outside a single benchmark.

**The quarantine could not have caught this.** The split held back 42 cases so no rule was
tested on the cases that suggested it -- a control on case-level outcome leakage. This
confound is a property of the corpus, and that property was already tabulated: **1,064 of
the 1,260 validation cases (84.4%)** are inside the 1,106-trajectory population whose AER
correctness the pairing study had already scored case by case, as are all 42 quarantined
cases. A held-out split controls for having seen the outcome of these cases, not for
having seen the structure of this corpus. A confound in a covariate -- benchmark, domain,
agent -- survives any split that does not stratify on it. Section 7 of
`scripts/arb_r3_slice_check.py` prints the overlap.

---

## R4 -- terminal search-results route: **carries almost no information**

| | primary | strict |
|---|---|---|
| fires | 118 (9.4%) | 118 (10.0%) |
| ref=fail among firings | 87.3% | 87.3% |
| base rate | 72.4% | 73.0% |
| lift | 1.20x | 1.20x |
| AER wrong on firings | **16.1%** | 16.1% |
| AER wrong on non-firings | **15.5%** | 14.3% |

The mild enrichment for reference-fail (1.20x) is real but nearly uninformative
about the evaluator: AER's error rate on R4's firings is 16.1% against 15.5%
elsewhere -- a 0.6-point difference. Ending on a search page is weakly associated
with the task having failed, and essentially unassociated with the evaluator getting
it wrong. R4 tells you about the agent, not about the evaluation.

**Disposition: ~~REJECTED as a useful assurance signal.~~** It stays frozen in its
failing form. For the record, and not as a recommendation: as a veto it would have
helped 14 and harmed 10, net +4 over 118 firings -- which is a worse trade than R2
achieves on a tenth of the volume, and is not worth the application-specific route
table it requires.

**Correction 2026-10-02 (external reproduction) -- the REJECTED label above is post
hoc.** R4 had no accept/reject threshold. Section 7 of the preregistration reads:
*"**R1 and R4 (evidence, not vetoes).** No accept/reject on accuracy, since they
change no verdict. Reported as firing precision against base rate. A rule whose
firings are no more enriched for reference-fail than the corpus base rate carries no
information and will be recorded as such."* That is a direction, not a bar, and R4
**met it**: 1.20x, above base rate. The 16.1%-vs-15.5% evaluator-error contrast on
which REJECTED was decided is a metric the preregistration never named, and
application-specificity was declared in advance (section 9, *"R4 is explicitly
application-specific"*) rather than discovered. Section 8 committed that *"thresholds
in section 7 will not be revised after the fact"*; adding one where section 7 declined
to set one is the same violation. Overturning a rule on a criterion chosen after
seeing the data is the move this project reverted on R3 the same day, pointing the
other way.

What survives, stated as the preregistration allows: R4's firings are enriched 1.20x
for reference-fail, and that enrichment does not transfer to evaluator error (0.6 pt,
p = 0.89). R4 is therefore **weak evidence about the agent's outcome and no evidence
about the evaluator** -- which is a finding about what R4 measures, not a failed gate.
The preregistered disposition is **MET (directional)**; the earlier REJECTED wording is
superseded and kept above for the record.

---

## Composite R2 + R3

| | primary | strict |
|---|---|---|
| eligible | 145 (11.5%) | 145 (12.3%) |
| verdicts changed | 139 | 139 |
| helped / harmed | 6 / 0 | 6 / 0 |
| E1 | 98 -> 70 | 95 -> 68 |
| E2 | 98 -> 86 | 76 -> 64 |
| cases still scored | 1259 -> 1126 | 1179 -> 1046 |
| accuracy | 84.4% -> 86.1% | 85.5% -> 86.9% |

As preregistered, the composite is sub-additive: R3's `UNVERIFIABLE` absorbs cases
before R2 can veto them. The 1.7-point accuracy gain is reported for completeness and
was declared in advance not to be a decision input -- most of it is R3 declining to
answer, which is not an improvement in judgment.

---

## Summary

| rule | gate type (corrected 2026-10-02) | held-out verdict |
|---|---|---|
| R1 contradictory infeasibility | **directional only** (§7, no threshold) | **FAILS ITS DIRECTION** -- 0.51x, inverted: firings less enriched than base rate, the §7 no-information case. Escalation half (33.3% vs 15.2%) survives but is post hoc |
| R2 negative self-report on modification | numeric gate: veto SUCCESS | **ACCEPTED but underpowered** (6 helped, 0 harmed, n=13) |
| R3 unverifiable image premise | numeric gate: volume <15% + error contrast | **ACCEPTED** (both preregistered tests pass, both arms). Pooled reading narrowed 2026-10-02: all 133 firings are visualwebarena; within-slice 25.6% vs 19.7%, p = 0.26 |
| R4 terminal search route | **directional only** (§7, no threshold) | **MEETS ITS DIRECTION** -- 1.20x, above base rate. ~~REJECTED~~ was post hoc; no evaluator-level signal (0.6 pt, p = 0.89), which §7 never made a criterion |

Of the four, **two carried numeric accept/reject gates** (R2, R3): one accepted, one
accepted-but-underpowered. The other two carried a direction and no threshold: R1
failed its direction, R4 met it. ~~"Two of four rejected"~~ is superseded -- it counted
R4 against a bar that was never set, and the earlier line that *"the rejected pair are
the two that came from the cleanest-looking discovery cases"* was a pattern read off
that miscount.

## What these results do not establish

- Any prevalence claim. Firing rates are rates on an enriched research corpus.
- That R2 works. It did not harm anything on thirteen cases.
- That these rules generalise beyond AgentRewardBench's four benchmarks and twelve
  applications.
- That `UNVERIFIABLE` is the right production disposition. This measured only that
  it fires on cases the evaluator was mishandling. Whether 133 human reviews are
  worth 22 corrected E1 errors is a cost question this experiment does not touch.
