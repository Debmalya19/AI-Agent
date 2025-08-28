"""
Unit tests for voice assistant API endpoints.
Tests CRUD operations, authentication, and error handling.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import json

from backend.database import Base, get_db
from backend.models import User, UserSession, VoiceSettings as VoiceSettingsDB, VoiceAnalytics as VoiceAnalyticsDB
from backend.voice_models import VoiceActionType
from main import app

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_voice.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test database
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture
def test_user_and_session():
    """Create test user and session"""
    db = TestingSessionLocal()
    
    # Create test user
    test_user = User(
        user_id="test_user_123",
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password",
        full_name="Test User"
    )
    db.add(test_user)
    db.commit()
    
    # Create test session
    test_session = UserSession(
        session_id="test_session_123",
        user_id="test_user_123",
        token_hash="hashed_token",
        expires_at=datetime.utcnow() + timedelta(hours=24),
        is_active=True
    )
    db.add(test_session)
    db.commit()
    
    yield {
        "user_id": "test_user_123",
        "session_id": "test_session_123"
    }
    
    # Cleanup
    db.query(VoiceAnalyticsDB).filter(VoiceAnalyticsDB.user_id == "test_user_123").delete()
    db.query(VoiceSettingsDB).filter(VoiceSettingsDB.user_id == "test_user_123").delete()
    db.query(UserSession).filter(UserSession.user_id == "test_user_123").delete()
    db.query(User).filter(User.user_id == "test_user_123").delete()
    db.commit()
    db.close()


class TestVoiceCapabilities:
    """Test voice capabilities endpoint"""
    
    def test_get_voice_capabilities_success(self):
        """Test successful voice capabilities retrieval"""
        response = client.get("/voice/capabilities")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "speech_recognition_available" in data
        assert "speech_synthesis_available" in data
        assert "available_voices" in data
        assert "supported_languages" in data
        assert "browser_support" in data
        
        # Check that we have expected voices and languages
        assert len(data["available_voices"]) > 0
        assert len(data["supported_languages"]) > 0
        assert "en-US" in data["supported_languages"]


class TestVoiceSettings:
    """Test voice settings endpoints"""
    
    def test_get_voice_settings_default(self, test_user_and_session):
        """Test getting default voice settings when none exist"""
        session_id = test_user_and_session["session_id"]
        
        response = client.get(
            "/voice/settings",
            cookies={"session_token": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "settings" in data
        settings = data["settings"]
        
        # Check default values
        assert settings["auto_play_enabled"] is False
        assert settings["voice_name"] == "default"
        assert settings["speech_rate"] == 1.0
        assert settings["language"] == "en-US"
    
    def test_get_voice_settings_unauthorized(self):
        """Test getting voice settings without authentication"""
        response = client.get("/voice/settings")
        
        assert response.status_code == 401
        assert "Unauthorized" in response.json()["detail"]
    
    def test_update_voice_settings_create_new(self, test_user_and_session):
        """Test creating new voice settings"""
        session_id = test_user_and_session["session_id"]
        
        settings_data = {
            "settings": {
                "auto_play_enabled": True,
                "voice_name": "en-US-Standard-A",
                "speech_rate": 1.2,
                "language": "en-GB"
            }
        }
        
        response = client.post(
            "/voice/settings",
            json=settings_data,
            cookies={"session_token": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        settings = data["settings"]
        assert settings["auto_play_enabled"] is True
        assert settings["voice_name"] == "en-US-Standard-A"
        assert settings["speech_rate"] == 1.2
        assert settings["language"] == "en-GB"    
    
    def test_update_voice_settings_partial_update(self, test_user_and_session):
        """Test partial update of existing voice settings"""
        session_id = test_user_and_session["session_id"]
        user_id = test_user_and_session["user_id"]
        
        # First create initial settings
        db = TestingSessionLocal()
        initial_settings = VoiceSettingsDB(
            user_id=user_id,
            auto_play_enabled=False,
            voice_name="default",
            speech_rate=1.0,
            language="en-US"
        )
        db.add(initial_settings)
        db.commit()
        db.close()
        
        # Now update only some fields
        update_data = {
            "settings": {
                "auto_play_enabled": True,
                "speech_rate": 1.5
            }
        }
        
        response = client.post(
            "/voice/settings",
            json=update_data,
            cookies={"session_token": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        settings = data["settings"]
        assert settings["auto_play_enabled"] is True  # Updated
        assert settings["speech_rate"] == 1.5  # Updated
        assert settings["voice_name"] == "default"  # Unchanged
        assert settings["language"] == "en-US"  # Unchanged

    def test_update_voice_settings_validation_error(self, test_user_and_session):
        """Test voice settings update with invalid data"""
        session_id = test_user_and_session["session_id"]
        
        invalid_data = {
            "settings": {
                "speech_rate": 5.0,  # Invalid: > 3.0
                "speech_volume": 2.0  # Invalid: > 1.0
            }
        }
        
        response = client.post(
            "/voice/settings",
            json=invalid_data,
            cookies={"session_token": session_id}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_reset_voice_settings(self, test_user_and_session):
        """Test resetting voice settings to defaults"""
        session_id = test_user_and_session["session_id"]
        user_id = test_user_and_session["user_id"]
        
        # First create some settings
        db = TestingSessionLocal()
        settings = VoiceSettingsDB(
            user_id=user_id,
            auto_play_enabled=True,
            voice_name="custom_voice",
            speech_rate=2.0
        )
        db.add(settings)
        db.commit()
        db.close()
        
        # Reset settings
        response = client.delete(
            "/voice/settings",
            cookies={"session_token": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        settings = data["settings"]
        # Should return default values
        assert settings["auto_play_enabled"] is False
        assert settings["voice_name"] == "default"
        assert settings["speech_rate"] == 1.0


class TestVoiceAnalytics:
    """Test voice analytics endpoints"""
    
    def test_log_voice_analytics_success(self, test_user_and_session):
        """Test successful voice analytics logging"""
        session_id = test_user_and_session["session_id"]
        
        analytics_data = {
            "analytics": {
                "action_type": "stt_complete",
                "duration_ms": 1500,
                "text_length": 25,
                "accuracy_score": 0.95,
                "metadata": {"language": "en-US", "confidence": 0.9}
            }
        }
        
        response = client.post(
            "/voice/analytics",
            json=analytics_data,
            cookies={"session_token": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "analytics_id" in data
        assert isinstance(data["analytics_id"], int)
    
    def test_log_voice_analytics_with_error(self, test_user_and_session):
        """Test logging voice analytics with error message"""
        session_id = test_user_and_session["session_id"]
        
        analytics_data = {
            "analytics": {
                "action_type": "stt_error",
                "error_message": "Microphone access denied",
                "metadata": {"error_code": "PERMISSION_DENIED"}
            }
        }
        
        response = client.post(
            "/voice/analytics",
            json=analytics_data,
            cookies={"session_token": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_get_analytics_summary_empty(self, test_user_and_session):
        """Test getting analytics summary with no data"""
        session_id = test_user_and_session["session_id"]
        
        response = client.get(
            "/voice/analytics/summary",
            cookies={"session_token": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        summary = data["summary"]
        assert summary["total_actions"] == 0
        assert summary["action_breakdown"] == {}
        assert summary["average_duration"] == 0
        assert summary["error_rate"] == 0
    
    def test_get_analytics_summary_with_data(self, test_user_and_session):
        """Test getting analytics summary with existing data"""
        session_id = test_user_and_session["session_id"]
        user_id = test_user_and_session["user_id"]
        
        # Add some test analytics data
        db = TestingSessionLocal()
        
        analytics_records = [
            VoiceAnalyticsDB(
                user_id=user_id,
                action_type="stt_complete",
                duration_ms=1000,
                text_length=20
            ),
            VoiceAnalyticsDB(
                user_id=user_id,
                action_type="tts_complete",
                duration_ms=2000,
                text_length=30
            ),
            VoiceAnalyticsDB(
                user_id=user_id,
                action_type="stt_error",
                error_message="Network error"
            )
        ]
        
        for record in analytics_records:
            db.add(record)
        db.commit()
        db.close()
        
        response = client.get(
            "/voice/analytics/summary",
            cookies={"session_token": session_id}
        )
        
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


class TestVoiceAuthenticationScenarios:
    """Test various authentication scenarios for voice endpoints"""
    
    def test_expired_session(self):
        """Test voice endpoints with expired session"""
        # Create expired session
        db = TestingSessionLocal()
        
        expired_user = User(
            user_id="expired_user",
            username="expireduser",
            email="expired@example.com",
            password_hash="hashed"
        )
        db.add(expired_user)
        
        expired_session = UserSession(
            session_id="expired_session",
            user_id="expired_user",
            token_hash="expired_token",
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired
            is_active=True
        )
        db.add(expired_session)
        db.commit()
        
        response = client.get(
            "/voice/settings",
            cookies={"session_token": "expired_session"}
        )
        
        assert response.status_code == 401
        
        # Cleanup
        db.query(UserSession).filter(UserSession.user_id == "expired_user").delete()
        db.query(User).filter(User.user_id == "expired_user").delete()
        db.commit()
        db.close()
    
    def test_invalid_session_token(self):
        """Test voice endpoints with invalid session token"""
        response = client.get(
            "/voice/settings",
            cookies={"session_token": "invalid_token"}
        )
        
        assert response.status_code == 401
        assert "Invalid or expired session" in response.json()["detail"]
    
    def test_inactive_session(self):
        """Test voice endpoints with inactive session"""
        db = TestingSessionLocal()
        
        inactive_user = User(
            user_id="inactive_user",
            username="inactiveuser",
            email="inactive@example.com",
            password_hash="hashed"
        )
        db.add(inactive_user)
        
        inactive_session = UserSession(
            session_id="inactive_session",
            user_id="inactive_user",
            token_hash="inactive_token",
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_active=False  # Inactive
        )
        db.add(inactive_session)
        db.commit()
        
        response = client.get(
            "/voice/settings",
            cookies={"session_token": "inactive_session"}
        )
        
        assert response.status_code == 401
        
        # Cleanup
        db.query(UserSession).filter(UserSession.user_id == "inactive_user").delete()
        db.query(User).filter(User.user_id == "inactive_user").delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    pytest.main([__file__])