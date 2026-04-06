---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - path: _bmad-output/planning-artifacts/prd.md
    type: prd
  - path: _bmad-output/planning-artifacts/architecture.md
    type: architecture
  - path: _bmad-output/planning-artifacts/ux-design-specification.md
    type: ux_spec
---

# gov-intelligence-nlp - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for gov-intelligence-nlp, decomposing the requirements from the PRD, UX Design, and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

**Ingestion & Processing**
FR1: An admin or technical owner can configure one or more data sources (CSV files or pre-scraped platform dumps) to be ingested into the system.
FR2: An admin or technical owner can trigger an ingestion run that reads raw posts from configured sources into the system's raw data store.
FR3: The system can automatically or manually start a processing run that applies the NLP pipeline (topic, subtopic, sentiment, target, intensity) to ingested posts.
FR4: The system can store processed posts, including structured fields and embeddings, in a queryable store for later analytics and Q&A.
FR5: An admin or technical owner can view the status of recent ingestion and processing runs, including whether they succeeded or failed and when they last ran.
FR6: An admin or technical owner can re-run a failed ingestion or processing job from the admin view or via an API.

**Analytics & Dashboards**
FR7: A campaign or communications user can view an overview dashboard showing the volume of political posts over time for a selected time range.
FR8: A campaign or communications user can view aggregated sentiment over time for a selected topic or issue.
FR9: A campaign or communications user can filter dashboard views by topic, subtopic, party or target, time range, and platform.
FR10: A user can see which topics and subtopics are most discussed and which are most negative or most positive within a given time window.
FR11: A user can view representative example posts that illustrate a chosen topic, subtopic, or sentiment segment.
FR12: An analyst can compare sentiment and volume across at least two parties or targets for a chosen topic and time range.

**Question-Answering Interface**
FR13: A campaign, communications, or analyst user can submit a natural-language question about political discourse through a Q&A interface.
FR14: A user can optionally specify filters (topic, time range, party or target, platform) together with a question.
FR15: The system can return a concise, grounded answer to a question that is clearly based on the underlying processed data.
FR16: The Q&A response includes links to or previews of underlying posts used as evidence.
FR17: The Q&A response includes basic numerical context (counts of posts and sentiment breakdowns) relevant to the question.
FR18: A user can submit multiple questions in a single session without reloading the application.

**User Journeys & Workflow Support**
FR19: A campaign manager can execute the "check housing issue performance" journey end-to-end using only dashboard and Q&A views.
FR20: A rapid response user can identify and investigate short-term narrative spikes about a leader, including seeing clusters of narratives and representative posts.
FR21: A rapid response user can recover from a transient system or data issue by retrying or adjusting filters and still obtain a usable picture of the situation.
FR22: An analyst can conduct a month-long deep dive on a specific topic by exploring trends, subtopics, and sentiment, and by exporting or copying data for a memo.
FR23: An admin or technical owner can monitor ingestion health and follow a simple documented sequence to restore data flow when a run fails.

**Admin & Operations**
FR24: An admin or technical owner can access an operations view summarizing ingestion jobs, their status, and key error messages.
FR25: An admin or technical owner can perform basic health checks on the service (API availability, DB connectivity) through an admin UI or endpoint.
FR26: An admin or technical owner can see approximate data volume per source to understand current dataset coverage.

**Data Access & Exports**
FR27: An analyst can export or download a structured snapshot of aggregated metrics and representative posts for a given topic, time window, and party comparison.
FR28: A user can copy or otherwise capture key charts and narrative summaries from the dashboard or Q&A view for inclusion in external documents or presentations.

**Configuration & Taxonomy**
FR29: An admin or technical user can configure the list of political topics, subtopics, and targets (parties, leaders) used by the classification pipeline.
FR30: The system can use the configured taxonomy to tag posts consistently across ingestion runs.
FR31: A technical user can adjust or update model and pipeline configuration (thresholds, model versions) without changing application code.

**Demo & Classroom Usage**
FR32: Any classroom participant can access the platform without individual authentication in the MVP environment.
FR33: Instructors or reviewers can ask their own natural-language questions during the demo and receive coherent, data-grounded answers.
FR34: A demo operator can reset or reinitialize the dataset and run a clean end-to-end pipeline in preparation for a new demonstration.

### NonFunctional Requirements

**Performance**
NFR1: For the target demo dataset (~5–10k posts), typical Q&A requests should complete in 5 seconds or less end-to-end, including retrieval, aggregation, and LLM response generation.
NFR2: For standard dashboard interactions (changing filters, time ranges, or topics), visible charts and key metrics should update within 2 seconds for the target dataset size.
NFR3: The system should support at least 5–10 concurrent classroom users without failing requests, even if performance degrades toward the upper bound of response times.

**Reliability & Operations**
NFR4: Ingestion and processing failures must be surfaced clearly in the admin/ops view, with enough information (timestamp, error summary) for a student operator to diagnose and retry without reading server logs.
NFR5: It should be possible to run the full ingestion and processing pipeline from a clean state within a reasonable preparation window before a demo (within a couple of hours on a typical student machine or lab server).
NFR6: During a live demo, the system should be stable enough that core flows (dashboards and Q&A) can be exercised for at least 30–45 minutes without needing to restart services.

**Security & Privacy (MVP Context)**
NFR7: The MVP will only process public or synthetic political content and will not store personal identifying information beyond what is present in source posts; no additional sensitive user data will be collected.
NFR8: Access to the running demo environment should be limited to the project team, instructors, and classmates; it is not intended for open internet exposure or production use.
NFR9: Any API keys or credentials used for data collection or LLM access must be stored in environment variables or configuration files that are not committed to source control.

### Additional Requirements

- **Starter Template (Architecture):** Use official Next.js App Router starter (`npx create-next-app frontend --ts --tailwind --app`) for the frontend and a minimal hand-structured FastAPI backend in a `backend/` folder. Initializing these is the first implementation story.
- **Database:** PostgreSQL with pgvector extension as the single data store for both relational structured data and vector embeddings.
- **ORM & Migrations:** Async SQLAlchemy 2.x for all DB interactions; Alembic for schema migrations.
- **Validation:** Pydantic models at all API boundaries and for pipeline configuration/validation.
- **No Caching Layer (MVP):** No Redis or distributed cache; rely on optimized SQL queries and optional small in-memory caches if needed.
- **Separate Raw and Processed Tables:** Data model must distinguish raw posts (original content/metadata) from processed posts (topic, subtopic, sentiment, target, intensity, embeddings).
- **REST-only API:** FastAPI backend with non-streaming JSON responses for Q&A; no WebSockets or streaming in MVP.
- **Frontend Data Fetching:** Next.js frontend calls backend via `NEXT_PUBLIC_API_BASE_URL`; manual refresh for analytics data.
- **Secrets Management:** `.env` for local secrets, `.env.example` as documentation; no secrets in version control.
- **Implementation Sequence:** (1) Init projects → (2) Set up PostgreSQL/pgvector + SQLAlchemy/Alembic → (3) Define DB models and Pydantic schemas → (4) Implement health and analytics endpoints → (5) Implement `POST /qa` endpoint → (6) Build Next.js dashboard and Q&A views.
- **OpenAPI Docs:** FastAPI automatically provides `/docs` and `/openapi.json` for the API.
- **Error Handling:** JSON error envelopes for non-validation errors with clear messages.

### UX Design Requirements

UX-DR1: Implement a desktop command-center layout with a slim left navigation, top header bar, and main content area divided into three vertical bands: KPI/alerts strip at top, primary analytics section (trend/comparison charts + topic/narrative tiles) in the middle, and evidence/Q&A panel at the bottom or as a right-side pane.
UX-DR2: Anchor a prominent question input near the top of the main content area, always visible while users scroll dashboard content, so asking or refining a question feels central rather than secondary.
UX-DR3: Implement a "Narrative Cluster Card" reusable component that groups related discourse narratives with sentiment label, volume count, and clickable link to pre-fill the question input.
UX-DR4: Implement an "Evidence Post Card" reusable component that displays a representative post with sentiment tag, basic metadata (source, date), and copyable text.
UX-DR5: Implement an "Insight Summary Panel" reusable component that shows a narrative summary, 2–3 key metrics/mini-charts, and a grid of Evidence Post Cards as a single structured Q&A answer block.
UX-DR6: Implement a "Spike Alert Banner" reusable component that surfaces sudden volume or sentiment spikes with topic label, urgency indicator, and a direct action link to investigate.
UX-DR7: Apply a color system with a neutral/blue-gray base for backgrounds and surfaces, a deep blue primary accent for actions and focus states, and semantic colors (green for positive, amber for warning, red for critical/negative sentiment). Color must not be the sole carrier of meaning.
UX-DR8: Apply a typography system using a clean sans-serif typeface (Inter or Roboto), a clear type scale (h1–h4, body, small), and generous line height, with hierarchy expressed through size, weight, and spacing rather than decorative fonts.
UX-DR9: Implement spacing using an 8px base unit and a 12-column desktop grid, with medium density—enough information on screen for analytical work without cramping, and clear visual gaps between major page sections.
UX-DR10: Ensure accessibility meets WCAG AA contrast ratios for all text and critical UI elements, provide visible keyboard focus states for all interactive elements, reinforce sentiment and status with icons or labels (not color alone), and maintain readable line lengths in narrative summaries and post cards.
UX-DR11: Provide a question-first interaction model with a natural-language input field and a small set of preset suggestions (e.g. "What's spiking?", "Compare us vs Party X on housing") to reduce blank-page anxiety for new queries.
UX-DR12: Implement progressive disclosure drill paths from overview KPIs → topic tiles → narrative clusters → individual posts, with clear breadcrumb or back-navigation so users stay oriented at each level.
UX-DR13: Show a reassuring loading state during Q&A processing (e.g. "Analyzing discourse…") that communicates the system is working without exposing raw technical details.
UX-DR14: Design error and empty states with plain-language explanations and concrete next steps (e.g. "Not enough data for this filter—try a wider time range" or "Retry ingestion from the admin panel"), rather than generic technical messages.
UX-DR15: Make narrative cluster tiles and topic tiles on the dashboard clickable so that selecting one pre-fills or shapes the question input, creating a smooth bridge between visual exploration and Q&A.
UX-DR16: Implement a reusable shell layout (left nav + top header + flexible main content grid) that hosts both the dashboard route and the Q&A/evidence panel route, sharing the same visual and interaction patterns (cards, chips, charts, evidence posts) across both views.

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 1 | Configure data sources for ingestion |
| FR2 | Epic 1 | Trigger ingestion run |
| FR3 | Epic 1 | Trigger NLP processing run |
| FR4 | Epic 1 | Store processed posts + embeddings |
| FR5 | Epic 1 | View ingestion/processing run status |
| FR6 | Epic 1 | Re-run failed jobs |
| FR7 | Epic 2 | Dashboard: volume over time |
| FR8 | Epic 2 | Dashboard: sentiment over time by topic |
| FR9 | Epic 2 | Dashboard filters (topic, party, time, platform) |
| FR10 | Epic 2 | Most discussed / most negative topics |
| FR11 | Epic 2 | Representative example posts |
| FR12 | Epic 2 | Cross-party sentiment/volume comparison |
| FR13 | Epic 3 | Submit natural-language Q&A question |
| FR14 | Epic 3 | Optional filters with Q&A question |
| FR15 | Epic 3 | Grounded answer based on processed data |
| FR16 | Epic 3 | Evidence posts in Q&A response |
| FR17 | Epic 3 | Numerical context in Q&A response |
| FR18 | Epic 3 | Multiple questions per session |
| FR19 | Epic 2 | Campaign manager end-to-end issue journey |
| FR20 | Epic 3 | Rapid response: spike investigation + narrative clusters |
| FR21 | Epic 3, Epic 4 | Recover from transient failure: Q&A retry/filter adjust (Story 3.6) + ingestion recovery (Story 4.1) |
| FR22 | Epic 2 | Analyst month-long deep dive + export |
| FR23 | Epic 4 | Admin monitors ingestion + restores data flow |
| FR24 | Epic 4 | Ops view: job status and error messages |
| FR25 | Epic 4 | Health checks (API availability, DB connectivity) |
| FR26 | Epic 4 | Data volume per source |
| FR27 | Epic 2 | Export structured snapshot (metrics + posts) |
| FR28 | Epic 2 | Copy/capture charts and summaries |
| FR29 | Epic 1 | Configure taxonomy (topics, subtopics, targets) |
| FR30 | Epic 1 | Consistent taxonomy tagging across runs |
| FR31 | Epic 1 | Update pipeline config without code changes |
| FR32 | Epic 4 | Unauthenticated classroom access |
| FR33 | Epic 3 | Ad-hoc Q&A from instructors during demo |
| FR34 | Epic 4 | Demo reset and clean pipeline reinitialization |

## Epic List

### Epic 1: Data Ingestion & Processing Pipeline
Admins and operators can configure data sources, trigger ingestion and NLP processing runs, and confirm that classified posts (topic, subtopic, sentiment, target, intensity, embeddings) are stored and queryable — establishing the data foundation that all other epics build on.
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR29, FR30, FR31
**Architecture note:** First story is project initialization (starter template), followed by DB schema + pipeline setup.

### Epic 2: Analytics Dashboard & Data Exploration
Campaign managers, comms teams, and analysts can explore political discourse through an interactive dashboard — filtering by topic, party, time range, and platform; viewing sentiment trends and topic distributions; comparing parties; drilling into representative posts; and exporting snapshots for memos.
**FRs covered:** FR7, FR8, FR9, FR10, FR11, FR12, FR19, FR22, FR27, FR28
**UX note:** Includes the command-center shell layout, KPI/spike strip, trend charts, Spike Alert Banner, Evidence Post Cards, design system tokens, and progressive drill-down paths.

### Epic 3: LLM-Powered Q&A Intelligence Interface
Campaign managers, comms, and analysts can type natural-language political questions (with optional filters), receive concise evidence-backed answers (narrative summary + metrics + representative posts), and iterate multiple questions in a session — fulfilling the core political intelligence loop.
**FRs covered:** FR13, FR14, FR15, FR16, FR17, FR18, FR20, FR21, FR33
**UX note:** Includes question input with presets, Insight Summary Panel, Narrative Cluster Cards, loading/error states, and clickable dashboard tiles pre-filling the question input.

### Epic 4: Admin, Operations & Demo Readiness
Admin and technical owners can monitor ingestion health, view job status and error summaries, run health checks, recover from failures, and reset the system for a clean demo run; all classroom participants can access the platform without individual authentication.
**FRs covered:** FR23, FR24, FR25, FR26, FR32, FR34

---

## Epic 1: Data Ingestion & Processing Pipeline

Admins and operators can configure data sources, trigger ingestion and NLP processing runs, and confirm that classified posts (topic, subtopic, sentiment, target, intensity, embeddings) are stored and queryable — establishing the data foundation that all other epics build on.

### Story 1.1: Project Initialization & Repository Setup

As a developer,
I want to initialize the frontend and backend projects from the chosen starter templates with all tooling configured,
So that the team has a clean, runnable foundation to build all features on.

**Acceptance Criteria:**

**Given** a fresh repository with no existing frontend or backend code
**When** the developer runs `npx create-next-app frontend --ts --tailwind --app` and creates the `backend/` folder with a Python venv and FastAPI installed
**Then** `frontend/` starts with `npm run dev` and displays the Next.js default page at localhost:3000
**And** `backend/` starts with `uvicorn main:app --reload` and serves `GET /health` returning `{"status": "ok"}`

**Given** the project needs secrets management
**When** a developer sets up the repository
**Then** a `.env.example` file documents all required environment variables (DB URL, OpenAI API key, etc.) and `.gitignore` excludes `.env` from version control
**And** the app reads all sensitive config from environment variables only — no hardcoded credentials in source

---

### Story 1.2: Database Schema & Migration Setup

As a developer,
I want PostgreSQL with pgvector configured and the core database tables created via Alembic migrations,
So that the system has a queryable store for raw and processed posts with vector support.

**Acceptance Criteria:**

**Given** a running PostgreSQL instance with the pgvector extension available
**When** the developer runs `alembic upgrade head`
**Then** the database contains a `raw_posts` table (id, source, platform, original_text, author, created_at, metadata jsonb) and a `processed_posts` table (id, raw_post_id FK, topic, subtopic, sentiment, target, intensity, embedding vector, processed_at)
**And** the pgvector extension is enabled and the `embedding` column accepts vector data

**Given** the schema needs to evolve over time
**When** a developer creates a new Alembic migration and runs `alembic upgrade head`
**Then** the migration applies cleanly on both a fresh database and an existing database with prior migrations

---

### Story 1.3: Political Taxonomy Configuration

As an admin or technical user,
I want to configure the list of political topics, subtopics, and targets from a config file,
So that the NLP pipeline tags posts consistently using a stable domain taxonomy without requiring code changes.

**Acceptance Criteria:**

**Given** a `taxonomy.yaml` file defining topics, subtopics, and targets (parties, leaders)
**When** the backend starts
**Then** the taxonomy is loaded into memory and `GET /taxonomy` returns the full taxonomy structure as JSON

**Given** an admin updates `taxonomy.yaml` to add or rename a topic
**When** the backend is restarted
**Then** subsequent processing runs use the updated taxonomy and new posts are tagged with the new labels
**And** already-processed posts retain their original labels (no retroactive re-tagging)

**Given** the taxonomy config is missing or malformed
**When** the backend starts
**Then** the app fails fast with a clear error identifying the config problem, rather than starting silently with broken data

---

### Story 1.4: CSV Data Ingestion

As an admin or technical owner,
I want to configure a CSV file as a data source and trigger an ingestion run,
So that raw Spanish political posts are loaded into the system's raw data store ready for processing.

**Acceptance Criteria:**

**Given** a CSV file with columns (text, platform, author, created_at) and its path configured
**When** the admin calls `POST /ingest`
**Then** all valid rows are inserted into `raw_posts` with source metadata captured
**And** a job record is created with status `completed`, row count, and timestamp

**Given** some rows in the CSV have missing required fields (e.g. empty text)
**When** ingestion runs
**Then** invalid rows are skipped and logged, while valid rows are still imported
**And** the job record captures the count and reason for skipped rows

**Given** the same CSV is ingested twice
**When** ingestion runs a second time
**Then** duplicate posts are detected (by content hash or source ID) and skipped rather than inserted again

---

### Story 1.5: NLP Classification Pipeline

As an admin or technical owner,
I want to trigger the NLP processing pipeline on ingested posts,
So that each raw post is classified by topic, subtopic, sentiment, target, and intensity, and an embedding is generated and stored for Q&A retrieval.

**Acceptance Criteria:**

**Given** unprocessed rows exist in `raw_posts`
**When** the admin calls `POST /process`
**Then** each post is classified and a corresponding row is inserted into `processed_posts` with topic, subtopic, sentiment, target, intensity, and a vector embedding
**And** a job record is created with status `completed`, count of posts processed, and timestamp

**Given** the NLP model or OpenAI API call fails for a specific post
**When** processing runs
**Then** that post is marked with an error status and skipped while remaining posts continue processing
**And** the job record captures the count and nature of failures

**Given** posts have already been processed (existing rows in `processed_posts`)
**When** processing runs again
**Then** already-processed posts are skipped to avoid duplicate entries

---

### Story 1.6: Ingestion Job Status Tracking API

As an admin or technical owner,
I want to view the status of recent ingestion and processing runs and re-run failed jobs via an API,
So that I can diagnose issues and restore data flow without accessing server logs directly.

**Acceptance Criteria:**

**Given** one or more ingestion or processing jobs have run
**When** the admin calls `GET /jobs`
**Then** the response lists recent jobs with: job type (ingest/process), status (completed/failed/running), start time, end time, row count, and error summary if failed

**Given** a job has status `failed`
**When** the admin calls `POST /jobs/{job_id}/retry`
**Then** the job re-runs for the same data source or unprocessed post set
**And** a new job record is created for the retry, preserving the original failed record

**Given** a job is currently running
**When** the admin calls `GET /jobs`
**Then** the running job appears with status `running` and start time, with no end time yet

---

## Epic 2: Analytics Dashboard & Data Exploration

Campaign managers, comms teams, and analysts can explore political discourse through an interactive dashboard — filtering by topic, party, time range, and platform; viewing sentiment trends and topic distributions; comparing parties; drilling into representative posts; and exporting snapshots for memos.

### Story 2.1: Frontend Shell Layout & Design System Setup

As a developer,
I want a reusable application shell with left navigation, top header, and a main content grid, plus a configured Tailwind design system,
So that all dashboard and Q&A views share consistent layout, spacing, typography, and color semantics from the start.

**Acceptance Criteria:**

**Given** the Next.js frontend is initialized
**When** a developer implements the shell layout
**Then** the app renders a slim left navigation bar, a top header bar, and a flexible main content area following a 12-column grid
**And** the left nav links to at least a Dashboard route and a Q&A route

**Given** the design system needs shared tokens
**When** Tailwind is configured
**Then** the config defines: a neutral/blue-gray base palette, a deep blue primary accent, semantic colors (green=positive, amber=warning, red=negative), an 8px spacing scale, and a sans-serif type scale (h1–h4, body, small)
**And** color is never the sole carrier of meaning — icons or labels accompany all sentiment/status indicators

**Given** any interactive element in the app
**When** a user navigates via keyboard
**Then** all focusable elements show a visible focus ring, and text/UI elements meet WCAG AA contrast ratios against their backgrounds

---

### Story 2.2: Post Volume & Sentiment Over Time Charts

As a campaign or communications user,
I want to view post volume and aggregated sentiment over time for a selected time range,
So that I can quickly understand how political discourse is evolving.

**Acceptance Criteria:**

**Given** processed posts exist in the database
**When** the user opens the dashboard with a default time range (e.g. last 7 days)
**Then** a time-series chart shows daily post volume and a sentiment trend line (positive/neutral/negative proportions) across the selected period
**And** the chart renders within 2 seconds for the target dataset size (≤10k posts)

**Given** the backend analytics endpoints
**When** `GET /analytics/volume` and `GET /analytics/sentiment` are called with `start_date` and `end_date` params
**Then** they return time-bucketed data (daily) with post counts and sentiment breakdowns suitable for charting

**Given** no posts exist for the selected time range
**When** the user views the dashboard
**Then** an empty state message explains that no data is available for this period and suggests adjusting the time range

---

### Story 2.3: Dashboard Filter Controls

As a campaign or communications user,
I want to filter the dashboard by topic, subtopic, party or target, time range, and platform,
So that I can focus on the specific slice of discourse that matters to my current question.

**Acceptance Criteria:**

**Given** the dashboard is loaded
**When** the user selects a topic, party, time range, or platform from the filter controls
**Then** all visible charts and metrics update to reflect only the filtered data within 2 seconds

**Given** filter controls are present
**When** the user selects a topic
**Then** the subtopic filter populates with only the subtopics belonging to that topic

**Given** filters are active
**When** the user clears all filters
**Then** the dashboard reverts to the default unfiltered view

**Given** a filter combination that returns no results
**When** the dashboard renders
**Then** an informative empty state is shown (not a blank chart) with a suggestion to broaden the filters

---

### Story 2.4: Topic Distribution & Trending Topics Panel

As a user,
I want to see which topics and subtopics are most discussed and which are most negative or positive within a given time window,
So that I can immediately identify what is driving the political conversation.

**Acceptance Criteria:**

**Given** processed posts exist for the selected filters
**When** the user views the topics panel
**Then** topics are listed ranked by volume (most discussed first), each showing post count and overall sentiment indicator (positive/neutral/negative)
**And** a secondary sort or badge highlights the most negative and most positive topics

**Given** the `GET /analytics/topics` endpoint is called with filter params
**When** the response is returned
**Then** it includes each topic with: label, post count, sentiment distribution (positive/neutral/negative counts), and top subtopics

**Given** the user clicks a topic tile
**When** the drill-down action fires
**Then** the dashboard filters update to that topic and subtopics panel expands to show subtopic-level breakdown, preserving other active filters

---

### Story 2.5: Representative Posts Panel (Evidence Post Cards)

As a user,
I want to view representative example posts for a chosen topic, subtopic, or sentiment segment,
So that I can understand the actual language and narratives driving the numbers.

**Acceptance Criteria:**

**Given** filters are applied (topic, sentiment, time range)
**When** the user views the posts panel
**Then** up to 10 representative posts are displayed as Evidence Post Cards, each showing: original text, platform, date, sentiment label, and topic tag

**Given** `GET /analytics/posts` is called with filter params
**When** the response is returned
**Then** it returns a ranked list of representative posts (selected by relevance/diversity, not purely random) with all metadata fields needed for the card

**Given** a post card is displayed
**When** the user clicks to copy the post text
**Then** the text is copied to the clipboard and a brief confirmation indicator appears

---

### Story 2.6: Cross-Party Sentiment Comparison

As an analyst or campaign manager,
I want to compare sentiment and volume across at least two parties or targets for a chosen topic and time range,
So that I can understand how my party's performance on an issue compares to competitors.

**Acceptance Criteria:**

**Given** the user selects a topic and a time range
**When** the user enables the comparison view and selects two or more parties
**Then** a side-by-side or overlaid chart shows sentiment distribution and volume for each selected party across the time window

**Given** `GET /analytics/compare` is called with `topic`, `parties[]`, `start_date`, `end_date`
**When** the response is returned
**Then** it returns per-party breakdowns: post count, sentiment distribution (positive/neutral/negative), and top subtopics for each party

**Given** the campaign manager journey (FR19)
**When** a user selects the "Housing" topic, sets a 7-day range, and compares two parties
**Then** the comparison view renders correctly with both parties' data visible and the most negative subtopic is identifiable from the chart or topic panel

---

### Story 2.7: Spike Alert Detection & Banner

As a communications or rapid-response user,
I want the dashboard to surface sudden spikes in post volume or negative sentiment as a prominent alert,
So that I can immediately see when something unusual is happening without having to spot it in a chart myself.

**Acceptance Criteria:**

**Given** processed posts show a significant volume or sentiment spike within the last 2–24 hours (configurable threshold)
**When** the dashboard loads
**Then** a Spike Alert Banner appears at the top of the main content area showing: the topic/entity spiking, the nature of the spike (volume or sentiment), and a link to investigate

**Given** `GET /analytics/spikes` is called
**When** the response is returned
**Then** it returns any detected spikes with: topic label, spike type, magnitude indicator, and the time window of the spike

**Given** no spikes are detected
**When** the dashboard loads
**Then** the Spike Alert Banner area is hidden — no empty banner or placeholder is shown

**Given** a Spike Alert Banner is visible on the dashboard
**When** the user clicks the "Investigate" link on the banner
**Then** the Q&A panel opens (or scrolls into view) with the question input pre-filled with a suggested question scoped to the spiking topic (e.g. "What are people saying about [topic] right now?") and the topic filter is pre-set

---

### Story 2.8: Analyst Deep-Dive Export & Copy

As an analyst,
I want to export a structured snapshot of aggregated metrics and representative posts and copy charts or summaries,
So that I can use the data directly in memos, briefings, and presentations without manual transcription.

**Acceptance Criteria:**

**Given** the analyst has applied filters (topic, time range, parties)
**When** the analyst clicks "Export"
**Then** a JSON or CSV file downloads containing: filter parameters used, aggregated metrics (sentiment counts, volume by topic), and up to 50 representative posts with metadata

**Given** `GET /analytics/export` is called with filter params
**When** the response is returned
**Then** it returns the structured snapshot as a downloadable file with Content-Disposition header

**Given** a chart or narrative summary block is visible
**When** the user clicks a "Copy summary" action on that block
**Then** the formatted text of the summary (key metrics + topic labels) is copied to the clipboard

**Given** the analyst performs a month-long deep dive (FR22) — selects a 30-day range, a specific topic, and compares two parties
**When** the analyst exports the snapshot
**Then** the export file includes data spanning the full 30-day range and correctly reflects both parties' data

---

## Epic 3: LLM-Powered Q&A Intelligence Interface

Campaign managers, comms, and analysts can type natural-language political questions, receive concise evidence-backed answers (narrative summary + metrics + representative posts), and iterate multiple questions in a session.

### Story 3.1: Q&A Retrieval & Aggregation Backend

As a campaign, communications, or analyst user,
I want the backend to retrieve relevant processed posts and aggregate metrics in response to a natural-language question with optional filters,
So that the Q&A system has a grounded, data-driven evidence set to answer from.

**Acceptance Criteria:**

**Given** a `POST /qa` request with a natural-language `question` and optional `filters` (topic, party, time_range, platform)
**When** the endpoint processes the request
**Then** it performs vector similarity search over `processed_posts` embeddings using the question as the query vector, retrieving the top-N most relevant posts
**And** it aggregates sentiment counts, post volume, and top subtopics from the retrieved set

**Given** filters are provided alongside the question
**When** retrieval runs
**Then** the vector search is scoped to only posts matching all specified filters before ranking by similarity

**Given** the target dataset size (≤10k posts)
**When** the retrieval and aggregation phase completes
**Then** it returns results in under 2 seconds, leaving budget for the LLM call within the overall 5-second NFR1 target

**Given** no posts match the question + filter combination
**When** the endpoint processes the request
**Then** it returns an empty result set with a flag indicating insufficient data, rather than hallucinating an answer

---

### Story 3.2: LLM Answer Generation

As a campaign, communications, or analyst user,
I want the system to generate a concise narrative summary from the retrieved posts and aggregated metrics using an LLM,
So that I receive a grounded, human-readable answer rather than raw data.

**Acceptance Criteria:**

**Given** retrieved posts and aggregated metrics from Story 3.1
**When** the LLM is called
**Then** it generates a concise narrative summary (2–4 sentences) that directly answers the original question, referencing the key sentiment findings and notable subtopics
**And** the full `POST /qa` response payload includes: `summary` (string), `metrics` (post count, sentiment breakdown), and `evidence_posts` (list of top supporting posts with text, platform, date, sentiment)

**Given** the OpenAI API call fails or times out
**When** the Q&A endpoint handles the error
**Then** it returns a structured error response (not a 500 crash) with a message like "Answer generation temporarily unavailable — here are the retrieved posts and metrics" plus the raw retrieval results
**And** end-to-end Q&A latency for a successful call is under 5 seconds for the target dataset (NFR1)

**Given** the retrieved evidence set is empty (insufficient data)
**When** the LLM step runs
**Then** the LLM call is skipped and the response explains there is not enough data for the applied filters, rather than generating a speculative answer

---

### Story 3.3: Q&A Frontend — Question Input & Insight Summary Panel

As a campaign, communications, or analyst user,
I want a prominent question input with preset suggestions and a structured answer panel showing summary, metrics, and evidence posts,
So that I can ask political questions and immediately understand the grounded answer without leaving the app.

**Acceptance Criteria:**

**Given** the user opens the Q&A view (or the Q&A panel on the dashboard)
**When** the page renders
**Then** a prominent text input is visible with placeholder text and 3–5 preset suggestion chips (e.g. "What's spiking?", "How are we doing on housing vs Party X?", "Main negative narratives about our leader?")

**Given** the user types a question and submits
**When** the request is in flight
**Then** a loading state ("Analyzing discourse…") replaces the answer area with a visible indicator that does not obscure the question input

**Given** a successful Q&A response is received
**When** the answer renders
**Then** the Insight Summary Panel shows: (1) the narrative summary, (2) key metrics strip (post count, sentiment breakdown), (3) a grid of up to 5 Evidence Post Cards
**And** a label like "Based on 1,234 posts · Last 7 days" is visible so users understand the scope and can judge reliability

**Given** the user has received an answer
**When** the user types a new question and submits
**Then** the previous answer is replaced with the new answer without a page reload (FR18), and the question history is not required to be preserved

---

### Story 3.4: Q&A Filter Controls & Multi-Session Iteration

As a campaign, communications, or analyst user,
I want to specify optional filters (topic, time range, party, platform) alongside my question,
So that I can scope my question to the exact slice of data I care about.

**Acceptance Criteria:**

**Given** the Q&A input is visible
**When** the user expands the filter panel
**Then** they can select topic, subtopic, party/target, time range, and platform — matching the same filter options available on the dashboard

**Given** filters are set and a question is submitted
**When** the `POST /qa` request is made
**Then** all selected filter values are passed as parameters and the retrieval is scoped accordingly

**Given** the user submits a question with no filters applied
**When** the Q&A processes the request
**Then** retrieval runs across the full dataset with no filter scoping — all filters are optional

**Given** an active filter selection
**When** the user clears one or all filters
**Then** the filter state resets to "no filter" and the next question submission uses the cleared state

---

### Story 3.5: Narrative Clusters & Rapid Response Investigation

As a rapid-response user,
I want the Q&A response to group related posts into distinct narrative clusters and display them as Narrative Cluster Cards, and I want to click dashboard topic tiles to pre-fill the question input,
So that I can quickly identify the 2–3 key narrative threads driving a crisis and investigate without manual reformulation.

**Acceptance Criteria:**

**Given** a Q&A response for a crisis-style question (e.g. "What are the main negative narratives about our leader right now?")
**When** the response renders
**Then** the Insight Summary Panel includes a narrative clusters section showing 2–4 Narrative Cluster Cards, each with: a cluster label, sentiment tag, post count, and 1–2 representative quotes

**Given** `POST /qa` returns its payload
**When** the backend groups retrieved posts into clusters
**Then** clustering is performed by subtopic or topic label (as a lightweight proxy for narrative grouping in the MVP), with each cluster containing its top posts

**Given** a topic tile or narrative cluster card is clicked on the dashboard
**When** the click action fires
**Then** the Q&A panel opens (or scrolls into view) with the question input pre-filled based on the clicked context

---

### Story 3.6: Q&A Resilience, Error States & Demo Readiness

As a rapid-response user or demo participant,
I want the Q&A interface to handle errors and empty results gracefully and allow me to retry or adjust filters without losing my context,
So that I can recover from transient issues quickly and the system behaves reliably during live demonstrations.

**Acceptance Criteria:**

**Given** the Q&A request fails due to a transient error (network issue, LLM timeout)
**When** the error is received
**Then** the answer panel shows a plain-language message (e.g. "Something went wrong — please try again") with a visible "Retry" button that resubmits the same question and filters

**Given** the user adjusts filters after a failed or empty result
**When** a new question is submitted with updated filters
**Then** the interface clears the previous error/empty state and shows the new loading state, then the new result

**Given** a question returns no results due to an overly narrow filter
**When** the empty state renders
**Then** the message explains why (e.g. "No posts found for this topic in the last 2 hours") and suggests a concrete next step (e.g. "Try a wider time range or remove the platform filter")

**Given** an instructor or classmate submits their own ad-hoc question during a demo (FR33)
**When** the question is processed
**Then** the system returns a coherent, data-grounded answer (or a clear empty-state explanation) without crashing or requiring a page reload

---

## Epic 4: Admin, Operations & Demo Readiness

Admin and technical owners can monitor ingestion health, view job status and error summaries, run health checks, recover from failures, and reset the system for a clean demo run.

### Story 4.1: Admin Operations Dashboard UI

As an admin or technical owner,
I want a dedicated admin view showing ingestion job history, statuses, error summaries, and data volume per source,
So that I can monitor pipeline health and restore data flow when something fails without reading server logs.

**Acceptance Criteria:**

**Given** the admin navigates to the `/admin` route
**When** the page loads
**Then** it displays a table of recent ingestion and processing jobs with columns: job type, status (completed/failed/running), start time, end time, row count, and error message if failed (FR24)

**Given** a job has status `failed`
**When** the admin clicks "Retry" next to that job
**Then** a retry is triggered (calling `POST /jobs/{job_id}/retry`) and the table updates to show the new job running (FR23, FR6)

**Given** jobs have run for multiple data sources
**When** the admin views the ops dashboard
**Then** a summary section shows approximate post counts per source (e.g. "twitter_dump.csv: 4,823 posts") so the admin can verify coverage (FR26)

**Given** the admin follows the documented recovery flow (FR23)
**When** they identify a failed job, click retry, and confirm the new job completes successfully
**Then** the pipeline is restored and new posts become available for analytics and Q&A without any server-level intervention

---

### Story 4.2: System Health Check Endpoints & Status Indicators

As an admin or technical owner,
I want health check endpoints and a visible status indicator in the admin view,
So that I can confirm the API and database are operational before and during a demo session.

**Acceptance Criteria:**

**Given** the backend is running
**When** `GET /health` is called
**Then** it returns `{"status": "ok", "timestamp": "..."}` with HTTP 200 within 500ms

**Given** the backend is running with a live database connection
**When** `GET /health/db` is called
**Then** it returns `{"status": "ok", "db": "connected"}` confirming PostgreSQL connectivity
**And** if the DB is unreachable, it returns `{"status": "degraded", "db": "disconnected"}` with HTTP 503

**Given** the admin views the ops dashboard
**When** the page loads
**Then** a status strip at the top shows API health (green/red) and DB health (green/red) based on the health endpoint responses
**And** the status refreshes automatically every 30 seconds so the admin can keep the page open during a demo session (NFR6)

---

### Story 4.3: Demo Environment Configuration & Unauthenticated Access

As a demo operator,
I want the platform to be accessible to all classroom participants without individual login, with environment configuration documented for the demo setup,
So that any instructor or classmate can use the platform during the demo without friction.

**Acceptance Criteria:**

**Given** the application is running in the demo environment
**When** any user navigates to the app URL
**Then** they reach the dashboard directly with no login screen or authentication prompt (FR32)

**Given** the app is configured for the demo environment
**When** a developer follows the README / setup guide
**Then** they can configure the full stack (frontend + backend + DB) using only the `.env.example` as a reference, with no undocumented secrets or environment variables required

**Given** multiple classroom users access the app simultaneously
**When** 5–10 users load the dashboard or submit Q&A questions concurrently
**Then** the system serves all requests without errors, even if response times approach the upper NFR bounds (NFR3)

---

### Story 4.4: Demo Reset & Clean Pipeline Reinitialization

As a demo operator,
I want to reset the dataset and run a clean end-to-end pipeline in preparation for a new demonstration,
So that each demo starts from a known, consistent state with fresh data.

**Acceptance Criteria:**

**Given** the demo operator wants to reset for a new run
**When** they call `POST /admin/reset` (or run the documented reset script)
**Then** all processed posts and job records are cleared from the database, while raw posts are optionally preserved or also cleared based on a parameter

**Given** a clean reset has been performed
**When** the operator triggers `POST /ingest` followed by `POST /process`
**Then** the full pipeline runs end-to-end from the configured CSV source and produces a fresh set of processed posts and embeddings
**And** the dashboard and Q&A views reflect the newly processed data without requiring a frontend restart

**Given** the full pipeline is run from a clean state on a typical student machine
**When** the operator times the run
**Then** ingestion + processing of the demo dataset (≤10k posts) completes within a reasonable preparation window (NFR5), producing stable, inspectable outputs in the database
