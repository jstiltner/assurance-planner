# Scoping: `required-conjunct-never-attempted`

Date: 2026-09-29. Written after `af10543`, in which held-out outcomes for four frozen
rules were observed.

The governing constraint on everything below:

> Observed held-out results may teach the next rule, but they cannot validate the rule
> they taught us to write.

Everything in sections 1-9 is therefore **exploratory**. Nothing here is evidence that
`required-conjunct-never-attempted` works. The frozen, testable form of the rule is in
`docs/required_conjunct_preregistration.md`, committed before any reference-conditioned
number on the new corpus is computed.

---

## 1. Burn ledger

The question is which cases remain usable as held-out evidence for a rule designed after
`af10543`.

| stratum | n | what was consumed |
|---|---|---|
| ARB corpus, first-annotator dedup | 1302 | -- |
| discovery cases (read in depth: goals, full action histories, captions, every cached judge, reference label) | 15 | everything |
| same-task siblings quarantined at task level | 27 | nothing directly, but they are paraphrases of the 15 |
| validation, primary arm | 1260 (1259 scored) | see below |
| validation, strict arm | 1180 (1179 scored) | subset of the above |
| **genuinely untouched ARB cases** | **0** | -- |

1302 = 1260 validation + 42 quarantined. There is no remainder.

### 1.1 What "consumed" means for the 1259, case by case

The brief asks that a mechanically-present-but-never-inspected subset be established
carefully rather than assumed. Doing that honestly:

| sub-stratum | n | outcome exposure |
|---|---|---|
| R2-eligible, individually read with reference labels during Phase 2 below | 13 | **full, per case** |
| R1 firings | 27 | published as a 2x2 of (AER verdict x reference) |
| R3 firings | 133 | published as a 2x2 of (AER verdict x reference) |
| R4 firings | 118 | published as firing precision and AER error rate |
| fired at least one rule (union, with overlap) | 274 | at least cell-level |
| **fired no rule at all** | **985** | contributes only to published corpus aggregates |

The 985 are the least contaminated stratum in the corpus. They are still not held out,
for two reasons that are worth stating rather than waving at:

1. **Aggregate exposure is still exposure.** The base rate (72.4% ref=fail), AER's
   overall accuracy (84.4%), and AER's error rate on the non-firing remainder (14.4%)
   are all published. A new rule tuned to beat those numbers is tuned on them.
2. **The stratum is defined by the outcomes.** "Cases the four frozen rules do not fire
   on" is a set I can only name because I know how those four rules performed. Scoring a
   fifth rule on the complement of four rules whose results I have seen is selection on
   a post-outcome criterion, even if no individual label in the complement was read.

**Default, adopted:** the AgentRewardBench corpus is exploratory for any rule designed
after `af10543`. It may generate hypotheses and it may be used to test whether a rule is
*implementable*. It may not be used to estimate that rule's performance.

### 1.2 What is still legitimate on ARB

Label-blind work. Checking whether a feature can be extracted, how often it is present,
and what its firing rate is are all computations that never touch `trajectory_success`.
Section 3.3 below is exactly that, and it is the reason this rule does not get validated
on ARB at all.

---

## 2. Is R2 the wrong abstraction?

### 2.1 R2 exactly as frozen

From `scripts/arb_production_signals.py`, unmodified since `db0975d`:

```python
def rule_r2_negative_selfreport_on_modification(f):
    if not IMPERATIVE_MODIFICATION.match(f["goal_first_line"]):
        return False, ""
    if f["terminal_action"] not in ABSTENTION_ACTIONS:
        return False, ""
    if COMPLETION_ASSERTION.search(f["terminal_arg"]):
        return False, ""
    if NEGATIVE_SELF_REPORT.search(f["terminal_arg"]):
        return True, f"modification goal + negative terminal report: {f['terminal_arg'][:120]}"
    return False, ""
```

with `ABSTENTION_ACTIONS = ("send_msg_to_user", "report_infeasible")`. Disposition: veto
of a SUCCESS verdict. Held-out result: 13 eligible, 6 verdicts changed, 6 helped, 0
harmed; preregistered criterion met; declared UNDERPOWERED-REGARDLESS in advance.

### 2.2 All 13 eligible cases

| case | goal (first line) | terminal message, abridged | ref | AER | changed? |
|---|---|---|---|---|---|
| visualwebarena.resized.314 | Upvote all posts with food picture | "No posts with food images found to upvote." | fail | SUCCESS | helped |
| webarena.730 | DisLike all submissions by Hrekires | "No more submissions by Hrekires found" | fail | SUCCESS | helped |
| webarena.776 (agent A) | Delete all reviews from the scammer Carlo | "No customer named Carlo found" | fail | SUCCESS | helped |
| webarena.776 (agent B) | Delete all reviews from the scammer Carlo | "No customer named Carlo found" | fail | SUCCESS | helped |
| webarena.666 | Submit merge request, assign Carol as reviewer | "cannot find a user named 'Carol'" | fail | SUCCESS | helped |
| webarena.471 | Cancel order 307 | "Order 307 not found in the system." | fail | SUCCESS | helped |
| webarena.642 (agent A) | (post) | "Cannot post more at this time" | **success** | FAIL | no change |
| webarena.642 (agent B) | (post) | "there's a rate limit on the forum" | **success** | FAIL | no change |
| webarena.629 | (post) | environment block / HTTP 520 | **success** | FAIL | no change |
| 4 others | -- | -- | fail | FAIL | no change |

### 2.3 The number that was not preregistered

```
R2 firing precision (EXPLORATORY -- not a preregistered metric)
  ref=fail among all 13 firings        10/13 = 76.9%
  corpus base rate ref=fail                    72.4%
  lift                                          1.06x
  ref=SUCCESS among firings                 3 (23.1%)
  P(all 6 verdict-changing firings ref=fail | base rate 0.724) = 0.144
  rule-of-three upper bound on harm rate, n=6, zero harms = 39.3%
```

Three things follow, in order of how much they are entitled to claim.

**First, the preregistered disposition stands.** R2 met the criterion declared in
`docs/repair_validation_preregistration.md` section 7 before the numbers were computed.
Firing precision was not among the metrics declared for R2 (it was declared only for the
evidence-only rules R1 and R4). Overturning an accept with a metric chosen after seeing
the data is precisely the move the preregistration exists to prevent, and it is not made
here. R2 remains ACCEPTED-BUT-UNDERPOWERED.

**Second, the acceptance is thinner than it reads.** A 1.06x lift means R2's firings are
barely enriched for reference-fail relative to a coin weighted by the corpus base rate.
The zero-harm record is an artefact of baseline agreement, not of rule safety: all three
reference-SUCCESS firings were cases where AER had *already* said FAIL, so R2's veto
changed nothing and cost nothing. Had AER said SUCCESS on any of them, R2 would have
harmed. At n=6 verdict-changing firings, the true harm rate is bounded above only at
39.3%, which comfortably contains the 23% reference-SUCCESS rate observed among the
eligible 13.

**Third, this lowers the prior that R2's mechanism generalises.** That is a statement
about what to do next, not a re-scoring of what was done.

### 2.4 Which mechanism actually drove the six corrections

The brief's five candidates:

| candidate | verdict |
|---|---|
| (A) terminal negative self-report alone | insufficient -- the three rate-limit cases are negative self-reports and reference-SUCCESS |
| (B) modification task type alone | insufficient -- all 13 are modification tasks and 3 are reference-SUCCESS |
| (C) no state-changing attempt | not what R2 measures; R2 never inspects the action sequence |
| (D) contradiction between requested action and execution trace | closest, but R2 does not read the trace |
| (E) a conjunction | yes, but not the conjunction R2 encodes |

The empirical split is sharper than any of the five:

- **"the target entity does not exist"** -- no posts with food images, no more submissions
  by Hrekires, no customer named Carlo, no user named Carol, order 307 not found. 6 of 6
  verdict-changing firings. All reference=fail.
- **"the environment blocked me"** -- rate limit, HTTP 520. 3 of 3. All
  reference=SUCCESS.

The distinction is not modification-vs-not and not negative-vs-positive. It is *whose
failure the agent is reporting*: the agent claims the world lacks the target (usually
because the agent failed to find it) versus the agent claims the world refused the
request (which in these cases followed a partially-completed post that the annotator
counted as success). R2's lexicon does not separate these, and both match
`NEGATIVE_SELF_REPORT`.

Note the second-order point: in all six corrected cases the agent was *extremely* active
-- `webarena.471` performs 23 clicks, `visualwebarena.resized.314` performs 27 actions.
These agents did not fail to try. They tried hard and never reached the required action
class.

### 2.5 Subsumption verdict

**Partial overlap, different mechanism. `required-conjunct-never-attempted` does not
subsume R2, and R2 should not be widened.**

- On the six corrected cases, the new rule fires only if "attempt" is typed by action
  *class* (upvote / delete / cancel / assign). The agents were busy; they were not
  inactive. Typing the attempt requires knowing what each click targeted.
- On the three rate-limit reference-SUCCESS cases the agents visibly `fill` and `click`
  a submit control, so the new rule would *not* fire. That is a genuine structural
  argument in the new rule's favour -- and it is a hypothesis generated by outcomes I
  have now seen, so it is a reason to test, not a result.
- R2's residual honest content is narrower than its frozen form: *entity-not-found
  assertion on a modification goal*. n=6. Widening R2's lexicon or its eligibility to
  chase the new mechanism would destroy the only thing R2 has, which is a frozen
  definition that predates its outcomes.

**Disposition: R2 stays exactly as frozen. It is not widened, not rerun, and not
redefined.** Its status is "licenses a larger test", as preregistered.

---

## 3. Defining "required conjunct"

This is the part that can silently solve the user's task. The discipline is negative:
the definition is written as a list of things it may not consult, and only then as a
list of things it may.

### 3.1 Forbidden inputs (any of these makes the rule invalid)

- the reference verdict or any expert annotation
- the benchmark's expected final database state, expected URL, or expected entity id
- the benchmark's ground-truth action list (tau-bench `Task.actions`, ARB task metadata)
- the benchmark family or task id
- the correct entity, unless the user named it themselves
- anything computed from the judge's own verdict

### 3.2 Permitted inputs

1. **The user's utterances.** In a chat setting, the user-role turns. In a single-goal
   setting, the goal string. Not a hidden task brief, not a paraphrase supplied by the
   harness.
2. **The deployment's tool catalogue** -- the names, signatures and docstrings of the
   tools the agent was given, plus a static classification of each as read-only or
   state-changing.
3. **The execution record** -- the ordered list of tool calls the agent actually made,
   with names and arguments, and the tool responses.

Point 2 needs defending, because it looks application-specific and R4 was ~~rejected~~
criticised for being application-specific. (*Corrected 2026-10-02:* R4 had no numeric gate
to be rejected against, and its application-specificity was declared in §9 of its own
preregistration rather than found in the results — so it is a scoping limit, not a verdict.
The argument below is unaffected; only the word "rejected" was wrong. See
`research_synthesis.md` §3.3.3.) The distinction: R4's route table encoded *which URLs mean
the task failed*, which is knowledge about outcomes. A tool catalogue encodes *which of
my own tools write*, which is knowledge every production system has about itself before
any task is run. It is deployment configuration, not oracle metadata. A system that
cannot say which of its tools mutate state has a bigger problem than evaluation.

### 3.3 The definition

A **required conjunct** is an obligation pair

```
(ACTION_CLASS, OBJECT_PHRASE)
```

extracted from the user's utterances, where:

- `ACTION_CLASS` is a member of a closed vocabulary of state transitions defined over the
  deployment's write-tools (for tau-bench retail: CANCEL_ORDER, MODIFY_ORDER_ITEMS,
  MODIFY_ORDER_ADDRESS, MODIFY_ORDER_PAYMENT, MODIFY_USER_ADDRESS, RETURN_ITEMS,
  EXCHANGE_ITEMS; for airline: BOOK, CANCEL, MODIFY_FLIGHTS, MODIFY_BAGGAGE,
  MODIFY_PASSENGERS, SEND_CERTIFICATE).
- `OBJECT_PHRASE` is the user's own noun phrase, retained verbatim and **never resolved**
  to an entity id. The rule must not know which order is meant.

The obligation describes an action class and a state-transition duty. It does not
describe, and may not be permitted to describe, what the correct final state is. This is
the line: **the rule asserts that a class of action was owed, never that a particular
outcome was owed.**

### 3.4 Extraction: deterministic, heuristic, or LLM?

| setting | extraction | verdict |
|---|---|---|
| tool-calling agent with a fixed catalogue (tau-bench) | lexical imperative match on user turns, mapped to ACTION_CLASS by a hand-written verb table derived from tool docstrings | **deterministic, high precision** -- preferred |
| raw browser agent (ARB) | no catalogue exists; obligations would have to be inferred from free text against an open action space | requires an LLM |

The ARB row is a stopping condition, and it is respected. The imperative-modification
detector already in `arb_production_signals.py` was sampled label-blind at 20/20
precision, but it produces only "some modification was requested" -- it cannot produce an
ACTION_CLASS, because ARB has no catalogue to map into. Producing one would require paid
inference. **Stopping here and naming it, per the brief.**

The tau-bench row is deterministic because the closed vocabulary is small (13 write tools
across two domains) and because the tool docstrings supply the verb set directly. The
verb table is written from the catalogue, before any trajectory is read.

### 3.5 Known failure mode of the extractor

A verb table has recall holes. "I'd like to get rid of order #W123" does not contain
"cancel". Recall failures cause the rule to stay silent, which is the safe direction. A
precision failure -- firing an obligation the user did not impose -- is the dangerous
direction, and the preregistration declares a manual label-blind precision audit of the
extractor before any outcome is scored.

---

## 4. Defining "attempted"

Attempt is not success. The rule's whole value is the ability to say: *I cannot verify
that this succeeded, but I can verify that it was never tried.*

Four states. They are **never collapsed**, and only one of them is actionable.

| state | condition | actionable? |
|---|---|---|
| `NEVER_ATTEMPTED` | an obligation was extracted, and **no** tool call of that ACTION_CLASS appears anywhere in the execution record | **yes** |
| `ATTEMPTED_BUT_SUCCESS_UNKNOWN` | at least one call of the required ACTION_CLASS appears, and the record does not establish whether it took effect | no |
| `SUCCESS_EVIDENCE_PRESENT` | a call of the required ACTION_CLASS returned a success-shaped response | no |
| `UNRESOLVED` | the execution record is incomplete, truncated, or the obligation could not be extracted with confidence | no |

Load-bearing details:

- `NEVER_ATTEMPTED` is an assertion about the **absence** of a call of a named class. It
  is checkable by set membership over tool names. It requires no argument matching, no
  entity resolution, and no knowledge of what the arguments should have been.
- `UNRESOLVED` must never be silently folded into `NEVER_ATTEMPTED`. The failure mode
  being guarded against is a truncated or malformed trace producing a confident
  "the agent never tried". Every condition that makes extraction or trace-reading
  uncertain routes to `UNRESOLVED`, and `UNRESOLVED` does nothing.
- `SUCCESS_EVIDENCE_PRESENT` is deliberately weak and deliberately unused. It exists to
  keep the taxonomy honest -- a success-shaped tool response is evidence of effect, not
  of correctness -- and to prevent a later version of this rule from quietly acquiring a
  positive-assurance role.

---

## 5. Adversarial tests, before any code

Each row: does the rule fire, should it, what guard is needed, and is the guard
production-visible.

| # | scenario | fires? | should it? | guard | guard production-visible? |
|---|---|---|---|---|---|
| 1 | desired state already holds; agent reads, confirms, reports | **yes** | **no** | none available | **NO** |
| 2 | agent verifies and correctly does nothing | **yes** | **no** | none available | **NO** |
| 3 | one tool call satisfies several conjuncts | no (call present) | correct | obligations are per-class, not per-clause | yes |
| 4 | indirect action via a different tool that has the same effect | **yes** | **no** | catalogue must map effects, not tools; partly solvable | partly |
| 5 | attempt made and failed | no (call present) | correct -- attempt was made | none | yes |
| 6 | deferred / asynchronous action | **yes** | ambiguous | none available in-trace | **NO** |
| 7 | request mixes informational and modification clauses | fires on the modification clause | correct | per-clause extraction | yes |
| 8 | conditional request, "if X then change Y" | **yes**, when X was false | **no** | condition evaluation needs the world | **NO** |
| 9 | user asks for a plan, not execution | should not fire | -- | imperative table excludes plan/advise/explain verbs | yes |
| 10 | task becomes impossible after execution begins | **yes** | ambiguous | none | **NO** |
| 11 | agent abstains because authorisation is absent | **yes** | **no** | policy state is deployment config; partly solvable | partly |
| 12 | environment blocks the write (rate limit, 5xx) -- found empirically in R2's three reference-SUCCESS cases | no, if the agent called the write tool and it errored | correct | none needed | yes |
| 13 | agent calls `transfer_to_human_agents` -- correct escalation under policy | **yes** | **no** | treat handoff tools as a terminal exception | yes |

Five rows have **no production-visible guard**: 1, 2, 6, 8, 10. Those are not edge cases
invented for completeness. Rows 1, 2 and 8 are the same failure -- *the required change
was not owed after all, and only the world can say so* -- and it is exactly the failure
the `production_signal_audit.md` red-team already identified when it kept R2 off the
"absence of state-changing actions" formulation.

**Does guarding make the rule application-specific?** Partly, and the honest answer is:
rows 4, 11 and 13 require deployment configuration (effect-equivalence between tools,
authorisation state, which tools are handoffs). That is the same class of knowledge as
the tool catalogue and is defensible on the same grounds. Rows 1, 2, 6, 8 and 10 are not
application-specific -- they are *unguardable*, and they are the reason section 6 does
not grant this rule a veto.

---

## 6. Action authority

**Recommended: `UNVERIFIABLE` plus escalation. Not a veto.**

The argument, in the order that decides it:

1. **Five unguardable counterexamples produce silent false fires.** A rule that cannot
   distinguish "never tried" from "correctly declined to try" cannot be allowed to
   convert a SUCCESS into a FAIL on its own authority.
2. **R1 is the precedent.** R1 was a plausible deterministic signal that was correctly
   denied veto power before its outcomes were known. The held-out counterfactual was
   6 helped, 14 harmed, net -8. The single most valuable number in the previous
   experiment is one a rule did not produce, because the rule was not given the power to
   produce it.
3. **R2's zero-harm record must not be laundered into authority for a different rule.**
   R2 observed zero harms on six verdict-changing firings, which bounds its harm rate at
   39.3% and says nothing at all about a rule that fires on a different condition.
4. **Volume forbids it.** 438 of 1980 tau-bench trajectories (22.1%) contain no
   write-tool call at all, measured label-blind. Before obligation filtering, that is the
   ceiling on the firing population. A veto at anything near that rate would rewrite a
   fifth of all verdicts on a signal with no measured precision.

The `UNVERIFIABLE` disposition also matches what the rule actually establishes. It
asserts an evidence gap. It does not assert failure.

**The counterfactual veto is reported but never applied.** The preregistration requires
computing, for every firing, what a veto would have done (helped / harmed / net), and
reporting it as a counterfactual only. This is the one design lesson from R1 worth
importing wholesale: had the previous experiment logged that counterfactual for R1 by
design rather than by luck, the rejection would have been available immediately. A
rule's right to a veto should be earned by the counterfactual accumulating over time,
never by its author's confidence.

---

## 7. Relation to R3

R3 and the new rule may both be instances of:

> Do not permit a positive assurance claim when a material proposition lacks admissible
> evidence.

with a shared representation `EVIDENCE_GAP(material_conjunct, required_evidence_type)`:

| rule | material conjunct | required evidence type | where the evidence is missing |
|---|---|---|---|
| R3 | "the image shows X" | perceptual | the **evaluator's** input |
| new | "the state was changed" | execution / effect | the **agent's** behaviour |

The unification is attractive and is not built. The disanalogy is real and matters:

- R3's gap is an *instrumentation* gap. The evidence exists in the world; the evaluator
  was not given it. Escalating to a human resolves it, because the human can look at the
  image.
- The new rule's gap is a *behavioural* gap. The evidence does not exist anywhere,
  because the action was never performed. Escalating to a human resolves it only if the
  human can inspect the world's state, which is a different and more expensive
  capability.

A framework that collapses these would obscure the fact that the two gaps have different
remedies and different costs. **Recorded as a hypothesis. Not built.**

---

## 8. Fresh validation corpus

### 8.1 Candidates

| candidate | trajectories | goals | production-visible action evidence | independent reference outcome | licence | rule inputs present? | prior exposure in this project |
|---|---|---|---|---|---|---|---|
| **AgentRewardBench** (in repo) | 1302 | yes | **no -- see 8.2** | expert `trajectory_success` | research terms, in repo | **no** | **fully burned** |
| **tau-bench** `historical_trajectories` | **1980** (verified) | yes, as user turns | **yes -- named tool calls with arguments** | programmatic env reward | **MIT** (verified) | **yes** | **none** (verified by grep across `docs/` and `scripts/`) |
| WebVoyager | 643 tasks, unverified trajectory release | yes | browser actions, same element-identity problem as ARB | partly GPT-4V-derived (85.3% human agreement) -- an LLM label, not independent | unverified | no | none |
| Mind2Web | large | yes | human demonstrations with element identity | **no agent-failure labels** -- it is a demonstration corpus | unverified | no | none |
| OSWorld / WorkArena / BrowserGym | environments, not trace corpora | -- | would require running agents | execution-based, but requires paid inference to generate | -- | n/a | none |

### 8.2 Why ARB cannot supply the inputs, regardless of the burn ledger

Even if ARB were untouched, the rule is not implementable on it. Measured label-blind
across the corpus:

```
cases with at least one click and a final accessibility tree   1200
total click actions                                          15401
click bids resolvable against the FINAL axtree               10134  (65.8%)
per-case resolution coverage                        median 50.0%, mean 52.0%
cases where NO click resolves at all                       221 / 1200
click argument form (sample of 300 cases)        bare numeric bid 2680, other 232 (92%)
```

Browser-agent actions are recorded as `click('156')`. The bid is an index into the
accessibility tree *of the step at which the click occurred*, and the archive retains
only the **last** accessibility tree. 65.8% is therefore an optimistic ceiling on
resolution, since a bid that happens to exist in the final tree may denote a different
element than it did three navigations earlier. 221 cases resolve nothing.

The obligation classes that actually appear in the discovery data -- upvote, delete,
cancel, submit, assign, like -- are all click-mediated. `webarena.471` "Cancel order 307"
is recorded as `click('156'), click('168'), click('2090')`. There is no production-visible
way to ask whether a cancel was attempted.

This places `required-conjunct-never-attempted` in **deployability class B**: producible
with instrumentation, absent from the archive. Any real browser agent can log the
accessible name and role of the element it clicked; AgentRewardBench simply did not.
That is a property of the archive, not of the rule, and it is the single most important
finding of this pass.

### 8.3 Recommendation: tau-bench historical trajectories

Verified directly against `sierra-research/tau-bench` (MIT, 1452 stars, last pushed
2026-03-18):

```
historical_trajectories/gpt-4o-airline.json             200 records,  50 tasks, 4 trials
historical_trajectories/gpt-4o-retail.json              460 records, 115 tasks, 4 trials
historical_trajectories/sonnet-35-new-airline.json      400 records,  50 tasks, 8 trials
historical_trajectories/sonnet-35-new-retail.json       920 records, 115 tasks, 8 trials
TOTAL                                                  1980 records, 165 distinct tasks
```

Why it fits, point by point against the brief's requirements:

- **Rich traces.** Each record is a full chat trajectory (`system` 200, `user` 1490,
  `assistant` 2454, `tool` 1164 messages in the airline file). Every tool call carries a
  function name and arguments. Verified.
- **User goals in production-visible form.** The user's request appears as user-role
  turns in the conversation. The hidden task brief in `tasks_test.py` is **not used**;
  it is oracle metadata.
- **A clean read/write split in the catalogue.** Airline write tools:
  `book_reservation`, `cancel_reservation`, `send_certificate`,
  `update_reservation_{flights,baggages,passengers}`. Retail write tools:
  `cancel_pending_order`, `exchange_delivered_order_items`,
  `modify_pending_order_{address,items,payment}`, `modify_user_address`,
  `return_delivered_order_items`. This is the element identity ARB lacks, supplied by
  construction.
- **An independent reference outcome.** The `reward` field comes from the environment's
  database-state comparison plus required-output checks. It is not an LLM judgment and
  it is not derived from any evaluator this project is studying.
- **A modification-task population large enough to test harm.** Measured label-blind:
  438 / 1980 (22.1%) of trajectories contain no write-tool call at all -- 41.0% and
  37.5% in the two airline files, 15.7% and 14.6% in the two retail files. That is the
  pre-filter ceiling on the firing population.
- **An abstention analogue.** `transfer_to_human_agents` is called 48 times in the
  airline file, playing the role `report_infeasible` played in ARB.
- **Never inspected by this project.** Grep across `docs/` and `scripts/` returns no
  mention of tau-bench or any non-ARB corpus. The only other alternate-corpus documents
  in the repo, `alternate_source_collection_protocol.md` and
  `alternate_corpus_red_team.md`, concern collecting a second *judge's* output on
  production traffic and name no external dataset.

**Engineering work required:** an ingest script that reads the four JSON files, extracts
per-record `(task_id, trial, user_turns, ordered tool calls)`, and **drops `reward` and
`info` on ingest** so that rule development cannot see them. A verb-to-ACTION_CLASS table
written from the tool docstrings. Estimated as one small deterministic module; no model
call anywhere in it.

### 8.4 Chronology disclosure

The four trajectory files were downloaded during this scoping pass in order to answer the
brief's question of whether the rule's inputs exist. What was read: record counts, task
and trial ids, message roles, and tool-call names. What was **not** read: the `reward`
field and the `info` field, which were programmatically withheld at inspection time. No
reference-conditioned quantity on tau-bench has been computed. The files live in a
temporary directory and are not committed.

### 8.5 Known limitations of this corpus

- **Two domains, one company's benchmark.** Generalisation beyond customer-service tool
  agents is not tested.
- **Heavy task-level clustering.** 1980 trajectories over 165 tasks, so 8-12 trajectories
  per task. Effective sample size for anything task-correlated is far closer to 165.
  Section 9 treats this as the binding constraint.
- **Two agent models only**, both from 2024.
- **The reward is not a human label.** It is a programmatic check. It is independent of
  any LLM judge, which is what matters here, but it inherits whatever the benchmark's
  authors decided counts as success.
- **There is no evaluator to correct.** ARB supplied a cached judge whose errors the
  rules were repairing. tau-bench supplies no such judge, so the primary metric shifts
  from "does this fix an evaluator's error" to "does this rule's firing identify
  reference-failures without catching reference-successes". The preregistration states
  this consequence explicitly rather than pretending the designs are parallel.

---

## 9. Power

### 9.1 The relationship, not a manufactured threshold

With zero harms observed in `n` firings, the one-sided 95% upper bound on the true harm
rate is `1 - 0.05^(1/n)`:

| n firings, zero harms | 95% upper bound on harm rate |
|---|---|
| 6 (R2's actual) | **39.3%** |
| 13 | 20.6% |
| 30 | 9.5% |
| 60 | 4.9% |
| 100 | 3.0% |
| 149 | 2.0% |
| 300 | 1.0% |

Inverted: `n = ln(0.05) / ln(1 - p)`. To bound harm at 5% you need 59 clean firings; at
2%, 149; at 1%, 299.

The brief forbids inventing a business tolerance we do not possess, so none is invented.
What is stated instead: **the decision of how many firings are enough is identical to the
decision of what harm rate is tolerable, and the table above is the whole of that
relationship.** Whoever owns the deployment owns the number.

### 9.2 The clustering correction, which dominates

The trajectory-level table above is the optimistic reading. With 165 distinct tasks and
8-12 trajectories each, trajectories from the same task share the same user request, the
same obligation, and very often the same agent behaviour. For any effect that operates at
task level -- and "did the extractor mis-parse this request" operates entirely at task
level -- the effective n is the number of **distinct tasks** on which the rule fires, not
the number of trajectories.

Worked consequence: if the rule fires on 200 trajectories concentrated in 20 tasks, the
harm-rate bound is the n=20 bound (13.9%), not the n=200 bound (1.5%). The preregistration
therefore requires both counts be reported side by side, and requires the **task-level**
count to be the one compared against any threshold.

### 9.3 Metrics implied by the recommended authority

Because the disposition is `UNVERIFIABLE` + escalate rather than a veto, "harm" is not
"changed a correct verdict to an incorrect one". The metric set follows the authority:

- **escalation volume**, at trajectory level and task level
- **reference-fail rate among firings vs the corpus base rate** (the lift that R2 turned
  out not to have)
- **counterfactual-veto helped / harmed / net**, reported and never applied
- **false-fire audit**: among firings where the reference says success, a manual
  label-blind-at-design-time classification into the section 5 rows, so that a failure is
  diagnosed rather than merely counted

---

## 10. Deliverables

The frozen specification is in `docs/required_conjunct_preregistration.md`, committed in
the same commit as this document and before any reference-conditioned tau-bench number
exists.

## 11. Claims after this pass

| claim | status |
|---|---|
| Evidence-absence detection has held-out support as an escalation signal (R3) | ~~**survives unchanged**~~ **narrowed 2026-10-02** -- the preregistered disposition is still ACCEPTED and the test ran as specified, but all 133 firings sit in visualwebarena, and conditioned on slice the separation is +5.8 pp (p = 0.26) against +11.2 pp (p = 0.0015) pooled. Held-out support for the *escalation reading* is what shrank; see `research_synthesis.md` §3.3.1 |
| R2 is promising but underpowered | **weakened** -- still ACCEPTED as preregistered, but firing precision is 1.06x and the harm bound at n=6 is 39.3% |
| A broad deterministic veto architecture is validated | **still false**, and this pass adds a fourth reason |
| ~~Two of four candidate deterministic rules failed held-out evaluation~~ | **superseded 2026-10-02** -- only two of the four (R2, R3) had numeric accept/reject gates; R1 and R4 had a direction and no threshold, and R4 met its direction at 1.20x. See `research_synthesis.md` §3.3.3 |
| Human review cost remains material | **survives, and grows** -- the new rule's pre-filter population is 22.1% of trajectories |
| The 15 discovery cases may teach but not prove | **extended** -- the 1259 validation cases now fall under the same rule |
| AgentRewardBench can host the next rule | **dead** -- zero untouched cases, and the required inputs are not in the archive |
| `required-conjunct-never-attempted` may subsume R2 | **not established** -- partial overlap, different mechanism |

## 12. Model recommendation

**Sonnet 4.6** for the next task, which is deterministic ingest, a verb table written
from tool docstrings, and a rule that performs set membership over tool names. None of it
requires adjudication.

Opus is warranted only if the label-blind precision audit of the extractor (section 3.5)
finds ambiguous user requests that need judgment to classify. That is a small, bounded
escalation, and it should be requested at that point rather than assumed now.
