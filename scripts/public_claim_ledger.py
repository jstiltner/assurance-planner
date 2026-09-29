"""
Public-claim ledger for the evaluator-assurance project.

Two roles:
  1. Machine-readable source of truth for canonical numbers and forbidden phrases.
  2. Lint target used by check_public_claims.py against README.md and docs/FINDINGS.md.

Do not edit the FORBIDDEN or CANONICAL blocks without a corresponding correction in
the source document (research_synthesis.md or a correction doc).
"""

# ---------------------------------------------------------------------------
# CANONICAL VALUES  (corrected; used by figure scripts and lint assertions)
# ---------------------------------------------------------------------------

CANONICAL = {
    # Repetition study — class A, preregistered
    "rep_n_cases": 1106,
    "rep_n_fail": 811,
    "rep_n_pass": 295,
    "rep_n_reps": 5,
    "rep_n_calls": 5530,
    "rep_cost_usd": 46.18,
    "rep_intermediate_cases": 20,          # k in 1..4 out of 5
    "rep_extreme_fraction_fail": 0.988,    # 98.8% ref-fail at k=0 or k=5
    "rep_extreme_fraction_pass": 0.966,    # 96.6% ref-success at k=0 or k=5
    "rep_k0_fail": 97,
    "rep_k5_fail": 704,
    "rep_k0_pass": 75,
    "rep_k5_pass": 210,
    "rep_stopping_call_reduction": 0.398,  # 39.8% fewer calls, first-to-3
    "rep_stopping_cost_usd": 27.86,
    "rep_config": "gpt-4o-2024-11-20, temperature 0.0, seed 0",

    # AER evaluator pairing — class A (pair selection) + B (analysis)
    "arb_predeclared_recovery": 0.543,
    "arb_predeclared_phi": 0.323,
    "arb_posthoc_best_recovery": 0.759,
    "arb_posthoc_best_phi": 0.064,
    "arb_operational_overturn_fail": 0.366,    # 15/41
    "arb_operational_overturn_pass": 0.465,    # 73/157
    "arb_missed_failures": 32,
    "arb_false_alarms": 130,
    "arb_n_primary_errors": 162,

    # Held-out rules — class A
    "r1_lift": 0.51,         # REJECTED (inverted)
    "r1_helped": 6,
    "r1_harmed": 14,
    "r2_helped": 6,
    "r2_harmed": 0,
    "r2_lift": 1.06,
    "r2_harm_bound": 0.393,  # rule-of-three at n=6
    "r3_error_fired": 0.256,
    "r3_error_unfired": 0.144,
    "r3_fires": 133,
    "r3_already_correct": 99,
    "r4_lift": 1.20,

    # RC1 tau-bench — class A/FRESH (corrected)
    "rc1_volume": 0.253,       # 501/1980
    "rc1_volume_n": 501,
    "rc1_n_records": 1980,
    "rc1_traj_lift": 1.165,
    "rc1_within_task_lift": 1.101,
    "rc1_harm_rate": 0.531,    # 53.1%  (266/501)
    "rc1_extractor_pass": 28,
    "rc1_extractor_total": 30,

    # Successor probe — within-task on deployable outcome
    "oracle_within_task_lift": 2.339,
    "null_within_task_lift": 1.171,
    "rc1_within_task_lift_probe": 1.101,   # same as above, cross-checks

    # Process errors
    "process_errors_total": 13,
    "process_errors_before": 6,
    "process_errors_after": 7,
}

# ---------------------------------------------------------------------------
# MECHANISM DISPOSITIONS  (machine-readable; use for programmatic validation)
# Fields: prereg, frozen_threshold, evaluation_surface, disposition
# disposition values: FAIL | PASS | ACCEPTED_UNDERPOWERED | WEAKENED | INVALID | EXPLORATORY
# ---------------------------------------------------------------------------

MECHANISM_DISPOSITIONS = {
    "M1_repetition": {
        "label": "Repeated execution (R=5)",
        "prereg": True,
        "frozen_threshold": False,   # outcome taxonomy A–F, not a numeric gate
        "evaluation_surface": "fresh_inference",
        "disposition": "FAIL",       # Outcome C; deployed config only
        "scope": "one judge, one config (gpt-4o-2024-11-20, temp 0.0, seed 0), one corpus",
    },
    "M2_pairing": {
        "label": "Alt-evaluator pairing",
        "prereg": True,              # pair selection predeclared; no recovery threshold
        "frozen_threshold": False,
        "evaluation_surface": "same_corpus",
        "disposition": "WEAKENED",   # no binary gate; 20–30pt operational gap
        "scope": "AER corpus; operational precision 0.366/0.465 vs reference-conditioned 0.543",
    },
    "M3_R1": {
        "label": "R1 (deterministic pre-check)",
        "prereg": True,
        "frozen_threshold": True,
        "evaluation_surface": "held_out",
        "disposition": "FAIL",       # 0.51× inverted; 6 helped / 14 harmed
        "scope": "1,260-case held-out arm",
    },
    "M4_R2": {
        "label": "R2 (deterministic pre-check)",
        "prereg": True,
        "frozen_threshold": True,
        "evaluation_surface": "held_out",
        "disposition": "ACCEPTED_UNDERPOWERED",  # n=6; harm bound 39.3%
        "scope": "1,260-case held-out arm; rule-of-three harm bound 39.3% at n=6",
    },
    "M5_R3": {
        "label": "R3 (evidence-gap escalation)",
        "prereg": True,
        "frozen_threshold": True,
        "evaluation_surface": "held_out",
        "disposition": "PASS",       # 25.6% vs 14.4%; clearest positive result
        "scope": "1,260-case held-out arm; 133 fires; 99/133 already correct",
    },
    "M6_R4": {
        "label": "R4 (deterministic pre-check)",
        "prereg": True,
        "frozen_threshold": True,
        "evaluation_surface": "held_out",
        "disposition": "FAIL",       # 0.6-pt difference; tells about agent not evaluation
        "scope": "1,260-case held-out arm",
    },
    "M7_RC1": {
        "label": "RC1 (static obligation matching)",
        "prereg": True,
        "frozen_threshold": True,    # A1 <15% / A2-traj ≥1.50× / A3 ≥28/30
        "evaluation_surface": "fresh_corpus",
        "disposition": "FAIL",       # A1 FAIL (25.3%), A2-traj FAIL (1.165×), A3 PASS
        "scope": "τ-bench fresh corpus; A2-task gate INVALID (unpassable by construction)",
    },
    "M8_null_rule": {
        "label": "Null rule (no successful write)",
        "prereg": False,             # preregistered as disqualified; never gated
        "frozen_threshold": False,
        "evaluation_surface": "exploratory_recut",
        "disposition": "EXPLORATORY",
        "scope": "τ-bench; 24.1% volume fails A1; exploratory floor only",
    },
}

# ---------------------------------------------------------------------------
# FORBIDDEN PHRASES
# Each entry: (pattern, reason, severity)
# severity: ERROR = must fix before publish, WARN = review carefully
# ---------------------------------------------------------------------------

FORBIDDEN = [
    # Withdrawn arithmetic
    ("four of five",
     "Withdrawn: no enumerated denominator. Use §3.6 disposition table.",
     "ERROR"),
    ("4 of 5",
     "Withdrawn: see 'four of five'.",
     "ERROR"),
    ("sole survivor",
     "Withdrawn: R2 is also ACCEPTED; 'sole survivor' contradicts §2 boundary rule 3.",
     "ERROR"),

    # Nonexistent benchmark fields
    ("task.type label",
     "Does not exist: no task-type column in annotations.csv. Task type is class C, "
     "inferred from goal text.",
     "ERROR"),
    ("task-type label",
     "Does not exist: see 'task.type label'.",
     "ERROR"),
    ("infeasibility flag",
     "Oracle leakage (class D). Its use as a judge input is withdrawn. "
     "See production_signal_audit.md §3.",
     "ERROR"),

    # Collided tau-bench values (replaced by corrected values)
    ("37.5%",
     "Collided-key value. Corrected to 40.3%.",
     "ERROR"),
    ("1.090",
     "Collided-key τ-bench lift. Corrected to 1.165×.",
     "ERROR"),
    ("0.902",
     "Collided-key τ-bench task lift. Corrected to 0.906× (and also INVALID GATE).",
     "ERROR"),
    ("59.1%",
     "Collided-key τ-bench harm rate. Corrected to 53.1%.",
     "ERROR"),
    ("net.*-91",
     "Collided-key τ-bench veto net. Corrected to −31.",
     "ERROR"),
    ("55.6%",
     "Collided-key τ-bench figure. Corrected to 83.3%.",
     "ERROR"),

    # Withdrawn mechanism claims
    ("fired tasks are easier",
     "Withdrawn: saturating indicator inverted the result. "
     "Non-saturating statistic says fired tasks are harder (1.682×).",
     "ERROR"),
    ("7.189",
     "Withdrawn: invalid comparison across two different outcome variables.",
     "ERROR"),
    ("F4.*dominant",
     "Withdrawn: F4 dominant 9/15 was from collided sample. F6 is dominant (~242 firings).",
     "ERROR"),
    ("9.*before.*4.*after",
     "Wrong process-error count. Corrected to 6 before / 7 after.",
     "ERROR"),
    ("nine.*before",
     "Wrong process-error count. Corrected to six before.",
     "ERROR"),

    # Repetition framed as failing a numeric threshold (it had none)
    (r"repetition.{0,40}fail.{0,30}threshold",
     "Overclaim. Repetition study used an outcome taxonomy (A–F), not a numeric pass/fail gate.",
     "ERROR"),
    (r"repetition.{0,40}threshold.{0,40}fail",
     "Overclaim. See 'repetition failed a threshold'.",
     "ERROR"),

    # Evaluator pairing framed as binary fail (it had no recovery threshold)
    (r"evaluator pairing.{0,30}fail",
     "Overclaim. Pairing had no numeric recovery threshold; disposition is WEAKENED, not FAIL.",
     "WARN"),
    (r"alternate.{0,20}judge.{0,30}fail",
     "Overclaim. Alternate-judge pairing has no binary gate; use 'weakened' or name the operational gap.",
     "WARN"),

    # Overclaims
    ("repetition does not work",
     "Overclaim. Scope is one judge (gpt-4o-2024-11-20, temp 0, seed 0), "
     "one corpus, judge stage only.",
     "ERROR"),
    ("repetition doesn.t work",
     "Overclaim. See 'repetition does not work'.",
     "ERROR"),
    ("deterministic checks.*don.t work",
     "Overclaim. n=4; two failed, one ACCEPTED, one ACCEPTED-UNDERPOWERED.",
     "WARN"),
    ("obligation tracking does not work",
     "Overclaim. The construct is real (2.339×). The production *detector* failed.",
     "ERROR"),
    ("semantic machinery is useless",
     "Overclaim. Oracle construct 2.339× > null 1.171×.",
     "ERROR"),

    # Compressing heterogeneous dispositions to a single positive
    ("one positive result",
     "Overclaim. R2 is also ACCEPTED (underpowered); R3 is the clearest pass, not the only positive.",
     "ERROR"),
    ("only positive result",
     "Overclaim. See 'one positive result'.",
     "ERROR"),
    (r"only mechanism.{0,30}surviv",
     "Overclaim. R2 also survived (accepted, underpowered). Use 'clearest pass' or 'cleanest pass'.",
     "ERROR"),
    (r"only mechanism.{0,30}work",
     "Overclaim. See 'only mechanism that survived'.",
     "ERROR"),

    # Misrepresenting dispositions — only flag if R2 is called a failure explicitly
    ("R2.{0,30}(?:was|is|were) (?:a )?fail",
     "R2 is ACCEPTED (preregistered), not failed. Report as underpowered.",
     "WARN"),
    # A2-task specifically (the trajectory gate A2 did genuinely fail; the task gate is INVALID)
    ("A2.task.{0,40}fail",
     "The A2-task gate is INVALID / NON-DECISION-BEARING, not a failure gate that was failed.",
     "WARN"),
    ("15.*shared.unresolved",
     "Only 5 cases meet the strict shared-unresolved definition. "
     "The term applies to 5, not 15.",
     "WARN"),
]

# ---------------------------------------------------------------------------
# REQUIRED SCOPINGS  (claims that MUST carry their scope qualifier)
# ---------------------------------------------------------------------------

REQUIRED_SCOPES = [
    # If you say repetition does/doesn't help, the config must appear nearby
    {
        "trigger": r"repeat\w*.*judg|judg.*repeat",
        "required_near": ["temperature", "temp.*0", "gpt-4o-2024-11-20", "one judge"],
        "message": "Repetition claim must be scoped to the deployed configuration.",
    },
]
