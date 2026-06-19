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
    "AdobeDocs/platform-learn.en":
        "https://experienceleague.adobe.com/en/docs/platform-learn",
    "AdobeDocs/customer-journey-analytics-learn.en":
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using",
}

# Data Collection docs live inside experience-platform.en (help/collection,
# help/datastreams, help/tags, help/web-sdk) but are ingested under
# adobe-docs/data-collection/ in S3. EXL publishes under /experience-platform/.
DATA_COLLECTION_HELP_FOLDERS = (
    "collection",
    "datastreams",
    "tags",
    "web-sdk",
)

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
        "AdobeDocs/experience-platform.en",
    "adobe-docs/platform-learn/":
        "AdobeDocs/platform-learn.en",
    "adobe-docs/customer-journey-analytics-learn/":
        "AdobeDocs/customer-journey-analytics-learn.en",
}

# CJA product guide: GitHub help/cja-main/ folder names differ from EXL publish paths.
CJA_FOLDER_MAP = {
    "connections": "cja-connections",
    "data-views": "cja-dataviews",
    "analysis-workspace": "cja-workspace",
    "components": "cja-components",
    "use-cases": "cja-usecases",
    "permissions": "cja-admin",
    "cja-basics": "compare-aa-cja",
    "reporting-activity-manager": "cja-admin",
}

# Repo-relative paths that are not published on Experience League (skip citations).
CJA_UNPUBLISHED_REPO_PATHS = frozenset({
    "code-of-conduct.md",
    "contributing.md",
    "license.md",
    "help/cja-main/TOC.md",
    "help/video-clips",
})

# Filename slug overrides after folder mapping (repo stem → EXL slug).
CJA_FILE_SLUG_MAP = {
    "guided-analysis-in-workspace": "overview",
    "object-arrays-in-cja": "object-arrays",
}

# Prefix rewrites applied after CJA folder mapping (old → new).
CJA_PATH_REWRITES = (
    ("cja-workspace/curate-and-share/", "cja-workspace/export/"),
    ("cja-workspace/curate-share/", "cja-workspace/export/"),
    (
        "cja-workspace/virtual-analyst/anomaly-detection/",
        "cja-workspace/anomaly-detection/",
    ),
    (
        "cja-workspace/panels/media-playback-timespent/",
        "cja-workspace/panels/media-playback-time-spent/",
    ),
    ("cja-dataviews/context-aware-sessions", "cja-dataviews/session-settings"),
    ("cja-main/overview", "cja-workspace/home"),
    ("overview", "cja-workspace/home"),
)

# Analytics: GitHub guide folder names differ from EXL publish slugs.
ANALYTICS_GUIDE_MAP = {
    "implement": "implementation",
    "integrate": "integration",
}

# AJO: journey docs publish under orchestrate-journeys on EXL.
AJO_FOLDER_MAP = {
    "building-journeys": "orchestrate-journeys",
}

# AEP: GitHub folder names that differ from EXL publish paths.
AEP_FOLDER_MAP = {
    "query-service": "query",
}

_USING_PRODUCTS = ("journey-optimizer", "target")


def repo_from_s3_key(s3_key: str) -> str | None:
    for prefix, repo in S3_PREFIX_TO_REPO.items():
        if s3_key.startswith(prefix):
            return repo
    return None


def repo_path_from_s3_key(s3_key: str) -> str | None:
    for prefix, _repo in S3_PREFIX_TO_REPO.items():
        if s3_key.startswith(prefix):
            return s3_key[len(prefix):]
    return None


def s3_key_from_repo_path(repo: str, repo_path: str) -> str | None:
    path = repo_path.lstrip("/")
    for prefix, mapped_repo in S3_PREFIX_TO_REPO.items():
        if mapped_repo == repo:
            return f"{prefix}{path}"
    return None


def get_canonical_exl_url(repo_path: str, repo: str) -> str | None:
    """
    Resolve canonical Experience League URL from a GitHub repo-relative path.

    Example:
        get_canonical_exl_url("help/using/campaigns/api-triggered-campaigns.md",
                              "AdobeDocs/journey-optimizer.en")
    """
    s3_key = s3_key_from_repo_path(repo, repo_path)
    if not s3_key:
        return None
    return derive_exl_url(s3_key)


def _ensure_using_prefix(url: str, product: str) -> str:
    """Inject /using/ after product slug when the derived path omits it."""
    marker = f"/en/docs/{product}/"
    if marker not in url:
        return url
    suffix = url.split(marker, 1)[1]
    if suffix.startswith("using/"):
        return url
    return f"https://experienceleague.adobe.com/en/docs/{product}/using/{suffix}"


def _normalize_cja_file_slug(slug: str) -> str:
    if slug in CJA_FILE_SLUG_MAP:
        return CJA_FILE_SLUG_MAP[slug]
    for suffix in ("-in-customer-journey-analytics", "-in-cja"):
        if slug.endswith(suffix):
            return slug[: -len(suffix)]
    return slug


def _collapse_duplicate_path_segment(path: str) -> str:
    parts = path.split("/")
    if len(parts) >= 2 and parts[-1] == parts[-2]:
        return "/".join(parts[:-1])
    return path


def _apply_cja_path_rewrites(path: str) -> str:
    for old, new in CJA_PATH_REWRITES:
        if path == old or path.startswith(old):
            return new + path[len(old):]
    return path


def _apply_cja_folder_map(repo_relative: str) -> str:
    parts = repo_relative.split("/")
    if parts and parts[0] in CJA_FOLDER_MAP:
        parts = CJA_FOLDER_MAP[parts[0]].split("/") + parts[1:]
        repo_relative = "/".join(parts)
    if parts:
        parts[-1] = _normalize_cja_file_slug(parts[-1])
        repo_relative = "/".join(parts)
    repo_relative = _collapse_duplicate_path_segment(repo_relative)
    return _apply_cja_path_rewrites(repo_relative)


def _is_cja_unpublished_repo_path(repo_relative: str) -> bool:
    clean = repo_relative.lstrip("/")
    if clean in CJA_UNPUBLISHED_REPO_PATHS:
        return True
    return any(clean.startswith(p) for p in CJA_UNPUBLISHED_REPO_PATHS if p.endswith("/") or "/" in p)


def _apply_analytics_guide_map(repo_relative: str) -> str:
    parts = repo_relative.split("/")
    if parts and parts[0] in ANALYTICS_GUIDE_MAP:
        parts[0] = ANALYTICS_GUIDE_MAP[parts[0]]
        return "/".join(parts)
    return repo_relative


def _apply_ajo_folder_map(repo_relative: str) -> str:
    parts = repo_relative.split("/")
    for i, part in enumerate(parts):
        if part in AJO_FOLDER_MAP:
            parts[i] = AJO_FOLDER_MAP[part]
            break
    return "/".join(parts)


def _apply_aep_folder_map(repo_relative: str) -> str:
    parts = repo_relative.split("/")
    if parts and parts[0] in AEP_FOLDER_MAP:
        parts[0] = AEP_FOLDER_MAP[parts[0]]
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

        if repo == "AdobeDocs/analytics-platform.en" and _is_cja_unpublished_repo_path(repo_relative):
            return None

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

        if repo == "AdobeDocs/customer-journey-analytics-learn.en" and repo_relative.startswith("cja-main/"):
            repo_relative = repo_relative[len("cja-main/"):]

        if repo == "AdobeDocs/target.en" and repo_relative.startswith("main/"):
            repo_relative = repo_relative[len("main/"):]

        if repo_relative.endswith(".md"):
            repo_relative = repo_relative[:-3]

        if repo_relative.endswith("/index"):
            repo_relative = repo_relative[:-6]

        if repo == "AdobeDocs/analytics-platform.en":
            repo_relative = _apply_cja_folder_map(repo_relative)

        if repo == "AdobeDocs/customer-journey-analytics-learn.en":
            repo_relative = _apply_cja_folder_map(repo_relative)

        if repo == "AdobeDocs/analytics.en":
            repo_relative = _apply_analytics_guide_map(repo_relative)

        if repo == "AdobeDocs/journey-optimizer.en":
            repo_relative = _apply_ajo_folder_map(repo_relative)

        if repo == "AdobeDocs/experience-platform.en":
            repo_relative = _apply_aep_folder_map(repo_relative)

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
    Read the citation URL from chunk metadata only.

    URLs must be attached at index time (validated exl_url / url fields).
    This function never derives URLs from s3_key at answer time.
    """
    _ = content
    for key in ("exl_url", "url"):
        stored = (meta.get(key) or "").strip()
        if is_specific_url(stored):
            return stored
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
