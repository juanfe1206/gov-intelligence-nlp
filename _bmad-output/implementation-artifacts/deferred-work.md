# Deferred Work

## Deferred from: code review of 1-3-political-taxonomy-configuration (2026-04-07)

- No schema-level validation that `name` fields are lowercase with no spaces — real gap, but Story 1.5 (NLP classification) is the right enforcement point when names are used as DB values
- `tardà` uses non-ASCII character as a machine identifier in taxonomy.yaml — valid for now; should be addressed before any URL routing or DB key usage
- API tests assert specific taxonomy YAML content, not just structure — low-risk brittleness; tests will break on any taxonomy data change even if the API is correct
- `request.app.state.taxonomy` AttributeError if lifespan is bypassed in tests — current TestClient context manager usage guards against this; revisit if test patterns change

## Deferred from: code review of 1-6-ingestion-job-status-tracking-api.md (2026-04-07)

- Existing processing selection can double-process posts under concurrent workers due to non-claiming reads; address with a concurrency-safe claim/locking strategy in a dedicated follow-up.

## Deferred from: code review of 2-6-cross-party-sentiment-comparison.md (2026-04-08)

- `get_comparison` contains an unreachable `parties = [None]` branch given the HTTP layer rejects empty `parties`; harmless but worth removing if the service is only called from the route.
- Party comparison control relies on hover to open the checklist; consider focusable trigger + click/tap for keyboard and mobile users when polishing accessibility.

## Deferred from: code review of 2-7-spike-alert-detection-banner.md (2026-04-08)

- Top-5 sort mixes volume ratios with sentiment deltas on a single `magnitude` scale, so volume spikes tend to crowd out sentiment spikes; matches current spec but may need product input if balanced surfacing is required.

## Deferred from: code review of 2-8-analyst-deep-dive-export-copy.md (2026-04-08)

- Party comparison sentiment buckets are case-sensitive and can silently zero-out counts when labels are not exactly normalized lowercase.
- Spike detection treats any non-zero recent count over zero baseline as a spike; this can create false positives on sparse datasets.
- Dashboard empty-state predicate likely does not trigger when backend returns zero-filled time series for valid ranges.

## Deferred from: code review of 3-3-qa-frontend-question-input-insight-summary-panel (2026-04-08)

- SpikeAlertBanner navigates to `/qa?topic=...&question=...` but QAContent ignores URL params — Story 3.5 scope (clickable dashboard tiles pre-filling the question)
- Frontend never sends `filters` or `top_n` in POST body — Story 3.4 scope (filter controls)
- `NEXT_PUBLIC_API_BASE_URL` fallback to `http://localhost:8000` — established codebase pattern across all components
- Render path where `insufficient_data` is false but both `summary` and `answer_error` are null — not practically reachable with current backend code
- Sentiment type mismatch: frontend `QAPostItem.sentiment` is union type, backend schema is `str` — speculative about future backend changes
- `filters_applied` not rendered in the UI — not required by Story 3.3 spec
- `insufficient_data` early-return hides metrics/posts — backend returns empty data in this case, so behavior is correct

## Deferred from: code review of 3-4-qa-filter-controls-multi-session-iteration (2026-04-08)

- Silent taxonomy/platform fetch failure (`.catch(() => {})`) — spec-compliant and mirrors FilterBar pattern; consider adding console.warn or user-facing fallback in future polish pass
- `hasActiveFilters` redundant in useCallback deps (derived from `qaFilters` already in deps) — spec-mandated, harmless; can remove in a refactor pass

## Deferred from: code review of 3-6-qa-resilience-error-states-demo-readiness (2026-04-08)

- Retry button styling deviates from spec — current style is intentionally more prominent but doesn't match "Clear filters" exactly; will revisit styling holistically at end of dev using external tool UIs as design inspiration
- Suggestion shows only one action even when multiple filters are active — currently suggests removing only the most specific filter; AC3 example shows combined suggestion but implementation follows priority order; UX enhancement beyond current spec
- No loading text change on Retry button — label stays "Retry" during loading; common pattern is "Retrying…" but not specified in AC; nice-to-have UX improvement

## Deferred from: code review of 4-1-admin-operations-dashboard-ui.md (2026-04-08)

- No auth/authorization guard on admin page or retry endpoint — any user can view admin page and trigger retry; not Story 4.1 scope, Story 4.3 covers unauthenticated access
- `formatDateTime` returns "Invalid Date" for unparseable ISO strings — only triggered by malformed backend data; pre-existing concern not specific to this change
- "X total jobs" header can display count larger than displayed list — API defaults to `limit=50`; no pagination in Story 4.1 scope
