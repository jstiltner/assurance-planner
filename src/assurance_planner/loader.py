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


def load_characterization(path: str | Path) -> CharacterizationRun:
    """Load per-case evaluator outcomes.

    ``outcomes`` is a string of ``1``/``0`` rather than a YAML list because a case with
    eight repetitions is the common shape and a list of eight booleans per case makes
    a fifty-case file unreadable.  The encoding is the only concession to brevity: the
    per-case records themselves are never collapsed.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    cases: list[CaseRun] = []
    for entry in raw["cases"]:
        outcomes = str(entry["outcomes"])
        if set(outcomes) - {"0", "1"} or not outcomes:
            raise ValueError(
                f"case '{entry['case_id']}': outcomes must be a non-empty string of "
                f"0 and 1, got {outcomes!r}"
            )
        cases.append(
            CaseRun(
                case_id=entry["case_id"],
                reference_label=bool(entry["failure_present"]),
                outcomes=tuple(c == "1" for c in outcomes),
                scores=tuple(float(s) for s in entry.get("scores", [])),
                note=entry.get("note", ""),
            )
        )

    return CharacterizationRun(
        evaluator_version=_parse_source_ref(raw["evaluator"]),
        failure_mode=_parse_failure_mode_ref(raw["failure_mode"]),
        population_id=raw["population"],
        distribution_id=raw["measured_against"],
        cases=tuple(cases),
        note=raw.get("note", ""),
    )
