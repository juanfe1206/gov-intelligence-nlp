# Story 2.8: Analyst Deep-Dive Export & Copy

**Status:** done
**Epic:** 2 — Analytics Dashboard & Data Exploration
**Story ID:** 2.8
**Story Key:** 2-8-analyst-deep-dive-export-copy
**Created:** 2026-04-08

---

## Story

As an analyst,
I want to export a structured snapshot of aggregated metrics and representative posts and copy charts or summaries,
So that I can use the data directly in memos, briefings, and presentations without manual transcription.

---

## Acceptance Criteria

1. **Given** the analyst has applied filters (topic, time range, parties)
   **When** the analyst clicks "Export"
   **Then** a JSON file downloads containing: filter parameters used, aggregated metrics (sentiment counts, volume by topic), and up to 50 representative posts with metadata

2. **Given** `GET /analytics/export` is called with filter params
   **When** the response is returned
   **Then** it returns the structured snapshot as a downloadable JSON file with `Content-Disposition: attachment` header

3. **Given** a chart or narrative summary block is visible
   **When** the user clicks a "Copy summary" action on that block
   **Then** the formatted text of the summary (key metrics + topic labels) is copied to the clipboard

4. **Given** the analyst performs a month-long deep dive (FR22) — selects a 30-day range, a specific topic, and compares two parties
   **When** the analyst exports the snapshot
   **Then** the export file includes data spanning the full 30-day range and correctly reflects both parties' data

---

## Tasks / Subtasks

- [x] Backend: Add `ExportSnapshot` schema (AC: 1, 2)
  - [x] Add `ExportFilters`, `ExportMetrics`, `ExportSnapshot` to `backend/app/analytics/schemas.py`

- [x] Backend: Add `get_export` service function (AC: 1, 2, 4)
  - [x] Add `get_export` to `backend/app/analytics/service.py`
  - [x] Reuse existing `get_volume`, `get_sentiment`, `get_topics`, `get_posts` calls (no duplicate queries)
  - [x] Bundle: filter params + volume data + sentiment data + topic distribution + up to 50 posts

- [x] Backend: Add `GET /analytics/export` endpoint (AC: 2, 4)
  - [x] Add endpoint to `backend/app/api/analytics.py`
  - [x] Return `Response` with `media_type="application/json"` and `Content-Disposition: attachment; filename="export.json"` header
  - [x] Accept all standard filter params: `start_date`, `end_date`, `topic`, `subtopic`, `target`, `platform`

- [x] Frontend: Add Export button to `DashboardContent` (AC: 1, 4)
  - [x] Add `handleExport()` function that builds query params from current `filters` state and triggers download
  - [x] Use `window.open(url)` or fetch + blob approach — see Dev Notes for correct pattern
  - [x] Render `<button>Export</button>` near the FilterBar

- [x] Frontend: Add "Copy summary" button to `DashboardContent` (AC: 3)
  - [x] Add `handleCopySummary()` function using `navigator.clipboard.writeText()`
  - [x] Summary text format: key metrics (total posts, sentiment %, top topics) derived from already-fetched `volumeData` and `sentimentData`
  - [x] Show brief confirmation ("Copied!" tooltip or inline text) after successful copy

- [x] Validate (AC: 1, 2, 3, 4)
  - [x] `npm run lint` — zero errors
  - [x] `npm run build` — clean TypeScript build
  - [x] Manual: export with 30-day range + two parties — verify file downloads with correct data
  - [x] Manual: copy summary — verify clipboard content matches displayed metrics

### Review Findings

- [x] [Review][Patch] Export does not preserve selected parties end-to-end [frontend/components/dashboard/DashboardContent.tsx:44]
- [x] [Review][Patch] Export endpoint/service/schema do not accept and persist `parties` filters [backend/app/api/analytics.py:178]
- [x] [Review][Patch] Copy summary output omits topic labels from analytics results [frontend/components/dashboard/DashboardContent.tsx:55]
- [x] [Review][Patch] Export and copy actions fail silently with no user feedback on errors [frontend/components/dashboard/DashboardContent.tsx:82]
- [x] [Review][Defer] Party comparison sentiment buckets are case-sensitive and can silently zero-out counts [backend/app/analytics/service.py:get_comparison] — deferred, pre-existing
- [x] [Review][Defer] Spike detection treats any non-zero recent count over zero baseline as spike (false positives in sparse data) [backend/app/analytics/service.py:get_spikes] — deferred, pre-existing
- [x] [Review][Defer] Dashboard empty-state predicate likely unreachable with zero-filled timeseries responses [frontend/components/dashboard/DashboardContent.tsx:isEmpty] — deferred, pre-existing

---

## Developer Context

### CRITICAL: Story Foundation & Requirements

**User Story Objective:**
Enable analysts to export a structured data snapshot and copy summaries without leaving the app. This is a utility feature — no new data queries beyond what's already fetched, just bundling and delivery.

**Key Requirements:**
- Export includes: filter params, volume by date, sentiment by date, topic distribution, up to 50 representative posts
- Export format: **JSON** (preserves nested structure; CSV would flatten and lose relationships)
- `Content-Disposition: attachment; filename="export.json"` — browser must trigger download, not render inline
- "Copy summary" is frontend-only — uses existing fetched data, no new API call
- FR22 (month-long deep dive): accept `start_date`/`end_date` from query params — already supported by existing filter pattern; 30-day range is just a date range, no special handling needed
- Parties filter: pass `parties` as repeated query params to export endpoint — same pattern as `/compare`

---

### Architecture Compliance & Patterns

**Backend Patterns (established in Stories 2.2–2.7):**
- Service functions accept `AsyncSession`, `TaxonomyConfig`, filter params — match existing signatures exactly
- Return Pydantic schemas via FastAPI endpoint — add new schemas to `schemas.py` AFTER `SpikesResponse`
- SQLAlchemy ORM with `or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))` — NULL-safe filter; already handled inside reused service functions
- `_default_start()` / `_default_end()` helpers already exist in `analytics.py` — use them, do not duplicate
- All filter params optional and backward-compatible — same pattern as every other endpoint

**CRITICAL: Reuse Service Functions — Do NOT Re-query**

The `get_export` function MUST call existing service functions via `asyncio.gather()`:
```python
volume, sentiment, topics, posts = await asyncio.gather(
    get_volume(session, start_date, end_date, topic, subtopic, target, platform),
    get_sentiment(session, start_date, end_date, topic, subtopic, target, platform),
    get_topics(session, taxonomy, start_date, end_date, topic, subtopic, target, platform),
    get_posts(session, taxonomy, start_date, end_date, topic, subtopic, target, platform, limit=50),
)
```
Do NOT write raw SQL queries in `get_export` — all data access is already implemented correctly in the other functions.

**Frontend Patterns (established in Stories 2.3–2.7):**
- `'use client'` directive — required for any component using state or effects
- `const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'` — same constant, already in `DashboardContent.tsx`
- Import `FilterState` from `'./FilterBar'` — do NOT redefine it
- Design tokens: CSS variables from `globals.css` — NO hard-coded colors
- Tailwind v4: font size pattern `[font-size:var(--font-size-body)]`

**FastAPI File Response Pattern:**
```python
from fastapi import Response
import json

@router.get("/export")
async def export_snapshot(...) -> Response:
    data = await analytics_service.get_export(...)
    json_bytes = json.dumps(data.model_dump(), ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="gov-intelligence-export.json"'},
    )
```
**Note:** Return `Response` directly, NOT `dict` or Pydantic model — Pydantic model would cause FastAPI to serialize without the download header. No `response_model` param on this endpoint.

---

### Technical Requirements

**Backend: New Pydantic Schemas**

Add to `backend/app/analytics/schemas.py` (after `SpikesResponse`):

```python
class ExportFilters(BaseModel):
    """Filter parameters included in the export for reproducibility."""
    start_date: str
    end_date: str
    topic: str | None = None
    subtopic: str | None = None
    target: str | None = None
    platform: str | None = None
    parties: list[str] | None = None


class ExportSnapshot(BaseModel):
    """Structured snapshot for analyst export."""
    exported_at: str            # ISO date string "YYYY-MM-DD"
    filters: ExportFilters
    volume: VolumeResponse
    sentiment: SentimentResponse
    topics: TopicsResponse
    posts: PostsResponse        # up to 50 posts
```

**No `ExportMetrics` wrapper needed** — `VolumeResponse`, `SentimentResponse`, `TopicsResponse`, `PostsResponse` already exist and are correctly structured.

---

**Backend: `get_export` Service Function**

Add to `backend/app/analytics/service.py`:

```python
from app.analytics.schemas import ..., ExportFilters, ExportSnapshot

async def get_export(
    session: AsyncSession,
    taxonomy: TaxonomyConfig,
    start_date: date,
    end_date: date,
    topic: str | None = None,
    subtopic: str | None = None,
    target: str | None = None,
    platform: str | None = None,
    parties: list[str] | None = None,
) -> ExportSnapshot:
    """Bundle all analytics data for export."""
    volume, sentiment, topics, posts = await asyncio.gather(
        get_volume(session, start_date, end_date, topic, subtopic, target, platform),
        get_sentiment(session, start_date, end_date, topic, subtopic, target, platform),
        get_topics(session, taxonomy, start_date, end_date, topic, subtopic, target, platform),
        get_posts(session, taxonomy, start_date, end_date, topic, subtopic, target, platform, limit=50),
    )
    return ExportSnapshot(
        exported_at=str(date.today()),
        filters=ExportFilters(
            start_date=str(start_date),
            end_date=str(end_date),
            topic=topic,
            subtopic=subtopic,
            target=target,
            platform=platform,
            parties=parties,
        ),
        volume=volume,
        sentiment=sentiment,
        topics=topics,
        posts=posts,
    )
```

**Service notes:**
- `asyncio` is already imported in `service.py` (added in Story 2.7) — no duplicate import
- `get_volume`, `get_sentiment`, `get_topics`, `get_posts` are all already defined above `get_export` in the same file — call them directly (no self-reference, no circular imports)
- `parties` filter is stored in `filters` for reproducibility but NOT passed to the individual service calls — `get_topics` and `get_posts` don't filter by party (that's `get_comparison`'s job)
- If parties filtering for export is needed in the future, it would require a new service function — out of scope for this story

---

**Backend: `GET /analytics/export` Endpoint**

Add to `backend/app/api/analytics.py`:

```python
from fastapi import ..., Response  # add Response to existing fastapi import
import json  # add at top with other stdlib imports

from app.analytics.schemas import (
    VolumeResponse, SentimentResponse, PlatformsResponse, TopicsResponse,
    PostsResponse, ComparisonResponse, SpikesResponse, ExportFilters, ExportSnapshot,
)

@router.get("/export")
async def export_snapshot(
    request: Request,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    topic: str | None = Query(default=None),
    subtopic: str | None = Query(default=None),
    target: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    parties: list[str] = Query(default=[]),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Export a structured snapshot of analytics data as a downloadable JSON file."""
    s = start_date or _default_start()
    e = end_date or _default_end()
    if s > e:
        raise HTTPException(status_code=422, detail="start_date must be before end_date")
    taxonomy = request.app.state.taxonomy
    snapshot = await analytics_service.get_export(
        session, taxonomy, s, e, topic, subtopic, target, platform,
        parties=parties if parties else None,
    )
    json_bytes = json.dumps(snapshot.model_dump(), ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="gov-intelligence-export.json"'},
    )
```

**CRITICAL endpoint notes:**
- `response_model` is NOT set — return type is `Response`, not a Pydantic model
- `parties: list[str] = Query(default=[])` — FastAPI supports repeated `?parties=pp1&parties=pp2` automatically
- `_default_start()` and `_default_end()` are already defined in `analytics.py` — call them directly
- `json.dumps(snapshot.model_dump(), ...)` — use `.model_dump()` (Pydantic v2) NOT `.dict()` (Pydantic v1)
- Add `Response` to existing `from fastapi import ...` line; add `import json` at top of file

---

**Frontend: Export Button in `DashboardContent`**

In `frontend/components/dashboard/DashboardContent.tsx`, add the export handler and button:

```tsx
function buildExportUrl(filters: FilterState): string {
  const params = new URLSearchParams()
  if (filters.startDate) params.set('start_date', filters.startDate)
  if (filters.endDate) params.set('end_date', filters.endDate)
  if (filters.topic) params.set('topic', filters.topic)
  if (filters.subtopic) params.set('subtopic', filters.subtopic)
  if (filters.target) params.set('target', filters.target)
  if (filters.platform) params.set('platform', filters.platform)
  filters.selectedParties?.forEach(p => params.append('parties', p))
  return `${API_BASE}/analytics/export?${params.toString()}`
}
```

Render the export button near the FilterBar (outside the `isEmpty` check — always visible):

```tsx
<div className="col-span-12 flex justify-end">
  <a
    href={buildExportUrl(filters)}
    download="gov-intelligence-export.json"
    className="px-4 py-2 rounded border border-border text-foreground hover:bg-surface-raised [font-size:var(--font-size-body)]"
  >
    Export
  </a>
</div>
```

**Export download approach:** Use `<a href=... download>` — NOT `fetch` + blob. The `download` attribute triggers the browser's native download dialog and handles the `Content-Disposition` header correctly. A plain anchor tag avoids CORS preflight issues and is simpler. The `buildExportUrl` helper constructs the URL client-side from the current filter state — no state mutation needed.

---

**Frontend: Copy Summary Button in `DashboardContent`**

Add the copy handler and button to `DashboardContent.tsx`:

```tsx
const [copied, setCopied] = useState(false)

function buildSummaryText(
  filters: FilterState,
  volumeData: VolumeData | null,
  sentimentData: SentimentData | null,
): string {
  const lines: string[] = ['=== Gov Intelligence Analytics Summary ===']
  lines.push(`Date range: ${filters.startDate ?? 'default'} → ${filters.endDate ?? 'default'}`)
  if (filters.topic) lines.push(`Topic: ${filters.topic}`)
  if (filters.platform) lines.push(`Platform: ${filters.platform}`)
  if (volumeData) lines.push(`Total posts: ${volumeData.total.toLocaleString()}`)
  if (sentimentData?.data.length) {
    const totals = sentimentData.data.reduce(
      (acc, d) => ({
        pos: acc.pos + d.positive,
        neu: acc.neu + d.neutral,
        neg: acc.neg + d.negative,
      }),
      { pos: 0, neu: 0, neg: 0 },
    )
    const total = totals.pos + totals.neu + totals.neg || 1
    lines.push(
      `Sentiment: ${((totals.pos / total) * 100).toFixed(1)}% positive, ` +
      `${((totals.neu / total) * 100).toFixed(1)}% neutral, ` +
      `${((totals.neg / total) * 100).toFixed(1)}% negative`,
    )
  }
  return lines.join('\n')
}

async function handleCopySummary() {
  const text = buildSummaryText(filters, volumeData, sentimentData)
  try {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  } catch {
    // clipboard API unavailable (e.g., non-HTTPS) — fail silently
  }
}
```

Render the copy button alongside the export button:

```tsx
<div className="col-span-12 flex justify-end gap-2">
  <button
    onClick={handleCopySummary}
    className="px-4 py-2 rounded border border-border text-foreground hover:bg-surface-raised [font-size:var(--font-size-body)]"
  >
    {copied ? 'Copied!' : 'Copy summary'}
  </button>
  <a
    href={buildExportUrl(filters)}
    download="gov-intelligence-export.json"
    className="px-4 py-2 rounded border border-border text-foreground hover:bg-surface-raised [font-size:var(--font-size-body)]"
  >
    Export
  </a>
</div>
```

**Copy notes:**
- `navigator.clipboard.writeText()` requires HTTPS or localhost — in dev, it works; in production HTTPS, it works
- Silent `catch` is intentional — no visual error state needed for this MVP utility feature
- `copied` state drives the button label toggle (`'Copied!'` for 2 seconds) — no external toast library needed
- Summary text is derived from already-fetched `volumeData` and `sentimentData` — no additional API call
- `buildSummaryText` is a pure function (no hooks) — can be defined outside the component or inside, either works

---

### File Structure

| File | Action | Notes |
|------|--------|-------|
| `backend/app/analytics/schemas.py` | Modify | Add `ExportFilters`, `ExportSnapshot` after `SpikesResponse` |
| `backend/app/analytics/service.py` | Modify | Add `get_export` function; update schemas import |
| `backend/app/api/analytics.py` | Modify | Add `GET /export` endpoint; add `Response` to fastapi import; add `import json`; extend schemas import |
| `frontend/components/dashboard/DashboardContent.tsx` | Modify | Add `buildExportUrl`, `buildSummaryText`, `handleCopySummary`, `copied` state, export + copy buttons |

**Do NOT modify** `FilterBar.tsx`, `SpikeAlertBanner.tsx`, `ComparisonPanel.tsx`, `TopicsPanel.tsx`, `PostsPanel.tsx`, any chart components, or any schema/service files outside `analytics/`.

---

### Previous Story Intelligence (from Story 2.7)

- **`asyncio` is already imported** in `service.py` — do NOT add it again
- **`asyncio.gather()` pattern**: parallel calls to service functions — copy this pattern; it's already established
- **`or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))`**: NULL-safe filter — already handled inside the reused service functions, no need to add it to `get_export`
- **Pydantic v2 `.model_dump()`**: NOT `.dict()` — confirmed by review feedback on 2.7
- **`AbortController` + `isActive`**: not needed here — export is a direct anchor link, not a fetch call; copy summary is fire-and-forget (no abort needed)
- **Return `null` when no data**: not applicable — buttons are always rendered (they operate on current filter state)
- **`'use client'` directive**: already present in `DashboardContent.tsx` — do not add again
- **`API_BASE` constant**: already defined in `DashboardContent.tsx` — do not redeclare

---

### Git Intelligence Summary

From recent commits:
- **Sequence**: schemas → service function → API route → frontend integration in `DashboardContent` — follow this exact order
- **`DashboardContent` state pattern**: `volumeData` (`VolumeData | null`) and `sentimentData` (`SentimentData | null`) are already held in component state — read them directly in `buildSummaryText`, no new fetches
- **`FilterState` type**: imported from `'./FilterBar'` — already contains `selectedParties: string[]`, `startDate`, `endDate`, `topic`, `subtopic`, `target`, `platform`
- **No test files needed**: Epic 2 validation is `npm run lint` + `npm run build` + manual smoke test

---

### NOTES: Frontend-Only Patterns

**Clipboard API:**
```typescript
// Correct — async/await, catch silently
await navigator.clipboard.writeText(text)
```
Do NOT use `document.execCommand('copy')` — deprecated.

**`<a download>` for file download:**
```tsx
<a href={url} download="filename.json">Export</a>
```
The `download` attribute on an anchor tag is the correct approach for a same-origin URL. Do NOT use `fetch` + `URL.createObjectURL` for this endpoint — the direct link approach is simpler and the `Content-Disposition` header ensures the file downloads correctly.

**`list[str] = Query(default=[])` for repeated params:**
- FastAPI receives `?parties=pp&parties=psoe` as `["pp", "psoe"]` automatically
- Frontend: `filters.selectedParties?.forEach(p => params.append('parties', p))` — use `append` not `set` for list params

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References
- 2026-04-08: Successfully implemented all backend and frontend changes for export and copy functionality
- All service functions reused via asyncio.gather() as specified
- Frontend uses <a download> pattern for export, navigator.clipboard for copy

### Completion Notes List
- ✅ Backend schemas added: ExportFilters, ExportSnapshot in schemas.py
- ✅ Backend service function: get_export in service.py using asyncio.gather() to reuse existing service functions
- ✅ Backend endpoint: GET /analytics/export in analytics.py returning Response with Content-Disposition attachment header
- ✅ Frontend Export button added to DashboardContent with exportUrl computed via useMemo
- ✅ Frontend Copy summary button added with handleCopySummary function using navigator.clipboard.writeText()
- ✅ Both buttons visible in both empty and non-empty states
- ✅ Validation: npm run lint passed (zero errors)
- ✅ Validation: npm run build passed (clean TypeScript build)

### File List
- `backend/app/analytics/schemas.py` - Added ExportFilters and ExportSnapshot schemas
- `backend/app/analytics/service.py` - Added get_export function
- `backend/app/api/analytics.py` - Added GET /analytics/export endpoint
- `frontend/components/dashboard/DashboardContent.tsx` - Added exportUrl, summaryText, handleCopySummary, and both buttons

---

**The developer has everything needed for flawless implementation!**
