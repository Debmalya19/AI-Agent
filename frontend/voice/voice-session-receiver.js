/**
 * Voice Session Receiver
 * Handles session data and communication from main chat interface
 */

class VoiceSessionReceiver {
    constructor() {
        this.sessionData = null;
        this.isInitialized = false;
        this.parentOrigin = null;
        this.messageHandlers = new Map();
        
        // Bind methods
        this.handleMessage = this.handleMessage.bind(this);
        this.handleBeforeUnload = this.handleBeforeUnload.bind(this);
        
        // Initialize message listener
        window.addEventListener('message', this.handleMessage);
        window.addEventListener('beforeunload', this.handleBeforeUnload);
        
        // Signal that voice page is ready
        this.signalReady();
        
        console.log('Voice Session Receiver initialized');
    }
    
    /**
     * Signal to parent window that voice page is ready
     */
    signalReady() {
        // Try to determine parent origin
        const referrer = document.referrer;
        if (referrer) {
            try {
                const url = new URL(referrer);
                this.parentOrigin = url.origin;
            } catch (error) {
                console.warn('Could not parse referrer URL:', error);
            }
        }
        
        // Default to same origin if referrer not available
        if (!this.parentOrigin) {
            this.parentOrigin = window.location.origin;
        }
        
        // Signal ready to parent
        if (window.opener) {
            try {
                window.opener.postMessage({
                    type: 'VOICE_PAGE_READY',
                    data: {
                        timestamp: Date.now(),
                        url: window.location.href
                    }
                }, this.parentOrigin);
                
                console.log('Signaled ready to parent window');
            } catch (error) {
                console.error('Failed to signal ready to parent:', error);
            }
        }
    }
    
    /**
     * Handle messages from parent window
     */
    handleMessage(event) {
        // Verify origin for security
        if (event.origin !== this.parentOrigin && event.origin !== window.location.origin) {
            console.warn('Ignoring message from unknown origin:', event.origin);
            return;
        }
        
        if (!event.data || typeof event.data !== 'object') {
            return;
        }
        
        const { type, data } = event.data;
        
        switch (type) {
            case 'INIT_SESSION':
                this.handleSessionInit(data);
                break;
                
            case 'SESSION_UPDATE':
                this.handleSessionUpdate(data);
                break;
                
            case 'CONVERSATION_SYNC':
                this.handleConversationSync(data);
                break;
                
            default:
                console.log('Unknown message type from parent:', type);
        }
    }
    
    /**
     * Handle session initialization
     */
    handleSessionInit(sessionData) {
        console.log('Received session data from parent:', sessionData);
        
        this.sessionData = sessionData;
        this.isInitialized = true;
        
        // Validate session data
        if (!this.validateSessionData(sessionData)) {
            console.error('Invalid session data received');
            this.showError('Invalid session data. Please refresh and try again.');
            return;
        }
        
        // Initialize voice assistant with session context
        this.initializeVoiceAssistant(sessionData);
        
        // Emit session ready event
        this.emit('sessionReady', sessionData);
    }
    
    /**
     * Handle session updates
     */
    handleSessionUpdate(sessionData) {
        console.log('Received session update from parent');
        
        if (this.sessionData) {
            // Merge with existing session data
            this.sessionData = { ...this.sessionData, ...sessionData };
        } else {
            this.sessionData = sessionData;
        }
        
        this.emit('sessionUpdated', this.sessionData);
    }
    
    /**
     * Handle conversation sync
     */
    handleConversationSync(conversationData) {
        console.log('Received conversation sync from parent');
        
        if (this.sessionData) {
            this.sessionData.conversationHistory = conversationData.messages || [];
        }
        
        this.emit('conversationSynced', conversationData);
    }
    
    /**
     * Validate session data
     */
    validateSessionData(sessionData) {
        if (!sessionData) return false;
        
        const required = ['sessionId', 'timestamp', 'origin'];
        return required.every(field => sessionData.hasOwnProperty(field));
    }
    
    /**
     * Initialize voice assistant with session context
     */
    initializeVoiceAssistant(sessionData) {
        // Set up API client with session context
        if (window.VoiceAPIClient) {
            const apiClient = new window.VoiceAPIClient();
            apiClient.setSessionContext(sessionData);
        }
        
        // Display conversation history if available
        if (sessionData.conversationHistory && sessionData.conversationHistory.length > 0) {
            this.displayConversationHistory(sessionData.conversationHistory);
        }
        
        // Update UI with session info
        this.updateUIWithSessionInfo(sessionData);
        
        console.log('Voice assistant initialized with session context');
    }
    
    /**
     * Display conversation history in voice assistant
     */
    displayConversationHistory(messages) {
        const transcriptArea = document.getElementById('transcript-area');
        const responseArea = document.getElementById('response-area');
        
        if (!transcriptArea || !responseArea) return;
        
        // Get the last user message and bot response for context
        const lastUserMessage = messages.filter(m => m.role === 'user').pop();
        const lastBotMessage = messages.filter(m => m.role === 'assistant').pop();
        
        if (lastUserMessage) {
            const transcriptText = transcriptArea.querySelector('.transcript-text');
            if (transcriptText) {
                transcriptText.textContent = lastUserMessage.content;
                transcriptArea.style.opacity = '0.7'; // Show as historical
            }
        }
        
        if (lastBotMessage) {
            const responseText = responseArea.querySelector('.response-text');
            if (responseText) {
                responseText.textContent = lastBotMessage.content;
                responseArea.style.opacity = '0.7'; // Show as historical
            }
        }
        
        // Update status to show context loaded
        const statusText = document.getElementById('status-text');
        if (statusText) {
            statusText.textContent = 'Context loaded - tap to continue conversation';
        }
    }
    
    /**
     * Update UI with session information
     */
    updateUIWithSessionInfo(sessionData) {
        // Update page title if needed
        if (sessionData.userId) {
            document.title = `Voice Assistant - User ${sessionData.userId}`;
        }
        
        // Add session indicator to UI
        const header = document.getElementById('voice-header');
        if (header && !header.querySelector('.session-indicator')) {
            const sessionIndicator = document.createElement('div');
            sessionIndicator.className = 'session-indicator';
            sessionIndicator.innerHTML = `
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                    <path d="M8 12L11 15L16 9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span>Connected</span>
            `;
            sessionIndicator.style.cssText = `
                position: absolute;
                top: 10px;
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                align-items: center;
                gap: 4px;
                font-size: 0.8rem;
                color: rgba(255, 255, 255, 0.7);
                background: rgba(76, 175, 80, 0.2);
                padding: 4px 8px;
                border-radius: 12px;
                border: 1px solid rgba(76, 175, 80, 0.3);
            `;
            header.appendChild(sessionIndicator);
        }
    }
    
    /**
     * Send message to parent window
     */
    sendToParent(type, data) {
        if (!window.opener) {
            console.warn('No parent window available');
            return;
        }
        
        try {
            window.opener.postMessage({
                type: type,
                data: data
            }, this.parentOrigin);
            
            console.log('Sent message to parent:', type);
        } catch (error) {
            console.error('Failed to send message to parent:', error);
        }
    }
    
    /**
     * Request session sync from parent
     */
    requestSessionSync() {
        this.sendToParent('VOICE_SESSION_SYNC', {
            timestamp: Date.now(),
            requestId: this.generateRequestId()
        });
    }
    
    /**
     * Send conversation update to parent
     */
    sendConversationUpdate(message, response) {
        this.sendToParent('VOICE_CONVERSATION_UPDATE', {
            message: message,
            response: response,
            timestamp: Date.now(),
            sessionId: this.sessionData?.sessionId
        });
    }
    
    /**
     * Request to close voice page
     */
    requestClose() {
        this.sendToParent('VOICE_PAGE_CLOSE_REQUEST', {
            timestamp: Date.now(),
            reason: 'user_requested'
        });
    }
    
    /**
     * Handle before unload
     */
    handleBeforeUnload() {
        // Notify parent that window is closing
        this.sendToParent('VOICE_PAGE_CLOSING', {
            timestamp: Date.now(),
            reason: 'window_closing'
        });
    }
    
    /**
     * Get session data
     */
    getSessionData() {
        return this.sessionData;
    }
    
    /**
     * Check if session is initialized
     */
    isSessionReady() {
        return this.isInitialized && this.sessionData !== null;
    }
    
    /**
     * Show error message
     */
    showError(message) {
        const statusText = document.getElementById('status-text');
        if (statusText) {
            statusText.textContent = message;
            statusText.style.color = '#f44336';
        }
        
        console.error('Voice Session Error:', message);
    }
    
    /**
     * Generate unique request ID
     */
    generateRequestId() {
        return 'req_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * Simple event emitter functionality
     */
    emit(eventName, data) {
        const handlers = this.messageHandlers.get(eventName) || [];
        handlers.forEach(handler => {
            try {
                handler(data);
            } catch (error) {
                console.error('Error in event handler:', error);
            }
        });
    }
    
    /**
     * Add event listener
     */
    on(eventName, handler) {
        if (!this.messageHandlers.has(eventName)) {
            this.messageHandlers.set(eventName, []);
        }
        this.messageHandlers.get(eventName).push(handler);
    }
    
    /**
     * Remove event listener
     */
    off(eventName, handler) {
        const handlers = this.messageHandlers.get(eventName);
        if (handlers) {
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }
    
    /**
     * Clean up resources
     */
    destroy() {
        window.removeEventListener('message', this.handleMessage);
        window.removeEventListener('beforeunload', this.handleBeforeUnload);
        this.messageHandlers.clear();
        console.log('Voice Session Receiver destroyed');
    }
}

// Auto-initialize when script loads
window.voiceSessionReceiver = new VoiceSessionReceiver();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceSessionReceiver;
}