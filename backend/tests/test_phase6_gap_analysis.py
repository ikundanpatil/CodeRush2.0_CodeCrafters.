from src.engine.research_gap import GapPriority, GapType, analyze_gaps, classify_source
from src.evidence.graph import EvidenceGraph
from src.models.evidence import Claim, ClaimStatus
from src.models.schemas import EvidenceRecord, Source
from src.quality.validator import ResearchQualityValidator


def _claim(status: ClaimStatus, supporting=0, contradicting=0, importance=0.9) -> Claim:
    return Claim(
        research_run_id="run1", claim_text="Some claim", status=status,
        supporting_count=supporting, contradicting_count=contradicting, importance=importance,
    )


def _source(url: str) -> Source:
    return Source(title="T", url=url)


VALIDATOR = ResearchQualityValidator(min_sources=3, min_evidence=3, min_supported_claims=1)


# --------------------------------------------------------------------------
# classify_source
# --------------------------------------------------------------------------

def test_classify_source_academic():
    assert classify_source("https://arxiv.org/abs/1234") == "academic"
    assert classify_source("https://foo.edu/paper") == "academic"


def test_classify_source_government():
    assert classify_source("https://www.nist.gov/report") == "government"


def test_classify_source_repository():
    assert classify_source("https://github.com/org/repo") == "repository"


def test_classify_source_news():
    assert classify_source("https://www.reuters.com/article") == "news"


def test_classify_source_other_for_unknown_or_missing():
    assert classify_source("https://random-blog.example.com/post") == "other"
    assert classify_source("") == "other"
    assert classify_source(None) == "other"


# --------------------------------------------------------------------------
# analyze_gaps -- source/evidence/claim count gaps
# --------------------------------------------------------------------------

def test_insufficient_sources_gap():
    quality = VALIDATOR.validate("q", [_source("https://a.com")], [], [], None)
    gaps = analyze_gaps(quality, [], [_source("https://a.com")])
    assert any(g.type == GapType.INSUFFICIENT_SOURCES for g in gaps)


def test_insufficient_evidence_gap():
    sources = [_source(f"https://{c}.com") for c in "abc"]
    quality = VALIDATOR.validate("q", sources, [], [], None)
    gaps = analyze_gaps(quality, [], sources)
    assert any(g.type == GapType.INSUFFICIENT_EVIDENCE for g in gaps)


def test_unsupported_claims_gap_for_zero_evidence_claim():
    claim = _claim(ClaimStatus.UNVERIFIED, supporting=0, contradicting=0)
    quality = VALIDATOR.validate("q", [], [], [claim], None)
    gaps = analyze_gaps(quality, [claim], [])
    gap = next(g for g in gaps if g.type == GapType.UNSUPPORTED_CLAIMS)
    assert claim.id in gap.related_claim_ids
    assert gap.priority == GapPriority.HIGH  # also fails the supported-claims threshold


def test_unsupported_claims_gap_for_mixed_claim_below_threshold():
    # A MIXED claim has evidence (so it's not "zero evidence"), but it still
    # isn't a fully SUPPORTED claim -- this must not be silently invisible to
    # gap analysis, or the research loop would stop improving forever.
    claim = _claim(ClaimStatus.MIXED, supporting=1, contradicting=1)
    quality = VALIDATOR.validate("q", [], [], [claim], None)
    assert quality.valid is False
    gaps = analyze_gaps(quality, [claim], [])
    gap = next(g for g in gaps if g.type == GapType.UNSUPPORTED_CLAIMS)
    assert claim.id in gap.related_claim_ids


def test_unverified_claims_gap():
    claim = _claim(ClaimStatus.UNVERIFIED)
    quality = VALIDATOR.validate("q", [], [], [claim], None)
    gaps = analyze_gaps(quality, [claim], [])
    assert any(g.type == GapType.UNVERIFIED_CLAIMS and claim.id in g.related_claim_ids for g in gaps)


def test_duplicate_sources_gap():
    sources = [_source("https://a.com"), _source("https://a.com")]
    quality = VALIDATOR.validate("q", sources, [], [], None)
    gaps = analyze_gaps(quality, [], sources)
    assert any(g.type == GapType.DUPLICATE_SOURCES for g in gaps)


# --------------------------------------------------------------------------
# Contradiction-aware research
# --------------------------------------------------------------------------

def test_missing_contradiction_check_gap_for_significant_one_sided_claim():
    claim = _claim(ClaimStatus.SUPPORTED, supporting=3, contradicting=0, importance=0.9)
    quality = VALIDATOR.validate("q", [], [], [claim], None)
    gaps = analyze_gaps(quality, [claim], [])
    assert any(g.type == GapType.MISSING_CONTRADICTION_CHECK and claim.id in g.related_claim_ids for g in gaps)


def test_missing_contradiction_check_not_triggered_for_low_importance_claim():
    # Not every topic needs an opposing viewpoint -- a claim with low
    # importance and thin support shouldn't force a contradiction search.
    claim = _claim(ClaimStatus.SUPPORTED, supporting=1, contradicting=0, importance=0.2)
    quality = VALIDATOR.validate("q", [], [], [claim], None)
    gaps = analyze_gaps(quality, [claim], [])
    assert not any(g.type == GapType.MISSING_CONTRADICTION_CHECK for g in gaps)


def test_missing_contradiction_check_not_triggered_when_contradiction_exists():
    claim = _claim(ClaimStatus.MIXED, supporting=3, contradicting=1, importance=0.9)
    quality = VALIDATOR.validate("q", [], [], [claim], None)
    gaps = analyze_gaps(quality, [claim], [])
    assert not any(g.type == GapType.MISSING_CONTRADICTION_CHECK for g in gaps)


# --------------------------------------------------------------------------
# Source diversity
# --------------------------------------------------------------------------

def test_source_diversity_gap_detected_when_skewed():
    sources = [_source(f"https://news{n}.reuters.com/x") for n in range(4)] + [_source("https://arxiv.org/abs/1")]
    quality = VALIDATOR.validate("q", sources, [], [], None)
    gaps = analyze_gaps(quality, [], sources)
    gap = next(g for g in gaps if g.type == GapType.SOURCE_DIVERSITY)
    assert "news" in gap.description


def test_source_diversity_not_triggered_when_diverse():
    sources = [
        _source("https://arxiv.org/abs/1"),
        _source("https://www.nist.gov/report"),
        _source("https://github.com/org/repo"),
        _source("https://www.reuters.com/article"),
    ]
    quality = VALIDATOR.validate("q", sources, [], [], None)
    gaps = analyze_gaps(quality, [], sources)
    assert not any(g.type == GapType.SOURCE_DIVERSITY for g in gaps)


def test_source_diversity_not_triggered_below_minimum_sample_size():
    # 2 sources of the same category on a niche topic is normal, not a gap.
    sources = [_source("https://arxiv.org/abs/1"), _source("https://arxiv.org/abs/2")]
    quality = VALIDATOR.validate("q", sources, [], [], None)
    gaps = analyze_gaps(quality, [], sources)
    assert not any(g.type == GapType.SOURCE_DIVERSITY for g in gaps)


# --------------------------------------------------------------------------
# Ordering, and the "no gaps when everything is fine" case
# --------------------------------------------------------------------------

def test_gaps_sorted_high_priority_first():
    sources = [_source("https://a.com")]  # triggers a HIGH gap
    dup_sources = sources + [_source("https://a.com")]  # also a LOW gap
    quality = VALIDATOR.validate("q", dup_sources, [], [], None)
    gaps = analyze_gaps(quality, [], dup_sources)
    priorities = [g.priority for g in gaps]
    order = {GapPriority.HIGH: 0, GapPriority.MEDIUM: 1, GapPriority.LOW: 2}
    assert priorities == sorted(priorities, key=lambda p: order[p])


def test_no_gaps_when_research_is_fully_sufficient():
    sources = [_source(f"https://{c}.com") for c in "abc"]
    evidences = [
        EvidenceRecord(claim="c", source_id="s", source_title="T", source_url="https://a.com", passage="p")
        for _ in range(3)
    ]
    claim = _claim(ClaimStatus.SUPPORTED, supporting=1, contradicting=0, importance=0.9)

    graph = EvidenceGraph(research_run_id="run1")
    graph.add_node(claim.id, "claim", claim.claim_text)
    graph.add_node("ev1", "evidence", "evidence text")
    graph.add_node("s1", "source", "source title")
    graph.add_edge(claim.id, "ev1", "SUPPORTS")
    graph.add_edge("ev1", "s1", "DERIVED_FROM")

    quality = VALIDATOR.validate("q", sources, evidences, [claim], graph)
    assert quality.valid is True
    gaps = analyze_gaps(quality, [claim], sources)
    # Even when valid, informational gaps (e.g. missing-contradiction) may
    # still legitimately fire -- but none of the blocking/threshold gaps should.
    blocking_types = {GapType.INSUFFICIENT_SOURCES, GapType.INSUFFICIENT_EVIDENCE, GapType.UNSUPPORTED_CLAIMS}
    assert not any(g.type in blocking_types for g in gaps)
