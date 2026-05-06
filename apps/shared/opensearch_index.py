"""
OpenSearch index definitions used by the Legal RAG system.

Milestone 3 (Part 1) introduces the keyword-only chunks index (BM25).
Later milestones will extend the index with vectors and extra fields.
"""

from __future__ import annotations


def chunks_v1_keyword_index_body() -> dict:
    """
    OpenSearch index body for keyword search over chunks.

    Notes
    - We keep mappings simple and filter-friendly:
      - `text` is analyzed (BM25)
      - metadata fields are keywords/integers for exact filtering
    - `section_path` is stored as keyword; arrays of keywords are supported.
    """
    return {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
            },
            "analysis": {
                "analyzer": {
                    # Built-in analyzers in OpenSearch: "english" and "arabic".
                    # We explicitly name them so we can target them in queries.
                    "en_analyzer": {"type": "english"},
                    "ar_analyzer": {"type": "arabic"},
                }
            },
        },
        "mappings": {
            "properties": {
                "chunk_id": {"type": "keyword"},
                "document_id": {"type": "keyword"},
                "document_title": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                # `text` is searchable with a standard analyzer and also via
                # subfields for English/Arabic-specific analysis.
                "text": {
                    "type": "text",
                    "fields": {
                        "en": {"type": "text", "analyzer": "en_analyzer"},
                        "ar": {"type": "text", "analyzer": "ar_analyzer"},
                    },
                },
                "citations": {"type": "keyword"},
                "citation_types": {"type": "keyword"},
                "citation_official_urls": {"type": "keyword"},
                "jurisdiction": {"type": "keyword"},
                "law_type": {"type": "keyword"},
                "year": {"type": "integer"},
                "source": {"type": "keyword"},
                "section_path": {"type": "keyword"},
                "ordinal": {"type": "integer"},
                "page_start": {"type": "integer"},
                "page_end": {"type": "integer"},
            }
        },
    }


def chunks_v3_hybrid_index_body(*, embedding_dim: int) -> dict:
    """
    OpenSearch index body for hybrid search (keyword + vectors).

    Milestone 7 (Part 1):
    - Adds `embedding` knn_vector field
    - Keeps multilingual analyzed subfields for `text`
    - Keeps metadata filters and citations fields
    """
    body = chunks_v1_keyword_index_body()

    # Enable k-NN on the index.
    body.setdefault("settings", {}).setdefault("index", {})["knn"] = True

    props = body.setdefault("mappings", {}).setdefault("properties", {})
    props["embedding"] = {
        "type": "knn_vector",
        "dimension": int(embedding_dim),
    }
    return body
