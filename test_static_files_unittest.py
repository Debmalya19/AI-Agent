#!/usr/bin/env python3
"""
Static File Serving Tests using unittest
Task 5: Create static file serving tests

This test suite uses Python's built-in unittest framework and provides
comprehensive testing for static file serving functionality.

Requirements covered:
- 1.1: CSS files served successfully without 404 errors
- 2.1: JavaScript files served without 404 errors  
- 3.1: HTML files load properly without 404 errors
- 5.1: Clear error handling when static files fail to load
"""

import unittest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestStaticFileExistence(unittest.TestCase):
    """Test that static files exist on the filesystem"""
    
    def setUp(self):
        """Set up test fixtures"""
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
        self.css_dir = Path("admin-dashboard/frontend/css")
        self.js_dir = Path("admin-dashboard/frontend/js")
    
    def test_css_directory_exists(self):
        """Test that CSS directory exists"""
        self.assertTrue(self.css_dir.exists(), f"CSS directory {self.css_dir} does not exist")
        self.assertTrue(self.css_dir.is_dir(), f"CSS path {self.css_dir} is not a directory")
    
    def test_js_directory_exists(self):
        """Test that JS directory exists"""
        self.assertTrue(self.js_dir.exists(), f"JS directory {self.js_dir} does not exist")
        self.assertTrue(self.js_dir.is_dir(), f"JS path {self.js_dir} is not a directory")
    
    def test_css_files_exist(self):
        """Test that all required CSS files exist and are not empty"""
        for css_file in self.css_files:
            with self.subTest(css_file=css_file):
                file_path = self.css_dir / css_file
                self.assertTrue(file_path.exists(), f"CSS file {css_file} does not exist at {file_path}")
                self.assertTrue(file_path.is_file(), f"CSS file {css_file} is not a regular file")
                self.assertGreater(file_path.stat().st_size, 0, f"CSS file {css_file} is empty")
    
    def test_js_files_exist(self):
        """Test that all required JavaScript files exist and are not empty"""
        for js_file in self.js_files:
            with self.subTest(js_file=js_file):
                file_path = self.js_dir / js_file
                self.assertTrue(file_path.exists(), f"JS file {js_file} does not exist at {file_path}")
                self.assertTrue(file_path.is_file(), f"JS file {js_file} is not a regular file")
                self.assertGreater(file_path.stat().st_size, 0, f"JS file {js_file} is empty")
    
    def test_css_file_permissions(self):
        """Test that CSS files have proper read permissions"""
        for css_file in self.css_files:
            with self.subTest(css_file=css_file):
                file_path = self.css_dir / css_file
                if file_path.exists():
                    self.assertTrue(os.access(file_path, os.R_OK), f"CSS file {css_file} is not readable")
    
    def test_js_file_permissions(self):
        """Test that JavaScript files have proper read permissions"""
        for js_file in self.js_files:
            with self.subTest(js_file=js_file):
                file_path = self.js_dir / js_file
                if file_path.exists():
                    self.assertTrue(os.access(file_path, os.R_OK), f"JS file {js_file} is not readable")

class TestStaticFileContent(unittest.TestCase):
    """Test static file content validity"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.css_dir = Path("admin-dashboard/frontend/css")
        self.js_dir = Path("admin-dashboard/frontend/js")
    
    def test_css_content_validity(self):
        """Test that CSS files contain valid CSS content"""
        css_files = ["modern-dashboard.css", "admin.css"]  # Test subset for performance
        
        for css_file in css_files:
            with self.subTest(css_file=css_file):
                file_path = self.css_dir / css_file
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Basic CSS validation - should contain CSS syntax
                    self.assertTrue('{' in content or '}' in content, 
                                  f"CSS file {css_file} doesn't appear to contain valid CSS")
    
    def test_js_content_validity(self):
        """Test that JavaScript files contain valid JavaScript content"""
        js_files = ["main.js", "auth.js", "dashboard.js"]  # Test subset for performance
        
        for js_file in js_files:
            with self.subTest(js_file=js_file):
                file_path = self.js_dir / js_file
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Basic JavaScript validation - should contain common JS patterns
                    js_patterns = ['function', 'var', 'let', 'const', 'class', '(', ')', '{', '}']
                    has_js_pattern = any(pattern in content for pattern in js_patterns)
                    self.assertTrue(has_js_pattern, 
                                  f"JS file {js_file} doesn't appear to contain valid JavaScript")

class TestFastAPIIntegration(unittest.TestCase):
    """Test FastAPI integration with static files"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = None
        self.client = None
        
        # Try to import FastAPI app and TestClient
        try:
            from main import app
            self.app = app
            
            from fastapi.testclient import TestClient
            self.client = TestClient(app)
            self.fastapi_available = True
        except ImportError:
            self.fastapi_available = False
    
    def test_fastapi_app_import(self):
        """Test that FastAPI app can be imported"""
        self.assertTrue(self.fastapi_available, "FastAPI app could not be imported")
        self.assertIsNotNone(self.app, "FastAPI app is None")
    
    @unittest.skipIf(not hasattr(unittest.TestCase, 'fastapi_available'), "FastAPI not available")
    def test_static_file_mounts(self):
        """Test that static file mounts are configured"""
        if not self.fastapi_available:
            self.skipTest("FastAPI not available")
        
        # Check that the app has routes
        self.assertTrue(hasattr(self.app, 'routes'), "App does not have routes attribute")
        
        # Check for expected static file mounts
        expected_mounts = ["/css", "/js", "/admin", "/static"]
        found_mounts = []
        
        for route in self.app.routes:
            if hasattr(route, 'path') and route.path in expected_mounts:
                found_mounts.append(route.path)
        
        for mount in expected_mounts:
            self.assertIn(mount, found_mounts, f"Static file mount {mount} not found")
    
    def test_admin_html_endpoint(self):
        """Test that admin HTML endpoint is accessible"""
        if not self.fastapi_available:
            self.skipTest("FastAPI not available")
        
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200, "Admin dashboard root should return 200")
        self.assertIn("text/html", response.headers.get("content-type", "").lower())
    
    def test_css_file_accessibility(self):
        """Test that CSS files are accessible via HTTP"""
        if not self.fastapi_available:
            self.skipTest("FastAPI not available")
        
        # Test key CSS files
        css_files = ["modern-dashboard.css", "admin.css"]
        
        for css_file in css_files:
            with self.subTest(css_file=css_file):
                # Test root path
                response = self.client.get(f"/css/{css_file}")
                self.assertEqual(response.status_code, 200, 
                               f"CSS file {css_file} should be accessible at /css/")
                self.assertIn("text/css", response.headers.get("content-type", "").lower())
                
                # Test admin path
                response = self.client.get(f"/admin/css/{css_file}")
                self.assertEqual(response.status_code, 200, 
                               f"CSS file {css_file} should be accessible at /admin/css/")
    
    def test_js_file_accessibility(self):
        """Test that JavaScript files are accessible via HTTP"""
        if not self.fastapi_available:
            self.skipTest("FastAPI not available")
        
        # Test key JS files
        js_files = ["main.js", "auth.js", "dashboard.js"]
        
        for js_file in js_files:
            with self.subTest(js_file=js_file):
                # Test root path
                response = self.client.get(f"/js/{js_file}")
                self.assertEqual(response.status_code, 200, 
                               f"JS file {js_file} should be accessible at /js/")
                
                # Test admin path
                response = self.client.get(f"/admin/js/{js_file}")
                self.assertEqual(response.status_code, 200, 
                               f"JS file {js_file} should be accessible at /admin/js/")
    
    def test_404_error_handling(self):
        """Test proper 404 error handling for missing files"""
        if not self.fastapi_available:
            self.skipTest("FastAPI not available")
        
        missing_files = [
            "/css/nonexistent.css",
            "/js/nonexistent.js",
            "/css/missing-file.css",
            "/js/missing-script.js"
        ]
        
        for missing_file in missing_files:
            with self.subTest(missing_file=missing_file):
                response = self.client.get(missing_file)
                self.assertEqual(response.status_code, 404, 
                               f"Missing file {missing_file} should return 404")

class TestHTMLIntegration(unittest.TestCase):
    """Test HTML file integration with static files"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.html_files = [
            "index.html",
            "tickets.html", 
            "users.html",
            "settings.html",
            "integration.html",
            "logs.html"
        ]
        self.html_dir = Path("admin-dashboard/frontend")
    
    def test_html_files_exist(self):
        """Test that HTML files exist"""
        for html_file in self.html_files:
            with self.subTest(html_file=html_file):
                file_path = self.html_dir / html_file
                self.assertTrue(file_path.exists(), f"HTML file {html_file} does not exist")
                self.assertGreater(file_path.stat().st_size, 0, f"HTML file {html_file} is empty")
    
    def test_html_static_references(self):
        """Test that HTML files reference static assets correctly"""
        # Test the main index.html file
        index_path = self.html_dir / "index.html"
        
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Check for CSS references
            css_patterns = ["/css/", "css/", "/admin/css/"]
            has_css_ref = any(pattern in content for pattern in css_patterns)
            self.assertTrue(has_css_ref, "HTML should reference CSS files")
            
            # Check for JS references
            js_patterns = ["/js/", "js/", "/admin/js/"]
            has_js_ref = any(pattern in content for pattern in js_patterns)
            self.assertTrue(has_js_ref, "HTML should reference JavaScript files")

def run_test_suite():
    """Run the complete test suite"""
    print("*** Static File Serving Test Suite (unittest) ***")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestStaticFileExistence))
    suite.addTests(loader.loadTestsFromTestCase(TestStaticFileContent))
    suite.addTests(loader.loadTestsFromTestCase(TestFastAPIIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestHTMLIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n📊 Test Summary")
    print("=" * 30)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.wasSuccessful():
        print("\n🎉 All tests passed!")
        return True
    else:
        print(f"\n❌ {len(result.failures + result.errors)} tests failed")
        return False

if __name__ == "__main__":
    success = run_test_suite()
    sys.exit(0 if success else 1)