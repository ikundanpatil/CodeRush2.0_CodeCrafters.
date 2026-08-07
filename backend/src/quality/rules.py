"""Pure, individually-testable quality checks used by ResearchQualityValidator.

Every function here operates only on the runtime objects it is given --
sources, evidence records, claims, and the evidence graph -- and never
invents a count or fabricates a metric. Thresholds are configurable through
environment variables so operators can tune "enough evidence" without a
code change.
"""

import os
from typing import List, Optional
from urllib.parse import urlparse

from src.evidence.graph import EvidenceGraph
from src.models.evidence import Claim
from src.models.schemas import EvidenceRecord, Source
from src.quality.models import CheckSeverity, QualityCheck

DEFAULT_MIN_SOURCES = 3
DEFAULT_MIN_EVIDENCE = 3
DEFAULT_MIN_SUPPORTED_CLAIMS = 1


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def min_sources() -> int:
    return _env_int("MIN_SOURCES", DEFAULT_MIN_SOURCES)


def min_evidence() -> int:
    return _env_int("MIN_EVIDENCE", DEFAULT_MIN_EVIDENCE)


def min_supported_claims() -> int:
    return _env_int("MIN_SUPPORTED_CLAIMS", DEFAULT_MIN_SUPPORTED_CLAIMS)


# -- pure metric helpers -----------------------------------------------------

def is_valid_url(url: Optional[str]) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _normalized_url(source: Source) -> str:
    return (source.url or "").strip().lower()


def unique_source_count(sources: List[Source]) -> int:
    return len({_normalized_url(s) for s in sources if s.url})


def duplicate_source_count(sources: List[Source]) -> int:
    seen = set()
    duplicates = 0
    for source in sources:
        key = _normalized_url(source)
        if not key:
            continue
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return duplicates


def invalid_url_sources(sources: List[Source]) -> List[Source]:
    return [s for s in sources if not is_valid_url(s.url)]


# -- checks -------------------------------------------------------------------

def check_source_count(source_count: int, threshold: int) -> QualityCheck:
    return QualityCheck(
        name="source_count",
        passed=source_count >= threshold,
        severity=CheckSeverity.ERROR,
        message=f"Collected {source_count} source(s); minimum required is {threshold}.",
        actual_value=source_count,
        expected_value=threshold,
    )


def check_evidence_count(evidence_count: int, threshold: int) -> QualityCheck:
    return QualityCheck(
        name="evidence_count",
        passed=evidence_count >= threshold,
        severity=CheckSeverity.ERROR,
        message=f"Collected {evidence_count} evidence passage(s); minimum required is {threshold}.",
        actual_value=evidence_count,
        expected_value=threshold,
    )


def check_claim_count(claim_count: int) -> QualityCheck:
    return QualityCheck(
        name="claim_count",
        passed=claim_count > 0,
        severity=CheckSeverity.WARNING,
        message=(
            f"{claim_count} claim(s) were extracted." if claim_count > 0
            else "No claims were extracted from the collected evidence."
        ),
        actual_value=claim_count,
        expected_value=1,
    )


def check_source_url_validity(sources: List[Source]) -> QualityCheck:
    invalid = invalid_url_sources(sources)
    return QualityCheck(
        name="source_url_validity",
        passed=len(invalid) == 0,
        severity=CheckSeverity.ERROR,
        message=(
            "All source URLs are valid http/https URLs." if not invalid
            else f"{len(invalid)} source(s) have a missing or invalid (non-http/https) URL."
        ),
        actual_value=len(invalid),
        expected_value=0,
    )


def check_duplicate_sources(duplicate_count: int) -> QualityCheck:
    return QualityCheck(
        name="duplicate_sources",
        passed=duplicate_count == 0,
        severity=CheckSeverity.WARNING,
        message=(
            "No duplicate source URLs detected." if duplicate_count == 0
            else f"{duplicate_count} duplicate source URL(s) detected."
        ),
        actual_value=duplicate_count,
        expected_value=0,
    )


def check_evidence_source_linkage(graph: Optional[EvidenceGraph]) -> QualityCheck:
    """Every evidence node in the graph must be DERIVED_FROM a source node."""
    if graph is None or not graph.nodes:
        return QualityCheck(
            name="evidence_source_linkage",
            passed=True,
            severity=CheckSeverity.INFO,
            message="No evidence graph available to check evidence-to-source linkage.",
            actual_value=0,
            expected_value=0,
        )
    evidence_ids = {n.id for n in graph.nodes if n.type == "evidence"}
    linked_ids = {e.from_ for e in graph.edges if e.relationship == "DERIVED_FROM"}
    unlinked = evidence_ids - linked_ids
    return QualityCheck(
        name="evidence_source_linkage",
        passed=len(unlinked) == 0,
        severity=CheckSeverity.ERROR,
        message=(
            "All evidence nodes are linked to a source." if not unlinked
            else f"{len(unlinked)} evidence node(s) are not linked to any source."
        ),
        actual_value=len(unlinked),
        expected_value=0,
    )


def check_claim_evidence_linkage(graph: Optional[EvidenceGraph], claims: List[Claim]) -> QualityCheck:
    """Every claim node in the graph must have at least one outgoing edge to evidence."""
    if not claims:
        return QualityCheck(
            name="claim_evidence_linkage",
            passed=True,
            severity=CheckSeverity.INFO,
            message="No claims were extracted; nothing to link.",
            actual_value=0,
            expected_value=0,
        )
    linked_claim_ids = {
        e.from_ for e in (graph.edges if graph else [])
        if e.relationship in ("SUPPORTS", "CONTRADICTS", "RELATED_TO")
    }
    unlinked_claims = [c for c in claims if c.id not in linked_claim_ids]
    return QualityCheck(
        name="claim_evidence_linkage",
        passed=len(unlinked_claims) == 0,
        severity=CheckSeverity.ERROR,
        message=(
            "All claims are linked to evidence in the graph." if not unlinked_claims
            else f"{len(unlinked_claims)} claim(s) have no linked evidence in the graph."
        ),
        actual_value=len(unlinked_claims),
        expected_value=0,
    )


def check_claims_without_evidence(unsupported_count: int, claim_count: int) -> QualityCheck:
    return QualityCheck(
        name="claims_without_evidence",
        passed=unsupported_count == 0,
        severity=CheckSeverity.WARNING,
        message=(
            "Every claim has at least one supporting or contradicting evidence link."
            if unsupported_count == 0
            else f"{unsupported_count} of {claim_count} claim(s) have no supporting or contradicting evidence."
        ),
        actual_value=unsupported_count,
        expected_value=0,
    )


def check_supported_claims(supported_count: int, claim_count: int, threshold: int) -> QualityCheck:
    severity = CheckSeverity.ERROR if claim_count > 0 else CheckSeverity.WARNING
    return QualityCheck(
        name="supported_claims",
        passed=supported_count >= threshold,
        severity=severity,
        message=f"{supported_count} claim(s) are fully supported by evidence; minimum required is {threshold}.",
        actual_value=supported_count,
        expected_value=threshold,
    )


def check_evidence_graph_presence(graph: Optional[EvidenceGraph], evidence_count: int) -> QualityCheck:
    node_count = len(graph.nodes) if graph else 0
    edge_count = len(graph.edges) if graph else 0
    passed = evidence_count == 0 or (node_count > 0 and edge_count > 0)
    return QualityCheck(
        name="evidence_graph_presence",
        passed=passed,
        severity=CheckSeverity.WARNING,
        message=(
            f"Evidence graph has {node_count} node(s) and {edge_count} edge(s)." if passed
            else "Evidence was collected but no evidence graph was built."
        ),
        actual_value={"nodes": node_count, "edges": edge_count},
        expected_value=None,
    )
