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
deterministic rules failed, one passed as an evidence-gap escalation signal, and
one was accepted but underpowered; alternate-judge pairing weakened substantially
under operational analysis; and the static required-conjunct rule failed
fresh-corpus validation despite a 28/30 label-blind extractor audit.

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

- **Evidence-gap escalation (R3):** Evaluator error was 25.6% on the 133 fired
  cases versus 14.4% elsewhere in the 1,260-case held-out arm. This was the
  clearest positive result, but it was an escalation signal rather than a
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
