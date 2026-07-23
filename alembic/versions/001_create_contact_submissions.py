"""create contact_submissions

Revision ID: 001_contact_submissions
Revises:
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_contact_submissions"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contact_submissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("email_sent", sa.Boolean(), nullable=False),
        sa.Column("ai_available", sa.Boolean(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("sentiment", sa.String(length=32), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("suggested_reply", sa.Text(), nullable=True),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("contact_submissions")
