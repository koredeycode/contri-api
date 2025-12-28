import pytest
import uuid
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_update_user_profile(client: AsyncClient, session):
    """
    Test updating user profile.
    """
    # 0. Setup User
    email_base = uuid.uuid4().hex[:8]
    email = f"user_{email_base}@example.com"
    password = "password123"
    
    # Register
    resp = await client.post(f"{settings.API_V1_STR}/auth/signup", json={
        "email": email,
        "password": password,
        "first_name": "Original",
        "last_name": "Name",
        "phone_number": "+2348000000000"
    })
    assert resp.status_code == 200, resp.text
    
    # Login
    resp = await client.post(f"{settings.API_V1_STR}/auth/login", json={
        "email": email,
        "password": password
    })
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Update Profile
    update_data = {
        "first_name": "UpdatedName",
        "last_name": "UpdatedLast",
        "phone_number": "+2348999999999"
    }
    
    response = await client.put(
        f"{settings.API_V1_STR}/users/me",
        headers=headers,
        json=update_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "User profile updated"
    assert data["data"]["first_name"] == "UpdatedName"
    assert data["data"]["last_name"] == "UpdatedLast"
    assert data["data"]["phone_number"] == "+2348999999999"

    # 2. Verify persistence with GET
    response_get = await client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=headers
    )
    assert response_get.status_code == 200
    data_get = response_get.json()
    assert data_get["data"]["first_name"] == "UpdatedName"
    assert data_get["data"]["phone_number"] == "+2348999999999"
