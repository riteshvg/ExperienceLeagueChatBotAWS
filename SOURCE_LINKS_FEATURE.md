# 📚 Source Links Feature

## Overview

The chatbot now automatically extracts and displays links to Experience League articles in every response. When users ask questions, the chatbot will:

1. **Retrieve relevant documents** from the Knowledge Base
2. **Extract source URLs** from document metadata (S3 locations)
3. **Convert S3 paths** to proper Experience League article URLs
4. **Display links** below each response in the chat interface

## How It Works

### Backend Processing

1. **Document Retrieval**: When a query is processed, documents are retrieved from the Knowledge Base
2. **URL Extraction**: The `extract_source_url()` function extracts the S3 URI from each document's metadata
3. **URL Conversion**: S3 paths are converted to Experience League URLs:
   - `s3://bucket/adobe-docs/adobe-analytics/help/...` → `https://experienceleague.adobe.com/docs/analytics/...`
   - `s3://bucket/adobe-docs/customer-journey-analytics/...` → `https://experienceleague.adobe.com/docs/customer-journey-analytics/...`
   - `s3://bucket/adobe-docs/experience-platform/...` → `https://experienceleague.adobe.com/docs/experience-platform/...`
4. **Link Formatting**: Links are formatted with titles extracted from document content
5. **Response Enhancement**: Source links are included in the API response

### Frontend Display

1. **Link Rendering**: The `ChatMessage` component displays source links below assistant responses
2. **Visual Design**: Links are shown in a dedicated section with:
   - Clear "📚 Related Articles:" heading
   - Clickable links with external icon
   - Proper styling and hover effects
3. **User Experience**: Users can click links to open Experience League articles in new tabs

## Implementation Details

### Backend Files Modified

1. **`backend/app/services/chat_helpers.py`**
   - Added `extract_source_url()` function
   - Added `extract_source_links()` function

2. **`backend/app/services/chat_service.py`**
   - Updated to extract source links from documents
   - Enhanced context with source links for model
   - Included source links in response

3. **`backend/app/models/schemas.py`**
   - Added `SourceLink` model
   - Updated `ChatResponse` to include `source_links` field

4. **`backend/app/api/v1/chat.py`**
   - Updated to return source links in responses
   - Included source links in streaming responses

### Frontend Files Modified

1. **`frontend/src/components/ChatMessage.tsx`**
   - Added source links display section
   - Styled links with Material-UI components
   - Added external link icons

2. **`frontend/src/services/api.ts`**
   - Updated `ChatResponse` interface to include `source_links`

3. **`frontend/src/pages/ChatPage.tsx`**
   - Updated to pass source links to message metadata

## URL Mapping

The system maps S3 paths to Experience League URLs:

| S3 Path Pattern | Experience League URL |
|----------------|----------------------|
| `adobe-docs/adobe-analytics/...` | `https://experienceleague.adobe.com/docs/analytics/...` |
| `adobe-docs/customer-journey-analytics/...` | `https://experienceleague.adobe.com/docs/customer-journey-analytics/...` |
| `adobe-docs/analytics-apis/...` | `https://experienceleague.adobe.com/docs/analytics/apis/...` |
| `adobe-docs/experience-platform/...` | `https://experienceleague.adobe.com/docs/experience-platform/...` |

## Example Response

When a user asks: *"How do I create a segment in Adobe Analytics?"*

The chatbot will respond with:
- The answer text
- Below the answer, a section showing:
  ```
  📚 Related Articles:
  • Creating Segments: https://experienceleague.adobe.com/docs/analytics/components/segmentation/...
  • Segment Builder Guide: https://experienceleague.adobe.com/docs/analytics/components/segmentation/...
  ```

## Benefits

1. **Transparency**: Users can see the source of information
2. **Verification**: Users can verify answers by reading original articles
3. **Learning**: Users can explore related documentation
4. **Trust**: Source citations increase trust in the chatbot
5. **Navigation**: Direct links to relevant Experience League content

## Testing

To test the feature:

1. **Start the application**:
   ```bash
   # Backend
   cd backend && source ../venv/bin/activate && uvicorn app.main:app --reload
   
   # Frontend
   cd frontend && npm run dev
   ```

2. **Ask a question** in the chat interface

3. **Verify** that source links appear below the response

4. **Click links** to ensure they open correct Experience League articles

## Future Enhancements

Potential improvements:

1. **Link Ranking**: Prioritize most relevant links
2. **Link Descriptions**: Add brief descriptions for each link
3. **Link Categories**: Group links by topic
4. **Link Preview**: Show article previews on hover
5. **Link Analytics**: Track which links users click most

---

**The source links feature is now live! 🎉**

