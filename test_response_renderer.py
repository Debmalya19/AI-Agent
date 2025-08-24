"""
Unit tests for ResponseRenderer - Content type detection and basic rendering.
"""

import json
import pytest
from datetime import datetime

from intelligent_chat.response_renderer import ResponseRenderer
from intelligent_chat.models import (
    ContentType, ContentSection, UIState, LoadingIndicator, 
    LoadingState, InteractiveElement, ErrorState, ErrorSeverity
)
from intelligent_chat.exceptions import RenderingError


class TestResponseRenderer:
    """Test suite for ResponseRenderer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = ResponseRenderer()
    
    def test_init(self):
        """Test ResponseRenderer initialization."""
        assert self.renderer is not None
        assert hasattr(self.renderer, '_format_processors')
        assert len(self.renderer._format_processors) == 7  # All content types
    
    # Content Type Detection Tests
    
    def test_detect_plain_text(self):
        """Test detection of plain text content."""
        content = "This is a simple plain text message."
        result = self.renderer.detect_content_type(content)
        assert result == ContentType.PLAIN_TEXT
    
    def test_detect_empty_content(self):
        """Test detection of empty content."""
        assert self.renderer.detect_content_type("") == ContentType.PLAIN_TEXT
        assert self.renderer.detect_content_type("   ") == ContentType.PLAIN_TEXT
        assert self.renderer.detect_content_type(None) == ContentType.PLAIN_TEXT
    
    def test_detect_json_content(self):
        """Test detection of JSON content."""
        json_content = '{"name": "test", "value": 123}'
        result = self.renderer.detect_content_type(json_content)
        assert result == ContentType.JSON
        
        # Complex JSON
        complex_json = '{"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}'
        result = self.renderer.detect_content_type(complex_json)
        assert result == ContentType.JSON
    
    def test_detect_code_block_explicit(self):
        """Test detection of explicit code blocks."""
        code_content = """```python
def hello_world():
    print("Hello, World!")
```"""
        result = self.renderer.detect_content_type(code_content)
        assert result == ContentType.CODE_BLOCK
    
    def test_detect_code_block_implicit(self):
        """Test detection of implicit code blocks."""
        python_code = """def calculate_sum(a, b):
    return a + b

class Calculator:
    def __init__(self):
        self.result = 0"""
        result = self.renderer.detect_content_type(python_code)
        assert result == ContentType.CODE_BLOCK
        
        javascript_code = """function greet(name) {
    return `Hello, ${name}!`;
}"""
        result = self.renderer.detect_content_type(javascript_code)
        assert result == ContentType.CODE_BLOCK
    
    def test_detect_error_message(self):
        """Test detection of error messages."""
        error_content = "Error: File not found at /path/to/file"
        result = self.renderer.detect_content_type(error_content)
        assert result == ContentType.ERROR_MESSAGE
        
        traceback_content = """Traceback (most recent call last):
  File "test.py", line 10, in <module>
    raise ValueError("Something went wrong")
ValueError: Something went wrong"""
        result = self.renderer.detect_content_type(traceback_content)
        assert result == ContentType.ERROR_MESSAGE
    
    def test_detect_table_content(self):
        """Test detection of table content."""
        pipe_table = """| Name | Age | City |
|------|-----|------|
| Alice | 30 | NYC |
| Bob | 25 | LA |"""
        result = self.renderer.detect_content_type(pipe_table)
        assert result == ContentType.TABLE
        
        tab_table = "Name\tAge\tCity\nAlice\t30\tNYC\nBob\t25\tLA"
        result = self.renderer.detect_content_type(tab_table)
        assert result == ContentType.TABLE
    
    def test_detect_markdown_content(self):
        """Test detection of markdown content."""
        markdown_content = """# Main Title

This is a **bold** text and this is *italic*.

- Item 1
- Item 2
- Item 3

[Link to example](https://example.com)"""
        result = self.renderer.detect_content_type(markdown_content)
        assert result == ContentType.MARKDOWN
    
    def test_detect_structured_data(self):
        """Test detection of structured data."""
        structured_content = """name: John Doe
age: 30
email: john@example.com
address: 123 Main St"""
        result = self.renderer.detect_content_type(structured_content)
        assert result == ContentType.STRUCTURED_DATA
    
    # Basic Rendering Tests
    
    def test_render_plain_text(self):
        """Test rendering of plain text."""
        content = "This is plain text."
        metadata = {"source": "test"}
        
        sections = self.renderer.render_response(content, metadata)
        
        assert len(sections) == 1
        assert sections[0].content == content
        assert sections[0].content_type == ContentType.PLAIN_TEXT
        assert sections[0].metadata["source"] == "test"
    
    def test_render_json_content(self):
        """Test rendering of JSON content."""
        content = '{"name": "test", "value": 123}'
        metadata = {}
        
        sections = self.renderer.render_response(content, metadata)
        
        assert len(sections) == 1
        assert sections[0].content_type == ContentType.JSON
        # Should be pretty-printed
        assert "  " in sections[0].content  # Indentation
    
    def test_render_code_block(self):
        """Test rendering of code blocks."""
        content = """```python
def hello():
    print("Hello")
```"""
        metadata = {"language": "python"}
        
        sections = self.renderer.render_response(content, metadata)
        
        assert len(sections) == 1
        assert sections[0].content_type == ContentType.CODE_BLOCK
        # Should remove code block markers
        assert "```" not in sections[0].content
        assert "def hello():" in sections[0].content
    
    def test_render_error_message(self):
        """Test rendering of error messages."""
        content = "Error: Something went wrong"
        metadata = {}
        
        sections = self.renderer.render_response(content, metadata)
        
        assert len(sections) == 1
        assert sections[0].content_type == ContentType.ERROR_MESSAGE
        assert sections[0].metadata["severity"] == "error"
    
    def test_format_structured_data_dict(self):
        """Test formatting of dictionary data."""
        data = {"name": "Alice", "age": 30, "city": "NYC"}
        result = self.renderer.format_structured_data(data)
        
        assert "name: Alice" in result
        assert "age: 30" in result
        assert "city: NYC" in result
    
    def test_format_structured_data_list(self):
        """Test formatting of list data."""
        data = ["apple", "banana", "cherry"]
        result = self.renderer.format_structured_data(data)
        
        assert "1. apple" in result
        assert "2. banana" in result
        assert "3. cherry" in result
    
    def test_format_structured_data_primitives(self):
        """Test formatting of primitive data types."""
        assert self.renderer.format_structured_data(42) == "42"
        assert self.renderer.format_structured_data(3.14) == "3.14"
        assert self.renderer.format_structured_data(True) == "True"
    
    # Rendering Pipeline Tests
    
    def test_create_rendering_pipeline(self):
        """Test the rendering pipeline."""
        content = '{"test": "value"}'
        metadata = {"source": "test"}
        
        sections = self.renderer.create_rendering_pipeline(content, metadata)
        
        assert len(sections) == 1
        assert sections[0].content_type == ContentType.JSON
        assert "processed_at" in sections[0].metadata
        assert "renderer_version" in sections[0].metadata
    
    def test_preprocess_content_code_block(self):
        """Test preprocessing of code block content."""
        content = "\n\n  def hello():\n      print('hi')\n\n"
        result = self.renderer._preprocess_content(content, ContentType.CODE_BLOCK)
        
        # Should remove leading/trailing empty lines
        assert not result.startswith("\n")
        assert not result.endswith("\n\n")
        assert "def hello():" in result
    
    def test_preprocess_content_json(self):
        """Test preprocessing of JSON content."""
        content = '{"name":"test","value":123}'
        result = self.renderer._preprocess_content(content, ContentType.JSON)
        
        # Should be pretty-printed
        assert "  " in result  # Indentation
        assert '"name": "test"' in result
    
    def test_postprocess_sections(self):
        """Test post-processing of sections."""
        sections = [
            ContentSection("content1", ContentType.PLAIN_TEXT, {}, 0),
            ContentSection("content2", ContentType.PLAIN_TEXT, {}, 0)
        ]
        
        result = self.renderer._postprocess_sections(sections, {})
        
        # Should add ordering
        assert result[0].order == 0
        assert result[1].order == 1
        
        # Should add metadata
        for section in result:
            assert "processed_at" in section.metadata
            assert "renderer_version" in section.metadata
    
    # Error Handling Tests
    
    def test_render_response_error_handling(self):
        """Test error handling in render_response."""
        # Mock a scenario that would cause an error by breaking the detect method
        renderer = ResponseRenderer()
        
        def broken_detect(content):
            raise Exception("Detection failed")
        
        # Replace the detect method to force an error
        renderer.detect_content_type = broken_detect
        
        with pytest.raises(RenderingError) as exc_info:
            renderer.render_response("test content", {})
        
        assert "Failed to render response" in str(exc_info.value)
        assert exc_info.value.content == "test content"
    
    def test_rendering_pipeline_fallback(self):
        """Test fallback behavior in rendering pipeline."""
        # Test that the pipeline properly handles errors by re-raising them
        # This is now handled at the render_response level
        renderer = ResponseRenderer()
        
        def broken_detect(content):
            raise Exception("Detection failed")
        
        renderer.detect_content_type = broken_detect
        
        # Should raise the exception (no longer has fallback in pipeline)
        with pytest.raises(Exception) as exc_info:
            renderer.create_rendering_pipeline("test", {})
        
        assert "Detection failed" in str(exc_info.value)
    
    # Content Type Detection Accuracy Tests
    
    def test_content_type_detection_accuracy(self):
        """Test accuracy of content type detection with various inputs."""
        test_cases = [
            ('{"key": "value"}', ContentType.JSON),
            ('def func():\n    return True', ContentType.CODE_BLOCK),  # More code-like
            ('Error: failed to connect', ContentType.ERROR_MESSAGE),
            ('# Title\n\n**Bold** text and *italic*', ContentType.MARKDOWN),  # More markdown patterns
            ('|col1|col2|\n|a|b|', ContentType.TABLE),
            ('key: value\nother: data', ContentType.STRUCTURED_DATA),
            ('Just plain text here', ContentType.PLAIN_TEXT),
        ]
        
        for content, expected_type in test_cases:
            result = self.renderer.detect_content_type(content)
            assert result == expected_type, f"Failed for content: {content[:50]}..."
    
    def test_complex_content_detection(self):
        """Test detection of complex mixed content."""
        # JSON with code-like content
        json_with_code = '{"code": "def hello():\\n    print(\\"hi\\")"}'
        assert self.renderer.detect_content_type(json_with_code) == ContentType.JSON
        
        # Markdown with code blocks (should be detected as markdown due to multiple patterns)
        markdown_with_code = """# Title

This is a **bold** statement and *italic* text.

```python
def hello():
    print("hi")
```

- List item 1
- List item 2

Some more **bold** text."""
        assert self.renderer.detect_content_type(markdown_with_code) == ContentType.MARKDOWN
    
    def test_edge_cases(self):
        """Test edge cases in content detection."""
        # Very short content
        assert self.renderer.detect_content_type("{}") == ContentType.JSON
        assert self.renderer.detect_content_type("[]") == ContentType.JSON
        
        # Content with special characters
        special_content = "Content with émojis 🚀 and unicode ñ"
        assert self.renderer.detect_content_type(special_content) == ContentType.PLAIN_TEXT
        
        # Mixed line endings
        mixed_content = "line1\r\nline2\nline3\r"
        assert self.renderer.detect_content_type(mixed_content) == ContentType.PLAIN_TEXT


if __name__ == "__main__":
    pytest.main([__file__])


class TestUIAdaptationLogic:
    """Test suite for UI adaptation logic in ResponseRenderer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = ResponseRenderer()
    
    # UI State Generation Tests
    
    def test_generate_ui_state_basic(self):
        """Test basic UI state generation."""
        content = "Hello, world!"
        metadata = {}
        
        ui_state = self.renderer.generate_ui_state(content, metadata)
        
        assert isinstance(ui_state, UIState)
        assert len(ui_state.content_sections) == 1
        assert ui_state.content_sections[0].content == content
        assert len(ui_state.loading_indicators) == 0
        assert len(ui_state.error_states) == 0
        assert 'generated_at' in ui_state.metadata
        assert ui_state.metadata['content_length'] == len(content)
        assert ui_state.metadata['has_errors'] is False
        assert ui_state.metadata['has_loading'] is False
    
    def test_generate_ui_state_with_active_tools(self):
        """Test UI state generation with active tools."""
        content = "Processing your request..."
        metadata = {
            'active_tools': [
                {
                    'name': 'web_scraper',
                    'progress': 0.5,
                    'state': 'loading',
                    'message': 'Scraping website...',
                    'estimated_time': 30.0
                },
                {
                    'name': 'data_analyzer',
                    'progress': 0.2,
                    'state': 'processing',
                    'message': 'Analyzing data...'
                }
            ]
        }
        
        ui_state = self.renderer.generate_ui_state(content, metadata)
        
        assert len(ui_state.loading_indicators) == 2
        
        # Check first indicator
        indicator1 = ui_state.loading_indicators[0]
        assert indicator1.tool_name == 'web_scraper'
        assert indicator1.progress == 0.5
        assert indicator1.state == LoadingState.LOADING
        assert indicator1.message == 'Scraping website...'
        assert indicator1.estimated_time == 30.0
        
        # Check second indicator
        indicator2 = ui_state.loading_indicators[1]
        assert indicator2.tool_name == 'data_analyzer'
        assert indicator2.progress == 0.2
        assert indicator2.state == LoadingState.PROCESSING
        assert indicator2.message == 'Analyzing data...'
        
        assert ui_state.metadata['has_loading'] is True
    
    def test_generate_ui_state_with_completed_tools(self):
        """Test UI state generation with completed tools."""
        content = "Analysis complete!"
        metadata = {
            'completed_tools': ['web_scraper', 'data_analyzer']
        }
        
        ui_state = self.renderer.generate_ui_state(content, metadata)
        
        assert len(ui_state.loading_indicators) == 2
        for indicator in ui_state.loading_indicators:
            assert indicator.state == LoadingState.COMPLETED
            assert indicator.progress == 1.0
            assert 'completed successfully' in indicator.message
    
    def test_generate_ui_state_with_failed_tools(self):
        """Test UI state generation with failed tools."""
        content = "Some tools failed to execute"
        metadata = {
            'failed_tools': [
                {
                    'name': 'broken_tool',
                    'error': 'Connection timeout'
                },
                'simple_failed_tool'
            ]
        }
        
        ui_state = self.renderer.generate_ui_state(content, metadata)
        
        assert len(ui_state.loading_indicators) == 2
        
        # Check detailed failure
        indicator1 = ui_state.loading_indicators[0]
        assert indicator1.tool_name == 'broken_tool'
        assert indicator1.state == LoadingState.ERROR
        assert indicator1.progress == 0.0
        assert 'Connection timeout' in indicator1.message
        
        # Check simple failure
        indicator2 = ui_state.loading_indicators[1]
        assert indicator2.tool_name == 'simple_failed_tool'
        assert indicator2.state == LoadingState.ERROR
        assert 'Execution failed' in indicator2.message
    
    # Interactive Elements Tests
    
    def test_generate_interactive_elements_code_block(self):
        """Test interactive elements for code blocks."""
        content = """```python
def hello():
    print("Hello, World!")
```"""
        metadata = {}
        
        ui_state = self.renderer.generate_ui_state(content, metadata)
        
        # Should have copy button for code
        copy_elements = [e for e in ui_state.interactive_elements if e.element_id == 'copy_code']
        assert len(copy_elements) == 1
        
        copy_element = copy_elements[0]
        assert copy_element.element_type == 'button'
        assert copy_element.properties['label'] == 'Copy Code'
        assert 'copy_to_clipboard' in copy_element.actions
    
    def test_generate_interactive_elements_json_data(self):
        """Test interactive elements for JSON data."""
        content = '{"users": [{"name": "Alice", "age": 30}]}'
        metadata = {}
        
        ui_state = self.renderer.generate_ui_state(content, metadata)
        
        # Should have download button for JSON
        download_elements = [e for e in ui_state.interactive_elements if e.element_id == 'download_data']
        assert len(download_elements) == 1
        
        download_element = download_elements[0]
        assert download_element.element_type == 'button'
        assert download_element.properties['label'] == 'Download'
        assert 'download_as_file' in download_element.actions
    
    def test_generate_interactive_elements_error_message(self):
        """Test interactive elements for error messages."""
        content = "Error: Connection failed to database"
        metadata = {}
        
        ui_state = self.renderer.generate_ui_state(content, metadata)
        
        # Should have retry button for errors
        retry_elements = [e for e in ui_state.interactive_elements if e.element_id == 'retry_action']
        assert len(retry_elements) == 1
        
        retry_element = retry_elements[0]
        assert retry_element.element_type == 'button'
        assert retry_element.properties['label'] == 'Retry'
        assert 'retry_operation' in retry_element.actions
    
    def test_generate_interactive_elements_long_content(self):
        """Test interactive elements for long content."""
        content = "A" * 1500  # Long content
        metadata = {}
        
        ui_state = self.renderer.generate_ui_state(content, metadata)
        
        # Should have expand/collapse toggle
        expand_elements = [e for e in ui_state.interactive_elements if e.element_id == 'expand_content']
        assert len(expand_elements) == 1
        
        expand_element = expand_elements[0]
        assert expand_element.element_type == 'toggle'
        assert expand_element.properties['label'] == 'Show More'
        assert expand_element.properties['expanded'] is False
        assert 'toggle_expand' in expand_element.actions
    
    # Error State Generation Tests
    
    def test_generate_error_states_from_metadata(self):
        """Test error state generation from metadata."""
        content = "Processing failed"
        metadata = {
            'errors': [
                {
                    'type': 'connection_error',
                    'message': 'Failed to connect to API',
                    'severity': 'error',
                    'recovery_actions': ['retry', 'check_connection'],
                    'context': {'url': 'https://api.example.com'}
                }
            ]
        }
        
        ui_state = self.renderer.generate_ui_state(content, metadata)
        
        assert len(ui_state.error_states) == 1
        error_state = ui_state.error_states[0]
        
        assert error_state.error_type == 'connection_error'
        assert error_state.message == 'Failed to connect to API'
        assert error_state.severity == ErrorSeverity.ERROR
        assert 'retry' in error_state.recovery_actions
        assert 'check_connection' in error_state.recovery_actions
        assert error_state.context['url'] == 'https://api.example.com'
        
        assert ui_state.metadata['has_errors'] is True
    
    def test_generate_error_states_from_content(self):
        """Test error state generation from error content."""
        content = "Critical error: Database connection timeout"
        metadata = {}
        
        ui_state = self.renderer.generate_ui_state(content, metadata)
        
        assert len(ui_state.error_states) == 1
        error_state = ui_state.error_states[0]
        
        assert error_state.error_type == 'timeout_error'
        assert error_state.message == content
        assert error_state.severity == ErrorSeverity.CRITICAL
        assert 'retry' in error_state.recovery_actions
        assert 'increase_timeout' in error_state.recovery_actions
        assert error_state.context['source'] == 'content_analysis'
    
    def test_extract_error_type(self):
        """Test error type extraction from content."""
        test_cases = [
            ("Connection timeout occurred", "timeout_error"),
            ("Network connection failed", "connection_error"),
            ("Permission denied for user", "permission_error"),
            ("File not found at path", "not_found_error"),
            ("Syntax error in line 5", "syntax_error"),
            ("Validation failed for input", "validation_error"),
            ("Unknown error occurred", "general_error")
        ]
        
        for content, expected_type in test_cases:
            result = self.renderer._extract_error_type(content)
            assert result == expected_type, f"Failed for content: {content}"
    
    def test_determine_error_severity(self):
        """Test error severity determination."""
        test_cases = [
            ("Critical system failure", ErrorSeverity.CRITICAL),
            ("Fatal error occurred", ErrorSeverity.CRITICAL),
            ("Error: Connection failed", ErrorSeverity.ERROR),
            ("Exception in processing", ErrorSeverity.ERROR),
            ("Warning: Low disk space", ErrorSeverity.WARNING),
            ("Info: Process completed", ErrorSeverity.INFO)
        ]
        
        for content, expected_severity in test_cases:
            result = self.renderer._determine_error_severity(content)
            assert result == expected_severity, f"Failed for content: {content}"
    
    def test_suggest_recovery_actions(self):
        """Test recovery action suggestions."""
        test_cases = [
            ("timeout_error", ["retry", "increase_timeout"]),
            ("connection_error", ["retry", "check_connection"]),
            ("permission_error", ["check_permissions", "contact_admin"]),
            ("not_found_error", ["check_path", "verify_resource"]),
            ("syntax_error", ["fix_syntax", "validate_input"]),
            ("validation_error", ["correct_input", "check_format"]),
            ("general_error", ["retry", "contact_support"])
        ]
        
        for error_type, expected_actions in test_cases:
            result = self.renderer._suggest_recovery_actions("", error_type)
            for action in expected_actions:
                assert action in result, f"Missing action {action} for {error_type}"
    
    # Tool Progress Tracking Tests
    
    def test_track_tool_progress_loading(self):
        """Test tool progress tracking for loading state."""
        indicator = self.renderer.track_tool_progress("test_tool", 0.5, "Processing data...")
        
        assert indicator.tool_name == "test_tool"
        assert indicator.state == LoadingState.LOADING
        assert indicator.progress == 0.5
        assert indicator.message == "Processing data..."
    
    def test_track_tool_progress_completed(self):
        """Test tool progress tracking for completed state."""
        indicator = self.renderer.track_tool_progress("test_tool", 1.0)
        
        assert indicator.tool_name == "test_tool"
        assert indicator.state == LoadingState.COMPLETED
        assert indicator.progress == 1.0
        assert "Processing test_tool" in indicator.message
    
    def test_track_tool_progress_error(self):
        """Test tool progress tracking for error state."""
        indicator = self.renderer.track_tool_progress("test_tool", -1.0, "Failed to execute")
        
        assert indicator.tool_name == "test_tool"
        assert indicator.state == LoadingState.ERROR
        assert indicator.progress == 0.0  # Clamped to 0
        assert indicator.message == "Failed to execute"
    
    def test_track_tool_progress_bounds(self):
        """Test tool progress tracking with out-of-bounds values."""
        # Test upper bound
        indicator = self.renderer.track_tool_progress("test_tool", 1.5)
        assert indicator.progress == 1.0
        
        # Test lower bound
        indicator = self.renderer.track_tool_progress("test_tool", -0.5)
        assert indicator.progress == 0.0
    
    # Error Recovery UI Tests
    
    def test_create_error_recovery_ui_connection_error(self):
        """Test error recovery UI for connection errors."""
        error = ConnectionError("Failed to connect to server")
        context = {"server": "api.example.com", "port": 443}
        
        error_state = self.renderer.create_error_recovery_ui(error, context)
        
        assert error_state.error_type == "connectionerror"
        assert error_state.message == "Failed to connect to server"
        assert error_state.severity == ErrorSeverity.WARNING
        assert "retry" in error_state.recovery_actions
        assert "check_connection" in error_state.recovery_actions
        assert error_state.context == context
    
    def test_create_error_recovery_ui_permission_error(self):
        """Test error recovery UI for permission errors."""
        error = PermissionError("Access denied")
        context = {"resource": "/protected/file.txt"}
        
        error_state = self.renderer.create_error_recovery_ui(error, context)
        
        assert error_state.error_type == "permissionerror"
        assert error_state.severity == ErrorSeverity.ERROR
        assert "check_permissions" in error_state.recovery_actions
        assert "contact_admin" in error_state.recovery_actions
    
    def test_create_error_recovery_ui_value_error(self):
        """Test error recovery UI for value errors."""
        error = ValueError("Invalid input format")
        context = {"input": "invalid_data"}
        
        error_state = self.renderer.create_error_recovery_ui(error, context)
        
        assert error_state.error_type == "valueerror"
        assert error_state.severity == ErrorSeverity.ERROR
        assert "correct_input" in error_state.recovery_actions
        assert "validate_data" in error_state.recovery_actions
    
    def test_create_error_recovery_ui_generic_error(self):
        """Test error recovery UI for generic errors."""
        error = RuntimeError("Something went wrong")
        context = {}
        
        error_state = self.renderer.create_error_recovery_ui(error, context)
        
        assert error_state.error_type == "runtimeerror"
        assert error_state.severity == ErrorSeverity.ERROR
        assert "retry" in error_state.recovery_actions
        assert "contact_support" in error_state.recovery_actions
    
    # UI State Transitions Tests
    
    def test_ui_state_transitions_loading_to_complete(self):
        """Test UI state transitions from loading to complete."""
        # Initial loading state
        loading_metadata = {
            'active_tools': [
                {'name': 'processor', 'progress': 0.3, 'state': 'loading'}
            ]
        }
        
        loading_ui = self.renderer.generate_ui_state("Processing...", loading_metadata)
        assert len(loading_ui.loading_indicators) == 1
        assert loading_ui.loading_indicators[0].state == LoadingState.LOADING
        assert loading_ui.metadata['has_loading'] is True
        
        # Completed state
        complete_metadata = {
            'completed_tools': ['processor']
        }
        
        complete_ui = self.renderer.generate_ui_state("Processing complete!", complete_metadata)
        assert len(complete_ui.loading_indicators) == 1
        assert complete_ui.loading_indicators[0].state == LoadingState.COMPLETED
        assert complete_ui.metadata['has_loading'] is True
    
    def test_ui_state_transitions_loading_to_error(self):
        """Test UI state transitions from loading to error."""
        # Initial loading state
        loading_metadata = {
            'active_tools': [
                {'name': 'processor', 'progress': 0.7, 'state': 'loading'}
            ]
        }
        
        loading_ui = self.renderer.generate_ui_state("Processing...", loading_metadata)
        assert loading_ui.loading_indicators[0].state == LoadingState.LOADING
        
        # Error state
        error_metadata = {
            'failed_tools': [
                {'name': 'processor', 'error': 'Timeout occurred'}
            ],
            'errors': [
                {'type': 'timeout_error', 'message': 'Processing timeout'}
            ]
        }
        
        error_ui = self.renderer.generate_ui_state("Processing failed", error_metadata)
        assert len(error_ui.loading_indicators) == 1
        assert error_ui.loading_indicators[0].state == LoadingState.ERROR
        assert len(error_ui.error_states) == 1
        assert error_ui.metadata['has_errors'] is True
    
    def test_complex_ui_state_multiple_elements(self):
        """Test complex UI state with multiple elements."""
        content = """```python
# This is a long code example that demonstrates
# multiple features and should trigger various
# UI elements including copy button and expand toggle
def complex_function():
    data = {"key": "value"}
    return process_data(data)
""" + "# " + "A" * 1000  # Make it long enough for expand toggle
        
        metadata = {
            'active_tools': [
                {'name': 'code_analyzer', 'progress': 0.8, 'state': 'processing'}
            ],
            'completed_tools': ['syntax_checker'],
            'errors': [
                {'type': 'warning', 'message': 'Deprecated function used', 'severity': 'warning'}
            ]
        }
        
        ui_state = self.renderer.generate_ui_state(content, metadata)
        
        # Should have content sections
        assert len(ui_state.content_sections) == 1
        assert ui_state.content_sections[0].content_type == ContentType.CODE_BLOCK
        
        # Should have loading indicators
        assert len(ui_state.loading_indicators) == 2  # One active, one completed
        
        # Should have interactive elements (copy + expand)
        element_ids = [e.element_id for e in ui_state.interactive_elements]
        assert 'copy_code' in element_ids
        assert 'expand_content' in element_ids
        
        # Should have error states
        assert len(ui_state.error_states) == 1
        assert ui_state.error_states[0].severity == ErrorSeverity.WARNING
        
        # Should have correct metadata flags
        assert ui_state.metadata['has_loading'] is True
        assert ui_state.metadata['has_errors'] is True
        assert ui_state.metadata['content_length'] > 1000


if __name__ == "__main__":
    pytest.main([__file__])