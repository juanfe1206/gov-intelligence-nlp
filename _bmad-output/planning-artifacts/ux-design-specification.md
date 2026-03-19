stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-03-core-experience
  - step-04-emotional-response
  - step-05-inspiration
  - step-06-design-system
  - step-07-defining-experience
  - step-08-visual-foundation
  - step-09-design-directions
  - step-08-visual-foundation
inputDocuments:
  - path: _bmad-output/planning-artifacts/product-brief-gov-intelligence-nlp-2026-03-18.md
    type: product_brief
  - path: _bmad-output/planning-artifacts/prd.md
    type: prd
  - path: docs/political_intelligence_platform.md
    type: project_doc
date: 2026-03-19
author: Phillip
---

# UX Design Specification gov-intelligence-nlp

**Author:** Phillip
**Date:** 2026-03-19

---

## Executive Summary

### Project Vision

The gov-intelligence-nlp platform is a Spanish-politics-first intelligence tool that turns fragmented online discourse into decision-ready insights for political parties. It ingests posts from platforms like X, Threads, Bluesky, and Reddit, classifies them using a Spanish political taxonomy (topics, sentiment, targets, intensity), and exposes the results through a focused dashboard and an LLM-powered Q&A interface. The UX goal is to let non-technical political users move from noisy feeds and generic charts to clear, grounded answers to concrete political questions in under a few minutes, especially in high-pressure moments.

### Target Users

The primary users are campaign managers, digital directors, communications and rapid-response teams, and political analysts working inside Spanish political parties. They are comfortable with basic dashboards and analytics tools but are not data engineers; they care about fast, trustworthy answers more than configuration. Secondary users include party leadership and external consultants, who consume summaries and visualizations produced by the tool, and internal IT/data owners, who are responsible for data freshness and system health. For the MVP, we optimize UX for desktop/laptop use in office and war-room settings, where users are under time pressure but have access to a full screen and keyboard.

### Key Design Challenges

- **Clarity in complex data**: Presenting multidimensional analytics (topics, sentiment, parties, time, platforms) in a way that makes “what matters now” obvious to political users without requiring analyst-level interpretation.
- **Trustworthy, explainable answers**: Designing the Q&A experience so that every answer clearly shows why it can be trusted, by grounding narratives in representative posts and simple supporting metrics instead of opaque model outputs.
- **Fast crisis navigation**: Supporting rapid-response workflows where users must detect spikes, understand narratives, and drill into concrete examples within a few clicks and seconds, even when they are stressed and context-switching.

### Design Opportunities

- **Narrative-first presentation**: Framing the interface around narratives and clusters of discourse (e.g. “criticism about rent caps”) rather than just charts and keyword clouds, so the product feels built for political strategy work instead of generic monitoring.
- **Question-led interaction model**: Making natural-language questions and a small set of guided presets (“What’s spiking?”, “How are we doing on housing vs Party X?”) the primary entry points, aligning the UX with how campaign teams actually think about problems.
- **Guided drill-down paths**: Providing clear, opinionated drill paths from overview dashboards into topics, then narrative clusters, and finally representative posts, so users can go from high-level signals to actionable evidence without getting lost in filters.

## Core User Experience

### Defining Experience

At the heart of gov-intelligence-nlp is a simple loop: political users ask a natural-language question about public discourse, and the system responds with a concise, grounded answer plus evidence they can trust. The core experience is built around letting campaign managers, communications leads, and analysts type questions such as “What are the main negative narratives about our housing policy vs Party X this week?” and receive, within seconds, a clear narrative summary supported by key metrics and representative posts. Most critical user journeys—issue performance checks, crisis investigations, and topic deep-dives—are variations of this question-and-answer loop.

### Platform Strategy

The MVP is delivered as a desktop-first web application, optimized for mouse and keyboard use in office and war-room environments where users have access to a full screen. The primary surfaces are a focused dashboard view (for scanning trends, spikes, and comparative performance) and a Q&A view (for asking natural-language questions with optional filters). Mobile and tablet experiences are explicitly out of scope for the first version; instead, the UX is tuned for clarity and speed on laptops and desktops commonly used by campaign and communications teams.

### Effortless Interactions

The most important interaction to make effortless is moving from a political question in a user’s head to a trustworthy, interpretable answer on screen. Typing a question, optionally choosing a preset filter (e.g. topic or time range), and seeing a structured response—with narratives, basic metrics, and a handful of copyable example posts—should require almost no thought or configuration. Secondary interactions that should also feel smooth include scanning a dashboard for spikes, clicking into a topic or leader, and drilling down into narrative clusters and posts without losing context or getting lost in filters.

### Critical Success Moments

Key success moments include the first time a campaign manager or communications lead, under time pressure, uses the tool to understand a spike in negative discourse or to compare performance on a key issue versus a competitor, and feels they have a clear answer within a couple of minutes. Another critical moment is when an analyst can iteratively ask several related questions about a topic (e.g. immigration over the last month) and refine their view without leaving the tool or exporting data. Failure moments to avoid are slow or opaque Q&A responses, confusing dashboards that hide what matters, or drill-down paths that make it hard to connect high-level signals to concrete example posts.

### Experience Principles

- **Question-first, not chart-first**: The primary entry point is asking political questions in natural language, with dashboards supporting that loop rather than replacing it.
- **Evidence-backed answers**: Every answer should be anchored in representative posts and simple, visible metrics so users can quickly judge credibility.
- **Fast paths under pressure**: Critical flows for crisis investigation and issue performance comparison must be usable in seconds, with minimal configuration and clear drill paths.
- **Stay oriented while drilling down**: Users should always understand where they are in the journey from overview to topic to narrative to post, and be able to move back and forth without losing their place.

## Desired Emotional Response

### Primary Emotional Goals

The product should make users feel efficient and productive, as if they are cutting through noise and getting to a clear answer much faster than with their current tools or workflows. When using gov-intelligence-nlp, campaign managers, communications leads, and analysts should feel that the platform is helping them stay ahead of the conversation rather than chasing it, turning complex discourse into something they can act on quickly.

### Emotional Journey Mapping

- **First discovery:** Users feel intrigued and cautiously optimistic that this might finally give them a politics-focused alternative to generic dashboards.
- **During core use (asking questions, scanning spikes):** They feel focused and in control, with the sense that the interface is helping them prioritize what matters instead of adding more clutter.
- **After completing a task:** They feel productive and relieved, with a clear answer or narrative they can immediately use in a briefing, memo, or response.
- **When something goes wrong (e.g. data gaps, errors):** They should feel informed rather than helpless; the system explains what happened in plain language and offers a simple next step (retry, adjust filters, or check ingestion status).
- **On returning:** They feel confident that the tool will help them quickly reorient to what has changed since they last checked.

### Micro-Emotions

The most important micro-emotions for success are:
- **Confidence over confusion:** Users should feel they understand what the charts, narratives, and metrics are telling them, without needing an analyst to translate.
- **Trust over skepticism:** Answers should feel grounded and transparent, with visible evidence (representative posts and simple counts) so users can quickly sanity-check results.
- **Calm focus over anxiety:** In tense situations, the interface should reduce perceived chaos by highlighting the few things that matter rather than overwhelming users with options.
- **Accomplishment over frustration:** Common tasks—like checking a key issue, understanding a spike, or comparing against a competitor—should feel like short, successful paths, not long struggles with filters.

### Design Implications

- To avoid confusion, the UI should favor clear, opinionated defaults and simple language over dense control panels and ambiguous labels.
- To minimize frustration, core flows (ask a question, investigate a spike, compare on an issue) must be reachable with very few steps and respond within predictable time limits.
- To build trust, every Q&A answer and key chart should be accompanied by visible evidence and simple explanations of what data is being shown.
- Error and empty states should be designed to explain what is happening and what the user can do next, rather than showing generic technical messages.

### Emotional Design Principles

- **Clarity beats cleverness:** Interfaces should prioritize clear explanations and straightforward layouts that reduce mental load, especially under time pressure.
- **Always show your work:** Wherever possible, pair summaries with underlying evidence so users can quickly verify and reuse what they see.
- **Guide, don’t overwhelm:** Default views and drill paths should gently guide users toward the most important insights instead of exposing every possible control upfront.
- **Fail gracefully and transparently:** When data is missing or something breaks, the product should communicate calmly and constructively, preserving user confidence rather than causing panic or irritation.

## UX Pattern Analysis & Inspiration

### Inspiring Products Analysis

GovernLens and CivIntel-style platforms show how political intelligence tools can center around a unified command center: a main dashboard with relevance scoring, alerts, and a question box that accepts plain-language queries (“Which political developments affect me?”). They handle complexity by structuring content into dimensions (topics, actors, procedures) and always tying insights back to original sources.

PolecatX demonstrates a strong conversational AI pattern for high-stakes intelligence work: users “just ask” questions and receive fully referenced, evidence-based answers. Its emphasis on transparent sourcing and sentiment accuracy maps closely to our need for trust and traceability in Spanish political discourse.

Ask Amplitude and Memnai illustrate mature “question-first” analytics UX. Instead of forcing users to build charts, they let people type natural-language questions and automatically generate relevant visualizations and metrics. This reduces friction for non-technical users and shortens the path from question to insight, which aligns directly with our core experience goals.

### Transferable UX Patterns

- **Navigation Patterns**
  - A central “command center” view combining a small set of key KPIs, alerts/spikes, and an always-visible question input, so users can both scan and ask without changing screens.
  - Progressive disclosure from overview to detail: top-level KPIs and trends at the top, with drill-down sections for topics, parties, and narrative clusters below.

- **Interaction Patterns**
  - Question-first input that accepts natural-language queries and offers a few guided presets (e.g. “What’s spiking?”, “Compare us vs Party X on housing”) to reduce blank-page anxiety.
  - Clickable narrative clusters and issue tiles from the dashboard that pre-fill or shape questions, creating a smooth bridge between visual exploration and Q&A.
  - Interactive visualizations that support hover for detail-on-demand and simple filters, without requiring users to compose complex queries or multi-step configuration flows.

- **Visual Patterns**
  - Clear visual hierarchy: 3–5 core KPIs visible within the first screen, with primary trend or comparison charts occupying most of the viewport, and secondary panels for narratives and posts.
  - Strong evidence blocks beneath summaries: cards that show representative posts with sentiment tags and simple metrics, reinforcing trust in the aggregated view.

### Anti-Patterns to Avoid

- Overloaded dashboards crammed with too many charts, filters, and widgets that make it hard to see “what matters now” within a few seconds.
- Opaque AI answers that read like generic text without clear links to underlying posts or simple counts, which would undermine trust.
- Filter-heavy, configuration-first workflows that require many clicks and parameter choices before users see any meaningful insight, especially harmful in crisis or time-pressured scenarios.

### Design Inspiration Strategy

- **What to Adopt**
  - A question-first interaction model inspired by Ask Amplitude and Memnai, where users can type political questions in natural language and quickly see generated insights plus visualizations.
  - A command-center style dashboard, similar in spirit to GovernLens/CivIntel, focused on a small set of key metrics, spikes, and issues relevant to Spanish politics.

- **What to Adapt**
  - Conversational AI patterns from PolecatX, adapted to our smaller MVP scope but preserving the principle of fully referenced, evidence-backed answers.
  - Analytics visualization best practices (clear hierarchy, detail-on-demand, trend and comparison charts) tuned specifically to topics, parties, and sentiment in Spanish political discourse.

- **What to Avoid**
  - Generic marketing-style social listening dashboards that prioritize vanity metrics and keyword clouds over narrative clarity and actionable political insight.
  - Any UX that requires analyst-level skills (SQL, complex segmentation builders) for basic questions, since our primary users should feel productive and efficient without technical expertise.

## Design System Foundation

### 1.1 Design System Choice

For gov-intelligence-nlp, we will use a themeable design system built on React with Tailwind CSS and a small set of opinionated, accessible components (either from a headless library such as Headless UI/Radix or a light component kit styled with Tailwind). This approach gives us fast development with proven interaction patterns, while still allowing us to shape a visual language that feels focused and serious enough for political intelligence work.

### Rationale for Selection

- We need to move quickly as a small student team, so building a fully custom design system from scratch would be too costly for the MVP.
- Established, heavy systems like pure Material/Ant would speed development but risk giving the product a generic analytics-tool look that doesn’t fully match our narrative-first, question-first UX goals.
- A Tailwind-based, themeable system offers a strong foundation of utility classes and layout primitives, plus flexible components we can tune for clarity, hierarchy, and evidence-focused presentation without fighting a rigid visual language.

### Implementation Approach

- Use React as the frontend framework, with Tailwind CSS for layout, spacing, typography, and responsive behavior.
- Rely on a headless or minimal component library (e.g. Headless UI/Radix) for accessible primitives such as dialogs, popovers, lists, tabs, and comboboxes, then style them via Tailwind.
- Define a small set of layout templates for the main dashboard (command center) and Q&A views, ensuring consistent placement of KPIs, charts, narrative clusters, and evidence cards.
- Standardize interaction patterns for filters, question input, and drill-downs so similar actions always look and behave the same across the app.

### Customization Strategy

- Establish basic design tokens via Tailwind configuration: color palette (neutral base with accent color for alerts/spikes), typography scale, spacing, and border radius to create a calm, focused analytic feel.
- Create reusable components tailored to this product, such as “Narrative Cluster Card”, “Evidence Post Card”, “Insight Summary Panel”, and “Spike Alert Banner”, built on top of the underlying primitives.
- Gradually refine visuals as needed (e.g. adding subtle state indicators for sentiment, status, or urgency) without diverging from the core system, so the UI stays cohesive and easy to maintain.

## Defining Core Experience

### Defining Experience

The defining experience of gov-intelligence-nlp is that users can type a politically relevant question and almost instantly receive a clear, grounded answer with supporting charts and real example posts on a single, focused screen. In practical terms, a campaign manager or communications lead can ask something like “What are the main negative narratives about our housing policy vs Party X this week?” and see, within seconds, a concise narrative summary, key sentiment/volume metrics, and a small set of copyable posts they can drop into a briefing or response plan. This “ask a question, see trusted insight + evidence” loop is what users will describe when explaining the product to others.

### User Mental Model

Users think of the platform as a political “answer box” powered by structured social listening data rather than as a traditional analytics tool they have to configure. Their mental model is closer to asking a well-briefed analyst in a war room a direct question than to building a dashboard: they expect to type natural-language questions, optionally adjust simple campaign-relevant levers (issue, party, time window, platform), and then read an answer that makes sense without technical translation. They bring expectations from tools like Google and conversational AI (speed, simplicity, and continuity) but also assume that, because this is about politics, the system will show its work so they can judge whether to trust it.

### Success Criteria

- Users can go from typing a question to understanding the main answer and supporting evidence in seconds, not minutes, even in time-pressured situations.
- The combination of summary, metrics, and posts makes users feel they do not need to export to spreadsheets or other tools just to “make sense” of what the system is telling them.
- After a few uses, campaign managers, comms leads, and analysts feel confident starting important conversations (briefings, memos, rapid responses) directly from what they see in the app.

### Novel UX Patterns

The core experience combines established patterns (search bar, analytics dashboard cards, conversational answers) in a way that is still relatively novel for political intelligence: a question-first, narrative-centric interface over structured discourse data. Rather than inventing entirely new interaction paradigms, the product leans on familiar models—search input, chat-style answer blocks, evidence cards, and filters—but orients them around political questions and narratives instead of generic metrics. The main novelty is the tight coupling between natural-language questions, structured analytics, and traceable example posts presented together as a single, coherent answer.

### Experience Mechanics

1. **Initiation**
   - The user lands on a command-center screen where a prominent question input sits near key KPIs and alerts.
   - Placeholder text and a few preset suggestions (“What’s spiking?”, “How are we doing on housing vs Party X?”) invite them to start by asking a question in natural language.

2. **Interaction**
   - The user types their question and optionally adjusts simple filters (topic, party/leader, time window, platform).
   - On submit, the system runs retrieval and aggregation in the background, showing a brief, reassuring loading state that indicates it is analyzing discourse, not just fetching a single result.

3. **Feedback**
   - The answer appears as a structured panel: a short narrative summary, 2–3 key metrics or charts, and a small grid of representative posts with sentiment labels and basic context.
   - Clear labels and subtle affordances (e.g. “based on 1,234 posts in the last 7 days”) help users immediately understand scope and reliability. If there is not enough data, the system explains that instead of guessing.

4. **Completion**
   - The user feels they have a usable, defensible understanding of the situation and can copy text, metrics, or posts directly for their work.
   - From this state, they can refine the question, tweak filters, or follow links into deeper dashboard views (e.g. topic drill-down, narrative clusters) without losing the original answer context.

## Visual Design Foundation

### Color System

With no pre-existing brand guidelines, the color system should support a serious, professional tone while keeping the interface calm enough for analytical work. A neutral, cool-leaning base (shades of gray and subtle blue-grays) forms the background for dashboards and Q&A panels, with a restrained accent palette for highlighting key elements: a primary accent (for example a deep blue) for actions and focus states, and semantic colors for status (green for positive, amber for warnings, red for critical or negative sentiment). Color usage should emphasize clarity rather than decoration, with strong contrast for text against backgrounds and limited use of saturated tones reserved for spikes, alerts, and selected states.

### Typography System

The typography should feel professional and modern, optimized for reading short narrative summaries, metric labels, and example posts. A clean, sans-serif primary typeface with good on-screen readability (similar to Inter or Roboto) can be used across headings and body text, with a simple type scale (for example h1–h4, body, small) and generous line height to keep multi-line summaries easy to scan. Hierarchy should rely on size, weight, and spacing rather than decorative fonts, and minimum sizes should respect accessibility guidelines so metrics, labels, and post text remain legible on common laptop screens during long work sessions.

### Spacing & Layout Foundation

The layout should strike a medium balance between density and breathing room, allowing users to see key KPIs, charts, and evidence cards on a single screen without feeling cramped. A consistent spacing system based on an 8px unit keeps components aligned and predictable, while slightly larger gaps between major sections (for example header, KPI strip, charts, evidence area) help users parse the page at a glance. A grid-based layout (for example a 12-column desktop grid) supports responsive arrangements of charts and cards, with component-level spacing kept tight enough to feel efficient but not so tight that elements visually merge under time pressure.

### Accessibility Considerations

High contrast and readability are explicit goals: text and critical UI elements should meet or exceed WCAG AA contrast ratios against their backgrounds, especially for metrics, labels, and action buttons. Interactive elements need clear focus states for keyboard users, and color should not be the only carrier of meaning—icons, labels, or patterns should reinforce sentiment and status where possible. Long narrative answers and example posts should avoid overly long line lengths, and the overall system should favor clarity and legibility over visual flourish to remain usable for extended analytical and crisis-response sessions.

## Design Direction Decision

### Design Directions Explored

Based on the established UX foundations, the primary design direction focuses on a command-center style layout for desktop, with a clear separation between high-level signals, detailed analytics, and the Q&A experience. Within this, we considered variations in navigation (top vs side), density of the main dashboard area, and relative prominence of the question input versus charts and cards. All variations stayed within the same visual foundation: neutral/blue-gray base, restrained accents, medium density, and a question-first interaction model.

### Chosen Direction

The chosen direction is a desktop command-center layout with a slim left navigation, a top header bar, and a main content area split into three vertical bands: a KPI and alerts strip at the top, a primary analytics section (trend and comparison charts plus topic/narrative tiles) in the middle, and an evidence/Q&A panel that can occupy the lower half or open as a right-side pane. The question input is anchored prominently near the top of the main content area, always visible as users scroll within the dashboard content, so asking or refining a question feels central rather than secondary to chart exploration.

### Design Rationale

- This layout strongly supports the core experience: users can see “what’s going on” via KPIs and charts while having the question input and Q&A results in the same visual context, reducing mode switching between dashboard and assistant.
- The side navigation and top header keep structural navigation out of the way of daily workflows, letting the main area focus on topics, narratives, and evidence cards aligned with political use cases.
- Medium-density panels with clear sectioning match the need to see enough information for analytical work without overwhelming users under time pressure, and they align well with the Tailwind-based design system and spacing/grid decisions.

### Implementation Approach

- Implement a reusable shell layout with left navigation, top header, and a flexible main content grid that can host the dashboard view and the Q&A/evidence panel.
- In the dashboard route, use the top band for KPIs and alerts, the central band for core charts and topic/narrative tiles, and reserve a dedicated region or toggle for the Q&A/evidence panel so answers always appear in a predictable place.
- Reuse the same visual and interaction patterns (cards, chips, charts, evidence posts) across both dashboard and Q&A views, ensuring that clicking on dashboard elements can prefill or adjust the question input to keep the experience coherent.
