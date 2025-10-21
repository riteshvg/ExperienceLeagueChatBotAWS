# SECTION A: Discovery & Analysis - COMPLETE ✅

## A1: Citation-Related Code Locations ✅

### Found Citation System:
- **Primary File**: `src/utils/citation_manager.py` (already exists)
- **Integration Points**: `app.py` (2 locations)
- **Test File**: `test_citation_manager.py`

## A2: ALL Citation Generation Locations ✅

### Location 1: Main Chatbot (app.py:2728-2737)
```python
# Add citations if available
if CITATION_MANAGER_AVAILABLE and citation_manager and documents:
    try:
        citations = citation_manager.extract_citations(documents)
        if citations:
            # Format citations as markdown and append
            citations_markdown = citation_manager.format_citations_markdown(citations)
            fixed_response += citations_markdown
    except Exception as e:
        logger.error(f"Error adding citations: {e}")
```

### Location 2: Optimized Chatbot (app.py:3169-3178)
```python
# Add citations if available
if CITATION_MANAGER_AVAILABLE and citation_manager and result.get('documents'):
    try:
        citations = citation_manager.extract_citations(result['documents'])
        if citations:
            # Format citations as markdown and append
            citations_markdown = citation_manager.format_citations_markdown(citations)
            fixed_answer += citations_markdown
    except Exception as e:
        logger.error(f"Error adding citations: {e}")
```

## A3: Document Retrieval Structure ✅

### AWS Bedrock Knowledge Base Retrieve Response:
```python
response = bedrock_agent_client.retrieve(
    knowledgeBaseId=knowledge_base_id,
    retrievalQuery={'text': query},
    retrievalConfiguration={
        'vectorSearchConfiguration': {
            'numberOfResults': max_results
        }
    }
)

raw_results = response.get('retrievalResults', [])
```

### Retrieved Document Structure:
```python
{
    'content': {
        'text': 'Adobe Analytics eVars (conversion variables) are used to track...'
    },
    'score': 0.78,  # Similarity score (0-1)
    'location': {
        's3Location': {
            'uri': 's3://experienceleaguechatbot/adobe-docs/adobe-analytics/help/components/dimensions/evar.md'
        }
    }
}
```

### Available Metadata Fields:
- `content.text` - Document content
- `score` - Relevance score (float 0-1)
- `location.s3Location.uri` - S3 URI of source document
- `metadata` - Additional metadata (if present)

## A4: Current URL Construction Logic ✅

### Current Implementation (citation_manager.py):

**Step 1: Extract path from S3 URI**
```python
# Input: s3://experienceleaguechatbot/adobe-docs/adobe-analytics/help/components/dimensions/evar.md
# Extract: adobe-docs/adobe-analytics/help/components/dimensions/evar.md
```

**Step 2: Match prefix and strip**
```python
# Matched prefix: 'adobe-docs/adobe-analytics/help'
# Strip prefix: 'adobe-docs/adobe-analytics/help/'
# Result: components/dimensions/evar.md
```

**Step 3: Remove .md extension**
```python
# Result: components/dimensions/evar
```

**Step 4: Build URL**
```python
# Base URL: https://experienceleague.adobe.com/en/docs/analytics
# Final URL: https://experienceleague.adobe.com/en/docs/analytics/components/dimensions/evar
```

### Current URL Mappings:
```python
{
    'adobe-docs/adobe-analytics/help': {
        'base_url': 'https://experienceleague.adobe.com/en/docs/analytics',
        'strip_prefix': 'adobe-docs/adobe-analytics/help/'
    },
    'adobe-docs/customer-journey-analytics/help/cja-main': {
        'base_url': 'https://experienceleague.adobe.com/en/docs/analytics-platform',
        'strip_prefix': 'adobe-docs/customer-journey-analytics/help/cja-main/'
    },
    'aep': {
        'base_url': 'https://experienceleague.adobe.com/en/docs/experience-platform',
        'strip_prefix': 'aep/'
    },
    'adobe-docs/analytics-apis/docs': {
        'base_url': 'https://developer.adobe.com/analytics-apis/docs',
        'strip_prefix': 'adobe-docs/analytics-apis/docs/'
    }
}
```

## A5: Sample Retrieved Document ✅

### Complete Document Example:
```json
{
  "content": {
    "text": "Adobe Analytics eVars (conversion variables) are used to track custom values that persist across visits. eVars are great for tracking campaign performance, user journeys, and conversion attribution..."
  },
  "score": 0.7845231,
  "location": {
    "s3Location": {
      "uri": "s3://experienceleaguechatbot/adobe-docs/adobe-analytics/help/components/dimensions/evar.md"
    }
  }
}
```

### Transformed Citation:
```python
{
    'id': 1,
    'title': 'eVar',
    'experience_league_url': 'https://experienceleague.adobe.com/en/docs/analytics/components/dimensions/evar',
    'github_url': 'https://github.com/AdobeDocs/analytics.en/blob/master/help/components/dimensions/evar.md',
    's3_uri': 's3://experienceleaguechatbot/adobe-docs/adobe-analytics/help/components/dimensions/evar.md',
    'score': 0.7845231,
    'preview': 'Adobe Analytics eVars (conversion variables) are used to track custom values...'
}
```

---

## 🔍 IDENTIFIED ISSUES:

### Issue 1: CJA URL Mapping
- **Problem**: CJA documentation has been reorganized
- **Current**: `help/cja-main/` → `/en/docs/analytics-platform/`
- **May Need**: Different mapping logic for CJA

### Issue 2: Missing 'using/cja-' prefix for some CJA docs
- **Example**: Some CJA paths may require `/using/cja-{section}/` format

### Issue 3: No verification of generated URLs
- **Problem**: URLs are generated but not validated
- **Solution**: Need to add URL validation or fallback

---

## ✅ SECTION A COMPLETE!

**Next Steps**: Proceed to Section B (Create Citation Mapping Utilities)
