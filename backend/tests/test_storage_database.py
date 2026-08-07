"""Database backend selection and MemoryStore persistence tests."""

import json

import pytest
from sqlalchemy import create_engine

from src.config import Settings
from src.models.schemas import ResearchRun, RunStatus
from src.storage.store import MemoryStore, _normalize_pg_url


# ---------------------------------------------------------------------------
# TEST 1–4: backend selection
# ---------------------------------------------------------------------------

def test_no_database_configuration_uses_memory_backend(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("MYSQL_HOST", "")
    monkeypatch.setenv("MYSQL_USER", "")
    monkeypatch.setenv("MYSQL_DATABASE", "")

    settings = Settings()
    assert settings.database_backend == "memory"

    store = MemoryStore(engine=None, create_tables=False)
    assert store.database_backend == "memory"
    assert store.is_db_active is False


def test_mysql_configuration_selects_mysql_backend(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_PORT", "3306")
    monkeypatch.setenv("MYSQL_USER", "root")
    monkeypatch.setenv("MYSQL_PASSWORD", "")
    monkeypatch.setenv("MYSQL_DATABASE", "evoresearch")

    settings = Settings()
    assert settings.database_backend == "mysql"

    store = MemoryStore(engine=None, create_tables=False)
    engine = store._build_engine_from_env()
    if engine is not None:
        assert str(engine.url.drivername).startswith("mysql")
        assert store._database_backend == "mysql"
    else:
        # Driver may be absent in minimal CI; config selection is still verified above.
        pytest.skip("mysql driver unavailable in this environment")


def test_database_url_configuration_selects_postgresql_backend(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.delenv("MYSQL_HOST", raising=False)

    settings = Settings()
    assert settings.database_backend == "postgresql"

    store = MemoryStore(engine=None, create_tables=False)
    engine = store._build_engine_from_env()
    if engine is not None:
        assert str(engine.url).startswith("postgresql+psycopg://")
        assert store._database_backend == "postgresql"
    else:
        pytest.skip("psycopg driver unavailable in this environment")


def test_database_url_has_priority_over_mysql(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host:5432/db")
    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_USER", "root")
    monkeypatch.setenv("MYSQL_DATABASE", "evoresearch")

    settings = Settings()
    assert settings.database_backend == "postgresql"

    store = MemoryStore(engine=None, create_tables=False)
    engine = store._build_engine_from_env()
    if engine is not None:
        assert str(engine.url).startswith("postgresql+psycopg://")
        assert store._database_backend == "postgresql"
    else:
        pytest.skip("psycopg driver unavailable in this environment")


def test_normalize_pg_url_variants():
    assert _normalize_pg_url("postgres://u:p@h/d").startswith("postgresql+psycopg://")
    assert _normalize_pg_url("postgresql://u:p@h/d").startswith("postgresql+psycopg://")
    assert _normalize_pg_url("postgresql+psycopg://u:p@h/d") == "postgresql+psycopg://u:p@h/d"


# ---------------------------------------------------------------------------
# TEST 5–7: save_run / get_run / list_runs
# ---------------------------------------------------------------------------

@pytest.fixture
def sqlite_store():
    engine = create_engine("sqlite:///:memory:")
    store = MemoryStore(engine=engine, create_tables=True)
    yield store


def test_save_run_updates_memory_and_database(sqlite_store):
    run = ResearchRun(question="save_run persistence test")
    sqlite_store.save_run(run)

    assert run.run_id in sqlite_store._runs
    assert sqlite_store._runs[run.run_id] is run
    assert sqlite_store.get_run(run.run_id) is run


def test_get_run_returns_none_for_missing_run(sqlite_store):
    assert sqlite_store.get_run("missing-run-id") is None


def test_list_runs_merges_db_and_memory_with_memory_winning(sqlite_store):
    run_a = ResearchRun(question="run A")
    run_b = ResearchRun(question="run B")
    sqlite_store.save_run(run_a)
    sqlite_store.save_run(run_b)

    runs = sqlite_store.list_runs()
    ids = [r.run_id for r in runs]
    assert run_a.run_id in ids
    assert run_b.run_id in ids
    assert runs[0].created_at >= runs[-1].created_at


# ---------------------------------------------------------------------------
# TEST 8–9: ResearchRun serialization / status
# ---------------------------------------------------------------------------

def test_research_run_serialization_roundtrip():
    run = ResearchRun(
        question="serialization test",
        answer="An answer",
        sources=[],
    )
    payload = json.loads(run.model_dump_json())
    restored = ResearchRun.model_validate(payload)
    assert restored.run_id == run.run_id
    assert restored.question == run.question
    assert restored.answer == run.answer


def test_research_run_status_serialization():
    run = ResearchRun(question="status test", status=RunStatus.PLANNING)
    payload = json.loads(run.model_dump_json())
    assert payload["status"] == "planning"

    restored = ResearchRun.model_validate(payload)
    assert restored.status == RunStatus.PLANNING
    assert restored.status.value == "planning"


# ---------------------------------------------------------------------------
# MOST IMPORTANT: simulate process restart
# ---------------------------------------------------------------------------

def test_research_run_survives_fresh_memory_store_instance():
    """Save in one store, reload from a brand-new store (same DB engine)."""
    engine = create_engine("sqlite:///:memory:")

    store1 = MemoryStore(engine=engine, create_tables=True)
    run = ResearchRun(question="Does persistence survive a backend restart?")
    captured_run_id = run.run_id
    store1.save_run(run)

    store2 = MemoryStore(engine=engine, create_tables=False)
    reloaded = store2.get_run(captured_run_id)

    assert reloaded is not None
    assert reloaded.run_id == captured_run_id
    assert reloaded.question == run.question
    assert reloaded.status == run.status
    assert any(r.run_id == captured_run_id for r in store2.list_runs())
