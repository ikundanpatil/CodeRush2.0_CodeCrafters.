"""Phase 9 deterministic benchmark metrics.

Every function here takes real runtime objects (Source, Claim,
ResearchQualityResult) and expectation numbers from a BenchmarkQuestion --
never an LLM output, never a hardcoded score. All ratio metrics are clamped
to [0.0, 1.0] and guard every division by zero.
"""

from typing import List
from urllib.parse import urlparse

from src.benchmark.models import BenchmarkMetrics
from src.models.evidence import Claim, ClaimStatus
from src.models.schemas import Source
from src.quality.models import ResearchQualityResult
from src.quality.rules import is_valid_url

# quality_score weights -- documented, deterministic, must sum to 1.0.
WEIGHT_SOURCE_COVERAGE = 0.20
WEIGHT_EVIDENCE_COVERAGE = 0.20
WEIGHT_CLAIM_SUPPORT = 0.25
WEIGHT_SOURCE_DIVERSITY = 0.15
WEIGHT_RESEARCH_COMPLETENESS = 0.20


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def source_coverage(sources: List[Source], expected_min_sources: int) -> float:
    """Fraction of the expected source count met by *valid* (real http/https
    URL) sources actually collected."""
    valid_count = sum(1 for s in sources if is_valid_url(s.url))
    if expected_min_sources <= 0:
        return 1.0 if valid_count > 0 else 0.0
    return _clamp01(valid_count / expected_min_sources)


def evidence_coverage(evidence_count: int, expected_min_evidence: int) -> float:
    if expected_min_evidence <= 0:
        return 1.0 if evidence_count > 0 else 0.0
    return _clamp01(evidence_count / expected_min_evidence)


def claim_support(claims: List[Claim]) -> float:
    """supported_claims / total_claims. 0.0 (not 1.0 or NaN) when there are
    no claims at all -- an empty claim set is not "fully supported"."""
    total = len(claims)
    if total == 0:
        return 0.0
    supported = sum(1 for c in claims if c.status == ClaimStatus.SUPPORTED)
    return _clamp01(supported / total)


def source_diversity(sources: List[Source]) -> float:
    """unique source domains / total sources -- a single-domain result set
    scores low even if it has many sources."""
    if not sources:
        return 0.0
    domains = set()
    for s in sources:
        try:
            domain = urlparse(s.url).netloc.lower()
        except ValueError:
            domain = ""
        domains.add(domain)
    return _clamp01(len(domains) / len(sources))


def research_completeness(quality_result: ResearchQualityResult) -> float:
    """Fraction of the Phase 5 quality checks that passed -- a real signal
    already computed by ResearchQualityValidator, not a new invented one."""
    checks = quality_result.checks
    if not checks:
        return 0.0
    passed = sum(1 for c in checks if c.passed)
    return _clamp01(passed / len(checks))


def quality_score(metrics: BenchmarkMetrics) -> float:
    """Deterministic weighted sum. The LLM never chooses or influences this
    value -- it is a pure function of the five component metrics above."""
    score = (
        WEIGHT_SOURCE_COVERAGE * metrics.source_coverage
        + WEIGHT_EVIDENCE_COVERAGE * metrics.evidence_coverage
        + WEIGHT_CLAIM_SUPPORT * metrics.claim_support
        + WEIGHT_SOURCE_DIVERSITY * metrics.source_diversity
        + WEIGHT_RESEARCH_COMPLETENESS * metrics.research_completeness
    )
    return _clamp01(score)


def compute_metrics(
    sources: List[Source],
    evidence_count: int,
    claims: List[Claim],
    quality_result: ResearchQualityResult,
    expected_min_sources: int,
    expected_min_evidence: int,
) -> BenchmarkMetrics:
    """Compute all six metrics from real runtime objects in one place, so
    every caller (runner, tests) builds a BenchmarkMetrics the same way."""
    partial = BenchmarkMetrics(
        source_coverage=source_coverage(sources, expected_min_sources),
        evidence_coverage=evidence_coverage(evidence_count, expected_min_evidence),
        claim_support=claim_support(claims),
        source_diversity=source_diversity(sources),
        research_completeness=research_completeness(quality_result),
        quality_score=0.0,
    )
    partial.quality_score = quality_score(partial)
    return partial
