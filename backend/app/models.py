from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    settings = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    # Billing
    stripe_customer_id = Column(String, nullable=True, unique=True, index=True)
    stripe_subscription_id = Column(String, nullable=True)
    plan = Column(String, default="free")  # free, starter, growth, enterprise
    plan_status = Column(String, default="active")  # active, past_due, canceled
    plan_expires_at = Column(DateTime, nullable=True)

    # SSO
    sso_enabled = Column(Boolean, default=False)
    sso_provider = Column(String, nullable=True)  # okta, azure_ad, google
    sso_metadata_url = Column(Text, nullable=True)
    sso_entity_id = Column(String, nullable=True)
    sso_acs_url = Column(String, nullable=True)

    users = relationship("User", back_populates="organization")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # nullable for SSO-only users
    full_name = Column(String, nullable=True)
    is_active = Column(Integer, default=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    role = Column(String, default="MEMBER")  # ADMIN, MEMBER, VIEWER
    auth_provider = Column(String, default="local")  # local, saml, google
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Email notification preferences
    email_weekly_digest = Column(Boolean, default=True)
    email_action_alerts = Column(Boolean, default=True)
    email_sync_summaries = Column(Boolean, default=False)

    organization = relationship("Organization", back_populates="users")


class Invitation(Base):
    __tablename__ = "invitations"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    token = Column(String, unique=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    role = Column(String, default="MEMBER")
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class Decision(Base):
    __tablename__ = "decisions"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String)
    decision_type = Column(String, index=True)  # HIRE, AD_CAMPAIGN, TOOL, VENDOR
    status = Column(String, default="ACTIVE", index=True)  # ACTIVE, ENDED
    start_date = Column(Date, index=True)
    end_date = Column(Date, nullable=True)
    cost = Column(Float)  # Monthly for HIRE/TOOL, total for AD_CAMPAIGN/VENDOR
    currency = Column(String, default="USD")
    source = Column(String, default="MANUAL")  # MANUAL, HUBSPOT, QUICKBOOKS
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    meta_data = Column(JSON, nullable=True)

    outcomes = relationship("Outcome", back_populates="decision")


class Outcome(Base):
    __tablename__ = "outcomes"
    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(Integer, ForeignKey("decisions.id"), nullable=True, index=True)
    metric_name = Column(String)  # REVENUE, PIPELINE_VALUE, LEADS
    value = Column(Float)
    date = Column(Date, index=True)
    description = Column(String, nullable=True)
    source = Column(String, nullable=True)  # HUBSPOT, MANUAL
    source_id = Column(String, nullable=True, unique=True, index=True)  # External ID for dedup
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)

    decision = relationship("Decision", back_populates="outcomes")


class Attribution(Base):
    __tablename__ = "attributions"
    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(Integer, ForeignKey("decisions.id"), index=True)
    outcome_id = Column(Integer, ForeignKey("outcomes.id"), nullable=True, index=True)
    weight = Column(Float)
    roi_multiple = Column(Float)
    attributed_value = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    confidence_score = Column(Float)
    recommendation = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Integration(Base):
    __tablename__ = "integrations"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    provider = Column(String, index=True)  # HUBSPOT, SALESFORCE, GOOGLE_ADS, META_ADS, LINKEDIN_ADS, QUICKBOOKS
    access_token = Column(String)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    portal_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    config = Column(JSON, nullable=True, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    action = Column(String, index=True)
    resource_type = Column(String, index=True)
    resource_id = Column(String)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User")


class SyncLog(Base):
    """Tracks integration sync history."""
    __tablename__ = "sync_logs"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    provider = Column(String, index=True)
    status = Column(String, default="running")  # running, success, failed
    created = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class EmailLog(Base):
    """Tracks sent emails."""
    __tablename__ = "email_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    email_type = Column(String, index=True)  # weekly_digest, action_alert, sync_summary
    subject = Column(String)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="sent")  # sent, failed, bounced
