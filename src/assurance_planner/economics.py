"""Cost, wall clock and human burden for a set of steps.

Two rules this module exists to enforce:

1. Blocking batch wall clock and per-interaction added latency are different physical
   quantities and are never added together or averaged into each other.
2. A conditional cost is reported as (per-invocation figure, fraction of traffic), not
   as their product.  "500ms on 10% of cases" never becomes "50ms".
"""

from __future__ import annotations

from .constraints import PlanBudgetFacts
from .domain import (
    CADENCE_WINDOW_SECONDS,
    DevelopmentContext,
    ExecutionMode,
    PlanEconomics,
    PlanStep,
    PopulationKind,
    SourceKind,
    StepRole,
)
from .registry import World


def compute(
    steps: tuple[PlanStep, ...], context: DevelopmentContext, world: World
) -> tuple[PlanEconomics, PlanBudgetFacts]:
    cost = 0.0
    blocking = 0.0
    background = 0.0
    conditional_latency = 0.0
    conditional_fraction = 0.0
    human_minutes = 0.0
    human_units = 0
    human_capacity = 0
    invocations = 0

    cadence = steps[0].cadence
    runs_per_window = context.runs_per_window(cadence)

    for step in steps:
        if step.is_conditional:
            #: Escalation volume is not estimated in v0; see architecture note s.6.
            continue
        profile = world.economics[step.source.ref]
        step_invocations = step.invocations
        invocations += step_invocations
        cost += step_invocations * profile.cost_per_invocation_usd

        wall = (
            step_invocations
            * profile.latency_seconds_per_invocation
            / max(1, profile.parallelism)
        )

        if step.execution_mode is ExecutionMode.SYNCHRONOUS:
            if step.population.kind is PopulationKind.ENUMERABLE_CORPUS:
                blocking += wall
            else:
                #: One interaction waits for its own replications, not for the batch.
                per_interaction = (
                    step.replications
                    * profile.latency_seconds_per_invocation
                    / max(1, profile.parallelism)
                )
                conditional_latency = max(conditional_latency, per_interaction)
                conditional_fraction = max(conditional_fraction, step.sample_fraction)
        else:
            background += wall

        if profile.human_minutes_per_invocation > 0.0:
            human_minutes += step_invocations * profile.human_minutes_per_invocation
            human_units += step_invocations
            if profile.human_capacity_per_window > 0:
                human_capacity = (
                    profile.human_capacity_per_window
                    if human_capacity == 0
                    else min(human_capacity, profile.human_capacity_per_window)
                )

    human_units_per_window = human_units * runs_per_window
    capacity_exceeded = human_capacity > 0 and human_units_per_window > human_capacity

    economics = PlanEconomics(
        monetary_cost_usd=round(cost, 8),
        monetary_cost_per_window_usd=round(cost * runs_per_window, 8),
        runs_per_window=runs_per_window,
        blocking_feedback_seconds=blocking,
        blocking_feedback_seconds_per_window=blocking * runs_per_window,
        conditional_interaction_latency_seconds=conditional_latency,
        conditional_interaction_fraction=conditional_fraction,
        background_wall_clock_seconds=background,
        human_minutes=human_minutes,
        human_minutes_per_window=human_minutes * runs_per_window,
        total_invocations=invocations,
    )
    facts = PlanBudgetFacts(
        blocking_feedback_seconds=blocking,
        background_wall_clock_seconds=background,
        cadence_window_seconds=CADENCE_WINDOW_SECONDS[cadence],
        human_units_per_window=human_units_per_window,
        human_capacity_per_window=human_capacity,
        human_capacity_exceeded=capacity_exceeded,
    )
    return economics, facts


def has_human_confirmation(steps: tuple[PlanStep, ...]) -> bool:
    """A plan whose primary evidence *is* a human needs no separate confirmer."""
    return any(
        s.role is StepRole.HUMAN_CONFIRMATION
        or (s.role is StepRole.PRIMARY and s.source.kind is SourceKind.HUMAN)
        for s in steps
    )
