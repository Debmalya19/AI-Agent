"""
Comprehensive Voice Features Test Suite
Tests all voice functionality including unit tests, integration tests, and performance tests.
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import threading
import concurrent.futures

from backend.database import Base, get_db
from backend.models import User, UserSession, VoiceSettings as VoiceSettingsDB, VoiceAnalytics as VoiceAnalyticsDB
from backend.voice_models import VoiceActionType
from main import app

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_comprehensive_voice.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
def test_user_session():
    """Create test user and session for comprehensive testing"""
    db = TestingSessionLocal()
    
    # Create test user
    test_user = User(
        user_id="comprehensive_test_user",
        username="comptest",
        email="comprehensive@test.com",
        password_hash="hashed_password",
        full_name="Comprehensive Test User"
    )
    db.add(test_user)
    db.commit()
    
    # Create test session
    test_session = UserSession(
        session_id="comprehensive_test_session",
        user_id="comprehensive_test_user",
        token_hash="hashed_token",
        expires_at=datetime.utcnow() + timedelta(hours=24),
        is_active=True
    )
    db.add(test_session)
    db.commit()
    
    yield {
        "user_id": "comprehensive_test_user",
        "session_id": "comprehensive_test_session"
    }
    
    # Cleanup
    db.query(VoiceAnalyticsDB).filter(VoiceAnalyticsDB.user_id == "comprehensive_test_user").delete()
    db.query(VoiceSettingsDB).filter(VoiceSettingsDB.user_id == "comprehensive_test_user").delete()
    db.query(UserSession).filter(UserSession.user_id == "comprehensive_test_user").delete()
    db.query(User).filter(User.user_id == "comprehensive_test_user").delete()
    db.commit()
    db.close()


class TestVoiceIntegrationFlows:
    """Test complete voice conversation flows end-to-end"""
    
    def test_complete_voice_conversation_flow(self, test_user_session):
        """Test complete voice conversation from STT to TTS"""
        session_id = test_user_session["session_id"]
        
        # Step 1: Get voice capabilities
        capabilities_response = client.get("/voice/capabilities")
        assert capabilities_response.status_code == 200
        capabilities = capabilities_response.json()
        assert capabilities["speech_recognition_available"] is True
        
        # Step 2: Configure voice settings
        settings_data = {
            "settings": {
                "auto_play_enabled": True,
                "voice_name": "en-US-Standard-A",
                "speech_rate": 1.0,
                "language": "en-US"
            }
        }
        
        settings_response = client.post(
            "/voice/settings",
            json=settings_data,
            cookies={"session_token": session_id}
        )
        assert settings_response.status_code == 200
        
        # Step 3: Log STT start analytics
        stt_start_analytics = {
            "analytics": {
                "action_type": "stt_start",
                "metadata": {"language": "en-US", "session_start": True}
            }
        }
        
        analytics_response = client.post(
            "/voice/analytics",
            json=stt_start_analytics,
            cookies={"session_token": session_id}
        )
        assert analytics_response.status_code == 200
        
        # Step 4: Log STT completion with transcript
        stt_complete_analytics = {
            "analytics": {
                "action_type": "stt_complete",
                "duration_ms": 2500,
                "text_length": 35,
                "accuracy_score": 0.92,
                "metadata": {
                    "transcript": "Hello, I need help with my account",
                    "confidence": 0.92,
                    "language": "en-US"
                }
            }
        }
        
        analytics_response = client.post(
            "/voice/analytics",
            json=stt_complete_analytics,
            cookies={"session_token": session_id}
        )
        assert analytics_response.status_code == 200
        
        # Step 5: Log TTS start for response
        tts_start_analytics = {
            "analytics": {
                "action_type": "tts_start",
                "text_length": 85,
                "metadata": {
                    "response_text": "I'd be happy to help you with your account. What specific issue are you experiencing?",
                    "voice_name": "en-US-Standard-A"
                }
            }
        }
        
        analytics_response = client.post(
            "/voice/analytics",
            json=tts_start_analytics,
            cookies={"session_token": session_id}
        )
        assert analytics_response.status_code == 200
        
        # Step 6: Log TTS completion
        tts_complete_analytics = {
            "analytics": {
                "action_type": "tts_complete",
                "duration_ms": 4200,
                "text_length": 85,
                "metadata": {"playback_successful": True}
            }
        }
        
        analytics_response = client.post(
            "/voice/analytics",
            json=tts_complete_analytics,
            cookies={"session_token": session_id}
        )
        assert analytics_response.status_code == 200
        
        # Step 7: Verify analytics summary
        summary_response = client.get(
            "/voice/analytics/summary",
            cookies={"session_token": session_id}
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()["summary"]
        
        assert summary["total_actions"] == 4
        assert summary["action_breakdown"]["stt_start"] == 1
        assert summary["action_breakdown"]["stt_complete"] == 1
        assert summary["action_breakdown"]["tts_start"] == 1
        assert summary["action_breakdown"]["tts_complete"] == 1
        assert summary["error_rate"] == 0.0
    
    def test_voice_conversation_with_errors_and_recovery(self, test_user_session):
        """Test voice conversation flow with error handling and recovery"""
        session_id = test_user_session["session_id"]
        
        # Step 1: Log STT error
        stt_error_analytics = {
            "analytics": {
                "action_type": "stt_error",
                "error_message": "Microphone access denied",
                "metadata": {
                    "error_code": "PERMISSION_DENIED",
                    "retry_attempt": 1
                }
            }
        }
        
        analytics_response = client.post(
            "/voice/analytics",
            json=stt_error_analytics,
            cookies={"session_token": session_id}
        )
        assert analytics_response.status_code == 200
        
        # Step 2: Log successful retry
        stt_retry_analytics = {
            "analytics": {
                "action_type": "stt_complete",
                "duration_ms": 3000,
                "text_length": 25,
                "accuracy_score": 0.88,
                "metadata": {
                    "retry_attempt": 2,
                    "previous_error": "PERMISSION_DENIED"
                }
            }
        }
        
        analytics_response = client.post(
            "/voice/analytics",
            json=stt_retry_analytics,
            cookies={"session_token": session_id}
        )
        assert analytics_response.status_code == 200
        
        # Step 3: Log TTS error
        tts_error_analytics = {
            "analytics": {
                "action_type": "tts_error",
                "error_message": "Voice synthesis failed",
                "metadata": {
                    "error_code": "SYNTHESIS_FAILED",
                    "fallback_used": True
                }
            }
        }
        
        analytics_response = client.post(
            "/voice/analytics",
            json=tts_error_analytics,
            cookies={"session_token": session_id}
        )
        assert analytics_response.status_code == 200
        
        # Step 4: Verify error tracking in summary
        summary_response = client.get(
            "/voice/analytics/summary",
            cookies={"session_token": session_id}
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()["summary"]
        
        assert summary["total_actions"] == 3
        assert summary["action_breakdown"]["stt_error"] == 1
        assert summary["action_breakdown"]["stt_complete"] == 1
        assert summary["action_breakdown"]["tts_error"] == 1
        assert summary["error_rate"] == 0.667  # 2 errors out of 3 actions


class TestVoicePerformanceUnderLoad:
    """Test voice processing performance under various conditions"""
    
    def test_concurrent_voice_settings_updates(self, test_user_session):
        """Test concurrent voice settings updates"""
        session_id = test_user_session["session_id"]
        
        def update_settings(setting_value):
            settings_data = {
                "settings": {
                    "speech_rate": setting_value,
                    "auto_play_enabled": setting_value > 1.5
                }
            }
            
            response = client.post(
                "/voice/settings",
                json=settings_data,
                cookies={"session_token": session_id}
            )
            return response.status_code == 200
        
        # Test concurrent updates
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(update_settings, 1.0 + (i * 0.1))
                for i in range(10)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All updates should succeed
        assert all(results), "Some concurrent updates failed"
        
        # Verify final state
        final_response = client.get(
            "/voice/settings",
            cookies={"session_token": session_id}
        )
        assert final_response.status_code == 200
    
    def test_high_volume_analytics_logging(self, test_user_session):
        """Test high volume analytics logging performance"""
        session_id = test_user_session["session_id"]
        
        start_time = time.time()
        
        def log_analytics(action_index):
            analytics_data = {
                "analytics": {
                    "action_type": "stt_complete",
                    "duration_ms": 1000 + (action_index * 10),
                    "text_length": 20 + action_index,
                    "accuracy_score": 0.9,
                    "metadata": {"batch_test": True, "index": action_index}
                }
            }
            
            response = client.post(
                "/voice/analytics",
                json=analytics_data,
                cookies={"session_token": session_id}
            )
            return response.status_code == 200
        
        # Log 50 analytics entries concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(log_analytics, i)
                for i in range(50)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All logs should succeed
        assert all(results), "Some analytics logging failed"
        
        # Performance check: should complete within reasonable time
        assert total_time < 10.0, f"High volume logging took too long: {total_time}s"
        
        # Verify all entries were logged
        summary_response = client.get(
            "/voice/analytics/summary",
            cookies={"session_token": session_id}
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()["summary"]
        assert summary["total_actions"] == 50
    
    def test_voice_api_response_times(self, test_user_session):
        """Test voice API response times under normal load"""
        session_id = test_user_session["session_id"]
        
        # Test capabilities endpoint performance
        start_time = time.time()
        for _ in range(10):
            response = client.get("/voice/capabilities")
            assert response.status_code == 200
        capabilities_time = (time.time() - start_time) / 10
        
        # Test settings endpoint performance
        settings_data = {"settings": {"speech_rate": 1.2}}
        start_time = time.time()
        for _ in range(10):
            response = client.post(
                "/voice/settings",
                json=settings_data,
                cookies={"session_token": session_id}
            )
            assert response.status_code == 200
        settings_time = (time.time() - start_time) / 10
        
        # Test analytics endpoint performance
        analytics_data = {
            "analytics": {
                "action_type": "stt_complete",
                "duration_ms": 1500,
                "text_length": 25
            }
        }
        start_time = time.time()
        for _ in range(10):
            response = client.post(
                "/voice/analytics",
                json=analytics_data,
                cookies={"session_token": session_id}
            )
            assert response.status_code == 200
        analytics_time = (time.time() - start_time) / 10
        
        # Performance assertions (reasonable response times)
        assert capabilities_time < 0.1, f"Capabilities endpoint too slow: {capabilities_time}s"
        assert settings_time < 0.2, f"Settings endpoint too slow: {settings_time}s"
        assert analytics_time < 0.2, f"Analytics endpoint too slow: {analytics_time}s"


class TestVoiceNetworkConditions:
    """Test voice processing under various network conditions"""
    
    def test_voice_api_with_network_delays(self, test_user_session):
        """Test voice API behavior with simulated network delays"""
        session_id = test_user_session["session_id"]
        
        # Simulate network delay by adding sleep in request
        def delayed_request(delay_seconds):
            time.sleep(delay_seconds)
            response = client.get(
                "/voice/settings",
                cookies={"session_token": session_id}
            )
            return response.status_code == 200
        
        # Test with various delays
        delays = [0.1, 0.5, 1.0, 2.0]
        results = []
        
        for delay in delays:
            start_time = time.time()
            success = delayed_request(delay)
            total_time = time.time() - start_time
            
            results.append({
                "delay": delay,
                "success": success,
                "total_time": total_time
            })
        
        # All requests should succeed despite delays
        assert all(r["success"] for r in results), "Some delayed requests failed"
        
        # Verify timing is reasonable (delay + processing time)
        for result in results:
            expected_min_time = result["delay"]
            assert result["total_time"] >= expected_min_time, f"Request completed too quickly: {result}"
    
    def test_voice_api_timeout_handling(self, test_user_session):
        """Test voice API timeout handling"""
        session_id = test_user_session["session_id"]
        
        # Test with very large analytics payload (might cause timeout)
        large_metadata = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}
        
        analytics_data = {
            "analytics": {
                "action_type": "stt_complete",
                "duration_ms": 1500,
                "text_length": 25,
                "metadata": large_metadata
            }
        }
        
        start_time = time.time()
        response = client.post(
            "/voice/analytics",
            json=analytics_data,
            cookies={"session_token": session_id}
        )
        request_time = time.time() - start_time
        
        # Should either succeed or fail gracefully (not hang)
        assert response.status_code in [200, 413, 422], f"Unexpected status: {response.status_code}"
        assert request_time < 30.0, f"Request took too long: {request_time}s"


class TestVoiceDataIntegrity:
    """Test voice data integrity and consistency"""
    
    def test_voice_settings_data_consistency(self, test_user_session):
        """Test voice settings data consistency across operations"""
        session_id = test_user_session["session_id"]
        user_id = test_user_session["user_id"]
        
        # Create initial settings
        initial_settings = {
            "settings": {
                "auto_play_enabled": True,
                "voice_name": "test-voice",
                "speech_rate": 1.5,
                "language": "en-GB"
            }
        }
        
        response = client.post(
            "/voice/settings",
            json=initial_settings,
            cookies={"session_token": session_id}
        )
        assert response.status_code == 200
        
        # Verify settings were stored correctly
        response = client.get(
            "/voice/settings",
            cookies={"session_token": session_id}
        )
        assert response.status_code == 200
        stored_settings = response.json()["settings"]
        
        assert stored_settings["auto_play_enabled"] is True
        assert stored_settings["voice_name"] == "test-voice"
        assert stored_settings["speech_rate"] == 1.5
        assert stored_settings["language"] == "en-GB"
        
        # Update partial settings
        partial_update = {
            "settings": {
                "speech_rate": 2.0,
                "auto_play_enabled": False
            }
        }
        
        response = client.post(
            "/voice/settings",
            json=partial_update,
            cookies={"session_token": session_id}
        )
        assert response.status_code == 200
        
        # Verify partial update maintained other settings
        response = client.get(
            "/voice/settings",
            cookies={"session_token": session_id}
        )
        assert response.status_code == 200
        updated_settings = response.json()["settings"]
        
        assert updated_settings["auto_play_enabled"] is False  # Updated
        assert updated_settings["speech_rate"] == 2.0  # Updated
        assert updated_settings["voice_name"] == "test-voice"  # Unchanged
        assert updated_settings["language"] == "en-GB"  # Unchanged
    
    def test_voice_analytics_data_integrity(self, test_user_session):
        """Test voice analytics data integrity and aggregation"""
        session_id = test_user_session["session_id"]
        
        # Log various analytics entries
        analytics_entries = [
            {
                "action_type": "stt_start",
                "metadata": {"session_start": True}
            },
            {
                "action_type": "stt_complete",
                "duration_ms": 1500,
                "text_length": 25,
                "accuracy_score": 0.9
            },
            {
                "action_type": "tts_start",
                "text_length": 50
            },
            {
                "action_type": "tts_complete",
                "duration_ms": 2500,
                "text_length": 50
            },
            {
                "action_type": "stt_error",
                "error_message": "Network timeout"
            }
        ]
        
        # Log all entries
        for entry in analytics_entries:
            response = client.post(
                "/voice/analytics",
                json={"analytics": entry},
                cookies={"session_token": session_id}
            )
            assert response.status_code == 200
        
        # Verify summary aggregation
        response = client.get(
            "/voice/analytics/summary",
            cookies={"session_token": session_id}
        )
        assert response.status_code == 200
        summary = response.json()["summary"]
        
        assert summary["total_actions"] == 5
        assert summary["action_breakdown"]["stt_start"] == 1
        assert summary["action_breakdown"]["stt_complete"] == 1
        assert summary["action_breakdown"]["tts_start"] == 1
        assert summary["action_breakdown"]["tts_complete"] == 1
        assert summary["action_breakdown"]["stt_error"] == 1
        
        # Verify error rate calculation
        expected_error_rate = 1 / 5  # 1 error out of 5 actions
        assert abs(summary["error_rate"] - expected_error_rate) < 0.001
        
        # Verify average duration calculation (only for completed actions)
        expected_avg_duration = (1500 + 2500) / 2  # Only stt_complete and tts_complete have durations
        assert abs(summary["average_duration_ms"] - expected_avg_duration) < 0.001


class TestVoiceSecurityAndValidation:
    """Test voice security and input validation"""
    
    def test_voice_settings_validation_boundaries(self, test_user_session):
        """Test voice settings validation at boundaries"""
        session_id = test_user_session["session_id"]
        
        # Test valid boundary values
        valid_boundary_tests = [
            {"speech_rate": 0.1},  # Minimum
            {"speech_rate": 3.0},  # Maximum
            {"speech_pitch": 0.0},  # Minimum
            {"speech_pitch": 2.0},  # Maximum
            {"speech_volume": 0.0},  # Minimum
            {"speech_volume": 1.0},  # Maximum
        ]
        
        for test_settings in valid_boundary_tests:
            response = client.post(
                "/voice/settings",
                json={"settings": test_settings},
                cookies={"session_token": session_id}
            )
            assert response.status_code == 200, f"Valid boundary test failed: {test_settings}"
        
        # Test invalid boundary values
        invalid_boundary_tests = [
            {"speech_rate": 0.05},  # Below minimum
            {"speech_rate": 3.5},   # Above maximum
            {"speech_pitch": -0.1}, # Below minimum
            {"speech_pitch": 2.5},  # Above maximum
            {"speech_volume": -0.1}, # Below minimum
            {"speech_volume": 1.5},  # Above maximum
        ]
        
        for test_settings in invalid_boundary_tests:
            response = client.post(
                "/voice/settings",
                json={"settings": test_settings},
                cookies={"session_token": session_id}
            )
            assert response.status_code == 422, f"Invalid boundary test should fail: {test_settings}"
    
    def test_voice_analytics_input_sanitization(self, test_user_session):
        """Test voice analytics input sanitization"""
        session_id = test_user_session["session_id"]
        
        # Test with potentially malicious input
        malicious_inputs = [
            {
                "action_type": "stt_complete",
                "error_message": "<script>alert('xss')</script>",
                "metadata": {"malicious": "<img src=x onerror=alert(1)>"}
            },
            {
                "action_type": "tts_error",
                "error_message": "'; DROP TABLE voice_analytics; --",
                "metadata": {"sql_injection": "1' OR '1'='1"}
            }
        ]
        
        for malicious_input in malicious_inputs:
            response = client.post(
                "/voice/analytics",
                json={"analytics": malicious_input},
                cookies={"session_token": session_id}
            )
            # Should either succeed (with sanitized input) or fail validation
            assert response.status_code in [200, 422], f"Unexpected response to malicious input: {response.status_code}"
        
        # Verify system is still functional after malicious input attempts
        normal_analytics = {
            "analytics": {
                "action_type": "stt_complete",
                "duration_ms": 1500,
                "text_length": 25
            }
        }
        
        response = client.post(
            "/voice/analytics",
            json=normal_analytics,
            cookies={"session_token": session_id}
        )
        assert response.status_code == 200, "System should remain functional after malicious input attempts"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])