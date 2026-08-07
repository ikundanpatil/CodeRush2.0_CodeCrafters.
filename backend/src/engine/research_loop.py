"""Phase 6 autonomous research loop.

Turns the Phase 1-5 sequential pipeline (search -> browse -> evidence graph
-> quality check) into a bounded iterative loop: after each iteration the
existing Phase 5 `ResearchQualityValidator` decides, deterministically,
whether the run has "enough evidence" to answer the question. If not, a
Phase 6 gap analysis (src/engine/research_gap.py) explains *why*, the LLM
adapter is used to turn that gap into targeted follow-up queries, and the
loop searches again -- accumulating evidence rather than discarding it.

Reuses, unchanged: LLMAdapter, SearchProvider, safe_browser, security_guard,
build_evidence_graph (Phase 4), research_quality_validator (Phase 5). This
module owns none of those concerns; it only owns the iteration control flow.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from src.browser.base import BrowserError
from src.browser.safe_browser import safe_browser
from src.evidence.graph import EvidenceGraph
from src.evidence.graph_builder import build_evidence_graph
from src.evidence.store import EvidenceStore, get_evidence_store
from src.engine.research_gap import ResearchGap, analyze_gaps
from src.llm.base import LLMAdapter
from src.llm.structured import generate_structured
from src.models.evidence import Claim
from src.models.schemas import AgentEvent, EventType, EvidenceRecord, ResearchRun, Source
from src.quality.models import ResearchQualityResult
from src.quality.validator import ResearchQualityValidator, research_quality_validator
from src.search.base import SearchError, SearchProvider
from src.security.guard import security_guard

DEFAULT_MAX_ITERATIONS = 3
MAX_RESULTS_PER_QUERY = 4
MAX_SOURCES_PER_ITERATION = 5
MAX_PASSAGE_CHARS = 1500
MAX_FOLLOWUP_QUERIES = 4


def _max_iterations() -> int:
    raw = os.getenv("MAX_RESEARCH_ITERATIONS")
    if not raw or not raw.strip():
        return DEFAULT_MAX_ITERATIONS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_ITERATIONS
    return value if value > 0 else DEFAULT_MAX_ITERATIONS


def _clip(text: str, limit: int = MAX_PASSAGE_CHARS) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


class IterationDecision(str, Enum):
    CONTINUE_RESEARCH = "continue_research"
    COMPLETE = "complete"
    FAILED = "failed"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"


class FollowUpQueryPlan(BaseModel):
    """Structured LLM output for targeted follow-up search queries."""
    research_gap: str = Field(min_length=1)
    queries: List[str] = Field(min_length=1)
    reason: str = ""


class ResearchIteration(BaseModel):
    iteration_number: int
    queries: List[str] = Field(default_factory=list)
    sources_found: int = 0
    new_sources: int = 0
    duplicate_sources: int = 0
    evidence_count: int = 0
    claim_count: int = 0
    quality_result: dict = Field(default_factory=dict)
    gaps: List[dict] = Field(default_factory=list)
    decision: str
    reason: str


@dataclass
class ResearchLoopResult:
    iterations: List[ResearchIteration]
    final_decision: IterationDecision
    sources: List[Source]
    evidence: List[EvidenceRecord]
    claims: List[Claim] = field(default_factory=list)
    graph: Optional[EvidenceGraph] = None
    quality_result: Optional[ResearchQualityResult] = None


class ResearchLoop:
    """Bounded, quality-driven autonomous research loop for a single run.

    Holds the `ResearchRun` directly (same convention as
    `ResearchOrchestrator`'s own private helpers) so it can append AgentEvents
    and populate `run.sources`/`run.evidence`/`run.security_events` live, the
    same way the rest of the pipeline already does.
    """

    def __init__(
        self,
        llm: LLMAdapter,
        search_provider: SearchProvider,
        run: ResearchRun,
        max_iterations: Optional[int] = None,
        quality_validator: Optional[ResearchQualityValidator] = None,
        max_results_per_query: Optional[int] = None,
        max_sources_per_iteration: Optional[int] = None,
    ):
        self.llm = llm
        self.search_provider = search_provider
        self.research_run = run
        self.max_iterations = max_iterations if max_iterations is not None else _max_iterations()
        self.quality_validator = quality_validator or research_quality_validator
        self.max_results_per_query = max_results_per_query or MAX_RESULTS_PER_QUERY
        self.max_sources_per_iteration = max_sources_per_iteration or MAX_SOURCES_PER_ITERATION
        self.seen_urls: Set[str] = set()

    def _emit(self, step: str, event_type: EventType, title: str, message: str, data: Optional[dict] = None):
        self.research_run.trace.append(AgentEvent(
            run_id=self.research_run.run_id, step=step, type=event_type,
            title=title, message=message, data=data,
        ))

    async def run(self, initial_queries: List[str]) -> ResearchLoopResult:
        all_sources: List[Source] = []
        all_evidences: List[EvidenceRecord] = []
        iterations: List[ResearchIteration] = []
        claims: List[Claim] = []
        graph = EvidenceGraph(research_run_id=self.research_run.run_id)
        quality_result: Optional[ResearchQualityResult] = None
        queries = list(initial_queries) or [self.research_run.question]
        final_decision = IterationDecision.FAILED

        for iteration_number in range(1, self.max_iterations + 1):
            self._emit(
                "Research Loop", EventType.RESEARCH_ITERATION_STARTED,
                f"Research Iteration {iteration_number} Started",
                f"Searching {len(queries)} quer{'y' if len(queries) == 1 else 'ies'} for iteration {iteration_number}.",
                {"iteration": iteration_number, "queries": queries},
            )

            try:
                new_sources, new_evidences, duplicate_count = await self._search_iteration(queries)
            except Exception as e:
                self._emit(
                    "Research Loop", EventType.RESEARCH_LOOP_DECISION,
                    "Research Iteration Failed",
                    f"Iteration {iteration_number} failed unexpectedly: {e}. Stopping the loop gracefully.",
                    {"iteration": iteration_number, "error": str(e)},
                )
                final_decision = IterationDecision.FAILED
                break

            all_sources.extend(new_sources)
            all_evidences.extend(new_evidences)

            try:
                graph, claims = await self._build_graph(all_evidences, all_sources)
                quality_result = self.quality_validator.validate(
                    self.research_run.question, all_sources, all_evidences, claims, graph,
                )
            except Exception as e:
                self._emit(
                    "Research Loop", EventType.QUALITY_VALIDATION_FAILED,
                    "Quality Validation Failed",
                    f"Quality validation could not complete for iteration {iteration_number}: {e}",
                    {"iteration": iteration_number, "error": str(e)},
                )
                quality_result = quality_result or self.quality_validator.validate(
                    self.research_run.question, all_sources, all_evidences, claims, graph,
                )

            gaps = analyze_gaps(quality_result, claims, all_sources)
            for gap in gaps:
                self._emit(
                    "Research Loop", EventType.RESEARCH_GAP_IDENTIFIED,
                    f"Research Gap: {gap.type.value}",
                    gap.description,
                    {"iteration": iteration_number, "type": gap.type.value, "priority": gap.priority.value,
                     "related_claim_ids": gap.related_claim_ids},
                )

            if quality_result.valid:
                decision = IterationDecision.COMPLETE
                reason = "Research quality requirements were satisfied."
            elif iteration_number >= self.max_iterations:
                decision = IterationDecision.MAX_ITERATIONS_REACHED
                reason = (
                    f"Reached the maximum of {self.max_iterations} iteration(s) with "
                    f"{len(quality_result.errors)} unresolved quality error(s)."
                )
            else:
                decision = IterationDecision.CONTINUE_RESEARCH
                reason = (
                    f"{len(quality_result.errors)} quality error(s) remain: "
                    + "; ".join(quality_result.errors[:3])
                ) if quality_result.errors else "Quality requirements not yet satisfied."

            iterations.append(ResearchIteration(
                iteration_number=iteration_number,
                queries=queries,
                sources_found=len(all_sources),
                new_sources=len(new_sources),
                duplicate_sources=duplicate_count,
                evidence_count=len(all_evidences),
                claim_count=len(claims),
                quality_result=quality_result.model_dump(),
                gaps=[g.model_dump() for g in gaps],
                decision=decision.value,
                reason=reason,
            ))

            self._emit(
                "Research Loop", EventType.RESEARCH_ITERATION_COMPLETED,
                f"Research Iteration {iteration_number} Completed",
                f"Iteration {iteration_number}: {len(all_sources)} source(s), {len(all_evidences)} "
                f"evidence item(s), {len(claims)} claim(s). Quality valid: {quality_result.valid}.",
                {"iteration": iteration_number, "source_count": len(all_sources),
                 "evidence_count": len(all_evidences), "claim_count": len(claims)},
            )
            self._emit(
                "Research Loop", EventType.RESEARCH_LOOP_DECISION,
                "Research Loop Decision",
                f"Decision for iteration {iteration_number}: {decision.value} -- {reason}",
                {"iteration": iteration_number, "decision": decision.value, "reason": reason},
            )

            final_decision = decision
            if decision != IterationDecision.CONTINUE_RESEARCH:
                if decision == IterationDecision.MAX_ITERATIONS_REACHED:
                    self._emit(
                        "Research Loop", EventType.MAX_ITERATIONS_REACHED,
                        "Maximum Iterations Reached",
                        f"Stopped after {iteration_number} iteration(s) without satisfying all quality requirements.",
                        {"iteration": iteration_number, "max_iterations": self.max_iterations},
                    )
                break

            new_queries = await self._generate_followup_queries(gaps, queries, iteration_number)
            if not new_queries:
                final_decision = IterationDecision.MAX_ITERATIONS_REACHED
                self._emit(
                    "Research Loop", EventType.MAX_ITERATIONS_REACHED,
                    "Research Stopped Early",
                    "Unable to generate further follow-up queries; stopping research early rather than looping blindly.",
                    {"iteration": iteration_number},
                )
                break
            queries = new_queries

        # Persist the final accumulated graph to the shared evidence store so
        # the Phase 4 evidence API reflects exactly one, final generation of
        # claims/evidence for this run (intermediate iterations use a scratch
        # store so their now-superseded claims never leak into that API).
        try:
            graph, claims = await self._build_graph(all_evidences, all_sources, store=get_evidence_store())
            quality_result = self.quality_validator.validate(
                self.research_run.question, all_sources, all_evidences, claims, graph,
            )
        except Exception as e:
            self._emit(
                "Research Loop", EventType.QUALITY_VALIDATION_FAILED,
                "Final Quality Persistence Failed",
                f"Could not persist the final evidence graph: {e}",
                {"error": str(e)},
            )

        self._emit(
            "Research Loop", EventType.RESEARCH_LOOP_COMPLETED,
            "Research Loop Completed",
            f"Completed after {len(iterations)} iteration(s) with decision '{final_decision.value}': "
            f"{len(all_sources)} source(s), {len(all_evidences)} evidence item(s), {len(claims)} claim(s).",
            {"iterations": len(iterations), "decision": final_decision.value,
             "source_count": len(all_sources), "evidence_count": len(all_evidences), "claim_count": len(claims)},
        )

        return ResearchLoopResult(
            iterations=iterations,
            final_decision=final_decision,
            sources=all_sources,
            evidence=all_evidences,
            claims=claims,
            graph=graph,
            quality_result=quality_result,
        )

    # -- per-iteration search -------------------------------------------------

    async def _search_iteration(
        self, queries: List[str]
    ) -> Tuple[List[Source], List[EvidenceRecord], int]:
        """Search -> Safe Browser -> Prompt Injection Guard -> Evidence for one
        iteration's queries. Never processes a URL already seen in a prior
        iteration (or earlier in this one) -- `self.seen_urls` persists across
        the whole loop, not just this call."""
        run_id = self.research_run.run_id

        self._emit(
            "Searching", EventType.SEARCH_STARTED, "Web Search Started",
            f"Searching for {len(queries)} quer{'y' if len(queries) == 1 else 'ies'}.",
            {"queries": queries},
        )

        raw_results = []
        duplicate_count = 0
        for query in queries:
            try:
                results = await self.search_provider.search(query, max_results=self.max_results_per_query)
            except SearchError as e:
                self._emit(
                    "Searching", EventType.SEARCH_STARTED, "Search Query Failed",
                    f"Search for '{query}' failed: {e}", {"query": query, "error": str(e)},
                )
                continue
            for result in results:
                if result.url in self.seen_urls:
                    duplicate_count += 1
                    continue
                self.seen_urls.add(result.url)
                raw_results.append(result)
            if len(raw_results) >= self.max_sources_per_iteration:
                break

        sources: List[Source] = []
        evidences: List[EvidenceRecord] = []

        for result in raw_results[:self.max_sources_per_iteration]:
            page_text = result.content

            if not getattr(self.search_provider, "provides_full_content", False):
                self._emit(
                    "Browser", EventType.BROWSER_FETCH_STARTED, "Fetching Source",
                    f"Fetching '{result.url}' safely.", {"url": result.url},
                )
                try:
                    page = safe_browser.fetch_page(result.url)
                    page_text = page.text or result.content
                    self._emit(
                        "Browser", EventType.BROWSER_FETCH_COMPLETED, "Source Fetched",
                        f"Fetched '{result.url}' ({len(page_text)} chars).",
                        {"url": result.url, "truncated": page.truncated},
                    )
                except BrowserError as e:
                    self._emit(
                        "Browser", EventType.BROWSER_FETCH_FAILED, "Source Fetch Failed",
                        f"Could not safely fetch '{result.url}': {e}. Falling back to the search snippet.",
                        {"url": result.url, "error": str(e)},
                    )
                    page_text = result.content

            if not page_text:
                continue

            sanitized_content, sec_events = security_guard.scan_content(page_text, run_id)
            for sec_ev in sec_events:
                self.research_run.security_events.append(sec_ev)
                self._emit(
                    "Security Verification", EventType.PROMPT_INJECTION_DETECTED,
                    "Untrusted Prompt Injection Neutralized",
                    f"Detected prompt injection pattern: '{sec_ev.snippet}'. Content sanitized.",
                    {"action": sec_ev.action_taken, "snippet": sec_ev.snippet, "url": result.url},
                )

            passage = _clip(sanitized_content)
            evidence = EvidenceRecord(
                claim=f"Key observation from {result.title}",
                source_id="",
                source_title=result.title,
                source_url=result.url,
                passage=passage,
                confidence=max(0.5, min(0.95, result.score or 0.85)),
            )
            source = Source(
                title=result.title,
                url=result.url,
                publisher=result.source or "Web",
                published_at=None,
                description=_clip(sanitized_content, 300),
                evidence=[evidence],
            )
            evidence.source_id = source.id
            sources.append(source)
            evidences.append(evidence)

        self.research_run.sources = self.research_run.sources + sources
        self.research_run.evidence = self.research_run.evidence + evidences
        self.research_run.source_count = len(self.research_run.sources)

        self._emit(
            "Searching", EventType.SEARCH_COMPLETED, "Retrieved & Sanitized Sources",
            f"Gathered {len(sources)} new source(s) ({duplicate_count} duplicate URL(s) skipped).",
            {"new_source_count": len(sources), "duplicate_count": duplicate_count},
        )

        return sources, evidences, duplicate_count

    # -- evidence graph ---------------------------------------------------------

    async def _build_graph(
        self, evidences: List[EvidenceRecord], sources: List[Source],
        store: Optional[EvidenceStore] = None,
    ):
        def evidence_event_sink(event_type: str, title: str, message: str, data=None):
            self._emit("Evidence Graph", EventType(event_type), title, message, data)

        return await build_evidence_graph(
            self.llm, self.research_run.run_id, self.research_run.question, evidences, sources,
            store=store or EvidenceStore(), event_sink=evidence_event_sink,
        )

    # -- follow-up query generation ----------------------------------------------

    async def _generate_followup_queries(
        self, gaps: List[ResearchGap], previous_queries: List[str], iteration_number: int,
    ) -> List[str]:
        """Ask the LLM for targeted follow-up queries addressing the highest-
        priority research gaps. Never repeats the original query verbatim.
        Returns [] (never raises) if the LLM is unavailable or its structured
        output can't be validated after one retry -- callers treat that as
        "can't continue" and stop the loop gracefully."""
        if not gaps:
            return []

        top_gaps = gaps[:3]
        gap_text = "\n".join(f"- {g.type.value}: {g.description}" for g in top_gaps)
        tried_text = "\n".join(f"- {q}" for q in previous_queries) or "None."

        system_prompt = (
            "You are EvoResearch's follow-up research planner. TRUSTED INSTRUCTIONS: "
            "given the original research question and a list of identified research gaps, "
            "produce a single JSON object with keys: research_gap (string summarizing the "
            "primary gap being addressed), queries (array of 2-4 new, specific search query "
            "strings that target the identified gaps -- never a verbatim repeat of a "
            "previously tried query), and reason (string explaining why these queries were "
            "chosen). Respond with ONLY the JSON object -- no markdown fences, no commentary."
        )
        prompt = (
            f"Original research question: {self.research_run.question}\n\n"
            f"Research gaps identified after iteration {iteration_number}:\n{gap_text}\n\n"
            f"Queries already tried:\n{tried_text}\n\n"
            "Produce the follow-up query JSON now."
        )

        plan, error = await generate_structured(self.llm, system_prompt, prompt, FollowUpQueryPlan, retries=1)
        if plan is None:
            self._emit(
                "Research Loop", EventType.FOLLOWUP_QUERIES_GENERATED,
                "Follow-Up Query Generation Failed",
                f"Could not generate valid follow-up queries: {error}",
                {"iteration": iteration_number, "error": str(error)},
            )
            return []

        queries = [q for q in plan.queries if q and q.strip()][:MAX_FOLLOWUP_QUERIES]
        self._emit(
            "Research Loop", EventType.FOLLOWUP_QUERIES_GENERATED,
            "Follow-Up Queries Generated",
            f"Generated {len(queries)} follow-up quer{'y' if len(queries) == 1 else 'ies'} "
            f"targeting: {plan.research_gap}.",
            {"iteration": iteration_number, "queries": queries, "research_gap": plan.research_gap, "reason": plan.reason},
        )
        return queries
