"""Report data model (Part F/H) -- the single structured assembly of a
ResearchRun that both the JSON report endpoint and the PDF generator render
from. Built once, in generator.py, so there is exactly one authoritative
path from real ResearchRun data to a rendered report (Part O)."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReportData(BaseModel):
    run_id: str
    question: str
    status: str
    generated_at: str
    research_run_created_at: str
    completed_at: Optional[str] = None

    executive_summary: str = ""
    key_findings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)

    verified_claims: List[Dict[str, Any]] = Field(default_factory=list)
    unsupported_claims: List[Dict[str, Any]] = Field(default_factory=list)
    contradicted_claims: List[Dict[str, Any]] = Field(default_factory=list)
    verification_valid: Optional[bool] = None
    verification_score: Optional[float] = None

    citations: List[Dict[str, Any]] = Field(default_factory=list)

    quality: Dict[str, Any] = Field(default_factory=dict)
    gaps: List[Dict[str, Any]] = Field(default_factory=list)
    iteration_count: int = 0
    research_decision: Optional[str] = None

    sources: List[Dict[str, Any]] = Field(default_factory=list)
