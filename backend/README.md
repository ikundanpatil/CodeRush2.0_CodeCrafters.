# EvoResearch Backend

FastAPI backend for EvoResearch. Run standalone from this `backend/` directory; the React frontend lives in [`../frontend`](../frontend).

## Phase 1 — LLM Adapter

The orchestrator's planning and report-generation steps are driven by a provider-independent LLM adapter (`src/llm/`) instead of hardcoded templates:

- `src/llm/base.py` — the `LLMAdapter` interface (`generate(prompt, system_prompt=None, **kwargs) -> str`) and typed errors (`LLMConfigError`, `LLMProviderError`, `LLMTimeoutError`, `LLMRateLimitError`, `LLMOutputError`).
- `src/llm/providers/` — `mock.py` (offline, default, used by tests), `openai.py`, `nvidia.py` (NVIDIA NIM, OpenAI-compatible API).
- `src/llm/adapter.py` — `get_llm_adapter()` factory, selects a provider from `LLM_PROVIDER`.

The orchestrator (`src/engine/orchestrator.py`) calls `llm.generate()` to produce a structured `ResearchPlan` (objective, sub-queries, source types, things to verify) before searching, and a structured `ResearchReportLLM` (answer, key findings, limitations) after evidence is collected — both validated with Pydantic. Invalid JSON output is retried once with a stricter prompt; if it still fails, the run degrades gracefully (a fallback plan/report plus an `llm_planning_failed` / `llm_report_failed` trace event) instead of crashing. If the configured provider fails to initialize (e.g. missing API key), the orchestrator logs it and falls back to the Mock provider so a run never hard-fails on LLM configuration.

Real source URLs always come from the pipeline's verified `Source` list, never from the LLM, to avoid fabricated citations.

**Security boundary**: external/untrusted research content is passed inside an explicit `<UNTRUSTED_RESEARCH_CONTENT>` / `<UNTRUSTED_RESEARCH_CONTEXT>` block within the user prompt, never in the system prompt. The system prompt explicitly instructs the model to treat that block as data only and ignore any embedded directives. The existing prompt-injection security guard still scans and sanitizes all retrieved content before it ever reaches the LLM.

## Phase 3 — Research Memory

EvoResearch also includes a Phase 3 research-memory layer that allows the agent to remember useful findings from earlier research runs and retrieve them as context for future questions. The system is designed to preserve the safety principle that old memories are only previous research context and must still be verified with fresh evidence.

## Phase 3 Architecture

- MySQL stores canonical structured memories and metadata.
- ChromaDB stores semantic vector indexes for similarity search.
- The memory layer is coordinated through `MemoryManager`.
- The orchestrator retrieves memory before planning, then still performs fresh research and evidence verification.

## Memory Lifecycle

1. A completed research run is analyzed and transformed into concise memories.
2. Memories are stored in MySQL and indexed in ChromaDB.
3. A future question triggers semantic retrieval from ChromaDB.
4. The canonical memory records are loaded from MySQL.
5. The planner receives the recalled context, but the pipeline still performs fresh research and security checks.

## Environment Variables

Copy [.env.example](.env.example) to `.env` and configure. Never commit `.env`.

- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
- `CHROMA_PERSIST_DIR`
- `EVORESEARCH_EMBEDDING_PROVIDER`
- `OPENAI_API_KEY` (used for OpenAI embeddings, and for the OpenAI LLM provider)
- `LLM_PROVIDER` — `mock` (default), `openai`, or `nvidia`
- `LLM_MODEL` — model name for the chosen provider (optional, provider has a default)
- `NVIDIA_API_KEY` — required when `LLM_PROVIDER=nvidia`
- `CORS_ORIGINS` — comma-separated allowed frontend origins (default `http://localhost:5173`)

## Backend Setup

```bash
cd backend
pip install -r requirements.txt
pytest -q
uvicorn src.api.main:app --reload --port 8000
```

## API Endpoints

- `GET /api/memory/search?q=<query>&top_k=5`
- `GET /api/memory/{memory_id}`
- `GET /api/memory/research/{research_run_id}`
- `POST /api/memory`

## Demo Flow

1. Submit a first research question such as: "Compare the impact of generative AI on software developer productivity."
2. Let the agent complete the run and store memories.
3. Submit a follow-up question such as: "How does AI affect developer productivity?"
4. The trace should show memory retrieval followed by fresh research and verification.

## Testing

The repository includes Phase 1 (core + LLM adapter) and Phase 3 (memory) tests, all run from `backend/`:

```bash
cd backend
pytest -q
```

Tests always use `LLM_PROVIDER=mock` (the default) and require no API keys or paid services.

## Notes

The memory subsystem degrades gracefully. If MySQL, ChromaDB, or embeddings are unavailable, the pipeline continues and records the issue in the research trace instead of crashing. The LLM adapter degrades the same way: an unavailable/misconfigured provider or malformed model output falls back to the Mock provider or a minimal fallback plan/report, and is recorded in the trace, rather than failing the run.
