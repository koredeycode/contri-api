import pytest
import uuid
from httpx import AsyncClient
from sqlmodel import select
from app.core.config import settings
from tests.utils import create_user_and_get_headers
from app.models.wallet import Wallet
from app.models.user import User

@pytest.mark.asyncio
async def test_contribute_to_circle_flow(client: AsyncClient, session):
    # 1. Create Host User
    host_data, host_headers = await create_user_and_get_headers(client)

    # 2. Create Circle (Host creates)
    circle_resp = await client.post(
        f"{settings.API_V1_STR}/circles/",
        json={
            "name": "Contribution Test Circle",
            "amount": 5000, # 50.00 NGN
            "frequency": "weekly",
            "payout_preference": "fixed"
        },
        headers=host_headers
    )
    assert circle_resp.status_code == 200
    circle_id = circle_resp.json()["data"]["id"]
    invite_code = circle_resp.json()["data"]["invite_code"]

    # 3. Create Member User
    member_data, member_headers = await create_user_and_get_headers(client)

    # 4. Member Joins Circle
    join_resp = await client.post(
        f"{settings.API_V1_STR}/circles/join?invite_code={invite_code}",
        headers=member_headers
    )
    assert join_resp.status_code == 200

    # 5. Start Circle (needs at least 2 members)
    start_resp = await client.post(
        f"{settings.API_V1_STR}/circles/{circle_id}/start",
        headers=host_headers
    )
    assert start_resp.status_code == 200

    # 6. Fund Member Wallet (Direct DB Update)
    # Find member user id
    result = await session.execute(select(User).where(User.email == member_data["email"]))
    member_user = result.scalars().first()
    
    result = await session.execute(select(Wallet).where(Wallet.user_id == member_user.id))
    member_wallet = result.scalars().first()
    assert member_wallet is not None
    
    member_wallet.balance = 50000 # Fund with enough
    session.add(member_wallet)
    await session.commit()

    # 7. Contribute (Member contributes)
    contribute_resp = await client.post(
        f"{settings.API_V1_STR}/circles/{circle_id}/contribute",
        headers=member_headers
    )
    
    assert contribute_resp.status_code == 200
    data = contribute_resp.json()
    assert data["message"] == "Contribution successful"


@pytest.mark.asyncio
async def test_claim_payout_flow(client: AsyncClient, session):
    # 1. Create Host User
    host_data, host_headers = await create_user_and_get_headers(client)

    # 2. Create Circle
    circle_resp = await client.post(
        f"{settings.API_V1_STR}/circles/",
        json={
            "name": "Claim Test Circle",
            "amount": 5000, 
            "frequency": "weekly",
            "payout_preference": "fixed"
        },
        headers=host_headers
    )
    circle_id = circle_resp.json()["data"]["id"]
    invite_code = circle_resp.json()["data"]["invite_code"]

    # 3. Create Member User
    member_data, member_headers = await create_user_and_get_headers(client)

    # 4. Member Joins
    await client.post(
        f"{settings.API_V1_STR}/circles/join?invite_code={invite_code}",
        headers=member_headers
    )

    # 5. Start Circle
    await client.post(
        f"{settings.API_V1_STR}/circles/{circle_id}/start",
        headers=host_headers
    )
    
    # 6. Fund Wallets (Member & Host) for contribution
    # Assuming host is payout #1 (fixed order, host joined first)
    # Check order:
    # Host: Order 1
    # Member: Order 2
    
    # Fund Host Wallet
    result = await session.execute(select(User).where(User.email == host_data["email"]))
    host_user = result.scalars().first()
    result = await session.execute(select(Wallet).where(Wallet.user_id == host_user.id))
    host_wallet = result.scalars().first()
    host_wallet.balance = 50000
    session.add(host_wallet)
    
    # Fund Member Wallet
    result = await session.execute(select(User).where(User.email == member_data["email"]))
    member_user = result.scalars().first()
    result = await session.execute(select(Wallet).where(Wallet.user_id == member_user.id))
    member_wallet = result.scalars().first()
    member_wallet.balance = 50000
    session.add(member_wallet)
    
    await session.commit()
    
    # 7. Contribute (Both contribute for Cycle 1)
    # Host contributes
    resp = await client.post(f"{settings.API_V1_STR}/circles/{circle_id}/contribute", headers=host_headers)
    assert resp.status_code == 200
    
    # Member contributes
    resp = await client.post(f"{settings.API_V1_STR}/circles/{circle_id}/contribute", headers=member_headers)
    assert resp.status_code == 200
    
    # Cycle 1 is now funded. Payout Order 1 (Host) should be eligible.
    
    # 8. Host Claims Payout
    claim_resp = await client.post(f"{settings.API_V1_STR}/circles/{circle_id}/claim", headers=host_headers)
    
    assert claim_resp.status_code == 200
    data = claim_resp.json()
    assert data["message"] == "Payout claimed successfully"
    assert data["data"]["amount"] == 10000 # 5000 * 2 members
    
    # 9. Verify Host Wallet Balance increased
    new_host_wallet_balance = host_wallet.balance # Need refresh?
    await session.refresh(host_wallet)
    # Started 50000, Contributed -5000, Claimed +10000 = 55000
    assert host_wallet.balance == 55000
    
    # 10. Verify Circle Wallet Balance is 0
    query = select(Wallet).where(Wallet.circle_id == circle_id)
    result = await session.execute(query)
    circle_wallet = result.scalar_one()
    assert circle_wallet.balance == 0
