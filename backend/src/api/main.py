import os

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
from src.evidence.store import get_evidence_store
from src.models.evidence import Claim, Evidence, RelationshipType
from src.evolution.models import EvolutionCycleResult, Strategy
from src.evolution.service import evolution_service
from src.evolution.store import get_evolution_store

app = FastAPI(
    title="EvoResearch AE-02 API",
    description="Observable Autonomous Research MVP Phase 1 API",
    version="0.1.0"
)

# Enable CORS for the local frontend (configurable via CORS_ORIGINS, comma-separated)
_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
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
        completed_at=run.completed_at,
        claim_count=run.claim_count,
        evidence_graph_available=run.evidence_graph_available,
        quality_result=run.quality_result,
        quality_valid=run.quality_valid,
        iteration_count=len(run.iterations),
        research_decision=run.research_decision,
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

# --------------------------------------------------------------------------
# Phase 4 - Evidence Graph API
# --------------------------------------------------------------------------
@app.get("/api/evidence/research/{research_run_id}", response_model=List[Claim])
def evidence_claims_for_run(research_run_id: str):
    """All claims extracted for a research run."""
    return get_evidence_store().list_claims_by_run(research_run_id)

@app.get("/api/evidence/claims/{claim_id}", response_model=Claim)
def evidence_get_claim(claim_id: str):
    claim = get_evidence_store().get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")
    return claim

@app.get("/api/evidence/claims/{claim_id}/evidence", response_model=List[Evidence])
def evidence_for_claim(claim_id: str):
    return get_evidence_store().list_evidence_by_claim(claim_id)

@app.get("/api/evidence/claims/{claim_id}/contradictions", response_model=List[Evidence])
def evidence_contradictions_for_claim(claim_id: str):
    return get_evidence_store().get_contradictions_for_claim(claim_id)

@app.get("/api/evidence/graph/{research_run_id}")
def evidence_graph_for_run(research_run_id: str):
    """Node/edge graph: {"research_run_id", "nodes": [{id,type,label}], "edges": [{from,to,relationship}]}."""
    ev_store = get_evidence_store()
    claims = ev_store.list_claims_by_run(research_run_id)
    run = store.get_run(research_run_id)
    source_titles = {s.id: s.title for s in run.sources} if run else {}

    nodes = []
    edges = []
    seen_node_ids = set()

    def add_node(node_id: str, node_type: str, label: str):
        if node_id in seen_node_ids:
            return
        seen_node_ids.add(node_id)
        nodes.append({"id": node_id, "type": node_type, "label": label})

    for claim in claims:
        add_node(claim.id, "claim", claim.claim_text)
        for rel in ev_store.list_relationships_from(claim.id):
            edges.append({"from": rel.from_id, "to": rel.to_id, "relationship": rel.relationship_type.value})

        for evidence in ev_store.list_evidence_by_claim(claim.id):
            add_node(evidence.id, "evidence", evidence.evidence_text[:120])
            source_id = evidence.source_id
            if source_id:
                add_node(source_id, "source", source_titles.get(source_id, source_id))
                for rel in ev_store.list_relationships_from(evidence.id):
                    edges.append({"from": rel.from_id, "to": rel.to_id, "relationship": rel.relationship_type.value})

    return {"research_run_id": research_run_id, "nodes": nodes, "edges": edges}

# --------------------------------------------------------------------------
# Phase 5 - Research Quality API
# --------------------------------------------------------------------------
@app.get("/api/research/{run_id}/quality")
def get_research_quality(run_id: str):
    """Structured research-quality result for a run, computed from the
    run's actual sources/evidence/claims/evidence graph. Never fabricates
    figures the run does not have."""
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    if not run.quality_result:
        return {
            "run_id": run_id,
            "quality": None,
            "message": "Quality validation has not run yet for this research run.",
        }

    return {"run_id": run_id, "quality": run.quality_result}

# --------------------------------------------------------------------------
# Phase 6 - Autonomous Research Loop API
# --------------------------------------------------------------------------
@app.get("/api/research/{run_id}/iterations")
def get_research_iterations(run_id: str):
    """Per-iteration record of the autonomous research loop for a run --
    queries tried, new/duplicate sources, evidence/claim counts, and the
    quality-driven decision at each step. Empty list if the loop hasn't
    produced any iterations yet (e.g. the run is still planning)."""
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    return {"run_id": run_id, "iterations": run.iterations}

# --------------------------------------------------------------------------
# Phase 7 - Self-Evolution API
# --------------------------------------------------------------------------
@app.post("/api/strategy/evolve", response_model=EvolutionCycleResult)
async def trigger_evolution_cycle():
    """Run one full Research Strategy -> ... -> Accept/Reject cycle against
    the fixed offline benchmark and return the result. Only affects future
    research runs if the candidate strategy is accepted."""
    return await evolution_service.run_cycle()

@app.get("/api/strategy/current", response_model=Strategy)
def get_current_strategy():
    """The current champion strategy applied to new research runs."""
    return get_evolution_store().get_champion()

@app.get("/api/strategy/lineage", response_model=List[Strategy])
def get_strategy_lineage():
    """Full strategy history, newest generation first, including rejected candidates."""
    return get_evolution_store().list_lineage()

@app.get("/api/strategy/{strategy_id}", response_model=Strategy)
def get_strategy(strategy_id: str):
    strategy = get_evolution_store().get(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found.")
    return strategy
