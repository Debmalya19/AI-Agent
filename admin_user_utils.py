#!/usr/bin/env python3
"""
Admin User Utilities - Simple interface for common admin user management tasks

This script provides a simplified interface for the most common admin user management
operations, making it easy to quickly verify, create, and manage admin users.
"""

import sys
import os
import getpass
from typing import Optional

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from admin_user_verification import AdminUserManager, print_verification_results

def quick_verify():
    """Quick verification of admin users"""
    print("Performing quick admin user verification...")
    
    with AdminUserManager() as manager:
        results = manager.verify_admin_users()
        
        # Print simplified results
        print(f"\nQuick Summary:")
        print(f"  Total Users: {results['total_users']}")
        print(f"  Admin Users: {results['admin_users']}")
        print(f"  Active Admin Users: {results['active_admin_users']}")
        
        if results['issues_found']:
            print(f"\n⚠️  Issues Found: {len(results['issues_found'])}")
            for issue in results['issues_found'][:3]:  # Show first 3 issues
                print(f"    - {issue}")
            if len(results['issues_found']) > 3:
                print(f"    ... and {len(results['issues_found']) - 3} more")
        else:
            print("\n✅ No issues found")
        
        if results['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in results['recommendations'][:2]:  # Show first 2 recommendations
                print(f"    - {rec}")

def quick_create_admin():
    """Quick admin user creation with prompts"""
    print("Creating new admin user...")
    
    username = input("Enter username: ").strip()
    if not username:
        print("Username is required!")
        return False
    
    email = input("Enter email: ").strip()
    if not email:
        print("Email is required!")
        return False
    
    full_name = input("Enter full name (optional): ").strip() or None
    
    role = input("Enter role (admin/super_admin) [admin]: ").strip().lower() or "admin"
    if role not in ["admin", "super_admin"]:
        print("Invalid role! Must be 'admin' or 'super_admin'")
        return False
    
    password = getpass.getpass("Enter password: ")
    if len(password) < 8:
        print("Password must be at least 8 characters long!")
        return False
    
    confirm_password = getpass.getpass("Confirm password: ")
    if password != confirm_password:
        print("Passwords do not match!")
        return False
    
    with AdminUserManager() as manager:
        result = manager.create_admin_user(username, email, password, full_name, role)
        
        if result['success']:
            print(f"\n✅ Admin user created successfully!")
            print(f"   Username: {username}")
            print(f"   Email: {email}")
            print(f"   Role: {role}")
            print(f"   User ID: {result['user_id']}")
            return True
        else:
            print(f"\n❌ Failed to create admin user: {result['error']}")
            return False

def quick_reset_password():
    """Quick password reset with prompts"""
    print("Resetting user password...")
    
    username = input("Enter username/email to reset password for: ").strip()
    if not username:
        print("Username/email is required!")
        return False
    
    password = getpass.getpass("Enter new password: ")
    if len(password) < 8:
        print("Password must be at least 8 characters long!")
        return False
    
    confirm_password = getpass.getpass("Confirm new password: ")
    if password != confirm_password:
        print("Passwords do not match!")
        return False
    
    with AdminUserManager() as manager:
        result = manager.reset_user_password(username, password)
        
        if result['success']:
            print(f"\n✅ Password reset successfully for {username}")
            print("   All user sessions have been invalidated for security.")
            return True
        else:
            print(f"\n❌ Failed to reset password: {result['error']}")
            return False

def quick_list_admins():
    """Quick list of admin users"""
    print("Listing admin users...")
    
    with AdminUserManager() as manager:
        admin_users = manager.list_admin_users()
        
        if admin_users:
            print(f"\nFound {len(admin_users)} admin users:")
            print("-" * 80)
            for user in admin_users:
                status = "Active" if user['is_active'] else "Inactive"
                last_login = user['last_login'].strftime("%Y-%m-%d %H:%M") if user['last_login'] else "Never"
                print(f"  {user['username']} ({user['email']}) - {user['role']} - {status} - Last login: {last_login}")
        else:
            print("No admin users found.")

def quick_validate_login():
    """Quick login validation"""
    print("Validating user login...")
    
    username = input("Enter username/email: ").strip()
    if not username:
        print("Username/email is required!")
        return False
    
    password = getpass.getpass("Enter password: ")
    
    with AdminUserManager() as manager:
        result = manager.validate_password_hash(username, password)
        
        if result['user_found']:
            if result['password_valid']:
                print(f"\n✅ Login validation successful for {username}")
                print("   Password is correct")
            else:
                print(f"\n❌ Login validation failed for {username}")
                print("   Password is incorrect")
        else:
            print(f"\n❌ User not found: {username}")
        
        return result['password_valid'] if result['user_found'] else False

def quick_integrity_check():
    """Quick database integrity check"""
    print("Performing database integrity check...")
    
    with AdminUserManager() as manager:
        results = manager.check_database_integrity()
        
        print(f"\nIntegrity Check Results:")
        print(f"  Checks performed: {len(results['checks_performed'])}")
        print(f"  Issues found: {len(results['issues_found'])}")
        print(f"  Warnings: {len(results['warnings'])}")
        
        if results['issues_found']:
            print(f"\n⚠️  Critical Issues:")
            for issue in results['issues_found'][:3]:
                print(f"    - {issue}")
            if len(results['issues_found']) > 3:
                print(f"    ... and {len(results['issues_found']) - 3} more")
        
        if results['warnings']:
            print(f"\n⚠️  Warnings:")
            for warning in results['warnings'][:2]:
                print(f"    - {warning}")
        
        if not results['issues_found'] and not results['warnings']:
            print("\n✅ Database integrity is good")

def interactive_menu():
    """Interactive menu for admin user management"""
    while True:
        print("\n" + "="*60)
        print("ADMIN USER MANAGEMENT UTILITIES")
        print("="*60)
        print("1. Quick verify admin users")
        print("2. Create new admin user")
        print("3. Reset user password")
        print("4. List admin users")
        print("5. Validate user login")
        print("6. Database integrity check")
        print("7. Full verification report")
        print("0. Exit")
        print("-"*60)
        
        choice = input("Select option (0-7): ").strip()
        
        try:
            if choice == "0":
                print("Goodbye!")
                break
            elif choice == "1":
                quick_verify()
            elif choice == "2":
                quick_create_admin()
            elif choice == "3":
                quick_reset_password()
            elif choice == "4":
                quick_list_admins()
            elif choice == "5":
                quick_validate_login()
            elif choice == "6":
                quick_integrity_check()
            elif choice == "7":
                with AdminUserManager() as manager:
                    results = manager.verify_admin_users()
                    print_verification_results(results)
            else:
                print("Invalid option. Please select 0-7.")
        
        except KeyboardInterrupt:
            print("\n\nOperation cancelled.")
        except Exception as e:
            print(f"\nError: {e}")
        
        if choice != "0":
            input("\nPress Enter to continue...")

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "verify":
            quick_verify()
        elif command == "create":
            quick_create_admin()
        elif command == "reset":
            quick_reset_password()
        elif command == "list":
            quick_list_admins()
        elif command == "validate":
            quick_validate_login()
        elif command == "integrity":
            quick_integrity_check()
        elif command == "menu":
            interactive_menu()
        else:
            print("Usage: python admin_user_utils.py [command]")
            print("Commands: verify, create, reset, list, validate, integrity, menu")
            print("Or run without arguments for interactive menu")
    else:
        interactive_menu()

if __name__ == "__main__":
    main()