# Red-team: the two-corpus alternate-source design

Written against [`alternate_source_collection_protocol.md`](alternate_source_collection_protocol.md)
before any alternate-source data exists, to test a specific proposal for making that
protocol cheaper, and to re-examine a conclusion the protocol asserted without deriving.

**The proposal.** Split collection in two.

* **Corpus A — representative.** Sampled from production traffic without reference to any
  outcome. Estimates prevalences, joint error rates, disagreement prevalence, slice
  frequencies, and the cost and latency distributions.
* **Corpus B — failure-enriched.** Confirmed primary failures, selected *without reference
  to the alternate's result*. Estimates `P(alternate correct | primary wrong)`, per-mode
  recovery, and the shared-failure fraction.

**The question.** Can rare-error complementarity be estimated efficiently from a
failure-enriched corpus while prevalence is estimated separately from representative data,
without introducing invalid claims?

**The verdict.** *Valid with limitations, and not applicable here yet.* The mathematics
works. The saving is real but it is not a saving on the resource this project is actually
short of. §11 states the disposition; §§1–10 are the argument; §12 lists four claims made
in earlier documents that this review retracts or narrows.

---

## 1. Metric-by-metric identifiability

Enrichment on primary correctness is a case-control design. Everything downstream turns on
one condition, stated here once and referred to throughout as **ignorability**:

> **S ⊥ E_a | E_p = 1** — inclusion in Corpus B is independent of whether the alternate is
> correct, *within the stratum of primary errors*.

This is much stronger than "the selector was blind to the alternate's output". Blindness
rules out reading the alternate's verdict. It does not rule out selecting on anything
*correlated* with the alternate's verdict: case length, domain, escalation history,
customer severity, or whichever failures happened to be noticed. Ignorability is a claim
about the whole selection mechanism, and §6 argues it is essentially untestable in the
regime where enrichment is worth doing.

Writing `π = P(E_p=1)` for the primary error rate, `β = P(E_a=1 | E_p=1)`, and
`γ = P(E_a=1 | E_p=0)`:

| statistic | A | B | notes |
|---|---|---|---|
| `P(alternate correct \| primary wrong)` — recovery | yes | **yes** | the target. `1 − β`. Estimable from B under ignorability, and the entire case for the design. |
| `primary errors also made by alternate` | yes | **yes** | `β`. One minus recovery on the same denominator; same status. |
| per-mode / per-slice recovery | yes | **yes** | same conditional inside a stratum; see §3 for what goes wrong. |
| primary error rate `π` | **yes** | no | B is `E_p = 1` by construction. Its "error rate" is 1. |
| alternate error rate | yes | no | B estimates only `β`, which is the alternate's error rate *on primary errors*. |
| primary sensitivity / FPR | **yes** | no | marginals require both columns. |
| alternate sensitivity / FPR | **yes** | no | same. This is the pair that H1 turns on, and B cannot speak to it at all. |
| `P(primary correct \| alternate wrong)` | **yes** | no | denominator is alternate errors, which in B are a biased subset. |
| joint error rate `P(both wrong)` | **yes** | reconstructed | `πβ`. Not directly observable in B — B's both-wrong fraction is `β`, not `πβ`. |
| verdict disagreement rate | **yes** | **no, and dangerously so** | see §1.1. |
| error association (Pearson phi) | **yes** | **no, and silently so** | see §1.2. |
| `γ = P(E_a=1 \| E_p=0)` | **yes** | no | the primary-correct column is absent from B entirely. |
| cost / latency distributions | **yes** | no | B's cases are not drawn from the operating distribution; their cost profile is not the production cost profile. |
| slice frequency | **yes** | no | enrichment reweights slices by their error rates. |

Two entries deserve their own headings, because in both cases B produces a *number* that
looks like the statistic asked for.

### 1.1 On Corpus B, the disagreement rate **is** the recovery rate

Every case in B has the primary wrong. With binary verdicts against a shared reference
label, the two sources therefore disagree exactly when the alternate is right. So

> `verdict disagreement on B` = `1 − β` = `recovery on B`

— the same number, reported under a different name, referring to a different thing. The
production disagreement rate is `P(E_p ≠ E_a) = π(1−β) + (1−π)γ`, which on a corpus with
`π ≈ 0.05` is a small number, and on B is by construction a large one. Quoting B's
disagreement rate as "how often the sources disagree" overstates it by roughly `1/π`.

Nothing in the instrument distinguishes these. Both are printed in the same block of
`characterize-alternate`, adjacent, with no annotation tying either to a sampling design.

### 1.2 Phi is not invariant to outcome-dependent sampling

The odds ratio is the standard estimand for case-control designs precisely because it
*is* invariant to differential sampling of the outcome strata. Pearson's phi is not. Phi
is a function of the four cell *proportions*, and enrichment changes them by construction:
oversampling the `E_p = 1` row inflates the two cells in it relative to the other two, and
phi moves accordingly without anything about the underlying association having changed.

So phi computed on B estimates nothing. Phi computed on A ∪ B estimates nothing, and is
worse, because pooling makes the result a function of the *mixing ratio* — an arbitrary
budget decision — rather than of either population.

This is the more dangerous of the two, because phi is the statistic the routing hypothesis
lives or dies on, it has no denominator printed next to it that would look suspicious, and
a reader has no way to tell a phi of +0.22 computed on a representative corpus from a phi
of +0.22 computed on a pooled one.

**Conclusion of §1.** Enrichment buys one column of the 2×2. Roughly half the instrument's
outputs become undefined on B, two of them become actively misleading, and the two that
become misleading are the ones a reader is least equipped to catch.

## 2. Do the corpora recombine?

Yes, exactly, and the identity is short. Three estimands recover the full joint:

```
π = P(E_p = 1)            from A
β = P(E_a = 1 | E_p = 1)  from B
γ = P(E_a = 1 | E_p = 0)  from A
```

giving

```
both wrong          = π · β
primary only wrong  = π · (1 − β)
alternate only wrong = (1 − π) · γ
neither wrong       = (1 − π) · (1 − γ)
```

from which every cell-derived statistic — joint error rate, disagreement, phi, both
conditionals — follows. Note that `γ` comes from **A**, not B: the primary-correct column
is simply absent from B, so recombination is not symmetric. A and B are not two halves of
one table; A is a whole table with a thin row, and B thickens that row.

Three things this does not do:

1. **It does not propagate uncertainty for free.** The products are ratio estimators of
   correlated-in-name-only quantities; intervals on `πβ` must be built from intervals on
   both factors. The instrument computes no such interval today and `Conditional` has no
   representation for a derived product.
2. **It does not survive a violated ignorability assumption**, and the violation is
   invisible in the output. A biased `β` produces a perfectly well-formed table.
3. **It does not licence pooling the case rows.** Recombination is arithmetic on three
   estimates. Concatenating the two corpora into one case list and running the existing
   `paired_errors` over it is a different operation and a wrong one.

### 2.1 Five sources of "enriched" failures, which are not equivalent

The proposal says "confirmed primary failures selected without reference to the alternate's
result". In practice failures arrive by different routes, and the routes have materially
different standing:

| # | source of failures | ignorability | usable as Corpus B? |
|---|---|---|---|
| 1 | **Random sample, fully labelled, errors retained.** Label a representative draw; keep the primary's errors as B, the whole draw as A. | Holds **by construction** — selection depends on `E_p` and nothing else. | Yes, unconditionally. It is the reference case. But see §8: it saves nothing on labels. |
| 2 | **Prove-red misses.** Known-broken targets where the primary stayed GREEN (§7). | Holds *within the prove-red target set*. The set itself is adversarially constructed and is not the production population. | Yes for `β` **restricted to that population**, and it must be reported as such. Not transportable to production `π`. |
| 3 | **Production incidents / escalations / complaints.** | Fails plausibly. A failure is noticed because it was consequential, visible, or complained about — all of which correlate with case properties the alternate is also sensitive to. Severity-weighted, not error-weighted. | Only with the selection mechanism documented and the resulting `β` labelled as conditional on noticing. Treat as a distinct estimand, not as `β`. |
| 4 | **Disagreement mining** — cases where the primary and the alternate already differed. | **Fails by construction.** Selection is a deterministic function of `E_a` inside the primary-error stratum. This is the exact violation of `S ⊥ E_a \| E_p = 1`. | **No.** Recovery estimated this way is 1.0 by construction wherever the reference agrees with the alternate. Unusable for any recovery claim. |
| 5 | **Adversarially authored cases** — hand-written to break the primary. | Not applicable; there is no population and therefore no sampling mechanism to be ignorable with respect to. | Only as a stress corpus. `β` on it is a statement about the author's imagination. |

These must not be pooled with each other either. Four of the five estimate different
things, and only the first estimates the thing the protocol wants.

## 3. Failure-mode stratification

Stratifying B by failure mode is the right instinct and it does not solve the sparse-data
problem; it relocates it.

* Enrichment fixes the *global* conditional's denominator. Per-mode denominators are then
  set by the enrichment plan's per-mode quotas, which is an improvement over the
  representative case only if the quotas are filled — and filling a quota for a rare mode
  requires screening `1/P(mode | error)` times as many failures.
* **Mode assignment is itself a judgment, made after the failure is known**, and there is
  no reference label for it. Two reviewers who disagree about whether a case is
  "retrieval miss" or "instruction-following" move a case between denominators. That
  disagreement rate must be measured the way §3 of the protocol requires for the primary
  labels, and it usually is not.
* **Root-cause deduplication is mandatory and is a source of bias in both directions.**
  Twenty cases from one broken template are one failure observed twenty times; counting
  them as twenty makes the interval around `β` about `1/√20` too narrow and weights
  recovery toward whatever that one template does. Deduplicating aggressively, on the other
  hand, can delete exactly the failure mode that dominates production volume. There is no
  neutral choice; there is only a recorded one. Record the dedup key and report both counts.
* Balanced quotas across modes make **per-mode** estimates comparable and make the
  **pooled** `β` an estimate of nothing — it becomes a weighted average with weights set by
  the quota rather than by production. If quotas are balanced, the pooled figure must be
  reweighted by A's mode frequencies or not reported.

Net: stratification converts one sparse denominator into *k* sparse denominators with a
reweighting step between them and the answer. That is a real gain for diagnosis and a
modest one for sizing.

## 4. The 0.50 threshold, and the 16-error floor — retracted

The protocol required 16 primary errors before quoting a conditional, and derived 16 as the
denominator at which a Wilson interval around an optimistic observed 0.75 clears **0.5**
(12/16 → [0.505, 0.898]; 9/12 → [0.468, 0.911], which does not).

The arithmetic is right. The premise is not.

**0.5 was never justified and is not a statistical quantity.** It encodes "the alternate is
right more often than not on the primary's mistakes" — a rhetorically satisfying sentence
with no economic content. The threshold that matters is the **break-even recovery `r*`**:
the recovery rate at which escalating to the alternate stops costing more than it saves.
It is set by the consequence of the recovered failure, the prevalence of the failure, the
price and latency of an alternate invocation, and the cost of the alternate's own false
alarms. It can land anywhere in [0, 1], and for a cheap alternate guarding an expensive
failure it is routinely far *below* 0.5.

The sample size needed is a function of the **gap** `|r − r*|`, and a steep one:

| observed recovery | `r*` | primary errors to decide |
|---|---|---|
| 0.60 | 0.10 | 3 |
| 0.60 | 0.20 | 3 |
| 0.60 | 0.30 | 12 |
| 0.60 | 0.50 | 91 |
| 0.75 | 0.70 | 306 |
| 0.50 | 0.50 | no finite study |

A thirtyfold swing, driven entirely by an economic input. No constant can stand in for
that, so **16 cannot be a sufficiency criterion** — and a fixed floor is not merely
imprecise, it is the wrong *kind* of object. It smuggles an economic assertion into a
document that presents it as a statistical convention, which is the harder error to notice
because the register is wrong rather than the arithmetic.

**What replaces it:** nothing, at the level of a constant. `r*` is declared by the caller,
exactly as `--max-error` already is, and the study reports which side of the declared line
its interval falls on. A study with no declared `r*` has been asked no question and reports
that, rather than substituting a default.

**What 16 is still good for:** a presentation warning. Below 16 the interval is wider than
0.39 even at an optimistic 0.75, so a point estimate quoted without its interval will be
read as more precise than it is. That is a statement about typography, carries no verdict,
and a thin denominator can still be decisive against a distant `r*` while a fat one can
fail against a near one.

**A cheaper decision than adoption.** Because sizing depends on the gap, *rejection is
usually far cheaper to establish than adoption*: if the true recovery is near zero, a
declared `r*` of 0.20 is cleared from below on a handful of errors. This is the one place
the enrichment idea earns its keep, and §10 builds on it.

## 5. Which inputs the expected-value framing actually needs

Escalation is worth it when the expected saving exceeds the expected cost. Every term:

| term | where it must come from |
|---|---|
| prevalence of the failure mode in production, `π` and its per-mode split | **Representative data (A) only.** Enrichment destroys it by construction. |
| recovery `1 − β`, overall and per mode | Representative **or** enriched (B), under §1's condition. |
| `γ`, the alternate's error rate where the primary is right — i.e. what escalation *breaks* | **Representative (A) only.** B has no primary-correct column. Routinely forgotten; it is the term that makes an over-eager alternate a net loss. |
| alternate invocation cost, human review cost | **Telemetry / billing.** Not inferable from either corpus; the protocol's §5 fields. |
| alternate latency, including human turnaround | **Telemetry, wall clock.** |
| how often a routing policy would actually fire | **Representative (A).** A function of the production disagreement rate, which B overstates by ~`1/π` (§1.1). |
| cost of a missed failure reaching production | **Business input.** Never measured by this project. Must be declared. |
| cost of a false escalation | **Business input.** Declared. |
| `r*` itself | **Derived from the two business inputs and the price and prevalence terms — declared as policy, not computed by the instrument.** |

Three observations. First, the majority of the terms come from A or from telemetry; B
supplies exactly one. Second, `γ` is the term most likely to be skipped, and skipping it
makes every escalation look free. Third, `r*` depends on `π`, so a design that estimates
`β` precisely while leaving `π` on three observations has precision in the numerator and
noise in the threshold it is being compared against.

## 6. Safeguards against selection bias — and their power

Required if B is ever collected:

1. **Pre-register the selection rule** before looking at any alternate output, in enough
   detail that a third party could re-execute it and arrive at the same case set.
2. **Record the sampling frame and the screening ratio**: how many cases were examined to
   find each failure, and by what mechanism.
3. **Record per-case provenance**: which of §2.1's five routes this case arrived by. Cases
   from different routes may not share a denominator.
4. **The selector must never see alternate output**, and must not see any *derivative* of
   it — including which cases were previously escalated.
5. **Freeze reference labels before the alternate runs**, per protocol §3. Enrichment makes
   this worse, not better: a labeller who knows a case was selected *because it was a
   failure* is anchored.
6. **Root-cause dedup keys recorded**, with both raw and deduplicated counts (§3).
7. **Cases used to screen or gate must be discarded before estimation**, or the conditioning
   reported. A case admitted to B because it passed a "is this really a failure?" check is
   conditioned on that check.
8. **Report `β` from B beside `β` from A** whenever A has any errors at all.

**Safeguard 8 is the only actual diagnostic, and it has almost no power.** Comparing B's
recovery to A's is the one way to detect a violated ignorability assumption empirically —
and A has few primary errors *by construction*, since that scarcity is the entire reason
for wanting B. The check's power is proportional to the thing enrichment exists to avoid
buying. In the regime where the design is attractive, it cannot be validated.

That is the second bounding limitation: not "this assumption might be wrong" but "this
assumption cannot be checked where it matters".

## 7. What prove-red contributes, and what it cannot

`prove_red_runs` counts RED observations on a known-broken build. A *successful* prove-red
is therefore a case where **the primary succeeded** — it is evidence that the guard detects
the defect, and it is not failure-corpus material.

The useful artifact is the **miss**: a prove-red exercise where the evaluator stayed GREEN
on a target known to be broken. That is a confirmed primary failure with unusually good
provenance — the ground truth is not a labeller's judgment but the construction of the
target, and the failure was found by a mechanism that never saw the alternate.

What it contributes:

* **Confirmed primary errors at near-zero labelling cost**, with the reference label
  established by construction rather than adjudication.
* **Route 2 in §2.1** — ignorable *within the prove-red target population*.
* Cheap **rejection** evidence in particular: if the alternate also stays GREEN on
  deliberately broken targets, that is decisive against H2 at a small sample size.

What it cannot do:

* **It is not representative of anything.** Prove-red targets are authored to be broken in
  specific ways. `β` measured on them is `β` on that construction, and transporting it to
  production requires an untestable assumption about the two populations matching.
* **It cannot estimate `π`.** There is no denominator — the rate of prove-red misses is a
  property of the test suite's difficulty.
* **It cannot estimate `γ`** or either marginal, for the §1 reason.
* **It is subject to the same author-imagination bound as route 5** insofar as targets are
  hand-constructed.
* **Selection on the failure being noticed is absent here**, which is its main advantage
  over route 3 and worth stating explicitly.

**And it is currently hypothetical.** No prove-red exercise is executed in this repository.
`prove_red_runs` is a scalar typed into a scenario file and consumed by one constraint;
there are no per-case records, no target identifiers, and no attempt count — so a miss is
not merely discarded, it is not a representable event. `prove_red_runs: 3` may be 3 of 3 or
3 of 20. §9.5 of the protocol specifies what a harness would have to emit; the two blocking
changes both alter schemas that other code reads, and neither is made here.

## 8. How collection burden scales — and what the saving is actually on

Two relationships govern everything, and neither depends on a constant.

**(a) Errors needed is a function of the gap to `r*`** (§4), not of the sample size.

**(b) Representative cases needed is `errors / π`.** At `π = 0.05`, sixteen errors costs
320 labelled cases; at `π = 0.20` it costs 80. Enrichment breaks this dependence: B buys
`k` errors at roughly `k` cases, a factor-of-`1/π` reduction in *cases carrying an
alternate observation*.

**But the cost that binds is labelling, not alternate invocation.** To find a confirmed
primary failure you must know the reference label, which means you must label. Under route
1 — the only unconditionally valid route — you label a representative draw and keep its
errors. You have then paid the full representative labelling cost and produced Corpus A as
a by-product. **Design B saves nothing on labels in that case.** Its saving is on alternate
observations only, which matters when the alternate is a slow or expensive human panel and
labelling is cheap, and does not matter when labelling is the constraint.

Routes 2 and 3 do dodge the labelling cost, by obtaining failures from a mechanism that
establishes truth some other way — and they pay for it with a non-transportable population
(§7) or a broken ignorability assumption (§2.1).

**A third relationship, easy to miss.** For a proportion, relative standard error `s`
requires about `k ≈ 1/s²` events, independent of the underlying rate. So **16 errors is
exactly 25 % relative SE on `π`** — which means a representative corpus sized to deliver 16
errors for the conditional *already* delivers prevalence at that precision, at no extra
cost. And enrichment cannot improve prevalence at all.

Worked consequence, because it is the number that decides this: suppose recovery is
enriched from 16 errors to 100 (relative SE 0.11 → 0.045) while `π` still rests on the 3
errors a small representative corpus produced (relative SE 0.58). The expected-value
calculation needs the **product** `πβ`. Its relative SE moves from 0.61 to 0.58. Enriching
recovery sixfold bought a 5 % improvement in the quantity the decision is made on, because
the error is dominated by the factor enrichment cannot touch.

**This is the third bounding limitation, and the decisive one for this project.** Precision
on `β` is only worth buying once `π` is solid, and `π` can only come from A.

## 9. What each design supports, strictly

Using the hypotheses as posed: **H1** replace the primary, **H2** keep both and route
selectively, **H3** little incremental value.

| | Design A alone (representative) | Design B alone (enriched) | A + B recombined |
|---|---|---|---|
| **H1 — replace** | **Supports.** Both marginals with intervals, on the same case set, differenceable. Powered by total cases, not by errors — the one question that is *cheap*. | **Cannot address at all.** No marginals exist on B. | Supports, via A. B contributes nothing. |
| **H2 — route** | **Supports in principle, expensively.** Needs the recovery interval against a declared `r*`, `γ`, the joint rate, phi, and per-slice versions of each. Cost driven by `errors / π`. | **Cannot support.** Recovery alone is insufficient: adoption also requires `γ` (what escalation breaks), the firing rate, and phi — none estimable on B, and two of them producing plausible wrong numbers if attempted (§1.1, §1.2). | **Supports, conditional on ignorability**, with intervals that must be propagated through the products and with phi computed from the recombined cells rather than from any observed table. |
| **H3 — reject** | Supports, and is the cheapest thing A does: a recovery interval lying below a declared `r*`, or a phi near +1, kills routing quickly. | **Supports — and this is B's real contribution.** Rejection needs only the recovery interval on one side of `r*`, which is exactly the one estimand B delivers. A handful of enriched errors can kill H2 outright. | Supports; usually unnecessary, since either corpus can reject on its own. |

The asymmetry is the finding: **B is an instrument for rejecting H2, not for adopting it.**
Adoption requires terms B structurally cannot produce.

## 10. The one design change worth making

Not "run A and B in parallel". **Sequence them, and use B as a rejection screen.**

Because rejection is an order of magnitude cheaper to establish than adoption (§4, §9), a
small pre-registered enriched corpus — 10–20 confirmed primary failures, ideally prove-red
misses (§7) — can kill the routing branch before the representative study is commissioned.
If the alternate recovers nothing on cases constructed to be recoverable, no amount of
representative data will rescue it.

Conditions, all of which bind:

* Pre-register the selection rule and a declared `r*` **before** collection. Without a
  declared `r*` the screen cannot reject anything, because rejection is defined relative to it.
* Report only the recovery interval. No phi, no disagreement rate, no marginals, no
  prevalence (§1).
* Label the population explicitly — "recovery on prove-red misses", never "recovery".
* **A negative screen rejects. A positive screen does not adopt**; it licenses commissioning
  the representative study, nothing more.
* Discard gate cases, or report the conditioning (§6.7).

This is the entire endorsement. It is a cheap way to stop, not a cheap way to go.

---

## 11. Disposition

**The two-corpus design is valid with limitations, but it is not the first-study design for
this project, because no real labelled corpus currently exists. The first empirical study
remains a representative corpus (Design A).**

Three limitations bound it:

1. **Only the primary-error column is estimable from B** (§1). Half the instrument's
   outputs become undefined on it and two — disagreement and phi — become actively
   misleading, with no denominator or annotation to warn a reader.
2. **Ignorability is untestable in the regime where enrichment is attractive** (§6). The
   only diagnostic compares B's recovery to A's, and A is error-poor by construction; the
   check has power proportional to precisely the thing enrichment exists to avoid buying.
3. **The saving is on alternate observations, not on labels** (§8), and this project has
   zero labelled cases. Design B does not relieve the binding constraint. It also cannot
   improve `π`, which dominates the error in the product the decision is actually made on.

Enriched sampling is therefore **not planned**, and nothing in the codebase supports it.
The forbidden operations of §1.1 and §1.2 are recorded in the protocol so that if an
enriched corpus is ever collected, the two traps are already named.

## 12. Retractions and corrections to earlier documents

Four claims made before this review. One is retracted outright; three are narrowed.

**(1) "~320 paired cases at a 5 % primary error rate." — Weakened.**
Correct only under two conditions that were never stated: that `r*` is 0.50, and that
enrichment is unavailable. 320 is `16 / 0.05`, and 16 came from the retracted rule below.
The honest statement is that the case count is `errors_to_decide(r, r*) / π`, where the
numerator swings from 3 to 306 across plausible `r*`. 320 is one point on that surface and
was presented as the surface.

**(2) "An accurate primary makes complementarity expensive to measure." — Narrowed, not
retracted.**
True for a representative design, and true for the *prevalence* factor under every design.
False for the conditional under valid enrichment, where the cost is set by the gap to `r*`
and not by `π` at all. `README.md` and `docs/architecture.md` §10.4 state it unqualified;
both overreach and are corrected.

**(3) "Complementarity may be unmeasurable at this scale." — Weakened.**
Unmeasurable *by representative sampling at a fixed budget*. Enrichment, and in particular
a prove-red-miss screen, can reject H2 at a scale this project can afford. It cannot adopt
H2 at that scale, which is the part worth keeping.

**(4) The 16-error floor as a sufficiency criterion. — Retracted.**
`MIN_ERRORS_FOR_CONDITIONAL = 16` was derived against 0.5, and 0.5 was an undeclared
economic assumption printed in the register of a statistical convention (§4). It is not
replaced by another constant. Sufficiency is now evaluated against a caller-declared `r*`;
a study with no declared `r*` reports descriptive statistics and refuses to call them
decision-sufficient. 16 survives only as `POINT_ESTIMATE_FLOOR`, an explicitly labelled
presentation warning that carries no verdict.

Retraction (4) is implemented in `complementarity.py`, `complementarity_report.py` and
`cli.py`. Retractions (1)–(3) are corrections to prose, applied in the protocol, the README
and the architecture document.
