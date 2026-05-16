"""
email_service.py
----------------
Handles branded HTML email delivery for TenderMatch notifications.
Uses standard SMTP with premium responsive templates.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_match_alert(vendor_email: str, vendor_name: str, tender_title: str, match_score: float, explanation: str):
        """
        Sends a high-conversion, branded match alert email.
        """
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("Email Service: SMTP credentials not configured.")
            return False

        # Color coding based on score
        score_color = "#16a34a" if match_score >= 85 else "#0ea5e9" if match_score >= 70 else "#f59e0b"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎯 Tender Match Found ({int(match_score)}%): {tender_title[:40]}..."
        msg["From"] = f"TenderMatch AI <{settings.FROM_EMAIL}>"
        msg["To"] = vendor_email

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
                body {{ font-family: 'Inter', -apple-system, sans-serif; background-color: #f1f5f9; margin: 0; padding: 40px 0; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 24px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); }}
                .header {{ background: #162f3e; padding: 40px; text-align: center; }}
                .content {{ padding: 40px; color: #1e293b; }}
                .badge {{ display: inline-block; padding: 6px 12px; background: {score_color}20; color: {score_color}; border-radius: 8px; font-size: 12px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 20px; }}
                .score-circle {{ width: 80px; height: 80px; border-radius: 50%; border: 4px solid {score_color}; display: flex; align-items: center; justify-content: center; margin: 0 auto 30px auto; }}
                .score-value {{ font-size: 24px; font-weight: 900; color: {score_color}; }}
                h1 {{ font-size: 24px; font-weight: 900; margin: 0 0 10px 0; color: #1e293b; line-height: 1.2; }}
                .tender-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 16px; padding: 24px; margin: 30px 0; }}
                .explanation {{ font-style: italic; color: #64748b; line-height: 1.6; border-left: 3px solid #cbd5e1; padding-left: 20px; margin-top: 15px; }}
                .btn {{ display: block; background: #c41230; color: #ffffff !important; text-align: center; padding: 18px; border-radius: 16px; font-weight: 700; text-decoration: none; margin-top: 30px; box-shadow: 0 10px 15px -3px rgba(196, 18, 48, 0.3); }}
                .footer {{ padding: 30px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="https://via.placeholder.com/150x40/162f3e/ffffff?text=TENDERMATCH" alt="TenderMatch Logo" style="height: 30px;">
                </div>
                <div class="content">
                    <div style="text-align: center;">
                        <div class="badge">AI Match Analysis Complete</div>
                        <div class="score-circle">
                            <span class="score-value">{int(match_score)}%</span>
                        </div>
                    </div>
                    <h1>Hello {vendor_name},</h1>
                    <p>Our Intelligence Engine just identified a high-priority opportunity perfectly aligned with your business capabilities.</p>
                    
                    <div class="tender-box">
                        <div style="font-size: 10px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.1em; color: #94a3b8; margin-bottom: 8px;">Tender Title</div>
                        <div style="font-size: 18px; font-weight: 700;">{tender_title}</div>
                        
                        <div style="font-size: 10px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.1em; color: #94a3b8; margin: 20px 0 8px 0;">AI Strategic Alignment</div>
                        <div class="explanation">"{explanation}"</div>
                    </div>
                    
                    <a href="{settings.FRONTEND_URL}/tenders" class="btn">VIEW TENDER & APPLY</a>
                </div>
                <div class="footer">
                    &copy; 2026 TenderMatch. All rights reserved.<br>
                    You are receiving this automated alert based on your business profile.
                </div>
            </div>
        </body>
        </html>
        """

        try:
            msg.attach(MIMEText(html_body, "html"))
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.FROM_EMAIL, vendor_email, msg.as_string())
            
            logger.info(f"Premium match alert sent to {vendor_email}")
            return True
        except Exception as e:
            logger.error(f"SMTP Error: {str(e)}")
            return False
