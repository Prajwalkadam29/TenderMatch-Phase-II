"""
hybrid_retriever.py
-------------------
Implements hybrid retrieval (Vector + BM25) for TenderMatch scoring.
"""

import math
from typing import Dict, List, Tuple
from rank_bm25 import BM25Okapi

import numpy as np

def cosine_similarity(v1: list, v2: list) -> float:
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.clip(np.dot(a, b) / (a_norm * b_norm), 0.0, 1.0))

class HybridRetriever:
    """
    Combines pgvector cosine similarity with BM25 scoring.
    """
    
    def __init__(self):
        pass

    def get_alpha(self, retrieval_strategy: str) -> float:
        if retrieval_strategy == "vector_only":
            return 1.0
        elif retrieval_strategy == "bm25_fallback":
            return 0.3
        return 0.7  # default hybrid

    def calculate_hybrid_score(
        self,
        vendor_text: str,
        tender_title: str,
        tender_scope: str,
        vendor_vector: list,
        tender_vector: list,
        retrieval_strategy: str = "hybrid"
    ) -> Dict[str, float]:
        """
        Calculates the hybrid score for a single tender document.
        Returns a dict with vector_score, bm25_score, hybrid_score, alpha_used.
        """
        alpha = self.get_alpha(retrieval_strategy)
        
        # 1. Vector Score
        if vendor_vector and tender_vector:
            vector_score = cosine_similarity(vendor_vector, tender_vector)
        else:
            vector_score = 0.0
            
        # 2. BM25 Score
        # For a single document comparison, we treat the tender as a 1-document corpus.
        # But BM25 on a 1-document corpus gives 0 IDF.
        # To make it work as a "similarity" score, we'll chunk the tender,
        # score the chunks, and take the max or average, OR we can just use
        # a pseudo-corpus or raw term frequency if we really only have 1 document.
        # However, the prompt says "BM25 index built over tender scope_of_work + title text fields".
        # Let's chunk the tender into passages to form a corpus of chunks.
        
        tender_text = f"{tender_title} {tender_scope}"
        chunks = self._chunk_text(tender_text)
        
        if chunks and vendor_text:
            tokenized_corpus = [chunk.lower().split() for chunk in chunks]
            bm25 = BM25Okapi(tokenized_corpus)
            tokenized_query = vendor_text.lower().split()
            chunk_scores = bm25.get_scores(tokenized_query)
            
            # Normalize BM25 score to 0-1 range roughly. BM25 isn't bounded,
            # so we'll use a sigmoid-like normalization or max scaling.
            # For simplicity, we just use the max chunk score, capped and scaled.
            max_bm25 = max(chunk_scores) if len(chunk_scores) > 0 else 0.0
            # Simple normalization: score / (score + 10)
            bm25_score = max_bm25 / (max_bm25 + 10.0) 
        else:
            bm25_score = 0.0
            
        # 3. Hybrid Score
        hybrid_score = (alpha * vector_score) + ((1.0 - alpha) * bm25_score)
        
        return {
            "vector_score": float(vector_score),
            "bm25_score": float(bm25_score),
            "hybrid_score": float(hybrid_score),
            "alpha_used": float(alpha)
        }
        
    def retrieve_top_chunks(
        self,
        vendor_text: str,
        tender_title: str,
        tender_scope: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Retrieves top-K chunks from the tender using BM25.
        Useful for the reranker node.
        """
        tender_text = f"{tender_title}\n\n{tender_scope}"
        chunks = self._chunk_text(tender_text)
        
        if not chunks or not vendor_text:
            return []
            
        tokenized_corpus = [chunk.lower().split() for chunk in chunks]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = vendor_text.lower().split()
        
        chunk_scores = bm25.get_scores(tokenized_query)
        
        scored_chunks = list(zip(chunks, chunk_scores))
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        return scored_chunks[:top_k]

    def _chunk_text(self, text: str, chunk_size: int = 50) -> List[str]:
        """Simple word-based chunking."""
        words = text.split()
        return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
