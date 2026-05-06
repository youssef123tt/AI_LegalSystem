"""add ingest_jobs extraction diagnostics fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-07

Adds Milestone 3+ diagnostics to ingest_jobs so we can:
- flag needs_ocr / needs_review without failing the job
- store extraction quality metrics for Arabic/English PDFs
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ingest_jobs", sa.Column("needs_ocr", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("ingest_jobs", sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column("ingest_jobs", sa.Column("extraction_method", sa.String(50), nullable=True))
    op.add_column("ingest_jobs", sa.Column("quality_score", sa.Integer(), nullable=True))
    op.add_column("ingest_jobs", sa.Column("arabic_letter_count", sa.Integer(), nullable=True))
    op.add_column("ingest_jobs", sa.Column("arabic_presentation_forms", sa.Integer(), nullable=True))
    op.add_column("ingest_jobs", sa.Column("replacement_char_count", sa.Integer(), nullable=True))
    op.add_column("ingest_jobs", sa.Column("has_tounicode", sa.Boolean(), nullable=True))

    op.add_column("ingest_jobs", sa.Column("indexed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("ingest_jobs", sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index("ix_ingest_jobs_needs_ocr", "ingest_jobs", ["needs_ocr"])
    op.create_index("ix_ingest_jobs_needs_review", "ingest_jobs", ["needs_review"])


def downgrade() -> None:
    op.drop_index("ix_ingest_jobs_needs_review", table_name="ingest_jobs")
    op.drop_index("ix_ingest_jobs_needs_ocr", table_name="ingest_jobs")

    op.drop_column("ingest_jobs", "indexed_at")
    op.drop_column("ingest_jobs", "indexed")

    op.drop_column("ingest_jobs", "has_tounicode")
    op.drop_column("ingest_jobs", "replacement_char_count")
    op.drop_column("ingest_jobs", "arabic_presentation_forms")
    op.drop_column("ingest_jobs", "arabic_letter_count")
    op.drop_column("ingest_jobs", "quality_score")
    op.drop_column("ingest_jobs", "extraction_method")

    op.drop_column("ingest_jobs", "needs_review")
    op.drop_column("ingest_jobs", "needs_ocr")

