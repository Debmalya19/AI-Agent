#!/usr/bin/env python3
"""
Test script to verify data usage query handling with multiple tools
"""

import logging
import sys
import os
import json

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_data_usage_query():
    """Test data usage query processing"""
    try:
        logger.info("Testing data usage query processing...")
        
        # Import required modules
        from main import (
            support_knowledge_tool_func, 
            bt_website_tool, 
            rag_tool_func, 
            intelligent_orchestrator_tool
        )
        
        test_query = "How can I check my data usage?"
        logger.info(f"Testing query: '{test_query}'")
        
        # Test each tool that should be triggered for data usage queries
        tools_used = []
        results = {}
        
        # 1. Test Support Knowledge Base
        try:
            logger.info("Testing SupportKnowledgeBase...")
            support_result = support_knowledge_tool_func(test_query)
            if support_result and len(support_result) > 20:
                tools_used.append("SupportKnowledgeBase")
                results["SupportKnowledgeBase"] = support_result[:100] + "..."
                logger.info("✅ SupportKnowledgeBase returned result")
            else:
                logger.warning("❌ SupportKnowledgeBase returned empty/short result")
        except Exception as e:
            logger.error(f"❌ SupportKnowledgeBase error: {e}")
        
        # 2. Test BT Website Search
        try:
            logger.info("Testing BTWebsiteSearch...")
            bt_result = bt_website_tool.invoke({"query": "check data usage balance allowance"})
            if bt_result and len(bt_result) > 20:
                tools_used.append("BTWebsiteSearch")
                results["BTWebsiteSearch"] = bt_result[:100] + "..."
                logger.info("✅ BTWebsiteSearch returned result")
            else:
                logger.warning("❌ BTWebsiteSearch returned empty/short result")
        except Exception as e:
            logger.error(f"❌ BTWebsiteSearch error: {e}")
        
        # 3. Test Context Retriever
        try:
            logger.info("Testing ContextRetriever...")
            rag_result = rag_tool_func("data usage check balance mobile app")
            if rag_result and len(rag_result) > 20:
                tools_used.append("ContextRetriever")
                results["ContextRetriever"] = rag_result[:100] + "..."
                logger.info("✅ ContextRetriever returned result")
            else:
                logger.warning("❌ ContextRetriever returned empty/short result")
        except Exception as e:
            logger.error(f"❌ ContextRetriever error: {e}")
        
        # 4. Test Intelligent Orchestrator
        try:
            logger.info("Testing IntelligentToolOrchestrator...")
            orchestrator_result = intelligent_orchestrator_tool.invoke({"query": test_query})
            if orchestrator_result and len(orchestrator_result) > 50:
                tools_used.append("IntelligentToolOrchestrator")
                results["IntelligentToolOrchestrator"] = orchestrator_result[:100] + "..."
                logger.info("✅ IntelligentToolOrchestrator returned result")
            else:
                logger.warning("❌ IntelligentToolOrchestrator returned empty/short result")
        except Exception as e:
            logger.error(f"❌ IntelligentToolOrchestrator error: {e}")
        
        # Summary
        logger.info(f"\n=== DATA USAGE QUERY TEST RESULTS ===")
        logger.info(f"Query: '{test_query}'")
        logger.info(f"Tools that returned results: {len(tools_used)}")
        logger.info(f"Tools used: {tools_used}")
        
        for tool, result in results.items():
            logger.info(f"\n{tool}:")
            logger.info(f"  Result preview: {result}")
        
        if len(tools_used) >= 2:
            logger.info("✅ Multi-tool orchestration working - multiple tools returned results")
            return True
        else:
            logger.warning("❌ Multi-tool orchestration not working properly - too few tools returned results")
            return False
        
    except Exception as e:
        logger.error(f"❌ Data usage query test failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🚀 Starting data usage query test...")
    
    success = test_data_usage_query()
    
    if success:
        logger.info("✅ Data usage query test passed!")
        return 0
    else:
        logger.error("❌ Data usage query test failed!")
        return 1

if __name__ == "__main__":
    exit(main())