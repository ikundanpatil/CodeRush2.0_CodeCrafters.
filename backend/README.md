# EvoResearch — Autonomous AI Research Agent

FastAPI backend for EvoResearch. Run standalone from this `backend/` directory; the React frontend lives in [`../frontend`](../frontend).

## Overview

EvoResearch answers a research question by autonomously planning sub-queries, searching the web, safely browsing and sanitizing results, extracting claims into a structured evidence graph, validating research quality, detecting its own research gaps, iterating until quality requirements are met, then verifying its own final answer against the collected evidence and attaching real citations — all under a deterministic safety/policy layer, with a self-evolving research strategy measured against an offline benchmark.

## Architecture

```
USER (text or voice)
  ↓ CONVERSATIONAL SESSION      src/conversation/    backend-side context
  ↓ RESEARCH PLANNING           src/engine/          LLM-generated plan
  ↓ LLM ADAPTER                 src/llm/             mock | openai | nvidia
  ↓ WEB SEARCH                  src/search/          mock | tavily
  ↓ SAFE BROWSER                src/browser/         timeouts, size caps
  ↓ PROMPT INJECTION GUARD      src/security/        sanitizes all content
  ↓ EVIDENCE COLLECTION         src/evidence/
  ↓ EVIDENCE GRAPH              src/evidence/graph   claim→evidence→source
  ↓ QUALITY VALIDATION          src/quality/         deterministic checks
  ↓ RESEARCH GAP DETECTION      src/engine/research_gap.py
  ↓ AUTONOMOUS RESEARCH LOOP    src/engine/research_loop.py
  ↓ SELF-EVOLUTION              src/evolution/       strategy mutation
  ↓ POLICY ENGINE               src/policy/          deterministic allow/deny
  ↓ FINAL ANSWER VERIFICATION   src/verification/    checks the answer text
  ↓ CITATION ENGINE             src/citations/       real sources only
  ↓ PDF RESEARCH REPORT         src/reports/         reportlab
  ↓ VOICE RESPONSE              frontend (Web Speech API)
```

Supporting subsystems: `src/memory/` (MySQL + ChromaDB research memory), `src/sandbox/` (Docker-isolated code execution), `src/benchmark/` (offline strategy benchmarking), `src/feedback/` (answer ratings), `src/storage/` (research run persistence), `src/config.py` (central `.env` loading).

## Features

- Autonomous, bounded, quality-driven research loop with gap detection
- Structured evidence graph with SUPPORTS / CONTRADICTS / DERIVED_FROM edges
- Deterministic research-quality validation (never fabricated metrics)
- Final-answer verification: unsupported claims and fabricated URLs/citations are detected and flagged, never silently kept
- Real citations built only from actually-collected sources
- Real PDF research reports (reportlab) generated from live run data
- Conversational sessions with backend-side context ("what are the disadvantages?" resolves against the current topic)
- Self-evolving research strategy, gated by the Policy Engine and measured by an offline benchmark
- Deterministic Safety/Policy Engine (voice input can never reach a dangerous action)
- Research history, JSON export, sanitized share view, and user feedback

## Tech stack

Python 3.14 · FastAPI · Pydantic v2 · SQLAlchemy 2 · MySQL · ChromaDB · reportlab · pytest — React 19 · Vite · Tailwind v4 · vitest on the frontend.

## Environment setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env      # then fill in real values
```

`.env` is loaded at startup by `src/config.py`. It is gitignored — **never commit it**. Secrets never appear in logs, API responses, or exports.

| Mode | Configuration |
|---|---|
| Development / tests | `LLM_PROVIDER=mock`, `SEARCH_PROVIDER=mock` (fully offline, deterministic) |
| Production | `LLM_PROVIDER=nvidia` (or `openai`), `SEARCH_PROVIDER=tavily` |

The test suite pins the mock providers itself (`tests/conftest.py`), so it stays offline regardless of `.env`.

### Database setup (MySQL)

```sql
CREATE DATABASE IF NOT EXISTS eversoresearch CHARACTER SET utf8mb4;
```

Set `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE`. Tables are created automatically and non-destructively on first use (`everso_research_runs`, `everso_memories`, `everso_strategies`, `everso_conversations`, `everso_feedback`). **If MySQL is unreachable, every store falls back to in-memory mode** so the app still runs — you just lose durability across restarts.

### ChromaDB

Set `CHROMA_PERSIST_DIR` for on-disk vector persistence, or leave it empty for an ephemeral in-memory index.

### NVIDIA setup

```
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=<your key>
LLM_MODEL=<optional, provider default otherwise>
```

### Tavily setup

```
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=<your key>
```

### Docker sandbox setup

`SANDBOX_PROVIDER=docker` requires the Docker CLI on PATH. Use `mock` (the default) for offline development — it never executes anything. Sandbox execution is always mediated by the Policy Engine.

## Running locally

```bash
# Backend
cd backend
uvicorn src.api.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

On startup the backend prints which real backend each subsystem resolved to (LLM provider, search provider, memory backend, vector backend, policy status) — never credentials.

## Testing

```bash
cd backend  && pytest -q
cd frontend && npm run test && npm run build
```

## Voice interface

The Command Center page (`/command-center`) provides a voice-first interface using the browser's Web Speech API (Chrome/Edge). Click the microphone, speak, and the assistant transitions through IDLE → LISTENING → PROCESSING → RESEARCHING → ANALYZING → VERIFYING → COMPLETED (or CANCELLED/ERROR). Supported commands include: research a topic, find more evidence, compare the findings, summarize the research, create a PDF, read the answer, and stop.

Voice is only an input mechanism: transcripts map to a small fixed set of application intents and then to the same REST endpoints the rest of the UI uses. There is no path from speech to shell commands, filesystem access, or policy modification.

## Conversation

`POST /api/conversations` starts a session; `POST /api/conversations/{id}/messages` continues it. Context lives on the backend, so a follow-up such as *"what are the disadvantages?"* is resolved against the session's stored topic rather than treated as a brand-new question.

## Research workflow

1. Question arrives (text or voice, optionally inside a conversation session).
2. Memory retrieval supplies prior research context.
3. The LLM produces a structured research plan.
4. The autonomous loop searches, browses, sanitizes, extracts evidence, builds the evidence graph, validates quality, and detects gaps — iterating until quality is satisfied or the safety-limited iteration cap is reached.
5. The LLM writes a report from verified evidence only.
6. Citations are built from real sources; the final answer is independently verified.
7. Memories are stored; a PDF report is available on demand.

## PDF generation

`GET /api/research/{run_id}/report/pdf` returns a real `application/pdf` document rendered by reportlab from the run's actual data — question, executive summary, key findings, verified/unsupported/contradicted claims, citations, quality metrics, gaps, iteration count, methodology, limitations, sources, timestamp and run ID. It is never a static template and never contains fabricated data.

## API endpoints

**Research** — `POST /api/research`, `GET /api/research/{id}`, `/result`, `/trace`, `/quality`, `/iterations`, `POST /api/research/{id}/cancel`
**History & export** — `GET /api/research/history`, `/history/{id}`, `GET /api/research/{id}/export/json`, `/share`, `GET /api/history`
**Reports** — `POST|GET /api/research/{id}/report`, `GET /api/research/{id}/report/pdf`
**Conversations** — `POST /api/conversations`, `GET /api/conversations`, `GET|DELETE /api/conversations/{id}`, `POST /api/conversations/{id}/messages`
**Feedback** — `POST|GET /api/research/{id}/feedback`
**Memory** — `GET /api/memory/search`, `/memory/{id}`, `/memory/research/{run_id}`, `POST /api/memory`
**Evidence** — `GET /api/evidence/research/{run_id}`, `/evidence/claims/{id}`, `/claims/{id}/evidence`, `/claims/{id}/contradictions`, `/evidence/graph/{run_id}`
**Evolution** — `POST /api/strategy/evolve`, `GET /api/strategy/current`, `/lineage`, `/{id}`
**Policy** — `GET /api/policy/status`, `POST /api/policy/check`
**Benchmarks** — `POST /api/benchmark/run`, `GET /api/benchmark/{id}`, `/results`, `POST /api/benchmark/compare`, `GET /api/benchmark/history/list`

## Security

- **Prompt injection**: all retrieved content is scanned and sanitized by `src/security/guard.py` before reaching the LLM, and is passed inside explicit untrusted-content blocks that the system prompt instructs the model to treat as data only.
- **Policy Engine**: deterministic allow/deny for every sensitive action. `MODIFY_CODE`, `MODIFY_SECURITY`, `MODIFY_POLICY`, `ACCESS_SECRET`, `EXECUTE_HOST_COMMAND` and unknown actions are always denied; no security decision is delegated to an LLM.
- **Self-evolution boundary**: an explicit field allowlist plus hard safety limits — an evolved strategy can never modify code, policy, or security, nor exceed the global iteration/source caps.
- **Sandbox**: agent-produced code only ever runs through the Docker sandbox abstraction, never on the host.
- **Secrets**: never logged, never returned by any endpoint, never included in PDFs or exports.

## Project phases

1. Foundation + LLM adapter · 2. Web search + safe browser · 3. Memory (MySQL + ChromaDB) · 4. Evidence graph · 5. Sandbox + research quality · 6. Autonomous research loop · 7. Self-evolution · 8. Safety/policy engine · 9. Benchmarks + improvement tests · 10. Voice interface / Command Center · Final: configuration, persistence, conversation, final-answer verification, citations, PDF reports, history/export/share, feedback.

## Known limitations

- Voice input requires a Chromium-based browser (Web Speech API); microphone and speech-synthesis behavior cannot be verified headlessly.
- Research progress uses polling rather than SSE/WebSockets.
- Verification is deterministic and evidence-linkage based; it detects unsupported claims, fabricated URLs, bad citation markers and source-count mismatches, but does not perform semantic entailment checking of every sentence.
- The Docker sandbox has no caller in the research pipeline today; it is exercised through the policy layer and its own tests.
- Real-provider (NVIDIA/Tavily) runs depend on external services and on those services returning absolute URLs — Tavily occasionally returns relative redirect URLs, which the verifier correctly flags as invalid citations.
