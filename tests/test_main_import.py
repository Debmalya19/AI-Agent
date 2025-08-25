#!/usr/bin/env python3
"""
Test script to import main module step by step
"""

import time
import sys

def test_main_import():
    """Test importing the main module"""
    print("Testing main module import...")
    print("=" * 50)
    
    start_time = time.time()
    
    try:
        # Import step by step
        print("1. Importing basic modules...")
        import os
        import json
        import logging
        import datetime
        import hashlib
        import secrets
        import pandas
        import sqlalchemy
        print("   ✓ Basic modules imported")
        
        print("2. Importing FastAPI modules...")
        from fastapi import FastAPI, HTTPException, Request, Response, status, Cookie, Form
        from fastapi.responses import FileResponse, JSONResponse
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.security import HTTPBasic, HTTPBasicCredentials
        from fastapi.staticfiles import StaticFiles
        print("   ✓ FastAPI modules imported")
        
        print("3. Importing LangChain modules...")
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain.agents import create_tool_calling_agent, AgentExecutor
        from langchain.tools import Tool
        print("   ✓ LangChain modules imported")
        
        print("4. Importing local modules...")
        from database import SessionLocal, get_db
        from models import KnowledgeEntry, ChatHistory, SupportIntent, SupportResponse, User, UserSession
        from db_utils import search_knowledge_entries, get_knowledge_entries, save_chat_history, get_chat_history
        print("   ✓ Local modules imported")
        
        print("5. Importing tools...")
        from tools import search_tool, wiki_tool, save_tool
        from customer_db_tool import get_customer_orders
        print("   ✓ Tools imported")
        
        print("6. Importing RAG orchestrator...")
        from enhanced_rag_orchestrator import search_with_priority
        print("   ✓ RAG orchestrator imported")
        
        print("7. Testing LLM import...")
        from langchain_google_genai import ChatGoogleGenerativeAI
        print("   ✓ LLM import successful")
        
        print("8. Importing main module...")
        import main
        print("   ✓ Main module imported successfully!")
        
        elapsed = time.time() - start_time
        print(f"\nTotal import time: {elapsed:.2f}s")
        return True
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"✗ Import failed after {elapsed:.2f}s: {e}")
        return False

if __name__ == "__main__":
    test_main_import()
