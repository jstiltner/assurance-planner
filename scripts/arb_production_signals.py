"""Production-visible signal extraction and FROZEN candidate repair rules.

Governing rule for this module:

    Benchmark metadata may diagnose a failure, but only production-visible
    evidence may power a production assurance mechanism.

Everything in `extract_features` is recoverable at evaluation time by a deployed
system that does NOT know the reference answer. The rules in `RULES` read only
those features. Reference labels, `cum_reward`, the benchmark `task_id`, and the
`infeasible-*` family name are NEVER read by a rule -- they are scoring material
only, and `assert_no_oracle_fields` enforces that the rule input record does not
even carry them.

FROZEN 2026-09-29, before any held-out outcome was computed. Coverage (how often
a rule fires) was measured first, label-blind; that is deliberate and recorded in
docs/production_signal_audit.md. No rule was altered after seeing agreement with
the reference label.

Usage:
  python scripts/arb_production_signals.py --coverage      # label-blind firing rates
  python scripts/arb_production_signals.py --dump out.json # per-case features+fires
"""

import argparse
import collections
import json
import os
import re
import urllib.parse

SNAPSHOT = os.path.expanduser(
    "~/.cache/huggingface/hub/datasets--McGill-NLP--agent-reward-bench/"
    "snapshots/b6d17e646009d6cb63d5dd7be78807b680693f61"
)
JUDGMENTS = os.path.join(SNAPSHOT, "judgments")

# Fields that exist only because a benchmark author knew the answer. A rule that
# reads any of these is not a production assurance mechanism.
ORACLE_FIELDS = frozenset({
    "reference_label", "trajectory_success", "trajectory_side_effect",
    "trajectory_optimality", "trajectory_looping", "cum_reward",
    "cum_raw_reward", "task_id", "is_infeasible_family", "expected_url",
    "expected_entity", "input_image_identity",
})

STEP_RE = re.compile(r"^Step: (\d+)\nURL: (.*?)\nAction: (.*?)\nReasoning:", re.S | re.M)
CAPTION_MARKER = "The detailed final state of the webpage:"

# -- lexical resources, all applied to production-visible text only ------------

# The agent asserting, inside the "I cannot do this" tool, that it did the thing.
COMPLETION_ASSERTION = re.compile(
    r"\b(task (is |has been )?(complete|completed|successfully)"
    r"|successfully (completed|posted|added|submitted|created)"
    r"|has been (successfully )?(posted|added|submitted|completed|created)"
    r"|already (been )?(posted|added|set|exists)"
    r"|is complete)\b", re.I)

# The agent asserting it could not achieve the goal / the target does not exist.
NEGATIVE_SELF_REPORT = re.compile(
    r"\b(no |none of|not (available|present|found|possible)|cannot|can't"
    r"|could not|couldn't|unable to|there (are|is) no|does not (provide|exist|contain)"
    r"|impossible|failed to)", re.I)

# High-precision modification detector: an imperative modification verb in the
# leading position of the goal. Chosen over a bag-of-verbs scan because "post",
# "order", "like" and "star" are all common NOUNS in these goals; a bag-of-verbs
# scan mislabels "help me find the most recent post of it" as a modification.
IMPERATIVE_MODIFICATION = re.compile(
    r"^\s*(?:please\s+)?(post|add|create|order|buy|purchase|upvote|downvote|like"
    r"|dislike|subscribe|unsubscribe|delete|remove|edit|update|set|change|submit"
    r"|send|upload|assign|close|fork|star|rename|draft|reply|rate|cancel|schedule"
    r"|book|apply|approve|reject|install|enable|disable|mark|make|write|leave"
    r"|open an|start a|increase|decrease|reduce|raise|lower|modify|configure"
    r"|register|checkout|place)\b", re.I)

# Deictic reference to an image the goal treats as its premise.
IMAGE_PREMISE = re.compile(
    r"(input image|this image|the image|this picture|the picture|this exact item"
    r"|on this page whose image|shown in the (image|picture)|pictured)", re.I)

ABSTENTION_ACTIONS = ("send_msg_to_user", "report_infeasible")
STATE_CHANGING = ("fill", "select_option", "upload_file", "clear")

# Application-specific search-results routes. This table is explicitly NOT
# general: it is a per-application declaration, and any rule using it inherits
# that scope.
SEARCH_ROUTE_PATTERNS = [
    (r"openstreetmap", r"/search\?query="),
    (r"wa-shopping", r"catalogsearch/result"),
    (r"vwa-shopping", r"catalogsearch/result"),
    (r"gitlab", r"/search\?"),
    (r"reddit|forum", r"/search\?"),
    (r"", r"[?&]q=|[?&]query=|[?&]search="),
]


def assert_no_oracle_fields(record):
    """Fail loudly if a rule input record carries benchmark-only truth."""
    leaked = ORACLE_FIELDS & set(record)
    if leaked:
        raise AssertionError(f"oracle leakage into rule input: {sorted(leaked)}")


def parse_action(raw):
    raw = raw.strip()
    name = raw.split("(")[0].strip()
    arg = raw[len(name):].strip()
    if arg.startswith("(") and arg.endswith(")"):
        arg = arg[1:-1]
    return name, arg


def extract_features(judgment):
    """Production-visible features only. Nothing here requires the answer.

    Every field is something a deployed evaluator observes at evaluation time:
    the user's goal, the agent's own tool calls and their arguments, the URLs the
    session visited, and whether the evaluator itself was handed an image.
    """
    goal = judgment["goal"]
    user_msg = judgment["chat_messages"]["regular"][1]["content"]
    steps = STEP_RE.findall(user_msg)

    actions = []
    for _, url, raw in steps:
        name, arg = parse_action(raw)
        actions.append({"url": url.strip(), "action": name, "arg": arg})

    real = [a for a in actions if a["action"] not in ("None", "")]
    urls = [a["url"] for a in actions if a["url"]]
    final_url = urls[-1] if urls else ""
    host = urllib.parse.urlparse(final_url).netloc if final_url else ""

    infeasible_calls = [a for a in real if a["action"] == "report_infeasible"]
    terminal = real[-1] if real else None

    # Does the evaluator's own input contain an image? Determined from the
    # evaluator's configuration, which it trivially knows about itself.
    ja = judgment.get("judge_args") or {}
    evaluator_has_image = bool(ja.get("use_screenshot"))

    return {
        "goal": goal,
        "goal_first_line": goal.strip().split("\n")[0],
        "n_steps": len(actions),
        "actions": actions,
        "action_names": [a["action"] for a in real],
        "final_url": final_url,
        "final_host": host,
        "terminal_action": terminal["action"] if terminal else None,
        "terminal_arg": terminal["arg"] if terminal else "",
        "infeasible_reasons": [a["arg"] for a in infeasible_calls],
        "has_state_changing_action": any(a["action"] in STATE_CHANGING for a in real),
        "evaluator_has_image": evaluator_has_image,
        "evaluator_input_chars": len(user_msg),
        "caption_present": CAPTION_MARKER in user_msg,
    }


# -- FROZEN RULES --------------------------------------------------------------
# Each returns (fired: bool, detail: str). None may read an oracle field.

def rule_r1_contradictory_infeasibility(f):
    """R1 SELF-CONTRADICTORY INFEASIBILITY CLAIM.

    The agent invoked the "this task cannot be done" tool while the reason it
    passed asserts the task WAS done. Whatever the truth, the agent's own
    terminal self-report is internally incoherent, so it is not admissible as
    evidence of success. Disposition: escalate + evidence-against, NOT a veto --
    the agent may have completed the task and merely misused the tool.
    """
    for reason in f["infeasible_reasons"]:
        if COMPLETION_ASSERTION.search(reason):
            return True, f"report_infeasible reason asserts completion: {reason[:120]}"
    return False, ""


def rule_r2_negative_selfreport_on_modification(f):
    """R2 NEGATIVE SELF-REPORT ON AN IMPERATIVE MODIFICATION GOAL.

    The goal opens with an imperative modification verb, and the agent's terminal
    message asserts it could not do it / the target does not exist. A request to
    change state is not satisfied by a report that the change was not made.
    Disposition: VETO of a SUCCESS verdict.

    Deliberately keyed on the agent's explicit NEGATIVE assertion, not on the
    absence of state-changing actions -- see the red-team note in the audit: a
    modification goal can legitimately require no action if the desired state
    already holds, and 'a state-changing action occurred' establishes effort,
    not success.
    """
    if not IMPERATIVE_MODIFICATION.match(f["goal_first_line"]):
        return False, ""
    if f["terminal_action"] not in ABSTENTION_ACTIONS:
        return False, ""
    # Precision guard, added 2026-09-29 from a LABEL-BLIND inspection of firings
    # before any outcome was scored. "...has been successfully created. No further
    # actions are required." matches NEGATIVE_SELF_REPORT on the bare "no ", but
    # it is a completion claim, not a negative self-report. A message that asserts
    # completion is not evidence against completion.
    if COMPLETION_ASSERTION.search(f["terminal_arg"]):
        return False, ""
    if NEGATIVE_SELF_REPORT.search(f["terminal_arg"]):
        return True, f"modification goal + negative terminal report: {f['terminal_arg'][:120]}"
    return False, ""


def rule_r3_unverifiable_image_premise(f):
    """R3 UNVERIFIABLE IMAGE PREMISE.

    The goal's success condition is defined by an image ("this exact item", "the
    product in this picture"), and the evaluator was handed no image. A material
    conjunct of the task is therefore not evaluable from the evaluator's input.
    This is an evidence-absence test, not an uncertainty test: it fires on the
    structure of the input, never on how confident the evaluator feels.

    Disposition: emit UNVERIFIABLE. Blocks a SUCCESS verdict and escalates; does
    NOT assert failure.
    """
    if f["evaluator_has_image"]:
        return False, ""
    if IMAGE_PREMISE.search(f["goal"]):
        return True, "goal premise is an image; evaluator input contains no image"
    return False, ""


def _search_route(host, url):
    for host_pat, route_pat in SEARCH_ROUTE_PATTERNS:
        if host_pat and not re.search(host_pat, host, re.I):
            continue
        if re.search(route_pat, url, re.I):
            return route_pat
    return None


def rule_r4_terminal_search_route(f):
    """R4 TERMINAL SEARCH-RESULTS ROUTE (APPLICATION-SPECIFIC).

    The session's final URL is a search-results route rather than a detail route.
    Reaching a list of candidates is an affordance for completing a locate-item
    goal, not the completion of one.

    This rule is application-specific by construction: it depends on the declared
    SEARCH_ROUTE_PATTERNS table, and it is blind to single-page applications that
    open detail views in a modal without changing the URL. Disposition:
    supplemental evidence / rubric input only. NOT a veto.
    """
    if not f["final_url"]:
        return False, ""
    pat = _search_route(f["final_host"], f["final_url"])
    if pat:
        return True, f"final URL is a search route ({pat}) on {f['final_host']}"
    return False, ""


RULES = {
    "R1_contradictory_infeasibility": (rule_r1_contradictory_infeasibility,
                                       "escalate + evidence-against"),
    "R2_negative_selfreport_modification": (rule_r2_negative_selfreport_on_modification,
                                            "veto SUCCESS"),
    "R3_unverifiable_image_premise": (rule_r3_unverifiable_image_premise,
                                      "UNVERIFIABLE (block SUCCESS, escalate)"),
    "R4_terminal_search_route": (rule_r4_terminal_search_route,
                                 "supplemental evidence (app-specific)"),
}


def iter_cases():
    for benchmark in sorted(os.listdir(JUDGMENTS)):
        bdir = os.path.join(JUDGMENTS, benchmark)
        for agent in sorted(os.listdir(bdir)):
            aer = os.path.join(bdir, agent, "aer")
            if not os.path.isdir(aer):
                continue
            for fn in sorted(os.listdir(aer)):
                yield benchmark, agent, fn[:-5], os.path.join(aer, fn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage", action="store_true")
    ap.add_argument("--dump")
    args = ap.parse_args()

    counts = collections.Counter()
    per_bench = collections.defaultdict(collections.Counter)
    out = {}
    n = 0
    for benchmark, agent, task, path in iter_cases():
        with open(path, encoding="utf-8") as fh:
            judgment = json.load(fh)
        f = extract_features(judgment)
        assert_no_oracle_fields(f)
        n += 1
        fires = {}
        for name, (fn, _) in RULES.items():
            hit, detail = fn(f)
            fires[name] = {"fired": hit, "detail": detail}
            if hit:
                counts[name] += 1
                per_bench[name][benchmark] += 1
        out[f"{benchmark}/{agent}/{task}"] = {
            "final_url": f["final_url"],
            "terminal_action": f["terminal_action"],
            "goal_first_line": f["goal_first_line"],
            "fires": fires,
        }

    if args.coverage:
        print(f"cases: {n}\n")
        print(f"{'rule':42s} {'fires':>6s} {'rate':>7s}   disposition")
        for name, (_, disp) in RULES.items():
            c = counts[name]
            print(f"{name:42s} {c:6d} {c / n:7.1%}   {disp}")
        print("\nby benchmark:")
        for name in RULES:
            print(f"  {name:42s} {dict(per_bench[name])}")

    if args.dump:
        with open(args.dump, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)
        print(f"\nwrote {args.dump}")


if __name__ == "__main__":
    main()
