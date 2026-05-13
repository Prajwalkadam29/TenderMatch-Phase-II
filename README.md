# TenderMatch 🚀 — Production-Grade AI Matching Engine

TenderMatch is a high-performance, enterprise-ready Vendor–Tender matching ecosystem. Moving beyond simple keyword searches, it leverages **vector embeddings**, **distributed task queues**, and **hard-filter business logic** to deliver mathematically precise and explainable procurement intelligence.

---

## 🏗️ Technical Architecture & Refinements

### 1. Hardened Document Ingestion Pipeline (Phase 1)
- **MIME Security**: Implemented binary-level inspection using `python-magic` to thwart MIME-spoofing attacks.
- **Path Sanitization**: Integrated Werkzeug's `secure_filename()` to prevent path traversal vulnerabilities during multi-tenant file uploads.
- **Distributed Extraction**: Offloaded PDF parsing and Groq LLM extraction to **Celery workers** using a robust isolated connection pool manager (`celery_db.py`).

### 2. High-Performance Matching Engine (Phase 2 & 3)
- **FAISS Vector Scaling**: Optimized retrieval using `reconstruct_vectors_batch()` to eliminate N+1 thread starvation during high-concurrency vector lookups.
- **CPU Offloading**: Offloaded heavy NumPy matrix similarity computations to a dedicated thread pool using `asyncio.to_thread`, keeping the FastAPI event loop unblocked.
- **Strict Hard Filters**: Implemented deterministic disqualification logic for:
  - **Certifications**: Mandatory license intersection checks.
  - **Geography**: Operational state validation with "willingness to expand" logic.

### 3. Enterprise Database & State Management (Phase 4 & 5)
- **MongoDB Schema Enforcement**: Applied strict BSON `$jsonSchema` validation at the database engine level for `documents` and `vendor_profiles` to ensure data integrity.
- **Stateless Web Scraping**: Refactored the `TenderTiger` scraper to use **Redis set operations** (`SISMEMBER` / `SADD`) for duplicate tracking, making the scraping pipeline distributed and stateless.
- **Rate Limiting & CORS**: Secured API surfaces with Redis-backed rate limiting and environment-driven CORS origin matching.

### 4. Distributed Logging & Observability (Phase 7)
- **Structured JSON Logging**: Replaced standard text logs with machine-readable JSON formatting across the entire stack for seamless ELK/Datadog integration.
- **Request Tracing**: Implemented `X-Request-ID` correlation middleware that tracks request lifecycles across async tasks and threads using `ContextVars`.

### 5. Production DevOps & Containerization (Phase 7)
- **Multi-Stage Docker Builds**: Created highly optimized, lean production images using a dual-stage build process:
  - `builder` stage: Compiles heavy C++ dependencies (FAISS).
  - `production` stage: Minimal `slim` runner with zero build-tools, running under a non-root `appuser` (UID 1000).

---

## 🛠️ Tech Stack

**Backend:**
- **Core**: FastAPI, Pydantic v2
- **Data**: MongoDB (Motor), Redis (Session & Tracking)
- **AI**: FAISS (Vector DB), Sentence-Transformers (`all-MiniLM-L6-v2`), Groq LLM
- **Task Orchestration**: Celery (Beat & Worker)
- **Security**: JWT (Jose), Bcrypt, Python-Magic (MIME check)

**Frontend:**
- **Framework**: React 18 (Vite), TypeScript
- **Styling**: Vanilla CSS + Tailwind (Glassmorphic Design)
- **State/Auth**: Axios with 401 Interceptors, Custom AuthContext

---

## 🖥️ Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Node.js 18+

### 1. Infrastructure Setup
Spin up the containerized database and broker:
```bash
docker compose up -d
```
*MongoDB: localhost:27018 | Redis: localhost:6380*

### 2. Backend Installation
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Worker Execution
Open a separate terminal to run the document extraction and matching workers:
```bash
python -m celery -A app.core.celery_app worker --pool=solo --loglevel=info
```

### 4. Frontend Installation
```bash
npm install
npm run dev
```

---

## 🧪 Production Verification Suite

1. **Structured Log Audit**:
   Verify logs are produced in JSON format with correlation IDs:
   ```json
   {"timestamp": "...", "level": "INFO", "message": "...", "request_id": "..."}
   ```
2. **Rate Limit Test**:
   Spam the `/auth/login` endpoint to trigger the Redis-backed 429 response.
3. **MIME Validation Test**:
   Rename a `.txt` file to `.pdf` and attempt an upload; the server will reject it via magic-byte inspection.
4. **Scraper Deduplication**:
   Run `run_automated_scraper()` multiple times; verify Redis prevents redundant MongoDB insertions.

---

**TenderMatch AI Engine v2.5** · *Built for Production, Scaled for Growth.*
