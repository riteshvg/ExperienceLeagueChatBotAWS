# Citation flow: GitHub source → index metadata → Rovr answer

## Principle

Experience League URLs are resolved **once at index time**, HTTP-validated, and stored on
each chunk. Answer generation reads `url` / `exl_url` from metadata — it never
reconstructs URLs from `s3_key`.

## Supported products

| Product | GitHub repo | S3 prefix | Redirects CSV |
|---------|-------------|-----------|---------------|
| Adobe Analytics | `AdobeDocs/analytics.en` | `adobe-docs/adobe-analytics/` | `redirects-analytics.csv` |
| Customer Journey Analytics | `AdobeDocs/analytics-platform.en` | `adobe-docs/customer-journey-analytics/` | `redirects-cja.csv` |
| Adobe Experience Platform | `AdobeDocs/experience-platform.en` | `adobe-docs/experience-platform/` | `redirects-aep.csv` |
| Adobe Journey Optimizer | `AdobeDocs/journey-optimizer.en` | `adobe-docs/adobe-journey-optimizer/` | `redirects-ajo.csv` |
| Adobe Target | `AdobeDocs/target.en` | `adobe-docs/adobe-target/` | — |
| Adobe Data Collection | `AdobeDocs/experience-platform.en` *(subset)* | `adobe-docs/data-collection/` | `redirects-aep.csv` |

**Data Collection source paths** (same GitHub repo as AEP, separate S3 product prefix):

| GitHub folder | TOC | EXL path |
|---------------|-----|----------|
| `help/collection/` | `help/collection/TOC.md` | `/en/docs/experience-platform/collection/` |
| `help/datastreams/` | `help/datastreams/TOC.md` | `/en/docs/experience-platform/datastreams/` |
| `help/tags/` | `help/tags/TOC.md` | `/en/docs/experience-platform/tags/` |
| `help/web-sdk/` | *(no root TOC)* | `/en/docs/experience-platform/web-sdk/` |

There is no standalone `AdobeDocs/data-collection.en` repo. Ingest is configured in
`scripts/sync_docs_to_s3.py` (`data-collection-tags`, `data-collection-web-sdk`, etc.).
See `reports/data_collection_toc_exl_mapping.csv` for sample TOC → EXL mappings.

## Index-time metadata

Each chunk stores:

```json
{
  "repo_path": "help/using/campaigns/api-triggered-campaigns.md",
  "exl_url": "https://experienceleague.adobe.com/en/docs/journey-optimizer/using/campaigns/api-triggered-campaigns",
  "url": "<same as exl_url when HTTP 200, else blank>",
  "url_source": "validated | dead | unmapped"
}
```

## Resolver API

```python
from src.utils.exl_url_mapper import get_canonical_exl_url

get_canonical_exl_url("help/using/campaigns/api-triggered-campaigns.md",
                      "AdobeDocs/journey-optimizer.en")
```

## Pipeline

```
GitHub .md  →  ingest_to_chroma.py  →  build_index_metadata()
                enrich_citation_metadata.py  →  HTTP validate  →  ChromaDB

Query  →  retrieve chunks  →  resolve_doc_url(meta)  →  reads url only
        →  evidence / citations SSE  →  Sources panel
```

## Tooling

```bash
python3 scripts/validate_exl_urls.py --csv reports/exl_validation.csv
python3 scripts/enrich_citation_metadata.py --dry-run
python3 scripts/enrich_citation_metadata.py
```
