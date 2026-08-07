import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    RESEARCH_SUMMARY = "research_summary"
    FINDING = "finding"
    EVIDENCE = "evidence"
    SOURCE = "source"
    CONCLUSION = "conclusion"
    STRATEGY = "strategy"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Memory(BaseModel):
    """Canonical memory model shared across the API, MySQL and in-memory store."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: MemoryType
    content: str
    summary: str = ""
    research_run_id: Optional[str] = None
    source_ids: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


class MemorySearchResponseItem(BaseModel):
    id: str
    memory_type: str
    content: str
    summary: str = ""
    confidence: float
    importance: float
    similarity: float
    research_run_id: Optional[str] = None
    created_at: str


class MemorySearchResponse(BaseModel):
    query: str
    results: List[MemorySearchResponseItem] = Field(default_factory=list)


def utc_now() -> str:
    return _now()