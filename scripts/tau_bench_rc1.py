"""tau_bench_rc1.py -- Frozen RC1 rule: required-conjunct-never-attempted.

Specification: docs/required_conjunct_preregistration.md, committed 2026-09-29
at commit 086f0c6.

ORACLE BOUNDARY
---------------
This module reads only TrajectoryRecord objects produced by tau_bench_ingest.
Those objects carry no reward or reference outcome field.  RC1 decisions are
made and serialised before any reward join occurs.

DESIGN AUTHORITY
----------------
RC1 emits UNVERIFIABLE + escalate.  It has no veto power.
A counterfactual veto is computed and reported separately -- it is never applied.

DO NOT MODIFY after reward is unlocked.  If RC1 fails its preregistered criteria,
this file stays frozen in its failing form exactly as the preregistration requires.
"""

import enum
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

from tau_bench_ingest import (
    TrajectoryRecord,
    ToolCall,
    AIRLINE_WRITE_TOOLS,
    RETAIL_WRITE_TOOLS,
    HANDOFF_TOOLS,
)


# ── four attempt states -- never collapsed ─────────────────────────────────────

class AttemptState(str, enum.Enum):
    NEVER_ATTEMPTED              = "NEVER_ATTEMPTED"
    ATTEMPTED_BUT_SUCCESS_UNKNOWN = "ATTEMPTED_BUT_SUCCESS_UNKNOWN"
    SUCCESS_EVIDENCE_PRESENT     = "SUCCESS_EVIDENCE_PRESENT"
    UNRESOLVED                   = "UNRESOLVED"


# ── obligation ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Obligation:
    """
    One extracted required conjunct.

    action_class: frozenset of tool names; calling ANY one satisfies the
                  obligation.  The set covers ambiguous cases where the user's
                  request could map to more than one write tool.

    object_phrase: verbatim user noun phrase; retained for audit and reporting;
                   never resolved to an entity id and never used to decide
                   whether RC1 fires.

    confidence:   "high" -- pattern is specific and the obligation is clear;
                  "low"  -- pattern matched but the verb-object context is
                           ambiguous; routing to UNRESOLVED if confidence is
                           low everywhere.
    """
    action_class: frozenset   # frozenset[str]
    object_phrase: str
    confidence: str           # "high" or "low"


# ── rc1 output ─────────────────────────────────────────────────────────────────

@dataclass
class RC1Result:
    """Output of classify_trajectory().  No reward or reference outcome field."""
    task_id: int
    trial: int
    domain: str
    agent: str

    # Per-obligation state.  One entry per extracted obligation.
    obligations: List[Obligation]

    # Final attempt state for the trajectory.
    state: AttemptState

    # Plain-text reason for the state, for audit inspection.
    reason: str

    # Write tools that were actually called (any domain).
    called_write_tools: frozenset   # frozenset[str]

    # Which obligations (by index) contributed to NEVER_ATTEMPTED, if any.
    never_attempted_indices: List[int]

    # Exception clause that forced UNRESOLVED, if any (section 4 clause number).
    unresolved_clause: Optional[str]

    @property
    def fires(self) -> bool:
        """RC1 fires when state is NEVER_ATTEMPTED."""
        return self.state == AttemptState.NEVER_ATTEMPTED


# ── verb-to-action-class table ─────────────────────────────────────────────────
#
# Derived from tool docstrings in sierra-research/tau-bench, not from outcome
# frequencies.  The tool catalogue is I2 per the preregistration; using it to
# decide which verbs map to which tools is deployment config, not oracle leakage.
#
# Each entry: (compiled_regex, action_class_frozenset, confidence)
#
# Rules:
# - Applied to individual sentences within user turns.
# - The FIRST matching pattern per sentence wins (no double-counting).
# - All patterns are case-insensitive.
# - The object_phrase is the text matched by the regex's first capture group.
# - Patterns are listed from most-specific to least-specific within each section.
# - "low" confidence patterns require corroboration from a second sentence;
#   a trajectory whose ONLY obligations are low-confidence is UNRESOLVED.

# ── airline verb patterns ──────────────────────────────────────────────────────

_A_BOOK = frozenset({"book_reservation"})
_A_CANCEL = frozenset({"cancel_reservation"})
_A_FLIGHTS = frozenset({"update_reservation_flights"})
_A_BAGS = frozenset({"update_reservation_baggages"})
_A_PAX = frozenset({"update_reservation_passengers"})
_A_CERT = frozenset({"send_certificate"})
# Vague "make changes to my reservation": any of the three update tools.
_A_VAGUE_UPDATE = frozenset({
    "update_reservation_flights",
    "update_reservation_baggages",
    "update_reservation_passengers",
})

AIRLINE_PATTERNS: List[Tuple[re.Pattern, frozenset, str]] = [
    # send / issue certificate before generic "book" to avoid false matches.
    # "apply" is excluded: "apply the certificate to my booking" means payment
    # routing (using an existing certificate), not requesting a new one.
    (re.compile(
        r"\b(?:send|issue|give|add|provide)\b"
        r"[^.!?]*?\b(certificate|voucher|travel credit|compensation)\b",
        re.I), _A_CERT, "high"),

    # book a flight / reservation.
    # "purchase" is excluded from the short-form to prevent "purchase insurance
    # for my flight" from matching: the insurance noun intervenes between the
    # verb and the flight noun and the intent is insurance, not booking.
    (re.compile(
        r"\b(?:book|reserve|buy)\b"
        r"[^.!?]*?\b(flight|reservation|ticket|seat)\b",
        re.I), _A_BOOK, "high"),
    # "purchase [a] ticket/seat/reservation" -- kept separate so "purchase
    # insurance for my flight" doesn't match (insurance is not a flight noun).
    (re.compile(
        r"\bpurchase\b[^.!?]*?\b(ticket|seat|reservation)\b",
        re.I), _A_BOOK, "high"),

    # cancel flight / reservation (handles singular and plural)
    (re.compile(
        r"\b(?:cancel|void|drop)\b"
        r"[^.!?]*?\b(flights?|reservation|booking|trip|tickets?)\b",
        re.I), _A_CANCEL, "high"),

    # cancel all -- imperative without object noun, still clearly cancel_reservation
    (re.compile(r"\bcancel all\b[^.!?]*?\b(?:upcoming|my|the)\b", re.I),
     _A_CANCEL, "high"),

    # change / update / modify baggage -- more specific than generic flight change
    (re.compile(
        r"\b(?:add|change|modify|update|remove|reduce|increase)\b"
        r"[^.!?]*?\b(bag(?:gage)?|luggage|suitcase|checked bag)\b",
        re.I), _A_BAGS, "high"),

    # change / remove / update passenger name
    (re.compile(
        r"\b(?:change|modify|update|remove|fix|correct|add)\b"
        r"[^.!?]*?\b(passenger|traveler|name on|name for|companion)\b",
        re.I), _A_PAX, "high"),

    # upgrade / downgrade cabin class -- flight modification
    (re.compile(
        r"\b(?:upgrade|downgrade|switch)\b"
        r"[^.!?]*?\b(business|economy|first class|cabin|class)\b",
        re.I), _A_FLIGHTS, "high"),

    # change / modify / reschedule / rebook / reroute flight (singular and plural)
    (re.compile(
        r"\b(?:change|modify|update|reschedule|rebook|reroute|move|switch|"
        r"adjust|alter)\b"
        r"[^.!?]*?\b(flights?|reservation|booking|itinerary|route|trip|"
        r"return flight|outbound|departure|connection)\b",
        re.I), _A_FLIGHTS, "high"),

    # "need to make a few changes to my upcoming trip/flight" -- vague
    (re.compile(
        r"\b(?:make|make some|make a few|make several)\b"
        r"[^.!?]*?\b(?:change|changes|modification|modifications)\b"
        r"[^.!?]*?\b(trip|flight|reservation|booking|reservation)\b",
        re.I), _A_VAGUE_UPDATE, "low"),
]

# ── retail verb patterns ───────────────────────────────────────────────────────

_R_CANCEL = frozenset({"cancel_pending_order"})
_R_RETURN = frozenset({"return_delivered_order_items"})
_R_EXCHANGE = frozenset({"exchange_delivered_order_items"})
# Address change: may refer to order shipping address or profile address.
_R_ADDRESS = frozenset({"modify_pending_order_address", "modify_user_address"})
_R_ITEMS = frozenset({"modify_pending_order_items"})
_R_PAYMENT = frozenset({"modify_pending_order_payment"})

RETAIL_PATTERNS: List[Tuple[re.Pattern, frozenset, str]] = [
    # cancel order -- before generic "return/cancel" combos
    (re.compile(
        r"\b(?:cancel)\b"
        r"[^.!?]*?\b(orders?|pending orders?)\b",
        re.I), _R_CANCEL, "high"),

    # cancel all pending orders
    (re.compile(r"\bcancel all\b[^.!?]*?\b(?:pending|my)\b[^.!?]*?\borders?\b",
                re.I), _R_CANCEL, "high"),

    # return / send back items.  "refund" is NOT listed here: "refund it to
    # [payment method]" is a payment-direction instruction, not a return request.
    # Use the bare-refund pattern below for "need a refund".
    (re.compile(
        r"\b(?:return|send back)\b"
        r"[^.!?]*?\b(items?|products?|orders?|everything|them|it|all|laptops?|"
        r"cameras?|chairs?|vacuums?|purifiers?|tablets?|bicycles?|keyboards?|"
        r"earbuds?|bottles?|backpacks?|jackets?|skateboards?|boots?|helmets?|"
        r"watches?|speakers?|luggage|jigsaws?|bookshelfs?|grills?|hoses?|"
        r"thermostats?|shoes?)\b",
        re.I), _R_RETURN, "high"),

    # bare "need a refund" / "want a refund"
    (re.compile(r"\b(?:need|want|get|requesting|looking for)\b"
                r"[^.!?]*?\b(refund)\b", re.I), _R_RETURN, "high"),

    # "switch/change all items to their cheapest/cheaper/lower options" means
    # spec modification in a pending order, not an exchange of delivered items.
    # This must appear BEFORE the exchange pattern so it wins for this phrasing.
    (re.compile(
        r"\b(?:switch|change|adjust)\b"
        r"[^.!?]*?\b(items?|products?)\b"
        r"[^.!?]*?\bto\b[^.!?]*?\b(?:cheapest|cheaper|lower|affordable)\b",
        re.I), _R_ITEMS, "high"),

    # exchange / swap / replace items (handle plurals for specific product nouns)
    (re.compile(
        r"\b(?:exchange|swap|replace|switch)\b"
        r"[^.!?]*?\b(items?|products?|orders?|it|them|keyboards?|cameras?|"
        r"earbuds?|jackets?|boots?|helmets?|thermostats?|vacuums?|bicycles?|"
        r"tablets?|shoes?|skateboards?|t-shirts?|t shirts?|tshirts?|"
        r"bookshelfs?|watches?|kettles?|laptops?)\b",
        re.I), _R_EXCHANGE, "high"),

    # upgrade items -- usually exchange to a higher-tier variant
    (re.compile(r"\b(?:upgrade)\b[^.!?]*?\b(items?|products?|orders?|it|them)\b",
                re.I), _R_EXCHANGE, "high"),

    # modify pending order items (change color/size/variant in pending order)
    (re.compile(
        r"\b(?:change|modify|update|switch|adjust)\b"
        r"[^.!?]*?\b(item|items|color|size|variant|style|boot|boots|earbuds|"
        r"keyboard|product)\b"
        r"[^.!?]*?\b(?:in|from|of|on)\b[^.!?]*?\b(?:order|pending)\b",
        re.I), _R_ITEMS, "high"),

    # "change my boot order" / "change the item in my order"
    (re.compile(
        r"\b(?:change|modify|update)\b"
        r"[^.!?]*?\b(boot|boots|item|items|earbuds|keyboard)\b"
        r"[^.!?]*?\border\b",
        re.I), _R_ITEMS, "high"),

    # change payment method
    (re.compile(
        r"\b(?:change|modify|update|switch|split)\b"
        r"[^.!?]*?\b(payment|card|payment method|billing)\b",
        re.I), _R_PAYMENT, "high"),

    # change delivery/shipping address
    (re.compile(
        r"\b(?:change|modify|update|fix|correct|update)\b"
        r"[^.!?]*?\b(address|delivery address|shipping address)\b",
        re.I), _R_ADDRESS, "high"),

    # "change my address" without order context -- profile or order
    (re.compile(r"\b(?:change|update|modify)\b[^.!?]*?\bmy address\b",
                re.I), _R_ADDRESS, "high"),

    # "update delivery/shipping" without explicit "address" noun
    (re.compile(
        r"\b(?:update|change|fix)\b"
        r"[^.!?]*?\b(delivery|shipping)\b"
        r"(?![^.!?]*\b(?:status|time|date|arrival|estimate)\b)",
        re.I), _R_ADDRESS, "low"),
]


# ── obligation extractor ───────────────────────────────────────────────────────

# Sentence boundary splitter.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Clause splitter within sentences.  Splits on coordinating conjunctions and
# commas so that "cancel X and return Y" produces two matchable clauses.
# Applied AFTER sentence splitting.
_CLAUSE_SPLIT = re.compile(r"\s+(?:and|but|also|plus|as well as)\s+|,\s+", re.I)

# Patterns whose match should suppress firing (informational only, no write duty):
# These are request structures that linguistically indicate information-seeking.
_INFORMATIONAL_ONLY = re.compile(
    r"^\s*(?:how many|what is|what are|tell me|could you tell|can you tell|"
    r"please tell|let me know|just wondering|curious|wondering|"
    r"check|find out|look up|see if|verify)\b",
    re.I,
)

# Retraction patterns: user explicitly cancels or retracts their entire earlier
# request.  These must be explicit, unambiguous withdrawal phrases.  Hedges
# like "actually I don't have the order ID" are NOT retractions -- they are
# information qualifications that do not change the user's underlying goal.
_RETRACTION = re.compile(
    r"\b(?:never mind|forget it|I (?:changed|change) my mind|"
    r"don\'t worry about it|disregard|ignore that|scratch that|"
    r"actually,? never mind|on second thought,? never mind)\b",
    re.I,
)

# Conditional patterns suggesting the obligation may not be absolute.
# These are genuine syntactic conditionals, not politeness hedges.
_CONDITIONAL_SYNTACTIC = re.compile(
    r"\bif (?:I\'m|I am) eligible\b"
    r"|\bif (?:it\'s|it is) (?:possible|pending|available|allowed|applicable)\b"
    r"|\bif (?:there\'s|there is) (?:a|any|an)\b"
    r"|\bif (?:possible|applicable|allowed|eligible)\b",
    re.I,
)


def _clauses(text: str) -> List[str]:
    """Split text into rough clauses (sentences then coordinating conjunctions).

    Returns a list of clause strings.  The clause is the unit to which the
    'first pattern wins' rule applies, preventing double-counting within a
    single obligation phrase while allowing two distinct obligations in the
    same sentence (e.g. 'cancel X and return Y').
    """
    result = []
    for sent in _SENT_SPLIT.split(text):
        sent = sent.strip()
        if not sent:
            continue
        for clause in _CLAUSE_SPLIT.split(sent):
            clause = clause.strip()
            if clause:
                result.append(clause)
    return result


def extract_obligations(record: TrajectoryRecord) -> List[Obligation]:
    """
    Extract required conjuncts from the user's utterances (I1).

    Rules derived from preregistration section 3:
    - Applies verb patterns to each sentence of each user turn.
    - The first matching pattern per sentence wins.
    - Informational sentences do not generate obligations.
    - Low-confidence patterns are retained but flagged.
    - Each unique (action_class, object_phrase) pair is returned once.
    """
    patterns = AIRLINE_PATTERNS if record.domain == "airline" else RETAIL_PATTERNS

    seen: Set[frozenset] = set()
    obligations: List[Obligation] = []

    for turn_text in record.user_turns:
        # Skip ###STOP### sentinel turns.
        if "###STOP###" in turn_text:
            continue
        for clause in _clauses(turn_text):
            if _INFORMATIONAL_ONLY.match(clause):
                continue
            for pat, action_class, confidence in patterns:
                m = pat.search(clause)
                if m:
                    # Capture group 1 is the object phrase if present.
                    try:
                        obj_phrase = m.group(1)
                    except IndexError:
                        obj_phrase = m.group(0)

                    # Deduplicate by action_class (not object_phrase).
                    if action_class not in seen:
                        seen.add(action_class)
                        obligations.append(Obligation(
                            action_class=action_class,
                            object_phrase=obj_phrase.strip(),
                            confidence=confidence,
                        ))
                    break  # first pattern wins per clause

    return obligations


# ── four-state classifier ──────────────────────────────────────────────────────

def _classify_attempt(
    obligation: Obligation,
    tool_calls: Tuple[ToolCall, ...],
) -> AttemptState:
    """
    Classify one obligation against the execution record.

    Never collapses states.
    """
    relevant = [tc for tc in tool_calls if tc.name in obligation.action_class]

    if not relevant:
        return AttemptState.NEVER_ATTEMPTED

    # At least one call was made.  Did any succeed?
    if any(tc.succeeded for tc in relevant):
        return AttemptState.SUCCESS_EVIDENCE_PRESENT

    return AttemptState.ATTEMPTED_BUT_SUCCESS_UNKNOWN


def classify_trajectory(record: TrajectoryRecord) -> RC1Result:
    """
    Apply RC1 to one TrajectoryRecord.

    Section 3 (trigger) and section 4 (exceptions) of the preregistration.
    """
    called_write = record.called_tool_names & (AIRLINE_WRITE_TOOLS | RETAIL_WRITE_TOOLS)

    # ── exceptions (section 4) -- each forces UNRESOLVED ──────────────────────

    # 4.1 Truncated or malformed trajectory.
    if not record.has_terminal_assistant_turn and record.n_turns < 4:
        return RC1Result(
            task_id=record.task_id, trial=record.trial,
            domain=record.domain, agent=record.agent,
            obligations=[], state=AttemptState.UNRESOLVED,
            reason="exception 4.1: trajectory truncated or too short",
            called_write_tools=called_write,
            never_attempted_indices=[],
            unresolved_clause="4.1",
        )

    # 4.2 No user turns.
    if not record.user_turns:
        return RC1Result(
            task_id=record.task_id, trial=record.trial,
            domain=record.domain, agent=record.agent,
            obligations=[], state=AttemptState.UNRESOLVED,
            reason="exception 4.2: no user turns",
            called_write_tools=called_write,
            never_attempted_indices=[],
            unresolved_clause="4.2",
        )

    # Extract obligations (I1 + I2).
    obligations = extract_obligations(record)

    # 4.2 continued: no parseable request.
    if not obligations:
        return RC1Result(
            task_id=record.task_id, trial=record.trial,
            domain=record.domain, agent=record.agent,
            obligations=[], state=AttemptState.UNRESOLVED,
            reason="no obligation extracted (informational or unrecognised request)",
            called_write_tools=called_write,
            never_attempted_indices=[],
            unresolved_clause="4.2",
        )

    # 4.3 ACTION_CLASS not in domain vocabulary (already enforced by
    #     extract_obligations; included for completeness).

    # 4.4 User retraction in a later turn.
    for turn_text in record.user_turns[1:]:  # skip first turn
        if _RETRACTION.search(turn_text):
            return RC1Result(
                task_id=record.task_id, trial=record.trial,
                domain=record.domain, agent=record.agent,
                obligations=obligations, state=AttemptState.UNRESOLVED,
                reason="exception 4.4: user retraction detected",
                called_write_tools=called_write,
                never_attempted_indices=[],
                unresolved_clause="4.4",
            )

    # 4.5 Agent's final action is the domain's handoff tool.
    if record.ends_with_handoff:
        return RC1Result(
            task_id=record.task_id, trial=record.trial,
            domain=record.domain, agent=record.agent,
            obligations=obligations, state=AttemptState.UNRESOLVED,
            reason="exception 4.5: trajectory ends with handoff tool",
            called_write_tools=called_write,
            never_attempted_indices=[],
            unresolved_clause="4.5",
        )

    # Only low-confidence obligations present -- treat as UNRESOLVED (section 3.5).
    if all(o.confidence == "low" for o in obligations):
        return RC1Result(
            task_id=record.task_id, trial=record.trial,
            domain=record.domain, agent=record.agent,
            obligations=obligations, state=AttemptState.UNRESOLVED,
            reason="only low-confidence obligations extracted",
            called_write_tools=called_write,
            never_attempted_indices=[],
            unresolved_clause="low-confidence",
        )

    # ── T1 satisfied; check T2 per obligation ─────────────────────────────────

    obligation_states: List[AttemptState] = []
    for ob in obligations:
        if ob.confidence == "low":
            obligation_states.append(AttemptState.UNRESOLVED)
            continue
        obligation_states.append(_classify_attempt(ob, record.tool_calls))

    never_attempted_indices = [
        i for i, s in enumerate(obligation_states)
        if s == AttemptState.NEVER_ATTEMPTED
    ]

    # RC1 fires if at least one high-confidence obligation was NEVER_ATTEMPTED.
    if never_attempted_indices:
        fired_obs = [obligations[i] for i in never_attempted_indices]
        parts = [
            f"{ob.object_phrase!r} (needs {sorted(ob.action_class)})"
            for ob in fired_obs
        ]
        return RC1Result(
            task_id=record.task_id, trial=record.trial,
            domain=record.domain, agent=record.agent,
            obligations=obligations,
            state=AttemptState.NEVER_ATTEMPTED,
            reason=f"obligation(s) with no matching write-tool call: {'; '.join(parts)}",
            called_write_tools=called_write,
            never_attempted_indices=never_attempted_indices,
            unresolved_clause=None,
        )

    # All high-confidence obligations have at least an attempt.
    # Pick the "worst" state to summarise the trajectory.
    has_success = any(
        s == AttemptState.SUCCESS_EVIDENCE_PRESENT for s in obligation_states
    )
    summary_state = (
        AttemptState.SUCCESS_EVIDENCE_PRESENT
        if has_success
        else AttemptState.ATTEMPTED_BUT_SUCCESS_UNKNOWN
    )

    return RC1Result(
        task_id=record.task_id, trial=record.trial,
        domain=record.domain, agent=record.agent,
        obligations=obligations,
        state=summary_state,
        reason=f"all obligations have corresponding write-tool call(s)",
        called_write_tools=called_write,
        never_attempted_indices=[],
        unresolved_clause=None,
    )


# ── corpus-level runner ────────────────────────────────────────────────────────

def run_corpus(records: List[TrajectoryRecord]) -> List[RC1Result]:
    """Classify all trajectories.  No reward field is read."""
    return [classify_trajectory(r) for r in records]


def state_distribution(results: List[RC1Result]):
    """Return (state -> count) dict."""
    from collections import Counter
    return dict(Counter(r.state.value for r in results))


def firing_task_ids(results: List[RC1Result]) -> Set[int]:
    """Task IDs where at least one trial fires."""
    return {r.task_id for r in results if r.fires}


if __name__ == "__main__":
    import sys
    import os
    traj_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
        "~/AppData/Local/Temp"
    )
    from tau_bench_ingest import load_corpus
    print(f"Loading corpus from {traj_dir} ...")
    records = load_corpus(traj_dir)
    print(f"Loaded {len(records)} records")
    results = run_corpus(records)
    dist = state_distribution(results)
    fires = [r for r in results if r.fires]
    fire_tasks = firing_task_ids(results)
    print(f"State distribution: {dist}")
    print(f"Fires (NEVER_ATTEMPTED): {len(fires)} trajectories  "
          f"{len(fire_tasks)} distinct tasks")
    unresolved_clause = {}
    for r in results:
        if r.unresolved_clause:
            unresolved_clause[r.unresolved_clause] = unresolved_clause.get(r.unresolved_clause, 0) + 1
    print(f"UNRESOLVED by clause: {unresolved_clause}")
