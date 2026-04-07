# Story 2.6: Cross-Party Sentiment Comparison

**Status:** review
**Epic:** 2 — Analytics Dashboard & Data Exploration
**Story ID:** 2.6
**Story Key:** 2-6-cross-party-sentiment-comparison
**Created:** 2026-04-08

---

## Story

As an analyst or campaign manager,
I want to compare sentiment and volume across at least two parties or targets for a chosen topic and time range,
So that I can understand how my party's performance on an issue compares to competitors.

---

## Acceptance Criteria

1. **Given** the user selects a topic and a time range
   **When** the user enables the comparison view and selects two or more parties
   **Then** a side-by-side or overlaid chart shows sentiment distribution and volume for each selected party across the time window

2. **Given** `GET /analytics/compare` is called with `topic`, `parties[]`, `start_date`, `end_date`
   **When** the response is returned
   **Then** it returns per-party breakdowns: post count, sentiment distribution (positive/neutral/negative), and top subtopics for each party

3. **Given** the campaign manager journey (FR19)
   **When** a user selects the "Housing" topic, sets a 7-day range, and compares two parties
   **Then** the comparison view renders correctly with both parties' data visible and the most negative subtopic is identifiable from the chart or topic panel

---

## Tasks / Subtasks

- [x] Backend: Add schemas for comparison endpoint (AC: 2)
  - [x] Add `PartyComparison`, `ComparisonData`, and `ComparisonResponse` to `backend/app/analytics/schemas.py`

- [x] Backend: Add `get_comparison` service function (AC: 1, 2)
  - [x] Add `get_comparison` to `backend/app/analytics/service.py` — query per-party post counts, sentiment distributions, and top subtopics for the given filters
  - [x] Return structured breakdown per party with topic/subtopic labels mapped from taxonomy

- [x] Backend: Add `GET /analytics/compare` endpoint (AC: 2)
  - [x] Add endpoint to `backend/app/api/analytics.py` with `topic`, `parties[]` (array param), `start_date`, `end_date`
  - [x] Import `ComparisonResponse` in schemas import line

- [x] Frontend: Create `ComparisonPanel` component (AC: 1)
  - [x] Create `frontend/components/dashboard/ComparisonPanel.tsx` — `'use client'`, accepts topic and selected parties
  - [x] Fetches `GET /analytics/compare` with topic, parties array, and current date filters
  - [x] Render side-by-side comparison cards showing per-party breakdowns: post count, sentiment bars/distribution, and top subtopics
  - [x] Show loading, error, and empty states using same pattern as `PostsPanel`

- [x] Frontend: Add party selection filter to `FilterBar` (AC: 1)
  - [x] Update `FilterBar.tsx` to include multi-select for parties/targets
  - [x] Pass selected parties to `ComparisonPanel` via `FilterState`

- [x] Frontend: Integrate `ComparisonPanel` into `DashboardContent` (AC: 1)
  - [x] Import and render `<ComparisonPanel filters={filters} />` alongside other panels in `frontend/components/dashboard/DashboardContent.tsx`
  - [x] Position comparison panel below the topic/posts panels for clear data flow (topic → comparison → posts)

- [x] Validate (AC: 1, 2, 3)
  - [x] `npm run lint` — zero errors
  - [x] `npm run build` — clean TypeScript build
  - [x] Manual: confirm comparison panel renders with two parties; verify post counts and sentiment distributions match analytics endpoints

---

## Developer Context

### CRITICAL: Story Foundation & Requirements

**User Story Objective:**  
Enable campaign managers and analysts to compare how their party is performing on a specific issue versus one or more competitors. This is a core workflow (FR19 from UX spec: "Campaign manager checking issue performance vs a competitor"), so speed and clarity of the comparison view is critical.

**Key Requirements Extracted from Epics:**
- Must support **two or more parties** in a single view (plural, not just A vs B)
- Must show **sentiment distribution per party** (positive/neutral/negative counts or percentages)
- Must show **post volume per party**
- Must show **top subtopics per party** so users can identify which sub-issues drive sentiment for each party
- Comparison must work with **existing filters** (topic, time range, platform)
- The "Housing" topic example (AC: 3) must work seamlessly with the schema and service

**Design & UX Context (from UX spec):**
- Comparison view should be **side-by-side or overlaid chart** — the developer can choose the visual approach, but both parties' data must be visible at once for fast comparison
- Fits into the command-center dashboard as part of the **analytical drill-down path**: users see top-level dashboard → topic/issue tile → can launch a comparison for two parties → drill into posts/subtopics
- The most negative subtopic should be **identifiable from the chart or topic panel** — this means either a tooltip/label on the chart or a separate panel showing top subtopics ranked by negative sentiment

---

### Architecture Compliance & Patterns

**Backend Patterns (from Story 2.5 & earlier):**
- Service functions accept `AsyncSession`, `TaxonomyConfig`, and filter params
- Return Pydantic schemas via FastAPI endpoint
- Use SQLAlchemy ORM with `select()`, `where()`, `and_()`, joins to `RawPost` and `ProcessedPost`
- CRITICAL: use `or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))` for NULL-safe filtering
- Map topic/subtopic names → labels using taxonomy lookup tables (avoid cross-topic name collisions)
- Return separate queries for counts vs detail rows when needed (similar to `get_posts` which runs COUNT then SELECT)

**Frontend Patterns (from Story 2.5 & 2.4):**
- Client components (`'use client'`) for anything that fetches or holds state
- Use `useEffect` with `AbortController` and `isActive` flag to manage async fetches safely
- Fetch via `NEXT_PUBLIC_API_BASE_URL`
- Pass `FilterState` (from `FilterBar`) as props
- Design tokens from `frontend/app/globals.css` — use CSS variable references, NOT hard-coded colors
- Tailwind v4: use `[font-size:var(--font-size-*)]` pattern, NO `tailwind.config.js`
- Error/loading/empty states follow the exact same text + class patterns as `TopicsPanel` and `PostsPanel`

**API Design:**
- All filter params are **optional** (backward-compatible with existing endpoints)
- Date validation: return HTTP 422 if `start_date > end_date`
- Array params like `parties[]` can be passed via query string multiple times (e.g. `?parties=party1&parties=party2`) or as a comma-separated string — FastAPI will handle both

---

### Technical Requirements

**Backend: New Pydantic Schemas**

Add to `backend/app/analytics/schemas.py` (after `PostsResponse`):

```python
class SubtopicSentiment(BaseModel):
    """Subtopic with sentiment breakdown for a party."""
    subtopic: str
    subtopic_label: str
    positive_count: int
    neutral_count: int
    negative_count: int
    total: int
    sentiment_percentage: dict[str, float]  # {"positive": 0.45, "neutral": 0.30, "negative": 0.25}


class PartyComparison(BaseModel):
    """Per-party sentiment and volume breakdown for comparison view."""
    party: str  # target name (e.g., "partido-socialista")
    party_label: str  # display label
    post_count: int
    positive_count: int
    neutral_count: int
    negative_count: int
    sentiment_percentage: dict[str, float]  # {"positive": 0.X, "neutral": 0.Y, "negative": 0.Z}
    top_subtopics: list[SubtopicSentiment]  # up to 3–5 subtopics ranked by negative sentiment


class ComparisonResponse(BaseModel):
    """Response for cross-party sentiment comparison."""
    topic: str
    topic_label: str
    parties: list[PartyComparison]
    total_posts: int
    date_range: dict[str, str]  # {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}
```

---

**Backend: `get_comparison` Service Function**

Add to `backend/app/analytics/service.py`:

```python
from app.analytics.schemas import ..., SubtopicSentiment, PartyComparison, ComparisonResponse

async def get_comparison(
    session: AsyncSession,
    taxonomy: TaxonomyConfig,
    topic: str,
    parties: list[str],
    start_date: date,
    end_date: date,
    platform: str | None = None,
) -> ComparisonResponse:
    """Get per-party sentiment and volume breakdown for a given topic and time range.
    
    Returns post counts, sentiment distributions (positive/neutral/negative),
    and top 3–5 subtopics ranked by negative sentiment for each party.
    """
    if not parties:
        parties = [None]  # Allow None to represent no target filter (all posts)
    
    date_col = cast(RawPost.created_at, Date)
    topic_label_map = {t.name: t.label for t in taxonomy.topics}
    
    # Build per-topic subtopic label map for accurate label lookup
    topic_subtopic_labels: dict[str, dict[str, str]] = {}
    for t in taxonomy.topics:
        topic_subtopic_labels[t.name] = {st.name: st.label for st in t.subtopics}
    
    # Target label map
    target_label_map: dict[str, str] = {t.name: t.label for t in taxonomy.targets}
    
    results: list[PartyComparison] = []
    
    # Query each party separately for clarity
    for party in parties:
        base_filters = [
            date_col >= start_date,
            date_col <= end_date,
            ProcessedPost.topic == topic,
            or_(
                ProcessedPost.error_status.is_(False),
                ProcessedPost.error_status.is_(None),
            ),
        ]
        if party is not None:
            base_filters.append(ProcessedPost.target == party)
        if platform is not None:
            base_filters.append(RawPost.platform == platform)
        
        # Main query: post counts and sentiment distribution
        stmt = (
            select(
                func.count().label("total"),
                func.sum(
                    case(
                        (ProcessedPost.sentiment == "positive", 1),
                        else_=0,
                    )
                ).label("positive_count"),
                func.sum(
                    case(
                        (ProcessedPost.sentiment == "neutral", 1),
                        else_=0,
                    )
                ).label("neutral_count"),
                func.sum(
                    case(
                        (ProcessedPost.sentiment == "negative", 1),
                        else_=0,
                    )
                ).label("negative_count"),
            )
            .select_from(ProcessedPost)
            .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
            .where(and_(*base_filters))
        )
        result = await session.execute(stmt)
        row = result.first()
        
        post_count = row.total or 0
        positive_count = row.positive_count or 0
        neutral_count = row.neutral_count or 0
        negative_count = row.negative_count or 0
        
        sentiment_pct = {
            "positive": round(positive_count / post_count, 3) if post_count > 0 else 0.0,
            "neutral": round(neutral_count / post_count, 3) if post_count > 0 else 0.0,
            "negative": round(negative_count / post_count, 3) if post_count > 0 else 0.0,
        }
        
        # Query top subtopics ranked by negative sentiment count
        subtopic_stmt = (
            select(
                ProcessedPost.subtopic,
                func.sum(
                    case(
                        (ProcessedPost.sentiment == "positive", 1),
                        else_=0,
                    )
                ).label("positive_count"),
                func.sum(
                    case(
                        (ProcessedPost.sentiment == "neutral", 1),
                        else_=0,
                    )
                ).label("neutral_count"),
                func.sum(
                    case(
                        (ProcessedPost.sentiment == "negative", 1),
                        else_=0,
                    )
                ).label("negative_count"),
                func.count().label("total"),
            )
            .select_from(ProcessedPost)
            .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
            .where(and_(*base_filters))
            .group_by(ProcessedPost.subtopic)
            .order_by(desc("negative_count"))
            .limit(5)
        )
        subtopic_result = await session.execute(subtopic_stmt)
        
        top_subtopics: list[SubtopicSentiment] = []
        for st_row in subtopic_result.all():
            st_name = st_row.subtopic or "unknown"
            st_positive = st_row.positive_count or 0
            st_neutral = st_row.neutral_count or 0
            st_negative = st_row.negative_count or 0
            st_total = st_row.total or 0
            
            st_label = topic_subtopic_labels.get(topic, {}).get(st_name, st_name)
            st_pct = {
                "positive": round(st_positive / st_total, 3) if st_total > 0 else 0.0,
                "neutral": round(st_neutral / st_total, 3) if st_total > 0 else 0.0,
                "negative": round(st_negative / st_total, 3) if st_total > 0 else 0.0,
            }
            
            top_subtopics.append(SubtopicSentiment(
                subtopic=st_name,
                subtopic_label=st_label,
                positive_count=st_positive,
                neutral_count=st_neutral,
                negative_count=st_negative,
                total=st_total,
                sentiment_percentage=st_pct,
            ))
        
        party_label = target_label_map.get(party, party) if party else "Overall"
        results.append(PartyComparison(
            party=party or "all",
            party_label=party_label,
            post_count=post_count,
            positive_count=positive_count,
            neutral_count=neutral_count,
            negative_count=negative_count,
            sentiment_percentage=sentiment_pct,
            top_subtopics=top_subtopics,
        ))
    
    return ComparisonResponse(
        topic=topic,
        topic_label=topic_label_map.get(topic, topic),
        parties=results,
        total_posts=sum(p.post_count for p in results),
        date_range={"start_date": str(start_date), "end_date": str(end_date)},
    )
```

**CRITICAL service notes:**
- MUST use `or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))` — same NULL fix as Story 2.2
- `parties` is passed as a **list** — the endpoint will handle parsing `?parties=party1&parties=party2` and converting to a list
- **Per-topic subtopic label lookup:** Use `topic_subtopic_labels[topic][subtopic_name]` to avoid cross-topic collisions (same lesson from Story 2.5)
- Sentiment percentages should be **rounded to 3 decimal places** for consistency
- Top subtopics are ranked by **negative_count DESC** — this makes the most negative subtopic immediately visible

---

**Backend: `GET /analytics/compare` Endpoint**

Add to `backend/app/api/analytics.py`:

```python
from app.analytics.schemas import VolumeResponse, SentimentResponse, PlatformsResponse, TopicsResponse, PostsResponse, ComparisonResponse

# ... existing endpoints ...

@router.get("/compare", response_model=ComparisonResponse)
async def get_comparison(
    request: Request,
    topic: str = Query(..., description="Topic name (e.g., 'vivienda')"),
    parties: list[str] = Query(default=[], description="List of target/party names to compare (e.g., ?parties=party1&parties=party2)"),
    start_date: date = Query(default_factory=_default_start),
    end_date: date = Query(default_factory=_default_end),
    platform: str | None = Query(default=None, description="Filter by platform"),
    session: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """Get per-party sentiment and volume comparison for a topic."""
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be less than or equal to end_date")
    if not parties:
        raise HTTPException(status_code=400, detail="At least one party must be specified for comparison")
    taxonomy = request.app.state.taxonomy
    return await analytics_service.get_comparison(session, taxonomy, topic, parties, start_date, end_date, platform)
```

**Import update** — extend the schemas import line:
```python
from app.analytics.schemas import VolumeResponse, SentimentResponse, PlatformsResponse, TopicsResponse, PostsResponse, ComparisonResponse
```

---

**Frontend: `ComparisonPanel` Component**

**New file:** `frontend/components/dashboard/ComparisonPanel.tsx`

Architecture requirements:
- `'use client'` directive (uses state + effects)
- Fetches `GET /analytics/compare` with topic, parties array, and date filters
- Renders **side-by-side comparison cards** for each party showing:
  - Party name and post count
  - Sentiment distribution as bars or percentages (positive/neutral/negative)
  - Top 3–5 subtopics with negative sentiment highlighted
- Loading / error / empty states using same text + class patterns as `PostsPanel`
- Design tokens: use CSS variable references from `globals.css`

```tsx
'use client'
import { useEffect, useState } from 'react'
import { FilterState } from './FilterBar'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface SubtopicSentiment {
  subtopic: string
  subtopic_label: string
  positive_count: number
  neutral_count: number
  negative_count: number
  total: number
  sentiment_percentage: {
    positive: number
    neutral: number
    negative: number
  }
}

interface PartyComparison {
  party: string
  party_label: string
  post_count: number
  positive_count: number
  neutral_count: number
  negative_count: number
  sentiment_percentage: {
    positive: number
    neutral: number
    negative: number
  }
  top_subtopics: SubtopicSentiment[]
}

interface ComparisonData {
  topic: string
  topic_label: string
  parties: PartyComparison[]
  total_posts: number
  date_range: {
    start_date: string
    end_date: string
  }
}

interface Props {
  filters: FilterState
}

function sentimentBarColor(sentiment: 'positive' | 'neutral' | 'negative'): string {
  switch (sentiment) {
    case 'positive':
      return 'bg-sentiment-positive'
    case 'negative':
      return 'bg-sentiment-negative'
    default:
      return 'bg-muted'
  }
}

function SubtopicItem({ subtopic }: { subtopic: SubtopicSentiment }) {
  const negPct = (subtopic.sentiment_percentage.negative * 100).toFixed(0)
  return (
    <div className="flex items-center justify-between text-muted [font-size:var(--font-size-small)] py-1">
      <span className="truncate">{subtopic.subtopic_label}</span>
      <span className="text-sentiment-negative whitespace-nowrap ml-2">{negPct}% negative</span>
    </div>
  )
}

function PartyCard({ party }: { party: PartyComparison }) {
  const totalPosts = party.post_count
  const sentiments = [
    { label: 'Positive', count: party.positive_count, color: 'bg-sentiment-positive' },
    { label: 'Neutral', count: party.neutral_count, color: 'bg-muted' },
    { label: 'Negative', count: party.negative_count, color: 'bg-sentiment-negative' },
  ]

  return (
    <div className="rounded border border-border bg-surface-raised p-4 flex flex-col gap-3">
      {/* Party header */}
      <div className="flex items-baseline justify-between border-b border-border pb-2">
        <h4 className="font-medium text-foreground [font-size:var(--font-size-h4)]">
          {party.party_label}
        </h4>
        <span className="text-muted [font-size:var(--font-size-small)]">
          {totalPosts.toLocaleString()} posts
        </span>
      </div>

      {/* Sentiment distribution bars */}
      <div className="flex gap-1 h-6">
        {sentiments.map((s) => {
          const widthPct = totalPosts > 0 ? (s.count / totalPosts) * 100 : 0
          return (
            <div
              key={s.label}
              className={`flex-1 rounded ${s.color} opacity-80 hover:opacity-100 transition-opacity group relative`}
              style={{ width: `${widthPct}%` }}
              title={`${s.label}: ${s.count} (${(party.sentiment_percentage[s.label.toLowerCase() as 'positive' | 'neutral' | 'negative'] * 100).toFixed(1)}%)`}
            >
              {/* Tooltip on hover */}
              <div className="hidden group-hover:block absolute top-full mt-1 px-2 py-1 bg-foreground text-surface rounded text-xs whitespace-nowrap z-10">
                {s.label}: {s.count}
              </div>
            </div>
          )
        })}
      </div>

      {/* Sentiment percentage breakdown */}
      <div className="flex gap-4 text-muted [font-size:var(--font-size-small)]">
        <span>
          <span className="text-sentiment-positive">●</span> Positive: {(party.sentiment_percentage.positive * 100).toFixed(1)}%
        </span>
        <span>
          <span className="text-muted">●</span> Neutral: {(party.sentiment_percentage.neutral * 100).toFixed(1)}%
        </span>
        <span>
          <span className="text-sentiment-negative">●</span> Negative: {(party.sentiment_percentage.negative * 100).toFixed(1)}%
        </span>
      </div>

      {/* Top subtopics */}
      {party.top_subtopics.length > 0 && (
        <div className="border-t border-border pt-3">
          <p className="text-muted [font-size:var(--font-size-small)] font-medium mb-2">
            Top Subtopics
          </p>
          <div className="flex flex-col gap-1">
            {party.top_subtopics.slice(0, 5).map((st) => (
              <SubtopicItem key={st.subtopic} subtopic={st} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function ComparisonPanel({ filters }: Props) {
  const [data, setData] = useState<ComparisonData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    let isActive = true

    async function fetchComparison() {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({
          topic: filters.topic || '',
          start_date: filters.startDate,
          end_date: filters.endDate,
        })

        // Add parties (if multiple selected in filters)
        // Note: filters.target might be single; this assumes future FilterBar supports multi-party selection
        if (filters.target) {
          params.append('parties', filters.target)
        }
        if (filters.platform) {
          params.append('platform', filters.platform)
        }

        if (!filters.topic) {
          setError('Please select a topic to view comparisons.')
          setLoading(false)
          return
        }

        const res = await fetch(`${API_BASE}/analytics/compare?${params.toString()}`, {
          signal: controller.signal,
        })
        if (!res.ok) {
          if (res.status === 400) {
            setError('Please select at least two parties to compare.')
          } else {
            throw new Error('Failed to fetch comparison data')
          }
          return
        }
        const json = await res.json()
        if (!isActive) return
        setData(json)
      } catch (err) {
        if ((err as Error).name === 'AbortError') return
        if (!isActive) return
        setError('Unable to load comparison data.')
      } finally {
        if (!isActive) return
        setLoading(false)
      }
    }

    fetchComparison()
    return () => {
      isActive = false
      controller.abort()
    }
  }, [filters])

  if (loading) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">Loading comparison…</p>
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

  const parties = data?.parties ?? []

  if (parties.length === 0) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">
          No comparison data available for the selected filters.
        </p>
      </div>
    )
  }

  return (
    <div className="col-span-12 bg-surface-raised rounded-lg border border-border p-4">
      <div className="mb-4">
        <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)]">
          Sentiment Comparison: {data?.topic_label}
        </h3>
        <p className="text-muted [font-size:var(--font-size-small)] mt-1">
          {data?.date_range.start_date} to {data?.date_range.end_date} — {data?.total_posts.toLocaleString()} posts
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {parties.map((party) => (
          <PartyCard key={party.party} party={party} />
        ))}
      </div>
    </div>
  )
}
```

---

**Frontend: Updated `FilterBar.tsx`**

Extend the existing `FilterBar` to include **multi-select for parties/targets**:

1. Add a new state for selected parties (can be multi-select or single depending on your design choice)
2. Export the selected parties in `FilterState` type
3. Pass selected parties to the `ComparisonPanel`

**Minimal change example:**
```tsx
// In FilterBar.tsx, add to FilterState type:
export interface FilterState {
  startDate: string
  endDate: string
  topic: string | null
  subtopic: string | null
  target: string | null
  platform: string | null
  selectedParties: string[]  // NEW: for comparison view
}

// In FilterBar component, add a party multi-select dropdown
// (use existing UI patterns from the topic/subtopic selects)
```

Alternatively, if you want to keep comparison simple, you can allow the `target` field to accept a single party and the `ComparisonPanel` can work with that. The endpoint accepts a `parties[]` array, so the frontend can decide how many parties to send.

---

**Frontend: Updated `DashboardContent.tsx`**

Add `ComparisonPanel` to the dashboard:

1. Import `ComparisonPanel`:
   ```tsx
   import ComparisonPanel from './ComparisonPanel'
   ```

2. Render `<ComparisonPanel filters={filters} />` after `<PostsPanel>` in both branches (empty and main):
   ```tsx
   // After <PostsPanel .../>:
   <ComparisonPanel filters={filters} />
   ```

**Position logic:**
- If a **topic is selected**, show the comparison panel so users can select parties and compare
- If **no topic is selected**, the panel can show a placeholder: "Select a topic to enable party comparison"

---

## Architecture Compliance

- ✅ `ComparisonPanel` is `'use client'` — uses state + effects
- ✅ `DashboardContent` stays `'use client'` — owns filter state
- ✅ `dashboard/page.tsx` stays a server component — no changes
- ✅ Data fetched via `NEXT_PUBLIC_API_BASE_URL` — same pattern as all other components
- ✅ New backend endpoint follows same filter param pattern — all params optional except `topic` and `parties[]`
- ✅ `request.app.state.taxonomy` used for label lookup — same as `GET /analytics/topics`
- ✅ `or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))` — MUST preserve this form
- ✅ Per-topic subtopic label maps prevent cross-topic collisions — same lesson from Story 2.5
- ✅ Tailwind v4: use `[font-size:var(--font-size-*)]` pattern — NOT `text-sm`, `text-base`, etc.
- ✅ Design tokens from globals.css — do NOT use hard-coded hex values
- ✅ No `tailwind.config.js`
- ✅ No new pages, routes, or API routers (only extend existing analytics router)
- ✅ HTTP 422 date validation preserved from Story 2.2

---

## Previous Story Learnings (Stories 2.2–2.5 — MUST PRESERVE)

1. **UTC date shift bug** — Do NOT use `d.toISOString().split('T')[0]`. Use `str(start_date)` in the backend and pass `filters.startDate` as-is from the frontend. Already fixed in existing code.

2. **error_status filter** — MUST use `or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))`. Not just `.is_(False)`.

3. **Date validation** — Preserve HTTP 422 when `start_date > end_date`. This is now standard across all analytics endpoints.

4. **AbortController pattern** — Use the same `controller/isActive` pattern for all frontend fetch calls.

5. **Tailwind v4 no config** — There is NO `tailwind.config.js`. All design tokens are in `frontend/app/globals.css` under `@theme`. Use only CSS variable references.

6. **Both branches pattern** — All panels (VolumeChart, SentimentChart, TopicsPanel, PostsPanel, ComparisonPanel) must render in BOTH the `isEmpty` branch AND the main `return` branch of DashboardContent.

7. **Per-topic subtopic label maps** — Build a `topic_subtopic_labels: dict[str, dict[str, str]]` from the taxonomy to avoid cross-topic name collisions when looking up labels (confirmed in Story 2.5 review).

8. **intensity can be NULL** — ProcessedPost.intensity is nullable. Use `.nulls_last()` in ORDER BY where applicable.

9. **Sentiment percentages precision** — Round to 3 decimal places (0.123, not 0.123456) for consistency and readability.

10. **Top subtopics ranking** — Rank by **negative_count DESC** so the most concerning subtopic appears first. This directly supports AC: 3 ("most negative subtopic is identifiable").

---

## Git Intelligence Summary

**Recent commit patterns (last 5 commits):**
- **226c222:** PostsPanel + schemas + endpoints — established full fetch/state/render patterns
- **34c8eb4:** TopicsPanel + comparison-ready schema (sentiment breakdown by topic)
- **fe3cafe:** FilterBar refactor — added optional topic/subtopic/target/platform filters
- **eff947c:** SentimentChart + analytics router integration
- **5ff9867:** Frontend styling — globals.css design tokens, Inter font

**File patterns to follow:**
- Backend service functions always: `async def func_name(...) -> ResponseSchema`
- Frontend client components always: `'use client'` at top, `useEffect(() => { controller/isActive }, [deps])`
- All new API endpoints follow `/analytics/*` pattern with query params
- All data returned via Pydantic `BaseModel` schemas for automatic OpenAPI docs

**No breaking changes:** All new endpoints are additions to the existing analytics API surface; no existing endpoints are modified.

---

## Latest Tech Information

**Frameworks & Libraries (Current Versions):**
- **FastAPI 0.100+:** Latest async/await patterns fully supported; SQLAlchemy 2.x async integration is stable
- **SQLAlchemy 2.x:** Use `select()`, `func.count()`, `case()`, `func.sum()` for aggregations; no raw SQL
- **Next.js 16.2.2, React 19.2.4:** App Router fully async server components; client components via `'use client'`
- **Tailwind CSS v4:** CSS-first, no JS config, all tokens in CSS `@theme` block
- **TypeScript 5.x:** Modern generics and union types; no legacy patterns needed

**API Best Practices:**
- Array query params in FastAPI: `?parties=party1&parties=party2` automatically becomes `list[str]`
- Optional query params: use `Query(default=None)` or `Query(default=[])`
- Status code 422 for validation errors is automatic with FastAPI; 400 for business logic errors

---

## File Path Summary

**Backend — Modify:**
- `backend/app/analytics/schemas.py` — add `SubtopicSentiment`, `PartyComparison`, `ComparisonResponse`
- `backend/app/analytics/service.py` — add `get_comparison()` function + imports
- `backend/app/api/analytics.py` — add `GET /analytics/compare` + import `ComparisonResponse`

**Frontend — Create:**
- `frontend/components/dashboard/ComparisonPanel.tsx`

**Frontend — Modify:**
- `frontend/components/dashboard/FilterBar.tsx` — add multi-select for parties (or extend `target` to support comparison)
- `frontend/components/dashboard/DashboardContent.tsx` — import `ComparisonPanel`, render in both branches

**Do NOT create:**
- Any new pages or routes
- Any new API routers or modules
- Any test files
- `tailwind.config.js`

---

## References

- `frontend/AGENTS.md` — bundled Next.js docs
- `frontend/components/dashboard/DashboardContent.tsx` — main dashboard structure; import + render pattern
- `frontend/components/dashboard/PostsPanel.tsx` — direct predecessor; mirror fetch/state patterns exactly
- `frontend/components/dashboard/FilterBar.tsx` — `FilterState` type definition + existing filter UI
- `backend/app/api/analytics.py` — existing analytics router; extend with `GET /analytics/compare`
- `backend/app/analytics/service.py` — existing service; extend with `get_comparison()` using same SQL + taxonomy pattern
- `backend/app/analytics/schemas.py` — existing schemas; add `SubtopicSentiment`, `PartyComparison`, `ComparisonResponse`
- `backend/app/taxonomy/schemas.py` — `TaxonomyConfig` type with `.targets` array
- `backend/app/models/processed_post.py` — ProcessedPost fields: `id`, `raw_post_id`, `topic`, `subtopic`, `sentiment`, `target`, `intensity`, `error_status`
- `backend/app/models/raw_post.py` — RawPost fields: `id`, `platform`, `original_text`, `author`, `source`, `created_at`
- `frontend/app/globals.css` — design tokens under `@theme` block
- `_bmad-output/implementation-artifacts/2-5-representative-posts-panel-evidence-post-cards.md` — previous story; fetch/state patterns, error handling
- `_bmad-output/implementation-artifacts/2-4-topic-distribution-trending-topics-panel.md` — story 2-4; multi-select patterns, sentiment coloring

---

## Dev Agent Record

### Agent Model Used

kimi-k2.5:cloud

### Debug Log References

(None — clean implementation)

### Completion Notes List

1. ✅ Added `SubtopicSentiment`, `PartyComparison`, and `ComparisonResponse` Pydantic schemas to `backend/app/analytics/schemas.py`
2. ✅ Implemented `get_comparison()` service function in `backend/app/analytics/service.py` with per-party sentiment aggregation and top subtopics ranked by negative sentiment
3. ✅ Added `GET /analytics/compare` endpoint to `backend/app/api/analytics.py` with proper validation (400 for empty parties, 422 for invalid date range)
4. ✅ Created `ComparisonPanel.tsx` component with side-by-side party cards, sentiment distribution bars, and top subtopics display
5. ✅ Extended `FilterBar.tsx` with `selectedParties` field in `FilterState` and hover-activated multi-select dropdown for party selection
6. ✅ Integrated `ComparisonPanel` into `DashboardContent.tsx` positioned after `TopicsPanel` and before `PostsPanel`
7. ✅ All validation passed: `npm run lint` (zero errors), `npm run build` (clean TypeScript build with static generation)

---

## File List

**Backend (Modified):**
- `backend/app/analytics/schemas.py` — Added `SubtopicSentiment`, `PartyComparison`, `ComparisonResponse` schemas
- `backend/app/analytics/service.py` — Added `get_comparison()` function with imports (`case`, `desc`)
- `backend/app/api/analytics.py` — Added `GET /analytics/compare` endpoint

**Frontend (Created):**
- `frontend/components/dashboard/ComparisonPanel.tsx` — New component for side-by-side party comparison

**Frontend (Modified):**
- `frontend/components/dashboard/FilterBar.tsx` — Added `selectedParties` to `FilterState`, added party multi-select dropdown UI
- `frontend/components/dashboard/DashboardContent.tsx` — Added `ComparisonPanel` import and integration

## Change Log

- **2026-04-08:** Implemented cross-party sentiment comparison feature (Story 2.6)
  - Added comparison schemas, service function, and API endpoint
  - Created ComparisonPanel with sentiment bars and top subtopics
  - Extended FilterBar with party multi-select capability

### Review Findings

- [x] [Review][Patch] ComparisonPanel calls `/analytics/compare` without `parties` when only a topic is set — users see a red API error instead of a neutral “select parties” empty state [`frontend/components/dashboard/ComparisonPanel.tsx`] — fixed: guard + muted copy before fetch
- [x] [Review][Patch] AC1 requires comparing **two or more** parties; the API and UI allow a single party (no minimum-2 validation) [`backend/app/api/analytics.py`, `ComparisonPanel.tsx`] — fixed: `len(parties) >= 2` on API; UI requires two slugs before fetch
- [x] [Review][Patch] Empty-data branch orders panels `TopicsPanel` → `PostsPanel` → `ComparisonPanel`, but the main branch uses `TopicsPanel` → `ComparisonPanel` → `PostsPanel` (story asked for comparison before posts consistently) [`frontend/components/dashboard/DashboardContent.tsx`] — fixed: aligned order
- [x] [Review][Patch] Sentiment strip uses `flex-1` on each segment **and** an inline `width: ${widthPct}%`, which fights flex layout; bar widths may not match counts [`frontend/components/dashboard/ComparisonPanel.tsx`] — fixed: width-only segments in a flex row
- [x] [Review][Patch] Hover tooltip uses `text-xs` instead of the project’s `[font-size:var(--font-size-*)]` token pattern [`frontend/components/dashboard/ComparisonPanel.tsx`] — fixed: `--font-size-small`
- [x] [Review][Defer] `get_comparison` sets `parties = [None]` when empty, but the route already returns 400 for empty `parties` — dead path unless called directly [`backend/app/analytics/service.py`] — addressed: dead branch removed; service raises if `< 2` parties
- [x] [Review][Defer] “Compare Parties” control is hover-only (`group-hover`); poor for keyboard/touch [`frontend/components/dashboard/FilterBar.tsx`] — deferred, pre-existing UX pattern

## Status

**Current Status:** done  
**Created:** 2026-04-08  
**Last Updated:** 2026-04-08  

**Next Steps:**
1. Optional: re-run `/bmad-code-review` on a future change
2. Pick up next backlog story in sprint plan
