"""Final Answer Verification domain models (Part D).

Distinct from Phase 5's ResearchQualityResult: that layer checks the
research process (counts, graph linkage). This layer checks the GENERATED
ANSWER TEXT itself, after report generation, against the real claims and
sources that actually produced it.
"""

from typing import List

from pydantic import BaseModel, Field


class VerifiedClaim(BaseModel):
    claim_id: str
    claim_text: str
    status: str
    supporting_count: int
    contradicting_count: int
    source_count: int


class VerificationResult(BaseModel):
    valid: bool
    score: float
    verified_claims: List[VerifiedClaim] = Field(default_factory=list)
    unsupported_claims: List[VerifiedClaim] = Field(default_factory=list)
    contradicted_claims: List[VerifiedClaim] = Field(default_factory=list)
    citation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
