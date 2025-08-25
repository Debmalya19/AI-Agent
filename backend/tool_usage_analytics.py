"""
Tool Usage Analytics System

This module provides comprehensive analytics for tool usage patterns, performance tracking,
and intelligent tool recommendation based on historical data and success rates.

Requirements covered:
- 3.1: Tool usage tracking and performance metrics
- 3.2: Tool recommendation algorithms based on historical data  
- 3.3: Tool optimization logic for better selection
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict
import json
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from backend.memory_models import ToolUsageMetrics, ToolRecommendationDTO
from backend.database import SessionLocal


@dataclass
class ToolPerformanceReport:
    """Report containing tool performance analytics"""
    tool_name: str
    total_usage: int
    success_rate: float
    average_response_time: float
    average_quality_score: float
    trend: str  # 'improving', 'declining', 'stable'
    recommendations: List[str]


@dataclass
class QueryAnalysis:
    """Analysis of query characteristics for tool selection"""
    query_type: str
    complexity_score: float
    keywords: List[str]
    intent: str
    confidence: float


class ToolUsageAnalytics:
    """
    Analytics system for tracking tool performance and providing intelligent recommendations.
    
    This class handles:
    - Recording tool usage metrics
    - Analyzing tool performance patterns
    - Generating tool recommendations based on historical data
    - Optimizing tool selection for better results
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize the analytics system with database session"""
        self.db_session = db_session or SessionLocal()
        self.logger = logging.getLogger(__name__)
        
        # Cache for frequently accessed data
        self._performance_cache = {}
        self._cache_expiry = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Tool categories for better organization
        self.tool_categories = {
            'search': ['search', 'BTWebsiteSearch', 'DuckDuckGoSearchRun'],
            'knowledge': ['ContextRetriever', 'ComprehensiveAnswerGenerator'],
            'bt_specific': ['BTSupportHours', 'BTPlansInformation', 'BTWebsiteSearch'],
            'support': ['CreateSupportTicket'],
            'orchestration': ['IntelligentToolOrchestrator', 'ComprehensiveAnswerGenerator']
        }
    
    def record_tool_usage(
        self,
        tool_name: str,
        query: str,
        success: bool,
        response_quality: float,
        response_time: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record tool usage metrics for analytics.
        
        Args:
            tool_name: Name of the tool used
            query: The query that triggered the tool
            success: Whether the tool execution was successful
            response_quality: Quality score of the response (0.0-1.0)
            response_time: Time taken for tool execution in seconds
            context: Additional context information
            
        Returns:
            bool: True if recording was successful
        """
        try:
            # Generate query hash for grouping similar queries
            query_hash = self._generate_query_hash(query)
            query_type = self._analyze_query_type(query)
            
            # Check if we have existing metrics for this tool/query combination
            existing_metric = self.db_session.query(ToolUsageMetrics).filter(
                and_(
                    ToolUsageMetrics.tool_name == tool_name,
                    ToolUsageMetrics.query_hash == query_hash
                )
            ).first()
            
            if existing_metric:
                # Update existing metrics
                self._update_existing_metrics(
                    existing_metric, success, response_quality, response_time
                )
            else:
                # Create new metrics entry
                self._create_new_metrics(
                    tool_name, query_type, query_hash, success, 
                    response_quality, response_time
                )
            
            self.db_session.commit()
            
            # Clear cache to ensure fresh data
            self._clear_performance_cache(tool_name)
            
            self.logger.info(f"Recorded usage for tool {tool_name}: success={success}, quality={response_quality}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error recording tool usage: {e}")
            self.db_session.rollback()
            return False
    
    def get_tool_recommendations(
        self,
        query: str,
        available_tools: List[str],
        context: Optional[Dict[str, Any]] = None,
        max_recommendations: int = 5
    ) -> List[ToolRecommendationDTO]:
        """
        Get tool recommendations based on query analysis and historical performance.
        
        Args:
            query: The user query
            available_tools: List of available tools to choose from
            context: Additional context for recommendation
            max_recommendations: Maximum number of recommendations to return
            
        Returns:
            List of tool recommendations sorted by confidence score
        """
        try:
            # Analyze the query
            query_analysis = self._analyze_query(query)
            
            # Get performance data for available tools
            tool_performances = {}
            for tool in available_tools:
                performance = self._get_tool_performance(tool, query_analysis.query_type)
                if performance:
                    tool_performances[tool] = performance
            
            # Generate recommendations based on multiple factors
            recommendations = []
            
            for tool_name in available_tools:
                confidence_score = self._calculate_confidence_score(
                    tool_name, query_analysis, tool_performances.get(tool_name)
                )
                
                if confidence_score > 0.1:  # Minimum confidence threshold
                    reason = self._generate_recommendation_reason(
                        tool_name, query_analysis, tool_performances.get(tool_name)
                    )
                    
                    expected_performance = self._estimate_performance(
                        tool_name, query_analysis, tool_performances.get(tool_name)
                    )
                    
                    recommendation = ToolRecommendationDTO(
                        tool_name=tool_name,
                        confidence_score=confidence_score,
                        reason=reason,
                        expected_performance=expected_performance
                    )
                    recommendations.append(recommendation)
            
            # Sort by confidence score and return top recommendations
            recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
            return recommendations[:max_recommendations]
            
        except Exception as e:
            self.logger.error(f"Error generating tool recommendations: {e}")
            # Return empty list on error to ensure graceful handling
            return []
    
    def analyze_tool_performance(
        self,
        time_period: timedelta = timedelta(days=30),
        tool_name: Optional[str] = None
    ) -> List[ToolPerformanceReport]:
        """
        Analyze tool performance over a specified time period.
        
        Args:
            time_period: Time period to analyze
            tool_name: Specific tool to analyze (None for all tools)
            
        Returns:
            List of performance reports
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - time_period
            
            # Build query
            query = self.db_session.query(ToolUsageMetrics).filter(
                ToolUsageMetrics.last_used >= cutoff_date
            )
            
            if tool_name:
                query = query.filter(ToolUsageMetrics.tool_name == tool_name)
            
            metrics = query.all()
            
            # Group metrics by tool
            tool_metrics = defaultdict(list)
            for metric in metrics:
                tool_metrics[metric.tool_name].append(metric)
            
            # Generate reports
            reports = []
            for tool, tool_metric_list in tool_metrics.items():
                report = self._generate_performance_report(tool, tool_metric_list)
                reports.append(report)
            
            # Sort by usage count
            reports.sort(key=lambda x: x.total_usage, reverse=True)
            return reports
            
        except Exception as e:
            self.logger.error(f"Error analyzing tool performance: {e}")
            return []
    
    def optimize_tool_selection(
        self,
        query: str,
        available_tools: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Optimize tool selection based on query analysis and performance data.
        
        Args:
            query: The user query
            available_tools: List of available tools
            context: Additional context for optimization
            
        Returns:
            Optimized list of tools in recommended order
        """
        try:
            # Get recommendations
            recommendations = self.get_tool_recommendations(
                query, available_tools, context
            )
            
            if not recommendations:
                # Fallback to default ordering based on tool categories
                return self._get_default_tool_order(query, available_tools)
            
            # Extract tool names in order of confidence
            optimized_tools = [rec.tool_name for rec in recommendations]
            
            # Add any remaining tools that weren't recommended
            remaining_tools = [tool for tool in available_tools if tool not in optimized_tools]
            optimized_tools.extend(remaining_tools)
            
            self.logger.info(f"Optimized tool selection for query: {optimized_tools[:3]}")
            return optimized_tools
            
        except Exception as e:
            self.logger.error(f"Error optimizing tool selection: {e}")
            return available_tools  # Return original list as fallback
    
    def get_tool_success_rate(self, tool_name: str, days: int = 30) -> float:
        """Get success rate for a specific tool over the last N days"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            metrics = self.db_session.query(ToolUsageMetrics).filter(
                and_(
                    ToolUsageMetrics.tool_name == tool_name,
                    ToolUsageMetrics.last_used >= cutoff_date
                )
            ).all()
            
            if not metrics:
                return 0.5  # Default neutral success rate
            
            # Calculate weighted average success rate
            total_weight = sum(metric.usage_count for metric in metrics)
            if total_weight == 0:
                return 0.5
            
            weighted_success = sum(
                metric.success_rate * metric.usage_count for metric in metrics
            )
            
            return weighted_success / total_weight
            
        except Exception as e:
            self.logger.error(f"Error getting success rate for {tool_name}: {e}")
            return 0.5
    
    def get_usage_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive usage statistics"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            metrics = self.db_session.query(ToolUsageMetrics).filter(
                ToolUsageMetrics.last_used >= cutoff_date
            ).all()
            
            if not metrics:
                return {"total_usage": 0, "tools": {}}
            
            # Calculate statistics
            total_usage = sum(metric.usage_count for metric in metrics)
            tool_stats = {}
            
            for metric in metrics:
                tool_name = metric.tool_name
                if tool_name not in tool_stats:
                    tool_stats[tool_name] = {
                        "usage_count": 0,
                        "success_rate": 0.0,
                        "avg_quality": 0.0,
                        "avg_response_time": 0.0
                    }
                
                tool_stats[tool_name]["usage_count"] += metric.usage_count
                tool_stats[tool_name]["success_rate"] = metric.success_rate
                tool_stats[tool_name]["avg_quality"] = metric.response_quality_score
                tool_stats[tool_name]["avg_response_time"] = metric.average_response_time
            
            return {
                "total_usage": total_usage,
                "tools": tool_stats,
                "period_days": days,
                "most_used": max(tool_stats.keys(), key=lambda k: tool_stats[k]["usage_count"]) if tool_stats else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting usage statistics: {e}")
            return {"total_usage": 0, "tools": {}}
    
    # Private helper methods
    
    def _generate_query_hash(self, query: str) -> str:
        """Generate a hash for similar queries"""
        # Normalize query for better grouping
        normalized = query.lower().strip()
        # Remove punctuation and common words for better similarity
        import re
        normalized = re.sub(r'[^\w\s]', '', normalized)
        words = [word for word in normalized.split() if len(word) > 2]
        # Sort words to ensure similar queries get same hash
        normalized = " ".join(sorted(words))
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _analyze_query_type(self, query: str) -> str:
        """Analyze query type for categorization"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['support', 'help', 'contact', 'hours']):
            return 'support'
        elif any(word in query_lower for word in ['plan', 'pricing', 'cost', 'upgrade']):
            return 'plans'
        elif any(word in query_lower for word in ['technical', 'error', 'problem', 'fix']):
            return 'technical'
        elif any(word in query_lower for word in ['billing', 'payment', 'invoice']):
            return 'billing'
        else:
            return 'general'
    
    def _analyze_query(self, query: str) -> QueryAnalysis:
        """Comprehensive query analysis"""
        query_type = self._analyze_query_type(query)
        keywords = [word.lower() for word in query.split() if len(word) > 2]
        
        # Calculate complexity based on length and keywords
        complexity_score = min(len(query) / 100.0, 1.0)
        
        # Determine intent
        intent = self._determine_intent(query)
        
        # Calculate confidence based on keyword clarity
        confidence = self._calculate_query_confidence(query, keywords)
        
        return QueryAnalysis(
            query_type=query_type,
            complexity_score=complexity_score,
            keywords=keywords,
            intent=intent,
            confidence=confidence
        )
    
    def _determine_intent(self, query: str) -> str:
        """Determine user intent from query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['how', 'what', 'when', 'where', 'why']):
            return 'information_seeking'
        elif any(word in query_lower for word in ['help', 'support', 'problem', 'issue']):
            return 'support_seeking'
        elif any(word in query_lower for word in ['buy', 'purchase', 'upgrade', 'change']):
            return 'transactional'
        else:
            return 'general'
    
    def _calculate_query_confidence(self, query: str, keywords: List[str]) -> float:
        """Calculate confidence in query analysis"""
        # Base confidence on query length and keyword specificity
        base_confidence = min(len(query) / 50.0, 1.0)
        
        # Boost confidence for specific keywords
        specific_keywords = ['bt', 'mobile', 'plan', 'support', 'billing']
        keyword_boost = sum(1 for kw in keywords if kw in specific_keywords) * 0.1
        
        return min(base_confidence + keyword_boost, 1.0)
    
    def _update_existing_metrics(
        self,
        metric: ToolUsageMetrics,
        success: bool,
        response_quality: float,
        response_time: Optional[float]
    ):
        """Update existing metrics with new data"""
        # Update usage count
        metric.usage_count += 1
        
        # Update success rate (weighted average)
        old_success_rate = metric.success_rate
        new_success_rate = 1.0 if success else 0.0
        metric.success_rate = (
            (old_success_rate * (metric.usage_count - 1) + new_success_rate) / 
            metric.usage_count
        )
        
        # Update quality score (weighted average)
        old_quality = metric.response_quality_score
        metric.response_quality_score = (
            (old_quality * (metric.usage_count - 1) + response_quality) / 
            metric.usage_count
        )
        
        # Update response time if provided
        if response_time is not None:
            old_time = metric.average_response_time
            metric.average_response_time = (
                (old_time * (metric.usage_count - 1) + response_time) / 
                metric.usage_count
            )
        
        metric.last_used = datetime.now(timezone.utc)
    
    def _create_new_metrics(
        self,
        tool_name: str,
        query_type: str,
        query_hash: str,
        success: bool,
        response_quality: float,
        response_time: Optional[float]
    ):
        """Create new metrics entry"""
        new_metric = ToolUsageMetrics(
            tool_name=tool_name,
            query_type=query_type,
            query_hash=query_hash,
            success_rate=1.0 if success else 0.0,
            average_response_time=response_time or 0.0,
            response_quality_score=response_quality,
            usage_count=1
        )
        
        self.db_session.add(new_metric)
    
    def _get_tool_performance(self, tool_name: str, query_type: str) -> Optional[Dict[str, float]]:
        """Get cached or fresh performance data for a tool"""
        cache_key = f"{tool_name}_{query_type}"
        
        # Check cache first
        if (cache_key in self._performance_cache and 
            cache_key in self._cache_expiry and
            datetime.now() < self._cache_expiry[cache_key]):
            return self._performance_cache[cache_key]
        
        # Fetch fresh data
        try:
            metrics = self.db_session.query(ToolUsageMetrics).filter(
                and_(
                    ToolUsageMetrics.tool_name == tool_name,
                    ToolUsageMetrics.query_type == query_type
                )
            ).all()
            
            if not metrics:
                return None
            
            # Calculate aggregated performance
            total_usage = sum(m.usage_count for m in metrics)
            if total_usage == 0:
                return None
                
            weighted_success = sum(m.success_rate * m.usage_count for m in metrics) / total_usage
            weighted_quality = sum(m.response_quality_score * m.usage_count for m in metrics) / total_usage
            avg_response_time = sum(m.average_response_time * m.usage_count for m in metrics) / total_usage
            
            performance = {
                'success_rate': weighted_success,
                'quality_score': weighted_quality,
                'response_time': avg_response_time,
                'usage_count': total_usage
            }
            
            # Cache the result
            self._performance_cache[cache_key] = performance
            self._cache_expiry[cache_key] = datetime.now() + timedelta(seconds=self._cache_ttl)
            
            return performance
            
        except Exception as e:
            self.logger.error(f"Error getting performance for {tool_name}: {e}")
            return None
    
    def _calculate_confidence_score(
        self,
        tool_name: str,
        query_analysis: QueryAnalysis,
        performance: Optional[Dict[str, float]]
    ) -> float:
        """Calculate confidence score for tool recommendation"""
        base_score = 0.5  # Base confidence
        
        # Factor 1: Tool category match with query type
        category_score = self._get_category_match_score(tool_name, query_analysis.query_type)
        
        # Factor 2: Historical performance
        performance_score = 0.5
        if performance:
            performance_score = (
                performance['success_rate'] * 0.4 +
                performance['quality_score'] * 0.4 +
                min(performance['usage_count'] / 100.0, 0.2)  # Usage frequency bonus
            )
        
        # Factor 3: Query confidence
        query_confidence_factor = query_analysis.confidence * 0.2
        
        # Combine factors
        final_score = (
            base_score * 0.2 +
            category_score * 0.4 +
            performance_score * 0.3 +
            query_confidence_factor * 0.1
        )
        
        return min(final_score, 1.0)
    
    def _get_category_match_score(self, tool_name: str, query_type: str) -> float:
        """Get score for how well tool category matches query type"""
        # Define query type to tool category mappings
        type_category_map = {
            'support': ['support', 'bt_specific'],
            'plans': ['bt_specific', 'search'],
            'technical': ['knowledge', 'search'],
            'billing': ['support', 'bt_specific'],
            'general': ['knowledge', 'orchestration']
        }
        
        preferred_categories = type_category_map.get(query_type, ['knowledge'])
        
        # Check if tool belongs to preferred categories
        for category, tools in self.tool_categories.items():
            if tool_name in tools and category in preferred_categories:
                return 0.8
        
        return 0.3  # Default score for non-matching tools
    
    def _generate_recommendation_reason(
        self,
        tool_name: str,
        query_analysis: QueryAnalysis,
        performance: Optional[Dict[str, float]]
    ) -> str:
        """Generate human-readable reason for recommendation"""
        reasons = []
        
        # Category-based reason
        category_match = self._get_category_match_score(tool_name, query_analysis.query_type)
        if category_match > 0.5:
            reasons.append(f"Well-suited for {query_analysis.query_type} queries")
        
        # Performance-based reason
        if performance:
            if performance['success_rate'] > 0.8:
                reasons.append("High success rate in similar queries")
            if performance['quality_score'] > 0.7:
                reasons.append("Consistently produces high-quality responses")
            if performance['usage_count'] > 50:
                reasons.append("Proven track record with extensive usage")
        
        # Intent-based reason
        if query_analysis.intent == 'information_seeking' and 'search' in tool_name.lower():
            reasons.append("Optimized for information retrieval")
        elif query_analysis.intent == 'support_seeking' and 'support' in tool_name.lower():
            reasons.append("Specialized for support requests")
        
        return "; ".join(reasons) if reasons else "General purpose tool"
    
    def _estimate_performance(
        self,
        tool_name: str,
        query_analysis: QueryAnalysis,
        performance: Optional[Dict[str, float]]
    ) -> float:
        """Estimate expected performance for the tool"""
        if performance:
            # Weight success rate and quality score
            return (performance['success_rate'] * 0.6 + performance['quality_score'] * 0.4)
        
        # Default estimates based on tool type
        if 'BT' in tool_name:
            return 0.75  # BT-specific tools generally perform well
        elif 'search' in tool_name.lower():
            return 0.65  # Search tools are reliable
        elif 'orchestrator' in tool_name.lower():
            return 0.8   # Orchestrators combine multiple sources
        else:
            return 0.6   # Default estimate
    
    def _generate_performance_report(
        self,
        tool_name: str,
        metrics: List[ToolUsageMetrics]
    ) -> ToolPerformanceReport:
        """Generate performance report for a tool"""
        total_usage = sum(m.usage_count for m in metrics)
        
        # Calculate weighted averages
        success_rates = [m.success_rate for m in metrics]
        quality_scores = [m.response_quality_score for m in metrics]
        response_times = [m.average_response_time for m in metrics]
        
        avg_success_rate = statistics.mean(success_rates) if success_rates else 0.0
        avg_quality_score = statistics.mean(quality_scores) if quality_scores else 0.0
        avg_response_time = statistics.mean(response_times) if response_times else 0.0
        
        # Determine trend (simplified)
        trend = "stable"
        if len(metrics) > 1:
            recent_success = statistics.mean(success_rates[-3:]) if len(success_rates) >= 3 else success_rates[-1]
            older_success = statistics.mean(success_rates[:-3]) if len(success_rates) >= 6 else success_rates[0]
            
            if recent_success > older_success + 0.1:
                trend = "improving"
            elif recent_success < older_success - 0.1:
                trend = "declining"
        
        # Generate recommendations
        recommendations = []
        if avg_success_rate < 0.6:
            recommendations.append("Consider reviewing tool configuration or usage patterns")
        if avg_response_time > 5.0:
            recommendations.append("Optimize for better response time")
        if total_usage < 10:
            recommendations.append("Consider promoting this tool for relevant queries")
        
        return ToolPerformanceReport(
            tool_name=tool_name,
            total_usage=total_usage,
            success_rate=avg_success_rate,
            average_response_time=avg_response_time,
            average_quality_score=avg_quality_score,
            trend=trend,
            recommendations=recommendations
        )
    
    def _get_default_tool_order(self, query: str, available_tools: List[str]) -> List[str]:
        """Get default tool ordering when no analytics data is available"""
        query_type = self._analyze_query_type(query)
        
        # Define priority orders for different query types
        priority_orders = {
            'support': ['BTSupportHours', 'CreateSupportTicket', 'BTWebsiteSearch'],
            'plans': ['BTPlansInformation', 'BTWebsiteSearch', 'ComprehensiveAnswerGenerator'],
            'technical': ['ContextRetriever', 'ComprehensiveAnswerGenerator', 'BTWebsiteSearch'],
            'billing': ['CreateSupportTicket', 'BTSupportHours', 'BTWebsiteSearch'],
            'general': ['ComprehensiveAnswerGenerator', 'BTWebsiteSearch', 'ContextRetriever']
        }
        
        preferred_order = priority_orders.get(query_type, priority_orders['general'])
        
        # Order available tools based on preferences
        ordered_tools = []
        for tool in preferred_order:
            if tool in available_tools:
                ordered_tools.append(tool)
        
        # Add remaining tools
        for tool in available_tools:
            if tool not in ordered_tools:
                ordered_tools.append(tool)
        
        return ordered_tools
    
    def _clear_performance_cache(self, tool_name: Optional[str] = None):
        """Clear performance cache for specific tool or all tools"""
        if tool_name:
            keys_to_remove = [key for key in self._performance_cache.keys() if key.startswith(tool_name)]
            for key in keys_to_remove:
                self._performance_cache.pop(key, None)
                self._cache_expiry.pop(key, None)
        else:
            self._performance_cache.clear()
            self._cache_expiry.clear()
    
    def __del__(self):
        """Cleanup database session"""
        if hasattr(self, 'db_session') and self.db_session:
            try:
                self.db_session.close()
            except:
                pass