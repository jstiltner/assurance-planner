# docs/ — Content Hierarchy

This index classifies every document by its role in the research record.
The tiers follow §13 of [`research_synthesis.md`](research_synthesis.md).

---

## Tier 1 — Read first (research artifact)

| document | what it contains |
|---|---|
| [`research_synthesis.md`](research_synthesis.md) | Full 21-section synthesis; mechanism-disposition table (§3.6); claim ledger with forbidden wordings (§9); process-failure audit (§10); attacks on the thesis (§6) |
| [`repetition_study_findings.md`](repetition_study_findings.md) | R=5 full results — the single strongest empirical result |
| [`agent_reward_bench_directional.md`](agent_reward_bench_directional.md) | Operational vs reference-conditioned decomposition; the most transferable finding |
| [`repair_validation_results.md`](repair_validation_results.md) | R1–R4 held-out sweep with counterfactuals |
| [`rc1_forensic_audit.md`](rc1_forensic_audit.md) | Correction chain for τ-bench collided values; best evidence of rigour |
| [`rc1_successor_probe.md`](rc1_successor_probe.md) | Null-baseline comparison (oracle 2.339× / null 1.171× / RC1 1.101×); branch closure |
| [`FINDINGS.md`](FINDINGS.md) | Public-facing summary: Tier-1 findings, claim-scope table, links |

---

## Tier 2 — Appendix / audit trail (reproducibility, not narrative)

These documents are the preregistration and correction record.
They must be retained; they need not be read to understand the findings.

| document | role |
|---|---|
| [`repetition_study_predeclaration.md`](repetition_study_predeclaration.md) | Preregistration with three amendments (withdrawn gate is evidence, not embarrassment) |
| [`agent_reward_bench_gate1.md`](agent_reward_bench_gate1.md) | AER pair predeclaration and evidence audit |
| [`agent_reward_bench_findings.md`](agent_reward_bench_findings.md) | AER full results |
| [`agent_reward_bench_conditional.md`](agent_reward_bench_conditional.md) | Conditional analysis |
| [`required_conjunct_preregistration.md`](required_conjunct_preregistration.md) | RC1 preregistration and gate definitions |
| [`required_conjunct_scoping.md`](required_conjunct_scoping.md) | RC1 scoping decisions |
| [`rc1_final_report.md`](rc1_final_report.md) | RC1 final report (pre-correction) |
| [`rc1_post_outcome_decomposition.md`](rc1_post_outcome_decomposition.md) | Post-outcome decomposition |
| [`rc1_extractor_audit.md`](rc1_extractor_audit.md) | Extractor 28/30 precision audit |
| [`production_signal_audit.md`](production_signal_audit.md) | Oracle-leakage classification of every rule input |
| [`repair_validation_preregistration.md`](repair_validation_preregistration.md) | R1–R4 preregistration |
| [`shared_unresolved_case_review.md`](shared_unresolved_case_review.md) | 15-case qualitative review (n=15; two key claims superseded in-place) |

---

## Tier 3 — De-emphasize (historical scaffolding)

These documents record design decisions and red-team sessions that preceded
the experiments. They are superseded by the synthesis but preserved for
provenance and the `[REVISED after implementation]` markers.

- [`architecture.md`](architecture.md) — pre-experiment design (46K); §10.1 prior art survives
- [`policy_benchmark_findings.md`](policy_benchmark_findings.md)
- [`real_experiment_protocol.md`](real_experiment_protocol.md)
- [`measurement_review.md`](measurement_review.md)
- [`measurement_red_team.md`](measurement_red_team.md)
- [`experiment_red_team.md`](experiment_red_team.md)
- [`red_team_review.md`](red_team_review.md)
- [`alternate_corpus_red_team.md`](alternate_corpus_red_team.md)
- [`alternate_source_collection_protocol.md`](alternate_source_collection_protocol.md)

---

## Superseded claims (retained in git / in-place corrections only)

The following claims appear in older documents. Each has an in-place
correction block where it originated. **Do not quote these as findings.**
See `docs/research_synthesis.md` §13 and `scripts/public_claim_ledger.py`
for the authoritative withdrawal record.

| withdrawn claim | corrected value / status |
|---|---|
| τ-bench trajectory lift 1.090× | Corrected to 1.165× (join-key collision) |
| τ-bench base fail rate 37.5% | Corrected to 40.3% |
| τ-bench harm rate 59.1% | Corrected to 53.1% |
| τ-bench veto net −91 | Corrected to −31 |
| τ-bench task lift 0.902× | Corrected to 0.906× (and gate is INVALID) |
| τ-bench figure 55.6% | Corrected to 83.3% |
| Null rule 7.189× vs construct 2.339× | Withdrawn — compared different outcome variables |
| "F4 is dominant harm mechanism (9/15)" | Withdrawn — collided sample; F6 is dominant (~242 firings) |
| "Fired tasks are easier" | Withdrawn — saturating indicator inverted the result |
| "Shared unresolved errors" across 15 cases | 5 strict cases, not 15 |
| "Four of five mechanisms failed" / "sole survivor" | Withdrawn — no enumerated denominator; R2 accepted |
| "One positive result" / "only mechanism that survived" | Withdrawn — R2 also accepted (underpowered) |
| AgentRewardBench task-type label | Does not exist; task type is class C, inferred from goal text |
| Infeasibility flag as judge input | Oracle leakage (class D); withdrawn |
