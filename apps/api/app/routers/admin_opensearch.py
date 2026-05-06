"""
Admin endpoints for OpenSearch initialization.

Note: This is intentionally minimal for early milestones.
In production, admin endpoints must be protected (auth, network ACLs).
"""

from fastapi import APIRouter

from app.opensearch_utils import ensure_chunks_alias, ensure_chunks_index


router = APIRouter(prefix="/v1/admin/opensearch", tags=["admin"])


@router.post("/init")
def init_opensearch():
    """
    Initialize required OpenSearch indexes.

    Milestone 3 (Part 1): ensures the chunks keyword index exists.
    """
    return {"chunks": ensure_chunks_index(), "alias": ensure_chunks_alias()}
