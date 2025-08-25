# Visual Feedback System

The Visual Feedback System provides comprehensive user interface feedback during tool execution in the intelligent chat system. It combines loading indicators, status monitoring, and error visualization to create a responsive and informative user experience.

## Overview

The system consists of three main components:

1. **Loading Indicators** - Visual feedback for tool execution progress
2. **Status Monitoring** - Comprehensive tracking of tool execution states
3. **Visual Feedback Integration** - Unified system that coordinates all feedback

## Components

### 1. Loading Indicators (`loading_indicators.py`)

Manages visual loading indicators with different configurations for different tool types.

#### Key Classes:
- `LoadingIndicatorManager` - Core manager for loading indicators
- `ConcurrentLoadingManager` - Handles multiple concurrent tool executions
- `ToolType` - Enum defining different tool types with specific configurations

#### Features:
- **Tool-specific configurations** - Different loading behaviors for database queries, web scraping, API calls, etc.
- **Real-time progress tracking** - Automatic progress updates based on time estimates
- **Concurrent execution support** - Coordinate multiple tools running simultaneously
- **Customizable indicators** - Progress bars, spinners, estimated time display

#### Example Usage:
```python
from intelligent_chat.loading_indicators import LoadingIndicatorManager, ToolType

manager = LoadingIndicatorManager()

# Start loading indicator
indicator = manager.start_loading("database_query", ToolType.DATABASE_QUERY)

# Update progress
await manager.update_progress("database_query", 0.5, "Processing results...")

# Complete
manager.complete_loading("database_query", True, "Query completed")
```

### 2. Status Monitoring (`status_monitor.py`)

Provides comprehensive monitoring of tool execution with status tracking, notifications, and error handling.

#### Key Classes:
- `ToolExecutionMonitor` - Main monitoring system
- `ExecutionStatus` - Enum for different execution states
- `Notification` - User notifications with different types and actions
- `ErrorVisualization` - Rich error display with recovery options

#### Features:
- **Execution status tracking** - Pending, running, completed, failed, timeout, cancelled
- **Real-time notifications** - Success, error, warning, and info notifications
- **Error visualization** - Detailed error information with recovery suggestions
- **Metrics collection** - Execution time, resource usage, performance data
- **Recovery actions** - Automated suggestions for handling failures

#### Example Usage:
```python
from intelligent_chat.status_monitor import ToolExecutionMonitor, ExecutionStatus

monitor = ToolExecutionMonitor(loading_manager)

# Start monitoring
monitor.start_monitoring("web_scraper", ToolType.WEB_SCRAPING)

# Update status
await monitor.update_status("web_scraper", ExecutionStatus.RUNNING, "Fetching data...")

# Handle error
error = ConnectionError("Failed to connect")
monitor.create_error_visualization("web_scraper", error)

# Complete
monitor.complete_execution("web_scraper", True, "Scraping completed")
```

### 3. Visual Feedback Integration (`visual_feedback.py`)

Unified system that coordinates all visual feedback components for a seamless user experience.

#### Key Classes:
- `VisualFeedbackSystem` - Main integration system
- `VisualFeedbackConfig` - Configuration for feedback behavior
- `UIState` - Complete UI state information

#### Features:
- **Session management** - Group related tools by session
- **Coordinated execution** - Handle multiple tools with synchronized feedback
- **UI state generation** - Complete UI state for frontend rendering
- **Event tracking** - Analytics and history of all feedback events
- **Recovery actions** - Execute user-selected recovery options

#### Example Usage:
```python
from intelligent_chat.visual_feedback import VisualFeedbackSystem, VisualFeedbackConfig

# Configure system
config = VisualFeedbackConfig(
    show_loading_indicators=True,
    show_progress_bars=True,
    auto_dismiss_success=True
)

system = VisualFeedbackSystem(config)

# Start tool execution with feedback
await system.start_tool_execution(
    "data_analyzer", 
    "user_session_123", 
    ToolType.ANALYSIS,
    "Analyzing user data..."
)

# Update progress
await system.update_tool_progress("data_analyzer", 0.3, "Processing 30%")

# Get UI state for frontend
ui_state = system.get_session_ui_state("user_session_123")

# Complete execution
system.complete_tool_execution("data_analyzer", True, "Analysis complete", results)
```

## Tool Types and Configurations

The system supports different tool types with optimized configurations:

| Tool Type | Estimated Duration | Progress Steps | Visual Elements |
|-----------|-------------------|----------------|-----------------|
| `DATABASE_QUERY` | 2.0s | Connect → Execute → Process | Progress bar, time estimate |
| `WEB_SCRAPING` | 5.0s | Fetch → Parse → Extract | Progress bar, spinner, time |
| `API_CALL` | 3.0s | Request → Response | Spinner, time estimate |
| `FILE_PROCESSING` | 4.0s | Read → Process → Output | Progress bar, time estimate |
| `ANALYSIS` | 6.0s | Analyze → Compute → Format | Progress bar, spinner, time |
| `SEARCH` | 3.0s | Search → Rank → Format | Spinner |
| `GENERATION` | 8.0s | Prepare → Generate → Format | Progress bar, spinner, time |

## Error Handling and Recovery

The system provides comprehensive error handling with visual feedback:

### Error Severity Levels:
- **INFO** - Informational messages
- **WARNING** - Non-critical issues
- **ERROR** - Standard errors
- **CRITICAL** - System-critical failures

### Recovery Options:
- **Retry** - Retry with same parameters
- **Retry with Fallback** - Retry with alternative approach
- **Check Connection** - Verify connectivity (for connection errors)
- **Increase Timeout** - Retry with longer timeout (for timeout errors)

### Error Visualization:
```python
# Error visualization includes:
error_viz = ErrorVisualization(
    error_type="ConnectionError",
    error_message="Failed to connect to database",
    severity=ErrorSeverity.CRITICAL,
    context={"host": "db.example.com", "port": 5432},
    recovery_options=[retry_option, fallback_option],
    troubleshooting_steps=["Check network", "Verify credentials"],
    related_tools=["backup_db", "cache_service"]
)
```

## UI State Management

The system generates comprehensive UI state information for frontend rendering:

```python
ui_state = UIState(
    loading_indicators=[
        LoadingIndicator(
            tool_name="data_processor",
            state=LoadingState.PROCESSING,
            progress=0.65,
            message="Processing data...",
            estimated_time=15.0
        )
    ],
    error_states=[
        ErrorState(
            error_type="TimeoutError",
            message="Request timed out",
            severity=ErrorSeverity.WARNING,
            recovery_actions=["retry", "increase_timeout"]
        )
    ],
    metadata={
        "session_id": "user_session_123",
        "active_tools": 2,
        "notifications": [...]
    }
)
```

## Configuration Options

### VisualFeedbackConfig:
```python
config = VisualFeedbackConfig(
    show_loading_indicators=True,      # Show loading spinners/progress bars
    show_progress_bars=True,           # Show detailed progress bars
    show_status_notifications=True,    # Show status notifications
    show_error_visualizations=True,    # Show detailed error information
    auto_dismiss_success=True,         # Auto-dismiss success notifications
    auto_dismiss_delay=5.0,           # Delay before auto-dismiss (seconds)
    max_concurrent_indicators=5,       # Maximum concurrent loading indicators
    enable_sound_notifications=False,  # Enable sound notifications
    enable_desktop_notifications=False # Enable desktop notifications
)
```

## Integration with Chat Manager

The visual feedback system integrates seamlessly with the chat manager:

```python
from intelligent_chat.chat_manager import ChatManager
from intelligent_chat.visual_feedback import VisualFeedbackSystem

class EnhancedChatManager(ChatManager):
    def __init__(self):
        super().__init__()
        self.feedback_system = VisualFeedbackSystem()
    
    async def process_message_with_feedback(self, message, user_id, session_id):
        # Start feedback for message processing
        await self.feedback_system.start_tool_execution(
            "message_processor", session_id, ToolType.ANALYSIS
        )
        
        try:
            # Process message with progress updates
            await self.feedback_system.update_tool_progress(
                "message_processor", 0.3, "Analyzing context..."
            )
            
            # ... processing logic ...
            
            # Complete successfully
            self.feedback_system.complete_tool_execution(
                "message_processor", True, "Message processed", response
            )
            
        except Exception as e:
            # Handle error with visualization
            self.feedback_system.handle_tool_error("message_processor", e)
            raise
```

## Testing

The system includes comprehensive tests:

- `test_loading_indicators.py` - Tests for loading indicator functionality
- `test_status_monitor.py` - Tests for status monitoring and error handling
- `test_visual_feedback.py` - Integration tests for the complete system

Run tests with:
```bash
python -m pytest ai-agent/test_loading_indicators.py -v
python -m pytest ai-agent/test_status_monitor.py -v
python -m pytest ai-agent/test_visual_feedback.py -v
```

## Performance Considerations

### Memory Management:
- Automatic cleanup of completed indicators after configurable delay
- History size limits to prevent memory leaks
- Efficient event tracking with circular buffers

### Async Operations:
- Non-blocking progress updates
- Concurrent tool execution support
- Graceful handling of event loop availability

### Resource Limits:
- Configurable maximum concurrent indicators
- Timeout handling for long-running operations
- Resource usage monitoring and reporting

## Future Enhancements

Potential future improvements:

1. **Machine Learning Integration** - Learn from user interactions to improve feedback timing
2. **Advanced Analytics** - Detailed performance metrics and user behavior analysis
3. **Custom Themes** - Configurable visual themes for different use cases
4. **Voice Feedback** - Audio notifications for accessibility
5. **Predictive Loading** - Pre-load indicators based on user patterns
6. **Real-time Collaboration** - Shared feedback states across multiple users

## Conclusion

The Visual Feedback System provides a comprehensive, flexible, and user-friendly way to handle tool execution feedback in the intelligent chat system. It ensures users are always informed about what's happening, can understand and recover from errors, and have a smooth, responsive experience during tool execution.