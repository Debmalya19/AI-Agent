"""
Visual feedback system that integrates loading indicators and status monitoring
for comprehensive user experience during tool execution.
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from .loading_indicators import LoadingIndicatorManager, ConcurrentLoadingManager, ToolType
from .status_monitor import ToolExecutionMonitor, ExecutionStatus, NotificationType
from .models import LoadingState, UIState, LoadingIndicator


@dataclass
class VisualFeedbackConfig:
    """Configuration for visual feedback system."""
    show_loading_indicators: bool = True
    show_progress_bars: bool = True
    show_status_notifications: bool = True
    show_error_visualizations: bool = True
    auto_dismiss_success: bool = True
    auto_dismiss_delay: float = 5.0
    max_concurrent_indicators: int = 5
    enable_sound_notifications: bool = False
    enable_desktop_notifications: bool = False


class VisualFeedbackSystem:
    """
    Comprehensive visual feedback system that coordinates loading indicators,
    status monitoring, and user notifications for tool execution.
    """
    
    def __init__(self, config: Optional[VisualFeedbackConfig] = None):
        self.config = config or VisualFeedbackConfig()
        
        # Initialize core components
        self.loading_manager = LoadingIndicatorManager()
        self.concurrent_manager = ConcurrentLoadingManager(self.loading_manager)
        self.status_monitor = ToolExecutionMonitor(self.loading_manager)
        
        # State tracking
        self._active_sessions: Dict[str, List[str]] = {}  # session_id -> tool_names
        self._ui_callbacks: List[Callable[[UIState], None]] = []
        self._feedback_history: List[Dict[str, Any]] = []
        
        # Setup callbacks
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Setup callbacks between components."""
        # Status monitor callbacks
        self.status_monitor.add_status_callback(self._on_status_update)
        self.status_monitor.add_notification_callback(self._on_notification)
        
        # Loading manager callbacks
        self.loading_manager.add_progress_callback("*", self._on_progress_update)
    
    async def start_tool_execution(self, tool_name: str, session_id: str,
                                 tool_type: Optional[ToolType] = None,
                                 custom_message: Optional[str] = None,
                                 timeout: Optional[float] = None) -> str:
        """
        Start comprehensive visual feedback for tool execution.
        
        Args:
            tool_name: Name of the tool being executed
            session_id: Session identifier for grouping related tools
            tool_type: Type of tool for appropriate visual feedback
            custom_message: Custom message for initial feedback
            timeout: Execution timeout in seconds
            
        Returns:
            Tool execution identifier
        """
        # Track session
        if session_id not in self._active_sessions:
            self._active_sessions[session_id] = []
        self._active_sessions[session_id].append(tool_name)
        
        # Start monitoring
        execution_id = self.status_monitor.start_monitoring(
            tool_name, tool_type, timeout, custom_message
        )
        
        # Update UI state
        await self._update_ui_state(session_id)
        
        # Record feedback event
        self._record_feedback_event("tool_started", {
            "tool_name": tool_name,
            "session_id": session_id,
            "tool_type": tool_type.value if tool_type else None,
            "message": custom_message
        })
        
        return execution_id
    
    async def start_coordinated_execution(self, tool_names: List[str], session_id: str,
                                        tool_configs: Dict[str, ToolType],
                                        group_message: Optional[str] = None) -> str:
        """
        Start coordinated execution of multiple tools with synchronized feedback.
        
        Args:
            tool_names: List of tool names to execute
            session_id: Session identifier
            tool_configs: Tool type configuration for each tool
            group_message: Message for the coordinated group
            
        Returns:
            Coordination group identifier
        """
        group_id = f"{session_id}_group_{len(self._active_sessions.get(session_id, []))}"
        
        # Create coordination group
        self.concurrent_manager.create_coordination_group(group_id, tool_names)
        
        # Start coordinated loading
        indicators = await self.concurrent_manager.start_coordinated_loading(group_id, tool_configs)
        
        # Start monitoring for each tool
        for tool_name in tool_names:
            tool_type = tool_configs.get(tool_name, ToolType.UNKNOWN)
            await self.start_tool_execution(tool_name, session_id, tool_type)
        
        # Update UI state
        await self._update_ui_state(session_id)
        
        # Record coordination event
        self._record_feedback_event("coordinated_execution_started", {
            "group_id": group_id,
            "tool_names": tool_names,
            "session_id": session_id,
            "message": group_message
        })
        
        return group_id
    
    async def update_tool_progress(self, tool_name: str, progress: float,
                                 message: Optional[str] = None,
                                 metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update progress for a tool with comprehensive feedback.
        
        Args:
            tool_name: Name of the tool
            progress: Progress value (0.0 to 1.0)
            message: Progress message
            metadata: Additional metadata
            
        Returns:
            True if update was successful
        """
        # Update status monitor
        success = await self.status_monitor.update_progress(tool_name, progress, message)
        
        if success and metadata:
            # Update status with metadata
            await self.status_monitor.update_status(
                tool_name, ExecutionStatus.RUNNING, message, metadata
            )
        
        # Find session and update UI
        session_id = self._find_session_for_tool(tool_name)
        if session_id:
            await self._update_ui_state(session_id)
        
        return success
    
    async def update_tool_status(self, tool_name: str, status: ExecutionStatus,
                               message: Optional[str] = None,
                               metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update status for a tool with visual feedback.
        
        Args:
            tool_name: Name of the tool
            status: New execution status
            message: Status message
            metadata: Additional metadata
            
        Returns:
            True if update was successful
        """
        success = await self.status_monitor.update_status(tool_name, status, message, metadata)
        
        # Update UI state
        session_id = self._find_session_for_tool(tool_name)
        if session_id:
            await self._update_ui_state(session_id)
        
        return success
    
    def complete_tool_execution(self, tool_name: str, success: bool,
                              result_message: Optional[str] = None,
                              result_data: Optional[Any] = None) -> bool:
        """
        Complete tool execution with final feedback.
        
        Args:
            tool_name: Name of the tool
            success: Whether execution was successful
            result_message: Final result message
            result_data: Result data
            
        Returns:
            True if completion was successful
        """
        # Complete monitoring
        completion_success = self.status_monitor.complete_execution(
            tool_name, success, result_message, result_data
        )
        
        # Record completion event
        self._record_feedback_event("tool_completed", {
            "tool_name": tool_name,
            "success": success,
            "message": result_message,
            "has_result_data": result_data is not None
        })
        
        # Schedule UI update
        session_id = self._find_session_for_tool(tool_name)
        if session_id:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._update_ui_state(session_id))
            except RuntimeError:
                pass
        
        return completion_success
    
    def handle_tool_error(self, tool_name: str, error: Exception,
                         context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle tool error with comprehensive error visualization.
        
        Args:
            tool_name: Name of the tool that failed
            error: The exception that occurred
            context: Additional error context
            
        Returns:
            True if error handling was successful
        """
        # Create error visualization
        error_viz = self.status_monitor.create_error_visualization(tool_name, error, context)
        
        # Complete execution as failed
        self.complete_tool_execution(tool_name, False, f"Error: {str(error)}")
        
        # Record error event
        self._record_feedback_event("tool_error", {
            "tool_name": tool_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": error_viz.severity.value,
            "recovery_options_count": len(error_viz.recovery_options)
        })
        
        return True
    
    def get_session_ui_state(self, session_id: str) -> UIState:
        """
        Get comprehensive UI state for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            UI state with all visual feedback elements
        """
        tool_names = self._active_sessions.get(session_id, [])
        
        # Collect loading indicators
        loading_indicators = []
        for tool_name in tool_names:
            indicator = self.loading_manager.get_indicator(tool_name)
            if indicator:
                loading_indicators.append(indicator)
        
        # Collect notifications
        notifications = self.status_monitor.get_active_notifications()
        session_notifications = [n for n in notifications 
                               if n.tool_name in tool_names or n.tool_name is None]
        
        # Collect error states
        error_states = []
        for tool_name in tool_names:
            error_viz = self.status_monitor.get_error_visualization(tool_name)
            if error_viz:
                from .models import ErrorState
                error_state = ErrorState(
                    error_type=error_viz.error_type,
                    message=error_viz.error_message,
                    severity=error_viz.severity,
                    recovery_actions=[opt.option_id for opt in error_viz.recovery_options],
                    context=error_viz.context
                )
                error_states.append(error_state)
        
        # Create UI state
        ui_state = UIState(
            loading_indicators=loading_indicators,
            error_states=error_states,
            metadata={
                "session_id": session_id,
                "active_tools": len(tool_names),
                "notifications": [
                    {
                        "id": n.notification_id,
                        "type": n.notification_type.value,
                        "title": n.title,
                        "message": n.message,
                        "auto_dismiss": n.auto_dismiss,
                        "actions": n.actions
                    }
                    for n in session_notifications
                ]
            }
        )
        
        return ui_state
    
    def get_system_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive system summary.
        
        Returns:
            System summary with all feedback statistics
        """
        loading_summary = self.loading_manager.get_loading_summary()
        monitoring_summary = self.status_monitor.get_monitoring_summary()
        
        return {
            "loading_indicators": loading_summary,
            "status_monitoring": monitoring_summary,
            "active_sessions": len(self._active_sessions),
            "total_tools": sum(len(tools) for tools in self._active_sessions.values()),
            "feedback_events": len(self._feedback_history),
            "config": {
                "show_loading_indicators": self.config.show_loading_indicators,
                "show_progress_bars": self.config.show_progress_bars,
                "show_status_notifications": self.config.show_status_notifications,
                "max_concurrent_indicators": self.config.max_concurrent_indicators
            }
        }
    
    def add_ui_callback(self, callback: Callable[[UIState], None]):
        """Add callback for UI state updates."""
        self._ui_callbacks.append(callback)
    
    def dismiss_notification(self, notification_id: str) -> bool:
        """Dismiss a notification."""
        return self.status_monitor.dismiss_notification(notification_id)
    
    def execute_recovery_action(self, tool_name: str, action_id: str,
                              parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Execute a recovery action for a failed tool.
        
        Args:
            tool_name: Name of the tool
            action_id: Recovery action identifier
            parameters: Action parameters
            
        Returns:
            True if action was executed
        """
        error_viz = self.status_monitor.get_error_visualization(tool_name)
        if not error_viz:
            return False
        
        # Find recovery option
        recovery_option = next((opt for opt in error_viz.recovery_options 
                              if opt.option_id == action_id), None)
        if not recovery_option:
            return False
        
        # Record recovery attempt
        self._record_feedback_event("recovery_action_executed", {
            "tool_name": tool_name,
            "action_id": action_id,
            "action_title": recovery_option.title,
            "parameters": parameters or {}
        })
        
        # This would typically trigger the actual recovery action
        # For now, we just record the attempt
        return True
    
    def cleanup_session(self, session_id: str):
        """Clean up all feedback for a session."""
        tool_names = self._active_sessions.get(session_id, [])
        
        # Clean up each tool
        for tool_name in tool_names:
            self.loading_manager.manual_cleanup(tool_name)
        
        # Remove session
        self._active_sessions.pop(session_id, None)
        
        # Record cleanup event
        self._record_feedback_event("session_cleanup", {
            "session_id": session_id,
            "tools_cleaned": len(tool_names)
        })
    
    # Private helper methods
    
    def _find_session_for_tool(self, tool_name: str) -> Optional[str]:
        """Find session ID for a tool."""
        for session_id, tool_names in self._active_sessions.items():
            if tool_name in tool_names:
                return session_id
        return None
    
    async def _update_ui_state(self, session_id: str):
        """Update UI state and notify callbacks."""
        ui_state = self.get_session_ui_state(session_id)
        
        # Notify callbacks
        for callback in self._ui_callbacks:
            try:
                callback(ui_state)
            except Exception as e:
                print(f"Error in UI callback: {e}")
    
    def _on_status_update(self, status_update):
        """Handle status updates from monitor."""
        session_id = self._find_session_for_tool(status_update.tool_name)
        if session_id:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._update_ui_state(session_id))
            except RuntimeError:
                pass
    
    def _on_notification(self, notification):
        """Handle notifications from monitor."""
        if notification.tool_name:
            session_id = self._find_session_for_tool(notification.tool_name)
            if session_id:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._update_ui_state(session_id))
                except RuntimeError:
                    pass
    
    def _on_progress_update(self, tool_name: str, progress: float, message: str):
        """Handle progress updates from loading manager."""
        session_id = self._find_session_for_tool(tool_name)
        if session_id:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._update_ui_state(session_id))
            except RuntimeError:
                pass
    
    def _record_feedback_event(self, event_type: str, data: Dict[str, Any]):
        """Record feedback event for analytics."""
        from datetime import datetime
        
        event = {
            "timestamp": datetime.now(),
            "event_type": event_type,
            "data": data
        }
        
        self._feedback_history.append(event)
        
        # Limit history size
        if len(self._feedback_history) > 1000:
            self._feedback_history = self._feedback_history[-500:]