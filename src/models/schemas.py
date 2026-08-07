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

class EventType(str, Enum):
    STATUS_CHANGE = "status_change"
    PLANNING = "planning"
    SEARCH_EXECUTED = "search_executed"
    SECURITY_CHECK = "security_check"
    EVIDENCE_EXTRACTED = "evidence_extracted"
    REPORT_GENERATED = "report_generated"
    ERROR = "error"

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

class ResearchResultResponse(BaseModel):
    run_id: str
    question: str
    status: RunStatus
    answer: Optional[str]
    sources: List[Source]
    evidence: List[EvidenceRecord]
    security_events: List[SecurityEvent]
    completed_at: Optional[str]
