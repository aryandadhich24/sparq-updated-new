"""
Tests for the Decision CRUD API endpoints.

Covers:
  POST   /api/v1/decisions
  GET    /api/v1/decisions
  GET    /api/v1/decisions/{id}
  PUT    /api/v1/decisions/{id}
  DELETE /api/v1/decisions/{id}
"""

import pytest

# Reusable payload for creating decisions
_DECISION_PAYLOAD = {
    "description": "LinkedIn Q1 Campaign",
    "decision_type": "AD_CAMPAIGN",
    "start_date": "2026-01-15",
    "cost": 5000.0,
    "status": "ACTIVE",
    "source": "MANUAL",
}


class TestCreateDecision:
    """POST /api/v1/decisions"""

    def test_create_decision(self, test_client, auth_headers):
        resp = test_client.post(
            "/api/v1/decisions", json=_DECISION_PAYLOAD, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "LinkedIn Q1 Campaign"
        assert data["decision_type"] == "AD_CAMPAIGN"
        assert data["cost"] == 5000.0
        assert "id" in data

    def test_create_decision_unauthenticated(self, test_client):
        resp = test_client.post("/api/v1/decisions", json=_DECISION_PAYLOAD)
        assert resp.status_code == 401

    def test_create_decision_missing_fields(self, test_client, auth_headers):
        resp = test_client.post(
            "/api/v1/decisions",
            json={"description": "Incomplete"},
            headers=auth_headers,
        )
        assert resp.status_code == 422  # Pydantic validation


class TestListDecisions:
    """GET /api/v1/decisions"""

    def _seed(self, client, headers, count=3):
        ids = []
        for i in range(count):
            payload = {
                **_DECISION_PAYLOAD,
                "description": f"Decision {i}",
                "cost": 1000.0 * (i + 1),
            }
            resp = client.post("/api/v1/decisions", json=payload, headers=headers)
            ids.append(resp.json()["id"])
        return ids

    def test_list_decisions(self, test_client, auth_headers):
        self._seed(test_client, auth_headers, count=3)
        resp = test_client.get("/api/v1/decisions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 3

    def test_list_decisions_empty(self, test_client, auth_headers):
        resp = test_client.get("/api/v1/decisions", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_decision_filtering(self, test_client, auth_headers):
        """Filter decisions by type."""
        # Create one AD_CAMPAIGN and one HIRE
        test_client.post(
            "/api/v1/decisions",
            json={**_DECISION_PAYLOAD, "description": "Ad campaign"},
            headers=auth_headers,
        )
        test_client.post(
            "/api/v1/decisions",
            json={
                "description": "New AE hire",
                "decision_type": "HIRE",
                "start_date": "2026-02-01",
                "cost": 8000.0,
            },
            headers=auth_headers,
        )

        # Filter by AD_CAMPAIGN
        resp = test_client.get(
            "/api/v1/decisions?decision_type=AD_CAMPAIGN",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["decision_type"] == "AD_CAMPAIGN"

        # Filter by HIRE
        resp = test_client.get(
            "/api/v1/decisions?decision_type=HIRE",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_decision_status_filter(self, test_client, auth_headers):
        """Filter decisions by status."""
        test_client.post(
            "/api/v1/decisions",
            json={**_DECISION_PAYLOAD, "description": "Active one", "status": "ACTIVE"},
            headers=auth_headers,
        )
        test_client.post(
            "/api/v1/decisions",
            json={**_DECISION_PAYLOAD, "description": "Ended one", "status": "ENDED"},
            headers=auth_headers,
        )

        resp = test_client.get(
            "/api/v1/decisions?status=ACTIVE", headers=auth_headers
        )
        assert resp.status_code == 200
        assert all(d["status"] == "ACTIVE" for d in resp.json())


class TestGetDecisionDetail:
    """GET /api/v1/decisions/{decision_id}"""

    def test_get_decision_detail(self, test_client, auth_headers):
        create_resp = test_client.post(
            "/api/v1/decisions", json=_DECISION_PAYLOAD, headers=auth_headers
        )
        decision_id = create_resp.json()["id"]

        resp = test_client.get(
            f"/api/v1/decisions/{decision_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == decision_id
        assert data["description"] == "LinkedIn Q1 Campaign"
        # Should contain attribution fields (possibly default zeros)
        assert "roi" in data
        assert "confidence" in data
        assert "related_outcomes" in data

    def test_get_decision_not_found(self, test_client, auth_headers):
        resp = test_client.get("/api/v1/decisions/99999", headers=auth_headers)
        assert resp.status_code == 404


class TestUpdateDecision:
    """PUT /api/v1/decisions/{decision_id}"""

    def test_update_decision(self, test_client, auth_headers):
        create_resp = test_client.post(
            "/api/v1/decisions", json=_DECISION_PAYLOAD, headers=auth_headers
        )
        decision_id = create_resp.json()["id"]

        update_payload = {"description": "Updated Campaign Name", "cost": 7500.0}
        resp = test_client.put(
            f"/api/v1/decisions/{decision_id}",
            json=update_payload,
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "Updated Campaign Name"
        assert data["cost"] == 7500.0

    def test_update_decision_not_found(self, test_client, auth_headers):
        resp = test_client.put(
            "/api/v1/decisions/99999",
            json={"description": "Ghost"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestDeleteDecision:
    """DELETE /api/v1/decisions/{decision_id}"""

    def test_delete_decision(self, test_client, auth_headers):
        create_resp = test_client.post(
            "/api/v1/decisions", json=_DECISION_PAYLOAD, headers=auth_headers
        )
        decision_id = create_resp.json()["id"]

        resp = test_client.delete(
            f"/api/v1/decisions/{decision_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

        # Verify it's gone
        get_resp = test_client.get(
            f"/api/v1/decisions/{decision_id}", headers=auth_headers
        )
        assert get_resp.status_code == 404

    def test_delete_decision_not_found(self, test_client, auth_headers):
        resp = test_client.delete("/api/v1/decisions/99999", headers=auth_headers)
        assert resp.status_code == 404
