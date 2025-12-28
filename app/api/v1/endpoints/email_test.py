from fastapi import APIRouter, BackgroundTasks, Request
from app.core.rate_limit import limiter
from app.worker import send_email_task
from typing import Any

router = APIRouter()

@router.post("/send-test-email", status_code=201)
@limiter.limit("2/minute")
def send_test_email(
    request: Request, 
    email_to: str,
    subject: str = "Welcome to Contri!",
    template_name: str = "welcome.html"
) -> Any:
    """
    Send a test email using Celery worker.
    """
    send_email_task.delay(
        email_to=email_to,
        subject=subject,
        html_template=template_name,
        environment={
            "project_name": "Contri",
            "name": "User",
            "link": "https://contri.com/verify-email?token=123",
            "currency": "NGN",
            "amount": "5000.00",
            "transaction_reference": "REF_TEST_123",
            "date": "2023-01-01",
            "dashboard_link": "https://contri.app/dashboard",
            "circle_name": "Test Circle",
            "frequency": "Monthly",
            "payout_order": 1,
            "circle_link": "https://contri.app/circles/123",
            "cycle": 1
        }
    )
    return {"message": f"Email sent with template {template_name}"}
