import pytest
import uuid
import uuid
from app.models.wallet import Wallet
from sqlmodel import select

@pytest.mark.asyncio
async def test_contribution_flow(client, session):
    # 1. Setup Users
    email1 = f"user1_{uuid.uuid4()}@example.com"
    email2 = f"user2_{uuid.uuid4()}@example.com"
    password = "password123"
    
    # Register User 1
    resp = await client.post("/api/v1/auth/signup", json={
        "email": email1,
        "password": password,
        "first_name": "User",
        "last_name": "One",
        "phone_number": "+2348011111111"
    })
    assert resp.status_code == 200, resp.text
    
    # Login User 1
    resp = await client.post("/api/v1/auth/login", json={
        "email": email1,
        "password": password
    })
    token1 = resp.json()["data"]["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}
    
    # Register User 2
    resp = await client.post("/api/v1/auth/signup", json={
        "email": email2,
        "password": password,
        "first_name": "User",
        "last_name": "Two",
        "phone_number": "+2348022222222"
    })
    assert resp.status_code == 200, resp.text
    
    # Login User 2
    resp = await client.post("/api/v1/auth/login", json={
        "email": email2,
        "password": password
    })
    token2 = resp.json()["data"]["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}
    
    # 2. Fund Wallets (Direct DB)
    # Get User IDs
    resp = await client.get("/api/v1/users/me", headers=headers1)
    user1_id = uuid.UUID(resp.json()["data"]["id"])
    
    resp = await client.get("/api/v1/users/me", headers=headers2)
    user2_id = uuid.UUID(resp.json()["data"]["id"])
    
    # Update wallets
    q = select(Wallet).where(Wallet.user_id == user1_id)
    r = await session.execute(q)
    w1 = r.scalar_one()
    w1.balance = 5000000 # 50,000 NGN
    session.add(w1)
    
    q = select(Wallet).where(Wallet.user_id == user2_id)
    r = await session.execute(q)
    w2 = r.scalar_one()
    w2.balance = 5000000 # 50,000 NGN
    session.add(w2)
    await session.commit()
    
    # 3. Create Circle
    circle_data = {
        "name": "Test Circle",
        "amount": 1000000,
        "frequency": "weekly",
        "payout_preference": "fixed"
    }
    resp = await client.post("/api/v1/circles/", json=circle_data, headers=headers1)
    assert resp.status_code == 200, resp.text
    circle_id = resp.json()["data"]["id"]
    invite_code = resp.json()["data"]["invite_code"]
    
    # 4. User 2 Joins
    resp = await client.post(f"/api/v1/circles/join?invite_code={invite_code}", headers=headers2)
    assert resp.status_code == 200, resp.text
    
    # 5. Start Circle (User 1)
    resp = await client.post(f"/api/v1/circles/{circle_id}/start", headers=headers1)
    assert resp.status_code == 200, resp.text
    
    # 6. User 1 Contributes
    resp = await client.post(f"/api/v1/circles/{circle_id}/contribute", headers=headers1)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["payout_triggered"] is False
    
    # Check Wallet 1 Debit
    await session.refresh(w1)
    assert w1.balance == 4000000 # 50000 - 10000 = 40000
    
    # 7. User 2 Contributes
    resp = await client.post(f"/api/v1/circles/{circle_id}/contribute", headers=headers2)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["payout_triggered"] is True
    
    # Check Wallet 1 Debit
    await session.refresh(w1)
    assert w1.balance == 4000000 
    
    # Check Wallet 2 Debit
    await session.refresh(w2)
    assert w2.balance == 4000000
    
    # 8. User 1 Claims Payout (Manual Step)
    # User 1 is Order 1, Cycle 1 -> Eligible
    resp = await client.post(f"/api/v1/circles/{circle_id}/claim", headers=headers1)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["amount"] == 2000000 # 10000 * 2
    
    # 9. Check Wallet 1 Credit (Payout)
    # The pool is 1000000 * 2 = 2000000.
    # New Balance User 1 = 4000000 (after debit) + 2000000 (payout) = 6000000
    await session.refresh(w1)
    assert w1.balance == 6000000
