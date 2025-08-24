"""
Privacy utilities for data anonymization and GDPR compliance
"""

import re
import hashlib
import secrets
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class AnonymizationConfig:
    """Configuration for data anonymization"""
    preserve_structure: bool = True
    hash_identifiers: bool = True
    redact_pii: bool = True
    anonymize_timestamps: bool = False
    keep_statistical_properties: bool = True

@dataclass
class PIIPattern:
    """Pattern for detecting personally identifiable information"""
    name: str
    pattern: str
    replacement: str
    confidence_threshold: float = 0.8

class PrivacyUtils:
    """
    Utilities for data privacy, anonymization, and PII detection
    """
    
    # Common PII patterns
    PII_PATTERNS = [
        PIIPattern("email", r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "[EMAIL]"),
        PIIPattern("phone", r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b', "[PHONE]"),
        PIIPattern("ssn", r'\b\d{3}-?\d{2}-?\d{4}\b', "[SSN]"),
        PIIPattern("credit_card", r'\b(?:\d{4}[-\s]?){3}\d{4}\b', "[CREDIT_CARD]"),
        PIIPattern("ip_address", r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', "[IP_ADDRESS]"),
        PIIPattern("url", r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?', "[URL]"),
        PIIPattern("address", r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Place|Pl)\b', "[ADDRESS]"),
    ]
    
    def __init__(self, config: AnonymizationConfig = None):
        self.config = config or AnonymizationConfig()
        self._identifier_cache: Dict[str, str] = {}
    
    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect personally identifiable information in text
        
        Args:
            text: Text to analyze for PII
            
        Returns:
            List of detected PII with positions and types
        """
        detected_pii = []
        
        for pattern in self.PII_PATTERNS:
            matches = re.finditer(pattern.pattern, text, re.IGNORECASE)
            for match in matches:
                detected_pii.append({
                    "type": pattern.name,
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": pattern.confidence_threshold,
                    "replacement": pattern.replacement
                })
        
        return detected_pii
    
    def anonymize_text(self, text: str, preserve_length: bool = True) -> str:
        """
        Anonymize text by replacing PII with placeholders
        
        Args:
            text: Text to anonymize
            preserve_length: Whether to preserve original text length
            
        Returns:
            Anonymized text
        """
        if not text:
            return text
        
        anonymized = text
        pii_detections = self.detect_pii(text)
        
        # Sort by position (reverse order to maintain positions)
        pii_detections.sort(key=lambda x: x["start"], reverse=True)
        
        for detection in pii_detections:
            start, end = detection["start"], detection["end"]
            original_value = detection["value"]
            replacement = detection["replacement"]
            
            if preserve_length and self.config.preserve_structure:
                # Create replacement that preserves length and some structure
                replacement = self._create_structured_replacement(
                    original_value, detection["type"]
                )
            
            anonymized = anonymized[:start] + replacement + anonymized[end:]
        
        return anonymized
    
    def _create_structured_replacement(self, original: str, pii_type: str) -> str:
        """Create a replacement that preserves structure"""
        if pii_type == "email":
            parts = original.split("@")
            if len(parts) == 2:
                username_len = len(parts[0])
                domain_len = len(parts[1])
                return f"{'x' * username_len}@{'x' * domain_len}"
        
        elif pii_type == "phone":
            # Preserve phone number structure
            digits_only = re.sub(r'\D', '', original)
            if len(digits_only) == 10:
                return "xxx-xxx-xxxx"
            elif len(digits_only) == 11:
                return "x-xxx-xxx-xxxx"
        
        elif pii_type == "credit_card":
            return "xxxx-xxxx-xxxx-xxxx"
        
        # Default: preserve length with x's
        return "x" * len(original)
    
    def hash_identifier(self, identifier: str, salt: str = None) -> str:
        """
        Create consistent hash for identifier
        
        Args:
            identifier: Identifier to hash
            salt: Optional salt for hashing
            
        Returns:
            Hashed identifier
        """
        if identifier in self._identifier_cache:
            return self._identifier_cache[identifier]
        
        if not salt:
            salt = "privacy_hash_salt"
        
        hash_input = f"{identifier}:{salt}"
        hashed = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
        
        self._identifier_cache[identifier] = hashed
        return hashed
    
    def anonymize_conversation_data(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize conversation data while preserving utility
        
        Args:
            conversation_data: Conversation data to anonymize
            
        Returns:
            Anonymized conversation data
        """
        anonymized = conversation_data.copy()
        
        # Anonymize user identifier
        if "user_id" in anonymized:
            anonymized["user_id"] = self.hash_identifier(anonymized["user_id"])
        
        # Anonymize session identifier
        if "session_id" in anonymized:
            anonymized["session_id"] = self.hash_identifier(anonymized["session_id"])
        
        # Anonymize message content
        if "user_message" in anonymized:
            anonymized["user_message"] = self.anonymize_text(anonymized["user_message"])
        
        if "bot_response" in anonymized:
            anonymized["bot_response"] = self.anonymize_text(anonymized["bot_response"])
        
        # Anonymize context data
        if "context_used" in anonymized and isinstance(anonymized["context_used"], list):
            anonymized["context_used"] = [
                self.anonymize_text(str(context)) for context in anonymized["context_used"]
            ]
        
        # Preserve timestamps but optionally fuzz them
        if self.config.anonymize_timestamps:
            for timestamp_field in ["created_at", "updated_at", "timestamp"]:
                if timestamp_field in anonymized:
                    anonymized[timestamp_field] = self._fuzz_timestamp(
                        anonymized[timestamp_field]
                    )
        
        return anonymized
    
    def _fuzz_timestamp(self, timestamp: Any) -> Any:
        """Add small random offset to timestamp for privacy"""
        if isinstance(timestamp, datetime):
            # Add random offset of up to 1 hour
            offset_minutes = secrets.randbelow(120) - 60  # -60 to +60 minutes
            return timestamp + timedelta(minutes=offset_minutes)
        elif isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                fuzzed = self._fuzz_timestamp(dt)
                return fuzzed.isoformat()
            except:
                return timestamp
        
        return timestamp
    
    def create_privacy_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create privacy analysis report for data
        
        Args:
            data: Data to analyze
            
        Returns:
            Privacy report with PII detection results
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_fields_analyzed": 0,
            "pii_detections": [],
            "privacy_score": 0.0,
            "recommendations": []
        }
        
        def analyze_value(key: str, value: Any, path: str = ""):
            report["total_fields_analyzed"] += 1
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, str):
                pii_found = self.detect_pii(value)
                if pii_found:
                    for pii in pii_found:
                        report["pii_detections"].append({
                            "field_path": current_path,
                            "pii_type": pii["type"],
                            "confidence": pii["confidence"],
                            "value_preview": pii["value"][:10] + "..." if len(pii["value"]) > 10 else pii["value"]
                        })
            
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    analyze_value(sub_key, sub_value, current_path)
            
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    analyze_value(f"[{i}]", item, current_path)
        
        # Analyze all data
        for key, value in data.items():
            analyze_value(key, value)
        
        # Calculate privacy score
        pii_count = len(report["pii_detections"])
        if report["total_fields_analyzed"] > 0:
            report["privacy_score"] = max(0.0, 1.0 - (pii_count / report["total_fields_analyzed"]))
        
        # Generate recommendations
        if pii_count > 0:
            report["recommendations"].append("Consider anonymizing detected PII before logging or storage")
        
        if report["privacy_score"] < 0.7:
            report["recommendations"].append("High amount of PII detected - implement stronger privacy controls")
        
        unique_pii_types = set(detection["pii_type"] for detection in report["pii_detections"])
        if "email" in unique_pii_types or "phone" in unique_pii_types:
            report["recommendations"].append("Contact information detected - ensure proper consent and retention policies")
        
        return report
    
    def sanitize_for_logging(self, data: Dict[str, Any], max_depth: int = 3) -> Dict[str, Any]:
        """
        Sanitize data for safe logging by removing/anonymizing sensitive information
        
        Args:
            data: Data to sanitize
            max_depth: Maximum depth to traverse in nested structures
            
        Returns:
            Sanitized data safe for logging
        """
        def sanitize_value(value: Any, depth: int = 0) -> Any:
            if depth > max_depth:
                return "[MAX_DEPTH_REACHED]"
            
            if isinstance(value, str):
                # Anonymize PII in strings
                return self.anonymize_text(value)
            
            elif isinstance(value, dict):
                sanitized = {}
                for key, val in value.items():
                    # Skip sensitive keys entirely
                    if key.lower() in ["password", "token", "secret", "key", "auth"]:
                        sanitized[key] = "[REDACTED]"
                    else:
                        sanitized[key] = sanitize_value(val, depth + 1)
                return sanitized
            
            elif isinstance(value, list):
                return [sanitize_value(item, depth + 1) for item in value[:10]]  # Limit list size
            
            else:
                return value
        
        return sanitize_value(data)