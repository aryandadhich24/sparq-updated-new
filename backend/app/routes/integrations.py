
import os
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..middleware.auth import get_current_user
from ..core.crypto import encrypt, decrypt
from ..core.security import create_access_token
from ..core.config import settings

logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

router = APIRouter()


# ---------------------------------------------------------------------------
# OAuth CSRF state helpers (signed JWT)
# ---------------------------------------------------------------------------

def _create_oauth_state(user: models.User, provider: str) -> str:
    """Create a signed JWT to use as the OAuth ``state`` parameter.

    Contains org_id, user_id, and provider so the callback can verify that
    the request originated from a legitimate authorize flow.  Expires in
    10 minutes.
    """
    return create_access_token(
        data={
            "org_id": user.organization_id,
            "user_id": user.id,
            "provider": provider,
            "purpose": "oauth_state",
        },
        expires_delta=timedelta(minutes=10),
    )


def _validate_oauth_state(state: str | None, expected_provider: str) -> dict:
    """Decode and validate an OAuth state JWT.

    Returns the decoded payload on success.  Raises HTTPException(400) if
    the state is missing, expired, or does not match the expected provider.
    """
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state parameter")
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    if payload.get("purpose") != "oauth_state":
        raise HTTPException(status_code=400, detail="Invalid OAuth state token purpose")

    if payload.get("provider") != expected_provider:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth state provider mismatch: expected {expected_provider}",
        )

    return payload

HUBSPOT_CLIENT_ID = os.getenv("HUBSPOT_CLIENT_ID", "")
HUBSPOT_CLIENT_SECRET = os.getenv("HUBSPOT_CLIENT_SECRET", "")
HUBSPOT_REDIRECT_URI = os.getenv(
    "HUBSPOT_REDIRECT_URI",
    "http://localhost:8000/api/v1/integrations/hubspot/callback",
)
HUBSPOT_SCOPES = "crm.objects.deals.read"

SALESFORCE_CLIENT_ID = os.getenv("SALESFORCE_CLIENT_ID", "")
SALESFORCE_CLIENT_SECRET = os.getenv("SALESFORCE_CLIENT_SECRET", "")
SALESFORCE_REDIRECT_URI = os.getenv(
    "SALESFORCE_REDIRECT_URI",
    "http://localhost:8000/api/v1/integrations/salesforce/callback",
)

# Ad platform credentials
GOOGLE_ADS_CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
GOOGLE_ADS_CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
META_ADS_APP_ID = os.getenv("META_ADS_APP_ID", "")
META_ADS_APP_SECRET = os.getenv("META_ADS_APP_SECRET", "")
LINKEDIN_ADS_CLIENT_ID = os.getenv("LINKEDIN_ADS_CLIENT_ID", "")
LINKEDIN_ADS_CLIENT_SECRET = os.getenv("LINKEDIN_ADS_CLIENT_SECRET", "")

# All known providers
ALL_PROVIDERS = [
    "HUBSPOT", "SALESFORCE",
    "GOOGLE_ADS", "META_ADS", "LINKEDIN_ADS",
    "QUICKBOOKS",
]


def _is_mock(client_id: str) -> bool:
    """True when no real OAuth credentials are configured."""
    return not client_id or client_id.startswith("mock")


def _get_integration(db: Session, org_id: int, provider: str):
    return db.query(models.Integration).filter(
        models.Integration.organization_id == org_id,
        models.Integration.provider == provider,
    ).first()


def _upsert_integration(db: Session, org_id: int, provider: str, **kwargs):
    integration = _get_integration(db, org_id, provider)
    if not integration:
        integration = models.Integration(
            organization_id=org_id,
            provider=provider,
        )
        db.add(integration)
    for k, v in kwargs.items():
        setattr(integration, k, v)
    integration.is_active = True
    integration.updated_at = datetime.utcnow()
    db.commit()
    return integration


# ---------------------------------------------------------------------------
# Disconnect (works for ALL providers)
# ---------------------------------------------------------------------------

@router.delete("/{provider}/disconnect")
def disconnect_integration(
    provider: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Disconnect an integration by deleting its record."""
    provider_upper = provider.upper().replace("-", "_")
    integration = _get_integration(db, current_user.organization_id, provider_upper)
    if not integration:
        raise HTTPException(status_code=404, detail=f"{provider} is not connected")
    db.delete(integration)
    db.commit()
    return {"message": f"{provider} disconnected successfully"}


# ---------------------------------------------------------------------------
# Unified Status (ALL providers)
# ---------------------------------------------------------------------------

@router.get("/status")
def get_integrations_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return connection status for every known provider."""
    integrations = db.query(models.Integration).filter(
        models.Integration.organization_id == current_user.organization_id,
    ).all()

    int_map = {i.provider: i for i in integrations}

    result = {}
    for provider in ALL_PROVIDERS:
        i = int_map.get(provider)
        result[provider.lower()] = {
            "connected": i is not None and i.is_active,
            "last_sync": i.updated_at.isoformat() if i and i.updated_at else None,
            "expires_at": i.expires_at.isoformat() if i and i.expires_at else None,
        }

    return result


# ---------------------------------------------------------------------------
# HubSpot
# ---------------------------------------------------------------------------

@router.get("/hubspot/authorize")
def authorize_hubspot(user: models.User = Depends(get_current_user)):
    state = _create_oauth_state(user, "hubspot")
    if _is_mock(HUBSPOT_CLIENT_ID):
        return {
            "url": f"{FRONTEND_URL}/integrations/callback?code=mock_hubspot_code&provider=hubspot&state={state}"
        }
    auth_url = (
        f"https://app.hubspot.com/oauth/authorize"
        f"?client_id={HUBSPOT_CLIENT_ID}"
        f"&redirect_uri={HUBSPOT_REDIRECT_URI}"
        f"&scope={HUBSPOT_SCOPES}"
        f"&state={state}"
    )
    return {"url": auth_url}


@router.get("/hubspot/callback")
def hubspot_callback(code: str, state: str = ""):
    return RedirectResponse(
        f"{FRONTEND_URL}/integrations/callback?code={code}&provider=hubspot&state={state}"
    )


@router.post("/hubspot/exchange")
def exchange_hubspot_token(
    code: str,
    state: str = "",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _validate_oauth_state(state, "hubspot")
    if _is_mock(HUBSPOT_CLIENT_ID):
        access_token = f"mock_hs_token_{code}"
        refresh_token = f"mock_hs_refresh_{code}"
        expires_in = 21600
    else:
        import requests as req
        resp = req.post(
            "https://api.hubapi.com/oauth/v1/token",
            data={
                "grant_type": "authorization_code",
                "client_id": HUBSPOT_CLIENT_ID,
                "client_secret": HUBSPOT_CLIENT_SECRET,
                "redirect_uri": HUBSPOT_REDIRECT_URI,
                "code": code,
            },
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"HubSpot auth failed: {resp.text}")
        token_data = resp.json()
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        expires_in = token_data["expires_in"]

    _upsert_integration(
        db, current_user.organization_id, "HUBSPOT",
        access_token=encrypt(access_token),
        refresh_token=encrypt(refresh_token),
        expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
    )
    return {"message": "HubSpot connected successfully"}


# ---------------------------------------------------------------------------
# Salesforce
# ---------------------------------------------------------------------------

@router.get("/salesforce/authorize")
def authorize_salesforce(user: models.User = Depends(get_current_user)):
    state = _create_oauth_state(user, "salesforce")
    if _is_mock(SALESFORCE_CLIENT_ID):
        return {
            "url": f"{FRONTEND_URL}/integrations/callback?code=mock_sf_code&provider=salesforce&state={state}"
        }
    auth_url = (
        f"https://login.salesforce.com/services/oauth2/authorize"
        f"?response_type=code&client_id={SALESFORCE_CLIENT_ID}"
        f"&redirect_uri={SALESFORCE_REDIRECT_URI}"
        f"&state={state}"
    )
    return {"url": auth_url}


@router.get("/salesforce/callback")
def salesforce_callback(code: str, state: str = ""):
    return RedirectResponse(
        f"{FRONTEND_URL}/integrations/callback?code={code}&provider=salesforce&state={state}"
    )


@router.post("/salesforce/exchange")
def exchange_salesforce_token(
    code: str,
    state: str = "",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _validate_oauth_state(state, "salesforce")
    if _is_mock(SALESFORCE_CLIENT_ID):
        access_token = f"mock_sf_token_{code}"
        refresh_token = f"mock_sf_refresh_{code}"
        instance_url = "https://mock.salesforce.com"
    else:
        import requests as req
        resp = req.post(
            "https://login.salesforce.com/services/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": SALESFORCE_CLIENT_ID,
                "client_secret": SALESFORCE_CLIENT_SECRET,
                "redirect_uri": SALESFORCE_REDIRECT_URI,
                "code": code,
            },
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Salesforce auth failed: {resp.text}")
        token_data = resp.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        instance_url = token_data["instance_url"]

    _upsert_integration(
        db, current_user.organization_id, "SALESFORCE",
        access_token=encrypt(access_token),
        refresh_token=encrypt(refresh_token) if refresh_token else None,
        portal_id=instance_url,
    )
    return {"message": "Salesforce connected successfully"}


# ---------------------------------------------------------------------------
# Google Ads
# ---------------------------------------------------------------------------

@router.get("/google-ads/authorize")
def authorize_google_ads(user: models.User = Depends(get_current_user)):
    state = _create_oauth_state(user, "google_ads")
    if _is_mock(GOOGLE_ADS_CLIENT_ID):
        return {
            "url": f"{FRONTEND_URL}/integrations/callback?code=mock_gads_code&provider=google_ads&state={state}"
        }
    redirect_uri = os.getenv("GOOGLE_ADS_REDIRECT_URI",
        f"{FRONTEND_URL}/integrations/callback?provider=google_ads")
    scopes = "https://www.googleapis.com/auth/adwords"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_ADS_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"scope={scopes}&"
        f"response_type=code&"
        f"access_type=offline&"
        f"prompt=consent&"
        f"state={state}"
    )
    return {"url": auth_url}


@router.post("/google-ads/exchange")
def exchange_google_ads_token(
    code: str,
    state: str = "",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _validate_oauth_state(state, "google_ads")
    if _is_mock(GOOGLE_ADS_CLIENT_ID):
        access_token = f"mock_gads_token_{code}"
        refresh_token = f"mock_gads_refresh_{code}"
        expires_in = 3600
    else:
        import requests as req
        redirect_uri = os.getenv("GOOGLE_ADS_REDIRECT_URI",
            f"{FRONTEND_URL}/integrations/callback?provider=google_ads")
        resp = req.post("https://oauth2.googleapis.com/token", data={
            "grant_type": "authorization_code",
            "client_id": GOOGLE_ADS_CLIENT_ID,
            "client_secret": GOOGLE_ADS_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "code": code,
        })
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Google Ads auth failed: {resp.text}")
        token_data = resp.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token", "")
        expires_in = token_data.get("expires_in", 3600)

    _upsert_integration(
        db, current_user.organization_id, "GOOGLE_ADS",
        access_token=encrypt(access_token),
        refresh_token=encrypt(refresh_token),
        expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
    )
    return {"message": "Google Ads connected successfully"}


# ---------------------------------------------------------------------------
# Meta Ads (Facebook / Instagram)
# ---------------------------------------------------------------------------

@router.get("/meta-ads/authorize")
def authorize_meta_ads(user: models.User = Depends(get_current_user)):
    state = _create_oauth_state(user, "meta_ads")
    if _is_mock(META_ADS_APP_ID):
        return {
            "url": f"{FRONTEND_URL}/integrations/callback?code=mock_meta_code&provider=meta_ads&state={state}"
        }
    redirect_uri = os.getenv("META_ADS_REDIRECT_URI",
        f"{FRONTEND_URL}/integrations/callback?provider=meta_ads")
    scopes = "ads_read,ads_management,read_insights"
    auth_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth?"
        f"client_id={META_ADS_APP_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"scope={scopes}&"
        f"response_type=code&"
        f"state={state}"
    )
    return {"url": auth_url}


@router.post("/meta-ads/exchange")
def exchange_meta_ads_token(
    code: str,
    state: str = "",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _validate_oauth_state(state, "meta_ads")
    if _is_mock(META_ADS_APP_ID):
        access_token = f"mock_meta_token_{code}"
        expires_in = 5184000  # 60 days
    else:
        import requests as req
        redirect_uri = os.getenv("META_ADS_REDIRECT_URI",
            f"{FRONTEND_URL}/integrations/callback?provider=meta_ads")
        # Exchange for short-lived token
        resp = req.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
            "client_id": META_ADS_APP_ID,
            "client_secret": META_ADS_APP_SECRET,
            "redirect_uri": redirect_uri,
            "code": code,
        })
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Meta auth failed: {resp.text}")
        short_token = resp.json()["access_token"]

        # Exchange for long-lived token
        resp2 = req.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": META_ADS_APP_ID,
            "client_secret": META_ADS_APP_SECRET,
            "fb_exchange_token": short_token,
        })
        if resp2.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Meta token exchange failed: {resp2.text}")
        token_data = resp2.json()
        access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 5184000)

    _upsert_integration(
        db, current_user.organization_id, "META_ADS",
        access_token=encrypt(access_token),
        expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
    )
    return {"message": "Meta Ads connected successfully"}


# ---------------------------------------------------------------------------
# LinkedIn Ads
# ---------------------------------------------------------------------------

@router.get("/linkedin-ads/authorize")
def authorize_linkedin_ads(user: models.User = Depends(get_current_user)):
    state = _create_oauth_state(user, "linkedin_ads")
    if _is_mock(LINKEDIN_ADS_CLIENT_ID):
        return {
            "url": f"{FRONTEND_URL}/integrations/callback?code=mock_li_code&provider=linkedin_ads&state={state}"
        }
    redirect_uri = os.getenv("LINKEDIN_ADS_REDIRECT_URI",
        f"{FRONTEND_URL}/integrations/callback?provider=linkedin_ads")
    scopes = "r_ads,r_ads_reporting,r_organization_social"
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code&"
        f"client_id={LINKEDIN_ADS_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"scope={scopes}&"
        f"state={state}"
    )
    return {"url": auth_url}


@router.post("/linkedin-ads/exchange")
def exchange_linkedin_ads_token(
    code: str,
    state: str = "",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _validate_oauth_state(state, "linkedin_ads")
    if _is_mock(LINKEDIN_ADS_CLIENT_ID):
        access_token = f"mock_li_token_{code}"
        refresh_token = f"mock_li_refresh_{code}"
        expires_in = 5184000
    else:
        import requests as req
        redirect_uri = os.getenv("LINKEDIN_ADS_REDIRECT_URI",
            f"{FRONTEND_URL}/integrations/callback?provider=linkedin_ads")
        resp = req.post("https://www.linkedin.com/oauth/v2/accessToken", data={
            "grant_type": "authorization_code",
            "client_id": LINKEDIN_ADS_CLIENT_ID,
            "client_secret": LINKEDIN_ADS_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "code": code,
        })
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"LinkedIn auth failed: {resp.text}")
        token_data = resp.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token", "")
        expires_in = token_data.get("expires_in", 5184000)

    _upsert_integration(
        db, current_user.organization_id, "LINKEDIN_ADS",
        access_token=encrypt(access_token),
        refresh_token=encrypt(refresh_token) if refresh_token else None,
        expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
    )
    return {"message": "LinkedIn Ads connected successfully"}

# ---------------------------------------------------------------------------
# PRIVATE APP TOKEN FLOW — paste-your-own-credentials, no OAuth app required
# Append this entire block to the END of backend/app/routes/integrations.py
# Uses the existing _upsert_integration / _get_integration helpers already
# defined above in this file — does not duplicate or replace any OAuth code.
# ---------------------------------------------------------------------------

from pydantic import BaseModel
from typing import Optional as _Optional


class HubSpotTokenPayload(BaseModel):
    access_token: str


class SalesforceCredPayload(BaseModel):
    username: str
    password: str
    security_token: str
    domain: _Optional[str] = "login"


@router.post("/hubspot/token")
def save_hubspot_token(
    payload: HubSpotTokenPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Save a HubSpot Private App access token (paste-flow).
    Validates the token against HubSpot before storing it encrypted.
    Stored in the same `access_token` field the OAuth flow uses, so
    /hubspot/ingest in main.py picks it up with zero changes needed.
    """
    token = payload.access_token.strip()

    if not token:
        raise HTTPException(status_code=400, detail="Access token is required.")

    if not token.startswith("pat-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid token format. HubSpot Private App tokens start with 'pat-'."
        )

    try:
        from hubspot import HubSpot
        client = HubSpot(access_token=token)
        client.crm.deals.basic_api.get_page(limit=1)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not connect to HubSpot with this token. Check the token and "
                   f"required scope (crm.objects.deals.read). Error: {e}"
        )

    _upsert_integration(
        db, current_user.organization_id, "HUBSPOT",
        access_token=encrypt(token),
    )
    return {"message": "HubSpot connected successfully"}


@router.post("/salesforce/token")
def save_salesforce_token(
    payload: SalesforceCredPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Save Salesforce username + password + security_token (paste-flow).
    Validates against Salesforce before storing.

    Stored in the integration's `config` JSON field (NOT access_token) so it
    never collides with the OAuth access_token/portal_id fields used by the
    existing /salesforce/exchange flow. ingest_salesforce in main.py is
    updated separately to check `config` first, then fall back to OAuth
    access_token, then env vars — see the main.py patch instructions.
    """
    if not payload.username or not payload.password or not payload.security_token:
        raise HTTPException(
            status_code=400,
            detail="Username, password, and security token are all required."
        )

    try:
        from simple_salesforce import Salesforce
        Salesforce(
            username=payload.username,
            password=payload.password,
            security_token=payload.security_token,
            domain=payload.domain or "login",
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not connect to Salesforce. Check your credentials. Error: {e}"
        )

    _upsert_integration(
        db, current_user.organization_id, "SALESFORCE",
        config={
            "auth_method": "password",
            "username": payload.username,
            "password": encrypt(payload.password),
            "security_token": encrypt(payload.security_token),
            "domain": payload.domain or "login",
        },
    )
    return {"message": "Salesforce connected successfully"}
