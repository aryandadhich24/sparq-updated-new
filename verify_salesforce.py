import requests
import time
import sys
import uuid

# Base URL
BASE_URL = "http://localhost:8000/api/v1"

def run_test():
    # 1. Register a new user
    user_email = f"salesforce_test_{str(uuid.uuid4())[:8]}@example.com"
    password = "password123"
    org_name = f"SF Org {str(uuid.uuid4())[:8]}"
    
    print(f"1. Registering/Logging in user {user_email}...")
    
    # Try register
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "email": user_email,
        "password": password,
        "full_name": "SF Test User",
        "organization_name": org_name
    })

    if resp.status_code != 200 and "already exists" not in resp.text:
         print("Registration failed:", resp.text)
         sys.exit(1)

    # Login to get token
    resp = requests.post(f"{BASE_URL}/auth/login", data={
        "username": user_email,
        "password": password
    })
    
    if resp.status_code != 200:
         print("Login failed:", resp.text)
         sys.exit(1)
         
    try:
        token = resp.json()["access_token"]
    except KeyError:
        print("Login response invalid:", resp.text)
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Check initial status
    print("2. Checking initial status...")
    resp = requests.get(f"{BASE_URL}/integrations/status", headers=headers)
    status = resp.json()
    if status["salesforce"]["connected"]:
        print("   Already connected? Unexpected for new user but ok.")
    else:
        print("   Not connected (Correct)")

    # 3. Simulate OAuth Callback
    print("3. Simulating OAuth callback exchange...")
    # Simulate the code we'd get from Salesforce
    mock_code = "mock_sf_auth_code_123"
    
    # Call the exchange endpoint directly (frontend does this)
    resp = requests.post(
        f"{BASE_URL}/integrations/salesforce/exchange?code={mock_code}", 
        headers=headers
    )
    
    if resp.status_code == 200:
        print("   Exchange successful.")
    else:
        print(f"❌ Exchange failed: {resp.status_code} {resp.text}")
        sys.exit(1)

    # 4. Check status again
    print("4. Checking status after exchange...")
    resp = requests.get(f"{BASE_URL}/integrations/status", headers=headers)
    status = resp.json()
    if status["salesforce"]["connected"]:
        print("   Connected (Correct)")
    else:
        print("❌ Still not connected!")
        sys.exit(1)

    # 5. Trigger Ingest
    print("5. Triggering Salesforce Ingest...")
    resp = requests.post(f"{BASE_URL}/integrations/salesforce/ingest", headers=headers)
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"   Success! {data}")
    else:
        print(f"❌ Ingest failed: {resp.text}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"❌ Exception: {e}")
        sys.exit(1)
