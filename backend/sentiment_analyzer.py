"""
Sentiment Analysis Module
Analyzes text content to determine sentiment and extract relevant information
"""

from typing import Dict, Tuple, List, Optional
import re
from dataclasses import dataclass
from enum import Enum

class SentimentCategory(Enum):
    VERY_NEGATIVE = 1
    NEGATIVE = 2
    NEUTRAL = 3
    POSITIVE = 4
    VERY_POSITIVE = 5

@dataclass
class SentimentAnalysis:
    sentiment: SentimentCategory
    confidence: float
    keywords: List[str]
    entities: Dict[str, str]
    urgency_level: float

class SentimentAnalyzer:
    """Analyzes text content for sentiment and key information"""
    
    def __init__(self):
        # Initialize sentiment dictionaries
        self.positive_words = {
            'great', 'awesome', 'excellent', 'good', 'happy', 'pleased',
            'satisfied', 'thanks', 'love', 'wonderful', 'perfect'
        }
        
        self.negative_words = {
            'bad', 'terrible', 'awful', 'horrible', 'disappointed', 'angry',
            'frustrated', 'poor', 'issue', 'problem', 'error', 'fail'
        }
        
        self.urgent_words = {
            'urgent', 'asap', 'emergency', 'critical', 'serious',
            'immediately', 'urgent', 'broken', 'down', 'outage'
        }
        
        self.entity_patterns = {
            'customer_id': r'(?i)(?:customer|cust|client|account)[\s-]*(?:id|number|#):?\s*(\d+)',
            'order_id': r'(?i)(?:order|transaction)[\s-]*(?:id|number|#):?\s*(\d+)',
            'email': r'[\w\.-]+@[\w\.-]+\.\w+',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        }
    
    def analyze_text(self, text: str) -> SentimentAnalysis:
        """
        Analyze text content and return sentiment analysis results
        """
        # Convert to lowercase for analysis
        text_lower = text.lower()
        words = set(re.findall(r'\w+', text_lower))
        
        # Calculate sentiment scores
        positive_score = len(words.intersection(self.positive_words))
        negative_score = len(words.intersection(self.negative_words))
        urgency_score = len(words.intersection(self.urgent_words))
        
        # Calculate overall sentiment
        sentiment_score = positive_score - negative_score
        
        # Determine sentiment category
        if sentiment_score < -2:
            sentiment = SentimentCategory.VERY_NEGATIVE
        elif sentiment_score < 0:
            sentiment = SentimentCategory.NEGATIVE
        elif sentiment_score == 0:
            sentiment = SentimentCategory.NEUTRAL
        elif sentiment_score <= 2:
            sentiment = SentimentCategory.POSITIVE
        else:
            sentiment = SentimentCategory.VERY_POSITIVE
            
        # Calculate confidence based on word count
        total_sentiment_words = positive_score + negative_score
        confidence = min(total_sentiment_words / len(words), 1.0) if words else 0.5
        
        # Extract entities using patterns
        entities = {}
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                entities[entity_type] = matches[0]
        
        # Extract keywords (significant words that might indicate the topic)
        keywords = self._extract_keywords(text_lower)
        
        # Calculate urgency level (0-1 scale)
        urgency_level = min((urgency_score * 0.5) + 
                          (1.0 if sentiment == SentimentCategory.VERY_NEGATIVE else 0.0) +
                          (0.5 if sentiment == SentimentCategory.NEGATIVE else 0.0), 1.0)
        
        return SentimentAnalysis(
            sentiment=sentiment,
            confidence=confidence,
            keywords=keywords,
            entities=entities,
            urgency_level=urgency_level
        )
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract significant keywords from the text
        """
        # Common words to ignore
        stop_words = {'the', 'is', 'at', 'which', 'on', 'in', 'a', 'an', 'and', 'or',
                     'but', 'to', 'for', 'with', 'about', 'from', 'as', 'of'}
                     
        # Extract words and filter out stop words
        words = [word for word in re.findall(r'\w+', text.lower())
                if word not in stop_words and len(word) > 2]
        
        # Count word frequencies
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
            
        # Sort by frequency and return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:10]]  # Return top 10 keywords

def analyze_social_media_content(content: str) -> Dict[str, any]:
    """
    Analyze social media content and return structured analysis
    """
    analyzer = SentimentAnalyzer()
    analysis = analyzer.analyze_text(content)
    
    return {
        'sentiment': analysis.sentiment.name,
        'confidence': analysis.confidence,
        'keywords': analysis.keywords,
        'entities': analysis.entities,
        'urgency_level': analysis.urgency_level,
        'priority_recommendation': 'HIGH' if analysis.urgency_level > 0.7 else 'MEDIUM'
    }