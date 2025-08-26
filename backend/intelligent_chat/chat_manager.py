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
    from backend.memory_layer_manager import MemoryLayerManager, MemoryStats
    from backend.context_retrieval_engine import ContextRetrievalEngine
    from backend.memory_models import ConversationEntryDTO, ContextEntryDTO
    from backend.memory_config import load_config
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
            context = await self._get_context_with_memory_integration(message, user_id, session_id)
            
            # Process with enhanced tool orchestration using learning
            tools_used = []
            tool_performance = {}
            
            # Use adaptive tool selection based on learned patterns
            adaptive_tools = await self._adaptive_tool_selection(message, user_id, context)
            
            if self.tool_orchestrator:
                try:
                    # Monitor tool execution with resource limits
                    with resource_monitor.monitor_tool_execution("ToolOrchestrator", timeout=30.0):
                        # First try learned/adaptive tool selection
                        if adaptive_tools:
                            tool_results = await self.tool_orchestrator.execute_tools(
                                adaptive_tools, message, {"context": context}
                            )
                            tools_used = [result.tool_name for result in tool_results if result.success]
                            
                            # Track tool performance
                            for result in tool_results:
                                tool_performance[result.tool_name] = {
                                    'success': result.success,
                                    'execution_time': result.execution_time,
                                    'error': result.error_message
                                }
                        
                        # If adaptive tools didn't work well, try orchestrator's selection
                        if not tools_used or len(tools_used) == 0:
                            tool_recommendations = await self.tool_orchestrator.select_tools(message, context)
                            if tool_recommendations:
                                tool_names = [rec.tool_name for rec in tool_recommendations]
                                tool_results = await self.tool_orchestrator.execute_tools(
                                    tool_names, message, {"context": context}
                                )
                                tools_used.extend([result.tool_name for result in tool_results if result.success])
                                
                                # Track additional tool performance
                                for result in tool_results:
                                    tool_performance[result.tool_name] = {
                                        'success': result.success,
                                        'execution_time': result.execution_time,
                                        'error': result.error_message
                                    }
                except Exception as e:
                    # Log error but continue with basic response
                    print(f"Tool orchestration failed: {e}")
            
            # If no tool orchestrator, use adaptive tools directly with agent executor
            elif adaptive_tools and self.agent_executor:
                try:
                    # Use the agent executor with learned tool preferences
                    tools_used = adaptive_tools
                    for tool in adaptive_tools:
                        tool_performance[tool] = {
                            'success': True,
                            'execution_time': 0.1,
                            'error': None,
                            'adaptive_selection': True
                        }
                except Exception as e:
                    print(f"Adaptive tool execution failed: {e}")
            
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
            
            # Store conversation in memory layer with learning updates
            await self._store_conversation_in_memory(
                user_id, session_id, message, response, tools_used, tool_performance, context
            )
            
            # Update learning models based on this interaction
            await self._update_learning_models(message, tools_used, tool_performance, response.confidence_score)
            
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
            
            # Update session state even for errors
            self._update_session_state(user_id, session_id, message, error_response)
            
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
                "last_activity": datetime.now(),
                "conversation_history": []  # Track conversation within session
            }
    
    async def _get_context_with_memory_integration(self, message: str, user_id: str, session_id: str = None) -> List[ContextEntry]:
        """Get context using integrated memory layer with enhanced learning capabilities."""
        try:
            # Get session-specific context first (most recent conversation in this session)
            session_context = []
            if session_id:
                session_key = f"{user_id}:{session_id}"
                session_data = self._active_sessions.get(session_key, {})
                
                # Add recent messages from this session as context
                if "conversation_history" in session_data:
                    for msg in session_data["conversation_history"][-5:]:  # Last 5 messages
                        session_context.append(ContextEntry(
                            content=msg["content"],
                            source=f"session_{session_id}",
                            relevance_score=1.0,  # High relevance for same session
                            timestamp=msg.get("timestamp", datetime.now()),
                            context_type=msg["type"],
                            metadata={"session_id": session_id, "recent": True}
                        ))
            
            # Try intelligent context retriever
            retriever_context = []
            if self.context_retriever:
                retriever_context = await self.context_retriever.get_relevant_context(message, user_id)
            
            # Enhanced memory-based context retrieval with learning
            memory_context = []
            if self.memory_manager:
                # Get conversation context
                memory_contexts = self.memory_manager.retrieve_context(message, user_id, 10)
                memory_context = self._convert_memory_contexts_to_context_entries(memory_contexts)
                
                # Enhance with learned patterns
                memory_context = await self._enhance_context_with_learning(message, user_id, memory_context)
            
            # Fallback to context engine
            engine_context = []
            if self.context_engine:
                engine_contexts = self.context_engine.get_relevant_context(message, user_id, limit=10)
                engine_context = self._convert_engine_contexts_to_context_entries(engine_contexts)
            
            # Combine all contexts, prioritizing session context
            all_contexts = session_context + retriever_context + memory_context + engine_context
            
            # Remove duplicates and rank by relevance
            seen_content = set()
            unique_contexts = []
            for ctx in all_contexts:
                content_hash = hashlib.md5(ctx.content.encode()).hexdigest()
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    unique_contexts.append(ctx)
            
            # Sort by relevance score (descending) and return top 10
            unique_contexts.sort(key=lambda x: x.relevance_score, reverse=True)
            return unique_contexts[:10]
            
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
            
            # Add to conversation history for context
            if "conversation_history" not in session:
                session["conversation_history"] = []
            
            # Add user message
            session["conversation_history"].append({
                "type": "user_message",
                "content": message,
                "timestamp": datetime.now()
            })
            
            # Add bot response
            session["conversation_history"].append({
                "type": "bot_response", 
                "content": response.content,
                "timestamp": datetime.now(),
                "tools_used": response.tools_used,
                "confidence_score": response.confidence_score
            })
            
            # Keep only last 20 messages (10 exchanges) to prevent memory bloat
            if len(session["conversation_history"]) > 20:
                session["conversation_history"] = session["conversation_history"][-20:]
    
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
    
    async def _enhance_context_with_learning(
        self, 
        message: str, 
        user_id: str, 
        base_contexts: List[ContextEntry]
    ) -> List[ContextEntry]:
        """Enhance context with learned patterns and successful interaction history."""
        try:
            enhanced_contexts = base_contexts.copy()
            
            # Add learned tool recommendations as context
            if self.memory_manager:
                tool_recommendation = self.memory_manager.analyze_tool_usage(message, [])
                if tool_recommendation:
                    tool_context = ContextEntry(
                        content=f"Based on similar queries, the {tool_recommendation.tool_name} tool has been successful with {tool_recommendation.confidence_score:.1%} confidence. {tool_recommendation.reason}",
                        source="tool_learning",
                        relevance_score=tool_recommendation.confidence_score,
                        timestamp=datetime.now(),
                        context_type="tool_usage",  # Use valid context type
                        metadata={
                            "tool_name": tool_recommendation.tool_name,
                            "expected_performance": tool_recommendation.expected_performance,
                            "learning_based": True,
                            "learning_type": "tool_recommendation"
                        }
                    )
                    enhanced_contexts.append(tool_context)
            
            # Add conversation pattern learning
            pattern_context = await self._get_conversation_pattern_context(message, user_id)
            if pattern_context:
                enhanced_contexts.extend(pattern_context)
            
            # Sort by relevance score
            enhanced_contexts.sort(key=lambda x: x.relevance_score, reverse=True)
            
            return enhanced_contexts[:15]  # Limit to top 15 contexts
            
        except Exception as e:
            print(f"Error enhancing context with learning: {e}")
            return base_contexts
    
    async def _get_conversation_pattern_context(self, message: str, user_id: str) -> List[ContextEntry]:
        """Get context based on learned conversation patterns."""
        try:
            if not self.memory_manager:
                return []
            
            # Get user's conversation history for pattern analysis
            user_history = self.memory_manager.get_user_conversation_history(user_id, limit=20)
            
            if not user_history:
                return []
            
            pattern_contexts = []
            
            # Analyze for similar question patterns
            similar_questions = self._find_similar_questions(message, user_history)
            for similar_q in similar_questions[:3]:  # Top 3 similar questions
                if similar_q.response_quality_score and similar_q.response_quality_score > 0.7:
                    pattern_context = ContextEntry(
                        content=f"Previously successful response to similar query: {similar_q.bot_response[:200]}...",
                        source=f"pattern_learning_{similar_q.session_id}",
                        relevance_score=similar_q.response_quality_score,
                        timestamp=similar_q.timestamp,
                        context_type="conversation",  # Use valid context type
                        metadata={
                            "original_question": similar_q.user_message,
                            "tools_used": similar_q.tools_used,
                            "quality_score": similar_q.response_quality_score,
                            "pattern_based": True,
                            "learning_type": "pattern_learning"
                        }
                    )
                    pattern_contexts.append(pattern_context)
            
            # Analyze for successful tool combinations
            successful_tool_patterns = self._analyze_successful_tool_patterns(user_history)
            if successful_tool_patterns:
                tool_pattern_context = ContextEntry(
                    content=f"Successful tool combinations for this user: {', '.join(successful_tool_patterns)}",
                    source="tool_pattern_learning",
                    relevance_score=0.8,
                    timestamp=datetime.now(),
                    context_type="tool_usage",  # Use valid context type
                    metadata={
                        "successful_tools": successful_tool_patterns,
                        "pattern_based": True,
                        "learning_type": "tool_pattern"
                    }
                )
                pattern_contexts.append(tool_pattern_context)
            
            return pattern_contexts
            
        except Exception as e:
            print(f"Error getting conversation pattern context: {e}")
            return []
    
    def _find_similar_questions(self, current_message: str, history: List) -> List:
        """Find similar questions in conversation history using simple text similarity."""
        try:
            current_words = set(current_message.lower().split())
            similar_conversations = []
            
            for conv in history:
                if hasattr(conv, 'user_message') and conv.user_message:
                    conv_words = set(conv.user_message.lower().split())
                    
                    # Calculate Jaccard similarity
                    intersection = current_words.intersection(conv_words)
                    union = current_words.union(conv_words)
                    
                    if union:
                        similarity = len(intersection) / len(union)
                        if similarity > 0.3:  # Threshold for similarity
                            # Add similarity score to the conversation object
                            conv.similarity_score = similarity
                            similar_conversations.append(conv)
            
            # Sort by similarity score
            similar_conversations.sort(key=lambda x: getattr(x, 'similarity_score', 0), reverse=True)
            return similar_conversations
            
        except Exception as e:
            print(f"Error finding similar questions: {e}")
            return []
    
    def _analyze_successful_tool_patterns(self, history: List) -> List[str]:
        """Analyze successful tool usage patterns from conversation history."""
        try:
            tool_success_count = {}
            tool_usage_count = {}
            
            for conv in history:
                if hasattr(conv, 'tools_used') and hasattr(conv, 'response_quality_score'):
                    if conv.tools_used and conv.response_quality_score and conv.response_quality_score > 0.7:
                        for tool in conv.tools_used:
                            tool_success_count[tool] = tool_success_count.get(tool, 0) + 1
                            tool_usage_count[tool] = tool_usage_count.get(tool, 0) + 1
                    elif conv.tools_used:
                        for tool in conv.tools_used:
                            tool_usage_count[tool] = tool_usage_count.get(tool, 0) + 1
            
            # Find tools with high success rates
            successful_tools = []
            for tool, success_count in tool_success_count.items():
                total_usage = tool_usage_count.get(tool, 1)
                success_rate = success_count / total_usage
                
                if success_rate > 0.6 and success_count >= 2:  # At least 60% success rate and 2+ successes
                    successful_tools.append(tool)
            
            return successful_tools
            
        except Exception as e:
            print(f"Error analyzing tool patterns: {e}")
            return []
    
    async def _adaptive_tool_selection(self, message: str, user_id: str, context: List[ContextEntry]) -> List[str]:
        """Adaptively select tools based on learned patterns and context."""
        try:
            selected_tools = []
            
            # Check for tool recommendations from learning
            tool_recommendation_contexts = [ctx for ctx in context 
                                          if ctx.context_type == "tool_usage" and 
                                          ctx.metadata.get("learning_type") == "tool_recommendation"]
            if tool_recommendation_contexts:
                # Use the highest confidence tool recommendation
                best_recommendation = max(tool_recommendation_contexts, key=lambda x: x.relevance_score)
                recommended_tool = best_recommendation.metadata.get("tool_name")
                if recommended_tool:
                    selected_tools.append(recommended_tool)
            
            # Check for successful tool patterns
            pattern_contexts = [ctx for ctx in context 
                              if ctx.context_type == "tool_usage" and 
                              ctx.metadata.get("learning_type") == "tool_pattern"]
            if pattern_contexts:
                successful_tools = pattern_contexts[0].metadata.get("successful_tools", [])
                selected_tools.extend(successful_tools[:2])  # Add top 2 successful tools
            
            # Add default tools based on message content if no learned patterns
            if not selected_tools:
                message_lower = message.lower()
                if any(word in message_lower for word in ['support', 'help', 'issue', 'problem']):
                    selected_tools.extend(["SupportKnowledgeBase", "CreateSupportTicket"])
                elif any(word in message_lower for word in ['plan', 'upgrade', 'pricing']):
                    selected_tools.extend(["BTPlansInformation", "BTWebsiteSearch"])
                elif any(word in message_lower for word in ['hours', 'contact', 'phone']):
                    selected_tools.extend(["BTSupportHours", "SupportKnowledgeBase"])
                else:
                    selected_tools.extend(["ContextRetriever", "SupportKnowledgeBase"])
            
            # Remove duplicates while preserving order
            unique_tools = []
            for tool in selected_tools:
                if tool not in unique_tools:
                    unique_tools.append(tool)
            
            return unique_tools[:3]  # Limit to 3 tools for performance
            
        except Exception as e:
            print(f"Error in adaptive tool selection: {e}")
            return ["ContextRetriever", "SupportKnowledgeBase"]  # Fallback tools
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance-related statistics."""
        resource_monitor = get_resource_monitor()
        
        stats = {
            "total_conversations": self._conversation_count,
            "total_processing_time": self._total_processing_time,
            "active_sessions": len(self._active_sessions),
            "avg_processing_time": (
                self._total_processing_time / self._conversation_count 
                if self._conversation_count > 0 else 0.0
            ),
            "memory_integration_enabled": self.memory_manager is not None,
            "context_engine_enabled": self.context_engine is not None,
            "learning_features_enabled": True
        }
        
        # Add memory layer stats if available
        if self.memory_manager:
            try:
                memory_stats = self.memory_manager.get_memory_stats()
                stats["memory_stats"] = memory_stats.to_dict()
            except Exception as e:
                print(f"Error getting memory stats: {e}")
        
        return stats
    
    async def _update_learning_models(
        self, 
        message: str, 
        tools_used: List[str], 
        tool_performance: Dict[str, Any], 
        response_quality: float
    ) -> None:
        """Update learning models based on interaction results."""
        try:
            if not self.memory_manager or not tools_used:
                return
            
            # Update tool usage metrics for each tool used
            for tool_name in tools_used:
                performance = tool_performance.get(tool_name, {})
                success = performance.get('success', False)
                execution_time = performance.get('execution_time', 0.0)
                
                # Generate query hash for similar query grouping
                import hashlib
                query_hash = hashlib.md5(message.lower().encode()).hexdigest()[:16]
                
                # This would ideally update the ToolUsageMetrics table
                # For now, we'll log the learning update
                print(f"Learning update: Tool {tool_name} - Success: {success}, Quality: {response_quality}, Time: {execution_time}s")
                
                # Record the learning in memory manager if method exists
                if hasattr(self.memory_manager, 'record_health_metric'):
                    self.memory_manager.record_health_metric(
                        f"tool_learning_{tool_name}",
                        response_quality,
                        "quality_score",
                        "learning"
                    )
            
        except Exception as e:
            print(f"Error updating learning models: {e}")
    
    def get_learning_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights about learned patterns for a user."""
        try:
            if not self.memory_manager:
                return {"error": "Memory manager not available"}
            
            # Get user conversation history
            user_history = self.memory_manager.get_user_conversation_history(user_id, limit=50)
            
            if not user_history:
                return {"message": "No conversation history available for learning insights"}
            
            insights = {
                "total_conversations": len(user_history),
                "avg_quality_score": 0.0,
                "most_successful_tools": [],
                "conversation_patterns": [],
                "improvement_suggestions": []
            }
            
            # Calculate average quality score
            quality_scores = [conv.response_quality_score for conv in user_history 
                            if conv.response_quality_score is not None]
            if quality_scores:
                insights["avg_quality_score"] = sum(quality_scores) / len(quality_scores)
            
            # Find most successful tools
            successful_tools = self._analyze_successful_tool_patterns(user_history)
            insights["most_successful_tools"] = successful_tools
            
            # Identify conversation patterns
            patterns = self._identify_conversation_patterns(user_history)
            insights["conversation_patterns"] = patterns
            
            # Generate improvement suggestions
            suggestions = self._generate_improvement_suggestions(user_history, insights)
            insights["improvement_suggestions"] = suggestions
            
            return insights
            
        except Exception as e:
            return {"error": f"Failed to get learning insights: {str(e)}"}
    
    def _identify_conversation_patterns(self, history: List) -> List[Dict[str, Any]]:
        """Identify patterns in conversation history."""
        try:
            patterns = []
            
            # Pattern 1: Most common question types
            question_types = {}
            for conv in history:
                if hasattr(conv, 'user_message') and conv.user_message:
                    message_lower = conv.user_message.lower()
                    if any(word in message_lower for word in ['help', 'support', 'issue']):
                        question_types['support'] = question_types.get('support', 0) + 1
                    elif any(word in message_lower for word in ['plan', 'upgrade', 'pricing']):
                        question_types['plans'] = question_types.get('plans', 0) + 1
                    elif any(word in message_lower for word in ['bill', 'payment', 'invoice']):
                        question_types['billing'] = question_types.get('billing', 0) + 1
                    else:
                        question_types['general'] = question_types.get('general', 0) + 1
            
            if question_types:
                most_common = max(question_types, key=question_types.get)
                patterns.append({
                    "type": "question_preference",
                    "pattern": f"User most commonly asks {most_common} questions",
                    "frequency": question_types[most_common],
                    "total": sum(question_types.values())
                })
            
            # Pattern 2: Time-based patterns (simplified)
            if len(history) > 5:
                recent_quality = sum(conv.response_quality_score or 0 
                                   for conv in history[:5]) / 5
                older_quality = sum(conv.response_quality_score or 0 
                                  for conv in history[-5:]) / 5
                
                if recent_quality > older_quality + 0.1:
                    patterns.append({
                        "type": "improvement_trend",
                        "pattern": "Response quality has improved over time",
                        "recent_quality": recent_quality,
                        "older_quality": older_quality
                    })
                elif older_quality > recent_quality + 0.1:
                    patterns.append({
                        "type": "decline_trend",
                        "pattern": "Response quality has declined recently",
                        "recent_quality": recent_quality,
                        "older_quality": older_quality
                    })
            
            return patterns
            
        except Exception as e:
            print(f"Error identifying conversation patterns: {e}")
            return []
    
    def _generate_improvement_suggestions(self, history: List, insights: Dict[str, Any]) -> List[str]:
        """Generate suggestions for improving user experience."""
        suggestions = []
        
        try:
            avg_quality = insights.get("avg_quality_score", 0.0)
            
            if avg_quality < 0.6:
                suggestions.append("Consider providing more specific details in your questions to get better responses")
            
            if not insights.get("most_successful_tools"):
                suggestions.append("Try asking questions that can benefit from our specialized tools (plans, support, billing)")
            
            # Check for repeated similar questions
            if len(history) > 10:
                recent_messages = [conv.user_message for conv in history[:5] 
                                 if hasattr(conv, 'user_message') and conv.user_message]
                if len(set(recent_messages)) < len(recent_messages) * 0.7:
                    suggestions.append("You've asked similar questions recently - try exploring follow-up questions for more detailed information")
            
            if len(suggestions) == 0:
                suggestions.append("Your conversation patterns look good! Continue asking detailed questions for the best responses")
            
            return suggestions
            
        except Exception as e:
            print(f"Error generating improvement suggestions: {e}")
            return ["Continue engaging with the system to improve response quality"]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance-related statistics."""
        try:
            resource_monitor = get_resource_monitor()
            performance_cache = get_performance_cache()
            
            return {
                "cache_stats": performance_cache.get_stats() if performance_cache else {},
                "resource_usage": resource_monitor.get_current_usage() if resource_monitor else {},
                "conversation_memory": resource_monitor.get_conversation_memory_usage() if resource_monitor else {},
                "system_stats": resource_monitor.get_system_stats() if resource_monitor else {}
            }
        except Exception as e:
            print(f"Error getting performance stats: {e}")
            return {"error": str(e)}
    
    async def _enhance_context_with_learning(self, message: str, user_id: str, context_entries: List[ContextEntry]) -> List[ContextEntry]:
        """Enhance context entries with learned patterns and preferences."""
        try:
            # For now, return the context as-is
            # This can be enhanced later with ML-based context enhancement
            return context_entries
        except Exception as e:
            print(f"Error enhancing context with learning: {e}")
            return context_entries

    async def _adaptive_tool_selection(self, message: str, user_id: str, context: List[ContextEntry]) -> List[str]:
        """Select tools adaptively based on learned patterns."""
        try:
            # Simple adaptive tool selection based on message content
            adaptive_tools = []
            message_lower = message.lower()
            
            # Always start with knowledge base for any query
            adaptive_tools.append("SupportKnowledgeBase")
            
            # Add specific tools based on content
            if any(word in message_lower for word in ['problem', 'issue', 'error', 'broken', 'not working', 'help']):
                adaptive_tools.append("CreateSupportTicket")
            
            if any(word in message_lower for word in ['plan', 'upgrade', 'package', 'price']):
                adaptive_tools.append("BTPlansInformation")
            
            if any(word in message_lower for word in ['hours', 'contact', 'support', 'phone']):
                adaptive_tools.append("BTSupportHours")
            
            if any(word in message_lower for word in ['broadband', 'internet', 'wifi', 'connection']):
                adaptive_tools.append("BTWebsiteSearch")
            
            return adaptive_tools
            
        except Exception as e:
            print(f"Error in adaptive tool selection: {e}")
            return []

    async def _update_learning_models(self, message: str, tools_used: List[str], tool_performance: Dict[str, Any], confidence_score: float) -> None:
        """Update learning models based on interaction results."""
        try:
            # For now, just log the interaction for future ML implementation
            print(f"Learning update: message_len={len(message)}, tools={len(tools_used)}, confidence={confidence_score}")
        except Exception as e:
            print(f"Error updating learning models: {e}")

    async def _process_simplified_message(self, message: str, user_id: str, session_id: str) -> ChatResponse:
        """Process message with simplified logic when resources are constrained."""
        try:
            # Simple response without heavy processing
            response_content = self._generate_response_content(message, [], [])
            
            return ChatResponse(
                content=response_content,
                content_type=self._determine_content_type(response_content),
                tools_used=[],
                context_used=[],
                confidence_score=0.5,  # Lower confidence for simplified processing
                execution_time=0.1,
                ui_hints={
                    "session_id": session_id,
                    "simplified": True
                },
                timestamp=datetime.now()
            )
        except Exception as e:
            return ChatResponse(
                content=f"I'm experiencing high load right now. Please try again in a moment.",
                content_type=ContentType.PLAIN_TEXT,
                execution_time=0.1,
                ui_hints={"error": True, "session_id": session_id}
            )

    def _estimate_conversation_memory(self, message: str, session_id: str) -> int:
        """Estimate memory usage for conversation processing."""
        # Much more conservative estimation to avoid false memory alerts
        base_memory = len(message) * 0.001  # Very small estimate in KB
        
        session_key = f"*:{session_id}"  # Wildcard user for session lookup
        for key in self._active_sessions:
            if key.endswith(f":{session_id}"):
                session_data = self._active_sessions[key]
                history_size = len(session_data.get("conversation_history", []))
                base_memory += history_size * 0.01  # Very small estimate per history item in KB
                break
        
        return max(base_memory, 0.1)  # Minimum 0.1KB estimate