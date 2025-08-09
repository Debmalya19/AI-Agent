from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)
    content = Column(Text)
    source = Column(String(255))
    embedding = Column(JSON)  # Store vector embeddings
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, unique=True, index=True)
    name = Column(String(255))
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(50))
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"))
    order_date = Column(DateTime)
    amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    customer = relationship("Customer", back_populates="orders")

class SupportIntent(Base):
    __tablename__ = "support_intents"
    
    id = Column(Integer, primary_key=True, index=True)
    intent_id = Column(String(50), unique=True, index=True)
    intent_name = Column(String(255))
    description = Column(Text)
    category = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class SupportResponse(Base):
    __tablename__ = "support_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    intent_id = Column(String(50), ForeignKey("support_intents.intent_id"))
    response_text = Column(Text)
    response_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    intent = relationship("SupportIntent", back_populates="responses")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True)
    user_message = Column(Text)
    bot_response = Column(Text)
    tools_used = Column(JSON)
    sources = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# Add relationships
Customer.orders = relationship("Order", back_populates="customer")
SupportIntent.responses = relationship("SupportResponse", back_populates="intent")
