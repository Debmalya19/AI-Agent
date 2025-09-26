#!/usr/bin/env python3
"""
Test script to verify admin-dashboard backend integration from admin-dashboard directory
"""
import sys
import os

print(f"Current working directory: {os.getcwd()}")
print(f"Initial sys.path: {sys.path}")

# Add ai-agent backend path FIRST
ai_agent_backend = os.path.abspath(os.path.join('.', 'backend'))
print(f"AI Agent backend path: {ai_agent_backend}")
if ai_agent_backend not in sys.path:
    sys.path.insert(0, ai_agent_backend)
    print(f"Added ai-agent backend to sys.path: {ai_agent_backend}")

# Add parent directory to path to access backend
sys.path.insert(0, '..')
print(f"Updated sys.path: {sys.path}")

print("Testing backend integration from admin-dashboard directory...")

try:
    # Test backend import
    from backend import database
    print("✓ backend.database import successful")

    from backend import models
    print("✓ backend.models import successful")

    # Test integration module
    from backend.integration import AI_AGENT_BACKEND_AVAILABLE
    print(f"✓ Integration import successful: AI_AGENT_BACKEND_AVAILABLE = {AI_AGENT_BACKEND_AVAILABLE}")

    if AI_AGENT_BACKEND_AVAILABLE:
        print("✓ Backend integration is working correctly")
    else:
        print("✗ Backend integration failed")

except Exception as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()
