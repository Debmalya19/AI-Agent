"""
Tool execution status monitoring system for comprehensive tracking and user feedback.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from .models import LoadingState, ErrorSeverity
from .loading_indicators import LoadingIndicatorManager, ToolType


class ExecutionStatus(Enum):
    """Execution status for tools."""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class NotificationType(Enum):
    """Types of notifications."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"


@dataclass
class ExecutionMetrics:
    """Metrics for tool execution."""
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None
    network_requests: int = 0
    database_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass
class StatusUpdate:
    """Status update for tool execution."""
    tool_name: str
    status: ExecutionStatus
    progress: float
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: Optional[ExecutionMetrics] = None


@dataclass
class Notification:
    """Notification for user feedback."""
    notification_id: str
    notification_type: NotificationType
    title: str
    message: str
    tool_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    auto_dismiss: bool = True
    dismiss_after: float = 5.0
    actions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryOption:
    """Recovery option for failed executions."""
    option_id: str
    title: str
    description: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    estimated_time: Optional[float] = None
    success_probability: float = 0.5


@dataclass
class ErrorVisualization:
    """Error visualization information."""
    error_type: str
    error_message: str
    severity: ErrorSeverity
    context: Dict[str, Any]
    recovery_options: List[RecoveryOption] = field(default_factory=list)
    troubleshooting_steps: List[str] = field(default_factory=list)
    related_tools: List[str] = field(default_factory=list)


class ToolExecutionMonitor:
    """Monitors tool execution with comprehensive status tracking."""
    
    def __init__(self, loading_manager: LoadingIndicatorManager):
        self.loading_manager = loading_manager
        self._execution_status: Dict[str, ExecutionStatus] = {}
        self._execution_metrics: Dict[str, ExecutionMetrics] = {}
        self._status_history: Dict[str, List[StatusUpdate]] = {}
        self._notifications: Dict[str, Notification] = {}
        self._error_visualizations: Dict[str, ErrorVisualization] = {}
        self._status_callbacks: List[Callable[[StatusUpdate], None]] = []
        self._notification_callbacks: List[Callable[[Notification], None]] = []
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._completion_callbacks: Dict[str, List[Callable]] = {}
        
        # Configuration
        self.default_timeout = 300.0  # 5 minutes
        self.progress_update_interval = 1.0  # 1 second
        self.metrics_collection_enabled = True
        self.auto_cleanup_delay = 30.0  # 30 seconds
    
    def start_monitoring(self, tool_name: str, tool_type: Optional[ToolType] = None,
                        timeout: Optional[float] = None, 
                        custom_message: Optional[str] = None) -> str:
        """Start monitoring a tool execution."""
        # Start loading indicator
        self.loading_manager.start_loading(tool_name, tool_type, custom_message)
        
        # Initialize execution tracking
        self._execution_status[tool_name] = ExecutionStatus.PENDING
        self._execution_metrics[tool_name] = ExecutionMetrics(start_time=datetime.now())
        self._status_history[tool_name] = []
        
        # Create initial status update
        status_update = StatusUpdate(
            tool_name=tool_name,
            status=ExecutionStatus.PENDING,
            progress=0.0,
            message=custom_message or f"Starting {tool_name}...",
            metrics=self._execution_metrics[tool_name]
        )
        self._add_status_update(tool_name, status_update)
        
        # Start monitoring task
        monitor_timeout = timeout or self.default_timeout
        try:
            loop = asyncio.get_running_loop()
            self._monitoring_tasks[tool_name] = loop.create_task(
                self._monitor_execution(tool_name, monitor_timeout)
            )
        except RuntimeError:
            # No event loop running
            pass
        
        # Create notification
        notification = Notification(
            notification_id=f"{tool_name}_started",
            notification_type=NotificationType.INFO,
            title="Tool Started",
            message=f"{tool_name} execution started",
            tool_name=tool_name,
            auto_dismiss=True,
            dismiss_after=3.0
        )
        self._add_notification(notification)
        
        return tool_name
    
    async def _monitor_execution(self, tool_name: str, timeout: float):
        """Monitor tool execution with timeout and progress tracking."""
        start_time = time.time()
        
        try:
            while tool_name in self._execution_status:
                current_time = time.time()
                elapsed = current_time - start_time
                
                # Check timeout
                if elapsed > timeout:
                    await self._handle_timeout(tool_name)
                    break
                
                # Update progress based on elapsed time (if no manual updates)
                status = self._execution_status.get(tool_name)
                if status in [ExecutionStatus.RUNNING, ExecutionStatus.STARTING]:
                    # Estimate progress based on time (rough approximation)
                    estimated_progress = min(elapsed / timeout, 0.9)  # Cap at 90%
                    await self.update_progress(tool_name, estimated_progress)
                
                # Check if completed
                if status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, 
                             ExecutionStatus.CANCELLED]:
                    break
                
                await asyncio.sleep(self.progress_update_interval)
                
        except asyncio.CancelledError:
            await self._handle_cancellation(tool_name)
        except Exception as e:
            await self._handle_monitoring_error(tool_name, e)
    
    async def update_status(self, tool_name: str, status: ExecutionStatus, 
                           message: Optional[str] = None, 
                           metadata: Optional[Dict[str, Any]] = None):
        """Update tool execution status."""
        if tool_name not in self._execution_status:
            return False
        
        old_status = self._execution_status[tool_name]
        self._execution_status[tool_name] = status
        
        # Update metrics
        metrics = self._execution_metrics.get(tool_name)
        if metrics and status == ExecutionStatus.COMPLETED:
            metrics.end_time = datetime.now()
            metrics.duration = (metrics.end_time - metrics.start_time).total_seconds()
        
        # Create status update
        current_progress = 0.0
        if tool_name in self.loading_manager._active_indicators:
            current_progress = self.loading_manager._active_indicators[tool_name].progress
        
        status_update = StatusUpdate(
            tool_name=tool_name,
            status=status,
            progress=current_progress,
            message=message or self._get_default_status_message(status, tool_name),
            metadata=metadata or {},
            metrics=metrics
        )
        self._add_status_update(tool_name, status_update)
        
        # Update loading indicator
        if status == ExecutionStatus.RUNNING:
            await self.loading_manager.update_progress(tool_name, current_progress, status_update.message)
        elif status == ExecutionStatus.COMPLETED:
            self.loading_manager.complete_loading(tool_name, True, status_update.message)
        elif status in [ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT, ExecutionStatus.CANCELLED]:
            self.loading_manager.complete_loading(tool_name, False, status_update.message)
        
        # Create notifications for important status changes
        await self._create_status_notification(tool_name, old_status, status, status_update.message)
        
        # Trigger completion callbacks
        if status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            await self._trigger_completion_callbacks(tool_name, status)
        
        return True
    
    async def update_progress(self, tool_name: str, progress: float, 
                            message: Optional[str] = None):
        """Update tool execution progress."""
        if tool_name not in self._execution_status:
            return False
        
        # Update loading indicator
        success = await self.loading_manager.update_progress(tool_name, progress, message)
        
        if success:
            # Create progress status update
            status_update = StatusUpdate(
                tool_name=tool_name,
                status=self._execution_status[tool_name],
                progress=progress,
                message=message or f"{tool_name} progress: {progress:.1%}",
                metrics=self._execution_metrics.get(tool_name)
            )
            self._add_status_update(tool_name, status_update)
        
        return success
    
    def complete_execution(self, tool_name: str, success: bool, 
                          result_message: Optional[str] = None,
                          result_data: Optional[Any] = None):
        """Complete tool execution."""
        if tool_name not in self._execution_status:
            return False
        
        status = ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED
        message = result_message or ("Execution completed successfully" if success else "Execution failed")
        
        # Update status synchronously
        self._execution_status[tool_name] = status
        
        # Update metrics
        metrics = self._execution_metrics.get(tool_name)
        if metrics:
            metrics.end_time = datetime.now()
            metrics.duration = (metrics.end_time - metrics.start_time).total_seconds()
        
        # Complete loading indicator
        self.loading_manager.complete_loading(tool_name, success, message)
        
        # Create final status update
        status_update = StatusUpdate(
            tool_name=tool_name,
            status=status,
            progress=1.0,
            message=message,
            metadata={"result_data": result_data} if result_data else {},
            metrics=metrics
        )
        self._add_status_update(tool_name, status_update)
        
        # Create completion notification
        notification_type = NotificationType.SUCCESS if success else NotificationType.ERROR
        notification = Notification(
            notification_id=f"{tool_name}_completed",
            notification_type=notification_type,
            title="Tool Completed" if success else "Tool Failed",
            message=message,
            tool_name=tool_name,
            auto_dismiss=success,  # Only auto-dismiss success notifications
            dismiss_after=5.0 if success else 0.0
        )
        self._add_notification(notification)
        
        # Schedule cleanup
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._cleanup_after_delay(tool_name))
        except RuntimeError:
            pass
        
        return True
    
    def create_error_visualization(self, tool_name: str, error: Exception,
                                 context: Optional[Dict[str, Any]] = None) -> ErrorVisualization:
        """Create error visualization with recovery options."""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Determine severity
        severity = self._determine_error_severity(error)
        
        # Generate recovery options
        recovery_options = self._generate_recovery_options(tool_name, error)
        
        # Generate troubleshooting steps
        troubleshooting_steps = self._generate_troubleshooting_steps(error_type)
        
        # Find related tools
        related_tools = self._find_related_tools(tool_name)
        
        error_viz = ErrorVisualization(
            error_type=error_type,
            error_message=error_message,
            severity=severity,
            context=context or {},
            recovery_options=recovery_options,
            troubleshooting_steps=troubleshooting_steps,
            related_tools=related_tools
        )
        
        self._error_visualizations[tool_name] = error_viz
        
        # Create error notification
        notification = Notification(
            notification_id=f"{tool_name}_error",
            notification_type=NotificationType.ERROR,
            title=f"Error in {tool_name}",
            message=error_message,
            tool_name=tool_name,
            auto_dismiss=False,
            actions=[opt.option_id for opt in recovery_options[:3]]  # Show top 3 options
        )
        self._add_notification(notification)
        
        return error_viz
    
    def get_execution_status(self, tool_name: str) -> Optional[ExecutionStatus]:
        """Get current execution status for a tool."""
        return self._execution_status.get(tool_name)
    
    def get_execution_metrics(self, tool_name: str) -> Optional[ExecutionMetrics]:
        """Get execution metrics for a tool."""
        return self._execution_metrics.get(tool_name)
    
    def get_status_history(self, tool_name: str) -> List[StatusUpdate]:
        """Get status history for a tool."""
        return self._status_history.get(tool_name, [])
    
    def get_active_notifications(self) -> List[Notification]:
        """Get all active notifications."""
        return list(self._notifications.values())
    
    def get_error_visualization(self, tool_name: str) -> Optional[ErrorVisualization]:
        """Get error visualization for a tool."""
        return self._error_visualizations.get(tool_name)
    
    def dismiss_notification(self, notification_id: str) -> bool:
        """Dismiss a notification."""
        if notification_id in self._notifications:
            del self._notifications[notification_id]
            return True
        return False
    
    def add_status_callback(self, callback: Callable[[StatusUpdate], None]):
        """Add callback for status updates."""
        self._status_callbacks.append(callback)
    
    def add_notification_callback(self, callback: Callable[[Notification], None]):
        """Add callback for notifications."""
        self._notification_callbacks.append(callback)
    
    def add_completion_callback(self, tool_name: str, callback: Callable):
        """Add callback for tool completion."""
        if tool_name not in self._completion_callbacks:
            self._completion_callbacks[tool_name] = []
        self._completion_callbacks[tool_name].append(callback)
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get summary of all monitoring activities."""
        active_tools = len(self._execution_status)
        running_tools = len([s for s in self._execution_status.values() 
                           if s in [ExecutionStatus.RUNNING, ExecutionStatus.STARTING]])
        completed_tools = len([s for s in self._execution_status.values() 
                             if s == ExecutionStatus.COMPLETED])
        failed_tools = len([s for s in self._execution_status.values() 
                          if s == ExecutionStatus.FAILED])
        
        return {
            "active_tools": active_tools,
            "running_tools": running_tools,
            "completed_tools": completed_tools,
            "failed_tools": failed_tools,
            "active_notifications": len(self._notifications),
            "error_visualizations": len(self._error_visualizations),
            "tools": list(self._execution_status.keys())
        }
    
    # Private helper methods
    
    def _add_status_update(self, tool_name: str, status_update: StatusUpdate):
        """Add status update to history and notify callbacks."""
        if tool_name not in self._status_history:
            self._status_history[tool_name] = []
        
        self._status_history[tool_name].append(status_update)
        
        # Limit history size
        if len(self._status_history[tool_name]) > 100:
            self._status_history[tool_name] = self._status_history[tool_name][-50:]
        
        # Notify callbacks
        for callback in self._status_callbacks:
            try:
                callback(status_update)
            except Exception as e:
                print(f"Error in status callback: {e}")
    
    def _add_notification(self, notification: Notification):
        """Add notification and notify callbacks."""
        self._notifications[notification.notification_id] = notification
        
        # Auto-dismiss if configured
        if notification.auto_dismiss and notification.dismiss_after > 0:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._auto_dismiss_notification(notification.notification_id, 
                                                               notification.dismiss_after))
            except RuntimeError:
                pass
        
        # Notify callbacks
        for callback in self._notification_callbacks:
            try:
                callback(notification)
            except Exception as e:
                print(f"Error in notification callback: {e}")
    
    async def _auto_dismiss_notification(self, notification_id: str, delay: float):
        """Auto-dismiss notification after delay."""
        await asyncio.sleep(delay)
        self.dismiss_notification(notification_id)
    
    def _get_default_status_message(self, status: ExecutionStatus, tool_name: str) -> str:
        """Get default message for status."""
        messages = {
            ExecutionStatus.PENDING: f"{tool_name} is pending execution",
            ExecutionStatus.STARTING: f"{tool_name} is starting up",
            ExecutionStatus.RUNNING: f"{tool_name} is running",
            ExecutionStatus.COMPLETING: f"{tool_name} is completing",
            ExecutionStatus.COMPLETED: f"{tool_name} completed successfully",
            ExecutionStatus.FAILED: f"{tool_name} execution failed",
            ExecutionStatus.CANCELLED: f"{tool_name} execution was cancelled",
            ExecutionStatus.TIMEOUT: f"{tool_name} execution timed out"
        }
        return messages.get(status, f"{tool_name} status: {status.value}")
    
    async def _create_status_notification(self, tool_name: str, old_status: ExecutionStatus,
                                        new_status: ExecutionStatus, message: str):
        """Create notification for important status changes."""
        important_transitions = [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT,
            ExecutionStatus.CANCELLED
        ]
        
        if new_status in important_transitions:
            notification_type = NotificationType.SUCCESS if new_status == ExecutionStatus.COMPLETED else NotificationType.ERROR
            
            notification = Notification(
                notification_id=f"{tool_name}_{new_status.value}",
                notification_type=notification_type,
                title=f"Tool {new_status.value.title()}",
                message=message,
                tool_name=tool_name,
                auto_dismiss=new_status == ExecutionStatus.COMPLETED,
                dismiss_after=5.0 if new_status == ExecutionStatus.COMPLETED else 0.0
            )
            self._add_notification(notification)
    
    async def _trigger_completion_callbacks(self, tool_name: str, status: ExecutionStatus):
        """Trigger completion callbacks for a tool."""
        callbacks = self._completion_callbacks.get(tool_name, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(tool_name, status)
                else:
                    callback(tool_name, status)
            except Exception as e:
                print(f"Error in completion callback for {tool_name}: {e}")
    
    async def _handle_timeout(self, tool_name: str):
        """Handle tool execution timeout."""
        await self.update_status(tool_name, ExecutionStatus.TIMEOUT, 
                               f"{tool_name} execution timed out")
    
    async def _handle_cancellation(self, tool_name: str):
        """Handle tool execution cancellation."""
        await self.update_status(tool_name, ExecutionStatus.CANCELLED,
                               f"{tool_name} execution was cancelled")
    
    async def _handle_monitoring_error(self, tool_name: str, error: Exception):
        """Handle monitoring error."""
        await self.update_status(tool_name, ExecutionStatus.FAILED,
                               f"Monitoring error for {tool_name}: {error}")
    
    async def _cleanup_after_delay(self, tool_name: str):
        """Clean up monitoring data after delay."""
        await asyncio.sleep(self.auto_cleanup_delay)
        
        # Clean up data structures
        self._execution_status.pop(tool_name, None)
        self._execution_metrics.pop(tool_name, None)
        self._status_history.pop(tool_name, None)
        self._error_visualizations.pop(tool_name, None)
        self._completion_callbacks.pop(tool_name, None)
        
        # Cancel monitoring task
        if tool_name in self._monitoring_tasks:
            self._monitoring_tasks[tool_name].cancel()
            del self._monitoring_tasks[tool_name]
    
    def _determine_error_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity based on exception type."""
        critical_errors = [ConnectionError, TimeoutError, MemoryError]
        warning_errors = [ValueError, KeyError, AttributeError]
        
        error_type = type(error)
        if any(isinstance(error, err_type) for err_type in critical_errors):
            return ErrorSeverity.CRITICAL
        elif any(isinstance(error, err_type) for err_type in warning_errors):
            return ErrorSeverity.WARNING
        else:
            return ErrorSeverity.ERROR
    
    def _generate_recovery_options(self, tool_name: str, error: Exception) -> List[RecoveryOption]:
        """Generate recovery options based on error type."""
        options = []
        
        # Common recovery options
        options.append(RecoveryOption(
            option_id="retry",
            title="Retry Execution",
            description="Retry the tool execution with the same parameters",
            action="retry",
            estimated_time=30.0,
            success_probability=0.7
        ))
        
        options.append(RecoveryOption(
            option_id="retry_with_fallback",
            title="Retry with Fallback",
            description="Retry with alternative parameters or fallback method",
            action="retry_fallback",
            estimated_time=45.0,
            success_probability=0.8
        ))
        
        # Error-specific options
        if isinstance(error, ConnectionError):
            options.append(RecoveryOption(
                option_id="check_connection",
                title="Check Connection",
                description="Verify network connectivity and retry",
                action="check_connection",
                estimated_time=15.0,
                success_probability=0.6
            ))
        
        if isinstance(error, TimeoutError):
            options.append(RecoveryOption(
                option_id="increase_timeout",
                title="Increase Timeout",
                description="Retry with increased timeout duration",
                action="increase_timeout",
                parameters={"timeout_multiplier": 2.0},
                estimated_time=60.0,
                success_probability=0.8
            ))
        
        return options
    
    def _generate_troubleshooting_steps(self, error_type: str) -> List[str]:
        """Generate troubleshooting steps based on error type."""
        common_steps = [
            "Check system resources (CPU, memory, disk space)",
            "Verify network connectivity",
            "Review tool configuration and parameters",
            "Check for recent system or software updates"
        ]
        
        specific_steps = {
            "ConnectionError": [
                "Verify the target service is running",
                "Check firewall and proxy settings",
                "Test connectivity with ping or telnet"
            ],
            "TimeoutError": [
                "Increase timeout duration",
                "Check for network latency issues",
                "Verify the target service response time"
            ],
            "ValueError": [
                "Validate input parameters",
                "Check data format and encoding",
                "Review parameter constraints"
            ]
        }
        
        steps = common_steps.copy()
        steps.extend(specific_steps.get(error_type, []))
        return steps
    
    def _find_related_tools(self, tool_name: str) -> List[str]:
        """Find tools related to the current tool."""
        # This is a simplified implementation
        # In practice, this could use tool metadata, categories, or dependencies
        all_tools = list(self._execution_status.keys())
        return [tool for tool in all_tools if tool != tool_name][:3]  # Return up to 3 related tools