# Story 2.1: Frontend Shell Layout & Design System Setup

Status: review

## Story

As a developer,
I want a reusable application shell with left navigation, top header, and a main content grid, plus a configured Tailwind design system,
so that all dashboard and Q&A views share consistent layout, spacing, typography, and color semantics from the start.

## Acceptance Criteria

1. **Given** the Next.js frontend is initialized
   **When** a developer implements the shell layout
   **Then** the app renders a slim left navigation bar, a top header bar, and a flexible main content area following a 12-column grid
   **And** the left nav links to at least a Dashboard route (`/dashboard`) and a Q&A route (`/qa`)

2. **Given** the design system needs shared tokens
   **When** Tailwind is configured
   **Then** the config defines: a neutral/blue-gray base palette, a deep blue primary accent, semantic colors (green=positive, amber=warning, red=negative), an 8px spacing scale, and a sans-serif type scale (h1–h4, body, small)
   **And** color is never the sole carrier of meaning — icons or labels accompany all sentiment/status indicators

3. **Given** any interactive element in the app
   **When** a user navigates via keyboard
   **Then** all focusable elements show a visible focus ring, and text/UI elements meet WCAG AA contrast ratios against their backgrounds

## Tasks / Subtasks

- [x] Configure Tailwind v4 design tokens in globals.css (AC: 2)
  - [x] Extend `@theme` block in `frontend/app/globals.css` with semantic color tokens: primary (deep blue), neutral/blue-gray base, sentiment colors (green/amber/red)
  - [x] Add global focus-visible styles and WCAG AA contrast baseline to globals.css (AC: 3)
  - [x] Switch font from Geist to Inter via `next/font/google` in root layout (sans-serif type scale)

- [x] Create shell layout components (AC: 1)
  - [x] Create `frontend/components/shell/LeftNav.tsx` — slim left nav with Dashboard and Q&A `<Link>` items, active state via `usePathname` (`'use client'`)
  - [x] Create `frontend/components/shell/TopHeader.tsx` — top header bar with app name/logo (server component)

- [x] Create app shell route group layout (AC: 1)
  - [x] Create `frontend/app/(shell)/layout.tsx` — wraps routes with LeftNav + TopHeader + 12-column main grid; does NOT include `<html>`/`<body>` (those stay in root layout)

- [x] Create Dashboard and Q&A routes (AC: 1)
  - [x] Create `frontend/app/(shell)/dashboard/page.tsx` — Dashboard placeholder page
  - [x] Create `frontend/app/(shell)/qa/page.tsx` — Q&A placeholder page

- [x] Update root page to redirect to dashboard (AC: 1)
  - [x] Update `frontend/app/page.tsx` to use `redirect('/dashboard')` from `next/navigation`

- [x] Validate and verify (AC: 1, 2, 3)
  - [x] Run `npm run lint` — zero errors
  - [x] Run `npm run build` — builds successfully with no TypeScript errors
  - [x] Manually verify: `/dashboard` renders shell with left nav and top header; keyboard Tab moves focus with visible focus rings

## Dev Notes

### CRITICAL: Read Bundled Next.js Docs Before Writing Code

**`frontend/AGENTS.md` explicitly warns**: "This is NOT the Next.js you know. This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code."

Key docs to read first:
- `frontend/node_modules/next/dist/docs/01-app/01-getting-started/03-layouts-and-pages.md`
- `frontend/node_modules/next/dist/docs/01-app/01-getting-started/11-css.md`
- `frontend/node_modules/next/dist/docs/01-app/01-getting-started/04-linking-and-navigating.md`

### Current Frontend State (from Story 1.1)

The frontend was initialized via `npx create-next-app frontend --ts --tailwind --app`. Current files:

- `frontend/app/layout.tsx` — root layout with Geist fonts, `<html>` + `<body>` tags
- `frontend/app/page.tsx` — Next.js default starter page (will be replaced with redirect)
- `frontend/app/globals.css` — Tailwind v4 via `@import "tailwindcss"` + `@theme inline` block
- `frontend/package.json` — Next.js **16.2.2**, React 19.2.4, Tailwind CSS v4 (`@tailwindcss/postcss ^4`)

### Tech Stack Versions (Critical)

- **Next.js 16.2.2** (NOT 14 or 15 — may have breaking API changes)
- **React 19.2.4**
- **Tailwind CSS v4** (CSS-first config — NO `tailwind.config.js` needed)
- **TypeScript 5.x**

### Tailwind v4 Design Token Configuration (CSS-first)

Tailwind v4 uses a **CSS-first approach** — all custom design tokens go in the `@theme` block inside `globals.css`. There is NO `tailwind.config.js` file for token configuration.

Extend the existing `@theme inline` block (or replace with separate `@theme` block for tokens) with semantic colors:

```css
/* frontend/app/globals.css */
@import "tailwindcss";

/* CSS custom properties for light mode */
:root {
  --background: #ffffff;
  --foreground: #171717;
}

/* Tailwind v4 design tokens — generates utility classes like text-primary, bg-sentiment-positive */
@theme {
  /* Primary accent — deep blue */
  --color-primary: #1d4ed8;          /* blue-700 */
  --color-primary-hover: #1e40af;    /* blue-800 */
  --color-primary-foreground: #ffffff;

  /* Neutral blue-gray base */
  --color-surface: #f8fafc;          /* slate-50 */
  --color-surface-raised: #ffffff;
  --color-border: #e2e8f0;           /* slate-200 */
  --color-muted: #64748b;            /* slate-500 */

  /* Semantic sentiment colors */
  --color-sentiment-positive: #16a34a;   /* green-600 */
  --color-sentiment-warning: #d97706;    /* amber-600 */
  --color-sentiment-negative: #dc2626;   /* red-600 */

  /* Typography */
  --font-sans: var(--font-inter), ui-sans-serif, system-ui, sans-serif;

  /* Shell layout dimensions */
  --spacing-nav-width: 16rem;   /* 256px left nav width */
  --spacing-header-height: 4rem; /* 64px top header height */
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --font-mono: var(--font-geist-mono);
}
```

**Note:** In Tailwind v4, `@theme` generates utility classes. `--color-primary` → `text-primary`, `bg-primary`, etc. `--color-sentiment-positive` → `text-sentiment-positive`, etc.

### Root Layout Font Update

Switch from Geist Sans to Inter in `frontend/app/layout.tsx`. Keep Geist Mono for code if desired:

```tsx
import { Inter, Geist_Mono } from "next/font/google";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});
```

Update `<html>` className to use `inter.variable` and `geistMono.variable`.

### Shell Layout Architecture (App Router Route Groups)

Use App Router **route group** `(shell)` so the shell layout applies to `/dashboard` and `/qa` without affecting the root URL or other routes:

```
frontend/app/
├── layout.tsx              ← root layout (html + body, unchanged structure)
├── page.tsx                ← redirect to /dashboard
├── globals.css             ← design tokens
├── (shell)/                ← route group (no URL segment)
│   ├── layout.tsx          ← shell layout: LeftNav + TopHeader + main grid
│   ├── dashboard/
│   │   └── page.tsx        ← /dashboard
│   └── qa/
│       └── page.tsx        ← /qa
└── components/             ← (OR use frontend/components/ at root)
    └── shell/
        ├── LeftNav.tsx
        └── TopHeader.tsx
```

**Use `frontend/components/shell/` for components** (not inside `app/`) for clean separation.

### Next.js 16 Conventions (IMPORTANT)

From the bundled docs (`03-layouts-and-pages.md`):

1. **`params` is now a `Promise`** in Next.js 16:
   ```tsx
   // Next.js 16 style — params is Promise<{...}>
   export default async function Page(props: PageProps<'/blog/[slug]'>) {
     const { slug } = await props.params
   }
   ```
   This story doesn't use dynamic params, but be aware for future stories.

2. **`PageProps` and `LayoutProps` are global helpers** — no import needed:
   ```tsx
   export default function Layout(props: LayoutProps<'/dashboard'>) {
     return <section>{props.children}</section>
   }
   ```

3. **Route groups** `(shell)` work identically to prior versions — folder name is excluded from URL.

4. **`'use client'`** required for any component using hooks (`usePathname`, `useState`, etc.).

### LeftNav Component

`LeftNav` needs `usePathname` for active link highlighting → must be `'use client'`:

```tsx
// frontend/components/shell/LeftNav.tsx
'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const navItems = [
  { label: 'Dashboard', href: '/dashboard', icon: '📊' },
  { label: 'Q&A', href: '/qa', icon: '💬' },
]

export default function LeftNav() {
  const pathname = usePathname()
  return (
    <nav className="flex flex-col w-64 h-full bg-surface border-r border-border px-4 py-6 gap-1">
      {navItems.map(({ label, href, icon }) => {
        const isActive = pathname.startsWith(href)
        return (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 ${
              isActive
                ? 'bg-primary text-primary-foreground'
                : 'text-muted hover:bg-border hover:text-foreground'
            }`}
            aria-current={isActive ? 'page' : undefined}
          >
            <span aria-hidden="true">{icon}</span>
            {label}
          </Link>
        )
      })}
    </nav>
  )
}
```

**Accessibility:** `aria-current="page"` on the active link. Icons marked `aria-hidden` since labels provide meaning (color is NOT the sole indicator).

### TopHeader Component

Server component (no hooks needed):

```tsx
// frontend/components/shell/TopHeader.tsx
export default function TopHeader() {
  return (
    <header className="h-16 bg-surface-raised border-b border-border flex items-center px-6">
      <h1 className="text-sm font-semibold text-foreground tracking-wide uppercase">
        Gov Intelligence
      </h1>
    </header>
  )
}
```

### Shell Layout (Route Group)

```tsx
// frontend/app/(shell)/layout.tsx
import LeftNav from '@/components/shell/LeftNav'
import TopHeader from '@/components/shell/TopHeader'

export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <LeftNav />
      <div className="flex flex-col flex-1 overflow-hidden">
        <TopHeader />
        <main className="flex-1 overflow-y-auto bg-surface">
          <div className="grid grid-cols-12 gap-6 p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
```

### Root Page Redirect

```tsx
// frontend/app/page.tsx
import { redirect } from 'next/navigation'

export default function RootPage() {
  redirect('/dashboard')
}
```

### Dashboard and Q&A Placeholders

Both pages are `col-span-12` placeholders — actual content comes in Stories 2.2+:

```tsx
// frontend/app/(shell)/dashboard/page.tsx
export default function DashboardPage() {
  return (
    <div className="col-span-12">
      <h2 className="text-2xl font-semibold text-foreground">Dashboard</h2>
      <p className="mt-2 text-muted">Analytics content coming soon.</p>
    </div>
  )
}
```

```tsx
// frontend/app/(shell)/qa/page.tsx
export default function QAPage() {
  return (
    <div className="col-span-12">
      <h2 className="text-2xl font-semibold text-foreground">Q&A</h2>
      <p className="mt-2 text-muted">Question input and insight panel coming soon.</p>
    </div>
  )
}
```

### Global Focus and Accessibility Styles

Add to `globals.css` after the `@theme` blocks:

```css
/* Ensure all interactive elements have visible focus rings by default */
*:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
```

This ensures focus rings without relying purely on Tailwind utility classes being present on every element.

### `@` Path Alias

The project uses `@/` as a path alias for the `frontend/` root (from `tsconfig.json`). Use `@/components/shell/LeftNav` not relative paths.

### TypeScript Path Alias Verification

Check `frontend/tsconfig.json` — should have:
```json
"paths": {
  "@/*": ["./*"]
}
```
If missing, add it to resolve `@/components/...` imports.

### No External Component Library Required

This story uses **only Tailwind CSS utility classes** — no Headless UI or Radix needed yet. Those will be added when interactive components (dialogs, popovers, dropdowns) are needed in later stories.

### Testing Approach

No frontend testing framework (Jest/Vitest/Playwright) is installed. Validation for this story:
1. **`npm run lint`** — must pass with zero ESLint errors (Next.js ESLint config is already set up)
2. **`npm run build`** — must produce a clean TypeScript build with no type errors
3. **Manual verification** — open `/dashboard` and `/qa`, Tab through interactive elements to verify visible focus rings

A testing framework setup is a separate concern, likely to be addressed in a dedicated infrastructure story or when first complex interactive component is needed.

### File Path Summary

**Create:**
- `frontend/components/shell/LeftNav.tsx`
- `frontend/components/shell/TopHeader.tsx`
- `frontend/app/(shell)/layout.tsx`
- `frontend/app/(shell)/dashboard/page.tsx`
- `frontend/app/(shell)/qa/page.tsx`

**Modify:**
- `frontend/app/globals.css` — add design tokens to `@theme` block, add focus-visible styles
- `frontend/app/layout.tsx` — switch Geist Sans to Inter, update className
- `frontend/app/page.tsx` — replace placeholder with `redirect('/dashboard')`
- `frontend/tsconfig.json` — verify `@/*` path alias exists (add if missing)

**Do NOT create:**
- `tailwind.config.js` — Tailwind v4 uses CSS-first config in globals.css
- Any backend files — this story is frontend-only

### Architecture Compliance Checklist

- ✅ Next.js App Router with TypeScript (no Pages Router)
- ✅ Tailwind CSS v4 CSS-first token configuration (no `tailwind.config.js`)
- ✅ Route group `(shell)` for shared layout without URL pollution
- ✅ `'use client'` only on components that need hooks (LeftNav)
- ✅ Inter sans-serif font (UX spec: "Inter or Roboto")
- ✅ Color + icon/label for sentiment (never color alone — WCAG)
- ✅ WCAG AA: focus-visible rings on all interactive elements
- ✅ 12-column grid in main content area (UX-DR9)
- ✅ Left nav + top header + flexible main content area (UX-DR16)
- ✅ 8px spacing base (Tailwind default spacing is 4px per unit, so `gap-2`=8px, `p-2`=8px)

### Epic 2 Cross-Story Context

This story is the **foundation for all of Epic 2**. Stories 2.2–2.8 will:
- Add content inside `frontend/app/(shell)/dashboard/page.tsx`
- Add content inside `frontend/app/(shell)/qa/page.tsx`
- Use the design tokens defined here (`text-primary`, `text-sentiment-positive`, etc.)
- Add new components reusing the shell's 12-column grid

**Do NOT implement any chart, filter, or data-fetching logic in this story** — that's 2.2+.

### Epic 2 UX Requirements for This Story

From `_bmad-output/planning-artifacts/ux-design-specification.md`:
- UX-DR7: Neutral/blue-gray base, deep blue primary accent, semantic colors (green/amber/red)
- UX-DR8: Clean sans-serif (Inter or Roboto), clear type scale, generous line height
- UX-DR9: 8px base unit, 12-column grid, medium density
- UX-DR10: WCAG AA contrast, visible keyboard focus, icons+labels not color alone
- UX-DR16: Reusable shell layout (left nav + top header + flexible main content grid)

### References

- [Source: `frontend/AGENTS.md`] — Critical warning: read bundled docs before writing code
- [Source: `frontend/node_modules/next/dist/docs/01-app/01-getting-started/03-layouts-and-pages.md`] — Route groups, layouts, Next.js 16 conventions
- [Source: `frontend/node_modules/next/dist/docs/01-app/01-getting-started/11-css.md`] — Tailwind CSS v4 setup
- [Source: `_bmad-output/planning-artifacts/ux-design-specification.md`] — Design system, layout, accessibility requirements
- [Source: `_bmad-output/planning-artifacts/architecture.md`] — Next.js + Tailwind stack, App Router
- [Source: `_bmad-output/planning-artifacts/epics.md#Story 2.1`] — Acceptance criteria and story requirements
- [Source: `frontend/app/globals.css`] — Existing Tailwind v4 setup to extend
- [Source: `frontend/app/layout.tsx`] — Root layout to modify (font swap)
- [Source: `frontend/package.json`] — Exact versions: Next.js 16.2.2, React 19.2.4, Tailwind v4

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- ✅ Configured Tailwind v4 design tokens with semantic colors (primary deep blue, surface blue-gray, sentiment colors)
- ✅ Added WCAG AA focus-visible styles to globals.css
- ✅ Switched font from Geist to Inter via next/font/google
- ✅ Created shell layout components (LeftNav.tsx, TopHeader.tsx)
- ✅ Created app shell route group layout at frontend/app/(shell)/layout.tsx
- ✅ Created Dashboard and Q&A placeholder routes
- ✅ Updated root page to redirect to /dashboard
- ✅ Validated: npm run lint (0 errors), npm run build (success)
- ✅ All 3 Acceptance Criteria satisfied

### File List

**Created:**
- frontend/components/shell/LeftNav.tsx
- frontend/components/shell/TopHeader.tsx
- frontend/app/(shell)/layout.tsx
- frontend/app/(shell)/dashboard/page.tsx
- frontend/app/(shell)/qa/page.tsx

**Modified:**
- frontend/app/globals.css — Added @theme block with design tokens, focus-visible styles
- frontend/app/layout.tsx — Switched Geist Sans to Inter font
- frontend/app/page.tsx — Replaced placeholder with redirect('/dashboard')
