"""
embedding_service.py
--------------------
Stateless sentence-transformer embeddings for pgvector semantic search.

Design:
  - Singleton pattern (module-level _service instance)
  - Lazy model loading, warm-up at app startup recommended
  - Generates L2-normalised vectors for exact cosine similarity in pgvector
  - CPU-bound ops run in ThreadPoolExecutor (never blocks asyncio event loop)
"""

from __future__ import annotations

import logging
import threading
from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False
    np = None  # type: ignore

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

MODEL_NAME      = "all-MiniLM-L6-v2"   # 384-dim, fast, great for semantic search
EMBEDDING_DIM   = 384

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="embeddings")


# ─── EmbeddingService ─────────────────────────────────────────────────────────

class EmbeddingService:
    """
    Singleton service: Stateless SentenceTransformer model.
    All public methods are async-safe.
    """

    def __init__(self):
        self._model  = None
        self._lock   = threading.Lock()
        self._ai_available: bool = False

    def _require_ai(self):
        """Raise a clear error if AI libraries are not installed."""
        try:
            import sentence_transformers
            import torch
            self._ai_available = True
        except ImportError:
            self._ai_available = False
            raise RuntimeError(
                "AI engine not available: torch/sentence-transformers are not "
                "installed. Semantic search is disabled."
            )

    # ── Warm-up ──────────────────────────────────────────────────────────────

    async def warmup(self):
        """Pre-load model at app startup. Non-fatal if AI libs are missing."""
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
        except ImportError:
            logger.warning(
                "[Embedding] torch/sentence-transformers not installed. "
                "Vectors will not be generated. Install AI deps to enable."
            )
            self._ai_available = False
            return
        self._ai_available = True
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, self._load_model)

    # ── Public async API ─────────────────────────────────────────────────────

    async def encode_text(self, text: str) -> list[float]:
        """
        Encode a single string → L2-normalised 384-dim float list.
        Used to generate vectors for PostgreSQL insertion.
        """
        self._require_ai()
        loop = asyncio.get_event_loop()
        vecs = await loop.run_in_executor(_executor, self._encode, [text])
        return vecs[0].tolist()   # Return as standard Python list

    async def encode_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Encode a list of strings → L2-normalised vectors.
        """
        if not texts:
            return []
        self._require_ai()
        loop = asyncio.get_event_loop()
        vecs = await loop.run_in_executor(_executor, self._encode, texts)
        return vecs.tolist()

    # ── Public sync API (For Celery / Background tasks) ───────────────────────

    def encode_text_sync(self, text: str) -> list[float]:
        """Synchronous version for background tasks."""
        self._require_ai()
        vecs = self._encode([text])
        return vecs[0].tolist()

    def encode_texts_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous version for background tasks."""
        if not texts:
            return []
        self._require_ai()
        vecs = self._encode(texts)
        return vecs.tolist()

    # ── Internal sync methods (all run inside _executor) ─────────────────────

    def _load_model(self):
        """Load model once; noop if already loaded."""
        from sentence_transformers import SentenceTransformer

        if self._model is None:
            with self._lock:
                if self._model is None:  # double check
                    logger.info("[Embedding] Loading model: %s ...", MODEL_NAME)
                    self._model = SentenceTransformer(MODEL_NAME)
                    logger.info("[Embedding] Model loaded.")

    def _encode(self, texts: list[str]) -> np.ndarray:
        """Encode & L2-normalise → cosine similarity via inner product."""
        self._load_model()
        vecs = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        vecs = vecs.astype(np.float32)
        # L2 Normalize natively with NumPy (FAISS removed)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        # Avoid division by zero
        norms[norms == 0] = 1e-10
        vecs = vecs / norms
        return vecs


# ─── Module-level singleton ───────────────────────────────────────────────────

_service = EmbeddingService()

def get_embedding_service() -> EmbeddingService:
    return _service

