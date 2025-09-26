#!/usr/bin/env python3
"""
Test script for comprehensive diagnostic tools and endpoints.
This script tests all the diagnostic functionality implemented for admin dashboard login troubleshooting.
"""

import asyncio
import aiohttp
import json
import sys
import time
from datetime import datetime

class DiagnosticToolsTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.results = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_endpoint(self, endpoint, method="GET", data=None, expected_status=200):
        """Test a single diagnostic endpoint"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            
            if method == "GET":
                async with self.session.get(url) as response:
                    response_data = await response.json()
                    status_code = response.status
            elif method == "POST":
                headers = {"Content-Type": "application/json"}
                async with self.session.post(url, json=data, headers=headers) as response:
                    response_data = await response.json()
                    status_code = response.status
            
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)  # Convert to milliseconds
            
            success = status_code == expected_status
            
            return {
                "success": success,
                "status_code": status_code,
                "response_time_ms": response_time,
                "response_data": response_data,
                "error": None if success else f"Expected {expected_status}, got {status_code}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "status_code": None,
                "response_time_ms": None,
                "response_data": None,
                "error": str(e)
            }
    
    async def test_system_status(self):
        """Test system status endpoint"""
        print("🔍 Testing system status endpoint...")
        
        result = await self.test_endpoint("/api/debug/status")
        self.results["system_status"] = result
        
        if result["success"]:
            data = result["response_data"]
            print(f"  ✅ System Status: {data.get('status', 'unknown')}")
            print(f"  📊 Database Connected: {data.get('database_connected', False)}")
            print(f"  👥 Admin Users: {data.get('admin_users_count', 0)}")
            print(f"  🔐 Recent Sessions: {data.get('recent_sessions', 0)}")
        else:
            print(f"  ❌ Failed: {result['error']}")
        
        return result["success"]
    
    async def test_login_functionality(self):
        """Test login testing endpoint"""
        print("🔐 Testing login functionality...")
        
        # Test with sample credentials
        test_data = {
            "email": "admin@example.com",
            "username": "admin",
            "password": "test_password"
        }
        
        result = await self.test_endpoint("/api/debug/test-login", method="POST", data=test_data)
        self.results["login_test"] = result
        
        if result["success"]:
            data = result["response_data"]
            print(f"  ✅ Login Test Response: {data.get('message', 'No message')}")
            if data.get('debug_info'):
                debug = data['debug_info']
                print(f"  🔍 User Lookup Attempts: {len(debug.get('lookup_attempts', []))}")
                print(f"  ✅ User Found: {bool(debug.get('user_found'))}")
        else:
            print(f"  ❌ Failed: {result['error']}")
        
        return result["success"]
    
    async def test_api_connectivity(self):
        """Test API connectivity endpoint"""
        print("🌐 Testing API connectivity...")
        
        result = await self.test_endpoint("/api/debug/connectivity")
        self.results["api_connectivity"] = result
        
        if result["success"]:
            data = result["response_data"]
            print(f"  ✅ Overall Status: {data.get('overall_status', 'unknown')}")
            
            if "connectivity_test_results" in data:
                results = data["connectivity_test_results"]
                successful = sum(1 for r in results if r.get("success", False))
                total = len(results)
                print(f"  📊 Connectivity Tests: {successful}/{total} passed")
        else:
            print(f"  ❌ Failed: {result['error']}")
        
        return result["success"]
    
    async def test_browser_compatibility(self):
        """Test browser compatibility endpoint"""
        print("🌍 Testing browser compatibility...")
        
        result = await self.test_endpoint("/api/debug/browser-compatibility")
        self.results["browser_compatibility"] = result
        
        if result["success"]:
            data = result["response_data"]
            print(f"  ✅ Browser Info Available: {bool(data.get('browser_info'))}")
            
            if "compatibility_results" in data:
                results = data["compatibility_results"]
                supported = sum(1 for r in results if r.get("supported", False))
                total = len(results)
                print(f"  📊 Compatibility Tests: {supported}/{total} supported")
        else:
            print(f"  ❌ Failed: {result['error']}")
        
        return result["success"]
    
    async def test_admin_users_list(self):
        """Test admin users listing endpoint"""
        print("👥 Testing admin users list...")
        
        result = await self.test_endpoint("/api/debug/admin-users")
        self.results["admin_users"] = result
        
        if result["success"]:
            data = result["response_data"]
            count = data.get("total_count", 0)
            print(f"  ✅ Admin Users Found: {count}")
            
            if count > 0 and "admin_users" in data:
                for user in data["admin_users"][:3]:  # Show first 3 users
                    print(f"    👤 {user.get('username', 'unknown')} ({user.get('email', 'no email')})")
        else:
            print(f"  ❌ Failed: {result['error']}")
        
        return result["success"]
    
    async def test_sessions_list(self):
        """Test sessions listing endpoint"""
        print("🔑 Testing sessions list...")
        
        result = await self.test_endpoint("/api/debug/sessions?hours=24")
        self.results["sessions"] = result
        
        if result["success"]:
            data = result["response_data"]
            count = data.get("total_count", 0)
            print(f"  ✅ Recent Sessions Found: {count}")
        else:
            print(f"  ❌ Failed: {result['error']}")
        
        return result["success"]
    
    async def test_error_logging(self):
        """Test error logging endpoint"""
        print("📝 Testing error logging...")
        
        test_error = {
            "category": "frontend",
            "severity": "medium",
            "message": "Test diagnostic error from automated test",
            "details": {
                "test_type": "automated_diagnostic_test",
                "timestamp": datetime.now().isoformat(),
                "test_runner": "diagnostic_tools_tester"
            }
        }
        
        result = await self.test_endpoint("/api/debug/log-error", method="POST", data=test_error)
        self.results["error_logging"] = result
        
        if result["success"]:
            data = result["response_data"]
            print(f"  ✅ Error Logged: {data.get('success', False)}")
            print(f"  📝 Message: {data.get('message', 'No message')}")
        else:
            print(f"  ❌ Failed: {result['error']}")
        
        return result["success"]
    
    async def test_error_simulation(self):
        """Test error simulation endpoint"""
        print("🧪 Testing error simulation...")
        
        result = await self.test_endpoint("/api/debug/simulate-error", method="POST", data={})
        self.results["error_simulation"] = result
        
        if result["success"]:
            data = result["response_data"]
            print(f"  ✅ Error Simulated: {data.get('success', False)}")
            if data.get('error_details'):
                details = data['error_details']
                print(f"  📊 Category: {details.get('category', 'unknown')}")
                print(f"  📊 Severity: {details.get('severity', 'unknown')}")
        else:
            print(f"  ❌ Failed: {result['error']}")
        
        return result["success"]
    
    async def test_recent_errors(self):
        """Test recent errors endpoint"""
        print("📊 Testing recent errors retrieval...")
        
        result = await self.test_endpoint("/api/debug/recent-errors?hours=24&limit=10")
        self.results["recent_errors"] = result
        
        if result["success"]:
            data = result["response_data"]
            count = data.get("total_count", 0)
            print(f"  ✅ Recent Errors Found: {count}")
        else:
            print(f"  ❌ Failed: {result['error']}")
        
        return result["success"]
    
    async def test_error_statistics(self):
        """Test error statistics endpoint"""
        print("📈 Testing error statistics...")
        
        result = await self.test_endpoint("/api/debug/error-statistics?hours=24")
        self.results["error_statistics"] = result
        
        if result["success"]:
            data = result["response_data"]
            total = data.get("total_errors", 0)
            print(f"  ✅ Total Errors (24h): {total}")
            
            if "category_breakdown" in data:
                categories = data["category_breakdown"]
                print(f"  📊 Categories: {len([k for k, v in categories.items() if v > 0])} active")
        else:
            print(f"  ❌ Failed: {result['error']}")
        
        return result["success"]
    
    async def test_health_check(self):
        """Test health check endpoint"""
        print("❤️ Testing health check...")
        
        result = await self.test_endpoint("/api/debug/health")
        self.results["health_check"] = result
        
        if result["success"]:
            data = result["response_data"]
            print(f"  ✅ Service Status: {data.get('status', 'unknown')}")
            print(f"  🔧 Service: {data.get('service', 'unknown')}")
            print(f"  📦 Version: {data.get('version', 'unknown')}")
        else:
            print(f"  ❌ Failed: {result['error']}")
        
        return result["success"]
    
    async def run_all_tests(self):
        """Run all diagnostic tests"""
        print("🚀 Starting comprehensive diagnostic tools test suite...")
        print(f"🎯 Target URL: {self.base_url}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Define all tests
        tests = [
            ("Health Check", self.test_health_check),
            ("System Status", self.test_system_status),
            ("Admin Users List", self.test_admin_users_list),
            ("Sessions List", self.test_sessions_list),
            ("Login Functionality", self.test_login_functionality),
            ("API Connectivity", self.test_api_connectivity),
            ("Browser Compatibility", self.test_browser_compatibility),
            ("Error Logging", self.test_error_logging),
            ("Error Simulation", self.test_error_simulation),
            ("Recent Errors", self.test_recent_errors),
            ("Error Statistics", self.test_error_statistics),
        ]
        
        # Run tests
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                success = await test_func()
                if success:
                    passed += 1
                print()  # Add spacing between tests
            except Exception as e:
                print(f"  ❌ Test '{test_name}' crashed: {e}")
                print()
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        # Print summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {passed}/{total} tests")
        print(f"⏱️ Duration: {duration} seconds")
        print(f"📈 Success Rate: {round((passed/total)*100, 1)}%")
        
        if passed == total:
            print("🎉 All diagnostic tools are working correctly!")
            return True
        else:
            print("⚠️ Some diagnostic tools need attention.")
            return False
    
    def save_results(self, filename="diagnostic_test_results.json"):
        """Save test results to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "base_url": self.base_url,
                    "results": self.results
                }, f, indent=2)
            print(f"📄 Results saved to {filename}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")

async def main():
    """Main test runner"""
    base_url = "http://localhost:8000"
    
    # Check if custom URL provided
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print("🔧 Diagnostic Tools Test Suite")
    print("=" * 60)
    
    async with DiagnosticToolsTester(base_url) as tester:
        success = await tester.run_all_tests()
        tester.save_results()
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())