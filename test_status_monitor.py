"""
Tests for tool execution status monitoring system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from intelligent_chat.status_monitor import (
    ToolExecutionMonitor, ExecutionStatus, NotificationType, 
    ExecutionMetrics, StatusUpdate, Notification, RecoveryOption, ErrorVisualization
)
from intelligent_chat.loading_indicators import LoadingIndicatorManager, ToolType
from intelligent_chat.models import ErrorSeverity


class TestToolExecutionMonitor:
    """Test cases for ToolExecutionMonitor."""
    
    @pytest.fixture
    def loading_manager(self):
        """Create a LoadingIndicatorManager instance."""
        return LoadingIndicatorManager()
    
    @pytest.fixture
    def monitor(self, loading_manager):
        """Create a ToolExecutionMonitor instance."""
        return ToolExecutionMonitor(loading_manager)
    
    def test_initialization(self, monitor):
        """Test monitor initialization."""
        assert isinstance(monitor.loading_manager, LoadingIndicatorManager)
        assert len(monitor._execution_status) == 0
        assert len(monitor._execution_metrics) == 0
        assert len(monitor._status_history) == 0
        assert len(monitor._notifications) == 0
        assert monitor.default_timeout == 300.0
        assert monitor.progress_update_interval == 1.0
    
    def test_start_monitoring_basic(self, monitor):
        """Test starting basic monitoring."""
        tool_name = monitor.start_monitoring("test_tool", ToolType.DATABASE_QUERY)
        
        assert tool_name == "test_tool"
        assert monitor._execution_status["test_tool"] == ExecutionStatus.PENDING
        assert "test_tool" in monitor._execution_metrics
        assert "test_tool" in monitor._status_history
        assert len(monitor._status_history["test_tool"]) == 1
        
        # Check that loading indicator was started
        assert monitor.loading_manager.is_loading("test_tool")
    
    def test_start_monitoring_custom_message(self, monitor):
        """Test starting monitoring with custom message."""
        custom_msg = "Custom initialization message"
        monitor.start_monitoring("test_tool", ToolType.API_CALL, custom_message=custom_msg)
        
        status_history = monitor.get_status_history("test_tool")
        assert len(status_history) == 1
        assert status_history[0].message == custom_msg
    
    @pytest.mark.asyncio
    async def test_update_status(self, monitor):
        """Test updating execution status."""
        monitor.start_monitoring("test_tool", ToolType.DATABASE_QUERY)
        
        success = await monitor.update_status("test_tool", ExecutionStatus.RUNNING, "Now running")
        assert success
        
        assert monitor._execution_status["test_tool"] == ExecutionStatus.RUNNING
        status_history = monitor.get_status_history("test_tool")
        assert len(status_history) == 2  # Initial + update
        assert status_history[-1].status == ExecutionStatus.RUNNING
        assert status_history[-1].message == "Now running"
    
    @pytest.mark.asyncio
    async def test_update_status_nonexistent_tool(self, monitor):
        """Test updating status for non-existent tool."""
        success = await monitor.update_status("nonexistent", ExecutionStatus.RUNNING)
        assert not success
    
    @pytest.mark.asyncio
    async def test_update_status_completion(self, monitor):
        """Test updating status to completion."""
        monitor.start_monitoring("test_tool", ToolType.DATABASE_QUERY)
        
        await monitor.update_status("test_tool", ExecutionStatus.COMPLETED, "Task completed")
        
        assert monitor._execution_status["test_tool"] == ExecutionStatus.COMPLETED
        
        # Check metrics were updated
        metrics = monitor.get_execution_metrics("test_tool")
        assert metrics.end_time is not None
        assert metrics.duration is not None
        assert metrics.duration > 0
    
    @pytest.mark.asyncio
    async def test_update_progress(self, monitor):
        """Test updating execution progress."""
        monitor.start_monitoring("test_tool", ToolType.DATABASE_QUERY)
        
        success = await monitor.update_progress("test_tool", 0.5, "Half done")
        assert success
        
        # Check loading indicator was updated
        indicator = monitor.loading_manager.get_indicator("test_tool")
        assert indicator.progress == 0.5
        
        # Check status history
        status_history = monitor.get_status_history("test_tool")
        assert len(status_history) >= 2
        progress_update = next((s for s in status_history if s.progress == 0.5), None)
        assert progress_update is not None
        assert progress_update.message == "Half done"
    
    @pytest.mark.asyncio
    async def test_update_progress_nonexistent_tool(self, monitor):
        """Test updating progress for non-existent tool."""
        success = await monitor.update_progress("nonexistent", 0.5)
        assert not success
    
    def test_complete_execution_success(self, monitor):
        """Test completing execution successfully."""
        monitor.start_monitoring("test_tool", ToolType.DATABASE_QUERY)
        
        success = monitor.complete_execution("test_tool", True, "Success!", {"result": "data"})
        assert success
        
        assert monitor._execution_status["test_tool"] == ExecutionStatus.COMPLETED
        
        # Check final status update
        status_history = monitor.get_status_history("test_tool")
        final_update = status_history[-1]
        assert final_update.status == ExecutionStatus.COMPLETED
        assert final_update.progress == 1.0
        assert final_update.message == "Success!"
        assert final_update.metadata["result_data"] == {"result": "data"}
        
        # Check notification was created
        notifications = monitor.get_active_notifications()
        completion_notification = next((n for n in notifications if "completed" in n.notification_id), None)
        assert completion_notification is not None
        assert completion_notification.notification_type == NotificationType.SUCCESS
    
    def test_complete_execution_failure(self, monitor):
        """Test completing execution with failure."""
        monitor.start_monitoring("test_tool", ToolType.DATABASE_QUERY)
        
        success = monitor.complete_execution("test_tool", False, "Failed!")
        assert success
        
        assert monitor._execution_status["test_tool"] == ExecutionStatus.FAILED
        
        # Check notification
        notifications = monitor.get_active_notifications()
        completion_notification = next((n for n in notifications if "completed" in n.notification_id), None)
        assert completion_notification is not None
        assert completion_notification.notification_type == NotificationType.ERROR
        assert not completion_notification.auto_dismiss  # Error notifications should not auto-dismiss
    
    def test_complete_execution_nonexistent_tool(self, monitor):
        """Test completing execution for non-existent tool."""
        success = monitor.complete_execution("nonexistent", True)
        assert not success
    
    def test_create_error_visualization(self, monitor):
        """Test creating error visualization."""
        monitor.start_monitoring("test_tool", ToolType.DATABASE_QUERY)
        
        error = ConnectionError("Connection failed")
        context = {"host": "example.com", "port": 5432}
        
        error_viz = monitor.create_error_visualization("test_tool", error, context)
        
        assert error_viz.error_type == "ConnectionError"
        assert error_viz.error_message == "Connection failed"
        assert error_viz.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR]
        assert error_viz.context == context
        assert len(error_viz.recovery_options) > 0
        assert len(error_viz.troubleshooting_steps) > 0
        
        # Check that error visualization was stored
        stored_viz = monitor.get_error_visualization("test_tool")
        assert stored_viz == error_viz
        
        # Check that error notification was created
        notifications = monitor.get_active_notifications()
        error_notification = next((n for n in notifications if "error" in n.notification_id), None)
        assert error_notification is not None
        assert error_notification.notification_type == NotificationType.ERROR
        assert not error_notification.auto_dismiss
    
    def test_get_execution_status(self, monitor):
        """Test getting execution status."""
        assert monitor.get_execution_status("nonexistent") is None
        
        monitor.start_monitoring("test_tool", ToolType.DATABASE_QUERY)
        status = monitor.get_execution_status("test_tool")
        assert status == ExecutionStatus.PENDING
    
    def test_get_execution_metrics(self, monitor):
        """Test getting execution metrics."""
        assert monitor.get_execution_metrics("nonexistent") is None
        
        monitor.start_monitoring("test_tool", ToolType.DATABASE_QUERY)
        metrics = monitor.get_execution_metrics("test_tool")
        assert isinstance(metrics, ExecutionMetrics)
        assert metrics.start_time is not None
        assert metrics.end_time is None
    
    def test_get_status_history(self, monitor):
        """Test getting status history."""
        assert monitor.get_status_history("nonexistent") == []
        
        monitor.start_monitoring("test_tool", ToolType.DATABASE_QUERY)
        history = monitor.get_status_history("test_tool")
        assert len(history) == 1
        assert history[0].tool_name == "test_tool"
        assert history[0].status == ExecutionStatus.PENDING
    
    def test_dismiss_notification(self, monitor):
        """Test dismissing notifications."""
        monitor.start_monitoring("test_tool", ToolType.DATABASE_QUERY)
        
        notifications = monitor.get_active_notifications()
        assert len(notifications) > 0
        
        notification_id = notifications[0].notification_id
        success = monitor.dismiss_notification(notification_id)
        assert success
        
        updated_notifications = monitor.get_active_notifications()
        assert len(updated_notifications) == len(notifications) - 1
        
        # Test dismissing non-existent notification
        success = monitor.dismiss_notification("nonexistent")
        assert not success
    
    def test_callbacks(self, monitor):
        """Test status and notification callbacks."""
        status_calls = []
        notification_calls = []
        
        def status_callback(status_update):
            status_calls.append(status_update)
        
        def notification_callback(notification):
            notification_calls.append(notification)
        
        monitor.add_status_callback(status_callback)
        monitor.add_notification_callback(notification_callback)
        
        monitor.start_monitoring("test_tool", ToolType.DATABASE_QUERY)
        
        assert len(status_calls) == 1
        assert len(notification_calls) == 1
        assert status_calls[0].tool_name == "test_tool"
        assert notification_calls[0].tool_name == "test_tool"
    
    def test_completion_callbacks(self, monitor):
        """Test completion callbacks."""
        completion_calls = []
        
        def completion_callback(tool_name, status):
            completion_calls.append((tool_name, status))
        
        monitor.start_monitoring("test_tool", ToolType.DATABASE_QUERY)
        monitor.add_completion_callback("test_tool", completion_callback)
        
        monitor.complete_execution("test_tool", True)
        
        # Note: completion callbacks are async, so they might not be called immediately
        # In a real async environment, we would await the completion
        assert len(completion_calls) == 0  # Will be called asynchronously
    
    def test_get_monitoring_summary(self, monitor):
        """Test getting monitoring summary."""
        summary = monitor.get_monitoring_summary()
        assert summary["active_tools"] == 0
        assert summary["running_tools"] == 0
        assert summary["completed_tools"] == 0
        assert summary["failed_tools"] == 0
        
        # Start some tools
        monitor.start_monitoring("tool1", ToolType.DATABASE_QUERY)
        monitor.start_monitoring("tool2", ToolType.WEB_SCRAPING)
        monitor.complete_execution("tool1", True)
        monitor.complete_execution("tool2", False)
        
        summary = monitor.get_monitoring_summary()
        assert summary["active_tools"] == 2
        assert summary["completed_tools"] == 1
        assert summary["failed_tools"] == 1
        assert "tool1" in summary["tools"]
        assert "tool2" in summary["tools"]
    
    def test_error_severity_determination(self, monitor):
        """Test error severity determination."""
        # Test critical errors
        critical_error = ConnectionError("Connection failed")
        severity = monitor._determine_error_severity(critical_error)
        assert severity == ErrorSeverity.CRITICAL
        
        # Test warning errors
        warning_error = ValueError("Invalid value")
        severity = monitor._determine_error_severity(warning_error)
        assert severity == ErrorSeverity.WARNING
        
        # Test general errors
        general_error = RuntimeError("Runtime error")
        severity = monitor._determine_error_severity(general_error)
        assert severity == ErrorSeverity.ERROR
    
    def test_recovery_options_generation(self, monitor):
        """Test recovery options generation."""
        # Test connection error
        connection_error = ConnectionError("Connection failed")
        options = monitor._generate_recovery_options("test_tool", connection_error)
        
        assert len(options) >= 3
        option_ids = [opt.option_id for opt in options]
        assert "retry" in option_ids
        assert "retry_with_fallback" in option_ids
        assert "check_connection" in option_ids
        
        # Test timeout error
        timeout_error = TimeoutError("Request timed out")
        options = monitor._generate_recovery_options("test_tool", timeout_error)
        
        option_ids = [opt.option_id for opt in options]
        assert "increase_timeout" in option_ids
        
        # Check that all options have required fields
        for option in options:
            assert option.option_id
            assert option.title
            assert option.description
            assert option.action
            assert 0 <= option.success_probability <= 1
    
    def test_troubleshooting_steps_generation(self, monitor):
        """Test troubleshooting steps generation."""
        steps = monitor._generate_troubleshooting_steps("ConnectionError")
        
        assert len(steps) > 4  # Common steps + specific steps
        assert any("network" in step.lower() for step in steps)
        assert any("connectivity" in step.lower() for step in steps)
        
        # Test unknown error type
        steps = monitor._generate_troubleshooting_steps("UnknownError")
        assert len(steps) >= 4  # At least common steps
    
    def test_related_tools_finding(self, monitor):
        """Test finding related tools."""
        monitor.start_monitoring("tool1", ToolType.DATABASE_QUERY)
        monitor.start_monitoring("tool2", ToolType.WEB_SCRAPING)
        monitor.start_monitoring("tool3", ToolType.API_CALL)
        
        related = monitor._find_related_tools("tool1")
        assert len(related) <= 3
        assert "tool1" not in related
        assert all(tool in ["tool2", "tool3"] for tool in related)


class TestExecutionMetrics:
    """Test cases for ExecutionMetrics."""
    
    def test_initialization(self):
        """Test metrics initialization."""
        start_time = datetime.now()
        metrics = ExecutionMetrics(start_time=start_time)
        
        assert metrics.start_time == start_time
        assert metrics.end_time is None
        assert metrics.duration is None
        assert metrics.memory_usage is None
        assert metrics.cpu_usage is None
        assert metrics.network_requests == 0
        assert metrics.database_queries == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
    
    def test_with_all_fields(self):
        """Test metrics with all fields."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)
        
        metrics = ExecutionMetrics(
            start_time=start_time,
            end_time=end_time,
            duration=30.0,
            memory_usage=1024.0,
            cpu_usage=50.0,
            network_requests=5,
            database_queries=3,
            cache_hits=10,
            cache_misses=2
        )
        
        assert metrics.start_time == start_time
        assert metrics.end_time == end_time
        assert metrics.duration == 30.0
        assert metrics.memory_usage == 1024.0
        assert metrics.cpu_usage == 50.0
        assert metrics.network_requests == 5
        assert metrics.database_queries == 3
        assert metrics.cache_hits == 10
        assert metrics.cache_misses == 2


class TestStatusUpdate:
    """Test cases for StatusUpdate."""
    
    def test_initialization(self):
        """Test status update initialization."""
        update = StatusUpdate(
            tool_name="test_tool",
            status=ExecutionStatus.RUNNING,
            progress=0.5,
            message="Running test"
        )
        
        assert update.tool_name == "test_tool"
        assert update.status == ExecutionStatus.RUNNING
        assert update.progress == 0.5
        assert update.message == "Running test"
        assert isinstance(update.timestamp, datetime)
        assert update.metadata == {}
        assert update.metrics is None


class TestNotification:
    """Test cases for Notification."""
    
    def test_initialization(self):
        """Test notification initialization."""
        notification = Notification(
            notification_id="test_notification",
            notification_type=NotificationType.INFO,
            title="Test Title",
            message="Test message"
        )
        
        assert notification.notification_id == "test_notification"
        assert notification.notification_type == NotificationType.INFO
        assert notification.title == "Test Title"
        assert notification.message == "Test message"
        assert notification.tool_name is None
        assert isinstance(notification.timestamp, datetime)
        assert notification.auto_dismiss is True
        assert notification.dismiss_after == 5.0
        assert notification.actions == []
        assert notification.metadata == {}
    
    def test_custom_values(self):
        """Test notification with custom values."""
        notification = Notification(
            notification_id="custom_notification",
            notification_type=NotificationType.ERROR,
            title="Error Title",
            message="Error message",
            tool_name="test_tool",
            auto_dismiss=False,
            dismiss_after=0.0,
            actions=["retry", "cancel"],
            metadata={"error_code": 500}
        )
        
        assert notification.notification_type == NotificationType.ERROR
        assert notification.tool_name == "test_tool"
        assert notification.auto_dismiss is False
        assert notification.dismiss_after == 0.0
        assert notification.actions == ["retry", "cancel"]
        assert notification.metadata == {"error_code": 500}


class TestRecoveryOption:
    """Test cases for RecoveryOption."""
    
    def test_initialization(self):
        """Test recovery option initialization."""
        option = RecoveryOption(
            option_id="retry",
            title="Retry Execution",
            description="Retry the operation",
            action="retry"
        )
        
        assert option.option_id == "retry"
        assert option.title == "Retry Execution"
        assert option.description == "Retry the operation"
        assert option.action == "retry"
        assert option.parameters == {}
        assert option.estimated_time is None
        assert option.success_probability == 0.5
    
    def test_with_parameters(self):
        """Test recovery option with parameters."""
        option = RecoveryOption(
            option_id="retry_with_timeout",
            title="Retry with Timeout",
            description="Retry with increased timeout",
            action="retry",
            parameters={"timeout": 60},
            estimated_time=30.0,
            success_probability=0.8
        )
        
        assert option.parameters == {"timeout": 60}
        assert option.estimated_time == 30.0
        assert option.success_probability == 0.8


class TestErrorVisualization:
    """Test cases for ErrorVisualization."""
    
    def test_initialization(self):
        """Test error visualization initialization."""
        viz = ErrorVisualization(
            error_type="ConnectionError",
            error_message="Connection failed",
            severity=ErrorSeverity.CRITICAL,
            context={"host": "example.com"}
        )
        
        assert viz.error_type == "ConnectionError"
        assert viz.error_message == "Connection failed"
        assert viz.severity == ErrorSeverity.CRITICAL
        assert viz.context == {"host": "example.com"}
        assert viz.recovery_options == []
        assert viz.troubleshooting_steps == []
        assert viz.related_tools == []
    
    def test_with_recovery_options(self):
        """Test error visualization with recovery options."""
        recovery_option = RecoveryOption(
            option_id="retry",
            title="Retry",
            description="Retry the operation",
            action="retry"
        )
        
        viz = ErrorVisualization(
            error_type="TimeoutError",
            error_message="Request timed out",
            severity=ErrorSeverity.WARNING,
            context={},
            recovery_options=[recovery_option],
            troubleshooting_steps=["Check network", "Increase timeout"],
            related_tools=["tool1", "tool2"]
        )
        
        assert len(viz.recovery_options) == 1
        assert viz.recovery_options[0] == recovery_option
        assert viz.troubleshooting_steps == ["Check network", "Increase timeout"]
        assert viz.related_tools == ["tool1", "tool2"]


@pytest.mark.asyncio
async def test_integration_monitoring_flow():
    """Test complete monitoring flow integration."""
    loading_manager = LoadingIndicatorManager()
    monitor = ToolExecutionMonitor(loading_manager)
    
    # Start monitoring
    monitor.start_monitoring("integration_tool", ToolType.ANALYSIS, custom_message="Starting analysis")
    
    # Update status and progress
    await monitor.update_status("integration_tool", ExecutionStatus.RUNNING, "Analysis running")
    await monitor.update_progress("integration_tool", 0.3, "30% complete")
    await monitor.update_progress("integration_tool", 0.7, "70% complete")
    
    # Complete successfully
    monitor.complete_execution("integration_tool", True, "Analysis completed", {"results": "data"})
    
    # Verify final state
    assert monitor.get_execution_status("integration_tool") == ExecutionStatus.COMPLETED
    
    metrics = monitor.get_execution_metrics("integration_tool")
    assert metrics.duration is not None
    assert metrics.duration > 0
    
    history = monitor.get_status_history("integration_tool")
    assert len(history) >= 4  # Initial, running, 2 progress updates, completion
    
    notifications = monitor.get_active_notifications()
    assert len(notifications) >= 2  # Start and completion notifications


if __name__ == "__main__":
    pytest.main([__file__])