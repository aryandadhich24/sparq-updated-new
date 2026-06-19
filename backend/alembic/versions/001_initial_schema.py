"""Comprehensive initial schema - all 10 models

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-03-27

Consolidates the full schema from models.py, replacing the previous
partial migration (e71fb0fe2eb2) and the standalone migrate_audit.py,
migrate_rbac.py, and migrate_settings.py scripts.

Tables: organizations, users, invitations, decisions, outcomes,
        attributions, integrations, audit_logs, sync_logs, email_logs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. organizations
    # ------------------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, unique=True, nullable=False),
        sa.Column("settings", sa.JSON, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        # Billing
        sa.Column("stripe_customer_id", sa.String, nullable=True, unique=True),
        sa.Column("stripe_subscription_id", sa.String, nullable=True),
        sa.Column("plan", sa.String, server_default="free"),
        sa.Column("plan_status", sa.String, server_default="active"),
        sa.Column("plan_expires_at", sa.DateTime, nullable=True),
        # SSO
        sa.Column("sso_enabled", sa.Boolean, server_default=sa.text("false")),
        sa.Column("sso_provider", sa.String, nullable=True),
        sa.Column("sso_metadata_url", sa.Text, nullable=True),
        sa.Column("sso_entity_id", sa.String, nullable=True),
        sa.Column("sso_acs_url", sa.String, nullable=True),
    )
    op.create_index("ix_organizations_id", "organizations", ["id"])
    op.create_index("ix_organizations_name", "organizations", ["name"], unique=True)
    op.create_index(
        "ix_organizations_stripe_customer_id",
        "organizations",
        ["stripe_customer_id"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # 2. users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String, unique=True, nullable=False),
        sa.Column("hashed_password", sa.String, nullable=True),
        sa.Column("full_name", sa.String, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column(
            "organization_id",
            sa.Integer,
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("role", sa.String, server_default="MEMBER"),
        sa.Column("auth_provider", sa.String, server_default="local"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        # Email notification preferences
        sa.Column("email_weekly_digest", sa.Boolean, server_default=sa.text("true")),
        sa.Column("email_action_alerts", sa.Boolean, server_default=sa.text("true")),
        sa.Column("email_sync_summaries", sa.Boolean, server_default=sa.text("false")),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    # ------------------------------------------------------------------
    # 3. invitations
    # ------------------------------------------------------------------
    op.create_table(
        "invitations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String),
        sa.Column("token", sa.String, unique=True),
        sa.Column(
            "organization_id",
            sa.Integer,
            sa.ForeignKey("organizations.id"),
        ),
        sa.Column("role", sa.String, server_default="MEMBER"),
        sa.Column("expires_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_invitations_id", "invitations", ["id"])
    op.create_index("ix_invitations_email", "invitations", ["email"])
    op.create_index("ix_invitations_token", "invitations", ["token"], unique=True)

    # ------------------------------------------------------------------
    # 4. decisions
    # ------------------------------------------------------------------
    op.create_table(
        "decisions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("description", sa.String),
        sa.Column("decision_type", sa.String),
        sa.Column("status", sa.String, server_default="ACTIVE"),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("cost", sa.Float),
        sa.Column("currency", sa.String, server_default="USD"),
        sa.Column("source", sa.String, server_default="MANUAL"),
        sa.Column(
            "organization_id",
            sa.Integer,
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("meta_data", sa.JSON, nullable=True),
    )
    op.create_index("ix_decisions_id", "decisions", ["id"])
    op.create_index("ix_decisions_decision_type", "decisions", ["decision_type"])
    op.create_index("ix_decisions_status", "decisions", ["status"])
    op.create_index("ix_decisions_start_date", "decisions", ["start_date"])
    op.create_index("ix_decisions_organization_id", "decisions", ["organization_id"])

    # ------------------------------------------------------------------
    # 5. outcomes
    # ------------------------------------------------------------------
    op.create_table(
        "outcomes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "decision_id",
            sa.Integer,
            sa.ForeignKey("decisions.id"),
            nullable=True,
        ),
        sa.Column("metric_name", sa.String),
        sa.Column("value", sa.Float),
        sa.Column("date", sa.Date),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("source", sa.String, nullable=True),
        sa.Column("source_id", sa.String, nullable=True, unique=True),
        sa.Column(
            "organization_id",
            sa.Integer,
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_outcomes_id", "outcomes", ["id"])
    op.create_index("ix_outcomes_decision_id", "outcomes", ["decision_id"])
    op.create_index("ix_outcomes_date", "outcomes", ["date"])
    op.create_index("ix_outcomes_source_id", "outcomes", ["source_id"], unique=True)
    op.create_index("ix_outcomes_organization_id", "outcomes", ["organization_id"])

    # ------------------------------------------------------------------
    # 6. attributions
    # ------------------------------------------------------------------
    op.create_table(
        "attributions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "decision_id",
            sa.Integer,
            sa.ForeignKey("decisions.id"),
        ),
        sa.Column(
            "outcome_id",
            sa.Integer,
            sa.ForeignKey("outcomes.id"),
            nullable=True,
        ),
        sa.Column("weight", sa.Float),
        sa.Column("roi_multiple", sa.Float),
        sa.Column("attributed_value", sa.Float, server_default="0.0"),
        sa.Column("total_cost", sa.Float, server_default="0.0"),
        sa.Column("confidence_score", sa.Float),
        sa.Column("recommendation", sa.String),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_attributions_id", "attributions", ["id"])
    op.create_index("ix_attributions_decision_id", "attributions", ["decision_id"])
    op.create_index("ix_attributions_outcome_id", "attributions", ["outcome_id"])

    # ------------------------------------------------------------------
    # 7. integrations
    # ------------------------------------------------------------------
    op.create_table(
        "integrations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer,
            sa.ForeignKey("organizations.id"),
        ),
        sa.Column("provider", sa.String),
        sa.Column("access_token", sa.String),
        sa.Column("refresh_token", sa.String, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("portal_id", sa.String, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("config", sa.JSON, nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_integrations_id", "integrations", ["id"])
    op.create_index(
        "ix_integrations_organization_id", "integrations", ["organization_id"]
    )
    op.create_index("ix_integrations_provider", "integrations", ["provider"])

    # ------------------------------------------------------------------
    # 8. audit_logs
    # ------------------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id"),
        ),
        sa.Column("action", sa.String),
        sa.Column("resource_type", sa.String),
        sa.Column("resource_id", sa.String),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("timestamp", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])

    # ------------------------------------------------------------------
    # 9. sync_logs
    # ------------------------------------------------------------------
    op.create_table(
        "sync_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer,
            sa.ForeignKey("organizations.id"),
        ),
        sa.Column("provider", sa.String),
        sa.Column("status", sa.String, server_default="running"),
        sa.Column("created", sa.Integer, server_default="0"),
        sa.Column("skipped", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_sync_logs_id", "sync_logs", ["id"])
    op.create_index("ix_sync_logs_organization_id", "sync_logs", ["organization_id"])
    op.create_index("ix_sync_logs_provider", "sync_logs", ["provider"])

    # ------------------------------------------------------------------
    # 10. email_logs
    # ------------------------------------------------------------------
    op.create_table(
        "email_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id"),
        ),
        sa.Column("email_type", sa.String),
        sa.Column("subject", sa.String),
        sa.Column("sent_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("status", sa.String, server_default="sent"),
    )
    op.create_index("ix_email_logs_id", "email_logs", ["id"])
    op.create_index("ix_email_logs_user_id", "email_logs", ["user_id"])
    op.create_index("ix_email_logs_email_type", "email_logs", ["email_type"])


def downgrade() -> None:
    op.drop_table("email_logs")
    op.drop_table("sync_logs")
    op.drop_table("audit_logs")
    op.drop_table("integrations")
    op.drop_table("attributions")
    op.drop_table("outcomes")
    op.drop_table("decisions")
    op.drop_table("invitations")
    op.drop_table("users")
    op.drop_table("organizations")
