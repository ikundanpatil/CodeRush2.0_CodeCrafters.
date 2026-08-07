# CodeRush 2.0 | Team Project Repository

## Project Information

- **Team Name:** CodeCrafters
- **Project Title:** Autonomous AI Research Agent
- **Track/Theme:** Agentic AI
## Project Description

**ResearchMind AI** is an autonomous research agent built specifically for **deep research**, unlike general-purpose chatbots that mainly focus on answering questions.

It:

* 🔍 **Searches multiple web & academic sources**
* 📚 Uses **RAG & Grounding** to base answers on retrieved evidence
* ✅ **Verifies evidence and citations**
* 🧠 Uses a **Critique Loop** to identify weak or unsupported information
* 📊 Generates **structured, traceable research reports**
* 🎛️ Lets users **choose their AI model and research sources**

**Key Difference:**
**Normal chatbots → Answer questions**
**ResearchMind → Researches, verifies, and shows the evidence behind the answer**

## 🛠️ Tech Stack

### Frontend

* **React.js** – Interactive user interface
* **Vite** – Fast development and build tool
* **Tailwind CSS** – Responsive and modern UI
* **JavaScript** – Frontend logic

### Backend

* **Python** – Core backend and AI logic
* **FastAPI** – REST API and agent orchestration

### AI & Agents

* **OpenAI** – LLM provider
* **Claude** – LLM provider
* **RAG (Retrieval-Augmented Generation)** – Evidence-based response generation
* **Grounding** – Connects AI responses to retrieved sources
* **Agentic Workflow** – Planning, research, analysis, and verification
* **Critic & Verification Loop** – Reviews generated results and citations

### Research & Data Sources

* **Tavily** – Web research and search
* **Semantic Scholar** – Academic research
* **arXiv** – Research papers and preprints
* **Crossref** – Scholarly metadata and publications

### Database

* **MySQL / chromdb** – Users, research history, reports, and application data

### Development & Deployment

* **Git & GitHub** – Version control and collaboration
* **Vercel** – Frontend deployment
* **Railway** – Backend deployment

## Setup and Installation

This is a two-service repo: `backend/` (FastAPI) and `frontend/` (React + Vite), run independently.

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env      # fill in real values; never commit .env
uvicorn src.api.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

See [`backend/README.md`](backend/README.md) for the full environment variable reference, database setup, and API documentation.

## Deployment (Vercel + Railway)

### Backend → Railway

1. Create a new Railway project, deploy from this GitHub repo, and set the **Root Directory** to `backend`.
2. Railway detects `requirements.txt` and the `Procfile` (`web: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`) automatically — no extra build config needed.
3. Add a MySQL plugin (optional — the app falls back to in-memory storage if MySQL isn't configured) and set these variables, referencing the plugin's own vars:
   ```
   MYSQL_HOST=${{MySQL.MYSQLHOST}}
   MYSQL_PORT=${{MySQL.MYSQLPORT}}
   MYSQL_USER=${{MySQL.MYSQLUSER}}
   MYSQL_PASSWORD=${{MySQL.MYSQLPASSWORD}}
   MYSQL_DATABASE=${{MySQL.MYSQLDATABASE}}
   ```
4. Set the real provider + secret variables (`LLM_PROVIDER=nvidia` or `openai`, `NVIDIA_API_KEY`/`OPENAI_API_KEY`, `SEARCH_PROVIDER=tavily`, `TAVILY_API_KEY`) and `CORS_ORIGINS=https://<your-vercel-domain>`.
5. Leave `SANDBOX_PROVIDER=mock` — Railway's containers don't provide Docker-in-Docker, so the real Docker sandbox provider won't work there.
6. Leave `CHROMA_PERSIST_DIR` empty unless you attach a persistent volume — otherwise Chroma runs in-memory and resets on redeploy (research history in MySQL is unaffected).
7. Note the generated `*.up.railway.app` URL — you'll need it for the frontend.

### Frontend → Vercel

1. Import this repo into Vercel and set the **Root Directory** to `frontend`. Vercel auto-detects the Vite framework preset (build command `npm run build`, output `dist`).
2. Add an environment variable: `VITE_API_BASE_URL=https://<your-railway-domain>/api`.
3. `vercel.json` (already in `frontend/`) rewrites all routes to `index.html` so client-side routes (e.g. `/command-center`) work on direct load/refresh.
4. Deploy, then go back to Railway and set `CORS_ORIGINS` to the resulting `https://<your-vercel-domain>` (no trailing slash).

### Verifying the deployment

- `GET https://<railway-domain>/api/health` should return `{"status":"ok",...}`.
- Open the Vercel URL, submit a research question from the Command Center, and confirm it reaches the backend (network tab / no CORS errors).
- Voice input requires a Chromium-based browser and HTTPS (Vercel serves HTTPS by default, so this works out of the box).
