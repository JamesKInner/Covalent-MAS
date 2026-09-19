"""Stable, dependency-free contracts for covalent molecule design.

The project intentionally keeps the workflow independent of a particular
generator, optimizer, or docking package. Implement these protocols for a
local tool, container, remote service, or an in-house model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Protocol, Sequence


@dataclass(frozen=True)
class Candidate:
    """One generated molecule before structure-based evaluation."""

    candidate_id: str
    smiles: str
    source: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DockingRequest:
    """Inputs shared by all docking implementations."""

    candidate: Candidate
    receptor: Path
    ligand: Path
    center: tuple[float, float, float]
    box_size: tuple[float, float, float]
    output_dir: Path
    exhaustiveness: int = 8


@dataclass(frozen=True)
class DockingResult:
    """Normalized docking output used by downstream reporting."""

    candidate_id: str
    status: str
    score: float | None = None
    pose_path: str | None = None
    tool: str = "unknown"
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OptimizationObjective:
    """One property objective or constraint used during molecule optimization."""

    name: str
    direction: str
    weight: float = 1.0
    target: float | None = None
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryRecord:
    """Evidence-linked experience that can be retrieved for a later iteration."""

    memory_id: str
    summary: str
    evidence_event_ids: tuple[str, ...]
    target_scope: str | None = None
    retrieval_tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillRecord:
    """A versioned, reusable optimization or evaluation procedure."""

    skill_id: str
    name: str
    description: str
    applicability: dict[str, Any]
    procedure: tuple[str, ...]
    evidence_event_ids: tuple[str, ...]
    version: str = "1.0"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationRequest:
    """Target and retrieved knowledge supplied to a molecule generator."""

    target: dict[str, Any]
    recalled_memory: tuple[MemoryRecord, ...] = ()
    active_skills: tuple[SkillRecord, ...] = ()
    limit: int = 20
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OptimizationRequest:
    """Context supplied to a multi-objective covalent molecule optimizer."""

    parent: Candidate
    target: dict[str, Any]
    objectives: tuple[OptimizationObjective, ...]
    evaluation: dict[str, Any] = field(default_factory=dict)
    recalled_memory: tuple[MemoryRecord, ...] = ()
    active_skills: tuple[SkillRecord, ...] = ()
    limit: int = 20
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OptimizationResult:
    """Normalized result from a covalent multi-objective optimization model."""

    parent_candidate_id: str
    candidates: tuple[Candidate, ...]
    status: str
    model: str
    objective_values: dict[str, dict[str, float]] = field(default_factory=dict)
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TrajectoryEvent:
    """One append-only event in a generation, evaluation, or optimization run."""

    event_id: str
    run_id: str
    target_id: str
    iteration: int
    stage: str
    created_at: str
    candidate_ids: tuple[str, ...] = ()
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    decision: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class DockingTool(Protocol):
    """Interface implemented by every docking backend."""

    name: str

    def run(self, request: DockingRequest) -> DockingResult:
        """Run one candidate and return a normalized result."""


class CandidateGenerator(Protocol):
    """Interface for a knowledge-aware molecule-generation model or service."""

    name: str

    def generate(self, request: GenerationRequest) -> Iterable[Candidate]:
        """Return candidates with enough lineage for downstream filtering."""


class CovalentOptimizer(Protocol):
    """Interface for a model that optimizes multiple covalent-drug properties."""

    name: str

    def optimize(self, request: OptimizationRequest) -> OptimizationResult:
        """Generate optimized children while preserving parent-child lineage."""


class TrajectoryStore(Protocol):
    """Append and retrieve auditable workflow events."""

    def append(self, event: TrajectoryEvent) -> None:
        """Persist one event without mutating earlier events."""

    def query(
        self,
        *,
        target_id: str | None = None,
        stage: str | None = None,
        limit: int | None = None,
    ) -> Sequence[TrajectoryEvent]:
        """Return matching events in insertion order."""


class ExperienceBuilder(Protocol):
    """Build evidence-linked memory and reusable skills from trajectories."""

    name: str

    def build_memory(self, events: Sequence[TrajectoryEvent]) -> Iterable[MemoryRecord]:
        """Summarize transferable observations with source-event references."""

    def build_skills(
        self,
        events: Sequence[TrajectoryEvent],
        memory: Sequence[MemoryRecord],
    ) -> Iterable[SkillRecord]:
        """Create versioned procedures supported by trajectory evidence."""


class KnowledgeRetriever(Protocol):
    """Retrieve relevant memory and skills for a new design iteration."""

    def retrieve(
        self,
        *,
        target: dict[str, Any],
        candidate: Candidate | None = None,
        limit: int = 10,
    ) -> tuple[Sequence[MemoryRecord], Sequence[SkillRecord]]:
        """Return context ranked for the current target and molecule."""
