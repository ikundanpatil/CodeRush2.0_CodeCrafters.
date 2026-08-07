import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class RunStatus(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    SEARCHING = "searching"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class EventType(str, Enum):
    STATUS_CHANGE = "status_change"
    PLANNING = "planning"
    SEARCH_EXECUTED = "search_executed"
    SECURITY_CHECK = "security_check"
    EVIDENCE_EXTRACTED = "evidence_extracted"
    REPORT_GENERATED = "report_generated"
    ERROR = "error"

    # Phase 3 - Memory events
    MEMORY_RETRIEVAL_STARTED = "memory_retrieval_started"
    MEMORY_RETRIEVAL_COMPLETED = "memory_retrieval_completed"
    MEMORY_RETRIEVAL_FAILED = "memory_retrieval_failed"
    MEMORY_CREATED = "memory_created"
    MEMORY_UPDATED = "memory_updated"
    MEMORY_STORAGE_FAILED = "memory_storage_failed"

    # Phase 1 - LLM adapter events
    LLM_PLANNING_STARTED = "llm_planning_started"
    LLM_PLANNING_COMPLETED = "llm_planning_completed"
    LLM_PLANNING_FAILED = "llm_planning_failed"
    REPORT_GENERATION_STARTED = "report_generation_started"
    REPORT_GENERATION_COMPLETED = "report_generation_completed"
    LLM_REPORT_FAILED = "llm_report_failed"

    # Phase 2 - Search / browser events
    SEARCH_STARTED = "search_started"
    SEARCH_COMPLETED = "search_completed"
    BROWSER_FETCH_STARTED = "browser_fetch_started"
    BROWSER_FETCH_COMPLETED = "browser_fetch_completed"
    BROWSER_FETCH_FAILED = "browser_fetch_failed"
    PROMPT_INJECTION_DETECTED = "prompt_injection_detected"

    # Phase 4 - Evidence graph events
    CLAIM_EXTRACTION_STARTED = "claim_extraction_started"
    CLAIM_EXTRACTION_COMPLETED = "claim_extraction_completed"
    EVIDENCE_LINKED = "evidence_linked"
    CONTRADICTION_DETECTED = "contradiction_detected"
    VERIFICATION_COMPLETED = "verification_completed"

    # Phase 5 - Quality validation events
    QUALITY_VALIDATION_STARTED = "quality_validation_started"
    QUALITY_VALIDATION_COMPLETED = "quality_validation_completed"
    QUALITY_VALIDATION_FAILED = "quality_validation_failed"

    # Phase 5 - Sandbox execution events
    SANDBOX_EXECUTION_STARTED = "sandbox_execution_started"
    SANDBOX_EXECUTION_COMPLETED = "sandbox_execution_completed"
    SANDBOX_EXECUTION_FAILED = "sandbox_execution_failed"
    SANDBOX_TIMEOUT = "sandbox_timeout"
    SANDBOX_RESOURCE_LIMIT = "sandbox_resource_limit"

    # Phase 6 - Autonomous research loop events
    RESEARCH_ITERATION_STARTED = "research_iteration_started"
    RESEARCH_ITERATION_COMPLETED = "research_iteration_completed"
    RESEARCH_GAP_IDENTIFIED = "research_gap_identified"
    FOLLOWUP_QUERIES_GENERATED = "followup_queries_generated"
    RESEARCH_LOOP_DECISION = "research_loop_decision"
    RESEARCH_LOOP_COMPLETED = "research_loop_completed"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"

    # Phase 7 - Self-evolution events
    STRATEGY_APPLIED = "strategy_applied"
    EVOLUTION_CYCLE_STARTED = "evolution_cycle_started"
    EVOLUTION_BASELINE_EVALUATED = "evolution_baseline_evaluated"
    EVOLUTION_MUTATION_PROPOSED = "evolution_mutation_proposed"
    EVOLUTION_CANDIDATE_EVALUATED = "evolution_candidate_evaluated"
    EVOLUTION_ACCEPTED = "evolution_accepted"
    EVOLUTION_REJECTED = "evolution_rejected"
    EVOLUTION_CYCLE_COMPLETED = "evolution_cycle_completed"

    # Phase 8 - Safety + Policy Engine events
    POLICY_CHECK_STARTED = "policy_check_started"
    POLICY_ALLOWED = "policy_allowed"
    POLICY_DENIED = "policy_denied"
    POLICY_REVIEW_REQUIRED = "policy_review_required"
    EVOLUTION_POLICY_CHECKED = "evolution_policy_checked"
    EVOLUTION_POLICY_REJECTED = "evolution_policy_rejected"
    SAFETY_LIMIT_EXCEEDED = "safety_limit_exceeded"

    # Phase 9 - Benchmarks + Improvement Tests events
    BENCHMARK_STARTED = "benchmark_started"
    BENCHMARK_COMPLETED = "benchmark_completed"
    BENCHMARK_QUESTION_STARTED = "benchmark_question_started"
    BENCHMARK_QUESTION_COMPLETED = "benchmark_question_completed"
    STRATEGY_COMPARISON_STARTED = "strategy_comparison_started"
    STRATEGY_COMPARISON_COMPLETED = "strategy_comparison_completed"
    BENCHMARK_REGRESSION_DETECTED = "benchmark_regression_detected"
    BENCHMARK_IMPROVEMENT_DETECTED = "benchmark_improvement_detected"

    # Phase 10 - Voice interface / cancellation events
    RESEARCH_CANCELLED = "research_cancelled"

    # Final Completion Phase - verification, citations, PDF, conversation, feedback
    # (named FINAL_ANSWER_* to stay distinct from Phase 4's per-claim
    # VERIFICATION_COMPLETED above -- this is a separate, later-stage check
    # of the generated answer text itself, not the research process)
    FINAL_ANSWER_VERIFICATION_STARTED = "final_answer_verification_started"
    FINAL_ANSWER_VERIFICATION_COMPLETED = "final_answer_verification_completed"
    FINAL_ANSWER_VERIFICATION_ISSUES_FOUND = "final_answer_verification_issues_found"
    CITATIONS_BUILT = "citations_built"
    PDF_GENERATED = "pdf_generated"
    CONVERSATION_MESSAGE_RECEIVED = "conversation_message_received"
    CONVERSATION_INTENT_RESOLVED = "conversation_intent_resolved"
    FEEDBACK_SUBMITTED = "feedback_submitted"

class AgentEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    step: str
    type: EventType
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None

class EvidenceRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    claim: str
    source_id: str
    source_title: str
    source_url: str
    passage: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence: float = 0.95

class Source(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    url: str
    type: str = "web_page"
    publisher: str = "Unknown Publisher"
    published_at: Optional[str] = None
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    relevance: float = 0.9
    description: str = ""
    evidence: List[EvidenceRecord] = Field(default_factory=list)

class SecurityEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: str = "prompt_injection_detected"
    action_taken: str = "blocked_and_sanitized"
    snippet: str

class ResearchRun(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    status: RunStatus = RunStatus.QUEUED
    current_step: str = "Initialization"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    source_count: int = 0
    sources: List[Source] = Field(default_factory=list)
    evidence: List[EvidenceRecord] = Field(default_factory=list)
    security_events: List[SecurityEvent] = Field(default_factory=list)
    answer: Optional[str] = None
    error: Optional[str] = None
    trace: List[AgentEvent] = Field(default_factory=list)
    memory_context: List[Dict[str, Any]] = Field(default_factory=list)
    claim_count: int = 0
    evidence_graph_available: bool = False
    quality_result: Dict[str, Any] = Field(default_factory=dict)
    quality_valid: Optional[bool] = None
    iterations: List[Dict[str, Any]] = Field(default_factory=list)
    research_decision: Optional[str] = None
    cancel_requested: bool = False
    verification_result: Dict[str, Any] = Field(default_factory=dict)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    conversation_session_id: Optional[str] = None
    # Structured report components (Part F/H), kept separate from the fully
    # formatted `answer` string above so PDF/JSON export never has to
    # re-parse markdown back into sections.
    report_summary: Optional[str] = None
    report_key_findings: List[str] = Field(default_factory=list)
    report_limitations: List[str] = Field(default_factory=list)

class ResearchPlan(BaseModel):
    """Structured research plan produced by the LLM adapter."""
    objective: str = Field(min_length=1)
    sub_queries: List[str] = Field(min_length=1)
    source_types: List[str] = Field(default_factory=list)
    verify: List[str] = Field(default_factory=list)


class ResearchReportLLM(BaseModel):
    """Structured report produced by the LLM adapter.

    Deliberately has no source/URL field: real sources come from the
    orchestrator's verified evidence, never from the model, to avoid
    fabricated citations.
    """
    answer: str = Field(min_length=1)
    key_findings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class ResearchCreateRequest(BaseModel):
    question: str

class ResearchStatusResponse(BaseModel):
    run_id: str
    question: str
    status: RunStatus
    current_step: str
    created_at: str
    updated_at: str
    source_count: int
    error: Optional[str] = None

class ResearchHistoryItem(BaseModel):
    """Richer history row than ResearchStatusResponse (Part G) -- adds
    quality/verification/report-availability, all real, none fabricated."""
    run_id: str
    question: str
    status: RunStatus
    created_at: str
    updated_at: str
    source_count: int
    claim_count: int
    iteration_count: int
    quality_valid: Optional[bool] = None
    verification_valid: Optional[bool] = None
    report_available: bool = False
    error: Optional[str] = None


class ResearchResultResponse(BaseModel):
    run_id: str
    question: str
    status: RunStatus
    answer: Optional[str]
    sources: List[Source]
    evidence: List[EvidenceRecord]
    security_events: List[SecurityEvent]
    completed_at: Optional[str]
    claim_count: int = 0
    evidence_graph_available: bool = False
    quality_result: Dict[str, Any] = Field(default_factory=dict)
    quality_valid: Optional[bool] = None
    iteration_count: int = 0
    research_decision: Optional[str] = None
    verification: Dict[str, Any] = Field(default_factory=dict)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
