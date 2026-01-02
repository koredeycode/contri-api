import asyncio
import httpx
import uuid
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.core.config import settings

print(settings.SMTP_USER)
print(settings.SMTP_PASSWORD)

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
HOST_EMAIL = f"host_{uuid.uuid4().hex[:6]}@example.com"
MEMBER_EMAIL = f"member_{uuid.uuid4().hex[:6]}@example.com"
PASSWORD = "password123"

async def get_db_session():
    return AsyncSessionLocal()

async def fund_wallet(email: str, amount: float):
    """Directly update wallet balance in DB since deposit endpoint is mocked"""
    print(f"💰 Funding wallet for {email} with {amount}...")
    async with await get_db_session() as session:
        # Find user
        res = await session.execute(text(f"SELECT id FROM \"user\" WHERE email = '{email}'"))
        user_id = res.scalar()
        if not user_id:
            print(f"❌ User {email} not found for funding")
            return
            
        # Update wallet
        await session.execute(text(f"UPDATE wallet SET balance = balance + {int(amount * 100)} WHERE user_id = '{user_id}'"))
        await session.commit()
        print("✅ Wallet funded.")

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"🚀 Starting Email Trigger Simulation")
        print(f"Host: {HOST_EMAIL}")
        print(f"Member: {MEMBER_EMAIL}")
        
        # 1. Signup Host (Triggers Welcome Email)
        print("\n1️⃣ Registering Host...")
        resp = await client.post(f"{BASE_URL}/auth/signup", json={
            "email": HOST_EMAIL,
            "password": PASSWORD,
            "first_name": "Host",
            "last_name": "User",
            "phone_number": f"+234{uuid.uuid4().int}"[:14]
        })
        if resp.status_code != 200:
            print(f"❌ Failed to signup host: {resp.text}")
            return
        
        # Login Host
        resp = await client.post(f"{BASE_URL}/auth/login", json={
            "email": HOST_EMAIL,
            "password": PASSWORD
        })
        if resp.status_code != 200:
            print(f"❌ Failed to login host: {resp.text}")
            return
            
        host_token = resp.json()["data"]["access_token"]
        host_headers = {"Authorization": f"Bearer {host_token}"}
        
        # 2. Signup Member (Triggers Welcome Email)
        print("\n2️⃣ Registering Member...")
        resp = await client.post(f"{BASE_URL}/auth/signup", json={
            "email": MEMBER_EMAIL,
            "password": PASSWORD,
            "first_name": "Member",
            "last_name": "User",
            "phone_number": f"+234{uuid.uuid4().int}"[:14]
        })
        if resp.status_code != 200:
            print(f"❌ Failed to signup member: {resp.text}")
            return
        
        # Login Member
        resp = await client.post(f"{BASE_URL}/auth/login", json={
            "email": MEMBER_EMAIL,
            "password": PASSWORD
        })
        if resp.status_code != 200:
            print(f"❌ Failed to login member: {resp.text}")
            return

        member_token = resp.json()["data"]["access_token"]
        member_headers = {"Authorization": f"Bearer {member_token}"}
        
        # 3. Create Circle
        print("\n3️⃣ Creating Circle...")
        circle_data = {
            "name": "Vacation Fund",
            "description": "Saving for summer",
            "amount": 500000, # 5000 NGN (in cents)
            "frequency": "monthly",
            "payout_preference": "fixed" 
        }
        resp = await client.post(f"{BASE_URL}/circles/", json=circle_data, headers=host_headers)
        if resp.status_code != 200:
            print(f"❌ Failed to create circle: {resp.text}")
            return
        circle = resp.json()["data"]
        circle_id = circle["id"]
        invite_code = circle["invite_code"]
        print(f"✅ Circle '{circle['name']}' created. ID: {circle_id}, Invite: {invite_code}")

        # 4. Join Circle (Triggers Circle Joined for Member, Member Joined for Host)
        print(f"\n4️⃣ Member Joining Circle...")
        resp = await client.post(f"{BASE_URL}/circles/join", params={"invite_code": invite_code}, headers=member_headers)
        if resp.status_code != 200:
            print(f"❌ Failed to join circle: {resp.text}")
            return
        print("✅ Member joined.")
        
        # 5. Start Circle (Triggers Circle Started)
        print(f"\n5️⃣ Starting Circle...")
        # Start endpoint might require ensuring minimum members or just start?
        # Logic says min 2 members. we have Host + Member = 2.
        resp = await client.post(f"{BASE_URL}/circles/{circle_id}/start", headers=host_headers)
        if resp.status_code != 200:
            print(f"❌ Failed to start circle: {resp.text}")
            return
        print("✅ Circle started.")
        
        # Fund Wallets for Contribution
        await fund_wallet(HOST_EMAIL, 100000) # 100k
        await fund_wallet(MEMBER_EMAIL, 100000) # 100k
        
        # 6. Host Contributes (Triggers Contribution Success)
        print(f"\n6️⃣ Host Contributing...")
        resp = await client.post(f"{BASE_URL}/circles/{circle_id}/contribute", headers=host_headers)
        if resp.status_code != 200:
            print(f"❌ Host contribution failed: {resp.text}")
            return
        print("✅ Host contributed.")
        
        # 7. Member Contributes (Triggers Contribution Success AND Payout Ready if cycle complete)
        print(f"\n7️⃣ Member Contributing...")
        resp = await client.post(f"{BASE_URL}/circles/{circle_id}/contribute", headers=member_headers)
        if resp.status_code != 200:
            print(f"❌ Member contribution failed: {resp.text}")
            return
        # Check if payout triggered
        data = resp.json()["data"]
        payout_triggered = data.get("payout_triggered", False)
        print(f"✅ Member contributed. Payout Triggered? {payout_triggered}")
        
        if payout_triggered:
            # 8. Claim Payout (Triggers Payout Received)
            # Find who is receiving. Order 1 is usually host or whoever was first in fixed list.
            # Host joined first (creator). Member joined second.
            # Usually creator is index 0 -> Order 1.
            print(f"\n8️⃣ Host Claiming Payout...")
            resp = await client.post(f"{BASE_URL}/circles/{circle_id}/claim", headers=host_headers)
            if resp.status_code != 200:
                print(f"❌ Payout claim failed: {resp.text}")
                # Try member just in case random logic shuffled it
                print("Trying member claim...")
                resp = await client.post(f"{BASE_URL}/circles/{circle_id}/claim", headers=member_headers)
                if resp.status_code != 200:
                     print(f"❌ Member claim failed too: {resp.text}")
                else:
                     print("✅ Member claimed payout!")
            else:
                print("✅ Host claimed payout!")
                
        print("\n🎉 Simulation Complete! Check your Celery/Flower logs for email previews.")

if __name__ == "__main__":
    asyncio.run(main())
