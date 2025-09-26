#!/usr/bin/env python3
"""
Admin User Verification and Credential Management Tools

This script provides comprehensive tools for verifying admin users, validating credentials,
and managing admin user accounts in the unified authentication system.

Requirements addressed:
- 5.1: Verify admin users exist with correct credentials in database
- 5.2: Implement password hash validation and reset functionality  
- 5.3: Create admin user creation utility with proper role and permission assignment
- 5.4: Add database integrity checks for user authentication data
"""

import sys
import os
import argparse
import getpass
import secrets
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from tabulate import tabulate
import logging

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database import get_db, SessionLocal, engine
from backend.unified_models import UnifiedUser, UnifiedUserSession, UserRole
from backend.unified_auth import auth_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AdminUserManager:
    """Comprehensive admin user management and verification system"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()
    
    def verify_admin_users(self) -> Dict[str, Any]:
        """
        Verify admin users exist with correct credentials in database
        Requirement: 5.1
        """
        logger.info("Starting admin user verification...")
        
        verification_results = {
            "total_users": 0,
            "admin_users": 0,
            "active_admin_users": 0,
            "inactive_admin_users": 0,
            "super_admin_users": 0,
            "users_with_sessions": 0,
            "admin_users_details": [],
            "issues_found": [],
            "recommendations": []
        }
        
        try:
            # Get all users
            all_users = self.db.query(UnifiedUser).all()
            verification_results["total_users"] = len(all_users)
            
            # Filter admin users
            admin_users = [user for user in all_users if user.is_admin or user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]]
            verification_results["admin_users"] = len(admin_users)
            
            # Analyze admin users
            for user in admin_users:
                # Check if user is active
                if user.is_active:
                    verification_results["active_admin_users"] += 1
                else:
                    verification_results["inactive_admin_users"] += 1
                
                # Check if user is super admin
                if user.role == UserRole.SUPER_ADMIN:
                    verification_results["super_admin_users"] += 1
                
                # Check for active sessions
                active_sessions = self.db.query(UnifiedUserSession).filter(
                    UnifiedUserSession.user_id == user.id,
                    UnifiedUserSession.is_active == True,
                    UnifiedUserSession.expires_at > datetime.now(timezone.utc)
                ).count()
                
                if active_sessions > 0:
                    verification_results["users_with_sessions"] += 1
                
                # Validate password hash format
                password_hash_valid = self._validate_password_hash(user.password_hash)
                
                # Collect user details
                user_detail = {
                    "id": user.id,
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role.value if user.role else "None",
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                    "last_login": user.last_login,
                    "password_hash_valid": password_hash_valid,
                    "active_sessions": active_sessions
                }
                verification_results["admin_users_details"].append(user_detail)
                
                # Check for issues
                if not password_hash_valid:
                    verification_results["issues_found"].append(
                        f"User {user.username} has invalid password hash format"
                    )
                
                if not user.is_active:
                    verification_results["issues_found"].append(
                        f"Admin user {user.username} is inactive"
                    )
                
                if user.is_admin and user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                    verification_results["issues_found"].append(
                        f"User {user.username} has is_admin=True but role is {user.role}"
                    )
            
            # Generate recommendations
            if verification_results["admin_users"] == 0:
                verification_results["recommendations"].append(
                    "No admin users found. Create at least one admin user."
                )
            
            if verification_results["super_admin_users"] == 0:
                verification_results["recommendations"].append(
                    "No super admin users found. Consider creating a super admin user."
                )
            
            if verification_results["active_admin_users"] == 0:
                verification_results["recommendations"].append(
                    "No active admin users found. Activate at least one admin user."
                )
            
            logger.info(f"Admin user verification completed. Found {verification_results['admin_users']} admin users.")
            return verification_results
            
        except Exception as e:
            logger.error(f"Admin user verification failed: {e}")
            verification_results["issues_found"].append(f"Verification error: {str(e)}")
            return verification_results
    
    def validate_password_hash(self, username: str, password: str) -> Dict[str, Any]:
        """
        Validate password hash for a specific user
        Requirement: 5.2
        """
        logger.info(f"Validating password hash for user: {username}")
        
        result = {
            "username": username,
            "user_found": False,
            "password_valid": False,
            "hash_format_valid": False,
            "error": None
        }
        
        try:
            # Find user
            user = self.db.query(UnifiedUser).filter(
                (UnifiedUser.username == username) |
                (UnifiedUser.email == username) |
                (UnifiedUser.user_id == username)
            ).first()
            
            if not user:
                result["error"] = "User not found"
                return result
            
            result["user_found"] = True
            
            # Validate hash format
            result["hash_format_valid"] = self._validate_password_hash(user.password_hash)
            
            # Validate password
            result["password_valid"] = auth_service.verify_password(password, user.password_hash)
            
            logger.info(f"Password validation completed for {username}: valid={result['password_valid']}")
            return result
            
        except Exception as e:
            logger.error(f"Password validation error for {username}: {e}")
            result["error"] = str(e)
            return result
    
    def reset_user_password(self, username: str, new_password: str) -> Dict[str, Any]:
        """
        Reset password for a user with proper hash validation
        Requirement: 5.2
        """
        logger.info(f"Resetting password for user: {username}")
        
        result = {
            "username": username,
            "success": False,
            "user_found": False,
            "error": None
        }
        
        try:
            # Find user
            user = self.db.query(UnifiedUser).filter(
                (UnifiedUser.username == username) |
                (UnifiedUser.email == username) |
                (UnifiedUser.user_id == username)
            ).first()
            
            if not user:
                result["error"] = "User not found"
                return result
            
            result["user_found"] = True
            
            # Validate new password
            if len(new_password) < 8:
                result["error"] = "Password must be at least 8 characters long"
                return result
            
            # Hash new password
            new_hash = auth_service.hash_password(new_password)
            
            # Validate the new hash
            if not self._validate_password_hash(new_hash):
                result["error"] = "Failed to generate valid password hash"
                return result
            
            # Update password
            user.password_hash = new_hash
            user.updated_at = datetime.now(timezone.utc)
            
            # Invalidate all existing sessions for security
            self.db.query(UnifiedUserSession).filter(
                UnifiedUserSession.user_id == user.id
            ).update({"is_active": False})
            
            self.db.commit()
            
            result["success"] = True
            logger.info(f"Password reset successful for user: {username}")
            return result
            
        except Exception as e:
            logger.error(f"Password reset error for {username}: {e}")
            self.db.rollback()
            result["error"] = str(e)
            return result
    
    def create_admin_user(self, username: str, email: str, password: str, 
                         full_name: str = None, role: str = "admin") -> Dict[str, Any]:
        """
        Create admin user with proper role and permission assignment
        Requirement: 5.3
        """
        logger.info(f"Creating admin user: {username}")
        
        result = {
            "username": username,
            "success": False,
            "user_created": False,
            "error": None,
            "user_id": None
        }
        
        try:
            # Validate role
            try:
                user_role = UserRole(role.lower())
            except ValueError:
                result["error"] = f"Invalid role: {role}. Valid roles: admin, super_admin"
                return result
            
            # Check if user already exists
            existing_user = self.db.query(UnifiedUser).filter(
                (UnifiedUser.username == username) |
                (UnifiedUser.email == email)
            ).first()
            
            if existing_user:
                result["error"] = "User with this username or email already exists"
                return result
            
            # Validate password
            if len(password) < 8:
                result["error"] = "Password must be at least 8 characters long"
                return result
            
            # Generate unique user_id
            user_id = f"admin_{secrets.token_hex(8)}"
            
            # Hash password
            password_hash = auth_service.hash_password(password)
            
            # Validate hash
            if not self._validate_password_hash(password_hash):
                result["error"] = "Failed to generate valid password hash"
                return result
            
            # Create user
            new_user = UnifiedUser(
                user_id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                role=user_role,
                is_admin=True,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)
            
            result["success"] = True
            result["user_created"] = True
            result["user_id"] = new_user.user_id
            
            logger.info(f"Admin user created successfully: {username} (ID: {user_id})")
            return result
            
        except Exception as e:
            logger.error(f"Admin user creation error for {username}: {e}")
            self.db.rollback()
            result["error"] = str(e)
            return result
    
    def check_database_integrity(self) -> Dict[str, Any]:
        """
        Add database integrity checks for user authentication data
        Requirement: 5.4
        """
        logger.info("Starting database integrity checks...")
        
        integrity_results = {
            "checks_performed": [],
            "issues_found": [],
            "warnings": [],
            "recommendations": [],
            "statistics": {}
        }
        
        try:
            # Check 1: Users with invalid password hashes
            logger.info("Checking password hash integrity...")
            users_with_invalid_hashes = []
            all_users = self.db.query(UnifiedUser).all()
            
            for user in all_users:
                if not self._validate_password_hash(user.password_hash):
                    users_with_invalid_hashes.append(user.username)
            
            integrity_results["checks_performed"].append("Password hash format validation")
            if users_with_invalid_hashes:
                integrity_results["issues_found"].append(
                    f"Users with invalid password hashes: {', '.join(users_with_invalid_hashes)}"
                )
            
            # Check 2: Users with inconsistent admin flags
            logger.info("Checking admin flag consistency...")
            inconsistent_admin_flags = []
            
            for user in all_users:
                # Check if is_admin flag matches role
                expected_is_admin = user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
                if user.is_admin != expected_is_admin:
                    inconsistent_admin_flags.append(
                        f"{user.username}: is_admin={user.is_admin}, role={user.role}"
                    )
            
            integrity_results["checks_performed"].append("Admin flag consistency")
            if inconsistent_admin_flags:
                integrity_results["issues_found"].extend(inconsistent_admin_flags)
            
            # Check 3: Orphaned sessions
            logger.info("Checking for orphaned sessions...")
            orphaned_sessions = self.db.query(UnifiedUserSession).filter(
                ~UnifiedUserSession.user_id.in_(
                    self.db.query(UnifiedUser.id)
                )
            ).count()
            
            integrity_results["checks_performed"].append("Orphaned sessions check")
            if orphaned_sessions > 0:
                integrity_results["issues_found"].append(
                    f"Found {orphaned_sessions} orphaned sessions"
                )
            
            # Check 4: Expired but still active sessions
            logger.info("Checking for expired active sessions...")
            expired_active_sessions = self.db.query(UnifiedUserSession).filter(
                UnifiedUserSession.is_active == True,
                UnifiedUserSession.expires_at < datetime.now(timezone.utc)
            ).count()
            
            integrity_results["checks_performed"].append("Expired active sessions check")
            if expired_active_sessions > 0:
                integrity_results["warnings"].append(
                    f"Found {expired_active_sessions} expired but still active sessions"
                )
            
            # Check 5: Users without required fields
            logger.info("Checking for users with missing required fields...")
            users_missing_fields = []
            
            for user in all_users:
                missing_fields = []
                if not user.username:
                    missing_fields.append("username")
                if not user.email:
                    missing_fields.append("email")
                if not user.password_hash:
                    missing_fields.append("password_hash")
                if not user.user_id:
                    missing_fields.append("user_id")
                
                if missing_fields:
                    users_missing_fields.append(
                        f"{user.username or 'Unknown'}: missing {', '.join(missing_fields)}"
                    )
            
            integrity_results["checks_performed"].append("Required fields validation")
            if users_missing_fields:
                integrity_results["issues_found"].extend(users_missing_fields)
            
            # Check 6: Duplicate usernames or emails
            logger.info("Checking for duplicate usernames and emails...")
            
            # Check duplicate usernames
            duplicate_usernames = self.db.query(UnifiedUser.username).group_by(
                UnifiedUser.username
            ).having(func.count(UnifiedUser.username) > 1).all()
            
            if duplicate_usernames:
                integrity_results["issues_found"].append(
                    f"Duplicate usernames found: {[u[0] for u in duplicate_usernames]}"
                )
            
            # Check duplicate emails
            duplicate_emails = self.db.query(UnifiedUser.email).group_by(
                UnifiedUser.email
            ).having(func.count(UnifiedUser.email) > 1).all()
            
            if duplicate_emails:
                integrity_results["issues_found"].append(
                    f"Duplicate emails found: {[e[0] for e in duplicate_emails]}"
                )
            
            integrity_results["checks_performed"].append("Duplicate data check")
            
            # Generate statistics
            integrity_results["statistics"] = {
                "total_users": len(all_users),
                "admin_users": len([u for u in all_users if u.is_admin]),
                "active_users": len([u for u in all_users if u.is_active]),
                "total_sessions": self.db.query(UnifiedUserSession).count(),
                "active_sessions": self.db.query(UnifiedUserSession).filter(
                    UnifiedUserSession.is_active == True
                ).count(),
                "expired_sessions": self.db.query(UnifiedUserSession).filter(
                    UnifiedUserSession.expires_at < datetime.now(timezone.utc)
                ).count()
            }
            
            # Generate recommendations
            if len(integrity_results["issues_found"]) == 0:
                integrity_results["recommendations"].append(
                    "Database integrity is good. No critical issues found."
                )
            else:
                integrity_results["recommendations"].append(
                    "Fix the identified issues to ensure database integrity."
                )
            
            if expired_active_sessions > 0:
                integrity_results["recommendations"].append(
                    "Run session cleanup to remove expired sessions."
                )
            
            logger.info(f"Database integrity check completed. Found {len(integrity_results['issues_found'])} issues.")
            return integrity_results
            
        except Exception as e:
            logger.error(f"Database integrity check failed: {e}")
            integrity_results["issues_found"].append(f"Integrity check error: {str(e)}")
            return integrity_results
    
    def cleanup_expired_sessions(self) -> Dict[str, Any]:
        """Clean up expired sessions"""
        logger.info("Cleaning up expired sessions...")
        
        try:
            cleaned_count = auth_service.cleanup_expired_sessions(self.db)
            
            return {
                "success": True,
                "cleaned_sessions": cleaned_count,
                "message": f"Cleaned up {cleaned_count} expired sessions"
            }
            
        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _validate_password_hash(self, password_hash: str) -> bool:
        """Validate password hash format (bcrypt)"""
        if not password_hash:
            return False
        
        # bcrypt hashes start with $2a$, $2b$, $2x$, or $2y$ and are 60 characters long
        if not password_hash.startswith(('$2a$', '$2b$', '$2x$', '$2y$')):
            return False
        
        if len(password_hash) != 60:
            return False
        
        return True
    
    def list_admin_users(self) -> List[Dict[str, Any]]:
        """List all admin users with their details"""
        try:
            admin_users = self.db.query(UnifiedUser).filter(
                (UnifiedUser.is_admin == True) |
                (UnifiedUser.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN]))
            ).all()
            
            return [
                {
                    "id": user.id,
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role.value if user.role else "None",
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                    "last_login": user.last_login
                }
                for user in admin_users
            ]
            
        except Exception as e:
            logger.error(f"Failed to list admin users: {e}")
            return []

def print_verification_results(results: Dict[str, Any]):
    """Print admin user verification results in a formatted way"""
    print("\n" + "="*60)
    print("ADMIN USER VERIFICATION RESULTS")
    print("="*60)
    
    # Summary statistics
    print(f"\nSUMMARY:")
    print(f"  Total Users: {results['total_users']}")
    print(f"  Admin Users: {results['admin_users']}")
    print(f"  Active Admin Users: {results['active_admin_users']}")
    print(f"  Inactive Admin Users: {results['inactive_admin_users']}")
    print(f"  Super Admin Users: {results['super_admin_users']}")
    print(f"  Admin Users with Active Sessions: {results['users_with_sessions']}")
    
    # Admin users details
    if results['admin_users_details']:
        print(f"\nADMIN USERS DETAILS:")
        headers = ["Username", "Email", "Role", "Active", "Last Login", "Sessions", "Hash Valid"]
        table_data = []
        
        for user in results['admin_users_details']:
            table_data.append([
                user['username'],
                user['email'],
                user['role'],
                "Yes" if user['is_active'] else "No",
                user['last_login'].strftime("%Y-%m-%d %H:%M") if user['last_login'] else "Never",
                user['active_sessions'],
                "Yes" if user['password_hash_valid'] else "No"
            ])
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Issues found
    if results['issues_found']:
        print(f"\nISSUES FOUND:")
        for i, issue in enumerate(results['issues_found'], 1):
            print(f"  {i}. {issue}")
    
    # Recommendations
    if results['recommendations']:
        print(f"\nRECOMMENDATIONS:")
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"  {i}. {rec}")
    
    print("\n" + "="*60)

def print_integrity_results(results: Dict[str, Any]):
    """Print database integrity check results in a formatted way"""
    print("\n" + "="*60)
    print("DATABASE INTEGRITY CHECK RESULTS")
    print("="*60)
    
    # Checks performed
    print(f"\nCHECKS PERFORMED:")
    for i, check in enumerate(results['checks_performed'], 1):
        print(f"  {i}. {check}")
    
    # Statistics
    if results['statistics']:
        print(f"\nSTATISTICS:")
        stats = results['statistics']
        print(f"  Total Users: {stats.get('total_users', 0)}")
        print(f"  Admin Users: {stats.get('admin_users', 0)}")
        print(f"  Active Users: {stats.get('active_users', 0)}")
        print(f"  Total Sessions: {stats.get('total_sessions', 0)}")
        print(f"  Active Sessions: {stats.get('active_sessions', 0)}")
        print(f"  Expired Sessions: {stats.get('expired_sessions', 0)}")
    
    # Issues found
    if results['issues_found']:
        print(f"\nISSUES FOUND:")
        for i, issue in enumerate(results['issues_found'], 1):
            print(f"  {i}. {issue}")
    
    # Warnings
    if results['warnings']:
        print(f"\nWARNINGS:")
        for i, warning in enumerate(results['warnings'], 1):
            print(f"  {i}. {warning}")
    
    # Recommendations
    if results['recommendations']:
        print(f"\nRECOMMENDATIONS:")
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"  {i}. {rec}")
    
    print("\n" + "="*60)

def main():
    """Main CLI interface for admin user verification tools"""
    parser = argparse.ArgumentParser(
        description="Admin User Verification and Credential Management Tools"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify admin users exist with correct credentials')
    
    # Validate password command
    validate_parser = subparsers.add_parser('validate', help='Validate password for a user')
    validate_parser.add_argument('username', help='Username, email, or user_id to validate')
    validate_parser.add_argument('--password', help='Password to validate (will prompt if not provided)')
    
    # Reset password command
    reset_parser = subparsers.add_parser('reset-password', help='Reset password for a user')
    reset_parser.add_argument('username', help='Username, email, or user_id to reset password for')
    reset_parser.add_argument('--password', help='New password (will prompt if not provided)')
    
    # Create admin command
    create_parser = subparsers.add_parser('create-admin', help='Create new admin user')
    create_parser.add_argument('username', help='Username for new admin user')
    create_parser.add_argument('email', help='Email for new admin user')
    create_parser.add_argument('--password', help='Password for new admin user (will prompt if not provided)')
    create_parser.add_argument('--full-name', help='Full name for new admin user')
    create_parser.add_argument('--role', choices=['admin', 'super_admin'], default='admin', help='Role for new admin user')
    
    # Integrity check command
    integrity_parser = subparsers.add_parser('integrity', help='Check database integrity for user authentication data')
    
    # List admin users command
    list_parser = subparsers.add_parser('list', help='List all admin users')
    
    # Cleanup sessions command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up expired sessions')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        with AdminUserManager() as manager:
            if args.command == 'verify':
                results = manager.verify_admin_users()
                print_verification_results(results)
                
            elif args.command == 'validate':
                password = args.password
                if not password:
                    password = getpass.getpass(f"Enter password for {args.username}: ")
                
                result = manager.validate_password_hash(args.username, password)
                
                print(f"\nPassword validation for {args.username}:")
                print(f"  User found: {'Yes' if result['user_found'] else 'No'}")
                if result['user_found']:
                    print(f"  Hash format valid: {'Yes' if result['hash_format_valid'] else 'No'}")
                    print(f"  Password valid: {'Yes' if result['password_valid'] else 'No'}")
                if result['error']:
                    print(f"  Error: {result['error']}")
                
            elif args.command == 'reset-password':
                password = args.password
                if not password:
                    password = getpass.getpass(f"Enter new password for {args.username}: ")
                    confirm_password = getpass.getpass("Confirm new password: ")
                    if password != confirm_password:
                        print("Passwords do not match!")
                        return
                
                result = manager.reset_user_password(args.username, password)
                
                print(f"\nPassword reset for {args.username}:")
                print(f"  Success: {'Yes' if result['success'] else 'No'}")
                if result['error']:
                    print(f"  Error: {result['error']}")
                elif result['success']:
                    print("  Password reset successfully. All user sessions have been invalidated.")
                
            elif args.command == 'create-admin':
                password = args.password
                if not password:
                    password = getpass.getpass(f"Enter password for new admin user {args.username}: ")
                    confirm_password = getpass.getpass("Confirm password: ")
                    if password != confirm_password:
                        print("Passwords do not match!")
                        return
                
                result = manager.create_admin_user(
                    args.username, args.email, password, args.full_name, args.role
                )
                
                print(f"\nAdmin user creation for {args.username}:")
                print(f"  Success: {'Yes' if result['success'] else 'No'}")
                if result['success']:
                    print(f"  User ID: {result['user_id']}")
                    print(f"  Role: {args.role}")
                if result['error']:
                    print(f"  Error: {result['error']}")
                
            elif args.command == 'integrity':
                results = manager.check_database_integrity()
                print_integrity_results(results)
                
            elif args.command == 'list':
                admin_users = manager.list_admin_users()
                
                if admin_users:
                    print(f"\nFound {len(admin_users)} admin users:")
                    headers = ["Username", "Email", "Role", "Active", "Created", "Last Login"]
                    table_data = []
                    
                    for user in admin_users:
                        table_data.append([
                            user['username'],
                            user['email'],
                            user['role'],
                            "Yes" if user['is_active'] else "No",
                            user['created_at'].strftime("%Y-%m-%d") if user['created_at'] else "Unknown",
                            user['last_login'].strftime("%Y-%m-%d %H:%M") if user['last_login'] else "Never"
                        ])
                    
                    print(tabulate(table_data, headers=headers, tablefmt="grid"))
                else:
                    print("No admin users found.")
                
            elif args.command == 'cleanup':
                result = manager.cleanup_expired_sessions()
                
                print(f"\nSession cleanup:")
                print(f"  Success: {'Yes' if result['success'] else 'No'}")
                if result['success']:
                    print(f"  Cleaned sessions: {result['cleaned_sessions']}")
                if result.get('error'):
                    print(f"  Error: {result['error']}")
    
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()