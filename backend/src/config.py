"""Central configuration entry point.

The single, critical fix this module provides: `backend/.env` was never
actually loaded into the process before this existed (no `python-dotenv`,
no `--env-file`), so every `os.getenv(...)` call across the app -- in
`llm/adapter.py`, `search/factory.py`, `sandbox/factory.py`,
`quality/rules.py`, `memory/mysql_store.py`, `policy/rules.py`, etc. -- was
silently seeing nothing and always falling back to mock/offline defaults,
regardless of what `.env` said.

Importing this module (done once, at the top of `src/api/main.py`) loads
`.env` into `os.environ` with `override=False` -- it fills in anything not
already set, but never clobbers a real env var or a test's explicit
override. This is deliberately NOT a wholesale rewrite of every existing
`os.getenv()` call site into a settings object (that would be a large,
risky change to already-working code); those call sites keep working
exactly as before, they just finally see real values. New modules (added
in this phase) read configuration through `get_settings()` below instead of
scattering their own `os.getenv()` calls.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(key, default)
    return value


class Settings:
    """Read-only, always-live view of the environment (values are read on
    each access, not cached at import time, so tests that monkeypatch
    `os.environ` per-test still work exactly as the rest of the app does)."""

    # -- LLM ---------------------------------------------------------------
    @property
    def llm_provider(self) -> str:
        return (_env("LLM_PROVIDER", "mock") or "mock").strip().lower()

    @property
    def llm_model(self) -> Optional[str]:
        return _env("LLM_MODEL")

    # -- Search --------------------------------------------------------------
    @property
    def search_provider(self) -> str:
        return (_env("SEARCH_PROVIDER", "mock") or "mock").strip().lower()

    # -- Sandbox -------------------------------------------------------------
    @property
    def sandbox_provider(self) -> str:
        return (_env("SANDBOX_PROVIDER", "mock") or "mock").strip().lower()

    @property
    def sandbox_enabled(self) -> bool:
        return (_env("SANDBOX_ENABLED", "true") or "true").strip().lower() != "false"

    # -- MySQL ---------------------------------------------------------------
    @property
    def mysql_configured(self) -> bool:
        return bool(_env("MYSQL_HOST") and _env("MYSQL_USER") and _env("MYSQL_DATABASE"))

    # -- Chroma --------------------------------------------------------------
    @property
    def chroma_persist_dir(self) -> Optional[str]:
        return _env("CHROMA_PERSIST_DIR")

    # -- Policy / quality (documented here; still read live by their own
    # modules -- see module docstring for why those call sites are unchanged)
    @property
    def policy_engine_enabled(self) -> bool:
        return (_env("POLICY_ENGINE_ENABLED", "true") or "true").strip().lower() != "false"


settings = Settings()


def log_startup_config() -> None:
    """Prints which REAL backend is active for each subsystem. Never logs a
    credential -- only provider/backend names, which are not secrets."""
    from src.memory.mysql_store import get_mysql_store
    from src.memory.chroma_store import chroma_store

    memory_backend = "MySQL" if get_mysql_store().is_mysql_active else "in-memory fallback"
    vector_backend = "ChromaDB" if chroma_store.is_chroma_active else "in-memory fallback"

    lines = [
        "=" * 60,
        "EvoResearch configuration",
        f"  LLM provider:      {settings.llm_provider}",
        f"  Search provider:   {settings.search_provider}",
        f"  Sandbox provider:  {settings.sandbox_provider if settings.sandbox_enabled else 'disabled'}",
        f"  Memory backend:    {memory_backend}",
        f"  Vector backend:    {vector_backend}",
        f"  Policy engine:     {'active' if settings.policy_engine_enabled else 'inactive'}",
        "=" * 60,
    ]
    print("\n".join(lines))
