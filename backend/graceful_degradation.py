"""
Graceful Degradation Handler

Implements graceful degradation strategies when database is unavailable or performing poorly.
Provides fallback mechanisms and user-friendly error responses.
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Union
from functools import wraps
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from .database_monitoring import get_database_health_score, database_monitor
from .database import PostgreSQLErrorHandler

logger = logging.getLogger(__name__)

class DegradationLevel:
    """Degradation level constants"""
    NONE = "none"
    MINIMAL = "minimal"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"
    SEVERE = "severe"

class GracefulDegradationHandler:
    """Handles graceful degradation scenarios"""
    
    def __init__(self):
        self.degradation_cache = {}
        self.fallback_responses = {}
        self.circuit_breaker_state = {}
        self.last_health_check = None
        self.health_check_interval = 30  # seconds
    
    def get_current_degradation_level(self) -> str:
        """Get current system degradation level"""
        try:
            health_score = get_database_health_score()
            
            if health_score >= 90:
                return DegradationLevel.NONE
            elif health_score >= 70:
                return DegradationLevel.MINIMAL
            elif health_score >= 50:
                return DegradationLevel.MODERATE
            elif health_score >= 30:
                return DegradationLevel.SIGNIFICANT
            else:
                return DegradationLevel.SEVERE
                
        except Exception as e:
            logger.error(f"Failed to get degradation level: {e}")
            return DegradationLevel.SEVERE
    
    def should_use_fallback(self, operation: str) -> bool:
        """Determine if operation should use fallback mechanism"""
        degradation_level = self.get_current_degradation_level()
        
        # Define which operations should use fallback at different levels
        fallback_rules = {
            DegradationLevel.NONE: [],
            DegradationLevel.MINIMAL: [],
            DegradationLevel.MODERATE: ["non_critical_queries", "analytics"],
            DegradationLevel.SIGNIFICANT: ["non_critical_queries", "analytics", "search", "recommendations"],
            DegradationLevel.SEVERE: ["non_critical_queries", "analytics", "search", "recommendations", "chat_history"]
        }
        
        return operation in fallback_rules.get(degradation_level, [])
    
    def get_fallback_response(self, operation: str, error: Exception = None) -> Dict[str, Any]:
        """Get appropriate fallback response for operation"""
        degradation_level = self.get_current_degradation_level()
        
        base_response = {
            "status": "degraded",
            "degradation_level": degradation_level,
            "timestamp": datetime.now().isoformat(),
            "message": self._get_user_friendly_message(degradation_level)
        }
        
        # Operation-specific fallback responses
        if operation == "chat_history":
            return {
                **base_response,
                "data": [],
                "message": "Chat history temporarily unavailable. Your conversation will continue normally."
            }
        elif operation == "search":
            return {
                **base_response,
                "data": {"results": [], "total": 0},
                "message": "Search temporarily unavailable. Please try again in a few moments."
            }
        elif operation == "analytics":
            return {
                **base_response,
                "data": {"metrics": {}, "charts": []},
                "message": "Analytics data temporarily unavailable."
            }
        elif operation == "recommendations":
            return {
                **base_response,
                "data": [],
                "message": "Recommendations temporarily unavailable."
            }
        else:
            return {
                **base_response,
                "message": "Service temporarily degraded. Core functionality remains available."
            }
    
    def _get_user_friendly_message(self, degradation_level: str) -> str:
        """Get user-friendly message for degradation level"""
        messages = {
            DegradationLevel.NONE: "All systems operating normally",
            DegradationLevel.MINIMAL: "Minor performance issues detected. Service continues normally.",
            DegradationLevel.MODERATE: "Some features may be slower than usual. Core functionality remains available.",
            DegradationLevel.SIGNIFICANT: "Reduced functionality due to system issues. Essential features remain available.",
            DegradationLevel.SEVERE: "Limited functionality available. We're working to restore full service."
        }
        return messages.get(degradation_level, "System status unknown")
    
    def create_circuit_breaker(self, operation: str, failure_threshold: int = 5, timeout: int = 60):
        """Create circuit breaker for operation"""
        if operation not in self.circuit_breaker_state:
            self.circuit_breaker_state[operation] = {
                "failures": 0,
                "last_failure": None,
                "state": "closed",  # closed, open, half_open
                "failure_threshold": failure_threshold,
                "timeout": timeout
            }
    
    def record_operation_result(self, operation: str, success: bool):
        """Record operation result for circuit breaker"""
        if operation not in self.circuit_breaker_state:
            self.create_circuit_breaker(operation)
        
        breaker = self.circuit_breaker_state[operation]
        
        if success:
            breaker["failures"] = 0
            if breaker["state"] == "half_open":
                breaker["state"] = "closed"
                logger.info(f"Circuit breaker for {operation} closed - operation successful")
        else:
            breaker["failures"] += 1
            breaker["last_failure"] = datetime.now()
            
            if breaker["failures"] >= breaker["failure_threshold"]:
                breaker["state"] = "open"
                logger.warning(f"Circuit breaker for {operation} opened - failure threshold reached")
    
    def is_circuit_breaker_open(self, operation: str) -> bool:
        """Check if circuit breaker is open for operation"""
        if operation not in self.circuit_breaker_state:
            return False
        
        breaker = self.circuit_breaker_state[operation]
        
        if breaker["state"] == "closed":
            return False
        elif breaker["state"] == "open":
            # Check if timeout has passed
            if breaker["last_failure"]:
                time_since_failure = (datetime.now() - breaker["last_failure"]).total_seconds()
                if time_since_failure >= breaker["timeout"]:
                    breaker["state"] = "half_open"
                    logger.info(f"Circuit breaker for {operation} half-opened - attempting recovery")
                    return False
            return True
        else:  # half_open
            return False

# Global degradation handler
degradation_handler = GracefulDegradationHandler()

def with_graceful_degradation(operation: str, fallback_enabled: bool = True):
    """Decorator for graceful degradation handling"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check circuit breaker
            if degradation_handler.is_circuit_breaker_open(operation):
                logger.warning(f"Circuit breaker open for {operation}, returning fallback response")
                if fallback_enabled:
                    return degradation_handler.get_fallback_response(operation)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Service temporarily unavailable: {operation}"
                    )
            
            # Check if should use fallback
            if fallback_enabled and degradation_handler.should_use_fallback(operation):
                logger.info(f"Using fallback for {operation} due to degradation")
                return degradation_handler.get_fallback_response(operation)
            
            # Execute operation with error handling
            try:
                result = func(*args, **kwargs)
                degradation_handler.record_operation_result(operation, True)
                return result
                
            except Exception as e:
                degradation_handler.record_operation_result(operation, False)
                
                # Determine if error should trigger fallback
                error_category = PostgreSQLErrorHandler.get_error_category(e)
                
                if fallback_enabled and error_category in ["transient", "connection"]:
                    logger.warning(f"Database error in {operation}, using fallback: {e}")
                    return degradation_handler.get_fallback_response(operation, e)
                else:
                    # Re-raise for permanent errors or when fallback disabled
                    raise
        
        return wrapper
    return decorator

def create_degraded_response(message: str, data: Any = None, status_code: int = 200) -> JSONResponse:
    """Create standardized degraded response"""
    response_data = {
        "status": "degraded",
        "message": message,
        "degradation_level": degradation_handler.get_current_degradation_level(),
        "timestamp": datetime.now().isoformat()
    }
    
    if data is not None:
        response_data["data"] = data
    
    return JSONResponse(content=response_data, status_code=status_code)

def get_system_status() -> Dict[str, Any]:
    """Get comprehensive system status for monitoring"""
    try:
        degradation_level = degradation_handler.get_current_degradation_level()
        health_score = get_database_health_score()
        
        # Get circuit breaker states
        circuit_breakers = {}
        for operation, state in degradation_handler.circuit_breaker_state.items():
            circuit_breakers[operation] = {
                "state": state["state"],
                "failures": state["failures"],
                "last_failure": state["last_failure"].isoformat() if state["last_failure"] else None
            }
        
        return {
            "degradation_level": degradation_level,
            "health_score": health_score,
            "circuit_breakers": circuit_breakers,
            "timestamp": datetime.now().isoformat(),
            "message": degradation_handler._get_user_friendly_message(degradation_level)
        }
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return {
            "degradation_level": "unknown",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Utility functions for common degradation scenarios
def handle_database_unavailable() -> JSONResponse:
    """Handle complete database unavailability"""
    return create_degraded_response(
        message="Database temporarily unavailable. Core functionality limited.",
        status_code=503
    )

def handle_slow_database() -> JSONResponse:
    """Handle slow database performance"""
    return create_degraded_response(
        message="Database performance degraded. Some operations may be slower."
    )

def handle_connection_pool_exhausted() -> JSONResponse:
    """Handle connection pool exhaustion"""
    return create_degraded_response(
        message="High system load detected. Please try again in a moment.",
        status_code=503
    )