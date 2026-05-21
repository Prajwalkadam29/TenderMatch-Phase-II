"""
document.py (schema)
--------------------
Pydantic response schemas for the /upload endpoints.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict


class StructuredDataResponse(BaseModel):
    scope: Optional[str] = None
    eligibility: Optional[str] = None
    technical_specs: Optional[str] = None
    certifications: list[str] = []
    location: Optional[str] = None

    model_config = ConfigDict(extra="allow")


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
    error_detail: Optional[str] = None    # Populated when status is "failed" or "completed_degraded"
    created_at: str

    model_config = ConfigDict(populate_by_name=True)

