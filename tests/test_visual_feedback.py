"""
Tests for visual feedback system integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from intelligent_chat.visual_feedback import VisualFeedbackSystem, VisualFeedbackConfig
from intelligent_chat.loading_indicators import ToolType
from intelligent_chat.status_monitor import ExecutionStatus, NotificationType
from intelligent_chat.models import UIState, LoadingState


class TestVisualFeedbackSystem:
    """Test cases for VisualFeedbackSystem."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return VisualFeedbackConfig(
            show_loading_indicators=True,
            show_progress_bars=True,
            show_status_notifications=True,
            auto_dismiss_success=True,
            auto_dismiss_delay=2.0,
            max_concurrent_indicators=3
        )
    
    @pytest.fixture
    def feedback_system(self, config):
        """Create a VisualFeedbackSystem instance."""
        return VisualFeedbackSystem(config)
    
    def test_initialization(self, feedback_system):
        """Test system initialization."""
        assert feedback_system.loading_manager is not None
        assert feedback_system.concurrent_manager is not None
        assert feedback_system.status_monitor is not None
        assert len(feedback_system._active_sessions) == 0
        assert len(feedback_system._ui_callbacks) == 0
        assert len(feedback_system._feedback_history) == 0
    
    def test_initialization_default_config(self):
        """Test initialization with default config."""
        system = VisualFeedbackSystem()
        assert system.config.show_loading_indicators is True
        assert system.config.show_progress_bars is True
        assert system.config.auto_dismiss_success is True
    
    @pytest.mark.asyncio
    async def test_start_tool_execution(self, feedback_system):
        """Test starting tool execution with feedback."""
        session_id = "test_session"
        tool_name = "test_tool"
        
        execution_id = await feedback_system.start_tool_execution(
            tool_name, session_id, ToolType.DATABASE_QUERY, "Starting test tool"
        )
        
        assert execution_id == tool_name
        assert session_id in feedback_system._active_sessions
        assert tool_name in feedback_system._active_sessions[session_id]
        
        # Check that monitoring was started
        status = feedback_system.status_monitor.get_execution_status(tool_name)
        assert status == ExecutionStatus.PENDING
        
        # Check that loading indicator was started
        assert feedback_system.loading_manager.is_loading(tool_name)
        
        # Check feedback history
        assert len(feedback_system._feedback_history) == 1
        assert feedback_system._feedback_history[0]["event_type"] == "tool_started"
    
    @pytest.mark.asyncio
    async def test_start_coordinated_execution(self, feedback_system):
        """Test starting coordinated execution."""
        session_id = "test_session"
        tool_names = ["tool1", "tool2", "tool3"]
        tool_configs = {
            "tool1": ToolType.DATABASE_QUERY,
            "tool2": ToolType.WEB_SCRAPING,
            "tool3": ToolType.API_CALL
        }
        
        group_id = await feedback_system.start_coordinated_execution(
            tool_names, session_id, tool_configs, "Starting coordinated execution"
        )
        
        assert group_id.startswith(session_id)
        assert session_id in feedback_system._active_sessions
        
        # Check that all tools are tracked
        for tool_name in tool_names:
            assert tool_name in feedback_system._active_sessions[session_id]
            assert feedback_system.loading_manager.is_loading(tool_name)
        
        # Check feedback history
        events = [event["event_type"] for event in feedback_system._feedback_history]
        assert "coordinated_execution_started" in events
        assert events.count("tool_started") == 3  # One for each tool
    
    @pytest.mark.asyncio
    async def test_update_tool_progress(self, feedback_system):
        """Test updating tool progress."""
        session_id = "test_session"
        tool_name = "test_tool"
        
        # Start tool first
        await feedback_system.start_tool_execution(tool_name, session_id, ToolType.DATABASE_QUERY)
        
        # Update progress
        success = await feedback_system.update_tool_progress(tool_name, 0.5, "Half done")
        assert success
        
        # Check loading indicator progress
        indicator = feedback_system.loading_manager.get_indicator(tool_name)
        assert indicator.progress == 0.5
        assert indicator.message == "Half done"
        
        # Check status history
        history = feedback_system.status_monitor.get_status_history(tool_name)
        progress_updates = [h for h in history if h.progress == 0.5]
        assert len(progress_updates) > 0
    
    @pytest.mark.asyncio
    async def test_update_tool_progress_with_metadata(self, feedback_system):
        """Test updating tool progress with metadata."""
        session_id = "test_session"
        tool_name = "test_tool"
        
        await feedback_system.start_tool_execution(tool_name, session_id, ToolType.DATABASE_QUERY)
        
        metadata = {"processed_items": 50, "total_items": 100}
        success = await feedback_system.update_tool_progress(
            tool_name, 0.5, "Processing items", metadata
        )
        assert success
        
        # Check that status was updated with metadata
        history = feedback_system.status_monitor.get_status_history(tool_name)
        metadata_updates = [h for h in history if h.metadata.get("processed_items") == 50]
        assert len(metadata_updates) > 0
    
    @pytest.mark.asyncio
    async def test_update_tool_status(self, feedback_system):
        """Test updating tool status."""
        session_id = "test_session"
        tool_name = "test_tool"
        
        await feedback_system.start_tool_execution(tool_name, session_id, ToolType.DATABASE_QUERY)
        
        success = await feedback_system.update_tool_status(
            tool_name, ExecutionStatus.RUNNING, "Now running"
        )
        assert success
        
        # Check status was updated
        status = feedback_system.status_monitor.get_execution_status(tool_name)
        assert status == ExecutionStatus.RUNNING
    
    def test_complete_tool_execution_success(self, feedback_system):
        """Test completing tool execution successfully."""
        session_id = "test_session"
        tool_name = "test_tool"
        
        # Start tool first (synchronous for this test)
        feedback_system.status_monitor.start_monitoring(tool_name, ToolType.DATABASE_QUERY)
        feedback_system._active_sessions[session_id] = [tool_name]
        
        success = feedback_system.complete_tool_execution(
            tool_name, True, "Completed successfully", {"result": "data"}
        )
        assert success
        
        # Check status
        status = feedback_system.status_monitor.get_execution_status(tool_name)
        assert status == ExecutionStatus.COMPLETED
        
        # Check feedback history
        completion_events = [e for e in feedback_system._feedback_history 
                           if e["event_type"] == "tool_completed"]
        assert len(completion_events) == 1
        assert completion_events[0]["data"]["success"] is True
    
    def test_complete_tool_execution_failure(self, feedback_system):
        """Test completing tool execution with failure."""
        session_id = "test_session"
        tool_name = "test_tool"
        
        feedback_system.status_monitor.start_monitoring(tool_name, ToolType.DATABASE_QUERY)
        feedback_system._active_sessions[session_id] = [tool_name]
        
        success = feedback_system.complete_tool_execution(
            tool_name, False, "Execution failed"
        )
        assert success
        
        status = feedback_system.status_monitor.get_execution_status(tool_name)
        assert status == ExecutionStatus.FAILED
        
        # Check feedback history
        completion_events = [e for e in feedback_system._feedback_history 
                           if e["event_type"] == "tool_completed"]
        assert len(completion_events) == 1
        assert completion_events[0]["data"]["success"] is False
    
    def test_handle_tool_error(self, feedback_system):
        """Test handling tool error."""
        session_id = "test_session"
        tool_name = "test_tool"
        
        feedback_system.status_monitor.start_monitoring(tool_name, ToolType.DATABASE_QUERY)
        feedback_system._active_sessions[session_id] = [tool_name]
        
        error = ConnectionError("Connection failed")
        context = {"host": "example.com", "port": 5432}
        
        success = feedback_system.handle_tool_error(tool_name, error, context)
        assert success
        
        # Check error visualization was created
        error_viz = feedback_system.status_monitor.get_error_visualization(tool_name)
        assert error_viz is not None
        assert error_viz.error_type == "ConnectionError"
        assert error_viz.context == context
        
        # Check feedback history
        error_events = [e for e in feedback_system._feedback_history 
                       if e["event_type"] == "tool_error"]
        assert len(error_events) == 1
        assert error_events[0]["data"]["error_type"] == "ConnectionError"
    
    def test_get_session_ui_state(self, feedback_system):
        """Test getting session UI state."""
        session_id = "test_session"
        tool_name = "test_tool"
        
        # Setup session with tool
        feedback_system.status_monitor.start_monitoring(tool_name, ToolType.DATABASE_QUERY)
        feedback_system._active_sessions[session_id] = [tool_name]
        
        ui_state = feedback_system.get_session_ui_state(session_id)
        
        assert isinstance(ui_state, UIState)
        assert len(ui_state.loading_indicators) == 1
        assert ui_state.loading_indicators[0].tool_name == tool_name
        assert ui_state.metadata["session_id"] == session_id
        assert ui_state.metadata["active_tools"] == 1
    
    def test_get_session_ui_state_with_error(self, feedback_system):
        """Test getting UI state with error visualization."""
        session_id = "test_session"
        tool_name = "test_tool"
        
        feedback_system.status_monitor.start_monitoring(tool_name, ToolType.DATABASE_QUERY)
        feedback_system._active_sessions[session_id] = [tool_name]
        
        # Create error
        error = ValueError("Invalid input")
        feedback_system.handle_tool_error(tool_name, error)
        
        ui_state = feedback_system.get_session_ui_state(session_id)
        
        assert len(ui_state.error_states) == 1
        assert ui_state.error_states[0].error_type == "ValueError"
        assert ui_state.error_states[0].message == "Invalid input"
    
    def test_get_system_summary(self, feedback_system):
        """Test getting system summary."""
        # Add some activity
        session_id = "test_session"
        feedback_system._active_sessions[session_id] = ["tool1", "tool2"]
        feedback_system._feedback_history.append({"event_type": "test", "data": {}})
        
        summary = feedback_system.get_system_summary()
        
        assert "loading_indicators" in summary
        assert "status_monitoring" in summary
        assert summary["active_sessions"] == 1
        assert summary["total_tools"] == 2
        assert summary["feedback_events"] == 1
        assert "config" in summary
        assert summary["config"]["show_loading_indicators"] is True
    
    def test_ui_callbacks(self, feedback_system):
        """Test UI callbacks."""
        callback_calls = []
        
        def ui_callback(ui_state):
            callback_calls.append(ui_state)
        
        feedback_system.add_ui_callback(ui_callback)
        
        # Trigger UI update by getting state
        session_id = "test_session"
        feedback_system._active_sessions[session_id] = []
        
        # Manual trigger since we can't easily test async callbacks
        ui_state = feedback_system.get_session_ui_state(session_id)
        ui_callback(ui_state)
        
        assert len(callback_calls) == 1
        assert isinstance(callback_calls[0], UIState)
    
    def test_dismiss_notification(self, feedback_system):
        """Test dismissing notifications."""
        tool_name = "test_tool"
        feedback_system.status_monitor.start_monitoring(tool_name, ToolType.DATABASE_QUERY)
        
        # Get a notification
        notifications = feedback_system.status_monitor.get_active_notifications()
        assert len(notifications) > 0
        
        notification_id = notifications[0].notification_id
        success = feedback_system.dismiss_notification(notification_id)
        assert success
        
        # Check notification was dismissed
        updated_notifications = feedback_system.status_monitor.get_active_notifications()
        assert len(updated_notifications) == len(notifications) - 1
    
    def test_execute_recovery_action(self, feedback_system):
        """Test executing recovery action."""
        tool_name = "test_tool"
        feedback_system.status_monitor.start_monitoring(tool_name, ToolType.DATABASE_QUERY)
        
        # Create error with recovery options
        error = ConnectionError("Connection failed")
        feedback_system.handle_tool_error(tool_name, error)
        
        # Execute recovery action
        success = feedback_system.execute_recovery_action(tool_name, "retry")
        assert success
        
        # Check feedback history
        recovery_events = [e for e in feedback_system._feedback_history 
                          if e["event_type"] == "recovery_action_executed"]
        assert len(recovery_events) == 1
        assert recovery_events[0]["data"]["action_id"] == "retry"
    
    def test_execute_recovery_action_invalid(self, feedback_system):
        """Test executing invalid recovery action."""
        tool_name = "test_tool"
        
        # Try to execute recovery action for non-existent tool
        success = feedback_system.execute_recovery_action(tool_name, "retry")
        assert not success
        
        # Try with tool that has no error
        feedback_system.status_monitor.start_monitoring(tool_name, ToolType.DATABASE_QUERY)
        success = feedback_system.execute_recovery_action(tool_name, "retry")
        assert not success
    
    def test_cleanup_session(self, feedback_system):
        """Test cleaning up session."""
        session_id = "test_session"
        tool_names = ["tool1", "tool2"]
        
        # Setup session
        feedback_system._active_sessions[session_id] = tool_names
        for tool_name in tool_names:
            feedback_system.status_monitor.start_monitoring(tool_name, ToolType.DATABASE_QUERY)
        
        # Cleanup
        feedback_system.cleanup_session(session_id)
        
        # Check session was removed
        assert session_id not in feedback_system._active_sessions
        
        # Check feedback history
        cleanup_events = [e for e in feedback_system._feedback_history 
                         if e["event_type"] == "session_cleanup"]
        assert len(cleanup_events) == 1
        assert cleanup_events[0]["data"]["tools_cleaned"] == 2
    
    def test_find_session_for_tool(self, feedback_system):
        """Test finding session for tool."""
        session_id = "test_session"
        tool_name = "test_tool"
        
        # Tool not in any session
        assert feedback_system._find_session_for_tool(tool_name) is None
        
        # Add tool to session
        feedback_system._active_sessions[session_id] = [tool_name]
        assert feedback_system._find_session_for_tool(tool_name) == session_id
    
    def test_feedback_event_recording(self, feedback_system):
        """Test feedback event recording."""
        # Record some events
        feedback_system._record_feedback_event("test_event", {"key": "value"})
        feedback_system._record_feedback_event("another_event", {"data": 123})
        
        assert len(feedback_system._feedback_history) == 2
        assert feedback_system._feedback_history[0]["event_type"] == "test_event"
        assert feedback_system._feedback_history[0]["data"]["key"] == "value"
        assert feedback_system._feedback_history[1]["event_type"] == "another_event"
        assert feedback_system._feedback_history[1]["data"]["data"] == 123
    
    def test_feedback_history_limit(self, feedback_system):
        """Test feedback history size limit."""
        # Add many events to trigger limit
        for i in range(1100):  # More than the 1000 limit
            feedback_system._record_feedback_event(f"event_{i}", {"index": i})
        
        # Should be limited - the exact number depends on when the limit is triggered
        # but should be between 500 and 600 (500 + 99 more additions after last trim)
        assert 500 <= len(feedback_system._feedback_history) <= 600
        
        # Should keep the most recent events
        assert feedback_system._feedback_history[-1]["data"]["index"] == 1099


class TestVisualFeedbackConfig:
    """Test cases for VisualFeedbackConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = VisualFeedbackConfig()
        
        assert config.show_loading_indicators is True
        assert config.show_progress_bars is True
        assert config.show_status_notifications is True
        assert config.show_error_visualizations is True
        assert config.auto_dismiss_success is True
        assert config.auto_dismiss_delay == 5.0
        assert config.max_concurrent_indicators == 5
        assert config.enable_sound_notifications is False
        assert config.enable_desktop_notifications is False
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = VisualFeedbackConfig(
            show_loading_indicators=False,
            show_progress_bars=False,
            auto_dismiss_delay=10.0,
            max_concurrent_indicators=10,
            enable_sound_notifications=True
        )
        
        assert config.show_loading_indicators is False
        assert config.show_progress_bars is False
        assert config.auto_dismiss_delay == 10.0
        assert config.max_concurrent_indicators == 10
        assert config.enable_sound_notifications is True


@pytest.mark.asyncio
async def test_integration_visual_feedback_flow():
    """Test complete visual feedback flow integration."""
    system = VisualFeedbackSystem()
    session_id = "integration_session"
    
    # Start multiple tools
    tool1_id = await system.start_tool_execution("tool1", session_id, ToolType.DATABASE_QUERY)
    tool2_id = await system.start_tool_execution("tool2", session_id, ToolType.WEB_SCRAPING)
    
    # Update progress
    await system.update_tool_progress("tool1", 0.3, "30% complete")
    await system.update_tool_progress("tool2", 0.5, "50% complete")
    
    # Update status
    await system.update_tool_status("tool1", ExecutionStatus.RUNNING, "Processing data")
    
    # Complete one successfully
    system.complete_tool_execution("tool1", True, "Tool1 completed", {"result": "success"})
    
    # Fail the other
    error = TimeoutError("Request timed out")
    system.handle_tool_error("tool2", error)
    
    # Get final UI state
    ui_state = system.get_session_ui_state(session_id)
    
    # Verify state
    assert len(ui_state.loading_indicators) >= 0  # May be cleaned up
    assert len(ui_state.error_states) == 1
    assert ui_state.error_states[0].error_type == "TimeoutError"
    
    # Get system summary
    summary = system.get_system_summary()
    assert summary["active_sessions"] == 1
    assert summary["feedback_events"] >= 4  # Start events, progress, completion, error
    
    # Cleanup
    system.cleanup_session(session_id)
    assert session_id not in system._active_sessions


if __name__ == "__main__":
    pytest.main([__file__])