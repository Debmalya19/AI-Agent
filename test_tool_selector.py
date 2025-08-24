"""
Unit tests for ToolSelector algorithm.

Tests cover:
- Basic tool scoring functionality
- Keyword-based relevance scoring
- Historical performance integration
- Context-aware tool boosting
- Analytics service integration
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from intelligent_chat.tool_selector import ToolSelector
from intelligent_chat.models import ToolScore, ContextEntry
from intelligent_chat.exceptions import ToolSelectionError


class TestToolSelector:
    """Test suite for ToolSelector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.selector = ToolSelector()
        self.mock_analytics = Mock()
        self.selector_with_analytics = ToolSelector(analytics_service=self.mock_analytics)
        
        # Sample tools for testing
        self.sample_tools = [
            "BTWebsiteSearch",
            "BTSupportHours", 
            "BTPlansInformation",
            "CreateSupportTicket",
            "ComprehensiveAnswerGenerator",
            "web_search",
            "database_query"
        ]
    
    def test_initialization(self):
        """Test ToolSelector initialization."""
        selector = ToolSelector()
        assert selector is not None
        assert selector.tool_metadata == {}
        assert selector.analytics_service is None
        assert len(selector._default_tool_info) > 0
        
        # Test with analytics service
        mock_analytics = Mock()
        selector_with_analytics = ToolSelector(analytics_service=mock_analytics)
        assert selector_with_analytics.analytics_service == mock_analytics
    
    def test_score_tools_basic(self):
        """Test basic tool scoring functionality."""
        query = "search for BT mobile plans"
        scores = self.selector.score_tools(query, self.sample_tools)
        
        # Verify all tools are scored
        assert len(scores) == len(self.sample_tools)
        
        # Verify score structure
        for score in scores:
            assert isinstance(score, ToolScore)
            assert 0 <= score.final_score <= 1
            assert 0 <= score.base_score <= 1
            assert 0 <= score.performance_score <= 1
            assert score.tool_name in self.sample_tools
            assert isinstance(score.reasoning, str)
        
        # Verify scores are sorted by final_score
        final_scores = [s.final_score for s in scores]
        assert final_scores == sorted(final_scores, reverse=True)
    
    def test_keyword_relevance_scoring(self):
        """Test keyword-based relevance scoring."""
        # Test BT-specific query
        bt_query = "BT mobile plans pricing"
        bt_scores = self.selector.score_tools(bt_query, self.sample_tools)
        
        # BT-specific tools should score higher
        bt_tools = ["BTWebsiteSearch", "BTPlansInformation"]
        bt_tool_scores = [s for s in bt_scores if s.tool_name in bt_tools]
        other_tool_scores = [s for s in bt_scores if s.tool_name not in bt_tools]
        
        # At least one BT tool should score higher than average
        max_bt_score = max(s.final_score for s in bt_tool_scores)
        avg_other_score = sum(s.final_score for s in other_tool_scores) / len(other_tool_scores)
        assert max_bt_score > avg_other_score
        
        # Test support query
        support_query = "I need help with customer support hours"
        support_scores = self.selector.score_tools(support_query, self.sample_tools)
        
        # Support tools should score higher
        support_tool = next(s for s in support_scores if s.tool_name == "BTSupportHours")
        assert support_tool.final_score > 0.5
    
    def test_performance_score_integration(self):
        """Test integration with historical performance data."""
        # Mock analytics service to return performance data
        self.mock_analytics.get_tool_success_rate.return_value = 0.9
        
        query = "test query"
        scores = self.selector_with_analytics.score_tools(query, ["BTWebsiteSearch"])
        
        # Verify analytics service was called
        self.mock_analytics.get_tool_success_rate.assert_called_with("BTWebsiteSearch", days=30)
        
        # Verify performance score is used
        assert len(scores) == 1
        assert scores[0].performance_score == 0.9
    
    def test_context_boost_application(self):
        """Test context-aware score boosting."""
        # Create sample context entries
        context = [
            ContextEntry(
                content="I was asking about BT mobile plans earlier",
                source="conversation",
                relevance_score=0.8,
                timestamp=datetime.now(),
                context_type="conversation",
                metadata={"tools_used": ["BTPlansInformation"]}
            ),
            ContextEntry(
                content="User mentioned pricing and upgrades",
                source="conversation", 
                relevance_score=0.7,
                timestamp=datetime.now(),
                context_type="conversation",
                metadata={}
            )
        ]
        
        # Get initial scores
        query = "tell me more about plans"
        initial_scores = self.selector.score_tools(query, self.sample_tools)
        
        # Apply context boost
        boosted_scores = self.selector.apply_context_boost(initial_scores, context)
        
        # Verify boost was applied
        assert len(boosted_scores) == len(initial_scores)
        
        # Find BTPlansInformation tool scores
        initial_bt_plans = next(s for s in initial_scores if s.tool_name == "BTPlansInformation")
        boosted_bt_plans = next(s for s in boosted_scores if s.tool_name == "BTPlansInformation")
        
        # Should have received context boost
        assert boosted_bt_plans.context_boost > 0
        assert boosted_bt_plans.final_score >= initial_bt_plans.final_score
    
    def test_filter_by_threshold(self):
        """Test filtering tools by score threshold."""
        query = "search for information"
        scores = self.selector.score_tools(query, self.sample_tools)
        
        # Test different thresholds
        high_threshold_tools = self.selector.filter_by_threshold(scores, threshold=0.8)
        medium_threshold_tools = self.selector.filter_by_threshold(scores, threshold=0.5)
        low_threshold_tools = self.selector.filter_by_threshold(scores, threshold=0.2)
        
        # Higher threshold should return fewer tools
        assert len(high_threshold_tools) <= len(medium_threshold_tools)
        assert len(medium_threshold_tools) <= len(low_threshold_tools)
        
        # All returned tools should meet threshold
        for tool_name in high_threshold_tools:
            tool_score = next(s for s in scores if s.tool_name == tool_name)
            assert tool_score.final_score >= 0.8
    
    def test_performance_metrics_update(self):
        """Test updating performance metrics."""
        tool_name = "BTWebsiteSearch"
        query = "test query"
        
        # Test local cache update
        self.selector.update_performance_metrics(
            tool_name=tool_name,
            query=query,
            success=True,
            execution_time=1.5,
            response_quality=0.9
        )
        
        # Verify cache was updated
        assert tool_name in self.selector._performance_cache
        metrics = self.selector._performance_cache[tool_name]
        assert metrics["total_executions"] == 1
        assert metrics["successful_executions"] == 1
        assert metrics["success_rate"] == 1.0
        assert metrics["avg_time"] == 1.5
        
        # Test with analytics service
        self.selector_with_analytics.update_performance_metrics(
            tool_name=tool_name,
            query=query,
            success=True,
            execution_time=2.0,
            response_quality=0.8
        )
        
        # Verify analytics service was called
        self.mock_analytics.record_tool_usage.assert_called_with(
            tool_name=tool_name,
            query=query,
            success=True,
            response_quality=0.8,
            response_time=2.0
        )
    
    def test_get_tool_recommendations(self):
        """Test getting tool recommendations from analytics service."""
        # Mock analytics service recommendations
        mock_recommendation = Mock()
        mock_recommendation.tool_name = "BTWebsiteSearch"
        mock_recommendation.confidence_score = 0.9
        mock_recommendation.expected_performance = 0.8
        mock_recommendation.reason = "High relevance for BT queries"
        
        self.mock_analytics.get_tool_recommendations.return_value = [mock_recommendation]
        # Also mock the success rate call that happens during scoring
        self.mock_analytics.get_tool_success_rate.return_value = 0.8
        
        query = "BT mobile plans"
        recommendations = self.selector_with_analytics.get_tool_recommendations(
            query=query,
            available_tools=self.sample_tools,
            max_recommendations=3
        )
        
        # Verify analytics service was called
        self.mock_analytics.get_tool_recommendations.assert_called_with(
            query=query,
            available_tools=self.sample_tools,
            max_recommendations=3
        )
        
        # Verify recommendations structure
        assert len(recommendations) == 1
        rec = recommendations[0]
        assert isinstance(rec, ToolScore)
        assert rec.tool_name == "BTWebsiteSearch"
        assert rec.final_score == 0.9
        assert rec.performance_score == 0.8
        assert rec.reasoning == "High relevance for BT queries"
    
    def test_error_handling(self):
        """Test error handling in tool scoring."""
        # Test with empty inputs
        empty_scores = self.selector.score_tools("", [])
        assert empty_scores == []
        
        empty_query_scores = self.selector.score_tools("", self.sample_tools)
        assert empty_query_scores == []
        
        empty_tools_scores = self.selector.score_tools("test query", [])
        assert empty_tools_scores == []
        
        # Test with analytics service error
        self.mock_analytics.get_tool_success_rate.side_effect = Exception("Analytics error")
        
        # Should fallback gracefully
        scores = self.selector_with_analytics.score_tools("test query", ["BTWebsiteSearch"])
        assert len(scores) == 1
        assert scores[0].performance_score == 0.7  # Default fallback
    
    def test_query_analysis(self):
        """Test query analysis and tokenization."""
        # Test tokenization
        tokens = self.selector._tokenize_query("Search for BT mobile plans!")
        expected_tokens = ["search", "for", "bt", "mobile", "plans"]
        assert tokens == expected_tokens
        
        # Test keyword extraction
        keywords = self.selector._extract_keywords("I need help with BT customer support")
        assert "help" in keywords
        assert "customer" in keywords
        assert "support" in keywords
        assert "the" not in keywords  # Stop word should be filtered
        assert "i" not in keywords    # Short word should be filtered
    
    def test_tool_info_retrieval(self):
        """Test tool information retrieval."""
        # Test known tool
        bt_info = self.selector._get_tool_info("BTWebsiteSearch")
        assert "bt" in bt_info["keywords"]
        assert bt_info["category"] == "bt_specific"
        assert bt_info["base_score"] == 0.9
        
        # Test unknown tool
        unknown_info = self.selector._get_tool_info("UnknownTool")
        assert unknown_info["keywords"] == []
        assert unknown_info["category"] == "unknown"
        assert unknown_info["base_score"] == 0.5
    
    def test_context_analysis(self):
        """Test context analysis for tool boosting."""
        context = [
            ContextEntry(
                content="User asked about BT plans",
                source="conversation",
                relevance_score=0.8,
                timestamp=datetime.now(),
                context_type="conversation",
                metadata={"tools_used": ["BTPlansInformation", "BTWebsiteSearch"]}
            )
        ]
        
        # Extract tools from context
        context_tools = self.selector._extract_tools_from_context(context)
        assert context_tools["BTPlansInformation"] == 1
        assert context_tools["BTWebsiteSearch"] == 1
        
        # Extract keywords from context
        context_keywords = self.selector._extract_context_keywords(context)
        assert "plans" in context_keywords
        assert "user" in context_keywords
    
    def test_reasoning_generation(self):
        """Test reasoning generation for tool scores."""
        reasoning = self.selector._generate_reasoning("BTWebsiteSearch", 0.8, 0.9)
        
        assert "BTWebsiteSearch" in reasoning
        assert "High relevance" in reasoning or "relevance" in reasoning
        assert "excellent" in reasoning or "performance" in reasoning
    
    @pytest.mark.asyncio
    async def test_concurrent_scoring(self):
        """Test tool scoring under concurrent access."""
        import asyncio
        
        async def score_tools_async():
            return self.selector.score_tools("test query", self.sample_tools)
        
        # Run multiple scoring operations concurrently
        tasks = [score_tools_async() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All results should be valid
        for scores in results:
            assert len(scores) == len(self.sample_tools)
            assert all(isinstance(s, ToolScore) for s in scores)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])