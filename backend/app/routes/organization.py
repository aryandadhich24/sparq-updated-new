from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..middleware.auth import get_current_user
from ..engine import engine as attribution_engine

router = APIRouter()

@router.get("/", response_model=schemas.Organization)
def get_organization_details(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    org = db.query(models.Organization).filter(models.Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Ensure settings is valid dict (in case it's null in DB)
    if not org.settings:
        org.settings = {}

    return org

@router.put("/settings", response_model=schemas.Organization)
def update_organization_settings(
    org_in: schemas.OrganizationUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    org = db.query(models.Organization).filter(models.Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    current_settings = dict(org.settings) if org.settings else {}
    old_window = current_settings.get("attribution_window")

    if org_in.settings:
        # Convert typed OrganizationSettings to dict, excluding unset fields
        current_settings.update(org_in.settings.model_dump(exclude_none=True))

    org.settings = current_settings

    db.add(org)
    db.commit()
    db.refresh(org)

    # Re-run attribution if the window changed
    new_window = current_settings.get("attribution_window")
    if new_window != old_window:
        background_tasks.add_task(
            attribution_engine.run_full_attribution,
            db,
            organization_id=current_user.organization_id,
        )

    return org
