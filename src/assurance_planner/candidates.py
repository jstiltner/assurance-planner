"""Deterministic candidate enumeration.

The enumerator proposes replication counts rather than solving for them, so the
replication count in the selected plan is the outcome of ranking a real choice, not a
solver's opinion handed straight to the output.

Enumerated (planner-controlled, never read from configuration):

    primary source x population x sample fraction x replications x cadence x mode

Derived, not enumerated:

    decision threshold k     smallest threshold meeting the error bound at that n
    escalation step          iff policy escalates and the band is non-empty
    human confirmation step  iff policy requires it
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from .domain import (
    AssuranceProfile,
    Cadence,
    EvaluationPopulation,
    EvidenceSourceVersion,
    ExecutionMode,
    FailureMode,
    PopulationKind,
)
from .registry import World
from .statistics import MAX_REPLICATIONS, minimal_procedure

#: Fractions the planner may choose from.  A coarse ladder is enough to demonstrate
#: that run percentage is a decision variable; a continuous search would add no
#: information about the abstraction.
SAMPLE_FRACTIONS: tuple[float, ...] = (1.0, 0.25, 0.10, 0.05)

#: Replication counts offered to the ranker.  The ladder is dense at the bottom
#: because that is where the interesting boundary is.
_LADDER: tuple[int, ...] = tuple(range(1, 13))


@dataclass(frozen=True, slots=True)
class Candidate:
    source: EvidenceSourceVersion
    population: EvaluationPopulation
    sample_fraction: float
    replications: int
    cadence: Cadence
    execution_mode: ExecutionMode

    @property
    def family(self) -> tuple[str, str]:
        return (str(self.source.ref), self.population.population_id)

    @property
    def candidate_id(self) -> str:
        return (
            f"{self.source.ref}|{self.population.population_id}"
            f"|f{self.sample_fraction:g}|n{self.replications}"
            f"|{self.cadence}|{self.execution_mode}"
        )


def replication_options(
    source: EvidenceSourceVersion,
    failure_mode: FailureMode,
    population: EvaluationPopulation,
    profile: AssuranceProfile,
    world: World,
) -> tuple[int, ...]:
    """The ladder, extended once if this source needs more runs than the ladder has.

    The extension keeps a very noisy source from being reported as impossible when it
    is merely expensive.
    """
    evidence = world.qualification_for(source, failure_mode, population)
    options = set(_LADDER)
    if evidence is not None:
        sensitivity, false_positive_rate = evidence.planning_rates(profile.estimator)
        minimal = minimal_procedure(
            sensitivity,
            false_positive_rate,
            profile.maximum_error_requirement,
        )
        if minimal is not None and minimal.replications <= MAX_REPLICATIONS:
            options.add(minimal.replications)
    return tuple(sorted(options))


def enumerate_candidates(
    failure_mode: FailureMode, profile: AssuranceProfile, world: World
) -> list[Candidate]:
    from .constraints import structurally_coherent

    out: list[Candidate] = []
    sources = sorted(world.sources.values(), key=lambda s: (s.source_id, s.version))
    populations = sorted(world.populations.values(), key=lambda p: p.population_id)

    for source, population in product(sources, populations):
        replications = replication_options(
            source, failure_mode, population, profile, world
        )
        #: Sampling is offered only where the population cannot be exhausted.  v0 has
        #: no model of *which* corpus cases to drop or what is lost by dropping them,
        #: so it does not pretend to make that choice.  See architecture note s.6.
        fractions = (
            SAMPLE_FRACTIONS
            if population.kind is PopulationKind.LIVE_STREAM
            else (1.0,)
        )
        for fraction, reps, cadence, mode in product(
            fractions,
            replications,
            sorted(Cadence, key=str),
            sorted(ExecutionMode, key=str),
        ):
            if not structurally_coherent(population, cadence, mode):
                continue
            out.append(
                Candidate(source, population, fraction, reps, cadence, mode)
            )
    return out
