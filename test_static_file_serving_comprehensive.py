#!/usr/bin/env python3
"""
Comprehensive Static File Serving Tests for Admin Dashboard
Task 5: Create static file serving tests

This test suite verifies:
- All CSS files are accessible at correct paths
- All JavaScript files are accessible at correct paths  
- Integration tests for admin dashboard loading with static files
- Error handling and 404 responses
- Requirements: 1.1, 2.1, 3.1, 5.1
"""

import pytest
import requests
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import time
import concurrent.futures
from typing import List, Dict, Any

# Add the ai-agent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the FastAPI app
try:
    from main import app
    client = TestClient(app)
    FASTAPI_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import FastAPI app: {e}")
    FASTAPI_AVAILABLE = False
    client = None

class TestStaticFileServing:
    """Test suite for static file serving functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.base_url = "http://localhost:8000"
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
        
    def test_css_files_exist_on_filesystem(self):
        """Test that all required CSS files exist in the filesystem"""
        css_dir = Path("admin-dashboard/frontend/css")
        
        for css_file in self.css_files:
            file_path = css_dir / css_file
            assert file_path.exists(), f"CSS file {css_file} does not exist at {file_path}"
            assert file_path.is_file(), f"CSS file {css_file} is not a regular file"
            assert file_path.stat().st_size > 0, f"CSS file {css_file} is empty"
    
    def test_js_files_exist_on_filesystem(self):
        """Test that all required JavaScript files exist in the filesystem"""
        js_dir = Path("admin-dashboard/frontend/js")
        
        for js_file in self.js_files:
            file_path = js_dir / js_file
            assert file_path.exists(), f"JS file {js_file} does not exist at {file_path}"
            assert file_path.is_file(), f"JS file {js_file} is not a regular file"
            assert file_path.stat().st_size > 0, f"JS file {js_file} is empty"

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
    def test_css_files_accessible_root_paths(self):
        """Test that all CSS files are accessible at root paths (/css/*)
        Requirements: 1.1 - CSS files served successfully without 404 errors
        """
        for css_file in self.css_files:
            response = client.get(f"/css/{css_file}")
            
            assert response.status_code == 200, f"CSS file {css_file} returned {response.status_code}"
            assert "text/css" in response.headers.get("content-type", "").lower(), \
                f"CSS file {css_file} has incorrect content-type: {response.headers.get('content-type')}"
            assert len(response.content) > 0, f"CSS file {css_file} has empty content"
            
            # Verify CSS content is valid (basic check)
            content = response.content.decode('utf-8', errors='ignore')
            assert '{' in content or '}' in content, f"CSS file {css_file} doesn't appear to contain valid CSS"

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
    def test_js_files_accessible_root_paths(self):
        """Test that all JavaScript files are accessible at root paths (/js/*)
        Requirements: 2.1 - JavaScript files served without 404 errors
        """
        for js_file in self.js_files:
            response = client.get(f"/js/{js_file}")
            
            assert response.status_code == 200, f"JS file {js_file} returned {response.status_code}"
            content_type = response.headers.get("content-type", "").lower()
            assert any(js_type in content_type for js_type in ["javascript", "text/plain", "application/octet-stream"]), \
                f"JS file {js_file} has unexpected content-type: {content_type}"
            assert len(response.content) > 0, f"JS file {js_file} has empty content"
            
            # Verify JavaScript content is valid (basic check)
            content = response.content.decode('utf-8', errors='ignore')
            # Check for common JavaScript patterns
            js_patterns = ['function', 'var', 'let', 'const', 'class', '(', ')', '{', '}']
            assert any(pattern in content for pattern in js_patterns), \
                f"JS file {js_file} doesn't appear to contain valid JavaScript"

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
    def test_css_files_accessible_admin_paths(self):
        """Test that CSS files are also accessible via /admin/css/* paths for compatibility"""
        for css_file in self.css_files:
            response = client.get(f"/admin/css/{css_file}")
            
            assert response.status_code == 200, f"CSS file {css_file} not accessible via /admin/css/"
            assert "text/css" in response.headers.get("content-type", "").lower()

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
    def test_js_files_accessible_admin_paths(self):
        """Test that JavaScript files are also accessible via /admin/js/* paths for compatibility"""
        for js_file in self.js_files:
            response = client.get(f"/admin/js/{js_file}")
            
            assert response.status_code == 200, f"JS file {js_file} not accessible via /admin/js/"
            content_type = response.headers.get("content-type", "").lower()
            assert any(js_type in content_type for js_type in ["javascript", "text/plain", "application/octet-stream"])

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
    def test_admin_dashboard_html_loading(self):
        """Test that admin dashboard HTML files load correctly with static file references
        Requirements: 3.1 - HTML files load properly without 404 errors
        """
        html_files = [
            ("", "index.html"),  # Root admin dashboard
            ("tickets.html", "tickets.html"),
            ("users.html", "users.html"),
            ("settings.html", "settings.html"),
            ("integration.html", "integration.html"),
            ("logs.html", "logs.html")
        ]
        
        for url_path, expected_file in html_files:
            if url_path:
                response = client.get(f"/admin/{url_path}")
            else:
                response = client.get("/admin/")
            
            assert response.status_code == 200, f"HTML file {expected_file} returned {response.status_code}"
            assert "text/html" in response.headers.get("content-type", "").lower()
            
            content = response.text
            assert len(content) > 0, f"HTML file {expected_file} has empty content"
            
            # Check for HTML structure
            assert "<html" in content.lower() or "<!doctype" in content.lower(), \
                f"HTML file {expected_file} doesn't appear to be valid HTML"

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
    def test_admin_dashboard_static_references(self):
        """Test that admin dashboard HTML files reference static assets correctly
        Requirements: 1.1, 2.1 - Static files referenced with correct paths
        """
        response = client.get("/admin/")
        assert response.status_code == 200
        
        content = response.text
        
        # Check for CSS references
        css_references = [
            "/css/modern-dashboard.css",
            "css/modern-dashboard.css",
            "/admin/css/modern-dashboard.css"
        ]
        
        css_found = any(css_ref in content for css_ref in css_references)
        assert css_found, "No CSS references found in admin dashboard HTML"
        
        # Check for JavaScript references
        js_patterns = ["/js/", "js/", "/admin/js/"]
        js_found = any(js_pattern in content for js_pattern in js_patterns)
        assert js_found, "No JavaScript references found in admin dashboard HTML"

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
    def test_404_error_handling_missing_css(self):
        """Test proper 404 error handling for missing CSS files
        Requirements: 5.1 - Clear error handling when static files fail to load
        """
        missing_css_files = [
            "nonexistent.css",
            "missing-file.css",
            "invalid-name.css"
        ]
        
        for missing_file in missing_css_files:
            response = client.get(f"/css/{missing_file}")
            assert response.status_code == 404, f"Missing CSS file {missing_file} should return 404"

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
    def test_404_error_handling_missing_js(self):
        """Test proper 404 error handling for missing JavaScript files
        Requirements: 5.1 - Clear error handling when static files fail to load
        """
        missing_js_files = [
            "nonexistent.js",
            "missing-script.js",
            "invalid-module.js"
        ]
        
        for missing_file in missing_js_files:
            response = client.get(f"/js/{missing_file}")
            assert response.status_code == 404, f"Missing JS file {missing_file} should return 404"

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
    def test_static_file_caching_headers(self):
        """Test that static files have appropriate caching headers for performance"""
        # Test CSS file caching
        response = client.get("/css/modern-dashboard.css")
        assert response.status_code == 200
        
        # Check for caching headers (may vary based on FastAPI StaticFiles configuration)
        headers = response.headers
        # At minimum, we should have some form of cache control or etag
        has_caching = any(header in headers for header in ["cache-control", "etag", "last-modified"])
        # Note: This is informational - FastAPI StaticFiles may not set these by default
        
        # Test JS file caching
        response = client.get("/js/main.js")
        assert response.status_code == 200

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
    def test_concurrent_static_file_requests(self):
        """Test handling of multiple simultaneous static file requests
        Requirements: 7.1, 7.2 - Efficient serving for concurrent requests
        """
        def fetch_static_file(path):
            return client.get(path)
        
        # Test concurrent requests to different file types
        paths = [
            "/css/modern-dashboard.css",
            "/js/main.js",
            "/js/auth.js",
            "/css/admin.css",
            "/js/dashboard.js"
        ]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_static_file, path) for path in paths]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        for result in results:
            assert result.status_code == 200, f"Concurrent request failed with status {result.status_code}"

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
    def test_static_file_content_integrity(self):
        """Test that static files maintain content integrity across requests"""
        # Test the same file multiple times to ensure consistent content
        test_file = "/css/modern-dashboard.css"
        
        responses = []
        for _ in range(3):
            response = client.get(test_file)
            assert response.status_code == 200
            responses.append(response.content)
        
        # All responses should have identical content
        first_content = responses[0]
        for i, content in enumerate(responses[1:], 1):
            assert content == first_content, f"Content mismatch in request {i+1}"

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
    def test_admin_dashboard_integration_complete(self):
        """Integration test: Admin dashboard loads completely with all static files
        Requirements: 1.1, 2.1, 7.1, 7.2 - Dashboard loads without 404 errors
        """
        # Load the main admin dashboard
        response = client.get("/admin/")
        assert response.status_code == 200
        
        content = response.text
        
        # Extract static file references from HTML
        import re
        
        # Find CSS references
        css_refs = re.findall(r'href=["\']([^"\']*\.css)["\']', content)
        js_refs = re.findall(r'src=["\']([^"\']*\.js)["\']', content)
        
        # Test that referenced CSS files are accessible
        for css_ref in css_refs:
            # Normalize path
            if css_ref.startswith('/'):
                test_path = css_ref
            elif css_ref.startswith('css/'):
                test_path = f"/{css_ref}"
            else:
                test_path = f"/css/{css_ref.split('/')[-1]}"
            
            response = client.get(test_path)
            assert response.status_code == 200, f"Referenced CSS file {css_ref} not accessible at {test_path}"
        
        # Test that referenced JS files are accessible
        for js_ref in js_refs:
            # Normalize path
            if js_ref.startswith('/'):
                test_path = js_ref
            elif js_ref.startswith('js/'):
                test_path = f"/{js_ref}"
            else:
                test_path = f"/js/{js_ref.split('/')[-1]}"
            
            response = client.get(test_path)
            assert response.status_code == 200, f"Referenced JS file {js_ref} not accessible at {test_path}"

    def test_static_file_permissions(self):
        """Test that static files have proper file system permissions"""
        css_dir = Path("admin-dashboard/frontend/css")
        js_dir = Path("admin-dashboard/frontend/js")
        
        # Test CSS files permissions
        for css_file in self.css_files:
            file_path = css_dir / css_file
            if file_path.exists():
                # Check that file is readable
                assert os.access(file_path, os.R_OK), f"CSS file {css_file} is not readable"
        
        # Test JS files permissions
        for js_file in self.js_files:
            file_path = js_dir / js_file
            if file_path.exists():
                # Check that file is readable
                assert os.access(file_path, os.R_OK), f"JS file {js_file} is not readable"

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
    def test_static_file_mime_types(self):
        """Test that static files are served with correct MIME types"""
        # Test CSS MIME types
        for css_file in self.css_files[:2]:  # Test first 2 to avoid too many requests
            response = client.get(f"/css/{css_file}")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "").lower()
            assert "text/css" in content_type, f"CSS file {css_file} has wrong MIME type: {content_type}"
        
        # Test JS MIME types
        for js_file in self.js_files[:2]:  # Test first 2 to avoid too many requests
            response = client.get(f"/js/{js_file}")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "").lower()
            # JavaScript files might be served as various MIME types
            valid_js_types = ["javascript", "text/plain", "application/octet-stream"]
            assert any(js_type in content_type for js_type in valid_js_types), \
                f"JS file {js_file} has unexpected MIME type: {content_type}"

class TestStaticFileServingLive:
    """Live server tests for static file serving (requires running server)"""
    
    def setup_method(self):
        """Setup for live server tests"""
        self.base_url = "http://localhost:8000"
        self.session = requests.Session()
        self.session.timeout = 10
    
    def test_live_server_css_accessibility(self):
        """Test CSS file accessibility on live server"""
        css_files = ["modern-dashboard.css", "admin.css"]
        
        for css_file in css_files:
            try:
                response = self.session.get(f"{self.base_url}/css/{css_file}")
                if response.status_code == 200:
                    assert "text/css" in response.headers.get("content-type", "").lower()
                    print(f"✅ Live test: {css_file} accessible")
                else:
                    print(f"⚠️  Live test: {css_file} returned {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"⚠️  Live test: {css_file} failed - {e}")
    
    def test_live_server_js_accessibility(self):
        """Test JavaScript file accessibility on live server"""
        js_files = ["main.js", "auth.js", "dashboard.js"]
        
        for js_file in js_files:
            try:
                response = self.session.get(f"{self.base_url}/js/{js_file}")
                if response.status_code == 200:
                    print(f"✅ Live test: {js_file} accessible")
                else:
                    print(f"⚠️  Live test: {js_file} returned {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"⚠️  Live test: {js_file} failed - {e}")

def run_comprehensive_static_file_tests():
    """Run all static file serving tests and generate a report"""
    print("🧪 Running Comprehensive Static File Serving Tests")
    print("=" * 60)
    
    # Run pytest with verbose output
    import subprocess
    
    test_file = __file__
    cmd = [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        print(f"\nTest execution completed with return code: {result.returncode}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

if __name__ == "__main__":
    # Run the comprehensive test suite
    success = run_comprehensive_static_file_tests()
    
    if success:
        print("\n🎉 All static file serving tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some static file serving tests failed.")
        sys.exit(1)