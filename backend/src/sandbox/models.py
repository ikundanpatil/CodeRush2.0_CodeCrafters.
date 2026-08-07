"""Phase 5 sandbox result models. `SandboxResult` is the single structured
return type of every `Sandbox.execute()` call, whichever provider (Docker,
Mock) produced it -- callers never branch on provider-specific shapes."""

import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SandboxStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"
    UNSUPPORTED = "unsupported"
    SANDBOX_UNAVAILABLE = "sandbox_unavailable"


class SandboxResult(BaseModel):
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: SandboxStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    duration_ms: int = 0
    timed_out: bool = False
    resource_limited: bool = False
    language: str = "python"

    @property
    def succeeded(self) -> bool:
        return self.status == SandboxStatus.SUCCESS
