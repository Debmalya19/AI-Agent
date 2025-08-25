"""
Exception classes for the intelligent chat UI system.
"""

from typing import Optional, Dict, Any, List


class ChatUIException(Exception):
    """Base exception for intelligent chat UI system."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}
        self.message = message


class ToolExecutionError(ChatUIException):
    """Exception raised when tool execution fails."""
    
    def __init__(
        self, 
        message: str, 
        tool_name: str, 
        execution_time: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, context)
        self.tool_name = tool_name
        self.execution_time = execution_time


class ToolSelectionError(ChatUIException):
    """Exception raised when tool selection fails."""
    
    def __init__(
        self, 
        message: str, 
        query: str,
        available_tools: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, context)
        self.query = query
        self.available_tools = available_tools or []


class ContextRetrievalError(ChatUIException):
    """Exception raised when context retrieval fails."""
    
    def __init__(
        self, 
        message: str, 
        user_id: str,
        query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, context)
        self.user_id = user_id
        self.query = query


class RenderingError(ChatUIException):
    """Exception raised when response rendering fails."""
    
    def __init__(
        self, 
        message: str, 
        content: str,
        content_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, context)
        self.content = content
        self.content_type = content_type


class ConfigurationError(ChatUIException):
    """Exception raised when configuration is invalid."""
    
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, context)
        self.config_key = config_key


class ValidationError(ChatUIException):
    """Exception raised when data validation fails."""
    
    def __init__(
        self, 
        message: str, 
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, context)
        self.field_name = field_name
        self.field_value = field_value


class ResourceLimitError(ChatUIException):
    """Exception raised when resource limits are exceeded."""
    
    def __init__(
        self, 
        message: str, 
        resource_type: str,
        current_usage: Optional[float] = None,
        limit: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, context)
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.limit = limit


class TimeoutError(ChatUIException):
    """Exception raised when operations timeout."""
    
    def __init__(
        self, 
        message: str, 
        operation: str,
        timeout_duration: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, context)
        self.operation = operation
        self.timeout_duration = timeout_duration


class DependencyError(ChatUIException):
    """Exception raised when dependencies are not met."""
    
    def __init__(
        self, 
        message: str, 
        missing_dependencies: List[str],
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, context)
        self.missing_dependencies = missing_dependencies