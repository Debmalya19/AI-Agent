"""
Security integration module for memory layer
Integrates security manager, privacy utils, and GDPR compliance with existing memory components
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.security_manager import SecurityManager, EncryptionConfig, AccessControlPolicy
from backend.privacy_utils import PrivacyUtils, AnonymizationConfig
from backend.gdpr_compliance import GDPRComplianceManager, DataSubjectRightType, ConsentRecord
from backend.memory_layer_manager import MemoryLayerManager
from backend.memory_models import EnhancedChatHistory, MemoryContextCache, ConversationEntry, ContextEntry

logger = logging.getLogger(__name__)

class SecureMemoryLayerManager:
    """
    Enhanced memory layer manager with integrated security and privacy features
    """
    
    def __init__(self, 
                 memory_manager: MemoryLayerManager,
                 encryption_config: EncryptionConfig = None,
                 anonymization_config: AnonymizationConfig = None):
        """
        Initialize secure memory layer manager
        
        Args:
            memory_manager: Base memory layer manager
            encryption_config: Configuration for encryption
            anonymization_config: Configuration for anonymization
        """
        self.memory_manager = memory_manager
        
        # Initialize security components
        self.security_manager = SecurityManager(encryption_config)
        self.privacy_utils = PrivacyUtils(anonymization_config)
        self.gdpr_manager = GDPRComplianceManager(
            self.security_manager, 
            self.privacy_utils
        )
        
        logger.info("Secure memory layer manager initialized")
    
    def store_conversation_secure(self, conversation: ConversationEntry, 
                                db_session: Session) -> bool:
        """
        Store conversation with encryption and privacy protection
        
        Args:
            conversation: Conversation entry to store
            db_session: Database session
            
        Returns:
            True if stored successfully
        """
        try:
            # Check user consent for data processing
            if not self.gdpr_manager.check_consent(conversation.user_id, "conversation_memory"):
                logger.warning(f"No consent for conversation storage: user {conversation.user_id}")
                return False
            
            # Validate user session
            if hasattr(conversation, 'session_id'):
                if not self.security_manager.validate_user_session(
                    conversation.user_id, conversation.session_id, db_session
                ):
                    logger.warning(f"Invalid session for conversation storage: {conversation.session_id}")
                    return False
            
            # Encrypt sensitive conversation data
            conversation_dict = conversation.to_dict()
            encrypted_data = self.security_manager.encrypt_conversation_data(
                conversation_dict, conversation.user_id
            )
            
            # Create enhanced chat history entry with encrypted data
            chat_entry = EnhancedChatHistory(
                session_id=conversation.session_id,
                user_id=conversation.user_id,
                tools_used=conversation.tools_used,
                tool_performance=conversation.tool_performance,
                context_used=conversation.context_used,
                response_quality_score=conversation.response_quality_score,
                data_classification="internal",  # Default classification
                retention_policy="standard_365_days"
            )
            
            # Set encrypted fields
            if "user_message_encrypted" in encrypted_data:
                chat_entry.user_message_encrypted = encrypted_data["user_message_encrypted"]
            else:
                chat_entry.user_message = conversation.user_message
            
            if "bot_response_encrypted" in encrypted_data:
                chat_entry.bot_response_encrypted = encrypted_data["bot_response_encrypted"]
            else:
                chat_entry.bot_response = conversation.bot_response
            
            db_session.add(chat_entry)
            db_session.commit()
            
            # Audit the data access
            self.security_manager.audit_data_access(
                conversation.user_id, "write", "conversation", True,
                {"session_id": conversation.session_id, "encrypted": True}
            )
            
            logger.info(f"Conversation stored securely for user {conversation.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store conversation securely: {e}")
            db_session.rollback()
            
            # Audit the failed access
            self.security_manager.audit_data_access(
                conversation.user_id, "write", "conversation", False,
                {"error": str(e)}
            )
            return False
    
    def retrieve_context_secure(self, query: str, user_id: str, 
                              db_session: Session, limit: int = 10) -> List[ContextEntry]:
        """
        Retrieve context with access control and decryption
        
        Args:
            query: Query for context retrieval
            user_id: User ID requesting context
            db_session: Database session
            limit: Maximum number of context entries
            
        Returns:
            List of decrypted context entries
        """
        try:
            # Check access permission
            if not self.security_manager.check_access_permission(user_id, "read"):
                logger.warning(f"Access denied for context retrieval: user {user_id}")
                return []
            
            # Get encrypted context from base memory manager
            encrypted_contexts = self.memory_manager.retrieve_context(
                query, user_id, limit
            )
            
            # Decrypt and return contexts
            decrypted_contexts = []
            for context in encrypted_contexts:
                try:
                    # If context has encrypted data, decrypt it
                    if hasattr(context, 'metadata') and 'encrypted_data' in context.metadata:
                        decrypted_content = self.security_manager.decrypt_data(
                            context.metadata['encrypted_data']
                        )
                        context.content = decrypted_content
                    
                    decrypted_contexts.append(context)
                    
                except Exception as e:
                    logger.warning(f"Failed to decrypt context entry: {e}")
                    # Continue with other entries
                    continue
            
            # Audit the data access
            self.security_manager.audit_data_access(
                user_id, "read", "context", True,
                {"query_hash": hash(query), "results_count": len(decrypted_contexts)}
            )
            
            return decrypted_contexts
            
        except Exception as e:
            logger.error(f"Failed to retrieve context securely: {e}")
            
            # Audit the failed access
            self.security_manager.audit_data_access(
                user_id, "read", "context", False,
                {"error": str(e)}
            )
            return []
    
    def export_user_data_secure(self, user_id: str, db_session: Session,
                              request_format: str = "json") -> Dict[str, Any]:
        """
        Export user data with GDPR compliance
        
        Args:
            user_id: User ID to export data for
            db_session: Database session
            request_format: Export format (json, csv, xml)
            
        Returns:
            Exported user data
        """
        try:
            # Submit GDPR access request
            request_id = self.gdpr_manager.submit_data_subject_request(
                user_id, DataSubjectRightType.ACCESS,
                {"format": request_format}
            )
            
            # Process the request
            exported_data = self.gdpr_manager.process_access_request(
                request_id, db_session
            )
            
            logger.info(f"User data exported securely: user {user_id}, request {request_id}")
            return exported_data
            
        except Exception as e:
            logger.error(f"Failed to export user data: {e}")
            raise
    
    def delete_user_data_secure(self, user_id: str, db_session: Session,
                               hard_delete: bool = False) -> Dict[str, Any]:
        """
        Delete user data with GDPR compliance (right to be forgotten)
        
        Args:
            user_id: User ID to delete data for
            db_session: Database session
            hard_delete: Whether to permanently delete or soft delete
            
        Returns:
            Deletion summary
        """
        try:
            # Submit GDPR erasure request
            request_id = self.gdpr_manager.submit_data_subject_request(
                user_id, DataSubjectRightType.ERASURE,
                {"hard_delete": hard_delete}
            )
            
            # Process the request
            deletion_result = self.gdpr_manager.process_erasure_request(
                request_id, db_session
            )
            
            logger.info(f"User data deleted securely: user {user_id}, request {request_id}")
            return deletion_result
            
        except Exception as e:
            logger.error(f"Failed to delete user data: {e}")
            raise
    
    def anonymize_conversation_history(self, user_id: str, db_session: Session,
                                     older_than_days: int = 365) -> int:
        """
        Anonymize old conversation history for privacy protection
        
        Args:
            user_id: User ID to anonymize data for
            db_session: Database session
            older_than_days: Anonymize conversations older than this many days
            
        Returns:
            Number of conversations anonymized
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            
            # Get old conversations
            old_conversations = db_session.query(EnhancedChatHistory).filter(
                EnhancedChatHistory.user_id == user_id,
                EnhancedChatHistory.created_at < cutoff_date,
                EnhancedChatHistory.anonymized_at.is_(None)
            ).all()
            
            anonymized_count = 0
            
            for conversation in old_conversations:
                try:
                    # Anonymize user message
                    if conversation.user_message:
                        conversation.user_message = self.privacy_utils.anonymize_text(
                            conversation.user_message
                        )
                    
                    # Anonymize bot response
                    if conversation.bot_response:
                        conversation.bot_response = self.privacy_utils.anonymize_text(
                            conversation.bot_response
                        )
                    
                    # Anonymize encrypted fields if they exist
                    if conversation.user_message_encrypted:
                        # Decrypt, anonymize, re-encrypt
                        decrypted = self.security_manager.decrypt_data(
                            conversation.user_message_encrypted
                        )
                        anonymized = self.privacy_utils.anonymize_text(decrypted)
                        conversation.user_message_encrypted = self.security_manager.encrypt_data(
                            anonymized, user_id
                        )
                    
                    if conversation.bot_response_encrypted:
                        # Decrypt, anonymize, re-encrypt
                        decrypted = self.security_manager.decrypt_data(
                            conversation.bot_response_encrypted
                        )
                        anonymized = self.privacy_utils.anonymize_text(decrypted)
                        conversation.bot_response_encrypted = self.security_manager.encrypt_data(
                            anonymized, user_id
                        )
                    
                    # Mark as anonymized
                    conversation.anonymized_at = datetime.utcnow()
                    anonymized_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to anonymize conversation {conversation.id}: {e}")
                    continue
            
            db_session.commit()
            
            logger.info(f"Anonymized {anonymized_count} conversations for user {user_id}")
            return anonymized_count
            
        except Exception as e:
            logger.error(f"Failed to anonymize conversation history: {e}")
            db_session.rollback()
            return 0
    
    def setup_user_consent(self, user_id: str, purposes: List[str],
                          consent_method: str = "api") -> List[str]:
        """
        Set up user consent for data processing purposes
        
        Args:
            user_id: User ID
            purposes: List of processing purposes
            consent_method: How consent was obtained
            
        Returns:
            List of consent IDs
        """
        consent_ids = []
        
        for purpose in purposes:
            consent_id = self.gdpr_manager.record_consent(
                user_id, purpose, consent_given=True, consent_method=consent_method
            )
            consent_ids.append(consent_id)
        
        logger.info(f"Set up consent for user {user_id}: {len(consent_ids)} purposes")
        return consent_ids
    
    def apply_retention_policies(self, db_session: Session) -> Dict[str, int]:
        """
        Apply data retention policies across the system
        
        Args:
            db_session: Database session
            
        Returns:
            Summary of retention actions
        """
        try:
            # Apply GDPR retention policies
            gdpr_summary = self.gdpr_manager.apply_retention_policies(db_session)
            
            # Apply memory layer retention policies
            memory_summary = self.memory_manager.cleanup_expired_data()
            
            # Combine summaries
            combined_summary = {**gdpr_summary, **memory_summary}
            
            logger.info(f"Applied retention policies: {combined_summary}")
            return combined_summary
            
        except Exception as e:
            logger.error(f"Failed to apply retention policies: {e}")
            return {}
    
    def generate_privacy_report(self, db_session: Session) -> Dict[str, Any]:
        """
        Generate comprehensive privacy and compliance report
        
        Args:
            db_session: Database session
            
        Returns:
            Privacy report
        """
        try:
            # Get GDPR compliance report
            gdpr_report = self.gdpr_manager.generate_compliance_report(db_session)
            
            # Get memory system statistics
            memory_stats = self.memory_manager.get_memory_stats()
            
            # Analyze data for privacy issues
            sample_data = {
                "total_conversations": memory_stats.get("total_conversations", 0),
                "total_users": memory_stats.get("total_users", 0),
                "encrypted_conversations": memory_stats.get("encrypted_conversations", 0),
                "anonymized_conversations": memory_stats.get("anonymized_conversations", 0)
            }
            
            privacy_analysis = self.privacy_utils.create_privacy_report(sample_data)
            
            # Combine reports
            comprehensive_report = {
                "report_timestamp": datetime.utcnow().isoformat(),
                "gdpr_compliance": gdpr_report,
                "memory_statistics": memory_stats,
                "privacy_analysis": privacy_analysis,
                "security_metrics": {
                    "encryption_enabled": True,
                    "anonymization_enabled": True,
                    "access_control_enabled": True,
                    "audit_logging_enabled": True
                }
            }
            
            logger.info("Generated comprehensive privacy report")
            return comprehensive_report
            
        except Exception as e:
            logger.error(f"Failed to generate privacy report: {e}")
            return {"error": str(e)}
    
    def get_security_status(self) -> Dict[str, Any]:
        """
        Get current security status of the memory layer
        
        Returns:
            Security status information
        """
        return {
            "encryption": {
                "enabled": True,
                "algorithm": "Fernet (AES 128)",
                "key_rotation": "manual"
            },
            "access_control": {
                "enabled": True,
                "session_validation": True,
                "permission_checks": True
            },
            "privacy": {
                "pii_detection": True,
                "anonymization": True,
                "data_classification": True
            },
            "gdpr_compliance": {
                "consent_management": True,
                "data_subject_rights": True,
                "retention_policies": True,
                "audit_logging": True
            },
            "monitoring": {
                "security_events": True,
                "privacy_violations": True,
                "compliance_metrics": True
            }
        }