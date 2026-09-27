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
assurance-plan characterize-evaluator data/judge_runs_systematic.yaml
assurance-plan benchmark-policies data/judge_runs_mixed.yaml
```

The second command is the planner's own falsifier. See
[Are the inputs measurable?](#are-the-inputs-measurable) — the short answer is that on
one of the three shipped fixtures they are not, and the planner cannot tell.

The third asks whether a planner is needed at all. It replays every established
evaluation policy — fixed-N, majority-race early stopping, interval stopping, a
probe-and-escalate cascade — against the same recorded observations under one cost model,
on held-out folds, alongside a blind escalation control sized to match. It prints the
table and **refuses to name a preferred policy**, because choosing inside the Pareto set
requires a price for a missed failure, which is policy rather than measurement.

Results so far, on synthetic fixtures: repetition stops buying anything after six
observations; repetition cannot touch a case the judge is confidently wrong about, and
escalation can; and on one fixture the blind control beats the candidate policy outright.
See [`docs/policy_benchmark_findings.md`](docs/policy_benchmark_findings.md) for all of it
including the parts that argue against continuing,
[`docs/real_experiment_protocol.md`](docs/real_experiment_protocol.md) for the real-data study
and its ten kill criteria written before any real data exists, and
[`docs/experiment_red_team.md`](docs/experiment_red_team.md) for the pass that found the
protocol's original sample size could not test its own central claim.

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
- **Not a governance DSL.** `AssuranceProfile` has eight structured fields and an opaque
  `profile_ref`. A field only exists if changing it can change which plans are
  admissible — there is a test that flips every one of them and asserts the outcome
  moves, and a second test asserting `profile_ref` changes nothing at all.
- **Not validated.** The qualification numbers in the fixtures are plausible, not
  measured, and Scenario A's error requirements were reverse-engineered from the
  replication counts they were meant to produce — stated in the file itself, and
  asserted in a test so it stays stated. See `docs/red_team_review.md`.
- **Not a measurement system.** It consumes sensitivity and false-positive rate. It
  does not produce them, and `characterize-evaluator` exists to argue that consuming
  only those two numbers is the planner's largest remaining assumption.
- **Not novel in its mechanisms.** Judge nondeterminism, adaptive sampling, early
  stopping, judge cascades, selective human escalation and uncertainty calibration are
  all established work, and `docs/architecture.md` §10.1 lists them so that none can be
  quietly renamed as a finding here. The only candidate claim is a systems one — §10.2 —
  and §10.3 says what would falsify it.

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

## Are the inputs measurable?

The planner reduces an evaluator to two numbers. Everything above assumes that
reduction is fair. `characterize-evaluator` exists to test it, and on the shipped
fixtures it does not survive.

**Qualification is now keyed by what it was measured against.** The key is
`evaluator version × failure-mode version × population × behaviour distribution`. The
`distribution_id` is a *declaration* by the system's owner, not something inferred from
a build hash — so a rebuild that changes nothing behavioural keeps every row, and
declaring a move orphans them all at once. A price change still invalidates nothing;
an evaluator version bump still invalidates everything. A miss is diagnosed as
`qualification_stale` rather than a bare absence, so the rationale can name the
distribution the evidence actually came from.

**Rates are no longer storable.** A qualification row carries counts —
`positive_cases`, `true_positives`, `negative_cases`, `false_positives` — and the rate
is derived. A scenario cannot assert a sensitivity its sample size does not support,
because there is nowhere to write one down. Each rate reports a **Wilson score
interval**, chosen over the normal approximation because the latter is zero-width at
p=0 and would let a 30-for-30 oracle claim certainty.

**Conservatism is a policy, not a default.** `AssuranceProfile.estimator` selects
`point` or `conservative` (lower bound on sensitivity, upper bound on FPR). It defaults
to `point`, so nothing was silently repriced. Its bite varies:

| scenario | point | conservative |
|---|---|---|
| A / nightly | n=7, $8.75/day | n=12, $15.00/day |
| B / verify (oracle, 15 for 15) | n=1, $0 | **no admissible plan at all** |
| C / production_guard (n=400) | n=3, $740.48/day | n=3, $740.48/day |

Row B is the uncomfortable one: a deterministic oracle measured 15 times is not exempt
from its own sample size, and under conservative planning the scenario has no answer.
That is either the correct conclusion or evidence the policy is too blunt; the repo
does not claim to know which.

**The two-number summary loses the thing that matters.** Three adversarial fixtures
live in `data/`. A and B were tuned to nearly the same pooled sensitivity from
structurally opposite evaluators:

| | A `judge_runs_noisy` | B `judge_runs_systematic` |
|---|---|---|
| pooled sensitivity | 0.672 | 0.682 |
| **planner's answer** | **n=7, k=3** | **n=7, k=3** |
| mean same-case agreement | 0.732 | **0.896** |
| dispersion φ | 1.67 | 6.82 |
| effective runs (of 192) | 115 | **28** |
| cases repetition cannot fix | 0 | 7 |
| empirical P(miss) at n=7 | 0.142, falling | 0.289, **flat** |

The planner cannot tell them apart. B agrees with itself *more* than A does, because
being reliably wrong is a form of reliability — which is why the report prints
"consistently and confidently wrong" as a separate list from the disagreement ranking.
B fires the independence warning and exits non-zero; A does not.

**But φ is necessary, not sufficient.** Fixture A passes the clustering check and
*still* fails the replication analysis: no n in 1..12 meets the 0.05 target on per-case
rates, while the model claims n=7 suffices. The cause is not clustering. Averaging
P(miss) over heterogeneous per-case rates is not P(miss) at the mean rate, so **case
heterogeneity, not within-case correlation, is the dominant error** — and the
empirical-versus-model curve, not the dispersion statistic, is the diagnostic that
catches it. A constructed homogeneous fixture in the test suite comes out clean on
both, which is the only reason the tooling can be said to discriminate rather than
always cry wolf.

Fixture C is the third failure: sensitivity 0.900 on twenty cases, one run each. It
has the best point estimate of the three and an interval of [0.596, 0.982], which is
to say it has told you nothing.

### Policy, measurement, planner

```
Policy       maximum acceptable residual error   asserted by someone accountable
Measurement  what the evaluator appears capable of, with its uncertainty
Planner      the cheapest admissible plan given exactly those two
```

`--max-error` on `characterize-evaluator` is a policy input and the report labels it
as one. It is never inferred from the data being characterised. Scenario A's `0.35`
and `0.05` were chosen after seeing which values produced n=1 and n=7 — the file says
so, and a test asserts that it keeps saying so.

## Reading the code

| file | contents |
|---|---|
| `statistics.py` | the binomial decision procedure and the Wilson interval |
| `domain.py` | typed domain objects, grouped by mutability class |
| `registry.py` | the world; two registries that are never merged |
| `candidates.py` | enumeration. Crosses source × population × fraction × n × cadence × mode |
| `constraints.py` | every rejection rule, staged. All domain content lives here |
| `economics.py` | cost, wall clock, human burden. Never averages a conditional latency |
| `ranking.py` | least cost. Deliberately dumb |
| `planner.py` | enumerate → reject → rank |
| `rationale.py` | why the winner won and why the losers lost |
| `characterization.py` | the falsifier. Imported by nothing in the planner's decision path |

`docs/architecture.md` was written before the implementation and its wrong predictions
are marked `[REVISED]` rather than corrected. `docs/red_team_review.md` is the
post-implementation attempt to falsify the whole thing; start with its first table.
`docs/measurement_review.md` and `docs/measurement_red_team.md` are the second pass,
before and after, asking whether the quantities the planner optimises are measurable
well enough to deserve optimisation. The short answer is in the second document's first
paragraph and it is not a favourable one.

`scripts/make_fixtures.py` generates `data/`. It lives outside `src/` because the
planner package is asserted to contain no randomness, and because the committed YAML —
not the generator — is the artefact under review.

```bash
python -m pytest        # 119 tests
```
