---
stepsCompleted:
  - step-01-init
  - step-02-context
  - step-03-starter
  - step-04-decisions
inputDocuments:
  - path: _bmad-output/planning-artifacts/product-brief-gov-intelligence-nlp-2026-03-18.md
    type: product_brief
  - path: _bmad-output/planning-artifacts/prd.md
    type: prd
  - path: _bmad-output/planning-artifacts/ux-design-specification.md
    type: ux_spec
workflowType: 'architecture'
project_name: 'gov-intelligence-nlp'
user_name: 'Phillip'
date: '2026-03-19'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

The PRD defines around 34 functional requirements grouped into several areas:

- **Ingestion & Processing:**  
  The system must ingest a realistic dataset of Spanish political posts (initially CSV or pre-scraped dumps), store raw data as a source of truth, and run an NLP pipeline that classifies posts by topic, subtopic, sentiment, target, and intensity, and generates embeddings. Ingestion and processing runs must be triggerable, observable, and re-runnable from an admin/ops surface.

- **Analytics & Dashboards:**  
  The backend must expose APIs that power a dashboard showing volume and sentiment over time, topic and subtopic distributions, cross-party comparisons, and representative posts. Users need filters for topics, parties/targets, time windows, and platforms, plus the ability to see “most discussed” and “most negative” topics and drill into example posts.

- **Question-Answering Interface (Q&A):**  
  The platform must provide a question-first interface where campaign, comms, and analyst users submit natural-language questions, optionally with filters, and receive concise, grounded answers. Responses must include narrative summaries, basic numerical context (counts, sentiment breakdowns), and traceable evidence (links/previews of underlying posts).

- **User Journeys & Workflows:**  
  The architecture must support key flows:  
  - Campaign manager checking issue performance vs a competitor.  
  - Rapid-response user investigating short-term narrative spikes and recovering from transient failures.  
  - Analyst conducting a month-long deep dive and exporting insights.  
  - Admin/technical owner monitoring ingestion health and restoring data flow after failures.

- **Admin & Operations:**  
  There must be an ops view or equivalent APIs for ingestion job status, last run times, error summaries, health checks, and approximate data volume per source. Operators must be able to re-run failed jobs and validate pipeline health without low-level server access.

- **Data Access & Exports:**  
  Analysts must be able to export or capture structured snapshots (aggregated metrics + example posts) and copy key charts or narrative summaries for memos, briefings, and presentations.

- **Configuration & Taxonomy:**  
  The political taxonomy (topics, subtopics, targets) and pipeline settings must be configurable without code changes and applied consistently across runs so that analytics and Q&A operate on a stable domain model.

- **Demo & Classroom Usage:**  
  The system must be easy to reset and reinitialize for demos, support unauthenticated access in a controlled environment, and handle ad-hoc natural-language questions from instructors and peers.

**Non-Functional Requirements:**

NFRs drive several important architectural constraints:

- **Performance:**  
  - Q&A flows should complete in ≲5 seconds end-to-end for a 5–10k post dataset.  
  - Dashboard interactions (filters, time changes) should update within ≲2 seconds.  
  - The system should support a small group of concurrent classroom users without breaking, even if latency grows toward the upper bounds.

- **Reliability & Operations:**  
  - Ingestion and processing failures must be clearly exposed with timestamps and error summaries, allowing a student operator to diagnose and retry quickly.  
  - The full pipeline should be runnable from scratch in a reasonable preparation window on a student machine.  
  - During a 30–45 minute demo session, core flows (dashboards and Q&A) should remain stable.

- **Security & Privacy (MVP):**  
  - Only public or synthetic political content is processed; no new sensitive personal data is collected.  
  - API keys and credentials live in environment variables or non-checked-in config files.  
  - Access to the running environment is limited to the project team and classroom context; no internet-scale exposure or production-grade hardening.

These NFRs suggest an architecture that prioritizes simplicity, debuggability, and observability over distributed complexity, while still being structured enough to evolve toward a more serious product later.

**Scale & Complexity:**

Overall, the project sits in the **data-driven web app / SaaS dashboard** domain with integrated **ML/NLP and LLM/RAG** capabilities.

- **Primary domain:**  
  Backend APIs with an ingestion + processing pipeline, analytics endpoints, and a web frontend (React) providing dashboards and a Q&A interface.

- **Complexity level:**  
  **Medium–high** for a student MVP:
  - Multiple subsystems (ingestion, NLP pipeline, structured store, vector index, analytics APIs, Q&A layer, frontend, admin/ops).  
  - Strong coupling between data model, analytics views, and Q&A semantics.  
  - Need for reliability and observability despite limited infra and team size.  
  Complexity is bounded by MVP constraints: small dataset (5–10k posts), single tenancy, no auth/RBAC, single deployment environment.

- **Estimated architectural components (logical):**  
  - Data ingestion and raw storage component.  
  - NLP processing pipeline (classification + embeddings).  
  - Structured data store / vector index.  
  - Analytics/query API layer.  
  - Q&A / RAG service layer.  
  - Web frontend (dashboard + Q&A UI).  
  - Admin/ops and monitoring surface.  

These components can be implemented within a small number of physical services (for example, one backend service + one database) but should be kept modular in code.

### Technical Constraints & Dependencies

- **Tech stack constraints (from docs):**  
  - Backend: FastAPI.  
  - ML/NLP: HuggingFace / OpenAI.  
  - Database: PostgreSQL with a vector extension (e.g. pgvector).  
  - Frontend: React with a Tailwind-based design system.  

The architecture must respect this stack, leaning on Postgres for both relational and vector workloads to keep infra simple.

- **Operational constraints:**  
  - Single-tenant, classroom/demo deployment (likely on a single machine or simple Docker setup).  
  - Limited operator expertise and no dedicated DevOps, so deployment, configuration, and recovery flows must be straightforward and well-encapsulated.

- **Domain constraints:**  
  - Focus on Spanish political discourse with a fixed taxonomy and limited set of topics/targets in the MVP.  
  - Need for traceability: each answer or chart must be easily traceable back to underlying posts and filters.

### Cross-Cutting Concerns Identified

Several concerns will span multiple architectural components:

- **Observability & Health:**  
  Logging, metrics, and simple status endpoints for ingestion, processing, and Q&A must be available to drive the admin/ops views and enable fast debugging.

- **Configuration Management:**  
  Taxonomy definitions, model choices, thresholds, and data source configs should be externalized and versionable, with clear impact on both analytics and Q&A behavior.

- **Error Handling & Degradation:**  
  The system must handle ingestion failures, partial data, or LLM issues gracefully, surfacing clear messages in the UI and offering useful next steps (retry, adjust filters) rather than silent or opaque failures.

- **Data Modeling & Provenance:**  
  The schema must keep enough structure (topics, sentiment, targets, timestamps, platforms, embeddings) and provenance (source URLs, time windows) to power dashboards, RAG retrieval, and evidence-backed Q&A consistently.

- **Performance & Cost Control:**  
  Efficient queries over the structured store and careful scoping of LLM calls are necessary to meet latency goals and keep resource usage reasonable on student hardware.

These cross-cutting concerns will strongly influence later decisions about service boundaries, database schema design, caching, and how we structure the API surface.

## Starter Template Evaluation

### Primary Technology Domain

Full-stack **web application** with:

- **Frontend:** Next.js (App Router) + React + TypeScript + Tailwind CSS  
- **Backend:** FastAPI + PostgreSQL (with pgvector)  

This matches the PRD and project info document: a data-driven web app / SaaS dashboard with an LLM-powered Q&A interface.

### Starter Options Considered

For the **frontend**, we considered:

- The **official Next.js App Router starter** created via `create-next-app`, with TypeScript and Tailwind enabled. This is maintained by the Next.js team, stays up to date with framework changes, and provides a clean, minimal structure without heavy additional opinions.
- Community “production-ready” Next.js 15+ starters that bundle extra tooling (auth, complex state management, PWA, etc.). These offer more batteries included but add complexity and opinions that are not required for this MVP and could distract from the core political-intelligence functionality.

For the **backend**, instead of a heavy cookiecutter template (with many batteries included), we evaluated current FastAPI cookiecutter options and decided they would introduce more structure (auth systems, multiple ORMs, advanced CI/CD) than needed for a focused student MVP.

Given the scope and classroom context, the chosen approach is:

- Use the **official Next.js starter** for the frontend.
- Use a **minimal, hand-structured FastAPI backend** in a `backend/` folder, organized into clear modules (ingestion, processing, APIs) that we define explicitly rather than generated by a complex template.

### Selected Starter: Official Next.js App Router Starter + Custom FastAPI Skeleton

**Rationale for Selection:**

- Aligns with the documented stack (React, Tailwind, FastAPI, PostgreSQL/pgvector).
- Keeps frontend scaffolding **simple, modern, and well-documented**, with App Router, TypeScript, Tailwind, ESLint, and basic best practices handled by Next.js itself.
- Avoids over-opinionated backend templates so that the **architecture of the ingestion pipeline, analytics APIs, and Q&A layer is explicit** in this project, which is valuable for learning and for alignment with the PRD.
- Minimizes hidden complexity and makes it straightforward to explain each layer and file during a classroom demo or review.

### Initialization Commands

**Frontend (Next.js, in a `frontend` folder):**

```bash
npx create-next-app frontend --ts --tailwind --app
```

This initializes:
- Next.js (App Router) with React and TypeScript
- Tailwind CSS
- ESLint and basic project structure suitable for the dashboard + Q&A UI

**Backend (FastAPI, in a `backend` folder):**

Create a new backend directory and set up a virtual environment and minimal FastAPI app:

```bash
mkdir backend
cd backend
python -m venv .venv
.\.venv\Scripts\activate  # on Windows PowerShell
pip install fastapi uvicorn[standard]
```

From there, we will add:
- A `main.py` FastAPI entrypoint
- Modules for ingestion, processing, analytics APIs, and Q&A endpoints
- Database integration with PostgreSQL and pgvector

### Architectural Decisions Provided by the Starters

**Language & Runtime:**

- **Frontend:** TypeScript with Next.js, running on Node.js in development and production.
- **Backend:** Python 3 + FastAPI, running under Uvicorn (ASGI server).

**Styling Solution:**

- Tailwind CSS configured out of the box by `create-next-app`, used to implement the command-center dashboard, Q&A view, and evidence cards described in the UX specification.

**Build Tooling:**

- Frontend build and optimization handled by Next.js (bundling, routing, code-splitting, image optimization where used).
- Backend built and run via standard Python tooling; Dockerization can be added later following simple patterns.

**Code Organization:**

- Frontend: App Router structure with React server and client components, pages/layouts for the dashboard and Q&A, and co-located components for charts, filters, and evidence cards.
- Backend: Explicitly organized Python packages for data ingestion, NLP processing, analytics/read APIs, and Q&A endpoints, rather than hidden inside a template.

**Development Experience:**

- Hot reload and fast dev server for both frontend (`next dev`) and backend (`uvicorn main:app --reload`).
- TypeScript and ESLint on the frontend for safer iteration.
- Simple, readable backend code structure that can be extended as the data pipeline and Q&A logic evolve.

**Note:** Initializing these two projects using the commands above should be among the first implementation stories once we move from architecture to coding.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Use **PostgreSQL + pgvector** as the single source of truth for both structured data and embeddings.
- Use **async SQLAlchemy 2.x + Alembic** as the data access and migration layer.
- Implement a **REST-only** FastAPI backend with non-streaming Q&A responses.
- Expose a **Next.js (App Router) frontend** that talks to the backend via HTTP using `NEXT_PUBLIC_API_BASE_URL`.
- Run the MVP as a **single-tenant, unauthenticated classroom demo** with secrets in environment variables only.

**Important Decisions (Shape Architecture):**
- Use **Pydantic models** at API boundaries and for pipeline configuration/validation.
+- Skip distributed caching (e.g. Redis) for MVP and rely on Postgres (plus optional in-process caching if needed).
- Model data explicitly for political discourse (topics, sentiment, targets, intensity, embeddings) in separate tables for raw vs processed posts.
- Provide **manual refresh** on the frontend for analytics data, with room to add light polling later.
- Keep backend and frontend as **separate projects** (`backend/` and `frontend/`) in the same repo for clarity.

**Deferred Decisions (Post-MVP):**
- Introducing **Redis or other caching layers** for hot queries.
- Adding **authentication and role-based access control**.
- Moving to more complex deployment (multi-service, managed DB, cloud CI/CD).
- Adding **WebSockets/real-time updates** or streaming responses for Q&A.

### Data Architecture

- **Database:** PostgreSQL with pgvector extension, used for:
  - Raw posts table (original content and metadata).
  - Processed posts table (topic, subtopic, sentiment, target, intensity, embeddings).
  - Supporting tables for taxonomy configuration and analytics aggregates if needed.
- **ORM / Access Layer:** Async SQLAlchemy 2.x for all DB interactions in the backend.
- **Migrations:** Alembic to manage schema evolution over the course of the project.
- **Validation:** Pydantic models for request/response schemas and key internal structures.
- **Caching:** No external cache in MVP; rely on optimized SQL queries and, if needed, small in-memory caches inside API handlers or services.

### Authentication & Security

- **Authentication:** None in MVP; the UI is a shared classroom instance.
- **Authorization:** None; all users share the same capabilities.
- **API Exposure:** Backend is intended for local or controlled-network use; no public internet hardening assumed.
- **Secrets Management:** All sensitive values (DB URL, OpenAI API key, etc.) are stored in environment variables, with `.env` used locally and `.env.example` documenting required keys.
- **Transport Security:** HTTP for local development; HTTPS is deferred to any future deployment infrastructure.

### API & Communication Patterns

- **Style:** RESTful HTTP APIs via FastAPI.
- **Key endpoints:**
  - Health/status endpoints for basic monitoring.
  - Ingestion and processing triggers (admin-oriented).
  - Analytics endpoints (time series, distributions, representative posts).
  - `POST /qa` endpoint for question-answering over the processed data store.
- **Q&A Behavior:** Non-streaming HTTP responses: the backend performs retrieval, aggregation, and LLM call, then returns a single JSON payload. The frontend is responsible for presenting this response in a user-friendly, staged way.
- **Real-Time / Streaming:** No WebSockets or streaming responses for MVP; any “live” behavior is simulated via manual refresh or optional later polling.
- **Docs:** OpenAPI schema and interactive docs provided automatically by FastAPI (`/docs` and `/openapi.json`).
- **Error Handling:** JSON error envelopes for non-validation errors, with clear messages suitable for a classroom/demo environment.

### Frontend Architecture

- **Framework:** Next.js (App Router) with React and TypeScript.
- **Styling:** Tailwind CSS as the core styling solution, implementing the command-center layout and evidence-centric cards described in the UX spec.
- **Structure:**
  - App Router layout with routes for:
    - Main dashboard (topics, sentiment, spikes).
    - Q&A-focused view (or panel embedded in the dashboard).
  - Shared components for charts, filters, narrative summary blocks, and evidence post cards.
- **State Management:** Rely primarily on React state and simple hooks for MVP; introduce heavier state tools only if needed.
- **Data Fetching:** Use Next.js data fetching (server components or client-side fetches where appropriate) to call the FastAPI backend via `NEXT_PUBLIC_API_BASE_URL`.
- **UX Behavior:** Manual refresh controls for analytics; Q&A responses are shown with clear loading states and structured sections (summary, metrics, posts).

### Infrastructure & Deployment

- **Process Model:** Two main processes for local dev:
  - FastAPI backend served with Uvicorn.
  - Next.js frontend dev server.
- **Environments:** Local development only for MVP; environment separation is done via env vars.
- **Configuration:** `.env` for local secrets, `.env.example` as documentation; no secrets in version control.
- **Deployment (future):** A simple Docker-based deployment or single VM is expected; more advanced CI/CD and cloud architectures are deferred.

### Decision Impact Analysis

**Implementation Sequence:**
1. Initialize `frontend/` and `backend/` projects using the chosen starters.
2. Set up PostgreSQL with pgvector and configure SQLAlchemy + Alembic in the backend.
3. Define core DB models and Pydantic schemas for raw and processed posts.
4. Implement basic health and analytics endpoints in FastAPI.
5. Implement a first version of the `POST /qa` endpoint with mocked data, then connect it to real retrieval and LLM logic.
6. Build the Next.js dashboard and Q&A views that call these endpoints and present results according to the UX spec.

**Cross-Component Dependencies:**
- The frontend depends on a stable API contract for analytics and Q&A endpoints.
- The Q&A behavior and UX depend on the schema and availability of processed posts and embeddings in Postgres.
- Observability and admin views depend on health and status endpoints in the backend.
- Future enhancements (auth, caching, real-time updates) can be layered on top of this foundation without rewriting the core data model or API surface.
