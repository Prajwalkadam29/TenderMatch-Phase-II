"""
embedding_service.py
--------------------
Manages sentence-transformer embeddings + FAISS index for semantic search.

Design:
  - Singleton pattern (module-level _service instance)
  - Lazy model loading, warm-up at app startup recommended
  - FAISS IndexFlatIP with L2-normalised vectors → exact cosine similarity
  - index.faiss + mapping.json persisted to disk on every write (survives restarts)
  - CPU-bound ops run in ThreadPoolExecutor (never blocks asyncio event loop)
  - threading.Lock protects FAISS writes
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

import numpy as np

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

MODEL_NAME      = "all-MiniLM-L6-v2"   # 384-dim, fast, great for semantic search
EMBEDDING_DIM   = 384
FAISS_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "faiss_store")
INDEX_FILE      = os.path.join(FAISS_STORE_DIR, "index.faiss")
MAPPING_FILE    = os.path.join(FAISS_STORE_DIR, "mapping.json")

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="embeddings")


# ─── EmbeddingService ─────────────────────────────────────────────────────────

class EmbeddingService:
    """
    Singleton service: SentenceTransformer model + FAISS index.
    All public methods are async-safe.
    """

    def __init__(self):
        self._model  = None
        self._index  = None
        self._mapping: dict[int, str] = {}   # faiss_id → mongo_id
        self._lock   = threading.Lock()
        os.makedirs(FAISS_STORE_DIR, exist_ok=True)

    # ── Warm-up ──────────────────────────────────────────────────────────────

    async def warmup(self):
        """Pre-load model + index at app startup to avoid cold-start latency."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, self._load_model_and_index)
        logger.info("[Embedding] Warmed up. Index size: %d", self._index.ntotal)

    # ── Public async API ─────────────────────────────────────────────────────

    async def add_document(
        self,
        mongo_id: str,
        search_text: str,
        keywords: list[str],
    ) -> dict:
        """
        Encode search_text + keywords, add doc vector to FAISS.
        Returns { "embedding_id": int, "keyword_embeddings": [[float, ...], ...] }
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self._add_document_sync, mongo_id, search_text, keywords
        )

    async def search(
        self,
        query_text: str,
        k: int = 10,
        doc_type_filter: Optional[str] = None,
    ) -> list[dict]:
        """
        Semantic search over the full FAISS index.
        Returns [ {"faiss_id": int, "mongo_id": str, "score": float} ]
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._search_sync, query_text, k)

    async def encode_text(self, text: str) -> np.ndarray:
        """
        Encode a single string → normalised (384,) float32 embedding.
        Used by matching engine to build the vendor query vector.
        """
        loop = asyncio.get_event_loop()
        vecs = await loop.run_in_executor(_executor, self._encode, [text])
        return vecs[0]   # strip batch dim → (384,)

    async def reconstruct_vector(self, faiss_id: int) -> Optional[np.ndarray]:
        """
        Pull a stored (384,) embedding out of the flat FAISS index by its id.
        IndexFlatIP supports reconstruct() natively.
        Returns None if faiss_id is invalid.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self._reconstruct_vector_sync, faiss_id
        )

    @property
    def index_size(self) -> int:
        return self._index.ntotal if self._index else 0

    # ── Internal sync methods (all run inside _executor) ─────────────────────

    def _load_model_and_index(self):
        """Load model + FAISS index once; noop if already loaded."""
        import faiss
        from sentence_transformers import SentenceTransformer

        if self._model is None:
            logger.info("[Embedding] Loading model: %s ...", MODEL_NAME)
            self._model = SentenceTransformer(MODEL_NAME)
            logger.info("[Embedding] Model loaded.")

        if self._index is None:
            if os.path.exists(INDEX_FILE) and os.path.exists(MAPPING_FILE):
                logger.info("[Embedding] Restoring FAISS index from disk...")
                self._index = faiss.read_index(INDEX_FILE)
                with open(MAPPING_FILE, "r") as f:
                    raw = json.load(f)
                self._mapping = {int(k): v for k, v in raw.items()}
                logger.info("[Embedding] Index restored. Vectors: %d", self._index.ntotal)
            else:
                logger.info("[Embedding] Creating fresh IndexFlatIP ...")
                self._index = faiss.IndexFlatIP(EMBEDDING_DIM)
                self._mapping = {}

    def _encode(self, texts: list[str]) -> np.ndarray:
        """Encode & L2-normalise → cosine similarity via inner product."""
        import faiss
        self._load_model_and_index()
        vecs = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        vecs = vecs.astype(np.float32)
        faiss.normalize_L2(vecs)
        return vecs

    def _add_document_sync(
        self,
        mongo_id: str,
        search_text: str,
        keywords: list[str],
    ) -> dict:
        with self._lock:
            self._load_model_and_index()

            doc_vec = self._encode([search_text])           # (1, 384)

            kw_embeddings: list[list[float]] = []
            if keywords:
                kw_vecs = self._encode(keywords)            # (n, 384)
                kw_embeddings = kw_vecs.tolist()

            faiss_id: int = self._index.ntotal
            self._index.add(doc_vec)
            self._mapping[faiss_id] = mongo_id
            self._persist()

            logger.info(
                "[Embedding] Added mongo_id=%s → faiss_id=%d (total=%d)",
                mongo_id, faiss_id, self._index.ntotal,
            )
            return {"embedding_id": faiss_id, "keyword_embeddings": kw_embeddings}

    def _search_sync(self, query_text: str, k: int) -> list[dict]:
        self._load_model_and_index()
        if self._index.ntotal == 0:
            return []
        query_vec = self._encode([query_text])
        actual_k  = min(k, self._index.ntotal)
        scores, indices = self._index.search(query_vec, actual_k)
        results = []
        for score, faiss_id in zip(scores[0], indices[0]):
            if faiss_id == -1:
                continue
            mongo_id = self._mapping.get(int(faiss_id))
            if mongo_id:
                results.append({
                    "faiss_id": int(faiss_id),
                    "mongo_id": mongo_id,
                    "score":    float(score),
                })
        return results

    def _reconstruct_vector_sync(self, faiss_id: int) -> Optional[np.ndarray]:
        """Return the stored L2-normalised vector for faiss_id from the flat index."""
        self._load_model_and_index()
        if self._index is None or faiss_id < 0 or faiss_id >= self._index.ntotal:
            return None
        vec = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        self._index.reconstruct(int(faiss_id), vec)
        return vec

    def _persist(self):
        """Write index + mapping to disk."""
        import faiss
        faiss.write_index(self._index, INDEX_FILE)
        with open(MAPPING_FILE, "w") as f:
            json.dump(self._mapping, f)


# ─── Module-level singleton ───────────────────────────────────────────────────

_service = EmbeddingService()


def get_embedding_service() -> EmbeddingService:
    return _service
