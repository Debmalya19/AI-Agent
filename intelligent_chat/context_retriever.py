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
            
            # Try to get real context from memory manager or context engine
            if self.memory_manager:
                try:
                    memory_contexts = self.memory_manager.retrieve_context(query, user_id, limit)
                    context_entries = self._convert_memory_contexts_to_context_entries(memory_contexts)
                except Exception as e:
                    self.logger.warning(f"Memory manager context retrieval failed: {e}")
            
            # Fallback to context engine if available
            if not context_entries and self.context_engine:
                try:
                    engine_contexts = self.context_engine.get_relevant_context(query, user_id, limit=limit)
                    context_entries = self._convert_engine_contexts_to_context_entries(engine_contexts)
                except Exception as e:
                    self.logger.warning(f"Context engine retrieval failed: {e}")
            
            # If no real context available, return empty list instead of mock data
            if not context_entries:
                self.logger.info(f"No real context found for query: {query}")
                context_entries = []
            
            # Cache results with TTL
            self._cache_context(cache_key, context_entries)
            
            # Track performance
            retrieval_time = (datetime.now() - start_time).total_seconds()
            self._retrieval_times.append(retrieval_time)
            # Keep only last 100 entries
            if len(self._retrieval_times) > 100:
                self._retrieval_times = self._retrieval_times[-100:]
            
            # Update total contexts processed
            self._total_contexts_processed += len(context_entries)
            
            self.logger.info(f"Retrieved {len(context_entries)} context entries in {retrieval_time:.3f}s")
            
            return context_entries
            
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
            # Apply medium compression
            result = self._create_compressed_summary(context)
            # Track compression statistics
            self._compression_stats['total_compressed'] += 1
            self._compression_stats['original_sizes'].append(total_length)
            self._compression_stats['compressed_sizes'].append(len(result))
            return result
        else:
            # Apply heavy compression for large contexts
            result = self._create_context_summary(context)
            # Track compression statistics
            self._compression_stats['total_compressed'] += 1
            self._compression_stats['original_sizes'].append(total_length)
            self._compression_stats['compressed_sizes'].append(len(result))
            return result
    
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
        # Cleanup old cache entries if too many BEFORE adding new one
        if len(self._context_cache) >= 100:
            self._cleanup_cache()
        
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
            "total_contexts_processed": self._total_contexts_processed,
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

    # Private helper methods
    
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
        # Cleanup old cache entries if too many BEFORE adding new one
        if len(self._context_cache) >= 100:
            self._cleanup_cache()
        
        self._context_cache[cache_key] = {
            "context": context,
            "timestamp": datetime.now(),
            "access_count": 1
        }
        self._cache_timestamps[cache_key] = datetime.now()
    
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
        )
    
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
    
    def _update_context_priority(self, source: str, effectiveness: float, relevance: float) -> None:
        """Update context priority based on usage effectiveness."""
        if source not in self._context_priorities:
            self._context_priorities[source] = 0.5
        
        # Update priority using exponential moving average
        current_priority = self._context_priorities[source]
        new_score = (effectiveness + relevance) / 2
        
        # EMA with alpha = 0.1
        self._context_priorities[source] = current_priority * 0.9 + new_score * 0.1
    
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
        target_length = self.max_context_length // 3  # More aggressive compression for medium
        
        for entry in sorted_context:
            if total_length >= target_length:
                break
            
            # Compress content more aggressively for medium summary
            compressed_content = self._compress_content(entry.content, 100)
            
            if total_length + len(compressed_content) <= target_length:
                summary_parts.append(f"[{entry.context_type}] {compressed_content}")
                total_length += len(compressed_content)
        
        if len(sorted_context) > len(summary_parts):
            summary_parts.append(f"... and {len(sorted_context) - len(summary_parts)} more entries")
        
        return "\n\n".join(summary_parts)
    
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
    
    def _convert_memory_contexts_to_context_entries(self, memory_contexts: List) -> List[ContextEntry]:
        """Convert memory layer contexts to ContextEntry objects."""
        context_entries = []
        
        for ctx in memory_contexts:
            if hasattr(ctx, 'content'):  # ContextEntryDTO
                context_entries.append(ContextEntry(
                    content=ctx.content,
                    source=ctx.source,
                    relevance_score=ctx.relevance_score,
                    timestamp=ctx.timestamp,
                    context_type=ctx.context_type,
                    metadata=ctx.metadata
                ))
        
        return context_entries
    
    def _convert_engine_contexts_to_context_entries(self, engine_contexts: List) -> List[ContextEntry]:
        """Convert context engine contexts to ContextEntry objects."""
        context_entries = []
        
        for ctx in engine_contexts:
            if hasattr(ctx, 'content'):  # ContextEntryDTO
                context_entries.append(ContextEntry(
                    content=ctx.content,
                    source=ctx.source,
                    relevance_score=ctx.relevance_score,
                    timestamp=ctx.timestamp,
                    context_type=ctx.context_type,
                    metadata=ctx.metadata
                ))
        
        return context_entries