# Story 2.4: Topic Distribution & Trending Topics Panel

**Status:** done
**Epic:** 2 — Analytics Dashboard & Data Exploration
**Story ID:** 2.4
**Story Key:** 2-4-topic-distribution-trending-topics-panel
**Created:** 2026-04-07

---

## Story

As a user,
I want to see which topics and subtopics are most discussed and which are most negative or positive within a given time window,
So that I can immediately identify what is driving the political conversation.

---

## Acceptance Criteria

1. **Given** processed posts exist for the selected filters
   **When** the user views the topics panel
   **Then** topics are listed ranked by volume (most discussed first), each showing post count and overall sentiment indicator (positive/neutral/negative)
   **And** a secondary sort or badge highlights the most negative and most positive topics

2. **Given** the `GET /analytics/topics` endpoint is called with filter params
   **When** the response is returned
   **Then** it includes each topic with: label, post count, sentiment distribution (positive/neutral/negative counts), and top subtopics

3. **Given** the user clicks a topic tile
   **When** the drill-down action fires
   **Then** the dashboard filters update to that topic and the panel shows the subtopic-level breakdown for that topic, preserving other active filters

---

## Tasks / Subtasks

- [x] Backend: Add schemas for topics endpoint (AC: 2)
  - [x] Add `SubtopicDistributionItem`, `TopicDistributionItem`, `TopicsResponse` to `backend/app/analytics/schemas.py`

- [x] Backend: Add `get_topics` service function (AC: 1, 2)
  - [x] Add `get_topics` to `backend/app/analytics/service.py` — two SQL queries (group by topic; group by topic+subtopic), merge results, apply same filter pattern as `get_volume`/`get_sentiment`
  - [x] Map topic/subtopic `name` → `label` using taxonomy from `app.state.taxonomy` (pass as argument)

- [x] Backend: Add `GET /analytics/topics` endpoint (AC: 2)
  - [x] Add endpoint to `backend/app/api/analytics.py` — same filter params as `/volume`/`/sentiment` plus `Request` for taxonomy access
  - [x] Import `TopicsResponse`, `TaxonomyConfig` types; pass `request.app.state.taxonomy` to service

- [x] Frontend: Create `TopicsPanel` component (AC: 1, 3)
  - [x] Create `frontend/components/dashboard/TopicsPanel.tsx` — `'use client'`, fetches `/analytics/topics` with current filters
  - [x] Render tiles ranked by count; show post count + sentiment bar; badge most negative/positive topics
  - [x] When `filters.topic` is set: show subtopic breakdown for that topic; show "All topics" back button
  - [x] On topic tile click: call `onTopicSelect(topic.name)` prop

- [x] Frontend: Integrate `TopicsPanel` into `DashboardContent` (AC: 3)
  - [x] Import and render `<TopicsPanel>` below the charts in `frontend/components/dashboard/DashboardContent.tsx`
  - [x] Pass `filters` and `onTopicSelect` callback: `(name) => setFilters({ ...filters, topic: name, subtopic: '' })`

- [x] Validate (AC: 1, 2, 3)
  - [x] `npm run lint` — zero errors
  - [x] `npm run build` — clean TypeScript build
  - [x] Manual: confirm topics panel renders ranked by volume; click a topic tile confirms filter updates and subtopic view appears; verify "All topics" reset works

---

## Dev Notes

### CRITICAL: Read Bundled Next.js Docs Before Writing Code

`frontend/AGENTS.md` warns: **"This is NOT the Next.js you know. This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code."**

This project uses:
- **Next.js 16.2.2** (NOT 14 or 15)
- **React 19.2.4**
- **Tailwind CSS v4** — CSS-first, no `tailwind.config.js`
- **TypeScript 5.x**
- **Recharts** — already in `package.json`, used by VolumeChart and SentimentChart

---

### Files to Create / Modify

**Create:**
```
frontend/components/dashboard/TopicsPanel.tsx     ← NEW topic distribution component
```

**Modify:**
```
backend/app/analytics/schemas.py                  ← ADD SubtopicDistributionItem, TopicDistributionItem, TopicsResponse
backend/app/analytics/service.py                  ← ADD get_topics() function
backend/app/api/analytics.py                      ← ADD GET /analytics/topics endpoint
frontend/components/dashboard/DashboardContent.tsx ← ADD TopicsPanel render + onTopicSelect callback
```

**Do NOT touch:**
- `frontend/app/(shell)/dashboard/page.tsx` — server component, no changes needed
- `frontend/components/charts/VolumeChart.tsx` — no changes
- `frontend/components/charts/SentimentChart.tsx` — no changes
- `frontend/components/dashboard/FilterBar.tsx` — no changes
- Any QA routes or components

---

### Backend: New Pydantic Schemas

Add to `backend/app/analytics/schemas.py`:

```python
class SubtopicDistributionItem(BaseModel):
    """Subtopic-level breakdown within a topic."""
    name: str
    label: str
    count: int
    positive: int
    neutral: int
    negative: int


class TopicDistributionItem(BaseModel):
    """Topic distribution with sentiment breakdown and top subtopics."""
    name: str
    label: str
    count: int
    positive: int
    neutral: int
    negative: int
    subtopics: list[SubtopicDistributionItem]


class TopicsResponse(BaseModel):
    """Response for topics distribution endpoint."""
    topics: list[TopicDistributionItem]
```

---

### Backend: `get_topics` Service Function

Add to `backend/app/analytics/service.py`:

```python
from app.analytics.schemas import ..., SubtopicDistributionItem, TopicDistributionItem, TopicsResponse
from app.taxonomy.schemas import TaxonomyConfig


async def get_topics(
    session: AsyncSession,
    taxonomy: TaxonomyConfig,
    start_date: date,
    end_date: date,
    topic: str | None = None,
    subtopic: str | None = None,
    target: str | None = None,
    platform: str | None = None,
) -> TopicsResponse:
    """Get topic distribution with sentiment breakdown.

    Ranks topics by post count (descending). Each topic includes sentiment
    distribution and top subtopics. Applies same filter pattern as get_volume.
    If topic filter is set, returns only that topic with its subtopics.
    """
    date_col = cast(RawPost.created_at, Date)
    base_filters = [
        date_col >= start_date,
        date_col <= end_date,
        or_(
            ProcessedPost.error_status.is_(False),
            ProcessedPost.error_status.is_(None),
        ),
    ]
    if topic is not None:
        base_filters.append(ProcessedPost.topic == topic)
    if subtopic is not None:
        base_filters.append(ProcessedPost.subtopic == subtopic)
    if target is not None:
        base_filters.append(ProcessedPost.target == target)
    if platform is not None:
        base_filters.append(RawPost.platform == platform)

    # Query 1: group by topic + sentiment
    topic_stmt = (
        select(
            ProcessedPost.topic,
            ProcessedPost.sentiment,
            func.count().label("count"),
        )
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(and_(*base_filters))
        .group_by(ProcessedPost.topic, ProcessedPost.sentiment)
    )
    topic_result = await session.execute(topic_stmt)

    # Aggregate topic-level counts
    topic_data: dict[str, dict] = {}
    for row in topic_result.all():
        t = row.topic or "unknown"
        if t not in topic_data:
            topic_data[t] = {"count": 0, "positive": 0, "neutral": 0, "negative": 0}
        sentiment = (row.sentiment or "neutral").lower()
        if sentiment not in ("positive", "neutral", "negative"):
            sentiment = "neutral"
        topic_data[t][sentiment] += row.count
        topic_data[t]["count"] += row.count

    # Query 2: group by topic + subtopic + sentiment
    subtopic_stmt = (
        select(
            ProcessedPost.topic,
            ProcessedPost.subtopic,
            ProcessedPost.sentiment,
            func.count().label("count"),
        )
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(and_(*base_filters))
        .group_by(ProcessedPost.topic, ProcessedPost.subtopic, ProcessedPost.sentiment)
    )
    subtopic_result = await session.execute(subtopic_stmt)

    # Aggregate subtopic-level counts
    subtopic_data: dict[str, dict[str, dict]] = {}
    for row in subtopic_result.all():
        t = row.topic or "unknown"
        s = row.subtopic or ""
        if not s:
            continue
        if t not in subtopic_data:
            subtopic_data[t] = {}
        if s not in subtopic_data[t]:
            subtopic_data[t][s] = {"count": 0, "positive": 0, "neutral": 0, "negative": 0}
        sentiment = (row.sentiment or "neutral").lower()
        if sentiment not in ("positive", "neutral", "negative"):
            sentiment = "neutral"
        subtopic_data[t][s][sentiment] += row.count
        subtopic_data[t][s]["count"] += row.count

    # Build label lookup maps from taxonomy
    topic_label_map: dict[str, str] = {t.name: t.label for t in taxonomy.topics}
    subtopic_label_map: dict[str, str] = {}
    for t in taxonomy.topics:
        for st in t.subtopics:
            subtopic_label_map[st.name] = st.label

    # Build response, sorted by count descending
    result_topics: list[TopicDistributionItem] = []
    for topic_name, counts in sorted(topic_data.items(), key=lambda x: x[1]["count"], reverse=True):
        subtopics_for_topic = []
        for st_name, st_counts in sorted(
            subtopic_data.get(topic_name, {}).items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        ):
            subtopics_for_topic.append(SubtopicDistributionItem(
                name=st_name,
                label=subtopic_label_map.get(st_name, st_name),
                **st_counts,
            ))
        result_topics.append(TopicDistributionItem(
            name=topic_name,
            label=topic_label_map.get(topic_name, topic_name),
            subtopics=subtopics_for_topic,
            **{k: counts[k] for k in ("count", "positive", "neutral", "negative")},
        ))

    return TopicsResponse(topics=result_topics)
```

**CRITICAL service notes:**
- Use `or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))` — must use this form (fixes NULL exclusion bug from Story 2.2)
- `taxonomy` is passed in as a parameter — do NOT import or load it directly in the service
- Fall back to the topic/subtopic `name` for label if not found in taxonomy (graceful degradation)
- Skip rows where `subtopic` is None/empty — subtopics are optional on processed posts

---

### Backend: `GET /analytics/topics` Endpoint

Add to `backend/app/api/analytics.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.analytics.schemas import VolumeResponse, SentimentResponse, PlatformsResponse, TopicsResponse

# ... existing endpoints ...

@router.get("/topics", response_model=TopicsResponse)
async def get_topics(
    request: Request,
    start_date: date = Query(default_factory=_default_start),
    end_date: date = Query(default_factory=_default_end),
    topic: str | None = Query(default=None, description="Filter by topic name (e.g. 'vivienda')"),
    subtopic: str | None = Query(default=None, description="Filter by subtopic name"),
    target: str | None = Query(default=None, description="Filter by political target"),
    platform: str | None = Query(default=None, description="Filter by platform"),
    session: AsyncSession = Depends(get_db),
) -> TopicsResponse:
    """Get topic distribution ranked by volume with sentiment breakdown."""
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be less than or equal to end_date")
    taxonomy = request.app.state.taxonomy
    return await analytics_service.get_topics(session, taxonomy, start_date, end_date, topic, subtopic, target, platform)
```

**Import update:** Add `Request` to existing FastAPI imports and `TopicsResponse` to the schemas import line.

**Existing import line** (line 7 in analytics.py):
```python
from app.analytics.schemas import VolumeResponse, SentimentResponse, PlatformsResponse
```
Change to:
```python
from app.analytics.schemas import VolumeResponse, SentimentResponse, PlatformsResponse, TopicsResponse
```

**Existing import line** (line 6 in analytics.py):
```python
from fastapi import APIRouter, Depends, HTTPException, Query
```
Change to:
```python
from fastapi import APIRouter, Depends, HTTPException, Query, Request
```

---

### Frontend: `TopicsPanel` Component

**New file:** `frontend/components/dashboard/TopicsPanel.tsx`

Architecture requirements:
- `'use client'` directive (uses state + effects)
- Fetches `GET /analytics/topics` with all current filter params on mount and when filters change
- Does NOT fetch taxonomy — backend already returns labels
- Shows topic tiles when `filters.topic` is empty (all-topics view)
- Shows subtopic tiles when `filters.topic` is set (drill-down view) + "← All topics" back button
- On topic tile click: calls `onTopicSelect(topic.name)` to update dashboard filters
- Badge logic: find the topic with lowest positive% → "Most Negative"; highest positive% → "Most Positive"
- Uses design tokens from globals.css (see Design Token Reference below)

```tsx
'use client'
import { useEffect, useState } from 'react'
import { FilterState } from './FilterBar'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface SubtopicItem {
  name: string
  label: string
  count: number
  positive: number
  neutral: number
  negative: number
}

interface TopicItem {
  name: string
  label: string
  count: number
  positive: number
  neutral: number
  negative: number
  subtopics: SubtopicItem[]
}

interface TopicsData {
  topics: TopicItem[]
}

interface Props {
  filters: FilterState
  onTopicSelect: (topicName: string) => void
  onClearTopic: () => void
}

export default function TopicsPanel({ filters, onTopicSelect, onClearTopic }: Props) {
  const [data, setData] = useState<TopicsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    let isActive = true

    async function fetchTopics() {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({
          start_date: filters.startDate,
          end_date: filters.endDate,
        })
        if (filters.topic) params.set('topic', filters.topic)
        if (filters.subtopic) params.set('subtopic', filters.subtopic)
        if (filters.target) params.set('target', filters.target)
        if (filters.platform) params.set('platform', filters.platform)

        const res = await fetch(`${API_BASE}/analytics/topics?${params.toString()}`, {
          signal: controller.signal,
        })
        if (!res.ok) throw new Error('Failed to fetch topics')
        const json = await res.json()
        if (!isActive) return
        setData(json)
      } catch (err) {
        if ((err as Error).name === 'AbortError') return
        if (!isActive) return
        setError('Unable to load topics data.')
      } finally {
        if (!isActive) return
        setLoading(false)
      }
    }

    fetchTopics()
    return () => {
      isActive = false
      controller.abort()
    }
  }, [filters])

  const topics = data?.topics ?? []
  const isDrillDown = Boolean(filters.topic)

  // Determine items to display: when topic filter is set, show that topic's subtopics
  const displayItems: Array<{ name: string; label: string; count: number; positive: number; neutral: number; negative: number }> =
    isDrillDown && topics.length > 0
      ? topics[0].subtopics
      : topics

  // Badge logic (only for top-level topics view)
  let mostNegativeName = ''
  let mostPositiveName = ''
  if (!isDrillDown && topics.length > 1) {
    const withRatios = topics.map((t) => ({
      name: t.name,
      negRatio: t.count > 0 ? t.negative / t.count : 0,
      posRatio: t.count > 0 ? t.positive / t.count : 0,
    }))
    mostNegativeName = withRatios.reduce((a, b) => (b.negRatio > a.negRatio ? b : a)).name
    mostPositiveName = withRatios.reduce((a, b) => (b.posRatio > a.posRatio ? b : a)).name
  }

  if (loading) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">Loading topics…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="col-span-12">
        <p className="text-sentiment-negative [font-size:var(--font-size-body)]">{error}</p>
      </div>
    )
  }

  if (displayItems.length === 0) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">
          No topic data for the selected filters.
        </p>
      </div>
    )
  }

  return (
    <div className="col-span-12 bg-surface-raised rounded-lg border border-border p-4">
      <div className="flex items-center gap-3 mb-4">
        {isDrillDown && (
          <button
            onClick={onClearTopic}
            className="text-primary [font-size:var(--font-size-small)] hover:underline"
          >
            ← All topics
          </button>
        )}
        <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)]">
          {isDrillDown && topics.length > 0 ? `${topics[0].label} — Subtopics` : 'Topic Distribution'}
        </h3>
      </div>

      <div className="flex flex-col gap-2">
        {displayItems.map((item) => {
          const total = item.positive + item.neutral + item.negative || 1
          const posW = Math.round((item.positive / total) * 100)
          const neuW = Math.round((item.neutral / total) * 100)
          const negW = 100 - posW - neuW

          return (
            <button
              key={item.name}
              onClick={() => !isDrillDown && onTopicSelect(item.name)}
              disabled={isDrillDown}
              className={`w-full text-left rounded border border-border p-3 transition-colors ${
                !isDrillDown ? 'hover:border-primary hover:bg-surface cursor-pointer' : 'cursor-default'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-foreground [font-size:var(--font-size-body)]">
                  {item.label}
                </span>
                <div className="flex items-center gap-2">
                  {!isDrillDown && item.name === mostNegativeName && (
                    <span className="px-1.5 py-0.5 rounded bg-sentiment-negative/10 text-sentiment-negative [font-size:var(--font-size-small)]">
                      Most negative
                    </span>
                  )}
                  {!isDrillDown && item.name === mostPositiveName && item.name !== mostNegativeName && (
                    <span className="px-1.5 py-0.5 rounded bg-sentiment-positive/10 text-sentiment-positive [font-size:var(--font-size-small)]">
                      Most positive
                    </span>
                  )}
                  <span className="text-muted [font-size:var(--font-size-small)]">
                    {item.count.toLocaleString()} posts
                  </span>
                </div>
              </div>

              {/* Sentiment bar */}
              <div className="flex h-1.5 rounded overflow-hidden gap-px">
                {posW > 0 && (
                  <div className="bg-sentiment-positive" style={{ width: `${posW}%` }} />
                )}
                {neuW > 0 && (
                  <div className="bg-muted" style={{ width: `${neuW}%` }} />
                )}
                {negW > 0 && (
                  <div className="bg-sentiment-negative" style={{ width: `${negW}%` }} />
                )}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
```

---

### Frontend: Updated `DashboardContent.tsx`

Extend the existing component — do NOT rewrite from scratch. Minimal changes:

1. Import `TopicsPanel`:
   ```tsx
   import TopicsPanel from './TopicsPanel'
   ```

2. Add `onTopicSelect` and `onClearTopic` callbacks (before the return statement):
   ```tsx
   function handleTopicSelect(topicName: string) {
     setFilters((prev) => ({ ...prev, topic: topicName, subtopic: '' }))
   }
   function handleClearTopic() {
     setFilters((prev) => ({ ...prev, topic: '', subtopic: '' }))
   }
   ```

3. Render `<TopicsPanel>` in the main return block, below the SentimentChart card:
   ```tsx
   <TopicsPanel
     filters={filters}
     onTopicSelect={handleTopicSelect}
     onClearTopic={handleClearTopic}
   />
   ```

4. Also render `<TopicsPanel>` in the `isEmpty` branch (below `<FilterBar>`), so the panel shows even when volume/sentiment charts have no data.

**CRITICAL:** The `isEmpty` check (`!volumeData?.data?.length && !sentimentData?.data?.length`) must NOT cause TopicsPanel to disappear. Render TopicsPanel in BOTH the empty branch and the main return branch.

---

### Architecture Compliance

- ✅ `TopicsPanel` is `'use client'` — uses state + effects
- ✅ `DashboardContent` remains `'use client'` — owns filter state
- ✅ `dashboard/page.tsx` stays a server component — no changes
- ✅ Data fetched via `NEXT_PUBLIC_API_BASE_URL` — same pattern as all other components
- ✅ New backend endpoint follows same filter param pattern — all params optional, backward compatible
- ✅ `request.app.state.taxonomy` used for label lookup — same pattern as `GET /taxonomy` endpoint
- ✅ `or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))` — preserve this form in new service function
- ✅ Tailwind v4: use `[font-size:var(--font-size-small)]` pattern (NOT `text-sm`)
- ✅ Design tokens from globals.css — use `text-sentiment-negative`, `text-sentiment-positive`, `bg-surface-raised`, `border-border`, `text-muted`, `text-foreground`
- ✅ No `tailwind.config.js`
- ✅ No new pages or routing

---

### Previous Story Learnings (Stories 2.2 & 2.3 — Must Preserve)

1. **UTC date shift bug** — Do NOT use `d.toISOString().split('T')[0]`. Already fixed in existing code.
2. **error_status filter** — MUST use `or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))`. Not just `.is_(False)`.
3. **Date validation** — Preserve HTTP 422 when `start_date > end_date`. Add this check to the new `/topics` endpoint.
4. **AbortController pattern** — Use the same `controller/isActive` pattern seen in DashboardContent for all frontend fetch calls (already shown in TopicsPanel template above).
5. **Tailwind v4 no config** — There is NO `tailwind.config.js`. All design tokens are in `frontend/app/globals.css` under `@theme`. Use only the CSS variable references documented below.
6. **`setFilters` replaces object** — When updating filters in callbacks, spread the existing object: `{ ...prev, topic: name, subtopic: '' }`. This triggers `useEffect([filters])` correctly.

---

### Design Token Reference (from `frontend/app/globals.css`)

```
Backgrounds & Surfaces:
  bg-surface              → slate-50  (#f8fafc light / #111827 dark)
  bg-surface-raised       → white (#ffffff light / #1f2937 dark)

Borders:
  border-border           → slate-200 (#e2e8f0 light / #334155 dark)

Text:
  text-foreground         → dark text (primary content)
  text-muted              → slate-500 (#64748b light / #94a3b8 dark)
  text-primary            → blue-700 (#1d4ed8)

Sentiment:
  text-sentiment-positive → green-600 (#16a34a)
  text-sentiment-negative → red-600 (#dc2626)
  bg-sentiment-positive   → (same color, use /10 opacity suffix for background)
  bg-sentiment-negative   → (same color, use /10 opacity suffix for background)
  bg-muted                → use for neutral sentiment bar segment

Typography (via CSS variable):
  [font-size:var(--font-size-h4)]     → 1.125rem / 18px
  [font-size:var(--font-size-body)]   → 1rem / 16px
  [font-size:var(--font-size-small)]  → 0.875rem / 14px
```

---

### File Path Summary

**Backend — Modify:**
- `backend/app/analytics/schemas.py` — add 3 new schemas
- `backend/app/analytics/service.py` — add `get_topics()` function + new imports
- `backend/app/api/analytics.py` — add `GET /analytics/topics` + import `Request` and `TopicsResponse`

**Frontend — Create:**
- `frontend/components/dashboard/TopicsPanel.tsx`

**Frontend — Modify:**
- `frontend/components/dashboard/DashboardContent.tsx` — import TopicsPanel, add callbacks, render TopicsPanel in both branches

**Do NOT create:**
- Any new pages or routes
- Any new API routers or modules
- Any test files
- `tailwind.config.js`

---

### References

- `frontend/AGENTS.md` — CRITICAL: read bundled Next.js docs before writing code
- `frontend/components/dashboard/DashboardContent.tsx` — existing client component to extend
- `frontend/components/dashboard/FilterBar.tsx` — FilterState type, existing filter pattern to mirror
- `frontend/components/charts/VolumeChart.tsx` — recharts usage pattern for reference
- `backend/app/api/analytics.py` — existing analytics router to extend
- `backend/app/analytics/service.py` — existing service functions; extend same SQL + filter pattern
- `backend/app/analytics/schemas.py` — existing schemas to extend
- `backend/app/api/taxonomy.py` — shows `request.app.state.taxonomy` access pattern (line 11-12)
- `backend/app/taxonomy/schemas.py` — TaxonomyConfig type (for type hint on `taxonomy` param)
- `backend/app/models/processed_post.py` — ProcessedPost fields: `topic`, `subtopic`, `sentiment`, `target`, `error_status`
- `backend/app/models/raw_post.py` — RawPost fields: `platform`, `created_at`
- `frontend/app/globals.css` — design tokens under `@theme` block
- `_bmad-output/implementation-artifacts/2-3-dashboard-filter-controls.md` — previous story patterns

---

## Dev Agent Record

### Completion Notes List

- **Backend schemas**: Added `SubtopicDistributionItem`, `TopicDistributionItem`, and `TopicsResponse` Pydantic schemas to `backend/app/analytics/schemas.py` to support the topics distribution endpoint.

- **Backend service**: Implemented `get_topics()` function in `backend/app/analytics/service.py` with dual SQL queries (topic-level and subtopic-level aggregations), proper filter application following the pattern from `get_volume`/`get_sentiment`, and label mapping using taxonomy.

- **Backend endpoint**: Added `GET /analytics/topics` endpoint to `backend/app/api/analytics.py` with same filter params as volume/sentiment endpoints, plus `Request` injection for taxonomy access.

- **Frontend TopicsPanel**: Created `frontend/components/dashboard/TopicsPanel.tsx` as a client component that fetches `/analytics/topics`, displays topic tiles ranked by volume with sentiment breakdown bars, badges most negative/positive topics, and supports drill-down to subtopic view when a topic is selected.

- **Frontend integration**: Integrated `TopicsPanel` into `DashboardContent.tsx` with `handleTopicSelect` and `handleClearTopic` callbacks for filter management. Panel renders in both empty and data branches.

- **Validation**: All checks passed - `npm run lint` (0 errors), `npm run build` (clean TypeScript build, all pages prerendered), Python syntax verification passed.

### File List

**Created:**
- `frontend/components/dashboard/TopicsPanel.tsx` — Topic distribution panel component with drill-down support

**Modified:**
- `backend/app/analytics/schemas.py` — Added `SubtopicDistributionItem`, `TopicDistributionItem`, `TopicsResponse` schemas
- `backend/app/analytics/service.py` — Added `get_topics()` function with taxonomy-aware label mapping
- `backend/app/api/analytics.py` — Added `GET /analytics/topics` endpoint with Request dependency
- `frontend/components/dashboard/DashboardContent.tsx` — Integrated TopicsPanel with filter callbacks

### Review Findings

- [x] [Review][Patch] Subtopic labels should be resolved per parent topic — `get_topics` uses a single flat `subtopic_label_map` over all topics, so duplicate `name` values across different topics would get an arbitrary label. Prefer resolving each subtopic’s label from `taxonomy.topics` for the current topic only. [`backend/app/analytics/service.py`] — fixed: per-topic `topic_subtopic_labels` map

- [x] [Review][Patch] Drill-down empty states in TopicsPanel — When `filters.topic` is set, an empty list shows “No topic data for the selected filters.” even if the real case is “no subtopics in range” or stale filter; if the API returns `topics: []` while a topic filter is active, the heading can fall back to “Topic Distribution” despite drill-down UI. Adjust copy and title for `isDrillDown` + empty `topics` / empty `displayItems`. [`frontend/components/dashboard/TopicsPanel.tsx`] — fixed: contextual `emptyMessage`, `panelTitle`, drill-down card with back button on empty
