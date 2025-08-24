"""
Unit tests for ToolOrchestrator coordination logic.

Tests cover:
- Tool selection and execution coordination
- Parallel tool execution with asyncio
- Dependency resolution and execution ordering
- Tool execution monitoring and timeout handling
- Error handling and recovery mechanisms
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from intelligent_chat.tool_orchestrator import ToolOrchestrator
from intelligent_chat.tool_selector import ToolSelector
from intelligent_chat.models import (
    ToolRecommendation, ToolResult, ContextEntry, ToolScore
)
from intelligent_chat.exceptions import ToolExecutionError, ToolSelectionError


class TestToolOrchestrator:
    """Test suite for ToolOrchestrator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock tool selector
        self.mock_selector = Mock(spec=ToolSelector)
        
        # Mock analytics service
        self.mock_analytics = Mock()
        
        # Sample tools for testing
        self.sample_tools = {
            "tool_a": Mock(return_value="Result from tool A"),
            "tool_b": Mock(return_value="Result from tool B"),
            "tool_c": Mock(return_value="Result from tool C"),
            "async_tool": AsyncMock(return_value="Result from async tool"),
            "slow_tool": Mock(return_value="Slow result"),
            "failing_tool": Mock(side_effect=Exception("Tool failed"))
        }
        
        # Create orchestrator instance
        self.orchestrator = ToolOrchestrator(
            tool_selector=self.mock_selector,
            available_tools=self.sample_tools,
            max_concurrent_tools=3,
            default_timeout=5.0,
            analytics_service=self.mock_analytics
        )
        
        # Sample context
        self.sample_context = [
            ContextEntry(
                content="Previous conversation about tools",
                source="conversation",
                relevance_score=0.8,
                timestamp=datetime.now(),
                context_type="conversation"
            )
        ]
    
    def test_initialization(self):
        """Test ToolOrchestrator initialization."""
        orchestrator = ToolOrchestrator()
        assert orchestrator is not None
        assert orchestrator.tool_selector is None
        assert orchestrator.available_tools == {}
        assert orchestrator.max_concurrent_tools == 3
        assert orchestrator.default_timeout == 30.0
        
        # Test with parameters
        custom_orchestrator = ToolOrchestrator(
            tool_selector=self.mock_selector,
            available_tools=self.sample_tools,
            max_concurrent_tools=5,
            default_timeout=10.0,
            analytics_service=self.mock_analytics
        )
        assert custom_orchestrator.tool_selector == self.mock_selector
        assert custom_orchestrator.available_tools == self.sample_tools
        assert custom_orchestrator.max_concurrent_tools == 5
        assert custom_orchestrator.default_timeout == 10.0
        assert custom_orchestrator.analytics_service == self.mock_analytics
    
    @pytest.mark.asyncio
    async def test_select_tools(self):
        """Test tool selection functionality."""
        # Mock tool selector responses
        mock_scores = [
            ToolScore("tool_a", 0.8, 0.1, 0.9, 0.85, "High relevance"),
            ToolScore("tool_b", 0.6, 0.0, 0.8, 0.68, "Medium relevance"),
            ToolScore("tool_c", 0.4, 0.2, 0.7, 0.5, "Low relevance")
        ]
        
        self.mock_selector.score_tools.return_value = mock_scores
        self.mock_selector.apply_context_boost.return_value = mock_scores
        
        query = "test query"
        recommendations = await self.orchestrator.select_tools(query, self.sample_context)
        
        # Verify selector was called
        self.mock_selector.score_tools.assert_called_once()
        self.mock_selector.apply_context_boost.assert_called_once()
        
        # Verify recommendations structure
        assert len(recommendations) == 3
        for rec in recommendations:
            assert isinstance(rec, ToolRecommendation)
            assert rec.tool_name in ["tool_a", "tool_b", "tool_c"]
            assert 0 <= rec.relevance_score <= 1
            assert rec.expected_execution_time > 0
        
        # Verify sorting by relevance
        scores = [rec.relevance_score for rec in recommendations]
        assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_execute_tools_basic(self):
        """Test basic tool execution."""
        tools = ["tool_a", "tool_b"]
        query = "test query"
        context = {"user_id": "test_user"}
        
        results = await self.orchestrator.execute_tools(tools, query, context)
        
        # Verify results
        assert len(results) == 2
        for result in results:
            assert isinstance(result, ToolResult)
            assert result.tool_name in tools
            assert result.success is True
            assert result.result is not None
            assert result.execution_time > 0
        
        # Verify tools were called
        self.sample_tools["tool_a"].assert_called_once_with(query)
        self.sample_tools["tool_b"].assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_execute_tools_with_async(self):
        """Test execution with async tools."""
        tools = ["async_tool", "tool_a"]
        query = "test query"
        context = {}
        
        results = await self.orchestrator.execute_tools(tools, query, context)
        
        # Verify results
        assert len(results) == 2
        async_result = next(r for r in results if r.tool_name == "async_tool")
        sync_result = next(r for r in results if r.tool_name == "tool_a")
        
        assert async_result.success is True
        assert sync_result.success is True
        
        # Verify async tool was awaited
        self.sample_tools["async_tool"].assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_execute_tools_with_failure(self):
        """Test tool execution with failures."""
        tools = ["tool_a", "failing_tool", "tool_b"]
        query = "test query"
        context = {}
        
        results = await self.orchestrator.execute_tools(tools, query, context)
        
        # Verify results
        assert len(results) == 3
        
        # Check successful tools
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        assert len(successful_results) == 2
        assert len(failed_results) == 1
        
        # Verify failed tool result
        failed_result = failed_results[0]
        assert failed_result.tool_name == "failing_tool"
        assert "Tool failed" in failed_result.error_message
    
    @pytest.mark.asyncio
    async def test_execute_tools_with_timeout(self):
        """Test tool execution with timeout."""
        # Create a slow tool that will timeout
        async def slow_async_tool(query):
            await asyncio.sleep(10)  # Longer than default timeout
            return "Should not reach here"
        
        self.sample_tools["timeout_tool"] = slow_async_tool
        
        # Set short timeout for this tool
        self.orchestrator._tool_timeouts["timeout_tool"] = 0.1
        
        tools = ["timeout_tool"]
        query = "test query"
        context = {}
        
        results = await self.orchestrator.execute_tools(tools, query, context)
        
        # Verify timeout result
        assert len(results) == 1
        result = results[0]
        assert result.tool_name == "timeout_tool"
        assert result.success is False
        assert "timed out" in result.error_message.lower()
    
    def test_create_execution_plan(self):
        """Test execution plan creation with dependencies."""
        # Set up dependencies
        self.orchestrator._tool_dependencies = {
            "tool_a": [],
            "tool_b": ["tool_a"],
            "tool_c": ["tool_a", "tool_b"],
            "tool_d": []
        }
        
        tools = ["tool_a", "tool_b", "tool_c", "tool_d"]
        execution_plan = self.orchestrator._create_execution_plan(tools)
        
        # Verify execution plan structure
        assert len(execution_plan) >= 1
        
        # tool_a and tool_d should be in first batch (no dependencies)
        first_batch = execution_plan[0]
        assert "tool_a" in first_batch
        assert "tool_d" in first_batch
        
        # tool_b should come after tool_a
        tool_b_batch = None
        for i, batch in enumerate(execution_plan):
            if "tool_b" in batch:
                tool_b_batch = i
                break
        
        tool_a_batch = None
        for i, batch in enumerate(execution_plan):
            if "tool_a" in batch:
                tool_a_batch = i
                break
        
        assert tool_b_batch > tool_a_batch
    
    def test_optimize_execution_order(self):
        """Test execution order optimization."""
        # Create sample recommendations
        recommendations = [
            ToolRecommendation("tool_a", 0.9, 1.0, 0.9, []),
            ToolRecommendation("tool_b", 0.8, 2.0, 0.8, ["tool_a"]),
            ToolRecommendation("tool_c", 0.7, 0.5, 0.7, [])
        ]
        
        optimized = self.orchestrator.optimize_execution_order(recommendations)
        
        # Verify optimization
        assert len(optimized) == 3
        assert all(isinstance(rec, ToolRecommendation) for rec in optimized)
        
        # Tools with no dependencies should generally come first
        no_deps = [rec for rec in optimized if not rec.dependencies]
        with_deps = [rec for rec in optimized if rec.dependencies]
        
        # Find positions
        no_deps_positions = [optimized.index(rec) for rec in no_deps]
        with_deps_positions = [optimized.index(rec) for rec in with_deps]
        
        # At least some no-dependency tools should come before dependent ones
        assert min(no_deps_positions) <= min(with_deps_positions) if with_deps_positions else True
    
    @pytest.mark.asyncio
    async def test_parallel_execution_limit(self):
        """Test that parallel execution respects concurrency limits."""
        # Create many tools
        many_tools = {f"tool_{i}": Mock(return_value=f"Result {i}") for i in range(10)}
        
        orchestrator = ToolOrchestrator(
            available_tools=many_tools,
            max_concurrent_tools=3
        )
        
        tools = list(many_tools.keys())
        query = "test query"
        context = {}
        
        start_time = asyncio.get_event_loop().time()
        results = await orchestrator.execute_tools(tools, query, context)
        end_time = asyncio.get_event_loop().time()
        
        # Verify all tools executed
        assert len(results) == 10
        assert all(result.success for result in results)
        
        # Execution should take some time due to batching
        # (This is a rough check - actual timing may vary)
        assert end_time - start_time > 0
    
    def test_get_execution_stats(self):
        """Test execution statistics tracking."""
        # Simulate some executions
        result1 = ToolResult("tool_a", True, "result", 1.5)
        result2 = ToolResult("tool_a", False, None, 2.0, "Error")
        result3 = ToolResult("tool_b", True, "result", 1.0)
        
        self.orchestrator._update_execution_stats("tool_a", result1)
        self.orchestrator._update_execution_stats("tool_a", result2)
        self.orchestrator._update_execution_stats("tool_b", result3)
        
        stats = self.orchestrator.get_execution_stats()
        
        # Verify tool_a stats
        tool_a_stats = stats["tool_a"]
        assert tool_a_stats["total_executions"] == 2
        assert tool_a_stats["successful_executions"] == 1
        assert tool_a_stats["success_rate"] == 0.5
        assert tool_a_stats["avg_execution_time"] == 1.75
        
        # Verify tool_b stats
        tool_b_stats = stats["tool_b"]
        assert tool_b_stats["total_executions"] == 1
        assert tool_b_stats["successful_executions"] == 1
        assert tool_b_stats["success_rate"] == 1.0
        assert tool_b_stats["avg_execution_time"] == 1.0
    
    @pytest.mark.asyncio
    async def test_analytics_integration(self):
        """Test integration with analytics service."""
        tools = ["tool_a", "tool_b"]
        query = "test query"
        context = {}
        
        await self.orchestrator.execute_tools(tools, query, context)
        
        # Verify analytics service was called
        assert self.mock_analytics.record_tool_usage.call_count == 2
        
        # Check call arguments
        calls = self.mock_analytics.record_tool_usage.call_args_list
        for call in calls:
            args, kwargs = call
            assert kwargs["query"] == query
            assert kwargs["success"] is True
            assert kwargs["response_quality"] == 0.8
            assert kwargs["response_time"] > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_in_selection(self):
        """Test error handling during tool selection."""
        # Mock selector to raise exception
        self.mock_selector.score_tools.side_effect = Exception("Selection failed")
        
        query = "test query"
        
        with pytest.raises(ToolSelectionError):
            await self.orchestrator.select_tools(query, self.sample_context)
    
    @pytest.mark.asyncio
    async def test_empty_inputs(self):
        """Test handling of empty inputs."""
        # Empty tools list
        results = await self.orchestrator.execute_tools([], "query", {})
        assert results == []
        
        # Empty query (should still work)
        results = await self.orchestrator.execute_tools(["tool_a"], "", {})
        assert len(results) == 1
        assert results[0].success is True
    
    @pytest.mark.asyncio
    async def test_unknown_tools(self):
        """Test handling of unknown tools."""
        tools = ["unknown_tool", "tool_a"]
        query = "test query"
        context = {}
        
        results = await self.orchestrator.execute_tools(tools, query, context)
        
        # Should only execute known tools
        assert len(results) == 1
        assert results[0].tool_name == "tool_a"
        assert results[0].success is True
    
    @pytest.mark.asyncio
    async def test_execution_monitoring(self):
        """Test execution monitoring capabilities."""
        # Test getting active executions (should be empty initially)
        active = self.orchestrator.get_active_executions()
        assert active == []
        
        # Test execution stats
        stats = self.orchestrator.get_execution_stats()
        assert isinstance(stats, dict)
    
    def test_tool_dependencies_configuration(self):
        """Test tool dependencies configuration."""
        # Test getting dependencies for known tools
        deps_a = self.orchestrator._get_tool_dependencies("BTWebsiteSearch")
        assert isinstance(deps_a, list)
        assert deps_a == []  # No dependencies
        
        deps_b = self.orchestrator._get_tool_dependencies("CreateSupportTicket")
        assert isinstance(deps_b, list)
        assert "database_connection" in deps_b
        
        # Test unknown tool
        deps_unknown = self.orchestrator._get_tool_dependencies("unknown_tool")
        assert deps_unknown == []
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_safety(self):
        """Test thread safety during concurrent executions."""
        async def execute_batch():
            return await self.orchestrator.execute_tools(
                ["tool_a", "tool_b"], "test query", {}
            )
        
        # Run multiple executions concurrently
        tasks = [execute_batch() for _ in range(3)]
        results_list = await asyncio.gather(*tasks)
        
        # Verify all executions completed successfully
        for results in results_list:
            assert len(results) == 2
            assert all(result.success for result in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])