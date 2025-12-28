
import pytest
from httpx import AsyncClient
from app.core.config import settings
from tests.utils import create_user_and_get_headers

@pytest.mark.asyncio
async def test_update_user_profile(client: AsyncClient, session):
    """
    Test updating user profile.
    """
    # 0. Setup User
    _, headers = await create_user_and_get_headers(client)

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

@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, session):
    user_data, headers = await create_user_and_get_headers(client)
    
    response = await client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["email"] == user_data["email"]
