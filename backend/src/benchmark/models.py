"""Phase 9 benchmark domain models.

Every numeric field here is meant to be computed from real runtime objects
(Source, EvidenceRecord, Claim, EvidenceGraph, ResearchQualityResult) by
src/benchmark/metrics.py and src/benchmark/runner.py -- nothing in this file
computes anything itself, it only describes shapes.
"""

from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _uuid() -> str:
    return str(uuid4())


class BenchmarkQuestion(BaseModel):
    """One fixed, offline benchmark case. Expectations only -- never a
    pre-baked score."""
    benchmark_id: str
    question: str
    category: str
    expected_min_sources: int
    expected_min_evidence: int
    expected_min_supported_claims: int


class BenchmarkMetrics(BaseModel):
    source_coverage: float
    evidence_coverage: float
    claim_support: float
    source_diversity: float
    research_completeness: float
    quality_score: float


class BenchmarkResult(BaseModel):
    benchmark_id: str
    strategy_id: str
    score: float
    metrics: BenchmarkMetrics
    passed: bool
    source_count: int
    evidence_count: int
    supported_claim_count: int
    total_claim_count: int


class BenchmarkSuiteResult(BaseModel):
    strategy_id: str
    benchmark_count: int
    average_score: float
    median_score: float
    best_score: float
    worst_score: float
    passed_count: int
    failed_count: int
    results: List[BenchmarkResult] = Field(default_factory=list)


class ComparisonStatus(str, Enum):
    IMPROVED = "IMPROVED"
    REGRESSED = "REGRESSED"
    UNCHANGED = "UNCHANGED"
    MIXED = "MIXED"


class StrategyComparisonResult(BaseModel):
    baseline_strategy_id: str
    candidate_strategy_id: str
    baseline_score: float
    candidate_score: float
    absolute_improvement: float
    improvement_percentage: Optional[float]
    status: ComparisonStatus
    regressions: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
