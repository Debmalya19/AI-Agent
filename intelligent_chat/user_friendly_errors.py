"""
User-friendly error messaging and recovery UI components.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .models import ErrorState, ErrorSeverity, InteractiveElement, ContentType
from .exceptions import (
    ChatUIException, ToolExecutionError, ToolSelectionError, 
    ContextRetrievalError, RenderingError, TimeoutError, 
    ResourceLimitError, ValidationError, ConfigurationError
)


class ErrorCategory(Enum):
    """Categories of errors for user-friendly messaging."""
    TOOL_FAILURE = "tool_failure"
    NETWORK_ISSUE = "network_issue"
    TIMEOUT = "timeout"
    RESOURCE_LIMIT = "resource_limit"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    CONTEXT_ISSUE = "context_issue"
    RENDERING = "rendering"
    UNKNOWN = "unknown"


class RecoveryActionType(Enum):
    """Types of recovery actions users can take."""
    RETRY = "retry"
    SIMPLIFY_QUERY = "simplify_query"
    TRY_DIFFERENT_APPROACH = "try_different_approach"
    CONTACT_SUPPORT = "contact_support"
    WAIT_AND_RETRY = "wait_and_retry"
    CHECK_CONNECTION = "check_connection"
    REFRESH_PAGE = "refresh_page"
    CLEAR_CONTEXT = "clear_context"


@dataclass
class UserFriendlyError:
    """User-friendly error representation."""
    title: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    suggested_actions: List[str] = field(default_factory=list)
    recovery_buttons: List[Dict[str, Any]] = field(default_factory=list)
    technical_details: Optional[str] = None
    help_link: Optional[str] = None
    estimated_fix_time: Optional[str] = None


@dataclass
class ErrorUIComponent:
    """UI component for displaying errors."""
    component_type: str
    title: str
    message: str
    severity: ErrorSeverity
    actions: List[InteractiveElement] = field(default_factory=list)
    show_technical_details: bool = False
    technical_details: Optional[str] = None
    icon: Optional[str] = None
    color_scheme: Optional[str] = None


class UserFriendlyErrorGenerator:
    """
    Generates user-friendly error messages and recovery suggestions.
    
    Converts technical exceptions into clear, actionable messages that
    help users understand what went wrong and how to fix it.
    """
    
    def __init__(self, enable_technical_details: bool = False):
        """
        Initialize the error generator.
        
        Args:
            enable_technical_details: Whether to include technical details in errors
        """
        self.enable_technical_details = enable_technical_details
        self.logger = logging.getLogger(__name__)
        
        # Error message templates
        self._error_templates = {
            ErrorCategory.TOOL_FAILURE: {
                "title": "Service Temporarily Unavailable",
                "message": "I'm having trouble accessing one of my information sources. Let me try a different approach.",
                "actions": [RecoveryActionType.RETRY, RecoveryActionType.TRY_DIFFERENT_APPROACH],
                "icon": "⚠️",
                "color_scheme": "warning"
            },
            ErrorCategory.NETWORK_ISSUE: {
                "title": "Connection Issue",
                "message": "I'm experiencing connectivity problems. Please check your internet connection and try again.",
                "actions": [RecoveryActionType.CHECK_CONNECTION, RecoveryActionType.RETRY],
                "icon": "🌐",
                "color_scheme": "error"
            },
            ErrorCategory.TIMEOUT: {
                "title": "Request Taking Too Long",
                "message": "Your request is taking longer than expected. This might be due to high demand or complex processing.",
                "actions": [RecoveryActionType.WAIT_AND_RETRY, RecoveryActionType.SIMPLIFY_QUERY],
                "icon": "⏱️",
                "color_scheme": "warning",
                "estimated_fix_time": "1-2 minutes"
            },
            ErrorCategory.RESOURCE_LIMIT: {
                "title": "System Busy",
                "message": "I'm currently handling many requests. Please wait a moment and try again.",
                "actions": [RecoveryActionType.WAIT_AND_RETRY, RecoveryActionType.SIMPLIFY_QUERY],
                "icon": "🔄",
                "color_scheme": "info",
                "estimated_fix_time": "30 seconds"
            },
            ErrorCategory.VALIDATION: {
                "title": "Invalid Input",
                "message": "There's an issue with your request format. Please check your input and try again.",
                "actions": [RecoveryActionType.SIMPLIFY_QUERY, RecoveryActionType.TRY_DIFFERENT_APPROACH],
                "icon": "❌",
                "color_scheme": "error"
            },
            ErrorCategory.CONFIGURATION: {
                "title": "Configuration Issue",
                "message": "There's a configuration problem that's preventing me from processing your request.",
                "actions": [RecoveryActionType.CONTACT_SUPPORT, RecoveryActionType.REFRESH_PAGE],
                "icon": "⚙️",
                "color_scheme": "error"
            },
            ErrorCategory.CONTEXT_ISSUE: {
                "title": "Context Problem",
                "message": "I'm having trouble understanding the context of our conversation. Let me start fresh.",
                "actions": [RecoveryActionType.CLEAR_CONTEXT, RecoveryActionType.TRY_DIFFERENT_APPROACH],
                "icon": "💭",
                "color_scheme": "warning"
            },
            ErrorCategory.RENDERING: {
                "title": "Display Issue",
                "message": "I'm having trouble formatting the response properly. The content is available in simplified format.",
                "actions": [RecoveryActionType.REFRESH_PAGE, RecoveryActionType.RETRY],
                "icon": "🎨",
                "color_scheme": "info"
            },
            ErrorCategory.UNKNOWN: {
                "title": "Unexpected Error",
                "message": "Something unexpected happened. I'm working to resolve this issue.",
                "actions": [RecoveryActionType.RETRY, RecoveryActionType.CONTACT_SUPPORT],
                "icon": "❓",
                "color_scheme": "error"
            }
        }
        
        # Recovery action descriptions
        self._recovery_actions = {
            RecoveryActionType.RETRY: {
                "label": "Try Again",
                "description": "Retry the same request",
                "button_text": "Retry",
                "action_id": "retry_request"
            },
            RecoveryActionType.SIMPLIFY_QUERY: {
                "label": "Simplify Request",
                "description": "Try asking a simpler or more specific question",
                "button_text": "Simplify",
                "action_id": "simplify_query"
            },
            RecoveryActionType.TRY_DIFFERENT_APPROACH: {
                "label": "Different Approach",
                "description": "Try rephrasing your question or asking something else",
                "button_text": "Rephrase",
                "action_id": "different_approach"
            },
            RecoveryActionType.CONTACT_SUPPORT: {
                "label": "Contact Support",
                "description": "Get help from our support team",
                "button_text": "Get Help",
                "action_id": "contact_support"
            },
            RecoveryActionType.WAIT_AND_RETRY: {
                "label": "Wait and Retry",
                "description": "Wait a moment and try again",
                "button_text": "Wait & Retry",
                "action_id": "wait_retry"
            },
            RecoveryActionType.CHECK_CONNECTION: {
                "label": "Check Connection",
                "description": "Verify your internet connection",
                "button_text": "Check Network",
                "action_id": "check_connection"
            },
            RecoveryActionType.REFRESH_PAGE: {
                "label": "Refresh",
                "description": "Refresh the page to reset the interface",
                "button_text": "Refresh",
                "action_id": "refresh_page"
            },
            RecoveryActionType.CLEAR_CONTEXT: {
                "label": "Start Fresh",
                "description": "Clear conversation history and start over",
                "button_text": "Start Over",
                "action_id": "clear_context"
            }
        }
    
    def generate_user_friendly_error(
        self, 
        error: Exception, 
        context: Optional[Dict[str, Any]] = None
    ) -> UserFriendlyError:
        """
        Generate a user-friendly error message from an exception.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            UserFriendlyError with user-friendly messaging
        """
        category = self._categorize_error(error)
        severity = self._determine_severity(error, category)
        template = self._error_templates[category]
        
        # Customize message based on specific error details
        title, message = self._customize_message(error, template, context)
        
        # Generate suggested actions
        suggested_actions = self._generate_suggested_actions(error, category, context)
        
        # Create recovery buttons
        recovery_buttons = self._create_recovery_buttons(template["actions"])
        
        # Add technical details if enabled
        technical_details = None
        if self.enable_technical_details:
            technical_details = self._format_technical_details(error, context)
        
        # Determine help link
        help_link = self._get_help_link(category)
        
        return UserFriendlyError(
            title=title,
            message=message,
            category=category,
            severity=severity,
            suggested_actions=suggested_actions,
            recovery_buttons=recovery_buttons,
            technical_details=technical_details,
            help_link=help_link,
            estimated_fix_time=template.get("estimated_fix_time")
        )
    
    def create_error_ui_component(
        self, 
        user_friendly_error: UserFriendlyError
    ) -> ErrorUIComponent:
        """
        Create a UI component for displaying the error.
        
        Args:
            user_friendly_error: The user-friendly error to display
            
        Returns:
            ErrorUIComponent for rendering
        """
        template = self._error_templates[user_friendly_error.category]
        
        # Create interactive elements for recovery actions
        actions = []
        for button in user_friendly_error.recovery_buttons:
            action = InteractiveElement(
                element_type="button",
                element_id=button["action_id"],
                properties={
                    "text": button["button_text"],
                    "description": button["description"],
                    "variant": "primary" if button["action_id"] == "retry_request" else "secondary",
                    "icon": button.get("icon")
                },
                actions=[button["action_id"]]
            )
            actions.append(action)
        
        return ErrorUIComponent(
            component_type="error_display",
            title=user_friendly_error.title,
            message=user_friendly_error.message,
            severity=user_friendly_error.severity,
            actions=actions,
            show_technical_details=self.enable_technical_details and user_friendly_error.technical_details is not None,
            technical_details=user_friendly_error.technical_details,
            icon=template.get("icon"),
            color_scheme=template.get("color_scheme")
        )
    
    def create_error_state(
        self, 
        error: Exception, 
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorState:
        """
        Create an ErrorState object for the UI system.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            ErrorState for UI integration
        """
        user_friendly_error = self.generate_user_friendly_error(error, context)
        
        return ErrorState(
            error_type=type(error).__name__,
            message=user_friendly_error.message,
            severity=user_friendly_error.severity,
            recovery_actions=[action["label"] for action in user_friendly_error.recovery_buttons],
            context={
                "title": user_friendly_error.title,
                "category": user_friendly_error.category.value,
                "suggested_actions": user_friendly_error.suggested_actions,
                "recovery_buttons": user_friendly_error.recovery_buttons,
                "technical_details": user_friendly_error.technical_details,
                "help_link": user_friendly_error.help_link,
                "estimated_fix_time": user_friendly_error.estimated_fix_time
            }
        )
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize an error for appropriate messaging."""
        if isinstance(error, ToolExecutionError):
            return ErrorCategory.TOOL_FAILURE
        elif isinstance(error, ToolSelectionError):
            return ErrorCategory.TOOL_FAILURE
        elif isinstance(error, TimeoutError):
            return ErrorCategory.TIMEOUT
        elif isinstance(error, ResourceLimitError):
            return ErrorCategory.RESOURCE_LIMIT
        elif isinstance(error, ValidationError):
            return ErrorCategory.VALIDATION
        elif isinstance(error, ConfigurationError):
            return ErrorCategory.CONFIGURATION
        elif isinstance(error, ContextRetrievalError):
            return ErrorCategory.CONTEXT_ISSUE
        elif isinstance(error, RenderingError):
            return ErrorCategory.RENDERING
        elif "network" in str(error).lower() or "connection" in str(error).lower():
            return ErrorCategory.NETWORK_ISSUE
        else:
            return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity for UI display."""
        if category in [ErrorCategory.CONFIGURATION, ErrorCategory.NETWORK_ISSUE]:
            return ErrorSeverity.ERROR
        elif category in [ErrorCategory.TOOL_FAILURE, ErrorCategory.TIMEOUT, ErrorCategory.CONTEXT_ISSUE]:
            return ErrorSeverity.WARNING
        elif category in [ErrorCategory.RENDERING, ErrorCategory.RESOURCE_LIMIT]:
            return ErrorSeverity.INFO
        else:
            return ErrorSeverity.ERROR
    
    def _customize_message(
        self, 
        error: Exception, 
        template: Dict[str, Any], 
        context: Optional[Dict[str, Any]]
    ) -> Tuple[str, str]:
        """Customize error message based on specific error details."""
        title = template["title"]
        message = template["message"]
        
        # Customize based on specific error types
        if isinstance(error, ToolExecutionError):
            if hasattr(error, 'tool_name') and error.tool_name:
                message = f"I'm having trouble with the {error.tool_name} service. Let me try a different approach to help you."
        
        elif isinstance(error, TimeoutError):
            if hasattr(error, 'timeout_duration') and error.timeout_duration:
                message = f"Your request is taking longer than the usual {error.timeout_duration} seconds. This might be due to high demand or complex processing."
        
        elif isinstance(error, ResourceLimitError):
            if hasattr(error, 'resource_type') and error.resource_type:
                message = f"I'm currently at capacity for {error.resource_type} resources. Please wait a moment and try again."
        
        elif isinstance(error, ValidationError):
            if hasattr(error, 'field_name') and error.field_name:
                message = f"There's an issue with the {error.field_name} in your request. Please check and try again."
        
        # Add context-specific customizations
        if context:
            query = context.get('query')
            if query and len(query) > 100:
                message += " You might want to try a shorter, more specific question."
            
            tool_name = context.get('tool_name')
            if tool_name:
                message = message.replace("information sources", f"{tool_name} service")
        
        return title, message
    
    def _generate_suggested_actions(
        self, 
        error: Exception, 
        category: ErrorCategory, 
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Generate specific suggested actions based on error context."""
        suggestions = []
        
        if category == ErrorCategory.TOOL_FAILURE:
            suggestions.extend([
                "Try rephrasing your question",
                "Ask for a different type of information",
                "Wait a moment and try again"
            ])
        
        elif category == ErrorCategory.TIMEOUT:
            suggestions.extend([
                "Try a simpler or more specific question",
                "Break complex requests into smaller parts",
                "Wait a moment for the system to catch up"
            ])
        
        elif category == ErrorCategory.RESOURCE_LIMIT:
            suggestions.extend([
                "Wait 30 seconds and try again",
                "Try a simpler request",
                "Ask one question at a time"
            ])
        
        elif category == ErrorCategory.VALIDATION:
            suggestions.extend([
                "Check your input for typos or formatting issues",
                "Try a different way of asking your question",
                "Make sure your request is clear and specific"
            ])
        
        elif category == ErrorCategory.NETWORK_ISSUE:
            suggestions.extend([
                "Check your internet connection",
                "Try refreshing the page",
                "Wait a moment and try again"
            ])
        
        elif category == ErrorCategory.CONTEXT_ISSUE:
            suggestions.extend([
                "Start a new conversation",
                "Provide more context in your question",
                "Ask your question differently"
            ])
        
        else:
            suggestions.extend([
                "Try again in a moment",
                "Refresh the page",
                "Contact support if the problem persists"
            ])
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    def _create_recovery_buttons(self, action_types: List[RecoveryActionType]) -> List[Dict[str, Any]]:
        """Create recovery button configurations."""
        buttons = []
        
        for action_type in action_types:
            if action_type in self._recovery_actions:
                action_config = self._recovery_actions[action_type]
                button = {
                    "label": action_config["label"],
                    "description": action_config["description"],
                    "button_text": action_config["button_text"],
                    "action_id": action_config["action_id"]
                }
                buttons.append(button)
        
        return buttons
    
    def _format_technical_details(
        self, 
        error: Exception, 
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Format technical details for debugging."""
        details = []
        
        details.append(f"Error Type: {type(error).__name__}")
        details.append(f"Error Message: {str(error)}")
        
        if hasattr(error, 'context') and error.context:
            details.append(f"Error Context: {error.context}")
        
        if context:
            details.append(f"Additional Context: {context}")
        
        return "\n".join(details)
    
    def _get_help_link(self, category: ErrorCategory) -> Optional[str]:
        """Get help documentation link for error category."""
        help_links = {
            ErrorCategory.TOOL_FAILURE: "/help/tool-issues",
            ErrorCategory.NETWORK_ISSUE: "/help/connection-problems",
            ErrorCategory.TIMEOUT: "/help/performance-issues",
            ErrorCategory.RESOURCE_LIMIT: "/help/system-limits",
            ErrorCategory.VALIDATION: "/help/input-formatting",
            ErrorCategory.CONFIGURATION: "/help/configuration",
            ErrorCategory.CONTEXT_ISSUE: "/help/conversation-context",
            ErrorCategory.RENDERING: "/help/display-issues"
        }
        
        return help_links.get(category)


class ErrorRecoveryHandler:
    """
    Handles user-initiated error recovery actions.
    
    Processes recovery button clicks and executes appropriate recovery strategies.
    """
    
    def __init__(self, chat_manager=None, error_handler=None):
        """
        Initialize the recovery handler.
        
        Args:
            chat_manager: Chat manager for retrying requests
            error_handler: Error handler for recovery strategies
        """
        self.chat_manager = chat_manager
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
    
    async def handle_recovery_action(
        self, 
        action_id: str, 
        original_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle a user-initiated recovery action.
        
        Args:
            action_id: ID of the recovery action to execute
            original_context: Context from the original failed request
            
        Returns:
            Result of the recovery action
        """
        try:
            if action_id == "retry_request":
                return await self._handle_retry(original_context)
            
            elif action_id == "simplify_query":
                return await self._handle_simplify_query(original_context)
            
            elif action_id == "different_approach":
                return await self._handle_different_approach(original_context)
            
            elif action_id == "wait_retry":
                return await self._handle_wait_retry(original_context)
            
            elif action_id == "clear_context":
                return await self._handle_clear_context(original_context)
            
            elif action_id == "refresh_page":
                return self._handle_refresh_page()
            
            elif action_id == "contact_support":
                return self._handle_contact_support(original_context)
            
            elif action_id == "check_connection":
                return self._handle_check_connection()
            
            else:
                return {
                    "success": False,
                    "message": f"Unknown recovery action: {action_id}"
                }
                
        except Exception as e:
            self.logger.error(f"Recovery action failed: {e}")
            return {
                "success": False,
                "message": f"Recovery action failed: {str(e)}"
            }
    
    async def _handle_retry(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle retry recovery action."""
        if self.chat_manager and "query" in context:
            try:
                # Retry the original request
                response = await self.chat_manager.process_message(
                    context["query"],
                    context.get("user_id", ""),
                    context.get("session_id", "")
                )
                return {
                    "success": True,
                    "message": "Request retried successfully",
                    "response": response
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Retry failed: {str(e)}"
                }
        else:
            return {
                "success": False,
                "message": "Cannot retry: missing context or chat manager"
            }
    
    async def _handle_simplify_query(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle simplify query recovery action."""
        return {
            "success": True,
            "message": "Please try asking a simpler or more specific question",
            "suggestion": "Break down complex requests into smaller parts"
        }
    
    async def _handle_different_approach(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle different approach recovery action."""
        return {
            "success": True,
            "message": "Try rephrasing your question or asking about something else",
            "suggestion": "Consider asking for different information or using different keywords"
        }
    
    async def _handle_wait_retry(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle wait and retry recovery action."""
        import asyncio
        await asyncio.sleep(2)  # Brief wait
        return await self._handle_retry(context)
    
    async def _handle_clear_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle clear context recovery action."""
        return {
            "success": True,
            "message": "Conversation context cleared. You can start fresh now.",
            "action": "clear_context"
        }
    
    def _handle_refresh_page(self) -> Dict[str, Any]:
        """Handle refresh page recovery action."""
        return {
            "success": True,
            "message": "Please refresh the page to reset the interface",
            "action": "refresh_page"
        }
    
    def _handle_contact_support(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle contact support recovery action."""
        return {
            "success": True,
            "message": "Support contact information provided",
            "support_info": {
                "email": "support@example.com",
                "help_center": "/help",
                "error_context": context
            }
        }
    
    def _handle_check_connection(self) -> Dict[str, Any]:
        """Handle check connection recovery action."""
        return {
            "success": True,
            "message": "Please check your internet connection and try again",
            "suggestion": "Verify you can access other websites"
        }