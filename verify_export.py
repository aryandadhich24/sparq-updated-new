import requests
import sys
import uuid
import time

BASE_URL = "http://localhost:8000/api/v1"

def run_test():
    # 1. Register/Login Admin
    admin_email = f"export_admin_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    print(f"1. Registering ADMIN {admin_email}...")
    
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": admin_email, "password": password, "full_name": "Export Admin", "organization_name": f"Export Org {uuid.uuid4().hex[:8]}"
    })
    
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": admin_email, "password": password})
    if resp.status_code != 200:
        print(f"❌ Login failed: {resp.text}")
        sys.exit(1)
        
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # HACK: Promote to ADMIN
    import sqlite3
    conn = sqlite3.connect("backend/test.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role='ADMIN' WHERE email=?", (admin_email,))
    conn.commit()
    conn.close()

    # 2. Seed some data so we have something to export
    print("2. Seeding Data...")
    requests.post(f"{BASE_URL}/seed", headers=headers)

    # 3. Test Export Decisions
    print("3. Testing Export Decisions...")
    res = requests.get(f"{BASE_URL}/export/decisions", headers=headers)
    if res.status_code != 200:
        print(f"❌ Export Decisions failed: {res.text}")
        sys.exit(1)
    
    csv_content = res.text
    if "description" in csv_content and "LinkedIn Q1 Campaign" in csv_content:
        print("✅ Decisions CSV correctly generated.")
    else:
        print(f"❌ Decisions CSV content missing. Found: {csv_content[:100]}")
        sys.exit(1)

    # 4. Test Export Audit Logs
    print("4. Testing Export Audit Logs...")
    res = requests.get(f"{BASE_URL}/export/audit", headers=headers)
    if res.status_code != 200:
        print(f"❌ Export Audit Logs failed: {res.text}")
        sys.exit(1)
        
    audit_csv = res.text
    if "action" in audit_csv and "user_email" in audit_csv:
        print("✅ Audit Logs CSV correctly generated.")
    else:
        print(f"❌ Audit Logs CSV content missing. Found: {audit_csv[:100]}")
        sys.exit(1)
         
    print("✅ DATA EXPORT VERIFIED")

if __name__ == "__main__":
    run_test()
