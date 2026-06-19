import requests
import sys
import uuid
import time

BASE_URL = "http://localhost:8000/api/v1"

def run_test():
    # 1. Register/Login
    email = f"crud_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    print(f"1. Registering {email}...")
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": email, 
        "password": password, 
        "full_name": "CRUD User", 
        "organization_name": f"CRUD Org {uuid.uuid4().hex[:8]}" 
    })
    
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password})
    if resp.status_code != 200:
        print("Login failed")
        sys.exit(1)
        
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create Decision
    print("2. Creating Decision...")
    payload = {
        "description": "Test Decision",
        "decision_type": "HIRE",
        "start_date": "2026-01-01",
        "cost": 5000,
        "status": "ACTIVE",
        "source": "MANUAL"
    }
    resp = requests.post(f"{BASE_URL}/decisions", json=payload, headers=headers)
    if resp.status_code != 200:
        print(f"Create failed: {resp.text}")
        sys.exit(1)
    
    decision = resp.json()
    decision_id = decision["id"]
    print(f"   Created ID: {decision_id}")
    
    # 3. Update Decision
    print("3. Updating Decision...")
    resp = requests.put(f"{BASE_URL}/decisions/{decision_id}", json={"cost": 6000}, headers=headers)
    if resp.status_code != 200:
        print(f"Update failed: {resp.text}")
        sys.exit(1)
    
    updated = resp.json()
    if updated["cost"] != 6000:
        print("Update didn't persist!")
        sys.exit(1)
    print("   Update success.")
    
    # 4. Delete Decision
    print("4. Deleting Decision...")
    resp = requests.delete(f"{BASE_URL}/decisions/{decision_id}", headers=headers)
    if resp.status_code != 200:
        print(f"Delete failed: {resp.text}")
        sys.exit(1)
    print("   Delete success.")
    
    # 5. Verify Deletion
    resp = requests.get(f"{BASE_URL}/decisions/{decision_id}", headers=headers)
    if resp.status_code != 404:
        print("Decision still exists!")
        sys.exit(1)
        
    print("\n✅ CRUD VERIFIED")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"❌ Exception: {e}")
        sys.exit(1)
