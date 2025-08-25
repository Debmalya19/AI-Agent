"""
GDPR Compliance module for memory layer
Handles data subject rights, consent management, and compliance reporting
"""

import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import logging

from .memory_models import EnhancedChatHistory, UserSession, MemoryContextCache
from .security_manager import SecurityManager
from .privacy_utils import PrivacyUtils

logger = logging.getLogger(__name__)

class DataSubjectRightType(Enum):
    """Types of data subject rights under GDPR"""
    ACCESS = "access"  # Article 15 - Right of access
    RECTIFICATION = "rectification"  # Article 16 - Right to rectification
    ERASURE = "erasure"  # Article 17 - Right to erasure (right to be forgotten)
    RESTRICT_PROCESSING = "restrict_processing"  # Article 18 - Right to restriction of processing
    DATA_PORTABILITY = "data_portability"  # Article 20 - Right to data portability
    OBJECT = "object"  # Article 21 - Right to object

class RequestStatus(Enum):
    """Status of data subject rights requests"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class ConsentRecord:
    """Record of user consent for data processing"""
    user_id: str
    consent_id: str
    purpose: str  # Purpose of data processing
    consent_given: bool
    consent_timestamp: datetime
    consent_method: str  # How consent was obtained (web_form, api, etc.)
    consent_version: str  # Version of privacy policy/terms
    withdrawal_timestamp: Optional[datetime] = None
    legal_basis: str = "consent"  # GDPR legal basis (Article 6)

@dataclass
class DataSubjectRequest:
    """Data subject rights request"""
    request_id: str
    user_id: str
    request_type: DataSubjectRightType
    status: RequestStatus
    requested_at: datetime
    completed_at: Optional[datetime] = None
    request_details: Dict[str, Any] = None
    response_data: Dict[str, Any] = None
    notes: str = ""

@dataclass
class RetentionPolicy:
    """Data retention policy configuration"""
    data_type: str
    retention_period_days: int
    legal_basis: str
    auto_delete: bool = True
    archive_before_delete: bool = True
    notification_before_delete_days: int = 30

class GDPRComplianceManager:
    """
    Manages GDPR compliance for the memory layer system
    """
    
    def __init__(self, security_manager: SecurityManager, privacy_utils: PrivacyUtils):
        self.security_manager = security_manager
        self.privacy_utils = privacy_utils
        self._consent_records: Dict[str, List[ConsentRecord]] = {}
        self._data_requests: Dict[str, DataSubjectRequest] = {}
        self._retention_policies: List[RetentionPolicy] = self._get_default_retention_policies()
    
    def _get_default_retention_policies(self) -> List[RetentionPolicy]:
        """Get default data retention policies"""
        return [
            RetentionPolicy(
                data_type="chat_history",
                retention_period_days=365,
                legal_basis="legitimate_interest",
                auto_delete=True,
                archive_before_delete=True
            ),
            RetentionPolicy(
                data_type="user_sessions",
                retention_period_days=90,
                legal_basis="legitimate_interest",
                auto_delete=True,
                archive_before_delete=False
            ),
            RetentionPolicy(
                data_type="context_cache",
                retention_period_days=30,
                legal_basis="legitimate_interest",
                auto_delete=True,
                archive_before_delete=False
            ),
            RetentionPolicy(
                data_type="audit_logs",
                retention_period_days=2555,  # 7 years
                legal_basis="legal_obligation",
                auto_delete=False,
                archive_before_delete=True
            )
        ]
    
    def record_consent(self, user_id: str, purpose: str, consent_given: bool,
                      consent_method: str = "api", consent_version: str = "1.0") -> str:
        """
        Record user consent for data processing
        
        Args:
            user_id: User ID
            purpose: Purpose of data processing
            consent_given: Whether consent was given
            consent_method: How consent was obtained
            consent_version: Version of privacy policy/terms
            
        Returns:
            Consent ID
        """
        consent_id = str(uuid.uuid4())
        consent_record = ConsentRecord(
            user_id=user_id,
            consent_id=consent_id,
            purpose=purpose,
            consent_given=consent_given,
            consent_timestamp=datetime.utcnow(),
            consent_method=consent_method,
            consent_version=consent_version
        )
        
        if user_id not in self._consent_records:
            self._consent_records[user_id] = []
        
        self._consent_records[user_id].append(consent_record)
        
        logger.info(f"Consent recorded for user {self.privacy_utils.hash_identifier(user_id)}: "
                   f"purpose={purpose}, consent={consent_given}")
        
        return consent_id
    
    def withdraw_consent(self, user_id: str, consent_id: str) -> bool:
        """
        Withdraw user consent for data processing
        
        Args:
            user_id: User ID
            consent_id: Consent ID to withdraw
            
        Returns:
            True if consent was successfully withdrawn
        """
        if user_id not in self._consent_records:
            return False
        
        for consent in self._consent_records[user_id]:
            if consent.consent_id == consent_id and consent.consent_given:
                consent.withdrawal_timestamp = datetime.utcnow()
                consent.consent_given = False
                
                logger.info(f"Consent withdrawn for user {self.privacy_utils.hash_identifier(user_id)}: "
                           f"consent_id={consent_id}")
                return True
        
        return False
    
    def check_consent(self, user_id: str, purpose: str) -> bool:
        """
        Check if user has given valid consent for specific purpose
        
        Args:
            user_id: User ID
            purpose: Purpose to check consent for
            
        Returns:
            True if valid consent exists
        """
        if user_id not in self._consent_records:
            return False
        
        for consent in self._consent_records[user_id]:
            if (consent.purpose == purpose and 
                consent.consent_given and 
                consent.withdrawal_timestamp is None):
                return True
        
        return False
    
    def submit_data_subject_request(self, user_id: str, request_type: DataSubjectRightType,
                                  request_details: Dict[str, Any] = None) -> str:
        """
        Submit a data subject rights request
        
        Args:
            user_id: User ID making the request
            request_type: Type of request
            request_details: Additional details about the request
            
        Returns:
            Request ID
        """
        request_id = str(uuid.uuid4())
        request = DataSubjectRequest(
            request_id=request_id,
            user_id=user_id,
            request_type=request_type,
            status=RequestStatus.PENDING,
            requested_at=datetime.utcnow(),
            request_details=request_details or {}
        )
        
        self._data_requests[request_id] = request
        
        logger.info(f"Data subject request submitted: user={self.privacy_utils.hash_identifier(user_id)}, "
                   f"type={request_type.value}, request_id={request_id}")
        
        return request_id
    
    def process_access_request(self, request_id: str, db_session: Session) -> Dict[str, Any]:
        """
        Process a data access request (Article 15)
        
        Args:
            request_id: Request ID to process
            db_session: Database session
            
        Returns:
            User data export
        """
        request = self._data_requests.get(request_id)
        if not request or request.request_type != DataSubjectRightType.ACCESS:
            raise ValueError("Invalid access request")
        
        try:
            request.status = RequestStatus.IN_PROGRESS
            
            # Export user data using security manager
            user_data = self.security_manager.export_user_data(
                request.user_id, db_session, include_deleted=False
            )
            
            # Add consent information
            user_data["consent_records"] = []
            if request.user_id in self._consent_records:
                for consent in self._consent_records[request.user_id]:
                    user_data["consent_records"].append(asdict(consent))
            
            # Add processing information
            user_data["processing_info"] = {
                "data_controller": "AI Agent Memory System",
                "processing_purposes": self._get_processing_purposes(request.user_id),
                "legal_basis": self._get_legal_basis(request.user_id),
                "retention_periods": self._get_retention_info(),
                "data_sources": ["user_interactions", "system_logs", "session_data"],
                "data_recipients": ["internal_systems", "analytics_processors"]
            }
            
            request.status = RequestStatus.COMPLETED
            request.completed_at = datetime.utcnow()
            request.response_data = {"export_size": len(json.dumps(user_data))}
            
            logger.info(f"Access request completed: request_id={request_id}")
            return user_data
            
        except Exception as e:
            request.status = RequestStatus.REJECTED
            request.notes = f"Processing failed: {str(e)}"
            logger.error(f"Access request failed: request_id={request_id}, error={e}")
            raise
    
    def process_erasure_request(self, request_id: str, db_session: Session) -> Dict[str, Any]:
        """
        Process a data erasure request (Article 17 - Right to be forgotten)
        
        Args:
            request_id: Request ID to process
            db_session: Database session
            
        Returns:
            Deletion summary
        """
        request = self._data_requests.get(request_id)
        if not request or request.request_type != DataSubjectRightType.ERASURE:
            raise ValueError("Invalid erasure request")
        
        try:
            request.status = RequestStatus.IN_PROGRESS
            
            # Check if erasure is legally required or if there are legitimate grounds to refuse
            if not self._can_erase_data(request.user_id):
                request.status = RequestStatus.REJECTED
                request.notes = "Erasure refused due to legal obligations or legitimate interests"
                return {"status": "refused", "reason": request.notes}
            
            # Perform data deletion
            deletion_counts = self.security_manager.delete_user_data(
                request.user_id, db_session, hard_delete=True
            )
            
            # Remove consent records
            if request.user_id in self._consent_records:
                del self._consent_records[request.user_id]
            
            request.status = RequestStatus.COMPLETED
            request.completed_at = datetime.utcnow()
            request.response_data = deletion_counts
            
            logger.info(f"Erasure request completed: request_id={request_id}, "
                       f"deleted={deletion_counts}")
            
            return {
                "status": "completed",
                "deletion_summary": deletion_counts,
                "completed_at": request.completed_at.isoformat()
            }
            
        except Exception as e:
            request.status = RequestStatus.REJECTED
            request.notes = f"Erasure failed: {str(e)}"
            logger.error(f"Erasure request failed: request_id={request_id}, error={e}")
            raise
    
    def process_portability_request(self, request_id: str, db_session: Session) -> Dict[str, Any]:
        """
        Process a data portability request (Article 20)
        
        Args:
            request_id: Request ID to process
            db_session: Database session
            
        Returns:
            Portable data in structured format
        """
        request = self._data_requests.get(request_id)
        if not request or request.request_type != DataSubjectRightType.DATA_PORTABILITY:
            raise ValueError("Invalid portability request")
        
        try:
            request.status = RequestStatus.IN_PROGRESS
            
            # Export data in portable format (JSON)
            user_data = self.security_manager.export_user_data(
                request.user_id, db_session, include_deleted=False
            )
            
            # Structure data for portability (machine-readable format)
            portable_data = {
                "format": "JSON",
                "version": "1.0",
                "exported_at": datetime.utcnow().isoformat(),
                "user_id": request.user_id,
                "data": user_data
            }
            
            request.status = RequestStatus.COMPLETED
            request.completed_at = datetime.utcnow()
            request.response_data = {"export_size": len(json.dumps(portable_data))}
            
            logger.info(f"Portability request completed: request_id={request_id}")
            return portable_data
            
        except Exception as e:
            request.status = RequestStatus.REJECTED
            request.notes = f"Portability export failed: {str(e)}"
            logger.error(f"Portability request failed: request_id={request_id}, error={e}")
            raise
    
    def _can_erase_data(self, user_id: str) -> bool:
        """
        Check if user data can be erased or if there are legal grounds to refuse
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if data can be erased
        """
        # Check for legal obligations that prevent erasure
        # In a real system, this would check various conditions:
        # - Legal obligations (Article 17(3)(b))
        # - Public interest (Article 17(3)(d))
        # - Legal claims (Article 17(3)(e))
        
        # For this implementation, we'll allow erasure unless there are active legal holds
        # This would be customized based on specific business requirements
        
        return True
    
    def _get_processing_purposes(self, user_id: str) -> List[str]:
        """Get list of processing purposes for user data"""
        purposes = ["conversation_memory", "context_enhancement", "service_improvement"]
        
        # Add purposes based on consent records
        if user_id in self._consent_records:
            for consent in self._consent_records[user_id]:
                if consent.consent_given and consent.purpose not in purposes:
                    purposes.append(consent.purpose)
        
        return purposes
    
    def _get_legal_basis(self, user_id: str) -> List[str]:
        """Get legal basis for processing user data"""
        return ["legitimate_interest", "consent", "contract_performance"]
    
    def _get_retention_info(self) -> Dict[str, Dict[str, Any]]:
        """Get retention information for different data types"""
        retention_info = {}
        
        for policy in self._retention_policies:
            retention_info[policy.data_type] = {
                "retention_period_days": policy.retention_period_days,
                "legal_basis": policy.legal_basis,
                "auto_delete": policy.auto_delete
            }
        
        return retention_info
    
    def apply_retention_policies(self, db_session: Session) -> Dict[str, int]:
        """
        Apply data retention policies and clean up expired data
        
        Args:
            db_session: Database session
            
        Returns:
            Summary of retention actions taken
        """
        retention_summary = {}
        
        for policy in self._retention_policies:
            if not policy.auto_delete:
                continue
            
            cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_period_days)
            deleted_count = 0
            
            try:
                if policy.data_type == "chat_history":
                    # Delete old chat history
                    old_chats = db_session.query(EnhancedChatHistory).filter(
                        EnhancedChatHistory.created_at < cutoff_date
                    )
                    
                    if policy.archive_before_delete:
                        # In a real system, this would archive to cold storage
                        logger.info(f"Would archive {old_chats.count()} chat records before deletion")
                    
                    deleted_count = old_chats.delete()
                
                elif policy.data_type == "user_sessions":
                    # Delete old user sessions
                    deleted_count = db_session.query(UserSession).filter(
                        UserSession.created_at < cutoff_date
                    ).delete()
                
                elif policy.data_type == "context_cache":
                    # Delete expired context cache
                    deleted_count = db_session.query(MemoryContextCache).filter(
                        or_(
                            MemoryContextCache.expires_at < datetime.utcnow(),
                            MemoryContextCache.created_at < cutoff_date
                        )
                    ).delete()
                
                retention_summary[policy.data_type] = deleted_count
                
                if deleted_count > 0:
                    logger.info(f"Retention policy applied: {policy.data_type}, "
                               f"deleted {deleted_count} records")
                
            except Exception as e:
                logger.error(f"Retention policy failed for {policy.data_type}: {e}")
                retention_summary[policy.data_type] = 0
        
        db_session.commit()
        return retention_summary
    
    def generate_compliance_report(self, db_session: Session) -> Dict[str, Any]:
        """
        Generate GDPR compliance report
        
        Args:
            db_session: Database session
            
        Returns:
            Compliance report
        """
        report = {
            "report_generated_at": datetime.utcnow().isoformat(),
            "report_period": "last_30_days",
            "data_subject_requests": {
                "total": len(self._data_requests),
                "by_type": {},
                "by_status": {},
                "average_processing_time_hours": 0
            },
            "consent_management": {
                "total_users_with_consent": len(self._consent_records),
                "active_consents": 0,
                "withdrawn_consents": 0
            },
            "data_retention": {
                "policies_count": len(self._retention_policies),
                "last_cleanup": None
            },
            "data_inventory": {}
        }
        
        # Analyze data subject requests
        for request in self._data_requests.values():
            request_type = request.request_type.value
            status = request.status.value
            
            report["data_subject_requests"]["by_type"][request_type] = \
                report["data_subject_requests"]["by_type"].get(request_type, 0) + 1
            
            report["data_subject_requests"]["by_status"][status] = \
                report["data_subject_requests"]["by_status"].get(status, 0) + 1
        
        # Analyze consent records
        active_consents = 0
        withdrawn_consents = 0
        
        for user_consents in self._consent_records.values():
            for consent in user_consents:
                if consent.consent_given and consent.withdrawal_timestamp is None:
                    active_consents += 1
                elif consent.withdrawal_timestamp is not None:
                    withdrawn_consents += 1
        
        report["consent_management"]["active_consents"] = active_consents
        report["consent_management"]["withdrawn_consents"] = withdrawn_consents
        
        # Data inventory
        try:
            report["data_inventory"]["chat_history_count"] = db_session.query(
                func.count(EnhancedChatHistory.id)
            ).scalar()
            
            report["data_inventory"]["user_sessions_count"] = db_session.query(
                func.count(UserSession.id)
            ).scalar()
            
            report["data_inventory"]["context_cache_count"] = db_session.query(
                func.count(MemoryContextCache.id)
            ).scalar()
            
        except Exception as e:
            logger.error(f"Failed to generate data inventory: {e}")
            report["data_inventory"]["error"] = str(e)
        
        return report