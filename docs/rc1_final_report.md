# RC1 Final Report: `required-conjunct-never-attempted`

**Date:** 2026-09-29. Written after reward unlock (Commit D). Rule stays frozen in failing form.

---

## 0. Correction notice (2026-09-29, post-outcome)

The Commit D reward join keyed on `(task_id, trial, domain)`. That key is **not unique**:
both agents cover the same `task_id` range, and gpt-4o's trials 0–3 are a subset of
sonnet's 0–7. Because `DEFAULT_FILES` lists the sonnet files last, sonnet's rewards
overwrote **all 660 gpt-4o entries — 33.3% of the corpus was scored against the wrong
agent's outcome.**

How it was caught: §18 of the original report contained a case the classifier makes
impossible — `exchange_delivered_order_items` present in `called_write_tools` while the
state was `NEVER_ATTEMPTED`. Tracing that contradiction rather than filing it as a
"parsing edge case" exposed the collision. The same bad key was used for the §18
trajectory lookup, so the harm-case sample was reading the other agent's trajectory.

**Scope of the defect:** every reward-conditioned figure in this report. It does **not**
touch RC1, the preregistration, the frozen rule, or the pre-outcome firing artifact —
none of which read reward. A1 (volume) is computed without reward and is unchanged at
25.3%.

**What changed on correction:**

| figure | original (corrupt) | corrected |
|--------|--------------------|-----------|
| base reference-fail rate | 37.5% | **40.3%** |
| trajectory lift | 1.090× | **1.165×** |
| task lift | 0.902× | **0.906×** |
| harm rate | 59.1% | **53.1%** |
| counterfactual veto net | −91 | **−31** |
| ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN fail rate | 55.6% | **83.3%** |

**What did not change:** the verdict. RC1 fails A1 on volume alone, and fails both A2 arms
by wide margins under either join. The task-level lift stays below 1.0×. Every qualitative
conclusion in §19–§21 survives; §17's "all states within 5 points of base" does not and is
corrected below.

`scripts/rc1_validation.py` now keys on `(task_id, trial, domain, agent)` and asserts the
join is 1:1, so a recurrence fails loudly instead of silently. Recomputation:
`scripts/rc1_correction.py`. All figures below are the corrected ones.

---

## 1. Name and version

`required-conjunct-never-attempted`, abbreviated **RC1**. This is not a widening of R2.
Preregistration: `docs/required_conjunct_preregistration.md`, committed at `086f0c6` on 2026-09-29.

---

## 2. Commit chain of custody

| commit | content | reward read? |
|--------|---------|-------------|
| `3dc3a85` | Commit A: ingest + frozen RC1 + 56 tests | no |
| `d5d2324` | Commit A2: extractor precision fixes (audit-driven, pre-outcome) | no |
| `8197c5a` | Commit B: label-blind extractor audit — A3 PASSES (28/30) | no |
| `c294eb9` | Commit C: pre-outcome firing artifact (1980 rows, no reward) | no |
| `404174f` | Commit D: reward unlock + validation — RC1 REJECTED | **yes** |
| (this commit) | Post-outcome correction: join key `+agent`; report figures restated | yes |

The rule existed before it was allowed to know whether it was right.

---

## 3. Corpus

`sierra-research/tau-bench`, `historical_trajectories/`, MIT licence.

| file | records | domain | agent |
|------|---------|--------|-------|
| gpt-4o-airline.json | 200 | airline | gpt-4o |
| gpt-4o-retail.json | 460 | retail | gpt-4o |
| sonnet-35-new-airline.json | 400 | airline | sonnet-3.5-new |
| sonnet-35-new-retail.json | 920 | retail | sonnet-3.5-new |
| **total** | **1980** | 2 domains | 2 agents |

165 distinct tasks; 8–12 trials each. Programmatic non-LLM reward (reference outcome).

---

## 4. A3: Extractor precision (preregistered gate ≥27/30)

**Result: PASS. 28/30 correct.**

Label-blind audit of 30 distinct tasks, seed `20260929`, one trajectory per task, stratified
(15 NEVER\_ATTEMPTED / 7 UNRESOLVED / 8 other). Conducted in two passes:

**Pass 1** (pre-A2 patterns) found 3 false positives:

| FP | task | trigger text | wrong extraction | root cause |
|----|------|-------------|-----------------|-----------|
| FP1 | airline 9 | "apply the \$500 certificate to my booking" | `send_certificate` | "apply" was in verb list; applying existing cert to payment ≠ requesting new cert |
| FP2 | airline 42 | "I did purchase insurance for my flight" | `book_reservation` | "purchase" + "flight" matched with "insurance" intervening |
| FP3 | retail 36 | "switch all items to their cheapest options" | `exchange_delivered_order_items` | spec-reduction via "switch" matched the exchange pattern |

Fixed in Commit A2. Final audit results (post-A2):

| judgment | n | cases |
|----------|---|-------|
| CORRECT | 28 | all except 09, 19 |
| MISS (F8, false negative — safe direction) | 1 | case 09: "change them to purple" — pronoun "them" not in item noun list |
| INCORRECT (false positive) | 1 | case 19: cancel extracted from "I'm trying to see if I can cancel or return" — exploratory phrasing, informational filter missed it |

Remaining limitation: the `_INFORMATIONAL_ONLY` filter catches "see if" only at clause start.
"I'm trying to see if I can X" starts with "I'm trying" and escapes the filter. This was not
corrected because 28/30 already passes A3; fixing it would require extending the filter in a
way that risks suppressing genuine obligations.

---

## 5. A1: Volume (preregistered threshold <15%)

**Result: FAIL. 25.3% (501/1980).**

RC1 fires on a quarter of all trajectories — nearly double the preregistered ceiling.

---

## 6. A2: Enrichment — trajectory level (preregistered threshold ≥1.50×)

**Result: FAIL. Lift = 1.165×.**

| | n | reference FAIL | fail rate |
|--|---|---------------|----------|
| All trajectories | 1980 | 797 | 40.3% |
| Fires (NEVER\_ATTEMPTED) | 501 | 235 | 46.9% |

Lift = 46.9% / 40.3% = **1.165×** against a threshold of 1.50×.

---

## 7. A2: Enrichment — task level (preregistered threshold ≥1.25×)

**Result: FAIL. Lift = 0.906× (below 1.0×).**

| | tasks | any reference FAIL | fail rate |
|--|-------|--------------------|----------|
| All 165 tasks | 165 | 135 | 81.8% |
| Fired tasks (≥1 NEVER\_ATTEMPTED) | 112 | 83 | 74.1% |

Lift = 74.1% / 81.8% = **0.906×** — fires are concentrated in tasks that pass more often
than average. RC1 provides no task-level enrichment; the signal is anti-discriminative at
this level.

---

## 8. Verdict

**RC1 REJECTED.** Per preregistration section 13, the rule stays frozen in its failing form.

A1 fails. A2 fails on both the trajectory arm (1.17× < 1.50×) and the task arm (0.91× < 1.25×).
The failure is clean: all three arms (primary / domain / agent) show the same pattern and
none approaches the threshold.

The UNDERPOWERED-REGARDLESS condition does not apply (112 distinct firing tasks ≥ 30).

---

## 9. Harm rate

**53.1%** (266 of 501 fires are on reference-pass trajectories).

More than half of RC1's firings flag trajectories that were evaluated as correct by the
programmatic reference. This is the most consequential quantification from the experiment:
a deployed RC1 would spend the majority of its escalation budget on correct cases.

---

## 10. Counterfactual veto (reported, never applied)

| | n |
|---|---|
| Would have helped (fire on reference fail) | 235 |
| Would have harmed (fire on reference pass) | 266 |
| Net | **−31** |

A hypothetical veto would have produced 31 more harms than helps on this corpus. This
evidence enters the permanent record for any future decision about granting veto authority.
No such decision is made here.

---

## 11. State distribution

| state | n | % | reference fail rate | lift |
|-------|---|---|---------------------|------|
| SUCCESS\_EVIDENCE\_PRESENT | 918 | 46.4% | 38.2% | 0.950× |
| UNRESOLVED | 543 | 27.4% | 36.1% | 0.897× |
| NEVER\_ATTEMPTED (fires) | 501 | 25.3% | 46.9% | 1.165× |
| ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN | 18 | 0.9% | 83.3% | 2.070× |

The ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN state (tool called but returned `Error:`) has by far the
highest fail rate — **83.3%**, lift 2.07× against the 40.3% base. That is the only state in
this table that clears the A2 trajectory threshold RC1 was written to meet, and RC1 is
explicitly not the rule that fires on it. n=18 is far too small to conclude anything; it is
recorded as a candidate for independent future analysis, separate from RC1's mandate.

*(Corrected: the original report put this state at 55.6% / 1.48×. The corrected figure is
substantially stronger, which is a reason to treat it more carefully, not less — a
20-fold-smaller cell than the fires cell is exactly where a small number of mis-joined rows
moves the headline most.)*

---

## 12. UNRESOLVED breakdown by exception clause (preregistration section 4)

| clause | n | % of UNRESOLVED | description |
|--------|---|-----------------|-------------|
| 4.2 | 300 | 55.2% | No parseable obligation (informational request or no user turns) |
| 4.5 | 215 | 39.6% | Ends with handoff (transfer\_to\_human\_agents) |
| 4.4 | 20 | 3.7% | Retraction detected via explicit phrase list |
| low-confidence | 8 | 1.5% | Only low-confidence obligations extracted |

Exception 4.2 dominates: more than half of UNRESOLVED cases are informational trajectories
where no write obligation was stated. This confirms the informational filter is doing work.
Exception 4.5 accounts for 215 cases — proper handoffs are correctly excluded from firing.

---

## 13. By domain

| domain | total | fires | fire% | fail-in-fires | base fail | lift |
|--------|-------|-------|-------|---------------|-----------|------|
| airline | 600 | 150 | 25.0% | 61.3% | 55.3% | 1.108× |
| retail | 1380 | 351 | 25.4% | 40.7% | 33.7% | 1.209× |

Both domains are similar: 25% volume, lift barely above 1.0×. The verb table generalises
equally across catalogues — but generalises equally poorly, not equally well.

---

## 14. By agent

| agent | total | fires | fire% | fail-in-fires | base fail | lift |
|-------|-------|-------|-------|---------------|-----------|------|
| gpt-4o | 660 | 191 | 28.9% | 55.0% | 45.2% | 1.218× |
| sonnet-3.5-new | 1320 | 310 | 23.5% | 41.9% | 37.8% | 1.109× |

This is the arm the join defect destroyed: the original table reported gpt-4o's base fail
rate as 37.0% when it is 45.2%, because gpt-4o rows had been scored with sonnet's rewards.
The corrected split shows gpt-4o is the weaker agent on this corpus (45.2% vs 37.8% base
fail) and that RC1 fires on it slightly more often *and* slightly more informatively
(1.218× vs 1.109×).

Neither agent arm approaches the 1.50× threshold, and the gap between them (0.11×) is small
against the distance to bar (0.28× at best). The direction is now at least coherent —
more errors, more fires — but the rule still does not discriminate usefully on either agent.

---

## 15. Concentration analysis

| category | n | notes |
|----------|---|-------|
| Tasks firing on ALL trials (universal misfire) | 3 | retail 36, 37, 65 — all 0 fail-fires |
| Tasks firing on SOME trials (mixed) | 109 | mean fire fraction 0.37 |
| Tasks that never fire | 53 | 32.1% of all tasks |

The three universal-fire tasks each achieve 0/N fail-fires — they fire exclusively on
reference-pass trajectories. Retail tasks 36 and 37 share the "payment-split-then-item-modify"
pattern (obligation: modify\_pending\_order\_payment extracted; agent resolves via item
modification instead; reference passes). Retail task 65 is the "exchange bookshelf for
camera" task where the item is never delivered and the agent correctly informs the user to
wait — every trial passes, every trial fires (F5 failure mode systematically).

Fire fractions across fired tasks: mean=0.37, median=0.25, stdev=0.29. Fires are not
concentrated in a small set of tasks; they are distributed broadly, which explains why
there is no task-level enrichment.

---

## 16. R2 structural comparison

RC1 and R2 are non-overlapping by construction:

- **R2** fires on trajectories where a write tool was called but returned an Error response
  (environment-blocked execution). State classification: ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN.
- **RC1** fires on trajectories where the relevant write tool class was never called at all
  (NEVER\_ATTEMPTED). These two states are mutually exclusive in the classifier.

Confirmed in data: 0 trajectories are simultaneously NEVER\_ATTEMPTED and
ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN. R2 is not re-run, redefined, or widened.

The ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN arm (n=18, fail rate 55.6%, lift ~1.48×) is noted
as a candidate for independent future analysis, not as an extension of either R2 or RC1.

---

## 17. Evidence-gap hypothesis assessment

The scoping document hypothesised that RC1 (never-attempted) and R3 (success-unverifiable)
might be instances of a unified EVIDENCE\_GAP signal. This hypothesis is not confirmed.

Fail rates by state (base = 40.3%):
- SUCCESS\_EVIDENCE\_PRESENT: 38.2% (slightly below base)
- UNRESOLVED: 36.1% (slightly below base)
- NEVER\_ATTEMPTED: 46.9% (above base)
- ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN: 83.3% (far above base, n=18)

**This assessment is corrected and the conclusion is now stronger, not weaker.** The
original report claimed all four states cluster within 5 points of base; on the corrected
join they do not — the range is 36.1% to 83.3%. But the spread runs the wrong way for the
unification hypothesis. The three large states (n=918, 543, 501) do cluster, within 11
points of each other; the one state that separates cleanly is
ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN, which is the R2 mechanism and not part of the proposed
EVIDENCE\_GAP construct at all.

So: NEVER\_ATTEMPTED and UNRESOLVED — the two states the unification would merge — sit at
46.9% and 36.1%, on *opposite* sides of base. Merging them would dilute the only state with
any enrichment with a state that has none. There is no evidence they jointly capture a
discriminable class of failures, and some evidence they capture opposing ones. The
evidence-gap unification remains a hypothesis and is not built.

---

## 18. F-mode breakdown for harm cases (fires on reference pass)

**This section is fully replaced.** The original sample was drawn through the collided key,
so it was reading a different agent's trajectory than the one whose reward marked it a harm.
That is what produced the "3/15 unclear — exchange tool called but NEVER\_ATTEMPTED"
row, which the classifier makes impossible. Re-drawn at the same seed `20260929` against the
corrected index; full traces in `data/rc1_harm_sample_corrected.json`.

Corrected inspection of 15 pass-fire cases:

| F-mode | description | observed | was |
|--------|-------------|----------|-----|
| **F4** | **Obligation retracted or became impossible** | **9/15** | 3/15 |
| F6 | Indirect/equivalent tool correctly used | 5/15 | 5/15 |
| — | Reference-label error (RC1 was right) | 1/15 | not identified |
| F2/F7, F5, F9, unclear | — | 0/15 | 6/15 |

**The dominant mechanism is F4, not F6. The original report's headline conclusion for this
section is overturned.** F6 was never dominant; it was tied with an artifact.

**F4 (9/15) — the obligation stops being owed mid-conversation.** Three sub-patterns:

- *Forbidden by domain policy* (3): airline 20/7 — "remove the checked bag and refund it";
  the agent explains baggage cannot be removed; user replies "In that case, I'll just take
  the flight change." retail 38/2 — "split the payment with another card"; policy forbids
  it; user pivots to cancelling. retail 57/3 — "refund to my gift card"; policy forbids it;
  user says "I'll keep the order as is."
- *Premise false* (2): retail 69/0 and 69/6 — "I recently **received** a laptop and want to
  return it"; the order is still pending, so return is inapplicable and the agent cancels
  instead. RC1 extracted `return_delivered_order_items` from the user's own incorrect
  account of world state.
- *Plain change of mind* (4): retail 24/3 — "now that I think about it, I might want to keep
  the grill." retail 106/7 — "I suppose I'll wait... could you cancel this exchange request
  for now?" Plus retail 56/2 and airline 1/5, where the user pivots to a different action.

In all nine the agent's behaviour is correct and the reference passes. RC1 fires because the
obligation was extracted from an early user turn and nothing in the frozen rule revisits it.
The frozen retraction phrase list (exception 4.4) caught 20 cases corpus-wide; these nine
show how narrow that list is against real conversational revocation.

**F6 (5/15) — order-state disambiguation.** Real, and exactly as the original report
described it: "exchange" on a *pending* order is done with `modify_pending_order_items`,
while `exchange_delivered_order_items` is for delivered orders; the verb table maps
"exchange" → the delivered tool regardless of state (retail 64/0, 111/5, 86/0, 86/7). One
variant is scope rather than state: retail 63/0, "cancel just the speaker from my order," is
an item-level modification, not an order cancellation.

**Reference-label error (1/15) — retail 106/0.** The reference for this task *requires*
`exchange_delivered_order_items`; the agent called no write tool at all; reward is
nonetheless 1.0. RC1's firing is correct and the reference is wrong. Corpus-wide this
pattern — reference requires a write, agent performs none, reward = 1.0 — occurs **28 times
(1.4% of records, 12 distinct tasks), and RC1 fires on 16 of them.** So roughly 6% of RC1's
266 counted harms are not RC1 errors. This is reported as a bound on reference reliability,
not applied as a correction: even crediting all 16, trajectory lift moves 1.165× → 1.202×,
still far below the 1.50× bar, and A1 is untouched.

**Consequence for the "read the arguments" remedy.** The original report concluded from F6's
apparent dominance that the fix was order-state disambiguation via tool arguments. On the
corrected sample that remedy addresses 5 of 15 harms. The larger share — 9 of 15 — is
conversational obligation revocation, which is not an argument-level problem at all; the
evidence is in the dialogue text the rule already reads, and RC1 simply never re-examines an
obligation after extracting it.

---

## 19. Failure mode analysis

**Why did RC1 fail both A1 and A2?**

**A1 failure (25.3% volume):** The verb table extracts obligations from the user's opening
intent, before the conversation resolves whether the intent was satisfiable. Many extracted
obligations are from tasks that:
- always succeed (3 universal-fire tasks — all false fires)
- involve multi-step conversations where the user first states a general intent, then pivots

The verb table cannot distinguish "I would like to cancel" (definitive) from "I'm trying to
see if I can cancel" (exploratory). It also cannot detect whether the requested action was
eventually rendered unnecessary by the conversation's resolution.

**A2 failure (lift 1.165× traj, 0.906× task):** The fires are not enriched for failures
because the dominant false fire mode — F4, conversational revocation of the obligation — is
distributed across tasks that both pass and fail, and RC1 has no mechanism that revisits an
obligation once extracted.

> **Narrowed 2026-09-29 (post-outcome).** The paragraph that stood here read: *"The
> task-level lift below 1.0× is the most diagnostic finding. It means that the tasks RC1
> fires on are, on average, easier than the tasks it doesn't fire on."* **That inference does
> not hold and is withdrawn.** Two defects:
>
> 1. **The A2-task gate was mathematically unpassable.** 135 of 165 tasks (81.8%) contain at
>    least one failing trial, and a fired task's any-fail rate is capped at 100%, so the
>    maximum achievable A2-task lift on this corpus is **1.2222×** against a preregistered
>    threshold of **1.25×**. No rule of any design could have passed it. Preregistration
>    §5 made the task-level count the *binding* one, so the binding arm of A2 carried no
>    information. This is the repo's recurring lesson-(1) defect — a threshold correctly
>    applied to the wrong quantity, here a denominator that was already saturated.
> 2. **The "easier tasks" reading is an artifact of the saturating any-fail indicator.**
>    Measured with a non-saturating statistic — mean per-task reference-fail *fraction* —
>    fired tasks are **harder**, not easier: 0.463 vs 0.275 for unfired tasks, a 1.682×
>    separation in the expected direction.
>
> RC1's rejection is unaffected: it fails A1 at 25.3% against a 15% ceiling on a metric that
> reads no reward, and fails A2-traj at 1.165× against 1.50×. Two independent grounds, both
> intact. But the task-level arm must be retired from the decision rather than merely
> restated, and the 0.906× figure must not be cited as evidence of anti-discrimination.

**The genuinely diagnostic finding is different, and worse for RC1.** Controlling for task
identity — restricting to the 109 tasks that have both fired and unfired trials, which is
the only informative stratum and the only quantity a production system could act on, since
in deployment you always know which task you are on:

| | fail rate among fired trials | fail rate among unfired trials, same task | within-task lift |
|--|--|--|--|
| RC1 | 50.5% (235/465) | 45.9% (387/843) | **1.101×** |

Almost all of RC1's apparent 1.165× pooled lift is *between*-task variation — it is
detecting which tasks are hard, not which trials failed. Given the task, RC1's firing is
close to uninformative. A signal that only tells you a task is difficult tells a production
escalator nothing it does not already know from that task's historical failure rate.

---

## 20. What this result settles

- RC1, as implemented (verb-table extraction + ACTION_CLASS non-intersection test), does not
  provide a useful escalation signal on this benchmark.
- ~~The A2 failure at the task level (lift < 1.0×) is strong evidence that the mechanism
  cannot discriminate...~~ **Withdrawn — see the narrowing in §19.** The A2-task gate was
  unpassable by construction. The claim it supported is replaced by a stronger one below.
- **RC1's within-task lift is 1.101×.** Controlling for task identity, RC1's firing barely
  moves the failure probability. Its pooled 1.165× is mostly task-difficulty detection, and
  task difficulty is not a quantity an escalator needs a rule to learn.
- The 53.1% harm rate means any deployment of RC1 in escalation mode would spend the
  majority of human-review capacity on correct cases. Roughly 6% of those counted harms are
  reference-label errors rather than RC1 errors (§18); the conclusion survives the
  adjustment.
- The counterfactual veto net −31 means a veto authority would, on balance, overturn correct
  verdicts more often than it would flag incorrect ones.
- **The failure is a representation failure, not an abstraction failure.** Measured against
  an oracle reconstruction of the construct RC1 was written to detect — "a write-tool class
  the reference solution required was never called" — the construct carries 2.079× pooled
  lift and **2.339× within-task**, at 16.3% harm and +227 veto net. RC1 recovers that
  construct at 33.1% precision and 49.3% recall, and that degradation is sufficient to
  destroy the signal. See `docs/rc1_post_outcome_decomposition.md`. This raises the ceiling
  on a successor; it does **not** establish that any production-visible detector can reach
  it, because the oracle reconstruction reads `info.task.actions` and is not deployable.
  Even the oracle fails A1 at 17.0% against the 15% ceiling.
- **R2 is unaffected.** R2 remains exactly as it was; it is not weakened by RC1's failure.
- **The preregistered thresholds held.** No threshold was chosen after seeing a number.

---

## 21. What this result does not settle

- Whether a different extraction mechanism (one that observes order state, models obligation
  conditionality, or uses a language model) could produce a viable signal of the same kind.
  RC1's verb table cannot observe order state; that limitation is not inherent to the concept.
- Whether the F6 failure mode (pending vs. delivered order state) is specific to tau-bench's
  retail domain or is a general property of multi-state tool catalogues.
- Whether the ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN arm (18 cases, 55.6% fail rate, lift ~1.48×)
  constitutes a viable signal in the R2 family. Its sample is too small to conclude.
- Whether RC1 works on non-customer-service agents. The result is valid only for
  tool-calling agents in two 2024-era models on one benchmark.
- Whether RC1 and R3 are structurally related. The evidence-gap unification is not built and
  is not supported or refuted by this data.

---

## 22. Preregistered commitments — status

| commitment | status |
|-----------|--------|
| RC1 will not be modified after any reference-conditioned number is seen | KEPT |
| No second rule added in the same pass | KEPT |
| Thresholds not revised after the fact | KEPT |
| All arms reported regardless of which is more favourable | KEPT |
| R2 not widened, not rerun, not redefined | KEPT |
| No paid inference | KEPT |
| Counterfactual veto computed and reported, never applied | KEPT |
| Rule stays frozen in failing form | ACTIVE |

---

*Report generated 2026-09-29. All metrics reproducible from `scripts/rc1_validation.py`
and `data/rc1_outcome_joined.json`. Artifact chain: Commits A → A2 → B → C → D.*
