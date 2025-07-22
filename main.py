
from dotenv import load_dotenv
from pydantic import BaseModel as PydanticBaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain.tools import Tool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from tools import search_tool, wiki_tool, save_tool
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from langchain_core.messages import HumanMessage, AIMessage
from langchain.schema import Document

load_dotenv()

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

# -------------------- 🔍 RAG SETUP -----------------------

import logging

# Load and index documents (you can replace this with PDFLoader, WebLoader, etc.)
logging.info("Loading text knowledge base documents...")
loader = TextLoader("data/knowledge.txt")  # 👈 Your knowledge source
documents = loader.load()
logging.info(f"Loaded {len(documents)} text documents.")

# Split documents into chunks with improved chunk size and overlap to avoid warnings
logging.info("Splitting text documents into chunks...")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
split_docs = text_splitter.split_documents(documents)
logging.info(f"Split into {len(split_docs)} text chunks.")

# Embed and store in FAISS
logging.info("Embedding text chunks and creating vector store...")
embedding = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
text_vectorstore = FAISS.from_documents(split_docs, embedding)
text_retriever = text_vectorstore.as_retriever()
logging.info("Text vector store created.")

# Remove Excel documents from RAG retriever to use alternative process for Excel knowledge base

# Define RAG tool function only for text knowledge base
def rag_tool_func(query: str) -> str:
    docs = text_retriever.get_relevant_documents(query)
    # Collect page contents
    contents = [doc.page_content for doc in docs[:5]]
    # Collect sources, default to www.bt.com if not present
    sources = []
    for doc in docs[:5]:
        if hasattr(doc, 'metadata') and 'source' in doc.metadata:
            sources.append(doc.metadata['source'])
        else:
            sources.append("www.bt.com")
    # Store sources in a global variable for access in chat endpoint
    global last_rag_sources
    last_rag_sources = list(set(sources))
    return "\n".join(contents)

rag_tool = Tool.from_function(
    func=rag_tool_func,
    name="ContextRetriever",
    description="Use this tool to fetch relevant information from the text knowledge base using RAG."
)

import re
from functools import lru_cache

@lru_cache(maxsize=1)
def load_support_knowledge_base():
    """Load and cache the customer support knowledge base Excel sheets."""
    xls = pd.ExcelFile('data/customer_support_knowledge_base.xlsx')
    df_categories = pd.read_excel(xls, sheet_name='Categories')
    df_intents = pd.read_excel(xls, sheet_name='Intents')
    df_support_samples = pd.read_excel(xls, sheet_name='SupportSamples')
    return df_categories, df_intents, df_support_samples

def support_knowledge_tool_func(query: str) -> str:
    """
    Fetch support response from the customer support knowledge base based on the query.
    Matches query to intents and returns corresponding support sample responses.
    """
    try:
        df_categories, df_intents, df_support_samples = load_support_knowledge_base()

        q = query.lower()

        # Improved matching: check if any word in intent is in query or vice versa
        def intent_matches_query(intent: str, query: str) -> bool:
            intent_words = set(intent.lower().split())
            query_words = set(query.lower().split())
            return not intent_words.isdisjoint(query_words) or intent.lower() in query or query in intent.lower()

        matched_intents = df_intents[df_intents['intent'].apply(lambda intent: intent_matches_query(intent, q))]

        if matched_intents.empty:
            return "Sorry, I could not find any support information matching your query."

        # For each matched intent, find support samples and return the first matching response
        for _, intent_row in matched_intents.iterrows():
            intent_id = intent_row['intent_id']
            samples = df_support_samples[df_support_samples['intent_id'] == intent_id]
            if not samples.empty:
                # Return the first sample response
                response = samples.iloc[0]['response']
                return response

        return "Sorry, I could not find any support information matching your query."
    except Exception as e:
        return f"Error accessing support knowledge base: {str(e)}"

support_knowledge_tool = Tool.from_function(
    func=support_knowledge_tool_func,
    name="SupportKnowledgeBase",
    description="Use this tool to fetch customer support responses from the Excel knowledge base."
)

# ---------------------- 🤖 Agent Setup -----------------------

# Prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
          You are a highly professional, friendly, and knowledgeable customer support agent for a telecom company. Your mission is to provide clear, accurate, and concise answers to customer questions using the available knowledge base and tools. Always maintain a polite, empathetic, and customer-focused tone, ensuring the customer feels valued and understood.

          Always use the ContextRetriever tool first to check the company knowledge base for relevant information before using any other tools or providing an answer.

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

# Serve frontend static files
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import Request

from fastapi.staticfiles import StaticFiles

# Mount frontend directory as static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def root():
    return FileResponse("frontend/chat.html")

# Request model for chat input
class ChatRequest(PydanticBaseModel):
    query: str

# Response model for chat output
class ChatResponse(PydanticBaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools_used: list[str]


import re


from langchain_core.messages import HumanMessage, AIMessage
from fastapi import Request
import logging

MAX_CHAT_HISTORY = 10  # Limit chat history length to last 10 messages

import re

def exact_knowledge_lookup(query: str) -> str:
    """
    Perform an exact lookup in knowledge.txt for the query.
    Returns the answer if found, else empty string.
    """
    try:
        with open("data/knowledge.txt", "r", encoding="utf-8") as f:
            content = f.read()
        # Use regex to find Q&A pairs
        pattern = re.compile(r"Q:\s*(.+?)\nA:\s*(.+?)(?=\nQ:|\Z)", re.DOTALL)
        matches = pattern.findall(content)
        for q, a in matches:
            if q.strip().lower() == query.strip().lower():
                return a.strip()
        return ""
    except Exception as e:
        logging.error(f"Error reading knowledge.txt: {e}")
        return ""

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: Request, chat_request: ChatRequest):
    try:
        # Use request state to store chat history per request (thread-safe)
        if not hasattr(request.state, "chat_history_store"):
            request.state.chat_history_store = []

        # Append user message to chat history
        request.state.chat_history_store.append(("human", chat_request.query))

        # Limit chat history length
        if len(request.state.chat_history_store) > MAX_CHAT_HISTORY:
            request.state.chat_history_store[:] = request.state.chat_history_store[-MAX_CHAT_HISTORY:]

        # Check exact knowledge base lookup first
        exact_answer = exact_knowledge_lookup(chat_request.query)
        if exact_answer:
            # Return exact answer directly
            response = ResearchResponse(
                topic=chat_request.query,
                summary=exact_answer,
                sources=["data/knowledge.txt"],
                tools_used=["ExactKnowledgeLookup"]
            )
            # Append assistant response to chat history as tuple
            request.state.chat_history_store.append(("assistant", exact_answer))
            return response.dict()

        # Convert chat_history_store to messages list expected by agent_executor
        messages = []
        for role, content in request.state.chat_history_store:
            if role == "user" or role == "human":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        # Invoke agent with query and chat history (as messages)
        raw_response = agent_executor.invoke({"query": chat_request.query, "chat_history": messages})

        logging.info(f"Raw response type: {type(raw_response)}")
        logging.info(f"Raw response content: {raw_response}")

        output = raw_response.get("output", "")

        # Extract JSON string inside triple backticks or fallback to entire output
        import re
        match = re.search(r"```json\\n(.+?)```", output, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Try to parse entire output as JSON string fallback
            json_str = output

        try:
            # Pass raw JSON string to parser.parse()
            structured_response = parser.parse(json_str)
            # Override sources with last_rag_sources if available
            if 'last_rag_sources' in globals() and last_rag_sources:
                structured_response.sources = last_rag_sources
        except Exception as parse_exc:
            logging.error(f"Failed to parse LLM output JSON: {parse_exc}")
            logging.error(f"Raw LLM output: {output}")
            # Fallback response for unparseable output
            structured_response = ResearchResponse(
                topic="Unknown",
                summary="Sorry, I couldn't understand the response. Please try rephrasing your question or contact human support.",
                sources=[],
                tools_used=[]
            )

        # Append assistant response to chat history as tuple
        request.state.chat_history_store.append(("assistant", output))

        return structured_response.dict()
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logging.error(f"Exception traceback: {tb}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {e}")
