#!/usr/bin/env python3
"""
Test script to verify that the LLM integration is working correctly.
"""

import sys
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from intelligent_chat.chat_manager import ChatManager
from intelligent_chat.tool_orchestrator import ToolOrchestrator
from intelligent_chat.context_retriever import ContextRetriever
from intelligent_chat.response_renderer import ResponseRenderer
from memory_layer_manager import MemoryLayerManager
from memory_config import load_config

# Import LLM and agent components
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from tools import (
    search_tool, wiki_tool, save_tool, bt_website_tool, 
    bt_support_hours_tool_instance, bt_plans_tool, multi_tool_tool,
    intelligent_orchestrator_tool, context_memory
)

async def test_llm_integration():
    """Test that the LLM integration is working correctly."""
    
    print("🤖 Testing LLM Integration")
    print("=" * 50)
    
    # Check if Google API key is available
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("❌ GOOGLE_API_KEY not found in environment variables")
        print("Please set your Google API key to test LLM integration")
        return
    
    print("✅ Google API key found")
    
    try:
        # Initialize LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.3,
            google_api_key=google_api_key
        )
        print("✅ LLM initialized successfully")
        
        # Initialize tools
        tools = [
            search_tool,
            wiki_tool,
            bt_website_tool,
            bt_support_hours_tool_instance,
            bt_plans_tool,
            save_tool
        ]
        print(f"✅ {len(tools)} tools loaded")
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are a helpful customer support agent for a telecom company. 
            Provide clear, concise, and helpful responses to customer queries.
            Use the available tools when needed to get accurate information.
            """),
            ("placeholder", "{chat_history}"),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        # Create agent and executor
        agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=tools)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        print("✅ Agent and executor created successfully")
        
        # Initialize memory and chat components
        memory_config = load_config()
        memory_manager = MemoryLayerManager(config=memory_config)
        
        tools_dict = {tool.name: tool for tool in tools}
        tool_orchestrator = ToolOrchestrator(available_tools=tools_dict)
        context_retriever = ContextRetriever(memory_manager=memory_manager)
        response_renderer = ResponseRenderer()
        
        # Initialize ChatManager with LLM integration
        chat_manager = ChatManager(
            tool_orchestrator=tool_orchestrator,
            context_retriever=context_retriever,
            response_renderer=response_renderer,
            memory_manager=memory_manager,
            llm=llm,
            agent_executor=agent_executor
        )
        print("✅ ChatManager initialized with LLM integration")
        
        # Test queries
        test_queries = [
            "my broadband is not working",
            "How do I upgrade my plan?",
            "What are BT's support hours?"
        ]
        
        print("\n" + "=" * 50)
        print("Testing LLM-powered responses:")
        print("=" * 50)
        
        for i, query in enumerate(test_queries, 1):
            print(f"\nTest {i}: '{query}'")
            print("-" * 30)
            
            try:
                response = await chat_manager.process_message(
                    message=query,
                    user_id=f"llm_test_user_{i}",
                    session_id=f"llm_test_session_{i}"
                )
                
                print(f"Response: {response.content}")
                print(f"Tools Used: {response.tools_used}")
                print(f"Confidence: {response.confidence_score:.2f}")
                print(f"Execution Time: {response.execution_time:.2f}s")
                
                # Check if response looks like LLM-generated content
                if len(response.content) > 100 and not response.content.startswith("Mock context"):
                    print("✅ PASS: LLM-generated response detected")
                else:
                    print("⚠️  WARNING: Response may not be LLM-generated")
                
            except Exception as e:
                print(f"❌ ERROR: {e}")
        
        print("\n" + "=" * 50)
        print("✅ LLM integration test completed!")
        
    except Exception as e:
        print(f"❌ LLM integration test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_integration())