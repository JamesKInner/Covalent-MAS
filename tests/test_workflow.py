from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from covalent_generation import (
    Candidate,
    MemoryRecord,
    OptimizationObjective,
    OptimizationResult,
    SkillRecord,
    TrajectoryEvent,
)
from covalent_generation.learning import JsonlTrajectoryStore
from covalent_generation.pipeline import optimize_candidates


class RecordingOptimizer:
    name = "recording-optimizer"

    def optimize(self, request):
        child = Candidate(
            candidate_id=f"{request.parent.candidate_id}-child",
            smiles=request.parent.smiles + "C",
            source=self.name,
            metadata={"parent_id": request.parent.candidate_id},
        )
        return OptimizationResult(
            parent_candidate_id=request.parent.candidate_id,
            candidates=(child,),
            status="completed",
            model=self.name,
            metadata={
                "memory_count": len(request.recalled_memory),
                "skill_count": len(request.active_skills),
            },
        )


class WorkflowContractTests(unittest.TestCase):
    def test_optimizer_receives_memory_and_skills(self) -> None:
        memory = MemoryRecord("mem-1", "A useful edit", ("event-1",))
        skill = SkillRecord(
            "skill-1",
            "Preserve warhead",
            "Keep the reactive group while editing the scaffold.",
            {"warhead": "acrylamide"},
            ("identify_warhead", "edit_scaffold", "re_evaluate"),
            ("event-1",),
        )
        results = optimize_candidates(
            [Candidate("parent-1", "C=CC(=O)N", "generator")],
            target={"target_id": "target-1"},
            objectives=(OptimizationObjective("selectivity", "maximize"),),
            optimizer=RecordingOptimizer(),
            recalled_memory=(memory,),
            active_skills=(skill,),
            children_per_parent=3,
        )

        self.assertEqual(results[0].parent_candidate_id, "parent-1")
        self.assertEqual(results[0].candidates[0].metadata["parent_id"], "parent-1")
        self.assertEqual(results[0].metadata, {"memory_count": 1, "skill_count": 1})

    def test_jsonl_trajectory_store_is_append_only_and_queryable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = JsonlTrajectoryStore(Path(directory) / "trajectories.jsonl")
            for index, stage in enumerate(("generation", "optimization"), start=1):
                store.append(
                    TrajectoryEvent(
                        event_id=f"event-{index}",
                        run_id="run-1",
                        target_id="target-1",
                        iteration=index,
                        stage=stage,
                        created_at=f"2026-01-01T00:00:0{index}+00:00",
                        candidate_ids=(f"candidate-{index}",),
                    )
                )

            self.assertEqual(len(store.query(target_id="target-1")), 2)
            optimized = store.query(stage="optimization")
            self.assertEqual([event.event_id for event in optimized], ["event-2"])
            self.assertEqual(optimized[0].candidate_ids, ("candidate-2",))


if __name__ == "__main__":
    unittest.main()
