from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import sys

# Initialize SQLAlchemy
db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and user management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Field to store the corresponding customer ID in the ai-agent backend
    ai_agent_customer_id = db.Column(db.Integer, nullable=True)
    
    # Relationships
    tickets = db.relationship('Ticket', foreign_keys='Ticket.customer_id', lazy=True)
    assigned_tickets = db.relationship('Ticket', foreign_keys='Ticket.assigned_agent_id', lazy=True)
    comments = db.relationship('TicketComment', lazy=True, overlaps="ticket_comments")
    activities = db.relationship('TicketActivity', lazy=True, overlaps="ticket_activities")
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'is_admin': self.is_admin,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'ai_agent_customer_id': self.ai_agent_customer_id
        }