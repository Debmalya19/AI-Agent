"""
Tests for the comprehensive error handling and recovery system.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock

from intelligent_chat.error_handler import (
    ErrorHandler, RecoveryStrategy, ErrorSeverity, RecoveryAction, 
    ErrorContext, RecoveryResult
)
from intelligent_chat.models import ToolResult, ContextEntry, ChatResponse
from intelligent_chat.exceptions import (
    ToolExecutionError, ToolSelectionError, ContextRetrievalError,
    RenderingError, TimeoutError, ResourceLimitError
)


class TestErrorHandler:
    """Test cases for ErrorHandler class."""
    
    @pytest.fixture
    def mock_tool_selector(self):
        """Mock tool selector."""
        selector = Mock()
        selector.score_tools.return_value = [
            Mock(tool_name="fallback_tool_1", final_score=0.8),
            Mock(tool_name="fallback_tool_2", final_score=0.6)
        ]
        return selector
    
    @pytest.fixture
    def mock_available_tools(self):
        """Mock available tools."""
        return {
            "BTWebsiteSearch": Mock(),
            "ComprehensiveAnswerGenerator": Mock(),
            "ContextRetriever": Mock(),
            "fallback_tool_1": Mock(),
            "fallback_tool_2": Mock()
        }
    
    @pytest.fixture
    def error_handler(self, mock_tool_selector, mock_available_tools):
        """Create ErrorHandler instance for testing."""
        return ErrorHandler(
            tool_selector=mock_tool_selector,
            available_tools=mock_available_tools,
            max_retry_attempts=3,
            retry_delay=0.1,  # Short delay for tests
            enable_fallback_tools=True
        )
    
    def test_initialization(self, error_handler):
        """Test ErrorHandler initialization."""
        assert error_handler.max_retry_attempts == 3
        assert error_handler.retry_delay == 0.1
        assert error_handler.enable_fallback_tools is True
        assert len(error_handler._tool_fallbacks) > 0
        assert len(error_handler._error_severity_map) > 0
    
    def test_handle_tool_failure_timeout_error(self, error_handler):
        """Test handling tool failure with timeout error."""
        error = TimeoutError("Tool execution timed out", "test_tool", 30.0)
        query = "test query"
        from datetime import datetime
        context = [ContextEntry(
            content="test", 
            source="test", 
            relevance_score=0.8,
            timestamp=datetime.now(),
            context_type="conversation"
        )]
        execution_context = {"attempt": 1}
        
        result = error_handler.handle_tool_failure(
            "test_tool", error, query, context, execution_context
        )
        
        assert isinstance(result, RecoveryResult)
        assert result.strategy_used in [RecoveryStrategy.RETRY, RecoveryStrategy.FALLBACK_TOOL]
    
    def test_handle_tool_failure_execution_error(self, error_handler):
        """Test handling tool failure with execution error."""
        error = ToolExecutionError("Tool failed to execute", "test_tool")
        query = "test query"
        context = []
        execution_context = {}
        
        result = error_handler.handle_tool_failure(
            "test_tool", error, query, context, execution_context
        )
        
        assert isinstance(result, RecoveryResult)
        assert result.strategy_used in [RecoveryStrategy.RETRY, RecoveryStrategy.FALLBACK_TOOL]
    
    def test_handle_tool_failure_resource_limit_error(self, error_handler):
        """Test handling tool failure with resource limit error."""
        error = ResourceLimitError("Resource limit exceeded", "memory", 100.0, 80.0)
        query = "test query"
        context = []
        execution_context = {}
        
        result = error_handler.handle_tool_failure(
            "test_tool", error, query, context, execution_context
        )
        
        assert isinstance(result, RecoveryResult)
        assert result.strategy_used == RecoveryStrategy.GRACEFUL_DEGRADATION
        # For resource limit errors, the recovery action should include reduce_concurrency
        # but the actual execution returns a degraded response
        assert result.success is True
    
    def test_handle_context_failure_timeout(self, error_handler):
        """Test handling context retrieval failure with timeout."""
        error = TimeoutError("Context retrieval timed out", "context_retrieval", 10.0)
        user_id = "test_user"
        query = "test query"
        
        result = error_handler.handle_context_failure(error, user_id, query)
        
        assert isinstance(result, RecoveryResult)
        assert result.strategy_used == RecoveryStrategy.PARTIAL_RESULTS
        assert result.result_data["use_cached_context"] is True
    
    def test_handle_context_failure_general_error(self, error_handler):
        """Test handling context retrieval failure with general error."""
        error = ContextRetrievalError("Context retrieval failed", "test_user")
        user_id = "test_user"
        query = "test query"
        
        result = error_handler.handle_context_failure(error, user_id, query)
        
        assert isinstance(result, RecoveryResult)
        assert result.strategy_used == RecoveryStrategy.GRACEFUL_DEGRADATION
        assert result.result_data["no_context"] is True
    
    def test_handle_rendering_failure(self, error_handler):
        """Test handling rendering failure."""
        error = RenderingError("Failed to render content", "test content")
        content = "**Bold text** and `code`"
        content_type = "markdown"
        
        result = error_handler.handle_rendering_failure(content, error, content_type)
        
        assert isinstance(result, RecoveryResult)
        assert result.success is True
        assert result.strategy_used == RecoveryStrategy.GRACEFUL_DEGRADATION
        assert "plain_text_content" in result.result_data
        
        # Check that markdown was stripped
        plain_text = result.result_data["plain_text_content"]
        assert "**" not in plain_text
        assert "`" not in plain_text
    
    def test_get_fallback_tools_predefined(self, error_handler):
        """Test getting predefined fallback tools."""
        fallback_tools = error_handler.get_fallback_tools("BTWebsiteSearch", "test query")
        
        assert isinstance(fallback_tools, list)
        assert len(fallback_tools) > 0
        assert "web_search" in fallback_tools or "ComprehensiveAnswerGenerator" in fallback_tools
    
    def test_get_fallback_tools_with_selector(self, error_handler):
        """Test getting fallback tools with intelligent selection."""
        fallback_tools = error_handler.get_fallback_tools("unknown_tool", "test query")
        
        assert isinstance(fallback_tools, list)
        # Should include tools from intelligent selection
        error_handler.tool_selector.score_tools.assert_called_once()
    
    def test_get_fallback_tools_disabled(self, error_handler):
        """Test getting fallback tools when disabled."""
        error_handler.enable_fallback_tools = False
        fallback_tools = error_handler.get_fallback_tools("BTWebsiteSearch", "test query")
        
        assert fallback_tools == []
    
    def test_create_partial_result_with_successful_results(self, error_handler):
        """Test creating partial result with successful tool results."""
        successful_results = [
            ToolResult(
                tool_name="tool1",
                success=True,
                result="Result from tool 1",
                execution_time=1.0
            ),
            ToolResult(
                tool_name="tool2",
                success=True,
                result="Result from tool 2",
                execution_time=2.0
            )
        ]
        failed_tools = ["tool3", "tool4"]
        query = "test query"
        
        response = error_handler.create_partial_result(successful_results, failed_tools, query)
        
        assert isinstance(response, ChatResponse)
        assert response.content_type == "text"
        assert "Result from tool 1" in response.content
        assert "Result from tool 2" in response.content
        assert "tool3" in response.content  # Failed tools mentioned
        assert response.tools_used == ["tool1", "tool2"]
        assert response.execution_time == 3.0
        assert response.ui_hints["partial_results"] is True
        assert response.ui_hints["failed_tools"] == failed_tools
    
    def test_create_partial_result_no_successful_results(self, error_handler):
        """Test creating partial result with no successful results."""
        successful_results = []
        failed_tools = ["tool1", "tool2"]
        query = "test query"
        
        response = error_handler.create_partial_result(successful_results, failed_tools, query)
        
        assert isinstance(response, ChatResponse)
        assert "apologize" in response.content.lower()
        assert response.confidence_score == 0.1
        assert response.ui_hints["error_state"] is True
    
    def test_error_statistics_recording(self, error_handler):
        """Test error statistics recording."""
        # Simulate some errors
        error1 = ToolExecutionError("Error 1", "tool1")
        error2 = TimeoutError("Error 2", "tool2", 30.0)
        error3 = ToolExecutionError("Error 3", "tool1")
        
        context1 = ErrorContext(
            error_type="ToolExecutionError",
            component="tool_orchestrator",
            operation="execution",
            tool_name="tool1"
        )
        context2 = ErrorContext(
            error_type="TimeoutError",
            component="tool_orchestrator",
            operation="execution",
            tool_name="tool2"
        )
        
        error_handler._record_error(context1, error1)
        error_handler._record_error(context2, error2)
        error_handler._record_error(context1, error3)
        
        stats = error_handler.get_error_statistics()
        
        assert stats["total_errors"] == 3
        assert "tool_orchestrator" in stats["component_stats"]
        assert stats["component_stats"]["tool_orchestrator"]["total_errors"] == 3
        assert "ToolExecutionError" in stats["component_stats"]["tool_orchestrator"]["error_types"]
        assert stats["component_stats"]["tool_orchestrator"]["error_types"]["ToolExecutionError"] == 2
    
    def test_error_history_analysis(self, error_handler):
        """Test error history analysis."""
        # Simulate timeout errors
        for i in range(3):
            error = TimeoutError(f"Timeout {i}", "test_tool", 30.0)
            context = ErrorContext(
                error_type="TimeoutError",
                component="test_tool",
                operation="execution"
            )
            error_handler._record_error(context, error)
        
        history = error_handler._get_error_history("test_tool")
        
        assert history["total_errors"] == 3
        assert history["timeout_count"] == 3
        assert history["execution_failures"] == 0
    
    def test_recovery_strategy_determination_repeated_timeouts(self, error_handler):
        """Test recovery strategy determination for repeated timeouts."""
        # Simulate error history with multiple timeouts
        error_handler._error_stats["test_tool"] = {
            "total_errors": 3,
            "error_types": {"TimeoutError": 3},
            "recent_errors": [
                {"timestamp": time.time(), "error_type": "TimeoutError", "context": Mock()},
                {"timestamp": time.time(), "error_type": "TimeoutError", "context": Mock()},
                {"timestamp": time.time(), "error_type": "TimeoutError", "context": Mock()}
            ]
        }
        
        error = TimeoutError("Another timeout", "test_tool", 30.0)
        context = ErrorContext(
            error_type="TimeoutError",
            component="tool_orchestrator",
            operation="execution",
            tool_name="test_tool",
            query="test query"
        )
        
        recovery_action = error_handler._determine_recovery_strategy(error, context)
        
        assert recovery_action.strategy == RecoveryStrategy.FALLBACK_TOOL
        assert len(recovery_action.fallback_tools) > 0
    
    def test_recovery_strategy_determination_first_timeout(self, error_handler):
        """Test recovery strategy determination for first timeout."""
        error = TimeoutError("First timeout", "test_tool", 30.0)
        context = ErrorContext(
            error_type="TimeoutError",
            component="tool_orchestrator",
            operation="execution",
            tool_name="test_tool"
        )
        
        recovery_action = error_handler._determine_recovery_strategy(error, context)
        
        assert recovery_action.strategy == RecoveryStrategy.RETRY
        assert recovery_action.action_data["timeout_multiplier"] == 2.0
    
    def test_convert_to_plain_text(self, error_handler):
        """Test conversion to plain text."""
        content = "**Bold text** and *italic* and `code` and <b>HTML</b>"
        plain_text = error_handler._convert_to_plain_text(content)
        
        assert "**" not in plain_text
        assert "*" not in plain_text
        assert "`" not in plain_text
        assert "<b>" not in plain_text
        assert "Bold text" in plain_text
        assert "italic" in plain_text
        assert "code" in plain_text
        assert "HTML" in plain_text
    
    def test_execute_retry_recovery(self, error_handler):
        """Test retry recovery execution."""
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            description="Retry operation",
            action_data={"timeout_multiplier": 2.0}
        )
        
        result = error_handler._execute_retry_recovery(
            recovery_action, "test query", [], {}
        )
        
        assert result.success is True
        assert result.strategy_used == RecoveryStrategy.RETRY
        assert result.result_data["should_retry"] is True
        assert "retry_config" in result.result_data
    
    def test_execute_fallback_tool_recovery(self, error_handler):
        """Test fallback tool recovery execution."""
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.FALLBACK_TOOL,
            description="Use fallback tools",
            fallback_tools=["tool1", "tool2"]
        )
        
        result = error_handler._execute_fallback_tool_recovery(
            recovery_action, "test query", [], {}
        )
        
        assert result.success is True
        assert result.strategy_used == RecoveryStrategy.FALLBACK_TOOL
        assert result.result_data["fallback_tools"] == ["tool1", "tool2"]
    
    def test_execute_fallback_tool_recovery_no_tools(self, error_handler):
        """Test fallback tool recovery with no available tools."""
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.FALLBACK_TOOL,
            description="Use fallback tools",
            fallback_tools=[]
        )
        
        result = error_handler._execute_fallback_tool_recovery(
            recovery_action, "test query", [], {}
        )
        
        assert result.success is False
        assert result.strategy_used == RecoveryStrategy.FALLBACK_TOOL
        assert "No fallback tools available" in result.error_message
    
    def test_execute_partial_results_recovery(self, error_handler):
        """Test partial results recovery execution."""
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.PARTIAL_RESULTS,
            description="Use partial results"
        )
        
        successful_results = [Mock(), Mock()]
        execution_context = {"successful_results": successful_results}
        
        result = error_handler._execute_partial_results_recovery(
            recovery_action, execution_context
        )
        
        assert result.success is True
        assert result.strategy_used == RecoveryStrategy.PARTIAL_RESULTS
        assert result.partial_results == successful_results
    
    def test_execute_graceful_degradation_recovery(self, error_handler):
        """Test graceful degradation recovery execution."""
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
            description="Graceful degradation"
        )
        
        result = error_handler._execute_graceful_degradation_recovery(
            recovery_action, "test query"
        )
        
        assert result.success is True
        assert result.strategy_used == RecoveryStrategy.GRACEFUL_DEGRADATION
        assert "degraded_response" in result.result_data
        assert "test query" in result.result_data["degraded_response"]


class TestRecoveryIntegration:
    """Integration tests for error recovery scenarios."""
    
    @pytest.fixture
    def error_handler(self):
        """Create ErrorHandler for integration tests."""
        return ErrorHandler(
            max_retry_attempts=2,
            retry_delay=0.01,
            enable_fallback_tools=True
        )
    
    def test_tool_failure_recovery_flow(self, error_handler):
        """Test complete tool failure recovery flow."""
        # Simulate tool failure
        error = ToolExecutionError("Tool execution failed", "test_tool")
        query = "test query"
        context = []
        execution_context = {"attempt": 1}
        
        # Handle the failure
        result = error_handler.handle_tool_failure(
            "test_tool", error, query, context, execution_context
        )
        
        # Should get a recovery result
        assert isinstance(result, RecoveryResult)
        assert result.strategy_used in [RecoveryStrategy.RETRY, RecoveryStrategy.FALLBACK_TOOL]
        
        # Check error was recorded
        stats = error_handler.get_error_statistics()
        assert stats["total_errors"] > 0
    
    def test_multiple_error_pattern_detection(self, error_handler):
        """Test detection of error patterns across multiple failures."""
        # Simulate multiple timeout errors for the same tool
        for i in range(3):
            error = TimeoutError(f"Timeout {i}", "problematic_tool", 30.0)
            context = ErrorContext(
                error_type="TimeoutError",
                component="problematic_tool",
                operation="execution"
            )
            error_handler._record_error(context, error)
        
        # Next error should trigger fallback strategy
        error = TimeoutError("Another timeout", "problematic_tool", 30.0)
        context = ErrorContext(
            error_type="TimeoutError",
            component="tool_orchestrator",
            operation="execution",
            tool_name="problematic_tool",
            query="test query"
        )
        
        recovery_action = error_handler._determine_recovery_strategy(error, context)
        
        # Should recommend fallback due to repeated timeouts
        assert recovery_action.strategy == RecoveryStrategy.FALLBACK_TOOL
    
    def test_error_recovery_with_partial_success(self, error_handler):
        """Test error recovery when some tools succeed."""
        successful_results = [
            ToolResult(
                tool_name="successful_tool",
                success=True,
                result="Success result",
                execution_time=1.0
            )
        ]
        failed_tools = ["failed_tool"]
        query = "test query"
        
        # Create partial result
        response = error_handler.create_partial_result(
            successful_results, failed_tools, query
        )
        
        # Should create a meaningful response
        assert isinstance(response, ChatResponse)
        assert response.confidence_score > 0.1  # Better than complete failure
        assert response.confidence_score < 1.0   # But not perfect
        assert "Success result" in response.content
        assert "failed_tool" in response.content
        assert response.ui_hints["partial_results"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])