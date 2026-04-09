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

---

## Demo Setup

For classroom demos, the platform is configured for **no authentication required** (demo/classroom use only — not intended for production). All users share direct access to the dashboard.

### Prerequisites
Same as Quick Start:
- Node.js 20+
- Python 3.11+
- PostgreSQL 15+ with pgvector extension (Supabase or local)

### Environment Configuration
```bash
cp .env.example .env
```

Edit `.env` and configure:
1. `DATABASE_URL` and `DATABASE_SYNC_URL` - Your Supabase or PostgreSQL connection string
2. `OPENAI_API_KEY` - Valid OpenAI API key (required for Q&A feature)
3. `APP_ENV=demo` - Sets demo mode (disables SQL query logging)
4. `BACKEND_HOST=0.0.0.0` - Allows the backend to accept connections from other devices

For **classroom access from other devices**, replace `localhost` with the demo machine's IP address:
```bash
# In .env (backend):
CORS_ALLOW_ORIGINS=http://192.168.1.42:3000,http://localhost:3000
BACKEND_HOST=0.0.0.0

# In frontend .env.local (or .env if using dev server):
NEXT_PUBLIC_API_BASE_URL=http://192.168.1.42:8000
```

> **Note:** `NEXT_PUBLIC_*` environment variables are read at build time. If you change them after running `npm run build`, you must rebuild. In development mode (`npm run dev`), changes take effect on restart.

### Starting Both Services

**Backend** (from project root, `backend/` directory):
```bash
cd backend
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Note: `--host 0.0.0.0` is required for network access from other devices. Omit `--reload` for stable demo runs — it adds overhead and can restart the server if files change mid-demo.

**Frontend** (from project root, `frontend/` directory):
```bash
cd frontend
npm run dev -- -H 0.0.0.0
```
Note: `-H 0.0.0.0` is required for network access from other devices. Without it, Next.js only listens on `localhost`.

### Concurrent Users
The default SQLAlchemy pool (`pool_size=5, max_overflow=10`) supports **5-10 simultaneous users** without additional configuration. Each Q&A request holds a connection for ~1-5 seconds.

### No Authentication
The platform requires **no login** for demo/classroom use. All users reach the dashboard directly at http://localhost:3000/dashboard or http://localhost:3000/admin. This is intentional for the shared classroom scenario — do not deploy this configuration to production without adding authentication.