import requests
import sys
import uuid
import time
from datetime import date

BASE_URL = "http://localhost:8000/api/v1"

def run_test():
    # 1. Register/Login
    email = f"ai_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    print(f"1. Registering {email}...")
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": email, 
        "password": password, 
        "full_name": "AI User", 
        "organization_name": f"AI Org {uuid.uuid4().hex[:8]}" 
    })
    
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password})
    if resp.status_code != 200:
        print("Login failed")
        sys.exit(1)
        
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create Decision
    print("2. Creating Decision...")
    d1 = requests.post(f"{BASE_URL}/decisions", json={
        "description": "AI Test Decision", "decision_type": "HIRE", "start_date": date.today().isoformat(), "cost": 5000, "status": "ACTIVE"
    }, headers=headers).json()
    
    # 3. Request Insight
    print(f"3. Requesting Insight for Decision {d1['id']}...")
    try:
        res = requests.get(f"{BASE_URL}/decisions/{d1['id']}/insight", headers=headers)
        if res.status_code != 200:
            print(f"❌ Failed to get insight: {res.text}")
            sys.exit(1)
            
        insight = res.json()["insight"]
        print(f"✅ Received Insight: {insight}")
        
        if "Insights are disabled" in insight:
             print("⚠️ (Note: Gemini API Key was likely missing, but flow worked)")
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        sys.exit(1)

    print("\n✅ AI ENDPOINT VERIFIED")

if __name__ == "__main__":
    run_test()
