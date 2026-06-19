from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
from ..middleware.auth import get_current_user
from ..utils.csv_generator import generate_csv_response
from datetime import datetime

router = APIRouter()

@router.get("/decisions")
def export_decisions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Export all decisions for the organization as CSV."""
    decisions = db.query(models.Decision).filter(
        models.Decision.organization_id == current_user.organization_id
    ).all()
    
    if not decisions:
        data = []
    else:
        data = []
        for d in decisions:
            data.append({
                "id": d.id,
                "description": d.description,
                "type": d.decision_type,
                "status": d.status,
                "start_date": d.start_date.isoformat() if d.start_date else "",
                "end_date": d.end_date.isoformat() if d.end_date else "",
                "cost": d.cost,
                "currency": d.currency,
                "source": d.source
            })
            
    fieldnames = ["id", "description", "type", "status", "start_date", "end_date", "cost", "currency", "source"]
    csv_content = generate_csv_response(data, fieldnames)
    
    filename = f"decisions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/audit")
def export_audit_logs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Export all audit logs for the organization as CSV (Admin only)."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only Admins can export audit logs.")
        
    # Get all user IDs in org
    user_ids = db.query(models.User.id).filter(
        models.User.organization_id == current_user.organization_id
    ).all()
    user_ids = [uid[0] for uid in user_ids]
    
    logs = db.query(models.AuditLog).filter(
        models.AuditLog.user_id.in_(user_ids)
    ).order_by(models.AuditLog.timestamp.desc()).all()
    
    data = []
    for log in logs:
        data.append({
            "timestamp": log.timestamp.isoformat(),
            "user": log.user.full_name if log.user else "Unknown",
            "user_email": log.user.email if log.user else "Unknown",
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": str(log.details)
        })
        
    fieldnames = ["timestamp", "user", "user_email", "action", "resource_type", "resource_id", "details"]
    csv_content = generate_csv_response(data, fieldnames)
    
    filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
