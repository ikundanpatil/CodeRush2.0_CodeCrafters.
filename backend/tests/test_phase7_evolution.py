import asyncio
import json

from fastapi.testclient import TestClient

from src.api.main import app
from src.evolution.benchmark import RotatingPoolSearchProvider
from src.evolution.evaluator import run_benchmark
from src.evolution.models import (
    BenchmarkQuestionResult, EvaluationResult, Strategy, StrategyParams, StrategyStatus,
)
from src.evolution.mutator import _fallback_mutation, propose_mutation
from src.evolution.scoring import score_quality_result
from src.evolution.service import EvolutionService
from src.evolution.store import EvolutionStore
from src.llm.base import LLMAdapter
from src.llm.providers.mock import MockAdapter
from src.quality.models import CheckSeverity, QualityCheck, ResearchQualityResult

client = TestClient(app)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _quality(**overrides) -> ResearchQualityResult:
    base = dict(
        valid=True, source_count=4, unique_source_count=4, evidence_count=4,
        claim_count=1, supported_claim_count=1, contradicted_claim_count=0,
        mixed_claim_count=0, unverified_claim_count=0, unsupported_claim_count=0,
        duplicate_source_count=0, graph_node_count=6, graph_edge_count=8,
        warnings=[], errors=[], checks=[],
    )
    base.update(overrides)
    return ResearchQualityResult(**base)


def _check(name: str, passed: bool) -> QualityCheck:
    return QualityCheck(
        name=name, passed=passed, severity=CheckSeverity.ERROR,
        message=f"{name} check", actual_value=0, expected_value=1,
    )


def _default_params() -> StrategyParams:
    return StrategyParams(
        min_sources=3, min_evidence=3, min_supported_claims=1,
        max_iterations=3, max_results_per_query=4, max_sources_per_iteration=5,
    )


def _strategy(params: StrategyParams, generation=0, status=StrategyStatus.ACCEPTED) -> Strategy:
    return Strategy(generation=generation, params=params, status=status, created_at="t")


# --------------------------------------------------------------------------
# scoring.py
# --------------------------------------------------------------------------

def test_score_rewards_supported_claims_and_validity():
    good = _quality(valid=True, supported_claim_count=3, errors=[], warnings=[])
    bad = _quality(valid=False, supported_claim_count=0, contradicted_claim_count=2, errors=["e1"], warnings=["w1"])
    assert score_quality_result(good) > score_quality_result(bad)


def test_score_penalizes_errors_more_than_warnings():
    with_error = _quality(errors=["e1"], warnings=[])
    with_warning = _quality(errors=[], warnings=["w1"])
    assert score_quality_result(with_error) < score_quality_result(with_warning)


# --------------------------------------------------------------------------
# mutator.py fallback heuristic (no LLM)
# --------------------------------------------------------------------------

def test_fallback_widens_loop_when_sources_insufficient():
    baseline = _default_params()
    evaluation = EvaluationResult(
        strategy_id="s1", mean_score=0.0,
        per_question=[BenchmarkQuestionResult(
            question="q", score=0.0,
            quality=_quality(checks=[_check("source_count", False)]),
        )],
    )
    params, reasoning = _fallback_mutation(baseline, evaluation)
    assert params.max_iterations == baseline.max_iterations + 1
    assert params.max_sources_per_iteration == baseline.max_sources_per_iteration + 1
    assert "source" in reasoning.lower() or "evidence" in reasoning.lower()


def test_fallback_tightens_rigor_when_baseline_is_clean():
    baseline = _default_params()
    evaluation = EvaluationResult(
        strategy_id="s1", mean_score=10.0,
        per_question=[BenchmarkQuestionResult(
            question="q", score=10.0,
            quality=_quality(errors=[], warnings=[], checks=[_check("source_count", True)]),
        )],
    )
    params, reasoning = _fallback_mutation(baseline, evaluation)
    assert params.min_supported_claims == baseline.min_supported_claims + 1
    assert params.max_iterations == baseline.max_iterations  # unchanged


def test_fallback_bounds_never_exceeded():
    baseline = StrategyParams(
        min_sources=10, min_evidence=10, min_supported_claims=10,
        max_iterations=6, max_results_per_query=10, max_sources_per_iteration=10,
    )
    evaluation = EvaluationResult(
        strategy_id="s1", mean_score=0.0,
        per_question=[BenchmarkQuestionResult(
            question="q", score=0.0,
            quality=_quality(checks=[_check("source_count", False)]),
        )],
    )
    params, _ = _fallback_mutation(baseline, evaluation)
    assert params.max_iterations <= 6
    assert params.max_sources_per_iteration <= 10


# --------------------------------------------------------------------------
# mutator.py -- LLM path and its fallback wiring
# --------------------------------------------------------------------------

class _AlwaysInvalidLLM(LLMAdapter):
    async def generate(self, prompt, system_prompt=None, **kwargs) -> str:
        return "not valid json at all"


class _ValidProposalLLM(LLMAdapter):
    async def generate(self, prompt, system_prompt=None, **kwargs) -> str:
        return json.dumps({
            "min_sources": 5, "min_evidence": 5, "min_supported_claims": 2,
            "max_iterations": 4, "max_results_per_query": 6, "max_sources_per_iteration": 6,
            "reasoning": "LLM proposed tightening thresholds.",
        })


def test_propose_mutation_falls_back_when_llm_output_invalid():
    baseline = _strategy(_default_params())
    evaluation = EvaluationResult(
        strategy_id=baseline.id, mean_score=0.0,
        per_question=[BenchmarkQuestionResult(
            question="q", score=0.0, quality=_quality(checks=[_check("source_count", False)]),
        )],
    )
    params, reasoning = asyncio.run(propose_mutation(baseline, evaluation, _AlwaysInvalidLLM()))
    assert params.max_iterations == baseline.params.max_iterations + 1


def test_propose_mutation_uses_valid_llm_output():
    baseline = _strategy(_default_params())
    evaluation = EvaluationResult(strategy_id=baseline.id, mean_score=1.0, per_question=[])
    params, reasoning = asyncio.run(propose_mutation(baseline, evaluation, _ValidProposalLLM()))
    assert params.min_sources == 5
    assert params.max_iterations == 4
    assert reasoning == "LLM proposed tightening thresholds."


def test_default_mock_adapter_exercises_fallback_path():
    """MockAdapter doesn't recognize the mutation prompt shape, so evolution
    running against the default offline provider always uses the
    deterministic fallback -- by design, not a bug."""
    baseline = _strategy(_default_params())
    evaluation = EvaluationResult(
        strategy_id=baseline.id, mean_score=0.0,
        per_question=[BenchmarkQuestionResult(
            question="q", score=0.0, quality=_quality(checks=[_check("source_count", False)]),
        )],
    )
    params, _ = asyncio.run(propose_mutation(baseline, evaluation, MockAdapter()))
    assert params.max_iterations == baseline.params.max_iterations + 1


# --------------------------------------------------------------------------
# benchmark.py / evaluator.py
# --------------------------------------------------------------------------

def test_rotating_pool_provider_never_repeats_a_url():
    provider = RotatingPoolSearchProvider("q")

    async def _drain():
        seen = set()
        for _ in range(4):
            results = await provider.search("q", max_results=3)
            for r in results:
                assert r.url not in seen
                seen.add(r.url)
        return seen

    seen = asyncio.run(_drain())
    assert len(seen) > 3  # pool exhausted across calls, not repeated per-call


def test_loose_strategy_scores_higher_and_gathers_more_than_strict():
    loose = _strategy(StrategyParams(
        min_sources=1, min_evidence=1, min_supported_claims=1,
        max_iterations=3, max_results_per_query=8, max_sources_per_iteration=8,
    ), generation=1)
    strict = _strategy(StrategyParams(
        min_sources=20, min_evidence=20, min_supported_claims=20,
        max_iterations=3, max_results_per_query=8, max_sources_per_iteration=8,
    ), generation=2)

    async def _run():
        loose_eval = await run_benchmark(loose, MockAdapter())
        strict_eval = await run_benchmark(strict, MockAdapter())
        return loose_eval, strict_eval

    loose_eval, strict_eval = asyncio.run(_run())

    assert loose_eval.mean_score > strict_eval.mean_score
    assert all(r.quality.valid for r in loose_eval.per_question)
    assert not any(r.quality.valid for r in strict_eval.per_question)


def test_loop_knobs_change_how_much_evidence_is_gathered():
    narrow = _strategy(StrategyParams(
        min_sources=1, min_evidence=1, min_supported_claims=1,
        max_iterations=1, max_results_per_query=2, max_sources_per_iteration=2,
    ), generation=1)
    wide = _strategy(StrategyParams(
        min_sources=1, min_evidence=1, min_supported_claims=1,
        max_iterations=3, max_results_per_query=8, max_sources_per_iteration=8,
    ), generation=2)

    async def _run():
        narrow_eval = await run_benchmark(narrow, MockAdapter())
        wide_eval = await run_benchmark(wide, MockAdapter())
        return narrow_eval, wide_eval

    narrow_eval, wide_eval = asyncio.run(_run())

    narrow_evidence = sum(r.quality.evidence_count for r in narrow_eval.per_question)
    wide_evidence = sum(r.quality.evidence_count for r in wide_eval.per_question)
    assert wide_evidence > narrow_evidence


# --------------------------------------------------------------------------
# store.py
# --------------------------------------------------------------------------

def test_get_champion_seeds_generation_zero_when_empty():
    store = EvolutionStore()
    champion = store.get_champion()
    assert champion.generation == 0
    assert champion.status == StrategyStatus.ACCEPTED
    assert store.get(champion.id) is not None


def test_save_get_and_lineage_roundtrip():
    store = EvolutionStore()
    seeded = store.get_champion()
    candidate = _strategy(_default_params(), generation=1, status=StrategyStatus.REJECTED)
    store.save(candidate)

    assert store.get(candidate.id).status == StrategyStatus.REJECTED
    lineage = store.list_lineage()
    ids = {s.id for s in lineage}
    assert {seeded.id, candidate.id} <= ids
    assert lineage[0].generation >= lineage[-1].generation  # newest generation first


# --------------------------------------------------------------------------
# service.py -- full cycle, accept and reject paths
# --------------------------------------------------------------------------

def test_run_cycle_accepts_a_clearly_better_candidate(monkeypatch):
    store = EvolutionStore()
    service = EvolutionService(store=store)
    baseline = store.get_champion()

    async def _better_mutation(baseline_strategy, baseline_eval, llm):
        params = baseline_strategy.params.model_copy()
        params.min_sources = 1
        params.min_evidence = 1
        params.min_supported_claims = 1
        params.max_results_per_query = 8
        params.max_sources_per_iteration = 8
        return params, "test: loosen everything for a guaranteed improvement"

    monkeypatch.setattr("src.evolution.service.propose_mutation", _better_mutation)

    result = asyncio.run(service.run_cycle())

    assert result.decision == "accepted"
    assert result.candidate.status == StrategyStatus.ACCEPTED
    champion = store.get_champion()
    assert champion.id == result.candidate.id
    assert champion.generation == baseline.generation + 1


def test_run_cycle_rejects_a_clearly_worse_candidate(monkeypatch):
    store = EvolutionStore()
    service = EvolutionService(store=store)
    baseline = store.get_champion()

    async def _worse_mutation(baseline_strategy, baseline_eval, llm):
        params = baseline_strategy.params.model_copy()
        params.min_sources = 50
        params.min_evidence = 50
        params.min_supported_claims = 50
        return params, "test: impossible thresholds, guaranteed to score worse"

    monkeypatch.setattr("src.evolution.service.propose_mutation", _worse_mutation)

    result = asyncio.run(service.run_cycle())

    assert result.decision == "rejected"
    assert result.candidate.status == StrategyStatus.REJECTED
    champion = store.get_champion()
    assert champion.id == baseline.id  # unchanged
    # rejected candidate is still auditable in the lineage
    lineage_ids = {s.id for s in store.list_lineage()}
    assert result.candidate.id in lineage_ids


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

def test_strategy_current_endpoint_returns_champion():
    response = client.get("/api/strategy/current")
    assert response.status_code == 200
    body = response.json()
    assert "params" in body and "status" in body


def test_evolve_endpoint_runs_a_cycle_and_lineage_reflects_it():
    response = client.post("/api/strategy/evolve")
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] in ("accepted", "rejected")
    assert len(body["trace"]) > 0

    lineage = client.get("/api/strategy/lineage").json()
    assert any(s["id"] == body["candidate"]["id"] for s in lineage)


def test_get_strategy_by_id_and_404():
    current = client.get("/api/strategy/current").json()
    ok = client.get(f"/api/strategy/{current['id']}")
    assert ok.status_code == 200

    missing = client.get("/api/strategy/does-not-exist")
    assert missing.status_code == 404
