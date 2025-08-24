"""
Integration tests for response rendering and UI state transitions.

Tests the complete flow from raw response content through rendering
to final UI state generation.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch
from typing import List, Dict, Any

# Import intelligent chat components
from intelligent_chat.response_renderer import ResponseRenderer
from intelligent_chat.chat_manager import ChatManager
from intelligent_chat.models import (
    ChatResponse, ContentType, ContentSection, UIState,
    LoadingIndicator, LoadingState, ErrorState, ErrorSeverity
)


class TestResponseRenderingIntegration:
    """Test response rendering integration with chat flow."""
    
    @pytest.fixture
    def response_renderer(self):
        """Create ResponseRenderer for testing."""
        return ResponseRenderer()
    
    @pytest.fixture
    def chat_manager_with_renderer(self, response_renderer):
        """Create ChatManager with ResponseRenderer."""
        return ChatManager(
            response_renderer=response_renderer,
            auto_create_context_engine=False
        )
    
    def test_plain_text_rendering(self, response_renderer):
        """Test rendering of plain text responses."""
        content = "This is a simple text response."
        metadata = {"confidence": 0.8}
        
        sections = response_renderer.render_response(content, metadata)
        
        assert len(sections) == 1
        assert sections[0].content_type == ContentType.PLAIN_TEXT
        assert sections[0].content == content
        assert sections[0].metadata["confidence"] == 0.8
    
    def test_code_block_rendering(self, response_renderer):
        """Test rendering of code block responses."""
        content = """Here's a Python function:

```python
def hello_world():
    print("Hello, World!")
    return "success"
```

This function prints a greeting."""
        
        sections = response_renderer.render_response(content, {})
        
        # Should detect and separate code blocks
        assert len(sections) >= 2
        
        # Find the code section
        code_sections = [s for s in sections if s.content_type == ContentType.CODE_BLOCK]
        assert len(code_sections) == 1
        
        code_section = code_sections[0]
        assert "def hello_world():" in code_section.content
        assert code_section.metadata.get("language") == "python"
    
    def test_structured_data_rendering(self, response_renderer):
        """Test rendering of structured data responses."""
        # JSON data
        json_content = '{"name": "John", "age": 30, "city": "New York"}'
        
        sections = response_renderer.render_response(json_content, {})
        
        assert len(sections) == 1
        assert sections[0].content_type == ContentType.JSON
        
        # Verify JSON is properly formatted
        parsed_data = json.loads(sections[0].content)
        assert parsed_data["name"] == "John"
        assert parsed_data["age"] == 30
    
    def test_mixed_content_rendering(self, response_renderer):
        """Test rendering of mixed content types."""
        content = """Here's your data analysis:

The results show:
- Total users: 1,250
- Active users: 890
- Conversion rate: 71.2%

```python
# Code to calculate conversion rate
conversion_rate = (active_users / total_users) * 100
print(f"Conversion rate: {conversion_rate:.1f}%")
```

Additional data:
{"users": 1250, "active": 890, "rate": 0.712}"""
        
        sections = response_renderer.render_response(content, {})
        
        # Should have multiple sections for different content types
        assert len(sections) >= 3
        
        content_types = [s.content_type for s in sections]
        assert ContentType.PLAIN_TEXT in content_types
        assert ContentType.CODE_BLOCK in content_types
        assert ContentType.JSON in content_types
    
    def test_error_content_rendering(self, response_renderer):
        """Test rendering of error content."""
        error_content = "Error: Failed to connect to database. Please try again later."
        
        sections = response_renderer.render_response(error_content, {"error": True})
        
        assert len(sections) == 1
        assert sections[0].content_type == ContentType.ERROR_MESSAGE
        assert "Error:" in sections[0].content
        assert sections[0].metadata.get("error") is True
    
    def test_markdown_rendering(self, response_renderer):
        """Test rendering of markdown content."""
        markdown_content = """# Weather Report

## Current Conditions
- **Temperature**: 22°C
- **Humidity**: 65%
- **Wind**: 10 km/h

### Forecast
Tomorrow will be *partly cloudy* with a chance of rain."""
        
        sections = response_renderer.render_response(markdown_content, {})
        
        assert len(sections) == 1
        assert sections[0].content_type == ContentType.MARKDOWN
        assert "# Weather Report" in sections[0].content
        assert sections[0].metadata.get("has_headers") is True
    
    @pytest.mark.asyncio
    async def test_end_to_end_rendering_flow(self, chat_manager_with_renderer):
        """Test complete flow from message to rendered response."""
        # Mock tool that returns structured data
        with patch.object(chat_manager_with_renderer, 'tool_orchestrator') as mock_orchestrator:
            mock_orchestrator.select_tools.return_value = []
            mock_orchestrator.execute_tools.return_value = []
            
            response = await chat_manager_with_renderer.process_message(
                "Show me user statistics",
                "user123",
                "session456"
            )
            
            # Verify response was processed
            assert response is not None
            assert response.content_type in [ContentType.PLAIN_TEXT, ContentType.MARKDOWN]
            
            # Test UI state generation
            ui_state = chat_manager_with_renderer.update_ui_state(response)
            assert isinstance(ui_state, UIState)
    
    def test_content_type_detection_accuracy(self, response_renderer):
        """Test accuracy of content type detection."""
        test_cases = [
            ("Simple text", ContentType.PLAIN_TEXT),
            ("```python\nprint('hello')\n```", ContentType.CODE_BLOCK),
            ('{"key": "value"}', ContentType.JSON),
            ("# Header\n**bold text**", ContentType.MARKDOWN),
            ("Error: Something went wrong", ContentType.ERROR_MESSAGE),
        ]
        
        for content, expected_type in test_cases:
            detected_type = response_renderer.detect_content_type(content)
            assert detected_type == expected_type, f"Failed for content: {content}"
    
    def test_format_structured_data(self, response_renderer):
        """Test structured data formatting."""
        # Test dictionary formatting
        data_dict = {"name": "Alice", "score": 95, "active": True}
        formatted = response_renderer.format_structured_data(data_dict)
        
        assert isinstance(formatted, str)
        assert "name" in formatted
        assert "Alice" in formatted
        
        # Test list formatting
        data_list = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
        formatted_list = response_renderer.format_structured_data(data_list)
        
        assert isinstance(formatted_list, str)
        assert "Item 1" in formatted_list
        assert "Item 2" in formatted_list
    
    def test_rendering_with_metadata_preservation(self, response_renderer):
        """Test that metadata is preserved through rendering."""
        content = "Test content"
        metadata = {
            "source": "test_tool",
            "confidence": 0.9,
            "execution_time": 1.5,
            "custom_field": "custom_value"
        }
        
        sections = response_renderer.render_response(content, metadata)
        
        assert len(sections) == 1
        section = sections[0]
        
        # Verify metadata preservation
        assert section.metadata["source"] == "test_tool"
        assert section.metadata["confidence"] == 0.9
        assert section.metadata["execution_time"] == 1.5
        assert section.metadata["custom_field"] == "custom_value"
    
    def test_large_content_handling(self, response_renderer):
        """Test handling of large content."""
        # Create large content
        large_content = "This is a test sentence. " * 1000  # ~25KB
        
        sections = response_renderer.render_response(large_content, {})
        
        assert len(sections) >= 1
        
        # Verify content is handled properly (not truncated unexpectedly)
        total_content_length = sum(len(s.content) for s in sections)
        assert total_content_length >= len(large_content) * 0.9  # Allow some processing overhead
    
    def test_special_characters_handling(self, response_renderer):
        """Test handling of special characters and encoding."""
        special_content = """Content with special characters:
        - Unicode: 🚀 ✨ 🎉
        - Accents: café, naïve, résumé
        - Symbols: ©️ ®️ ™️
        - Math: ∑ ∆ π ∞
        - Quotes: "smart quotes" 'apostrophe's'"""
        
        sections = response_renderer.render_response(special_content, {})
        
        assert len(sections) == 1
        assert "🚀" in sections[0].content
        assert "café" in sections[0].content
        assert "©️" in sections[0].content
        assert "∑" in sections[0].content


class TestUIStateTransitions:
    """Test UI state transitions during conversation flow."""
    
    @pytest.fixture
    def chat_manager(self):
        """Create ChatManager for UI state testing."""
        return ChatManager(auto_create_context_engine=False)
    
    def test_loading_state_generation(self, chat_manager):
        """Test generation of loading states."""
        # Create response with tools
        response = ChatResponse(
            content="Processing your request...",
            content_type=ContentType.PLAIN_TEXT,
            tools_used=["weather_tool", "location_tool"],
            execution_time=2.5
        )
        
        ui_state = chat_manager.update_ui_state(response)
        
        # Should have loading indicators for each tool
        assert len(ui_state.loading_indicators) == 2
        
        tool_names = [indicator.tool_name for indicator in ui_state.loading_indicators]
        assert "weather_tool" in tool_names
        assert "location_tool" in tool_names
        
        # All should be completed
        for indicator in ui_state.loading_indicators:
            assert indicator.state == LoadingState.COMPLETED
            assert indicator.progress == 1.0
    
    def test_error_state_generation(self, chat_manager):
        """Test generation of error states."""
        # Create error response
        error_response = ChatResponse(
            content="Failed to process your request due to network error.",
            content_type=ContentType.ERROR_MESSAGE,
            execution_time=0.5,
            ui_hints={"error_type": "network_error"}
        )
        
        ui_state = chat_manager.update_ui_state(error_response)
        
        # Should have error state
        assert len(ui_state.error_states) == 1
        
        error_state = ui_state.error_states[0]
        assert error_state.error_type == "processing_error"
        assert error_state.severity == ErrorSeverity.ERROR
        assert "retry" in error_state.recovery_actions
    
    def test_mixed_state_generation(self, chat_manager):
        """Test generation of mixed UI states."""
        # Create response with both successful and failed elements
        response = ChatResponse(
            content="Partial results available. Some tools failed.",
            content_type=ContentType.PLAIN_TEXT,
            tools_used=["successful_tool"],
            execution_time=3.0,
            ui_hints={"partial_failure": True}
        )
        
        ui_state = chat_manager.update_ui_state(response)
        
        # Should have both loading indicators and potentially warnings
        assert len(ui_state.loading_indicators) >= 1
        
        # Verify successful tool indicator
        successful_indicators = [
            ind for ind in ui_state.loading_indicators 
            if ind.tool_name == "successful_tool"
        ]
        assert len(successful_indicators) == 1
        assert successful_indicators[0].state == LoadingState.COMPLETED
    
    def test_ui_state_metadata(self, chat_manager):
        """Test UI state metadata generation."""
        response = ChatResponse(
            content="Test response",
            content_type=ContentType.PLAIN_TEXT,
            tools_used=["test_tool"],
            context_used=["context1", "context2"],
            confidence_score=0.85,
            execution_time=1.2,
            ui_hints={
                "session_id": "test_session",
                "context_count": 2,
                "tools_count": 1
            }
        )
        
        ui_state = chat_manager.update_ui_state(response)
        
        # Verify metadata is included
        assert "response_metadata" in ui_state.metadata or len(ui_state.loading_indicators) > 0
        
        # Verify loading indicator has proper metadata
        if ui_state.loading_indicators:
            indicator = ui_state.loading_indicators[0]
            assert indicator.tool_name == "test_tool"
            assert indicator.state == LoadingState.COMPLETED


class TestRenderingPerformance:
    """Test rendering performance under various conditions."""
    
    @pytest.fixture
    def response_renderer(self):
        """Create ResponseRenderer for performance testing."""
        return ResponseRenderer()
    
    def test_rendering_performance_simple_content(self, response_renderer):
        """Test rendering performance for simple content."""
        import time
        
        content = "Simple text content for performance testing."
        
        # Measure rendering time
        start_time = time.time()
        for _ in range(100):
            sections = response_renderer.render_response(content, {})
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100
        
        # Should be very fast for simple content
        assert avg_time < 0.01  # Less than 10ms per render
        assert len(sections) == 1
    
    def test_rendering_performance_complex_content(self, response_renderer):
        """Test rendering performance for complex content."""
        import time
        
        # Create complex content with multiple types
        complex_content = """# Analysis Report

## Summary
Here are the key findings from our analysis:

```python
def analyze_data(data):
    results = {}
    for item in data:
        results[item.id] = item.value * 2
    return results
```

## Data
{"total_items": 1500, "processed": 1450, "errors": 50}

## Recommendations
- Improve error handling
- Optimize processing speed
- Add monitoring"""
        
        # Measure rendering time
        start_time = time.time()
        for _ in range(50):
            sections = response_renderer.render_response(complex_content, {})
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 50
        
        # Should still be reasonably fast
        assert avg_time < 0.05  # Less than 50ms per render
        assert len(sections) >= 3  # Multiple content types
    
    def test_concurrent_rendering_performance(self, response_renderer):
        """Test concurrent rendering performance."""
        import asyncio
        import time
        
        contents = [
            f"Content {i} with some text and data." for i in range(20)
        ]
        
        async def render_content(content):
            """Async wrapper for rendering."""
            return response_renderer.render_response(content, {})
        
        async def concurrent_rendering():
            tasks = [render_content(content) for content in contents]
            return await asyncio.gather(*tasks)
        
        # Measure concurrent rendering time
        start_time = time.time()
        results = asyncio.run(concurrent_rendering())
        end_time = time.time()
        
        total_time = end_time - start_time
        
        # Should handle concurrent rendering efficiently
        assert total_time < 1.0  # Less than 1 second for 20 concurrent renders
        assert len(results) == 20
        assert all(len(result) >= 1 for result in results)


if __name__ == "__main__":
    # Run response rendering integration tests
    pytest.main([
        __file__,
        "-v", "--tb=short"
    ])