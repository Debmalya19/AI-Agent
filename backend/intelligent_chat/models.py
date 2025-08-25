"""
Data models and interfaces for the intelligent chat UI system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod


class ContentType(Enum):
    """Content types for response rendering."""
    PLAIN_TEXT = "plain_text"
    CODE_BLOCK = "code_block"
    STRUCTURED_DATA = "structured_data"
    ERROR_MESSAGE = "error_message"
    TOOL_STATUS = "tool_status"
    MARKDOWN = "markdown"
    JSON = "json"
    TABLE = "table"


class LoadingState(Enum):
    """Loading states for UI indicators."""
    IDLE = "idle"
    LOADING = "loading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LoadingIndicator:
    """Loading indicator for UI feedback."""
    tool_name: str
    state: LoadingState
    progress: float = 0.0
    message: str = ""
    estimated_time: Optional[float] = None


@dataclass
class ContentSection:
    """Content section for rendered responses."""
    content: str
    content_type: ContentType
    metadata: Dict[str, Any] = field(default_factory=dict)
    order: int = 0


@dataclass
class InteractiveElement:
    """Interactive UI element."""
    element_type: str
    element_id: str
    properties: Dict[str, Any] = field(default_factory=dict)
    actions: List[str] = field(default_factory=list)


@dataclass
class ErrorState:
    """Error state information."""
    error_type: str
    message: str
    severity: ErrorSeverity
    recovery_actions: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    """Response from chat processing."""
    content: str
    content_type: ContentType
    tools_used: List[str] = field(default_factory=list)
    context_used: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    execution_time: float = 0.0
    ui_hints: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ToolRecommendation:
    """Tool recommendation with scoring."""
    tool_name: str
    relevance_score: float
    expected_execution_time: float
    confidence_level: float
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UIState:
    """UI state information."""
    loading_indicators: List[LoadingIndicator] = field(default_factory=list)
    content_sections: List[ContentSection] = field(default_factory=list)
    interactive_elements: List[InteractiveElement] = field(default_factory=list)
    error_states: List[ErrorState] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextEntry:
    """Context entry for conversation history."""
    content: str
    source: str
    relevance_score: float
    timestamp: datetime
    context_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolScore:
    """Tool scoring information."""
    tool_name: str
    base_score: float
    context_boost: float
    performance_score: float
    final_score: float
    reasoning: str = ""


@dataclass
class ToolResult:
    """Result from tool execution."""
    tool_name: str
    success: bool
    result: Any
    execution_time: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# Base interfaces for core components

class BaseChatManager(ABC):
    """Base interface for ChatManager."""
    
    @abstractmethod
    async def process_message(self, message: str, user_id: str, session_id: str) -> ChatResponse:
        """Process a user message and return a chat response."""
        pass
    
    @abstractmethod
    async def get_conversation_context(self, user_id: str, limit: int = 10) -> List[ContextEntry]:
        """Get conversation context for a user."""
        pass
    
    @abstractmethod
    def update_ui_state(self, response: ChatResponse) -> UIState:
        """Update UI state based on response."""
        pass


class BaseToolOrchestrator(ABC):
    """Base interface for ToolOrchestrator."""
    
    @abstractmethod
    async def select_tools(self, query: str, context: List[ContextEntry]) -> List[ToolRecommendation]:
        """Select relevant tools for a query."""
        pass
    
    @abstractmethod
    async def execute_tools(self, tools: List[str], query: str, context: Dict[str, Any]) -> List[ToolResult]:
        """Execute selected tools."""
        pass
    
    @abstractmethod
    def optimize_execution_order(self, tools: List[ToolRecommendation]) -> List[ToolRecommendation]:
        """Optimize tool execution order."""
        pass


class BaseResponseRenderer(ABC):
    """Base interface for ResponseRenderer."""
    
    @abstractmethod
    def render_response(self, content: str, metadata: Dict[str, Any]) -> List[ContentSection]:
        """Render response content."""
        pass
    
    @abstractmethod
    def detect_content_type(self, content: str) -> ContentType:
        """Detect content type."""
        pass
    
    @abstractmethod
    def format_structured_data(self, data: Any) -> str:
        """Format structured data."""
        pass


class BaseContextRetriever(ABC):
    """Base interface for ContextRetriever."""
    
    @abstractmethod
    async def get_relevant_context(self, query: str, user_id: str, limit: int = 10) -> List[ContextEntry]:
        """Get relevant context for a query."""
        pass
    
    @abstractmethod
    def summarize_context(self, context: List[ContextEntry]) -> str:
        """Summarize context entries."""
        pass
    
    @abstractmethod
    def track_context_usage(self, context: List[ContextEntry], effectiveness: float) -> None:
        """Track context usage effectiveness."""
        pass


class BaseToolSelector(ABC):
    """Base interface for ToolSelector."""
    
    @abstractmethod
    def score_tools(self, query: str, available_tools: List[str]) -> List[ToolScore]:
        """Score tools for relevance."""
        pass
    
    @abstractmethod
    def apply_context_boost(self, scores: List[ToolScore], context: List[ContextEntry]) -> List[ToolScore]:
        """Apply context-based score boosting."""
        pass
    
    @abstractmethod
    def filter_by_threshold(self, scores: List[ToolScore], threshold: float = 0.5) -> List[str]:
        """Filter tools by score threshold."""
        pass