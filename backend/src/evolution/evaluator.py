"""Phase 7 benchmark evaluation: runs a candidate/baseline Strategy through
the *real* `ResearchLoop` (Phase 6) against the fixed offline benchmark
(`src/evolution/benchmark.py`) and scores each result with
`src/evolution/scoring.py`. Deliberately reuses `ResearchLoop` unchanged
rather than reimplementing research logic for evaluation purposes.
"""

from src.engine.research_loop import ResearchLoop
from src.evolution.benchmark import BENCHMARK_QUESTIONS, RotatingPoolSearchProvider
from src.evolution.models import BenchmarkQuestionResult, EvaluationResult, Strategy
from src.evolution.scoring import score_quality_result
from src.llm.base import LLMAdapter
from src.models.schemas import ResearchRun
from src.quality.validator import ResearchQualityValidator


async def run_benchmark(strategy: Strategy, llm: LLMAdapter) -> EvaluationResult:
    validator = ResearchQualityValidator(
        min_sources=strategy.params.min_sources,
        min_evidence=strategy.params.min_evidence,
        min_supported_claims=strategy.params.min_supported_claims,
    )

    per_question = []
    for question in BENCHMARK_QUESTIONS:
        run = ResearchRun(question=question)
        loop = ResearchLoop(
            llm=llm,
            search_provider=RotatingPoolSearchProvider(question),
            run=run,
            max_iterations=strategy.params.max_iterations,
            quality_validator=validator,
            max_results_per_query=strategy.params.max_results_per_query,
            max_sources_per_iteration=strategy.params.max_sources_per_iteration,
        )
        loop_result = await loop.run(initial_queries=[question])
        quality = loop_result.quality_result or validator.validate(
            question, loop_result.sources, loop_result.evidence, loop_result.claims, loop_result.graph,
        )
        per_question.append(BenchmarkQuestionResult(
            question=question,
            quality=quality,
            score=score_quality_result(quality),
        ))

    mean_score = sum(r.score for r in per_question) / len(per_question) if per_question else 0.0
    return EvaluationResult(strategy_id=strategy.id, per_question=per_question, mean_score=mean_score)
