"""
Unit tests for Tool Usage Analytics system.

Tests cover all major functionality including:
- Tool usage recording
- Performance analysis
- Tool recommendations
- Query analysis
- Optimization algorithms
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# Import the classes we're testing
from tool_usage_analytics import (
    ToolUsageAnalytics,
    ToolPerformanceReport,
    QueryAnalysis
)
from memory_models import ToolUsageMetrics, ToolRecommendationDTO


class TestToolUsageAnalytics(unittest.TestCase):
    """Test suite for ToolUsageAnalytics class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_session = Mock()
        self.analytics = ToolUsageAnalytics(db_session=self.mock_db_session)
        
        # Sample test data
        self.sample_tool_name = "BTWebsiteSearch"
        self.sample_query = "What are BT mobile plans?"
        self.sample_tools = [
            "BTWebsiteSearch",
            "BTPlansInformation", 
            "ComprehensiveAnswerGenerator",
            "CreateSupportTicket"
        ]
    
    def test_init(self):
        """Test analytics system initialization"""
        self.assertIsNotNone(self.analytics.db_session)
        self.assertEqual(self.analytics._cache_ttl, 300)
        self.assertIsInstance(self.analytics.tool_categories, dict)
        self.assertIn('search', self.analytics.tool_categories)
        self.assertIn('bt_specific', self.analytics.tool_categories)
    
    def test_generate_query_hash(self):
        """Test query hash generation for similar queries"""
        query1 = "What are BT mobile plans?"
        query2 = "what are bt mobile plans"
        query3 = "BT mobile plans what are"
        
        hash1 = self.analytics._generate_query_hash(query1)
        hash2 = self.analytics._generate_query_hash(query2)
        hash3 = self.analytics._generate_query_hash(query3)
        
        # Similar queries should have same hash
        self.assertEqual(hash1, hash2)
        self.assertEqual(hash1, hash3)
        
        # Different query should have different hash
        different_query = "How to contact BT support?"
        different_hash = self.analytics._generate_query_hash(different_query)
        self.assertNotEqual(hash1, different_hash)
    
    def test_analyze_query_type(self):
        """Test query type analysis"""
        test_cases = [
            ("What are BT support hours?", "support"),
            ("How much do BT plans cost?", "plans"),
            ("I have a technical problem", "technical"),
            ("My billing is wrong", "billing"),
            ("Hello there", "general")
        ]
        
        for query, expected_type in test_cases:
            result = self.analytics._analyze_query_type(query)
            self.assertEqual(result, expected_type, f"Failed for query: {query}")
    
    def test_analyze_query(self):
        """Test comprehensive query analysis"""
        query = "What are the current BT mobile plans and pricing?"
        
        analysis = self.analytics._analyze_query(query)
        
        self.assertIsInstance(analysis, QueryAnalysis)
        self.assertEqual(analysis.query_type, "plans")
        self.assertGreater(analysis.complexity_score, 0)
        self.assertLessEqual(analysis.complexity_score, 1.0)
        self.assertIn("current", analysis.keywords)
        self.assertIn("mobile", analysis.keywords)
        self.assertGreater(analysis.confidence, 0)
    
    def test_record_tool_usage_new_metric(self):
        """Test recording tool usage for new metric"""
        # Mock database query to return None (no existing metric)
        self.mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Test recording
        result = self.analytics.record_tool_usage(
            tool_name=self.sample_tool_name,
            query=self.sample_query,
            success=True,
            response_quality=0.8,
            response_time=2.5
        )
        
        self.assertTrue(result)
        self.mock_db_session.add.assert_called_once()
        self.mock_db_session.commit.assert_called_once()
    
    def test_record_tool_usage_existing_metric(self):
        """Test recording tool usage for existing metric"""
        # Mock existing metric
        existing_metric = Mock(spec=ToolUsageMetrics)
        existing_metric.usage_count = 5
        existing_metric.success_rate = 0.6
        existing_metric.response_quality_score = 0.7
        existing_metric.average_response_time = 3.0
        
        self.mock_db_session.query.return_value.filter.return_value.first.return_value = existing_metric
        
        # Test recording
        result = self.analytics.record_tool_usage(
            tool_name=self.sample_tool_name,
            query=self.sample_query,
            success=True,
            response_quality=0.9,
            response_time=2.0
        )
        
        self.assertTrue(result)
        self.assertEqual(existing_metric.usage_count, 6)
        self.assertGreater(existing_metric.success_rate, 0.6)  # Should increase
        self.assertGreater(existing_metric.response_quality_score, 0.7)  # Should increase
        self.mock_db_session.commit.assert_called_once()
    
    def test_record_tool_usage_error_handling(self):
        """Test error handling in tool usage recording"""
        # Mock database error
        self.mock_db_session.commit.side_effect = Exception("Database error")
        
        result = self.analytics.record_tool_usage(
            tool_name=self.sample_tool_name,
            query=self.sample_query,
            success=True,
            response_quality=0.8
        )
        
        self.assertFalse(result)
        self.mock_db_session.rollback.assert_called_once()
    
    def test_get_tool_recommendations(self):
        """Test tool recommendation generation"""
        # Mock performance data
        with patch.object(self.analytics, '_get_tool_performance') as mock_perf:
            mock_perf.return_value = {
                'success_rate': 0.8,
                'quality_score': 0.75,
                'response_time': 2.0,
                'usage_count': 50
            }
            
            recommendations = self.analytics.get_tool_recommendations(
                query="What are BT mobile plans?",
                available_tools=self.sample_tools
            )
            
            self.assertIsInstance(recommendations, list)
            self.assertGreater(len(recommendations), 0)
            
            # Check first recommendation
            first_rec = recommendations[0]
            self.assertIsInstance(first_rec, ToolRecommendationDTO)
            self.assertIn(first_rec.tool_name, self.sample_tools)
            self.assertGreater(first_rec.confidence_score, 0)
            self.assertIsInstance(first_rec.reason, str)
            self.assertGreater(first_rec.expected_performance, 0)
    
    def test_get_tool_recommendations_empty_tools(self):
        """Test tool recommendations with empty tool list"""
        recommendations = self.analytics.get_tool_recommendations(
            query="test query",
            available_tools=[]
        )
        
        self.assertEqual(len(recommendations), 0)
    
    def test_optimize_tool_selection(self):
        """Test tool selection optimization"""
        with patch.object(self.analytics, 'get_tool_recommendations') as mock_recs:
            # Mock recommendations
            mock_recs.return_value = [
                ToolRecommendationDTO("BTPlansInformation", 0.9, "High confidence", 0.8),
                ToolRecommendationDTO("BTWebsiteSearch", 0.7, "Good match", 0.7)
            ]
            
            optimized_tools = self.analytics.optimize_tool_selection(
                query="BT mobile plans",
                available_tools=self.sample_tools
            )
            
            self.assertIsInstance(optimized_tools, list)
            self.assertEqual(len(optimized_tools), len(self.sample_tools))
            
            # First tool should be highest confidence
            self.assertEqual(optimized_tools[0], "BTPlansInformation")
            self.assertEqual(optimized_tools[1], "BTWebsiteSearch")
    
    def test_optimize_tool_selection_fallback(self):
        """Test tool selection optimization fallback"""
        with patch.object(self.analytics, 'get_tool_recommendations') as mock_recs:
            # Mock empty recommendations
            mock_recs.return_value = []
            
            optimized_tools = self.analytics.optimize_tool_selection(
                query="BT support hours",
                available_tools=self.sample_tools
            )
            
            self.assertIsInstance(optimized_tools, list)
            self.assertEqual(len(optimized_tools), len(self.sample_tools))
            # Should use default ordering
    
    def test_get_tool_success_rate(self):
        """Test tool success rate calculation"""
        # Mock metrics
        mock_metrics = [
            Mock(success_rate=0.8, usage_count=10),
            Mock(success_rate=0.9, usage_count=20),
            Mock(success_rate=0.7, usage_count=5)
        ]
        
        self.mock_db_session.query.return_value.filter.return_value.all.return_value = mock_metrics
        
        success_rate = self.analytics.get_tool_success_rate("TestTool")
        
        # Should be weighted average: (0.8*10 + 0.9*20 + 0.7*5) / (10+20+5) = 0.84
        expected_rate = (0.8*10 + 0.9*20 + 0.7*5) / 35
        self.assertAlmostEqual(success_rate, expected_rate, places=2)
    
    def test_get_tool_success_rate_no_data(self):
        """Test tool success rate with no data"""
        self.mock_db_session.query.return_value.filter.return_value.all.return_value = []
        
        success_rate = self.analytics.get_tool_success_rate("NonExistentTool")
        
        self.assertEqual(success_rate, 0.5)  # Default neutral rate
    
    def test_get_usage_statistics(self):
        """Test usage statistics generation"""
        # Mock metrics
        mock_metrics = [
            Mock(
                tool_name="Tool1",
                usage_count=10,
                success_rate=0.8,
                response_quality_score=0.75,
                average_response_time=2.0
            ),
            Mock(
                tool_name="Tool2", 
                usage_count=5,
                success_rate=0.9,
                response_quality_score=0.85,
                average_response_time=1.5
            )
        ]
        
        self.mock_db_session.query.return_value.filter.return_value.all.return_value = mock_metrics
        
        stats = self.analytics.get_usage_statistics()
        
        self.assertIsInstance(stats, dict)
        self.assertEqual(stats["total_usage"], 15)
        self.assertIn("tools", stats)
        self.assertIn("Tool1", stats["tools"])
        self.assertIn("Tool2", stats["tools"])
        self.assertEqual(stats["most_used"], "Tool1")
    
    def test_analyze_tool_performance(self):
        """Test tool performance analysis"""
        # Mock metrics
        mock_metrics = [
            Mock(
                tool_name="Tool1",
                usage_count=10,
                success_rate=0.8,
                response_quality_score=0.75,
                average_response_time=2.0
            ),
            Mock(
                tool_name="Tool1",
                usage_count=5,
                success_rate=0.9,
                response_quality_score=0.85,
                average_response_time=1.5
            )
        ]
        
        self.mock_db_session.query.return_value.filter.return_value.all.return_value = mock_metrics
        
        reports = self.analytics.analyze_tool_performance()
        
        self.assertIsInstance(reports, list)
        self.assertGreater(len(reports), 0)
        
        report = reports[0]
        self.assertIsInstance(report, ToolPerformanceReport)
        self.assertEqual(report.tool_name, "Tool1")
        self.assertEqual(report.total_usage, 15)
        self.assertIsInstance(report.recommendations, list)
    
    def test_calculate_confidence_score(self):
        """Test confidence score calculation"""
        query_analysis = QueryAnalysis(
            query_type="plans",
            complexity_score=0.5,
            keywords=["bt", "mobile", "plans"],
            intent="information_seeking",
            confidence=0.8
        )
        
        performance = {
            'success_rate': 0.9,
            'quality_score': 0.8,
            'response_time': 2.0,
            'usage_count': 100
        }
        
        confidence = self.analytics._calculate_confidence_score(
            "BTPlansInformation",
            query_analysis,
            performance
        )
        
        self.assertGreater(confidence, 0)
        self.assertLessEqual(confidence, 1.0)
        self.assertGreater(confidence, 0.5)  # Should be above base score
    
    def test_get_category_match_score(self):
        """Test category matching score"""
        # Test BT-specific tool with plans query
        score1 = self.analytics._get_category_match_score("BTPlansInformation", "plans")
        self.assertEqual(score1, 0.8)
        
        # Test non-matching tool
        score2 = self.analytics._get_category_match_score("RandomTool", "plans")
        self.assertEqual(score2, 0.3)
    
    def test_generate_recommendation_reason(self):
        """Test recommendation reason generation"""
        query_analysis = QueryAnalysis(
            query_type="support",
            complexity_score=0.5,
            keywords=["support", "help"],
            intent="support_seeking",
            confidence=0.8
        )
        
        performance = {
            'success_rate': 0.9,
            'quality_score': 0.8,
            'response_time': 2.0,
            'usage_count': 100
        }
        
        reason = self.analytics._generate_recommendation_reason(
            "CreateSupportTicket",
            query_analysis,
            performance
        )
        
        self.assertIsInstance(reason, str)
        self.assertGreater(len(reason), 0)
        self.assertIn("support", reason.lower())
    
    def test_estimate_performance(self):
        """Test performance estimation"""
        query_analysis = QueryAnalysis(
            query_type="plans",
            complexity_score=0.5,
            keywords=["plans"],
            intent="information_seeking",
            confidence=0.8
        )
        
        # Test with performance data
        performance = {
            'success_rate': 0.8,
            'quality_score': 0.9,
            'response_time': 2.0,
            'usage_count': 50
        }
        
        estimated = self.analytics._estimate_performance(
            "BTPlansInformation",
            query_analysis,
            performance
        )
        
        expected = 0.8 * 0.6 + 0.9 * 0.4  # Weighted average
        self.assertAlmostEqual(estimated, expected, places=2)
        
        # Test without performance data
        estimated_default = self.analytics._estimate_performance(
            "BTPlansInformation",
            query_analysis,
            None
        )
        
        self.assertEqual(estimated_default, 0.75)  # BT-specific default
    
    def test_get_default_tool_order(self):
        """Test default tool ordering"""
        # Test support query
        support_order = self.analytics._get_default_tool_order(
            "I need help with support",
            self.sample_tools
        )
        
        self.assertIsInstance(support_order, list)
        self.assertEqual(len(support_order), len(self.sample_tools))
        # Support tools should be prioritized
        self.assertIn("CreateSupportTicket", support_order[:2])
        
        # Test plans query
        plans_order = self.analytics._get_default_tool_order(
            "What are the mobile plans?",
            self.sample_tools
        )
        
        self.assertIn("BTPlansInformation", plans_order[:2])
    
    def test_cache_functionality(self):
        """Test performance cache functionality"""
        # Test cache miss and population
        with patch.object(self.analytics.db_session, 'query') as mock_query:
            mock_metrics = [
                Mock(
                    usage_count=10,
                    success_rate=0.8,
                    response_quality_score=0.75,
                    average_response_time=2.0
                )
            ]
            mock_query.return_value.filter.return_value.all.return_value = mock_metrics
            
            # First call should query database
            performance1 = self.analytics._get_tool_performance("TestTool", "general")
            self.assertIsNotNone(performance1)
            
            # Second call should use cache
            performance2 = self.analytics._get_tool_performance("TestTool", "general")
            self.assertEqual(performance1, performance2)
            
            # Database should only be queried once
            self.assertEqual(mock_query.call_count, 1)
    
    def test_clear_performance_cache(self):
        """Test cache clearing functionality"""
        # Populate cache
        self.analytics._performance_cache["TestTool_general"] = {"test": "data"}
        self.analytics._cache_expiry["TestTool_general"] = datetime.now() + timedelta(minutes=5)
        
        # Clear specific tool cache
        self.analytics._clear_performance_cache("TestTool")
        
        self.assertNotIn("TestTool_general", self.analytics._performance_cache)
        self.assertNotIn("TestTool_general", self.analytics._cache_expiry)
        
        # Test clear all cache
        self.analytics._performance_cache["AnotherTool_general"] = {"test": "data"}
        self.analytics._clear_performance_cache()
        
        self.assertEqual(len(self.analytics._performance_cache), 0)
        self.assertEqual(len(self.analytics._cache_expiry), 0)


class TestToolPerformanceReport(unittest.TestCase):
    """Test suite for ToolPerformanceReport dataclass"""
    
    def test_creation(self):
        """Test report creation"""
        report = ToolPerformanceReport(
            tool_name="TestTool",
            total_usage=100,
            success_rate=0.85,
            average_response_time=2.5,
            average_quality_score=0.8,
            trend="improving",
            recommendations=["Optimize response time"]
        )
        
        self.assertEqual(report.tool_name, "TestTool")
        self.assertEqual(report.total_usage, 100)
        self.assertEqual(report.success_rate, 0.85)
        self.assertEqual(report.trend, "improving")
        self.assertIsInstance(report.recommendations, list)


class TestQueryAnalysis(unittest.TestCase):
    """Test suite for QueryAnalysis dataclass"""
    
    def test_creation(self):
        """Test query analysis creation"""
        analysis = QueryAnalysis(
            query_type="support",
            complexity_score=0.7,
            keywords=["help", "support", "issue"],
            intent="support_seeking",
            confidence=0.9
        )
        
        self.assertEqual(analysis.query_type, "support")
        self.assertEqual(analysis.complexity_score, 0.7)
        self.assertIsInstance(analysis.keywords, list)
        self.assertEqual(analysis.intent, "support_seeking")
        self.assertEqual(analysis.confidence, 0.9)


class TestIntegrationScenarios(unittest.TestCase):
    """Integration test scenarios for realistic usage patterns"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.mock_db_session = Mock()
        self.analytics = ToolUsageAnalytics(db_session=self.mock_db_session)
    
    def test_complete_workflow(self):
        """Test complete workflow from recording to recommendation"""
        # Mock no existing metrics initially
        self.mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Record several tool usages
        tools_and_queries = [
            ("BTPlansInformation", "What are BT mobile plans?", True, 0.9),
            ("BTWebsiteSearch", "BT customer support", True, 0.8),
            ("CreateSupportTicket", "I have a billing issue", True, 0.85),
            ("BTPlansInformation", "Mobile plan pricing", True, 0.88)
        ]
        
        for tool, query, success, quality in tools_and_queries:
            result = self.analytics.record_tool_usage(tool, query, success, quality)
            self.assertTrue(result)
        
        # Mock performance data for recommendations
        with patch.object(self.analytics, '_get_tool_performance') as mock_perf:
            mock_perf.return_value = {
                'success_rate': 0.9,
                'quality_score': 0.85,
                'response_time': 2.0,
                'usage_count': 10
            }
            
            # Get recommendations
            recommendations = self.analytics.get_tool_recommendations(
                "What are the current BT mobile plans?",
                ["BTPlansInformation", "BTWebsiteSearch", "ComprehensiveAnswerGenerator"]
            )
            
            self.assertGreater(len(recommendations), 0)
            
            # Optimize tool selection
            optimized = self.analytics.optimize_tool_selection(
                "What are the current BT mobile plans?",
                ["BTPlansInformation", "BTWebsiteSearch", "ComprehensiveAnswerGenerator"]
            )
            
            self.assertIsInstance(optimized, list)
            self.assertGreater(len(optimized), 0)
    
    def test_error_recovery(self):
        """Test system behavior under error conditions"""
        # Test database connection error in _get_tool_performance
        with patch.object(self.analytics, '_get_tool_performance') as mock_perf:
            mock_perf.side_effect = Exception("Connection lost")
            
            # Should handle gracefully and return empty recommendations
            recommendations = self.analytics.get_tool_recommendations(
                "test query",
                ["TestTool"]
            )
            
            # Should return empty list due to error
            self.assertEqual(len(recommendations), 0)
        
        # Test partial data scenarios
        self.mock_db_session.query.return_value.filter.return_value.all.return_value = []
        
        stats = self.analytics.get_usage_statistics()
        self.assertEqual(stats["total_usage"], 0)


if __name__ == '__main__':
    # Configure logging for tests
    logging.basicConfig(level=logging.WARNING)
    
    # Run tests
    unittest.main(verbosity=2)