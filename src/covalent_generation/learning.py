"""Append-only trajectory storage for iterative covalent molecule design."""

from __future__ import annotations

import json
from pathlib import Path

from .interfaces import TrajectoryEvent


class JsonlTrajectoryStore:
    """Store workflow events as portable JSON Lines records.

    JSONL keeps the event history inspectable and makes it straightforward to
    stream trajectories into a database, feature pipeline, or training set.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, event: TrajectoryEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def query(
        self,
        *,
        target_id: str | None = None,
        stage: str | None = None,
        limit: int | None = None,
    ) -> list[TrajectoryEvent]:
        if not self.path.exists() or (limit is not None and limit <= 0):
            return []
        events: list[TrajectoryEvent] = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = json.loads(line)
                if target_id is not None and payload.get("target_id") != target_id:
                    continue
                if stage is not None and payload.get("stage") != stage:
                    continue
                payload["candidate_ids"] = tuple(payload.get("candidate_ids", ()))
                events.append(TrajectoryEvent(**payload))
                if limit is not None and len(events) >= limit:
                    break
        return events
