"""
OpenSearch helpers for the API service.

Milestone 3 (Part 1):
- define how the keyword-only chunks index is created
- provide a single function to "ensure" the index exists
"""

from __future__ import annotations

from opensearchpy import OpenSearch

from app.settings import settings
from shared.opensearch_index import chunks_v1_keyword_index_body, chunks_v3_hybrid_index_body


def make_client() -> OpenSearch:
    return OpenSearch(hosts=[settings.opensearch_url])


def ensure_chunks_index() -> dict:
    """
    Create the chunks keyword index if it does not exist.

    Returns a small status dict suitable for API responses/logging.
    """
    client = make_client()
    index_name = settings.opensearch_chunks_index

    if client.indices.exists(index=index_name):
        # Safe mapping updates for newly added fields (does not change analyzers).
        try:
            client.indices.put_mapping(
                index=index_name,
                body={
                    "properties": {
                        "citations": {"type": "keyword"},
                        "citation_types": {"type": "keyword"},
                        "citation_official_urls": {"type": "keyword"},
                        "page_start": {"type": "integer"},
                        "page_end": {"type": "integer"},
                    }
                },
            )
        except Exception:
            # Mapping update is best-effort; index may already have the fields.
            pass
        return {"index": index_name, "status": "exists"}

    # Choose index body based on configured index name.
    if settings.opensearch_chunks_index.startswith("chunks_v3"):
        body = chunks_v3_hybrid_index_body(embedding_dim=settings.embeddings_dimensions)
    else:
        body = chunks_v1_keyword_index_body()
    client.indices.create(index=index_name, body=body)
    return {"index": index_name, "status": "created"}


def ensure_chunks_alias() -> dict:
    """
    Ensure the stable chunks alias points to the configured chunks index.

    This enables zero-downtime index versioning by letting clients query the alias.
    """
    client = make_client()
    alias = settings.opensearch_chunks_alias
    index = settings.opensearch_chunks_index

    # Create index if missing (so alias can be attached).
    ensure_chunks_index()

    # If alias exists, check if it's already pointing to our index.
    if client.indices.exists_alias(name=alias):
        current = client.indices.get_alias(name=alias)
        if index in current:
            return {"alias": alias, "status": "exists", "index": index}

        actions = []
        for idx in current.keys():
            actions.append({"remove": {"index": idx, "alias": alias}})
        actions.append({"add": {"index": index, "alias": alias}})
        client.indices.update_aliases({"actions": actions})
        return {"alias": alias, "status": "moved", "index": index}

    client.indices.put_alias(index=index, name=alias)
    return {"alias": alias, "status": "created", "index": index}
