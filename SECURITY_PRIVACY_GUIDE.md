# Security and Privacy Features Guide

This guide explains how to use the security and privacy features implemented in the memory layer system.

## Overview

The security and privacy implementation includes:

- **Data Encryption**: Field-level encryption for sensitive conversation data
- **Access Control**: User-based permissions and session validation
- **Privacy Protection**: PII detection, anonymization, and data sanitization
- **GDPR Compliance**: Consent management, data subject rights, and retention policies
- **Security Monitoring**: Audit logging and access tracking

## Components

### 1. SecurityManager

Handles encryption, access control, and security monitoring.

```python
from security_manager import SecurityManager, EncryptionConfig, AccessControlPolicy

# Configure encryption
config = EncryptionConfig(
    enable_field_level_encryption=True,
    encrypted_fields=["user_message", "bot_response", "context_data"]
)

# Initialize security manager
security_manager = SecurityManager(config)

# Encrypt sensitive data
encrypted = security_manager.encrypt_data("sensitive text", "user_123")
decrypted = security_manager.decrypt_data(encrypted)

# Set access control policy
policy = AccessControlPolicy(
    user_id="user_123",
    allowed_operations=["read", "write", "export"],
    data_retention_days=365
)
security_manager.set_access_policy("user_123", policy)
```

### 2. PrivacyUtils

Provides PII detection, anonymization, and privacy analysis.

```python
from privacy_utils import PrivacyUtils, AnonymizationConfig

# Configure anonymization
config = AnonymizationConfig(
    preserve_structure=True,
    hash_identifiers=True,
    redact_pii=True
)

# Initialize privacy utils
privacy_utils = PrivacyUtils(config)

# Detect PII in text
text = "Contact me at john@example.com or 555-1234"
pii_detected = privacy_utils.detect_pii(text)

# Anonymize text
anonymized = privacy_utils.anonymize_text(text)

# Generate privacy report
report = privacy_utils.create_privacy_report(data)
```

### 3. GDPRComplianceManager

Manages GDPR compliance including consent and data subject rights.

```python
from gdpr_compliance import GDPRComplianceManager, DataSubjectRightType

# Initialize GDPR manager
gdpr_manager = GDPRComplianceManager(security_manager, privacy_utils)

# Record user consent
consent_id = gdpr_manager.record_consent(
    "user_123", "conversation_memory", consent_given=True
)

# Submit data subject request
request_id = gdpr_manager.submit_data_subject_request(
    "user_123", DataSubjectRightType.ACCESS
)

# Process access request (requires database session)
exported_data = gdpr_manager.process_access_request(request_id, db_session)
```

## Usage Examples

### Secure Conversation Storage

```python
from memory_models import ConversationEntry
from security_integration import SecureMemoryLayerManager

# Create secure memory manager
secure_memory = SecureMemoryLayerManager(memory_manager)

# Store conversation securely
conversation = ConversationEntry(
    session_id="session_123",
    user_id="user_123",
    user_message="Hello, my email is john@example.com",
    bot_response="Hello! How can I help you?"
)

success = secure_memory.store_conversation_secure(conversation, db_session)
```

### User Data Export (GDPR Article 15)

```python
# Export user data for GDPR compliance
exported_data = secure_memory.export_user_data_secure(
    "user_123", db_session, request_format="json"
)

# The exported data includes:
# - All conversation history (decrypted)
# - User sessions
# - Context cache
# - Consent records
# - Processing information
```

### Data Erasure (Right to be Forgotten)

```python
# Delete user data for GDPR compliance
deletion_result = secure_memory.delete_user_data_secure(
    "user_123", db_session, hard_delete=True
)

# Returns summary of deleted records by type
print(deletion_result["deletion_summary"])
```

### Privacy-Safe Logging

```python
# Sanitize data before logging
sensitive_data = {
    "user_message": "My email is john@example.com",
    "user_id": "user_123",
    "session_id": "session_456"
}

sanitized = privacy_utils.sanitize_for_logging(sensitive_data)
logger.info(f"User interaction: {sanitized}")
```

## Database Schema Updates

The security features require additional database fields. Run the migration:

```python
from security_migration import run_security_migration

# Run migration to add security fields
run_security_migration()
```

### New Tables Created

1. **user_sessions**: Session management with security features
2. **data_processing_consent**: GDPR consent records
3. **data_subject_rights**: Data subject rights requests

### Enhanced Existing Tables

1. **enhanced_chat_history**: Added encryption and privacy fields
2. **memory_context_cache**: Added encryption and access control fields

## Configuration

### Environment Variables

Set the encryption key in your environment:

```bash
export MEMORY_ENCRYPTION_KEY="your-base64-encoded-key-here"
```

If not set, a new key will be generated automatically (not recommended for production).

### Encryption Configuration

```python
encryption_config = EncryptionConfig(
    key_derivation_iterations=100000,  # PBKDF2 iterations
    salt_length=32,                    # Salt length in bytes
    enable_field_level_encryption=True,
    encrypted_fields=["user_message", "bot_response", "context_data"]
)
```

### Privacy Configuration

```python
anonymization_config = AnonymizationConfig(
    preserve_structure=True,      # Keep text structure when anonymizing
    hash_identifiers=True,        # Hash user IDs consistently
    redact_pii=True,             # Remove PII from text
    anonymize_timestamps=False,   # Whether to fuzz timestamps
    keep_statistical_properties=True
)
```

## Security Best Practices

### 1. Key Management

- Use a secure key management system in production
- Rotate encryption keys regularly
- Store keys separately from encrypted data
- Use environment variables or secure vaults for key storage

### 2. Access Control

- Implement principle of least privilege
- Validate user sessions before data access
- Log all data access attempts
- Use role-based access control where appropriate

### 3. Data Classification

- Classify data based on sensitivity (public, internal, confidential, restricted)
- Apply appropriate security controls based on classification
- Document data flows and processing purposes

### 4. Privacy Protection

- Minimize data collection to what's necessary
- Anonymize or pseudonymize data when possible
- Implement data retention policies
- Provide clear privacy notices to users

### 5. GDPR Compliance

- Obtain explicit consent for data processing
- Implement all data subject rights
- Maintain records of processing activities
- Conduct privacy impact assessments

## Monitoring and Auditing

### Security Events

The system logs security events including:

- Data access attempts (successful and failed)
- Permission checks
- Encryption/decryption operations
- GDPR request processing
- Consent changes

### Audit Log Format

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "user_id": "hashed_user_id",
  "operation": "read",
  "resource": "conversation",
  "success": true,
  "details": {
    "query_hash": "abc123",
    "results_count": 5
  }
}
```

### Compliance Reporting

Generate compliance reports:

```python
# Generate comprehensive privacy report
report = secure_memory.generate_privacy_report(db_session)

# Includes:
# - GDPR compliance metrics
# - Memory system statistics
# - Privacy analysis
# - Security metrics
```

## Testing

Run the security tests to verify functionality:

```bash
# Basic security tests
python test_security_basic.py

# GDPR compliance tests
python test_gdpr_basic.py

# Comprehensive demonstration
python security_example.py

# Full test suite (requires pytest)
python -m pytest test_security_privacy.py -v
```

## Troubleshooting

### Common Issues

1. **Encryption Key Not Found**
   - Set the `MEMORY_ENCRYPTION_KEY` environment variable
   - Or allow the system to generate a new key (development only)

2. **Database Migration Errors**
   - Ensure database user has ALTER TABLE permissions
   - Check for existing columns before migration
   - Review migration logs for specific errors

3. **PII Detection False Positives**
   - Adjust PII patterns in `privacy_utils.py`
   - Configure confidence thresholds
   - Add custom patterns for domain-specific data

4. **Performance Issues**
   - Enable database indexing for security fields
   - Use caching for frequently accessed encrypted data
   - Consider async processing for large data operations

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration with Existing Code

### Memory Layer Manager Integration

```python
from memory_layer_manager import MemoryLayerManager
from security_integration import SecureMemoryLayerManager

# Wrap existing memory manager with security
base_memory_manager = MemoryLayerManager(config)
secure_memory_manager = SecureMemoryLayerManager(base_memory_manager)

# Use secure manager instead of base manager
secure_memory_manager.store_conversation_secure(conversation, db_session)
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from security_integration import SecureMemoryLayerManager

app = FastAPI()

@app.post("/chat")
async def chat_endpoint(
    message: str,
    user_id: str = Depends(get_current_user),
    secure_memory: SecureMemoryLayerManager = Depends(get_secure_memory)
):
    # Check user consent
    if not secure_memory.gdpr_manager.check_consent(user_id, "conversation_memory"):
        raise HTTPException(403, "Consent required for conversation storage")
    
    # Process chat with security
    # ... chat processing logic ...
    
    # Store securely
    success = secure_memory.store_conversation_secure(conversation, db_session)
    return {"success": success}
```

## Compliance Checklist

- [ ] Encryption keys properly managed
- [ ] User consent obtained and recorded
- [ ] Access control policies implemented
- [ ] Data retention policies configured
- [ ] PII detection and anonymization enabled
- [ ] Audit logging configured
- [ ] Data subject rights endpoints implemented
- [ ] Privacy notices provided to users
- [ ] Security testing completed
- [ ] Compliance reporting configured

## Support

For questions or issues with the security and privacy features:

1. Check the troubleshooting section above
2. Review the test files for usage examples
3. Run the demonstration script to verify functionality
4. Check audit logs for security events
5. Consult the GDPR compliance documentation