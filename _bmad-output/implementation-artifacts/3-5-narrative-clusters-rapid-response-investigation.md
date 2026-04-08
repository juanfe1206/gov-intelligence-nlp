# Story 3.5: Narrative Clusters & Rapid Response Investigation

**Status:** done
**Epic:** 3 — LLM-Powered Q&A Intelligence Interface
**Story ID:** 3.5
**Story Key:** 3-5-narrative-clusters-rapid-response-investigation
**Created:** 2026-04-08

---

## Story

As a rapid-response user,
I want the Q&A response to group related posts into distinct narrative clusters and display them as Narrative Cluster Cards, and I want to click dashboard topic tiles to pre-fill the question input,
So that I can quickly identify the 2–3 key narrative threads driving a crisis and investigate without manual reformulation.

---

## Acceptance Criteria

1. **Given** a Q&A response for a crisis-style question (e.g. "What are the main negative narratives about our leader right now?")
   **When** the response renders
   **Then** the Insight Summary Panel includes a narrative clusters section showing 2–4 Narrative Cluster Cards, each with: a cluster label, sentiment tag, post count, and 1–2 representative quotes

2. **Given** `POST /qa` returns its payload
   **When** the backend groups retrieved posts into clusters
   **Then** clustering is performed by subtopic or topic label (as a lightweight proxy for narrative grouping in the MVP), with each cluster containing its top posts

3. **Given** a topic tile or spike alert is clicked on the dashboard
   **When** the click action fires
   **Then** the Q&A page opens with the question input pre-filled based on the clicked context (topic tile pre-fills a default question about that topic; spike alert "Investigate →" pre-fills the `suggested_question`)

---

## Scope for Story 3.5

**IN SCOPE:**
- Backend: `NarrativeCluster` schema + cluster grouping in Q&A service
- Frontend: `NarrativeClusterCard` section in `QAContent.tsx` answer panel
- Frontend: `QAContent.tsx` reads `?question=` and `?topic=` URL search params on mount to pre-fill state
- Frontend: `qa/page.tsx` wrapped in `<Suspense>` to support `useSearchParams()` in child
- Frontend: Topic tiles in `TopicsPanel.tsx` get a secondary "→ Q&A" action button
- Spike alert "Investigate →" button already navigates correctly — just need `QAContent` to read the params

**OUT OF SCOPE:**
- Retry button on transient errors — Story 3.6
- Context-aware empty-state filter suggestions — Story 3.6
- Demo-reset or admin flows — Epic 4

---

## Tasks / Subtasks

### Backend

- [x] Add `NarrativeCluster` schema to `backend/app/qa/schemas.py` (AC: 1, 2)
  - [x] Add `NarrativeCluster` model with `label`, `sentiment`, `post_count`, `representative_posts`
  - [x] Add `clusters: list[NarrativeCluster] = []` field to `QAResponse`

- [x] Add cluster grouping to `backend/app/qa/service.py` (AC: 2)
  - [x] After building `retrieved_posts`, group by `subtopic` (fallback to `topic` when subtopic is None)
  - [x] Build up to 4 clusters sorted by post count descending
  - [x] For each cluster: compute dominant sentiment, collect up to 2 representative posts
  - [x] Populate `qa_result.clusters` before returning

### Frontend

- [x] Wrap `<QAContent />` in `<Suspense>` in `frontend/app/(shell)/qa/page.tsx` (AC: 3)
  - [x] Required so `useSearchParams()` in `QAContent` does not break SSR/streaming in Next.js App Router

- [x] Read URL search params in `QAContent.tsx` on mount (AC: 3)
  - [x] Import `useSearchParams` from `next/navigation`
  - [x] On first render, if `?question=` param exists: set `question` state to its decoded value
  - [x] On first render, if `?topic=` param exists: set `qaFilters.topic` state to its decoded value
  - [x] If both `question` and `topic` params are present: also open the filter panel (`setFilterOpen(true)`)
  - [x] Only apply URL params once on mount (use `useEffect` with `[]` dep array)

- [x] Add `NarrativeClusterCard` section to answer panel in `QAContent.tsx` (AC: 1)
  - [x] Add `NarrativeCluster` TypeScript interface matching backend schema
  - [x] Add `clusters` field to `QAResponse` interface (`clusters: NarrativeCluster[]`)
  - [x] Render cluster section only when `result.clusters.length > 0`
  - [x] Section title: "Narrative Clusters"
  - [x] Render 2–4 `NarrativeClusterCard` components (cap at 4)
  - [x] Each card: cluster label, sentiment tag, post count, up to 2 representative post quotes

- [x] Add "→ Q&A" navigation to topic tiles in `TopicsPanel.tsx` (AC: 3)
  - [x] Import `useRouter` from `next/navigation`
  - [x] On each top-level topic tile row (not drill-down subtopics), add a small secondary button
  - [x] Button label: "Investigate →"
  - [x] On click: `router.push('/qa?topic=${item.name}&question=What+are+people+saying+about+${encodeURIComponent(item.label)}%3F')` — do NOT call `onTopicSelect` (that's for dashboard drill-down only)
  - [x] The primary tile click (`onClick={() => !isDrillDown && onTopicSelect(item.name)}`) must remain unchanged

- [x] Manual smoke test (AC: 1, 2, 3)
  - [x] Ask a broad question → clusters section appears with 2–4 cards, each showing label, sentiment, count, quotes
  - [x] Click "Investigate →" on a dashboard topic tile → navigates to `/qa` with `?topic=` and `?question=` pre-filled; question input auto-fills; filter panel opens showing that topic selected
  - [x] Click "Investigate →" on a spike alert → navigates to `/qa?topic=...&question=...` → QAContent pre-fills question and topic filter

---

## Developer Context

### CRITICAL: Next.js Version Warning

`frontend/AGENTS.md` warns:
> "This is NOT the Next.js you know. This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. **Read the relevant guide in `node_modules/next/dist/docs/` before writing any code.**"

---

### Backend: Schema Changes (`backend/app/qa/schemas.py`)

Add after the `QASubtopicSummary` class:

```python
class NarrativeCluster(BaseModel):
    """A group of thematically related posts representing a single narrative thread."""
    label: str                                  # subtopic_label, or topic_label if no subtopic
    sentiment: str                              # dominant sentiment: "positive" | "neutral" | "negative"
    post_count: int
    representative_posts: list[QAPostItem]      # up to 2 posts (most similar / top of cluster)
```

In `QAResponse`, add the `clusters` field (default empty — backward-compatible):

```python
class QAResponse(BaseModel):
    question: str
    filters_applied: QAFilters
    retrieved_posts: list[QAPostItem]
    metrics: QAMetrics
    insufficient_data: bool
    summary: str | None = None
    answer_error: str | None = None
    clusters: list[NarrativeCluster] = []       # ADD THIS — 2-4 narrative clusters (empty when insufficient_data)
```

---

### Backend: Clustering Logic (`backend/app/qa/service.py`)

Add cluster building after the `retrieved_posts` list is fully built (between Step 5 and Step 6 in the service). Insert before the `top_subtopics` block:

```python
# Step 5b: group posts into narrative clusters by subtopic (fallback to topic)
from collections import defaultdict as _dd  # already imported at top of file

cluster_groups: dict[str, list[QAPostItem]] = defaultdict(list)
for post in retrieved_posts:
    key = post.subtopic or post.topic  # subtopic preferred; fall back to topic
    cluster_groups[key].append(post)

clusters: list = []
for _key, posts in sorted(cluster_groups.items(), key=lambda x: len(x[1]), reverse=True)[:4]:
    sentiments = [p.sentiment for p in posts]
    dominant_sentiment = max(set(sentiments), key=sentiments.count)
    first = posts[0]
    cluster_label = first.subtopic_label or first.topic_label
    clusters.append(
        NarrativeCluster(
            label=cluster_label,
            sentiment=dominant_sentiment,
            post_count=len(posts),
            representative_posts=posts[:2],
        )
    )
```

Import `NarrativeCluster` at the top of `service.py` — add to the existing `from app.qa.schemas import (...)` block:
```python
from app.qa.schemas import (
    NarrativeCluster,      # ADD THIS
    QAFilters,
    QAMetrics,
    QAPostItem,
    QAResponse,
    QASubtopicSummary,
)
```

In the `return QAResponse(...)` at the bottom of the happy path, add `clusters=clusters`:
```python
return QAResponse(
    question=question,
    filters_applied=filters_applied,
    retrieved_posts=retrieved_posts,
    metrics=metrics,
    insufficient_data=False,
    clusters=clusters,          # ADD THIS
)
```

Note: The early-return paths (embedding failure, no rows) already use `insufficient_data=True` and don't pass `clusters` — they'll default to `[]`. No change needed there.

---

### Frontend: `qa/page.tsx` — Add Suspense Wrapper

`QAContent` will call `useSearchParams()`. In Next.js App Router, client components that call `useSearchParams()` must be wrapped in a `<Suspense>` boundary at the server-component boundary to avoid a hard error during static rendering.

Change `frontend/app/(shell)/qa/page.tsx` from:
```tsx
import QAContent from '@/components/qa/QAContent'

export default function QAPage() {
  return <QAContent />
}
```
To:
```tsx
import { Suspense } from 'react'
import QAContent from '@/components/qa/QAContent'

export default function QAPage() {
  return (
    <Suspense>
      <QAContent />
    </Suspense>
  )
}
```

No fallback UI is needed — `QAContent` renders immediately on client.

---

### Frontend: URL Params in `QAContent.tsx`

Add `useSearchParams` import:
```tsx
import { useSearchParams } from 'next/navigation'
```

Inside the component, add the hook and a mount-once effect:
```tsx
const searchParams = useSearchParams()

// Apply URL params on first mount (from SpikeAlertBanner or TopicsPanel navigation)
useEffect(() => {
  const questionParam = searchParams.get('question')
  const topicParam = searchParams.get('topic')
  if (questionParam) setQuestion(decodeURIComponent(questionParam))
  if (topicParam) {
    setQAFilters((f) => ({ ...f, topic: decodeURIComponent(topicParam) }))
    setFilterOpen(true)   // open filter panel so user sees the pre-set topic
  }
}, [])  // empty deps — intentionally run only on mount
```

**Important:** `useSearchParams` returns the CURRENT URL params object. The decoded values from `searchParams.get()` are already URL-decoded by Next.js — do NOT double-decode. The `encodeURIComponent` in the navigation callers (SpikeAlertBanner, TopicsPanel) is correct; `searchParams.get()` decodes them.

---

### Frontend: `NarrativeCluster` TypeScript Interface

Add to the type definitions block in `QAContent.tsx`:

```typescript
interface NarrativeCluster {
  label: string
  sentiment: string               // "positive" | "neutral" | "negative"
  post_count: number
  representative_posts: QAPostItem[]   // up to 2 items
}
```

Add `clusters` to `QAResponse`:
```typescript
interface QAResponse {
  // ... existing fields ...
  clusters: NarrativeCluster[]    // ADD THIS (2-4 items, or empty when insufficient_data)
}
```

---

### Frontend: `NarrativeClusterCard` Component

Add as an inline component in `QAContent.tsx` (same file, before `export default function QAContent`):

```tsx
function NarrativeClusterCard({ cluster }: { cluster: NarrativeCluster }) {
  return (
    <div className="rounded border border-border bg-surface p-4 flex flex-col gap-3">
      {/* Header: label + sentiment tag + post count */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="font-medium text-foreground [font-size:var(--font-size-body)]">
          {cluster.label}
        </span>
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${sentimentStyles(cluster.sentiment)}`}>
            {cluster.sentiment}
          </span>
          <span className="text-muted [font-size:var(--font-size-small)]">
            {cluster.post_count.toLocaleString()} posts
          </span>
        </div>
      </div>
      {/* Representative quotes */}
      {cluster.representative_posts.length > 0 && (
        <div className="flex flex-col gap-2">
          {cluster.representative_posts.map((post) => (
            <blockquote
              key={post.id}
              className="border-l-2 border-border pl-3 text-muted [font-size:var(--font-size-small)] [line-height:var(--line-height-body)] line-clamp-2"
            >
              {post.original_text}
            </blockquote>
          ))}
        </div>
      )}
    </div>
  )
}
```

Reuse the existing `sentimentStyles` function (already in `QAContent.tsx`) — do NOT redefine it.

---

### Frontend: Narrative Clusters Section in Answer Panel

In `renderAnswerArea()`, add the clusters section after the Evidence Posts block and before the scope label:

```tsx
{/* Narrative Clusters */}
{result.clusters.length > 0 && (
  <div className="flex flex-col gap-3">
    <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)]">
      Narrative Clusters
    </h3>
    <div className="grid grid-cols-1 gap-4">
      {result.clusters.slice(0, 4).map((cluster, i) => (
        <NarrativeClusterCard key={`${cluster.label}-${i}`} cluster={cluster} />
      ))}
    </div>
  </div>
)}
```

Note: `slice(0, 4)` guards against the backend returning more than 4 (though the backend caps at 4).

---

### Frontend: `TopicsPanel.tsx` — Add "Investigate →" Button

The topic tiles currently have a single `<button>` wrapping the entire tile content. To add a secondary "→ Q&A" action without changing the existing drill-down click behavior, add a second button INSIDE the tile row (right side, after the post count):

```tsx
// In the displayItems.map render, modify the returned button's inner content:
// BEFORE the post count span, add the investigate button (only for top-level, not drill-down)

import { useRouter } from 'next/navigation'

// Inside the component:
const router = useRouter()

// Inside the map, replace the tile button render with this pattern:
<div key={item.name} className={`w-full text-left rounded border border-border p-3 transition-colors ${!isDrillDown ? 'hover:border-primary hover:bg-surface' : ''}`}>
  <div className="flex items-center justify-between mb-1">
    <button
      type="button"
      onClick={() => !isDrillDown && onTopicSelect(item.name)}
      disabled={isDrillDown}
      className={`flex-1 text-left ${!isDrillDown ? 'cursor-pointer' : 'cursor-default'}`}
    >
      <span className="font-medium text-foreground [font-size:var(--font-size-body)]">
        {item.label}
      </span>
    </button>
    <div className="flex items-center gap-2">
      {/* badges */}
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
      {/* Q&A investigate button — top-level only */}
      {!isDrillDown && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            const q = encodeURIComponent(`What are people saying about ${item.label}?`)
            router.push(`/qa?topic=${encodeURIComponent(item.name)}&question=${q}`)
          }}
          className="px-2 py-0.5 rounded border border-border text-muted hover:text-foreground hover:border-primary [font-size:var(--font-size-small)] whitespace-nowrap"
        >
          Investigate →
        </button>
      )}
    </div>
  </div>
  {/* Sentiment bar — unchanged */}
  <div className="flex h-1.5 rounded overflow-hidden gap-px">
    {posW > 0 && <div className="bg-sentiment-positive" style={{ width: `${posW}%` }} />}
    {neuW > 0 && <div className="bg-muted" style={{ width: `${neuW}%` }} />}
    {negW > 0 && <div className="bg-sentiment-negative" style={{ width: `${negW}%` }} />}
  </div>
</div>
```

**CRITICAL:** `e.stopPropagation()` on the "Investigate →" click prevents bubbling to the outer tile. The outer tile's `onTopicSelect` must NOT fire when clicking "Investigate →" (they are separate actions).

**Existing tile `onClick`** (`!isDrillDown && onTopicSelect(item.name)`) is currently on the wrapping `<button>`. Refactor: make the outer container a `<div>` and move the drill-down click onto the label button only. The sentiment bar remains non-interactive.

---

### Frontend: `SpikeAlertBanner` — No Changes Needed

`SpikeAlertBanner` already navigates to `/qa?topic=${t}&question=${q}` (lines 125–128). Once `QAContent` reads these params, the spike alert → Q&A flow is complete with no further changes to `SpikeAlertBanner`.

---

### Styling Conventions

Reuse all existing Tailwind tokens — no new colors or utilities:
- `NarrativeClusterCard`: `rounded border border-border bg-surface p-4` — same as `EvidencePostCard`
- Representative quotes: `border-l-2 border-border pl-3` left-border style
- `sentimentStyles()` function already in `QAContent.tsx` — reuse for cluster sentiment tag

---

### Previous Story Intelligence (from Stories 3.1–3.4)

- **No automated tests** in Epic 3 — manual smoke test only. Do NOT create test files.
- **No shared fetch utility** — components call `fetch()` directly.
- **`useCallback` dep arrays** — after adding `useSearchParams`, make sure `handleSubmit`'s dep array does not need updating (it reads `question` and `qaFilters` from state, not from URL params — so no change).
- **AbortController** — existing cleanup is unchanged.
- **Deferred from 3.3 review**: "SpikeAlertBanner URL params ignored by QAContent" — this story closes that deferred item.
- **`QAResponse.filters_applied`** is already typed correctly in `QAContent.tsx` and includes `subtopic` (added in 3.4).
- **`TopicsPanel`** currently calls `onTopicSelect` for drill-down. The refactor to add "Investigate →" must preserve this callback — it is still used by `DashboardContent.tsx` to set the `FilterState.topic`.

---

### Git Intelligence

From recent commits:
- Inline sub-components (like `EvidencePostCard`, `MetricsStrip`) are defined in `QAContent.tsx` — add `NarrativeClusterCard` the same way
- Backend schema additions use Pydantic `BaseModel` — no DB migrations (clusters are computed from existing data, not stored)
- `page.tsx` files are thin server-component shells — any change should remain minimal (Suspense wrapper only)
- `TopicsPanel.tsx` is a self-contained client component — `useRouter` import is already used in `SpikeAlertBanner.tsx` at the same path level

---

### Testing / Validation

No automated tests. Validate manually:

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. **AC1 (Cluster Cards):** Navigate to `http://localhost:3000/qa`, ask "What are the main negative narratives?" → answer panel shows "Narrative Clusters" section with 2–4 cards; each card has a label, sentiment chip, post count, and 1–2 quoted lines
4. **AC2 (Clustering):** Inspect Network tab → `POST /qa` response includes `clusters` array; each cluster has `label`, `sentiment`, `post_count`, `representative_posts`
5. **AC3 — TopicsPanel:** Navigate to `http://localhost:3000/dashboard` → each topic tile shows "Investigate →" button; click it → navigates to `/qa?topic=...&question=...`; Q&A page loads with question pre-filled and filter panel open showing the topic
6. **AC3 — SpikeAlertBanner:** (If spikes exist) Click "Investigate →" on a spike → `/qa` loads with question and topic pre-filled from spike's `suggested_question` and `topic`
7. **AC3 — No params:** Navigate directly to `/qa` with no params → question input is empty, no filters active (normal state unaffected)

---

## Dev Agent Record

### Agent Model Used
kimi-k2.5:cloud

### Debug Log References

### Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-04-08 | Initial implementation | Story 3.5 - Narrative Clusters & Rapid Response Investigation |

### Completion Notes List

- ✅ Added `NarrativeCluster` Pydantic model to `backend/app/qa/schemas.py` with fields: label, sentiment, post_count, representative_posts
- ✅ Added `clusters: list[NarrativeCluster] = []` to `QAResponse` for backward compatibility
- ✅ Implemented cluster grouping logic in `backend/app/qa/service.py` - groups posts by subtopic (fallback to topic), builds up to 4 clusters sorted by post count, computes dominant sentiment, collects up to 2 representative posts per cluster
- ✅ Wrapped `QAContent` in `<Suspense>` in `frontend/app/(shell)/qa/page.tsx` to support `useSearchParams()`
- ✅ Added `useSearchParams` hook to `QAContent.tsx` with mount effect to read `?question=` and `?topic=` URL params
- ✅ URL params auto-fill question input and topic filter, and open filter panel when topic param is present
- ✅ Added `NarrativeCluster` TypeScript interface and updated `QAResponse` interface with `clusters` field
- ✅ Created `NarrativeClusterCard` component with label, sentiment tag, post count, and representative quotes
- ✅ Added Narrative Clusters section to answer panel (renders after Evidence Posts)
- ✅ Refactored `TopicsPanel.tsx` tile structure - outer container is now `<div>`, label is a separate `<button>` for drill-down
- ✅ Added "Investigate →" button to top-level topic tiles that navigates to `/qa?topic=...&question=...` with pre-filled question
- ✅ Used `e.stopPropagation()` to prevent drill-down when clicking Investigate button

### File List

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/app/qa/schemas.py` | Modify | Add `NarrativeCluster` model; add `clusters` field to `QAResponse` |
| `backend/app/qa/service.py` | Modify | Add cluster grouping logic; populate `clusters` in response |
| `frontend/app/(shell)/qa/page.tsx` | Modify | Wrap `<QAContent />` in `<Suspense>` |
| `frontend/components/qa/QAContent.tsx` | Modify | Add `useSearchParams`, URL param mount effect, `NarrativeCluster` types, `NarrativeClusterCard`, clusters section in answer panel |
| `frontend/components/dashboard/TopicsPanel.tsx` | Modify | Add "Investigate →" button to top-level topic tiles; import `useRouter` |

### Review Findings

- [x] [Review][Patch] Double-decoding URL params — `QAContent.tsx` uses `decodeURIComponent(searchParams.get('question'))` but `searchParams.get()` already decodes values. Remove `decodeURIComponent()` calls. Spec explicitly warns: "searchParams.get() already decodes values — do NOT double-decode."
- [x] [Review][Patch] `cluster_label` can be `None` — In `service.py`, `first.subtopic_label or first.topic_label` can yield `None` if both are null, violating the `str` type on `NarrativeCluster.label`. Use the grouping key as ultimate fallback.
- [x] [Review][Patch] Grouping key/label fallback mismatch — Posts are grouped by `post.subtopic or post.topic` (short IDs) but labeled by `first.subtopic_label or first.topic_label` (display names). If subtopic exists but subtopic_label is null, the label falls back to topic_label describing a different (broader) group. Ensure label matches what the group was keyed on.
- [x] [Review][Patch] `max()` O(n²) sentiment computation — `max(set(sentiments), key=sentiments.count)` is O(n²). Use `collections.Counter` for O(n).
- [x] [Review][Patch] Weak type annotation on `clusters` — `clusters: list = []` in `service.py` should be `clusters: list[NarrativeCluster] = []` for type safety.
- [x] [Review][Patch] `useEffect` empty deps → stale state on client-side nav — resolved: add `searchParams` to deps so URL param changes trigger re-read.
- [x] [Review][Patch] Button label "Investigate →" vs spec "→ Q&A" — resolved: changed to "→ Q&A" per spec.
- [x] [Review][Patch] No minimum-cluster guard (AC1 says 2-4) — resolved: changed condition from `clusters.length > 0` to `clusters.length >= 2`.
