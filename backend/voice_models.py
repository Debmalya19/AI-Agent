"""
Voice assistant Pydantic models for API validation and data transfer.
These models handle voice settings, analytics, and API request/response validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class VoiceActionType(str, Enum):
    """Enumeration of voice action types for analytics"""
    STT_START = "stt_start"
    STT_COMPLETE = "stt_complete"
    STT_ERROR = "stt_error"
    TTS_START = "tts_start"
    TTS_COMPLETE = "tts_complete"
    TTS_ERROR = "tts_error"
    VOICE_ENABLED = "voice_enabled"
    VOICE_DISABLED = "voice_disabled"


class VoiceSettings(BaseModel):
    """Pydantic model for voice settings validation"""
    auto_play_enabled: bool = Field(default=False, description="Enable automatic TTS playback")
    voice_name: str = Field(default="default", description="Selected TTS voice name")
    speech_rate: float = Field(default=1.0, ge=0.1, le=3.0, description="Speech rate (0.1-3.0)")
    speech_pitch: float = Field(default=1.0, ge=0.0, le=2.0, description="Speech pitch (0.0-2.0)")
    speech_volume: float = Field(default=1.0, ge=0.0, le=1.0, description="Speech volume (0.0-1.0)")
    language: str = Field(default="en-US", description="Speech recognition language")
    microphone_sensitivity: float = Field(default=0.5, ge=0.0, le=1.0, description="Microphone sensitivity")
    noise_cancellation: bool = Field(default=True, description="Enable noise cancellation")

    @validator('voice_name')
    def validate_voice_name(cls, v):
        """Validate voice name format"""
        if not v or len(v.strip()) == 0:
            return "default"
        return v.strip()

    @validator('language')
    def validate_language(cls, v):
        """Validate language code format"""
        if not v or len(v) < 2:
            return "en-US"
        # Basic validation for language code format (e.g., en-US, fr-FR)
        if len(v) == 2 or (len(v) == 5 and v[2] == '-'):
            return v
        return "en-US"

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class VoiceSettingsUpdate(BaseModel):
    """Pydantic model for voice settings updates (partial updates allowed)"""
    auto_play_enabled: Optional[bool] = None
    voice_name: Optional[str] = None
    speech_rate: Optional[float] = Field(None, ge=0.1, le=3.0)
    speech_pitch: Optional[float] = Field(None, ge=0.0, le=2.0)
    speech_volume: Optional[float] = Field(None, ge=0.0, le=1.0)
    language: Optional[str] = None
    microphone_sensitivity: Optional[float] = Field(None, ge=0.0, le=1.0)
    noise_cancellation: Optional[bool] = None

    @validator('voice_name')
    def validate_voice_name(cls, v):
        """Validate voice name format"""
        if v is not None and (not v or len(v.strip()) == 0):
            raise ValueError("voice_name cannot be empty")
        return v.strip() if v else v

    @validator('language')
    def validate_language(cls, v):
        """Validate language code format"""
        if v is not None:
            if not v or len(v) < 2:
                raise ValueError("Invalid language code")
            # Basic validation for language code format
            if not (len(v) == 2 or (len(v) == 5 and v[2] == '-')):
                raise ValueError("Language code must be in format 'en' or 'en-US'")
        return v


class VoiceAnalytics(BaseModel):
    """Pydantic model for voice analytics data"""
    action_type: VoiceActionType = Field(..., description="Type of voice action")
    duration_ms: Optional[int] = Field(None, ge=0, description="Duration in milliseconds")
    text_length: Optional[int] = Field(None, ge=0, description="Length of processed text")
    accuracy_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Accuracy score (0.0-1.0)")
    error_message: Optional[str] = Field(None, description="Error message if action failed")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    @validator('error_message')
    def validate_error_message(cls, v):
        """Validate error message length"""
        if v and len(v) > 1000:
            return v[:1000]  # Truncate long error messages
        return v

    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata is JSON serializable"""
        if v is None:
            return {}
        # Ensure all values are JSON serializable
        try:
            import json
            json.dumps(v)
            return v
        except (TypeError, ValueError):
            return {}

    class Config:
        """Pydantic configuration"""
        use_enum_values = True


class VoiceCapabilities(BaseModel):
    """Pydantic model for voice capabilities response"""
    speech_recognition_available: bool = Field(..., description="Speech recognition available")
    speech_synthesis_available: bool = Field(..., description="Speech synthesis available")
    available_voices: List[str] = Field(default_factory=list, description="Available TTS voices")
    supported_languages: List[str] = Field(default_factory=list, description="Supported languages")
    browser_support: Dict[str, bool] = Field(default_factory=dict, description="Browser feature support")


class VoiceSettingsResponse(BaseModel):
    """Pydantic model for voice settings API response"""
    success: bool = Field(..., description="Operation success status")
    settings: Optional[VoiceSettings] = Field(None, description="Voice settings data")
    message: Optional[str] = Field(None, description="Response message")


class VoiceAnalyticsResponse(BaseModel):
    """Pydantic model for voice analytics API response"""
    success: bool = Field(..., description="Operation success status")
    message: Optional[str] = Field(None, description="Response message")
    analytics_id: Optional[int] = Field(None, description="Created analytics record ID")


class VoiceErrorResponse(BaseModel):
    """Pydantic model for voice API error responses"""
    success: bool = Field(default=False, description="Operation success status")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for client handling")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


# Request models for API endpoints
class VoiceSettingsRequest(BaseModel):
    """Request model for updating voice settings"""
    settings: VoiceSettingsUpdate = Field(..., description="Voice settings to update")


class VoiceAnalyticsRequest(BaseModel):
    """Request model for logging voice analytics"""
    analytics: VoiceAnalytics = Field(..., description="Voice analytics data")


# Utility functions for model validation
def validate_voice_settings_data(data: Dict[str, Any]) -> VoiceSettings:
    """Validate and create VoiceSettings from dictionary data"""
    try:
        return VoiceSettings(**data)
    except Exception as e:
        raise ValueError(f"Invalid voice settings data: {str(e)}")


def validate_voice_analytics_data(data: Dict[str, Any]) -> VoiceAnalytics:
    """Validate and create VoiceAnalytics from dictionary data"""
    try:
        return VoiceAnalytics(**data)
    except Exception as e:
        raise ValueError(f"Invalid voice analytics data: {str(e)}")


# Default voice settings
DEFAULT_VOICE_SETTINGS = VoiceSettings()