# Admin User Verification and Credential Management Tools

This document describes the comprehensive admin user verification and credential management tools implemented to address the admin dashboard login issues.

## Overview

The admin user verification system provides tools to:

1. **Verify admin users exist with correct credentials in database** (Requirement 5.1)
2. **Implement password hash validation and reset functionality** (Requirement 5.2)  
3. **Create admin user creation utility with proper role and permission assignment** (Requirement 5.3)
4. **Add database integrity checks for user authentication data** (Requirement 5.4)

## Files Created

### Core Tools

- **`admin_user_verification.py`** - Main comprehensive tool with full CLI interface
- **`admin_user_utils.py`** - Simplified utility for common tasks
- **`test_admin_user_verification.py`** - Comprehensive test suite

### Documentation

- **`ADMIN_USER_VERIFICATION_README.md`** - This documentation file

## Quick Start

### Interactive Menu (Recommended for beginners)

```bash
cd ai-agent
python admin_user_utils.py
```

This launches an interactive menu with all common operations.

### Command Line Usage

#### Quick Operations

```bash
# Quick verification
python admin_user_utils.py verify

# Create new admin user (with prompts)
python admin_user_utils.py create

# Reset password (with prompts)
python admin_user_utils.py reset

# List admin users
python admin_user_utils.py list

# Validate login credentials
python admin_user_utils.py validate

# Check database integrity
python admin_user_utils.py integrity
```

#### Comprehensive CLI Tool

```bash
# Full admin user verification
python admin_user_verification.py verify

# Validate specific user password
python admin_user_verification.py validate username --password mypassword

# Reset user password
python admin_user_verification.py reset-password username --password newpassword

# Create new admin user
python admin_user_verification.py create-admin newadmin admin@example.com --password adminpass --role admin

# Database integrity check
python admin_user_verification.py integrity

# List all admin users
python admin_user_verification.py list

# Clean up expired sessions
python admin_user_verification.py cleanup
```

## Detailed Features

### 1. Admin User Verification (Requirement 5.1)

Verifies that admin users exist and have correct credentials:

```python
with AdminUserManager() as manager:
    results = manager.verify_admin_users()
```

**Checks performed:**
- Count of total users vs admin users
- Active vs inactive admin users
- Super admin user count
- Users with active sessions
- Password hash format validation
- Role consistency checks

**Output includes:**
- Summary statistics
- Detailed admin user information
- Issues found (inactive admins, invalid hashes, etc.)
- Recommendations for fixes

### 2. Password Hash Validation and Reset (Requirement 5.2)

#### Password Validation

```python
result = manager.validate_password_hash("username", "password")
```

**Validates:**
- User exists in database
- Password hash format is correct (bcrypt)
- Password matches stored hash

#### Password Reset

```python
result = manager.reset_user_password("username", "new_password")
```

**Features:**
- Validates new password strength (minimum 8 characters)
- Generates secure bcrypt hash
- Invalidates all existing user sessions for security
- Updates user record with timestamp

### 3. Admin User Creation (Requirement 5.3)

```python
result = manager.create_admin_user(
    username="newadmin",
    email="admin@example.com", 
    password="secure_password",
    full_name="New Admin",
    role="admin"  # or "super_admin"
)
```

**Features:**
- Proper role assignment (admin or super_admin)
- Automatic permission mapping based on role
- Unique user ID generation
- Email and username uniqueness validation
- Password strength validation
- Secure password hashing

**Roles supported:**
- `admin` - Standard admin with most permissions
- `super_admin` - Full system access with all permissions

### 4. Database Integrity Checks (Requirement 5.4)

```python
results = manager.check_database_integrity()
```

**Checks performed:**
1. **Password hash format validation** - Ensures all users have valid bcrypt hashes
2. **Admin flag consistency** - Verifies is_admin flag matches role
3. **Orphaned sessions check** - Finds sessions without corresponding users
4. **Expired active sessions** - Identifies sessions that should be cleaned up
5. **Required fields validation** - Ensures all users have required data
6. **Duplicate data check** - Finds duplicate usernames or emails

**Output includes:**
- List of all checks performed
- Critical issues found
- Warnings for minor issues
- Database statistics
- Recommendations for fixes

## Security Features

### Password Security
- Uses bcrypt for password hashing
- Minimum 8 character password requirement
- Secure random salt generation
- Password confirmation for interactive operations

### Session Security
- Session invalidation on password reset
- Expired session cleanup
- Session token validation
- Secure session token generation

### Access Control
- Role-based permission system
- Admin privilege verification
- User activation status checks
- Comprehensive audit logging

## Testing

### Run Unit Tests

```bash
cd ai-agent
python -m pytest test_admin_user_verification.py -v
```

### Run Integration Test

```bash
python test_admin_user_verification.py integration
```

The integration test creates a temporary admin user and tests all functionality end-to-end.

## Common Use Cases

### 1. Troubleshooting Login Issues

```bash
# Check if admin users exist and are properly configured
python admin_user_utils.py verify

# Validate specific user credentials
python admin_user_utils.py validate
# Enter username and password when prompted

# Check database integrity
python admin_user_utils.py integrity
```

### 2. Setting Up New Admin User

```bash
# Interactive creation with prompts
python admin_user_utils.py create

# Or command line
python admin_user_verification.py create-admin newadmin admin@company.com --role admin
```

### 3. Fixing Password Issues

```bash
# Reset password interactively
python admin_user_utils.py reset

# Or command line
python admin_user_verification.py reset-password username --password newpassword
```

### 4. System Maintenance

```bash
# Clean up expired sessions
python admin_user_verification.py cleanup

# Full integrity check
python admin_user_verification.py integrity

# List all admin users
python admin_user_verification.py list
```

## Error Handling

The tools include comprehensive error handling:

- **Database connection errors** - Graceful handling with informative messages
- **Invalid input validation** - Clear error messages for invalid data
- **Permission errors** - Proper handling of access control issues
- **Data integrity errors** - Detection and reporting of database inconsistencies

## Logging

All operations are logged with appropriate levels:

- **INFO** - Normal operations and results
- **WARNING** - Non-critical issues (inactive users, expired sessions)
- **ERROR** - Critical errors that need attention

## Integration with Existing System

The tools integrate seamlessly with the existing unified authentication system:

- Uses existing `UnifiedUser` and `UnifiedUserSession` models
- Leverages `auth_service` for password operations
- Compatible with existing role and permission system
- Works with current database schema

## Best Practices

### Regular Maintenance

1. **Weekly integrity checks** to catch issues early
2. **Monthly session cleanup** to remove expired sessions
3. **Quarterly admin user review** to ensure proper access

### Security Practices

1. **Use strong passwords** (minimum 8 characters, mixed case, numbers)
2. **Regular password rotation** for admin accounts
3. **Monitor failed login attempts** through verification reports
4. **Keep admin user count minimal** (principle of least privilege)

### Troubleshooting Workflow

1. **Start with quick verify** to get overview
2. **Run integrity check** if issues found
3. **Validate specific user credentials** if login fails
4. **Check session status** for authentication issues
5. **Reset passwords** as needed
6. **Create new admin users** if none exist

## API Reference

### AdminUserManager Class

#### Methods

- `verify_admin_users()` - Comprehensive admin user verification
- `validate_password_hash(username, password)` - Validate user credentials
- `reset_user_password(username, new_password)` - Reset user password
- `create_admin_user(username, email, password, full_name, role)` - Create admin user
- `check_database_integrity()` - Database integrity checks
- `list_admin_users()` - List all admin users
- `cleanup_expired_sessions()` - Clean expired sessions

#### Context Manager Support

```python
with AdminUserManager() as manager:
    # All operations automatically handle database connections
    results = manager.verify_admin_users()
```

## Troubleshooting

### Common Issues

1. **"No admin users found"**
   - Solution: Create admin user with `create-admin` command

2. **"Invalid password hash format"**
   - Solution: Reset password to regenerate proper hash

3. **"User found but password invalid"**
   - Solution: Reset password or check for typos

4. **"Database connection error"**
   - Solution: Check database configuration and connectivity

5. **"Orphaned sessions found"**
   - Solution: Run cleanup command to remove invalid sessions

### Getting Help

For additional help:

1. Run tools with `--help` flag for usage information
2. Check log files for detailed error messages
3. Run integrity check to identify specific issues
4. Use interactive menu for guided operations

## Dependencies

The tools require these Python packages (already in requirements.txt):

- `sqlalchemy` - Database operations
- `bcrypt` - Password hashing
- `tabulate` - Formatted output tables
- `pytest` - Testing framework

## Conclusion

These admin user verification and credential management tools provide a comprehensive solution for managing admin users and troubleshooting authentication issues. They address all requirements while providing both simple utilities for common tasks and comprehensive tools for detailed analysis and maintenance.