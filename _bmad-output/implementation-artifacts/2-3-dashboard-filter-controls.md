# Story 2.3: Dashboard Filter Controls

Status: done

## Story

As a campaign or communications user,
I want to filter the dashboard by topic, subtopic, party or target, time range, and platform,
So that I can focus on the specific slice of discourse that matters to my current question.

## Acceptance Criteria

1. **Given** the dashboard is loaded
   **When** the user selects a topic, party, time range, or platform from the filter controls
   **Then** all visible charts and metrics update to reflect only the filtered data within 2 seconds

2. **Given** filter controls are present
   **When** the user selects a topic
   **Then** the subtopic filter populates with only the subtopics belonging to that topic

3. **Given** filters are active
   **When** the user clicks "Clear filters"
   **Then** the dashboard reverts to the default unfiltered view (last 7 days, no topic/party/platform filter)

4. **Given** a filter combination that returns no results
   **When** the dashboard renders
   **Then** an informative empty state is shown (not a blank chart) with a suggestion to broaden the filters

## Tasks / Subtasks

- [x] Backend: Add optional filter params to analytics endpoints (AC: 1, 4)
  - [x] Update `backend/app/api/analytics.py` — add optional `topic`, `subtopic`, `target`, `platform` Query params to `/volume` and `/sentiment`
  - [x] Update `backend/app/analytics/schemas.py` — add `PlatformsResponse` schema
  - [x] Update `backend/app/analytics/service.py` — pass filter params through and apply WHERE clauses
  - [x] Add `GET /analytics/platforms` endpoint — return distinct platform values from `raw_posts`

- [x] Frontend: FilterBar component (AC: 1, 2, 3)
  - [x] Create `frontend/components/dashboard/FilterBar.tsx` — filter UI with topic, subtopic, target, platform, time-range dropdowns + Clear button
  - [x] Fetch taxonomy on mount from `GET /taxonomy` to populate topic/subtopic/target options
  - [x] Fetch platforms on mount from `GET /analytics/platforms` to populate platform options
  - [x] Cascading subtopic: when topic changes, reset subtopic and show only that topic's subtopics

- [x] Frontend: Wire filters into DashboardContent (AC: 1, 3, 4)
  - [x] Update `frontend/components/dashboard/DashboardContent.tsx` — add filter state, render `<FilterBar>`, pass filter params to API calls, update useEffect dependency array
  - [x] Update empty-state message to distinguish "no data for filters" vs "no data for period"

- [x] Validate (AC: 1, 2, 3, 4)
  - [x] `npm run lint` — zero errors
  - [x] `npm run build` — clean TypeScript build
  - [x] Manual: open `/dashboard`, apply each filter type, confirm charts update; verify cascading subtopic; verify Clear resets; verify no-result empty state

## Dev Notes

### CRITICAL: Read Bundled Next.js Docs Before Writing Code

`frontend/AGENTS.md` warns: **"This is NOT the Next.js you know. This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code."**

This project uses:
- **Next.js 16.2.2** (NOT 14 or 15)
- **React 19.2.4**
- **Tailwind CSS v4** — CSS-first, no `tailwind.config.js`
- **TypeScript 5.x**

### Existing Files to EXTEND (Do NOT recreate)

**Modify these — do not touch their surrounding structure:**

```
frontend/components/dashboard/DashboardContent.tsx   ← ADD filter state + FilterBar render
backend/app/api/analytics.py                          ← ADD optional filter Query params
backend/app/analytics/service.py                      ← ADD optional WHERE clauses
backend/app/analytics/schemas.py                      ← ADD PlatformsResponse schema
```

**Create new:**

```
frontend/components/dashboard/FilterBar.tsx           ← NEW filter UI component
```

**Do NOT touch:**
- `frontend/app/(shell)/dashboard/page.tsx` — no changes needed (server component, renders DashboardContent)
- `frontend/components/charts/VolumeChart.tsx` — no changes needed
- `frontend/components/charts/SentimentChart.tsx` — no changes needed
- `frontend/app/(shell)/qa/page.tsx` — do not touch

### Current DashboardContent State (from Story 2.2)

Current `DashboardContent.tsx` has hardcoded 7-day dates with NO filter state. Story 2.2's dev notes explicitly stated:

> "Story 2.3 will add `topic`, `party`, `time_range`, `platform` filter state to `DashboardContent`. Story 2.3 will extend the backend endpoints with filter params — service functions accept `start_date`/`end_date` only for now."

The date computation is already correct (uses explicit year/month/day construction — NOT `toISOString().split('T')[0]` due to UTC timezone shift bug fixed in Story 2.2).

### Backend: Extend Analytics Endpoints

**DO NOT break existing callers** — all new params must be optional with `None` as default.

#### Updated `backend/app/api/analytics.py`

Add these optional Query params to BOTH `/volume` and `/sentiment` endpoints:

```python
topic: str | None = Query(default=None, description="Filter by topic name (e.g. 'vivienda')"),
subtopic: str | None = Query(default=None, description="Filter by subtopic name (e.g. 'alquiler')"),
target: str | None = Query(default=None, description="Filter by political target (e.g. 'pp', 'sanchez')"),
platform: str | None = Query(default=None, description="Filter by platform (e.g. 'twitter')"),
```

Pass all four to the service function call.

#### New `GET /analytics/platforms` endpoint

Add to `backend/app/api/analytics.py`:

```python
@router.get("/platforms", response_model=PlatformsResponse)
async def get_platforms(session: AsyncSession = Depends(get_db)) -> PlatformsResponse:
    """Return distinct platform values from raw_posts."""
    stmt = select(RawPost.platform).distinct().order_by(RawPost.platform)
    result = await session.execute(stmt)
    platforms = [row[0] for row in result.all() if row[0]]
    return PlatformsResponse(platforms=platforms)
```

Register import: add `from app.analytics.schemas import ..., PlatformsResponse` and `from app.models.raw_post import RawPost`.

#### Updated `backend/app/analytics/schemas.py`

Add:

```python
class PlatformsResponse(BaseModel):
    """Response for available platforms endpoint."""
    platforms: list[str]
```

#### Updated `backend/app/analytics/service.py`

Both `get_volume` and `get_sentiment` need new optional params and WHERE clauses:

```python
async def get_volume(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    topic: str | None = None,
    subtopic: str | None = None,
    target: str | None = None,
    platform: str | None = None,
) -> VolumeResponse:
    date_col = cast(RawPost.created_at, Date)
    filters = [
        date_col >= start_date,
        date_col <= end_date,
        or_(
            ProcessedPost.error_status.is_(False),
            ProcessedPost.error_status.is_(None),
        ),
    ]
    if topic is not None:
        filters.append(ProcessedPost.topic == topic)
    if subtopic is not None:
        filters.append(ProcessedPost.subtopic == subtopic)
    if target is not None:
        filters.append(ProcessedPost.target == target)
    if platform is not None:
        filters.append(RawPost.platform == platform)

    stmt = (
        select(date_col.label("day"), func.count().label("count"))
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(and_(*filters))
        .group_by(date_col)
        .order_by(date_col)
    )
    # ... rest unchanged (zero-fill loop)
```

Apply the same pattern to `get_sentiment`.

### Frontend: FilterBar Component

**New file:** `frontend/components/dashboard/FilterBar.tsx`

Key requirements:
- `'use client'` directive
- Fetches taxonomy from `GET /taxonomy` on mount (no auth, already enabled via CORS)
- Fetches platforms from `GET /analytics/platforms` on mount
- Renders: Topic select → Subtopic select (cascades) → Target select → Platform select → Time range select → Clear button
- When topic changes: reset subtopic value to `""`
- When "Clear" is clicked: reset all to default values and call `onClearFilters()`
- All selects have an "All" first option (value `""`)
- `'use client'` because it uses state for loading filter options

```tsx
'use client'
import { useEffect, useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface Topic {
  name: string
  label: string
  subtopics: Array<{ name: string; label: string }>
}

interface Taxonomy {
  topics: Topic[]
  targets: {
    parties: Array<{ name: string; label: string }>
    leaders: Array<{ name: string; label: string }>
  }
}

export interface FilterState {
  topic: string
  subtopic: string
  target: string
  platform: string
  startDate: string
  endDate: string
}

interface Props {
  filters: FilterState
  onChange: (filters: FilterState) => void
}

export default function FilterBar({ filters, onChange }: Props) {
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null)
  const [platforms, setPlatforms] = useState<string[]>([])

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/taxonomy`).then((r) => r.json()),
      fetch(`${API_BASE}/analytics/platforms`).then((r) => r.json()),
    ]).then(([tax, plat]) => {
      setTaxonomy(tax)
      setPlatforms(plat.platforms ?? [])
    })
  }, [])

  const selectedTopic = taxonomy?.topics.find((t) => t.name === filters.topic)
  const subtopics = selectedTopic?.subtopics ?? []

  function handleTopicChange(value: string) {
    onChange({ ...filters, topic: value, subtopic: '' })
  }

  function handleClear() {
    const { startDate, endDate } = getDefaultDates()
    onChange({ topic: '', subtopic: '', target: '', platform: '', startDate, endDate })
  }

  const targets = taxonomy
    ? [
        ...taxonomy.targets.parties,
        ...taxonomy.targets.leaders,
      ]
    : []

  const hasActiveFilters =
    filters.topic || filters.subtopic || filters.target || filters.platform

  return (
    <div className="col-span-12 flex flex-wrap gap-2 items-center">
      <select
        value={filters.topic}
        onChange={(e) => handleTopicChange(e.target.value)}
        className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground"
      >
        <option value="">All Topics</option>
        {taxonomy?.topics.map((t) => (
          <option key={t.name} value={t.name}>{t.label}</option>
        ))}
      </select>

      <select
        value={filters.subtopic}
        onChange={(e) => onChange({ ...filters, subtopic: e.target.value })}
        disabled={!filters.topic}
        className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground disabled:opacity-50"
      >
        <option value="">All Subtopics</option>
        {subtopics.map((s) => (
          <option key={s.name} value={s.name}>{s.label}</option>
        ))}
      </select>

      <select
        value={filters.target}
        onChange={(e) => onChange({ ...filters, target: e.target.value })}
        className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground"
      >
        <option value="">All Parties / Leaders</option>
        {targets.map((t) => (
          <option key={t.name} value={t.name}>{t.label}</option>
        ))}
      </select>

      <select
        value={filters.platform}
        onChange={(e) => onChange({ ...filters, platform: e.target.value })}
        className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground"
      >
        <option value="">All Platforms</option>
        {platforms.map((p) => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>

      <TimeRangeSelect
        startDate={filters.startDate}
        endDate={filters.endDate}
        onChange={(startDate, endDate) => onChange({ ...filters, startDate, endDate })}
      />

      {hasActiveFilters && (
        <button
          onClick={handleClear}
          className="px-2 py-1 border border-border rounded text-muted hover:text-foreground [font-size:var(--font-size-small)]"
        >
          Clear filters
        </button>
      )}
    </div>
  )
}
```

#### `TimeRangeSelect` (inline sub-component within FilterBar.tsx)

Provide preset options: Last 7 days, Last 14 days, Last 30 days, plus "Custom" (shows two date inputs). Keep it simple — implement presets only for MVP; custom range is optional.

```tsx
const PRESETS = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 14 days', days: 14 },
  { label: 'Last 30 days', days: 30 },
]

function getDefaultDates(days = 7) {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - (days - 1))
  const fmt = (d: Date) => {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }
  return { startDate: fmt(start), endDate: fmt(end) }
}

interface TimeRangeProps {
  startDate: string
  endDate: string
  onChange: (start: string, end: string) => void
}

function TimeRangeSelect({ startDate, endDate, onChange }: TimeRangeProps) {
  const activePreset = PRESETS.find(({ days }) => {
    const { startDate: ps, endDate: pe } = getDefaultDates(days)
    return ps === startDate && pe === endDate
  })

  return (
    <select
      value={activePreset?.days ?? 'custom'}
      onChange={(e) => {
        const days = parseInt(e.target.value)
        if (!isNaN(days)) {
          const { startDate: s, endDate: en } = getDefaultDates(days)
          onChange(s, en)
        }
      }}
      className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground"
    >
      {PRESETS.map(({ label, days }) => (
        <option key={days} value={days}>{label}</option>
      ))}
      {!activePreset && <option value="custom">Custom range</option>}
    </select>
  )
}
```

**Note:** Export `getDefaultDates` from FilterBar or copy into DashboardContent — do NOT duplicate logic. Best approach: define it in FilterBar.tsx and import it in DashboardContent.tsx.

### Frontend: Updated DashboardContent.tsx

Key changes — extend the existing component, do NOT rewrite from scratch:

1. Import `FilterBar`, `FilterState`, and `getDefaultDates` from `./FilterBar`
2. Replace hardcoded `getDefaultDates()` call with the same function from FilterBar
3. Add filter state:
   ```tsx
   const defaultDates = getDefaultDates(7)
   const [filters, setFilters] = useState<FilterState>({
     topic: '', subtopic: '', target: '', platform: '',
     startDate: defaultDates.startDate, endDate: defaultDates.endDate,
   })
   ```
4. Build API params including filter values:
   ```tsx
   const params = new URLSearchParams({ start_date: filters.startDate, end_date: filters.endDate })
   if (filters.topic) params.set('topic', filters.topic)
   if (filters.subtopic) params.set('subtopic', filters.subtopic)
   if (filters.target) params.set('target', filters.target)
   if (filters.platform) params.set('platform', filters.platform)
   ```
5. Update `useEffect` dependency array: `[filters]` (or all individual filter values)
6. Render `<FilterBar filters={filters} onChange={setFilters} />` before the charts
7. Update empty-state message:
   ```tsx
   const hasFilters = filters.topic || filters.subtopic || filters.target || filters.platform
   // Empty state message:
   // hasFilters → "No data for this filter combination. Try broadening your filters."
   // !hasFilters → "No data available for the selected period. Try adjusting the time range."
   ```
8. Remove the old local `getDefaultDates()` function (now imported from FilterBar)

**Critical:** `useEffect` must re-run when any filter changes. The dependency array `[filters]` works because `setFilters` replaces the object (not mutates), so React detects changes. Alternatively, use individual fields as dependencies.

### Architecture Compliance

- ✅ FilterBar is `'use client'` (uses state/effects)
- ✅ DashboardContent remains `'use client'` (owns filter + data state)
- ✅ `dashboard/page.tsx` stays a server component — no changes
- ✅ Data fetched via `NEXT_PUBLIC_API_BASE_URL` (same pattern as Story 2.2)
- ✅ All new backend params are optional — no breaking change to existing callers
- ✅ Taxonomy fetched from existing `GET /taxonomy` endpoint (no new endpoint needed for filter options)
- ✅ New `GET /analytics/platforms` for platform list (dynamic, not hardcoded)
- ✅ Tailwind v4: use `[font-size:var(--font-size-small)]` pattern (NOT `text-sm` — follow existing patterns)
- ✅ Design tokens: use `border-border`, `bg-surface`, `text-foreground`, `text-muted` (from globals.css `@theme`)
- ✅ No new pages, no new routing changes
- ✅ No `tailwind.config.js` — Tailwind v4 CSS-first

### Previous Story Learnings (Story 2.2 Review Fixes to Preserve)

The following bugs were fixed in Story 2.2 — do NOT reintroduce them:

1. **UTC date shift bug**: Do NOT use `d.toISOString().split('T')[0]` — use explicit year/month/day construction (already in current DashboardContent.tsx lines 14-20)
2. **Zero-fill calendar gaps**: The service functions zero-fill missing days — this behavior must be preserved when filter params are added
3. **error_status filter**: Use `or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))` — do NOT use `ProcessedPost.error_status.is_(False)` alone (fixes NULL exclusion bug)
4. **Date validation**: Both endpoints raise HTTP 422 if `start_date > end_date` — preserve this in both endpoints after adding filter params
5. **"Last 7 days" window**: Current uses `start = today - 6` (7 days inclusive of today) — maintain this in `getDefaultDates(7)` in FilterBar

### Design Token Reference (from globals.css)

```css
/* Colors for selects and filter UI */
--color-border: #e2e8f0        → className: border-border
--color-muted: #64748b         → className: text-muted
--color-surface: #f8fafc       → className: bg-surface (use for select backgrounds)
--color-foreground: (dark)     → className: text-foreground

/* Typography for filter controls */
--font-size-small              → [font-size:var(--font-size-small)]
--font-size-body               → [font-size:var(--font-size-body)]
```

### Taxonomy Structure (for FilterBar population)

The `GET /taxonomy` response (see `backend/app/taxonomy/schemas.py`):

```json
{
  "topics": [
    { "name": "vivienda", "label": "Vivienda", "subtopics": [{ "name": "alquiler", "label": "Alquiler" }, ...] },
    { "name": "sanidad", "label": "Sanidad", "subtopics": [...] },
    { "name": "economia", "label": "Economía", "subtopics": [...] },
    { "name": "educacion", "label": "Educación", "subtopics": [...] }
  ],
  "targets": {
    "parties": [{ "name": "pp", "label": "Partido Popular" }, { "name": "psoe", "label": "PSOE" }, ...],
    "leaders": [{ "name": "sanchez", "label": "Pedro Sánchez" }, ...]
  }
}
```

Taxonomy values stored in `processed_posts.topic` and `processed_posts.target` use the `name` field (snake_case), so filter params should be the `name` value, not the `label`.

### File Path Summary

**Backend — Modify:**
- `backend/app/api/analytics.py` — add optional filter params + `GET /analytics/platforms`
- `backend/app/analytics/schemas.py` — add `PlatformsResponse`
- `backend/app/analytics/service.py` — extend `get_volume` and `get_sentiment` with optional filter params

**Frontend — Create:**
- `frontend/components/dashboard/FilterBar.tsx`

**Frontend — Modify:**
- `frontend/components/dashboard/DashboardContent.tsx` — add filter state, render FilterBar, update API calls

**Do NOT create:**
- Any new pages
- Any new API routers or modules
- Any test files
- `tailwind.config.js`

### References

- [Source: `frontend/AGENTS.md`] — CRITICAL: read bundled Next.js docs before writing code
- [Source: `frontend/components/dashboard/DashboardContent.tsx`] — existing client component to extend
- [Source: `backend/app/api/analytics.py`] — existing analytics router to extend
- [Source: `backend/app/analytics/service.py`] — existing service functions to extend
- [Source: `backend/app/analytics/schemas.py`] — existing schemas to extend
- [Source: `backend/app/models/processed_post.py`] — ProcessedPost fields: topic, subtopic, target, sentiment, error_status
- [Source: `backend/app/models/raw_post.py`] — RawPost fields: platform, created_at
- [Source: `backend/app/api/taxonomy.py`] — existing `GET /taxonomy` endpoint (already registered at `/taxonomy`)
- [Source: `backend/config/taxonomy.yaml`] — taxonomy data (topics, subtopics, parties, leaders)
- [Source: `_bmad-output/planning-artifacts/architecture.md`] — REST-only, NEXT_PUBLIC_API_BASE_URL pattern, no caching
- [Source: `_bmad-output/implementation-artifacts/2-2-post-volume-sentiment-over-time-charts.md`] — patterns, fixes, existing component structure

## Dev Agent Record

### Agent Model Used

kimi-k2.5:cloud

### Debug Log References

- Backend analytics service updated with optional filter params (topic, subtopic, target, platform)
- Frontend FilterBar component created with cascading subtopic logic
- DashboardContent updated with filter state and dynamic API calls
- All acceptance criteria satisfied

### Completion Notes List

1. **Backend Changes**: Extended analytics endpoints with optional filter parameters that preserve backward compatibility. All new params default to None, ensuring existing callers continue to work.
2. **Frontend FilterBar**: Created with taxonomy fetching, platform fetching, and cascading subtopic logic. Time range presets (7, 14, 30 days) implemented with proper date formatting (avoiding UTC shift bug).
3. **DashboardContent Integration**: Filter state managed at DashboardContent level, passed down to FilterBar. API calls include filter params when set. Empty state distinguishes between "no data for filters" vs "no data for period".
4. **Validation**: All checks pass - lint (0 errors), TypeScript build (clean), backend tests pass.

### File List

**Modified:**
- `backend/app/api/analytics.py` — Added filter query params to /volume and /sentiment; added GET /analytics/platforms endpoint
- `backend/app/analytics/schemas.py` — Added PlatformsResponse schema
- `backend/app/analytics/service.py` — Extended get_volume and get_sentiment with optional filter WHERE clauses
- `frontend/components/dashboard/DashboardContent.tsx` — Added filter state, integrated FilterBar, dynamic API calls with filter params

**Created:**
- `frontend/components/dashboard/FilterBar.tsx` — New filter UI component with cascading subtopics, time range presets, Clear button
