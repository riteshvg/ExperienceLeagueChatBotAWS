# SECTION D: Integration - COMPLETE ✅

## ✅ D1: Imported citation_mapper in app.py

**Location**: `app.py` (lines 55-62)

**Code**:
```python
# Import citation mapper (new verified system)
try:
    from src.utils.citation_mapper import format_citation, map_to_experience_league_url
    CITATION_MAPPER_AVAILABLE = True
    print("✅ Citation mapper loaded successfully")
except ImportError as e:
    print(f"Warning: Citation mapper not available: {e}")
    CITATION_MAPPER_AVAILABLE = False
```

---

## ✅ D2: Found Document Processing Locations

**Location 1**: Main Chatbot (app.py:~2730-2760)
- After document retrieval
- After smart routing
- Before saving chat message

**Location 2**: Optimized Chatbot (app.py:~3190-3220)
- After streaming response
- After processing query
- Before saving chat message

---

## ✅ D3: Added Citation Formatting

### Implementation (Both Locations):
```python
# Add citations using new verified citation mapper
if CITATION_MAPPER_AVAILABLE and documents:
    try:
        citations = []
        for doc in documents:
            citation_info = format_citation(
                doc_metadata=doc,
                doc_title=None  # Will be extracted from metadata
            )
            citations.append(citation_info)
        
        if citations:
            # Format citations as markdown
            citations_markdown = "\n\n---\n\n### 📚 Sources\n\n"
            for idx, citation in enumerate(citations, 1):
                citations_markdown += f"{idx}. **[{citation['title']}]({citation['url']})** "
                citations_markdown += f"(Relevance: {citation['score']:.2%})"
                if citation.get('github_url'):
                    citations_markdown += f" • [View on GitHub →]({citation['github_url']})"
                citations_markdown += "\n"
            
            fixed_response += citations_markdown
            logger.info(f"Added {len(citations)} citations to response")
    except Exception as e:
        logger.error(f"Error adding citations: {e}")
```

---

## ✅ D4: Modified Response Structure

**Response Structure**:
- Response text (fixed markdown links)
- Citations section (appended as markdown)
- No structural changes to return values

**Citation Format**:
```markdown
---

### 📚 Sources

1. **[Segment Workflow](https://experienceleague.adobe.com/en/docs/analytics/components/segmentation/seg-workflow)** (Relevance: 85%) • [View on GitHub →](https://github.com/AdobeDocs/analytics.en/blob/master/help/components/segmentation/seg-workflow.md)
2. **[eVar](https://experienceleague.adobe.com/en/docs/analytics/components/dimensions/evar)** (Relevance: 78%) • [View on GitHub →](https://github.com/AdobeDocs/analytics.en/blob/master/help/components/dimensions/evar.md)
```

---

## ✅ D5: Updated Return Statements

**Changes**: None required
- Citations are appended to response text
- Return structure unchanged
- Backward compatible

---

## ✅ D6: Verified Backward Compatibility

**Compatibility Checks**:
- ✅ No changes to function signatures
- ✅ No changes to return types
- ✅ Citations appended to text (not separate field)
- ✅ Graceful error handling (logs error, continues)
- ✅ Feature flag controlled (CITATION_MAPPER_AVAILABLE)
- ✅ Existing code unaffected if citation mapper unavailable

**Integration Points**:
1. ✅ Main chatbot (lines 2736-2760)
2. ✅ Optimized chatbot (lines 3192-3216)

---

## 📊 SECTION D SUMMARY

### Files Modified:
- ✅ `app.py` (2 integration points)

### Changes Made:
- ✅ Imported citation_mapper functions
- ✅ Added citation formatting at both chatbot endpoints
- ✅ Maintained backward compatibility
- ✅ Added error handling and logging
- ✅ Feature flag controlled integration

### Integration Features:
- ✅ Automatic citation extraction
- ✅ Verified Experience League URLs
- ✅ GitHub fallback URLs
- ✅ Relevance scores displayed
- ✅ Readable titles
- ✅ Markdown formatting

---

## ✅ SECTION D COMPLETE!

**Next Steps**: Proceed to Section E (UI Updates)

