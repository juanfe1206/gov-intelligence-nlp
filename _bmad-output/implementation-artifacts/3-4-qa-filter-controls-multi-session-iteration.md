# Story 3.4: Q&A Filter Controls & Multi-Session Iteration

**Status:** done
**Epic:** 3 — LLM-Powered Q&A Intelligence Interface
**Story ID:** 3.4
**Story Key:** 3-4-qa-filter-controls-multi-session-iteration
**Created:** 2026-04-08

---

## Story

As a campaign, communications, or analyst user,
I want to specify optional filters (topic, time range, party, platform) alongside my question,
So that I can scope my question to the exact slice of data I care about.

---

## Acceptance Criteria

1. **Given** the Q&A input is visible
   **When** the user expands the filter panel
   **Then** they can select topic, subtopic, party/target, time range, and platform — matching the same filter options available on the dashboard

2. **Given** filters are set and a question is submitted
   **When** the `POST /qa` request is made
   **Then** all selected filter values are passed as parameters and the retrieval is scoped accordingly

3. **Given** the user submits a question with no filters applied
   **When** the Q&A processes the request
   **Then** retrieval runs across the full dataset with no filter scoping — all filters are optional

4. **Given** an active filter selection
   **When** the user clears one or all filters
   **Then** the filter state resets to "no filter" and the next question submission uses the cleared state

---

## Scope

**IN SCOPE:**
- Collapsible filter panel in `QAContent.tsx` (expand/collapse toggle button)
- Filter controls: topic, subtopic (dependent on topic), party/target, time range (preset + custom), platform
- Pass selected filters in `POST /qa` body as `filters` object
- Update scope label ("Based on X posts") to reflect active time range when set
- Clear all filters button (visible when any filter is active)
- Backend: add `subtopic` field to `QAFilters` schema and `retrieve_and_aggregate` service

**OUT OF SCOPE:**
- Multi-session question history — explicitly not required (FR18)
- URL param pre-filling the question from dashboard tiles — Story 3.5
- Narrative cluster cards — Story 3.5

---

## Tasks / Subtasks

### Backend Tasks

- [x] Add `subtopic` to `QAFilters` schema (AC: 1, 2)
  - [x] Edit `backend/app/qa/schemas.py`: add `subtopic: str | None = None` to `QAFilters`

- [x] Add subtopic filtering to service (AC: 2)
  - [x] Edit `backend/app/qa/service.py`: add `subtopic: str | None = None` param to `retrieve_and_aggregate`
  - [x] Add `if subtopic is not None: sql_filters.append(ProcessedPost.subtopic == subtopic)` to the SQL filter block (after the `topic` filter block)
  - [x] Update `filters_applied = QAFilters(...)` constructor to include `subtopic=subtopic`

- [x] Wire subtopic through the router (AC: 2)
  - [x] Edit `backend/app/api/qa.py`: pass `subtopic=f.subtopic if f else None` to `qa_service.retrieve_and_aggregate`

### Frontend Tasks

- [x] Add filter state to `QAContent.tsx` (AC: 1, 3, 4)
  - [x] Add `filterOpen` boolean state (default `false`) for panel visibility
  - [x] Add `qaFilters` state typed as `QAFilterState` (see interface below)
  - [x] Add helper to compute `hasActiveFilters` (any filter non-empty / non-default)

- [x] Create `QAFilterState` interface in `QAContent.tsx` (AC: 1)
  ```typescript
  interface QAFilterState {
    topic: string       // machine name or ''
    subtopic: string    // machine name or '' (only valid when topic is set)
    party: string       // machine name or ''
    platform: string    // or ''
    startDate: string   // "YYYY-MM-DD" or ''
    endDate: string     // "YYYY-MM-DD" or ''
  }
  ```
  Default: all empty strings.

- [x] Fetch taxonomy and platforms in `QAContent.tsx` (AC: 1)
  - [x] Add `useEffect` to fetch `${API_BASE}/taxonomy` and `${API_BASE}/analytics/platforms` in parallel (same pattern as `FilterBar.tsx:92-104`)
  - [x] Store in local state: `taxonomy: Taxonomy | null` and `platforms: string[]`
  - [x] On fetch error, silently fail — filter options will be empty (same as FilterBar)

- [x] Add `QAFilterPanel` as inline function component inside `QAContent.tsx` (AC: 1, 4)
  - [x] Render only when `filterOpen === true`
  - [x] Topic `<select>` — options from taxonomy (same structure as FilterBar, minus party comparison)
  - [x] Subtopic `<select>` — disabled when no topic selected; options derived from selected topic's subtopics
  - [x] Party/Target `<select>` — options from `[...taxonomy.targets.parties, ...taxonomy.targets.leaders]` (same as FilterBar `targets` computation)
  - [x] Platform `<select>` — options from `platforms` array
  - [x] Time range `<select>` — preset options: "All time" (empty), "Last 7 days", "Last 14 days", "Last 30 days" using `getDefaultDates` from `FilterBar.tsx`
  - [x] Clear filters button — visible when `hasActiveFilters`; resets all to defaults

- [x] Add filter toggle button above filter panel (AC: 1)
  - [x] Render "Filters ▼" / "Filters ▲" button below the preset suggestion chips in the question input card
  - [x] Toggle `filterOpen` on click

- [x] Update `handleSubmit` to include filters in request body (AC: 2, 3)
  - [x] Build `filters` object only when any filter is active (send `undefined`/omit when no filters set — same as 3.3 behavior)
  - [x] Map frontend state to backend schema:
    ```typescript
    const filters = hasActiveFilters ? {
      topic: qaFilters.topic || undefined,
      subtopic: qaFilters.subtopic || undefined,
      party: qaFilters.party || undefined,
      platform: qaFilters.platform || undefined,
      start_date: qaFilters.startDate || undefined,
      end_date: qaFilters.endDate || undefined,
    } : undefined
    ```
  - [x] Pass `filters` in the POST body: `{ question: question.trim(), ...(filters && { filters }) }`

- [x] Update scope label to reflect time range (AC: 2)
  - [x] When `result.filters_applied.start_date` or `result.filters_applied.end_date` is non-null, append the date range to scope label: "Based on {N} posts · {start_date} to {end_date}"

- [x] Validate (AC: 1, 2, 3, 4)
  - [x] Filter panel hidden by default; "Filters ▼" button visible
  - [x] Click toggle → filter panel expands with all controls
  - [x] Select a topic → subtopic dropdown enables; select another topic → subtopic resets
  - [x] Select party, platform, time range independently
  - [x] Submit question with filters → `POST /qa` body includes filters; retrieval scoped accordingly
  - [x] Submit with no filters → `POST /qa` body has no `filters` key; full dataset used
  - [x] Click "Clear filters" → all selects reset; next submit uses no filters
  - [x] Scope label shows date range when time filter applied

---

## Developer Context

### CRITICAL: Do NOT reuse `FilterBar.tsx` from dashboard

`components/dashboard/FilterBar.tsx` is NOT suitable for Q&A filters:
- It has party **comparison multi-select** (for `ComparisonPanel`) — not relevant to Q&A
- It uses `FilterState` with `selectedParties: string[]` — a different interface
- It manages its own taxonomy/platform fetch — duplicating this in `QAContent.tsx` is acceptable and keeps Q&A self-contained

Build filter controls **inline within `QAContent.tsx`** (as a local component `QAFilterPanel`). This keeps the file self-contained and avoids entangling Q&A state with the dashboard's filter abstraction.

**However**: Do reuse these utilities from `FilterBar.tsx`:
- `getDefaultDates(days: number)` — IMPORT this function from `components/dashboard/FilterBar.tsx` using `import { getDefaultDates } from '@/components/dashboard/FilterBar'`
- The `Taxonomy` interface and `FilterState` type are NOT needed — define a simpler `QAFilterState` interface inline

---

### Backend: Files to Change

| File | Change |
|------|--------|
| `backend/app/qa/schemas.py` | Add `subtopic: str \| None = None` to `QAFilters` |
| `backend/app/qa/service.py` | Add `subtopic` param + SQL filter |
| `backend/app/api/qa.py` | Pass `subtopic` to service call |

**`schemas.py` exact change** — add one line to `QAFilters`:
```python
class QAFilters(BaseModel):
    topic: str | None = None
    subtopic: str | None = None   # ADD THIS LINE
    party: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    platform: str | None = None
```

**`service.py` exact changes:**
1. Add `subtopic: str | None = None` to `retrieve_and_aggregate` signature (after `topic` param)
2. Update `QAFilters(...)` constructor: add `subtopic=subtopic`
3. Add after the `if topic` block:
   ```python
   if subtopic is not None:
       sql_filters.append(ProcessedPost.subtopic == subtopic)
   ```
4. Verify `ProcessedPost.subtopic` column exists (it does — the service already reads `pp.subtopic` in Step 5)

**`api/qa.py` exact change** — add one line to the `retrieve_and_aggregate` call:
```python
qa_result = await qa_service.retrieve_and_aggregate(
    session=session,
    taxonomy=taxonomy,
    question=body.question.strip(),
    topic=f.topic if f else None,
    subtopic=f.subtopic if f else None,    # ADD THIS LINE
    party=f.party if f else None,
    start_date=f.start_date if f else None,
    end_date=f.end_date if f else None,
    platform=f.platform if f else None,
    top_n=top_n,
)
```

---

### Frontend: Taxonomy & Platforms Fetch

`FilterBar.tsx` fetches both in a single `Promise.all`. Mirror this pattern in `QAContent.tsx`:

```typescript
// Add these state vars to QAContent component:
const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null)
const [platforms, setPlatforms] = useState<string[]>([])

// Add this useEffect (runs once on mount):
useEffect(() => {
  Promise.all([
    fetch(`${API_BASE}/taxonomy`).then((r) => r.json()),
    fetch(`${API_BASE}/analytics/platforms`).then((r) => r.json()),
  ])
    .then(([tax, plat]) => {
      setTaxonomy(tax)
      setPlatforms(plat.platforms ?? [])
    })
    .catch(() => {
      // Silently fail — filters will show empty options
    })
}, [])
```

Use the same `Taxonomy` / `Topic` interfaces as `FilterBar.tsx`. Either import them (they are exported via `FilterState` from FilterBar) or re-declare inline — simpler to re-declare inline since QAContent doesn't need `FilterState`.

---

### Frontend: QAFilterState Interface

```typescript
interface QAFilterState {
  topic: string       // '' = no filter
  subtopic: string    // '' = no filter; only meaningful when topic is set
  party: string       // '' = no filter; maps to backend QAFilters.party
  platform: string    // '' = no filter
  startDate: string   // "YYYY-MM-DD" or '' = no filter
  endDate: string     // "YYYY-MM-DD" or '' = no filter
}

const DEFAULT_FILTERS: QAFilterState = {
  topic: '', subtopic: '', party: '', platform: '', startDate: '', endDate: '',
}
```

`hasActiveFilters` check:
```typescript
const hasActiveFilters =
  qaFilters.topic !== '' ||
  qaFilters.subtopic !== '' ||
  qaFilters.party !== '' ||
  qaFilters.platform !== '' ||
  qaFilters.startDate !== '' ||
  qaFilters.endDate !== ''
```

---

### Frontend: Filter Panel Styling

Use the same Tailwind tokens as the rest of `QAContent.tsx`:

```tsx
// Toggle button — placed below preset chips in the question input card
<button
  type="button"
  onClick={() => setFilterOpen((o) => !o)}
  className="self-start text-muted hover:text-foreground [font-size:var(--font-size-small)] flex items-center gap-1"
>
  Filters {filterOpen ? '▲' : '▼'}
</button>

// Filter panel (rendered when filterOpen)
<div className="flex flex-wrap gap-2 items-center pt-2 border-t border-border">
  {/* selects go here */}
  {hasActiveFilters && (
    <button
      type="button"
      onClick={() => { setQAFilters(DEFAULT_FILTERS) }}
      className="px-2 py-1 border border-border rounded text-muted hover:text-foreground [font-size:var(--font-size-small)]"
    >
      Clear filters
    </button>
  )}
</div>
```

All `<select>` elements use the same class as `FilterBar.tsx`:
```
border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground
```
Disabled state for subtopic: `disabled:opacity-50`

---

### Frontend: Time Range Options

The "All time" option means no `start_date`/`end_date` is sent. Use presets from FilterBar's `PRESETS` array pattern:

```tsx
const QA_TIME_PRESETS = [
  { label: 'All time', days: 0 },
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 14 days', days: 14 },
  { label: 'Last 30 days', days: 30 },
]

// In the select:
<select
  value={selectedPresetDays}
  onChange={(e) => {
    const days = parseInt(e.target.value)
    if (days === 0) {
      setQAFilters((f) => ({ ...f, startDate: '', endDate: '' }))
    } else {
      const { startDate, endDate } = getDefaultDates(days)
      setQAFilters((f) => ({ ...f, startDate, endDate }))
    }
  }}
  className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground"
>
  {QA_TIME_PRESETS.map(({ label, days }) => (
    <option key={days} value={days}>{label}</option>
  ))}
</select>
```

`selectedPresetDays` is computed from `qaFilters.startDate`/`endDate` by matching against presets (same logic as `TimeRangeSelect` in FilterBar). Default is `0` (All time).

---

### Frontend: Scope Label Update

When time filters are applied, update the scope label at the bottom of the answer area:

```tsx
const scopeLabel = (() => {
  const total = result.metrics.total_retrieved.toLocaleString()
  const sd = result.filters_applied.start_date
  const ed = result.filters_applied.end_date
  if (sd && ed) return `Based on ${total} posts · ${sd} to ${ed}`
  if (sd) return `Based on ${total} posts · from ${sd}`
  if (ed) return `Based on ${total} posts · up to ${ed}`
  return `Based on ${total} posts`
})()
```

---

### Frontend: handleSubmit Update

Full request body construction with filters:

```typescript
const handleSubmit = useCallback(async () => {
  if (!question.trim()) return
  // ... abort + setup as before ...

  const activeFilters = hasActiveFilters ? {
    topic: qaFilters.topic || undefined,
    subtopic: qaFilters.subtopic || undefined,
    party: qaFilters.party || undefined,
    platform: qaFilters.platform || undefined,
    start_date: qaFilters.startDate || undefined,
    end_date: qaFilters.endDate || undefined,
  } : undefined

  const body: Record<string, unknown> = { question: question.trim() }
  if (activeFilters) body.filters = activeFilters

  const response = await fetch(`${API_BASE}/qa`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
  // ... rest of error handling as before ...
}, [question, qaFilters, hasActiveFilters])
```

Note: `hasActiveFilters` must be a stable value (computed at render, not inside the callback) — derive it as a `const` at the component body level, not inside `handleSubmit`.

---

### Existing API: No Backend Changes to `/taxonomy` or `/analytics/platforms`

Both endpoints are already implemented and working:
- `GET /taxonomy` → returns `{ topics: [...], targets: { parties: [...], leaders: [...] } }`
- `GET /analytics/platforms` → returns `{ platforms: [...] }`

No changes needed to these endpoints.

---

### Previous Story Intelligence (from Stories 3.1–3.3)

- **No test files** were added for any Epic 3 story — manual smoke test only. Do not create test files.
- **No shared API client** in the frontend — each component calls `fetch()` directly. `QAContent.tsx` should continue this pattern.
- **AbortController pattern** is already in `QAContent.tsx` (lines 148-184) — keep it intact; only modify the POST body construction.
- **`handleSubmit` uses `useCallback`** with `[question]` dep array. With this story, add `qaFilters` and `hasActiveFilters` to the dep array.
- **`QAResponse.filters_applied`** is already in the response type in `QAContent.tsx` (line 42-48) — use it for the scope label update.
- **Deferred from 3.3 review**: "Frontend never sends `filters` or `top_n` in POST body — Story 3.4 scope" — this story closes that deferred item.

---

### Git Intelligence

From recent commits:
- All new frontend components go in `frontend/components/[feature]/`; inline sub-components (like `EvidencePostCard`, `MetricsStrip` in 3.3) are acceptable within one file
- `'use client'` directive at top of client components
- `page.tsx` files remain thin server-component shells (no changes needed to `qa/page.tsx` this story)
- Backend schema changes are minimal Pydantic field additions — no Alembic migrations needed (no DB schema change)

---

### Testing / Validation

No automated tests. Validate manually:

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to `http://localhost:3000/qa`
4. **AC1:** "Filters ▼" button visible below preset chips; click → filter panel expands with topic, subtopic, party, platform, time range selects
5. **AC1:** Select topic → subtopic dropdown enables with relevant options; change topic → subtopic resets
6. **AC1:** Select party, platform, time preset independently
7. **AC2:** Select "Last 7 days" + a topic, submit question → check browser Network tab: POST body contains `filters` with `topic` and `start_date`/`end_date`; response `filters_applied` reflects them; scope label shows date range
8. **AC3:** Clear all filters, submit → POST body has no `filters` key; full dataset used
9. **AC4:** Set multiple filters, click "Clear filters" → all selects reset; "Clear filters" button disappears; next submit uses no filters
10. **Subtopic filter:** Select topic "economia", select a subtopic, submit question → POST body includes `filters.subtopic`; verify backend log shows subtopic filter applied

---

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- Implemented collapsible filter panel in QAContent.tsx with all required controls
- Added subtopic field to QAFilters schema and wired through backend
- Updated handleSubmit to conditionally include filters in POST body
- Updated scope label to display date range when time filters are active

### File List

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/app/qa/schemas.py` | Modify | Add `subtopic` field to `QAFilters` |
| `backend/app/qa/service.py` | Modify | Add `subtopic` param + SQL filter clause |
| `backend/app/api/qa.py` | Modify | Pass `subtopic` to service call |
| `frontend/components/qa/QAContent.tsx` | Modify | Add filter state, panel, taxonomy/platforms fetch, update POST body and scope label |

### Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-04-08 | Added filter controls to Q&A interface | Story 3.4 implementation complete |
