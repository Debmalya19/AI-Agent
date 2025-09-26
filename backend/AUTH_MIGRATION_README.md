# Authentication Migration System

This document describes the comprehensive authentication migration system that migrates from the legacy User/UserSession authentication to the unified authentication system.

## Overview

The authentication migration system addresses the critical authentication issues in the AI Agent application by consolidating conflicting authentication systems into a single, unified approach. The main problem was that the application had two authentication systems running simultaneously: the legacy system in `main.py` using the `User` model, and the newer unified authentication system using `UnifiedUser` model.

## Requirements Addressed

- **1.3**: Consistent authentication method across all endpoints
- **3.1**: Single user model for authentication  
- **3.2**: Proper data migration to unified system
- **4.1, 4.2, 4.3**: Preserve existing user account data and sessions

## Components

### 1. Core Migration System (`auth_migration_system.py`)

The main migration engine that handles:
- Data migration from legacy User table to UnifiedUser table
- Password hash format validation and migration
- Session migration from UserSession to UnifiedUserSession
- Comprehensive backup creation
- Transaction management and rollback support

**Key Classes:**
- `AuthMigrationSystem`: Main migration orchestrator
- `MigrationConfig`: Configuration for migration process
- `MigrationStats`: Statistics and progress tracking
- `PasswordHashMigrator`: Password hash format handling

### 2. Migration Validator (`auth_migration_validator.py`)

Comprehensive validation system that ensures:
- Pre-migration data integrity validation
- Post-migration verification
- Migration completeness checking
- Data consistency validation between legacy and unified systems

**Key Classes:**
- `AuthMigrationValidator`: Main validation engine
- Validation functions for different migration phases

### 3. Rollback System (`auth_migration_rollback.py`)

Safe rollback functionality that provides:
- Complete migration rollback capability
- Backup validation before rollback
- Data preservation options
- Rollback verification and reporting

**Key Classes:**
- `AuthMigrationRollback`: Rollback orchestrator
- `RollbackStats`: Rollback statistics tracking

### 4. CLI Interface (`run_auth_migration.py`)

Command-line interface for:
- Running migrations with various options
- Validation at different phases
- Rollback operations
- Status checking and reporting

## Migration Process

### Phase 1: Pre-Migration Validation
- Validates legacy user data integrity
- Checks for duplicate users/emails
- Validates password hash formats
- Identifies potential migration issues

### Phase 2: Backup Creation
- Creates timestamped backup of all authentication data
- Exports users and sessions to JSON format
- Stores backup metadata for rollback operations

### Phase 3: User Migration
- Migrates users from legacy User table to UnifiedUser table
- Handles password hash format consistency
- Maps legacy user IDs to unified user IDs
- Preserves all user attributes and metadata

### Phase 4: Session Migration
- Migrates active sessions to unified session table
- Updates foreign key references
- Preserves session expiration and metadata

### Phase 5: Post-Migration Validation
- Verifies migration completeness
- Validates data integrity
- Checks for orphaned records
- Confirms password hash compatibility

### Phase 6: Finalization
- Generates migration report
- Updates migration tracking fields
- Cleans up temporary data

## Usage

### Basic Migration

```bash
# Check current status
python backend/run_auth_migration.py status

# Run migration with backup (recommended)
python backend/run_auth_migration.py migrate --backup

# Run migration without backup (faster, but riskier)
python backend/run_auth_migration.py migrate --no-backup

# Dry run to see what would be migrated
python backend/run_auth_migration.py migrate --dry-run
```

### Validation

```bash
# Validate before migration
python backend/run_auth_migration.py validate --pre-migration

# Validate after migration
python backend/run_auth_migration.py validate --post-migration

# Check migration integrity
python backend/run_auth_migration.py validate --integrity
```

### Rollback

```bash
# Rollback migration (requires backup path)
python backend/run_auth_migration.py rollback --backup-path ./backups/auth_migration_backup_20241217_143022

# Rollback with unified data preservation
python backend/run_auth_migration.py rollback --backup-path ./backups/auth_migration_backup_20241217_143022 --preserve
```

### Programmatic Usage

```python
from backend.auth_migration_system import run_authentication_migration

# Simple migration
stats = run_authentication_migration(
    backup_enabled=True,
    validate_before=True,
    validate_after=True
)

# Advanced migration with custom config
from backend.auth_migration_system import AuthMigrationSystem, MigrationConfig

config = MigrationConfig(
    backup_enabled=True,
    validate_before_migration=True,
    validate_after_migration=True,
    force_bcrypt_rehash=False,
    dry_run=False
)

migration_system = AuthMigrationSystem(config)
stats = migration_system.run_migration()
```

## Configuration Options

### MigrationConfig Parameters

- `backup_enabled`: Create backup before migration (default: True)
- `backup_directory`: Directory for backup files (default: "backups")
- `validate_before_migration`: Run pre-migration validation (default: True)
- `validate_after_migration`: Run post-migration validation (default: True)
- `preserve_legacy_tables`: Keep legacy tables after migration (default: True)
- `batch_size`: Batch size for processing records (default: 100)
- `session_expiry_hours`: Default session expiry for new sessions (default: 24)
- `force_bcrypt_rehash`: Force rehashing of all passwords to bcrypt (default: False)
- `dry_run`: Run without making actual changes (default: False)

## Password Hash Migration

The system handles different password hash formats:

### Supported Formats
- **bcrypt**: `$2b$` or `$2a$` prefixed hashes (recommended)
- **SHA256**: 64-character hexadecimal hashes (legacy support)

### Migration Strategy
- bcrypt hashes are preserved as-is (already secure)
- SHA256 hashes are kept but flagged for eventual rehashing
- Unknown formats are rejected with validation errors

### Security Considerations
- Original passwords cannot be recovered from SHA256 hashes
- Users with SHA256 hashes will need to reset passwords for bcrypt conversion
- All new passwords are automatically hashed with bcrypt

## Data Mapping

### User Migration Mapping

| Legacy User Field | Unified User Field | Notes |
|------------------|-------------------|-------|
| `id` | `legacy_customer_id` | Stored for reference |
| `user_id` | `user_id` | Direct mapping |
| `username` | `username` | Direct mapping |
| `email` | `email` | Direct mapping |
| `password_hash` | `password_hash` | Format validated |
| `full_name` | `full_name` | Direct mapping |
| `is_active` | `is_active` | Direct mapping |
| `is_admin` | `is_admin` | Direct mapping |
| `is_admin` | `role` | Mapped to UserRole enum |
| `created_at` | `created_at` | Direct mapping |
| `updated_at` | `updated_at` | Direct mapping |

### Session Migration Mapping

| Legacy Session Field | Unified Session Field | Notes |
|---------------------|----------------------|-------|
| `session_id` | `session_id` | Direct mapping |
| `user_id` | `user_id` | Mapped to unified user ID |
| `token_hash` | `token_hash` | Direct mapping |
| `created_at` | `created_at` | Direct mapping |
| `expires_at` | `expires_at` | Direct mapping |
| `last_accessed` | `last_accessed` | Direct mapping |
| `is_active` | `is_active` | Direct mapping |

## Error Handling

### Migration Errors
- **Validation Failures**: Pre-migration validation errors prevent migration
- **Data Integrity Issues**: Duplicate users, invalid formats, missing fields
- **Database Errors**: Connection issues, constraint violations
- **Backup Failures**: Insufficient disk space, permission issues

### Recovery Strategies
- **Automatic Rollback**: On critical failures, automatic rollback to backup
- **Manual Rollback**: Use CLI rollback command with backup path
- **Partial Recovery**: Fix specific issues and re-run migration
- **Data Repair**: Use validation tools to identify and fix data issues

## Monitoring and Logging

### Log Levels
- **INFO**: General migration progress and statistics
- **WARNING**: Non-critical issues that don't stop migration
- **ERROR**: Critical issues that may cause migration failure
- **DEBUG**: Detailed information for troubleshooting

### Key Metrics Tracked
- Users migrated successfully
- Sessions migrated successfully
- Password hashes converted
- Validation errors and warnings
- Migration duration
- Backup size and location

## Testing

### Test Coverage
- Unit tests for all migration components
- Integration tests for complete migration workflows
- Validation tests for data integrity
- Rollback tests for recovery scenarios
- Performance tests for large datasets

### Running Tests

```bash
# Run all migration tests
python -m pytest backend/test_auth_migration.py -v

# Run specific test categories
python -m pytest backend/test_auth_migration.py::TestPasswordHashMigrator -v
python -m pytest backend/test_auth_migration.py::TestAuthMigrationSystem -v
```

## Troubleshooting

### Common Issues

#### 1. Duplicate User Data
**Problem**: Multiple users with same email/username
**Solution**: 
```bash
python backend/run_auth_migration.py validate --pre-migration
# Fix duplicates manually, then re-run migration
```

#### 2. Invalid Password Hashes
**Problem**: Unsupported password hash formats
**Solution**:
```bash
# Identify invalid hashes
python backend/run_auth_migration.py validate --pre-migration
# Users with invalid hashes need password reset
```

#### 3. Migration Stuck/Failed
**Problem**: Migration fails partway through
**Solution**:
```bash
# Check status
python backend/run_auth_migration.py status

# Rollback if needed
python backend/run_auth_migration.py rollback --backup-path <backup_path>

# Fix issues and retry
python backend/run_auth_migration.py migrate
```

#### 4. Backup Issues
**Problem**: Cannot create or access backup
**Solution**:
```bash
# Check disk space and permissions
ls -la backups/

# Run without backup (not recommended)
python backend/run_auth_migration.py migrate --no-backup
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
python backend/run_auth_migration.py migrate --log-level DEBUG --log-file migration.log
```

## Security Considerations

### Data Protection
- All backups contain sensitive password hashes
- Backup files should be stored securely and encrypted
- Access to migration tools should be restricted
- Migration logs may contain sensitive information

### Password Security
- bcrypt is the recommended hash format
- SHA256 hashes are supported but should be migrated to bcrypt
- Users should be encouraged to update passwords post-migration
- Failed login attempts should be monitored during transition

### Session Security
- Active sessions are preserved during migration
- Session tokens remain valid across migration
- Expired sessions are not migrated
- Session cleanup should be performed regularly

## Performance Considerations

### Large Datasets
- Use batch processing for large user bases
- Monitor memory usage during migration
- Consider running during low-traffic periods
- Test migration on staging environment first

### Optimization Tips
- Disable unnecessary validation for trusted data
- Use dry-run mode to estimate migration time
- Increase batch size for better performance
- Ensure adequate disk space for backups

## Post-Migration Steps

### 1. Update Application Code
- Update main.py to use unified authentication
- Replace legacy User model imports with UnifiedUser
- Update authentication middleware
- Test all authentication endpoints

### 2. Verify System Operation
- Test user login functionality
- Verify admin dashboard access
- Check session management
- Validate password changes

### 3. Monitor System Health
- Watch for authentication errors
- Monitor login success rates
- Check session creation/validation
- Review security logs

### 4. Clean Up (Optional)
- Remove legacy authentication tables (after verification)
- Clean up old backup files
- Update documentation
- Train support staff on new system

## Support and Maintenance

### Regular Tasks
- Monitor migration logs for issues
- Clean up old backup files
- Update password hash formats
- Review authentication metrics

### Emergency Procedures
- Keep recent backups available
- Document rollback procedures
- Maintain emergency contact list
- Test disaster recovery plans

## Version History

- **v1.0**: Initial migration system implementation
- **v1.1**: Added rollback functionality
- **v1.2**: Enhanced validation and error handling
- **v1.3**: Added CLI interface and comprehensive testing

## Related Documentation

- [Unified Authentication System](./UNIFIED_AUTH_README.md)
- [Database Models](./UNIFIED_MODELS_README.md)
- [Admin Dashboard Integration](./ADMIN_INTEGRATION_README.md)
- [Security Guidelines](./SECURITY_README.md)

## Contact

For issues or questions regarding the authentication migration system:
- Review this documentation
- Check the troubleshooting section
- Run validation tools to identify issues
- Consult the test suite for usage examples