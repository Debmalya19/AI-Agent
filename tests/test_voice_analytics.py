"""
Test suite for voice analytics and performance monitoring system.

This module tests:
- Voice performance tracking
- Voice usage analytics collection
- Voice error logging and reporting
- Voice feature adoption metrics
- Integration with existing memory layer and chat analytics
"""

import pytest
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from backend.voice_analytics import (
    VoiceAnalyticsManager, 
    VoicePerformanceMetrics, 
    VoiceUsageReport,
    VoiceErrorAnalysis,
    VoiceFeatureType
)
from backend.voice_models import VoiceActionType
from backend.models import VoiceAnalytics as VoiceAnalyticsDB, User
from backend.database import SessionLocal


class TestVoiceAnalyticsManager:
    """Test the VoiceAnalyticsManager class"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        session = Mock(spec=Session)
        session.query.return_value = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        return session
    
    @pytest.fixture
    def analytics_manager(self, mock_db_session):
        """Create a VoiceAnalyticsManager instance with mock database"""
        return VoiceAnalyticsManager(mock_db_session)
    
    def test_record_voice_performance_success(self, analytics_manager, mock_db_session):
        """Test recording voice performance metrics successfully"""
        # Test data
        user_id = "test_user_123"
        action_type = VoiceActionType.STT_COMPLETE
        duration_ms = 1500
        text_length = 25
        accuracy_score = 0.95
        metadata = {"browser": "Chrome", "language": "en-US"}
        
        # Execute
        result = analytics_manager.record_voice_performance(
            user_id=user_id,
            action_type=action_type,
            duration_ms=duration_ms,
            text_length=text_length,
            accuracy_score=accuracy_score,
            metadata=metadata
        )
        
        # Verify
        assert result is True
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        
        # Check the analytics record was created correctly
        call_args = mock_db_session.add.call_args[0][0]
        assert isinstance(call_args, VoiceAnalyticsDB)
        assert call_args.user_id == user_id
        assert call_args.action_type == action_type.value
        assert call_args.duration_ms == duration_ms
        assert call_args.text_length == text_length
        assert call_args.accuracy_score == accuracy_score
        assert call_args.analytics_metadata == metadata
    
    def test_record_voice_performance_sanitizes_metadata(self, analytics_manager, mock_db_session):
        """Test that sensitive data is removed from metadata"""
        # Test data with sensitive information
        metadata = {
            "browser": "Chrome",
            "audio_data": "sensitive_audio_content",
            "raw_audio": b"binary_audio_data",
            "settings": {"voice": "en-US"}
        }
        
        # Execute
        analytics_manager.record_voice_performance(
            user_id="test_user",
            action_type=VoiceActionType.STT_START,
            metadata=metadata
        )
        
        # Verify sensitive data was removed
        call_args = mock_db_session.add.call_args[0][0]
        stored_metadata = call_args.analytics_metadata
        
        assert "browser" in stored_metadata
        assert "settings" in stored_metadata
        assert "audio_data" not in stored_metadata
        assert "raw_audio" not in stored_metadata
    
    def test_record_voice_error(self, analytics_manager, mock_db_session):
        """Test recording voice errors"""
        # Test data
        user_id = "test_user_123"
        error_type = "network"
        error_message = "Connection timeout"
        context = {"browser": "Firefox", "connection": "wifi"}
        recovery_action = "retry_with_delay"
        
        # Execute
        result = analytics_manager.record_voice_error(
            user_id=user_id,
            error_type=error_type,
            error_message=error_message,
            context=context,
            recovery_action=recovery_action
        )
        
        # Verify
        assert result is True
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        
        # Check the error record
        call_args = mock_db_session.add.call_args[0][0]
        assert call_args.user_id == user_id
        assert call_args.error_message == error_message
        assert call_args.analytics_metadata["error_type"] == error_type
        assert call_args.analytics_metadata["recovery_action"] == recovery_action
    
    def test_record_feature_adoption(self, analytics_manager, mock_db_session):
        """Test recording feature adoption metrics"""
        # Test data
        user_id = "test_user_123"
        feature_type = VoiceFeatureType.AUTO_PLAY
        enabled = True
        settings_data = {"autoPlayEnabled": True, "volume": 0.8}
        
        # Execute
        result = analytics_manager.record_feature_adoption(
            user_id=user_id,
            feature_type=feature_type,
            enabled=enabled,
            settings_data=settings_data
        )
        
        # Verify
        assert result is True
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        
        # Check the adoption record
        call_args = mock_db_session.add.call_args[0][0]
        assert call_args.user_id == user_id
        assert call_args.action_type == VoiceActionType.VOICE_ENABLED.value
        assert call_args.analytics_metadata["feature_type"] == feature_type.value
        assert call_args.analytics_metadata["enabled"] == enabled
    
    def test_get_voice_usage_report_with_data(self, analytics_manager, mock_db_session):
        """Test generating voice usage report with data"""
        # Mock database query results
        mock_analytics = [
            Mock(
                action_type="stt_complete",
                duration_ms=1200,
                error_message=None,
                created_at=datetime.now(timezone.utc)
            ),
            Mock(
                action_type="tts_complete", 
                duration_ms=800,
                error_message=None,
                created_at=datetime.now(timezone.utc)
            ),
            Mock(
                action_type="stt_error",
                duration_ms=None,
                error_message="Network error",
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        mock_db_session.query.return_value.filter.return_value.all.return_value = mock_analytics
        
        # Execute
        report = analytics_manager.get_voice_usage_report("test_user", 30)
        
        # Verify
        assert report is not None
        assert isinstance(report, VoiceUsageReport)
        assert report.user_id == "test_user"
        assert report.total_voice_interactions == 3
        assert report.stt_usage_count == 2  # stt_complete + stt_error
        assert report.tts_usage_count == 1
        assert report.voice_error_count == 1
        assert report.avg_stt_processing_time == 1200.0  # Only successful STT
        assert report.avg_tts_processing_time == 800.0
    
    def test_get_voice_usage_report_no_data(self, analytics_manager, mock_db_session):
        """Test generating voice usage report with no data"""
        # Mock empty query result
        mock_db_session.query.return_value.filter.return_value.all.return_value = []
        
        # Execute
        report = analytics_manager.get_voice_usage_report("test_user", 30)
        
        # Verify
        assert report is None
    
    def test_get_voice_performance_metrics(self, analytics_manager, mock_db_session):
        """Test getting voice performance metrics"""
        # Mock database query results
        mock_analytics = [
            Mock(
                action_type="stt_complete",
                duration_ms=1200,
                error_message=None,
                accuracy_score=0.95,
                created_at=datetime.now(timezone.utc)
            ),
            Mock(
                action_type="stt_complete",
                duration_ms=1100,
                error_message=None,
                accuracy_score=0.92,
                created_at=datetime.now(timezone.utc)
            ),
            Mock(
                action_type="stt_error",
                duration_ms=None,
                error_message="Audio error",
                accuracy_score=None,
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        mock_db_session.query.return_value.filter.return_value.all.return_value = mock_analytics
        
        # Execute
        metrics = analytics_manager.get_voice_performance_metrics(30)
        
        # Verify
        assert len(metrics) == 2  # stt_complete and stt_error grouped separately
        
        # Find the stt_complete metric
        stt_metric = next((m for m in metrics if m.feature_type == "stt_complete"), None)
        assert stt_metric is not None
        assert stt_metric.usage_count == 2
        assert stt_metric.success_rate == 1.0  # Both stt_complete records were successful
        assert stt_metric.avg_processing_time == 1150.0  # Average of 1200 and 1100
        assert stt_metric.quality_score == 0.935  # Average of 0.95 and 0.92
    
    def test_analyze_voice_errors(self, analytics_manager, mock_db_session):
        """Test analyzing voice errors for troubleshooting"""
        # Mock error records
        mock_errors = [
            Mock(
                error_message="Network connection timeout",
                duration_ms=2000,
                analytics_metadata={"context": {"browser": "Chrome"}}
            ),
            Mock(
                error_message="Network connection failed",
                duration_ms=1500,
                analytics_metadata={"context": {"browser": "Firefox"}}
            ),
            Mock(
                error_message="Microphone permission denied",
                duration_ms=None,
                analytics_metadata={"context": {"browser": "Safari"}}
            )
        ]
        
        mock_db_session.query.return_value.filter.return_value.all.return_value = mock_errors
        
        # Execute
        error_analysis = analytics_manager.analyze_voice_errors(30)
        
        # Verify
        assert len(error_analysis) >= 1
        
        # Check network error analysis
        network_analysis = next((a for a in error_analysis if a.error_type == "network"), None)
        assert network_analysis is not None
        assert network_analysis.frequency == 2
        assert network_analysis.avg_recovery_time == 1750.0  # Average of 2000 and 1500
        assert len(network_analysis.suggested_fixes) > 0
    
    def test_get_voice_adoption_metrics(self, analytics_manager, mock_db_session):
        """Test getting voice feature adoption metrics"""
        # Mock user query
        mock_users = [("user1",), ("user2",), ("user3",)]
        mock_db_session.query.return_value.filter.return_value.distinct.return_value.all.return_value = mock_users
        
        # Mock total users count
        mock_db_session.query.return_value.scalar.return_value = 100
        
        # Mock feature adoption queries
        mock_db_session.query.return_value.filter.return_value.count.return_value = 2
        
        # Execute
        adoption_metrics = analytics_manager.get_voice_adoption_metrics(30)
        
        # Verify
        assert "total_voice_users" in adoption_metrics
        assert "voice_adoption_rate" in adoption_metrics
        assert "feature_adoption" in adoption_metrics
        assert adoption_metrics["total_voice_users"] == 3
        assert adoption_metrics["voice_adoption_rate"] == 0.03  # 3/100
    
    def test_integrate_with_chat_analytics(self, analytics_manager, mock_db_session):
        """Test integration with chat analytics"""
        # Test data
        session_id = "chat_session_123"
        user_id = "test_user"
        voice_metrics = {
            "total_time": 5000,
            "quality_score": 0.9,
            "interactions": 3
        }
        
        # Execute
        result = analytics_manager.integrate_with_chat_analytics(
            session_id=session_id,
            user_id=user_id,
            voice_enabled=True,
            voice_metrics=voice_metrics
        )
        
        # Verify
        assert result is True
        # Should have recorded voice usage and tool usage
        assert mock_db_session.add.call_count >= 1
        assert mock_db_session.commit.call_count >= 1
    
    def test_cleanup_old_analytics(self, analytics_manager, mock_db_session):
        """Test cleanup of old analytics data"""
        # Mock delete and anonymize operations
        mock_db_session.query.return_value.filter.return_value.delete.return_value = 5
        
        # Mock records for anonymization
        mock_records = [
            Mock(user_id="user1", analytics_metadata={"browser": "Chrome"}),
            Mock(user_id="user2", analytics_metadata={"ip": "192.168.1.1"})
        ]
        mock_db_session.query.return_value.filter.return_value.all.return_value = mock_records
        
        # Execute
        cleanup_stats = analytics_manager.cleanup_old_analytics(
            retention_days=90,
            anonymize_after_days=30
        )
        
        # Verify
        assert cleanup_stats["deleted_records"] == 5
        assert cleanup_stats["anonymized_records"] == 2
        
        # Check that user_ids were anonymized
        for record in mock_records:
            assert record.user_id == "anonymous"
    
    def test_error_categorization(self, analytics_manager):
        """Test error message categorization"""
        # Test various error messages
        test_cases = [
            ("Network connection timeout", "network"),
            ("Microphone permission denied", "permission"),
            ("Audio-capture failed", "audio"),  # Fixed: use hyphen to match pattern
            ("Speech synthesis error", "synthesis"),
            ("Recognition failed", "recognition"),
            ("Unknown error occurred", "other")
        ]
        
        for error_message, expected_category in test_cases:
            category = analytics_manager._categorize_error(error_message)
            assert category == expected_category, f"Expected '{expected_category}' for '{error_message}', got '{category}'"
    
    def test_metadata_sanitization(self, analytics_manager):
        """Test metadata sanitization removes sensitive data"""
        # Test metadata with sensitive information
        metadata = {
            "browser": "Chrome",
            "audio_data": "sensitive_content",
            "raw_audio": b"binary_data",
            "microphone_data": "mic_info",
            "speech_data": "speech_content",
            "settings": {
                "volume": 0.8,
                "audio_data": "nested_sensitive"
            }
        }
        
        sanitized = analytics_manager._sanitize_metadata(metadata)
        
        # Verify sensitive keys are removed
        assert "browser" in sanitized
        assert "settings" in sanitized
        assert sanitized["settings"]["volume"] == 0.8
        
        # Verify sensitive data is removed
        assert "audio_data" not in sanitized
        assert "raw_audio" not in sanitized
        assert "microphone_data" not in sanitized
        assert "speech_data" not in sanitized
        assert "audio_data" not in sanitized["settings"]
    
    def test_performance_metrics_calculation(self, analytics_manager):
        """Test performance metrics calculation"""
        # Mock analytics records
        records = [
            Mock(
                duration_ms=1200,
                error_message=None,
                accuracy_score=0.95
            ),
            Mock(
                duration_ms=1100,
                error_message=None,
                accuracy_score=0.92
            ),
            Mock(
                duration_ms=None,
                error_message="Error occurred",
                accuracy_score=None
            )
        ]
        
        # Execute
        metric = analytics_manager._calculate_performance_metric("stt_complete", records)
        
        # Verify
        assert metric is not None
        assert metric.feature_type == "stt_complete"
        assert metric.usage_count == 3
        assert metric.success_rate == 2/3  # 2 successful out of 3
        assert metric.error_rate == 1/3   # 1 error out of 3
        assert metric.avg_processing_time == 1150.0  # Average of 1200 and 1100
        assert metric.quality_score == 0.935  # Average of 0.95 and 0.92


class TestVoiceAnalyticsIntegration:
    """Test voice analytics integration with other systems"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        session = Mock(spec=Session)
        session.query.return_value = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        return session
    
    @pytest.fixture
    def mock_tool_analytics(self):
        """Mock tool usage analytics"""
        with patch('backend.voice_analytics.ToolUsageAnalytics') as mock:
            mock_instance = Mock()
            mock.return_value = mock_instance
            yield mock_instance
    
    def test_tool_analytics_integration(self, mock_db_session, mock_tool_analytics):
        """Test integration with existing tool analytics"""
        analytics_manager = VoiceAnalyticsManager(mock_db_session)
        
        # Test chat analytics integration
        result = analytics_manager.integrate_with_chat_analytics(
            session_id="test_session",
            user_id="test_user",
            voice_enabled=True,
            voice_metrics={"quality_score": 0.9}  # Fixed: use correct key
        )
        
        assert result is True
        # Verify tool analytics was called
        mock_tool_analytics.record_tool_usage.assert_called_once()
        
        # Check the call arguments
        call_args = mock_tool_analytics.record_tool_usage.call_args
        assert call_args[1]['tool_name'] == 'VoiceAssistant'
        assert call_args[1]['success'] is True
        assert call_args[1]['response_quality'] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])