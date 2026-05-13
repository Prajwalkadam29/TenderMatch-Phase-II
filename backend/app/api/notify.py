from fastapi import APIRouter, Depends, BackgroundTasks, status
from pydantic import BaseModel, EmailStr
from app.core.dependencies import get_current_user
from app.tasks.notification_tasks import send_match_notification_email

router = APIRouter(prefix="/notify", tags=["Notifications"])

class NotificationTestRequest(BaseModel):
    vendor_email: EmailStr
    vendor_name: str
    tender_title: str
    match_score: float
    explanation: str

@router.post("/test-email", status_code=status.HTTP_202_ACCEPTED)
async def test_email_notification(
    payload: NotificationTestRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Test endpoint to trigger the Celery email notification task.
    In production, this is triggered automatically by the matching engine when a high score is found.
    """
    # Dispatch to Celery background worker
    task = send_match_notification_email.delay(
        vendor_email=payload.vendor_email,
        vendor_name=payload.vendor_name,
        tender_title=payload.tender_title,
        match_score=payload.match_score,
        explanation=payload.explanation
    )
    
    return {
        "message": "Email notification task dispatched to worker pool successfully.",
        "task_id": task.id
    }
