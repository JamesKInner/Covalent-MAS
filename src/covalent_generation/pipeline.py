"""Simple orchestration and JSON/CSV helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .interfaces import Candidate, DockingRequest, DockingResult, DockingTool


def read_candidates(path: Path) -> list[Candidate]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [Candidate(row["candidate_id"], row["smiles"], row.get("source", "csv")) for row in csv.DictReader(handle)]


def dock_candidates(candidates: Iterable[Candidate], *, receptor: Path, ligand_dir: Path, output_dir: Path,
                    center: tuple[float, float, float], box_size: tuple[float, float, float],
                    tool: DockingTool, exhaustiveness: int = 8) -> list[DockingResult]:
    results: list[DockingResult] = []
    for candidate in candidates:
        ligand = ligand_dir / f"{candidate.candidate_id}.pdbqt"
        request = DockingRequest(candidate, receptor, ligand, center, box_size, output_dir, exhaustiveness)
        results.append(tool.run(request))
    return results


def write_results(results: Iterable[DockingResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([item.as_dict() for item in results], indent=2, ensure_ascii=False), encoding="utf-8")
