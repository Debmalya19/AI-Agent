# Intelligent Chat UI API Documentation

This document describes the new API endpoints added for the intelligent chat UI system, which enhance the existing chat functionality with real-time status updates, context retrieval, and tool information.

## Overview

The intelligent chat UI system adds four new endpoints to provide enhanced functionality:

1. `/chat/status` - Real-time system and session status
2. `/chat/context` - Conversation context retrieval  
3. `/chat/tools` - Available tools information
4. `/chat/ui-state/{session_id}` - UI state management

All endpoints require authentication via session token cookie.

## Enhanced Chat Endpoint

### POST `/chat`

The existing chat endpoint has been enhanced with intelligent chat UI integration while maintaining backward compatibility.

**Enhanced Response Fields:**
```json
{
  "topic": "string",           // Original field
  "summary": "string",         // Original field  
  "sources": ["string"],       // Original field
  "tools_used": ["string"],    // Original field
  "confidence_score": 0.85,    // NEW: Response confidence (0.0-1.0)
  "execution_time": 1.23,      // NEW: Processing time in seconds
  "content_type": "plain_text", // NEW: Content type classification
  "ui_state": {                // NEW: UI state information
    "loading_indicators": [...],
    "error_states": [...]
  }
}
```

**Behavior:**
- Attempts to use intelligent chat manager first
- Falls back to legacy agent executor if intelligent processing fails
- Maintains full backward compatibility with existing clients

## New Endpoints

### GET `/chat/status`

Get real-time tool execution updates and chat system status.

**Authentication:** Required (session token cookie)

**Response:**
```json
{
  "status": "success",
  "data": {
    "system_status": "operational",
    "intelligent_chat_enabled": true,
    "legacy_agent_enabled": true,
    "memory_layer_enabled": true,
    "timestamp": "2024-01-15T10:30:00Z",
    "session_stats": {
      "message_count": 5,
      "total_processing_time": 12.5,
      "tools_used_count": 8,
      "avg_processing_time": 2.5,
      "created_at": "2024-01-15T10:00:00Z",
      "last_activity": "2024-01-15T10:29:00Z"
    },
    "global_stats": {
      "total_conversations": 150,
      "active_sessions": 12,
      "avg_processing_time": 2.1,
      "memory_integration_enabled": true,
      "context_engine_enabled": true
    },
    "memory_stats": {
      "health_score": 0.95,
      "total_conversations": 1250,
      "average_response_time": 0.8,
      "error_count": 2
    }
  }
}
```

**Use Cases:**
- Monitor system health and performance
- Track session-specific statistics
- Real-time status updates for dashboards
- Performance monitoring and optimization

### GET `/chat/context`

Get conversation context for the current user.

**Authentication:** Required (session token cookie)

**Query Parameters:**
- `limit` (int, default: 10): Maximum number of context entries
- `include_metadata` (bool, default: false): Include metadata in response

**Response:**
```json
{
  "status": "success",
  "user_id": "user_123",
  "context_count": 3,
  "context_entries": [
    {
      "content": "Previous user question about BT plans",
      "source": "conversation_history",
      "relevance_score": 0.9,
      "timestamp": "2024-01-15T10:25:00Z",
      "context_type": "user_message",
      "metadata": {
        "session_id": "session_123",
        "message_id": "msg_456"
      }
    },
    {
      "content": "Bot response about BT broadband options",
      "source": "conversation_history", 
      "relevance_score": 0.8,
      "timestamp": "2024-01-15T10:25:30Z",
      "context_type": "bot_response",
      "metadata": {
        "tools_used": ["BTPlansInformation"],
        "confidence_score": 0.85
      }
    }
  ],
  "limit": 10,
  "include_metadata": true,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Use Cases:**
- Display conversation history in UI
- Context-aware follow-up suggestions
- Debugging conversation flow
- Analytics and conversation analysis

### GET `/chat/tools`

Get information about available tools and their current status.

**Authentication:** Required (session token cookie)

**Response:**
```json
{
  "status": "success",
  "tools": [
    {
      "name": "ContextRetriever",
      "description": "Use this tool to fetch relevant information from the database knowledge base using RAG.",
      "status": "available",
      "category": "context"
    },
    {
      "name": "BTWebsiteSearch", 
      "description": "Search BT website for current information",
      "status": "available",
      "category": "bt_specific"
    },
    {
      "name": "SupportKnowledgeBase",
      "description": "Fetch customer support responses from the database knowledge base",
      "status": "available", 
      "category": "support"
    }
  ],
  "tool_performance": {
    "total_tools": 9,
    "performance_data_available": true,
    "last_updated": "2024-01-15T10:30:00Z"
  },
  "orchestrator_status": {
    "enabled": true,
    "intelligent_selection": true,
    "parallel_execution": true,
    "context_aware_boosting": true
  },
  "categories": {
    "bt_specific": 3,
    "support": 2,
    "context": 2,
    "search": 1,
    "general": 1
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Tool Categories:**
- `bt_specific`: BT-specific tools (website, plans, support hours)
- `support`: Customer support tools (knowledge base, responses)
- `context`: Context and memory tools (RAG, context retrieval)
- `search`: General search tools (web search, Wikipedia)
- `general`: Other general-purpose tools

**Use Cases:**
- Display available tools to users
- Tool performance monitoring
- System capability discovery
- Debugging tool selection issues

### GET `/chat/ui-state/{session_id}`

Get current UI state for a specific session.

**Authentication:** Required (session token cookie)

**Path Parameters:**
- `session_id` (string): Session identifier

**Response:**
```json
{
  "status": "success",
  "ui_state": {
    "session_id": "session_123",
    "loading_indicators": [
      {
        "tool_name": "ContextRetriever",
        "state": "loading",
        "progress": 0.7,
        "message": "Retrieving conversation context...",
        "estimated_time": 2.5
      }
    ],
    "error_states": [
      {
        "error_type": "tool_timeout",
        "message": "Tool execution timed out",
        "severity": "warning",
        "recovery_actions": ["retry", "use_alternative_tool"],
        "context": {
          "tool_name": "BTWebsiteSearch",
          "timeout_duration": 30.0
        }
      }
    ],
    "content_sections": [
      {
        "content": "Here are the available BT plans:",
        "content_type": "plain_text",
        "metadata": {
          "source": "BTPlansInformation"
        },
        "order": 1
      }
    ],
    "interactive_elements": [
      {
        "element_type": "button",
        "element_id": "retry_search",
        "properties": {
          "label": "Retry Search",
          "variant": "primary"
        },
        "actions": ["click"]
      }
    ],
    "last_updated": "2024-01-15T10:30:00Z"
  }
}
```

**Loading States:**
- `idle`: Tool not active
- `loading`: Tool is executing
- `processing`: Tool is processing results
- `completed`: Tool execution completed
- `error`: Tool execution failed

**Error Severities:**
- `info`: Informational message
- `warning`: Warning that doesn't prevent operation
- `error`: Error that affects functionality
- `critical`: Critical error requiring immediate attention

**Use Cases:**
- Real-time UI updates during tool execution
- Progress indicators for long-running operations
- Error state management and recovery
- Interactive element management

## Error Responses

All endpoints return consistent error responses:

```json
{
  "detail": "Error description"
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `401`: Unauthorized (missing or invalid session token)
- `500`: Internal server error

## Authentication

All endpoints require authentication via session token cookie:

```http
Cookie: session_token=your_session_token_here
```

The session token is obtained through the existing `/login` endpoint.

## Integration Examples

### Real-time Status Updates

```javascript
// Poll for status updates
async function pollChatStatus() {
  try {
    const response = await fetch('/chat/status', {
      credentials: 'include' // Include cookies
    });
    const data = await response.json();
    
    if (data.status === 'success') {
      updateStatusDisplay(data.data);
    }
  } catch (error) {
    console.error('Status update failed:', error);
  }
}

// Poll every 5 seconds
setInterval(pollChatStatus, 5000);
```

### Context-Aware UI

```javascript
// Get conversation context for display
async function loadConversationContext() {
  try {
    const response = await fetch('/chat/context?limit=5&include_metadata=true', {
      credentials: 'include'
    });
    const data = await response.json();
    
    if (data.status === 'success') {
      displayContextEntries(data.context_entries);
    }
  } catch (error) {
    console.error('Context loading failed:', error);
  }
}
```

### Tool Information Display

```javascript
// Display available tools
async function loadAvailableTools() {
  try {
    const response = await fetch('/chat/tools', {
      credentials: 'include'
    });
    const data = await response.json();
    
    if (data.status === 'success') {
      displayToolsGrid(data.tools, data.categories);
      updateOrchestratorStatus(data.orchestrator_status);
    }
  } catch (error) {
    console.error('Tools loading failed:', error);
  }
}
```

## Performance Considerations

- **Caching**: Context and tool information are cached for performance
- **Rate Limiting**: Consider implementing rate limiting for status polling
- **Pagination**: Context endpoint supports limit parameter for large histories
- **Metadata**: Use `include_metadata=false` for faster context retrieval when metadata isn't needed

## Backward Compatibility

The enhanced `/chat` endpoint maintains full backward compatibility:
- All original response fields are preserved
- New fields are added without breaking existing clients
- Legacy agent executor is used as fallback
- Existing authentication and session management unchanged

## Future Enhancements

Planned improvements include:
- WebSocket support for real-time updates
- Server-sent events for status streaming
- Enhanced tool performance analytics
- Advanced UI state management
- Tool execution queuing and prioritization