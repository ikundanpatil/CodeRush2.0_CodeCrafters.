"""Phase 7 strategy persistence.

Database priority (mirrors src/storage/store.py):
    1. DATABASE_URL  → PostgreSQL (Render production)
    2. MYSQL_*       → local MySQL (development)
    3. (none)        → volatile in-memory dict (degraded mode)

Same pattern as `src/memory/mysql_store.py`: SQLAlchemy 2.0 declarative
mapping, non-destructive `create_all`, and a volatile in-memory fallback so
evolution keeps working (just non-durably) if the database is unreachable.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import JSON, Float, String, Text

from src.engine import research_loop as research_loop_module
from src.evolution.models import Strategy, StrategyParams, StrategyStatus
from src.quality import rules as quality_rules


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class StrategyRecord(Base):
    __tablename__ = "everso_strategies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    generation: Mapped[int] = mapped_column()
    parent_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    params: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), index=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reasoning: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(64))
    accepted_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    def to_strategy(self) -> Strategy:
        return Strategy(
            id=self.id,
            generation=self.generation,
            parent_id=self.parent_id,
            params=StrategyParams(**self.params),
            status=StrategyStatus(self.status),
            score=self.score,
            reasoning=self.reasoning or "",
            created_at=self.created_at,
            accepted_at=self.accepted_at,
        )


def _env(key: str, default=None):
    return os.getenv(key, default)


_logger = logging.getLogger(__name__)


def _normalize_pg_url(url: str) -> str:
    """Normalize postgres:// or postgresql:// → postgresql+psycopg:// for SQLAlchemy."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


class EvolutionStore:
    """Strategy lineage store. MySQL primary, in-memory fallback for degraded mode."""

    def __init__(self, engine: Optional[Engine] = None, create_tables: bool = True):
        self._mysql_active = False
        self._engine: Optional[Engine] = None
        self._session = None
        self._fallback: Dict[str, Strategy] = {}

        if engine is None:
            engine = self._build_engine_from_env()
        self._try_connect(engine, create_tables)

    def _build_engine_from_env(self) -> Optional[Engine]:
        # 1. DATABASE_URL takes priority (Render PostgreSQL)
        db_url = _env("DATABASE_URL")
        if db_url:
            try:
                return create_engine(
                    _normalize_pg_url(db_url),
                    pool_pre_ping=True,
                    pool_recycle=3600,
                    connect_args={"connect_timeout": 5},
                )
            except Exception as e:
                _logger.warning(
                    "EvolutionStore: DATABASE_URL engine creation failed (%s: %s); trying MYSQL_*.",
                    type(e).__name__, e,
                )

        # 2. Local MySQL
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
        except Exception as e:
            _logger.warning(
                "EvolutionStore: MySQL engine creation failed (%s: %s); using in-memory fallback.",
                type(e).__name__, e,
            )
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
        except Exception as e:
            _logger.warning(
                "EvolutionStore: DB connection test failed (%s: %s); using in-memory fallback.",
                type(e).__name__, e,
            )
            self._mysql_active = False

    @property
    def is_mysql_active(self) -> bool:
        return self._mysql_active

    def ping(self) -> bool:
        return self._mysql_active

    def _record_from_strategy(self, strategy: Strategy) -> StrategyRecord:
        return StrategyRecord(
            id=strategy.id,
            generation=strategy.generation,
            parent_id=strategy.parent_id,
            params=strategy.params.model_dump(),
            status=strategy.status.value,
            score=strategy.score,
            reasoning=strategy.reasoning or "",
            created_at=strategy.created_at or _utc_now(),
            accepted_at=strategy.accepted_at,
        )

    def save(self, strategy: Strategy) -> Strategy:
        if not strategy.created_at:
            strategy.created_at = _utc_now()
        if self._mysql_active:
            try:
                with self._session() as session:
                    session.merge(self._record_from_strategy(strategy))
                    session.commit()
                return strategy
            except Exception:
                self._fallback[strategy.id] = strategy.model_copy()
                return strategy
        self._fallback[strategy.id] = strategy.model_copy()
        return strategy

    def get(self, strategy_id: str) -> Optional[Strategy]:
        if self._mysql_active:
            try:
                with self._session() as session:
                    record = session.get(StrategyRecord, strategy_id)
                    return record.to_strategy() if record else None
            except Exception:
                return self._fallback.get(strategy_id)
        return self._fallback.get(strategy_id)

    def list_lineage(self) -> List[Strategy]:
        if self._mysql_active:
            try:
                with self._session() as session:
                    records = (
                        session.query(StrategyRecord)
                        .order_by(StrategyRecord.generation.desc())
                        .all()
                    )
                    return [r.to_strategy() for r in records]
            except Exception:
                pass
        return sorted(self._fallback.values(), key=lambda s: s.generation, reverse=True)

    def _seed_generation_zero(self) -> Strategy:
        params = StrategyParams(
            min_sources=quality_rules.min_sources(),
            min_evidence=quality_rules.min_evidence(),
            min_supported_claims=quality_rules.min_supported_claims(),
            max_iterations=research_loop_module._max_iterations(),
            max_results_per_query=research_loop_module.MAX_RESULTS_PER_QUERY,
            max_sources_per_iteration=research_loop_module.MAX_SOURCES_PER_ITERATION,
        )
        strategy = Strategy(
            generation=0,
            parent_id=None,
            params=params,
            status=StrategyStatus.ACCEPTED,
            reasoning="Seeded from default environment configuration.",
            created_at=_utc_now(),
            accepted_at=_utc_now(),
        )
        return self.save(strategy)

    def get_champion(self) -> Strategy:
        accepted = [s for s in self.list_lineage() if s.status == StrategyStatus.ACCEPTED]
        if not accepted:
            return self._seed_generation_zero()
        return max(accepted, key=lambda s: s.generation)


_evolution_store: Optional[EvolutionStore] = None


def get_evolution_store() -> EvolutionStore:
    global _evolution_store
    if _evolution_store is None:
        _evolution_store = EvolutionStore()
    return _evolution_store
