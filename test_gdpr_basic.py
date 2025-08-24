#!/usr/bin/env python3
"""
Basic test for GDPR compliance functionality
"""

from security_manager import SecurityManager
from privacy_utils import PrivacyUtils
from gdpr_compliance import GDPRComplianceManager, DataSubjectRightType

def test_consent_management():
    """Test consent recording and management"""
    print("Testing consent management...")
    
    security_manager = SecurityManager()
    privacy_utils = PrivacyUtils()
    gdpr_manager = GDPRComplianceManager(security_manager, privacy_utils)
    
    user_id = "test_user_123"
    purpose = "conversation_memory"
    
    # Record consent
    consent_id = gdpr_manager.record_consent(user_id, purpose, True)
    print(f"Consent recorded: {consent_id}")
    
    # Check consent
    has_consent = gdpr_manager.check_consent(user_id, purpose)
    print(f"Has consent: {has_consent}")
    
    # Withdraw consent
    withdrawal_success = gdpr_manager.withdraw_consent(user_id, consent_id)
    print(f"Consent withdrawn: {withdrawal_success}")
    
    # Check consent after withdrawal
    has_consent_after = gdpr_manager.check_consent(user_id, purpose)
    print(f"Has consent after withdrawal: {has_consent_after}")
    
    if has_consent and withdrawal_success and not has_consent_after:
        print("✓ Consent management test passed!")
        return True
    else:
        print("✗ Consent management test failed!")
        return False

def test_data_subject_requests():
    """Test data subject rights requests"""
    print("\nTesting data subject requests...")
    
    security_manager = SecurityManager()
    privacy_utils = PrivacyUtils()
    gdpr_manager = GDPRComplianceManager(security_manager, privacy_utils)
    
    user_id = "test_user_456"
    
    # Submit access request
    access_request_id = gdpr_manager.submit_data_subject_request(
        user_id, DataSubjectRightType.ACCESS
    )
    print(f"Access request submitted: {access_request_id}")
    
    # Submit erasure request
    erasure_request_id = gdpr_manager.submit_data_subject_request(
        user_id, DataSubjectRightType.ERASURE
    )
    print(f"Erasure request submitted: {erasure_request_id}")
    
    # Check requests exist
    access_request = gdpr_manager._data_requests.get(access_request_id)
    erasure_request = gdpr_manager._data_requests.get(erasure_request_id)
    
    access_valid = (access_request and 
                   access_request.user_id == user_id and 
                   access_request.request_type == DataSubjectRightType.ACCESS)
    
    erasure_valid = (erasure_request and 
                    erasure_request.user_id == user_id and 
                    erasure_request.request_type == DataSubjectRightType.ERASURE)
    
    if access_valid and erasure_valid:
        print("✓ Data subject requests test passed!")
        return True
    else:
        print("✗ Data subject requests test failed!")
        return False

def test_privacy_report():
    """Test privacy report generation"""
    print("\nTesting privacy report generation...")
    
    privacy_utils = PrivacyUtils()
    
    test_data = {
        "user_message": "My email is john@example.com and phone is 555-1234",
        "user_info": {
            "contact": "user@example.com",
            "address": "123 Main Street"
        },
        "metadata": {
            "ip": "192.168.1.1",
            "session": "session_123"
        }
    }
    
    report = privacy_utils.create_privacy_report(test_data)
    
    print(f"Fields analyzed: {report['total_fields_analyzed']}")
    print(f"PII detections: {len(report['pii_detections'])}")
    print(f"Privacy score: {report['privacy_score']:.2f}")
    print(f"Recommendations: {len(report['recommendations'])}")
    
    has_detections = len(report['pii_detections']) > 0
    has_recommendations = len(report['recommendations']) > 0
    has_score = 'privacy_score' in report
    
    if has_detections and has_recommendations and has_score:
        print("✓ Privacy report test passed!")
        return True
    else:
        print("✗ Privacy report test failed!")
        return False

def test_data_anonymization():
    """Test data anonymization for logging"""
    print("\nTesting data anonymization...")
    
    privacy_utils = PrivacyUtils()
    
    sensitive_data = {
        "user_id": "user_12345",
        "user_message": "My email is john@example.com",
        "session_id": "session_67890",
        "metadata": {
            "ip_address": "192.168.1.100",
            "phone": "555-123-4567"
        }
    }
    
    anonymized = privacy_utils.anonymize_conversation_data(sensitive_data)
    
    print(f"Original user_id: {sensitive_data['user_id']}")
    print(f"Anonymized user_id: {anonymized['user_id']}")
    print(f"Original message: {sensitive_data['user_message']}")
    print(f"Anonymized message: {anonymized['user_message']}")
    
    user_id_changed = anonymized['user_id'] != sensitive_data['user_id']
    email_removed = "john@example.com" not in anonymized['user_message']
    
    if user_id_changed and email_removed:
        print("✓ Data anonymization test passed!")
        return True
    else:
        print("✗ Data anonymization test failed!")
        return False

if __name__ == "__main__":
    print("Running basic GDPR compliance tests...\n")
    
    results = []
    results.append(test_consent_management())
    results.append(test_data_subject_requests())
    results.append(test_privacy_report())
    results.append(test_data_anonymization())
    
    print(f"\nTest Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All GDPR tests passed!")
    else:
        print("❌ Some GDPR tests failed!")