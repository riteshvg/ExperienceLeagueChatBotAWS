"""
Unit tests for session service
"""
import pytest
import time
from app.services.session_service import SessionService, Session, Message


class TestMessage:
    """Test Message class"""
    
    def test_message_creation(self):
        """Test message creation"""
        msg = Message("user", "Hello", {"test": "data"})
        
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.metadata == {"test": "data"}
        assert msg.id is not None
        assert msg.timestamp > 0
    
    def test_message_to_dict(self):
        """Test message to dictionary conversion"""
        msg = Message("assistant", "Hi there")
        msg_dict = msg.to_dict()
        
        assert msg_dict["role"] == "assistant"
        assert msg_dict["content"] == "Hi there"
        assert "id" in msg_dict
        assert "timestamp" in msg_dict
        assert "datetime" in msg_dict


class TestSession:
    """Test Session class"""
    
    def test_session_creation(self):
        """Test session creation"""
        session = Session("session_123", "user_456")
        
        assert session.session_id == "session_123"
        assert session.user_id == "user_456"
        assert len(session.messages) == 0
        assert session.created_at > 0
    
    def test_session_add_message(self):
        """Test adding messages to session"""
        session = Session("session_123")
        
        msg1 = session.add_message("user", "Hello")
        msg2 = session.add_message("assistant", "Hi", {"model": "haiku"})
        
        assert len(session.messages) == 2
        assert session.messages[0].content == "Hello"
        assert session.messages[1].content == "Hi"
        assert session.messages[1].metadata == {"model": "haiku"}
    
    def test_session_get_recent_messages(self):
        """Test getting recent messages"""
        session = Session("session_123")
        
        # Add 15 messages
        for i in range(15):
            session.add_message("user" if i % 2 == 0 else "assistant", f"Message {i}")
        
        recent = session.get_recent_messages(limit=10)
        assert len(recent) == 10
        assert recent[0].content == "Message 5"  # Last 10 messages
        assert recent[-1].content == "Message 14"
    
    def test_session_conversation_context(self):
        """Test getting conversation context"""
        session = Session("session_123")
        
        session.add_message("user", "What is Adobe Analytics?")
        session.add_message("assistant", "Adobe Analytics is a web analytics platform.")
        session.add_message("user", "How is it different from CJA?")
        
        context = session.get_conversation_context(max_tokens=500)
        assert "What is Adobe Analytics" in context
        assert "Adobe Analytics is a web analytics platform" in context
        assert "How is it different from CJA" in context
    
    def test_session_to_dict(self):
        """Test session to dictionary conversion"""
        session = Session("session_123", "user_456")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi")
        
        session_dict = session.to_dict()
        
        assert session_dict["session_id"] == "session_123"
        assert session_dict["user_id"] == "user_456"
        assert session_dict["message_count"] == 2
        assert len(session_dict["messages"]) == 2


class TestSessionService:
    """Test SessionService class"""
    
    def test_session_service_initialization(self):
        """Test session service initialization"""
        service = SessionService(max_sessions=100, session_ttl=3600)
        
        assert service.max_sessions == 100
        assert service.session_ttl == 3600
        assert len(service.sessions) == 0
    
    def test_get_or_create_session(self):
        """Test getting or creating a session"""
        service = SessionService()
        
        # Create new session
        session1 = service.get_or_create_session(user_id="user1")
        assert session1 is not None
        assert session1.user_id == "user1"
        assert session1.session_id in service.sessions
        
        # Get existing session
        session2 = service.get_or_create_session(
            session_id=session1.session_id,
            user_id="user1"
        )
        assert session2.session_id == session1.session_id
    
    def test_add_message(self):
        """Test adding messages to a session"""
        service = SessionService()
        session = service.get_or_create_session(user_id="user1")
        
        msg = service.add_message(
            session.session_id,
            "user",
            "Hello",
            {"test": "data"}
        )
        
        assert msg is not None
        assert msg.content == "Hello"
        assert msg.role == "user"
    
    def test_get_conversation_context(self):
        """Test getting conversation context"""
        service = SessionService()
        session = service.get_or_create_session(user_id="user1")
        
        service.add_message(session.session_id, "user", "Question 1")
        service.add_message(session.session_id, "assistant", "Answer 1")
        service.add_message(session.session_id, "user", "Question 2")
        
        context = service.get_conversation_context(session.session_id)
        assert "Question 1" in context
        assert "Answer 1" in context
        assert "Question 2" in context
    
    def test_get_recent_messages(self):
        """Test getting recent messages"""
        service = SessionService()
        session = service.get_or_create_session(user_id="user1")
        
        for i in range(10):
            service.add_message(
                session.session_id,
                "user" if i % 2 == 0 else "assistant",
                f"Message {i}"
            )
        
        recent = service.get_recent_messages(session.session_id, limit=5)
        assert len(recent) == 5
    
    def test_delete_session(self):
        """Test deleting a session"""
        service = SessionService()
        session = service.get_or_create_session(user_id="user1")
        session_id = session.session_id
        
        assert service.delete_session(session_id) is True
        assert service.get_session(session_id) is None
        assert service.delete_session("nonexistent") is False
    
    def test_session_expiration(self):
        """Test session expiration"""
        service = SessionService(session_ttl=0.1)  # Very short TTL
        session = service.get_or_create_session(user_id="user1")
        session_id = session.session_id
        
        assert service.get_session(session_id) is not None
        
        time.sleep(0.2)
        assert service.get_session(session_id) is None  # Should be expired
    
    def test_cleanup_expired(self):
        """Test cleaning up expired sessions"""
        service = SessionService(session_ttl=0.1)
        
        session1 = service.get_or_create_session(user_id="user1")
        session2 = service.get_or_create_session(user_id="user2")
        
        time.sleep(0.2)
        
        removed = service.cleanup_expired()
        assert removed >= 2
        assert len(service.sessions) == 0
    
    def test_get_stats(self):
        """Test getting session statistics"""
        service = SessionService()
        
        service.get_or_create_session(user_id="user1")
        service.get_or_create_session(user_id="user2")
        
        stats = service.get_stats()
        assert stats['active_sessions'] == 2
        assert stats['total_sessions_created'] >= 2

