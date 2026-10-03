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

Repeated execution failed for the deployed configuration; of four held-out
deterministic rules only two carried numeric gates — one accepted but underpowered,
one passed as an evidence-gap escalation signal but did not survive conditioning on
benchmark slice — while the other two carried a direction and no threshold (R1
inverted, R4 met its direction); alternate-judge pairing weakened substantially under
operational analysis; and the static required-conjunct rule failed fresh-corpus
validation despite a 28/30 label-blind extractor **precision** audit (25/27 strictly
out-of-sample; recall unmeasured).

## Quantitative bullets

- **Repetition:** Five repeated calls produced intermediate correctness on only 20
  of 1,106 cases (1.8%); majority voting was marginally worse than a single call
  in both error directions, while first-to-3 stopping used 39.7% fewer calls at
  verdicts identical to majority-of-5 **by construction** (the two cannot disagree
  once three of five agree, so only the call saving is empirical; this read
  "reproduced majority-of-5 verdicts exactly" until 2026-10-03). Scope:
  gpt-4o-2024-11-20, temperature 0.0, seed 0, judge stage only.

- **Alternate-judge pairing:** The predeclared pair reached P(alt correct | primary
  wrong) = 0.543 [0.466, 0.618], while operational overturn precision was
  0.366 / 0.465, because the reference-conditioned quantity conditions on a label
  unavailable to the runtime policy. Direction-matched, the gap is **10.3 pp** on the
  missed-failure side (catch 0.469 vs 0.366) and **9.7 pp** on the false-alarm side
  (rescue 0.562 vs 0.465). Across all eight alternates the false-alarm-side gap is
  always positive (9.7–46.0 pp); the missed-failure-side gap ranges −14.7 to +23.1 pp
  and is negative for two. Blanket adjudication on the primary's FAIL verdict is a
  raw-count loss for 5 of 8 alternates, and non-positive for all 8 only if a missed
  failure is weighted ≥ 1.057× a false alarm.

- **Evidence-gap escalation (R3) — reading narrowed 2026-10-02:**
  Evaluator error was 25.6% on the 133 fired cases versus 14.4% elsewhere in the
  1,260-case held-out arm (Fisher p = 0.0015). All 133 firings are visualwebarena,
  the slice with the highest judge error, so the pooled test compares one hard
  benchmark against three easier ones. Within visualwebarena: **25.6% versus
  19.7%, Fisher p = 0.26.** Never quote the pooled pair without the within-slice
  pair beside it. R3's preregistered disposition is unchanged (ACCEPTED) — it met its
  criterion and the test ran as specified; what is narrowed is the reading. R3 is
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

**2026-10-02 — R3's reading narrowed, not withdrawn (post-freeze, external
reproduction):**

An independent reproduction audit asked which benchmarks R3 fires in. All 133
firings are visualwebarena, which also carries the highest judge-error point
estimate of the four slices: 22.4%, against **19.8% on webarena**, 11.1% on
workarena and 3.9% on assistantbench. The preregistered test pooled across
benchmarks, so it compared one slice against the other three rather than escalated
cases against unescalated ones.

~~"the slice where the judge is weakest (22.4% error, against 3.9% on
assistantbench and 11.1% on workarena)"~~ — corrected 2026-10-03. Omitting webarena
turns a 2.6-point gap over the next-highest slice into an apparent 22.4-against-11.1
contrast, and at n = 290 against n = 373 that ordering is not separated. Say
"highest point estimate", never "weakest" or "hardest".

Conditioned on slice: **25.6% vs 19.7%, Fisher p = 0.26**, against **25.6% vs
14.4%, p = 0.0015** pooled. Of +11.2 pp separation, +5.8 pp survives and +5.4 pp
is slice identity. Reproduce with `scripts/arb_r3_slice_check.py`, added in the
same change.

This is the first correction to land after the canonical freeze, and the first
found by someone outside the project. It is a withdrawal, not a retraction: the
within-slice residual runs in the predicted direction and is underpowered rather
than absent, so R3 is unproven. Settling it requires a corpus where the evidence
gap occurs outside a single benchmark.

It narrows a reading, not a disposition. R3's disposition stays ACCEPTED: it met
its preregistered criterion and the test ran as specified. A `CONFOUNDED` disposition
was briefly introduced for it on 2026-10-02 and reverted the same day — downgrading a
disposition on the strength of an analysis the preregistration never named is the
post-hoc move this project exists to catch, whichever direction it points.

The hazard was already written down, though not where this document used to say.
`docs/repair_validation_results.md` says, in a **post-results** caveat: "Any rule
that escalates the cases a judge finds hard will pass a test of the form 'is the
judge worse on the escalated subset'. That test is necessary, not sufficient, and
the preregistration should have said so." The caveat's own last clause is the
point — the preregistration did *not* say so, and the caveat was written after
R3's numbers were in, two paragraphs above *Disposition: ACCEPTED*. (Attribution
corrected 2026-10-02; never cite this sentence to the preregistration.)
`docs/research_synthesis.md` separately records "visualwebarena-only firings" in a
scope column. The two facts sat in different documents and were never joined. The
defence offered at the time — that R3's condition is structural and was frozen
before its error rate was known — is true and does not address the confound:
freezing a rule does not control for a covariate the test never measured.

**2026-10-02 — R1 and R4 never had numeric gates (post-freeze, external
reproduction):**

The headline above said ~~"two of four held-out deterministic rules failed"~~. Section 7
of `docs/repair_validation_preregistration.md` gives R1 and R4 no accept/reject bar at
all — only a direction, firing enrichment above the corpus base rate, *"since they
change no verdict"*. R1 fails that direction (0.51×, inverted). **R4 meets it**
(1.20×). R4's published `REJECTED` disposition was decided afterwards on its
evaluator-error contrast (16.1% vs 15.5%, p = 0.89), a metric the preregistration never
named, and on application-specificity, which §9 declared in advance.

So the gated denominator is **three** (R2, R3, RC1), not five, and the held-out arm
contributes one accepted-but-underpowered rule and one pass rather than two failures.
Reproduce with `scripts/arb_repair_validation.py`; the 3 + 2 split is asserted by
`scripts/check_synthesis_counts.py`.

This is the mirror image of the R3 correction above, and is recorded as such: the
project reverted a post-hoc label that made a result look *worse* within hours of
introducing it, and carried a post-hoc label that made its own negative-result count
look *larger* from the day R4 was evaluated until an outside reader read §7. R4's
substantive finding is unchanged — weak evidence about the agent's outcome, none about
the evaluator, application-specific. Only the verdict word was unearned.

A knock-on: RC1's A2 threshold was justified as sitting *"strictly between this
project's own rejected and accepted precedents"*, with R4's 1.20× as the rejected
endpoint. That endpoint did not exist. The threshold is **not** revised — 1.165× fails
1.50× and 1.20× alike, so nothing turns on it numerically — but the anchor was less
principled than claimed. Noted in `docs/required_conjunct_preregistration.md` §A2.
