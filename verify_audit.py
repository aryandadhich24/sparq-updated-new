import requests
import sys
import uuid
import time

BASE_URL = "http://localhost:8000/api/v1"

def run_test():
    # 1. Register/Login Admin
    admin_email = f"audit_admin_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    print(f"1. Registering ADMIN {admin_email}...")
    
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": admin_email, "password": password, "full_name": "Audit Admin", "organization_name": f"Audit Org {uuid.uuid4().hex[:8]}"
    })
    
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": admin_email, "password": password})
    if resp.status_code != 200:
        print(f"❌ Login failed: {resp.text}")
        sys.exit(1)
        
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # HACK: Promote to ADMIN (required for fetching audit logs)
    import sqlite3
    conn = sqlite3.connect("backend/test.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role='ADMIN' WHERE email=?", (admin_email,))
    conn.commit()
    conn.close()

    # 2. Perform Actions
    print("2. Performing Actions...")
    
    # CREATE Decision
    print("   -> Creating Decision...")
    res = requests.post(f"{BASE_URL}/decisions", json={
        "description": "Audit Test Decision",
        "decision_type": "HIRE",
        "start_date": "2026-03-01",
        "cost": 5000,
        "status": "ACTIVE"
    }, headers=headers)
    decision_id = res.json()["id"]
    
    # UPDATE Decision
    print("   -> Updating Decision...")
    requests.put(f"{BASE_URL}/decisions/{decision_id}", json={
        "description": "Audit Test Decision UPDATED",
        "cost": 6000
    }, headers=headers)
    
    # DELETE Decision
    print("   -> Deleting Decision...")
    requests.delete(f"{BASE_URL}/decisions/{decision_id}", headers=headers)
    
    # 3. Verify Logs
    print("3. Verifying Audit Logs...")
    # Wait a sec for potential async write? (It's synchronous in code but good practice)
    time.sleep(1)
    
    res = requests.get(f"{BASE_URL}/audit", headers=headers)
    if res.status_code != 200:
        print(f"❌ Failed to fetch logs: {res.text}")
        sys.exit(1)
        
    logs = res.json()
    print(f"   -> Found {len(logs)} logs.")
    
    # Check for specific actions
    actions = [l["action"] for l in logs]
    resource_ids = [l["resource_id"] for l in logs]
    
    print(f"   -> Actions found: {actions}")
    
    if "CREATE" in actions and "UPDATE" in actions and "DELETE" in actions:
        print("✅ Found CREATE, UPDATE, DELETE logs.")
    else:
        print("❌ Missing expected log actions.")
        sys.exit(1)
        
    if str(decision_id) in resource_ids:
        print(f"✅ Logs reference correct Decision ID: {decision_id}")
    else:
         print(f"❌ Logs do not reference Decision ID: {decision_id}")
         sys.exit(1)
         
    print("✅ AUDIT LOGS VERIFIED")

if __name__ == "__main__":
    run_test()
