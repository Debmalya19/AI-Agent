from sqlalchemy.orm import Session
from models import KnowledgeEntry, Customer, Order, SupportIntent, SupportResponse, ChatHistory
from typing import List, Optional
import json

# Knowledge Entry CRUD operations
def create_knowledge_entry(db: Session, title: str, content: str, source: str = None):
    entry = KnowledgeEntry(title=title, content=content, source=source)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def get_knowledge_entries(db: Session, skip: int = 0, limit: int = 100):
    return db.query(KnowledgeEntry).offset(skip).limit(limit).all()

def search_knowledge_entries(db: Session, query: str):
    return db.query(KnowledgeEntry).filter(
        KnowledgeEntry.title.contains(query) | KnowledgeEntry.content.contains(query)
    ).all()

# Customer CRUD operations
def create_customer(db: Session, customer_id: int, name: str, email: str, phone: str = None, address: str = None):
    customer = Customer(
        customer_id=customer_id,
        name=name,
        email=email,
        phone=phone,
        address=address
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

def get_customer(db: Session, customer_id: int):
    return db.query(Customer).filter(Customer.customer_id == customer_id).first()

def get_customers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Customer).offset(skip).limit(limit).all()

# Order CRUD operations
def create_order(db: Session, order_id: int, customer_id: int, order_date: str, amount: float):
    order = Order(
        order_id=order_id,
        customer_id=customer_id,
        order_date=order_date,
        amount=amount
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order

def get_customer_orders(db: Session, customer_id: int):
    return db.query(Order).filter(Order.customer_id == customer_id).all()

# Support Knowledge CRUD operations
def get_support_response(db: Session, intent_name: str):
    intent = db.query(SupportIntent).filter(
        SupportIntent.intent_name.ilike(f"%{intent_name}%")
    ).first()
    
    if intent:
        response = db.query(SupportResponse).filter(
            SupportResponse.intent_id == intent.intent_id
        ).first()
        return response.response_text if response else None
    return None

def get_all_support_intents(db: Session):
    return db.query(SupportIntent).all()

# Chat History CRUD operations
def save_chat_history(db: Session, session_id: str, user_message: str, bot_response: str, 
                     tools_used: List[str] = None, sources: List[str] = None):
    chat_entry = ChatHistory(
        session_id=session_id,
        user_message=user_message,
        bot_response=bot_response,
        tools_used=json.dumps(tools_used) if tools_used else None,
        sources=json.dumps(sources) if sources else None
    )
    db.add(chat_entry)
    db.commit()
    db.refresh(chat_entry)
    return chat_entry

def get_chat_history(db: Session, session_id: str, limit: int = 10):
    return db.query(ChatHistory).filter(
        ChatHistory.session_id == session_id
    ).order_by(ChatHistory.created_at.desc()).limit(limit).all()

# Vector storage operations
def get_knowledge_for_embedding(db: Session):
    """Get all knowledge entries for embedding generation"""
    return db.query(KnowledgeEntry).all()

def update_knowledge_embedding(db: Session, entry_id: int, embedding: List[float]):
    """Update embedding for a knowledge entry"""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    if entry:
        entry.embedding = embedding
        db.commit()
        return True
    return False
