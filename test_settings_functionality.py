#!/usr/bin/env python3
"""
Test Settings Page Functionality
Tests the enhanced settings page with modern theme and new features
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def setup_driver():
    """Set up Chrome driver with appropriate options"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Failed to setup Chrome driver: {e}")
        return None

def test_settings_page_structure(driver):
    """Test the basic structure and modern theme application"""
    print("Testing settings page structure...")
    
    try:
        # Navigate to settings page
        settings_path = os.path.join(os.getcwd(), "ai-agent", "admin-dashboard", "frontend", "settings.html")
        driver.get(f"file://{settings_path}")
        
        # Wait for page to load
        WebDriverWait(driver, 10).wait(
            EC.presence_of_element_located((By.CLASS_NAME, "dashboard-container"))
        )
        
        # Check if modern dashboard CSS is loaded
        css_links = driver.find_elements(By.CSS_SELECTOR, 'link[href*="modern-dashboard.css"]')
        assert len(css_links) > 0, "Modern dashboard CSS not found"
        print("✓ Modern dashboard CSS is loaded")
        
        # Check sidebar structure
        sidebar = driver.find_element(By.CLASS_NAME, "sidebar")
        assert sidebar.is_displayed(), "Sidebar not visible"
        print("✓ Sidebar is visible")
        
        # Check navigation links including logs
        nav_links = driver.find_elements(By.CSS_SELECTOR, ".sidebar-nav a")
        link_texts = [link.text for link in nav_links]
        expected_links = ["Dashboard", "Support Tickets", "User Management", "Integration", "Settings", "System Logs"]
        
        for expected in expected_links:
            assert any(expected in text for text in link_texts), f"Navigation link '{expected}' not found"
        print("✓ All navigation links present including System Logs")
        
        # Check settings active state
        active_link = driver.find_element(By.CSS_SELECTOR, ".sidebar-nav .active a")
        assert "Settings" in active_link.text, "Settings link not marked as active"
        print("✓ Settings navigation is marked as active")
        
        return True
        
    except Exception as e:
        print(f"✗ Settings page structure test failed: {e}")
        return False

def test_settings_search_functionality(driver):
    """Test the settings search functionality"""
    print("Testing settings search functionality...")
    
    try:
        # Find search input
        search_input = driver.find_element(By.ID, "settings-search")
        assert search_input.is_displayed(), "Settings search input not visible"
        print("✓ Settings search input is visible")
        
        # Test search placeholder
        placeholder = search_input.get_attribute("placeholder")
        assert "Search settings" in placeholder, "Search placeholder not correct"
        print("✓ Search placeholder is correct")
        
        # Test search functionality (basic structure check)
        search_input.send_keys("theme")
        time.sleep(0.5)  # Allow for search processing
        
        # The search should be functional via JavaScript
        # We can't fully test the filtering without running JS, but we can verify the input works
        search_value = search_input.get_attribute("value")
        assert search_value == "theme", "Search input not accepting text"
        print("✓ Search input accepts text")
        
        return True
        
    except Exception as e:
        print(f"✗ Settings search test failed: {e}")
        return False

def test_settings_tabs_structure(driver):
    """Test the settings tabs structure and content"""
    print("Testing settings tabs structure...")
    
    try:
        # Check tabs container
        tabs_container = driver.find_element(By.ID, "settings-tabs")
        assert tabs_container.is_displayed(), "Settings tabs not visible"
        
        # Check all expected tabs
        expected_tabs = ["General", "Appearance", "Notifications", "Security", "Advanced"]
        tab_buttons = driver.find_elements(By.CSS_SELECTOR, "#settings-tabs .nav-link")
        
        tab_texts = [tab.text for tab in tab_buttons]
        for expected in expected_tabs:
            assert expected in tab_texts, f"Tab '{expected}' not found"
        print("✓ All expected tabs are present")
        
        # Check tab content panes
        tab_panes = driver.find_elements(By.CSS_SELECTOR, ".tab-pane")
        assert len(tab_panes) == 5, f"Expected 5 tab panes, found {len(tab_panes)}"
        print("✓ All tab content panes are present")
        
        # Check if General tab is active by default
        active_tab = driver.find_element(By.CSS_SELECTOR, "#settings-tabs .nav-link.active")
        assert "General" in active_tab.text, "General tab not active by default"
        print("✓ General tab is active by default")
        
        return True
        
    except Exception as e:
        print(f"✗ Settings tabs test failed: {e}")
        return False

def test_advanced_settings_management_cards(driver):
    """Test the enhanced advanced settings management cards"""
    print("Testing advanced settings management cards...")
    
    try:
        # Click on Advanced tab
        advanced_tab = driver.find_element(By.ID, "advanced-tab")
        advanced_tab.click()
        time.sleep(0.5)
        
        # Check for system management section
        management_cards = driver.find_elements(By.CSS_SELECTOR, "#advanced .card")
        assert len(management_cards) >= 4, f"Expected at least 4 management cards, found {len(management_cards)}"
        print("✓ System management cards are present")
        
        # Check for specific management buttons
        expected_buttons = [
            "btn-clear-cache",
            "btn-backup-now", 
            "btn-restore-backup",
            "btn-reset-settings",
            "btn-export-settings"
        ]
        
        for button_id in expected_buttons:
            button = driver.find_element(By.ID, button_id)
            assert button.is_displayed(), f"Button {button_id} not visible"
        print("✓ All management buttons are present and visible")
        
        return True
        
    except Exception as e:
        print(f"✗ Advanced settings management cards test failed: {e}")
        return False

def test_confirmation_modals_structure(driver):
    """Test the confirmation modals structure"""
    print("Testing confirmation modals structure...")
    
    try:
        # Check for modal elements in DOM
        expected_modals = [
            "backup-modal",
            "restore-modal", 
            "reset-modal"
        ]
        
        for modal_id in expected_modals:
            modal = driver.find_element(By.ID, modal_id)
            assert modal is not None, f"Modal {modal_id} not found in DOM"
        print("✓ All confirmation modals are present in DOM")
        
        # Check backup modal structure
        backup_modal = driver.find_element(By.ID, "backup-modal")
        backup_title = backup_modal.find_element(By.CSS_SELECTOR, ".modal-title")
        assert "Backup" in backup_title.text, "Backup modal title incorrect"
        
        # Check restore modal structure
        restore_modal = driver.find_element(By.ID, "restore-modal")
        restore_title = restore_modal.find_element(By.CSS_SELECTOR, ".modal-title")
        assert "Restore" in restore_title.text, "Restore modal title incorrect"
        
        # Check reset modal structure
        reset_modal = driver.find_element(By.ID, "reset-modal")
        reset_title = reset_modal.find_element(By.CSS_SELECTOR, ".modal-title")
        assert "Reset" in reset_title.text, "Reset modal title incorrect"
        
        print("✓ All modal structures are correct")
        
        return True
        
    except Exception as e:
        print(f"✗ Confirmation modals test failed: {e}")
        return False

def test_form_structure_and_validation_elements(driver):
    """Test form structure and validation elements"""
    print("Testing form structure and validation elements...")
    
    try:
        # Test General form
        general_form = driver.find_element(By.ID, "general-settings-form")
        assert general_form.is_displayed(), "General settings form not visible"
        
        # Check for required form fields
        required_fields = ["site-title", "admin-email", "timezone"]
        for field_id in required_fields:
            field = driver.find_element(By.ID, field_id)
            assert field.is_displayed(), f"Field {field_id} not visible"
        print("✓ General form fields are present")
        
        # Test Security form validation elements
        security_tab = driver.find_element(By.ID, "security-tab")
        security_tab.click()
        time.sleep(0.5)
        
        security_form = driver.find_element(By.ID, "security-settings-form")
        assert security_form.is_displayed(), "Security settings form not visible"
        
        # Check numeric input fields
        numeric_fields = ["session-timeout", "login-attempts"]
        for field_id in numeric_fields:
            field = driver.find_element(By.ID, field_id)
            assert field.get_attribute("type") == "number", f"Field {field_id} not numeric type"
        print("✓ Security form numeric fields are properly typed")
        
        return True
        
    except Exception as e:
        print(f"✗ Form structure test failed: {e}")
        return False

def run_all_tests():
    """Run all settings page tests"""
    print("Starting Settings Page Enhancement Tests")
    print("=" * 50)
    
    driver = setup_driver()
    if not driver:
        print("Failed to setup driver. Exiting.")
        return False
    
    tests = [
        test_settings_page_structure,
        test_settings_search_functionality,
        test_settings_tabs_structure,
        test_advanced_settings_management_cards,
        test_confirmation_modals_structure,
        test_form_structure_and_validation_elements
    ]
    
    passed = 0
    failed = 0
    
    try:
        for test in tests:
            print(f"\n--- {test.__name__} ---")
            if test(driver):
                passed += 1
                print(f"✓ {test.__name__} PASSED")
            else:
                failed += 1
                print(f"✗ {test.__name__} FAILED")
    
    finally:
        driver.quit()
    
    print("\n" + "=" * 50)
    print(f"Settings Page Enhancement Test Results:")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All settings page enhancement tests passed!")
        return True
    else:
        print(f"\n❌ {failed} test(s) failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)