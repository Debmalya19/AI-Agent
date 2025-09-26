#!/usr/bin/env python3
"""
HTML Structure and CSS Validation Test

This test validates HTML structure and CSS consistency without requiring browser automation.
Focuses on static analysis of HTML files and CSS references.
"""

import os
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime

class HTMLStructureValidator:
    def __init__(self):
        self.admin_dashboard_path = "admin-dashboard/frontend"
        self.pages = [
            "index.html",
            "tickets.html", 
            "users.html",
            "integration.html",
            "settings.html",
            "logs.html"
        ]
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "pages": {},
            "consistency_check": {},
            "overall_score": 0
        }
    
    def validate_html_structure(self, page_path, page_name):
        """Validate HTML structure for a single page"""
        try:
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            validation = {
                "file_exists": True,
                "valid_doctype": content.strip().startswith('<!DOCTYPE'),
                "has_html_tag": soup.find('html') is not None,
                "has_head_tag": soup.find('head') is not None,
                "has_body_tag": soup.find('body') is not None,
                "has_title": soup.find('title') is not None,
                "title_text": soup.find('title').get_text() if soup.find('title') else "",
                "css_files": [],
                "js_files": [],
                "common_elements": {},
                "bootstrap_usage": False,
                "modern_css_usage": False
            }
            
            # Check CSS files
            css_links = soup.find_all('link', rel='stylesheet')
            for link in css_links:
                href = link.get('href', '')
                validation["css_files"].append(href)
                if 'modern-dashboard.css' in href:
                    validation["modern_css_usage"] = True
                if 'bootstrap' in href.lower():
                    validation["bootstrap_usage"] = True
            
            # Check JS files
            js_scripts = soup.find_all('script', src=True)
            for script in js_scripts:
                src = script.get('src', '')
                validation["js_files"].append(src)
            
            # Check for common dashboard elements
            common_classes = [
                'sidebar', 'navbar', 'main-content', 'content-header',
                'breadcrumb', 'card', 'table', 'btn', 'form-control'
            ]
            
            for class_name in common_classes:
                elements = soup.find_all(class_=lambda x: x and class_name in x.split())
                validation["common_elements"][class_name] = len(elements)
            
            # Calculate structure score
            structure_checks = [
                validation["valid_doctype"],
                validation["has_html_tag"],
                validation["has_head_tag"],
                validation["has_body_tag"],
                validation["has_title"],
                validation["modern_css_usage"],
                len(validation["common_elements"]) > 0
            ]
            
            validation["structure_score"] = (sum(structure_checks) / len(structure_checks)) * 100
            
            return validation
            
        except FileNotFoundError:
            return {
                "file_exists": False,
                "error": f"File not found: {page_path}",
                "structure_score": 0
            }
        except Exception as e:
            return {
                "file_exists": True,
                "error": str(e),
                "structure_score": 0
            }
    
    def check_css_consistency(self):
        """Check CSS consistency across all pages"""
        css_usage = {}
        js_usage = {}
        
        for page_name, page_data in self.results["pages"].items():
            if "css_files" in page_data:
                for css_file in page_data["css_files"]:
                    if css_file not in css_usage:
                        css_usage[css_file] = []
                    css_usage[css_file].append(page_name)
            
            if "js_files" in page_data:
                for js_file in page_data["js_files"]:
                    if js_file not in js_usage:
                        js_usage[js_file] = []
                    js_usage[js_file].append(page_name)
        
        # Check for modern-dashboard.css usage
        modern_css_pages = []
        for page_name, page_data in self.results["pages"].items():
            if page_data.get("modern_css_usage", False):
                modern_css_pages.append(page_name)
        
        consistency_score = (len(modern_css_pages) / len(self.pages)) * 100
        
        self.results["consistency_check"] = {
            "css_files": css_usage,
            "js_files": js_usage,
            "modern_css_pages": modern_css_pages,
            "modern_css_consistency": consistency_score,
            "total_pages": len(self.pages),
            "pages_with_modern_css": len(modern_css_pages)
        }
    
    def validate_all_pages(self):
        """Validate all dashboard pages"""
        print("Validating HTML structure for all pages...")
        
        for page in self.pages:
            page_path = os.path.join(self.admin_dashboard_path, page)
            print(f"Validating {page}...")
            
            validation_result = self.validate_html_structure(page_path, page)
            self.results["pages"][page] = validation_result
        
        # Check consistency across pages
        self.check_css_consistency()
        
        # Calculate overall score
        page_scores = []
        for page_data in self.results["pages"].values():
            if "structure_score" in page_data:
                page_scores.append(page_data["structure_score"])
        
        if page_scores:
            avg_structure_score = sum(page_scores) / len(page_scores)
            consistency_score = self.results["consistency_check"]["modern_css_consistency"]
            self.results["overall_score"] = (avg_structure_score + consistency_score) / 2
        else:
            self.results["overall_score"] = 0
    
    def generate_report(self):
        """Generate validation report"""
        # JSON report
        json_report_path = "html_structure_validation_report.json"
        with open(json_report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Markdown summary
        md_report_path = "html_structure_validation_summary.md"
        with open(md_report_path, 'w', encoding='utf-8') as f:
            f.write("# HTML Structure Validation Report\n\n")
            f.write(f"**Generated:** {self.results['timestamp']}\n")
            f.write(f"**Overall Score:** {self.results['overall_score']:.1f}%\n\n")
            
            # Individual page results
            f.write("## Page Validation Results\n\n")
            for page, data in self.results["pages"].items():
                if data.get("file_exists", False):
                    score = data.get("structure_score", 0)
                    status = "PASS" if score >= 80 else "WARNING" if score >= 60 else "FAIL"
                    f.write(f"### {page} - {status} ({score:.1f}%)\n\n")
                    
                    f.write("**Structure Checks:**\n")
                    f.write(f"- Valid DOCTYPE: {'PASS' if data.get('valid_doctype') else 'FAIL'}\n")
                    f.write(f"- HTML tag: {'PASS' if data.get('has_html_tag') else 'FAIL'}\n")
                    f.write(f"- Head tag: {'PASS' if data.get('has_head_tag') else 'FAIL'}\n")
                    f.write(f"- Body tag: {'PASS' if data.get('has_body_tag') else 'FAIL'}\n")
                    f.write(f"- Title tag: {'PASS' if data.get('has_title') else 'FAIL'}\n")
                    f.write(f"- Modern CSS: {'PASS' if data.get('modern_css_usage') else 'FAIL'}\n")
                    f.write(f"- Bootstrap: {'PASS' if data.get('bootstrap_usage') else 'FAIL'}\n\n")
                    
                    if data.get("title_text"):
                        f.write(f"**Page Title:** {data['title_text']}\n\n")
                    
                    # Common elements
                    if data.get("common_elements"):
                        f.write("**Dashboard Elements Found:**\n")
                        for element, count in data["common_elements"].items():
                            if count > 0:
                                f.write(f"- {element}: {count}\n")
                        f.write("\n")
                else:
                    f.write(f"### {page} - FAIL File Not Found\n\n")
            
            # Consistency results
            f.write("## CSS Consistency Analysis\n\n")
            consistency = self.results["consistency_check"]
            f.write(f"**Modern CSS Usage:** {consistency['pages_with_modern_css']}/{consistency['total_pages']} pages ({consistency['modern_css_consistency']:.1f}%)\n\n")
            
            if consistency["modern_css_pages"]:
                f.write("**Pages using modern-dashboard.css:**\n")
                for page in consistency["modern_css_pages"]:
                    f.write(f"- {page}\n")
                f.write("\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            if consistency['modern_css_consistency'] < 100:
                missing_pages = set(self.pages) - set(consistency["modern_css_pages"])
                f.write("**CSS Consistency Issues:**\n")
                for page in missing_pages:
                    f.write(f"- {page} should include modern-dashboard.css\n")
                f.write("\n")
            
            low_score_pages = []
            for page, data in self.results["pages"].items():
                if data.get("structure_score", 0) < 80:
                    low_score_pages.append(page)
            
            if low_score_pages:
                f.write("**Structure Issues:**\n")
                for page in low_score_pages:
                    f.write(f"- {page} needs structure improvements\n")
                f.write("\n")
        
        print(f"HTML validation report saved to: {json_report_path}")
        print(f"Summary report saved to: {md_report_path}")
        
        return self.results["overall_score"]

def main():
    """Main execution function"""
    validator = HTMLStructureValidator()
    
    print("=" * 50)
    print("HTML STRUCTURE VALIDATION")
    print("=" * 50)
    
    validator.validate_all_pages()
    score = validator.generate_report()
    
    print(f"\nValidation completed with overall score: {score:.1f}%")
    
    if score >= 80:
        print("PASS - HTML structure validation PASSED")
        return 0
    elif score >= 60:
        print("WARNING - HTML structure validation passed with warnings")
        return 1
    else:
        print("FAIL - HTML structure validation FAILED")
        return 2

if __name__ == "__main__":
    exit(main())