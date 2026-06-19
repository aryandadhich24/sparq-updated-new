from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
import datetime
import os

from .. import models, schemas
from ..database import get_db
from ..middleware.auth import get_current_user
from ..core.config import settings

router = APIRouter()

@router.get("/", response_model=List[schemas.User])
def list_team_members(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all users in the current organization."""
    members = db.query(models.User).filter(
        models.User.organization_id == current_user.organization_id
    ).all()
    return members

@router.post("/invite")
def invite_member(
    invite_in: schemas.UserInvite,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Generate an invitation link for a new member.
    RESTRICTION: Only ADMINs can invite others.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only Admins can invite members.")

    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == invite_in.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists.")

    # Check if invite already pending
    existing_invite = db.query(models.Invitation).filter(
        models.Invitation.email == invite_in.email,
        models.Invitation.organization_id == current_user.organization_id
    ).first()
    
    token = str(uuid.uuid4())
    expires = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    
    if existing_invite:
        existing_invite.token = token
        existing_invite.expires_at = expires
        existing_invite.role = invite_in.role
        invite = existing_invite
    else:
        invite = models.Invitation(
            email=invite_in.email,
            token=token,
            organization_id=current_user.organization_id,
            role=invite_in.role,
            expires_at=expires
        )
        db.add(invite)
    
    db.commit()
    
    # In a real app, we would send an email here.
    # For now, return the link.
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    invite_link = f"{frontend_url}/register?invite={token}"
    
    return {
        "message": "Invitation created",
        "link": invite_link,
        "token": token,
        "email": invite.email,
        "role": invite.role
    }

@router.delete("/{user_id}")
def remove_member(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Remove a member from the organization."""
    if current_user.role != "ADMIN" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    user_to_remove = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.organization_id == current_user.organization_id
    ).first()
    
    if not user_to_remove:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_to_remove.role == "ADMIN" and db.query(models.User).filter(
        models.User.organization_id == current_user.organization_id,
        models.User.role == "ADMIN"
    ).count() <= 1:
        raise HTTPException(status_code=400, detail="Cannot remove the last Admin.")

    # In a real app, we might soft delete or just remove org access.
    # Here, we'll set org_id to None (orphan them) or delete? 
    # Let's delete for simplicity in this MVP.
    db.delete(user_to_remove)
    db.commit()
    
    return {"message": "User removed from organization"}
