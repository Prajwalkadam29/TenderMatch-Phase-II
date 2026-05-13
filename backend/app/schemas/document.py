"""
document.py (schema)
--------------------
Pydantic response schemas for the /upload endpoints.
"""

from typing import Optional
from pydantic import BaseModel


class StructuredDataResponse(BaseModel):
    scope: Optional[str] = None
    eligibility: Optional[str] = None
    technical_specs: Optional[str] = None
    certifications: list[str] = []
    location: Optional[str] = None

    class Config:
        extra = "allow"


class DocumentUploadResponse(BaseModel):
    """Response returned after an upload. Tracks asynchronous parsing status."""
    id: str
    type: str
    original_filename: str
    uploaded_by: Optional[str] = None
    org_id: Optional[str] = None
    status: str = "processing"   # processing, completed, failed
    task_id: Optional[str] = None
    structured_data: Optional[StructuredDataResponse] = None
    keywords: list[str] = []
    search_text: str = ""
    file_url: Optional[str]
    embedding_id: Optional[int] = None    # FAISS index id; None if embedding failed/pending
    created_at: str

    class Config:
        populate_by_name = True

