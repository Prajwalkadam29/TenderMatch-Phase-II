from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any

from app.core.dependencies import get_current_user
from app.services.structured_matching_service import evaluate_match

router = APIRouter(prefix="/match/structured", tags=["Structured Matching Engine"])

@router.post("/")
async def run_structured_match(
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Evaluates a vendor against a tender JSON.
    Expected payload:
    {
      "vendor_id": "V-00001",
      "tender": {
         "tender_id": "TW-2024-NMPA-0758",
         "domain": "Electrical Works",
         "min_avg_turnover": 173962,
         "estimated_value": 579873,
         "mandatory_certifications": ["Valid Electrical Contract License"],
         "location_state": "Karnataka",
         "similar_work_definition": "Supply and Installation of HT/LT Electrical works"
      }
    }
    """
    vendor_id = payload.get("vendor_id")
    tender = payload.get("tender")
    
    if not vendor_id or not tender:
        raise HTTPException(status_code=400, detail="Missing vendor_id or tender object")

    try:
        # Pass current_user for tenant-isolated vendor lookup
        match_result = await evaluate_match(vendor_id, tender, current_user=current_user)
        return match_result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from app.core.database import get_db

from app.services.matching_service import run_matching_engine

@router.post("/run/{vendor_id}")
async def run_batch_structured_match(
    vendor_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Evaluates a vendor against all available tenders using the 
    Unified Matching Engine (pgvector + Business Rules).
    """
    try:
        results = await run_matching_engine(
            vendor_id=vendor_id,
            top_k=50,
            explain=True,
            current_user=current_user
        )
        return {"results": results}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

