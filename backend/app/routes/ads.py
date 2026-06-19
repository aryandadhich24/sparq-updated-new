"""
Ad Platform Sync Routes

Sync endpoints that pull campaign data from connected ad platforms
and create Decision records. OAuth is handled in integrations.py.
"""
import logging
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..middleware.auth import get_current_user
from ..core.crypto import decrypt
from ..engine import engine as attribution_engine
from .. import models

logger = logging.getLogger(__name__)
router = APIRouter()


def _sync_campaigns(
    db: Session,
    org_id: int,
    provider: str,
    campaigns: list,
    background_tasks: BackgroundTasks,
):
    """Shared logic: upsert Decision records from campaign data."""
    created = 0
    updated = 0

    for c in campaigns:
        # Check if we already imported this campaign (by source + meta_data.external_id)
        existing = db.query(models.Decision).filter(
            models.Decision.organization_id == org_id,
            models.Decision.source == provider,
            models.Decision.description == c["description"],
        ).first()

        if existing:
            existing.cost = c["cost"]
            existing.meta_data = c.get("meta_data")
            updated += 1
        else:
            # Ensure start_date is a date object, not a string
            raw_date = c.get("start_date", date.today())
            if isinstance(raw_date, str):
                raw_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()

            decision = models.Decision(
                description=c["description"],
                decision_type="AD_CAMPAIGN",
                start_date=raw_date,
                cost=c["cost"],
                status=c.get("status", "ACTIVE"),
                source=provider,
                organization_id=org_id,
                meta_data=c.get("meta_data"),
            )
            db.add(decision)
            created += 1

    db.commit()

    if created > 0:
        background_tasks.add_task(
            attribution_engine.run_full_attribution, db, organization_id=org_id
        )

    return {"created": created, "updated": updated}


# ---------------------------------------------------------------------------
# Google Ads Sync
# ---------------------------------------------------------------------------

@router.post("/google-ads/sync")
def sync_google_ads(
    background_tasks: BackgroundTasks,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    integration = db.query(models.Integration).filter(
        models.Integration.organization_id == current_user.organization_id,
        models.Integration.provider == "GOOGLE_ADS",
        models.Integration.is_active == True,
    ).first()
    if not integration:
        raise HTTPException(status_code=400, detail="Google Ads not connected")

    from ..integrations.google_ads import GoogleAdsConnector
    connector = GoogleAdsConnector(
        refresh_token=decrypt(integration.refresh_token) if integration.refresh_token else "",
        customer_id=(integration.config or {}).get("customer_id", ""),
    )
    raw_campaigns = connector.get_campaigns(start_date, end_date)
    campaigns = [connector.campaign_to_decision(c) for c in raw_campaigns]

    result = _sync_campaigns(db, current_user.organization_id, "GOOGLE_ADS", campaigns, background_tasks)
    return {"message": f"Google Ads sync complete", **result}


# ---------------------------------------------------------------------------
# Meta Ads Sync
# ---------------------------------------------------------------------------

@router.post("/meta-ads/sync")
def sync_meta_ads(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    integration = db.query(models.Integration).filter(
        models.Integration.organization_id == current_user.organization_id,
        models.Integration.provider == "META_ADS",
        models.Integration.is_active == True,
    ).first()
    if not integration:
        raise HTTPException(status_code=400, detail="Meta Ads not connected")

    from ..integrations.meta_ads import MetaAdsConnector
    connector = MetaAdsConnector(
        access_token=decrypt(integration.access_token),
        ad_account_id=(integration.config or {}).get("ad_account_id", ""),
    )
    raw_campaigns = connector.get_campaigns()
    campaigns = [connector.campaign_to_decision(c) for c in raw_campaigns]

    result = _sync_campaigns(db, current_user.organization_id, "META_ADS", campaigns, background_tasks)
    return {"message": "Meta Ads sync complete", **result}


# ---------------------------------------------------------------------------
# LinkedIn Ads Sync
# ---------------------------------------------------------------------------

@router.post("/linkedin-ads/sync")
def sync_linkedin_ads(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    integration = db.query(models.Integration).filter(
        models.Integration.organization_id == current_user.organization_id,
        models.Integration.provider == "LINKEDIN_ADS",
        models.Integration.is_active == True,
    ).first()
    if not integration:
        raise HTTPException(status_code=400, detail="LinkedIn Ads not connected")

    from ..integrations.linkedin_ads import LinkedInAdsConnector
    connector = LinkedInAdsConnector(
        access_token=decrypt(integration.access_token),
        account_id=(integration.config or {}).get("account_id", ""),
    )
    raw_campaigns = connector.get_campaigns()
    campaigns = [connector.campaign_to_decision(c) for c in raw_campaigns]

    result = _sync_campaigns(db, current_user.organization_id, "LINKEDIN_ADS", campaigns, background_tasks)
    return {"message": "LinkedIn Ads sync complete", **result}


# ---------------------------------------------------------------------------
# Ad integrations status (convenience — main status is in /integrations/status)
# ---------------------------------------------------------------------------

@router.get("/status")
def get_ad_integrations_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    integrations = db.query(models.Integration).filter(
        models.Integration.organization_id == current_user.organization_id,
        models.Integration.provider.in_(["GOOGLE_ADS", "META_ADS", "LINKEDIN_ADS"]),
    ).all()

    status = {
        "google_ads": {"connected": False, "last_sync": None},
        "meta_ads": {"connected": False, "last_sync": None},
        "linkedin_ads": {"connected": False, "last_sync": None},
    }

    for i in integrations:
        key = i.provider.lower()
        if key in status:
            status[key] = {
                "connected": i.is_active,
                "last_sync": i.updated_at.isoformat() if i.updated_at else None,
            }

    return status
