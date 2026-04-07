# Story 2.7: Spike Alert Detection & Banner

**Status:** done
**Epic:** 2 — Analytics Dashboard & Data Exploration
**Story ID:** 2.7
**Story Key:** 2-7-spike-alert-detection-banner
**Created:** 2026-04-08

---

## Story

As a communications or rapid-response user,
I want the dashboard to surface sudden spikes in post volume or negative sentiment as a prominent alert,
So that I can immediately see when something unusual is happening without having to spot it in a chart myself.

---

## Acceptance Criteria

1. **Given** processed posts show a significant volume or sentiment spike within the last 2–24 hours (configurable threshold)
   **When** the dashboard loads
   **Then** a Spike Alert Banner appears at the top of the main content area showing: the topic/entity spiking, the nature of the spike (volume or sentiment), and a link to investigate

2. **Given** `GET /analytics/spikes` is called
   **When** the response is returned
   **Then** it returns any detected spikes with: topic label, spike type, magnitude indicator, and the time window of the spike

3. **Given** no spikes are detected
   **When** the dashboard loads
   **Then** the Spike Alert Banner area is hidden — no empty banner or placeholder is shown

4. **Given** a Spike Alert Banner is visible on the dashboard
   **When** the user clicks the "Investigate" link on the banner
   **Then** the user is navigated to the Q&A page (`/qa`) with the topic filter pre-set via URL query params (e.g., `/qa?topic={topic}&question=What+are+people+saying+about+{topic}+right+now%3F`)

---

## Tasks / Subtasks

- [x] Backend: Add schemas for spikes endpoint (AC: 2)
  - [x] Add `SpikeAlert` and `SpikesResponse` to `backend/app/analytics/schemas.py`

- [x] Backend: Add `get_spikes` service function (AC: 1, 2, 3)
  - [x] Add `get_spikes` to `backend/app/analytics/service.py`
  - [x] Detect volume spikes: compare recent window vs baseline window per topic
  - [x] Detect sentiment spikes: compare negative % in recent vs baseline window per topic
  - [x] Return empty list when no spikes detected

- [x] Backend: Add `GET /analytics/spikes` endpoint (AC: 2)
  - [x] Add endpoint to `backend/app/api/analytics.py`
  - [x] Import `SpikesResponse` in schemas import line

- [x] Frontend: Create `SpikeAlertBanner` component (AC: 1, 3, 4)
  - [x] Create `frontend/components/dashboard/SpikeAlertBanner.tsx` — `'use client'`, accepts filters
  - [x] Fetch `GET /analytics/spikes` on mount and when filters change
  - [x] Render banner only when spikes are returned (hidden/null when no spikes)
  - [x] Each alert shows: topic label, spike type, magnitude, "Investigate" link to `/qa?topic=...&question=...`

- [x] Frontend: Integrate `SpikeAlertBanner` into `DashboardContent` (AC: 1, 3)
  - [x] Import and render `<SpikeAlertBanner filters={filters} />` at the top of the main content area in `DashboardContent.tsx`, before charts

- [x] Validate (AC: 1, 2, 3, 4)
  - [x] `npm run lint` — zero errors
  - [x] `npm run build` — clean TypeScript build
  - [x] Manual: confirm banner is hidden when no spikes; confirm banner appears with spike data when spikes present

---

## Developer Context

### CRITICAL: Story Foundation & Requirements

**User Story Objective:**
Surface sudden spikes in post volume or negative sentiment as a prominent, action-oriented alert at the top of the dashboard. This is a rapid-response feature — the banner must be **immediately visible** and **immediately actionable** (link to investigate). It is the primary entry point for the rapid-response user persona.

**Key Requirements Extracted from Epics:**
- Spike window is configurable (last 2–24 hours) — implemented as a query param `window_hours` (default: 24)
- Must detect **two types of spikes**: volume spike and sentiment (negative) spike
- Must show: topic label, spike type, magnitude indicator, and time window
- **Banner is completely hidden when no spikes** — no empty state, no placeholder, no "No alerts"
- "Investigate" link pre-fills the Q&A page with topic + suggested question via URL query params
- The Q&A page (`/qa`) already exists as a route (from Story 2.1). Epic 3 will implement the actual Q&A functionality including reading URL params to pre-fill the input. For now, just navigate there with query params.

---

### Architecture Compliance & Patterns

**Backend Patterns (established in Stories 2.2–2.6):**
- Service functions accept `AsyncSession`, `TaxonomyConfig`, filter params — match existing signatures exactly
- Return Pydantic schemas via FastAPI endpoint — add new schemas to `schemas.py` AFTER existing ones
- SQLAlchemy ORM: `select()`, `where()`, `and_()`, `func.count()`, `case()`, joins to `RawPost` and `ProcessedPost`
- CRITICAL: always use `or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))` — NULL-safe filter for error_status
- Taxonomy label lookup: `{t.name: t.label for t in taxonomy.topics}` — required for topic labels
- Date filtering via `cast(RawPost.created_at, Date)` pattern — same as volume/sentiment endpoints
- `_default_start` / `_default_end` helper functions already exist in `analytics.py` — do not duplicate

**Frontend Patterns (established in Stories 2.3–2.6):**
- `'use client'` directive — required for any component using state or effects
- `useEffect` with `AbortController` + `isActive` flag — copy this pattern exactly from `ComparisonPanel.tsx`
- `const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'` — same constant
- Import `FilterState` from `'./FilterBar'` — do NOT redefine it
- Design tokens: CSS variables from `globals.css`, e.g., `text-sentiment-negative`, `text-foreground`, `text-muted`, `bg-surface-raised`, `border-border` — NO hard-coded colors
- Tailwind v4: font size pattern `[font-size:var(--font-size-body)]` — no `tailwind.config.js`
- Loading state: `<p className="text-muted [font-size:var(--font-size-body)]">Loading…</p>`
- Error state: `<p className="text-sentiment-negative [font-size:var(--font-size-body)]">{error}</p>`
- **Banner hidden when no data**: return `null` (not empty div, not placeholder text)

**API Design:**
- All filter params optional and backward-compatible with existing endpoints
- Date validation: return HTTP 422 if `start_date > end_date`
- `window_hours` param: integer, default 24, accepted range 2–168 (up to 7 days)

---

### Technical Requirements

**Backend: New Pydantic Schemas**

Add to `backend/app/analytics/schemas.py` (after `ComparisonResponse`):

```python
class SpikeAlert(BaseModel):
    """A detected spike in volume or negative sentiment for a topic."""
    topic: str           # topic name (e.g., "vivienda")
    topic_label: str     # display label (e.g., "Vivienda")
    spike_type: str      # "volume" or "sentiment"
    magnitude: float     # ratio for volume (e.g., 2.5 = 2.5× increase); percentage points for sentiment (e.g., 0.25 = +25pp)
    recent_count: int    # posts in recent window
    baseline_count: int  # posts in baseline window (0 if baseline is empty)
    window_hours: int    # time window used for detection
    suggested_question: str  # pre-filled Q&A question, e.g., "What are people saying about Vivienda right now?"


class SpikesResponse(BaseModel):
    """Response for spike detection endpoint."""
    spikes: list[SpikeAlert]
    window_hours: int
    detected_at: str  # ISO date string "YYYY-MM-DD"
```

---

**Backend: `get_spikes` Service Function**

Add to `backend/app/analytics/service.py`:

```python
from app.analytics.schemas import ..., SpikeAlert, SpikesResponse

async def get_spikes(
    session: AsyncSession,
    taxonomy: TaxonomyConfig,
    window_hours: int = 24,
    volume_threshold: float = 2.0,   # spike if recent > baseline * threshold
    sentiment_threshold: float = 0.20,  # spike if recent negative% > baseline negative% + threshold
    platform: str | None = None,
) -> SpikesResponse:
    """Detect volume and sentiment spikes across all topics.
    
    Compares the recent window (last `window_hours`) against the prior
    equal-length baseline window. Returns spikes sorted by magnitude desc.
    """
    from datetime import datetime, timedelta
    now = date.today()
    recent_end = now
    recent_start = now - timedelta(hours=window_hours)
    baseline_end = recent_start
    baseline_start = baseline_end - timedelta(hours=window_hours)
    
    topic_label_map = {t.name: t.label for t in taxonomy.topics}
    
    base_error_filter = or_(
        ProcessedPost.error_status.is_(False),
        ProcessedPost.error_status.is_(None),
    )
    
    date_col = cast(RawPost.created_at, Date)
    
    def _platform_filter() -> list:
        return [RawPost.platform == platform] if platform else []
    
    # Query volume per topic for recent and baseline windows in one pass each
    async def _topic_counts(start: date, end: date) -> dict[str, int]:
        stmt = (
            select(ProcessedPost.topic, func.count().label("cnt"))
            .select_from(ProcessedPost)
            .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
            .where(and_(
                date_col >= start,
                date_col <= end,
                base_error_filter,
                *_platform_filter(),
            ))
            .group_by(ProcessedPost.topic)
        )
        result = await session.execute(stmt)
        return {row.topic: row.cnt for row in result.all() if row.topic}
    
    async def _topic_sentiment_counts(start: date, end: date) -> dict[str, dict[str, int]]:
        """Returns {topic: {positive: N, neutral: N, negative: N, total: N}}"""
        stmt = (
            select(ProcessedPost.topic, ProcessedPost.sentiment, func.count().label("cnt"))
            .select_from(ProcessedPost)
            .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
            .where(and_(
                date_col >= start,
                date_col <= end,
                base_error_filter,
                *_platform_filter(),
            ))
            .group_by(ProcessedPost.topic, ProcessedPost.sentiment)
        )
        result = await session.execute(stmt)
        out: dict[str, dict[str, int]] = {}
        for row in result.all():
            if not row.topic:
                continue
            t = out.setdefault(row.topic, {"positive": 0, "neutral": 0, "negative": 0, "total": 0})
            sentiment = (row.sentiment or "neutral").lower()
            if sentiment in t:
                t[sentiment] += row.cnt
            t["total"] += row.cnt
        return out
    
    recent_vol, baseline_vol, recent_sent, baseline_sent = await asyncio.gather(
        _topic_counts(recent_start, recent_end),
        _topic_counts(baseline_start, baseline_end),
        _topic_sentiment_counts(recent_start, recent_end),
        _topic_sentiment_counts(baseline_start, baseline_end),
    )
    
    spikes: list[SpikeAlert] = []
    
    for topic_name in set(list(recent_vol.keys()) + list(recent_sent.keys())):
        label = topic_label_map.get(topic_name, topic_name)
        suggested_q = f"What are people saying about {label} right now?"
        
        r_cnt = recent_vol.get(topic_name, 0)
        b_cnt = baseline_vol.get(topic_name, 0)
        
        # Volume spike detection
        if r_cnt > 0 and (b_cnt == 0 or r_cnt / max(b_cnt, 1) >= volume_threshold):
            magnitude = r_cnt / max(b_cnt, 1)
            spikes.append(SpikeAlert(
                topic=topic_name,
                topic_label=label,
                spike_type="volume",
                magnitude=round(magnitude, 2),
                recent_count=r_cnt,
                baseline_count=b_cnt,
                window_hours=window_hours,
                suggested_question=suggested_q,
            ))
        
        # Sentiment spike detection
        r_sent = recent_sent.get(topic_name, {})
        b_sent = baseline_sent.get(topic_name, {})
        r_total = r_sent.get("total", 0)
        b_total = b_sent.get("total", 0)
        if r_total > 0:
            r_neg_pct = r_sent.get("negative", 0) / r_total
            b_neg_pct = b_sent.get("negative", 0) / b_total if b_total > 0 else 0.0
            delta = r_neg_pct - b_neg_pct
            if delta >= sentiment_threshold:
                spikes.append(SpikeAlert(
                    topic=topic_name,
                    topic_label=label,
                    spike_type="sentiment",
                    magnitude=round(delta, 3),
                    recent_count=r_sent.get("negative", 0),
                    baseline_count=b_sent.get("negative", 0),
                    window_hours=window_hours,
                    suggested_question=suggested_q,
                ))
    
    # Sort by magnitude descending; limit to top 5 most significant spikes
    spikes.sort(key=lambda s: s.magnitude, reverse=True)
    spikes = spikes[:5]
    
    return SpikesResponse(
        spikes=spikes,
        window_hours=window_hours,
        detected_at=str(date.today()),
    )
```

**CRITICAL service notes:**
- MUST import `asyncio` at top of file — needed for `asyncio.gather()`
- `recent_start = now - timedelta(hours=window_hours)` uses `timedelta(hours=...)` — since `date_col` is cast to `Date`, this effectively compares by day boundaries, which is correct for daily-bucketed data
- Volume spike: triggers when `recent_count / max(baseline_count, 1) >= volume_threshold` OR when baseline is 0 and recent > 0
- Sentiment spike threshold is in **percentage points** (absolute delta), not relative — `0.20` means a 20pp swing
- Top 5 spikes only — prevents the banner from becoming overwhelming
- Return empty `spikes: []` when nothing detected — the frontend hides the banner when `spikes.length === 0`

---

**Backend: `GET /analytics/spikes` Endpoint**

Add to `backend/app/api/analytics.py`:

```python
from app.analytics.schemas import VolumeResponse, SentimentResponse, PlatformsResponse, TopicsResponse, PostsResponse, ComparisonResponse, SpikesResponse

@router.get("/spikes", response_model=SpikesResponse)
async def get_spikes(
    request: Request,
    window_hours: int = Query(default=24, ge=2, le=168, description="Detection window in hours (2–168)"),
    volume_threshold: float = Query(default=2.0, ge=1.0, description="Volume spike ratio threshold (default 2.0 = 2× increase)"),
    sentiment_threshold: float = Query(default=0.20, ge=0.0, le=1.0, description="Sentiment spike delta threshold in percentage points (default 0.20 = +20pp)"),
    platform: str | None = Query(default=None, description="Filter by platform"),
    session: AsyncSession = Depends(get_db),
) -> SpikesResponse:
    """Detect volume and sentiment spikes across all topics."""
    taxonomy = request.app.state.taxonomy
    return await analytics_service.get_spikes(session, taxonomy, window_hours, volume_threshold, sentiment_threshold, platform)
```

**Import update** — extend the schemas import line:
```python
from app.analytics.schemas import VolumeResponse, SentimentResponse, PlatformsResponse, TopicsResponse, PostsResponse, ComparisonResponse, SpikesResponse
```

**Note:** Also add `import asyncio` to `backend/app/analytics/service.py` if not already present.

---

**Frontend: `SpikeAlertBanner` Component**

**New file:** `frontend/components/dashboard/SpikeAlertBanner.tsx`

```tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { FilterState } from './FilterBar'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface SpikeAlert {
  topic: string
  topic_label: string
  spike_type: 'volume' | 'sentiment'
  magnitude: number
  recent_count: number
  baseline_count: number
  window_hours: number
  suggested_question: string
}

interface SpikesResponse {
  spikes: SpikeAlert[]
  window_hours: number
  detected_at: string
}

interface Props {
  filters: Pick<FilterState, 'platform'>
}

function formatMagnitude(alert: SpikeAlert): string {
  if (alert.spike_type === 'volume') {
    return `${alert.magnitude.toFixed(1)}× increase`
  }
  return `+${(alert.magnitude * 100).toFixed(0)}pp negative sentiment`
}

export default function SpikeAlertBanner({ filters }: Props) {
  const [spikes, setSpikes] = useState<SpikeAlert[]>([])
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    const controller = new AbortController()
    let isActive = true

    async function fetchSpikes() {
      setLoading(true)
      try {
        const params = new URLSearchParams()
        if (filters.platform) params.set('platform', filters.platform)

        const res = await fetch(`${API_BASE}/analytics/spikes?${params.toString()}`, {
          signal: controller.signal,
        })
        if (!res.ok) throw new Error('Failed to fetch spikes')
        const json = (await res.json()) as SpikesResponse
        if (!isActive) return
        setSpikes(json.spikes)
      } catch (err) {
        if ((err as Error).name === 'AbortError') return
        if (!isActive) return
        setSpikes([])
      } finally {
        if (!isActive) return
        setLoading(false)
      }
    }

    fetchSpikes()
    return () => {
      isActive = false
      controller.abort()
    }
  }, [filters.platform])

  // Hidden while loading or when no spikes — no placeholder shown
  if (loading || spikes.length === 0) return null

  return (
    <div className="col-span-12 rounded-lg border border-border bg-surface-raised p-4 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span className="text-sentiment-negative font-semibold [font-size:var(--font-size-body)]">
          ⚠ Spike Alerts
        </span>
        <span className="text-muted [font-size:var(--font-size-small)]">
          {spikes.length} topic{spikes.length !== 1 ? 's' : ''} flagged
        </span>
      </div>
      <div className="flex flex-col gap-2">
        {spikes.map((alert, i) => (
          <div
            key={`${alert.topic}-${alert.spike_type}-${i}`}
            className="flex items-center justify-between rounded border border-border bg-surface px-3 py-2"
          >
            <div className="flex items-center gap-3">
              <span className="text-sentiment-negative [font-size:var(--font-size-small)] font-medium">
                {alert.spike_type === 'volume' ? '📈' : '😠'}{' '}
                {alert.spike_type === 'volume' ? 'Volume' : 'Sentiment'} spike
              </span>
              <span className="text-foreground [font-size:var(--font-size-body)]">
                {alert.topic_label}
              </span>
              <span className="text-muted [font-size:var(--font-size-small)]">
                {formatMagnitude(alert)} in last {alert.window_hours}h
              </span>
            </div>
            <button
              onClick={() => {
                const q = encodeURIComponent(alert.suggested_question)
                router.push(`/qa?topic=${alert.topic}&question=${q}`)
              }}
              className="px-3 py-1 rounded border border-border text-foreground hover:bg-surface-raised [font-size:var(--font-size-small)] whitespace-nowrap"
            >
              Investigate →
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
```

**Component design notes:**
- Returns `null` when `loading` OR `spikes.length === 0` — no flicker, no placeholder
- Only passes `platform` filter to spikes endpoint — spike detection is global across all topics, not filtered by the user's current topic/subtopic/target selection (this matches the banner's purpose: ambient awareness of spikes across the dataset)
- `useRouter` from `'next/navigation'` — correct import for Next.js App Router
- Investigate link navigates to `/qa?topic=...&question=...` — Epic 3 will read these params to pre-fill the Q&A input; this is safe to ship before Epic 3 is done

---

**Frontend: Integrate into `DashboardContent`**

In `frontend/components/dashboard/DashboardContent.tsx`:

```tsx
import SpikeAlertBanner from './SpikeAlertBanner'
```

Render `<SpikeAlertBanner filters={filters} />` **at the very top of the main content area**, before `FilterBar`:

```tsx
return (
  <>
    <SpikeAlertBanner filters={filters} />
    <FilterBar filters={filters} onChange={setFilters} />
    {/* ... rest of dashboard ... */}
  </>
)
```

Apply this in **both** return blocks in `DashboardContent` (the `isEmpty` block and the main return block). The banner should always be rendered regardless of whether chart data exists.

---

### File Structure

| File | Action | Notes |
|------|--------|-------|
| `backend/app/analytics/schemas.py` | Modify | Add `SpikeAlert`, `SpikesResponse` after `ComparisonResponse` |
| `backend/app/analytics/service.py` | Modify | Add `get_spikes` function; add `import asyncio` if missing |
| `backend/app/api/analytics.py` | Modify | Add `GET /spikes` endpoint; extend schemas import |
| `frontend/components/dashboard/SpikeAlertBanner.tsx` | Create | New component |
| `frontend/components/dashboard/DashboardContent.tsx` | Modify | Import + render `SpikeAlertBanner` in both return branches |

**Do NOT modify** `FilterBar.tsx`, `ComparisonPanel.tsx`, `TopicsPanel.tsx`, `PostsPanel.tsx`, or any chart components.

---

### Previous Story Intelligence (from Story 2.6)

- **NULL-safe `error_status` filter**: `or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))` — this is a CRITICAL pattern; missing it causes silent data omissions
- **Taxonomy label map**: always build `{t.name: t.label for t in taxonomy.topics}` for display labels — never use raw topic names in the UI
- **Frontend loading guard**: `if (!isActive) return` before every state setter in the async function — prevents React state updates on unmounted components
- **`useMemo` for derived filter values**: if computing slugs from `filters`, wrap in `useMemo` to avoid infinite effect loops (see `ComparisonPanel.tsx` `comparisonPartySlugs`)
- **`AbortController` pattern**: `const controller = new AbortController()` → `{ signal: controller.signal }` → cleanup: `controller.abort()` — copy this verbatim from `ComparisonPanel.tsx`
- **Sentiment percentages**: round to 3 decimal places; multiply by 100 in the UI for display
- **Multi-value query params**: `params.append('key', value)` for list params (not `params.set`)
- **`'use client'` directive**: must be the very first line in any component file using hooks

---

### Git Intelligence Summary

Recent commits show:
- **Pattern for adding endpoints**: schemas → service function → API route → frontend component → integrate into `DashboardContent` — follow this exact sequence
- **Sprint status update**: each completed story updates `sprint-status.yaml` (handled by code-review workflow, not dev story)
- **DashboardContent pattern**: panels are rendered in order inside a single `<>` fragment; `SpikeAlertBanner` goes first (above `FilterBar`)
- **No test files needed** for stories in Epic 2 — validation is via `npm run lint` + `npm run build` + manual check

---

### NOTES: Next.js App Router Version Caveat

Per `frontend/AGENTS.md`: "This is NOT the Next.js you know — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code."

Specific confirmed patterns in this codebase:
- `useRouter` from `'next/navigation'` (App Router) — NOT from `'next/router'`
- `router.push('/qa?...')` for programmatic navigation
- `'use client'` directive — required for client components
- No `getServerSideProps` / `getStaticProps` — this is App Router

---

## Dev Agent Record

### Implementation Plan

1. **Backend Schemas**: Added `SpikeAlert` and `SpikesResponse` Pydantic models to `backend/app/analytics/schemas.py` following the exact specifications in Dev Notes.

2. **Backend Service**: Implemented `get_spikes()` service function in `backend/app/analytics/service.py`:
   - Added `import asyncio` at top of file
   - Implemented dual window detection (recent vs baseline)
   - Volume spike detection: triggers when recent/baseline ratio >= threshold (default 2.0)
   - Sentiment spike detection: triggers when negative sentiment delta >= threshold (default 0.20 = 20pp)
   - Used `asyncio.gather()` for parallel query execution
   - Returns top 5 spikes sorted by magnitude descending
   - Returns empty list when no spikes detected (AC 3)

3. **Backend API**: Added `GET /analytics/spikes` endpoint to `backend/app/api/analytics.py`:
   - Query params: `window_hours` (2-168), `volume_threshold`, `sentiment_threshold`, `platform`
   - Extended schemas import to include `SpikesResponse`

4. **Frontend Component**: Created `SpikeAlertBanner.tsx`:
   - `'use client'` directive for client-side hooks
   - Uses `AbortController` + `isActive` pattern for safe async fetching
   - Returns `null` when loading or no spikes (hidden banner - AC 3)
   - Shows spike type icon (📈 for volume, 😠 for sentiment)
   - Navigate to `/qa?topic=&question=` on Investigate click (AC 4)

5. **Frontend Integration**: Added `<SpikeAlertBanner filters={filters} />` to both return blocks in `DashboardContent.tsx` (isEmpty and main return)

### Completion Notes

- All 4 Acceptance Criteria satisfied
- Linting: 0 errors
- Build: Clean TypeScript compilation
- Pattern compliance: NULL-safe error_status filter, taxonomy label lookup, AbortController pattern
- Component returns `null` when no spikes - no flicker, no placeholder (AC 3)

---

## File List

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/app/analytics/schemas.py` | Modified | Added `SpikeAlert` and `SpikesResponse` schemas |
| `backend/app/analytics/service.py` | Modified | Added `import asyncio` and `get_spikes()` service function |
| `backend/app/api/analytics.py` | Modified | Added `GET /analytics/spikes` endpoint, updated imports |
| `frontend/components/dashboard/SpikeAlertBanner.tsx` | Created | New spike alert banner component |
| `frontend/components/dashboard/DashboardContent.tsx` | Modified | Integrated `SpikeAlertBanner` at top of both return blocks |

---

## Change Log

- 2026-04-08: Implemented Story 2.7 - Spike Alert Detection & Banner
  - Backend: Added schemas, service function, and API endpoint
  - Frontend: Created SpikeAlertBanner component and integrated into DashboardContent
  - Validations: npm run lint (0 errors), npm run build (clean)

---

**The developer has everything needed for flawless implementation!**

### Review Findings

- [x] [Review][Patch] `window_hours` date windows collapse for 2–23h — Python `date - timedelta(hours=…)` ignores sub-day components, so recent and baseline ranges can be identical and spike detection does nothing for those API values [`backend/app/analytics/service.py:563-565`] — fixed: map hours to whole-day spans (`span_days`)

- [x] [Review][Patch] `topic` query value should be URL-encoded for `/qa` navigation (special characters, spaces) [`frontend/components/dashboard/SpikeAlertBanner.tsx:109`] — fixed: `encodeURIComponent(alert.topic)`

- [x] [Review][Patch] Fetch failures clear spikes and hide the banner, same as “no spikes,” and skip the dashboard error-state pattern described in story context [`frontend/components/dashboard/SpikeAlertBanner.tsx:59-65`] — fixed: dedicated error state with `text-sentiment-negative` body style

- [x] [Review][Defer] Top-5 sort mixes volume ratios (often ≫1) with sentiment deltas (≈0–1), so volume spikes tend to crowd out sentiment spikes — behavior matches written spec; revisit if product wants balanced surfacing [`backend/app/analytics/service.py:678-679`] — deferred, pre-existing design in spec
