# Story 2.2: Post Volume & Sentiment Over Time Charts

Status: done

## Story

As a campaign or communications user,
I want to view post volume and aggregated sentiment over time for a selected time range,
So that I can quickly understand how political discourse is evolving.

## Acceptance Criteria

1. **Given** processed posts exist in the database
   **When** the user opens the dashboard with a default time range (last 7 days)
   **Then** a time-series chart shows daily post volume and a sentiment trend line (positive/neutral/negative proportions) across the selected period
   **And** the charts render within 2 seconds for the target dataset size (≤10k posts)

2. **Given** the backend analytics endpoints
   **When** `GET /analytics/volume` and `GET /analytics/sentiment` are called with `start_date` and `end_date` query params
   **Then** they return time-bucketed data (daily) with post counts and sentiment breakdowns suitable for charting

3. **Given** no posts exist for the selected time range
   **When** the user views the dashboard
   **Then** an empty state message explains no data is available for this period and suggests adjusting the time range

## Tasks / Subtasks

- [x] Backend: Create analytics module (AC: 2)
  - [x] Create `backend/app/analytics/__init__.py`
  - [x] Create `backend/app/analytics/schemas.py` — Pydantic response models
  - [x] Create `backend/app/analytics/service.py` — async DB queries joining processed_posts → raw_posts
  - [x] Create `backend/app/api/analytics.py` — FastAPI router with volume + sentiment endpoints
  - [x] Update `backend/app/main.py` — register analytics router at prefix `/analytics`

- [x] Frontend: Environment setup (AC: 1, 2)
  - [x] Create `frontend/.env.local` with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
  - [x] Verify `frontend/.env.example` documents `NEXT_PUBLIC_API_BASE_URL`

- [x] Frontend: Install charting library (AC: 1)
  - [x] Run `npm install recharts` inside `frontend/`
  - [x] Verify install with `npm run build` (no type errors)

- [x] Frontend: Chart components (AC: 1, 3)
  - [x] Create `frontend/components/charts/VolumeChart.tsx` — `'use client'` Recharts bar/line chart for daily volume
  - [x] Create `frontend/components/charts/SentimentChart.tsx` — `'use client'` Recharts stacked area chart for positive/neutral/negative proportions
  - [x] Create `frontend/components/dashboard/DashboardContent.tsx` — `'use client'` component owning state and API fetching
  - [x] Update `frontend/app/(shell)/dashboard/page.tsx` — render `<DashboardContent />`

- [x] Validate (AC: 1, 2, 3)
  - [x] `npm run lint` — zero errors
  - [x] `npm run build` — clean TypeScript build
  - [x] Manual: open `/dashboard`, confirm charts load; verify empty state with no-data date range

### Review Findings

- [x] [Review][Patch] Zero-fill missing calendar days in analytics series (decision: include explicit zero buckets across requested range) [backend/app/analytics/service.py:14]
- [x] [Review][Patch] Local date handling uses UTC conversion and can shift requested day range in non-UTC timezones [frontend/components/dashboard/DashboardContent.tsx:14]
- [x] [Review][Patch] API accepts invalid ranges (`start_date > end_date`) and returns silent empty data instead of validation error [backend/app/api/analytics.py:27]
- [x] [Review][Patch] "Last 7 days" default computes an 8-day inclusive window (`today-7` through `today`) [frontend/components/dashboard/DashboardContent.tsx:13]
- [x] [Review][Patch] `error_status` filter excludes NULL rows, despite requirement being to exclude only `True` [backend/app/analytics/service.py:33]

## Dev Notes

### CRITICAL: Read Bundled Next.js Docs Before Writing Code

**`frontend/AGENTS.md` warns**: "This is NOT the Next.js you know. This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code."

Key docs:
- `frontend/node_modules/next/dist/docs/01-app/01-getting-started/03-layouts-and-pages.md`
- `frontend/node_modules/next/dist/docs/01-app/01-getting-started/04-linking-and-navigating.md`

### Tech Stack Versions (Critical)

- **Next.js 16.2.2** (NOT 14 or 15)
- **React 19.2.4**
- **Tailwind CSS v4** (CSS-first, no `tailwind.config.js`)
- **TypeScript 5.x**
- **FastAPI** with async SQLAlchemy 2.x, PostgreSQL + pgvector

### Current Frontend State (from Story 2.1)

Story 2.1 created the following — do NOT recreate them, only extend:

**Shell Layout** (already exists):
```
frontend/
├── app/
│   ├── globals.css          ← design tokens in @theme block
│   ├── layout.tsx           ← root layout, Inter font
│   ├── page.tsx             ← redirect('/dashboard')
│   └── (shell)/
│       ├── layout.tsx       ← LeftNav + TopHeader + 12-col main grid
│       ├── dashboard/
│       │   └── page.tsx     ← MODIFY: replace placeholder with DashboardContent
│       └── qa/
│           └── page.tsx     ← do NOT touch
├── components/
│   └── shell/
│       ├── LeftNav.tsx
│       └── TopHeader.tsx
```

**Design tokens (from globals.css `@theme` block) — use these in Recharts props:**
```
--color-primary: #1d4ed8          → Recharts: stroke="#1d4ed8"
--color-sentiment-positive: #16a34a  → stroke="#16a34a"
--color-sentiment-warning: #d97706   → stroke="#d97706"
--color-sentiment-negative: #dc2626  → stroke="#dc2626"
--color-border: #e2e8f0
--color-muted: #64748b
--color-surface: #f8fafc
```

**Typography pattern (existing, from dashboard/page.tsx):**
```tsx
<h2 className="text-foreground font-semibold [font-size:var(--font-size-h2)] [line-height:var(--line-height-h2)]">
<p className="text-muted [font-size:var(--font-size-body)] [line-height:var(--line-height-body)]">
```

### Backend: Analytics Module

**New files to create:**

#### `backend/app/analytics/schemas.py`

```python
from datetime import date
from pydantic import BaseModel

class DailyVolume(BaseModel):
    date: str  # "YYYY-MM-DD"
    count: int

class VolumeResponse(BaseModel):
    data: list[DailyVolume]
    total: int

class DailySentiment(BaseModel):
    date: str  # "YYYY-MM-DD"
    positive: int
    neutral: int
    negative: int

class SentimentResponse(BaseModel):
    data: list[DailySentiment]
```

#### `backend/app/analytics/service.py`

The date dimension comes from `raw_posts.created_at` (NOT `processed_posts.processed_at`).
Join: `processed_posts JOIN raw_posts ON processed_posts.raw_post_id = raw_posts.id`
Filter out posts where `processed_posts.error_status = True`.

```python
from datetime import date
from sqlalchemy import func, cast, Date, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.raw_post import RawPost
from app.models.processed_post import ProcessedPost
from app.analytics.schemas import DailyVolume, VolumeResponse, DailySentiment, SentimentResponse

async def get_volume(
    session: AsyncSession,
    start_date: date,
    end_date: date,
) -> VolumeResponse:
    date_col = cast(RawPost.created_at, Date)
    stmt = (
        select(date_col.label("day"), func.count().label("count"))
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(
            and_(
                date_col >= start_date,
                date_col <= end_date,
                ProcessedPost.error_status.is_(False),
            )
        )
        .group_by(date_col)
        .order_by(date_col)
    )
    result = await session.execute(stmt)
    rows = result.all()
    data = [DailyVolume(date=str(row.day), count=row.count) for row in rows]
    return VolumeResponse(data=data, total=sum(d.count for d in data))


async def get_sentiment(
    session: AsyncSession,
    start_date: date,
    end_date: date,
) -> SentimentResponse:
    date_col = cast(RawPost.created_at, Date)
    stmt = (
        select(
            date_col.label("day"),
            ProcessedPost.sentiment,
            func.count().label("count"),
        )
        .select_from(ProcessedPost)
        .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
        .where(
            and_(
                date_col >= start_date,
                date_col <= end_date,
                ProcessedPost.error_status.is_(False),
            )
        )
        .group_by(date_col, ProcessedPost.sentiment)
        .order_by(date_col)
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Aggregate by date
    from collections import defaultdict
    by_date: dict[str, dict[str, int]] = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})
    for row in rows:
        day_str = str(row.day)
        sentiment = row.sentiment.lower() if row.sentiment else "neutral"
        if sentiment in ("positive", "neutral", "negative"):
            by_date[day_str][sentiment] += row.count
        else:
            by_date[day_str]["neutral"] += row.count  # fallback

    data = [
        DailySentiment(date=day, **counts)
        for day, counts in sorted(by_date.items())
    ]
    return SentimentResponse(data=data)
```

#### `backend/app/api/analytics.py`

Follow the exact same pattern as `backend/app/api/ingestion.py` for router structure:

```python
import logging
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.analytics.schemas import VolumeResponse, SentimentResponse
from app.analytics import service as analytics_service

logger = logging.getLogger(__name__)
router = APIRouter()

def _default_start() -> date:
    return date.today() - timedelta(days=7)

def _default_end() -> date:
    return date.today()

@router.get("/volume", response_model=VolumeResponse)
async def get_volume(
    start_date: date = Query(default_factory=_default_start),
    end_date: date = Query(default_factory=_default_end),
    session: AsyncSession = Depends(get_db),
) -> VolumeResponse:
    return await analytics_service.get_volume(session, start_date, end_date)

@router.get("/sentiment", response_model=SentimentResponse)
async def get_sentiment(
    start_date: date = Query(default_factory=_default_start),
    end_date: date = Query(default_factory=_default_end),
    session: AsyncSession = Depends(get_db),
) -> SentimentResponse:
    return await analytics_service.get_sentiment(session, start_date, end_date)
```

#### Update `backend/app/main.py`

Add after the existing router imports and registrations:

```python
from app.api.analytics import router as analytics_router
# ...
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
```

### Frontend: Environment Variable

The frontend calls the backend via `NEXT_PUBLIC_API_BASE_URL`. This variable must be set:

**Create `frontend/.env.local`** (not committed to git):
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

**Verify/create `frontend/.env.example`** documents this variable.

The variable is accessed in client components as `process.env.NEXT_PUBLIC_API_BASE_URL`.

### Frontend: Recharts Installation

```bash
cd frontend
npm install recharts
```

Recharts 2.x is compatible with React 19 (may show minor deprecation warnings — ignore for MVP). Recharts components use browser APIs so **all Recharts usage must be in `'use client'` components**.

**Recharts color usage:** Tailwind CSS classes (e.g. `text-sentiment-positive`) do NOT work as Recharts prop values. Use the raw hex values or CSS variables directly:
```tsx
<Line stroke="#16a34a" />    // sentiment-positive
<Line stroke="#d97706" />    // sentiment-warning (neutral proxy)
<Line stroke="#dc2626" />    // sentiment-negative
<Bar fill="#1d4ed8" />       // primary
```

### Frontend: Component Architecture

```
frontend/components/
├── charts/
│   ├── VolumeChart.tsx       ← 'use client', accepts data prop
│   └── SentimentChart.tsx    ← 'use client', accepts data prop
└── dashboard/
    └── DashboardContent.tsx  ← 'use client', owns data fetching state
```

**Rationale for this structure:** `dashboard/page.tsx` stays a server component (clean Next.js pattern). `DashboardContent` is the client boundary — it manages fetch state, error handling, and renders charts. Story 2.3 will add filter state to `DashboardContent` without changing the page file.

#### `frontend/components/dashboard/DashboardContent.tsx`

```tsx
'use client'
import { useEffect, useState } from 'react'
import VolumeChart from '@/components/charts/VolumeChart'
import SentimentChart from '@/components/charts/SentimentChart'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

// Default: last 7 days
function getDefaultDates() {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 7)
  const fmt = (d: Date) => d.toISOString().split('T')[0]
  return { startDate: fmt(start), endDate: fmt(end) }
}

export default function DashboardContent() {
  const { startDate, endDate } = getDefaultDates()
  const [volumeData, setVolumeData] = useState<VolumeData | null>(null)
  const [sentimentData, setSentimentData] = useState<SentimentData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      setError(null)
      try {
        const params = `start_date=${startDate}&end_date=${endDate}`
        const [volRes, sentRes] = await Promise.all([
          fetch(`${API_BASE}/analytics/volume?${params}`),
          fetch(`${API_BASE}/analytics/sentiment?${params}`),
        ])
        if (!volRes.ok || !sentRes.ok) throw new Error('Failed to fetch analytics data')
        const [vol, sent] = await Promise.all([volRes.json(), sentRes.json()])
        setVolumeData(vol)
        setSentimentData(sent)
      } catch (e) {
        setError('Unable to load analytics data. Check that the backend is running.')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [startDate, endDate])

  if (loading) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">Loading analytics…</p>
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

  const isEmpty = !volumeData?.data?.length && !sentimentData?.data?.length

  if (isEmpty) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">
          No data available for the selected period. Try adjusting the time range.
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="col-span-12">
        <h2 className="text-foreground font-semibold [font-size:var(--font-size-h2)] [line-height:var(--line-height-h2)]">
          Dashboard
        </h2>
        <p className="mt-1 text-muted [font-size:var(--font-size-small)]">
          Last 7 days · {startDate} – {endDate}
        </p>
      </div>

      <div className="col-span-12 lg:col-span-6 bg-surface-raised rounded-lg border border-border p-4">
        <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)] mb-4">
          Post Volume
        </h3>
        <VolumeChart data={volumeData?.data ?? []} />
      </div>

      <div className="col-span-12 lg:col-span-6 bg-surface-raised rounded-lg border border-border p-4">
        <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)] mb-4">
          Sentiment Over Time
        </h3>
        <SentimentChart data={sentimentData?.data ?? []} />
      </div>
    </>
  )
}

// Type definitions (inline for this story — move to shared types/ if used across stories)
interface VolumeData {
  data: Array<{ date: string; count: number }>
  total: number
}

interface SentimentData {
  data: Array<{ date: string; positive: number; neutral: number; negative: number }>
}
```

#### `frontend/components/charts/VolumeChart.tsx`

```tsx
'use client'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface Props {
  data: Array<{ date: string; count: number }>
}

export default function VolumeChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12, fill: '#64748b' }}
          tickFormatter={(v: string) => v.slice(5)} // "MM-DD"
        />
        <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
        <Tooltip
          contentStyle={{ fontSize: 12, borderColor: '#e2e8f0' }}
          labelFormatter={(label) => `Date: ${label}`}
        />
        <Bar dataKey="count" fill="#1d4ed8" name="Posts" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
```

#### `frontend/components/charts/SentimentChart.tsx`

```tsx
'use client'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface Props {
  data: Array<{ date: string; positive: number; neutral: number; negative: number }>
}

export default function SentimentChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12, fill: '#64748b' }}
          tickFormatter={(v: string) => v.slice(5)}
        />
        <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
        <Tooltip contentStyle={{ fontSize: 12, borderColor: '#e2e8f0' }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area type="monotone" dataKey="positive" stackId="1" stroke="#16a34a" fill="#16a34a" fillOpacity={0.3} name="Positive" />
        <Area type="monotone" dataKey="neutral" stackId="1" stroke="#d97706" fill="#d97706" fillOpacity={0.3} name="Neutral" />
        <Area type="monotone" dataKey="negative" stackId="1" stroke="#dc2626" fill="#dc2626" fillOpacity={0.3} name="Negative" />
      </AreaChart>
    </ResponsiveContainer>
  )
}
```

#### Updated `frontend/app/(shell)/dashboard/page.tsx`

```tsx
import DashboardContent from '@/components/dashboard/DashboardContent'

export default function DashboardPage() {
  return <DashboardContent />
}
```

### Performance Note

The SQL queries join `processed_posts` → `raw_posts` and group by date. For ≤10k posts this should complete well under 2 seconds without extra indexes. If you observe slowness, an index on `raw_posts.created_at` would help — but do NOT add a migration in this story; note it for Story 2.3 or a dedicated story.

### Architecture Compliance Checklist

- ✅ Recharts chart components are `'use client'` (browser APIs required)
- ✅ `dashboard/page.tsx` remains a server component (client boundary is `DashboardContent`)
- ✅ Data fetched via `NEXT_PUBLIC_API_BASE_URL` (architecture requirement)
- ✅ Date dimension from `raw_posts.created_at` (not `processed_posts.processed_at`)
- ✅ Analytics endpoints under `/analytics` prefix, registered in `main.py`
- ✅ Pydantic response schemas for all API endpoints
- ✅ Design tokens used for colors (hex values in Recharts props match globals.css tokens)
- ✅ 12-column grid: charts use `col-span-12 lg:col-span-6` (side-by-side on desktop)
- ✅ Empty state + error state + loading state all implemented
- ✅ No Redis/caching — raw DB queries per architecture decision
- ✅ Filter out `error_status=True` posts from analytics (only successful classifications)

### Epic 2 Cross-Story Context

Story 2.3 (Dashboard Filter Controls) will:
- Add `topic`, `party`, `time_range`, `platform` filter state to `DashboardContent`
- Pass those as query params to the analytics endpoints
- The analytics service will need filter params added — leave room in the service function signatures

**Do NOT implement any filter logic in this story** — only default 7-day date range.

Story 2.3 will also add `topic` and `party` filter params to the backend endpoints — the service functions accept `start_date`/`end_date` only for now. Story 2.3 will extend them.

### File Path Summary

**Backend — Create:**
- `backend/app/analytics/__init__.py`
- `backend/app/analytics/schemas.py`
- `backend/app/analytics/service.py`
- `backend/app/api/analytics.py`

**Backend — Modify:**
- `backend/app/main.py` — add analytics router import and `app.include_router(...)`

**Frontend — Create:**
- `frontend/.env.local` (not committed, add to .gitignore if missing)
- `frontend/components/charts/VolumeChart.tsx`
- `frontend/components/charts/SentimentChart.tsx`
- `frontend/components/dashboard/DashboardContent.tsx`

**Frontend — Modify:**
- `frontend/app/(shell)/dashboard/page.tsx` — replace placeholder content with `<DashboardContent />`
- `frontend/package.json` — recharts added via npm install (auto-updated)

**Do NOT create:**
- `tailwind.config.js` — Tailwind v4 CSS-first (already configured)
- Any test files — no testing framework installed yet
- Any new pages — dashboard/page.tsx is only modified, not recreated

### References

- [Source: `frontend/AGENTS.md`] — Critical: read bundled Next.js docs before writing code
- [Source: `_bmad-output/implementation-artifacts/2-1-frontend-shell-layout-design-system-setup.md`] — Shell layout, design tokens, Tailwind v4 patterns
- [Source: `frontend/app/globals.css`] — All design tokens (colors, typography, spacing)
- [Source: `_bmad-output/planning-artifacts/epics.md#Story 2.2`] — Acceptance criteria
- [Source: `_bmad-output/planning-artifacts/architecture.md`] — REST API, no caching, NEXT_PUBLIC_API_BASE_URL pattern
- [Source: `_bmad-output/planning-artifacts/ux-design-specification.md`] — Chart hierarchy, evidence-backed design
- [Source: `backend/app/models/processed_post.py`] — ProcessedPost schema (sentiment, error_status, raw_post_id)
- [Source: `backend/app/models/raw_post.py`] — RawPost schema (created_at is date dimension)
- [Source: `backend/app/api/ingestion.py`] — Router pattern to follow for analytics endpoints
- [Source: `backend/app/db/session.py`] — get_db dependency pattern

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- Created backend analytics module with volume and sentiment endpoints
- Implemented SQL queries joining processed_posts with raw_posts for date dimension
- Added error_status filtering to exclude failed classifications from analytics
- Created Recharts-based chart components for volume (BarChart) and sentiment (AreaChart)
- Implemented DashboardContent with loading, error, and empty states
- Frontend build successful with zero TypeScript errors

### File List

**Backend (Created):**
- `backend/app/analytics/__init__.py`
- `backend/app/analytics/schemas.py`
- `backend/app/analytics/service.py`
- `backend/app/api/analytics.py`

**Backend (Modified):**
- `backend/app/main.py` — registered analytics router at `/analytics`

**Frontend (Created):**
- `frontend/.env.local`
- `frontend/.env.example`
- `frontend/components/charts/VolumeChart.tsx`
- `frontend/components/charts/SentimentChart.tsx`
- `frontend/components/dashboard/DashboardContent.tsx`

**Frontend (Modified):**
- `frontend/app/(shell)/dashboard/page.tsx` — integrated DashboardContent
- `frontend/package.json` — added recharts dependency
