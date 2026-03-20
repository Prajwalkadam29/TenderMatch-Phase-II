# TenderMatch 🚀

TenderMatch is an AI-powered Vendor–Tender matching engine. It leverages Generative AI (Groq LLM) to extract structured data and keywords from procurement documents (PDFs/TXTs), generates semantic embeddings using Sentence Transformers, and uses FAISS to quickly find the best tender matches for a given vendor based on semantic and keyword similarity.

---

## 🧠 How It Works

### 1. Document Upload & Extraction
- Users upload a Vendor Profile or a Tender Document (PDF/TXT).
- The text is extracted and passed to **Groq's LLaMA-based LLM**, which performs structured extraction (Scope, Eligibility, Location, Certifications) and identifies domain-specific **keywords**.

### 2. Semantic Embedding
- The extracted structured data and keywords are combined into a `search_text`.
- The `sentence-transformers` library (using `all-MiniLM-L6-v2`) converts this text into a high-dimensional vector.
- The same embedding model also converts the individual extracted keywords into vectors.

### 3. Storage & Indexing
- **MongoDB** stores the raw document, structured data, keywords, and keyword embeddings.
- **FAISS (Facebook AI Similarity Search)** creates an in-memory (and disk-persisted) index for ultra-fast document-level semantic search.

### 4. Matching Engine
When a Vendor ID is queried:
1. The **Document Vector** is compared against all Tender Vectors in FAISS (Cosine Similarity).
2. The **Keyword Vectors** of the Vendor and Tender are cross-compared to find the best matching capabilities (Keyword Matrix Multiplication).
3. The final score is computed dynamically (`0.75 * Semantic_Score + 0.25 * Keyword_Score`).
4. (Optional) Groq LLM can be triggered to generate a human-readable explanation of *why* the score is high or low.

---

## 🛠️ Tech Stack

**Backend:**
- Python 3.10+
- FastAPI (REST framework)
- MongoDB & Motor (Asynchronous NoSQL Storage)
- FAISS (Vector Indexing & Similarity Search)
- sentence-transformers (Local Embedding Model)
- PyMuPDF (PDF Text Extraction)
- Groq Cloud API (LLM JSON Extraction & Explanations)

**Frontend:**
- React (Vite)
- TypeScript
- Tailwind CSS
- Lucide Icons
- Axios (API Calls)

---

## 🚀 How to Run

### Prerequisites
1. **Python 3.10+**
2. **Node.js**
3. **MongoDB Server** (Running locally on `mongodb://localhost:27017` or via Docker)
4. **Groq API Key** (Set via changing the `config.py` default or creating a `.env` in the backend folder).

### Step 1: Start the Backend

Open a terminal and navigate to the `backend` folder:
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
*The backend API documentation will be available at: http://localhost:8000/docs*

*(Note: The first time you upload a document, the `sentence-transformers` model ~90MB will be downloaded automatically).*

### Step 2: Start the Frontend

Open a **new, separate terminal** and navigate to the root folder:
```powershell
npm install
npm run dev
```
*The frontend application will be available at: http://localhost:5173*

### Step 3: Test the Application

1. **Register/Login**: Open the frontend (`http://localhost:5173`), register a new user, and log in.
2. **Upload Documents**: Navigate to the "Upload Docs" page. Upload a vendor document and a tender document. (You can use the `backend/test_vendor.txt` and `backend/test_tender.txt` as examples).
3. **AI Matching**: Navigate to the "AI Matching" page. Copy the MongoDB ID of your uploaded vendor, paste it into the search box, and click "Find Matching Tenders".
4. **(Optional) Run the Backend CLI Test End-to-End**: 
   Inside the `backend` folder, you can run: `python test_matching_e2e.py` to see the complete flow without the UI.

---

## 🔑 Environment Variables & Configuration

**Backend configuration** (`backend/app/core/config.py`):
You can override these values by creating a `backend/.env` file:
```ini
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=tendermatch
JWT_SECRET=your_super_secret_string
GROQ_API_KEY=your_groq_api_key_here
```

**Frontend configuration** (`.env` at frontend root):
```ini
VITE_API_URL=http://localhost:8000
```
