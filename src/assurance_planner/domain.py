"""Typed domain objects.

Grouped by the mutability classes in docs/architecture.md section 7.  The grouping is
enforced structurally, not by comment: identity-bearing fields live on frozen
dataclasses used as registry keys, economics live in a registry the qualification
lookup cannot reach, and planner-controlled fields appear only on PlanStep.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


# --------------------------------------------------------------------------------
# Enumerations
# --------------------------------------------------------------------------------


class Intent(StrEnum):
    DISCOVER = "discover"
    VERIFY_FIX = "verify_fix"
    ASSESS_BLAST_RADIUS = "assess_blast_radius"
    RELEASE = "release"


class SourceKind(StrEnum):
    DETERMINISTIC = "deterministic"
    STOCHASTIC_JUDGE = "stochastic_judge"
    HUMAN = "human"


class PopulationKind(StrEnum):
    #  A finite, enumerable set of cases.  "Sync" means a batch wall clock that blocks
    #  a developer.
    ENUMERABLE_CORPUS = "enumerable_corpus"
    #  A continuous arrival process.  "Sync" means latency added to a single end-user
    #  interaction.  These two quantities are never summed.
    LIVE_STREAM = "live_stream"


class Cadence(StrEnum):
    PER_CHANGE = "per_change"
    PER_CHECKPOINT = "per_checkpoint"
    NIGHTLY = "nightly"
    CONTINUOUS = "continuous"


class ExecutionMode(StrEnum):
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"


class UncertaintyDisposition(StrEnum):
    ACCEPT = "accept"
    ESCALATE = "escalate"


class StepRole(StrEnum):
    PRIMARY = "primary"
    HUMAN_CONFIRMATION = "human_confirmation"
    ESCALATION = "escalation"


#: Wall-clock seconds available to a cadence before the next one starts.  Used to
#: reject a plan that cannot finish inside its own window.
CADENCE_WINDOW_SECONDS: dict[Cadence, float] = {
    Cadence.PER_CHANGE: float("inf"),  # bounded by the context's feedback budget
    Cadence.PER_CHECKPOINT: float("inf"),  # bounded by the context's feedback budget
    Cadence.NIGHTLY: 8 * 3600.0,
    Cadence.CONTINUOUS: float("inf"),
}


# --------------------------------------------------------------------------------
# Versioned / frozen identities
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, order=True)
class SourceVersionRef:
    """Qualification key component.  Bumping ``version`` orphans prior evidence."""

    source_id: str
    version: str

    def __str__(self) -> str:
        return f"{self.source_id}@{self.version}"


@dataclass(frozen=True, slots=True, order=True)
class FailureModeRef:
    failure_mode_id: str
    version: str

    def __str__(self) -> str:
        return f"{self.failure_mode_id}@{self.version}"


@dataclass(frozen=True, slots=True)
class FailureMode:
    """A versioned behavioural failure definition.

    ``description`` is opaque to the planner.  Nothing in planner code may branch on
    its contents; domain risk judgement enters only through AssuranceProfile.
    """

    failure_mode_id: str
    version: str
    case_id: str
    description: str

    @property
    def ref(self) -> FailureModeRef:
        return FailureModeRef(self.failure_mode_id, self.version)


@dataclass(frozen=True, slots=True)
class EvidenceSourceVersion:
    source_id: str
    version: str
    kind: SourceKind
    #: Can this mechanism surface a failure its criterion did not anticipate?
    #: Structural property of the mechanism.  Gates `discover`.
    open_ended: bool
    #: Does it reconcile against a system of record rather than forming a judgement?
    consults_authoritative_source: bool

    @property
    def ref(self) -> SourceVersionRef:
        return SourceVersionRef(self.source_id, self.version)

    def __str__(self) -> str:
        return str(self.ref)


# --------------------------------------------------------------------------------
# Populations
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EvaluationPopulation:
    """A set of evaluable units plus the denominator any percentage refers to."""

    population_id: str
    #: Mandatory.  A run percentage is rendered only alongside this string.
    denominator: str
    kind: PopulationKind
    #: Enumerable corpora only.
    case_ids: tuple[str, ...] = ()
    #: Live streams only: expected units arriving per cadence window.
    units_per_window: int = 0

    @property
    def size(self) -> int:
        if self.kind is PopulationKind.ENUMERABLE_CORPUS:
            return len(self.case_ids)
        return self.units_per_window

    def contains_case(self, case_id: str) -> bool:
        if self.kind is PopulationKind.ENUMERABLE_CORPUS:
            return case_id in self.case_ids
        #: A live stream is assumed to carry any case that can occur in production.
        return True


# --------------------------------------------------------------------------------
# The system being evaluated
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SystemUnderTest:
    """A concrete build, and the behaviour distribution its owner declares it to be in.

    Sensitivity is a property of the *pair* (evaluator, system under test), not of the
    evaluator alone.  So qualification has to be keyed by something that identifies the
    system -- but keying on the build would orphan every measurement on every deploy,
    which is wrong for the overwhelming majority of deploys that do not move the
    behaviour distribution at all.

    Materiality is therefore **declared, not inferred**, exactly like assurance level.
    Two builds that share a ``distribution_id`` are an assertion by a human that they
    are interchangeable for the purpose of evaluator qualification.  That declaration
    is what buys continuity: a non-material change reuses every existing qualification
    row, and a material one is spelled by choosing a new ``distribution_id``, which
    orphans them all at once.

    The planner cannot check that assertion and does not try.  It is an input with the
    same epistemic status as ``maximum_error_requirement``.
    """

    system_version: str
    distribution_id: str

    def __str__(self) -> str:
        return f"{self.system_version} ({self.distribution_id})"


# --------------------------------------------------------------------------------
# Qualification evidence  (versioned between cycles; measurements are dynamic)
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QualificationKey:
    """Evaluator quality is never global: it is specific to all four of these.

    This key is also what freezes a verification claim.  A RED observed under
    ``oracle@v2`` is filed against ``oracle@v2``; a GREEN claimed under ``oracle@v3``
    looks up a key that does not exist and the source becomes inadmissible.  v0 needs
    no separate claim object to express that -- the lookup miss *is* the mechanism.

    ``distribution_id`` extends the same mechanism to the system being evaluated; see
    ``SystemUnderTest`` for why it is a declared distribution and not a build number.
    """

    source_version: SourceVersionRef
    failure_mode: FailureModeRef
    population_id: str
    distribution_id: str


@dataclass(frozen=True, slots=True)
class QualificationEvidence:
    key: QualificationKey
    #: Measured end-to-end over (system under test x evaluator).  The key names which
    #: system; v0 still cannot attribute a miss to one side or the other.
    sensitivity: float
    false_positive_rate: float
    observation_count: int
    prove_red_runs: int
    prove_green_runs: int
    evidence_date: date
    known_limitations: tuple[str, ...] = ()


# --------------------------------------------------------------------------------
# Execution economics  (dynamic; must never invalidate qualification)
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExecutionProfile:
    source_version: SourceVersionRef
    cost_per_invocation_usd: float
    latency_seconds_per_invocation: float
    parallelism: int = 1
    human_minutes_per_invocation: float = 0.0
    #: Human review capacity per cadence window; 0 means not human-limited.
    human_capacity_per_window: int = 0
    available: bool = True


# --------------------------------------------------------------------------------
# Externally supplied constraints
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AssuranceProfile:
    """Organisational risk appetite, supplied to the planner, never decided by it."""

    #: Opaque identifier.  Deliberately inert: the planner never interprets it.
    profile_ref: str
    maximum_error_requirement: float
    sampling_allowed: bool = True
    human_confirmation_required: bool = False
    authoritative_source_required: bool = False
    synchronous_requirement: bool = False
    uncertainty_disposition: UncertaintyDisposition = UncertaintyDisposition.ACCEPT
    #: Minimum qualification study size before evidence counts at all.
    minimum_observation_count: int = 1


@dataclass(frozen=True, slots=True)
class DevelopmentContext:
    """What the team is trying to accomplish right now.  Not a lifecycle stage."""

    intent: Intent
    #: Blocking wall clock a developer will tolerate, in seconds.
    feedback_budget_seconds: float
    #: Amortisation horizon.  How many changes and checkpoints occur per window
    #: (a window is one day).  These make cadence an economic decision rather than a
    #: free parameter: the same plan costs `runs_per_window` times as much per day at
    #: per-change cadence as it does nightly.
    changes_per_window: int = 1
    checkpoints_per_window: int = 1

    def runs_per_window(self, cadence: Cadence) -> int:
        match cadence:
            case Cadence.PER_CHANGE:
                return max(1, self.changes_per_window)
            case Cadence.PER_CHECKPOINT:
                return max(1, self.checkpoints_per_window)
            case Cadence.NIGHTLY | Cadence.CONTINUOUS:
                #: A live-stream population already counts a whole window of units.
                return 1


# --------------------------------------------------------------------------------
# Planner output
# --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PlanStep:
    role: StepRole
    source: EvidenceSourceVersion
    population: EvaluationPopulation
    sample_fraction: float
    replications: int
    threshold_k: int
    escalation_band: tuple[int, int] | None
    escalation_target: SourceVersionRef | None
    cadence: Cadence
    execution_mode: ExecutionMode
    miss_probability: float
    false_alarm_probability: float

    @property
    def denominator(self) -> str:
        """No percentage is available without one."""
        return self.population.denominator

    @property
    def units_selected(self) -> int:
        from math import ceil

        if self.sample_fraction <= 0.0:
            #: Conditional step (escalation): volume depends on an unmeasured base
            #: rate, so v0 reports it as conditional rather than inventing a number.
            return 0
        return max(1, ceil(self.population.size * self.sample_fraction))

    @property
    def is_conditional(self) -> bool:
        return self.sample_fraction <= 0.0

    @property
    def invocations(self) -> int:
        return self.units_selected * self.replications

    def scope_phrase(self) -> str:
        if self.is_conditional:
            return f"conditional on escalation band, within {self.denominator}"
        return (
            f"{self.sample_fraction * 100:g}% of {self.denominator} "
            f"({self.units_selected} of {self.population.size})"
        )


@dataclass(frozen=True, slots=True)
class PlanEconomics:
    #: Cost of executing the plan once.
    monetary_cost_usd: float
    #: Cost per day, given the plan's cadence and the context's change rate.  This is
    #: the ranking quantity: it is what makes nightly cheaper than per-change.
    monetary_cost_per_window_usd: float
    runs_per_window: int
    #: Batch wall clock that blocks a developer, per run.  Corpus steps only.  This
    #: is what the feedback budget is checked against.
    blocking_feedback_seconds: float
    #: The same wait, accumulated over a day at this cadence.  Ranked, because a
    #: 40-minute blocking run is a different proposition 15 times a day than twice.
    #: Without it, cadence is undetermined for a zero-cost source.
    blocking_feedback_seconds_per_window: float
    #: Latency added to one end-user interaction by a synchronous stream guard, and
    #: the fraction of interactions that pay it.  Reported as a pair and never
    #: multiplied together into an amortised average.
    conditional_interaction_latency_seconds: float
    conditional_interaction_fraction: float
    #: Asynchronous wall clock, checked against the cadence window, not the budget.
    background_wall_clock_seconds: float
    human_minutes: float
    human_minutes_per_window: float
    total_invocations: int


@dataclass(frozen=True, slots=True)
class EvidencePlan:
    plan_id: str
    steps: tuple[PlanStep, ...]
    economics: PlanEconomics

    @property
    def primary(self) -> PlanStep:
        return next(s for s in self.steps if s.role is StepRole.PRIMARY)


@dataclass(frozen=True, slots=True)
class Rejection:
    plan_id: str
    constraint: str
    reason: str


@dataclass(slots=True)
class PlanningResult:
    selected: EvidencePlan | None
    #: Admissible but more expensive, in ranked order.
    runners_up: list[EvidencePlan] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)
    #: Populated when nothing is admissible.
    no_plan_reason: str | None = None
