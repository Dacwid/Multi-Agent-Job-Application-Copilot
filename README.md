# ApplyPilot

A multi-agent job-application copilot: paste a job posting and upload a
resume, and five cooperating agents produce a job analysis, a match
report, a tailored cover letter, and interview prep — with a human
approval gate before anything is finalized.

Built as a portfolio project to demonstrate agentic AI patterns:
orchestration graphs, parallel fan-out, reflection/critique loops,
structured outputs, human-in-the-loop via graph interrupts, and streaming
progress to a live timeline UI.

See [docs/architecture.md](docs/architecture.md) for the full graph design
and the reasoning behind it.

<!-- TODO: add a screenshot or GIF of the live agent timeline here — it's
     the most visually compelling part of the demo. -->

## Agentic patterns demonstrated

- **State graph orchestration** (LangGraph) instead of a linear prompt
  chain — conditional routing, cycles, and parallelism as explicit graph
  structure rather than ad hoc control flow.
- **Parallel fan-out / fan-in** — Cover Letter and Interview Prep run
  concurrently off the same Resume Matcher output; the Critic is a fan-in
  point that waits for both.
- **Reflection / critic loop** — a second model call scores the first
  model's output against a rubric and triggers targeted regeneration,
  bounded by a revision cap so it can't run away.
- **Structured outputs as the agent-to-agent contract** — every agent
  returns a Pydantic-validated schema; downstream agents consume the
  validated model, not raw text.
- **Human-in-the-loop via graph interrupts** — `interrupt()` +
  `Command(resume=...)` backed by a Postgres checkpointer, so a pipeline
  run can pause indefinitely and resume later from a completely separate
  HTTP request.
- **Streaming observability** — every node emits start/finish events over
  SSE, and a full audit trail (every attempt, every agent, every revision)
  is persisted to `agent_runs` independent of the final result.

## Stack

| Layer | Choice |
|---|---|
| Frontend | React + Vite + TypeScript + Tailwind CSS |
| Backend | Python + FastAPI |
| Agent framework | LangGraph |
| LLM | Gemini (`google-genai`) |
| Database / Auth / Storage | Supabase (Postgres, RLS, Storage) |
| Checkpointer | `langgraph-checkpoint-postgres` over Supabase Postgres |
| Streaming | Server-Sent Events |

## Setup

### Prerequisites

- Node.js 20+ and Python 3.11+
- A Supabase project (free tier is fine)
- A Gemini API key ([ai.google.dev](https://ai.google.dev))

### 1. Supabase

1. Create a project at [supabase.com](https://supabase.com).
2. Run [`db/schema.sql`](db/schema.sql) in the SQL editor — this creates
   all tables, RLS policies, and the private `resumes` storage bucket.
3. Collect four values from **Project Settings → API**: the project URL,
   the `anon` key, and the `service_role` key.
4. Collect a direct Postgres connection string from the **Connect** dialog
   → **Direct** tab → **Session pooler** — needed by the LangGraph
   checkpointer, separate from the API keys above.

### 2. Backend

```bash
cd backend
python -m venv venv
venv/Scripts/activate   # or `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env
```

Fill in `backend/.env`:

```
GEMINI_API_KEY=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
DATABASE_URL=          # Session pooler connection string, password URL-encoded
CORS_ORIGINS=["http://localhost:5173"]
```

Run it:

```bash
uvicorn app.main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

Fill in `frontend/.env`:

```
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

Run it:

```bash
npm run dev
```

Open the printed local URL, sign up, upload a resume, paste a job posting,
and watch the agent timeline run.

### 4. Tests

```bash
cd backend
pytest
```

## Deployment (optional)

Frontend on Vercel, backend on Render's free tier — both free, and Render's
usual free-tier downsides (databases deleted after 90 days, no persistent
disk) don't matter here since all data lives in Supabase, not on Render.

### Backend → Render

1. Push this repo to GitHub (if not already).
2. In Render: **New → Blueprint**, connect the repo. Render reads
   [`render.yaml`](render.yaml) at the repo root and provisions a free web
   service rooted at `backend/`.
3. Fill in the env vars it prompts for — same values as `backend/.env`
   (`GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
   `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`), plus `CORS_ORIGINS` — leave
   this as `["http://localhost:5173"]` for now, you'll add the Vercel URL
   once you have it.
4. Deploy. Note the resulting URL (`https://applypilot-backend-xxxx.onrender.com`).
   Free tier sleeps after 15 minutes of inactivity — the first request after
   that takes 30–60s to wake up, which is fine for a portfolio demo.

### Frontend → Vercel

1. In Vercel: **New Project**, import the repo.
2. Set **Root Directory** to `frontend` (Vercel auto-detects the Vite
   framework preset from there — no config file needed).
3. Add env vars: `VITE_API_URL` (the Render URL from above),
   `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
4. Deploy. Note the resulting URL (`https://your-project.vercel.app`).

### Wire them together

1. Back in Render, update `CORS_ORIGINS` to
   `["https://your-project.vercel.app"]` (add `http://localhost:5173` too
   if you still want local dev to work against the deployed backend) and
   redeploy.
2. In Supabase → **Authentication → URL Configuration**, add the Vercel
   URL to **Site URL** / **Redirect URLs** — otherwise auth email links
   (signup confirmation, password reset) redirect to `localhost`.

## Project structure

```
frontend/          React + Vite + TS + Tailwind
backend/
  app/
    agents/        LangGraph nodes, state, graph wiring, event streaming
    schemas/        Pydantic models — the contract between agents
    routes/         FastAPI endpoints
    services/       Supabase client, LLM client, Postgres checkpointer
  tests/
db/schema.sql        Full Postgres schema + RLS policies + storage bucket
docs/architecture.md  Graph design write-up
render.yaml           Render Blueprint for backend deployment
```
