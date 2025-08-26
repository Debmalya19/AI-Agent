from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.tools import Tool
from datetime import datetime
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

# Short-term memory for context understanding
class ContextMemory:
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.conversation_history = []
        self.context_cache = {}
        self.tool_usage_history = []
        
        # Initialize enhanced context retrieval engine lazily to avoid circular imports
        self.enhanced_engine = None
        self._enhanced_engine_initialized = False
    
    def add_conversation(self, user_query: str, response: str, tools_used: List[str]):
        """Add conversation to memory"""
        entry = {
            'timestamp': datetime.now(),
            'user_query': user_query,
            'response': response,
            'tools_used': tools_used
        }
        self.conversation_history.append(entry)
        
        # Keep only recent conversations
        if len(self.conversation_history) > self.max_size:
            self.conversation_history.pop(0)
        
        # Enhanced engine integration can be added later if needed
    
    def add_context(self, key: str, data: Any, ttl: int = 3600):
        """Add context data with TTL"""
        self.context_cache[key] = {
            'data': data,
            'timestamp': datetime.now(),
            'ttl': ttl
        }
        
        # Enhanced engine caching can be added later if needed
    
    def get_context(self, key: str) -> Optional[Any]:
        """Get context data if not expired"""
        if key in self.context_cache:
            entry = self.context_cache[key]
            if (datetime.now() - entry['timestamp']).seconds < entry['ttl']:
                return entry['data']
            else:
                del self.context_cache[key]
        return None
    
    def get_recent_context(self, query: str, limit: int = 3) -> List[Dict]:
        """Get recent relevant context based on query similarity"""
        # Use legacy implementation for now
        relevant_contexts = []
        query_lower = query.lower()
        
        for entry in reversed(self.conversation_history[-limit:]):
            if any(word in entry['user_query'].lower() for word in query_lower.split()):
                relevant_contexts.append(entry)
        
        return relevant_contexts
    
    def get_tool_usage_pattern(self, query_type: str) -> List[str]:
        """Get recommended tools based on query type and usage history"""
        # Use legacy implementation for now
        if query_type in ['support_hours', 'contact']:
            return ['BTSupportHours', 'BTWebsiteSearch']
        elif query_type in ['plans', 'pricing', 'upgrade']:
            return ['BTPlansInformation', 'BTWebsiteSearch', 'ContextRetriever']
        elif query_type in ['technical', 'troubleshooting']:
            return ['ContextRetriever', 'BTWebsiteSearch', 'Search Tool']
        else:
            return ['ContextRetriever', 'BTWebsiteSearch']

# Global context memory instance
context_memory = ContextMemory()

def scrape_bt_website(query: str, max_pages: int = 5) -> str:
    """
    Scrape BT.com website for comprehensive information.
    This tool provides detailed, up-to-date information directly from BT's official website.
    """
    try:
        # Check memory first
        cache_key = f"bt_scrape_{hashlib.md5(query.encode()).hexdigest()}"
        cached_result = context_memory.get_context(cache_key)
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
            # Cache the result
            context_memory.add_context(cache_key, combined_result, ttl=1800)  # 30 minutes
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
        cached_result = context_memory.get_context(cache_key)
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
            
            # Cache the result for 1 hour
            context_memory.add_context(cache_key, result, ttl=3600)
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
        cached_result = context_memory.get_context(cache_key)
        if cached_result:
            return cached_result
        
        # Scrape BT plans information
        plans_result = scrape_bt_website(f"mobile plans {query}")
        
        if "From BT.com:" in plans_result:
            # Cache the result for 2 hours
            context_memory.add_context(cache_key, plans_result, ttl=7200)
            return plans_result
        else:
            result = "For current BT mobile plans and pricing, please visit bt.com/mobile or contact our sales team."
            context_memory.add_context(cache_key, result, ttl=7200)
            return result
        
    except Exception as e:
        logging.error(f"BT plan information tool error: {e}")
        return "For current BT mobile plans and pricing, please visit bt.com/mobile or contact our sales team."

def intelligent_tool_orchestrator(query: str) -> str:
    """
    Intelligent tool orchestrator with context memory and smart tool selection.
    This tool combines multiple tools intelligently based on context and query analysis.
    """
    try:
        # Analyze query type and context
        query_type = analyze_query_type(query)
        relevant_context = context_memory.get_recent_context(query)
        recommended_tools = context_memory.get_tool_usage_pattern(query_type)
        
        comprehensive_answer = []
        tools_used = []
        context_used = []
        
        # Add context from recent conversations if relevant
        if relevant_context:
            context_used.append("Recent conversation context")
            for ctx in relevant_context:
                if any(word in query.lower() for word in ctx['user_query'].lower().split()):
                    comprehensive_answer.append(f"📝 **Related to your previous question:**")
                    comprehensive_answer.append(f"Previous: {ctx['user_query']}")
                    comprehensive_answer.append(f"Answer: {ctx['response'][:200]}...")
                    break
        
        # Step 1: Check database knowledge base first (always)
        try:
            from backend.enhanced_rag_orchestrator import search_with_priority
            rag_results = search_with_priority(query, max_results=2)
            if rag_results:
                comprehensive_answer.append("📚 **From our knowledge base:**")
                for result in rag_results[:2]:
                    comprehensive_answer.append(result['content'])
                tools_used.append("Knowledge Base")
        except Exception as e:
            logging.error(f"RAG search error in orchestrator: {e}")
        
        # Step 2: Use BT-specific tools based on query type
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
        
        # Step 3: Scrape BT.com for comprehensive information
        try:
            bt_scraped = scrape_bt_website(query)
            if "From BT.com:" in bt_scraped:
                comprehensive_answer.append(f"\n🌐 **Comprehensive BT.com Information:**")
                comprehensive_answer.append(bt_scraped)
                tools_used.append("BTWebsiteScraping")
        except Exception as e:
            logging.error(f"BT scraping error: {e}")
        
        # Step 4: Web search for additional context
        try:
            from langchain_community.tools import DuckDuckGoSearchRun
            search = DuckDuckGoSearchRun()
            web_results = search.run(f"BT {query} 2024")
            
            if web_results and len(web_results) > 100:
                comprehensive_answer.append(f"\n🔍 **Additional Web Information:**")
                web_content = clean_bt_content(web_results)
                comprehensive_answer.append(web_content)
                tools_used.append("Web Search")
        except Exception as e:
            logging.error(f"Web search error: {e}")
        
        # Step 5: Add context and recommendations
        if context_used:
            comprehensive_answer.append(f"\n💡 **Context Used:** {', '.join(context_used)}")
        
        # Combine all results
        if comprehensive_answer:
            final_answer = "\n\n".join(comprehensive_answer)
            final_answer += f"\n\n*This comprehensive answer was compiled using: {', '.join(tools_used)}*"
            
            # Store in memory for future context
            context_memory.add_conversation(query, final_answer, tools_used)
            
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

def multi_tool_orchestrator(query: str) -> str:
    """
    Enhanced multi-tool orchestrator with intelligent tool selection and context memory.
    This tool combines multiple tools automatically for comprehensive answers.
    """
    return intelligent_tool_orchestrator(query)

def create_ticket_tool(query: str, user_id: Optional[Union[int, str]] = None) -> str:
    """
    Create a support ticket for customer issues. Use this when a customer needs
    technical support, billing assistance, or any issue that requires human intervention.
    
    The input should be a description of the issue and customer user_id.
    """
    db = SessionLocal()
    try:
        service = TickingService(db)
        
        # Get customer information if user_id is provided
        customer_info = ""
        if user_id:
            try:
                # Try to get customer details from the User table
                from models import User
                user = db.query(User).filter(User.user_id == str(user_id)).first()
                if user:
                    customer_info = f"Customer ID: {user_id}\nCustomer Email: {user.email if hasattr(user, 'email') else 'N/A'}\n"
                    logging.info(f"Retrieved customer details for user {user_id}")
                else:
                    customer_info = f"Customer ID: {user_id}\n"
                    logging.info(f"Customer {user_id} not found in User table, using ID only")
            except Exception as e:
                logging.warning(f"Could not retrieve customer details for {user_id}: {e}")
                customer_info = f"Customer ID: {user_id}\n"
        
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
            "customer_id": user_id,
            "initial_query": query,
            "creation_timestamp": datetime.utcnow().isoformat(),
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
Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

This ticket was automatically created based on the customer's chat interaction with our AI support agent."""

        ticket = service.create_ticket(
            title=title,
            description=description,
            user_id=user_id,
            priority=priority,
            category=category,
            tags=tags,
            ticket_metadata=metadata
        )
        
        # Create a professional customer-focused response
        response = f"""🎫 Support Ticket Created Successfully!

Ticket ID: #{ticket.id}
Priority: {priority.value.title()}
Category: {category.value.replace('_', ' ').title()}
Status: {ticket.status.value.title()}

Thank you for contacting us! Your support request has been logged and assigned to our technical team. We will review your case and get back to you as soon as possible.

Please save your ticket number #{ticket.id} for future reference when contacting our support team."""
        
        # Store in memory for context
        context_memory.add_conversation(query, response, ["CreateSupportTicket"])
        
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

# Create enhanced tools
save_tool = Tool(
    name="save_text_to_file",
    func=save_to_txt,
    description="Saves structured research data to a text file.",
)

search = DuckDuckGoSearchRun()
search_tool = Tool(
    name="search",
    func=search.run,
    description="Search the web for information",
)

api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=100)
wiki_tool = Tool(
    name="wikipedia",
    func=WikipediaQueryRun(api_wrapper=api_wrapper).run,
    description="Search Wikipedia for general information and context",
)

# BT-specific tools with enhanced capabilities
bt_website_tool = Tool(
    name="BTWebsiteSearch",
    func=bt_website_search,
    description="Search and scrape BT.com website for official information about services, plans, and support. Use this for current BT-specific information.",
)

bt_support_hours_tool_instance = Tool(
    name="BTSupportHours",
    func=bt_support_hours_tool,
    description="Get current BT customer support hours and contact information from www.bt.com with real-time scraping",
)

bt_plans_tool = Tool(
    name="BTPlansInformation",
    func=bt_plan_information_tool,
    description="Get comprehensive information about BT mobile plans, pricing, and features from www.bt.com with scraping",
)

# Enhanced multi-tool orchestrator
multi_tool_tool = Tool(
    name="ComprehensiveAnswerGenerator",
    func=multi_tool_orchestrator,
    description="Generate comprehensive answers by intelligently combining multiple information sources including knowledge base, support database, BT.com scraping, and web search. Uses context memory for better understanding.",
)

# Intelligent tool orchestrator
intelligent_orchestrator_tool = Tool(
    name="IntelligentToolOrchestrator",
    func=intelligent_tool_orchestrator,
    description="Intelligent tool orchestrator with context memory, smart tool selection, and comprehensive information gathering. Provides the most relevant and up-to-date answers.",
)

# Create ticket tool
create_ticket_tool_instance = Tool.from_function(
    func=create_ticket_tool,
    name="CreateSupportTicket",
    description="Use this tool DIRECTLY (without any introduction) when a customer has a technical issue, needs support, or has any problem that requires human assistance. The tool will create a support ticket and return a professional response. DO NOT add any explanatory text before or after using this tool."
)

