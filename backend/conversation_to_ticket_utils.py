"""
Conversation to Ticket Conversion Utilities

This module provides utilities to convert AI agent conversations into support tickets
with intelligent analysis and categorization.

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from dataclasses import dataclass
from enum import Enum
import re
import json

from backend.database import SessionLocal
from backend.unified_models import (
    UnifiedUser, UnifiedTicket, UnifiedChatHistory, UnifiedTicketComment,
    UnifiedTicketActivity, TicketStatus, TicketPriority, TicketCategory
)

logger = logging.getLogger(__name__)

class ConversationAnalysisResult(Enum):
    """Results of conversation analysis"""
    NEEDS_TICKET = "needs_ticket"
    RESOLVED = "resolved"
    INFORMATIONAL = "informational"
    ESCALATION_REQUIRED = "escalation_required"

@dataclass
class TicketMetadata:
    """Metadata extracted from conversation for ticket creation"""
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority
    tags: List[str]
    urgency_score: float  # 0.0 to 1.0
    complexity_score: float  # 0.0 to 1.0
    sentiment_score: float  # -1.0 to 1.0 (negative to positive)
    
    def __post_init__(self):
        if not isinstance(self.tags, list):
            self.tags = []

@dataclass
class ConversationAnalysis:
    """Complete analysis of a conversation"""
    conversation_id: int
    analysis_result: ConversationAnalysisResult
    ticket_metadata: Optional[TicketMetadata]
    confidence_score: float  # 0.0 to 1.0
    reasoning: str
    extracted_entities: Dict[str, Any]
    
    def __post_init__(self):
        if self.extracted_entities is None:
            self.extracted_entities = {}

class ConversationAnalyzer:
    """
    Analyzes AI agent conversations to determine if they need to be converted to tickets
    """
    
    def __init__(self):
        # Keywords for different categories
        self.category_keywords = {
            TicketCategory.TECHNICAL: [
                "error", "bug", "crash", "not working", "broken", "malfunction",
                "technical issue", "system down", "outage", "connection problem",
                "slow", "performance", "timeout", "server", "database"
            ],
            TicketCategory.BILLING: [
                "bill", "billing", "payment", "charge", "invoice", "cost", "price",
                "refund", "credit", "overcharge", "subscription", "plan change",
                "payment method", "card", "bank", "transaction"
            ],
            TicketCategory.ACCOUNT: [
                "account", "login", "password", "profile", "settings", "username",
                "email change", "phone number", "address", "personal information",
                "security", "two-factor", "verification"
            ],
            TicketCategory.FEATURE_REQUEST: [
                "feature", "request", "suggestion", "improvement", "enhancement",
                "new functionality", "add", "would like", "wish", "could you",
                "missing", "need"
            ],
            TicketCategory.BUG_REPORT: [
                "bug", "error", "issue", "problem", "glitch", "fault", "defect",
                "unexpected behavior", "wrong result", "incorrect", "broken feature"
            ]
        }
        
        # Priority keywords
        self.priority_keywords = {
            TicketPriority.CRITICAL: [
                "urgent", "critical", "emergency", "asap", "immediately", "now",
                "production down", "system down", "can't work", "blocking",
                "severe", "major impact"
            ],
            TicketPriority.HIGH: [
                "important", "high priority", "soon", "quickly", "affecting business",
                "multiple users", "significant", "serious"
            ],
            TicketPriority.LOW: [
                "low priority", "minor", "cosmetic", "enhancement", "nice to have",
                "when possible", "no rush", "eventually"
            ]
        }
        
        # Sentiment indicators
        self.negative_sentiment = [
            "frustrated", "angry", "disappointed", "terrible", "awful", "hate",
            "worst", "horrible", "useless", "broken", "fed up", "annoyed"
        ]
        
        self.positive_sentiment = [
            "great", "excellent", "love", "perfect", "amazing", "wonderful",
            "helpful", "satisfied", "happy", "pleased", "thank you"
        ]
        
        # Urgency indicators
        self.urgency_indicators = [
            "urgent", "asap", "immediately", "right now", "emergency", "critical",
            "can't work", "blocking", "deadline", "time sensitive"
        ]
        
        # Complexity indicators
        self.complexity_indicators = [
            "multiple", "several", "various", "complex", "complicated", "integration",
            "system", "database", "network", "configuration", "setup"
        ]
    
    def analyze_conversation(self, conversation_id: int) -> ConversationAnalysis:
        """
        Analyze a conversation to determine if it needs to be converted to a ticket
        """
        try:
            with SessionLocal() as db:
                conversation = db.query(UnifiedChatHistory).filter(
                    UnifiedChatHistory.id == conversation_id
                ).first()
                
                if not conversation:
                    return ConversationAnalysis(
                        conversation_id=conversation_id,
                        analysis_result=ConversationAnalysisResult.INFORMATIONAL,
                        ticket_metadata=None,
                        confidence_score=0.0,
                        reasoning="Conversation not found",
                        extracted_entities={}
                    )
                
                # Analyze the conversation content
                user_message = conversation.user_message or ""
                bot_response = conversation.bot_response or ""
                
                # Extract entities and metadata
                extracted_entities = self._extract_entities(user_message, bot_response)
                
                # Determine if ticket is needed
                analysis_result = self._determine_ticket_need(user_message, bot_response, extracted_entities)
                
                # Calculate confidence score
                confidence_score = self._calculate_confidence_score(user_message, bot_response, analysis_result)
                
                # Generate ticket metadata if needed
                ticket_metadata = None
                if analysis_result in [ConversationAnalysisResult.NEEDS_TICKET, ConversationAnalysisResult.ESCALATION_REQUIRED]:
                    ticket_metadata = self._generate_ticket_metadata(user_message, bot_response, extracted_entities)
                
                # Generate reasoning
                reasoning = self._generate_reasoning(user_message, bot_response, analysis_result, extracted_entities)
                
                return ConversationAnalysis(
                    conversation_id=conversation_id,
                    analysis_result=analysis_result,
                    ticket_metadata=ticket_metadata,
                    confidence_score=confidence_score,
                    reasoning=reasoning,
                    extracted_entities=extracted_entities
                )
                
        except Exception as e:
            logger.error(f"Error analyzing conversation {conversation_id}: {e}")
            return ConversationAnalysis(
                conversation_id=conversation_id,
                analysis_result=ConversationAnalysisResult.INFORMATIONAL,
                ticket_metadata=None,
                confidence_score=0.0,
                reasoning=f"Analysis error: {str(e)}",
                extracted_entities={}
            )
    
    def _extract_entities(self, user_message: str, bot_response: str) -> Dict[str, Any]:
        """Extract entities and metadata from conversation"""
        entities = {
            "user_keywords": [],
            "bot_keywords": [],
            "mentioned_products": [],
            "mentioned_features": [],
            "error_codes": [],
            "urls": [],
            "email_addresses": [],
            "phone_numbers": []
        }
        
        combined_text = f"{user_message} {bot_response}".lower()
        
        # Extract error codes (pattern: ERROR_123, ERR-456, etc.)
        error_pattern = r'\b(?:error|err)[-_]?\d+\b'
        entities["error_codes"] = re.findall(error_pattern, combined_text, re.IGNORECASE)
        
        # Extract URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        entities["urls"] = re.findall(url_pattern, combined_text)
        
        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities["email_addresses"] = re.findall(email_pattern, combined_text)
        
        # Extract phone numbers (basic pattern)
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
        entities["phone_numbers"] = re.findall(phone_pattern, combined_text)
        
        # Extract product mentions (common telecom products)
        products = ["internet", "phone", "tv", "cable", "fiber", "broadband", "wifi", "router", "modem"]
        entities["mentioned_products"] = [p for p in products if p in combined_text]
        
        # Extract feature mentions
        features = ["speed", "bandwidth", "connection", "signal", "coverage", "plan", "package"]
        entities["mentioned_features"] = [f for f in features if f in combined_text]
        
        return entities
    
    def _determine_ticket_need(self, user_message: str, bot_response: str, entities: Dict[str, Any]) -> ConversationAnalysisResult:
        """Determine if the conversation needs to be converted to a ticket"""
        user_msg_lower = user_message.lower()
        bot_msg_lower = bot_response.lower()
        
        # Check for explicit problem indicators
        problem_indicators = [
            "problem", "issue", "error", "bug", "not working", "broken", "help",
            "support", "can't", "unable", "difficulty", "trouble", "wrong"
        ]
        
        has_problem = any(indicator in user_msg_lower for indicator in problem_indicators)
        
        # Check for resolution indicators in bot response
        resolution_indicators = [
            "resolved", "fixed", "solved", "working now", "should work", "try this",
            "here's how", "follow these steps", "solution"
        ]
        
        has_resolution = any(indicator in bot_msg_lower for indicator in resolution_indicators)
        
        # Check for escalation indicators
        escalation_indicators = [
            "contact support", "human agent", "escalate", "transfer", "speak to someone",
            "not resolved", "still having issues", "doesn't work"
        ]
        
        needs_escalation = any(indicator in user_msg_lower or indicator in bot_msg_lower 
                              for indicator in escalation_indicators)
        
        # Check for informational queries
        info_indicators = [
            "what is", "how does", "explain", "tell me about", "information",
            "learn more", "understand", "definition"
        ]
        
        is_informational = any(indicator in user_msg_lower for indicator in info_indicators)
        
        # Decision logic
        if needs_escalation:
            return ConversationAnalysisResult.ESCALATION_REQUIRED
        elif has_problem and not has_resolution:
            return ConversationAnalysisResult.NEEDS_TICKET
        elif has_problem and has_resolution:
            return ConversationAnalysisResult.RESOLVED
        elif is_informational:
            return ConversationAnalysisResult.INFORMATIONAL
        else:
            # Default based on message length and complexity
            if len(user_message) > 100 and has_problem:
                return ConversationAnalysisResult.NEEDS_TICKET
            else:
                return ConversationAnalysisResult.INFORMATIONAL
    
    def _calculate_confidence_score(self, user_message: str, bot_response: str, 
                                  analysis_result: ConversationAnalysisResult) -> float:
        """Calculate confidence score for the analysis"""
        score = 0.5  # Base score
        
        user_msg_lower = user_message.lower()
        bot_msg_lower = bot_response.lower()
        
        # Increase confidence based on clear indicators
        if analysis_result == ConversationAnalysisResult.NEEDS_TICKET:
            problem_words = ["problem", "issue", "error", "bug", "broken", "help"]
            problem_count = sum(1 for word in problem_words if word in user_msg_lower)
            score += min(problem_count * 0.1, 0.3)
            
        elif analysis_result == ConversationAnalysisResult.RESOLVED:
            resolution_words = ["resolved", "fixed", "solved", "working", "thanks"]
            resolution_count = sum(1 for word in resolution_words if word in bot_msg_lower)
            score += min(resolution_count * 0.1, 0.3)
            
        elif analysis_result == ConversationAnalysisResult.ESCALATION_REQUIRED:
            escalation_words = ["contact support", "human", "escalate", "transfer"]
            escalation_count = sum(1 for word in escalation_words if word in user_msg_lower or word in bot_msg_lower)
            score += min(escalation_count * 0.15, 0.4)
        
        # Adjust based on message length (longer messages often more complex)
        if len(user_message) > 200:
            score += 0.1
        elif len(user_message) < 50:
            score -= 0.1
        
        # Ensure score is within bounds
        return max(0.0, min(1.0, score))
    
    def _generate_ticket_metadata(self, user_message: str, bot_response: str, 
                                entities: Dict[str, Any]) -> TicketMetadata:
        """Generate ticket metadata from conversation analysis"""
        
        # Generate title (first 100 chars of user message, cleaned up)
        title = user_message[:100].strip()
        if len(user_message) > 100:
            title += "..."
        
        # Generate description
        description = f"Support ticket created from AI conversation:\n\n"
        description += f"Customer Query:\n{user_message}\n\n"
        description += f"AI Assistant Response:\n{bot_response}\n\n"
        
        if entities.get("error_codes"):
            description += f"Error Codes Mentioned: {', '.join(entities['error_codes'])}\n"
        
        if entities.get("mentioned_products"):
            description += f"Products Mentioned: {', '.join(entities['mentioned_products'])}\n"
        
        # Determine category
        category = self._determine_category(user_message)
        
        # Determine priority
        priority = self._determine_priority(user_message)
        
        # Generate tags
        tags = self._generate_tags(user_message, entities)
        
        # Calculate scores
        urgency_score = self._calculate_urgency_score(user_message)
        complexity_score = self._calculate_complexity_score(user_message, entities)
        sentiment_score = self._calculate_sentiment_score(user_message)
        
        return TicketMetadata(
            title=title,
            description=description,
            category=category,
            priority=priority,
            tags=tags,
            urgency_score=urgency_score,
            complexity_score=complexity_score,
            sentiment_score=sentiment_score
        )
    
    def _determine_category(self, user_message: str) -> TicketCategory:
        """Determine ticket category based on message content"""
        user_msg_lower = user_message.lower()
        
        category_scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in user_msg_lower)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        else:
            return TicketCategory.GENERAL
    
    def _determine_priority(self, user_message: str) -> TicketPriority:
        """Determine ticket priority based on message content"""
        user_msg_lower = user_message.lower()
        
        # Check for critical priority indicators
        for keyword in self.priority_keywords[TicketPriority.CRITICAL]:
            if keyword in user_msg_lower:
                return TicketPriority.CRITICAL
        
        # Check for high priority indicators
        for keyword in self.priority_keywords[TicketPriority.HIGH]:
            if keyword in user_msg_lower:
                return TicketPriority.HIGH
        
        # Check for low priority indicators
        for keyword in self.priority_keywords[TicketPriority.LOW]:
            if keyword in user_msg_lower:
                return TicketPriority.LOW
        
        # Default to medium priority
        return TicketPriority.MEDIUM
    
    def _generate_tags(self, user_message: str, entities: Dict[str, Any]) -> List[str]:
        """Generate tags for the ticket"""
        tags = []
        user_msg_lower = user_message.lower()
        
        # Add category-based tags
        if "billing" in user_msg_lower or "payment" in user_msg_lower:
            tags.append("billing")
        if "technical" in user_msg_lower or "error" in user_msg_lower:
            tags.append("technical")
        if "account" in user_msg_lower or "login" in user_msg_lower:
            tags.append("account")
        
        # Add product tags
        if entities.get("mentioned_products"):
            tags.extend(entities["mentioned_products"])
        
        # Add urgency tags
        if any(indicator in user_msg_lower for indicator in self.urgency_indicators):
            tags.append("urgent")
        
        # Add AI-generated tag
        tags.append("ai-generated")
        
        return list(set(tags))  # Remove duplicates
    
    def _calculate_urgency_score(self, user_message: str) -> float:
        """Calculate urgency score (0.0 to 1.0)"""
        user_msg_lower = user_message.lower()
        
        urgency_count = sum(1 for indicator in self.urgency_indicators 
                           if indicator in user_msg_lower)
        
        # Base score
        score = 0.3
        
        # Add points for urgency indicators
        score += min(urgency_count * 0.2, 0.6)
        
        # Add points for negative sentiment
        negative_count = sum(1 for word in self.negative_sentiment 
                           if word in user_msg_lower)
        score += min(negative_count * 0.1, 0.3)
        
        return min(1.0, score)
    
    def _calculate_complexity_score(self, user_message: str, entities: Dict[str, Any]) -> float:
        """Calculate complexity score (0.0 to 1.0)"""
        user_msg_lower = user_message.lower()
        
        # Base score based on message length
        score = min(len(user_message) / 500, 0.4)
        
        # Add points for complexity indicators
        complexity_count = sum(1 for indicator in self.complexity_indicators 
                             if indicator in user_msg_lower)
        score += min(complexity_count * 0.15, 0.3)
        
        # Add points for multiple products/features mentioned
        product_count = len(entities.get("mentioned_products", []))
        feature_count = len(entities.get("mentioned_features", []))
        score += min((product_count + feature_count) * 0.1, 0.3)
        
        return min(1.0, score)
    
    def _calculate_sentiment_score(self, user_message: str) -> float:
        """Calculate sentiment score (-1.0 to 1.0)"""
        user_msg_lower = user_message.lower()
        
        positive_count = sum(1 for word in self.positive_sentiment 
                           if word in user_msg_lower)
        negative_count = sum(1 for word in self.negative_sentiment 
                           if word in user_msg_lower)
        
        # Calculate net sentiment
        net_sentiment = positive_count - negative_count
        
        # Normalize to -1.0 to 1.0 range
        max_words = max(len(self.positive_sentiment), len(self.negative_sentiment))
        return max(-1.0, min(1.0, net_sentiment / max_words))
    
    def _generate_reasoning(self, user_message: str, bot_response: str, 
                          analysis_result: ConversationAnalysisResult, 
                          entities: Dict[str, Any]) -> str:
        """Generate human-readable reasoning for the analysis"""
        
        reasoning_parts = []
        
        if analysis_result == ConversationAnalysisResult.NEEDS_TICKET:
            reasoning_parts.append("Conversation indicates a problem or issue that requires support attention.")
            
        elif analysis_result == ConversationAnalysisResult.RESOLVED:
            reasoning_parts.append("Conversation shows a problem that was resolved by the AI assistant.")
            
        elif analysis_result == ConversationAnalysisResult.ESCALATION_REQUIRED:
            reasoning_parts.append("Conversation requires escalation to human support.")
            
        elif analysis_result == ConversationAnalysisResult.INFORMATIONAL:
            reasoning_parts.append("Conversation appears to be informational or educational in nature.")
        
        # Add specific indicators found
        user_msg_lower = user_message.lower()
        
        if any(word in user_msg_lower for word in ["urgent", "critical", "emergency"]):
            reasoning_parts.append("Urgent language detected in user message.")
            
        if entities.get("error_codes"):
            reasoning_parts.append(f"Error codes mentioned: {', '.join(entities['error_codes'])}")
            
        if entities.get("mentioned_products"):
            reasoning_parts.append(f"Products discussed: {', '.join(entities['mentioned_products'])}")
        
        return " ".join(reasoning_parts)

# Global analyzer instance
conversation_analyzer = ConversationAnalyzer()

# Utility functions
def analyze_conversation_for_ticket(conversation_id: int) -> ConversationAnalysis:
    """Analyze a conversation to determine if it needs a ticket"""
    return conversation_analyzer.analyze_conversation(conversation_id)

def should_create_ticket_from_conversation(conversation_id: int, threshold: float = 0.6) -> bool:
    """Determine if a ticket should be created based on analysis confidence"""
    analysis = analyze_conversation_for_ticket(conversation_id)
    
    return (analysis.analysis_result in [ConversationAnalysisResult.NEEDS_TICKET, 
                                       ConversationAnalysisResult.ESCALATION_REQUIRED] and
            analysis.confidence_score >= threshold)

def get_ticket_metadata_from_conversation(conversation_id: int) -> Optional[TicketMetadata]:
    """Get ticket metadata for a conversation"""
    analysis = analyze_conversation_for_ticket(conversation_id)
    return analysis.ticket_metadata