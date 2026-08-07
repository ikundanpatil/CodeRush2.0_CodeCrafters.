"""Provider-independent LLM interface.

The orchestrator only ever depends on this module (and the factory in
adapter.py) -- never on a concrete provider SDK. Concrete providers live in
llm/providers/ and each implements LLMAdapter.generate().
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMError(Exception):
    """Base class for all LLM adapter failures."""


class LLMConfigError(LLMError):
    """Missing/invalid configuration: unknown provider, missing API key, missing SDK."""


class LLMProviderError(LLMError):
    """The upstream provider call failed (network error, unexpected 5xx, etc.)."""


class LLMTimeoutError(LLMError):
    """The request to the LLM provider timed out."""


class LLMRateLimitError(LLMError):
    """The LLM provider reported a rate limit."""


class LLMOutputError(LLMError):
    """The LLM's output could not be parsed/validated as expected."""


class LLMAdapter(ABC):
    """Provider-independent text generation interface."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Generate text from a prompt.

        system_prompt carries TRUSTED instructions only. prompt carries the
        user/task content, which may itself embed untrusted data -- callers
        are responsible for clearly delimiting untrusted content within it.
        """
        raise NotImplementedError
