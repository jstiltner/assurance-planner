# assurance-planner

A deterministic function that answers one question:

> Given a specific AI failure mode, what a team is trying to accomplish right now, an
> organisational assurance requirement, and a set of evidence-producing mechanisms with
> *measured* reliability and *known* prices — what is the least-cost admissible way to
> get the evidence?

```
plan : (DevelopmentContext, FailureMode, AssuranceProfile, World) -> PlanningResult
```

No LLM, no network, no clock, no randomness inside the planner. The world it reasons
about is stochastic; the reasoning is not.

```bash
pip install -e .
assurance-plan scenarios/voice_early.yaml --context nightly
```

## What it decides

Nothing in this list may be written into a scenario file. The loader rejects all nine
keys at any depth, and a test tampers with a real scenario to prove it.

| decision | derived from |
|---|---|
| which mechanism | least cost among the admissible |
| which population, and how much of it | goal coverage requirement + `sampling_allowed` |
| run percentage | always paired with its denominator; never a bare number |
| replication count `n` | measured sensitivity/FPR + `maximum_error_requirement` |
| decision threshold `k` | smallest `k` bounding both miss and false-alarm at `n` |
| escalation band | `1..k-1`; empty when `k=1`, so deterministic paths get no hop |
| escalation target | cheapest qualified source that adds *different* evidence and satisfies the same policy |
| cadence | cost per *day*, which is what makes nightly cheaper than per-change |
| sync vs async | whether the intent must gate the change |
| human allocation | `human_confirmation_required`, bounded by measured capacity |

## What it is not

- **Not an assurance authority.** It never decides how much risk is acceptable. That
  arrives as an `AssuranceProfile` and the planner obeys it.
- **Not an optimiser.** It enumerates, rejects, and sorts. No solver, no search
  heuristic, no tuned coefficients. If ranking ever needs a weight to make a scenario
  come out right, the abstraction has failed and that should be reported, not patched.
- **Not an executor.** It emits a plan. It does not run evaluations, call models, or
  orchestrate a prove-red cycle.
- **Not a governance DSL.** `AssuranceProfile` has six structured fields and an opaque
  `profile_ref`. A field only exists if changing it can change which plans are
  admissible — there is a test that flips every one of them and asserts the outcome
  moves, and a second test asserting `profile_ref` changes nothing at all.
- **Not validated.** The qualification numbers in the fixtures are plausible, not
  measured. See `docs/red_team_review.md`.

## The three scenarios

**A — `scenarios/voice_early.yaml`.** Early voice-agent development. One world, four
contexts, and the claim under test is that mechanism, scope, replications and cadence
are four separate dimensions rather than one:

| context | mechanism | scope | n | cadence | cost |
|---|---|---|---:|---|---:|
| inner_loop | deterministic simulator | 1 case | 1 | per change | 2.0 min, $0 |
| checkpoint | judge | 20 cases | 1 | per checkpoint | 40 min, $1.25 |
| nightly | judge | 20 cases | **7** | nightly, async | 4.7 h, $8.75 |
| discovery | judge | 20 cases | 1 | nightly, async | $1.25 |

The 2 min / 40 min / ~5 h / ~$10 hierarchy the real team lived is reproduced as
`cases × replications × 120s`, and none of those figures appears anywhere in the repo.
`discovery` is the context worth staring at: it buys the **expensive** judge over the
**free** simulator, because only an open-ended source can surface a failure its
criterion did not anticipate.

**B — `scenarios/duplex_silence.yaml`.** A known, machine-verifiable full-duplex
silence defect. The planner selects the deterministic oracle at n=1 for $0. The two
LLM judges are *admissible* — qualified, available, twelve prove-red observations each
— and lose on price:

```
frontier_judge   -> admissible but dominated on cost: $12.6000/window vs $0.0000/window
transcript_judge -> admissible but dominated on cost:  $3.7500/window vs $0.0000/window
```

That distinction is the whole point. No rule anywhere says "do not use a judge." The
oracle already reports `P(miss)=0`, so extra sensitivity buys no assurance and the
comparison collapses to price. A second call with `assess_blast_radius` buys the broad
20-case suite once at checkpoint cadence, not on every debugging iteration.

**C — `scenarios/clinical_factual.yaml`.** A hypothetical high-consequence factual
mismatch. Two contexts share a world, a set of mechanisms, a set of qualification
measurements and a set of prices. **Only the `AssuranceProfile` differs**, and the
answer moves six orders of magnitude:

| | strict | routine |
|---|---:|---:|
| cost | $740.48/day | $0.0004/day |
| human minutes | 480/day | 0 |
| replications | 3 | 1 |

`sampling_allowed=false` rejects every sampled plan; `human_confirmation_required=true`
rejects every fully automated one; `authoritative_source_required=true` rejects the
judge and also binds the *escalation* target, so an ambiguous case cannot be routed
around the constraint that selected the primary. No clinical vocabulary appears in any
planner module — there is a test that greps for it.

## Changing an input changes the plan

Take Scenario A's nightly release gate and make the judge **less noisy**, changing
nothing else — one measurement in the qualification registry, no price change, no
policy change:

| measured sensitivity | replications | threshold | wall clock | cost/day |
|---:|---:|---:|---:|---:|
| 0.70 | 7 | 3 of 7 | 4.7 h | $8.75 |
| 0.80 | 6 | 3 of 6 | 4.0 h | $7.50 |
| 0.90 | 3 | 2 of 3 | 2.0 h | $3.75 |
| 0.95 | 3 | 2 of 3 | 2.0 h | $3.75 |

Nothing in the repo maps sensitivity to a replication count. The planner searches for
the smallest `n` at which some threshold `k` bounds *both* the miss probability and the
false-alarm probability below the profile's `maximum_error_requirement` of 0.05. A
better judge is worth 2.7 hours of nightly wall clock and $5 a day — and the 0.90 → 0.95
row shows the improvement saturating, because at that point `n` is being held up by the
false-alarm side, not the miss side.

An economic input does the same. Repricing the judge with `parallelism=8` drops a
40-minute suite to 5 minutes and makes it admissible inside a 10-minute budget it
previously missed — without touching a single qualification row.

## Reading the code

| file | contents |
|---|---|
| `statistics.py` | the binomial decision procedure. The only module with real content. |
| `domain.py` | typed domain objects, grouped by mutability class |
| `registry.py` | the world; two registries that are never merged |
| `candidates.py` | enumeration. Crosses source × population × fraction × n × cadence × mode |
| `constraints.py` | every rejection rule, staged. All domain content lives here |
| `economics.py` | cost, wall clock, human burden. Never averages a conditional latency |
| `ranking.py` | least cost. Deliberately dumb |
| `planner.py` | enumerate → reject → rank |
| `rationale.py` | why the winner won and why the losers lost |

`docs/architecture.md` was written before the implementation and its wrong predictions
are marked `[REVISED]` rather than corrected. `docs/red_team_review.md` is the
post-implementation attempt to falsify the whole thing; start with its first table.

```bash
python -m pytest        # 88 tests
```
