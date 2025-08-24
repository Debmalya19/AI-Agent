from typing import Optional, List, Dict
import logging
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Customer, Order
from datetime import datetime

def get_customer_by_id(customer_id: int) -> Optional[Dict]:
    """
    Get customer information by customer ID from database.
    
    Args:
        customer_id: The customer's unique ID
        
    Returns:
        Dictionary with customer details or None if not found
    """
    try:
        db: Session = SessionLocal()
        
        customer = db.query(Customer).filter(
            Customer.customer_id == customer_id
        ).first()
        
        if not customer:
            db.close()
            return None
        
        customer_data = {
            'customer_id': customer.customer_id,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone,
            'address': customer.address,
            'created_at': customer.created_at.isoformat() if customer.created_at else None
        }
        
        db.close()
        return customer_data
        
    except Exception as e:
        logging.error(f"Error retrieving customer by ID: {e}")
        return None

def get_customer_by_email(email: str) -> Optional[Dict]:
    """
    Get customer information by email address from database.
    
    Args:
        email: Customer's email address
        
    Returns:
        Dictionary with customer details or None if not found
    """
    try:
        db: Session = SessionLocal()
        
        customer = db.query(Customer).filter(
            Customer.email.ilike(email)
        ).first()
        
        if not customer:
            db.close()
            return None
        
        customer_data = {
            'customer_id': customer.customer_id,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone,
            'address': customer.address,
            'created_at': customer.created_at.isoformat() if customer.created_at else None
        }
        
        db.close()
        return customer_data
        
    except Exception as e:
        logging.error(f"Error retrieving customer by email: {e}")
        return None

def get_customer_by_name(name: str) -> Optional[Dict]:
    """
    Get customer information by name from database.
    
    Args:
        name: Customer's full name
        
    Returns:
        Dictionary with customer details or None if not found
    """
    try:
        db: Session = SessionLocal()
        
        customer = db.query(Customer).filter(
            Customer.name.ilike(f"%{name}%")
        ).first()
        
        if not customer:
            db.close()
            return None
        
        customer_data = {
            'customer_id': customer.customer_id,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone,
            'address': customer.address,
            'created_at': customer.created_at.isoformat() if customer.created_at else None
        }
        
        db.close()
        return customer_data
        
    except Exception as e:
        logging.error(f"Error retrieving customer by name: {e}")
        return None

def get_customer_orders(customer_identifier: str, identifier_type: str = "name") -> str:
    """
    Get order information for a customer from database.
    
    Args:
        customer_identifier: Customer ID, email, or name
        identifier_type: Type of identifier ('id', 'email', or 'name')
        
    Returns:
        String containing order details for the customer
    """
    try:
        db: Session = SessionLocal()
        
        # Find customer based on identifier type
        if identifier_type == "id":
            customer = db.query(Customer).filter(
                Customer.customer_id == int(customer_identifier)
            ).first()
        elif identifier_type == "email":
            customer = db.query(Customer).filter(
                Customer.email.ilike(customer_identifier)
            ).first()
        else:  # name
            customer = db.query(Customer).filter(
                Customer.name.ilike(f"%{customer_identifier}%")
            ).first()
        
        if not customer:
            db.close()
            return f"No customer found with {identifier_type}: {customer_identifier}"
        
        # Get orders for this customer
        orders = db.query(Order).filter(
            Order.customer_id == customer.customer_id
        ).order_by(Order.order_date.desc()).all()
        
        if not orders:
            db.close()
            return f"No orders found for customer: {customer.name}"
        
        # Format response
        response = f"📋 **Order Details for {customer.name}**\n\n"
        response += f"**Customer ID:** {customer.customer_id}\n"
        response += f"**Email:** {customer.email}\n"
        response += f"**Phone:** {customer.phone}\n\n"
        
        response += "**Orders:**\n"
        for order in orders:
            response += f"\n📦 **Order #{order.order_id}**\n"
            response += f"   Date: {order.order_date.strftime('%Y-%m-%d') if order.order_date else 'N/A'}\n"
            response += f"   Amount: ${order.amount:.2f}\n"
            if order.created_at:
                response += f"   Created: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        db.close()
        return response
        
    except Exception as e:
        logging.error(f"Error retrieving customer orders: {e}")
        return f"Sorry, I encountered an error retrieving your order information. Please contact human support."

def get_all_customers() -> List[Dict]:
    """
    Get all customers from database.
    
    Returns:
        List of dictionaries with customer details
    """
    try:
        db: Session = SessionLocal()
        
        customers = db.query(Customer).all()
        
        customers_data = []
        for customer in customers:
            customers_data.append({
                'customer_id': customer.customer_id,
                'name': customer.name,
                'email': customer.email,
                'phone': customer.phone,
                'address': customer.address,
                'created_at': customer.created_at.isoformat() if customer.created_at else None
            })
        
        db.close()
        return customers_data
        
    except Exception as e:
        logging.error(f"Error retrieving all customers: {e}")
        return []

def search_customers(search_term: str) -> List[Dict]:
    """
    Search customers by name, email, or phone.
    
    Args:
        search_term: Search term to match against customer data
        
    Returns:
        List of dictionaries with matching customer details
    """
    try:
        db: Session = SessionLocal()
        
        customers = db.query(Customer).filter(
            Customer.name.ilike(f"%{search_term}%") |
            Customer.email.ilike(f"%{search_term}%") |
            Customer.phone.ilike(f"%{search_term}%")
        ).all()
        
        customers_data = []
        for customer in customers:
            customers_data.append({
                'customer_id': customer.customer_id,
                'name': customer.name,
                'email': customer.email,
                'phone': customer.phone,
                'address': customer.address,
                'created_at': customer.created_at.isoformat() if customer.created_at else None
            })
        
        db.close()
        return customers_data
        
    except Exception as e:
        logging.error(f"Error searching customers: {e}")
        return []

# Create LangChain tools
from langchain.tools import Tool

customer_lookup_tool = Tool.from_function(
    func=get_customer_orders,
    name="CustomerOrderLookup",
    description="Use this tool to look up customer orders by name, email, or customer ID. Input should be the customer identifier."
)

customer_search_tool = Tool.from_function(
    func=search_customers,
    name="CustomerSearch",
    description="Use this tool to search for customers by name, email, or phone number. Input should be the search term."
)

if __name__ == "__main__":
    # Test the functions
    print("Testing customer database tools...")
    
    # Test customer lookup
    print("\n1. Customer lookup by name:")
    print(get_customer_orders("John Doe", "name"))
    
    print("\n2. Customer lookup by email:")
    print(get_customer_orders("john@example.com", "email"))
    
    print("\n3. Customer lookup by ID:")
    print(get_customer_orders("1001", "id"))
    
    print("\n4. Search customers:")
    customers = search_customers("john")
    for customer in customers:
        print(f"Found: {customer['name']} ({customer['email']})")
