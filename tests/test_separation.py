"""Tests for the separations the architecture claims to maintain.

These exist because a design note asserting "qualification and economics are
separate" is worth nothing.  Each test corresponds to a numbered question in
docs/red_team_review.md.
"""

from __future__ import annotations

from dataclasses import fields, replace
from datetime import date
from pathlib import Path

import pytest
import yaml

from assurance_planner import load, plan
from assurance_planner.domain import (
    AssuranceProfile,
    Estimator,
    EvidenceSourceVersion,
    ExecutionProfile,
    PlanStep,
    QualificationEvidence,
    QualificationKey,
    SourceKind,
    SourceVersionRef,
    UncertaintyDisposition,
)
from assurance_planner.loader import FORBIDDEN_KEYS
from conftest import SCENARIO_DIR, run

SRC = Path(__file__).resolve().parents[1] / "src" / "assurance_planner"


# --- Q2: are the three concepts genuinely separable? -----------------------------


def test_q2_no_field_appears_in_both_qualification_and_economics():
    qualification_fields = {f.name for f in fields(QualificationEvidence)} - {"key"}
    economics_fields = {f.name for f in fields(ExecutionProfile)} - {"source_version"}
    assert qualification_fields.isdisjoint(economics_fields)


def test_q2_assurance_profile_contains_no_mechanism_or_price_fields():
    policy_fields = {f.name for f in fields(AssuranceProfile)}
    mechanism_fields = {f.name for f in fields(EvidenceSourceVersion)}
    economics_fields = {f.name for f in fields(ExecutionProfile)}
    assert policy_fields.isdisjoint(mechanism_fields)
    assert policy_fields.isdisjoint(economics_fields)


def test_q2_the_two_registries_are_independent_dicts(clinical_factual):
    world = clinical_factual.world
    repriced = world.reprice(
        SourceVersionRef("frontier_judge", "v2"), cost_per_invocation_usd=1234.0
    )
    requalified = world.requalify(
        QualificationKey(
            SourceVersionRef("frontier_judge", "v2"),
            clinical_factual.failure_mode.ref,
            "flagged_interactions",
            world.system_under_test.distribution_id,
        ),
        true_positives=200,
    )
    assert repriced.qualification == world.qualification
    assert requalified.economics == world.economics


# --- Q3: is evaluator quality treated as global? ---------------------------------


def test_q3_qualification_is_keyed_by_failure_mode_and_population(voice_early):
    """The same judge version is qualified on one population and not another."""
    world = voice_early.world
    judge = world.sources[SourceVersionRef("transcript_judge", "v7")]
    simulation = world.sources[SourceVersionRef("behavioral_simulation", "v3")]
    focused = world.populations["affected_scenario"]
    corpus = world.populations["scenario_corpus"]
    mode = voice_early.failure_mode

    assert world.qualification_for(judge, mode, focused) is not None
    assert world.qualification_for(judge, mode, corpus) is not None
    assert world.qualification_for(simulation, mode, focused) is not None
    # The crux: a deterministic assertion qualified on one case is NOT thereby
    # qualified on the whole corpus.
    assert world.qualification_for(simulation, mode, corpus) is None


def test_q3_a_different_failure_mode_does_not_inherit_qualification(voice_early):
    world = voice_early.world
    judge = world.sources[SourceVersionRef("transcript_judge", "v7")]
    other_mode = replace(voice_early.failure_mode, failure_mode_id="VFD-SOMETHING-ELSE")
    assert (
        world.qualification_for(
            judge, other_mode, world.populations["scenario_corpus"]
        )
        is None
    )


def test_q3_planner_refuses_a_source_with_no_evidence_for_this_population(voice_early):
    from conftest import rejection_constraints

    result = run(voice_early, "checkpoint")
    constraints = rejection_constraints(
        result, "behavioral_simulation@v3", "scenario_corpus"
    )
    assert "qualification_exists" in constraints


# --- Q4: is any dynamic parameter hidden in static config? -----------------------


def test_q4_scenario_files_cannot_set_planner_controlled_fields():
    planner_controlled = {
        "sample_fraction",
        "replications",
        "threshold_k",
        "escalation_band",
        "escalation_target",
        "cadence",
        "execution_mode",
    }
    step_fields = {f.name for f in fields(PlanStep)}
    assert planner_controlled <= step_fields
    assert planner_controlled <= FORBIDDEN_KEYS


@pytest.mark.parametrize("key", sorted(FORBIDDEN_KEYS))
def test_q4_the_loader_rejects_forbidden_keys(tmp_path, key):
    raw = yaml.safe_load((SCENARIO_DIR / "voice_early.yaml").read_text())
    raw["contexts"][0][key] = 3
    path = tmp_path / "tampered.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="planner-controlled"):
        load(path)


@pytest.mark.parametrize(
    "scenario_file",
    ["voice_early.yaml", "duplex_silence.yaml", "clinical_factual.yaml"],
)
def test_q4_no_shipped_scenario_names_a_planner_field(scenario_file):
    text = (SCENARIO_DIR / scenario_file).read_text(encoding="utf-8")
    body = "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("#")
    )
    for key in FORBIDDEN_KEYS:
        assert f"{key}:" not in body


# --- Q5: does run percentage always carry a denominator? -------------------------


@pytest.mark.parametrize(
    "scenario_file",
    ["voice_early.yaml", "duplex_silence.yaml", "clinical_factual.yaml"],
)
def test_q5_every_step_of_every_admissible_plan_has_a_denominator(scenario_file):
    scenario = load(SCENARIO_DIR / scenario_file)
    for request in scenario.requests:
        result = plan(
            request.context, scenario.failure_mode, request.profile, scenario.world
        )
        candidates = (
            [result.selected, *result.runners_up] if result.selected else []
        )
        for candidate in candidates:
            for step in candidate.steps:
                assert step.denominator
                assert step.denominator in step.scope_phrase()


def test_q5_a_population_cannot_exist_without_a_denominator():
    from assurance_planner.domain import EvaluationPopulation

    required = [f for f in fields(EvaluationPopulation) if f.default is not None]
    assert "denominator" in {f.name for f in required}
    with pytest.raises(TypeError):
        EvaluationPopulation(population_id="x")  # type: ignore[call-arg]


# --- Q6: are scope, replications, cadence and mechanism independent? -------------


def test_q6_each_dimension_varies_alone_across_the_scenarios(voice_early, duplex_silence):
    inner = run(voice_early, "inner_loop").selected.primary
    checkpoint = run(voice_early, "checkpoint").selected.primary
    nightly = run(voice_early, "nightly").selected.primary
    verify = run(duplex_silence, "verify").selected.primary
    broad = run(duplex_silence, "blast_radius").selected.primary

    # scope alone (B): same mechanism, same replications, different scope
    assert verify.source.ref == broad.source.ref
    assert verify.replications == broad.replications
    assert verify.units_selected != broad.units_selected

    # replications alone (A): same mechanism, same scope, different replications
    assert checkpoint.source.ref == nightly.source.ref
    assert checkpoint.units_selected == nightly.units_selected
    assert checkpoint.replications != nightly.replications

    # mechanism alone (A): different mechanism at the same replication count
    assert inner.source.ref != checkpoint.source.ref
    assert inner.replications == checkpoint.replications

    # cadence alone (B): same mechanism, same scope, same replications
    assert broad.cadence != verify.cadence


# --- Q8: does a version bump correctly invalidate prior qualification? -----------


def test_q8_bumping_the_evaluator_version_orphans_its_evidence(duplex_silence):
    world = duplex_silence.world
    old = SourceVersionRef("state_machine_assertion", "v2")
    bumped = EvidenceSourceVersion(
        source_id="state_machine_assertion",
        version="v3",
        kind=SourceKind.DETERMINISTIC,
        open_ended=False,
        consults_authoritative_source=False,
    )
    sources = {ref: s for ref, s in world.sources.items() if ref != old}
    sources[bumped.ref] = bumped
    economics = dict(world.economics)
    economics[bumped.ref] = replace(world.economics[old], source_version=bumped.ref)
    bumped_world = replace(world, sources=sources, economics=economics)

    # The evidence rows still exist, but they are keyed to v2 and no longer match.
    assert (
        bumped_world.qualification_for(
            bumped, duplex_silence.failure_mode, world.populations["focused_repro"]
        )
        is None
    )

    request = duplex_silence.request("verify")
    result = plan(
        request.context, duplex_silence.failure_mode, request.profile, bumped_world
    )
    assert result.selected is None or (
        result.selected.primary.source.source_id != "state_machine_assertion"
    )


def test_q8_bumping_the_failure_mode_version_orphans_its_evidence(duplex_silence):
    request = duplex_silence.request("verify")
    redefined = replace(duplex_silence.failure_mode, version="v018")
    result = plan(request.context, redefined, request.profile, duplex_silence.world)
    assert result.selected is None
    assert any(r.constraint == "qualification_exists" for r in result.rejections)


def test_q8_a_red_under_one_version_cannot_license_a_green_under_another(
    duplex_silence,
):
    """The claim freeze, stated as behaviour rather than as a separate claim object.

    The prove-red evidence is filed against an exact ``QualificationKey``.  Bumping
    the evaluator version does not carry it forward, so the RED observed under v2
    cannot be used to support a verification claim made under v3.
    """
    world = duplex_silence.world
    key = QualificationKey(
        SourceVersionRef("state_machine_assertion", "v2"),
        duplex_silence.failure_mode.ref,
        "focused_repro",
        world.system_under_test.distribution_id,
    )
    assert world.qualification[key].prove_red_runs >= 1
    rekeyed = replace(key, source_version=SourceVersionRef("state_machine_assertion", "v3"))
    assert rekeyed not in world.qualification


# --- Q10: are there abstractions no scenario exercises? --------------------------


def test_q10_every_assurance_profile_field_changes_the_outcome_somewhere(
    clinical_factual,
):
    """If flipping a field never changes anything, the field should not exist.

    The signature covers both which plans survive and what those plans contain --
    `uncertainty_disposition` leaves the admissible set alone here while adding an
    escalation hop, and it gates admissibility in test_scenario_c.
    """
    request = clinical_factual.request("production_guard_routine_policy")
    base = request.profile

    def plan_ids(profile) -> set[tuple]:
        result = plan(
            request.context, clinical_factual.failure_mode, profile, clinical_factual.world
        )
        candidates = ([result.selected] if result.selected else []) + result.runners_up
        return {
            (
                p.plan_id,
                tuple(
                    (s.role, str(s.source.ref), s.replications, s.threshold_k)
                    for s in p.steps
                ),
            )
            for p in candidates
        }

    baseline = plan_ids(base)
    for field, value in [
        ("sampling_allowed", False),
        ("human_confirmation_required", True),
        ("authoritative_source_required", True),
        ("synchronous_requirement", True),
        # The enum member, not the string: `replace` bypasses the loader's coercion
        # and the planner compares enum identity.
        ("uncertainty_disposition", UncertaintyDisposition.ESCALATE),
        ("maximum_error_requirement", 0.001),
        ("minimum_observation_count", 1000),
        ("estimator", Estimator.CONSERVATIVE),
    ]:
        changed = plan_ids(replace(base, **{field: value}))
        assert changed != baseline, f"AssuranceProfile.{field} changes nothing"


def test_q10_profile_ref_is_deliberately_inert(clinical_factual):
    """The one field that must NOT change anything: the policy identifier itself."""
    request = clinical_factual.request("production_guard")
    renamed = replace(request.profile, profile_ref="SOME-OTHER-NAME")
    original = plan(
        request.context,
        clinical_factual.failure_mode,
        request.profile,
        clinical_factual.world,
    )
    after = plan(
        request.context, clinical_factual.failure_mode, renamed, clinical_factual.world
    )
    assert original.selected.plan_id == after.selected.plan_id
    assert original.selected.economics == after.selected.economics


def test_q10_parallelism_is_load_bearing_not_decorative(voice_early):
    """`ExecutionProfile.parallelism` sits in the wall-clock formula.

    No shipped scenario varies it, which is exactly how a field becomes decorative
    without anyone noticing.  It has to be able to flip admissibility.
    """
    request = voice_early.request("checkpoint")
    #: A budget the serial 20x120s suite misses and the 8-way parallel one makes.
    tight = replace(request.context, feedback_budget_seconds=600.0)
    judge = SourceVersionRef("transcript_judge", "v7")

    serial = plan(tight, voice_early.failure_mode, request.profile, voice_early.world)
    assert serial.selected is None
    assert any(r.constraint == "budget_feedback" for r in serial.rejections)

    world = voice_early.world.reprice(judge, parallelism=8)
    parallel = plan(tight, voice_early.failure_mode, request.profile, world)
    assert parallel.selected is not None
    assert parallel.selected.economics.blocking_feedback_seconds == 300.0
    #: And it moved nothing in the other registry.
    assert world.qualification == voice_early.world.qualification


def test_q10_availability_is_load_bearing(voice_early):
    request = voice_early.request("inner_loop")
    world = voice_early.world.reprice(
        SourceVersionRef("behavioral_simulation", "v3"), available=False
    )
    result = plan(request.context, voice_early.failure_mode, request.profile, world)
    assert result.selected is None
    assert any(r.constraint == "source_available" for r in result.rejections)


def test_q10_every_source_kind_is_used_by_some_scenario():
    used = set()
    for scenario_file in (
        "voice_early.yaml",
        "duplex_silence.yaml",
        "clinical_factual.yaml",
    ):
        scenario = load(SCENARIO_DIR / scenario_file)
        used |= {s.kind for s in scenario.world.sources.values()}
    assert used == set(SourceKind)


# --- planner purity ---------------------------------------------------------------


def test_planner_makes_no_network_or_model_calls():
    banned = ("import requests", "import httpx", "openai", "anthropic", "urllib")
    for path in SRC.glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for token in banned:
            assert token not in text, f"{path.name} references '{token}'"


def test_planner_uses_no_randomness_or_wall_clock():
    for path in SRC.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "import random" not in text
        assert "datetime.now" not in text
        assert "time.time" not in text
