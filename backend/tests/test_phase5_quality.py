from src.evidence.graph import EvidenceGraph
from src.models.evidence import Claim, ClaimStatus
from src.models.schemas import EvidenceRecord, Source
from src.quality.models import CheckSeverity
from src.quality.validator import ResearchQualityValidator


def _source(url="https://example.com/a", title="A", sid=None) -> Source:
    kwargs = {"title": title, "url": url}
    if sid:
        kwargs["id"] = sid
    return Source(**kwargs)


def _evidence(source_id: str, url="https://example.com/a") -> EvidenceRecord:
    return EvidenceRecord(
        claim="c", source_id=source_id, source_title="A", source_url=url, passage="text",
    )


def _claim(status: ClaimStatus, supporting=0, contradicting=0, source_count=0) -> Claim:
    return Claim(
        research_run_id="run1", claim_text="Some claim", status=status,
        supporting_count=supporting, contradicting_count=contradicting, source_count=source_count,
    )


def _linked_graph(claim: Claim, evidence_id: str, source_id: str, relationship="SUPPORTS") -> EvidenceGraph:
    graph = EvidenceGraph(research_run_id="run1")
    graph.add_node(claim.id, "claim", claim.claim_text)
    graph.add_node(evidence_id, "evidence", "evidence text")
    graph.add_node(source_id, "source", "source title")
    graph.add_edge(claim.id, evidence_id, relationship)
    graph.add_edge(evidence_id, source_id, "DERIVED_FROM")
    return graph


# --------------------------------------------------------------------------
# Core counting -- the most important guarantee: real counts, never invented
# --------------------------------------------------------------------------

def test_actual_source_counting_never_fabricated():
    sources = [_source("https://a.com"), _source("https://b.com")]
    result = ResearchQualityValidator().validate("q", sources, [], [], None)
    assert result.source_count == 2
    assert result.source_count != 18


def test_zero_sources_reports_zero_not_a_default():
    result = ResearchQualityValidator().validate("q", [], [], [], None)
    assert result.source_count == 0
    assert result.evidence_count == 0
    assert result.claim_count == 0
    assert result.valid is False  # below MIN_SOURCES / MIN_EVIDENCE thresholds


def test_valid_research_data_passes():
    s1 = _source("https://a.com", sid="s1")
    s2 = _source("https://b.com", sid="s2")
    s3 = _source("https://c.com", sid="s3")
    sources = [s1, s2, s3]
    evidences = [_evidence("s1", "https://a.com"), _evidence("s2", "https://b.com"), _evidence("s3", "https://c.com")]
    claim = _claim(ClaimStatus.SUPPORTED, supporting=1, source_count=1)
    graph = _linked_graph(claim, "ev1", "s1", "SUPPORTS")

    validator = ResearchQualityValidator(min_sources=3, min_evidence=3, min_supported_claims=1)
    result = validator.validate("q", sources, evidences, [claim], graph)

    assert result.valid is True
    assert result.errors == []
    assert result.source_count == 3
    assert result.supported_claim_count == 1


# --------------------------------------------------------------------------
# Source validation
# --------------------------------------------------------------------------

def test_duplicate_sources_detected():
    sources = [_source("https://a.com"), _source("https://a.com"), _source("https://b.com")]
    result = ResearchQualityValidator().validate("q", sources, [], [], None)
    assert result.duplicate_source_count == 1
    assert result.unique_source_count == 2
    assert result.source_count == 3


def test_missing_url_is_invalid():
    sources = [Source(title="No URL", url="")]
    result = ResearchQualityValidator().validate("q", sources, [], [], None)
    url_check = next(c for c in result.checks if c.name == "source_url_validity")
    assert url_check.passed is False
    assert url_check.actual_value == 1


def test_invalid_url_scheme_rejected():
    sources = [_source("ftp://example.com/file")]
    result = ResearchQualityValidator().validate("q", sources, [], [], None)
    url_check = next(c for c in result.checks if c.name == "source_url_validity")
    assert url_check.passed is False
    assert url_check.actual_value == 1


# --------------------------------------------------------------------------
# Claim / evidence validation
# --------------------------------------------------------------------------

def test_evidence_without_source_flagged_by_linkage_check():
    claim = _claim(ClaimStatus.SUPPORTED, supporting=1, source_count=1)
    graph = EvidenceGraph(research_run_id="run1")
    graph.add_node(claim.id, "claim", claim.claim_text)
    graph.add_node("ev1", "evidence", "evidence text")
    graph.add_edge(claim.id, "ev1", "SUPPORTS")
    # No DERIVED_FROM edge from ev1 to any source.

    result = ResearchQualityValidator().validate("q", [], [], [claim], graph)
    linkage_check = next(c for c in result.checks if c.name == "evidence_source_linkage")
    assert linkage_check.passed is False
    assert linkage_check.actual_value == 1


def test_claim_without_evidence():
    claim = _claim(ClaimStatus.UNVERIFIED, supporting=0, contradicting=0)
    result = ResearchQualityValidator().validate("q", [], [], [claim], None)
    assert result.unsupported_claim_count == 1
    linkage_check = next(c for c in result.checks if c.name == "claim_evidence_linkage")
    assert linkage_check.passed is False


def test_supported_claim_counted():
    claim = _claim(ClaimStatus.SUPPORTED, supporting=2, source_count=1)
    result = ResearchQualityValidator().validate("q", [], [], [claim], None)
    assert result.supported_claim_count == 1
    assert result.contradicted_claim_count == 0
    assert result.mixed_claim_count == 0
    assert result.unverified_claim_count == 0


def test_contradicted_claim_counted():
    claim = _claim(ClaimStatus.CONTRADICTED, contradicting=2, source_count=1)
    result = ResearchQualityValidator().validate("q", [], [], [claim], None)
    assert result.contradicted_claim_count == 1
    assert result.supported_claim_count == 0


def test_mixed_claim_counted():
    claim = _claim(ClaimStatus.MIXED, supporting=1, contradicting=1, source_count=2)
    result = ResearchQualityValidator().validate("q", [], [], [claim], None)
    assert result.mixed_claim_count == 1


def test_unverified_claim_counted():
    claim = _claim(ClaimStatus.UNVERIFIED)
    result = ResearchQualityValidator().validate("q", [], [], [claim], None)
    assert result.unverified_claim_count == 1
    assert result.unsupported_claim_count == 1


def test_empty_evidence_graph_flagged_when_evidence_exists():
    evidences = [_evidence("s1")]
    result = ResearchQualityValidator().validate("q", [], evidences, [], EvidenceGraph(research_run_id="run1"))
    graph_check = next(c for c in result.checks if c.name == "evidence_graph_presence")
    assert graph_check.passed is False


def test_empty_evidence_graph_ok_when_no_evidence_collected():
    result = ResearchQualityValidator().validate("q", [], [], [], EvidenceGraph(research_run_id="run1"))
    graph_check = next(c for c in result.checks if c.name == "evidence_graph_presence")
    assert graph_check.passed is True


# --------------------------------------------------------------------------
# No fabricated metrics: checks always report real actual_value/expected_value
# --------------------------------------------------------------------------

def test_checks_carry_real_actual_and_expected_values():
    sources = [_source("https://a.com")]
    result = ResearchQualityValidator(min_sources=5).validate("q", sources, [], [], None)
    source_check = next(c for c in result.checks if c.name == "source_count")
    assert source_check.actual_value == 1
    assert source_check.expected_value == 5
    assert source_check.severity == CheckSeverity.ERROR
    assert source_check.passed is False
