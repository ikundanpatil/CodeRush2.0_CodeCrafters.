"""Feedback persistence -- same MySQL+in-memory-fallback pattern as every
other store in this codebase (memory, evolution, storage)."""

import json
import os
from typing import Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import Integer, String, Text

from src.feedback.models import Feedback


class Base(DeclarativeBase):
    pass


class FeedbackRecord(Base):
    __tablename__ = "everso_feedback"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    helpful: Mapped[Optional[bool]] = mapped_column(nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(64))


def _env(key, default=None):
    return os.getenv(key, default)


class FeedbackStore:
    def __init__(self, engine: Optional[Engine] = None, create_tables: bool = True):
        self._items: Dict[str, Feedback] = {}
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

    def save(self, feedback: Feedback) -> Feedback:
        self._items[feedback.id] = feedback
        if self._mysql_active:
            try:
                with self._session_factory() as session:
                    session.merge(FeedbackRecord(
                        id=feedback.id, run_id=feedback.run_id, helpful=feedback.helpful,
                        rating=feedback.rating, comment=feedback.comment, created_at=feedback.created_at,
                    ))
                    session.commit()
            except Exception:
                pass
        return feedback

    def list_by_run(self, run_id: str) -> List[Feedback]:
        if self._mysql_active:
            try:
                with self._session_factory() as session:
                    records = session.query(FeedbackRecord).filter(FeedbackRecord.run_id == run_id).all()
                    return [
                        Feedback(id=r.id, run_id=r.run_id, helpful=r.helpful, rating=r.rating,
                                 comment=r.comment, created_at=r.created_at)
                        for r in records
                    ]
            except Exception:
                pass
        return [f for f in self._items.values() if f.run_id == run_id]


feedback_store = FeedbackStore()
