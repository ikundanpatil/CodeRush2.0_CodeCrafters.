"""Phase 10 - cooperative research cancellation.

A minimal, additive backend change to support the voice UI's "Stop"
command: a `cancel_requested` flag on `ResearchRun` that `ResearchLoop`
checks between iterations. Real cancellation at a real checkpoint -- never
kills the process, never pretends an in-flight iteration was interrupted
mid-search.
"""

import asyncio
from typing import List

from fastapi.testclient import TestClient

from src.api.main import app
from src.engine.orchestrator import orchestrator
from src.engine.research_loop import IterationDecision, ResearchLoop
from src.llm.providers.mock import MockAdapter
from src.memory.manager import memory_manager
from src.models.schemas import ResearchRun, RunStatus
from src.search.base import SearchProvider, SearchResult
from src.search.providers.mock import MockSearchProvider
from src.storage.store import store

client = TestClient(app)


class _CancelDuringFirstSearchProvider(SearchProvider):
    """Returns one (insufficient) source on its first call, then flips
    `cancel_requested` on the run -- simulating the user pressing Stop while
    iteration 1 is still in flight. Iteration 1 is allowed to finish
    normally; the loop must stop before iteration 2 starts."""

    provides_full_content = True

    def __init__(self, run: ResearchRun):
        self.run = run
        self.calls = 0

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        self.calls += 1
        self.run.cancel_requested = True
        return [SearchResult(
            title="Source A", url="https://a.example.com/study",
            content="A study found a boost in outcomes.", source="Test Journal", score=0.9,
        )]


# --------------------------------------------------------------------------
# ResearchLoop-level cooperative cancellation
# --------------------------------------------------------------------------

def test_research_loop_stops_immediately_when_already_cancelled():
    run = ResearchRun(question="Q")
    run.cancel_requested = True
    loop = ResearchLoop(llm=MockAdapter(), search_provider=MockSearchProvider(), run=run, max_iterations=3)

    result = asyncio.run(loop.run(initial_queries=["Q"]))

    assert result.final_decision == IterationDecision.CANCELLED
    assert len(result.iterations) == 0
    assert len(result.sources) == 0


def test_research_loop_stops_before_next_iteration_once_cancelled_midrun():
    run = ResearchRun(question="Q")
    provider = _CancelDuringFirstSearchProvider(run)
    loop = ResearchLoop(llm=MockAdapter(), search_provider=provider, run=run, max_iterations=3)

    result = asyncio.run(loop.run(initial_queries=["Q"]))

    # Iteration 1 completed (its search already returned before the flag
    # flipped) -- only iteration 2 was skipped, at the top-of-loop checkpoint.
    assert provider.calls == 1
    assert len(result.iterations) == 1
    assert result.final_decision == IterationDecision.CANCELLED
    assert result.final_decision != IterationDecision.MAX_ITERATIONS_REACHED


# --------------------------------------------------------------------------
# Orchestrator-level: cancellation skips report generation + memory storage
# --------------------------------------------------------------------------

def test_orchestrator_marks_run_cancelled_and_skips_report_and_memory():
    run = ResearchRun(question="Does cancellation stop the pipeline cleanly?")
    provider = _CancelDuringFirstSearchProvider(run)
    store.save_run(run)

    import src.engine.orchestrator as orchestrator_module
    original_get_search = orchestrator_module.ResearchOrchestrator._get_search
    orchestrator_module.ResearchOrchestrator._get_search = lambda self, r: provider
    try:
        asyncio.run(orchestrator.execute_run(run.run_id))
    finally:
        orchestrator_module.ResearchOrchestrator._get_search = original_get_search

    finished = store.get_run(run.run_id)
    assert finished.status == RunStatus.CANCELLED
    assert "cancelled" in finished.answer.lower()
    assert finished.completed_at is not None
    # Report generation and memory storage were skipped entirely.
    assert memory_manager.get_by_research_run(run.run_id) == []


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

def test_cancel_unknown_run_returns_404():
    assert client.post("/api/research/does-not-exist/cancel").status_code == 404


def test_cancel_endpoint_sets_flag_on_a_pending_run():
    run = ResearchRun(question="Q")
    store.save_run(run)

    response = client.post(f"/api/research/{run.run_id}/cancel")

    assert response.status_code == 200
    assert store.get_run(run.run_id).cancel_requested is True


def test_cancel_on_a_completed_run_is_a_safe_noop():
    response = client.post("/api/research", json={"question": "Does exercise improve health outcomes?"})
    run_id = response.json()["run_id"]
    # TestClient executes BackgroundTasks synchronously, so with the mock
    # providers this run is already finished by the time we get here.
    assert client.get(f"/api/research/{run_id}").json()["status"] == "completed"

    cancel_response = client.post(f"/api/research/{run_id}/cancel")

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "completed"
    assert store.get_run(run_id).cancel_requested is False
