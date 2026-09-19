"""Stable, dependency-free contracts for integrating models and tools.

The project intentionally keeps the workflow independent of a particular
generator or docking package. Implement ``DockingTool`` for a local tool,
container, remote service, or an in-house model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Protocol


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


class DockingTool(Protocol):
    """Interface implemented by every docking backend."""

    name: str

    def run(self, request: DockingRequest) -> DockingResult:
        """Run one candidate and return a normalized result."""


class CandidateGenerator(Protocol):
    """Optional interface for any molecule-generation model or service."""

    name: str

    def generate(self, target: dict[str, Any], limit: int = 20) -> Iterable[Candidate]:
        """Return candidates with enough metadata for downstream filtering."""
