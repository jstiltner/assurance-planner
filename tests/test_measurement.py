"""Acceptance tests for the measurement pass.

These exist to falsify claims about the planner's *inputs*, not its decision logic.
Section 1 covers stale-evidence identity; later sections cover estimate uncertainty.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from assurance_planner import plan
from assurance_planner.domain import SystemUnderTest

from conftest import run


def _with_distribution(scenario, distribution_id: str, system_version: str = "next"):
    """The same world, planning against a differently-declared system."""
    world = replace(
        scenario.world,
        system_under_test=SystemUnderTest(system_version, distribution_id),
    )
    return replace(scenario, world=world)


# --------------------------------------------------------------------------------
# 1. Stale evidence identity
# --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_name,context",
    [
        ("voice_early", "nightly"),
        ("duplex_silence", "verify"),
        ("clinical_factual", "production_guard"),
    ],
)
def test_evidence_from_another_distribution_is_never_reused(
    request, fixture_name, context
):
    """Acceptance 1.  Every scenario loses every plan when the distribution moves."""
    scenario = request.getfixturevalue(fixture_name)
    assert run(scenario, context).selected is not None

    moved = _with_distribution(scenario, "rebuilt-on-a-different-stack")
    result = run(moved, context)

    assert result.selected is None
    constraints = {r.constraint for r in result.rejections}
    assert "qualification_stale" in constraints
    #: Nothing survives far enough to be rejected for any other reason.  The pairs
    #: that were never qualified at all still report absence; there is no row for
    #: them to have gone stale.
    assert constraints <= {"qualification_stale", "qualification_exists"}


def test_staleness_is_diagnosed_distinctly_from_absence(voice_early):
    """"Measured against a system that is no longer running" is the actionable message.

    A bare ``qualification_exists`` miss would tell a reader to go and qualify the
    judge, when what actually happened is that someone moved the system underneath a
    qualification that already exists.
    """
    moved = _with_distribution(voice_early, "voice-agent-turntaking-r5")
    reasons = [
        r.reason
        for r in run(moved, "nightly").rejections
        if r.plan_id.startswith("transcript_judge")
    ]

    assert reasons, "expected the judge's rows to be reported stale"
    for reason in reasons:
        assert "voice-agent-turntaking-r4" in reason
        assert "voice-agent-turntaking-r5" in reason

    # The population the simulation was never qualified on still reports absence, not
    # staleness: there is no row to be stale.
    absent = [
        r
        for r in run(voice_early, "checkpoint").rejections
        if r.plan_id.startswith("behavioral_simulation")
    ]
    assert absent
    assert "qualification_exists" in {r.constraint for r in absent}
    assert "qualification_stale" not in {r.constraint for r in absent}


def test_a_non_material_rebuild_reuses_every_qualification_row(voice_early):
    """Continuity.  A new build in the same declared distribution changes nothing.

    This is the reason the key holds a distribution and not a build number: without
    it, every deploy would orphan every measurement and the registry would have to be
    rewritten wholesale on each one.
    """
    before = run(voice_early, "nightly").selected
    rebuilt = _with_distribution(
        voice_early,
        voice_early.world.system_under_test.distribution_id,
        system_version="voice-agent-2026.09.19",
    )
    after = run(rebuilt, "nightly").selected

    assert after is not None
    assert after.plan_id == before.plan_id
    assert after.economics == before.economics
    assert rebuilt.world.qualification == voice_early.world.qualification


def test_declaring_the_move_is_the_only_way_to_invalidate(voice_early):
    """The planner cannot infer materiality and does not pretend to.

    Changing the build string alone is inert; the ``distribution_id`` is the assertion.
    Stating that plainly in a test is the point -- this is a human judgement the
    planner obeys, with the same epistemic status as ``maximum_error_requirement``.
    """
    relabelled = _with_distribution(
        voice_early,
        voice_early.world.system_under_test.distribution_id,
        system_version="a-completely-different-build-string",
    )
    assert run(relabelled, "nightly").selected is not None


def test_a_moved_distribution_cannot_be_escaped_by_escalation(clinical_factual):
    """Staleness binds the escalation target too, not just the primary.

    Scenario C's strict profile derives an escalation hop and a human confirmer.  If
    staleness only gated the primary source, an ambiguous case would be routed to a
    source whose qualification is equally stale, which is worse than no plan at all.
    """
    moved = _with_distribution(clinical_factual, "assistant-retrained-r10")
    result = run(moved, "production_guard")

    assert result.selected is None
    stale_sources = {
        r.plan_id.split("|")[0]
        for r in result.rejections
        if r.constraint == "qualification_stale"
    }
    assert stale_sources == {
        "record_reconciliation@v1",
        "frontier_judge@v2",
        "clinician_review@v1",
    }


def test_the_rationale_names_what_the_evidence_was_measured_against(voice_early):
    """A plan a reader cannot trace back to a system state is not auditable."""
    from assurance_planner.rationale import render

    request = voice_early.request("nightly")
    result = plan(
        request.context, voice_early.failure_mode, request.profile, voice_early.world
    )
    text = render(
        result,
        request.context,
        voice_early.failure_mode,
        request.profile,
        voice_early.world,
    )
    assert "against voice-agent-turntaking-r4" in text
