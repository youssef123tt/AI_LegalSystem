"""create documents and ingest_jobs tables

Revision ID: 0001
Revises: (none — this is the first migration)
Create Date: 2026-04-03

WHAT THIS MIGRATION DOES
-------------------------
Creates the two core tables for Milestone 2:

1. documents    — stores metadata about each uploaded legal document.
2. ingest_jobs  — tracks the background processing job for each document.

HOW TO READ THIS FILE
---------------------
- upgrade()   : the changes to APPLY (moving forward).
- downgrade() : the changes to UNDO  (rolling back).

Alembic runs upgrade() when you do  `alembic upgrade head`.
Alembic runs downgrade() when you do  `alembic downgrade -1`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Alembic identifiers — these connect migrations into a chain.
revision: str = "0001"
down_revision: Union[str, None] = None          # First migration, no parent.
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Create "documents" table ---
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("jurisdiction", sa.String(100), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("law_type", sa.String(50), nullable=True),
        sa.Column("file_path", sa.String(1000), nullable=True),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # --- Create "ingest_jobs" table ---
    op.create_table(
        "ingest_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    # Drop in reverse order because ingest_jobs references documents.
    op.drop_table("ingest_jobs")
    op.drop_table("documents")
