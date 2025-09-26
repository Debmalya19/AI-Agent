#!/usr/bin/env python3
"""
Test UI Feedback Implementation
Tests the consistent loading states and error handling implementation
"""

import os
import sys
import json
import time
from pathlib import Path

def test_css_loading_states():
    """Test that CSS includes loading states and error handling styles"""
    css_path = Path("admin-dashboard/frontend/css/modern-dashboard.css")
    
    if not css_path.exists():
        return False, "CSS file not found"
    
    css_content = css_path.read_text()
    
    # Check for loading spinner styles
    required_css_classes = [
        '.loading-spinner',
        '.loading-overlay',
        '.skeleton',
        '.toast-container',
        '.alert-success',
        '.alert-danger',
        '.alert-warning',
        '.alert-info',
        '.btn.loading',
        '.empty-state',
        '.progress-bar'
    ]
    
    missing_classes = []
    for css_class in required_css_classes:
        if css_class not in css_content:
            missing_classes.append(css_class)
    
    if missing_classes:
        return False, f"Missing CSS classes: {', '.join(missing_classes)}"
    
    return True, "All required CSS classes found"

def test_ui_feedback_js():
    """Test that UI feedback JavaScript file exists and has required methods"""
    js_path = Path("admin-dashboard/frontend/js/ui-feedback.js")
    
    if not js_path.exists():
        return False, "UI feedback JavaScript file not found"
    
    js_content = js_path.read_text()
    
    # Check for required methods
    required_methods = [
        'showLoading',
        'hideLoading',
        'showButtonLoading',
        'hideButtonLoading',
        'showTableSkeleton',
        'showSuccess',
        'showError',
        'showWarning',
        'showInfo',
        'showToast',
        'showAlert',
        'showEmptyState',
        'handleApiRequest',
        'handleFormSubmit'
    ]
    
    missing_methods = []
    for method in required_methods:
        if f'{method}(' not in js_content:
            missing_methods.append(method)
    
    if missing_methods:
        return False, f"Missing JavaScript methods: {', '.join(missing_methods)}"
    
    return True, "All required JavaScript methods found"

def test_html_includes():
    """Test that HTML files include the UI feedback script"""
    html_files = [
        "admin-dashboard/frontend/index.html",
        "admin-dashboard/frontend/tickets.html",
        "admin-dashboard/frontend/users.html",
        "admin-dashboard/frontend/integration.html",
        "admin-dashboard/frontend/settings.html",
        "admin-dashboard/frontend/logs.html"
    ]
    
    missing_includes = []
    
    for html_file in html_files:
        html_path = Path(html_file)
        if not html_path.exists():
            missing_includes.append(f"{html_file} - file not found")
            continue
        
        html_content = html_path.read_text()
        if 'ui-feedback.js' not in html_content:
            missing_includes.append(f"{html_file} - missing ui-feedback.js include")
    
    if missing_includes:
        return False, f"Missing UI feedback includes: {', '.join(missing_includes)}"
    
    return True, "All HTML files include UI feedback script"

def test_js_integration():
    """Test that JavaScript files use the UI feedback system"""
    js_files = [
        ("admin-dashboard/frontend/js/tickets.js", ["uiFeedback.showTableSkeleton", "uiFeedback.handleApiRequest"]),
        ("admin-dashboard/frontend/js/users.js", ["uiFeedback.showTableSkeleton", "uiFeedback.handleApiRequest"]),
        ("admin-dashboard/frontend/js/integration.js", ["uiFeedback.handleApiRequest", "uiFeedback.showButtonLoading"])
    ]
    
    integration_issues = []
    
    for js_file, required_calls in js_files:
        js_path = Path(js_file)
        if not js_path.exists():
            integration_issues.append(f"{js_file} - file not found")
            continue
        
        js_content = js_path.read_text()
        
        for required_call in required_calls:
            if required_call not in js_content:
                integration_issues.append(f"{js_file} - missing {required_call}")
    
    if integration_issues:
        return False, f"JavaScript integration issues: {', '.join(integration_issues)}"
    
    return True, "JavaScript files properly integrated with UI feedback system"

def test_hover_effects():
    """Test that CSS includes hover effects for interactive elements"""
    css_path = Path("admin-dashboard/frontend/css/modern-dashboard.css")
    
    if not css_path.exists():
        return False, "CSS file not found"
    
    css_content = css_path.read_text()
    
    # Check for hover effects
    hover_selectors = [
        '.btn:hover',
        '.card:hover',
        '.table tbody tr:hover',
        '.form-control:focus',
        '.form-select:focus'
    ]
    
    missing_hover = []
    for selector in hover_selectors:
        if selector not in css_content:
            missing_hover.append(selector)
    
    if missing_hover:
        return False, f"Missing hover effects: {', '.join(missing_hover)}"
    
    return True, "All required hover effects found"

def test_animation_keyframes():
    """Test that CSS includes animation keyframes"""
    css_path = Path("admin-dashboard/frontend/css/modern-dashboard.css")
    
    if not css_path.exists():
        return False, "CSS file not found"
    
    css_content = css_path.read_text()
    
    # Check for animation keyframes
    required_animations = [
        '@keyframes spin',
        '@keyframes loading',
        '@keyframes slideInDown',
        '@keyframes fadeIn'
    ]
    
    missing_animations = []
    for animation in required_animations:
        if animation not in css_content:
            missing_animations.append(animation)
    
    if missing_animations:
        return False, f"Missing animations: {', '.join(missing_animations)}"
    
    return True, "All required animations found"

def run_all_tests():
    """Run all tests and return results"""
    tests = [
        ("CSS Loading States", test_css_loading_states),
        ("UI Feedback JavaScript", test_ui_feedback_js),
        ("HTML Includes", test_html_includes),
        ("JavaScript Integration", test_js_integration),
        ("Hover Effects", test_hover_effects),
        ("Animation Keyframes", test_animation_keyframes)
    ]
    
    results = []
    all_passed = True
    
    print("Testing UI Feedback Implementation...")
    print("=" * 50)
    
    for test_name, test_func in tests:
        try:
            success, message = test_func()
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}: {message}")
            
            results.append({
                "test": test_name,
                "success": success,
                "message": message
            })
            
            if not success:
                all_passed = False
                
        except Exception as e:
            print(f"❌ FAIL {test_name}: Exception - {str(e)}")
            results.append({
                "test": test_name,
                "success": False,
                "message": f"Exception: {str(e)}"
            })
            all_passed = False
    
    print("=" * 50)
    print(f"Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return results, all_passed

if __name__ == "__main__":
    results, success = run_all_tests()
    
    # Save results to JSON file
    results_file = Path("ui_feedback_test_results.json")
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": time.time(),
            "overall_success": success,
            "test_results": results
        }, f, indent=2)
    
    print(f"\nTest results saved to: {results_file}")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)