
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import Base, engine

# Reset DB for clean test
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

def register_and_login(email, password, org_name):
    print(f"   Registering {email}...")
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Test User",
        "organization_name": org_name
    })
    
    print(f"   Logging in {email}...")
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    if resp.status_code != 200:
        raise Exception(f"Login failed: {resp.text}")
    return resp.json()["access_token"]

def test_scoping():
    print("1. Setup User A (Org A)")
    token_a = register_and_login("userA@test.com", "pass123", "Org A")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    print("2. Setup User B (Org B)")
    token_b = register_and_login("userB@test.com", "pass123", "Org B")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    print("3. Seed Data for User A")
    resp = client.post("/api/v1/seed", headers=headers_a)
    assert resp.status_code == 200, f"Seed A failed: {resp.text}"
    
    # Check A sees data
    resp = client.get("/api/v1/decisions", headers=headers_a)
    data_a = resp.json()
    count_a = len(data_a)
    print(f"   User A sees {count_a} decisions.")
    assert count_a > 0

    print("4. Verify User B sees NOTHING")
    resp = client.get("/api/v1/decisions", headers=headers_b)
    data_b = resp.json()
    count_b = len(data_b)
    print(f"   User B sees {count_b} decisions.")
    assert count_b == 0

    print("5. Seed Data for User B")
    resp = client.post("/api/v1/seed", headers=headers_b)
    assert resp.status_code == 200
    
    # Check B sees only their data (seed creates fixed count)
    resp = client.get("/api/v1/decisions", headers=headers_b)
    data_b_new = resp.json()
    count_b_new = len(data_b_new)
    print(f"   User B now sees {count_b_new} decisions.")
    assert count_b_new == count_a # Should be same count if seed is deterministic

    # Verify A still sees only A's data (count shouldn't double)
    resp = client.get("/api/v1/decisions", headers=headers_a)
    data_a_new = resp.json()
    assert len(data_a_new) == count_a, "User A sees User B's data!"

    print("6. Verify Detail View Scoping")
    # A tries to see B's decision
    b_decision_id = data_b_new[0]["id"]
    resp = client.get(f"/api/v1/decisions/{b_decision_id}", headers=headers_a)
    assert resp.status_code == 404, "User A could access User B's decision detail!"
    print("   User A blocked from viewing User B's decision.")

if __name__ == "__main__":
    try:
        test_scoping()
        print("\n✅ DATA SCOPING VERIFIED")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)
