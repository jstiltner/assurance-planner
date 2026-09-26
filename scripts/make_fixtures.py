"""Generate the synthetic judge-characterization fixtures in ``data/``.

Run from the repository root:

    python scripts/make_fixtures.py

Lives outside ``src/`` because the planner package is asserted to contain no
randomness, and because the generated YAML -- not the generator -- is the artefact
under review.  The output is committed so a reader can inspect and edit the data
without running anything.

These three evaluators are built to *break* assumptions, not to confirm them.  A and B
are tuned to the same pooled sensitivity on purpose: if the headline metric cannot
distinguish a judge that repetition fixes from one it cannot, that is the finding.
"""

from __future__ import annotations

import random
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"

FAILURE_MODE = "VFD-CORRECTION-UPTAKE@v1"
POPULATION = "correction-uptake-suite"
DISTRIBUTION = "voice-agent-turntaking-r4"

#: A behavioural failure that needs semantic judgement: whether the agent took up a
#: correction is not decidable from a transcript by pattern match, and two careful
#: humans can disagree on the borderline cases.  Explicitly not the full-duplex
#: silence defect, which a state machine settles.
FAILURE_DESCRIPTION = (
    "Caller corrects a value the agent has already read back, mid-turn, and the agent "
    "continues on the uncorrected value without acknowledging the correction."
)

RUNS_PER_CASE = 8


def _emit(rng: random.Random, probability: float, runs: int) -> str:
    return "".join("1" if rng.random() < probability else "0" for _ in range(runs))


def _case(index: int, present: bool, outcomes: str, note: str = "") -> dict:
    case = {
        "case_id": f"CASE-{'pos' if present else 'neg'}-{index:03d}",
        "failure_present": present,
        "outcomes": outcomes,
    }
    if note:
        case["note"] = note
    return case


def noisy_but_useful(rng: random.Random) -> dict:
    """A. Genuinely stochastic, centred on the right answer.  Repetition works.

    Every case's own flag rate sits on the correct side of the threshold; none is
    stuck.  This is the evaluator the planner's binomial model actually describes, and
    it is included so the diagnostics can be shown not to cry wolf.
    """
    cases = []
    for i in range(24):
        cases.append(_case(i, True, _emit(rng, rng.uniform(0.55, 0.85), RUNS_PER_CASE)))
    for i in range(26):
        cases.append(
            _case(i, False, _emit(rng, rng.uniform(0.02, 0.18), RUNS_PER_CASE))
        )
    return {
        "evaluator": "correction_uptake_judge@v4",
        "note": (
            "Synthetic. Every case fluctuates around its correct label; no case is "
            "systematically misjudged. Included as the control: the diagnostics "
            "should report that independence is plausible here."
        ),
        "cases": cases,
    }


def systematically_wrong_subset(rng: random.Random) -> dict:
    """B. Same pooled sensitivity as A, built from a completely different structure.

    Seventeen of twenty-four positive cases are near-certain flags and seven are
    near-certain misses -- cases where the rubric simply disagrees with the reference
    label. Repetition cannot rescue those seven, but the aggregate cannot see them.
    """
    cases = []
    for i in range(17):
        cases.append(_case(i, True, _emit(rng, 0.96, RUNS_PER_CASE)))
    for i in range(17, 24):
        cases.append(
            _case(
                i,
                True,
                _emit(rng, 0.03, RUNS_PER_CASE),
                note="rubric reads the correction as an unrelated new assertion",
            )
        )
    for i in range(23):
        cases.append(_case(i, False, _emit(rng, 0.02, RUNS_PER_CASE)))
    for i in range(23, 26):
        cases.append(
            _case(
                i,
                False,
                _emit(rng, 0.52, RUNS_PER_CASE),
                note="agent restates the value verbatim; rubric treats that as a miss",
            )
        )
    return {
        "evaluator": "rubric_uptake_judge@v2",
        "note": (
            "Synthetic. Tuned to roughly the same pooled sensitivity as "
            "correction_uptake_judge@v4 while being a structurally different "
            "evaluator: most cases are near-deterministic and a minority are "
            "near-deterministically wrong. If sensitivity alone drives planning, "
            "these two are indistinguishable."
        ),
        "cases": cases,
    }


def strong_but_barely_measured(rng: random.Random) -> dict:
    """C. Excellent point estimate, ten cases, one run each.  Nothing is known."""
    cases = [
        _case(i, True, "1" if i < 9 else "0") for i in range(10)
    ] + [_case(i, False, "1" if i == 0 else "0") for i in range(10)]
    return {
        "evaluator": "correction_uptake_judge@v6",
        "note": (
            "Synthetic. A pilot: twenty cases, one run each. Sensitivity 0.90 and a "
            "false-positive rate of 0.10 look better than either evaluator above, and "
            "the intervals are wide enough that the comparison means nothing. Also "
            "exercises the path where within-case variance is undefined."
        ),
        "cases": cases,
    }


def write(name: str, payload: dict) -> None:
    import yaml

    document = {
        "evaluator": payload["evaluator"],
        "failure_mode": FAILURE_MODE,
        "failure_description": FAILURE_DESCRIPTION,
        "population": POPULATION,
        "measured_against": DISTRIBUTION,
        "note": payload["note"],
        "cases": payload["cases"],
    }
    path = DATA / name
    path.write_text(
        yaml.safe_dump(document, sort_keys=False, width=88), encoding="utf-8"
    )
    positives = [c for c in payload["cases"] if c["failure_present"]]
    negatives = [c for c in payload["cases"] if not c["failure_present"]]
    sensitivity = sum(c["outcomes"].count("1") for c in positives) / sum(
        len(c["outcomes"]) for c in positives
    )
    fpr = sum(c["outcomes"].count("1") for c in negatives) / sum(
        len(c["outcomes"]) for c in negatives
    )
    print(f"{path.name:34} sensitivity={sensitivity:.3f}  fpr={fpr:.3f}")


def main() -> None:
    DATA.mkdir(exist_ok=True)
    #: Fixed seed.  The committed YAML is the artefact; the seed only makes it
    #: reproducible if someone wants to change the generating assumptions.
    write("judge_runs_noisy.yaml", noisy_but_useful(random.Random(20260926)))
    write(
        "judge_runs_systematic.yaml",
        systematically_wrong_subset(random.Random(20260927)),
    )
    write(
        "judge_runs_small_sample.yaml",
        strong_but_barely_measured(random.Random(20260928)),
    )


if __name__ == "__main__":
    main()
