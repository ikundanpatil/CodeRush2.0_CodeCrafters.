"""Phase 9 - Benchmarks + Improvement Tests: dataset, metrics, runner.

Covers: the fixed offline dataset, deterministic metric formulas, that the
BenchmarkRunner genuinely drives the real ResearchLoop (Policy Engine
included, since it's wired inside ResearchLoop itself), determinism, and
that no metric or score can be fabricated by an LLM response.
"""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.benchmark import metrics as metrics_module
from src.benchmark.datasets import BENCHMARK_QUESTIONS, BenchmarkFixtureSearchProvider
from src.benchmark.models import BenchmarkMetrics
from src.benchmark.runner import BenchmarkRunner, benchmark_runner
from src.engine import research_loop as research_loop_module
from src.evidence.graph import EvidenceGraph
from src.evolution.models import Strategy, StrategyParams, StrategyStatus
from src.llm.base import LLMAdapter
from src.llm.providers.mock import MockAdapter
from src.models.evidence import Claim, ClaimStatus
from src.models.schemas import Source
from src.policy.audit import policy_audit_log
from src.quality.models import CheckSeverity, QualityCheck, ResearchQualityResult

client = TestClient(app)


def _params(**overrides) -> StrategyParams:
    base = dict(
        min_sources=3, min_evidence=3, min_supported_claims=1,
        max_iterations=3, max_results_per_query=4, max_sources_per_iteration=5,
    )
    base.update(overrides)
    return StrategyParams(**base)


def _strategy(**overrides) -> Strategy:
    return Strategy(generation=0, status=StrategyStatus.ACCEPTED, params=_params(**overrides))


# --------------------------------------------------------------------------
# dataset
# --------------------------------------------------------------------------

def test_dataset_loads_correctly():
    assert len(BENCHMARK_QUESTIONS) > 0
    for q in BENCHMARK_QUESTIONS:
        assert q.benchmark_id
        assert q.question
        assert q.category
        assert q.expected_min_sources > 0
        assert q.expected_min_evidence > 0
        assert q.expected_min_supported_claims > 0


def test_dataset_has_at_least_ten_questions():
    assert len(BENCHMARK_QUESTIONS) >= 10


def test_dataset_covers_required_categories():
    categories = {q.category for q in BENCHMARK_QUESTIONS}
    required = {
        "Technology", "AI", "Software Development", "Cybersecurity", "Environment",
        "Education", "Healthcare Technology", "Business", "Science", "General Knowledge",
    }
    assert required <= categories


def test_benchmark_questions_are_deterministic():
    ids_a = [q.benchmark_id for q in BENCHMARK_QUESTIONS]
    from src.benchmark.datasets import BENCHMARK_QUESTIONS as reloaded
    ids_b = [q.benchmark_id for q in reloaded]
    assert ids_a == ids_b
    assert len(ids_a) == len(set(ids_a))  # no duplicate ids


def test_benchmark_search_provider_is_deterministic():
    async def _drain(benchmark_id):
        provider = BenchmarkFixtureSearchProvider(benchmark_id)
        out = []
        for _ in range(3):
            out.append([r.url for r in await provider.search("q", max_results=3)])
        return out

    run_a = asyncio.run(_drain("AI-001"))
    run_b = asyncio.run(_drain("AI-001"))
    assert run_a == run_b


# --------------------------------------------------------------------------
# metrics -- pure formulas
# --------------------------------------------------------------------------

def _source(url="https://a.example.com/x") -> Source:
    return Source(title="T", url=url)


def _claim(status: ClaimStatus) -> Claim:
    return Claim(research_run_id="r1", claim_text="c", status=status)


def _quality_result(checks) -> ResearchQualityResult:
    return ResearchQualityResult(
        valid=True, source_count=0, unique_source_count=0, evidence_count=0, claim_count=0,
        supported_claim_count=0, contradicted_claim_count=0, mixed_claim_count=0,
        unverified_claim_count=0, unsupported_claim_count=0, duplicate_source_count=0,
        graph_node_count=0, graph_edge_count=0, warnings=[], errors=[], checks=checks,
    )


def _check(passed: bool) -> QualityCheck:
    return QualityCheck(name="x", passed=passed, severity=CheckSeverity.INFO, message="m")


def test_source_coverage_calculation():
    sources = [_source("https://a.com"), _source("https://b.com")]
    assert metrics_module.source_coverage(sources, 4) == pytest.approx(0.5)
    assert metrics_module.source_coverage(sources, 2) == pytest.approx(1.0)
    assert metrics_module.source_coverage(sources, 1) == pytest.approx(1.0)  # clamped


def test_evidence_coverage_calculation():
    assert metrics_module.evidence_coverage(3, 6) == pytest.approx(0.5)
    assert metrics_module.evidence_coverage(6, 6) == pytest.approx(1.0)
    assert metrics_module.evidence_coverage(10, 6) == pytest.approx(1.0)  # clamped


def test_claim_support_calculation():
    claims = [_claim(ClaimStatus.SUPPORTED), _claim(ClaimStatus.SUPPORTED), _claim(ClaimStatus.CONTRADICTED)]
    assert metrics_module.claim_support(claims) == pytest.approx(2 / 3)


def test_source_diversity_calculation():
    same_domain = [_source("https://a.com/1"), _source("https://a.com/2")]
    assert metrics_module.source_diversity(same_domain) == pytest.approx(0.5)
    diverse = [_source("https://a.com"), _source("https://b.com")]
    assert metrics_module.source_diversity(diverse) == pytest.approx(1.0)


def test_research_completeness_calculation():
    checks = [_check(True), _check(True), _check(False), _check(True)]
    assert metrics_module.research_completeness(_quality_result(checks)) == pytest.approx(0.75)


def test_quality_score_calculation_is_deterministic_weighted_sum():
    m = BenchmarkMetrics(
        source_coverage=1.0, evidence_coverage=1.0, claim_support=1.0,
        source_diversity=1.0, research_completeness=1.0, quality_score=0.0,
    )
    assert metrics_module.quality_score(m) == pytest.approx(1.0)

    m2 = BenchmarkMetrics(
        source_coverage=0.0, evidence_coverage=0.0, claim_support=0.0,
        source_diversity=0.0, research_completeness=0.0, quality_score=0.0,
    )
    assert metrics_module.quality_score(m2) == pytest.approx(0.0)

    m3 = BenchmarkMetrics(
        source_coverage=0.5, evidence_coverage=0.5, claim_support=0.5,
        source_diversity=0.5, research_completeness=0.5, quality_score=0.0,
    )
    expected = (
        metrics_module.WEIGHT_SOURCE_COVERAGE + metrics_module.WEIGHT_EVIDENCE_COVERAGE
        + metrics_module.WEIGHT_CLAIM_SUPPORT + metrics_module.WEIGHT_SOURCE_DIVERSITY
        + metrics_module.WEIGHT_RESEARCH_COMPLETENESS
    ) * 0.5
    assert metrics_module.quality_score(m3) == pytest.approx(expected)


def test_zero_division_handled_everywhere():
    assert metrics_module.source_coverage([], 3) == 0.0
    assert metrics_module.source_coverage([], 0) == 0.0  # no expectation, no sources
    assert metrics_module.evidence_coverage(0, 0) == 0.0
    assert metrics_module.claim_support([]) == 0.0
    assert metrics_module.source_diversity([]) == 0.0
    assert metrics_module.research_completeness(_quality_result([])) == 0.0


def test_score_is_clamped_between_zero_and_one():
    # expected_min of 1 with far more sources than needed must not push
    # source_coverage (or the final score) above 1.0.
    many_sources = [_source(f"https://s{i}.com") for i in range(50)]
    assert metrics_module.source_coverage(many_sources, 1) == 1.0
    assert metrics_module.evidence_coverage(500, 1) == 1.0
    full = BenchmarkMetrics(
        source_coverage=1.0, evidence_coverage=1.0, claim_support=1.0,
        source_diversity=1.0, research_completeness=1.0, quality_score=0.0,
    )
    assert 0.0 <= metrics_module.quality_score(full) <= 1.0


# --------------------------------------------------------------------------
# runner: real ResearchLoop + Policy Engine reuse
# --------------------------------------------------------------------------

def test_research_loop_is_actually_used(monkeypatch):
    calls = {"n": 0}
    original_run = research_loop_module.ResearchLoop.run

    async def spy_run(self, *args, **kwargs):
        calls["n"] += 1
        return await original_run(self, *args, **kwargs)

    monkeypatch.setattr(research_loop_module.ResearchLoop, "run", spy_run)

    strategy = _strategy()
    question = BENCHMARK_QUESTIONS[0]
    asyncio.run(BenchmarkRunner().run_question(question, strategy, MockAdapter()))
    assert calls["n"] == 1


def test_policy_engine_is_active_during_benchmark():
    # The audit log is bounded (maxlen), so its length can plateau once
    # full -- track run_ids already present instead of relying on growth.
    known_run_ids = {e.run_id for e in policy_audit_log.recent(1000)}

    strategy = _strategy()
    question = BENCHMARK_QUESTIONS[0]
    asyncio.run(BenchmarkRunner().run_question(question, strategy, MockAdapter()))

    new_entries = [e for e in policy_audit_log.recent(1000) if e.run_id not in known_run_ids]
    assert new_entries, "benchmark run must produce new, policy-evaluated audit entries"
    assert any(e.action == "SEARCH" and e.decision == "ALLOW" for e in new_entries)


def test_benchmark_results_are_deterministic():
    strategy = _strategy()
    suite_a = asyncio.run(benchmark_runner.run_suite(strategy, llm=MockAdapter()))
    suite_b = asyncio.run(benchmark_runner.run_suite(strategy, llm=MockAdapter()))
    assert [r.score for r in suite_a.results] == [r.score for r in suite_b.results]
    assert suite_a.average_score == suite_b.average_score


# --------------------------------------------------------------------------
# anti-fabrication (section 9 / 20)
# --------------------------------------------------------------------------

class _ScoreInjectingLLM(LLMAdapter):
    """Always tries to smuggle a fake, high 'score' field into whatever
    structured JSON is expected -- claim extraction, relationship
    classification, follow-up queries, everything."""

    async def generate(self, prompt, system_prompt=None, **kwargs) -> str:
        return json.dumps({"score": 0.99, "improvement": "research improved by 30%"})


def test_llm_cannot_directly_set_score(monkeypatch):
    sentinel = 0.4242
    monkeypatch.setattr(metrics_module, "quality_score", lambda m: sentinel)
    # runner.py calls compute_metrics, which internally calls quality_score --
    # patch at the compute_metrics call site's module too, since it imported
    # the function by reference.
    import src.benchmark.metrics as m
    monkeypatch.setattr(m, "quality_score", lambda metrics: sentinel)

    strategy = _strategy()
    question = BENCHMARK_QUESTIONS[0]
    result = asyncio.run(BenchmarkRunner().run_question(question, strategy, _ScoreInjectingLLM()))

    # The final score is exactly whatever metrics.quality_score computed --
    # never 0.99, never anything the LLM said.
    assert result.score == sentinel
    assert result.score != 0.99


def test_no_fabricated_metrics_end_to_end():
    """Without patching anything: run a benchmark question against an LLM
    that only ever emits a fake 'score', and confirm the resulting
    BenchmarkResult score is independently reproducible from the same real
    objects via metrics.compute_metrics -- proof it was computed, not
    copied from the LLM's output."""
    strategy = _strategy()
    question = BENCHMARK_QUESTIONS[0]

    run = None
    from src.models.schemas import ResearchRun
    from src.engine.research_loop import ResearchLoop
    from src.quality.validator import ResearchQualityValidator

    run = ResearchRun(question=question.question)
    validator = ResearchQualityValidator(
        min_sources=strategy.params.min_sources, min_evidence=strategy.params.min_evidence,
        min_supported_claims=strategy.params.min_supported_claims,
    )
    loop = ResearchLoop(
        llm=_ScoreInjectingLLM(),
        search_provider=BenchmarkFixtureSearchProvider(question.benchmark_id),
        run=run, max_iterations=strategy.params.max_iterations, quality_validator=validator,
        max_results_per_query=strategy.params.max_results_per_query,
        max_sources_per_iteration=strategy.params.max_sources_per_iteration,
    )
    loop_result = asyncio.run(loop.run(initial_queries=[question.question]))
    quality_result = loop_result.quality_result or validator.validate(
        question.question, loop_result.sources, loop_result.evidence, loop_result.claims, loop_result.graph,
    )
    expected_metrics = metrics_module.compute_metrics(
        sources=loop_result.sources, evidence_count=len(loop_result.evidence), claims=loop_result.claims,
        quality_result=quality_result, expected_min_sources=question.expected_min_sources,
        expected_min_evidence=question.expected_min_evidence,
    )

    result = asyncio.run(BenchmarkRunner().run_question(question, strategy, _ScoreInjectingLLM()))
    assert result.score == pytest.approx(expected_metrics.quality_score)
    assert result.score != 0.99


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

def test_api_benchmark_run_and_results():
    response = client.post("/api/benchmark/run")
    assert response.status_code == 200
    body = response.json()
    run_id = body["benchmark_run_id"]
    assert body["suite"]["benchmark_count"] == len(BENCHMARK_QUESTIONS)

    status_response = client.get(f"/api/benchmark/{run_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"

    results_response = client.get(f"/api/benchmark/{run_id}/results")
    assert results_response.status_code == 200
    assert len(results_response.json()) == len(BENCHMARK_QUESTIONS)


def test_api_benchmark_run_not_found():
    assert client.get("/api/benchmark/does-not-exist").status_code == 404
    assert client.get("/api/benchmark/does-not-exist/results").status_code == 404
