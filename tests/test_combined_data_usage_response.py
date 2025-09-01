#!/usr/bin/env python3
"""
Test script to see what the combined data usage response looks like
"""

import logging
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_combined_response():
    """Test what the combined data usage response looks like"""
    try:
        logger.info("Testing combined data usage response...")
        
        # Import required modules
        from main import (
            support_knowledge_tool_func, 
            bt_website_tool, 
            rag_tool_func, 
            intelligent_orchestrator_tool
        )
        
        test_query = "How can I check my data usage?"
        logger.info(f"Testing query: '{test_query}'")
        
        # Simulate the multi-tool response combination logic from main.py
        summary = ""
        tools_used = []
        
        # 1. Start with support knowledge base
        try:
            support_result = support_knowledge_tool_func(test_query)
            if support_result and len(support_result) > 20:
                tools_used.append("SupportKnowledgeBase")
                summary = support_result
                logger.info("✅ Added SupportKnowledgeBase result")
        except Exception as e:
            logger.error(f"SupportKnowledgeBase error: {e}")
        
        # 2. Add BT website information
        try:
            bt_website_result = bt_website_tool.invoke({"query": "check data usage balance allowance"})
            if bt_website_result and len(bt_website_result) > 20:
                tools_used.append("BTWebsiteSearch")
                if summary:
                    summary += f"\n\n**Additional BT Information:**\n{bt_website_result}"
                else:
                    summary = bt_website_result
                logger.info("✅ Added BTWebsiteSearch result")
        except Exception as e:
            logger.error(f"BTWebsiteSearch error: {e}")
        
        # 3. Add context from knowledge base
        try:
            rag_result = rag_tool_func("data usage check balance mobile app")
            if rag_result and len(rag_result) > 20:
                tools_used.append("ContextRetriever")
                if summary:
                    summary += f"\n\n**Additional Help:**\n{rag_result}"
                else:
                    summary = rag_result
                logger.info("✅ Added ContextRetriever result")
        except Exception as e:
            logger.error(f"ContextRetriever error: {e}")
        
        # 4. Use intelligent orchestrator for comprehensive response
        try:
            orchestrator_result = intelligent_orchestrator_tool.invoke({"query": test_query})
            if orchestrator_result and len(orchestrator_result) > 50:
                tools_used.append("IntelligentToolOrchestrator")
                # If orchestrator provides a better comprehensive answer, use it
                if len(orchestrator_result) > len(summary or ""):
                    summary = orchestrator_result
                logger.info("✅ Used IntelligentToolOrchestrator result")
        except Exception as e:
            logger.error(f"IntelligentToolOrchestrator error: {e}")
        
        # Display the final combined response
        logger.info(f"\n=== FINAL COMBINED RESPONSE ===")
        logger.info(f"Query: '{test_query}'")
        logger.info(f"Tools used: {tools_used}")
        logger.info(f"Response length: {len(summary)} characters")
        logger.info(f"\nFinal Response:")
        logger.info("=" * 80)
        logger.info(summary)
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Combined response test failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🚀 Starting combined data usage response test...")
    
    success = test_combined_response()
    
    if success:
        logger.info("✅ Combined response test completed!")
        return 0
    else:
        logger.error("❌ Combined response test failed!")
        return 1

if __name__ == "__main__":
    exit(main())