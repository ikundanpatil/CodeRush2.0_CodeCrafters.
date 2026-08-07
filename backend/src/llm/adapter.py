import os

from src.llm.base import LLMAdapter, LLMConfigError
from src.llm.providers.mock import MockAdapter
from src.llm.providers.nvidia import NVIDIAAdapter
from src.llm.providers.openai import OpenAIAdapter

_PROVIDERS = {
    "mock": MockAdapter,
    "openai": OpenAIAdapter,
    "nvidia": NVIDIAAdapter,
}


def get_llm_adapter(provider: str | None = None) -> LLMAdapter:
    """Return an LLMAdapter for the requested provider.

    Reads LLM_PROVIDER from the environment when provider is not given.
    Defaults to "mock" so the app and test suite work offline out of the box.
    """
    name = (provider or os.getenv("LLM_PROVIDER") or "mock").strip().lower()
    provider_cls = _PROVIDERS.get(name)
    if provider_cls is None:
        raise LLMConfigError(
            f"Unknown LLM_PROVIDER '{name}'. Valid options: {', '.join(sorted(_PROVIDERS))}."
        )
    return provider_cls()
