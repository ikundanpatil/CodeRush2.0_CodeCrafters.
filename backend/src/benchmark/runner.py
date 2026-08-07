"""Phase 9 BenchmarkRunner.

Runs the fixed benchmark dataset through the REAL Phase 6 ResearchLoop for a
given Strategy -- never a simulation that assigns scores directly. Reuses,
unchanged: ResearchLoop, build_evidence_graph (via ResearchLoop), the Phase 5
ResearchQualityValidator, and the Phase 8 PolicyEngine (already wired inside
ResearchLoop itself, so it stays active here with zero extra code).

Benchmark mode isolation:
  * each question gets its own scratch ResearchRun with a fresh run_id --
    never passed to src.storage.store, so it can never appear in
    GET /api/history or GET /api/research/{id}.
  * the runner never touches src.memory.manager, so benchmark runs cannot
    write research memories.
  * the runner never touches src.evolution.service/store beyond a read-only
    Strategy lookup -- it cannot create, accept, or promote a champion.
"""

from datetime import datetime, timezone
from statistics import median
from typing import Callable, Dict, List, Optional
from uuid import uuid4

from src.benchmark.datasets import BENCHMARK_QUESTIONS, BenchmarkFixtureSearchProvider
from src.benchmark.metrics import compute_metrics
from src.benchmark.models import BenchmarkQuestion, BenchmarkResult, BenchmarkSuiteResult
from src.engine.research_loop import ResearchLoop
from src.evolution.models import Strategy
from src.llm.adapter import get_llm_adapter
from src.llm.base import LLMAdapter, LLMError
from src.llm.providers.mock import MockAdapter
from src.models.evidence import ClaimStatus
from src.models.schemas import AgentEvent, EventType, ResearchRun
from src.quality.validator import ResearchQualityValidator


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_llm() -> LLMAdapter:
    try:
        return get_llm_adapter()
    except LLMError:
        return MockAdapter()


class BenchmarkRunner:
    def __init__(self, dataset: Optional[List[BenchmarkQuestion]] = None):
        self.dataset = dataset if dataset is not None else BENCHMARK_QUESTIONS

    async def run_question(
        self, question: BenchmarkQuestion, strategy: Strategy, llm: LLMAdapter,
        emit: Optional[Callable[..., None]] = None,
    ) -> BenchmarkResult:
        if emit:
            emit(EventType.BENCHMARK_QUESTION_STARTED, f"Benchmark Question Started: {question.benchmark_id}",
                 f"Running '{question.question}' ({question.category}).",
                 {"benchmark_id": question.benchmark_id, "category": question.category})

        # Isolated scratch run: fresh id, never persisted to src.storage.store.
        run = ResearchRun(run_id=str(uuid4()), question=question.question)

        validator = ResearchQualityValidator(
            min_sources=strategy.params.min_sources,
            min_evidence=strategy.params.min_evidence,
            min_supported_claims=strategy.params.min_supported_claims,
        )
        loop = ResearchLoop(
            llm=llm,
            search_provider=BenchmarkFixtureSearchProvider(question.benchmark_id),
            run=run,
            max_iterations=strategy.params.max_iterations,
            quality_validator=validator,
            max_results_per_query=strategy.params.max_results_per_query,
            max_sources_per_iteration=strategy.params.max_sources_per_iteration,
        )
        loop_result = await loop.run(initial_queries=[question.question])

        quality_result = loop_result.quality_result or validator.validate(
            question.question, loop_result.sources, loop_result.evidence, loop_result.claims, loop_result.graph,
        )

        metrics = compute_metrics(
            sources=loop_result.sources,
            evidence_count=len(loop_result.evidence),
            claims=loop_result.claims,
            quality_result=quality_result,
            expected_min_sources=question.expected_min_sources,
            expected_min_evidence=question.expected_min_evidence,
        )

        supported_claim_count = sum(1 for c in loop_result.claims if c.status == ClaimStatus.SUPPORTED)
        passed = (
            len(loop_result.sources) >= question.expected_min_sources
            and len(loop_result.evidence) >= question.expected_min_evidence
            and supported_claim_count >= question.expected_min_supported_claims
        )

        result = BenchmarkResult(
            benchmark_id=question.benchmark_id,
            strategy_id=strategy.id,
            score=metrics.quality_score,
            metrics=metrics,
            passed=passed,
            source_count=len(loop_result.sources),
            evidence_count=len(loop_result.evidence),
            supported_claim_count=supported_claim_count,
            total_claim_count=len(loop_result.claims),
        )

        if emit:
            emit(EventType.BENCHMARK_QUESTION_COMPLETED, f"Benchmark Question Completed: {question.benchmark_id}",
                 f"Score {result.score:.3f}, passed={result.passed}.",
                 {"benchmark_id": question.benchmark_id, "score": result.score, "passed": result.passed})

        return result

    async def run_suite(
        self, strategy: Strategy, llm: Optional[LLMAdapter] = None,
        emit: Optional[Callable[..., None]] = None,
    ) -> BenchmarkSuiteResult:
        llm = llm or _get_llm()

        if emit:
            emit(EventType.BENCHMARK_STARTED, "Benchmark Suite Started",
                 f"Running {len(self.dataset)} benchmark question(s) against strategy generation {strategy.generation}.",
                 {"strategy_id": strategy.id, "generation": strategy.generation, "benchmark_count": len(self.dataset)})

        results: List[BenchmarkResult] = []
        for question in self.dataset:
            result = await self.run_question(question, strategy, llm, emit=emit)
            results.append(result)

        scores = [r.score for r in results]
        passed_count = sum(1 for r in results if r.passed)
        suite = BenchmarkSuiteResult(
            strategy_id=strategy.id,
            benchmark_count=len(results),
            average_score=sum(scores) / len(scores) if scores else 0.0,
            median_score=median(scores) if scores else 0.0,
            best_score=max(scores) if scores else 0.0,
            worst_score=min(scores) if scores else 0.0,
            passed_count=passed_count,
            failed_count=len(results) - passed_count,
            results=results,
        )

        if emit:
            emit(EventType.BENCHMARK_COMPLETED, "Benchmark Suite Completed",
                 f"Average score {suite.average_score:.3f} ({suite.passed_count}/{suite.benchmark_count} passed).",
                 {"strategy_id": strategy.id, "average_score": suite.average_score,
                  "passed_count": suite.passed_count, "failed_count": suite.failed_count})

        return suite


benchmark_runner = BenchmarkRunner()


# --------------------------------------------------------------------------
# In-memory benchmark run store -- keyed by an isolated benchmark_run_id,
# entirely separate from src.storage.store (real research run history).
# --------------------------------------------------------------------------
class _BenchmarkRunRecord:
    def __init__(self, benchmark_run_id: str, suite: BenchmarkSuiteResult, trace: List[AgentEvent]):
        self.benchmark_run_id = benchmark_run_id
        self.suite = suite
        self.trace = trace
        self.created_at = _utc_now()


_benchmark_runs: Dict[str, _BenchmarkRunRecord] = {}


async def run_and_store_suite(strategy: Strategy) -> _BenchmarkRunRecord:
    benchmark_run_id = str(uuid4())
    trace: List[AgentEvent] = []

    def emit(event_type: EventType, title: str, message: str, data=None):
        trace.append(AgentEvent(
            run_id=benchmark_run_id, step="Benchmark", type=event_type,
            title=title, message=message, data=data,
        ))

    suite = await benchmark_runner.run_suite(strategy, emit=emit)
    record = _BenchmarkRunRecord(benchmark_run_id, suite, trace)
    _benchmark_runs[benchmark_run_id] = record
    return record


def get_benchmark_run(benchmark_run_id: str) -> Optional[_BenchmarkRunRecord]:
    return _benchmark_runs.get(benchmark_run_id)


def list_benchmark_runs() -> List[_BenchmarkRunRecord]:
    return sorted(_benchmark_runs.values(), key=lambda r: r.created_at)
