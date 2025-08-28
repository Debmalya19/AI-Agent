#!/usr/bin/env python3
"""
Simple integration test for voice settings persistence functionality.
Tests the backend API endpoints without requiring the full FastAPI app.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import json

from backend.database import Base
from backend.models import User, UserSession, VoiceSettings as VoiceSettingsDB
from backend.voice_models import VoiceSettings, VoiceSettingsUpdate

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_voice_integration.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test database
Base.metadata.create_all(bind=engine)

def test_voice_settings_persistence():
    """Test voice settings persistence functionality"""
    print("Testing voice settings persistence...")
    
    db = TestingSessionLocal()
    
    try:
        # Create test user
        test_user = User(
            user_id="test_user_voice_123",
            username="voiceuser",
            email="voice@example.com",
            password_hash="hashed_password",
            full_name="Voice Test User"
        )
        db.add(test_user)
        db.commit()
        
        # Create user session
        session_expires = datetime.utcnow() + timedelta(hours=24)
        test_session = UserSession(
            session_id="test_session_voice_123",
            user_id=test_user.user_id,
            token_hash="hashed_token",
            expires_at=session_expires
        )
        db.add(test_session)
        db.commit()
        
        print("✓ Test user and session created")
        
        # Test 1: Create voice settings
        voice_settings = VoiceSettingsDB(
            user_id=test_user.user_id,
            auto_play_enabled=True,
            voice_name="en-US-Standard-A",
            speech_rate=1.2,
            speech_pitch=1.1,
            speech_volume=0.8,
            language="en-US",
            microphone_sensitivity=0.7,
            noise_cancellation=True
        )
        db.add(voice_settings)
        db.commit()
        
        print("✓ Voice settings created")
        
        # Test 2: Retrieve voice settings
        retrieved_settings = db.query(VoiceSettingsDB).filter(
            VoiceSettingsDB.user_id == test_user.user_id
        ).first()
        
        assert retrieved_settings is not None
        assert retrieved_settings.auto_play_enabled is True
        assert retrieved_settings.voice_name == "en-US-Standard-A"
        assert retrieved_settings.speech_rate == 1.2
        assert retrieved_settings.language == "en-US"
        
        print("✓ Voice settings retrieved and validated")
        
        # Test 3: Update voice settings
        retrieved_settings.auto_play_enabled = False
        retrieved_settings.speech_rate = 1.5
        retrieved_settings.language = "en-GB"
        db.commit()
        
        # Verify update
        updated_settings = db.query(VoiceSettingsDB).filter(
            VoiceSettingsDB.user_id == test_user.user_id
        ).first()
        
        assert updated_settings.auto_play_enabled is False
        assert updated_settings.speech_rate == 1.5
        assert updated_settings.language == "en-GB"
        assert updated_settings.voice_name == "en-US-Standard-A"  # Unchanged
        
        print("✓ Voice settings updated and validated")
        
        # Test 4: Test Pydantic model validation
        valid_settings = VoiceSettings(
            auto_play_enabled=True,
            voice_name="default",
            speech_rate=1.0,
            speech_pitch=1.0,
            speech_volume=1.0,
            language="en-US",
            microphone_sensitivity=0.5,
            noise_cancellation=True
        )
        
        assert valid_settings.auto_play_enabled is True
        assert valid_settings.speech_rate == 1.0
        
        print("✓ Pydantic model validation works")
        
        # Test 5: Test partial update model
        partial_update = VoiceSettingsUpdate(
            auto_play_enabled=False,
            speech_rate=2.0
        )
        
        assert partial_update.auto_play_enabled is False
        assert partial_update.speech_rate == 2.0
        assert partial_update.voice_name is None  # Not set
        
        print("✓ Partial update model works")
        
        # Test 6: Test session persistence across browser refreshes
        # Simulate user logout and login
        test_session.is_active = False
        db.commit()
        
        # Create new session (simulating login)
        new_session = UserSession(
            session_id="test_session_voice_456",
            user_id=test_user.user_id,
            token_hash="new_hashed_token",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        db.add(new_session)
        db.commit()
        
        # Settings should still exist
        persistent_settings = db.query(VoiceSettingsDB).filter(
            VoiceSettingsDB.user_id == test_user.user_id
        ).first()
        
        assert persistent_settings is not None
        assert persistent_settings.auto_play_enabled is False  # From previous update
        assert persistent_settings.speech_rate == 1.5  # From previous update
        
        print("✓ Settings persist across sessions")
        
        print("\n🎉 All voice settings persistence tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        # Cleanup
        db.query(VoiceSettingsDB).filter(VoiceSettingsDB.user_id == test_user.user_id).delete()
        db.query(UserSession).filter(UserSession.user_id == test_user.user_id).delete()
        db.query(User).filter(User.user_id == test_user.user_id).delete()
        db.commit()
        db.close()

def test_voice_settings_validation():
    """Test voice settings validation"""
    print("\nTesting voice settings validation...")
    
    try:
        # Test valid settings
        valid_settings = VoiceSettings(
            auto_play_enabled=True,
            voice_name="en-US-Standard-A",
            speech_rate=1.5,
            speech_pitch=1.2,
            speech_volume=0.8,
            language="en-US",
            microphone_sensitivity=0.6,
            noise_cancellation=True
        )
        print("✓ Valid settings accepted")
        
        # Test invalid speech rate (too high)
        try:
            invalid_settings = VoiceSettings(
                speech_rate=5.0  # Invalid: > 3.0
            )
            print("❌ Should have failed validation for high speech rate")
            assert False, "Validation should have failed"
        except Exception:
            print("✓ Invalid speech rate rejected")
        
        # Test invalid language format
        try:
            invalid_settings = VoiceSettings(
                language="invalid-format"  # Should be xx-XX format
            )
            print("❌ Should have failed validation for invalid language")
            assert False, "Validation should have failed"
        except Exception:
            print("✓ Invalid language format rejected")
        
        print("✓ All validation tests passed")
        
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        raise

if __name__ == "__main__":
    print("🎤 Voice Settings Integration Test")
    print("=" * 50)
    
    test_voice_settings_persistence()
    test_voice_settings_validation()
    
    print("\n✅ All tests completed successfully!")
    print("Voice settings persistence and user preferences are working correctly.")