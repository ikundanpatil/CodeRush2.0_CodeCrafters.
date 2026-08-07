import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force safe, deterministic, offline defaults for the ENTIRE test session
# before any src module is imported. backend/.env now actually gets loaded
# (see src/config.py), and it may contain real provider selections
# (LLM_PROVIDER=nvidia, SEARCH_PROVIDER=tavily, a real MYSQL_HOST, ...) --
# `load_dotenv(override=False)` never overwrites an already-set env var, so
# these `setdefault` calls win and the test suite stays exactly as
# deterministic/offline as it always was, regardless of .env contents.
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("SEARCH_PROVIDER", "mock")
os.environ.setdefault("SANDBOX_PROVIDER", "mock")
os.environ.setdefault("SANDBOX_ENABLED", "true")
os.environ.setdefault("MYSQL_HOST", "")
# .env sets a real on-disk CHROMA_PERSIST_DIR for production; tests must
# keep using the ephemeral, per-instance-isolated in-memory Chroma client
# (see the uuid-suffix fix in src/memory/chroma_store.py) or fresh_manager
# fixtures across different test files start sharing one on-disk collection.
os.environ.setdefault("CHROMA_PERSIST_DIR", "")
