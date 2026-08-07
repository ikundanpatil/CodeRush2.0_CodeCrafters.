# CodeRush 2.0 | Team Project Repository

---

Project Information

- Team Name : CodeCrafters
- Project Title : EvoResearch — Self-Evolving Autonomous Research Agent
- Track/Theme : Agentic AI

---

## Project Description

EvoResearch is an autonomous AI research agent that can understand a research question, create a research plan, search for relevant information, collect evidence, detect potentially malicious instructions in retrieved content, and generate a source-backed research report.

The main idea behind EvoResearch is **controlled self-improvement**.

Instead of only answering questions, the agent evaluates how well its research strategy performed, identifies weaknesses, proposes an improved strategy, tests that strategy, and only accepts the improvement when it performs better and passes safety checks.

### Core Workflow

```text
User Question
      ↓
Research Planner
      ↓
Web Search
      ↓
Safe Content Processing
      ↓
Prompt Injection Defense
      ↓
Evidence Collection
      ↓
Research Report
      ↓
Strategy Evaluation
      ↓
Improved Strategy
      ↓
Safety Check
      ↓
Approve / Reject
```

---

## Technical Stack

List the technologies used in this project:

* **Frontend:** [Enter Frontend e.g., React, Next.js, Tailwind]
* **Backend:** [Enter Backend e.g., Node.js, Python, FastAPI]
* **Database:** [Enter Database e.g., PostgreSQL, MongoDB, Supabase]
* **Tools/APIs:** [Enter Tools/APIs e.g., OpenAI API, LangChain, Tavily Search]

---

## Setup and Installation

Provide instructions on how to run your project locally:

1. Clone the repository.
2. Install dependencies: `npm install` or `pip install -r requirements.txt`
3. Configure environment variables (provide a `.env.example` if necessary).
4. Start the development server: `npm run dev` or `python main.py`
