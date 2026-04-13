# gov-intelligence-nlp

Political intelligence platform for analyzing Spanish political discourse via NLP and LLM-powered Q&A.

## Quick Start

### Prerequisites
- Node.js 20+
- Python 3.11+
- PostgreSQL 15+ with pgvector extension

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at http://localhost:3000

### Backend Setup
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```
Backend API at http://localhost:8000
API docs at http://localhost:8000/docs

> `alembic upgrade head` is required before running connector and jobs endpoints.

### Environment Variables
Copy `.env.example` to `.env` and configure your database URL and API keys.

## Production (Railway)

The live app is deployed on [Railway](https://railway.app/) with separate services for the backend and frontend.

- **Backend**: Nixpacks build; start command runs `uvicorn` on `0.0.0.0` with Railway’s `PORT`. Health checks use `GET /health` (see `railway.toml` / `railway.json`).
- **Frontend**: Next.js app with `NEXT_PUBLIC_API_BASE_URL` set to the public backend URL so the browser can call the API.
- **Database**: Managed PostgreSQL with the pgvector extension enabled (same schema as local; run Alembic migrations against the production URL when deploying schema changes).
- **Deploy pipeline**: Pushing to the `production` branch triggers `.github/workflows/deploy.yml`, which runs a backend import check and then `railway up` for the `backend` and `frontend` services (requires `RAILWAY_TOKEN` in GitHub Actions secrets).

For a new Railway setup, create two services from this repo, attach Postgres to the backend, set env vars to match `.env.example` (including `DATABASE_URL` / `DATABASE_SYNC_URL`, `OPENAI_API_KEY`, and CORS origins for your frontend URL), and configure the frontend service with the backend’s public origin in `NEXT_PUBLIC_API_BASE_URL`.

## Data Ingestion Workflow (Epic 5)

This repo includes an offline-first connector that reads a local Twitter/X JSONL file and ingests it into `raw_posts`.

### 1) Prepare Connector Input File

- Default path: `backend/data/twitter_posts.jsonl`
- Configure via `CONNECTOR_TWITTER_FILE_PATH` in `backend/.env`
- Optional cap per run: `CONNECTOR_TWITTER_MAX_RECORDS`

Each line in the JSONL file must be a JSON object, for example:

```json
{"id":"123","id_str":"123","full_text":"[PSOE] ... [ECONOMIA] ...","text":"[PSOE] ... [ECONOMIA] ...","user":{"screen_name":"demo_user"},"author":"demo_user","created_at":"Thu Apr 01 12:00:00 +0000 2021","lang":"es"}
```

### 2) Run Connector Ingestion

Start backend first, then trigger:

```bash
curl -X POST "http://127.0.0.1:8000/connectors/twitter-file/run" \
  -H "Content-Type: application/json" \
  -d '{"mode":"live"}'
```

PowerShell equivalent:

```powershell
Invoke-RestMethod -Method POST `
  -Uri "http://127.0.0.1:8000/connectors/twitter-file/run" `
  -ContentType "application/json" `
  -Body '{"mode":"live"}'
```

### 3) Run NLP Processing

Connector ingestion populates `raw_posts`. To populate `processed_posts` (used by analytics and Q&A), trigger processing:

```bash
curl -X POST "http://127.0.0.1:8000/process?batch_size=50"
```

PowerShell equivalent:

```powershell
Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8000/process?batch_size=50"
```

### 4) Verify Runs

- API: `GET /jobs?job_type=connector&limit=5`
- API: `GET /jobs?job_type=process&limit=5`
- DB checks:
  - `SELECT COUNT(*) FROM raw_posts;`
  - `SELECT COUNT(*) FROM processed_posts;`

## Security note

The app is built for direct access to the dashboard and admin routes in trusted environments. For any deployment that is exposed on the public internet, add authentication, tighten CORS, and review API exposure before going live.
