import asyncio
from typing import Dict, List, Set

import pytest

from src.browser.base import BrowserError
from src.engine import research_loop as research_loop_module
from src.engine.orchestrator import orchestrator
from src.engine.research_loop import IterationDecision, ResearchLoop
from src.llm.base import LLMAdapter
from src.llm.providers.mock import MockAdapter
from src.memory.manager import memory_manager
from src.models.schemas import ResearchRun, ResearchReportLLM
from src.quality.validator import ResearchQualityValidator
from src.search.base import SearchError, SearchProvider, SearchResult
from src.storage.store import store


class _MapSearchProvider(SearchProvider):
    """Deterministic test double: returns canned results per query string, so
    follow-up queries (which differ from the original ones) can return new
    sources -- unlike the always-identical Phase 2 MockSearchProvider."""

    provides_full_content = True

    def __init__(self, query_map: Dict[str, List[SearchResult]], fail_queries: Set[str] = frozenset()):
        self._map = query_map
        self._fail_queries = fail_queries

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        if query in self._fail_queries:
            raise SearchError(f"search provider failed for query: {query}")
        return list(self._map.get(query, []))


class _NonFullContentSearchProvider(_MapSearchProvider):
    """Like _MapSearchProvider but forces the loop through the safe-browser
    fetch path (provides_full_content=False), so browser failures can be
    exercised."""
    provides_full_content = False


class _FollowupBreakingLLM(LLMAdapter):
    """Delegates to MockAdapter for everything except follow-up query
    generation, which always returns invalid JSON -- simulates the LLM
    producing unusable structured output for that one call."""

    def __init__(self):
        self._inner = MockAdapter()

    async def generate(self, prompt: str, system_prompt=None, **kwargs) -> str:
        combined = f"{system_prompt or ''}\n{prompt}"
        if "research_gap" in combined and "follow-up" in combined.lower():
            return "not valid json at all"
        return await self._inner.generate(prompt, system_prompt=system_prompt, **kwargs)


FOLLOWUP_QUERIES = [
    "independent controlled studies on the topic",
    "critical review and limitations of the claim",
    "contradicting evidence and counterpoints",
]

SUPPORTIVE_RESULT = SearchResult(
    title="Source A", url="https://a.example.com/study",
    content="Independent studies show a large boost in developer productivity from AI tools.",
    source="Test Journal", score=0.9,
)
DUPLICATE_OF_A = SearchResult(
    title="Source A (mirror)", url="https://a.example.com/study",
    content="A mirrored listing of the same study.",
    source="Test Mirror", score=0.5,
)
CONTRADICTING_RESULT = SearchResult(
    title="Source C", url="https://c.example.com/study",
    content="A controlled study did not show measurable productivity gains over 12 months.",
    source="Test Council", score=0.7,
)


def _loose_validator(monkeypatch, min_sources=1, min_evidence=1, min_supported_claims=1):
    monkeypatch.setenv("MIN_SOURCES", str(min_sources))
    monkeypatch.setenv("MIN_EVIDENCE", str(min_evidence))
    monkeypatch.setenv("MIN_SUPPORTED_CLAIMS", str(min_supported_claims))
    fresh = ResearchQualityValidator(
        min_sources=min_sources, min_evidence=min_evidence, min_supported_claims=min_supported_claims,
    )
    monkeypatch.setattr(research_loop_module, "research_quality_validator", fresh)
    return fresh


# --------------------------------------------------------------------------
# 1. Completion / continuation
# --------------------------------------------------------------------------

def test_research_completes_on_first_iteration(monkeypatch):
    _loose_validator(monkeypatch, min_sources=1, min_evidence=1, min_supported_claims=1)
    provider = _MapSearchProvider({"Q1": [SUPPORTIVE_RESULT]})
    run = ResearchRun(question="Does generative AI improve developer productivity?")
    loop = ResearchLoop(llm=MockAdapter(), search_provider=provider, run=run, max_iterations=3)

    result = asyncio.run(loop.run(initial_queries=["Q1"]))

    assert result.final_decision == IterationDecision.COMPLETE
    assert len(result.iterations) == 1
    assert result.quality_result.valid is True


def test_research_continues_when_quality_fails():
    # Default thresholds (3 sources / 3 evidence / 1 supported claim) --
    # one thin source is never enough on the first pass.
    provider = _MapSearchProvider({"Q1": [SUPPORTIVE_RESULT]})
    run = ResearchRun(question="Does generative AI improve developer productivity?")
    loop = ResearchLoop(llm=MockAdapter(), search_provider=provider, run=run, max_iterations=2)

    result = asyncio.run(loop.run(initial_queries=["Q1"]))

    assert len(result.iterations) >= 1
    assert result.iterations[0].decision in (
        IterationDecision.CONTINUE_RESEARCH.value, IterationDecision.MAX_ITERATIONS_REACHED.value,
    )
    assert result.quality_result.valid is False


# --------------------------------------------------------------------------
# 2. Follow-up query generation
# --------------------------------------------------------------------------

def test_followup_queries_are_generated_from_gaps():
    provider = _MapSearchProvider({
        "Q1": [SUPPORTIVE_RESULT],
        FOLLOWUP_QUERIES[0]: [CONTRADICTING_RESULT],
    })
    run = ResearchRun(question="Does generative AI improve developer productivity?")
    loop = ResearchLoop(llm=MockAdapter(), search_provider=provider, run=run, max_iterations=2)

    result = asyncio.run(loop.run(initial_queries=["Q1"]))

    events = [e for e in run.trace if e.type.value == "followup_queries_generated"]
    assert events, "expected at least one FOLLOWUP_QUERIES_GENERATED event"
    generated = events[0].data["queries"]
    assert generated  # non-empty
    assert "Q1" not in generated  # never just repeats the original query
    assert len(result.iterations) == 2


# --------------------------------------------------------------------------
# 3. Maximum iterations
# --------------------------------------------------------------------------

def test_maximum_iterations_are_respected():
    # Impossible-to-satisfy threshold -> the loop must still stop at the cap.
    provider = _MapSearchProvider({q: [SUPPORTIVE_RESULT] for q in ["Q1", *FOLLOWUP_QUERIES]})
    run = ResearchRun(question="q")
    loop = ResearchLoop(llm=MockAdapter(), search_provider=provider, run=run, max_iterations=2)
    import src.engine.research_loop as rl
    orig = rl.research_quality_validator

    class _NeverValid(ResearchQualityValidator):
        def validate(self, *a, **k):
            r = orig.validate(*a, **k)
            r.valid = False
            r.errors = r.errors or ["forced invalid for test"]
            return r

    rl.research_quality_validator = _NeverValid()
    try:
        result = asyncio.run(loop.run(initial_queries=["Q1"]))
    finally:
        rl.research_quality_validator = orig

    assert len(result.iterations) == 2
    assert result.final_decision == IterationDecision.MAX_ITERATIONS_REACHED


# --------------------------------------------------------------------------
# 4. Deduplication and accumulation
# --------------------------------------------------------------------------

def test_duplicate_urls_are_skipped_within_and_across_iterations():
    provider = _MapSearchProvider({
        "Q1": [SUPPORTIVE_RESULT],
        "Q2": [DUPLICATE_OF_A],  # same URL as Q1's result
        FOLLOWUP_QUERIES[0]: [CONTRADICTING_RESULT],
        FOLLOWUP_QUERIES[2]: [DUPLICATE_OF_A],  # same URL again, from a later iteration
    })
    run = ResearchRun(question="q")
    loop = ResearchLoop(llm=MockAdapter(), search_provider=provider, run=run, max_iterations=2)

    result = asyncio.run(loop.run(initial_queries=["Q1", "Q2"]))

    assert result.iterations[0].new_sources == 1
    assert result.iterations[0].duplicate_sources == 1
    urls = [s.url for s in result.sources]
    assert len(urls) == len(set(urls))  # no duplicate Source objects anywhere in the accumulated result


def test_evidence_accumulates_between_iterations():
    provider = _MapSearchProvider({
        "Q1": [SUPPORTIVE_RESULT],
        FOLLOWUP_QUERIES[0]: [CONTRADICTING_RESULT],
    })
    run = ResearchRun(question="q")
    loop = ResearchLoop(llm=MockAdapter(), search_provider=provider, run=run, max_iterations=2)

    result = asyncio.run(loop.run(initial_queries=["Q1"]))

    assert result.iterations[0].sources_found == 1
    assert result.iterations[1].sources_found == 2  # cumulative, iteration 1's source is still there
    assert len(result.evidence) == 2
    assert len(result.sources) == 2


# --------------------------------------------------------------------------
# 5. Quality re-evaluated each iteration, and gaps surface through the loop
# --------------------------------------------------------------------------

def test_quality_reevaluated_after_each_iteration():
    provider = _MapSearchProvider({
        "Q1": [SUPPORTIVE_RESULT],
        FOLLOWUP_QUERIES[0]: [CONTRADICTING_RESULT],
    })
    run = ResearchRun(question="q")
    loop = ResearchLoop(llm=MockAdapter(), search_provider=provider, run=run, max_iterations=2)

    result = asyncio.run(loop.run(initial_queries=["Q1"]))

    assert result.iterations[0].quality_result["evidence_count"] == 1
    assert result.iterations[1].quality_result["evidence_count"] == 2


def test_research_gap_identified_events_recorded():
    provider = _MapSearchProvider({"Q1": [SUPPORTIVE_RESULT]})
    run = ResearchRun(question="q")
    loop = ResearchLoop(llm=MockAdapter(), search_provider=provider, run=run, max_iterations=1)

    asyncio.run(loop.run(initial_queries=["Q1"]))

    gap_events = [e for e in run.trace if e.type.value == "research_gap_identified"]
    assert gap_events  # insufficient sources/evidence gap must have been identified


# --------------------------------------------------------------------------
# 6. Failure handling
# --------------------------------------------------------------------------

def test_llm_invalid_output_for_followups_is_handled_gracefully():
    provider = _MapSearchProvider({"Q1": [SUPPORTIVE_RESULT]})
    run = ResearchRun(question="q")
    loop = ResearchLoop(llm=_FollowupBreakingLLM(), search_provider=provider, run=run, max_iterations=3)

    result = asyncio.run(loop.run(initial_queries=["Q1"]))

    # Can't generate follow-ups -> loop stops early rather than crashing or looping blindly.
    assert result.final_decision == IterationDecision.MAX_ITERATIONS_REACHED
    assert len(result.iterations) == 1


def test_search_failure_on_one_query_does_not_crash_the_run():
    provider = _MapSearchProvider(
        {"Q2": [SUPPORTIVE_RESULT]}, fail_queries={"Q1"},
    )
    run = ResearchRun(question="q")
    loop = ResearchLoop(llm=MockAdapter(), search_provider=provider, run=run, max_iterations=1)

    result = asyncio.run(loop.run(initial_queries=["Q1", "Q2"]))

    assert len(result.sources) == 1  # Q2's result still made it through
    failed_events = [e for e in run.trace if "failed" in e.title.lower()]
    assert failed_events


def test_browser_failure_falls_back_to_search_snippet(monkeypatch):
    provider = _NonFullContentSearchProvider({"Q1": [SUPPORTIVE_RESULT]})
    run = ResearchRun(question="q")
    loop = ResearchLoop(llm=MockAdapter(), search_provider=provider, run=run, max_iterations=1)

    def _raise_browser_error(url):
        raise BrowserError("simulated browser failure")

    monkeypatch.setattr(research_loop_module.safe_browser, "fetch_page", _raise_browser_error)

    result = asyncio.run(loop.run(initial_queries=["Q1"]))

    assert len(result.sources) == 1  # fell back to the search snippet instead of crashing
    assert result.evidence[0].passage  # snippet content still captured


# --------------------------------------------------------------------------
# 7. Reuses Phase 5 validator; no fabricated metrics
# --------------------------------------------------------------------------

def test_reuses_the_existing_phase5_quality_validator():
    from src.quality.validator import research_quality_validator as phase5_singleton
    assert research_loop_module.research_quality_validator is phase5_singleton


def test_actual_source_counts_are_never_fabricated():
    provider = _MapSearchProvider({"Q1": []})  # zero results
    run = ResearchRun(question="q")
    loop = ResearchLoop(llm=MockAdapter(), search_provider=provider, run=run, max_iterations=1)

    result = asyncio.run(loop.run(initial_queries=["Q1"]))

    assert result.iterations[0].sources_found == 0
    assert result.iterations[0].evidence_count == 0
    assert result.iterations[0].claim_count == 0
    assert result.quality_result.source_count == 0


# --------------------------------------------------------------------------
# 8. Max-iteration result is marked incomplete in the final report
# --------------------------------------------------------------------------

def test_max_iterations_report_is_clearly_marked_incomplete():
    run = ResearchRun(question="q")
    run.research_decision = IterationDecision.MAX_ITERATIONS_REACHED.value
    run.quality_result = {}
    report = ResearchReportLLM(answer="Some answer.", key_findings=[], limitations=[])

    answer = orchestrator._format_answer(run, report, [], [])

    assert "maximum number of iterations" in answer
    assert "not fully verified" in answer.lower() or "preliminary" in answer.lower()


def test_complete_report_has_no_incomplete_disclaimer():
    run = ResearchRun(question="q")
    run.research_decision = IterationDecision.COMPLETE.value
    run.quality_result = {}
    report = ResearchReportLLM(answer="Some answer.", key_findings=[], limitations=[])

    answer = orchestrator._format_answer(run, report, [], [])

    assert "maximum number of iterations" not in answer


# --------------------------------------------------------------------------
# 9. Memory receives only the final research result
# --------------------------------------------------------------------------

def test_memory_receives_only_final_result_not_per_iteration(monkeypatch):
    calls = []
    monkeypatch.setattr(memory_manager, "extract_and_store", lambda run: (calls.append(run), [])[1])

    provider = _MapSearchProvider({q: [SUPPORTIVE_RESULT] for q in ["What direct evidence addresses the question?",
                                                                     "What benchmarks or studies quantify the effect?",
                                                                     "What risks or limitations are documented?",
                                                                     *FOLLOWUP_QUERIES]})
    monkeypatch.setattr("src.engine.orchestrator.get_search_provider", lambda: provider)

    run = ResearchRun(question="Does generative AI improve developer productivity?")
    store.save_run(run)
    asyncio.run(orchestrator.execute_run(run.run_id))

    assert len(calls) <= 1  # extract_and_store called at most once for the whole run, never per-iteration
