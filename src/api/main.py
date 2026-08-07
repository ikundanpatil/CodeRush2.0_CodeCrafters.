from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from src.models.schemas import (
    ResearchRun, ResearchCreateRequest, ResearchStatusResponse,
    ResearchResultResponse, AgentEvent
)
from src.models.memory import (
    Memory, MemorySearchResponse, MemorySearchResponseItem
)
from src.storage.store import store
from src.engine.orchestrator import orchestrator
from src.memory.manager import memory_manager

app = FastAPI(
    title="EvoResearch AE-02 API",
    description="Observable Autonomous Research MVP Phase 1 API",
    version="0.1.0"
)

# Enable CORS for frontend web integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "EvoResearch AE-02 Phase 1 MVP", "version": "0.1.0"}

@app.post("/api/research", response_model=ResearchStatusResponse, status_code=status.HTTP_201_CREATED)
async def create_research_run(payload: ResearchCreateRequest, background_tasks: BackgroundTasks):
    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=400, detail="Research question cannot be empty.")

    run = ResearchRun(question=payload.question.strip())
    store.save_run(run)

    # Launch autonomous orchestrator in background task
    background_tasks.add_task(orchestrator.execute_run, run.run_id)

    return ResearchStatusResponse(
        run_id=run.run_id,
        question=run.question,
        status=run.status,
        current_step=run.current_step,
        created_at=run.created_at,
        updated_at=run.updated_at,
        source_count=run.source_count,
        error=run.error
    )

@app.get("/api/research/{run_id}", response_model=ResearchStatusResponse)
def get_research_status(run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    return ResearchStatusResponse(
        run_id=run.run_id,
        question=run.question,
        status=run.status,
        current_step=run.current_step,
        created_at=run.created_at,
        updated_at=run.updated_at,
        source_count=run.source_count,
        error=run.error
    )

@app.get("/api/research/{run_id}/result", response_model=ResearchResultResponse)
def get_research_result(run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    return ResearchResultResponse(
        run_id=run.run_id,
        question=run.question,
        status=run.status,
        answer=run.answer,
        sources=run.sources,
        evidence=run.evidence,
        security_events=run.security_events,
        completed_at=run.completed_at
    )

@app.get("/api/research/{run_id}/trace", response_model=List[AgentEvent])
def get_research_trace(run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    return run.trace

@app.get("/api/history", response_model=List[ResearchStatusResponse])
def list_research_history():
    runs = store.list_runs()
    return [
        ResearchStatusResponse(
            run_id=r.run_id,
            question=r.question,
            status=r.status,
            current_step=r.current_step,
            created_at=r.created_at,
            updated_at=r.updated_at,
            source_count=r.source_count,
            error=r.error
        )
        for r in runs
    ]

# --------------------------------------------------------------------------
# Phase 3 - Memory API
# --------------------------------------------------------------------------
@app.get("/api/memory/search", response_model=MemorySearchResponse)
def memory_search(q: str = "", top_k: int = 5):
    top_k = max(1, min(int(top_k), 50))
    results = memory_manager.search(q, top_k=top_k)
    return MemorySearchResponse(
        query=q,
        results=[
            MemorySearchResponseItem(
                id=r.memory.id,
                memory_type=r.memory.memory_type.value,
                content=r.memory.content,
                summary=r.memory.summary,
                confidence=r.memory.confidence,
                importance=r.memory.importance,
                similarity=r.similarity,
                research_run_id=r.memory.research_run_id,
                created_at=r.memory.created_at,
            )
            for r in results
        ],
    )

@app.get("/api/memory/research/{research_run_id}", response_model=List[Memory])
def memory_by_research_run(research_run_id: str):
    """Return all memories associated with a research run."""
    memories = memory_manager.get_by_research_run(research_run_id)
    return [Memory(**m.model_dump()) for m in memories]

@app.get("/api/memory/{memory_id}", response_model=Memory)
def get_memory(memory_id: str):
    memory = memory_manager.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return memory

@app.post("/api/memory", response_model=Memory, status_code=status.HTTP_201_CREATED)
def create_memory(payload: Memory):
    """Controlled memory creation for testing/admin purposes.

    Restricted to Memory-type fields only; no unconstrained DB operations.
    """
    memory = Memory(
        memory_type=payload.memory_type,
        content=payload.content,
        summary=payload.summary,
        research_run_id=payload.research_run_id,
        source_ids=list(payload.source_ids or []),
        confidence=payload.confidence,
        importance=payload.importance,
        metadata=dict(payload.metadata or {}),
    )
    result = memory_manager.store(memory)
    return result.memory or memory
