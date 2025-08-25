"""
ToolSelector - Algorithm for optimal tool selection.
"""

import re
import logging
from typing import List, Dict, Any, Set, Optional
from collections import Counter

from .models import BaseToolSelector, ToolScore, ContextEntry
from .exceptions import ToolSelectionError


class ToolSelector(BaseToolSelector):
    """
    Algorithm for optimal tool selection.
    
    Implements scoring algorithms for tool relevance based on query analysis,
    historical performance, and context awareness.
    """
    
    def __init__(
        self, 
        tool_metadata: Optional[Dict[str, Dict[str, Any]]] = None, 
        analytics_service=None,
        memory_manager=None
    ):
        """
        Initialize ToolSelector.
        
        Args:
            tool_metadata: Metadata about available tools including keywords,
                          categories, and performance metrics
            analytics_service: ToolUsageAnalytics service for historical performance data
            memory_manager: Memory layer manager for context integration
        """
        self.tool_metadata = tool_metadata or {}
        self.analytics_service = analytics_service
        self.memory_manager = memory_manager
        self._performance_cache: Dict[str, Dict[str, float]] = {}
        self._keyword_cache: Dict[str, Set[str]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Enhanced tool categories and keywords based on existing tools
        self._default_tool_info = {
            "web_search": {
                "keywords": ["search", "find", "lookup", "web", "internet", "online"],
                "category": "information_retrieval",
                "base_score": 0.7
            },
            "database_query": {
                "keywords": ["data", "database", "query", "sql", "records", "table"],
                "category": "data_access",
                "base_score": 0.8
            },
            "file_analysis": {
                "keywords": ["file", "document", "analyze", "read", "parse", "content"],
                "category": "file_processing",
                "base_score": 0.6
            },
            "calculation": {
                "keywords": ["calculate", "compute", "math", "number", "formula"],
                "category": "computation",
                "base_score": 0.9
            },
            "code_generation": {
                "keywords": ["code", "program", "script", "function", "class", "generate"],
                "category": "development",
                "base_score": 0.8
            },
            # BT-specific tools
            "BTWebsiteSearch": {
                "keywords": ["bt", "mobile", "plan", "service", "website", "official", "current"],
                "category": "bt_specific",
                "base_score": 0.9
            },
            "BTSupportHours": {
                "keywords": ["support", "hours", "contact", "help", "phone", "customer", "service"],
                "category": "support",
                "base_score": 0.8
            },
            "BTPlansInformation": {
                "keywords": ["plan", "pricing", "cost", "upgrade", "mobile", "data", "unlimited"],
                "category": "plans",
                "base_score": 0.9
            },
            "CreateSupportTicket": {
                "keywords": ["issue", "problem", "error", "bug", "help", "support", "ticket"],
                "category": "support",
                "base_score": 0.7
            },
            "ComprehensiveAnswerGenerator": {
                "keywords": ["comprehensive", "detailed", "complete", "thorough", "information"],
                "category": "orchestration",
                "base_score": 0.8
            },
            "IntelligentToolOrchestrator": {
                "keywords": ["intelligent", "smart", "orchestrate", "combine", "multiple"],
                "category": "orchestration",
                "base_score": 0.8
            },
            "ContextRetriever": {
                "keywords": ["context", "history", "previous", "memory", "conversation"],
                "category": "context",
                "base_score": 0.7
            }
        }
    
    def score_tools(self, query: str, available_tools: List[str]) -> List[ToolScore]:
        """
        Score tools for relevance to a query.
        
        Args:
            query: User query to analyze
            available_tools: List of available tool names
            
        Returns:
            List of tool scores sorted by relevance
            
        Raises:
            ToolSelectionError: If scoring fails
        """
        try:
            if not query or not available_tools:
                return []
            
            # Preprocess query
            query_tokens = self._tokenize_query(query)
            query_keywords = self._extract_keywords(query)
            
            tool_scores = []
            
            for tool_name in available_tools:
                # Calculate base relevance score
                base_score = self._calculate_base_score(tool_name, query_tokens, query_keywords)
                
                # Get performance score
                performance_score = self._get_performance_score(tool_name)
                
                # Calculate final score
                final_score = (base_score * 0.7) + (performance_score * 0.3)
                
                # Create tool score
                tool_score = ToolScore(
                    tool_name=tool_name,
                    base_score=base_score,
                    context_boost=0.0,  # Will be applied later
                    performance_score=performance_score,
                    final_score=final_score,
                    reasoning=self._generate_reasoning(tool_name, base_score, performance_score)
                )
                
                tool_scores.append(tool_score)
            
            # Sort by final score
            tool_scores.sort(key=lambda x: x.final_score, reverse=True)
            
            return tool_scores
            
        except Exception as e:
            raise ToolSelectionError(
                f"Failed to score tools: {str(e)}",
                query=query,
                available_tools=available_tools,
                context={"error": str(e)}
            )
    
    def apply_context_boost(
        self, 
        scores: List[ToolScore], 
        context: List[ContextEntry]
    ) -> List[ToolScore]:
        """
        Apply context-based score boosting with advanced conversation pattern analysis.
        
        Args:
            scores: Current tool scores
            context: Conversation context entries
            
        Returns:
            Updated tool scores with context boost applied
        """
        if not context:
            return scores
        
        # Analyze context for multiple dimensions
        context_analysis = self._analyze_conversation_context(context)
        
        boosted_scores = []
        
        for score in scores:
            # Calculate multi-dimensional context boost
            context_boost = self._calculate_advanced_context_boost(
                score.tool_name, 
                context_analysis
            )
            
            # Apply boost to final score
            new_final_score = min(score.final_score + context_boost, 1.0)
            
            # Generate enhanced reasoning
            boost_reasoning = self._generate_boost_reasoning(
                score.tool_name, 
                context_boost, 
                context_analysis
            )
            
            # Create updated score
            boosted_score = ToolScore(
                tool_name=score.tool_name,
                base_score=score.base_score,
                context_boost=context_boost,
                performance_score=score.performance_score,
                final_score=new_final_score,
                reasoning=f"{score.reasoning} {boost_reasoning}"
            )
            
            boosted_scores.append(boosted_score)
        
        # Re-sort by final score
        boosted_scores.sort(key=lambda x: x.final_score, reverse=True)
        
        return boosted_scores
    
    def filter_by_threshold(self, scores: List[ToolScore], threshold: float = 0.5) -> List[str]:
        """
        Filter tools by score threshold.
        
        Args:
            scores: Tool scores to filter
            threshold: Minimum score threshold
            
        Returns:
            List of tool names that meet the threshold
        """
        filtered_tools = [
            score.tool_name 
            for score in scores 
            if score.final_score >= threshold
        ]
        
        return filtered_tools
    
    def _tokenize_query(self, query: str) -> List[str]:
        """Tokenize query into words."""
        # Simple tokenization - split on whitespace and punctuation
        tokens = re.findall(r'\b\w+\b', query.lower())
        return tokens
    
    def _extract_keywords(self, query: str) -> Set[str]:
        """Extract important keywords from query."""
        tokens = self._tokenize_query(query)
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'can', 'may', 'might', 'must', 'i', 'you', 'he', 'she', 'it', 'we',
            'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her',
            'its', 'our', 'their'
        }
        
        keywords = {token for token in tokens if token not in stop_words and len(token) > 2}
        return keywords
    
    def _calculate_base_score(
        self, 
        tool_name: str, 
        query_tokens: List[str], 
        query_keywords: Set[str]
    ) -> float:
        """Calculate base relevance score for a tool."""
        # Get tool information
        tool_info = self._get_tool_info(tool_name)
        tool_keywords = set(tool_info.get("keywords", []))
        base_score = tool_info.get("base_score", 0.5)
        
        if not tool_keywords:
            return base_score * 0.5  # Penalty for unknown tools
        
        # Calculate keyword overlap
        keyword_overlap = len(query_keywords.intersection(tool_keywords))
        max_possible_overlap = min(len(query_keywords), len(tool_keywords))
        
        if max_possible_overlap == 0:
            overlap_score = 0.0
        else:
            overlap_score = keyword_overlap / max_possible_overlap
        
        # Combine base score with overlap score
        final_score = (base_score * 0.6) + (overlap_score * 0.4)
        
        return min(final_score, 1.0)
    
    def _get_performance_score(self, tool_name: str) -> float:
        """Get performance score for a tool using analytics service."""
        try:
            # Check cache first
            if tool_name in self._performance_cache:
                return self._performance_cache[tool_name].get("success_rate", 0.7)
            
            # Get performance from analytics service if available
            if self.analytics_service:
                success_rate = self.analytics_service.get_tool_success_rate(tool_name, days=30)
                
                # Cache the result
                self._performance_cache[tool_name] = {
                    "success_rate": success_rate,
                    "cached_at": __import__('datetime').datetime.now()
                }
                
                return success_rate
            
            # Default performance score
            return 0.7
            
        except Exception as e:
            self.logger.warning(f"Failed to get performance score for {tool_name}: {e}")
            return 0.7
    
    def _get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get tool information from metadata or defaults."""
        if tool_name in self.tool_metadata:
            return self.tool_metadata[tool_name]
        elif tool_name in self._default_tool_info:
            return self._default_tool_info[tool_name]
        else:
            return {"keywords": [], "category": "unknown", "base_score": 0.5}
    
    def _extract_tools_from_context(self, context: List[ContextEntry]) -> Counter:
        """Extract tool usage patterns from context."""
        tool_mentions = Counter()
        
        for entry in context:
            # Look for tool mentions in context
            content_lower = entry.content.lower()
            
            # Check for explicit tool mentions
            for tool_name in self._default_tool_info.keys():
                if tool_name.replace("_", " ") in content_lower:
                    tool_mentions[tool_name] += 1
            
            # Check metadata for tool information
            if "tools_used" in entry.metadata:
                for tool in entry.metadata["tools_used"]:
                    tool_mentions[tool] += 1
        
        return tool_mentions
    
    def _extract_context_keywords(self, context: List[ContextEntry]) -> Set[str]:
        """Extract keywords from context entries."""
        all_keywords = set()
        
        for entry in context:
            entry_keywords = self._extract_keywords(entry.content)
            all_keywords.update(entry_keywords)
        
        return all_keywords
    
    def _analyze_conversation_context(self, context: List[ContextEntry]) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of conversation context.
        
        Args:
            context: List of context entries
            
        Returns:
            Dictionary containing various context analysis results
        """
        analysis = {
            "tool_usage_patterns": Counter(),
            "keyword_frequency": Counter(),
            "conversation_themes": [],
            "user_intent_progression": [],
            "temporal_patterns": {},
            "success_patterns": {},
            "context_continuity": 0.0
        }
        
        if not context:
            return analysis
        
        # Sort context by timestamp for temporal analysis
        sorted_context = sorted(context, key=lambda x: x.timestamp)
        
        # Analyze tool usage patterns
        for entry in context:
            # Extract tool mentions
            tools_used = entry.metadata.get("tools_used", [])
            for tool in tools_used:
                analysis["tool_usage_patterns"][tool] += 1
            
            # Extract keywords
            keywords = self._extract_keywords(entry.content)
            analysis["keyword_frequency"].update(keywords)
            
            # Analyze success patterns
            if "success" in entry.metadata:
                success = entry.metadata["success"]
                for tool in tools_used:
                    if tool not in analysis["success_patterns"]:
                        analysis["success_patterns"][tool] = {"successes": 0, "total": 0}
                    analysis["success_patterns"][tool]["total"] += 1
                    if success:
                        analysis["success_patterns"][tool]["successes"] += 1
        
        # Identify conversation themes
        analysis["conversation_themes"] = self._identify_conversation_themes(context)
        
        # Analyze user intent progression
        analysis["user_intent_progression"] = self._analyze_intent_progression(sorted_context)
        
        # Calculate temporal patterns
        analysis["temporal_patterns"] = self._analyze_temporal_patterns(sorted_context)
        
        # Calculate context continuity
        analysis["context_continuity"] = self._calculate_context_continuity(sorted_context)
        
        return analysis
    
    def _calculate_advanced_context_boost(
        self, 
        tool_name: str, 
        context_analysis: Dict[str, Any]
    ) -> float:
        """
        Calculate advanced context boost using multiple factors.
        
        Args:
            tool_name: Name of the tool to boost
            context_analysis: Comprehensive context analysis
            
        Returns:
            Context boost value (0.0 to 0.5)
        """
        try:
            boost = 0.0
            
            # 1. Recent tool usage boost (max 0.15)
            tool_usage_patterns = context_analysis.get("tool_usage_patterns", {})
            usage_count = tool_usage_patterns.get(tool_name, 0) if hasattr(tool_usage_patterns, 'get') else 0
            if usage_count > 0:
                usage_boost = min(usage_count * 0.05, 0.15)
                boost += usage_boost
            
            # 2. Keyword relevance boost (max 0.1)
            tool_info = self._get_tool_info(tool_name)
            tool_keywords = set(tool_info.get("keywords", []))
            keyword_freq = context_analysis.get("keyword_frequency", {})
            
            if hasattr(keyword_freq, 'get'):
                keyword_score = sum(keyword_freq.get(kw, 0) for kw in tool_keywords)
                if keyword_score > 0:
                    keyword_boost = min(keyword_score * 0.02, 0.1)
                    boost += keyword_boost
            
            # 3. Theme relevance boost (max 0.1)
            themes = context_analysis.get("conversation_themes", [])
            tool_category = tool_info.get("category", "unknown")
            
            theme_boost = 0.0
            for theme in themes:
                if self._is_theme_relevant_to_tool(theme, tool_category):
                    theme_boost += 0.03
            theme_boost = min(theme_boost, 0.1)
            boost += theme_boost
            
            # 4. Success pattern boost (max 0.08)
            success_patterns = context_analysis.get("success_patterns", {})
            if tool_name in success_patterns:
                pattern = success_patterns[tool_name]
                if isinstance(pattern, dict) and pattern.get("total", 0) > 0:
                    success_rate = pattern["successes"] / pattern["total"]
                    success_boost = success_rate * 0.08
                    boost += success_boost
            
            # 5. Context continuity boost (max 0.07)
            continuity = context_analysis.get("context_continuity", 0.0)
            if isinstance(continuity, (int, float)) and continuity > 0.5:
                continuity_boost = (continuity - 0.5) * 0.14  # Scale to max 0.07
                boost += continuity_boost
            
            return min(boost, 0.5)  # Cap total boost at 0.5
            
        except Exception as e:
            self.logger.warning(f"Error calculating context boost for {tool_name}: {e}")
            return 0.0
    
    def _identify_conversation_themes(self, context: List[ContextEntry]) -> List[str]:
        """Identify main themes in the conversation."""
        themes = []
        all_content = " ".join(entry.content.lower() for entry in context)
        
        # Define theme patterns
        theme_patterns = {
            "support": ["help", "support", "problem", "issue", "error", "trouble"],
            "plans": ["plan", "pricing", "cost", "upgrade", "subscription", "package"],
            "technical": ["technical", "setup", "configure", "install", "troubleshoot"],
            "billing": ["bill", "payment", "charge", "invoice", "refund", "cost"],
            "information": ["information", "details", "explain", "what", "how", "when"]
        }
        
        for theme, keywords in theme_patterns.items():
            if any(keyword in all_content for keyword in keywords):
                themes.append(theme)
        
        return themes
    
    def _analyze_intent_progression(self, sorted_context: List[ContextEntry]) -> List[str]:
        """Analyze how user intent has progressed through the conversation."""
        intents = []
        
        for entry in sorted_context:
            content = entry.content.lower()
            
            # Intent classification with priority order
            if any(word in content for word in ["plan", "pricing", "upgrade", "cost"]):
                intents.append("plan_inquiry")
            elif any(word in content for word in ["help", "support", "problem", "issue"]):
                intents.append("support_seeking")
            elif any(word in content for word in ["how", "what", "explain", "check"]):
                intents.append("information_seeking")
            elif any(word in content for word in ["buy", "purchase", "order"]):
                intents.append("transactional")
            elif any(word in content for word in ["technical", "error", "trouble"]):
                intents.append("support_seeking")
            else:
                intents.append("general")
        
        return intents
    
    def _analyze_temporal_patterns(self, sorted_context: List[ContextEntry]) -> Dict[str, Any]:
        """Analyze temporal patterns in the conversation."""
        if len(sorted_context) < 2:
            return {"avg_gap": 0, "conversation_pace": "unknown"}
        
        # Calculate time gaps between entries
        time_gaps = []
        for i in range(1, len(sorted_context)):
            gap = (sorted_context[i].timestamp - sorted_context[i-1].timestamp).total_seconds()
            time_gaps.append(gap)
        
        avg_gap = sum(time_gaps) / len(time_gaps) if time_gaps else 0
        
        # Classify conversation pace
        if avg_gap < 30:  # Less than 30 seconds
            pace = "rapid"
        elif avg_gap < 300:  # Less than 5 minutes
            pace = "normal"
        else:
            pace = "slow"
        
        return {
            "avg_gap": avg_gap,
            "conversation_pace": pace,
            "total_duration": (sorted_context[-1].timestamp - sorted_context[0].timestamp).total_seconds()
        }
    
    def _calculate_context_continuity(self, sorted_context: List[ContextEntry]) -> float:
        """Calculate how continuous/coherent the conversation context is."""
        if len(sorted_context) < 2:
            return 0.0
        
        continuity_score = 0.0
        
        for i in range(1, len(sorted_context)):
            current_keywords = self._extract_keywords(sorted_context[i].content)
            previous_keywords = self._extract_keywords(sorted_context[i-1].content)
            
            # Calculate keyword overlap
            if current_keywords and previous_keywords:
                overlap = len(current_keywords.intersection(previous_keywords))
                total_unique = len(current_keywords.union(previous_keywords))
                if total_unique > 0:
                    continuity_score += overlap / total_unique
        
        # Average continuity across all adjacent pairs
        return continuity_score / (len(sorted_context) - 1) if len(sorted_context) > 1 else 0.0
    
    def _is_theme_relevant_to_tool(self, theme: str, tool_category: str) -> bool:
        """Check if a conversation theme is relevant to a tool category."""
        relevance_map = {
            "support": ["support", "bt_specific"],
            "plans": ["plans", "bt_specific"],
            "technical": ["technical", "information_retrieval"],
            "billing": ["support", "bt_specific"],
            "information": ["information_retrieval", "orchestration", "context"]
        }
        
        relevant_categories = relevance_map.get(theme, [])
        return tool_category in relevant_categories
    
    def _generate_boost_reasoning(
        self, 
        tool_name: str, 
        boost_value: float, 
        context_analysis: Dict[str, Any]
    ) -> str:
        """Generate human-readable reasoning for context boost."""
        if boost_value < 0.01:
            return ""
        
        reasons = []
        
        # Usage pattern reasoning
        usage_count = context_analysis["tool_usage_patterns"].get(tool_name, 0)
        if usage_count > 0:
            reasons.append(f"recently used {usage_count} time(s)")
        
        # Theme relevance reasoning
        themes = context_analysis["conversation_themes"]
        tool_info = self._get_tool_info(tool_name)
        tool_category = tool_info.get("category", "unknown")
        
        relevant_themes = [theme for theme in themes 
                          if self._is_theme_relevant_to_tool(theme, tool_category)]
        if relevant_themes:
            reasons.append(f"relevant to {', '.join(relevant_themes)} theme(s)")
        
        # Continuity reasoning
        continuity = context_analysis["context_continuity"]
        if continuity > 0.7:
            reasons.append("high conversation continuity")
        
        if reasons:
            return f"Context boost (+{boost_value:.2f}): {', '.join(reasons)}"
        else:
            return f"Context boost: +{boost_value:.2f}"
    
    def get_enhanced_context_for_user(
        self, 
        user_id: str, 
        query: str, 
        limit: int = 10
    ) -> List[ContextEntry]:
        """
        Get enhanced context for a user by integrating with memory layer.
        
        Args:
            user_id: User identifier
            query: Current query for relevance filtering
            limit: Maximum number of context entries to return
            
        Returns:
            List of relevant context entries
        """
        context_entries = []
        
        try:
            # Try to get context from memory manager if available
            if self.memory_manager:
                # This would integrate with the existing MemoryLayerManager
                memory_context = self.memory_manager.get_relevant_context(
                    user_id=user_id,
                    query=query,
                    limit=limit
                )
                
                # Convert memory context to ContextEntry format
                for memory_entry in memory_context:
                    context_entry = ContextEntry(
                        content=memory_entry.get("content", ""),
                        source="memory_layer",
                        relevance_score=memory_entry.get("relevance_score", 0.5),
                        timestamp=memory_entry.get("timestamp", __import__('datetime').datetime.now()),
                        context_type="conversation",
                        metadata=memory_entry.get("metadata", {})
                    )
                    context_entries.append(context_entry)
            
            # Enhance context with tool usage patterns from analytics
            if self.analytics_service and len(context_entries) < limit:
                try:
                    # Get recent tool usage statistics
                    usage_stats = self.analytics_service.get_usage_statistics(days=7)
                    
                    # Create synthetic context entries for tool usage patterns
                    for tool_name, stats in usage_stats.get("tools", {}).items():
                        if stats["usage_count"] > 0:
                            synthetic_entry = ContextEntry(
                                content=f"Recently used {tool_name} with {stats['success_rate']:.1%} success rate",
                                source="analytics",
                                relevance_score=min(stats["usage_count"] / 10.0, 1.0),
                                timestamp=__import__('datetime').datetime.now(),
                                context_type="tool_usage",
                                metadata={
                                    "tools_used": [tool_name],
                                    "success": stats["success_rate"] > 0.7,
                                    "usage_count": stats["usage_count"]
                                }
                            )
                            context_entries.append(synthetic_entry)
                            
                            if len(context_entries) >= limit:
                                break
                                
                except Exception as e:
                    self.logger.warning(f"Failed to get analytics context: {e}")
            
            # Sort by relevance and timestamp
            context_entries.sort(
                key=lambda x: (x.relevance_score, x.timestamp), 
                reverse=True
            )
            
            return context_entries[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to get enhanced context for user {user_id}: {e}")
            return []
    
    def learn_from_tool_usage(
        self, 
        user_id: str, 
        query: str, 
        selected_tools: List[str], 
        tool_results: List[Dict[str, Any]]
    ) -> None:
        """
        Learn from tool usage to improve future context-aware recommendations.
        
        Args:
            user_id: User identifier
            query: Original query
            selected_tools: Tools that were selected
            tool_results: Results from tool execution
        """
        try:
            # Update analytics service with usage data
            if self.analytics_service:
                for i, tool_name in enumerate(selected_tools):
                    result = tool_results[i] if i < len(tool_results) else {}
                    
                    success = result.get("success", False)
                    response_quality = result.get("quality_score", 0.5)
                    execution_time = result.get("execution_time", 0.0)
                    
                    self.analytics_service.record_tool_usage(
                        tool_name=tool_name,
                        query=query,
                        success=success,
                        response_quality=response_quality,
                        response_time=execution_time
                    )
            
            # Store context in memory manager if available
            if self.memory_manager:
                context_data = {
                    "query": query,
                    "selected_tools": selected_tools,
                    "results": tool_results,
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                }
                
                # This would integrate with existing memory storage
                self.memory_manager.store_interaction(
                    user_id=user_id,
                    interaction_type="tool_selection",
                    data=context_data
                )
                
        except Exception as e:
            self.logger.error(f"Failed to learn from tool usage: {e}")
    
    def _generate_reasoning(
        self, 
        tool_name: str, 
        base_score: float, 
        performance_score: float
    ) -> str:
        """Generate reasoning for tool score."""
        reasoning_parts = []
        
        if base_score > 0.7:
            reasoning_parts.append("High relevance to query")
        elif base_score > 0.4:
            reasoning_parts.append("Moderate relevance to query")
        else:
            reasoning_parts.append("Low relevance to query")
        
        if performance_score > 0.8:
            reasoning_parts.append("excellent historical performance")
        elif performance_score > 0.6:
            reasoning_parts.append("good historical performance")
        else:
            reasoning_parts.append("average historical performance")
        
        return f"{tool_name}: {', '.join(reasoning_parts)}"
    
    def update_performance_metrics(
        self, 
        tool_name: str, 
        query: str,
        success: bool, 
        execution_time: float,
        response_quality: float = 0.8
    ) -> None:
        """Update performance metrics for a tool."""
        try:
            # Update local cache
            if tool_name not in self._performance_cache:
                self._performance_cache[tool_name] = {
                    "total_executions": 0,
                    "successful_executions": 0,
                    "total_time": 0.0,
                    "success_rate": 0.0,
                    "avg_time": 0.0
                }
            
            metrics = self._performance_cache[tool_name]
            metrics["total_executions"] += 1
            metrics["total_time"] += execution_time
            
            if success:
                metrics["successful_executions"] += 1
            
            # Update derived metrics
            metrics["success_rate"] = metrics["successful_executions"] / metrics["total_executions"]
            metrics["avg_time"] = metrics["total_time"] / metrics["total_executions"]
            
            # Update analytics service if available
            if self.analytics_service:
                self.analytics_service.record_tool_usage(
                    tool_name=tool_name,
                    query=query,
                    success=success,
                    response_quality=response_quality,
                    response_time=execution_time
                )
                
        except Exception as e:
            self.logger.error(f"Failed to update performance metrics for {tool_name}: {e}")
    
    def get_tool_recommendations(
        self, 
        query: str, 
        available_tools: List[str], 
        max_recommendations: int = 5
    ) -> List[ToolScore]:
        """
        Get tool recommendations using analytics service.
        
        Args:
            query: User query
            available_tools: List of available tool names
            max_recommendations: Maximum number of recommendations
            
        Returns:
            List of tool scores with recommendations
        """
        try:
            if self.analytics_service:
                # Get recommendations from analytics service
                recommendations = self.analytics_service.get_tool_recommendations(
                    query=query,
                    available_tools=available_tools,
                    max_recommendations=max_recommendations
                )
                
                # Convert to ToolScore objects
                tool_scores = []
                for rec in recommendations:
                    # Get base score using our scoring algorithm
                    base_scores = self.score_tools(query, [rec.tool_name])
                    base_score = base_scores[0].base_score if base_scores else 0.5
                    
                    tool_score = ToolScore(
                        tool_name=rec.tool_name,
                        base_score=base_score,
                        context_boost=0.0,
                        performance_score=rec.expected_performance,
                        final_score=rec.confidence_score,
                        reasoning=rec.reason
                    )
                    tool_scores.append(tool_score)
                
                return tool_scores
            else:
                # Fallback to basic scoring
                return self.score_tools(query, available_tools)[:max_recommendations]
                
        except Exception as e:
            self.logger.error(f"Failed to get tool recommendations: {e}")
            # Fallback to basic scoring
            return self.score_tools(query, available_tools)[:max_recommendations]