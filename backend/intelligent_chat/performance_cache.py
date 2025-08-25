"""
Performance Cache System for Intelligent Chat UI

This module implements caching and performance optimization for the intelligent chat system,
including tool performance metrics caching, response caching, and background metric updates.

Requirements covered:
- 6.1: Performance optimization through caching
- 6.2: Response time optimization
- 6.4: Resource usage optimization
- 6.5: Background performance metric updates
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from backend.database import SessionLocal
from backend.memory_models import ToolUsageMetrics
from .models import ChatResponse, ToolRecommendation, ContextEntry


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Any
    timestamp: datetime
    ttl: int  # Time to live in seconds
    access_count: int = 0
    last_accessed: datetime = None
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.timestamp
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.now(timezone.utc) > self.timestamp + timedelta(seconds=self.ttl)
    
    def access(self):
        """Mark cache entry as accessed."""
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    cache_hits: int = 0
    cache_misses: int = 0
    total_requests: int = 0
    average_response_time: float = 0.0
    cache_size: int = 0
    memory_usage: float = 0.0
    
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests
    
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        return 1.0 - self.hit_rate()


class PerformanceCache:
    """
    High-performance caching system for intelligent chat components.
    
    Features:
    - Multi-level caching (memory, database)
    - TTL-based expiration
    - LRU eviction policy
    - Background refresh
    - Performance monitoring
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize performance cache.
        
        Args:
            max_size: Maximum number of cache entries
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        
        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        
        # Performance tracking
        self.metrics = PerformanceMetrics()
        self.logger = logging.getLogger(__name__)
        
        # Background refresh
        self._refresh_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cache-refresh")
        self._refresh_tasks: Dict[str, asyncio.Task] = {}
        
        # Cache categories for better organization
        self.cache_categories = {
            'tool_performance': 3600,  # 1 hour
            'tool_recommendations': 1800,  # 30 minutes
            'response_cache': 600,  # 10 minutes
            'context_cache': 900,  # 15 minutes
            'query_analysis': 1200,  # 20 minutes
        }
    
    def get(self, key: str, category: str = 'default') -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            category: Cache category for TTL management
            
        Returns:
            Cached value or None if not found/expired
        """
        start_time = time.time()
        
        with self._lock:
            self.metrics.total_requests += 1
            
            if key not in self._cache:
                self.metrics.cache_misses += 1
                self.logger.debug(f"Cache miss for key: {key}")
                return None
            
            entry = self._cache[key]
            
            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                self.metrics.cache_misses += 1
                self.logger.debug(f"Cache expired for key: {key}")
                return None
            
            # Update access statistics
            entry.access()
            self.metrics.cache_hits += 1
            
            # Update average response time
            response_time = time.time() - start_time
            self._update_response_time(response_time)
            
            self.logger.debug(f"Cache hit for key: {key}")
            return entry.data
    
    def set(self, key: str, value: Any, category: str = 'default', ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            category: Cache category
            ttl: Time-to-live override
            
        Returns:
            True if successfully cached
        """
        try:
            with self._lock:
                # Determine TTL
                if ttl is None:
                    ttl = self.cache_categories.get(category, self.default_ttl)
                
                # Check if we need to evict entries
                if len(self._cache) >= self.max_size:
                    self._evict_lru()
                
                # Create cache entry
                entry = CacheEntry(
                    data=value,
                    timestamp=datetime.now(timezone.utc),
                    ttl=ttl
                )
                
                self._cache[key] = entry
                self.metrics.cache_size = len(self._cache)
                
                self.logger.debug(f"Cached value for key: {key} (TTL: {ttl}s)")
                return True
                
        except Exception as e:
            self.logger.error(f"Error caching value for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self.metrics.cache_size = len(self._cache)
                self.logger.debug(f"Deleted cache entry: {key}")
                return True
            return False
    
    def clear_category(self, category: str) -> int:
        """Clear all entries in a category."""
        cleared = 0
        with self._lock:
            keys_to_remove = []
            for key, entry in self._cache.items():
                if key.startswith(f"{category}:"):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._cache[key]
                cleared += 1
            
            self.metrics.cache_size = len(self._cache)
        
        self.logger.info(f"Cleared {cleared} entries from category: {category}")
        return cleared
    
    def clear_all(self) -> int:
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self.metrics.cache_size = 0
        
        self.logger.info(f"Cleared all {count} cache entries")
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                'cache_size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': self.metrics.hit_rate(),
                'miss_rate': self.metrics.miss_rate(),
                'total_requests': self.metrics.total_requests,
                'cache_hits': self.metrics.cache_hits,
                'cache_misses': self.metrics.cache_misses,
                'average_response_time': self.metrics.average_response_time,
                'memory_usage_mb': self._estimate_memory_usage(),
            }
    
    def cleanup_expired(self) -> int:
        """Remove expired entries from cache."""
        expired_keys = []
        
        with self._lock:
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            self.metrics.cache_size = len(self._cache)
        
        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entries."""
        if not self._cache:
            return
        
        # Find LRU entry
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        
        del self._cache[lru_key]
        self.logger.debug(f"Evicted LRU entry: {lru_key}")
    
    def _update_response_time(self, response_time: float) -> None:
        """Update average response time."""
        if self.metrics.total_requests == 1:
            self.metrics.average_response_time = response_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.metrics.average_response_time = (
                alpha * response_time + 
                (1 - alpha) * self.metrics.average_response_time
            )
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        try:
            import sys
            total_size = 0
            
            for key, entry in self._cache.items():
                total_size += sys.getsizeof(key)
                total_size += sys.getsizeof(entry)
                total_size += sys.getsizeof(entry.data)
            
            return total_size / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0.0


class ResponseCache:
    """
    Specialized cache for chat responses and common query patterns.
    """
    
    def __init__(self, cache: PerformanceCache):
        """Initialize with performance cache instance."""
        self.cache = cache
        self.logger = logging.getLogger(__name__)
    
    def get_response(self, query: str, context_hash: str) -> Optional[ChatResponse]:
        """Get cached response for query and context."""
        cache_key = self._generate_response_key(query, context_hash)
        cached_data = self.cache.get(cache_key, 'response_cache')
        
        if cached_data:
            try:
                # Reconstruct ChatResponse from cached data
                return ChatResponse(**cached_data)
            except Exception as e:
                self.logger.error(f"Error reconstructing cached response: {e}")
                self.cache.delete(cache_key)
        
        return None
    
    def cache_response(self, query: str, context_hash: str, response: ChatResponse) -> bool:
        """Cache response for future use."""
        try:
            cache_key = self._generate_response_key(query, context_hash)
            
            # Convert response to cacheable format
            response_data = asdict(response)
            
            # Cache with shorter TTL for responses
            return self.cache.set(cache_key, response_data, 'response_cache', ttl=600)
            
        except Exception as e:
            self.logger.error(f"Error caching response: {e}")
            return False
    
    def _generate_response_key(self, query: str, context_hash: str) -> str:
        """Generate cache key for response."""
        combined = f"{query}:{context_hash}"
        return f"response:{hashlib.md5(combined.encode()).hexdigest()}"


class ToolPerformanceCache:
    """
    Specialized cache for tool performance metrics and recommendations.
    """
    
    def __init__(self, cache: PerformanceCache, db_session: Optional[Session] = None):
        """Initialize with performance cache and database session."""
        self.cache = cache
        self.db_session = db_session or SessionLocal()
        self.logger = logging.getLogger(__name__)
        
        # Background refresh interval
        self.refresh_interval = 300  # 5 minutes
        self._last_refresh = datetime.now(timezone.utc)
    
    def get_tool_performance(self, tool_name: str, query_type: str) -> Optional[Dict[str, float]]:
        """Get cached tool performance metrics."""
        cache_key = f"tool_performance:{tool_name}:{query_type}"
        cached_data = self.cache.get(cache_key, 'tool_performance')
        
        if cached_data:
            return cached_data
        
        # Fetch from database and cache
        performance = self._fetch_tool_performance(tool_name, query_type)
        if performance:
            self.cache.set(cache_key, performance, 'tool_performance')
        
        return performance
    
    def get_tool_recommendations(self, query_hash: str) -> Optional[List[ToolRecommendation]]:
        """Get cached tool recommendations."""
        cache_key = f"tool_recommendations:{query_hash}"
        cached_data = self.cache.get(cache_key, 'tool_recommendations')
        
        if cached_data:
            try:
                # Reconstruct ToolRecommendation objects
                return [ToolRecommendation(**rec) for rec in cached_data]
            except Exception as e:
                self.logger.error(f"Error reconstructing cached recommendations: {e}")
                self.cache.delete(cache_key)
        
        return None
    
    def cache_tool_recommendations(self, query_hash: str, recommendations: List[ToolRecommendation]) -> bool:
        """Cache tool recommendations."""
        try:
            cache_key = f"tool_recommendations:{query_hash}"
            
            # Convert to cacheable format
            rec_data = [asdict(rec) for rec in recommendations]
            
            return self.cache.set(cache_key, rec_data, 'tool_recommendations')
            
        except Exception as e:
            self.logger.error(f"Error caching tool recommendations: {e}")
            return False
    
    def refresh_tool_metrics(self, tool_names: List[str]) -> None:
        """Refresh tool metrics in background."""
        try:
            for tool_name in tool_names:
                # Clear existing cache entries for this tool
                self.cache.clear_category(f"tool_performance:{tool_name}")
                
                # Pre-populate cache with fresh data
                query_types = ['support', 'plans', 'technical', 'billing', 'general']
                for query_type in query_types:
                    performance = self._fetch_tool_performance(tool_name, query_type)
                    if performance:
                        cache_key = f"tool_performance:{tool_name}:{query_type}"
                        self.cache.set(cache_key, performance, 'tool_performance')
            
            self._last_refresh = datetime.now(timezone.utc)
            self.logger.info(f"Refreshed metrics for {len(tool_names)} tools")
            
        except Exception as e:
            self.logger.error(f"Error refreshing tool metrics: {e}")
    
    def _fetch_tool_performance(self, tool_name: str, query_type: str) -> Optional[Dict[str, float]]:
        """Fetch tool performance from database."""
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
            
            return {
                'success_rate': weighted_success,
                'quality_score': weighted_quality,
                'response_time': avg_response_time,
                'usage_count': total_usage
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching performance for {tool_name}: {e}")
            return None


class BackgroundMetricsUpdater:
    """
    Background service for updating performance metrics and cache refresh.
    """
    
    def __init__(self, cache: PerformanceCache, tool_cache: ToolPerformanceCache):
        """Initialize background updater."""
        self.cache = cache
        self.tool_cache = tool_cache
        self.logger = logging.getLogger(__name__)
        
        self._running = False
        self._update_thread = None
        self.update_interval = 300  # 5 minutes
    
    def start(self) -> None:
        """Start background metrics updates."""
        if self._running:
            return
        
        self._running = True
        self._update_thread = threading.Thread(
            target=self._update_loop,
            name="metrics-updater",
            daemon=True
        )
        self._update_thread.start()
        self.logger.info("Started background metrics updater")
    
    def stop(self) -> None:
        """Stop background metrics updates."""
        self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=5)
        self.logger.info("Stopped background metrics updater")
    
    def _update_loop(self) -> None:
        """Main update loop."""
        while self._running:
            try:
                # Clean up expired cache entries
                expired_count = self.cache.cleanup_expired()
                
                # Refresh tool metrics if needed
                if self._should_refresh_metrics():
                    self._refresh_tool_metrics()
                
                # Log cache statistics
                stats = self.cache.get_stats()
                self.logger.debug(f"Cache stats: {stats}")
                
                # Sleep until next update
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Error in background metrics update: {e}")
                time.sleep(60)  # Wait before retrying
    
    def _should_refresh_metrics(self) -> bool:
        """Check if metrics should be refreshed."""
        time_since_refresh = datetime.now(timezone.utc) - self.tool_cache._last_refresh
        return time_since_refresh.total_seconds() > self.tool_cache.refresh_interval
    
    def _refresh_tool_metrics(self) -> None:
        """Refresh tool metrics in background."""
        try:
            # Get list of active tools from database
            db_session = SessionLocal()
            try:
                active_tools = db_session.query(ToolUsageMetrics.tool_name).distinct().all()
                tool_names = [tool[0] for tool in active_tools]
                
                if tool_names:
                    self.tool_cache.refresh_tool_metrics(tool_names)
                
            finally:
                db_session.close()
                
        except Exception as e:
            self.logger.error(f"Error refreshing tool metrics: {e}")


# Global cache instances
_global_cache = None
_response_cache = None
_tool_cache = None
_background_updater = None


def get_performance_cache() -> PerformanceCache:
    """Get global performance cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = PerformanceCache()
    return _global_cache


def get_response_cache() -> ResponseCache:
    """Get global response cache instance."""
    global _response_cache
    if _response_cache is None:
        _response_cache = ResponseCache(get_performance_cache())
    return _response_cache


def get_tool_performance_cache() -> ToolPerformanceCache:
    """Get global tool performance cache instance."""
    global _tool_cache
    if _tool_cache is None:
        _tool_cache = ToolPerformanceCache(get_performance_cache())
    return _tool_cache


def start_background_updater() -> None:
    """Start global background metrics updater."""
    global _background_updater
    if _background_updater is None:
        _background_updater = BackgroundMetricsUpdater(
            get_performance_cache(),
            get_tool_performance_cache()
        )
    _background_updater.start()


def stop_background_updater() -> None:
    """Stop global background metrics updater."""
    global _background_updater
    if _background_updater:
        _background_updater.stop()