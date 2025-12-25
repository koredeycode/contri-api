import asyncio
import httpx
import sys

# Configure verify check
BASE_URL = "http://localhost:8000/api/v1"

async def verify_auth():
    print("Verifying Auth Changes...")
    async with httpx.AsyncClient() as client:
        # 1. Signup with limited fields
        email = f"test_{asyncio.get_event_loop().time()}@example.com"
        password = "password123"
        print(f"1. Attempting Signup with: {email}")
        
        signup_data = {
            "email": email,
            "password": password,
            "first_name": "Test",
            "last_name": "User",
            "phone_number": "1234567890"
        }
        
        response = await client.post(f"{BASE_URL}/auth/signup", json=signup_data)
        if response.status_code != 200:
            print(f"FAILED: Signup failed with {response.status_code}: {response.text}")
            return False
        else:
            print("SUCCESS: Signup successful")
            user_data = response.json()
            if "hashed_password" in user_data:
                 print("FAILED: hashed_password leaked in response")
                 return False

        # 2. Login with JSON
        print("2. Attempting Login with JSON")
        login_data = {
            "email": email,
            "password": password
        }
        
        response = await client.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code != 200:
            print(f"FAILED: Login failed with {response.status_code}: {response.text}")
            return False
        else:
             print("SUCCESS: Login successful")
             token_data = response.json()
             access_token = token_data.get("access_token")
        
        # 3. Get /me
        print("3. Attempting GET /users/me")
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get(f"{BASE_URL}/users/me", headers=headers)
        
        if response.status_code != 200:
            print(f"FAILED: GET /me failed with {response.status_code}: {response.text}")
            return False
        else:
            print("SUCCESS: GET /me successful")
            me_data = response.json()
            if me_data["email"] != email:
                 print("FAILED: /me returned wrong email")
                 return False

        # 4. Verify Wallet Security
        print("4. Verifying Wallet Security")
        
        # 4a. Try without token
        print("   - Testing deposit without token")
        response = await client.post(f"{BASE_URL}/wallet/deposit")
        if response.status_code != 401:
             print(f"FAILED: Deposit should be 401 without token, got {response.status_code}")
             return False
        else:
             print("     SUCCESS: Deposit protected")

        print("   - Testing withdraw without token")
        response = await client.post(f"{BASE_URL}/wallet/withdraw")
        if response.status_code != 401:
             print(f"FAILED: Withdraw should be 401 without token, got {response.status_code}")
             return False
        else:
             print("     SUCCESS: Withdraw protected")

        # 4b. Try with token
        print("   - Testing deposit with token")
        response = await client.post(f"{BASE_URL}/wallet/deposit", headers=headers)
        if response.status_code != 200:
             print(f"FAILED: Deposit failed with token: {response.status_code} {response.text}")
             return False
        else:
             print("     SUCCESS: Deposit allowed")

        print("   - Testing withdraw with token")
        response = await client.post(f"{BASE_URL}/wallet/withdraw", headers=headers)
        if response.status_code != 200:
             print(f"FAILED: Withdraw failed with token: {response.status_code} {response.text}")
             return False
        else:
             print("     SUCCESS: Withdraw allowed")

    return True

if __name__ == "__main__":
    try:
        if asyncio.run(verify_auth()):
            print("\nALL VERIFICATION CHECKS PASSED")
            sys.exit(0)
        else:
            print("\nVERIFICATION FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"Error during verification: {e}")
        # If connection refused, maybe server is not running
        print("Ensure the server is running on localhost:8000")
        sys.exit(1)
