"""The world the planner reasons about.

Qualification and economics live in two dicts that are never merged and never
cross-read.  ``World.reprice`` exists to make that testable: it can change any price
and cannot reach a qualification row.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .domain import (
    EvaluationPopulation,
    EvidenceSourceVersion,
    ExecutionProfile,
    FailureMode,
    FailureModeRef,
    PopulationKind,
    QualificationEvidence,
    QualificationKey,
    SourceVersionRef,
    SystemUnderTest,
)


@dataclass
class World:
    #: No default.  A world in which nothing is declared about the system being
    #: evaluated is not a world in which any qualification measurement means anything.
    system_under_test: SystemUnderTest

    failure_modes: dict[FailureModeRef, FailureMode] = field(default_factory=dict)
    sources: dict[SourceVersionRef, EvidenceSourceVersion] = field(default_factory=dict)
    populations: dict[str, EvaluationPopulation] = field(default_factory=dict)

    # --- two separate registries; see architecture note section 1.7 ---------------
    qualification: dict[QualificationKey, QualificationEvidence] = field(
        default_factory=dict
    )
    economics: dict[SourceVersionRef, ExecutionProfile] = field(default_factory=dict)

    #: Every case the team currently regards as a known regression.  Used to decide
    #: whether a population covers blast radius; derived, not declared per-population.
    known_regression_cases: frozenset[str] = frozenset()

    # -----------------------------------------------------------------------------
    # Lookups
    # -----------------------------------------------------------------------------

    def add_source(self, source: EvidenceSourceVersion) -> None:
        self.sources[source.ref] = source

    def add_population(self, population: EvaluationPopulation) -> None:
        self.populations[population.population_id] = population

    def add_qualification(self, evidence: QualificationEvidence) -> None:
        self.qualification[evidence.key] = evidence

    def add_economics(self, profile: ExecutionProfile) -> None:
        self.economics[profile.source_version] = profile

    def qualification_for(
        self,
        source: EvidenceSourceVersion,
        failure_mode: FailureMode,
        population: EvaluationPopulation,
    ) -> QualificationEvidence | None:
        """Exact match on the key.  No inheritance, no defaults, no fallback.

        A miss is the mechanism by which a version bump, a failure-mode redefinition,
        an untested population or a moved behaviour distribution makes a source
        inadmissible.
        """
        return self.qualification.get(
            QualificationKey(
                source_version=source.ref,
                failure_mode=failure_mode.ref,
                population_id=population.population_id,
                distribution_id=self.system_under_test.distribution_id,
            )
        )

    def stale_qualification_for(
        self,
        source: EvidenceSourceVersion,
        failure_mode: FailureMode,
        population: EvaluationPopulation,
    ) -> tuple[QualificationEvidence, ...]:
        """Rows that would match but for the behaviour distribution.

        Only for diagnosis.  These are never usable -- the point is to be able to say
        "measured against a system that is no longer running" instead of the far less
        actionable "no qualification evidence".
        """
        return tuple(
            evidence
            for key, evidence in self.qualification.items()
            if key.source_version == source.ref
            and key.failure_mode == failure_mode.ref
            and key.population_id == population.population_id
            and key.distribution_id != self.system_under_test.distribution_id
        )

    def economics_for(self, source: EvidenceSourceVersion) -> ExecutionProfile | None:
        return self.economics.get(source.ref)

    def population_covers_blast_radius(self, population: EvaluationPopulation) -> bool:
        """A live stream carries every case that can occur, so it always covers.

        Consistent with ``EvaluationPopulation.contains_case``.  The difference is
        that a stream can never be *exhausted*, which is why the coverage constraint
        treats fractions differently for the two kinds (see constraints.check_goal).
        """
        if population.kind is PopulationKind.LIVE_STREAM:
            return True
        if not self.known_regression_cases:
            return False
        return self.known_regression_cases.issubset(set(population.case_ids))

    # -----------------------------------------------------------------------------
    # Dynamic mutation helpers.  Each touches exactly one registry.
    # -----------------------------------------------------------------------------

    def reprice(self, source_version: SourceVersionRef, **changes: object) -> "World":
        """Return a copy with changed economics.  Cannot reach qualification."""
        profile = self.economics[source_version]
        updated = dict(self.economics)
        updated[source_version] = replace(profile, **changes)  # type: ignore[arg-type]
        return replace(self, economics=updated)

    def requalify(self, key: QualificationKey, **changes: object) -> "World":
        """Return a copy with changed measurements.  Cannot reach economics."""
        evidence = self.qualification[key]
        updated = dict(self.qualification)
        updated[key] = replace(evidence, **changes)  # type: ignore[arg-type]
        return replace(self, qualification=updated)
