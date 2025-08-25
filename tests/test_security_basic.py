#!/usr/bin/env python3
"""
Basic test for security functionality
"""

from security_manager import SecurityManager, EncryptionConfig
from privacy_utils import PrivacyUtils, AnonymizationConfig

def test_encryption():
    """Test basic encryption functionality"""
    print("Testing encryption...")
    
    config = EncryptionConfig()
    sm = SecurityManager(config)
    
    test_data = 'Hello, this is test data with PII: john@example.com'
    user_id = 'test_user'
    
    # Test encryption
    encrypted = sm.encrypt_data(test_data, user_id)
    print(f"Original: {test_data}")
    print(f"Encrypted: {encrypted['encrypted']}")
    print(f"Has salt: {bool(encrypted['salt'])}")
    
    # Test decryption
    decrypted = sm.decrypt_data(encrypted)
    print(f"Decrypted: {decrypted}")
    
    if test_data == decrypted:
        print("✓ Encryption test passed!")
        return True
    else:
        print("✗ Encryption test failed!")
        return False

def test_privacy():
    """Test basic privacy functionality"""
    print("\nTesting privacy utilities...")
    
    config = AnonymizationConfig()
    pu = PrivacyUtils(config)
    
    test_text = "Contact me at john.doe@example.com or call 555-123-4567"
    
    # Test PII detection
    pii_detected = pu.detect_pii(test_text)
    print(f"Original text: {test_text}")
    print(f"PII detected: {len(pii_detected)} items")
    
    for pii in pii_detected:
        print(f"  - {pii['type']}: {pii['value']}")
    
    # Test anonymization
    anonymized = pu.anonymize_text(test_text)
    print(f"Anonymized: {anonymized}")
    
    if len(pii_detected) > 0 and "john.doe@example.com" not in anonymized:
        print("✓ Privacy test passed!")
        return True
    else:
        print("✗ Privacy test failed!")
        return False

def test_conversation_encryption():
    """Test conversation data encryption"""
    print("\nTesting conversation encryption...")
    
    config = EncryptionConfig()
    sm = SecurityManager(config)
    
    conversation_data = {
        "user_id": "test_user",
        "session_id": "session_123",
        "user_message": "Hello, my email is john@example.com",
        "bot_response": "Hello! I can help you with that.",
        "tools_used": ["email_tool"],
        "created_at": "2024-01-01T00:00:00Z"
    }
    
    # Encrypt conversation data
    encrypted_data = sm.encrypt_conversation_data(conversation_data, "test_user")
    print(f"Original keys: {list(conversation_data.keys())}")
    print(f"Encrypted keys: {list(encrypted_data.keys())}")
    
    # Check that sensitive fields are encrypted
    has_encrypted_message = "user_message_encrypted" in encrypted_data
    has_encrypted_response = "bot_response_encrypted" in encrypted_data
    no_plain_message = "user_message" not in encrypted_data
    no_plain_response = "bot_response" not in encrypted_data
    
    if has_encrypted_message and has_encrypted_response and no_plain_message and no_plain_response:
        print("✓ Conversation encryption test passed!")
        return True
    else:
        print("✗ Conversation encryption test failed!")
        return False

if __name__ == "__main__":
    print("Running basic security tests...\n")
    
    results = []
    results.append(test_encryption())
    results.append(test_privacy())
    results.append(test_conversation_encryption())
    
    print(f"\nTest Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed!")