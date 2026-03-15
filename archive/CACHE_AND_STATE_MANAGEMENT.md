# Cache and State Management Implementation

## Overview
This document describes the caching and state management features added to reduce LLM calls for repetitive queries and maintain conversation context.

## Features Implemented

### 1. Cache Service (`backend/app/services/cache_service.py`)
- **LRU Cache**: Least Recently Used eviction policy
- **TTL Support**: Time-to-live for cache entries (default: 1 hour)
- **Query Normalization**: Normalizes queries for consistent caching
- **User-Specific Caching**: Supports per-user cache isolation
- **Statistics**: Tracks hits, misses, evictions, and hit rate

**Key Methods:**
- `get(query, user_id)`: Retrieve cached response
- `set(query, data, user_id, ttl)`: Store response in cache
- `invalidate(query, user_id)`: Remove specific entry
- `clear()`: Clear all cache entries
- `get_stats()`: Get cache statistics

### 2. Session Service (`backend/app/services/session_service.py`)
- **Session Management**: Tracks conversations per user/session
- **Message History**: Stores all messages in a session
- **Conversation Context**: Generates context from recent messages for LLM
- **Auto-Expiration**: Sessions expire after 24 hours of inactivity
- **Statistics**: Tracks active sessions and total sessions created

**Key Methods:**
- `get_or_create_session(session_id, user_id)`: Get or create session
- `add_message(session_id, role, content, metadata)`: Add message to session
- `get_conversation_context(session_id, max_tokens)`: Get formatted context
- `get_recent_messages(session_id, limit)`: Get recent messages
- `delete_session(session_id)`: Delete a session
- `get_stats()`: Get session statistics

### 3. Chat Service Updates (`backend/app/services/chat_service.py`)
- **Cache Integration**: Checks cache before calling LLM
- **Conversation Context**: Includes previous messages in LLM context
- **Session Tracking**: Maintains conversation history per session
- **Streaming Support**: Cache works with streaming responses

**Changes:**
- `process_query()`: Now checks cache and includes conversation context
- `process_query_stream()`: Supports caching and context for streaming
- Both methods accept `use_cache` and `include_context` parameters

### 4. API Endpoints (`backend/app/api/v1/health.py`)
New endpoints for monitoring and management:
- `GET /api/v1/cache/stats`: Get cache statistics
- `POST /api/v1/cache/clear`: Clear the cache
- `GET /api/v1/sessions/stats`: Get session statistics

### 5. Frontend Persistence (`frontend/src/store/chatStore.ts`)
- **localStorage Persistence**: Chat history persists across page refreshes
- **Session ID Management**: Automatically generates and tracks session IDs
- **State Management**: Uses Zustand with persist middleware

**Features:**
- Messages are saved to localStorage
- Session ID is maintained across sessions
- "New Chat" clears messages but keeps session structure

### 6. Frontend Integration (`frontend/src/pages/ChatPage.tsx`)
- **Session ID**: Automatically sends session_id with each query
- **Cache Indicators**: Can display when response is from cache (via metadata)
- **History Persistence**: Chat history persists in browser

## Benefits

### 1. Reduced LLM Costs
- **Cache Hit Rate**: Repetitive queries are served from cache
- **No LLM Call**: Cached responses don't call AWS Bedrock
- **Faster Responses**: Cached responses are instant

### 2. Better Context Awareness
- **Conversation History**: LLM sees previous messages in conversation
- **Contextual Responses**: Responses are more relevant to ongoing conversation
- **Follow-up Questions**: Can reference previous answers

### 3. Improved User Experience
- **Persistent History**: Chat history survives page refreshes
- **Session Continuity**: Conversations continue across sessions
- **Faster Responses**: Cached queries respond instantly

## Configuration

### Cache Settings
- **Max Size**: 1000 entries (configurable in `CacheService.__init__`)
- **Default TTL**: 3600 seconds (1 hour)
- **Eviction Policy**: LRU (Least Recently Used)

### Session Settings
- **Max Sessions**: 1000 active sessions
- **Session TTL**: 86400 seconds (24 hours)
- **Context Limit**: 2000 tokens (configurable)

## Usage Examples

### Backend: Using Cache
```python
# Cache is automatically used in chat service
result = chat_service.process_query(
    query="What is Adobe Analytics?",
    user_id="user123",
    session_id="session456",
    use_cache=True,  # Default: True
    include_context=True  # Default: True
)

# Check if response was from cache
if result.get("from_cache"):
    print("Response served from cache!")
```

### Backend: Cache Statistics
```python
stats = chat_service.cache_service.get_stats()
print(f"Hit Rate: {stats['hit_rate']}%")
print(f"Cache Size: {stats['size']}/{stats['max_size']}")
```

### Frontend: Session Management
```typescript
const { messages, sessionId, clearMessages } = useChatStore()

// Messages are automatically persisted to localStorage
// Session ID is automatically generated and maintained
// Clear messages to start new conversation
clearMessages() // Creates new session ID
```

## Testing

Unit tests are available:
- `backend/tests/unit/test_cache_service.py`: Tests for cache service
- `backend/tests/unit/test_session_service.py`: Tests for session service

Run tests:
```bash
cd backend
pytest tests/unit/test_cache_service.py -v
pytest tests/unit/test_session_service.py -v
```

## Monitoring

### Cache Statistics Endpoint
```bash
curl http://localhost:8000/api/v1/cache/stats
```

Response:
```json
{
  "success": true,
  "stats": {
    "size": 150,
    "max_size": 1000,
    "hits": 45,
    "misses": 105,
    "hit_rate": 30.0,
    "evictions": 5,
    "expired": 10,
    "total_requests": 150
  }
}
```

### Session Statistics Endpoint
```bash
curl http://localhost:8000/api/v1/sessions/stats
```

Response:
```json
{
  "success": true,
  "stats": {
    "active_sessions": 25,
    "max_sessions": 1000,
    "total_sessions_created": 150,
    "expired_sessions": 125,
    "session_ttl": 86400
  }
}
```

## Future Enhancements

1. **Redis Backend**: Replace in-memory cache with Redis for distributed caching
2. **Database Persistence**: Store sessions in database for long-term persistence
3. **Cache Warming**: Pre-populate cache with common queries
4. **Analytics**: Track cache performance and optimize TTL values
5. **Multi-User Sessions**: Support multiple users in same session
6. **Cache Invalidation**: Smart invalidation based on Knowledge Base updates

## Notes

- Cache is currently in-memory and will be lost on server restart
- Sessions expire after 24 hours of inactivity
- Cache entries expire after 1 hour
- Frontend localStorage has browser storage limits (~5-10MB)
- Session context is limited to 2000 tokens to avoid exceeding LLM context limits

