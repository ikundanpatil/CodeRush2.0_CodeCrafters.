"""Semantic / vector memory layer backed by ChromaDB.

ChromaDB is NOT a source of truth -- it is a retrieval index. The canonical
record always lives in MySQL; ChromaMapC stores memory-id-keyed vectors and
metadata so a semantic query can return candidate memory IDs, which callers
then resolve against MySQL.

Fault tolerance: when ChromaDB is unavailable (not installed / not running) a
volatile in-memory vector index with cosine similarity keeps semantic retrieval
working for tests and demos, and the research pipeline continues.
"""

import os
from typing import Any, Dict, List, Optional, Tuple

from src.memory.embedding_service import EmbeddingService, embedding_service
from src.memory.retriever import cosine_similarity

COLLECTION_NAME = "eversoresearch_memories"


class ChromaStore:
    def __init__(
        self,
        collection_name: str = COLLECTION_NAME,
        embedding: Optional[EmbeddingService] = None,
        persist_dir: Optional[str] = None,
    ):
        self.collection_name = collection_name
        self.embeddings = embedding or embedding_service
        self.persist_dir = persist_dir or os.getenv("CHROMA_PERSIST_DIR")
        self._client = None
        self._collection = None
        self._fallback: Dict[str, List[float]] = {}
        self._fallback_meta: Dict[str, Dict[str, Any]] = {}
        self._chroma_active = False
        self._try_connect()

    def _try_connect(self):
        try:
            import chromadb  # lazy import so absence is non-fatal

            if self.persist_dir:
                self._client = chromadb.PersistentClient(path=self.persist_dir)
            else:
                self._client = chromadb.Client()
            self._collection = self._client.get_or_create_collection\
                (self.collection_name, metadata={"hnsw:space": "cosine"})
            self._chroma_active = True
        except Exception:
            self._chroma_active = False
            self._client = None
            self._collection = None

    @property
    def is_chroma_active(self) -> bool:
        return self._chroma_active

    def ping(self) -> bool:
        return self.is_chroma_active

    # -- vector storage ----------------------------------------------------
    def add(self, memory_id: str, vector: List[float], metadata: Dict[str, Any]) -> bool:
        if vector is None:
            return False
        if self._chroma_active:
            try:
                documents = str(metadata.get("content", ""))
                self._collection.upsert(
                    ids=[memory_id],
                    embeddings=[vector],
                    metadatas=[{k: v for k, v in metadata.items() if v is not None}],
                    documents=[documents],
                )
                return True
            except Exception:
                self._fallback[memory_id] = vector
                self._fallback_meta[memory_id] = metadata
                return True
        self._fallback[memory_id] = vector
        self._fallback_meta[memory_id] = metadata
        return True

    def delete(self, memory_id: str) -> bool:
        if self._chroma_active:
            try:
                self._collection.delete(ids=[memory_id])
            except Exception:
                pass
        self._fallback.pop(memory_id, None)
        self._fallback_meta.pop(memory_id, None)
        return True

    # -- semantic query ----------------------------------------------------
    def query(
        self, vector: List[float], top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """Return ``[(memory_id, similarity), ...]`` ordered by similarity desc."""
        if vector is None:
            return []
        if self._chroma_active:
            try:
                res = self._collection.query(
                    query_embeddings=[vector],
                    n_results=max(1, min(top_k, 100)),
                    include=["documents", "metadatas", "distances"],
                )
                ids = res.get("ids", [[]])[0]
                distances = res.get("distances", [[]])[0]
                out: List[Tuple[str, float]] = []
                for mid, dist in zip(ids, distances):
                    score = max(0.0, 1.0 - abs(float(dist)))
                    out.append((str(mid), score))
                return out
            except Exception:
                pass
        # in-memory cosine fallback
        scored = [
            (mid, cosine_similarity(vector, stored))
            for mid, stored in self._fallback.items()
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def count(self) -> int:
        if self._chroma_active:
            try:
                return self._collection.count()
            except Exception:
                pass
        return len(self._fallback)


chroma_store = ChromaStore()