"""Phase 9 - improvement calculation, regression detection, and the
Phase 7/8/9 integration flow: Generation 0 -> Benchmark -> Baseline Score ->
Evolution -> Policy Validation -> Candidate Strategy -> Benchmark ->
Candidate Score -> Comparator -> Improvement/Regression.
"""

import asyncio

from src.benchmark.comparator import SIGNIFICANCE_EPSILON, StrategyComparator
from src.benchmark.models import BenchmarkResult, BenchmarkMetrics, BenchmarkSuiteResult, ComparisonStatus
from src.benchmark.report import generate_improvement_report
from src.benchmark.runner import BenchmarkRunner
from src.evolution.models import Strategy, StrategyParams, StrategyStatus
from src.evolution.store import EvolutionStore
from src.llm.providers.mock import MockAdapter
from src.policy.engine import policy_engine
from src.policy.models import PolicyAction, PolicyDecision, PolicyRequest

comparator = StrategyComparator()


def _metrics(score: float) -> BenchmarkMetrics:
    return BenchmarkMetrics(
        source_coverage=score, evidence_coverage=score, claim_support=score,
        source_diversity=score, research_completeness=score, quality_score=score,
    )


def _result(benchmark_id: str, strategy_id: str, score: float, passed: bool = True) -> BenchmarkResult:
    return BenchmarkResult(
        benchmark_id=benchmark_id, strategy_id=strategy_id, score=score, metrics=_metrics(score),
        passed=passed, source_count=3, evidence_count=4, supported_claim_count=1, total_claim_count=1,
    )


def _suite(strategy_id: str, scores: dict) -> BenchmarkSuiteResult:
    results = [_result(bid, strategy_id, s) for bid, s in scores.items()]
    vals = list(scores.values())
    return BenchmarkSuiteResult(
        strategy_id=strategy_id, benchmark_count=len(results),
        average_score=sum(vals) / len(vals), median_score=sorted(vals)[len(vals) // 2],
        best_score=max(vals), worst_score=min(vals),
        passed_count=len(results), failed_count=0, results=results,
    )


def _params(**overrides) -> StrategyParams:
    base = dict(
        min_sources=3, min_evidence=3, min_supported_claims=1,
        max_iterations=3, max_results_per_query=4, max_sources_per_iteration=5,
    )
    base.update(overrides)
    return StrategyParams(**base)


# --------------------------------------------------------------------------
# improvement percentage / absolute improvement
# --------------------------------------------------------------------------

def test_improvement_percentage_calculated_correctly():
    baseline = _suite("baseline", {"A": 0.65, "B": 0.65})
    candidate = _suite("candidate", {"A": 0.72, "B": 0.72})
    result = comparator.compare(baseline, candidate)
    assert result.absolute_improvement == 0.72 - 0.65
    assert result.improvement_percentage == ((0.72 - 0.65) / 0.65) * 100


def test_zero_baseline_handled_safely():
    baseline = _suite("baseline", {"A": 0.0, "B": 0.0})
    candidate = _suite("candidate", {"A": 0.5, "B": 0.5})
    result = comparator.compare(baseline, candidate)
    assert result.improvement_percentage is None  # never inf, never a crash
    assert result.absolute_improvement == 0.5


# --------------------------------------------------------------------------
# regression / improvement / unchanged / mixed detection
# --------------------------------------------------------------------------

def test_improvement_detected():
    baseline = _suite("baseline", {"A": 0.65, "B": 0.65})
    candidate = _suite("candidate", {"A": 0.72, "B": 0.72})
    result = comparator.compare(baseline, candidate)
    assert result.status == ComparisonStatus.IMPROVED
    assert result.improvements
    assert not result.regressions


def test_regression_detected():
    baseline = _suite("baseline", {"A": 0.72, "B": 0.72})
    candidate = _suite("candidate", {"A": 0.68, "B": 0.68})
    result = comparator.compare(baseline, candidate)
    assert result.status == ComparisonStatus.REGRESSED
    assert result.regressions
    assert not result.improvements


def test_unchanged_detected():
    baseline = _suite("baseline", {"A": 0.70, "B": 0.70})
    candidate = _suite("candidate", {"A": 0.705, "B": 0.702})
    result = comparator.compare(baseline, candidate)
    assert result.status == ComparisonStatus.UNCHANGED
    assert not result.improvements
    assert not result.regressions


def test_mixed_result_detected():
    baseline = _suite("baseline", {"A": 0.60, "B": 0.80})
    candidate = _suite("candidate", {"A": 0.85, "B": 0.55})  # A up, B down, both significant
    result = comparator.compare(baseline, candidate)
    assert result.status == ComparisonStatus.MIXED
    assert "A" in result.improvements
    assert "B" in result.regressions


def test_single_benchmark_improvement_does_not_override_flat_average():
    """Regression guard: one benchmark crossing the significance threshold
    upward must not report IMPROVED if the strategy is, on average, no
    better -- see comparator.py's _classify docstring. Here A improves just
    past the threshold (+0.021) while B and C each drift down by just under
    it (-0.019, individually not flagged as regressions), netting an
    average change well inside the noise band."""
    baseline = _suite("baseline", {"A": 0.700, "B": 0.700, "C": 0.700})
    candidate = _suite("candidate", {"A": 0.721, "B": 0.681, "C": 0.681})
    result = comparator.compare(baseline, candidate)

    assert "A" in result.improvements
    assert not result.regressions
    assert abs(result.absolute_improvement) <= SIGNIFICANCE_EPSILON
    assert result.status == ComparisonStatus.UNCHANGED
    assert result.status != ComparisonStatus.IMPROVED


def test_improvement_report_never_claims_more_than_computed():
    baseline = _suite("baseline", {"A": 0.65, "B": 0.65})
    candidate = _suite("candidate", {"A": 0.72, "B": 0.72})
    comparison = comparator.compare(baseline, candidate)
    report = generate_improvement_report(comparison)
    assert report["status"] == "IMPROVED"
    assert report["improvement_percentage"] == comparison.improvement_percentage
    assert report["absolute_improvement"] == comparison.absolute_improvement


# --------------------------------------------------------------------------
# champion isolation (section 14) -- Phase 9 never selects a champion
# --------------------------------------------------------------------------

def test_benchmark_does_not_automatically_change_champion():
    store = EvolutionStore()
    original_champion = store.get_champion()

    strong_candidate = Strategy(
        generation=original_champion.generation + 1, parent_id=original_champion.id,
        status=StrategyStatus.CANDIDATE, params=_params(max_results_per_query=8, max_sources_per_iteration=8),
    )
    # Benchmark it -- a measurement operation only.
    asyncio.run(BenchmarkRunner().run_suite(strong_candidate, llm=MockAdapter()))

    # Nothing about running (or even scoring very well in) a benchmark
    # touches the store or promotes anything -- champion is unchanged, and
    # the candidate strategy was never even saved to the store by Phase 9.
    assert store.get_champion().id == original_champion.id
    assert store.get(strong_candidate.id) is None


# --------------------------------------------------------------------------
# Phase 7 + 8 + 9 integration: the full evolution-validation flow
# --------------------------------------------------------------------------

def test_full_generation_0_to_1_benchmark_validation_flow():
    """Generation 0 -> Benchmark -> Baseline Score -> (simulated) Evolution
    -> Policy Validation -> Candidate Strategy -> Benchmark -> Candidate
    Score -> Comparator -> Improvement/Regression, using the REAL
    BenchmarkRunner (and therefore the real ResearchLoop + Policy Engine)
    for both suites."""
    baseline = Strategy(generation=0, status=StrategyStatus.ACCEPTED, params=_params(
        min_sources=1, min_evidence=1, min_supported_claims=1,
        max_iterations=1, max_results_per_query=2, max_sources_per_iteration=2,
    ))
    candidate = Strategy(generation=1, parent_id=baseline.id, status=StrategyStatus.CANDIDATE, params=_params(
        min_sources=3, min_evidence=5, min_supported_claims=1,
        max_iterations=3, max_results_per_query=6, max_sources_per_iteration=6,
    ))

    # A candidate must never bypass the Phase 8 Policy Engine -- verify the
    # candidate's params clear policy before it's even benchmarked (the
    # same gate EvolutionService itself applies in Phase 7/8).
    policy_result = policy_engine.evaluate(PolicyRequest(
        action=PolicyAction.EVOLVE_STRATEGY, parameters={"strategy": candidate.params.model_dump()},
    ))
    assert policy_result.decision == PolicyDecision.ALLOW

    runner = BenchmarkRunner()
    baseline_suite = asyncio.run(runner.run_suite(baseline, llm=MockAdapter()))
    candidate_suite = asyncio.run(runner.run_suite(candidate, llm=MockAdapter()))

    comparison = comparator.compare(baseline_suite, candidate_suite)

    # Real, measured outcome -- the weaker/narrower baseline strategy must
    # score lower than the more generous, policy-approved candidate.
    assert baseline_suite.average_score < candidate_suite.average_score
    assert comparison.status == ComparisonStatus.IMPROVED
    assert comparison.improvement_percentage > 0

    report = generate_improvement_report(comparison)
    assert report["status"] == "IMPROVED"


def test_policy_denied_strategy_never_reaches_benchmark_as_champion_material():
    """A strategy that fails Phase 8 policy (e.g. exceeds the global
    iteration limit) is denied by the same policy check the evolution flow
    uses -- Phase 9 does not, and must not, provide a way around it."""
    reckless = _params(max_iterations=99999)
    policy_result = policy_engine.evaluate(PolicyRequest(
        action=PolicyAction.EVOLVE_STRATEGY, parameters={"strategy": reckless.model_dump()},
    ))
    assert policy_result.decision == PolicyDecision.DENY
