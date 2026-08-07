"""Deterministic (with optional LLM assist) resolution of a conversation
message into an intent + (if research is needed) a self-contained
question. This is what makes "what are the disadvantages?" understood as
"what are the disadvantages of <the current topic>?" -- backend-side, real
session state, not a frontend illusion.

The LLM path is attempted first (asks it to rewrite the message using the
session's topic/history); if unavailable or its structured output doesn't
validate, a deterministic keyword classifier takes over -- the exact same
graceful-degradation pattern used throughout this codebase (Phase 6/7/8).
The default offline MockAdapter doesn't recognize this prompt shape, so it
always exercises the deterministic path, by design (same precedent as
src/evolution/mutator.py).
"""

import re
from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel

from src.conversation.models import ConversationMessage
from src.llm.base import LLMAdapter
from src.llm.structured import generate_structured


class ConversationIntent(str, Enum):
    NEW_RESEARCH = "new_research"
    FOLLOW_UP = "follow_up"
    FIND_MORE_EVIDENCE = "find_more_evidence"
    COMPARE = "compare"
    SUMMARIZE = "summarize"
    GENERATE_PDF = "generate_pdf"
    READ_ANSWER = "read_answer"
    STOP = "stop"
    EMPTY = "empty"


class _IntentProposal(BaseModel):
    action: str
    rewritten_question: str = ""
    reasoning: str = ""


_STOP_PATTERN = re.compile(r"\b(stop|cancel)\b", re.IGNORECASE)
_READ_PATTERN = re.compile(r"\bread\b", re.IGNORECASE)
_PDF_PATTERN = re.compile(r"\bpdf\b", re.IGNORECASE)
_SUMMARIZE_PATTERN = re.compile(r"\bsummar(y|ize|ise)\b", re.IGNORECASE)
_COMPARE_PATTERN = re.compile(r"\bcompare\b", re.IGNORECASE)
_MORE_EVIDENCE_PATTERN = re.compile(
    r"\b(more evidence|continue research|keep researching|dig deeper|go deeper|find more)\b", re.IGNORECASE,
)
_REFERENTIAL_PATTERN = re.compile(
    r"\b(it|this|that|these|those|its|the (disadvantages|advantages|risks|benefits|downsides|pros|cons|drawbacks))\b",
    re.IGNORECASE,
)

_VALID_ACTIONS = {i.value for i in ConversationIntent}


def _fallback_classify(message: str, has_active_topic: bool, topic: Optional[str]) -> Tuple[ConversationIntent, str]:
    if _STOP_PATTERN.search(message):
        return ConversationIntent.STOP, ""
    if _PDF_PATTERN.search(message):
        return ConversationIntent.GENERATE_PDF, ""
    if _READ_PATTERN.search(message):
        return ConversationIntent.READ_ANSWER, ""
    if _SUMMARIZE_PATTERN.search(message):
        return ConversationIntent.SUMMARIZE, ""
    if has_active_topic and _COMPARE_PATTERN.search(message):
        return ConversationIntent.COMPARE, ""
    if has_active_topic and _MORE_EVIDENCE_PATTERN.search(message):
        return ConversationIntent.FIND_MORE_EVIDENCE, message
    if has_active_topic and _REFERENTIAL_PATTERN.search(message):
        suffix = f" (regarding: {topic})" if topic else ""
        return ConversationIntent.FOLLOW_UP, f"{message.strip().rstrip('?')}{suffix}"
    return ConversationIntent.NEW_RESEARCH, message


async def resolve_intent(
    message: str, topic: Optional[str], recent_messages: List[ConversationMessage], llm: LLMAdapter,
) -> Tuple[ConversationIntent, str]:
    """Returns (intent, question) -- question is only meaningful for
    NEW_RESEARCH/FOLLOW_UP/FIND_MORE_EVIDENCE."""
    text = (message or "").strip()
    if not text:
        return ConversationIntent.EMPTY, ""

    has_active_topic = bool(topic)

    history_text = "\n".join(f"{m.role.value}: {m.content}" for m in recent_messages[-6:]) or "None."
    system_prompt = (
        "You are EvoResearch's conversation assistant. TRUSTED INSTRUCTIONS: given the current "
        "research topic (if any) and recent conversation history, classify the user's latest "
        "message into a single JSON object with keys: action (one of: new_research, follow_up, "
        "find_more_evidence, compare, summarize, generate_pdf, read_answer, stop, empty), "
        "rewritten_question (a self-contained research question -- only needed for new_research/"
        "follow_up/find_more_evidence, empty string otherwise), and reasoning (string). If the "
        "message clearly continues the current topic (e.g. asks about 'the disadvantages' of it), "
        "use follow_up and write a self-contained question that includes the topic. Respond with "
        "ONLY the JSON object -- no markdown fences, no commentary."
    )
    prompt = (
        f"Current topic: {topic or 'None (no active research session yet).'}\n\n"
        f"Recent conversation:\n{history_text}\n\n"
        f"User's latest message: {text}\n\n"
        "Produce the classification JSON now."
    )

    proposal, _error = await generate_structured(llm, system_prompt, prompt, _IntentProposal, retries=1)
    if proposal is not None and proposal.action in _VALID_ACTIONS:
        intent = ConversationIntent(proposal.action)
        question = proposal.rewritten_question.strip() or text
        return intent, question

    return _fallback_classify(text, has_active_topic, topic)
