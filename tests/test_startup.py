#!/usr/bin/env python3
"""
Test script to verify startup logging and memory manager initialization
"""

import logging
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging to see all messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_memory_manager_initialization():
    """Test memory manager initialization"""
    try:
        logger.info("Testing Memory Layer Manager initialization...")
        
        from backend.memory_config import load_config
        from backend.memory_layer_manager import MemoryLayerManager
        
        # Load configuration
        config = load_config()
        logger.info(f"Configuration loaded: {config}")
        
        # Initialize memory manager
        memory_manager = MemoryLayerManager(config=config)
        logger.info("✅ Memory Layer Manager initialized successfully")
        
        # Test basic functionality
        stats = memory_manager.get_memory_stats()
        logger.info(f"Memory stats: {stats.to_dict()}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Memory manager initialization failed: {e}")
        return False

def test_tools_integration():
    """Test tools integration with shared memory manager"""
    try:
        logger.info("Testing tools integration...")
        
        from backend.memory_config import load_config
        from backend.memory_layer_manager import MemoryLayerManager
        from backend.tools import set_shared_memory_manager
        
        # Initialize memory manager
        config = load_config()
        memory_manager = MemoryLayerManager(config=config)
        
        # Set shared memory manager
        set_shared_memory_manager(memory_manager)
        logger.info("✅ Shared memory manager set successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Tools integration failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🚀 Starting startup tests...")
    
    success = True
    
    # Test memory manager
    if not test_memory_manager_initialization():
        success = False
    
    # Test tools integration
    if not test_tools_integration():
        success = False
    
    if success:
        logger.info("✅ All startup tests passed!")
        return 0
    else:
        logger.error("❌ Some startup tests failed!")
        return 1

if __name__ == "__main__":
    exit(main())