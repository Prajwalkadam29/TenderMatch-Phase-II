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

---

## 🛠️ Tech Stack

**Backend:**
- Python 3.10+
- FastAPI (REST framework)
- MongoDB & Motor (Asynchronous NoSQL Storage)
- FAISS & sentence-transformers (Embeddings & Semantic Match)
- PyMuPDF, jose (JWT)

**Frontend:**
- React (Vite)
- TypeScript
- Tailwind CSS (With Glassmorphism UI)
- Lucide Icons
- Axios

---

## 🖥️ How to Run & Test locally

### Prerequisites
1. **Python 3.10+**
2. **Node.js**
3. **MongoDB Server** (Running locally on `mongodb://localhost:27017`)

### Step 1: Start the Backend server
Open a terminal and navigate to the `backend` folder:
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
*API docs at: http://localhost:8000/docs*

### Step 2: Ingest Mock Tenders
Open a separate terminal inside `backend` and ingest some mock test data so the database isn't empty!
```powershell
# Ensuring you are activating your environment first
.\venv\Scripts\python.exe backend/scripts/ingest_tenders.py
```
*This inserts 10 realistic tenders into `tendermatch.tenders`.*

### Step 3: Start the Frontend Application
Open a new terminal and navigate to the root folder:
```powershell
npm install
npm run dev
```

### Step 4: End-to-End Walkthrough
1. **Register/Login** at `http://localhost:5173`.
2. Navigate to **Vendor Profile** via the sidebar. 
3. Carefully fill out all 3 phases of the structured profile Builder (ensure you add a valid Sub Domain using the `+ Add` button). Click **Submit Profile**.
4. Navigate to **AI Matching Engine**. 
5. Select your newly created Vendor Profile from the dropdown and hit **Run Structured Matching**.
6. The UI will hit the new Bulk Evaluator Endpoint, running your profile simultaneously against all 10 MongoDB Tenders.
7. Observe the incredibly detailed Match Cards highlighting your Disqualification reasons, Strong Matches, Semantic overrides, and Final Score multipliers!
