import os

from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

# Must be the first src import: loads backend/.env into the process before
# any other module's module-level os.getenv() calls (several -- memory
# singletons, provider factories -- run at import time). See src/config.py.
from src import config as _config

from src.models.schemas import (
    ResearchRun, ResearchCreateRequest, ResearchStatusResponse,
    ResearchResultResponse, ResearchHistoryItem, AgentEvent, RunStatus, EventType
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
from src.policy import rules as policy_rules
from src.policy.audit import policy_audit_log
from src.policy.engine import policy_engine
from src.policy.models import PolicyAction, PolicyRequest, PolicyResult
from src.benchmark.comparator import strategy_comparator
from src.benchmark.models import BenchmarkResult, StrategyComparisonResult
from src.benchmark.runner import get_benchmark_run, list_benchmark_runs, run_and_store_suite
from src.reports.models import ReportData
from src.reports.service import report_service
from src.feedback.models import Feedback
from src.feedback.service import feedback_service
from src.conversation.models import ConversationSession
from src.conversation.service import conversation_service

app = FastAPI(
    title="EvoResearch AE-02 API",
    description="Observable Autonomous Research MVP Phase 1 API",
    version="0.1.0"
)

try:
    _config.log_startup_config()
except Exception as _startup_log_error:  # never let a logging step block startup
    print(f"Configuration logging failed (non-fatal): {_startup_log_error}")

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

def _to_history_item(r: ResearchRun) -> ResearchHistoryItem:
    return ResearchHistoryItem(
        run_id=r.run_id,
        question=r.question,
        status=r.status,
        created_at=r.created_at,
        updated_at=r.updated_at,
        source_count=r.source_count,
        claim_count=r.claim_count,
        iteration_count=len(r.iterations),
        quality_valid=r.quality_valid,
        verification_valid=(r.verification_result or {}).get("valid"),
        report_available=r.status == RunStatus.COMPLETED,
        error=r.error,
    )

# NOTE: registered BEFORE GET /api/research/{run_id} below -- otherwise
# that single-dynamic-segment route would greedily match "history" as a
# run_id (Starlette matches routes in registration order).
@app.get("/api/research/history", response_model=List[ResearchHistoryItem])
def get_research_history():
    """Richer history list (Part G): question, status, quality,
    verification status, and report availability -- all real, straight
    from stored ResearchRun data, no mock fallback for production use."""
    return [_to_history_item(r) for r in store.list_runs()]

@app.get("/api/research/history/{run_id}", response_model=ResearchHistoryItem)
def get_research_history_item(run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")
    return _to_history_item(run)

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
        verification=run.verification_result,
        citations=run.citations,
    )

@app.get("/api/research/{run_id}/trace", response_model=List[AgentEvent])
def get_research_trace(run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    return run.trace

@app.post("/api/research/{run_id}/cancel", response_model=ResearchStatusResponse)
def cancel_research_run(run_id: str):
    """Request cancellation of an in-progress research run (Phase 10).

    Cooperative, not forceful: sets a flag on the run that ResearchLoop
    checks between iterations (see src/engine/research_loop.py) and stops at
    the next safe checkpoint -- never kills the process or an in-flight
    request. A no-op (returns current status) if the run has already
    finished; never errors for that case, only for an unknown run_id."""
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    if run.status not in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
        run.cancel_requested = True
        store.save_run(run)

    return ResearchStatusResponse(
        run_id=run.run_id,
        question=run.question,
        status=run.status,
        current_step=run.current_step,
        created_at=run.created_at,
        updated_at=run.updated_at,
        source_count=run.source_count,
        error=run.error,
    )

@app.post("/api/research/{run_id}/report", response_model=ReportData)
def generate_research_report(run_id: str):
    """Assembles the structured report for a run (Part F) -- the SAME
    ReportData the JSON GET below and the PDF endpoint both render from.
    Idempotent: report data is always derived live from the run, nothing is
    cached or regenerated by an LLM here."""
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")
    if run.status != RunStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Research run has not completed yet.")
    return report_service.get_report_data(run)

@app.get("/api/research/{run_id}/report", response_model=ReportData)
def get_research_report(run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")
    return report_service.get_report_data(run)

@app.get("/api/research/{run_id}/report/pdf")
def get_research_report_pdf(run_id: str):
    """Returns a REAL PDF (reportlab-generated from the run's actual data)
    with a real application/pdf Content-Type -- never JSON, never a text
    blob mislabeled as a PDF (see Part O)."""
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    pdf_bytes = report_service.generate_pdf_bytes(run)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="evoresearch-{run_id}.pdf"'},
    )

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

@app.get("/api/research/{run_id}/export/json")
def export_research_json(run_id: str):
    """Part H: full research data as a downloadable JSON file -- the same
    real ResearchResultResponse shape used by the UI, never fabricated,
    never including secrets (ResearchRun carries no credentials)."""
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    payload = ResearchResultResponse(
        run_id=run.run_id, question=run.question, status=run.status, answer=run.answer,
        sources=run.sources, evidence=run.evidence, security_events=run.security_events,
        completed_at=run.completed_at, claim_count=run.claim_count,
        evidence_graph_available=run.evidence_graph_available, quality_result=run.quality_result,
        quality_valid=run.quality_valid, iteration_count=len(run.iterations),
        research_decision=run.research_decision, verification=run.verification_result,
        citations=run.citations,
    )
    return Response(
        content=payload.model_dump_json(indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="evoresearch-{run_id}.json"'},
    )

@app.get("/api/research/{run_id}/share")
def share_research_run(run_id: str):
    """Part H: a sanitized, read-only public view -- question/answer/
    sources/citations/quality summary only. Never includes internal
    bookkeeping (memory_context, raw security_events, cancel flags) or
    anything credential-shaped."""
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    return {
        "run_id": run.run_id,
        "question": run.question,
        "status": run.status,
        "answer": run.answer,
        "sources": [{"title": s.title, "url": s.url, "publisher": s.publisher} for s in run.sources],
        "citations": run.citations,
        "quality_valid": run.quality_valid,
        "verification_valid": (run.verification_result or {}).get("valid"),
        "completed_at": run.completed_at,
    }

# --------------------------------------------------------------------------
# Part I - User Feedback / Answer Rating API
# --------------------------------------------------------------------------
class FeedbackRequest(BaseModel):
    helpful: Optional[bool] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = None

@app.post("/api/research/{run_id}/feedback", response_model=Feedback, status_code=status.HTTP_201_CREATED)
def submit_research_feedback(run_id: str, payload: FeedbackRequest):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")
    if payload.helpful is None and payload.rating is None and not payload.comment:
        raise HTTPException(status_code=400, detail="Provide at least one of helpful, rating, or comment.")

    feedback = feedback_service.submit(run_id, payload.helpful, payload.rating, payload.comment)
    run.trace.append(AgentEvent(
        run_id=run_id, step="Feedback", type=EventType.FEEDBACK_SUBMITTED,
        title="Feedback Submitted", message="User submitted feedback for this research run.",
        data={"helpful": payload.helpful, "rating": payload.rating},
    ))
    store.save_run(run)
    return feedback

@app.get("/api/research/{run_id}/feedback", response_model=List[Feedback])
def get_research_feedback(run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")
    return feedback_service.list_for_run(run_id)

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

# --------------------------------------------------------------------------
# Phase 8 - Safety + Policy Engine API
# --------------------------------------------------------------------------
class PolicyCheckRequest(BaseModel):
    action: str
    actor: str = "system"
    target: Optional[str] = None
    parameters: Dict[str, Any] = {}
    run_id: Optional[str] = None
    strategy_id: Optional[str] = None
    metadata: Dict[str, Any] = {}

@app.get("/api/policy/status")
def get_policy_status():
    """Current policy configuration and recent decisions. Never includes
    secrets -- only hard limits (from config) and decision metadata."""
    recent = policy_audit_log.recent(limit=20)
    return {
        "enabled": policy_rules.policy_engine_enabled(),
        "limits": policy_rules.safety_limits(),
        "allowed_evolution_fields": sorted(policy_rules.ALLOWED_EVOLUTION_FIELDS),
        "recent_decisions": [
            {
                "action": e.action, "decision": e.decision, "risk": e.risk,
                "policy_rule": e.policy_rule, "reason": e.reason, "timestamp": e.timestamp,
                "run_id": e.run_id, "strategy_id": e.strategy_id,
            }
            for e in recent
        ],
    }

@app.post("/api/policy/check", response_model=PolicyResult)
def check_policy(payload: PolicyCheckRequest):
    """Inspection/testing endpoint: evaluate one policy request and return
    the decision. Unrecognized action strings are treated as UNKNOWN (denied
    by default) rather than raising a validation error."""
    try:
        action = PolicyAction(payload.action.strip().upper())
    except ValueError:
        action = PolicyAction.UNKNOWN

    request = PolicyRequest(
        action=action, actor=payload.actor, target=payload.target,
        parameters=payload.parameters, run_id=payload.run_id,
        strategy_id=payload.strategy_id, metadata=payload.metadata,
    )
    return policy_engine.evaluate(request)

# --------------------------------------------------------------------------
# Phase 9 - Benchmarks + Improvement Tests API
# --------------------------------------------------------------------------
class BenchmarkRunRequest(BaseModel):
    strategy_id: Optional[str] = None

class BenchmarkCompareRequest(BaseModel):
    baseline_run_id: str
    candidate_run_id: str

@app.post("/api/benchmark/run")
async def start_benchmark_run(payload: BenchmarkRunRequest = BenchmarkRunRequest()):
    """Run the fixed offline benchmark suite (10 questions) against a
    strategy through the real ResearchLoop. Uses the current champion if no
    strategy_id is given. Synchronous -- offline fixtures make this fast,
    the same way /api/strategy/evolve is synchronous."""
    if payload.strategy_id:
        strategy = get_evolution_store().get(payload.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found.")
    else:
        strategy = get_evolution_store().get_champion()

    record = await run_and_store_suite(strategy)
    return {
        "benchmark_run_id": record.benchmark_run_id,
        "status": "completed",
        "strategy_id": strategy.id,
        "generation": strategy.generation,
        "suite": record.suite,
    }

@app.get("/api/benchmark/{benchmark_run_id}")
def get_benchmark_run_status(benchmark_run_id: str):
    record = get_benchmark_run(benchmark_run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Benchmark run not found.")
    return {
        "benchmark_run_id": record.benchmark_run_id,
        "status": "completed",
        "created_at": record.created_at,
        "suite": record.suite,
        "trace": record.trace,
    }

@app.get("/api/benchmark/{benchmark_run_id}/results", response_model=List[BenchmarkResult])
def get_benchmark_run_results(benchmark_run_id: str):
    record = get_benchmark_run(benchmark_run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Benchmark run not found.")
    return record.suite.results

@app.post("/api/benchmark/compare", response_model=StrategyComparisonResult)
def compare_benchmark_runs(payload: BenchmarkCompareRequest):
    baseline = get_benchmark_run(payload.baseline_run_id)
    candidate = get_benchmark_run(payload.candidate_run_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="baseline_run_id not found.")
    if not candidate:
        raise HTTPException(status_code=404, detail="candidate_run_id not found.")
    return strategy_comparator.compare(baseline.suite, candidate.suite)

@app.get("/api/benchmark/history/list")
def get_benchmark_history():
    """Every stored benchmark suite run, oldest first, labeled with the
    strategy's generation -- backed entirely by real stored results."""
    history = []
    for record in list_benchmark_runs():
        strategy = get_evolution_store().get(record.suite.strategy_id)
        history.append({
            "benchmark_run_id": record.benchmark_run_id,
            "strategy_id": record.suite.strategy_id,
            "generation": strategy.generation if strategy else None,
            "average_score": record.suite.average_score,
            "passed_count": record.suite.passed_count,
            "benchmark_count": record.suite.benchmark_count,
            "created_at": record.created_at,
        })
    return {"history": history}

# --------------------------------------------------------------------------
# Part C - Conversational Research API
# --------------------------------------------------------------------------
class ConversationCreateRequest(BaseModel):
    message: str

class ConversationMessageRequest(BaseModel):
    message: str

@app.post("/api/conversations", response_model=ConversationSession, status_code=status.HTTP_201_CREATED)
async def create_conversation(payload: ConversationCreateRequest, background_tasks: BackgroundTasks):
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    def schedule(run_id: str):
        background_tasks.add_task(orchestrator.execute_run, run_id)

    return await conversation_service.create_session(payload.message.strip(), schedule)

@app.get("/api/conversations", response_model=List[ConversationSession])
def list_conversations():
    return conversation_service.list_sessions()

@app.get("/api/conversations/{session_id}", response_model=ConversationSession)
def get_conversation(session_id: str):
    session = conversation_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Conversation session not found.")
    return session

@app.post("/api/conversations/{session_id}/messages", response_model=ConversationSession)
async def post_conversation_message(session_id: str, payload: ConversationMessageRequest, background_tasks: BackgroundTasks):
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    def schedule(run_id: str):
        background_tasks.add_task(orchestrator.execute_run, run_id)

    session, outcome = await conversation_service.add_message(session_id, payload.message.strip(), schedule)
    if session is None:
        raise HTTPException(status_code=404, detail="Conversation session not found.")
    return session

@app.delete("/api/conversations/{session_id}")
def delete_conversation(session_id: str):
    deleted = conversation_service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation session not found.")
    return {"deleted": True, "session_id": session_id}
