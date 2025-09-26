#!/usr/bin/env python3
"""
Final comprehensive test for admin login fix
"""

import requests
import time
import json

def test_backend_only():
    """Test just the backend authentication"""
    print("=== Testing Backend Authentication ===")
    
    try:
        response = requests.post(
            'http://localhost:8000/api/auth/login',
            json={
                'email': 'admin@example.com',
                'password': 'admin123'
            },
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Raw response: {response.text[:500]}...")
            
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            print(f"Success: {data.get('success', False)}")
            print(f"Has Token: {'token' in data}")
            print(f"Has Access Token: {'access_token' in data}")
            print(f"Has User: {'user' in data}")
            
            # Check if token is None vs missing
            if 'token' in data:
                print(f"Token Value: {data['token']}")
            if 'access_token' in data:
                print(f"Access Token Value: {data['access_token']}")
            
            print(f"User Data: {data.get('user', {})}")
            
            has_any_token = data.get('token') or data.get('access_token')
            print(f"Has Any Token: {bool(has_any_token)}")
            
            if data.get('success') and data.get('user'):
                print("✅ Backend authentication is working (user authenticated)!")
                return True
            else:
                print("❌ Backend authentication failed!")
                return False
        else:
            print(f"❌ Backend error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend - make sure the server is running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def test_admin_page_access():
    """Test accessing the admin page"""
    print("\n=== Testing Admin Page Access ===")
    
    try:
        response = requests.get('http://localhost:8000/admin', timeout=10)
        print(f"Admin page status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            
            # Check for key elements
            has_login_modal = 'id="loginModal"' in content
            has_login_form = 'id="login-form"' in content
            has_dashboard_content = 'id="content-dashboard"' in content
            has_simple_auth_fix = 'simple-auth-fix.js' in content
            
            print(f"Has login modal: {has_login_modal}")
            print(f"Has login form: {has_login_form}")
            print(f"Has dashboard content: {has_dashboard_content}")
            print(f"Has simple auth fix: {has_simple_auth_fix}")
            
            if has_login_modal and has_login_form and has_dashboard_content:
                print("✅ Admin page structure is correct!")
                return True
            else:
                print("❌ Admin page missing required elements")
                return False
        else:
            print(f"❌ Admin page access failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Admin page test error: {e}")
        return False

def test_simple_auth_fix_script():
    """Test if the simple auth fix script is accessible"""
    print("\n=== Testing Simple Auth Fix Script ===")
    
    try:
        response = requests.get('http://localhost:8000/admin/js/simple-auth-fix.js', timeout=10)
        print(f"Simple auth fix script status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            
            # Check for key functions
            has_handle_simple_login = 'handleSimpleLogin' in content
            has_hide_login_modal = 'hideLoginModal' in content
            has_show_dashboard_content = 'showDashboardContent' in content
            
            print(f"Has handleSimpleLogin: {has_handle_simple_login}")
            print(f"Has hideLoginModal: {has_hide_login_modal}")
            print(f"Has showDashboardContent: {has_show_dashboard_content}")
            
            if has_handle_simple_login and has_hide_login_modal and has_show_dashboard_content:
                print("✅ Simple auth fix script is correct!")
                return True
            else:
                print("❌ Simple auth fix script missing required functions")
                return False
        else:
            print(f"❌ Simple auth fix script not accessible: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Simple auth fix script test error: {e}")
        return False

def create_test_instructions():
    """Create manual test instructions"""
    instructions = """
=== MANUAL TESTING INSTRUCTIONS ===

1. Start your backend server:
   python main.py

2. Open browser to: http://localhost:8000/admin

3. You should see:
   - Login modal appears
   - Email field pre-filled or enter: admin@example.com
   - Password field enter: admin123

4. Click "Login" button

5. Expected result:
   ✅ Login modal disappears immediately
   ✅ Dashboard content becomes visible
   ✅ Username appears in top-right dropdown
   ✅ No page refresh occurs
   ✅ You can navigate the dashboard

6. If issues persist, check browser console (F12) for errors

7. Alternative test page: http://localhost:8000/admin-dashboard/frontend/test-simple-login.html

=== DEBUGGING STEPS ===

If login modal still persists:

1. Open browser console (F12)
2. Check for JavaScript errors
3. Run these commands in console:

   // Check if tokens are stored
   console.log('Tokens:', {
       authToken: localStorage.getItem('authToken'),
       adminToken: localStorage.getItem('admin_session_token')
   });

   // Force hide modal
   const modal = document.getElementById('loginModal');
   if (modal) {
       modal.style.display = 'none';
       document.body.classList.remove('modal-open');
       document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
   }

   // Check if simple auth fix loaded
   console.log('Simple auth functions:', {
       hideLoginModal: typeof hideLoginModal,
       showDashboardContent: typeof showDashboardContent,
       handleSimpleLogin: typeof handleSimpleLogin
   });

=== EXPECTED BROWSER CONSOLE LOGS ===

When login works correctly, you should see:
- "Simple auth fix loaded"
- "Simple login handler attached"
- "Simple login handler triggered"
- "Sending login request..."
- "Login response status: 200"
- "Login successful, processing..."
- "Tokens stored, hiding modal..."
- "Modal hidden using direct DOM manipulation"
- "Showing dashboard content..."

"""
    
    with open('ai-agent/MANUAL_TEST_INSTRUCTIONS.txt', 'w') as f:
        f.write(instructions)
    
    print(instructions)

def main():
    """Run all tests"""
    print("🔧 FINAL ADMIN LOGIN FIX TEST")
    print("=" * 50)
    
    backend_ok = test_backend_only()
    admin_page_ok = test_admin_page_access()
    script_ok = test_simple_auth_fix_script()
    
    print("\n" + "=" * 50)
    print("TEST RESULTS:")
    print(f"Backend Authentication: {'✅ PASS' if backend_ok else '❌ FAIL'}")
    print(f"Admin Page Structure: {'✅ PASS' if admin_page_ok else '❌ FAIL'}")
    print(f"Simple Auth Fix Script: {'✅ PASS' if script_ok else '❌ FAIL'}")
    
    overall_success = backend_ok and admin_page_ok and script_ok
    print(f"Overall Status: {'✅ READY FOR TESTING' if overall_success else '❌ NEEDS FIXES'}")
    
    if overall_success:
        print("\n🎉 All automated tests passed!")
        print("The login fix should now work. Please test manually in browser.")
        create_test_instructions()
    else:
        print("\n❌ Some tests failed. Check the errors above.")
    
    return overall_success

if __name__ == "__main__":
    main()