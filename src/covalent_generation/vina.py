"""AutoDock Vina command-line adapter.

This adapter assumes receptor and ligand are already prepared as PDBQT files.
Preparation is kept outside the project so users can choose their preferred
protonation, atom typing, and covalent-ligand representation.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .interfaces import DockingRequest, DockingResult


class VinaDockingTool:
    name = "autodock-vina"

    def __init__(self, executable: str = "vina", timeout: int = 3600) -> None:
        self.executable = executable
        self.timeout = timeout

    def run(self, request: DockingRequest) -> DockingResult:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        pose_path = request.output_dir / f"{request.candidate.candidate_id}.pdbqt"
        cx, cy, cz = request.center
        sx, sy, sz = request.box_size
        command = [
            self.executable,
            "--receptor", str(request.receptor),
            "--ligand", str(request.ligand),
            "--center_x", str(cx), "--center_y", str(cy), "--center_z", str(cz),
            "--size_x", str(sx), "--size_y", str(sy), "--size_z", str(sz),
            "--exhaustiveness", str(request.exhaustiveness),
            "--out", str(pose_path),
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=self.timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return DockingResult(request.candidate.candidate_id, "failed", tool=self.name, message=str(exc))
        text = f"{completed.stdout}\n{completed.stderr}"
        score = _first_affinity(text)
        status = "completed" if completed.returncode == 0 and score is not None else "failed"
        message = None if status == "completed" else text[-1000:].strip()
        return DockingResult(request.candidate.candidate_id, status, score, str(pose_path) if pose_path.exists() else None, self.name, message)


def _first_affinity(text: str) -> float | None:
    """Read Vina's first affinity in kcal/mol from stdout/stderr."""

    match = re.search(r"^\s*\d+\s+(-?\d+(?:\.\d+)?)\s+", text, re.MULTILINE)
    return float(match.group(1)) if match else None
