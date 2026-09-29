# Preregistration: `required-conjunct-never-attempted`

Date: 2026-09-29. Written **before** any reference-conditioned quantity on the validation
corpus has been computed. Scoping, mechanism analysis and corpus selection are in
`docs/required_conjunct_scoping.md`.

This document is the frozen specification. It is committed before the rule is
implemented and before any `reward` field in the validation corpus is read.

The question under test:

> When a user request contains a required state-changing conjunct, can we detect from
> production-visible execution evidence that the agent never even attempted the required
> action, and therefore prevent an unsupported SUCCESS verdict?

---

## 1. Name

`required-conjunct-never-attempted`, abbreviated **RC1**. It is not a widening of R2. R2
remains frozen exactly as it is in `scripts/arb_production_signals.py` and is not rerun,
redefined, or extended by this work.

## 2. Exact production-visible inputs

RC1 may read **only** these three things.

**I1 -- the user's utterances.** The ordered content of `role == "user"` messages in the
trajectory. Nothing else. In particular the benchmark's hidden task brief
(`tau_bench/envs/*/tasks_*.py`, field `instruction`) is **not** an input, and neither is
its ground-truth `actions` list.

**I2 -- the deployment tool catalogue.** The tool names available to the agent, and a
static read-only / state-changing classification of each, written from the tool
docstrings before any trajectory is inspected. For the validation corpus:

```
AIRLINE write tools:
  book_reservation, cancel_reservation, send_certificate,
  update_reservation_flights, update_reservation_baggages,
  update_reservation_passengers
AIRLINE handoff tool:  transfer_to_human_agents
RETAIL write tools:
  cancel_pending_order, exchange_delivered_order_items,
  modify_pending_order_address, modify_pending_order_items,
  modify_pending_order_payment, modify_user_address,
  return_delivered_order_items
RETAIL handoff tool:   transfer_to_human_agents
All other tools in both domains are read-only, including `think` and `calculate`.
```

**I3 -- the execution record.** The ordered list of tool calls the agent made, with
function names and arguments, and the tool responses.

### 2.1 Forbidden inputs

RC1 is invalid if it reads any of: the environment `reward`; the `info` block; the
benchmark task id or split; the ground-truth action list; the expected final database
state; the hidden task instruction; any expected entity id. The implementation must drop
`reward` and `info` at ingest so that rule code cannot reach them, in the same way
`arb_production_signals.ORACLE_FIELDS` enforces the boundary for the ARB rules.

## 3. Trigger

RC1 fires on a trajectory when **both** hold:

**T1 -- an obligation is extracted.** At least one `(ACTION_CLASS, OBJECT_PHRASE)` pair is
extracted from I1 by the frozen verb table, where `ACTION_CLASS` ranges over the closed
vocabulary induced by I2's write tools and `OBJECT_PHRASE` is the user's verbatim noun
phrase. `OBJECT_PHRASE` is recorded for audit and is **never resolved to an entity**; it
plays no part in whether RC1 fires.

**T2 -- no call of that ACTION_CLASS appears in I3.** Set membership over tool names
across the entire execution record. No argument matching. No entity resolution. No
comparison against what the arguments should have been.

If T1 and T2 both hold and no exception in section 4 applies, the trajectory's state is
`NEVER_ATTEMPTED` and RC1 fires. Otherwise its state is one of
`ATTEMPTED_BUT_SUCCESS_UNKNOWN`, `SUCCESS_EVIDENCE_PRESENT`, or `UNRESOLVED`, and RC1 does
nothing. The four states are recorded separately for every trajectory and are **never
collapsed**.

## 4. Exceptions -- conditions that force `UNRESOLVED` instead of firing

1. The trajectory is truncated, malformed, or exceeds the agent's step budget with no
   terminal assistant turn.
2. No user-role turn is present, or the user turns contain no parseable request.
3. The extractor produces an obligation whose `ACTION_CLASS` is not in the domain's write
   vocabulary.
4. The user retracts or replaces the request in a later turn (detected by a second
   obligation of the same class with a different `OBJECT_PHRASE`, or by an explicit
   cancellation phrase in the frozen retraction list).
5. The agent's final action is the domain's handoff tool (`transfer_to_human_agents`).
   Escalating to a human is the policy-correct terminal behaviour in this deployment and
   is not an unattempted obligation.

`UNRESOLVED` does nothing. It is never counted as a firing, never escalated, and never
folded into `NEVER_ATTEMPTED`. Its count is reported.

## 5. Action semantics

**RC1 emits `UNVERIFIABLE` and routes the trajectory to human review. RC1 has no veto.**

It does not change a verdict to FAIL. It asserts that a material conjunct of the user's
request lacks admissible evidence in the execution record, and removes the trajectory
from automated authority.

**The counterfactual veto is computed and reported, and never applied.** For every
firing, the analysis records what a veto would have done (helped / harmed / net), as a
diagnostic only. This is imported deliberately from the R1 result, where the decisive
number -- 6 helped, 14 harmed, net -8 -- existed only because the rule had been denied
the power to produce it. No future decision to grant RC1 a veto may be made on anything
other than accumulated counterfactual evidence.

## 6. Expected failure modes, declared in advance

Declared now so that a failure cannot later be presented as a surprise, and so that the
section 10 audit has a fixed taxonomy to classify into.

| # | mode | direction |
|---|---|---|
| F1 | the requested change already held, so no write was owed | false fire |
| F2 | the agent correctly verified and did nothing | false fire |
| F3 | the request was conditional and the condition was false | false fire |
| F4 | the obligation became impossible mid-conversation | false fire |
| F5 | the action was deferred or asynchronous | false fire |
| F6 | an effect-equivalent tool outside the mapped ACTION_CLASS was used | false fire |
| F7 | policy forbade the write and the agent correctly declined | false fire |
| F8 | the verb table missed the user's phrasing | silent miss (safe direction) |
| F9 | the verb table extracted an obligation the user did not impose | false fire (the dangerous extractor error) |

F1, F2, F3, F4 and F5 have **no production-visible guard**. They are the reason RC1 has
no veto. They are expected to appear among the firings and their prevalence is the
principal thing this experiment measures.

## 7. Validation population

`sierra-research/tau-bench`, `historical_trajectories/`, MIT licence, commit as of
2026-03-18.

| file | records | tasks | trials |
|---|---|---|---|
| gpt-4o-airline.json | 200 | 50 | 4 |
| gpt-4o-retail.json | 460 | 115 | 4 |
| sonnet-35-new-airline.json | 400 | 50 | 8 |
| sonnet-35-new-retail.json | 920 | 115 | 8 |
| **total** | **1980** | **165 distinct** | -- |

**Reference outcome:** the environment `reward` field, a programmatic database-state and
required-output check. It is not an LLM judgment. It enters only after RC1 has already
decided whether it fires.

**Arms**, reported unconditionally regardless of which is more favourable:

- **primary** -- all 1980
- **by domain** -- airline (600) vs retail (1380), testing whether the verb table
  generalises across catalogues
- **by agent** -- gpt-4o (660) vs sonnet-3.5-new (1320), testing whether the rule learned
  one agent's habits

## 8. Duplicate and task-family leakage policy

The corpus has 8-12 trajectories per task. Trajectories of the same task share the user
request and therefore share the obligation and any extractor error.

1. Every count is reported **twice**: at trajectory level and at distinct-task level.
2. Any threshold in section 11 is evaluated against the **task-level** count. The
   trajectory-level count is descriptive.
3. No discovery/validation split of tau-bench is made, because no reference label is read
   before the rule is frozen. The freeze in this document is the whole of the leakage
   control, and it is stronger than a split would be.
4. Label-blind development is permitted and is not leakage: the verb table may be written
   and its precision audited against user-turn text, provided no `reward` value is read.
   This follows the standard already established in `docs/production_signal_audit.md` --
   using the reference label to score a frozen rule is valid; using it to compute or
   choose the rule is leakage.

## 9. What counts as help and what counts as harm

RC1 escalates rather than vetoes, so "help" and "harm" are defined against review cost
and against the reference label, not against a judge's verdict. There is no cached judge
in this corpus; section 8.5 of the scoping document records that asymmetry.

**Help.** A firing on a trajectory whose reference says failure. Automated authority is
withdrawn from a case that was in fact wrong.

**Harm.** A firing on a trajectory whose reference says success. A human is spent on a
case that was already right, and -- more seriously -- RC1's premise was wrong: a write
was not in fact owed, or was satisfied some other way.

**Harm rate** = firings with reference success / all firings, reported at trajectory and
task level.

**Counterfactual-veto helped / harmed / net**, reported and not acted on: helped = firings
where an emitted FAIL would have matched a reference failure that some upstream evaluator
called success; since no upstream evaluator exists here, this reduces to the reference
class of the firings, and is reported as such rather than dressed up as an accuracy gain.

## 10. Metrics

For each arm, at trajectory level and distinct-task level:

1. state distribution over all 1980: `NEVER_ATTEMPTED` / `ATTEMPTED_BUT_SUCCESS_UNKNOWN` /
   `SUCCESS_EVIDENCE_PRESENT` / `UNRESOLVED`
2. obligation extraction rate, and the `UNRESOLVED` count broken down by section 4 clause
3. firing volume, absolute and as a fraction
4. reference-fail rate among firings, against the arm's base rate, and the **lift**
5. harm rate as defined in section 9
6. counterfactual-veto helped / harmed / net
7. a manual audit of **every** firing whose reference says success, classified into the
   F1-F9 taxonomy of section 6
8. a label-blind precision audit of the extractor on a sample of 30 extracted obligations,
   performed before metric 4 is computed

Accuracy is not reported and is not a decision input. There is no evaluator whose accuracy
would be at stake.

## 11. Decision rules

Declared now so that no threshold can be chosen after seeing a number.

**RC1 is ACCEPTED as an escalation signal if all three hold on the primary arm:**

- **A1 -- affordability.** Firing volume is under **15%** of trajectories. This threshold
  is imported unchanged from R3's preregistration rather than invented, and it is imported
  because the escalation cost structure is the same.
- **A2 -- enrichment.** The lift of reference-fail among firings over the arm's base rate
  is at least **1.50x** at trajectory level **and** at least **1.25x** at task level. The
  1.50x anchor is not free-standing: R4 was rejected at 1.20x, R2 turned out to carry
  1.06x, and R3 was accepted at 1.78x. The bar is set strictly between this project's
  own rejected and accepted precedents.
- **A3 -- extractor validity.** The label-blind precision audit in metric 8 finds at least
  27 of 30 extracted obligations correct. Below that, RC1's firings cannot be attributed
  to the rule rather than to the extractor, and the result is void rather than negative.

**RC1 is REJECTED** if A1 or A2 fails. A failing RC1 stays frozen in its failing form and
the failure is recorded, exactly as R1 and R4 were.

**RC1 is reported UNDERPOWERED-REGARDLESS** if it fires on fewer than **30 distinct
tasks**, whatever the trajectory count. At 30 clean firings the one-sided 95% upper bound
on an unobserved harm rate is 9.5%; below 30 the bound is loose enough that a favourable
result cannot distinguish a good rule from a lucky one. This is declared now, in advance,
for the same reason R2's underpowering was declared in advance: so that a clean result
cannot later be presented as though the experiment had been adequate to detect an unclean
one.

**No accept/reject on the counterfactual veto.** It is reported. It is the beginning of
an evidence base for a future decision that this experiment does not make.

## 12. Stopping conditions

Limited to infrastructure, as required.

- The trajectory files are unavailable or their schema has changed such that tool-call
  names cannot be extracted.
- Fewer than 95% of records yield a parseable trajectory. Below that, stop and report the
  parse rate rather than analysing a biased remainder.
- The run requires a paid model call. It does not; if a question arises that would, the
  experiment stops and the question is named rather than answered.

No stopping condition is conditioned on a result.

## 13. Commitments

- RC1 will not be modified after any reference-conditioned number is seen. If it fails,
  the failure is recorded and RC1 stays frozen in its failing form.
- No second rule will be added in the same pass.
- The thresholds in section 11 will not be revised after the fact.
- All arms in section 7 are reported regardless of which is more favourable.
- R2 is not widened, not rerun, and not redefined.
- No paid inference.

## 14. What this experiment cannot settle

- Whether RC1 generalises beyond tool-calling customer-service agents. Two domains, one
  benchmark, two 2024-era agent models.
- Whether RC1 works on browser agents. It is not implementable on AgentRewardBench at
  all: 65.8% of click bids resolve against the archive's final accessibility tree, 221 of
  1200 cases resolve none, and 92% of click arguments are bare numeric bids with no
  element identity. RC1 is deployability class B -- producible with instrumentation,
  absent from that archive.
- Whether RC1 should ever hold a veto. That requires counterfactual evidence accumulated
  across more than one corpus.
- Whether RC1 and R3 are the same rule. The `EVIDENCE_GAP` unification in section 7 of
  the scoping document is a hypothesis and is deliberately not built.
- Any prevalence claim. Firing rates are rates on a benchmark.
