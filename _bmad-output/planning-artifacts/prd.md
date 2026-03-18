---
workflowType: 'prd'
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
inputDocuments:
  - path: _bmad-output/planning-artifacts/product-brief-gov-intelligence-nlp-2026-03-18.md
    type: product_brief
  - path: docs/political_intelligence_platform.md
    type: project_doc
documentCounts:
  productBriefs: 1
  researchDocs: 0
  brainstormingDocs: 0
  projectDocs: 1
classification:
  projectType: data-driven web app / SaaS dashboard with LLM interface
  domain: political intelligence / govtech analytics (Spanish politics)
  complexity: medium-high
  projectContext: greenfield
date: 2026-03-18
author: Phillip
---

# Product Requirements Document - gov-intelligence-nlp

**Author:** Phillip
**Date:** 2026-03-18

## Executive Summary

Spanish political parties and campaign teams operate in an environment where online political discourse is fragmented across platforms like X, Threads, Bluesky, and Reddit, and existing social listening tools are generic, dashboard-centric, and not tuned to Spanish political language. This project, *gov-intelligence-nlp*, aims to build a Spanish-politics-first intelligence platform that continuously ingests public discourse, structures it using a tailored political taxonomy (topics, policies, parties, sentiment, intensity), and exposes it through a simple dashboard plus an LLM-powered question interface. The goal is to let strategy, communications, and campaign teams move from noisy feeds and generic charts to precise, grounded answers to their own political questions, even though the initial implementation is scoped as a university-level MVP.

The platform targets campaign managers, digital directors, communications and rapid-response teams, and political analysts within Spanish parties who today depend on analysts, agencies, and generic tools to interpret online sentiment. Instead of requiring complex configuration and manual analysis, the system offers a question-first experience: users ask political questions in natural language (e.g. "How has sentiment around our housing policy shifted this week vs Party X?"), and the platform returns structured, explainable insights derived from a domain-specific NLP pipeline and an LLM reasoning over curated data. A lightweight dashboard complements this by surfacing key trends, negative spikes, and topic composition across parties and issues.

### What Makes This Special

The product is designed as a political-first, Spanish-language-first alternative to generic brand monitoring tools. Its core differentiator is the combination of (1) a Spanish political taxonomy and models tuned to political discourse, including slang, irony, and polarized language; (2) a structured data layer where each post is classified by topic, subtopic, sentiment, target, and intensity; and (3) an LLM-powered Q&A layer that operates over this structured store rather than raw text. This lets teams ask specific strategic questions and receive grounded answers supported by traceable underlying data, rather than interpreting generic sentiment dashboards or keyword clouds.

The key insight is that by pre-structuring public political conversation into a domain-aware schema and then applying LLMs for retrieval and explanation, the platform can automate much of the tedious monitoring and basic reporting work that analysts or agencies currently perform. For parties and campaigns, this means earlier detection of emerging narratives or attacks, faster understanding of how policies are perceived, and the ability to base messaging and strategy on continuously updated, explainable intelligence rather than ad-hoc manual reports. Even as an MVP, the architecture is intended to be a credible foundation for a future production-grade political intelligence product.

## Project Classification

- **Project Type:** Data-driven web application / SaaS-style dashboard with backend APIs, NLP/ML pipeline, and LLM query interface  
- **Domain:** Political intelligence / govtech analytics focused on Spanish politics  
- **Complexity:** Medium–high (multi-source ingestion, NLP/ML classification, LLM/RAG, analytics)  
- **Project Context:** Greenfield (no existing implementation, built from this documentation and PRD)

## Success Criteria

### User Success

- Core outcome: campaign, communications, and analyst users can ask specific political questions in natural language (for example, “How is sentiment on our housing policy vs Party X this month?”) and receive a grounded answer in under 1–2 minutes using the platform.
- Aha moment: users see that the system already understands Spanish political topics, parties, and policies without heavy configuration, and returns structured insights (topics, sentiment, parties, representative posts) instead of just generic charts.
- Practical success: for a given test scenario (for example housing or immigration), a user can see top topics and sentiment trends, drill into representative posts that explain the narrative, and use the answer to support a concrete strategic or communications decision during the demo.

### Business Success

- Course and demo success: deliver a working end-to-end demo that ingests a non-trivial sample of Spanish political posts from at least one real platform (or a realistic synthetic dataset), runs them through the topic, sentiment, and target classification pipeline, and exposes results via both a simple dashboard and an LLM Q&A interface.
- Teacher and peer validation: during final presentations, teachers and classmates can ask their own questions about the dataset and receive coherent, data-grounded answers, not hard-coded scripts.
- Documentation and clarity: the project ships with a clear architecture description, PRD, and usage guide that make it believable as the seed of a real product rather than a one-off toy.

### Technical Success

- Pipeline robustness: implement a repeatable pipeline that can ingest at least a few thousand posts from a CSV or API, classify them into topics, sentiment, and targets, and produce stable, inspectable outputs (not just one-off notebooks).
- Query performance: for the demo dataset, typical Q&A queries should return an answer in 5 seconds or less end-to-end (retrieval, aggregation, and LLM).
- Quality and explainability: for a curated test set of questions, the system can show relevant underlying posts and basic metrics (counts, sentiment shares) that match manual inspection well enough for an MVP, without obviously wrong directional errors.
- Engineering hygiene: core components for ingestion, processing, API, and basic tests are implemented as modular, version-controlled code rather than ad-hoc scripts.

### Measurable Outcomes

- Time to answer a standard political question from the demo scenario is consistently under 1–2 minutes for users.
- The system can process and classify at least a few thousand posts in a reproducible way.
- A small set of curated test questions (for example 10–20) produce answers whose underlying evidence and metrics align with manual checks by the project team and instructors.
- The final demo and documentation clearly communicate how the system works end-to-end and how it could evolve into a production product.

## Product Scope

### MVP - Minimum Viable Product

- Ingest a realistic dataset of Spanish political posts.
- Classify posts by topic, sentiment, and party or target using a simple but working NLP pipeline.
- Store processed data in a queryable store (for example a database or equivalent).
- Provide a basic dashboard that shows topic distribution, sentiment over time, and simple filters.
- Provide an LLM Q&A endpoint or UI that can answer a small set of predefined but natural-language questions over the processed data.

### Growth Features (Post-MVP)

- Support multi-platform ingestion (for example X, Threads, Bluesky, and Reddit) with scheduling or regular refresh.
- Add alerting for spikes in negative sentiment or the emergence of new topics.
- Extend the taxonomy and models to include stance detection (for example pro or anti on specific issues) and more fine-grained categories.
- Add user accounts and saved views so different campaign teams can keep their own dashboards and queries.

### Vision (Future)

- Evolve into a production-grade SaaS platform for Spanish and later European political parties, with scalable ingestion and storage, higher-quality models, and geographic or demographic breakdowns.
- Integrate deeply into party workflows with exports to decks, reports, CRMs, and other internal tools.
- Provide richer agentic assistants that can propose messaging tests or strategy options based on live discourse and historical patterns.

## User Journeys

### Journey 1 – Campaign Manager, core success path

**Persona:** Marta, Campaign Manager for a mid-size Spanish party who owns messaging and wants to understand whether the housing narrative is helping or hurting compared to Party X.

- Opening scene: it is Monday morning in campaign HQ after a new housing package announcement. Traditional polls will not reflect the impact for days, but Twitter/X and Reddit are already full of reactions. Marta previously relied on an agency that sends weekly PDFs, which is too slow for this moment.
- Rising action: Marta logs into the platform, selects the “Housing” topic and the last 7 days, and immediately sees a summary of volume and sentiment across parties. She then switches to the Q&A view and asks “How has sentiment about our housing policy changed since Friday compared to Party X?”. The system pulls processed posts, aggregates sentiment by topic and party, and shows a concise answer plus charts and representative posts.
- Climax: she spots that sentiment for her party is roughly neutral overall but strongly negative on a specific subtopic (rent caps) while Party X is being praised for “stability and predictability”. She drills into example posts to understand the exact criticisms and phrases that are getting traction.
- Resolution: Marta shares a short summary and example posts with the communications team, adjusting the day’s talking points to address the rent caps narrative directly. She feels she now has near-real-time political intelligence instead of waiting for a weekly report and plans to check the same view after tonight’s TV appearance.

### Journey 2 – Communications / Rapid Response, edge case and recovery

**Persona:** Diego, Social Media and Rapid Response Lead for the party who watches for attacks and crises.

- Opening scene: late at night, Diego sees a spike in mentions of the party’s leader after a controversial TV clip circulates. Interns report that “we’re getting destroyed on X”, but the volume is chaotic and hard to interpret.
- Rising action: Diego opens the platform, filters the last 2 hours, and asks “What are the main negative narratives about our leader right now?”. The system initially times out on his first attempt due to a temporary ingestion lag, but he quickly retries with a slightly broader time window. The dashboard view shows a spike in volume tagged under “Corruption” and “Integrity”.
- Climax: in the Q&A answer, he gets a breakdown of two or three distinct narrative clusters plus representative posts and sources. He notices one cluster is driven by an old story resurfacing and another by a misinterpreted quote from tonight’s debate. The system’s explanations and examples let him distinguish old noise from a new, dangerous narrative.
- Resolution: Diego coordinates with the press office to issue a clarifying statement about the misquote and prepares talking points for morning radio. In the MVP demo, we show how he recovers from a partial system hiccup (retry, narrower filters) and still gets a usable, actionable picture of the crisis.

### Journey 3 – Political Analyst / Data Staff, deep-dive exploration

**Persona:** Laura, Data and Insights Analyst embedded in the party.

- Opening scene: Laura has been asked to prepare a memo on how perceptions of the party’s immigration stance evolved over the last month, ahead of an internal strategy offsite. Normally, she would export data from a generic social-listening tool and spend hours in spreadsheets.
- Rising action: she uses the platform’s analytics view to select the “Immigration” topic and the past 30 days, comparing her party with two competitors. She then queries “For our party, what are the main positive and negative narratives on immigration in the last month?”. The system shows trends and clusters plus links to drill down by subtopic such as border control, regularisation, and refugees.
- Climax: Laura exports a structured snapshot (aggregated metrics and sample posts) straight from the platform and uses the Q&A interface to refine questions such as “What changed after our border policy announcement on March 5?”. The responses highlight shifts in tone and which subtopics gained traction.
- Resolution: she assembles the memo in a fraction of her usual time with richer qualitative examples. For the MVP demo, success is that she can iterate multiple analytical questions in one session without leaving the tool or writing custom scripts.

### Journey 4 – Internal Admin / Technical Owner, setup and monitoring

**Persona:** Carlos, internal IT or data engineer responsible for reliability.

- Opening scene: Carlos has been asked to own the political intelligence platform from a technical perspective. He cares less about narratives and more about data freshness, ingestion health, and cost.
- Rising action: he logs into an admin view where he can see the status of recent ingestion jobs (success or failure, last run time), the volume of posts ingested per source, and basic resource usage or limits appropriate for the MVP setup. He configures a daily ingestion run for an X dataset and a small synthetic Reddit dump used for the university project.
- Climax: one day, ingestion for X fails due to an API or scraping change. Carlos sees a clear error in the admin panel, can re-run the job, and confirm that the data is flowing again. He feels the system is transparent and debuggable enough for a small team to trust.
- Resolution: Carlos documents a simple operational runbook (how to load data, how to check if it is working, how to retry) that makes the platform maintainable beyond the class project.

### Journey Requirements Summary

- For campaign and communications users (Journeys 1 and 2):
  - Fast, filtered access to topic, sentiment, and party views over time.
  - A question-first Q&A interface over processed data with representative example posts.
  - Handling of short-term spikes (hours or days) and associated narratives.
  - Basic error and retry flows when ingestion or queries fail, with clear feedback.
- For analysts (Journey 3):
  - Historical analysis over configurable time windows.
  - Ability to compare topics and sentiment across parties and time periods.
  - Export or at least view aggregated metrics and sample posts for offline memos.
- For admin and technical owners (Journey 4):
  - A basic admin or operations view with ingestion status, last run times, and simple controls.
  - Visibility into data volume and health for each source.
  - Simple, documented flows to recover from ingestion failures.

## Data-Driven Web App / SaaS Dashboard Requirements

### Project-Type Overview

The product is a data-driven web application with a SaaS-style dashboard and an LLM-powered query interface. The backend is a FastAPI service that ingests Spanish political posts, processes them through an NLP pipeline (topic, sentiment, target, intensity), stores structured results in PostgreSQL (including vector embeddings via pgvector or a similar extension), and exposes REST endpoints used by a React frontend for dashboards and Q&A. The MVP is single-tenant and demo-oriented for a university project: one dataset, one logical “party” context, and no production-grade authentication or multi-tenancy.

### Technical Architecture Considerations

- Backend:
  - FastAPI backend exposing REST endpoints for ingestion, analytics, and Q&A.
  - NLP and ML components using HuggingFace or OpenAI models for topic, sentiment, and target classification, plus an LLM used in a RAG pattern for question answering.
- Data storage:
  - PostgreSQL as the primary store for raw and processed posts, topics, sentiment, and aggregates.
  - Vector storage implemented with a Postgres vector extension (for example pgvector) to support similarity search over embeddings for Q&A retrieval.
- Frontend:
  - React single-page application providing:
    - A dashboard view (topic distribution, sentiment over time, filters).
    - A Q&A view where users ask natural-language questions and see grounded answers plus supporting posts.
- Deployment:
  - Simple single-service or few-services deployment (for example Docker-based) suitable for local development and a classroom demo, not multi-region or horizontally scaled production.

### Dynamic Capabilities by Area

- Ingestion and processing:
  - Ability to ingest posts from CSV files or simple connectors (for example pre-scraped X or Reddit dumps) into a raw table.
  - Batch processing job or endpoint that runs the NLP pipeline, writing structured fields (topic, subtopic, sentiment, target, intensity) and embeddings into the database.
  - Basic monitoring of ingestion runs (status, timestamps, error messages) exposed via an admin-facing API and/or UI.
- Analytics and dashboard APIs:
  - Endpoints to return:
    - Time-series sentiment data filtered by time range, topic, party or target, and platform.
    - Topic and subtopic distributions, including “most negative” and “most discussed” topics.
    - Representative example posts for a given filter combination.
- Q&A and LLM interface:
  - Endpoint (for example `POST /qa`) that accepts a natural-language question plus optional filters and:
    - Performs retrieval over the structured store and vector index.
    - Aggregates relevant metrics.
    - Calls an LLM to generate a grounded answer with references to underlying posts.
- Admin and operations:
  - Simple admin view and/or endpoints to:
    - See ingestion job status and last run times.
    - Trigger re-runs of ingestion or processing jobs for a dataset.
    - Perform basic health checks on the service and data pipeline.

### Implementation Considerations

- Authentication and tenancy:
  - No authentication for the MVP (demo in a controlled classroom environment); all users share the same interface.
  - Single-tenant design: the system assumes one logical party or dataset at a time; multi-tenancy and RBAC are explicitly deferred to a future version.
- Data volume and performance:
  - Target dataset size for the course is on the order of 5–10k posts, processed end-to-end through ingestion, NLP, and storage.
  - End-to-end Q&A latency (retrieval, aggregation, LLM call) should typically be under 5 seconds for this dataset size.
- Engineering and maintainability:
  - Clear modular separation between ingestion, processing, analytics APIs, and Q&A logic.
  - Configuration for data sources and model settings is kept in code or simple configuration files rather than hidden in notebooks.
  - Basic logging and error reporting sufficient to debug ingestion failures and Q&A errors during the demo.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-solving / learning MVP focused on demonstrating that structured Spanish political discourse plus an LLM Q&A layer can answer real campaign questions end-to-end, not just show charts. The goal is to prove that the core intelligence loop (ingest → classify → store → query → explain) works on a realistic dataset and supports the key user journeys for campaign, comms, and analyst users in a classroom setting.

**Resource Requirements:** Small student team (1–3 people) with skills across Python/ML (ingestion and NLP pipeline), backend (FastAPI, PostgreSQL, basic vector search), and frontend (React dashboard and Q&A UI). No dedicated DevOps team; deployment can be a simple Docker or single-VM setup.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**

- Campaign manager checking how a specific issue (for example housing) is discussed and how sentiment compares to a competitor, using both dashboard views and Q&A.
- Comms / rapid response user investigating short-term narrative spikes around a leader or issue and seeing representative posts to inform a response.
- Analyst performing a scoped deep-dive on one topic (for example immigration) over a fixed time window and exporting insights for a memo.

**Must-Have Capabilities:**

- Ingestion and processing of a realistic dataset (around 5–10k Spanish political posts) through the NLP pipeline (topic, sentiment, target, intensity) into PostgreSQL and a vector index.
- Dashboard APIs and UI for topic distributions, sentiment over time, filters by topic/party/platform, and access to representative posts.
- Q&A endpoint and UI where users ask natural-language questions within the demo scenario and receive grounded answers plus supporting posts and basic metrics.
- Simple admin/ops view or status indicators for ingestion runs (at least enough to demo recovery from a failed run).
- No authentication and single-tenant configuration suitable for a classroom demo.

### Post-MVP Features

**Phase 2 (Post-MVP / Growth):**

- Multi-platform ingestion (adding more sources beyond the initial dataset) with scheduled refresh.
- Alerting or highlighting for spikes in negative sentiment or newly emerging topics.
- Richer taxonomy and stance detection (for example explicitly pro/anti classifications on key policies).
- Saved views or simple user profiles so different teams can return to their preferred dashboards and questions.

**Phase 3 (Expansion / Vision):**

- Production-grade multi-tenant SaaS offering for multiple parties with authentication, RBAC, and organization-level separation.
- Geographic and demographic breakdowns where data supports it, plus deeper integrations into party tooling (exports to decks, CRMs, reporting pipelines).
- More advanced agentic assistants that can propose messaging experiments or strategic options based on live and historical discourse.

### Risk Mitigation Strategy

**Technical Risks:** The NLP pipeline and LLM Q&A integration are the most technically challenging pieces. To de-risk, the MVP limits itself to a modest dataset size, uses well-documented libraries (HuggingFace/OpenAI, pgvector), and focuses on a small set of evaluation questions where outputs can be manually validated. If full end-to-end RAG proves too complex, a fallback is to lean more heavily on pre-aggregated analytics and simpler retrieval.

**Market / Value Risks:** The main risk is that, even if technically working, the answers may not feel clearly more useful than generic dashboards to the target users. The MVP mitigates this by anchoring on concrete demo journeys (housing, immigration, leader narratives) and allowing instructors/classmates to ask their own questions during the demo as an informal validation.

**Resource Risks:** With limited time and team size, scope creep is a major risk. The PRD explicitly treats multi-tenancy, complex auth, large-scale ingestion, and advanced analytics as post-MVP features so the team can focus on getting a narrow but convincing end-to-end experience working first.

## Functional Requirements

### Ingestion & Processing

- FR1: An admin or technical owner can configure one or more data sources (for example CSV files or pre-scraped platform dumps) to be ingested into the system.
- FR2: An admin or technical owner can trigger an ingestion run that reads raw posts from the configured sources into the system’s raw data store.
- FR3: The system can automatically or manually start a processing run that applies the NLP pipeline (topic, subtopic, sentiment, target, intensity) to ingested posts.
- FR4: The system can store processed posts, including structured fields and embeddings, in a queryable store for later analytics and Q&A.
- FR5: An admin or technical owner can view the status of recent ingestion and processing runs, including whether they succeeded or failed and when they last ran.
- FR6: An admin or technical owner can re-run a failed ingestion or processing job from the admin view or via an API.

### Analytics & Dashboards

- FR7: A campaign or communications user can view an overview dashboard showing the volume of political posts over time for a selected time range.
- FR8: A campaign or communications user can view aggregated sentiment over time for a selected topic or issue.
- FR9: A campaign or communications user can filter dashboard views by topic, subtopic, party or target, time range, and platform.
- FR10: A user can see which topics and subtopics are most discussed and which are most negative or most positive within a given time window.
- FR11: A user can view representative example posts that illustrate a chosen topic, subtopic, or sentiment segment.
- FR12: An analyst can compare sentiment and volume across at least two parties or targets for a chosen topic and time range.

### Question-Answering Interface

- FR13: A campaign, communications, or analyst user can submit a natural-language question about political discourse through a Q&A interface.
- FR14: A user can optionally specify filters (for example topic, time range, party or target, platform) together with a question.
- FR15: The system can return a concise, grounded answer to a question that is clearly based on the underlying processed data.
- FR16: The Q&A response includes links to or previews of underlying posts used as evidence.
- FR17: The Q&A response includes basic numerical context (for example counts of posts and sentiment breakdowns) relevant to the question.
- FR18: A user can submit multiple questions in a single session without reloading the application.

### User Journeys & Workflow Support

- FR19: A campaign manager can execute the “check housing issue performance” journey end-to-end using only the dashboard and Q&A views (selecting topics, comparing parties, drilling into posts).
- FR20: A rapid response user can identify and investigate short-term narrative spikes about a leader, including seeing clusters of narratives and representative posts.
- FR21: A rapid response user can recover from a transient system or data issue (for example a failed ingestion) by retrying or adjusting filters and still obtain a usable picture of the situation.
- FR22: An analyst can conduct a month-long deep dive on a specific topic (for example immigration) by exploring trends, subtopics, and sentiment, and by exporting or copying data for use in a memo.
- FR23: An admin or technical owner can monitor ingestion health and follow a simple, documented sequence to restore data flow when a run fails.

### Admin & Operations

- FR24: An admin or technical owner can access an operations view summarizing ingestion jobs, their status, and key error messages.
- FR25: An admin or technical owner can perform basic health checks on the service (for example checking API availability or DB connectivity) through an admin UI or endpoint.
- FR26: An admin or technical owner can see approximate data volume per source to understand the current coverage of the dataset.

### Data Access & Exports

- FR27: An analyst can export or download a structured snapshot of aggregated metrics and representative posts for a given topic, time window, and party comparison.
- FR28: A user can copy or otherwise capture key charts and narrative summaries from the dashboard or Q&A view for inclusion in external documents or presentations.

### Configuration & Taxonomy

- FR29: An admin or technical user can configure the list of political topics, subtopics, and targets (for example parties or leaders) used by the classification pipeline.
- FR30: The system can use the configured taxonomy to tag posts consistently across ingestion runs.
- FR31: A technical user can adjust or update model and pipeline configuration (for example thresholds or model versions) without changing application code.

### Demo & Classroom Usage

- FR32: Any classroom participant can access the platform without individual authentication in the MVP environment.
- FR33: Instructors or reviewers can ask their own natural-language questions during the demo and receive coherent, data-grounded answers from the Q&A interface.
- FR34: A demo operator can reset or reinitialize the dataset and run a clean end-to-end pipeline in preparation for a new demonstration.

## Non-Functional Requirements

### Performance

- NFR1: For the target demo dataset (approximately 5–10k posts), typical Q&A requests should complete in 5 seconds or less end-to-end, including retrieval, aggregation, and LLM response generation.
- NFR2: For standard dashboard interactions (changing filters, time ranges, or topics), visible charts and key metrics should update within 2 seconds for the target dataset size.
- NFR3: The system should support at least a handful of concurrent classroom users (for example 5–10 people) without failing requests, even if performance gracefully degrades toward the upper bound of response times.

### Reliability & Operations

- NFR4: Ingestion and processing failures should be surfaced clearly in the admin or ops view, with enough information (timestamp, error summary) to allow a student operator to diagnose and retry without reading logs on the server.
- NFR5: It should be possible to run the full ingestion and processing pipeline from a clean state within a reasonable preparation window before a demo (for example within a couple of hours on a typical student machine or lab server).
- NFR6: During a live demo, the system should be stable enough that core flows (dashboards and Q&A) can be exercised for at least 30–45 minutes without needing to restart services.

### Security & Privacy (MVP Context)

- NFR7: The MVP will only process public or synthetic political content and will not store personal identifying information beyond what is present in the source posts; no additional sensitive user data (such as passwords or payment information) will be collected.
- NFR8: Access to the running demo environment should be limited to the project team, instructors, and classmates; it is not intended for open internet exposure or production use.
- NFR9: Any API keys or credentials used for data collection or LLM access should be stored in environment variables or configuration files that are not committed to source control.
