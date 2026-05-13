import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from celery import shared_task
from app.core.config import settings

logger = logging.getLogger(__name__)

@shared_task(name="send_match_notification_email", bind=True, max_retries=3)
def send_match_notification_email(self, vendor_email: str, vendor_name: str, tender_title: str, match_score: float, explanation: str):
    """
    Sends an asynchronous email notification to a vendor about a high-scoring tender match.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured. Skipping email notification.")
        return False

    try:
        # Construct the email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚨 New High-Match Tender Alert: {tender_title[:30]}..."
        msg["From"] = settings.FROM_EMAIL
        msg["To"] = vendor_email

        # Create HTML Body
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2563eb;">TenderMatch Alert 🚀</h2>
                <p>Hello <strong>{vendor_name}</strong>,</p>
                <p>We found a highly relevant tender that matches your business profile with a score of <strong>{match_score:.1f}%</strong>!</p>
                
                <div style="background-color: #f8fafc; padding: 15px; border-left: 4px solid #2563eb; margin: 20px 0;">
                    <h3 style="margin-top: 0;">{tender_title}</h3>
                    <p><strong>AI Explanation:</strong></p>
                    <p style="font-style: italic;">{explanation}</p>
                </div>
                
                <p>Log into your <a href="http://localhost:5173" style="color: #2563eb; text-decoration: none; font-weight: bold;">TenderMatch Dashboard</a> to view the full tender details and apply.</p>
                
                <p style="font-size: 12px; color: #64748b; margin-top: 30px;">
                    You are receiving this because you subscribed to automated matching alerts.
                </p>
            </body>
        </html>
        """

        msg.attach(MIMEText(html_body, "html"))

        # Send the email
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, vendor_email, msg.as_string())

        logger.info(f"Successfully sent match notification email to {vendor_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {vendor_email}: {str(e)}")
        # Retry with exponential backoff (e.g. 60s, 120s, 240s)
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=e, countdown=countdown)
