"""Citation Engine domain models (Part E). Every field is copied directly
from a real Source object collected during research -- never invented."""

from typing import Dict, List

from pydantic import BaseModel, Field


class Citation(BaseModel):
    citation_id: int
    title: str
    publisher: str
    url: str
    accessed_at: str


class CitedAnswer(BaseModel):
    citations: List[Citation] = Field(default_factory=list)
    # claim_id -> citation_id(s) that support/relate to it, from the real
    # evidence graph -- never guessed.
    claim_citations: Dict[str, List[int]] = Field(default_factory=dict)
