#!/usr/bin/env python3
"""
Minimal test script to identify hanging issues
"""

import time
import sys

def test_step(step_name, func):
    """Test a specific step"""
    print(f"Testing: {step_name}")
    start_time = time.time()
    try:
        result = func()
        elapsed = time.time() - start_time
        print(f"  ✓ {step_name} completed in {elapsed:.2f}s")
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ✗ {step_name} failed in {elapsed:.2f}s: {e}")
        return None

def main():
    """Test each component step by step"""
    print("Minimal component testing...")
    print("=" * 50)
    
    # Test 1: Basic imports
    def test_basic_imports():
        import os, json, logging
        return True
    
    test_step("Basic imports", test_basic_imports)
    
    # Test 2: Database
    def test_database():
        from database import SessionLocal
        return True
    
    test_step("Database import", test_database)
    
    # Test 3: Models
    def test_models():
        from models import User, UserSession
        return True
    
    test_step("Models import", test_models)
    
    # Test 4: LLM
    def test_llm():
        from langchain_google_genai import ChatGoogleGenerativeAI
        return True
    
    test_step("LLM import", test_llm)
    
    # Test 5: Agent creation
    def test_agent():
        from langchain.agents import create_tool_calling_agent, AgentExecutor
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import PydanticOutputParser
        
        # Create a simple prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant."),
            ("human", "{query}")
        ])
        
        # Create a simple parser
        parser = PydanticOutputParser(pydantic_object=None)
        
        return True
    
    test_step("Agent components", test_agent)
    
    # Test 6: FastAPI
    def test_fastapi():
        from fastapi import FastAPI
        app = FastAPI()
        return app
    
    test_step("FastAPI creation", test_fastapi)
    
    print("=" * 50)
    print("Minimal testing completed.")

if __name__ == "__main__":
    main()
