"""
Security Manager for Memory Layer
Handles data encryption, access control, and privacy features
"""

import os
import hashlib
import secrets
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import json
import logging
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.memory_models import EnhancedChatHistory, UserSession, MemoryContextCache

logger = logging.getLogger(__name__)

@dataclass
class EncryptionConfig:
    """Configuration for encryption settings"""
    key_derivation_iterations: int = 100000
    salt_length: int = 32
    encryption_key_env_var: str = "MEMORY_ENCRYPTION_KEY"
    enable_field_level_encryption: bool = True
    encrypted_fields: List[str] = None
    
    def __post_init__(self):
        if self.encrypted_fields is None:
            self.encrypted_fields = ["user_message", "bot_response", "context_data"]

@dataclass
class AccessControlPolicy:
    """Access control policy for user data"""
    user_id: str
    allowed_operations: List[str]
    data_retention_days: int = 365
    can_export_data: bool = True
    can_delete_data: bool = True
    session_timeout_minutes: int = 60

@dataclass
class DataExportRequest:
    """Request for user data export"""
    user_id: str
    request_id: str
    requested_at: datetime
    export_format: str = "json"
    include_deleted: bool = False
    status: str = "pending"

class SecurityManager:
    """
    Manages security and privacy features for the memory layer
    """
    
    def __init__(self, config: EncryptionConfig = None):
        self.config = config or EncryptionConfig()
        self._encryption_key = None
        self._access_policies: Dict[str, AccessControlPolicy] = {}
        self._setup_encryption()
    
    def _setup_encryption(self):
        """Initialize encryption key from environment or generate new one"""
        try:
            # Try to get key from environment
            key_b64 = os.getenv(self.config.encryption_key_env_var)
            if key_b64:
                self._encryption_key = base64.urlsafe_b64decode(key_b64)
            else:
                # Generate new key and warn
                self._encryption_key = Fernet.generate_key()
                logger.warning(
                    f"No encryption key found in {self.config.encryption_key_env_var}. "
                    f"Generated new key: {base64.urlsafe_b64encode(self._encryption_key).decode()}"
                )
        except Exception as e:
            logger.error(f"Failed to setup encryption: {e}")
            raise
    
    def _get_cipher(self, salt: bytes = None) -> Fernet:
        """Get Fernet cipher instance"""
        if salt:
            # Derive key from master key and salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=self.config.key_derivation_iterations,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self._encryption_key))
        else:
            key = self._encryption_key
        
        return Fernet(key)
    
    def encrypt_data(self, data: str, user_id: str = None) -> Dict[str, str]:
        """
        Encrypt sensitive data with optional user-specific salt
        
        Args:
            data: Data to encrypt
            user_id: Optional user ID for user-specific encryption
            
        Returns:
            Dictionary with encrypted data and metadata
        """
        try:
            if not data:
                return {"encrypted_data": "", "salt": "", "encrypted": False}
            
            # Generate salt for user-specific encryption
            salt = None
            if user_id:
                salt = hashlib.sha256(f"{user_id}:{secrets.token_hex(16)}".encode()).digest()
            
            cipher = self._get_cipher(salt)
            encrypted_data = cipher.encrypt(data.encode())
            
            return {
                "encrypted_data": base64.urlsafe_b64encode(encrypted_data).decode(),
                "salt": base64.urlsafe_b64encode(salt).decode() if salt else "",
                "encrypted": True,
                "encryption_version": "1.0"
            }
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            # Return unencrypted data with flag
            return {"encrypted_data": data, "salt": "", "encrypted": False}
    
    def decrypt_data(self, encrypted_data: Dict[str, str]) -> str:
        """
        Decrypt data using stored salt and metadata
        
        Args:
            encrypted_data: Dictionary with encrypted data and metadata
            
        Returns:
            Decrypted string data
        """
        try:
            if not encrypted_data.get("encrypted", False):
                return encrypted_data.get("encrypted_data", "")
            
            salt = None
            if encrypted_data.get("salt"):
                salt = base64.urlsafe_b64decode(encrypted_data["salt"])
            
            cipher = self._get_cipher(salt)
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data["encrypted_data"])
            decrypted_data = cipher.decrypt(encrypted_bytes)
            
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            # Return encrypted data as fallback
            return encrypted_data.get("encrypted_data", "")
    
    def encrypt_conversation_data(self, conversation_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in conversation data
        
        Args:
            conversation_data: Conversation data dictionary
            user_id: User ID for user-specific encryption
            
        Returns:
            Dictionary with encrypted sensitive fields
        """
        if not self.config.enable_field_level_encryption:
            return conversation_data
        
        encrypted_data = conversation_data.copy()
        
        for field in self.config.encrypted_fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_field = self.encrypt_data(str(encrypted_data[field]), user_id)
                encrypted_data[f"{field}_encrypted"] = encrypted_field
                # Remove original field for security
                del encrypted_data[field]
        
        return encrypted_data
    
    def decrypt_conversation_data(self, encrypted_conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in conversation data
        
        Args:
            encrypted_conversation_data: Encrypted conversation data
            
        Returns:
            Dictionary with decrypted sensitive fields
        """
        if not self.config.enable_field_level_encryption:
            return encrypted_conversation_data
        
        decrypted_data = encrypted_conversation_data.copy()
        
        for field in self.config.encrypted_fields:
            encrypted_field_key = f"{field}_encrypted"
            if encrypted_field_key in decrypted_data:
                encrypted_field_data = decrypted_data[encrypted_field_key]
                if isinstance(encrypted_field_data, dict):
                    decrypted_data[field] = self.decrypt_data(encrypted_field_data)
                    # Remove encrypted field
                    del decrypted_data[encrypted_field_key]
        
        return decrypted_data
    
    def set_access_policy(self, user_id: str, policy: AccessControlPolicy):
        """Set access control policy for a user"""
        self._access_policies[user_id] = policy
    
    def get_access_policy(self, user_id: str) -> Optional[AccessControlPolicy]:
        """Get access control policy for a user"""
        return self._access_policies.get(user_id)
    
    def check_access_permission(self, user_id: str, operation: str) -> bool:
        """
        Check if user has permission for specific operation
        
        Args:
            user_id: User ID to check
            operation: Operation to check (read, write, delete, export)
            
        Returns:
            True if user has permission, False otherwise
        """
        policy = self.get_access_policy(user_id)
        if not policy:
            # Default policy - allow basic operations
            return operation in ["read", "write"]
        
        return operation in policy.allowed_operations
    
    def validate_user_session(self, user_id: str, session_id: str, db_session: Session) -> bool:
        """
        Validate user session for access control
        
        Args:
            user_id: User ID
            session_id: Session ID to validate
            db_session: Database session
            
        Returns:
            True if session is valid, False otherwise
        """
        try:
            # Get user session from database
            user_session = db_session.query(UserSession).filter(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.session_id == session_id,
                    UserSession.is_active == True
                )
            ).first()
            
            if not user_session:
                return False
            
            # Check session timeout
            policy = self.get_access_policy(user_id)
            timeout_minutes = policy.session_timeout_minutes if policy else 60
            
            if user_session.last_activity:
                time_since_activity = datetime.utcnow() - user_session.last_activity
                if time_since_activity > timedelta(minutes=timeout_minutes):
                    # Mark session as inactive
                    user_session.is_active = False
                    db_session.commit()
                    return False
            
            # Update last activity
            user_session.last_activity = datetime.utcnow()
            db_session.commit()
            
            return True
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return False
    
    def anonymize_data_for_logging(self, data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """
        Anonymize sensitive data for logging purposes
        
        Args:
            data: Data to anonymize
            user_id: Optional user ID to anonymize
            
        Returns:
            Anonymized data dictionary
        """
        anonymized = data.copy()
        
        # Anonymize user ID
        if user_id:
            anonymized["user_id"] = self._hash_identifier(user_id)
        elif "user_id" in anonymized:
            anonymized["user_id"] = self._hash_identifier(anonymized["user_id"])
        
        # Anonymize sensitive fields
        sensitive_fields = [
            "user_message", "bot_response", "email", "phone", "address",
            "session_id", "ip_address", "user_agent"
        ]
        
        for field in sensitive_fields:
            if field in anonymized:
                if isinstance(anonymized[field], str) and len(anonymized[field]) > 0:
                    # Replace with anonymized version
                    anonymized[field] = self._anonymize_text(anonymized[field])
        
        return anonymized
    
    def _hash_identifier(self, identifier: str) -> str:
        """Create consistent hash for identifier anonymization"""
        return hashlib.sha256(f"{identifier}:anonymous".encode()).hexdigest()[:12]
    
    def _anonymize_text(self, text: str) -> str:
        """Anonymize text content while preserving structure"""
        if len(text) <= 10:
            return "[REDACTED]"
        
        # Keep first and last few characters, anonymize middle
        start = text[:3]
        end = text[-3:]
        middle_length = len(text) - 6
        middle = "*" * min(middle_length, 20)
        
        return f"{start}{middle}{end}"
    
    def export_user_data(self, user_id: str, db_session: Session, 
                        include_deleted: bool = False) -> Dict[str, Any]:
        """
        Export all user data for GDPR compliance
        
        Args:
            user_id: User ID to export data for
            db_session: Database session
            include_deleted: Whether to include soft-deleted data
            
        Returns:
            Dictionary containing all user data
        """
        try:
            if not self.check_access_permission(user_id, "export"):
                raise PermissionError(f"User {user_id} does not have export permission")
            
            export_data = {
                "user_id": user_id,
                "export_timestamp": datetime.utcnow().isoformat(),
                "data_types": []
            }
            
            # Export chat history
            chat_query = db_session.query(EnhancedChatHistory).filter(
                EnhancedChatHistory.user_id == user_id
            )
            
            if not include_deleted:
                chat_query = chat_query.filter(
                    or_(
                        EnhancedChatHistory.deleted_at.is_(None),
                        EnhancedChatHistory.deleted_at > datetime.utcnow()
                    )
                )
            
            chat_history = chat_query.all()
            
            export_data["chat_history"] = []
            for chat in chat_history:
                chat_dict = {
                    "session_id": chat.session_id,
                    "created_at": chat.created_at.isoformat() if chat.created_at else None,
                    "tools_used": chat.tools_used,
                    "tool_performance": chat.tool_performance,
                    "context_used": chat.context_used,
                    "response_quality_score": chat.response_quality_score
                }
                
                # Decrypt sensitive data for export
                if hasattr(chat, 'user_message_encrypted') and chat.user_message_encrypted:
                    chat_dict["user_message"] = self.decrypt_data(chat.user_message_encrypted)
                else:
                    chat_dict["user_message"] = getattr(chat, 'user_message', '')
                
                if hasattr(chat, 'bot_response_encrypted') and chat.bot_response_encrypted:
                    chat_dict["bot_response"] = self.decrypt_data(chat.bot_response_encrypted)
                else:
                    chat_dict["bot_response"] = getattr(chat, 'bot_response', '')
                
                export_data["chat_history"].append(chat_dict)
            
            export_data["data_types"].append("chat_history")
            
            # Export user sessions
            user_sessions = db_session.query(UserSession).filter(
                UserSession.user_id == user_id
            ).all()
            
            export_data["user_sessions"] = []
            for session in user_sessions:
                session_dict = {
                    "session_id": session.session_id,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                    "last_activity": session.last_activity.isoformat() if session.last_activity else None,
                    "is_active": session.is_active,
                    "session_metadata": session.session_metadata
                }
                export_data["user_sessions"].append(session_dict)
            
            export_data["data_types"].append("user_sessions")
            
            # Export memory context cache
            context_cache = db_session.query(MemoryContextCache).filter(
                MemoryContextCache.user_id == user_id
            ).all()
            
            export_data["context_cache"] = []
            for cache in context_cache:
                cache_dict = {
                    "cache_key": cache.cache_key,
                    "context_type": cache.context_type,
                    "relevance_score": cache.relevance_score,
                    "created_at": cache.created_at.isoformat() if cache.created_at else None,
                    "expires_at": cache.expires_at.isoformat() if cache.expires_at else None
                }
                
                # Decrypt context data
                if hasattr(cache, 'context_data_encrypted') and cache.context_data_encrypted:
                    cache_dict["context_data"] = self.decrypt_data(cache.context_data_encrypted)
                else:
                    cache_dict["context_data"] = cache.context_data
                
                export_data["context_cache"].append(cache_dict)
            
            export_data["data_types"].append("context_cache")
            
            logger.info(f"Data export completed for user {self._hash_identifier(user_id)}")
            return export_data
            
        except Exception as e:
            logger.error(f"Data export failed for user {self._hash_identifier(user_id)}: {e}")
            raise
    
    def delete_user_data(self, user_id: str, db_session: Session, 
                        hard_delete: bool = False) -> Dict[str, int]:
        """
        Delete all user data for GDPR compliance (right to be forgotten)
        
        Args:
            user_id: User ID to delete data for
            db_session: Database session
            hard_delete: Whether to permanently delete or soft delete
            
        Returns:
            Dictionary with count of deleted records by type
        """
        try:
            if not self.check_access_permission(user_id, "delete"):
                raise PermissionError(f"User {user_id} does not have delete permission")
            
            deletion_counts = {}
            
            # Delete chat history
            if hard_delete:
                chat_count = db_session.query(EnhancedChatHistory).filter(
                    EnhancedChatHistory.user_id == user_id
                ).delete()
            else:
                # Soft delete - mark as deleted
                chat_records = db_session.query(EnhancedChatHistory).filter(
                    EnhancedChatHistory.user_id == user_id
                ).all()
                
                chat_count = 0
                for record in chat_records:
                    record.deleted_at = datetime.utcnow()
                    chat_count += 1
            
            deletion_counts["chat_history"] = chat_count
            
            # Delete user sessions
            session_count = db_session.query(UserSession).filter(
                UserSession.user_id == user_id
            ).delete()
            deletion_counts["user_sessions"] = session_count
            
            # Delete context cache
            cache_count = db_session.query(MemoryContextCache).filter(
                MemoryContextCache.user_id == user_id
            ).delete()
            deletion_counts["context_cache"] = cache_count
            
            # Remove access policy
            if user_id in self._access_policies:
                del self._access_policies[user_id]
            
            db_session.commit()
            
            logger.info(f"Data deletion completed for user {self._hash_identifier(user_id)}: {deletion_counts}")
            return deletion_counts
            
        except Exception as e:
            logger.error(f"Data deletion failed for user {self._hash_identifier(user_id)}: {e}")
            db_session.rollback()
            raise
    
    def audit_data_access(self, user_id: str, operation: str, resource: str, 
                         success: bool, details: Dict[str, Any] = None):
        """
        Log data access for audit purposes
        
        Args:
            user_id: User ID performing the operation
            operation: Type of operation (read, write, delete, export)
            resource: Resource being accessed
            success: Whether the operation was successful
            details: Additional details about the operation
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": self._hash_identifier(user_id),
            "operation": operation,
            "resource": resource,
            "success": success,
            "details": self.anonymize_data_for_logging(details or {})
        }
        
        # Log audit entry (in production, this would go to a secure audit log)
        logger.info(f"AUDIT: {json.dumps(audit_entry)}")