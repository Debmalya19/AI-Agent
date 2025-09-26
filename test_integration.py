#!/usr/bin/env python3
"""
Test script to verify admin-dashboard backend integration
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, '.')

print("Testing backend integration...")

try:
    # Test direct backend import
    from backend import database
    print("✓ backend.database import successful")

    from backend import models
    print("✓ backend.models import successful")

    # Test integration module
    from admin_dashboard.backend import integration
    print(f"✓ Integration import successful: AI_AGENT_BACKEND_AVAILABLE = {integration.AI_AGENT_BACKEND_AVAILABLE}")

    if integration.AI_AGENT_BACKEND_AVAILABLE:
        print("✓ Backend integration is working correctly")
    else:
        print("✗ Backend integration failed")

except Exception as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()
