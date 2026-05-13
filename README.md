# TenderMatch (Phase 2) 🚀

TenderMatch is an advanced, AI-powered Vendor–Tender matching engine. Moving beyond simple textual matching, Phase 2 implements a **Structured Vendor Profile system** alongside an intelligent **Structured Matching Engine**. It performs strict eligibility filtering (hard filters), calculates a granular weighted score across key business dimensions, integrates semantic AI capabilities (Sentence Transformers), and scales results based on mathematically derived profile completeness metrics. 

---

## 🚀 Key Features

### 1. Multi-tenant B2B Architecture & RBAC
- **Organizations & Users**: Secure registration logic separating accounts by `org_id` and `user_id`. Each document and vendor profile belongs to a specific tenant.
- **Roles**: Enforces Route Guards separating ADMIN level controls from standard USER actions seamlessly across the React Vite frontend and FastAPI backend.

### 2. Multi-phase Vendor Profile Builder
A beautiful, modern React application that dynamically collects Vendor Data across 3 critical phases:
- **Phase 1: Identity & Compliance**: Legal company name, GSTINs, Udyam Registration, and regulatory compliance flags (like Litigations or Debarment).
- **Phase 2: Business & Financials**: Dynamic multi-input domains & sub-domains, annual turnover arrays, operational & registered geographies, and capability freetext indexing.
- **Phase 3: Past Projects & Certifications**: Recording previous highest project values, ISO certifications, and mandatory domain licenses.
*Data is saved directly to the highly-structured `vendor_profiles` collection in MongoDB.*

### 3. Structured Matching Engine
Instead of just matching uploaded static PDFs, the engine evaluates a Vendor Profile dynamically against structured `tenders` in MongoDB.

#### Step 1: Strict Hard Eligibility Filters
The engine automatically **disqualifies (returns 0 score)** a vendor if any of these critical requirements fail:
1. **Blacklist Check**: Vendor must not be blacklisted or debarred.
2. **Domain Match**: Vendor’s `primary_domains` must overlap with the tender.
3. **Geographic Check**: Vendor must be operational/registered in the target state, or explicitly marked as `willing_to_operate_in_new_states`.
4. **Mandatory Certifications**: Any mandatory cert array (e.g., "Valid Electrical Contract License") must fully intersect with the vendor's held licenses.
5. **Financial Threshold**: The vendor's average annual turnover must exceed the tender's `min_avg_turnover`.

#### Step 2: Weighted Field-Wise Scoring
If the vendor passes all hard filters, a similarity score `[0, 1]` is generated across 7 weighted dimensions:
- 📊 **Domain Match (20%)**: Primary and sub-domain exact/partial intersects.
- 🌍 **Geography Match (15%)**: Weighted by Registered (1.0) vs Preferred (0.9) vs Operational (0.8) vs Willing to expand (0.5).
- 💰 **Financial Capacity (15%)**: Evaluates vendor turnover against total tender estimated value.
- 🏗️ **Experience Match (20%)**: Analyzes the magnitude of the largest previous single project against the current tender size.
- 📜 **Certification Match (10%)**: Jaccard similarity of extra certifications against tender bonus requirements.
- 🧠 **Semantic / Requirement Match (15%)**: Uses AI via **Sentence-Transformers** (`all-MiniLM-L6-v2`) to compare the vendor's freetext `capability_description` to the tender's overall `scope` using cosine similarity.
- ⚖️ **Compliance & Risk (5%)**: Deductions for active litigations, ESI/PF non-compliance, etc.

#### Step 3: Completeness Confidence Boost
The raw weighted score is multiplied by the Vendor Profile's completeness percentage (`profile_completeness_pct / 100`) to generate the Final Score.

#### Step 4: Explainable Output Wrapper
The engine inserts the final result into the `match_results` MongoDB collection using a highly explicit JSON Schema wrapper detailing the granular scores, the hard-filter rationale, and a human-readable AI-Style explanation paragraph. 

### 4. Asynchronous Task Queue & Document Ingestion Pipeline ⚙️
- **Celery & Redis Integration**: Offloads resource-heavy, blocking extraction tasks (PDF text extraction, Groq LLM parsing, and FAISS vector index updates) from the main request thread to asynchronous background worker processes.
- **Task Status Tracking**: Real-time status endpoints (`GET /documents/{doc_id}`) tracking the async state (`processing`, `completed`, `failed`) and returning the updated document schema.

### 5. Production-Grade API Security & Gatekeeping 🔒
- **Stateful JWT Blacklisting (`/auth/logout`)**: Implements instant session revocation. Logged-out JWTs are stored in Redis with their respective TTL, instantly blocking subsequent API calls in the authentication dependency middleware.
- **Redis-Backed Rate Limiting**: Leverages `fastapi-limiter` to protect high-impact endpoints from abuse, including:
  - `POST /auth/login` → 5 requests per minute (stops brute-forcing).
  - `POST /upload/vendor` & `/upload/tender` → 10 uploads per minute (prevents worker-pool resource starvation).
  - `GET /match/{vendor_id}` → 5 matching computations per minute (protects heavy vector matching + Groq LLM explanation runs).

---

## 🛠️ Tech Stack

**Backend:**
- Python 3.10+
- FastAPI (REST framework)
- MongoDB & Motor (Asynchronous NoSQL Storage)
- FAISS & sentence-transformers (Embeddings & Semantic Match)
- Celery (Asynchronous background worker orchestration)
- Redis (In-Memory Message Broker, Session Storage & Rate Limiting)
- PyMuPDF, jose (JWT)
- Gevent (Local async coroutine worker execution engine)

**Frontend:**
- React (Vite)
- TypeScript
- Tailwind CSS (With Glassmorphic UI)
- Lucide Icons
- Axios

---

## 🖥️ How to Run & Test locally

### Prerequisites
1. **Python 3.10+**
2. **Node.js**
3. **Docker Desktop** (To spin up containerized MongoDB & Redis)

### Step 1: Start Containerized Infrastructure
Run Docker Compose from the root directory to spin up isolated database and broker instances:
```powershell
docker compose up -d
```
*Note: This isolates services from any local Windows installs: MongoDB runs on `localhost:27018` and Redis runs on `localhost:6380`.*

### Step 2: Start the Backend server
Navigate to the `backend` folder, configure your environment, and launch FastAPI:
1. Create a `backend/.env` file:
   ```env
   MONGODB_URI=mongodb://localhost:27018
   DATABASE_NAME=tendermatch
   REDIS_URL=redis://localhost:6380/0
   JWT_SECRET=your_super_secret_key
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   GROQ_API_KEY=your_groq_api_key
   ```
2. Activate environment and run:
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```
*API docs are available at: http://localhost:8000/docs*

### Step 3: Run the Celery Asynchronous Worker
Open a separate terminal in `backend`, activate your virtual env, and spin up the worker pool (optimized for Windows environments via coroutines):
```powershell
.\.venv\Scripts\activate
python -m celery -A app.core.celery_app worker --pool=gevent --concurrency=4 --loglevel=info
```

### Step 4: Ingest Mock Tenders
Run the bulk ingest script to populate your isolated database:
```powershell
.\.venv\Scripts\python.exe scripts/ingest_tenders.py
```

### Step 5: Start the Frontend Application
Open a new terminal and navigate to the root directory:
```powershell
npm install
npm run dev
```

### Step 6: End-to-End Walkthrough
1. **Register/Login** at `http://localhost:5173`.
2. Navigate to **Vendor Profile** and fill out all 3 phases. Hit **Submit Profile**.
3. Upload PDF documents to test the **Celery-backed extraction worker** under the Upload module. Poll `/api/upload/documents/{doc_id}` to watch its state progress from `processing` to `completed`.
4. Try spamming the `POST /auth/login` or `POST /upload/vendor` endpoints to test the active **Redis Rate Limiters**.
5. Test instant token revocation by clicking **Logout**, then attempt to hit any secure endpoint with the blacklisted token.
6. Navigate to **AI Matching Engine**, select your profile, and hit **Run Structured Matching** to see the scoring and Groq LLM explanations.ntic overrides, and Final Score multipliers!
