#!/usr/bin/env python3
"""
Test script to verify memory cleanup functionality
"""

import logging
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_memory_cleanup():
    """Test memory cleanup functionality"""
    try:
        logger.info("Testing memory cleanup functionality...")
        
        from backend.memory_config import load_config
        from backend.memory_layer_manager import MemoryLayerManager
        
        # Load configuration
        config = load_config()
        
        # Initialize memory manager
        memory_manager = MemoryLayerManager(config=config)
        logger.info("✅ Memory manager initialized successfully")
        
        # Test user session cleanup
        test_user_id = "test_user_cleanup"
        test_session_id = "test_session_cleanup"
        
        logger.info(f"Testing cleanup for user: {test_user_id}")
        cleanup_result = memory_manager.cleanup_user_session_data(test_user_id, test_session_id)
        
        if cleanup_result.errors:
            logger.error(f"❌ Cleanup had errors: {cleanup_result.errors}")
            return False
        else:
            logger.info(f"✅ Cleanup completed successfully:")
            logger.info(f"  - Conversations cleaned: {cleanup_result.conversations_cleaned}")
            logger.info(f"  - Context entries cleaned: {cleanup_result.context_entries_cleaned}")
            logger.info(f"  - Tool metrics cleaned: {cleanup_result.tool_metrics_cleaned}")
            logger.info(f"  - Duration: {cleanup_result.cleanup_duration:.3f}s")
            return True
        
    except Exception as e:
        logger.error(f"❌ Memory cleanup test failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🚀 Starting memory cleanup tests...")
    
    success = test_memory_cleanup()
    
    if success:
        logger.info("✅ Memory cleanup test passed!")
        return 0
    else:
        logger.error("❌ Memory cleanup test failed!")
        return 1

if __name__ == "__main__":
    exit(main())