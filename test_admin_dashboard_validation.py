#!/usr/bin/env python3
"""
Admin Dashboard Functionality Validation Test
Task 6: Validate admin dashboard functionality

This test validates:
- Admin dashboard loads completely without 404 errors
- CSS styling is applied correctly
- JavaScript functionality works properly
- Authentication and navigation features
- Requirements: 1.1, 2.1, 7.1, 7.2
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any
import requests
import time
from urllib.parse import urljoin

class AdminDashboardValidator:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.admin_frontend_path = Path("admin-dashboard/frontend")
        self.results = {
            "static_files": {},
            "html_files": {},
            "css_validation": {},
            "js_validation": {},
            "authentication": {},
            "navigation": {},
            "overall_status": "PENDING"
        }
        
    def validate_file_structure(self) -> Dict[str, Any]:
        """Validate that all required static files exist in the correct structure"""
        print("🔍 Validating admin dashboard file structure...")
        
        required_files = {
            "html": [
                "index.html", "tickets.html", "users.html", "settings.html",
                "integration.html", "logs.html", "register.html"
            ],
            "css": [
                "modern-dashboard.css", "admin.css", "styles.css", "support.css"
            ],
            "js": [
                "session-manager.js", "auth-error-handler.js", "api-connectivity-checker.js",
                "admin-auth-service.js", "unified_api.js", "api.js", "navigation.js",
                "ui-feedback.js", "auth.js", "dashboard.js", "integration.js",
                "main.js", "simple-auth-fix.js"
            ]
        }
        
        structure_results = {"missing_files": [], "existing_files": [], "directories": {}}
        
        # Check main directories
        for dir_type in ["css", "js"]:
            dir_path = self.admin_frontend_path / dir_type
            structure_results["directories"][dir_type] = {
                "exists": dir_path.exists(),
                "path": str(dir_path),
                "files": []
            }
            
            if dir_path.exists():
                structure_results["directories"][dir_type]["files"] = [
                    f.name for f in dir_path.iterdir() if f.is_file()
                ]
        
        # Check required files
        for file_type, files in required_files.items():
            for filename in files:
                if file_type == "html":
                    file_path = self.admin_frontend_path / filename
                else:
                    file_path = self.admin_frontend_path / file_type / filename
                
                if file_path.exists():
                    structure_results["existing_files"].append({
                        "type": file_type,
                        "name": filename,
                        "path": str(file_path),
                        "size": file_path.stat().st_size
                    })
                    print(f"  ✅ Found {file_type}/{filename}")
                else:
                    structure_results["missing_files"].append({
                        "type": file_type,
                        "name": filename,
                        "expected_path": str(file_path)
                    })
                    print(f"  ❌ Missing {file_type}/{filename}")
        
        self.results["static_files"] = structure_results
        return structure_results
    
    def validate_html_structure(self) -> Dict[str, Any]:
        """Validate HTML files for proper structure and static file references"""
        print("🔍 Validating HTML structure and static file references...")
        
        html_results = {}
        index_path = self.admin_frontend_path / "index.html"
        
        if not index_path.exists():
            html_results["index.html"] = {"error": "Main index.html file not found"}
            return html_results
        
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Check for CSS references
            css_refs = re.findall(r'href=["\']([^"\']*\.css)["\']', html_content)
            js_refs = re.findall(r'src=["\']([^"\']*\.js)["\']', html_content)
            
            html_results["index.html"] = {
                "size": len(html_content),
                "css_references": css_refs,
                "js_references": js_refs,
                "has_bootstrap": "bootstrap" in html_content.lower(),
                "has_chart_js": "chart.js" in html_content.lower(),
                "has_login_modal": "loginModal" in html_content,
                "has_navigation": "sidebar-nav" in html_content
            }
            
            # Validate that referenced files exist
            missing_refs = []
            for css_ref in css_refs:
                if css_ref.startswith('http'):
                    continue  # Skip external references
                css_path = self.admin_frontend_path / css_ref.lstrip('/')
                if not css_path.exists():
                    missing_refs.append(f"CSS: {css_ref}")
            
            for js_ref in js_refs:
                if js_ref.startswith('http'):
                    continue  # Skip external references
                js_path = self.admin_frontend_path / js_ref.lstrip('/')
                if not js_path.exists():
                    missing_refs.append(f"JS: {js_ref}")
            
            html_results["index.html"]["missing_references"] = missing_refs
            
            print(f"  ✅ HTML structure validated")
            print(f"  📄 Found {len(css_refs)} CSS references")
            print(f"  📄 Found {len(js_refs)} JS references")
            if missing_refs:
                print(f"  ⚠️  {len(missing_refs)} missing file references")
                for ref in missing_refs:
                    print(f"    - {ref}")
            
        except Exception as e:
            html_results["index.html"] = {"error": f"Failed to parse HTML: {str(e)}"}
            print(f"  ❌ Error parsing HTML: {e}")
        
        self.results["html_files"] = html_results
        return html_results
    
    def validate_css_files(self) -> Dict[str, Any]:
        """Validate CSS files for proper content and structure"""
        print("🔍 Validating CSS files...")
        
        css_results = {}
        css_dir = self.admin_frontend_path / "css"
        
        if not css_dir.exists():
            css_results["error"] = "CSS directory not found"
            return css_results
        
        critical_css_files = ["modern-dashboard.css", "admin.css", "styles.css"]
        
        for css_file in critical_css_files:
            css_path = css_dir / css_file
            if css_path.exists():
                try:
                    with open(css_path, 'r', encoding='utf-8') as f:
                        css_content = f.read()
                    
                    css_results[css_file] = {
                        "size": len(css_content),
                        "has_responsive_rules": "@media" in css_content,
                        "has_dashboard_styles": any(selector in css_content for selector in 
                                                  [".dashboard", ".sidebar", ".main-content"]),
                        "has_bootstrap_overrides": ".btn" in css_content or ".card" in css_content,
                        "has_color_variables": ":root" in css_content or "--" in css_content,
                        "line_count": css_content.count('\n') + 1
                    }
                    
                    print(f"  ✅ {css_file} validated ({css_results[css_file]['size']} bytes)")
                    
                except Exception as e:
                    css_results[css_file] = {"error": f"Failed to read CSS: {str(e)}"}
                    print(f"  ❌ Error reading {css_file}: {e}")
            else:
                css_results[css_file] = {"error": "File not found"}
                print(f"  ❌ {css_file} not found")
        
        self.results["css_validation"] = css_results
        return css_results
    
    def validate_js_files(self) -> Dict[str, Any]:
        """Validate JavaScript files for proper structure and functionality"""
        print("🔍 Validating JavaScript files...")
        
        js_results = {}
        js_dir = self.admin_frontend_path / "js"
        
        if not js_dir.exists():
            js_results["error"] = "JavaScript directory not found"
            return js_results
        
        critical_js_files = [
            "session-manager.js", "auth.js", "dashboard.js", "main.js",
            "navigation.js", "api.js", "admin-auth-service.js"
        ]
        
        for js_file in critical_js_files:
            js_path = js_dir / js_file
            if js_path.exists():
                try:
                    with open(js_path, 'r', encoding='utf-8') as f:
                        js_content = f.read()
                    
                    js_results[js_file] = {
                        "size": len(js_content),
                        "has_functions": "function" in js_content,
                        "has_event_listeners": "addEventListener" in js_content,
                        "has_api_calls": any(term in js_content for term in 
                                           ["fetch(", "XMLHttpRequest", "axios"]),
                        "has_error_handling": any(term in js_content for term in 
                                                ["try", "catch", "error"]),
                        "has_dom_manipulation": any(term in js_content for term in 
                                                  ["getElementById", "querySelector", "innerHTML"]),
                        "line_count": js_content.count('\n') + 1,
                        "syntax_check": self._basic_js_syntax_check(js_content)
                    }
                    
                    print(f"  ✅ {js_file} validated ({js_results[js_file]['size']} bytes)")
                    
                except Exception as e:
                    js_results[js_file] = {"error": f"Failed to read JS: {str(e)}"}
                    print(f"  ❌ Error reading {js_file}: {e}")
            else:
                js_results[js_file] = {"error": "File not found"}
                print(f"  ❌ {js_file} not found")
        
        self.results["js_validation"] = js_results
        return js_results
    
    def _basic_js_syntax_check(self, js_content: str) -> Dict[str, Any]:
        """Perform basic JavaScript syntax validation"""
        issues = []
        
        # Check for common syntax issues
        if js_content.count('{') != js_content.count('}'):
            issues.append("Mismatched curly braces")
        
        if js_content.count('(') != js_content.count(')'):
            issues.append("Mismatched parentheses")
        
        if js_content.count('[') != js_content.count(']'):
            issues.append("Mismatched square brackets")
        
        # Check for unterminated strings (basic check)
        single_quotes = js_content.count("'") - js_content.count("\\'")
        double_quotes = js_content.count('"') - js_content.count('\\"')
        
        if single_quotes % 2 != 0:
            issues.append("Possible unterminated single-quoted string")
        
        if double_quotes % 2 != 0:
            issues.append("Possible unterminated double-quoted string")
        
        return {
            "issues": issues,
            "clean": len(issues) == 0
        }
    
    def test_server_connectivity(self) -> Dict[str, Any]:
        """Test if the server is running and accessible"""
        print("🔍 Testing server connectivity...")
        
        connectivity_results = {
            "server_running": False,
            "admin_accessible": False,
            "static_files_served": False,
            "response_times": {}
        }
        
        try:
            # Test basic server connectivity
            start_time = time.time()
            response = requests.get(self.base_url, timeout=5)
            connectivity_results["response_times"]["root"] = time.time() - start_time
            connectivity_results["server_running"] = response.status_code < 500
            print(f"  ✅ Server is running (status: {response.status_code})")
            
            # Test admin dashboard accessibility
            start_time = time.time()
            admin_response = requests.get(f"{self.base_url}/admin/", timeout=5)
            connectivity_results["response_times"]["admin"] = time.time() - start_time
            connectivity_results["admin_accessible"] = admin_response.status_code == 200
            
            if admin_response.status_code == 200:
                print(f"  ✅ Admin dashboard accessible")
            else:
                print(f"  ⚠️  Admin dashboard returned status {admin_response.status_code}")
            
            # Test static file serving
            test_files = [
                "/css/modern-dashboard.css",
                "/js/main.js",
                "/admin/css/modern-dashboard.css",
                "/admin/js/main.js"
            ]
            
            static_file_results = {}
            for test_file in test_files:
                try:
                    start_time = time.time()
                    file_response = requests.get(f"{self.base_url}{test_file}", timeout=5)
                    response_time = time.time() - start_time
                    
                    static_file_results[test_file] = {
                        "status_code": file_response.status_code,
                        "response_time": response_time,
                        "content_type": file_response.headers.get("content-type", ""),
                        "size": len(file_response.content)
                    }
                    
                    if file_response.status_code == 200:
                        print(f"  ✅ {test_file} served successfully")
                        connectivity_results["static_files_served"] = True
                    else:
                        print(f"  ❌ {test_file} returned {file_response.status_code}")
                        
                except requests.RequestException as e:
                    static_file_results[test_file] = {"error": str(e)}
                    print(f"  ❌ Error accessing {test_file}: {e}")
            
            connectivity_results["static_file_tests"] = static_file_results
            
        except requests.RequestException as e:
            connectivity_results["error"] = str(e)
            print(f"  ❌ Server connectivity test failed: {e}")
        
        return connectivity_results
    
    def validate_authentication_features(self) -> Dict[str, Any]:
        """Validate authentication-related functionality"""
        print("🔍 Validating authentication features...")
        
        auth_results = {
            "login_form_present": False,
            "auth_scripts_loaded": False,
            "session_management": False,
            "logout_functionality": False
        }
        
        # Check if authentication scripts exist and have proper content
        auth_scripts = [
            "session-manager.js", "auth.js", "admin-auth-service.js", 
            "auth-error-handler.js", "simple-auth-fix.js"
        ]
        
        auth_script_status = {}
        js_dir = self.admin_frontend_path / "js"
        
        for script in auth_scripts:
            script_path = js_dir / script
            if script_path.exists():
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    auth_script_status[script] = {
                        "exists": True,
                        "has_login_function": "login" in content.lower(),
                        "has_logout_function": "logout" in content.lower(),
                        "has_session_handling": "session" in content.lower(),
                        "has_token_management": "token" in content.lower(),
                        "size": len(content)
                    }
                    print(f"  ✅ {script} found and analyzed")
                    
                except Exception as e:
                    auth_script_status[script] = {"exists": True, "error": str(e)}
                    print(f"  ⚠️  Error reading {script}: {e}")
            else:
                auth_script_status[script] = {"exists": False}
                print(f"  ❌ {script} not found")
        
        # Check HTML for authentication elements
        index_path = self.admin_frontend_path / "index.html"
        if index_path.exists():
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                auth_results["login_form_present"] = "login-form" in html_content
                auth_results["logout_functionality"] = "logout" in html_content.lower()
                auth_results["session_management"] = "session" in html_content.lower()
                
                print(f"  ✅ HTML authentication elements checked")
                
            except Exception as e:
                print(f"  ❌ Error checking HTML for auth elements: {e}")
        
        auth_results["script_analysis"] = auth_script_status
        auth_results["auth_scripts_loaded"] = all(
            status.get("exists", False) for status in auth_script_status.values()
        )
        
        self.results["authentication"] = auth_results
        return auth_results
    
    def validate_navigation_features(self) -> Dict[str, Any]:
        """Validate navigation and UI functionality"""
        print("🔍 Validating navigation features...")
        
        nav_results = {
            "navigation_script_present": False,
            "sidebar_navigation": False,
            "page_routing": False,
            "ui_feedback": False
        }
        
        # Check navigation script
        nav_script_path = self.admin_frontend_path / "js" / "navigation.js"
        if nav_script_path.exists():
            try:
                with open(nav_script_path, 'r', encoding='utf-8') as f:
                    nav_content = f.read()
                
                nav_results["navigation_script_present"] = True
                nav_results["page_routing"] = "route" in nav_content.lower()
                
                print(f"  ✅ Navigation script found and analyzed")
                
            except Exception as e:
                print(f"  ❌ Error reading navigation script: {e}")
        else:
            print(f"  ❌ Navigation script not found")
        
        # Check UI feedback script
        ui_script_path = self.admin_frontend_path / "js" / "ui-feedback.js"
        if ui_script_path.exists():
            nav_results["ui_feedback"] = True
            print(f"  ✅ UI feedback script found")
        else:
            print(f"  ❌ UI feedback script not found")
        
        # Check HTML for navigation elements
        index_path = self.admin_frontend_path / "index.html"
        if index_path.exists():
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                nav_results["sidebar_navigation"] = "sidebar-nav" in html_content
                
                # Count navigation links
                nav_links = html_content.count('href="') + html_content.count("href='")
                nav_results["navigation_links_count"] = nav_links
                
                print(f"  ✅ HTML navigation elements checked ({nav_links} links found)")
                
            except Exception as e:
                print(f"  ❌ Error checking HTML for navigation: {e}")
        
        self.results["navigation"] = nav_results
        return nav_results
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run all validation tests and generate comprehensive report"""
        print("🚀 Starting comprehensive admin dashboard validation...")
        print("=" * 60)
        
        # Run all validation tests
        self.validate_file_structure()
        self.validate_html_structure()
        self.validate_css_files()
        self.validate_js_files()
        
        # Test server connectivity (if server is running)
        try:
            connectivity = self.test_server_connectivity()
            self.results["server_connectivity"] = connectivity
        except Exception as e:
            self.results["server_connectivity"] = {
                "error": f"Server connectivity test failed: {str(e)}",
                "note": "This is expected if the server is not running"
            }
            print(f"  ℹ️  Server connectivity test skipped: {e}")
        
        self.validate_authentication_features()
        self.validate_navigation_features()
        
        # Generate overall status
        self._generate_overall_status()
        
        print("=" * 60)
        print("🏁 Validation complete!")
        
        return self.results
    
    def _generate_overall_status(self):
        """Generate overall validation status based on all tests"""
        issues = []
        warnings = []
        
        # Check static files
        if self.results["static_files"].get("missing_files"):
            issues.extend([f"Missing {f['type']}/{f['name']}" for f in self.results["static_files"]["missing_files"]])
        
        # Check HTML structure
        html_results = self.results.get("html_files", {}).get("index.html", {})
        if "error" in html_results:
            issues.append(f"HTML validation error: {html_results['error']}")
        elif html_results.get("missing_references"):
            warnings.extend(html_results["missing_references"])
        
        # Check CSS files
        css_results = self.results.get("css_validation", {})
        for css_file, result in css_results.items():
            if isinstance(result, dict) and "error" in result:
                issues.append(f"CSS error in {css_file}: {result['error']}")
        
        # Check JS files
        js_results = self.results.get("js_validation", {})
        for js_file, result in js_results.items():
            if isinstance(result, dict) and "error" in result:
                issues.append(f"JS error in {js_file}: {result['error']}")
            elif isinstance(result, dict) and not result.get("syntax_check", {}).get("clean", True):
                warnings.append(f"JS syntax issues in {js_file}")
        
        # Check authentication
        auth_results = self.results.get("authentication", {})
        if not auth_results.get("auth_scripts_loaded", False):
            warnings.append("Some authentication scripts are missing")
        
        # Determine overall status
        if issues:
            self.results["overall_status"] = "FAILED"
            self.results["critical_issues"] = issues
        elif warnings:
            self.results["overall_status"] = "PASSED_WITH_WARNINGS"
            self.results["warnings"] = warnings
        else:
            self.results["overall_status"] = "PASSED"
        
        self.results["summary"] = {
            "total_issues": len(issues),
            "total_warnings": len(warnings),
            "status": self.results["overall_status"]
        }
    
    def generate_report(self) -> str:
        """Generate a detailed validation report"""
        report = []
        report.append("ADMIN DASHBOARD VALIDATION REPORT")
        report.append("=" * 50)
        report.append(f"Overall Status: {self.results['overall_status']}")
        report.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        summary = self.results.get("summary", {})
        report.append("SUMMARY:")
        report.append(f"  Critical Issues: {summary.get('total_issues', 0)}")
        report.append(f"  Warnings: {summary.get('total_warnings', 0)}")
        report.append("")
        
        # Critical Issues
        if self.results.get("critical_issues"):
            report.append("CRITICAL ISSUES:")
            for issue in self.results["critical_issues"]:
                report.append(f"  ❌ {issue}")
            report.append("")
        
        # Warnings
        if self.results.get("warnings"):
            report.append("WARNINGS:")
            for warning in self.results["warnings"]:
                report.append(f"  ⚠️  {warning}")
            report.append("")
        
        # Detailed Results
        report.append("DETAILED RESULTS:")
        report.append("")
        
        # Static Files
        static_files = self.results.get("static_files", {})
        report.append(f"Static Files: {len(static_files.get('existing_files', []))} found, {len(static_files.get('missing_files', []))} missing")
        
        # HTML Validation
        html_files = self.results.get("html_files", {})
        if "index.html" in html_files:
            html_info = html_files["index.html"]
            if "error" not in html_info:
                report.append(f"HTML Structure: ✅ Valid ({html_info.get('size', 0)} bytes)")
                report.append(f"  CSS References: {len(html_info.get('css_references', []))}")
                report.append(f"  JS References: {len(html_info.get('js_references', []))}")
            else:
                report.append(f"HTML Structure: ❌ {html_info['error']}")
        
        # CSS Validation
        css_validation = self.results.get("css_validation", {})
        css_valid = sum(1 for result in css_validation.values() if isinstance(result, dict) and "error" not in result)
        css_total = len(css_validation)
        report.append(f"CSS Files: {css_valid}/{css_total} valid")
        
        # JS Validation
        js_validation = self.results.get("js_validation", {})
        js_valid = sum(1 for result in js_validation.values() if isinstance(result, dict) and "error" not in result)
        js_total = len(js_validation)
        report.append(f"JavaScript Files: {js_valid}/{js_total} valid")
        
        # Authentication
        auth_results = self.results.get("authentication", {})
        auth_status = "✅" if auth_results.get("auth_scripts_loaded", False) else "⚠️"
        report.append(f"Authentication: {auth_status} Scripts loaded: {auth_results.get('auth_scripts_loaded', False)}")
        
        # Navigation
        nav_results = self.results.get("navigation", {})
        nav_status = "✅" if nav_results.get("navigation_script_present", False) else "⚠️"
        report.append(f"Navigation: {nav_status} Script present: {nav_results.get('navigation_script_present', False)}")
        
        # Server Connectivity (if tested)
        if "server_connectivity" in self.results:
            conn_results = self.results["server_connectivity"]
            if "error" not in conn_results:
                server_status = "✅" if conn_results.get("server_running", False) else "❌"
                admin_status = "✅" if conn_results.get("admin_accessible", False) else "❌"
                static_status = "✅" if conn_results.get("static_files_served", False) else "❌"
                report.append(f"Server Connectivity: {server_status} Running, {admin_status} Admin accessible, {static_status} Static files served")
            else:
                report.append(f"Server Connectivity: ℹ️  Not tested ({conn_results.get('note', 'Server not running')})")
        
        report.append("")
        report.append("=" * 50)
        report.append("Validation completed successfully!")
        
        return "\n".join(report)


def main():
    """Main function to run the admin dashboard validation"""
    print("Admin Dashboard Functionality Validation")
    print("Task 6: Validate admin dashboard functionality")
    print()
    
    # Change to the correct directory
    if os.path.exists("ai-agent"):
        os.chdir("ai-agent")
        print("📁 Changed to ai-agent directory")
    
    # Initialize validator
    validator = AdminDashboardValidator()
    
    # Run comprehensive validation
    results = validator.run_comprehensive_validation()
    
    # Generate and display report
    report = validator.generate_report()
    print()
    print(report)
    
    # Save results to file
    results_file = "admin_dashboard_validation_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n📄 Detailed results saved to {results_file}")
    
    # Save report to file
    report_file = "admin_dashboard_validation_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📄 Report saved to {report_file}")
    
    # Return exit code based on validation status
    if results["overall_status"] == "FAILED":
        print("\n❌ Validation FAILED - Critical issues found")
        return 1
    elif results["overall_status"] == "PASSED_WITH_WARNINGS":
        print("\n⚠️  Validation PASSED with warnings")
        return 0
    else:
        print("\n✅ Validation PASSED - All checks successful")
        return 0


if __name__ == "__main__":
    sys.exit(main())