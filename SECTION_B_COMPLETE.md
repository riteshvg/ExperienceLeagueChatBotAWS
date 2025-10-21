# SECTION B: Create Citation Mapping Utilities - COMPLETE ✅

## ✅ B1: Created `src/utils/citation_mapper.py`

**File Location**: `src/utils/citation_mapper.py`
**Lines of Code**: ~450 lines
**Status**: ✅ Complete

---

## ✅ B2: Implemented `extract_path_from_metadata()`

**Function**: Extract file path from various metadata formats

**Supported Formats**:
- `location.s3Location.uri` (primary)
- `uri` (direct)
- `metadata.x-amz-bedrock-kb-source-uri` (AWS metadata)
- `source` (alternative)

**Example**:
```python
metadata = {
    'location': {
        's3Location': {
            'uri': 's3://bucket/adobe-docs/adobe-analytics/help/components/segments/seg-workflow.md'
        }
    }
}
path = extract_path_from_metadata(metadata)
# Returns: 'adobe-docs/adobe-analytics/help/components/segments/seg-workflow.md'
```

---

## ✅ B3: Implemented `map_to_experience_league_url()`

**Function**: Convert document metadata to valid Experience League URL

**Mapping Logic**:

### Adobe Analytics:
```
Input:  adobe-docs/adobe-analytics/help/components/segments/seg-workflow.md
Output: https://experienceleague.adobe.com/en/docs/analytics/components/segments/seg-workflow
```

### Customer Journey Analytics:
```
Input:  adobe-docs/customer-journey-analytics/help/cja-main/data-views/create-dataview.md
Output: https://experienceleague.adobe.com/en/docs/analytics-platform/data-views/create-dataview
```

### Adobe Experience Platform:
```
Input:  aep/sources/connectors/adobe-applications/analytics.md
Output: https://experienceleague.adobe.com/en/docs/experience-platform/sources/connectors/adobe-applications/analytics
```

### Analytics APIs:
```
Input:  adobe-docs/analytics-apis/docs/2.0/getting-started.md
Output: https://developer.adobe.com/analytics-apis/docs/2.0/getting-started
```

**Features**:
- ✅ Removes `help/` prefix
- ✅ Removes `.md` extension
- ✅ Product-specific transformations
- ✅ Fallback URL for unknown formats

---

## ✅ B4: Implemented `extract_title_from_metadata()`

**Function**: Extract document title from metadata

**Title Extraction Priority**:
1. `metadata.title` field (if exists)
2. First markdown heading from content (`# Title`)
3. Generated from filename

**Example**:
```python
title = extract_title_from_metadata(doc_metadata)
# Returns: "Segment Workflow" (from seg-workflow.md)
```

**Title Formatting**:
- Converts dashes/underscores to spaces
- Title case
- Fixes Adobe terms: CJA, AA, AEP, eVar, API

---

## ✅ B5: Implemented `format_citation()`

**Function**: Returns formatted citation dict

**Output Structure**:
```python
{
    'url': 'https://experienceleague.adobe.com/en/docs/analytics/...',
    'title': 'Segment Workflow',
    'display': 'Source: Segment Workflow (Relevance: 85%)',
    'score': 0.85,
    'github_url': 'https://github.com/AdobeDocs/analytics.en/blob/master/...',
    'path': 'adobe-docs/adobe-analytics/help/...'
}
```

---

## ✅ B6: Edge Case Handling

**Implemented**:
1. ✅ Missing metadata → Fallback URL
2. ✅ Invalid S3 URI → Return None
3. ✅ Unknown path format → Fallback to Analytics URL
4. ✅ Multiple path prefixes supported
5. ✅ URL-encoded paths → Decoded
6. ✅ Missing title → Generate from filename
7. ✅ API documentation paths → developer.adobe.com
8. ✅ Learn/tutorial paths → Standard mapping

**Fallback Strategy**:
```python
if not path:
    return "https://experienceleague.adobe.com/en/docs/analytics"
```

---

## ✅ B7: Logging Throughout

**Logging Levels**:
- `DEBUG`: Input/output for each function
- `INFO`: Successful mappings and generated URLs
- `WARNING`: Fallback usage, missing metadata
- `ERROR`: Exceptions and failures

**Example Log Output**:
```
2025-10-21 14:00:00 - citation_mapper - DEBUG - Extracted path: adobe-docs/adobe-analytics/help/components/segments/seg-workflow.md
2025-10-21 14:00:00 - citation_mapper - INFO - Adobe Analytics mapping: adobe-docs/adobe-analytics/help/components/segments/seg-workflow.md → https://experienceleague.adobe.com/en/docs/analytics/components/segments/seg-workflow
2025-10-21 14:00:00 - citation_mapper - INFO - Generated citation: Segment Workflow → https://experienceleague.adobe.com/en/docs/analytics/components/segments/seg-workflow
```

---

## 📊 SECTION B SUMMARY

### Files Created:
- ✅ `src/utils/citation_mapper.py` (450+ lines)

### Functions Implemented:
- ✅ `extract_path_from_metadata()` - Extract path from various metadata formats
- ✅ `map_to_experience_league_url()` - Main URL mapping logic
- ✅ `extract_title_from_metadata()` - Title extraction with fallbacks
- ✅ `format_citation()` - Complete citation formatting
- ✅ `_extract_path_from_s3_uri()` - Helper for S3 URI parsing
- ✅ `_map_adobe_analytics_url()` - AA-specific mapping
- ✅ `_map_cja_url()` - CJA-specific mapping
- ✅ `_map_aep_url()` - AEP-specific mapping
- ✅ `_map_analytics_api_url()` - API docs mapping
- ✅ `_generate_github_url()` - GitHub URL generation

### Features:
- ✅ Multi-format metadata support
- ✅ Product-specific URL transformations
- ✅ Comprehensive logging
- ✅ Edge case handling
- ✅ Fallback strategies
- ✅ Title generation
- ✅ GitHub URL support

---

## ✅ SECTION B COMPLETE!

**Next Steps**: Proceed to Section C (Testing)
