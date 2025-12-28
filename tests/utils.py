
import uuid
from httpx import AsyncClient
from app.core.config import settings

async def create_user(client: AsyncClient, email: str = None, password: str = "password123"):
    if not email:
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    
    register_data = {
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": "User",
        "phone_number": f"+234{uuid.uuid4().int % 10000000000:010d}"
    }
    
    resp = await client.post(f"{settings.API_V1_STR}/auth/signup", json=register_data)
    assert resp.status_code == 200
    return register_data

async def get_auth_headers(client: AsyncClient, email: str, password: str = "password123"):
    resp = await client.post(f"{settings.API_V1_STR}/auth/login", json={
        "email": email,
        "password": password
    })
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

async def create_user_and_get_headers(client: AsyncClient):
    user_data = await create_user(client)
    headers = await get_auth_headers(client, user_data["email"], user_data["password"])
    return user_data, headers
