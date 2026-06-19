"""
Tests for authentication endpoints: register, login, /me, token refresh.

Covers the routes defined in backend/app/routes/auth.py.
"""

import pytest


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegister:
    """POST /api/v1/auth/register"""

    def test_register_success(self, test_client):
        """A new user with a new org should be created successfully."""
        payload = {
            "email": "newuser@example.com",
            "password": "Str0ngP@ss!",
            "full_name": "New User",
            "organization_name": "New Corp",
        }
        resp = test_client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "ADMIN"  # first user in org -> ADMIN
        assert "id" in data
        assert data["organization_id"] is not None

    def test_register_duplicate_email(self, test_client):
        """Registering the same email twice should return 400."""
        payload = {
            "email": "dup@example.com",
            "password": "password123",
            "full_name": "Dup User",
            "organization_name": "Dup Org",
        }
        resp1 = test_client.post("/api/v1/auth/register", json=payload)
        assert resp1.status_code == 200

        resp2 = test_client.post("/api/v1/auth/register", json=payload)
        assert resp2.status_code == 400
        assert "already exists" in resp2.json()["detail"]

    def test_register_missing_org_name(self, test_client):
        """Registration without an organization name should fail."""
        payload = {
            "email": "noorg@example.com",
            "password": "password123",
            "full_name": "No Org",
            "organization_name": "",
        }
        resp = test_client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 400
        assert "Organization name" in resp.json()["detail"]

    def test_register_invalid_email(self, test_client):
        """An invalid email should be rejected by Pydantic validation."""
        payload = {
            "email": "not-an-email",
            "password": "password123",
            "full_name": "Bad Email",
            "organization_name": "Some Org",
        }
        resp = test_client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 422  # Pydantic validation error


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:
    """POST /api/v1/auth/login (OAuth2 form)"""

    def _register(self, client, email="logintest@example.com"):
        client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "SecurePass1!",
            "full_name": "Login Tester",
            "organization_name": "Login Org",
        })

    def test_login_success(self, test_client):
        """Valid credentials should return a bearer token."""
        self._register(test_client)
        resp = test_client.post(
            "/api/v1/auth/login",
            data={"username": "logintest@example.com", "password": "SecurePass1!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, test_client):
        """Wrong password should return 400."""
        self._register(test_client, email="wrongpw@example.com")
        resp = test_client.post(
            "/api/v1/auth/login",
            data={"username": "wrongpw@example.com", "password": "WRONG"},
        )
        assert resp.status_code == 400
        assert "Incorrect" in resp.json()["detail"]

    def test_login_nonexistent_user(self, test_client):
        """A user that does not exist should get 400."""
        resp = test_client.post(
            "/api/v1/auth/login",
            data={"username": "ghost@example.com", "password": "whatever"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /me and token refresh
# ---------------------------------------------------------------------------

class TestMeAndRefresh:
    """GET /api/v1/auth/me and POST /api/v1/auth/refresh"""

    def test_me_endpoint(self, test_client, auth_headers):
        """Authenticated user should receive their own profile."""
        resp = test_client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "testuser@sparqai.com"
        assert data["full_name"] == "Test User"
        assert data["role"] == "ADMIN"

    def test_me_without_token(self, test_client):
        """Unauthenticated request to /me should return 401."""
        resp = test_client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_with_bad_token(self, test_client):
        """A garbage token should return 401."""
        resp = test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer totally.invalid.token"},
        )
        assert resp.status_code == 401

    def test_token_refresh(self, test_client, auth_headers):
        """Refreshing with a valid token should return a new token."""
        resp = test_client.post("/api/v1/auth/refresh", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # The new token should also work
        new_headers = {"Authorization": f"Bearer {data['access_token']}"}
        me_resp = test_client.get("/api/v1/auth/me", headers=new_headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "testuser@sparqai.com"

    def test_token_refresh_without_auth(self, test_client):
        """Refresh without a valid token should fail."""
        resp = test_client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401
