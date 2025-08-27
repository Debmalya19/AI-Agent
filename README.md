# AI Agent Customer Support System

**© 2025 Debmalya Koner. All rights reserved.**

## Overview
A comprehensive AI-powered customer support system built with FastAPI, featuring intelligent chat capabilities, memory layer management, multi-tool orchestration, and database-backed knowledge retrieval. The system provides contextual, personalized responses using advanced RAG (Retrieval-Augmented Generation) technology and intelligent tool selection.

## 🚀 Key Features

### 🧠 Intelligent Chat UI
- **Dynamic Response Adaptation**: UI adapts based on conversation context and response type
- **Real-time Tool Orchestration**: Automatic selection and execution of relevant tools
- **Context-Aware Conversations**: Maintains conversation history for natural follow-up interactions
- **Visual Feedback System**: Loading indicators and progress tracking during tool execution
- **Error Recovery**: Graceful error handling with user-friendly messages

### 💾 Advanced Memory Layer
- **Persistent Conversation Storage**: Chat history maintained across sessions
- **Context Retrieval Engine**: Intelligent context extraction from conversation history
- **Tool Usage Analytics**: Learning from previous tool usage patterns
- **Memory Configuration**: Configurable retention policies and cleanup strategies
- **Performance Optimization**: Efficient memory management with caching

### 🛠️ Multi-Tool Orchestration System
- **Intelligent Tool Selection**: Algorithm-based tool selection for optimal responses
- **Parallel Tool Execution**: Concurrent tool execution for faster responses
- **Tool Performance Monitoring**: Analytics and optimization of tool usage
- **Context-Aware Tool Recommendations**: Historical data influences tool selection
- **Comprehensive Answer Generation**: Multi-source information synthesis

### 🔐 Security & Privacy
- **Secure Session Management**: Hashed session tokens with configurable expiration
- **User Authentication**: Complete registration and login system
- **GDPR Compliance**: Privacy-focused data handling and retention policies
- **Security Integration**: Comprehensive security monitoring and threat detection
- **Data Encryption**: Sensitive information protection

### 📊 Database Integration
- **PostgreSQL Backend**: Full PostgreSQL integration with optimized schema
- **Knowledge Base Management**: Searchable knowledge entries with RAG capabilities
- **Customer Data Management**: Comprehensive customer and order tracking
- **Support Ticket System**: Automated ticket creation and management
- **Analytics Storage**: Tool usage and performance metrics

## 🏗️ System Architecture

### Core Components

#### Backend Architecture
```
backend/
├── intelligent_chat/          # Intelligent chat UI components
│   ├── chat_manager.py        # Central chat coordinator
│   ├── tool_orchestrator.py   # Tool selection and execution
│   ├── context_retriever.py   # Context retrieval engine
│   ├── response_renderer.py   # Dynamic response formatting
│   └── models.py             # Data models and types
├── memory_layer_manager.py    # Memory management system
├── tools.py                   # Multi-tool system implementation
├── models.py                  # Database models
├── database.py               # Database configuration
└── security_manager.py       # Security and privacy management
```

#### Database Schema
- **Enhanced Chat History**: Conversation storage with context
- **Memory Context Cache**: Intelligent context caching
- **Tool Usage Metrics**: Performance analytics and optimization
- **Conversation Summaries**: Automated conversation summarization
- **Memory Health Metrics**: System performance monitoring
- **Users & Sessions**: Secure authentication system
- **Knowledge Entries**: RAG knowledge base
- **Support System**: Ticket management and responses

### API Endpoints

#### Core Chat API
- `POST /chat` - Intelligent chat processing with multi-tool orchestration
- `GET /memory/stats` - Memory layer statistics and health metrics
- `POST /memory/cleanup` - Manual memory cleanup operations

#### Authentication & Session Management
- `POST /register` - User registration with security validation
- `POST /login` - Secure login with session token generation
- `POST /logout` - Session termination and cleanup
- `GET /me` - Current user profile and session information

#### System Management
- `GET /health` - Comprehensive system health check
- `GET /tools/status` - Tool availability and performance metrics
- `POST /tools/analytics` - Tool usage analytics and recommendations

#### Frontend Routes
- `GET /` - Login interface
- `GET /chat.html` - Intelligent chat interface
- `GET /register.html` - User registration interface

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Google Gemini API Key

### 1. Environment Setup
```bash
# Clone the repository
git clone <repository-url>
cd ai-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Configuration
```bash
# Install PostgreSQL and create database
createdb knowledge_base

# Update .env file
DATABASE_URL=postgresql://postgres:password@localhost:5432/knowledge_base
GOOGLE_API_KEY=your_google_gemini_api_key_here
DEBUG=True
HOST=0.0.0.0
PORT=8000
```

### 3. Database Initialization
```bash
# Run database migrations
python scripts/migrate_postgres_schema.py

# Initialize with sample data (optional)
python scripts/database_init.py

# Verify memory layer setup
python scripts/verify_memory_schema.py
```

### 4. Launch Application
```bash
# Start the FastAPI server
python main.py

# Or use uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access the System
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 💡 Usage Examples

### Intelligent Chat Interactions
```python
# Complex multi-tool queries
"What are the current BT mobile plans and how do I upgrade my existing plan?"

# Context-aware follow-ups
"What about the pricing for unlimited data?"
"Can you create a support ticket for my billing issue?"

# Customer service queries
"What are your support hours and how can I contact customer service?"
"I'm having trouble with my voicemail setup"
```

### API Usage Examples

#### Chat with Context
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=your_session_token" \
  -d '{
    "query": "What are the current mobile plans available?"
  }'
```

#### User Registration
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

#### Memory Statistics
```bash
curl -X GET http://localhost:8000/memory/stats \
  -H "Cookie: session_token=your_session_token"
```

### Python SDK Usage
```python
from backend.intelligent_chat import ChatManager
from backend.memory_layer_manager import MemoryLayerManager

# Initialize components
memory_manager = MemoryLayerManager()
chat_manager = ChatManager(memory_manager=memory_manager)

# Process message with context
response = await chat_manager.process_message(
    message="What are your support hours?",
    user_id="user123",
    session_id="session456"
)

print(f"Response: {response.content}")
print(f"Tools used: {response.tools_used}")
print(f"Confidence: {response.confidence_score}")
```

## 🛠️ Available Tools & Capabilities

### Intelligent Tool Orchestration
The system features 9+ specialized tools that work together to provide comprehensive responses:

| Tool                            | Purpose                        | Use Case                                   |
|---------------------------------|--------------------------------|--------------------------------------------|
| **ContextRetriever**            | Database knowledge base search | Primary information source                 |
| **SupportKnowledgeBase**        | Customer support responses     | Common support queries                     |
| **IntelligentToolOrchestrator** | Smart multi-tool coordination  | Complex queries requiring multiple sources |
| **CreateSupportTicket**         | Automated ticket creation      | Customer issues and escalations            |
| **BTWebsiteSearch**             | Real-time BT.com scraping      | Current BT services and information        |
| **BTSupportHours**              | Live support hours data        | Contact information and availability       |
| **BTPlansInformation**          | Current plan pricing           | Mobile plans and pricing details           |
| **Search Tool**                 | Web search capabilities        | Additional context and information         |
| **Wiki Tool**                   | Wikipedia integration          | Background and educational content         |

### Memory Layer Features
- **Conversation Persistence**: Chat history maintained across sessions
- **Context-Aware Responses**: Previous conversations inform current responses
- **Tool Usage Learning**: System learns from successful tool combinations
- **Performance Analytics**: Continuous optimization based on usage patterns
- **Configurable Retention**: Customizable data retention policies

### Intelligent Chat UI Features
- **Dynamic Response Rendering**: Adapts UI based on response content type
- **Real-time Tool Execution Feedback**: Visual indicators during tool processing
- **Error Recovery**: Graceful handling of tool failures with fallback strategies
- **Context Window Management**: Efficient handling of long conversations
- **Multi-format Support**: Text, code, JSON, tables, and structured data

### Testing & Demos
```bash
# Run comprehensive system tests
python tests/test_comprehensive.py

# Demo intelligent chat capabilities
python examples/demo_multi_tool.py

# Test memory layer functionality
python examples/example_memory_usage.py

# Performance optimization demo
python examples/performance_optimization_demo.py
```

For detailed documentation:
- [Multi-Tool System Guide](docs/MULTI_TOOL_SYSTEM_GUIDE.md)
- [Intelligent Chat API Documentation](docs/INTELLIGENT_CHAT_API_DOCUMENTATION.md)
- [Memory Layer Configuration](docs/MEMORY_CONFIG_GUIDE.md)

## 🧪 Testing & Validation

### Comprehensive Test Suite
```bash
# Run all system tests
python tests/test_comprehensive.py

# Test intelligent chat components
python tests/test_intelligent_chat.py

# Test memory layer functionality
python tests/test_memory_layer.py

# Test security and privacy features
python tests/test_security.py
```

### Component-Specific Testing
```bash
# Database connectivity
python scripts/database_init.py

# Memory layer validation
python scripts/verify_memory_schema.py

# Tool orchestration testing
python examples/demo_multi_tool.py

# Performance benchmarking
python examples/performance_optimization_demo.py
```

### Integration Testing
```bash
# End-to-end chat flow
python tests/test_chat_integration.py

# Multi-tool orchestration
python tests/test_tool_orchestration.py

# Context retrieval and memory
python tests/test_context_memory.py
```

## 🔒 Security & Privacy

### Security Features
- **Secure Session Management**: Hashed session tokens with configurable expiration
- **Input Validation & Sanitization**: Comprehensive protection against injection attacks
- **GDPR Compliance**: Privacy-focused data handling with retention policies
- **Security Monitoring**: Real-time threat detection and logging
- **Data Encryption**: Sensitive information protection at rest and in transit

### Privacy Protection
- **Data Anonymization**: PII protection in logs and analytics
- **Configurable Retention**: Automatic data cleanup based on policies
- **User Consent Management**: Granular privacy controls
- **Audit Logging**: Comprehensive activity tracking for compliance

## ⚡ Performance & Optimization

### Performance Features
- **Intelligent Caching**: Multi-layer caching for faster responses
- **Parallel Tool Execution**: Concurrent processing for complex queries
- **Database Optimization**: Indexed queries and connection pooling
- **Memory Management**: Efficient context window and cleanup strategies
- **Response Streaming**: Real-time response delivery for better UX

### Monitoring & Analytics
- **Tool Performance Metrics**: Usage analytics and optimization recommendations
- **Memory Health Monitoring**: System performance tracking and alerts
- **Response Time Analytics**: Continuous performance optimization
- **Resource Usage Tracking**: CPU, memory, and database performance monitoring

## 🔧 Troubleshooting

### Common Issues & Solutions

#### Database Issues
```bash
# Check PostgreSQL connection
python -c "from backend.database import engine; print(engine.execute('SELECT 1').scalar())"

# Verify schema
python scripts/verify_memory_schema.py

# Reset database (if needed)
python scripts/migrate_postgres_schema.py
```

#### Memory Layer Issues
```bash
# Check memory layer health
python -c "from backend.memory_layer_manager import MemoryLayerManager; print(MemoryLayerManager().get_memory_stats())"

# Manual cleanup
python scripts/run_memory_migration.py
```

#### Tool Orchestration Issues
```bash
# Test individual tools
python examples/demo_multi_tool.py

# Check tool availability
python -c "from backend.tools import tools; print([tool.name for tool in tools])"
```

#### Session & Authentication Issues
```bash
# Verify user sessions table
python scripts/fix_user_sessions_schema.py

# Test authentication flow
python tests/test_login_db.py
```

### Debug Configuration
```python
# Enable comprehensive logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable memory layer debugging
from backend.memory_config import load_config
config = load_config()
config.debug_mode = True
```

### Health Monitoring
```bash
# System health check
curl http://localhost:8000/health

# Memory statistics
curl http://localhost:8000/memory/stats

# Tool status
curl http://localhost:8000/tools/status
```

## 🚀 Production Deployment

### Environment Configuration
```bash
# Production environment variables
DATABASE_URL=postgresql://user:pass@prod-server:5432/knowledge_base
GOOGLE_API_KEY=your_production_gemini_key
DEBUG=False
HOST=0.0.0.0
PORT=8000

# Security settings
SECRET_KEY=your_secure_secret_key
SESSION_TIMEOUT=3600
CORS_ORIGINS=["https://yourdomain.com"]

# Memory layer configuration
MEMORY_RETENTION_DAYS=30
MEMORY_CLEANUP_INTERVAL_HOURS=24
MEMORY_MAX_CONVERSATIONS=10000
```

### Production Checklist
- [ ] Configure HTTPS with SSL certificates
- [ ] Set up database connection pooling
- [ ] Implement rate limiting and request throttling
- [ ] Configure monitoring and alerting
- [ ] Set up log aggregation and analysis
- [ ] Enable security headers and CORS policies
- [ ] Configure backup and disaster recovery
- [ ] Set up health checks and load balancing

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📚 API Documentation

### Enhanced Chat API
```http
POST /chat
Content-Type: application/json
Cookie: session_token=your_session_token

{
  "query": "What are the current mobile plans and pricing?"
}
```

#### Enhanced Response Format
```json
{
  "topic": "Mobile plans inquiry",
  "summary": "Comprehensive response with current plans...",
  "sources": ["knowledge_base", "bt_website", "support_db"],
  "tools_used": ["ContextRetriever", "BTPlansInformation", "SupportKnowledgeBase"],
  "confidence_score": 0.95,
  "execution_time": 2.3,
  "content_type": "structured_data",
  "ui_state": {
    "loading_indicators": [],
    "error_states": []
  }
}
```

### Memory Management API
```http
GET /memory/stats
Cookie: session_token=your_session_token

# Response
{
  "total_conversations": 1250,
  "active_sessions": 45,
  "memory_usage_mb": 128.5,
  "cleanup_last_run": "2024-01-15T10:30:00Z"
}
```

For complete API documentation, visit: http://localhost:8000/docs

## 📖 Documentation

### Core Documentation
- [Multi-Tool System Guide](docs/MULTI_TOOL_SYSTEM_GUIDE.md) - Comprehensive tool usage guide
- [Intelligent Chat API](docs/INTELLIGENT_CHAT_API_DOCUMENTATION.md) - Chat system documentation
- [Memory Layer Guide](docs/MEMORY_CONFIG_GUIDE.md) - Memory management configuration
- [Security & Privacy Guide](docs/SECURITY_PRIVACY_GUIDE.md) - Security implementation details
- [Database Setup Guide](docs/DATABASE_SETUP_GUIDE.md) - Database configuration and setup

### Implementation Guides
- [Context Retriever Implementation](docs/CONTEXT_RETRIEVER_IMPLEMENTATION.md)
- [Visual Feedback System](docs/VISUAL_FEEDBACK_SYSTEM.md)
- [Performance Optimization](docs/PERFORMANCE_OPTIMIZATION_SUMMARY.md)
- [Comprehensive Testing](docs/COMPREHENSIVE_TESTING_COMPLETE.md)

## 🤝 Contributing

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest black flake8 mypy

# Run code formatting
black .

# Run linting
flake8 .

# Run type checking
mypy .

# Run tests
pytest tests/
```

### Code Standards
- Follow PEP 8 style guidelines
- Add type hints for all functions
- Write comprehensive docstrings
- Include unit tests for new features
- Update documentation for API changes

## 📞 Support

### Getting Help
1. **Documentation**: Check the comprehensive docs in the `/docs` folder
2. **Troubleshooting**: Follow the troubleshooting guide above
3. **Health Checks**: Use `/health` endpoint for system diagnostics
4. **Logs**: Enable debug logging for detailed error information

### Reporting Issues
- Include system information and error logs
- Provide steps to reproduce the issue
- Check existing documentation first
- Test with the latest version

---

**Built with ❤️ using FastAPI, LangChain, PostgreSQL, and Google Gemini AI**

---

**© 2025 Debmalya Koner. All rights reserved.**
