"""
Voice assistant API endpoints for the AI agent customer support system.
Provides CRUD operations for voice settings, capabilities detection, and analytics logging.
"""

from fastapi import APIRouter, HTTPException, Cookie, Depends
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone

from backend.database import get_db
from backend.models import User, UserSession, VoiceSettings as VoiceSettingsDB, VoiceAnalytics as VoiceAnalyticsDB
from backend.voice_models import (
    VoiceSettings, VoiceSettingsUpdate, VoiceAnalytics, VoiceCapabilities,
    VoiceSettingsResponse, VoiceAnalyticsResponse, VoiceErrorResponse,
    VoiceSettingsRequest, VoiceAnalyticsRequest, VoiceActionType
)

logger = logging.getLogger(__name__)

# Create router for voice endpoints
voice_router = APIRouter(prefix="/voice", tags=["voice"])


def get_current_user(session_token: str = Cookie(None), db: Session = Depends(get_db)) -> str:
    """Get current user ID from session token"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Unauthorized: No session token")

    user_session = db.query(UserSession).filter(
        UserSession.session_id == session_token,
        UserSession.is_active == True
    ).first()
    
    if not user_session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    # Update last accessed time
    user_session.last_accessed = datetime.now(timezone.utc)
    db.commit()
    
    return user_session.user_id


@voice_router.get("/capabilities", response_model=VoiceCapabilities)
async def get_voice_capabilities():
    """
    Get voice capabilities information for the client.
    This endpoint provides information about available voice features with enhanced error handling.
    """
    try:
        # Return static capabilities - actual detection happens client-side
        capabilities = VoiceCapabilities(
            speech_recognition_available=True,  # Assume available, client will verify
            speech_synthesis_available=True,    # Assume available, client will verify
            available_voices=[
                "default",
                "en-US-Standard-A",
                "en-US-Standard-B", 
                "en-US-Standard-C",
                "en-US-Standard-D",
                "en-GB-Standard-A",
                "en-GB-Standard-B"
            ],
            supported_languages=[
                "en-US",
                "en-GB", 
                "es-ES",
                "fr-FR",
                "de-DE",
                "it-IT",
                "pt-BR",
                "ja-JP",
                "ko-KR",
                "zh-CN"
            ],
            browser_support={
                "webkitSpeechRecognition": True,
                "SpeechRecognition": True,
                "speechSynthesis": True,
                "mediaDevices": True,
                "audioContext": True
            }
        )
        
        logger.info("Voice capabilities requested")
        return capabilities
        
    except Exception as e:
        logger.error(f"Error getting voice capabilities: {e}")
        # Log error for monitoring (requirement 6.3)
        try:
            # Create error analytics record if possible
            error_analytics = VoiceAnalyticsDB(
                user_id="system",
                session_id=None,
                action_type="capabilities_error",
                duration_ms=None,
                text_length=None,
                accuracy_score=None,
                error_message=str(e),
                analytics_metadata={"endpoint": "/voice/capabilities", "error_type": "server_error"}
            )
            # Note: We can't commit to DB here without session, but we log it
            logger.error(f"Voice capabilities error logged: {error_analytics}")
        except Exception as log_error:
            logger.error(f"Failed to log voice capabilities error: {log_error}")
            
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Failed to get voice capabilities",
                "fallback_message": "Voice features may not be available. Please use text input.",
                "retry_after": 30  # Suggest retry after 30 seconds
            }
        )


@voice_router.get("/settings", response_model=VoiceSettingsResponse)
async def get_voice_settings(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get voice settings for the current user with enhanced error handling.
    Returns default settings if none exist.
    """
    try:
        # Get existing voice settings
        voice_settings_db = db.query(VoiceSettingsDB).filter(
            VoiceSettingsDB.user_id == user_id
        ).first()
        
        if voice_settings_db:
            # Convert database model to Pydantic model
            settings = VoiceSettings(
                auto_play_enabled=voice_settings_db.auto_play_enabled,
                voice_name=voice_settings_db.voice_name,
                speech_rate=voice_settings_db.speech_rate,
                speech_pitch=voice_settings_db.speech_pitch,
                speech_volume=voice_settings_db.speech_volume,
                language=voice_settings_db.language,
                microphone_sensitivity=voice_settings_db.microphone_sensitivity,
                noise_cancellation=voice_settings_db.noise_cancellation
            )
        else:
            # Return default settings
            settings = VoiceSettings()
        
        logger.info(f"Voice settings retrieved for user {user_id}")
        return VoiceSettingsResponse(
            success=True,
            settings=settings,
            message="Voice settings retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice settings for user {user_id}: {e}")
        
        # Log error for monitoring (requirement 6.3)
        try:
            error_analytics = VoiceAnalyticsDB(
                user_id=user_id,
                session_id=None,
                action_type="settings_error",
                duration_ms=None,
                text_length=None,
                accuracy_score=None,
                error_message=str(e),
                analytics_metadata={"endpoint": "/voice/settings", "operation": "get", "error_type": "database_error"}
            )
            db.add(error_analytics)
            db.commit()
        except Exception as log_error:
            logger.error(f"Failed to log voice settings error: {log_error}")
            db.rollback()
        
        # Return graceful fallback with default settings
        try:
            default_settings = VoiceSettings()
            return VoiceSettingsResponse(
                success=False,
                settings=default_settings,
                message="Failed to retrieve settings, using defaults. Voice features may be limited."
            )
        except Exception:
            raise HTTPException(
                status_code=500, 
                detail={
                    "error": "Failed to get voice settings",
                    "fallback_message": "Voice settings unavailable. Please try again later or use text input.",
                    "use_defaults": True
                }
            )


@voice_router.post("/settings", response_model=VoiceSettingsResponse)
async def update_voice_settings(
    request: VoiceSettingsRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update voice settings for the current user.
    Creates new settings if none exist, otherwise updates existing settings.
    """
    try:
        settings_update = request.settings
        
        # Get existing voice settings
        voice_settings_db = db.query(VoiceSettingsDB).filter(
            VoiceSettingsDB.user_id == user_id
        ).first()
        
        if voice_settings_db:
            # Update existing settings
            if settings_update.auto_play_enabled is not None:
                voice_settings_db.auto_play_enabled = settings_update.auto_play_enabled
            if settings_update.voice_name is not None:
                voice_settings_db.voice_name = settings_update.voice_name
            if settings_update.speech_rate is not None:
                voice_settings_db.speech_rate = settings_update.speech_rate
            if settings_update.speech_pitch is not None:
                voice_settings_db.speech_pitch = settings_update.speech_pitch
            if settings_update.speech_volume is not None:
                voice_settings_db.speech_volume = settings_update.speech_volume
            if settings_update.language is not None:
                voice_settings_db.language = settings_update.language
            if settings_update.microphone_sensitivity is not None:
                voice_settings_db.microphone_sensitivity = settings_update.microphone_sensitivity
            if settings_update.noise_cancellation is not None:
                voice_settings_db.noise_cancellation = settings_update.noise_cancellation
            
            voice_settings_db.updated_at = datetime.now(timezone.utc)
            
        else:
            # Create new settings with defaults, then apply updates
            default_settings = VoiceSettings()
            
            voice_settings_db = VoiceSettingsDB(
                user_id=user_id,
                auto_play_enabled=settings_update.auto_play_enabled if settings_update.auto_play_enabled is not None else default_settings.auto_play_enabled,
                voice_name=settings_update.voice_name if settings_update.voice_name is not None else default_settings.voice_name,
                speech_rate=settings_update.speech_rate if settings_update.speech_rate is not None else default_settings.speech_rate,
                speech_pitch=settings_update.speech_pitch if settings_update.speech_pitch is not None else default_settings.speech_pitch,
                speech_volume=settings_update.speech_volume if settings_update.speech_volume is not None else default_settings.speech_volume,
                language=settings_update.language if settings_update.language is not None else default_settings.language,
                microphone_sensitivity=settings_update.microphone_sensitivity if settings_update.microphone_sensitivity is not None else default_settings.microphone_sensitivity,
                noise_cancellation=settings_update.noise_cancellation if settings_update.noise_cancellation is not None else default_settings.noise_cancellation
            )
            
            db.add(voice_settings_db)
        
        db.commit()
        db.refresh(voice_settings_db)
        
        # Convert back to Pydantic model for response
        updated_settings = VoiceSettings(
            auto_play_enabled=voice_settings_db.auto_play_enabled,
            voice_name=voice_settings_db.voice_name,
            speech_rate=voice_settings_db.speech_rate,
            speech_pitch=voice_settings_db.speech_pitch,
            speech_volume=voice_settings_db.speech_volume,
            language=voice_settings_db.language,
            microphone_sensitivity=voice_settings_db.microphone_sensitivity,
            noise_cancellation=voice_settings_db.noise_cancellation
        )
        
        logger.info(f"Voice settings updated for user {user_id}")
        return VoiceSettingsResponse(
            success=True,
            settings=updated_settings,
            message="Voice settings updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating voice settings for user {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update voice settings")


@voice_router.post("/analytics", response_model=VoiceAnalyticsResponse)
async def log_voice_analytics(
    request: VoiceAnalyticsRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Log voice analytics data for usage tracking and performance monitoring.
    """
    try:
        analytics = request.analytics
        
        # Create analytics record
        analytics_db = VoiceAnalyticsDB(
            user_id=user_id,
            session_id=None,  # Could be extracted from session token if needed
            action_type=analytics.action_type,  # Already a string value from Pydantic
            duration_ms=analytics.duration_ms,
            text_length=analytics.text_length,
            accuracy_score=analytics.accuracy_score,
            error_message=analytics.error_message,
            analytics_metadata=analytics.metadata
        )
        
        db.add(analytics_db)
        db.commit()
        db.refresh(analytics_db)
        
        logger.info(f"Voice analytics logged for user {user_id}: {analytics.action_type}")
        return VoiceAnalyticsResponse(
            success=True,
            message="Voice analytics logged successfully",
            analytics_id=analytics_db.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging voice analytics for user {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to log voice analytics")


# Additional utility endpoints for voice features

@voice_router.get("/analytics/summary")
async def get_voice_analytics_summary(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get voice analytics summary for the current user.
    """
    try:
        # Get analytics summary
        analytics_records = db.query(VoiceAnalyticsDB).filter(
            VoiceAnalyticsDB.user_id == user_id
        ).all()
        
        if not analytics_records:
            return {
                "success": True,
                "summary": {
                    "total_actions": 0,
                    "action_breakdown": {},
                    "average_duration": 0,
                    "error_rate": 0
                }
            }
        
        # Calculate summary statistics
        total_actions = len(analytics_records)
        action_breakdown = {}
        total_duration = 0
        duration_count = 0
        error_count = 0
        
        for record in analytics_records:
            # Count actions by type
            action_type = record.action_type
            action_breakdown[action_type] = action_breakdown.get(action_type, 0) + 1
            
            # Calculate average duration
            if record.duration_ms:
                total_duration += record.duration_ms
                duration_count += 1
            
            # Count errors
            if record.error_message:
                error_count += 1
        
        average_duration = total_duration / duration_count if duration_count > 0 else 0
        error_rate = error_count / total_actions if total_actions > 0 else 0
        
        summary = {
            "total_actions": total_actions,
            "action_breakdown": action_breakdown,
            "average_duration_ms": round(average_duration, 2),
            "error_rate": round(error_rate, 3)
        }
        
        logger.info(f"Voice analytics summary retrieved for user {user_id}")
        return {
            "success": True,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice analytics summary for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get voice analytics summary")


@voice_router.delete("/settings")
async def reset_voice_settings(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reset voice settings to defaults for the current user.
    """
    try:
        # Delete existing settings (will fall back to defaults)
        voice_settings_db = db.query(VoiceSettingsDB).filter(
            VoiceSettingsDB.user_id == user_id
        ).first()
        
        if voice_settings_db:
            db.delete(voice_settings_db)
            db.commit()
            logger.info(f"Voice settings reset for user {user_id}")
            message = "Voice settings reset to defaults"
        else:
            logger.info(f"No voice settings found to reset for user {user_id}")
            message = "No voice settings found to reset"
        
        return VoiceSettingsResponse(
            success=True,
            settings=VoiceSettings(),  # Return default settings
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting voice settings for user {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to reset voice settings")


# Voice Analytics Endpoints

@voice_router.post("/analytics/batch")
async def log_voice_analytics_batch(
    request: Dict[str, Any],
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Log batch voice analytics data for performance monitoring and usage tracking.
    """
    try:
        from backend.voice_analytics import VoiceAnalyticsManager
        
        analytics_manager = VoiceAnalyticsManager(db)
        
        session_summary = request.get('sessionSummary', {})
        analytics_data = request.get('analyticsData', [])
        
        processed_count = 0
        error_count = 0
        
        # Process each analytics record
        for data in analytics_data:
            try:
                data_type = data.get('type')
                
                if data_type == 'performance':
                    # Map operation type to VoiceActionType
                    operation_type = data.get('operationType', '')
                    if 'stt' in operation_type.lower():
                        if 'start' in operation_type.lower():
                            action_type = VoiceActionType.STT_START
                        else:
                            action_type = VoiceActionType.STT_COMPLETE
                    elif 'tts' in operation_type.lower():
                        if 'start' in operation_type.lower():
                            action_type = VoiceActionType.TTS_START
                        else:
                            action_type = VoiceActionType.TTS_COMPLETE
                    else:
                        continue  # Skip unknown operation types
                    
                    success = analytics_manager.record_voice_performance(
                        user_id=user_id,
                        action_type=action_type,
                        duration_ms=data.get('duration'),
                        text_length=data.get('textLength'),
                        accuracy_score=data.get('accuracyScore'),
                        error_message=None if data.get('success', True) else 'Performance tracking error',
                        metadata=data.get('context', {}),
                        session_id=data.get('sessionId')
                    )
                    
                    if success:
                        processed_count += 1
                    else:
                        error_count += 1
                
                elif data_type == 'error':
                    success = analytics_manager.record_voice_error(
                        user_id=user_id,
                        error_type=data.get('errorType', 'unknown'),
                        error_message=data.get('errorMessage', ''),
                        context=data.get('context', {}),
                        recovery_action=data.get('recoveryAction'),
                        session_id=data.get('sessionId')
                    )
                    
                    if success:
                        processed_count += 1
                    else:
                        error_count += 1
                
                elif data_type == 'feature_adoption':
                    from backend.voice_analytics import VoiceFeatureType
                    
                    feature_type_map = {
                        'voiceInput': VoiceFeatureType.VOICE_INPUT,
                        'voiceOutput': VoiceFeatureType.VOICE_OUTPUT,
                        'autoPlay': VoiceFeatureType.AUTO_PLAY,
                        'settingsChanged': VoiceFeatureType.SETTINGS_CHANGE
                    }
                    
                    feature_type = feature_type_map.get(
                        data.get('featureType'), 
                        VoiceFeatureType.SETTINGS_CHANGE
                    )
                    
                    success = analytics_manager.record_feature_adoption(
                        user_id=user_id,
                        feature_type=feature_type,
                        enabled=data.get('enabled', True),
                        settings_data=data.get('settings', {}),
                        session_id=data.get('sessionId')
                    )
                    
                    if success:
                        processed_count += 1
                    else:
                        error_count += 1
                
                elif data_type == 'voice_in_chat':
                    success = analytics_manager.integrate_with_chat_analytics(
                        session_id=data.get('chatSessionId', ''),
                        user_id=user_id,
                        voice_enabled=True,
                        voice_metrics=data.get('voiceMetrics', {})
                    )
                    
                    if success:
                        processed_count += 1
                    else:
                        error_count += 1
                        
            except Exception as record_error:
                logger.error(f"Error processing analytics record: {record_error}")
                error_count += 1
        
        logger.info(f"Voice analytics batch processed: {processed_count} success, {error_count} errors")
        
        return {
            "success": True,
            "message": f"Processed {processed_count} analytics records",
            "processed_count": processed_count,
            "error_count": error_count,
            "session_summary": session_summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing voice analytics batch: {e}")
        raise HTTPException(status_code=500, detail="Failed to process voice analytics batch")


@voice_router.get("/analytics/report")
async def get_voice_analytics_report(
    days: int = 30,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get voice analytics report for the current user.
    """
    try:
        from backend.voice_analytics import VoiceAnalyticsManager
        
        analytics_manager = VoiceAnalyticsManager(db)
        report = analytics_manager.get_voice_usage_report(user_id, days)
        
        if not report:
            return {
                "success": True,
                "message": "No voice analytics data available",
                "report": None
            }
        
        # Convert dataclass to dict for JSON serialization
        from dataclasses import asdict
        report_dict = asdict(report)
        
        # Convert datetime objects to ISO strings
        report_dict['period_start'] = report.period_start.isoformat()
        report_dict['period_end'] = report.period_end.isoformat()
        
        return {
            "success": True,
            "message": "Voice analytics report generated",
            "report": report_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating voice analytics report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate voice analytics report")


@voice_router.get("/analytics/performance")
async def get_voice_performance_metrics(
    days: int = 30,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get voice performance metrics for the current user.
    """
    try:
        from backend.voice_analytics import VoiceAnalyticsManager
        
        analytics_manager = VoiceAnalyticsManager(db)
        metrics = analytics_manager.get_voice_performance_metrics(days, user_id)
        
        # Convert dataclasses to dicts for JSON serialization
        from dataclasses import asdict
        metrics_dict = [asdict(metric) for metric in metrics]
        
        return {
            "success": True,
            "message": f"Voice performance metrics for {days} days",
            "metrics": metrics_dict,
            "period_days": days
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get voice performance metrics")


@voice_router.get("/analytics/errors")
async def get_voice_error_analysis(
    days: int = 30,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get voice error analysis for troubleshooting.
    """
    try:
        from backend.voice_analytics import VoiceAnalyticsManager
        
        analytics_manager = VoiceAnalyticsManager(db)
        error_analysis = analytics_manager.analyze_voice_errors(days, user_id)
        
        # Convert dataclasses to dicts for JSON serialization
        from dataclasses import asdict
        analysis_dict = [asdict(analysis) for analysis in error_analysis]
        
        return {
            "success": True,
            "message": f"Voice error analysis for {days} days",
            "error_analysis": analysis_dict,
            "period_days": days
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice error analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to get voice error analysis")


# Admin endpoints for system-wide analytics (require admin privileges)

@voice_router.get("/analytics/adoption")
async def get_voice_adoption_metrics(
    days: int = 30,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get voice feature adoption metrics (admin only).
    """
    try:
        # Check if user is admin (simplified check - in production, use proper role checking)
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user or not getattr(user, 'is_admin', False):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        from backend.voice_analytics import VoiceAnalyticsManager
        
        analytics_manager = VoiceAnalyticsManager(db)
        adoption_metrics = analytics_manager.get_voice_adoption_metrics(days)
        
        return {
            "success": True,
            "message": f"Voice adoption metrics for {days} days",
            "adoption_metrics": adoption_metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice adoption metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get voice adoption metrics")


@voice_router.get("/config")
async def get_voice_production_config(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get production-optimized voice configuration"""
    try:
        from .voice_production_config import get_voice_production_manager
        from .voice_config import get_voice_config_manager
        
        # Get production manager
        config_manager = get_voice_config_manager()
        production_manager = get_voice_production_manager(config_manager)
        
        # Get production-optimized configuration
        config = production_manager.get_production_config(user_id)
        
        return {
            "success": True,
            "config": config,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting voice production config: {e}")
        return {
            "success": False,
            "error": str(e),
            "fallback_config": {
                "featureToggles": {
                    "voice_input": True,
                    "voice_output": True,
                    "voice_settings": True,
                    "lazy_loading": False,
                    "performance_tracking": False
                }
            }
        }


@voice_router.get("/metrics")
async def get_voice_system_metrics(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current system metrics for monitoring (admin only)"""
    try:
        # Check if user is admin
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user or not getattr(user, 'is_admin', False):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        from .voice_production_config import get_voice_production_manager
        from .voice_config import get_voice_config_manager
        
        config_manager = get_voice_config_manager()
        production_manager = get_voice_production_manager(config_manager)
        
        metrics = production_manager.get_system_metrics()
        
        return {
            "success": True,
            "metrics": metrics,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice system metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")