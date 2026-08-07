"""Pluggable, environment-configurable embedding service.

Not hard-coded to a single provider. Selected at runtime from env var
``EVORESEARCH_EMBEDDING_PROVIDER`` (default ``local``). A deterministic local
hash embedder is the safe fallback so semantic memory keeps working even with
no external API credentials. If a configured remote provider cannot be used,
the service reports itself unavailable and callers degrade gracefully.
"""

import hashlib
import math
import os
import re
from typing import List, Optional, Sequence

_token_re = re.compile(r"[a-z0-9]+", re.IGNORECASE)


class LocalHashEmbedder:
    """Deterministic char-n-gram hashing embedder (no external service).

    Produces a fixed-dimension, normalized vector purely from text so semantic
    similarity works offline. Good enough for an MVP and for tests.
    """

    DIMENSION = 192

    def __init__(self, dimension: int = DIMENSION):
        self.dimension = int(dimension)

    def _tokens(self, text: str) -> List[str]:
        words = [w.lower() for w in _token_re.findall(text or "")]
        tokens = list(words)
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i + 1]}")
        return tokens

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dimension
        for token in self._tokens(text):
            digest = hashlib.md5(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dimension
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]

    def available(self) -> bool:
        return True


class _OpenAIBackend:
    """Optional OpenAI-backed embedder. Only used when a key is configured."""

    MODEL = "text-embedding-3-small"

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")

    def embed(self, text: str) -> List[float]:
        return self._call([text])[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._call(texts)

    def _call(self, texts: List[str]) -> List[List[float]]:
        import httpx

        response = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.MODEL, "input": texts},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()["data"]
        ordered = sorted(data, key=lambda item: item["index"])
        return [item["embedding"] for item in ordered]

    def available(self) -> bool:
        try:
            self.embed("ping")
            return True
        except Exception:
            return False


class EmbeddingService:
    """Uniform interface used by MemoryManager and ChromaStore.

    Interface:
        embed_text(text) -> Optional[List[float]]
        embed_documents(texts) -> Optional[List[List[float]]]
        is_available() -> bool
    """

    def __init__(self, provider: Optional[str] = None):
        provider = (provider or os.getenv("EVORESEARCH_EMBEDDING_PROVIDER", "local")).lower()
        self._provider = provider
        self._backend = self._build(provider)

    def _build(self, provider: str):
        if provider == "openai":
            try:
                return _OpenAIBackend()
            except Exception:
                return None
        return LocalHashEmbedder()

    def is_available(self) -> bool:
        backend = self._backend
        if backend is None:
            return False
        try:
            return bool(backend.available())
        except Exception:
            return False

    def embed_text(self, text: str) -> Optional[List[float]]:
        if not self.is_available():
            return None
        try:
            return self._backend.embed(text)
        except Exception:
            return None

    def embed_documents(self, texts: List[str]) -> Optional[List[List[float]]]:
        if not self.is_available():
            return None
        try:
            return self._backend.embed_documents(texts)
        except Exception:
            return None

    @property
    def provider(self) -> str:
        return self._provider


embedding_service = EmbeddingService()