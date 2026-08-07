"""Orchestrates the Phase 4 evidence-graph pipeline for one research run:

    claims = extract_claims(evidence)
    for each claim:
        linked = link_evidence(claim, evidence)      # SUPPORTS / CONTRADICTS / RELATED_TO
        status = verify_claim(linked)                # supported / contradicted / mixed / unverified
    persist everything, build node/edge graph for the API

Does not touch Phase 3 memory. Never fabricates a claim or relationship that
isn't grounded in the run's actual (already sanitized) evidence.
"""

from typing import Callable, List, Optional, Tuple

from src.evidence.claim_extractor import extract_claims
from src.evidence.evidence_extractor import link_evidence
from src.evidence.graph import EvidenceGraph
from src.evidence.store import EvidenceStore, get_evidence_store
from src.evidence.verifier import verify_claim
from src.llm.base import LLMAdapter
from src.models.evidence import Claim, EvidenceRelationship, NodeType, RelationshipType
from src.models.schemas import EvidenceRecord, Source

EventSink = Callable[[str, str, str, Optional[dict]], None]


def _noop_sink(event_type: str, title: str, message: str, data=None):
    pass


async def build_evidence_graph(
    llm: LLMAdapter,
    research_run_id: str,
    question: str,
    evidences: List[EvidenceRecord],
    sources: List[Source],
    store: Optional[EvidenceStore] = None,
    event_sink: EventSink = _noop_sink,
) -> Tuple[EvidenceGraph, List[Claim]]:
    store = store or get_evidence_store()
    graph = EvidenceGraph(research_run_id=research_run_id)
    source_by_id = {s.id: s for s in sources}

    event_sink(
        "claim_extraction_started", "Claim Extraction Started",
        f"Extracting factual claims from {len(evidences)} evidence passages.",
    )
    claims, extract_error = await extract_claims(llm, research_run_id, question, evidences)
    if extract_error is not None:
        event_sink(
            "claim_extraction_started", "Claim Extraction Degraded",
            f"Claim extraction failed; continuing without an evidence graph for this run: {extract_error}",
            {"error": str(extract_error)},
        )
        return graph, []

    event_sink(
        "claim_extraction_completed", "Claim Extraction Completed",
        f"Extracted {len(claims)} candidate claim(s).",
        {"claim_count": len(claims)},
    )

    verified_claims: List[Claim] = []

    for claim in claims:
        graph.add_node(claim.id, "claim", claim.claim_text)
        store.save_claim(claim)

        linked = await link_evidence(llm, claim, evidences)

        for evidence_node, relationship in linked:
            store.save_evidence(evidence_node)

            source = source_by_id.get(evidence_node.source_id)
            source_label = source.title if source else evidence_node.source_id

            graph.add_node(evidence_node.id, "evidence", evidence_node.evidence_text[:120])
            if evidence_node.source_id:
                graph.add_node(evidence_node.source_id, "source", source_label)

            store.save_relationship(_relationship(
                research_run_id, NodeType.CLAIM, claim.id, relationship, NodeType.EVIDENCE, evidence_node.id,
            ))
            event_sink(
                "evidence_linked", "Evidence Linked",
                f"Linked evidence to claim '{claim.claim_text[:60]}' as {relationship.value}.",
                {"claim_id": claim.id, "evidence_id": evidence_node.id, "relationship": relationship.value},
            )
            if relationship == RelationshipType.CONTRADICTS:
                event_sink(
                    "contradiction_detected", "Contradiction Detected",
                    f"Evidence contradicts claim '{claim.claim_text[:60]}'.",
                    {"claim_id": claim.id, "evidence_id": evidence_node.id},
                )

            if evidence_node.source_id:
                graph.add_edge(evidence_node.id, evidence_node.source_id, RelationshipType.DERIVED_FROM.value)
                store.save_relationship(_relationship(
                    research_run_id, NodeType.EVIDENCE, evidence_node.id,
                    RelationshipType.DERIVED_FROM, NodeType.SOURCE, evidence_node.source_id,
                ))

            graph.add_edge(claim.id, evidence_node.id, relationship.value)

        verification = verify_claim([e for e, _ in linked])
        claim.status = verification["status"]
        claim.supporting_count = verification["supporting_count"]
        claim.contradicting_count = verification["contradicting_count"]
        claim.source_count = verification["source_count"]
        store.save_claim(claim)
        verified_claims.append(claim)

        event_sink(
            "verification_completed", "Claim Verification Completed",
            f"Claim '{claim.claim_text[:60]}' verified as {claim.status.value} "
            f"({claim.supporting_count} supporting, {claim.contradicting_count} contradicting).",
            {
                "claim_id": claim.id,
                "status": claim.status.value,
                "supporting_count": claim.supporting_count,
                "contradicting_count": claim.contradicting_count,
                "source_count": claim.source_count,
            },
        )

    return graph, verified_claims


def _relationship(research_run_id, from_type, from_id, relationship_type, to_type, to_id) -> EvidenceRelationship:
    return EvidenceRelationship(
        research_run_id=research_run_id,
        from_type=from_type,
        from_id=from_id,
        relationship_type=relationship_type,
        to_type=to_type,
        to_id=to_id,
    )
