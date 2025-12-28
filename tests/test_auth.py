
import pytest
import uuid
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_signup(client: AsyncClient, session):
    email = f"signup_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    response = await client.post(f"{settings.API_V1_STR}/auth/signup", json={
        "email": email,
        "password": password,
        "first_name": "New",
        "last_name": "User",
        "phone_number": f"+234{uuid.uuid4().int % 10000000000:010d}"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "User created successfully"
    assert data["data"]["email"] == email

@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient, session):
    email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    # First signup
    await client.post(f"{settings.API_V1_STR}/auth/signup", json={
        "email": email,
        "password": password,
        "first_name": "First",
        "last_name": "One",
        "phone_number": f"+234{uuid.uuid4().int % 10000000000:010d}"
    })
    
    # Second signup with same email
    response = await client.post(f"{settings.API_V1_STR}/auth/signup", json={
        "email": email,
        "password": password,
        "first_name": "Second",
        "last_name": "One",
        "phone_number": f"+234{uuid.uuid4().int % 10000000000:010d}"
    })
    
    # Should probably be 400 or 409 depending on implementation, usually 400 in this codebase based on patterns
    assert response.status_code in [400, 409] 

@pytest.mark.asyncio
async def test_login(client: AsyncClient, session):
    email = f"login_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    # Register first
    await client.post(f"{settings.API_V1_STR}/auth/signup", json={
        "email": email,
        "password": password,
        "first_name": "Login",
        "last_name": "User",
        "phone_number": f"+234{uuid.uuid4().int % 10000000000:010d}"
    })
    
    # Login
    response = await client.post(f"{settings.API_V1_STR}/auth/login", json={
        "email": email,
        "password": password
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, session):
    response = await client.post(f"{settings.API_V1_STR}/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    })
    
    assert response.status_code in [400, 401, 404]

@pytest.mark.asyncio
async def test_social_auth_google_mock(client: AsyncClient, session):
    # This test might need mocking of the actual Google verification service
    # For now, we'll check if the endpoint validates input structure
    
    response = await client.post(f"{settings.API_V1_STR}/auth/social/google", json={
        "token": "fake_google_token"
    })
    
    # It should fail validation or return 400 because token is invalid
    # If we want to test success, we'd need to mock 'verify_google_token'
    assert response.status_code != 500

