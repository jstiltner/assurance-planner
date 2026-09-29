# Preregistration: held-out validation of the frozen repair rules

Date: 2026-09-29. Written **before** any held-out outcome was computed.
Commit 2 of 3.

Rules under test: the four frozen in `scripts/arb_production_signals.py`, audited in
`docs/production_signal_audit.md`. Split frozen in
`scripts/arb_discovery_validation_split.py`.

The burden this document sets up is the one named in the brief:

> Can a production-valid rule derived from these failures improve unseen cases
> without introducing worse errors?

---

## 1. Discovery set

The 15 cases in `data/shared_unresolved_case_review.csv`. These were read in depth
-- goals, full action histories, captions, every cached judge's response -- and the
rules were written from them. They are burned. No result computed on them counts as
evidence that a rule works, and none is reported as such below.

## 2. Near-duplicate leakage analysis

Case-level exclusion is insufficient. A rule derived from case `T/A` has effectively
seen task `T`: the goal text is identical across agents, the application is
identical, and for `webarena.426` the review found the trajectory and the AER error
were near-identical under two different agents. Scoring on `T/B` would be scoring on
a paraphrase of the training example.

The 15 discovery cases span **13 distinct (benchmark, task_id) pairs** --
`visualwebarena.resized.598` and `webarena.426` each appear twice under different
agents. Those 13 tasks carry **27 further cases** under other agents. All are
quarantined.

| | n |
|---|---|
| annotated corpus (first-annotator dedup) | 1302 |
| discovery cases | 15 |
| distinct discovery tasks | 13 |
| same-task siblings removed | 27 |
| **total quarantined** | **42** |
| **validation set (primary arm)** | **1260** |

### Sensitivity arm

R1's mechanism was discovered on a `workarena.servicenow.infeasible-*` task. That
family shares construction across its members, so even after removing the discovery
task there is a family-level resemblance that case-level quarantine does not
address. A stricter arm removes the whole family:

| | n |
|---|---|
| `infeasible-*` cases remaining in the primary validation arm | 80 |
| **validation set (strict arm)** | **1180** |

Both arms are reported. If R1's result holds in the primary arm but collapses in the
strict arm, that is evidence the rule learned the family rather than the mechanism,
and it will be reported that way.

A credible held-out split **can** be formed here: 1260 cases across four benchmarks,
four agents and twelve applications, none of them read during discovery. No external
dataset is required for this round.

## 3. Rule eligibility on held-out data (label-blind, computed before freezing outcomes)

| rule | primary arm (n=1260) | strict arm (n=1180) |
|---|---|---|
| R1 contradictory infeasibility | 27 (2.1%) | 20 (1.7%) |
| R2 negative self-report on modification | 13 (1.0%) | 13 (1.1%) |
| R3 unverifiable image premise | 133 (10.6%) | 133 (11.3%) |
| R4 terminal search route | 118 (9.4%) | 118 (10.0%) |

**Declared in advance: R2 is underpowered.** Thirteen eligible cases cannot
distinguish a good rule from a lucky one. Whatever R2 does on those 13 will be
reported as a descriptive observation and explicitly **not** as validation. It is
recorded here so that a favourable R2 result cannot later be presented as if the
experiment had been adequate to detect an unfavourable one.

## 4. Required fields and zero-cost evaluability

| rule | required fields | already present? | needs an oracle field to FIRE? | zero-cost evaluable? |
|---|---|---|---|---|
| R1 | action names + args from the AER prompt | yes, 1302/1302 | no | **yes** |
| R2 | goal first line; terminal action + arg | yes, 1302/1302 | no | **yes** |
| R3 | goal text; evaluator `use_screenshot` | yes, 1302/1302 | no | **yes** |
| R4 | final URL + host; declared route table | yes, 1302/1302 | no | **yes** |

All four are evaluable over the full held-out corpus with **no new inference**.
Nothing in this experiment requires a model call.

Scoring material -- used only to grade a frozen rule after it has fired, never to
compute whether it fires: the expert `trajectory_success` (first annotator) as the
reference label, and the cached AER verdict via `arb_extract.parse_verdict`.

## 5. Baseline

The unmodified historical AER verdict on each validation case. Rules are applied as
post-hoc modifiers to that verdict. No judge is re-run.

## 6. Preregistered metrics

Polarity, stated explicitly to avoid the confusion that produced an earlier
correction in this repo. "Positive" = the evaluator says SUCCESS.

- **E1 = judge says SUCCESS, reference says fail.** The error the rules target.
- **E2 = judge says FAIL, reference says success.** The error the rules risk
  creating.

For each rule, and for the composite of all verdict-changing rules, on each arm:

1. coverage -- n eligible, and eligible/n as a fraction
2. n verdicts changed
3. cases **helped** -- verdict changed from disagreeing with the reference to
   agreeing
4. cases **harmed** -- verdict changed from agreeing to disagreeing
5. E1 count and rate, before and after
6. E2 count and rate, before and after
7. which reference class the changes fell in (ref=fail vs ref=success), reported
   separately -- **not** pooled
8. escalation / abstention volume: n routed to `UNVERIFIABLE` or human review, and
   the fraction of the corpus that represents
9. for non-verdict-changing rules (R1, R4): firing precision as evidence, i.e. the
   fraction of firings where the reference says fail, against the arm's base rate

Overall accuracy will be reported but is **not** a decision input. A rule that
raises accuracy by converting a 90%-prevalent class is not thereby good.

## 7. Preregistered decision rules

Declared now so that the threshold cannot be chosen after seeing the number.

**R2 (the only veto).** ACCEPTED if, on the primary arm, it strictly reduces E1
**and** `harmed <= helped / 3`. REJECTED otherwise. Reported as
**UNDERPOWERED-REGARDLESS** given n=13 -- acceptance here licenses a larger test, not
deployment.

**R3 (abstention trigger).** R3 changes no verdict to FAIL; it removes cases from the
evaluator's authority. Judged on two things: (a) the escalation volume must be
affordable -- declared threshold, under 15% of the corpus; (b) the cases it escalates
must be ones the evaluator was actually getting wrong. Declared test: AER's error
rate **on the escalated subset** must exceed AER's error rate on the non-escalated
remainder. If AER is no worse on the escalated cases, R3 is buying nothing and is
REJECTED as a net loss of coverage.

**R1 and R4 (evidence, not vetoes).** No accept/reject on accuracy, since they change
no verdict. Reported as firing precision against base rate. A rule whose firings are
no more enriched for reference-fail than the corpus base rate carries no information
and will be recorded as such.

**Composite.** R2 and R3 applied together, since they are the only two that alter
output. Same metrics. Declared in advance: the composite is not expected to be
additive, because R3's `UNVERIFIABLE` removes cases from the population R2 could
veto.

## 8. Commitments

- No rule will be modified after seeing held-out outcomes. If a rule fails, the
  failure is recorded in Commit 3 and the rule stays frozen in its failing form.
- No new rule will be added in Commit 3.
- Thresholds in section 7 will not be revised after the fact.
- Results are reported for both arms regardless of which is more favourable.
- No paid inference. If a question arises that requires it, the experiment stops and
  the question is named rather than answered.

## 9. What this experiment cannot settle

- Whether these rules generalise beyond AgentRewardBench. The corpus is four
  benchmarks and twelve applications; R4 is explicitly application-specific.
- Whether the imperative-modification detector is accurate. Its precision was sampled
  label-blind at 20/20; its recall is unmeasured, and R2's eligible population is
  small enough that classifier error and rule error cannot be separated.
- Whether `UNVERIFIABLE` is the right production disposition. This measures only
  whether it fires on cases the evaluator was mishandling.
- Anything about prevalence. The rates here are firing rates on an enriched research
  corpus.
