"""create citations tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-07

Adds Milestone 5 storage:
- citations
- chunk_citations
- citation_edges
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "citations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("canonical_id", sa.String(300), nullable=False),
        sa.Column("citation_type", sa.String(50), nullable=False),
        sa.Column("jurisdiction", sa.String(50), nullable=True),
        sa.Column("display", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("canonical_id", name="uq_citations_canonical_id"),
    )

    op.create_table(
        "chunk_citations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "chunk_id",
            sa.Uuid(),
            sa.ForeignKey("chunks.id"),
            nullable=False,
        ),
        sa.Column(
            "citation_id",
            sa.Uuid(),
            sa.ForeignKey("citations.id"),
            nullable=False,
        ),
        sa.Column("raw_text", sa.String(500), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=True),
        sa.Column("end_char", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "citation_edges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "from_document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column(
            "to_citation_id",
            sa.Uuid(),
            sa.ForeignKey("citations.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_chunk_citations_chunk_id", "chunk_citations", ["chunk_id"])
    op.create_index("ix_chunk_citations_citation_id", "chunk_citations", ["citation_id"])
    op.create_index("ix_citation_edges_from_document_id", "citation_edges", ["from_document_id"])
    op.create_index("ix_citation_edges_to_citation_id", "citation_edges", ["to_citation_id"])


def downgrade() -> None:
    op.drop_index("ix_citation_edges_to_citation_id", table_name="citation_edges")
    op.drop_index("ix_citation_edges_from_document_id", table_name="citation_edges")
    op.drop_index("ix_chunk_citations_citation_id", table_name="chunk_citations")
    op.drop_index("ix_chunk_citations_chunk_id", table_name="chunk_citations")

    op.drop_table("citation_edges")
    op.drop_table("chunk_citations")
    op.drop_table("citations")

