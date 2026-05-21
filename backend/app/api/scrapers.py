from fastapi import APIRouter, Depends, status
from app.core.dependencies import require_super_admin
from app.tasks.scraper_tasks import run_automated_scraper
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scrapers", tags=["Scrapers"])

@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scraper(user=Depends(require_super_admin)):
    """
    Manually trigger the web scraper Celery task.
    Requires SUPER admin privileges.
    """
    try:
        task = run_automated_scraper.delay()
        return {"message": "Scraper task triggered successfully.", "task_id": task.id}
    except Exception as e:
        logger.error(f"Failed to trigger scraper task: {e}")
        return {"message": "Failed to trigger scraper task.", "error": str(e)}
