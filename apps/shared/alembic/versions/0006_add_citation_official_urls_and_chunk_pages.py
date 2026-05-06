"""add citation official url and chunk page mapping

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("citations", sa.Column("official_url", sa.String(length=2000), nullable=True))
    op.add_column("chunks", sa.Column("page_start", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("page_end", sa.Integer(), nullable=True))
    op.create_index("ix_chunks_page_start", "chunks", ["page_start"])
    op.create_index("ix_chunks_page_end", "chunks", ["page_end"])


def downgrade() -> None:
    op.drop_index("ix_chunks_page_end", table_name="chunks")
    op.drop_index("ix_chunks_page_start", table_name="chunks")
    op.drop_column("chunks", "page_end")
    op.drop_column("chunks", "page_start")
    op.drop_column("citations", "official_url")

