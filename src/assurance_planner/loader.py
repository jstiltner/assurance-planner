"""YAML scenario loading.

The loader can construct a world and the inputs to a planning call.  It has **no
parser for any planner-controlled field**: there is no way to write a replication
count, sample fraction, cadence, threshold or execution mode into a scenario file.
That is the structural guarantee that answers "have we hidden a dynamic parameter
inside static configuration".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .domain import (
    AssuranceProfile,
    DevelopmentContext,
    EvaluationPopulation,
    Estimator,
    EvidenceSourceVersion,
    ExecutionProfile,
    FailureMode,
    FailureModeRef,
    Intent,
    PopulationKind,
    QualificationEvidence,
    QualificationKey,
    SourceKind,
    SourceVersionRef,
    SystemUnderTest,
    UncertaintyDisposition,
)
from .artifacts import load_artifact
from .characterization import CaseRun, CharacterizationRun
from .registry import World

#: Fields a scenario file may never contain.  Enforced, not documented.
FORBIDDEN_KEYS = frozenset(
    {
        "replications",
        "sample_fraction",
        "run_percentage",
        "cadence",
        "execution_mode",
        "decision_threshold",
        "threshold_k",
        "escalation_band",
        "escalation_target",
    }
)


@dataclass(frozen=True, slots=True)
class PlanningRequest:
    name: str
    context: DevelopmentContext
    profile: AssuranceProfile


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    failure_mode: FailureMode
    world: World
    requests: tuple[PlanningRequest, ...]

    def request(self, name: str) -> PlanningRequest:
        for request in self.requests:
            if request.name == name:
                return request
        raise KeyError(f"no context named '{name}' in scenario '{self.name}'")


def _parse_source_ref(text: str) -> SourceVersionRef:
    source_id, _, version = text.partition("@")
    if not version:
        raise ValueError(f"source reference '{text}' must be 'id@version'")
    return SourceVersionRef(source_id, version)


def _parse_failure_mode_ref(text: str) -> FailureModeRef:
    mode_id, _, version = text.partition("@")
    if not version:
        raise ValueError(f"failure mode reference '{text}' must be 'id@version'")
    return FailureModeRef(mode_id, version)


def _reject_forbidden(node: Any, path: str = "") -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in FORBIDDEN_KEYS:
                raise ValueError(
                    f"scenario file sets planner-controlled field '{key}' at "
                    f"'{path or '<root>'}'; these are decided by the planner, not "
                    f"configured"
                )
            _reject_forbidden(value, f"{path}.{key}" if path else str(key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _reject_forbidden(value, f"{path}[{index}]")


def load(path: str | Path) -> Scenario:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    _reject_forbidden(raw)

    fm = raw["failure_mode"]
    failure_mode = FailureMode(
        failure_mode_id=fm["id"],
        version=fm["version"],
        case_id=fm["case_id"],
        description=fm["description"],
    )

    sut = raw["system_under_test"]
    world = World(
        system_under_test=SystemUnderTest(
            system_version=sut["system_version"],
            distribution_id=sut["distribution_id"],
        ),
        known_regression_cases=frozenset(raw.get("known_regression_cases", [])),
    )
    world.failure_modes[failure_mode.ref] = failure_mode

    for entry in raw.get("populations", []):
        world.add_population(
            EvaluationPopulation(
                population_id=entry["id"],
                denominator=entry["denominator"],
                kind=PopulationKind(entry["kind"]),
                case_ids=tuple(entry.get("case_ids", [])),
                units_per_window=int(entry.get("units_per_window", 0)),
            )
        )

    for entry in raw.get("sources", []):
        world.add_source(
            EvidenceSourceVersion(
                source_id=entry["id"],
                version=entry["version"],
                kind=SourceKind(entry["kind"]),
                open_ended=bool(entry["open_ended"]),
                consults_authoritative_source=bool(
                    entry.get("consults_authoritative_source", False)
                ),
            )
        )

    for entry in raw.get("economics", []):
        world.add_economics(
            ExecutionProfile(
                source_version=_parse_source_ref(entry["source"]),
                cost_per_invocation_usd=float(entry["cost_per_invocation_usd"]),
                latency_seconds_per_invocation=float(
                    entry["latency_seconds_per_invocation"]
                ),
                parallelism=int(entry.get("parallelism", 1)),
                human_minutes_per_invocation=float(
                    entry.get("human_minutes_per_invocation", 0.0)
                ),
                human_capacity_per_window=int(entry.get("human_capacity_per_window", 0)),
                available=bool(entry.get("available", True)),
            )
        )

    for entry in raw.get("qualification", []):
        #: A row may be typed out, or it may point at an artifact emitted by
        #: ``characterize-evaluator``.  The artifact form is the one that removes the
        #: transcription seam; the inline form is kept because a scenario describing a
        #: deterministic oracle has no characterization study to point at.
        if "artifact" in entry:
            artifact_path = (Path(path).parent / entry["artifact"]).resolve()
            world.add_qualification(
                load_artifact(
                    artifact_path,
                    expected_key=QualificationKey(
                        source_version=_parse_source_ref(entry["source"]),
                        failure_mode=_parse_failure_mode_ref(entry["failure_mode"]),
                        population_id=entry["population"],
                        distribution_id=entry["measured_against"],
                    ),
                    prove_red_runs=int(entry.get("prove_red_runs", 0)),
                    prove_green_runs=int(entry.get("prove_green_runs", 0)),
                )
            )
            continue

        evidence_date = entry["evidence_date"]
        world.add_qualification(
            QualificationEvidence(
                key=QualificationKey(
                    source_version=_parse_source_ref(entry["source"]),
                    failure_mode=_parse_failure_mode_ref(entry["failure_mode"]),
                    population_id=entry["population"],
                    #: Required.  A measurement that does not say which system it was
                    #: taken against is the defect this key exists to prevent, so
                    #: there is deliberately no default to the current one.
                    distribution_id=entry["measured_against"],
                ),
                #: Counts, not rates.  A scenario cannot assert a sensitivity that
                #: its stated sample size does not support, because there is nowhere
                #: to write one down.
                positive_cases=int(entry["positive_cases"]),
                true_positives=int(entry["true_positives"]),
                negative_cases=int(entry["negative_cases"]),
                false_positives=int(entry["false_positives"]),
                prove_red_runs=int(entry.get("prove_red_runs", 0)),
                prove_green_runs=int(entry.get("prove_green_runs", 0)),
                evidence_date=(
                    evidence_date
                    if isinstance(evidence_date, date)
                    else date.fromisoformat(str(evidence_date))
                ),
                known_limitations=tuple(entry.get("known_limitations", [])),
            )
        )

    profiles: dict[str, AssuranceProfile] = {}
    for key, entry in raw.get("assurance_profiles", {}).items():
        profiles[key] = AssuranceProfile(
            profile_ref=entry["profile_ref"],
            maximum_error_requirement=float(entry["maximum_error_requirement"]),
            sampling_allowed=bool(entry.get("sampling_allowed", True)),
            human_confirmation_required=bool(
                entry.get("human_confirmation_required", False)
            ),
            authoritative_source_required=bool(
                entry.get("authoritative_source_required", False)
            ),
            synchronous_requirement=bool(entry.get("synchronous_requirement", False)),
            uncertainty_disposition=UncertaintyDisposition(
                entry.get("uncertainty_disposition", "accept")
            ),
            minimum_observation_count=int(entry.get("minimum_observation_count", 1)),
            estimator=Estimator(entry.get("estimator", "point")),
        )

    requests = tuple(
        PlanningRequest(
            name=entry["name"],
            context=DevelopmentContext(
                intent=Intent(entry["intent"]),
                feedback_budget_seconds=float(entry["feedback_budget_seconds"]),
                changes_per_window=int(entry.get("changes_per_window", 1)),
                checkpoints_per_window=int(entry.get("checkpoints_per_window", 1)),
            ),
            profile=profiles[entry["assurance_profile"]],
        )
        for entry in raw.get("contexts", [])
    )

    return Scenario(
        name=raw["scenario"],
        failure_mode=failure_mode,
        world=world,
        requests=requests,
    )


#: Verdict spellings accepted in the long-form observation list.  ``pass`` means the
#: evaluator did *not* flag the failure; ``fail`` means it did.  Both spellings of each
#: are accepted because a harness author will reach for whichever their tool emits, and
#: rejecting real data over vocabulary is a bad trade.
_FLAGGED = {"fail": True, "flag": True, "flagged": True, "true": True, "1": True}
_NOT_FLAGGED = {"pass": False, "ok": False, "clean": False, "false": False, "0": False}


def _parse_verdict(value: object, case_id: str) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in _FLAGGED:
        return True
    if text in _NOT_FLAGGED:
        return False
    raise ValueError(
        f"case '{case_id}': verdict {value!r} is not one of "
        f"{sorted(_FLAGGED) + sorted(_NOT_FLAGGED)}"
    )


def _parse_bitstring_case(entry: dict) -> CaseRun:
    outcomes = str(entry["outcomes"])
    if set(outcomes) - {"0", "1"} or not outcomes:
        raise ValueError(
            f"case '{entry['case_id']}': outcomes must be a non-empty string of "
            f"0 and 1, got {outcomes!r}"
        )
    return CaseRun(
        case_id=entry["case_id"],
        reference_label=bool(entry["failure_present"]),
        outcomes=tuple(c == "1" for c in outcomes),
        scores=tuple(float(s) for s in entry.get("scores", [])),
        slice_id=str(entry.get("slice_id", "")),
        note=entry.get("note", ""),
    )


def _parse_observation_case(entry: dict) -> CaseRun:
    """The long form: one mapping per observation, with optional cost and latency.

    This is the shape a real harness emits.  ``reference_label`` is spelled
    ``pass``/``fail`` rather than a boolean because "failure_present: false" reads as a
    double negative on a labelling sheet and gets miskeyed.
    """
    case_id = entry["case_id"]
    if "reference_label" in entry:
        reference = _parse_verdict(entry["reference_label"], case_id)
    else:
        reference = bool(entry["failure_present"])

    observations = entry["observations"]
    if not observations:
        raise ValueError(f"case '{case_id}': observations must be non-empty")

    scores = [o["score"] for o in observations if o.get("score") is not None]
    latencies = [o["latency_ms"] for o in observations if o.get("latency_ms") is not None]
    costs = [o["cost"] for o in observations if o.get("cost") is not None]
    for name, values in (("score", scores), ("latency_ms", latencies), ("cost", costs)):
        if values and len(values) != len(observations):
            raise ValueError(
                f"case '{case_id}': {name} is present on {len(values)} of "
                f"{len(observations)} observations; supply it on all or none"
            )

    return CaseRun(
        case_id=case_id,
        reference_label=reference,
        outcomes=tuple(_parse_verdict(o["verdict"], case_id) for o in observations),
        scores=tuple(float(s) for s in scores),
        slice_id=str(entry.get("slice_id", "")),
        latencies_ms=tuple(float(v) for v in latencies),
        costs_usd=tuple(float(v) for v in costs),
        note=entry.get("note", ""),
    )


def load_characterization(path: str | Path) -> CharacterizationRun:
    """Load per-case evaluator outcomes in either supported shape.

    **Long form** -- what a real harness should emit, and what
    ``docs/real_experiment_protocol.md`` specifies:

    ```yaml
    experiment:
      evaluator_version: judge@v4
      failure_mode_version: MODE@v1
      population_id: suite
      sut_distribution_id: dist-r4
    cases:
      - case_id: C-001
        slice_id: borderline-semantic
        reference_label: fail
        observations:
          - {verdict: fail, score: 0.81, latency_ms: 1900, cost: 0.0625}
    ```

    **Short form** -- ``outcomes: "10110100"`` with a top-level ``evaluator``.  Retained
    because a fifty-case synthetic fixture written the long way is unreadable, and
    because the committed fixtures are meant to be edited by hand.  The two forms
    produce identical objects; no statistic can tell them apart.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    header = raw.get("experiment", raw)

    evaluator = header.get("evaluator_version", header.get("evaluator"))
    failure_mode = header.get("failure_mode_version", header.get("failure_mode"))
    population = header.get("population_id", header.get("population"))
    distribution = header.get("sut_distribution_id", header.get("measured_against"))
    if not all((evaluator, failure_mode, population, distribution)):
        raise ValueError(
            f"{path}: every run must name an evaluator, a failure mode, a population "
            f"and the behaviour distribution it was measured against; a measurement "
            f"missing any of the four cannot be keyed to a qualification slot"
        )

    cases = tuple(
        _parse_observation_case(entry) if "observations" in entry
        else _parse_bitstring_case(entry)
        for entry in raw["cases"]
    )

    measured_on = header.get("measured_on", raw.get("measured_on"))
    return CharacterizationRun(
        evaluator_version=_parse_source_ref(evaluator),
        failure_mode=_parse_failure_mode_ref(failure_mode),
        population_id=population,
        distribution_id=distribution,
        cases=cases,
        note=raw.get("note", header.get("note", "")),
        measured_on=(
            None
            if measured_on is None
            else measured_on
            if isinstance(measured_on, date)
            else date.fromisoformat(str(measured_on))
        ),
        limitations=tuple(raw.get("limitations", header.get("limitations", []))),
        run_id=str(header.get("run_id", "")),
    )
