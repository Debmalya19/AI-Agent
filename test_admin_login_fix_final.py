#!/usr/bin/env python3
"""
Final test for admin login fix - verifies the complete authentication flow
"""

import requests
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def test_backend_authentication():
    """Test backend authentication endpoint"""
    print("Testing backend authentication...")
    
    try:
        # Test login endpoint
        login_data = {
            "email": "admin@example.com",
            "password": "admin123"
        }
        
        response = requests.post(
            "http://localhost:8000/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Login response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Login successful: {data.get('success', False)}")
            print(f"Has token: {'token' in data or 'access_token' in data}")
            print(f"Has user: {'user' in data}")
            print(f"Redirect URL: {data.get('redirect_url', 'Not specified')}")
            return True
        else:
            print(f"Login failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"Backend test error: {e}")
        return False

def test_frontend_authentication():
    """Test frontend authentication flow with Selenium"""
    print("\nTesting frontend authentication flow...")
    
    # Set up Chrome options for headless testing
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        # Navigate to admin page
        print("Navigating to admin page...")
        driver.get("http://localhost:8000/admin")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        print("Page loaded successfully")
        
        # Check if login modal is present
        try:
            login_modal = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "loginModal"))
            )
            print("Login modal found")
            
            # Check if modal is visible
            if login_modal.is_displayed():
                print("Login modal is visible - good!")
            else:
                print("Login modal exists but not visible")
                
        except TimeoutException:
            print("Login modal not found")
            return False
        
        # Find and fill login form
        try:
            email_field = driver.find_element(By.ID, "email")
            password_field = driver.find_element(By.ID, "password")
            submit_button = driver.find_element(By.CSS_SELECTOR, "#login-form button[type='submit']")
            
            print("Login form elements found")
            
            # Fill in credentials
            email_field.clear()
            email_field.send_keys("admin@example.com")
            
            password_field.clear()
            password_field.send_keys("admin123")
            
            print("Credentials entered")
            
            # Submit form
            submit_button.click()
            print("Login form submitted")
            
            # Wait for authentication to complete
            time.sleep(3)
            
            # Check if login was successful by looking for dashboard elements
            try:
                # Check if login modal is hidden
                login_modal = driver.find_element(By.ID, "loginModal")
                modal_hidden = not login_modal.is_displayed()
                print(f"Login modal hidden: {modal_hidden}")
                
                # Check if dashboard content is visible
                dashboard_content = driver.find_element(By.ID, "content-dashboard")
                dashboard_visible = dashboard_content.is_displayed()
                print(f"Dashboard content visible: {dashboard_visible}")
                
                # Check if sidebar is visible
                sidebar = driver.find_element(By.ID, "sidebar")
                sidebar_visible = sidebar.is_displayed()
                print(f"Sidebar visible: {sidebar_visible}")
                
                # Check if username is displayed
                try:
                    username_element = driver.find_element(By.ID, "username")
                    username_text = username_element.text
                    print(f"Username displayed: '{username_text}'")
                    username_set = username_text and username_text != "User"
                except NoSuchElementException:
                    username_set = False
                    print("Username element not found")
                
                # Check localStorage for tokens
                auth_token = driver.execute_script("return localStorage.getItem('authToken');")
                admin_token = driver.execute_script("return localStorage.getItem('admin_session_token');")
                
                print(f"authToken in localStorage: {bool(auth_token)}")
                print(f"admin_session_token in localStorage: {bool(admin_token)}")
                
                # Success criteria
                success = (
                    modal_hidden and 
                    (dashboard_visible or sidebar_visible) and
                    (auth_token or admin_token)
                )
                
                print(f"\nAuthentication test result: {'SUCCESS' if success else 'FAILED'}")
                
                if success:
                    print("✓ Login modal hidden after authentication")
                    print("✓ Dashboard content or sidebar visible")
                    print("✓ Authentication token stored")
                    if username_set:
                        print("✓ Username displayed correctly")
                else:
                    print("✗ Authentication flow incomplete")
                    
                    # Additional debugging
                    page_source_snippet = driver.page_source[:500]
                    print(f"Page source snippet: {page_source_snippet}")
                
                return success
                
            except Exception as e:
                print(f"Error checking authentication result: {e}")
                return False
                
        except Exception as e:
            print(f"Error with login form: {e}")
            return False
            
    except Exception as e:
        print(f"Frontend test error: {e}")
        return False
        
    finally:
        if driver:
            driver.quit()

def main():
    """Run all authentication tests"""
    print("=== Admin Login Fix - Final Test ===\n")
    
    backend_success = test_backend_authentication()
    frontend_success = test_frontend_authentication()
    
    print(f"\n=== Test Results ===")
    print(f"Backend Authentication: {'✓ PASS' if backend_success else '✗ FAIL'}")
    print(f"Frontend Authentication: {'✓ PASS' if frontend_success else '✗ FAIL'}")
    
    overall_success = backend_success and frontend_success
    print(f"Overall Result: {'✓ SUCCESS' if overall_success else '✗ FAILED'}")
    
    if overall_success:
        print("\n🎉 Admin login fix is working correctly!")
        print("Users should now be able to log in without page refresh issues.")
    else:
        print("\n❌ Admin login fix needs additional work.")
        print("Check the console logs and network requests for more details.")
    
    return overall_success

if __name__ == "__main__":
    main()