from app.core.celery_app import celery_app
from app.services.email import email_service
import logging

logger = logging.getLogger(__name__)

@celery_app.task(acks_late=True)
def test_celery(word: str) -> str:
    return f"test task return {word}"

@celery_app.task(acks_late=True)
def send_email_task(email_to: str, subject: str, html_template: str, environment: dict):
    logger.info(f"Sending email to {email_to} with template {html_template}")
    try:
        email_service.send_email(
            email_to=email_to,
            subject=subject,
            template_name=html_template,
            context=environment,
        )
        return "Email sent successfully"
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return f"Failed to send email: {e}"
