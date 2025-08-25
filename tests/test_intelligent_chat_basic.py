"""
Basic tests for intelligent chat UI infrastructure.
"""

import pytest
import asyncio
from datetime import datetime

from intelligent_chat import (
    ChatManager,
    ToolOrchestrator,
    ResponseRenderer,
    ContextRetriever,
    ToolSelector,
    ChatResponse,
    ToolRecommendation,
    UIState,
    ContextEntry,
    ContentType,
    ChatUIException,
    ToolExecutionError,
    ContextRetrievalError,
    RenderingError
)


def test_imports():
    """Test that all components can be imported."""
    assert ChatManager is not None
    assert ToolOrchestrator is not None
    assert ResponseRenderer is not None
    assert ContextRetriever is not None
    assert ToolSelector is not None


def test_data_models():
    """Test that data models can be instantiated."""
    # Test ChatResponse
    response = ChatResponse(
        content="Test response",
        content_type=ContentType.PLAIN_TEXT
    )
    assert response.content == "Test response"
    assert response.content_type == ContentType.PLAIN_TEXT
    assert isinstance(response.timestamp, datetime)
    
    # Test ContextEntry
    context = ContextEntry(
        content="Test context",
        source="test",
        relevance_score=0.8,
        timestamp=datetime.now(),
        context_type="test"
    )
    assert context.content == "Test context"
    assert context.relevance_score == 0.8


def test_exceptions():
    """Test that exceptions can be raised and caught."""
    with pytest.raises(ChatUIException):
        raise ChatUIException("Test error")
    
    with pytest.raises(ToolExecutionError):
        raise ToolExecutionError("Tool failed", "test_tool")
    
    with pytest.raises(ContextRetrievalError):
        raise ContextRetrievalError("Context failed", "user123")
    
    with pytest.raises(RenderingError):
        raise RenderingError("Render failed", "test content")


def test_chat_manager_initialization():
    """Test ChatManager can be initialized."""
    manager = ChatManager()
    assert manager is not None
    assert manager.tool_orchestrator is None
    assert manager.context_retriever is None
    assert manager.response_renderer is None


def test_tool_orchestrator_initialization():
    """Test ToolOrchestrator can be initialized."""
    orchestrator = ToolOrchestrator()
    assert orchestrator is not None
    assert orchestrator.tool_selector is None
    assert orchestrator.available_tools == {}


def test_response_renderer_initialization():
    """Test ResponseRenderer can be initialized."""
    renderer = ResponseRenderer()
    assert renderer is not None
    assert renderer._format_processors is not None


def test_context_retriever_initialization():
    """Test ContextRetriever can be initialized."""
    retriever = ContextRetriever()
    assert retriever is not None
    assert retriever.context_engine is None
    assert retriever.memory_manager is None


def test_tool_selector_initialization():
    """Test ToolSelector can be initialized."""
    selector = ToolSelector()
    assert selector is not None
    assert selector.tool_metadata == {}


@pytest.mark.asyncio
async def test_chat_manager_process_message():
    """Test ChatManager can process a basic message."""
    manager = ChatManager()
    
    response = await manager.process_message(
        message="Hello, world!",
        user_id="test_user",
        session_id="test_session"
    )
    
    assert isinstance(response, ChatResponse)
    assert "Hello, world!" in response.content
    assert response.execution_time > 0


def test_response_renderer_content_detection():
    """Test ResponseRenderer can detect content types."""
    renderer = ResponseRenderer()
    
    # Test plain text
    assert renderer.detect_content_type("Hello world") == ContentType.PLAIN_TEXT
    
    # Test JSON
    assert renderer.detect_content_type('{"key": "value"}') == ContentType.JSON
    
    # Test code block
    assert renderer.detect_content_type("```python\nprint('hello')\n```") == ContentType.CODE_BLOCK
    
    # Test error message
    assert renderer.detect_content_type("Error: Something went wrong") == ContentType.ERROR_MESSAGE


def test_tool_selector_scoring():
    """Test ToolSelector can score tools."""
    selector = ToolSelector()
    
    scores = selector.score_tools(
        query="search for information online",
        available_tools=["web_search", "database_query", "file_analysis"]
    )
    
    assert len(scores) == 3
    assert all(isinstance(score.final_score, float) for score in scores)
    assert all(0 <= score.final_score <= 1 for score in scores)
    
    # web_search should score highest for this query
    web_search_score = next(s for s in scores if s.tool_name == "web_search")
    assert web_search_score.final_score > 0.5


if __name__ == "__main__":
    pytest.main([__file__])