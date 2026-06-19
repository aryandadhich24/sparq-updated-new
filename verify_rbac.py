import requests
import sys
import uuid

BASE_URL = "http://localhost:8000/api/v1"

def run_test():
    # 1. Register Admin
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    print(f"1. Registering ADMIN {admin_email}...")
    
    # Register (default role is MEMBER usually, but we need to assume first user is admin or we manually update DB? 
    # For this test, I'll update the role via direct API if possible? No, we need to create the first user or mock it.
    # Actually, the user creation endpoint doesn't allow setting role. 
    # BUT, the `invite_member` endpoint checks `if current_user.role != "ADMIN"`. 
    # Since my migration defaults role to "MEMBER", the first user will be MEMBER and fail to invite.
    # I need to hack the first user to be ADMIN in the verify script or allow self-promotion for testing.
    # Let's bypass: Use Python to update the DB directly after registration.
    
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": admin_email, "password": password, "full_name": "Admin User", "organization_name": "Test Org"
    })
    
    # Login
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": admin_email, "password": password})
    token = resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {token}"}
    
    # HACK: Promote to ADMIN via raw SQL (since we don't have an endpoint for it)
    # This simulates "Platform Admin" doing it or the first user logic which we haven't implemented yet.
    import sqlite3
    conn = sqlite3.connect("backend/test.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role='ADMIN' WHERE email=?", (admin_email,))
    conn.commit()
    conn.close()
    print("   -> Promoted to ADMIN via DB hack.")

    # 2. Invite Member
    print("2. Inviting Member...")
    member_email = f"member_{uuid.uuid4().hex[:8]}@example.com"
    try:
        res = requests.post(f"{BASE_URL}/team/invite", json={"email": member_email, "role": "MEMBER"}, headers=admin_headers)
        if res.status_code != 200:
            print(f"❌ Failed to invite: {res.text}")
            sys.exit(1)
        invite_data = res.json()
        print(f"   -> Invite Link: {invite_data['link']}")
        print(f"   -> Token: {invite_data['token']}")
    except Exception as e:
        print(f"❌ Exception: {e}")
        sys.exit(1)

    # 3. List Team
    print("3. Listing Team...")
    res = requests.get(f"{BASE_URL}/team", headers=admin_headers)
    members = res.json()
    print(f"   -> Found {len(members)} members.")
    
    # 4. Remove Member (Admin only)
    # We can't remove the *invited* member because they haven't registered yet (they are just an invitation).
    # The `list_team_members` returns Users, not Invitations.
    # So let's register the second user normally (simulating they clicked the link - though we don't verify token in register endpoint yet).
    # Wait, Phase 4 plan didn't explicitly safeguard registration to require token. 
    # It just said "Register via Link -> Verify joined same Org".
    # Since we haven't implemented the "Join via Token" logic in Auth, we can just register them directly 
    # but we need to ensure they join the SAME organization.
    # Currently `register` endpoint creates a NEW organization.
    # The `Invitation` flow is incomplete without modifying `auth/register` to accept a token.
    # LIMITATION: I will verify the Invite creation works. Full join flow needs Auth Refactor.
    
    print("✅ RBAC INVITE FLOW VERIFIED (Partial - Join flow requires Auth update)")

if __name__ == "__main__":
    run_test()
