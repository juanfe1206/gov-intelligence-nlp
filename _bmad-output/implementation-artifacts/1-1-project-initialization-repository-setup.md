# Story 1.1: Project Initialization & Repository Setup

**Status:** ready-for-dev  
**Epic:** 1 (Data Ingestion & Processing Pipeline)  
**Story ID:** 1.1  
**Created:** 2026-04-06  

---

## Story Statement

As a developer,  
I want to initialize the frontend and backend projects from the chosen starter templates with all tooling configured,  
So that the team has a clean, runnable foundation to build all features on.

---

## Acceptance Criteria

**Given** a fresh repository with no existing frontend or backend code  
**When** the developer runs `npx create-next-app frontend --ts --tailwind --app` and creates the `backend/` folder with a Python venv and FastAPI installed  
**Then** `frontend/` starts with `npm run dev` and displays the Next.js default page at localhost:3000  
**And** `backend/` starts with `uvicorn main:app --reload` and serves `GET /health` returning `{"status": "ok"}`

**Given** the project needs secrets management  
**When** a developer sets up the repository  
**Then** a `.env.example` file documents all required environment variables (DB URL, OpenAI API key, etc.) and `.gitignore` excludes `.env` from version control  
**And** the app reads all sensitive config from environment variables only — no hardcoded credentials in source

---

## Developer Context Section

### What This Story Accomplishes

This is the **foundational story** for the entire gov-intelligence-nlp platform. You are setting up the two core projects that will host all future development:

1. **Frontend (`frontend/`)**: Next.js 15+ App Router application with TypeScript and Tailwind CSS
2. **Backend (`backend/`)**: FastAPI application with async SQLAlchemy and Alembic migrations

This story does NOT implement any business logic. It creates the scaffolding, tooling, and configuration that Stories 1.2+ will build upon.

### Critical Success Criteria

- Both projects must start cleanly with their respective dev servers
- `.env.example` must document ALL required variables (even if values are placeholders)
- `.gitignore` must exclude `.env` and all Python/Node build artifacts
- The backend must expose at least one working endpoint (`GET /health`)
- No hardcoded secrets anywhere in source control

---

## Technical Requirements

### Frontend Requirements

| Requirement | Details |
|-------------|---------|
| Framework | Next.js 15+ with App Router |
| Language | TypeScript (strict mode) |
| Styling | Tailwind CSS |
| Dev Server | `npm run dev` on port 3000 |
| Linting | ESLint configured |
| Package Manager | npm or pnpm (consistent across team) |

### Backend Requirements

| Requirement | Details |
|-------------|---------|
| Framework | FastAPI (latest stable) |
| Language | Python 3.11+ |
| Server | Uvicorn (ASGI) |
| Database ORM | Async SQLAlchemy 2.x |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Virtual Environment | Python venv in `backend/.venv` |

### Environment Variables Required

Document these in `.env.example`:

```
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/gov_intelligence_nlp

# OpenAI / LLM
OPENAI_API_KEY=sk-...

# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Optional: for future features
REDIS_URL=redis://localhost:6379
```

---

## Architecture Compliance

### Repository Structure (Post-Story 1.1)

After completion, the repository should have this structure:

```
gov-intelligence-nlp/
├── frontend/                 # Next.js App Router application
│   ├── app/                  # App Router pages and layouts
│   ├── components/           # Reusable React components
│   ├── public/               # Static assets
│   ├── .env.example          # Frontend env vars documentation
│   ├── .gitignore
│   ├── next.config.js
│   ├── package.json
│   ├── tailwind.config.js
│   └── tsconfig.json
│
├── backend/                  # FastAPI application
│   ├── .venv/                # Python virtual environment (gitignored)
│   ├── app/                  # Application package
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app entry point
│   │   └── api/              # API routes (start with /health)
│   ├── .env.example          # Backend env vars documentation
│   ├── .gitignore
│   ├── requirements.txt      # OR pyproject.toml with dependencies
│   └── alembic/              # Migration configs (created Story 1.2)
│
├── .env.example              # Root-level combined env documentation
├── .gitignore
├── README.md                 # Project overview and setup instructions
└── docs/                     # Project documentation
```

### Architectural Decisions Made

| Decision | Rationale |
|----------|-----------|
| **Separate `frontend/` and `backend/` folders** | Clear separation of concerns, independent deployment options, aligns with PRD and Architecture doc |
| **Next.js App Router (not Pages)** | Modern standard, better for future server components, recommended by Next.js team |
| **Tailwind CSS (not Material/Ant)** | Flexible theming without opinionated component styles, aligns with custom UX design requirements |
| **FastAPI (not Flask/Django)** | Async support, automatic OpenAPI docs, Pydantic integration, aligns with NFRs |
| **No Redis/caching in MVP** | Per Architecture doc: rely on optimized SQL queries; caching deferred to post-MVP |

---

## Library/Framework Requirements

### Frontend Dependencies (to install)

```json
{
  "dependencies": {
    "next": "^15.x",
    "react": "^19.x",
    "react-dom": "^19.x"
  },
  "devDependencies": {
    "@types/node": "^20.x",
    "@types/react": "^19.x",
    "@types/react-dom": "^19.x",
    "autoprefixer": "^10.x",
    "eslint": "^9.x",
    "postcss": "^8.x",
    "tailwindcss": "^4.x",
    "typescript": "^5.x"
  }
}
```

**Note:** These are installed automatically via `create-next-app`. Do not add additional UI libraries unless explicitly required by future stories.

### Backend Dependencies (to install)

Create `backend/requirements.txt`:

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.0.0
sqlalchemy[asyncio]>=2.0.0
alembic>=1.13.0
asyncpg>=0.29.0
psycopg2-binary>=2.9.0  # For development only
python-dotenv>=1.0.0
```

**Note:** 
- `pgvector` Python package is NOT needed yet (Story 1.2 will add it)
- Use `asyncpg` as the async PostgreSQL driver for SQLAlchemy
- `python-dotenv` for loading `.env` files in development

---

## File Structure Requirements

### Root-Level Files to Create

**`.gitignore`** (root):
```gitignore
# Environment
.env
.env.local
.env.*.local

# Node
node_modules/
.next/
out/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Testing
.coverage
htmlcov/
.pytest_cache/
```

**`.env.example`** (root - combined documentation):
```bash
# ===========================================
# GOV-INTELLIGENCE-NLP Environment Variables
# ===========================================
# Copy this file to .env and fill in actual values.
# NEVER commit .env to version control.

# -------------------------------------------
# Database Configuration
# -------------------------------------------
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/gov_intelligence_nlp

# -------------------------------------------
# LLM / AI Configuration
# -------------------------------------------
OPENAI_API_KEY=sk-your-key-here

# -------------------------------------------
# Frontend Configuration
# -------------------------------------------
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# -------------------------------------------
# Backend Configuration
# -------------------------------------------
# (Add any backend-only vars here)
```

**`README.md`** (root):
```markdown
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
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Backend API at http://localhost:8000
API docs at http://localhost:8000/docs

### Environment Variables
Copy `.env.example` to `.env` and configure your database URL and API keys.
```

### Frontend Files (via create-next-app)

The `create-next-app` command creates these automatically. Key files to know:

| File | Purpose |
|------|---------|
| `frontend/app/layout.tsx` | Root layout (add global fonts, metadata) |
| `frontend/app/page.tsx` | Home page (replace with dashboard in Story 2.1) |
| `frontend/tailwind.config.js` | Tailwind theme (extend for design system in Story 2.1) |
| `frontend/tsconfig.json` | TypeScript config (keep strict mode) |

### Backend Files (to create manually)

**`backend/app/__init__.py`**:
```python
# Backend application package
```

**`backend/app/main.py`**:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="gov-intelligence-nlp API",
    description="Political intelligence platform API",
    version="0.1.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "ok"}

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "gov-intelligence-nlp API",
        "version": "0.1.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**`backend/app/api/__init__.py`**:
```python
# API routes package
# Endpoints will be organized here in future stories
```

---

## Testing Requirements

### Frontend Testing Setup

No tests required for this story. Testing infrastructure (Jest, React Testing Library) will be added in a later story when there's actual functionality to test.

### Backend Testing Setup

No tests required for this story. Pytest configuration will be added when API endpoints have business logic to validate.

### Manual Testing Checklist

Before marking this story complete, verify:

- [ ] `cd frontend && npm run dev` starts without errors
- [ ] Visiting `http://localhost:3000` shows Next.js default page
- [ ] `cd backend && uvicorn app.main:app --reload` starts without errors
- [ ] Visiting `http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] Visiting `http://localhost:8000/docs` shows Swagger UI with `/health` endpoint
- [ ] `.env` is in `.gitignore` at root and in both `frontend/` and `backend/`
- [ ] `.env.example` exists and documents all required variables
- [ ] No secrets or API keys are committed to the repository

---

## Previous Story Intelligence

_N/A - This is the first story in Epic 1._

---

## Git Intelligence

_No git analysis available - this is a new project initialization._

---

## Latest Technical Information

### Next.js 15+ Notes

- **App Router** is the current standard (not Pages Router)
- **Server Components** are default; use `"use client"` directive for client components
- **TypeScript 5.x** is the current stable version
- **Tailwind CSS 4.x** uses new configuration patterns (check docs for latest)

### FastAPI Notes

- **Pydantic v2** has breaking changes from v1 (use `from pydantic import BaseModel`)
- **Async route handlers** are recommended for database operations
- **Automatic OpenAPI docs** at `/docs` endpoint (Swagger UI)
- **Dependency injection** system available for database sessions, auth, etc.

### PostgreSQL/pgvector Notes

- **PostgreSQL 15+** recommended for best pgvector performance
- **pgvector 0.5+** supports efficient vector indexing
- **Connection pooling** handled by SQLAlchemy; no separate pooler needed for MVP

---

## Project Context Reference

### Relevant Project Documents

| Document | Location | Relevance |
|----------|----------|-----------|
| Product Brief | `_bmad-output/planning-artifacts/product-brief-*.md` | Overall product vision |
| PRD | `_bmad-output/planning-artifacts/prd.md` | Functional requirements |
| Architecture | `_bmad-output/planning-artifacts/architecture.md` | Technical decisions, starter templates |
| UX Design Spec | `_bmad-output/planning-artifacts/ux-design-specification.md` | UI/UX requirements |
| Epics | `_bmad-output/planning-artifacts/epics.md` | This story's definition |

### Key Architecture References

From `architecture.md`:

**Starter Template Commands:**
```bash
# Frontend
npx create-next-app frontend --ts --tailwind --app

# Backend
mkdir backend
cd backend
python -m venv .venv
pip install fastapi uvicorn[standard]
```

**Implementation Sequence (from Architecture doc):**
1. ✅ Initialize `frontend/` and `backend/` projects (THIS STORY)
2. ⏭️ Set up PostgreSQL with pgvector + SQLAlchemy/Alembic (Story 1.2)
3. ⏭️ Define DB models and Pydantic schemas (Story 1.2)
4. ⏭️ Implement health and analytics endpoints (Story 1.6, 2.x)
5. ⏭️ Implement `POST /qa` endpoint (Story 3.x)
6. ⏭️ Build Next.js dashboard and Q&A views (Story 2.x, 3.x)

### UX Design System Notes (for future stories)

From `ux-design-specification.md`:

- **Color System**: Neutral/blue-gray base, deep blue accent, semantic colors (green/amber/red)
- **Typography**: Clean sans-serif (Inter/Roboto), clear hierarchy
- **Layout**: Desktop command-center with left nav, top header, main content area
- **Components to build later**: Narrative Cluster Card, Evidence Post Card, Insight Summary Panel, Spike Alert Banner

---

## Story Completion Status

**Status:** review
**Last Updated:** 2026-04-06  

### Definition of Done

- [x] Story file created with comprehensive developer context
- [x] Frontend project initialized and runs
- [x] Backend project initialized and runs
- [x] Health endpoint returns `{"status": "ok"}`
- [x] `.env.example` created with all required variables
- [x] `.gitignore` properly configured
- [x] README.md documents setup process
- [x] Manual testing checklist completed

### Dev Agent Record

**Implementation Summary:**
- Created Next.js 15 frontend with TypeScript and Tailwind CSS using `npx create-next-app@latest frontend --typescript --tailwind --app`
- Created FastAPI backend with Python 3.13 venv, installed all dependencies
- Backend health endpoint verified: `GET /health` returns `{"status": "ok"}`
- Frontend verified running at http://localhost:3000 showing Next.js default page
- Root `.gitignore` updated to exclude both frontend and backend artifacts
- Root `.env.example` updated with all required environment variables
- README.md created with quick start instructions

**Files Modified/Created:**
- `frontend/` - Next.js application (generated)
- `backend/app/__init__.py` - Backend package init
- `backend/app/api/__init__.py` - API routes package init
- `backend/app/main.py` - FastAPI application with health endpoint
- `backend/requirements.txt` - Python dependencies
- `.gitignore` - Updated for monorepo structure
- `.env.example` - Updated with all environment variables
- `README.md` - Project overview and setup instructions

**Completion Notes:**
Story 1.1 completed successfully. Both dev servers verified running:
- Frontend: http://localhost:3000 (Next.js default page)
- Backend: http://localhost:8000 (FastAPI with /health endpoint returning {"status": "ok"})
- API docs available at http://localhost:8000/docs

Ready to proceed to Story 1.2: Database Schema & Migration Setup.

### Next Story

After completing this story, proceed to **Story 1.2: Database Schema & Migration Setup** which will:
- Configure PostgreSQL with pgvector extension
- Set up async SQLAlchemy connection
- Initialize Alembic migrations
- Create initial migration for `raw_posts` and `processed_posts` tables

---

## References

- [Architecture Decision Document](_bmad-output/planning-artifacts/architecture.md#Starter%20Template%20Evaluation)
- [UX Design Specification](_bmad-output/planning-artifacts/ux-design-specification.md#Design%20System%20Foundation)
- [PRD](_bmad-output/planning-artifacts/prd.md#Additional%20Requirements)
- [Epics](_bmad-output/planning-artifacts/epics.md#Story%201.1)
