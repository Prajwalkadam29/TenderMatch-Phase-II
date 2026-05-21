import pytest
from app.services.hybrid_retriever import HybridRetriever

def test_hybrid_retriever_default_alpha():
    retriever = HybridRetriever()
    scores = retriever.calculate_hybrid_score(
        vendor_text="software development",
        tender_title="IT Services",
        tender_scope="software development required",
        vendor_vector=[0.1, 0.2],
        tender_vector=[0.1, 0.2],
        retrieval_strategy="hybrid"
    )
    assert scores["alpha_used"] == 0.7
    assert 0.0 <= scores["hybrid_score"] <= 1.0

def test_hybrid_retriever_bm25_fallback():
    retriever = HybridRetriever()
    scores = retriever.calculate_hybrid_score(
        vendor_text="software development",
        tender_title="IT Services",
        tender_scope="software development required",
        vendor_vector=[0.1, 0.2],
        tender_vector=[0.1, 0.2],
        retrieval_strategy="bm25_fallback"
    )
    assert scores["alpha_used"] == 0.3

def test_hybrid_retriever_vector_only():
    retriever = HybridRetriever()
    scores = retriever.calculate_hybrid_score(
        vendor_text="software development",
        tender_title="IT Services",
        tender_scope="software development required",
        vendor_vector=[1.0, 0.0],
        tender_vector=[1.0, 0.0],
        retrieval_strategy="vector_only"
    )
    assert scores["alpha_used"] == 1.0
    assert abs(scores["hybrid_score"] - 1.0) < 0.01  # Should exactly match cosine sim

def test_hybrid_retriever_empty_vendor_text():
    retriever = HybridRetriever()
    scores = retriever.calculate_hybrid_score(
        vendor_text="",
        tender_title="IT Services",
        tender_scope="software",
        vendor_vector=[0.1, 0.2],
        tender_vector=[0.1, 0.2],
        retrieval_strategy="hybrid"
    )
    assert scores["bm25_score"] == 0.0

def test_hybrid_retriever_chunking():
    retriever = HybridRetriever()
    text = "word " * 120
    chunks = retriever._chunk_text(text, chunk_size=50)
    assert len(chunks) == 3
    assert len(chunks[0].split()) == 50
    assert len(chunks[1].split()) == 50
    assert len(chunks[2].split()) == 20

def test_hybrid_retriever_top_chunks():
    retriever = HybridRetriever()
    vendor_text = "specific keyword"
    tender_title = "Title"
    tender_scope = "A lot of words here. " * 50 + " specific keyword. " + "More words. " * 50
    
    chunks = retriever.retrieve_top_chunks(vendor_text, tender_title, tender_scope, top_k=2)
    assert len(chunks) <= 2
    assert "specific keyword." in chunks[0][0]
