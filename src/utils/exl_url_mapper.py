"""
Canonical mapping from AdobeDocs GitHub repo to Experience League URL base.
File path within the repo maps directly to the URL path after stripping
repo-specific prefixes and applying folder renames.
"""

import re

REPO_TO_EXL_BASE = {
    "AdobeDocs/analytics.en":
        "https://experienceleague.adobe.com/en/docs/analytics",
    "AdobeDocs/analytics-platform.en":
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using",
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

# CJA product guide: repo folder names differ from EXL publish paths.
CJA_FOLDER_MAP = {
    "connections": "cja-connections",
    "data-views": "cja-dataviews",
    "analysis-workspace": "cja-workspace",
}

_USING_PRODUCTS = ("journey-optimizer", "target")


def _ensure_using_prefix(url: str, product: str) -> str:
    """Inject /using/ after product slug when the derived path omits it."""
    marker = f"/en/docs/{product}/"
    if marker not in url:
        return url
    suffix = url.split(marker, 1)[1]
    if suffix.startswith("using/"):
        return url
    return f"https://experienceleague.adobe.com/en/docs/{product}/using/{suffix}"


def _apply_cja_folder_map(repo_relative: str) -> str:
    parts = repo_relative.split("/")
    if parts and parts[0] in CJA_FOLDER_MAP:
        parts = CJA_FOLDER_MAP[parts[0]].split("/") + parts[1:]
        return "/".join(parts)
    return repo_relative


def _fix_target_url(url: str) -> str:
    """
    Target repo uses help/main/ and c-/r-/t- folder prefixes.
    EXL publishes under /using/ with plain segment names.
    """
    url = url.replace("/en/docs/target/main/", "/en/docs/target/using/")
    parts = url.split("/")
    return "/".join(re.sub(r"^[crt]-", "", p) for p in parts)


def derive_exl_url(s3_key: str) -> str | None:
    """
    Derive the canonical Experience League URL from an S3 key,
    then resolve through the redirects map to get the current URL.
    """
    from src.utils.exl_redirects import resolve_canonical_url

    for s3_prefix, repo in S3_PREFIX_TO_REPO.items():
        if not s3_key.startswith(s3_prefix):
            continue
        base_url = REPO_TO_EXL_BASE.get(repo)
        if not base_url:
            return None

        repo_relative = s3_key[len(s3_prefix):]

        # Analytics API docs live under src/pages/, published at developer.adobe.com
        if repo == "AdobeDocs/analytics.en" and repo_relative.startswith("src/pages/"):
            api_path = repo_relative[len("src/pages/"):]
            if api_path.endswith(".md"):
                api_path = api_path[:-3]
            if api_path.endswith("/index"):
                api_path = api_path[:-6]
            return f"https://developer.adobe.com/analytics-apis/docs/2.0/{api_path}"

        if repo_relative.startswith("help/"):
            repo_relative = repo_relative[len("help/"):]

        if repo == "AdobeDocs/analytics-platform.en" and repo_relative.startswith("cja-main/"):
            repo_relative = repo_relative[len("cja-main/"):]

        if repo == "AdobeDocs/target.en" and repo_relative.startswith("main/"):
            repo_relative = repo_relative[len("main/"):]

        if repo_relative.endswith(".md"):
            repo_relative = repo_relative[:-3]

        if repo_relative.endswith("/index"):
            repo_relative = repo_relative[:-6]

        if repo == "AdobeDocs/analytics-platform.en":
            repo_relative = _apply_cja_folder_map(repo_relative)

        raw_url = f"{base_url}/{repo_relative}"

        if repo == "AdobeDocs/journey-optimizer.en":
            raw_url = _ensure_using_prefix(raw_url, "journey-optimizer")
        elif repo == "AdobeDocs/target.en":
            raw_url = _ensure_using_prefix(raw_url, "target")

        resolved = resolve_canonical_url(raw_url)

        if repo == "AdobeDocs/target.en":
            resolved = _fix_target_url(resolved)

        return resolved

    return None


def resolve_doc_url(meta: dict, content: str = "") -> str | None:
    """
    Resolve the best citation URL from chunk metadata.
    Prefer fresh derivation from s3_key; fall back to stored url via redirects.
    """
    from src.utils.exl_redirects import resolve_canonical_url

    _ = content  # reserved; derivation uses metadata only

    s3_key = meta.get("s3_key", "")
    if s3_key:
        derived = derive_exl_url(s3_key)
        if is_specific_url(derived):
            return derived

    stored = meta.get("url", "")
    if stored:
        resolved = resolve_canonical_url(stored)
        if is_specific_url(resolved):
            return resolved

    return None


def is_specific_url(url: str | None) -> bool:
    """
    Returns True if the URL points to a specific documentation page.
    Rejects generic homepages, bare product roots, navigation-only files, and raw .md paths.
    """
    if not url:
        return False
    if url.lower().endswith(".md"):
        return False
    generic = [
        "https://experienceleague.adobe.com/en/docs",
        "https://experienceleague.adobe.com/docs",
        "https://experienceleague.adobe.com",
    ]
    clean = url.strip("/")
    if clean in [g.strip("/") for g in generic]:
        return False
    last_segment = clean.split("/")[-1].upper()
    if last_segment in ("TOC", "TOC.MD"):
        return False
    if "developer.adobe.com/" in clean:
        parts = clean.split("/")
        return len(parts) >= 7
    parts = clean.replace(
        "https://experienceleague.adobe.com/en/docs/", ""
    ).split("/")
    return len(parts) >= 2
