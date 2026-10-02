# Canonical External Copy

*Frozen 2026-09-29. Do not edit without a corresponding correction in
`docs/research_synthesis.md` and a new entry in `scripts/public_claim_ledger.py`.*

---

## Project description

Falsification study testing seven evaluator-assurance mechanisms on two real
agentic-trajectory corpora (AgentRewardBench, n=1,106; τ-bench, n=1,980), with
preregistration, held-out validation, fresh-corpus testing, and a full
process-failure audit.

## Headline

Repeated execution failed for the deployed configuration; two of four held-out
deterministic rules failed, one was accepted but underpowered, and the one that
passed as an evidence-gap escalation signal did not survive conditioning on
benchmark slice; alternate-judge pairing weakened substantially under operational
analysis; and the static required-conjunct rule failed fresh-corpus validation
despite a 28/30 label-blind extractor audit.

## Quantitative bullets

- **Repetition:** Five repeated calls produced intermediate correctness on only 20
  of 1,106 cases (1.8%); majority voting was marginally worse than a single call
  in both error directions, while first-to-3 stopping reproduced majority-of-5
  verdicts exactly using 39.8% fewer calls. Scope: gpt-4o-2024-11-20, temperature
  0.0, seed 0, judge stage only.

- **Alternate-judge pairing:** The predeclared pair reached P(alt correct | primary
  wrong) = 0.543 [0.466, 0.618], while operational overturn precision was
  0.366 / 0.465 — a 20–30 point gap because the reference-conditioned quantity
  conditions on a label unavailable to the runtime policy.

- **Evidence-gap escalation (R3) — withdrawn as a positive result 2026-10-02:**
  Evaluator error was 25.6% on the 133 fired cases versus 14.4% elsewhere in the
  1,260-case held-out arm (Fisher p = 0.0015). All 133 firings are visualwebarena,
  the slice with the highest judge error, so the pooled test compares one hard
  benchmark against three easier ones. Within visualwebarena: **25.6% versus
  19.7%, Fisher p = 0.26.** Never quote the pooled pair without the within-slice
  pair beside it. R3's preregistered disposition is unchanged (ACCEPTED) — it met its
  criterion and the test ran as specified; what is withdrawn is the reading. R3 is
  unproven rather than refuted: the residual runs in the predicted direction but is
  underpowered at n=133 vs 157. It was always an escalation signal rather than a
  correction mechanism: 99 of the 133 escalated cases were already correct.

- **Required-conjunct matching (RC1):** On the fresh τ-bench corpus, RC1 failed
  both binding gates: 25.3% firing volume versus a <15% ceiling and 1.165×
  trajectory lift versus a ≥1.50× bar. An oracle reconstruction of the target
  construct reached 2.339× within-task lift, showing that the latent construct
  carried signal that RC1 failed to recover — not that a deployable detector of
  that signal has been established.

---

## Correction notes

**2026-09-29 — two pre-freeze wording corrections:**

1. **Headline counting ambiguity removed.** An earlier draft said "three gated
   mechanisms failed outright" then described RC1 separately — a double-count.
   The headline now names dispositions mechanically without a summary count.

2. **RC1 oracle sentence narrowed.** "Representation failure, not abstraction
   failure" was stronger than the evidence warrants. The oracle establishes that
   the latent construct carries signal; it does not establish that a
   production-valid representation of it exists (H2a from the forensic audit).
   The sentence now reports what was demonstrated: the construct carried signal
   that RC1 failed to recover, not that a deployable detector of it exists.

**2026-10-02 — R3 withdrawn as the positive result (post-freeze, external
reproduction):**

An independent reproduction audit asked which benchmarks R3 fires in. All 133
firings are visualwebarena, which is also the slice where the judge is weakest
(22.4% error, against 3.9% on assistantbench and 11.1% on workarena). The
preregistered test pooled across benchmarks, so it compared one hard slice against
three easier ones rather than escalated cases against unescalated ones.

Conditioned on slice: **25.6% vs 19.7%, Fisher p = 0.26**, against **25.6% vs
14.4%, p = 0.0015** pooled. Of +11.2 pp separation, +5.8 pp survives and +5.4 pp
is slice identity. Reproduce with `scripts/arb_r3_slice_check.py`, added in the
same change.

This is the first correction to land after the canonical freeze, and the first
found by someone outside the project. It is a withdrawal, not a retraction: the
within-slice residual runs in the predicted direction and is underpowered rather
than absent, so R3 is unproven. Settling it requires a corpus where the evidence
gap occurs outside a single benchmark.

It withdraws a reading, not a disposition. R3's disposition stays ACCEPTED: it met
its preregistered criterion and the test ran as specified. A `CONFOUNDED` disposition
was briefly introduced for it on 2026-10-02 and reverted the same day — downgrading a
disposition on the strength of an analysis the preregistration never named is the
post-hoc move this project exists to catch, whichever direction it points.

The hazard was already written down. `docs/repair_validation_preregistration.md`
says "any rule that escalates hard cases passes this test", and
`docs/research_synthesis.md` records "visualwebarena-only firings" in a scope
column. The two facts sat in different documents and were never joined. The
defence offered at the time — that R3's condition is structural and was frozen
before its error rate was known — is true and does not address the confound:
freezing a rule does not control for a covariate the test never measured.
