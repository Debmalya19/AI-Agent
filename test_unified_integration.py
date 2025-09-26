#!/usr/bin/env python3
"""
Test script to verify unified authentication integration in main.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all unified authentication imports work correctly"""
    try:
        # Test main.py imports
        from backend.unified_auth import get_current_user_flexible, AuthenticatedUser
        from backend.unified_models import UnifiedUser, UnifiedUserSession, UnifiedChatHistory
        print("✓ Main application imports successful")
        
        # Test voice_api.py imports
        from backend.voice_api import voice_router
        print("✓ Voice API imports successful")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_authentication_dependencies():
    """Test that authentication dependencies are properly configured"""
    try:
        from fastapi import Depends
        from backend.unified_auth import get_current_user_flexible
        
        # Test that the dependency function exists and is callable
        assert callable(get_current_user_flexible)
        print("✓ Authentication dependency function is callable")
        
        # Test that we can create a Depends object
        dep = Depends(get_current_user_flexible)
        print("✓ Authentication dependency can be created")
        
        return True
    except Exception as e:
        print(f"✗ Authentication dependency error: {e}")
        return False

def test_unified_models():
    """Test that unified models are properly configured"""
    try:
        from backend.unified_models import UnifiedUser, UnifiedUserSession
        from backend.database import Base
        
        # Test that models inherit from Base
        assert issubclass(UnifiedUser, Base)
        assert issubclass(UnifiedUserSession, Base)
        print("✓ Unified models properly inherit from Base")
        
        # Test that models have required attributes
        assert hasattr(UnifiedUser, 'id')
        assert hasattr(UnifiedUser, 'user_id')
        assert hasattr(UnifiedUser, 'username')
        assert hasattr(UnifiedUser, 'email')
        print("✓ Unified models have required attributes")
        
        return True
    except Exception as e:
        print(f"✗ Unified models error: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing unified authentication integration...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_authentication_dependencies,
        test_unified_models
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Unified authentication integration is successful.")
        return 0
    else:
        print("❌ Some tests failed. Please check the integration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())