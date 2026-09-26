# Measurement review

Written before any behaviour change, as an inspection of what the planner's empirical
inputs currently are and what they actually support. Nothing in this document is a
proposal; it records the state of the repository at commit `80d8889`.

The question this pass has to answer is not "does the planner work". It is:

> Can evaluator properties be measured with enough stability that the planner can make
> meaningful decisions from them?

## 1. Where measured quantities enter the planner

Exactly two numbers cross the boundary from measurement into decision:
`QualificationEvidence.sensitivity` and `QualificationEvidence.false_positive_rate`.
They are read in two places and nowhere else:

| site | use |
|---|---|
| `candidates.py:83-84` | `minimal_procedure(...)` seeds the replication ladder with the smallest viable `n` |
| `planner.py:88-89` | `procedure_for(...)` fixes `k` and the two error probabilities at the candidate's `n` |

Both are bare floats. Neither call site knows how many observations produced them.

`QualificationEvidence.observation_count` exists but is load-bearing in only one place —
`constraints.py:161`, a hard floor against `profile.minimum_observation_count` — plus a
display line in `rationale.py:173`. **It never widens a bound, never shifts `n`, and never
changes which plan wins.** A study of 10 observations and a study of 10,000 produce
identical plans as long as both clear the floor.

## 2. The replication math, precisely

`statistics.py` is the only module with real content, and its model is explicit:

```
P(miss)        = P(Binomial(n, sensitivity)          <  k)
P(false alarm) = P(Binomial(n, false_positive_rate) >= k)
```

`minimal_procedure` walks `n = 1..64`, and at each `n` walks `k = 1..n`, returning the
first `(n, k)` where both probabilities fall at or below `maximum_error_requirement`.

This carries four assumptions, none of which is currently checked or checkable:

1. **The two rates are known exactly.** They are point estimates presented as parameters.
2. **Repeated evaluations of the same case are independent Bernoulli trials.** Nothing in
   the schema can express a case the judge is consistently wrong about. Under this model,
   enough repetitions rescue any `sensitivity > 0.5`.
3. **The rates are homogeneous across cases.** A single `sensitivity` is applied to every
   member of the population. Two evaluators with identical pooled sensitivity but
   different per-case structure are indistinguishable to the planner.
4. **The rates measured on the qualification study still hold now.** Section 4.

Assumption 2 is the one that makes the arithmetic work at all, and it is the one the
schema has no vocabulary to falsify.

## 3. What Scenario A's headline numbers actually rest on

`scenarios/voice_early.yaml`, `transcript_judge@v7 x VFD-TURNTAKING@v4 x scenario_corpus`:

```yaml
sensitivity: 0.70
false_positive_rate: 0.10
observation_count: 240
```

Those three lines are the entire empirical basis for the README's `n=7, k=3, 4.7 h,
$8.75/day`. The `240` is an aggregate with no recorded TP/FN/FP/TN split, so the study
that produced it cannot be reconstructed, re-analysed, or disagreed with.

**Reconstructing a split consistent with the stated aggregate** (120 positive cases with
84 detected; 120 negative cases with 12 false alarms) and taking 95% Wilson intervals:

| quantity | point | 95% interval |
|---|---:|---|
| sensitivity | 0.700 | 0.613 – 0.775 |
| false-positive rate | 0.100 | 0.058 – 0.167 |

Feeding the interval corners back through `minimal_procedure` at the gate profile's
`maximum_error_requirement = 0.05`:

| sensitivity | FPR | n | k |
|---:|---:|---:|---:|
| 0.775 | 0.058 | **4** | 2 |
| 0.700 | 0.100 | **7** | 3 |
| 0.613 | 0.167 | **12** | 5 |

**The published answer `n=7` sits inside a 4-to-12 range that the stated sample size does
not resolve** — a 3x spread in wall clock and cost, entirely within sampling noise of the
measurement the planner treats as exact. And 240 observations is a *generous* study. This
is the false precision the current pass exists to confront, and it is present at the
repository's most-cited number.

## 4. The qualification key is silent about the system under test

```python
QualificationKey(source_version, failure_mode, population_id)
```

Lookup is exact — `registry.py:qualification_for` does a plain `dict.get`, no inheritance,
no defaults, no fallback. That is deliberate and it is the mechanism by which an evaluator
version bump orphans its prior evidence (`test_separation.py` Q8).

What the key cannot express: **the state of the system being evaluated when the
measurement was taken.** A sensitivity of 0.70 is a property of the pair
(evaluator, system-under-test), not of the evaluator alone — `domain.py:195` already
concedes this in a comment ("measured end-to-end over (system under test x evaluator);
v0 cannot separate the two"). But the key has no slot for the second half of that pair.

Consequence: ship a materially different voice model, and every qualification row remains
a valid `dict` hit. The planner reports the same `n=7` with the same confident rationale
line, citing a study run against a system that no longer exists. There is no constraint
that can fire, because from the registry's point of view nothing changed.

The failure is silent, which is the worst available failure mode for a component whose
entire claim is that its inputs are auditable.

## 5. The policy inputs were chosen after seeing the output

`voice_early.yaml` declares `maximum_error_requirement: 0.35` for the screen profile and
`0.05` for the gate profile. These were selected during the first implementation pass
because they produced `n=1` and `n=7` respectively — numbers that matched a real team's
lived 2-minute / 40-minute / 5-hour hierarchy.

That is legitimate as *fixture construction* and illegitimate as *evidence*. The scenario
demonstrates that the planner responds coherently to a policy input; it does not
demonstrate that 0.05 is anyone's actual risk appetite. The distinction the repository
needs to keep visible:

```
Policy:      acceptable residual error        <- supplied by an organisation, never derived
Measurement: what the evaluator can do, with uncertainty   <- estimated, and estimated badly
Planner:     cheapest admissible plan under those two
```

The planner respects this separation in code. The *fixtures* currently blur it, and the
README's worked example inherits the blur. It should be stated in the scenario file rather
than left for a reader to discover.

## 6. Summary of what is wrong, in priority order

1. **Point estimates presented as parameters.** No sample counts, no intervals, and the
   one field that records study size cannot influence a plan. Section 3 shows the
   resulting `n` is unidentified across a 3x range at the repo's own headline scenario.
2. **The qualification key omits system-under-test identity.** Stale evidence stays valid
   silently. Section 4.
3. **The i.i.d. Bernoulli assumption is unfalsifiable by construction.** The schema stores
   aggregates, so a judge that is systematically wrong on a subset of cases is
   indistinguishable from one that is uniformly noisy — and the planner will promise the
   first one that repetition fixes it. Nothing in the repository can currently detect this.
4. **Fixture epsilon values are back-derived and not labelled as such.** Section 5.

Items 1 and 2 are schema corrections. Item 3 is not a planner problem at all — it needs
per-case data the repository has never held, which is what the characterization experiment
is for. Item 4 is documentation.
