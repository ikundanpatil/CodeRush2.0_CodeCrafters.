"""ConversationSession persistence -- same MySQL+in-memory-fallback,
write-through-cache pattern as src/storage/store.py (object identity
preserved for the live session within a process; MySQL for durability)."""

import json
import os
from typing import Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import JSON, String

from src.conversation.models import ConversationSession


class Base(DeclarativeBase):
    pass


class ConversationRecord(Base):
    __tablename__ = "everso_conversations"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[str] = mapped_column(String(64), index=True)
    updated_at: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict] = mapped_column(JSON)


def _env(key, default=None):
    return os.getenv(key, default)


class ConversationStore:
    def __init__(self, engine: Optional[Engine] = None, create_tables: bool = True):
        self._sessions: Dict[str, ConversationSession] = {}
        self._mysql_active = False
        self._session_factory: Optional[sessionmaker] = None

        if engine is None:
            engine = self._build_engine_from_env()
        self._try_connect(engine, create_tables)

    def _build_engine_from_env(self) -> Optional[Engine]:
        host = _env("MYSQL_HOST"); user = _env("MYSQL_USER"); database = _env("MYSQL_DATABASE")
        if not (host and user and database):
            return None
        try:
            return create_engine(
                f"mysql+pymysql://{user}:{_env('MYSQL_PASSWORD')}@{host}:{_env('MYSQL_PORT', '3306')}/{database}",
                pool_pre_ping=True, pool_recycle=3600, connect_args={"connect_timeout": 3},
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
            self._session_factory = sessionmaker(bind=engine)
            self._mysql_active = True
        except Exception:
            self._mysql_active = False

    @property
    def is_mysql_active(self) -> bool:
        return self._mysql_active

    def _persist(self, session: ConversationSession) -> None:
        if not self._mysql_active:
            return
        try:
            with self._session_factory() as db:
                db.merge(ConversationRecord(
                    session_id=session.session_id, created_at=session.created_at,
                    updated_at=session.updated_at, data=json.loads(session.model_dump_json()),
                ))
                db.commit()
        except Exception:
            pass

    def save(self, session: ConversationSession) -> ConversationSession:
        self._sessions[session.session_id] = session
        self._persist(session)
        return session

    def get(self, session_id: str) -> Optional[ConversationSession]:
        if session_id in self._sessions:
            return self._sessions[session_id]
        if self._mysql_active:
            try:
                with self._session_factory() as db:
                    record = db.get(ConversationRecord, session_id)
                    if record:
                        session = ConversationSession.model_validate(record.data)
                        self._sessions[session_id] = session
                        return session
            except Exception:
                pass
        return None

    def list_all(self) -> List[ConversationSession]:
        by_id: Dict[str, ConversationSession] = {}
        if self._mysql_active:
            try:
                with self._session_factory() as db:
                    for record in db.query(ConversationRecord).order_by(ConversationRecord.updated_at.desc()).all():
                        by_id[record.session_id] = ConversationSession.model_validate(record.data)
            except Exception:
                pass
        by_id.update(self._sessions)
        return sorted(by_id.values(), key=lambda s: s.updated_at, reverse=True)

    def delete(self, session_id: str) -> bool:
        existed = session_id in self._sessions
        self._sessions.pop(session_id, None)
        if self._mysql_active:
            try:
                with self._session_factory() as db:
                    record = db.get(ConversationRecord, session_id)
                    if record:
                        db.delete(record)
                        db.commit()
                        existed = True
            except Exception:
                pass
        return existed


conversation_store = ConversationStore()
