"""
Canonical mapping from AdobeDocs GitHub repo to Experience League URL base.
File path within the repo maps directly to the URL path after stripping
the 'help/' prefix and '.md' extension.
"""

REPO_TO_EXL_BASE = {
    "AdobeDocs/analytics.en":
        "https://experienceleague.adobe.com/en/docs/analytics",
    "AdobeDocs/analytics-platform.en":
        "https://experienceleague.adobe.com/en/docs/analytics-platform",
    "AdobeDocs/experience-platform.en":
        "https://experienceleague.adobe.com/en/docs/experience-platform",
    "AdobeDocs/journey-optimizer.en":
        "https://experienceleague.adobe.com/en/docs/journey-optimizer",
    "AdobeDocs/target.en":
        "https://experienceleague.adobe.com/en/docs/target",
    "AdobeDocs/data-collection.en":
        "https://experienceleague.adobe.com/en/docs/data-collection",
}

S3_PREFIX_TO_REPO = {
    "adobe-docs/adobe-analytics/":
        "AdobeDocs/analytics.en",
    "adobe-docs/customer-journey-analytics/":
        "AdobeDocs/analytics-platform.en",
    "adobe-docs/experience-platform/":
        "AdobeDocs/experience-platform.en",
    "adobe-docs/adobe-journey-optimizer/":
        "AdobeDocs/journey-optimizer.en",
    "adobe-docs/adobe-target/":
        "AdobeDocs/target.en",
    "adobe-docs/data-collection/":
        "AdobeDocs/data-collection.en",
}


def derive_exl_url(s3_key: str) -> str | None:
    """
    Derive the canonical Experience League URL from an S3 key,
    then resolve through the redirects map to get the current URL.

    Example:
        s3_key = "adobe-docs/adobe-analytics/help/analyze/analysis-workspace/
                  build-workspace-project/freeform-table.md"
        raw    = "https://experienceleague.adobe.com/en/docs/analytics/analyze/
                  analysis-workspace/build-workspace-project/freeform-table"
        result = resolved canonical URL via redirects.csv
    """
    from src.utils.exl_redirects import resolve_canonical_url

    for s3_prefix, repo in S3_PREFIX_TO_REPO.items():
        if s3_key.startswith(s3_prefix):
            base_url = REPO_TO_EXL_BASE.get(repo)
            if not base_url:
                return None

            repo_relative = s3_key[len(s3_prefix):]

            if repo_relative.startswith("help/"):
                repo_relative = repo_relative[len("help/"):]

            if repo_relative.endswith(".md"):
                repo_relative = repo_relative[:-3]

            if repo_relative.endswith("/index"):
                repo_relative = repo_relative[:-6]

            raw_url = f"{base_url}/{repo_relative}"
            return resolve_canonical_url(raw_url)

    return None


def is_specific_url(url: str | None) -> bool:
    """
    Returns True if the URL points to a specific page, not just the
    generic Experience League homepage or a bare product root.
    """
    if not url:
        return False
    generic = [
        "https://experienceleague.adobe.com/en/docs",
        "https://experienceleague.adobe.com/docs",
        "https://experienceleague.adobe.com",
    ]
    clean = url.strip("/")
    if clean in [g.strip("/") for g in generic]:
        return False
    parts = clean.replace(
        "https://experienceleague.adobe.com/en/docs/", ""
    ).split("/")
    return len(parts) >= 2
