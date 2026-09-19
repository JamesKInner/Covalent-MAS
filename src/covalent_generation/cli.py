"""Command-line entry point for the minimal Vina workflow."""

from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import dock_candidates, read_candidates, write_results
from .vina import VinaDockingTool


def main() -> None:
    parser = argparse.ArgumentParser(description="Dock prepared candidate ligands with AutoDock Vina.")
    parser.add_argument("--candidates", type=Path, required=True, help="CSV with candidate_id,smiles,source columns.")
    parser.add_argument("--receptor", type=Path, required=True, help="Prepared receptor PDBQT.")
    parser.add_argument("--ligand-dir", type=Path, required=True, help="Directory containing <candidate_id>.pdbqt files.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/docking"))
    parser.add_argument("--results", type=Path, default=Path("outputs/docking_results.json"))
    parser.add_argument("--center", type=float, nargs=3, required=True, metavar=("X", "Y", "Z"))
    parser.add_argument("--box-size", type=float, nargs=3, required=True, metavar=("X", "Y", "Z"))
    parser.add_argument("--exhaustiveness", type=int, default=8)
    parser.add_argument("--vina", default="vina", help="Vina executable or absolute path.")
    args = parser.parse_args()
    results = dock_candidates(read_candidates(args.candidates), receptor=args.receptor, ligand_dir=args.ligand_dir,
                              output_dir=args.output_dir, center=tuple(args.center), box_size=tuple(args.box_size),
                              tool=VinaDockingTool(args.vina), exhaustiveness=args.exhaustiveness)
    write_results(results, args.results)
    for result in results:
        print(f"{result.candidate_id}: {result.status} score={result.score}")


if __name__ == "__main__":
    main()
