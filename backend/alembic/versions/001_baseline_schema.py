"""Baseline schema alignment for existing Marble AI DB.

Revision ID: 001_baseline
Revises:
Create Date: 2026-03-23

For databases already created via Base.metadata.create_all:
  alembic stamp head

For fresh databases:
  alembic upgrade head
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure inventory.restocked_at exists (used by analytics aging)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "inventory" in tables:
        cols = {c["name"] for c in inspector.get_columns("inventory")}
        if "restocked_at" not in cols:
            op.add_column(
                "inventory",
                sa.Column(
                    "restocked_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                    nullable=True,
                ),
            )

    if "quotations_history" not in tables:
        op.create_table(
            "quotations_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("client_name", sa.String(), nullable=False),
            sa.Column("company_name", sa.String(), nullable=False),
            sa.Column("total_amount", sa.Float(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    if "admins" not in tables:
        op.create_table(
            "admins",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_admins_email", "admins", ["email"], unique=True)


def downgrade() -> None:
    # Non-destructive baseline — do not drop production tables
    pass
