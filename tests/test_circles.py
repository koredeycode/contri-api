
import pytest
import uuid
from httpx import AsyncClient
from app.core.config import settings
from tests.utils import create_user_and_get_headers, create_user

@pytest.mark.asyncio
async def test_create_circle(client: AsyncClient, session):
    _, headers = await create_user_and_get_headers(client)
    
    circle_data = {
        "name": "New Circle",
        "amount": 5000,
        "frequency": "monthly",
        "payout_preference": "fixed"
    }
    
    response = await client.post(
        f"{settings.API_V1_STR}/circles/",
        json=circle_data,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "New Circle"
    # assert data["data"]["target_members"] == 10 # Default is None in model
    assert data["data"]["target_members"] is None
    assert "invite_code" in data["data"]

@pytest.mark.asyncio
async def test_join_circle(client: AsyncClient, session):
    # Host creates circle
    _, host_headers = await create_user_and_get_headers(client)
    
    circle_resp = await client.post(
        f"{settings.API_V1_STR}/circles/",
        json={
            "name": "Joinable Circle",
            "amount": 2000,
            "frequency": "weekly",
            "payout_preference": "random"
        },
        headers=host_headers
    )
    invite_code = circle_resp.json()["data"]["invite_code"]
    
    # Member joins
    _, member_headers = await create_user_and_get_headers(client)
    
    join_resp = await client.post(
        f"{settings.API_V1_STR}/circles/join?invite_code={invite_code}",
        headers=member_headers
    )
    
    assert join_resp.status_code == 200
    data = join_resp.json()
    assert data["message"] == "Joined circle successfully"

@pytest.mark.asyncio
async def test_join_circle_already_member(client: AsyncClient, session):
    # Host creates circle
    _, host_headers = await create_user_and_get_headers(client)
    
    circle_resp = await client.post(
        f"{settings.API_V1_STR}/circles/",
        json={
            "name": "Double Join Circle",
            "amount": 1000,
            "frequency": "weekly",
            "payout_preference": "fixed"
        },
        headers=host_headers
    )
    invite_code = circle_resp.json()["data"]["invite_code"]
    
    # Host tries to join own circle again (should fail)
    join_resp = await client.post(
        f"{settings.API_V1_STR}/circles/join?invite_code={invite_code}",
        headers=host_headers
    )
    
    assert join_resp.status_code == 400
    # API error response typical structure: {"detail": "..."} not {"message": "..."}
    # Check detail
    assert "already a member" in join_resp.json()["detail"].lower()

@pytest.mark.asyncio
async def test_start_circle(client: AsyncClient, session):
    # Host creates circle
    _, host_headers = await create_user_and_get_headers(client)
    
    circle_resp = await client.post(
        f"{settings.API_V1_STR}/circles/",
        json={
            "name": "Start Circle",
            "amount": 1000,
            "frequency": "weekly",
            "payout_preference": "random"
        },
        headers=host_headers
    )
    circle_id = circle_resp.json()["data"]["id"]
    invite_code = circle_resp.json()["data"]["invite_code"]
    
    # Member joins to make it > 1 member
    _, member_headers = await create_user_and_get_headers(client)
    await client.post(
        f"{settings.API_V1_STR}/circles/join?invite_code={invite_code}",
        headers=member_headers
    )
    
    # Start circle
    start_resp = await client.post(
        f"{settings.API_V1_STR}/circles/{circle_id}/start",
        headers=host_headers
    )
    
    assert start_resp.status_code == 200
    data = start_resp.json()
    assert data["data"]["status"] == "active"

@pytest.mark.asyncio
async def test_get_circle_details(client: AsyncClient, session):
    _, headers = await create_user_and_get_headers(client)
    
    # Create circle
    resp = await client.post(
        f"{settings.API_V1_STR}/circles/",
        json={"name": "Details Circle", "amount": 100, "frequency": "weekly", "payout_preference": "fixed"},
        headers=headers
    )
    circle_id = resp.json()["data"]["id"]
    
    # Get details
    get_resp = await client.get(
        f"{settings.API_V1_STR}/circles/{circle_id}",
        headers=headers
    )
    
    # If this failed with KeyError data, maybe 404?
    # Or response structure difference?
    # Standard response: {"data": {...}}
    
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["id"] == circle_id
