# Building the Experience League Unofficial Chatbot
## A 5-Part Technical Series
### thelearningproject.in | Ritesh G

---

> **Note:** This is an unofficial personal project. Not an Adobe product, not endorsed by Adobe.

---

# Part 1: The Idea and the Architecture

**Part 1 of 5** | *thelearningproject.in*

---

I've been an Adobe engineer for a while now, which means I've spent more hours than I care to count navigating Experience League documentation. Not because the docs are bad — they're actually quite good. The problem is scale. Adobe's product surface is enormous: Analytics, Customer Journey Analytics, Experience Platform, Journey Optimizer, Real-Time CDP, and a dozen others, each with hundreds of documentation pages. When a colleague asks "how do I set up cross-device attribution in CJA?" or "what's the difference between a Profile Dataset and an Event Dataset in AEP?", the honest answer is usually "let me go dig through the docs for 20 minutes."

That's the itch I wanted to scratch. This post is the first in a five-part series documenting how I built an unofficial RAG chatbot for Adobe Experience League — from the initial architecture to the React frontend, including the wrong turns and the unexpected obstacles.

---

## The Problem Worth Solving

Adobe Experience League hosts genuinely excellent documentation. But "comprehensive" and "easy to navigate" are not the same thing.

The workflow for most Adobe practitioners looks like this: you have a specific question. You go to Experience League. You use the search, which works for exact-match queries but starts to fall apart for conceptual or procedural questions. You click through three or four results. Two of them aren't quite what you needed. You refine. You try again. By the time you have an answer, you've spent 15–25 minutes on something that, with the right tool, should have taken two.

Cross-product questions are particularly painful. A CDP implementation touching AEP, Analytics, and AJO simultaneously requires fluency across three separate documentation sets with different terminology and different structural conventions. There's often no single page that answers the question you actually have.

The goal: build something that lets you ask natural language questions against the full corpus of Experience League documentation and get grounded, cited answers. Not summaries hallucinated from training data — actual answers backed by specific documentation pages.

---

## The First Architecture (and Its Problems)

My initial instinct was to stay fully within AWS. The first architecture was:

- **Streamlit** for the UI
- **AWS Bedrock Knowledge Base** with OpenSearch Serverless for vector search
- **Claude 3 via Bedrock** — Haiku for simple queries, Sonnet for complex ones
- A single `app.py` that wired everything together

This worked. For a few weeks it worked quite well. But the seams started showing quickly.

**Streamlit's limits.** Building streaming responses that feel natural, maintaining conversation history, rendering markdown with inline images, adding feedback mechanisms — each pushed against Streamlit's model. Every interaction reruns the script from top to bottom. That's fine for dashboards. It's not fine for conversational UI.

**Bedrock KB abstracted too much.** Limited control over chunking strategy, limited ability to tune similarity thresholds, inconsistent citation quality.

**The monolith problem.** By the time I had query routing, conversation memory, a custom prompt system, citation extraction, and admin tooling wired together, `app.py` was sitting at **3,700 lines**.

---

## The Migration Decision: React + FastAPI + ChromaDB

**React + TypeScript + Vite** for the frontend. Proper component model, TypeScript type safety, **Zustand** for state management (lightweight, right-sized for this application).

**FastAPI** for the backend. Async-native — critical for streaming token-by-token over Server-Sent Events while ChromaDB does vector lookups in the background.

**ChromaDB (local embedded)** replacing Bedrock KB. Runs in-process with FastAPI, persists to disk, complete control over chunking strategy, embedding model, similarity thresholds, metadata schema, retrieval count.

```
backend/        # FastAPI app, RAG pipeline, smart router
frontend/       # React/Vite app
src/            # Shared utilities: citation mapper, query processor
data/           # ChromaDB persistence, metadata registry
scripts/        # Ingestion and maintenance scripts
```

```
┌─────────────────────────┐
│  Frontend (React/Vite)  │
│  Zustand + ReactMarkdown│
└────────────┬────────────┘
             │ SSE / POST /api/chat
┌────────────▼────────────┐
│   FastAPI Backend        │
│   Smart Router           │
└────┬─────────┬──────────┘
     │         │
┌────▼───┐ ┌───▼──────────────────┐
│ChromaDB│ │ LangChain LCEL /      │
│(local) │ │ LangGraph ReAct Agent │
└────────┘ └──────────┬───────────┘
                      │
          ┌───────────▼───────────┐
          │  Anthropic API         │
          │  (Claude Sonnet 4.6)   │
          └───────────┬───────────┘
                      │
          ┌───────────▼───────────┐
          │  AWS Bedrock           │
          │  (Titan Embed v2 only) │
          └───────────────────────┘
```

---

## The AWS AISPL Problem — The Unexpected Pivot

My plan was to call Claude through AWS Bedrock. I got:

```
botocore.exceptions.ClientError: An error occurred (AccessDeniedException)
when calling the InvokeModelWithResponseStream operation:
Model access is denied due to INVALID_PAYMENT_INSTRUMENT
```

After investigation: my AWS account is registered under **AISPL — Amazon Internet Services Private Limited** — the Indian entity through which AWS operates in India. Anthropic's models on Bedrock are distributed through the AWS Marketplace. AISPL accounts cannot subscribe to third-party Marketplace offerings. This is a hard restriction, not a configuration problem.

```bash
aws bedrock get-foundation-model-availability \
  --model-id anthropic.claude-sonnet-4-6 \
  --region us-east-1
# → agreementAvailability.status: NOT_AVAILABLE
```

The fix — use the Anthropic API directly:

```python
# Before: AWS Bedrock (blocked for AISPL accounts)
import boto3
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
response = bedrock.invoke_model(
    modelId='us.anthropic.claude-sonnet-4-20250514-v1:0',
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}],
    })
)

# After: Anthropic API directly
from anthropic import AsyncAnthropic
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
async with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=4000,
    messages=[{"role": "user", "content": prompt}]
) as stream:
    async for chunk in stream.text_stream:
        yield chunk
```

**Titan Embed v2 still runs on Bedrock** — Amazon's first-party models are not affected by the AISPL restriction.

### Update — June 2026: The AISPL Restriction Is Now Resolved

After this project was built, Amazon released **Global Cross-Region Inference (CRIS)** for Bedrock, which specifically addresses the AISPL limitation. Customers operating from `ap-south-1` (Mumbai) and `ap-south-2` (Hyderabad) can now access Claude models by using **Global inference profile IDs** — prefixed with `global.` instead of `us.`:

```python
# Now works from India via Global CRIS
bedrock = boto3.client('bedrock-runtime', region_name='ap-south-1')
resp = bedrock.converse(
    modelId='global.anthropic.claude-sonnet-4-6',
    messages=[{'role': 'user', 'content': [{'text': 'Hello'}]}],
    inferenceConfig={'maxTokens': 50}
)
```

To enable this, navigate to **Amazon Bedrock → Inference profiles** in the Mumbai console and look for profiles starting with `global.`. You'll also need to apply the three-part IAM policy for Global CRIS.

This project continues to use the direct Anthropic API — it works cleanly, requires no additional IAM configuration, and gives immediate access to the latest models. But if you're building in India and prefer to keep everything on AWS, Global CRIS is now the right path.

---

## A Query's Journey Through the Final Architecture

```python
@router.post("/chat")
async def chat(body: ChatRequest, pipeline: RAGPipeline, session_store: SessionStore):
    session_id = body.session_id or session_store.new_session()
    async def event_generator():
        async for event in pipeline.stream(query=body.query, session_id=session_id):
            yield {"data": json.dumps(event)}
    return EventSourceResponse(event_generator())
```

```typescript
export async function* streamChat(query: string, sessionId: string): AsyncGenerator<SSEEvent> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, session_id: sessionId }),
  })
  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line.startsWith('data: ')) yield JSON.parse(line.slice(6)) as SSEEvent
    }
  }
}
```

---

## Key Takeaways

- Streamlit's ceiling is real — not the right foundation for a polished conversational UI
- Abstraction has a cost — Bedrock KB gets you started fast but limits retrieval control
- AISPL accounts cannot use third-party Bedrock Marketplace models — hard restriction, no workaround
- Monoliths are fine until they're not — 3,700 lines was the signal
- The forced pivot improved the architecture — Anthropic API is cleaner and has better model availability

*Part 2: Building the Knowledge Base — corpus extraction, chunking strategy, and the metadata registry.*

---

---

# Part 2: Building the Knowledge Base — Corpus, Chunking, and the Metadata Registry

**Part 2 of 5** | *thelearningproject.in*

---

A RAG system is only as good as what you put into it. The retrieval can be perfect, the LLM prompt can be beautifully engineered, and the UI can be polished — but if the knowledge base has bad chunks, wrong URLs, or no metadata, the whole thing falls apart at query time. I spent more time on this layer than on everything else combined, and most of that time was on problems I didn't anticipate.

---

## Where the Data Comes From

Adobe open-sources all Experience League documentation on GitHub under the `AdobeDocs` organisation:

- `AdobeDocs/analytics.en` — Adobe Analytics (~964 unique pages)
- `AdobeDocs/analytics-platform.en` — Customer Journey Analytics (~136 pages)
- `AdobeDocs/experience-platform.en` — Adobe Experience Platform (~160 pages)

The pipeline: GitHub repos → S3 bucket (`experienceleaguechatbot`) → ChromaDB. S3 as an intermediate store means I've already filtered out non-documentation files once. The knowledge base cutoff is clearly defined as the last S3 sync date (March 14, 2026 in the current build).

---

## The Chunking Strategy

The naive approach — split every N characters with some overlap — produces bad retrieval for documentation. A procedure might span 800 tokens across seven numbered steps. Split that mid-step and you get semantically useless chunks.

Three-level strategy:

1. **Split on H2/H3 headers first** — the natural unit of documentation
2. **If a section exceeds 500 tokens, split on paragraph boundaries**
3. **If a paragraph still exceeds the limit, hard-split with overlap** (50-token overlap)

```python
def split_markdown(text: str, s3_key: str) -> list[str]:
    CHUNK_SIZE = 500
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
            paragraphs = [p.strip() for p in part.split("\n\n") if p.strip()]
            para_buf = ""
            for para in paragraphs:
                c2 = (para_buf + "\n\n" + para).strip() if para_buf else para
                if _rough_token_count(c2) <= CHUNK_SIZE:
                    para_buf = c2
                else:
                    if para_buf:
                        chunks.append(para_buf)
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

Token approximation: `len(text) // 4`. Rough but fast — exact counts don't matter as much as keeping logical units intact.

---

## Embeddings: Why Titan Embed v2

`amazon.titan-embed-text-v2:0`: credential continuity (first-party AWS, not AISPL-affected), 1024-dimensional vectors, and normalised output (`normalize: True`) for correct cosine similarity with ChromaDB's HNSW index.

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

---

## ChromaDB Collection Setup

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

`upsert()` not `add()` — chunk IDs are deterministic (`{s3_key}#{chunk_index}`), so running the ingest script twice doesn't duplicate chunks.

---

## The Metadata Registry: 1,500 Documents

S3 key: `adobe-docs/adobe-analytics/help/admin/admin-console/admin-roles-in-analytics.md`
EL URL: `https://experienceleague.adobe.com/en/docs/analytics/admin/admin-console/admin-roles-in-analytics`

These have almost nothing in common. Without a mapping, citation URLs are wrong. A wrong citation URL is worse than no citation — it destroys trust.

```json
{
  "adobe-docs/adobe-analytics/help/admin/admin-console/admin-roles-in-analytics.md": {
    "title": "Administrator roles in Adobe Analytics",
    "experience_league_url": "https://experienceleague.adobe.com/en/docs/analytics/admin/admin-console/admin-roles-in-analytics",
    "product": "Adobe Analytics",
    "doc_type": "Article",
    "role": "Admin",
    "level": "Beginner"
  }
}
```

The fallback (pattern-based URL construction) is wrong ~30% of the time. The registry is right 100% of the time. **Build the registry before you build the UI.**

---

## Media Extraction: Videos and Screenshots

CJA tutorial pages include video callouts in the markdown:

```yaml
---
thumbnail: 334261.jpg
---
>[!VIDEO](https://video.tv.adobe.com/v/3479637/?quality=12&learn=on)
```

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

Screenshot images use relative paths resolved to GitHub CDN URLs:

```python
GITHUB_RAW_BASES = {
    "adobe-docs/adobe-analytics/":
        "https://raw.githubusercontent.com/AdobeDocs/analytics.en/main/",
    "adobe-docs/customer-journey-analytics/":
        "https://raw.githubusercontent.com/AdobeDocs/analytics-platform.en/main/",
    "adobe-docs/experience-platform/":
        "https://raw.githubusercontent.com/AdobeDocs/experience-platform.en/main/",
}
```

**Critical gotcha:** AdobeDocs repos use `main`, not `master`. Using `master` causes every image URL to silently 404.

**Two-pass image search:** Screenshots appear throughout body chunks, not just chunk 0. Searching all chunks increased image coverage from 152 → 402 pages.

---

## Final Numbers

| Metric | Count |
|---|---|
| Total document chunks | 5,685 |
| Unique pages | 1,260 |
| Pages with media | 539 |
| Pages with screenshots | 402 |
| Pages with videos | 138 |
| Knowledge base cutoff | March 14, 2026 |

---

## Key Takeaways

- Respect document structure in chunking: header → paragraph → hard-split with overlap
- `len(text) // 4` token approximation is good enough — don't over-engineer it
- Normalise embedding vectors and match ChromaDB distance metric (`hnsw:space: cosine`)
- Build the metadata registry before building the UI — wrong citation URLs destroy trust
- AdobeDocs repos use `main` not `master` — every raw GitHub CDN URL depends on this
- Search all chunks for images, not just chunk 0 — screenshots are in the body

*Part 3: The RAG Pipeline with LangChain — LCEL chain, LangGraph agent, smart routing, and LangSmith.*

---

---

# Part 3: The RAG Pipeline — LangChain LCEL, LangGraph Agent, Smart Routing, and LangSmith

**Part 3 of 5** | *thelearningproject.in*

---

The first version of the pipeline was embarrassing. A single ChromaDB retrieval, a single prompt, a single Claude call. It charged Sonnet-level tokens for "What is a segment?" and gave shallow answers for "How do I create a derived field in CJA that extracts UTM parameters?" Those two queries don't belong in the same pipeline.

---

## Two Pipelines for the Price of One

- **Haiku + single-pass LangChain LCEL chain** — definitions, conceptual questions, simple lookups
- **Sonnet + LangGraph ReAct agent** — procedural, multi-step, comparison, and creation tasks

The smart router decides which path every query takes before any LLM call happens.

---

## The Smart Router

```python
import re

_CREATION_VERBS = re.compile(
    r'\b(create|build|set up|setup|configure|implement|migrate|integrate|'
    r'design|develop|deploy|install|enable|connect|map|transform|ingest|'
    r'calculate|define metric|define segment|add|remove|delete|update|edit)\b',
    re.IGNORECASE,
)

_SONNET_OVERRIDE = re.compile(
    r'\b(how does .+ work|when should i|which is better|pros and cons|'
    r'trade.?off)\b',
    re.IGNORECASE,
)

_DEFINITION_PATTERNS = re.compile(
    r'^(what is|what are|what does|define|explain|describe|tell me about|'
    r'what does .+ mean)',
    re.IGNORECASE,
)

def classify_query(query: str) -> str:
    q = query.strip()
    word_count = len(q.split())

    is_definition = bool(_DEFINITION_PATTERNS.match(q))
    has_creation = bool(_CREATION_VERBS.search(q))
    has_override = bool(_SONNET_OVERRIDE.search(q))

    # Definition queries → Haiku, even long ones
    if is_definition and not has_creation and word_count <= 25:
        return "haiku"

    # Comparison / mechanism questions → Sonnet
    if has_override:
        return "sonnet"

    # Creation verbs → Sonnet
    if has_creation:
        return "sonnet"

    # Long multi-part questions → Sonnet
    if word_count > 12:
        return "sonnet"

    return "haiku"
```

The evaluation order matters: `_DEFINITION_PATTERNS` is checked before `_SONNET_OVERRIDE`. "What is the difference between a metric and a calculated metric?" starts with "what is" — it's a lookup, not a procedure.

---

## The Haiku Pipeline: LangChain LCEL

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

_HAIKU_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert Adobe Experience League documentation assistant.
Give thorough, step-by-step answers grounded in the retrieved documentation below.

Media embedding rules:
- Embed images inline using: ![description](url)
- Embed videos inline using: [▶ Watch: Brief Title](video_url)
- Place media naturally after the relevant paragraph.

Retrieved documentation context:
{context}"""),
    MessagesPlaceholder("history"),
    ("human", "{query}"),
])

def _build_haiku_chain(api_key: str):
    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        api_key=api_key,
        max_tokens=2000,
        streaming=True,
    )
    return _HAIKU_PROMPT | llm | StrOutputParser()
```

`MessagesPlaceholder("history")` injects session turns as typed `HumanMessage`/`AIMessage` objects — the LLM sees them as real conversation context.

---

## The Follow-Up Query Problem

When a user asks "How do I create one?" after "What is a Connection in CJA?", ChromaDB receives "How do I create one?" and finds nothing relevant.

```python
_FOLLOWUP_PATTERNS = re.compile(
    r'\b(it|this|that|one|them|they|those|these|the same|the above|'
    r'do so|how do i|can i|steps|process)\b',
    re.IGNORECASE,
)

def _contextualize_query(query: str, history: list[dict]) -> str:
    if not history or not _FOLLOWUP_PATTERNS.search(query):
        return query

    last_user = next(
        (t["content"] for t in reversed(history) if t["role"] == "user"),
        None,
    )
    if last_user and len(query.split()) <= 12:
        return f"{last_user} — {query}"

    return query
```

"How do I create one?" becomes "What is a Connection in CJA? — How do I create one?" — ChromaDB finds exactly the right documents.

---

## The Sonnet Pipeline: LangGraph ReAct Agent

```python
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

def _make_search_tool(retriever, query_processor, settings, citations_out: list):
    @tool
    def search_documentation(query: str) -> str:
        """
        Search Adobe Experience League documentation for the given query.
        Call multiple times with refined queries if needed.
        """
        enhanced, _ = query_processor.preprocess_query(query)
        docs = retriever.retrieve(enhanced, n_results=settings.max_retrieval_results,
                                  similarity_threshold=settings.similarity_threshold)
        if not docs:
            return f"No documentation found for: {query}"

        parts = []
        for i, doc in enumerate(docs, 1):
            meta = doc.get("metadata", {})
            title = meta.get("title", f"Document {i}")
            c = format_citation(doc, doc_title=title)
            if c.get("url", "").startswith("https://experienceleague.adobe.com"):
                if c not in citations_out:
                    citations_out.append(c)
            block = f"[{i}] {title}\n{doc['content']}"
            if meta.get("video_url"):
                block += f"\nVideo: {meta['video_url']} (Title: {title})"
            parts.append(block)

        return "\n\n---\n\n".join(parts)

    return search_documentation

agent = create_react_agent(
    ChatAnthropic(model="claude-sonnet-4-6", api_key=api_key, max_tokens=4000, streaming=True),
    tools=[search_tool],
    prompt=SystemMessage(content=_AGENT_SYSTEM),
)
```

**Note:** `state_modifier` was renamed to `prompt` in LangGraph ≥1.0. All older examples use the old name.

---

## The Streaming Gotcha with Tool Use

When Claude uses tools, the Anthropic API returns content as a **list of typed blocks**, not a plain string:

```python
# What we assumed:
chunk.content = "Here is how to create..."

# What Claude actually returns during tool use:
chunk.content = [{"type": "text", "text": "Here is how to create..."}]
```

The fix:

```python
if isinstance(content, list):
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "")
            if text:
                yield {"type": "token", "content": text}
elif isinstance(content, str) and content:
    yield {"type": "token", "content": content}
```

This only surfaces for queries complex enough to trigger tool use. Test explicitly with multi-search agent queries.

---

## The SSE Event Protocol

```python
{"type": "token",     "content": "Here is how to create..."}
{"type": "citations", "citations": [{"url": "...", "title": "Build Segments", "score": 0.82}]}
{"type": "done",      "model": "sonnet", "session_id": "abc123"}
{"type": "error",     "message": "Agent stream error: ..."}
```

With streaming, you can't retroactively change a 200 to a 500 when an error occurs. Typed `error` events handle this cleanly.

---

## LangSmith for Observability

Zero instrumentation — purely environment variables at FastAPI startup:

```python
def _configure_langsmith() -> None:
    s = get_settings()
    if s.langchain_tracing_v2 and s.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = s.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = s.langchain_project
        os.environ["LANGCHAIN_ENDPOINT"] = s.langchain_endpoint
```

What traces reveal: the agent's multi-search behavior, retrieval latency from ChromaDB (150-300ms), which path (Haiku/Sonnet) each query took, and exactly which documents were retrieved.

---

## Key Takeaways

- Route by intent, not by user preference — regex-based smart router before any LLM call
- Multi-turn retrieval needs explicit query contextualization — pronoun resolution is not automatic
- `chunk.content` is a list of blocks during tool use, not a string — handle both
- LangSmith tracing is free observability if you're already using LangChain/LangGraph
- Similarity threshold 0.2 not 0.4 — niche docs score lower than expected
- `state_modifier` was renamed to `prompt` in LangGraph 1.0

*Part 4: The React Frontend — streaming UI, Zustand state, multi-session history, and inline media rendering.*

---

---

# Part 4: The React Frontend — State, Streaming, and UX

**Part 4 of 5** | *thelearningproject.in*

---

By the time the FastAPI backend was working, the Streamlit frontend was already showing its seams in three specific ways: the execution model (full script rerun per token), multi-turn state management (brittle `st.session_state` manipulation), and custom components (citation pills, inline video embeds, feedback buttons — each required fighting the layout model or writing a Streamlit component in React anyway).

---

## Zustand for Chat State

Early version: flat `messages: Message[]`. Problem: new chat wiped history. Current design: sessions map with active session pointer.

```typescript
export interface ChatSession {
  id: string
  title: string          // first user message, truncated to 45 chars
  messages: Message[]
  createdAt: number
}

interface ChatState {
  sessions: Record<string, ChatSession>
  activeSessionId: string
  isStreaming: boolean
  error: string | null

  sendMessage: (query: string) => Promise<void>
  setFeedback: (messageId: string, rating: 1 | -1, query: string) => void
  startNewChat: () => void
  switchSession: (id: string) => void
  deleteSession: (id: string) => void
}
```

The `patchActiveMessages` helper handles the three levels of spreading:

```typescript
function patchActiveMessages(
  sessions: Record<string, ChatSession>,
  activeId: string,
  updater: (msgs: Message[]) => Message[],
): Record<string, ChatSession> {
  const session = sessions[activeId]
  if (!session) return sessions
  const messages = updater(session.messages)
  return {
    ...sessions,
    [activeId]: { ...session, messages, title: deriveTitle(messages) },
  }
}
```

Persistence with `partialize` — only sessions and activeSessionId, not transient state. Store version 2 with migration from flat messages shape.

---

## SSE Streaming in the Store

```typescript
sendMessage: async (query: string) => {
  const { activeSessionId, isStreaming } = get()
  if (!query.trim() || isStreaming) return
  set({ error: null })

  const userMsg: Message = { id: makeId(), role: 'user', content: query }
  const assistantId = makeId()
  const assistantMsg: Message = { id: assistantId, role: 'assistant', content: '', streaming: true }

  set((s) => ({
    isStreaming: true,
    sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) => [
      ...msgs, userMsg, assistantMsg,
    ]),
  }))

  try {
    for await (const event of streamChat(query, activeSessionId, false)) {
      if (!get().isStreaming) break
      if (event.type === 'token') {
        set((s) => ({
          sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
            msgs.map((m) => m.id === assistantId
              ? { ...m, content: m.content + event.content } : m)
          ),
        }))
      } else if (event.type === 'citations') {
        set((s) => ({
          sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
            msgs.map((m) => m.id === assistantId ? { ...m, citations: event.citations } : m)
          ),
        }))
      } else if (event.type === 'done') {
        set((s) => ({
          sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
            msgs.map((m) => m.id === assistantId
              ? { ...m, streaming: false, model: event.model } : m)
          ),
        }))
      }
    }
  } finally {
    set({ isStreaming: false })
    // Non-blocking follow-up generation
    const finalMsg = get().sessions[get().activeSessionId]?.messages
      .find((m) => m.id === assistantId)
    if (finalMsg?.content && !finalMsg.content.startsWith('Error:')) {
      getFollowUps(query, finalMsg.content).then((follow_ups) => {
        if (follow_ups.length > 0) {
          set((s) => ({
            sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
              msgs.map((m) => m.id === assistantId ? { ...m, follow_ups } : m)
            ),
          }))
        }
      })
    }
  }
},
```

---

## The ChatMessage Component

**Adobe markup sanitization:**
```typescript
function sanitizeAdobeMarkup(text: string): string {
  return text
    .replace(/\[!UICONTROL\s+([^\]]+)\]/g, '`$1`')
    .replace(/\[!DNL\s+([^\]]+)\]/g, '**$1**')
    .replace(/>\[!(IMPORTANT|NOTE|TIP|WARNING)\]\s*/g, '> **$1:** ')
}
```

**Video flicker prevention** — ReactMarkdown re-renders all renderers on every token. Iframes re-mount on every token. Fix: static pill while streaming, real iframe after:

```typescript
// While streaming: no iframe
if (message.streaming) {
  return (
    <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg
      bg-slate-50 border border-slate-200 text-xs font-medium text-slate-500">
      <Play className="w-3 h-3 text-red-400 fill-red-400" />
      <span>{label || 'Watch video'}</span>
    </span>
  )
}
// After streaming: full 16:9 responsive iframe
const embedUrl = `https://video.tv.adobe.com/v/${videoId}?autoplay=0&hidetitle=true`
return (
  <span className="block my-3 rounded-xl overflow-hidden border border-slate-200 w-1/2">
    <span className="block relative w-full" style={{ paddingBottom: '56.25%' }}>
      <iframe src={embedUrl} className="absolute inset-0 w-full h-full"
        frameBorder="0" allow="autoplay; fullscreen" allowFullScreen />
    </span>
  </span>
)
```

**Confidence badge** — avg top-3 citation scores:
- ≥ 0.70: green "High confidence"
- 0.50–0.70: amber "Medium confidence"
- < 0.50: orange "Low confidence"

---

## ChatInput + `useImperativeHandle`

```typescript
export interface ChatInputHandle {
  fill: (text: string) => void
  focus: () => void
}

useImperativeHandle(ref, () => ({
  fill: (text: string) => {
    setValue(text)
    textareaRef.current?.focus()
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height =
        `${Math.min(textareaRef.current.scrollHeight, 160)}px`
    }
  },
  focus: () => textareaRef.current?.focus(),
}))
```

**Auto-focus after response:**
```typescript
useEffect(() => {
  if (!isStreaming && messages.length > 0) {
    inputRef.current?.focus()
  }
}, [isStreaming, messages.length])
```

---

## Key Takeaways

- Zustand is right for this scale — Redux ceremony not worth it for a single-domain store
- `patchActiveMessages` pattern — write it once, use for all nested message updates
- `for await` on an async generator is the clean way to consume SSE in a store
- ReactMarkdown re-renders on every token — design around it for stateful renderer elements
- Adobe's `[!UICONTROL]` and `[!DNL]` markup must be sanitized before rendering
- `useImperativeHandle` for custom ref handles — annotate `useRef` in parent, not child
- Non-blocking follow-up generation: `.then()` in `finally` block, not `await`

*Part 5: UX features, the media pipeline, feedback loop, and what's left to build.*

---

---

# Part 5: UX Features, Media, and What's Next

**Part 5 of 5** | *thelearningproject.in*

---

Parts 1 through 4 covered the forcing function (AISPL billing), the data pipeline and metadata registry, the stack migration, and the two-path RAG architecture. Part 5 is about everything that sits on top: UX features, the media pipeline, LangSmith in production, and the honest accounting of what's still missing.

---

## 1. Inline Media — Making Documentation Come Alive

Four distinct stages:

**Stage 1: Ingest.** `scripts/ingest_with_media.py` writes `image_urls`, `video_url`, and `thumbnail_url` to ChromaDB chunk metadata, extracted from markdown frontmatter (`>[!VIDEO]` tags, `thumbnail:` field) and body image references resolved to GitHub CDN URLs.

**Stage 2: Context injection.** A media context block appended to the retrieved text before it reaches Claude:

```python
def _build_media_context(docs: list[dict]) -> str:
    images, videos = [], []
    seen_imgs, seen_vids = set(), set()
    for doc in docs:
        meta = doc.get("metadata", {})
        raw = meta.get("image_urls", "")
        if raw:
            try:
                for url in json.loads(raw):
                    if url not in seen_imgs and len(images) < 4:
                        images.append(url); seen_imgs.add(url)
            except Exception:
                pass
        v = meta.get("video_url", "")
        if v and v not in seen_vids and len(videos) < 2:
            videos.append({"url": v, "title": meta.get("title", "Video")}); seen_vids.add(v)
    if not images and not videos:
        return ""
    lines = ["\n---\nAvailable media — embed inline where relevant:"]
    if images:
        lines.append("Images (use ![alt](url) markdown inline):")
        for url in images: lines.append(f"  - {url}")
    if videos:
        lines.append("Videos (embed as [▶ Watch: Short Title](url)):")
        for v in videos: lines.append(f"  - {v['title']} → {v['url']}")
    return "\n".join(lines)
```

**Stage 3: System prompt instruction.** "Place media naturally after the relevant paragraph — NOT grouped at the end." The "NOT grouped at the end" constraint is load-bearing.

**Stage 4: React renderers.** Custom `img` and `a` components in ReactMarkdown — `onError` hides broken images, streaming check prevents iframe flickering (covered in Part 4).

---

## 2. Adobe-Specific Markup Rendering

```typescript
function sanitizeAdobeMarkup(text: string): string {
  return text
    .replace(/\[!UICONTROL\s+([^\]]+)\]/g, '`$1`')
    .replace(/\[!DNL\s+([^\]]+)\]/g, '**$1**')
    .replace(/>\[!(IMPORTANT|NOTE|TIP|WARNING)\]\s*/g, '> **$1:** ')
}
```

Sanitize at the render layer, not the storage layer. You don't want to strip it from stored chunks — you'd lose context about what's a UI element versus body text.

---

## 3. The Follow-Up Question System

```python
@router.post("/chat/follow-ups")
async def get_follow_ups(body: FollowUpsRequest):
    client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    prompt = (
        f"Based on this question and answer, suggest exactly 3 concise follow-up questions "
        f"a user might ask next. Return only the 3 questions as a JSON array of strings.\n\n"
        f"Question: {body.query}\n\nAnswer summary: {body.answer[:500]}"
    )
    resp = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip()
    match = re.search(r'\[.*?\]', raw, re.DOTALL)
    follow_ups = json.loads(match.group()) if match else []
    return {"follow_ups": follow_ups[:3]}
```

`.then()` not `await` — fires in the store's `finally` block after streaming completes, zero effect on response latency. ~$0.001 per query on Haiku.

---

## 4. The Feedback Loop

```python
@router.post("/chat/feedback")
async def submit_feedback(body: FeedbackRequest):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message_id": body.message_id,
        "session_id": body.session_id,
        "rating": body.rating,      # 1 = thumbs up, -1 = thumbs down
        "query": body.query,
    }
    with open(FEEDBACK_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return {"status": "ok"}
```

`query` resolved in the store from the preceding user message — not passed from the UI component:

```typescript
setFeedback: (messageId, rating, _query) => {
  const msgs = sessions[activeSessionId]?.messages ?? []
  const idx = msgs.findIndex((m) => m.id === messageId)
  const precedingQuery = idx > 0 ? msgs[idx - 1].content : ''
  submitFeedback(messageId, activeSessionId, rating, precedingQuery).catch(() => {})
},
```

---

## 5. LangSmith in Production

After the first week of real use, LangSmith caught a retrieval contamination bug: queries about CJA Data Views were returning Analytics Virtual Report Suite content. Both topics share vocabulary. The trace showed exactly which documents were retrieved and their scores. Fix: add "Customer Journey Analytics" to query expansion for anything containing "data view" without a product qualifier.

Routing accuracy from traces: ~40% Haiku, ~60% Sonnet. Average cost ~$0.009/query.

---

## 6. What's Not Yet Built

**Automated data refresh** — two scripts needed:
1. `scripts/sync_docs_to_s3.py` — delta sync from AdobeDocs GitHub repos to S3
2. `.github/workflows/refresh-docs.yml` — weekly scheduled workflow

**MCP server (~60 lines):**

```python
from mcp import FastMCP

mcp = FastMCP("experience-league-docs")

@mcp.tool()
def search_experience_league(query: str) -> str:
    """Search Adobe Experience League documentation for the given query."""
    docs = retriever.retrieve(query, n_results=5, similarity_threshold=0.2)
    parts = []
    for doc in docs:
        meta = doc.get("metadata", {})
        parts.append(f"**{meta.get('title', 'Document')}**\n{doc['content'][:800]}")
    return "\n\n---\n\n".join(parts) if parts else "No relevant documentation found."
```

Deploy alongside FastAPI. Add URL to `~/.claude/settings.json` once. Adobe doc answers directly in the IDE.

**More products** — Marketo, Workfront, Target, Campaign. Pipeline is product-agnostic; the metadata registry work is the hard part.

---

## 7. Lessons Learned Across the Full Series

- **The AISPL restriction was the best thing that happened to this project.** Forced a better architecture — direct Anthropic API is cleaner than Bedrock for Claude.
- **The metadata registry is more valuable than the retrieval algorithm.** Build URL mapping before building the UI.
- **Set similarity threshold lower than you think.** 0.2, not 0.4 — niche technical docs score in the 0.3–0.5 range.
- **The content block streaming bug is a category.** Any code assuming `chunk.content` is a string breaks with tool use. Test with tool-using agents explicitly.
- **Multi-turn retrieval needs explicit query contextualization.** Six lines of code, but you have to know to write them.
- **`main` vs `master` on GitHub silently 404s everything.** Build URL validation into your ingest pipeline.
- **LangSmith from day one, not week three.** Traces reveal what logs cannot.
- **Non-blocking UX additions are nearly free.** Design the response handler to support post-stream hooks from the start.

---

## Key Takeaways: Full Series

1. Dense vector search on 5,685 chunks is fast enough (150–300ms) that latency is dominated by LLM generation, not retrieval
2. Two models behind one router beat one model everywhere — Haiku for lookups, Sonnet for procedures
3. SSE streaming from FastAPI to React over `fetch` with `AsyncGenerator` is simpler than WebSockets
4. Zustand with `persist` and `partialize` handles multi-session state cleanly
5. LangSmith tracing with LangChain LCEL and LangGraph is zero-configuration and extremely valuable
6. Adobe-specific markup (`[!UICONTROL]`, `[!DNL]`) in retrieved chunks appears verbatim in model responses — sanitize at render layer
7. Follow-up questions should be non-blocking and visually deferred — never affect main response latency
8. Media embedding requires placement instructions, not just URL availability
9. A metadata registry built before the UI is infrastructure, not overhead
10. The knowledge base cutoff is a product decision — be explicit about it, build the refresh pipeline before it matters

---

## Closing

This is a personal learning project. It works well enough that I use it daily for Experience League questions.

The "unofficial" framing is intentional and non-negotiable. This is not an Adobe product. The documentation it indexes is publicly available; the chatbot just provides a different interface to content that already exists. But it should never be mistaken for something Adobe built or maintains.

For anyone building something similar: control your chunking strategy, build your URL mapping before your UI, calibrate similarity thresholds empirically, and trace with LangSmith from the moment you have a working retrieval path.

---

*Ritesh G is a data engineer at Adobe. thelearningproject.in is where he writes about things he's building to learn.*
