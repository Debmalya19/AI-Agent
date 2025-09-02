"""
ResponseRenderer - Dynamic response formatting based on content type.
"""

import json
import re
from datetime import datetime
from typing import Dict, Any, List

from .models import (
    BaseResponseRenderer,
    ContentSection,
    ContentType,
    UIState,
    LoadingIndicator,
    LoadingState,
    InteractiveElement,
    ErrorState,
    ErrorSeverity
)
from .exceptions import RenderingError


class ResponseRenderer(BaseResponseRenderer):
    """
    Dynamic response formatting based on content type.
    
    Detects content types and formats responses appropriately for UI display.
    """
    
    def __init__(self):
        """Initialize ResponseRenderer with format processors."""
        self._format_processors = {
            ContentType.PLAIN_TEXT: self._format_plain_text,
            ContentType.CODE_BLOCK: self._format_code_block,
            ContentType.STRUCTURED_DATA: self._format_structured_data,
            ContentType.ERROR_MESSAGE: self._format_error_message,
            ContentType.MARKDOWN: self._format_markdown,
            ContentType.JSON: self._format_json,
            ContentType.TABLE: self._format_table
        }
    
    def render_response(self, content: str, metadata: Dict[str, Any]) -> List[ContentSection]:
        """
        Render response content into formatted sections using the rendering pipeline.
        
        Args:
            content: Raw content to render
            metadata: Additional metadata for rendering
            
        Returns:
            List of formatted content sections
            
        Raises:
            RenderingError: If rendering fails
        """
        try:
            # Use the rendering pipeline for better processing
            sections = self.create_rendering_pipeline(content, metadata)
            return sections
            
        except Exception as e:
            # Get content type for error context
            try:
                content_type = self.detect_content_type(content)
                content_type_value = content_type.value
            except Exception:
                content_type_value = None
            
            raise RenderingError(
                f"Failed to render response: {str(e)}",
                content=content,
                content_type=content_type_value,
                context={"metadata": metadata, "error": str(e)}
            )
    
    def detect_content_type(self, content: str) -> ContentType:
        """
        Detect content type based on content analysis with improved accuracy.
        
        Args:
            content: Content to analyze
            
        Returns:
            Detected content type
        """
        if not content or not content.strip():
            return ContentType.PLAIN_TEXT
        
        content = content.strip()
        
        # Priority order for detection (most specific first)
        
        # Check for JSON (high confidence)
        if self._is_json(content):
            return ContentType.JSON
        
        # Check for error patterns (high confidence)
        if self._is_error_message(content):
            return ContentType.ERROR_MESSAGE
        
        # Check for table format (high confidence)
        if self._is_table(content):
            return ContentType.TABLE
        
        # Check for markdown vs code blocks (need special handling)
        is_markdown = self._is_markdown(content)
        is_code = self._is_code_block(content)
        
        if is_markdown and is_code:
            # If both, prefer markdown if it has more markdown patterns
            markdown_score = self._count_markdown_patterns(content)
            if markdown_score >= 3:  # Strong markdown indicators
                return ContentType.MARKDOWN
            else:
                return ContentType.CODE_BLOCK
        elif is_markdown:
            return ContentType.MARKDOWN
        elif is_code:
            return ContentType.CODE_BLOCK
        
        # Check for structured data patterns (low confidence)
        if self._is_structured_data(content):
            return ContentType.STRUCTURED_DATA
        
        # Default to plain text
        return ContentType.PLAIN_TEXT
    
    def format_structured_data(self, data: Any) -> str:
        """
        Format structured data for display.
        
        Args:
            data: Data to format
            
        Returns:
            Formatted string representation
        """
        try:
            if isinstance(data, dict):
                return self._format_dict(data)
            elif isinstance(data, list):
                return self._format_list(data)
            elif isinstance(data, (int, float, bool)):
                return str(data)
            else:
                return str(data)
        except Exception:
            return str(data)
    
    def create_rendering_pipeline(self, content: str, metadata: Dict[str, Any]) -> List[ContentSection]:
        """
        Create a rendering pipeline that processes content through multiple stages.
        
        Args:
            content: Content to process
            metadata: Additional metadata
            
        Returns:
            List of processed content sections
        """
        try:
            # Stage 1: Content type detection
            content_type = self.detect_content_type(content)
            
            # Stage 2: Pre-processing
            processed_content = self._preprocess_content(content, content_type)
            
            # Stage 3: Format processing
            sections = self._apply_format_processor(processed_content, content_type, metadata)
            
            # Stage 4: Post-processing
            final_sections = self._postprocess_sections(sections, metadata)
            
            return final_sections
            
        except Exception as e:
            # Re-raise the exception to be caught by render_response
            raise e
    
    def generate_ui_state(self, content: str, metadata: Dict[str, Any]) -> UIState:
        """
        Generate UI state based on response content and metadata.
        
        Args:
            content: Response content
            metadata: Response metadata including tool execution info
            
        Returns:
            UIState with appropriate indicators and elements
        """
        ui_state = UIState()
        
        # Generate content sections
        ui_state.content_sections = self.render_response(content, metadata)
        
        # Generate loading indicators based on tool execution
        ui_state.loading_indicators = self._generate_loading_indicators(metadata)
        
        # Generate interactive elements based on content type
        ui_state.interactive_elements = self._generate_interactive_elements(content, metadata)
        
        # Generate error states if present
        ui_state.error_states = self._generate_error_states(content, metadata)
        
        # Add global metadata
        ui_state.metadata = {
            'generated_at': datetime.now().isoformat(),
            'content_length': len(content),
            'has_errors': len(ui_state.error_states) > 0,
            'has_loading': len(ui_state.loading_indicators) > 0
        }
        
        return ui_state
    
    def _generate_loading_indicators(self, metadata: Dict[str, Any]) -> List[LoadingIndicator]:
        """Generate loading indicators based on tool execution metadata."""
        indicators = []
        
        # Check for active tools
        active_tools = metadata.get('active_tools', [])
        for tool_info in active_tools:
            if isinstance(tool_info, dict):
                tool_name = tool_info.get('name', 'Unknown Tool')
                progress = tool_info.get('progress', 0.0)
                state = LoadingState(tool_info.get('state', 'loading'))
                message = tool_info.get('message', f'Executing {tool_name}...')
                estimated_time = tool_info.get('estimated_time')
                
                indicators.append(LoadingIndicator(
                    tool_name=tool_name,
                    state=state,
                    progress=progress,
                    message=message,
                    estimated_time=estimated_time
                ))
        
        # Check for completed tools
        completed_tools = metadata.get('completed_tools', [])
        for tool_name in completed_tools:
            indicators.append(LoadingIndicator(
                tool_name=tool_name,
                state=LoadingState.COMPLETED,
                progress=1.0,
                message=f'{tool_name} completed successfully'
            ))
        
        # Check for failed tools
        failed_tools = metadata.get('failed_tools', [])
        for tool_info in failed_tools:
            if isinstance(tool_info, dict):
                tool_name = tool_info.get('name', 'Unknown Tool')
                error_msg = tool_info.get('error', 'Execution failed')
            else:
                tool_name = str(tool_info)
                error_msg = 'Execution failed'
            
            indicators.append(LoadingIndicator(
                tool_name=tool_name,
                state=LoadingState.ERROR,
                progress=0.0,
                message=f'{tool_name}: {error_msg}'
            ))
        
        return indicators
    
    def _generate_interactive_elements(self, content: str, metadata: Dict[str, Any]) -> List[InteractiveElement]:
        """Generate interactive elements based on content and metadata."""
        elements = []
        content_type = self.detect_content_type(content)
        
        # Add copy button for code blocks
        if content_type == ContentType.CODE_BLOCK:
            elements.append(InteractiveElement(
                element_type='button',
                element_id='copy_code',
                properties={
                    'label': 'Copy Code',
                    'icon': 'copy',
                    'tooltip': 'Copy code to clipboard'
                },
                actions=['copy_to_clipboard']
            ))
        
        # Add download button for structured data
        if content_type in [ContentType.JSON, ContentType.TABLE, ContentType.STRUCTURED_DATA]:
            elements.append(InteractiveElement(
                element_type='button',
                element_id='download_data',
                properties={
                    'label': 'Download',
                    'icon': 'download',
                    'tooltip': 'Download data as file'
                },
                actions=['download_as_file']
            ))
        
        # Add retry button for error states
        if content_type == ContentType.ERROR_MESSAGE:
            elements.append(InteractiveElement(
                element_type='button',
                element_id='retry_action',
                properties={
                    'label': 'Retry',
                    'icon': 'refresh',
                    'tooltip': 'Retry the failed operation'
                },
                actions=['retry_operation']
            ))
        
        # Add expand/collapse for long content
        if len(content) > 1000:
            elements.append(InteractiveElement(
                element_type='toggle',
                element_id='expand_content',
                properties={
                    'label': 'Show More',
                    'expanded': False,
                    'preview_length': 500
                },
                actions=['toggle_expand']
            ))
        
        return elements
    
    def _generate_error_states(self, content: str, metadata: Dict[str, Any]) -> List[ErrorState]:
        """Generate error states based on content and metadata."""
        error_states = []
        
        # Check for explicit errors in metadata
        errors = metadata.get('errors', [])
        for error_info in errors:
            if isinstance(error_info, dict):
                error_type = error_info.get('type', 'unknown_error')
                message = error_info.get('message', 'An error occurred')
                severity = ErrorSeverity(error_info.get('severity', 'error'))
                recovery_actions = error_info.get('recovery_actions', [])
                context = error_info.get('context', {})
            else:
                error_type = 'general_error'
                message = str(error_info)
                severity = ErrorSeverity.ERROR
                recovery_actions = ['retry']
                context = {}
            
            error_states.append(ErrorState(
                error_type=error_type,
                message=message,
                severity=severity,
                recovery_actions=recovery_actions,
                context=context
            ))
        
        # Check if content itself indicates an error
        if self.detect_content_type(content) == ContentType.ERROR_MESSAGE:
            # Parse error information from content
            error_type = self._extract_error_type(content)
            severity = self._determine_error_severity(content)
            recovery_actions = self._suggest_recovery_actions(content, error_type)
            
            error_states.append(ErrorState(
                error_type=error_type,
                message=content,
                severity=severity,
                recovery_actions=recovery_actions,
                context={'source': 'content_analysis'}
            ))
        
        return error_states
    
    def _extract_error_type(self, content: str) -> str:
        """Extract error type from error content."""
        content_lower = content.lower()
        
        if 'timeout' in content_lower:
            return 'timeout_error'
        elif 'connection' in content_lower or 'network' in content_lower:
            return 'connection_error'
        elif 'permission' in content_lower or 'access' in content_lower:
            return 'permission_error'
        elif 'not found' in content_lower or '404' in content:
            return 'not_found_error'
        elif 'syntax' in content_lower:
            return 'syntax_error'
        elif 'validation' in content_lower:
            return 'validation_error'
        else:
            return 'general_error'
    
    def _determine_error_severity(self, content: str) -> ErrorSeverity:
        """Determine error severity from content."""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['critical', 'fatal', 'severe']):
            return ErrorSeverity.CRITICAL
        elif any(word in content_lower for word in ['error', 'failed', 'exception']):
            return ErrorSeverity.ERROR
        elif any(word in content_lower for word in ['warning', 'warn']):
            return ErrorSeverity.WARNING
        else:
            return ErrorSeverity.INFO
    
    def _suggest_recovery_actions(self, content: str, error_type: str) -> List[str]:
        """Suggest recovery actions based on error type and content."""
        actions = []
        
        if error_type == 'timeout_error':
            actions.extend(['retry', 'increase_timeout'])
        elif error_type == 'connection_error':
            actions.extend(['retry', 'check_connection'])
        elif error_type == 'permission_error':
            actions.extend(['check_permissions', 'contact_admin'])
        elif error_type == 'not_found_error':
            actions.extend(['check_path', 'verify_resource'])
        elif error_type == 'syntax_error':
            actions.extend(['fix_syntax', 'validate_input'])
        elif error_type == 'validation_error':
            actions.extend(['correct_input', 'check_format'])
        else:
            actions.extend(['retry', 'contact_support'])
        
        return actions
    
    def track_tool_progress(self, tool_name: str, progress: float, message: str = "") -> LoadingIndicator:
        """
        Create a loading indicator for tool progress tracking.
        
        Args:
            tool_name: Name of the tool being executed
            progress: Progress value between 0.0 and 1.0
            message: Optional progress message
            
        Returns:
            LoadingIndicator for the tool
        """
        state = LoadingState.LOADING
        if progress >= 1.0:
            state = LoadingState.COMPLETED
        elif progress < 0:
            state = LoadingState.ERROR
        
        return LoadingIndicator(
            tool_name=tool_name,
            state=state,
            progress=max(0.0, min(1.0, progress)),
            message=message or f"Processing {tool_name}..."
        )
    
    def create_error_recovery_ui(self, error: Exception, context: Dict[str, Any]) -> ErrorState:
        """
        Create an error state with recovery options.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            ErrorState with recovery options
        """
        error_type = type(error).__name__.lower()
        message = str(error)
        
        # Determine severity based on exception type
        if isinstance(error, (ConnectionError, TimeoutError)):
            severity = ErrorSeverity.WARNING
            recovery_actions = ['retry', 'check_connection']
        elif isinstance(error, PermissionError):
            severity = ErrorSeverity.ERROR
            recovery_actions = ['check_permissions', 'contact_admin']
        elif isinstance(error, (ValueError, TypeError)):
            severity = ErrorSeverity.ERROR
            recovery_actions = ['correct_input', 'validate_data']
        else:
            severity = ErrorSeverity.ERROR
            recovery_actions = ['retry', 'contact_support']
        
        return ErrorState(
            error_type=error_type,
            message=message,
            severity=severity,
            recovery_actions=recovery_actions,
            context=context
        )
    
    def _preprocess_content(self, content: str, content_type: ContentType) -> str:
        """Preprocess content based on type."""
        if content_type == ContentType.CODE_BLOCK:
            # Remove extra whitespace but preserve indentation
            lines = content.split('\n')
            # Remove empty lines at start and end
            while lines and not lines[0].strip():
                lines.pop(0)
            while lines and not lines[-1].strip():
                lines.pop()
            return '\n'.join(lines)
        
        elif content_type == ContentType.JSON:
            # Validate and reformat JSON
            try:
                import json
                parsed = json.loads(content)
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            except Exception:
                return content
        
        return content.strip()
    
    def _apply_format_processor(self, content: str, content_type: ContentType, metadata: Dict[str, Any]) -> List[ContentSection]:
        """Apply the appropriate format processor."""
        processor = self._format_processors.get(content_type, self._format_plain_text)
        result = processor(content, metadata)
        
        # Ensure result is a list
        if not isinstance(result, list):
            result = [result]
        
        return result
    
    def _postprocess_sections(self, sections: List[ContentSection], metadata: Dict[str, Any]) -> List[ContentSection]:
        """Post-process sections for final output."""
        # Add ordering if not present
        for i, section in enumerate(sections):
            if section.order == 0:
                section.order = i
        
        # Sort by order
        sections.sort(key=lambda x: x.order)
        
        # Add global metadata
        for section in sections:
            section.metadata.update({
                'processed_at': datetime.now().isoformat(),
                'renderer_version': '1.0'
            })
        
        return sections
    
    def _format_plain_text(self, content: str, metadata: Dict[str, Any]) -> ContentSection:
        """Format plain text content."""
        return ContentSection(
            content=content,
            content_type=ContentType.PLAIN_TEXT,
            metadata=metadata,
            order=0
        )
    
    def _format_code_block(self, content: str, metadata: Dict[str, Any]) -> ContentSection:
        """Format code block content."""
        # Extract language if present
        language = metadata.get("language", "")
        
        # Clean up code block markers
        cleaned_content = re.sub(r'^```\w*\n?', '', content)
        cleaned_content = re.sub(r'\n?```$', '', cleaned_content)
        
        return ContentSection(
            content=cleaned_content,
            content_type=ContentType.CODE_BLOCK,
            metadata={**metadata, "language": language},
            order=0
        )
    
    def _format_structured_data(self, content: str, metadata: Dict[str, Any]) -> ContentSection:
        """Format structured data content."""
        return ContentSection(
            content=content,
            content_type=ContentType.STRUCTURED_DATA,
            metadata=metadata,
            order=0
        )
    
    def _format_error_message(self, content: str, metadata: Dict[str, Any]) -> ContentSection:
        """Format error message content."""
        return ContentSection(
            content=content,
            content_type=ContentType.ERROR_MESSAGE,
            metadata={**metadata, "severity": "error"},
            order=0
        )
    
    def _format_markdown(self, content: str, metadata: Dict[str, Any]) -> ContentSection:
        """Format markdown content."""
        return ContentSection(
            content=content,
            content_type=ContentType.MARKDOWN,
            metadata=metadata,
            order=0
        )
    
    def _format_json(self, content: str, metadata: Dict[str, Any]) -> ContentSection:
        """Format JSON content."""
        try:
            # Pretty print JSON
            parsed = json.loads(content)
            formatted = json.dumps(parsed, indent=2)
            return ContentSection(
                content=formatted,
                content_type=ContentType.JSON,
                metadata=metadata,
                order=0
            )
        except json.JSONDecodeError:
            # Fallback to plain text if JSON parsing fails
            return self._format_plain_text(content, metadata)
    
    def _format_table(self, content: str, metadata: Dict[str, Any]) -> ContentSection:
        """Format table content."""
        return ContentSection(
            content=content,
            content_type=ContentType.TABLE,
            metadata=metadata,
            order=0
        )
    
    def _is_json(self, content: str) -> bool:
        """Check if content is JSON."""
        try:
            json.loads(content)
            return True
        except (json.JSONDecodeError, ValueError):
            return False
    
    def _is_code_block(self, content: str) -> bool:
        """Check if content is a code block with improved detection."""
        # Explicit code block markers
        if content.startswith('```') and content.endswith('```'):
            return True
        
        # Check for common programming patterns
        code_patterns = [
            r'^\s*def\s+\w+\s*\(',  # Python functions
            r'^\s*class\s+\w+',  # Class definitions
            r'^\s*function\s+\w+\s*\(',  # JavaScript functions
            r'^\s*import\s+\w+',  # Import statements
            r'^\s*from\s+\w+\s+import',  # From imports
            r'^\s*#include\s*<',  # C/C++ includes
            r'^\s*public\s+class\s+\w+',  # Java classes
            r'<\?php',  # PHP opening tag
            r'<html|<HTML',  # HTML
            r'^\s*\w+\s*=\s*function\s*\(',  # Function assignments
        ]
        
        # Check if content has multiple lines and programming patterns
        lines = content.split('\n')
        if len(lines) >= 2:  # Reduced from > 2 to >= 2
            pattern_count = 0
            for pattern in code_patterns:
                if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                    pattern_count += 1
            
            # Need at least one strong programming pattern
            if pattern_count > 0:
                return True
        
        # Check for high density of programming symbols (only for longer content)
        if len(content) > 50:
            programming_chars = ['{', '}', ';', '()', '[]', '==', '!=', '&&', '||']
            char_count = sum(content.count(char) for char in programming_chars)
            if char_count / len(content) > 0.1:
                return True
        
        return False
    
    def _is_markdown(self, content: str) -> bool:
        """Check if content contains markdown formatting with improved detection."""
        return self._count_markdown_patterns(content) >= 2
    
    def _count_markdown_patterns(self, content: str) -> int:
        """Count markdown patterns in content."""
        markdown_patterns = [
            r'^#{1,6}\s+.+',  # Headers with content
            r'\*\*[^*]+\*\*',  # Bold text
            r'\*[^*]+\*',  # Italic text
            r'^\s*[-*+]\s+.+',  # Unordered lists with content
            r'^\s*\d+\.\s+.+',  # Numbered lists with content
            r'\[.+\]\(.+\)',  # Links with content
            r'`[^`]+`',  # Inline code
            r'^\s*>',  # Blockquotes
            r'^\s*\|.+\|',  # Table rows
            r'---+',  # Horizontal rules
        ]
        
        # Count markdown patterns
        pattern_count = 0
        for pattern in markdown_patterns:
            if re.search(pattern, content, re.MULTILINE):
                pattern_count += 1
        
        return pattern_count
    
    def _is_table(self, content: str) -> bool:
        """Check if content is table format."""
        lines = content.split('\n')
        if len(lines) < 2:
            return False
        
        # Check for pipe-separated table
        pipe_count = content.count('|')
        if pipe_count > 2:
            return True
        
        # Check for tab-separated values
        tab_lines = [line for line in lines if '\t' in line]
        if len(tab_lines) > 1:
            return True
        
        return False
    
    def _is_error_message(self, content: str) -> bool:
        """Check if content is an error message with improved detection."""
        error_patterns = [
            r'\berror\b.*:',  # Error with colon
            r'\bexception\b.*:',  # Exception with colon
            r'\bfailed\b.*:',  # Failed with colon
            r'traceback.*:',  # Traceback
            r'stack\s+trace',  # Stack trace
            r'\bfatal\b.*:',  # Fatal error
            r'\bcritical\b.*:',  # Critical error
            r'\bwarning\b.*:',  # Warning
            r'^\s*at\s+\w+',  # Stack trace lines
            r'^\s*File\s+".*",\s+line\s+\d+',  # Python traceback
            r'Exception\s+in\s+thread',  # Java exception
        ]
        
        content_lower = content.lower()
        
        # Check for error patterns
        for pattern in error_patterns:
            if re.search(pattern, content_lower, re.MULTILINE):
                return True
        
        # Check for high concentration of error keywords
        error_keywords = [
            'error', 'exception', 'failed', 'failure', 'traceback',
            'stack trace', 'fatal', 'critical', 'warning', 'abort'
        ]
        
        keyword_count = sum(1 for keyword in error_keywords if keyword in content_lower)
        return keyword_count >= 2
    
    def _is_structured_data(self, content: str) -> bool:
        """Check if content contains structured data patterns."""
        # Check for key-value pairs
        if ':' in content and '\n' in content:
            lines = content.split('\n')
            kv_lines = [line for line in lines if ':' in line and len(line.split(':')) == 2]
            if len(kv_lines) > 1:
                return True
        
        return False
    
    def _format_dict(self, data: dict) -> str:
        """Format dictionary data."""
        lines = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{key}: {json.dumps(value, indent=2)}")
            else:
                lines.append(f"{key}: {value}")
        return '\n'.join(lines)
    
    def _format_list(self, data: list) -> str:
        """Format list data."""
        if not data:
            return "[]"
        
        lines = []
        for i, item in enumerate(data):
            if isinstance(item, (dict, list)):
                lines.append(f"{i + 1}. {json.dumps(item, indent=2)}")
            else:
                lines.append(f"{i + 1}. {item}")
        return '\n'.join(lines)