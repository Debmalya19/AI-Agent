"""
Unit tests for context-aware tool boosting functionality.

Tests cover:
- Advanced conversation context analysis
- Multi-dimensional context boosting
- Conversation theme identification
- Intent progression analysis
- Temporal pattern analysis
- Context continuity calculation
- Integration with memory layer and analytics
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
from collections import Counter

from intelligent_chat.tool_selector import ToolSelector
from intelligent_chat.models import ToolScore, ContextEntry


class TestContextAwareBoosting:
    """Test suite for context-aware tool boosting functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock analytics and memory services
        self.mock_analytics = Mock()
        self.mock_memory = Mock()
        
        # Create selector with mocked services
        self.selector = ToolSelector(
            analytics_service=self.mock_analytics,
            memory_manager=self.mock_memory
        )
        
        # Sample tool scores for testing
        self.sample_scores = [
            ToolScore("BTWebsiteSearch", 0.7, 0.0, 0.8, 0.73, "BT-specific tool"),
            ToolScore("BTSupportHours", 0.6, 0.0, 0.9, 0.69, "Support tool"),
            ToolScore("CreateSupportTicket", 0.5, 0.0, 0.7, 0.56, "Ticket creation"),
            ToolScore("web_search", 0.8, 0.0, 0.6, 0.74, "General search")
        ]
        
        # Sample context entries with various patterns
        base_time = datetime.now()
        self.rich_context = [
            ContextEntry(
                content="I need help with my BT mobile plan pricing",
                source="conversation",
                relevance_score=0.9,
                timestamp=base_time - timedelta(minutes=5),
                context_type="conversation",
                metadata={"tools_used": ["BTPlansInformation", "BTWebsiteSearch"], "success": True}
            ),
            ContextEntry(
                content="Can you check the current support hours?",
                source="conversation",
                relevance_score=0.8,
                timestamp=base_time - timedelta(minutes=3),
                context_type="conversation",
                metadata={"tools_used": ["BTSupportHours"], "success": True}
            ),
            ContextEntry(
                content="I'm having technical issues with my mobile service",
                source="conversation",
                relevance_score=0.7,
                timestamp=base_time - timedelta(minutes=1),
                context_type="conversation",
                metadata={"tools_used": ["CreateSupportTicket"], "success": False}
            )
        ]
    
    def test_analyze_conversation_context(self):
        """Test comprehensive conversation context analysis."""
        analysis = self.selector._analyze_conversation_context(self.rich_context)
        
        # Verify analysis structure
        assert isinstance(analysis, dict)
        required_keys = [
            "tool_usage_patterns", "keyword_frequency", "conversation_themes",
            "user_intent_progression", "temporal_patterns", "success_patterns",
            "context_continuity"
        ]
        for key in required_keys:
            assert key in analysis
        
        # Verify tool usage patterns
        tool_patterns = analysis["tool_usage_patterns"]
        assert isinstance(tool_patterns, Counter)
        assert tool_patterns["BTPlansInformation"] == 1
        assert tool_patterns["BTWebsiteSearch"] == 1
        assert tool_patterns["BTSupportHours"] == 1
        assert tool_patterns["CreateSupportTicket"] == 1
        
        # Verify keyword frequency
        keyword_freq = analysis["keyword_frequency"]
        assert isinstance(keyword_freq, Counter)
        assert "mobile" in keyword_freq
        assert "support" in keyword_freq
        
        # Verify conversation themes
        themes = analysis["conversation_themes"]
        assert isinstance(themes, list)
        assert "plans" in themes
        assert "support" in themes
        
        # Verify success patterns
        success_patterns = analysis["success_patterns"]
        assert isinstance(success_patterns, dict)
        assert "BTPlansInformation" in success_patterns
        assert success_patterns["BTPlansInformation"]["successes"] == 1
        assert success_patterns["BTPlansInformation"]["total"] == 1
        
        # Verify context continuity
        continuity = analysis["context_continuity"]
        assert isinstance(continuity, float)
        assert 0.0 <= continuity <= 1.0
    
    def test_identify_conversation_themes(self):
        """Test conversation theme identification."""
        themes = self.selector._identify_conversation_themes(self.rich_context)
        
        assert isinstance(themes, list)
        assert "plans" in themes  # From "mobile plan pricing"
        assert "support" in themes  # From "support hours" and "technical issues"
        assert "technical" in themes  # From "technical issues"
    
    def test_analyze_intent_progression(self):
        """Test user intent progression analysis."""
        sorted_context = sorted(self.rich_context, key=lambda x: x.timestamp)
        intents = self.selector._analyze_intent_progression(sorted_context)
        
        assert isinstance(intents, list)
        assert len(intents) == len(sorted_context)
        
        # Should identify different intent types
        assert "plan_inquiry" in intents  # From plan pricing question
        assert "support_seeking" in intents  # From support hours and technical issues
        
        # Verify specific intents for each entry
        assert intents[0] == "plan_inquiry"  # "BT mobile plan pricing"
        assert intents[1] == "support_seeking"  # "support hours"
        assert intents[2] == "support_seeking"  # "technical issues"
    
    def test_analyze_temporal_patterns(self):
        """Test temporal pattern analysis."""
        sorted_context = sorted(self.rich_context, key=lambda x: x.timestamp)
        patterns = self.selector._analyze_temporal_patterns(sorted_context)
        
        assert isinstance(patterns, dict)
        assert "avg_gap" in patterns
        assert "conversation_pace" in patterns
        assert "total_duration" in patterns
        
        # Verify pace classification
        assert patterns["conversation_pace"] in ["rapid", "normal", "slow"]
        
        # Verify timing calculations
        assert patterns["avg_gap"] > 0
        assert patterns["total_duration"] > 0
    
    def test_calculate_context_continuity(self):
        """Test context continuity calculation."""
        sorted_context = sorted(self.rich_context, key=lambda x: x.timestamp)
        continuity = self.selector._calculate_context_continuity(sorted_context)
        
        assert isinstance(continuity, float)
        assert 0.0 <= continuity <= 1.0
        
        # Test with empty context
        empty_continuity = self.selector._calculate_context_continuity([])
        assert empty_continuity == 0.0
        
        # Test with single entry
        single_continuity = self.selector._calculate_context_continuity([self.rich_context[0]])
        assert single_continuity == 0.0
    
    def test_calculate_advanced_context_boost(self):
        """Test advanced context boost calculation."""
        analysis = self.selector._analyze_conversation_context(self.rich_context)
        
        # Test boost for frequently used tool
        bt_plans_boost = self.selector._calculate_advanced_context_boost(
            "BTPlansInformation", analysis
        )
        assert isinstance(bt_plans_boost, float)
        assert 0.0 <= bt_plans_boost <= 0.5
        assert bt_plans_boost > 0  # Should get boost from usage
        
        # Test boost for tool with keyword relevance
        bt_website_boost = self.selector._calculate_advanced_context_boost(
            "BTWebsiteSearch", analysis
        )
        assert bt_website_boost > 0  # Should get boost from BT keywords
        
        # Test boost for unused tool
        unused_boost = self.selector._calculate_advanced_context_boost(
            "web_search", analysis
        )
        assert unused_boost >= 0  # May get small boost from keywords
    
    def test_is_theme_relevant_to_tool(self):
        """Test theme relevance to tool category mapping."""
        # Test support theme relevance
        assert self.selector._is_theme_relevant_to_tool("support", "support")
        assert self.selector._is_theme_relevant_to_tool("support", "bt_specific")
        assert not self.selector._is_theme_relevant_to_tool("support", "computation")
        
        # Test plans theme relevance
        assert self.selector._is_theme_relevant_to_tool("plans", "plans")
        assert self.selector._is_theme_relevant_to_tool("plans", "bt_specific")
        
        # Test information theme relevance
        assert self.selector._is_theme_relevant_to_tool("information", "information_retrieval")
        assert self.selector._is_theme_relevant_to_tool("information", "orchestration")
    
    def test_generate_boost_reasoning(self):
        """Test boost reasoning generation."""
        analysis = self.selector._analyze_conversation_context(self.rich_context)
        
        # Test reasoning for tool with usage
        reasoning = self.selector._generate_boost_reasoning(
            "BTPlansInformation", 0.15, analysis
        )
        assert isinstance(reasoning, str)
        assert "recently used" in reasoning.lower()
        assert "0.15" in reasoning
        
        # Test reasoning for tool without boost
        no_boost_reasoning = self.selector._generate_boost_reasoning(
            "unknown_tool", 0.0, analysis
        )
        assert no_boost_reasoning == ""
    
    def test_apply_context_boost_integration(self):
        """Test full context boost application."""
        boosted_scores = self.selector.apply_context_boost(
            self.sample_scores, self.rich_context
        )
        
        # Verify structure
        assert len(boosted_scores) == len(self.sample_scores)
        assert all(isinstance(score, ToolScore) for score in boosted_scores)
        
        # Verify boost application
        for score in boosted_scores:
            original_score = next(s for s in self.sample_scores if s.tool_name == score.tool_name)
            
            # Context boost should be applied
            assert score.context_boost >= 0
            
            # Final score should be updated
            expected_final = min(original_score.final_score + score.context_boost, 1.0)
            assert abs(score.final_score - expected_final) < 0.001
            
            # Reasoning should be enhanced
            if score.context_boost > 0:
                assert "Context boost" in score.reasoning
        
        # Verify sorting
        final_scores = [s.final_score for s in boosted_scores]
        assert final_scores == sorted(final_scores, reverse=True)
    
    def test_get_enhanced_context_for_user(self):
        """Test enhanced context retrieval with memory integration."""
        # Mock memory manager response
        mock_memory_context = [
            {
                "content": "Previous conversation about BT plans",
                "relevance_score": 0.8,
                "timestamp": datetime.now() - timedelta(hours=1),
                "metadata": {"tools_used": ["BTPlansInformation"]}
            }
        ]
        self.mock_memory.get_relevant_context.return_value = mock_memory_context
        
        # Mock analytics response
        mock_usage_stats = {
            "tools": {
                "BTWebsiteSearch": {"usage_count": 5, "success_rate": 0.8},
                "BTSupportHours": {"usage_count": 2, "success_rate": 0.9}
            }
        }
        self.mock_analytics.get_usage_statistics.return_value = mock_usage_stats
        
        # Get enhanced context
        context = self.selector.get_enhanced_context_for_user(
            user_id="test_user",
            query="BT mobile plans",
            limit=5
        )
        
        # Verify context structure
        assert isinstance(context, list)
        assert len(context) > 0
        assert all(isinstance(entry, ContextEntry) for entry in context)
        
        # Verify memory integration
        memory_entries = [e for e in context if e.source == "memory_layer"]
        assert len(memory_entries) > 0
        
        # Verify analytics integration
        analytics_entries = [e for e in context if e.source == "analytics"]
        assert len(analytics_entries) > 0
        
        # Verify services were called
        self.mock_memory.get_relevant_context.assert_called_once()
        self.mock_analytics.get_usage_statistics.assert_called_once()
    
    def test_learn_from_tool_usage(self):
        """Test learning from tool usage patterns."""
        user_id = "test_user"
        query = "Help with BT mobile plans"
        selected_tools = ["BTWebsiteSearch", "BTPlansInformation"]
        tool_results = [
            {"success": True, "quality_score": 0.9, "execution_time": 1.5},
            {"success": True, "quality_score": 0.8, "execution_time": 2.0}
        ]
        
        # Call learning method
        self.selector.learn_from_tool_usage(
            user_id=user_id,
            query=query,
            selected_tools=selected_tools,
            tool_results=tool_results
        )
        
        # Verify analytics service was called
        assert self.mock_analytics.record_tool_usage.call_count == 2
        
        # Verify memory manager was called
        self.mock_memory.store_interaction.assert_called_once()
        
        # Verify call arguments
        analytics_calls = self.mock_analytics.record_tool_usage.call_args_list
        for i, call in enumerate(analytics_calls):
            args, kwargs = call
            assert kwargs["tool_name"] == selected_tools[i]
            assert kwargs["query"] == query
            assert kwargs["success"] == tool_results[i]["success"]
    
    def test_context_boost_with_empty_context(self):
        """Test context boost with empty context."""
        boosted_scores = self.selector.apply_context_boost(self.sample_scores, [])
        
        # Should return original scores unchanged
        assert len(boosted_scores) == len(self.sample_scores)
        for i, score in enumerate(boosted_scores):
            original = self.sample_scores[i]
            assert score.tool_name == original.tool_name
            assert score.context_boost == 0.0
            assert score.final_score == original.final_score
    
    def test_context_boost_performance(self):
        """Test context boost performance with large context."""
        # Create large context
        large_context = []
        base_time = datetime.now()
        
        for i in range(100):
            entry = ContextEntry(
                content=f"Context entry {i} about BT mobile plans and support",
                source="conversation",
                relevance_score=0.5,
                timestamp=base_time - timedelta(minutes=i),
                context_type="conversation",
                metadata={"tools_used": ["BTWebsiteSearch"], "success": True}
            )
            large_context.append(entry)
        
        # Should handle large context efficiently
        import time
        start_time = time.time()
        boosted_scores = self.selector.apply_context_boost(self.sample_scores, large_context)
        end_time = time.time()
        
        # Verify results
        assert len(boosted_scores) == len(self.sample_scores)
        assert all(score.context_boost >= 0 for score in boosted_scores)
        
        # Should complete in reasonable time (less than 1 second)
        assert end_time - start_time < 1.0
    
    def test_error_handling_in_context_analysis(self):
        """Test error handling in context analysis methods."""
        # Test with malformed context entries
        malformed_context = [
            ContextEntry(
                content="",  # Empty content
                source="test",
                relevance_score=0.5,
                timestamp=datetime.now(),
                context_type="test",
                metadata={}
            )
        ]
        
        # Should handle gracefully
        analysis = self.selector._analyze_conversation_context(malformed_context)
        assert isinstance(analysis, dict)
        
        # Test boost calculation with malformed analysis
        malformed_analysis = {"invalid": "data"}
        boost = self.selector._calculate_advanced_context_boost(
            "BTWebsiteSearch", malformed_analysis
        )
        assert isinstance(boost, float)
        assert boost >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])