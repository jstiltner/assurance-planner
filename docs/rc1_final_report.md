# RC1 Final Report: `required-conjunct-never-attempted`

**Date:** 2026-09-29. Written after reward unlock (Commit D). Rule stays frozen in failing form.

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

**Result: FAIL. Lift = 1.090×.**

| | n | reference FAIL | fail rate |
|--|---|---------------|----------|
| All trajectories | 1980 | 743 | 37.5% |
| Fires (NEVER\_ATTEMPTED) | 501 | 205 | 40.9% |

Lift = 40.9% / 37.5% = **1.090×** against a threshold of 1.50×.

---

## 7. A2: Enrichment — task level (preregistered threshold ≥1.25×)

**Result: FAIL. Lift = 0.902× (below 1.0×).**

| | tasks | any reference FAIL | fail rate |
|--|-------|--------------------|----------|
| All 165 tasks | 165 | 116 | 70.3% |
| Fired tasks (≥1 NEVER\_ATTEMPTED) | 112 | 71 | 63.4% |

Lift = 63.4% / 70.3% = **0.902×** — fires are concentrated in tasks that pass more often
than average. RC1 provides no task-level enrichment; the signal is anti-discriminative at
this level.

---

## 8. Verdict

**RC1 REJECTED.** Per preregistration section 13, the rule stays frozen in its failing form.

A1 fails. A2 fails on both the trajectory arm (1.09× < 1.50×) and the task arm (0.90× < 1.25×).
The failure is clean: all three arms (primary / domain / agent) show the same pattern and
none approaches the threshold.

The UNDERPOWERED-REGARDLESS condition does not apply (112 distinct firing tasks ≥ 30).

---

## 9. Harm rate

**59.1%** (296 of 501 fires are on reference-pass trajectories).

More than half of RC1's firings flag trajectories that were evaluated as correct by the
programmatic reference. This is the most consequential quantification from the experiment:
a deployed RC1 would spend the majority of its escalation budget on correct cases.

---

## 10. Counterfactual veto (reported, never applied)

| | n |
|---|---|
| Would have helped (fire on reference fail) | 205 |
| Would have harmed (fire on reference pass) | 296 |
| Net | **−91** |

A hypothetical veto would have produced 91 more harms than helps on this corpus. This
evidence enters the permanent record for any future decision about granting veto authority.
No such decision is made here.

---

## 11. State distribution

| state | n | % | reference fail rate |
|-------|---|---|---------------------|
| SUCCESS\_EVIDENCE\_PRESENT | 918 | 46.4% | 36.5% |
| UNRESOLVED | 543 | 27.4% | 35.5% |
| NEVER\_ATTEMPTED (fires) | 501 | 25.3% | 40.9% |
| ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN | 18 | 0.9% | 55.6% |

The ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN state (tool called but returned Error:) has the highest
fail rate at 55.6%, well above the base rate of 37.5% (lift 1.48×). This is consistent with
the R2 mechanism (environment-blocked execution) and is noted as a candidate for a future
signal, separate from RC1's mandate.

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
| airline | 600 | 150 | 25.0% | 57.3% | 54.2% | 1.058× |
| retail | 1380 | 351 | 25.4% | 33.9% | 30.3% | 1.119× |

Both domains are similar: 25% volume, lift barely above 1.0×. The verb table generalises
equally across catalogues — but generalises equally poorly, not equally well.

---

## 14. By agent

| agent | total | fires | fire% | fail-in-fires | base fail | lift |
|-------|-------|-------|-------|---------------|-----------|------|
| gpt-4o | 660 | 191 | 28.9% | 39.3% | 37.0% | 1.062× |
| sonnet-3.5-new | 1320 | 310 | 23.5% | 41.9% | 37.8% | 1.109× |

Neither agent arm approaches the 1.50× threshold. gpt-4o fires slightly more often (28.9%
vs 23.5%); sonnet fires slightly more enriched, but both are well below bar. The rule does
not appear to have learned any single agent's error pattern.

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

Fail rates by state:
- SUCCESS\_EVIDENCE\_PRESENT: 36.5% (near base)
- NEVER\_ATTEMPTED: 40.9% (barely above base)
- UNRESOLVED: 35.5% (slightly below base)

All four states cluster within 5 percentage points of the base rate of 37.5%. There is no
evidence that NEVER\_ATTEMPTED and UNRESOLVED states are jointly capturing a discriminable
class of failures. The evidence-gap unification remains a hypothesis and is not built.

---

## 18. F-mode breakdown for harm cases (fires on reference pass)

Qualitative inspection of 15 pass-fire cases (random sample, seed `20260929`):

| F-mode | description | observed | notes |
|--------|-------------|----------|-------|
| F6 | Indirect/equivalent tool used | 5/15 | Most common. Agent used `modify_pending_order_items` for items still in pending state where RC1 expected `exchange_delivered_order_items`. Architecturally correct behavior: different order states require different tools. |
| F4 | Obligation retracted / became impossible | 3/15 | User changed mind informally ("I'll keep the grill after all"); soft retraction not in frozen phrase list. Agent correctly did nothing; reference passes. |
| F2/F7 | Agent correctly verified or escalated | 2/15 | One case: agent transferred to human before resolution; transfer not the last action so exception 4.5 did not fire. One case: agent verified state change not needed. |
| F5 | Deferred action | 1/15 | Item not yet delivered; agent correctly informed user to wait. Task passes; RC1 fires on the eventual exchange obligation. |
| F9 | Extractor false positive | 1/15 | Baggage-update obligation extracted from vague "changes to my flight booking" even though agent never modified baggage and task passed without it. |
| Unclear | Requires deeper trace | 3/15 | Anomalous: exchange tool called but NEVER\_ATTEMPTED state; likely a tool-call/response parsing edge case. |

**Dominant mechanism: F6.** The critical insight is architectural: in the tau-bench retail
domain, an "exchange" on a pending order is accomplished with `modify_pending_order_items`,
while `exchange_delivered_order_items` is for delivered orders. The verb table maps "exchange"
→ `exchange_delivered_order_items` regardless of order state. When the agent correctly uses
`modify_pending_order_items` because the order is still pending, RC1 fires — it cannot
observe order state from user text or tool names alone.

This is not a fixable extractor error. It is a structural limitation: order-state disambiguation
requires reading tool arguments or database state, which are I3 inputs that RC1 either lacks
(arguments are not entity-resolved) or that would require oracle-like knowledge.

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

**A2 failure (lift ≈ 1.09× traj, 0.90× task):** The fires are not enriched for failures
because the dominant false fire modes (F4, F5, F6) are uniformly distributed across tasks
that both pass and fail. A task where the agent correctly uses `modify_pending_order_items`
instead of `exchange_delivered_order_items` (F6) passes with the same frequency as tasks
where the wrong tool was used or nothing was done. RC1 cannot distinguish these cases.

The task-level lift below 1.0× is the most diagnostic finding. It means that the tasks RC1
fires on are, on average, *easier* than the tasks it doesn't fire on. RC1 fires heavily on
tasks like "exchange item that's still pending" (always easy, always F6) and misses tasks
where the agent genuinely failed to attempt a required action.

---

## 20. What this result settles

- RC1, as implemented (verb-table extraction + ACTION_CLASS non-intersection test), does not
  provide a useful escalation signal on this benchmark.
- The A2 failure at the task level (lift < 1.0×) is strong evidence that the mechanism —
  observing which tool class was never called — cannot discriminate agent failures from
  legitimate execution paths that use indirect tools or involve retracted obligations.
- The 59.1% harm rate means any deployment of RC1 in escalation mode would spend the
  majority of human-review capacity on correct cases.
- The counterfactual veto net −91 means a veto authority would, on balance, overturn correct
  verdicts more often than it would flag incorrect ones.
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
