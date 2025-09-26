# Optimized Data Processing Pipelines
# Minimizes latency, supports batch processing, and maintains data consistency

import asyncio
import threading
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from queue import Queue, PriorityQueue, Empty
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing
from contextlib import contextmanager
import redis
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import psutil
import gc
from functools import wraps, lru_cache
import pickle
import hashlib
import gzip
import io

# Import local modules
from .models import db, User
from .models_support import Ticket, TicketComment, TicketActivity, PerformanceMetric
from .error_handling import error_handler, ErrorCategory, ErrorSeverity, ErrorContext
from .realtime_sync import sync_service, IntegrationEvent, EventType

# Setup logging
logger = logging.getLogger(__name__)

class PipelineStage(Enum):
    """Pipeline processing stages"""
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    VALIDATE = "validate"
    AGGREGATE = "aggregate"
    CACHE = "cache"
    NOTIFY = "notify"

class ProcessingPriority(Enum):
    """Processing priority levels"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BATCH = 5

class DataConsistencyLevel(Enum):
    """Data consistency levels"""
    STRONG = "strong"  # ACID compliance
    EVENTUAL = "eventual"  # Eventually consistent
    WEAK = "weak"  # Best effort

@dataclass
class PipelineTask:
    """Represents a data processing task"""
    task_id: str
    task_type: str
    priority: ProcessingPriority
    data: Any
    metadata: Dict[str, Any]
    created_at: datetime
    consistency_level: DataConsistencyLevel = DataConsistencyLevel.EVENTUAL
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 300  # seconds
    
    def __lt__(self, other):
        return self.priority.value < other.priority.value

@dataclass
class PipelineMetrics:
    """Pipeline performance metrics"""
    tasks_processed: int = 0
    tasks_failed: int = 0
    average_processing_time: float = 0.0
    throughput_per_second: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    queue_size: int = 0
    cache_hit_rate: float = 0.0
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()

class CacheManager:
    """Intelligent caching system for data pipeline"""
    
    def __init__(self, redis_client, config: Dict[str, Any]):
        self.redis_client = redis_client
        self.config = config
        self.default_ttl = config.get('default_ttl', 3600)  # 1 hour
        self.max_memory_usage = config.get('max_memory_mb', 512)  # 512 MB
        self.compression_enabled = config.get('compression', True)
        
        # In-memory cache for frequently accessed data
        self.memory_cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
    
    def get(self, key: str, default=None) -> Any:
        """Get cached data with multi-level caching"""
        # Check memory cache first
        if key in self.memory_cache:
            self.cache_stats['hits'] += 1
            return self.memory_cache[key]['data']
        
        # Check Redis cache
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(f"cache:{key}")
                if cached_data:
                    if self.compression_enabled:
                        cached_data = gzip.decompress(cached_data)
                    
                    data = pickle.loads(cached_data)
                    
                    # Store in memory cache for faster access
                    self._store_in_memory(key, data)
                    
                    self.cache_stats['hits'] += 1
                    return data
            except Exception as e:
                logger.error(f"Cache read error: {e}")
        
        self.cache_stats['misses'] += 1
        return default
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Set cached data with multi-level caching"""
        if ttl is None:
            ttl = self.default_ttl
        
        try:
            # Store in memory cache
            self._store_in_memory(key, data, ttl)
            
            # Store in Redis cache
            if self.redis_client:
                serialized_data = pickle.dumps(data)
                
                if self.compression_enabled:
                    serialized_data = gzip.compress(serialized_data)
                
                self.redis_client.setex(f"cache:{key}", ttl, serialized_data)
            
            return True
        except Exception as e:
            logger.error(f"Cache write error: {e}")
            return False
    
    def delete(self, key: str):
        """Delete cached data"""
        # Remove from memory cache
        if key in self.memory_cache:
            del self.memory_cache[key]
        
        # Remove from Redis cache
        if self.redis_client:
            try:
                self.redis_client.delete(f"cache:{key}")
            except Exception as e:
                logger.error(f"Cache delete error: {e}")
    
    def _store_in_memory(self, key: str, data: Any, ttl: int = None):
        """Store data in memory cache with size management"""
        if ttl is None:
            ttl = self.default_ttl
        
        # Check memory usage
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        if current_memory > self.max_memory_usage:
            self._evict_memory_cache()
        
        self.memory_cache[key] = {
            'data': data,
            'expires_at': datetime.utcnow() + timedelta(seconds=ttl),
            'access_count': 1,
            'last_accessed': datetime.utcnow()
        }
    
    def _evict_memory_cache(self):
        """Evict least recently used items from memory cache"""
        if not self.memory_cache:
            return
        
        # Sort by last accessed time and remove oldest 25%
        sorted_items = sorted(
            self.memory_cache.items(),
            key=lambda x: x[1]['last_accessed']
        )
        
        items_to_remove = len(sorted_items) // 4
        for i in range(items_to_remove):
            key = sorted_items[i][0]
            del self.memory_cache[key]
            self.cache_stats['evictions'] += 1
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / max(1, total_requests)) * 100
        
        return {
            'hit_rate': hit_rate,
            'total_hits': self.cache_stats['hits'],
            'total_misses': self.cache_stats['misses'],
            'total_evictions': self.cache_stats['evictions'],
            'memory_cache_size': len(self.memory_cache),
            'memory_usage_mb': psutil.Process().memory_info().rss / 1024 / 1024
        }

class DataProcessor:
    """Base class for data processors"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.metrics = PipelineMetrics()
        self.processing_times = []
    
    async def process(self, task: PipelineTask) -> Any:
        """Process a pipeline task"""
        start_time = time.time()
        
        try:
            result = await self._process_impl(task)
            
            # Update metrics
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            self.metrics.tasks_processed += 1
            self._update_metrics()
            
            return result
            
        except Exception as e:
            self.metrics.tasks_failed += 1
            logger.error(f"Processing error in {self.name}: {e}")
            raise
    
    async def _process_impl(self, task: PipelineTask) -> Any:
        """Implementation-specific processing logic"""
        raise NotImplementedError
    
    def _update_metrics(self):
        """Update processor metrics"""
        if self.processing_times:
            self.metrics.average_processing_time = sum(self.processing_times) / len(self.processing_times)
            
            # Keep only recent processing times
            if len(self.processing_times) > 1000:
                self.processing_times = self.processing_times[-500:]
        
        self.metrics.last_updated = datetime.utcnow()

class TicketDataProcessor(DataProcessor):
    """Processor for ticket-related data"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("TicketDataProcessor", config)
        self.batch_size = config.get('batch_size', 100)
    
    async def _process_impl(self, task: PipelineTask) -> Any:
        """Process ticket data"""
        if task.task_type == "ticket_analytics":
            return await self._process_ticket_analytics(task)
        elif task.task_type == "ticket_batch_update":
            return await self._process_ticket_batch_update(task)
        elif task.task_type == "ticket_aggregation":
            return await self._process_ticket_aggregation(task)
        else:
            raise ValueError(f"Unknown task type: {task.task_type}")
    
    async def _process_ticket_analytics(self, task: PipelineTask) -> Dict[str, Any]:
        """Process ticket analytics"""
        filters = task.data.get('filters', {})
        date_range = task.data.get('date_range', {})
        
        # Build query
        query = db.session.query(Ticket)
        
        if date_range.get('start'):
            query = query.filter(Ticket.created_at >= date_range['start'])
        if date_range.get('end'):
            query = query.filter(Ticket.created_at <= date_range['end'])
        
        if filters.get('status'):
            query = query.filter(Ticket.status.in_(filters['status']))
        if filters.get('priority'):
            query = query.filter(Ticket.priority.in_(filters['priority']))
        if filters.get('category'):
            query = query.filter(Ticket.category.in_(filters['category']))
        
        # Execute query and process results
        tickets = query.all()
        
        analytics = {
            'total_tickets': len(tickets),
            'status_distribution': {},
            'priority_distribution': {},
            'category_distribution': {},
            'resolution_times': [],
            'created_by_day': {},
            'average_resolution_time': 0
        }
        
        # Process ticket data
        for ticket in tickets:
            # Status distribution
            status = ticket.status.value
            analytics['status_distribution'][status] = analytics['status_distribution'].get(status, 0) + 1
            
            # Priority distribution
            priority = ticket.priority.value
            analytics['priority_distribution'][priority] = analytics['priority_distribution'].get(priority, 0) + 1
            
            # Category distribution
            category = ticket.category.value
            analytics['category_distribution'][category] = analytics['category_distribution'].get(category, 0) + 1
            
            # Resolution time
            if ticket.resolved_at:
                resolution_time = (ticket.resolved_at - ticket.created_at).total_seconds() / 3600  # hours
                analytics['resolution_times'].append(resolution_time)
            
            # Created by day
            day = ticket.created_at.date().isoformat()
            analytics['created_by_day'][day] = analytics['created_by_day'].get(day, 0) + 1
        
        # Calculate average resolution time
        if analytics['resolution_times']:
            analytics['average_resolution_time'] = sum(analytics['resolution_times']) / len(analytics['resolution_times'])
        
        return analytics
    
    async def _process_ticket_batch_update(self, task: PipelineTask) -> Dict[str, Any]:
        """Process batch ticket updates"""
        updates = task.data.get('updates', [])
        results = {'updated': 0, 'failed': 0, 'errors': []}
        
        # Process in batches
        for i in range(0, len(updates), self.batch_size):
            batch = updates[i:i + self.batch_size]
            
            try:
                with db.session.begin():
                    for update in batch:
                        ticket_id = update.get('ticket_id')
                        fields = update.get('fields', {})
                        
                        ticket = Ticket.query.get(ticket_id)
                        if ticket:
                            for field, value in fields.items():
                                if hasattr(ticket, field):
                                    setattr(ticket, field, value)
                            
                            ticket.updated_at = datetime.utcnow()
                            results['updated'] += 1
                        else:
                            results['failed'] += 1
                            results['errors'].append(f"Ticket {ticket_id} not found")
                
            except Exception as e:
                results['failed'] += len(batch)
                results['errors'].append(f"Batch update error: {str(e)}")
                logger.error(f"Batch update error: {e}")
        
        return results
    
    async def _process_ticket_aggregation(self, task: PipelineTask) -> Dict[str, Any]:
        """Process ticket data aggregation"""
        aggregation_type = task.data.get('type', 'daily')
        date_range = task.data.get('date_range', {})
        
        # Use pandas for efficient aggregation
        query = """
        SELECT 
            DATE(created_at) as date,
            status,
            priority,
            category,
            COUNT(*) as count,
            AVG(CASE WHEN resolved_at IS NOT NULL 
                THEN EXTRACT(EPOCH FROM (resolved_at - created_at))/3600 
                ELSE NULL END) as avg_resolution_hours
        FROM tickets
        WHERE created_at >= :start_date AND created_at <= :end_date
        GROUP BY DATE(created_at), status, priority, category
        ORDER BY date
        """
        
        # Execute query with pandas
        df = pd.read_sql_query(
            query,
            db.engine,
            params={
                'start_date': date_range.get('start', datetime.utcnow() - timedelta(days=30)),
                'end_date': date_range.get('end', datetime.utcnow())
            }
        )
        
        # Process aggregation
        if aggregation_type == 'daily':
            aggregated = df.groupby('date').agg({
                'count': 'sum',
                'avg_resolution_hours': 'mean'
            }).to_dict('index')
        elif aggregation_type == 'status':
            aggregated = df.groupby('status').agg({
                'count': 'sum',
                'avg_resolution_hours': 'mean'
            }).to_dict('index')
        elif aggregation_type == 'priority':
            aggregated = df.groupby('priority').agg({
                'count': 'sum',
                'avg_resolution_hours': 'mean'
            }).to_dict('index')
        else:
            aggregated = df.to_dict('records')
        
        return {
            'aggregation_type': aggregation_type,
            'data': aggregated,
            'total_records': len(df),
            'date_range': date_range
        }

class DataPipeline:
    """Main data processing pipeline"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.task_queue = PriorityQueue()
        self.processors = {}
        self.cache_manager = None
        self.metrics = PipelineMetrics()
        self.running = False
        self.worker_threads = []
        self.max_workers = config.get('max_workers', multiprocessing.cpu_count())
        self.batch_size = config.get('batch_size', 100)
        
        # Initialize Redis for caching
        redis_url = config.get('redis_url', 'redis://localhost:6379')
        try:
            redis_client = redis.from_url(redis_url, decode_responses=False)
            self.cache_manager = CacheManager(redis_client, config.get('cache', {}))
        except Exception as e:
            logger.error(f"Failed to connect to Redis for caching: {e}")
        
        # Initialize processors
        self._init_processors()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _init_processors(self):
        """Initialize data processors"""
        self.processors['ticket'] = TicketDataProcessor(self.config.get('ticket_processor', {}))
        # Add more processors as needed
    
    def _start_background_tasks(self):
        """Start background processing tasks"""
        self.running = True
        
        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.worker_threads.append(worker)
        
        # Start metrics collection thread
        metrics_thread = threading.Thread(target=self._metrics_loop, daemon=True)
        metrics_thread.start()
        
        logger.info(f"Started data pipeline with {self.max_workers} workers")
    
    def submit_task(self, task: PipelineTask) -> str:
        """Submit a task to the pipeline"""
        # Check cache first for read operations
        if task.task_type.endswith('_read') or task.task_type.endswith('_analytics'):
            cache_key = self._generate_cache_key(task)
            if self.cache_manager:
                cached_result = self.cache_manager.get(cache_key)
                if cached_result is not None:
                    logger.info(f"Cache hit for task {task.task_id}")
                    return cached_result
        
        # Add task to queue
        self.task_queue.put(task)
        logger.info(f"Submitted task {task.task_id} with priority {task.priority.value}")
        
        return task.task_id
    
    def submit_batch_task(self, task_type: str, data_items: List[Any], 
                         priority: ProcessingPriority = ProcessingPriority.NORMAL) -> List[str]:
        """Submit multiple items as batch tasks"""
        task_ids = []
        
        # Split into batches
        for i in range(0, len(data_items), self.batch_size):
            batch_data = data_items[i:i + self.batch_size]
            
            task = PipelineTask(
                task_id=f"batch_{task_type}_{int(time.time())}_{i}",
                task_type=f"{task_type}_batch",
                priority=priority,
                data={'items': batch_data, 'batch_index': i},
                metadata={'batch_size': len(batch_data), 'total_items': len(data_items)},
                created_at=datetime.utcnow()
            )
            
            task_id = self.submit_task(task)
            task_ids.append(task_id)
        
        return task_ids
    
    def _worker_loop(self):
        """Main worker loop for processing tasks"""
        while self.running:
            try:
                # Get task from queue with timeout
                task = self.task_queue.get(timeout=1)
                
                # Process task
                result = asyncio.run(self._process_task(task))
                
                # Cache result if applicable
                if task.task_type.endswith('_analytics') or task.task_type.endswith('_aggregation'):
                    cache_key = self._generate_cache_key(task)
                    if self.cache_manager:
                        cache_ttl = self._get_cache_ttl(task)
                        self.cache_manager.set(cache_key, result, cache_ttl)
                
                # Emit real-time event if sync service is available
                if sync_service:
                    event = IntegrationEvent(
                        event_type=EventType.PERFORMANCE_METRIC,
                        entity_id=task.task_id,
                        entity_type="pipeline_task",
                        data={'task_type': task.task_type, 'status': 'completed'},
                        timestamp=datetime.utcnow()
                    )
                    sync_service.emit_event(event)
                
                self.task_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
                if error_handler:
                    context = ErrorContext(
                        operation='pipeline_worker',
                        component='data_pipeline'
                    )
                    error_handler.handle_error(e, context, ErrorSeverity.MEDIUM, ErrorCategory.SYSTEM)
    
    async def _process_task(self, task: PipelineTask) -> Any:
        """Process a single task"""
        start_time = time.time()
        
        try:
            # Determine processor based on task type
            processor_type = task.task_type.split('_')[0]
            processor = self.processors.get(processor_type)
            
            if not processor:
                raise ValueError(f"No processor found for task type: {task.task_type}")
            
            # Process task
            result = await processor.process(task)
            
            # Update metrics
            processing_time = time.time() - start_time
            self.metrics.tasks_processed += 1
            self.metrics.average_processing_time = (
                (self.metrics.average_processing_time * (self.metrics.tasks_processed - 1) + processing_time) /
                self.metrics.tasks_processed
            )
            
            return result
            
        except Exception as e:
            self.metrics.tasks_failed += 1
            
            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                logger.warning(f"Retrying task {task.task_id} (attempt {task.retry_count})")
                
                # Add back to queue with delay
                await asyncio.sleep(2 ** task.retry_count)  # Exponential backoff
                self.task_queue.put(task)
                return None
            else:
                logger.error(f"Task {task.task_id} failed after {task.max_retries} retries: {e}")
                raise
    
    def _generate_cache_key(self, task: PipelineTask) -> str:
        """Generate cache key for task"""
        # Create hash of task data for cache key
        task_data_str = json.dumps(task.data, sort_keys=True, default=str)
        data_hash = hashlib.md5(task_data_str.encode()).hexdigest()
        return f"{task.task_type}:{data_hash}"
    
    def _get_cache_ttl(self, task: PipelineTask) -> int:
        """Get cache TTL based on task type"""
        if task.task_type.endswith('_analytics'):
            return 1800  # 30 minutes
        elif task.task_type.endswith('_aggregation'):
            return 3600  # 1 hour
        else:
            return 300   # 5 minutes
    
    def _metrics_loop(self):
        """Background loop for collecting metrics"""
        while self.running:
            try:
                # Update system metrics
                self.metrics.queue_size = self.task_queue.qsize()
                self.metrics.memory_usage_mb = psutil.Process().memory_info().rss / 1024 / 1024
                self.metrics.cpu_usage_percent = psutil.Process().cpu_percent()
                
                # Calculate throughput
                if self.metrics.tasks_processed > 0:
                    uptime_seconds = (datetime.utcnow() - self.metrics.last_updated).total_seconds()
                    if uptime_seconds > 0:
                        self.metrics.throughput_per_second = self.metrics.tasks_processed / uptime_seconds
                
                # Update cache hit rate
                if self.cache_manager:
                    cache_stats = self.cache_manager.get_cache_stats()
                    self.metrics.cache_hit_rate = cache_stats['hit_rate']
                
                self.metrics.last_updated = datetime.utcnow()
                
                # Store metrics in database
                self._store_metrics()
                
                time.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                time.sleep(60)
    
    def _store_metrics(self):
        """Store metrics in database"""
        try:
            metric = PerformanceMetric(
                metric_name='data_pipeline',
                metric_value=json.dumps(asdict(self.metrics), default=str),
                timestamp=datetime.utcnow()
            )
            db.session.add(metric)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")
            db.session.rollback()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current pipeline metrics"""
        metrics_dict = asdict(self.metrics)
        
        # Add processor metrics
        metrics_dict['processors'] = {}
        for name, processor in self.processors.items():
            metrics_dict['processors'][name] = asdict(processor.metrics)
        
        # Add cache metrics
        if self.cache_manager:
            metrics_dict['cache'] = self.cache_manager.get_cache_stats()
        
        return metrics_dict
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get pipeline health status"""
        return {
            'status': 'healthy' if self.running else 'stopped',
            'active_workers': len([t for t in self.worker_threads if t.is_alive()]),
            'queue_size': self.task_queue.qsize(),
            'cache_available': self.cache_manager is not None,
            'metrics': self.get_metrics()
        }
    
    def stop(self):
        """Stop the pipeline"""
        self.running = False
        logger.info("Data pipeline stopped")

# Global pipeline instance
data_pipeline = None

def init_data_pipeline(config: Dict[str, Any]):
    """Initialize the global data pipeline"""
    global data_pipeline
    data_pipeline = DataPipeline(config)
    return data_pipeline

# Convenience functions for common operations

def process_ticket_analytics(filters: Dict[str, Any], date_range: Dict[str, Any], 
                           priority: ProcessingPriority = ProcessingPriority.NORMAL) -> str:
    """Submit ticket analytics task"""
    if not data_pipeline:
        raise RuntimeError("Data pipeline not initialized")
    
    task = PipelineTask(
        task_id=f"ticket_analytics_{int(time.time())}",
        task_type="ticket_analytics",
        priority=priority,
        data={'filters': filters, 'date_range': date_range},
        metadata={'operation': 'analytics'},
        created_at=datetime.utcnow()
    )
    
    return data_pipeline.submit_task(task)

def process_batch_ticket_updates(updates: List[Dict[str, Any]], 
                                priority: ProcessingPriority = ProcessingPriority.HIGH) -> List[str]:
    """Submit batch ticket update tasks"""
    if not data_pipeline:
        raise RuntimeError("Data pipeline not initialized")
    
    return data_pipeline.submit_batch_task('ticket_update', updates, priority)

def get_pipeline_health() -> Dict[str, Any]:
    """Get pipeline health status"""
    if not data_pipeline:
        return {'status': 'unhealthy', 'reason': 'Pipeline not initialized'}
    
    return data_pipeline.get_health_status()

# Decorator for caching function results
def cache_result(ttl: int = 3600, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not data_pipeline or not data_pipeline.cache_manager:
                return func(*args, **kwargs)
            
            # Generate cache key
            key_data = f"{func.__name__}:{args}:{kwargs}"
            cache_key = f"{key_prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
            
            # Check cache
            cached_result = data_pipeline.cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            data_pipeline.cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator