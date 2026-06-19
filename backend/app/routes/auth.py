
from datetime import datetime, timedelta
from typing import Any, Optional
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from ..database import get_db
from ..models import (
    User, Organization, Invitation,
    Decision, Outcome, Attribution, Integration, AuditLog, SyncLog, EmailLog,
)
from ..core import security, config
from ..middleware.auth import get_current_user
from ..services.email import send_password_reset, send_email_verification

logger = logging.getLogger("sparqai.auth")

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization_name: str = ""
    invite_token: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class VerifyEmailRequest(BaseModel):
    token: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str = None
    organization_id: int = None
    role: str = "MEMBER"
    email_verified: bool = False

    class Config:
        from_attributes = True

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    Create new user and organization, or join via invite token.
    First user in an org gets ADMIN role automatically.
    """
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )

    # --- Invite-based registration ---
    if user_in.invite_token:
        invitation = db.query(Invitation).filter(
            Invitation.token == user_in.invite_token
        ).first()

        if not invitation:
            raise HTTPException(status_code=400, detail="Invalid invitation token")
        if invitation.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invitation has expired")
        if invitation.email != user_in.email:
            raise HTTPException(
                status_code=400,
                detail="Email does not match the invitation",
            )

        user = User(
            email=user_in.email,
            hashed_password=security.get_password_hash(user_in.password),
            full_name=user_in.full_name,
            organization_id=invitation.organization_id,
            role=invitation.role,
            email_verified=False,
        )
        db.add(user)
        db.delete(invitation)  # consume the invite
        db.commit()
        db.refresh(user)

        # Send verification email
        _send_verification_email(db, user)

        return user

    # --- Normal registration: create org + user ---
    if not user_in.organization_name:
        raise HTTPException(
            status_code=400,
            detail="Organization name is required for new registrations",
        )

    org = Organization(name=user_in.organization_name)
    db.add(org)
    db.flush()

    # First user in the org is always ADMIN
    user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        organization_id=org.id,
        role="ADMIN",
        email_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Send verification email
    _send_verification_email(db, user)

    return user

@router.post("/login", response_model=Token)
def login_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email, "org_id": user.organization_id}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.post("/refresh", response_model=Token)
def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Issue a fresh access token for the currently authenticated user.
    Call this before the existing token expires to stay logged in.
    """
    access_token_expires = timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": current_user.email, "org_id": current_user.organization_id},
        expires_delta=access_token_expires,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Fetch the current logged in user.
    """
    return current_user


# ---------------------------------------------------------------------------
# Password Reset & Email Verification
# ---------------------------------------------------------------------------

def _create_purpose_token(email: str, purpose: str, expires_delta: timedelta) -> str:
    """Create a signed JWT with a specific purpose (reset / verify)."""
    return security.create_access_token(
        data={"sub": email, "purpose": purpose},
        expires_delta=expires_delta,
    )


def _decode_purpose_token(token: str, expected_purpose: str) -> str:
    """Decode and validate a purpose-scoped JWT. Returns the email on success."""
    try:
        payload = jwt.decode(
            token,
            config.settings.SECRET_KEY,
            algorithms=[config.settings.ALGORITHM],
        )
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    purpose = payload.get("purpose")
    email = payload.get("sub")

    if purpose != expected_purpose or not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    return email


def _send_verification_email(db: Session, user: User):
    """Generate a verification token and send the verification email."""
    try:
        token = _create_purpose_token(
            email=user.email,
            purpose="verify",
            expires_delta=timedelta(hours=24),
        )
        send_email_verification(db, user, token)
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {e}")


@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Initiate a password reset. Generates a signed JWT token and sends a
    reset email. Always returns 200 to avoid leaking whether the email exists.
    """
    user = db.query(User).filter(User.email == request.email).first()

    if user:
        token = _create_purpose_token(
            email=user.email,
            purpose="reset",
            expires_delta=timedelta(hours=1),
        )
        try:
            send_password_reset(db, user.email, token)
        except Exception as e:
            logger.error(f"Failed to send password reset email to {request.email}: {e}")

    # Always return success to prevent email enumeration
    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset a user's password using a signed JWT token from the reset email.
    Validates the token, hashes the new password, and updates the user record.
    """
    email = _decode_purpose_token(request.token, expected_purpose="reset")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user.hashed_password = security.get_password_hash(request.new_password)
    db.commit()

    return {"message": "Password has been reset successfully."}


@router.post("/verify-email")
def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    Verify a user's email address using a signed JWT token from the
    verification email sent at registration.
    """
    email = _decode_purpose_token(request.token, expected_purpose="verify")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    if user.email_verified:
        return {"message": "Email is already verified."}

    user.email_verified = True
    db.commit()

    return {"message": "Email verified successfully."}


@router.post("/resend-verification")
def resend_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Resend the email verification link. Requires authentication.
    """
    if current_user.email_verified:
        return {"message": "Email is already verified."}

    _send_verification_email(db, current_user)

    return {"message": "Verification email has been sent."}


# ---------------------------------------------------------------------------
# SSO — Google OAuth2 + SAML
# ---------------------------------------------------------------------------

class SSOLoginRequest(BaseModel):
    email: EmailStr

class SSOCallbackRequest(BaseModel):
    code: str
    provider: str = "google"  # google, saml

class GoogleLoginRequest(BaseModel):
    """Direct Google OAuth initiation (no email lookup needed)."""
    pass


@router.post("/sso/login")
def sso_login(request: SSOLoginRequest, db: Session = Depends(get_db)):
    """
    Initiate SSO login. Looks up the user's org to determine the SSO provider
    and returns the appropriate redirect URL.
    """
    from ..services.sso import get_sso_provider

    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if not org or not org.sso_enabled:
        raise HTTPException(status_code=400, detail="SSO not enabled for this organization")

    provider = get_sso_provider(org)
    if not provider:
        raise HTTPException(status_code=400, detail="SSO provider not configured")

    state = f"{uuid.uuid4()}:{org.id}"
    redirect_url = provider.get_authorization_url(state=state)

    return {
        "redirect_url": redirect_url,
        "provider": org.sso_provider,
        "message": "Redirecting to Identity Provider...",
    }


@router.post("/sso/google")
def sso_google_initiate(db: Session = Depends(get_db)):
    """
    Initiate Google OAuth2 login (for orgs with Google SSO or general Google sign-in).
    Returns the Google consent screen URL.
    """
    from ..services.sso import GoogleOAuthProvider
    import os

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    provider = GoogleOAuthProvider(redirect_uri=f"{frontend_url}/sso-callback")
    state = str(uuid.uuid4())

    return {
        "redirect_url": provider.get_authorization_url(state=state),
        "provider": "google",
    }


@router.post("/sso/callback", response_model=Token)
def sso_callback(request: SSOCallbackRequest, db: Session = Depends(get_db)):
    """
    Handle SSO callback — exchange the code for user info and issue a JWT.
    Supports Google OAuth2 and SAML responses.
    """
    import os
    from ..services.sso import GoogleOAuthProvider, SAMLProvider

    user_info = None

    if request.provider == "google":
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        google = GoogleOAuthProvider(redirect_uri=f"{frontend_url}/sso-callback")
        try:
            user_info = google.exchange_code(request.code)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Google SSO failed: {e}")

    elif request.provider == "saml":
        # SAML response is base64-encoded in the code field
        try:
            # Look up the org's SAML config from the state/RelayState
            # For now, validate the raw SAML response
            saml = SAMLProvider(metadata_url="", entity_id="", acs_url="")
            user_info = saml.validate_response(request.code)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"SAML validation failed: {e}")

    else:
        raise HTTPException(status_code=400, detail=f"Unknown SSO provider: {request.provider}")

    if not user_info or not user_info.get("email"):
        raise HTTPException(status_code=400, detail="Could not extract email from SSO response")

    email = user_info["email"]

    # Find or create user
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Auto-provision: create org + user for new Google SSO users
        if request.provider == "google":
            org_name = f"{user_info.get('family_name', email.split('@')[0])}'s Organization"
            org = Organization(name=org_name, sso_enabled=True, sso_provider="google")
            db.add(org)
            db.flush()

            user = User(
                email=email,
                full_name=user_info.get("full_name", ""),
                organization_id=org.id,
                role="ADMIN",
                auth_provider="google",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            raise HTTPException(
                status_code=404,
                detail="User not found. Contact your administrator to be added.",
            )

    # Issue JWT
    access_token_expires = timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email, "org_id": user.organization_id},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# ---------------------------------------------------------------------------
# GDPR -- Data export & account deletion
# ---------------------------------------------------------------------------

@router.get("/export-data")
def export_user_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GDPR data export: returns all personal data for the current user as JSON.
    Includes user profile, organization name, decisions, outcomes, and audit log entries.
    """
    from fastapi.encoders import jsonable_encoder

    org = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()

    decisions = db.query(Decision).filter(
        Decision.organization_id == current_user.organization_id
    ).all()

    outcomes = db.query(Outcome).filter(
        Outcome.organization_id == current_user.organization_id
    ).all()

    audit_entries = db.query(AuditLog).filter(
        AuditLog.user_id == current_user.id
    ).order_by(AuditLog.timestamp.desc()).all()

    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "created_at": jsonable_encoder(current_user.created_at),
        },
        "organization": {
            "id": org.id,
            "name": org.name,
        } if org else None,
        "decisions": jsonable_encoder([
            {
                "id": d.id,
                "description": d.description,
                "decision_type": d.decision_type,
                "start_date": d.start_date,
                "end_date": d.end_date,
                "cost": d.cost,
                "status": d.status,
                "source": d.source,
            }
            for d in decisions
        ]),
        "outcomes": jsonable_encoder([
            {
                "id": o.id,
                "metric_name": o.metric_name,
                "value": o.value,
                "date": o.date,
                "description": o.description,
                "decision_id": o.decision_id,
                "source": o.source,
            }
            for o in outcomes
        ]),
        "audit_log": jsonable_encoder([
            {
                "id": a.id,
                "action": a.action,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "details": a.details,
                "timestamp": a.timestamp,
            }
            for a in audit_entries
        ]),
    }


@router.delete("/account")
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete the current user's account (GDPR right-to-erasure).

    - If the user is the last ADMIN in their organization the entire org and
      all its data (decisions, outcomes, attributions, integrations, audit logs,
      sync logs, email logs, invitations) are deleted.
    - Otherwise only the user record and their personal audit log entries
      are removed.
    """
    org_id = current_user.organization_id

    # Count admins in the organization
    admin_count = db.query(User).filter(
        User.organization_id == org_id,
        User.role == "ADMIN",
    ).count()

    is_last_admin = (current_user.role == "ADMIN" and admin_count <= 1)

    if is_last_admin:
        # Full organization teardown -----------------------------------------
        logger.info(
            "Last admin %s deleting org %s -- cascading full deletion",
            current_user.email, org_id,
        )

        # Get all decision ids for this org (needed for attribution cleanup)
        decision_ids = [
            d.id for d in
            db.query(Decision.id).filter(Decision.organization_id == org_id).all()
        ]

        # Get all user ids for this org (needed for audit/email log cleanup)
        user_ids = [
            u.id for u in
            db.query(User.id).filter(User.organization_id == org_id).all()
        ]

        # Delete attributions linked to org decisions
        if decision_ids:
            db.query(Attribution).filter(
                Attribution.decision_id.in_(decision_ids)
            ).delete(synchronize_session=False)

        # Delete outcomes, decisions
        db.query(Outcome).filter(Outcome.organization_id == org_id).delete(
            synchronize_session=False,
        )
        db.query(Decision).filter(Decision.organization_id == org_id).delete(
            synchronize_session=False,
        )

        # Delete integrations, sync logs
        db.query(Integration).filter(
            Integration.organization_id == org_id
        ).delete(synchronize_session=False)
        db.query(SyncLog).filter(
            SyncLog.organization_id == org_id
        ).delete(synchronize_session=False)

        # Delete audit logs and email logs for all org users
        if user_ids:
            db.query(AuditLog).filter(
                AuditLog.user_id.in_(user_ids)
            ).delete(synchronize_session=False)
            db.query(EmailLog).filter(
                EmailLog.user_id.in_(user_ids)
            ).delete(synchronize_session=False)

        # Delete invitations for this org
        db.query(Invitation).filter(
            Invitation.organization_id == org_id
        ).delete(synchronize_session=False)

        # Delete all users in the org
        db.query(User).filter(
            User.organization_id == org_id
        ).delete(synchronize_session=False)

        # Delete the organization itself
        db.query(Organization).filter(
            Organization.id == org_id
        ).delete(synchronize_session=False)

        db.commit()

        return {
            "message": "Account and organization deleted successfully.",
            "org_deleted": True,
        }

    else:
        # Single user removal ------------------------------------------------
        logger.info("User %s deleting own account (non-last-admin)", current_user.email)

        # Remove personal audit logs and email logs
        db.query(AuditLog).filter(
            AuditLog.user_id == current_user.id
        ).delete(synchronize_session=False)
        db.query(EmailLog).filter(
            EmailLog.user_id == current_user.id
        ).delete(synchronize_session=False)

        db.delete(current_user)
        db.commit()

        return {
            "message": "Account deleted successfully.",
            "org_deleted": False,
        }
