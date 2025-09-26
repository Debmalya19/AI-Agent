#!/usr/bin/env python3
"""
Comprehensive Admin Dashboard UI Validation Test Suite

This test suite validates all pages for consistency and functionality according to:
- Requirements: 1.1, 1.2, 1.3, 1.4, 8.1, 8.2, 8.3, 8.4, 8.5

Test Coverage:
- Responsive design across different screen sizes
- HTML structure and CSS consistency across all pages
- Interactive elements (buttons, forms, modals, filters)
- Error handling and loading states
- Navigation flow between all pages
"""

import os
import sys
import json
import time
import requests
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime

class AdminDashboardValidator:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.admin_dashboard_path = "ai-agent/admin-dashboard/frontend"
        self.pages = [
            "index.html",
            "tickets.html", 
            "users.html",
            "integration.html",
            "settings.html",
            "logs.html"
        ]
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "responsive_design": {},
            "html_structure": {},
            "css_consistency": {},
            "interactive_elements": {},
            "error_handling": {},
            "navigation_flow": {},
            "overall_score": 0
        }
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome WebDriver with responsive testing capabilities"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            return True
        except Exception as e:
            print(f"Failed to setup Chrome driver: {e}")
            return False
    
    def teardown_driver(self):
        """Clean up WebDriver"""
        if self.driver:
            self.driver.quit()
    
    def test_responsive_design(self):
        """Test responsive design across different screen sizes"""
        print("Testing responsive design...")
        
        # Common screen sizes to test
        screen_sizes = [
            ("mobile", 375, 667),
            ("tablet", 768, 1024),
            ("desktop", 1920, 1080),
            ("large_desktop", 2560, 1440)
        ]
        
        for page in self.pages:
            page_results = {}
            page_path = f"file://{os.path.abspath(os.path.join(self.admin_dashboard_path, page))}"
            
            for size_name, width, height in screen_sizes:
                try:
                    self.driver.set_window_size(width, height)
                    self.driver.get(page_path)
                    time.sleep(2)  # Allow page to load
                    
                    # Check if page is responsive
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    viewport_width = self.driver.execute_script("return window.innerWidth")
                    
                    # Check for horizontal scrollbar (indicates non-responsive design)
                    has_horizontal_scroll = self.driver.execute_script(
                        "return document.body.scrollWidth > window.innerWidth"
                    )
                    
                    # Check if sidebar collapses on mobile
                    sidebar_elements = self.driver.find_elements(By.CLASS_NAME, "sidebar")
                    sidebar_responsive = True
                    if sidebar_elements and width < 768:
                        sidebar = sidebar_elements[0]
                        sidebar_display = sidebar.value_of_css_property("display")
                        if sidebar_display not in ["none", "block"]:
                            sidebar_responsive = False
                    
                    page_results[size_name] = {
                        "viewport_width": viewport_width,
                        "has_horizontal_scroll": has_horizontal_scroll,
                        "sidebar_responsive": sidebar_responsive,
                        "responsive": not has_horizontal_scroll and sidebar_responsive
                    }
                    
                except Exception as e:
                    page_results[size_name] = {"error": str(e), "responsive": False}
            
            self.test_results["responsive_design"][page] = page_results
    
    def test_html_structure_consistency(self):
        """Validate HTML structure and consistency across all pages"""
        print("Testing HTML structure consistency...")
        
        common_elements = [
            "sidebar",
            "main-content", 
            "content-header",
            "navbar",
            "breadcrumb"
        ]
        
        for page in self.pages:
            page_results = {
                "valid_html": False,
                "common_elements": {},
                "structure_score": 0
            }
            
            try:
                page_path = os.path.join(self.admin_dashboard_path, page)
                
                # Read and parse HTML
                with open(page_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Check for basic HTML structure
                has_doctype = html_content.strip().startswith('<!DOCTYPE')
                has_html_tag = soup.find('html') is not None
                has_head_tag = soup.find('head') is not None
                has_body_tag = soup.find('body') is not None
                has_title = soup.find('title') is not None
                
                page_results["valid_html"] = all([
                    has_doctype, has_html_tag, has_head_tag, has_body_tag, has_title
                ])
                
                # Check for common dashboard elements
                elements_found = 0
                for element_class in common_elements:
                    elements = soup.find_all(class_=lambda x: x and element_class in x)
                    page_results["common_elements"][element_class] = len(elements) > 0
                    if len(elements) > 0:
                        elements_found += 1
                
                page_results["structure_score"] = (elements_found / len(common_elements)) * 100
                
                # Check for modern-dashboard.css inclusion
                css_links = soup.find_all('link', rel='stylesheet')
                has_modern_css = any('modern-dashboard.css' in link.get('href', '') for link in css_links)
                page_results["has_modern_css"] = has_modern_css
                
            except Exception as e:
                page_results["error"] = str(e)
            
            self.test_results["html_structure"][page] = page_results
    
    def test_css_consistency(self):
        """Test CSS consistency across all pages"""
        print("Testing CSS consistency...")
        
        for page in self.pages:
            page_results = {}
            page_path = f"file://{os.path.abspath(os.path.join(self.admin_dashboard_path, page))}"
            
            try:
                self.driver.get(page_path)
                time.sleep(2)
                
                # Check if modern-dashboard.css is loaded
                stylesheets = self.driver.execute_script("""
                    return Array.from(document.styleSheets).map(sheet => {
                        try {
                            return sheet.href || 'inline';
                        } catch(e) {
                            return 'cross-origin';
                        }
                    });
                """)
                
                has_modern_css = any('modern-dashboard.css' in str(sheet) for sheet in stylesheets)
                page_results["has_modern_css"] = has_modern_css
                
                # Check consistent styling for common elements
                common_selectors = [
                    ".btn",
                    ".card", 
                    ".table",
                    ".form-control",
                    ".sidebar",
                    ".navbar"
                ]
                
                consistent_styles = {}
                for selector in common_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        # Get computed styles for first element
                        element = elements[0]
                        styles = self.driver.execute_script("""
                            var element = arguments[0];
                            var styles = window.getComputedStyle(element);
                            return {
                                'font-family': styles.fontFamily,
                                'color': styles.color,
                                'background-color': styles.backgroundColor,
                                'border-radius': styles.borderRadius
                            };
                        """, element)
                        consistent_styles[selector] = styles
                
                page_results["element_styles"] = consistent_styles
                
            except Exception as e:
                page_results["error"] = str(e)
            
            self.test_results["css_consistency"][page] = page_results
    
    def test_interactive_elements(self):
        """Test all interactive elements (buttons, forms, modals, filters)"""
        print("Testing interactive elements...")
        
        for page in self.pages:
            page_results = {
                "buttons": {},
                "forms": {},
                "modals": {},
                "filters": {}
            }
            
            page_path = f"file://{os.path.abspath(os.path.join(self.admin_dashboard_path, page))}"
            
            try:
                self.driver.get(page_path)
                time.sleep(3)  # Allow page and JS to load
                
                # Test buttons
                buttons = self.driver.find_elements(By.CSS_SELECTOR, "button, .btn, input[type='button'], input[type='submit']")
                page_results["buttons"]["count"] = len(buttons)
                page_results["buttons"]["clickable"] = 0
                
                for i, button in enumerate(buttons[:5]):  # Test first 5 buttons
                    try:
                        if button.is_enabled() and button.is_displayed():
                            page_results["buttons"]["clickable"] += 1
                    except:
                        pass
                
                # Test forms
                forms = self.driver.find_elements(By.TAG_NAME, "form")
                page_results["forms"]["count"] = len(forms)
                page_results["forms"]["valid"] = 0
                
                for form in forms:
                    try:
                        # Check if form has proper action or event handlers
                        action = form.get_attribute("action")
                        onsubmit = form.get_attribute("onsubmit")
                        if action or onsubmit:
                            page_results["forms"]["valid"] += 1
                    except:
                        pass
                
                # Test modals
                modals = self.driver.find_elements(By.CSS_SELECTOR, ".modal, [data-bs-toggle='modal']")
                page_results["modals"]["count"] = len(modals)
                
                # Test filters (common filter elements)
                filters = self.driver.find_elements(By.CSS_SELECTOR, "select, input[type='search'], .filter-control")
                page_results["filters"]["count"] = len(filters)
                
            except Exception as e:
                page_results["error"] = str(e)
            
            self.test_results["interactive_elements"][page] = page_results
    
    def test_error_handling_and_loading_states(self):
        """Test error handling and loading states"""
        print("Testing error handling and loading states...")
        
        for page in self.pages:
            page_results = {
                "loading_indicators": {},
                "error_elements": {},
                "feedback_elements": {}
            }
            
            page_path = f"file://{os.path.abspath(os.path.join(self.admin_dashboard_path, page))}"
            
            try:
                self.driver.get(page_path)
                time.sleep(2)
                
                # Check for loading indicators
                loading_selectors = [
                    ".spinner", ".loading", ".loader", 
                    "[data-loading]", ".fa-spinner", ".loading-overlay"
                ]
                
                loading_found = 0
                for selector in loading_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        loading_found += 1
                
                page_results["loading_indicators"]["types_found"] = loading_found
                page_results["loading_indicators"]["has_loading_states"] = loading_found > 0
                
                # Check for error handling elements
                error_selectors = [
                    ".alert", ".error", ".alert-danger", 
                    ".error-message", "[data-error]"
                ]
                
                error_found = 0
                for selector in error_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        error_found += 1
                
                page_results["error_elements"]["types_found"] = error_found
                page_results["error_elements"]["has_error_handling"] = error_found > 0
                
                # Check for success/feedback elements
                feedback_selectors = [
                    ".alert-success", ".success", ".notification",
                    ".toast", "[data-success]"
                ]
                
                feedback_found = 0
                for selector in feedback_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        feedback_found += 1
                
                page_results["feedback_elements"]["types_found"] = feedback_found
                page_results["feedback_elements"]["has_feedback"] = feedback_found > 0
                
            except Exception as e:
                page_results["error"] = str(e)
            
            self.test_results["error_handling"][page] = page_results
    
    def test_navigation_flow(self):
        """Test navigation flow between all pages"""
        print("Testing navigation flow...")
        
        navigation_results = {
            "sidebar_navigation": {},
            "breadcrumbs": {},
            "page_transitions": {}
        }
        
        for page in self.pages:
            page_path = f"file://{os.path.abspath(os.path.join(self.admin_dashboard_path, page))}"
            
            try:
                self.driver.get(page_path)
                time.sleep(2)
                
                # Test sidebar navigation
                sidebar_links = self.driver.find_elements(By.CSS_SELECTOR, ".sidebar a, .nav-link")
                navigation_results["sidebar_navigation"][page] = {
                    "link_count": len(sidebar_links),
                    "active_states": 0
                }
                
                # Check for active navigation states
                for link in sidebar_links:
                    classes = link.get_attribute("class") or ""
                    if "active" in classes:
                        navigation_results["sidebar_navigation"][page]["active_states"] += 1
                
                # Test breadcrumbs
                breadcrumbs = self.driver.find_elements(By.CSS_SELECTOR, ".breadcrumb, .breadcrumb-item")
                navigation_results["breadcrumbs"][page] = {
                    "has_breadcrumbs": len(breadcrumbs) > 0,
                    "breadcrumb_count": len(breadcrumbs)
                }
                
                # Test page title
                title = self.driver.title
                navigation_results["page_transitions"][page] = {
                    "has_title": bool(title and title.strip()),
                    "title": title
                }
                
            except Exception as e:
                navigation_results[page] = {"error": str(e)}
        
        self.test_results["navigation_flow"] = navigation_results
    
    def calculate_overall_score(self):
        """Calculate overall validation score"""
        scores = []
        
        # Responsive design score
        responsive_score = 0
        responsive_total = 0
        for page_data in self.test_results["responsive_design"].values():
            for size_data in page_data.values():
                if isinstance(size_data, dict) and "responsive" in size_data:
                    responsive_total += 1
                    if size_data["responsive"]:
                        responsive_score += 1
        
        if responsive_total > 0:
            scores.append((responsive_score / responsive_total) * 100)
        
        # HTML structure score
        structure_scores = []
        for page_data in self.test_results["html_structure"].values():
            if "structure_score" in page_data:
                structure_scores.append(page_data["structure_score"])
        
        if structure_scores:
            scores.append(sum(structure_scores) / len(structure_scores))
        
        # CSS consistency score
        css_score = 0
        css_total = 0
        for page_data in self.test_results["css_consistency"].values():
            if "has_modern_css" in page_data:
                css_total += 1
                if page_data["has_modern_css"]:
                    css_score += 1
        
        if css_total > 0:
            scores.append((css_score / css_total) * 100)
        
        # Interactive elements score
        interactive_score = 0
        interactive_total = 0
        for page_data in self.test_results["interactive_elements"].values():
            if "buttons" in page_data and "count" in page_data["buttons"]:
                interactive_total += 1
                if page_data["buttons"]["count"] > 0:
                    interactive_score += 1
        
        if interactive_total > 0:
            scores.append((interactive_score / interactive_total) * 100)
        
        # Calculate final score
        if scores:
            self.test_results["overall_score"] = sum(scores) / len(scores)
        else:
            self.test_results["overall_score"] = 0
    
    def run_all_tests(self):
        """Run all validation tests"""
        print("Starting comprehensive admin dashboard validation...")
        
        if not self.setup_driver():
            print("Failed to setup WebDriver. Skipping browser-based tests.")
            return False
        
        try:
            # Run all test suites
            self.test_html_structure_consistency()
            self.test_responsive_design()
            self.test_css_consistency()
            self.test_interactive_elements()
            self.test_error_handling_and_loading_states()
            self.test_navigation_flow()
            
            # Calculate overall score
            self.calculate_overall_score()
            
            return True
            
        except Exception as e:
            print(f"Error during testing: {e}")
            return False
        
        finally:
            self.teardown_driver()
    
    def generate_report(self):
        """Generate detailed test report"""
        report_path = "ai-agent/admin_dashboard_validation_report.json"
        
        with open(report_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        # Generate summary report
        summary_path = "ai-agent/admin_dashboard_validation_summary.md"
        
        with open(summary_path, 'w') as f:
            f.write("# Admin Dashboard Validation Report\n\n")
            f.write(f"**Generated:** {self.test_results['timestamp']}\n")
            f.write(f"**Overall Score:** {self.test_results['overall_score']:.1f}%\n\n")
            
            # Responsive Design Summary
            f.write("## Responsive Design Results\n\n")
            for page, results in self.test_results["responsive_design"].items():
                f.write(f"### {page}\n")
                for size, data in results.items():
                    if isinstance(data, dict) and "responsive" in data:
                        status = "✅ Pass" if data["responsive"] else "❌ Fail"
                        f.write(f"- **{size}**: {status}\n")
                f.write("\n")
            
            # HTML Structure Summary
            f.write("## HTML Structure Results\n\n")
            for page, results in self.test_results["html_structure"].items():
                if "structure_score" in results:
                    score = results["structure_score"]
                    status = "✅ Pass" if score >= 80 else "⚠️ Warning" if score >= 60 else "❌ Fail"
                    f.write(f"- **{page}**: {status} ({score:.1f}%)\n")
            f.write("\n")
            
            # CSS Consistency Summary
            f.write("## CSS Consistency Results\n\n")
            for page, results in self.test_results["css_consistency"].items():
                if "has_modern_css" in results:
                    status = "✅ Pass" if results["has_modern_css"] else "❌ Fail"
                    f.write(f"- **{page}**: {status}\n")
            f.write("\n")
            
            # Interactive Elements Summary
            f.write("## Interactive Elements Results\n\n")
            for page, results in self.test_results["interactive_elements"].items():
                if "buttons" in results:
                    button_count = results["buttons"].get("count", 0)
                    form_count = results["forms"].get("count", 0)
                    modal_count = results["modals"].get("count", 0)
                    f.write(f"- **{page}**: {button_count} buttons, {form_count} forms, {modal_count} modals\n")
            f.write("\n")
        
        print(f"Validation report saved to: {report_path}")
        print(f"Summary report saved to: {summary_path}")

def main():
    """Main execution function"""
    validator = AdminDashboardValidator()
    
    print("=" * 60)
    print("ADMIN DASHBOARD COMPREHENSIVE VALIDATION")
    print("=" * 60)
    
    success = validator.run_all_tests()
    
    if success:
        validator.generate_report()
        print(f"\nValidation completed with overall score: {validator.test_results['overall_score']:.1f}%")
        
        if validator.test_results['overall_score'] >= 80:
            print("✅ Dashboard validation PASSED")
            return 0
        elif validator.test_results['overall_score'] >= 60:
            print("⚠️ Dashboard validation passed with warnings")
            return 1
        else:
            print("❌ Dashboard validation FAILED")
            return 2
    else:
        print("❌ Validation could not be completed")
        return 3

if __name__ == "__main__":
    sys.exit(main())