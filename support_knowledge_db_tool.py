from typing import Optional
import logging
from sqlalchemy.orm import Session
from database import SessionLocal
from db_utils import get_support_response, get_all_support_intents

def support_knowledge_tool_func(query: str) -> str:
    """
    Fetch support response from the customer support knowledge base based on the query.
    Matches query to intents and returns corresponding support sample responses.
    Uses database queries instead of Excel files.
    """
    try:
        db: Session = SessionLocal()
        
        # Search for matching support response
        response_text = get_support_response(db, query)
        
        if response_text:
            db.close()
            return response_text
        
        # If no exact match, try fuzzy matching
        intents = get_all_support_intents(db)
        
        q = query.lower()
        
        # Improved matching: check if any word in intent is in query or vice versa
        def intent_matches_query(intent_name: str, query: str) -> bool:
            intent_words = set(intent_name.lower().split())
            query_words = set(query.lower().split())
            return not intent_words.isdisjoint(query_words) or intent_name.lower() in query or query in intent_name.lower()
        
        for intent in intents:
            if intent_matches_query(intent.intent_name, q):
                response = get_support_response(db, intent.intent_name)
                if response:
                    db.close()
                    return response
        
        db.close()
        return "Sorry, I could not find any support information matching your query."
        
    except Exception as e:
        logging.error(f"Error accessing support knowledge base: {e}")
        return f"Error accessing support knowledge base: {str(e)}"

# Create the tool for LangChain
from langchain.tools import Tool

support_knowledge_tool = Tool.from_function(
    func=support_knowledge_tool_func,
    name="SupportKnowledgeBase",
    description="Use this tool to fetch customer support responses from the database knowledge base."
)
