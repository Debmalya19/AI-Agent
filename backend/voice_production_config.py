"""
Voice Production Configuration and Resource Management
Provides production-ready configuration, monitoring, and resource management
"""

import os
import json
import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import redis
import psutil
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from .voice_config import VoiceConfigManager, DeploymentEnvironment, VoiceFeatureType
from .voice_analytics import VoiceAnalytics

logger = logging.getLogger(__name__)


@dataclass
class ResourceUsageMetrics:
    """Resource usage metrics"""
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    active_sessions: int
    concurrent_requests: int
    timestamp: datetime


@dataclass
class PerformanceThresholds:
    """Performance monitoring thresholds"""
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 75.0
    max_memory_mb: float = 512.0
    max_concurrent_sessions: int = 100
    max_response_time_ms: float = 5000.0
    max_error_rate_percent: float = 5.0


class VoiceProductionManager:
    """Manages voice features in production environment"""
    
    def __init__(self, 
                 config_manager: VoiceConfigManager,
                 redis_client: Optional[redis.Redis] = None,
                 db_session: Optional[Session] = None):
        self.config_manager = config_manager
        self.redis_client = redis_client
        self.db_session = db_session
        
        # Resource monitoring
        self.resource_monitor = VoiceResourceMonitor()
        self.performance_thresholds = PerformanceThresholds()
        
        # Session tracking
        self.active_sessions: Set[str] = set()
        self.session_start_times: Dict[str, datetime] = {}
        
        # Rate limiting
        self.rate_limiter = VoiceProductionRateLimiter(redis_client)
        
        # Circuit breaker for error handling
        self.circuit_breaker = VoiceCircuitBreaker()
        
        # Background tasks
        self.monitoring_task = None
        self.cleanup_task = None
        
        logger.info("VoiceProductionManager initialized")

    async def start_monitoring(self):
        """Start background monitoring tasks"""
        if self.monitoring_task is None:
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Voice production monitoring started")

    async def stop_monitoring(self):
        """Stop background monitoring tasks"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
        
        logger.info("Voice production monitoring stopped")

    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                await self._collect_metrics()
                await self._check_health()
                await self._update_feature_toggles()
                await asyncio.sleep(30)  # Monitor every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                await self._cleanup_stale_sessions()
                await self._cleanup_old_metrics()
                await asyncio.sleep(300)  # Cleanup every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(600)  # Wait longer on error

    async def _collect_metrics(self):
        """Collect system and application metrics"""
        try:
            metrics = self.resource_monitor.get_current_metrics()
            metrics.active_sessions = len(self.active_sessions)
            
            # Store metrics in Redis for monitoring
            if self.redis_client:
                metrics_key = f"voice_metrics:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
                self.redis_client.setex(
                    metrics_key, 
                    3600,  # 1 hour TTL
                    json.dumps(asdict(metrics), default=str)
                )
            
            # Check if metrics exceed thresholds
            await self._check_performance_thresholds(metrics)
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")

    async def _check_performance_thresholds(self, metrics: ResourceUsageMetrics):
        """Check if performance metrics exceed thresholds"""
        warnings = []
        
        if metrics.cpu_percent > self.performance_thresholds.max_cpu_percent:
            warnings.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
        
        if metrics.memory_percent > self.performance_thresholds.max_memory_percent:
            warnings.append(f"High memory usage: {metrics.memory_percent:.1f}%")
        
        if metrics.active_sessions > self.performance_thresholds.max_concurrent_sessions:
            warnings.append(f"High session count: {metrics.active_sessions}")
        
        if warnings:
            logger.warning(f"Performance thresholds exceeded: {', '.join(warnings)}")
            
            # Automatically adjust feature toggles if needed
            await self._auto_adjust_features(metrics)

    async def _auto_adjust_features(self, metrics: ResourceUsageMetrics):
        """Automatically adjust feature toggles based on performance"""
        try:
            # Disable non-essential features under high load
            if (metrics.cpu_percent > 90 or 
                metrics.memory_percent > 85 or 
                metrics.active_sessions > self.performance_thresholds.max_concurrent_sessions * 1.2):
                
                # Disable A/B testing
                self.config_manager.update_feature_toggle(
                    VoiceFeatureType.A_B_TESTING,
                    self.config_manager.config.feature_toggles[VoiceFeatureType.A_B_TESTING]._replace(enabled=False)
                )
                
                # Reduce analytics collection
                analytics_toggle = self.config_manager.config.feature_toggles.get(VoiceFeatureType.VOICE_ANALYTICS)
                if analytics_toggle:
                    self.config_manager.update_feature_toggle(
                        VoiceFeatureType.VOICE_ANALYTICS,
                        analytics_toggle._replace(rollout_percentage=50.0)
                    )
                
                logger.warning("Auto-adjusted features due to high resource usage")
            
        except Exception as e:
            logger.error(f"Error auto-adjusting features: {e}")

    async def _check_health(self):
        """Check overall system health"""
        try:
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'checks': {}
            }
            
            # Check Redis connectivity
            if self.redis_client:
                try:
                    self.redis_client.ping()
                    health_status['checks']['redis'] = 'healthy'
                except Exception as e:
                    health_status['checks']['redis'] = f'unhealthy: {e}'
                    health_status['status'] = 'degraded'
            
            # Check database connectivity
            if self.db_session:
                try:
                    self.db_session.execute('SELECT 1')
                    health_status['checks']['database'] = 'healthy'
                except Exception as e:
                    health_status['checks']['database'] = f'unhealthy: {e}'
                    health_status['status'] = 'degraded'
            
            # Check circuit breaker status
            if self.circuit_breaker.is_open():
                health_status['checks']['circuit_breaker'] = 'open'
                health_status['status'] = 'degraded'
            else:
                health_status['checks']['circuit_breaker'] = 'closed'
            
            # Store health status
            if self.redis_client:
                self.redis_client.setex(
                    'voice_health_status',
                    60,  # 1 minute TTL
                    json.dumps(health_status)
                )
            
        except Exception as e:
            logger.error(f"Error checking health: {e}")

    async def _update_feature_toggles(self):
        """Update feature toggles based on current conditions"""
        try:
            # Get current metrics
            metrics = self.resource_monitor.get_current_metrics()
            
            # Update rollout percentages based on performance
            if metrics.cpu_percent < 50 and metrics.memory_percent < 50:
                # System is healthy, can increase rollouts
                await self._increase_rollouts()
            elif metrics.cpu_percent > 80 or metrics.memory_percent > 80:
                # System under stress, decrease rollouts
                await self._decrease_rollouts()
            
        except Exception as e:
            logger.error(f"Error updating feature toggles: {e}")

    async def _increase_rollouts(self):
        """Gradually increase feature rollouts"""
        # Implementation for gradual rollout increase
        pass

    async def _decrease_rollouts(self):
        """Decrease feature rollouts under load"""
        # Implementation for rollout decrease
        pass

    async def _cleanup_stale_sessions(self):
        """Clean up stale voice sessions"""
        try:
            now = datetime.utcnow()
            stale_threshold = timedelta(minutes=30)
            
            stale_sessions = []
            for session_id, start_time in self.session_start_times.items():
                if now - start_time > stale_threshold:
                    stale_sessions.append(session_id)
            
            for session_id in stale_sessions:
                await self.end_voice_session(session_id, reason='stale_cleanup')
            
            if stale_sessions:
                logger.info(f"Cleaned up {len(stale_sessions)} stale sessions")
            
        except Exception as e:
            logger.error(f"Error cleaning up stale sessions: {e}")

    async def _cleanup_old_metrics(self):
        """Clean up old metrics data"""
        try:
            if self.redis_client:
                # Clean up metrics older than 24 hours
                cutoff = datetime.utcnow() - timedelta(hours=24)
                pattern = f"voice_metrics:{cutoff.strftime('%Y%m%d')}*"
                
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    logger.info(f"Cleaned up {len(keys)} old metric entries")
            
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {e}")

    @asynccontextmanager
    async def voice_session(self, session_id: str, user_id: str, operation_type: str):
        """Context manager for voice sessions with resource tracking"""
        try:
            # Check if session is allowed
            if not await self.can_start_session(user_id, operation_type):
                raise HTTPException(status_code=429, detail="Rate limit exceeded or resources unavailable")
            
            # Start session
            await self.start_voice_session(session_id, user_id, operation_type)
            
            yield session_id
            
        except Exception as e:
            logger.error(f"Error in voice session {session_id}: {e}")
            raise
        finally:
            # Always clean up session
            await self.end_voice_session(session_id)

    async def can_start_session(self, user_id: str, operation_type: str) -> bool:
        """Check if a new voice session can be started"""
        try:
            # Check rate limits
            if not await self.rate_limiter.check_rate_limit(user_id, operation_type):
                return False
            
            # Check resource availability
            metrics = self.resource_monitor.get_current_metrics()
            if (metrics.cpu_percent > self.performance_thresholds.max_cpu_percent or
                metrics.memory_percent > self.performance_thresholds.max_memory_percent or
                len(self.active_sessions) >= self.performance_thresholds.max_concurrent_sessions):
                return False
            
            # Check circuit breaker
            if self.circuit_breaker.is_open():
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking session availability: {e}")
            return False

    async def start_voice_session(self, session_id: str, user_id: str, operation_type: str):
        """Start tracking a voice session"""
        try:
            self.active_sessions.add(session_id)
            self.session_start_times[session_id] = datetime.utcnow()
            
            # Record session start in analytics
            if self.config_manager.is_feature_enabled(VoiceFeatureType.VOICE_ANALYTICS, user_id):
                # Log session start
                pass
            
            logger.debug(f"Started voice session {session_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error starting voice session {session_id}: {e}")
            raise

    async def end_voice_session(self, session_id: str, reason: str = 'completed'):
        """End tracking a voice session"""
        try:
            if session_id in self.active_sessions:
                self.active_sessions.remove(session_id)
            
            if session_id in self.session_start_times:
                start_time = self.session_start_times.pop(session_id)
                duration = datetime.utcnow() - start_time
                
                # Record session metrics
                logger.debug(f"Ended voice session {session_id} after {duration.total_seconds():.2f}s (reason: {reason})")
            
        except Exception as e:
            logger.error(f"Error ending voice session {session_id}: {e}")

    def get_production_config(self, user_id: str) -> Dict[str, Any]:
        """Get production-optimized configuration for client"""
        try:
            base_config = self.config_manager.get_config_for_client(user_id)
            
            # Add production-specific settings
            production_config = {
                **base_config,
                'resourceLimits': {
                    'maxConcurrentSessions': self.performance_thresholds.max_concurrent_sessions,
                    'maxResponseTimeMs': self.performance_thresholds.max_response_time_ms,
                    'maxMemoryMB': self.performance_thresholds.max_memory_mb
                },
                'monitoring': {
                    'enablePerformanceTracking': True,
                    'enableResourceMonitoring': True,
                    'reportingInterval': 60000  # 1 minute
                },
                'circuitBreaker': {
                    'enabled': True,
                    'isOpen': self.circuit_breaker.is_open(),
                    'failureThreshold': self.circuit_breaker.failure_threshold,
                    'recoveryTimeout': self.circuit_breaker.recovery_timeout
                }
            }
            
            return production_config
            
        except Exception as e:
            logger.error(f"Error getting production config: {e}")
            return self.config_manager.get_config_for_client(user_id)

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            metrics = self.resource_monitor.get_current_metrics()
            
            return {
                'timestamp': metrics.timestamp.isoformat(),
                'cpu': {
                    'percent': metrics.cpu_percent,
                    'threshold': self.performance_thresholds.max_cpu_percent
                },
                'memory': {
                    'percent': metrics.memory_percent,
                    'mb': metrics.memory_mb,
                    'threshold_percent': self.performance_thresholds.max_memory_percent,
                    'threshold_mb': self.performance_thresholds.max_memory_mb
                },
                'sessions': {
                    'active': len(self.active_sessions),
                    'max': self.performance_thresholds.max_concurrent_sessions
                },
                'circuit_breaker': {
                    'is_open': self.circuit_breaker.is_open(),
                    'failure_count': self.circuit_breaker.failure_count,
                    'last_failure': self.circuit_breaker.last_failure_time.isoformat() if self.circuit_breaker.last_failure_time else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}


class VoiceResourceMonitor:
    """Monitors system resource usage"""
    
    def __init__(self):
        self.process = psutil.Process()
    
    def get_current_metrics(self) -> ResourceUsageMetrics:
        """Get current resource usage metrics"""
        try:
            # Get system-wide metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Get process-specific metrics
            process_memory = self.process.memory_info()
            
            return ResourceUsageMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_mb=process_memory.rss / 1024 / 1024,
                active_sessions=0,  # Will be set by caller
                concurrent_requests=0,  # Will be set by caller
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error getting resource metrics: {e}")
            return ResourceUsageMetrics(
                cpu_percent=0,
                memory_percent=0,
                memory_mb=0,
                active_sessions=0,
                concurrent_requests=0,
                timestamp=datetime.utcnow()
            )


class VoiceProductionRateLimiter:
    """Production-grade rate limiter for voice operations"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.local_cache = {}  # Fallback for when Redis is unavailable
    
    async def check_rate_limit(self, user_id: str, operation_type: str) -> bool:
        """Check if operation is within rate limits"""
        try:
            if self.redis_client:
                return await self._check_redis_rate_limit(user_id, operation_type)
            else:
                return self._check_local_rate_limit(user_id, operation_type)
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Fail open
    
    async def _check_redis_rate_limit(self, user_id: str, operation_type: str) -> bool:
        """Check rate limit using Redis"""
        # Implementation using Redis sliding window
        # This is a simplified version - production would use more sophisticated algorithms
        key = f"rate_limit:{user_id}:{operation_type}"
        current_time = int(time.time())
        window_size = 60  # 1 minute window
        limit = 60  # 60 requests per minute
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, current_time - window_size)
        pipe.zcard(key)
        pipe.zadd(key, {str(current_time): current_time})
        pipe.expire(key, window_size)
        
        results = pipe.execute()
        current_count = results[1]
        
        return current_count < limit
    
    def _check_local_rate_limit(self, user_id: str, operation_type: str) -> bool:
        """Check rate limit using local cache (fallback)"""
        key = f"{user_id}:{operation_type}"
        current_time = time.time()
        window_size = 60
        limit = 60
        
        if key not in self.local_cache:
            self.local_cache[key] = []
        
        # Clean old entries
        self.local_cache[key] = [
            timestamp for timestamp in self.local_cache[key]
            if current_time - timestamp < window_size
        ]
        
        # Check limit
        if len(self.local_cache[key]) >= limit:
            return False
        
        # Add current request
        self.local_cache[key].append(current_time)
        return True


class VoiceCircuitBreaker:
    """Circuit breaker for voice operations"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = 'closed'  # closed, open, half-open
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.state == 'open':
            # Check if recovery timeout has passed
            if (self.last_failure_time and 
                datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)):
                self.state = 'half-open'
                return False
            return True
        return False
    
    def record_success(self):
        """Record a successful operation"""
        if self.state == 'half-open':
            self.state = 'closed'
            self.failure_count = 0
    
    def record_failure(self):
        """Record a failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


# Global production manager instance
_production_manager: Optional[VoiceProductionManager] = None

def get_voice_production_manager(
    config_manager: VoiceConfigManager,
    redis_client: Optional[redis.Redis] = None,
    db_session: Optional[Session] = None
) -> VoiceProductionManager:
    """Get global voice production manager instance"""
    global _production_manager
    if _production_manager is None:
        _production_manager = VoiceProductionManager(config_manager, redis_client, db_session)
    return _production_manager