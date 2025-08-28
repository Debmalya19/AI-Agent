"""
Integration tests for voice assistant API with database operations.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to the path so we can import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from backend.database import Base, get_db
from backend.models import User, UserSession, VoiceSettings as VoiceSettingsDB, VoiceAnalytics as VoiceAnalyticsDB

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_voice_integration_unique.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test database
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Database creation issue: {e}")
    # Continue anyway - tables might already exist


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="function")
def test_user_session():
    """Create a test user and session for each test"""
    db = TestingSessionLocal()
    
    # Create test user
    test_user = User(
        user_id="test_voice_user",
        username="voiceuser",
        email="voice@test.com",
        password_hash="hashed_password",
        full_name="Voice Test User"
    )
    db.add(test_user)
    db.commit()
    
    # Create test session
    test_session = UserSession(
        session_id="voice_test_session",
        user_id="test_voice_user",
        token_hash="hashed_token",
        expires_at=datetime.utcnow() + timedelta(hours=24),
        is_active=True
    )
    db.add(test_session)
    db.commit()
    
    yield {
        "user_id": "test_voice_user",
        "session_id": "voice_test_session"
    }
    
    # Cleanup
    db.query(VoiceAnalyticsDB).filter(VoiceAnalyticsDB.user_id == "test_voice_user").delete()
    db.query(VoiceSettingsDB).filter(VoiceSettingsDB.user_id == "test_voice_user").delete()
    db.query(UserSession).filter(UserSession.user_id == "test_voice_user").delete()
    db.query(User).filter(User.user_id == "test_voice_user").delete()
    db.commit()
    db.close()


def test_voice_settings_full_workflow(test_user_session):
    """Test complete voice settings workflow: get defaults, update, get updated, reset"""
    session_id = test_user_session["session_id"]
    
    # 1. Get default settings (should return defaults when none exist)
    response = client.get("/voice/settings", cookies={"session_token": session_id})
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    settings = data["settings"]
    assert settings["auto_play_enabled"] is False
    assert settings["voice_name"] == "default"
    assert settings["speech_rate"] == 1.0
    
    # 2. Update settings
    update_data = {
        "settings": {
            "auto_play_enabled": True,
            "voice_name": "en-US-Standard-A",
            "speech_rate": 1.5,
            "language": "en-GB"
        }
    }
    
    response = client.post("/voice/settings", json=update_data, cookies={"session_token": session_id})
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    settings = data["settings"]
    assert settings["auto_play_enabled"] is True
    assert settings["voice_name"] == "en-US-Standard-A"
    assert settings["speech_rate"] == 1.5
    assert settings["language"] == "en-GB"
    
    # 3. Get updated settings (should return updated values)
    response = client.get("/voice/settings", cookies={"session_token": session_id})
    assert response.status_code == 200
    
    data = response.json()
    settings = data["settings"]
    assert settings["auto_play_enabled"] is True
    assert settings["voice_name"] == "en-US-Standard-A"
    assert settings["speech_rate"] == 1.5
    assert settings["language"] == "en-GB"
    
    # 4. Reset settings
    response = client.delete("/voice/settings", cookies={"session_token": session_id})
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    settings = data["settings"]
    # Should return defaults after reset
    assert settings["auto_play_enabled"] is False
    assert settings["voice_name"] == "default"
    assert settings["speech_rate"] == 1.0


def test_voice_analytics_logging_and_summary(test_user_session):
    """Test voice analytics logging and summary generation"""
    session_id = test_user_session["session_id"]
    
    # 1. Check empty summary
    response = client.get("/voice/analytics/summary", cookies={"session_token": session_id})
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    summary = data["summary"]
    assert summary["total_actions"] == 0
    
    # 2. Log some analytics
    analytics_data = [
        {
            "analytics": {
                "action_type": "stt_complete",
                "duration_ms": 1000,
                "text_length": 20,
                "accuracy_score": 0.95
            }
        },
        {
            "analytics": {
                "action_type": "tts_complete",
                "duration_ms": 2000,
                "text_length": 30
            }
        },
        {
            "analytics": {
                "action_type": "stt_error",
                "error_message": "Network timeout"
            }
        }
    ]
    
    for data_item in analytics_data:
        response = client.post("/voice/analytics", json=data_item, cookies={"session_token": session_id})
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    # 3. Check summary with data
    response = client.get("/voice/analytics/summary", cookies={"session_token": session_id})
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    summary = data["summary"]
    
    assert summary["total_actions"] == 3
    assert summary["action_breakdown"]["stt_complete"] == 1
    assert summary["action_breakdown"]["tts_complete"] == 1
    assert summary["action_breakdown"]["stt_error"] == 1
    assert summary["average_duration_ms"] == 1500.0  # (1000 + 2000) / 2
    assert summary["error_rate"] == 0.333  # 1 error out of 3 actions


def test_voice_settings_partial_updates(test_user_session):
    """Test partial updates to voice settings"""
    session_id = test_user_session["session_id"]
    
    # 1. Create initial settings
    initial_data = {
        "settings": {
            "auto_play_enabled": True,
            "voice_name": "initial_voice",
            "speech_rate": 1.0,
            "language": "en-US"
        }
    }
    
    response = client.post("/voice/settings", json=initial_data, cookies={"session_token": session_id})
    assert response.status_code == 200
    
    # 2. Partial update (only change speech_rate and auto_play_enabled)
    partial_update = {
        "settings": {
            "auto_play_enabled": False,
            "speech_rate": 2.0
        }
    }
    
    response = client.post("/voice/settings", json=partial_update, cookies={"session_token": session_id})
    assert response.status_code == 200
    
    data = response.json()
    settings = data["settings"]
    
    # Updated fields
    assert settings["auto_play_enabled"] is False
    assert settings["speech_rate"] == 2.0
    
    # Unchanged fields
    assert settings["voice_name"] == "initial_voice"
    assert settings["language"] == "en-US"


def test_voice_settings_validation(test_user_session):
    """Test voice settings validation"""
    session_id = test_user_session["session_id"]
    
    # Test invalid speech_rate (too high)
    invalid_data = {
        "settings": {
            "speech_rate": 5.0  # Max is 3.0
        }
    }
    
    response = client.post("/voice/settings", json=invalid_data, cookies={"session_token": session_id})
    assert response.status_code == 422  # Validation error
    
    # Test invalid speech_volume (too high)
    invalid_data = {
        "settings": {
            "speech_volume": 2.0  # Max is 1.0
        }
    }
    
    response = client.post("/voice/settings", json=invalid_data, cookies={"session_token": session_id})
    assert response.status_code == 422  # Validation error


def test_voice_analytics_validation(test_user_session):
    """Test voice analytics validation"""
    session_id = test_user_session["session_id"]
    
    # Test invalid action_type
    invalid_data = {
        "analytics": {
            "action_type": "invalid_action"
        }
    }
    
    response = client.post("/voice/analytics", json=invalid_data, cookies={"session_token": session_id})
    assert response.status_code == 422  # Validation error
    
    # Test invalid accuracy_score (too high)
    invalid_data = {
        "analytics": {
            "action_type": "stt_complete",
            "accuracy_score": 1.5  # Max is 1.0
        }
    }
    
    response = client.post("/voice/analytics", json=invalid_data, cookies={"session_token": session_id})
    assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])