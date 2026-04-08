# Story 3.3: Q&A Frontend — Question Input & Insight Summary Panel

**Status:** done
**Epic:** 3 — LLM-Powered Q&A Intelligence Interface
**Story ID:** 3.3
**Story Key:** 3-3-qa-frontend-question-input-insight-summary-panel
**Created:** 2026-04-08

---

## Story

As a campaign, communications, or analyst user,
I want a prominent question input with preset suggestions and a structured answer panel showing summary, metrics, and evidence posts,
So that I can ask political questions and immediately understand the grounded answer without leaving the app.

---

## Acceptance Criteria

1. **Given** the user opens the Q&A view
   **When** the page renders
   **Then** a prominent text input is visible with placeholder text and 3–5 preset suggestion chips (e.g. "What's spiking?", "How are we doing on housing vs Party X?", "Main negative narratives about our leader?")

2. **Given** the user types a question and submits
   **When** the request is in flight
   **Then** a loading state ("Analyzing discourse…") replaces the answer area with a visible indicator that does not obscure the question input

3. **Given** a successful Q&A response is received
   **When** the answer renders
   **Then** the Insight Summary Panel shows: (1) the narrative summary, (2) key metrics strip (post count, sentiment breakdown), (3) a grid of up to 5 Evidence Post Cards
   **And** a label like "Based on 1,234 posts · Last 7 days" is visible so users understand the scope

4. **Given** the user has received an answer
   **When** the user types a new question and submits
   **Then** the previous answer is replaced with the new answer without a page reload, and question history is not required to be preserved

---

## Scope for Story 3.3

**IN SCOPE:**
- Question text input + submit button
- Preset suggestion chips (click to fill input)
- Loading state while POST /qa is in flight
- Insight Summary Panel: summary text, metrics strip, up to 5 Evidence Post Cards
- Scope label ("Based on X posts · …")
- Error and empty/insufficient-data states
- Replace previous answer on new submission

**OUT OF SCOPE (future stories):**
- Filter controls (topic, party, time range, platform) — Story 3.4
- Narrative Cluster Cards — Story 3.5
- Clickable dashboard tiles pre-filling the question — Story 3.5
- Multi-session question history — explicitly not required (FR18)

---

## Tasks / Subtasks

- [x] Update `frontend/app/(shell)/qa/page.tsx` to import and render `<QAContent />` (AC: all)
  - [x] Replace placeholder with `import QAContent from '@/components/qa/QAContent'` pattern matching `dashboard/page.tsx`

- [x] Create `frontend/components/qa/QAContent.tsx` — main Q&A client component (AC: 1, 2, 3, 4)
  - [x] Question input with placeholder and submit button
  - [x] 3–5 preset suggestion chips: "What's spiking?", "How are we doing on housing vs Party X?", "Main negative narratives about our leader?"
  - [x] `POST /qa` fetch call using `process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'`
  - [x] Loading state renders "Analyzing discourse…" in the answer area
  - [x] Insight Summary Panel rendered after successful response
  - [x] Replace previous answer on new submission (no history)
  - [x] Handle `insufficient_data: true` — show plain-language empty state
  - [x] Handle `answer_error` — show degradation message with metrics/posts still shown
  - [x] Handle network/API error — show plain-language error state

- [x] Validate (AC: 1, 2, 3, 4)
  - [x] Start backend + frontend; navigate to `/qa`
  - [x] Page renders with question input and preset chips
  - [x] Click a preset chip → fills question input
  - [x] Submit question → "Analyzing discourse…" loading indicator appears; question input remains visible
  - [x] Response renders: summary paragraph, metrics strip, up to 5 Evidence Post Cards, scope label
  - [x] Submit a second question → previous answer replaced without page reload
  - [x] Simulate `insufficient_data` → appropriate empty-state message shown
  - [x] Simulate LLM failure (bad OPENAI_API_KEY) → `answer_error` message + posts/metrics shown; no crash

---

## Developer Context

### CRITICAL: Next.js Version Warning

`frontend/AGENTS.md` explicitly warns:
> "This is NOT the Next.js you know. This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. **Read the relevant guide in `node_modules/next/dist/docs/` before writing any code.**"

Before writing any Next.js code, check `frontend/node_modules/next/dist/docs/` for current API behavior. The App Router conventions used in this codebase may differ from your training data.

---

### File Structure Pattern

Follow the established dashboard pattern exactly:

```
frontend/app/(shell)/qa/page.tsx          ← server component (thin shell, already exists — replace placeholder)
frontend/components/qa/QAContent.tsx      ← NEW: main 'use client' component
```

**`qa/page.tsx` must match `dashboard/page.tsx` pattern:**
```tsx
import QAContent from '@/components/qa/QAContent'

export default function QAPage() {
  return <QAContent />
}
```

**Do NOT** put 'use client' logic directly in the page file. Keep it in the component.

---

### API Contract — `POST /qa`

Endpoint: `POST {API_BASE}/qa`

**Request body:**
```typescript
interface QARequest {
  question: string          // required, non-empty
  filters?: {               // ALL optional — Story 3.3 sends no filters (filters are Story 3.4)
    topic?: string
    party?: string          // maps to ProcessedPost.target internally
    start_date?: string     // "YYYY-MM-DD"
    end_date?: string       // "YYYY-MM-DD"
    platform?: string
  }
  top_n?: number            // default 20, max 50
}
```

**Response body:**
```typescript
interface QAResponse {
  question: string
  filters_applied: {
    topic: string | null
    party: string | null
    start_date: string | null
    end_date: string | null
    platform: string | null
  }
  retrieved_posts: QAPostItem[]
  metrics: {
    total_retrieved: number
    positive_count: number
    neutral_count: number
    negative_count: number
    top_subtopics: Array<{ subtopic: string; subtopic_label: string; count: number }>
  }
  insufficient_data: boolean    // true = no posts matched; skip LLM was called
  summary: string | null        // LLM narrative (null if skipped or failed)
  answer_error: string | null   // degradation message (null unless LLM failed)
}

interface QAPostItem {
  id: string
  original_text: string
  platform: string
  created_at: string     // "YYYY-MM-DD"
  sentiment: string      // "positive" | "neutral" | "negative"
  topic: string
  topic_label: string
  subtopic: string | null
  subtopic_label: string | null
  author: string | null
  target: string | null
  intensity: float | null
  similarity_score: float
}
```

**Story 3.3 sends no filters** — the `filters` field should be omitted or `undefined` in requests. Filter UI is Story 3.4.

---

### Styling Conventions (MUST follow)

All existing components use these Tailwind design tokens — do not invent new ones:

**Colors:**
- `text-foreground` — primary text
- `text-muted` — secondary/placeholder text
- `text-primary` — accent (links, active actions)
- `text-sentiment-positive` — positive sentiment label color
- `text-sentiment-negative` — negative sentiment label color
- `bg-surface` — page background
- `bg-surface-raised` — card/panel background
- `border-border` — standard border color
- `bg-sentiment-positive/10` — positive sentiment chip background
- `bg-sentiment-negative/10` — negative sentiment chip background
- `bg-muted/10` — neutral sentiment chip background

**Typography CSS variables (use `[font-size:var(--font-size-X)]` syntax):**
- `[font-size:var(--font-size-h2)] [line-height:var(--line-height-h2)]` — section headings
- `[font-size:var(--font-size-h4)]` — panel headings
- `[font-size:var(--font-size-body)] [line-height:var(--line-height-body)]` — body text
- `[font-size:var(--font-size-small)]` — metadata, chips, labels

**Layout:**
- Shell layout wraps all page content in `grid grid-cols-12 gap-6 p-6`
- Top-level divs inside components must use `col-span-12` (or narrower) to fit the grid
- Panels: `bg-surface-raised rounded-lg border border-border p-4`
- Cards: `rounded border border-border bg-surface p-4 flex flex-col gap-2`

---

### Evidence Post Card

Story 3.3 needs Evidence Post Cards for Q&A. **Do NOT reuse `PostCard` from `PostsPanel.tsx`** — that component expects `PostItem` from the analytics endpoint (different interface, different fields). The Q&A post is `QAPostItem` (has `target`, `intensity`, `similarity_score`; lacks `source`).

Implement a simple `EvidencePostCard` inline in `QAContent.tsx` or as a separate component in `components/qa/`:

```typescript
// QAPostItem shape (from backend/app/qa/schemas.py)
interface QAPostItem {
  id: string
  original_text: string
  platform: string
  created_at: string        // "YYYY-MM-DD"
  sentiment: string         // "positive" | "neutral" | "negative"
  topic_label: string
  subtopic_label: string | null
}
```

Render sentiment chip using same pattern as `PostCard`:
```tsx
function sentimentStyles(sentiment: string) {
  switch (sentiment) {
    case 'positive': return 'text-sentiment-positive bg-sentiment-positive/10'
    case 'negative': return 'text-sentiment-negative bg-sentiment-negative/10'
    default:         return 'text-muted bg-muted/10'
  }
}
```

**Show up to 5 posts** from `retrieved_posts` (slice first 5).

---

### Metrics Strip

The metrics strip should show `total_retrieved`, `positive_count`, `neutral_count`, `negative_count` from `metrics`. Display as a compact horizontal strip of labeled counts.

**Scope label pattern:** "Based on {total_retrieved.toLocaleString()} posts" — the "Last N days" part is not possible in 3.3 since no date filters are sent; keep it as "Based on {N} posts" or "Based on {N} posts · all time" for now.

---

### Loading & Error States

- **Loading:** Replace answer area with text "Analyzing discourse…" — question input must remain visible and enabled
- **Insufficient data:** `if (response.insufficient_data)` → show "Not enough data to answer this question. Try a broader question." (UX-DR14 pattern)
- **LLM degradation:** `if (response.answer_error)` → show `answer_error` message as a warning banner, then still render metrics and evidence posts below it (`summary` will be null, skip the summary section)
- **Network error:** show "Unable to reach the server. Check that the backend is running."

---

### Preset Suggestion Chips

Render as clickable buttons that set the question input value:
```tsx
const PRESET_QUESTIONS = [
  "What's spiking?",
  "How are we doing on housing vs Party X?",
  "Main negative narratives about our leader?",
  "Which topics have the most negative sentiment?",
]
```

On click: set question state to the preset text. Do not auto-submit — let user review/modify before submitting (matches UX-DR11 "reduce blank-page anxiety").

---

### State Management Pattern

Follow `DashboardContent.tsx` and `PostsPanel.tsx` patterns:

```tsx
'use client'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

export default function QAContent() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QAResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  // ...
}
```

Use AbortController for fetch cleanup (see `PostsPanel.tsx` pattern). On new submission, cancel any in-flight request.

---

### Previous Story Intelligence (from Stories 3.1 & 3.2)

- **`POST /qa` endpoint** is registered under prefix `/qa` in `backend/app/main.py`. Fetch URL: `${API_BASE}/qa` with POST and `Content-Type: application/json`.
- **Schema fields:** `summary` and `answer_error` are optional strings defaulting to `null`. Always check `if (result.insufficient_data)` first, then `if (result.answer_error)` for degraded responses.
- **No test files added** for any Epic 3 story — manual smoke test only. Do not create test files.
- The frontend has **no shared API client or fetch utility** — each component calls `fetch()` directly (same pattern as `DashboardContent.tsx`, `PostsPanel.tsx`, etc.).

---

### Git Intelligence

From recent commits:
- New frontend components created in `frontend/components/[feature]/ComponentName.tsx`
- New feature directories created when needed (e.g. `components/dashboard/`, `components/charts/`)
- New `components/qa/` directory will be needed — create it
- All new components follow `'use client'` where state is needed
- `page.tsx` files are thin server shells that import from `components/`

---

### Testing / Validation

No automated tests. Validate manually:

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to `http://localhost:3000/qa`
4. **AC1:** Question input visible with preset chips
5. **AC1:** Click chip → input fills with preset text
6. **AC2:** Type question, submit → "Analyzing discourse…" appears; input still visible
7. **AC3:** On success: summary paragraph, metrics strip, up to 5 Evidence Post Cards, scope label rendered
8. **AC4:** Submit second question → answer area replaces without reload
9. **Insufficient data:** Submit "xyzzy irrelevant nonsense topic 99999" → empty state message
10. **LLM degradation:** Set `OPENAI_API_KEY=invalid` in backend env → restart backend → submit valid question → `answer_error` message shown + posts and metrics still rendered

---

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Change Log

| Date | Change | Reason |
|------|--------|--------|

### Completion Notes List

- Implemented QAContent component with question input, preset suggestion chips, loading state, and Insight Summary Panel
- Created EvidencePostCard component inline for Q&A-specific post display
- Implemented MetricsStrip component showing post counts and sentiment breakdown
- Handled all error states: insufficient_data, answer_error, and network errors
- Followed existing codebase patterns from DashboardContent.tsx and PostsPanel.tsx
- Used Tailwind design tokens and CSS variables as specified in Dev Notes

### File List

| File | Change Type | Description |
|------|-------------|-------------|
| `frontend/app/(shell)/qa/page.tsx` | Modify | Replace placeholder with `<QAContent />` import |
| `frontend/components/qa/QAContent.tsx` | Create | Main Q&A client component |

### Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-04-08 | Created QAContent component | Implement story 3.3 requirements |
| 2026-04-08 | Updated qa/page.tsx | Integrate QAContent into shell layout |

### Review Findings

**Decision-needed (resolved):**

- [x] [Review][Decision] Disabled input prevents abort-on-new-submission → Resolved: enable input during loading, keep submit button disabled, show "Analyzing…" on button
- [x] [Review][Decision] answer_error styled as error (red) instead of warning → Resolved: switched to `text-sentiment-warning bg-sentiment-warning/10 border-sentiment-warning/30` (amber)

**Patch (all fixed):**

- [x] [Review][Patch] Abort race condition: loading flickers on re-submit → Fixed: guard `setLoading` with identity check on AbortController
- [x] [Review][Patch] Server error details discarded / misleading error messages → Fixed: separate try/catch for `response.json()` with descriptive error
- [x] [Review][Patch] No AbortController cleanup on component unmount → Fixed: added `useEffect` cleanup
- [x] [Review][Patch] ASCII ellipsis "..." vs Unicode "…" in loading text → Fixed: replaced with Unicode ellipsis `…`
- [x] [Review][Patch] EvidencePostCard renders full text with no truncation → Fixed: added `line-clamp-3`
- [x] [Review][Patch] No input length limit → Fixed: added `maxLength={500}`
- [x] [Review][Patch] handleKeyDown not memoised → Fixed: wrapped in `useCallback`
- [x] [Review][Patch] response.json() can throw SyntaxError on non-JSON body → Fixed: added try/catch around `response.json()`
- [x] [Review][Patch] Preset question "Party X" is placeholder text → Fixed: replaced with real example text

**Defer:**

- [x] [Review][Defer] SpikeAlertBanner URL params ignored by QAContent — deferred, Story 3.5 scope
- [x] [Review][Defer] Frontend never sends filters/top_n — deferred, Story 3.4 scope
- [x] [Review][Defer] NEXT_PUBLIC_API_BASE_URL fallback to localhost — deferred, established codebase pattern
- [x] [Review][Defer] Render path with no summary and no answer_error — deferred, not practically reachable with current backend
- [x] [Review][Defer] Sentiment type mismatch (frontend union vs backend str) — deferred, speculative about future backend changes
- [x] [Review][Defer] filters_applied not rendered — deferred, not required by Story 3.3 spec
- [x] [Review][Defer] insufficient_data hides metrics/posts — deferred, backend returns empty data in this case
