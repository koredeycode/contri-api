
import asyncio
import sys
from unittest.mock import MagicMock, patch
import httpx

# We will patch the modules in app.api.v1.endpoints.auth directly, 
# BUT since the server runs in a separate process, we can't easily mock imports inside the running server from here using standard python mocks 
# UNLESS we run the test logic against the app object directly using TestClient, 
# OR we rely on a special test endpoint, OR we trust the "dry run" logic.

# Actually, the best way to test this without restarting the server with mocks injected 
# is to use FastAPI's TestClient which runs the app in the same process.
# So I will import the app and run it with TestClient.

import os
# Set env vars if needed
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5433/contri"

from httpx import AsyncClient, ASGITransport
from app.main import app

async def verify_social_flow():
    print("Verifying Social Login Flow...")
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
    
        # Mock Google
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_google:
            mock_google.return_value = {
                "email": "mock_google_user_v3@example.com",
                "sub": "google_123456_v3",
                "given_name": "Google",
                "family_name": "User"
            }
            
            print("1. Testing Google Login (New User with Names)")
            # Google endpoint only takes token
            response = await client.post("/api/v1/auth/social/google", json={
                "token": "valid_google_token"
            })
            
            if response.status_code == 200:
                print("   SUCCESS: Google login returned 200")
                token = response.json().get("access_token")
                if token:
                    # Verify names via /me
                    response_me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
                    if response_me.status_code == 200:
                        data = response_me.json()
                        if data["first_name"] == "Google" and data["last_name"] == "User":
                             print("   SUCCESS: Google names extracted correctly")
                        else:
                             print(f"   FAILED: Names mismatch: {data}")
                             return False
                    else:
                        print(f"   FAILED: Could not get profile: {response_me.status_code}")
                        return False
            else:
                print(f"   FAILED: {response.status_code} {response.text}")
                return False

        # Mock Apple
        with patch("requests.get") as mock_get, \
             patch("jwt.decode") as mock_jwt_decode, \
             patch("jwt.get_unverified_header") as mock_header_decode, \
             patch("jwt.algorithms.RSAAlgorithm.from_jwk") as mock_rsa:
            
            # Mock keys response
            mock_get.return_value.json.return_value = {
                "keys": [{"kid": "test_key_id", "n": "...", "e": "..."}]
            }
            
            mock_header_decode.return_value = {"kid": "test_key_id"}
            mock_rsa.return_value = "mock_public_key"
            
            mock_jwt_decode.return_value = {
                "email": "mock_apple_user_v3@example.com",
                "sub": "apple_098765_v3"
            }

            print("3. Testing Apple Login (New User with Client Names)")
            response = await client.post("/api/v1/auth/social/apple", json={
                "token": "valid_apple_token",
                "first_name": "Apple",
                "last_name": "User"
            })
            
            if response.status_code == 200:
                 print("   SUCCESS: Apple login returned 200")
                 token = response.json().get("access_token")
                 if token:
                    # Verify names via /me
                    response_me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
                    if response_me.status_code == 200:
                        data = response_me.json()
                        if data["first_name"] == "Apple" and data["last_name"] == "User":
                             print("   SUCCESS: Apple names saved correctly")
                        else:
                             print(f"   FAILED: Names mismatch: {data}")
                             return False
            else:
                 print(f"   FAILED: {response.status_code} {response.text}")
                 return False

    print("ALL CHECKS PASSED")
    return True

if __name__ == "__main__":
    try:
        if asyncio.run(verify_social_flow()):
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
