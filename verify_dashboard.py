import requests
import sys
import uuid
import time

BASE_URL = "http://localhost:8000/api/v1"

def run_test():
    # 1. Register/Login
    email = f"dash_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    print(f"1. Registering {email}...")
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": email, 
        "password": password, 
        "full_name": "Dash User", 
        "organization_name": f"Dash Org" 
    })
    
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password})
    if resp.status_code != 200:
        print("Login failed")
        sys.exit(1)
        
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create Data
    print("2. Creating Decisions...")
    d1 = requests.post(f"{BASE_URL}/decisions", json={
        "description": "Ad 1", "decision_type": "AD_CAMPAIGN", "start_date": "2026-01-01", "cost": 1000, "status": "ACTIVE", "source": "MANUAL"
    }, headers=headers).json()
    
    d2 = requests.post(f"{BASE_URL}/decisions", json={
        "description": "Hire 1", "decision_type": "HIRE", "start_date": "2026-02-01", "cost": 5000, "status": "ACTIVE", "source": "MANUAL"
    }, headers=headers).json()
    
    d3 = requests.post(f"{BASE_URL}/decisions", json={
        "description": "Tool 1", "decision_type": "TOOL", "start_date": "2026-03-01", "cost": 200, "status": "ENDED", "source": "MANUAL"
    }, headers=headers).json()
    
    # 3. Test Filter by Type
    print("3. Testing Filter by Type (HIRE)...")
    resp = requests.get(f"{BASE_URL}/decisions?decision_type=HIRE", headers=headers)
    data = resp.json()
    if len(data) != 1 or data[0]["decision_type"] != "HIRE":
        print(f"Filter Type failed: got {len(data)} items")
        sys.exit(1)
        
    # 4. Test Filter by Status
    print("4. Testing Filter by Status (ENDED)...")
    resp = requests.get(f"{BASE_URL}/decisions?status=ENDED", headers=headers)
    data = resp.json()
    if len(data) != 1 or data[0]["status"] != "ENDED":
        print(f"Filter Status failed: got {len(data)} items")
        sys.exit(1)
        
    # 5. Test Sort by Cost Desc
    print("5. Testing Sort by Cost Desc...")
    resp = requests.get(f"{BASE_URL}/decisions?sort_by=cost&order=desc", headers=headers)
    data = resp.json()
    costs = [d["total_cost"] for d in data]
    if costs != [5000, 1000, 200]:
        print(f"Sort Cost Desc failed: {costs}")
        sys.exit(1)

    # 6. Test Sort by Date Asc
    print("6. Testing Sort by Date Asc...")
    resp = requests.get(f"{BASE_URL}/decisions?sort_by=date&order=asc", headers=headers)
    data = resp.json()
    dates = [d["start_date"] for d in data]
    if dates != ["2026-01-01", "2026-02-01", "2026-03-01"]:
        print(f"Sort Date Asc failed: {dates}")
        sys.exit(1)

    print("\n✅ DASHBOARD API VERIFIED")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"❌ Exception: {e}")
        sys.exit(1)
