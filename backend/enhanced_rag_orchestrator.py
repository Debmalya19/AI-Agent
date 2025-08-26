"""
Enhanced RAG Orchestrator with Memory Layer Integration
Integrates with the memory layer for context-aware search and tool optimization
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import KnowledgeEntry, SupportIntent, SupportResponse
from backend.tools import context_memory, analyze_query_type
from backend.memory_layer_manager import MemoryLayerManager
from backend.context_retrieval_engine import ContextRetrievalEngine
from backend.tool_usage_analytics import ToolUsageAnalytics
from backend.memory_models import ConversationEntryDTO
import logging
from datetime import datetime, timedelta
import time

class EnhancedRAGOrchestrator:
    """Enhanced RAG orchestrator with memory layer integration and intelligent search"""
    
    def __init__(self, memory_manager: Optional[MemoryLayerManager] = None,
                 context_engine: Optional[ContextRetrievalEngine] = None,
                 analytics: Optional[ToolUsageAnalytics] = None):
        self.logger = logging.getLogger(__name__)
        
        # Legacy context memory for backward compatibility
        self.context_memory = context_memory
        
        # Memory layer components
        self.memory_manager = memory_manager or MemoryLayerManager()
        self.context_engine = context_engine or ContextRetrievalEngine()
        self.analytics = analytics or ToolUsageAnalytics()
        
        # Performance tracking
        self._operation_times = {}
        
        self.logger.info("Enhanced RAG Orchestrator initialized with memory layer integration")
    
    def search_with_context(self, query: str, user_id: str = "default", max_results: int = 3, 
                          include_context: bool = True, tools_used: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Enhanced RAG search with memory layer integration and intelligent result ranking
        
        Args:
            query: Search query
            user_id: User identifier for personalized context
            max_results: Maximum number of results to return
            include_context: Whether to include conversation context
            tools_used: List of tools used in this search (for analytics)
        """
        start_time = time.time()
        
        try:
            results = []
            
            # Get enhanced context from memory layer
            if include_context:
                enhanced_context = self._get_enhanced_context(query, user_id)
                if enhanced_context:
                    results.extend(enhanced_context)
            
            # Get legacy context for backward compatibility
            legacy_context = self._get_legacy_context(query)
            if legacy_context:
                results.extend(legacy_context)
            
            # Search support intents with enhanced matching
            support_results = self._search_support_intents(query)
            results.extend(support_results)
            
            # Search knowledge entries with semantic matching
            knowledge_results = self._search_knowledge_entries(query, max_results=max_results)
            results.extend(knowledge_results)
            
            # Apply memory-aware ranking
            ranked_results = self._rank_results_with_memory(results, query, user_id)
            
            # Store search context in memory layer
            self._store_search_context(query, user_id, ranked_results, tools_used)
            
            # Track performance
            duration = time.time() - start_time
            self._track_operation_time('search_with_context', duration)
            
            self.logger.info(f"Enhanced RAG search completed in {duration:.3f}s with {len(ranked_results)} results")
            
            return ranked_results[:max_results]
            
        except Exception as e:
            self.logger.error(f"Enhanced RAG search error: {e}")
            return []
    
    def _search_support_intents(self, query: str) -> List[Dict[str, Any]]:
        """Search support intents with enhanced matching"""
        try:
            with SessionLocal() as db:
                intents = db.query(SupportIntent).all()
                query_lower = query.lower()
                query_words = set(query_lower.split())
                
                support_results = []
                
                for intent in intents:
                    intent_lower = intent.intent_name.lower()
                    intent_words = set(intent_lower.split())
                    
                    # Calculate similarity score
                    score = self._calculate_similarity_score(query_words, intent_words, query_lower, intent_lower)
                    
                    if score >= 1.5:  # Threshold for relevance
                        response = db.query(SupportResponse).filter(
                            SupportResponse.intent_id == intent.intent_id
                        ).first()
                        
                        if response:
                            support_results.append({
                                'content': response.response_text,
                                'source': f'support_intent_{intent.intent_name}',
                                'confidence': min(score / 5.0, 1.0),  # Normalize score
                                'search_method': 'enhanced_intent_matching',
                                'timestamp': datetime.now()
                            })
                
                return support_results
                
        except Exception as e:
            self.logger.error(f"Support intent search error: {e}")
            return []
    
    def _search_knowledge_entries(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search knowledge entries with semantic matching"""
        try:
            with SessionLocal() as db:
                entries = db.query(KnowledgeEntry).all()
                query_lower = query.lower()
                query_words = set(query_lower.split())
                
                knowledge_results = []
                
                for entry in entries:
                    title_lower = entry.title.lower()
                    content_lower = entry.content.lower()
                    
                    # Calculate relevance score
                    title_score = self._calculate_similarity_score(query_words, set(title_lower.split()), query_lower, title_lower)
                    content_score = self._calculate_similarity_score(query_words, set(content_lower.split()), query_lower, content_lower)
                    
                    # Combined score with title weighted higher
                    combined_score = (title_score * 0.7) + (content_score * 0.3)
                    
                    if combined_score >= 1.0:
                        knowledge_results.append({
                            'content': entry.content,
                            'source': f'knowledge_entry_{entry.title}',
                            'confidence': min(combined_score / 5.0, 1.0),
                            'search_method': 'semantic_knowledge_search',
                            'timestamp': datetime.now()
                        })
                
                # Sort by confidence and return top results
                knowledge_results.sort(key=lambda x: x['confidence'], reverse=True)
                return knowledge_results[:max_results]
                
        except Exception as e:
            self.logger.error(f"Knowledge entries search error: {e}")
            return []
    
    def _calculate_similarity_score(self, query_words: set, target_words: set, query_text: str, target_text: str) -> float:
        """Calculate similarity score between query and target"""
        score = 0.0
        
        # Exact word matches
        common_words = query_words.intersection(target_words)
        score += len(common_words) * 0.5
        
        # Phrase matches
        for word in query_words:
            if word in target_text:
                score += 0.3
        
        # Semantic matches (common synonyms and related terms)
        semantic_matches = {
            'support': ['help', 'assist', 'customer service'],
            'hours': ['time', 'schedule', 'availability'],
            'plan': ['package', 'subscription', 'tariff'],
            'upgrade': ['change', 'modify', 'switch'],
            'data': ['internet', 'mobile data', 'bandwidth'],
            'wifi': ['wireless', 'internet', 'connection'],
            'phone': ['mobile', 'cell', 'handset'],
            'billing': ['payment', 'invoice', 'charge']
        }
        
        for query_word, synonyms in semantic_matches.items():
            if query_word in query_text.lower():
                for synonym in synonyms:
                    if synonym in target_text.lower():
                        score += 0.4
                        break
        
        # Context-specific scoring
        if any(word in query_text.lower() for word in ['urgent', 'emergency', 'critical']):
            if any(word in target_text.lower() for word in ['support', 'help', 'contact']):
                score += 1.0
        
        return score
    
    def _rank_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Rank results by relevance and freshness"""
        try:
            # Add ranking factors
            for result in results:
                # Base confidence
                rank_score = result.get('confidence', 0.0)
                
                # Recency bonus (newer results get slight boost)
                if 'timestamp' in result:
                    age_hours = (datetime.now() - result['timestamp']).total_seconds() / 3600
                    if age_hours < 24:  # Within 24 hours
                        rank_score += 0.1
                
                # Source priority
                source_priority = {
                    'conversation_memory': 0.2,
                    'support_intent': 0.3,
                    'knowledge_entry': 0.2,
                    'bt_scraping': 0.4
                }
                
                for source_type, priority in source_priority.items():
                    if source_type in result.get('source', ''):
                        rank_score += priority
                        break
                
                # Query type matching
                query_type = analyze_query_type(query)
                if query_type in ['support_hours', 'contact'] and 'support' in result.get('source', ''):
                    rank_score += 0.2
                elif query_type in ['plans', 'pricing'] and 'bt' in result.get('source', ''):
                    rank_score += 0.2
                
                result['rank_score'] = rank_score
            
            # Sort by rank score
            results.sort(key=lambda x: x.get('rank_score', 0.0), reverse=True)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Result ranking error: {e}")
            return results
    
    def _format_context_results(self, context_entries: List[Dict[str, Any]]) -> str:
        """Format context results for display"""
        if not context_entries:
            return ""
        
        formatted = "Based on our recent conversation:\n"
        for entry in context_entries:
            formatted += f"- Previous question: {entry['user_query']}\n"
            formatted += f"  Answer: {entry['response'][:150]}...\n\n"
        
        return formatted
    
    def get_context_summary(self, query: str, user_id: str = "default") -> str:
        """Get a summary of relevant context for a query using memory layer"""
        try:
            # Get enhanced context from memory layer
            enhanced_context = self.context_engine.get_relevant_context(query, user_id, limit=3)
            
            if not enhanced_context:
                # Fallback to legacy context
                recent_context = self.context_memory.get_recent_context(query, limit=2)
                if not recent_context:
                    return ""
                
                summary = "Context from recent conversations:\n"
                for ctx in recent_context:
                    summary += f"- {ctx['user_query']}: {ctx['response'][:100]}...\n"
                return summary
            
            # Format enhanced context
            summary = "Relevant context from conversation history:\n"
            for ctx in enhanced_context:
                if ctx.context_type == "user_message":
                    summary += f"- Previous question: {ctx.content[:100]}...\n"
                elif ctx.context_type == "bot_response":
                    summary += f"- Previous answer: {ctx.content[:100]}...\n"
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Context summary error: {e}")
            return ""
    
    def _get_enhanced_context(self, query: str, user_id: str) -> List[Dict[str, Any]]:
        """Get context from enhanced memory layer"""
        try:
            context_entries = self.context_engine.get_relevant_context(query, user_id, limit=3)
            
            results = []
            for entry in context_entries:
                if entry.relevance_score > 0.3:  # Minimum relevance threshold
                    result = {
                        'content': self._format_enhanced_context_entry(entry),
                        'source': f'memory_layer_{entry.source}',
                        'confidence': entry.relevance_score,
                        'search_method': 'enhanced_context_retrieval',
                        'timestamp': entry.timestamp,
                        'context_type': entry.context_type
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting enhanced context: {e}")
            return []
    
    def _get_legacy_context(self, query: str) -> List[Dict[str, Any]]:
        """Get context from legacy memory for backward compatibility"""
        try:
            recent_context = self.context_memory.get_recent_context(query, limit=2)
            
            results = []
            for ctx in recent_context:
                result = {
                    'content': f"Previous conversation:\nQ: {ctx['user_query']}\nA: {ctx['response'][:200]}...",
                    'source': 'legacy_conversation_memory',
                    'confidence': 0.7,
                    'search_method': 'legacy_context_memory',
                    'timestamp': ctx['timestamp']
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting legacy context: {e}")
            return []
    
    def _format_enhanced_context_entry(self, entry) -> str:
        """Format enhanced context entry for display"""
        if entry.context_type == "user_message":
            return f"Previous question: {entry.content}"
        elif entry.context_type == "bot_response":
            return f"Previous answer: {entry.content[:300]}..."
        else:
            return entry.content
    
    def _rank_results_with_memory(self, results: List[Dict[str, Any]], query: str, user_id: str) -> List[Dict[str, Any]]:
        """Enhanced result ranking using memory layer insights"""
        try:
            # Apply base ranking
            ranked_results = self._rank_results(results, query)
            
            # Apply memory-based boosting
            for result in ranked_results:
                # Boost results from memory layer
                if 'memory_layer' in result.get('source', ''):
                    result['rank_score'] = result.get('rank_score', result.get('confidence', 0.0)) * 1.2
                
                # Boost results with high context relevance
                if result.get('context_type') == 'bot_response' and result.get('confidence', 0) > 0.8:
                    result['rank_score'] = result.get('rank_score', result.get('confidence', 0.0)) * 1.1
            
            # Re-sort by updated rank scores
            ranked_results.sort(key=lambda x: x.get('rank_score', x.get('confidence', 0.0)), reverse=True)
            
            return ranked_results
            
        except Exception as e:
            self.logger.error(f"Error in memory-aware ranking: {e}")
            return self._rank_results(results, query)  # Fallback to base ranking
    
    def _store_search_context(self, query: str, user_id: str, results: List[Dict[str, Any]], 
                            tools_used: Optional[List[str]] = None):
        """Store search context in memory layer for future use"""
        try:
            # Store in legacy memory for backward compatibility
            self.context_memory.add_context(f"query_{hash(query)}", {
                'query': query,
                'results_count': len(results),
                'timestamp': datetime.now()
            }, ttl=3600)
            
            # Store enhanced context in memory layer
            if results:
                context_data = {
                    'query': query,
                    'results_summary': [
                        {
                            'source': r.get('source', ''),
                            'confidence': r.get('confidence', 0.0),
                            'content_preview': r.get('content', '')[:100]
                        }
                        for r in results[:3]
                    ],
                    'search_timestamp': datetime.now().isoformat(),
                    'tools_used': tools_used or []
                }
                
                self.context_engine.cache_context(
                    key=f"search_{hash(query)}_{user_id}",
                    context_data=context_data,
                    context_type="search_results",
                    ttl_hours=24,
                    user_id=user_id,
                    relevance_score=0.8
                )
            
        except Exception as e:
            self.logger.error(f"Error storing search context: {e}")
    
    def _track_operation_time(self, operation: str, duration: float):
        """Track operation execution time for performance monitoring"""
        if operation not in self._operation_times:
            self._operation_times[operation] = []
        
        self._operation_times[operation].append(duration)
        
        # Keep only last 100 measurements
        if len(self._operation_times[operation]) > 100:
            self._operation_times[operation] = self._operation_times[operation][-100:]
    
    def get_tool_recommendations(self, query: str, available_tools: List[str], 
                               user_id: str = "default") -> List[str]:
        """Get tool recommendations using analytics"""
        try:
            recommendations = self.analytics.get_tool_recommendations(
                query=query,
                available_tools=available_tools,
                max_recommendations=len(available_tools)
            )
            
            # Extract tool names in order of confidence
            recommended_tools = [rec.tool_name for rec in recommendations]
            
            # Add any tools not in recommendations
            for tool in available_tools:
                if tool not in recommended_tools:
                    recommended_tools.append(tool)
            
            self.logger.info(f"Tool recommendations for query: {recommended_tools[:3]}")
            return recommended_tools
            
        except Exception as e:
            self.logger.error(f"Error getting tool recommendations: {e}")
            # Fallback to legacy tool selection
            query_type = analyze_query_type(query)
            return self.context_memory.get_tool_usage_pattern(query_type)
    
    def record_tool_usage(self, tool_name: str, query: str, success: bool, 
                         response_quality: float, response_time: Optional[float] = None):
        """Record tool usage for analytics"""
        try:
            self.analytics.record_tool_usage(
                tool_name=tool_name,
                query=query,
                success=success,
                response_quality=response_quality,
                response_time=response_time
            )
            
        except Exception as e:
            self.logger.error(f"Error recording tool usage: {e}")
    
    def store_conversation(self, session_id: str, user_id: str, user_message: str, 
                         bot_response: str, tools_used: List[str], 
                         response_quality_score: float = 0.8):
        """Store conversation in memory layer"""
        try:
            conversation = ConversationEntryDTO(
                session_id=session_id,
                user_id=user_id,
                user_message=user_message,
                bot_response=bot_response,
                tools_used=tools_used,
                tool_performance={tool: 0.8 for tool in tools_used},  # Default performance
                context_used=[],
                response_quality_score=response_quality_score,
                timestamp=datetime.now()
            )
            
            success = self.memory_manager.store_conversation(conversation)
            if success:
                self.logger.info(f"Stored conversation for user {user_id}")
            
            # Also store in legacy memory for backward compatibility
            self.context_memory.add_conversation(user_message, bot_response, tools_used)
            
        except Exception as e:
            self.logger.error(f"Error storing conversation: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        try:
            stats = {
                'operation_times': {},
                'memory_stats': self.memory_manager.get_memory_stats().to_dict(),
                'cache_stats': self.context_engine.get_cache_stats()
            }
            
            # Calculate average operation times
            for op, times in self._operation_times.items():
                if times:
                    stats['operation_times'][op] = {
                        'avg_time': sum(times) / len(times),
                        'count': len(times),
                        'last_time': times[-1]
                    }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting performance stats: {e}")
            return {}

# Global instance with memory layer integration
enhanced_rag = EnhancedRAGOrchestrator()

def search_with_priority(query: str, user_id: str = "default", max_results: int = 3, 
                        tools_used: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Enhanced RAG search with memory layer integration and intelligent result ranking.
    This is the main function to use for RAG operations.
    
    Args:
        query: Search query
        user_id: User identifier for personalized context
        max_results: Maximum number of results to return
        tools_used: List of tools used in this search (for analytics)
    """
    return enhanced_rag.search_with_context(query, user_id, max_results, include_context=True, tools_used=tools_used)

def search_without_context(query: str, user_id: str = "default", max_results: int = 3) -> List[Dict[str, Any]]:
    """
    RAG search without context memory (for fresh searches).
    """
    return enhanced_rag.search_with_context(query, user_id, max_results, include_context=False)

def get_context_summary(query: str, user_id: str = "default") -> str:
    """
    Get a summary of relevant context for a query using memory layer.
    """
    return enhanced_rag.get_context_summary(query, user_id)

def get_tool_recommendations(query: str, available_tools: List[str], user_id: str = "default") -> List[str]:
    """
    Get tool recommendations based on query analysis and historical performance.
    """
    return enhanced_rag.get_tool_recommendations(query, available_tools, user_id)

def record_tool_usage(tool_name: str, query: str, success: bool, response_quality: float, 
                     response_time: Optional[float] = None):
    """
    Record tool usage for analytics and future optimization.
    """
    enhanced_rag.record_tool_usage(tool_name, query, success, response_quality, response_time)

def store_conversation(session_id: str, user_id: str, user_message: str, bot_response: str, 
                      tools_used: List[str], response_quality_score: float = 0.8):
    """
    Store conversation in memory layer for context-aware responses.
    """
    enhanced_rag.store_conversation(session_id, user_id, user_message, bot_response, 
                                  tools_used, response_quality_score)

def get_performance_stats() -> Dict[str, Any]:
    """
    Get comprehensive performance statistics from the enhanced RAG system.
    """
    return enhanced_rag.get_performance_stats()
