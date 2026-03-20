"""
test_matching_e2e.py
--------------------
End-to-end test for the full TenderMatch pipeline:
  1. Upload vendor document  → POST /upload/vendor
  2. Upload tender document  → POST /upload/tender
  3. Check index status      → GET  /match/status
  4. Run matching            → GET  /match/{vendor_id}
  5. Run matching + explain  → GET  /match/{vendor_id}?explain=true

Run from:  backend/
Command:   .\\venv\\Scripts\\python test_matching_e2e.py
"""

import urllib.request
import json
import sys
import time

BASE_URL  = "http://localhost:8000"
BOUNDARY  = "TenderMatchBoundaryE2E"
VENDOR_FILE = "test_vendor.txt"
TENDER_FILE = "test_tender.txt"


# ─── helpers ──────────────────────────────────────────────────────────────────

def _multipart_upload(endpoint: str, filepath: str) -> dict:
    """Upload a file using stdlib multipart/form-data — no requests needed."""
    import os
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        content = f.read()

    body = (
        b"--" + BOUNDARY.encode() + b"\r\n" +
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode() +
        b"Content-Type: text/plain\r\n\r\n" +
        content +
        b"\r\n--" + BOUNDARY.encode() + b"--\r\n"
    )

    req = urllib.request.Request(
        url=BASE_URL + endpoint,
        data=body,
        method="POST",
    )
    req.add_header("Content-Type", f"multipart/form-data; boundary={BOUNDARY}")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"   [HTTP ERROR] {e.code}: {e.read().decode()[:300]}")
        sys.exit(1)


def _get(path: str) -> dict:
    req = urllib.request.Request(BASE_URL + path)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ─── STEP 1: Upload vendor ─────────────────────────────────────────────────────

section("STEP 1 — Upload Vendor Document")
print(f"  File: {VENDOR_FILE}")
print("  POST /upload/vendor  (calls Groq LLM + generates embeddings) ...")
print("  ⏳ This may take 10–30 seconds ...")

vendor_resp = _multipart_upload("/upload/vendor", VENDOR_FILE)

vendor_id      = vendor_resp.get("id")
embedding_id   = vendor_resp.get("embedding_id")
vendor_keywords = vendor_resp.get("keywords", [])

print(f"\n  ✅ Vendor uploaded!")
print(f"     MongoDB ID   : {vendor_id}")
print(f"     FAISS ID     : {embedding_id}")
print(f"     Keywords     : {vendor_keywords[:5]}{'...' if len(vendor_keywords) > 5 else ''}")
print(f"\n  Structured Data:")
for k, v in vendor_resp.get("structured_data", {}).items():
    print(f"     {k:20s}: {str(v)[:80]}")


# ─── STEP 2: Upload tender ─────────────────────────────────────────────────────

section("STEP 2 — Upload Tender Document")
print(f"  File: {TENDER_FILE}")
print("  POST /upload/tender  (calls Groq LLM + generates embeddings) ...")
print("  ⏳ This may take 10–30 seconds ...")

tender_resp = _multipart_upload("/upload/tender", TENDER_FILE)

tender_id      = tender_resp.get("id")
tender_emb_id  = tender_resp.get("embedding_id")
tender_keywords = tender_resp.get("keywords", [])

print(f"\n  ✅ Tender uploaded!")
print(f"     MongoDB ID   : {tender_id}")
print(f"     FAISS ID     : {tender_emb_id}")
print(f"     Keywords     : {tender_keywords[:5]}{'...' if len(tender_keywords) > 5 else ''}")
print(f"\n  Structured Data:")
for k, v in tender_resp.get("structured_data", {}).items():
    print(f"     {k:20s}: {str(v)[:80]}")


# ─── STEP 3: Check status ──────────────────────────────────────────────────────

section("STEP 3 — Index Status")
print("  GET /match/status ...")
status = _get("/match/status")

print(f"\n  FAISS Index Size : {status['faiss_index_size']} vectors")
print(f"  Total Documents  : {status['total_documents']}")
print(f"  Vendors          : {status['total_vendors']}")
print(f"  Tenders          : {status['total_tenders']}")

if status["faiss_index_size"] < 2:
    print("\n  ⚠️  Index has fewer than 2 vectors. Matching may return no results.")
    print("      (This can happen if a previous run's FAISS store is gone.)")


# ─── STEP 4: Match vendor to tenders ──────────────────────────────────────────

section("STEP 4 — Match Vendor to Tenders")
print(f"  Vendor ID : {vendor_id}")
print(f"  GET /match/{vendor_id}?k=10 ...")

match_resp = _get(f"/match/{vendor_id}?k=10")

total = match_resp.get("total_matches", 0)
results = match_resp.get("results", [])

print(f"\n  ✅ {total} tender match(es) found\n")

for i, r in enumerate(results, 1):
    print(f"  Match #{i}")
    print(f"    Tender ID       : {r['tender_id']}")
    print(f"    File            : {r.get('tender_filename', '')}")
    print(f"    Semantic Score  : {r['semantic_score']:.4f}")
    print(f"    Keyword Score   : {r['keyword_score']:.4f}")
    print(f"    ★ FINAL SCORE  : {r['final_score']} / 100")

    ts = r.get("tender_summary", {})
    print(f"    Scope           : {str(ts.get('scope', ''))[:80]}")
    print(f"    Location        : {ts.get('location', 'N/A')}")
    print(f"    Certifications  : {ts.get('certifications', [])}")
    print(f"    Keywords        : {r.get('tender_keywords', [])[:4]}")
    print()


# ─── STEP 5: Match with Groq explanation ──────────────────────────────────────

section("STEP 5 — Match with Groq Explanation (explain=true)")
print(f"  GET /match/{vendor_id}?k=1&explain=true ...")
print("  ⏳ Calling Groq for explanation ...")

explain_resp = _get(f"/match/{vendor_id}?k=1&explain=true")
explain_results = explain_resp.get("results", [])

if explain_results:
    r = explain_results[0]
    print(f"\n  Top Match  : {r.get('tender_filename', r['tender_id'])}")
    print(f"  Final Score: {r['final_score']} / 100")
    print(f"\n  📝 Explanation:\n")
    print(f"     {r.get('explanation', '(none returned)')}")
else:
    print("  (No results)")


# ─── Done ─────────────────────────────────────────────────────────────────────

section("DONE ✅")
print(f"  Vendor ID (save this): {vendor_id}")
print(f"  Tender ID            : {tender_id}")
print(f"  Swagger UI           : http://localhost:8000/docs")
print(f"  Match endpoint       : GET http://localhost:8000/match/{vendor_id}")
print()
