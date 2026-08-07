import os
from typing import Optional

from src.llm.base import (
    LLMAdapter,
    LLMConfigError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)


class OpenAIAdapter(LLMAdapter):
    """OpenAI Chat Completions provider. Also the base for OpenAI-compatible
    providers (e.g. NVIDIA NIM) via the base_url override."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        **_,
    ):
        self.model = model or os.getenv("LLM_MODEL") or "gpt-4.1-mini"

        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise LLMConfigError(
                "OPENAI_API_KEY is not set. Set it in your environment or backend/.env."
            )

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise LLMConfigError(
                "The 'openai' package is required for LLM_PROVIDER=openai. "
                "Install it with `pip install openai`."
            ) from exc

        client_kwargs = {"api_key": resolved_key, "timeout": timeout}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**client_kwargs)

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        request_kwargs = {"model": self.model, "messages": messages}
        if kwargs.get("response_format") == "json":
            request_kwargs["response_format"] = {"type": "json_object"}
        if "temperature" in kwargs:
            request_kwargs["temperature"] = kwargs["temperature"]

        try:
            response = await self._client.chat.completions.create(**request_kwargs)
        except Exception as exc:  # noqa: BLE001 - mapped below into typed errors
            self._raise_mapped_error(exc)

        return response.choices[0].message.content or ""

    def _raise_mapped_error(self, exc: Exception):
        try:
            import openai as openai_sdk
        except ImportError:
            raise LLMProviderError(str(exc)) from exc

        if isinstance(exc, openai_sdk.AuthenticationError):
            raise LLMConfigError(f"Invalid or rejected API key: {exc}") from exc
        if isinstance(exc, openai_sdk.RateLimitError):
            raise LLMRateLimitError(f"LLM provider rate limit exceeded: {exc}") from exc
        if isinstance(exc, openai_sdk.APITimeoutError):
            raise LLMTimeoutError(f"LLM request timed out: {exc}") from exc
        if isinstance(exc, openai_sdk.NotFoundError):
            raise LLMConfigError(f"Requested model is not available: {exc}") from exc
        if isinstance(exc, openai_sdk.APIConnectionError):
            raise LLMProviderError(f"Network error contacting LLM provider: {exc}") from exc
        raise LLMProviderError(f"LLM provider error: {exc}") from exc
