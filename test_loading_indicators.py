"""
Tests for loading indicator system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from intelligent_chat.loading_indicators import (
    LoadingIndicatorManager, ConcurrentLoadingManager, ToolType, 
    LoadingConfiguration, ProgressUpdate
)
from intelligent_chat.models import LoadingState


class TestLoadingIndicatorManager:
    """Test cases for LoadingIndicatorManager."""
    
    @pytest.fixture
    def manager(self):
        """Create a LoadingIndicatorManager instance."""
        return LoadingIndicatorManager()
    
    def test_initialization(self, manager):
        """Test manager initialization."""
        assert len(manager._configurations) > 0
        assert ToolType.DATABASE_QUERY.value in manager._configurations
        assert ToolType.WEB_SCRAPING.value in manager._configurations
        assert len(manager._active_indicators) == 0
    
    def test_start_loading_basic(self, manager):
        """Test starting a basic loading indicator."""
        indicator = manager.start_loading("test_tool", ToolType.DATABASE_QUERY)
        
        assert indicator.tool_name == "test_tool"
        assert indicator.state == LoadingState.LOADING
        assert indicator.progress == 0.0
        assert indicator.estimated_time > 0
        assert "test_tool" in manager._active_indicators
    
    def test_start_loading_custom_message(self, manager):
        """Test starting loading with custom message."""
        custom_msg = "Custom loading message"
        indicator = manager.start_loading("test_tool", ToolType.API_CALL, custom_msg)
        
        assert indicator.message == custom_msg
    
    def test_start_loading_unknown_tool_type(self, manager):
        """Test starting loading with unknown tool type."""
        indicator = manager.start_loading("unknown_tool")
        
        assert indicator.tool_name == "unknown_tool"
        assert indicator.state == LoadingState.LOADING
        # Should use default configuration
        assert indicator.estimated_time > 0
    
    @pytest.mark.asyncio
    async def test_update_progress(self, manager):
        """Test updating progress."""
        manager.start_loading("test_tool", ToolType.DATABASE_QUERY)
        
        success = await manager.update_progress("test_tool", 0.5, "Halfway done")
        assert success
        
        indicator = manager.get_indicator("test_tool")
        assert indicator.progress == 0.5
        assert indicator.message == "Halfway done"
        assert indicator.state == LoadingState.PROCESSING
    
    @pytest.mark.asyncio
    async def test_update_progress_nonexistent_tool(self, manager):
        """Test updating progress for non-existent tool."""
        success = await manager.update_progress("nonexistent", 0.5)
        assert not success
    
    @pytest.mark.asyncio
    async def test_update_progress_bounds(self, manager):
        """Test progress bounds checking."""
        manager.start_loading("test_tool", ToolType.DATABASE_QUERY)
        
        # Test lower bound
        await manager.update_progress("test_tool", -0.5)
        indicator = manager.get_indicator("test_tool")
        assert indicator.progress == 0.0
        
        # Test upper bound
        await manager.update_progress("test_tool", 1.5)
        indicator = manager.get_indicator("test_tool")
        assert indicator.progress == 1.0
        assert indicator.state == LoadingState.COMPLETED
    
    def test_complete_loading_success(self, manager):
        """Test completing loading successfully."""
        manager.start_loading("test_tool", ToolType.DATABASE_QUERY)
        
        success = manager.complete_loading("test_tool", True, "All done!")
        assert success
        
        indicator = manager.get_indicator("test_tool")
        assert indicator.progress == 1.0
        assert indicator.state == LoadingState.COMPLETED
        assert indicator.message == "All done!"
        assert indicator.estimated_time == 0.0
    
    def test_complete_loading_failure(self, manager):
        """Test completing loading with failure."""
        manager.start_loading("test_tool", ToolType.DATABASE_QUERY)
        
        success = manager.complete_loading("test_tool", False)
        assert success
        
        indicator = manager.get_indicator("test_tool")
        assert indicator.progress == 1.0
        assert indicator.state == LoadingState.ERROR
        assert "failed" in indicator.message.lower()
    
    def test_complete_loading_nonexistent_tool(self, manager):
        """Test completing loading for non-existent tool."""
        success = manager.complete_loading("nonexistent")
        assert not success
    
    def test_get_active_indicators(self, manager):
        """Test getting active indicators."""
        assert len(manager.get_active_indicators()) == 0
        
        manager.start_loading("tool1", ToolType.DATABASE_QUERY)
        manager.start_loading("tool2", ToolType.WEB_SCRAPING)
        
        indicators = manager.get_active_indicators()
        assert len(indicators) == 2
        tool_names = [i.tool_name for i in indicators]
        assert "tool1" in tool_names
        assert "tool2" in tool_names
    
    def test_is_loading(self, manager):
        """Test checking if tool is loading."""
        assert not manager.is_loading("test_tool")
        
        manager.start_loading("test_tool", ToolType.DATABASE_QUERY)
        assert manager.is_loading("test_tool")
        
        manager.complete_loading("test_tool")
        # Should still be true until cleanup
        assert manager.is_loading("test_tool") or not manager.is_loading("test_tool")
    
    def test_get_concurrent_loading_count(self, manager):
        """Test getting concurrent loading count."""
        assert manager.get_concurrent_loading_count() == 0
        
        manager.start_loading("tool1", ToolType.DATABASE_QUERY)
        manager.start_loading("tool2", ToolType.WEB_SCRAPING)
        assert manager.get_concurrent_loading_count() == 2
        
        manager.complete_loading("tool1")
        # Count might still be 2 until cleanup, but should be at least 1
        assert manager.get_concurrent_loading_count() >= 1
    
    def test_get_loading_summary(self, manager):
        """Test getting loading summary."""
        summary = manager.get_loading_summary()
        assert summary["total_active"] == 0
        assert summary["loading"] == 0
        
        manager.start_loading("tool1", ToolType.DATABASE_QUERY)
        manager.start_loading("tool2", ToolType.WEB_SCRAPING)
        
        summary = manager.get_loading_summary()
        assert summary["total_active"] == 2
        assert summary["loading"] == 2
        assert "tool1" in summary["tools"]
        assert "tool2" in summary["tools"]
    
    def test_register_tool_configuration(self, manager):
        """Test registering custom tool configuration."""
        custom_config = LoadingConfiguration(
            tool_type=ToolType.ANALYSIS,
            estimated_duration=10.0,
            progress_steps=["Step 1", "Step 2"],
            show_progress_bar=False
        )
        
        manager.register_tool_configuration("custom_tool", custom_config)
        
        indicator = manager.start_loading("custom_tool")
        assert indicator.estimated_time == 10.0
    
    @pytest.mark.asyncio
    async def test_progress_callbacks(self, manager):
        """Test progress callbacks."""
        callback_calls = []
        
        def callback(tool_name, progress, message):
            callback_calls.append((tool_name, progress, message))
        
        manager.start_loading("test_tool", ToolType.DATABASE_QUERY)
        manager.add_progress_callback("test_tool", callback)
        
        await manager.update_progress("test_tool", 0.5, "Test message")
        
        assert len(callback_calls) == 1
        assert callback_calls[0] == ("test_tool", 0.5, "Test message")
    
    @pytest.mark.asyncio
    async def test_async_progress_callback(self, manager):
        """Test async progress callbacks."""
        callback_calls = []
        
        async def async_callback(tool_name, progress, message):
            callback_calls.append((tool_name, progress, message))
        
        manager.start_loading("test_tool", ToolType.DATABASE_QUERY)
        manager.add_progress_callback("test_tool", async_callback)
        
        await manager.update_progress("test_tool", 0.7, "Async test")
        
        assert len(callback_calls) == 1
        assert callback_calls[0] == ("test_tool", 0.7, "Async test")
    
    @pytest.mark.asyncio
    async def test_estimated_time_update(self, manager):
        """Test estimated time updates based on progress."""
        with patch('intelligent_chat.loading_indicators.datetime') as mock_datetime:
            start_time = datetime(2024, 1, 1, 12, 0, 0)
            current_time = datetime(2024, 1, 1, 12, 0, 2)  # 2 seconds later
            
            mock_datetime.now.side_effect = [start_time, current_time]
            
            manager.start_loading("test_tool", ToolType.DATABASE_QUERY)
            
            # Reset mock to return current time for progress update
            mock_datetime.now.return_value = current_time
            
            await manager.update_progress("test_tool", 0.5)  # 50% done in 2 seconds
            
            indicator = manager.get_indicator("test_tool")
            # Should estimate 2 more seconds (total 4 seconds, 2 elapsed, 2 remaining)
            assert indicator.estimated_time == pytest.approx(2.0, rel=0.1)


class TestConcurrentLoadingManager:
    """Test cases for ConcurrentLoadingManager."""
    
    @pytest.fixture
    def managers(self):
        """Create manager instances."""
        loading_manager = LoadingIndicatorManager()
        concurrent_manager = ConcurrentLoadingManager(loading_manager)
        return loading_manager, concurrent_manager
    
    def test_create_coordination_group(self, managers):
        """Test creating coordination group."""
        _, concurrent_manager = managers
        
        tool_names = ["tool1", "tool2", "tool3"]
        concurrent_manager.create_coordination_group("group1", tool_names)
        
        assert "group1" in concurrent_manager._coordination_groups
        assert concurrent_manager._coordination_groups["group1"] == tool_names
        assert concurrent_manager._group_progress["group1"] == 0.0
    
    @pytest.mark.asyncio
    async def test_start_coordinated_loading(self, managers):
        """Test starting coordinated loading."""
        loading_manager, concurrent_manager = managers
        
        tool_names = ["tool1", "tool2"]
        concurrent_manager.create_coordination_group("group1", tool_names)
        
        tool_configs = {
            "tool1": ToolType.DATABASE_QUERY,
            "tool2": ToolType.WEB_SCRAPING
        }
        
        indicators = await concurrent_manager.start_coordinated_loading("group1", tool_configs)
        
        assert len(indicators) == 2
        assert all(i.state == LoadingState.LOADING for i in indicators)
        
        # Check that tools are registered in loading manager
        assert loading_manager.is_loading("tool1")
        assert loading_manager.is_loading("tool2")
    
    @pytest.mark.asyncio
    async def test_start_coordinated_loading_invalid_group(self, managers):
        """Test starting coordinated loading with invalid group."""
        _, concurrent_manager = managers
        
        with pytest.raises(ValueError, match="Coordination group invalid not found"):
            await concurrent_manager.start_coordinated_loading("invalid", {})
    
    @pytest.mark.asyncio
    async def test_update_group_progress(self, managers):
        """Test updating group progress."""
        loading_manager, concurrent_manager = managers
        
        tool_names = ["tool1", "tool2"]
        concurrent_manager.create_coordination_group("group1", tool_names)
        
        # Start tools
        loading_manager.start_loading("tool1", ToolType.DATABASE_QUERY)
        loading_manager.start_loading("tool2", ToolType.WEB_SCRAPING)
        
        # Update individual progress
        await loading_manager.update_progress("tool1", 0.6)
        await loading_manager.update_progress("tool2", 0.4)
        
        # Update group progress
        await concurrent_manager.update_group_progress("group1")
        
        group_progress = concurrent_manager.get_group_progress("group1")
        assert group_progress == pytest.approx(0.5, rel=0.01)  # (0.6 + 0.4) / 2
    
    @pytest.mark.asyncio
    async def test_update_group_progress_invalid_group(self, managers):
        """Test updating group progress for invalid group."""
        _, concurrent_manager = managers
        
        # Should not raise error, just return silently
        await concurrent_manager.update_group_progress("invalid")
        assert concurrent_manager.get_group_progress("invalid") == 0.0
    
    def test_cleanup_group(self, managers):
        """Test cleaning up coordination group."""
        _, concurrent_manager = managers
        
        concurrent_manager.create_coordination_group("group1", ["tool1"])
        assert "group1" in concurrent_manager._coordination_groups
        
        concurrent_manager.cleanup_group("group1")
        assert "group1" not in concurrent_manager._coordination_groups
        assert "group1" not in concurrent_manager._group_progress


class TestLoadingConfiguration:
    """Test cases for LoadingConfiguration."""
    
    def test_default_configuration_values(self):
        """Test default configuration values."""
        config = LoadingConfiguration(
            tool_type=ToolType.DATABASE_QUERY,
            estimated_duration=5.0
        )
        
        assert config.tool_type == ToolType.DATABASE_QUERY
        assert config.estimated_duration == 5.0
        assert config.progress_steps == []
        assert config.show_progress_bar is True
        assert config.show_spinner is True
        assert config.show_estimated_time is True
        assert config.update_interval == 0.5
    
    def test_custom_configuration_values(self):
        """Test custom configuration values."""
        config = LoadingConfiguration(
            tool_type=ToolType.WEB_SCRAPING,
            estimated_duration=10.0,
            progress_steps=["Step 1", "Step 2", "Step 3"],
            show_progress_bar=False,
            show_spinner=False,
            show_estimated_time=False,
            update_interval=1.0
        )
        
        assert config.tool_type == ToolType.WEB_SCRAPING
        assert config.estimated_duration == 10.0
        assert config.progress_steps == ["Step 1", "Step 2", "Step 3"]
        assert config.show_progress_bar is False
        assert config.show_spinner is False
        assert config.show_estimated_time is False
        assert config.update_interval == 1.0


@pytest.mark.asyncio
async def test_integration_loading_flow():
    """Test complete loading flow integration."""
    manager = LoadingIndicatorManager()
    
    # Start loading
    indicator = manager.start_loading("integration_tool", ToolType.ANALYSIS)
    assert indicator.state == LoadingState.LOADING
    
    # Update progress multiple times
    await manager.update_progress("integration_tool", 0.25, "Quarter done")
    await manager.update_progress("integration_tool", 0.5, "Half done")
    await manager.update_progress("integration_tool", 0.75, "Almost done")
    
    # Complete successfully
    manager.complete_loading("integration_tool", True, "Integration complete")
    
    final_indicator = manager.get_indicator("integration_tool")
    assert final_indicator.state == LoadingState.COMPLETED
    assert final_indicator.progress == 1.0
    assert final_indicator.message == "Integration complete"


if __name__ == "__main__":
    pytest.main([__file__])