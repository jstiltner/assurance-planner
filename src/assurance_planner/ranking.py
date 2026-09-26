"""Ranking.

Deliberately dumb: least cost, then least delay, then least human burden, then a
stable identifier.  There is no intent-dependent weighting and no quality bonus.
Everything that makes one plan *better* rather than *cheaper* is an admissibility
constraint in constraints.py.

If this module ever needs a tuned coefficient to make an acceptance scenario pass,
that is evidence the abstraction has failed and should be reported, not patched here.
"""

from __future__ import annotations

from .domain import EvidencePlan

#: Printed in rationale so the ordering is never a mystery.
RANK_KEY_DESCRIPTION = (
    "monetary cost per day, then developer wait per day, then added interaction "
    "latency, then human minutes per day, then total invocations, then plan id"
)


def rank_key(plan: EvidencePlan) -> tuple[float, float, float, float, int, str]:
    e = plan.economics
    return (
        round(e.monetary_cost_per_window_usd, 8),
        e.blocking_feedback_seconds_per_window,
        e.conditional_interaction_latency_seconds,
        e.human_minutes_per_window,
        e.total_invocations,
        plan.plan_id,
    )


def rank(plans: list[EvidencePlan]) -> list[EvidencePlan]:
    return sorted(plans, key=rank_key)


def explain_loss(winner: EvidencePlan, loser: EvidencePlan) -> str:
    """Why an admissible plan lost.  Names the first field that separates them."""
    w, l = winner.economics, loser.economics
    if round(l.monetary_cost_per_window_usd, 8) > round(
        w.monetary_cost_per_window_usd, 8
    ):
        return (
            f"admissible but dominated on cost: "
            f"${l.monetary_cost_per_window_usd:.4f}/window vs "
            f"${w.monetary_cost_per_window_usd:.4f}/window"
        )
    if l.blocking_feedback_seconds_per_window > w.blocking_feedback_seconds_per_window:
        return (
            f"admissible at equal cost but costs more developer waiting: "
            f"{l.blocking_feedback_seconds_per_window / 60:.0f} min/day blocked "
            f"({l.blocking_feedback_seconds / 60:.0f} min x {l.runs_per_window}/day) "
            f"vs {w.blocking_feedback_seconds_per_window / 60:.0f} min/day"
        )
    if l.conditional_interaction_latency_seconds > w.conditional_interaction_latency_seconds:
        return (
            f"admissible at equal cost but adds more interaction latency: "
            f"{l.conditional_interaction_latency_seconds:.2f}s vs "
            f"{w.conditional_interaction_latency_seconds:.2f}s"
        )
    if l.human_minutes_per_window > w.human_minutes_per_window:
        return (
            f"admissible at equal cost but needs more human time: "
            f"{l.human_minutes_per_window:.0f} min/window vs "
            f"{w.human_minutes_per_window:.0f} min/window"
        )
    if l.total_invocations > w.total_invocations:
        return (
            f"admissible at equal cost and latency but runs more invocations: "
            f"{l.total_invocations} vs {w.total_invocations} "
            f"(no additional qualified evidence is required here)"
        )
    return "admissible and equivalent on every ranked quantity; broken by plan id"
