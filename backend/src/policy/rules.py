"""Deterministic policy rules: hard safety limits and the self-evolution
field allowlist. Nothing in this file calls an LLM or depends on one --
security-critical decisions must be reproducible from config alone.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, Set

from src.policy.models import PolicyRisk

# --------------------------------------------------------------------------
# Self-evolution boundary: an explicit allowlist, not a denylist. Anything
# not in this set is rejected, no matter what it's named or how harmless it
# looks. This must stay exactly equal to StrategyParams's field names
# (backend/src/evolution/models.py) -- test_phase8_policy.py asserts that.
# --------------------------------------------------------------------------
ALLOWED_EVOLUTION_FIELDS: Set[str] = frozenset({
    "min_sources",
    "min_evidence",
    "min_supported_claims",
    "max_iterations",
    "max_results_per_query",
    "max_sources_per_iteration",
})


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


# --------------------------------------------------------------------------
# Hard safety limits. An evolved/applied strategy may operate at or below
# these; it can never exceed them, regardless of what the mutator or an
# operator's env config proposes for the strategy itself.
# --------------------------------------------------------------------------
def max_allowed_research_iterations() -> int:
    return _env_int("MAX_ALLOWED_RESEARCH_ITERATIONS", 3)


def max_allowed_results_per_query() -> int:
    return _env_int("MAX_ALLOWED_RESULTS_PER_QUERY", 20)


def max_allowed_sources_per_iteration() -> int:
    return _env_int("MAX_ALLOWED_SOURCES_PER_ITERATION", 20)


def max_allowed_sandbox_timeout() -> int:
    return _env_int("MAX_ALLOWED_SANDBOX_TIMEOUT", 30)


def max_allowed_sandbox_memory() -> str:
    return os.getenv("MAX_ALLOWED_SANDBOX_MEMORY", "256m")


def max_allowed_sandbox_cpu() -> float:
    return _env_float("MAX_ALLOWED_SANDBOX_CPU", 0.5)


def policy_engine_enabled() -> bool:
    return os.getenv("POLICY_ENGINE_ENABLED", "true").strip().lower() != "false"


def safety_limits() -> Dict[str, Any]:
    """Snapshot of the current hard limits, safe to expose over the API."""
    return {
        "max_allowed_research_iterations": max_allowed_research_iterations(),
        "max_allowed_results_per_query": max_allowed_results_per_query(),
        "max_allowed_sources_per_iteration": max_allowed_sources_per_iteration(),
        "max_allowed_sandbox_timeout": max_allowed_sandbox_timeout(),
        "max_allowed_sandbox_memory": max_allowed_sandbox_memory(),
        "max_allowed_sandbox_cpu": max_allowed_sandbox_cpu(),
    }


def default_safe_strategy_params() -> Dict[str, int]:
    """A conservative strategy, clamped within the current hard limits.

    Used as a fallback if a strategy that somehow fails policy validation is
    ever loaded for a real run (defense in depth -- normally unreachable
    since only policy-approved strategies can become champion).
    """
    return {
        "min_sources": 3,
        "min_evidence": 3,
        "min_supported_claims": 1,
        "max_iterations": min(3, max_allowed_research_iterations()),
        "max_results_per_query": min(4, max_allowed_results_per_query()),
        "max_sources_per_iteration": min(5, max_allowed_sources_per_iteration()),
    }


@dataclass
class StrategyValidationResult:
    ok: bool
    reason: str
    risk: PolicyRisk


def validate_strategy_candidate(candidate: Dict[str, Any]) -> StrategyValidationResult:
    """The 3-stage pipeline: schema (allowlist) -> bounds -> pass/fail.

    `candidate` is a plain dict, not a StrategyParams -- this must be able to
    reject payloads that don't even match the schema (unknown/extra fields,
    wrong types), which is exactly the shape an adversarial proposal takes.
    """
    if not isinstance(candidate, dict):
        return StrategyValidationResult(
            False, "Strategy payload must be an object of approved fields.", PolicyRisk.HIGH,
        )

    # -- 1. schema validation: explicit allowlist, not a denylist ----------
    candidate_fields = set(candidate.keys())
    unknown = candidate_fields - ALLOWED_EVOLUTION_FIELDS
    if unknown:
        return StrategyValidationResult(
            False,
            f"Strategy contains fields outside the approved allowlist: {sorted(unknown)}.",
            PolicyRisk.HIGH,
        )
    missing = ALLOWED_EVOLUTION_FIELDS - candidate_fields
    if missing:
        return StrategyValidationResult(
            False,
            f"Strategy is missing required field(s): {sorted(missing)}.",
            PolicyRisk.MEDIUM,
        )
    for field in ALLOWED_EVOLUTION_FIELDS:
        value = candidate[field]
        if isinstance(value, bool) or not isinstance(value, int):
            return StrategyValidationResult(
                False, f"Field '{field}' must be an integer.", PolicyRisk.HIGH,
            )

    # -- 2. bounds validation ------------------------------------------------
    if candidate["min_sources"] <= 0 or candidate["min_evidence"] <= 0 or candidate["min_supported_claims"] <= 0:
        return StrategyValidationResult(
            False, "Strategy quality thresholds must be positive.", PolicyRisk.MEDIUM,
        )

    if candidate["max_iterations"] <= 0:
        return StrategyValidationResult(
            False,
            "Strategy exceeds global safety limit. max_iterations must remain positive "
            "-- the iteration limit can never be removed.",
            PolicyRisk.CRITICAL,
        )
    if candidate["max_iterations"] > max_allowed_research_iterations():
        return StrategyValidationResult(
            False,
            f"Strategy exceeds global safety limit. max_iterations={candidate['max_iterations']} "
            f"> allowed {max_allowed_research_iterations()}.",
            PolicyRisk.CRITICAL,
        )

    if candidate["max_results_per_query"] <= 0 or candidate["max_results_per_query"] > max_allowed_results_per_query():
        return StrategyValidationResult(
            False,
            f"Strategy exceeds global safety limit. max_results_per_query="
            f"{candidate['max_results_per_query']} > allowed {max_allowed_results_per_query()}.",
            PolicyRisk.HIGH,
        )

    if (
        candidate["max_sources_per_iteration"] <= 0
        or candidate["max_sources_per_iteration"] > max_allowed_sources_per_iteration()
    ):
        return StrategyValidationResult(
            False,
            f"Strategy exceeds global safety limit. max_sources_per_iteration="
            f"{candidate['max_sources_per_iteration']} > allowed {max_allowed_sources_per_iteration()}.",
            PolicyRisk.HIGH,
        )

    # -- 3. policy validation (allowlist + bounds both satisfied) ----------
    return StrategyValidationResult(
        True, "Strategy is within the approved allowlist and safety bounds.", PolicyRisk.LOW,
    )
