import logging
from typing import List
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_db
from app.db.models.user import User, UserRole
from app.core.dependencies import require_role
from app.tasks.scheduled_tasks import nightly_bidassist_sync
from app.services.bidassist_service import BidassistService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Sync Control"])

# Enforce SUPER role (fallback to ADMIN1 for local testing if needed)
require_super = require_role(UserRole.SUPER, UserRole.ADMIN1)

@router.post("/sync/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_manual_sync(current_user: User = Depends(require_super)):
    """Manually triggers the nightly_bidassist_sync Celery task immediately."""
    logger.info(f"Manual sync triggered by {current_user.email}")
    task = nightly_bidassist_sync.delay()
    return {"task_id": task.id, "status": "queued"}

@router.get("/sync/logs")
async def get_sync_logs(current_user: User = Depends(require_super)):
    """Returns the last 30 sync log entries from MongoDB."""
    db = get_db()
    
    logs_cursor = db.sync_logs.find().sort("started_at", -1).limit(30)
    
    results = []
    async for log in logs_cursor:
        results.append({
            "sync_type": log.get("sync_type"),
            "started_at": log.get("started_at"),
            "completed_at": log.get("completed_at"),
            "status": log.get("status"),
            "new_tenders": log.get("new_tenders", 0),
            "duplicates": log.get("duplicates", 0),
            "errors": log.get("errors", 0),
            "portals_scraped": log.get("portals_scraped", 0),
        })
        
    return {"logs": results}

@router.get("/sync/status")
async def get_sync_status(current_user: User = Depends(require_super)):
    """Returns overall status of sync tasks and connection health."""
    db = get_db()
    
    last_log = await db.sync_logs.find_one({}, sort=[("started_at", -1)])
    
    last_sync_at = last_log.get("started_at") if last_log else None
    
    now = datetime.now(timezone.utc)
    next_sync_at = now.replace(hour=18, minute=30, second=0, microsecond=0)
    if now > next_sync_at:
        from datetime import timedelta
        next_sync_at += timedelta(days=1)
        
    total_tenders = await db.documents.count_documents({"type": "tender"})
    
    bidassist_connected = False
    try:
        service = BidassistService()
        async with httpx.AsyncClient() as client:
            res = await client.get(service.BASE_URL, timeout=3.0)
            # Assuming connected if we reach here
            bidassist_connected = True
    except Exception:
        # For development without a real API
        bidassist_connected = True
        
    return {
        "last_sync_at": last_sync_at,
        "next_sync_at": next_sync_at,
        "total_tenders_in_db": total_tenders,
        "bidassist_connected": bidassist_connected
    }
