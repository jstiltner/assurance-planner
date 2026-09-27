"""Part 4: real repeated judge observations load without touching the code.

The format is what a future public corpus would be stored in, so these tests are as
much a specification as a check.  Two things they exist to protect:

* nothing proprietary is required.  ``score``, ``latency_ms`` and ``cost`` are all
  optional, and a dataset that only has verdicts is a first-class dataset;
* the ``slice_id`` is optional too, but it is the *only* handle a triage policy is
  allowed to generalise over, so a dataset without one can be characterized and cannot
  be triaged.  That asymmetry is tested rather than described.
"""

from __future__ import annotations

from datetime import date

import pytest

from assurance_planner.loader import load_characterization
from assurance_planner.policies import Calibration, HeterogeneityTriage

#: The shape from the brief, written out in full.  Kept verbatim rather than generated
#: so that a reader comparing the spec to the code has one thing to look at.
LONG_FORM = """
experiment:
  evaluator_version: correction_uptake_judge@v4
  failure_mode_version: VFD-CORRECTION-UPTAKE@v1
  population_id: correction-uptake-suite
  sut_distribution_id: voice-agent-turntaking-r4
  measured_on: 2026-09-24
  limitations:
    - collected on a single afternoon; no diurnal variation observed
cases:
  - case_id: CASE-real-001
    slice_id: implicit-correction
    reference_label: fail
    observations:
      - verdict: fail
        score: 0.91
        latency_ms: 1840
        cost: 0.0611
      - verdict: pass
        score: 0.44
        latency_ms: 2110
        cost: 0.0644
      - verdict: fail
        score: 0.88
        latency_ms: 1790
        cost: 0.0602
  - case_id: CASE-real-002
    reference_label: pass
    observations:
      - verdict: pass
      - verdict: pass
"""

MINIMAL = """
experiment:
  evaluator_version: judge@v1
  failure_mode_version: MODE@v1
  population_id: suite
  sut_distribution_id: release-1
cases:
  - case_id: CASE-001
    reference_label: fail
    observations:
      - verdict: fail
      - verdict: pass
"""


def _write(tmp_path, text: str):
    path = tmp_path / "experiment.yaml"
    path.write_text(text, encoding="utf-8")
    return load_characterization(path)


def test_the_documented_long_form_loads(tmp_path):
    run = _write(tmp_path, LONG_FORM)

    assert str(run.evaluator_version) == "correction_uptake_judge@v4"
    assert str(run.failure_mode) == "VFD-CORRECTION-UPTAKE@v1"
    assert run.population_id == "correction-uptake-suite"
    assert run.distribution_id == "voice-agent-turntaking-r4"
    assert run.measured_on == date(2026, 9, 24)
    assert run.limitations == (
        "collected on a single afternoon; no diurnal variation observed",
    )

    first, second = run.cases
    assert first.reference_label is True
    assert first.outcomes == (True, False, True)
    assert first.slice_id == "implicit-correction"
    assert first.scores == (0.91, 0.44, 0.88)
    assert first.latencies_ms == (1840.0, 2110.0, 1790.0)
    assert first.costs_usd == (0.0611, 0.0644, 0.0602)

    #: The second case supplies none of the optional fields and is still usable.
    assert second.reference_label is False
    assert second.outcomes == (False, False)
    assert second.slice_id == ""
    assert second.scores == ()
    assert second.costs_usd == ()


def test_nothing_proprietary_is_required(tmp_path):
    """Verdicts and labels only.  Everything else is optional by design."""
    run = _write(tmp_path, MINIMAL)
    case = run.cases[0]

    assert case.runs == 2
    assert case.flags == 1
    assert run.measured_on is None
    assert run.limitations == ()


def test_a_dataset_without_slices_can_be_measured_but_not_triaged(tmp_path):
    """The asymmetry that keeps the triage policy honest.

    Slices are the only generalisation handle a policy may use.  A dataset with no
    slices therefore has no calibration for the policy to act on, and the policy must
    fall back to the standard rule rather than inventing a route.  A policy that did
    something clever here would necessarily be keying on the case itself.
    """
    run = _write(tmp_path, MINIMAL)
    #: The unlabelled cases are one pseudo-slice, so the fold machinery still has
    #: something to partition on.  Calibration is built for it like any other.
    assert run.slices == ("",)

    calibration = Calibration.from_run(run)
    assert "" in calibration.slices
    #: But the triage policy refuses it, because routing the entire unlabelled
    #: population one way is a population-level decision, not triage.
    assert HeterogeneityTriage().route("", calibration) == "standard"


def test_a_verdict_spelling_nobody_uses_is_rejected_not_guessed(tmp_path):
    text = MINIMAL.replace("verdict: fail", "verdict: probably")
    with pytest.raises(ValueError, match="is not one of"):
        _write(tmp_path, text)


def test_partial_cost_annotation_is_rejected(tmp_path):
    """Half a cost column would silently understate the cost of every policy."""
    text = MINIMAL.replace(
        "      - verdict: fail\n", "      - verdict: fail\n        cost: 0.06\n"
    )
    with pytest.raises(ValueError, match="supply it on all or none"):
        _write(tmp_path, text)


def test_a_case_with_no_observations_is_rejected(tmp_path):
    text = """
experiment:
  evaluator_version: judge@v1
  failure_mode_version: MODE@v1
  population_id: suite
  sut_distribution_id: release-1
cases:
  - case_id: CASE-001
    reference_label: fail
    observations: []
"""
    with pytest.raises(ValueError, match="must be non-empty"):
        _write(tmp_path, text)


def test_the_short_bitstring_form_still_loads(tmp_path):
    """The fixtures in ``data/`` use it, and it is far easier to read and edit by hand."""
    text = """
evaluator: judge@v1
failure_mode: MODE@v1
population: suite
measured_against: release-1
cases:
  - case_id: CASE-001
    failure_present: true
    slice_id: some-slice
    outcomes: "11010"
"""
    run = _write(tmp_path, text)
    assert run.cases[0].outcomes == (True, True, False, True, False)
    assert run.cases[0].slice_id == "some-slice"


def test_an_outcomes_string_with_other_characters_is_rejected(tmp_path):
    text = """
evaluator: judge@v1
failure_mode: MODE@v1
population: suite
measured_against: release-1
cases:
  - case_id: CASE-001
    failure_present: true
    outcomes: "11x10"
"""
    with pytest.raises(ValueError, match="string of"):
        _write(tmp_path, text)


def test_the_run_id_is_derived_from_content_not_supplied(tmp_path):
    """Two studies with the same observations get the same id; one changed bit does not.

    The id is what ties a qualification row back to a study.  Deriving it from content
    means an edited fixture cannot keep claiming to be the run that was reviewed.
    """
    original = _write(tmp_path, LONG_FORM)
    edited = _write(tmp_path, LONG_FORM.replace("verdict: pass\n        score: 0.44", "verdict: fail\n        score: 0.44"))

    assert original.run_id
    assert original.run_id != edited.run_id
    assert _write(tmp_path, LONG_FORM).run_id == original.run_id
