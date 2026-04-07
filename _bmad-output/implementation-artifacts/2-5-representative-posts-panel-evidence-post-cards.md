# Story 2.5: Representative Posts Panel (Evidence Post Cards)

**Status:** done
**Epic:** 2 — Analytics Dashboard & Data Exploration
**Story ID:** 2.5
**Story Key:** 2-5-representative-posts-panel-evidence-post-cards
**Created:** 2026-04-08

---

## Story

As a user,
I want to view representative example posts for a chosen topic, subtopic, or sentiment segment,
So that I can understand the actual language and narratives driving the numbers.

---

## Acceptance Criteria

1. **Given** filters are applied (topic, subtopic, sentiment, time range, platform)
   **When** the user views the posts panel
   **Then** up to 10 representative posts are displayed as Evidence Post Cards, each showing: original text, platform, date, sentiment label, and topic tag

2. **Given** `GET /analytics/posts` is called with filter params
   **When** the response is returned
   **Then** it returns a ranked list of representative posts (ordered by intensity DESC NULLS LAST, then created_at DESC) with fields: `id`, `original_text`, `platform`, `created_at`, `sentiment`, `topic`, `topic_label`, `subtopic`, `subtopic_label`, `author`, `source`

3. **Given** a post card is displayed
   **When** the user clicks the copy button
   **Then** the post text is copied to the clipboard using the `navigator.clipboard.writeText()` API and a brief "Copied!" confirmation indicator appears for ~2 seconds, then resets

---

## Tasks / Subtasks

- [x] Backend: Add schemas for posts endpoint (AC: 2)
  - [x] Add `PostItem` and `PostsResponse` to `backend/app/analytics/schemas.py`

- [x] Backend: Add `get_posts` service function (AC: 1, 2)
  - [x] Add `get_posts` to `backend/app/analytics/service.py` — single SQL query joining ProcessedPost + RawPost, same filter pattern as `get_volume`, ordered by intensity DESC NULLS LAST then created_at DESC, LIMIT 10
  - [x] Map topic/subtopic `name` → `label` using taxonomy passed as argument (same as `get_topics`)
  - [x] Include `total` count (separate COUNT(*) query with same filters, no limit)

- [x] Backend: Add `GET /analytics/posts` endpoint (AC: 2)
  - [x] Add endpoint to `backend/app/api/analytics.py` — same filter params as `/volume`/`/sentiment`/`/topics`, plus `Request` for taxonomy access
  - [x] Import `PostsResponse` in the schemas import line

- [x] Frontend: Create `PostsPanel` component (AC: 1, 3)
  - [x] Create `frontend/components/dashboard/PostsPanel.tsx` — `'use client'`, fetches `/analytics/posts` with current filters
  - [x] Render up to 10 Evidence Post Cards with: original text (truncated to 3 lines with expand), platform badge, date, sentiment label chip, topic tag
  - [x] Add copy button per card using `navigator.clipboard.writeText()` with transient "Copied!" confirmation (setTimeout 2000ms reset)
  - [x] Show loading, error, and empty states using same pattern as TopicsPanel

- [x] Frontend: Integrate `PostsPanel` into `DashboardContent` (AC: 1)
  - [x] Import and render `<PostsPanel filters={filters} />` below `<TopicsPanel>` in `frontend/components/dashboard/DashboardContent.tsx`
  - [x] Render PostsPanel in BOTH the empty branch AND the main return branch (same pattern as TopicsPanel)

- [x] Validate (AC: 1, 2, 3)
  - [x] `npm run lint` — zero errors
  - [x] `npm run build` — clean TypeScript build
  - [x] Manual: confirm posts panel renders below topics panel; verify copy button copies text and shows "Copied!" then resets

---

## Dev Notes

### CRITICAL: Read Bundled Next.js Docs Before Writing Code

`frontend/AGENTS.md` warns: **"This is NOT the Next.js you know. This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code."**

This project uses:
- **Next.js 16.2.2** (NOT 14 or 15)
- **React 19.2.4**
- **Tailwind CSS v4** — CSS-first, no `tailwind.config.js`, tokens in `frontend/app/globals.css` under `@theme`
- **TypeScript 5.x**

---

### Files to Create / Modify

**Create:**
```
frontend/components/dashboard/PostsPanel.tsx     ← NEW evidence post cards component
```

**Modify:**
```
backend/app/analytics/schemas.py                  ← ADD PostItem, PostsResponse
backend/app/analytics/service.py                  ← ADD get_posts() function
backend/app/api/analytics.py                      ← ADD GET /analytics/posts endpoint
frontend/components/dashboard/DashboardContent.tsx ← ADD PostsPanel render in both branches
```

**Do NOT touch:**
- `frontend/app/(shell)/dashboard/page.tsx` — server component, no changes needed
- `frontend/components/charts/VolumeChart.tsx`
- `frontend/components/charts/SentimentChart.tsx`
- `frontend/components/dashboard/FilterBar.tsx`
- `frontend/components/dashboard/TopicsPanel.tsx`
- Any QA routes or components

---

### Backend: New Pydantic Schemas

Add to `backend/app/analytics/schemas.py` (after `TopicsResponse`):

```python
class PostItem(BaseModel):
    """A single representative post with metadata for display as an Evidence Post Card."""
    id: str
    original_text: str
    platform: str
    created_at: str  # ISO date string "YYYY-MM-DD"
    sentiment: str   # "positive", "neutral", or "negative"
    topic: str
    topic_label: str
    subtopic: str | None
    subtopic_label: str | None
    author: str | None
    source: str | None


class PostsResponse(BaseModel):
    """Response for representative posts endpoint."""
    posts: list[PostItem]
    total: int
```

---

### Backend: `get_posts` Service Function

Add to `backend/app/analytics/service.py`:

```python
from app.analytics.schemas import ..., PostItem, PostsResponse

async def get_posts(
    session: AsyncSession,
    taxonomy: TaxonomyConfig,
    start_date: date,
    end_date: date,
    topic: str | None = None,
    subtopic: str | None = None,
    target: str | None = None,
    platform: str | None = None,
    limit: int = 10,
) -> PostsResponse:
    """Get representative posts for the given filters.

    Posts are ranked by intensity DESC (most intense/representative first),
    then by created_at DESC (most recent). Applies same filter pattern as get_volume.
    Returns up to `limit` posts plus the total count matching filters.
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

    # Count query (no LIMIT)
    count_stmt = (
        select(func.count())
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(and_(*base_filters))
    )
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Posts query — ranked by intensity DESC NULLS LAST, then created_at DESC
    posts_stmt = (
        select(
            ProcessedPost.id,
            RawPost.original_text,
            RawPost.platform,
            RawPost.created_at,
            RawPost.author,
            RawPost.source,
            ProcessedPost.sentiment,
            ProcessedPost.topic,
            ProcessedPost.subtopic,
            ProcessedPost.intensity,
        )
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(and_(*base_filters))
        .order_by(ProcessedPost.intensity.desc().nulls_last(), RawPost.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(posts_stmt)

    # Build label lookup maps from taxonomy
    topic_label_map: dict[str, str] = {t.name: t.label for t in taxonomy.topics}
    subtopic_label_map: dict[str, str] = {}
    for t in taxonomy.topics:
        for st in t.subtopics:
            subtopic_label_map[st.name] = st.label

    posts: list[PostItem] = []
    for row in result.all():
        topic_name = row.topic or "unknown"
        subtopic_name = row.subtopic
        created_date = row.created_at.date() if hasattr(row.created_at, "date") else row.created_at
        posts.append(PostItem(
            id=str(row.id),
            original_text=row.original_text,
            platform=row.platform or "",
            created_at=str(created_date),
            sentiment=(row.sentiment or "neutral").lower(),
            topic=topic_name,
            topic_label=topic_label_map.get(topic_name, topic_name),
            subtopic=subtopic_name,
            subtopic_label=subtopic_label_map.get(subtopic_name, subtopic_name) if subtopic_name else None,
            author=row.author,
            source=row.source,
        ))

    return PostsResponse(posts=posts, total=total)
```

**CRITICAL service notes:**
- MUST use `or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))` — fixes NULL exclusion bug from Story 2.2
- `taxonomy` is passed as a parameter — do NOT import or load it directly in the service
- `intensity` can be NULL — use `.nulls_last()` in ORDER BY
- `created_at` is a `DateTime` object — call `.date()` to extract the date portion for the response string

---

### Backend: `GET /analytics/posts` Endpoint

Add to `backend/app/api/analytics.py`:

```python
from app.analytics.schemas import VolumeResponse, SentimentResponse, PlatformsResponse, TopicsResponse, PostsResponse

# ... existing endpoints ...

@router.get("/posts", response_model=PostsResponse)
async def get_posts(
    request: Request,
    start_date: date = Query(default_factory=_default_start),
    end_date: date = Query(default_factory=_default_end),
    topic: str | None = Query(default=None, description="Filter by topic name (e.g. 'vivienda')"),
    subtopic: str | None = Query(default=None, description="Filter by subtopic name"),
    target: str | None = Query(default=None, description="Filter by political target"),
    platform: str | None = Query(default=None, description="Filter by platform"),
    session: AsyncSession = Depends(get_db),
) -> PostsResponse:
    """Get representative posts ranked by intensity and recency."""
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be less than or equal to end_date")
    taxonomy = request.app.state.taxonomy
    return await analytics_service.get_posts(session, taxonomy, start_date, end_date, topic, subtopic, target, platform)
```

**Import update** — extend the existing schemas import line in `analytics.py` to add `PostsResponse`:
```python
from app.analytics.schemas import VolumeResponse, SentimentResponse, PlatformsResponse, TopicsResponse, PostsResponse
```

---

### Frontend: `PostsPanel` Component

**New file:** `frontend/components/dashboard/PostsPanel.tsx`

Architecture requirements:
- `'use client'` directive (uses state + effects)
- Fetches `GET /analytics/posts` with all current filter params on mount and when filters change
- Evidence Post Card per post: original text, platform badge, date, sentiment chip, topic tag, copy button
- Copy button uses `navigator.clipboard.writeText()` + per-card `copied` state (setTimeout 2000ms)
- Sentiment chip colors: use design tokens (positive → `text-sentiment-positive bg-sentiment-positive/10`, negative → `text-sentiment-negative bg-sentiment-negative/10`, neutral → `text-muted bg-muted/10`)
- Loading / error / empty states using same text + class patterns as `TopicsPanel`

```tsx
'use client'
import { useEffect, useState } from 'react'
import { FilterState } from './FilterBar'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface PostItem {
  id: string
  original_text: string
  platform: string
  created_at: string
  sentiment: string
  topic: string
  topic_label: string
  subtopic: string | null
  subtopic_label: string | null
  author: string | null
  source: string | null
}

interface PostsData {
  posts: PostItem[]
  total: number
}

interface Props {
  filters: FilterState
}

function sentimentStyles(sentiment: string): { chip: string } {
  switch (sentiment) {
    case 'positive':
      return { chip: 'text-sentiment-positive bg-sentiment-positive/10' }
    case 'negative':
      return { chip: 'text-sentiment-negative bg-sentiment-negative/10' }
    default:
      return { chip: 'text-muted bg-muted/10' }
  }
}

function PostCard({ post }: { post: PostItem }) {
  const [copied, setCopied] = useState(false)
  const { chip } = sentimentStyles(post.sentiment)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(post.original_text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard access denied — silently ignore
    }
  }

  return (
    <div className="rounded border border-border bg-surface p-4 flex flex-col gap-2">
      {/* Metadata row */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-muted [font-size:var(--font-size-small)]">{post.platform}</span>
        <span className="text-muted [font-size:var(--font-size-small)]">·</span>
        <span className="text-muted [font-size:var(--font-size-small)]">{post.created_at}</span>
        <span className={`px-1.5 py-0.5 rounded [font-size:var(--font-size-small)] ${chip}`}>
          {post.sentiment}
        </span>
        <span className="px-1.5 py-0.5 rounded border border-border text-muted [font-size:var(--font-size-small)]">
          {post.topic_label}
        </span>
        {post.subtopic_label && (
          <span className="px-1.5 py-0.5 rounded border border-border text-muted [font-size:var(--font-size-small)]">
            {post.subtopic_label}
          </span>
        )}
      </div>

      {/* Post text — line-clamp-3 for compact view */}
      <p className="text-foreground [font-size:var(--font-size-body)] line-clamp-3">
        {post.original_text}
      </p>

      {/* Copy button */}
      <div className="flex justify-end">
        <button
          onClick={handleCopy}
          className="text-primary [font-size:var(--font-size-small)] hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
        >
          {copied ? 'Copied!' : 'Copy text'}
        </button>
      </div>
    </div>
  )
}

export default function PostsPanel({ filters }: Props) {
  const [data, setData] = useState<PostsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    let isActive = true

    async function fetchPosts() {
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

        const res = await fetch(`${API_BASE}/analytics/posts?${params.toString()}`, {
          signal: controller.signal,
        })
        if (!res.ok) throw new Error('Failed to fetch posts')
        const json = await res.json()
        if (!isActive) return
        setData(json)
      } catch (err) {
        if ((err as Error).name === 'AbortError') return
        if (!isActive) return
        setError('Unable to load representative posts.')
      } finally {
        if (!isActive) return
        setLoading(false)
      }
    }

    fetchPosts()
    return () => {
      isActive = false
      controller.abort()
    }
  }, [filters])

  if (loading) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">Loading posts…</p>
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

  const posts = data?.posts ?? []

  if (posts.length === 0) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">
          No posts found for the selected filters.
        </p>
      </div>
    )
  }

  return (
    <div className="col-span-12 bg-surface-raised rounded-lg border border-border p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)]">
          Representative Posts
        </h3>
        <span className="text-muted [font-size:var(--font-size-small)]">
          Showing {posts.length} of {(data?.total ?? 0).toLocaleString()}
        </span>
      </div>
      <div className="flex flex-col gap-3">
        {posts.map((post) => (
          <PostCard key={post.id} post={post} />
        ))}
      </div>
    </div>
  )
}
```

---

### Frontend: Updated `DashboardContent.tsx`

Extend the existing component minimally — do NOT rewrite from scratch.

1. Import `PostsPanel`:
   ```tsx
   import PostsPanel from './PostsPanel'
   ```

2. Render `<PostsPanel filters={filters} />` in the **empty branch** (below `<TopicsPanel>`):
   ```tsx
   // In the isEmpty return block, after <TopicsPanel ...>:
   <PostsPanel filters={filters} />
   ```

3. Render `<PostsPanel filters={filters} />` in the **main return block** (below `<TopicsPanel>`):
   ```tsx
   // After <TopicsPanel .../>:
   <PostsPanel filters={filters} />
   ```

**CRITICAL:** PostsPanel must render in BOTH the empty branch and the main data branch — same requirement as TopicsPanel (established in Story 2.4).

---

### Architecture Compliance

- ✅ `PostsPanel` is `'use client'` — uses state + effects
- ✅ `DashboardContent` stays `'use client'` — owns filter state
- ✅ `dashboard/page.tsx` stays a server component — no changes
- ✅ Data fetched via `NEXT_PUBLIC_API_BASE_URL` — same pattern as all other components
- ✅ New backend endpoint follows same filter param pattern — all params optional, backward compatible
- ✅ `request.app.state.taxonomy` used for label lookup — same as `GET /analytics/topics`
- ✅ `or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))` — MUST preserve this form
- ✅ Tailwind v4: use `[font-size:var(--font-size-*)]` pattern — NOT `text-sm`, `text-base`, etc.
- ✅ Design tokens from globals.css — do NOT use hard-coded hex values
- ✅ No `tailwind.config.js`
- ✅ No new pages, routes, or API routers
- ✅ `line-clamp-3` is a valid Tailwind v4 utility — use directly, no plugin needed

---

### Previous Story Learnings (Stories 2.2–2.4 — Must Preserve)

1. **UTC date shift bug** — Do NOT use `d.toISOString().split('T')[0]`. Already fixed in existing code; in the service, use `row.created_at.date()` to extract the date portion from the Python DateTime.
2. **error_status filter** — MUST use `or_(ProcessedPost.error_status.is_(False), ProcessedPost.error_status.is_(None))`. Not just `.is_(False)`.
3. **Date validation** — Preserve HTTP 422 when `start_date > end_date`. Add this check to the new `/posts` endpoint.
4. **AbortController pattern** — Use the same `controller/isActive` pattern for all frontend fetch calls (shown in PostsPanel template above).
5. **Tailwind v4 no config** — There is NO `tailwind.config.js`. All design tokens are in `frontend/app/globals.css` under `@theme`. Use only CSS variable references.
6. **Both branches pattern** — TopicsPanel and PostsPanel must render in BOTH the `isEmpty` branch and the main `return` branch of DashboardContent (confirmed fixed in Story 2.4 review).
7. **SubtopicDistributionItem label resolution** — Use per-topic label maps to avoid cross-topic name collision. Same principle applies here: build label maps from taxonomy before iterating results.
8. **intensity can be NULL** — ProcessedPost.intensity is nullable. Use `.nulls_last()` in ORDER BY, never assume it is set.

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
  bg-sentiment-positive   → same color — use /10 opacity suffix for background
  bg-sentiment-negative   → same color — use /10 opacity suffix for background
  bg-muted                → use for neutral chip backgrounds

Typography (via CSS variable):
  [font-size:var(--font-size-h4)]     → 1.125rem / 18px
  [font-size:var(--font-size-body)]   → 1rem / 16px
  [font-size:var(--font-size-small)]  → 0.875rem / 14px
```

---

### File Path Summary

**Backend — Modify:**
- `backend/app/analytics/schemas.py` — add `PostItem`, `PostsResponse`
- `backend/app/analytics/service.py` — add `get_posts()` function + new imports
- `backend/app/api/analytics.py` — add `GET /analytics/posts` + import `PostsResponse`

**Frontend — Create:**
- `frontend/components/dashboard/PostsPanel.tsx`

**Frontend — Modify:**
- `frontend/components/dashboard/DashboardContent.tsx` — import PostsPanel, render in both branches

**Do NOT create:**
- Any new pages or routes
- Any new API routers or modules
- Any test files
- `tailwind.config.js`

---

### References

- `frontend/AGENTS.md` — CRITICAL: read bundled Next.js docs before writing code
- `frontend/components/dashboard/DashboardContent.tsx` — existing client component to extend; import pattern and filter state ownership
- `frontend/components/dashboard/TopicsPanel.tsx` — the direct predecessor; mirror its fetch, state, and render patterns exactly
- `frontend/components/dashboard/FilterBar.tsx` — `FilterState` type definition
- `backend/app/api/analytics.py` — existing analytics router; extend with same filter param pattern
- `backend/app/analytics/service.py` — existing service; extend with same SQL + filter + taxonomy pattern
- `backend/app/analytics/schemas.py` — existing schemas; add `PostItem` and `PostsResponse` after `TopicsResponse`
- `backend/app/api/taxonomy.py` — shows `request.app.state.taxonomy` access pattern
- `backend/app/taxonomy/schemas.py` — `TaxonomyConfig` type
- `backend/app/models/processed_post.py` — ProcessedPost fields: `id`, `raw_post_id`, `topic`, `subtopic`, `sentiment`, `target`, `intensity`, `error_status`
- `backend/app/models/raw_post.py` — RawPost fields: `id`, `platform`, `original_text`, `author`, `source`, `created_at`
- `frontend/app/globals.css` — design tokens under `@theme` block
- `_bmad-output/implementation-artifacts/2-4-topic-distribution-trending-topics-panel.md` — previous story; full fetch/state/render patterns to mirror

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- 2026-04-08: Code review (batch option 0): fixed per-topic subtopic labels in `get_posts`, PostCard expand/collapse for clamped text, and copy timeout cleanup on unmount.
- 2026-04-08: Story implementation complete. All acceptance criteria satisfied:
  - AC1: PostsPanel component created with Evidence Post Cards showing original text, platform, date, sentiment, and topic tags. Copy button works with navigator.clipboard.writeText() and shows "Copied!" confirmation for 2 seconds.
  - AC2: GET /analytics/posts endpoint added with all filter params (topic, subtopic, target, platform, date range). Returns posts ranked by intensity DESC NULLS LAST, then created_at DESC, with total count.
  - AC3: Copy functionality implemented with transient "Copied!" indicator using setTimeout 2000ms reset.
- All tasks completed and marked with [x]
- npm run lint: zero errors
- npm run build: clean TypeScript build
- PostsPanel renders in both empty and main branches of DashboardContent, below TopicsPanel

### File List

**Created:**
- `frontend/components/dashboard/PostsPanel.tsx` — Evidence Post Cards component with copy functionality

**Modified:**
- `backend/app/analytics/schemas.py` — Added PostItem and PostsResponse schemas
- `backend/app/analytics/service.py` — Added get_posts() service function with SQL query joining ProcessedPost + RawPost
- `backend/app/api/analytics.py` — Added GET /analytics/posts endpoint

### Review Findings

- [x] [Review][Patch] Subtopic labels use a single global name→label map — `get_posts` builds `subtopic_label_map` by overwriting on duplicate subtopic names across topics; `get_topics` uses per-topic maps (`topic_subtopic_labels`). Same collision called out in story Dev Notes. Resolve by looking up `subtopic_label` via `(topic_name, subtopic_name)` like `get_topics`. [backend/app/analytics/service.py:346-368] — fixed: per-topic `topic_subtopic_labels` lookup.

- [x] [Review][Patch] Post text is line-clamped only — Tasks require “truncated to 3 lines **with expand**”; `PostCard` uses `line-clamp-3` with no expand/collapse control, so long text cannot be read in-panel without copying. [frontend/components/dashboard/PostsPanel.tsx:76-79] — fixed: Show more / Show less when text overflows clamp.

- [x] [Review][Patch] Copy “Copied!” timeout not cleared on unmount — `setTimeout` in `handleCopy` can fire after `PostCard` unmounts (filter change, navigation), risking a React state update on an unmounted component. Clear timeout in a `useEffect` cleanup or store `timeoutId` and `clearTimeout` in unmount/copy handler. [frontend/components/dashboard/PostsPanel.tsx:46-53] — fixed: `useRef` + `useEffect` cleanup and clear before rescheduling.
