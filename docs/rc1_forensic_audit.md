# RC1 forensic audit

**Scope:** Every tau-bench result and claim that could depend on the faulty reward join,
and every subsequent correction. Correction and integrity verification only.

**Date:** 2026-09-29. Produced after commit `c43cdea`.

**Governing principle:** Before learning from a failed experiment, prove that we know what
actually failed. An oracle can show that a useful construct exists without showing that a
production system can observe it.

---

## 1. Canonical trajectory identity

**Minimal unique key: `(task_id, trial, domain, agent)`.**

The source files carry no stable `trajectory_id` field. The compound key is the minimal
one that is unique.

**Why 3-key is insufficient:**

| domain | gpt-4o task range | sonnet task range | collision |
|--------|------------------|-------------------|-----------|
| airline | task 0–49, trials 0–3 | task 0–49, trials 0–7 | all 200 gpt-4o keys collide |
| retail  | task 0–114, trials 0–3 | task 0–114, trials 0–7 | all 460 gpt-4o keys collide |

3-key produces 1,320 distinct keys for 1,980 records — 660 collisions.

**Verified uniqueness:**

```
source rows            : 1,980
unique 4-keys          : 1,980  ✓ CONFIRMED 1:1
3-key collisions       : 660    CONFIRMED DEFECTIVE
pre-outcome rows       : 1,980  ✓ CONFIRMED 1:1 with source
pre-outcome unique 4-k : 1,980  ✓ CONFIRMED 1:1
joined rows            : 1,980  ✓ CONFIRMED 1:1 with source
```

**Assertions now in `scripts/rc1_validation.py`:**
- Key presence assertion on every raw record before insertion
- `assert key not in raw_by_key, f"duplicate reward key: {key}"`
- `assert len(raw_by_key) == n_raw == len(records)`
- `assert key in raw_by_key` and direct lookup (no `.get()` default) for the join

Any future join violating these fails loudly rather than silently overwriting.

---

## 2. Affected-artifact inventory

| artifact | dependent on reward join? | status |
|----------|--------------------------|--------|
| `scripts/tau_bench_rc1.py` | no | UNAFFECTED — frozen rule, no reward read |
| `scripts/tau_bench_ingest.py` | no | UNAFFECTED — strips outcome fields at load |
| `scripts/test_tau_bench_rc1.py` | no | UNAFFECTED — 56 tests, all pre-outcome |
| `data/rc1_extractor_audit_cases_final.json` | no | UNAFFECTED — label-blind |
| `docs/rc1_extractor_audit.md` | no | UNAFFECTED — 28/30, A3 PASS, no reward |
| `data/rc1_pre_outcome_firings.json` | no | UNAFFECTED — see §3 |
| 501 firing count | no | UNAFFECTED — 25.3% volume |
| 112 distinct tasks fired | no | UNAFFECTED |
| `data/rc1_outcome_joined.json` | **YES** | RECOMPUTED AND CHANGED — regenerated with 4-key |
| base fail rate | **YES** | RECOMPUTED AND CHANGED — 37.5% → 40.3% |
| trajectory lift | **YES** | RECOMPUTED AND CHANGED — 1.090× → 1.165× |
| harm rate | **YES** | RECOMPUTED AND CHANGED — 59.1% → 53.1% |
| veto net | **YES** | RECOMPUTED AND CHANGED — −91 → −31 |
| A2-task lift (0.906×) | YES, and also | INVALID — see §5 |
| ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN fail rate | **YES** | RECOMPUTED AND CHANGED — 55.6% → 83.3% |
| by-agent table | **YES** | RECOMPUTED AND CHANGED — gpt-4o base was 37.0%, now 45.2% |
| by-domain table | **YES** | RECOMPUTED AND CHANGED |
| §18 harm sample in final report | **YES** (wrong agent's traj) | REBUILT — see §8 |
| F4/F6 mechanism distribution | **YES** (both join and method) | CORRECTED — see §8 |
| §17 evidence-gap unification | partially | CORRECTED — direction of NEVER\_ATTEMPTED vs UNRESOLVED changed |
| "fired tasks are easier" claim | via join | WITHDRAWN — see §7 |

---

## 3. Pre-outcome artifact integrity

Every pre-outcome artifact is CONFIRMED UNAFFECTED. Trace:

1. **Oracle boundary:** `tau_bench_ingest.load_file()` strips `reward` and `info` before
   parsing. The resulting `TrajectoryRecord` dataclass has no `reward` or `info` attribute
   by construction. Verified: 0 of 1,980 loaded records carry any outcome field.

2. **RC1 classifier** (`tau_bench_rc1.py`): takes `TrajectoryRecord` objects as input.
   Cannot access reward or info regardless of intent — the attribute does not exist.

3. **Pre-outcome firing artifact** (`data/rc1_pre_outcome_firings.json`):
   - 1,980 rows, unique 4-key
   - No `reward`, `reference_fail`, or `reference_pass` field
   - Agent field set from filename at load time, not from any outcome field
   - 0 unknown-agent rows
   - Firing count 501 is invariant across any join

4. **Extractor audit:** 30 distinct trajectories sampled and inspected without reading
   reward. Judgment was label-blind (§8.4). No contamination possible.

**The reward join bug corrupted Commit D and everything downstream of it.
It did not touch any pre-outcome artifact.**

---

## 4. Independently recomputed corrected metrics

Rebuilt from scratch: raw source → canonical reward map (with uniqueness assertion) →
join with pre-outcome artifact (with match assertion) → computed in a single pass.
None of the prior aggregated tables were used as inputs.

| metric | corrupt value (3-key join) | corrected value | delta |
|--------|---------------------------|-----------------|-------|
| base reference-fail rate | 37.5% | **40.3%** | +2.8 pp |
| trajectory lift | 1.090× | **1.165×** | +0.075 |
| harm rate | 59.1% | **53.1%** | −6.0 pp |
| veto net | −91 | **−31** | +60 |
| A1 volume | 25.3% | **25.3%** | 0 |
| firing count | 501 | **501** | 0 |
| distinct tasks fired | 112 | **112** | 0 |
| ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN fail rate | 55.6% | **83.3%** | +27.7 pp |
| gpt-4o base fail rate | 37.0% | **45.2%** | +8.2 pp |
| gpt-4o trajectory lift | 1.062× | **1.218×** | +0.156 |

Independent reproduction confirms the "hypothesis values" from commit `c43cdea`:
- base fail: 40.3% ✓
- trajectory lift: 1.165× ✓
- harm: 53.1% ✓
- veto net: −31 ✓
- within-task lift: 1.101× ✓

All five reproduce within rounding. No discrepancies found.

---

## 5. The task-level gate: INVALID / NON-DECISION-BEARING

**The preregistered A2-task criterion (`task lift ≥ 1.25×`) was mathematically
unpassable and must be retired as a gate, not merely reported as a failure.**

Proof:
- 135 of 165 tasks (81.8%) contain at least one failing trial.
- A fired task's any-fail rate (the metric used) is bounded above by 100%.
- Maximum achievable lift = 1.000 / 0.818 = **1.2222×**.
- Preregistered threshold = 1.25×.
- 1.2222× < 1.25×. No rule of any design on this corpus could have passed.

**Treatment:**

The historical criterion is preserved. It is marked `INVALID / NON-DECISION-BEARING`
in the preregistration record and this document. The 0.906× value is not cited as
evidence of anti-discrimination; it is withdrawn.

**This does not affect the verdict.** RC1 fails A1 at 25.3% > 15% on a metric that reads
no reward whatsoever, and fails A2-traj at 1.165× < 1.50×. Two independent valid grounds.
The task-level gate would not have changed the outcome had it been passable.

**Design rule:** Before preregistering a lift threshold, compute the maximum value the
metric can take under the corpus's own base rate. If the ceiling is within reach of the
threshold, the gate measures saturation, not signal. Prefer a non-saturating metric such
as mean per-task fail fraction.

---

## 6. RC1's corrected formal disposition

**RC1 REJECTED.**

| gate | criterion | result | value |
|------|-----------|--------|-------|
| A1 volume | < 15% | **FAIL** | 25.3% |
| A2 trajectory lift | ≥ 1.50× | **FAIL** | 1.165× |
| A2 task lift | ≥ 1.25× | **INVALID / NON-DECISION-BEARING** | 0.906× |
| A3 extractor precision | ≥ 27/30 | **PASS** | 28/30 |
| UNDERPOWERED-REGARDLESS | < 30 tasks | not triggered | 112 tasks |

RC1 is rejected on **two valid independent grounds** (A1 and A2-traj). The prior statement
"rejected on all three criteria" is corrected to "rejected on two valid criteria; the third
criterion is retired as non-decision-bearing."

---

## 7. Between-task and within-task analysis

### 7.1 "Fired tasks are easier" — WITHDRAWN

This claim was derived from the 0.906× task lift using the any-fail indicator. The
indicator is saturated (81.8% of tasks already have a failing trial), and the lift
inversion was an artifact of that saturation.

**Corrected descriptive analysis (mean fail fraction, non-saturating):**

| stratum | tasks | mean per-task fail fraction |
|---------|-------|----------------------------|
| all 165 tasks | 165 | 0.403 |
| 112 fired tasks | 112 | **0.463** |
| 53 unfired tasks | 53 | **0.275** |
| between-task lift (fired/all) | — | **1.150×** |

Fired tasks are **harder** on average, not easier. The direction of the original claim is
reversed. Report descriptively; this is not a gate.

### 7.2 Within-task lift — the operationally relevant quantity

In production you always know which task you are on. A deployed escalator cannot act on
between-task lift; it can only ask whether the signal is informative about the current
trial. The operationally relevant measurement conditions on task identity.

Restricted to the 109 tasks with both fired and unfired trials (the only informative
stratum; all-fired tasks carry no within-task contrast):

| | fail rate, fired trials | fail rate, unfired trials, same task | within-task lift |
|--|--|--|--|
| **RC1** | 50.5% (235/465) | 45.9% (387/843) | **1.101×** |

**RC1's within-task lift is 1.101×.** Almost all of its pooled 1.165× is between-task
variation — detecting which tasks tend to fail rather than which trials failed. This is a
sharper indictment than any version of the task-lift figure: it says the signal is nearly
uninformative at the moment of actual decision.

---

## 8. Rebuilt mechanism audit

### 8.1 Provenance of the second correction

The c43cdea decomposition doc (§18) claimed **F4 dominant at 9/15**, overturning the
original F6=5/15 claim. The oracle-grounded mechanism audit (`scripts/rc1_mechanism_audit.py`)
shows this second claim is also wrong.

**Source of the second error:** The decomposition doc classified "user revised their
stated request" as F4 (obligation revocation). In most of those cases the agent correctly
adapted to the revised request and the oracle GT reflects the *final resolution* — not the
initial user statement. The agent's action is correct; RC1 extracted the wrong action class
from the first user turn and never updated it.

### 8.2 Oracle-grounded classification (all 15 harm-sample cases)

Full provenance cards in `data/rc1_mechanism_audit.json`.

| mechanism | oracle basis | n | examples |
|-----------|-------------|---|----------|
| **F6_alt_tool** | oracle GT fully performed; RC1 extracted different action class | **10/15** | 86/0: exchange Fleece Jacket → agent uses `modify_pending_order_items` (correct per oracle); RC1 claimed `exchange_delivered_order_items`. 69/6: user says "return received laptop" → actually pending → agent cancels → oracle GT = cancel ✓ |
| **F4_true_revoc** | oracle GT empty; reference required no write | **2/15** | 24/3: user says cancel grill, then "I'll keep it" → oracle GT = ∅. 57/3: cancel blocked by policy; user accepts → oracle GT = ∅ |
| **construct_mismatch** | oracle requires write, none in traj, reward=1.0 | **3/15** | 64/0, 106/0, 106/7 — see §12 |

**WITHDRAWN from the decomposition doc:**
- "F4 is the dominant mechanism" — wrong; F6 is dominant at 10/15
- "The implied remedy is off 'read tool arguments' and onto dialogue text" — partially wrong; the fix is about the *action class*, not tool arguments

**The underlying failure mode:** RC1 extracts an action class from the first user turn and
never updates it as the conversation reveals the actual resolution. This is an F6 failure
(wrong action class), not an F4 failure (obligation dropped). The action class that the
oracle grades as correct is often different from what the first user turn suggested —
because the conversation is dynamic.

**The revised representation diagnosis:**
The original report focused on order-state disambiguation (pending vs delivered). The
corrected analysis shows the deeper issue: **early extraction locked to first-stated action
class, never updated as conversation evolves.** Order-state is one instance; another is
"user says cancel, conversation reveals modify is appropriate." Reading tool arguments
addresses the first; neither reads tool arguments nor dialogue state tracking alone fully
addresses the second. The full conversation trajectory is required to know what action
class was actually resolved.

This does **not** change the H2a verdict. It changes what kind of representation would be
needed: not "read arguments for order state" but "read the full conversation to determine
the resolved action class."

---

## 9. F4 conversational revocation — evidence

Of the 2 genuine F4 cases (oracle GT = ∅):

**retail 24/3 (gpt-4o):** User says "I was hoping to cancel an order I placed recently.
It's for a grill." Oracle instruction: "you want to cancel the grill, but if the agent
asks you to confirm, you regret and want to keep it." The agent located the grill order;
the user then said "now that I think about it, I might want to keep the grill." The
oracle required no write because the instruction scripted the change of mind. The evidence
for the revocation was in the dialogue text RC1 already reads. RC1 extracted the obligation
from turn 1 and did not process turn 4's revocation.

**retail 57/3 (sonnet-3.5-new):** User asks to cancel an order and refund to gift card.
Policy forbids gift-card refunds. User says "I'll keep the order as is since I can't get
the refund on a gift card." Oracle GT = ∅. The revocation was explicitly stated in the
dialogue. RC1 never re-examines an extracted obligation; this is a stale-obligation failure
not a policy-visibility failure.

**Assessment:** True F4 revocation is rare (2/15 in sample) and both instances have
revocation evidence in the dialogue text RC1 already processes. They represent an
architectural constraint — RC1 extracts once and never revisits — not a representation gap
about new inputs. Any fix would require treating obligation extraction as a dialogue-state
tracking problem rather than a one-pass classification.

---

## 10. Oracle construct analysis

### What `info.task.actions` measures

`info.task.actions` is tau-bench's reference solution: the exact write-tool calls
(with specific order IDs, item IDs, payment methods) that a perfect agent would execute.
This is oracle metadata. It is available to the benchmark's reward function but not to
any deployed agent. It encodes specific entity IDs the agent must look up and a specific
resolution path chosen by the benchmark designer.

**The construct measured by oracle_traj:** "A write-tool class the reference solution
required was never called in the traj." This is the closest oracle reconstruction of RC1's
intended target. It reads the same source (traj) that RC1 reads, using oracle knowledge of
which write classes were required.

**Key limitation:** `info.task.actions` captures **one** acceptable resolution, not all.
The benchmark accepts multiple paths as correct — when the agent takes an alternative path
to the same outcome, `info.task.actions` still lists the reference path, making the
construct appear "never attempted" even if the outcome was achieved. This is the mechanism
behind the 28 ambiguous cases (§12).

### Reproduced oracle figures

| metric | oracle_traj | RC1 (A2 ≥1.50×, A1 <15%) |
|--------|------------|--------------------------|
| volume | 17.0% | — A1 fails at 17.0% |
| trajectory lift | 2.079× | A2 passes at 2.079× |
| within-task lift | **2.339×** | vs RC1's 1.101× |
| harm rate | 16.3% | — |
| veto net | +227 | — |

Figures reproduced from `scripts/rc1_oracle_audit.py`. ✓

### Correct interpretation

**The latent construct is associated with reference failure when measured using
benchmark-authoritative information. The production mechanism is NOT validated.**

The 2.339× within-task ceiling means: if a system could perfectly detect "a required write
class was never executed," it would be strongly informative. RC1 recovers this construct at
33.1% precision / 49.3% recall; that degradation destroys the signal (1.101× within-task).

Two restraints on the ceiling:
1. It was measured with oracle data — it bounds the construct and forecasts nothing about
   any production-visible detector.
2. **Even the oracle fails A1 at 17.0% > 15%.** A perfect detector of this construct would
   still be too expensive to escalate on at the preregistered affordability threshold.

---

## 11. The "118 right-for-the-right-reason" subset

RC1 fires for the right reason — the named class is genuinely missing per oracle — on
**118 of 501 firings (23.6%)**. Those 118 would produce: volume 6.0%, lift 2.02×, +74 net.

**What this is:** an estimate of how much useful signal is mixed into RC1's broad firing
population. It is **not** a rule, not a deployable classifier, and not evidence that these
118 can be isolated in production. The 118 were identified using oracle knowledge of which
write classes were genuinely missing — that knowledge is not available at runtime.

Do not use this subset's performance as evidence for a successor unless a production-visible
detector is frozen and validated on a fresh corpus.

---

## 12. The 28 write/reward ambiguities

**Finding:** 28 retail records (1.4%, 12 distinct tasks) where `info.task.actions`
requires a write, the `traj` field shows no write tool call, and `reward = 1.0`.

**What they are NOT:**
- They are not definitively confirmed benchmark label errors.
- They are not definitively confirmed traj data completeness issues (a `reward_info.actions`
  analysis shows a write appears there, but `reward_info.actions` may record the reference
  path used for DB state comparison, not the agent's actual trace — 331 additional cases
  show the same pattern, making "agent traj is incomplete" unlikely to explain all of them).

**What they likely are:**
These cases appear to involve conditional task instructions ("do X; if X is impossible,
do Y instead"). The oracle GT (`info.task.actions`) records the primary path (X), but the
agent correctly executed the secondary path (Y), and the benchmark scored this as reward=1.0
based on a state check or output check rather than an action match check (evidenced by
`r_actions` being absent in some and present in others, and `r_outputs=1.0` in some).

**Conservative treatment:** Report as a **noise floor / construct-scope mismatch** of
1.4% of records. The oracle construct ("write class required by reference solution was
never called") does not capture all acceptable resolutions for conditional tasks.

**Not subtracted from any metric.** RC1's 266 harms and 1.165× lift stand as computed.
The noise floor tells us: effect sizes smaller than ~1–2 percentage points in harm rate are
inside the corpus's own measurement uncertainty and should not be the basis of conclusions.

---

## 13. H1 / H2 / H3 verdict — corrected

The appropriate verdict is **H2a**, not H2 (as stated in commit c43cdea).

**H2a: RC1's representation is falsified; the broader behavioral evidence-support
construct remains plausible but its deployability is unestablished.**

- **Against H1 (isolated modality):** The construct carries 2.339× within-task on tau-bench,
  a different corpus and modality from R3. It is not modality-bound.
- **Against H3 (too unconstrained):** The construct is strongly predictive when measured
  with oracle data. It is not too unconstrained; it may be too expensive (17.0% volume > 15%
  even at the oracle).
- **For H2a over H2b:** The oracle association establishes existence of signal, not
  deployability. The 2.339× ceiling was measured with `info.task.actions` — specific entity
  IDs, specific resolution paths, specific action arguments. This is not what a production
  evaluator holds. Whether a production-visible representation can close the gap from 1.101×
  to something useful is an open question, not a promising lead. Prefer H2a.

**H2b ("a production-valid mechanism is supported") is not supported.** The evidence
supports the construct's predictiveness, not any particular production implementation of it.

---

## 14. Claims withdrawn or narrowed

| claim | source | disposition |
|-------|--------|-------------|
| "All four states cluster within 5 points of base rate" | §17 final report | **WITHDRAWN** — ATTEMPTED_BUT_SUCCESS_UNKNOWN is 83.3%, far from base |
| "Task lift 0.902× — most diagnostic finding" | §19 final report | **WITHDRAWN** — gate was unpassable, metric was saturated |
| "Fired tasks are easier" | §19 final report | **WITHDRAWN** — direction inverts with non-saturating metric |
| "A2 failure at task level is strong evidence the mechanism cannot discriminate" | §20 final report | **WITHDRAWN** — see §5 and §7.2 |
| "F4 is the dominant harm mechanism (9/15)" | §18 decomp doc (c43cdea) | **WITHDRAWN** — itself an overcorrection from the collided sample |
| "Fix is off 'read tool arguments' and onto dialogue tracking" | §18 decomp doc | **NARROWED** — F6 still dominant; the fix is about action-class resolution, not purely arguments |
| "28 cases are reference label errors" | §6 decomp doc | **NARROWED** — ambiguous; more likely conditional task paths or scope mismatch |
| "RC1 rejected on three criteria" | §8 final report | **NARROWED** — rejected on two valid criteria; third is INVALID |
| H2 (representation failure) | §7 decomp doc | **NARROWED TO H2a** — oracle shows existence, not deployability |
| "Within-task lift 2.339× bounds the construct's value" | §10 this doc | **UPHELD, with a baseline attached** — see §16.1; a no-model null rule reaches only 1.171× on the same outcome, so the construct is real. RC1 itself (1.101×) falls below that null rule |

---

## 15. Clean commit

This document corresponds to the commit that also adds:
- `scripts/rc1_mechanism_audit.py` — oracle-grounded harm-sample classification
- `scripts/rc1_label_audit.py` — 28-case characterization
- Updates to `docs/rc1_post_outcome_decomposition.md` — all withdrawals applied in-place
- `data/rc1_mechanism_audit.json` — full provenance cards

---

## 16. Recommendation: successor-hypothesis work

**Continue only after the following are satisfied:**

1. The full correction chain is committed and the withdrawn claims are recorded in-place
   in the decomposition doc (not just here).
2. The A2-task gate is formally marked INVALID in the preregistration record.
3. The H2a language is propagated to all documents that currently say H2.

**On whether a successor should exist:**

The corrected evidence shows: the construct is predictive (2.339× within-task, oracle) but
even the oracle fails the volume gate. A successor would need to show (a) production-visible
detection and (b) volume under 15% — not as separate conditions but simultaneously, since
better detection is likely to increase volume.

The F6 mechanism (wrong action class due to early extraction) suggests a successor would
need full-conversation action-class resolution, which is a larger scope than a simple
extractor upgrade. Whether such a system produces useful signal is genuinely unknown.

**"No further experiment warranted" remains a valid answer.** A successor should not be
specified unless there is a specific production-visible detection approach that has not been
invalidated by this audit. If one is proposed, it should survive adversarial challenge
against the 12 hard cases from the original brief before being written.

### 16.1 RESOLVED — no successor (`docs/rc1_successor_probe.md`)

The probe was run. A production-visible corrective signal does exist: in 12/12 oracle-confirmed
harm cases, a read response exposed the state field that determines which write class is legal,
before the agent's first write. But that does not rescue the construct.

A **null rule** carrying no obligation model at all — "no successful write anywhere in the
trace" — was benchmarked against RC1 and against the construct. Computed in one code path on
the deployable outcome (reference FAIL), within-task:

| rule | volume | within-task lift |
|---|---|---|
| ORACLE construct | 17.0% | **2.339×** |
| NULL rule (no successful write) | 24.1% | **1.171×** |
| RC1 (production detector) | 25.3% | **1.101×** |

**Consequence for §10: the 2.339× ceiling is UPHELD, not narrowed.** The construct is worth
roughly twice the null rule on the same outcome, so it is not an artefact of trajectories that
did nothing, and H2a stands. **The damaging result is for RC1 itself: it lands below the null
rule (1.101× vs 1.171×).** The extractor also contributes only 0.2 precision points over the
null rule (40.2% → 40.4%), so its measurable effect is volume suppression, not detection.
Supporting evidence: the obligation-derived features (`n_obligations`, `n_unfired_obl`) are
flat across the right-reason/wrong-reason partition, which is instead separated by agent
identity (53.4% vs 33.4% gpt-4o) and is mostly between-task (15 of 127 tasks on both sides).

Note the null rule is not new: `required_conjunct_scoping.md` §6.4 recorded pre-outcome and
label-blind that 22.1% of trajectories contain no write call, and cited that volume as
disqualifying. The probe confirms a preregistered objection.

**Standing addition to the gate set:** any future rule of this family must beat the null
rule on the deployable outcome before its machinery is credited. RC1 would have been rejected
on that criterion alone, at zero inference cost, before A1 or A2 were computed.

---

*Reproduce all quantitative claims: `scripts/rc1_validation.py` (join integrity) →
`scripts/rc1_oracle_audit.py` (§1, §10, §11, §12) → `scripts/rc1_mechanism_audit.py`
(§8) → `scripts/rc1_label_audit.py` (§12) → `scripts/rc1_successor_probe.py` (§16.1).*
