
import requests
import sys

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
import uuid
EMAIL = f"integration_test_{uuid.uuid4().hex[:8]}@example.com"
PASSWORD = "password123"

def register_and_login():
    print(f"1. Registering/Logging in user {EMAIL}...")
    # Register
    payload = {
        "email": EMAIL,
        "password": PASSWORD,
        "full_name": "Integration Tester",
        "organization_name": f"Integration Corp {uuid.uuid4().hex[:8]}"
    }
    requests.post(f"{BASE_URL}/auth/register", json=payload)
    
    # Login
    login_data = {
        "username": EMAIL,
        "password": PASSWORD
    }
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        sys.exit(1)
    
    return response.json()["access_token"]

def verify_integration_flow(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Check status (should be false)
    print("2. Checking initial status...")
    resp = requests.get(f"{BASE_URL}/integrations/status", headers=headers)
    status = resp.json()
    if status["hubspot"]["connected"]:
        print("❌ Error: Should not be connected yet.")
        return
    print("   Not connected (Correct)")

    # 2. Simulate Exchange (Mock Flow)
    print("3. Simulating OAuth callback exchange...")
    code = "test_auth_code"
    resp = requests.post(f"{BASE_URL}/integrations/hubspot/exchange?code={code}", headers=headers)
    if resp.status_code != 200:
        print(f"❌ Exchange failed: {resp.text}")
        return
    print("   Exchange successful.")

    # 3. Check status again (should be true)
    print("4. Checking status after exchange...")
    resp = requests.get(f"{BASE_URL}/integrations/status", headers=headers)
    status = resp.json()
    if not status["hubspot"]["connected"]:
        print("❌ Error: Should be connected now.")
        return
    print("   Connected (Correct)")

    # 4. Trigger Ingest
    print("5. Triggering HubSpot Ingest...")
    resp = requests.post(f"{BASE_URL}/integrations/hubspot/ingest", headers=headers)
    if resp.status_code != 200:
         print(f"❌ Ingest failed: {resp.text}")
         return
    data = resp.json()
    print(f"   Ingest result: {data}")
    
    if "Synced" not in data["message"]:
        print("❌ Unexpected ingest response.")
        return

    print("\n✅ INTEGRATION FLOW VERIFIED")

if __name__ == "__main__":
    try:
        token = register_and_login()
        verify_integration_flow(token)
    except Exception as e:
        print(f"❌ Exception: {e}")
