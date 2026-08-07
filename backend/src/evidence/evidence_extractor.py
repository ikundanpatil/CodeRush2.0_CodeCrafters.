"""Link a claim to the evidence passages that support, contradict, or merely
relate to it. One Phase 4 `Evidence` graph node is created per (claim,
evidence passage) pair actually examined."""

from typing import List

from src.evidence.contradiction import classify_relationship
from src.llm.base import LLMAdapter
from src.models.evidence import Claim, Evidence, EvidenceType, RelationshipType
from src.models.schemas import EvidenceRecord

_RELATIONSHIP_TO_EVIDENCE_TYPE = {
    RelationshipType.SUPPORTS: EvidenceType.SUPPORTING,
    RelationshipType.CONTRADICTS: EvidenceType.CONTRADICTING,
    RelationshipType.RELATED_TO: EvidenceType.CONTEXTUAL,
}

MAX_EVIDENCE_PER_CLAIM = 8


async def link_evidence(
    llm: LLMAdapter, claim: Claim, evidence_records: List[EvidenceRecord]
) -> List[tuple[Evidence, RelationshipType]]:
    """Returns a list of (Evidence node, relationship-to-claim) pairs."""
    linked: List[tuple[Evidence, RelationshipType]] = []

    for record in evidence_records[:MAX_EVIDENCE_PER_CLAIM]:
        relationship, _error = await classify_relationship(llm, claim.claim_text, record.passage)
        evidence_type = _RELATIONSHIP_TO_EVIDENCE_TYPE.get(relationship, EvidenceType.CONTEXTUAL)

        evidence_node = Evidence(
            research_run_id=claim.research_run_id,
            claim_id=claim.id,
            source_id=record.source_id,
            evidence_text=record.passage,
            evidence_type=evidence_type,
            confidence=record.confidence,
        )
        linked.append((evidence_node, relationship))

    return linked
