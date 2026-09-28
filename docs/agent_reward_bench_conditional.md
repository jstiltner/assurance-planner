# Is pooled error association an operating-point artifact?

Zero-cost audit. No judgments were purchased for this document; it re-tabulates the eight
cells already written by `scripts/arb_directional.py` from the cached AgentRewardBench
judgments at upstream revision `b6d17e6`. Reproduce with:

```
python scripts/arb_import.py --tier-c
python scripts/arb_conditional_association.py
```

Output: `data/REAL_arb_conditional_association.csv`.

`docs/agent_reward_bench_directional.md` §8 raised a falsifiable worry: pooled Pearson phi
orders the eight alternates almost exactly as their own failure-sensitivity does, which
would mean phi measures how closely an alternate reproduces the primary's *operating
point* rather than anything about its mechanism. §12.2 recorded it as an open falsification.
This document runs it. The answer is worse than §8 guessed, and in a direction §8 did not
anticipate.

**Tier discipline is unchanged.** `functional` → `aer` remains the single confirmatory
pair. The other seven are exploratory diagnostics and are not retroactively alternatives.

---

## 1. Why conditioning is the right test, and why it costs nothing

Within a reference class there is only one way to be wrong.

- On a **reference-failure** case neither evaluator can false-alarm. Both can only miss.
- On a **reference-success** case neither can miss. Both can only false-alarm.

So a within-class association is an association between two evaluators making *the same
kind* of mistake, which is what "do their errors co-occur" was always supposed to mean.
Pooled phi mixes the two kinds and additionally mixes in the fact that the two classes
carry wildly different error rates — which is exactly the channel through which an
operating point can masquerade as a dependence.

The primary's operating point is the whole issue in one line:

| stratum | n | share of corpus | primary's error rate | primary's errors |
| --- | --- | --- | --- | --- |
| reference failure | 811 | 73.3% | **0.039** | 32 |
| reference success | 295 | 26.7% | **0.441** | 130 |

`functional` makes **80% of its errors in 27% of the corpus.** Any pooled 2×2 against it
is numerically dominated by the reference-success stratum. That is not a hypothesis; it
is arithmetic on the margins, and it is enough on its own to make a pooled statistic
suspect before any association is computed.

**Statistics carried, and why two.** Phi is what the repository already quotes, so it has
to appear or the comparison is not a comparison — but phi is bounded by its margins, and a
2×2 with a 4% marginal error rate cannot reach the phi that a 44% one can at identical
odds. Comparing phi across strata with different error rates is therefore partly comparing
the strata. The odds ratio is invariant to those margins, which is the entire reason for
carrying a second statistic. A risk ratio is also reported because it is the one number
here that a reader can act on without knowing what a phi of +0.25 is worth.

**Undefined stays undefined.** An odds ratio with an empty cell is not `1.0`; a phi with a
degenerate margin is not `0.0`. Both read as reassuring independence when they mean no
information. Nothing here is continuity-corrected into existence. (No cell was in fact
empty on this corpus; the guard is in `association()` regardless, because the next corpus
may not be so lucky.)

---

## 2. The table

`f.RR` / `s.RR` are risk ratios: the alternate's error rate among the primary's errors,
over its error rate among the cases the primary got right, within that stratum. `1.0` is
independence.

| alternate | pooled phi/OR | ref-failure phi/OR | ref-success phi/OR | f.RR | s.RR | p.FNR | p.FPR | a.FNR | a.FPR | catch | rescue |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `aer` **(confirmatory)** | +0.323 / 6.4 | +0.250 / 9.4 | +0.310 / 4.2 | 4.93 | 2.78 | 0.040 | 0.441 | 0.124 | 0.281 | 0.469 | 0.561 |
| `claude-3.7-sonnet` | +0.218 / 3.8 | +0.273 / **11.1** | +0.200 / 2.9 | 5.11 | 2.36 | 0.040 | 0.439 | 0.135 | 0.184 | 0.406 | 0.729 |
| `gpt-4o` | +0.236 / 4.3 | +0.260 / 10.1 | +0.272 / 4.7 | 4.98 | 3.61 | 0.040 | 0.441 | 0.131 | 0.170 | 0.438 | 0.715 |
| `llama-3.3-70b` | +0.202 / 3.5 | +0.251 / 9.5 | +0.145 / 2.0 | 4.71 | 1.76 | 0.040 | 0.441 | 0.137 | 0.210 | 0.438 | 0.723 |
| `qwen-2.5-vl` | +0.091 / 1.9 | +0.234 / 8.6 | +0.131 / 2.4 | 3.83 | 2.19 | 0.040 | 0.441 | 0.181 | 0.102 | 0.375 | 0.854 |
| `gpt-4o-mini` (no axtree) | +0.090 / 1.8 | +0.191 / 6.0 | **−0.077 / 0.7** | 3.34 | 0.77 | 0.040 | 0.441 | 0.174 | 0.261 | 0.469 | 0.777 |
| `gpt-4o-mini` (axtree) | +0.064 / 1.5 | +0.171 / 5.1 | +0.078 / 1.6 | 2.91 | 1.47 | 0.040 | 0.441 | 0.196 | 0.139 | 0.469 | 0.831 |
| `nnetnav` | +0.048 / 1.4 | +0.204 / 7.5 | +0.037 / 1.2 | 2.84 | 1.18 | 0.040 | 0.441 | 0.271 | 0.176 | 0.281 | 0.808 |

Sorted by pooled phi descending. **No overall rank is emitted**, and the sort is a
presentation choice, not a finding.

Spreads, which are the point of the table:

| | min | max | ratio |
| --- | --- | --- | --- |
| pooled phi | +0.048 | +0.323 | **6.7×** |
| ref-failure phi | +0.171 | +0.273 | **1.6×** |
| ref-success phi | −0.077 | +0.310 | sign change |
| pooled odds ratio | 1.35 | 6.38 | 4.7× |
| ref-failure odds ratio | **5.08** | **11.11** | 2.2× |
| ref-success odds ratio | 0.70 | 4.65 | 6.6× |

---

## 3. Question 1 — does pooled phi materially change after conditioning?

**Yes, substantially, and not by a constant.** The change is largest exactly where the
pooled figure is most flattering.

The cleanest statement is on the odds ratio, because it is the margin-free one:

> **The pooled odds ratio is below the reference-failure odds ratio for all eight
> alternates, without exception.** For three of the eight — `gpt-4o` (4.29 vs 4.65 and
> 10.10), `qwen-2.5-vl` (1.85 vs 2.40 and 8.56) and `gpt-4o-mini` axtree (1.54 vs 1.57 and
> 5.08) — the pooled odds ratio is below the odds ratio in **both** strata. That is a
> Simpson-direction result: pooling does not average the two associations, it attenuates
> them past the smaller one.

The mechanism is visible in the table and is not mysterious. The primary errs at 4% on
reference-failure cases and 44% on reference-success cases. Several alternates run the
other way — `nnetnav` errs at 27.1% on failures and 17.6% on successes, `gpt-4o-mini`
axtree at 19.6% and 13.9%. Pooling the two strata introduces a *negative* between-stratum
component that partially cancels the positive within-stratum association. The pooled
number is then a sum of a real dependence and a confound of opposite sign, and reporting
it as "error association" reports the residue of that cancellation.

The worked case is the one the repository has leaned on hardest. `nnetnav` has the lowest
pooled phi of the eight, **+0.048**, which is the number a reader takes as "essentially
independent errors." Conditional on the reference label its odds ratios are **7.55** and
1.22. Its reference-failure risk ratio is **2.84**: a failure the primary missed is 2.84×
likelier to be missed by `nnetnav` than a failure the primary caught. Nothing about that
is independence, and the pooled statistic said it was.

---

## 4. Question 2 — does the sensitivity ordering persist within either class?

**Not in the reference-failure class. Partly in the reference-success class — and that is
the tell.**

Positional agreement against the ordering by the alternate's own failure-sensitivity
(`aer` > `gpt-4o` > `claude` > `llama` > `mini-noaxtree` > `qwen` > `mini` > `nnetnav`):

| ordering | agrees on |
| --- | --- |
| pooled phi | **6/8** |
| ref-success phi | 4/8 |
| ref-failure phi | **1/8** |
| ref-failure odds ratio | **1/8** |
| ref-success odds ratio | 1/8 |

Positional agreement is reported rather than a rank correlation: with eight points a
coefficient invites a significance reading that eight points cannot support.

Two things to read off this.

**The §8 correspondence does not survive conditioning on the failure stratum.** It goes
from 6/8 to 1/8, and the top of the ordering changes hands — `aer` leads on pooled phi and
sits **fourth** on ref-failure phi and ref-failure odds, behind `claude-3.7-sonnet`,
`gpt-4o` and `llama-3.3-70b`. The alternate with the *lowest* failure-sensitivity,
`nnetnav`, moves from last on pooled phi to sixth of eight on ref-failure odds, ahead of
both `gpt-4o-mini` variants.

**Pooled phi is close to being a restatement of ref-success phi.** The two orderings agree
on the **top five positions exactly**, and every disagreement involves `gpt-4o-mini`
(no axtree), the one alternate whose ref-success association is negative. This is the
predicted consequence of §1's margin arithmetic: 80% of the primary's errors live in the
reference-success stratum, so a statistic computed on the pooled table is computed mostly
on that stratum. The §8 hypothesis was that phi tracks threshold alignment; the sharper
version is that **pooled phi against this primary is approximately the false-alarm-stratum
association wearing a corpus-wide label.**

---

## 5. Question 3 — is pooled phi plausibly dominated by operating-point alignment?

**Yes.** Three independent lines, none of which requires a model:

1. **Margin arithmetic, before any association is computed.** 130 of the primary's 162
   errors are false alarms on 26.7% of the corpus. The pooled 2×2 is dominated by that
   stratum by construction, and the domination is a property of the primary's threshold,
   not of any alternate.
2. **The pooled ordering reproduces the ref-success ordering** on its top five and departs
   from the ref-failure ordering almost completely (1/8). The stratum that drives pooled
   phi is the stratum where the primary's operating point puts its errors.
3. **The pooled odds ratio is attenuated below the ref-failure odds ratio in 8/8 cases,
   and below both strata in 3/8.** Attenuation of that form comes from the two strata
   having oppositely-ordered error rates, which is a statement about operating points.

**What is not claimed.** This is correlation on eight alternates against one primary. No
model is fitted; nothing here says the operating point *causes* the pooled figure. The
claim is the narrow one the brief permits: pooled phi against `functional` is substantially
confounded by the primary's operating point, and cannot be read as a mechanism-level
quantity. Whether the same holds against a primary with a different error mix is a separate
question, and `docs/agent_reward_bench_directional.md` §9 already shows that swapping the
primary to `aer` moves the missed-failure stratum from n=32 to n=101.

---

## 6. Question 4 — is any of phi's use as a diversity proxy left standing?

**No, and the reason is the most important finding in this pass.**

Conditioning did not merely reorder the alternates. It **compressed them**:

> On the reference-failure stratum, all eight alternates have an odds ratio between
> **5.08 and 11.11**, and a phi between **+0.171 and +0.273**. Every one of them. Across
> five backbones, three prompt lineages, and one alternate that sees no accessibility tree
> at all.

The risk-ratio form is the operational one: **a failure the primary missed is 2.8× to 5.1×
likelier to be missed by the alternate than a failure the primary caught**, for every
alternate in the corpus. The range of "mechanism diversity" measured on the stratum that
assurance actually depends on is a factor of 1.8 in risk ratio, against a pooled phi that
ranges over a factor of 6.7 and invites the reader to treat `nnetnav` (+0.048) and `aer`
(+0.323) as qualitatively different kinds of evidence.

They are not. On missed failures they are the same kind of evidence, to within the
resolution this corpus supports. Pooled phi was not measuring a diversity that conditioning
revealed to be smaller; **it was ordering the alternates on a stratum where the question
does not arise**, because on reference-success cases nobody can miss a failure.

Two corollaries worth stating plainly.

**The post-hoc oracle bought nothing here either, and now we know why.**
`agent_reward_bench_directional.md` §6 recorded that `functional` → `gpt-4o-mini` (axtree)
would have been selected post-hoc with phi +0.064 against the predeclared pair's +0.323,
and yet returned an *identical* 15/32 missed-failure catch. The conditional table explains
the coincidence that was not one: `gpt-4o-mini`'s reference-failure odds ratio is 5.08 and
`aer`'s is 9.38 — the same order of magnitude, both far from independence — while their
pooled phis differ fivefold. A selection made on pooled phi is a selection made on
false-alarm agreement, which is why it did not move the missed-failure number.

**One negative association exists and it is not where a diversity story would want it.**
`gpt-4o-mini` (no axtree) has ref-success phi **−0.077**, odds ratio 0.70, risk ratio 0.77:
on reference-success cases it false-alarms *less* often when the primary does. It is the
only sub-1.0 cell in the table, it is on the stratum that does not decide anything, and its
ref-failure odds ratio is 5.99 like everyone else's. Reported because it is the one datum
that cuts against §3–§5's uniformity, and suppressing it would be selecting on outcome.

---

## 7. What this does and does not license

**Permitted conclusion, per the brief's list:** pooled phi against this primary is
*substantially confounded by the primary's operating point*, and additionally the
conditional analysis shows within-class error dependence that the pooled figure
understates rather than overstates.

**Not licensed:**

- Any claim that an alternate is or is not "independent" in a mechanism sense. What is
  measured is co-occurrence of errors against one primary on one corpus.
- Any causal statement. Eight alternates, one primary, one benchmark population.
- Any re-selection of the confirmatory pair. `functional` → `aer` was predeclared and
  remains the confirmatory result; that `claude-3.7-sonnet` has the highest ref-failure
  odds ratio is an exploratory observation and nothing else.
- Any threshold. No `r*` is declared here and none is inferred. Absent a declared `r*` the
  correct planner output remains `NOT DECISION-SUFFICIENT`.

**Does this invalidate the repetition study?** No — and that is the specific check the
brief required before any judgments are purchased. Nothing here contradicts the study's
design. It does two things to it: it strengthens the premise (if every alternate's errors
on the missed-failure stratum are 2.8–5.1× enriched on the primary's errors, then "buy a
different evaluator" is a weaker lever than the pooled numbers implied, which raises the
value of knowing how much of the error is merely noise), and it reinforces the prohibition
on pooled reporting already written into `repetition_study_predeclaration.md` §2. The
judge, corpus and R are unchanged.

---

## 8. Corrections to earlier documents

Repository convention: narrowed in place, never deleted, with the correction recorded here.

**(1) `agent_reward_bench_directional.md` §8 — hypothesis confirmed in direction and
wrong in magnitude.** §8 proposed that phi "is mostly a restatement of how closely the
alternate reproduces the primary's operating point." Confirmed. But §8's framing implied
the true mechanism-level association was some *other* number that phi was standing in for;
§6 above shows the true within-class association is **uniformly strong and nearly constant
across all eight**, so the defect is not that phi mismeasures diversity but that it orders
alternates on a stratum where the diversity question does not arise. Narrowed in place with
a forward pointer.

**(2) `agent_reward_bench_directional.md` §12.2 — upgraded from "may be" to measured.**
It read "Error association phi *may be* measuring threshold alignment, not mechanism
diversity." That was correct to hedge at the time. It is now measured. Narrowed in place.

**(3) `agent_reward_bench_directional.md` §11 and §12.5 — the cross-mechanism stability
finding is stronger than stated.** §10 reported that 5 of 32 missed failures survive all
eight alternates and 18 of 32 are reached by two or fewer. Those are counts. §6 above adds
the rate statement: the enrichment is present for *every* alternate individually, not only
in the intersection. Narrowed in place.

**(4) `agent_reward_bench_findings.md` §2 and §6 — "materially weaker than independence
would give" is correct and understated.** §6 states that phi +0.323 shows the pair's joint
accuracy is weaker than an independence assumption would give, and licenses the claim that
assuming independence overstates joint accuracy threefold. The claim stands for this pair.
What it must no longer be read to support is the comparative reading — that a pair with a
lower pooled phi is closer to independent. On the missed-failure stratum the eight pairs
are not distinguishable in that way. Narrowed in place.

Nothing in `docs/agent_reward_bench_gate1.md` is edited. It is the record of what was
decided in advance, and its independence ratings were pre-outcome reasoning that this
document does not get to rewrite.
