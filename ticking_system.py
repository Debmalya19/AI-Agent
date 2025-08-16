"""
Ticking System Module
A comprehensive ticket management system that uses database as context retrieval
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from database import Base, get_db
from models import Customer, Ticket, TicketComment, TicketActivity, TicketStatus, TicketPriority, TicketCategory

# All Ticket-related classes are now imported from models.py
# This file can contain ticket system specific functionality
