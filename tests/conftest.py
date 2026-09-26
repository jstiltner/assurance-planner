from __future__ import annotations

from pathlib import Path

import pytest

from assurance_planner import load
from assurance_planner.loader import Scenario

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def _load(name: str) -> Scenario:
    return load(SCENARIO_DIR / name)


@pytest.fixture
def voice_early() -> Scenario:
    return _load("voice_early.yaml")


@pytest.fixture
def duplex_silence() -> Scenario:
    return _load("duplex_silence.yaml")


@pytest.fixture
def clinical_factual() -> Scenario:
    return _load("clinical_factual.yaml")


def run(scenario: Scenario, context_name: str):
    from assurance_planner import plan

    request = scenario.request(context_name)
    return plan(request.context, scenario.failure_mode, request.profile, scenario.world)


def rejection_constraints(result, source: str, population: str) -> set[str]:
    """Constraints that rejected a given (source, population) family."""
    return {
        r.constraint
        for r in result.rejections
        if r.plan_id.split("|")[0] == source and r.plan_id.split("|")[1] == population
    }
