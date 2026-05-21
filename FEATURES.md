# TenderMatch — Feature Reference

## Core Platform Features
- **Multi-Tenant Architecture**: Strict organizational isolation at the PostgreSQL database level.
- **RBAC (Role-Based Access Control)**: Tiered access roles (`ADMIN1`, `USER`, `SUPER`) ensuring users only execute actions permitted by their authorization level.
- **Subscription Management**: Built-in SaaS capability (Free, Pro, Enterprise) tracking resource quotas (e.g., maximum vendor profiles, max match runs per day).

## Vendor Profile System
- **3-Phase Structured Onboarding**: Collects identity/geography (Phase 1), business capabilities/financials (Phase 2), and compliances/preferences (Phase 3) sequentially to reduce cognitive load.
- **AI-Powered Vendor Document Auto-Fill**: Vendors can upload unstructured capability statements (PDFs). An asynchronous AI pipeline extracts 3-phase structured data, enforces human-in-the-loop review, and deep-merges the payload into PostgreSQL.
- **Completeness Scoring**: A mathematical assessment of profile readiness (`profile_completeness_pct`), encouraging users to input more data for better AI matching.
- **Soft Delete & Duplication**: Profiles can be archived without breaking historical match integrity. Users can seamlessly clone existing profiles to quickly target different industry verticals.

## Tender Management
- **PDF Upload & Ingestion**: Secure multipart uploads mapped to tenant buckets.
- **Automated Text Extraction**: Handles rich PDFs (via PyMuPDF) and scanned documents (falling back to Tesseract OCR).
- **Auto-Ingestion Trigger**: A Celery scraper task designed to automatically poll external governmental procurement sites (Bidassist readiness).
- **Tender Store**: A searchable repository (`documents` in MongoDB and `tenders` in PostgreSQL) of all fully processed tenders.

## AI Matching Engine
- **Deterministic Hard Filters**: 5 strict business rules (Domain, Geography, Financial, Experience, Certifications) that instantly disqualify non-compliant vendors.
- **Hybrid Retrieval System**: Blends semantic `pgvector` search with keyword `rank_bm25` search, dynamically adjusting alpha weights based on vendor completeness.
- **Weighted Scoring**: Evaluates eligible vendors across 7 dimensions returning a precise 0-100 match percentage.
- **Explainable AI (XAI)**: Generates detailed, human-readable executive summaries, strengths, and risk factors using Groq (LLaMA 3).
- **Conversational RAG (Chat with Tender)**: Interact directly with parsed tender documents. Ask specific questions (e.g., "Is there a penalty clause?") and receive answers grounded strictly in the source PDF via vector retrieval.
- **Critic Agent / Hallucination Detection**: Deterministic pipeline checks that suppress LLM hallucination and ensure scoring consistency. Throws warnings or overrides completely.
- **Asynchronous Execution**: Deeply integrated with Celery to prevent UI blocking during heavy computations. 
- **Status Polling**: Safe, stateful HTTP polling (`GET /match/status/{task_id}`) to track background matching runs.

## LangGraph Agentic Pipeline
- **Dynamic Planner (Agentic RAG)**: Injects a planning node to assess context (vendor completeness, cache status) and intelligently route tasks (e.g., fallback to BM25, trigger reranker).
- **Cross-Encoder Reranking**: High-precision semantic reranking using `sentence-transformers` conditionally triggered for borderline match scores.
- **Stateful Execution Graph**: An orchestration mesh representing the pipeline as discrete graph nodes, passing a heavily-typed `TenderMatchState` with execution plans and critic reports.
- **Checkpointing (`MemorySaver`)**: Freezes pipeline state to PostgreSQL per thread. Allows long-running or paused matches.
- **Human-In-The-Loop Ready**: Architectural capability for a user to pause the agent graph, manually override a scoring variable, and resume the graph execution.
- **Execution Toggle**: A boolean flag (`use_langgraph`) that dynamically switches between the Direct Orchestrator path and the Agentic path.

## Adaptive Feedback Learning
- **EMA Weight Updates**: Exponential Moving Average mathematically adjusts a specific vendor's 7-dimension weights dynamically over time.
- **Feedback Signals**: Translates user actions (`Won`, `Submitted`, `Interested`, `Lost`, `Not Relevant`) into quantifiable scalar values driving the EMA math.
- **Three-Tier Fallback Hierarchy**: Safely resolves scoring weights starting from Vendor-Specific → Organization-Specific → Global Defaults.
- **WeightRadarChart**: Visual Recharts implementation demonstrating the variance between global defaults and the AI's learned preferences.

## Notifications & Alerts
- **Threshold-based Emailing**: Automatically fires match notifications (via Celery/SMTP) when an inbound tender exceeds a 75% match threshold for a vendor.
- **Toast Notifications**: Interactive, non-blocking React UI toasts notifying the user of completed background tasks or match discoveries.

## Dashboard & Analytics
- **Activity Feed**: An org-level audit log displaying historical actions (e.g., profiles updated, matches run, feedback submitted).
- **Summary Metrics**: Quick-access aggregates measuring total ingested tenders, active profiles, and average completeness scores.
- **Match History Viewer**: A paginated, filterable grid displaying all past matches.

## Security
- **JWT + Refresh Cookie**: Dual-token architecture. Short-lived Access Tokens (Bearer) handle request authorization, while long-lived Refresh Tokens (HttpOnly Cookie) silently renew sessions.
- **Redis Blacklisting**: Immediate JWT revocation on logout or forced expiration.
- **Strict Tenancy Enforcement**: Endpoints validate that requested resource IDs physically belong to the requester's `org_id`.
- **SQL Injection Prevention**: Exclusive use of SQLAlchemy ORM / Core parameterization.
- **Rate Limiting**: Redis-backed request throttling to mitigate brute-force and DDoS attempts.
- **File Validation**: MIME-type sniffing to reject non-PDF payloads prior to extraction.

## Frontend Features
- **Key Pages**: `Dashboard`, `MyProfiles`, `VendorProfile` (Editor), `DocumentUpload`, `Tenders` (Search), `MatchHistory`, and `TenderDetail` (Analysis view).
- **TanStack Query Caching**: Aggressive, intelligent client-side caching of API responses to ensure a rapid UI and reduced backend load.
- **Optimistic Updates**: Immediate UI state mutations (like disabling a feedback button) before the server confirms the database commit.
- **Responsive Layout**: Sidebar-driven layout built cleanly with Vite and Tailwind CSS.

## Planned Features (Roadmap)
- **Phase 8 — Immutable Audit Ledger**: Exporting critical match/bid data to a verifiable, tamper-evident ledger.
- **Phase 9 — Multilingual Support**: Automatic localization and translation of extraction and explanation models to support global procurement.
