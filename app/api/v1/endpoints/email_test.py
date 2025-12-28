from fastapi import APIRouter, BackgroundTasks, Request
from app.core.rate_limit import limiter
from app.worker import send_email_task
from typing import Any

router = APIRouter()

@router.post("/send-test-email", status_code=201)
@limiter.limit("2/minute")
def send_test_email(request: Request, email_to: str) -> Any:
    """
    Send a test email using Celery worker.
    """
    send_email_task.delay(
        email_to=email_to,
        subject="Welcome to Contri!",
        html_template="welcome.html",
        environment={
            "project_name": "Contri",
            "name": "User",
            "link": "https://contri.com/verify-email?token=123"
        }
    )
    return {"message": "Email sent"}
