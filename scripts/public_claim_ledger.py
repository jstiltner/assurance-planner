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
    # Two figures, because they are two quantities. 46.18 is what the 5,530 deduplicated calls
    # the analysis runs on cost; 49.50 is what the provider billed, including 356 duplicate
    # valid calls that were dropped before analysis and paid for anyway. Until 2026-10-02 only
    # the first existed and it was published as "total API spend", which it is not.
    "rep_cost_usd": 46.18,          # analysed calls only (5,530)
    "rep_billed_cost_usd": 49.50,   # actually billed (5,886 valid calls)
    "rep_duplicate_valid_calls": 356,
    "rep_intermediate_cases": 20,          # k in 1..4 out of 5
    "rep_extreme_fraction_fail": 0.988,    # 98.8% ref-fail at k=0 or k=5
    "rep_extreme_fraction_pass": 0.966,    # 96.6% ref-success at k=0 or k=5
    "rep_k0_fail": 97,
    "rep_k5_fail": 704,
    "rep_k0_pass": 75,
    "rep_k5_pass": 210,
    # Majority-of-5 costs 5,530 calls; first-to-3 USES 3,336 of them; the SAVING is the 2,194 not
    # made.  2,194/5,530 = 39.67%.  Write the saving as 2,194/5,530 and never as 3,336/5,530 --
    # that fraction is 60.3%.
    #
    # This comment claimed until 2026-10-03 that "six documents and the live site printed it
    # beside '39.7%'".  Checked against origin/main: no document ever printed that fraction, and
    # 3,336 appears in exactly one of them.  What propagated was 39.8% -- into five prose
    # documents, three scripts and two site components -- from a hardcoded string in
    # arb_repetition_analysis.py that sat beside the count of calls USED with no denominator, so
    # the inverted fraction is the derivation a reader was left to make rather than one anyone
    # published.  The FORBIDDEN entry below is prophylactic on that basis.  Separately, the value
    # here carried 0.398 from 2026-09 until 2026-10-02, matching that same hardcoded string rather
    # than the saving the function computed.
    "rep_stopping_call_reduction": 0.397,  # 39.7% fewer calls, first-to-3 (2,194 saved of 5,530)
    "rep_stopping_calls": 3336,            # calls USED by first-to-3
    "rep_stopping_calls_saved": 2194,      # calls AVOIDED -- numerator of the saving
    "rep_stopping_calls_full": 5530,       # calls made by majority-of-5 -- denominator
    "rep_stopping_cost_usd": 27.86,
    "rep_config": "gpt-4o-2024-11-20, temperature 0.0, seed 0",

    # AER evaluator pairing — class A (pair selection) + B (analysis)
    "arb_predeclared_recovery": 0.543,
    # POOLED phi. Descriptive context only — do not quote it as the strength of error
    # association without the two stratum values beside it. `arb_conditional_association.py`
    # shows pooled phi orders the eight alternates almost opposite to the failure stratum
    # (1/8 positional agreement) and is close to a restatement of the false-alarm stratum,
    # because the primary's errors are concentrated there (FPR 0.441 vs FNR 0.040). Every
    # claim about "how dependent the evaluators are" that matters for assurance lives on the
    # failure stratum. Added 2026-10-02.
    "arb_predeclared_phi": 0.323,
    "arb_predeclared_failure_phi": 0.250,       # ref-failure stratum, n=811
    "arb_predeclared_failure_or": 9.38,
    "arb_predeclared_failure_rr": 4.93,
    "arb_predeclared_success_phi": 0.310,       # ref-success stratum, n=295
    "arb_predeclared_success_or": 4.17,
    "arb_predeclared_success_rr": 2.78,
    "arb_predeclared_pooled_rr": 3.92,
    # aer leads on pooled phi and is only FOURTH on the failure stratum, behind
    # claude-3.7-sonnet-noscreen (+0.273), gpt-4o-noscreen (+0.260) and llama-3.3-70b-noscreen
    # (+0.251). Its margin over 5th is 0.016 and over 4th is 0.001 — the rank is not meaningful,
    # which is the point: neither is the pooled rank that put it first.
    "arb_failure_phi_rank": 4,
    "arb_failure_phi_rank_of": 8,
    "arb_failure_phi_range": (0.171, 0.273),
    "arb_failure_or_range": (5.076, 11.108),
    "arb_pooled_phi_range": (0.048, 0.323),
    # Not a unique argmax: `gpt-4o-mini-noscreen` (axtree) and `qwen-2.5-vl-noscreen` both score
    # exactly 123/162. Documents that name "the post-hoc best pair" are tie-breaking silently,
    # and the two are not interchangeable — their phi values differ (+0.064 vs +0.091), so which
    # one is named changes the phi reported beside the recovery figure. Corrected 2026-10-02.
    "arb_posthoc_best_recovery": 0.759,        # 123/162, TIED between two alternates
    "arb_posthoc_best_tied_pairs": ("gpt-4o-mini-noscreen (axtree)", "qwen-2.5-vl-noscreen"),
    "arb_posthoc_best_phi": 0.064,
    "arb_operational_overturn_fail": 0.366,    # 15/41
    "arb_operational_overturn_pass": 0.465,    # 73/157
    "arb_missed_failures": 32,
    "arb_false_alarms": 130,
    "arb_n_primary_errors": 162,
    # Direction-matched gap, added 2026-10-02 (scripts/arb_directional.py, data/REAL_arb_directional.csv).
    #
    # The published gap was "20-30 points", from 0.543 minus 0.366 and 0.465. That subtraction
    # crosses error directions: 0.543 is recovery pooled over both strata, while the two overturn
    # precisions are direction-specific. Compared against the direction-matched reference-
    # conditioned quantity, the predeclared pair's gap is ~10 points in both directions, not 20-30:
    #   missed-failure side: catch 0.469 vs overturn-to-fail 0.366  -> 10.3 pp
    #   false-alarm side:    rescue 0.562 vs overturn-to-pass 0.465 ->  9.7 pp
    #
    # The finding survives the correction and the direction split is what makes it survive: the
    # false-alarm-side gap is positive for all eight alternates (9.7 to 46.0 pp), while the
    # missed-failure side ranges -14.7 to +23.1 pp and is NEGATIVE for two of them. "The
    # deployable quantity is lower" is therefore true of false alarms generally and NOT true of
    # missed failures generally. The pooled "20-30 points" concealed a sign change.
    "arb_catch_missed_failure": 0.469,         # 15/32, direction-matched to overturn-to-fail
    "arb_rescue_false_alarm": 0.562,           # 73/130, direction-matched to overturn-to-pass
    "arb_gap_missed_failure_pp": 10.3,
    "arb_gap_false_alarm_pp": 9.7,
    "arb_gap_missed_failure_range_pp": (-14.7, 23.1),
    "arb_gap_false_alarm_range_pp": (9.7, 46.0),
    "arb_gap_missed_failure_negative_for": ("gpt-4o-noscreen", "qwen-2.5-vl-noscreen"),

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
    # Slice conditioning, added 2026-10-02 (scripts/arb_r3_slice_check.py). All 133 firings
    # are visualwebarena, which also carries the highest judge-error point estimate of the four:
    # 22.4%, against 19.8% webarena, 11.1% workarena, 3.9% assistantbench. The pooled pair above
    # is therefore mostly a slice contrast. Quote the pooled numbers ONLY with these beside them.
    #
    # Say "highest point estimate", never "weakest" or "hardest" -- this comment said "the
    # judge's weakest slice" until 2026-10-03, and 22.4 against 19.8 at n=290 and n=373 is a rank
    # and not a separation. All four slices get quoted together wherever the comparison is made:
    # naming only assistantbench and workarena makes a 2.6-point gap look like an 11-point one.
    "r3_fires_visualwebarena": 133,
    "r3_fires_other_slices": 0,
    "r3_within_slice_error_fired": 0.256,    # 34/133
    "r3_within_slice_error_unfired": 0.197,  # 31/157, visualwebarena only
    "r3_within_slice_p": 0.26,               # Fisher exact, two-sided
    "r3_pooled_p": 0.0015,
    "r3_pooled_separation_pp": 11.2,
    "r3_within_slice_separation_pp": 5.8,
    # Direction split of the within-slice residual, added 2026-10-02
    # (scripts/arb_r3_slice_check.py section 6). "Evaluator error" pools two populations a
    # reviewer acts on differently: on reference-fail cases the only available error is a
    # missed failure, on reference-success cases a false alarm. The +5.8 pp residual is not
    # spread across both — it is entirely on the missed-failure side, and the false-alarm
    # side runs slightly the wrong way. Neither stratum reaches significance.
    "r3_vwa_fail_side_error_fired": 0.253,     # 22/87
    "r3_vwa_fail_side_error_unfired": 0.158,   # 18/114
    "r3_vwa_fail_side_separation_pp": 9.5,
    "r3_vwa_fail_side_p": 0.1099,              # Fisher exact, two-sided
    "r3_vwa_success_side_error_fired": 0.261,  # 12/46
    "r3_vwa_success_side_error_unfired": 0.302,  # 13/43
    "r3_vwa_success_side_separation_pp": -4.1,
    "r3_vwa_success_side_p": 0.8139,
    # Quarantine overlap, added 2026-10-02. The held-out split was drawn by case, but the
    # pairing study had already tabulated this judge's correctness on 84.4% of the cases it
    # held out — so "held out" meant unseen by the rule author, not unseen by the project.
    "r3_validation_cases_in_pairing_population": 1064,   # of 1,260
    "r3_validation_cases_outside": 196,
    "r4_lift": 1.20,
    # Class sweep, added 2026-10-02 (scripts/arb_rule_slice_audit.py). Finding the R3 confound
    # and not checking the rest of its class is how the R3 confound got published, so every rule
    # got the same treatment. R3 is the only one of the four whose firings sit in a single slice.
    # R1's escalation half, which makes the same kind of pooled claim, fires across three slices
    # and keeps a positive residual within each -- so it is underpowered, and NOT OBVIOUSLY
    # confounded. That hedge is the correction: until 2026-10-02 this read "not confounded", and
    # three same-signed slices at fired n of 7, 10 and 10 cannot establish the absence of a slice
    # effect. They establish that one was not found at the power available.
    #
    # The arm sizes also have to be stated as two sets. The FIRED arms are small (7 / 10 / 10);
    # the UNFIRED arms they are compared against are 283 / 363 / 458. "Every within-slice arm is
    # n < 20" was written in the synthesis and the site and is false of the comparison arms --
    # a reader takes it to mean the test saw 20 cases, when it saw 290, 373 and 468.
    "r1_fires": 27,
    "r1_slices_firing": 3,
    "r1_fired_arm_sizes": (7, 10, 10),       # visualwebarena / webarena / workarena
    "r1_unfired_arm_sizes": (283, 363, 458),  # same order -- not small
    "r1_escalation_error_fired": 0.333,     # 9/27 pooled
    "r1_escalation_error_unfired": 0.152,   # 187/1232 pooled
    "r1_escalation_pooled_p": 0.0262,
    "r2_slices_firing": 2,
    "r3_slices_firing": 1,                  # the defect
    "r4_fires": 118,
    "r4_slices_firing": 3,

    # RC1 tau-bench — class A/FRESH (corrected)
    "rc1_volume": 0.253,       # 501/1980
    "rc1_volume_n": 501,
    "rc1_n_records": 1980,
    "rc1_traj_lift": 1.165,
    "rc1_within_task_lift": 1.101,
    "rc1_harm_rate": 0.531,    # 53.1%  (266/501)
    # A3's extractor audit. 28/30 is the figure the gate was scored on, and it is not
    # out-of-sample: three of the thirty cases (02, 06, 16) are exactly the ones commit A2 had
    # already repaired before pass 2 scored them. Excluding them leaves 25/27 strictly
    # out-of-sample -- a weaker pass, still a pass. Corrected 2026-10-02 (external reproduction).
    #
    # A3 is also PRECISION ONLY. It asks whether the conjuncts the extractor emitted were right,
    # never whether it missed any, so "the extractor worked" is supported against false positives
    # and says nothing about recall. "The rule failed, not the parsing" therefore holds against
    # false positives alone.
    "rc1_extractor_pass": 28,
    "rc1_extractor_total": 30,
    "rc1_extractor_pass_out_of_sample": 25,
    "rc1_extractor_total_out_of_sample": 27,
    "rc1_extractor_a2_repaired_cases": ("02", "06", "16"),

    # Successor probe — within-task on deployable outcome.
    #
    # These three point estimates are each computed on a DIFFERENT set of tasks, because the
    # within-task filter keeps only tasks where that rule both fires and does not: 94 / 80 /
    # 109. Until 2026-10-02 they were published bare, and the ordering of two of them
    # (1.171 > 1.101) supported the claim that RC1 "fell below a no-model baseline". It does
    # not support it. Paired on the same task resamples, NULL - RC1 = +0.078 [-0.327, +0.575].
    # Quote no ordering between NULL and RC1 without that interval.
    "oracle_within_task_lift": 2.339,
    "null_within_task_lift": 1.171,
    "rc1_within_task_lift_probe": 1.101,   # same as above, cross-checks
    "oracle_within_task_tasks": 94,
    "null_within_task_tasks": 80,
    "rc1_within_task_tasks": 109,
    # Task-level bootstrap, 2,000 resamples, seed 20261002 (scripts/rc1_successor_probe.py)
    "oracle_within_task_lift_ci": (1.927, 2.927),
    "null_within_task_lift_ci": (0.802, 1.652),
    "rc1_within_task_lift_ci": (0.903, 1.360),
    # These two are the MEAN of the 2,000 paired resample differences, which is the figure the
    # synthesis and the site quote. It is not the difference of the two point estimates above:
    # 1.171 - 1.101 = +0.070, and +0.070 vs +0.078 is a third-decimal gap that a reader
    # recomputing from the published lifts will hit and be unable to attribute. Both are now
    # emitted by rc1_successor_probe.py under the keys `mean` and `point`, and prose that quotes
    # +0.078 has to say it is the bootstrap mean. Neither value changes the conclusion: the
    # interval straddles zero either way.
    "null_minus_rc1_lift": 0.078,          # bootstrap mean of the paired differences
    "null_minus_rc1_lift_point": 0.070,    # 1.171 - 1.101, the full-sample difference
    "null_minus_rc1_lift_ci": (-0.327, 0.575),
    # The oracle-vs-null ordering (2.339 vs 1.171) was asserted the same unsound way, on
    # 94 tasks against 80. Unlike NULL - RC1 it survives being done properly, which is why
    # the F9 caveat in the synthesis is still load-bearing.
    "oracle_minus_null_lift": 1.177,
    "oracle_minus_null_lift_ci": (0.721, 1.687),
    # Mantel-Haenszel risk ratio stratified by task, with the task-level CLUSTER bootstrap
    # interval. Greenland-Robins is reported by the script but must not be quoted: it assumes
    # independence within strata that are repeated trials of one task, and is narrow enough to
    # exclude 1 for both NULL and RC1 where the cluster interval does not.
    "mh_oracle_lift": 2.054,
    "mh_oracle_lift_ci": (1.752, 2.530),
    "mh_null_lift": 1.237,
    "mh_null_lift_ci": (0.904, 1.650),
    "mh_rc1_lift": 1.150,
    "mh_rc1_lift_ci": (0.979, 1.352),
    # Further stratified by task AND agent — both NULL and RC1 collapse toward 1.
    "mh_agent_oracle_lift": 1.912,
    "mh_agent_null_lift": 1.090,
    "mh_agent_rc1_lift": 1.054,

    # Process errors. Two populations, counted separately on purpose.
    #
    # The internal triple 13 / 6 / 7 is what the project's own safeguards and audits found, and it
    # is the figure the paper quotes. The external 11 are what an independent end-to-end
    # reproduction found on 2026-10-02 -- ten wrong or over-strong summary figures and protocol
    # descriptions, plus the R3 slice confound. Pooling them into 24 / 6 / 18 reads as though the
    # internal count moved, which it did not: 13 / 6 / 7 is still the correct description of what
    # this repo caught about itself. Any prose quoting the sum must name both parts.
    #
    # BEFORE means caught before the outcomes the error would have affected were visible, which is
    # the only group a safeguard running ahead of the data can claim. All eleven external findings
    # are AFTER by construction -- they were found by reading published output.
    #
    # scripts/check_synthesis_counts.py asserts the internal and external counts separately
    # against the origin column of docs/research_synthesis.md §10.
    "process_errors_internal": 13,
    "process_errors_internal_before": 6,
    "process_errors_internal_after": 7,
    "process_errors_external": 11,
    # Derived. Present because the §10 table has 24 numbered rows and a reader will add them up;
    # never to be quoted without the 13 + 11 breakdown beside it.
    "process_errors_total": 24,
    # "process_errors_before": 6 is the internal before-count and is above under its own name.
    # There is deliberately no pooled "process_errors_after" key. 18 was one, and it was the
    # defect: a single number that silently merged 7 errors this project caught about itself with
    # 11 an outsider caught about it. A key that can only be quoted wrongly should not exist, and
    # FORBIDDEN below rejects the figure in prose. Removed 2026-10-02.
    "process_errors_before": 6,
}

# ---------------------------------------------------------------------------
# MECHANISM DISPOSITIONS  (machine-readable; use for programmatic validation)
# Fields: prereg, frozen_threshold, evaluation_surface, disposition
# disposition values: FAIL | PASS | ACCEPTED_UNDERPOWERED | WEAKENED | INVALID | EXPLORATORY
#                     DIRECTIONAL_FAIL | DIRECTIONAL_MET
#
# DIRECTIONAL_* was added 2026-10-02. R1 and R4 had been recorded with
# frozen_threshold=True and disposition=FAIL, but §7 of repair_validation_preregistration.md
# gives them no accept/reject bar — only a direction (firings more enriched for reference-fail
# than base rate). Against that, R1 inverted and R4 met it. Collapsing "failed a threshold"
# and "came out the wrong way on a direction" into one FAIL inflated the project's own
# negative-result count from 1 gated failure to 3. Only PASS / FAIL / ACCEPTED_UNDERPOWERED
# on a frozen_threshold=True row may be counted in a gated denominator.
#
# These record what the preregistered test returned, not what the result is worth. A
# disposition is therefore fixed once the test has run: re-labelling it later with the benefit
# of an analysis the preregistration did not specify is exactly the post-hoc move this project
# exists to catch. A CONFOUNDED value was briefly added here for R3 on 2026-10-02 and reverted
# the same day for that reason — R3 passed its test, and what the slice check changes is the
# *reading*, which belongs in the `scope` field and in the prose. See §3.3.1 of the synthesis.
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
        "disposition": "WEAKENED",   # no binary gate; 10.3 / 9.7 pp direction-matched gap
        "scope": "AER corpus; operational precision 0.366/0.465 vs reference-conditioned 0.543",
    },
    "M3_R1": {
        "label": "R1 (deterministic pre-check)",
        "prereg": True,
        # Corrected 2026-10-02: was True. §7 declares firing precision against base rate as
        # evidence, with no accept/reject threshold, because R1 changes no verdict.
        "frozen_threshold": False,
        "evaluation_surface": "held_out",
        "disposition": "DIRECTIONAL_FAIL",   # 0.51× — inverted, the §7 no-information case
        "scope": "1,260-case held-out arm; 0.51× lift (37.0% vs 72.4% base rate). "
                 "Withheld-veto counterfactual 6 helped / 14 harmed is post hoc, as is the "
                 "escalation half (33.3% vs 15.2%)",
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
        # The disposition stands: R3 met its preregistered criterion and the test ran as
        # specified. What changed on 2026-10-02 is the reading, and only the reading. The
        # test as specified could not distinguish R3 from a proxy for the highest-error benchmark,
        # because all 133 firings are visualwebarena. The risk was named -- in the post-results
        # caveat in docs/repair_validation_results.md ("Any rule that escalates the cases a judge
        # finds hard will pass a test of the form 'is the judge worse on the escalated subset'...
        # and the preregistration should have said so"), NOT in the preregistration, which is what
        # this comment claimed until 2026-10-02 -- and the check was never run.
        # The old gloss on this line — "clearest positive result" — does not survive; the rule is
        # no longer quotable as a *demonstrated* positive result of the study. Narrowed, not
        # withdrawn: the residual runs in the predicted direction and is merely underpowered.
        "disposition": "PASS",       # 25.6% vs 14.4%; reading narrowed 2026-10-02, see scope
        "scope": "1,260-case held-out arm; 133 fires, ALL visualwebarena; within-benchmark "
                 "25.6% vs 19.7%, Fisher p = 0.26 (+5.8 pp of the +11.2 pp pooled gap). "
                 "Passed a test that, as specified, could not distinguish the rule from a "
                 "proxy for the highest-error environment; within-environment effect unresolved. "
                 "99/133 escalated were already correct",
    },
    "M6_R4": {
        "label": "R4 (deterministic pre-check)",
        "prereg": True,
        "frozen_threshold": False,   # corrected 2026-10-02; see M3_R1 and the header note
        "evaluation_surface": "held_out",
        # Was FAIL. R4 met the only criterion §7 gave it: 1.20× enrichment, above base rate.
        # The REJECTED label was decided afterwards on the evaluator-error contrast, which §7
        # never named, and on application-specificity, which §9 declared in advance. Changing
        # this value is not a post-hoc re-labelling of a test result — the test R4 was actually
        # given returned "met", and the FAIL recorded here was the post-hoc entry.
        "disposition": "DIRECTIONAL_MET",
        "scope": "1,260-case held-out arm; 1.20× lift (87.3% vs 72.4%) MEETS the §7 direction. "
                 "Carries no evaluator-level signal (16.1% vs 15.5%, 0.6 pt, p = 0.89) and is "
                 "application-specific — both true, neither a preregistered criterion",
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
# RULE IDENTITIES
#
# What each rule actually fires on, in the words of its source document. This
# block exists because FORBIDDEN cannot catch a fabricated *description*: a
# paraphrase like "deterministic signal on agent output" contains no banned
# token, cites no superseded number, and reads as competent summary. The
# portfolio case-study page shipped exactly that for R1, R2 and R4 before an
# audit caught it — every number on the page traced to source, but the prose
# around four of them had been written from memory.
#
# The check is therefore positive, not prohibitive: a document that names a
# rule must also contain one of its `discriminators` somewhere. A writer who
# knows what R1 fires on will reach for `report_infeasible` unprompted; one
# working from memory will not.
#
# `source` is authoritative. When a rule's description and this block
# disagree, this block is wrong — fix it here rather than softening the page.
# ---------------------------------------------------------------------------

RULE_IDENTITIES = {
    "R1": {
        "name": "self-contradictory infeasibility claim",
        "fires_on": (
            "the agent calls `report_infeasible` while simultaneously asserting "
            "the task was completed"
        ),
        "discriminators": ["report_infeasible", "infeasib"],
        "fires": "27 of 1,259 (2.1%)",
        "disposition": ("evidence half FAILS ITS DIRECTION (0.51× lift, inverted — the §7 "
                        "no-information case); escalation half survives, post hoc"),
        "care": (
            "6 helped / 14 harmed is a *counterfactual* — R1 was never given veto "
            "power. Say 'had it been a veto'. Its escalation half is real: 33.3% "
            "evaluator error on firings vs 15.2% elsewhere — but post hoc, and the "
            "FIRED arms are 7 / 10 / 10 against unfired arms of 283 / 363 / 458. "
            "Say 'not obviously confounded', never 'not confounded', and never "
            "'every within-slice arm is n < 20' — which this said until 2026-10-02 "
            "and is false of the three arms the firings are compared against. "
            "R1 had NO numeric gate (corrected 2026-10-02). §7 of the "
            "preregistration gave it firing enrichment against base rate as a "
            "direction, no threshold, 'since they change no verdict'. Do not call "
            "this a failed gate; call it a rule whose signal came out inverted."
        ),
        "source": "docs/repair_validation_results.md",
    },
    "R2": {
        "name": "negative self-report on an imperative modification goal",
        "fires_on": (
            "the agent reports it did not accomplish a goal phrased as an "
            "imperative modification"
        ),
        "discriminators": ["self-report", "self report", "imperative"],
        "fires": "13 eligible of 1,259 (1.0%); 6 changed a verdict",
        "disposition": "ACCEPTED and UNDERPOWERED-REGARDLESS, as preregistered",
        "care": (
            "13 eligible and 6 verdict changes are different numbers; n=6 is the "
            "rule-of-three harm-bound denominator (39.3%), not the firing count. "
            "On the other 7 the evaluator had already said FAIL."
        ),
        "source": "docs/repair_validation_results.md",
    },
    "R3": {
        "name": "unverifiable image premise",
        "fires_on": (
            "the goal names an image and the evaluator's input contains no image — "
            "structural and answer-independent"
        ),
        "discriminators": ["image"],
        "fires": "133 of 1,259 (10.6%)",
        "disposition": ("ACCEPTED — both preregistered tests pass, both arms. The *reading* is "
                        "narrowed 2026-10-02, not withdrawn: the within-slice residual stays "
                        "positive (+5.8 pp, p = 0.26), so the claim shrinks rather than inverting. "
                        "The disposition does not move at all"),
        "care": (
            "It concentrates error, it does not correct it: 99 of 133 escalated "
            "cases were already right. The answer-independence of the firing "
            "condition is what keeps the result from being circular — state it. "
            "All 133 firings are visualwebarena, the slice with the highest judge "
            "error. Never quote the pooled pair (25.6% vs 14.4%, p = 0.0015) "
            "without the within-slice pair beside it (25.6% vs 19.7%, p = 0.26). "
            "R3 is unproven, not refuted, and is not quotable as a positive result "
            "of this study."
        ),
        "source": "docs/repair_validation_results.md",
    },
    "R4": {
        "name": "terminal search-results route",
        "fires_on": "the trajectory ends on a search-results page",
        "discriminators": ["search-result", "search result", "search page"],
        "fires": "118 of 1,259 (9.4%)",
        "disposition": ("MEETS ITS DIRECTION (1.20× > base rate). 'REJECTED' is withdrawn "
                        "as post hoc, 2026-10-02"),
        "care": (
            "The 1.20× enrichment for reference-fail is real. It is the "
            "*evaluator*-level signal that is absent: 16.1% vs 15.5%, 0.6 pt, "
            "p = 0.89. R4 tells you about the agent, not the evaluation. "
            "Do NOT write 'R4 was rejected'. R4 had no numeric gate; §7 gave it a "
            "direction, which it met. The REJECTED label was decided afterwards on "
            "the evaluator-error contrast (not a §7 criterion) and on "
            "application-specificity (declared in §9 before the test). The finding "
            "stands; the verdict word does not."
        ),
        "source": "docs/repair_validation_results.md",
    },
    "RC1": {
        "name": "static required-conjunct matching",
        "fires_on": (
            "extract the observable actions a task obliges the agent to perform; "
            "fire if any are absent from the trajectory"
        ),
        "discriminators": ["required-conjunct", "required conjunct", "conjunct", "obligation"],
        "fires": "501 of 1,980 (25.3%)",
        "disposition": "FAIL — A1 and A2-traj both failed on the fresh corpus; A3 passed",
        "care": (
            "The extractor passing (28/30) and the rule failing are separate facts. "
            "A3 is a PRECISION gate with unmeasured recall, and 3 of its 28 passes "
            "(cases 02, 06, 16) are cases the same audit's pass 1 found defective and "
            "Commit A2 fixed before pass 2 scored them -- 25/27 strictly out-of-sample. "
            "So 'the rule failed, not the parsing' holds against false positives only. "
            "The oracle's 2.339× shows the latent construct carries signal; it does "
            "not show a production-valid detector of it exists."
        ),
        "source": "docs/rc1_successor_probe.md, docs/rc1_final_report.md",
    },
    "null rule": {
        "name": "no successful write",
        "fires_on": "the trajectory contains no successful write of any kind",
        "discriminators": ["successful write", "write anything", "wrote anything"],
        "fires": "24.1% volume — fails A1 by construction",
        "disposition": "EXPLORATORY — preregistered as disqualified before computation",
        "care": (
            "It is a floor, not a competitor. Its 1.171× exceeding RC1's 1.101× is "
            "a verdict on RC1, not a proposal to deploy the null rule."
        ),
        "source": "docs/rc1_successor_probe.md",
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
    # Added 2026-10-02, hours after the pooled triple was written. 24 / 6 / 18 is arithmetically
    # right and reads as though the project's own audit had grown to 24. It did not: internal is
    # 13 / 6 / 7 and that is the figure the paper quotes. The sum may be stated with both parts
    # named -- "13 found during the study, 11 more by external reproduction" -- never alone.
    # Spelled-out forms added later the same day: the §18 abstract wrote "Twenty-four process
    # errors ... 18 of them caught only after", and a digits-only pattern read straight past it.
    (r"(?:24|twenty[- ]four) process errors(?!.{0,120}\b(?:13|11|eleven|thirteen)\b)",
     "Pooled process-error count. Give both parts: 13 found during the study "
     "(6 before / 7 after) and 11 more by external reproduction.",
     "ERROR"),
    (r"\b(?:18|eighteen)\b.{0,40}(?:caught )?(?:only )?after",
     "Pooled process-error count. 18 sums the internal 7 and the external 11; report them "
     "separately. There is deliberately no ledger key for this figure.",
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
     "Overclaim. n=4; only R2 and R3 carried numeric gates (one ACCEPTED, one "
     "ACCEPTED-UNDERPOWERED). R1 and R4 were directional: R1 inverted, R4 met its "
     "direction at 1.20x.",
     "WARN"),
    ("obligation tracking does not work",
     "Overclaim. The construct is real (2.339×). The production *detector* failed.",
     "ERROR"),
    ("semantic machinery is useless",
     "Overclaim. Oracle construct 2.339× > null 1.171×.",
     "ERROR"),
    (r"representation failure,? not (?:an )?(?:empty )?abstraction",
     "Struck at canonical freeze. The oracle establishes that the latent construct carries "
     "signal; it does not establish that a production-valid representation of it exists. "
     "The original phrasing lets a reader conclude the abstraction was proven and only the "
     "engineering was unfinished. It was not. See docs/canonical_copy.md.",
     "ERROR"),
    (r"not an empty abstraction",
     "Struck at canonical freeze. See 'representation failure, not abstraction failure'.",
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

    # -----------------------------------------------------------------------
    # Added 2026-10-02 after an external reproduction. Every entry below is a
    # phrase this repository published, not a hypothetical. They are grouped
    # because they share one failure mode: a comparison was summarised in words
    # that asserted more than the comparison supported, and no interval or
    # denominator was carried alongside to contradict it.
    # -----------------------------------------------------------------------
    ("fell below a no-model baseline",
     "Withdrawn. The two lifts sit on DIFFERENT task sets (null 80 tasks, RC1 109) and "
     "NULL - RC1 = +0.078 [-0.327, +0.575] on paired task resamples; neither rule is "
     "distinguishable from 1. Say 'did not outperform'. See docs/rc1_successor_probe.md §1.",
     "ERROR"),
    (r"(?:fell|falls|landed|lands|sits|sat) below (?:a|the) (?:no-model|null)",
     "Withdrawn: see 'fell below a no-model baseline'. No ordering between the null rule "
     "and RC1 is supported in either direction.",
     "ERROR"),
    (r"20.{0,3}30 points",
     "Withdrawn. That gap subtracted two direction-specific overturn precisions from 0.543, "
     "which is recovery POOLED over both error directions. Direction-matched the gap is "
     "10.3 pp (missed-failure) and 9.7 pp (false-alarm). See research_synthesis.md §3.2.1.",
     "ERROR"),
    # Fires on the BARE assertion only. The claim is recoverable with its weighting stated,
    # and the corrected documents state it, so a line that already carries "1.057" or a
    # "weighted/only if" qualifier is making the permitted version of the claim.
    (r"non-positive for all 8(?!.{0,120}(?:1\.057|weight|only if|only at))",
     "Withdrawn as stated. Blanket FAIL adjudication is a raw-count LOSS for only 5 of 8 "
     "pairs; it is non-positive for all 8 only if a missed failure is weighted >= 1.057x a "
     "false alarm. That weighting is defensible but was never declared, so the sentence "
     "reported a value judgement as a measurement.",
     "ERROR"),
    (r"never touched",
     "Overstates blinding. τ-bench was read label-blind during scoping "
     "(required_conjunct_scoping.md §8.4); what was withheld was `reward`/`info`, by code, "
     "until the freeze. Say 'label-blind until the freeze', not 'untouched'.",
     "ERROR"),
    ("clearest positive result",
     "Narrowed 2026-10-02. R3's held-out pass shrinks under conditioning on benchmark: all 133 "
     "firings are visualwebarena, and within VWA the escalation gap goes from 11.2 pp to 5.8 pp "
     "(p = 0.26). The residual is still positive, so the rule is unproven rather than refuted. "
     "The preregistered disposition remains ACCEPTED; the superlative does not survive.",
     "ERROR"),
    ("39.8%",
     "Never correct. The sequential-stopping saving is 39.7% (2,194 saved of 5,530). 39.8% was a "
     "hardcoded string sitting beside the line that computed 39.67% -- not a rounding error, a "
     "literal nobody compared against the computation next to it.",
     "ERROR"),
    # A line may write this fraction in order to reject it -- the anchored lookaheads let it
    # through only if the line either strikes the wording (~~) or states the true value (60.3%)
    # on the same line.  Everything else is asserting a 39.7% saving over the wrong numerator.
    (r"^(?!.*~~)(?!.*60\.3).*3,?336\s*(?:of|/)\s*5,?530",
     "Inverted fraction. 3,336 is the number of calls first-to-3 USES; 3,336/5,530 is 60.3%. The "
     "39.7% saving is the 2,194 calls NOT made: 2,194/5,530. Write '2,194 saved of 5,530' and, if "
     "3,336 is needed, label it as the count used.",
     "ERROR"),
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
