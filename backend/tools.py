from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.tools import Tool, tool
from datetime import datetime, timezone
import logging
from typing import Optional, Dict, Any, List, Union
from backend.database import SessionLocal
from backend.models import Customer
from backend.ticking_service import TickingService, TicketPriority, TicketCategory
import requests
from bs4 import BeautifulSoup
import re
import json
import time
from urllib.parse import urljoin, urlparse
import hashlib

def optimize_memory_layer_performance():
    """
    Optimize memory layer performance for intelligent_chat.tool_orchestrator prioritization.
    """
    global context_memory
    if not context_memory:
        return False
    
    try:
        # Update memory configuration for better performance
        if hasattr(context_memory, 'config'):
            config = context_memory.config
            if hasattr(config, 'performance'):
                # Enable intelligent chat prioritization
                config.performance.prioritize_intelligent_chat = True
                config.performance.intelligent_chat_cache_size = 100
                config.performance.intelligent_chat_priority_weight = 0.9
                config.performance.context_retrieval_max_results = 5
                
                # Optimize cache settings
                config.performance.enable_caching = True
                config.performance.cache_ttl_seconds = 3600
                config.performance.enable_query_optimization = True
                
                logging.info("Memory layer performance optimized for intelligent_chat.tool_orchestrator")
                return True
    except Exception as e:
        logging.warning(f"Failed to optimize memory layer performance: {e}")
    
    return False

# Import memory manager for context handling
try:
    from backend.memory_layer_manager import MemoryLayerManager
    from backend.memory_config import load_config
    # Use shared memory manager instance (will be set from main.py)
    context_memory = None
    
    def set_shared_memory_manager(memory_manager):
        """Set the shared memory manager instance"""
        global context_memory
        context_memory = memory_manager
        # Optimize memory layer for intelligent_chat.tool_orchestrator prioritization
        optimize_memory_layer_performance()
    
except ImportError:
    # Fallback for when memory layer is not available
    context_memory = None
    
    def set_shared_memory_manager(memory_manager):
        pass

def get_prioritized_memory_context(query: str, max_results: int = 5) -> tuple:
    """
    Get prioritized context from memory layer with intelligent_chat.tool_orchestrator priority.
    Returns (intelligent_chat_contexts, general_contexts)
    """
    intelligent_chat_contexts = []
    general_contexts = []
    
    if not context_memory:
        return intelligent_chat_contexts, general_contexts
    
    try:
        # Priority 1: Look for intelligent_chat.tool_orchestrator specific responses
        intelligent_query = f"intelligent_chat tool_orchestrator {query}"
        intelligent_contexts = context_memory.retrieve_context(
            intelligent_query, 
            "system", 
            max_results // 2
        )
        
        if intelligent_contexts:
            intelligent_chat_contexts = [
                {
                    "user_query": ctx.content, 
                    "response": getattr(ctx, 'response', ''), 
                    "tools_used": ["intelligent_chat.tool_orchestrator"],
                    "priority": "high",
                    "source": "intelligent_chat_orchestrator"
                } 
                for ctx in intelligent_contexts
            ]
        
        # Priority 2: Get general context as fallback
        contexts = context_memory.retrieve_context(query, "system", max_results)
        if contexts:
            general_contexts = [
                {
                    "user_query": ctx.content, 
                    "response": getattr(ctx, 'response', ''), 
                    "tools_used": getattr(ctx, 'tools_used', []),
                    "priority": "medium",
                    "source": "memory_layer"
                } 
                for ctx in contexts
            ]
        
        logging.info(f"Retrieved {len(intelligent_chat_contexts)} intelligent_chat contexts and {len(general_contexts)} general contexts")
        
    except Exception as e:
        logging.warning(f"Memory layer context retrieval error: {e}")
    
    return intelligent_chat_contexts, general_contexts

def scrape_bt_website(query: str, max_pages: int = 5) -> str:
    """
    Scrape BT.com website for comprehensive information.
    This tool provides detailed, up-to-date information directly from BT's official website.
    """
    try:
        # Check memory first (if available)
        cache_key = f"bt_scrape_{hashlib.md5(query.encode()).hexdigest()}"
        cached_result = None
        if context_memory:
            # Use memory manager's context retrieval instead
            try:
                contexts = context_memory.retrieve_context(query, "system", 1)
                if contexts:
                    cached_result = contexts[0].content
            except Exception:
                cached_result = None
        
        if cached_result:
            return f"From BT.com (cached):\n\n{cached_result}"
        
        # Base URLs for different BT sections
        base_urls = [
            "https://www.bt.com",
            "https://www.bt.com/mobile",
            "https://www.bt.com/help",
            "https://www.bt.com/support",
            "https://www.bt.com/business"
        ]
        
        scraped_data = []
        visited_urls = set()
        
        for base_url in base_urls[:max_pages]:
            try:
                # Search for relevant content on each section
                search_query = f"site:{base_url} {query}"
                from langchain_community.tools import DuckDuckGoSearchRun
                search = DuckDuckGoSearchRun()
                search_results = search.run(search_query)
                
                if search_results and len(search_results) > 100:
                    # Extract and clean the content
                    cleaned_content = clean_bt_content(search_results)
                    if cleaned_content:
                        scraped_data.append(f"From {base_url}:\n{cleaned_content}")
                
                # Direct scraping of main pages
                try:
                    response = requests.get(base_url, timeout=10, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Extract relevant content
                        relevant_content = extract_relevant_content(soup, query)
                        if relevant_content:
                            scraped_data.append(f"From {base_url}:\n{relevant_content}")
                            
                except Exception as e:
                    logging.warning(f"Failed to scrape {base_url}: {e}")
                    continue
                    
            except Exception as e:
                logging.warning(f"Failed to search {base_url}: {e}")
                continue
        
        if scraped_data:
            combined_result = "\n\n".join(scraped_data[:3])  # Limit to top 3 results
            # Cache the result (MemoryLayerManager doesn't have add_context, skip caching for now)
            # TODO: Implement proper caching with MemoryLayerManager
            return f"From BT.com:\n\n{combined_result}"
        else:
            return "I couldn't find specific information about that on BT.com. Let me try a different approach."
            
    except Exception as e:
        logging.error(f"BT website scraping error: {e}")
        return "I encountered an error scraping BT.com. Let me try another approach to help you."

def clean_bt_content(content: str) -> str:
    """Clean and format scraped BT content"""
    if not content:
        return ""
    
    # Remove common web artifacts
    content = re.sub(r'DuckDuckGo|Search Results|\[.*?\]', '', content)
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content)
    
    # Extract meaningful sentences
    sentences = re.split(r'[.!?]+', content)
    meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 20 and 'BT' in s]
    
    if meaningful_sentences:
        return '. '.join(meaningful_sentences[:5]) + '.'
    
    return content[:500] + "..." if len(content) > 500 else content

def extract_relevant_content(soup: BeautifulSoup, query: str) -> str:
    """Extract relevant content from BT.com pages"""
    relevant_text = []
    query_words = query.lower().split()
    
    # Look for relevant headings and content
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'div']):
        if tag.get_text():
            text = tag.get_text().strip()
            if any(word in text.lower() for word in query_words) and len(text) > 20:
                relevant_text.append(text)
    
    if relevant_text:
        return ' '.join(relevant_text[:3])  # Return top 3 relevant pieces
    return ""

def bt_website_search(query: str) -> str:
    """
    Enhanced BT website search with scraping capabilities.
    This tool provides accurate, up-to-date information directly from BT's official website.
    """
    try:
        # Use scraping for comprehensive information
        scraped_result = scrape_bt_website(query)
        if "From BT.com:" in scraped_result:
            return scraped_result
        
        # Fallback to search if scraping fails
        search_query = f"site:bt.com {query}"
        from langchain_community.tools import DuckDuckGoSearchRun
        search = DuckDuckGoSearchRun()
        results = search.run(search_query)
        
        if not results:
            return "I couldn't find specific information about that on BT.com. Let me try a different approach."
        
        # Clean and format the results
        cleaned_results = clean_bt_content(results)
        
        # Add BT-specific context
        bt_context = f"From BT.com:\n\n{cleaned_results}"
        
        return bt_context
        
    except Exception as e:
        logging.error(f"BT website search error: {e}")
        return "I encountered an error searching BT.com. Let me try another approach to help you."

def bt_support_hours_tool(query: str) -> str:
    """
    Get current BT customer support hours and contact information with scraping.
    This tool provides real-time information about BT's support availability.
    """
    try:
        # Check memory first
        cache_key = "bt_support_hours"
        cached_result = None  # MemoryLayerManager doesn't have get_context method
        if cached_result:
            return cached_result
        
        # Scrape BT support pages for current information
        support_result = scrape_bt_website("customer support hours contact phone")
        
        if "From BT.com:" in support_result:
            # Extract support hours information
            if "24/7" in support_result.lower() or "24 hours" in support_result.lower():
                result = "Based on BT.com information, customer support is available 24/7 to assist you with any issues or inquiries."
            elif "business hours" in support_result.lower() or "9am" in support_result.lower() or "5pm" in support_result.lower():
                result = "Based on BT.com information, customer support is available during business hours. Please check the website for current hours."
            else:
                result = "Based on BT.com information, customer support is available. Please visit bt.com/help for current support hours and contact information."
            
            # Cache the result for 1 hour (skip caching for now)
            # TODO: Implement proper caching with MemoryLayerManager
            return result
        else:
            return "Our customer support is available to help you. Please contact us for current hours."
            
    except Exception as e:
        logging.error(f"BT support hours tool error: {e}")
        return "Our customer support is available to help you. Please contact us for current hours."

def bt_plan_information_tool(query: str) -> str:
    """
    Get comprehensive information about BT mobile plans, pricing, and features with scraping.
    This tool searches and scrapes BT.com for current plan information.
    """
    try:
        # Check memory first
        cache_key = f"bt_plans_{hashlib.md5(query.encode()).hexdigest()}"
        cached_result = None  # MemoryLayerManager doesn't have get_context method
        if cached_result:
            return cached_result
        
        # Scrape BT plans information
        plans_result = scrape_bt_website(f"mobile plans {query}")
        
        if "From BT.com:" in plans_result:
            # Cache the result for 2 hours (skip caching for now)
            # TODO: Implement proper caching with MemoryLayerManager
            return plans_result
        else:
            result = "For current BT mobile plans and pricing, please visit bt.com/mobile or contact our sales team."
            # Skip caching for now - TODO: Implement proper caching with MemoryLayerManager
            return result
        
    except Exception as e:
        logging.error(f"BT plan information tool error: {e}")
        return "For current BT mobile plans and pricing, please visit bt.com/mobile or contact our sales team."

def intelligent_tool_orchestrator(query: str) -> str:
    """
    Intelligent tool orchestrator with context memory and smart tool selection.
    This tool combines multiple tools intelligently based on context and query analysis.
    Prioritizes intelligent_chat.tool_orchestrator from memory layer for better performance.
    """
    try:
        # Analyze query type and context
        query_type = analyze_query_type(query)
        
        # PRIORITY 1: Get prioritized context from memory layer
        intelligent_chat_context, relevant_context = get_prioritized_memory_context(query, max_results=5)
        
        # Simple tool recommendation based on query type
        recommended_tools = []
        if query_type in ['support_hours', 'contact']:
            recommended_tools = ['IntelligentChatOrchestrator', 'BTSupportHours', 'BTWebsiteSearch']
        elif query_type in ['plans', 'pricing', 'upgrade']:
            recommended_tools = ['IntelligentChatOrchestrator', 'BTPlansInformation', 'BTWebsiteSearch', 'ContextRetriever']
        elif query_type in ['technical', 'troubleshooting']:
            recommended_tools = ['IntelligentChatOrchestrator', 'ContextRetriever', 'BTWebsiteSearch', 'Search Tool']
        else:
            recommended_tools = ['IntelligentChatOrchestrator', 'ContextRetriever', 'BTWebsiteSearch']
        
        comprehensive_answer = []
        tools_used = []
        context_used = []
        
        # PRIORITY 1: Add intelligent_chat.tool_orchestrator context first (highest priority)
        if intelligent_chat_context:
            context_used.append("Intelligent Chat Tool Orchestrator")
            for ctx in intelligent_chat_context:
                if any(word in query.lower() for word in ctx['user_query'].lower().split()):
                    comprehensive_answer.append(f"🤖 **From Intelligent Chat Tool Orchestrator (Priority Context):**")
                    comprehensive_answer.append(f"Previous Query: {ctx['user_query']}")
                    comprehensive_answer.append(f"Orchestrated Response: {ctx['response'][:300]}...")
                    tools_used.append("IntelligentChatOrchestrator")
                    break
        
        # PRIORITY 2: Add other memory layer context if no intelligent_chat context found
        if not intelligent_chat_context and relevant_context:
            context_used.append("Memory Layer Context")
            for ctx in relevant_context:
                if any(word in query.lower() for word in ctx['user_query'].lower().split()):
                    comprehensive_answer.append(f"📝 **From Memory Layer Context:**")
                    comprehensive_answer.append(f"Previous: {ctx['user_query']}")
                    comprehensive_answer.append(f"Answer: {ctx['response'][:200]}...")
                    tools_used.append("MemoryLayerContext")
                    break
        
        # PRIORITY 3: Check database knowledge base (enhanced RAG)
        try:
            from backend.enhanced_rag_orchestrator import search_with_priority
            rag_results = search_with_priority(query, max_results=2)
            if rag_results:
                comprehensive_answer.append("📚 **From Enhanced Knowledge Base:**")
                for result in rag_results[:2]:
                    comprehensive_answer.append(result['content'])
                tools_used.append("EnhancedRAG")
        except Exception as e:
            logging.error(f"Enhanced RAG search error in orchestrator: {e}")
        
        # PRIORITY 4: Use BT-specific tools based on query type
        if query_type in ['support_hours', 'contact']:
            try:
                bt_result = bt_support_hours_tool(query)
                if "Based on BT.com information" in bt_result:
                    comprehensive_answer.append(f"\n🕒 **Current BT Support Information:**")
                    comprehensive_answer.append(bt_result)
                    tools_used.append("BTSupportHours")
            except Exception as e:
                logging.error(f"BT support hours error: {e}")
        
        elif query_type in ['plans', 'pricing', 'upgrade']:
            try:
                bt_result = bt_plan_information_tool(query)
                if "From BT.com:" in bt_result:
                    comprehensive_answer.append(f"\n📱 **Current BT Plans Information:**")
                    comprehensive_answer.append(bt_result)
                    tools_used.append("BTPlansInformation")
            except Exception as e:
                logging.error(f"BT plans error: {e}")
        
        # PRIORITY 5: Scrape BT.com for comprehensive information (only if no high-priority context found)
        if not intelligent_chat_context:
            try:
                bt_scraped = scrape_bt_website(query)
                if "From BT.com:" in bt_scraped:
                    comprehensive_answer.append(f"\n🌐 **Comprehensive BT.com Information:**")
                    comprehensive_answer.append(bt_scraped)
                    tools_used.append("BTWebsiteScraping")
            except Exception as e:
                logging.error(f"BT scraping error: {e}")
        
        # PRIORITY 6: Web search for additional context (lowest priority)
        if len(comprehensive_answer) < 2:  # Only if we don't have enough information
            try:
                from langchain_community.tools import DuckDuckGoSearchRun
                search = DuckDuckGoSearchRun()
                web_results = search.run(f"BT {query} 2024")
                
                if web_results and len(web_results) > 100:
                    comprehensive_answer.append(f"\n🔍 **Additional Web Information:**")
                    web_content = clean_bt_content(web_results)
                    comprehensive_answer.append(web_content)
                    tools_used.append("WebSearch")
            except Exception as e:
                logging.error(f"Web search error: {e}")
        
        # Add context and recommendations
        if context_used:
            comprehensive_answer.append(f"\n💡 **Context Sources (Priority Order):** {', '.join(context_used)}")
        
        # Combine all results with priority indication
        if comprehensive_answer:
            final_answer = "\n\n".join(comprehensive_answer)
            final_answer += f"\n\n*This response prioritized intelligent_chat.tool_orchestrator from memory layer. Tools used: {', '.join(tools_used)}*"
            
            # Store in memory for future context using MemoryLayerManager with enhanced metadata
            if context_memory:
                try:
                    from backend.memory_models import ConversationEntryDTO
                    conversation = ConversationEntryDTO(
                        session_id="intelligent_tool_session",
                        user_id="system",
                        user_message=query,
                        bot_response=final_answer,
                        tools_used=tools_used,
                        tool_performance={
                            "intelligent_chat_priority": len(intelligent_chat_context) > 0,
                            "memory_layer_used": len(context_used) > 0,
                            "tools_count": len(tools_used)
                        },
                        context_used=context_used,
                        response_quality_score=0.9 if intelligent_chat_context else 0.8
                    )
                    context_memory.store_conversation(conversation)
                except Exception as e:
                    logging.warning(f"Failed to store conversation in memory: {e}")
            
            return final_answer
        else:
            return "I couldn't find comprehensive information about that. Please contact our support team for assistance."
            
    except Exception as e:
        logging.error(f"Intelligent tool orchestrator error: {e}")
        return "I encountered an error while gathering information. Let me try a simpler approach to help you."

def analyze_query_type(query: str) -> str:
    """Analyze query type for intelligent tool selection"""
    query_lower = query.lower()
    
    if any(word in query_lower for word in ['support hours', 'contact', 'phone', 'email', 'help']):
        return 'support_hours'
    elif any(word in query_lower for word in ['plan', 'pricing', 'cost', 'upgrade', 'change', 'unlimited', 'data']):
        return 'plans'
    elif any(word in query_lower for word in ['technical', 'troubleshooting', 'error', 'problem', 'fix', 'issue']):
        return 'technical'
    elif any(word in query_lower for word in ['order', 'billing', 'payment', 'invoice']):
        return 'billing'
    else:
        return 'general'

# Removed duplicate multi_tool_orchestrator - use intelligent_tool_orchestrator directly

def create_ticket_tool(query: str, user_id: Optional[Union[int, str]] = None) -> str:
    """
    Create a support ticket for customer issues. Use this when a customer needs
    technical support, billing assistance, or any issue that requires human intervention.
    
    The input should be a description of the issue and customer user_id.
    """
    db = SessionLocal()
    try:
        service = TickingService(db)
        
        # Get customer information if user_id is provided and convert to proper type
        customer_info = ""
        processed_user_id = None
        
        if user_id:
            # Try to convert user_id to integer if it's numeric
            try:
                if isinstance(user_id, str) and user_id.isdigit():
                    processed_user_id = int(user_id)
                elif isinstance(user_id, int):
                    processed_user_id = user_id
                else:
                    # For non-numeric user_ids, we'll store as None and include in metadata
                    processed_user_id = None
                    customer_info = f"Customer Reference: {user_id}\n"
                    logging.info(f"Non-numeric user_id {user_id}, storing as reference only")
            except (ValueError, TypeError):
                processed_user_id = None
                customer_info = f"Customer Reference: {user_id}\n"
                logging.warning(f"Could not convert user_id {user_id} to integer, storing as reference")
            
            # Try to get customer details from the User table if we have a numeric ID
            if processed_user_id:
                try:
                    from backend.models import User
                    user = db.query(User).filter(User.user_id == processed_user_id).first()
                    if user:
                        customer_info = f"Customer ID: {processed_user_id}\nCustomer Email: {user.email if hasattr(user, 'email') else 'N/A'}\n"
                        logging.info(f"Retrieved customer details for user {processed_user_id}")
                    else:
                        customer_info = f"Customer ID: {processed_user_id}\n"
                        logging.info(f"Customer {processed_user_id} not found in User table, using ID only")
                except Exception as e:
                    logging.warning(f"Could not retrieve customer details for {processed_user_id}: {e}")
                    customer_info = f"Customer ID: {processed_user_id}\n"
        
        # Determine ticket category based on query content
        category = TicketCategory.GENERAL
        if any(word in query.lower() for word in ['error', 'bug', 'crash', 'not working', 'broken', 'failed']):
            category = TicketCategory.BUG_REPORT
        elif any(word in query.lower() for word in ['bill', 'payment', 'charge', 'refund', 'cost', 'invoice', 'billing']):
            category = TicketCategory.BILLING
        elif any(word in query.lower() for word in ['feature', 'suggestion', 'improve', 'add', 'enhancement']):
            category = TicketCategory.FEATURE_REQUEST
        elif any(word in query.lower() for word in ['technical', 'setup', 'configure', 'install', 'connection', 'network']):
            category = TicketCategory.TECHNICAL
            
        # Determine priority based on urgency keywords
        priority = TicketPriority.MEDIUM
        if any(word in query.lower() for word in ['urgent', 'emergency', 'critical', 'serious', 'asap']):
            priority = TicketPriority.HIGH
        elif any(word in query.lower() for word in ['blocked', 'cannot access', 'down', 'outage', 'completely broken']):
            priority = TicketPriority.CRITICAL
        elif any(word in query.lower() for word in ['minor', 'small', 'low priority', 'when possible']):
            priority = TicketPriority.LOW
            
        # Create a descriptive title for customer support
        title = f"Customer Support Request: {query[:50]}..." if len(query) > 50 else f"Customer Support Request: {query}"
        
        # Prepare comprehensive metadata for customer service
        metadata = {
            "source": "ai_agent_chat",
            "customer_id": user_id,  # Keep original user_id in metadata for reference
            "processed_customer_id": processed_user_id,  # Store the processed integer ID
            "initial_query": query,
            "creation_timestamp": datetime.now(timezone.utc).isoformat(),
            "channel": "web_chat",
            "agent_assisted": True
        }
        
        # Prepare relevant tags for customer support
        tags = ["customer-support", "ai-agent", category.value, priority.value, "web-chat"]
        
        # Create comprehensive ticket description for customer support
        description = f"""CUSTOMER SUPPORT TICKET

{customer_info}
Issue Description:
{query}

Category: {category.value.replace('_', ' ').title()}
Priority: {priority.value.title()}
Submitted via: AI Chat Agent
Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

This ticket was automatically created based on the customer's chat interaction with our AI support agent."""

        # Try to create ticket with customer_id, fallback to None if customer doesn't exist
        try:
            ticket = service.create_ticket(
                title=title,
                description=description,
                user_id=processed_user_id,  # Use the processed integer user_id or None
                priority=priority,
                category=category,
                tags=tags,
                ticket_metadata=metadata
            )
        except Exception as db_error:
            # If foreign key constraint fails, create ticket without customer_id
            if "foreign key constraint" in str(db_error).lower() or "violates foreign key" in str(db_error).lower():
                logging.warning(f"Customer ID {processed_user_id} not found in database, creating ticket without customer reference")
                
                # Rollback the failed transaction
                try:
                    db.rollback()
                except Exception:
                    pass
                
                # Update metadata to reflect this
                metadata["customer_lookup_failed"] = True
                metadata["original_customer_error"] = "Customer ID not found in database"
                
                # Update description to include customer reference info
                description += f"\n\nNote: Original customer reference '{user_id}' could not be linked to existing customer record."
                
                ticket = service.create_ticket(
                    title=title,
                    description=description,
                    user_id=None,  # Create without customer_id
                    priority=priority,
                    category=category,
                    tags=tags,
                    ticket_metadata=metadata
                )
            else:
                # Re-raise other database errors
                raise db_error
        
        # Create a professional customer-focused response
        response = f"""🎫 Support Ticket Created Successfully!

Ticket ID: #{ticket.id}
Priority: {priority.value.title()}
Category: {category.value.replace('_', ' ').title()}
Status: {ticket.status.value.title()}

Thank you for contacting us! Your support request has been logged and assigned to our technical team. We will review your case and get back to you as soon as possible.

Please save your ticket number #{ticket.id} for future reference when contacting our support team."""
        
        # Store in memory for context using MemoryLayerManager
        if context_memory:
            try:
                from backend.memory_models import ConversationEntryDTO
                conversation = ConversationEntryDTO(
                    session_id="ticket_session",
                    user_id=str(processed_user_id) if processed_user_id else (str(user_id) if user_id else "anonymous"),
                    user_message=query,
                    bot_response=response,
                    tools_used=["CreateSupportTicket"],
                    tool_performance={
                        "user_id_processed": processed_user_id is not None,
                        "original_user_id": str(user_id) if user_id else None
                    },
                    context_used=[],
                    response_quality_score=0.9
                )
                context_memory.store_conversation(conversation)
            except Exception as e:
                logging.warning(f"Failed to store ticket conversation in memory: {e}")
        
        return response
        
    except Exception as e:
        logging.error(f"Error creating ticket: {e}")
        return f"❌ Sorry, I encountered an error creating your ticket. Please contact human support directly. Error: {str(e)}"
    finally:
        db.close()

def save_to_txt(data: str, filename: str = "research_output.txt"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_text = f"--- Research Output ---\nTimestamp: {timestamp}\n\n{data}\n\n"

    with open(filename, "a", encoding="utf-8") as f:
        f.write(formatted_text)
    
    return f"Data successfully saved to {filename}"

# Create enhanced tools using modern @tool decorator
@tool
def save_text_to_file(data: str, filename: str = "research_output.txt") -> str:
    """Saves structured research data to a text file."""
    return save_to_txt(data, filename)

save_tool = save_text_to_file

@tool
def search(query: str) -> str:
    """Search the web for information"""
    search_engine = DuckDuckGoSearchRun()
    return search_engine.run(query)

search_tool = search

@tool
def wikipedia(query: str) -> str:
    """Search Wikipedia for general information and context"""
    api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=100)
    wiki_search = WikipediaQueryRun(api_wrapper=api_wrapper)
    return wiki_search.run(query)

wiki_tool = wikipedia

# BT-specific tools with enhanced capabilities
@tool
def BTWebsiteSearch(query: str) -> str:
    """Search and scrape BT.com website for official information about services, plans, and support. Use this for current BT-specific information."""
    return bt_website_search(query)

bt_website_tool = BTWebsiteSearch

@tool
def BTSupportHours(query: str) -> str:
    """Get current BT customer support hours and contact information from www.bt.com with real-time scraping"""
    return bt_support_hours_tool(query)

bt_support_hours_tool_instance = BTSupportHours

@tool
def BTPlansInformation(query: str) -> str:
    """Get comprehensive information about BT mobile plans, pricing, and features from www.bt.com with scraping"""
    return bt_plan_information_tool(query)

bt_plans_tool = BTPlansInformation

# Removed duplicate multi_tool_tool - functionality merged into intelligent_orchestrator_tool

# Intelligent tool orchestrator
@tool
def IntelligentToolOrchestrator(query: str) -> str:
    """Intelligent tool orchestrator with context memory, smart tool selection, and comprehensive information gathering. Provides the most relevant and up-to-date answers."""
    return intelligent_tool_orchestrator(query)

intelligent_orchestrator_tool = IntelligentToolOrchestrator

# Create ticket tool
@tool
def CreateSupportTicket(query: str, user_id: Optional[Union[int, str]] = None) -> str:
    """Use this tool DIRECTLY (without any introduction) when a customer has a technical issue, needs support, or has any problem that requires human assistance. The tool will create a support ticket and return a professional response. DO NOT add any explanatory text before or after using this tool."""
    return create_ticket_tool(query, user_id)

create_ticket_tool_instance = CreateSupportTicket

# RAG search functions
def rag_search(query: str) -> str:
    """Search the knowledge base for relevant information about BT services, troubleshooting, and customer support"""
    try:
        # Use the enhanced RAG orchestrator if available
        from backend.enhanced_rag_orchestrator import search_with_priority
        results = search_with_priority(query, max_results=3)
        if results:
            formatted_results = []
            for result in results:
                formatted_results.append(f"📚 {result['content']}")
            return "\n\n".join(formatted_results)
        else:
            return "No relevant information found in the knowledge base."
    except ImportError:
        # Fallback if enhanced RAG is not available
        return "Knowledge base search is currently unavailable. Please contact support for assistance."
    except Exception as e:
        logging.error(f"RAG search error: {e}")
        return "Error searching knowledge base. Please try again or contact support."

def support_knowledge_search(query: str) -> str:
    """Search the support knowledge base for customer service responses and troubleshooting guides"""
    try:
        # Use the enhanced RAG orchestrator with support-specific context
        from backend.enhanced_rag_orchestrator import search_with_priority
        support_query = f"customer support {query}"
        results = search_with_priority(support_query, max_results=2)
        if results:
            formatted_results = []
            for result in results:
                formatted_results.append(f"🎧 Support: {result['content']}")
            return "\n\n".join(formatted_results)
        else:
            return "No relevant support information found. Please contact our support team directly."
    except ImportError:
        # Fallback if enhanced RAG is not available
        return "Support knowledge base is currently unavailable. Please contact our support team."
    except Exception as e:
        logging.error(f"Support knowledge search error: {e}")
        return "Error searching support knowledge base. Please contact our support team."

# RAG tool for knowledge base search
@tool
def ContextRetriever(query: str) -> str:
    """Search the knowledge base for relevant information about BT services, troubleshooting, and customer support"""
    return rag_search(query)

rag_tool = ContextRetriever

# Support knowledge tool
@tool
def SupportKnowledgeBase(query: str) -> str:
    """Search the support knowledge base for customer service responses and troubleshooting guides"""
    return support_knowledge_search(query)

support_knowledge_tool = SupportKnowledgeBase

