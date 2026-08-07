from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from src.models.schemas import (
    ResearchRun, ResearchCreateRequest, ResearchStatusResponse,
    ResearchResultResponse, AgentEvent
)
from src.storage.store import store
from src.engine.orchestrator import orchestrator

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
