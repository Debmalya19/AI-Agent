"""
Voice Processing Rate Limiter and Resource Usage Monitoring
Implements rate limiting, resource monitoring, and performance optimization
"""

import time
import asyncio
import logging
import psutil
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import redis
from fastapi import HTTPException
import json

logger = logging.getLogger(__name__)


@dataclass
class ResourceUsage:
    """Current resource usage metrics"""
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    active_sessions: int
    queue_size: int
    timestamp: datetime


@dataclass
class RateLimitResult:
    """Rate limit check result"""
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None
    reason: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Performance tracking metrics"""
    request_count: int = 0
    average_response_time: float = 0.0
    error_rate: float = 0.0
    queue_wait_time: float = 0.0
    resource_usage: Optional[ResourceUsage] = None


