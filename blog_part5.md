# Building the Experience League Unofficial Chatbot — Part 5: UX Features, Media, Smart Enhancements, and What's Next

**Part 5 of 5 | thelearningproject.in**

---

This is the final post in the series. Parts 1 through 4 covered the forcing function (AISPL billing that locked me out of AWS Bedrock), the data pipeline and metadata registry, migrating the stack from Streamlit to React + FastAPI + ChromaDB, and the two-path RAG architecture with a Haiku LCEL chain, a Sonnet LangGraph agent, and a smart router sitting in front of both. If you haven't read those, the short version: 5,685 chunks, 1,260 pages, 539 with embedded media, all living in a local ChromaDB instance, served through a FastAPI backend over SSE, rendered in React.

Part 5 is about everything that sits on top of the retrieval machinery: the UX features that make the chatbot feel like more than a glorified `grep`, the lessons that only surfaced after real use, and the honest assessment of where the project still falls short.

---

## 1. Inline Media — Making Docs Come Alive

The single biggest differentiator from a plain text chatbot is that Experience League documentation is rich with screenshots and short tutorial videos. Surfacing those inline in the answer — right next to the step they illustrate — is not a nice-to-have. It's the whole point of having a documentation chatbot rather than a search engine.

The pipeline for this has four distinct stages.

**Stage 1: Ingest.** During the S3 extraction and ChromaDB ingest, each chunk is stored with three media fields in its metadata: `image_urls` (a JSON array of screenshot URLs), `video_url` (the Adobe TV embed URL if the page has a tutorial video), and `thumbnail_url` (the video poster image). These come directly from the Experience League page structure — the scraper walks the HTML and pulls them out during the metadata enrichment step.

**Stage 2: Retrieval.** After the retriever returns documents, the Haiku path calls a helper function that assembles a media context block appended to the retrieved text before it goes to the model:

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
        lines.append("Images (use ![alt](url) markdown):")
        for url in images:
            lines.append(f"  - {url}")
    if videos:
        lines.append("Videos (embed as [▶ Watch: Short Title](url)):")
        for v in videos:
            lines.append(f"  - {v['title']} → {v['url']}")
    return "\n".join(lines)
```

Caps at four images and two videos. Without the cap, a response about a complex CJA topic would drag in every screenshot from every retrieved chunk — ten images, three videos, the model buries the prose in media links. The cap forces the model to be selective.

**Stage 3: The system prompt instruction.** The constraint isn't enough; you have to tell the model what to do with the media and, critically, where to place it:

```
Media embedding rules:
- If images are provided in the context, embed them inline using: ![description](url)
- Place each image immediately after the paragraph or step it illustrates.
- If a video is provided, embed it as a link inline: [▶ Watch: Brief Title](video_url)
- Place media naturally where it helps comprehension — NOT grouped at the end.
- Only include media that directly illustrates the point being made.
```

The "NOT grouped at the end" constraint took two iterations to get right. The first version of the instruction produced responses that answered the question correctly then dumped all four images in a block at the bottom. That's not inline; that's an appendix.

**Stage 4: React renderers.** ReactMarkdown's default `img` and `a` components don't know the difference between a regular hyperlink and an Adobe TV embed URL. The custom renderers in `ChatMessage.tsx` handle both:

```tsx
img: ({ src, alt }) => {
  if (!src) return null
  return (
    <a href={src} target="_blank" rel="noopener noreferrer" className="block my-3">
      <img
        src={src}
        alt={alt ?? ''}
        className="rounded-lg border border-slate-200 max-h-64 object-contain w-full"
        onError={(e) => {
          (e.currentTarget.closest('a') as HTMLElement).style.display = 'none'
        }}
      />
    </a>
  )
},
a: ({ href, children }) => {
  if (href && VIDEO_URL_RE.test(href)) {
    const match = href.match(/video\.tv\.adobe\.com\/v\/([^/?]+)/)
    if (match) {
      const videoId = match[1]
      const label = String(children).replace(/^▶\s*Watch:\s*/i, '').trim()
      if (message.streaming) {
        return (
          <span className="inline-flex items-center gap-2 ...">
            <Play className="w-3 h-3 text-red-400 fill-red-400 flex-shrink-0" />
            <span>{label || 'Watch video'}</span>
          </span>
        )
      }
      const embedUrl = `https://video.tv.adobe.com/v/${videoId}?autoplay=0&hidetitle=true`
      return (
        <span className="block my-3 rounded-xl overflow-hidden border border-slate-200 not-prose w-1/2">
          {label && (
            <span className="flex items-center gap-2 px-3 py-2 bg-slate-50 ...">
              <Play className="w-3 h-3 text-red-500 fill-red-500" />
              {label}
            </span>
          )}
          <span className="block relative w-full" style={{ paddingBottom: '56.25%' }}>
            <iframe src={embedUrl} className="absolute inset-0 w-full h-full"
              frameBorder="0" allow="autoplay; fullscreen" allowFullScreen title={label} />
          </span>
        </span>
      )
    }
  }
  return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
},
```

Two things worth noting in that renderer. First, the `onError` handler on the `img` element: Experience League screenshots occasionally return 404s when Adobe restructures their CDN. Rather than rendering a broken image icon, the handler walks up the DOM and hides the entire anchor wrapper. Second, the streaming check on the video renderer: during active streaming, the response is incomplete. An `iframe` rendered mid-stream would flicker — it would appear, disappear as the surrounding markdown re-parses, then reappear. The fix is to render a placeholder badge during streaming and only upgrade to the full embed after the `done` event fires.

---

## 2. Rendering Adobe-Specific Markup

Experience League markdown uses several Adobe-proprietary syntax extensions. They render fine on the Experience League site, which has custom plugins to handle them. They look like garbage in a standard ReactMarkdown renderer.

Three specific patterns needed handling:

- `[!UICONTROL Analytics]` — wraps a UI label. Should render as an inline code badge.
- `[!DNL Analysis Workspace]` — "Do Not Localize" wrapper for a product name. Should render as bold.
- `>[!NOTE]` / `>[!IMPORTANT]` — callout box syntax embedded in blockquotes.

The solution is a pre-processing function applied to message content before it hits ReactMarkdown:

```typescript
function sanitizeAdobeMarkup(text: string): string {
  return text
    .replace(/\[!UICONTROL\s+([^\]]+)\]/g, '`$1`')
    .replace(/\[!DNL\s+([^\]]+)\]/g, '**$1**')
    .replace(/>\[!(IMPORTANT|NOTE|TIP|WARNING)\]\s*/g, '> **$1:** ')
}
```

Without this, a response about navigating the Analytics Admin console looks like:

> Go to [!UICONTROL Analytics] > [!UICONTROL Admin] > [!UICONTROL Report Suites]

With it:

> Go to `Analytics` > `Admin` > `Report Suites`

It's a small thing, but the raw Adobe markup was actually appearing in LLM responses because the retrieved chunks contained it verbatim. The model would faithfully reproduce the markup from the source material rather than stripping it. Sanitization at the render layer is the right fix — you don't want to strip it from the stored chunks because you'd lose context about what's a UI element versus what's body text.

---

## 3. The Follow-Up Question System

After each response completes streaming, the store fires a non-blocking call to generate three contextual follow-up questions using Haiku. The implementation is intentionally simple:

```python
@router.post("/chat/follow-ups")
async def get_follow_ups(body: FollowUpsRequest):
    client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    prompt = (
        f"Based on this question and answer, suggest exactly 3 concise follow-up questions "
        f"a user might ask next. Return only the 3 questions as a JSON array of strings, "
        f"nothing else.\n\nQuestion: {body.query}\n\nAnswer summary: {body.answer[:500]}"
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

The `re.search` for the JSON array instead of a direct `json.loads` is defensive programming. Haiku occasionally adds a sentence before the array ("Here are three follow-up questions:"), which would cause a parse error. The regex extracts the array regardless of leading text.

On the frontend side, the call happens in the `finally` block of `sendMessage`, after streaming is complete:

```typescript
// After streaming: generate follow-up questions (non-blocking)
const finalMsg = get().sessions[get().activeSessionId]?.messages
  .find((m) => m.id === assistantId)
if (finalMsg && finalMsg.content && !finalMsg.content.startsWith('Error:')) {
  getFollowUps(query, finalMsg.content).then((follow_ups) => {
    if (follow_ups.length > 0) {
      set((s) => ({
        sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
          msgs.map((m) => (m.id === assistantId ? { ...m, follow_ups } : m))
        ),
      }))
    }
  })
}
```

No `await`, no blocking. The main message is already on screen by the time this fires. The follow-up chips appear about 1-2 seconds later with a subtle fade-in, below the citations. Clicking a chip calls `onFollowUpClick(q)` which pre-fills the input — but does not auto-submit, because occasionally the suggested follow-up needs editing.

---

## 4. The Feedback Loop

Every completed assistant message gets thumbs up/down buttons in the footer row alongside the model badge and copy button. Feedback is stored as newline-delimited JSON in `data/feedback.jsonl`:

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
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return {"status": "ok"}
```

The `query` field deserves a note. The initial implementation passed it directly from the feedback button click handler in `ChatMessage.tsx`, which meant passing `message.content` down from the parent — but at the time of a feedback click, what you want is the preceding user message, not the assistant's response. The first version stored an empty string for `query` because the frontend didn't have a clean way to walk backwards to the user message.

The fix ended up being in the Zustand store, not the component:

```typescript
setFeedback: (messageId, rating, _query) => {
  const { activeSessionId, sessions } = get()
  const msgs = sessions[activeSessionId]?.messages ?? []
  const idx = msgs.findIndex((m) => m.id === messageId)
  const precedingQuery = idx > 0 ? msgs[idx - 1].content : ''
  submitFeedback(messageId, activeSessionId, rating, precedingQuery).catch(() => {})
  // update local state...
},
```

The store already has the full message list. Finding the message at `idx` and reading `msgs[idx - 1].content` is the correct place to resolve this — the component doesn't need to know anything about message ordering. The `_query` parameter from the component is ignored; the store resolves it internally.

---

## 5. LangSmith Integration — Observability in Production

LangSmith tracing is configured entirely through environment variables (`LANGCHAIN_API_KEY`, `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_PROJECT`). Because the pipeline uses LangChain LCEL and LangGraph throughout, tracing is fully automatic — no decorators, no wrappers, no instrumentation code. Every retrieval call, every LLM generation, every tool invocation shows up in the LangSmith UI as a structured trace.

In the first week of real use, the most valuable trace caught a retrieval contamination bug. A query about CJA Data Views was returning an answer that mixed in some details from Adobe Analytics Virtual Report Suites. Looking at the LangSmith trace, the first `search_documentation` call from the LangGraph agent had retrieved three VRS chunks from the Analytics corpus alongside the CJA Data View chunks — they scored closely enough to pass the similarity threshold because both concepts involve "filtered views of data."

The fix was adding "Customer Journey Analytics" to the query expansion logic in `QueryProcessor` for any query containing "data view" without an explicit product qualifier. The expansion is applied before both the Haiku and Sonnet retrieval paths, so both benefit from it.

LangSmith also makes the smart router's behavior visible. You can filter traces by the `model` field in the `done` event and see exactly which queries went to Haiku versus Sonnet, what the token counts were on each path, and where retrieval latency lived. For this deployment, ChromaDB retrieval consistently clocks in at 150-300ms — fast enough that it doesn't noticeably affect the perceived first-token latency.

---

## 6. The Prompt Library

The sidebar contains a collapsible prompt library — 23 curated prompts across four categories: Adobe Analytics, Customer Journey Analytics, Adobe Experience Platform, and Comparisons.

```typescript
export const PROMPT_LIBRARY: PromptCategory[] = [
  {
    category: 'Adobe Analytics',
    prompts: [
      { id: 'aa-1', title: 'Create a segment',
        text: 'How do I create a segment in Adobe Analytics?' },
      { id: 'aa-2', title: 'Calculated metrics',
        text: 'How do I create a calculated metric in Adobe Analytics?' },
      { id: 'aa-3', title: 'Attribution IQ',
        text: 'What is Attribution IQ and how does it work in Adobe Analytics?' },
      // ...
    ],
  },
  // CJA, AEP, Comparisons categories follow
]
```

The sidebar renders these as a two-level accordion — top level is product category, second level is individual prompts. Click a prompt title and `onSelectPrompt(text)` fires, which calls `inputRef.current?.fill(text)` in the ChatPage — pre-filling the input without auto-submitting.

There's a design decision baked into the prompt library that isn't obvious from the code: the prompts are intentionally written to align with the smart router's classification logic. Procedural prompts ("How do I create...") route to Sonnet. Definitional prompts ("What is...", "What are...") route to Haiku. The prompt library is effectively a curated demonstration of the router's behavior — it shows users representative question patterns for each product and, as a side effect, exercises both RAG paths with well-formed queries.

---

## 7. What the Knowledge Base Cutoff Means in Practice

The knowledge base has a hard cutoff of March 14, 2026. Adobe's documentation is a living target — UI screenshots change when Adobe redesigns navigation, feature pages appear or disappear with product releases, API endpoint references get versioned.

In practice, the content that goes stale quickly is a smaller slice than it first appears:

**Goes stale:** UI screenshots (Adobe redesigns surfaces regularly), new feature availability (CJA in particular ships often), specific API endpoint references.

**Stays stable:** Conceptual explanations, fundamental workflows, architecture and data model documentation, historical feature descriptions. For a practitioner trying to understand how identity resolution works in AEP or what the difference is between a CJA Connection and a Data View, the answer from a March 2026 knowledge base is still correct in June.

My rough estimate is that the stable content covers 70-80% of what practitioners actually ask. The long tail — "what changed in the April 2026 release", "does CJA now support X" — is where it fails. The fix is an automated weekly data refresh: delta sync from the AdobeDocs GitHub repositories using file modification timestamps, re-ingest only changed files, re-run media enrichment. The ingest scripts already exist; the sync script and the GitHub Actions workflow are the missing pieces.

---

## 8. What's Next

**Automated data refresh (highest priority).** The two missing pieces are a `scripts/sync_docs_to_s3.py` delta sync script and a `.github/workflows/refresh-docs.yml` scheduled workflow. The former reads last-modified timestamps from the GitHub API and only downloads files that changed since the last run. The latter calls the former on a weekly schedule. Both are straightforward to build; they're just not built yet.

**MCP server (~60 lines, not yet built).** The plan is to expose the ChromaDB knowledge base as an MCP server so the retrieval capability is available directly in Claude Code or any MCP-compatible IDE:

```python
# Planned: backend/mcp_server.py
from mcp import FastMCP

mcp = FastMCP("experience-league-docs")

@mcp.tool()
def search_experience_league(query: str) -> str:
    """Search Adobe Experience League documentation"""
    docs = retriever.retrieve(query, n_results=5)
    return format_results(docs)
```

Deploy it alongside the FastAPI backend, share the URL, and anyone can add it to `~/.claude/settings.json` once and get grounded Adobe doc answers in their IDE. The appeal is that the same ChromaDB knowledge base that powers the chatbot would also power inline documentation lookups during implementation work — the two use cases converge on the same retrieval backend.

**More products.** Marketo, Workfront, Target, Adobe Campaign — none are in the current knowledge base. The ingest pipeline is product-agnostic. Adding a new product is: add the GitHub repo to the S3 sync list, add entries to the metadata registry, run the ingest script with `--product "Adobe Marketo"`. The architecture already supports it.

**Hybrid search.** The current pipeline uses pure dense vector search with Amazon Titan Embed. Dense retrieval excels at semantic similarity — "how do I configure attribution" finds relevant chunks even if the exact words don't appear in the query. But it underperforms on exact-match lookups: a specific eVar number, a precise API endpoint path, an exact error code. A hybrid approach combining dense retrieval with BM25 keyword matching would handle both modes. The architecture has a clear injection point for this at the retriever layer.

---

## 9. Lessons Learned Across the Full Build

I find end-of-series lessons sections useful when they're honest and specific rather than generic. Here are the ones that actually changed how I think about this kind of project:

- **The AISPL forcing function was a net positive.** Getting locked out of AWS Bedrock for a billing verification issue forced a migration that produced a better architecture. ChromaDB is faster for local development, easier to inspect, and free. The Anthropic API is less operationally complex than Bedrock. Sometimes the constraint is the improvement.

- **Build the metadata registry before the UI.** The citation system — showing users which specific Experience League pages an answer drew from — only works because there's a clean mapping from ChromaDB chunk IDs to canonical Experience League URLs. Building the metadata registry in Part 2, before writing a single line of frontend code, meant the citation UI in Part 3 had clean data to work with. If you're building a RAG chatbot, the URL mapping question should be the first thing you resolve, not the last.

- **The content blocks streaming bug cost two days.** Claude's API, when used with tool calling enabled (as in the LangGraph ReAct agent), returns `content` as a list of typed blocks — `[{"type": "text", "text": "..."}]` — rather than a plain string. The initial streaming handler assumed a string and got empty output for every Sonnet response. The fix is a four-line type check, but finding it required understanding the difference between LCEL streaming and LangGraph `astream_events` streaming. The distinction is documented but not prominently.

- **The video flicker fix was about the streaming lifecycle, not CSS.** Videos rendering mid-stream caused visible flickering because the iframe would appear, the surrounding markdown would re-parse as more tokens arrived, and the iframe URL would change. The fix — render a placeholder badge during streaming, upgrade to the iframe only after the `done` event — required understanding that the `streaming` boolean on a message is the authoritative signal for render mode, not any CSS animation property.

- **`main` vs `master` bites you once and only once.** GitHub Actions workflows that reference the wrong default branch silently do nothing. After spending time debugging a CI workflow that wasn't running, the lesson is: always check `git remote show origin | grep HEAD` before wiring up any branch-based automation.

- **Follow-up query contextualization is a retrieval problem, not a UX problem.** Short follow-up questions like "how does that work?" or "what about the API?" require the previous conversation turn to be meaningful. The `_contextualize_query` function in the pipeline that prepends the preceding user message for short follow-ups improved retrieval quality significantly for multi-turn conversations. This is a retrieval concern — the LLM handles conversational context fine through the history; it's ChromaDB that doesn't have access to the conversation.

- **Set your similarity threshold lower than you think you need to.** The instinct is to set it high to avoid irrelevant results. In practice, a high threshold makes the system reply "I don't have information about that" for questions that are perfectly answerable — the relevant chunk scores 0.62 instead of 0.68 and gets filtered. The current threshold of 0.35 is more permissive than it sounds because ChromaDB cosine similarity scores don't have the same semantic meaning as they would in a normalized space. Tune empirically against real queries, not intuition.

- **What you actually need before building the UI:** a working chunk-to-URL mapping (the citation system fails without it), at least 50 test queries with known answers to validate retrieval quality against, and clarity on your similarity threshold. Build the backend, run 50 queries in a notebook, inspect what gets retrieved and what doesn't, then build the frontend. Doing it the other way — building the UI first and hoping retrieval works — produces a chatbot that looks correct until a real user tries it.

---

## Key Takeaways: Full Series

1. Dense vector search on 5,685 chunks is fast enough (150-300ms retrieval) that the user-perceived latency is dominated by LLM generation, not retrieval.
2. Two models behind one router are better than one model everywhere. Haiku handles definitions and lookups at a fraction of the cost; Sonnet handles procedures and comparisons where depth matters.
3. SSE streaming from FastAPI to React over `fetch` with an `AsyncGenerator` is operationally simpler than WebSockets and sufficient for this use case.
4. Zustand with `persist` middleware handles multi-session state cleanly; `partialize` controls what gets written to localStorage so you don't accidentally persist runtime flags.
5. LangSmith tracing with LangChain LCEL and LangGraph is zero-configuration and extremely valuable — the CJA Data View retrieval contamination bug would have taken much longer to diagnose without it.
6. Adobe-specific markup (`[!UICONTROL]`, `[!DNL]`) in retrieved chunks will appear verbatim in model responses. Sanitize at the render layer, not the storage layer.
7. The follow-up question system should be non-blocking and visually deferred — it should never affect main response latency.
8. Media embedding requires instruction (where to place it) not just capability (knowing the URLs exist). The system prompt constraint "not grouped at the end" is load-bearing.
9. A metadata registry built before the UI is infrastructure, not overhead.
10. The knowledge base cutoff is a product decision. Be explicit about it to users, and build the refresh pipeline before it matters.

---

## Closing

This is a personal learning project. It works well enough that I use it daily for Experience League questions — questions I used to answer by either searching the documentation site directly or asking Perplexity and hoping it had indexed the right page. The chatbot is faster for the kind of procedural, multi-step questions that documentation answers well but search engines answer poorly.

The "unofficial" framing is intentional and non-negotiable. This is not an Adobe product. Adobe has not reviewed it, endorsed it, or in any way touched it. The documentation it indexes is publicly available; the chatbot just provides a different interface to content that already exists. But it should never be mistaken for something Adobe built or maintains.

For anyone building something similar on a different documentation corpus: the architecture is not the hard part. The hard part is the data layer — the chunking strategy, the URL mapping, the metadata registry, the similarity threshold experiments. Get that right and the LLM work is mostly prompt engineering. Get it wrong and no amount of model capability compensates for retrieving the wrong chunks.

The most transferable lessons from this project: control your chunking so chunk boundaries respect semantic units, not arbitrary character counts. Build your URL mapping before your UI, or your citations will be wrong and you'll rebuild the frontend after the fact. And set your similarity threshold lower than you think you need to.

---

*Ritesh G is a data engineer at Adobe. thelearningproject.in is where he writes about things he's building to learn.*
