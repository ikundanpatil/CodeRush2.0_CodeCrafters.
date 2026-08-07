"""Central MemoryManager -- the ONLY entry point the rest of the app uses.

Coordinates:
    MemoryExtractor   -> turns finished research runs into Memories
    MySQLStore        -> canonical structured storage (source of truth)
    ChromaStore       -> semantic / vector retrieval index
    EmbeddingService  -> pluggable embedder used by the vector layer

Design rules:
* Memory failures NEVER crash the research pipeline -- every operation degrades
  gracefully and records status so callers can emit AgentEvents.
* ChromaDB is only an index; a retrieved memory ID is always resolved against
  MySQL for the canonical record.
* Retrieval returns "Previous Research Context", never verified facts.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.memory.chroma_store import ChromaStore, chroma_store
from src.memory.embedding_service import EmbeddingService, embedding_service
from src.memory.extractor import MemoryExtractor, memory_extractor
from src.memory.mysql_store import MySQLStore, get_mysql_store
from src.memory.retriever import MemoryRetriever, RetrievalResult
from src.models.memory import Memory
from src.models.schemas import ResearchRun


@dataclass
class StorageResult:
    memory: Optional[Memory]
    mysql_ok: bool = True
    chroma_ok: bool = True
    embedding_ok: bool = True
    failures: List[str] = field(default_factory=list)


class MemoryManager:
    def __init__(
        self,
        mysql_store: Optional[MySQLStore] = None,
        chroma: Optional[ChromaStore] = None,
        embeddings: Optional[EmbeddingService] = None,
        extractor: Optional[MemoryExtractor] = None,
        event_sink: Optional[Callable[..., None]] = None,
    ):
        self.mysql = mysql_store or get_mysql_store()
        self.chroma = chroma or chroma_store
        self.embeddings = embeddings or embedding_service
        self.extractor = extractor or memory_extractor
        self.retriever = MemoryRetriever(self.mysql)
        self._event_sink = event_sink

    # -- plumbing ----------------------------------------------------------
    def set_event_sink(self, sink: Optional[Callable[..., None]]):
        self._event_sink = sink

    def _emit(self, event_type: str, title: str, message: str, data: Optional[Dict] = None):
        if self._event_sink is not None:
            try:
                self._event_sink(event_type, title, message, data)
            except Exception:
                pass

    def status(self) -> Dict[str, Any]:
        return {
            "mysql_active": self.mysql.ping(),
            "chroma_active": self.chroma.ping(),
            "embedding_provider": self.embeddings.provider,
            "embedding_available": self.embeddings.is_available(),
        }

    # -- write path --------------------------------------------------------
    def store(self, memory: Memory) -> StorageResult:
        """Persist one memory: MySQL canonical record + Chroma vector."""
        result = StorageResult(memory=memory)

        try:
            saved = self.mysql.save(memory)
            result.memory = saved or memory
        except Exception as exc:
            result.mysql_ok = False
            result.failures.append(f"mysql:{exc}")

        vector: Optional[List[float]] = None
        try:
            vector = self.embeddings.embed_text(memory.content)
        except Exception as exc:
            result.embedding_ok = False
            result.failures.append(f"embedding:{exc}")

        if vector is not None:
            try:
                self.chroma.add(
                    memory.id,
                    vector,
                    {
                        "memory_type": memory.memory_type.value,
                        "research_run_id": memory.research_run_id or "",
                        "content": memory.content,
                        "summary": memory.summary,
                    },
                )
            except Exception as exc:
                result.chroma_ok = False
                result.failures.append(f"chroma:{exc}")
        else:
            result.chroma_ok = False

        return result

    def store_many(self, memories: List[Memory]) -> List[StorageResult]:
        return [self.store(m) for m in memories]

    def extract_and_store(self, run: ResearchRun) -> List[StorageResult]:
        """Extract memories from a finished research run and persist them."""
        memories = self.extractor.extract(run)
        results = self.store_many(memories)
        for res in results:
            if res.memory is not None:
                self._emit(
                    "memory_created",
                    "Memory Created",
                    f"Stored {res.memory.memory_type.value} memory '{res.memory.id[:8]}'.",
                    {
                        "memory_id": res.memory.id,
                        "memory_type": res.memory.memory_type.value,
                        "mysql_ok": res.mysql_ok,
                        "chroma_ok": res.chroma_ok,
                        "research_run_id": res.memory.research_run_id,
                    },
                )
            if not (res.mysql_ok or res.chroma_ok):
                self._emit(
                    "memory_storage_failed",
                    "Memory Storage Failed",
                    f"Memory '{res.memory.id if res.memory else '?'}' could not be persisted.",
                    {"failures": res.failures},
                )
        return results

    # -- read path ---------------------------------------------------------
    def get(self, memory_id: str) -> Optional[Memory]:
        return self.mysql.get(memory_id)

    def update(self, memory_id: str, **fields) -> Optional[Memory]:
        updated = self.mysql.update(memory_id, **fields)
        if updated is not None:
            self._emit(
                "memory_updated",
                "Memory Updated",
                f"Memory '{updated.id[:8]}' updated.",
                {"memory_id": updated.id, "memory_type": updated.memory_type.value},
            )
        return updated

    def delete(self, memory_id: str) -> bool:
        deleted = self.mysql.delete(memory_id)
        try:
            self.chroma.delete(memory_id)
        except Exception:
            pass
        return deleted

    def get_by_research_run(self, research_run_id: str) -> List[Memory]:
        return self.mysql.list_by_run(research_run_id)

    def search(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """Semantic retrieval with keyword fallback. Never raises."""
        if not query or not query.strip():
            return []
        query = query.strip()

        try:
            vector = self.embeddings.embed_text(query)
            if vector is not None:
                candidates = self.chroma.query(vector, top_k=top_k)
                results = self.retriever.rank(candidates, top_k=top_k)
                if results:
                    return results
        except Exception:
            pass

        # Keyword fallback keeps retrieval alive when the vector layer is down.
        keyword_matches = self.mysql.search_keyword(query)
        return [
            RetrievalResult(memory=m, similarity=0.5)
            for m in keyword_matches[:top_k]
        ]

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """Alias for search() used by the orchestrator for pre-planning recall."""
        return self.search(query, top_k=top_k)


memory_manager = MemoryManager()