
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_auth_flow():
    email = "test_client@sparq.ai"
    password = "password123"
    
    # 1. Register
    print("1. Registering new user...")
    payload = {
        "email": email,
        "password": password,
        "full_name": "Test Client User",
        "organization_name": "Test Client Org"
    }
    
    # Try register
    resp = client.post("/api/v1/auth/register", json=payload)
    if resp.status_code == 400 and "already exists" in resp.text:
        print("   User already exists, skipping registration.")
    elif resp.status_code != 200:
        print(f"   FATAL: Registration failed: {resp.text}")
        sys.exit(1)
    else:
        print("   Registration successful.")

    # 2. Login
    print("2. Logging in...")
    login_data = {
        "username": email,
        "password": password
    }
    resp = client.post("/api/v1/auth/login", data=login_data)
    if resp.status_code != 200:
        print(f"   FATAL: Login failed: {resp.text}")
        sys.exit(1)
    
    token = resp.json()["access_token"]
    print("   Login successful. Token acquired.")

    # 3. Verify /me
    print("3. Verifying /me endpoint...")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/v1/auth/me", headers=headers)
    if resp.status_code == 200:
        user = resp.json()
        print(f"   /me success! Logged in as: {user['email']} (Org ID: {user['organization_id']})")
        assert user["email"] == email
        assert user["organization_id"] is not None
    else:
        print(f"   FATAL: /me failed: {resp.text}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        test_auth_flow()
        print("\n✅ AUTH VERIFICATION PASSED")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)
