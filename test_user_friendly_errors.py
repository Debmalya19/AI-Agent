"""
Tests for user-friendly error messaging and recovery UI components.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from intelligent_chat.user_friendly_errors import (
    UserFriendlyErrorGenerator, ErrorRecoveryHandler, ErrorCategory,
    RecoveryActionType, UserFriendlyError, ErrorUIComponent
)
from intelligent_chat.models import ErrorState, ErrorSeverity, InteractiveElement
from intelligent_chat.exceptions import (
    ToolExecutionError, ToolSelectionError, ContextRetrievalError,
    RenderingError, TimeoutError, ResourceLimitError, ValidationError,
    ConfigurationError
)


class TestUserFriendlyErrorGenerator:
    """Test cases for UserFriendlyErrorGenerator class."""
    
    @pytest.fixture
    def error_generator(self):
        """Create UserFriendlyErrorGenerator instance for testing."""
        return UserFriendlyErrorGenerator(enable_technical_details=True)
    
    @pytest.fixture
    def error_generator_no_tech(self):
        """Create UserFriendlyErrorGenerator without technical details."""
        return UserFriendlyErrorGenerator(enable_technical_details=False)
    
    def test_initialization(self, error_generator):
        """Test UserFriendlyErrorGenerator initialization."""
        assert error_generator.enable_technical_details is True
        assert len(error_generator._error_templates) > 0
        assert len(error_generator._recovery_actions) > 0
        assert ErrorCategory.TOOL_FAILURE in error_generator._error_templates
        assert RecoveryActionType.RETRY in error_generator._recovery_actions
    
    def test_categorize_tool_execution_error(self, error_generator):
        """Test categorization of tool execution error."""
        error = ToolExecutionError("Tool failed", "test_tool")
        category = error_generator._categorize_error(error)
        assert category == ErrorCategory.TOOL_FAILURE
    
    def test_categorize_timeout_error(self, error_generator):
        """Test categorization of timeout error."""
        error = TimeoutError("Request timed out", "test_operation", 30.0)
        category = error_generator._categorize_error(error)
        assert category == ErrorCategory.TIMEOUT
    
    def test_categorize_resource_limit_error(self, error_generator):
        """Test categorization of resource limit error."""
        error = ResourceLimitError("Resource limit exceeded", "memory", 100.0, 80.0)
        category = error_generator._categorize_error(error)
        assert category == ErrorCategory.RESOURCE_LIMIT
    
    def test_categorize_validation_error(self, error_generator):
        """Test categorization of validation error."""
        error = ValidationError("Invalid input", "field_name", "invalid_value")
        category = error_generator._categorize_error(error)
        assert category == ErrorCategory.VALIDATION
    
    def test_categorize_configuration_error(self, error_generator):
        """Test categorization of configuration error."""
        error = ConfigurationError("Config missing", "api_key")
        category = error_generator._categorize_error(error)
        assert category == ErrorCategory.CONFIGURATION
    
    def test_categorize_context_retrieval_error(self, error_generator):
        """Test categorization of context retrieval error."""
        error = ContextRetrievalError("Context failed", "user123")
        category = error_generator._categorize_error(error)
        assert category == ErrorCategory.CONTEXT_ISSUE
    
    def test_categorize_rendering_error(self, error_generator):
        """Test categorization of rendering error."""
        error = RenderingError("Render failed", "test content")
        category = error_generator._categorize_error(error)
        assert category == ErrorCategory.RENDERING
    
    def test_categorize_network_error(self, error_generator):
        """Test categorization of network-related error."""
        error = Exception("Network connection failed")
        category = error_generator._categorize_error(error)
        assert category == ErrorCategory.NETWORK_ISSUE
    
    def test_categorize_unknown_error(self, error_generator):
        """Test categorization of unknown error."""
        error = Exception("Some random error")
        category = error_generator._categorize_error(error)
        assert category == ErrorCategory.UNKNOWN
    
    def test_determine_severity_configuration_error(self, error_generator):
        """Test severity determination for configuration error."""
        error = ConfigurationError("Config missing", "api_key")
        severity = error_generator._determine_severity(error, ErrorCategory.CONFIGURATION)
        assert severity == ErrorSeverity.ERROR
    
    def test_determine_severity_tool_failure(self, error_generator):
        """Test severity determination for tool failure."""
        error = ToolExecutionError("Tool failed", "test_tool")
        severity = error_generator._determine_severity(error, ErrorCategory.TOOL_FAILURE)
        assert severity == ErrorSeverity.WARNING
    
    def test_determine_severity_rendering_error(self, error_generator):
        """Test severity determination for rendering error."""
        error = RenderingError("Render failed", "test content")
        severity = error_generator._determine_severity(error, ErrorCategory.RENDERING)
        assert severity == ErrorSeverity.INFO
    
    def test_customize_message_tool_execution_error(self, error_generator):
        """Test message customization for tool execution error."""
        error = ToolExecutionError("Tool failed", "BTWebsiteSearch")
        template = error_generator._error_templates[ErrorCategory.TOOL_FAILURE]
        
        title, message = error_generator._customize_message(error, template, None)
        
        assert "BTWebsiteSearch" in message
        assert "different approach" in message
    
    def test_customize_message_timeout_error(self, error_generator):
        """Test message customization for timeout error."""
        error = TimeoutError("Request timed out", "test_operation", 30.0)
        template = error_generator._error_templates[ErrorCategory.TIMEOUT]
        
        title, message = error_generator._customize_message(error, template, None)
        
        assert "30.0 seconds" in message
    
    def test_customize_message_with_context(self, error_generator):
        """Test message customization with context."""
        error = ToolExecutionError("Tool failed", "test_tool")
        template = error_generator._error_templates[ErrorCategory.TOOL_FAILURE]
        context = {"query": "This is a very long query that exceeds one hundred characters and should trigger a suggestion to use a shorter question"}
        
        title, message = error_generator._customize_message(error, template, context)
        
        assert "shorter, more specific question" in message
    
    def test_generate_suggested_actions_tool_failure(self, error_generator):
        """Test suggested actions generation for tool failure."""
        error = ToolExecutionError("Tool failed", "test_tool")
        suggestions = error_generator._generate_suggested_actions(
            error, ErrorCategory.TOOL_FAILURE, None
        )
        
        assert len(suggestions) <= 3
        assert any("rephrasing" in suggestion.lower() for suggestion in suggestions)
    
    def test_generate_suggested_actions_timeout(self, error_generator):
        """Test suggested actions generation for timeout."""
        error = TimeoutError("Request timed out", "test_operation", 30.0)
        suggestions = error_generator._generate_suggested_actions(
            error, ErrorCategory.TIMEOUT, None
        )
        
        assert len(suggestions) <= 3
        assert any("simpler" in suggestion.lower() for suggestion in suggestions)
    
    def test_create_recovery_buttons(self, error_generator):
        """Test recovery button creation."""
        action_types = [RecoveryActionType.RETRY, RecoveryActionType.SIMPLIFY_QUERY]
        buttons = error_generator._create_recovery_buttons(action_types)
        
        assert len(buttons) == 2
        assert buttons[0]["action_id"] == "retry_request"
        assert buttons[1]["action_id"] == "simplify_query"
        assert all("button_text" in button for button in buttons)
    
    def test_format_technical_details(self, error_generator):
        """Test technical details formatting."""
        error = ToolExecutionError("Tool failed", "test_tool")
        context = {"query": "test query", "user_id": "user123"}
        
        details = error_generator._format_technical_details(error, context)
        
        assert "Error Type: ToolExecutionError" in details
        assert "Error Message: Tool failed" in details
        assert "Additional Context:" in details
    
    def test_get_help_link(self, error_generator):
        """Test help link generation."""
        link = error_generator._get_help_link(ErrorCategory.TOOL_FAILURE)
        assert link == "/help/tool-issues"
        
        link = error_generator._get_help_link(ErrorCategory.NETWORK_ISSUE)
        assert link == "/help/connection-problems"
    
    def test_generate_user_friendly_error_complete(self, error_generator):
        """Test complete user-friendly error generation."""
        error = ToolExecutionError("Tool execution failed", "BTWebsiteSearch")
        context = {"query": "test query", "user_id": "user123"}
        
        user_error = error_generator.generate_user_friendly_error(error, context)
        
        assert isinstance(user_error, UserFriendlyError)
        assert user_error.title == "Service Temporarily Unavailable"
        assert "BTWebsiteSearch" in user_error.message
        assert user_error.category == ErrorCategory.TOOL_FAILURE
        assert user_error.severity == ErrorSeverity.WARNING
        assert len(user_error.suggested_actions) > 0
        assert len(user_error.recovery_buttons) > 0
        assert user_error.technical_details is not None  # Technical details enabled
        assert user_error.help_link == "/help/tool-issues"
    
    def test_generate_user_friendly_error_no_technical_details(self, error_generator_no_tech):
        """Test user-friendly error generation without technical details."""
        error = ToolExecutionError("Tool execution failed", "test_tool")
        
        user_error = error_generator_no_tech.generate_user_friendly_error(error)
        
        assert isinstance(user_error, UserFriendlyError)
        assert user_error.technical_details is None
    
    def test_create_error_ui_component(self, error_generator):
        """Test error UI component creation."""
        error = TimeoutError("Request timed out", "test_operation", 30.0)
        user_error = error_generator.generate_user_friendly_error(error)
        
        ui_component = error_generator.create_error_ui_component(user_error)
        
        assert isinstance(ui_component, ErrorUIComponent)
        assert ui_component.component_type == "error_display"
        assert ui_component.title == user_error.title
        assert ui_component.message == user_error.message
        assert ui_component.severity == user_error.severity
        assert len(ui_component.actions) > 0
        assert ui_component.icon == "⏱️"
        assert ui_component.color_scheme == "warning"
        
        # Check interactive elements
        for action in ui_component.actions:
            assert isinstance(action, InteractiveElement)
            assert action.element_type == "button"
            assert "text" in action.properties
    
    def test_create_error_state(self, error_generator):
        """Test error state creation."""
        error = ResourceLimitError("Resource limit exceeded", "memory", 100.0, 80.0)
        context = {"query": "test query"}
        
        error_state = error_generator.create_error_state(error, context)
        
        assert isinstance(error_state, ErrorState)
        assert error_state.error_type == "ResourceLimitError"
        assert error_state.severity == ErrorSeverity.INFO
        assert len(error_state.recovery_actions) > 0
        assert "title" in error_state.context
        assert "category" in error_state.context
        assert error_state.context["category"] == "resource_limit"


class TestErrorRecoveryHandler:
    """Test cases for ErrorRecoveryHandler class."""
    
    @pytest.fixture
    def mock_chat_manager(self):
        """Mock chat manager."""
        manager = AsyncMock()
        manager.process_message.return_value = Mock(content="Retry successful")
        return manager
    
    @pytest.fixture
    def mock_error_handler(self):
        """Mock error handler."""
        return Mock()
    
    @pytest.fixture
    def recovery_handler(self, mock_chat_manager, mock_error_handler):
        """Create ErrorRecoveryHandler instance for testing."""
        return ErrorRecoveryHandler(
            chat_manager=mock_chat_manager,
            error_handler=mock_error_handler
        )
    
    def test_initialization(self, recovery_handler, mock_chat_manager, mock_error_handler):
        """Test ErrorRecoveryHandler initialization."""
        assert recovery_handler.chat_manager == mock_chat_manager
        assert recovery_handler.error_handler == mock_error_handler
    
    @pytest.mark.asyncio
    async def test_handle_retry_action_success(self, recovery_handler, mock_chat_manager):
        """Test successful retry action handling."""
        context = {
            "query": "test query",
            "user_id": "user123",
            "session_id": "session456"
        }
        
        result = await recovery_handler.handle_recovery_action("retry_request", context)
        
        assert result["success"] is True
        assert "retried successfully" in result["message"]
        assert "response" in result
        mock_chat_manager.process_message.assert_called_once_with(
            "test query", "user123", "session456"
        )
    
    @pytest.mark.asyncio
    async def test_handle_retry_action_failure(self, recovery_handler, mock_chat_manager):
        """Test retry action handling with failure."""
        mock_chat_manager.process_message.side_effect = Exception("Retry failed")
        context = {"query": "test query", "user_id": "user123", "session_id": "session456"}
        
        result = await recovery_handler.handle_recovery_action("retry_request", context)
        
        assert result["success"] is False
        assert "Retry failed" in result["message"]
    
    @pytest.mark.asyncio
    async def test_handle_retry_action_missing_context(self, recovery_handler):
        """Test retry action handling with missing context."""
        context = {}  # Missing query
        
        result = await recovery_handler.handle_recovery_action("retry_request", context)
        
        assert result["success"] is False
        assert "missing context" in result["message"]
    
    @pytest.mark.asyncio
    async def test_handle_simplify_query_action(self, recovery_handler):
        """Test simplify query action handling."""
        context = {"query": "complex query"}
        
        result = await recovery_handler.handle_recovery_action("simplify_query", context)
        
        assert result["success"] is True
        assert "simpler" in result["message"]
        assert "suggestion" in result
    
    @pytest.mark.asyncio
    async def test_handle_different_approach_action(self, recovery_handler):
        """Test different approach action handling."""
        context = {"query": "test query"}
        
        result = await recovery_handler.handle_recovery_action("different_approach", context)
        
        assert result["success"] is True
        assert "rephrasing" in result["message"]
        assert "suggestion" in result
    
    @pytest.mark.asyncio
    async def test_handle_wait_retry_action(self, recovery_handler, mock_chat_manager):
        """Test wait and retry action handling."""
        context = {
            "query": "test query",
            "user_id": "user123",
            "session_id": "session456"
        }
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await recovery_handler.handle_recovery_action("wait_retry", context)
        
        mock_sleep.assert_called_once_with(2)
        assert result["success"] is True
        mock_chat_manager.process_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_clear_context_action(self, recovery_handler):
        """Test clear context action handling."""
        context = {"user_id": "user123"}
        
        result = await recovery_handler.handle_recovery_action("clear_context", context)
        
        assert result["success"] is True
        assert "context cleared" in result["message"]
        assert result["action"] == "clear_context"
    
    @pytest.mark.asyncio
    async def test_handle_refresh_page_action(self, recovery_handler):
        """Test refresh page action handling."""
        context = {}
        
        result = await recovery_handler.handle_recovery_action("refresh_page", context)
        
        assert result["success"] is True
        assert "refresh the page" in result["message"]
        assert result["action"] == "refresh_page"
    
    @pytest.mark.asyncio
    async def test_handle_contact_support_action(self, recovery_handler):
        """Test contact support action handling."""
        context = {"query": "test query", "error": "some error"}
        
        result = await recovery_handler.handle_recovery_action("contact_support", context)
        
        assert result["success"] is True
        assert "support_info" in result
        assert "email" in result["support_info"]
        assert result["support_info"]["error_context"] == context
    
    @pytest.mark.asyncio
    async def test_handle_check_connection_action(self, recovery_handler):
        """Test check connection action handling."""
        context = {}
        
        result = await recovery_handler.handle_recovery_action("check_connection", context)
        
        assert result["success"] is True
        assert "internet connection" in result["message"]
        assert "suggestion" in result
    
    @pytest.mark.asyncio
    async def test_handle_unknown_action(self, recovery_handler):
        """Test handling of unknown recovery action."""
        context = {}
        
        result = await recovery_handler.handle_recovery_action("unknown_action", context)
        
        assert result["success"] is False
        assert "Unknown recovery action" in result["message"]
    
    @pytest.mark.asyncio
    async def test_handle_recovery_action_exception(self, recovery_handler, mock_chat_manager):
        """Test recovery action handling with exception."""
        mock_chat_manager.process_message.side_effect = Exception("Unexpected error")
        context = {"query": "test query", "user_id": "user123", "session_id": "session456"}
        
        result = await recovery_handler.handle_recovery_action("retry_request", context)
        
        assert result["success"] is False
        assert "Retry failed" in result["message"]


class TestErrorIntegration:
    """Integration tests for error messaging system."""
    
    @pytest.fixture
    def error_generator(self):
        """Create error generator for integration tests."""
        return UserFriendlyErrorGenerator(enable_technical_details=True)
    
    @pytest.fixture
    def recovery_handler(self):
        """Create recovery handler for integration tests."""
        return ErrorRecoveryHandler()
    
    def test_complete_error_flow_tool_failure(self, error_generator):
        """Test complete error handling flow for tool failure."""
        # Create original error
        error = ToolExecutionError("Database connection failed", "CreateSupportTicket")
        context = {
            "query": "Create a support ticket for my billing issue",
            "user_id": "user123",
            "session_id": "session456"
        }
        
        # Generate user-friendly error
        user_error = error_generator.generate_user_friendly_error(error, context)
        
        # Verify error categorization and messaging
        assert user_error.category == ErrorCategory.TOOL_FAILURE
        assert user_error.severity == ErrorSeverity.WARNING
        assert "CreateSupportTicket" in user_error.message
        assert len(user_error.recovery_buttons) > 0
        
        # Create UI component
        ui_component = error_generator.create_error_ui_component(user_error)
        assert ui_component.component_type == "error_display"
        assert len(ui_component.actions) > 0
        
        # Create error state
        error_state = error_generator.create_error_state(error, context)
        assert error_state.error_type == "ToolExecutionError"
        assert len(error_state.recovery_actions) > 0
    
    def test_complete_error_flow_timeout(self, error_generator):
        """Test complete error handling flow for timeout."""
        # Create timeout error
        error = TimeoutError("Request processing timeout", "complex_query", 45.0)
        context = {
            "query": "Please analyze all my data and provide comprehensive insights with detailed charts and graphs",
            "user_id": "user456"
        }
        
        # Generate user-friendly error
        user_error = error_generator.generate_user_friendly_error(error, context)
        
        # Verify timeout-specific handling
        assert user_error.category == ErrorCategory.TIMEOUT
        assert "45.0 seconds" in user_error.message
        # Long query should be detected in suggested actions, not necessarily in main message
        assert any("simpler" in action.lower() for action in user_error.suggested_actions)
        assert user_error.estimated_fix_time == "1-2 minutes"
        
        # Verify recovery actions include appropriate options
        action_ids = [button["action_id"] for button in user_error.recovery_buttons]
        assert "wait_retry" in action_ids
        assert "simplify_query" in action_ids
    
    def test_error_severity_escalation(self, error_generator):
        """Test error severity escalation based on error type."""
        # Test different error types and their severities
        test_cases = [
            (ConfigurationError("Missing API key", "api_key"), ErrorSeverity.ERROR),
            (ToolExecutionError("Tool failed", "test_tool"), ErrorSeverity.WARNING),
            (RenderingError("Render failed", "content"), ErrorSeverity.INFO),
            (ValidationError("Invalid input", "field"), ErrorSeverity.ERROR)
        ]
        
        for error, expected_severity in test_cases:
            user_error = error_generator.generate_user_friendly_error(error)
            assert user_error.severity == expected_severity
    
    def test_recovery_action_consistency(self, error_generator):
        """Test consistency of recovery actions across error types."""
        # All errors should have at least one recovery action
        error_types = [
            ToolExecutionError("Tool failed", "test_tool"),
            TimeoutError("Timeout", "operation", 30.0),
            ResourceLimitError("Limit exceeded", "memory", 100.0, 80.0),
            ValidationError("Invalid", "field", "value"),
            ContextRetrievalError("Context failed", "user123")
        ]
        
        for error in error_types:
            user_error = error_generator.generate_user_friendly_error(error)
            
            # Should have recovery buttons
            assert len(user_error.recovery_buttons) > 0
            
            # Should have suggested actions
            assert len(user_error.suggested_actions) > 0
            
            # Should have help link
            assert user_error.help_link is not None
            
            # All recovery buttons should have required fields
            for button in user_error.recovery_buttons:
                assert "action_id" in button
                assert "button_text" in button
                assert "description" in button


if __name__ == "__main__":
    pytest.main([__file__, "-v"])