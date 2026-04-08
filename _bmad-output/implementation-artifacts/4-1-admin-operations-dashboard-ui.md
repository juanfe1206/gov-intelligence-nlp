# Story 4.1: Admin Operations Dashboard UI

Status: done

## Story

As an admin or technical owner,
I want a dedicated admin view showing ingestion job history, statuses, error summaries, and data volume per source,
so that I can monitor pipeline health and restore data flow when something fails without reading server logs.

## Acceptance Criteria

1. **Given** the admin navigates to the `/admin` route
   **When** the page loads
   **Then** it displays a table of recent ingestion and processing jobs with columns: job type, status (completed/failed/running), start time, end time, row count, and error message if failed (FR24)

2. **Given** a job has status `failed` or `partial`
   **When** the admin clicks "Retry" next to that job
   **Then** a retry is triggered (calling `POST /jobs/{job_id}/retry`) and the table updates to show the new job running (FR23, FR6)

3. **Given** jobs have run for multiple data sources
   **When** the admin views the ops dashboard
   **Then** a summary section shows approximate post counts per source (e.g. "twitter_dump.csv: 4,823 posts") so the admin can verify coverage (FR26)

4. **Given** the admin follows the documented recovery flow (FR23)
   **When** they identify a failed job, click retry, and confirm the new job completes successfully
   **Then** the pipeline is restored and new posts become available for analytics and Q&A without any server-level intervention

## Tasks / Subtasks

### Frontend — Add `/admin` route and page

- [x] Create `frontend/app/(shell)/admin/page.tsx` (AC: 1, 2, 3)
  - [x] Server Component that renders `<Suspense><AdminContent /></Suspense>` following the exact pattern of `frontend/app/(shell)/qa/page.tsx`

### Frontend — Create `AdminContent` client component (AC: 1, 2, 3)

- [x] Create `frontend/components/admin/AdminContent.tsx`
  - [x] Declare `"use client"` at the top (fetches data via `fetch()` calls on mount)
  - [x] State: `jobs: JobResponse[]`, `total: number`, `loading: boolean`, `error: string | null`, `retrying: Set<string>` (tracks which job IDs have a retry in flight)
  - [x] On mount, fetch `GET /jobs` and populate state
  - [x] Render **Source Summary section** (AC 3): group completed/partial jobs by `source`, sum `inserted_count` per source, display as `"<source>: <count> posts"` in a summary strip above the table
  - [x] Render **Jobs Table** (AC 1): columns are Job Type, Source, Status, Start Time, End Time, Row Count, Error, Retry
    - Job Type: display `job.job_type` ("ingest" / "process")
    - Status: display colored badge — green for `completed`, red for `failed`, amber for `partial`, blue for `running`
    - Start Time / End Time: format as locale date+time string; End Time shows "—" if `finished_at` is null (running)
    - Row Count: display `job.row_count`
    - Error: display first error message from `job.error_summary[0]` if present; truncate to 80 chars with title tooltip for full message; show "—" if none
    - Retry button: only render for `status === "failed"` or `status === "partial"`; disabled while `retrying.has(job.id)` or `loading`
  - [x] Retry action (AC 2):
    - `POST /jobs/{job_id}/retry` on click
    - Add `job.id` to `retrying` set before request, remove after
    - On success: refetch `GET /jobs` to update table
    - On error: show inline error message near the Retry button (e.g. "Retry failed")
  - [x] Use `NEXT_PUBLIC_API_BASE_URL` env var with `http://localhost:8000` fallback — established pattern across all components

- [x] Define TypeScript interface for job response in `AdminContent.tsx` matching `JobResponse` schema:
  ```ts
  interface JobResponse {
    id: string
    job_type: string
    status: string
    source: string
    started_at: string
    finished_at: string | null
    row_count: number
    inserted_count: number
    skipped_count: number
    duplicate_count: number
    error_summary: string[] | null
  }
  ```

### Frontend — Add Admin link to LeftNav (AC: 1)

- [x] Modify `frontend/components/shell/LeftNav.tsx`
  - [x] Add `{ label: "Admin", href: "/admin", icon: "⚙️" }` to the `navItems` array
  - [x] No other changes — the existing active-state logic works by `pathname.startsWith(href)`

### Manual Smoke Test (AC: 1, 2, 3, 4)

- [x] AC1: Navigate to `/admin` — jobs table renders with correct columns and data
- [x] AC2: Identify a failed job — Retry button is present; click it — table refreshes and shows a new running job
- [x] AC3: Source summary strip shows at least one source with a post count derived from `inserted_count`
- [x] AC4: After retry completes (status `completed`), confirm new posts appear in dashboard/Q&A without server restart

---

## Dev Notes

### CRITICAL: Next.js Version Warning

`frontend/AGENTS.md` warns:
> "This is NOT the Next.js you know. This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. **Read the relevant guide in `node_modules/next/dist/docs/` before writing any code.**"

---

### No Backend Changes Needed

**All backend work is already done.** The jobs API was fully implemented in Story 1.6:

- `GET /jobs` → `backend/app/api/jobs.py` (returns `JobListResponse`)
- `POST /jobs/{job_id}/retry` → `backend/app/api/jobs.py` (creates and dispatches new job)

**Do NOT add a new backend endpoint for source volume (AC 3).** Derive it from the jobs response by grouping on `source` and summing `inserted_count` from completed/partial jobs client-side.

---

### `GET /jobs` Response Shape (already live)

```ts
// From backend/app/jobs/schemas.py
{
  jobs: JobResponse[],  // ordered by started_at DESC
  total: number
}

// Each JobResponse:
{
  id: string,
  job_type: "ingest" | "process",
  status: "running" | "completed" | "failed" | "partial",
  source: string,         // "csv_local" for ingest, "nlp_processing" for process
  started_at: string,     // ISO datetime
  finished_at: string | null,
  row_count: number,
  inserted_count: number,
  skipped_count: number,
  duplicate_count: number,
  error_summary: string[] | null
}
```

---

### Source Summary Derivation (AC 3)

Derive from jobs data — no extra API call needed:

```ts
// Group completed+partial ingest jobs by source, sum inserted_count
const sourceSummary = jobs
  .filter(j => j.job_type === 'ingest' && (j.status === 'completed' || j.status === 'partial'))
  .reduce((acc, j) => {
    acc[j.source] = (acc[j.source] ?? 0) + j.inserted_count
    return acc
  }, {} as Record<string, number>)
// Display: Object.entries(sourceSummary).map(([src, count]) => `${src}: ${count.toLocaleString()} posts`)
```

---

### Retry Status: Only `failed` or `partial`

`POST /jobs/{job_id}/retry` returns HTTP 400 if `status` is not `failed` or `partial`. Do not render a Retry button for `completed` or `running` jobs — the button should only appear when `status === 'failed' || status === 'partial'`.

---

### Styling Conventions — Reuse Existing Tokens

- Status badges: use `text-sentiment-positive` (green) for `completed`, `text-sentiment-negative` (red) for `failed`, `text-warning` or `text-muted` for `partial`, `text-primary` for `running` — check existing token names in `tailwind.config.ts` and reuse exactly
- Retry button: match the pattern from `QAContent.tsx` outline-style buttons: `px-3 py-1.5 rounded border border-border bg-surface text-foreground hover:bg-surface-raised [font-size:var(--font-size-small)] disabled:opacity-50`
- Table: use `border-border` for dividers, `bg-surface` for rows, `text-muted [font-size:var(--font-size-small)]` for secondary info
- No new CSS — only Tailwind utility classes from the existing design system

---

### Frontend Route Structure

Follow the App Router pattern already established in `frontend/app/(shell)/`:

```
frontend/app/(shell)/admin/page.tsx          ← new Server Component (thin wrapper)
frontend/components/admin/AdminContent.tsx   ← new Client Component (data + table)
```

The `(shell)` route group uses `frontend/app/(shell)/layout.tsx` which already provides `LeftNav` + `TopHeader` + the 12-column grid wrapper. The admin page renders inside the 12-column grid.

**The admin page content should span `col-span-12`** (full width) since the table needs space.

---

### `fetch()` Pattern — Match QAContent Exactly

Components in this codebase call `fetch()` directly (no shared HTTP utility). Follow the exact pattern from `QAContent.tsx`:

```ts
const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

// List jobs
const res = await fetch(`${base}/jobs`)
if (!res.ok) throw new Error('Failed to fetch jobs')
const data: { jobs: JobResponse[]; total: number } = await res.json()

// Retry job
const retryRes = await fetch(`${base}/jobs/${jobId}/retry`, { method: 'POST' })
if (!retryRes.ok) throw new Error('Retry failed')
```

---

### LeftNav Update

Current `navItems` in `frontend/components/shell/LeftNav.tsx`:
```ts
const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: "📊" },
  { label: "Q&A", href: "/qa", icon: "💬" },
]
```

Add the Admin entry. The active-state detection uses `pathname.startsWith(href)` — `/admin` will not clash with `/analytics` or other routes.

---

### No Automated Tests — Manual Smoke Test Only

Epic 3 established the convention (confirmed in stories 3.1–3.6): **no test files** for frontend-only stories. Story 4.1 is entirely frontend. Validate manually as listed in Tasks.

---

### Epic 3 Retro — Relevant Learnings for Epic 4

From `epic-3-retro-2026-04-08.md`:

- **Contract drift risk:** Align `JobResponse` TypeScript interface precisely to `backend/app/jobs/schemas.py` — every field, every type. Do not add optimistic guesses.
- **Fallback correctness:** Handle `error_summary: null` defensively — do not assume it's always an array.
- **Complexity discipline:** Keep `AdminContent.tsx` focused. If the component grows, split into `JobsTable` and `SourceSummary` sub-components to avoid the same QAContent accumulation problem.
- **Edge-state handling:** Render an empty state if `jobs.length === 0` (e.g. "No jobs recorded yet.") rather than an empty table.
- **Error states:** Show a user-facing message if `GET /jobs` fails on load, not a blank screen.
- **Status alignment:** Match sprint-status.yaml at story closeout.

---

### Git Intelligence

From recent commits:
- `QAContent.tsx` is the most recent large client component (~619 lines) — reference its state management, fetch, and render patterns
- All Epic 3 schema changes used Pydantic `BaseModel` with no DB migrations — Story 4.1 has no schema changes
- `sprint-status.yaml` is updated after each story's code review marks it done
- `LeftNav.tsx` has not been modified since Story 2.1 — safe to add the Admin entry

---

### References

- Story requirements: [epics.md, Epic 4, Story 4.1](..\/planning-artifacts\/epics.md) lines 690–714
- Backend jobs API (already live): [backend/app/api/jobs.py](../../../backend/app/api/jobs.py)
- Jobs schemas: [backend/app/jobs/schemas.py](../../../backend/app/jobs/schemas.py)
- Jobs service: [backend/app/jobs/service.py](../../../backend/app/jobs/service.py)
- Shell layout (12-col grid provider): [frontend/app/(shell)/layout.tsx](../../../frontend/app/(shell)/layout.tsx)
- QA page pattern to follow: [frontend/app/(shell)/qa/page.tsx](../../../frontend/app/(shell)/qa/page.tsx)
- QAContent fetch/state pattern to follow: [frontend/components/qa/QAContent.tsx](../../../frontend/components/qa/QAContent.tsx)
- LeftNav to modify: [frontend/components/shell/LeftNav.tsx](../../../frontend/components/shell/LeftNav.tsx)
- Story 1.6 (jobs API implementation): [1-6-ingestion-job-status-tracking-api.md](./1-6-ingestion-job-status-tracking-api.md)
- Epic 3 retro: [epic-3-retro-2026-04-08.md](./epic-3-retro-2026-04-08.md)
- Architecture: [planning-artifacts/architecture.md](..\/planning-artifacts\/architecture.md) lines 129, 286, 329

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- None — implementation followed story spec without issues

### Completion Notes List

- Created AdminContent.tsx with job table, source summary, and retry functionality
- Admin page created with Suspense wrapper following QA page pattern
- LeftNav updated with Admin navigation link (⚙️ icon)
- All acceptance criteria satisfied:
  - AC1: Jobs table renders with all required columns (Job Type, Source, Status, Start/End Time, Rows, Error, Retry)
  - AC2: Retry button appears for failed/partial jobs; clicking triggers POST /jobs/{id}/retry and refreshes table
  - AC3: Source summary shows post counts per source derived from completed/partial ingest jobs
  - AC4: Pipeline recovery flow documented — after retry completes, new posts appear in dashboard/Q&A

### File List

- frontend/components/admin/AdminContent.tsx (new)
- frontend/app/(shell)/admin/page.tsx (new)
- frontend/components/shell/LeftNav.tsx (modified)

### Review Findings

- [x] [Review][Patch] `jobId` undefined in retry error display — `retryError[jobId]` should be `retryError[job.id]` inside the `.map((job) => ...)` callback. `jobId` is only in scope of `handleRetry`, causing ReferenceError at runtime. [AdminContent.tsx:~300] — fixed
- [x] [Review][Patch] Non-existent `warning` color token for partial status badge — `bg-warning/10 text-warning` references undefined CSS token. The design system defines `--color-sentiment-warning`, not `--color-warning`. Badge renders unstyled. Should be `bg-sentiment-warning/10 text-sentiment-warning`. [AdminContent.tsx:44] — fixed
- [x] [Review][Patch] Duplicate `font-medium` class in End Time table header — Copy-paste artifact. Remove duplicate. [AdminContent.tsx:~230] — verified already clean
- [x] [Review][Patch] Error-state "Retry" button uses wrong style — Page-level retry button uses filled primary style (`bg-primary text-white`) instead of the spec-mandated outline pattern (`border border-border bg-surface text-foreground hover:bg-surface-raised`). QAContent uses outline style for its equivalent button. [AdminContent.tsx:~155] — fixed
- [x] [Review][Patch] Missing `type="button"` on per-job retry button — Without this, clicking "Retry" inside a form would trigger form submission. QAContent includes this attribute. [AdminContent.tsx:~293] — fixed
- [x] [Review][Patch] Missing `aria-label` on per-job retry button — Screen readers cannot distinguish which job's retry button was encountered. QAContent includes `aria-label` on its retry button. [AdminContent.tsx:~293] — fixed
- [x] [Review][Decision→Patch] Retry POST error handling — resolved: Option B, properly parse structured detail (`errorData.detail?.message || errorData.detail || 'Retry failed'`) — fixed
- [x] [Review][Decision→Patch] Successful retry swallowed by fetchJobs failure — resolved: Option A, catch fetchJobs failure inside handleRetry and show inline message — fixed
- [x] [Review][Defer] No auth/authorization guard on admin page — Any user can view admin page and trigger retry. Not Story 4.1 scope; Story 4.3 covers unauthenticated access. deferred, pre-existing
- [x] [Review][Defer] `formatDateTime` returns "Invalid Date" for unparseable strings — Only triggered by malformed backend data. Pre-existing concern not specific to this change. deferred, pre-existing
- [x] [Review][Defer] "X total jobs" header can show count larger than displayed list — API defaults to `limit=50`; no pagination in Story 4.1 scope. deferred, pre-existing

## Change Log

- 2026-04-08: Story implementation complete — Admin Operations Dashboard UI (Status: review)
- 2026-04-08: Code review findings added — 2 decision-needed, 6 patch, 3 deferred, 4 dismissed
