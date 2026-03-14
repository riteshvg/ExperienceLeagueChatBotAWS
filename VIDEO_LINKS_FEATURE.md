# Video Links Feature

## Overview
The chatbot now automatically detects and displays video links associated with Experience League articles. When an article contains a video (YouTube, Vimeo, Adobe videos, etc.), a "Watch Video" link is displayed below the article link.

## Features

### 1. **Automatic Video Detection**
The system automatically scans document content for video links from:
- **YouTube**: `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/embed/`
- **Vimeo**: `vimeo.com/`, `vimeo.com/embed/`
- **Adobe Videos**: `experienceleague.adobe.com/*video*`, `video.adobe.com/`
- **Direct Video Files**: `.mp4`, `.mov`, `.avi`, `.webm`, `.mkv`
- **Embedded Videos**: `<iframe>` tags with video sources
- **Markdown Links**: `[video text](video_url)` patterns

### 2. **Video URL Normalization**
- YouTube short URLs (`youtu.be/`) are converted to full watch URLs
- YouTube embed URLs are converted to watch URLs
- Video IDs are extracted and reconstructed into proper URLs

### 3. **Frontend Display**
- Video links appear below article links with a video icon
- "Watch Video" text with external link icon
- Styled differently from article links (secondary color)
- Opens in new tab

## Implementation Details

### Backend Changes

#### 1. **`backend/app/models/schemas.py`**
- Added `video_url` field to `SourceLink` model (optional)

#### 2. **`backend/app/services/chat_helpers.py`**
- Added `extract_video_url()` function to detect video links in content
- Updated `extract_source_links()` to include video URLs when found

#### 3. **`backend/app/api/v1/chat.py`**
- Updated to pass `video_url` field in SourceLink objects

### Frontend Changes

#### 1. **`frontend/src/components/ChatMessage.tsx`**
- Added `VideoLibraryIcon` import
- Updated `SourceLink` interface to include `video_url`
- Added video link display below article links
- Styled with secondary color and video icon

#### 2. **`frontend/src/store/chatStore.ts`**
- Updated `SourceLink` interface to include optional `video_url`

#### 3. **`frontend/src/services/api.ts`**
- Updated `SourceLink` interface to include optional `video_url`

## Video URL Patterns Detected

### YouTube
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- `<iframe src="https://www.youtube.com/embed/VIDEO_ID">`

### Vimeo
- `https://vimeo.com/VIDEO_ID`
- `https://vimeo.com/embed/VIDEO_ID`
- `<iframe src="https://vimeo.com/embed/VIDEO_ID">`

### Adobe Videos
- `https://experienceleague.adobe.com/.../video/...`
- `https://video.adobe.com/...`

### Direct Video Files
- `https://example.com/video.mp4`
- `https://example.com/video.mov`

### Markdown Links
- `[Watch this video](https://youtube.com/watch?v=...)`
- `[Video tutorial](https://vimeo.com/123456)`

## Example Display

When an article has a video, the chatbot response will show:

```
📚 Related Articles:
  • Article Title → [Opens article]
    🎥 Watch Video → [Opens video]
```

## Benefits

1. **Enhanced User Experience**: Users can quickly access video content related to articles
2. **Better Learning**: Videos complement written documentation
3. **Automatic Detection**: No manual configuration needed
4. **Multiple Platforms**: Supports YouTube, Vimeo, Adobe videos, and direct video files

## Testing

To test video link detection:

1. Ask a question about a topic that has video content in Experience League
2. Check if video links appear below article links in the response
3. Verify video links open correctly in a new tab

## Future Enhancements

Potential improvements:
- Video thumbnail previews
- Video duration display
- Video transcript integration
- Embedded video player (for supported platforms)
- Video search within Knowledge Base

