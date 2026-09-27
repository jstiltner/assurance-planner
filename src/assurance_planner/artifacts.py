"""The seam between measuring an evaluator and planning with it.

Before this module a characterization run produced a report, a human read the report,
and a human typed four integers into a scenario file.  Every step of that is a place
to transcribe the wrong number, attach it to the wrong evaluator, or lose the caveat
that made it conditional.

A *qualification artifact* is the document that removes the typing.  It is emitted by
``characterize-evaluator --emit`` and consumed by the scenario loader, and it carries
three things at once:

1. the four counts the planner actually reads;
2. the provenance needed to trace those counts back to the study;
3. the case-level detail that the counts destroy.

(3) is not decoration.  The previous pass established that two evaluators with the
same counts can differ completely in what repetition buys, so an artifact that stored
only (1) would reintroduce the problem at the file boundary.

Identity is checked on load, not trusted.  An artifact measured against one evaluator,
failure mode, population or behaviour distribution cannot be read into a slot
expecting another, because that substitution is precisely the silent failure the
qualification key exists to prevent.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .characterization import Characterization, characterize
from .domain import (
    FailureModeRef,
    MeasurementProvenance,
    QualificationEvidence,
    QualificationKey,
    SourceVersionRef,
)

#: Bumped when the document shape changes incompatibly.  A reader that does not
#: recognise the version refuses rather than guessing.
ARTIFACT_SCHEMA = "assurance-planner/qualification-artifact/v1"


class ArtifactIdentityError(ValueError):
    """An artifact was read into a slot it was not measured for."""


class SyntheticArtifactError(ValueError):
    """An artifact built from generated observations was read as planner evidence.

    Separate from ``ArtifactIdentityError`` because the fix is different: an identity
    mismatch means the wrong file was referenced, and this means the right file was
    referenced and the study behind it never happened.
    """


def _ref(text: str) -> tuple[str, str]:
    left, _, right = text.partition("@")
    if not right:
        raise ValueError(f"reference '{text}' must be 'id@version'")
    return left, right


def _case_summary(analysis: Characterization) -> list[dict[str, Any]]:
    """Per-case records, kept because the aggregate provably cannot replace them."""
    verdicts = {v.case.case_id: v for v in analysis.verdicts}
    summary = []
    for case in analysis.run.cases:
        verdict = verdicts[case.case_id]
        entry: dict[str, Any] = {
            "case_id": case.case_id,
            "reference_label": case.reference_label,
            "runs": case.runs,
            "flags": case.flags,
            "majority_verdict": case.majority_verdict,
            "majority_agrees": case.majority_agrees_with_reference,
            "disagreement_rate": round(case.disagreement_rate, 4),
            "correct_rate": round(case.correct_rate, 4),
            "repetition_verdict": verdict.verdict,
        }
        if case.slice_id:
            entry["slice_id"] = case.slice_id
        if case.note:
            entry["note"] = case.note
        summary.append(entry)
    return summary


def artifact_document(
    analysis: Characterization, artifact_ref: str = ""
) -> dict[str, Any]:
    """The full artifact, as a plain dict ready for ``yaml.safe_dump``."""
    run = analysis.run
    if run.measured_on is None:
        raise ValueError(
            f"characterization run '{run.run_id}' has no measured_on date; a "
            f"qualification row cannot be dated from a clock this package does not read"
        )
    positive_runs, true_positives, negative_runs, false_positives = (
        analysis.qualification_counts()
    )
    provenance = analysis.provenance(artifact_ref)
    sensitivity, fpr = analysis.sensitivity, analysis.false_positive_rate

    document: dict[str, Any] = {
        "schema": ARTIFACT_SCHEMA,
        "identity": {
            "evaluator": str(run.evaluator_version),
            "failure_mode": str(run.failure_mode),
            "population": run.population_id,
            "measured_against": run.distribution_id,
        },
        "provenance": {
            "characterization_run_id": provenance.characterization_run_id,
            "measured_on": run.measured_on,
            "reference_positive_cases": provenance.reference_positive_cases,
            "reference_negative_cases": provenance.reference_negative_cases,
            "repetitions_per_case": round(provenance.repetitions_per_case, 3),
            "effective_positive_runs": round(provenance.effective_positive_runs, 2),
            "effective_negative_runs": round(provenance.effective_negative_runs, 2),
            "dispersion_phi": (
                None
                if provenance.dispersion_phi is None
                else round(provenance.dispersion_phi, 4)
            ),
            "mean_same_case_agreement": round(provenance.mean_same_case_agreement, 4),
            "cases_repetition_cannot_fix": provenance.cases_repetition_cannot_fix,
        },
        #: The four numbers the planner reads.  Everything above and below exists so
        #: that a reader can decide whether to believe them.
        "counts": {
            "positive_cases": positive_runs,
            "true_positives": true_positives,
            "negative_cases": negative_runs,
            "false_positives": false_positives,
        },
        "estimates": {
            "sensitivity": {
                "point": round(sensitivity.point, 6),
                "interval_iid": [round(v, 6) for v in sensitivity.naive_interval],
                "interval_clustered": [
                    round(v, 6) for v in sensitivity.corrected_interval
                ],
            },
            "false_positive_rate": {
                "point": round(fpr.point, 6),
                "interval_iid": [round(v, 6) for v in fpr.naive_interval],
                "interval_clustered": [round(v, 6) for v in fpr.corrected_interval],
            },
        },
        "known_limitations": list(analysis.derived_limitations()),
        "cases": _case_summary(analysis),
    }
    if run.synthetic:
        #: Second key in the document, right under the schema, because a reader
        #: skimming the head of the file must not have to reach ``known_limitations``
        #: to find out that none of this was collected.  ``qualification_from_document``
        #: refuses to load it, so the marker is enforced and not only displayed.
        document = {"schema": document.pop("schema"), "synthetic": True, **document}
    if run.note:
        document["note"] = run.note
    return document


def write_artifact(analysis: Characterization, path: str | Path) -> Path:
    destination = Path(path)
    document = artifact_document(analysis, artifact_ref=destination.name)
    destination.write_text(
        yaml.safe_dump(document, sort_keys=False, width=92), encoding="utf-8"
    )
    return destination


def qualification_from_document(
    document: dict[str, Any],
    *,
    expected_key: QualificationKey | None = None,
    prove_red_runs: int = 0,
    prove_green_runs: int = 0,
    artifact_ref: str = "",
) -> QualificationEvidence:
    """Build a planner input from an artifact, refusing an identity mismatch.

    ``prove_red_runs`` / ``prove_green_runs`` are *not* derived from the artifact.  A
    characterization study measures how often the evaluator flags a labelled case; it
    does not observe the evaluator going red on a known-broken build and green on the
    fix.  Inferring one from the other would manufacture verification evidence out of
    accuracy evidence, so the scenario has to state them.
    """
    schema = document.get("schema")
    if schema != ARTIFACT_SCHEMA:
        raise ValueError(
            f"unrecognised artifact schema {schema!r}; expected {ARTIFACT_SCHEMA!r}"
        )

    if document.get("synthetic"):
        raise SyntheticArtifactError(
            "this qualification artifact is marked synthetic: its counts were "
            "generated, not collected. It can be written and inspected, to exercise "
            "the analysis machinery on input whose structure is known, but it cannot "
            "become a planner input. Nothing that plans against it would be measuring "
            "anything."
        )

    identity = document["identity"]
    source_id, source_version = _ref(identity["evaluator"])
    mode_id, mode_version = _ref(identity["failure_mode"])
    key = QualificationKey(
        source_version=SourceVersionRef(source_id, source_version),
        failure_mode=FailureModeRef(mode_id, mode_version),
        population_id=identity["population"],
        distribution_id=identity["measured_against"],
    )

    if expected_key is not None and key != expected_key:
        differing = [
            name
            for name in (
                "source_version",
                "failure_mode",
                "population_id",
                "distribution_id",
            )
            if getattr(key, name) != getattr(expected_key, name)
        ]
        raise ArtifactIdentityError(
            f"artifact was measured for {key.source_version} x {key.failure_mode} x "
            f"'{key.population_id}' against '{key.distribution_id}', which differs "
            f"from the slot it is being read into on: {', '.join(differing)}. "
            f"Qualification is not transferable across any of these."
        )

    counts = document["counts"]
    raw_provenance = document.get("provenance", {})
    measured_on = raw_provenance.get("measured_on")
    provenance = MeasurementProvenance(
        characterization_run_id=raw_provenance.get("characterization_run_id", ""),
        reference_positive_cases=int(raw_provenance.get("reference_positive_cases", 0)),
        reference_negative_cases=int(raw_provenance.get("reference_negative_cases", 0)),
        repetitions_per_case=float(raw_provenance.get("repetitions_per_case", 0.0)),
        effective_positive_runs=float(
            raw_provenance.get("effective_positive_runs", 0.0)
        ),
        effective_negative_runs=float(
            raw_provenance.get("effective_negative_runs", 0.0)
        ),
        dispersion_phi=(
            None
            if raw_provenance.get("dispersion_phi") is None
            else float(raw_provenance["dispersion_phi"])
        ),
        mean_same_case_agreement=float(
            raw_provenance.get("mean_same_case_agreement", 0.0)
        ),
        cases_repetition_cannot_fix=int(
            raw_provenance.get("cases_repetition_cannot_fix", 0)
        ),
        artifact_ref=artifact_ref,
    )

    return QualificationEvidence(
        key=key,
        positive_cases=int(counts["positive_cases"]),
        true_positives=int(counts["true_positives"]),
        negative_cases=int(counts["negative_cases"]),
        false_positives=int(counts["false_positives"]),
        prove_red_runs=prove_red_runs,
        prove_green_runs=prove_green_runs,
        evidence_date=(
            measured_on
            if isinstance(measured_on, date)
            else date.fromisoformat(str(measured_on))
        ),
        known_limitations=tuple(document.get("known_limitations", [])),
        provenance=provenance,
    )


def load_artifact(
    path: str | Path,
    *,
    expected_key: QualificationKey | None = None,
    prove_red_runs: int = 0,
    prove_green_runs: int = 0,
) -> QualificationEvidence:
    location = Path(path)
    document = yaml.safe_load(location.read_text(encoding="utf-8"))
    return qualification_from_document(
        document,
        expected_key=expected_key,
        prove_red_runs=prove_red_runs,
        prove_green_runs=prove_green_runs,
        artifact_ref=location.name,
    )


def qualify(
    run, max_error: float, max_replications: int = 12, **kwargs
) -> QualificationEvidence:
    """Characterization run in, planner input out, with nothing retyped."""
    analysis = characterize(run, max_error, max_replications)
    return qualification_from_document(artifact_document(analysis), **kwargs)
