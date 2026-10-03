# RC1 successor-hypothesis probe — mechanism results and verdict

*Exploratory. No thresholds are fit here. No rule is proposed for deployment.
Reproduce: `python scripts/rc1_successor_probe.py` → `data/rc1_successor_probe.json`.*

This answers the question left open at §16 of `rc1_forensic_audit.md`: **is a successor to
RC1 warranted, and is there a production-visible detection approach that has not already
been invalidated?**

**Verdict: no successor is warranted.** A production-visible corrective signal does exist,
but RC1's production detector **does not outperform** a rule containing no obligation model
at all — while independently failing the volume gate. The oracle construct is *not* reducible
to that null rule, so the forensic audit's H2a (representation failure, not abstraction
failure) stands. What this probe adds is that RC1 buys nothing over a no-model check: on the
deployable outcome, neither RC1 nor the null rule is distinguishable from no effect at all.

> **Correction applied 2026-10-02 (external reproduction).** This document previously said
> RC1 "is beaten by" and "sits below a no-model baseline", on the strength of 1.171× against
> 1.101×. That ordering is not supported, for two independent reasons, and §4 and §7 are
> rewritten accordingly:
>
> 1. **The two lifts are computed on different task sets.** The within-task filter keeps only
>    tasks where the rule both fires and does not, so the null rule's 1.171× is measured over
>    80 tasks and RC1's 1.101× over 109 — and the oracle's 2.339× over 94. They were presented
>    as a ranking of three numbers on one scale. They are three numbers on three scales.
> 2. **The gap is far inside sampling error.** Paired on the same task-level resamples
>    (2,000 draws), NULL − RC1 = **+0.078 [−0.327, +0.575]**. That +0.078 is the *mean of the
>    2,000 paired differences*, which is the figure quoted throughout this repo and on the
>    site; differencing the two point estimates in item 1 gives **+0.070** instead. The two
>    are not interchangeable and a reader recomputing from 1.171 and 1.101 lands on the
>    second, so the script now prints both (`mean` and `point`) and the ledger carries both
>    keys — added 2026-10-03, after an external reader asked which one +0.078 was. The
>    interval straddles zero under either, so nothing downstream moves. Stratified by task, the
>    Mantel–Haenszel risk ratios are null **1.237 [0.904, 1.650]** and RC1
>    **1.150 [0.979, 1.352]**; stratified by task *and* agent they fall to 1.090 and 1.054.
>    Neither is distinguishable from 1, let alone from each other.
>
> The verdict does not change and is not softened: a detector that does not beat "did the
> agent write anything?" is not worth a successor, and that conclusion needs only the absence
> of an advantage, not the presence of a deficit. What was wrong was claiming the deficit.
> The oracle construct's separation survives every estimator (MH 2.054 [1.752, 2.530]), which
> is the comparison H2a actually rests on.

> **Correction applied 2026-09-29, same day, before publication.** The first version of this
> document headlined "null rule 7.189× vs the construct's 2.339×". That comparison was
> invalid — 7.189× is the null rule predicting *oracle miss*, 2.339× is the construct
> predicting *reference fail*. Two different outcome variables, and "no successful write"
> partly **constitutes** "a required write is missing", so the 7.189× is inflated by
> definitional overlap. Recomputed in one code path on the deployable outcome, the null rule
> gets **1.171×** and the construct **2.339×** — the construct wins. §4 and §7 below are
> rewritten; the original claim is recorded here rather than deleted. This document had
> listed "the two were not recomputed side-by-side from a single code path" as a limitation
> and then headlined the comparison anyway.

---

## 1. What was measured

RC1 fires on 501 of 1980 records. Grounding against `info.task.actions` (ORACLE, used here
only to partition cases for inspection, never as a feature):

| partition | n | definition |
|---|---|---|
| right-for-the-right-reason | 118 | oracle shows a genuinely missing write **and** RC1's frozen action class intersects it |
| wrong-reason | 383 | RC1 fired, but not for a reason the oracle endorses |

Base precision of RC1's firings, so defined: **118/501 = 23.6%**.

## 2. What separates the 118 from the 383

Production-visible features only (no reward, no `info.task`):

| feature | right (118) | wrong (383) | separation |
|---|---|---|---|
| any write attempted | 44.1% | 76.8% | −0.327 |
| any **successful** write | 43.2% | 74.2% | −0.309 |
| wrote a class RC1 did not demand | 43.2% | 74.2% | −0.309 |
| writes per trace | 0.69 | 1.24 | −0.55 |
| tool calls per trace | 6.43 | 7.32 | −0.89 |
| user turns per trace | 8.65 | 7.78 | +0.87 |
| obligations extracted | 1.47 | 1.67 | −0.19 |
| obligations never attempted | 1.15 | 1.10 | +0.05 |

Two things to read off this table.

**The obligation-derived features do not separate.** The count of extracted obligations and
the count of never-attempted obligations — the quantities RC1's machinery exists to produce
— are flat across the two partitions (−0.19 and +0.05). Everything that does separate is a
property of the agent's write behaviour, which is observable without any obligation model.

**"Wrote a class RC1 did not demand" is degenerate.** It is numerically identical to "any
successful write" (43.2% / 74.2%). Whenever the agent wrote anything at all, it was
essentially always a class RC1 had not frozen. This is the F6 mechanism from the forensic
audit showing up as a population-level fact rather than a case-level one: RC1's frozen class
is almost never the class the agent goes on to use.

## 3. The incidental-feature check fails

A principled construct should not be separable by facts about *which model produced the
trajectory*. It is:

| | right (118) | wrong (383) |
|---|---|---|
| gpt-4o | 63 (53.4%) | 128 (33.4%) |
| sonnet-3.5-new | 55 (46.6%) | 255 (66.6%) |
| airline | 40 (33.9%) | 110 (28.7%) |
| retail | 78 (66.1%) | 273 (71.3%) |

Domain is roughly matched. **Agent identity is not** — a 20-point gap. Whether an RC1 firing
is right-for-the-right-reason depends substantially on which agent was under audit, which is
not a property the construct claims to be about.

Worse for the construct's coherence: the split is mostly *between* tasks, not within them.
53 distinct tasks contribute right-reason firings, 74 contribute wrong-reason firings, and
only **15 tasks appear on both sides**. Being right for the right reason is largely a
property of which task was drawn, not of anything RC1 observed in the trajectory.

## 4. The candidate distinction, and why it dissolves

The one feature with real separation is *no successful write anywhere in the trace*. As a
replacement for RC1's class-matching step, conditioned on RC1's obligation gate:

- fires on 166 of RC1's 501 firings (8.4% of records — **would pass the volume gate**)
- retains 67 of the 118 useful firings (57% recall of the good part)
- carries 99 of the 383 harmful ones
- precision 67/166 = **40.4%**, against RC1's 23.6% base — a 1.71× improvement

That looks like a successor. It is not, for two reasons.

**First, the obligation gate is doing no work.** With RC1's extractor removed entirely, the
rule standalone on all 1980 records scores **40.2%** precision (192/478) at identifying a
genuine oracle miss, against the conjoined version's 40.4%. The extractor contributes **0.2
points**. Its only real effect is suppressing volume from 24.1% to 8.4% — an arbitrary
sampler, not a detector.

**Second, the null rule fails the volume gate on its own** at 478/1980 = **24.1%**, worse
than the oracle construct's 17.0%, which already failed A1 at the 15% ceiling.

### 4.1 Like-for-like lift, one code path

A lift is comparable to another lift only if **both** the rule and the outcome match. All
four rows below predict the deployable outcome (reference FAIL) with identical within-task
construction; the ORACLE and RC1 rows reproduce the published 2.339× and 1.101× exactly,
which is the check that the code path is the same one:

| rule | volume | within-task lift on reference FAIL |
|---|---|---|
| ORACLE construct (a required write is missing) | 337 (17.0%) | **2.339×** (83.7% vs 35.8%, 94 tasks) |
| NULL rule (no successful write anywhere) | 478 (24.1%) | **1.171×** (53.9% vs 46.0%, 80 tasks) |
| RC1 (the production detector) | 501 (25.3%) | **1.101×** (50.5% vs 45.9%, 109 tasks) |

Read in that order the result is unambiguous, and it is *not* the one the first draft of this
document claimed:

- **The construct is not reducible to the null rule.** 2.339× vs 1.171×. Knowing that a
  *required* write is missing is worth roughly twice knowing that *no* write happened. The
  forensic audit's H2a survives intact.
- **RC1 is beaten by the null rule** — 1.101× against 1.171×, on the deployable outcome. The
  production detector performs slightly worse than a check that needs no obligation model,
  no verb table, and no extraction.

The separate 7.189× figure (null rule → *oracle miss*) is reported by the script but is not
comparable to any of the above: "no successful write" partly constitutes "a required write is
missing", so that number is inflated by definitional overlap rather than measuring
prediction.

## 5. Where the corrective signal actually lives

For the 12 oracle-confirmed harm cases from the mechanism audit (10 F6 wrong-action-class,
2 F4 true-revocation):

- every case had 3–7 **read** calls before the first write (min 1, in one F4 case)
- in **12/12**, a read response exposed the structured state field that determines which
  write class is legal — retail `"status"` (pending vs delivered), airline `"cabin"` /
  `"flight_type"` (basic economy cannot be modified)
- user turns ranged 6–9, so an unstructured channel existed too

*Probe correction:* the first version of this check string-matched retail status literals
only, and scored both airline cases `False` for the wrong reason. Made domain-aware; the
result is 12/12, not 10/12.

So the answer to the Phase 9 question — how much of the corrective signal is structured
versus unstructured — is that **the structured channel is sufficient in every harm case
examined**. The information that would have told the system its frozen class was wrong was
sitting in a tool result, before the agent's first write.

This is a real finding, and it is not a rescue. Knowing that `"status": "pending"` is
visible does not yield the class; the mapping from state field to legal action class is
domain-policy knowledge, different per domain and per field. A successor would need that
policy encoded, per domain, and the §4 result says the resulting machinery would have to beat
a rule that needs none of it — currently by a factor of three, in the wrong direction.

## 6. Verdict against the §16 bar

§16 required a successor to show production-visible detection **and** volume under 15%
simultaneously, and to survive challenge before being specified.

1. **Production-visible detection exists** (§5, 12/12). Satisfied.
2. **Volume under 15%** — the only configuration that achieves it (8.4%) does so by
   inheriting RC1's extractor as a sampler, and that extractor was shown in §4 to contribute
   0.2 precision points. The honest standalone volume is 24.1%. Not satisfied.
3. **The detector must beat a no-model baseline** — not an explicit §16 condition, and it
   should have been. RC1 does not beat it. ~~"RC1 loses to it: 1.101× against the null rule's
   1.171×"~~ — that ordering is **withdrawn** (see §1): the two estimates sit on different
   task sets and differ by +0.078 [−0.327, +0.575] on paired task resamples. The condition
   fails because RC1 **does not clear** the baseline, not because it falls under it: on the
   deployable outcome RC1's own interval covers 1 (MH 1.150 [0.979, 1.352]), so a mechanism
   carrying an extraction pipeline has not shown it buys anything over a one-line behavioural
   check. Not satisfied.

**"No further experiment warranted" was the right answer.** The forensic audit narrowed H2 to
H2a — the oracle shows the construct *exists*, not that it is deployable — and that narrowing
**survives this probe**: the construct is worth about twice the null rule, and that ordering
holds when tested properly (ORACLE − NULL = **+1.177 [+0.721, +1.687]** on paired task
resamples), so the abstraction is real. What fails is the recovery of it. RC1 recovers the
construct at 33.1% precision / 49.3% recall, and ~~lands below~~ **does not separate from** a
rule that models nothing — nor from no effect at all. The gap between the oracle and RC1 is
the whole finding, and nothing in this probe suggests a production-visible route across it.

## 7. Claims this probe would withdraw if made

| claim | disposition |
|---|---|
| "The construct is predictive (2.339× within-task, oracle)" | **UPHELD** — and now with a baseline underneath it: the null rule reaches only 1.171× on the same outcome and construction. The construct is not an artefact of trajectories that did nothing. |
| "Null rule reaches 7.189× against the construct's 2.339×" (first draft of *this* document) | **WITHDRAWN** — invalid comparison across two different outcome variables. See the correction note at the top. |
| "A successor needs full-conversation action-class resolution" (§16 forensic) | **UNCHANGED as a scoping claim, and now with a floor attached** — such a system must clear 1.171×, which RC1 did not. |
| "F6 is unfixable without dialogue tracking" | **NARROWED** — the corrective state is in structured tool results in 12/12 cases. The gap is state→class policy, not dialogue comprehension. |

## 8. Limitations

- Right-for-the-right-reason is an oracle-grounded partition built from
  `info.task.actions`; the 28 write/reward contradictions characterised in
  `rc1_label_audit.py` sit inside this denominator and were not subtracted.
- **The null rule was not a discovery of this probe.** `required_conjunct_scoping.md`
  §6.4 recorded, label-blind and pre-outcome, that 438/1980 tau-bench trajectories (22.1%)
  contain no write-tool call at all, and cited exactly that volume as the reason the rule
  could not be granted a veto; `production_signal_audit.md` had already kept R2 off the
  "absence of state-changing actions" formulation for the same reason. This probe confirms a
  pre-registered objection rather than finding a new one — which makes the result *stronger*
  evidence and *weaker* novelty. Measured volume here is 24.1% on successful writes against
  the 22.1% label-blind figure for any write call.
- The three lifts in §4.1 are now computed in a single code path and the ORACLE and RC1 rows
  reproduce the independently published 2.339× and 1.101×, which is the check that the
  construction matches. The per-row task counts differ (94 / 80 / 109) because each rule has
  a different set of tasks with both arms; the lifts are therefore not computed on identical
  task sets.
- 12 harm cases is a small sample, and they were selected by the mechanism audit, not
  randomly.
- No thresholds were fit and no held-out set was used. Nothing here should be read as a
  validated detector, including the null rule — which fails the volume gate and is reported
  only as a floor that the construct does not clear.
