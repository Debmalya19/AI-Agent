import pandas as pd
from database import SessionLocal
from models import KnowledgeEntry, Customer, Order, SupportIntent, SupportResponse
import json
from datetime import datetime

def migrate_knowledge_txt():
    """Migrate knowledge.txt to database"""
    db = SessionLocal()
    try:
        with open("data/knowledge.txt", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Parse Q&A pairs
        import re
        pattern = re.compile(r"Q:\s*(.+?)\nA:\s*(.+?)(?=\nQ:|\Z)", re.DOTALL)
        matches = pattern.findall(content)
        
        for q, a in matches:
            entry = KnowledgeEntry(
                title=q.strip(),
                content=a.strip(),
                source="data/knowledge.txt"
            )
            db.add(entry)
        
        db.commit()
        print(f"Migrated {len(matches)} knowledge entries from knowledge.txt")
    except Exception as e:
        print(f"Error migrating knowledge.txt: {e}")
        db.rollback()
    finally:
        db.close()

def migrate_customer_knowledge_base():
    """Migrate customer_knowledge_base.xlsx to database"""
    db = SessionLocal()
    try:
        # Load Excel file
        xls = pd.ExcelFile('data/customer_knowledge_base.xlsx')
        
        # Migrate Customers
        customers_df = pd.read_excel(xls, sheet_name='Customers')
        for _, row in customers_df.iterrows():
            customer = Customer(
                customer_id=int(row['CustomerID']),
                name=row['Name'],
                email=row['Email'],
                phone=row['Phone'],
                address=row['Address']
            )
            db.add(customer)
        
        # Migrate Orders
        orders_df = pd.read_excel(xls, sheet_name='Orders')
        for _, row in orders_df.iterrows():
            order = Order(
                order_id=int(row['OrderID']),
                customer_id=int(row['CustomerID']),
                order_date=datetime.strptime(row['OrderDate'], '%Y-%m-%d'),
                amount=float(row['Amount'])
            )
            db.add(order)
        
        db.commit()
        print(f"Migrated {len(customers_df)} customers and {len(orders_df)} orders")
    except Exception as e:
        print(f"Error migrating customer knowledge base: {e}")
        db.rollback()
    finally:
        db.close()

def migrate_support_knowledge_base():
    """Migrate customer_support_knowledge_base.xlsx to database"""
    db = SessionLocal()
    try:
        xls = pd.ExcelFile('data/customer_support_knowledge_base.xlsx')
        
        # Migrate Categories and Intents
        df_categories = pd.read_excel(xls, sheet_name='Categories')
        df_intents = pd.read_excel(xls, sheet_name='Intents')
        df_support_samples = pd.read_excel(xls, sheet_name='SupportSamples')
        
        # Create intents
        for _, row in df_intents.iterrows():
            intent = SupportIntent(
                intent_id=str(row['intent_id']),
                intent_name=str(row['intent']),
                description=str(row.get('description', '')),
                category=str(row.get('category', ''))
            )
            db.add(intent)
        
        # Create responses
        for _, row in df_support_samples.iterrows():
            response = SupportResponse(
                intent_id=str(row['intent_id']),
                response_text=str(row['response']),
                response_type=str(row.get('response_type', 'text'))
            )
            db.add(response)
        
        db.commit()
        print(f"Migrated support knowledge base with {len(df_intents)} intents and {len(df_support_samples)} responses")
    except Exception as e:
        print(f"Error migrating support knowledge base: {e}")
        db.rollback()
    finally:
        db.close()

def migrate_all():
    """Run all migrations"""
    print("Starting data migration...")
    migrate_knowledge_txt()
    migrate_customer_knowledge_base()
    migrate_support_knowledge_base()
    print("Data migration completed!")

if __name__ == "__main__":
    migrate_all()
