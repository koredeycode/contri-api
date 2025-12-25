import asyncio
import httpx
import uuid

BASE_URL = "http://localhost:8000/api/v1"

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Signup
        email = f"test_{uuid.uuid4()}@example.com"
        password = "password123"
        print(f"Registering user: {email}")
        
        response = await client.post(f"{BASE_URL}/auth/signup", json={
            "email": email,
            "password": password,
            "first_name": "Test",
            "last_name": "User"
        })
        if response.status_code != 200:
            print(f"Signup failed: {response.text}")
            return
        
        user_data = response.json()
        print(f"User created: {user_data['id']}")

        # 2. Login
        response = await client.post(f"{BASE_URL}/auth/login", data={
            "username": email,
            "password": password
        })
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Logged in successfully")

        # 3. Get Wallet
        print("\nTesting Wallet Endpoint...")
        response = await client.get(f"{BASE_URL}/wallet/", headers=headers)
        if response.status_code == 200:
            wallet = response.json()
            print(f"Wallet retrieved: Balance {wallet['balance']} {wallet['currency']}")
        else:
            print(f"Get Wallet failed: Status {response.status_code} - {response.text}")

        # 4. Add Bank Account
        print("\nTesting Bank Account Endpoint...")
        response = await client.post(f"{BASE_URL}/wallet/banks", headers=headers, json={
            "bank_name": "GTBank",
            "account_number": "0123456789",
            "account_name": "Test User",
            "bank_code": "058"
        })
        if response.status_code == 200:
            bank = response.json()
            print(f"Bank linked: {bank['bank_name']} - {bank['account_number']}")
        else:
            # Endpoint path might be /banks or /wallet/banks depending on routing
            # Checked wallet.py -> @router.post("/banks")
            # Checked api.py -> prefix="/wallet"
            # So it is /wallet/banks
            print(f"Link Bank failed: {response.text}")

        # 5. Create Circle
        print("\nTesting Create Circle Endpoint...")
        response = await client.post(f"{BASE_URL}/circles/", headers=headers, json={
            "name": "My Savings Circle",
            "amount": 50000.00,
            "frequency": "monthly",
            "cycle_start_date": "2024-01-01T00:00:00"
        })
        if response.status_code == 200:
            circle = response.json()
            print(f"Circle created: {circle['name']} (Code: {circle['invite_code']})")
            circle_id = circle["id"]
        else:
            print(f"Create Circle failed: {response.text}")
            circle_id = None

        # 6. List Circles
        if circle_id:
            print("\nTesting List Circles Endpoint...")
            response = await client.get(f"{BASE_URL}/circles/", headers=headers)
            if response.status_code == 200:
                circles = response.json()
                print(f"Circles found: {len(circles)}")
            else:
                print(f"List Circles failed: {response.text}")

        # 7. Notifications
        print("\nTesting Notifications Endpoint...")
        response = await client.get(f"{BASE_URL}/notifications/", headers=headers)
        if response.status_code == 200:
            notifs = response.json()
            print(f"Notifications: {len(notifs)}")
        else:
            print(f"Get Notifications failed: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())
