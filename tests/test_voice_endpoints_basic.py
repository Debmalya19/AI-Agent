"""
Basic tests for voice assistant API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add the parent directory to the path so we can import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)


def test_voice_capabilities_endpoint():
    """Test that voice capabilities endpoint returns expected data"""
    response = client.get("/voice/capabilities")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "speech_recognition_available" in data
    assert "speech_synthesis_available" in data
    assert "available_voices" in data
    assert "supported_languages" in data
    assert "browser_support" in data
    
    # Check data types and content
    assert isinstance(data["speech_recognition_available"], bool)
    assert isinstance(data["speech_synthesis_available"], bool)
    assert isinstance(data["available_voices"], list)
    assert isinstance(data["supported_languages"], list)
    assert isinstance(data["browser_support"], dict)
    
    # Check that we have some voices and languages
    assert len(data["available_voices"]) > 0
    assert len(data["supported_languages"]) > 0
    assert "en-US" in data["supported_languages"]


def test_voice_settings_unauthorized():
    """Test that voice settings endpoints require authentication"""
    # Test GET without session token
    response = client.get("/voice/settings")
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]
    
    # Test POST without session token
    response = client.post("/voice/settings", json={"settings": {}})
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]
    
    # Test DELETE without session token
    response = client.delete("/voice/settings")
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


def test_voice_analytics_unauthorized():
    """Test that voice analytics endpoints require authentication"""
    # Test POST without session token
    response = client.post("/voice/analytics", json={"analytics": {"action_type": "stt_start"}})
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]
    
    # Test GET summary without session token
    response = client.get("/voice/analytics/summary")
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


def test_voice_settings_invalid_session():
    """Test voice settings with invalid session token"""
    response = client.get("/voice/settings", cookies={"session_token": "invalid_token"})
    assert response.status_code == 401
    assert "Invalid or expired session" in response.json()["detail"]


def test_voice_analytics_invalid_session():
    """Test voice analytics with invalid session token"""
    response = client.post(
        "/voice/analytics", 
        json={"analytics": {"action_type": "stt_start"}},
        cookies={"session_token": "invalid_token"}
    )
    assert response.status_code == 401
    assert "Invalid or expired session" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])