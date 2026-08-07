"""Conversational research session domain models (Part C).

A ConversationSession maintains real backend-side context (topic, active
research run) across turns -- NOT just a frontend-only illusion of memory.
Every follow-up is resolved against this stored context, not re-derived
from scratch each time.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ConversationMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    related_run_id: Optional[str] = None
    intent: Optional[str] = None
    created_at: str = Field(default_factory=_now)


class ConversationSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: Optional[str] = None
    active_run_id: Optional[str] = None
    messages: List[ConversationMessage] = Field(default_factory=list)
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)
