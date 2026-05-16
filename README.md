# TenderMatch AI 🎯

> **Enterprise-Grade AI-Powered Public Procurement Matching Platform**

TenderMatch AI is a production-ready, polyglot-persistence matching engine designed to bridge the gap between complex government/enterprise procurement opportunities (Tenders) and qualified service providers (Vendors). 

By leveraging Large Language Models (LLMs) for unstructured data extraction and Vector databases for semantic similarity, TenderMatch automates the laborious process of tender evaluation, offering deterministic eligibility filtering alongside probabilistic capability matching.

---

## 📖 Table of Contents
- [Problem Statement](#-problem-statement)
- [Solution Overview](#-solution-overview)
- [Current Implemented Features](#-current-implemented-features)
- [Architecture Overview](#-architecture-overview)
- [Tech Stack](#-tech-stack)
- [System Design](#-system-design)
  - [Polyglot Persistence Strategy](#polyglot-persistence-strategy)
  - [AI Matching Pipeline](#ai-matching-pipeline)
  - [Tender Ingestion Pipeline](#tender-ingestion-pipeline)
- [Project Structure](#-project-structure)
- [API Overview](#-api-overview)
- [Environment Setup](#-environment-setup)
- [Local Development Setup](#-local-development-setup)
- [Docker Infrastructure](#-docker-infrastructure)
- [Production Deployment Notes](#-production-deployment-notes)
- [Security Considerations](#-security-considerations)
- [Roadmap & Future Improvements](#-roadmap--future-improvements)
- [License](#-license)

---

## 🚨 Problem Statement

Public procurement and enterprise tendering are plagued by extreme friction:
1. **Unstructured Data:** Tenders are published as massive, complex PDFs (often scanned images or poorly formatted text).
2. **Evaluation Fatigue:** Vendors spend hundreds of hours manually parsing 500+ page documents just to determine basic eligibility.
3. **Missed Opportunities:** Keyword-based search fails to capture semantic capabilities (e.g., matching "NLP Engineering" to "Text Classification Services").
4. **Delayed Intelligence:** By the time a vendor discovers an eligible tender, the submission window is often closing.

## 💡 Solution Overview

TenderMatch acts as an automated procurement intelligence layer:
1. **Multi-Modal Extraction:** Ingests PDFs using a cascading pipeline (PyMuPDF for text, PDFPlumber for tables, Tesseract OCR for scans).
2. **LLM Structuring:** Uses Groq-powered LLMs to extract rigid JSON schemas (Turnover, Certifications, Scope, Deadlines) from unstructured text chunks.
3. **Semantic Matching:** Generates dense vector embeddings (`all-MiniLM-L6-v2`) for both Vendor Capabilities and Tender Scope.
4. **Hybrid Scoring:** Combines hard deterministic filters (e.g., "Must have ISO 9001", "Must have $5M turnover") with soft semantic similarity scores using `pgvector`.
5. **Real-time Notifications:** Dispatches automated email alerts when high-confidence matches are found.

---

## ✨ Current Implemented Features

### 🟢 Fully Implemented & Working
* **Polyglot Persistence Model:** PostgreSQL (Source of truth, auth, vectors) + MongoDB (Document payload store).
* **Robust Auth System:** JWT-based authentication, RBAC (Admin/User), and isolated Organizational tenancy.
* **Document Ingestion Pipeline:** Async Celery tasks handling PDF text/table/OCR extraction and overlapping text chunking (to bypass LLM token limits).
* **LLM Information Extraction:** Groq API integration for translating legal tender text into structured JSON.
* **Semantic Vector Generation:** SentenceTransformers (`all-MiniLM-L6-v2`) creating 384-dimensional embeddings.
* **Hybrid Matching Engine:** Configurable weighting system combining financial, geographic, domain, and semantic capability scores.
* **Automated Email Alerts:** Premium HTML email notifications triggered asynchronously for matches scoring >75%.
* **Frontend SPA:** React + TypeScript + Vite frontend utilizing TanStack Query for aggressive caching and optimized state management.
* **Dockerized Infrastructure:** Pre-configured `docker-compose.yaml` spinning up Postgres (`pgvector`), MongoDB, Redis, and Celery workers.
* **Database Migrations:** Fully configured Alembic pipeline for PostgreSQL schema evolution.

### 🟡 In Progress / Partially Implemented
* **Interactive Dashboard:** Basic metrics exist, but advanced Recharts visualizations for win-probability trends are pending.
* **Multi-Language Support:** LLM can read multiple languages, but the UI and prompt chains are optimized for English.

---

## 🏗 Architecture Overview

TenderMatch utilizes an event-driven, microservice-oriented architecture designed for horizontal scalability and high availability.

```mermaid
graph TD
    Client[Client (React/Vite)] -->|REST API| FastAPI[FastAPI Backend]
    
    FastAPI -->|Auth & Vendor Data| PG[(PostgreSQL + pgvector)]
    FastAPI -->|Fetch Raw Tenders| Mongo[(MongoDB)]
    
    FastAPI -->|Publish Task| Redis((Redis Broker))
    Redis -->|Consume Task| Celery[Celery Workers]
    
    Celery -->|1. Extract Text/Tables| PDFParser[PDF Pipeline (PyMuPDF/OCR)]
    Celery -->|2. Structure Data| Groq[Groq LLM API]
    Celery -->|3. Generate Vectors| EmbeddingLib[all-MiniLM-L6-v2]
    
    Celery -->|Write Structured| Mongo
    Celery -->|Write Vectors| PG
    
    Celery -->|4. High Match Alert| SMTP[SMTP Email Service]
    
    subgraph Data Layer
        PG
        Mongo
        Redis
    end
```

---

## 🛠 Tech Stack

**Backend:**
* **Framework:** FastAPI (Python 3.10+)
* **Task Queue:** Celery + Redis
* **ORM & Migrations:** SQLAlchemy 2.0 (Asyncpg), Alembic
* **AI/ML:** Groq API (LLaMA 3), `sentence-transformers`
* **Extraction:** `pymupdf`, `pdfplumber`, `pytesseract`
* **Testing:** Pytest, HTTPX

**Databases:**
* **PostgreSQL (16+):** Relational truth, Auth, `JSONB` for Vendor Profiles, `pgvector` for semantic embeddings.
* **MongoDB (6.0+):** NoSQL document store for massive, unstructured raw tender text and LLM JSON outputs.

**Frontend:**
* **Framework:** React 18, Vite, TypeScript
* **State/Data Fetching:** TanStack Query (React Query)
* **Styling:** Vanilla CSS / Design Tokens

**DevOps & Infrastructure:**
* **Containerization:** Docker, Docker Compose
* **Process Monitoring:** Celery Flower

---

## ⚙️ System Design

### Polyglot Persistence Strategy
Why two databases?
1. **PostgreSQL (`pgvector`)**: Acts as the absolute source of truth. Manages `Users`, `Organizations`, and `VendorProfiles` (stored as flexible `JSONB`). Crucially, it stores the 384-dimensional vector embeddings for sub-millisecond semantic search via HNSW indexes.
2. **MongoDB**: Acts as a high-throughput sink for incoming documents. Tenders can be hundreds of pages long. Storing megabytes of raw text and unpredictable LLM-extracted JSON hierarchies in Postgres leads to row-bloat and poor cache performance. MongoDB handles this unstructured payload effortlessly. The two databases are linked via a `mongo_id` indexed bridge column in Postgres.

### Tender Ingestion Pipeline
1. **Upload:** User uploads PDF. FastAPI saves bytes to disk/blob storage and returns a `202 Accepted`.
2. **Message Queue:** Task is dispatched to Redis.
3. **Cascading Extraction (Worker):**
   - Attempts fast text extraction via PyMuPDF.
   - Parses complex pricing/technical grids via PDFPlumber.
   - If empty (scanned image), falls back to Tesseract OCR.
4. **Chunking:** Text is split into 2,000-character overlapping chunks to respect LLM context windows.
5. **LLM Structuring:** Groq API converts legalese into structured JSON (Turnover, Exp, Certs).
6. **Vectorization:** A synthesized "Search Text" is embedded using local SentenceTransformers.
7. **Persistence & Notification:** Data is written to Mongo/Postgres. An observer pattern triggers a match cycle against all organizational vendor profiles, dispatching an email if score > 75%.

### AI Matching Pipeline
The Matching Engine evaluates candidates using a **Hybrid Scoring System**:
* **Deterministic Filters (Hard Pass/Fail):** Instantly disqualifies vendors if they are blacklisted, lack mandatory turnover, or operate outside allowed geographic bounds.
* **Probabilistic Scoring (Soft Weights):**
  - Domain Fit (25%)
  - Financial Capacity Ratio (20%)
  - Geographic Proximity (15%)
  - Experience / Track Record (15%)
  - Certification Overlap (10%)
  - Semantic Capability Similarity via Cosine Distance (10%)
  - Profile Completeness Confidence (5%)

---

## 📂 Project Structure

```text
tendermatch/
├── backend/
│   ├── alembic/                 # PostgreSQL Migration Scripts
│   ├── app/
│   │   ├── api/                 # FastAPI Route Handlers (Auth, Tenders, Match)
│   │   ├── core/                # Config, DB connections, Celery setup
│   │   ├── db/                  # SQLAlchemy ORM Models (User, Org, VendorProfile, Tender)
│   │   ├── services/            # Core Business Logic (Matching, PDF, Email, LLM)
│   │   └── tasks/               # Celery Background Workers (Ingestion, Notifications)
│   ├── scripts/                 # Init scripts (init_pgvector.sql)
│   ├── tests/                   # Pytest integration suite
│   ├── requirements.txt         
│   └── alembic.ini              
├── frontend/
│   ├── public/                  
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   ├── pages/               # Dashboard, Upload, AIMatching, TenderDetail
│   │   ├── services/            # Axios API clients
│   │   └── main.tsx             # Entry point (TanStack Query Provider)
│   ├── package.json             
│   └── vite.config.ts           
├── docker-compose.yaml          # Infrastructure definition
├── README.md                    # Project documentation
└── .gitignore                   
```

---

## 🔌 API Overview

*All endpoints are prefixed with `/api/v1` (or relative to setup).*

### Authentication (`/auth`)
* `POST /auth/register` - Create Organization + Admin User.
* `POST /auth/login` - Authenticate and receive JWT.

### Vendor Profiles (`/vendor-profiles`)
* `POST /vendor-profiles/` - Create a comprehensive JSONB profile.
* `GET /vendor-profiles/me` - Fetch active profiles for the current user.

### Document Management (`/upload`)
* `POST /upload/tender` - Upload PDF -> Returns Task ID.
* `GET /upload/status/{task_id}` - Poll Celery task status.

### AI Matching (`/match`)
* `POST /match/run` - Trigger matching engine for a specific Vendor Profile. Returns top K tenders with explanations.
* `GET /match/tender/{tender_id}` - Get full tender payload (from Mongo) + Match analysis.

---

## 🔐 Environment Setup

Create a `.env` file in the `backend/` directory. **Never commit this file.**

```env
# Backend Environment Configuration
ENVIRONMENT=development

# Security
JWT_SECRET=your_super_secret_64_char_hex_string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Databases
MONGODB_URI=mongodb://localhost:27018
DATABASE_NAME=tendermatch

POSTGRES_URI=postgresql+asyncpg://tendermatch:changeme@localhost:5433/tendermatch
POSTGRES_DB=tendermatch
POSTGRES_USER=tendermatch
POSTGRES_PASSWORD=changeme

REDIS_URL=redis://localhost:6380/0

# External APIs
GROQ_API_KEY=gsk_your_groq_api_key

# Email Service (SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your_app_specific_password
FROM_EMAIL=no-reply@tendermatch.com

# Frontend Context
FRONTEND_URL=http://localhost:5173
```

---

## 🐳 Docker Infrastructure

The project utilizes Docker Compose to orchestrate the foundational data layer.

1. **Start Infrastructure:**
   ```bash
   docker-compose up -d postgres mongodb redis celery_worker celery_beat
   ```
2. **Verify Health:**
   Ensure the `tendermatch_postgres` container successfully executes the `init_pgvector.sql` script on first boot to enable the `vector` extension.

*Note: The FastAPI app and Vite frontend are designed to run locally on the host during development, connecting to the exposed Docker ports (5433, 27018, 6380).*

---

## 💻 Local Development Setup

### 1. Database Migrations (Backend)
With the Docker infrastructure running, initialize the PostgreSQL schema:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run Alembic migrations
alembic upgrade head
```

### 2. Start FastAPI Server
```bash
# From the backend directory
uvicorn app.main:app --reload --port 8000
```

### 3. Start Frontend App
```bash
cd frontend
npm install
npm run dev
```

### 4. Run Automated Tests
```bash
cd backend
python -m pytest tests/test_polyglot_flow.py -v
```

---

## 🚀 Production Deployment Notes

To take this application to production, consider the following architecture hardening steps:

1. **Vector Indexing:** The current schema utilizes raw Cosine Similarity scans. For >1M tenders, implement an **HNSW** (Hierarchical Navigable Small World) index in Alembic:
   ```sql
   CREATE INDEX ON tenders USING hnsw (embedding vector_cosine_ops);
   ```
2. **Gunicorn & Uvicorn Workers:** Wrap the FastAPI application in Gunicorn with Uvicorn worker classes to handle concurrent connection pooling efficiently.
3. **Secret Management:** Move from `.env` files to AWS Secrets Manager or HashiCorp Vault.
4. **Celery Auto-Scaling:** Configure Celery workers to scale based on the Redis queue length (`sqs` or `rabbitmq` recommended for production over Redis).

---

## 🛡️ Security Considerations

* **Rate Limiting:** Implemented via `fastapi-limiter` using Redis to protect public endpoints.
* **Organizational Isolation:** All queries strictly enforce tenancy via the `org_id` foreign key. A user can never evaluate a tender or profile belonging to another tenant.
* **File Validation:** The `python-magic` library validates MIME types securely; malicious files disguised as PDFs are rejected before parsing.
* **SQL Injection:** Complete prevention via SQLAlchemy 2.0 parameterized execution.

---

## 🗺 Roadmap & Future Improvements

- [ ] **Multi-Agent Evaluation:** Introduce a secondary "Devil's Advocate" LLM agent to critique the initial match score before presenting it to the user.
- [ ] **Web Scraping Integration:** Activate the `celery_beat` scheduled tasks to automatically scrape active government portals (e.g., SAM.gov, eProcure) nightly.
- [ ] **Conversational RAG:** Allow users to "Chat with the Tender" (e.g., "What are the exact SLA penalties in Section 4?") using the existing vectors.
- [ ] **Export Engine:** Generate pre-filled compliance matrices and bid proposal templates as downloadable Word documents.

---

## 📄 License

Copyright © 2026 TenderMatch. All rights reserved.
*This is proprietary software intended for authorized enterprise usage.*
