"""
Simple test to verify new endpoints are working.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from main import app


def test_new_endpoints_exist():
    """Test that new endpoints exist and return proper error codes for unauthorized access."""
    client = TestClient(app)
    
    # Test endpoints without authentication - should return 401
    endpoints = [
        "/chat/status",
        "/chat/context", 
        "/chat/tools",
        "/chat/ui-state/test_session"
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"
        assert "Unauthorized" in response.json()["detail"]


def test_chat_tools_endpoint_with_mock_auth():
    """Test /chat/tools endpoint with mocked authentication."""
    client = TestClient(app)
    
    # Mock the database session validation
    mock_user_session = Mock()
    mock_user_session.session_id = "test_session"
    mock_user_session.user_id = "test_user"
    mock_user_session.is_active = True
    
    with patch('main.SessionLocal') as mock_db:
        mock_db.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user_session
        
        response = client.get(
            "/chat/tools",
            cookies={"session_token": "test_session"}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert data["status"] == "success"
    assert "tools" in data
    assert "tool_performance" in data
    assert "orchestrator_status" in data
    assert "categories" in data
    assert "timestamp" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])