#!/usr/bin/env python3
"""
Test script for logs page functionality
Tests the logs page UI and backend integration
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

class LogsPageTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        
    async def setup(self):
        """Setup test session and authentication"""
        self.session = aiohttp.ClientSession()
        
        # Login as admin
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        try:
            async with self.session.post(f"{BASE_URL}/api/auth/login", json=login_data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.auth_token = result.get("access_token")
                    print("✓ Admin authentication successful")
                else:
                    print(f"✗ Admin authentication failed: {response.status}")
                    return False
        except Exception as e:
            print(f"✗ Authentication error: {e}")
            return False
            
        return True
    
    async def test_logs_endpoint(self):
        """Test the logs API endpoint"""
        print("\n=== Testing Logs API Endpoint ===")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test basic logs retrieval
            async with self.session.get(f"{BASE_URL}/api/admin/logs", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    logs = result.get("logs", [])
                    print(f"✓ Retrieved {len(logs)} log entries")
                    
                    # Verify log structure
                    if logs:
                        log = logs[0]
                        required_fields = ['id', 'timestamp', 'level', 'category', 'message']
                        missing_fields = [field for field in required_fields if field not in log]
                        
                        if not missing_fields:
                            print("✓ Log entry structure is correct")
                        else:
                            print(f"✗ Missing fields in log entry: {missing_fields}")
                    
                else:
                    print(f"✗ Logs endpoint failed: {response.status}")
                    
        except Exception as e:
            print(f"✗ Logs endpoint error: {e}")
    
    async def test_logs_filtering(self):
        """Test logs filtering functionality"""
        print("\n=== Testing Logs Filtering ===")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test level filtering
        try:
            async with self.session.get(f"{BASE_URL}/api/admin/logs?level=error", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    logs = result.get("logs", [])
                    
                    # Verify all logs are error level
                    error_logs = [log for log in logs if log.get("level") == "error"]
                    if len(error_logs) == len(logs):
                        print("✓ Level filtering works correctly")
                    else:
                        print(f"✗ Level filtering failed: {len(error_logs)}/{len(logs)} are error level")
                else:
                    print(f"✗ Level filtering failed: {response.status}")
                    
        except Exception as e:
            print(f"✗ Level filtering error: {e}")
        
        # Test category filtering
        try:
            async with self.session.get(f"{BASE_URL}/api/admin/logs?category=auth", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    logs = result.get("logs", [])
                    
                    # Verify all logs are auth category
                    auth_logs = [log for log in logs if log.get("category") == "auth"]
                    if len(auth_logs) == len(logs):
                        print("✓ Category filtering works correctly")
                    else:
                        print(f"✗ Category filtering failed: {len(auth_logs)}/{len(logs)} are auth category")
                else:
                    print(f"✗ Category filtering failed: {response.status}")
                    
        except Exception as e:
            print(f"✗ Category filtering error: {e}")
    
    async def test_logs_pagination(self):
        """Test logs pagination"""
        print("\n=== Testing Logs Pagination ===")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test with limit
            async with self.session.get(f"{BASE_URL}/api/admin/logs?limit=10", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    logs = result.get("logs", [])
                    
                    if len(logs) <= 10:
                        print("✓ Pagination limit works correctly")
                    else:
                        print(f"✗ Pagination limit failed: got {len(logs)} logs, expected ≤10")
                else:
                    print(f"✗ Pagination test failed: {response.status}")
                    
        except Exception as e:
            print(f"✗ Pagination error: {e}")
    
    async def test_new_logs_endpoint(self):
        """Test new logs endpoint for real-time updates"""
        print("\n=== Testing New Logs Endpoint ===")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Use current timestamp
            since_timestamp = datetime.utcnow().isoformat()
            
            async with self.session.get(f"{BASE_URL}/api/admin/logs/new?since={since_timestamp}", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    new_logs = result.get("logs", [])
                    print(f"✓ New logs endpoint works: {len(new_logs)} new entries")
                else:
                    print(f"✗ New logs endpoint failed: {response.status}")
                    
        except Exception as e:
            print(f"✗ New logs endpoint error: {e}")
    
    async def test_clear_logs_endpoint(self):
        """Test clear logs endpoint"""
        print("\n=== Testing Clear Logs Endpoint ===")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            async with self.session.delete(f"{BASE_URL}/api/admin/logs", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        print("✓ Clear logs endpoint works correctly")
                    else:
                        print("✗ Clear logs endpoint returned success=false")
                else:
                    print(f"✗ Clear logs endpoint failed: {response.status}")
                    
        except Exception as e:
            print(f"✗ Clear logs endpoint error: {e}")
    
    async def test_logs_page_access(self):
        """Test logs page accessibility"""
        print("\n=== Testing Logs Page Access ===")
        
        try:
            async with self.session.get(f"{BASE_URL}/admin/logs.html") as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Check for key elements
                    required_elements = [
                        'System Logs',
                        'log-viewer',
                        'log-level-filter',
                        'category-filter',
                        'real-time-status'
                    ]
                    
                    missing_elements = [elem for elem in required_elements if elem not in content]
                    
                    if not missing_elements:
                        print("✓ Logs page loads correctly with all required elements")
                    else:
                        print(f"✗ Logs page missing elements: {missing_elements}")
                        
                else:
                    print(f"✗ Logs page access failed: {response.status}")
                    
        except Exception as e:
            print(f"✗ Logs page access error: {e}")
    
    async def run_all_tests(self):
        """Run all tests"""
        print("Starting Logs Page Functionality Tests...")
        print("=" * 50)
        
        # Setup
        if not await self.setup():
            print("Failed to setup tests")
            return
        
        # Run tests
        await self.test_logs_page_access()
        await self.test_logs_endpoint()
        await self.test_logs_filtering()
        await self.test_logs_pagination()
        await self.test_new_logs_endpoint()
        await self.test_clear_logs_endpoint()
        
        print("\n" + "=" * 50)
        print("Logs Page Tests Completed!")
    
    async def cleanup(self):
        """Cleanup test session"""
        if self.session:
            await self.session.close()

async def main():
    """Main test function"""
    tester = LogsPageTester()
    
    try:
        await tester.run_all_tests()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())