# Measurement red-team

Written after the changes, as an attempt to kill the premise rather than to defend it.
`docs/measurement_review.md` is the before; this is the after. It answers ten questions
in order and does not soften any of them.

The one-line summary: **the schema corrections landed and are sound; the central
empirical claim did not survive.** Sensitivity and false-positive rate are not an
adequate summary of a stochastic judge, and the project has now produced the evidence
against itself.

---

## 1. Are sensitivity and FPR meaningful enough to drive planning, or is per-case heterogeneity dominant?

**Heterogeneity dominates. This is the headline result and it is not close.**

`data/judge_runs_noisy.yaml` and `data/judge_runs_systematic.yaml` were built to have
nearly the same pooled sensitivity from opposite structures. They do, and the planner
gives them the same answer:

| | A `noisy` | B `systematic` |
|---|---:|---:|
| pooled sensitivity | 0.672 | 0.682 |
| pooled FPR | 0.087 | 0.096 |
| **planner output** | **n=7, k=3** | **n=7, k=3** |
| cases repetition cannot fix | 0 | 7 of 24 positives |
| empirical P(miss) at n=7 | 0.142, falling | 0.289, flat |

A plan built on B's numbers will miss roughly 29% of real failures no matter how many
replications it buys, and will report that it misses 3.7%. The two inputs the planner
consumes cannot see the difference, and no amount of care in *measuring* them would
help — the deficiency is in the statistic, not in the estimate of it.

The sharper version, from `test_the_illustrative_contrast_is_separated`: take ten
positive cases, sensitivity exactly 0.5 both ways. Five always-flag plus five
never-flag versus ten cases that flag on a coin toss. Identical to the planner. In the
first, five cases are permanently undetectable; in the second, every case is fixed by
n=12. Same input, opposite truth.

A caveat that cuts the other way: these are constructed adversaries. Nobody has shown
that a *real* judge is shaped like B rather than like A. What has been shown is that
the planner has no way to find out, and that the failure is silent when it happens.

## 2. Does repeated evaluation buy information, or mostly repeat the same mistake?

Both, and which one depends on a property the planner does not currently have access to.

Per-case verdicts across the two eight-run fixtures:

| | A | B |
|---|---:|---:|
| resolved by one run | 19 | 29 |
| helped by repetition | 31 | 14 |
| repetition cannot fix | 0 | 7 |

On A, repetition is doing exactly what the model says. On B it is buying almost
nothing: the empirical miss rate moves from 0.318 at n=1 to 0.287 at n=12. Twelve runs
purchase a 3-point improvement, for twelve times the money.

The trap worth flagging: **B agrees with itself more than A does.** Mean same-case
agreement is 0.896 for B and 0.732 for A. Being reliably wrong is a form of
reliability, and any dashboard reporting judge repeatability without correctness
alongside it will rank B as the better judge. `render_characterization` therefore
prints "consistently and confidently wrong" as a separate list from the disagreement
ranking, because those cases have a disagreement rate of exactly zero and are invisible
in any ordering by noise.

## 3. How wrong is the current independence assumption?

Badly wrong on B, mildly wrong on A — and **that framing is itself the mistake I made,
which is the more useful finding.**

The dispersion statistic behaved as designed: φ=6.82 on B's positives (ICC 0.83; 192
repetitions carrying about 28 runs' worth of information), φ=1.67 on A's, warning fired
on B only, exit code 1 on B only. A constructed homogeneous fixture in the test suite
lands near φ=1 and comes out clean, so the diagnostic discriminates rather than always
crying wolf.

But fixture A — the deliberate control, φ below threshold, warning not fired — **still
fails the replication analysis.** The model says P(miss)=0.042 at n=7; the per-case
average is 0.142; no n up to 12 reaches the 0.05 target the model claims n=7 already
met. The cause is not clustering. It is that the mean of P(miss | case) is not
P(miss | mean rate), a Jensen-type error present whenever per-case rates vary at all,
even with perfect within-case independence.

So: φ measures correlation *within* a case. The dominant error is variation *between*
cases. These are different defects, φ only sees the second-largest one, and I built the
diagnostic for the wrong quantity first. The model-versus-empirical curve is what
actually bites, and it is the thing to keep if only one survives.

## 4. Is a single replication count per failure mode defensible?

**No, and the reason is stronger than "it is imprecise".**

A single `n` per failure mode is the right shape only if cases are exchangeable draws
from one Bernoulli. Section 1 shows they are not. Concretely, on fixture B the plan
`n=7` is simultaneously:

- wasteful for 29 cases that one run already settles;
- correct for 14 cases;
- pure expenditure for 7 cases that no n will ever settle.

Counting runs rather than cases: 29 cases waste six of their seven runs and 7 waste all
seven, so about 64% of the money buys nothing. A per-failure-mode `n` cannot express any
of that.

The honest qualification: **an adaptive per-case sampler is not obviously the fix
either**, and this pass deliberately did not build one. Adapting per case requires
knowing each case's rate, which requires the per-case study the adaptive sampler was
supposed to make unnecessary. The cheap win available today is not adaptivity — it is
*triage*: identify the cases repetition cannot fix, remove them from the population or
fix the rubric, and then plan a single `n` over what remains. That keeps the planner's
shape and fixes the thing that actually costs money.

## 5. Does system/distribution identity belong in the qualification key, or did the implementation reveal a better abstraction?

It belongs, and the implementation sharpened *which* identity rather than replacing it.

The naive move — key on `system_version` — was rejected before it was written, and
correctly. It orphans every qualification row on every deploy, which makes the registry
useless within a week and guarantees people route around it. What is in the key is a
declared `distribution_id`: a human assertion that the system's behaviour has or has
not materially moved, carrying the same epistemic status as
`maximum_error_requirement`. A rebuild that changes nothing behavioural keeps every
row; declaring a move invalidates them all at once.

Three things I would argue are genuinely right about this:

1. It is a *declaration*, so it cannot be silently wrong in the way an inferred hash
   would be silently right. Someone is accountable for the claim.
2. The failure is diagnosed, not merely absent. `qualification_stale` names the
   distributions the evidence *was* measured against, so the reader sees "measured
   against r3, you are on r4" instead of "no evidence".
3. It is one field. No lineage graph, no compatibility matrix, no partial matching.

And one thing that is unresolved: **nothing enforces that `distribution_id` is updated
honestly.** A team under deadline pressure that does not want to requalify simply does
not bump it, and the planner cannot tell. The mechanism converts a silent technical
failure into a visible organisational one, which is an improvement, but it is not a
guarantee and should not be described as one.

## 6. Are the intervals wide enough that the current planner's exact n values are false precision?

**Yes, at the repository's most-cited number.**

Scenario A's judge is 84/120 and 12/120. Wilson 95%: sensitivity [0.613, 0.775], FPR
[0.058, 0.167]. Pushing the corners back through `minimal_procedure` at ε=0.05:

| sensitivity | FPR | n | k |
|---:|---:|---:|---:|
| 0.775 | 0.058 | 4 | 2 |
| 0.700 | 0.100 | **7** | 3 |
| 0.613 | 0.167 | 12 | 5 |

A 3× spread in wall clock and cost, entirely inside sampling noise, on a 240-observation
study that is *generous* by any realistic standard. The README quotes `n=7, 4.7 h,
$8.75/day` to three significant figures.

Fixture C is the same point made worse: sensitivity 0.900 on twenty cases with one run
each, interval [0.596, 0.982]. It has the best point estimate of the three fixtures and
tells you nothing whatsoever.

The `estimator` policy makes this actionable without forcing it, and its consequences
are not all comfortable:

| scenario | point | conservative |
|---|---|---|
| A / nightly | n=7, $8.75/day | n=12, $15.00/day |
| B / verify (oracle, 15 for 15) | n=1, $0 | **no admissible plan** |
| C / production_guard (n=400) | n=3, $740.48/day | n=3, $740.48/day |

Row B deserves attention. A deterministic oracle measured fifteen times has sensitivity
lower-bounded at 0.796, and under conservative planning the scenario has no answer at
all. That is either exactly right — fifteen observations really do not establish
certainty — or evidence that a single global estimator policy is too blunt an
instrument for a mechanism whose error model is structurally different. The repository
does not claim to know which, and the default is `point` so nothing was silently
repriced.

## 7. Which uncertainty should the planner model next?

In order, with the second and third deliberately reordered from where I would have put
them before running the fixtures:

1. **Case heterogeneity.** Largest measured effect, present even in clean data, and the
   one that produces silent 3× errors in the direction of overconfidence. Everything
   else is smaller.
2. **Parameter uncertainty.** Already exposed and already optional via `estimator`. The
   remaining work is judgement about when to require it, not machinery.
3. **Evaluator correlation within a case.** Real, measurable, and second-order relative
   to (1). φ and the effective run count are enough to flag it; a random-effects model
   would be precision the data does not support.
4. **SUT stochasticity.** Currently inseparable from evaluator noise by construction
   (the rates are joint). Separating them needs a different experiment — the same case
   replayed against a frozen transcript versus re-executed — and is not worth doing
   until (1) is handled.

## 8. Is this still a planner problem, or has the central challenge shifted to measurement infrastructure?

**It has shifted, and pretending otherwise would be the most dishonest thing in this
document.**

The planner is the easy half and was largely finished after the first pass. It
enumerates, rejects, ranks, and explains itself, and the second pass found no defect in
any of that. Every problem found this pass is upstream of it: the inputs do not exist,
and when constructed they turn out not to carry the information the planner assumes.

The measurement side, by contrast, is barely started. `characterization.py` reads
per-case records and reports on them. It does not collect them, does not version them,
does not connect to the qualification registry, and nothing writes a qualification row
from a characterization run — the two data models sit side by side and a human retypes
the numbers between them. That gap is where the real work is.

The most defensible framing of the project now: it is a **planner that has produced a
precise specification of the measurement system it needs**, which is a genuinely useful
artefact, but it is not the artefact the project set out to build.

## 9. What result would make you recommend stopping?

Three, in ascending order of how likely I think they are:

1. **If real judges look like fixture B rather than fixture A.** If per-case structure
   dominates in practice, then repetition is not the lever and the whole
   `(n, k)` decision procedure — the only module with real content — is answering the
   wrong question. The remedy would be rubric repair and case triage, which is a
   completely different tool. *This is the live risk and it is currently untested.*
2. **If `distribution_id` is not maintained in practice.** The entire staleness
   mechanism rests on a voluntary declaration. If, in a real team over a real quarter,
   nobody bumps it, then the planner confidently cites obsolete evidence and is worse
   than no planner, because it launders staleness through arithmetic.
3. **If nobody will fund the qualification studies.** 240 observations per
   (evaluator × failure mode × population × distribution) is a real cost, the key is
   now *wider* than it was, and the cells multiply. If teams will not pay for it, the
   registry fills with guesses and the planner becomes a machine for making guesses look
   like measurements. Note this risk got worse this pass, not better — a correctness
   fix that increases the cost of being correct.

What would *not* make me stop: the discovery that the binomial model is optimistic.
That is a fixable modelling error and the tooling to detect it now exists.

## 10. What is the single highest-value next experiment?

**Characterize one real judge on one real failure mode, with at least five repetitions
per case and at least forty cases, and check which of the three synthetic fixtures it
resembles.**

Everything in this document is conditional on synthetic data built by someone who knew
what he wanted to find. The fixtures prove the *diagnostics work*; they prove nothing
about the world. One real characterization run answers question 9.1, which is the
question that decides whether the project continues.

Specifically it should report: φ and the effective run count; the
model-versus-empirical replication curve; and the count of cases where repetition
cannot fix the verdict. If that last number is zero, the current planner is roughly
right and the next work is intervals and triage. If it is a fifth of the positives, the
decision procedure needs replacing and this pass will have been the one that found out.

The harness for this exists and takes a YAML file. It requires no changes to accept
real data, and deliberately makes no external calls of its own.

---

## Appendix: changes to the existing 88 tests

Acceptance criterion 10 asks that any intentional change be documented. No test was
deleted, weakened, or had an assertion relaxed. Two files changed mechanically for the
new schema:

| file | change | reason |
|---|---|---|
| `test_transitions.py` | `_qual_key` threads `distribution_id` | the key gained a fourth component |
| `test_transitions.py` | two fixtures rewritten from rates to counts | rates are no longer storable |
| `test_separation.py` | two `QualificationKey` constructions gain `distribution_id` | same |
| `test_separation.py` | Q10's field list gains `("estimator", CONSERVATIVE)` | `AssuranceProfile` gained a ninth field, and Q10 asserts every field changes some outcome |

`test_1_less_noisy_judge_needs_fewer_replications` previously wrote
`sensitivity=0.90, false_positive_rate=0.03` directly. It now writes the study that
would produce those rates (`108/120` and `3/100`). The assertion is unchanged and still
passes; expressing the same claim required stating a sample size, which is the point of
the change.

Test count: 88 → 119. All passing.
