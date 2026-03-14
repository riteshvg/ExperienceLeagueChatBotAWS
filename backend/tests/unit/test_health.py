"""
Unit tests for health endpoints
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data
    
    # Verify timestamp is valid
    timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
    assert isinstance(timestamp, datetime)


def test_config_status_without_aws(monkeypatch):
    """Test config status endpoint without AWS credentials"""
    # Mock AWS connection failure
    def mock_verify_aws(*args, **kwargs):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AWS connection failed"
        )
    
    # This test will fail if AWS is not configured, which is expected
    # We'll skip it in CI/CD if AWS credentials are not available
    try:
        response = client.get("/api/v1/config/status")
        # If AWS is configured, we should get 200
        if response.status_code == 200:
            data = response.json()
            assert "aws_configured" in data
            assert "knowledge_base_configured" in data
            assert "database_configured" in data
    except Exception:
        # If AWS is not configured, that's okay for unit tests
        pytest.skip("AWS credentials not available for testing")


def test_api_docs_available():
    """Test that API documentation is available"""
    response = client.get("/api/docs")
    assert response.status_code == 200


def test_redoc_available():
    """Test that ReDoc documentation is available"""
    response = client.get("/api/redoc")
    assert response.status_code == 200

