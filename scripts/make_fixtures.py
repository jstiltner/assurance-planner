"""Generate the synthetic judge-characterization fixtures in ``data/``.

Run from the repository root:

    python scripts/make_fixtures.py

Lives outside ``src/`` because the planner package is asserted to contain no
randomness, and because the generated YAML -- not the generator -- is the artefact
under review.  The output is committed so a reader can inspect and edit the data
without running anything.

These evaluators are built to *break* assumptions, not to confirm them.  A and B
are tuned to the same pooled sensitivity on purpose: if the headline metric cannot
distinguish a judge that repetition fixes from one it cannot, that is the finding.

`judge_runs_mixed.yaml` is the benchmark fixture and the only one designed for policy
comparison.  Two properties of it matter more than anything else here:

* **All regimes coexist.**  Stable-correct, noisy-informative and stable-wrong cases
  are drawn from one population, so pooled sensitivity describes none of them.

* **Slices predict regime imperfectly, on purpose.**  A fixture where `slice_id`
  perfectly identifies the stable-wrong cases would let a triage policy win by
  construction and would prove nothing.  Each slice here is a *mixture*, with the
  regime proportions differing between slices.  That is the weakest signal a triage
  policy could plausibly exploit in reality, so a policy that cannot beat early
  stopping on this data should not be expected to beat it on real data either.
"""

from __future__ import annotations

import random
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"

FAILURE_MODE = "VFD-CORRECTION-UPTAKE@v1"
POPULATION = "correction-uptake-suite"
DISTRIBUTION = "voice-agent-turntaking-r4"
MEASURED_ON = "2026-09-24"

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


def _case(
    index: int,
    present: bool,
    outcomes: str,
    note: str = "",
    slice_id: str = "",
    prefix: str = "",
) -> dict:
    tag = prefix or ("pos" if present else "neg")
    case = {
        "case_id": f"CASE-{tag}-{index:03d}",
        "failure_present": present,
        "outcomes": outcomes,
    }
    if slice_id:
        case["slice_id"] = slice_id
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
        cases.append(
            _case(
                i, True, _emit(rng, rng.uniform(0.55, 0.85), RUNS_PER_CASE),
                slice_id="uniform",
            )
        )
    for i in range(26):
        cases.append(
            _case(
                i, False, _emit(rng, rng.uniform(0.02, 0.18), RUNS_PER_CASE),
                slice_id="uniform",
            )
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
        cases.append(
            _case(i, True, _emit(rng, 0.96, RUNS_PER_CASE), slice_id="rubric-aligned")
        )
    for i in range(17, 24):
        cases.append(
            _case(
                i,
                True,
                _emit(rng, 0.03, RUNS_PER_CASE),
                note="rubric reads the correction as an unrelated new assertion",
                slice_id="rubric-blind",
            )
        )
    for i in range(23):
        cases.append(
            _case(i, False, _emit(rng, 0.02, RUNS_PER_CASE), slice_id="rubric-aligned")
        )
    for i in range(23, 26):
        cases.append(
            _case(
                i,
                False,
                _emit(rng, 0.52, RUNS_PER_CASE),
                note="agent restates the value verbatim; rubric treats that as a miss",
                slice_id="rubric-blind",
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
        _case(i, True, "1" if i < 9 else "0", slice_id="pilot") for i in range(10)
    ] + [_case(i, False, "1" if i == 0 else "0", slice_id="pilot") for i in range(10)]
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


# --------------------------------------------------------------------------------
# The benchmark fixture
# --------------------------------------------------------------------------------

#: Per-regime flag probability for a reference-positive and a reference-negative case.
#: "stable_wrong" is the regime the whole exercise is about: the judge is confident and
#: on the wrong side, so repetition converges away from the reference label.
REGIMES = {
    "stable_correct": (0.97, 0.03),
    "noisy_informative": (0.72, 0.28),
    "stable_wrong": (0.04, 0.95),
}

#: Regime mixture per slice.  None of these is pure, and that is the point -- see the
#: module docstring.  A triage policy calibrated on one fold of a slice learns a
#: *propensity*, not a lookup table, and must still pay for the cases it gets wrong.
SLICE_MIXTURES = {
    #: Unambiguous corrections.  Nearly always handled correctly.
    "explicit-restatement": {"stable_correct": 0.88, "noisy_informative": 0.12},
    #: Semantically borderline.  Genuinely noisy; this is where repetition earns money.
    "implicit-correction": {"noisy_informative": 0.80, "stable_correct": 0.20},
    #: A construction the rubric systematically mis-reads -- but only most of the time.
    "verbatim-readback": {
        "stable_wrong": 0.60,
        "noisy_informative": 0.25,
        "stable_correct": 0.15,
    },
}

#: Cases per slice, split evenly between reference-positive and reference-negative.
SLICE_SIZES = {
    "explicit-restatement": 24,
    "implicit-correction": 24,
    "verbatim-readback": 20,
}

#: A fourth slice at two repetitions instead of eight.  Regime D from the brief lives
#: here: within-slice estimates are real but far too wide to act on, and a policy that
#: ignores that is making an unfunded claim.
SPARSE_SLICE = "escalation-handoff"
SPARSE_CASES = 8
SPARSE_RUNS = 2


def _pick_regime(rng: random.Random, mixture: dict[str, float]) -> str:
    draw = rng.random()
    cumulative = 0.0
    for regime, weight in mixture.items():
        cumulative += weight
        if draw < cumulative:
            return regime
    return next(reversed(mixture))


def mixed_population(rng: random.Random) -> dict:
    """The benchmark. Every regime, three imperfectly-predictive slices, plus a sparse one."""
    cases = []
    index = 0
    for slice_id, size in SLICE_SIZES.items():
        for position in range(size):
            present = position % 2 == 0
            regime = _pick_regime(rng, SLICE_MIXTURES[slice_id])
            positive_rate, negative_rate = REGIMES[regime]
            rate = positive_rate if present else negative_rate
            cases.append(
                _case(
                    index,
                    present,
                    _emit(rng, rate, RUNS_PER_CASE),
                    slice_id=slice_id,
                    prefix="mix",
                    #: The regime is recorded in the note for a *reader*.  No loader
                    #: parses it and no policy may read it: a policy that knew the
                    #: regime would be scoring itself on the answer key.
                    note=f"generated regime: {regime}",
                )
            )
            index += 1

    for position in range(SPARSE_CASES):
        present = position % 2 == 0
        regime = _pick_regime(
            rng, {"stable_correct": 0.5, "noisy_informative": 0.3, "stable_wrong": 0.2}
        )
        positive_rate, negative_rate = REGIMES[regime]
        rate = positive_rate if present else negative_rate
        cases.append(
            _case(
                index,
                present,
                _emit(rng, rate, SPARSE_RUNS),
                slice_id=SPARSE_SLICE,
                prefix="mix",
                note=f"generated regime: {regime}",
            )
        )
        index += 1

    return {
        "evaluator": "correction_uptake_judge@v4",
        "note": (
            "Synthetic benchmark population. Stable-correct, noisy-informative and "
            "stable-wrong cases are drawn from one population, so no pooled "
            "sensitivity describes any of them. Slices predict regime imperfectly on "
            "purpose: a fixture where slice_id identified the stable-wrong cases "
            "exactly would let a triage policy win by construction. Regimes are "
            "recorded in per-case notes for the reader and are not loaded; a policy "
            "that read them would be scoring itself against the answer key."
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
        "measured_on": MEASURED_ON,
        "limitations": [
            "synthetic data generated by scripts/make_fixtures.py; no real evaluator "
            "was run and no claim about any real judge follows from it"
        ],
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
    print(
        f"{path.name:34} cases={len(payload['cases']):3d}  "
        f"sensitivity={sensitivity:.3f}  fpr={fpr:.3f}"
    )


def main() -> None:
    DATA.mkdir(exist_ok=True)
    #: Fixed seeds.  The committed YAML is the artefact; the seed only makes it
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
    write("judge_runs_mixed.yaml", mixed_population(random.Random(20260929)))


if __name__ == "__main__":
    main()
