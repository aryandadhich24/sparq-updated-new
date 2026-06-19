"""SSO/SAML authentication routes."""

import os
import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from .. import models
from ..core import security, config
from ..middleware.auth import get_current_user

logger = logging.getLogger("sparqai.sso")
router = APIRouter()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


class SSOConfigRequest(BaseModel):
    provider: str  # okta, azure_ad, google
    metadata_url: Optional[str] = None
    entity_id: Optional[str] = None
    sso_url: Optional[str] = None


# ---------- Admin SSO configuration ----------

@router.get("/config")
def get_sso_config(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get SSO configuration for the organization."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")

    org = db.query(models.Organization).filter(
        models.Organization.id == current_user.organization_id
    ).first()

    return {
        "sso_enabled": org.sso_enabled,
        "provider": org.sso_provider,
        "entity_id": org.sso_entity_id,
        "acs_url": f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/v1/sso/acs",
        "metadata_url": org.sso_metadata_url,
    }


@router.put("/config")
def update_sso_config(
    sso_config: SSOConfigRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Configure SSO for the organization. Requires Admin role and Enterprise plan."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")

    org = db.query(models.Organization).filter(
        models.Organization.id == current_user.organization_id
    ).first()

    if org.plan != "enterprise":
        raise HTTPException(status_code=403, detail="SSO requires Enterprise plan")

    org.sso_provider = sso_config.provider
    org.sso_metadata_url = sso_config.metadata_url
    org.sso_entity_id = sso_config.entity_id
    if sso_config.sso_url:
        org.sso_acs_url = sso_config.sso_url
    org.sso_enabled = True

    db.commit()

    logger.info(f"SSO configured for org {org.id}: {sso_config.provider}")
    return {"message": "SSO configured successfully", "sso_enabled": True}


@router.delete("/config")
def disable_sso(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Disable SSO for the organization."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")

    org = db.query(models.Organization).filter(
        models.Organization.id == current_user.organization_id
    ).first()

    org.sso_enabled = False
    db.commit()

    return {"message": "SSO disabled", "sso_enabled": False}


# ---------- SSO Login flow ----------

@router.get("/login/{org_slug}")
def sso_login_redirect(org_slug: str, db: Session = Depends(get_db)):
    """Initiate SSO login — redirect user to IdP."""
    org = db.query(models.Organization).filter(
        models.Organization.name == org_slug
    ).first()

    if not org or not org.sso_enabled:
        raise HTTPException(status_code=404, detail="SSO not configured for this organization")

    # For SAML, we'd build and sign an AuthnRequest here.
    # For this implementation, we redirect to the IdP metadata URL with a SAMLRequest.
    # In production, use python3-saml or pysaml2.

    if org.sso_provider == "google":
        # Google Workspace SSO — redirect to Google's OAuth with hd param
        google_client_id = os.getenv("GOOGLE_SSO_CLIENT_ID", "")
        redirect_uri = f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/v1/sso/callback/google"
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={google_client_id}&response_type=code&scope=email%20profile"
            f"&redirect_uri={redirect_uri}&state={org.id}"
            f"&hd={org.sso_entity_id}"  # restrict to org domain
        )
        return RedirectResponse(url=auth_url)

    # Generic SAML redirect
    if org.sso_metadata_url:
        return RedirectResponse(url=org.sso_metadata_url)

    raise HTTPException(status_code=400, detail="SSO provider not fully configured")


@router.post("/acs")
async def saml_acs(request: Request, db: Session = Depends(get_db)):
    """SAML Assertion Consumer Service endpoint.

    In production, parse and validate the SAML response using python3-saml.
    For now, this is a stub that shows the integration pattern.
    """
    form = await request.form()
    saml_response = form.get("SAMLResponse")

    if not saml_response:
        raise HTTPException(status_code=400, detail="Missing SAMLResponse")

    # TODO: In production, decode and validate SAML response:
    # - Verify signature against IdP certificate
    # - Check audience restriction
    # - Extract NameID (email) and attributes
    #
    # For now, return an error indicating SAML parsing needs python3-saml
    raise HTTPException(
        status_code=501,
        detail="SAML response parsing requires python3-saml. Use Google SSO or contact support."
    )


@router.get("/callback/google")
def google_sso_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Handle Google SSO callback."""
    try:
        import requests as req_lib

        org_id = int(state)
        org = db.query(models.Organization).filter(
            models.Organization.id == org_id
        ).first()

        if not org or not org.sso_enabled:
            raise HTTPException(status_code=400, detail="Invalid SSO state")

        # Exchange code for tokens
        token_resp = req_lib.post("https://oauth2.googleapis.com/token", data={
            "code": code,
            "client_id": os.getenv("GOOGLE_SSO_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_SSO_CLIENT_SECRET"),
            "redirect_uri": f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/v1/sso/callback/google",
            "grant_type": "authorization_code",
        })

        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code")

        token_data = token_resp.json()

        # Get user info
        user_resp = req_lib.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )

        if user_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")

        user_info = user_resp.json()
        email = user_info.get("email")
        name = user_info.get("name", email)

        # Find or create user
        user = db.query(models.User).filter(
            models.User.email == email,
            models.User.organization_id == org_id,
        ).first()

        if not user:
            user = models.User(
                email=email,
                full_name=name,
                organization_id=org_id,
                role="MEMBER",
                auth_provider="google",
                hashed_password=None,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Issue JWT
        access_token = security.create_access_token(
            data={"sub": user.email, "org_id": user.organization_id},
            expires_delta=timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{FRONTEND_URL}/login?sso_token={access_token}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google SSO callback failed: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?sso_error=true")
