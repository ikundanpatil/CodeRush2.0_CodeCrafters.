"""ConversationService: the backend-side context that makes follow-ups work
without relying only on frontend state (Part C's core requirement).

Reuses the existing research pipeline entirely -- every research action a
conversation takes is just constructing a ResearchRun and letting the
existing orchestrator.execute_run handle it (the exact same path
POST /api/research already uses), never a second research engine.
"""

from datetime import datetime, timezone
from typing import Callable, Optional, Tuple

from src.conversation.intents import ConversationIntent, resolve_intent
from src.conversation.models import ConversationMessage, ConversationSession, MessageRole
from src.conversation.store import ConversationStore, conversation_store
from src.llm.adapter import get_llm_adapter
from src.llm.base import LLMAdapter, LLMError
from src.llm.providers.mock import MockAdapter
from src.models.schemas import ResearchRun, RunStatus
from src.storage.store import store as research_store

_TERMINAL = (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED)
_RESEARCH_INTENTS = (ConversationIntent.NEW_RESEARCH, ConversationIntent.FOLLOW_UP, ConversationIntent.FIND_MORE_EVIDENCE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationService:
    def __init__(self, store: Optional[ConversationStore] = None):
        self.store = store or conversation_store

    def _get_llm(self) -> LLMAdapter:
        try:
            return get_llm_adapter()
        except LLMError:
            return MockAdapter()

    def _start_research(self, session: ConversationSession, question: str, schedule_research: Callable[[str], None]) -> ResearchRun:
        run = ResearchRun(question=question)
        run.conversation_session_id = session.session_id
        research_store.save_run(run)
        schedule_research(run.run_id)
        return run

    def _summarize(self, run: Optional[ResearchRun]) -> str:
        if not run or not run.report_key_findings:
            return "I don't have findings to summarize yet -- the research may still be in progress."
        return "Here's a summary of what I found: " + " ".join(run.report_key_findings[:3])

    def _compare(self, run: Optional[ResearchRun]) -> str:
        if not run or not run.verification_result:
            return "I don't have enough verified findings yet to compare."
        v = run.verification_result
        supported = [c["claim_text"] for c in v.get("verified_claims", [])]
        contradicted = [c["claim_text"] for c in v.get("contradicted_claims", [])]
        parts = []
        if supported:
            parts.append("Supporting findings: " + "; ".join(supported[:3]) + ".")
        if contradicted:
            parts.append("Conflicting findings: " + "; ".join(contradicted[:3]) + ".")
        return " ".join(parts) if parts else "I don't have both supporting and conflicting findings to compare yet."

    async def create_session(self, message: str, schedule_research: Callable[[str], None]) -> ConversationSession:
        session = ConversationSession()
        session.messages.append(ConversationMessage(role=MessageRole.USER, content=message))

        llm = self._get_llm()
        intent, question = await resolve_intent(message, None, [], llm)
        if intent not in _RESEARCH_INTENTS:
            # A brand-new session has no topic yet -- any opener is treated
            # as the start of new research, using the raw message.
            intent, question = ConversationIntent.NEW_RESEARCH, message

        run = self._start_research(session, question, schedule_research)
        session.topic = question
        session.active_run_id = run.run_id
        session.messages.append(ConversationMessage(
            role=MessageRole.ASSISTANT, related_run_id=run.run_id, intent=intent.value,
            content=f"Sure, I'll research: {question}",
        ))
        session.updated_at = _now()
        return self.store.save(session)

    async def add_message(
        self, session_id: str, message: str, schedule_research: Callable[[str], None],
    ) -> Tuple[Optional[ConversationSession], str]:
        session = self.store.get(session_id)
        if session is None:
            return None, "not_found"

        session.messages.append(ConversationMessage(role=MessageRole.USER, content=message))

        llm = self._get_llm()
        intent, question = await resolve_intent(message, session.topic, session.messages[:-1], llm)
        active_run = research_store.get_run(session.active_run_id) if session.active_run_id else None

        if intent == ConversationIntent.STOP:
            if active_run and active_run.status not in _TERMINAL:
                active_run.cancel_requested = True
                research_store.save_run(active_run)
                reply = "Okay, I've stopped the current research."
            else:
                reply = "There's no active research to stop."

        elif intent in _RESEARCH_INTENTS:
            run = self._start_research(session, question, schedule_research)
            session.active_run_id = run.run_id
            if intent == ConversationIntent.NEW_RESEARCH:
                session.topic = question
            reply = f"Sure, I'll research: {question}"

        elif intent == ConversationIntent.SUMMARIZE:
            reply = self._summarize(active_run)

        elif intent == ConversationIntent.COMPARE:
            reply = self._compare(active_run)

        elif intent == ConversationIntent.GENERATE_PDF:
            if active_run and active_run.status == RunStatus.COMPLETED:
                reply = f"Your PDF report is ready: /api/research/{active_run.run_id}/report/pdf"
            else:
                reply = "I don't have a completed research run yet to generate a PDF from."

        elif intent == ConversationIntent.READ_ANSWER:
            reply = active_run.answer if (active_run and active_run.answer) else "There's no answer yet to read."

        else:  # EMPTY
            reply = "I didn't catch a question -- could you rephrase that?"

        session.messages.append(ConversationMessage(
            role=MessageRole.ASSISTANT, content=reply, related_run_id=session.active_run_id, intent=intent.value,
        ))
        session.updated_at = _now()
        self.store.save(session)
        return session, intent.value

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        return self.store.get(session_id)

    def list_sessions(self):
        return self.store.list_all()

    def delete_session(self, session_id: str) -> bool:
        return self.store.delete(session_id)


conversation_service = ConversationService()
