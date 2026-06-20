"""
Adobe developer.adobe.com API doc repos for sync → S3 → Chroma.

Each entry mirrors a block in scripts/sync_docs_to_s3.py REPOS and maps S3 keys
to published URLs on developer.adobe.com (not Experience League).
"""

from __future__ import annotations

# GitHub tree → S3 sync config (merged into REPOS in sync_docs_to_s3.py)
API_DOC_REPOS: dict[str, dict] = {
    "adobe-docs/analytics-apis": {
        "github": "AdobeDocs/analytics-2.0-apis",
        "branch": "main",
        "s3_prefix": "adobe-docs/analytics-apis/",
        "path_filter": "src/pages/",
        "developer_adobe_base": "https://developer.adobe.com/analytics-apis/docs/2.0",
        "url_path_strip": "src/pages/",
        "product": "Analytics APIs",
        "doc_type": "api",
        "level": "advanced",
    },
    "adobe-docs/cja-apis": {
        "github": "AdobeDocs/cja-apis",
        "branch": "main",
        "s3_prefix": "adobe-docs/cja-apis/",
        "path_filter": "src/pages/",
        "developer_adobe_base": "https://developer.adobe.com/cja-apis/docs",
        "url_path_strip": "src/pages/",
        "product": "CJA APIs",
        "doc_type": "api",
        "level": "advanced",
    },
    "adobe-docs/data-collection-apis": {
        "github": "AdobeDocs/data-collection-apis",
        "branch": "main",
        "s3_prefix": "adobe-docs/data-collection-apis/",
        "path_filter": "src/pages/",
        "developer_adobe_base": "https://developer.adobe.com/data-collection-apis/docs",
        "url_path_strip": "src/pages/",
        "product": "Data Collection APIs",
        "doc_type": "api",
        "level": "advanced",
    },
    "adobe-docs/journey-optimizer-apis": {
        "github": "AdobeDocs/journey-optimizer-apis",
        "branch": "main",
        "s3_prefix": "adobe-docs/journey-optimizer-apis/",
        "path_filter": "src/pages/",
        "developer_adobe_base": "https://developer.adobe.com/journey-optimizer-apis",
        "url_path_strip": "src/pages/",
        "product": "AJO APIs",
        "doc_type": "api",
        "level": "advanced",
    },
    "adobe-docs/experience-platform-apis": {
        "github": "AdobeDocs/experience-platform-apis",
        "branch": "main",
        "s3_prefix": "adobe-docs/experience-platform-apis/",
        "path_filter": "src/pages/",
        "developer_adobe_base": "https://developer.adobe.com/experience-platform-apis",
        "url_path_strip": "src/pages/",
        "product": "AEP APIs",
        "doc_type": "api",
        "level": "advanced",
    },
}

# S3 prefix → (GitHub repo, developer.adobe.com base) for citation URL derivation
DEVELOPER_ADOBE_S3_MAP: dict[str, tuple[str, str]] = {
    cfg["s3_prefix"]: (cfg["github"], cfg["developer_adobe_base"].rstrip("/"))
    for cfg in API_DOC_REPOS.values()
}

# Ordered list for targeted ingest / GHA workflow_dispatch
API_DOC_INGEST_ORDER: list[tuple[str, str, str]] = [
    ("adobe-docs/analytics-apis", "adobe-docs/analytics-apis/", "Analytics APIs"),
    ("adobe-docs/cja-apis", "adobe-docs/cja-apis/", "CJA APIs"),
    ("adobe-docs/data-collection-apis", "adobe-docs/data-collection-apis/", "Data Collection APIs"),
    ("adobe-docs/journey-optimizer-apis", "adobe-docs/journey-optimizer-apis/", "AJO APIs"),
    ("adobe-docs/experience-platform-apis", "adobe-docs/experience-platform-apis/", "AEP APIs"),
]
