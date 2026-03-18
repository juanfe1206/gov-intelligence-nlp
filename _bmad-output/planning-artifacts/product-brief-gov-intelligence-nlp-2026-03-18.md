---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - docs/political_intelligence_platform.md
date: 2026-03-18
author: Phillip
---

# Product Brief: gov-intelligence-nlp

## Executive Summary

Spanish political parties today face an overwhelming volume of unstructured online discourse spread across platforms like X, TikTok, Threads, and Reddit. Strategy, communications, and campaign teams depend on analysts or agencies to manually monitor this noise, interpret sentiment, and package it into decision-ready insights. Existing social listening tools provide generic dashboards and sentiment scores, but they are not designed for the specific needs, language, and dynamics of Spanish politics.

This project proposes a political intelligence platform that transforms large-scale online political discourse into structured, queryable intelligence. By combining a domain-specific Spanish political taxonomy, machine learning pipelines, and an LLM-powered question interface, the platform enables political teams to move directly from raw public conversation to grounded, factual answers about topics, sentiment, and party perception. The goal is an easy-to-use, insight-first tool that could realistically be attractive to real political organizations, even though it is initially developed as a university assignment.

---

## Core Vision

### Problem Statement

Political parties and campaign organizations in Spain must continuously understand how the public talks about them and about key policy issues. Today, this understanding relies heavily on expensive analysts and agencies that manually monitor social media and online conversations, run ad-hoc queries in generic social listening tools, and distill findings into reports and decks. The result is slow, labour-intensive, and often too high-level to answer specific, day-to-day strategic questions.

### Problem Impact

Because analysis is manual and fragmented across tools and platforms, political teams:

- Struggle to keep up with the speed and volume of online discourse.
- Risk missing early signals of emerging narratives or attacks.
- Depend on intermediaries to translate dashboards and sentiment charts into concrete insights, which slows decision-making.
- Have difficulty answering precise questions such as "How is sentiment on our housing policy evolving this month versus Party X?" or "What are people actually saying about our latest announcement?" without launching new analyses.

When they are too slow or misread the online climate, they can suffer narrative loss, reputational damage, and missed opportunities to frame debates or respond to risks.

### Why Existing Solutions Fall Short

Current social listening platforms like Brandwatch, Talkwalker, Pulsar, and others are powerful but fundamentally general-purpose. They are designed for brands, PR, and marketing across many industries, not specifically for Spanish political campaigns. Their limitations for this use case include:

- Generic taxonomies that are not aligned with political issues (e.g., housing, immigration, healthcare, corruption).
- Sentiment models that are not optimized for Spanish political discourse, irony, or coded language.
- Dashboards that give high-level charts and keyword clouds but still require analysts to interpret and contextualize them for political strategy.
- Complex configuration and professional services requirements that make them less accessible to individual politicians or smaller parties.
- Lack of a natural-language, question-answering experience that returns grounded, explainable insights instead of only visualizations.

### Proposed Solution

The proposed platform ingests political discourse from relevant online sources (e.g., X, Threads, Bluesky, Reddit) and processes it through a tailored NLP pipeline that classifies posts by topic, subtopic, sentiment, target, and intensity using a Spanish political taxonomy. All processed data is stored in a structured database that serves as a source of truth for analysis.

On top of this, an LLM-powered query layer allows users—especially non-technical political actors—to ask natural language questions such as "What are the main criticisms of our housing policy this week?" or "How does sentiment about our party compare to Party X over the last month?" The system retrieves and aggregates relevant data, then generates factual, grounded answers, optionally enriched with strategic recommendations. A simple dashboard complements this interface with key trends and alerts, but the primary value is moving from unstructured noise to directly usable political intelligence.

### Key Differentiators

- **Political-first design**: The platform is built specifically for political parties and campaigns in Spain, with a topic taxonomy and metrics tailored to political issues rather than generic brand categories.
- **Spanish political language focus**: Models and prompts are tuned for Spanish political discourse, including slang, irony, and polarized language, improving sentiment and topic accuracy.
- **Question-first UX**: Instead of forcing users to interpret complex dashboards, the core interaction is a natural-language Q&A interface that returns grounded, explainable insights.
- **Analyst leverage, not replacement**: The system reduces the manual scanning and basic reporting workload, allowing analysts (if present) to focus on higher-level strategy, or enabling smaller teams to access intelligence they could not previously afford.
- **Scalable assignment-to-product path**: Although conceived as a university project, the architecture and value proposition are designed so that with additional robustness and data integrations it could be commercially attractive to real political organizations.

## Target Users

### Primary Users

**Campaign Managers and Digital Directors in Spanish Political Parties**  
These users are responsible for shaping overall campaign strategy, coordinating messaging across channels, and making rapid decisions based on how the public and media are reacting. Today they rely on reports from analysts, agencies, and generic social listening dashboards to understand sentiment and narrative shifts. They need a way to get precise, data-backed answers to questions about topics, parties, and policies without waiting for a new round of manual analysis.

**Communications and Rapid Response Teams**  
These teams monitor online conversations to detect emerging narratives, attacks, and crises, and to decide when and how to respond. They often work with custom monitoring setups focused on platforms like X and rely on automation and manual triage to route mentions to the right people. They need early warning on negative trends and clear visibility into what people are actually saying so they can craft timely, grounded responses.

**Political Analysts and Data/Insights Staff**  
Analysts and data specialists examine large volumes of online conversations to understand public sentiment, issue salience, and the impact of campaign actions. They often use general-purpose social listening tools plus custom scripts or spreadsheets. For them, the platform is a way to reduce the time spent on basic retrieval, cleaning, and aggregation, and to focus more on interpretation and strategic recommendations while still being able to drill down into the underlying data when needed.

### Secondary Users

**Party Leadership and Elected Officials**  
Leaders and senior politicians may not use the platform directly every day, but they consume the insights it produces through dashboards, briefings, or Q&A sessions. They care about clear, trustworthy summaries of how their party and policies are perceived, and about tracking how sentiment evolves over time in response to major events or decisions.

**External Consultants and Strategic Advisors**  
Campaign consultants, pollsters, and media strategists may use the platform as one of their data inputs when advising a party. They benefit from having an always-on, structured view of online discourse that complements polling and focus groups, and from being able to explore specific questions about narratives, sentiment, and comparative performance.

**Internal IT and Data Teams**  
Technical teams may not be primary consumers of insights, but they are important stakeholders for integration, data governance, and reliability. They may use exports or APIs from the platform to connect political intelligence data with other systems in the party’s data infrastructure.

### User Journey

**Discovery**  
The platform is typically discovered through internal innovation initiatives, recommendations from consultants, or as a response to a perceived gap in existing social listening and analytics tools. Campaign managers and digital directors recognize that current setups require too much manual work and are not tailored to Spanish political needs.

**Onboarding**  
A campaign or party configures the platform with its main parties, candidates, and policy topics, using the Spanish political taxonomy as a starting point. Analysts and digital staff connect relevant data sources (e.g., X, Threads, Bluesky, Reddit) and validate initial classifications and sentiment outputs on sample data.

**Core Usage**  
On a day-to-day basis, campaign managers, digital directors, and analysts use the platform to ask natural language questions about current sentiment, narratives, and comparative performance. Communications teams watch key dashboards and alerts for spikes in negative sentiment or the emergence of new topics. Analysts periodically review and refine topic and sentiment models based on observed edge cases.

**Success Moment**  
The "aha" moment occurs when a team quickly answers a high-stakes question—such as understanding the impact of a new policy announcement or a public controversy—by querying the platform and receiving a grounded, data-backed summary that directly informs their response. They see that they can move from intuition and scattered dashboards to a single, politically-focused source of truth.

**Long-term Integration**  
Over time, the platform becomes a regular part of campaign rhythm: it is consulted in daily or weekly war-room meetings, supports the preparation of strategy memos and speeches, and feeds into broader research and polling work. For some parties, it becomes a core intelligence asset that persists beyond a single election cycle.
