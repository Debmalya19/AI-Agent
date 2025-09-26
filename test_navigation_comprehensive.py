#!/usr/bin/env python3
"""
Comprehensive Navigation Flow Test

Tests navigation flow between all dashboard pages and validates
navigation consistency according to requirements 7.1, 7.2, 7.3, 7.4, 7.5, 1.2
"""

import os
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin, urlparse

class NavigationFlowTester:
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
            "navigation_analysis": {},
            "consistency_check": {},
            "link_validation": {},
            "breadcrumb_analysis": {},
            "overall_score": 0
        }
    
    def extract_navigation_links(self, page_path, page_name):
        """Extract all navigation links from a page"""
        try:
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            navigation_data = {
                "sidebar_links": [],
                "navbar_links": [],
                "breadcrumb_links": [],
                "all_links": [],
                "active_elements": [],
                "page_title": "",
                "has_sidebar": False,
                "has_navbar": False,
                "has_breadcrumbs": False
            }
            
            # Get page title
            title_tag = soup.find('title')
            if title_tag:
                navigation_data["page_title"] = title_tag.get_text().strip()
            
            # Check for sidebar
            sidebar = soup.find(class_=lambda x: x and any(cls in x.lower() for cls in ['sidebar', 'nav-sidebar']))
            if sidebar:
                navigation_data["has_sidebar"] = True
                sidebar_links = sidebar.find_all('a')
                for link in sidebar_links:
                    href = link.get('href', '')
                    text = link.get_text().strip()
                    classes = link.get('class', [])
                    navigation_data["sidebar_links"].append({
                        "href": href,
                        "text": text,
                        "classes": classes,
                        "is_active": 'active' in classes
                    })
            
            # Check for navbar
            navbar = soup.find(class_=lambda x: x and 'navbar' in x.lower())
            if navbar:
                navigation_data["has_navbar"] = True
                navbar_links = navbar.find_all('a')
                for link in navbar_links:
                    href = link.get('href', '')
                    text = link.get_text().strip()
                    classes = link.get('class', [])
                    navigation_data["navbar_links"].append({
                        "href": href,
                        "text": text,
                        "classes": classes,
                        "is_active": 'active' in classes
                    })
            
            # Check for breadcrumbs
            breadcrumb = soup.find(class_=lambda x: x and 'breadcrumb' in x.lower())
            if breadcrumb:
                navigation_data["has_breadcrumbs"] = True
                breadcrumb_links = breadcrumb.find_all('a')
                for link in breadcrumb_links:
                    href = link.get('href', '')
                    text = link.get_text().strip()
                    navigation_data["breadcrumb_links"].append({
                        "href": href,
                        "text": text
                    })
            
            # Get all links
            all_links = soup.find_all('a')
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text().strip()
                classes = link.get('class', [])
                if href:  # Only include links with href
                    navigation_data["all_links"].append({
                        "href": href,
                        "text": text,
                        "classes": classes
                    })
            
            # Find active elements
            active_elements = soup.find_all(class_=lambda x: x and 'active' in x)
            for element in active_elements:
                navigation_data["active_elements"].append({
                    "tag": element.name,
                    "classes": element.get('class', []),
                    "text": element.get_text().strip()[:50]  # First 50 chars
                })
            
            return navigation_data
            
        except Exception as e:
            return {"error": str(e)}
    
    def validate_link_targets(self):
        """Validate that navigation links point to existing pages"""
        print("Validating navigation link targets...")
        
        all_links = {}
        broken_links = {}
        
        for page in self.pages:
            page_path = os.path.join(self.admin_dashboard_path, page)
            nav_data = self.extract_navigation_links(page_path, page)
            
            if "error" not in nav_data:
                page_links = []
                
                # Collect all navigation links
                for link_group in [nav_data["sidebar_links"], nav_data["navbar_links"], nav_data["breadcrumb_links"]]:
                    for link in link_group:
                        href = link["href"]
                        if href and not href.startswith(('http', 'mailto:', 'tel:', '#')):
                            page_links.append(href)
                
                all_links[page] = page_links
                broken_links[page] = []
                
                # Check if linked files exist
                for href in page_links:
                    # Handle relative paths
                    if href.startswith('./'):
                        href = href[2:]
                    elif href.startswith('../'):
                        continue  # Skip parent directory links for now
                    
                    target_path = os.path.join(self.admin_dashboard_path, href)
                    if not os.path.exists(target_path):
                        broken_links[page].append(href)
        
        self.results["link_validation"] = {
            "all_links": all_links,
            "broken_links": broken_links,
            "total_links": sum(len(links) for links in all_links.values()),
            "total_broken": sum(len(broken) for broken in broken_links.values())
        }
    
    def analyze_navigation_consistency(self):
        """Analyze navigation consistency across all pages"""
        print("Analyzing navigation consistency...")
        
        navigation_structures = {}
        
        for page in self.pages:
            page_path = os.path.join(self.admin_dashboard_path, page)
            nav_data = self.extract_navigation_links(page_path, page)
            navigation_structures[page] = nav_data
        
        # Analyze consistency
        consistency_analysis = {
            "sidebar_consistency": {},
            "navbar_consistency": {},
            "breadcrumb_consistency": {},
            "title_consistency": {},
            "active_state_analysis": {}
        }
        
        # Check sidebar consistency
        pages_with_sidebar = [page for page, data in navigation_structures.items() 
                             if data.get("has_sidebar", False)]
        
        consistency_analysis["sidebar_consistency"] = {
            "pages_with_sidebar": pages_with_sidebar,
            "consistency_score": (len(pages_with_sidebar) / len(self.pages)) * 100
        }
        
        # Check navbar consistency
        pages_with_navbar = [page for page, data in navigation_structures.items() 
                            if data.get("has_navbar", False)]
        
        consistency_analysis["navbar_consistency"] = {
            "pages_with_navbar": pages_with_navbar,
            "consistency_score": (len(pages_with_navbar) / len(self.pages)) * 100
        }
        
        # Check breadcrumb consistency
        pages_with_breadcrumbs = [page for page, data in navigation_structures.items() 
                                 if data.get("has_breadcrumbs", False)]
        
        consistency_analysis["breadcrumb_consistency"] = {
            "pages_with_breadcrumbs": pages_with_breadcrumbs,
            "consistency_score": (len(pages_with_breadcrumbs) / len(self.pages)) * 100
        }
        
        # Check title consistency
        page_titles = {}
        for page, data in navigation_structures.items():
            title = data.get("page_title", "")
            page_titles[page] = title
        
        pages_with_titles = [page for page, title in page_titles.items() if title]
        consistency_analysis["title_consistency"] = {
            "page_titles": page_titles,
            "pages_with_titles": pages_with_titles,
            "consistency_score": (len(pages_with_titles) / len(self.pages)) * 100
        }
        
        # Analyze active states
        active_state_analysis = {}
        for page, data in navigation_structures.items():
            active_count = len(data.get("active_elements", []))
            has_active_nav = any(link.get("is_active", False) for link in data.get("sidebar_links", []))
            active_state_analysis[page] = {
                "active_element_count": active_count,
                "has_active_navigation": has_active_nav
            }
        
        consistency_analysis["active_state_analysis"] = active_state_analysis
        
        self.results["navigation_analysis"] = navigation_structures
        self.results["consistency_check"] = consistency_analysis
    
    def analyze_breadcrumb_structure(self):
        """Analyze breadcrumb structure and hierarchy"""
        print("Analyzing breadcrumb structure...")
        
        breadcrumb_analysis = {}
        
        for page in self.pages:
            page_path = os.path.join(self.admin_dashboard_path, page)
            nav_data = self.extract_navigation_links(page_path, page)
            
            if nav_data.get("has_breadcrumbs", False):
                breadcrumb_links = nav_data.get("breadcrumb_links", [])
                breadcrumb_analysis[page] = {
                    "has_breadcrumbs": True,
                    "breadcrumb_count": len(breadcrumb_links),
                    "breadcrumb_items": breadcrumb_links,
                    "proper_hierarchy": len(breadcrumb_links) >= 2  # At least Home > Current
                }
            else:
                breadcrumb_analysis[page] = {
                    "has_breadcrumbs": False,
                    "breadcrumb_count": 0,
                    "breadcrumb_items": [],
                    "proper_hierarchy": False
                }
        
        self.results["breadcrumb_analysis"] = breadcrumb_analysis
    
    def calculate_overall_score(self):
        """Calculate overall navigation score"""
        scores = []
        
        # Sidebar consistency score
        sidebar_score = self.results["consistency_check"]["sidebar_consistency"]["consistency_score"]
        scores.append(sidebar_score)
        
        # Navbar consistency score
        navbar_score = self.results["consistency_check"]["navbar_consistency"]["consistency_score"]
        scores.append(navbar_score)
        
        # Title consistency score
        title_score = self.results["consistency_check"]["title_consistency"]["consistency_score"]
        scores.append(title_score)
        
        # Link validation score
        total_links = self.results["link_validation"]["total_links"]
        broken_links = self.results["link_validation"]["total_broken"]
        
        if total_links > 0:
            link_score = ((total_links - broken_links) / total_links) * 100
            scores.append(link_score)
        
        # Active state score
        pages_with_active = sum(1 for data in self.results["consistency_check"]["active_state_analysis"].values() 
                               if data["has_active_navigation"])
        active_score = (pages_with_active / len(self.pages)) * 100
        scores.append(active_score)
        
        # Calculate final score
        if scores:
            self.results["overall_score"] = sum(scores) / len(scores)
        else:
            self.results["overall_score"] = 0
    
    def run_all_tests(self):
        """Run all navigation tests"""
        print("Starting comprehensive navigation flow tests...")
        
        self.analyze_navigation_consistency()
        self.validate_link_targets()
        self.analyze_breadcrumb_structure()
        self.calculate_overall_score()
        
        return True
    
    def generate_report(self):
        """Generate navigation test report"""
        # JSON report
        json_report_path = "navigation_flow_test_report.json"
        with open(json_report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Markdown summary
        md_report_path = "navigation_flow_test_summary.md"
        with open(md_report_path, 'w', encoding='utf-8') as f:
            f.write("# Navigation Flow Test Report\n\n")
            f.write(f"**Generated:** {self.results['timestamp']}\n")
            f.write(f"**Overall Score:** {self.results['overall_score']:.1f}%\n\n")
            
            # Consistency Results
            f.write("## Navigation Consistency Results\n\n")
            
            consistency = self.results["consistency_check"]
            
            f.write(f"**Sidebar Consistency:** {consistency['sidebar_consistency']['consistency_score']:.1f}%\n")
            f.write(f"- Pages with sidebar: {len(consistency['sidebar_consistency']['pages_with_sidebar'])}/{len(self.pages)}\n\n")
            
            f.write(f"**Navbar Consistency:** {consistency['navbar_consistency']['consistency_score']:.1f}%\n")
            f.write(f"- Pages with navbar: {len(consistency['navbar_consistency']['pages_with_navbar'])}/{len(self.pages)}\n\n")
            
            f.write(f"**Title Consistency:** {consistency['title_consistency']['consistency_score']:.1f}%\n")
            f.write(f"- Pages with titles: {len(consistency['title_consistency']['pages_with_titles'])}/{len(self.pages)}\n\n")
            
            # Link Validation Results
            f.write("## Link Validation Results\n\n")
            link_validation = self.results["link_validation"]
            f.write(f"**Total Links:** {link_validation['total_links']}\n")
            f.write(f"**Broken Links:** {link_validation['total_broken']}\n")
            
            if link_validation['total_broken'] > 0:
                f.write("\n**Broken Links by Page:**\n")
                for page, broken in link_validation['broken_links'].items():
                    if broken:
                        f.write(f"- **{page}**: {', '.join(broken)}\n")
            f.write("\n")
            
            # Breadcrumb Analysis
            f.write("## Breadcrumb Analysis\n\n")
            breadcrumb_data = self.results["breadcrumb_analysis"]
            pages_with_breadcrumbs = sum(1 for data in breadcrumb_data.values() if data["has_breadcrumbs"])
            f.write(f"**Pages with Breadcrumbs:** {pages_with_breadcrumbs}/{len(self.pages)}\n\n")
            
            for page, data in breadcrumb_data.items():
                if data["has_breadcrumbs"]:
                    f.write(f"- **{page}**: {data['breadcrumb_count']} items\n")
            f.write("\n")
            
            # Active State Analysis
            f.write("## Active State Analysis\n\n")
            active_analysis = consistency["active_state_analysis"]
            for page, data in active_analysis.items():
                status = "PASS" if data["has_active_navigation"] else "FAIL"
                f.write(f"- **{page}**: {status} Active navigation state\n")
            f.write("\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            
            if consistency['sidebar_consistency']['consistency_score'] < 100:
                missing_sidebar = set(self.pages) - set(consistency['sidebar_consistency']['pages_with_sidebar'])
                f.write("**Sidebar Issues:**\n")
                for page in missing_sidebar:
                    f.write(f"- {page} should include sidebar navigation\n")
                f.write("\n")
            
            if link_validation['total_broken'] > 0:
                f.write("**Link Issues:**\n")
                f.write("- Fix broken navigation links\n")
                f.write("- Ensure all navigation targets exist\n\n")
            
            if pages_with_breadcrumbs < len(self.pages):
                f.write("**Breadcrumb Issues:**\n")
                f.write("- Add breadcrumb navigation to all pages\n")
                f.write("- Ensure proper hierarchy in breadcrumbs\n\n")
        
        print(f"Navigation test report saved to: {json_report_path}")
        print(f"Summary report saved to: {md_report_path}")
        
        return self.results["overall_score"]

def main():
    """Main execution function"""
    tester = NavigationFlowTester()
    
    print("=" * 50)
    print("NAVIGATION FLOW COMPREHENSIVE TEST")
    print("=" * 50)
    
    success = tester.run_all_tests()
    
    if success:
        score = tester.generate_report()
        print(f"\nNavigation testing completed with overall score: {score:.1f}%")
        
        if score >= 80:
            print("PASS - Navigation flow test PASSED")
            return 0
        elif score >= 60:
            print("WARNING - Navigation flow test passed with warnings")
            return 1
        else:
            print("FAIL - Navigation flow test FAILED")
            return 2
    else:
        print("❌ Navigation testing could not be completed")
        return 3

if __name__ == "__main__":
    exit(main())