"""Research run storage: real MySQL persistence (Part B) with the exact
same in-memory-fallback pattern used by src/memory/mysql_store.py and
src/evolution/store.py.

Deliberately a write-through cache, not a pure MySQL-backed store: the
orchestrator and ResearchLoop mutate a run's `trace`/`sources`/etc. in place
throughout a run via plain attribute/list mutation (no `save_run()` call
after every single trace event), and Phase 10's cooperative cancellation
depends on `store.get_run(run_id)` returning the SAME live object the
running orchestrator coroutine holds. So within one process, the in-memory
`_runs` dict remains authoritative (unchanged behavior); MySQL is written
through on every `save_run()` for durability, and is the fallback read path
for a run created in a previous process (i.e. after a restart).
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import JSON, String, Text

from src.models.schemas import ResearchRun

import os


class Base(DeclarativeBase):
    pass


class ResearchRunRecord(Base):
    __tablename__ = "everso_research_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[str] = mapped_column(String(64), index=True)
    updated_at: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict] = mapped_column(JSON)  # full ResearchRun.model_dump(mode="json")


def _env(key: str, default=None):
    return os.getenv(key, default)


class MemoryStore:
    """Research run store. PostgreSQL / MySQL primary (durable), in-memory dict is the
    live cache every in-flight run is actually mutated through."""

    def __init__(self, engine: Optional[Engine] = None, create_tables: bool = True):
        self._runs: Dict[str, ResearchRun] = {}
        self._db_active = False
        self._db_backend_name = "in-memory fallback"
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

        if engine is None:
            engine = self._build_engine_from_env()
        self._try_connect(engine, create_tables)

    # -- engine / connection handling --------------------------------------
    def _build_engine_from_env(self) -> Optional[Engine]:
        # 1. Check DATABASE_URL (Render PostgreSQL)
        db_url = _env("DATABASE_URL")
        if db_url:
            # Normalize postgres:// or postgresql:// to postgresql+psycopg:// if no driver is specified
            if db_url.startswith("postgres://"):
                db_url = "postgresql+psycopg://" + db_url[len("postgres://"):]
            elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
                db_url = "postgresql+psycopg://" + db_url[len("postgresql://"):]

            try:
                engine = create_engine(
                    db_url,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                    connect_args={"connect_timeout": 5},
                )
                self._db_backend_name = "PostgreSQL"
                return engine
            except Exception:
                pass

        # 2. Check local MySQL
        host = _env("MYSQL_HOST")
        port = _env("MYSQL_PORT", "3306")
        user = _env("MYSQL_USER")
        password = _env("MYSQL_PASSWORD")
        database = _env("MYSQL_DATABASE")
        if host and user and database:
            try:
                engine = create_engine(
                    f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}",
                    pool_pre_ping=True,
                    pool_recycle=3600,
                    connect_args={"connect_timeout": 3},
                )
                self._db_backend_name = "MySQL"
                return engine
            except Exception:
                pass

        self._db_backend_name = "in-memory fallback"
        return None

    def _try_connect(self, engine: Optional[Engine], create_tables: bool):
        if engine is None:
            self._db_active = False
            self._db_backend_name = "in-memory fallback"
            return
        try:
            from sqlalchemy import text as sa_text

            with engine.connect() as conn:
                conn.execute(sa_text("SELECT 1"))
            if create_tables:
                Base.metadata.create_all(engine)
            self._engine = engine
            self._session_factory = sessionmaker(bind=engine)
            self._db_active = True
            if self._db_backend_name == "in-memory fallback":
                # Engine was passed in explicitly (e.g. SQLite in tests)
                self._db_backend_name = engine.dialect.name.capitalize()
        except Exception:
            self._db_active = False
            self._db_backend_name = "in-memory fallback"

    @property
    def is_mysql_active(self) -> bool:
        """Maintained for backward-compatibility with tests / code checking DB status."""
        return self._db_active

    @property
    def is_db_active(self) -> bool:
        return self._db_active

    @property
    def db_backend(self) -> str:
        return self._db_backend_name if self._db_active else "in-memory fallback"

    def ping(self) -> bool:
        return self._db_active

    # -- serialization -------------------------------------------------------
    def _record_from_run(self, run: ResearchRun) -> ResearchRunRecord:
        return ResearchRunRecord(
            run_id=run.run_id,
            question=run.question,
            status=run.status.value if hasattr(run.status, "value") else str(run.status),
            created_at=run.created_at,
            updated_at=run.updated_at,
            data=json.loads(run.model_dump_json()),
        )

    def _run_from_record(self, record: ResearchRunRecord) -> ResearchRun:
        return ResearchRun.model_validate(record.data)

    def _persist_to_db(self, run: ResearchRun) -> None:
        if not self._db_active:
            return
        try:
            with self._session_factory() as session:
                session.merge(self._record_from_run(run))
                session.commit()
        except Exception:
            # Durability is best-effort; the in-memory cache remains the
            # live source of truth for the current process either way.
            pass

    def _load_from_db(self, run_id: str) -> Optional[ResearchRun]:
        if not self._db_active:
            return None
        try:
            with self._session_factory() as session:
                record = session.get(ResearchRunRecord, run_id)
                return self._run_from_record(record) if record else None
        except Exception:
            return None

    def _list_from_db(self) -> List[ResearchRun]:
        if not self._db_active:
            return []
        try:
            with self._session_factory() as session:
                records = (
                    session.query(ResearchRunRecord)
                    .order_by(ResearchRunRecord.created_at.desc())
                    .all()
                )
                return [self._run_from_record(r) for r in records]
        except Exception:
            return []

    # -- public interface (unchanged signatures) ------------------------------
    def save_run(self, run: ResearchRun):
        run.updated_at = datetime.now(timezone.utc).isoformat()
        self._runs[run.run_id] = run
        self._persist_to_db(run)

    def get_run(self, run_id: str) -> Optional[ResearchRun]:
        if run_id in self._runs:
            return self._runs[run_id]
        loaded = self._load_from_db(run_id)
        if loaded is not None:
            self._runs[run_id] = loaded
        return loaded

    def list_runs(self) -> List[ResearchRun]:
        by_id: Dict[str, ResearchRun] = {r.run_id: r for r in self._list_from_db()}
        # The in-memory cache wins for any run currently live in this
        # process (freshest state, e.g. mid-run trace events not yet
        # written through), and covers runs DB doesn't have (fallback
        # mode, or a write that failed silently).
        by_id.update(self._runs)
        return sorted(by_id.values(), key=lambda r: r.created_at, reverse=True)


store = MemoryStore()
