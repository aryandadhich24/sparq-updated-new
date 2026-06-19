"""Notification preferences and email log routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from .. import models
from ..middleware.auth import get_current_user

router = APIRouter()


class NotificationPreferences(BaseModel):
    email_weekly_digest: Optional[bool] = None
    email_action_alerts: Optional[bool] = None
    email_sync_summaries: Optional[bool] = None


@router.get("/preferences")
def get_preferences(current_user: models.User = Depends(get_current_user)):
    """Get current user's notification preferences."""
    return {
        "email_weekly_digest": bool(current_user.email_weekly_digest),
        "email_action_alerts": bool(current_user.email_action_alerts),
        "email_sync_summaries": bool(current_user.email_sync_summaries),
    }


@router.put("/preferences")
def update_preferences(
    prefs: NotificationPreferences,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update notification preferences."""
    if prefs.email_weekly_digest is not None:
        current_user.email_weekly_digest = prefs.email_weekly_digest
    if prefs.email_action_alerts is not None:
        current_user.email_action_alerts = prefs.email_action_alerts
    if prefs.email_sync_summaries is not None:
        current_user.email_sync_summaries = prefs.email_sync_summaries

    db.add(current_user)
    db.commit()

    return {
        "email_weekly_digest": bool(current_user.email_weekly_digest),
        "email_action_alerts": bool(current_user.email_action_alerts),
        "email_sync_summaries": bool(current_user.email_sync_summaries),
        "message": "Preferences updated",
    }


@router.get("/history")
def email_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get email send history for current user."""
    logs = db.query(models.EmailLog).filter(
        models.EmailLog.user_id == current_user.id
    ).order_by(models.EmailLog.sent_at.desc()).limit(50).all()

    return [
        {
            "id": log.id,
            "type": log.email_type,
            "subject": log.subject,
            "sent_at": log.sent_at,
            "status": log.status,
        }
        for log in logs
    ]
