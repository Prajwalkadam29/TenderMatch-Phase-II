# TenderMatch AI

> An intelligent B2B procurement platform for deterministic and semantic tender‑to‑vendor matching.

## What is TenderMatch
TenderMatch is an advanced B2B procurement engine designed to seamlessly connect vendors with the most relevant government and enterprise tenders. By combining the precision of deterministic hard filtering (like turnover and geographic limits) with the nuance of AI‑driven semantic matching and Large Language Model (LLM) explanations, TenderMatch ensures that vendors only see opportunities they can actually win.

For organizations, the platform serves as an isolated, multi‑tenant workspace where detailed vendor capabilities, compliance standings, and financial profiles are securely managed and actively evaluated against inbound tender requirements. By implementing an adaptive learning loop, the AI engine dynamically learns from user feedback, making future recommendations increasingly accurate for each specific organization.

## Current System Status

| Component | Status | Notes |
|---|---|---|
| Auth & Multi‑tenancy | ✅ Complete | JWT + Refresh Cookie, Org‑level isolation |
| Vendor Profile Builder | ✅ Complete | 3‑Phase structured data collection |
| Tender PDF Ingestion | ✅ Complete | PyMuPDF/OCR fallback + chunking |
| AI Extraction (Groq/LLaMA 3) | ✅ Complete | JSON structured data extraction from PDFs |
| Hard Filter Engine | ✅ Complete | Deterministic pass/fail checks |
| Weighted Scoring Engine | ✅ Complete | 7‑dimension evaluation |
| LLM Explanation Engine | ✅ Complete | Groq‑powered strengths and risk generation |
| Match Orchestrator | ✅ Complete | Direct sequential processing pipeline |
| LangGraph Agentic Pipeline | ✅ Complete | Dynamic routing with Planner, Reranker, and Critic nodes |
| Critic Agent (Hallucination) | ✅ Complete | Deterministic validation & LLM hallucination suppression |
| Hybrid Retrieval System | ✅ Complete | Blended `pgvector` semantic + `rank_bm25` keyword search |
| Adaptive Feedback Learning | ✅ Complete | EMA weight updates via Celery |
| Frontend Dashboard | ✅ Complete | Metrics, stats, and recent activity |
| Match History & Detail | ✅ Complete | Detailed breakdown UI with explanations |
| Feedback Buttons & Signals | ✅ Complete | Submit/Won/Lost signals driving AI learning |
| Radar Chart Visualization | ✅ Complete | Real‑time Recharts weight tracking |
| **Bidassist Auto‑Ingestion** | ✅ Complete | Pulls tenders via Bidassist API, normalises, deduplicates, and routes through the production‑grade ingestion pipeline |
| **Scheduled Portal Scraping** | ✅ Complete | Firecrawl‑backed scraper with graceful BS4 fallback, configurable portals, rate‑limiting and deduplication |
| Admin Sync Dashboard | ✅ Complete | UI for manual sync trigger, history, and health monitoring |
| **Vendor Document Auto-Fill Pipeline** | ✅ Complete | 3-phase extraction (upload → draft review → PostgreSQL commit), 8 edge cases hardened, full security audit |

## Architecture Overview
The system relies on a polyglot persistence strategy powered by FastAPI and React. Document text and structured extractions live in MongoDB for flexible querying, while relational metadata, vendor profiles, and the pgvector embeddings are firmly rooted in PostgreSQL. Asynchronous workloads, such as tender ingestion and feedback‑driven weight updates, are brokered through Redis and processed by Celery workers. The matching engine features two distinct paths: a high‑speed direct Orchestrator and a resilient LangGraph Agentic Pipeline.

```mermaid
flowchart TD
    Client[React Frontend] -->|API Calls| FastAPI[FastAPI Backend]
    FastAPI -->|Queries| PG[(PostgreSQL + pgvector)]
    FastAPI -->|Documents| Mongo[(MongoDB)]
    FastAPI -->|Dispatch Task| Redis[(Redis Broker)]
    Redis --> Celery[Celery Workers]
    subgraph Celery Tasks
        TenderIngest[Tender Ingestion Task]
        MatchTask[Match & Notify Task]
        FeedbackTask[EMA Feedback Task]
    end
    Celery --> TenderIngest
    Celery --> MatchTask
    Celery --> FeedbackTask
    subgraph AI Pipeline
        direction TB
        Ext[Groq Extraction]
        Embed[Vector Embeddings]
        LangGraph[LangGraph Agent Graph]
        Direct[Direct Match Orchestrator]
    end
    TenderIngest --> Ext --> Embed
    MatchTask --> LangGraph
    MatchTask --> Direct
    LangGraph -->|Read/Write State| Mongo
    Direct --> Mongo
    FeedbackTask -->|Updates Weights| PG
```

## AI Pipeline — How It Works
1. **Tender Ingestion Pipeline**: When a PDF is uploaded (or fetched via Bidassist/Firecrawl), text is extracted via PyMuPDF (or OCR via Tesseract). The text is chunked and sent to Groq (LLaMA 3) to extract structured JSON requirements (turnover, sector, certifications). A 384‑dimensional embedding is generated and stored in PostgreSQL alongside the document in MongoDB.
2. **Hard Filter Engine**: A deterministic gauntlet that immediately disqualifies vendors failing strict binary requirements (e.g., vendor turnover is below the tender's strict minimum). No LLM tokens are wasted if a vendor is ineligible.
3. **Weighted Scoring Engine**: For eligible vendors, a 0‑100 score is computed across 7 dimensions (domain fit, geography, financial capacity, experience, certifications, capability similarity, and confidence).
4. **LLM Explanation Engine**: Groq analyzes the raw scores and filter results to generate a human‑readable executive summary, bulleted strengths, and risk factors, concluding with a definitive recommendation (e.g., "Strongly Recommended").
5. **LangGraph Agentic Pipeline**: An advanced orchestration path structured as a state machine. It begins with a **Planner Agent** that evaluates context (e.g., vendor completeness) to build a dynamic execution plan. The **Hybrid Retriever** blends semantic and keyword matching, conditionally invoking a **Reranker Agent** for ambiguous scores. After the LLM writes its rationale, a deterministic **Critic Agent** runs strict mathematical checks to suppress hallucinations and override rogue recommendations before notifying the user.
6. **Adaptive Feedback Learning Loop**: As users interact with matches, their signals trigger a Celery task that mathematically shifts the scoring weights for that specific vendor profile, ensuring the AI continuously aligns with business reality.
7. **Bidassist Integration**: `BidassistService` periodically pulls active tenders from the Bidassist public API, normalises the payload, deduplicates against existing records, and injects them into the same ingestion pipeline (PDFs are downloaded and processed, non‑PDF tenders are stored directly).
8. **Scheduled Portal Scraping**: `ScrapingService` reads `portal_configs.json` to drive Firecrawl‑backed scraping of configured government portals, applies the same deduplication logic, and routes new PDFs through the ingestion pipeline.

## Tech Stack
| Layer | Technologies |
|---|---|
| **Frontend** | React, Vite, Tailwind CSS, Recharts, TanStack Query, Axios |
| **Backend API** | FastAPI, Pydantic, Uvicorn |
| **Databases** | PostgreSQL, pgvector (Vector DB), MongoDB (Document DB), Redis |
| **AI / NLP** | LangChain, LangGraph, Groq API (LLaMA 3), `sentence-transformers` |
| **Async Processing** | Celery |
| **ORM & Migrations** | SQLAlchemy, Alembic |

## Project Structure
```text
TenderMatch/
├── backend/
│   ├── alembic/                # DB migrations
│   ├── app/
│   │   ├── agents/             # LangGraph nodes and state graph
│   │   ├── api/                # FastAPI routers (41 endpoints + admin sync)
│   │   ├── core/               # Settings, DB connections, Celery app
│   │   ├── db/models/          # SQLAlchemy and Mongo mappings
│   │   ├── services/           # Business logic, Hard Filter, Scoring, explanation, Bidassist, Scraping
│   │   └── tasks/              # Celery task definitions (including scheduled_tasks)
│   └── tests/                  # 10+ new Phase 5 integration tests
├── frontend/
│   └── src/
│       ├── components/         # React components, admin sync dashboard, etc.
│       ├── pages/              # 13 React views (incl. AdminSync)
│       └── services/           # Axios API clients
├── docker-compose.yaml
```

## API Overview
(All endpoints are documented in `API-Documentation.md`. Below are the new Phase 5 additions.)

### Admin Sync Control (`/admin/sync/*`)
- **POST `/admin/sync/trigger`** – Manually trigger the nightly Bidassist sync. Returns Celery `task_id` and status `queued`. **Role:** `SUPER` (or `ADMIN1` for testing).
- **GET `/admin/sync/logs`** – Retrieve the last 30 sync log entries (type, timestamps, status, counts). **Role:** `SUPER`.
- **GET `/admin/sync/status`** – Overview of sync health: last run, next scheduled run, total tenders in DB, and simple Bidassist connectivity check. **Role:** `SUPER`.

These endpoints are protected by the existing `require_role` dependency and use the Mongo `sync_logs` collection for persistence.

## Local Development Setup
1. **Clone repo**: `git clone <url> && cd TenderMatch`
2. **Environment Setup**: Copy `backend/.env.example` to `backend/.env` and fill in keys (`GROQ_API_KEY`, `BIDASSIST_API_KEY`, `FIRECRAWL_API_KEY`, etc.).
3. **Start Infrastructure**: `docker-compose up -d` to spin up PostgreSQL, MongoDB, and Redis.
4. **Database Migrations**: In the backend directory, run `alembic upgrade head`.
5. **Start Backend**: `uvicorn app.main:app --reload`.
6. **Start Frontend**: In a new terminal, `cd frontend && npm install && npm run dev`.
7. **Start Celery Worker**: `celery -A app.core.celery_app worker --loglevel=info -P gevent`.
8. **Start Celery Beat**: `celery -A app.core.celery_app beat --loglevel=info`.

## Environment Variables
| Variable | Purpose | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@localhost/db` |
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `REDIS_URL` | Redis message broker URL | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | Secret for signing tokens | `supersecret` |
| `GROQ_API_KEY` | Key for LLM inference | `gsk_...` |
| `BIDASSIST_API_URL` | Base URL for Bidassist API | `https://api.example-bidassist.com` |
| `BIDASSIST_API_KEY` | Key for Bidassist API | `YOUR_BIDASSIST_KEY` |
| `FIRECRAWL_API_KEY` | Key for Firecrawl scraper | `YOUR_FIRECRAWL_KEY` |

## Test Suite
| Test File | What It Tests | Test Count |
|---|---|---|
| `test_adaptive_feedback.py` | EMA math, fallback logic, normalization | 5 |
| `test_explanation_engine.py` | Groq prompting, recommendations, schemas | 17 |
| `test_hard_filter_engine.py` | Deterministic logic (turnover, geography) | 6 |
| `test_ingestion_pipeline.py` | Chunking, extraction unioning, text mapping | 13 |
| `test_langgraph_agent.py` | State routing, agent nodes, graph compilation | 15 |
| `test_planner_agent.py` | Planner Agent state routing, Redis caching, scoring | 8 |
| `test_match_api.py` | Match routes, async polling, feedback ingestion | 3 |
| `test_match_orchestrator.py` | Full sequential pipeline execution | 10 |
| `test_polyglot_flow.py` | Complete DB registration and storage flows | 3 |
| `test_scoring_engine.py` | Weighted dimensional calculations | 29 |
| `test_bidassist_sync.py` | Bidassist API integration, deduplication, scheduled task idempotency | 12 |
| `test_vendor_ingestion.py` | Unit tests: extraction service, merge logic, API stubs | 11 |
| `test_vendor_ingestion_e2e.py` | E2E pipeline, security (two-org isolation), EC1–EC8 edge cases, idempotency | 19 |
| **`test_tenders_api.py` / `test_scraping.py` / etc** | Additional integration tests and component tests | 35 |
| **Total** |  | **186** |

## Roadmap
- ✅ **Phase 1** — Core Platform (Multi‑tenancy, Auth, UI)
- ✅ **Phase 2** — AI Matching Pipeline (Extraction, Filtering, Scoring)
- ✅ **Phase 3** — LangGraph Agentic Pipeline (Stateful orchestration)
- ✅ **Phase 4** — Adaptive Feedback Learning (EMA weight updates)
- ✅ **Phase 5** — Bidassist Auto‑Ingestion & Scheduled Tender Scraping
- ✅ **Phase 6** — Agentic RAG, Critic Agent & Vendor Document Auto-Fill
- ✅ **Phase 7** — Conversational RAG (Chat with Tender)
- ⬜ **Phase 8** — Immutable Audit Ledger
- ⬜ **Phase 9** — Multilingual Support

---
