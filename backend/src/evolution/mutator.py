"""Phase 7 "Improve Strategy" step.

Asks the LLM to propose a new `StrategyParams` given the current champion and
its benchmark evaluation, using the same `generate_structured` + graceful-
fallback pattern as the orchestrator's planning/report steps. If the LLM is
unavailable or returns output that doesn't validate, falls back to a small
deterministic heuristic driven by which quality checks actually failed --
never raises, never blocks a cycle.

Note: the default offline `MockAdapter` does not recognize this prompt shape
(it returns a plain non-JSON string for anything it doesn't special-case), so
running evolution cycles against the default mock provider always exercises
the deterministic fallback below. That is by design, not a bug -- a real LLM
provider produces smarter mutations, mock/offline mode still evolves via the
heuristic.
"""

from collections import Counter
from typing import Tuple

from pydantic import BaseModel, Field

from src.evolution.models import EvaluationResult, Strategy, StrategyParams
from src.llm.base import LLMAdapter
from src.llm.structured import generate_structured

MIN_BOUND = 1
MAX_THRESHOLD_BOUND = 10
MAX_ITERATIONS_BOUND = 6


class MutationProposal(BaseModel):
    min_sources: int = Field(ge=MIN_BOUND, le=MAX_THRESHOLD_BOUND)
    min_evidence: int = Field(ge=MIN_BOUND, le=MAX_THRESHOLD_BOUND)
    min_supported_claims: int = Field(ge=MIN_BOUND, le=MAX_THRESHOLD_BOUND)
    max_iterations: int = Field(ge=MIN_BOUND, le=MAX_ITERATIONS_BOUND)
    max_results_per_query: int = Field(ge=MIN_BOUND, le=MAX_THRESHOLD_BOUND)
    max_sources_per_iteration: int = Field(ge=MIN_BOUND, le=MAX_THRESHOLD_BOUND)
    reasoning: str = ""


def _failed_check_names(evaluation: EvaluationResult) -> Counter:
    counts = Counter()
    for question_result in evaluation.per_question:
        for check in question_result.quality.checks:
            if not check.passed:
                counts[check.name] += 1
    return counts


def _fallback_mutation(baseline: StrategyParams, baseline_eval: EvaluationResult) -> Tuple[StrategyParams, str]:
    failed = _failed_check_names(baseline_eval)
    params = baseline.model_copy()

    if failed["source_count"] or failed["evidence_count"]:
        params.max_iterations = min(MAX_ITERATIONS_BOUND, params.max_iterations + 1)
        params.max_sources_per_iteration = min(MAX_THRESHOLD_BOUND, params.max_sources_per_iteration + 1)
        return params, "Baseline often lacked enough sources/evidence; widening the research loop."

    if failed["supported_claims"]:
        params.max_iterations = min(MAX_ITERATIONS_BOUND, params.max_iterations + 1)
        return params, "Baseline often lacked supported claims; allowing more iterations to find support."

    any_errors_or_warnings = any(
        qr.quality.errors or qr.quality.warnings for qr in baseline_eval.per_question
    )
    if not any_errors_or_warnings:
        params.min_supported_claims = min(MAX_THRESHOLD_BOUND, params.min_supported_claims + 1)
        return params, "Baseline was clean across the benchmark; raising the bar for supported claims."

    return params, "Baseline already balanced; no mutation proposed."


async def propose_mutation(
    baseline: Strategy, baseline_eval: EvaluationResult, llm: LLMAdapter,
) -> Tuple[StrategyParams, str]:
    failed = _failed_check_names(baseline_eval)
    failed_text = "\n".join(f"- {name}: failed {count} time(s)" for name, count in failed.items()) or "None."

    system_prompt = (
        "You are EvoResearch's strategy-improvement assistant. TRUSTED INSTRUCTIONS: given the "
        "current research strategy parameters and which quality checks failed across a benchmark "
        "run, propose a single JSON object with keys: min_sources, min_evidence, "
        "min_supported_claims, max_iterations, max_results_per_query, max_sources_per_iteration "
        "(all integers between 1 and 10, max_iterations between 1 and 6), and reasoning (string). "
        "Make small, targeted adjustments -- never wild swings. Respond with ONLY the JSON object -- "
        "no markdown fences, no commentary."
    )
    prompt = (
        f"Current strategy parameters:\n{baseline.params.model_dump()}\n\n"
        f"Quality checks that failed across the benchmark:\n{failed_text}\n\n"
        f"Mean benchmark score: {baseline_eval.mean_score}\n\n"
        "Propose improved strategy parameters as JSON now."
    )

    proposal, _error = await generate_structured(llm, system_prompt, prompt, MutationProposal, retries=1)
    if proposal is None:
        return _fallback_mutation(baseline.params, baseline_eval)

    return (
        StrategyParams(
            min_sources=proposal.min_sources,
            min_evidence=proposal.min_evidence,
            min_supported_claims=proposal.min_supported_claims,
            max_iterations=proposal.max_iterations,
            max_results_per_query=proposal.max_results_per_query,
            max_sources_per_iteration=proposal.max_sources_per_iteration,
        ),
        proposal.reasoning or "LLM-proposed strategy adjustment.",
    )
