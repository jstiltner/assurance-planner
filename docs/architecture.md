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

**[REVISED after the measurement pass — the triple was incomplete, and the
representation was wrong.]**

The paragraph above is the argument that the key was underspecified, and it was sitting
here the whole time. If the measured rates are joint over (SUT × evaluator), then a key
naming only the evaluator cannot say what the measurement was taken against, and
evidence gathered before a behavioural change silently remains valid after it. The key
is now a **quadruple**:

```
(source_version, failure_mode_version, population_id, distribution_id)
```

`distribution_id` is a *declared* behaviour-distribution identity carried by
`SystemUnderTest`, not the build version. This is the load-bearing choice and it was
not obvious: keying on `system_version` would orphan every qualification row on every
deploy, which makes the model useless and therefore makes people route around it.
Keying on a declaration means materiality is a human assertion with the same epistemic
status as `maximum_error_requirement` — a rebuild that changes nothing behavioural
keeps its `distribution_id` and every row survives; declaring a move invalidates them
all at once and the planner says so. No lineage, no inheritance, no partial matching. A
lookup that fails *only* on `distribution_id` is reported as `qualification_stale`
rather than as absence, because "we never measured this" and "we measured this against
a system that no longer exists" are different problems for the reader.

The rate fields are also gone. A row now stores **counts**:

```
positive_cases / true_positives      sensitivity is derived
negative_cases / false_positives     false-positive rate is derived
```

`observation_count` is derived too. The point of removing the rate fields is that there
is no longer anywhere to write a sensitivity down that the stated sample size does not
support — `0.80 from n=500` and `0.80 from n=10` were indistinguishable to v0 and are
now structurally different objects. Each rate exposes a **Wilson score interval**
(normal approximation rejected: it is zero-width at p=0, which would let a 30-for-30
oracle claim certainty). `AssuranceProfile.estimator` chooses whether the planner reads
the point estimate or the conservative bound; it defaults to `point`, so adding it
repriced nothing.

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

### 2.1 **[REVISED after the measurement pass — the model is not merely uncertain, it is the wrong shape]**

`P(Binomial(n, s) < k)` assumes the `n` runs are independent draws at a rate `s` that
is a property of the failure mode. It is not. `s` is a property of a *case*, and the
cases vary. Two consequences, in order of how badly they hurt:

**Case heterogeneity.** The quantity the planner wants is the average over cases of
each case's own miss probability. What it computes is the miss probability at the
average rate. These are not equal and the gap is not small: on `data/judge_runs_noisy`
— the deliberately well-behaved control — the model reports `P(miss)=0.042` at `n=7`
while the per-case average is `0.142`, and no `n` up to 12 reaches the 0.05 target the
model says `n=7` already met. This is a Jensen-type error, and it is present even when
every case is individually stochastic and centred on the right answer.

**A subset the evaluator is simply wrong about.** On `data/judge_runs_systematic`,
seven of twenty-four positive cases flag at ≈0.03. Repetition converges on the wrong
answer for those, so the empirical miss rate flatlines at ≈0.29 for every `n` from 1 to
12 while the model curve falls to 0.003. A single replication count per failure mode is
answering a question ("how many draws from this coin?") that the data does not pose.

The planner was **not changed** in response. Adding a heterogeneity correction to the
decision procedure is a real design change and this pass was scoped to find out whether
it is warranted, not to make it. What was added is the ability to tell:
`characterize-evaluator` reports a Pearson dispersion statistic φ, the effective run
count it implies, and both curves side by side. The honest summary of the diagnostics
themselves is that **φ is necessary but not sufficient** — fixture A passes the
clustering check (φ=1.67) and still fails the replication analysis, because
heterogeneity between cases and correlation within a case are different defects and
only the second one is what φ measures. The model-versus-empirical curve is the
diagnostic that actually bites.

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
`(SourceVersionRef, FailureModeRef, population_id, distribution_id)`. A RED observed
under `oracle@v2`
is keyed to `oracle@v2`; a GREEN claimed under `oracle@v3` looks up a key that does not
exist, the source is rejected on `qualification_exists`, and the claim cannot be made.
The lookup miss *is* the freeze.

**Versioned between development cycles** — `FailureMode.version`,
`EvidenceSourceVersion.version`, the population's `case_ids`, qualification rows,
`AssuranceProfile.profile_ref`, and **[REVISED]** `SystemUnderTest.distribution_id`.
Changing any of these changes a registry *key*, so stale evidence disappears by lookup
miss rather than by a validity check somebody might forget to write.

**Dynamically changing** — everything in `ExecutionProfile`, plus
`SystemUnderTest.system_version` and the measured counts on a qualification row.
Mutable without touching any frozen or versioned identity. **[REVISED]**
`system_version` is deliberately in *this* list and `distribution_id` in the one above:
that split is the whole stale-evidence design. Deploying a build does not invalidate
anything; declaring that the build behaves differently does.

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
   requires per-(source × failure-mode × population) sensitivity and FPR. If in practice
   they get filled in with guesses, the derived `n` inherits the guess and the arithmetic
   launders it into false precision.

   *Narrowed — see `docs/agent_reward_bench_findings.md` §9.* Earlier versions of this
   item said "Nobody has these" and that the model "depends entirely on an experiment
   nobody currently runs". Both overreached. AgentRewardBench measured 15 evaluators
   against six human experts' labels on 1,302 real agent trajectories across four
   benchmarks and four agents under test, with per-judgment cost, and this repository now
   holds two pairs of it as real evidence. What survives of the concern is narrower and
   still real: that corpus covers **one** failure mode, its populations are benchmarks
   rather than deployment traffic, it records **no judge latency at all** and no cost for
   self-hosted judges, and every judgment is **single-shot** — so it supplies marginals
   and paired structure but contains no evidence whatever about the run-to-run
   instability that the replication machinery exists to bound. The unrun experiment is
   the repetition study, not the qualification study.

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

**[REVISED again after the measurement pass — how 2 and 5 landed on data.]**

2. *Sharpened, not resolved, and it has got worse.* The objection was that nobody has
   these numbers. The measurement pass grants that and adds a second objection that is
   more serious: even when you *do* have them, they are not sufficient. Two synthetic
   evaluators with nearly identical pooled sensitivity (0.672 and 0.682) and identical
   planner output (`n=7, k=3`) differ completely in what repetition buys — one has zero
   cases repetition cannot fix, the other has seven. Filling the registry with *real*
   measured rates would not have separated them. The deficiency is in the summary
   statistic, not only in the effort required to obtain it.
5. *Confirmed on data, and the diagnosis was slightly wrong.* The prediction named
   correlation between consecutive runs. What dominates in the fixtures is heterogeneity
   *between cases* — averaging the miss probability over cases is not the miss
   probability at the average rate, and that error is present even in data with no
   detectable clustering at all (φ=1.67, warning not fired, model still off by 3× at
   `n=7`). Correlation is real and measurable on fixture B (φ=6.82, 192 runs carrying
   28 runs' worth of information), but it is the second-largest problem, not the first.
   See §2.1.

---

## 10. What is a contribution and what is not

Added after the experimental pass. This section exists so that nothing in this repository
can be written up as new when it is not, and so that the one claim that might be new is
stated narrowly enough to be falsified.

### 10.1 Established. Not ours, not novel, not to be renamed

Every item below is prior work. Where this repository implements one, it implements it as a
*baseline the candidate must beat*, under a name that says what it is. If a future
document describes any of these as a finding of this project, that document is wrong.

- LLM-as-judge nondeterminism and run-to-run verdict instability.
- Inconsistency across repeated judgments of the same item.
- Self-consistent wrong answers: an evaluator that is confidently and repeatably wrong.
- Item- and case-level heterogeneity in difficulty.
- Correlated evaluator errors, and the loss of effective sample size that follows.
- The inefficiency of fixed-N evaluation.
- Adaptive sampling and sequential early stopping. `EarlyStopMajority` is a
  majority-race stopping rule and nothing more; `ConfidenceStop` is interval-based
  stopping with a stated confidence level.
- Cheap-to-expensive evaluator cascades. `ProbeThenEscalate` is the simplest one.
- Selective escalation to human review.
- Value-of-information and sequential decision theory generally. The planner's
  minimal-replication search is a binomial admissibility check, not a VOI engine, and it
  is not to be described as one.
- Mutation testing of evaluators, and construct-validity testing.
- Uncertainty calibration and interval estimation. The Wilson intervals and the
  Beta-Binomial comparator are textbook.
- **Benchmarking evaluators against human reference labels, with per-judgment cost
  accounting.** Added after the AgentRewardBench pass; it was missing from this list and
  its absence let the gap claim in §9.2 stand wider than the field warranted.
  AgentRewardBench (arXiv:2504.08942) does this for 15 judges on 1,302 expert-annotated
  agent trajectories. ATFD (`Galea-foo/atfd`) additionally implements Wilson and bootstrap
  intervals, DR/FPR/F1, Fleiss' κ, and per-trajectory cost with latency and token counts.
- **Paired significance testing between two evaluators on the same cases.** McNemar's test,
  which ATFD implements. It is the nearest prior art to this repository's paired work and
  the distinction is narrow: McNemar asks whether one source is better, not whether the
  alternate recovers the primary's misses. If a future document describes paired
  evaluator comparison as new, that document is wrong.

### 10.2 The candidate contribution, stated as narrowly as it can be

> Treat deterministic tests, stochastic evaluators, and humans as **failure-mode-specific
> evidence sources**, then allocate verification effort according to assurance policy,
> development intent, empirical qualification, and current economics.

It is a *systems* claim, not a statistical one. The parts that are load-bearing:

1. **Qualification is keyed, not global.** A source's sensitivity and FPR are properties of
   the quadruple `(source version, failure mode, population, behaviour distribution)`, and
   a lookup miss is the invalidation mechanism rather than a staleness heuristic.
2. **Intent gates admissibility rather than weighting a score.** No hand-tuned objective.
3. **Effort is allocated per failure-mode subtype using empirically measured behaviour of
   the evidence source on that subtype**, with slices as the only generalisation handle.
4. **Economics enter only at selection**, never at measurement — so a price change can
   change the plan and can never change the qualification.

What is *not* claimed: that any individual mechanism is new, that the allocation is
optimal, that the binomial model is adequate (§2.1 says it is not), or that the planner's
output has been validated against anything.

### 10.3 What would falsify it

Item 3 is the vulnerable one and it is the only one with an experiment behind it. It fails
if slice-level behaviour of an evidence source does not transfer to cases the calibration
never saw — that is, if there is no reusable subtype signal, only memorised cases. The
held-out fold machinery exists to test exactly that, and
[`real_experiment_protocol.md`](real_experiment_protocol.md) §12 lists the kill criteria
in advance.

The synthetic evidence so far is mixed and is recorded in
[`policy_benchmark_findings.md`](policy_benchmark_findings.md). Two results cut against the
claim: a plain interval-stopping rule is the cheapest policy at equal assurance, so
everything the candidate adds is bought rather than saved; and on one fixture a blind
escalation control dominates the candidate policy outright because the assumed alternate
source is simply better than the primary.

Two support it. Where slices carry signal, targeting beats size-matched blind escalation on
errors, escalation count and cost simultaneously. And disagreement-triggered escalation —
the obvious alternative selection rule, requiring no subtype knowledge — is *worse* than
plain early stopping on two of three fixtures, because disagreement selects the noisy cases
repetition already resolves and can never select a confidently-wrong one. That an
escalation policy's whole value sits in its selection rule is the most direct support item
3 has.

Items 1, 2 and 4 are design claims that the implementation either exhibits or does not, and
it does — but exhibiting a design is not evidence that the design helps. Nothing here
measures that, and §9.2 remains the top open problem.

### 10.4 A premise that was never measured, and the instrument that would measure it

Added after building the alternate-source instrument. The finding is about the repository,
not about evaluators.

The paragraph in §10.3 that reads "the assumed alternate source is simply better than the
primary" was resting on **two float literals** — `alternate_sensitivity = 0.95` and
`alternate_false_positive_rate = 0.05` — sitting in the cost model with no study behind
them, consumed at exactly one place in the benchmark's scorer. Every escalation result in
[`policy_benchmark_findings.md`](policy_benchmark_findings.md) is downstream of them. And
[`experiment_red_team.md`](experiment_red_team.md) had already identified measuring those
two numbers as the cheapest open question in the project, on the grounds that it needed only
"one pass of a second evaluator over an already-labelled set".

**Both of those things are false, and the second is the more important error.** There is no
alternate evaluator and there is no labelled set. Every case in `data/` is generated by
`scripts/make_fixtures.py` from a seeded PRNG; the reference labels are the generator's
inputs. So the cheapest open question is not cheap — it is a data-collection project, whose
sizing is governed by an unwelcome piece of arithmetic: **under representative sampling**
the denominator of `P(alternate correct | primary wrong)` is *primary errors*, not cases,
so the more accurate the primary, the more expensive complementarity is to measure *by that
design*. A primary wrong one time in twenty buys sixteen primary errors only at 320 paired
cases.

Both qualifiers were added later, and both are load-bearing; §10.5 says why, and also why
"sixteen errors" is no longer a threshold this repository believes in.

What was built in response is an instrument and not a result:

- `complementarity.py` — the paired-error 2x2, both conditionals with Wilson intervals, the
  joint error rate, both shared-error fractions, verdict disagreement, Pearson phi on the
  error association (`None`, never `0.0`, when a margin is degenerate — because "no data"
  must not render as "reassuringly independent"), and per-slice versions with support flags.
- `complementarity_report.py` — renders all of it and emits **no verdict**. The three
  decision rows (replace / route selectively / reject) are hard-coded to `UNMEASURED`; there
  is no code path that writes anything else into one.
- `CharacterizationRun.alternate_view()` — the alternate is characterized by swapping the
  columns and reusing `characterize()` and `artifact_document()` wholesale, so the alternate
  inherits the fail-closed identity semantics of §10.2 item 1 rather than getting a second
  set of conventions that would drift.
- `AlternateCharacteristics` — unconstructible into a usable state unless it names a
  qualification artifact *or* records an explicit `assumed_because`. The refusal fires at
  point of use, so a primary-only benchmark needs no alternate evidence at all, and the
  published benchmark table now requires `--assume-alternate-rates 0.95 0.05` to reproduce.

Validated only on `data/SYNTHETIC_paired_runs.yaml`, which carries a structural
`synthetic: true` key. An artifact derived from it can be written — that write is how the
machinery gets exercised — but `qualification_from_document` refuses to load it, because a
qualification artifact is a planner input and there is nothing behind this one. **A
disclosed asymmetry:** the four pre-existing fixtures are equally synthetic but declare it
only in prose, because adding the structural key would retroactively break the artifacts and
scenario loads behind the published results. The hard refusal is therefore scoped to the new
fixture, and the gap is recorded here rather than closed silently.

[`alternate_source_collection_protocol.md`](alternate_source_collection_protocol.md)
specifies the input. Until it is satisfied, the replacement / complement / reject question
has no answer, and the escalation half of the design in §10.2 rests on an assumption that
now has to announce itself.

#### Repetition versus escalation: where the comparison actually stands

Stated explicitly because several documents in this repository drifted into treating it as
resolved, and the drift was always in the same direction — evidence about what repetition
*cannot* do being spent as evidence for what escalation *can*. The defensible position, in
five parts:

1. **Repetition policies have been measured under this repository's current assumptions.**
   Fixed-N, majority-race, interval stopping and their budgets were replayed against
   recorded observations on held-out folds. That repetition stops paying after roughly six
   observations, and cannot reach a case the judge is confidently wrong about, is a result
   about those fixtures and that cost model.
2. **Escalation is not measured, and is not even *decisionable*, except against a
   predeclared break-even recovery `r*`.** Every escalation figure in
   [`policy_benchmark_findings.md`](policy_benchmark_findings.md) is downstream of an
   alternate whose accuracy was declared at 0.95/0.05. Replacing that guess with a
   measurement would make the recovery rate knowable; it would still not make escalation
   *worth it*, because worth is a comparison against `r*`, and `r*` is policy.
3. **Population-level complementarity requires a representative paired corpus.** Prevalence,
   both marginals, the production disagreement rate, phi, and `P(alternate wrong | primary
   right)` — the term that measures what escalation breaks — are estimable from nothing
   else.
4. **An enriched corpus of confirmed primary failures supports an inexpensive rejection
   screen and nothing more.** It cannot estimate unconditional disagreement, phi, population
   recovery, or any routing economics; on it, the disagreement rate is identically the
   recovery rate, and phi is not invariant to the sampling that produced it. A negative
   screen kills the routing branch cheaply. A positive screen licenses commissioning the
   representative study and authorises no adoption.
5. **No universal sample size, sufficiency floor, or economic conclusion is justified by
   anything in this repository.** The sample size is a function of the gap between an
   observed recovery and a declared `r*`, and ranges over two orders of magnitude within
   plausible inputs.

So the comparison is asymmetric rather than settled: one arm has been measured under stated
assumptions, and the other has been *priced* under them. Those are different verbs, and §10.5
is the record of what happened the last time this repository let one stand in for the other.

### 10.5 An economic threshold that spent six weeks dressed as a statistical one

Added after [`alternate_corpus_red_team.md`](alternate_corpus_red_team.md), which set out to
evaluate a cheaper two-corpus collection design and found a defect in the instrument on the
way past.

The instrument shipped with `MIN_ERRORS_FOR_CONDITIONAL = 16`, below which a conditional was
marked unsupported and `characterize-alternate` exited non-zero. 16 was presented as derived
rather than chosen, and it was: it is the denominator at which a Wilson interval around an
optimistic observed recovery of 0.75 first clears **0.5**.

The arithmetic was right and the premise was not. **0.5 had no derivation anywhere in the
repository.** It encodes "the alternate is right more often than not on the primary's
mistakes" — a sentence that sounds like a standard and contains no economics. The quantity
that decides whether escalation is worth doing is the break-even recovery `r*`, fixed by the
consequence of the recovered failure, its prevalence, the price of an alternate invocation
and the cost of the alternate's own false alarms; it can land anywhere in [0, 1], and for a
cheap alternate guarding an expensive failure it sits well below 0.5.

That matters because the sample size is a function of the *gap*, and a steep one. An
observed recovery of 0.60 is decisive on **3** primary errors against an `r*` of 0.10 and
needs **91** against 0.50. A thirtyfold swing driven entirely by an economic input is not
something a constant can stand in for, so 16 could not have been a sufficiency criterion in
the first place.

This is the more instructive kind of error for a repository that spends as much effort as
this one on separating measurement from policy. The number was not wrong; the **register**
was wrong. An assertion about value was printed in the typography of a statistical
convention, in a module whose entire purpose is to refuse to do that — the same module that
prints `UNMEASURED` in every decision cell, and that had just finished deleting two
unsourced float literals for the identical offence (§10.4). `--max-error` had been carrying
the correct pattern the whole time: a policy input, labelled as one wherever it appears,
never inferred from the data it is applied to.

What changed:

- `Sufficiency` — an enum with no `SUPPORTED` member, because support is not a property of a
  sample size. `UNDECLARED` is distinct from `INCONCLUSIVE`: the first is a missing input,
  the second is a finding.
- `Conditional.against(threshold)` — reports which side of a *declared* line the interval
  falls on, and returns `UNDECLARED` rather than substituting a default when no line exists.
- `errors_to_decide(recovery, threshold)` — the sizing function that replaces the constant,
  returning `None` when the two are equal, since an interval cannot exclude the point it is
  centred on at any sample size. "No such study" is a more useful answer than a large number.
- `--break-even-recovery`, with no default, and an exit code that stays non-zero for a study
  that measured something but was never told what would count as success.
- `POINT_ESTIMATE_FLOOR = 16` — all that survives, as a presentation warning that the
  interval is too wide to summarise by its midpoint. It carries no verdict: a thin
  denominator can decide a question posed against a distant `r*`, and a fat one can fail to
  decide one posed against a near `r*`.

The red-team's other three findings are corrections to prose rather than to code, and are
recorded in §10 of the collection protocol. The two-corpus design itself was found sound and
not applicable: it saves alternate observations rather than labels, and labels are the
resource this project has none of.
