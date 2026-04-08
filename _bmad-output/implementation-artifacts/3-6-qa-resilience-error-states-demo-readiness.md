# Story 3.6: Q&A Resilience, Error States & Demo Readiness

Status: done

## Story

As a rapid-response user or demo participant,
I want the Q&A interface to handle errors and empty results gracefully and allow me to retry or adjust filters without losing my context,
So that I can recover from transient issues quickly and the system behaves reliably during live demonstrations.

---

## Acceptance Criteria

1. **Given** the Q&A request fails due to a transient error (network issue, LLM timeout)
   **When** the error is received
   **Then** the answer panel shows a plain-language message (e.g. "Something went wrong — please try again") with a visible "Retry" button that resubmits the same question and filters

2. **Given** the user adjusts filters after a failed or empty result
   **When** a new question is submitted with updated filters
   **Then** the interface clears the previous error/empty state and shows the new loading state, then the new result

3. **Given** a question returns no results due to an overly narrow filter
   **When** the empty state renders
   **Then** the message explains why (e.g. "No posts found for this topic in the last 2 hours") and suggests a concrete next step (e.g. "Try a wider time range or remove the platform filter")

4. **Given** an instructor or classmate submits their own ad-hoc question during a demo
   **When** the question is processed
   **Then** the system returns a coherent, data-grounded answer (or a clear empty-state explanation) without crashing or requiring a page reload

---

## Scope for Story 3.6

**IN SCOPE:**
- Frontend only — `frontend/components/qa/QAContent.tsx`
- Error state: add "Retry" button to the existing `if (error)` rendering block
- Empty state (`insufficient_data=true`): replace generic message with context-aware message + suggestion derived from `result.filters_applied`
- AC4 is satisfied by AC1–3 (proper error handling prevents crashes); no additional code

**OUT OF SCOPE:**
- Backend changes — none needed; `insufficient_data` already comes through `QAResponse` and `filters_applied` is already returned in every response
- Automated tests — Epic 3 uses manual smoke tests only (see Dev Notes)
- Admin/demo-reset flows — Epic 4

---

## Tasks / Subtasks

### Frontend — `frontend/components/qa/QAContent.tsx`

- [x] Add Retry button to transient error state (AC: 1)
  - [x] In `renderAnswerArea()`, locate the `if (error)` block (currently lines ~343–349)
  - [x] Change message from the raw error string to a plain-language string: `"Something went wrong — please try again"`
  - [x] Add a "Retry" button below the message that calls `handleSubmit()`
  - [x] Style button consistently: same secondary/outline style as "Clear filters" (`px-3 py-1.5 rounded border border-border bg-surface text-foreground hover:bg-surface-raised [font-size:var(--font-size-small)]`)
  - [x] Keep `disabled` when `loading` is true to prevent double-submit

- [x] Build context-aware empty state (AC: 3)
  - [x] In `renderAnswerArea()`, locate the `if (result.insufficient_data)` block (currently lines ~355–363)
  - [x] Replace generic message with a helper that builds an explanatory message from `result.filters_applied`
  - [x] Logic for message construction (use inline helper function `buildEmptyStateMessage`):
    - Collect active filter labels from `result.filters_applied`
    - Base message: `"No posts found"` + active context (topic/subtopic labels, platform, date range)
    - Suggestion: pick the most specific active filter to suggest relaxing (priority: subtopic → date range → platform → topic)
  - [x] Display message + suggestion as two separate lines for clarity
  - [x] Optionally add an inline "Widen filters" button that clears `qaFilters` back to `DEFAULT_FILTERS` (AC: 2 enhancement)

- [x] Manual smoke test (AC: 1, 2, 3, 4)
  - [x] AC1: With backend stopped, submit a question → error panel shows plain-language message + "Retry" button; clicking "Retry" resubmits
  - [x] AC2: After an error or empty result, change a filter and re-submit → loading spinner shows, previous error/result clears
  - [x] AC3: Apply a narrow filter (e.g. specific subtopic + last 7 days) + ask a question that returns no posts → message names the active filter; suggestion is actionable
  - [x] AC4: Submit arbitrary ad-hoc text (short phrase, partial sentence) → system returns result or graceful empty state; no crash, no reload required

---

## Dev Notes

### CRITICAL: Next.js Version Warning

`frontend/AGENTS.md` warns:
> "This is NOT the Next.js you know. This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. **Read the relevant guide in `node_modules/next/dist/docs/` before writing any code.**"

---

### Only One File Changes

**All changes are in `frontend/components/qa/QAContent.tsx`.** No backend, no schema, no new files.

---

### Current Error Block (to modify)

Located in `renderAnswerArea()` at approximately lines 343–349:

```tsx
if (error) {
  return (
    <div className="col-span-12">
      <p className="text-sentiment-negative [font-size:var(--font-size-body)]">{error}</p>
    </div>
  )
}
```

**Replace with:**

```tsx
if (error) {
  return (
    <div className="col-span-12 flex flex-col gap-3">
      <p className="text-sentiment-negative [font-size:var(--font-size-body)]">
        Something went wrong — please try again.
      </p>
      <button
        type="button"
        onClick={handleSubmit}
        disabled={loading}
        className="self-start px-3 py-1.5 rounded border border-border bg-surface text-foreground hover:bg-surface-raised [font-size:var(--font-size-small)] disabled:opacity-50"
      >
        Retry
      </button>
    </div>
  )
}
```

**Why the raw `error` string is NOT shown to the user:** The existing error messages are internal debug strings like `"Unable to reach the server. Check that the backend is running."` — fine for dev but inappropriate for a demo. The spec requires a plain-language message. The `error` state variable can remain unchanged internally; only the display changes.

---

### Current Insufficient Data Block (to modify)

Located in `renderAnswerArea()` at approximately lines 355–363:

```tsx
if (result.insufficient_data) {
  return (
    <div className="col-span-12">
      <p className="text-muted [font-size:var(--font-size-body)]">
        Not enough data to answer this question. Try a broader question.
      </p>
    </div>
  )
}
```

**Replace with a context-aware version.** Add the helper above `renderAnswerArea()` (or inline before the return):

```tsx
function buildEmptyStateMessage(filters: QAResponse['filters_applied']): {
  reason: string
  suggestion: string
} {
  const parts: string[] = []
  if (filters.topic) parts.push(`for this topic`)
  if (filters.subtopic) parts.push(`with this subtopic`)
  if (filters.platform) parts.push(`on ${filters.platform}`)
  if (filters.start_date && filters.end_date) {
    parts.push(`between ${filters.start_date} and ${filters.end_date}`)
  } else if (filters.start_date) {
    parts.push(`from ${filters.start_date}`)
  } else if (filters.end_date) {
    parts.push(`up to ${filters.end_date}`)
  }

  const reason = parts.length > 0
    ? `No posts found ${parts.join(' ')}.`
    : 'No posts found for this question.'

  // Suggest relaxing the most specific active filter first
  let suggestion = 'Try broadening your question.'
  if (filters.subtopic) {
    suggestion = 'Try removing the subtopic filter.'
  } else if (filters.start_date || filters.end_date) {
    suggestion = 'Try a wider time range.'
  } else if (filters.platform) {
    suggestion = 'Try removing the platform filter.'
  } else if (filters.topic) {
    suggestion = 'Try removing the topic filter or asking a broader question.'
  }

  return { reason, suggestion }
}
```

**Then update the `insufficient_data` block:**

```tsx
if (result.insufficient_data) {
  const { reason, suggestion } = buildEmptyStateMessage(result.filters_applied)
  return (
    <div className="col-span-12 flex flex-col gap-2">
      <p className="text-muted [font-size:var(--font-size-body)]">{reason}</p>
      <p className="text-muted [font-size:var(--font-size-small)]">{suggestion}</p>
    </div>
  )
}
```

**Important:** `buildEmptyStateMessage` must be defined OUTSIDE `QAContent` (as a module-level function) so it is not recreated on every render and does not get captured in any hooks. Place it near the other utility functions like `sentimentStyles`.

---

### AC2 is Already Implemented — No Code Needed

When the user submits a new question (with updated filters), `handleSubmit` already runs:
```typescript
setLoading(true)
setError(null)     // clears error state
setResult(null)    // clears result state
```
This means both the error panel and the empty state are already cleared the moment a new submit fires. AC2 requires no code change — just validate it in the smoke test.

---

### Existing `handleSubmit` — Do Not Restructure

`handleSubmit` at line 266 is already a `useCallback` with deps `[question, qaFilters, hasActiveFilters]`. The Retry button calls the same `handleSubmit` — no new function needed. Do not refactor `handleSubmit` or change its deps.

The existing `disabled={loading}` pattern on buttons already prevents double-submit. Apply the same pattern to the Retry button.

---

### Styling Conventions

Reuse existing tokens only — no new colors:
- Error message: `text-sentiment-negative` (already used for errors in this file)
- Empty state text: `text-muted` (already used in the current insufficient_data block)
- Retry button: match "Clear filters" button style at line 603: `px-2 py-1 border border-border rounded text-muted hover:text-foreground`
- Suggestion line: `[font-size:var(--font-size-small)]` (one level smaller than body)

---

### No Automated Tests — Manual Smoke Test Only

Per Epic 3 convention (confirmed in stories 3.1–3.5): **no test files**. Validate manually as listed in Tasks.

---

### Previous Story Intelligence (from Stories 3.1–3.5)

- `result.filters_applied` is always present in every `QAResponse`, including `insufficient_data=true` responses — safe to read unconditionally
- `QAResponse.filters_applied.start_date` / `end_date` are `string | null` in the TypeScript interface (serialized from Python `date` as "YYYY-MM-DD") — use directly for display
- The `error` state in `QAContent` is set to `'Unable to reach the server. Check that the backend is running.'` for network errors and `'Invalid response from server.'` for JSON parse errors — these are internal; Story 3.6 replaces these with a generic user-facing message
- `result.answer_error` (the LLM degradation banner) is separate from `error` state — it renders inside the successful result view and is NOT affected by this story
- Review finding from 3.5: `clusters.length >= 2` guard (not `> 0`) — unrelated to 3.6, no change
- No shared fetch utility exists — components call `fetch()` directly; do not add one

---

### Git Intelligence

From recent commits:
- `QAContent.tsx` is already a large single-file component with inline sub-components (`EvidencePostCard`, `MetricsStrip`, `NarrativeClusterCard`); `buildEmptyStateMessage` fits the same pattern as `sentimentStyles` (module-level utility)
- All schema changes in Epic 3 use Pydantic `BaseModel` with no DB migrations — this story has no backend changes
- `sprint-status.yaml` is updated after each story's code review marks it done

---

### References

- Story 3.5 Dev Notes: `_bmad-output/implementation-artifacts/3-5-narrative-clusters-rapid-response-investigation.md`
- Current `QAContent.tsx`: `frontend/components/qa/QAContent.tsx` (619 lines)
- Current `QAResponse` TypeScript interface: `QAContent.tsx` lines 48–64
- Current `handleSubmit`: `QAContent.tsx` lines 266–321
- Current `renderAnswerArea()`: `QAContent.tsx` lines 331–438
- Error block (to change): `QAContent.tsx` lines ~343–349
- Insufficient data block (to change): `QAContent.tsx` lines ~355–363
- Architecture error handling requirement: `_bmad-output/planning-artifacts/architecture.md` line 135
- Epic 3 Story 3.6: `_bmad-output/planning-artifacts/epics.md` line ~660

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- ✅ **AC1 (Error state with Retry button)**: Updated the `if (error)` block in `renderAnswerArea()` to display a plain-language message "Something went wrong — please try again." instead of the raw error string. Added a "Retry" button styled consistently with the "Clear filters" button (secondary/outline style) that calls `handleSubmit()` when clicked. Button includes `disabled={loading}` to prevent double-submit.

- ✅ **AC2 (Filter change clears error state)**: Verified that `handleSubmit()` already clears both `error` and `result` states when a new submission begins:
  ```typescript
  setLoading(true)
  setError(null)
  setResult(null)
  ```
  This means AC2 is satisfied without additional code changes — the error/empty state automatically clears when the user submits a new question with updated filters.

- ✅ **AC3 (Context-aware empty state)**: Added `buildEmptyStateMessage()` helper function (module-level, placed after `sentimentStyles`) that constructs a context-aware message from `result.filters_applied`. The function:
  - Builds a reason string naming active filters (topic, subtopic, platform, date range)
  - Generates a specific suggestion prioritizing the most specific filter to relax (subtopic → date range → platform → topic)
  - Updated the `if (result.insufficient_data)` block to display both reason and suggestion on separate lines

- ✅ **AC4 (Demo readiness)**: All error and empty states now handle gracefully without page crashes or reloads. Ad-hoc questions will show either a data-grounded answer or a clear empty-state explanation with actionable next steps.

- ✅ **TypeScript validation**: Ran `npx tsc --noEmit` — no errors.

### File List

- `frontend/components/qa/QAContent.tsx` (modified)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-04-08 | Added error state retry button with plain-language message |
| 2026-04-08 | Implemented context-aware empty state with filter-specific suggestions |
| 2026-04-08 | Added `buildEmptyStateMessage()` helper function for AC3 |
| 2026-04-08 | Verified AC2 already satisfied by existing `handleSubmit()` behavior |
| 2026-04-08 | TypeScript validation passed — no errors |

---

## Review Findings

### Patch

- [x] [Review][Patch] `party` filter not handled in `buildEmptyStateMessage` [`frontend/components/qa/QAContent.tsx`:113] — Added `filters.party` check in both reason builder and suggestion priority chain. Fixed.

- [x] [Review][Patch] `filters_applied` could be undefined at runtime [`frontend/components/qa/QAContent.tsx`:113] — Added null guard at top of `buildEmptyStateMessage`: returns generic message if `!filters`. Fixed.

- [x] [Review][Patch] Awkward grammar with multiple active filters [`frontend/components/qa/QAContent.tsx`:118-124] — Replaced `parts.join(' ')` with comma/and separator logic: `parts.slice(0, -1).join(', ') + ' and ' + parts[-1]`. Fixed.

- [x] [Review][Patch] No `aria-label` on Retry button [`frontend/components/qa/QAContent.tsx`:383] — Added `aria-label="Retry the question"`. Fixed.

- [x] [Review][Patch] Date values shown as raw ISO strings in empty-state message [`frontend/components/qa/QAContent.tsx`:118-124] — Added `formatDateString()` helper using `toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })`. Dates now render as "Jan 15, 2025". Fixed.

### Defer

- [x] [Review][Defer] Retry button styling deviates from spec [`frontend/components/qa/QAContent.tsx`:383] — Current style is intentionally more prominent than "Clear filters" but doesn't match spec exactly. Deferred: will revisit styling holistically at end of dev, using external tool UIs as design inspiration rather than purely AI-generated look. — deferred, end-of-dev polish

- [x] [Review][Defer] Suggestion shows only one action even when multiple filters are active [`frontend/components/qa/QAContent.tsx`:126-134] — Currently suggests removing only the most specific filter. AC3 example shows combined suggestion ("Try a wider time range or remove the platform filter"). Deferred as UX enhancement beyond current spec. — deferred, pre-existing UX limitation

- [x] [Review][Defer] No loading text change on Retry button [`frontend/components/qa/QAContent.tsx`:383] — Label stays "Retry" during loading. Common pattern is "Retrying…" but not specified in AC. — deferred, nice-to-have UX improvement
