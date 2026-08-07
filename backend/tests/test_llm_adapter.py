import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.main import app
from src.engine.orchestrator import orchestrator
from src.llm.adapter import get_llm_adapter
from src.llm.base import LLMAdapter, LLMConfigError, LLMError, LLMTimeoutError
from src.llm.providers.mock import MockAdapter
from src.models.schemas import AgentEvent, EventType, ResearchPlan, ResearchReportLLM, RunStatus

client = TestClient(app)


# --------------------------------------------------------------------------
# 1. Mock LLM generation
# --------------------------------------------------------------------------

def test_mock_adapter_plain_generation():
    adapter = MockAdapter()
    result = asyncio.run(adapter.generate("hello"))
    assert result == "Mock LLM response."


def test_mock_adapter_plan_shaped_response():
    adapter = MockAdapter()
    system_prompt = "Respond with JSON keys objective, sub_queries, source_types, verify."
    raw = asyncio.run(adapter.generate("Research question: X", system_prompt=system_prompt, response_format="json"))
    data = json.loads(raw)
    plan = ResearchPlan.model_validate(data)
    assert plan.objective
    assert len(plan.sub_queries) >= 1


def test_mock_adapter_report_shaped_response():
    adapter = MockAdapter()
    system_prompt = "Respond with JSON keys answer, key_findings, limitations."
    raw = asyncio.run(adapter.generate("Evidence: ...", system_prompt=system_prompt, response_format="json"))
    data = json.loads(raw)
    report = ResearchReportLLM.model_validate(data)
    assert report.answer


def test_mock_adapter_respects_explicit_override():
    adapter = MockAdapter()
    result = asyncio.run(adapter.generate("anything", mock_response="custom"))
    assert result == "custom"


# --------------------------------------------------------------------------
# 2. Provider factory
# --------------------------------------------------------------------------

def test_factory_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    adapter = get_llm_adapter()
    assert isinstance(adapter, MockAdapter)


def test_factory_explicit_mock():
    adapter = get_llm_adapter("mock")
    assert isinstance(adapter, MockAdapter)


def test_factory_reads_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    adapter = get_llm_adapter()
    assert isinstance(adapter, MockAdapter)


# --------------------------------------------------------------------------
# 3. Invalid provider
# --------------------------------------------------------------------------

def test_factory_invalid_provider_raises_config_error():
    with pytest.raises(LLMConfigError):
        get_llm_adapter("not-a-real-provider")


# --------------------------------------------------------------------------
# 4. Missing API key
# --------------------------------------------------------------------------

def test_openai_provider_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LLMConfigError):
        get_llm_adapter("openai")


def test_nvidia_provider_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    with pytest.raises(LLMConfigError):
        get_llm_adapter("nvidia")


# --------------------------------------------------------------------------
# 5. Planning response validation
# --------------------------------------------------------------------------

def test_research_plan_accepts_valid_payload():
    plan = ResearchPlan.model_validate({
        "objective": "Understand X",
        "sub_queries": ["a", "b"],
        "source_types": ["papers"],
        "verify": ["check dates"],
    })
    assert plan.objective == "Understand X"
    assert plan.sub_queries == ["a", "b"]


def test_research_plan_rejects_missing_objective():
    with pytest.raises(ValidationError):
        ResearchPlan.model_validate({"sub_queries": ["a"]})


def test_research_plan_rejects_empty_sub_queries():
    with pytest.raises(ValidationError):
        ResearchPlan.model_validate({"objective": "x", "sub_queries": []})


# --------------------------------------------------------------------------
# 6. Report generation
# --------------------------------------------------------------------------

def test_research_report_accepts_valid_payload():
    report = ResearchReportLLM.model_validate({
        "answer": "The answer.",
        "key_findings": ["finding 1"],
        "limitations": ["limitation 1"],
    })
    assert report.answer == "The answer."


def test_research_report_rejects_missing_answer():
    with pytest.raises(ValidationError):
        ResearchReportLLM.model_validate({"key_findings": []})


def test_full_pipeline_uses_llm_generated_plan_and_report():
    """End-to-end: default LLM_PROVIDER=mock drives planning + report generation."""
    response = client.post("/api/research", json={"question": "How does AI affect developer productivity?"})
    assert response.status_code == 201
    run_id = response.json()["run_id"]

    trace = client.get(f"/api/research/{run_id}/trace").json()
    planning_events = [e for e in trace if e["type"] == "planning"]
    assert len(planning_events) == 1
    assert "sub_queries" in planning_events[0]["data"]
    assert len(planning_events[0]["data"]["sub_queries"]) >= 1

    result = client.get(f"/api/research/{run_id}/result").json()
    assert result["status"] == "completed"
    assert "Mock answer synthesized" in result["answer"]
    assert "Key Findings" in result["answer"]


# --------------------------------------------------------------------------
# 7. Malformed LLM output -> graceful fallback, no crash
# --------------------------------------------------------------------------

class _MalformedAdapter(LLMAdapter):
    async def generate(self, prompt, system_prompt=None, **kwargs):
        return "this is not json"


def test_generate_structured_falls_back_on_malformed_output():
    run = _make_bare_run()
    result = asyncio.run(orchestrator._generate_structured(
        _MalformedAdapter(), "system", "prompt", ResearchPlan, run,
        EventType.LLM_PLANNING_FAILED, "LLM Planning Failed",
    ))
    assert result is None
    assert any(e.type == EventType.LLM_PLANNING_FAILED for e in run.trace)


def test_generate_plan_falls_back_gracefully_on_malformed_output():
    run = _make_bare_run()
    plan = asyncio.run(orchestrator._generate_plan(_MalformedAdapter(), run, []))
    assert isinstance(plan, ResearchPlan)
    assert plan.sub_queries  # fallback plan still has at least the question
    assert any(e.type == EventType.LLM_PLANNING_FAILED for e in run.trace)


# --------------------------------------------------------------------------
# 8. LLM timeout / failure -> graceful fallback, no crash
# --------------------------------------------------------------------------

class _FailingAdapter(LLMAdapter):
    async def generate(self, prompt, system_prompt=None, **kwargs):
        raise LLMTimeoutError("simulated timeout")


def test_generate_report_falls_back_gracefully_on_provider_failure():
    run = _make_bare_run()
    report = asyncio.run(orchestrator._generate_report(_FailingAdapter(), run, []))
    assert isinstance(report, ResearchReportLLM)
    assert any(e.type == EventType.LLM_REPORT_FAILED for e in run.trace)


def test_llm_provider_init_failure_falls_back_to_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    run = _make_bare_run()
    llm = orchestrator._get_llm(run)
    assert isinstance(llm, MockAdapter)
    assert any(e.type == EventType.LLM_PLANNING_FAILED for e in run.trace)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _make_bare_run():
    from src.models.schemas import ResearchRun
    return ResearchRun(question="Does X affect Y?")
