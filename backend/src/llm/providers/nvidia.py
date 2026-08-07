import os
from typing import Optional

from src.llm.base import LLMConfigError
from src.llm.providers.openai import OpenAIAdapter

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_DEFAULT_MODEL = "nvidia/nemotron-3-nano-30b-a3b"


class NVIDIAAdapter(OpenAIAdapter):
    """NVIDIA NIM provider, using NVIDIA's OpenAI-compatible API."""

    def __init__(self, model: Optional[str] = None, timeout: float = 30.0, **_):
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise LLMConfigError(
                "NVIDIA_API_KEY is not set. Set it in your environment or backend/.env."
            )
        resolved_model = model or os.getenv("LLM_MODEL") or NVIDIA_DEFAULT_MODEL
        super().__init__(
            model=resolved_model,
            api_key=api_key,
            base_url=NVIDIA_BASE_URL,
            timeout=timeout,
        )
