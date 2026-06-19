"""
Tests for the Outcome CRUD API and the automatic attribution trigger.

Covers:
  POST   /api/v1/outcomes
  DELETE /api/v1/outcomes/{id}
  Automatic attribution recalculation on outcome creation
"""

import pytest
from backend.app import models


_DECISION_PAYLOAD = {
    "description": "LinkedIn Q1 Campaign",
    "decision_type": "AD_CAMPAIGN",
    "start_date": "2026-01-15",
    "cost": 5000.0,
}


class TestCreateOutcome:
    """POST /api/v1/outcomes"""

    def _create_decision(self, client, headers):
        resp = client.post(
            "/api/v1/decisions", json=_DECISION_PAYLOAD, headers=headers
        )
        return resp.json()["id"]

    def test_create_outcome(self, test_client, auth_headers):
        decision_id = self._create_decision(test_client, auth_headers)

        payload = {
            "metric_name": "REVENUE",
            "value": 15000.0,
            "date": "2026-02-01",
            "description": "Acme Corp Deal",
            "decision_id": decision_id,
        }
        resp = test_client.post(
            "/api/v1/outcomes", json=payload, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metric_name"] == "REVENUE"
        assert data["value"] == 15000.0
        assert data["decision_id"] == decision_id
        assert "id" in data

    def test_create_outcome_without_decision_link(self, test_client, auth_headers):
        """An outcome without a decision_id should still be created (unlinked)."""
        payload = {
            "metric_name": "LEADS",
            "value": 50.0,
            "date": "2026-02-10",
            "description": "Inbound leads batch",
        }
        resp = test_client.post(
            "/api/v1/outcomes", json=payload, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision_id"] is None

    def test_create_outcome_with_invalid_decision(self, test_client, auth_headers):
        """Linking to a non-existent decision should return 404."""
        payload = {
            "metric_name": "REVENUE",
            "value": 5000.0,
            "date": "2026-02-15",
            "decision_id": 99999,
        }
        resp = test_client.post(
            "/api/v1/outcomes", json=payload, headers=auth_headers
        )
        assert resp.status_code == 404

    def test_create_outcome_unauthenticated(self, test_client):
        payload = {
            "metric_name": "REVENUE",
            "value": 5000.0,
            "date": "2026-02-15",
        }
        resp = test_client.post("/api/v1/outcomes", json=payload)
        assert resp.status_code == 401


class TestDeleteOutcome:
    """DELETE /api/v1/outcomes/{outcome_id}"""

    def _setup(self, client, headers):
        """Create a decision and an outcome linked to it."""
        d_resp = client.post(
            "/api/v1/decisions", json=_DECISION_PAYLOAD, headers=headers
        )
        decision_id = d_resp.json()["id"]

        o_resp = client.post(
            "/api/v1/outcomes",
            json={
                "metric_name": "REVENUE",
                "value": 10000.0,
                "date": "2026-02-05",
                "description": "Deal to delete",
                "decision_id": decision_id,
            },
            headers=headers,
        )
        return decision_id, o_resp.json()["id"]

    def test_delete_outcome(self, test_client, auth_headers):
        _, outcome_id = self._setup(test_client, auth_headers)
        resp = test_client.delete(
            f"/api/v1/outcomes/{outcome_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    def test_delete_outcome_not_found(self, test_client, auth_headers):
        resp = test_client.delete("/api/v1/outcomes/99999", headers=auth_headers)
        assert resp.status_code == 404


class TestOutcomeTriggersAttribution:
    """Creating an outcome should trigger attribution recalculation."""

    def test_outcome_triggers_attribution(self, test_client, auth_headers, test_db):
        """
        After creating a decision and a linked outcome via the API,
        the attribution engine should run and create Attribution rows.
        """
        # Create decision
        d_resp = test_client.post(
            "/api/v1/decisions", json=_DECISION_PAYLOAD, headers=auth_headers
        )
        decision_id = d_resp.json()["id"]

        # Create outcome linked to that decision
        o_resp = test_client.post(
            "/api/v1/outcomes",
            json={
                "metric_name": "REVENUE",
                "value": 20000.0,
                "date": "2026-02-01",
                "description": "Big Corp Win",
                "decision_id": decision_id,
            },
            headers=auth_headers,
        )
        assert o_resp.status_code == 200

        # The create_outcome endpoint calls run_full_attribution synchronously.
        # Verify that a summary Attribution row was created for the decision.
        summary = test_db.query(models.Attribution).filter(
            models.Attribution.decision_id == decision_id,
            models.Attribution.outcome_id == None,
        ).first()

        assert summary is not None, "Attribution summary row should exist after outcome creation"
        assert summary.attributed_value > 0, "Attributed value should be positive"
        assert summary.roi_multiple > 0, "ROI should be positive for a profitable outcome"
