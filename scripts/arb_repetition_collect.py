"""Collect R=5 repeat judge executions for all 1,106 study cases.

Frozen study per predeclaration commit 9fabf4702e48ea163a145c8c5f98b39df885c30b,
Amendment 3.  This script is data-collection only.

Estimand: judge-stage empirical repeatability conditional on fixed semantic evidence
under the deployed configuration (gpt-4o-2024-11-20, temperature 0.0, seed 0).

Do not call this full-pipeline repeatability.

Concurrency model: cases are processed in parallel (MAX_CONCURRENT coroutines);
repetitions within each case are sequential so collection order is well-defined.
asyncio is single-threaded — checkpoint writes are safe without an external lock.

Output: data/REAL_arb_repetition_raw.jsonl  (append-safe checkpoint)
"""

import asyncio
import json
import os
import pathlib
import subprocess
import sys
import time
import yaml

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent

_KEY = os.environ.get("OPENAI_API_KEY", "")
if not _KEY:
    sys.exit("OPENAI_API_KEY not set — cannot proceed")

from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=_KEY)

# ---------- frozen configuration --------------------------------------------------

MODEL = "gpt-4o-2024-11-20"
TEMPERATURE = 0.0
SEED = 0
MAX_COMPLETION_TOKENS = 1024
R = 5
COST_GUARD_USD = 75.0
MAX_CONCURRENT = 3             # final pass: reduced to avoid 429 storm on last 83 cases
BASELINE_COST_PER_CASE = 0.0105

# ---------- pricing: gpt-4o-2024-11-20 (USD per token) ---------------------------

PRICE_INPUT = 2.50 / 1_000_000
PRICE_CACHED = 1.25 / 1_000_000
PRICE_OUTPUT = 10.00 / 1_000_000

# ---------- paths -----------------------------------------------------------------

HF_REV = "b6d17e646009d6cb63d5dd7be78807b680693f61"
HF_CACHE = (
    pathlib.Path.home() / ".cache" / "huggingface" / "hub"
    / "datasets--McGill-NLP--agent-reward-bench" / "snapshots" / HF_REV
)
JUDGMENTS_DIR = HF_CACHE / "judgments"
CHECKPOINT = ROOT / "data" / "REAL_arb_repetition_raw.jsonl"
LOCK_FILE = ROOT / "data" / ".arb_collect.lock"
PAIR_FILE = ROOT / "data" / "REAL_arb_functional_x_aer.yaml"


# ---------- verdict parsing -------------------------------------------------------

def clean_label(label):
    if label is None or label == "":
        return None
    return label.strip().lower().replace("'", "").replace('"', "")


def numerize_success(label):
    label = clean_label(label)
    if label is None or label == "n/a":
        return None
    if label in ("successful", "yes", "success"):
        return 1
    if label in ("unsuccessful", "no", "failure", "unsuccesful"):
        return 0
    return None


def parse_aer_verdict(content):
    """(verdict_raw, verdict_correct_success) from judge response text."""
    raw = None
    for line in content.split("\n"):
        if line.startswith("Status:"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                raw = parts[1].strip()
    return raw, numerize_success(raw)


# ---------- cost ------------------------------------------------------------------

def compute_cost(usage):
    """(cost, prompt_tokens, cached_tokens, uncached_tokens, output_tokens)."""
    prompt_tokens = usage.prompt_tokens
    output_tokens = usage.completion_tokens
    cached = 0
    if hasattr(usage, "prompt_tokens_details") and usage.prompt_tokens_details:
        cached = usage.prompt_tokens_details.cached_tokens or 0
    uncached = prompt_tokens - cached
    cost = (
        uncached * PRICE_INPUT
        + cached * PRICE_CACHED
        + output_tokens * PRICE_OUTPUT
    )
    return cost, prompt_tokens, cached, uncached, output_tokens


# ---------- checkpoint ------------------------------------------------------------

def load_checkpoint():
    """(done_set, cumulative_cost).  done_set = valid (case_id, rep_idx) pairs."""
    done = set()
    total_cost = 0.0
    if not CHECKPOINT.exists():
        return done, total_cost
    with open(CHECKPOINT, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue  # truncated line from a previous SIGKILL — skip
            if rec.get("call_status") == "valid":
                done.add((rec["case_id"], rec["repetition_index"]))
                total_cost += rec.get("billed_cost", 0) or 0
    return done, total_cost


def append_record(rec):
    with open(CHECKPOINT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


# ---------- shared mutable state (safe: single asyncio event loop) ----------------

class State:
    done: set
    cumulative_cost: float
    calls_this_run: int
    cost_this_run: float
    target: int
    t_start: float

    def __init__(self, done, cumulative_cost, target):
        self.done = done
        self.cumulative_cost = cumulative_cost
        self.target = target
        self.calls_this_run = 0
        self.cost_this_run = 0.0
        self.t_start = time.monotonic()

    def check_cost_guard(self):
        # Guard on cumulative spend only.  Projection-based guards false-alarm
        # when early cases happen to come from an expensive slice.  Expected
        # total is ~$58; $75 allows 30% headroom before halting.
        if self.cumulative_cost > COST_GUARD_USD:
            raise SystemExit(
                f"\nCOST GUARD: cumulative ${self.cumulative_cost:.2f} "
                f"> guard ${COST_GUARD_USD:.2f}.\n"
                f"  done={len(self.done)}, remaining={self.target - len(self.done)}\n"
                f"  Investigate before continuing (wrong model, duplicate calls, "
                f"wrong prompt, runaway retries)."
            )

    def record_valid(self, case_id, rep_idx, cost, case_pos):
        self.done.add((case_id, rep_idx))
        self.cumulative_cost += cost
        self.calls_this_run += 1
        self.cost_this_run += cost
        n = len(self.done)
        if n % 200 == 0:
            elapsed = time.monotonic() - self.t_start
            rate = self.calls_this_run / elapsed if elapsed > 0 else 0
            rem = self.target - n
            eta_s = rem / rate if rate > 0 else 0
            print(
                f"Progress: {n}/{self.target} ({n/self.target*100:.1f}%) | "
                f"${self.cumulative_cost:.2f} total | "
                f"{rate:.1f} calls/s | ETA ~{eta_s/60:.0f}m | "
                f"case {case_pos}/1106"
            )


# ---------- per-case coroutine ----------------------------------------------------

async def run_case(sem, state, case, case_pos, judgment_lookup):
    case_id = case["case_id"]
    slice_id = case["slice_id"]
    reference_label = case["reference_label"]
    reference_correct_success = 1 if reference_label == "pass" else 0

    p = case_id.split("/")
    jpath = judgment_lookup[f"{p[0]}/{p[1]}/{p[2]}"]
    with open(jpath, encoding="utf-8") as f:
        judgment = json.load(f)
    chat_messages = judgment["chat_messages"]["regular"]

    async with sem:
        for rep_idx in range(1, R + 1):
            if (case_id, rep_idx) in state.done:
                continue

            state.check_cost_guard()

            MAX_RETRIES = 3
            response = None
            last_error = None
            latency_ms = None
            attempts_made = 0

            for attempt in range(MAX_RETRIES):
                attempts_made = attempt
                try:
                    t0 = time.monotonic()
                    response = await client.chat.completions.create(
                        model=MODEL,
                        messages=chat_messages,
                        temperature=TEMPERATURE,
                        seed=SEED,
                        max_completion_tokens=MAX_COMPLETION_TOKENS,
                    )
                    latency_ms = round((time.monotonic() - t0) * 1000)
                    last_error = None
                    break
                except Exception as exc:
                    last_error = repr(exc)
                    if attempt < MAX_RETRIES - 1:
                        if "429" in last_error:
                            # Extract "try again in Xs" hint; fallback to 35s
                            import re as _re
                            m = _re.search(r'try again in (\d+)ms', last_error)
                            wait = (int(m.group(1)) / 1000 + 2) if m else 35.0
                        else:
                            wait = 2 ** attempt
                        await asyncio.sleep(wait)

            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            if last_error is not None:
                rec = {
                    "case_id": case_id, "slice_id": slice_id,
                    "repetition_index": rep_idx,
                    "call_status": "transport_failure",
                    "error": last_error[:500],
                    "reference_label": reference_label,
                    "timestamp": timestamp,
                    "retry_count": attempts_made,
                }
                append_record(rec)
                print(
                    f"  TRANSPORT FAILURE  {case_id[:55]}  rep {rep_idx}:  "
                    f"{last_error[:60]}"
                )
                continue

            content = response.choices[0].message.content
            if content is None:
                rec = {
                    "case_id": case_id, "slice_id": slice_id,
                    "repetition_index": rep_idx,
                    "call_status": "provider_failure",
                    "error": "null content",
                    "reference_label": reference_label,
                    "timestamp": timestamp,
                }
                append_record(rec)
                print(f"  PROVIDER FAILURE   {case_id[:55]}  rep {rep_idx}")
                continue

            verdict_raw, verdict_correct_success = parse_aer_verdict(content)
            call_status = (
                "valid" if verdict_correct_success is not None else "parse_failure"
            )
            is_correct = None
            if verdict_correct_success is not None:
                is_correct = verdict_correct_success == reference_correct_success

            cost, prompt_tokens, cached_tokens, uncached_tokens, output_tokens = (
                compute_cost(response.usage)
            )

            rec = {
                "case_id": case_id,
                "slice_id": slice_id,
                "repetition_index": rep_idx,
                "timestamp": timestamp,
                "model": response.model,
                "temperature": TEMPERATURE,
                "seed": SEED,
                "verdict_raw": verdict_raw,
                "verdict_correct_success": verdict_correct_success,
                "is_correct": is_correct,
                "reference_label": reference_label,
                "reference_correct_success": reference_correct_success,
                "response_content": content,
                "system_fingerprint": getattr(response, "system_fingerprint", None),
                "input_tokens": prompt_tokens,
                "cached_input_tokens": cached_tokens,
                "uncached_input_tokens": uncached_tokens,
                "output_tokens": output_tokens,
                "billed_cost": cost,
                "latency_ms": latency_ms,
                "retry_count": attempts_made,
                "call_status": call_status,
                "chat_messages_variant": "regular",
            }
            append_record(rec)

            if call_status == "valid":
                state.record_valid(case_id, rep_idx, cost, case_pos)
            else:
                print(
                    f"  PARSE FAILURE      {case_id[:55]}  rep {rep_idx}:  "
                    f"raw={verdict_raw!r}"
                )


# ---------- main ------------------------------------------------------------------

async def amain():
    # Prevent concurrent runs from creating duplicate records
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text().strip())
            import psutil
            if psutil.pid_exists(old_pid):
                sys.exit(
                    f"Lock file {LOCK_FILE} exists and PID {old_pid} is running.\n"
                    "Stop that process first."
                )
            # Stale lock from a process that was SIGKILL'd
            LOCK_FILE.unlink()
            print(f"Removed stale lock file (dead PID {old_pid})")
        except Exception:
            # Can't verify; remove the lock and proceed (likely stale)
            LOCK_FILE.unlink(missing_ok=True)
            print("Removed unverifiable lock file")
    LOCK_FILE.write_text(str(os.getpid()))

    import atexit, signal

    def _cleanup():
        LOCK_FILE.unlink(missing_ok=True)

    atexit.register(_cleanup)

    def _sigterm(*_):
        _cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _sigterm)

    try:
        await _amain_locked()
    finally:
        _cleanup()


async def _amain_locked():
    # Verify frozen commit
    r = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    actual = r.stdout.strip()
    expected = "9fabf4702e48ea163a145c8c5f98b39df885c30b"
    if actual != expected:
        sys.exit(
            f"Commit mismatch.\n  expected: {expected}\n  actual:   {actual}\n"
            "  Working tree must be at the frozen pre-inference commit."
        )
    print(f"Commit verified: {actual}")

    with open(PAIR_FILE, encoding="utf-8") as f:
        pair_data = yaml.safe_load(f)
    cases = pair_data["cases"]
    assert len(cases) == 1106

    aer_jsons = list(JUDGMENTS_DIR.rglob("*/aer/*.json"))
    judgment_lookup = {}
    for p in aer_jsons:
        parts = p.parts
        key = f"{parts[-4]}/{parts[-3]}/{p.stem}"
        judgment_lookup[key] = p

    missing = [
        c["case_id"] for c in cases
        if (lambda p: f"{p[0]}/{p[1]}/{p[2]}" not in judgment_lookup)(
            c["case_id"].split("/")
        )
    ]
    if missing:
        sys.exit(f"Missing chat_messages for {len(missing)} cases")
    print("chat_messages verified for all 1,106 cases")

    done, cumulative_cost = load_checkpoint()
    target = len(cases) * R
    print(f"Checkpoint: {len(done)}/{target} valid, ${cumulative_cost:.4f} spent")
    print(f"Remaining: {target - len(done)} valid executions")
    print(f"Concurrency: {MAX_CONCURRENT} cases in parallel")
    remaining_estimate = (target - len(done)) * BASELINE_COST_PER_CASE
    print(f"Estimated remaining spend: ~${remaining_estimate:.2f} (baseline ${BASELINE_COST_PER_CASE}/call)")
    print(f"Note: assistantbench cases (~9% of corpus) cost ~$0.016/call; other slices cheaper")
    print()

    state = State(done, cumulative_cost, target)
    sem = asyncio.Semaphore(MAX_CONCURRENT)

    tasks = [
        run_case(sem, state, case, idx + 1, judgment_lookup)
        for idx, case in enumerate(cases)
    ]
    await asyncio.gather(*tasks)

    print(f"\nCollection complete.")
    print(f"  Valid executions:  {len(state.done)}/{target}")
    print(f"  Total API spend:   ${state.cumulative_cost:.4f}")
    print(f"  Calls this run:    {state.calls_this_run}")
    print(f"  Cost this run:     ${state.cost_this_run:.4f}")
    if len(state.done) < target:
        print(f"  WARNING: {target - len(state.done)} repetition slots have no valid result")


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
