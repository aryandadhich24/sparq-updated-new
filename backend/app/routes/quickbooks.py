"""
QuickBooks Integration Routes

Provides OAuth flows and sync endpoints for QuickBooks Online.
"""
import os
import logging
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from ..database import get_db
from ..middleware.auth import get_current_user
from ..core.crypto import encrypt, decrypt
from ..core.security import create_access_token
from ..core.config import settings
from .. import models
from ..integrations import quickbooks

logger = logging.getLogger(__name__)
router = APIRouter()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def _create_qb_oauth_state(user: models.User) -> str:
    """Create a signed JWT state parameter for QuickBooks OAuth."""
    return create_access_token(
        data={
            "org_id": user.organization_id,
            "user_id": user.id,
            "provider": "quickbooks",
            "purpose": "oauth_state",
        },
        expires_delta=timedelta(minutes=10),
    )


def _validate_qb_oauth_state(state: str) -> dict:
    """Decode and validate a QuickBooks OAuth state JWT.

    Returns the decoded payload with org_id.
    Raises HTTPException(400) if invalid, expired, or wrong provider.
    """
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state parameter")
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    if payload.get("purpose") != "oauth_state":
        raise HTTPException(status_code=400, detail="Invalid OAuth state token purpose")
    if payload.get("provider") != "quickbooks":
        raise HTTPException(status_code=400, detail="OAuth state provider mismatch")

    return payload


@router.get("/connect")
def quickbooks_connect(
    current_user: models.User = Depends(get_current_user)
):
    redirect_uri = f"{os.getenv('BACKEND_URL', 'http://localhost:8000')}/api/v1/quickbooks/callback"
    state = _create_qb_oauth_state(current_user)
    auth_url = quickbooks.get_oauth_url(redirect_uri, state)
    return {"authorization_url": auth_url}


@router.get("/callback")
def quickbooks_callback(
    code: str,
    state: str,
    realmId: str = Query(..., description="QuickBooks company ID"),
    db: Session = Depends(get_db),
):
    payload = _validate_qb_oauth_state(state)
    org_id = payload["org_id"]

    redirect_uri = f"{os.getenv('BACKEND_URL', 'http://localhost:8000')}/api/v1/quickbooks/callback"

    try:
        tokens = quickbooks.exchange_code_for_tokens(code, redirect_uri)

        integration = db.query(models.Integration).filter(
            models.Integration.organization_id == org_id,
            models.Integration.provider == "QUICKBOOKS",
        ).first()

        if not integration:
            integration = models.Integration(
                provider="QUICKBOOKS",
                organization_id=org_id,
            )
            db.add(integration)

        integration.access_token = encrypt(tokens["access_token"])
        integration.refresh_token = encrypt(tokens["refresh_token"])
        integration.config = {"realm_id": realmId}
        integration.is_active = True
        db.commit()

        return {"message": "QuickBooks connected successfully", "redirect": f"{FRONTEND_URL}/integrations?connected=quickbooks"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"QuickBooks OAuth error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sync")
def sync_quickbooks(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    integration = db.query(models.Integration).filter(
        models.Integration.organization_id == current_user.organization_id,
        models.Integration.provider == "QUICKBOOKS",
        models.Integration.is_active == True,
    ).first()
    if not integration:
        raise HTTPException(status_code=400, detail="QuickBooks not connected")

    realm_id = (integration.config or {}).get("realm_id", "")
    connector = quickbooks.QuickBooksConnector(
        access_token=decrypt(integration.access_token),
        refresh_token=decrypt(integration.refresh_token) if integration.refresh_token else "",
        realm_id=realm_id,
    )

    payments = connector.get_vendor_payments(start_date, end_date)
    created = 0
    updated = 0

    for payment in payments:
        decision_data = connector.payment_to_decision(payment)
        existing = db.query(models.Decision).filter(
            models.Decision.organization_id == current_user.organization_id,
            models.Decision.source == "QUICKBOOKS",
            models.Decision.description == decision_data["description"],
        ).first()

        if existing:
            existing.cost = decision_data["cost"]
            updated += 1
        else:
            decision = models.Decision(
                description=decision_data["description"],
                decision_type=decision_data.get("decision_type", "VENDOR"),
                start_date=decision_data.get("start_date", date.today()),
                cost=decision_data["cost"],
                status="ACTIVE",
                source="QUICKBOOKS",
                organization_id=current_user.organization_id,
                meta_data=decision_data.get("details"),
            )
            db.add(decision)
            created += 1

    db.commit()
    return {"message": "QuickBooks sync complete", "created": created, "updated": updated}


@router.get("/status")
def get_quickbooks_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    integration = db.query(models.Integration).filter(
        models.Integration.organization_id == current_user.organization_id,
        models.Integration.provider == "QUICKBOOKS",
    ).first()

    if not integration:
        return {"connected": False, "last_sync": None}

    return {
        "connected": integration.is_active,
        "last_sync": integration.updated_at.isoformat() if integration.updated_at else None,
        "company_id": (integration.config or {}).get("realm_id"),
    }
