"""Phase 5 research-quality domain models.

`ResearchQualityResult` holds only counters and checks computed directly
from the runtime `Source`/`EvidenceRecord`/`Claim`/`EvidenceGraph` objects
passed into the validator -- never an invented score.
"""

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class CheckSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class QualityCheck(BaseModel):
    name: str
    passed: bool
    severity: CheckSeverity
    message: str
    actual_value: Any = None
    expected_value: Optional[Any] = None


class ResearchQualityResult(BaseModel):
    valid: bool
    source_count: int
    unique_source_count: int
    evidence_count: int
    claim_count: int
    supported_claim_count: int
    contradicted_claim_count: int
    mixed_claim_count: int
    unverified_claim_count: int
    unsupported_claim_count: int
    duplicate_source_count: int
    graph_node_count: int
    graph_edge_count: int
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    checks: List[QualityCheck] = Field(default_factory=list)
