"""Research run storage: PostgreSQL (Render) primary, MySQL (local dev) fallback,
in-memory fallback of last resort.

Database priority:
    1. DATABASE_URL  → PostgreSQL (Render / any hosted PG)
    2. MYSQL_*       → local MySQL
    3. (none)        → volatile in-memory dict (degraded mode)

Write-through cache design (intentional):
    The orchestrator and ResearchLoop mutate a run's `trace`/`sources`/etc.
    in place throughout a run via plain attribute/list mutation (no
    `save_run()` after every trace event). Phase 10 cooperative cancellation
    depends on `store.get_run(run_id)` returning the SAME live object the
    running orchestrator coroutine holds. So within one process, the
    in-memory `_runs` dict remains authoritative (unchanged behavior);
    the configured database is written-through on every `save_run()` for
    durability, and is the fallback read path for a run created in a
    previous process (i.e. after a restart).
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import JSON, String, Text

from src.models.schemas import ResearchRun

import os

_logger = logging.getLogger(__name__)


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


def _normalize_pg_url(url: str) -> str:
    """Normalize postgres:// or postgresql:// to postgresql+psycopg:// for SQLAlchemy."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


class MemoryStore:
    """Research run store. PostgreSQL / MySQL primary (durable), in-memory dict is the
    live cache every in-flight run is actually mutated through."""

    def __init__(self, engine: Optional[Engine] = None, create_tables: bool = True):
        self._runs: Dict[str, ResearchRun] = {}
        self._db_active = False
        self._database_backend = "memory"
        self._db_backend_name = "memory"
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

        if engine is None:
            engine = self._build_engine_from_env()
        self._try_connect(engine, create_tables)

    # -- engine / connection handling --------------------------------------
    def _build_engine_from_env(self) -> Optional[Engine]:
        # 1. Check DATABASE_URL (Render PostgreSQL — takes priority over MySQL)
        db_url = _env("DATABASE_URL")
        if db_url:
            normalized = _normalize_pg_url(db_url)
            try:
                engine = create_engine(
                    normalized,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                    connect_args={"connect_timeout": 5},
                )
                self._database_backend = "postgresql"
                self._db_backend_name = "PostgreSQL"
                return engine
            except Exception as e:
                # Log the type/message but NEVER the url (it contains the password)
                _logger.warning(
                    "DATABASE_URL engine creation failed (%s: %s); "
                    "will try MYSQL_* fallback.",
                    type(e).__name__, e,
                )

        # 2. Check local MySQL (MYSQL_HOST + MYSQL_USER + MYSQL_DATABASE required)
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
                self._database_backend = "mysql"
                self._db_backend_name = "MySQL"
                return engine
            except Exception as e:
                _logger.warning(
                    "MySQL engine creation failed (%s: %s); "
                    "falling back to in-memory store.",
                    type(e).__name__, e,
                )

        # 3. Neither configured → in-memory fallback
        _logger.info(
            "No database configured (DATABASE_URL and MYSQL_* unset). "
            "Research runs will NOT survive a process restart."
        )
        self._database_backend = "memory"
        self._db_backend_name = "memory"
        return None

    def _try_connect(self, engine: Optional[Engine], create_tables: bool):
        if engine is None:
            self._db_active = False
            self._database_backend = "memory"
            self._db_backend_name = "memory"
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
            if self._database_backend == "memory":
                # Engine was passed in explicitly (e.g. SQLite in tests)
                self._db_backend_name = engine.dialect.name.capitalize()
        except Exception as e:
            _logger.warning(
                "Database connection test failed (%s: %s); "
                "using in-memory fallback. Research runs will NOT persist across restarts.",
                type(e).__name__, e,
            )
            self._db_active = False
            self._database_backend = "memory"
            self._db_backend_name = "memory"

    # -- backward-compat properties (used by tests + health endpoint) ------
    @property
    def is_mysql_active(self) -> bool:
        """Maintained for backward-compatibility with tests / code checking DB status."""
        return self._db_active

    @property
    def is_db_active(self) -> bool:
        return self._db_active

    @property
    def db_backend(self) -> str:
        """Human-readable backend name for startup logging."""
        if not self._db_active:
            return "memory"
        return self._db_backend_name

    @property
    def database_backend(self) -> str:
        """Canonical backend id: postgresql | mysql | memory."""
        return self._database_backend if self._db_active else "memory"

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
        except Exception as e:
            # Safe logging: log exception type and message — credentials are NEVER in these
            _logger.error(
                "Database persistence failed for run %s: %s - %s",
                run.run_id, type(e).__name__, e,
            )

    def _load_from_db(self, run_id: str) -> Optional[ResearchRun]:
        if not self._db_active:
            return None
        try:
            with self._session_factory() as session:
                record = session.get(ResearchRunRecord, run_id)
                return self._run_from_record(record) if record else None
        except Exception as e:
            _logger.error(
                "Database load failed for run %s: %s - %s",
                run_id, type(e).__name__, e,
            )
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
        except Exception as e:
            _logger.error("Database list failed: %s - %s", type(e).__name__, e)
            return []

    # -- public interface (unchanged signatures) ------------------------------
    def save_run(self, run: ResearchRun):
        run.updated_at = datetime.now(timezone.utc).isoformat()
        self._runs[run.run_id] = run
        self._persist_to_db(run)

    def get_run(self, run_id: str) -> Optional[ResearchRun]:
        # 1. Check live in-memory cache first (same object the orchestrator mutates)
        if run_id in self._runs:
            return self._runs[run_id]
        # 2. Try persistent database (cross-restart recovery)
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
