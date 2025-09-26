**© 2025 Debmalya Koner. All rights reserved.**

## Overview
A comprehensive AI-powered customer support system built with FastAPI and Google Gemini AI, featuring intelligent chat capabilities, voice interaction, memory layer management, multi-tool orchestration, and database-backed knowledge retrieval. The system provides contextual, personalized responses using advanced RAG (Retrieval-Augmented Generation) technology, intelligent tool selection, and real-time voice communication capabilities.

## 🚀 Key Features

### 🎤 Voice-Enabled AI Assistant
- **Voice Input Recognition**: Real-time speech-to-text using Web Speech API
- **Text-to-Speech Output**: Natural voice responses with customizable voices
- **Voice Settings Management**: Configurable voice preferences and audio controls
- **Voice Analytics**: Performance tracking and usage analytics for voice interactions
- **Error Recovery**: Intelligent fallback mechanisms for voice failures
- **Auto-Play Responses**: Optional automatic playback of AI responses

### 🧠 Intelligent Chat UI
- **Dynamic Response Adaptation**: UI adapts based on conversation context and response type
- **Real-time Tool Orchestration**: Automatic selection and execution of relevant tools
- **Context-Aware Conversations**: Maintains conversation history for natural follow-up interactions
- **Visual Feedback System**: Loading indicators and progress tracking during tool execution
- **Error Recovery**: Graceful error handling with user-friendly messages
- **Multi-Modal Interface**: Seamless integration between text and voice interactions

### 💾 Advanced Memory Layer
- **Persistent Conversation Storage**: Chat history maintained across sessions with PostgreSQL
- **Context Retrieval Engine**: Intelligent context extraction from conversation history
- **Tool Usage Analytics**: Learning from previous tool usage patterns
- **Memory Configuration**: Configurable retention policies and cleanup strategies
- **Performance Optimization**: Efficient memory management with caching
- **Session Memory**: Enhanced session-based memory for personalized experiences

### 🛠️ Multi-Tool Orchestration System
- **Intelligent Tool Selection**: Algorithm-based tool selection for optimal responses
- **Parallel Tool Execution**: Concurrent tool execution for faster responses
- **Tool Performance Monitoring**: Analytics and optimization of tool usage
- **Context-Aware Tool Recommendations**: Historical data influences tool selection
- **Comprehensive Answer Generation**: Multi-source information synthesis
- **BT-Specific Tools**: Specialized tools for BT.com website scraping and information retrieval

### 🔐 Security & Privacy
- **Secure Session Management**: Hashed session tokens with configurable expiration
- **User Authentication**: Complete registration and login system with bcrypt encryption
- **GDPR Compliance**: Privacy-focused data handling and retention policies
- **Security Integration**: Comprehensive security monitoring and threat detection
- **Data Encryption**: Sensitive information protection at rest and in transit
- **Privacy Utils**: Advanced privacy protection and data anonymization

### 📊 Database Integration
- **PostgreSQL Backend**: Full PostgreSQL integration with optimized schema
- **Knowledge Base Management**: Searchable knowledge entries with RAG capabilities
- **Customer Data Management**: Comprehensive customer and order tracking
- **Support Ticket System**: Automated ticket creation and management with priority classification
- **Analytics Storage**: Tool usage and performance metrics
- **Voice Data Storage**: Voice interaction logs and analytics

## 🏗️ System Architecture

<img width="1024" height="1024" alt="image" src="https://github.com/user-attachments/assets/4556be25-1dc5-4912-a0a6-d0e4d507a6a7" />


### Core Components

#### Backend Architecture
```
backend/
├── unified_startup.py         # Unified application startup system
├── unified_config.py          # Centralized configuration management
├── health_checks.py           # System health monitoring
├── unified_error_handler.py   # Unified error handling
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
├── voice_api.py              # Voice interaction API endpoints
├── analytics_service.py      # Analytics and monitoring
├── data_sync_service.py      # Data synchronization
├── admin_integration.py      # Admin dashboard integration
└── enhanced_rag_orchestrator.py # Advanced RAG system
```

#### Frontend Architecture
```
frontend/
├── chat.html                 # Main chat interface
├── login.html               # User authentication
├── register.html            # User registration
├── voice-controller.js      # Voice interaction controller
├── voice-ui.js             # Voice user interface components
├── voice-settings.js       # Voice configuration management
├── voice-capabilities.js   # Voice feature detection
├── voice-analytics.js      # Voice usage tracking
├── voice-error-handler.js  # Voice error management
├── voice-loader.js         # Lazy loading for voice modules
└── tests/                  # Frontend testing suite
```

#### Database Schema
- **Enhanced Chat History**: Conversation storage with context and voice metadata
- **Memory Context Cache**: Intelligent context caching with performance optimization
- **Tool Usage Metrics**: Performance analytics and optimization tracking
- **Conversation Summaries**: Automated conversation summarization
- **Memory Health Metrics**: System performance monitoring and alerts
- **Users & Sessions**: Secure authentication system with session management
- **Knowledge Entries**: RAG knowledge base with vector search capabilities
- **Support System**: Comprehensive ticket management with priority classification
- **Voice Analytics**: Voice interaction logs and performance metrics
- **Customer Data**: Customer information and order tracking
- **Support Intents & Responses**: Structured support knowledge base

### API Endpoints

#### Core Chat API
- `POST /chat` - Intelligent chat processing with multi-tool orchestration and voice support
- `GET /chat/status` - Real-time tool execution updates and system status
- `GET /chat/context` - Conversation context retrieval for enhanced responses
- `GET /chat/tools` - Available tools information and capabilities
- `GET /chat/ui-state/{session_id}` - UI state management for dynamic interfaces

#### Voice API Endpoints
- `POST /voice/synthesize` - Text-to-speech conversion with voice options
- `GET /voice/voices` - Available voice options and capabilities
- `POST /voice/settings` - Voice configuration management
- `GET /voice/analytics` - Voice usage analytics and performance metrics

#### Memory & Analytics
- `GET /memory/stats` - Memory layer statistics and health metrics
- `POST /memory/cleanup` - Manual memory cleanup operations
- `GET /learning/insights` - Learning insights for user interactions
- `GET /learning/conversation-patterns` - Conversation patterns and recommendations

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
- `GET /chat.html` - Intelligent chat interface with voice capabilities
- `GET /register.html` - User registration interface

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Google Gemini API Key

### 1. Environment Setup
```bash
# Navigate to the ai-agent directory
cd ai-agent

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup
```bash
# Install PostgreSQL and create database
# Make sure PostgreSQL is running on your system
createdb knowledge_base

# The .env file is already configured with:
# DATABASE_URL=postgresql://postgres:password@localhost:5432/knowledge_base
# GOOGLE_API_KEY=AIzaSyDeiOQQB9fHDHtsczKxqWcEqN9B5tDGCZE
# Update the database password if needed
```

### 3. Start the Application
```bash
# Start the AI Agent application
python main.py
```

**That's it! The application will:**
- Automatically initialize the database
- Set up all required tables and schemas
- Initialize AI components and memory layer
- Start the unified FastAPI server

### 4. Access the System
- **Login Page**: http://localhost:8080
- **Chat Interface**: http://localhost:8080/chat.html (after login)
- **Registration**: http://localhost:8080/register.html
- **API Documentation**: http://localhost:8080/docs
- **Health Check**: http://localhost:8080/health
- **Admin Dashboard**: http://localhost:8080/admin (if enabled)

### Alternative Start Methods
```bash
# Using uvicorn directly (recommended for Windows)
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8080

# Try different ports if 8080 is also blocked
python -m uvicorn main:app --reload --host 127.0.0.1 --port 3000
python -m uvicorn main:app --reload --host 127.0.0.1 --port 5000

# For development with auto-reload
python main.py --reload

# For production
python main.py --workers 4
```

## 💡 Usage Examples

### Intelligent Chat Interactions
```python
# Voice-enabled queries (speak or type)
"What are the current BT mobile plans and how do I upgrade my existing plan?"

# Context-aware follow-ups with voice responses
"What about the pricing for unlimited data?"
"Can you create a support ticket for my billing issue?"

# Customer service queries with voice output
"What are your support hours and how can I contact customer service?"
"I'm having trouble with my voicemail setup"

# Voice commands
"Enable auto-play for responses"
"Change voice settings"
"Stop voice playback"
```

### API Usage Examples

#### Chat with Voice Support
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=your_session_token" \
  -d '{
    "query": "What are the current mobile plans available?"
  }'
```

#### Voice Synthesis
```bash
curl -X POST http://localhost:8000/voice/synthesize \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=your_session_token" \
  -d '{
    "text": "Here are the current BT mobile plans available...",
    "voice": "default",
    "rate": 1.0,
    "pitch": 1.0
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
from backend.voice_api import VoiceController

# Initialize components
memory_manager = MemoryLayerManager()
chat_manager = ChatManager(memory_manager=memory_manager)

# Process message with context and voice support
response = await chat_manager.process_message(
    message="What are your support hours?",
    user_id="user123",
    session_id="session456"
)

print(f"Response: {response.content}")
print(f"Tools used: {response.tools_used}")
print(f"Confidence: {response.confidence_score}")

# Voice synthesis example
voice_controller = VoiceController()
audio_data = await voice_controller.synthesize_speech(
    text=response.content,
    voice_settings={"rate": 1.0, "pitch": 1.0}
)
```

## 🛠️ Available Tools & Capabilities

### Intelligent Tool Orchestration
The system features 9+ specialized tools that work together to provide comprehensive responses:

| Tool                            | Purpose                        | Use Case                                   |
|---------------------------------|--------------------------------|--------------------------------------------|
| **ContextRetriever**            | Database knowledge base search | Primary information source with RAG        |
| **SupportKnowledgeBase**        | Customer support responses     | Common support queries and intents         |
| **IntelligentToolOrchestrator** | Smart multi-tool coordination  | Complex queries requiring multiple sources |
| **CreateSupportTicket**         | Automated ticket creation      | Customer issues and escalations            |
| **BTWebsiteSearch**             | Real-time BT.com scraping      | Current BT services and information        |
| **BTSupportHours**              | Live support hours data        | Contact information and availability       |
| **BTPlansInformation**          | Current plan pricing           | Mobile plans and pricing details           |
| **Search Tool**                 | Web search capabilities        | Additional context and information         |
| **Wiki Tool**                   | Wikipedia integration          | Background and educational content         |

### Voice Capabilities
- **Speech Recognition**: Real-time voice input using Web Speech API
- **Text-to-Speech**: Natural voice output with multiple voice options
- **Voice Settings**: Customizable voice preferences (rate, pitch, volume)
- **Voice Analytics**: Performance tracking and usage statistics
- **Error Handling**: Intelligent fallback for voice failures
- **Multi-language Support**: Voice recognition and synthesis in multiple languages

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

# Test voice integration
python tests/test_voice_integration.py

# Demo intelligent chat capabilities
python examples/demo_multi_tool.py

# Test memory layer functionality
python examples/example_memory_usage.py

# Performance optimization demo
python examples/performance_optimization_demo.py

# Voice analytics demo
python scripts/run_comprehensive_voice_tests.py
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

# Test voice integration and capabilities
python tests/test_comprehensive_voice_suite.py

# Test intelligent chat components
python tests/test_intelligent_chat_basic.py

# Test memory layer functionality
python tests/test_memory_layer_manager.py

# Test security and privacy features
python tests/test_security_privacy.py

# Test voice analytics
python tests/test_voice_analytics.py
```

### Component-Specific Testing
```bash
# Database connectivity
python scripts/database_init.py

# Memory layer validation
python scripts/verify_memory_schema.py

# Voice system validation
python scripts/voice_migration.py

# Tool orchestration testing
python examples/demo_multi_tool.py

# Performance benchmarking
python examples/performance_optimization_demo.py

# Voice performance testing
python tests/test_voice_error_handling.py
```

### Integration Testing
```bash
# End-to-end chat flow with voice
python tests/test_comprehensive_integration.py

# Multi-tool orchestration
python tests/test_tool_orchestrator.py

# Context retrieval and memory
python tests/test_context_retrieval_engine.py

# Voice integration testing
python tests/test_voice_integration.py

# Enhanced session memory
python tests/test_enhanced_session_memory.py
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
- **Voice Optimization**: Lazy loading of voice modules and efficient audio processing
- **Performance Monitoring**: Real-time performance tracking and optimization

### Monitoring & Analytics
- **Tool Performance Metrics**: Usage analytics and optimization recommendations
- **Memory Health Monitoring**: System performance tracking and alerts
- **Response Time Analytics**: Continuous performance optimization
- **Resource Usage Tracking**: CPU, memory, and database performance monitoring
- **Voice Analytics**: Voice interaction tracking, error rates, and usage patterns
- **User Experience Metrics**: Response quality scoring and user satisfaction tracking

## 🔧 Troubleshooting

### Windows Port Permission Issues

If you get `[WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions`:

**Solution 1: Use a different port**
```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8080
# Or try: 3000, 5000, 9000
```

**Solution 2: Run as Administrator**
```bash
# Right-click Command Prompt/PowerShell and "Run as Administrator"
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Solution 3: Check what's using port 8000**
```bash
netstat -ano | findstr :8000
# Kill the process if needed: taskkill /PID <process_id> /F
```

**Solution 4: Use localhost instead of 0.0.0.0**
```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

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
python tests/test_tool_orchestrator.py

# Test tool usage analytics
python tests/test_tool_usage_analytics.py
```

#### Voice Issues
```bash
# Check voice capabilities and integration
python tests/test_voice_analytics.py

# Test voice controller integration
python tests/test_voice_integration.py

# Check voice API endpoints
python tests/test_voice_api.py

# Test voice error handling
python tests/test_voice_error_handling.py

# Run comprehensive voice tests
python scripts/run_comprehensive_voice_tests.py
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

# Voice and analytics configuration
VOICE_ANALYTICS_ENABLED=true
VOICE_ERROR_TRACKING=true
PERFORMANCE_MONITORING=true
VOICE_RATE_LIMITING=true
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

### Enhanced Chat API with Voice Support
```http
POST /chat
Content-Type: application/json
Cookie: session_token=your_session_token

{
  "query": "What are the current mobile plans and pricing?",
  "voice_enabled": true,
  "auto_play": false
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
    "error_states": [],
    "voice_available": true,
    "auto_play_enabled": false
  },
  "voice_metadata": {
    "synthesizable": true,
    "estimated_duration": 15.2,
    "voice_quality_score": 0.9
  }
}
```

### Voice API
```http
POST /voice/synthesize
Content-Type: application/json
Cookie: session_token=your_session_token

{
  "text": "Here are the current BT mobile plans...",
  "voice": "default",
  "rate": 1.0,
  "pitch": 1.0,
  "volume": 1.0
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
- [Voice Analytics Implementation](docs/VOICE_ANALYTICS_IMPLEMENTATION_SUMMARY.md)
- [Voice Production Optimization](docs/VOICE_PRODUCTION_OPTIMIZATION_SUMMARY.md)

### Voice Documentation
- [Voice Integration Summary](frontend/VOICE_INTEGRATION_SUMMARY.md)
- [Voice Testing Guide](tests/VOICE_TESTING_README.md)
- [Error Handling Summary](frontend/ERROR_HANDLING_SUMMARY.md)

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

## 🎯 Current Project Status

### ✅ Fully Implemented Features
- **Core AI Chat System**: FastAPI + Google Gemini AI integration
- **Voice Capabilities**: Complete voice input/output with Web Speech API
- **Multi-Tool Orchestration**: 9+ specialized tools for comprehensive responses
- **Memory Layer**: PostgreSQL-backed conversation storage and context retrieval
- **User Authentication**: Secure login/registration with session management
- **Support Ticket System**: Automated ticket creation with priority classification
- **BT-Specific Tools**: Real-time BT.com scraping and information retrieval
- **Performance Analytics**: Comprehensive monitoring and optimization
- **Security & Privacy**: GDPR compliance and data protection
- **Responsive UI**: Mobile-friendly chat interface with voice controls

### 🚧 Advanced Features
- **Unified Startup System**: Centralized application initialization and configuration
- **Intelligent Context Retrieval**: Enhanced RAG with conversation history
- **Voice Analytics**: Usage tracking and performance optimization
- **Error Recovery**: Intelligent fallback mechanisms with unified error handling
- **Real-time Status Updates**: Live tool execution feedback and health monitoring
- **Memory Management**: Configurable retention policies and cleanup
- **Performance Optimization**: Caching, parallel processing, and monitoring
- **Admin Dashboard Integration**: Complete admin interface with data synchronization

### 📊 Technical Specifications
- **Backend**: Python 3.8+, FastAPI, SQLAlchemy, PostgreSQL
- **AI Integration**: Google Gemini 2.0 Flash, LangChain
- **Frontend**: HTML5, JavaScript ES6+, Web Speech API
- **Database**: PostgreSQL with optimized schema for chat and voice data
- **Security**: bcrypt encryption, session tokens, GDPR compliance
- **Testing**: Comprehensive test suite with 50+ test files
- **Documentation**: Extensive documentation with implementation guides

---

**Built with ❤️ using FastAPI, LangChain, PostgreSQL, Google Gemini AI, and Web Speech API**

*A comprehensive AI-powered customer support system with advanced voice capabilities, intelligent tool orchestration, and enterprise-grade security.*

---

**© 2025 Debmalya Koner. All rights reserved.**
