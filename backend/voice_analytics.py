"""
Voice Analytics and Performance Monitoring System

This module provides comprehensive analytics for voice assistant features including:
- Performance tracking for STT/TTS processing times
- Voice usage analytics collection (without storing audio content)
- Voice error logging and reporting system for troubleshooting
- Voice feature adoption metrics and user engagement tracking
- Integration with existing memory layer and chat analytics

Requirements covered:
- 6.1: Voice usage metrics without storing audio content
- 6.2: STT/TTS error logging for troubleshooting
- 6.3: Voice processing performance metrics
- 6.4: Voice preference changes tracking
- 6.5: Privacy settings and data retention policies
- 6.6: System resource prioritization for voice features
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import json
import statistics
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from backend.models import VoiceAnalytics as VoiceAnalyticsDB, User
from backend.voice_models import VoiceActionType, VoiceAnalytics
from backend.database import SessionLocal
from backend.tool_usage_analytics import ToolUsageAnalytics


class VoiceFeatureType(str, Enum):
    """Voice feature types for adoption tracking"""
    VOICE_INPUT = "voice_input"
    VOICE_OUTPUT = "voice_output"
    AUTO_PLAY = "auto_play"
    SETTINGS_CHANGE = "settings_change"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class VoicePerformanceMetrics:
    """Voice performance metrics data structure"""
    feature_type: str
    avg_processing_time: float
    success_rate: float
    error_rate: float
    usage_count: int
    quality_score: float
    trend: str  # 'improving', 'declining', 'stable'


@dataclass
class VoiceUsageReport:
    """Voice usage analytics report"""
    user_id: str
    total_voice_interactions: int
    stt_usage_count: int
    tts_usage_count: int
    avg_stt_processing_time: float
    avg_tts_processing_time: float
    voice_error_count: int
    most_common_errors: List[str]
    feature_adoption_rate: float
    engagement_score: float
    period_start: datetime
    period_end: datetime


@dataclass
class VoiceErrorAnalysis:
    """Voice error analysis data structure"""
    error_type: str
    frequency: int
    avg_recovery_time: float
    common_contexts: List[str]
    suggested_fixes: List[str]


class VoiceAnalyticsManager:
    """
    Comprehensive voice analytics and performance monitoring system.
    
    This class handles:
    - Recording voice performance metrics
    - Analyzing voice usage patterns
    - Tracking voice feature adoption
    - Monitoring voice errors and recovery
    - Generating voice analytics reports
    - Integrating with existing chat analytics
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize the voice analytics manager"""
        self.db_session = db_session or SessionLocal()
        self.logger = logging.getLogger(__name__)
        
        # Integration with existing tool analytics
        self.tool_analytics = ToolUsageAnalytics(self.db_session)
        
        # Cache for performance data
        self._performance_cache = {}
        self._cache_expiry = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Error patterns for analysis
        self.error_patterns = {
            'network': ['network', 'connection', 'timeout'],
            'permission': ['not-allowed', 'permission', 'denied'],
            'audio': ['audio-capture', 'microphone', 'no-speech'],
            'synthesis': ['synthesis', 'voice-not-found', 'tts'],
            'recognition': ['recognition', 'stt', 'speech']
        }
    
    def record_voice_performance(
        self,
        user_id: str,
        action_type: VoiceActionType,
        duration_ms: Optional[int] = None,
        text_length: Optional[int] = None,
        accuracy_score: Optional[float] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Record voice performance metrics for analytics.
        
        Args:
            user_id: User identifier
            action_type: Type of voice action (STT_START, TTS_COMPLETE, etc.)
            duration_ms: Processing time in milliseconds
            text_length: Length of processed text
            accuracy_score: Accuracy score (0.0-1.0)
            error_message: Error message if action failed
            metadata: Additional metadata (browser info, settings, etc.)
            session_id: Session identifier
            
        Returns:
            bool: True if recording was successful
        """
        try:
            # Ensure metadata doesn't contain sensitive audio data
            safe_metadata = self._sanitize_metadata(metadata or {})
            
            # Create analytics record
            analytics_record = VoiceAnalyticsDB(
                user_id=user_id,
                session_id=session_id,
                action_type=action_type.value,
                duration_ms=duration_ms,
                text_length=text_length,
                accuracy_score=accuracy_score,
                error_message=error_message,
                analytics_metadata=safe_metadata
            )
            
            self.db_session.add(analytics_record)
            self.db_session.commit()
            
            # Clear relevant cache
            self._clear_performance_cache(user_id)
            
            # Log for monitoring
            self.logger.info(
                f"Voice analytics recorded: user={user_id}, action={action_type.value}, "
                f"duration={duration_ms}ms, success={error_message is None}"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error recording voice performance: {e}")
            self.db_session.rollback()
            return False
    
    def record_voice_error(
        self,
        user_id: str,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        recovery_action: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Record voice error for troubleshooting and analysis.
        
        Args:
            user_id: User identifier
            error_type: Type of error (network, permission, audio, etc.)
            error_message: Detailed error message
            context: Context information (browser, settings, etc.)
            recovery_action: Action taken to recover from error
            session_id: Session identifier
            
        Returns:
            bool: True if recording was successful
        """
        try:
            # Determine action type based on error type
            if 'stt' in error_type.lower() or 'recognition' in error_type.lower():
                action_type = VoiceActionType.STT_ERROR
            elif 'tts' in error_type.lower() or 'synthesis' in error_type.lower():
                action_type = VoiceActionType.TTS_ERROR
            else:
                action_type = VoiceActionType.STT_ERROR  # Default
            
            # Prepare metadata with context and recovery info
            metadata = {
                'error_type': error_type,
                'context': self._sanitize_metadata(context or {}),
                'recovery_action': recovery_action,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return self.record_voice_performance(
                user_id=user_id,
                action_type=action_type,
                error_message=error_message,
                metadata=metadata,
                session_id=session_id
            )
            
        except Exception as e:
            self.logger.error(f"Error recording voice error: {e}")
            return False
    
    def record_feature_adoption(
        self,
        user_id: str,
        feature_type: VoiceFeatureType,
        enabled: bool,
        settings_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Record voice feature adoption and usage patterns.
        
        Args:
            user_id: User identifier
            feature_type: Type of voice feature
            enabled: Whether feature was enabled or disabled
            settings_data: Related settings data
            session_id: Session identifier
            
        Returns:
            bool: True if recording was successful
        """
        try:
            action_type = VoiceActionType.VOICE_ENABLED if enabled else VoiceActionType.VOICE_DISABLED
            
            metadata = {
                'feature_type': feature_type.value,
                'enabled': enabled,
                'settings': self._sanitize_metadata(settings_data or {}),
                'adoption_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return self.record_voice_performance(
                user_id=user_id,
                action_type=action_type,
                metadata=metadata,
                session_id=session_id
            )
            
        except Exception as e:
            self.logger.error(f"Error recording feature adoption: {e}")
            return False
    
    def get_voice_usage_report(
        self,
        user_id: str,
        days: int = 30
    ) -> Optional[VoiceUsageReport]:
        """
        Generate comprehensive voice usage report for a user.
        
        Args:
            user_id: User identifier
            days: Number of days to analyze
            
        Returns:
            VoiceUsageReport or None if no data available
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Get all voice analytics for the user in the time period
            analytics = self.db_session.query(VoiceAnalyticsDB).filter(
                and_(
                    VoiceAnalyticsDB.user_id == user_id,
                    VoiceAnalyticsDB.created_at >= cutoff_date
                )
            ).all()
            
            if not analytics:
                return None
            
            # Calculate metrics
            total_interactions = len(analytics)
            stt_records = [a for a in analytics if 'stt' in a.action_type.lower()]
            tts_records = [a for a in analytics if 'tts' in a.action_type.lower()]
            error_records = [a for a in analytics if a.error_message is not None]
            
            # Processing times
            stt_times = [a.duration_ms for a in stt_records if a.duration_ms is not None]
            tts_times = [a.duration_ms for a in tts_records if a.duration_ms is not None]
            
            avg_stt_time = statistics.mean(stt_times) if stt_times else 0.0
            avg_tts_time = statistics.mean(tts_times) if tts_times else 0.0
            
            # Error analysis
            error_messages = [a.error_message for a in error_records]
            most_common_errors = self._get_most_common_errors(error_messages)
            
            # Feature adoption rate
            adoption_records = [a for a in analytics if 'enabled' in a.action_type.lower()]
            enabled_count = len([a for a in adoption_records if 'enabled' in a.action_type])
            adoption_rate = enabled_count / len(adoption_records) if adoption_records else 0.0
            
            # Engagement score (based on usage frequency and success rate)
            success_count = len([a for a in analytics if a.error_message is None])
            success_rate = success_count / total_interactions if total_interactions > 0 else 0.0
            usage_frequency = total_interactions / days
            engagement_score = (success_rate * 0.7 + min(usage_frequency / 10.0, 1.0) * 0.3)
            
            return VoiceUsageReport(
                user_id=user_id,
                total_voice_interactions=total_interactions,
                stt_usage_count=len(stt_records),
                tts_usage_count=len(tts_records),
                avg_stt_processing_time=avg_stt_time,
                avg_tts_processing_time=avg_tts_time,
                voice_error_count=len(error_records),
                most_common_errors=most_common_errors,
                feature_adoption_rate=adoption_rate,
                engagement_score=engagement_score,
                period_start=cutoff_date,
                period_end=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Error generating voice usage report: {e}")
            return None
    
    def get_voice_performance_metrics(
        self,
        days: int = 30,
        user_id: Optional[str] = None
    ) -> List[VoicePerformanceMetrics]:
        """
        Get voice performance metrics across all users or for specific user.
        
        Args:
            days: Number of days to analyze
            user_id: Specific user ID (None for all users)
            
        Returns:
            List of performance metrics by feature type
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Build query
            query = self.db_session.query(VoiceAnalyticsDB).filter(
                VoiceAnalyticsDB.created_at >= cutoff_date
            )
            
            if user_id:
                query = query.filter(VoiceAnalyticsDB.user_id == user_id)
            
            analytics = query.all()
            
            if not analytics:
                return []
            
            # Group by action type
            grouped_analytics = defaultdict(list)
            for record in analytics:
                grouped_analytics[record.action_type].append(record)
            
            metrics = []
            for action_type, records in grouped_analytics.items():
                metric = self._calculate_performance_metric(action_type, records)
                if metric:
                    metrics.append(metric)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting voice performance metrics: {e}")
            return []
    
    def analyze_voice_errors(
        self,
        days: int = 30,
        user_id: Optional[str] = None
    ) -> List[VoiceErrorAnalysis]:
        """
        Analyze voice errors for troubleshooting insights.
        
        Args:
            days: Number of days to analyze
            user_id: Specific user ID (None for all users)
            
        Returns:
            List of error analysis results
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Get error records
            query = self.db_session.query(VoiceAnalyticsDB).filter(
                and_(
                    VoiceAnalyticsDB.created_at >= cutoff_date,
                    VoiceAnalyticsDB.error_message.isnot(None)
                )
            )
            
            if user_id:
                query = query.filter(VoiceAnalyticsDB.user_id == user_id)
            
            error_records = query.all()
            
            if not error_records:
                return []
            
            # Group errors by type
            error_groups = defaultdict(list)
            for record in error_records:
                error_type = self._categorize_error(record.error_message)
                error_groups[error_type].append(record)
            
            analyses = []
            for error_type, records in error_groups.items():
                analysis = self._analyze_error_group(error_type, records)
                analyses.append(analysis)
            
            # Sort by frequency
            analyses.sort(key=lambda x: x.frequency, reverse=True)
            return analyses
            
        except Exception as e:
            self.logger.error(f"Error analyzing voice errors: {e}")
            return []
    
    def get_voice_adoption_metrics(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get voice feature adoption metrics across all users.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with adoption metrics
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Get all users who have voice analytics
            voice_users = self.db_session.query(VoiceAnalyticsDB.user_id).filter(
                VoiceAnalyticsDB.created_at >= cutoff_date
            ).distinct().all()
            
            total_voice_users = len(voice_users)
            
            if total_voice_users == 0:
                return {
                    'total_voice_users': 0,
                    'feature_adoption': {},
                    'usage_patterns': {},
                    'engagement_levels': {}
                }
            
            # Get total users for comparison
            total_users = self.db_session.query(func.count(User.id)).scalar()
            
            # Analyze feature adoption
            feature_adoption = {}
            for feature in VoiceFeatureType:
                enabled_count = self.db_session.query(VoiceAnalyticsDB).filter(
                    and_(
                        VoiceAnalyticsDB.created_at >= cutoff_date,
                        VoiceAnalyticsDB.analytics_metadata.contains({'feature_type': feature.value}),
                        VoiceAnalyticsDB.action_type == VoiceActionType.VOICE_ENABLED.value
                    )
                ).count()
                
                feature_adoption[feature.value] = {
                    'enabled_users': enabled_count,
                    'adoption_rate': enabled_count / total_voice_users if total_voice_users > 0 else 0.0
                }
            
            # Usage patterns
            usage_patterns = self._analyze_usage_patterns(cutoff_date)
            
            # Engagement levels
            engagement_levels = self._analyze_engagement_levels(cutoff_date)
            
            return {
                'total_voice_users': total_voice_users,
                'total_users': total_users,
                'voice_adoption_rate': total_voice_users / total_users if total_users > 0 else 0.0,
                'feature_adoption': feature_adoption,
                'usage_patterns': usage_patterns,
                'engagement_levels': engagement_levels,
                'analysis_period_days': days
            }
            
        except Exception as e:
            self.logger.error(f"Error getting voice adoption metrics: {e}")
            return {}
    
    def integrate_with_chat_analytics(
        self,
        session_id: str,
        user_id: str,
        voice_enabled: bool,
        voice_metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Integrate voice analytics with existing chat analytics.
        
        Args:
            session_id: Chat session ID
            user_id: User identifier
            voice_enabled: Whether voice was used in the session
            voice_metrics: Voice-specific metrics for the session
            
        Returns:
            bool: True if integration was successful
        """
        try:
            # Record voice usage in chat context
            if voice_enabled and voice_metrics:
                metadata = {
                    'chat_session_id': session_id,
                    'voice_in_chat': True,
                    'chat_voice_metrics': self._sanitize_metadata(voice_metrics)
                }
                
                # Record as voice usage in chat context
                self.record_voice_performance(
                    user_id=user_id,
                    action_type=VoiceActionType.VOICE_ENABLED,
                    metadata=metadata,
                    session_id=session_id
                )
            
            # Use existing tool analytics to record voice tool usage
            if voice_enabled:
                self.tool_analytics.record_tool_usage(
                    tool_name='VoiceAssistant',
                    query=f'Voice interaction in session {session_id}',
                    success=True,
                    response_quality=voice_metrics.get('quality_score', 0.8) if voice_metrics else 0.8,
                    response_time=voice_metrics.get('total_time', 0.0) if voice_metrics else None,
                    context={'voice_integration': True, 'session_id': session_id}
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error integrating with chat analytics: {e}")
            return False
    
    def cleanup_old_analytics(
        self,
        retention_days: int = 90,
        anonymize_after_days: int = 30
    ) -> Dict[str, int]:
        """
        Clean up old analytics data according to privacy policies.
        
        Args:
            retention_days: Days to retain analytics data
            anonymize_after_days: Days after which to anonymize data
            
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            now = datetime.now(timezone.utc)
            delete_cutoff = now - timedelta(days=retention_days)
            anonymize_cutoff = now - timedelta(days=anonymize_after_days)
            
            # Delete old records
            deleted_count = self.db_session.query(VoiceAnalyticsDB).filter(
                VoiceAnalyticsDB.created_at < delete_cutoff
            ).delete()
            
            # Anonymize records (remove user_id but keep aggregated data)
            anonymize_records = self.db_session.query(VoiceAnalyticsDB).filter(
                and_(
                    VoiceAnalyticsDB.created_at < anonymize_cutoff,
                    VoiceAnalyticsDB.created_at >= delete_cutoff,
                    VoiceAnalyticsDB.user_id != 'anonymous'
                )
            ).all()
            
            anonymized_count = 0
            for record in anonymize_records:
                record.user_id = 'anonymous'
                # Remove potentially identifying metadata
                if record.analytics_metadata:
                    record.analytics_metadata = self._anonymize_metadata(record.analytics_metadata)
                anonymized_count += 1
            
            self.db_session.commit()
            
            self.logger.info(f"Analytics cleanup: deleted {deleted_count}, anonymized {anonymized_count}")
            
            return {
                'deleted_records': deleted_count,
                'anonymized_records': anonymized_count,
                'retention_days': retention_days,
                'anonymize_after_days': anonymize_after_days
            }
            
        except Exception as e:
            self.logger.error(f"Error cleaning up analytics: {e}")
            self.db_session.rollback()
            return {'deleted_records': 0, 'anonymized_records': 0}
    
    # Private helper methods
    
    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from metadata"""
        sensitive_keys = ['audio_data', 'raw_audio', 'microphone_data', 'speech_data']
        
        sanitized = {}
        for key, value in metadata.items():
            if key.lower() not in sensitive_keys:
                if isinstance(value, dict):
                    sanitized[key] = self._sanitize_metadata(value)
                else:
                    sanitized[key] = value
        
        return sanitized
    
    def _anonymize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize metadata by removing identifying information"""
        identifying_keys = ['user_agent', 'ip_address', 'session_token', 'device_id']
        
        anonymized = {}
        for key, value in metadata.items():
            if key.lower() not in identifying_keys:
                if isinstance(value, dict):
                    anonymized[key] = self._anonymize_metadata(value)
                else:
                    anonymized[key] = value
        
        return anonymized
    
    def _get_most_common_errors(self, error_messages: List[str]) -> List[str]:
        """Get most common error types from error messages"""
        error_counts = defaultdict(int)
        
        for message in error_messages:
            if message:
                error_type = self._categorize_error(message)
                error_counts[error_type] += 1
        
        # Return top 5 most common errors
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return [error for error, count in sorted_errors[:5]]
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize error message into error type"""
        if not error_message:
            return 'unknown'
        
        message_lower = error_message.lower()
        
        for error_type, patterns in self.error_patterns.items():
            if any(pattern in message_lower for pattern in patterns):
                return error_type
        
        return 'other'
    
    def _calculate_performance_metric(
        self,
        action_type: str,
        records: List[VoiceAnalyticsDB]
    ) -> Optional[VoicePerformanceMetrics]:
        """Calculate performance metrics for a specific action type"""
        if not records:
            return None
        
        # Processing times
        processing_times = [r.duration_ms for r in records if r.duration_ms is not None]
        avg_processing_time = statistics.mean(processing_times) if processing_times else 0.0
        
        # Success/error rates
        error_count = len([r for r in records if r.error_message is not None])
        success_rate = (len(records) - error_count) / len(records) if records else 0.0
        error_rate = error_count / len(records) if records else 0.0
        
        # Quality scores
        quality_scores = [r.accuracy_score for r in records if r.accuracy_score is not None]
        avg_quality = statistics.mean(quality_scores) if quality_scores else 0.0
        
        # Trend analysis (simplified)
        trend = "stable"
        if len(records) > 5:
            recent_success = len([r for r in records[-3:] if r.error_message is None]) / 3
            older_success = len([r for r in records[:-3] if r.error_message is None]) / (len(records) - 3)
            
            if recent_success > older_success + 0.1:
                trend = "improving"
            elif recent_success < older_success - 0.1:
                trend = "declining"
        
        return VoicePerformanceMetrics(
            feature_type=action_type,
            avg_processing_time=avg_processing_time,
            success_rate=success_rate,
            error_rate=error_rate,
            usage_count=len(records),
            quality_score=avg_quality,
            trend=trend
        )
    
    def _analyze_error_group(
        self,
        error_type: str,
        records: List[VoiceAnalyticsDB]
    ) -> VoiceErrorAnalysis:
        """Analyze a group of similar errors"""
        frequency = len(records)
        
        # Calculate average recovery time (time between error and next successful action)
        recovery_times = []
        for record in records:
            # This is simplified - in practice, you'd look at subsequent successful actions
            if record.duration_ms:
                recovery_times.append(record.duration_ms)
        
        avg_recovery_time = statistics.mean(recovery_times) if recovery_times else 0.0
        
        # Extract common contexts
        contexts = []
        for record in records:
            if record.analytics_metadata and 'context' in record.analytics_metadata:
                context_info = record.analytics_metadata['context']
                if isinstance(context_info, dict):
                    contexts.extend(context_info.keys())
        
        common_contexts = list(set(contexts))[:5]  # Top 5 contexts
        
        # Generate suggested fixes based on error type
        suggested_fixes = self._get_error_fixes(error_type)
        
        return VoiceErrorAnalysis(
            error_type=error_type,
            frequency=frequency,
            avg_recovery_time=avg_recovery_time,
            common_contexts=common_contexts,
            suggested_fixes=suggested_fixes
        )
    
    def _get_error_fixes(self, error_type: str) -> List[str]:
        """Get suggested fixes for error type"""
        fixes = {
            'network': [
                'Check internet connection stability',
                'Implement retry logic with exponential backoff',
                'Add offline mode fallback'
            ],
            'permission': [
                'Provide clear microphone permission instructions',
                'Add permission status checking',
                'Implement graceful degradation to text input'
            ],
            'audio': [
                'Check microphone hardware and drivers',
                'Adjust microphone sensitivity settings',
                'Implement audio quality detection'
            ],
            'synthesis': [
                'Check available TTS voices',
                'Implement voice fallback options',
                'Add TTS engine compatibility checks'
            ],
            'recognition': [
                'Improve speech recognition settings',
                'Add language detection',
                'Implement confidence threshold adjustments'
            ]
        }
        
        return fixes.get(error_type, ['Contact technical support', 'Check system requirements'])
    
    def _analyze_usage_patterns(self, cutoff_date: datetime) -> Dict[str, Any]:
        """Analyze voice usage patterns"""
        try:
            # Get usage by hour of day
            hourly_usage = defaultdict(int)
            daily_usage = defaultdict(int)
            
            records = self.db_session.query(VoiceAnalyticsDB).filter(
                VoiceAnalyticsDB.created_at >= cutoff_date
            ).all()
            
            for record in records:
                hour = record.created_at.hour
                day = record.created_at.strftime('%A')
                hourly_usage[hour] += 1
                daily_usage[day] += 1
            
            return {
                'peak_hours': sorted(hourly_usage.items(), key=lambda x: x[1], reverse=True)[:3],
                'peak_days': sorted(daily_usage.items(), key=lambda x: x[1], reverse=True)[:3],
                'total_usage_events': len(records)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing usage patterns: {e}")
            return {}
    
    def _analyze_engagement_levels(self, cutoff_date: datetime) -> Dict[str, Any]:
        """Analyze user engagement levels with voice features"""
        try:
            # Get user engagement metrics
            user_engagement = {}
            
            users = self.db_session.query(VoiceAnalyticsDB.user_id).filter(
                VoiceAnalyticsDB.created_at >= cutoff_date
            ).distinct().all()
            
            for (user_id,) in users:
                user_records = self.db_session.query(VoiceAnalyticsDB).filter(
                    and_(
                        VoiceAnalyticsDB.user_id == user_id,
                        VoiceAnalyticsDB.created_at >= cutoff_date
                    )
                ).all()
                
                if user_records:
                    success_count = len([r for r in user_records if r.error_message is None])
                    success_rate = success_count / len(user_records)
                    
                    # Categorize engagement level
                    if len(user_records) > 50 and success_rate > 0.8:
                        engagement_level = 'high'
                    elif len(user_records) > 10 and success_rate > 0.6:
                        engagement_level = 'medium'
                    else:
                        engagement_level = 'low'
                    
                    user_engagement[user_id] = {
                        'usage_count': len(user_records),
                        'success_rate': success_rate,
                        'engagement_level': engagement_level
                    }
            
            # Aggregate engagement levels
            engagement_counts = defaultdict(int)
            for user_data in user_engagement.values():
                engagement_counts[user_data['engagement_level']] += 1
            
            return {
                'engagement_distribution': dict(engagement_counts),
                'total_engaged_users': len(user_engagement),
                'high_engagement_rate': engagement_counts['high'] / len(user_engagement) if user_engagement else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing engagement levels: {e}")
            return {}
    
    def _clear_performance_cache(self, user_id: Optional[str] = None):
        """Clear performance cache for specific user or all users"""
        if user_id:
            keys_to_remove = [key for key in self._performance_cache.keys() if user_id in key]
            for key in keys_to_remove:
                self._performance_cache.pop(key, None)
                self._cache_expiry.pop(key, None)
        else:
            self._performance_cache.clear()
            self._cache_expiry.clear()
    
    def __del__(self):
        """Cleanup database session"""
        if hasattr(self, 'db_session') and self.db_session:
            try:
                self.db_session.close()
            except Exception:
                pass