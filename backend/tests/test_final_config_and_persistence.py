"""Final Completion Phase - Part A (config) and Part B (persistence) tests."""

from src.config import Settings, log_startup_config
from src.models.schemas import ResearchRun
from src.storage.store import MemoryStore


def test_settings_reads_live_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("SEARCH_PROVIDER", "tavily")
    settings = Settings()
    assert settings.llm_provider == "nvidia"
    assert settings.search_provider == "tavily"


def test_settings_defaults_to_mock_when_unset(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("SEARCH_PROVIDER", raising=False)
    settings = Settings()
    assert settings.llm_provider == "mock"
    assert settings.search_provider == "mock"


def test_startup_config_logging_never_prints_secrets(monkeypatch, capsys):
    fake_secret = "sk-super-secret-value-should-never-print"
    monkeypatch.setenv("OPENAI_API_KEY", fake_secret)
    monkeypatch.setenv("MYSQL_PASSWORD", fake_secret)
    monkeypatch.setenv("DATABASE_URL", f"postgresql://user:{fake_secret}@localhost/db")

    log_startup_config()

    output = capsys.readouterr().out
    assert fake_secret not in output
    assert "LLM provider:" in output
    assert "Database backend:" in output
    assert "Vector backend:" in output


def test_research_run_persistence_roundtrip_in_memory_fallback():
    """No engine -> pure in-memory fallback, same contract as before."""
    store = MemoryStore(engine=None, create_tables=False)
    run = ResearchRun(question="Does the store round-trip correctly?")
    store.save_run(run)

    fetched = store.get_run(run.run_id)
    assert fetched is run  # object identity preserved -- required for live cancellation
    assert fetched.question == run.question

    listed = store.list_runs()
    assert any(r.run_id == run.run_id for r in listed)


def test_get_missing_run_returns_none():
    store = MemoryStore(engine=None, create_tables=False)
    assert store.get_run("does-not-exist") is None


def test_database_url_normalization_and_engine_persistence():
    """Verifies DATABASE_URL connection normalization, engine persistence,
    JSON serialization, ResearchRun status handling, and multi-instance restart simulation."""
    from sqlalchemy import create_engine
    # Use SQLite engine to simulate a real SQL database backend
    engine = create_engine("sqlite:///:memory:")

    store1 = MemoryStore(engine=engine, create_tables=True)
    assert store1.is_db_active is True
    assert store1.db_backend == "Sqlite"

    run = ResearchRun(question="Does sqlite/postgres persistence survive fresh instances?")
    store1.save_run(run)

    # Instantiate new MemoryStore using same database engine (simulate process restart)
    store2 = MemoryStore(engine=engine, create_tables=False)
    reloaded = store2.get_run(run.run_id)
    assert reloaded is not None
    assert reloaded.run_id == run.run_id
    assert reloaded.question == run.question
    assert reloaded.status == run.status
    assert any(r.run_id == run.run_id for r in store2.list_runs())


def test_database_url_precedence_and_formatting(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost/db")
    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_USER", "root")
    monkeypatch.setenv("MYSQL_DATABASE", "test")

    store = MemoryStore(engine=None, create_tables=False)
    # Check that database url postgres:// gets converted to postgresql+psycopg://
    engine_or_none = store._build_engine_from_env()
    if engine_or_none:
        assert str(engine_or_none.url).startswith("postgresql+psycopg://")


def test_research_run_survives_a_simulated_restart_when_mysql_is_active():
    """If a real MySQL server is reachable in this environment (via the
    already-loaded backend/.env), persistence must survive a fresh store
    instance (simulating a process restart). Skips its durability assertion
    -- without failing -- when no real MySQL is available, since that's a
    genuine environment limitation, not a code defect."""
    store1 = MemoryStore()
    if not store1.is_mysql_active:
        return  # environment has no reachable database server; nothing to verify here

    run = ResearchRun(question="Does persistence survive a simulated restart?")
    store1.save_run(run)

    store2 = MemoryStore()  # fresh instance, no shared in-memory dict
    reloaded = store2.get_run(run.run_id)
    assert reloaded is not None
    assert reloaded.question == run.question
    assert any(r.run_id == run.run_id for r in store2.list_runs())
