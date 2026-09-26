# Post-implementation red-team review

Written after `88 passed`, before declaring anything. The purpose is to try to
falsify the project, not to defend it. Every number below was measured from the
shipped code, not recalled from the architecture note.

Repairs made as a result of this review are in commit
`Delete two decorative abstractions, make two economic fields load-bearing`.

---

## The measurement everything else hangs off

For each shipped context: how large is the candidate space, how many candidates
survive admissibility, and how many *distinct mechanism/scope/cadence families*
survive? The last column is the one that matters. If exactly one family survives
everywhere, admissibility is doing all the work and ranking is theatre.

| scenario | context | enumerated | admissible | families | distinct sources |
|---|---|---:|---:|---:|---:|
| A voice_early | inner_loop | 288 | **1** | **1** | **1** |
| A voice_early | checkpoint | 288 | 2 | 2 | 1 |
| A voice_early | nightly | 288 | 24 | 2 | 1 |
| A voice_early | discovery | 288 | 24 | 2 | 1 |
| B duplex_silence | verify | 432 | 4 | 3 | **3** |
| B duplex_silence | blast_radius | 432 | 4 | 2 | 1 |
| C clinical_factual | production_guard | 648 | 10 | 1 | 1 |
| C clinical_factual | routine_policy | 648 | 404 | 8 | 3 |

Reproduce with `docs/` absent — the numbers come from
`enumerate_candidates` and `plan` directly.

Read honestly, this says:

- **Ranking does real work in 7 of 8 contexts.** In `verify` it chooses between
  three different mechanisms; in `routine_policy` between three mechanisms, two
  populations and three cadences; elsewhere it chooses cadence or replication
  count.
- **`inner_loop` has exactly one admissible plan.** The architecture note's
  §9.1 said that if a scenario has exactly one survivor, that is close to
  falsification and must be reported. So: reported. Section Q1 below explains
  why I do not think it falsifies the abstraction, and what would.
- **`production_guard` has ten survivors but only one family.** Policy narrows
  the mechanism to one and ranking only picks the replication count. That is the
  correct behaviour for a policy that demands an authoritative source, full
  coverage, synchronous execution and human confirmation — but it means Scenario
  C is a test of the constraint engine, not of the ranker.

---

## 1. Is this really doing anything more than static rules encoded in YAML?

**Partly yes, partly no, and the boundary is sharp enough to state.**

What *is* a static rule table: `constraints.GOALS`, the map from `Intent` to an
`EvidenceGoal`. Four intents, six booleans and a cadence set each. That is a
lookup table written in Python rather than YAML, and calling it anything grander
would be dishonest.

What is *not* a static rule, and could not be written in YAML without
recomputing it by hand every time an input moves:

| output | derived from | evidence |
|---|---|---|
| replication count `n` | sensitivity, FPR, `maximum_error_requirement` | judge at 0.70/0.10 under ε=0.05 needs n=7; under ε=0.35 needs n=1 |
| threshold `k` | the same, via smallest `k` meeting both bounds | n=7 ⇒ k=3; n=3 at 0.995/0.002 ⇒ k=2 |
| escalation band | `1..k-1`, empty when k=1 | deterministic paths never acquire an escalation hop, and nothing in the code says so |
| prove-red sufficiency | `prove_red_runs >= n` | the judge with 3 REDs is rejected for `verify_fix` at ε=0.05 but not at ε=0.35 |
| cadence | cost per *window*, which is `cost × runs_per_window` | per_checkpoint beats per_change at 2400s×2/day vs 2400s×15/day |
| mechanism | least cost among survivors | the free oracle beats a $12.60/day frontier judge in B |

The strongest evidence that the derivations are real is that **two of them
contradicted my own architecture note**. §8 predicted that a 5-minute `discover`
context would return no admissible plan; it returns a plan, because discovery is
asynchronous and the feedback budget therefore does not bind. §8 also predicted
the nightly suite would run 8 replications because that is what the real team
did; the planner derives 7 from the measured noise and the error bound. A rules
table encoded in YAML cannot disagree with its author.

The honest weakness: **the `Intent → EvidenceGoal` table is the one place where a
new intent requires new code rather than new data.** If the abstraction is going
to collapse, it collapses there — see "What would falsify this" below.

## 2. Are `AssuranceProfile`, `QualificationEvidence` and `ExecutionProfile` genuinely separable?

**Yes, and it is enforced by three separate mechanisms rather than by
convention.**

- *Structurally.* `test_q2_no_field_appears_in_both_qualification_and_economics`
  and `test_q2_assurance_profile_contains_no_mechanism_or_price_fields` compare
  the dataclass field sets and assert disjointness. Adding a price to
  `QualificationEvidence` breaks a test.
- *At rest.* `World.qualification` and `World.economics` are two dicts keyed
  differently (`QualificationKey` vs `SourceVersionRef`) and never merged.
- *In motion.* `World.reprice` and `World.requalify` each construct a copy that
  touches exactly one dict, and
  `test_q2_the_two_registries_are_independent_dicts` asserts the other is
  unchanged by identity.

## 3. Are we accidentally treating evaluator quality as global?

**No, and the fixture is built to make the mistake visible if it returns.**

`World.qualification_for` does an exact dict lookup on
`(SourceVersionRef, FailureModeRef, population_id)`. There is no inheritance, no
defaulting, no "if not found, try the parent population". In `voice_early`,
`behavioral_simulation@v3` is qualified on `affected_scenario` and **not** on
`scenario_corpus`, and that single missing row is what forces the nightly suite
onto a judge. If anyone adds a fallback, `test_q3_*` fails and Scenario A stops
reproducing.

## 4. Have we hidden any supposedly dynamic parameter inside static configuration?

**Structurally prevented for the nine planner-controlled fields; two grids
remain hard-coded and I am flagging them rather than defending them.**

`loader.FORBIDDEN_KEYS` recursively rejects any scenario file containing
`replications`, `sample_fraction`, `run_percentage`, `cadence`,
`execution_mode`, `decision_threshold`, `threshold_k`, `escalation_band` or
`escalation_target`, at any depth. `test_q4_the_loader_rejects_forbidden_keys`
is parametrised over all nine and tampers with a real scenario file to prove it.

Still hard-coded, and honestly these are the weakest spots in the answer:

- `candidates.SAMPLE_FRACTIONS = (1.0, 0.25, 0.10, 0.05)` and
  `_LADDER = range(1, 13)`. These are *search grids*, not configuration — no
  scenario can set them and the planner will extend the ladder if a source needs
  more runs than it contains. But a grid is still a prior. A 0.15 sample
  fraction cannot be chosen, and nothing tells the reader that.
- `CADENCE_WINDOW_SECONDS` fixes nightly at 8 hours and a "window" at one day.
  `changes_per_window` and `checkpoints_per_window` are configurable, so the
  ratio that drives cadence choice is not hidden, but the absolute day is.

## 5. Does run percentage always have an explicit denominator?

**Yes, by construction.** `EvaluationPopulation.denominator` is a required
positional field — `test_q5_a_population_cannot_exist_without_a_denominator`
asserts that constructing one without it raises `TypeError`. `PlanStep` exposes a
percentage only through `scope_phrase()`, which interpolates the denominator into
the same string, and
`test_q5_every_step_of_every_admissible_plan_has_a_denominator` walks every step
of every admissible plan in all three scenarios asserting the denominator appears
in the rendered phrase. There is no code path that produces a bare percentage.

The renderer says `100% of production interactions asserting a high-consequence
fact, per day (400 of 400)`, never `100%`.

## 6. Are scope, replications, cadence and evaluator type truly independent?

**Yes.** The enumerator takes their full cross product, and
`test_q6_each_dimension_varies_alone_across_the_scenarios` pins one axis moving
at a time across the real scenarios:

- scope alone: B `verify` → B `blast_radius` is the same oracle, same n=1,
  1 unit → 20 units.
- replications alone: A `checkpoint` → A `nightly` is the same judge, same 20
  units, n=1 → n=7.
- mechanism alone: A `inner_loop` → A `checkpoint` changes source at equal n.
- cadence alone: B `verify` → B `blast_radius` changes per_change → per_checkpoint.

There is one soft spot: replications and cadence interact through
`runs_per_window` in the cost. That is intended — it is the whole reason nightly
is affordable at n=7 — but it means they are independent *decision variables*,
not independent *cost terms*.

## 7. Can price change without invalidating qualification?

**Yes.** `World.reprice` cannot reach the qualification dict; it is a
`dataclasses.replace` over `economics` only. Repricing `frontier_judge@v2` to
$1234 leaves `world.qualification` equal by value. This is the property the
transition tests lean on: transition 2 ("judge becomes cheaper") is implemented
as a pure reprice, and the fact that the plan changes while the derived
replication count does *not* is the evidence that price and quality are separate
levers.

## 8. Can an evaluator-version change correctly invalidate prior qualification?

**Yes, by lookup miss rather than by an invalidation routine.** Bumping
`state_machine_assertion@v2` to `@v3` while carrying its `ExecutionProfile`
forward leaves the qualification rows keyed to v2. `qualification_for` returns
`None`, the source is rejected on `qualification_exists`, and the planner either
picks a different mechanism or reports no plan. Same for a failure-mode version
bump: redefining `VFD-TURNTAKING@v4` as `@v018` makes every source in the world
unqualified at once.

**This question caused a repair.** `FrozenVerificationClaim` existed to express
"a RED under one evaluator version cannot license a GREEN under another" — but
nothing in the planner constructed one and nothing consumed one. Its only test
asserted that two hashes differ, which is a property of `dataclass(frozen=True)`,
not of this design. It has been deleted. The freeze it described is already
enforced, and now the test asserts the enforcement: prove-red evidence is filed
against an exact `QualificationKey`, and the v3 key is not in the dict.

## 9. Can the planner explain why an expensive, high-quality judge is not worth buying?

**Yes, and the explanation is economic rather than categorical, which is the
point.** In Scenario B `verify`, all three mechanisms are admissible. The
frontier judge is not disqualified for being a judge — it is qualified, it has
twelve prove-red observations, and it is available. `explain_loss` returns:

```
frontier_judge  ->  admissible but dominated on cost: $12.6000/window vs $0.0000/window
transcript_judge -> admissible but dominated on cost:  $3.7500/window vs $0.0000/window
```

The reason extra sensitivity buys nothing here is visible in the plan itself: the
oracle's step reports `P(miss)=0.00e+00`. There is no assurance left to purchase,
so the comparison collapses to price. `explain_loss` names the *first separating
field* in the rank key rather than emitting a narrative, so it cannot flatter the
winner.

## 10. Have we created abstractions not exercised by any scenario?

**We had four. All four are now either deleted or covered.** This was the most
productive question in the list.

| abstraction | verdict | action |
|---|---|---|
| `FrozenVerificationClaim` | no producer, no consumer, duplicated `QualificationKey` | **deleted** |
| `DevelopmentContext.change_scope` | a string that reached only a rationale header; changing it changed nothing | **deleted** |
| `QualificationEvidence.evidence_date` | parsed, stored, never read | now rendered against the step it qualifies |
| `QualificationEvidence.known_limitations` | parsed, stored, never read | now rendered as `caveat:` lines |
| `ExecutionProfile.parallelism` | in the wall-clock formula, but no scenario or test varied it | test now flips admissibility with it |
| `ExecutionProfile.available` | in the constraint engine, never exercised | test now asserts it produces `source_available` |

Fields that survive scrutiny: every `AssuranceProfile` field except
`profile_ref` is proven to change the admissible set or the plan contents by
`test_q10_every_assurance_profile_field_changes_the_outcome_somewhere`, which
flips each one in turn and asserts the outcome signature moves. `profile_ref` is
proven *inert* by its own test — it is the policy-by-reference handle the spec
asked for, and the planner must never interpret it.

The date and limitations repairs are worth naming for what they are: those two
fields are not load-bearing for *admissibility*. They are load-bearing for
*audit*. A plan that cannot tell you its evidence is from 2026-09-12 and was
measured on a single accent cohort is not auditable, and auditability was the
stated reason for excluding an LLM from the planner in the first place.

## 11. Does Scenario A reproduce the real hierarchy for principled reasons?

Measured output:

| context | mechanism | n | units | cadence | blocking | background | cost/run |
|---|---|---:|---:|---|---:|---:|---:|
| inner_loop | behavioral_simulation | 1 | 1 | per_change | **2.0 min** | — | $0.00 |
| checkpoint | transcript_judge | 1 | 20 | per_checkpoint | **40.0 min** | — | $1.25 |
| nightly | transcript_judge | **7** | 20 | nightly | — | **4.7 h** | **$8.75** |

Against the brief's 2 min / 40 min / ~5 h / ~$10 / 8 runs: every figure lands,
and none is written down anywhere in the repo.

**Why I believe this is principled and not fitted.** Three of these outputs
resisted me:

1. The replication count is 7, not 8. I could have made it 8 by nudging the
   sensitivity in the fixture. I did not, because the planner deriving a number
   *close to but not equal to* the number a team reached by intuition is a more
   interesting result than a match.
2. The first fixture I wrote qualified `behavioral_simulation@v3` on the whole
   corpus, and the nightly plan then picked the free oracle and the scenario
   collapsed. The fix was not to special-case anything: it was to notice that the
   real reason that team ran a judge suite is that **no machine-verifiable oracle
   exists for behavioural quality corpus-wide**, and to delete the qualification
   row that claimed otherwise. The scenario now reproduces because the world is
   described correctly.
3. "All 20 scenarios × 1 run" was inadmissible at ε=0.05, because a 0.70/0.10
   judge cannot bound both error directions in one shot. My first instinct was
   that this was a bug. It is not — it is the planner telling me that the
   40-minute checkpoint run and the 5-hour nightly run are *answering different
   assurance questions*. That is why the fixture now carries two profiles
   (`screen` at ε=0.35, `gate` at ε=0.05) and why the 8× replication jump is a
   policy consequence rather than a constant.

**The remaining discomfort.** Two contexts differ by an assurance profile that I
chose after seeing which ε produced n=1 and n=7. I did not tune a coefficient,
but I did choose where to stand. A cleaner demonstration would derive ε from
something external.

## 12. Does Scenario B select prove-red deterministic verification without being special-cased?

**Yes, and this is machine-checked rather than asserted.**
`test_no_planner_module_is_aware_of_any_scenario` greps every module in
`src/assurance_planner/` for ten tokens — `silence`, `duplex`, `laterality`,
`clinical`, `voice`, `VFD-`, `HCF-`, and all four source ids — and fails if any
appears. `test_the_planner_holds_no_clinical_knowledge` does the same for
clinical vocabulary. "judge" appears in planner modules only in comments and in
the `SourceKind.STOCHASTIC_JUDGE` member name. `SourceKind` is branched on
exactly twice in the whole planner, both in `constraints.py`, and neither branch
prefers or penalises a stochastic judge:
`choose_human_confirmer` requires `SourceKind.HUMAN` because
`human_confirmation_required` is a demand for a human; `choose_escalation_target`
accepts `open_ended or HUMAN` because re-running the same fixed criterion cannot
resolve a case that criterion already found ambiguous. Nothing tests for
`STOCHASTIC_JUDGE` anywhere.

The selection happens because n=1, k=1 for a source with sensitivity 1.0 and FPR
0.0, and `prove_red_runs=1 >= 1` satisfies the prove-red bar — the "one RED and
one GREEN suffice for a deterministic evaluator" primitive falls out of the same
binomial machinery that demands seven runs of the judge. No branch on
`SourceKind` produces it.

## 13. Does Scenario C constrain the planner without putting clinical judgement in planner code?

**Yes.** The two contexts in `clinical_factual.yaml` share a world, a set of
mechanisms, a set of qualification measurements and a set of prices. Only the
`AssuranceProfile` differs. The result moves from $740.48/day with 480 human
minutes to $0.0004/day with zero — six orders of magnitude, from four booleans
and an ε.

The one thing worth flagging: policy binds the *whole decision path*, not just
the primary source. An early version escalated ambiguous cases to a
non-authoritative judge, which routed around the very constraint that had
selected the primary. `choose_escalation_target` now filters on
`consults_authoritative_source`, and
`test_escalation_target_must_also_satisfy_policy` pins it by showing the strict
profile escalates to a human and the routine profile escalates to the cheaper
judge.

---

## What I think is actually weak

Four things, in descending order of how much they bother me.

**1. `inner_loop` has one admissible plan.** Admissibility, not economics,
decided Scenario A's inner loop. I do not think this falsifies the abstraction,
because the constraints that eliminated the alternatives are themselves derived
(the judge fails `error_bound_met` at n=1 and `prove_red_sufficient` at n=7 with
only 3 REDs recorded — both computed, neither stipulated). But it does mean that
in the tightest, most common development context, this system is a filter rather
than an optimiser. **The thing that would genuinely falsify the project is a
world where the derived constraints admit exactly one plan in *every* context.**
That is not this world — `verify` admits three mechanisms and `routine_policy`
admits eight families — but it is the failure mode to watch as scenarios are
added.

**2. Replications are assumed independent.** `P(miss) = P(Bin(n, s) < k)` assumes
each run is an independent draw. For a stateful voice agent with a cached LLM and
a fixed seed, consecutive runs are correlated, and the true miss probability is
higher than reported — possibly much higher. The planner therefore *understates*
the replication count needed. This is the assumption most likely to be wrong in a
way that matters, and nothing in the current design detects it.

**3. Sensitivity and FPR are measured end-to-end over (system × evaluator).**
When the system under test changes, the qualification evidence is stale, but the
key does not change — only an evaluator or failure-mode version bump orphans it.
There is no `system_version` in `QualificationKey`. This is a real hole in the
invalidation story and I did not close it because no scenario exercises it.

**4. Corpus sampling is not modelled.** The enumerator offers fractions below 1.0
only for live streams, because v0 has no model of *which* corpus cases to drop or
what coverage is lost by dropping them. That is the honest choice, but it means
"run percentage is a decision variable" is only demonstrated on one of the two
population kinds.

One minor residue: for nightly-vs-per_checkpoint asynchronous corpus plans at
equal cost, equal blocking time and equal invocations, the tie breaks on
`plan_id`. The rationale says so explicitly rather than inventing a preference.
