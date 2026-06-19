from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from .. import models
from ..database import get_db
from ..middleware.auth import get_current_user

router = APIRouter()

@router.get("/")
def list_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List audit logs for the organization (Admin only). Paginated."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only Admins can view audit logs.")

    user_ids = [uid[0] for uid in db.query(models.User.id).filter(
        models.User.organization_id == current_user.organization_id
    ).all()]

    base_query = db.query(models.AuditLog).filter(
        models.AuditLog.user_id.in_(user_ids)
    )

    total = base_query.count()
    logs = base_query.order_by(
        models.AuditLog.timestamp.desc()
    ).offset((page - 1) * per_page).limit(per_page).all()

    results = []
    for log in logs:
        results.append({
            "id": log.id,
            "user": log.user.full_name if log.user else "Unknown",
            "user_email": log.user.email if log.user else "Unknown",
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "timestamp": log.timestamp
        })

    return {
        "items": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }
