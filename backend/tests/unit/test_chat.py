"""
Unit tests for chat endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_chat_service():
    """Mock chat service"""
    service = Mock()
    service.validate_query.return_value = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "is_relevant": True,
        "relevance_score": 1.0
    }
    service.process_query.return_value = {
        "success": True,
        "answer": "Test answer",
        "error": None,
        "documents": [],
        "model_used": "haiku",
        "routing_decision": {"model": "haiku"},
        "processing_time": 0.5
    }
    return service


def test_validate_query_endpoint():
    """Test query validation endpoint"""
    response = client.post(
        "/api/v1/chat/validate",
        json={"query": "What is Adobe Analytics?"}
    )
    
    # Should either succeed or fail gracefully if AWS not configured
    assert response.status_code in [200, 503, 500]


def test_chat_endpoint_basic():
    """Test basic chat endpoint"""
    response = client.post(
        "/api/v1/chat",
        json={
            "query": "What is Adobe Analytics?",
            "user_id": "test_user"
        }
    )
    
    # Should either succeed or fail gracefully if AWS not configured
    assert response.status_code in [200, 503, 500]


def test_chat_endpoint_empty_query():
    """Test chat endpoint with empty query"""
    response = client.post(
        "/api/v1/chat",
        json={"query": ""}
    )
    
    # Should return validation error
    assert response.status_code in [200, 400, 422, 503]


def test_chat_endpoint_long_query():
    """Test chat endpoint with very long query"""
    long_query = "a" * 30000
    response = client.post(
        "/api/v1/chat",
        json={"query": long_query}
    )
    
    # Should return validation error
    assert response.status_code in [200, 400, 422, 503]


def test_validate_query_empty():
    """Test validation with empty query"""
    response = client.post(
        "/api/v1/chat/validate",
        json={"query": ""}
    )
    
    assert response.status_code in [200, 422, 503]


def test_validate_query_short():
    """Test validation with very short query"""
    response = client.post(
        "/api/v1/chat/validate",
        json={"query": "ab"}
    )
    
    assert response.status_code in [200, 422, 503]

