# Architecture note — assurance-planner v0

Written **before** implementation, revised only where the implementation falsified a
claim made here. Revisions are marked `[REVISED]`.

## 0. What this is

A deterministic function:

```
plan : (DevelopmentContext, FailureMode, AssuranceProfile, World) -> PlanningResult
```

where `World` holds evidence sources, qualification evidence, execution economics and
evaluation populations. No LLM, no network, no clock, no randomness inside the planner.

The thesis under test: **"least-cost admissible evaluation strategy" is a real
computation**, i.e. the interesting content lives in *admissibility*, and once
admissibility is right, selection is just "cheapest". If instead we find ourselves
hand-weighting a scoring function to make scenarios come out right, the abstraction has
collapsed into a rules engine and we should say so.

---

## 1. Smallest domain model

Eight types. Anything not on this list is deferred.

### 1.1 `FailureMode`
`(id, version, case_id, description)`.

`case_id` is the reproducible failure case the mode is anchored to. Versioned: a
definition change is a new `FailureMode`, and qualification evidence keyed to the old
version does not transfer.

### 1.2 `DevelopmentContext`
`(intent, feedback_budget_seconds, change_scope, amortization_runs)`.

`intent ∈ {discover, verify_fix, assess_blast_radius, release}`.

**Intent is not a preference weight. It selects an evidence goal, and the goal imposes
admissibility requirements.** This is the single most important design decision in v0
(see §4).

`amortization_runs` = how many times this plan is expected to execute before the next
change invalidates it. Used only to report amortized vs. per-run cost; it does not
affect admissibility in v0.

**[REVISED after implementation]** Two changes. `change_scope` is gone: it was a string
that reached only a rationale header, and by the rule this note applies to
`AssuranceProfile` — only keep a field if changing it can change the outcome — it had no
business existing. `amortization_runs` shipped as the pair
`(changes_per_window, checkpoints_per_window)`, and it turned out to be *load-bearing*
rather than reporting-only: per-window cost is `cost × runs_per_window(cadence)`, which
is what makes cadence an economic decision instead of a free parameter. Without it a
per-change suite and a nightly suite cost the same and the planner has no grounds to
prefer either.

### 1.3 `AssuranceProfile`
Policy-by-reference plus the minimum structured constraints:

```
profile_ref                    str    opaque; the planner never interprets it
maximum_error_requirement      float  bound on the decision procedure's error probability
sampling_allowed               bool
human_confirmation_required    bool
authoritative_source_required  bool
synchronous_requirement        bool
uncertainty_disposition        enum   accept | escalate
```

Every field was checked against the rule "only add a field if changing it can change
which plans are admissible". All seven pass; `profile_ref` is the exception and is
deliberately inert — it exists so the *organizational* risk decision has a stable
identifier the planner does not reason about.

### 1.4 `EvidenceSourceVersion`
`(source_id, version, kind, open_ended, consults_authoritative_source)`.

`kind ∈ {deterministic, stochastic_judge, human}`.

`open_ended` — can this mechanism surface a failure its criterion did not anticipate?
A programmatic assertion cannot; a general-rubric judge and a human can. This is a
structural property of the mechanism, not a policy knob, and it is what makes
`discover` a different problem from `verify_fix`.

`consults_authoritative_source` — does the mechanism reconcile against a system of
record rather than producing a judgement? Structural, satisfies
`authoritative_source_required`.

`(source_id, version)` is the qualification key. Changing model/prompt/rubric ⇒ new
version ⇒ prior qualification no longer matches ⇒ source becomes inadmissible until
re-qualified. That is the intended, load-bearing behaviour.

### 1.5 `EvaluationPopulation`
`(id, denominator, kind, case_ids | units_per_window)`.

`kind ∈ {enumerable_corpus, live_stream}`.

`denominator` is a mandatory human-readable string ("affected regression scenarios",
"production interactions per day"). **There is no code path that produces a run
percentage without one** — the fraction lives on the plan step, the denominator comes
from the population, and the renderer prints them together.

Corpus vs. stream is not cosmetic: it determines whether "sync" means *blocks the
developer for a batch wall-clock* or *adds latency to an end-user interaction*. These
are different quantities and v0 refuses to add them together.

### 1.6 `QualificationEvidence`
Keyed by the triple **`(source_version, failure_mode_version, population_id)`**.

```
sensitivity              P(flag | failure present), measured end-to-end
false_positive_rate      P(flag | failure absent),  measured end-to-end
observation_count        n of the qualification study
prove_red_runs           observed REDs against a known-broken implementation
prove_green_runs         observed GREENs against the fixed implementation
known_limitations        list[str], rendered in rationale, not interpreted
evidence_date            date
```

Exact-match lookup. No inheritance, no defaults, no "qualified elsewhere so probably
fine here". A judge qualified on the focused case is **not** qualified on the full
corpus until someone records that row.

`sensitivity`/`false_positive_rate` are deliberately **joint** over
(system-under-test × evaluator). In the real setting you cannot measure them
separately without a different experiment; pretending to separate them would be a fake
knob. Consequence: "the judge got less noisy" and "the SUT got less flaky" are the same
input to v0. Documented limitation, see §5.

### 1.7 `ExecutionProfile`
Keyed by `(source_id, version)` in a **separate registry**:

```
cost_per_invocation_usd
latency_seconds_per_invocation
parallelism
human_minutes_per_invocation
human_capacity_per_window
available
```

No qualification field may appear here and no economic field may appear in
qualification. The two registries are loaded from different YAML blocks and never
merged. A price change is a write to one dict and cannot touch the other.

### 1.8 `PlanStep` / `EvidencePlan`
Step: `(source_version, population, sample_fraction, denominator, replications,
decision_threshold_k, escalation_band, cadence, execution_mode, role)`.

Plan: ordered steps + computed `PlanEconomics` + rationale.

---

## 2. The decision-procedure model (how replications stop being a magic number)

A step runs the same source `n` times on a case and flags the case as failing when
`>= k` runs flag it. Given qualification `(sensitivity s, false-positive rate f)`:

```
P(miss)        = P(Binomial(n, s) <  k)
P(false alarm) = P(Binomial(n, f) >= k)
```

A step is **statistically admissible** iff both `<= maximum_error_requirement`.
`(n, k)` is chosen as the lexicographically smallest admissible pair.

Interpretation of `maximum_error_requirement` as bounding **both** error directions is
an assumption; the prompt does not say which error it bounds (§3.1).

Consequences that fall out rather than being coded:

- deterministic oracle `(s=1, f=0)` ⇒ `n=1, k=1`. "One RED and one GREEN may be
  sufficient" is a theorem here, not a special case.
- stochastic judge `(s=0.70, f=0.10, ε=0.05)` ⇒ `n=7, k=3`.
- **verified before writing this note**: `n` is weakly monotone decreasing in `s` and
  weakly increasing in `f` across a 6×10 grid, 0 violations. Transition test 1 is a
  property of the model, not of a fixture.

Decision bands:

```
0 flags           pass
1 .. k-1 flags    inconclusive -> escalation band
>= k flags        fail
```

For `n=1, k=1` the escalation band is **empty**. This is why `uncertainty_disposition
= escalate` does not bolt a human onto a deterministic verification path: there is no
inconclusive region to route. That result is derived, not special-cased.

---

## 3. Contradictions and underspecification in the prompt

### 3.1 `maximum_error_requirement` has no specified direction or unit
Not stated whether it bounds misses, false alarms, or both; nor whether it is
per-decision, per-case or per-window. **v0: bounds both, per decision, on one case.**
Changing this would change every derived `n`.

### 3.2 "Least-cost admissible" vs. intent-sensitive ranking
`discover` wants breadth, which costs *more*. If intent were a ranking weight, "least
cost" would be false and we would be hand-tuning coefficients. **v0 resolves this by
making intent purely an admissibility input** (§4). Ranking is then literally
least-cost. This is the difference between an abstraction and a scoring hack, so it is
worth the rigidity.

**[REVISED after implementation]** "Least cost" needed one more term than anticipated,
and it is worth being explicit about why it is not a tuned weight. Money alone leaves
cadence undetermined for a **zero-cost** source: a free deterministic oracle costs $0
whether it runs fifteen times a day or twice, so the ranker was breaking the tie on
plan id. The rank key therefore carries `blocking_feedback_seconds_per_window` as its
second term — the developer time the plan consumes per day. This is not a coefficient;
it is a second resource being spent, ordered lexicographically after money rather than
blended with it, so no exchange rate between dollars and developer-minutes is ever
invented. Full key: money/day, then developer wait/day, then added interaction latency,
then human minutes/day, then invocations, then plan id.

### 3.3 Run percentage on a finite corpus
"100% of affected regression scenarios" is a percentage of an enumerable set, where a
subset — not a sampling rate — is the real decision. v0 keeps the fraction uniform for
both kinds but tags the population kind, so `sampling_allowed=false` correctly rejects
`fraction < 1.0` in both cases while the denominator stays honest.

**[REVISED after implementation]** Not enough. Enumerating `fraction < 1.0` over a
finite corpus produced plans with no model of *which* cases were dropped or what
coverage was lost by dropping them — a percentage that was arithmetically honest and
epistemically empty. The enumerator now offers fractions below 1.0 **only for
`LIVE_STREAM` populations**, which cannot be exhausted and for which a rate is the real
decision. The cost: "run percentage is a decision variable" is demonstrated on one
population kind rather than two. The alternative was inventing a subset-selection
policy the prototype has no basis for. See red-team review, weakness 4.

### 3.4 Scenario A never states the error target that the 8 runs satisfy
The 8 was an empirical heuristic. To *derive* a replication count the planner needs an
error bound, which must come from an assurance profile. v0 supplies `ε = 0.05` for
nightly assurance and reports what falls out (n=7). The prototype therefore cannot
"reproduce 8"; it can only show that a stated error target plus measured noise lands in
the same neighbourhood. Claiming more would be tuning to the answer.

### 3.5 Prove-red is a process; the planner emits a plan
The RED→freeze→fix→GREEN cycle spans time and two implementations. A single planner
call cannot execute it. **v0 models prove-red in two places**: as *evidence already
held* (an admissibility precondition for `verify_fix`) and as a `FrozenVerificationClaim`
value object that records what was frozen. The planner does not orchestrate the cycle.

**[REVISED after implementation]** `FrozenVerificationClaim` has been deleted. Nothing
constructed one and nothing read one; the freeze it described was already enforced by
`QualificationKey`, whose exact-match lookup is what stops a RED filed against
`oracle@v2` from licensing a GREEN under `oracle@v3`. Prove-red now lives in one place,
not two. See red-team review, Q8 and Q10.

### 3.6 "Human confirmation required" — of what?
Every decision, or only adverse ones? v0: **every decision in scope**, which is the
expensive reading, and therefore the one where human capacity constraints bite.

### 3.7 `availability` in ExecutionProfile
Listed as economics, but a source being unavailable is an admissibility fact. v0 keeps
it in `ExecutionProfile` (it is dynamic) and lets the constraint engine read it.

---

## 4. Intent ⇒ evidence goal ⇒ admissibility

| intent | population requirement | source requirement | prove-red required |
|---|---|---|---|
| `verify_fix` | must contain the target failure case | qualified for this mode+population | **yes** |
| `assess_blast_radius` | must cover all known regression cases | qualified | no |
| `release` | must cover all known regression cases | qualified | no |
| `discover` | must not be the single frozen case | **`open_ended`** | no |

Prove-red sufficiency is itself derived: a `verify_fix` step needs
`prove_red_runs >= n`, where `n` is the derived replication count. Deterministic
oracle: `n=1`, so one RED suffices. Stochastic judge: `n=7`, so a single RED
observation is **not** adequate evidence — exactly the property the prompt asks for,
obtained without a rule that says "judges are untrustworthy".

`discover` requiring `open_ended` is what stops the planner from being a
deterministic-oracle maximalist. A programmatic assertion cannot find a failure nobody
has specified, so in discovery the expensive judge is not merely admissible, it is the
*only* admissible mechanism. The planner can therefore explain both why the judge loses
(scenario B) and why it wins (discovery) using one rule.

---

## 5. v0 assumptions

1. `maximum_error_requirement` bounds both error directions per decision (§3.1).
2. Replications within a step are independent. False for correlated SUT state; it will
   understate `n`. Correlation would need a different qualification experiment.
3. Sensitivity/FPR are point estimates used directly. `observation_count` is recorded
   and a minimum is enforced, but no confidence interval is propagated. A judge
   qualified on 5 observations and one qualified on 5000 are otherwise treated alike.
4. Judge and SUT nondeterminism are measured jointly and cannot be separated (§1.6).
5. Costs are linear in invocations. No volume discounts, no caching, no batching.
6. Wall clock is `invocations × latency / parallelism`. No queueing, no startup cost.
7. A case costs the same regardless of which case it is.
8. Qualification never expires. `evidence_date` is recorded and rendered but does not
   gate admissibility — a staleness policy is a governance decision we do not have.
9. Plans are flat lists of steps. No conditional DAGs beyond a single escalation hop.

---

## 6. Explicitly NOT modelled in v0

- Multi-failure-mode planning or portfolio/budget allocation across modes.
- Cost of a missed defect. The planner minimises evaluation cost subject to an error
  bound; it does not do expected-loss optimisation. This is a real limitation: it means
  the planner cannot tell you whether the error bound is worth its price.
- Sequential/adaptive stopping (run 3, escalate to 8 only if ambiguous). v0 fixes `n`
  up front, which is strictly more expensive than a sequential test.
- Confidence intervals on qualification, and evidence staleness/decay.
- Scheduling, queueing, retries, partial failures, flaky infrastructure.
- Learning: nothing writes back. Qualification evidence is read-only input.
- Any persistence, service, UI, or Phoenix integration.
- Plugin architecture for source kinds. Three kinds, closed enum.

---

## 7. Mutability model

**Frozen within one verification claim** — **[REVISED after implementation]** this was
going to be a `FrozenVerificationClaim` value object. It turned out to duplicate a
mechanism that already existed, so the claim freeze is now expressed as behaviour rather
than as a type: prove-red evidence is filed against an exact `QualificationKey`
`(SourceVersionRef, FailureModeRef, population_id)`. A RED observed under `oracle@v2`
is keyed to `oracle@v2`; a GREEN claimed under `oracle@v3` looks up a key that does not
exist, the source is rejected on `qualification_exists`, and the claim cannot be made.
The lookup miss *is* the freeze.

**Versioned between development cycles** — `FailureMode.version`,
`EvidenceSourceVersion.version`, the population's `case_ids`, qualification rows,
`AssuranceProfile.profile_ref`. Changing any of these changes a registry *key*, so
stale evidence disappears by lookup miss rather than by a validity check somebody
might forget to write.

**Dynamically changing** — everything in `ExecutionProfile`, plus the measured
`sensitivity` / `false_positive_rate` / `observation_count`. Mutable without touching
any frozen or versioned identity.

**Planner-controlled** — source mix, population, `sample_fraction`, `replications`,
`decision_threshold_k`, `escalation_band`, `cadence`, `execution_mode`, human
allocation. Nothing in this list may be read from YAML as an input; the loader has no
parser for any of them.

---

## 8. Scenario mapping

### A — early voice-agent development
Not one planner call. **Three contexts over one world**, which is the point: mechanism,
scope, replications and cadence are separate dimensions.

| context | intent | budget | expected | why |
|---|---|---|---|---|
| inner loop | `verify_fix` | 5 min | focused × 1 rep, sync, per-change | goal only needs the target case |
| checkpoint | `assess_blast_radius` | 60 min | corpus (20) × 1 rep, sync | goal needs corpus coverage; 20×120s = 40 min |
| nightly | `release` | 8 h | corpus × derived n, async, nightly | ε=0.05 with measured noise forces n>1 |

The 2 min / 40 min / 5 h hierarchy must emerge as `cases × reps × 120s`:
`1×1×120s = 2m`, `20×1×120s = 40m`, `20×7×120s = 4.7h`. Nightly cost at
$0.0625/invocation × 140 = $8.75, against the reported ~$10. If these have to be
hard-coded the scenario has failed.

A fourth context — `discover` on a 5-minute budget — should return **no admissible
plan**, because discovery needs an open-ended source over a broad population and that
cannot be bought in five minutes. An honest "you cannot do this" is a result, not a bug.

**[REVISED after implementation — this prediction was wrong.]** Discovery returns a
plan: the judge over the full 20-case corpus, nightly, asynchronous, $1.25. The
prediction assumed the feedback budget binds. It does not, because the budget bounds
*blocking* wall clock and `discover` does not gate a change, so the work is admissible
asynchronously and is checked against the cadence window instead. The scenario is
better for it: `discovery` is now the one context where the planner buys the
**expensive** judge over the **free** deterministic simulator, because only an
open-ended source can surface a failure its criterion did not anticipate. That is a
sharper counterexample to "the planner just picks the cheapest deterministic check"
than a no-plan result would have been.

### B — full-duplex silence defect (VFD-SILENCE-017)
`verify_fix`, machine-verifiable oracle available and qualified with prove-red.
Expected: deterministic oracle, focused population, n=1, ~2 min, $0. The judge is
admissible (also qualified, also has prove-red) but must lose on cost and latency,
**by ranking, not by a rule about judges**. Then a second call with
`assess_blast_radius` buys the 40-minute corpus run once.

Test must assert the judge was rejected as *dominated*, and must not reference the
scenario by name anywhere in planner code.

### C — high-consequence clinical factual mismatch
Policy does the work: `sampling_allowed=false` kills every `fraction<1.0` candidate;
`human_confirmation_required=true` kills fully automated plans;
`authoritative_source_required=true` kills any plan whose primary source does not
consult a system of record. The surviving cheapest plan is deterministic reconciliation
at 100% of the flagged-interaction stream plus human confirmation, with the judge
rejected for adding no *required* evidence at nonzero cost.

No clinical knowledge appears in planner code. Laterality/blood-type/medication live
only in a fixture's `FailureMode.description`, which the planner treats as an opaque
string. If planner code ever needs to know what "laterality" means, the separation has
failed.

---

## 9. At least three ways this abstraction could fail

1. **It is a rules engine wearing a lab coat.** If every scenario's answer is pinned by
   exactly one admissibility rule, the "optimisation" is decorative and the whole thing
   is a YAML lookup table. The only defence is that the ranking must sometimes have a
   real choice to make — several admissible plans differing in cost. If every scenario
   has exactly one survivor, that is close to falsification and must be reported.

2. **Qualification evidence is unobtainable, so the model is vacuous.** The planner
   requires per-(source × failure-mode × population) sensitivity and FPR. Nobody has
   these. If in practice they get filled in with guesses, the derived `n` inherits the
   guess and the arithmetic launders it into false precision. The model's realism
   depends entirely on an experiment nobody currently runs — which may itself be the
   most valuable thing this exercise reveals.

3. **Intent-as-admissibility is too rigid.** Making intent gate admissibility keeps
   "least-cost" honest but means the planner returns *nothing* rather than a degraded
   plan when the budget is short. Real teams degrade. If users demand "give me the best
   thing that fits", we are back to a weighted objective and §3.2's resolution
   collapses.

4. **It reduces to "prefer the cheapest qualified deterministic check".** For every
   scenario except discovery, that one sentence may reproduce the planner's output.
   Discovery is doing a lot of load-bearing work for the claim of non-triviality, and
   discovery is also the case v0 models most weakly.

5. **The economics are the easy half and the assurance is the hard half.** Cost and
   latency arithmetic is trivially correct and will look impressive in the CLI output.
   The binomial model is the only part with real content, and it rests on an
   independence assumption (§5.2) that is probably false for a stateful voice agent
   where consecutive runs share prompt/state pathologies. A correlated-failure model
   could change `n` by a large factor.

**[REVISED after implementation — how these five landed.]**

1. *Partly hit.* Measured across all eight shipped contexts, ranking has a real choice
   in seven; `voice_early / inner_loop` has exactly one admissible plan, which is the
   condition this section said must be reported. Reported, with the caveat that the
   constraints which eliminated the alternatives are themselves derived, not stipulated.
   See red-team review, §Q1 and weakness 1.
2. *Unresolved and now the top recommendation.* Nothing in the implementation made this
   better or worse; it remains the assumption the whole model rests on.
3. *Held.* No scenario needed a degraded plan, and the two no-plan results the suite
   produces (`policy_human_confirmation` with no qualified human;
   `policy_escalation_target` with no qualified escalation path) both read as correct
   answers rather than as failures to be helpful.
4. *Falsified, by discovery.* `voice_early / discovery` buys the **expensive** judge
   over the **free** deterministic simulator, because `discover` requires an open-ended
   source and the simulator is not one. "Prefer the cheapest qualified deterministic
   check" gets that context wrong. It was close for the rest.
5. *Held, and it is weakness 2 in the red-team review.* Untouched by implementation.
