import pytest
from httpx import AsyncClient
from app.models.circle import Circle, CircleMember
from app.models.wallet import Wallet
from app.models.user import User
from app.models.enums import CircleFrequency
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from datetime import datetime, timedelta
from app.core.config import settings
from tests.utils import create_user_and_get_headers

@pytest.mark.asyncio
async def test_contribution_progress(client: AsyncClient, session: AsyncSession):
    # 1. Create a Circle (User 1 - Host)
    user_1_data, headers_1 = await create_user_and_get_headers(client)
    
    # Get User 1 ID
    result = await session.execute(select(User).where(User.email == user_1_data["email"]))
    user_1_in_db = result.scalar_one()
    
    response = await client.post(
        f"{settings.API_V1_STR}/circles/",
        headers=headers_1,
        json={
            "name": "Progress Test Circle",
            "amount": 10000,
            "frequency": "weekly",
            "target_members": 2,
            "payout_preference": "fixed"
        },
    )
    assert response.status_code == 200
    circle_id = response.json()["data"]["id"]
    invite_code = response.json()["data"]["invite_code"]

    # 2. Add another member (User 2)
    user_2_data, headers_2 = await create_user_and_get_headers(client)
    
    # Get User 2 ID
    result = await session.execute(select(User).where(User.email == user_2_data["email"]))
    user_2_in_db = result.scalar_one()
    
    # User 2 joins
    join_resp = await client.post(
        f"{settings.API_V1_STR}/circles/join?invite_code={invite_code}",
        headers=headers_2
    )
    assert join_resp.status_code == 200
    
    # Re-fetch users from DB using session to ensure they are attached to current session if needed
    # We already have user objects user_1_in_db and user_2_in_db
    
    # Verify/Create Wallet for User 1
    result = await session.execute(select(Wallet).where(Wallet.user_id == user_1_in_db.id))
    wallet_1 = result.scalar_one_or_none()
    if not wallet_1:
        wallet_1 = Wallet(user_id=user_1_in_db.id, balance=50000)
        session.add(wallet_1)
    else:
        wallet_1.balance = 50000
        session.add(wallet_1)
        
    # Verify/Create Wallet for User 2
    result = await session.execute(select(Wallet).where(Wallet.user_id == user_2_in_db.id))
    wallet_2 = result.scalar_one_or_none()
    if not wallet_2:
        wallet_2 = Wallet(user_id=user_2_in_db.id, balance=50000)
        session.add(wallet_2)
    else:
        wallet_2.balance = 50000
        session.add(wallet_2)
        
    await session.commit()

    # 3. Start the Circle
    response = await client.post(
        f"{settings.API_V1_STR}/circles/{circle_id}/start",
        headers=headers_1,
    )
    assert response.status_code == 200

    # 4. Check Initial Progress (Cycle 1, 0 Paid)
    response = await client.get(
        f"{settings.API_V1_STR}/circles/{circle_id}",
        headers=headers_1,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    
    assert data["current_cycle"] == 1
    assert data["progress"]["cycle_number"] == 1
    assert data["progress"]["total_members"] == 2
    assert data["progress"]["paid_members"] == 0
    assert data["progress"]["pending_members"] == 2
    assert data["progress"]["collected_amount"] == 0
    assert len(data["contributions"]) == 2
    
    # Verify both are pending
    for c in data["contributions"]:
        assert c["status"] == "pending"

    # 5. Make a contribution for User 1 (Host)
    response = await client.post(
        f"{settings.API_V1_STR}/circles/{circle_id}/contribute",
        headers=headers_1,
    )
    assert response.status_code == 200
    
    # 6. Check Progress Again (Cycle 1, 1 Paid)
    response = await client.get(
        f"{settings.API_V1_STR}/circles/{circle_id}",
        headers=headers_1,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    
    # Check updated progress
    assert data["progress"]["paid_members"] == 1
    assert data["progress"]["pending_members"] == 1
    assert data["progress"]["collected_amount"] == 10000 # 10000 cents
    
    # Verify statuses
    for c in data["contributions"]:
        if c["user_id"] == str(user_1_in_db.id):
            assert c["status"] == "paid"
            assert c["paid_at"] is not None
        else:
            assert c["status"] == "pending"
