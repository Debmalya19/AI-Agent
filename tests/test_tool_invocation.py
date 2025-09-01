#!/usr/bin/env python3
"""
Test script to verify that tool invocation is working correctly with the new invoke() method
"""

import logging
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_tool_invocation():
    """Test that tools can be invoked using the new invoke() method"""
    try:
        logger.info("Testing tool invocation with invoke() method...")
        
        # Import tools from main
        from main import bt_plans_tool, bt_support_hours_tool_instance, intelligent_orchestrator_tool
        
        # Test BT Plans tool
        logger.info("Testing BT Plans tool...")
        try:
            result = bt_plans_tool.invoke({"query": "What are your mobile plans?"})
            logger.info(f"✅ BT Plans tool invoked successfully: {len(result)} characters returned")
        except Exception as e:
            logger.error(f"❌ BT Plans tool failed: {e}")
            return False
        
        # Test BT Support Hours tool
        logger.info("Testing BT Support Hours tool...")
        try:
            result = bt_support_hours_tool_instance.invoke({"query": "What are your support hours?"})
            logger.info(f"✅ BT Support Hours tool invoked successfully: {len(result)} characters returned")
        except Exception as e:
            logger.error(f"❌ BT Support Hours tool failed: {e}")
            return False
        
        # Test Intelligent Orchestrator tool
        logger.info("Testing Intelligent Orchestrator tool...")
        try:
            result = intelligent_orchestrator_tool.invoke({"query": "Help me with my account"})
            logger.info(f"✅ Intelligent Orchestrator tool invoked successfully: {len(result)} characters returned")
        except Exception as e:
            logger.error(f"❌ Intelligent Orchestrator tool failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Tool invocation test failed: {e}")
        return False

def test_deprecated_method_warning():
    """Test that using the old .func() method would generate a warning"""
    try:
        logger.info("Testing that deprecated .func() method is no longer used...")
        
        # Import a tool
        from main import bt_plans_tool
        
        # Check that the tool has invoke method
        if hasattr(bt_plans_tool, 'invoke'):
            logger.info("✅ Tool has invoke() method")
        else:
            logger.error("❌ Tool missing invoke() method")
            return False
        
        # Check that we're not using .func() anywhere in main.py
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if '.func(' in content:
                logger.error("❌ Found .func() usage in main.py")
                return False
            else:
                logger.info("✅ No .func() usage found in main.py")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Deprecated method test failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🚀 Starting tool invocation tests...")
    
    success = True
    
    # Test tool invocation
    if not test_tool_invocation():
        success = False
    
    # Test deprecated method warning
    if not test_deprecated_method_warning():
        success = False
    
    if success:
        logger.info("✅ All tool invocation tests passed!")
        return 0
    else:
        logger.error("❌ Some tool invocation tests failed!")
        return 1

if __name__ == "__main__":
    exit(main())