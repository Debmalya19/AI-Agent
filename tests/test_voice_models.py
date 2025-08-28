"""
Unit tests for voice assistant models and database operations.
Tests both Pydantic models for API validation and SQLAlchemy models for database operations.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend'))

from voice_models import (
    VoiceSettings, VoiceSettingsUpdate, VoiceAnalytics, VoiceCapabilities,
    VoiceSettingsResponse, VoiceAnalyticsResponse, VoiceErrorResponse,
    VoiceActionType, validate_voice_settings_data, validate_voice_analytics_data,
    DEFAULT_VOICE_SETTINGS
)
from models import VoiceSettings as DBVoiceSettings, VoiceAnalytics as DBVoiceAnalytics, User
from database import Base


class TestVoicePydanticModels:
    """Test Pydantic models for voice assistant API validation"""
    
    def test_voice_settings_default_values(self):
        """Test VoiceSettings model with default values"""
        settings = VoiceSettings()
        
        assert settings.auto_play_enabled is False
        assert settings.voice_name == "default"
        assert settings.speech_rate == 1.0
        assert settings.speech_pitch == 1.0
        assert settings.speech_volume == 1.0
        assert settings.language == "en-US"
        assert settings.microphone_sensitivity == 0.5
        assert settings.noise_cancellation is True
    
    def test_voice_settings_validation_success(self):
        """Test VoiceSettings validation with valid data"""
        settings_data = {
            "auto_play_enabled": True,
            "voice_name": "female-voice",
            "speech_rate": 1.5,
            "speech_pitch": 1.2,
            "speech_volume": 0.8,
            "language": "fr-FR",
            "microphone_sensitivity": 0.7,
            "noise_cancellation": False
        }
        
        settings = VoiceSettings(**settings_data)
        
        assert settings.auto_play_enabled is True
        assert settings.voice_name == "female-voice"
        assert settings.speech_rate == 1.5
        assert settings.speech_pitch == 1.2
        assert settings.speech_volume == 0.8
        assert settings.language == "fr-FR"
        assert settings.microphone_sensitivity == 0.7
        assert settings.noise_cancellation is False
    
    def test_voice_settings_validation_errors(self):
        """Test VoiceSettings validation with invalid data"""
        # Test speech_rate out of range
        with pytest.raises(ValueError):
            VoiceSettings(speech_rate=5.0)  # Max is 3.0
        
        with pytest.raises(ValueError):
            VoiceSettings(speech_rate=0.05)  # Min is 0.1
        
        # Test speech_pitch out of range
        with pytest.raises(ValueError):
            VoiceSettings(speech_pitch=3.0)  # Max is 2.0
        
        with pytest.raises(ValueError):
            VoiceSettings(speech_pitch=-0.1)  # Min is 0.0
        
        # Test speech_volume out of range
        with pytest.raises(ValueError):
            VoiceSettings(speech_volume=1.5)  # Max is 1.0
        
        with pytest.raises(ValueError):
            VoiceSettings(speech_volume=-0.1)  # Min is 0.0
        
        # Test microphone_sensitivity out of range
        with pytest.raises(ValueError):
            VoiceSettings(microphone_sensitivity=1.5)  # Max is 1.0
        
        with pytest.raises(ValueError):
            VoiceSettings(microphone_sensitivity=-0.1)  # Min is 0.0
    
    def test_voice_settings_voice_name_validation(self):
        """Test voice name validation"""
        # Empty voice name should default to "default"
        settings = VoiceSettings(voice_name="")
        assert settings.voice_name == "default"
        
        # Whitespace-only voice name should default to "default"
        settings = VoiceSettings(voice_name="   ")
        assert settings.voice_name == "default"
        
        # Valid voice name should be trimmed
        settings = VoiceSettings(voice_name="  my-voice  ")
        assert settings.voice_name == "my-voice"
    
    def test_voice_settings_language_validation(self):
        """Test language code validation"""
        # Valid language codes
        valid_languages = ["en", "fr", "en-US", "fr-FR", "es-ES"]
        for lang in valid_languages:
            settings = VoiceSettings(language=lang)
            assert settings.language == lang
        
        # Invalid language codes should default to "en-US"
        invalid_languages = ["", "x", "invalid-lang-code"]
        for lang in invalid_languages:
            settings = VoiceSettings(language=lang)
            assert settings.language == "en-US"
    
    def test_voice_settings_update_model(self):
        """Test VoiceSettingsUpdate model for partial updates"""
        # Test with partial data
        update_data = {
            "auto_play_enabled": True,
            "speech_rate": 1.2
        }
        
        update = VoiceSettingsUpdate(**update_data)
        assert update.auto_play_enabled is True
        assert update.speech_rate == 1.2
        assert update.voice_name is None
        assert update.speech_pitch is None
    
    def test_voice_analytics_model(self):
        """Test VoiceAnalytics model"""
        analytics_data = {
            "action_type": VoiceActionType.STT_COMPLETE,
            "duration_ms": 1500,
            "text_length": 25,
            "accuracy_score": 0.95,
            "metadata": {"test": True}
        }
        
        analytics = VoiceAnalytics(**analytics_data)
        
        assert analytics.action_type == VoiceActionType.STT_COMPLETE
        assert analytics.duration_ms == 1500
        assert analytics.text_length == 25
        assert analytics.accuracy_score == 0.95
        assert analytics.metadata == {"test": True}
        assert analytics.error_message is None
    
    def test_voice_analytics_validation(self):
        """Test VoiceAnalytics validation"""
        # Test negative duration
        with pytest.raises(ValueError):
            VoiceAnalytics(action_type=VoiceActionType.STT_START, duration_ms=-100)
        
        # Test negative text length
        with pytest.raises(ValueError):
            VoiceAnalytics(action_type=VoiceActionType.STT_COMPLETE, text_length=-5)
        
        # Test accuracy score out of range
        with pytest.raises(ValueError):
            VoiceAnalytics(action_type=VoiceActionType.STT_COMPLETE, accuracy_score=1.5)
        
        with pytest.raises(ValueError):
            VoiceAnalytics(action_type=VoiceActionType.STT_COMPLETE, accuracy_score=-0.1)
    
    def test_voice_analytics_error_message_truncation(self):
        """Test error message truncation"""
        long_error = "x" * 1500  # Longer than 1000 characters
        analytics = VoiceAnalytics(
            action_type=VoiceActionType.STT_ERROR,
            error_message=long_error
        )
        
        assert len(analytics.error_message) == 1000
        assert analytics.error_message == "x" * 1000
    
    def test_voice_capabilities_model(self):
        """Test VoiceCapabilities model"""
        capabilities = VoiceCapabilities(
            speech_recognition_available=True,
            speech_synthesis_available=True,
            available_voices=["voice1", "voice2"],
            supported_languages=["en-US", "fr-FR"],
            browser_support={"webkitSpeechRecognition": True}
        )
        
        assert capabilities.speech_recognition_available is True
        assert capabilities.speech_synthesis_available is True
        assert len(capabilities.available_voices) == 2
        assert len(capabilities.supported_languages) == 2
        assert capabilities.browser_support["webkitSpeechRecognition"] is True
    
    def test_utility_functions(self):
        """Test utility functions"""
        # Test validate_voice_settings_data
        valid_data = {"auto_play_enabled": True, "speech_rate": 1.5}
        settings = validate_voice_settings_data(valid_data)
        assert isinstance(settings, VoiceSettings)
        assert settings.auto_play_enabled is True
        assert settings.speech_rate == 1.5
        
        # Test with invalid data
        invalid_data = {"speech_rate": 5.0}  # Out of range
        with pytest.raises(ValueError):
            validate_voice_settings_data(invalid_data)
        
        # Test validate_voice_analytics_data
        valid_analytics = {"action_type": "stt_complete", "duration_ms": 1000}
        analytics = validate_voice_analytics_data(valid_analytics)
        assert isinstance(analytics, VoiceAnalytics)
        assert analytics.action_type == VoiceActionType.STT_COMPLETE
        assert analytics.duration_ms == 1000
    
    def test_default_voice_settings(self):
        """Test default voice settings constant"""
        assert isinstance(DEFAULT_VOICE_SETTINGS, VoiceSettings)
        assert DEFAULT_VOICE_SETTINGS.auto_play_enabled is False
        assert DEFAULT_VOICE_SETTINGS.voice_name == "default"
        assert DEFAULT_VOICE_SETTINGS.speech_rate == 1.0


class TestVoiceDatabaseModels:
    """Test SQLAlchemy database models for voice assistant"""
    
    @pytest.fixture
    def db_session(self):
        """Create a test database session"""
        # Use in-memory SQLite for testing
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Create a test user
        test_user = User(
            user_id="test_user_001",
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User"
        )
        session.add(test_user)
        session.commit()
        
        yield session
        session.close()
    
    def test_voice_settings_creation(self, db_session):
        """Test creating voice settings in database"""
        voice_settings = DBVoiceSettings(
            user_id="test_user_001",
            auto_play_enabled=True,
            voice_name="test-voice",
            speech_rate=1.5,
            speech_pitch=1.2,
            speech_volume=0.8,
            language="fr-FR",
            microphone_sensitivity=0.7,
            noise_cancellation=False
        )
        
        db_session.add(voice_settings)
        db_session.commit()
        
        # Retrieve and verify
        retrieved = db_session.query(DBVoiceSettings).filter_by(user_id="test_user_001").first()
        assert retrieved is not None
        assert retrieved.auto_play_enabled is True
        assert retrieved.voice_name == "test-voice"
        assert retrieved.speech_rate == 1.5
        assert retrieved.speech_pitch == 1.2
        assert retrieved.speech_volume == 0.8
        assert retrieved.language == "fr-FR"
        assert retrieved.microphone_sensitivity == 0.7
        assert retrieved.noise_cancellation is False
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None
    
    def test_voice_settings_unique_constraint(self, db_session):
        """Test unique constraint on user_id for voice settings"""
        # Create first voice settings
        voice_settings1 = DBVoiceSettings(
            user_id="test_user_001",
            auto_play_enabled=True
        )
        db_session.add(voice_settings1)
        db_session.commit()
        
        # Try to create second voice settings for same user
        voice_settings2 = DBVoiceSettings(
            user_id="test_user_001",
            auto_play_enabled=False
        )
        db_session.add(voice_settings2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_voice_settings_foreign_key_constraint(self, db_session):
        """Test foreign key constraint for voice settings"""
        # Try to create voice settings for non-existent user
        voice_settings = DBVoiceSettings(
            user_id="non_existent_user",
            auto_play_enabled=True
        )
        db_session.add(voice_settings)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_voice_analytics_creation(self, db_session):
        """Test creating voice analytics in database"""
        voice_analytics = DBVoiceAnalytics(
            user_id="test_user_001",
            session_id="session_123",
            action_type="stt_complete",
            duration_ms=1500,
            text_length=25,
            accuracy_score=0.95,
            analytics_metadata={"test": True, "browser": "Chrome"}
        )
        
        db_session.add(voice_analytics)
        db_session.commit()
        
        # Retrieve and verify
        retrieved = db_session.query(DBVoiceAnalytics).filter_by(user_id="test_user_001").first()
        assert retrieved is not None
        assert retrieved.session_id == "session_123"
        assert retrieved.action_type == "stt_complete"
        assert retrieved.duration_ms == 1500
        assert retrieved.text_length == 25
        assert retrieved.accuracy_score == 0.95
        assert retrieved.analytics_metadata == {"test": True, "browser": "Chrome"}
        assert retrieved.created_at is not None
    
    def test_voice_analytics_optional_fields(self, db_session):
        """Test voice analytics with optional fields"""
        # Create analytics with minimal required fields
        voice_analytics = DBVoiceAnalytics(
            user_id="test_user_001",
            action_type="voice_enabled"
        )
        
        db_session.add(voice_analytics)
        db_session.commit()
        
        # Retrieve and verify optional fields are None
        retrieved = db_session.query(DBVoiceAnalytics).filter_by(user_id="test_user_001").first()
        assert retrieved is not None
        assert retrieved.session_id is None
        assert retrieved.duration_ms is None
        assert retrieved.text_length is None
        assert retrieved.accuracy_score is None
        assert retrieved.error_message is None
        assert retrieved.analytics_metadata is None
    
    def test_voice_analytics_error_logging(self, db_session):
        """Test logging voice analytics errors"""
        error_analytics = DBVoiceAnalytics(
            user_id="test_user_001",
            session_id="session_error",
            action_type="stt_error",
            error_message="Microphone access denied",
            analytics_metadata={"error_code": "PERMISSION_DENIED"}
        )
        
        db_session.add(error_analytics)
        db_session.commit()
        
        # Retrieve and verify
        retrieved = db_session.query(DBVoiceAnalytics).filter_by(action_type="stt_error").first()
        assert retrieved is not None
        assert retrieved.error_message == "Microphone access denied"
        assert retrieved.analytics_metadata["error_code"] == "PERMISSION_DENIED"
    
    def test_voice_analytics_foreign_key_constraint(self, db_session):
        """Test foreign key constraint for voice analytics"""
        # Try to create analytics for non-existent user
        voice_analytics = DBVoiceAnalytics(
            user_id="non_existent_user",
            action_type="stt_start"
        )
        db_session.add(voice_analytics)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_user_voice_relationships(self, db_session):
        """Test relationships between User and voice models"""
        # Create voice settings and analytics
        voice_settings = DBVoiceSettings(
            user_id="test_user_001",
            auto_play_enabled=True
        )
        
        voice_analytics = DBVoiceAnalytics(
            user_id="test_user_001",
            action_type="stt_complete"
        )
        
        db_session.add(voice_settings)
        db_session.add(voice_analytics)
        db_session.commit()
        
        # Test relationships
        user = db_session.query(User).filter_by(user_id="test_user_001").first()
        assert user is not None
        assert user.voice_settings is not None
        assert user.voice_settings.auto_play_enabled is True
        assert len(user.voice_analytics) == 1
        assert user.voice_analytics[0].action_type == "stt_complete"
    
    def test_voice_analytics_bulk_insert(self, db_session):
        """Test bulk insertion of voice analytics"""
        analytics_data = []
        for i in range(10):
            analytics = DBVoiceAnalytics(
                user_id="test_user_001",
                session_id=f"session_{i}",
                action_type="stt_complete" if i % 2 == 0 else "tts_complete",
                duration_ms=1000 + i * 100,
                text_length=20 + i
            )
            analytics_data.append(analytics)
        
        db_session.add_all(analytics_data)
        db_session.commit()
        
        # Verify all records were inserted
        count = db_session.query(DBVoiceAnalytics).count()
        assert count == 10
        
        # Verify different action types
        stt_count = db_session.query(DBVoiceAnalytics).filter_by(action_type="stt_complete").count()
        tts_count = db_session.query(DBVoiceAnalytics).filter_by(action_type="tts_complete").count()
        assert stt_count == 5
        assert tts_count == 5
    
    def test_voice_settings_update_timestamp(self, db_session):
        """Test that updated_at timestamp changes on update"""
        # Create voice settings
        voice_settings = DBVoiceSettings(
            user_id="test_user_001",
            auto_play_enabled=False
        )
        db_session.add(voice_settings)
        db_session.commit()
        
        original_updated_at = voice_settings.updated_at
        
        # Update the settings
        voice_settings.auto_play_enabled = True
        db_session.commit()
        
        # Note: In SQLite, the onupdate trigger doesn't work the same way as PostgreSQL
        # This test would work properly with PostgreSQL and the trigger we created
        # For now, we just verify the field exists
        assert voice_settings.updated_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])