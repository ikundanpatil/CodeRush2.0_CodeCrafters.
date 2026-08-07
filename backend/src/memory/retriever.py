"""Memory retrieval ranking & result types.

Retrieved memories are historical knowledge -- they are treated as "Previous
Research Context", never as automatically-verified facts. Ranking simply orders
candidates by semantic similarity and lets the research planner consume them as
context that still needs fresh verification.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.models.memory import Memory


@dataclass
class RetrievalResult:
    """A retrieved memory plus its semantic similarity score."""

    memory: Memory
    similarity: float

    def to_dict(self, include_content: bool = True) -> Dict[str, Any]:
        data = {
            "id": self.memory.id,
            "memory_type": self.memory.memory_type.value,
            "confidence": self.memory.confidence,
            "importance": self.memory.importance,
            "similarity": round(float(self.similarity), 4),
            "research_run_id": self.memory.research_run_id,
            "created_at": self.memory.created_at,
            "summary": self.memory.summary,
        }
        if include_content:
            data["content"] = self.memory.content
        return data


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(n))
    norm_a = math.sqrt(sum(v * v for v in a)) or 1.0
    norm_b = math.sqrt(sum(v * v for v in b)) or 1.0
    return dot / (norm_a * norm_b)


class MemoryRetriever:
    """Maps semantically-similar vector hits onto canonical MySQL memories.

    The retriever is deliberately store-agnostic: it receives candidate
    ``(memory_id, similarity)`` pairs from a vector store, fetches the canonical
    records through the MySQL store, and returns ranked ``RetrievalResult``s.
    """

    def __init__(self, mysql_store):
        self._mysql = mysql_store

    def rank(
        self,
        candidates: List[tuple],
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> List[RetrievalResult]:
        if not candidates:
            return []

        results: List[RetrievalResult] = []
        for memory_id, similarity in candidates:
            if similarity < min_similarity:
                continue
            memory = self._mysql.get(memory_id)
            if memory is not None:
                results.append(RetrievalResult(memory=memory, similarity=similarity))

        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:top_k]


def merge_context_notes(results: List[RetrievalResult]) -> List[Dict[str, Any]]:
    """Serialize retrieval results for the research planner as context notes."""
    return [r.to_dict(include_content=True) for r in results]