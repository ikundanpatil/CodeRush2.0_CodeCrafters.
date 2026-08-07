"""Provider-independent sandbox interface for executing untrusted, agent- or
LLM-generated code in isolation. Mirrors src/llm and src/search: callers
(the orchestrator, or any future agent) depend on this abstraction only,
never on the Docker CLI directly.

MVP supports `language="python"` only; anything else returns a controlled
`SandboxResult(status=unsupported)` rather than raising or attempting to run
arbitrary shell commands on the host.
"""

from abc import ABC, abstractmethod

from src.sandbox.models import SandboxResult

SUPPORTED_LANGUAGES = {"python"}


class Sandbox(ABC):
    @abstractmethod
    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout_seconds: int = 10,
    ) -> SandboxResult:
        raise NotImplementedError
