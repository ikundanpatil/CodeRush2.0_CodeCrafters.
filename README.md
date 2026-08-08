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

om the Command Center, and confirm it reaches the backend (network tab / no CORS errors).
- Voice input requires a Chromium-based browser and HTTPS (Vercel serves HTTPS by default, so this works out of the box).
