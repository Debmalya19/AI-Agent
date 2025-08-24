"""
Comprehensive tests for security and privacy features
"""

import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from security_manager import SecurityManager, EncryptionConfig, AccessControlPolicy
from privacy_utils import PrivacyUtils, AnonymizationConfig, PIIPattern
from gdpr_compliance import (
    GDPRComplianceManager, DataSubjectRightType, RequestStatus,
    ConsentRecord, DataSubjectRequest, RetentionPolicy
)
from memory_models import Base, EnhancedChatHistory, UserSession, MemoryContextCache

class TestSecurityManager:
    """Test cases for SecurityManager"""
    
    @pytest.fixture
    def security_manager(self):
        """Create SecurityManager instance for testing"""
        config = EncryptionConfig(
            key_derivation_iterations=1000,  # Reduced for testing
            enable_field_level_encryption=True
        )
        return SecurityManager(config)
    
    @pytest.fixture
    def test_db_session(self):
        """Create test database session"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_encryption_setup(self, security_manager):
        """Test encryption key setup"""
        assert security_manager._encryption_key is not None
        assert len(security_manager._encryption_key) == 44  # Fernet key length
    
    def test_data_encryption_decryption(self, security_manager):
        """Test data encryption and decryption"""
        test_data = "This is sensitive user data with PII: john@example.com"
        user_id = "test_user_123"
        
        # Encrypt data
        encrypted = security_manager.encrypt_data(test_data, user_id)
        
        assert encrypted["encrypted"] is True
        assert encrypted["encrypted_data"] != test_data
        assert encrypted["salt"] != ""
        assert encrypted["encryption_version"] == "1.0"
        
        # Decrypt data
        decrypted = security_manager.decrypt_data(encrypted)
        assert decrypted == test_data
    
    def test_conversation_data_encryption(self, security_manager):
        """Test conversation data field-level encryption"""
        conversation_data = {
            "user_id": "test_user",
            "session_id": "session_123",
            "user_message": "Hello, my email is john@example.com",
            "bot_response": "Hello! I can help you with that.",
            "tools_used": ["email_tool"],
            "created_at": datetime.utcnow()
        }
        
        # Encrypt conversation data
        encrypted_data = security_manager.encrypt_conversation_data(
            conversation_data, "test_user"
        )
        
        # Check that sensitive fields are encrypted
        assert "user_message" not in encrypted_data
        assert "bot_response" not in encrypted_data
        assert "user_message_encrypted" in encrypted_data
        assert "bot_response_encrypted" in encrypted_data
        
        # Non-sensitive fields should remain
        assert encrypted_data["user_id"] == "test_user"
        assert encrypted_data["session_id"] == "session_123"
        
        # Decrypt conversation data
        decrypted_data = security_manager.decrypt_conversation_data(encrypted_data)
        
        assert decrypted_data["user_message"] == conversation_data["user_message"]
        assert decrypted_data["bot_response"] == conversation_data["bot_response"]
    
    def test_access_control_policy(self, security_manager):
        """Test access control policy management"""
        user_id = "test_user"
        policy = AccessControlPolicy(
            user_id=user_id,
            allowed_operations=["read", "write", "export"],
            data_retention_days=365,
            can_export_data=True,
            can_delete_data=False
        )
        
        # Set policy
        security_manager.set_access_policy(user_id, policy)
        
        # Check permissions
        assert security_manager.check_access_permission(user_id, "read") is True
        assert security_manager.check_access_permission(user_id, "write") is True
        assert security_manager.check_access_permission(user_id, "export") is True
        assert security_manager.check_access_permission(user_id, "delete") is False
    
    def test_session_validation(self, security_manager, test_db_session):
        """Test user session validation"""
        user_id = "test_user"
        session_id = "test_session"
        
        # Create user session
        user_session = UserSession(
            user_id=user_id,
            session_id=session_id,
            is_active=True,
            last_activity=datetime.utcnow()
        )
        test_db_session.add(user_session)
        test_db_session.commit()
        
        # Validate active session
        assert security_manager.validate_user_session(
            user_id, session_id, test_db_session
        ) is True
        
        # Test expired session
        user_session.last_activity = datetime.utcnow() - timedelta(hours=2)
        test_db_session.commit()
        
        assert security_manager.validate_user_session(
            user_id, session_id, test_db_session
        ) is False
    
    def test_data_anonymization_for_logging(self, security_manager):
        """Test data anonymization for logging"""
        sensitive_data = {
            "user_id": "user_123",
            "user_message": "My email is john@example.com and phone is 555-1234",
            "session_id": "session_456",
            "ip_address": "192.168.1.1"
        }
        
        anonymized = security_manager.anonymize_data_for_logging(sensitive_data)
        
        # Check that identifiers are hashed
        assert anonymized["user_id"] != sensitive_data["user_id"]
        assert len(anonymized["user_id"]) == 12  # Hash length
        
        # Check that sensitive content is anonymized
        assert "john@example.com" not in anonymized["user_message"]
        assert "555-1234" not in anonymized["user_message"]
    
    def test_user_data_export(self, security_manager, test_db_session):
        """Test user data export functionality"""
        user_id = "test_user"
        
        # Set export permission
        policy = AccessControlPolicy(
            user_id=user_id,
            allowed_operations=["read", "export"],
            can_export_data=True
        )
        security_manager.set_access_policy(user_id, policy)
        
        # Create test data
        chat_history = EnhancedChatHistory(
            user_id=user_id,
            session_id="session_123",
            user_message="Test message",
            bot_response="Test response",
            created_at=datetime.utcnow()
        )
        test_db_session.add(chat_history)
        test_db_session.commit()
        
        # Export data
        exported_data = security_manager.export_user_data(user_id, test_db_session)
        
        assert exported_data["user_id"] == user_id
        assert "export_timestamp" in exported_data
        assert "chat_history" in exported_data
        assert len(exported_data["chat_history"]) == 1
        assert exported_data["chat_history"][0]["user_message"] == "Test message"
    
    def test_user_data_deletion(self, security_manager, test_db_session):
        """Test user data deletion functionality"""
        user_id = "test_user"
        
        # Set delete permission
        policy = AccessControlPolicy(
            user_id=user_id,
            allowed_operations=["read", "delete"],
            can_delete_data=True
        )
        security_manager.set_access_policy(user_id, policy)
        
        # Create test data
        chat_history = EnhancedChatHistory(
            user_id=user_id,
            session_id="session_123",
            user_message="Test message",
            bot_response="Test response",
            created_at=datetime.utcnow()
        )
        test_db_session.add(chat_history)
        test_db_session.commit()
        
        # Delete data
        deletion_counts = security_manager.delete_user_data(
            user_id, test_db_session, hard_delete=True
        )
        
        assert deletion_counts["chat_history"] == 1
        
        # Verify data is deleted
        remaining_chats = test_db_session.query(EnhancedChatHistory).filter(
            EnhancedChatHistory.user_id == user_id
        ).count()
        assert remaining_chats == 0

class TestPrivacyUtils:
    """Test cases for PrivacyUtils"""
    
    @pytest.fixture
    def privacy_utils(self):
        """Create PrivacyUtils instance for testing"""
        config = AnonymizationConfig(
            preserve_structure=True,
            hash_identifiers=True,
            redact_pii=True
        )
        return PrivacyUtils(config)
    
    def test_pii_detection(self, privacy_utils):
        """Test PII detection in text"""
        text = "Contact me at john.doe@example.com or call 555-123-4567"
        
        detected_pii = privacy_utils.detect_pii(text)
        
        assert len(detected_pii) == 2
        
        # Check email detection
        email_detection = next(
            (pii for pii in detected_pii if pii["type"] == "email"), None
        )
        assert email_detection is not None
        assert email_detection["value"] == "john.doe@example.com"
        
        # Check phone detection
        phone_detection = next(
            (pii for pii in detected_pii if pii["type"] == "phone"), None
        )
        assert phone_detection is not None
        assert "555-123-4567" in phone_detection["value"]
    
    def test_text_anonymization(self, privacy_utils):
        """Test text anonymization"""
        text = "My email is john@example.com and my phone is 555-1234"
        
        anonymized = privacy_utils.anonymize_text(text)
        
        assert "john@example.com" not in anonymized
        assert "555-1234" not in anonymized
        assert "[EMAIL]" in anonymized or "x" in anonymized
        assert "[PHONE]" in anonymized or "x" in anonymized
    
    def test_structured_replacement(self, privacy_utils):
        """Test structured replacement for PII"""
        # Test email structure preservation
        email_replacement = privacy_utils._create_structured_replacement(
            "john.doe@example.com", "email"
        )
        assert "@" in email_replacement
        assert email_replacement.count("x") > 0
        
        # Test phone structure preservation
        phone_replacement = privacy_utils._create_structured_replacement(
            "555-123-4567", "phone"
        )
        assert "-" in phone_replacement
        assert phone_replacement == "xxx-xxx-xxxx"
    
    def test_identifier_hashing(self, privacy_utils):
        """Test consistent identifier hashing"""
        identifier = "user_12345"
        
        hash1 = privacy_utils.hash_identifier(identifier)
        hash2 = privacy_utils.hash_identifier(identifier)
        
        # Should be consistent
        assert hash1 == hash2
        assert len(hash1) == 12
        assert hash1 != identifier
    
    def test_conversation_data_anonymization(self, privacy_utils):
        """Test conversation data anonymization"""
        conversation_data = {
            "user_id": "user_123",
            "session_id": "session_456",
            "user_message": "My email is john@example.com",
            "bot_response": "I can help you with that",
            "context_used": ["Previous conversation about email setup"],
            "created_at": datetime.utcnow()
        }
        
        anonymized = privacy_utils.anonymize_conversation_data(conversation_data)
        
        # Check that identifiers are hashed
        assert anonymized["user_id"] != conversation_data["user_id"]
        assert anonymized["session_id"] != conversation_data["session_id"]
        
        # Check that PII is anonymized
        assert "john@example.com" not in anonymized["user_message"]
        
        # Check that context is anonymized
        assert isinstance(anonymized["context_used"], list)
        assert len(anonymized["context_used"]) == 1
    
    def test_privacy_report_generation(self, privacy_utils):
        """Test privacy report generation"""
        data = {
            "user_message": "Contact me at john@example.com or 555-1234",
            "user_info": {
                "email": "user@example.com",
                "phone": "555-5678"
            },
            "metadata": {
                "ip": "192.168.1.1",
                "session": "session_123"
            }
        }
        
        report = privacy_utils.create_privacy_report(data)
        
        assert "timestamp" in report
        assert "total_fields_analyzed" in report
        assert "pii_detections" in report
        assert "privacy_score" in report
        assert "recommendations" in report
        
        # Should detect multiple PII instances
        assert len(report["pii_detections"]) > 0
        
        # Should have recommendations if PII found
        if len(report["pii_detections"]) > 0:
            assert len(report["recommendations"]) > 0
    
    def test_logging_sanitization(self, privacy_utils):
        """Test data sanitization for logging"""
        sensitive_data = {
            "user_message": "My password is secret123",
            "auth_token": "bearer_token_12345",
            "user_info": {
                "email": "user@example.com",
                "password": "another_secret"
            },
            "large_list": list(range(20))  # Test list truncation
        }
        
        sanitized = privacy_utils.sanitize_for_logging(sensitive_data)
        
        # Check that sensitive keys are redacted
        assert sanitized["auth_token"] == "[REDACTED]"
        assert sanitized["user_info"]["password"] == "[REDACTED]"
        
        # Check that PII in messages is anonymized
        assert "user@example.com" not in str(sanitized["user_info"]["email"])
        
        # Check that large lists are truncated
        assert len(sanitized["large_list"]) <= 10

class TestGDPRCompliance:
    """Test cases for GDPR compliance"""
    
    @pytest.fixture
    def gdpr_manager(self):
        """Create GDPR compliance manager for testing"""
        security_manager = SecurityManager()
        privacy_utils = PrivacyUtils()
        return GDPRComplianceManager(security_manager, privacy_utils)
    
    @pytest.fixture
    def test_db_session(self):
        """Create test database session"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_consent_recording(self, gdpr_manager):
        """Test consent recording and management"""
        user_id = "test_user"
        purpose = "conversation_memory"
        
        # Record consent
        consent_id = gdpr_manager.record_consent(
            user_id, purpose, consent_given=True
        )
        
        assert consent_id is not None
        assert gdpr_manager.check_consent(user_id, purpose) is True
        
        # Withdraw consent
        withdrawal_success = gdpr_manager.withdraw_consent(user_id, consent_id)
        assert withdrawal_success is True
        assert gdpr_manager.check_consent(user_id, purpose) is False
    
    def test_data_subject_request_submission(self, gdpr_manager):
        """Test data subject request submission"""
        user_id = "test_user"
        
        # Submit access request
        request_id = gdpr_manager.submit_data_subject_request(
            user_id, DataSubjectRightType.ACCESS
        )
        
        assert request_id is not None
        assert request_id in gdpr_manager._data_requests
        
        request = gdpr_manager._data_requests[request_id]
        assert request.user_id == user_id
        assert request.request_type == DataSubjectRightType.ACCESS
        assert request.status == RequestStatus.PENDING
    
    def test_access_request_processing(self, gdpr_manager, test_db_session):
        """Test processing of data access requests"""
        user_id = "test_user"
        
        # Create test data
        chat_history = EnhancedChatHistory(
            user_id=user_id,
            session_id="session_123",
            user_message="Test message",
            bot_response="Test response",
            created_at=datetime.utcnow()
        )
        test_db_session.add(chat_history)
        test_db_session.commit()
        
        # Submit and process access request
        request_id = gdpr_manager.submit_data_subject_request(
            user_id, DataSubjectRightType.ACCESS
        )
        
        # Set up security manager permissions
        policy = AccessControlPolicy(
            user_id=user_id,
            allowed_operations=["read", "export"],
            can_export_data=True
        )
        gdpr_manager.security_manager.set_access_policy(user_id, policy)
        
        # Process request
        exported_data = gdpr_manager.process_access_request(request_id, test_db_session)
        
        assert exported_data["user_id"] == user_id
        assert "chat_history" in exported_data
        assert "consent_records" in exported_data
        assert "processing_info" in exported_data
        
        # Check request status
        request = gdpr_manager._data_requests[request_id]
        assert request.status == RequestStatus.COMPLETED
    
    def test_erasure_request_processing(self, gdpr_manager, test_db_session):
        """Test processing of data erasure requests"""
        user_id = "test_user"
        
        # Create test data
        chat_history = EnhancedChatHistory(
            user_id=user_id,
            session_id="session_123",
            user_message="Test message",
            bot_response="Test response",
            created_at=datetime.utcnow()
        )
        test_db_session.add(chat_history)
        test_db_session.commit()
        
        # Submit erasure request
        request_id = gdpr_manager.submit_data_subject_request(
            user_id, DataSubjectRightType.ERASURE
        )
        
        # Set up security manager permissions
        policy = AccessControlPolicy(
            user_id=user_id,
            allowed_operations=["read", "delete"],
            can_delete_data=True
        )
        gdpr_manager.security_manager.set_access_policy(user_id, policy)
        
        # Process request
        result = gdpr_manager.process_erasure_request(request_id, test_db_session)
        
        assert result["status"] == "completed"
        assert "deletion_summary" in result
        
        # Verify data is deleted
        remaining_chats = test_db_session.query(EnhancedChatHistory).filter(
            EnhancedChatHistory.user_id == user_id
        ).count()
        assert remaining_chats == 0
    
    def test_portability_request_processing(self, gdpr_manager, test_db_session):
        """Test processing of data portability requests"""
        user_id = "test_user"
        
        # Create test data
        chat_history = EnhancedChatHistory(
            user_id=user_id,
            session_id="session_123",
            user_message="Test message",
            bot_response="Test response",
            created_at=datetime.utcnow()
        )
        test_db_session.add(chat_history)
        test_db_session.commit()
        
        # Submit portability request
        request_id = gdpr_manager.submit_data_subject_request(
            user_id, DataSubjectRightType.DATA_PORTABILITY
        )
        
        # Set up security manager permissions
        policy = AccessControlPolicy(
            user_id=user_id,
            allowed_operations=["read", "export"],
            can_export_data=True
        )
        gdpr_manager.security_manager.set_access_policy(user_id, policy)
        
        # Process request
        portable_data = gdpr_manager.process_portability_request(request_id, test_db_session)
        
        assert portable_data["format"] == "JSON"
        assert portable_data["version"] == "1.0"
        assert portable_data["user_id"] == user_id
        assert "data" in portable_data
        assert "exported_at" in portable_data
    
    def test_retention_policy_application(self, gdpr_manager, test_db_session):
        """Test application of data retention policies"""
        # Create old test data
        old_date = datetime.utcnow() - timedelta(days=400)  # Older than default retention
        
        old_chat = EnhancedChatHistory(
            user_id="test_user",
            session_id="old_session",
            user_message="Old message",
            bot_response="Old response",
            created_at=old_date
        )
        test_db_session.add(old_chat)
        
        # Create recent test data
        recent_chat = EnhancedChatHistory(
            user_id="test_user",
            session_id="recent_session",
            user_message="Recent message",
            bot_response="Recent response",
            created_at=datetime.utcnow()
        )
        test_db_session.add(recent_chat)
        test_db_session.commit()
        
        # Apply retention policies
        retention_summary = gdpr_manager.apply_retention_policies(test_db_session)
        
        # Check that old data was deleted
        assert "chat_history" in retention_summary
        assert retention_summary["chat_history"] >= 1
        
        # Verify recent data remains
        remaining_chats = test_db_session.query(EnhancedChatHistory).filter(
            EnhancedChatHistory.session_id == "recent_session"
        ).count()
        assert remaining_chats == 1
    
    def test_compliance_report_generation(self, gdpr_manager, test_db_session):
        """Test GDPR compliance report generation"""
        # Create some test data and requests
        user_id = "test_user"
        
        # Record consent
        gdpr_manager.record_consent(user_id, "conversation_memory", True)
        
        # Submit some requests
        gdpr_manager.submit_data_subject_request(user_id, DataSubjectRightType.ACCESS)
        gdpr_manager.submit_data_subject_request(user_id, DataSubjectRightType.ERASURE)
        
        # Generate report
        report = gdpr_manager.generate_compliance_report(test_db_session)
        
        assert "report_generated_at" in report
        assert "data_subject_requests" in report
        assert "consent_management" in report
        assert "data_retention" in report
        assert "data_inventory" in report
        
        # Check request statistics
        assert report["data_subject_requests"]["total"] == 2
        assert "access" in report["data_subject_requests"]["by_type"]
        assert "erasure" in report["data_subject_requests"]["by_type"]
        
        # Check consent statistics
        assert report["consent_management"]["total_users_with_consent"] == 1
        assert report["consent_management"]["active_consents"] == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])