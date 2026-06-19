import requests
import sys
import uuid
import time

BASE_URL = "http://localhost:8000/api/v1"

def run_test():
    # 1. Register/Login
    email = f"csv_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    print(f"1. Registering {email}...")
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": email, 
        "password": password, 
        "full_name": "CSV User", 
        "organization_name": f"CSV Org {uuid.uuid4().hex[:8]}" 
    })
    
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password})
    if resp.status_code != 200:
        print("Login failed")
        sys.exit(1)
        
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Bulk Import Decisions
    print("2. Bulk Importing Decisions...")
    decisions_payload = [
        {
            "description": "Bulk Decision 1",
            "decision_type": "HIRE",
            "start_date": "2026-03-01",
            "cost": 5000,
            "status": "ACTIVE",
            "source": "CSV"
        },
        {
            "description": "Bulk Decision 2",
            "decision_type": "AD_CAMPAIGN",
            "start_date": "2026-03-05",
            "cost": 2500,
            "status": "ACTIVE",
            "source": "CSV"
        }
    ]
    
    resp = requests.post(f"{BASE_URL}/import/decisions/bulk", json=decisions_payload, headers=headers)
    if resp.status_code != 200:
        print(f"Decision import failed: {resp.text}")
        sys.exit(1)
        
    print(f"   Response: {resp.json()}")
    
    # 3. Bulk Import Outcomes
    print("3. Bulk Importing Outcomes...")
    
    # First get a decision ID to link to
    resp = requests.get(f"{BASE_URL}/decisions", headers=headers)
    decisions = resp.json()
    decision_id = decisions[0]["id"]
    
    outcomes_payload = [
        {
            "description": "Bulk Outcome 1",
            "value": 10000,
            "date": "2026-03-10",
            "metric_name": "REVENUE",
            "decision_id": decision_id
        },
        {
            "description": "Bulk Outcome 2",
            "value": 5000,
            "date": "2026-03-15",
            "metric_name": "REVENUE"
        }
    ]
    
    resp = requests.post(f"{BASE_URL}/import/outcomes/bulk", json=outcomes_payload, headers=headers)
    if resp.status_code != 200:
        print(f"Outcome import failed: {resp.text}")
        sys.exit(1)
        
    print(f"   Response: {resp.json()}")
    
    print("   Waiting for background attribution...")
    time.sleep(2)
    
    # 4. Verify Data Exists
    print("4. Verifying Data...")
    resp = requests.get(f"{BASE_URL}/decisions", headers=headers)
    all_decisions = resp.json()
    if len(all_decisions) < 2:
        print("Decisions not found!")
        sys.exit(1)
        
    # Check outcomes
    # Note: Outcomes are not directly listed in an endpoint yet except via decision detail or if we added a list endpoint.
    # But detail check for decision 1 should show 1 linked outcome.
    resp = requests.get(f"{BASE_URL}/decisions/{decision_id}", headers=headers)
    detail = resp.json()
    if len(detail["related_outcomes"]) < 1:
         print("Linked outcome not found!")
         sys.exit(1)

    print("\n✅ CSV API VERIFIED")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"❌ Exception: {e}")
        sys.exit(1)
