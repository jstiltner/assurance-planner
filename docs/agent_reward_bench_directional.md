# Directional analysis: which of the primary's errors can anything actually fix

`docs/agent_reward_bench_findings.md` reported `P(alternate correct | primary wrong)` on
the primary's errors pooled together, and flagged in §3 that the pooling was doing most
of the work. This document splits that denominator and asks the replacement question
before the routing question.

No new judgments were purchased. No planner code changed. Everything below is a
re-tabulation of the verdicts imported at `594918f`.

Reproduce with:

```
python scripts/arb_extract.py && python scripts/arb_import.py --tier-c
python scripts/arb_directional.py
```

**Tier discipline, unchanged.** `functional` → `aer` was predeclared in
`docs/agent_reward_bench_gate1.md` at `9fdaaf1`, before any joint error table existed,
and is the only confirmatory pair. `aer` → `nnetnav` was predeclared as Tier B. The
other seven pairs are exploratory diagnostics and are labelled `C-EXPLORATORY` on every
row of `data/REAL_arb_directional.csv`. Nothing here converts an exploratory pair into a
predeclared one.

**One thing is new and must be flagged as such.** The *directional split itself* was not
predeclared. It is a post-hoc decomposition applied uniformly to all pairs, motivated by
a defect found in the Phase 2 analysis rather than by an outcome. That is weaker than a
predeclared analysis and much stronger than post-hoc pair selection, and the distinction
is the reason both directions are reported for every candidate rather than the flattering
one.

**Polarity verified, not assumed.** `scripts/arb_directional.py` recomputes the
success-class precision and recall of every judge in upstream's polarity and compares
them to Table 7 of arXiv:2504.08942. All seven judges the paper tabulates reproduce
**exactly to one decimal place** — `functional` 83.8/55.9, `aer` 67.7/71.9, `nnetnav`
52.5/82.4, `gpt-4o` 69.8/83.1, `gpt-4o-mini` 61.5/86.1, `claude-3.7-sonnet` 68.8/81.6,
`llama-3.3-70b` 67.7/79.0, `qwen-2.5-vl` 64.3/89.8. An inverted label anywhere in the
import would land these at the complements of the published values. It does not.

---

## 1. The two directional quantities, and the two that a running system can see

For each candidate, four rates, never pooled:

| | conditions on | denominator | what it answers |
| --- | --- | --- | --- |
| **missed-failure catch** | reference label | primary's false negatives | of the failures the primary let through, how many does the alternate see |
| **false-alarm rescue** | reference label | primary's false positives | of the successes the primary rejected, how many does the alternate clear |
| **overturn-to-fail precision** | verdicts only | primary PASS ∧ alternate FAIL | if the alternate contradicts a pass, is it right |
| **overturn-to-pass precision** | verdicts only | primary FAIL ∧ alternate PASS | if the alternate contradicts a fail, is it right |

The first two are the quantities the brief asked for. The second two are here because
**the first two condition on something a deployed system does not have.** "Given this was
a false alarm, the alternate clears it 83% of the time" is not a policy: nothing selects
the false alarms at runtime. The policy operates on the disagreement, and the rate on the
disagreement is a different number — much lower whenever the primary's positive class is
mostly correct, which it is here.

That gap is the main result of this pass and it is large. `gpt-4o-mini` rescues 83.1% of
the primary's false alarms and is right on only 43.2% of the overturns it would actually
perform.

---

## 2. Full evaluator comparison

Primary = `functional` (the AgentRewardBench programmatic verifier), baseline row first,
alternates alphabetical. **No overall rank is emitted**; `data/REAL_arb_directional.csv`
carries the eight-cell contingency table for every pair, which is the complete sufficient
statistic for every number below, so any column can be re-sorted without rerunning
anything.

Failure is the positive class throughout. Paired support differs by pair because
unparseable alternate verdicts stay missing rather than being scored as wrong.

| source | n | TP | FN | FP | TN | sens | spec | prec | FNR | FPR | acc | errors | cost/judgment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **`functional` (primary)** | 1106 | 779 | 32 | 130 | 165 | 0.961 | 0.559 | 0.857 | **0.039** | **0.441** | 0.854 | 162 | absent (no model call) |
| `aer` — **Tier A, predeclared** | 1106 | 710 | 101 | 83 | 212 | 0.875 | 0.719 | 0.895 | 0.125 | 0.281 | 0.834 | 184 | $0.0105 |
| `claude-3.7-sonnet` (axtree) | 1100 | 697 | 109 | 54 | 240 | 0.865 | 0.816 | 0.928 | 0.135 | 0.184 | 0.852 | 163 | $0.0394 |
| `gpt-4o` (axtree) | 1106 | 705 | 106 | 50 | 245 | 0.869 | 0.831 | 0.934 | 0.131 | 0.169 | 0.859 | 156 | $0.0264 |
| `gpt-4o-mini` (axtree) | 1105 | 651 | 159 | 41 | 254 | 0.804 | 0.861 | 0.941 | 0.196 | 0.139 | 0.819 | 200 | $0.0015 |
| `gpt-4o-mini` (neither) | 1106 | 670 | 141 | 77 | 218 | 0.826 | 0.739 | 0.897 | 0.174 | 0.261 | 0.803 | 218 | $0.0006 |
| `llama-3.3-70b` (axtree) | 1106 | 700 | 111 | 62 | 233 | 0.863 | 0.790 | 0.919 | 0.137 | 0.210 | 0.844 | 173 | unpriced (vllm) |
| `nnetnav` (llama-3.3-70b) | 1106 | 591 | 220 | 52 | 243 | 0.729 | 0.824 | 0.919 | 0.271 | 0.176 | 0.754 | 272 | unpriced (vllm) |
| `qwen-2.5-vl` (axtree) | 1106 | 664 | 147 | 30 | 265 | 0.819 | 0.898 | 0.957 | 0.181 | 0.102 | 0.840 | 177 | unpriced (vllm) |

Pair-level statistics, same ordering:

| alternate | joint err | phi | disagreements | catch (n=32) | rescue (n=130) | overturn→fail | overturn→pass |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `aer` — **Tier A** | 0.067 | +0.323 | 198 | **0.469** | 0.562 | 0.366 (15/41) | 0.465 (73/157) |
| `claude-3.7-sonnet` | 0.049 | +0.218 | 216 | 0.406 | 0.729 | 0.406 (13/32) | 0.511 (94/184) |
| `gpt-4o` | 0.050 | +0.236 | 208 | 0.438 | 0.715 | 0.519 (14/27) | 0.514 (93/181) |
| `gpt-4o-mini` (axtree) | 0.035 | +0.064 | 284 | **0.469** | 0.831 | 0.441 (15/34) | 0.432 (108/250) |
| `gpt-4o-mini` (neither) | 0.042 | +0.090 | 288 | **0.469** | 0.777 | 0.238 (15/63) | 0.449 (101/225) |
| `llama-3.3-70b` | 0.049 | +0.202 | 227 | 0.438 | 0.723 | 0.350 (14/40) | 0.503 (94/187) |
| `nnetnav` | 0.043 | +0.048 | 338 | 0.281 | 0.808 | 0.250 (9/36) | 0.348 (105/302) |
| `qwen-2.5-vl` | 0.035 | +0.091 | 261 | 0.375 | 0.854 | 0.522 (12/23) | 0.466 (111/238) |

Latency is **UNMEASURED for every row**. Upstream records no judge timing; the elapsed
time it does record belongs to the agent under test. Three of eight alternates have no
cost either — a literal `0.0` written by a self-hosted vllm endpoint, which is not a
measurement of zero.

`claude-3.7-sonnet`'s denominators are 1100/32/129 rather than 1106/32/130: six of its
judgments were unparseable and one of those falls in the false-alarm stratum.

---

## 3. Directional table 1 — missed-failure catch

`P(alternate correct | primary false negative)`, denominator = the primary's 32 false
negatives. Ordered by this column only; this is not an overall ranking.

| alternate | catch | 95% Wilson | numerator / denominator |
| --- | --- | --- | --- |
| `aer` — **Tier A, predeclared** | 0.469 | [0.309, 0.636] | 15 / 32 |
| `gpt-4o-mini` (axtree) | 0.469 | [0.309, 0.636] | 15 / 32 |
| `gpt-4o-mini` (neither) | 0.469 | [0.309, 0.636] | 15 / 32 |
| `gpt-4o` (axtree) | 0.438 | [0.282, 0.607] | 14 / 32 |
| `llama-3.3-70b` (axtree) | 0.438 | [0.282, 0.607] | 14 / 32 |
| `claude-3.7-sonnet` (axtree) | 0.406 | [0.255, 0.577] | 13 / 32 |
| `qwen-2.5-vl` (axtree) | 0.375 | [0.229, 0.547] | 12 / 32 |
| `nnetnav` | 0.281 | [0.156, 0.454] | 9 / 32 |

The denominator is not suppressed and is the point. Nine to fifteen successes out of
thirty-two: **every interval contains every other point estimate.** The eight candidates
are not distinguishable on this stratum, and no arrangement of these numbers licenses
preferring one alternate over another for missed-failure detection.

No point estimate reaches 0.5. That is reported as an observation about where the
evidence lies, **not** as a comparison against a threshold — no `r*` has been declared,
and the correct reading under an undeclared `r*` remains `NOT DECISION-SUFFICIENT`.

**And the predeclared pair is tied for the top of this table.** It came last of the eight
on pooled recovery. That reversal is §6.

---

## 4. Directional table 2 — false-alarm rescue

`P(alternate correct | primary false positive)`, denominator = the primary's 130 false
positives (129 for `claude-3.7-sonnet`).

| alternate | rescue | 95% Wilson | numerator / denominator |
| --- | --- | --- | --- |
| `qwen-2.5-vl` (axtree) | 0.854 | [0.783, 0.904] | 111 / 130 |
| `gpt-4o-mini` (axtree) | 0.831 | [0.757, 0.886] | 108 / 130 |
| `nnetnav` | 0.808 | [0.732, 0.866] | 105 / 130 |
| `gpt-4o-mini` (neither) | 0.777 | [0.698, 0.840] | 101 / 130 |
| `claude-3.7-sonnet` (axtree) | 0.729 | [0.646, 0.798] | 94 / 129 |
| `llama-3.3-70b` (axtree) | 0.723 | [0.641, 0.793] | 94 / 130 |
| `gpt-4o` (axtree) | 0.715 | [0.633, 0.786] | 93 / 130 |
| `aer` — **Tier A, predeclared** | 0.562 | [0.476, 0.644] | 73 / 130 |

Here the candidates *are* separated: `qwen` at 0.854 and `aer` at 0.562 have
non-overlapping intervals. This is the stratum on which the whole pooled-recovery
ranking was built, and it is the stratum the assurance question is not about.

### Why this table does not support an adjudication architecture

The obvious reading — "route the primary's FAIL verdicts to an alternate and recover 85%
of the false alarms" — does not survive contact with the cases it would run on. The
primary says FAIL on 909 of 1,106 cases, of which 779 are correct and 130 are not. An
adjudicator that clears cases cannot tell those apart:

| alternate | clears a real success (correction) | clears a real failure (new miss) | net |
| --- | --- | --- | --- |
| `aer` — **Tier A** | 73 | 84 | **−11** |
| `claude-3.7-sonnet` | 94 | 90 | +4 |
| `gpt-4o` | 93 | 88 | +5 |
| `gpt-4o-mini` (axtree) | 108 | 142 | **−34** |
| `gpt-4o-mini` (neither) | 101 | 124 | **−23** |
| `llama-3.3-70b` | 94 | 93 | +1 |
| `nnetnav` | 105 | 197 | **−92** |
| `qwen-2.5-vl` | 111 | 127 | **−16** |

Blanket adjudication on `primary FAIL` is, for every one of the eight, **at best a
one-for-one exchange of false alarms for missed failures**, and for five of the eight a
losing one even counted in raw cases. The "net" column is shown for arithmetic only and
must not be read as a decision: the two columns are different errors and netting them
assumes an exchange rate this project declines to assume. But the sign is enough for a
weak conditional statement that requires no `r*`, only the sign of the asymmetry:

> **If a missed failure costs at least as much as a false alarm, blanket adjudication on
> the primary's FAIL verdict is non-positive against every candidate measured here.**

The overturn-to-pass precisions in §2 say the same thing directly: 0.348 to 0.514. The
alternate is right on roughly half the overturns it would perform. That is a coin flip,
and it is the number a policy would run at.

### What the false-alarm stratum is actually evidence of

Of the 130 false alarms, **60 (46.2%) are cleared by all eight alternates** and 80
(61.5%) by at least seven — five backbones, three prompt lineages, unanimous. Only six
(4.6%) are missed by every alternate.

Near-unanimous disagreement is not a complementarity signal. It is evidence that the
primary's decision rule is wrong on a recognisable and large class of cases. Upstream
says so itself: the AgentRewardBench paper's central claim is that programmatic reward
functions misjudge real trajectories, and `functional` is that programmatic verifier,
here measured at specificity 0.559. Of the brief's three readings of a rescue result —
replacement, adjudication, or *evidence that the primary's threshold/configuration is
wrong* — **this corpus supports the third.**

---

## 5. Replacement gate

Checked before routing, on the two dimensions measured for every source. Cost is
measured for five of nine and structurally absent or unpriced for the rest; latency is
measured for none. Neither can enter a dominance test without inventing the missing
values, so what follows is **dominance on measured error only**, a strictly weaker claim
than operational dominance.

### Does any alternate Pareto-dominate the primary?

**No.** Every one of the eight trades false negatives for false positives against it:

```
source                              FNR    FPR
functional (primary)              0.039  0.441     <- best FNR of all nine, worst FPR
aer                               0.125  0.281
claude-3.7-sonnet (axtree)        0.135  0.184
gpt-4o (axtree)                   0.131  0.169
gpt-4o-mini (axtree)              0.196  0.139
gpt-4o-mini (neither)             0.174  0.261
llama-3.3-70b (axtree)            0.137  0.210
nnetnav                           0.271  0.176
qwen-2.5-vl (axtree)              0.181  0.102     <- best FPR of all nine
```

The primary sits on the Pareto frontier, at one extreme of it. The frontier is
`functional` → `aer` → `gpt-4o` → `qwen-2.5-vl`, four points spanning FNR 0.039–0.181
and FPR 0.441–0.102. **The replacement candidate flag does not fire.** No evaluator
reduces both FN and FP relative to the current primary, so the primary is not an inferior
default in the sense the gate was built to catch — it is a *differently positioned* one.

`gpt-4o` has fewer total errors than the primary (156 vs 162) and higher accuracy (0.859
vs 0.854). Neither is dominance, both are secondary context, and reading either as
superiority would be exactly the aggregation error this document exists to correct: the
two error counts are not interchangeable.

### Dominance among the alternates

Four of the eight are dominated on both error rates by another alternate:

| dominated | by |
| --- | --- |
| `claude-3.7-sonnet` (axtree), $0.0394 | `gpt-4o` (axtree), $0.0264 — **and cheaper** |
| `llama-3.3-70b` (axtree) | `gpt-4o`, `claude-3.7-sonnet` |
| `gpt-4o-mini` (neither), $0.0006 | `gpt-4o`, `claude-3.7-sonnet`, `llama-3.3-70b` |
| `gpt-4o-mini` (axtree), $0.0015 | `qwen-2.5-vl` (unpriced — no cost comparison possible) |
| `nnetnav` | `gpt-4o`, `gpt-4o-mini` (axtree), `qwen-2.5-vl` |

`claude-3.7-sonnet` is the only case where dominance extends to a measured cost: it is
worse on both error rates than `gpt-4o` and 49% more expensive per judgment. Everywhere
else the dominating source is unpriced or the priced comparison runs the other way, so
operational dominance **cannot be established**, only error dominance.

Two consequences worth carrying forward: `nnetnav` — the predeclared Tier B alternate —
is dominated on error by three of its peers; and any future alternate-evidence
architecture has four candidates already excluded on measured error rates alone, before
any economics are declared.

### Statistical evidence of superiority, as distinct from different point estimates

Paired, on the discordant cases only, which is the conditional proportion McNemar's test
is a test of, reported as a Wilson interval rather than a p-value because a p-value
invites a threshold nobody has declared. An interval clear of 0.5 is paired evidence that
one source is better on that stratum.

- **On failure-labelled cases**, the alternate is right on 4.4%–15.2% of disagreements
  (`nnetnav` 0.044 [0.023, 0.081] to `aer` 0.152 [0.094, 0.235]). Every interval is far
  below 0.5. **The primary is decisively better at detecting failures than all eight.**
- **On success-labelled cases**, the alternate is right on 67.8%–91.0% of disagreements
  (`gpt-4o-mini` neither 0.678 [0.599, 0.748] to `qwen-2.5-vl` 0.910 [0.846, 0.949]).
  Every interval is far above 0.5. **All eight are decisively better at recognising
  success.**

Both directions are statistically supported and they point opposite ways. This is not a
case where the intervals are too wide to separate the sources; it is a case where the
sources are cleanly separated on both dimensions and the separations cancel.

---

## 6. Confirmatory pair versus post-hoc oracle

The pair that would have looked best after viewing all eight joint-error tables is
`functional` → `gpt-4o-mini` (axtree): equal-best pooled recovery, lowest phi but one,
equal-lowest joint error. It is labelled here and in the CSV as
**POST-HOC ORACLE / EXPLORATORY ONLY** and may not be used for any recommendation.

| quantity | confirmatory `aer` | **post-hoc oracle** `gpt-4o-mini` | difference |
| --- | --- | --- | --- |
| pooled recovery | 0.543 [0.466, 0.618] | 0.759 [0.688, 0.819] | **+0.216** |
| error association phi | +0.323 | +0.064 | −0.259 |
| joint error rate | 0.067 | 0.035 | −0.032 |
| **missed-failure catch** | **0.469 (15/32)** | **0.469 (15/32)** | **0.000 — identical** |
| false-alarm rescue | 0.562 (73/130) | 0.831 (108/130) | +0.269 |
| overturn-to-fail precision | 0.366 (15/41) | 0.441 (15/34) | +0.075 |
| overturn-to-pass precision | 0.465 (73/157) | 0.432 (108/250) | −0.033 |
| adjudication balance | 73 correct / 84 wrong | 108 correct / 142 wrong | worse |
| measured cost | $0.0105 | $0.0015 | 7× cheaper |

The Phase 2 finding stands: selecting after looking inflates the headline by 0.216 of
recovery and makes the errors look nearly unassociated (+0.323 → +0.064) in a report that
would read identically. **What is new is where that inflation lives.**

> Post-hoc selection bought **+0.216 of pooled recovery and exactly zero** on the
> missed-failure stratum — the same 15 of the same 32 cases. The entire apparent
> advantage of the oracle pair is located in the stratum the assurance question is not
> about.

And the corollary, which cuts the other way and is reported because it does:

> The predeclared pair came **last of eight** on pooled recovery and is **tied first of
> eight** on missed-failure catch. Its ranking did not improve because the pair got
> better; it improved because the pooled statistic that ranked it last was measuring
> something else.

Neither observation is a general magnitude. One corpus, one primary, eight alternates
sharing 32 error cases. What generalises is the mechanism: a pooled rate over strata with
different meanings can be moved a long way by selection without moving the stratum that
matters at all, in either direction.

---

## 7. Benchmark decomposition

The primary's two error strata are distributed very differently across the four
benchmarks:

| benchmark | paired n | missed failures | false alarms | primary errors |
| --- | --- | --- | --- | --- |
| `assistantbench` | 108 | 3 | 7 | 10 |
| `visualwebarena` | 276 | 8 | 33 | 41 |
| `webarena` | 310 | **17** | 55 | 72 |
| `workarena` | 412 | 4 | 35 | 39 |

**The error types do concentrate, in opposite places.** `webarena` is 28% of the corpus
and carries 53% of the missed failures. `workarena` is 37% of the corpus and carries 12%
of the missed failures but 27% of the false alarms — the primary is nearly never wrong in
the assurance-relevant direction there.

False-alarm rescue on the confirmatory pair, by benchmark: `assistantbench` 0.714 (n=7),
`visualwebarena` 0.576 (n=33), `webarena` 0.745 (n=55), `workarena` 0.229 (n=35). The
`workarena` figure is the lowest cell in the entire slice analysis and is low for *every*
alternate (0.229–0.800, with six of eight below 0.72) — the one place where the eight
disagree sharply, `nnetnav` being best at 0.800 while being worst overall on catch.

Missed-failure catch by benchmark cannot carry any weight at all: the four denominators
are 3, 8, 17 and 4, and three of the four are below the 16-case presentation floor and
are marked `THIN` in the script output. `webarena`'s 17 is the only one above it, at
0.471 [0.262, 0.690].

**None of this may be used as a routing feature.** Every slice effect here was discovered
after seeing outcomes and is exploratory. The `workarena` rescue deficit is the shape a
slice-keyed router would want, and fitting a threshold to it would fit it to the data it
would later be scored on — the same objection recorded in `docs/agent_reward_bench_findings.md`
§5, which this section does not relax.

---

## 8. Structural independence versus measured error independence

Gate 1's pre-outcome reasoning used prompt lineage, backbone and input modality as
proxies for evaluator independence, and picked `aer` partly because its prompt is
externally authored. Phase 2 recorded that this ranked backwards. Here is the full
tabulation, with the alternate's own failure-sensitivity added in the last column:

| alternate | lineage | backbone | inputs | phi | sens | catch | rescue |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `aer` | **AER** | gpt-4o | axtree | +0.323 | 0.875 | 0.469 | 0.562 |
| `gpt-4o` | simplified | gpt-4o | axtree | +0.236 | 0.869 | 0.438 | 0.715 |
| `claude-3.7-sonnet` | simplified | claude-3.7-sonnet | axtree | +0.218 | 0.865 | 0.406 | 0.729 |
| `llama-3.3-70b` | simplified | llama-3.3-70b | axtree | +0.202 | 0.863 | 0.438 | 0.723 |
| `qwen-2.5-vl` | simplified | qwen-2.5-vl | axtree | +0.091 | 0.819 | 0.375 | 0.854 |
| `gpt-4o-mini` | simplified | gpt-4o-mini | **none** | +0.090 | 0.826 | 0.469 | 0.777 |
| `gpt-4o-mini` | simplified | gpt-4o-mini | axtree | +0.064 | 0.804 | 0.469 | 0.831 |
| `nnetnav` | **NNetNav** | llama-3.3-70b | axtree | +0.048 | 0.729 | 0.281 | 0.808 |

Read the lineage column against the phi column. The two judges with distinct, externally
authored prompt lineages sit at **opposite ends** of the phi ordering — `aer` most
associated, `nnetnav` least — with the six judges that share one template filling the
middle in no lineage-related order. Backbone does no better: the two `gpt-4o-mini`
variants are adjacent, but so are `gpt-4o` and `claude-3.7-sonnet`, and `llama-3.3-70b`
appears at +0.202 and +0.048 depending only on which prompt it is wearing.

> **The "opposite ends" evidence is a pooled artifact — narrowed by
> `docs/agent_reward_bench_conditional.md` §4.** Conditional on the reference label the two
> externally-authored lineages are *not* at opposite ends: `aer` ranks fourth of eight and
> `nnetnav` sixth of eight on the missed-failure stratum. The conclusion below is
> unaffected and in fact strengthened — see the note at the end of this section.

The permitted conclusion, and no more than this:

> **Structural or provenance diversity cannot be assumed to imply error diversity. In
> this benchmark it must be measured.**

### A mechanism that fits these eight points, offered as a hypothesis and not a predictor

Ordering the eight by phi and ordering them by the alternate's **own failure-sensitivity**
produces the same sequence up to a single adjacent transposition — `qwen-2.5-vl` (+0.091,
sens 0.819) and `gpt-4o-mini` neither (+0.090, sens 0.826) swap, and their phi values
differ by 0.001. Six of eight positions are identical; the two that differ are a tie.

A plausible reading is that phi against this primary is mostly a restatement of how
closely the alternate reproduces the primary's *operating point* rather than anything
about its mechanism. The primary is the most trigger-happy source available
(sensitivity 0.961, specificity 0.559); 73% of the corpus is failure-labelled; an
alternate that also flags aggressively will agree with it, including where it is wrong.
Under that reading, two judges with identical prompts and different thresholds would show
low phi, and two with unrelated prompts at the same threshold would show high phi — which
is the opposite of what phi gets used for.

This is **eight points and one primary**. It is not a predictor, no model is fitted to it,
and it may not be used to select or exclude a candidate. It is written down because it is
a falsifiable explanation of a negative result that would otherwise read as
unexplained — and because, if it holds, "error association" is not the independence
measurement the planner's argument has been treating it as.

> **Narrowed by `docs/agent_reward_bench_conditional.md`.** The hypothesis above was
> falsified in the direction stated and was wrong about the magnitude. Conditioning on
> the reference label takes the phi/sensitivity correspondence from 6/8 positions to
> **1/8** on the reference-failure stratum, confirming that the pooled correspondence is
> an operating-point effect. But this section implies the true mechanism-level association
> is some other number phi was standing in for. It is not: within the reference-failure
> stratum **all eight alternates sit between odds ratio 5.08 and 11.11**, nearly constant
> across five backbones and three prompt lineages. The defect is therefore not that phi
> mismeasures diversity — it is that phi orders the alternates on the reference-success
> stratum, which holds 80% of this primary's errors and on which the missed-failure
> question does not arise at all. Left as written; see `conditional.md` §4 and §6.

---

## 9. The primary's operating point determines everything above — Tier B

Every result in §§2–8 is conditioned on a primary whose errors are 80% false alarms.
Nothing in the eight-pair table can say whether that is a fact about evaluator pairing or
an artifact of having predeclared the most trigger-happy verdict source in the corpus.
Tier B was predeclared for a different reason and answers it.

**`aer` → `nnetnav`, n = 1,106.** Both stochastic, different backbones, different prompt
lineages.

| | Tier A (`functional` primary) | **Tier B (`aer` primary)** |
| --- | --- | --- |
| primary error mix | 32 missed / 130 false alarms — **80% false alarms** | 101 missed / 83 false alarms — **45% false alarms** |
| missed-failure catch | 0.469 [0.309, 0.636] n=32 | 0.356 [0.270, 0.454] **n=101** |
| false-alarm rescue | 0.562 [0.476, 0.644] n=130 | 0.663 [0.556, 0.755] n=83 |
| escalate on `primary PASS` | catches 15, adds 26 — **net negative** | catches 36, adds 24 — **net positive** |
| adjudicate on `primary FAIL` | clears 73 right, 84 wrong | clears 55 right, **155 wrong** |
| overturn-to-fail precision | 0.366 [0.236, 0.519] n=41 | **0.600 [0.474, 0.714] n=60** |
| overturn-to-pass precision | 0.465 [0.389, 0.543] n=157 | 0.262 [0.207, 0.325] n=210 |

Three things follow.

1. **The n=32 constraint is a property of the primary, not of the corpus.** Swapping to a
   mid-sensitivity primary that was *also* predeclared triples the assurance-relevant
   denominator, from 32 to 101, on the same 1,106 cases. The Phase 2 correction — that
   Gate 1's support check bound on the wrong denominator — has a second half: the
   denominator is not fixed by the data, it is chosen by the primary.
2. **The informative direction flips with the operating point.** Against `functional`,
   neither overturn direction clears 0.5 and adjudication is the plausible-looking one.
   Against `aer`, adjudication collapses to 0.262 and **escalation becomes the direction
   with signal**: `aer says PASS, nnetnav says FAIL` is a real failure 60% of the time, on
   60 such cases. This is the first positive escalation result in the repository.
3. **It is not decision-sufficient.** The interval [0.474, 0.714] contains 0.5. The point
   estimate looks potentially useful; that is a different statement from decision-
   sufficient under a declared scenario, and no scenario is declared. `nnetnav` is also
   dominated on error by three other judges (§5), so the specific pairing is not the one
   a redesign should carry forward unexamined.

The directional split of Tier B was not predeclared either — same caveat as §1. Both
directions are reported.

---

## 10. How much of this error is reachable by *anything* available

Joining the eight pairs on `case_id` answers a question no single pair can: not "how many
of the 32 does this alternate catch" but "how many does anything available catch".

**The primary's 32 missed failures**, by how many of the eight alternates detect them:

| alternates detecting | cases | share |
| --- | --- | --- |
| 0 of 8 | 5 | 15.6% |
| 1 of 8 | 9 | 28.1% |
| 2 of 8 | 4 | 12.5% |
| 3–5 of 8 | 3 | 9.4% |
| 6 of 8 | 3 | 9.4% |
| 7 of 8 | 4 | 12.5% |
| 8 of 8 | 4 | 12.5% |

Reachable by at least one: 27 of 32 (84.4%). Missed by the primary *and* by all eight:
**5 of 32 (15.6%)** — three in `visualwebarena`, two in `webarena`.

But the shape matters more than the headline. **18 of the 32 (56%) are detected by two or
fewer of the eight.** A case caught by one judge out of eight is not a case an
alternate-evidence architecture can be designed around: which judge catches it is not
predictable in advance, and the 84% "reachable" figure is only achievable by a system
that runs all eight and takes any failure vote — which would also inherit all eight
judges' false alarms on the other 1,074 cases.

**The primary's 130 false alarms**, by contrast, are overwhelmingly reachable and
overwhelmingly *unanimously* reachable: 60 cases (46.2%) cleared by 8 of 8, 80 (61.5%) by
at least 7, only 6 (4.6%) by none. The two strata have entirely different structures.
Failure detection is idiosyncratic and near-irreducible; false-alarm clearing is
unanimous and looks like a defect in one component.

**The caveat that must travel with this section.** Agreement across *judges* is not the
same measurement as agreement across *repeats of one judge*. This bounds what different
evidence can do on this corpus. It says nothing about what repetition can do, which
remains unmeasured everywhere here. It is, however, the stronger form of the stability
question: an error made by a programmatic verifier and eight LLM judges spanning five
backbones and three prompt lineages is stable across *mechanism*, not merely across
draws.

---

## 11. Which interpretation the evidence supports

Against the brief's six dispositions, for the confirmatory Tier A arm:

**Not A (Replace).** The replacement gate does not fire. No alternate reduces both FN and
FP relative to the primary; the primary is on the Pareto frontier of measured error. §5.

**Not B (False-alarm adjudication), and this is a positive finding rather than an absence
of one.** The rescue rates that motivate B are 0.562–0.854, but they condition on the
reference label. Conditioned on what a running system sees, the overturn is right
0.348–0.514 of the time, and blanket adjudication trades 73–111 corrections against
84–197 new missed failures. B is contraindicated, not merely unsupported. §4.

**C (Missed-failure escalation) — live but only off the confirmatory arm, and not
decision-sufficient.** Against `functional`, escalation adds more false alarms than it
catches failures for six of eight candidates and the overturn-to-fail precision never
clears 0.5. Against `aer` (Tier B), escalation is net positive and the overturn-to-fail
precision is 0.600 [0.474, 0.714] on n=60 — an interval that contains 0.5. §9.

**Not D (both, direction-specific).** D would require the two directions to be
simultaneously usable against one primary. They are not: §5 shows the primary is
decisively better on failure-labelled disagreements and decisively worse on
success-labelled ones, and the two separations cancel.

**Between E and F, and the honest answer is F for the confirmatory arm.** Errors are not
too correlated to be worth studying — phi runs 0.048–0.323, none of it near a ceiling,
and 84% of missed failures are reached by something. The binding problem is that the
stratum the decision turns on has 32 cases and eight mutually indistinguishable readings
of them. That is **F. Insufficient evidence**, exactly where the brief predicted it would
land.

With the uncertainty stated plainly: F is a statement about the missed-failure stratum at
n=32 under this primary. It is not a statement that alternate evidence is worthless — §9
shows the same corpus produces a positive escalation signal under a different predeclared
primary, and §10 shows 84% of missed failures are reachable by *something*, just not
predictably by any one thing.

### Does the planner's original escalation premise survive?

**Qualified yes, with a constraint the planner does not currently represent.**

The premise — that a second, different evidence source can recover failures the primary
misses — is not falsified. It is measured at 0.281–0.469 against one primary and 0.356
against another, all well above zero, so the recovery rate does not kill the idea by
itself, which is the one thing `complementarity.py` says recovery can do alone.

What the premise loses is its unconditional form. Three conditions now attach to it, all
empirical:

1. **Escalation value depends on the primary's operating point, and the planner has no
   representation of that.** A maximally sensitive primary leaves almost nothing for
   escalation to find (32 cases) and makes every disagreement a false-alarm argument. The
   planner reasons about recovery rates and costs; it has no term for where the primary
   sits on its own ROC curve, and §9 shows that term dominates.
2. **The recovery rate the planner consumes is the wrong conditional.** It conditions on
   the reference label. The rate a policy runs at is the overturn precision, which is
   0.35–0.52 where recovery is 0.54–0.76. Feeding recovery into an escalation decision
   overstates the intervention by 20–30 points. This is a defect in the quantity, not in
   the measurement of it, and it is the most directly actionable finding in this document.
3. **A large share of missed failures is unreachable by any available evidence.** 15.6%
   is missed by all nine sources and 56% by six or more. Repetition cannot touch that and
   neither can a ninth judge.

The escalation premise survives as a conditional claim about primaries that are not
already operating at maximal sensitivity. It does not survive as a general architectural
justification, and §4 is now the standing counter-example to the adjudication variant.

---

## 12. Further falsifications of the current story

Collected here so they are not spread across sections. Each narrows a claim the
repository currently makes.

1. **`P(alternate correct | primary wrong)` is not a decision quantity.** It conditions on
   the reference label. Every consumer of it in the planner's reasoning — the recovery
   rate, its interval, its comparison against `r*` — inherits that. The operational
   analogue is the overturn precision and it is 20–30 points lower on this corpus. This is
   the single most consequential thing found in this pass and it is a defect in the
   framing, not in the data.
2. **Error association phi may be measuring threshold alignment, not mechanism
   diversity.** §8. If so, the repository's use of phi as evidence about evaluator
   independence is measuring the wrong thing, and the "assuming independence overstates
   joint accuracy threefold" result in `agent_reward_bench_findings.md` §6 is a true
   statement about *this pair's operating points* rather than about evaluator diversity.
   **No longer a "may be" — measured in `docs/agent_reward_bench_conditional.md`.** The
   pooled odds ratio is attenuated below the reference-failure odds ratio in 8/8 pairs and
   below *both* strata in 3/8, and pooled phi's ordering reproduces the reference-success
   ordering on its top five positions while agreeing with the reference-failure ordering
   on 1/8. The hedge is withdrawn; the conclusion in the sentence above stands.
3. **The assurance-relevant denominator is chosen, not given.** §9. Gate 1's support check
   bound on the wrong quantity; the deeper issue is that the right quantity varies by a
   factor of three depending on which predeclared primary is used.
4. **Nearly half the primary's false alarms are unanimously overturned.** §4. That is not
   complementarity and should not be reported as complementarity; it is a miscalibrated
   component, which upstream published as its own headline finding.
5. **Error stability across mechanism is measurable here and is substantial.** §10. Five
   of 32 missed failures survive nine different evaluators. The project's thesis
   distinguishes variance (attackable by repetition) from stable bias (attackable only by
   different evidence). This corpus shows a third category the thesis does not name:
   **error stable across different evidence too**, which neither lever reaches.
   **Stronger than stated, per `docs/agent_reward_bench_conditional.md` §6.** The counts
   above describe the intersection of the eight. The enrichment holds for every alternate
   *individually*: a failure the primary missed is 2.8×–5.1× likelier to be missed by the
   alternate than a failure the primary caught, for all eight.

---

## 13. Corrections to earlier documents

Following the repository convention: narrowed in place, never deleted, with the
correction recorded here.

**(1) "The predeclared pair came last of the eight." — Narrowed.**
`docs/agent_reward_bench_findings.md` §1 is correct on pooled recovery and misleading as
a summary. On the missed-failure stratum the same pair is tied first of eight (§3, §6).
The sentence stands; a pointer to this document has been added in place, because the
original claim is the one that was published and deleting it would destroy the record.

**(2) §3's "the ranking reverses" was understated.** It observed that `nnetnav` ranks
fourth on pooled recovery and last on missed failures. The stronger and correct statement
is that the pooled ranking and the directional ranking share almost no information: the
pooled ranking is a ranking on the false-alarm stratum, which is 80% of the denominator.
Narrowed in place.

**(3) §6's disposition — "complementarity is real but weaker than the marginals suggest,
and the evidence is not decision-sufficient" — is superseded for the Tier A arm by §11
above (F, insufficient evidence on the stratum that decides).** The earlier disposition
was correct on the evidence available to it; it was computed on the pooled statistic that
§12.1 now identifies as the wrong conditional. Left as written, with a forward pointer.

Nothing in `docs/agent_reward_bench_gate1.md` is edited. It is the record of what was
decided in advance.
