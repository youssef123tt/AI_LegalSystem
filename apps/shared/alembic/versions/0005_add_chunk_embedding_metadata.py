"""add chunks embedding metadata

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-08

Adds Milestone 7 (Part 1) fields:
- chunks.embedding_model
- chunks.embedded_at

Vector values are stored in OpenSearch, not Postgres.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("embedding_model", sa.String(200), nullable=True))
    op.add_column("chunks", sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_chunks_embedding_model", "chunks", ["embedding_model"])


def downgrade() -> None:
    op.drop_index("ix_chunks_embedding_model", table_name="chunks")
    op.drop_column("chunks", "embedded_at")
    op.drop_column("chunks", "embedding_model")

