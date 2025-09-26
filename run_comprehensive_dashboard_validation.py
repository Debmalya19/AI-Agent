#!/usr/bin/env python3
"""
Comprehensive Dashboard Validation Test Runner

This script runs all validation tests for the admin dashboard UI enhancement
according to task 12 requirements:
- Test responsive design across different screen sizes
- Validate HTML structure and CSS consistency across all pages
- Test all interactive elements (buttons, forms, modals, filters)
- Verify proper error handling and loading states
- Test navigation flow between all pages
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

class ComprehensiveDashboardValidator:
    def __init__(self):
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "test_suites": {},
            "overall_summary": {},
            "recommendations": []
        }
        
    def run_html_structure_validation(self):
        """Run HTML structure validation test"""
        print("=" * 60)
        print("RUNNING HTML STRUCTURE VALIDATION")
        print("=" * 60)
        
        try:
            result = subprocess.run([
                sys.executable, "test_html_structure_validation.py"
            ], capture_output=True, text=True, cwd=".")
            
            self.test_results["test_suites"]["html_structure"] = {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "status": "PASS" if result.returncode == 0 else "FAIL" if result.returncode == 2 else "WARNING"
            }
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
                
            return result.returncode
            
        except Exception as e:
            print(f"Error running HTML structure validation: {e}")
            self.test_results["test_suites"]["html_structure"] = {
                "exit_code": -1,
                "error": str(e),
                "status": "ERROR"
            }
            return -1
    
    def run_navigation_flow_test(self):
        """Run navigation flow test"""
        print("=" * 60)
        print("RUNNING NAVIGATION FLOW TEST")
        print("=" * 60)
        
        try:
            result = subprocess.run([
                sys.executable, "test_navigation_comprehensive.py"
            ], capture_output=True, text=True, cwd=".")
            
            self.test_results["test_suites"]["navigation_flow"] = {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "status": "PASS" if result.returncode == 0 else "FAIL" if result.returncode == 2 else "WARNING"
            }
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
                
            return result.returncode
            
        except Exception as e:
            print(f"Error running navigation flow test: {e}")
            self.test_results["test_suites"]["navigation_flow"] = {
                "exit_code": -1,
                "error": str(e),
                "status": "ERROR"
            }
            return -1
    
    def check_responsive_design_manually(self):
        """Manual check for responsive design elements"""
        print("=" * 60)
        print("CHECKING RESPONSIVE DESIGN ELEMENTS")
        print("=" * 60)
        
        responsive_checks = {
            "viewport_meta_tags": 0,
            "bootstrap_responsive_classes": 0,
            "css_media_queries": 0,
            "flexible_layouts": 0
        }
        
        pages = [
            "admin-dashboard/frontend/index.html",
            "admin-dashboard/frontend/tickets.html", 
            "admin-dashboard/frontend/users.html",
            "admin-dashboard/frontend/integration.html",
            "admin-dashboard/frontend/settings.html",
            "admin-dashboard/frontend/logs.html"
        ]
        
        for page_path in pages:
            if os.path.exists(page_path):
                try:
                    with open(page_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check viewport meta tag
                    if 'name="viewport"' in content:
                        responsive_checks["viewport_meta_tags"] += 1
                    
                    # Check Bootstrap responsive classes
                    responsive_classes = ['col-', 'd-', 'flex-', 'container', 'row']
                    if any(cls in content for cls in responsive_classes):
                        responsive_checks["bootstrap_responsive_classes"] += 1
                    
                    # Check for CSS media queries (basic check)
                    if '@media' in content or 'media=' in content:
                        responsive_checks["css_media_queries"] += 1
                    
                    # Check for flexible layout indicators
                    flexible_indicators = ['flex', 'grid', 'responsive', 'mobile']
                    if any(indicator in content.lower() for indicator in flexible_indicators):
                        responsive_checks["flexible_layouts"] += 1
                        
                except Exception as e:
                    print(f"Error checking {page_path}: {e}")
        
        total_pages = len(pages)
        responsive_score = 0
        
        for check, count in responsive_checks.items():
            percentage = (count / total_pages) * 100 if total_pages > 0 else 0
            print(f"{check}: {count}/{total_pages} pages ({percentage:.1f}%)")
            responsive_score += percentage
        
        responsive_score = responsive_score / len(responsive_checks)
        
        self.test_results["test_suites"]["responsive_design"] = {
            "checks": responsive_checks,
            "total_pages": total_pages,
            "score": responsive_score,
            "status": "PASS" if responsive_score >= 80 else "WARNING" if responsive_score >= 60 else "FAIL"
        }
        
        print(f"\\nResponsive Design Score: {responsive_score:.1f}%")
        return 0 if responsive_score >= 80 else 1 if responsive_score >= 60 else 2
    
    def check_interactive_elements_manually(self):
        """Manual check for interactive elements"""
        print("=" * 60)
        print("CHECKING INTERACTIVE ELEMENTS")
        print("=" * 60)
        
        interactive_checks = {
            "buttons": 0,
            "forms": 0,
            "modals": 0,
            "tables": 0,
            "input_fields": 0,
            "javascript_files": 0
        }
        
        pages = [
            "admin-dashboard/frontend/index.html",
            "admin-dashboard/frontend/tickets.html", 
            "admin-dashboard/frontend/users.html",
            "admin-dashboard/frontend/integration.html",
            "admin-dashboard/frontend/settings.html",
            "admin-dashboard/frontend/logs.html"
        ]
        
        for page_path in pages:
            if os.path.exists(page_path):
                try:
                    with open(page_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for buttons
                    if '<button' in content or 'class="btn' in content:
                        interactive_checks["buttons"] += 1
                    
                    # Check for forms
                    if '<form' in content:
                        interactive_checks["forms"] += 1
                    
                    # Check for modals
                    if 'modal' in content.lower() or 'data-bs-toggle="modal"' in content:
                        interactive_checks["modals"] += 1
                    
                    # Check for tables
                    if '<table' in content or 'class="table' in content:
                        interactive_checks["tables"] += 1
                    
                    # Check for input fields
                    if '<input' in content or '<select' in content or '<textarea' in content:
                        interactive_checks["input_fields"] += 1
                    
                    # Check for JavaScript files
                    if '<script' in content and 'src=' in content:
                        interactive_checks["javascript_files"] += 1
                        
                except Exception as e:
                    print(f"Error checking {page_path}: {e}")
        
        total_pages = len(pages)
        interactive_score = 0
        
        for check, count in interactive_checks.items():
            percentage = (count / total_pages) * 100 if total_pages > 0 else 0
            print(f"{check}: {count}/{total_pages} pages ({percentage:.1f}%)")
            interactive_score += percentage
        
        interactive_score = interactive_score / len(interactive_checks)
        
        self.test_results["test_suites"]["interactive_elements"] = {
            "checks": interactive_checks,
            "total_pages": total_pages,
            "score": interactive_score,
            "status": "PASS" if interactive_score >= 80 else "WARNING" if interactive_score >= 60 else "FAIL"
        }
        
        print(f"\\nInteractive Elements Score: {interactive_score:.1f}%")
        return 0 if interactive_score >= 80 else 1 if interactive_score >= 60 else 2
    
    def check_error_handling_manually(self):
        """Manual check for error handling and loading states"""
        print("=" * 60)
        print("CHECKING ERROR HANDLING AND LOADING STATES")
        print("=" * 60)
        
        error_handling_checks = {
            "alert_elements": 0,
            "loading_indicators": 0,
            "error_containers": 0,
            "success_containers": 0,
            "form_validation": 0,
            "ui_feedback_js": 0
        }
        
        pages = [
            "admin-dashboard/frontend/index.html",
            "admin-dashboard/frontend/tickets.html", 
            "admin-dashboard/frontend/users.html",
            "admin-dashboard/frontend/integration.html",
            "admin-dashboard/frontend/settings.html",
            "admin-dashboard/frontend/logs.html"
        ]
        
        # Check JavaScript files for error handling
        js_files = [
            "admin-dashboard/frontend/js/ui-feedback.js",
            "admin-dashboard/frontend/js/auth-error-handler.js",
            "admin-dashboard/frontend/js/unified_api.js"
        ]
        
        for js_file in js_files:
            if os.path.exists(js_file):
                error_handling_checks["ui_feedback_js"] += 1
        
        for page_path in pages:
            if os.path.exists(page_path):
                try:
                    with open(page_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for alert elements
                    if 'alert' in content.lower() or 'notification' in content.lower():
                        error_handling_checks["alert_elements"] += 1
                    
                    # Check for loading indicators
                    loading_indicators = ['spinner', 'loading', 'loader', 'fa-spinner']
                    if any(indicator in content.lower() for indicator in loading_indicators):
                        error_handling_checks["loading_indicators"] += 1
                    
                    # Check for error containers
                    error_indicators = ['error', 'alert-danger', 'text-danger']
                    if any(indicator in content.lower() for indicator in error_indicators):
                        error_handling_checks["error_containers"] += 1
                    
                    # Check for success containers
                    success_indicators = ['success', 'alert-success', 'text-success']
                    if any(indicator in content.lower() for indicator in success_indicators):
                        error_handling_checks["success_containers"] += 1
                    
                    # Check for form validation
                    validation_indicators = ['invalid-feedback', 'valid-feedback', 'required']
                    if any(indicator in content.lower() for indicator in validation_indicators):
                        error_handling_checks["form_validation"] += 1
                        
                except Exception as e:
                    print(f"Error checking {page_path}: {e}")
        
        total_pages = len(pages)
        error_handling_score = 0
        
        for check, count in error_handling_checks.items():
            if check == "ui_feedback_js":
                percentage = (count / len(js_files)) * 100 if len(js_files) > 0 else 0
            else:
                percentage = (count / total_pages) * 100 if total_pages > 0 else 0
            print(f"{check}: {count} ({percentage:.1f}%)")
            error_handling_score += percentage
        
        error_handling_score = error_handling_score / len(error_handling_checks)
        
        self.test_results["test_suites"]["error_handling"] = {
            "checks": error_handling_checks,
            "total_pages": total_pages,
            "score": error_handling_score,
            "status": "PASS" if error_handling_score >= 80 else "WARNING" if error_handling_score >= 60 else "FAIL"
        }
        
        print(f"\\nError Handling Score: {error_handling_score:.1f}%")
        return 0 if error_handling_score >= 80 else 1 if error_handling_score >= 60 else 2
    
    def calculate_overall_score(self):
        """Calculate overall validation score"""
        scores = []
        statuses = []
        
        for suite_name, suite_data in self.test_results["test_suites"].items():
            if "score" in suite_data:
                scores.append(suite_data["score"])
            elif suite_data.get("status") == "PASS":
                scores.append(100)
            elif suite_data.get("status") == "WARNING":
                scores.append(70)
            elif suite_data.get("status") == "FAIL":
                scores.append(30)
            else:
                scores.append(0)
            
            statuses.append(suite_data.get("status", "ERROR"))
        
        overall_score = sum(scores) / len(scores) if scores else 0
        
        # Determine overall status
        if all(status == "PASS" for status in statuses):
            overall_status = "PASS"
        elif any(status == "FAIL" for status in statuses):
            overall_status = "FAIL"
        else:
            overall_status = "WARNING"
        
        self.test_results["overall_summary"] = {
            "score": overall_score,
            "status": overall_status,
            "total_suites": len(self.test_results["test_suites"]),
            "passed_suites": sum(1 for status in statuses if status == "PASS"),
            "warning_suites": sum(1 for status in statuses if status == "WARNING"),
            "failed_suites": sum(1 for status in statuses if status == "FAIL")
        }
        
        return overall_score, overall_status
    
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        recommendations = []
        
        for suite_name, suite_data in self.test_results["test_suites"].items():
            status = suite_data.get("status", "ERROR")
            
            if status == "FAIL":
                if suite_name == "html_structure":
                    recommendations.append("Fix HTML structure issues: ensure all pages have proper DOCTYPE, HTML, head, body, and title tags")
                    recommendations.append("Include modern-dashboard.css in all pages for consistent styling")
                elif suite_name == "navigation_flow":
                    recommendations.append("Fix navigation consistency: ensure all pages have sidebar and proper navigation links")
                    recommendations.append("Add breadcrumb navigation to all pages")
                elif suite_name == "responsive_design":
                    recommendations.append("Improve responsive design: add viewport meta tags and responsive CSS classes")
                elif suite_name == "interactive_elements":
                    recommendations.append("Enhance interactive elements: ensure all pages have proper buttons, forms, and JavaScript functionality")
                elif suite_name == "error_handling":
                    recommendations.append("Implement error handling: add loading indicators, error messages, and success feedback")
            
            elif status == "WARNING":
                if suite_name == "navigation_flow":
                    recommendations.append("Improve navigation consistency across all pages")
                elif suite_name == "responsive_design":
                    recommendations.append("Enhance responsive design for better mobile experience")
                elif suite_name == "interactive_elements":
                    recommendations.append("Add more interactive elements and JavaScript functionality")
                elif suite_name == "error_handling":
                    recommendations.append("Improve error handling and user feedback mechanisms")
        
        self.test_results["recommendations"] = recommendations
    
    def generate_final_report(self):
        """Generate final comprehensive report"""
        overall_score, overall_status = self.calculate_overall_score()
        self.generate_recommendations()
        
        # Save JSON report
        json_report_path = "comprehensive_dashboard_validation_report.json"
        with open(json_report_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        # Generate markdown summary
        md_report_path = "comprehensive_dashboard_validation_summary.md"
        with open(md_report_path, 'w', encoding='utf-8') as f:
            f.write("# Comprehensive Dashboard Validation Report\\n\\n")
            f.write(f"**Generated:** {self.test_results['timestamp']}\\n")
            f.write(f"**Overall Score:** {overall_score:.1f}%\\n")
            f.write(f"**Overall Status:** {overall_status}\\n\\n")
            
            # Summary
            summary = self.test_results["overall_summary"]
            f.write("## Test Suite Summary\\n\\n")
            f.write(f"- **Total Test Suites:** {summary['total_suites']}\\n")
            f.write(f"- **Passed:** {summary['passed_suites']}\\n")
            f.write(f"- **Warnings:** {summary['warning_suites']}\\n")
            f.write(f"- **Failed:** {summary['failed_suites']}\\n\\n")
            
            # Individual test results
            f.write("## Individual Test Results\\n\\n")
            for suite_name, suite_data in self.test_results["test_suites"].items():
                status = suite_data.get("status", "ERROR")
                score = suite_data.get("score", "N/A")
                
                f.write(f"### {suite_name.replace('_', ' ').title()}\\n")
                f.write(f"**Status:** {status}\\n")
                if isinstance(score, (int, float)):
                    f.write(f"**Score:** {score:.1f}%\\n")
                f.write("\\n")
            
            # Recommendations
            if self.test_results["recommendations"]:
                f.write("## Recommendations\\n\\n")
                for i, rec in enumerate(self.test_results["recommendations"], 1):
                    f.write(f"{i}. {rec}\\n")
                f.write("\\n")
            
            # Requirements coverage
            f.write("## Requirements Coverage\\n\\n")
            f.write("This validation covers the following requirements:\\n")
            f.write("- **1.1, 1.2, 1.3, 1.4:** Consistent modern styling and layout\\n")
            f.write("- **8.1, 8.2, 8.3, 8.4, 8.5:** Interactive elements and error handling\\n")
            f.write("- **7.1, 7.2, 7.3, 7.4, 7.5:** Navigation flow and consistency\\n\\n")
        
        print(f"\\nComprehensive validation report saved to: {json_report_path}")
        print(f"Summary report saved to: {md_report_path}")
        
        return overall_score, overall_status
    
    def run_all_validations(self):
        """Run all validation tests"""
        print("STARTING COMPREHENSIVE DASHBOARD VALIDATION")
        print("=" * 80)
        
        # Run all test suites
        html_result = self.run_html_structure_validation()
        nav_result = self.run_navigation_flow_test()
        responsive_result = self.check_responsive_design_manually()
        interactive_result = self.check_interactive_elements_manually()
        error_result = self.check_error_handling_manually()
        
        # Generate final report
        overall_score, overall_status = self.generate_final_report()
        
        print("\\n" + "=" * 80)
        print("COMPREHENSIVE VALIDATION COMPLETE")
        print("=" * 80)
        print(f"Overall Score: {overall_score:.1f}%")
        print(f"Overall Status: {overall_status}")
        
        if overall_status == "PASS":
            print("\\nPASS - All dashboard validation tests passed!")
            return 0
        elif overall_status == "WARNING":
            print("\\nWARNING - Dashboard validation passed with warnings")
            return 1
        else:
            print("\\nFAIL - Dashboard validation failed")
            return 2

def main():
    """Main execution function"""
    validator = ComprehensiveDashboardValidator()
    return validator.run_all_validations()

if __name__ == "__main__":
    sys.exit(main())