"""
ContextRetriever - Wrapper around existing context retrieval with UI enhancements.
"""

import asyncio
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from .models import BaseContextRetriever, ContextEntry
from .exceptions import ContextRetrievalError

# Import existing components
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from context_retrieval_engine import ContextRetrievalEngine
    from memory_layer_manager import MemoryLayerManager
    from memory_models import ContextEntryDTO
except ImportError:
    # Fallback for testing or when components aren't available
    ContextRetrievalEngine = None
    MemoryLayerManager = None
    ContextEntryDTO = None


class ContextRetriever(BaseContextRetriever):
    """
    Wrapper around existing context retrieval with UI-specific enhancements.
    
    Integrates with existing ContextRetrievalEngine and MemoryLayerManager
    while adding UI-specific features like summarization and effectiveness tracking.
    """
    
    def __init__(
        self, 
        context_engine: Optional[ContextRetrievalEngine] = None, 
        memory_manager: Optional[MemoryLayerManager] = None,
        max_context_length: int = 4000,
        cache_ttl_seconds: int = 300,
        compression_threshold: int = 8000
    ):
        """
        Initialize ContextRetriever.
        
        Args:
            context_engine: Existing ContextRetrievalEngine instance
            memory_manager: Existing MemoryLayerManager instance
            max_context_length: Maximum context length for summarization
            cache_ttl_seconds: Cache time-to-live in seconds
            compression_threshold: Context length threshold for compression
        """
        self.context_engine = context_engine
        self.memory_manager = memory_manager
        self.max_context_length = max_context_length
        self.cache_ttl_seconds = cache_ttl_seconds
        self.compression_threshold = compression_threshold
        
        # Context caching with TTL
        self._context_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # Context effectiveness tracking
        self._effectiveness_tracking: Dict[str, Dict[str, Any]] = {}
        
        # Context window management
        self._context_priorities: Dict[str, float] = {}
        self._compressed_contexts: Dict[str, str] = {}
        
        # Performance metrics
        self._retrieval_times: List[float] = []
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_contexts_processed = 0
        
        # Compression statistics
        self._compression_stats = {
            'total_compressed': 0,
            'original_sizes': [],
            'compressed_sizes': []
        }
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("ContextRetriever initialized with UI enhancements")
    
    async def get_relevant_context(
        self, 
        query: str, 
        user_id: str, 
        limit: int = 10
    ) -> List[ContextEntry]:
        """
        Get relevant context for a query with intelligent caching and prioritization.
        
        Args:
            query: Query to find context for
            user_id: User identifier
            limit: Maximum number of context entries
            
        Returns:
            List of relevant context entries
            
        Raises:
            ContextRetrievalError: If context retrieval fails
        """
        start_time = datetime.now()
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(query, user_id, limit)
            
            # Check cache first
            cached_context = self._get_cached_context(cache_key)
            if cached_context:
                self._cache_hits += 1
                self.logger.debug(f"Cache hit for context retrieval: {cache_key}")
                return cached_context[:limit]
            
            self._cache_misses += 1
            context_entries = []
            
            # Get context from context engine if available
            if self.context_engine:
                try:
                    engine_context = await self._get_engine_context(query, user_id, limit * 2)
                    context_entries.extend(engine_context)
                    self.logger.debug(f"Retrieved {len(engine_context)} entries from context engine")
                except Exception as e:
                    self.logger.warning(f"Context engine retrieval failed: {e}")
            
            # Get context from memory manager if available
            if self.memory_manager:
                try:
                    memory_context = await self._get_memory_context(user_id, query, limit)
                    context_entries.extend(memory_context)
                    self.logger.debug(f"Retrieved {len(memory_context)} entries from memory manager")
                except Exception as e:
                    self.logger.warning(f"Memory context retrieval failed: {e}")
            
            # Remove duplicates and apply intelligent ranking
            unique_context = self._deduplicate_context(context_entries)
            ranked_context = self._apply_intelligent_ranking(unique_context, query, user_id)
            
            # Apply context window management
            optimized_context = self._optimize_context_window(ranked_context, limit)
            
            # Cache results with TTL
            self._cache_context(cache_key, optimized_context)
            
            # Track performance
            retrieval_time = (datetime.now() - start_time).total_seconds()
            self._retrieval_times.append(retrieval_time)
            if len(self._retrieval_times) > 100:
                self._retrieval_times = self._retrieval_times[-100:]
            
            # Update total contexts processed
            self._total_contexts_processed += len(optimized_context)
            
            self.logger.info(f"Retrieved {len(optimized_context)} context entries in {retrieval_time:.3f}s")
            
            return optimized_context
            
        except Exception as e:
            self.logger.error(f"Context retrieval failed: {e}")
            raise ContextRetrievalError(
                f"Failed to retrieve context: {str(e)}",
                user_id=user_id,
                query=query,
                context={"error": str(e), "retrieval_time": (datetime.now() - start_time).total_seconds()}
            )
    
    def summarize_context(self, context: List[ContextEntry]) -> str:
        """
        Summarize context entries for UI display with intelligent compression.
        
        Args:
            context: List of context entries to summarize
            
        Returns:
            Summarized context string optimized for UI display
        """
        if not context:
            return "No relevant context found."
        
        # Calculate total length
        total_length = sum(len(entry.content) for entry in context)
        
        if total_length <= self.max_context_length:
            # Return full context if within limits
            return self._format_full_context(context)
        elif total_length <= self.compression_threshold:
            # Apply light compression
            return self._create_compressed_summary(context)
        else:
            # Apply heavy compression for large contexts
            return self._create_context_summary(context)
    
    def track_context_usage(self, context: List[ContextEntry], effectiveness: float) -> None:
        """
        Track context usage effectiveness with detailed analytics.
        
        Args:
            context: Context entries that were used
            effectiveness: Effectiveness score (0.0 to 1.0)
        """
        timestamp = datetime.now()
        
        for entry in context:
            source = entry.source
            context_type = entry.context_type
            
            # Initialize tracking if not exists
            if source not in self._effectiveness_tracking:
                self._effectiveness_tracking[source] = {
                    "total_uses": 0,
                    "total_effectiveness": 0.0,
                    "average_effectiveness": 0.0,
                    "last_used": None,
                    "context_types": {},
                    "effectiveness_history": [],
                    "relevance_scores": []
                }
            
            tracking = self._effectiveness_tracking[source]
            
            # Update overall statistics
            tracking["total_uses"] += 1
            tracking["total_effectiveness"] += effectiveness
            tracking["average_effectiveness"] = (
                tracking["total_effectiveness"] / tracking["total_uses"]
            )
            tracking["last_used"] = timestamp
            
            # Track by context type
            if context_type not in tracking["context_types"]:
                tracking["context_types"][context_type] = {
                    "uses": 0,
                    "effectiveness": 0.0,
                    "average": 0.0
                }
            
            type_tracking = tracking["context_types"][context_type]
            type_tracking["uses"] += 1
            type_tracking["effectiveness"] += effectiveness
            type_tracking["average"] = type_tracking["effectiveness"] / type_tracking["uses"]
            
            # Keep effectiveness history (last 50 entries)
            tracking["effectiveness_history"].append({
                "timestamp": timestamp,
                "effectiveness": effectiveness,
                "relevance_score": entry.relevance_score
            })
            if len(tracking["effectiveness_history"]) > 50:
                tracking["effectiveness_history"] = tracking["effectiveness_history"][-50:]
            
            # Track relevance scores for analysis
            tracking["relevance_scores"].append(entry.relevance_score)
            if len(tracking["relevance_scores"]) > 100:
                tracking["relevance_scores"] = tracking["relevance_scores"][-100:]
            
            # Update context priorities based on effectiveness
            self._update_context_priority(source, effectiveness, entry.relevance_score)
    
    async def _get_memory_context(
        self, 
        user_id: str, 
        query: str, 
        limit: int
    ) -> List[ContextEntry]:
        """Get context from memory manager with proper integration."""
        if not self.memory_manager:
            return []
        
        try:
            # Use the existing memory manager's retrieve_context method
            context_dtos = self.memory_manager.retrieve_context(query, user_id, limit)
            
            # Convert ContextEntryDTO to ContextEntry
            memory_entries = []
            for dto in context_dtos:
                entry = ContextEntry(
                    content=dto.content,
                    source=dto.source,
                    relevance_score=dto.relevance_score,
                    timestamp=dto.timestamp,
                    context_type=dto.context_type,
                    metadata=dto.metadata
                )
                memory_entries.append(entry)
            
            return memory_entries
            
        except Exception as e:
            self.logger.error(f"Memory context retrieval failed: {e}")
            return []
    
    async def _get_engine_context(
        self, 
        query: str, 
        user_id: str, 
        limit: int
    ) -> List[ContextEntry]:
        """Get context from context engine with proper integration."""
        if not self.context_engine:
            return []
        
        try:
            # Use the existing context engine's get_relevant_context method
            context_dtos = self.context_engine.get_relevant_context(
                query=query,
                user_id=user_id,
                limit=limit
            )
            
            # Convert ContextEntryDTO to ContextEntry
            engine_entries = []
            for dto in context_dtos:
                entry = ContextEntry(
                    content=dto.content,
                    source=dto.source,
                    relevance_score=dto.relevance_score,
                    timestamp=dto.timestamp,
                    context_type=dto.context_type,
                    metadata=dto.metadata
                )
                engine_entries.append(entry)
            
            return engine_entries
            
        except Exception as e:
            self.logger.error(f"Context engine retrieval failed: {e}")
            return []
    
    def _deduplicate_context(self, context_entries: List[ContextEntry]) -> List[ContextEntry]:
        """Remove duplicate context entries."""
        seen_content = set()
        unique_entries = []
        
        for entry in context_entries:
            # Use content hash for deduplication
            content_key = f"{entry.content[:100]}:{entry.source}"
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_entries.append(entry)
        
        return unique_entries
    
    def _format_full_context(self, context: List[ContextEntry]) -> str:
        """Format full context for display."""
        sections = []
        
        for i, entry in enumerate(context, 1):
            section = f"Context {i} (from {entry.source}):\n{entry.content}"
            sections.append(section)
        
        return "\n\n".join(sections)
    
    def _create_context_summary(self, context: List[ContextEntry]) -> str:
        """Create an intelligent summary of context entries."""
        # Group by source and context type
        by_source = {}
        by_type = {}
        
        for entry in context:
            # Group by source
            if entry.source not in by_source:
                by_source[entry.source] = []
            by_source[entry.source].append(entry)
            
            # Group by context type
            if entry.context_type not in by_type:
                by_type[entry.context_type] = []
            by_type[entry.context_type].append(entry)
        
        summary_parts = []
        
        # Prioritize by effectiveness if available
        sorted_sources = sorted(
            by_source.items(),
            key=lambda x: self._get_source_priority(x[0]),
            reverse=True
        )
        
        for source, entries in sorted_sources[:3]:  # Top 3 sources
            # Take the highest scoring entries from each source
            top_entries = sorted(entries, key=lambda x: x.relevance_score, reverse=True)[:2]
            
            source_summary = f"From {source}:"
            for entry in top_entries:
                # Intelligent content truncation
                content = self._truncate_content_intelligently(entry.content, 150)
                source_summary += f"\n- {content}"
            
            summary_parts.append(source_summary)
        
        # Add context type summary if diverse
        if len(by_type) > 2:
            type_summary = f"Context includes: {', '.join(by_type.keys())}"
            summary_parts.append(type_summary)
        
        return "\n\n".join(summary_parts)
    
    def _create_compressed_summary(self, context: List[ContextEntry]) -> str:
        """Create a compressed summary for medium-sized contexts."""
        # Sort by relevance and effectiveness
        sorted_context = sorted(
            context,
            key=lambda x: (x.relevance_score, self._get_source_priority(x.source)),
            reverse=True
        )
        
        summary_parts = []
        total_length = 0
        
        for entry in sorted_context:
            if total_length >= self.max_context_length:
                break
            
            # Compress content while preserving key information
            compressed_content = self._compress_content(entry.content, 300)
            
            if total_length + len(compressed_content) <= self.max_context_length:
                summary_parts.append(f"[{entry.context_type}] {compressed_content}")
                total_length += len(compressed_content)
        
        if len(sorted_context) > len(summary_parts):
            summary_parts.append(f"... and {len(sorted_context) - len(summary_parts)} more entries")
        
        return "\n\n".join(summary_parts)
    
    def get_context_effectiveness_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get context effectiveness statistics."""
        return self._effectiveness_tracking.copy()
    
    def clear_context_cache(self) -> None:
        """Clear the context cache."""
        self._context_cache.clear()
    
    def _generate_cache_key(self, query: str, user_id: str, limit: int) -> str:
        """Generate cache key for context retrieval."""
        key_parts = [query[:100], user_id, str(limit)]
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_context(self, cache_key: str) -> Optional[List[ContextEntry]]:
        """Get context from cache if not expired."""
        if cache_key not in self._context_cache:
            return None
        
        # Check TTL
        if cache_key in self._cache_timestamps:
            cache_time = self._cache_timestamps[cache_key]
            if (datetime.now() - cache_time).total_seconds() > self.cache_ttl_seconds:
                # Expired, remove from cache
                del self._context_cache[cache_key]
                del self._cache_timestamps[cache_key]
                return None
        
        return self._context_cache[cache_key]["context"]
    
    def _cache_context(self, cache_key: str, context: List[ContextEntry]) -> None:
        """Cache context with metadata."""
        self._context_cache[cache_key] = {
            "context": context,
            "timestamp": datetime.now(),
            "access_count": 1
        }
        self._cache_timestamps[cache_key] = datetime.now()
        
        # Cleanup old cache entries if too many
        if len(self._context_cache) > 100:
            self._cleanup_cache()
    
    def _cleanup_cache(self) -> None:
        """Clean up old cache entries."""
        # Remove oldest 20% of entries
        sorted_keys = sorted(
            self._cache_timestamps.keys(),
            key=lambda k: self._cache_timestamps[k]
        )
        
        keys_to_remove = sorted_keys[:len(sorted_keys) // 5]
        for key in keys_to_remove:
            if key in self._context_cache:
                del self._context_cache[key]
            if key in self._cache_timestamps:
                del self._cache_timestamps[key]
    
    def _apply_intelligent_ranking(
        self, 
        context: List[ContextEntry], 
        query: str, 
        user_id: str
    ) -> List[ContextEntry]:
        """Apply intelligent ranking based on multiple factors."""
        for entry in context:
            # Base relevance score from the engine
            base_score = entry.relevance_score
            
            # Apply effectiveness boost
            effectiveness_boost = self._get_effectiveness_boost(entry.source)
            
            # Apply recency boost
            recency_boost = self._get_recency_boost(entry.timestamp)
            
            # Apply context type boost
            type_boost = self._get_context_type_boost(entry.context_type, query)
            
            # Calculate final score
            final_score = base_score * (1 + effectiveness_boost + recency_boost + type_boost)
            entry.relevance_score = min(final_score, 1.0)  # Cap at 1.0
        
        # Sort by final relevance score
        return sorted(context, key=lambda x: x.relevance_score, reverse=True)
    
    def _optimize_context_window(
        self, 
        context: List[ContextEntry], 
        limit: int
    ) -> List[ContextEntry]:
        """Optimize context window for performance and relevance."""
        if len(context) <= limit:
            return context
        
        # Prioritize high-scoring, diverse contexts
        optimized = []
        seen_sources = set()
        seen_types = set()
        
        # First pass: ensure diversity
        for entry in context:
            if len(optimized) >= limit:
                break
            
            # Prefer diverse sources and types
            source_penalty = 0.1 if entry.source in seen_sources else 0
            type_penalty = 0.05 if entry.context_type in seen_types else 0
            
            adjusted_score = entry.relevance_score - source_penalty - type_penalty
            
            if adjusted_score > 0.3 or len(optimized) < limit // 2:
                optimized.append(entry)
                seen_sources.add(entry.source)
                seen_types.add(entry.context_type)
        
        # Second pass: fill remaining slots with highest scores
        remaining_context = [e for e in context if e not in optimized]
        remaining_slots = limit - len(optimized)
        
        if remaining_slots > 0:
            top_remaining = sorted(
                remaining_context,
                key=lambda x: x.relevance_score,
                reverse=True
            )[:remaining_slots]
            optimized.extend(top_remaining)
        
        return optimized
    
    def _get_effectiveness_boost(self, source: str) -> float:
        """Get effectiveness boost for a source."""
        if source not in self._effectiveness_tracking:
            return 0.0
        
        tracking = self._effectiveness_tracking[source]
        avg_effectiveness = tracking.get("average_effectiveness", 0.0)
        
        # Boost based on effectiveness (max 20% boost)
        return min(avg_effectiveness * 0.2, 0.2)
    
    def _get_recency_boost(self, timestamp: datetime) -> float:
        """Get recency boost based on timestamp."""
        if not timestamp:
            return 0.0
        
        # Calculate age in hours
        age_hours = (datetime.now(timezone.utc) - timestamp.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        
        # Recent contexts get boost (max 15% boost)
        if age_hours < 1:
            return 0.15
        elif age_hours < 24:
            return 0.10
        elif age_hours < 168:  # 1 week
            return 0.05
        else:
            return 0.0
    
    def _get_context_type_boost(self, context_type: str, query: str) -> float:
        """Get context type boost based on query characteristics."""
        query_lower = query.lower()
        
        # Boost certain context types based on query content
        if "error" in query_lower or "problem" in query_lower:
            if context_type in ["error_context", "troubleshooting"]:
                return 0.1
        
        if "how to" in query_lower or "help" in query_lower:
            if context_type in ["knowledge_base", "documentation"]:
                return 0.1
        
        if "previous" in query_lower or "before" in query_lower:
            if context_type in ["conversation_history", "user_message"]:
                return 0.1
        
        return 0.0
    
    def _get_source_priority(self, source: str) -> float:
        """Get priority score for a source."""
        if source in self._context_priorities:
            return self._context_priorities[source]
        
        # Default priorities based on source type
        if "conversation" in source:
            return 0.8
        elif "knowledge" in source or "engine" in source:
            return 0.7
        elif "cache" in source:
            return 0.6
        else:
            return 0.5
    
    def _update_context_priority(self, source: str, effectiveness: float, relevance: float) -> None:
        """Update context priority based on usage effectiveness."""
        if source not in self._context_priorities:
            self._context_priorities[source] = 0.5
        
        # Update priority using exponential moving average
        current_priority = self._context_priorities[source]
        new_score = (effectiveness + relevance) / 2
        
        # EMA with alpha = 0.1
        self._context_priorities[source] = current_priority * 0.9 + new_score * 0.1
    
    def _truncate_content_intelligently(self, content: str, max_length: int) -> str:
        """Intelligently truncate content preserving key information."""
        if len(content) <= max_length:
            return content
        
        # Try to break at sentence boundaries
        sentences = content.split('. ')
        if len(sentences) > 1:
            truncated = ""
            for sentence in sentences:
                if len(truncated + sentence + '. ') <= max_length - 3:
                    truncated += sentence + '. '
                else:
                    break
            
            if truncated:
                return truncated.rstrip() + "..."
        
        # Fallback to simple truncation
        return content[:max_length - 3] + "..."
    
    def _compress_content(self, content: str, target_length: int) -> str:
        """Compress content while preserving meaning."""
        if len(content) <= target_length:
            return content
        
        # Simple compression: remove redundant words and phrases
        words = content.split()
        
        # Remove common filler words
        filler_words = {'very', 'really', 'quite', 'rather', 'somewhat', 'actually', 'basically'}
        filtered_words = [w for w in words if w.lower() not in filler_words]
        
        compressed = ' '.join(filtered_words)
        
        if len(compressed) <= target_length:
            return compressed
        
        # Further compression: take first and last parts
        if target_length > 50:
            first_part = compressed[:target_length//2 - 10]
            last_part = compressed[-(target_length//2 - 10):]
            return f"{first_part} ... {last_part}"
        
        return compressed[:target_length - 3] + "..."
    
    # Performance and analytics methods
    
    def get_context_effectiveness_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed context effectiveness statistics."""
        stats = {}
        
        for source, tracking in self._effectiveness_tracking.items():
            stats[source] = {
                "total_uses": tracking["total_uses"],
                "average_effectiveness": tracking["average_effectiveness"],
                "last_used": tracking["last_used"].isoformat() if tracking["last_used"] else None,
                "context_types": tracking["context_types"],
                "recent_effectiveness": self._get_recent_effectiveness(tracking["effectiveness_history"])
            }
        
        return stats
    
    def _get_recent_effectiveness(self, history: List[Dict[str, Any]]) -> float:
        """Get recent effectiveness from history."""
        if not history:
            return 0.0
        
        # Get effectiveness from last 10 entries
        recent_entries = history[-10:]
        if not recent_entries:
            return 0.0
        
        return sum(entry["effectiveness"] for entry in recent_entries) / len(recent_entries)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the context retriever."""
        total_requests = self._cache_hits + self._cache_misses
        cache_hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0
        
        avg_retrieval_time = (
            sum(self._retrieval_times) / len(self._retrieval_times)
            if self._retrieval_times else 0.0
        )
        
        return {
            "cache_hit_rate": cache_hit_rate,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "average_retrieval_time": avg_retrieval_time,
            "cached_contexts": len(self._context_cache),
            "tracked_sources": len(self._effectiveness_tracking),
            "context_priorities": len(self._context_priorities)
        }
    
    def clear_context_cache(self) -> None:
        """Clear the context cache and reset metrics."""
        self._context_cache.clear()
        self._cache_timestamps.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self.logger.info("Context cache cleared")
    
    def reset_effectiveness_tracking(self) -> None:
        """Reset effectiveness tracking data."""
        self._effectiveness_tracking.clear()
        self._context_priorities.clear()
        self.logger.info("Effectiveness tracking reset")
    
    # Context window management methods
    
    def set_context_compression_threshold(self, threshold: int) -> None:
        """Set the threshold for context compression."""
        self.compression_threshold = threshold
        self.logger.info(f"Context compression threshold set to {threshold}")
    
    def set_max_context_length(self, length: int) -> None:
        """Set the maximum context length for summarization."""
        self.max_context_length = length
        self.logger.info(f"Maximum context length set to {length}")
    
    def get_context_window_stats(self) -> Dict[str, Any]:
        """Get context window management statistics."""
        return {
            "max_context_length": self.max_context_length,
            "compression_threshold": self.compression_threshold,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "compressed_contexts": len(self._compressed_contexts),
            "context_priorities": len(self._context_priorities),
            "total_contexts_processed": getattr(self, '_total_contexts_processed', 0)
        }
    
    # Context window management methods for performance optimization
    
    def compress_context_window(self, contexts: List[ContextEntry], target_size: int) -> List[ContextEntry]:
        """
        Compress context window to target size with intelligent prioritization.
        
        Args:
            contexts: List of context entries to compress
            target_size: Target number of contexts to keep
            
        Returns:
            Compressed list of context entries
        """
        if len(contexts) <= target_size:
            return contexts
        
        # Sort by composite score (relevance + effectiveness + recency)
        scored_contexts = []
        for context in contexts:
            composite_score = self._calculate_composite_score(context)
            scored_contexts.append((composite_score, context))
        
        # Sort by score descending
        scored_contexts.sort(key=lambda x: x[0], reverse=True)
        
        # Apply diversity filter to ensure variety in sources and types
        compressed = self._apply_diversity_filter(
            [ctx for _, ctx in scored_contexts], 
            target_size
        )
        
        # Update compression statistics
        if not hasattr(self, '_compression_stats'):
            self._compression_stats = {
                'total_compressed': 0,
                'original_sizes': [],
                'compressed_sizes': []
            }
        
        self._compression_stats['total_compressed'] += 1
        self._compression_stats['original_sizes'].append(len(contexts))
        self._compression_stats['compressed_sizes'].append(len(compressed))
        
        self.logger.debug(f"Compressed {len(contexts)} contexts to {len(compressed)}")
        return compressed
    
    def optimize_context_for_performance(self, contexts: List[ContextEntry], mode: str = "balanced") -> List[ContextEntry]:
        """
        Optimize context for different performance modes.
        
        Args:
            contexts: List of context entries to optimize
            mode: Optimization mode - "speed", "accuracy", or "balanced"
            
        Returns:
            Optimized list of context entries
        """
        if mode == "speed":
            # Prioritize speed - minimal contexts, highest relevance only
            target_size = min(5, len(contexts))
            return self._optimize_for_speed(contexts, target_size)
        elif mode == "accuracy":
            # Prioritize accuracy - more contexts, diverse sources
            target_size = min(15, len(contexts))
            return self._optimize_for_accuracy(contexts, target_size)
        else:  # balanced
            # Balance speed and accuracy
            target_size = min(10, len(contexts))
            return self._optimize_for_balance(contexts, target_size)
    
    def create_context_cache_entry(
        self, 
        contexts: List[ContextEntry], 
        query: str, 
        user_id: str, 
        ttl_hours: int = 1
    ) -> str:
        """
        Create a context cache entry with specified TTL.
        
        Args:
            contexts: Context entries to cache
            query: Query associated with contexts
            user_id: User identifier
            ttl_hours: Time-to-live in hours
            
        Returns:
            Cache key for the entry
        """
        cache_key = self._generate_cache_key(query, user_id, len(contexts))
        
        # Calculate expiry time
        expiry_time = datetime.now() + timedelta(hours=ttl_hours)
        
        # Store in cache with metadata
        self._context_cache[cache_key] = {
            "context": contexts,
            "timestamp": datetime.now(),
            "expiry_time": expiry_time,
            "access_count": 0,
            "query": query,
            "user_id": user_id
        }
        
        self._cache_timestamps[cache_key] = datetime.now()
        
        self.logger.debug(f"Created cache entry {cache_key} with {len(contexts)} contexts")
        return cache_key
    
    def get_cached_context_entry(self, cache_key: str) -> Optional[List[ContextEntry]]:
        """
        Get context entry from cache by key.
        
        Args:
            cache_key: Cache key to retrieve
            
        Returns:
            Cached context entries or None if not found/expired
        """
        if cache_key not in self._context_cache:
            return None
        
        cache_entry = self._context_cache[cache_key]
        
        # Check if expired
        if datetime.now() > cache_entry.get("expiry_time", datetime.now()):
            # Remove expired entry
            del self._context_cache[cache_key]
            if cache_key in self._cache_timestamps:
                del self._cache_timestamps[cache_key]
            return None
        
        # Update access count
        cache_entry["access_count"] += 1
        
        return cache_entry["context"]
    
    def cleanup_expired_cache_entries(self) -> int:
        """
        Clean up expired cache entries.
        
        Returns:
            Number of entries cleaned up
        """
        current_time = datetime.now()
        expired_keys = []
        
        for cache_key, cache_entry in self._context_cache.items():
            expiry_time = cache_entry.get("expiry_time", current_time)
            if current_time > expiry_time:
                expired_keys.append(cache_key)
        
        # Remove expired entries
        for key in expired_keys:
            if key in self._context_cache:
                del self._context_cache[key]
            if key in self._cache_timestamps:
                del self._cache_timestamps[key]
        
        self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        return len(expired_keys)
    
    def get_context_window_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive context window analytics.
        
        Returns:
            Dictionary with analytics data
        """
        total_requests = self._cache_hits + self._cache_misses
        cache_hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0
        
        avg_retrieval_time = (
            sum(self._retrieval_times) / len(self._retrieval_times)
            if self._retrieval_times else 0.0
        )
        
        compression_stats = self.get_context_compression_stats()
        
        return {
            "total_contexts_processed": getattr(self, '_total_contexts_processed', 0),
            "cache_efficiency": {
                "hit_rate": cache_hit_rate,
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "total_entries": len(self._context_cache)
            },
            "performance_metrics": {
                "avg_retrieval_time": avg_retrieval_time,
                "max_retrieval_time": max(self._retrieval_times) if self._retrieval_times else 0.0,
                "min_retrieval_time": min(self._retrieval_times) if self._retrieval_times else 0.0
            },
            "compression_stats": compression_stats,
            "compressed_cache_entries": len(self._compressed_contexts),
            "context_priorities": len(self._context_priorities),
            "effectiveness_tracking": len(self._effectiveness_tracking)
        }
    
    def get_context_compression_stats(self) -> Dict[str, Any]:
        """
        Get context compression statistics.
        
        Returns:
            Dictionary with compression statistics
        """
        if not hasattr(self, '_compression_stats'):
            return {
                "compression_ratio": 0.0,
                "total_compressed_contexts": 0,
                "average_original_size": 0.0,
                "average_compressed_size": 0.0
            }
        
        stats = self._compression_stats
        
        if not stats['original_sizes'] or not stats['compressed_sizes']:
            return {
                "compression_ratio": 0.0,
                "total_compressed_contexts": stats['total_compressed'],
                "average_original_size": 0.0,
                "average_compressed_size": 0.0
            }
        
        avg_original = sum(stats['original_sizes']) / len(stats['original_sizes'])
        avg_compressed = sum(stats['compressed_sizes']) / len(stats['compressed_sizes'])
        compression_ratio = avg_compressed / avg_original if avg_original > 0 else 0.0
        
        return {
            "compression_ratio": compression_ratio,
            "total_compressed_contexts": stats['total_compressed'],
            "average_original_size": avg_original,
            "average_compressed_size": avg_compressed
        }
    
    # Private helper methods for context window management
    
    def _calculate_composite_score(self, context: ContextEntry) -> float:
        """Calculate composite score for context prioritization."""
        base_score = context.relevance_score
        effectiveness_boost = self._get_effectiveness_boost(context.source)
        recency_boost = self._get_recency_boost(context.timestamp)
        type_boost = 0.05 if context.context_type in ["conversation_history", "user_message"] else 0.0
        
        return base_score + effectiveness_boost + recency_boost + type_boost
    
    def _apply_diversity_filter(self, contexts: List[ContextEntry], target_size: int) -> List[ContextEntry]:
        """Apply diversity filter to ensure variety in sources and types."""
        if len(contexts) <= target_size:
            return contexts
        
        selected = []
        seen_sources = set()
        seen_types = set()
        
        # First pass: ensure diversity
        for context in contexts:
            if len(selected) >= target_size:
                break
            
            # Prefer unseen sources and types
            source_new = context.source not in seen_sources
            type_new = context.context_type not in seen_types
            
            if source_new or type_new or len(selected) < target_size // 2:
                selected.append(context)
                seen_sources.add(context.source)
                seen_types.add(context.context_type)
        
        # Second pass: fill remaining slots with highest scores
        remaining = [ctx for ctx in contexts if ctx not in selected]
        remaining_slots = target_size - len(selected)
        
        if remaining_slots > 0:
            selected.extend(remaining[:remaining_slots])
        
        return selected
    
    def _optimize_for_speed(self, contexts: List[ContextEntry], target_size: int) -> List[ContextEntry]:
        """Optimize contexts for speed - minimal, high-relevance only."""
        # Sort by relevance score only
        sorted_contexts = sorted(contexts, key=lambda x: x.relevance_score, reverse=True)
        
        # Take top contexts with relevance > 0.7
        high_relevance = [ctx for ctx in sorted_contexts if ctx.relevance_score > 0.7]
        
        return high_relevance[:target_size]
    
    def _optimize_for_accuracy(self, contexts: List[ContextEntry], target_size: int) -> List[ContextEntry]:
        """Optimize contexts for accuracy - diverse, comprehensive."""
        # Use composite scoring with diversity
        scored_contexts = []
        for context in contexts:
            score = self._calculate_composite_score(context)
            scored_contexts.append((score, context))
        
        scored_contexts.sort(key=lambda x: x[0], reverse=True)
        
        # Apply strong diversity filter
        return self._apply_diversity_filter(
            [ctx for _, ctx in scored_contexts], 
            target_size
        )
    
    def _optimize_for_balance(self, contexts: List[ContextEntry], target_size: int) -> List[ContextEntry]:
        """Optimize contexts for balanced performance."""
        # Use moderate diversity with good scoring
        scored_contexts = []
        for context in contexts:
            score = self._calculate_composite_score(context)
            # Apply slight penalty for very old contexts in balanced mode
            if context.timestamp:
                age_hours = (datetime.now(timezone.utc) - context.timestamp.replace(tzinfo=timezone.utc)).total_seconds() / 3600
                if age_hours > 168:  # 1 week
                    score *= 0.9
            scored_contexts.append((score, context))
        
        scored_contexts.sort(key=lambda x: x[0], reverse=True)
        
        # Apply moderate diversity filter
        return self._apply_diversity_filter(
            [ctx for _, ctx in scored_contexts], 
            target_size
        )ics."""
        return {
            "max_context_length": self.max_context_length,
            "compression_threshold": self.compression_threshold,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "compressed_contexts": len(self._compressed_contexts)
        }
    
    # Advanced Context Window Management Methods
    
    def set_context_window_limits(self, max_contexts: int, max_total_length: int) -> None:
        """
        Set context window limits for performance optimization.
        
        Args:
            max_contexts: Maximum number of context entries
            max_total_length: Maximum total character length
        """
        self.max_contexts = max_contexts
        self.max_total_length = max_total_length
        self.logger.info(f"Context window limits set: {max_contexts} contexts, {max_total_length} chars")
    
    def compress_context_window(self, contexts: List[ContextEntry], target_size: int) -> List[ContextEntry]:
        """
        Compress context window using intelligent truncation and prioritization.
        
        Args:
            contexts: List of context entries to compress
            target_size: Target number of contexts after compression
            
        Returns:
            Compressed list of context entries
        """
        if len(contexts) <= target_size:
            return contexts
        
        # Sort by composite score (relevance + effectiveness + recency)
        scored_contexts = []
        for context in contexts:
            composite_score = self._calculate_composite_score(context)
            scored_contexts.append((composite_score, context))
        
        # Sort by composite score (highest first)
        scored_contexts.sort(key=lambda x: x[0], reverse=True)
        
        # Select top contexts ensuring diversity
        compressed = []
        seen_sources = set()
        seen_types = set()
        
        # First pass: prioritize diverse, high-scoring contexts
        for score, context in scored_contexts:
            if len(compressed) >= target_size:
                break
            
            # Diversity bonus for new sources/types
            diversity_bonus = 0
            if context.source not in seen_sources:
                diversity_bonus += 0.1
            if context.context_type not in seen_types:
                diversity_bonus += 0.05
            
            adjusted_score = score + diversity_bonus
            
            if adjusted_score > 0.4 or len(compressed) < target_size // 2:
                compressed.append(context)
                seen_sources.add(context.source)
                seen_types.add(context.context_type)
        
        # Second pass: fill remaining slots with highest scores
        remaining_slots = target_size - len(compressed)
        if remaining_slots > 0:
            remaining_contexts = [ctx for _, ctx in scored_contexts if ctx not in compressed]
            compressed.extend(remaining_contexts[:remaining_slots])
        
        self.logger.debug(f"Compressed context window from {len(contexts)} to {len(compressed)} entries")
        return compressed
    
    def _calculate_composite_score(self, context: ContextEntry) -> float:
        """Calculate composite score for context prioritization."""
        base_score = context.relevance_score
        
        # Effectiveness boost
        effectiveness_boost = self._get_effectiveness_boost(context.source)
        
        # Recency boost
        recency_boost = self._get_recency_boost(context.timestamp)
        
        # Content quality boost (based on length and structure)
        quality_boost = self._get_content_quality_boost(context.content)
        
        return base_score + effectiveness_boost + recency_boost + quality_boost
    
    def _get_content_quality_boost(self, content: str) -> float:
        """Get content quality boost based on content characteristics."""
        if not content:
            return 0.0
        
        boost = 0.0
        
        # Length boost (prefer moderate length content)
        length = len(content)
        if 50 <= length <= 500:
            boost += 0.05
        elif 500 < length <= 1000:
            boost += 0.03
        
        # Structure boost (prefer well-structured content)
        if '.' in content and len(content.split('.')) > 1:
            boost += 0.02
        
        # Information density boost
        words = content.split()
        if len(words) > 5:
            unique_words = len(set(word.lower() for word in words))
            density = unique_words / len(words)
            if density > 0.7:
                boost += 0.03
        
        return min(boost, 0.1)  # Cap at 10% boost
    
    def create_context_cache_entry(
        self, 
        contexts: List[ContextEntry], 
        query: str, 
        user_id: str,
        cache_duration_hours: int = 24
    ) -> str:
        """
        Create a cached context entry for frequently accessed data.
        
        Args:
            contexts: Context entries to cache
            query: Query associated with contexts
            user_id: User ID for scoping
            cache_duration_hours: Cache duration in hours
            
        Returns:
            Cache key for the created entry
        """
        cache_key = self._generate_cache_key(query, user_id, len(contexts))
        
        # Create compressed representation for caching
        compressed_contexts = []
        for context in contexts:
            compressed_contexts.append({
                'content': self._compress_content(context.content, 200),
                'source': context.source,
                'relevance_score': context.relevance_score,
                'context_type': context.context_type,
                'timestamp': context.timestamp.isoformat(),
                'metadata': context.metadata
            })
        
        cache_entry = {
            'contexts': compressed_contexts,
            'query': query,
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=cache_duration_hours)).isoformat(),
            'access_count': 0,
            'effectiveness_score': 0.0
        }
        
        # Store in compressed cache
        self._compressed_contexts[cache_key] = cache_entry
        
        self.logger.debug(f"Created compressed cache entry: {cache_key}")
        return cache_key
    
    def get_cached_context_entry(self, cache_key: str) -> Optional[List[ContextEntry]]:
        """
        Retrieve cached context entry and convert back to ContextEntry objects.
        
        Args:
            cache_key: Cache key to retrieve
            
        Returns:
            List of ContextEntry objects or None if not found/expired
        """
        if cache_key not in self._compressed_contexts:
            return None
        
        cache_entry = self._compressed_contexts[cache_key]
        
        # Check expiration
        expires_at = datetime.fromisoformat(cache_entry['expires_at'])
        if datetime.now() > expires_at:
            del self._compressed_contexts[cache_key]
            return None
        
        # Convert back to ContextEntry objects
        contexts = []
        for compressed_ctx in cache_entry['contexts']:
            context = ContextEntry(
                content=compressed_ctx['content'],
                source=compressed_ctx['source'],
                relevance_score=compressed_ctx['relevance_score'],
                timestamp=datetime.fromisoformat(compressed_ctx['timestamp']),
                context_type=compressed_ctx['context_type'],
                metadata=compressed_ctx['metadata']
            )
            contexts.append(context)
        
        # Update access count
        cache_entry['access_count'] += 1
        
        self.logger.debug(f"Retrieved compressed cache entry: {cache_key}")
        return contexts
    
    def optimize_context_for_performance(
        self, 
        contexts: List[ContextEntry], 
        performance_target: str = "balanced"
    ) -> List[ContextEntry]:
        """
        Optimize context for different performance targets.
        
        Args:
            contexts: Context entries to optimize
            performance_target: "speed", "accuracy", or "balanced"
            
        Returns:
            Optimized context entries
        """
        if performance_target == "speed":
            # Prioritize speed: fewer, shorter contexts
            return self._optimize_for_speed(contexts)
        elif performance_target == "accuracy":
            # Prioritize accuracy: more comprehensive contexts
            return self._optimize_for_accuracy(contexts)
        else:
            # Balanced approach
            return self._optimize_balanced(contexts)
    
    def _optimize_for_speed(self, contexts: List[ContextEntry]) -> List[ContextEntry]:
        """Optimize contexts for speed (fewer, shorter contexts)."""
        # Limit to top 5 contexts
        top_contexts = sorted(contexts, key=lambda x: x.relevance_score, reverse=True)[:5]
        
        # Compress content for faster processing
        for context in top_contexts:
            if len(context.content) > 300:
                context.content = self._compress_content(context.content, 300)
        
        return top_contexts
    
    def _optimize_for_accuracy(self, contexts: List[ContextEntry]) -> List[ContextEntry]:
        """Optimize contexts for accuracy (more comprehensive contexts)."""
        # Keep more contexts but ensure quality
        quality_contexts = [
            ctx for ctx in contexts 
            if ctx.relevance_score > 0.3 and len(ctx.content) > 20
        ]
        
        # Sort by relevance and effectiveness
        sorted_contexts = sorted(
            quality_contexts,
            key=lambda x: (x.relevance_score, self._get_effectiveness_boost(x.source)),
            reverse=True
        )
        
        return sorted_contexts[:15]  # Up to 15 contexts for accuracy
    
    def _optimize_balanced(self, contexts: List[ContextEntry]) -> List[ContextEntry]:
        """Optimize contexts for balanced performance."""
        # Medium number of contexts with good diversity
        optimized = self._optimize_context_window(contexts, 10)
        
        # Apply moderate compression to long contexts
        for context in optimized:
            if len(context.content) > 500:
                context.content = self._compress_content(context.content, 500)
        
        return optimized
    
    def get_context_window_analytics(self) -> Dict[str, Any]:
        """
        Get analytics about context window usage and performance.
        
        Returns:
            Dictionary with context window analytics
        """
        total_contexts_processed = sum(
            tracking.get("total_uses", 0) 
            for tracking in self._effectiveness_tracking.values()
        )
        
        avg_context_length = 0
        if self._context_cache:
            total_length = 0
            total_contexts = 0
            for cache_entry in self._context_cache.values():
                if isinstance(cache_entry, dict) and "context" in cache_entry:
                    contexts = cache_entry["context"]
                    for ctx in contexts:
                        total_length += len(ctx.content)
                        total_contexts += 1
            
            avg_context_length = total_length / total_contexts if total_contexts > 0 else 0
        
        return {
            "total_contexts_processed": total_contexts_processed,
            "average_context_length": avg_context_length,
            "compressed_cache_entries": len(self._compressed_contexts),
            "context_priorities_tracked": len(self._context_priorities),
            "cache_efficiency": {
                "hit_rate": self._cache_hits / (self._cache_hits + self._cache_misses) if (self._cache_hits + self._cache_misses) > 0 else 0,
                "total_hits": self._cache_hits,
                "total_misses": self._cache_misses
            },
            "performance_metrics": {
                "avg_retrieval_time": sum(self._retrieval_times) / len(self._retrieval_times) if self._retrieval_times else 0,
                "retrieval_count": len(self._retrieval_times)
            }
        }
    
    def cleanup_expired_cache_entries(self) -> int:
        """
        Clean up expired cache entries to free memory.
        
        Returns:
            Number of entries cleaned up
        """
        current_time = datetime.now()
        expired_keys = []
        
        # Check regular cache
        for key, timestamp in self._cache_timestamps.items():
            if (current_time - timestamp).total_seconds() > self.cache_ttl_seconds:
                expired_keys.append(key)
        
        # Remove expired regular cache entries
        for key in expired_keys:
            if key in self._context_cache:
                del self._context_cache[key]
            if key in self._cache_timestamps:
                del self._cache_timestamps[key]
        
        # Check compressed cache
        compressed_expired = []
        for key, entry in self._compressed_contexts.items():
            expires_at = datetime.fromisoformat(entry['expires_at'])
            if current_time > expires_at:
                compressed_expired.append(key)
        
        # Remove expired compressed cache entries
        for key in compressed_expired:
            del self._compressed_contexts[key]
        
        total_cleaned = len(expired_keys) + len(compressed_expired)
        
        if total_cleaned > 0:
            self.logger.info(f"Cleaned up {total_cleaned} expired cache entries")
        
        return total_cleaned
    
    def preload_context_for_user(self, user_id: str, common_queries: List[str]) -> None:
        """
        Preload context for common user queries to improve performance.
        
        Args:
            user_id: User ID to preload context for
            common_queries: List of common queries to preload
        """
        async def preload_task():
            for query in common_queries:
                try:
                    contexts = await self.get_relevant_context(query, user_id, 10)
                    if contexts:
                        cache_key = self.create_context_cache_entry(contexts, query, user_id, 48)  # 48 hour cache
                        self.logger.debug(f"Preloaded context for query: {query[:50]}...")
                except Exception as e:
                    self.logger.warning(f"Failed to preload context for query '{query}': {e}")
        
        # Run preloading in background (would need proper async handling in production)
        self.logger.info(f"Preloading context for {len(common_queries)} queries for user {user_id}")
        # Note: In a real implementation, this would be run as a background task
        
        # For now, we'll just log that preloading would happen
        # In production, this would use asyncio.create_task(preload_task())
    
