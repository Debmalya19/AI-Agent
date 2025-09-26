#!/usr/bin/env python3
"""
Debug script to check registered routes
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app

def debug_routes():
    """Debug registered routes"""
    print("Debugging Registered Routes")
    print("=" * 60)
    
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            for method in route.methods:
                if method != 'HEAD':  # Skip HEAD methods
                    routes.append(f"{method:8} {route.path}")
    
    # Sort routes for better readability
    routes.sort()
    
    print("All registered routes:")
    for route in routes:
        print(f"   {route}")
    
    print(f"\nTotal routes: {len(routes)}")
    
    # Check specific routes we're looking for
    target_routes = [
        "/api/auth/verify",
        "/api/admin/dashboard", 
        "/api/admin/integration/status"
    ]
    
    print(f"\nChecking target routes:")
    for target in target_routes:
        found = any(target in route for route in routes)
        status = "FOUND" if found else "MISSING"
        print(f"   {status}: {target}")
        
        if found:
            matching_routes = [route for route in routes if target in route]
            for match in matching_routes:
                print(f"      -> {match}")

if __name__ == "__main__":
    debug_routes()