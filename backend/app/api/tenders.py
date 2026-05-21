import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from bson import ObjectId

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.groq_service import chat_with_tender

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenders", tags=["Tenders"])

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str

@router.post("/{tender_id}/chat", response_model=ChatResponse)
async def chat_with_tender_endpoint(
    tender_id: str,
    req: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Conversational RAG endpoint.
    Allows users to ask questions directly against the raw text of a specific tender.
    """
    if not ObjectId.is_valid(tender_id):
        raise HTTPException(status_code=400, detail="Invalid Tender ID")
        
    db = get_db()
    
    # 1. Fetch Tender Document from Mongo
    # Validate tenancy
    org_id = str(current_user.org_id) if hasattr(current_user, "org_id") and current_user.org_id else None
    
    tenant_filter = {"$or": [{"is_global": True}]}
    if org_id:
        tenant_filter["$or"].append({"org_id": org_id})
    else:
        # Fallback to user-level if not using orgs strictly yet
        tenant_filter["$or"].append({"uploaded_by": str(current_user.id)})

    tender_doc = await db.documents.find_one({
        "_id": ObjectId(tender_id),
        "type": "tender",
        **tenant_filter
    })
    
    if not tender_doc:
        raise HTTPException(status_code=404, detail="Tender not found or you do not have permission to view it.")
        
    raw_text = tender_doc.get("raw_text")
    if not raw_text:
        raise HTTPException(status_code=400, detail="Tender document has no text available for analysis.")
        
    # 2. Query the LLM
    try:
        answer = await chat_with_tender(raw_text, req.question)
        return ChatResponse(answer=answer)
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process conversational query.")
