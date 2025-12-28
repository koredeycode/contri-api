import pytest
import uuid
from httpx import AsyncClient
from app.core.config import settings
from app.core import security
from app.models.user import User
from sqlmodel import select

@pytest.mark.asyncio
async def test_email_verification_flow(client: AsyncClient, session):
    email = f"verify_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    # 1. Signup
    response = await client.post(f"{settings.API_V1_STR}/auth/signup", json={
        "email": email,
        "password": password,
        "first_name": "Verify",
        "last_name": "Me",
        "phone_number": f"+234{uuid.uuid4().int % 10000000000:010d}"
    })
    assert response.status_code == 200
    user_data = response.json()["data"]
    user_id = user_data["id"]
    
    # 2. Verify user is initially not verified (or handled by default)
    # Actually, let's check the DB directly to be sure
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    # Note: user might vary based on default model, but we expect is_verified=False usually for email signup
    # But wait, looking at User model: is_verified: bool = Field(default=False, ...)
    assert user.is_verified is False
    
    # 3. Generate Token (simulating the one sent in email)
    token = security.create_verification_token(user_id)
    
    # 4. Call Verify Endpoint
    verify_response = await client.post(
        f"{settings.API_V1_STR}/auth/verify-email", 
        params={"token": token}
    )
    
    assert verify_response.status_code == 200
    assert verify_response.json()["message"] == "Email verified successfully"
    assert verify_response.json()["data"]["verified"] is True
    
    # 5. Check DB again
    session.expire_all() # Ensure we get fresh data
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    assert user.is_verified is True

@pytest.mark.asyncio
async def test_verify_email_invalid_token(client: AsyncClient):
    response = await client.post(
        f"{settings.API_V1_STR}/auth/verify-email", 
        params={"token": "invalid_token_string"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired verification token"
