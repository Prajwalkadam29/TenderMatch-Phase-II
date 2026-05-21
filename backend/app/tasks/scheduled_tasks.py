import asyncio
import logging
from datetime import datetime, timezone
from celery import shared_task

from app.core.celery_db import get_celery_db
from app.core.postgres import get_pg_session
from app.db.models.user import User, UserRole
from app.services.bidassist_service import BidassistService
from app.services.scraping_service import ScrapingService
from sqlalchemy import select

logger = logging.getLogger(__name__)

def run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)

async def _send_super_admin_notification(subject: str, message: str):
    try:
        async with get_pg_session() as session:
            stmt = select(User).where(User.role == UserRole.SUPER, User.is_active == True)
            res = await session.execute(stmt)
            super_admins = res.scalars().all()
            
            emails = [admin.email for admin in super_admins]
            if not emails:
                logger.warning("[Scheduled Tasks] No SUPER_ADMINs found to send notification.")
                return
                
            # In a real scenario, use an SMTP client here (e.g. aiosmtplib)
            # using settings.SMTP_SERVER, settings.SMTP_USER, etc.
            # For this MVP, we will simulate the send:
            logger.info(f"[Email Simulation] Sending email to {emails} | Subject: {subject} | Body: {message}")
            
    except Exception as e:
        logger.error(f"Failed to send SUPER_ADMIN notification: {e}")

@shared_task(name="nightly_bidassist_sync")
def nightly_bidassist_sync():
    """Scheduled task to sync tenders from Bidassist every night."""
    logger.info("Starting nightly_bidassist_sync...")
    
    db = get_celery_db()
    started_at = datetime.now(timezone.utc)
    
    # Initialize log entry
    log_entry = {
        "sync_type": "bidassist",
        "started_at": started_at,
        "completed_at": None,
        "status": "running",
        "new_tenders": 0,
        "duplicates": 0,
        "errors": 0,
        "tender_ids": []
    }
    
    try:
        service = BidassistService()
        # Fetching for default generic categories, could be customized
        stats = run_async(service.sync_tenders())
        
        log_entry.update({
            "new_tenders": stats.get("new_tenders", 0),
            "duplicates": stats.get("duplicates_skipped", 0),
            "errors": stats.get("errors", 0),
            "tender_ids": stats.get("tender_ids", []),
            "status": "success",
            "completed_at": datetime.now(timezone.utc)
        })
        
        # Send Notification
        msg = f"Nightly sync complete: {stats.get('new_tenders', 0)} new tenders ingested from Bidassist. " \
              f"Duplicates skipped: {stats.get('duplicates_skipped', 0)}. Errors: {stats.get('errors', 0)}."
        run_async(_send_super_admin_notification("Nightly Bidassist Sync Complete", msg))
        
    except Exception as e:
        logger.error(f"nightly_bidassist_sync failed: {e}", exc_info=True)
        log_entry.update({
            "status": "failed",
            "error_detail": str(e),
            "completed_at": datetime.now(timezone.utc)
        })
    finally:
        # Persist to Mongo
        db.sync_logs.insert_one(log_entry)
        
    return f"Completed with status {log_entry['status']}"

@shared_task(name="nightly_portal_scrape")
def nightly_portal_scrape():
    """Scheduled task to scrape enabled portals every night."""
    logger.info("Starting nightly_portal_scrape...")
    
    db = get_celery_db()
    started_at = datetime.now(timezone.utc)
    
    log_entry = {
        "sync_type": "web_scrape",
        "started_at": started_at,
        "completed_at": None,
        "status": "running",
        "new_tenders": 0,
        "duplicates": 0,
        "errors": 0,
        "portals_scraped": 0
    }
    
    try:
        service = ScrapingService()
        stats = run_async(service.scrape_all_portals())
        
        log_entry.update({
            "new_tenders": stats.get("new_tenders", 0),
            "duplicates": stats.get("duplicates_skipped", 0),
            "errors": stats.get("errors", 0),
            "portals_scraped": stats.get("portals_scraped", 0),
            "status": "success",
            "completed_at": datetime.now(timezone.utc)
        })
        
        msg = f"Nightly portal scrape complete: {stats.get('new_tenders', 0)} new tenders across {stats.get('portals_scraped', 0)} portals."
        run_async(_send_super_admin_notification("Nightly Portal Scrape Complete", msg))
        
    except Exception as e:
        logger.error(f"nightly_portal_scrape failed: {e}", exc_info=True)
        log_entry.update({
            "status": "failed",
            "error_detail": str(e),
            "completed_at": datetime.now(timezone.utc)
        })
    finally:
        db.sync_logs.insert_one(log_entry)
        
    return f"Completed with status {log_entry['status']}"
