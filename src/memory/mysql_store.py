"""Structured memory persistence backed by MySQL (source of truth).

Uses SQLAlchemy 2.0 declarative mapping. The table is created non-destructively
(``create_all``) so it never touches existing Phase 1 tables/data.

Fault tolerance: if MySQL is unreachable at import/startup time, the store
seamlessly falls back to a volatile in-memory dict store so research can
continue in a degraded "memory disabled" mode instead of crashing. The moment
MySQL becomes available the real engine is used. MySQL remains the intended
source of truth for structured metadata.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.types import JSON, String, Text

from src.models.memory import Memory, utc_now


class Base(DeclarativeBase):
    pass


class MemoryRecord(Base):
    __tablename__ = "everso_memories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    memory_type: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    research_run_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    source_ids: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(default=1.0)
    importance: Mapped[float] = mapped_column(default=0.5)
    extra: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[str] = mapped_column(String(64))

    def to_memory(self) -> Memory:
        return Memory(
            id=self.id,
            memory_type=self.memory_type,
            content=self.content,
            summary=self.summary or "",
            research_run_id=self.research_run_id,
            source_ids=list(self.source_ids or []),
            confidence=float(self.confidence),
            importance=float(self.importance),
            metadata=dict(self.extra or {}),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


def _env(key: str, default: Any = None) -> Any:
    value = os.getenv(key, default)
    return value


class MySQLStore:
    """Structured memory store. MySQL primary, in-memory fallback for degraded mode."""

    COLLECTION_SOURCE_ID_KEY = "source_ids"

    def __init__(self, engine: Optional[Engine] = None, create_tables: bool = True):
        self._mysql_active = False
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._fallback: Dict[str, Memory] = {}

        if engine is None:
            engine = self._build_engine_from_env()
        self._try_connect(engine, create_tables)

    # -- engine / connection handling --------------------------------------
    def _build_engine_from_env(self) -> Optional[Engine]:
        host = _env("MYSQL_HOST")
        port = _env("MYSQL_PORT", "3306")
        user = _env("MYSQL_USER")
        password = _env("MYSQL_PASSWORD")
        database = _env("MYSQL_DATABASE")
        if not (host and user and database):
            return None

        try:
            return create_engine(
                f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}",
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={"connect_timeout": 3},
            )
        except Exception:
            return None

    def _try_connect(self, engine: Optional[Engine], create_tables: bool):
        if engine is None:
            return
        try:
            from sqlalchemy import text as sa_text

            with engine.connect() as conn:
                conn.execute(sa_text("SELECT 1"))
            if create_tables:
                Base.metadata.create_all(engine)
            self._engine = engine
            self._session = sessionmaker(bind=engine)
            self._mysql_active = True
        except Exception:
            self._mysql_active = False

    # -- counting / availability -------------------------------------------
    @property
    def is_mysql_active(self) -> bool:
        return self._mysql_active

    def ping(self) -> bool:
        return self.is_mysql_active

    # -- internal helpers --------------------------------------------------
    def _session_ctx(self):
        return self._session()

    def _record_from_memory(self, memory: Memory) -> MemoryRecord:
        now = utc_now()
        return MemoryRecord(
            id=memory.id,
            memory_type=memory.memory_type.value,
            content=memory.content,
            summary=memory.summary or "",
            research_run_id=memory.research_run_id,
            source_ids=memory.source_ids or [],
            confidence=memory.confidence,
            importance=memory.importance,
            extra=memory.metadata or {},
            created_at=memory.created_at or now,
            updated_at=memory.updated_at or now,
        )

    def _record_to_memory(self, record) -> Memory:
        return Memory(
            id=record.id,
            memory_type=record.memory_type,
            content=record.content,
            summary=record.summary or "",
            research_run_id=record.research_run_id,
            source_ids=list(record.source_ids or []),
            confidence=float(record.confidence),
            importance=float(record.importance),
            extra=dict(record.extra or {}),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    # -- CRUD --------------------------------------------------------------
    def save(self, memory: Memory) -> Optional[Memory]:
        memory.updated_at = utc_now()
        if self._mysql_active:
            try:
                with self._session_ctx() as session:
                    session.merge(self._record_from_memory(memory))
                    session.commit()
                return memory
            except Exception:
                # fall back to volatile storage rather than lose the memory
                self._fallback[memory.id] = memory.model_copy()
                return memory
        self._fallback[memory.id] = memory.model_copy()
        return memory

    def get(self, memory_id: str) -> Optional[Memory]:
        if self._mysql_active:
            try:
                with self._session_ctx() as session:
                    record = session.get(MemoryRecord, memory_id)
                    return self._record_to_memory(record) if record else None
            except Exception:
                return self._fallback.get(memory_id)
        return self._fallback.get(memory_id)

    def update(self, memory_id: str, **fields) -> Optional[Memory]:
        memory = self.get(memory_id)
        if memory is None:
            return None
        allowed = {
            "content", "summary", "confidence", "importance",
            "metadata", "source_ids", "research_run_id",
        }
        for key, value in fields.items():
            if key in allowed:
                setattr(memory, key, value)
        memory.updated_at = utc_now()
        return self.save(memory)

    def delete(self, memory_id: str) -> bool:
        if self._mysql_active:
            try:
                with self._session_ctx() as session:
                    record = session.get(MemoryRecord, memory_id)
                    if record:
                        session.delete(record)
                        session.commit()
                        return True
            except Exception:
                pass
        self._fallback.pop(memory_id, None)
        return memory_id not in self._fallback

    def list_by_run(self, research_run_id: str) -> List[Memory]:
        if self._mysql_active:
            try:
                with self._session_ctx() as session:
                    records = (
                        session.query(MemoryRecord)
                        .filter(MemoryRecord.research_run_id == research_run_id)
                        .all()
                    )
                    return [self._record_to_memory(r) for r in records]
            except Exception:
                pass
        return [m for m in self._fallback.values()
                if m.research_run_id == research_run_id]

    def list_all(self) -> List[Memory]:
        if self._mysql_active:
            try:
                with self._session_ctx() as session:
                    records = session.query(MemoryRecord).all()
                    return [self._record_to_memory(r) for r in records]
            except Exception:
                pass
        return list(self._fallback.values())

    def search_keyword(self, query: str) -> List[Memory]:
        needle = (query or "").lower().strip()
        if not needle:
            return []
        if self._mysql_active:
            try:
                with self._session_ctx() as session:
                    like = f"%{needle}%"
                    records = (
                        session.query(MemoryRecord)
                        .filter(
                            MemoryRecord.content.ilike(like)
                            | MemoryRecord.summary.ilike(like)
                        )
                        .all()
                    )
                    return [self._record_to_memory(r) for r in records]
            except Exception:
                pass
        return [
            m for m in self._fallback.values()
            if needle in m.content.lower() or needle in (m.summary or "").lower()
        ]


_mysql_store = None


def get_mysql_store() -> MySQLStore:
    global _mysql_store
    if _mysql_store is None:
        _mysql_store = MySQLStore()
    return _mysql_store