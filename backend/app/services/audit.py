from sqlalchemy.orm import Session
from .. import models
import json
from datetime import datetime

def log_action(db: Session, user: models.User, action: str, resource_type: str, resource_id: str, details: dict = None):
    """
    Logs an action to the audit_logs table.
    
    Args:
        db: Database session
        user: The user performing the action
        action: CREATE, UPDATE, DELETE
        resource_type: DECISION, OUTCOME, SETTINGS
        resource_id: ID of the resource
        details: Optional dictionary of details (e.g. diffs)
    """
    from fastapi.encoders import jsonable_encoder
    
    try:
        log_entry = models.AuditLog(
            user_id=user.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=jsonable_encoder(details) if details else None,
            timestamp=datetime.utcnow()
        )
        db.add(log_entry)
        # We don't commit here to allow the caller to commit as part of their transaction, 
        # OR we commit to ensure log is saved even if main transaction fails?
        # Standard practice: Atomic with the action. So caller commits.
        # BUT, if we want to log invalid attempts, we'd need separate commit.
        # For now, let's assume successful actions only.
        # Wait, the caller usually commits the content. We should flush/commit here if we want to be safe, 
        # but if the caller's transaction rolls back, the log should probably legally roll back too 
        # (check "transactional" requirement). 
        # For simple audit of *changes*, it should happen in same transaction.
    except Exception as e:
        print(f"Failed to create audit log: {e}")
