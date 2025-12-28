from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.template_dir = Path(__file__).resolve().parent.parent / "email-templates" / "src"
        self.env = Environment(loader=FileSystemLoader(str(self.template_dir)), autoescape=True)

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        template = self.env.get_template(template_name)
        return template.render(**context)

    def send_email(
        self,
        *,
        email_to: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any] = {},
    ) -> None:
        assert settings.EMAILS_FROM_EMAIL, "EMAILS_FROM_EMAIL is not configured"
        
        html_content = self._render_template(template_name, context)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        msg["To"] = email_to

        part = MIMEText(html_content, "html")
        msg.attach(part)

        # Retry logic for connection
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to SMTP server: {settings.SMTP_HOST}:{settings.SMTP_PORT} (Attempt {attempt+1}/{max_retries})")
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=60) as server:
                    server.set_debuglevel(1) # Enable debug output to stdout for diagnostics
                    
                    logger.debug("Sending EHLO")
                    server.ehlo()
                    
                    if settings.SMTP_TLS:
                        logger.debug("Starting TLS")
                        server.starttls()
                        logger.debug("Sending EHLO after TLS")
                        server.ehlo()
                    
                    if settings.SMTP_USER and settings.SMTP_PASSWORD:
                        logger.debug("Logging in")
                        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    
                    # Use lower-level commands to capture response
                    logger.debug(f"Sending MAIL FROM: {settings.EMAILS_FROM_EMAIL}")
                    server.mail(settings.EMAILS_FROM_EMAIL)
                    
                    logger.debug(f"Sending RCPT TO: {email_to}")
                    code, resp = server.rcpt(email_to)
                    if code not in (250, 251):
                        raise Exception(f"Failed to set recipient: {code} {resp}")
                    
                    logger.debug("Sending DATA")
                    (code, resp) = server.data(msg.as_string())
                    
                    if code != 250:
                        raise Exception(f"Failed to send email: {code} {resp}")
                    
                    logger.info(f"Email sent to {email_to} with type: {template_name}")
                    
                    # Check for Ethereal Preview URL
                    if "ethereal.email" in (settings.SMTP_HOST or ""):
                        resp_str = resp.decode("utf-8") if isinstance(resp, bytes) else str(resp)
                        match = re.search(r"MSGID=([a-zA-Z0-9\-\.]+)", resp_str)
                        if match:
                            msg_id = match.group(1)
                            preview_url = f"https://ethereal.email/message/{msg_id}"
                            logger.info(f"Preview URL: {preview_url}")
                        else:
                             logger.info("Check your Ethereal inbox at: https://ethereal.email/messages")
                    
                    # Success, break retry loop
                    return

            except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, smtplib.SMTPResponseException) as e:
                logger.warning(f"SMTP connection error on attempt {attempt+1}: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to send email to {email_to} after {max_retries} attempts")
                    raise
                import time
                time.sleep(2) # Wait a bit before retrying
            except Exception as e:
                logger.error(f"Unexpected error sending email: {e}")
                raise


    # --- Helper methods for common emails ---
    def send_welcome_email(self, email_to: str, name: str, verify_link: str) -> None:
        self.send_email(
            email_to=email_to,
            subject="Welcome to Contri!",
            template_name="welcome.html",
            context={
                "project_name": settings.PROJECT_NAME,
                "name": name,
                "link": verify_link
            }
        )
    
    def send_deposit_success_email(self, email_to: str, name: str, amount: str, reference: str, date: str) -> None:
        self.send_email(
            email_to=email_to,
            subject="Deposit Confirmed",
            template_name="deposit_success.html",
            context={
                "project_name": "Contri",
                "name": name,
                "currency": "NGN",
                "amount": amount,
                "transaction_reference": reference,
                "date": date,
                "dashboard_link": "https://contri.app/dashboard"
            }
        )

    def send_circle_joined_email(self, email_to: str, name: str, circle_name: str, amount: str, frequency: str, payout_order: int, circle_id: str) -> None:
        self.send_email(
            email_to=email_to,
            subject=f"You joined {circle_name}",
            template_name="circle_joined.html",
            context={
                 "project_name": "Contri",
                 "name": name,
                 "circle_name": circle_name,
                 "currency": "NGN",
                 "amount": amount,
                 "frequency": frequency,
                 "payout_order": payout_order,
                 "circle_link": f"https://contri.app/circles/{circle_id}"
            }
        )

    def send_contribution_success_email(self, email_to: str, name: str, amount: str, circle_name: str, cycle: int, circle_id: str) -> None:
        self.send_email(
            email_to=email_to,
            subject=f"Contribution Received - {circle_name}",
            template_name="contribution_success.html",
            context={
                 "project_name": "Contri",
                 "name": name,
                 "amount": amount,
                 "currency": "NGN",
                 "cycle": cycle,
                 "circle_name": circle_name,
                 "date": datetime.now().strftime("%Y-%m-%d"),
                 "circle_link": f"https://contri.app/circles/{circle_id}"
            }
        )

    def send_payout_received_email(self, email_to: str, name: str, amount: str, circle_name: str, cycle: int) -> None:
        self.send_email(
             email_to=email_to,
             subject=f"Payout Received from {circle_name}!",
             template_name="payout_received.html",
             context={
                  "project_name": "Contri",
                  "name": name,
                  "amount": amount,
                  "currency": "NGN",
                  "cycle": cycle,
                  "circle_name": circle_name,
                  "dashboard_link": "https://contri.app/wallet"
             }
        )

email_service = EmailService()
