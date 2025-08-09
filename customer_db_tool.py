import pandas as pd
from typing import Optional
import logging

def get_customer_orders(customer_name: str) -> str:
    """
    Get order information for a specific customer by name.
    
    Args:
        customer_name: The customer's full name
        
    Returns:
        String containing order details for the customer
    """
    try:
        # Load customer knowledge base
        xls = pd.ExcelFile('data/customer_knowledge_base.xlsx')
        customers_df = pd.read_excel(xls, sheet_name='Customers')
        orders_df = pd.read_excel(xls, sheet_name='Orders')
        
        # Find customer by name
        customer = customers_df[customers_df['Name'].str.lower() == customer_name.lower()]
        
        if customer.empty:
            return f"No customer found with name: {customer_name}"
        
        customer_id = customer.iloc[0]['CustomerID']
        
        # Get orders for this customer
        customer_orders = orders_df[orders_df['CustomerID'] == customer_id]
        
        if customer_orders.empty:
            return f"No orders found for customer: {customer_name}"
        
        # Format response
        response = f"Here are your order details, {customer_name}:\n\n"
        for _, order in customer_orders.iterrows():
            response += f"Order ID: {order['OrderID']}\n"
            response += f"Order Date: {order['OrderDate']}\n"
            response += f"Amount: ${order['Amount']:.2f}\n\n"
        
        return response
        
    except Exception as e:
        logging.error(f"Error retrieving customer orders: {e}")
        return f"Sorry, I encountered an error retrieving your order information. Please contact human support."

def get_customer_by_email(email: str) -> Optional[dict]:
    """
    Get customer information by email address.
    
    Args:
        email: Customer's email address
        
    Returns:
        Dictionary with customer details or None if not found
    """
    try:
        xls = pd.ExcelFile('data/customer_knowledge_base.xlsx')
        customers_df = pd.read_excel(xls, sheet_name='Customers')
        
        customer = customers_df[customers_df['Email'].str.lower() == email.lower()]
        
        if customer.empty:
            return None
            
        return customer.iloc[0].to_dict()
        
    except Exception as e:
        logging.error(f"Error retrieving customer by email: {e}")
        return None
