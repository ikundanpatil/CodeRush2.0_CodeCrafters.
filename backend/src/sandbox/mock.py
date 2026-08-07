"""Deterministic, offline sandbox. Required for the automated test suite,
which must never depend on a Docker daemon being available.

Does not use `eval`/`exec` and never actually runs the given code -- it
simulates one of the four sandbox outcomes (success, failed, timeout,
resource limit) deterministically, selected by looking for a marker
substring in `code`. This keeps scenarios fully controllable from a test
without any randomness or real subprocess execution.
"""

import os
import time
from typing import Optional

from src.sandbox.base import SUPPORTED_LANGUAGES, Sandbox
from src.sandbox.models import SandboxResult, SandboxStatus

DEFAULT_OUTPUT_LIMIT = 65536

FORCE_FAILURE_MARKER = "__SANDBOX_MOCK_FAIL__"
FORCE_TIMEOUT_MARKER = "__SANDBOX_MOCK_TIMEOUT__"
FORCE_RESOURCE_LIMIT_MARKER = "__SANDBOX_MOCK_RESOURCE_LIMIT__"


class MockSandbox(Sandbox):
    def __init__(self, output_limit: Optional[int] = None):
        self.output_limit = (
            output_limit if output_limit is not None
            else int(os.getenv("SANDBOX_OUTPUT_LIMIT", DEFAULT_OUTPUT_LIMIT))
        )

    async def execute(
        self, code: str, language: str = "python", timeout_seconds: Optional[int] = None
    ) -> SandboxResult:
        effective_timeout = timeout_seconds if timeout_seconds is not None else 10

        if language not in SUPPORTED_LANGUAGES:
            return SandboxResult(
                status=SandboxStatus.UNSUPPORTED,
                language=language,
                stderr=f"Language '{language}' is not supported by the sandbox MVP.",
            )

        if FORCE_TIMEOUT_MARKER in code:
            return SandboxResult(
                status=SandboxStatus.TIMEOUT,
                language=language,
                timed_out=True,
                duration_ms=effective_timeout * 1000,
                stderr=f"[mock sandbox] execution exceeded {effective_timeout}s and was killed (simulated).",
            )

        if FORCE_RESOURCE_LIMIT_MARKER in code:
            return SandboxResult(
                status=SandboxStatus.RESOURCE_LIMIT_EXCEEDED,
                language=language,
                resource_limited=True,
                exit_code=137,
                duration_ms=5,
                stderr="[mock sandbox] process was killed for exceeding the memory limit (simulated).",
            )

        if FORCE_FAILURE_MARKER in code:
            return SandboxResult(
                status=SandboxStatus.FAILED,
                language=language,
                exit_code=1,
                duration_ms=5,
                stdout="",
                stderr="[mock sandbox] simulated execution failure.",
            )

        start = time.monotonic()
        stdout = f"[mock sandbox] executed {len(code)} char(s) of {language} code:\n{code}"
        duration_ms = int((time.monotonic() - start) * 1000)
        return SandboxResult(
            status=SandboxStatus.SUCCESS,
            language=language,
            exit_code=0,
            duration_ms=duration_ms,
            stdout=stdout[: self.output_limit],
            stderr="",
        )
