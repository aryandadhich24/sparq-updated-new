import requests
import sys
import uuid
import time
from datetime import date, timedelta

BASE_URL = "http://localhost:8000/api/v1"

def run_test():
    # 1. Register/Login
    email = f"settings_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    print(f"1. Registering {email}...")
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": email, 
        "password": password, 
        "full_name": "Settings User", 
        "organization_name": f"Settings Org {uuid.uuid4().hex[:8]}" 
    })
    
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password})
    if resp.status_code != 200:
        print("Login failed")
        sys.exit(1)
        
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Update Settings (High Window)
    print("2. Setting Window to 10 days...")
    requests.put(f"{BASE_URL}/organization/settings", json={"settings": {"attribution_window": 10}}, headers=headers)
    
    # 3. Create Data (Decision 5 days ago, Outcome today => SHOULD Match)
    d1_date = (date.today() - timedelta(days=5)).isoformat()
    d1 = requests.post(f"{BASE_URL}/decisions", json={
        "description": "Short Window Test", "decision_type": "HIRE", "start_date": d1_date, "cost": 1000, "status": "ACTIVE"
    }, headers=headers).json()
    
    # Create Outcome (Not hard linked, relying on description match if needed or just time)
    # The attribution engine relies on Description Match OR Hard Link primarily.
    # Time Decay is a multiplier. If cost/val > 0.
    # We need to ensure text match to trigger attribution.
    requests.post(f"{BASE_URL}/outcomes", json={
        "metric_name": "REVENUE", "value": 5000, "date": date.today().isoformat(), "description": "Short Window Test Revenue"
    }, headers=headers)
    
    time.sleep(2) # Wait for async
    
    # Verify attribution
    d1_check = requests.get(f"{BASE_URL}/decisions/{d1['id']}", headers=headers).json()
    if d1_check["value"] == 0:
        print("❌ Expected attribution for 5 day gap (Window 10), got 0.")
        sys.exit(1)
        
    print("✅ Attribution worked for 5 day gap.")

    # 4. Update Settings (Low Window)
    print("4. Setting Window to 2 days...")
    requests.put(f"{BASE_URL}/organization/settings", json={"settings": {"attribution_window": 2}}, headers=headers)
    
    # Trigger re-calc?? Updating settings doesn't trigger calc automatically yet.
    # We need to trigger it manually or assume next data entry triggers it.
    # Let's just create a new decision/outcome pair to test the NEW window.
    # Or creating a new outcome triggers it. Let's create a dummy outcome.
    requests.post(f"{BASE_URL}/outcomes", json={
        "metric_name": "REVENUE", "value": 1, "date": date.today().isoformat(), "description": "Trigger Calc"
    }, headers=headers)
    time.sleep(2)
    
    d1_check = requests.get(f"{BASE_URL}/decisions/{d1['id']}", headers=headers).json()
    if d1_check["value"] > 0:
        print(f"❌ Expected NO attribution for 5 day gap (Window 2), got {d1_check['value']}.")
        # Note: Previous calculation might persist if run_full_attribution doesn't clear aggressively enough?
        # Engine: "Clear old attribution data for this org" -> YES, it deletes all.
        sys.exit(1)
        
    print("✅ Attribution REMOVED for 5 day gap after shrinking window.")
    print("\n✅ SETTINGS API VERIFIED")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"❌ Exception: {e}")
        sys.exit(1)
