"""
ChatManager - Central coordinator for chat interactions.
"""

import asyncio
import time
import sys
import os
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .models import (
    BaseChatManager, 
    ChatResponse, 
    ContextEntry, 
    UIState, 
    ContentType,
    LoadingIndicator,
    LoadingState,
    ErrorState,
    ErrorSeverity
)
from .exceptions import ChatUIException, ToolExecutionError, ContextRetrievalError
from .performance_cache import get_response_cache, get_performance_cache
from .resource_monitor import get_resource_monitor

# Import memory layer components
try:
    from memory_layer_manager import MemoryLayerManager, MemoryStats
    from context_retrieval_engine import ContextRetrievalEngine
    from memory_models import ConversationEntryDTO, ContextEntryDTO
    from memory_config import load_config
except ImportError as e:
    print(f"Warning: Could not import memory components: {e}")
    MemoryLayerManager = None
    ContextRetrievalEngine = None


class ChatManager(BaseChatManager):
    """
    Central coordinator for chat interactions.
    
    Manages the flow between tool orchestration, context retrieval,
    and response rendering while maintaining conversation state.
    Integrates with existing memory layer for conversation storage and context retrieval.
    """
    
    def __init__(
        self,
        tool_orchestrator=None,
        context_retriever=None,
        response_renderer=None,
        memory_manager=None,
        context_engine=None,
        auto_create_context_engine=True,
        llm=None,
        agent_executor=None
    ):
        """Initialize ChatManager with component dependencies."""
        self.tool_orchestrator = tool_orchestrator
        self.context_retriever = context_retriever
        self.response_renderer = response_renderer
        
        # Initialize memory layer integration
        self.memory_manager = memory_manager or (MemoryLayerManager() if MemoryLayerManager else None)
        
        # Only auto-create context engine if requested and available
        if context_engine is None and auto_create_context_engine and ContextRetrievalEngine:
            self.context_engine = ContextRetrievalEngine()
        else:
            self.context_engine = context_engine
        
        # LLM and Agent integration
        self.llm = llm
        self.agent_executor = agent_executor
        
        # Session management
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self._conversation_count = 0
        self._total_processing_time = 0.0
        
    async def process_message(self, message: str, user_id: str, session_id: str) -> ChatResponse:
        """
        Process a user message and return a chat response with performance optimization.
        
        Args:
            message: User's input message
            user_id: Unique user identifier
            session_id: Session identifier for conversation tracking
            
        Returns:
            ChatResponse with processed content and metadata
            
        Raises:
            ChatUIException: If processing fails
        """
        start_time = time.time()
        
        # Get performance optimization components
        response_cache = get_response_cache()
        resource_monitor = get_resource_monitor()
        
        try:
            # Initialize session if needed
            self._ensure_session(user_id, session_id)
            
            # Generate context hash for caching
            context_hash = self._generate_context_hash(message, user_id, session_id)
            
            # Check response cache first
            cached_response = response_cache.get_response(message, context_hash)
            if cached_response:
                # Update timestamp for cached response
                cached_response.timestamp = datetime.now()
                cached_response.ui_hints["cached"] = True
                return cached_response
            
            # Track conversation memory usage
            estimated_memory = self._estimate_conversation_memory(message, session_id)
            if not resource_monitor.track_conversation_memory(session_id, estimated_memory):
                # Memory limit exceeded, use simplified processing
                return await self._process_simplified_message(message, user_id, session_id)
            
            # Get conversation context using integrated memory layer
            context = await self._get_context_with_memory_integration(message, user_id)
            
            # Process with tool orchestrator if available
            tools_used = []
            tool_performance = {}
            if self.tool_orchestrator:
                try:
                    # Monitor tool execution with resource limits
                    with resource_monitor.monitor_tool_execution("ToolOrchestrator", timeout=30.0):
                        tool_recommendations = await self.tool_orchestrator.select_tools(message, context)
                        if tool_recommendations:
                            tool_names = [rec.tool_name for rec in tool_recommendations]
                            tool_results = await self.tool_orchestrator.execute_tools(
                                tool_names, message, {"context": context}
                            )
                            tools_used = [result.tool_name for result in tool_results if result.success]
                            
                            # Track tool performance
                            for result in tool_results:
                                tool_performance[result.tool_name] = {
                                    'success': result.success,
                                    'execution_time': result.execution_time,
                                    'error': result.error_message
                                }
                except Exception as e:
                    # Log error but continue with basic response
                    print(f"Tool orchestration failed: {e}")
            
            # Generate response content
            response_content = self._generate_response_content(message, context, tools_used)
            
            # Calculate confidence score based on context and tools
            confidence_score = self._calculate_confidence_score(context, tools_used, tool_performance)
            
            # Create chat response
            execution_time = time.time() - start_time
            response = ChatResponse(
                content=response_content,
                content_type=self._determine_content_type(response_content),
                tools_used=tools_used,
                context_used=[entry.source for entry in context],
                confidence_score=confidence_score,
                execution_time=execution_time,
                ui_hints={
                    "session_id": session_id,
                    "context_count": len(context),
                    "tools_count": len(tools_used),
                    "cached": False
                },
                timestamp=datetime.now()
            )
            
            # Store conversation in memory layer
            await self._store_conversation_in_memory(
                user_id, session_id, message, response, tools_used, tool_performance, context
            )
            
            # Update session state
            self._update_session_state(user_id, session_id, message, response)
            
            # Update performance tracking
            self._conversation_count += 1
            self._total_processing_time += execution_time
            
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_response = ChatResponse(
                content=f"I encountered an error processing your message: {str(e)}",
                content_type=ContentType.ERROR_MESSAGE,
                execution_time=execution_time,
                ui_hints={"error": True, "session_id": session_id, "error_type": type(e).__name__}
            )
            
            # Still try to store the error for learning
            try:
                await self._store_conversation_in_memory(
                    user_id, session_id, message, error_response, [], {}, []
                )
            except:
                pass  # Don't fail on storage error
            
            return error_response
    
    async def get_conversation_context(self, user_id: str, limit: int = 10) -> List[ContextEntry]:
        """
        Get conversation context for a user using integrated memory layer.
        
        Args:
            user_id: User identifier
            limit: Maximum number of context entries
            
        Returns:
            List of context entries
        """
        try:
            # Try context retriever first (intelligent chat component)
            if self.context_retriever:
                return await self.context_retriever.get_relevant_context("", user_id, limit)
            
            # Fallback to memory layer manager
            if self.memory_manager:
                memory_contexts = self.memory_manager.retrieve_context("", user_id, limit)
                return self._convert_memory_contexts_to_context_entries(memory_contexts)
            
            # Fallback to context engine
            if self.context_engine:
                engine_contexts = self.context_engine.get_relevant_context("", user_id, limit=limit)
                return self._convert_engine_contexts_to_context_entries(engine_contexts)
            
            return []
            
        except Exception as e:
            print(f"Context retrieval failed: {e}")
            return []
    
    def update_ui_state(self, response: ChatResponse) -> UIState:
        """
        Update UI state based on response.
        
        Args:
            response: Chat response to generate UI state for
            
        Returns:
            UIState with appropriate indicators and elements
        """
        ui_state = UIState()
        
        # Add loading indicators for active tools
        for tool_name in response.tools_used:
            indicator = LoadingIndicator(
                tool_name=tool_name,
                state=LoadingState.COMPLETED,
                progress=1.0,
                message=f"{tool_name} completed"
            )
            ui_state.loading_indicators.append(indicator)
        
        # Add error states if needed
        if response.content_type == ContentType.ERROR_MESSAGE:
            error_state = ErrorState(
                error_type="processing_error",
                message="Failed to process message",
                severity=ErrorSeverity.ERROR,
                recovery_actions=["retry", "simplify_query"]
            )
            ui_state.error_states.append(error_state)
        
        return ui_state
    
    def _ensure_session(self, user_id: str, session_id: str) -> None:
        """Ensure session exists in active sessions."""
        session_key = f"{user_id}:{session_id}"
        if session_key not in self._active_sessions:
            self._active_sessions[session_key] = {
                "user_id": user_id,
                "session_id": session_id,
                "created_at": datetime.now(),
                "message_count": 0,
                "last_activity": datetime.now()
            }
    
    async def _get_context_with_memory_integration(self, message: str, user_id: str) -> List[ContextEntry]:
        """Get context using integrated memory layer with fallbacks."""
        try:
            # Try intelligent context retriever first
            if self.context_retriever:
                return await self.context_retriever.get_relevant_context(message, user_id)
            
            # Fallback to context engine
            if self.context_engine:
                engine_contexts = self.context_engine.get_relevant_context(message, user_id, limit=10)
                return self._convert_engine_contexts_to_context_entries(engine_contexts)
            
            # Fallback to memory manager
            if self.memory_manager:
                memory_contexts = self.memory_manager.retrieve_context(message, user_id, 10)
                return self._convert_memory_contexts_to_context_entries(memory_contexts)
            
            return []
            
        except Exception as e:
            print(f"Context retrieval failed: {e}")
            return []
    
    def _convert_memory_contexts_to_context_entries(self, memory_contexts: List) -> List[ContextEntry]:
        """Convert memory layer contexts to ContextEntry objects."""
        context_entries = []
        
        for ctx in memory_contexts:
            if hasattr(ctx, 'content'):  # ContextEntryDTO
                context_entries.append(ContextEntry(
                    content=ctx.content,
                    source=ctx.source,
                    relevance_score=ctx.relevance_score,
                    timestamp=ctx.timestamp,
                    context_type=ctx.context_type,
                    metadata=ctx.metadata
                ))
        
        return context_entries
    
    def _convert_engine_contexts_to_context_entries(self, engine_contexts: List) -> List[ContextEntry]:
        """Convert context engine contexts to ContextEntry objects."""
        context_entries = []
        
        for ctx in engine_contexts:
            if hasattr(ctx, 'content'):  # ContextEntryDTO
                context_entries.append(ContextEntry(
                    content=ctx.content,
                    source=ctx.source,
                    relevance_score=ctx.relevance_score,
                    timestamp=ctx.timestamp,
                    context_type=ctx.context_type,
                    metadata=ctx.metadata
                ))
        
        return context_entries
    
    async def _store_conversation_in_memory(
        self, 
        user_id: str, 
        session_id: str, 
        message: str, 
        response: ChatResponse,
        tools_used: List[str],
        tool_performance: Dict[str, Any],
        context: List[ContextEntry]
    ) -> None:
        """Store conversation in memory layer for future context retrieval."""
        try:
            if not self.memory_manager:
                return
            
            # Create conversation entry
            conversation = ConversationEntryDTO(
                session_id=session_id,
                user_id=user_id,
                user_message=message,
                bot_response=response.content,
                tools_used=tools_used,
                tool_performance=tool_performance,
                context_used=[ctx.source for ctx in context],
                response_quality_score=response.confidence_score,
                timestamp=response.timestamp
            )
            
            # Store in memory layer
            success = self.memory_manager.store_conversation(conversation)
            if not success:
                print(f"Failed to store conversation for user {user_id}")
                
        except Exception as e:
            print(f"Error storing conversation in memory: {e}")
    
    def _calculate_confidence_score(
        self, 
        context: List[ContextEntry], 
        tools_used: List[str],
        tool_performance: Dict[str, Any]
    ) -> float:
        """Calculate confidence score based on available context and tool performance."""
        base_score = 0.5  # Base confidence
        
        # Boost for relevant context
        if context:
            avg_relevance = sum(ctx.relevance_score for ctx in context) / len(context)
            base_score += avg_relevance * 0.3
        
        # Boost for successful tool usage
        if tools_used:
            successful_tools = sum(1 for tool in tools_used 
                                 if tool_performance.get(tool, {}).get('success', False))
            tool_success_rate = successful_tools / len(tools_used) if tools_used else 0
            base_score += tool_success_rate * 0.2
        
        return min(base_score, 1.0)  # Cap at 1.0
    
    def _determine_content_type(self, content: str) -> ContentType:
        """Determine content type based on response content."""
        if not content:
            return ContentType.PLAIN_TEXT
        
        content_lower = content.lower()
        
        # Check for error indicators
        if any(indicator in content_lower for indicator in ['error:', 'failed', 'exception']):
            return ContentType.ERROR_MESSAGE
        
        # Check for code blocks
        if '```' in content:
            return ContentType.CODE_BLOCK
        
        # Check for JSON
        if content.strip().startswith('{') and content.strip().endswith('}'):
            return ContentType.JSON
        
        # Check for markdown
        if any(marker in content for marker in ['#', '**', '*', '`']):
            return ContentType.MARKDOWN
        
        return ContentType.PLAIN_TEXT
    
    def _generate_response_content(
        self, 
        message: str, 
        context: List[ContextEntry], 
        tools_used: List[str]
    ) -> str:
        """Generate helpful response content using LLM and tools when available."""
        
        # Try to use LLM and agent executor for intelligent responses
        if self.agent_executor and self.llm:
            try:
                # Build chat history from context
                chat_history = []
                for ctx in context:
                    if hasattr(ctx, 'context_type'):
                        if ctx.context_type == "user_message":
                            from langchain_core.messages import HumanMessage
                            chat_history.append(HumanMessage(content=ctx.content))
                        elif ctx.context_type == "bot_response":
                            from langchain_core.messages import AIMessage
                            chat_history.append(AIMessage(content=ctx.content))
                
                # Use agent executor to get intelligent response
                agent_input = {
                    "query": message,
                    "chat_history": chat_history
                }
                
                response = self.agent_executor.invoke(agent_input)
                
                if response and 'output' in response:
                    response_content = response['output']
                    
                    # Clean up structured response format if present
                    if 'summary:' in response_content.lower():
                        lines = response_content.split('\n')
                        for line in lines:
                            if line.lower().startswith('summary:'):
                                return line.split(':', 1)[1].strip()
                    
                    return response_content
                    
            except Exception as e:
                print(f"LLM/Agent execution failed: {e}")
                # Fall back to context-based or fallback responses
        
        # Check if we have real context (not mock) to provide a meaningful response
        if context and not any(ctx.metadata.get("mock", False) for ctx in context):
            # Use the most relevant context entry as the primary response
            primary_context = context[0]  # Highest relevance score
            response = primary_context.content
            
            # If we have additional relevant context, incorporate it
            if len(context) > 1:
                additional_info = []
                for ctx in context[1:3]:  # Use up to 2 additional contexts
                    if ctx.relevance_score > 0.7:  # Only high-relevance additional info
                        additional_info.append(ctx.content)
                
                if additional_info:
                    response += "\n\nAdditional information:\n" + "\n".join(additional_info)
            
            return response
        
        # If no real context but tools were used, provide a basic helpful response
        if tools_used:
            if "SupportKnowledgeBase" in tools_used:
                return "I've searched our support knowledge base for information about your query. Let me provide you with the most relevant information I found."
            elif "ContextRetriever" in tools_used:
                return "I've searched our knowledge base for information related to your question. Here's what I found that might help."
            elif "BTWebsiteSearch" in tools_used:
                return "I've checked our latest information from BT's website to provide you with current details."
            else:
                return "I've used our available resources to find information that can help with your query."
        
        # Fallback response for common queries without context
        message_lower = message.lower()
        
        # Check for specific billing/payment queries first (more specific than general 'help')
        if any(word in message_lower for word in ['bill', 'payment', 'invoice', 'charge', 'cost', 'price']):
            return "I can help you with billing and account-related questions. You can view and manage your bills through your online account, set up direct debit payments, or contact our billing team directly. If you're experiencing issues with payments or have questions about charges, I can guide you to the right resources."
        
        elif any(word in message_lower for word in ['broadband', 'internet', 'connection', 'wifi']):
            return "I understand you're having issues with your broadband connection. Let me help you troubleshoot this. First, please check if all cables are securely connected and try restarting your router by unplugging it for 30 seconds, then plugging it back in. If the issue persists, there might be a service outage in your area or a technical issue that requires further investigation."
        
        elif any(word in message_lower for word in ['upgrade', 'plan', 'package']):
            return "I can help you with upgrading your plan. To provide you with the best upgrade options, I'll need to check your current package and available plans in your area. You can upgrade your plan through your online account, by calling our customer service team, or I can guide you through the available options."
        
        elif any(word in message_lower for word in ['support', 'help', 'hours']):
            return "Our customer support team is available to help you. You can reach us through multiple channels: phone support, online chat, or through your online account. Our support hours vary by service type, and I can provide specific hours for the type of support you need."
        
        else:
            return "I'm here to help you with your query. Could you please provide a bit more detail about what you need assistance with? I can help with broadband issues, plan upgrades, billing questions, technical support, and general account management."
    
    def _update_session_state(
        self, 
        user_id: str, 
        session_id: str, 
        message: str, 
        response: ChatResponse
    ) -> None:
        """Update session state with new interaction."""
        session_key = f"{user_id}:{session_id}"
        if session_key in self._active_sessions:
            session = self._active_sessions[session_key]
            session["message_count"] += 1
            session["last_activity"] = datetime.now()
            session["last_message"] = message
            session["last_response"] = response.content
            session["total_processing_time"] = session.get("total_processing_time", 0.0) + response.execution_time
            session["tools_used_count"] = session.get("tools_used_count", 0) + len(response.tools_used)
    
    def get_session_stats(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Get statistics for a specific session."""
        session_key = f"{user_id}:{session_id}"
        session = self._active_sessions.get(session_key, {})
        
        return {
            "message_count": session.get("message_count", 0),
            "total_processing_time": session.get("total_processing_time", 0.0),
            "tools_used_count": session.get("tools_used_count", 0),
            "created_at": session.get("created_at"),
            "last_activity": session.get("last_activity"),
            "avg_processing_time": (
                session.get("total_processing_time", 0.0) / session.get("message_count", 1)
                if session.get("message_count", 0) > 0 else 0.0
            )
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global ChatManager statistics."""
        return {
            "total_conversations": self._conversation_count,
            "total_processing_time": self._total_processing_time,
            "active_sessions": len(self._active_sessions),
            "avg_processing_time": (
                self._total_processing_time / self._conversation_count 
                if self._conversation_count > 0 else 0.0
            ),
            "memory_integration_enabled": self.memory_manager is not None,
            "context_engine_enabled": self.context_engine is not None
        }
    
    async def cleanup_inactive_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up inactive sessions older than max_age_hours."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        inactive_sessions = []
        
        for session_key, session_data in self._active_sessions.items():
            last_activity = session_data.get("last_activity", session_data.get("created_at"))
            if last_activity and last_activity < cutoff_time:
                inactive_sessions.append(session_key)
        
        for session_key in inactive_sessions:
            del self._active_sessions[session_key]
        
        return len(inactive_sessions)    

    # Performance optimization helper methods
    
    def _generate_context_hash(self, message: str, user_id: str, session_id: str) -> str:
        """Generate hash for context-based caching."""
        # Include recent conversation context in hash
        session_key = f"{user_id}:{session_id}"
        session_data = self._active_sessions.get(session_key, {})
        
        # Create hash input from message and recent context
        hash_input = f"{message}:{user_id}:{session_data.get('last_message', '')}:{session_data.get('message_count', 0)}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _estimate_conversation_memory(self, message: str, session_id: str) -> float:
        """Estimate memory usage for conversation in MB."""
        # Base memory for message
        message_memory = len(message.encode('utf-8')) / (1024 * 1024)  # Convert to MB
        
        # Add estimated context memory
        context_memory = 0.5  # Base context overhead
        
        # Add session-specific memory
        session_memory = 0.1  # Base session overhead
        
        return message_memory + context_memory + session_memory
    
    async def _process_simplified_message(self, message: str, user_id: str, session_id: str) -> ChatResponse:
        """Process message with simplified logic when resources are constrained."""
        start_time = time.time()
        
        # Generate basic response without heavy processing
        response_content = f"I understand you're asking: '{message}'. Due to high system load, I'm providing a simplified response. Please try again in a moment for a more comprehensive answer."
        
        execution_time = time.time() - start_time
        
        return ChatResponse(
            content=response_content,
            content_type=ContentType.PLAIN_TEXT,
            tools_used=[],
            context_used=[],
            confidence_score=0.3,  # Low confidence for simplified response
            execution_time=execution_time,
            ui_hints={
                "session_id": session_id,
                "simplified": True,
                "reason": "resource_constraints"
            },
            timestamp=datetime.now()
        )
    
    def _cache_response_if_appropriate(self, message: str, context_hash: str, response: ChatResponse) -> None:
        """Cache response if it meets caching criteria."""
        # Only cache successful responses with reasonable confidence
        if (response.confidence_score > 0.6 and 
            response.execution_time > 1.0 and  # Only cache expensive responses
            len(response.tools_used) > 0):  # Only cache tool-assisted responses
            
            response_cache = get_response_cache()
            response_cache.cache_response(message, context_hash, response)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance-related statistics."""
        resource_monitor = get_resource_monitor()
        performance_cache = get_performance_cache()
        
        return {
            "cache_stats": performance_cache.get_stats(),
            "resource_usage": resource_monitor.get_current_usage(),
            "conversation_memory": resource_monitor.get_conversation_memory_usage(),
            "system_stats": resource_monitor.get_system_stats()
        }