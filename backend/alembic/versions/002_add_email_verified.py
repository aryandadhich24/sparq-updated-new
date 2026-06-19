"""Add email_verified column to users table

Revision ID: 002_add_email_verified
Revises: 001_initial_schema
Create Date: 2026-03-27

Adds a boolean email_verified column (default False) to support
the email verification flow on registration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_add_email_verified"
down_revision: Union[str, Sequence[str]] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean, server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "email_verified")
