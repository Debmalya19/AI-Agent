"""
Comprehensive error handling and recovery mechanisms for the intelligent chat UI system.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Union, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field

from .models import ToolResult, ToolRecommendation, ContextEntry, ChatResponse
from .exceptions import (
    ChatUIException, ToolExecutionError, ToolSelectionError, 
    ContextRetrievalError, RenderingError, TimeoutError, ResourceLimitError
)


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""
    RETRY = "retry"
    FALLBACK_TOOL = "fallback_tool"
    PARTIAL_RESULTS = "partial_results"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    USER_INTERVENTION = "user_intervention"
    SKIP_AND_CONTINUE = "skip_and_continue"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RecoveryAction:
    """Represents a recovery action for an error."""
    strategy: RecoveryStrategy
    description: str
    action_data: Dict[str, Any] = field(default_factory=dict)
    estimated_time: float = 0.0
    success_probability: float = 0.0
    fallback_tools: List[str] = field(default_factory=list)
    user_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ErrorContext:
    """Context information for error handling."""
    error_type: str
    component: str
    operation: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    query: Optional[str] = None
    tool_name: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    success: bool
    strategy_used: RecoveryStrategy
    result_data: Any = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    partial_results: List[Any] = field(default_factory=list)
    user_message: Optional[str] = None


class ErrorHandler:
    """
    Comprehensive error handling and recovery system.
    
    Provides intelligent error recovery strategies, fallback mechanisms,
    and graceful degradation for the intelligent chat UI system.
    """
    
    def __init__(
        self,
        tool_selector=None,
        available_tools: Optional[Dict[str, Any]] = None,
        context_retriever=None,
        response_renderer=None,
        max_retry_attempts: int = 3,
        retry_delay: float = 1.0,
        enable_fallback_tools: bool = True
    ):
        """
        Initialize ErrorHandler.
        
        Args:
            tool_selector: Tool selection service for fallback tool selection
            available_tools: Dictionary of available tools for fallback
            context_retriever: Context retrieval service for fallback context
            response_renderer: Response renderer for error message formatting
            max_retry_attempts: Maximum number of retry attempts
            retry_delay: Delay between retry attempts in seconds
            enable_fallback_tools: Whether to enable automatic fallback tool selection
        """
        self.tool_selector = tool_selector
        self.available_tools = available_tools or {}
        self.context_retriever = context_retriever
        self.response_renderer = response_renderer
        self.max_retry_attempts = max_retry_attempts
        self.retry_delay = retry_delay
        self.enable_fallback_tools = enable_fallback_tools
        
        self.logger = logging.getLogger(__name__)
        
        # Error statistics and patterns
        self._error_stats: Dict[str, Dict[str, Any]] = {}
        self._recovery_success_rates: Dict[RecoveryStrategy, float] = {
            RecoveryStrategy.RETRY: 0.7,
            RecoveryStrategy.FALLBACK_TOOL: 0.8,
            RecoveryStrategy.PARTIAL_RESULTS: 0.9,
            RecoveryStrategy.GRACEFUL_DEGRADATION: 0.95,
            RecoveryStrategy.USER_INTERVENTION: 0.6,
            RecoveryStrategy.SKIP_AND_CONTINUE: 1.0
        }
        
        # Tool fallback mappings
        self._tool_fallbacks = {
            "BTWebsiteSearch": ["web_search", "ComprehensiveAnswerGenerator"],
            "BTSupportHours": ["ComprehensiveAnswerGenerator"],
            "BTPlansInformation": ["BTWebsiteSearch", "ComprehensiveAnswerGenerator"],
            "CreateSupportTicket": ["ComprehensiveAnswerGenerator"],
            "ComprehensiveAnswerGenerator": ["ContextRetriever"],
            "ContextRetriever": [],
            "web_search": ["ComprehensiveAnswerGenerator"],
            "database_query": ["ComprehensiveAnswerGenerator"],
            "file_analysis": ["ComprehensiveAnswerGenerator"]
        }
        
        # Error severity mappings
        self._error_severity_map = {
            ToolExecutionError: ErrorSeverity.MEDIUM,
            ToolSelectionError: ErrorSeverity.HIGH,
            ContextRetrievalError: ErrorSeverity.MEDIUM,
            RenderingError: ErrorSeverity.LOW,
            TimeoutError: ErrorSeverity.MEDIUM,
            ResourceLimitError: ErrorSeverity.HIGH,
            ChatUIException: ErrorSeverity.MEDIUM
        }
    
    def handle_tool_failure(
        self, 
        tool_name: str, 
        error: Exception, 
        query: str,
        context: List[ContextEntry],
        execution_context: Dict[str, Any]
    ) -> RecoveryResult:
        """
        Handle tool execution failure with intelligent recovery strategies.
        
        Args:
            tool_name: Name of the failed tool
            error: The exception that occurred
            query: Original user query
            context: Conversation context
            execution_context: Additional execution context
            
        Returns:
            RecoveryResult with recovery outcome
        """
        error_context = ErrorContext(
            error_type=type(error).__name__,
            component="tool_orchestrator",
            operation="tool_execution",
            query=query,
            tool_name=tool_name,
            metadata=execution_context
        )
        
        self.logger.warning(f"Tool failure detected: {tool_name} - {str(error)}")
        self._record_error(error_context, error)
        
        # Determine recovery strategy
        recovery_action = self._determine_recovery_strategy(error, error_context)
        
        # Execute recovery strategy
        return self._execute_recovery_strategy(recovery_action, query, context, execution_context)
    
    def handle_context_failure(
        self, 
        error: Exception, 
        user_id: str,
        query: Optional[str] = None
    ) -> RecoveryResult:
        """
        Handle context retrieval failure with fallback mechanisms.
        
        Args:
            error: The exception that occurred
            user_id: User identifier
            query: Optional query that caused the failure
            
        Returns:
            RecoveryResult with recovery outcome
        """
        error_context = ErrorContext(
            error_type=type(error).__name__,
            component="context_retriever",
            operation="context_retrieval",
            user_id=user_id,
            query=query
        )
        
        self.logger.warning(f"Context retrieval failure: {str(error)}")
        self._record_error(error_context, error)
        
        # Try fallback context strategies
        if isinstance(error, TimeoutError):
            # Use cached context if available
            recovery_action = RecoveryAction(
                strategy=RecoveryStrategy.PARTIAL_RESULTS,
                description="Using cached context due to timeout",
                action_data={"use_cache": True},
                success_probability=0.8,
                user_message="Using recent conversation history due to slow response"
            )
        else:
            # Graceful degradation without context
            recovery_action = RecoveryAction(
                strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
                description="Continue without context",
                success_probability=0.7,
                user_message="Continuing without full conversation context"
            )
        
        return self._execute_context_recovery(recovery_action, user_id, query)
    
    def handle_rendering_failure(
        self, 
        content: str, 
        error: Exception,
        content_type: Optional[str] = None
    ) -> RecoveryResult:
        """
        Handle response rendering failure with fallback formatting.
        
        Args:
            content: Content that failed to render
            error: The exception that occurred
            content_type: Optional content type
            
        Returns:
            RecoveryResult with recovery outcome
        """
        error_context = ErrorContext(
            error_type=type(error).__name__,
            component="response_renderer",
            operation="content_rendering",
            metadata={"content_type": content_type, "content_length": len(content)}
        )
        
        self.logger.warning(f"Rendering failure: {str(error)}")
        self._record_error(error_context, error)
        
        # Always fallback to plain text rendering
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
            description="Fallback to plain text rendering",
            success_probability=0.95,
            user_message="Content displayed in simplified format"
        )
        
        return self._execute_rendering_recovery(recovery_action, content, content_type)
    
    def get_fallback_tools(self, failed_tool: str, query: str) -> List[str]:
        """
        Get fallback tools for a failed tool based on query analysis.
        
        Args:
            failed_tool: Name of the tool that failed
            query: User query for context
            
        Returns:
            List of fallback tool names
        """
        if not self.enable_fallback_tools:
            return []
        
        # Get predefined fallbacks
        fallback_tools = self._tool_fallbacks.get(failed_tool, [])
        
        # Use tool selector for intelligent fallback selection if available
        if self.tool_selector and self.available_tools:
            try:
                available_tools = [t for t in self.available_tools.keys() if t != failed_tool]
                tool_scores = self.tool_selector.score_tools(query, available_tools)
                
                # Add top-scoring tools as fallbacks
                for score in tool_scores[:2]:  # Top 2 alternatives
                    if score.tool_name not in fallback_tools:
                        fallback_tools.append(score.tool_name)
                        
            except Exception as e:
                self.logger.warning(f"Failed to get intelligent fallbacks: {e}")
        
        return fallback_tools[:3]  # Limit to 3 fallback tools
    
    def create_partial_result(
        self, 
        successful_results: List[ToolResult],
        failed_tools: List[str],
        query: str
    ) -> ChatResponse:
        """
        Create a partial result from successful tool executions.
        
        Args:
            successful_results: Results from successful tool executions
            failed_tools: Names of tools that failed
            query: Original user query
            
        Returns:
            ChatResponse with partial results
        """
        if not successful_results:
            return ChatResponse(
                content="I apologize, but I encountered issues processing your request. Please try again.",
                content_type="text",
                tools_used=[],
                context_used=[],
                confidence_score=0.1,
                execution_time=0.0,
                ui_hints={"error_state": True, "retry_available": True}
            )
        
        # Combine successful results
        combined_content = []
        tools_used = []
        total_execution_time = 0.0
        
        for result in successful_results:
            if result.success and result.result:
                combined_content.append(str(result.result))
                tools_used.append(result.tool_name)
                total_execution_time += result.execution_time
        
        content = "\n\n".join(combined_content)
        
        # Add note about partial results
        if failed_tools:
            content += f"\n\n*Note: Some information sources were unavailable ({', '.join(failed_tools)}). The above response is based on available data.*"
        
        confidence_score = len(successful_results) / (len(successful_results) + len(failed_tools))
        
        return ChatResponse(
            content=content,
            content_type="text",
            tools_used=tools_used,
            context_used=[],
            confidence_score=confidence_score,
            execution_time=total_execution_time,
            ui_hints={
                "partial_results": True,
                "failed_tools": failed_tools,
                "retry_available": True
            }
        )
    
    def _determine_recovery_strategy(
        self, 
        error: Exception, 
        error_context: ErrorContext
    ) -> RecoveryAction:
        """Determine the best recovery strategy for an error."""
        error_type = type(error)
        severity = self._error_severity_map.get(error_type, ErrorSeverity.MEDIUM)
        
        # Check error patterns and history
        error_history = self._get_error_history(error_context.tool_name or "unknown")
        
        if isinstance(error, TimeoutError):
            if error_history.get("timeout_count", 0) < 2:
                return RecoveryAction(
                    strategy=RecoveryStrategy.RETRY,
                    description="Retry with extended timeout",
                    action_data={"timeout_multiplier": 2.0},
                    success_probability=0.6,
                    max_retries=1
                )
            else:
                fallback_tools = self.get_fallback_tools(error_context.tool_name or "", error_context.query or "")
                return RecoveryAction(
                    strategy=RecoveryStrategy.FALLBACK_TOOL,
                    description="Use fallback tool due to repeated timeouts",
                    fallback_tools=fallback_tools,
                    success_probability=0.8
                )
        
        elif isinstance(error, ToolExecutionError):
            if error_history.get("execution_failures", 0) < 2:
                return RecoveryAction(
                    strategy=RecoveryStrategy.RETRY,
                    description="Retry tool execution",
                    success_probability=0.5,
                    max_retries=2
                )
            else:
                fallback_tools = self.get_fallback_tools(error_context.tool_name or "", error_context.query or "")
                return RecoveryAction(
                    strategy=RecoveryStrategy.FALLBACK_TOOL,
                    description="Use fallback tool due to repeated failures",
                    fallback_tools=fallback_tools,
                    success_probability=0.7
                )
        
        elif isinstance(error, ResourceLimitError):
            return RecoveryAction(
                strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
                description="Reduce resource usage and continue",
                action_data={"reduce_concurrency": True},
                success_probability=0.8
            )
        
        else:
            # Default strategy based on severity
            if severity == ErrorSeverity.CRITICAL:
                return RecoveryAction(
                    strategy=RecoveryStrategy.USER_INTERVENTION,
                    description="Critical error requires user intervention",
                    success_probability=0.3,
                    user_message="A critical error occurred. Please try again or contact support."
                )
            else:
                return RecoveryAction(
                    strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
                    description="Continue with reduced functionality",
                    success_probability=0.7
                )
    
    def _execute_recovery_strategy(
        self, 
        recovery_action: RecoveryAction,
        query: str,
        context: List[ContextEntry],
        execution_context: Dict[str, Any]
    ) -> RecoveryResult:
        """Execute a recovery strategy."""
        start_time = time.time()
        
        try:
            if recovery_action.strategy == RecoveryStrategy.RETRY:
                return self._execute_retry_recovery(recovery_action, query, context, execution_context)
            
            elif recovery_action.strategy == RecoveryStrategy.FALLBACK_TOOL:
                return self._execute_fallback_tool_recovery(recovery_action, query, context, execution_context)
            
            elif recovery_action.strategy == RecoveryStrategy.PARTIAL_RESULTS:
                return self._execute_partial_results_recovery(recovery_action, execution_context)
            
            elif recovery_action.strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                return self._execute_graceful_degradation_recovery(recovery_action, query)
            
            else:
                return RecoveryResult(
                    success=False,
                    strategy_used=recovery_action.strategy,
                    error_message=f"Recovery strategy {recovery_action.strategy} not implemented",
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            self.logger.error(f"Recovery strategy execution failed: {e}")
            return RecoveryResult(
                success=False,
                strategy_used=recovery_action.strategy,
                error_message=f"Recovery failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def _execute_retry_recovery(
        self, 
        recovery_action: RecoveryAction,
        query: str,
        context: List[ContextEntry],
        execution_context: Dict[str, Any]
    ) -> RecoveryResult:
        """Execute retry recovery strategy."""
        # This would be implemented by the calling component
        # Return a placeholder result indicating retry should be attempted
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.RETRY,
            result_data={"should_retry": True, "retry_config": recovery_action.action_data},
            user_message="Retrying operation..."
        )
    
    def _execute_fallback_tool_recovery(
        self, 
        recovery_action: RecoveryAction,
        query: str,
        context: List[ContextEntry],
        execution_context: Dict[str, Any]
    ) -> RecoveryResult:
        """Execute fallback tool recovery strategy."""
        if not recovery_action.fallback_tools:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FALLBACK_TOOL,
                error_message="No fallback tools available"
            )
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.FALLBACK_TOOL,
            result_data={
                "fallback_tools": recovery_action.fallback_tools,
                "original_query": query,
                "context": context
            },
            user_message=f"Trying alternative approach..."
        )
    
    def _execute_partial_results_recovery(
        self, 
        recovery_action: RecoveryAction,
        execution_context: Dict[str, Any]
    ) -> RecoveryResult:
        """Execute partial results recovery strategy."""
        successful_results = execution_context.get("successful_results", [])
        
        if successful_results:
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.PARTIAL_RESULTS,
                partial_results=successful_results,
                user_message="Showing available results..."
            )
        else:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.PARTIAL_RESULTS,
                error_message="No partial results available"
            )
    
    def _execute_graceful_degradation_recovery(
        self, 
        recovery_action: RecoveryAction,
        query: str
    ) -> RecoveryResult:
        """Execute graceful degradation recovery strategy."""
        # Provide a basic response acknowledging the issue
        degraded_response = f"I encountered some technical difficulties while processing your request about '{query}'. I'm working with limited functionality but can still try to help. Please let me know if you'd like to try a different approach."
        
        result_data = {"degraded_response": degraded_response}
        
        # Include any specific action data from the recovery action
        if recovery_action.action_data:
            result_data.update(recovery_action.action_data)
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.GRACEFUL_DEGRADATION,
            result_data=result_data,
            user_message="Operating with reduced functionality"
        )
    
    def _execute_context_recovery(
        self, 
        recovery_action: RecoveryAction,
        user_id: str,
        query: Optional[str]
    ) -> RecoveryResult:
        """Execute context retrieval recovery."""
        if recovery_action.strategy == RecoveryStrategy.PARTIAL_RESULTS:
            # Try to get cached context
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.PARTIAL_RESULTS,
                result_data={"use_cached_context": True},
                user_message=recovery_action.user_message
            )
        else:
            # Continue without context
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.GRACEFUL_DEGRADATION,
                result_data={"no_context": True},
                user_message=recovery_action.user_message
            )
    
    def _execute_rendering_recovery(
        self, 
        recovery_action: RecoveryAction,
        content: str,
        content_type: Optional[str]
    ) -> RecoveryResult:
        """Execute rendering recovery."""
        # Fallback to plain text
        plain_text_content = self._convert_to_plain_text(content)
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.GRACEFUL_DEGRADATION,
            result_data={"plain_text_content": plain_text_content},
            user_message=recovery_action.user_message
        )
    
    def _convert_to_plain_text(self, content: str) -> str:
        """Convert content to plain text format."""
        # Simple conversion - remove common markup
        import re
        
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Remove markdown formatting
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Bold
        content = re.sub(r'\*(.*?)\*', r'\1', content)      # Italic
        content = re.sub(r'`(.*?)`', r'\1', content)        # Code
        
        return content.strip()
    
    def _record_error(self, error_context: ErrorContext, error: Exception):
        """Record error for pattern analysis."""
        component = error_context.component
        if component not in self._error_stats:
            self._error_stats[component] = {
                "total_errors": 0,
                "error_types": {},
                "recent_errors": []
            }
        
        self._error_stats[component]["total_errors"] += 1
        error_type = type(error).__name__
        
        if error_type not in self._error_stats[component]["error_types"]:
            self._error_stats[component]["error_types"][error_type] = 0
        self._error_stats[component]["error_types"][error_type] += 1
        
        # Keep recent errors for pattern analysis
        recent_errors = self._error_stats[component]["recent_errors"]
        recent_errors.append({
            "timestamp": time.time(),
            "error_type": error_type,
            "context": error_context
        })
        
        # Keep only last 10 errors
        if len(recent_errors) > 10:
            recent_errors.pop(0)
    
    def _get_error_history(self, component: str) -> Dict[str, Any]:
        """Get error history for a component."""
        if component not in self._error_stats:
            return {}
        
        stats = self._error_stats[component]
        recent_errors = stats["recent_errors"]
        
        # Analyze recent error patterns
        timeout_count = sum(1 for e in recent_errors if "Timeout" in e["error_type"])
        execution_failures = sum(1 for e in recent_errors if "Execution" in e["error_type"])
        
        return {
            "total_errors": stats["total_errors"],
            "timeout_count": timeout_count,
            "execution_failures": execution_failures,
            "recent_error_types": [e["error_type"] for e in recent_errors[-5:]]
        }
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        return {
            "component_stats": self._error_stats,
            "recovery_success_rates": self._recovery_success_rates,
            "total_errors": sum(stats["total_errors"] for stats in self._error_stats.values())
        }