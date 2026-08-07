import json
import os
from typing import Dict, List, Optional
from src.models.schemas import ResearchRun, RunStatus

class MemoryStore:
    def __init__(self):
        self._runs: Dict[str, ResearchRun] = {}

    def save_run(self, run: ResearchRun):
        self._runs[run.run_id] = run

    def get_run(self, run_id: str) -> Optional[ResearchRun]:
        return self._runs.get(run_id)

    def list_runs(self) -> List[ResearchRun]:
        # Return sorted by created_at descending
        return sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)

store = MemoryStore()
