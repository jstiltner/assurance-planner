# RC1 post-outcome decomposition

**Status: post-outcome exploratory.** Every figure here was computed after reward unlock.
Nothing in this document is confirmatory. RC1 is not modified, not rerun in modified form,
and not rescued. Its REJECTED disposition stands on two independent grounds.

**Date:** 2026-09-29. Companion to `docs/rc1_final_report.md` (corrected same day).

---

## 0. Two corrections that had to land before any decomposition

### 0.1 The reward join was keyed on a non-unique key

Commit D joined rewards on `(task_id, trial, domain)`. Both agents cover the same task_ids
and gpt-4o's trials 0–3 are a subset of sonnet's 0–7, so **660 gpt-4o records (33.3% of the
corpus) were scored against sonnet's rewards.** Fixed to `(task_id, trial, domain, agent)`
with a 1:1 assertion in `scripts/rc1_validation.py`. All figures below use the corrected join.

It was caught by chasing a contradiction the original report had filed as "likely a parsing
edge case": a sampled case showed `exchange_delivered_order_items` in `called_write_tools`
while the state was `NEVER_ATTEMPTED`, which the classifier cannot produce. It could not
produce it. The record and the reward were from different agents.

The verdict survived: A1 reads no reward at all, and A2-traj moved 1.090× → 1.165×, still
far below 1.50×.

### 0.2 The binding A2 threshold was mathematically unpassable

Preregistration §5 makes the **task-level** count binding and §11 sets A2-task at ≥1.25×.

- 135 of 165 tasks (81.8%) contain at least one failing trial.
- A fired task's any-fail rate cannot exceed 100%.
- Maximum achievable A2-task lift = 1.0 / 0.818 = **1.2222×**.

**No rule of any design could have passed A2-task on this corpus.** The gate was dead on
arrival, and it was the binding one. This is the repo's recurring lesson-(1) defect — a
threshold correctly applied to a quantity whose denominator was already saturated.

It does not rescue RC1, which fails A1 (25.3% vs 15%, reward-free) and A2-traj
(1.165× vs 1.50×). But the 0.906× task figure must be retired from the decision, not
merely restated — and in particular the original report's reading of it ("the tasks RC1
fires on are *easier*") is withdrawn. On a non-saturating statistic the direction reverses:
mean per-task fail fraction is **0.463 for fired tasks vs 0.275 for unfired** — fired tasks
are *harder*, 1.682×.

**Design rule going forward:** before preregistering a lift threshold, compute the maximum
value the metric can take under the corpus's own base rate. If the ceiling is within reach
of the threshold, the gate is measuring saturation, not signal.

---

## 1. The finding that replaces the task-level inversion

In production you always know which task you are on. Cross-task lift is therefore not an
operable quantity — it is partly a restatement of task difficulty, which a deployed system
already knows from that task's own history. The operable quantity conditions on task identity.

Restricting to the 109 tasks that contain **both** fired and unfired trials (the only
informative stratum):

| | fail rate, fired trials | fail rate, unfired trials of the *same* task | within-task lift |
|--|--|--|--|
| **RC1** | 50.5% (235/465) | 45.9% (387/843) | **1.101×** |

Almost all of RC1's pooled 1.165× is between-task variation. **Given the task, RC1's firing
is close to uninformative.** This is a sharper and more damaging statement than the
task-level inversion it replaces, and unlike that figure it is not an artifact of a
saturated denominator.

---

## 2. Decomposition of the 501 firings

Volume is stable across every partition — RC1 fires on ~25% of everything. It is the
enrichment that varies.

| partition | n | fires | fire % | fail-in-fires | base | lift |
|--|--|--|--|--|--|--|
| all | 1980 | 501 | 25.3% | 46.9% | 40.3% | 1.165× |
| airline | 600 | 150 | 25.0% | 61.3% | 55.3% | 1.108× |
| retail | 1380 | 351 | 25.4% | 40.7% | 33.7% | 1.209× |
| gpt-4o | 660 | 191 | 28.9% | 55.0% | 45.2% | 1.218× |
| sonnet-3.5-new | 1320 | 310 | 23.5% | 41.9% | 37.8% | 1.109× |

No partition approaches 1.50×. The agent split is the one the join defect had destroyed;
corrected, it is at least coherent (gpt-4o is the weaker agent at 45.2% base fail and RC1
fires on it more often and slightly more informatively), but the spread between agents
(0.11×) is small against the distance to bar (0.28× at best).

By attempt-state:

| state | n | % | fail rate | lift |
|--|--|--|--|--|
| SUCCESS\_EVIDENCE\_PRESENT | 918 | 46.4% | 38.2% | 0.950× |
| UNRESOLVED | 543 | 27.4% | 36.1% | 0.897× |
| NEVER\_ATTEMPTED (fires) | 501 | 25.3% | 46.9% | 1.165× |
| ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN | 18 | 0.9% | 83.3% | 2.070× |

The only state that clears 1.50× is the R2 mechanism, at n=18. Noted, not pursued; a cell
that small is exactly where a handful of mis-joined rows moves a headline most, and this
figure already moved from 55.6% to 83.3% on correcting one join.

---

## 3. Is RC1 right for the right reason?

This is the load-bearing question, and it is answerable because tau-bench ships the
reference solution's action list in `info.task.actions`. **That is oracle data.** It is used
here only to audit RC1 after the fact. It is not available to any deployable rule, and
nothing derived from it may be fed back into a successor.

For each firing, compare the tool classes RC1 *claimed* were never attempted against the
write-tool classes the reference solution actually required but the agent never called.

**RC1's 235 true positives (fired, reference failed):**

| | n | % |
|--|--|--|
| **RIGHT reason** — the class RC1 named is genuinely missing | **96** | 40.9% |
| Wrong — every write the reference required *was* performed | 86 | 36.6% |
| Wrong — something was missing, but not what RC1 named | 34 | 14.5% |
| Wrong — the reference required no write at all | 19 | 8.1% |

**RC1's 266 harms (fired, reference passed):**

| | n | % |
|--|--|--|
| Every write the reference required was performed | 156 | 58.6% |
| The reference required no write at all | 74 | 27.8% |
| The class RC1 named is genuinely missing, yet the reference passed | 22 | 8.3% |
| Something missing, but not what RC1 named | 14 | 5.3% |

**RC1 is right for the right reason on 118 of 501 firings — 23.6%.** Three quarters of its
firings are detector errors, not instances of the phenomenon it was written to detect.

And the 118 it gets right are *excellent*:

| RC1 restricted to its right-for-the-right-reason firings | value | gate |
|--|--|--|
| volume | 118/1980 = **6.0%** | A1 <15% — **passes** |
| fail rate among firings | 96/118 = **81.4%** | — |
| trajectory lift | **2.02×** | A2-traj ≥1.50× — **passes** |
| harm rate | 18.6% | — |
| counterfactual veto net | **+74** | — |

This is not a proposal and not a result. It is a diagnosis: **the signal RC1 was aiming at
is present and strong; RC1's 23.6% aim is what destroys it.** 383 wrong-reason firings drag
2.02× down to 1.165×.

---

## 4. The construct measured directly

Define the construct RC1 was written to detect, using the oracle: *a write-tool class the
reference solution required was never called.* 337/1980 = 17.0% of the corpus.

| | RC1 (Level 0, tool-name matching) | the construct, perfectly detected |
|--|--|--|
| volume (A1 <15%) | 25.3% — fail | 17.0% — **fail** |
| trajectory lift (A2 ≥1.50×) | 1.165× — fail | **2.079× — pass** |
| **within-task lift** | **1.101×** | **2.339×** |
| harm rate | 53.1% | 16.3% |
| veto net | −31 | **+227** |
| task lift (A2 ≥1.25×) | 0.906× | 1.053× — fail, but see §0.2: unpassable |

RC1 recovers this construct at **33.1% precision and 49.3% recall**.

Two conclusions, and the second constrains the first:

1. **The abstraction is sound.** "A required action was never attempted" is strongly
   predictive of reference failure — 2.079× pooled, and crucially **2.339× within-task**,
   which is the test that killed RC1. It survives task-identity control. The answer to the
   governing research question is therefore: *RC1 failed because tool-name matching was an
   inadequate representation of the evidence, not because the abstraction is wrong.*

2. **This does not license optimism about a successor.** The ceiling was measured with
   oracle data. `info.task.actions` is the reference solution — specific entity IDs, the
   particular resolution chosen, the exact tool sequence. It is not a task specification a
   production system would hold. The 2.339× is a **ceiling on the construct, not a forecast
   for any detector**, and nothing here shows the gap from 1.101× to 2.339× is bridgeable
   with production-visible inputs. That is an open question, not a promising lead.

   And **even the oracle fails A1** at 17.0% against the 15% ceiling. A perfect detector of
   this construct would still be too expensive to escalate on under this project's own
   affordability threshold.

---

## 5. Where the wrong-reason firings come from

> **Narrowed 2026-09-29 (forensic audit).** The §5 claim that stood here attributed the
> harm-sample F4/F6 distribution as F4=9/15 dominant, F6=5/15. **That claim is withdrawn.**
> It was itself an overcorrection from the first correction pass (commit c43cdea), which
> fixed the collided-key sample but introduced a new error by classifying "user revised
> their stated request" as F4 revocation. Oracle-grounded reclassification
> (`scripts/rc1_mechanism_audit.py`, `data/rc1_mechanism_audit.json`) shows F6 is dominant.
>
> The full corrected mechanism analysis is in `docs/rc1_forensic_audit.md` §§8–9.
> Summary below.

The 383 wrong-reason firings fall into three mechanisms. Oracle-grounded counts use
`info.task.actions` (oracle, undeployable). Harm-sample (15 cases) provides the
qualitative reading.

**(a) Oracle GT fully performed under a different action class — ~242 firings,
F6_alt_tool — 10/15 sampled harms.**

This is **F6**, and it is the dominant mechanism. "Every required write was performed;
RC1 extracted the wrong action class." Two sub-patterns:

- *Order-state mismatch:* "exchange" on a pending order is `modify_pending_order_items`;
  `exchange_delivered_order_items` applies to delivered orders. RC1 maps "exchange" → the
  delivered tool regardless of conversation context.
- *Conversation-evolved action class:* user initially states X ("return this received
  item"), conversation reveals Y is appropriate ("actually still pending, cancel instead"),
  agent correctly executes Y per oracle GT — but RC1 extracted X from turn 1 and never
  updated it.

The second sub-pattern is the larger one and the more diagnostic: **RC1 is locked to the
first-stated action class; the oracle grades the resolved one.** Reading tool arguments
addresses the first sub-pattern (order state). Neither argument-reading nor dialogue-state
tracking alone addresses the second — the full conversation trajectory is required to know
what action class was actually resolved.

**This changes the implied remedy relative to the c43cdea decomposition doc.** That doc
concluded "fix is off 'read tool arguments' and onto dialogue text." The corrected
conclusion is: the fix requires action-class resolution from the full conversation —
substantially broader than either tool arguments or a retraction list.

**(b) Oracle GT empty — ~93 firings, F4_true_revoc — 2/15 sampled harms.**

The reference solution required no write at all. RC1 extracted an obligation from an early
user turn that was never actually owed — plain change of mind (retail 24/3: user keeps
grill) or policy block accepted (retail 57/3: refund to gift card forbidden, user accepts).
F4 is real but rare in the oracle-grounded count, not dominant.

**(c) Something was missing, but not what RC1 named — ~48 firings.**
Partial credit: a genuine gap exists and RC1 pointed at the wrong one.

**(d) 28 ambiguous (traj-incomplete or conditional task path)** — see §6 and §12 of the
forensic audit. These contribute to the harm count; their mechanism is ambiguous.

---

## 6. The 28 ambiguous write/reward cases

Corpus-wide, `info.task.actions` requires a write ∧ traj shows none ∧ reward = 1.0 occurs
**28 times (1.4% of records, 12 distinct tasks, retail only). RC1 fires on 16 of them.**

> **Narrowed 2026-09-29 (forensic audit).** The c43cdea decomposition doc initially called
> these "reference label errors." **That characterisation is withdrawn.** Deeper investigation
> (`scripts/rc1_label_audit.py`) shows all 28 have the write action recorded in
> `reward_info.actions` — but whether `reward_info.actions` is the agent's actual execution
> log or the reference solution's path used for state checking is ambiguous without access
> to tau-bench's scoring source. The `reward_info.actions` vs `traj` divergence is 339
> records (not just 28), confirming a systematic structural difference, not simple traj
> incompleteness.

**Correct characterisation:** These 28 cases are **ambiguous — likely conditional task
paths.** The oracle GT (`info.task.actions`) records the primary resolution; when the
conversation takes a valid alternative path (e.g., agent correctly explains an impossibility
and the benchmark accepts the outcome), reward=1.0 is awarded without the primary action
being executed. The `info.task.actions` construct does not capture all acceptable
resolutions, and the 28 cases are at the boundary of the construct's scope.

**Conservative treatment:** Report as a noise floor / construct-scope boundary.
Do NOT subtract from any metric. Do NOT relabel. Report the noise floor: any future
tau-bench result claiming a lift improvement smaller than ~1–2 percentage points in harm
rate may be within the corpus's own measurement uncertainty.

---

## 7. Verdict on H1 / H2 / H3

The scoping document offered three readings of the R3↔RC1 relationship.

- **H1 — isolated modality phenomenon.** Not supported. The construct carries 2.339×
  within-task on tau-bench, a different corpus, different modality, and different agents
  from R3's. It is not modality-bound.
- **H2a — RC1's representation is falsified; the broader construct remains plausible but
  its deployability is unestablished.** **Supported, and this is the corrected verdict.**
  RC1 and R3 both ask "is there evidence the required thing happened?"; RC1 answered it at
  Level 0 (tool name only) and recovered the underlying construct at 33.1% precision. The
  construct is strongly predictive (2.339× within-task on oracle). But the oracle ceiling
  uses `info.task.actions` — entity-specific, path-specific reference data that no
  production system holds. Whether any production-visible representation closes the gap from
  1.101× to something useful is an open question, not a promising lead.
- **H3 — the abstraction is too unconstrained to be a rule.** Not supported *as stated*, but
  it lands a blow that H2a must absorb: even perfectly detected, the construct fires on 17.0%
  of trajectories and **fails A1**. So the abstraction is not too unconstrained to be
  *predictive*; it may well be too unconstrained to be *affordable*.
- **H2b — a production-valid mechanism is supported.** **Not supported.** Oracle association
  establishes existence of signal, not deployability. Do not advance to H2b without a
  production-visible detector frozen and validated on a fresh corpus.

H2a is retained because the evidence supports it. Its cost is stated plainly: H2a being
right does not imply a successor is worth building, because the measured headroom was
measured with oracle data and even the oracle fails the volume gate.

---

## 8. The evidence-gap unification is not supported

The three large states cluster within 11 points (SUCCESS\_EVIDENCE\_PRESENT 38.2%,
UNRESOLVED 36.1%, NEVER\_ATTEMPTED 46.9%), and the two the unification would merge —
NEVER\_ATTEMPTED and UNRESOLVED — sit on **opposite sides** of the 40.3% base. Merging them
would dilute the only state with any enrichment using a state with none. The one state that
separates cleanly (ATTEMPTED\_BUT\_SUCCESS\_UNKNOWN, 83.3%) is the R2 mechanism and is not
part of the proposed construct at all.

---

## 9. What is still open

Deliberately not settled here:

- Whether any **production-visible** detector closes the gap from 1.101× to the 2.339×
  ceiling. Every input that would obviously help — which tool class the task required,
  whether an order is pending or delivered, whether an obligation was revoked — needs
  classifying as production-available / producible-with-instrumentation / derived / oracle
  before it may appear in a successor. Not done.
- Whether a successor could pass A1, given that the oracle itself does not.
- Whether the F4 mechanism (conversational obligation revocation) is separable from the
  attempt question entirely — it may be a different rule about dialogue state rather than a
  granularity upgrade to this one.
- **Whether any successor should be built at all.** The value-of-information gate has not
  been run, and "no further experiment is warranted" remains an available answer.

**tau-bench is now burned for successors** by the same argument as ARB (lesson 13): the
corpus has been examined in aggregate against known outcomes, including per-case reading of
the reference solutions in §3–§5. Any rule designed after this document is exploratory on
tau-bench and would need a genuinely fresh corpus for a confirmatory run.

---

*Reproduce: `scripts/rc1_validation.py` (corrected join) → `scripts/rc1_correction.py`
(report tables, harm sample) → `scripts/rc1_oracle_audit.py` (§1, §3, §4, §6, the A2-task
ceiling). The oracle audit reads `info.task.actions`; no rule code touches it, and
`tau_bench_ingest.py` still strips every outcome field before RC1 sees a record.*
