# Database-Backed RAG System with Customer Support Intents

## Overview
This is a comprehensive RAG (Retrieval-Augmented Generation) system designed for customer support in a telecom company. It features database-backed knowledge retrieval, customer order lookup, secure session management, and multi-tool support.

## Features

### ✅ Database-Backed RAG System
- **PostgreSQL Database**: Full PostgreSQL integration with proper schema
- **Knowledge Base**: Database-driven knowledge entries with search capabilities
- **Vector Embeddings**: Support for vector search and embeddings
- **ContextRetriever**: Enhanced RAG tool for knowledge base queries

### ✅ Customer Order Lookup
- **Database Integration**: Replaced Excel-based lookup with PostgreSQL queries
- **Multiple Search Methods**: Search by customer ID, email, or name
- **Real-time Data**: Live database queries for accurate customer information
- **Comprehensive Results**: Detailed order information with customer details

### ✅ Session Management
- **Secure Authentication**: JWT-like session tokens with proper hashing
- **Session Expiration**: Configurable session timeouts
- **User Registration**: Complete user management system
- **Password Security**: SHA-256 hashing (upgrade to bcrypt in production)

### ✅ Enhanced Multi-Tool System
- **ContextRetriever**: Database knowledge base search (primary tool)
- **SupportKnowledgeBase**: Customer support intent matching
- **ComprehensiveAnswerGenerator**: Multi-tool orchestrator for complex queries
- **BTWebsiteSearch**: BT.com specific information retrieval
- **BTSupportHours**: Current BT support hours and contact info
- **BTPlansInformation**: Current BT mobile plans and pricing
- **CustomerOrderLookup**: Customer and order information retrieval
- **Search Tool**: Web search capabilities for additional context
- **Wiki Tool**: Wikipedia integration for background information
- **Save Tool**: File saving functionality for research notes

## Architecture

### Database Schema
- **users**: User accounts with authentication
- **user_sessions**: Secure session management
- **customers**: Customer information
- **orders**: Customer order details
- **knowledge_entries**: Knowledge base content
- **support_intents**: Support intent definitions
- **support_responses**: Automated support responses
- **chat_history**: Conversation history

### API Endpoints

#### Authentication
- `POST /register` - User registration
- `POST /login` - User login with session creation
- `POST /logout` - Session termination
- `GET /me` - Current user information

#### RAG System
- `POST /chat` - Process customer queries with RAG
- `GET /health` - System health check

#### Static Files
- `GET /` - Login page
- `GET /chat.html` - Chat interface
- `GET /register.html` - Registration page

## Setup Instructions

### 1. Database Setup
```bash
# Install PostgreSQL (if not already installed)
# Create database: knowledge_base
# Update DATABASE_URL in .env file

# Run database migration
python migrate_postgres_schema.py
```

### 2. Environment Configuration
Create `.env` file:
```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/knowledge_base
GOOGLE_API_KEY=your_google_api_key_here
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize Database
```bash
python migrate_postgres_schema.py
```

### 5. Run the Application
```bash
python main.py
```

## Usage Examples

### Customer Order Lookup
```python
# Query examples:
"Show me orders for John Doe"
"What are my orders?" (when logged in)
"Customer 1001 order history"
```

### Support Queries
```python
# Query examples:
"What are your support hours?"
"How do I set up voicemail?"
"Tell me about data usage monitoring"
```

### Registration
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "username": "johndoe",
    "email": "john@example.com",
    "password": "securepassword",
    "full_name": "John Doe"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user123&password=securepassword"
```

## Enhanced Multi-Tool System

The Enhanced Multi-Tool System provides comprehensive customer support by combining multiple information sources and tools with intelligent context understanding and real-time web scraping.

### Key Features

- **🕷️ Real-time BT.com Web Scraping**: Automatically scrapes current information from BT.com when needed
- **🧠 Context Memory**: Maintains conversation history and uses it for personalized responses
- **🤖 Intelligent Tool Orchestration**: Automatically selects and combines the best tools for each query
- **📚 Enhanced RAG**: Context-aware knowledge retrieval with semantic matching
- **⚡ Performance Optimization**: Intelligent caching and tool selection for faster responses

### Available Tools

- **ContextRetriever**: Database knowledge base search (primary tool)
- **SupportKnowledgeBase**: Customer support intent matching
- **IntelligentToolOrchestrator**: Smart tool orchestrator with context memory
- **ComprehensiveAnswerGenerator**: Multi-tool orchestrator for complex queries
- **BTWebsiteSearch**: BT.com specific information with real-time scraping
- **BTSupportHours**: Current BT support hours with live data scraping
- **BTPlansInformation**: Current BT mobile plans with real-time pricing
- **Search Tool**: Web search capabilities for additional context
- **Wiki Tool**: Wikipedia integration for background information
- **Save Tool**: File saving functionality for research notes

### Quick Demo
```bash
python demo_multi_tool.py
```

### Enhanced System Testing
```bash
python test_enhanced_system.py
```

### Basic System Testing
```bash
python test_multi_tool_system.py
```

### Individual Tool Testing
```python
from tools import bt_website_search, multi_tool_orchestrator, intelligent_tool_orchestrator

# Test BT website search with scraping
result = bt_website_search("mobile plans")

# Test multi-tool orchestrator
result = multi_tool_orchestrator("How do I upgrade my plan?")

# Test intelligent orchestrator with context memory
result = intelligent_tool_orchestrator("What are your current support hours?")

# Test context memory
from tools import context_memory
context = context_memory.get_recent_context("support hours")
```

For detailed information, see [MULTI_TOOL_SYSTEM_GUIDE.md](MULTI_TOOL_SYSTEM_GUIDE.md)

## Testing

### Run Comprehensive Tests
```bash
python test_comprehensive.py
```

### Individual Component Tests
```bash
# Test database connection
python test_login_db.py

# Test customer database integration
python -c "from enhanced_customer_db_tool import get_customer_orders; print(get_customer_orders('John Doe', 'name'))"
```

## Security Features

- **Session Tokens**: Secure, hashed session tokens
- **HTTPS Ready**: Configured for HTTPS in production
- **Input Validation**: Comprehensive input sanitization
- **SQL Injection Protection**: Parameterized queries
- **CORS Configuration**: Configurable CORS settings

## Performance Optimizations

- **Database Indexes**: Optimized indexes for fast queries
- **Connection Pooling**: Efficient database connection management
- **Caching**: Prepared for Redis caching implementation
- **Query Optimization**: Efficient SQL queries

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running
   - Verify DATABASE_URL in .env
   - Ensure database exists

2. **Session Issues**
   - Check user_sessions table schema
   - Verify token hashing
   - Check session expiration

3. **Customer Lookup Not Working**
   - Ensure sample data is loaded
   - Check customer and order tables
   - Verify database connection

### Debug Mode
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Production Deployment

### Environment Variables
```bash
# Production settings
DATABASE_URL=postgresql://user:pass@prod-server:5432/knowledge_base
GOOGLE_API_KEY=your_production_key
SECRET_KEY=your_secret_key
```

### Security Enhancements
- Use bcrypt for password hashing
- Implement rate limiting
- Add HTTPS certificates
- Configure proper CORS origins
- Set up monitoring and logging

## API Documentation

### Chat Endpoint
```http
POST /chat
Content-Type: application/json
Cookie: session_token=your_session_token

{
  "query": "Your customer support question"
}
```

### Response Format
```json
{
  "topic": "Original query",
  "summary": "AI response",
  "sources": ["source1", "source2"],
  "tools_used": ["ContextRetriever", "CustomerOrderLookup"]
}
```

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Ensure all dependencies are installed
4. Verify database connectivity

## License
MIT License - See LICENSE file for details
