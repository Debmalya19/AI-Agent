from dotenv import load_dotenv
from pydantic import BaseModel as PydanticBaseModel
from typing import Optional, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

import bcrypt
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import Tool
from backend.tools import (
    search_tool, wiki_tool, save_tool, bt_website_tool, 
    bt_support_hours_tool_instance, bt_plans_tool,
    intelligent_orchestrator_tool, context_memory, create_ticket_tool_instance
)
from backend.customer_db_tool import get_customer_orders
import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request, Response, status, Cookie, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
# Removed unused HTTPBasic imports
from fastapi.staticfiles import StaticFiles
import secrets
# Removed unused pandas import
from langchain_core.messages import HumanMessage, AIMessage
from langchain.schema import Document
from backend.database import SessionLocal, get_db, init_db
from backend.models import KnowledgeEntry, ChatHistory, SupportIntent, SupportResponse, User, UserSession
from backend.db_utils import search_knowledge_entries, get_knowledge_entries, save_chat_history, get_chat_history
from backend.enhanced_rag_orchestrator import search_with_priority
import logging
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
import hashlib
import time

# Memory layer imports
from backend.memory_layer_manager import MemoryLayerManager, MemoryStats, CleanupResult
from backend.memory_config import MemoryConfig, load_config
from backend.memory_models import ConversationEntry, ContextEntry, ToolRecommendation

# Intelligent chat UI imports
from backend.intelligent_chat.chat_manager import ChatManager
from backend.intelligent_chat.tool_orchestrator import ToolOrchestrator
from backend.intelligent_chat.context_retriever import ContextRetriever
from backend.intelligent_chat.response_renderer import ResponseRenderer
from backend.intelligent_chat.models import ChatResponse as IntelligentChatResponse, ContentType, UIState

# Ticket handling imports
from backend.ticket_chat_handler import TicketChatHandler

# Voice assistant imports
from backend.voice_api import voice_router

# Tool imports (moved from middle of file)
from backend.tools import set_shared_memory_manager

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_configuration():
    """Validate that all required configuration is present"""
    required_vars = []
    missing_vars = []
    
    # Check for required environment variables
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info("Configuration validation passed")

# Validate configuration on import
try:
    validate_configuration()
except Exception as e:
    logger.error(f"Configuration validation failed: {e}")
    # You can choose to raise the error or continue with warnings



# Setup Gemini LLM
llm = None
try:
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        logger.warning("GOOGLE_API_KEY not found. LLM functionality will be limited.")
        # Continue without LLM for now
    else:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.3,
            google_api_key=google_api_key
        )
        logger.info("Gemini LLM initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Gemini LLM: {e}")
    logger.warning("Continuing without LLM functionality")
    llm = None



# -------------------- 🔍 DATABASE-BACKED RAG SETUP -----------------------

# Define RAG tool function using database knowledge base
def rag_tool_func(query: str) -> str:
    """RAG tool using database knowledge base"""
    try:
        # Use the enhanced RAG orchestrator for database search
        results = search_with_priority(query, max_results=3)
        
        if not results:
            return "I couldn't find specific information about that in our knowledge base. Let me try searching for related information."
        
        # Format results in a user-friendly way
        if len(results) == 1:
            # Single result - return it directly
            return results[0]['content']
        else:
            # Multiple results - combine them intelligently
            formatted_results = []
            for i, result in enumerate(results):
                if i == 0:
                    # Primary result
                    formatted_results.append(result['content'])
                else:
                    # Additional helpful information
                    formatted_results.append(f"\n\nAdditional information:\n{result['content']}")
            
            return "\n\n".join(formatted_results)
        
    except Exception as e:
        logger.error(f"RAG tool error: {e}")
        return "I encountered an error while searching our knowledge base. Let me try a different approach to help you."

# Define exact knowledge lookup using database
def exact_knowledge_lookup(query: str) -> str:
    """Perform exact lookup in database knowledge base"""
    try:
        with SessionLocal() as db:
            # Search for exact matches in knowledge entries
            entries = search_knowledge_entries(db, query)
            
            if not entries:
                return ""
            
            # Return the most relevant entry
            best_match = entries[0]
            return best_match.content
            
    except Exception as e:
        logger.error(f"Exact knowledge lookup error: {e}")
        return ""

# Support knowledge tool using database
def support_knowledge_tool_func(query: str) -> str:
    """Fetch support response from the customer support knowledge base"""
    try:
        with SessionLocal() as db:
            # Search support intents and responses
            intents = db.query(SupportIntent).all()
            
            # First try exact intent matching
            for intent in intents:
                if intent.intent_name.lower() in query.lower():
                    response = db.query(SupportResponse).filter(
                        SupportResponse.intent_id == intent.intent_id
                    ).first()
                    
                    if response:
                        return response.response_text
            
            # If no exact match, try intelligent fuzzy matching with scoring
            query_lower = query.lower()
            query_words = query_lower.split()
            
            best_match = None
            best_score = 0
            
            for intent in intents:
                intent_lower = intent.intent_name.lower()
                score = 0
                
                # Exact word matches get high scores
                for word in query_words:
                    if word in intent_lower:
                        score += 0.5
                
                # Check for semantic matches (common synonyms)
                if 'upgrade' in query_lower and 'upgrade' in intent_lower:
                    score += 2.0
                elif 'upgrade' in query_lower and 'change' in intent_lower:
                    score += 1.5
                
                if 'plan' in query_lower and 'plan' in intent_lower:
                    score += 2.0
                elif 'plan' in query_lower and 'subscription' in intent_lower:
                    score += 1.5
                
                if 'support' in query_lower and 'support' in intent_lower:
                    score += 2.0
                elif 'support' in query_lower and 'customer' in intent_lower:
                    score += 1.0
                
                if 'hours' in query_lower and 'hours' in intent_lower:
                    score += 2.0
                
                # Check for change vs change_order confusion
                if 'change' in query_lower and 'change' in intent_lower:
                    if 'plan' in query_lower and 'plan' in intent_lower:
                        score += 3.0  # Exact match for change_plan
                    elif 'order' in query_lower and 'order' in intent_lower:
                        score += 3.0  # Exact match for change_order
                    else:
                        score += 1.0  # Generic change match
                
                # Update best match if this score is higher
                if score > best_score:
                    best_score = score
                    best_match = intent
            
            # Return the best match if score is high enough
            if best_match and best_score >= 1.5:
                response = db.query(SupportResponse).filter(
                    SupportResponse.intent_id == best_match.intent_id
                ).first()
                
                if response:
                    return response.response_text
            
            # If still no match, try searching knowledge entries
            entries = db.query(KnowledgeEntry).all()
            for entry in entries:
                if any(word in entry.title.lower() for word in query_lower.split()):
                    return entry.content
            
            return "I couldn't find specific support information for your query. Let me search our general knowledge base for more details."
            
    except Exception as e:
        logger.error(f"Support knowledge tool error: {e}")
        return "Error accessing support knowledge base."

# Create RAG tool
rag_tool = Tool.from_function(
    func=rag_tool_func,
    name="ContextRetriever",
    description="Use this tool to fetch relevant information from the database knowledge base using RAG."
)

# Create support knowledge tool
support_knowledge_tool = Tool.from_function(
    func=support_knowledge_tool_func,
    name="SupportKnowledgeBase",
    description="Use this tool to fetch customer support responses from the database knowledge base."
)

# ---------------------- 🤖 Agent Setup -----------------------

# Prompt template

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
          You are a highly professional, friendly, and knowledgeable customer support agent for a telecom company. Your mission is to provide comprehensive, accurate, and helpful answers using multiple information sources and tools with intelligent context understanding.

          **ENHANCED TOOL USAGE STRATEGY:**
          
          1. **Start with Knowledge Base**: Always use the ContextRetriever tool first to check our database knowledge base for relevant information.
          
          2. **Check Support Database**: Use the SupportKnowledgeBase tool to find specific support responses and intents.
          
          3. **Create Support Tickets**: When customers have issues, problems, complaints, or need human assistance, IMMEDIATELY use the CreateSupportTicket tool to create a support ticket. This includes technical problems, billing issues, service outages, or any situation requiring escalation.
          
          4. **Use Intelligent Orchestrator**: For complex queries, use the IntelligentToolOrchestrator which automatically combines multiple sources with context memory and smart tool selection.
          
          5. **BT-Specific Information**: For current BT services, plans, or support information, use the BTWebsiteSearch, BTSupportHours, or BTPlansInformation tools which now include real-time web scraping from www.bt.com.
          
          6. **Context Memory**: The system automatically remembers recent conversations and uses this context to provide more relevant and personalized answers.
          
          7. **Additional Context**: Use the search tool for general web information and wiki_tool for background context when needed.
          
          8. **Save Important Information**: Use the save_tool to save any research or important information for future reference.

          **RESPONSE GUIDELINES:**
          - Always maintain a polite, empathetic, and customer-focused tone
          - Provide comprehensive answers that combine information from multiple sources when appropriate
          - Use context from previous conversations to provide more personalized responses
          - For complex queries, use the IntelligentToolOrchestrator for automatic multi-source information gathering
          - **CRITICAL**: When customers report problems, issues, complaints, or need human assistance, ALWAYS use the CreateSupportTicket tool first
          - Never mention internal tools, processes, or system details in your responses
          - If you don't know the answer, create a support ticket for human assistance
          - For customer orders, use the appropriate customer database tools
          
          **CONTEXT AWARENESS:**
          - The system automatically tracks conversation context and uses it to improve responses
          - Reference previous questions and answers when relevant
          - Provide follow-up suggestions based on conversation history
          
          **IMPORTANT**: Provide your response in natural, conversational language that directly answers the customer's question. Do NOT use any special formatting, structure, or technical language. Just give a clear, helpful answer as if you're speaking directly to the customer.
            """,
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)

# Enhanced tools list with intelligent orchestration and context memory
tools = [
    rag_tool,  # Database knowledge base first
    support_knowledge_tool,  # Support responses
    create_ticket_tool_instance,  # Support ticket creation for customer issues
    intelligent_orchestrator_tool,  # Intelligent tool orchestrator with context memory
    bt_website_tool,  # BT.com specific information with scraping
    bt_support_hours_tool_instance,  # BT support hours with real-time data
    bt_plans_tool,  # BT plans and pricing with scraping
    search_tool,  # General web search for additional context
    wiki_tool,  # Wikipedia for background information
    save_tool  # Save important information for future reference
]

# Agent creation
agent = None
agent_executor = None

try:
    if llm is None:
        logger.warning("LLM not available, agent creation skipped")
    else:
        agent = create_tool_calling_agent(
            llm=llm,
            prompt=prompt,
            tools=tools
        )

        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        logger.info("Agent and executor created successfully")
except Exception as e:
    logger.error(f"Failed to create agent: {e}")
    logger.warning("Continuing without agent functionality")
    agent = None
    agent_executor = None

# Initialize memory layer manager (singleton instance)
memory_config = load_config()
memory_manager = MemoryLayerManager(config=memory_config)

# Set shared memory manager for tools
set_shared_memory_manager(memory_manager)

# Initialize intelligent chat UI components
try:
    # Convert tools list to dictionary for ToolOrchestrator
    tools_dict = {tool.name: tool for tool in tools}
    
    # Initialize components with existing integrations
    intelligent_tool_orchestrator = ToolOrchestrator(
        available_tools=tools_dict,
        max_concurrent_tools=3,
        default_timeout=30.0
    )
    
    intelligent_context_retriever = ContextRetriever(
        memory_manager=memory_manager
    )
    
    intelligent_response_renderer = ResponseRenderer()
    
    # Initialize ChatManager with all components including LLM and agent executor
    intelligent_chat_manager = ChatManager(
        tool_orchestrator=intelligent_tool_orchestrator,
        context_retriever=intelligent_context_retriever,
        response_renderer=intelligent_response_renderer,
        memory_manager=memory_manager,
        llm=llm,
        agent_executor=agent_executor
    )
    
    logger.info("Intelligent chat UI components initialized successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize intelligent chat UI components: {e}")
    intelligent_chat_manager = None

# Lifespan function for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    try:
        logger.info("Starting AI Agent Customer Support application...")
        
        # Initialize database tables
        try:
            init_db()
            logger.info("✅ Database tables initialized successfully")
        except Exception as db_error:
            logger.error(f"❌ Database initialization failed: {db_error}")
            logger.warning("Application will continue but registration/login may not work")
        
        # Log configuration status
        if llm:
            logger.info("✅ LLM (Gemini) is available")
        else:
            logger.warning("⚠️ LLM is not available")
        
        if agent_executor:
            logger.info("✅ Agent executor is available")
        else:
            logger.warning("⚠️ Agent executor is not available")
        
        if memory_manager:
            logger.info("✅ Memory manager is available")
        else:
            logger.warning("⚠️ Memory manager is not available")
        
        # Start background cleanup task
        if memory_config.retention.auto_cleanup_enabled:
            asyncio.create_task(cleanup_memory_task())
            logger.info("Memory cleanup background task started")
        
        logger.info("🚀 AI Agent Customer Support application started successfully!")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Agent Customer Support application...")

# FastAPI app setup with lifespan
app = FastAPI(
    title="AI Agent Customer Support", 
    version="1.0.0",
    lifespan=lifespan
)

# Allow CORS for local frontend testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include voice assistant router
app.include_router(voice_router)

# Background task for memory cleanup
async def cleanup_memory_task():
    """Background task to periodically clean up expired memory data"""
    while True:
        try:
            logger.info("Starting memory cleanup task")
            cleanup_result = memory_manager.cleanup_expired_data()
            
            if cleanup_result.errors:
                logger.error(f"Memory cleanup errors: {cleanup_result.errors}")
            else:
                logger.info(f"Memory cleanup completed: {cleanup_result.to_dict()}")
            
            # Record cleanup metrics
            memory_manager.record_health_metric(
                "cleanup_duration", 
                cleanup_result.cleanup_duration, 
                "seconds", 
                "performance"
            )
            memory_manager.record_health_metric(
                "conversations_cleaned", 
                cleanup_result.conversations_cleaned, 
                "count", 
                "storage"
            )
            
        except Exception as e:
            logger.error(f"Memory cleanup task error: {e}")
        
        # Wait for next cleanup interval (convert hours to seconds)
        await asyncio.sleep(memory_config.retention.cleanup_interval_hours * 3600)

# Duplicate cleanup_memory_task function removed - using the one above

# Startup logic moved to lifespan function above

# Learning and insights endpoints
@app.get("/learning/insights")
async def get_learning_insights(session_token: str = Cookie(None)):
    """Get learning insights for the current user"""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Unauthorized: No session token")

        # Get user ID from session
        with SessionLocal() as db:
            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_token,
                UserSession.is_active == True
            ).first()
            
            if not user_session:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            user_id = user_session.user_id

        # Get learning insights from intelligent chat manager
        if intelligent_chat_manager:
            insights = intelligent_chat_manager.get_learning_insights(user_id)
            return JSONResponse(content=insights)
        else:
            return JSONResponse(content={"error": "Learning system not available"})
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting learning insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to get learning insights")

@app.get("/learning/conversation-patterns")
async def get_conversation_patterns(session_token: str = Cookie(None)):
    """Get conversation patterns and recommendations for the current user"""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Unauthorized: No session token")

        # Get user ID from session
        with SessionLocal() as db:
            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_token,
                UserSession.is_active == True
            ).first()
            
            if not user_session:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            user_id = user_session.user_id

        # Get conversation patterns from memory manager
        if memory_manager:
            user_history = memory_manager.get_user_conversation_history(user_id, limit=30)
            
            patterns = {
                "total_conversations": len(user_history),
                "recent_topics": [],
                "successful_interactions": [],
                "tool_usage_patterns": []
            }
            
            # Analyze recent topics
            recent_topics = {}
            for conv in user_history[:10]:  # Last 10 conversations
                if hasattr(conv, 'user_message') and conv.user_message:
                    words = conv.user_message.lower().split()
                    for word in words:
                        if len(word) > 4:  # Only meaningful words
                            recent_topics[word] = recent_topics.get(word, 0) + 1
            
            # Get top topics
            patterns["recent_topics"] = sorted(recent_topics.items(), 
                                             key=lambda x: x[1], reverse=True)[:5]
            
            # Find successful interactions
            successful = [conv for conv in user_history 
                         if hasattr(conv, 'response_quality_score') and 
                         conv.response_quality_score and conv.response_quality_score > 0.8]
            
            patterns["successful_interactions"] = len(successful)
            
            # Analyze tool usage
            tool_usage = {}
            for conv in user_history:
                if hasattr(conv, 'tools_used') and conv.tools_used:
                    for tool in conv.tools_used:
                        tool_usage[tool] = tool_usage.get(tool, 0) + 1
            
            patterns["tool_usage_patterns"] = sorted(tool_usage.items(), 
                                                   key=lambda x: x[1], reverse=True)
            
            return JSONResponse(content=patterns)
        else:
            return JSONResponse(content={"error": "Memory manager not available"})
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation patterns: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation patterns")

# Data lake endpoints removed - data_lake folder was deleted as it was unused

# Serve frontend static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def root():
    return FileResponse("frontend/login.html")

@app.get("/login.html")
async def login_page():
    return FileResponse("frontend/login.html")

@app.get("/chat.html")
async def chat_page():
    return FileResponse("frontend/chat.html")

@app.get("/register.html")
async def register_page():
    return FileResponse("frontend/register.html")

@app.get("/test-voice-button.html")
async def test_voice_button_page():
    return FileResponse("frontend/test-voice-button.html")

@app.get("/voice-integration-debug.html")
async def voice_integration_debug_page():
    return FileResponse("frontend/voice-integration-debug.html")

@app.get("/simple-voice-test.html")
async def simple_voice_test_page():
    return FileResponse("frontend/simple-voice-test.html")

@app.get("/voice-page-integration.js")
async def voice_page_integration_js():
    return FileResponse("frontend/voice-page-integration.js")

@app.get("/voice-assistant-test.html")
async def voice_assistant_test_page():
    return FileResponse("frontend/voice-assistant-test.html")

# Removed test-fixes.html endpoint - file not found

# Authentication endpoints
@app.post("/logout")
async def logout(response: Response, session_token: str = Cookie(None)):
    """Logout endpoint to invalidate user session and clean up memory data"""
    try:
        user_id = None
        session_id = None
        
        if session_token:
            # Invalidate the session in the database
            with SessionLocal() as db:
                user_session = db.query(UserSession).filter(
                    UserSession.session_id == session_token
                ).first()
                
                if user_session:
                    user_id = user_session.user_id
                    session_id = user_session.session_id
                    
                    user_session.is_active = False
                    user_session.logout_time = datetime.now(timezone.utc)
                    db.commit()
                    logger.info(f"User session {session_token} logged out successfully")
        
        # Clean up user memory data on logout
        if user_id and memory_manager:
            try:
                cleanup_result = memory_manager.cleanup_user_session_data(user_id, session_id)
                if cleanup_result.errors:
                    logger.warning(f"Memory cleanup had errors for user {user_id}: {cleanup_result.errors}")
                else:
                    logger.info(f"Memory cleanup completed for user {user_id}: "
                              f"{cleanup_result.conversations_cleaned} conversations, "
                              f"{cleanup_result.context_entries_cleaned} cache entries cleaned")
            except Exception as cleanup_error:
                logger.error(f"Memory cleanup failed for user {user_id}: {cleanup_error}")
        
        # Clear the session cookie
        response.delete_cookie("session_token")
        
        return JSONResponse(
            content={"message": "Logged out successfully"},
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Still clear the cookie even if database update fails
        response.delete_cookie("session_token")
        return JSONResponse(
            content={"message": "Logged out successfully"},
            status_code=200
        )

# Registration request model
class RegisterRequest(PydanticBaseModel):
    user_id: str
    username: str
    email: str
    full_name: Optional[str] = None
    password: str

@app.post("/register")
async def register_user(register_request: RegisterRequest):
    """Register a new user"""
    try:
        logger.info(f"Registration attempt for user_id: {register_request.user_id}, username: {register_request.username}, email: {register_request.email}")
        with SessionLocal() as db:
            # Check if user_id already exists
            existing_user_by_id = db.query(User).filter(User.user_id == register_request.user_id).first()
            if existing_user_by_id:
                raise HTTPException(status_code=400, detail="User ID already exists")
            
            # Check if username already exists
            existing_user_by_username = db.query(User).filter(User.username == register_request.username).first()
            if existing_user_by_username:
                raise HTTPException(status_code=400, detail="Username already exists")
            
            # Check if email already exists
            existing_user_by_email = db.query(User).filter(User.email == register_request.email).first()
            if existing_user_by_email:
                raise HTTPException(status_code=400, detail="Email already exists")
            
            # Hash the password
            password_hash = hashlib.sha256(register_request.password.encode()).hexdigest()
            
            # Create new user
            new_user = User(
                user_id=register_request.user_id,
                username=register_request.username,
                email=register_request.email,
                full_name=register_request.full_name,
                password_hash=password_hash,
                is_active=True,
                is_admin=False
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            logger.info(f"New user registered successfully: {register_request.user_id}")
            
            return JSONResponse(
                content={
                    "message": "User registered successfully",
                    "user_id": new_user.user_id,
                    "username": new_user.username,
                    "email": new_user.email
                },
                status_code=201
            )
            
    except HTTPException as he:
        logger.error(f"Registration HTTP error: {he.detail}")
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.get("/me")
async def get_current_user(session_token: str = Cookie(None)):
    """Get current user information from session"""
    try:
        if not session_token:
            return JSONResponse(
                content={"authenticated": False, "message": "No session token"},
                status_code=401
            )
        
        # Check if session is valid
        with SessionLocal() as db:
            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_token,
                UserSession.is_active == True
            ).first()
            
            if not user_session:
                return JSONResponse(
                    content={"authenticated": False, "message": "Invalid session"},
                    status_code=401
                )
            
            # Get user information
            user = db.query(User).filter(User.user_id == user_session.user_id).first()
            
            if not user:
                return JSONResponse(
                    content={"authenticated": False, "message": "User not found"},
                    status_code=401
                )
            
            return JSONResponse(
                content={
                    "authenticated": True,
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "session_id": session_token
                },
                status_code=200
            )
            
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        return JSONResponse(
            content={"authenticated": False, "message": "Session check failed"},
            status_code=500
        )

# Request model for chat input
class ChatRequest(PydanticBaseModel):
    query: str

# Response model for chat output
class ChatResponse(PydanticBaseModel):
    topic: str
    summary: str
    sources: list[str] = []
    tools_used: list[str] = []
    # Enhanced fields for intelligent chat UI
    confidence_score: float = 0.0
    execution_time: float = 0.0
    ui_state: Optional[Dict[str, Any]] = None
    content_type: str = "plain_text"

# API endpoints

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest, session_token: str = Cookie(None)):
    start_time = time.time()
    user_id = None
    
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Unauthorized: No session token")

        # Get user ID from session
        with SessionLocal() as db:
            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_token,
                UserSession.is_active == True
            ).first()
            
            if not user_session:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            user_id = user_session.user_id

        # Try intelligent chat manager first, fallback to legacy agent executor
        if intelligent_chat_manager:
            try:
                # Use intelligent chat manager for enhanced processing
                intelligent_response = await intelligent_chat_manager.process_message(
                    message=chat_request.query,
                    user_id=user_id,
                    session_id=session_token
                )
                
                # Convert intelligent response to legacy format with enhanced fields
                ui_state_dict = None
                if intelligent_chat_manager:
                    ui_state = intelligent_chat_manager.update_ui_state(intelligent_response)
                    ui_state_dict = {
                        "loading_indicators": [
                            {
                                "tool_name": indicator.tool_name,
                                "state": indicator.state.value,
                                "progress": indicator.progress,
                                "message": indicator.message
                            } for indicator in ui_state.loading_indicators
                        ],
                        "error_states": [
                            {
                                "error_type": error.error_type,
                                "message": error.message,
                                "severity": error.severity.value,
                                "recovery_actions": error.recovery_actions
                            } for error in ui_state.error_states
                        ]
                    }
                
                return ChatResponse(
                    topic=chat_request.query,
                    summary=intelligent_response.content,
                    sources=intelligent_response.context_used,
                    tools_used=intelligent_response.tools_used,
                    confidence_score=intelligent_response.confidence_score,
                    execution_time=intelligent_response.execution_time,
                    ui_state=ui_state_dict,
                    content_type=intelligent_response.content_type.value
                )
                
            except Exception as intelligent_error:
                logger.warning(f"Intelligent chat manager failed, falling back to legacy: {intelligent_error}")
                # Continue to legacy implementation below

        # Legacy implementation (fallback)
        # Validate that agent executor is available
        if not agent_executor:
            raise HTTPException(status_code=500, detail="Agent executor not available")

        # Retrieve conversation context from memory layer with session awareness
        context_entries = memory_manager.retrieve_context(
            query=chat_request.query,
            user_id=user_id,
            limit=15  # Get more context for better understanding
        )
        
        # Build context for the agent with proper conversation flow
        chat_history = []
        context_used = []
        
        logger.info(f"Retrieved {len(context_entries)} context entries for user {user_id}")
        
        # Sort context entries by timestamp to maintain conversation order
        sorted_contexts = sorted(context_entries, key=lambda x: x.timestamp if x.timestamp else datetime.min)
        
        # Group consecutive user/bot messages to maintain conversation flow
        conversation_pairs = []
        current_pair = {"user": None, "bot": None}
        
        for context in sorted_contexts:
            if context.context_type == "user_message":
                # If we have a complete pair, save it and start new one
                if current_pair["user"] is not None:
                    conversation_pairs.append(current_pair)
                    current_pair = {"user": None, "bot": None}
                current_pair["user"] = context
            elif context.context_type == "bot_response":
                current_pair["bot"] = context
                # Complete pair - add to list
                conversation_pairs.append(current_pair)
                current_pair = {"user": None, "bot": None}
        
        # Add any remaining incomplete pair
        if current_pair["user"] is not None:
            conversation_pairs.append(current_pair)
        
        # Build chat history from conversation pairs (most recent first for context)
        for pair in conversation_pairs[-5:]:  # Last 5 conversation exchanges
            if pair["user"]:
                chat_history.append(HumanMessage(content=pair["user"].content))
                context_used.append(f"user_msg_{pair['user'].source}")
                logger.info(f"Added user message: {pair['user'].content[:50]}...")
            
            if pair["bot"]:
                chat_history.append(AIMessage(content=pair["bot"].content))
                context_used.append(f"bot_response_{pair['bot'].source}")
                logger.info(f"Added bot response: {pair['bot'].content[:50]}...")
        
        # If no context from memory, add some default context
        if not context_used:
            context_used.append("session_context")
            context_used.append("query_analysis")
            logger.info("Added default context entries")

        # Get tool recommendations
        tool_recommendation = memory_manager.analyze_tool_usage(
            query=chat_request.query,
            tools_used=[]  # Will be populated after agent execution
        )

        # Use the agent executor to process the query with context
        try:
            agent_input = {
                "query": chat_request.query,
                "chat_history": chat_history
            }
            logger.info(f"Invoking agent with query: {chat_request.query}")
            logger.info(f"Available tools: {[tool.name for tool in tools]}")
            
            response = agent_executor.invoke(agent_input)
            logger.info(f"Agent response keys: {response.keys() if response else 'None'}")
            
            # Debug the full response structure
            if response:
                logger.info(f"Full agent response: {response}")
            
            if response and 'intermediate_steps' in response:
                logger.info(f"Number of intermediate steps: {len(response['intermediate_steps'])}")
                for i, step in enumerate(response['intermediate_steps']):
                    logger.info(f"Step {i}: {type(step)} - {step}")
            else:
                logger.warning("No intermediate_steps found in agent response")
                
                # If no intermediate steps, let's force some tool usage based on the query
                logger.info("Attempting to manually trigger tool usage based on query content")
        except Exception as agent_error:
            logger.error(f"Agent execution error: {agent_error}")
            
            # Store failed conversation in memory
            failed_conversation = ConversationEntry(
                session_id=session_token,
                user_id=user_id,
                user_message=chat_request.query,
                bot_response="I'm sorry, I encountered an error processing your query. Please try again or contact support.",
                tools_used=[],
                tool_performance={},
                context_used=context_used,
                response_quality_score=0.0
            )
            memory_manager.store_conversation(failed_conversation)
            
            return ChatResponse(
                topic=chat_request.query,
                summary="I'm sorry, I encountered an error processing your query. Please try again or contact support."
            )
        
        # Process the response
        summary = ""
        tools_used = []
        sources = []
        tool_performance = {}
        
        if response and 'output' in response:
            # Extract the response content
            response_content = response['output']
            
            # If the response contains structured format, extract just the summary
            if 'summary:' in response_content.lower():
                # Try to extract summary from structured response
                lines = response_content.split('\n')
                for line in lines:
                    if line.lower().startswith('summary:'):
                        summary = line.split(':', 1)[1].strip()
                        break
                
                if not summary:
                    summary = response_content
            else:
                summary = response_content
            
            # Extract tools used from intermediate steps if available
            if 'intermediate_steps' in response:
                logger.info(f"Processing {len(response['intermediate_steps'])} intermediate steps")
                
                for i, step in enumerate(response['intermediate_steps']):
                    try:
                        if isinstance(step, tuple) and len(step) >= 2:
                            # Standard format: (AgentAction, observation)
                            action, observation = step[0], step[1]
                            
                            if hasattr(action, 'tool'):
                                tool_name = action.tool
                                tools_used.append(tool_name)
                                
                                # Calculate basic tool performance based on observation
                                if observation and len(str(observation)) > 10:
                                    tool_performance[tool_name] = 1.0  # Success
                                else:
                                    tool_performance[tool_name] = 0.5  # Partial success
                                
                                logger.info(f"Extracted tool: {tool_name}")
                            
                        elif hasattr(step, 'tool'):
                            # Direct tool reference
                            tool_name = step.tool
                            tools_used.append(tool_name)
                            tool_performance[tool_name] = 1.0
                            logger.info(f"Extracted direct tool: {tool_name}")
                            
                    except Exception as step_error:
                        logger.warning(f"Error processing step {i}: {step_error}")
                        continue
                
                # Remove duplicates while preserving order
                tools_used = list(dict.fromkeys(tools_used))
                logger.info(f"Final tools used: {tools_used}")
            
            # Also check if tools are mentioned in the response content
            if not tools_used and response_content:
                # Look for tool mentions in the response
                tool_names = [tool.name for tool in tools]
                for tool_name in tool_names:
                    if tool_name.lower() in response_content.lower():
                        tools_used.append(tool_name)
                        tool_performance[tool_name] = 0.8  # Inferred usage
                
                if tools_used:
                    logger.info(f"Inferred tools from response content: {tools_used}")
        
        # Try ticket-related queries first
        ticket_handler = TicketChatHandler()
        ticket_response = ticket_handler.handle_ticket_query(chat_request.query, user_id)
        
        if ticket_response:
            summary = ticket_response['response']
            tools_used.append('TicketHandler')
            tool_performance['TicketHandler'] = 1.0
            if 'ticket_info' in ticket_response:
                context_used.append(f"ticket_{ticket_response['ticket_info']['ticket_id']}")
        
        # If still no tools used, manually trigger appropriate tools based on query content
        if not tools_used:
            logger.info("No tools detected, attempting manual tool selection based on query")
            query_lower = chat_request.query.lower()
            
            # Manual tool selection based on query keywords - CHECK OTHER TOOLS FIRST
            
            # 1. Check for specific plan/upgrade queries first
            if any(keyword in query_lower for keyword in ['upgrade', 'plan', 'change plan', 'pricing', 'subscription']):
                try:
                    # Use the support knowledge tool for plan upgrades
                    support_result = support_knowledge_tool_func(chat_request.query)
                    if support_result and len(support_result) > 20:
                        tools_used.append("SupportKnowledgeBase")
                        tool_performance["SupportKnowledgeBase"] = 1.0
                        summary = support_result
                        logger.info("Manually triggered SupportKnowledgeBase tool")
                        
                        # Also try BT plans tool for additional info
                        try:
                            bt_plans_result = bt_plans_tool.invoke({"query": chat_request.query})
                            if bt_plans_result and len(bt_plans_result) > 20:
                                tools_used.append("BTPlansInformation")
                                tool_performance["BTPlansInformation"] = 1.0
                                logger.info("Manually triggered BTPlansInformation tool")
                        except Exception as bt_error:
                            logger.warning(f"BT plans tool error: {bt_error}")
                except Exception as manual_error:
                    logger.warning(f"Manual plan tool trigger error: {manual_error}")
            
            # 2. Check for data usage queries - USE MULTIPLE TOOLS
            elif any(keyword in query_lower for keyword in ['data usage', 'check data', 'data balance', 'usage', 'remaining data', 'data allowance', 'how much data']):
                try:
                    logger.info("Detected data usage query - using multiple tools for comprehensive answer")
                    
                    # Start with support knowledge base for specific instructions
                    support_result = support_knowledge_tool_func(chat_request.query)
                    if support_result and len(support_result) > 20:
                        tools_used.append("SupportKnowledgeBase")
                        tool_performance["SupportKnowledgeBase"] = 1.0
                        summary = support_result
                        logger.info("Used SupportKnowledgeBase for data usage instructions")
                    
                    # Add BT-specific information from website
                    try:
                        bt_website_result = bt_website_tool.invoke({"query": "check data usage balance allowance"})
                        if bt_website_result and len(bt_website_result) > 20:
                            tools_used.append("BTWebsiteSearch")
                            tool_performance["BTWebsiteSearch"] = 1.0
                            # Combine with existing summary
                            if summary:
                                summary += f"\n\n**Additional BT Information:**\n{bt_website_result}"
                            else:
                                summary = bt_website_result
                            logger.info("Added BTWebsiteSearch for current BT data usage info")
                    except Exception as bt_error:
                        logger.warning(f"BT website tool error: {bt_error}")
                    
                    # Add context from knowledge base
                    try:
                        rag_result = rag_tool_func("data usage check balance mobile app")
                        if rag_result and len(rag_result) > 20:
                            tools_used.append("ContextRetriever")
                            tool_performance["ContextRetriever"] = 1.0
                            # Enhance the summary with additional context
                            if summary:
                                summary += f"\n\n**Additional Help:**\n{rag_result}"
                            else:
                                summary = rag_result
                            logger.info("Added ContextRetriever for additional data usage help")
                    except Exception as rag_error:
                        logger.warning(f"RAG tool error: {rag_error}")
                    
                    # Use intelligent orchestrator for comprehensive response
                    try:
                        orchestrator_result = intelligent_orchestrator_tool.invoke({"query": chat_request.query})
                        if orchestrator_result and len(orchestrator_result) > 50:
                            tools_used.append("IntelligentToolOrchestrator")
                            tool_performance["IntelligentToolOrchestrator"] = 1.0
                            
                            # For data usage queries, prioritize relevant content over length
                            # Check if orchestrator result is actually about data usage
                            orchestrator_lower = orchestrator_result.lower()
                            if any(keyword in orchestrator_lower for keyword in ['data usage', '*124#', '*123#', 'mobile app', 'check data', 'usage']):
                                # Orchestrator result is relevant, use it
                                summary = orchestrator_result
                                logger.info("Used relevant IntelligentToolOrchestrator result for data usage")
                            elif not summary or len(summary) < 50:
                                # No good summary yet, use orchestrator as fallback
                                summary = orchestrator_result
                                logger.info("Used IntelligentToolOrchestrator as fallback for data usage")
                            else:
                                # Keep existing summary as it's more relevant
                                logger.info("Kept existing summary as it's more relevant than orchestrator result")
                    except Exception as orchestrator_error:
                        logger.warning(f"Orchestrator tool error: {orchestrator_error}")
                    
                    if tools_used:
                        logger.info(f"Data usage query processed with {len(tools_used)} tools: {tools_used}")
                    
                except Exception as manual_error:
                    logger.warning(f"Manual data usage tool trigger error: {manual_error}")
            
            # 3. Check for support hours/contact queries
            elif any(keyword in query_lower for keyword in ['support hours', 'contact', 'phone number', 'opening hours', 'customer service']):
                try:
                    # Use support hours tool
                    support_hours_result = bt_support_hours_tool_instance.invoke({"query": chat_request.query})
                    if support_hours_result and len(support_hours_result) > 10:
                        tools_used.append("BTSupportHours")
                        tool_performance["BTSupportHours"] = 1.0
                        summary = support_hours_result
                        logger.info("Manually triggered BTSupportHours tool")
                except Exception as manual_error:
                    logger.warning(f"Manual support hours tool error: {manual_error}")
            
            # 4. Check for password/account queries
            elif any(keyword in query_lower for keyword in ['password', 'reset', 'account', 'login', 'username', 'forgot']):
                try:
                    # Use knowledge base for password/account issues
                    rag_result = rag_tool_func(chat_request.query)
                    if rag_result and len(rag_result) > 20:
                        tools_used.append("ContextRetriever")
                        tool_performance["ContextRetriever"] = 1.0
                        summary = rag_result
                        logger.info("Manually triggered ContextRetriever tool")
                except Exception as manual_error:
                    logger.warning(f"Manual RAG tool error: {manual_error}")
            
            # 4. Try support knowledge base for general queries
            if not tools_used:
                try:
                    support_result = support_knowledge_tool_func(chat_request.query)
                    if support_result and len(support_result) > 20:
                        tools_used.append("SupportKnowledgeBase")
                        tool_performance["SupportKnowledgeBase"] = 1.0
                        summary = support_result
                        logger.info("Manually triggered SupportKnowledgeBase tool for general query")
                except Exception as manual_error:
                    logger.warning(f"Manual support knowledge tool error: {manual_error}")
            
            # 5. Try RAG/context retriever for general knowledge
            if not tools_used:
                try:
                    rag_result = rag_tool_func(chat_request.query)
                    if rag_result and len(rag_result) > 20:
                        tools_used.append("ContextRetriever")
                        tool_performance["ContextRetriever"] = 1.0
                        summary = rag_result
                        logger.info("Manually triggered ContextRetriever tool for general query")
                except Exception as manual_error:
                    logger.warning(f"Manual RAG tool error: {manual_error}")
            
            # 6. Try the intelligent orchestrator
            if not tools_used:
                try:
                    orchestrator_result = intelligent_orchestrator_tool.invoke({"query": chat_request.query})
                    if orchestrator_result and len(orchestrator_result) > 20:
                        tools_used.append("IntelligentToolOrchestrator")
                        tool_performance["IntelligentToolOrchestrator"] = 1.0
                        summary = orchestrator_result
                        logger.info("Manually triggered IntelligentToolOrchestrator tool")
                except Exception as manual_error:
                    logger.warning(f"Manual orchestrator tool error: {manual_error}")
            
            # 7. ONLY create ticket if other tools failed AND it's clearly a problem/complaint
            if not tools_used and any(keyword in query_lower for keyword in [
                'create ticket', 'support ticket', 'complaint', 'escalate', 'human support',
                'not working', 'broken', 'error', 'bug', 'billing issue', 'technical problem',
                'urgent', 'emergency', 'outage', 'service down'
            ]):
                try:
                    # Create a support ticket for the customer
                    logger.info(f"Creating support ticket for customer {user_id} with query: {chat_request.query}")
                    
                    # Convert user_id to int if it's a string (for compatibility with ticket system)
                    customer_id = int(user_id) if isinstance(user_id, str) and user_id.isdigit() else user_id
                    
                    ticket_result = create_ticket_tool_instance.invoke({"query": chat_request.query, "user_id": customer_id})
                    if ticket_result and len(ticket_result) > 20:
                        tools_used.append("CreateSupportTicket")
                        tool_performance["CreateSupportTicket"] = 1.0
                        summary = ticket_result
                        logger.info(f"Successfully created support ticket for customer {customer_id}")
                    else:
                        logger.warning("Ticket creation returned empty or short result")
                except Exception as manual_error:
                    logger.error(f"Manual ticket creation error for customer {user_id}: {manual_error}")
                    # Provide fallback response if ticket creation fails
                    summary = "I understand you need assistance. While I'm having trouble creating a support ticket right now, please contact our customer service team directly at 0330 123 4150 for immediate help with your issue."
            
            if tools_used:
                logger.info(f"Manually triggered tools: {tools_used}")
        
        if not summary:
            summary = "I'm sorry, I couldn't process your query."
        
        # Calculate response quality score (simple implementation)
        response_quality_score = min(1.0, len(summary) / 100.0)  # Basic quality metric
        if context_entries:
            response_quality_score += 0.2  # Bonus for using context
        if tools_used:
            response_quality_score += 0.1 * len(tools_used)  # Bonus for tool usage
        response_quality_score = min(1.0, response_quality_score)
        
        # Store conversation in memory layer
        conversation_entry = ConversationEntry(
            session_id=session_token,
            user_id=user_id,
            user_message=chat_request.query,
            bot_response=summary,
            tools_used=tools_used,
            tool_performance=tool_performance,  # Use actual performance tracking
            context_used=context_used,
            response_quality_score=response_quality_score
        )
        
        success = memory_manager.store_conversation(conversation_entry)
        if not success:
            logger.warning("Failed to store conversation in memory layer")
        else:
            logger.info(f"Stored conversation for user {user_id} with {len(tools_used)} tools")
            
        # Also save to database for immediate availability in next request
        try:
            with SessionLocal() as db:
                chat_history = ChatHistory(
                    user_id=user_id,
                    session_id=session_token,
                    user_message=chat_request.query,
                    bot_response=summary,
                    tools_used=json.dumps(tools_used),
                    context_used=json.dumps(context_used),
                    response_quality_score=response_quality_score,
                    timestamp=datetime.now()
                )
                db.add(chat_history)
                db.commit()
                logger.info(f"Saved chat history to database for immediate context availability")
        except Exception as db_error:
            logger.error(f"Failed to save chat history to database: {db_error}")
        
        # Record performance metrics
        response_time = time.time() - start_time
        memory_manager.record_health_metric(
            "chat_response_time", 
            response_time, 
            "seconds", 
            "performance"
        )
        
        return ChatResponse(
            topic=chat_request.query,
            summary=summary,
            sources=sources,
            tools_used=tools_used
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        
        # Store error conversation if we have user_id
        if user_id and session_token:
            try:
                error_conversation = ConversationEntry(
                    session_id=session_token,
                    user_id=user_id,
                    user_message=chat_request.query,
                    bot_response=f"Error processing request: {str(e)}",
                    tools_used=[],
                    tool_performance={},
                    context_used=[],
                    response_quality_score=0.0
                )
                memory_manager.store_conversation(error_conversation)
            except Exception as store_error:
                logger.error(f"Failed to store error conversation: {store_error}")
        
        raise HTTPException(status_code=500, detail=f"Error processing request: {e}")

# Health check endpoint
@app.get("/health")
async def health_check():
    try:
        # Test database connection
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

# Database initialization endpoint
@app.post("/init-db")
async def initialize_database():
    """Initialize database tables if they don't exist"""
    try:
        from database import init_db
        init_db()
        return {"message": "Database initialized successfully"}
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {e}")

# Login endpoint with proper user ID and password validation
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    try:
        if not username or not password:
            raise HTTPException(status_code=400, detail="User ID and password required")

        with SessionLocal() as db:
            user = db.query(User).filter(
                User.user_id == username,
                User.is_active == True
            ).first()

            if not user:
                raise HTTPException(status_code=401, detail="Invalid user ID or password")

            stored_hash = user.password_hash

            # Debugging logs
            logger.info(f"🔑 Raw entered password: {password}")
            logger.info(f"🔑 Stored hash in DB: {stored_hash}")

            # --- Password Validation ---
            valid_password = False

            # Case 1: bcrypt stored
            if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
                valid_password = bcrypt.checkpw(password.encode(), stored_hash.encode())

            # Case 2: SHA-256 stored
            else:
                entered_hash = hashlib.sha256(password.encode()).hexdigest()
                logger.info(f"🔑 Entered SHA256 hash: {entered_hash}")
                valid_password = (entered_hash == stored_hash)

            if not valid_password:
                raise HTTPException(status_code=401, detail="Invalid user ID or password")

            # --- Session handling ---
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
            token_hash = hashlib.sha256(session_token.encode()).hexdigest()

            user_session = UserSession(
                session_id=session_token,   # ❗️Consider storing only token_hash
                token_hash=token_hash,
                user_id=user.user_id,
                created_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                last_accessed=datetime.now(timezone.utc),
                is_active=True
            )
            db.add(user_session)
            db.commit()

            login_entry = ChatHistory(
                session_id=session_token,
                user_message="login",
                bot_response=f"User {user.username} ({user.user_id}) logged in successfully"
            )
            db.add(login_entry)
            db.commit()

            db.refresh(user)

        response = JSONResponse({
            "access_token": session_token,
            "token_type": "bearer",
            "expires_in": 86400,
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name
            }
        })
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            max_age=86400,
            secure=False,  # ✅ change to True in production
            samesite="lax"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")



# Duplicate logout endpoint removed - using the enhanced one above with memory cleanup

# Get current user info
@app.get("/me")
async def get_current_user(session_token: str = Cookie(None)):
    """Get current user information from session"""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="No active session")
        
        # Get user info from session
        with SessionLocal() as db:
            # First, get the user session to find the user_id
            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_token,
                UserSession.is_active == True
            ).first()
            
            if not user_session:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            # Then get the actual user information
            user = db.query(User).filter(
                User.user_id == user_session.user_id,
                User.is_active == True
            ).first()
            
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
        
        return {
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name
            },
            "authenticated": True
        }
        
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user info")

# Memory layer endpoints
@app.get("/memory/stats")
async def get_memory_stats(session_token: str = Cookie(None)):
    """Get memory system statistics for monitoring"""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Unauthorized: No session token")
        
        # Validate session
        with SessionLocal() as db:
            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_token,
                UserSession.is_active == True
            ).first()
            
            if not user_session:
                raise HTTPException(status_code=401, detail="Invalid session")
        
        # Get memory statistics
        stats = memory_manager.get_memory_stats()
        
        return {
            "status": "success",
            "memory_stats": stats.to_dict(),
            "config_summary": {
                "retention_days": memory_config.retention.conversation_retention_days,
                "cache_enabled": memory_config.enable_cache_storage,
                "database_enabled": memory_config.enable_database_storage,
                "context_retrieval_enabled": memory_config.enable_context_retrieval,
                "tool_analytics_enabled": memory_config.enable_tool_analytics
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Memory stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get memory stats: {e}")

@app.get("/memory/user-history")
async def get_user_memory_history(session_token: str = Cookie(None), limit: int = 50):
    """Get conversation history for the current user"""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Unauthorized: No session token")
        
        # Get user ID from session
        with SessionLocal() as db:
            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_token,
                UserSession.is_active == True
            ).first()
            
            if not user_session:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            user_id = user_session.user_id
        
        # Get user conversation history
        conversations = memory_manager.get_user_conversation_history(user_id, limit)
        
        # Convert to serializable format
        history = []
        for conv in conversations:
            history.append({
                "session_id": conv.session_id,
                "user_message": conv.user_message,
                "bot_response": conv.bot_response,
                "tools_used": conv.tools_used,
                "response_quality_score": conv.response_quality_score,
                "timestamp": conv.timestamp.isoformat()
            })
        
        return {
            "status": "success",
            "user_id": user_id,
            "conversation_count": len(history),
            "conversations": history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User history error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user history: {e}")

@app.post("/memory/cleanup")
async def trigger_memory_cleanup(background_tasks: BackgroundTasks, session_token: str = Cookie(None)):
    """Manually trigger memory cleanup"""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Unauthorized: No session token")
        
        # Validate session (admin check could be added here)
        with SessionLocal() as db:
            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_token,
                UserSession.is_active == True
            ).first()
            
            if not user_session:
                raise HTTPException(status_code=401, detail="Invalid session")
        
        # Add cleanup task to background
        def run_cleanup():
            try:
                cleanup_result = memory_manager.cleanup_expired_data()
                logger.info(f"Manual cleanup completed: {cleanup_result.to_dict()}")
                return cleanup_result
            except Exception as e:
                logger.error(f"Manual cleanup error: {e}")
                raise
        
        background_tasks.add_task(run_cleanup)
        
        return {
            "status": "success",
            "message": "Memory cleanup task started in background"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cleanup trigger error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger cleanup: {e}")

@app.get("/memory/health")
async def get_memory_health():
    """Get memory system health status"""
    try:
        stats = memory_manager.get_memory_stats()
        
        # Determine health status
        health_status = "healthy"
        issues = []
        
        if stats.error_count > 10:
            health_status = "degraded"
            issues.append(f"High error count: {stats.error_count}")
        
        if stats.health_score < 0.8:
            health_status = "degraded"
            issues.append(f"Low health score: {stats.health_score}")
        
        if stats.average_response_time > 5.0:
            health_status = "degraded"
            issues.append(f"High response time: {stats.average_response_time}s")
        
        if stats.health_score < 0.5 or stats.error_count > 50:
            health_status = "unhealthy"
        
        return {
            "status": health_status,
            "health_score": stats.health_score,
            "error_count": stats.error_count,
            "average_response_time": stats.average_response_time,
            "last_cleanup": stats.last_cleanup.isoformat() if stats.last_cleanup else None,
            "issues": issues,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Memory health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Intelligent Chat UI specific endpoints

@app.get("/chat/status")
async def get_chat_status(session_token: str = Cookie(None)):
    """Get real-time tool execution updates and chat system status."""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Unauthorized: No session token")
        
        # Validate session
        with SessionLocal() as db:
            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_token,
                UserSession.is_active == True
            ).first()
            
            if not user_session:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            user_id = user_session.user_id
        
        # Get chat system status
        status_info = {
            "system_status": "operational",
            "intelligent_chat_enabled": intelligent_chat_manager is not None,
            "legacy_agent_enabled": agent_executor is not None,
            "memory_layer_enabled": memory_manager is not None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add intelligent chat manager stats if available
        if intelligent_chat_manager:
            try:
                session_stats = intelligent_chat_manager.get_session_stats(user_id, session_token)
                global_stats = intelligent_chat_manager.get_global_stats()
                
                status_info.update({
                    "session_stats": session_stats,
                    "global_stats": global_stats,
                    "active_tools": [],  # Will be populated during active tool execution
                    "tool_queue": [],   # Tools waiting to be executed
                    "last_activity": session_stats.get("last_activity")
                })
            except Exception as e:
                logger.warning(f"Failed to get intelligent chat stats: {e}")
                status_info["intelligent_chat_stats_error"] = str(e)
        
        # Add memory layer status if available
        if memory_manager:
            try:
                memory_stats = memory_manager.get_memory_stats()
                status_info["memory_stats"] = {
                    "health_score": memory_stats.health_score,
                    "total_conversations": memory_stats.total_conversations,
                    "average_response_time": memory_stats.average_response_time,
                    "error_count": memory_stats.error_count
                }
            except Exception as e:
                logger.warning(f"Failed to get memory stats: {e}")
                status_info["memory_stats_error"] = str(e)
        
        return {
            "status": "success",
            "data": status_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat status error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat status: {e}")

@app.get("/chat/context")
async def get_conversation_context(
    session_token: str = Cookie(None), 
    limit: int = 10,
    include_metadata: bool = False
):
    """Get conversation context for the current user."""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Unauthorized: No session token")
        
        # Validate session and get user ID
        with SessionLocal() as db:
            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_token,
                UserSession.is_active == True
            ).first()
            
            if not user_session:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            user_id = user_session.user_id
        
        # Get context using intelligent chat manager if available
        context_entries = []
        
        if intelligent_chat_manager:
            try:
                context_entries = await intelligent_chat_manager.get_conversation_context(user_id, limit)
            except Exception as e:
                logger.warning(f"Intelligent context retrieval failed: {e}")
        
        # Fallback to memory manager
        if not context_entries and memory_manager:
            try:
                memory_contexts = memory_manager.retrieve_context("", user_id, limit)
                # Convert to standard format
                for ctx in memory_contexts:
                    context_entries.append({
                        "content": ctx.content,
                        "source": ctx.source,
                        "relevance_score": ctx.relevance_score,
                        "timestamp": ctx.timestamp.isoformat(),
                        "context_type": ctx.context_type,
                        "metadata": ctx.metadata if include_metadata else {}
                    })
            except Exception as e:
                logger.warning(f"Memory context retrieval failed: {e}")
        
        # Convert intelligent chat context entries to serializable format
        if context_entries and hasattr(context_entries[0], 'content'):
            serializable_context = []
            for entry in context_entries:
                serializable_context.append({
                    "content": entry.content,
                    "source": entry.source,
                    "relevance_score": entry.relevance_score,
                    "timestamp": entry.timestamp.isoformat(),
                    "context_type": entry.context_type,
                    "metadata": entry.metadata if include_metadata else {}
                })
            context_entries = serializable_context
        
        return {
            "status": "success",
            "user_id": user_id,
            "context_count": len(context_entries),
            "context_entries": context_entries,
            "limit": limit,
            "include_metadata": include_metadata,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Context retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation context: {e}")

@app.get("/chat/tools")
async def get_available_tools(session_token: str = Cookie(None)):
    """Get information about available tools and their current status."""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Unauthorized: No session token")
        
        # Validate session
        with SessionLocal() as db:
            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_token,
                UserSession.is_active == True
            ).first()
            
            if not user_session:
                raise HTTPException(status_code=401, detail="Invalid session")
        
        # Get available tools information
        available_tools = []
        
        # Get tools from the global tools list
        for tool in tools:
            tool_info = {
                "name": tool.name,
                "description": tool.description,
                "status": "available",
                "category": "general"
            }
            
            # Add specific categorization
            if "BT" in tool.name or "bt_" in tool.name.lower():
                tool_info["category"] = "bt_specific"
            elif "Support" in tool.name or "support" in tool.name.lower():
                tool_info["category"] = "support"
            elif "Context" in tool.name or "RAG" in tool.name:
                tool_info["category"] = "context"
            elif "search" in tool.name.lower() or "wiki" in tool.name.lower():
                tool_info["category"] = "search"
            
            available_tools.append(tool_info)
        
        # Get tool performance data if available
        tool_performance = {}
        if memory_manager:
            try:
                # Get recent tool usage statistics
                # This would typically come from tool usage analytics
                tool_performance = {
                    "total_tools": len(available_tools),
                    "performance_data_available": True,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            except Exception as e:
                logger.warning(f"Failed to get tool performance data: {e}")
                tool_performance = {
                    "total_tools": len(available_tools),
                    "performance_data_available": False,
                    "error": str(e)
                }
        
        # Get intelligent tool orchestrator status if available
        orchestrator_status = {}
        if intelligent_chat_manager and hasattr(intelligent_chat_manager, 'tool_orchestrator'):
            try:
                orchestrator_status = {
                    "enabled": True,
                    "intelligent_selection": True,
                    "parallel_execution": True,
                    "context_aware_boosting": True
                }
            except Exception as e:
                logger.warning(f"Failed to get orchestrator status: {e}")
                orchestrator_status = {
                    "enabled": False,
                    "error": str(e)
                }
        else:
            orchestrator_status = {
                "enabled": False,
                "reason": "intelligent_chat_manager_not_available"
            }
        
        return {
            "status": "success",
            "tools": available_tools,
            "tool_performance": tool_performance,
            "orchestrator_status": orchestrator_status,
            "categories": {
                "bt_specific": len([t for t in available_tools if t["category"] == "bt_specific"]),
                "support": len([t for t in available_tools if t["category"] == "support"]),
                "context": len([t for t in available_tools if t["category"] == "context"]),
                "search": len([t for t in available_tools if t["category"] == "search"]),
                "general": len([t for t in available_tools if t["category"] == "general"])
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tools information error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tools information: {e}")

@app.get("/chat/ui-state/{session_id}")
async def get_ui_state(session_id: str, session_token: str = Cookie(None)):
    """Get current UI state for a specific session."""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Unauthorized: No session token")
        
        # Validate session
        with SessionLocal() as db:
            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_token,
                UserSession.is_active == True
            ).first()
            
            if not user_session:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            # Verify session_id matches or user has access
            if session_id != session_token:
                # Could add additional authorization logic here
                pass
        
        # Get UI state from intelligent chat manager if available
        ui_state_data = {
            "session_id": session_id,
            "loading_indicators": [],
            "error_states": [],
            "content_sections": [],
            "interactive_elements": [],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        if intelligent_chat_manager:
            try:
                # Create a mock response to get UI state
                # In a real implementation, this would be stored per session
                mock_response = IntelligentChatResponse(
                    content="Getting UI state",
                    content_type=ContentType.PLAIN_TEXT
                )
                
                ui_state = intelligent_chat_manager.update_ui_state(mock_response)
                
                ui_state_data.update({
                    "loading_indicators": [
                        {
                            "tool_name": indicator.tool_name,
                            "state": indicator.state.value,
                            "progress": indicator.progress,
                            "message": indicator.message,
                            "estimated_time": indicator.estimated_time
                        } for indicator in ui_state.loading_indicators
                    ],
                    "error_states": [
                        {
                            "error_type": error.error_type,
                            "message": error.message,
                            "severity": error.severity.value,
                            "recovery_actions": error.recovery_actions,
                            "context": error.context
                        } for error in ui_state.error_states
                    ],
                    "content_sections": [
                        {
                            "content": section.content,
                            "content_type": section.content_type.value,
                            "metadata": section.metadata,
                            "order": section.order
                        } for section in ui_state.content_sections
                    ],
                    "interactive_elements": [
                        {
                            "element_type": element.element_type,
                            "element_id": element.element_id,
                            "properties": element.properties,
                            "actions": element.actions
                        } for element in ui_state.interactive_elements
                    ]
                })
                
            except Exception as e:
                logger.warning(f"Failed to get UI state from intelligent chat manager: {e}")
                ui_state_data["error"] = str(e)
        
        return {
            "status": "success",
            "ui_state": ui_state_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"UI state error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get UI state: {e}")

if __name__ == "__main__":
    import uvicorn
    try:
        logger.info("Starting FastAPI application...")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
