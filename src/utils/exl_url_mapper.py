"""
Canonical mapping from AdobeDocs GitHub repo to Experience League URL base.
File path within the repo maps directly to the URL path after stripping
the 'help/' prefix and '.md' extension.
"""

import re

REPO_TO_EXL_BASE = {
    "AdobeDocs/analytics.en":
        "https://experienceleague.adobe.com/en/docs/analytics",
    "AdobeDocs/analytics-platform.en":
        "https://experienceleague.adobe.com/en/docs/customer-journey-analytics",
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


def _fix_target_url(url: str) -> str:
    """
    Target repo uses help/main/ and c-/r-/t- folder prefixes.
    EXL publishes under /using/ with plain segment names.
    """
    url = url.replace("/en/docs/target/main/", "/en/docs/target/using/")
    parts = url.split("/")
    return "/".join(re.sub(r'^[crt]-', '', p) for p in parts)


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

            # Analytics API docs live under src/pages/ in the repo, published at developer.adobe.com
            if repo == "AdobeDocs/analytics.en" and repo_relative.startswith("src/pages/"):
                api_path = repo_relative[len("src/pages/"):]
                if api_path.endswith(".md"):
                    api_path = api_path[:-3]
                if api_path.endswith("/index"):
                    api_path = api_path[:-6]
                return f"https://developer.adobe.com/analytics-apis/docs/2.0/{api_path}"

            if repo_relative.startswith("help/"):
                repo_relative = repo_relative[len("help/"):]

            # CJA repo uses cja-main/ as a top-level internal folder — strip it
            if repo == "AdobeDocs/analytics-platform.en" and repo_relative.startswith("cja-main/"):
                repo_relative = repo_relative[len("cja-main/"):]

            if repo_relative.endswith(".md"):
                repo_relative = repo_relative[:-3]

            if repo_relative.endswith("/index"):
                repo_relative = repo_relative[:-6]

            raw_url = f"{base_url}/{repo_relative}"
            resolved = resolve_canonical_url(raw_url)

            # Target docs: repo uses help/main/ + c-/r-/t- folder prefixes.
            # EXL publishes them under /using/ with plain names.
            if repo == "AdobeDocs/target.en":
                resolved = _fix_target_url(resolved)

            return resolved

    return None


def is_specific_url(url: str | None) -> bool:
    """
    Returns True if the URL points to a specific documentation page.
    Rejects generic homepages, bare product roots, and navigation-only files.
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
    # TOC files are navigation-only, never valid citation targets
    last_segment = clean.split("/")[-1].upper()
    if last_segment in ("TOC", "TOC.MD"):
        return False
    # developer.adobe.com API docs — specific if path has at least 4 segments after host
    if "developer.adobe.com/" in clean:
        parts = clean.split("/")
        return len(parts) >= 7
    parts = clean.replace(
        "https://experienceleague.adobe.com/en/docs/", ""
    ).split("/")
    return len(parts) >= 2
