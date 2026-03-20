"""
document.py (model)
-------------------
MongoDB document model for parsed vendor / tender documents.

Collection: documents
"""

from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime


# ─── Embedded structured data ─────────────────────────────────────────────────

class StructuredData(BaseModel):
    scope: Optional[str] = None
    eligibility: Optional[str] = None
    technical_specs: Optional[str] = None
    certifications: list[str] = []
    location: Optional[str] = None

    class Config:
        extra = "allow"   # don't blow up if Groq adds unexpected sub-fields


# ─── Main DB model ────────────────────────────────────────────────────────────

class DocumentInDB(BaseModel):
    """
    Represents the document record stored in MongoDB.
    'type' is either 'vendor' or 'tender'.
    'search_text' is a denormalized string used for downstream semantic matching.
    """
    id: Optional[str] = Field(default=None, alias="_id")

    type: str                          # "vendor" | "tender"
    original_filename: str

    uploaded_by: Optional[str] = None
    org_id: Optional[str] = None

    structured_data: StructuredData = Field(default_factory=StructuredData)
    keywords: list[str] = []
    search_text: str = ""              # concatenated for embedding / search

    raw_text: Optional[str] = None    # full extracted text (truncated at 50k chars)
    file_url: Optional[str] = None    # local path or future cloud URL

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


# ─── Helper: MongoDB dict → serialisable dict ─────────────────────────────────

def document_helper(doc: dict) -> dict:
    """Convert a raw MongoDB document into a clean serialisable dict."""
    return {
        "id": str(doc["_id"]),
        "type": doc.get("type", ""),
        "original_filename": doc.get("original_filename", ""),
        "uploaded_by": doc.get("uploaded_by"),
        "org_id": doc.get("org_id"),
        "structured_data": doc.get("structured_data", {}),
        "keywords": doc.get("keywords", []),
        "search_text": doc.get("search_text", ""),
        "file_url": doc.get("file_url"),
        "embedding_id": doc.get("embedding_id"),   # faiss_id for semantic search
        "created_at": (
            doc["created_at"].isoformat()
            if isinstance(doc.get("created_at"), datetime)
            else str(doc.get("created_at", ""))
        ),
    }


# ─── Helper: build search_text from structured data ──────────────────────────

def build_search_text(structured_data: dict, keywords: list[str]) -> str:
    """
    Concatenate all semantic fields into a single string for
    future embedding / full-text search.
    """
    parts: list[str] = []

    def _add(value):
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
        elif isinstance(value, list):
            parts.extend(v for v in value if isinstance(v, str) and v.strip())

    _add(structured_data.get("scope"))
    _add(structured_data.get("technical_specs"))
    _add(structured_data.get("eligibility"))
    _add(structured_data.get("certifications"))
    _add(structured_data.get("location"))
    _add(keywords)

    return " | ".join(parts)
