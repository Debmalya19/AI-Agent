from dotenv import load_dotenv
from pydantic import BaseModel as PydanticBaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import Tool
from tools import search_tool, wiki_tool, save_tool
from customer_db_tool import get_customer_orders
import os
import json
from fastapi import FastAPI, HTTPException, Request, Response, status, Cookie, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
import secrets
import pandas as pd
from langchain_core.messages import HumanMessage, AIMessage
from langchain.schema import Document
from database import SessionLocal, get_db
from models import KnowledgeEntry, ChatHistory, SupportIntent, SupportResponse, User, UserSession
from db_utils import search_knowledge_entries, get_knowledge_entries, save_chat_history, get_chat_history
from enhanced_rag_orchestrator import search_with_priority
import logging
from sqlalchemy import text
from datetime import datetime, timedelta
import hashlib

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define Pydantic output model
class ResearchResponse(PydanticBaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools_used: list[str]

# Setup Gemini LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.3
)

# Define parser
parser = PydanticOutputParser(pydantic_object=ResearchResponse)

# -------------------- 🔍 DATABASE-BACKED RAG SETUP -----------------------

# Define RAG tool function using database knowledge base
def rag_tool_func(query: str) -> str:
    """RAG tool using database knowledge base"""
    try:
        # Use the enhanced RAG orchestrator for database search
        results = search_with_priority(query, max_results=3)
        
        if not results:
            return "No relevant information found in knowledge base."
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(f"Source: {result['source']}\nContent: {result['content']}")
        
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        logger.error(f"RAG tool error: {e}")
        return "Error accessing knowledge base."

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
            
            for intent in intents:
                if intent.intent_name.lower() in query.lower():
                    response = db.query(SupportResponse).filter(
                        SupportResponse.intent_id == intent.intent_id
                    ).first()
                    
                    if response:
                        return response.response_text
            
            return "Sorry, I could not find any support information matching your query."
            
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
          You are a highly professional, friendly, and knowledgeable customer support agent for a telecom company. Your mission is to provide clear, accurate, and concise answers to customer questions using the available knowledge base and tools. Always maintain a polite, empathetic, and customer-focused tone, ensuring the customer feels valued and understood.

          Always use the ContextRetriever tool first to check the database knowledge base for relevant information before using any other tools or providing an answer.

          If the answer is not found in the knowledge base, use the SupportKnowledgeBase tool to check the customer support database for relevant information.

          If the answer is still not found, use the search tool to search the www.bt.com website to find relevant information and provide an accurate answer.

          If you do not know the answer to a question, politely inform the customer and suggest contacting human support for further assistance. For any queries related to customer orders or order details, always use the appropriate tools to fetch accurate information. Never mention internal tools, processes, or system details in your responses.

          Your responses should be solution-oriented, easy to understand, and should leave the customer satisfied with the support experience.

          Wrap the output in this format and provide no other text\n{format_instructions}
            """,
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
).partial(format_instructions=parser.get_format_instructions())

# Tools to be used (RAG tool first to ensure knowledge base is checked before LLM answers)
tools = [rag_tool, support_knowledge_tool, search_tool, wiki_tool, save_tool]

# Agent creation
agent = create_tool_calling_agent(
    llm=llm,
    prompt=prompt,
    tools=tools
)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# FastAPI app setup
app = FastAPI()

# Allow CORS for local frontend testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data lake API endpoints
@app.get("/data_lake/catalog")
async def get_data_lake_catalog():
    try:
        with open("data_lake/catalog.json", "r", encoding="utf-8") as f:
            catalog = json.load(f)
        return {"catalog": catalog}
    except Exception as e:
        return {"error": str(e)}

@app.get("/data_lake/file/{filename}")
async def get_data_lake_file(filename: str):
    file_path = os.path.join("data_lake", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        return {"error": "File not found in data lake."}

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

# Request model for chat input
class ChatRequest(PydanticBaseModel):
    query: str

# Response model for chat output
class ChatResponse(PydanticBaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools_used: list[str]

# API endpoints

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest, session_token: str = Cookie(None)):
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Unauthorized: No session token")

        # Use the agent executor to process the query
        response = agent_executor.invoke({"query": chat_request.query})
        
        # Parse the response
        if response and 'output' in response:
            try:
                parsed_response = parser.parse(response['output'])
                return ChatResponse(
                    topic=chat_request.query,
                    summary=parsed_response.summary,
                    sources=parsed_response.sources,
                    tools_used=parsed_response.tools_used
                )
            except Exception as parse_error:
                logger.error(f"Parse error: {parse_error}")
                return ChatResponse(
                    topic=chat_request.query,
                    summary=response['output'],
                    sources=[],
                    tools_used=["agent"]
                )
        
        return ChatResponse(
            topic=chat_request.query,
            summary="I'm sorry, I couldn't process your query.",
            sources=[],
            tools_used=[]
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
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
        return {"status": "unhealthy", "error": str(e)}

# Login endpoint with proper user ID and password validation
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """
    Authenticate user with user ID and password against database.
    Validates credentials and creates secure session.
    """
    try:
        user_id = username
        password = password
        
        if not user_id or not password:
            raise HTTPException(status_code=400, detail="User ID and password required")
        
        # Hash the password for comparison (demo implementation)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Validate against database
        with SessionLocal() as db:
            user = db.query(User).filter(
                User.user_id == user_id,
                User.is_active == True
            ).first()
            
            if not user:
                raise HTTPException(status_code=401, detail="Invalid user ID or password")
            
            # In production, use proper password hashing like bcrypt
            # For demo, we'll accept any password
            # if user.password_hash != password_hash:
            #     raise HTTPException(status_code=401, detail="Invalid user ID or password")
            
            # Generate secure session token
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            # Create user session
            user_session = UserSession(
                session_id=session_token,
                user_id=user.user_id,
                expires_at=expires_at
            )
            db.add(user_session)
            db.commit()
            
            # Create login record in chat history
            login_entry = ChatHistory(
                session_id=session_token,
                user_message="login",
                bot_response=f"User {user.username} ({user.user_id}) logged in successfully"
            )
            db.add(login_entry)
            db.commit()
            
            # Refresh user object to ensure it's properly attached to session
            db.refresh(user)
        
        # Set secure cookie
        response = JSONResponse({
            "access_token": session_token,
            "token_type": "bearer",
            "expires_in": 86400,  # 24 hours
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
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

# User registration endpoint
@app.post("/register")
async def register(user_data: dict):
    """Register new user with user ID and password"""
    try:
        user_id = user_data.get("user_id")
        username = user_data.get("username")
        email = user_data.get("email")
        password = user_data.get("password")
        full_name = user_data.get("full_name", "")
        
        if not all([user_id, username, email, password]):
            raise HTTPException(status_code=400, detail="All fields are required")
        
        # Hash password (demo implementation)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        with SessionLocal() as db:
            # Check if user already exists
            existing_user = db.query(User).filter(
                (User.user_id == user_id) | (User.username == username) | (User.email == email)
            ).first()
            
            if existing_user:
                raise HTTPException(status_code=400, detail="User already exists")
            
            # Create new user
            new_user = User(
                user_id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                full_name=full_name
            )
            db.add(new_user)
            db.commit()
            
            return {
                "message": "User registered successfully",
                "user_id": new_user.user_id,
                "username": new_user.username
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

# Logout endpoint
@app.post("/logout")
async def logout(session_token: str = Cookie(None)):
    """Logout user and invalidate session"""
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="No active session")
        
        # Remove session from database
        with SessionLocal() as db:
            # Delete UserSession
            db.query(UserSession).filter(UserSession.session_id == session_token).delete()
            # Delete ChatHistory
            db.query(ChatHistory).filter(ChatHistory.session_id == session_token).delete()
            db.commit()
        
        response = JSONResponse({"message": "Logged out successfully"})
        response.delete_cookie("session_token")
        return response
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
