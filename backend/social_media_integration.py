"""
Social Media Integration Module
Handles social media platform interactions and ticket creation based on mentions
"""

import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .models import Customer, Ticket, TicketStatus, TicketPriority, TicketCategory
from .database import SessionLocal
from .ticking_service import TickingService
from .twitter_client import TwitterClient
from .social_media_models import SocialMediaMention, SocialMediaResponse, SocialMediaPlatform
from .sentiment_analyzer import analyze_social_media_content, SentimentCategory

logger = logging.getLogger(__name__)

class SocialMediaMonitor:
    """Handles monitoring and processing of social media mentions"""
    
    def __init__(self, db_session: Session = None):
        self.db = db_session or SessionLocal()
        self.ticking_service = TickingService(self.db)
        self.twitter_client = TwitterClient()
    
    def process_tweet(self, tweet_data: Dict[str, Any]) -> Optional[int]:
        """
        Process a tweet mention and create a ticket if necessary
        Returns the ticket ID if created, None otherwise
        """
        try:
            # Extract customer ID from tweet text or user profile
            # This would need to be customized based on your customer ID format
            customer_id = self._extract_customer_id(tweet_data)
            
            # Analyze sentiment first
            tweet_text = tweet_data.get("text", "")
            sentiment_analysis = analyze_social_media_content(tweet_text)
            
            # Skip ticket creation for positive sentiments
            if sentiment_analysis.sentiment in [SentimentCategory.POSITIVE, SentimentCategory.VERY_POSITIVE]:
                logger.info(f"Skipping ticket creation for positive sentiment tweet: {tweet_text}")
                return None
            
            # Create ticket content for non-positive sentiments
            title = f"Social Media Mention - Twitter"
            description = self._create_ticket_description(tweet_data)
            
            # Determine ticket priority based on sentiment and content
            priority = self._determine_priority(tweet_data)
            
            # Create the ticket
            ticket = self.ticking_service.create_ticket(
                title=title,
                description=description,
                user_id=customer_id,
                priority=priority,
                category=TicketCategory.SOCIAL_MEDIA,
                tags=["twitter", "social-media"],
                ticket_metadata={
                    "source": "twitter",
                    "tweet_id": tweet_data.get("id"),
                    "tweet_timestamp": tweet_data.get("created_at"),
                    "user_handle": tweet_data.get("user", {}).get("screen_name"),
                }
            )
            
            return ticket.id
            
        except Exception as e:
            # Log the error and return None
            print(f"Error processing tweet: {str(e)}")
            return None
        
    def _extract_customer_id(self, tweet_data: Dict[str, Any]) -> Optional[int]:
        """
        Extract customer ID from tweet text or user profile
        Customize this method based on your customer ID format
        """
        # Example: Look for customer ID in tweet text
        text = tweet_data.get("text", "").lower()
        
        # Pattern: "customerid: 12345" or "#custid12345"
        import re
        patterns = [
            r"customer\s*id\s*:\s*(\d+)",
            r"#custid(\d+)",
            r"id:\s*(\d+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        # If no customer ID found in text, could try to match against user's profile
        return None
        
    def _create_ticket_description(self, tweet_data: Dict[str, Any]) -> str:
        """Create a detailed ticket description from tweet data including sentiment analysis"""
        user = tweet_data.get("user", {})
        tweet_text = tweet_data.get("text", "")
        created_at = tweet_data.get("created_at", datetime.now(timezone.utc).isoformat())
        
        # Analyze tweet content
        analysis = analyze_social_media_content(tweet_text)
        
        description = f"""Social Media Mention Details:
Tweet: {tweet_text}
Posted by: @{user.get("screen_name")}
Timestamp: {created_at}

Content Analysis:
Sentiment: {analysis['sentiment']}
Urgency Level: {analysis['urgency_level']:.2f}
Key Topics: {', '.join(analysis['keywords'])}
Identified Entities: {', '.join(f'{k}: {v}' for k, v in analysis['entities'].items())}

User Profile:
Name: {user.get("name")}
Followers: {user.get("followers_count")}
Account Created: {user.get("created_at")}
"""
        return description
        
    def _determine_priority(self, tweet_data: Dict[str, Any]) -> TicketPriority:
        """
        Determine ticket priority based on tweet content, sentiment analysis, and metadata
        """
        text = tweet_data.get("text", "")
        user = tweet_data.get("user", {})
        
        # Analyze tweet content
        analysis = analyze_social_media_content(text)
        
        # High priority if:
        # 1. High urgency level from sentiment analysis
        # 2. Very negative sentiment
        # 3. High follower count (influential user)
        if (analysis['urgency_level'] > 0.7 or 
            analysis['sentiment'] == 'VERY_NEGATIVE' or
            user.get("followers_count", 0) > 10000):
            return TicketPriority.HIGH
            
        # Medium priority if:
        # 1. Medium urgency level
        # 2. Negative sentiment
        # 3. Moderate follower count
        elif (analysis['urgency_level'] > 0.3 or
              analysis['sentiment'] == 'NEGATIVE' or
              user.get("followers_count", 0) > 1000):
            return TicketPriority.MEDIUM
            
        # Default to low priority
        return TicketPriority.LOW