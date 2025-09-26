#!/usr/bin/env python3
"""
Test Enhanced Settings Page Structure
Tests the HTML structure and JavaScript integration of the enhanced settings page
"""

import os
import re
import json

def test_html_structure():
    """Test the HTML structure of the enhanced settings page"""
    print("Testing HTML structure...")
    
    settings_path = os.path.join("admin-dashboard", "frontend", "settings.html")
    
    if not os.path.exists(settings_path):
        print("✗ Settings HTML file not found")
        return False
    
    with open(settings_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Test modern dashboard CSS inclusion
    if 'modern-dashboard.css' not in html_content:
        print("✗ Modern dashboard CSS not included")
        return False
    print("✓ Modern dashboard CSS is included")
    
    # Test enhanced search functionality
    if 'settings-actions' not in html_content:
        print("✗ Enhanced settings actions not found")
        return False
    print("✓ Enhanced settings actions are present")
    
    # Test import/export buttons
    if 'btn-import-settings' not in html_content or 'btn-export-settings' not in html_content:
        print("✗ Import/Export buttons not found")
        return False
    print("✓ Import/Export buttons are present")
    
    # Test enhanced modals
    required_modals = ['backup-modal', 'restore-modal', 'reset-modal', 'import-modal']
    for modal in required_modals:
        if modal not in html_content:
            print(f"✗ Modal {modal} not found")
            return False
    print("✓ All required modals are present")
    
    # Test enhanced styling
    if 'system-management-card' not in html_content:
        print("✗ Enhanced card styling not found")
        return False
    print("✓ Enhanced card styling is present")
    
    # Test confirmation checkboxes
    if 'confirm-reset-checkbox' not in html_content:
        print("✗ Reset confirmation checkbox not found")
        return False
    print("✓ Reset confirmation checkbox is present")
    
    return True

def test_javascript_structure():
    """Test the JavaScript structure and functionality"""
    print("Testing JavaScript structure...")
    
    js_path = os.path.join("admin-dashboard", "frontend", "js", "settings.js")
    
    if not os.path.exists(js_path):
        print("✗ Settings JavaScript file not found")
        return False
    
    with open(js_path, 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    # Test enhanced DOM elements
    required_elements = [
        'importSettingsBtn',
        'exportSettingsCardBtn', 
        'importSettingsCardBtn',
        'confirmImportBtn',
        'settingsFileInput',
        'mergeSettingsCheckbox',
        'confirmResetCheckbox'
    ]
    
    for element in required_elements:
        if element not in js_content:
            print(f"✗ DOM element {element} not found in JavaScript")
            return False
    print("✓ All enhanced DOM elements are present")
    
    # Test enhanced functions
    required_functions = [
        'performImport',
        'showLoadingState',
        'showSuccessFeedback',
        'resetButtonState',
        'setupRealTimeValidation',
        'setupKeyboardShortcuts',
        'highlightSearchTerm',
        'clearSearchHighlights'
    ]
    
    for function in required_functions:
        if f'function {function}' not in js_content:
            print(f"✗ Function {function} not found in JavaScript")
            return False
    print("✓ All enhanced functions are present")
    
    # Test validation enhancements
    if 'addValidationError' not in js_content or 'clearValidationErrors' not in js_content:
        print("✗ Enhanced validation functions not found")
        return False
    print("✓ Enhanced validation functions are present")
    
    # Test search enhancements
    if 'search-highlight' not in js_content:
        print("✗ Search highlighting functionality not found")
        return False
    print("✓ Search highlighting functionality is present")
    
    return True

def test_css_enhancements():
    """Test the CSS enhancements in the HTML file"""
    print("Testing CSS enhancements...")
    
    settings_path = os.path.join("admin-dashboard", "frontend", "settings.html")
    
    with open(settings_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Extract CSS from style tag
    style_match = re.search(r'<style>(.*?)</style>', html_content, re.DOTALL)
    if not style_match:
        print("✗ No style tag found")
        return False
    
    css_content = style_match.group(1)
    
    # Test enhanced styling classes
    required_styles = [
        '.settings-actions',
        '.settings-quick-actions',
        '.nav-tabs .nav-link:hover',
        '.system-management-card',
        '.loading-overlay',
        '.search-highlight'
    ]
    
    for style in required_styles:
        if style not in css_content:
            print(f"✗ CSS style {style} not found")
            return False
    print("✓ All enhanced CSS styles are present")
    
    # Test responsive design
    if '@media (max-width: 768px)' not in css_content:
        print("✗ Responsive design styles not found")
        return False
    print("✓ Responsive design styles are present")
    
    return True

def test_form_enhancements():
    """Test form enhancements and validation"""
    print("Testing form enhancements...")
    
    settings_path = os.path.join("admin-dashboard", "frontend", "settings.html")
    
    with open(settings_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Test enhanced form structure
    if 'form-check-input' not in html_content:
        print("✗ Enhanced form inputs not found")
        return False
    print("✓ Enhanced form inputs are present")
    
    # Test validation classes in CSS
    style_match = re.search(r'<style>(.*?)</style>', html_content, re.DOTALL)
    if style_match:
        css_content = style_match.group(1)
        if '.form-control:focus' not in css_content:
            print("✗ Enhanced form focus styles not found")
            return False
        print("✓ Enhanced form focus styles are present")
    
    return True

def run_all_tests():
    """Run all enhancement tests"""
    print("Starting Settings Page Enhancement Structure Tests")
    print("=" * 60)
    
    tests = [
        test_html_structure,
        test_javascript_structure,
        test_css_enhancements,
        test_form_enhancements
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"\n--- {test.__name__} ---")
        if test():
            passed += 1
            print(f"✓ {test.__name__} PASSED")
        else:
            failed += 1
            print(f"✗ {test.__name__} FAILED")
    
    print("\n" + "=" * 60)
    print(f"Settings Page Enhancement Structure Test Results:")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All settings page enhancement structure tests passed!")
        return True
    else:
        print(f"\n❌ {failed} test(s) failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)