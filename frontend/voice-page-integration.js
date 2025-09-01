/**
 * Voice Page Integration Module
 * Handles communication between main chat interface and voice assistant page
 */

class VoicePageIntegration {
    constructor() {
        this.voiceWindow = null;
        this.sessionData = null;
        this.isVoicePageOpen = false;
        this.messageHandlers = new Map();

        // Bind methods
        this.handleMessage = this.handleMessage.bind(this);
        this.handleVoiceWindowClose = this.handleVoiceWindowClose.bind(this);

        // Initialize message listener
        window.addEventListener('message', this.handleMessage);

        console.log('Voice Page Integration initialized');
    }

    /**
     * Open voice assistant page with session context
     */
    async openVoiceAssistant() {
        if (this.isVoicePageOpen && this.voiceWindow && !this.voiceWindow.closed) {
            // Focus existing window
            this.voiceWindow.focus();
            return;
        }

        try {
            // Gather session data from main chat
            this.sessionData = await this.gatherSessionData();

            // Calculate window dimensions and position
            const windowFeatures = this.calculateWindowFeatures();

            // Open voice assistant window
            this.voiceWindow = window.open(
                '/static/voice/voice-assistant.html',
                'voice-assistant',
                windowFeatures
            );

            if (!this.voiceWindow) {
                throw new Error('Failed to open voice assistant window. Please allow popups.');
            }

            this.isVoicePageOpen = true;

            // Set up window close detection
            this.setupWindowCloseDetection();

            // Wait for window to load and send session data
            this.voiceWindow.addEventListener('load', () => {
                this.sendSessionDataToVoicePage();
            });

            // If window is already loaded (cached), send data immediately
            if (this.voiceWindow.document.readyState === 'complete') {
                setTimeout(() => this.sendSessionDataToVoicePage(), 100);
            }

            console.log('Voice assistant window opened');

        } catch (error) {
            console.error('Failed to open voice assistant:', error);
            this.showError('Failed to open voice assistant: ' + error.message);
        }
    }

    /**
     * Gather session data from main chat interface
     */
    async gatherSessionData() {
        try {
            // Get current session info
            const sessionResponse = await fetch('/me', {
                credentials: 'include'
            });

            if (!sessionResponse.ok) {
                throw new Error('Session validation failed');
            }

            const sessionInfo = await sessionResponse.json();

            // Get conversation context from chat log
            const conversationContext = this.extractConversationContext();

            return {
                sessionId: this.generateSessionId(),
                userId: sessionInfo.user_id || sessionInfo.id,
                authenticated: sessionInfo.authenticated,
                conversationHistory: conversationContext,
                timestamp: Date.now(),
                origin: window.location.origin
            };

        } catch (error) {
            console.error('Failed to gather session data:', error);
            throw error;
        }
    }

    /**
     * Extract conversation context from chat log
     */
    extractConversationContext() {
        const chatLog = document.getElementById('chat-log');
        if (!chatLog) return [];

        const messages = [];
        const chatEntries = chatLog.querySelectorAll('.chat-entry');

        // Get last 10 messages for context
        const recentEntries = Array.from(chatEntries).slice(-10);

        recentEntries.forEach(entry => {
            const isUser = entry.classList.contains('user');
            const isBot = entry.classList.contains('bot');
            const isError = entry.classList.contains('error');

            if (isUser || isBot) {
                const messageContent = entry.querySelector('.message-content') || entry;
                const text = messageContent.textContent.trim();

                if (text) {
                    messages.push({
                        role: isUser ? 'user' : 'assistant',
                        content: text,
                        timestamp: Date.now(),
                        isError: isError
                    });
                }
            }
        });

        return messages;
    }

    /**
     * Calculate optimal window features for voice assistant
     */
    calculateWindowFeatures() {
        const screenWidth = window.screen.availWidth;
        const screenHeight = window.screen.availHeight;

        // Voice assistant dimensions
        const width = Math.min(900, screenWidth * 0.8);
        const height = Math.min(700, screenHeight * 0.8);

        // Center the window
        const left = Math.round((screenWidth - width) / 2);
        const top = Math.round((screenHeight - height) / 2);

        return [
            `width=${width}`,
            `height=${height}`,
            `left=${left}`,
            `top=${top}`,
            'resizable=yes',
            'scrollbars=no',
            'status=no',
            'menubar=no',
            'toolbar=no',
            'location=no',
            'directories=no'
        ].join(',');
    }

    /**
     * Send session data to voice assistant page
     */
    sendSessionDataToVoicePage() {
        if (!this.voiceWindow || this.voiceWindow.closed) {
            console.warn('Voice window not available for session data');
            return;
        }

        try {
            this.voiceWindow.postMessage({
                type: 'INIT_SESSION',
                data: this.sessionData
            }, window.location.origin);

            console.log('Session data sent to voice page');

        } catch (error) {
            console.error('Failed to send session data:', error);
        }
    }

    /**
     * Set up window close detection
     */
    setupWindowCloseDetection() {
        if (!this.voiceWindow) return;

        // Poll for window close
        const checkClosed = () => {
            if (this.voiceWindow && this.voiceWindow.closed) {
                this.handleVoiceWindowClose();
            } else if (this.isVoicePageOpen) {
                setTimeout(checkClosed, 1000);
            }
        };

        setTimeout(checkClosed, 1000);

        // Also listen for beforeunload
        this.voiceWindow.addEventListener('beforeunload', this.handleVoiceWindowClose);
    }

    /**
     * Handle voice window closing
     */
    handleVoiceWindowClose() {
        console.log('Voice assistant window closed');

        this.isVoicePageOpen = false;
        this.voiceWindow = null;

        // Focus back to main chat
        window.focus();

        // Focus the input field
        const queryInput = document.getElementById('query-input');
        if (queryInput) {
            queryInput.focus();
        }

        // Emit close event for any listeners
        this.emit('voicePageClosed');
    }

    /**
     * Handle messages from voice assistant page
     */
    handleMessage(event) {
        // Verify origin for security
        if (event.origin !== window.location.origin) {
            console.warn('Ignoring message from unknown origin:', event.origin);
            return;
        }

        if (!event.data || typeof event.data !== 'object') {
            return;
        }

        const { type, data } = event.data;

        switch (type) {
            case 'VOICE_PAGE_READY':
                this.handleVoicePageReady(data);
                break;

            case 'VOICE_PAGE_CLOSE_REQUEST':
                this.closeVoiceAssistant();
                break;

            case 'VOICE_CONVERSATION_UPDATE':
                this.handleConversationUpdate(data);
                break;

            case 'VOICE_SESSION_SYNC':
                this.handleSessionSync(data);
                break;

            default:
                console.log('Unknown message type from voice page:', type);
        }
    }

    /**
     * Handle voice page ready signal
     */
    handleVoicePageReady(data) {
        console.log('Voice page ready, sending session data');
        this.sendSessionDataToVoicePage();
    }

    /**
     * Handle conversation updates from voice page
     */
    handleConversationUpdate(data) {
        console.log('Conversation update from voice page:', data);

        // Optionally sync conversation back to main chat
        if (data.message && data.response) {
            this.syncConversationToMainChat(data);
        }
    }

    /**
     * Handle session sync requests
     */
    handleSessionSync(data) {
        console.log('Session sync request from voice page');

        // Re-gather and send fresh session data
        this.gatherSessionData().then(sessionData => {
            this.sessionData = sessionData;
            this.sendSessionDataToVoicePage();
        }).catch(error => {
            console.error('Failed to sync session:', error);
        });
    }

    /**
     * Sync conversation from voice page back to main chat
     */
    syncConversationToMainChat(conversationData) {
        const { message, response } = conversationData;

        // Add to main chat log if not already present
        const chatLog = document.getElementById('chat-log');
        if (chatLog && message && response) {
            // Check if this conversation is already in the log
            const existingEntries = chatLog.querySelectorAll('.chat-entry');
            const lastUserMessage = Array.from(existingEntries)
                .reverse()
                .find(entry => entry.classList.contains('user'));

            if (!lastUserMessage || lastUserMessage.textContent.trim() !== message.trim()) {
                // Add user message
                this.appendMessageToChat('user', message);

                // Add bot response
                this.appendMessageToChat('bot', response);
            }
        }
    }

    /**
     * Append message to main chat log
     */
    appendMessageToChat(sender, message) {
        const chatLog = document.getElementById('chat-log');
        if (!chatLog) return;

        const entry = document.createElement('div');
        entry.classList.add('chat-entry', sender);

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = message;

        entry.appendChild(messageContent);
        chatLog.appendChild(entry);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    /**
     * Close voice assistant window
     */
    closeVoiceAssistant() {
        if (this.voiceWindow && !this.voiceWindow.closed) {
            this.voiceWindow.close();
        }
        this.handleVoiceWindowClose();
    }

    /**
     * Generate unique session ID
     */
    generateSessionId() {
        return 'voice_session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Show error message to user
     */
    showError(message) {
        // Try to show in chat log first
        const chatLog = document.getElementById('chat-log');
        if (chatLog) {
            this.appendMessageToChat('bot', '❌ ' + message);
            return;
        }

        // Fallback to alert
        alert(message);
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
        this.closeVoiceAssistant();
        this.messageHandlers.clear();
        console.log('Voice Page Integration destroyed');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoicePageIntegration;
}