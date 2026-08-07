"""Compute a claim's verification status from its linked evidence."""

from typing import Dict, List

from src.models.evidence import ClaimStatus, Evidence, EvidenceType


def verify_claim(evidence_items: List[Evidence]) -> Dict[str, object]:
    supporting = sum(1 for e in evidence_items if e.evidence_type == EvidenceType.SUPPORTING)
    contradicting = sum(1 for e in evidence_items if e.evidence_type == EvidenceType.CONTRADICTING)
    source_count = len({e.source_id for e in evidence_items if e.source_id})

    if supporting == 0 and contradicting == 0:
        status = ClaimStatus.UNVERIFIED
    elif supporting > 0 and contradicting > 0:
        status = ClaimStatus.MIXED
    elif contradicting > 0:
        status = ClaimStatus.CONTRADICTED
    else:
        status = ClaimStatus.SUPPORTED

    return {
        "status": status,
        "supporting_count": supporting,
        "contradicting_count": contradicting,
        "source_count": source_count,
    }
