import pytest
from backend.app import models

def test_audit_log_on_decision_create(client, auth_headers, db):
    payload = {
        "description": "Audit Test Decision",
        "decision_type": "HIRE",
        "start_date": "2026-03-01",
        "cost": 5000.0
    }
    response = client.post("/api/v1/decisions", json=payload, headers=auth_headers)
    assert response.status_code == 200
    decision_id = response.json()["id"]
    
    # Check AuditLog table
    log = db.query(models.AuditLog).filter(
        models.AuditLog.resource_type == "DECISION",
        models.AuditLog.resource_id == str(decision_id),
        models.AuditLog.action == "CREATE"
    ).first()
    
    assert log is not None
    assert log.details["description"] == "Audit Test Decision"

def test_audit_log_on_decision_delete(client, auth_headers, db):
    # Setup: Create a decision
    payload = {
        "description": "Delete Me",
        "decision_type": "HIRE",
        "start_date": "2026-03-01",
        "cost": 5000.0
    }
    res = client.post("/api/v1/decisions", json=payload, headers=auth_headers)
    decision_id = res.json()["id"]
    
    # Delete it
    client.delete(f"/api/v1/decisions/{decision_id}", headers=auth_headers)
    
    # Check for DELETE log
    log = db.query(models.AuditLog).filter(
        models.AuditLog.resource_type == "DECISION",
        models.AuditLog.resource_id == str(decision_id),
        models.AuditLog.action == "DELETE"
    ).first()
    
    assert log is not None
    assert log.details["description"] == "Delete Me"

def test_list_audit_logs_permission(client, auth_headers):
    # Non-admin should be rejected
    # Note: Our conftest user is NOT an admin by default
    response = client.get("/api/v1/audit/", headers=auth_headers)
    assert response.status_code == 403
