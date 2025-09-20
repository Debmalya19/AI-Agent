"""
Social Media Models
Define database models for social media integration
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from backend.database import Base

class SocialMediaPlatform(enum.Enum):
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"

class SocialMediaMention(Base):
    __tablename__ = "social_media_mentions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(Enum(SocialMediaPlatform), nullable=False)
    external_id = Column(String(255), nullable=False)  # ID from the social media platform
    content = Column(Text, nullable=False)
    author_handle = Column(String(255), nullable=False)
    author_name = Column(String(255))
    posted_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Foreign keys
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="social_mentions")
    ticket = relationship("Ticket", back_populates="social_mentions")
    
    # Analysis fields
    sentiment_score = Column(Float)
    urgency_level = Column(Float)
    extracted_keywords = Column(String(500))

class SocialMediaResponse(Base):
    __tablename__ = "social_media_responses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    mention_id = Column(Integer, ForeignKey("social_media_mentions.id"), nullable=False)
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String(50))  # sent, failed, etc.
    
    # Relationship
    mention = relationship("SocialMediaMention", back_populates="responses")

# Update existing Customer model to include social media handles
def update_customer_model():
    from backend.models import Customer
    
    # Add social media fields to Customer model if they don't exist
    if not hasattr(Customer, 'twitter_handle'):
        Customer.twitter_handle = Column(String(255))
    if not hasattr(Customer, 'social_mentions'):
        Customer.social_mentions = relationship("SocialMediaMention", back_populates="customer")

# Update existing Ticket model to include social media relationship
def update_ticket_model():
    from backend.models import Ticket
    
    # Add social media relationship to Ticket model if it doesn't exist
    if not hasattr(Ticket, 'social_mentions'):
        Ticket.social_mentions = relationship("SocialMediaMention", back_populates="ticket")