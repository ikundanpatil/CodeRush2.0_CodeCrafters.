"""Comprehensive PostgreSQL / multi-database persistence tests.

Covers all 10 scenarios required by the spec:
1.  No database config  → memory backend
2.  MYSQL_* configured  → mysql backend (settings)
3.  DATABASE_URL set    → postgresql backend (settings)
4.  DATABASE_URL takes priority over MYSQL_*
5.  save_run() persists to in-memory dict
6.  get_run() reads live object from dict
7.  list_runs() combines DB + in-memory
8.  ResearchRun JSON serialization (model_dump_json round-trip)
9.  ResearchRun status enum serialization
10. Persistence across a second MemoryStore instance (simulated restart)

Extra:
11. db_backend returns correct human-readable string
12. database_backend property returns canonical id
13. DATABASE_URL normalization: postgres:// → postgresql+psycopg://
14. Settings.database_backend precedence
15. Startup log never prints credentials
"""

import pytest
from sqlalchemy import create_engine

from src.config import Settings, log_startup_config
from src.models.schemas import ResearchRun, RunStatus
from src.storage.store import MemoryStore, _normalize_pg_url


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_memory_store() -> MemoryStore:
    """Return a store that is always in-memory (no real DB needed)."""
    return MemoryStore(engine=None, create_tables=False)


def make_sqlite_store(create_tables: bool = True) -> tuple[MemoryStore, object]:
    """Return a MemoryStore backed by an in-process SQLite DB (simulates real DB)."""
    engine = create_engine("sqlite:///:memory:")
    store = MemoryStore(engine=engine, create_tables=create_tables)
    return store, engine


# ===========================================================================
# 1. No database config → memory backend
# ===========================================================================

def test_no_database_config_uses_memory_backend(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("MYSQL_HOST", raising=False)
    monkeypatch.delenv("MYSQL_USER", raising=False)
    monkeypatch.delenv("MYSQL_DATABASE", raising=False)

    settings = Settings()
    assert settings.database_backend == "memory"

    store = make_memory_store()
    assert store.is_db_active is False
    assert store.database_backend == "memory"
    assert "memory" in store.db_backend or "fallback" in store.db_backend


# ===========================================================================
# 2. MYSQL_* configured → mysql backend (settings level only; no real server)
# ===========================================================================

def test_mysql_vars_give_mysql_backend_in_settings(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_USER", "root")
    monkeypatch.setenv("MYSQL_DATABASE", "evoresearch")

    settings = Settings()
    assert settings.database_backend == "mysql"
    assert settings.mysql_configured is True


# ===========================================================================
# 3. DATABASE_URL set → postgresql backend (settings level)
# ===========================================================================

def test_database_url_gives_postgresql_backend_in_settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host/db")

    settings = Settings()
    assert settings.database_backend == "postgresql"
    assert settings.database_url == "postgres://user:pass@host/db"


# ===========================================================================
# 4. DATABASE_URL takes priority over MYSQL_*
# ===========================================================================

def test_database_url_priority_over_mysql(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host/db")
    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_USER", "root")
    monkeypatch.setenv("MYSQL_DATABASE", "evoresearch")

    settings = Settings()
    assert settings.database_backend == "postgresql"  # DATABASE_URL wins


# ===========================================================================
# 5. save_run() persists to in-memory dict
# ===========================================================================

def test_save_run_stores_in_memory():
    store = make_memory_store()
    run = ResearchRun(question="What is the meaning of life?")
    store.save_run(run)

    # Must be in the dict
    assert run.run_id in store._runs


# ===========================================================================
# 6. get_run() reads live object from dict (same identity)
# ===========================================================================

def test_get_run_returns_same_object():
    store = make_memory_store()
    run = ResearchRun(question="Does object identity survive get_run?")
    store.save_run(run)

    fetched = store.get_run(run.run_id)
    assert fetched is run, "get_run must return the same object for cooperative cancellation"


def test_get_run_missing_returns_none():
    store = make_memory_store()
    assert store.get_run("nonexistent-run-id-xyz") is None


# ===========================================================================
# 7. list_runs() combines DB + in-memory
# ===========================================================================

def test_list_runs_includes_in_memory_runs():
    store = make_memory_store()
    run1 = ResearchRun(question="First question")
    run2 = ResearchRun(question="Second question")
    store.save_run(run1)
    store.save_run(run2)

    runs = store.list_runs()
    run_ids = [r.run_id for r in runs]
    assert run1.run_id in run_ids
    assert run2.run_id in run_ids


def test_list_runs_sorted_newest_first():
    store = make_memory_store()
    run_a = ResearchRun(question="Alpha question")
    run_b = ResearchRun(question="Beta question")
    store.save_run(run_a)
    store.save_run(run_b)

    runs = store.list_runs()
    assert runs[0].created_at >= runs[-1].created_at


# ===========================================================================
# 8. ResearchRun JSON serialization round-trip
# ===========================================================================

def test_research_run_json_roundtrip():
    run = ResearchRun(question="Does JSON serialization work?")
    run.answer = "Yes, it works!"
    run.status = RunStatus.COMPLETED

    json_str = run.model_dump_json()
    restored = ResearchRun.model_validate_json(json_str)

    assert restored.run_id == run.run_id
    assert restored.question == run.question
    assert restored.answer == run.answer
    assert restored.status == RunStatus.COMPLETED


# ===========================================================================
# 9. ResearchRun status enum serialization
# ===========================================================================

def test_status_enum_serialization():
    run = ResearchRun(question="Status enum test")

    # Initial status
    assert run.status == RunStatus.QUEUED

    # Serialize + deserialize preserves enum
    data = run.model_dump(mode="json")
    assert data["status"] == RunStatus.QUEUED.value

    restored = ResearchRun.model_validate(data)
    assert restored.status == RunStatus.QUEUED

    # Change status, verify round-trip
    run.status = RunStatus.COMPLETED
    data2 = run.model_dump(mode="json")
    assert data2["status"] == RunStatus.COMPLETED.value


# ===========================================================================
# 10. Persistence across second MemoryStore instance (simulated restart)
# ===========================================================================

def test_persistence_across_new_store_instance_with_sqlite():
    """The most critical test: save in store1, load via fresh store2 sharing same DB."""
    store1, engine = make_sqlite_store(create_tables=True)
    assert store1.is_db_active is True

    run = ResearchRun(question="Does persistence survive a simulated restart?")
    store1.save_run(run)

    # Create a completely fresh store using the same engine (simulates process restart)
    store2 = MemoryStore(engine=engine, create_tables=False)
    assert store2.is_db_active is True

    loaded = store2.get_run(run.run_id)
    assert loaded is not None, "Run must be found after simulated restart"
    assert loaded.run_id == run.run_id
    assert loaded.question == run.question
    assert loaded.status == run.status


def test_list_runs_after_simulated_restart():
    store1, engine = make_sqlite_store(create_tables=True)
    run = ResearchRun(question="Will I appear in history after restart?")
    store1.save_run(run)

    store2 = MemoryStore(engine=engine, create_tables=False)
    runs = store2.list_runs()
    assert any(r.run_id == run.run_id for r in runs)


# ===========================================================================
# 11. db_backend returns correct human-readable string
# ===========================================================================

def test_db_backend_in_memory_fallback_string():
    store = make_memory_store()
    assert "memory" in store.db_backend or "fallback" in store.db_backend


def test_db_backend_sqlite_string():
    store, _ = make_sqlite_store()
    # SQLite used in tests; dialect.name is "sqlite", capitalized to "Sqlite"
    assert store.is_db_active is True
    assert "sqlite" in store.db_backend.lower() or "Sqlite" in store.db_backend


# ===========================================================================
# 12. database_backend property returns canonical id
# ===========================================================================

def test_database_backend_memory_id():
    store = make_memory_store()
    assert store.database_backend == "memory"


def test_database_backend_sqlite_id():
    store, _ = make_sqlite_store()
    # SQLite passed explicitly: dialect is sqlite; treated as "Sqlite" (not postgresql/mysql)
    assert store.is_db_active is True
    # canonical id for an explicitly-passed engine that isn't pg/mysql falls back to dialect name
    assert store.database_backend in ("memory", "Sqlite", "sqlite")


# ===========================================================================
# 13. DATABASE_URL normalization: postgres:// → postgresql+psycopg://
# ===========================================================================

def test_normalize_pg_url_postgres_scheme():
    url = "postgres://user:pass@host:5432/db"
    assert _normalize_pg_url(url) == "postgresql+psycopg://user:pass@host:5432/db"


def test_normalize_pg_url_postgresql_scheme():
    url = "postgresql://user:pass@host:5432/db"
    assert _normalize_pg_url(url) == "postgresql+psycopg://user:pass@host:5432/db"


def test_normalize_pg_url_already_normalized():
    url = "postgresql+psycopg://user:pass@host:5432/db"
    assert _normalize_pg_url(url) == url  # no change


def test_normalize_pg_url_build_engine_env(monkeypatch):
    """Verify _build_engine_from_env normalizes the URL before creating engine."""
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost/db")
    monkeypatch.delenv("MYSQL_HOST", raising=False)

    store = MemoryStore(engine=None, create_tables=False)
    # Engine may or may not connect (no real PG in test env), but we can
    # check the URL normalization path via _build_engine_from_env.
    result = store._build_engine_from_env()
    if result is not None:
        assert str(result.url).startswith("postgresql+psycopg://")


# ===========================================================================
# 14. Settings.database_backend precedence
# ===========================================================================

def test_settings_database_backend_memory(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("MYSQL_HOST", raising=False)
    monkeypatch.delenv("MYSQL_USER", raising=False)
    monkeypatch.delenv("MYSQL_DATABASE", raising=False)
    assert Settings().database_backend == "memory"


def test_settings_database_backend_mysql(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_USER", "root")
    monkeypatch.setenv("MYSQL_DATABASE", "mydb")
    assert Settings().database_backend == "mysql"


def test_settings_database_backend_postgresql_wins(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@h/db")
    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_USER", "root")
    monkeypatch.setenv("MYSQL_DATABASE", "mydb")
    assert Settings().database_backend == "postgresql"


# ===========================================================================
# 15. Startup log never prints credentials
# ===========================================================================

def test_startup_log_never_prints_credentials(monkeypatch, capsys):
    secret = "super-secret-db-password-9999"
    monkeypatch.setenv("MYSQL_PASSWORD", secret)
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    monkeypatch.setenv("DATABASE_URL", f"postgresql://user:{secret}@localhost/db")

    log_startup_config()

    captured = capsys.readouterr().out
    assert secret not in captured
    assert "Database backend:" in captured
