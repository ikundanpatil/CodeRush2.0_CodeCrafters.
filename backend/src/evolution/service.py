"""Phase 7 self-evolution service: drives the full

    Research Strategy -> Research/Evaluate -> Improve Strategy ->
    Test New Strategy -> Compare -> Accept/Reject

cycle. Manually triggered (POST /api/strategy/evolve); never runs on its own.
"""

from datetime import datetime, timezone
from uuid import uuid4

from src.evolution.evaluator import run_benchmark
from src.evolution.models import EvolutionCycleResult, Strategy, StrategyStatus
from src.evolution.mutator import propose_mutation
from src.evolution.store import EvolutionStore, get_evolution_store
from src.llm.adapter import get_llm_adapter
from src.llm.base import LLMAdapter, LLMError
from src.llm.providers.mock import MockAdapter
from src.models.schemas import AgentEvent, EventType


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvolutionService:
    def __init__(self, store: EvolutionStore = None):
        self.store = store or get_evolution_store()

    def _get_llm(self) -> LLMAdapter:
        try:
            return get_llm_adapter()
        except LLMError:
            return MockAdapter()

    async def run_cycle(self) -> EvolutionCycleResult:
        cycle_id = str(uuid4())
        trace = []

        def emit(event_type: EventType, title: str, message: str, data=None):
            trace.append(AgentEvent(
                run_id=cycle_id, step="Evolution", type=event_type,
                title=title, message=message, data=data,
            ))

        llm = self._get_llm()

        # 1. Research Strategy
        baseline = self.store.get_champion()
        emit(
            EventType.EVOLUTION_CYCLE_STARTED, "Evolution Cycle Started",
            f"Evaluating champion strategy generation {baseline.generation} before proposing a mutation.",
            {"baseline_id": baseline.id, "generation": baseline.generation, "params": baseline.params.model_dump()},
        )

        # 2. Research + Evaluate (baseline)
        baseline_eval = await run_benchmark(baseline, llm)
        if baseline.score is None:
            baseline.score = baseline_eval.mean_score
            self.store.save(baseline)
        emit(
            EventType.EVOLUTION_BASELINE_EVALUATED, "Baseline Evaluated",
            f"Baseline strategy scored {baseline_eval.mean_score:.2f} across {len(baseline_eval.per_question)} benchmark question(s).",
            {"mean_score": baseline_eval.mean_score},
        )

        # 3. Improve Strategy
        candidate_params, reasoning = await propose_mutation(baseline, baseline_eval, llm)
        candidate = Strategy(
            generation=baseline.generation + 1,
            parent_id=baseline.id,
            params=candidate_params,
            status=StrategyStatus.CANDIDATE,
            reasoning=reasoning,
            created_at=_utc_now(),
        )
        emit(
            EventType.EVOLUTION_MUTATION_PROPOSED, "Strategy Mutation Proposed",
            f"Proposed generation {candidate.generation}: {reasoning}",
            {"params": candidate.params.model_dump(), "reasoning": reasoning},
        )

        # 4. Test New Strategy
        candidate_eval = await run_benchmark(candidate, llm)
        emit(
            EventType.EVOLUTION_CANDIDATE_EVALUATED, "Candidate Evaluated",
            f"Candidate strategy scored {candidate_eval.mean_score:.2f} across {len(candidate_eval.per_question)} benchmark question(s).",
            {"mean_score": candidate_eval.mean_score},
        )

        # 5. Compare + 6. Accept/Reject
        if candidate_eval.mean_score > baseline_eval.mean_score:
            candidate.status = StrategyStatus.ACCEPTED
            candidate.score = candidate_eval.mean_score
            candidate.accepted_at = _utc_now()
            self.store.save(candidate)

            baseline.status = StrategyStatus.SUPERSEDED
            self.store.save(baseline)

            decision = "accepted"
            reason = (
                f"Candidate scored {candidate_eval.mean_score:.2f} vs baseline "
                f"{baseline_eval.mean_score:.2f}; adopted as the new champion."
            )
            emit(EventType.EVOLUTION_ACCEPTED, "Candidate Accepted", reason, {"generation": candidate.generation})
        else:
            candidate.status = StrategyStatus.REJECTED
            candidate.score = candidate_eval.mean_score
            self.store.save(candidate)

            decision = "rejected"
            reason = (
                f"Candidate scored {candidate_eval.mean_score:.2f} vs baseline "
                f"{baseline_eval.mean_score:.2f}; champion unchanged."
            )
            emit(EventType.EVOLUTION_REJECTED, "Candidate Rejected", reason, {"generation": candidate.generation})

        emit(
            EventType.EVOLUTION_CYCLE_COMPLETED, "Evolution Cycle Completed",
            f"Cycle finished with decision '{decision}'.",
            {"decision": decision},
        )

        return EvolutionCycleResult(
            cycle_id=cycle_id,
            baseline=baseline,
            baseline_eval=baseline_eval,
            candidate=candidate,
            candidate_eval=candidate_eval,
            decision=decision,
            reason=reason,
            trace=trace,
        )


evolution_service = EvolutionService()
