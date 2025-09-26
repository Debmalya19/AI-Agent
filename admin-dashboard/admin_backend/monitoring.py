# Real-time Monitoring, Historical Analysis, and Configuration Management
# Comprehensive monitoring system for the admin dashboard

import asyncio
import threading
import time
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict, deque
import statistics
from contextlib import contextmanager
import redis
import psutil
import requests
from sqlalchemy import create_engine, text, event, func
from sqlalchemy.orm import sessionmaker, Session
from flask import current_app
import yaml
import configparser
from pathlib import Path
import hashlib
import pickle
from concurrent.futures import ThreadPoolExecutor
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import numpy as np
from scipy import stats

# Import local modules
from .models import db, User
from .models_support import Ticket, TicketComment, PerformanceMetric, CustomerSatisfaction
from .error_handling import error_handler, ErrorCategory, ErrorSeverity, ErrorContext
from .realtime_sync import sync_service, IntegrationEvent, EventType
from .data_pipeline import data_pipeline

# Setup logging
logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of metrics to monitor"""
    SYSTEM = "system"
    APPLICATION = "application"
    BUSINESS = "business"
    SECURITY = "security"
    PERFORMANCE = "performance"
    USER_EXPERIENCE = "user_experience"

class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class MonitoringStatus(Enum):
    """Monitoring component status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"

@dataclass
class MetricDefinition:
    """Definition of a metric to monitor"""
    name: str
    metric_type: MetricType
    description: str
    unit: str
    collection_interval: int  # seconds
    retention_period: int  # days
    thresholds: Dict[str, float] = field(default_factory=dict)
    aggregation_methods: List[str] = field(default_factory=lambda: ['avg', 'min', 'max'])
    enabled: bool = True
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class MetricValue:
    """A metric value with timestamp"""
    metric_name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Alert:
    """Alert definition and state"""
    alert_id: str
    metric_name: str
    severity: AlertSeverity
    condition: str
    threshold: float
    current_value: float
    message: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HealthCheck:
    """Health check definition"""
    name: str
    description: str
    check_function: Callable[[], bool]
    interval: int  # seconds
    timeout: int  # seconds
    enabled: bool = True
    last_check: Optional[datetime] = None
    last_status: MonitoringStatus = MonitoringStatus.UNKNOWN
    consecutive_failures: int = 0
    max_failures: int = 3

class ConfigurationManager:
    """Manages system configuration with hot reloading"""
    
    def __init__(self, config_dir: str):
        self.config_dir = Path(config_dir)
        self.config_files = {}
        self.config_data = {}
        self.watchers = {}
        self.callbacks = defaultdict(list)
        self.last_modified = {}
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Start file watcher
        self.watching = True
        self.watcher_thread = threading.Thread(target=self._watch_config_files, daemon=True)
        self.watcher_thread.start()
    
    def register_config_file(self, name: str, filename: str, file_type: str = 'yaml'):
        """Register a configuration file to monitor"""
        file_path = self.config_dir / filename
        self.config_files[name] = {
            'path': file_path,
            'type': file_type,
            'last_modified': None
        }
        
        # Load initial configuration
        self._load_config_file(name)
        
        logger.info(f"Registered config file: {name} -> {file_path}")
    
    def get_config(self, name: str, key: str = None, default=None):
        """Get configuration value"""
        if name not in self.config_data:
            return default
        
        config = self.config_data[name]
        
        if key is None:
            return config
        
        # Support nested keys with dot notation
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set_config(self, name: str, key: str, value: Any, persist: bool = True):
        """Set configuration value"""
        if name not in self.config_data:
            self.config_data[name] = {}
        
        # Support nested keys with dot notation
        keys = key.split('.')
        config = self.config_data[name]
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        
        # Persist to file if requested
        if persist and name in self.config_files:
            self._save_config_file(name)
        
        # Notify callbacks
        self._notify_callbacks(name, key, value)
    
    def register_callback(self, name: str, callback: Callable[[str, str, Any], None]):
        """Register callback for configuration changes"""
        self.callbacks[name].append(callback)
    
    def _load_config_file(self, name: str):
        """Load configuration from file"""
        if name not in self.config_files:
            return
        
        file_info = self.config_files[name]
        file_path = file_info['path']
        
        if not file_path.exists():
            # Create default config file
            self._create_default_config(name)
            return
        
        try:
            with open(file_path, 'r') as f:
                if file_info['type'] == 'yaml':
                    config = yaml.safe_load(f) or {}
                elif file_info['type'] == 'json':
                    config = json.load(f)
                elif file_info['type'] == 'ini':
                    parser = configparser.ConfigParser()
                    parser.read(file_path)
                    config = {section: dict(parser[section]) for section in parser.sections()}
                else:
                    logger.error(f"Unsupported config file type: {file_info['type']}")
                    return
            
            self.config_data[name] = config
            file_info['last_modified'] = file_path.stat().st_mtime
            
            logger.info(f"Loaded config file: {name}")
            
        except Exception as e:
            logger.error(f"Failed to load config file {name}: {e}")
    
    def _save_config_file(self, name: str):
        """Save configuration to file"""
        if name not in self.config_files or name not in self.config_data:
            return
        
        file_info = self.config_files[name]
        file_path = file_info['path']
        config = self.config_data[name]
        
        try:
            with open(file_path, 'w') as f:
                if file_info['type'] == 'yaml':
                    yaml.dump(config, f, default_flow_style=False)
                elif file_info['type'] == 'json':
                    json.dump(config, f, indent=2)
                elif file_info['type'] == 'ini':
                    parser = configparser.ConfigParser()
                    for section, values in config.items():
                        parser[section] = values
                    parser.write(f)
            
            file_info['last_modified'] = file_path.stat().st_mtime
            logger.info(f"Saved config file: {name}")
            
        except Exception as e:
            logger.error(f"Failed to save config file {name}: {e}")
    
    def _create_default_config(self, name: str):
        """Create default configuration file"""
        default_configs = {
            'monitoring': {
                'metrics': {
                    'collection_interval': 60,
                    'retention_days': 30,
                    'batch_size': 100
                },
                'alerts': {
                    'enabled': True,
                    'email_notifications': False,
                    'webhook_notifications': False
                },
                'health_checks': {
                    'enabled': True,
                    'interval': 300,
                    'timeout': 30
                }
            },
            'dashboard': {
                'refresh_interval': 30,
                'max_data_points': 1000,
                'auto_refresh': True,
                'theme': 'light'
            },
            'integration': {
                'ai_agent_url': 'http://localhost:8000',
                'sync_interval': 60,
                'batch_size': 50,
                'timeout': 30
            }
        }
        
        if name in default_configs:
            self.config_data[name] = default_configs[name]
            self._save_config_file(name)
    
    def _watch_config_files(self):
        """Watch configuration files for changes"""
        while self.watching:
            try:
                for name, file_info in self.config_files.items():
                    file_path = file_info['path']
                    
                    if file_path.exists():
                        current_mtime = file_path.stat().st_mtime
                        last_mtime = file_info.get('last_modified', 0)
                        
                        if current_mtime > last_mtime:
                            logger.info(f"Config file changed: {name}")
                            self._load_config_file(name)
                            self._notify_callbacks(name, None, None)
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Config watcher error: {e}")
                time.sleep(10)
    
    def _notify_callbacks(self, name: str, key: str, value: Any):
        """Notify registered callbacks of configuration changes"""
        for callback in self.callbacks[name]:
            try:
                callback(name, key, value)
            except Exception as e:
                logger.error(f"Config callback error: {e}")
    
    def stop(self):
        """Stop the configuration manager"""
        self.watching = False
        if self.watcher_thread.is_alive():
            self.watcher_thread.join(timeout=5)

class MetricsCollector:
    """Collects and stores metrics"""
    
    def __init__(self, config_manager: ConfigurationManager, redis_client=None):
        self.config_manager = config_manager
        self.redis_client = redis_client
        self.metrics_definitions = {}
        self.metrics_buffer = deque(maxlen=10000)
        self.collection_threads = {}
        self.running = False
        
        # Initialize default metrics
        self._init_default_metrics()
        
        # Start collection
        self.start_collection()
    
    def _init_default_metrics(self):
        """Initialize default system and application metrics"""
        default_metrics = [
            MetricDefinition(
                name="system.cpu_usage",
                metric_type=MetricType.SYSTEM,
                description="CPU usage percentage",
                unit="percent",
                collection_interval=60,
                retention_period=30,
                thresholds={'warning': 80, 'critical': 95}
            ),
            MetricDefinition(
                name="system.memory_usage",
                metric_type=MetricType.SYSTEM,
                description="Memory usage percentage",
                unit="percent",
                collection_interval=60,
                retention_period=30,
                thresholds={'warning': 85, 'critical': 95}
            ),
            MetricDefinition(
                name="system.disk_usage",
                metric_type=MetricType.SYSTEM,
                description="Disk usage percentage",
                unit="percent",
                collection_interval=300,
                retention_period=30,
                thresholds={'warning': 80, 'critical': 90}
            ),
            MetricDefinition(
                name="app.active_users",
                metric_type=MetricType.APPLICATION,
                description="Number of active users",
                unit="count",
                collection_interval=300,
                retention_period=90
            ),
            MetricDefinition(
                name="app.response_time",
                metric_type=MetricType.PERFORMANCE,
                description="Average response time",
                unit="milliseconds",
                collection_interval=60,
                retention_period=30,
                thresholds={'warning': 1000, 'critical': 2000}
            ),
            MetricDefinition(
                name="business.tickets_created",
                metric_type=MetricType.BUSINESS,
                description="Number of tickets created",
                unit="count",
                collection_interval=300,
                retention_period=365
            ),
            MetricDefinition(
                name="business.tickets_resolved",
                metric_type=MetricType.BUSINESS,
                description="Number of tickets resolved",
                unit="count",
                collection_interval=300,
                retention_period=365
            ),
            MetricDefinition(
                name="security.failed_logins",
                metric_type=MetricType.SECURITY,
                description="Number of failed login attempts",
                unit="count",
                collection_interval=60,
                retention_period=90,
                thresholds={'warning': 10, 'critical': 50}
            )
        ]
        
        for metric in default_metrics:
            self.register_metric(metric)
    
    def register_metric(self, metric: MetricDefinition):
        """Register a metric for collection"""
        self.metrics_definitions[metric.name] = metric
        logger.info(f"Registered metric: {metric.name}")
    
    def collect_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None, metadata: Dict[str, Any] = None):
        """Collect a metric value"""
        if metric_name not in self.metrics_definitions:
            logger.warning(f"Unknown metric: {metric_name}")
            return
        
        metric_value = MetricValue(
            metric_name=metric_name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {},
            metadata=metadata or {}
        )
        
        # Add to buffer
        self.metrics_buffer.append(metric_value)
        
        # Store in Redis for real-time access
        if self.redis_client:
            try:
                key = f"metric:{metric_name}:latest"
                data = {
                    'value': value,
                    'timestamp': metric_value.timestamp.isoformat(),
                    'tags': tags or {},
                    'metadata': metadata or {}
                }
                self.redis_client.setex(key, 3600, json.dumps(data))  # 1 hour TTL
            except Exception as e:
                logger.error(f"Failed to store metric in Redis: {e}")
        
        # Store in database (batch processing)
        if len(self.metrics_buffer) >= 100:
            self._flush_metrics_buffer()
    
    def start_collection(self):
        """Start automatic metric collection"""
        self.running = True
        
        # Start collection threads for each metric
        for metric_name, metric_def in self.metrics_definitions.items():
            if metric_def.enabled:
                thread = threading.Thread(
                    target=self._collection_loop,
                    args=(metric_name, metric_def),
                    daemon=True
                )
                thread.start()
                self.collection_threads[metric_name] = thread
        
        # Start buffer flush thread
        flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        flush_thread.start()
        
        logger.info("Started metrics collection")
    
    def _collection_loop(self, metric_name: str, metric_def: MetricDefinition):
        """Collection loop for a specific metric"""
        while self.running:
            try:
                value = self._collect_metric_value(metric_name, metric_def)
                if value is not None:
                    self.collect_metric(metric_name, value)
                
                time.sleep(metric_def.collection_interval)
                
            except Exception as e:
                logger.error(f"Metric collection error for {metric_name}: {e}")
                time.sleep(metric_def.collection_interval)
    
    def _collect_metric_value(self, metric_name: str, metric_def: MetricDefinition) -> Optional[float]:
        """Collect value for a specific metric"""
        try:
            if metric_name == "system.cpu_usage":
                return psutil.cpu_percent(interval=1)
            
            elif metric_name == "system.memory_usage":
                memory = psutil.virtual_memory()
                return memory.percent
            
            elif metric_name == "system.disk_usage":
                disk = psutil.disk_usage('/')
                return (disk.used / disk.total) * 100
            
            elif metric_name == "app.active_users":
                # Count active users (logged in within last hour)
                cutoff = datetime.utcnow() - timedelta(hours=1)
                count = db.session.query(User).filter(User.last_login >= cutoff).count()
                return float(count)
            
            elif metric_name == "business.tickets_created":
                # Count tickets created in last collection interval
                cutoff = datetime.utcnow() - timedelta(seconds=metric_def.collection_interval)
                count = db.session.query(Ticket).filter(Ticket.created_at >= cutoff).count()
                return float(count)
            
            elif metric_name == "business.tickets_resolved":
                # Count tickets resolved in last collection interval
                cutoff = datetime.utcnow() - timedelta(seconds=metric_def.collection_interval)
                count = db.session.query(Ticket).filter(
                    Ticket.resolved_at >= cutoff,
                    Ticket.resolved_at.isnot(None)
                ).count()
                return float(count)
            
            elif metric_name == "security.failed_logins":
                # This would need to be tracked in authentication system
                # For now, return 0
                return 0.0
            
            else:
                logger.warning(f"No collection method for metric: {metric_name}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to collect metric {metric_name}: {e}")
            return None
    
    def _flush_metrics_buffer(self):
        """Flush metrics buffer to database"""
        if not self.metrics_buffer:
            return
        
        try:
            metrics_to_store = list(self.metrics_buffer)
            self.metrics_buffer.clear()
            
            # Store in database
            for metric_value in metrics_to_store:
                db_metric = PerformanceMetric(
                    metric_name=metric_value.metric_name,
                    metric_value=json.dumps({
                        'value': metric_value.value,
                        'tags': metric_value.tags,
                        'metadata': metric_value.metadata
                    }),
                    timestamp=metric_value.timestamp
                )
                db.session.add(db_metric)
            
            db.session.commit()
            logger.debug(f"Stored {len(metrics_to_store)} metrics in database")
            
        except Exception as e:
            logger.error(f"Failed to flush metrics buffer: {e}")
            db.session.rollback()
    
    def _flush_loop(self):
        """Periodic buffer flush loop"""
        while self.running:
            try:
                self._flush_metrics_buffer()
                time.sleep(30)  # Flush every 30 seconds
            except Exception as e:
                logger.error(f"Flush loop error: {e}")
                time.sleep(30)
    
    def get_metric_history(self, metric_name: str, start_time: datetime, end_time: datetime, 
                          aggregation: str = 'avg', interval: str = '1h') -> List[Dict[str, Any]]:
        """Get historical metric data with aggregation"""
        try:
            # Convert interval to seconds
            interval_seconds = {
                '1m': 60, '5m': 300, '15m': 900, '30m': 1800,
                '1h': 3600, '6h': 21600, '12h': 43200, '1d': 86400
            }.get(interval, 3600)
            
            # Query database
            query = """
            SELECT 
                DATE_TRUNC('hour', timestamp) as time_bucket,
                AVG(CAST(JSON_EXTRACT(metric_value, '$.value') AS FLOAT)) as avg_value,
                MIN(CAST(JSON_EXTRACT(metric_value, '$.value') AS FLOAT)) as min_value,
                MAX(CAST(JSON_EXTRACT(metric_value, '$.value') AS FLOAT)) as max_value,
                COUNT(*) as count
            FROM performance_metrics
            WHERE metric_name = :metric_name
            AND timestamp >= :start_time
            AND timestamp <= :end_time
            GROUP BY DATE_TRUNC('hour', timestamp)
            ORDER BY time_bucket
            """
            
            result = db.session.execute(text(query), {
                'metric_name': metric_name,
                'start_time': start_time,
                'end_time': end_time
            })
            
            history = []
            for row in result:
                history.append({
                    'timestamp': row.time_bucket.isoformat(),
                    'value': getattr(row, f'{aggregation}_value', row.avg_value),
                    'avg': row.avg_value,
                    'min': row.min_value,
                    'max': row.max_value,
                    'count': row.count
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get metric history: {e}")
            return []
    
    def stop(self):
        """Stop metrics collection"""
        self.running = False
        
        # Flush remaining metrics
        self._flush_metrics_buffer()
        
        logger.info("Stopped metrics collection")

class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self, config_manager: ConfigurationManager, metrics_collector: MetricsCollector):
        self.config_manager = config_manager
        self.metrics_collector = metrics_collector
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.notification_channels = {}
        self.running = False
        
        # Initialize notification channels
        self._init_notification_channels()
        
        # Start alert monitoring
        self.start_monitoring()
    
    def _init_notification_channels(self):
        """Initialize notification channels"""
        # Email notifications
        email_config = self.config_manager.get_config('monitoring', 'alerts.email')
        if email_config and email_config.get('enabled'):
            self.notification_channels['email'] = self._send_email_notification
        
        # Webhook notifications
        webhook_config = self.config_manager.get_config('monitoring', 'alerts.webhook')
        if webhook_config and webhook_config.get('enabled'):
            self.notification_channels['webhook'] = self._send_webhook_notification
    
    def start_monitoring(self):
        """Start alert monitoring"""
        self.running = True
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()
        
        logger.info("Started alert monitoring")
    
    def _monitoring_loop(self):
        """Main alert monitoring loop"""
        while self.running:
            try:
                self._check_metric_thresholds()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Alert monitoring error: {e}")
                time.sleep(60)
    
    def _check_metric_thresholds(self):
        """Check metric thresholds and trigger alerts"""
        for metric_name, metric_def in self.metrics_collector.metrics_definitions.items():
            if not metric_def.thresholds:
                continue
            
            try:
                # Get latest metric value
                if self.metrics_collector.redis_client:
                    key = f"metric:{metric_name}:latest"
                    data = self.metrics_collector.redis_client.get(key)
                    if data:
                        metric_data = json.loads(data)
                        current_value = metric_data['value']
                        
                        # Check thresholds
                        for threshold_name, threshold_value in metric_def.thresholds.items():
                            alert_id = f"{metric_name}:{threshold_name}"
                            
                            if current_value >= threshold_value:
                                if alert_id not in self.active_alerts:
                                    # Trigger new alert
                                    alert = Alert(
                                        alert_id=alert_id,
                                        metric_name=metric_name,
                                        severity=AlertSeverity(threshold_name.lower()),
                                        condition=f">= {threshold_value}",
                                        threshold=threshold_value,
                                        current_value=current_value,
                                        message=f"{metric_def.description} is {current_value} {metric_def.unit}, exceeding {threshold_name} threshold of {threshold_value} {metric_def.unit}",
                                        triggered_at=datetime.utcnow()
                                    )
                                    
                                    self._trigger_alert(alert)
                            else:
                                if alert_id in self.active_alerts:
                                    # Resolve alert
                                    self._resolve_alert(alert_id)
                
            except Exception as e:
                logger.error(f"Failed to check thresholds for {metric_name}: {e}")
    
    def _trigger_alert(self, alert: Alert):
        """Trigger a new alert"""
        self.active_alerts[alert.alert_id] = alert
        self.alert_history.append(alert)
        
        logger.warning(f"Alert triggered: {alert.alert_id} - {alert.message}")
        
        # Send notifications
        self._send_notifications(alert)
        
        # Emit real-time event
        if sync_service:
            event = IntegrationEvent(
                event_type=EventType.SYSTEM_ALERT,
                entity_id=alert.alert_id,
                entity_type="alert",
                data=asdict(alert),
                timestamp=datetime.utcnow()
            )
            sync_service.emit_event(event)
    
    def _resolve_alert(self, alert_id: str):
        """Resolve an active alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved_at = datetime.utcnow()
            
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert resolved: {alert_id}")
            
            # Emit real-time event
            if sync_service:
                event = IntegrationEvent(
                    event_type=EventType.SYSTEM_ALERT,
                    entity_id=alert_id,
                    entity_type="alert_resolved",
                    data=asdict(alert),
                    timestamp=datetime.utcnow()
                )
                sync_service.emit_event(event)
    
    def _send_notifications(self, alert: Alert):
        """Send alert notifications"""
        for channel_name, send_func in self.notification_channels.items():
            try:
                send_func(alert)
            except Exception as e:
                logger.error(f"Failed to send {channel_name} notification: {e}")
    
    def _send_email_notification(self, alert: Alert):
        """Send email notification"""
        email_config = self.config_manager.get_config('monitoring', 'alerts.email')
        if not email_config:
            return
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = email_config['from']
        msg['To'] = ', '.join(email_config['to'])
        msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.metric_name} Alert"
        
        body = f"""
        Alert Details:
        
        Metric: {alert.metric_name}
        Severity: {alert.severity.value.upper()}
        Current Value: {alert.current_value}
        Threshold: {alert.condition} {alert.threshold}
        Triggered At: {alert.triggered_at}
        
        Message: {alert.message}
        
        Please investigate and take appropriate action.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(email_config['smtp_host'], email_config['smtp_port'])
        if email_config.get('use_tls'):
            server.starttls()
        if email_config.get('username'):
            server.login(email_config['username'], email_config['password'])
        
        server.send_message(msg)
        server.quit()
    
    def _send_webhook_notification(self, alert: Alert):
        """Send webhook notification"""
        webhook_config = self.config_manager.get_config('monitoring', 'alerts.webhook')
        if not webhook_config:
            return
        
        payload = {
            'alert_id': alert.alert_id,
            'metric_name': alert.metric_name,
            'severity': alert.severity.value,
            'current_value': alert.current_value,
            'threshold': alert.threshold,
            'condition': alert.condition,
            'message': alert.message,
            'triggered_at': alert.triggered_at.isoformat(),
            'tags': alert.tags,
            'metadata': alert.metadata
        }
        
        response = requests.post(
            webhook_config['url'],
            json=payload,
            headers=webhook_config.get('headers', {}),
            timeout=30
        )
        
        response.raise_for_status()
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        return list(self.alert_history)[-limit:]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = acknowledged_by
            
            logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
    
    def stop(self):
        """Stop alert monitoring"""
        self.running = False
        logger.info("Stopped alert monitoring")

class HealthCheckManager:
    """Manages system health checks"""
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config_manager = config_manager
        self.health_checks = {}
        self.health_status = {}
        self.running = False
        
        # Initialize default health checks
        self._init_default_health_checks()
        
        # Start health monitoring
        self.start_monitoring()
    
    def _init_default_health_checks(self):
        """Initialize default health checks"""
        default_checks = [
            HealthCheck(
                name="database",
                description="Database connectivity",
                check_function=self._check_database,
                interval=300,  # 5 minutes
                timeout=30
            ),
            HealthCheck(
                name="redis",
                description="Redis connectivity",
                check_function=self._check_redis,
                interval=300,
                timeout=30
            ),
            HealthCheck(
                name="ai_agent_backend",
                description="AI Agent backend connectivity",
                check_function=self._check_ai_agent_backend,
                interval=300,
                timeout=30
            ),
            HealthCheck(
                name="disk_space",
                description="Disk space availability",
                check_function=self._check_disk_space,
                interval=600,  # 10 minutes
                timeout=10
            )
        ]
        
        for check in default_checks:
            self.register_health_check(check)
    
    def register_health_check(self, health_check: HealthCheck):
        """Register a health check"""
        self.health_checks[health_check.name] = health_check
        self.health_status[health_check.name] = MonitoringStatus.UNKNOWN
        logger.info(f"Registered health check: {health_check.name}")
    
    def start_monitoring(self):
        """Start health monitoring"""
        self.running = True
        
        # Start monitoring thread for each health check
        for check_name, health_check in self.health_checks.items():
            if health_check.enabled:
                thread = threading.Thread(
                    target=self._health_check_loop,
                    args=(check_name, health_check),
                    daemon=True
                )
                thread.start()
        
        logger.info("Started health monitoring")
    
    def _health_check_loop(self, check_name: str, health_check: HealthCheck):
        """Health check monitoring loop"""
        while self.running:
            try:
                start_time = time.time()
                
                # Run health check with timeout
                result = self._run_health_check_with_timeout(health_check)
                
                check_duration = time.time() - start_time
                health_check.last_check = datetime.utcnow()
                
                if result:
                    health_check.last_status = MonitoringStatus.HEALTHY
                    health_check.consecutive_failures = 0
                    self.health_status[check_name] = MonitoringStatus.HEALTHY
                else:
                    health_check.consecutive_failures += 1
                    
                    if health_check.consecutive_failures >= health_check.max_failures:
                        health_check.last_status = MonitoringStatus.CRITICAL
                        self.health_status[check_name] = MonitoringStatus.CRITICAL
                    else:
                        health_check.last_status = MonitoringStatus.WARNING
                        self.health_status[check_name] = MonitoringStatus.WARNING
                
                logger.debug(f"Health check {check_name}: {health_check.last_status.value} (duration: {check_duration:.2f}s)")
                
                time.sleep(health_check.interval)
                
            except Exception as e:
                logger.error(f"Health check error for {check_name}: {e}")
                health_check.consecutive_failures += 1
                health_check.last_status = MonitoringStatus.CRITICAL
                self.health_status[check_name] = MonitoringStatus.CRITICAL
                time.sleep(health_check.interval)
    
    def _run_health_check_with_timeout(self, health_check: HealthCheck) -> bool:
        """Run health check with timeout"""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(health_check.check_function)
            try:
                return future.result(timeout=health_check.timeout)
            except Exception as e:
                logger.error(f"Health check timeout or error: {e}")
                return False
    
    def _check_database(self) -> bool:
        """Check database connectivity"""
        try:
            db.session.execute(text('SELECT 1'))
            return True
        except Exception:
            return False
    
    def _check_redis(self) -> bool:
        """Check Redis connectivity"""
        try:
            # This would need Redis client from metrics collector
            # For now, assume healthy
            return True
        except Exception:
            return False
    
    def _check_ai_agent_backend(self) -> bool:
        """Check AI Agent backend connectivity"""
        try:
            ai_agent_url = self.config_manager.get_config('integration', 'ai_agent_url')
            if not ai_agent_url:
                return False
            
            response = requests.get(f"{ai_agent_url}/health", timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    def _check_disk_space(self) -> bool:
        """Check disk space availability"""
        try:
            disk = psutil.disk_usage('/')
            usage_percent = (disk.used / disk.total) * 100
            return usage_percent < 90  # Fail if > 90% used
        except Exception:
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        overall_status = MonitoringStatus.HEALTHY
        
        # Determine overall status
        for status in self.health_status.values():
            if status == MonitoringStatus.CRITICAL:
                overall_status = MonitoringStatus.CRITICAL
                break
            elif status == MonitoringStatus.WARNING and overall_status == MonitoringStatus.HEALTHY:
                overall_status = MonitoringStatus.WARNING
        
        return {
            'overall_status': overall_status.value,
            'checks': {
                name: {
                    'status': status.value,
                    'last_check': check.last_check.isoformat() if check.last_check else None,
                    'consecutive_failures': check.consecutive_failures,
                    'description': check.description
                }
                for name, (status, check) in zip(self.health_status.keys(), 
                                               zip(self.health_status.values(), self.health_checks.values()))
            }
        }
    
    def stop(self):
        """Stop health monitoring"""
        self.running = False
        logger.info("Stopped health monitoring")

class MonitoringSystem:
    """Main monitoring system that coordinates all components"""
    
    def __init__(self, config_dir: str = "config", redis_url: str = None):
        self.config_dir = config_dir
        self.redis_url = redis_url
        
        # Initialize components
        self.config_manager = ConfigurationManager(config_dir)
        
        # Register configuration files
        self.config_manager.register_config_file('monitoring', 'monitoring.yaml')
        self.config_manager.register_config_file('dashboard', 'dashboard.yaml')
        self.config_manager.register_config_file('integration', 'integration.yaml')
        
        # Initialize Redis client
        self.redis_client = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
        
        # Initialize monitoring components
        self.metrics_collector = MetricsCollector(self.config_manager, self.redis_client)
        self.alert_manager = AlertManager(self.config_manager, self.metrics_collector)
        self.health_check_manager = HealthCheckManager(self.config_manager)
        
        logger.info("Monitoring system initialized")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        return {
            'health': self.health_check_manager.get_health_status(),
            'alerts': {
                'active': [asdict(alert) for alert in self.alert_manager.get_active_alerts()],
                'recent': [asdict(alert) for alert in self.alert_manager.get_alert_history(10)]
            },
            'metrics': self._get_dashboard_metrics(),
            'system_info': self._get_system_info(),
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def _get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get key metrics for dashboard"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        key_metrics = [
            'system.cpu_usage',
            'system.memory_usage',
            'app.active_users',
            'business.tickets_created',
            'business.tickets_resolved'
        ]
        
        metrics_data = {}
        for metric_name in key_metrics:
            if metric_name in self.metrics_collector.metrics_definitions:
                # Get latest value
                if self.redis_client:
                    key = f"metric:{metric_name}:latest"
                    data = self.redis_client.get(key)
                    if data:
                        metric_data = json.loads(data)
                        metrics_data[metric_name] = {
                            'current': metric_data['value'],
                            'timestamp': metric_data['timestamp'],
                            'history': self.metrics_collector.get_metric_history(
                                metric_name, start_time, end_time, 'avg', '1h'
                            )
                        }
        
        return metrics_data
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        return {
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'disk_total': psutil.disk_usage('/').total,
            'uptime': time.time() - psutil.boot_time(),
            'python_version': os.sys.version,
            'platform': os.name
        }
    
    def stop(self):
        """Stop the monitoring system"""
        self.config_manager.stop()
        self.metrics_collector.stop()
        self.alert_manager.stop()
        self.health_check_manager.stop()
        
        logger.info("Monitoring system stopped")

# Global monitoring system instance
monitoring_system = None

def init_monitoring_system(config_dir: str = "config", redis_url: str = None):
    """Initialize the global monitoring system"""
    global monitoring_system
    monitoring_system = MonitoringSystem(config_dir, redis_url)
    return monitoring_system

def get_monitoring_health() -> Dict[str, Any]:
    """Get monitoring system health"""
    if not monitoring_system:
        return {'status': 'unhealthy', 'reason': 'Monitoring system not initialized'}
    
    return monitoring_system.get_dashboard_data()