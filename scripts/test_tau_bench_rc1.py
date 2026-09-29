"""Unit and invariance tests for RC1 and the ingest boundary.

Tests validate the frozen specification (preregistration sections 3-4).
No reward or reference-outcome values are used in any test fixture.

Run:
  python scripts/test_tau_bench_rc1.py
"""

import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tau_bench_ingest import (
    TrajectoryRecord, ToolCall,
    assert_no_outcome_fields, assert_no_outcome_in_record,
    load_file, OUTCOME_FIELDS,
    AIRLINE_WRITE_TOOLS, RETAIL_WRITE_TOOLS, HANDOFF_TOOLS,
)
from tau_bench_rc1 import (
    AttemptState, Obligation, RC1Result,
    extract_obligations, classify_trajectory, run_corpus,
    AIRLINE_PATTERNS, RETAIL_PATTERNS,
)


# ── helpers ────────────────────────────────────────────────────────────────────

def make_record(
    domain="airline",
    user_turns=("I need to cancel my flight.",),
    tool_calls=(),
    task_id=1,
    trial=0,
    agent="test-agent",
    ends_with_handoff=False,
    has_terminal_assistant_turn=True,
    n_turns=6,
):
    """Build a minimal TrajectoryRecord without any outcome field."""
    called = frozenset(tc.name for tc in tool_calls)
    return TrajectoryRecord(
        task_id=task_id,
        trial=trial,
        domain=domain,
        agent=agent,
        user_turns=tuple(user_turns),
        tool_calls=tuple(tool_calls),
        called_tool_names=called,
        ends_with_handoff=ends_with_handoff,
        has_terminal_assistant_turn=has_terminal_assistant_turn,
        n_turns=n_turns,
    )


def make_tc(name, args="{}", response='{"status": "ok"}', step=0):
    return ToolCall(name=name, args_str=args, response=response, step_index=step)


def make_error_tc(name, args="{}", step=0):
    return ToolCall(name=name, args_str=args, response="Error: not found", step_index=step)


PASS = []
FAIL = []


def test(name, condition, msg=""):
    if condition:
        PASS.append(name)
    else:
        FAIL.append(f"{name}: {msg}")


# ── oracle boundary tests ──────────────────────────────────────────────────────

def test_oracle_boundary():
    """assert_no_outcome_fields raises on reward and info."""
    for bad_field in ("reward", "info", "trajectory_success", "reference_label"):
        try:
            assert_no_outcome_fields({bad_field: 1.0})
            test(f"oracle_boundary/{bad_field}", False,
                 "should have raised AssertionError")
        except AssertionError:
            test(f"oracle_boundary/{bad_field}", True)

    # Clean record passes.
    try:
        assert_no_outcome_fields({"task_id": 0, "traj": []})
        test("oracle_boundary/clean_passes", True)
    except AssertionError:
        test("oracle_boundary/clean_passes", False, "raised on clean record")


def test_trajectory_record_has_no_outcome_fields():
    """TrajectoryRecord type contains no reward attribute."""
    r = make_record()
    try:
        assert_no_outcome_in_record(r)
        test("record_no_outcome_fields", True)
    except AssertionError as e:
        test("record_no_outcome_fields", False, str(e))

    test("record_no_reward_attr", not hasattr(r, "reward"))
    test("record_no_info_attr", not hasattr(r, "info"))


def test_load_file_drops_outcome():
    """load_file silently strips reward and info; the resulting record has no outcome attrs."""
    record_with_outcome = {
        "task_id": 0, "trial": 0,
        "traj": [],
        "reward": 1.0,   # stripped at load time, not rejected
        "info": {"some": "data"},
    }
    with tempfile.NamedTemporaryFile(
        suffix="-airline.json", mode="w", delete=False, encoding="utf-8"
    ) as f:
        json.dump([record_with_outcome], f)
        fname = f.name
    try:
        records = load_file(fname)
        test("load_file_accepts_without_raise", len(records) == 1)
        r = records[0]
        test("load_file_drops_reward_attr", not hasattr(r, "reward"))
        test("load_file_drops_info_attr", not hasattr(r, "info"))
    finally:
        os.unlink(fname)


# ── extraction tests ───────────────────────────────────────────────────────────

def test_cancel_flight_extracted():
    """'Cancel my flight' generates cancel_reservation obligation."""
    r = make_record(domain="airline", user_turns=("I need to cancel my flight.",))
    obs = extract_obligations(r)
    test("extract/cancel_flight",
         any("cancel_reservation" in ob.action_class for ob in obs),
         f"got: {obs}")


def test_book_flight_extracted():
    """'Book a flight' generates book_reservation obligation."""
    r = make_record(domain="airline",
                    user_turns=("Hi! I would like to book a flight to Seattle.",))
    obs = extract_obligations(r)
    test("extract/book_flight",
         any("book_reservation" in ob.action_class for ob in obs),
         f"got: {obs}")


def test_change_flight_extracted():
    """'Change my return flight' generates update_reservation_flights."""
    r = make_record(domain="airline",
                    user_turns=("I need to change my return flight from Texas to Newark.",))
    obs = extract_obligations(r)
    test("extract/change_flight",
         any("update_reservation_flights" in ob.action_class for ob in obs),
         f"got: {obs}")


def test_upgrade_to_business_extracted():
    """'Upgrade to business class' generates update_reservation_flights."""
    r = make_record(domain="airline",
                    user_turns=("I'd like to upgrade my tickets to business class.",))
    obs = extract_obligations(r)
    test("extract/upgrade_to_business",
         any("update_reservation_flights" in ob.action_class for ob in obs),
         f"got: {obs}")


def test_remove_passenger_extracted():
    """'Remove a passenger' generates update_reservation_passengers."""
    r = make_record(domain="airline",
                    user_turns=("Hi! I need to remove a passenger named Sophia from my flight.",))
    obs = extract_obligations(r)
    test("extract/remove_passenger",
         any("update_reservation_passengers" in ob.action_class for ob in obs),
         f"got: {obs}")


def test_return_item_extracted():
    """'Return items' generates return_delivered_order_items."""
    r = make_record(domain="retail",
                    user_turns=("I'd like to return an air purifier and a vacuum cleaner.",))
    obs = extract_obligations(r)
    test("extract/return_item",
         any("return_delivered_order_items" in ob.action_class for ob in obs),
         f"got: {obs}")


def test_exchange_item_extracted():
    """'Exchange items' generates exchange_delivered_order_items."""
    r = make_record(domain="retail",
                    user_turns=("I'd like to exchange a couple of items I received.",))
    obs = extract_obligations(r)
    test("extract/exchange_item",
         any("exchange_delivered_order_items" in ob.action_class for ob in obs),
         f"got: {obs}")


def test_cancel_order_extracted():
    """'Cancel order' generates cancel_pending_order."""
    r = make_record(domain="retail",
                    user_turns=("I need to cancel an order for a grill I placed recently.",))
    obs = extract_obligations(r)
    test("extract/cancel_order",
         any("cancel_pending_order" in ob.action_class for ob in obs),
         f"got: {obs}")


def test_change_address_extracted():
    """'Change my address' generates address-modification obligation."""
    r = make_record(domain="retail",
                    user_turns=("I need to update the delivery address for my order.",))
    obs = extract_obligations(r)
    addr_tools = {"modify_pending_order_address", "modify_user_address"}
    test("extract/change_address",
         any(ob.action_class & addr_tools for ob in obs),
         f"got: {obs}")


def test_informational_only_not_extracted():
    """'How many t-shirts do you have?' generates no obligation."""
    r = make_record(domain="retail",
                    user_turns=("How many t-shirt options are available?",))
    obs = extract_obligations(r)
    test("extract/informational_none", len(obs) == 0, f"got: {obs}")


def test_gift_card_balance_not_extracted():
    """'Tell me my gift card balance' generates no obligation."""
    r = make_record(domain="airline",
                    user_turns=("Could you please tell me the sum of my gift card balances?",))
    obs = extract_obligations(r)
    test("extract/gift_card_balance_none", len(obs) == 0, f"got: {obs}")


def test_multiple_conjuncts_extracted():
    """'Cancel pending orders AND return an item' generates two obligations."""
    r = make_record(domain="retail",
                    user_turns=("I need to cancel a few pending orders and return an item.",))
    obs = extract_obligations(r)
    has_cancel = any("cancel_pending_order" in ob.action_class for ob in obs)
    has_return = any("return_delivered_order_items" in ob.action_class for ob in obs)
    test("extract/multiple_conjuncts_cancel", has_cancel, f"got: {obs}")
    test("extract/multiple_conjuncts_return", has_return, f"got: {obs}")


def test_object_phrase_retained_verbatim():
    """Object phrase is kept verbatim and is not an entity id."""
    r = make_record(domain="retail",
                    user_turns=("I need to cancel my order for a grill.",))
    obs = extract_obligations(r)
    if obs:
        test("extract/object_phrase_not_id",
             not obs[0].object_phrase.startswith("#"),
             f"object_phrase={obs[0].object_phrase!r}")
    else:
        test("extract/object_phrase_not_id", False, "no obligation extracted")


# ── four-state classifier tests ────────────────────────────────────────────────

def test_cancel_no_call_is_never_attempted():
    """Cancel obligation + no cancel_reservation call -> NEVER_ATTEMPTED."""
    r = make_record(
        domain="airline",
        user_turns=("I need to cancel my flights under reservation ID SI5UKW.",),
        tool_calls=(make_tc("get_reservation_details"),),
    )
    result = classify_trajectory(r)
    test("classify/cancel_no_call",
         result.state == AttemptState.NEVER_ATTEMPTED, f"state={result.state}")
    test("classify/cancel_no_call_fires", result.fires)


def test_cancel_with_call_is_not_never_attempted():
    """Cancel obligation + cancel_reservation call -> not NEVER_ATTEMPTED."""
    r = make_record(
        domain="airline",
        user_turns=("I need to cancel my flight.",),
        tool_calls=(
            make_tc("get_reservation_details"),
            make_tc("cancel_reservation"),
        ),
    )
    result = classify_trajectory(r)
    test("classify/cancel_with_call_not_fire",
         not result.fires, f"state={result.state}")
    test("classify/cancel_with_call_state",
         result.state == AttemptState.SUCCESS_EVIDENCE_PRESENT,
         f"state={result.state}")


def test_cancel_with_failed_call_is_attempted_unknown():
    """Cancel obligation + error response -> ATTEMPTED_BUT_SUCCESS_UNKNOWN."""
    r = make_record(
        domain="airline",
        user_turns=("I need to cancel my flight.",),
        tool_calls=(make_error_tc("cancel_reservation"),),
    )
    result = classify_trajectory(r)
    test("classify/cancel_error_call",
         result.state == AttemptState.ATTEMPTED_BUT_SUCCESS_UNKNOWN,
         f"state={result.state}")
    test("classify/cancel_error_call_not_fire", not result.fires)


def test_informational_request_is_unresolved():
    """Pure informational request -> UNRESOLVED (no obligation extracted)."""
    r = make_record(
        domain="retail",
        user_turns=("How many t-shirts do you have in stock?",),
        tool_calls=(make_tc("list_all_product_types"),),
    )
    result = classify_trajectory(r)
    test("classify/informational_unresolved",
         result.state == AttemptState.UNRESOLVED, f"state={result.state}")
    test("classify/informational_not_fire", not result.fires)


def test_mixed_request_partial():
    """Return obligation + exchange call but NO return call -> fires for return."""
    r = make_record(
        domain="retail",
        user_turns=("I need to return an air purifier and exchange a vacuum cleaner.",),
        tool_calls=(
            make_tc("exchange_delivered_order_items"),
        ),
    )
    result = classify_trajectory(r)
    test("classify/mixed_partial_fires", result.fires,
         f"state={result.state} reason={result.reason}")


def test_conditional_request_informational_only():
    """
    'Let me know if the address can be updated' -- informational form.
    No clear imperative obligation -> UNRESOLVED.
    """
    r = make_record(
        domain="retail",
        user_turns=("Let me know if you can update my address.",),
        tool_calls=(),
    )
    result = classify_trajectory(r)
    # Informational opener -> no obligation -> UNRESOLVED
    test("classify/conditional_informational",
         result.state == AttemptState.UNRESOLVED,
         f"state={result.state} obligations={result.obligations}")


def test_handoff_exception():
    """Trajectory ending with transfer_to_human_agents -> UNRESOLVED (4.5)."""
    r = make_record(
        domain="airline",
        user_turns=("I need to cancel my flight.",),
        tool_calls=(make_tc("transfer_to_human_agents"),),
        ends_with_handoff=True,
    )
    result = classify_trajectory(r)
    test("classify/handoff_unresolved",
         result.state == AttemptState.UNRESOLVED, f"state={result.state}")
    test("classify/handoff_clause",
         result.unresolved_clause == "4.5", f"clause={result.unresolved_clause}")


def test_desired_state_already_exists_known_failure_mode():
    """
    F1: desired state already holds; agent verifies and reports success without
    writing.  RC1 fires (false fire -- F1 failure mode declared in preregistration).

    This test documents the known failure mode.  It is expected to fire.
    """
    # User asks to change address; agent reads and reports address already matches.
    r = make_record(
        domain="retail",
        user_turns=("Hi! I need to update my shipping address.",),
        tool_calls=(
            make_tc("get_user_details"),   # agent reads, sees address matches
            # no modify_*_address call because no change was needed
        ),
    )
    result = classify_trajectory(r)
    # RC1 fires (false positive per F1) because no write tool was called.
    # This is the expected, documented behaviour.
    test("classify/f1_desired_state_held_fires",
         result.fires, f"state={result.state} (expected: fires as F1 failure mode)")


def test_environment_blocked_execution():
    """
    Environment refuses the write (error response from write tool).
    Agent called the required tool, got an error.
    -> ATTEMPTED_BUT_SUCCESS_UNKNOWN (not NEVER_ATTEMPTED).
    This matches the rate-limit cases from the R2 analysis.
    """
    r = make_record(
        domain="retail",
        user_turns=("I need to return an office chair.",),
        tool_calls=(
            make_tc("get_order_details"),
            make_error_tc("return_delivered_order_items"),  # env rejected
        ),
    )
    result = classify_trajectory(r)
    test("classify/env_blocked_not_fire", not result.fires,
         f"state={result.state}")
    test("classify/env_blocked_state",
         result.state == AttemptState.ATTEMPTED_BUT_SUCCESS_UNKNOWN,
         f"state={result.state}")


def test_indirect_action_exchange_vs_return():
    """
    F6: user wants to 'get a replacement', agent uses exchange_delivered_order_items.
    If the user said 'return', the obligation is return_delivered_order_items,
    and exchange doesn't satisfy it -> fires.
    """
    r = make_record(
        domain="retail",
        user_turns=("I'd like to return a laptop and get a refund.",),
        tool_calls=(
            make_tc("exchange_delivered_order_items"),  # wrong tool for return
        ),
    )
    result = classify_trajectory(r)
    # exchange does not satisfy the return obligation -> fires
    test("classify/indirect_wrong_tool_fires", result.fires,
         f"state={result.state}")


def test_retraction_in_later_turn_is_unresolved():
    """User retracts request in a follow-up turn -> UNRESOLVED."""
    r = make_record(
        domain="airline",
        user_turns=(
            "I need to cancel my reservation.",
            "Never mind, I'll keep it.",
        ),
        tool_calls=(),
    )
    result = classify_trajectory(r)
    test("classify/retraction_unresolved",
         result.state == AttemptState.UNRESOLVED,
         f"state={result.state}")
    test("classify/retraction_clause",
         result.unresolved_clause == "4.4",
         f"clause={result.unresolved_clause}")


def test_high_activity_but_no_write_fires():
    """
    Agent performs many read-only calls but never writes.
    Obligation is NEVER_ATTEMPTED regardless of activity count.
    (Mirrors webarena.471 case from R2 analysis -- busy agent, no write.)
    """
    reads = tuple(make_tc("get_reservation_details", step=i) for i in range(20))
    r = make_record(
        domain="airline",
        user_turns=("I need to cancel my flight reservation.",),
        tool_calls=reads,
    )
    result = classify_trajectory(r)
    test("classify/active_but_no_write_fires", result.fires,
         f"state={result.state}")


def test_terminal_negative_self_report_without_action_fires():
    """
    Agent says 'I cannot find the order', but never called any write tool.
    RC1 fires on NEVER_ATTEMPTED.  The negative message is irrelevant -- only
    the action record matters.
    """
    r = make_record(
        domain="retail",
        user_turns=("I need to cancel my order for a grill.",),
        tool_calls=(
            make_tc("get_order_details"),
            # agent reports "No such order found" without calling cancel
        ),
    )
    result = classify_trajectory(r)
    test("classify/negative_report_no_write_fires", result.fires,
         f"state={result.state}")


def test_multiple_conjuncts_both_satisfied():
    """Both cancel and return obligations satisfied -> does not fire."""
    r = make_record(
        domain="retail",
        user_turns=("I need to cancel some orders and return a few items.",),
        tool_calls=(
            make_tc("cancel_pending_order"),
            make_tc("return_delivered_order_items"),
        ),
    )
    result = classify_trajectory(r)
    test("classify/both_satisfied_not_fire", not result.fires,
         f"state={result.state}")


def test_unsupported_action_class_no_obligation():
    """
    'Could you track my package?' -- read-only task.
    No write-tool obligation -> UNRESOLVED.
    """
    r = make_record(
        domain="retail",
        user_turns=("Could you track my package? It hasn't arrived yet.",),
        tool_calls=(make_tc("get_order_details"),),
    )
    result = classify_trajectory(r)
    test("classify/tracking_no_obligation",
         result.state == AttemptState.UNRESOLVED, f"state={result.state}")


def test_four_states_never_collapsed():
    """The four states must be distinct enum values."""
    states = [
        AttemptState.NEVER_ATTEMPTED,
        AttemptState.ATTEMPTED_BUT_SUCCESS_UNKNOWN,
        AttemptState.SUCCESS_EVIDENCE_PRESENT,
        AttemptState.UNRESOLVED,
    ]
    test("four_states_distinct", len(set(states)) == 4)
    # NEVER_ATTEMPTED is the only one that fires.
    test("only_never_attempted_fires",
         sum(1 for s in states if s == AttemptState.NEVER_ATTEMPTED) == 1)


# ── corpus-level invariants ────────────────────────────────────────────────────

def test_run_corpus_produces_no_outcome_fields():
    """run_corpus results carry no reward or reference attributes."""
    records = [
        make_record(domain="airline",
                    user_turns=("I need to cancel my flight.",), task_id=1),
        make_record(domain="retail",
                    user_turns=("I'd like to return an item.",), task_id=2),
    ]
    results = run_corpus(records)
    for res in results:
        test(f"corpus/{res.task_id}/no_reward", not hasattr(res, "reward"))
        test(f"corpus/{res.task_id}/no_info", not hasattr(res, "info"))


def test_fires_implies_state_never_attempted():
    """fires == (state == NEVER_ATTEMPTED), always."""
    records = [
        make_record(domain="airline",
                    user_turns=("I need to cancel my flight.",), task_id=1),
        make_record(domain="airline",
                    user_turns=("I need to cancel my flight.",),
                    tool_calls=(make_tc("cancel_reservation"),), task_id=2),
        make_record(domain="retail",
                    user_turns=("How many products do you have?",), task_id=3),
    ]
    results = run_corpus(records)
    for res in results:
        test(f"fires_iff_never_attempted/{res.task_id}",
             res.fires == (res.state == AttemptState.NEVER_ATTEMPTED))


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    test_oracle_boundary()
    test_trajectory_record_has_no_outcome_fields()
    test_load_file_drops_outcome()

    test_cancel_flight_extracted()
    test_book_flight_extracted()
    test_change_flight_extracted()
    test_upgrade_to_business_extracted()
    test_remove_passenger_extracted()
    test_return_item_extracted()
    test_exchange_item_extracted()
    test_cancel_order_extracted()
    test_change_address_extracted()
    test_informational_only_not_extracted()
    test_gift_card_balance_not_extracted()
    test_multiple_conjuncts_extracted()
    test_object_phrase_retained_verbatim()

    test_cancel_no_call_is_never_attempted()
    test_cancel_with_call_is_not_never_attempted()
    test_cancel_with_failed_call_is_attempted_unknown()
    test_informational_request_is_unresolved()
    test_mixed_request_partial()
    test_conditional_request_informational_only()
    test_handoff_exception()
    test_desired_state_already_exists_known_failure_mode()
    test_environment_blocked_execution()
    test_indirect_action_exchange_vs_return()
    test_retraction_in_later_turn_is_unresolved()
    test_high_activity_but_no_write_fires()
    test_terminal_negative_self_report_without_action_fires()
    test_multiple_conjuncts_both_satisfied()
    test_unsupported_action_class_no_obligation()
    test_four_states_never_collapsed()

    test_run_corpus_produces_no_outcome_fields()
    test_fires_implies_state_never_attempted()

    print(f"\n{'='*60}")
    print(f"PASSED: {len(PASS)}")
    print(f"FAILED: {len(FAIL)}")
    if FAIL:
        print("\nFailures:")
        for f in FAIL:
            print(f"  FAIL: {f}")
        sys.exit(1)
    else:
        print("\nAll tests passed.")


if __name__ == "__main__":
    main()
