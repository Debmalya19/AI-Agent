# Voice Page Integration

This document describes the implementation of Task 11: "Integrate voice page trigger from main chat interface".

## Overview

The voice page integration allows users to click the microphone button in the main chat interface to open a dedicated voice assistant page. The integration handles session data passing, window communication, and proper cleanup when the voice page is closed.

## Components

### 1. VoicePageIntegration (`voice-page-integration.js`)

Main integration class that handles:
- Opening the voice assistant page in a new window
- Gathering session data from the main chat interface
- Passing session context to the voice page
- Managing window communication
- Handling voice page closing

**Key Methods:**
- `openVoiceAssistant()` - Opens the voice assistant window
- `gatherSessionData()` - Collects session and conversation context
- `sendSessionDataToVoicePage()` - Sends session data to voice page
- `handleMessage()` - Handles messages from voice page
- `closeVoiceAssistant()` - Closes the voice assistant window

### 2. VoiceSessionReceiver (`voice/voice-session-receiver.js`)

Handles session data reception in the voice assistant page:
- Receives session data from parent window
- Validates session information
- Initializes voice assistant with session context
- Manages communication back to parent window

**Key Methods:**
- `handleSessionInit()` - Processes initial session data
- `sendToParent()` - Sends messages to parent window
- `requestClose()` - Requests parent to close voice page
- `sendConversationUpdate()` - Sends conversation updates to parent

### 3. Modified Chat Interface (`chat.html`)

Updated main chat interface to:
- Include voice page integration script
- Replace inline voice functionality with voice page trigger
- Handle voice page opening on microphone button click

### 4. Modified Voice Assistant (`voice/voice-assistant.html` & `voice-assistant.js`)

Enhanced voice assistant to:
- Include session receiver script
- Handle session data from parent window
- Send conversation updates back to parent
- Properly close and communicate with parent window

## Integration Flow

1. **User clicks microphone button** in main chat interface
2. **VoicePageIntegration** gathers current session data and conversation context
3. **New window opens** with voice assistant page using calculated dimensions
4. **VoiceSessionReceiver** signals ready to parent window
5. **Session data is passed** from parent to voice page
6. **Voice assistant initializes** with session context
7. **Conversation updates** are sent back to parent window
8. **Window closes** properly with cleanup and focus return

## Session Data Structure

```javascript
{
    sessionId: 'voice_session_timestamp_random',
    userId: 'user_id_from_backend',
    authenticated: true,
    conversationHistory: [
        {
            role: 'user|assistant',
            content: 'message content',
            timestamp: Date,
            isError: false
        }
    ],
    timestamp: Date.now(),
    origin: window.location.origin
}
```

## Message Types

### Parent to Voice Page:
- `INIT_SESSION` - Initial session data
- `SESSION_UPDATE` - Session updates
- `CONVERSATION_SYNC` - Conversation synchronization

### Voice Page to Parent:
- `VOICE_PAGE_READY` - Voice page loaded and ready
- `VOICE_PAGE_CLOSE_REQUEST` - Request to close voice page
- `VOICE_CONVERSATION_UPDATE` - New conversation data
- `VOICE_SESSION_SYNC` - Request session sync

## Window Features

The voice assistant window is opened with:
- **Size**: 900x700px (or 80% of screen if smaller)
- **Position**: Centered on screen
- **Features**: Resizable, no scrollbars, no browser UI
- **Focus**: Automatic focus on open, return focus on close

## Security Considerations

- **Origin validation** for all window messages
- **Input sanitization** for voice transcripts
- **Session validation** with backend
- **Secure communication** using same-origin policy

## Error Handling

- **Popup blocked**: User-friendly error message
- **Session expired**: Redirect to login
- **Network errors**: Retry logic with exponential backoff
- **Voice page fails**: Fallback to inline voice functionality

## Testing

Use `voice-integration-test.html` to test:
- Voice page integration functionality
- Session data gathering and passing
- Window communication
- Message handling
- Error scenarios

## Browser Compatibility

- **Chrome**: Full support
- **Firefox**: Full support
- **Safari**: Full support
- **Edge**: Full support
- **Mobile browsers**: Responsive design with touch optimization

## Requirements Fulfilled

✅ **1.1, 1.2**: Microphone button opens dedicated voice assistant page
✅ **1.4**: Clear way to return to main chat interface  
✅ **1.5**: Navigation handling with proper cleanup
✅ **1.6**: Session and context preservation

## Usage

### In Main Chat Interface:
```javascript
// Initialize voice page integration
const voicePageIntegration = new VoicePageIntegration();

// Open voice assistant
voicePageIntegration.openVoiceAssistant();
```

### In Voice Assistant Page:
```javascript
// Session receiver is auto-initialized
// Listen for session ready event
window.voiceSessionReceiver.on('sessionReady', (sessionData) => {
    console.log('Session ready:', sessionData);
});
```

## File Structure

```
ai-agent/frontend/
├── chat.html (modified)
├── voice-page-integration.js (new)
├── voice-integration-test.html (new)
└── voice/
    ├── voice-assistant.html (modified)
    ├── voice-assistant.js (modified)
    ├── voice-session-receiver.js (new)
    └── voice-api-client.js (modified)
```

## Future Enhancements

- **Multi-tab support**: Handle multiple voice pages
- **Conversation persistence**: Save conversation across sessions
- **Advanced window management**: Remember window position/size
- **Mobile optimization**: Native app integration
- **Accessibility improvements**: Screen reader support