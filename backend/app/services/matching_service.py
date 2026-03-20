"""
matching_service.py
-------------------
Core matching engine: Vendor → Top-K Tender matching.

Algorithm:
  1. Fetch vendor doc from MongoDB
  2. Encode vendor search_text → query vector
  3. Reconstruct all tender doc vectors from FAISS
  4. Compute semantic_doc_score  = cosine_sim(vendor_vec, tender_vec)
  5. Compute keyword_score via best-match keyword embedding comparison:
       for each tender_keyword_embedding:
           best = max(dot(tender_kw, vendor_kw)  for vendor_kw)
       keyword_score = mean(best scores)
  6. final_score = 0.75 * doc_score + 0.25 * keyword_score   → scaled to 0–100
  7. Optionally call Groq to generate a human-readable explanation

Notes:
  - Vectors are L2-normalised in the embedding service, so dot product = cosine sim
  - keyword_embeddings stored in MongoDB as list[list[float]] — loaded as np arrays
  - FAISS search is used as pre-filter (over-fetch k*5 from full index) → filter to tenders
  - Falls back gracefully when keyword_embeddings are absent (keyword_score = 0)
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from bson import ObjectId

from app.core.database import get_db
from app.services.embedding_service import get_embedding_service
# (Groq client imported lazily inside _generate_explanation to keep import clean)

logger = logging.getLogger(__name__)

# ─── Scoring weights ─────────────────────────────────────────────────────────

W_DOC     = 0.75
W_KEYWORD = 0.25
SCORE_SCALE = 100.0


# ─── Public entry point ───────────────────────────────────────────────────────

async def match_vendor_to_tenders(
    vendor_id: str,
    top_k: int = 10,
    explain: bool = False,
    current_user: dict = None,
) -> list[dict]:
    """
    Find top-K tenders for a given vendor.

    Args:
        vendor_id: MongoDB _id string of the vendor document
        top_k:     Number of top results to return
        explain:   If True, call Groq LLM to generate match explanation

    Returns:
        List of match dicts, sorted by final_score descending.
    """
    db = get_db()
    emb_svc = get_embedding_service()

    # ── 1. Fetch vendor from MongoDB ──────────────────────────────────────────
    tenant_filter = {}
    if current_user:
        org_id = current_user.get("org_id")
        if org_id:
            tenant_filter["org_id"] = org_id
        else:
            tenant_filter["uploaded_by"] = str(current_user["_id"])

    vendor_query = {
        "_id": ObjectId(vendor_id),
        "type": "vendor",
        **tenant_filter
    }

    try:
        vendor_doc = await db.documents.find_one(vendor_query)
    except Exception:
        return []

    if not vendor_doc:
        return []

    vendor_search_text   = vendor_doc.get("search_text", "")
    vendor_kw_embeddings = _load_kw_matrix(vendor_doc.get("keyword_embeddings", []))

    # ── 2. Encode vendor search_text → query vector ───────────────────────────
    vendor_vec: np.ndarray = await emb_svc.encode_text(vendor_search_text)
    # shape: (384,) — already L2-normalised

    # ── 3. Load ALL tender docs with embedding_id from MongoDB ────────────────
    tender_query = {
        "type": "tender",
        "embedding_id": {"$ne": None},
        **tenant_filter
    }
    raw_tenders = await db.documents.find(tender_query).to_list(length=500)   # cap at 500 tenders for PoC

    if not raw_tenders:
        logger.info("[Match] No indexed tenders found in MongoDB.")
        return []

    logger.info("[Match] Scoring vendor_id=%s against %d tenders", vendor_id, len(raw_tenders))

    # ── 4–6. Score each tender ────────────────────────────────────────────────
    scored: list[dict] = []

    for tender_doc in raw_tenders:
        tender_mongo_id = str(tender_doc["_id"])
        faiss_id        = tender_doc.get("embedding_id")

        # Reconstruct tender doc vector from FAISS
        tender_vec = await emb_svc.reconstruct_vector(faiss_id)
        if tender_vec is None:
            logger.warning("[Match] Could not reconstruct vector for faiss_id=%s", faiss_id)
            continue

        # --- Semantic document score (dot product of L2-normalised vecs = cosine) ---
        doc_score = float(np.dot(vendor_vec, tender_vec))
        doc_score = _clamp(doc_score)   # cosine can marginally exceed 1.0 due to float32

        # --- Keyword semantic score ---
        tender_kw_embeddings = _load_kw_matrix(tender_doc.get("keyword_embeddings", []))
        kw_score = _keyword_similarity(vendor_kw_embeddings, tender_kw_embeddings)

        # --- Combined final score scaled to 0-100 ---
        raw_final = W_DOC * doc_score + W_KEYWORD * kw_score
        final_score = round(raw_final * SCORE_SCALE, 2)

        match_entry: dict = {
            "tender_id":      tender_mongo_id,
            "tender_filename": tender_doc.get("original_filename", ""),
            "semantic_score": round(doc_score, 4),
            "keyword_score":  round(kw_score, 4),
            "final_score":    final_score,
            # Compact structured data for display
            "tender_summary": {
                "scope":          tender_doc.get("structured_data", {}).get("scope"),
                "location":       tender_doc.get("structured_data", {}).get("location"),
                "certifications": tender_doc.get("structured_data", {}).get("certifications", []),
            },
            "tender_keywords": tender_doc.get("keywords", []),
        }

        # ── 7. Optional Groq explanation ──────────────────────────────────────
        if explain:
            match_entry["explanation"] = await _generate_explanation(
                vendor_doc=vendor_doc,
                tender_doc=tender_doc,
                doc_score=doc_score,
                kw_score=kw_score,
                final_score=final_score,
            )

        scored.append(match_entry)

    # Sort by final_score descending, return top_k
    scored.sort(key=lambda x: x["final_score"], reverse=True)
    return scored[:top_k]


# ─── Keyword similarity ───────────────────────────────────────────────────────

def _load_kw_matrix(kw_embeddings_raw: list) -> Optional[np.ndarray]:
    """
    Convert keyword_embeddings (list of float lists from MongoDB) to
    a (N, 384) float32 numpy matrix. Returns None if empty.
    """
    if not kw_embeddings_raw:
        return None
    try:
        mat = np.array(kw_embeddings_raw, dtype=np.float32)
        if mat.ndim != 2 or mat.shape[1] != 384:
            return None
        return mat
    except Exception:
        return None


def _keyword_similarity(
    vendor_kw_mat: Optional[np.ndarray],
    tender_kw_mat: Optional[np.ndarray],
) -> float:
    """
    For each tender keyword, find the max cosine similarity to any vendor keyword.
    Return the mean of these best-match scores.

    Since both matrices are L2-normalised, cosine sim = dot product.
    Implements: avg( max( tender_kw @ vendor_kw.T ) for each tender_kw )
    """
    if vendor_kw_mat is None or tender_kw_mat is None:
        return 0.0

    # sim_matrix[i, j] = cosine_sim(tender_kw[i], vendor_kw[j])
    sim_matrix = tender_kw_mat @ vendor_kw_mat.T   # (T, V)

    # Best vendor keyword match for each tender keyword
    best_per_tender_kw = sim_matrix.max(axis=1)    # (T,)

    return float(_clamp(best_per_tender_kw.mean()))


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp value to [lo, hi] — cosine can slightly exceed 1.0 in float32."""
    return max(lo, min(hi, float(val)))


# ─── Groq explanation generator ───────────────────────────────────────────────

async def _generate_explanation(
    vendor_doc: dict,
    tender_doc: dict,
    doc_score: float,
    kw_score: float,
    final_score: float,
) -> str:
    """
    Call Groq to produce a concise human-readable match explanation.
    Non-fatal: returns empty string on error.
    """
    try:
        from groq import AsyncGroq
        from app.core.config import settings

        vendor_sd = vendor_doc.get("structured_data", {})
        tender_sd = tender_doc.get("structured_data", {})

        prompt = f"""You are a procurement analyst AI.

Vendor Capabilities:
- Scope: {vendor_sd.get('scope', 'N/A')}
- Certifications: {vendor_sd.get('certifications', [])}
- Location: {vendor_sd.get('location', 'N/A')}
- Keywords: {vendor_doc.get('keywords', [])}

Tender Requirements:
- Scope: {tender_sd.get('scope', 'N/A')}
- Eligibility: {tender_sd.get('eligibility', 'N/A')}
- Certifications: {tender_sd.get('certifications', [])}
- Location: {tender_sd.get('location', 'N/A')}

Match Scores:
- Semantic Document Score: {doc_score:.3f}
- Keyword Match Score: {kw_score:.3f}
- Final Score: {final_score}/100

In 2-3 sentences, explain why this match score is high or low.
Focus on: which capabilities align, which are missing, and the overall recommendation.
Be concise and professional."""

        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a concise procurement analyst. Respond in plain text only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()

    except Exception as exc:
        logger.warning("[Match] Groq explanation failed (non-fatal): %s", exc)
        return ""
