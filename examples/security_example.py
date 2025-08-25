#!/usr/bin/env python3
"""
Comprehensive example of security and privacy features in the memory layer
"""

import os
import json
from datetime import datetime
from security_manager import SecurityManager, EncryptionConfig, AccessControlPolicy
from privacy_utils import PrivacyUtils, AnonymizationConfig
from gdpr_compliance import GDPRComplianceManager, DataSubjectRightType

def setup_security_environment():
    """Set up the security environment with proper configuration"""
    print("🔧 Setting up security environment...")
    
    # Configure encryption
    encryption_config = EncryptionConfig(
        key_derivation_iterations=100000,
        enable_field_level_encryption=True,
        encrypted_fields=["user_message", "bot_response", "context_data"]
    )
    
    # Configure anonymization
    anonymization_config = AnonymizationConfig(
        preserve_structure=True,
        hash_identifiers=True,
        redact_pii=True,
        anonymize_timestamps=False
    )
    
    # Initialize security components
    security_manager = SecurityManager(encryption_config)
    privacy_utils = PrivacyUtils(anonymization_config)
    gdpr_manager = GDPRComplianceManager(security_manager, privacy_utils)
    
    print("✅ Security environment configured")
    return security_manager, privacy_utils, gdpr_manager

def demonstrate_user_onboarding(security_manager, gdpr_manager):
    """Demonstrate secure user onboarding with consent management"""
    print("\n👤 Demonstrating user onboarding...")
    
    user_id = "demo_user_001"
    
    # Set up access control policy
    policy = AccessControlPolicy(
        user_id=user_id,
        allowed_operations=["read", "write", "export"],
        data_retention_days=365,
        can_export_data=True,
        can_delete_data=True,
        session_timeout_minutes=60
    )
    security_manager.set_access_policy(user_id, policy)
    print(f"✅ Access policy set for user {user_id}")
    
    # Record user consent for various purposes
    purposes = [
        "conversation_memory",
        "context_enhancement", 
        "service_improvement",
        "analytics"
    ]
    
    consent_ids = []
    for purpose in purposes:
        consent_id = gdpr_manager.record_consent(
            user_id, purpose, consent_given=True, 
            consent_method="web_form", consent_version="1.0"
        )
        consent_ids.append(consent_id)
        print(f"✅ Consent recorded for {purpose}: {consent_id}")
    
    return user_id, consent_ids

def demonstrate_secure_conversation_storage(security_manager, privacy_utils, user_id):
    """Demonstrate secure conversation storage with encryption"""
    print(f"\n💬 Demonstrating secure conversation storage for {user_id}...")
    
    # Sample conversation with PII
    conversation_data = {
        "user_id": user_id,
        "session_id": "session_demo_001",
        "user_message": "Hi, I need help with my account. My email is john.doe@example.com and my phone is 555-123-4567",
        "bot_response": "Hello! I'd be happy to help you with your account. I can see your contact information and will assist you.",
        "tools_used": ["account_lookup", "contact_verification"],
        "tool_performance": {"account_lookup": 0.95, "contact_verification": 0.88},
        "context_used": ["previous_conversation", "user_preferences"],
        "response_quality_score": 0.92,
        "timestamp": datetime.utcnow()
    }
    
    print("📝 Original conversation data:")
    print(f"  User message: {conversation_data['user_message'][:50]}...")
    print(f"  Bot response: {conversation_data['bot_response'][:50]}...")
    
    # Encrypt sensitive conversation data
    encrypted_data = security_manager.encrypt_conversation_data(
        conversation_data, user_id
    )
    
    print("🔒 Encrypted conversation data:")
    print(f"  Encrypted fields: {[k for k in encrypted_data.keys() if 'encrypted' in k]}")
    print(f"  Preserved fields: {[k for k in encrypted_data.keys() if 'encrypted' not in k]}")
    
    # Demonstrate decryption
    decrypted_data = security_manager.decrypt_conversation_data(encrypted_data)
    print("🔓 Successfully decrypted conversation data")
    
    return encrypted_data

def demonstrate_privacy_protection(privacy_utils, user_id):
    """Demonstrate privacy protection and PII handling"""
    print(f"\n🛡️ Demonstrating privacy protection for {user_id}...")
    
    # Sample data with various types of PII
    sensitive_data = {
        "user_message": "My details: email john.doe@company.com, phone 555-987-6543, SSN 123-45-6789",
        "user_info": {
            "address": "123 Main Street, Anytown",
            "credit_card": "4532-1234-5678-9012",
            "ip_address": "192.168.1.100"
        },
        "session_metadata": {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "referrer": "https://example.com/login"
        }
    }
    
    # Detect PII
    pii_detections = privacy_utils.detect_pii(sensitive_data["user_message"])
    print(f"🔍 PII detected: {len(pii_detections)} items")
    for pii in pii_detections:
        print(f"  - {pii['type']}: {pii['value']}")
    
    # Generate privacy report
    privacy_report = privacy_utils.create_privacy_report(sensitive_data)
    print(f"📊 Privacy analysis:")
    print(f"  - Fields analyzed: {privacy_report['total_fields_analyzed']}")
    print(f"  - PII detections: {len(privacy_report['pii_detections'])}")
    print(f"  - Privacy score: {privacy_report['privacy_score']:.2f}")
    print(f"  - Recommendations: {len(privacy_report['recommendations'])}")
    
    # Anonymize for logging
    anonymized_data = privacy_utils.sanitize_for_logging(sensitive_data)
    print("🎭 Anonymized data for logging:")
    print(f"  - Original message: {sensitive_data['user_message'][:50]}...")
    print(f"  - Anonymized message: {anonymized_data['user_message'][:50]}...")
    
    return privacy_report

def demonstrate_gdpr_compliance(gdpr_manager, user_id):
    """Demonstrate GDPR compliance features"""
    print(f"\n⚖️ Demonstrating GDPR compliance for {user_id}...")
    
    # Submit data access request
    access_request_id = gdpr_manager.submit_data_subject_request(
        user_id, DataSubjectRightType.ACCESS,
        {"format": "json", "include_metadata": True}
    )
    print(f"📋 Data access request submitted: {access_request_id}")
    
    # Submit data portability request
    portability_request_id = gdpr_manager.submit_data_subject_request(
        user_id, DataSubjectRightType.DATA_PORTABILITY,
        {"format": "json", "structured": True}
    )
    print(f"📦 Data portability request submitted: {portability_request_id}")
    
    # Check request status
    access_request = gdpr_manager._data_requests[access_request_id]
    portability_request = gdpr_manager._data_requests[portability_request_id]
    
    print(f"📊 Request statuses:")
    print(f"  - Access request: {access_request.status.value}")
    print(f"  - Portability request: {portability_request.status.value}")
    
    # Generate compliance report
    compliance_report = gdpr_manager.generate_compliance_report(None)  # No DB session for demo
    print(f"📈 Compliance metrics:")
    print(f"  - Total requests: {compliance_report['data_subject_requests']['total']}")
    print(f"  - Users with consent: {compliance_report['consent_management']['total_users_with_consent']}")
    print(f"  - Active consents: {compliance_report['consent_management']['active_consents']}")
    
    return compliance_report

def demonstrate_security_monitoring(security_manager, user_id):
    """Demonstrate security monitoring and audit logging"""
    print(f"\n📊 Demonstrating security monitoring for {user_id}...")
    
    # Simulate various security events
    security_events = [
        ("read", "conversation", True, {"query_type": "context_search"}),
        ("write", "conversation", True, {"encrypted": True, "pii_detected": True}),
        ("export", "user_data", True, {"format": "json", "size_mb": 2.5}),
        ("delete", "conversation", False, {"error": "insufficient_permissions"}),
    ]
    
    print("🔍 Audit log entries:")
    for operation, resource, success, details in security_events:
        security_manager.audit_data_access(
            user_id, operation, resource, success, details
        )
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  - {operation.upper()} {resource}: {status}")
    
    # Check access permissions
    permissions_to_check = ["read", "write", "export", "delete"]
    print(f"🔐 Access permissions for {user_id}:")
    for permission in permissions_to_check:
        has_permission = security_manager.check_access_permission(user_id, permission)
        status = "✅ ALLOWED" if has_permission else "❌ DENIED"
        print(f"  - {permission.upper()}: {status}")

def demonstrate_data_lifecycle_management(gdpr_manager, privacy_utils, user_id):
    """Demonstrate data lifecycle management and retention"""
    print(f"\n🔄 Demonstrating data lifecycle management for {user_id}...")
    
    # Simulate retention policy application
    print("📅 Applying retention policies...")
    retention_policies = gdpr_manager._retention_policies
    
    for policy in retention_policies[:3]:  # Show first 3 policies
        print(f"  - {policy.data_type}: {policy.retention_period_days} days")
        print(f"    Legal basis: {policy.legal_basis}")
        print(f"    Auto-delete: {policy.auto_delete}")
    
    # Demonstrate data anonymization
    print("🎭 Data anonymization process:")
    sample_old_data = {
        "user_message": "Hi, I'm John Doe from john.doe@company.com",
        "timestamp": "2023-01-15T10:30:00Z",
        "session_id": "old_session_12345"
    }
    
    anonymized = privacy_utils.anonymize_conversation_data(sample_old_data)
    print(f"  - Original: {sample_old_data['user_message']}")
    print(f"  - Anonymized: {anonymized['user_message']}")
    
    # Simulate consent withdrawal impact
    print("⚠️ Consent withdrawal simulation:")
    print("  - User withdraws consent for 'analytics'")
    print("  - System stops analytics data collection")
    print("  - Existing analytics data marked for deletion")

def main():
    """Main demonstration function"""
    print("🔐 Security and Privacy Features Demonstration")
    print("=" * 50)
    
    # Setup
    security_manager, privacy_utils, gdpr_manager = setup_security_environment()
    
    # User onboarding
    user_id, consent_ids = demonstrate_user_onboarding(security_manager, gdpr_manager)
    
    # Secure conversation storage
    encrypted_data = demonstrate_secure_conversation_storage(
        security_manager, privacy_utils, user_id
    )
    
    # Privacy protection
    privacy_report = demonstrate_privacy_protection(privacy_utils, user_id)
    
    # GDPR compliance
    compliance_report = demonstrate_gdpr_compliance(gdpr_manager, user_id)
    
    # Security monitoring
    demonstrate_security_monitoring(security_manager, user_id)
    
    # Data lifecycle management
    demonstrate_data_lifecycle_management(gdpr_manager, privacy_utils, user_id)
    
    print("\n" + "=" * 50)
    print("🎉 Security and Privacy Demonstration Complete!")
    print("\nKey Features Demonstrated:")
    print("✅ Data encryption and decryption")
    print("✅ PII detection and anonymization")
    print("✅ GDPR consent management")
    print("✅ Data subject rights handling")
    print("✅ Access control and permissions")
    print("✅ Security audit logging")
    print("✅ Data retention policies")
    print("✅ Privacy impact assessment")

if __name__ == "__main__":
    main()