"""Phase 7 self-evolution domain models.

A `Strategy` is a named bundle of the quality thresholds and research-loop
limits that are otherwise static env-var defaults (`src/quality/rules.py`,
`src/engine/research_loop.py`). Evolution proposes, tests, and accepts/rejects
new `StrategyParams` -- it never touches prompts, and every score here is
computed from a real `ResearchQualityResult` produced by the actual pipeline,
never invented.
"""

from enum import Enum
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from src.models.schemas import AgentEvent
from src.quality.models import ResearchQualityResult


def _uuid() -> str:
    return str(uuid4())


class StrategyParams(BaseModel):
    min_sources: int
    min_evidence: int
    min_supported_claims: int
    max_iterations: int
    max_results_per_query: int
    max_sources_per_iteration: int


class StrategyStatus(str, Enum):
    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class Strategy(BaseModel):
    id: str = Field(default_factory=_uuid)
    generation: int
    parent_id: Optional[str] = None
    params: StrategyParams
    status: StrategyStatus
    score: Optional[float] = None
    reasoning: str = ""
    created_at: str = ""
    accepted_at: Optional[str] = None


class BenchmarkQuestionResult(BaseModel):
    question: str
    quality: ResearchQualityResult
    score: float


class EvaluationResult(BaseModel):
    strategy_id: str
    per_question: List[BenchmarkQuestionResult] = Field(default_factory=list)
    mean_score: float


class EvolutionCycleResult(BaseModel):
    cycle_id: str = Field(default_factory=_uuid)
    baseline: Strategy
    baseline_eval: EvaluationResult
    candidate: Strategy
    candidate_eval: EvaluationResult
    decision: Literal["accepted", "rejected"]
    reason: str
    trace: List[AgentEvent] = Field(default_factory=list)
