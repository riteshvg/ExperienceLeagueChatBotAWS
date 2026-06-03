# Building the Knowledge Base: Corpus, Chunking, and the Metadata Registry

**Part 2 of 5 — Building the Experience League Unofficial Chatbot**

---

If Part 1 was about why this project exists and the architectural decisions that shaped it, Part 2 is about the work that made it actually useful: building a knowledge base worth querying.

A RAG system is only as good as what you put into it. The retrieval can be perfect, the LLM prompt can be beautifully engineered, and the UI can be polished — but if the knowledge base has bad chunks, wrong URLs, or no metadata, the whole thing falls apart at query time. I spent more time on this layer than on everything else combined, and most of that time was on problems I didn't anticipate.

This post covers the full pipeline: where the docs come from, how I chunked them, why I chose Titan Embed v2, how ChromaDB is configured, what the metadata registry is and why it matters, and how media (videos and screenshots) gets extracted and linked back to the correct documents.

---

## Where the Data Comes From

Adobe open-sources all Experience League documentation on GitHub under the `AdobeDocs` organisation. Every product's documentation lives in its own repo, and they're all public. The three repos powering this chatbot are:

- `AdobeDocs/analytics.en` — Adobe Analytics (~964 unique pages)
- `AdobeDocs/analytics-platform.en` — Customer Journey Analytics (~136 pages)
- `AdobeDocs/experience-platform.en` — Adobe Experience Platform (~160 pages)

Everything is Markdown. The frontmatter is YAML (title, description, role, level, doc_type), the body is standard CommonMark with some Adobe-flavoured extensions like `>[!NOTE]` and `>[!VIDEO]` callouts.

The pipeline goes: GitHub repos → S3 bucket (`experienceleaguechatbot`) → ChromaDB. I upload the raw `.md` files to S3 and treat S3 as the stable source of truth for ingestion.

This intermediate store matters more than it might seem. Without it, every time I want to re-embed with a different model or change the chunking strategy, I'd have to re-clone three GitHub repos, filter out the non-documentation files (there are a lot of them: `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, CI configs, etc.), and re-run the whole process. With S3, I've already done that filtering once. The files in the bucket are exactly what I want to ingest — nothing more.

It also decouples ingestion timing from indexing. The docs on GitHub are updated constantly; the S3 bucket represents a stable snapshot. My knowledge base cutoff is clearly defined as the last S3 sync date (March 14, 2026 in the current build), which I can surface in the UI so users know how fresh the information is.

---

## The Chunking Strategy

This is the decision I thought about most, and got partially wrong the first time.

The naive approach — split every N characters with some overlap — produces bad retrieval for documentation. Documentation has logical structure. A procedure might span 800 tokens across seven numbered steps. A configuration reference might have a 50-token header followed by a 600-token table. Split that down the middle and you get chunks that are syntactically valid but semantically useless: a retriever might surface step 4 of a process with no context for what the process is, or half a configuration table with the column headers in a different chunk than the values.

The strategy I settled on, implemented in `scripts/ingest_to_chroma.py`, has three levels:

1. **Split on H2/H3 headers first.** A markdown section is the natural unit of documentation. The header line itself gets kept with the section content that follows it, so a retrieved chunk always has its own heading.

2. **If a section exceeds 500 tokens, split on paragraph boundaries.** Paragraphs are the next logical unit down. Most paragraphs in technical documentation are 100–300 tokens, so this handles the majority of oversized sections cleanly.

3. **If a paragraph still exceeds the limit, hard-split with overlap.** This is the escape hatch for things like large tables, code blocks that can't be broken up, or long bullet-point lists. The overlap (`CHUNK_OVERLAP = 50` tokens, represented as 200 characters) means adjacent hard-split chunks share a small window of context.

Here is the full chunking function from `scripts/ingest_to_chroma.py`:

```python
def split_markdown(text: str, s3_key: str) -> list[str]:
    """
    Split a markdown document into chunks of ~500 tokens.

    Strategy:
    1. Split on ## or ### headers (keep header with its section)
    2. If a section is still too large, split on paragraphs
    3. If a paragraph is still too large, hard-split by character count
    """
    CHUNK_SIZE = 500   # approximate token ceiling
    CHUNK_OVERLAP = 50

    text = text.replace("\r\n", "\n").strip()
    sections = re.split(r"(?m)^(#{1,3} .+)$", text)

    chunks: list[str] = []
    current = ""

    for part in sections:
        part = part.strip()
        if not part:
            continue
        candidate = (current + "\n\n" + part).strip() if current else part
        if _rough_token_count(candidate) <= CHUNK_SIZE:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # If the part itself is large, split on paragraphs
            paragraphs = [p.strip() for p in part.split("\n\n") if p.strip()]
            para_buf = ""
            for para in paragraphs:
                c2 = (para_buf + "\n\n" + para).strip() if para_buf else para
                if _rough_token_count(c2) <= CHUNK_SIZE:
                    para_buf = c2
                else:
                    if para_buf:
                        chunks.append(para_buf)
                    # Hard-split oversized paragraph with overlap
                    chars = CHUNK_SIZE * 4
                    overlap = CHUNK_OVERLAP * 4
                    for start in range(0, len(para), chars - overlap):
                        chunks.append(para[start: start + chars])
                    para_buf = ""
            current = para_buf

    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]
```

The token approximation is `len(text) // 4` — four characters per token on average. This is rough. It will be wrong for heavily code-laden text (which has more tokens per character), and slightly generous for English prose. But the exact count doesn't matter. What matters is keeping logical units intact, and that heuristic is good enough to prevent the most destructive splits. Using a real tokenizer here would add meaningful latency across 5,685 chunks with negligible benefit.

One detail worth noting: `re.split` with a capturing group (the `(#{1,3} .+)` pattern) interleaves the header lines with the section bodies in the output list. The headers don't get swallowed. This is intentional — you want `## Understanding eVars` to appear at the top of the chunk that explains eVars, not orphaned in a previous chunk or discarded entirely.

---

## Embeddings: Why Titan Embed v2

I'm using `amazon.titan-embed-text-v2:0` for embeddings. The choice comes down to three things.

**Credential continuity.** I already have AWS credentials for this project. Bedrock is the service I'm calling. Titan Embed is Amazon's first-party model, so it's not subject to the same Marketplace/AISPL restrictions that blocked me from using Anthropic's Claude through Bedrock (the root cause of the whole migration covered in Part 1). My Bedrock credentials work for Titan without any additional setup.

**Vector quality at reasonable size.** Titan Embed v2 produces 1024-dimensional vectors. That's large enough to capture semantic nuance in technical documentation — distinguishing "eVar expiration" from "prop traffic variable", for example — without being as expensive as 3072-dimensional models. The quality-to-cost ratio is good for a hobby project with a fixed corpus.

**Normalised vectors.** Passing `normalize: True` in the request means the returned embedding vectors are already L2-normalised. This matters because ChromaDB's HNSW index uses cosine similarity when configured with `hnsw:space: cosine`. Cosine similarity between two normalised vectors is equivalent to their dot product, which HNSW can compute efficiently. Without normalisation, you'd get slightly wrong similarity scores at the margin.

```python
def _get_titan_embedding(text: str, bedrock_client) -> list[float]:
    body = json.dumps({
        "inputText": text,
        "dimensions": 1024,
        "normalize": True
    })
    resp = bedrock_client.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(resp["body"].read())["embedding"]
```

One practical limit: Titan Embed v2 has an 8,000-character input cap. Long markdown files — some AEP reference pages are 12,000+ characters — get truncated before embedding. The chunking strategy mostly prevents this since chunks are targeted at 500 tokens (~2,000 characters), but I added an explicit `text[:8000]` guard in the ingest loop as a safety net.

---

## ChromaDB Collection Setup

ChromaDB is the local vector store. I chose it over alternatives (Pinecone, Weaviate, pgvector) specifically because I wanted zero infrastructure for the initial version. It's a Python package, persists to disk, and runs in-process with the FastAPI backend. No Docker, no managed service, no network hop on every retrieval.

The collection configuration:

```python
chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR),
    settings=ChromaSettings(anonymized_telemetry=False),
)
collection = chroma_client.get_or_create_collection(
    name="experience_league",
    metadata={"hnsw:space": "cosine"},
)
```

`PersistentClient` writes the index to `chroma_db/` at the project root. The FastAPI server reads from that path on startup, which means the knowledge base survives restarts. No re-embedding required unless you explicitly reset the collection with `--reset`.

The `hnsw:space: cosine` setting tells ChromaDB to build its HNSW graph using cosine distance. ChromaDB returns distances, not similarities — so at query time I convert: `score = 1.0 - dist`. For cosine distance ranging from 0 (identical) to 2 (opposite), this gives a similarity score between -1 and 1. In practice, with normalised vectors on domain-specific technical text, relevant chunks tend to score between 0.5 and 0.9.

The ingest script uses `collection.upsert()` rather than `collection.add()`. This is intentional: chunk IDs are deterministic strings of the form `{s3_key}#{chunk_index}`. Running the ingest script twice — say, after updating a few documents — doesn't duplicate chunks. Existing chunks get overwritten, new ones get added. This makes incremental updates straightforward.

---

## The Metadata Registry: 1,500 Documents

This is the least glamorous part of the entire system and probably the most important.

The problem: S3 keys look like this:
```
adobe-docs/adobe-analytics/help/admin/admin-console/admin-roles-in-analytics.md
```

The canonical URL for that document on Experience League looks like this:
```
https://experienceleague.adobe.com/en/docs/analytics/admin/admin-console/admin-roles-in-analytics
```

These two strings have almost nothing in common except the filename. The S3 key has `adobe-docs/adobe-analytics/help/` where the URL has `analytics/`. The S3 key ends in `.md` where the URL has no extension. The S3 key uses the full GitHub repo path structure; the URL uses a cleaned-up Experience League path.

Without a reliable mapping, the chatbot can cite a retrieved document, but the citation URL it generates will be wrong or missing. A wrong citation URL is worse than no citation — it destroys trust.

`data/metadata_registry.json` is a 1,500-entry JSON file where every S3 key maps to its full metadata:

```json
{
  "adobe-docs/adobe-analytics/help/admin/admin-console/admin-roles-in-analytics.md": {
    "title": "Administrator roles in Adobe Analytics",
    "experience_league_url": "https://experienceleague.adobe.com/en/docs/analytics/admin/admin-console/admin-roles-in-analytics",
    "github_url": "https://github.com/AdobeDocs/analytics.en/blob/master/help/admin/admin-console/admin-roles-in-analytics.md",
    "product": "Adobe Analytics",
    "doc_type": "Article",
    "role": "Admin",
    "level": "Beginner",
    "description": "Understand how to get started with Adobe Analytics, general role types, and logging in to the UI."
  }
}
```

The registry is built by `scripts/extract_metadata_from_s3.py`, which downloads each file from S3, parses the YAML frontmatter, extracts the H1 title as a fallback, and constructs the Experience League URL using a series of path transformation rules. It's not elegant code — there are several special-case branches for different repo structures — but it runs once and the output is stable.

At query time, the citation mapper uses the registry as a lookup table:

```python
def format_citation(doc_metadata: dict, doc_title: str = None) -> dict:
    source_path = extract_path_from_metadata(doc_metadata)
    metadata = lookup_metadata_by_path(source_path)

    if metadata:
        return {
            'url': metadata['experience_league_url'],
            'title': metadata['title'],
            'product': metadata['product'],
            'doc_type': metadata.get('doc_type', 'Article'),
            'score': doc_metadata.get('score', 0.0),
        }
    else:
        # Fallback: pattern-based URL construction
        return _create_fallback_citation(doc_metadata, score)
```

The fallback path exists for documents that aren't in the registry — it tries to reverse-engineer an Experience League URL from the S3 key path using regex substitutions. It works maybe 70% of the time. The registry-based path works 100% of the time. This is why building the registry first, before anything else, is the right order of operations.

The registry also stores `product`, `doc_type`, `role`, and `level` metadata, which the UI uses to show the document badge (Article, Tutorial, Video) and the audience tag (Admin, Developer, User). These come directly from the frontmatter that Adobe's technical writers maintain in the GitHub repos.

---

## Media Extraction: Videos and Screenshots

Plain text ingestion misses a significant portion of what makes documentation useful: screenshots showing exactly where a button is, and tutorial videos walking through the full workflow. Both exist in the markdown files. You just have to know where to look.

### Tutorial Videos

Customer Journey Analytics tutorial pages include an Adobe-flavoured video callout in the markdown body:

```yaml
---
title: Add area visualizations to Analysis Workspace
thumbnail: 334261.jpg
kt: 13401
---

>[!VIDEO](https://video.tv.adobe.com/v/3479637/?quality=12&learn=on)
```

The frontmatter `thumbnail` field is a bare filename. The `>[!VIDEO]` tag in the body contains the direct video URL.

The `scripts/ingest_with_media.py` script processes the ChromaDB collection after initial ingestion. Rather than going back to S3, it reads the document text that's already stored in ChromaDB and runs regex extraction over it:

```python
RE_VIDEO_TAG = re.compile(r">\[!VIDEO\]\(([^)]+)\)")
RE_THUMBNAIL = re.compile(r"^thumbnail:\s*(\S+)", re.MULTILINE)

def extract_media_from_markdown(content: str, s3_key: str) -> dict:
    media = {"thumbnail_url": None, "video_url": None, "image_urls": []}

    video_match = RE_VIDEO_TAG.search(content)
    if video_match:
        media["video_url"] = video_match.group(1).strip()

    thumb_match = RE_THUMBNAIL.search(content)
    if thumb_match:
        thumb_id = thumb_match.group(1).strip()
        media["thumbnail_url"] = f"https://cdn.experienceleague.adobe.com/thumb/{thumb_id}"

    return media
```

The thumbnail CDN URL pattern (`https://cdn.experienceleague.adobe.com/thumb/{filename}`) was reverse-engineered by inspecting Experience League pages in the browser. It's consistent across all products.

### Screenshot Images

Documentation images use relative paths:

```markdown
![Analysis Workspace panel](assets/freeform-table.png)
```

These need to be resolved to absolute GitHub CDN URLs to be surfaced in the chatbot UI. The S3 key structure maps directly to GitHub repos, so the resolution is a string transformation:

```python
GITHUB_RAW_BASES = {
    "adobe-docs/adobe-analytics/":
        "https://raw.githubusercontent.com/AdobeDocs/analytics.en/main/",
    "adobe-docs/customer-journey-analytics/":
        "https://raw.githubusercontent.com/AdobeDocs/analytics-platform.en/main/",
    "adobe-docs/experience-platform/":
        "https://raw.githubusercontent.com/AdobeDocs/experience-platform.en/main/",
}

def resolve_image_url(img_path: str, s3_key: str) -> str | None:
    if img_path.startswith("http"):
        return img_path

    for prefix, base in GITHUB_RAW_BASES.items():
        if s3_key.startswith(prefix):
            repo_path = s3_key[len(prefix):]
            doc_dir = (base + repo_path).rsplit("/", 1)[0] + "/"
            if img_path.startswith("/"):
                return base + img_path.lstrip("/")
            elif img_path.startswith("./"):
                return doc_dir + img_path[2:]
            else:
                return doc_dir + img_path
    return None
```

There's a gotcha that caused several hours of debugging: the AdobeDocs repos use `main` as the default branch, not `master`. GitHub raw content URLs are branch-sensitive — `raw.githubusercontent.com/AdobeDocs/analytics.en/master/...` will 404 for every image because `master` doesn't exist. Every image in the knowledge base was 404ing until I found this. The fix is the `main` in `GITHUB_RAW_BASES` above.

The media enrichment script runs a two-pass extraction per document. Frontmatter fields (`thumbnail`, `kt`) appear only in chunk 0 of each document. But screenshots appear throughout the body — in step-by-step procedures, in feature descriptions, in comparison tables. A first version of this script only searched chunk 0 for images and found 152 pages with screenshots. Searching all chunks tripled coverage to 402 pages. The updated logic:

```python
# Extract video + thumbnail from frontmatter (chunk 0 only)
media = extract_media_from_markdown(first_chunk["doc"], url, s3_key=s3_key)

# Extract images from ALL chunks (screenshots appear in body, not just frontmatter)
if len(media["image_urls"]) < 4:
    for chunk in all_chunks_for_url:
        if chunk["meta"].get("chunk_index", 0) == 0:
            continue  # already processed
        for m in RE_IMG_ALL.finditer(chunk["doc"]):
            resolved = resolve_image_url(m.group(2), chunk["meta"].get("s3_key", s3_key))
            if resolved and resolved not in media["image_urls"]:
                media["image_urls"].append(resolved)
            if len(media["image_urls"]) >= 4:
                break
```

The cap of 4 images per page is a practical limit for UI display, not a corpus limitation.

---

## The Final Numbers

After running the full ingestion pipeline — ingest to ChromaDB, then media enrichment — the knowledge base looks like this:

| Metric | Count |
|---|---|
| Total document chunks | 5,685 |
| Unique pages | 1,260 |
| Pages enriched with media | 539 |
| Pages with screenshot images | 402 |
| Pages with embedded videos | 138 |
| Knowledge base cutoff | March 14, 2026 |

Product breakdown from the metadata registry (1,500 entries, which includes some non-article files like `CODE_OF_CONDUCT.md` and API reference stubs that get filtered at ingest time):

- Adobe Analytics: 1,062 entries
- Adobe Experience Platform: 206 entries
- Analytics APIs: 95 entries
- Customer Journey Analytics: 137 entries

---

## What Retrieval Actually Looks Like

At query time, the `ChromaRetriever` class handles the full retrieval flow: embed the query with the same Titan model used at ingest time, query ChromaDB, filter by similarity threshold, and return structured results.

```python
class ChromaRetriever:
    def retrieve(
        self,
        query: str,
        n_results: int = 8,
        similarity_threshold: float = 0.2,
    ) -> list[dict]:
        embedding = _get_titan_embedding(query, self.bedrock)
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        output = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = 1.0 - dist  # cosine distance → similarity
            if score >= similarity_threshold:
                output.append({
                    "content": doc,
                    "score": score,
                    "metadata": meta,
                    "location": {"s3Location": {"uri": meta.get("s3_key", "")}},
                })
        return output
```

The `similarity_threshold=0.2` default was tuned empirically. It's lower than you might expect. Experience League documentation covers some genuinely niche topics — `prop` traffic variables, VISTA rules, the differences between `s.products` syntax variants — and the relevant chunks for these queries tend to score in the 0.3–0.5 range rather than 0.7+. Setting the threshold too high (0.4 was my first guess) caused the system to return empty results for legitimate technical questions. Too low, and you're injecting noise into the LLM context.

The `location` field preserves backward compatibility with the original Bedrock Knowledge Base response format. The upstream RAG pipeline was written against Bedrock's response schema; keeping that shape meant the rest of the pipeline needed no changes when I swapped in ChromaDB.

---

## What Wasn't Obvious Until Later

**Screenshot coverage.** My initial assumption was that frontmatter and the first chunk would contain all media references. Wrong. Screenshots appear throughout the body — sometimes 10 or 15 chunks into a long reference page. Searching only chunk 0 for images produced 152 enriched pages. Searching all chunks produced 402. The difference shows up noticeably in the UI.

**The `main` vs `master` branch issue.** Every GitHub raw content URL I was constructing pointed to `master`. The AdobeDocs repos had migrated to `main` at some point. All image 404s traced back to this single string. It took longer to find than I want to admit because the failure was silent — the `<img>` tags would just not render.

**Build the metadata registry before anything else.** When I first tested citations on the deployed app, the fallback URL construction was producing wrong URLs for about 30% of queries. The pattern-based construction gets confused by repos that don't follow a predictable path structure (the AEP repo is particularly inconsistent). The registry eliminates the problem entirely for every document it covers. If you're building something similar, do the registry first, not as an afterthought.

**S3 as the source of truth pays off immediately.** When I wanted to add AEP documents after the initial Analytics-only ingestion, I uploaded the new files to S3, added their entries to the metadata registry, and ran the ingest script with `--product "Adobe Experience Platform"`. The existing Analytics and CJA chunks were untouched. The S3-backed approach made incremental expansion straightforward from the start.

---

## Key Takeaways

- Documentation has logical structure; respect it in your chunking strategy. Header-based splits + paragraph-based fallback + hard-split escape hatch is a reasonable three-level approach.
- The `len(text) // 4` token approximation is good enough. Don't over-engineer it.
- Normalise your embedding vectors and set the vector store's distance metric to match. For cosine similarity with ChromaDB, that means `normalize: True` in the Titan request and `hnsw:space: cosine` in the collection metadata.
- Build the metadata registry before you build the UI. Wrong citation URLs are worse than no citation URLs.
- The `main` branch name: AdobeDocs repos don't use `master`. Every raw GitHub CDN URL you construct needs this to be right or images will silently fail.
- Search all chunks for images, not just chunk 0. Screenshots are in the body, not the frontmatter.

---

## What's Coming

- **Part 3** — The FastAPI backend: session management, the RAG pipeline, streaming responses, and the Strands multi-search agent that runs parallel retrieval across products.
- **Part 4** — The React frontend: why I migrated from Streamlit, the streaming UI, the citation card component, and the admin panel for monitoring query analytics.
- **Part 5** — Deployment, observability, and what I'd do differently: Railway vs ECS, feedback loops, auto-retraining hooks, and the MCP server I haven't built yet.
