"""
Loading indicator system for visual feedback during tool execution.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from .models import LoadingIndicator, LoadingState


class ToolType(Enum):
    """Types of tools for different loading indicators."""
    DATABASE_QUERY = "database_query"
    WEB_SCRAPING = "web_scraping"
    API_CALL = "api_call"
    FILE_PROCESSING = "file_processing"
    ANALYSIS = "analysis"
    SEARCH = "search"
    GENERATION = "generation"
    UNKNOWN = "unknown"


@dataclass
class ProgressUpdate:
    """Progress update for tool execution."""
    tool_name: str
    progress: float
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadingConfiguration:
    """Configuration for loading indicators."""
    tool_type: ToolType
    estimated_duration: float
    progress_steps: List[str] = field(default_factory=list)
    show_progress_bar: bool = True
    show_spinner: bool = True
    show_estimated_time: bool = True
    update_interval: float = 0.5


class LoadingIndicatorManager:
    """Manages loading indicators for tool execution."""
    
    def __init__(self):
        self._active_indicators: Dict[str, LoadingIndicator] = {}
        self._progress_callbacks: Dict[str, List[Callable]] = {}
        self._configurations: Dict[str, LoadingConfiguration] = {}
        self._start_times: Dict[str, datetime] = {}
        self._update_tasks: Dict[str, asyncio.Task] = {}
        
        # Default configurations for different tool types
        self._setup_default_configurations()
    
    def _setup_default_configurations(self):
        """Setup default configurations for different tool types."""
        self._configurations.update({
            ToolType.DATABASE_QUERY.value: LoadingConfiguration(
                tool_type=ToolType.DATABASE_QUERY,
                estimated_duration=2.0,
                progress_steps=["Connecting to database", "Executing query", "Processing results"],
                show_progress_bar=True,
                show_spinner=False,
                show_estimated_time=True
            ),
            ToolType.WEB_SCRAPING.value: LoadingConfiguration(
                tool_type=ToolType.WEB_SCRAPING,
                estimated_duration=5.0,
                progress_steps=["Fetching webpage", "Parsing content", "Extracting data"],
                show_progress_bar=True,
                show_spinner=True,
                show_estimated_time=True
            ),
            ToolType.API_CALL.value: LoadingConfiguration(
                tool_type=ToolType.API_CALL,
                estimated_duration=3.0,
                progress_steps=["Making API request", "Processing response"],
                show_progress_bar=False,
                show_spinner=True,
                show_estimated_time=True
            ),
            ToolType.FILE_PROCESSING.value: LoadingConfiguration(
                tool_type=ToolType.FILE_PROCESSING,
                estimated_duration=4.0,
                progress_steps=["Reading file", "Processing content", "Generating output"],
                show_progress_bar=True,
                show_spinner=False,
                show_estimated_time=True
            ),
            ToolType.ANALYSIS.value: LoadingConfiguration(
                tool_type=ToolType.ANALYSIS,
                estimated_duration=6.0,
                progress_steps=["Analyzing data", "Computing results", "Formatting output"],
                show_progress_bar=True,
                show_spinner=True,
                show_estimated_time=True
            ),
            ToolType.SEARCH.value: LoadingConfiguration(
                tool_type=ToolType.SEARCH,
                estimated_duration=3.0,
                progress_steps=["Searching index", "Ranking results", "Formatting results"],
                show_progress_bar=False,
                show_spinner=True,
                show_estimated_time=False
            ),
            ToolType.GENERATION.value: LoadingConfiguration(
                tool_type=ToolType.GENERATION,
                estimated_duration=8.0,
                progress_steps=["Preparing context", "Generating content", "Formatting output"],
                show_progress_bar=True,
                show_spinner=True,
                show_estimated_time=True
            ),
            ToolType.UNKNOWN.value: LoadingConfiguration(
                tool_type=ToolType.UNKNOWN,
                estimated_duration=5.0,
                progress_steps=["Processing"],
                show_progress_bar=False,
                show_spinner=True,
                show_estimated_time=False
            )
        })
    
    def register_tool_configuration(self, tool_name: str, config: LoadingConfiguration):
        """Register a custom configuration for a specific tool."""
        self._configurations[tool_name] = config
    
    def start_loading(self, tool_name: str, tool_type: Optional[ToolType] = None, 
                     custom_message: Optional[str] = None) -> LoadingIndicator:
        """Start loading indicator for a tool."""
        # Determine configuration
        config_key = tool_name if tool_name in self._configurations else (
            tool_type.value if tool_type else ToolType.UNKNOWN.value
        )
        config = self._configurations.get(config_key, self._configurations[ToolType.UNKNOWN.value])
        
        # Create loading indicator
        indicator = LoadingIndicator(
            tool_name=tool_name,
            state=LoadingState.LOADING,
            progress=0.0,
            message=custom_message or f"Starting {tool_name}...",
            estimated_time=config.estimated_duration
        )
        
        self._active_indicators[tool_name] = indicator
        self._start_times[tool_name] = datetime.now()
        
        # Start progress update task if needed and event loop is running
        if config.progress_steps:
            try:
                loop = asyncio.get_running_loop()
                self._update_tasks[tool_name] = loop.create_task(
                    self._auto_update_progress(tool_name, config)
                )
            except RuntimeError:
                # No event loop running, skip auto-update
                pass
        
        return indicator
    
    async def _auto_update_progress(self, tool_name: str, config: LoadingConfiguration):
        """Automatically update progress based on configuration."""
        try:
            steps = config.progress_steps
            step_duration = config.estimated_duration / len(steps)
            
            for i, step_message in enumerate(steps):
                if tool_name not in self._active_indicators:
                    break
                
                progress = (i + 1) / len(steps)
                await self.update_progress(tool_name, progress, step_message)
                
                # Wait for step duration or until completion
                await asyncio.sleep(step_duration)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            # Log error but don't crash
            print(f"Error in auto progress update for {tool_name}: {e}")
    
    async def update_progress(self, tool_name: str, progress: float, 
                            message: Optional[str] = None) -> bool:
        """Update progress for a tool."""
        if tool_name not in self._active_indicators:
            return False
        
        indicator = self._active_indicators[tool_name]
        indicator.progress = min(max(progress, 0.0), 1.0)
        indicator.state = LoadingState.PROCESSING if progress < 1.0 else LoadingState.COMPLETED
        
        if message:
            indicator.message = message
        
        # Update estimated time based on actual progress
        if progress > 0 and tool_name in self._start_times:
            elapsed = (datetime.now() - self._start_times[tool_name]).total_seconds()
            estimated_total = elapsed / progress
            indicator.estimated_time = max(0, estimated_total - elapsed)
        
        # Notify callbacks
        await self._notify_progress_callbacks(tool_name, progress, message or "")
        
        return True
    
    def complete_loading(self, tool_name: str, success: bool = True, 
                        final_message: Optional[str] = None) -> bool:
        """Complete loading for a tool."""
        if tool_name not in self._active_indicators:
            return False
        
        indicator = self._active_indicators[tool_name]
        indicator.progress = 1.0
        indicator.state = LoadingState.COMPLETED if success else LoadingState.ERROR
        indicator.estimated_time = 0.0
        
        if final_message:
            indicator.message = final_message
        elif success:
            indicator.message = f"{tool_name} completed successfully"
        else:
            indicator.message = f"{tool_name} failed"
        
        # Cancel auto-update task
        if tool_name in self._update_tasks:
            self._update_tasks[tool_name].cancel()
            del self._update_tasks[tool_name]
        
        # Clean up after a delay if event loop is running
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._cleanup_indicator(tool_name, delay=2.0))
        except RuntimeError:
            # No event loop running, don't clean up immediately in tests
            # Let the indicator remain for inspection
            pass
        
        return True
    
    async def _cleanup_indicator(self, tool_name: str, delay: float = 2.0):
        """Clean up indicator after delay."""
        await asyncio.sleep(delay)
        self._active_indicators.pop(tool_name, None)
        self._start_times.pop(tool_name, None)
        self._progress_callbacks.pop(tool_name, None)
    
    def get_active_indicators(self) -> List[LoadingIndicator]:
        """Get all active loading indicators."""
        return list(self._active_indicators.values())
    
    def get_indicator(self, tool_name: str) -> Optional[LoadingIndicator]:
        """Get specific loading indicator."""
        return self._active_indicators.get(tool_name)
    
    def is_loading(self, tool_name: str) -> bool:
        """Check if tool is currently loading."""
        indicator = self._active_indicators.get(tool_name)
        return indicator is not None and indicator.state in [LoadingState.LOADING, LoadingState.PROCESSING]
    
    def add_progress_callback(self, tool_name: str, callback: Callable[[str, float, str], None]):
        """Add callback for progress updates."""
        if tool_name not in self._progress_callbacks:
            self._progress_callbacks[tool_name] = []
        self._progress_callbacks[tool_name].append(callback)
    
    async def _notify_progress_callbacks(self, tool_name: str, progress: float, message: str):
        """Notify progress callbacks."""
        callbacks = self._progress_callbacks.get(tool_name, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(tool_name, progress, message)
                else:
                    callback(tool_name, progress, message)
            except Exception as e:
                print(f"Error in progress callback for {tool_name}: {e}")
    
    def get_concurrent_loading_count(self) -> int:
        """Get number of currently loading tools."""
        return len([i for i in self._active_indicators.values() 
                   if i.state in [LoadingState.LOADING, LoadingState.PROCESSING]])
    
    def get_loading_summary(self) -> Dict[str, Any]:
        """Get summary of loading states."""
        indicators = list(self._active_indicators.values())
        return {
            "total_active": len(indicators),
            "loading": len([i for i in indicators if i.state == LoadingState.LOADING]),
            "processing": len([i for i in indicators if i.state == LoadingState.PROCESSING]),
            "completed": len([i for i in indicators if i.state == LoadingState.COMPLETED]),
            "error": len([i for i in indicators if i.state == LoadingState.ERROR]),
            "tools": [i.tool_name for i in indicators]
        }
    
    def manual_cleanup(self, tool_name: str):
        """Manually clean up indicator (useful for testing)."""
        self._active_indicators.pop(tool_name, None)
        self._start_times.pop(tool_name, None)
        self._progress_callbacks.pop(tool_name, None)
        if tool_name in self._update_tasks:
            self._update_tasks[tool_name].cancel()
            del self._update_tasks[tool_name]


class ConcurrentLoadingManager:
    """Manages multiple concurrent loading indicators with coordination."""
    
    def __init__(self, loading_manager: LoadingIndicatorManager):
        self.loading_manager = loading_manager
        self._coordination_groups: Dict[str, List[str]] = {}
        self._group_progress: Dict[str, float] = {}
    
    def create_coordination_group(self, group_id: str, tool_names: List[str]):
        """Create a coordination group for related tools."""
        self._coordination_groups[group_id] = tool_names
        self._group_progress[group_id] = 0.0
    
    async def start_coordinated_loading(self, group_id: str, tool_configs: Dict[str, ToolType]):
        """Start loading for a coordinated group of tools."""
        if group_id not in self._coordination_groups:
            raise ValueError(f"Coordination group {group_id} not found")
        
        tool_names = self._coordination_groups[group_id]
        indicators = []
        
        for tool_name in tool_names:
            tool_type = tool_configs.get(tool_name, ToolType.UNKNOWN)
            indicator = self.loading_manager.start_loading(tool_name, tool_type)
            indicators.append(indicator)
        
        return indicators
    
    async def update_group_progress(self, group_id: str):
        """Update overall progress for a coordination group."""
        if group_id not in self._coordination_groups:
            return
        
        tool_names = self._coordination_groups[group_id]
        total_progress = 0.0
        active_tools = 0
        
        for tool_name in tool_names:
            indicator = self.loading_manager.get_indicator(tool_name)
            if indicator:
                total_progress += indicator.progress
                active_tools += 1
        
        if active_tools > 0:
            self._group_progress[group_id] = total_progress / active_tools
    
    def get_group_progress(self, group_id: str) -> float:
        """Get overall progress for a coordination group."""
        return self._group_progress.get(group_id, 0.0)
    
    def cleanup_group(self, group_id: str):
        """Clean up coordination group."""
        self._coordination_groups.pop(group_id, None)
        self._group_progress.pop(group_id, None)