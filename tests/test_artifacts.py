"""Part 1: the characterization -> qualification seam, with nobody retyping anything.

The seam these tests guard used to be a human reading a report and typing four integers
into a scenario file.  Three things could go wrong there and all three are now tested:
the numbers could be mistyped, the caveats could be dropped, and the artifact could be
attached to the wrong evaluator, failure mode, population or behaviour distribution.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from assurance_planner.artifacts import (
    ARTIFACT_SCHEMA,
    ArtifactIdentityError,
    artifact_document,
    load_artifact,
    qualification_from_document,
    qualify,
    write_artifact,
)
from assurance_planner.characterization import characterize
from assurance_planner.domain import (
    FailureModeRef,
    QualificationKey,
    SourceVersionRef,
)
from assurance_planner.loader import load, load_characterization

DATA = Path(__file__).resolve().parents[1] / "data"
MAX_ERROR = 0.05


@pytest.fixture
def mixed():
    return load_characterization(DATA / "judge_runs_mixed.yaml")


@pytest.fixture
def analysis(mixed):
    return characterize(mixed, MAX_ERROR)


def _key(run) -> QualificationKey:
    return QualificationKey(
        source_version=run.evaluator_version,
        failure_mode=run.failure_mode,
        population_id=run.population_id,
        distribution_id=run.distribution_id,
    )


# --------------------------------------------------------------------------------
# Test 1: the counts reach the planner without a human in the loop
# --------------------------------------------------------------------------------


def test_characterization_output_becomes_planner_input_without_retyping(
    mixed, analysis
):
    """The four numbers the planner reads are derived, never restated.

    The assertion is deliberately made against ``analysis`` rather than against
    literals: a test that hard-coded 560 and 426 would pass even if the artifact writer
    and the analysis drifted apart, which is exactly the failure the artifact exists to
    prevent.
    """
    evidence = qualify(mixed, MAX_ERROR)
    positive_runs, true_positives, negative_runs, false_positives = (
        analysis.qualification_counts()
    )

    assert evidence.positive_cases == positive_runs
    assert evidence.true_positives == true_positives
    assert evidence.negative_cases == negative_runs
    assert evidence.false_positives == false_positives
    assert evidence.sensitivity == pytest.approx(analysis.sensitivity.point)
    assert evidence.false_positive_rate == pytest.approx(
        analysis.false_positive_rate.point
    )


def test_the_counts_are_observations_not_cases(mixed, analysis):
    """The planner's model is Binomial over *runs*, so the counts must be runs.

    Worth pinning because 'positive cases' reads like a case count, and feeding 38
    where 296 was meant would silently make every interval three times too wide and
    every replication count too high.
    """
    positive_runs, _, negative_runs, _ = analysis.qualification_counts()
    positive_cases = sum(1 for c in mixed.cases if c.reference_label)

    assert positive_runs == sum(c.runs for c in mixed.cases if c.reference_label)
    assert positive_runs > positive_cases
    assert negative_runs == sum(c.runs for c in mixed.cases if not c.reference_label)


def test_an_undated_study_cannot_produce_a_qualification_row(mixed):
    """No clock in this package, so an undated study has to be refused.

    Staleness is decided against ``evidence_date``; defaulting it to today would make
    every artifact permanently fresh, which is the one wrong answer.
    """
    undated = mixed.with_cases(mixed.cases)
    object.__setattr__(undated, "measured_on", None)
    with pytest.raises(ValueError, match="no measured_on date"):
        artifact_document(characterize(undated, MAX_ERROR))


# --------------------------------------------------------------------------------
# Test 2: provenance and case-level detail survive the round trip
# --------------------------------------------------------------------------------


def test_provenance_survives_the_round_trip(tmp_path, mixed, analysis):
    path = write_artifact(analysis, tmp_path / "artifact.yaml")
    evidence = load_artifact(path)

    assert evidence.provenance is not None
    provenance = evidence.provenance
    assert provenance.characterization_run_id == mixed.run_id
    assert provenance.reference_positive_cases == sum(
        1 for c in mixed.cases if c.reference_label
    )
    assert provenance.cases_repetition_cannot_fix == len(analysis.unfixable_cases)
    assert provenance.artifact_ref == "artifact.yaml"
    assert evidence.evidence_date == date(2026, 9, 24)


def test_the_artifact_keeps_the_case_level_detail_the_counts_destroy(
    tmp_path, mixed, analysis
):
    """Part 1 is explicit that aggregates must not be the whole artifact.

    The previous pass proved two evaluators with identical counts can differ completely
    in what repetition buys.  An artifact storing only the counts would put that
    problem back at the file boundary.
    """
    path = write_artifact(analysis, tmp_path / "artifact.yaml")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert len(document["cases"]) == len(mixed.cases)
    sample = document["cases"][0]
    for field in (
        "case_id",
        "reference_label",
        "runs",
        "flags",
        "majority_verdict",
        "majority_agrees",
        "disagreement_rate",
        "repetition_verdict",
        "slice_id",
    ):
        assert field in sample, field
    assert {c["slice_id"] for c in document["cases"]} == set(mixed.slices)


def test_limitations_the_study_did_not_write_down_are_added_anyway(analysis):
    """A caveat that depends on the data must not depend on the author remembering it."""
    document = artifact_document(analysis)
    limitations = " ".join(document["known_limitations"])

    assert "synthetic" in limitations
    assert "observation" in limitations
    assert document["known_limitations"], "an artifact with no limitations is a claim"


def test_an_unknown_schema_is_refused_rather_than_guessed(tmp_path, analysis):
    path = write_artifact(analysis, tmp_path / "artifact.yaml")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["schema"] = "assurance-planner/qualification-artifact/v99"
    with pytest.raises(ValueError, match="unrecognised artifact schema"):
        qualification_from_document(document)
    assert ARTIFACT_SCHEMA.endswith("/v1")


# --------------------------------------------------------------------------------
# Test 3: an artifact cannot be read into a slot it was not measured for
# --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,replacement,expected",
    [
        ("evaluator", "correction_uptake_judge@v5", "source_version"),
        ("failure_mode", "VFD-SOMETHING-ELSE@v1", "failure_mode"),
        ("population", "some-other-suite", "population_id"),
        ("measured_against", "voice-agent-turntaking-r5", "distribution_id"),
    ],
)
def test_identity_mismatch_is_refused_on_every_component(
    analysis, field, replacement, expected
):
    """All four components of the qualification key, not just the evaluator.

    Each of these substitutions is a plausible real mistake -- a judge prompt revision,
    a renamed suite, a new behaviour release -- and each one silently invalidates the
    measurement.  A test per component, because a guard that only checks the evaluator
    version is the guard most likely to be written.
    """
    document = artifact_document(analysis)
    expected_key = QualificationKey(
        source_version=SourceVersionRef(
            *document["identity"]["evaluator"].split("@")
        ),
        failure_mode=FailureModeRef(*document["identity"]["failure_mode"].split("@")),
        population_id=document["identity"]["population"],
        distribution_id=document["identity"]["measured_against"],
    )
    document["identity"][field] = replacement

    with pytest.raises(ArtifactIdentityError) as raised:
        qualification_from_document(document, expected_key=expected_key)
    assert expected in str(raised.value)
    assert "not transferable" in str(raised.value)


def test_a_matching_identity_is_accepted(mixed, analysis):
    evidence = qualification_from_document(
        artifact_document(analysis), expected_key=_key(mixed)
    )
    assert evidence.key == _key(mixed)


def test_verification_evidence_is_not_manufactured_from_accuracy_evidence(analysis):
    """``prove_red_runs`` cannot be inferred from a characterization study.

    A characterization study measures how often the judge flags a labelled case.  It
    never observes the judge going red on a known-broken build and green on the fix.
    Deriving one from the other would invent verification evidence, so the artifact
    contributes zero and the scenario has to state it.
    """
    document = artifact_document(analysis)
    assert "prove_red_runs" not in document
    assert "prove_green_runs" not in document

    default = qualification_from_document(document)
    assert default.prove_red_runs == 0
    assert default.prove_green_runs == 0

    stated = qualification_from_document(
        document, prove_red_runs=4, prove_green_runs=4
    )
    assert stated.prove_red_runs == 4


# --------------------------------------------------------------------------------
# Scenario wiring
# --------------------------------------------------------------------------------


def _scenario_text(mixed, artifact_name: str, measured_against: str) -> str:
    """A minimal scenario whose only qualification row is an artifact reference.

    Deliberately minimal: the point under test is the qualification row, and a scenario
    with contexts in it would make a loader failure look like a planning failure.
    """
    return f"""
scenario: artifact-wiring

failure_mode:
  id: {mixed.failure_mode.failure_mode_id}
  version: {mixed.failure_mode.version}
  case_id: CASE-mix-000
  description: a behavioural failure needing semantic judgement

system_under_test:
  system_version: voice-agent-2026.09.24
  distribution_id: {mixed.distribution_id}

populations:
  - id: {mixed.population_id}
    denominator: curated correction-uptake cases
    kind: enumerable_corpus
    case_ids:
      - CASE-mix-000

sources:
  - id: {mixed.evaluator_version.source_id}
    version: {mixed.evaluator_version.version}
    kind: stochastic_judge
    open_ended: true

economics:
  - source: {mixed.evaluator_version}
    cost_per_invocation_usd: 0.0625
    latency_seconds_per_invocation: 120.0

qualification:
  - artifact: {artifact_name}
    source: {mixed.evaluator_version}
    failure_mode: {mixed.failure_mode}
    population: {mixed.population_id}
    measured_against: {measured_against}
    prove_red_runs: 3
    prove_green_runs: 3

assurance_profiles:
  gate:
    profile_ref: ARTIFACT-TEST
    maximum_error_requirement: 0.05

contexts: []
"""


def test_a_scenario_can_reference_an_artifact_instead_of_typing_counts(
    tmp_path, mixed, analysis
):
    """End to end: the numbers in the plan came out of the study, not a keyboard."""
    artifact = write_artifact(analysis, tmp_path / "judge.yaml")
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text(
        _scenario_text(mixed, artifact.name, mixed.distribution_id), encoding="utf-8"
    )

    scenario = load(scenario_path)
    evidence = scenario.world.qualification[_key(mixed)]
    positive_runs, true_positives, _, _ = analysis.qualification_counts()

    assert evidence is not None
    assert evidence.positive_cases == positive_runs
    assert evidence.true_positives == true_positives
    #: These two came from the scenario, because nothing else could have supplied them.
    assert evidence.prove_red_runs == 3
    assert evidence.provenance is not None
    assert evidence.provenance.characterization_run_id == mixed.run_id
    #: The caveats the study author never wrote down travelled with the counts.
    assert any("synthetic" in text for text in evidence.known_limitations)


def test_a_scenario_pointing_at_the_wrong_artifact_fails_to_load(
    tmp_path, mixed, analysis
):
    """The substitution that matters: right judge, right suite, different behaviour."""
    artifact = write_artifact(analysis, tmp_path / "judge.yaml")
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text(
        _scenario_text(mixed, artifact.name, "a-completely-different-release"),
        encoding="utf-8",
    )

    with pytest.raises(ArtifactIdentityError, match="distribution_id"):
        load(scenario_path)
