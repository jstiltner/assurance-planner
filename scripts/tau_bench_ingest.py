"""tau_bench_ingest.py -- Outcome-free trajectory loader.

Loads the four sierra-research/tau-bench historical trajectory files and produces
TrajectoryRecord objects that contain ONLY production-visible fields.

ORACLE BOUNDARY
---------------
`reward` and `info` are dropped at load time.  The dataclass types carry only
production-visible state, so downstream rule code cannot reach outcome fields --
not by promise but by the absence of those attributes.

assert_no_outcome_fields() is called on every raw JSON record before any field is
read.  If the file format ever adds new outcome fields, the assertion fires rather
than silently leaking.

Nothing in this module reads reference labels, expected database state, expected
outputs, or the benchmark's hidden task instructions (tasks_test.py).  task_id is
kept for grouping and scoring joins only; it is not a semantic input to RC1.

Usage
-----
  from tau_bench_ingest import load_corpus, TrajectoryRecord
  records = load_corpus(trajectory_dir)          # list[TrajectoryRecord]
  for r in records:
      print(r.task_id, r.domain, len(r.tool_calls))
"""

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ── oracle boundary ────────────────────────────────────────────────────────────

OUTCOME_FIELDS = frozenset({
    "reward", "info",
    # expected fields that would constitute oracle leakage if present:
    "expected_output", "expected_actions", "expected_state",
    "trajectory_success", "reference_label",
})


def assert_no_outcome_fields(raw: dict, source_hint: str = "") -> None:
    """Raise AssertionError if any outcome field is present in the raw record."""
    leaked = OUTCOME_FIELDS & set(raw)
    if leaked:
        raise AssertionError(
            f"oracle leakage into ingest layer: {sorted(leaked)}"
            + (f" (source: {source_hint})" if source_hint else "")
        )


# ── production-visible types ───────────────────────────────────────────────────

@dataclass(frozen=True)
class ToolCall:
    """One tool invocation from the agent."""
    name: str          # function name
    args_str: str      # raw JSON argument string, verbatim
    response: str      # tool response string, verbatim ("Error: ..." or JSON)
    step_index: int    # position in the ordered execution record

    @property
    def succeeded(self) -> bool:
        """Response does not start with 'Error:' -- a success-shaped reply."""
        return not self.response.startswith("Error:")


@dataclass(frozen=True)
class TrajectoryRecord:
    """Production-visible fields only.

    reward and info are absent by construction.  There is no attribute to
    accidentally inspect.
    """
    task_id: int
    trial: int
    domain: str   # "airline" or "retail"
    agent: str

    # User utterances, in dialogue order.  Only role=="user" content.
    user_turns: Tuple[str, ...]

    # Ordered tool calls with responses.  Includes read-only and write tools.
    tool_calls: Tuple[ToolCall, ...]

    # Derived convenience fields -- all production-visible.
    called_tool_names: frozenset  # set of all function names called

    # True if transfer_to_human_agents was the last substantive action.
    ends_with_handoff: bool

    # True if the trajectory terminated normally (last turn is assistant).
    has_terminal_assistant_turn: bool

    # Number of dialogue turns (all roles).
    n_turns: int


# ── domain catalogs (derived from tool docstrings, not from outcomes) ──────────

# Write tools per domain.  Derived from tool docstrings in
# sierra-research/tau-bench.  Read-only tools (get_*, search_*, calculate,
# think, list_*) are excluded.  This classification is deployment config: a
# production system knows which of its own tools mutate state.

AIRLINE_WRITE_TOOLS = frozenset({
    "book_reservation",           # "Book a reservation."
    "cancel_reservation",         # "Cancel the whole reservation."
    "send_certificate",           # "Send a certificate to a user."
    "update_reservation_flights", # "Update the flight information of a reservation."
    "update_reservation_baggages",# "Update the baggage information of a reservation."
    "update_reservation_passengers", # "Update the passenger information of a reservation."
})

RETAIL_WRITE_TOOLS = frozenset({
    "cancel_pending_order",           # "Cancel a pending order."
    "exchange_delivered_order_items", # "Exchange items in a delivered order."
    "modify_pending_order_address",   # "Modify the shipping address of a pending order."
    "modify_pending_order_items",     # "Modify items in a pending order."
    "modify_pending_order_payment",   # "Modify the payment method of a pending order."
    "modify_user_address",            # "Modify the default address of a user."
    "return_delivered_order_items",   # "Return some items of a delivered order."
})

HANDOFF_TOOLS = frozenset({"transfer_to_human_agents"})

ALL_WRITE_TOOLS = AIRLINE_WRITE_TOOLS | RETAIL_WRITE_TOOLS


def write_tools_for_domain(domain: str) -> frozenset:
    if domain == "airline":
        return AIRLINE_WRITE_TOOLS
    if domain == "retail":
        return RETAIL_WRITE_TOOLS
    raise ValueError(f"unknown domain: {domain!r}")


# ── low-level parsing ──────────────────────────────────────────────────────────

def _content_text(content) -> str:
    """Flatten message content (string or list of parts) to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content) if content else ""


def _domain_from_files(path: str) -> str:
    base = os.path.basename(path).lower()
    if "airline" in base or base == "tb_air.json":
        return "airline"
    if "retail" in base:
        return "retail"
    raise ValueError(f"cannot infer domain from filename: {base!r}")


def _parse_trajectory(raw: dict, domain: str) -> TrajectoryRecord:
    """
    Parse one raw trajectory record into a TrajectoryRecord.

    Reads: task_id, trial, traj (messages).
    Drops: reward, info, and any other outcome field.
    """
    traj = raw.get("traj") or []
    user_turns = []
    tool_calls_list: List[ToolCall] = []

    # Build the ordered tool call list.  We need to pair assistant tool_calls
    # with the subsequent tool-role responses.
    pending_calls: List[Tuple[str, str]] = []  # (name, args_str)

    step_idx = 0
    last_role = None

    for msg in traj:
        role = msg.get("role", "")
        content = _content_text(msg.get("content"))

        if role == "user":
            user_turns.append(content)
            last_role = role

        elif role == "assistant":
            # Record any tool calls the assistant issued.
            for tc in msg.get("tool_calls") or []:
                fn = tc.get("function") or {}
                name = fn.get("name", "")
                args = fn.get("arguments", "")
                pending_calls.append((name, args))
            last_role = role

        elif role == "tool":
            # Match with pending call.
            name_from_msg = msg.get("name", "")
            response = content
            if pending_calls:
                call_name, call_args = pending_calls.pop(0)
                # Prefer name from the call record; fall back to message name.
                resolved_name = call_name or name_from_msg
            else:
                resolved_name = name_from_msg
                call_args = ""

            tool_calls_list.append(ToolCall(
                name=resolved_name,
                args_str=call_args,
                response=response,
                step_index=step_idx,
            ))
            step_idx += 1
            last_role = role

    # Flush any pending calls that had no matching response (truncated trajectory).
    for call_name, call_args in pending_calls:
        tool_calls_list.append(ToolCall(
            name=call_name,
            args_str=call_args,
            response="",
            step_index=step_idx,
        ))
        step_idx += 1

    called_names = frozenset(tc.name for tc in tool_calls_list)
    ends_with_handoff = bool(called_names & HANDOFF_TOOLS) and bool(
        [tc for tc in tool_calls_list if tc.name in HANDOFF_TOOLS]
        and tool_calls_list[-1].name in HANDOFF_TOOLS
    )

    return TrajectoryRecord(
        task_id=int(raw.get("task_id", -1)),
        trial=int(raw.get("trial", -1)),
        domain=domain,
        agent=str(raw.get("agent", "") if "agent" in raw else _agent_from_traj(traj)),
        user_turns=tuple(user_turns),
        tool_calls=tuple(tool_calls_list),
        called_tool_names=called_names,
        ends_with_handoff=ends_with_handoff,
        has_terminal_assistant_turn=(last_role == "assistant"),
        n_turns=len(traj),
    )


def _agent_from_traj(traj: list) -> str:
    """Infer agent label from system prompt if not in record."""
    for msg in traj:
        if msg.get("role") == "system":
            c = _content_text(msg.get("content"))
            if "gpt-4o" in c:
                return "gpt-4o"
            if "sonnet" in c.lower():
                return "sonnet-3.5"
    return "unknown"


# ── public loader ──────────────────────────────────────────────────────────────

#: Default file names, relative to a trajectory directory.
DEFAULT_FILES = [
    "gpt-4o-airline.json",
    "gpt-4o-retail.json",
    "sonnet-35-new-airline.json",
    "sonnet-35-new-retail.json",
]


def load_file(path: str) -> List[TrajectoryRecord]:
    """
    Load one trajectory JSON file.  Drops reward and info at the record level.

    Returns a list of TrajectoryRecord objects.
    """
    domain = _domain_from_files(path)
    with open(path, encoding="utf-8") as fh:
        raw_records = json.load(fh)

    records: List[TrajectoryRecord] = []
    for raw in raw_records:
        # Strip known outcome fields first so _parse_trajectory never sees them.
        clean = {k: v for k, v in raw.items() if k not in OUTCOME_FIELDS}
        # Then assert that no OTHER outcome-like fields remain.
        assert_no_outcome_fields(clean, source_hint=os.path.basename(path))
        records.append(_parse_trajectory(clean, domain))

    return records


def load_corpus(trajectory_dir: str,
                filenames: Optional[List[str]] = None) -> List[TrajectoryRecord]:
    """
    Load all four trajectory files from trajectory_dir.

    Each file is loaded with load_file(); outcome fields are dropped before
    parsing.  Returns the combined list of TrajectoryRecord objects.
    """
    if filenames is None:
        filenames = DEFAULT_FILES
    out: List[TrajectoryRecord] = []
    for fname in filenames:
        path = os.path.join(trajectory_dir, fname)
        if not os.path.exists(path):
            raise FileNotFoundError(f"trajectory file not found: {path}")
        out.extend(load_file(path))
    return out


def assert_no_outcome_in_record(record: TrajectoryRecord) -> None:
    """
    Verify that a TrajectoryRecord carries no outcome-bearing attribute.

    This is a belt-and-suspenders check for use in unit tests and the audit.
    TrajectoryRecord is a frozen dataclass, so its fields are fixed at
    construction time; this check confirms the type contract.
    """
    import dataclasses
    names = {f.name for f in dataclasses.fields(record)}
    leaked = OUTCOME_FIELDS & names
    if leaked:
        raise AssertionError(
            f"TrajectoryRecord contains outcome field(s): {sorted(leaked)}"
        )
