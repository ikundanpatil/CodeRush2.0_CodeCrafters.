"""Phase 6 research-gap analysis.

Looks at the *actual* runtime `ResearchQualityResult` (Phase 5, reused
unchanged) plus the current claims/sources to explain WHY research quality
is insufficient, in a form the research loop can turn into targeted
follow-up queries. Purely deterministic/heuristic -- no LLM call here, so
gap detection itself can never hallucinate a reason that isn't grounded in
real data.
"""

from collections import Counter
from enum import Enum
from typing import List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from src.models.evidence import Claim, ClaimStatus
from src.models.schemas import Source
from src.quality import rules
from src.quality.models import ResearchQualityResult

# A claim is "significant" enough to warrant an explicit search for opposing
# evidence only when it's both well-supported and important -- not every
# claim on every topic needs a devil's advocate.
CONTRADICTION_CHECK_MIN_SUPPORTING = 2
CONTRADICTION_CHECK_MIN_IMPORTANCE = 0.6

# Only flag a single-category skew once there's a meaningful sample size,
# so 2 sources of the same type on a niche topic isn't treated as a gap.
SOURCE_DIVERSITY_MIN_SOURCES = 4
SOURCE_DIVERSITY_DOMINANT_FRACTION = 0.8

_ACADEMIC_MARKERS = (
    ".edu", "arxiv.org", "scholar.google", "ncbi.nlm.nih.gov", "springer",
    "sciencedirect", "ieee.org", "acm.org", "researchgate.net", "nature.com",
    "jstor.org", "pubmed",
)
_GOVERNMENT_MARKERS = (".gov", ".mil")
_REPOSITORY_MARKERS = ("github.com", "gitlab.com", "bitbucket.org", "npmjs.com", "pypi.org")
_TECHNICAL_MARKERS = (
    "stackoverflow.com", "stackexchange.com", "docs.", "readthedocs.io",
    "developer.", "dev.to", "medium.com",
)
_NEWS_MARKERS = (
    "news", "times", "post", "reuters", "bloomberg", "techcrunch", "theverge",
    "wired.com", "forbes.com", "bbc.", "cnn.", "nytimes",
)


class GapType(str, Enum):
    INSUFFICIENT_SOURCES = "insufficient_sources"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNSUPPORTED_CLAIMS = "unsupported_claims"
    UNVERIFIED_CLAIMS = "unverified_claims"
    MISSING_CONTRADICTION_CHECK = "missing_contradiction_check"
    DUPLICATE_SOURCES = "duplicate_sources"
    SOURCE_DIVERSITY = "source_diversity"


class GapPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResearchGap(BaseModel):
    type: GapType
    description: str
    priority: GapPriority
    related_claim_ids: List[str] = Field(default_factory=list)


def classify_source(url: Optional[str]) -> str:
    """Best-effort source category from the URL only -- deterministic, no
    network calls, no fabricated classification when the URL is unusable."""
    if not url:
        return "other"
    try:
        host = (urlparse(url).netloc or "").lower()
    except ValueError:
        return "other"
    if not host:
        return "other"

    if any(marker in host for marker in _GOVERNMENT_MARKERS):
        return "government"
    if any(marker in host for marker in _ACADEMIC_MARKERS):
        return "academic"
    if any(marker in host for marker in _REPOSITORY_MARKERS):
        return "repository"
    if any(marker in host for marker in _TECHNICAL_MARKERS):
        return "technical"
    if any(marker in host for marker in _NEWS_MARKERS):
        return "news"
    return "other"


def analyze_gaps(
    quality_result: ResearchQualityResult,
    claims: List[Claim],
    sources: List[Source],
) -> List[ResearchGap]:
    gaps: List[ResearchGap] = []

    if quality_result.source_count < rules.min_sources():
        gaps.append(ResearchGap(
            type=GapType.INSUFFICIENT_SOURCES,
            description=(
                f"Only {quality_result.source_count} source(s) collected; "
                f"at least {rules.min_sources()} are needed."
            ),
            priority=GapPriority.HIGH,
        ))

    if quality_result.evidence_count < rules.min_evidence():
        gaps.append(ResearchGap(
            type=GapType.INSUFFICIENT_EVIDENCE,
            description=(
                f"Only {quality_result.evidence_count} evidence passage(s) collected; "
                f"at least {rules.min_evidence()} are needed."
            ),
            priority=GapPriority.HIGH,
        ))

    # UNSUPPORTED_CLAIMS covers two related conditions the Phase 5 validator
    # can flag: claims with literally no evidence, and (more commonly, e.g. a
    # claim that ends up "mixed" rather than cleanly "supported") too few
    # claims reaching a fully SUPPORTED status to satisfy MIN_SUPPORTED_CLAIMS.
    zero_evidence_ids = [c.id for c in claims if c.supporting_count == 0 and c.contradicting_count == 0]
    insufficient_supported = quality_result.supported_claim_count < rules.min_supported_claims()
    if zero_evidence_ids or insufficient_supported:
        description_parts = []
        related_ids = set(zero_evidence_ids)
        if zero_evidence_ids:
            description_parts.append(f"{len(zero_evidence_ids)} claim(s) have no supporting or contradicting evidence")
        if insufficient_supported:
            description_parts.append(
                f"only {quality_result.supported_claim_count} claim(s) are fully supported by evidence "
                f"(minimum {rules.min_supported_claims()} required)"
            )
            related_ids |= {c.id for c in claims if c.status != ClaimStatus.SUPPORTED}
        gaps.append(ResearchGap(
            type=GapType.UNSUPPORTED_CLAIMS,
            description="; ".join(description_parts).capitalize() + ".",
            priority=GapPriority.HIGH if insufficient_supported else GapPriority.MEDIUM,
            related_claim_ids=sorted(related_ids),
        ))

    unverified_ids = [c.id for c in claims if c.status == ClaimStatus.UNVERIFIED]
    if unverified_ids:
        gaps.append(ResearchGap(
            type=GapType.UNVERIFIED_CLAIMS,
            description=f"{len(unverified_ids)} claim(s) remain unverified.",
            priority=GapPriority.MEDIUM,
            related_claim_ids=unverified_ids,
        ))

    if quality_result.duplicate_source_count > 0:
        gaps.append(ResearchGap(
            type=GapType.DUPLICATE_SOURCES,
            description=f"{quality_result.duplicate_source_count} duplicate source URL(s) detected.",
            priority=GapPriority.LOW,
        ))

    significant_one_sided = [
        c for c in claims
        if c.status == ClaimStatus.SUPPORTED
        and c.supporting_count >= CONTRADICTION_CHECK_MIN_SUPPORTING
        and c.contradicting_count == 0
        and c.importance >= CONTRADICTION_CHECK_MIN_IMPORTANCE
    ]
    if significant_one_sided:
        gaps.append(ResearchGap(
            type=GapType.MISSING_CONTRADICTION_CHECK,
            description=(
                f"{len(significant_one_sided)} important claim(s) are well-supported but no "
                f"contradicting evidence was sought; an opposing viewpoint may materially "
                f"improve completeness."
            ),
            priority=GapPriority.MEDIUM,
            related_claim_ids=[c.id for c in significant_one_sided],
        ))

    if len(sources) >= SOURCE_DIVERSITY_MIN_SOURCES:
        categories = Counter(classify_source(s.url) for s in sources)
        dominant_category, dominant_count = categories.most_common(1)[0]
        fraction = dominant_count / len(sources)
        if fraction >= SOURCE_DIVERSITY_DOMINANT_FRACTION:
            gaps.append(ResearchGap(
                type=GapType.SOURCE_DIVERSITY,
                description=(
                    f"{dominant_count} of {len(sources)} sources ({fraction:.0%}) are '{dominant_category}'; "
                    f"research may be overly dependent on one source type."
                ),
                priority=GapPriority.LOW,
            ))

    priority_order = {GapPriority.HIGH: 0, GapPriority.MEDIUM: 1, GapPriority.LOW: 2}
    gaps.sort(key=lambda g: priority_order[g.priority])
    return gaps
