"""
Enhanced Context Retrieval Engine for the AI agent memory layer.
Extends existing ContextMemory class with database integration, semantic similarity,
context relevance ranking, and performance caching mechanisms.
"""

import logging
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
import json
import re
from collections import defaultdict

from database import SessionLocal
from memory_config import MemoryConfig, load_config
from memory_models import (
    EnhancedChatHistory,
    MemoryContextCache,
    ToolUsageMetrics,
    ConversationSummary,
    ContextEntryDTO,
    create_context_cache_entry
)
from tools import ContextMemory


class SemanticFeatures:
    """Container for semantic features extracted from text"""
    
    def __init__(self, text: str):
        self.original_text = text
        self.word_count = len(text.split())
        self.keywords = self._extract_keywords(text)
        self.entities = self._extract_entities(text)
        self.topics = self._extract_topics(text)
        self.sentiment_indicators = self._extract_sentiment_indicators(text)
        self.technical_terms = self._extract_technical_terms(text)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        # Simple keyword extraction - can be enhanced with NLP libraries
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # Count frequency and return top keywords
        word_freq = defaultdict(int)
        for word in keywords:
            word_freq[word] += 1
        
        return sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)[:10]
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract named entities (simple pattern-based approach)"""
        entities = []
        
        # Extract potential product names, service names, etc.
        patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Proper nouns
            r'\b\d+GB\b|\b\d+MB\b',  # Data amounts
            r'£\d+(?:\.\d{2})?',  # Prices
            r'\b\d{4}-\d{2}-\d{2}\b',  # Dates
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            entities.extend(matches)
        
        return list(set(entities))
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topic categories from text"""
        topics = []
        text_lower = text.lower()
        
        # Define topic keywords
        topic_keywords = {
            'billing': ['bill', 'payment', 'charge', 'cost', 'price', 'invoice', 'refund'],
            'technical': ['error', 'problem', 'issue', 'bug', 'fix', 'troubleshoot', 'setup'],
            'mobile': ['mobile', 'phone', 'sim', 'data', 'roaming', 'network', 'signal'],
            'broadband': ['broadband', 'internet', 'wifi', 'router', 'connection', 'speed'],
            'support': ['help', 'support', 'contact', 'assistance', 'service'],
            'account': ['account', 'login', 'password', 'profile', 'settings'],
            'plans': ['plan', 'package', 'upgrade', 'downgrade', 'contract', 'tariff']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _extract_sentiment_indicators(self, text: str) -> Dict[str, int]:
        """Extract sentiment indicators from text"""
        text_lower = text.lower()
        
        positive_words = ['good', 'great', 'excellent', 'happy', 'satisfied', 'love', 'perfect', 'amazing', 'wonderful']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'disappointed', 'frustrated', 'angry', 'horrible', 'worst']
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        return {
            'positive': positive_count,
            'negative': negative_count,
            'neutral': 1 if positive_count == negative_count else 0
        }
    
    def _extract_technical_terms(self, text: str) -> List[str]:
        """Extract technical terms and abbreviations"""
        technical_patterns = [
            r'\b[A-Z]{2,}\b',  # Abbreviations like BT, SIM
            r'\b[A-Z][a-z]*[A-Z][a-z]*\b',  # CamelCase like WiFi
            r'\b\w+\.\w+\b',   # Domain-like patterns
            r'\b\d+[A-Za-z]+\b',  # Numbers with units
        ]
        
        technical_terms = []
        for pattern in technical_patterns:
            matches = re.findall(pattern, text)
            technical_terms.extend(matches)
        
        return list(set(technical_terms))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'word_count': self.word_count,
            'keywords': self.keywords,
            'entities': self.entities,
            'topics': self.topics,
            'sentiment_indicators': self.sentiment_indicators,
            'technical_terms': self.technical_terms
        }


class MemoryCache:
    """In-memory cache for frequently accessed context data"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, datetime] = {}
        self._hit_count = 0
        self._miss_count = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now(timezone.utc) - entry['timestamp'] < timedelta(seconds=self.ttl_seconds):
                self._access_times[key] = datetime.now(timezone.utc)
                self._hit_count += 1
                return entry['data']
            else:
                # Expired
                del self._cache[key]
                del self._access_times[key]
        
        self._miss_count += 1
        return None
    
    def put(self, key: str, data: Any) -> None:
        """Put item in cache"""
        # Clean up if at capacity
        if len(self._cache) >= self.max_size:
            self._evict_oldest()
        
        self._cache[key] = {
            'data': data,
            'timestamp': datetime.now(timezone.utc)
        }
        self._access_times[key] = datetime.now(timezone.utc)
    
    def _evict_oldest(self) -> None:
        """Evict oldest accessed item"""
        if not self._access_times:
            return
        
        oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        del self._cache[oldest_key]
        del self._access_times[oldest_key]
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate"""
        total = self._hit_count + self._miss_count
        return self._hit_count / total if total > 0 else 0.0
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        self._access_times.clear()
        self._hit_count = 0
        self._miss_count = 0


class ContextRetrievalEngine:
    """
    Enhanced context retrieval engine with database integration,
    semantic similarity calculation, and intelligent caching.
    """
    
    def __init__(self, db_session: Optional[Session] = None, cache: Optional[MemoryCache] = None, 
                 config: Optional[MemoryConfig] = None):
        """
        Initialize the Context Retrieval Engine.
        
        Args:
            db_session: Database session (optional)
            cache: Memory cache instance (optional)
            config: Memory configuration (optional)
        """
        self.db_session = db_session
        self._session_factory = SessionLocal if not db_session else None
        self.cache = cache or MemoryCache()
        self.config = config or load_config()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, self.config.log_level))
        
        # Performance tracking
        self._operation_times: Dict[str, List[float]] = {}
        
        # Initialize simple legacy memory for backward compatibility (avoid circular import)
        self.legacy_memory = None  # Will be initialized lazily if needed
        
        self.logger.info("Context Retrieval Engine initialized")
    
    def _get_session(self) -> Session:
        """Get database session"""
        if self.db_session:
            return self.db_session
        return self._session_factory()
    
    def _close_session(self, session: Session) -> None:
        """Close database session if we created it"""
        if not self.db_session:
            session.close()
    
    def _track_operation_time(self, operation: str, duration: float) -> None:
        """Track operation execution time"""
        if operation not in self._operation_times:
            self._operation_times[operation] = []
        
        self._operation_times[operation].append(duration)
        
        # Keep only last 100 measurements
        if len(self._operation_times[operation]) > 100:
            self._operation_times[operation] = self._operation_times[operation][-100:]
    
    def get_relevant_context(self, query: str, user_id: str, 
                           context_types: Optional[List[str]] = None, 
                           limit: int = 10) -> List[ContextEntryDTO]:
        """
        Get relevant context entries for a query with intelligent ranking.
        
        Args:
            query: Query string to find relevant context for
            user_id: User ID to filter context by
            context_types: Types of context to include (optional)
            limit: Maximum number of context entries to return
            
        Returns:
            List of relevant context entries ranked by relevance
        """
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(query, user_id, context_types, limit)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.logger.debug(f"Cache hit for context retrieval: {cache_key}")
                return cached_result
            
            # Get context from database
            db_contexts = self._get_database_context(query, user_id, context_types, limit)
            
            # Get context from legacy memory for backward compatibility
            legacy_contexts = self._get_legacy_context(query, limit)
            
            # Combine and rank all contexts
            all_contexts = db_contexts + legacy_contexts
            ranked_contexts = self.rank_context_relevance(all_contexts, query)
            
            # Apply limit
            result = ranked_contexts[:limit]
            
            # Cache the result
            self.cache.put(cache_key, result)
            
            duration = time.time() - start_time
            self._track_operation_time('get_relevant_context', duration)
            
            if self.config.log_memory_operations:
                self.logger.info(f"Retrieved {len(result)} context entries in {duration:.3f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error retrieving context: {e}")
            return []
    
    def _generate_cache_key(self, query: str, user_id: str, 
                          context_types: Optional[List[str]], limit: int) -> str:
        """Generate cache key for context retrieval"""
        key_parts = [query, user_id, str(limit)]
        if context_types:
            key_parts.append(','.join(sorted(context_types)))
        
        key_string = '|'.join(key_parts)
        return f"context_{hashlib.md5(key_string.encode()).hexdigest()}"
    
    def _get_database_context(self, query: str, user_id: str, 
                            context_types: Optional[List[str]], limit: int) -> List[ContextEntryDTO]:
        """Get context entries from database"""
        session = None
        contexts = []
        
        try:
            session = self._get_session()
            
            # Query enhanced chat history
            query_builder = session.query(EnhancedChatHistory).filter(
                and_(
                    EnhancedChatHistory.user_id == user_id,
                    EnhancedChatHistory.created_at >= datetime.now(timezone.utc) - timedelta(
                        days=self.config.retention.conversation_retention_days
                    )
                )
            )
            
            # Add text search if supported by database
            if hasattr(session.bind.dialect, 'name') and session.bind.dialect.name == 'postgresql':
                # Use PostgreSQL full-text search
                search_query = ' | '.join(query.split())  # OR search
                query_builder = query_builder.filter(
                    or_(
                        text("to_tsvector('english', user_message) @@ to_tsquery(:search)").params(search=search_query),
                        text("to_tsvector('english', bot_response) @@ to_tsquery(:search)").params(search=search_query)
                    )
                )
            
            conversations = query_builder.order_by(desc(EnhancedChatHistory.created_at)).limit(limit * 2).all()
            
            # Convert to context entries
            for conv in conversations:
                # Add user message as context
                contexts.append(ContextEntryDTO(
                    content=conv.user_message,
                    source=f"db_conversation_{conv.id}",
                    relevance_score=self.calculate_context_similarity(query, conv.user_message),
                    context_type="user_message",
                    timestamp=conv.created_at,
                    metadata={
                        'session_id': conv.session_id,
                        'tools_used': conv.tools_used or [],
                        'response_quality': conv.response_quality_score,
                        'conversation_id': conv.id
                    }
                ))
                
                # Add bot response as context
                contexts.append(ContextEntryDTO(
                    content=conv.bot_response,
                    source=f"db_conversation_{conv.id}",
                    relevance_score=self.calculate_context_similarity(query, conv.bot_response),
                    context_type="bot_response",
                    timestamp=conv.created_at,
                    metadata={
                        'session_id': conv.session_id,
                        'tools_used': conv.tools_used or [],
                        'response_quality': conv.response_quality_score,
                        'conversation_id': conv.id
                    }
                ))
            
            # Query cached context entries
            cached_contexts = session.query(MemoryContextCache).filter(
                and_(
                    MemoryContextCache.user_id == user_id,
                    MemoryContextCache.expires_at > datetime.now(timezone.utc)
                )
            ).order_by(desc(MemoryContextCache.relevance_score)).limit(limit).all()
            
            for cached in cached_contexts:
                contexts.append(ContextEntryDTO(
                    content=str(cached.context_data.get('content', '')),
                    source=f"cache_{cached.id}",
                    relevance_score=cached.relevance_score or 0.0,
                    context_type=cached.context_type,
                    timestamp=cached.created_at,
                    metadata=cached.context_data
                ))
            
            return contexts
            
        except Exception as e:
            self.logger.error(f"Error getting database context: {e}")
            return []
        
        finally:
            if session:
                self._close_session(session)
    
    def _get_legacy_context(self, query: str, limit: int) -> List[ContextEntryDTO]:
        """Get context from legacy ContextMemory for backward compatibility"""
        try:
            # Initialize legacy memory lazily to avoid circular imports
            if self.legacy_memory is None:
                # Create a simple in-memory store instead of importing ContextMemory
                self.legacy_memory = {'conversations': []}
            
            # For now, return empty list since we don't have legacy data
            # This can be enhanced later if needed
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting legacy context: {e}")
            return []
    
    def rank_context_relevance(self, contexts: List[ContextEntryDTO], query: str) -> List[ContextEntryDTO]:
        """
        Rank context entries by relevance to the query.
        
        Args:
            contexts: List of context entries to rank
            query: Query to rank against
            
        Returns:
            List of context entries sorted by relevance (highest first)
        """
        start_time = time.time()
        
        try:
            # Calculate enhanced relevance scores
            for context in contexts:
                # Base similarity score
                base_score = self.calculate_context_similarity(query, context.content)
                
                # Apply boosting factors
                boosted_score = self._apply_relevance_boosting(base_score, context, query)
                
                # Update relevance score
                context.relevance_score = boosted_score
            
            # Filter by minimum relevance threshold
            filtered_contexts = [
                ctx for ctx in contexts 
                if ctx.relevance_score >= self.config.quality.min_relevance_score
            ]
            
            # If no contexts meet threshold, return top 3 anyway
            if not filtered_contexts and contexts:
                contexts.sort(key=lambda x: x.relevance_score, reverse=True)
                filtered_contexts = contexts[:3]
            
            # Sort by relevance score (descending)
            filtered_contexts.sort(key=lambda x: x.relevance_score, reverse=True)
            
            duration = time.time() - start_time
            self._track_operation_time('rank_context_relevance', duration)
            
            return filtered_contexts
            
        except Exception as e:
            self.logger.error(f"Error ranking context relevance: {e}")
            return contexts
    
    def _apply_relevance_boosting(self, base_score: float, context: ContextEntryDTO, query: str) -> float:
        """Apply boosting factors to relevance score"""
        boosted_score = base_score
        
        # Boost recent contexts
        if context.timestamp:
            age_hours = (datetime.now(timezone.utc) - context.timestamp).total_seconds() / 3600
            if age_hours < 24:  # Recent context
                boosted_score *= 1.2
            elif age_hours < 168:  # Within a week
                boosted_score *= 1.1
        
        # Boost high-quality responses
        if context.metadata.get('response_quality', 0) > 0.8:
            boosted_score *= 1.15
        
        # Boost contexts with successful tool usage
        tools_used = context.metadata.get('tools_used', [])
        if tools_used and len(tools_used) > 0:
            boosted_score *= 1.1
        
        # Boost contexts with matching topics
        query_features = self.extract_semantic_features(query)
        context_features = self.extract_semantic_features(context.content)
        
        # Topic matching boost
        common_topics = set(query_features.topics) & set(context_features.topics)
        if common_topics:
            boosted_score *= (1.0 + len(common_topics) * 0.1)
        
        # Entity matching boost
        common_entities = set(query_features.entities) & set(context_features.entities)
        if common_entities:
            boosted_score *= (1.0 + len(common_entities) * 0.05)
        
        return min(boosted_score, 1.0)  # Cap at 1.0
    
    def extract_semantic_features(self, text: str) -> SemanticFeatures:
        """
        Extract semantic features from text for similarity calculation.
        
        Args:
            text: Text to extract features from
            
        Returns:
            SemanticFeatures object with extracted features
        """
        try:
            return SemanticFeatures(text)
        except Exception as e:
            self.logger.error(f"Error extracting semantic features: {e}")
            return SemanticFeatures("")  # Return empty features
    
    def calculate_context_similarity(self, query: str, context: str) -> float:
        """
        Calculate similarity between query and context using multiple methods.
        
        Args:
            query: Query string
            context: Context string to compare against
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not query or not context:
            return 0.0
        
        try:
            # Extract features for both query and context
            query_features = self.extract_semantic_features(query)
            context_features = self.extract_semantic_features(context)
            
            # Calculate different similarity components
            scores = []
            
            # 1. Keyword overlap similarity
            keyword_sim = self._calculate_keyword_similarity(query_features.keywords, context_features.keywords)
            scores.append(keyword_sim * 0.3)  # 30% weight
            
            # 2. Topic similarity
            topic_sim = self._calculate_topic_similarity(query_features.topics, context_features.topics)
            scores.append(topic_sim * 0.25)  # 25% weight
            
            # 3. Entity similarity
            entity_sim = self._calculate_entity_similarity(query_features.entities, context_features.entities)
            scores.append(entity_sim * 0.2)  # 20% weight
            
            # 4. Simple word overlap (fallback)
            word_sim = self._calculate_word_overlap_similarity(query, context)
            scores.append(word_sim * 0.25)  # 25% weight
            
            # Combine scores
            final_score = sum(scores)
            
            return min(final_score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating context similarity: {e}")
            # Fallback to simple word overlap
            return self._calculate_word_overlap_similarity(query, context)
    
    def _calculate_keyword_similarity(self, query_keywords: List[str], context_keywords: List[str]) -> float:
        """Calculate similarity based on keyword overlap"""
        if not query_keywords or not context_keywords:
            return 0.0
        
        query_set = set(query_keywords[:10])  # Top 10 keywords
        context_set = set(context_keywords[:10])
        
        intersection = query_set & context_set
        union = query_set | context_set
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_topic_similarity(self, query_topics: List[str], context_topics: List[str]) -> float:
        """Calculate similarity based on topic overlap"""
        if not query_topics or not context_topics:
            return 0.0
        
        query_set = set(query_topics)
        context_set = set(context_topics)
        
        intersection = query_set & context_set
        union = query_set | context_set
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_entity_similarity(self, query_entities: List[str], context_entities: List[str]) -> float:
        """Calculate similarity based on entity overlap"""
        if not query_entities or not context_entities:
            return 0.0
        
        query_set = set(query_entities)
        context_set = set(context_entities)
        
        intersection = query_set & context_set
        union = query_set | context_set
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_word_overlap_similarity(self, query: str, context: str) -> float:
        """Calculate simple word overlap similarity (fallback method)"""
        if not query or not context:
            return 0.0
        
        query_words = set(query.lower().split())
        context_words = set(context.lower().split())
        
        intersection = query_words & context_words
        union = query_words | context_words
        
        return len(intersection) / len(union) if union else 0.0
    
    def cache_context(self, key: str, context_data: Dict[str, Any], 
                     context_type: str, ttl_hours: int = 24, 
                     user_id: Optional[str] = None, relevance_score: float = 0.0) -> bool:
        """
        Cache context data for performance optimization.
        
        Args:
            key: Cache key
            context_data: Context data to cache
            context_type: Type of context
            ttl_hours: Time to live in hours
            user_id: User ID (optional)
            relevance_score: Relevance score for ranking
            
        Returns:
            bool: True if cached successfully
        """
        session = None
        
        try:
            # Cache in memory
            self.cache.put(key, context_data)
            
            # Cache in database for persistence
            if self.config.enable_database_storage:
                session = self._get_session()
                
                expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
                
                cache_entry = create_context_cache_entry(
                    cache_key=key,
                    context_data=context_data,
                    context_type=context_type,
                    expires_at=expires_at,
                    user_id=user_id,
                    relevance_score=relevance_score
                )
                
                session.add(cache_entry)
                session.commit()
            
            return True
            
        except Exception as e:
            if session:
                session.rollback()
            self.logger.error(f"Error caching context: {e}")
            return False
        
        finally:
            if session:
                self._close_session(session)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        return {
            'hit_rate': self.cache.get_hit_rate(),
            'cache_size': len(self.cache._cache),
            'max_size': self.cache.max_size,
            'operation_times': {
                op: {
                    'avg': sum(times) / len(times) if times else 0,
                    'count': len(times)
                }
                for op, times in self._operation_times.items()
            }
        }
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        self.cache.clear()
        self.logger.info("Context cache cleared")