from celery import shared_task
from app.services.email_service import EmailService
import logging
logger = logging.getLogger(__name__)

@shared_task(name="run_match_and_notify_task")
def run_match_and_notify_task(tender_mongo_id: str, org_id: str | None = None):
    """
    Background task to run the matching engine for a newly processed tender
    and send emails to high-scoring vendors.
    """
    from app.services.matching_service import match_tender_to_all_vendors
    import asyncio
    
    # Run the async matching logic
    loop = asyncio.get_event_loop()
    notified_count = loop.run_until_complete(
        match_tender_to_all_vendors(tender_mongo_id, org_id)
    )
    
    logger.info(f"[Celery] Match & Notify complete for tender {tender_mongo_id}. Notifications sent: {notified_count}")
    return notified_count

@shared_task(name="send_match_notification_email", bind=True, max_retries=3)
def send_match_notification_email(self, vendor_email: str, vendor_name: str, tender_title: str, match_score: float, explanation: str):
    """
    Asynchronous task wrapper for sending premium email alerts.
    """
    try:
        success = EmailService.send_match_alert(
            vendor_email=vendor_email,
            vendor_name=vendor_name,
            tender_title=tender_title,
            match_score=match_score,
            explanation=explanation
        )
        if not success:
            raise Exception("Email delivery failed")
        return True
    except Exception as e:
        logger.error(f"Task Retry: Failed to send email to {vendor_email}: {str(e)}")
        # Exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=e, countdown=countdown)
