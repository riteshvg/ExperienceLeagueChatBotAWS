"""
Session service for managing chat history and conversation context.
Stores conversation history per user/session for context-aware responses.
"""
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Message:
    """Represents a chat message"""
    def __init__(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None
    ):
        self.id = str(uuid.uuid4())
        self.role = role  # 'user' or 'assistant'
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = timestamp or time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'metadata': self.metadata,
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat()
        }


class Session:
    """Represents a chat session with conversation history"""
    def __init__(self, session_id: str, user_id: str = "anonymous"):
        self.session_id = session_id
        self.user_id = user_id
        self.messages: List[Message] = []
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.metadata: Dict[str, Any] = {}
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Add a message to the session"""
        message = Message(role, content, metadata)
        self.messages.append(message)
        self.last_accessed = time.time()
        return message
    
    def get_recent_messages(self, limit: int = 10) -> List[Message]:
        """Get the most recent messages"""
        return self.messages[-limit:] if len(self.messages) > limit else self.messages
    
    def get_conversation_context(self, max_tokens: int = 2000) -> str:
        """
        Get conversation context as a formatted string for LLM.
        Includes recent messages up to max_tokens limit.
        """
        if not self.messages:
            return ""
        
        # Start from most recent and work backwards
        context_parts = []
        total_length = 0
        
        for message in reversed(self.messages):
            message_text = f"{message.role.upper()}: {message.content}"
            message_length = len(message_text)
            
            if total_length + message_length > max_tokens:
                break
            
            context_parts.insert(0, message_text)
            total_length += message_length
        
        return "\n".join(context_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'message_count': len(self.messages),
            'created_at': self.created_at,
            'last_accessed': self.last_accessed,
            'messages': [msg.to_dict() for msg in self.messages],
            'metadata': self.metadata
        }


class SessionService:
    """
    Service for managing chat sessions and conversation history.
    Stores sessions in memory (can be extended to use Redis/database).
    """
    
    def __init__(self, max_sessions: int = 1000, session_ttl: int = 86400):
        """
        Initialize session service
        
        Args:
            max_sessions: Maximum number of active sessions
            session_ttl: Session time-to-live in seconds (24 hours default)
        """
        self.max_sessions = max_sessions
        self.session_ttl = session_ttl
        self.sessions: Dict[str, Session] = {}
        self.stats = {
            'total_sessions': 0,
            'active_sessions': 0,
            'expired_sessions': 0
        }
    
    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        user_id: str = "anonymous"
    ) -> Session:
        """
        Get existing session or create a new one
        
        Args:
            session_id: Optional session ID (generates new if not provided)
            user_id: User ID for the session
        
        Returns:
            Session object
        """
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            # Check if expired
            if time.time() - session.last_accessed > self.session_ttl:
                logger.debug(f"Session {session_id} expired, creating new one")
                del self.sessions[session_id]
                self.stats['expired_sessions'] += 1
            else:
                session.last_accessed = time.time()
                return session
        
        # Create new session
        if not session_id:
            session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        session = Session(session_id, user_id)
        self.sessions[session_id] = session
        self.stats['total_sessions'] += 1
        self.stats['active_sessions'] = len(self.sessions)
        
        logger.debug(f"Created new session: {session_id} for user: {user_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            # Check if expired
            if time.time() - session.last_accessed > self.session_ttl:
                del self.sessions[session_id]
                self.stats['expired_sessions'] += 1
                return None
            session.last_accessed = time.time()
            return session
        return None
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """Add a message to a session"""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None
        
        return session.add_message(role, content, metadata)
    
    def get_conversation_context(
        self,
        session_id: str,
        max_tokens: int = 2000
    ) -> str:
        """Get conversation context for a session"""
        session = self.get_session(session_id)
        if not session:
            return ""
        
        return session.get_conversation_context(max_tokens)
    
    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Message]:
        """Get recent messages from a session"""
        session = self.get_session(session_id)
        if not session:
            return []
        
        return session.get_recent_messages(limit)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.stats['active_sessions'] = len(self.sessions)
            logger.debug(f"Deleted session: {session_id}")
            return True
        return False
    
    def cleanup_expired(self) -> int:
        """
        Remove expired sessions
        
        Returns:
            Number of sessions removed
        """
        current_time = time.time()
        expired_sessions = [
            sid for sid, session in self.sessions.items()
            if current_time - session.last_accessed > self.session_ttl
        ]
        
        for sid in expired_sessions:
            del self.sessions[sid]
            self.stats['expired_sessions'] += len(expired_sessions)
        
        self.stats['active_sessions'] = len(self.sessions)
        
        if expired_sessions:
            logger.debug(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session service statistics"""
        return {
            'active_sessions': len(self.sessions),
            'max_sessions': self.max_sessions,
            'total_sessions_created': self.stats['total_sessions'],
            'expired_sessions': self.stats['expired_sessions'],
            'session_ttl': self.session_ttl
        }

