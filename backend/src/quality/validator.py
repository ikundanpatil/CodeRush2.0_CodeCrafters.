"""Research quality validation: runs after the Phase 4 evidence graph is
built and before the report is generated, and checks the *actual* research
output collected so far -- never invents a count, score, or confidence
value. All fields on ResearchQualityResult are computed directly from the
Source/EvidenceRecord/Claim/EvidenceGraph objects passed in.

Never blocks the pipeline: for Phase 5 the orchestrator records the result
(valid/warnings/errors) and continues to report generation regardless. The
autonomous retry loop that acts on `valid == False` is Phase 6.
"""

from typing import List, Optional

from src.evidence.graph import EvidenceGraph
from src.models.evidence import Claim, ClaimStatus
from src.models.schemas import EvidenceRecord, Source
from src.quality import rules
from src.quality.models import CheckSeverity, QualityCheck, ResearchQualityResult


class ResearchQualityValidator:
    def __init__(
        self,
        min_sources: Optional[int] = None,
        min_evidence: Optional[int] = None,
        min_supported_claims: Optional[int] = None,
    ):
        self.min_sources = min_sources if min_sources is not None else rules.min_sources()
        self.min_evidence = min_evidence if min_evidence is not None else rules.min_evidence()
        self.min_supported_claims = (
            min_supported_claims if min_supported_claims is not None else rules.min_supported_claims()
        )

    def validate(
        self,
        question: str,
        sources: List[Source],
        evidences: List[EvidenceRecord],
        claims: List[Claim],
        graph: Optional[EvidenceGraph] = None,
    ) -> ResearchQualityResult:
        source_count = len(sources)
        unique_sources = rules.unique_source_count(sources)
        duplicate_sources = rules.duplicate_source_count(sources)
        evidence_count = len(evidences)
        claim_count = len(claims)

        supported_count = sum(1 for c in claims if c.status == ClaimStatus.SUPPORTED)
        contradicted_count = sum(1 for c in claims if c.status == ClaimStatus.CONTRADICTED)
        mixed_count = sum(1 for c in claims if c.status == ClaimStatus.MIXED)
        unverified_count = sum(1 for c in claims if c.status == ClaimStatus.UNVERIFIED)
        unsupported_count = sum(
            1 for c in claims if c.supporting_count == 0 and c.contradicting_count == 0
        )

        graph_node_count = len(graph.nodes) if graph else 0
        graph_edge_count = len(graph.edges) if graph else 0

        checks: List[QualityCheck] = [
            rules.check_source_count(source_count, self.min_sources),
            rules.check_evidence_count(evidence_count, self.min_evidence),
            rules.check_claim_count(claim_count),
            rules.check_source_url_validity(sources),
            rules.check_duplicate_sources(duplicate_sources),
            rules.check_evidence_source_linkage(graph),
            rules.check_claim_evidence_linkage(graph, claims),
            rules.check_claims_without_evidence(unsupported_count, claim_count),
            rules.check_supported_claims(supported_count, claim_count, self.min_supported_claims),
            rules.check_evidence_graph_presence(graph, evidence_count),
        ]

        errors = [c.message for c in checks if not c.passed and c.severity == CheckSeverity.ERROR]
        warnings = [c.message for c in checks if not c.passed and c.severity == CheckSeverity.WARNING]

        return ResearchQualityResult(
            valid=len(errors) == 0,
            source_count=source_count,
            unique_source_count=unique_sources,
            evidence_count=evidence_count,
            claim_count=claim_count,
            supported_claim_count=supported_count,
            contradicted_claim_count=contradicted_count,
            mixed_claim_count=mixed_count,
            unverified_claim_count=unverified_count,
            unsupported_claim_count=unsupported_count,
            duplicate_source_count=duplicate_sources,
            graph_node_count=graph_node_count,
            graph_edge_count=graph_edge_count,
            warnings=warnings,
            errors=errors,
            checks=checks,
        )


research_quality_validator = ResearchQualityValidator()
