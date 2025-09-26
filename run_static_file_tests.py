#!/usr/bin/env python3
"""
Static File Serving Test Runner
Simple test runner for validating static file serving functionality
Part of Task 5: Create static file serving tests
"""

import requests
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class StaticFileTestRunner:
    """Test runner for static file serving validation"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 10
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "base_url": base_url,
            "tests": {},
            "summary": {}
        }
        
        # Define test files based on actual filesystem
        self.css_files = [
            "modern-dashboard.css",
            "admin.css", 
            "styles.css",
            "support.css"
        ]
        
        self.js_files = [
            "session-manager.js",
            "auth-error-handler.js",
            "api-connectivity-checker.js",
            "admin-auth-service.js",
            "unified_api.js",
            "api.js",
            "navigation.js",
            "ui-feedback.js",
            "auth.js",
            "dashboard.js",
            "integration.js",
            "main.js",
            "simple-auth-fix.js",
            "admin_register.js",
            "logs.js",
            "settings.js",
            "support-dashboard.js",
            "tickets.js",
            "users_addon.js",
            "users.js"
        ]
        
        self.html_files = [
            ("", "Admin Dashboard Root"),
            ("tickets.html", "Support Tickets"),
            ("users.html", "User Management"),
            ("settings.html", "Settings"),
            ("integration.html", "Integration"),
            ("logs.html", "Logs")
        ]
    
    def test_file_existence(self) -> Dict[str, Any]:
        """Test that static files exist on the filesystem"""
        print("\n📁 Testing File System Existence")
        print("-" * 40)
        
        results = {"css": {}, "js": {}, "passed": 0, "failed": 0}
        
        # Test CSS files
        css_dir = Path("admin-dashboard/frontend/css")
        for css_file in self.css_files:
            file_path = css_dir / css_file
            exists = file_path.exists()
            size = file_path.stat().st_size if exists else 0
            
            results["css"][css_file] = {
                "exists": exists,
                "size": size,
                "path": str(file_path)
            }
            
            status = "✅" if exists and size > 0 else "❌"
            print(f"  {status} CSS: {css_file} ({size} bytes)")
            
            if exists and size > 0:
                results["passed"] += 1
            else:
                results["failed"] += 1
        
        # Test JS files
        js_dir = Path("admin-dashboard/frontend/js")
        for js_file in self.js_files:
            file_path = js_dir / js_file
            exists = file_path.exists()
            size = file_path.stat().st_size if exists else 0
            
            results["js"][js_file] = {
                "exists": exists,
                "size": size,
                "path": str(file_path)
            }
            
            status = "✅" if exists and size > 0 else "❌"
            print(f"  {status} JS:  {js_file} ({size} bytes)")
            
            if exists and size > 0:
                results["passed"] += 1
            else:
                results["failed"] += 1
        
        return results
    
    def test_css_accessibility(self) -> Dict[str, Any]:
        """Test CSS file accessibility via HTTP"""
        print("\n🎨 Testing CSS File Accessibility")
        print("-" * 40)
        
        results = {"root_path": {}, "admin_path": {}, "passed": 0, "failed": 0}
        
        for css_file in self.css_files:
            # Test root path (/css/*)
            root_url = f"{self.base_url}/css/{css_file}"
            try:
                response = self.session.get(root_url)
                root_success = response.status_code == 200
                root_content_type = response.headers.get("content-type", "")
                root_size = len(response.content)
                
                results["root_path"][css_file] = {
                    "status_code": response.status_code,
                    "content_type": root_content_type,
                    "size": root_size,
                    "success": root_success
                }
                
            except Exception as e:
                root_success = False
                results["root_path"][css_file] = {
                    "error": str(e),
                    "success": False
                }
            
            # Test admin path (/admin/css/*)
            admin_url = f"{self.base_url}/admin/css/{css_file}"
            try:
                response = self.session.get(admin_url)
                admin_success = response.status_code == 200
                admin_content_type = response.headers.get("content-type", "")
                admin_size = len(response.content)
                
                results["admin_path"][css_file] = {
                    "status_code": response.status_code,
                    "content_type": admin_content_type,
                    "size": admin_size,
                    "success": admin_success
                }
                
            except Exception as e:
                admin_success = False
                results["admin_path"][css_file] = {
                    "error": str(e),
                    "success": False
                }
            
            # Display results
            root_status = "✅" if root_success else "❌"
            admin_status = "✅" if admin_success else "❌"
            print(f"  {root_status} /css/{css_file}")
            print(f"  {admin_status} /admin/css/{css_file}")
            
            if root_success:
                results["passed"] += 1
            else:
                results["failed"] += 1
                
            if admin_success:
                results["passed"] += 1
            else:
                results["failed"] += 1
        
        return results
    
    def test_js_accessibility(self) -> Dict[str, Any]:
        """Test JavaScript file accessibility via HTTP"""
        print("\n📜 Testing JavaScript File Accessibility")
        print("-" * 40)
        
        results = {"root_path": {}, "admin_path": {}, "passed": 0, "failed": 0}
        
        for js_file in self.js_files:
            # Test root path (/js/*)
            root_url = f"{self.base_url}/js/{js_file}"
            try:
                response = self.session.get(root_url)
                root_success = response.status_code == 200
                root_content_type = response.headers.get("content-type", "")
                root_size = len(response.content)
                
                results["root_path"][js_file] = {
                    "status_code": response.status_code,
                    "content_type": root_content_type,
                    "size": root_size,
                    "success": root_success
                }
                
            except Exception as e:
                root_success = False
                results["root_path"][js_file] = {
                    "error": str(e),
                    "success": False
                }
            
            # Test admin path (/admin/js/*)
            admin_url = f"{self.base_url}/admin/js/{js_file}"
            try:
                response = self.session.get(admin_url)
                admin_success = response.status_code == 200
                admin_content_type = response.headers.get("content-type", "")
                admin_size = len(response.content)
                
                results["admin_path"][js_file] = {
                    "status_code": response.status_code,
                    "content_type": admin_content_type,
                    "size": admin_size,
                    "success": admin_success
                }
                
            except Exception as e:
                admin_success = False
                results["admin_path"][js_file] = {
                    "error": str(e),
                    "success": False
                }
            
            # Display results
            root_status = "✅" if root_success else "❌"
            admin_status = "✅" if admin_success else "❌"
            print(f"  {root_status} /js/{js_file}")
            print(f"  {admin_status} /admin/js/{js_file}")
            
            if root_success:
                results["passed"] += 1
            else:
                results["failed"] += 1
                
            if admin_success:
                results["passed"] += 1
            else:
                results["failed"] += 1
        
        return results
    
    def test_html_integration(self) -> Dict[str, Any]:
        """Test HTML file loading and static file integration"""
        print("\n📄 Testing HTML Integration")
        print("-" * 40)
        
        results = {"html_files": {}, "passed": 0, "failed": 0}
        
        for url_path, description in self.html_files:
            if url_path:
                test_url = f"{self.base_url}/admin/{url_path}"
            else:
                test_url = f"{self.base_url}/admin/"
            
            try:
                response = self.session.get(test_url)
                success = response.status_code == 200
                content_type = response.headers.get("content-type", "")
                content = response.text if success else ""
                
                # Check for static file references
                has_css_refs = "/css/" in content or "css/" in content
                has_js_refs = "/js/" in content or "js/" in content
                
                results["html_files"][url_path or "root"] = {
                    "status_code": response.status_code,
                    "content_type": content_type,
                    "success": success,
                    "has_css_refs": has_css_refs,
                    "has_js_refs": has_js_refs,
                    "content_length": len(content)
                }
                
                status = "✅" if success else "❌"
                css_status = "📄" if has_css_refs else "⚠️"
                js_status = "📜" if has_js_refs else "⚠️"
                
                print(f"  {status} {description}")
                print(f"    {css_status} CSS refs: {has_css_refs}")
                print(f"    {js_status} JS refs: {has_js_refs}")
                
                if success:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                results["html_files"][url_path or "root"] = {
                    "error": str(e),
                    "success": False
                }
                print(f"  ❌ {description} - Error: {e}")
                results["failed"] += 1
        
        return results
    
    def test_error_handling(self) -> Dict[str, Any]:
        """Test 404 error handling for missing files"""
        print("\n🚫 Testing 404 Error Handling")
        print("-" * 40)
        
        results = {"missing_files": {}, "passed": 0, "failed": 0}
        
        missing_files = [
            ("/css/nonexistent.css", "Missing CSS"),
            ("/js/nonexistent.js", "Missing JS"),
            ("/css/invalid-file.css", "Invalid CSS"),
            ("/js/invalid-script.js", "Invalid JS")
        ]
        
        for url_path, description in missing_files:
            test_url = f"{self.base_url}{url_path}"
            
            try:
                response = self.session.get(test_url)
                is_404 = response.status_code == 404
                
                results["missing_files"][url_path] = {
                    "status_code": response.status_code,
                    "is_404": is_404,
                    "success": is_404  # Success means proper 404 handling
                }
                
                status = "✅" if is_404 else "❌"
                print(f"  {status} {description}: {response.status_code}")
                
                if is_404:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                results["missing_files"][url_path] = {
                    "error": str(e),
                    "success": False
                }
                print(f"  ❌ {description} - Error: {e}")
                results["failed"] += 1
        
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all static file serving tests"""
        print("*** Static File Serving Test Suite ***")
        print("=" * 50)
        print(f"Testing server at: {self.base_url}")
        print(f"Timestamp: {self.results['timestamp']}")
        
        # Run all test categories
        self.results["tests"]["file_existence"] = self.test_file_existence()
        self.results["tests"]["css_accessibility"] = self.test_css_accessibility()
        self.results["tests"]["js_accessibility"] = self.test_js_accessibility()
        self.results["tests"]["html_integration"] = self.test_html_integration()
        self.results["tests"]["error_handling"] = self.test_error_handling()
        
        # Calculate summary
        total_passed = sum(test.get("passed", 0) for test in self.results["tests"].values())
        total_failed = sum(test.get("failed", 0) for test in self.results["tests"].values())
        total_tests = total_passed + total_failed
        
        self.results["summary"] = {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "success_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0
        }
        
        # Display summary
        print(f"\n📊 Test Summary")
        print("=" * 30)
        print(f"Total tests: {total_tests}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failed}")
        print(f"Success rate: {self.results['summary']['success_rate']:.1f}%")
        
        if total_failed == 0:
            print("\n🎉 All static file serving tests passed!")
        else:
            print(f"\n⚠️  {total_failed} tests failed. Check server configuration.")
        
        return self.results
    
    def save_results(self, filename: str = None):
        """Save test results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"static_file_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")

def main():
    """Main test runner function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Static File Serving Test Runner")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="Base URL for testing (default: http://localhost:8000)")
    parser.add_argument("--save", action="store_true", 
                       help="Save results to JSON file")
    parser.add_argument("--output", help="Output filename for results")
    
    args = parser.parse_args()
    
    # Create and run test suite
    runner = StaticFileTestRunner(args.url)
    results = runner.run_all_tests()
    
    # Save results if requested
    if args.save:
        runner.save_results(args.output)
    
    # Exit with appropriate code
    if results["summary"]["failed"] == 0:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()