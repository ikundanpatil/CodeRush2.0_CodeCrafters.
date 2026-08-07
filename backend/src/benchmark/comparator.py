"""Phase 9 StrategyComparator.

Compares two completed BenchmarkSuiteResults (baseline vs. candidate) using
only their own numbers -- deterministic thresholds, no LLM involvement, no
"an evolved strategy is better because it's newer" assumption. A single
improved benchmark is never enough to call the whole strategy IMPROVED; a
single regressed one is never enough to call it REGRESSED outright either --
both directions happening together is MIXED.
"""

from typing import Dict, List

from src.benchmark.models import BenchmarkSuiteResult, ComparisonStatus, StrategyComparisonResult

# A per-benchmark score delta smaller than this is noise, not a real
# improvement or regression. Documented, deterministic, not tuned per-run.
SIGNIFICANCE_EPSILON = 0.02


def _index_by_benchmark_id(suite: BenchmarkSuiteResult) -> Dict[str, float]:
    return {r.benchmark_id: r.score for r in suite.results}


class StrategyComparator:
    def compare(
        self, baseline: BenchmarkSuiteResult, candidate: BenchmarkSuiteResult,
    ) -> StrategyComparisonResult:
        baseline_scores = _index_by_benchmark_id(baseline)
        candidate_scores = _index_by_benchmark_id(candidate)
        shared_ids = sorted(set(baseline_scores) & set(candidate_scores))

        improvements: List[str] = []
        regressions: List[str] = []
        for benchmark_id in shared_ids:
            delta = candidate_scores[benchmark_id] - baseline_scores[benchmark_id]
            if delta > SIGNIFICANCE_EPSILON:
                improvements.append(benchmark_id)
            elif delta < -SIGNIFICANCE_EPSILON:
                regressions.append(benchmark_id)

        absolute_improvement = candidate.average_score - baseline.average_score
        if baseline.average_score == 0:
            improvement_percentage = None
        else:
            improvement_percentage = (absolute_improvement / baseline.average_score) * 100

        status = self._classify(absolute_improvement, improvements, regressions)

        return StrategyComparisonResult(
            baseline_strategy_id=baseline.strategy_id,
            candidate_strategy_id=candidate.strategy_id,
            baseline_score=baseline.average_score,
            candidate_score=candidate.average_score,
            absolute_improvement=absolute_improvement,
            improvement_percentage=improvement_percentage,
            status=status,
            regressions=regressions,
            improvements=improvements,
        )

    def _classify(
        self, absolute_improvement: float, improvements: List[str], regressions: List[str],
    ) -> ComparisonStatus:
        # Both directions present at the per-benchmark level: some questions
        # got better, others got worse -- MIXED regardless of what the
        # average happens to net out to.
        if improvements and regressions:
            return ComparisonStatus.MIXED

        # Otherwise the overall average is the primary signal (matches the
        # spec's worked examples directly: 0.65 -> 0.72 is IMPROVED, 0.72 ->
        # 0.68 is REGRESSED). A single benchmark crossing the significance
        # threshold while the average barely moves is noise, not a verdict
        # -- e.g. one question improving by a hair while several others
        # each drift down by less than epsilon must not be reported as
        # "IMPROVED" when the strategy is, on average, no better.
        if absolute_improvement > SIGNIFICANCE_EPSILON:
            return ComparisonStatus.IMPROVED
        if absolute_improvement < -SIGNIFICANCE_EPSILON:
            return ComparisonStatus.REGRESSED
        return ComparisonStatus.UNCHANGED


strategy_comparator = StrategyComparator()
