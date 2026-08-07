"""Builds real, deterministic citations from a run's actual Source objects
and evidence graph -- reuses the existing EvidenceGraph (src/evidence/graph.py)
node/edge structure rather than re-deriving relationships, the same
traversal GET /api/evidence/graph/{id} already performs.
"""

from typing import Dict, List, Optional

from src.citations.models import Citation, CitedAnswer
from src.evidence.graph import EvidenceGraph
from src.models.evidence import Claim, RelationshipType
from src.models.schemas import Source


def build_citations(sources: List[Source]) -> List[Citation]:
    """Numbered in collection order (1-indexed) -- deterministic, and the
    only inputs are real Source fields."""
    return [
        Citation(
            citation_id=i + 1,
            title=s.title,
            publisher=s.publisher or "Unknown Publisher",
            url=s.url,
            accessed_at=s.retrieved_at,
        )
        for i, s in enumerate(sources)
    ]


def map_claims_to_citations(
    claims: List[Claim], graph: Optional[EvidenceGraph], citations: List[Citation], sources: List[Source],
) -> Dict[str, List[int]]:
    """claim_id -> sorted citation_id(s), derived purely from real graph
    edges (claim -> evidence -> DERIVED_FROM -> source)."""
    if graph is None or not graph.nodes:
        return {}

    source_id_to_citation_id = {s.id: c.citation_id for s, c in zip(sources, citations)}
    edges_from: Dict[str, list] = {}
    for edge in graph.edges:
        edges_from.setdefault(edge.from_, []).append(edge)

    result: Dict[str, List[int]] = {}
    for claim in claims:
        citation_ids = set()
        for claim_edge in edges_from.get(claim.id, []):
            if claim_edge.relationship not in (
                RelationshipType.SUPPORTS.value, RelationshipType.CONTRADICTS.value, RelationshipType.RELATED_TO.value,
            ):
                continue
            evidence_id = claim_edge.to
            for evidence_edge in edges_from.get(evidence_id, []):
                if evidence_edge.relationship != RelationshipType.DERIVED_FROM.value:
                    continue
                source_id = evidence_edge.to
                if source_id in source_id_to_citation_id:
                    citation_ids.add(source_id_to_citation_id[source_id])
        if citation_ids:
            result[claim.id] = sorted(citation_ids)
    return result


def build_cited_answer(
    claims: List[Claim], sources: List[Source], graph: Optional[EvidenceGraph],
) -> CitedAnswer:
    citations = build_citations(sources)
    claim_citations = map_claims_to_citations(claims, graph, citations, sources)
    return CitedAnswer(citations=citations, claim_citations=claim_citations)


def format_citation_block(cited: CitedAnswer, claims: List[Claim]) -> str:
    """Deterministic text block: verified claims with their real citation
    markers, then the numbered source list. Appended to the answer instead
    of asking an LLM to insert [n] markers into free prose (which risks
    misplacement/hallucination) -- see src/citations module docstring."""
    lines: List[str] = []

    supported_with_citations = [c for c in claims if cited.claim_citations.get(c.id)]
    if supported_with_citations:
        lines.append("\n**Verified Claims & Citations:**")
        for claim in supported_with_citations:
            markers = "".join(f"[{cid}]" for cid in cited.claim_citations[claim.id])
            lines.append(f"- {claim.claim_text} {markers}")

    if cited.citations:
        lines.append("\n**Sources:**")
        for citation in cited.citations:
            lines.append(f"[{citation.citation_id}] {citation.title} — {citation.publisher}")
            lines.append(f"    {citation.url}")

    return "\n".join(lines)
