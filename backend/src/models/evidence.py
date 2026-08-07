"""Phase 4 evidence-graph domain models.

These are separate from the flat Phase 1/2 `EvidenceRecord` in
src/models/schemas.py (one passage attached to one source, produced during
searching). Here, `Claim` and `Evidence` are graph nodes and
`EvidenceRelationship` is a typed, persisted edge between them -- built by
the Phase 4 pipeline (src/evidence/) from that same underlying research
content.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ClaimStatus(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    MIXED = "mixed"
    UNVERIFIED = "unverified"


class EvidenceType(str, Enum):
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    CONTEXTUAL = "contextual"


class RelationshipType(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    DERIVED_FROM = "DERIVED_FROM"
    RELATED_TO = "RELATED_TO"


class NodeType(str, Enum):
    CLAIM = "claim"
    EVIDENCE = "evidence"
    SOURCE = "source"


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    research_run_id: str
    claim_text: str
    normalized_claim: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    supporting_count: int = 0
    contradicting_count: int = 0
    source_count: int = 0
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    research_run_id: str
    claim_id: str
    source_id: str
    evidence_text: str
    evidence_type: EvidenceType = EvidenceType.CONTEXTUAL
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=_now)


class EvidenceRelationship(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    research_run_id: str
    from_type: NodeType
    from_id: str
    relationship_type: RelationshipType
    to_type: NodeType
    to_id: str
    created_at: str = Field(default_factory=_now)


class ClaimExtractionItem(BaseModel):
    """One claim as extracted (raw) by the LLM, before persistence."""
    claim_text: str = Field(min_length=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)


class ClaimExtractionResult(BaseModel):
    claims: list[ClaimExtractionItem] = Field(default_factory=list)


class RelationshipClassification(BaseModel):
    """LLM's classification of how one evidence passage relates to a claim."""
    relationship: RelationshipType = RelationshipType.RELATED_TO
    reasoning: str = ""
