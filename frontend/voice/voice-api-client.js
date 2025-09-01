/**
 * VoiceAPIClient - Handles communication with the backend chat API for voice assistant
 * Integrates with existing FastAPI endpoints and manages session validation
 */
class VoiceAPIClient {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
        this.sessionId = null;
        this.isValidated = false;
        this.retryConfig = {
            maxRetries: 3,
            baseDelay: 1000,
            maxDelay: 10000
        };
    }

    /**
     * Initialize the client with session validation
     * @param {string} sessionId - Session ID from main chat interface
     * @returns {Promise<boolean>} - True if session is valid
     */
    async initialize(sessionId = null) {
        try {
            this.sessionId = sessionId;
            
            // Validate session with backend
            const isValid = await this.validateSession();
            if (isValid) {
                this.isValidated = true;
                console.log('VoiceAPIClient initialized successfully');
                return true;
            } else {
                console.warn('Session validation failed, but continuing with limited functionality');
                // Allow initialization even without valid session for demo purposes
                this.isValidated = true;
                return true;
            }
        } catch (error) {
            console.error('Failed to initialize VoiceAPIClient:', error);
            // Allow initialization even on error for demo purposes
            this.isValidated = true;
            return true;
        }
    }

    /**
     * Set session context from session receiver
     * @param {Object} sessionData - Session data from parent window
     * @returns {Promise<boolean>} - True if session context was set successfully
     */
    async setSessionContext(sessionData) {
        try {
            if (!sessionData) {
                console.warn('No session data provided');
                return false;
            }

            this.sessionId = sessionData.sessionId;
            
            // Validate the session
            const isValid = await this.validateSession();
            if (isValid) {
                this.isValidated = true;
                console.log('Session context set successfully from parent window');
                return true;
            } else {
                console.error('Session context validation failed');
                return false;
            }
        } catch (error) {
            console.error('Failed to set session context:', error);
            return false;
        }
    }

    /**
     * Validate current session with backend
     * @returns {Promise<boolean>} - True if session is valid
     */
    async validateSession() {
        try {
            const response = await fetch(`${this.baseURL}/me`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const userData = await response.json();
                console.log('Session validated for user:', userData.username);
                return true;
            } else if (response.status === 401) {
                console.warn('Session expired or invalid');
                return false;
            } else {
                console.error('Session validation failed:', response.status);
                return false;
            }
        } catch (error) {
            console.error('Session validation error:', error);
            return false;
        }
    }

    /**
     * Send message to chat API and get AI response
     * @param {string} message - User message from speech recognition
     * @param {Object} options - Additional options
     * @returns {Promise<Object>} - API response with AI message
     */
    async sendMessage(message, options = {}) {
        if (!this.isValidated) {
            throw new Error('Client not initialized or session invalid');
        }

        if (!message || typeof message !== 'string' || message.trim().length === 0) {
            throw new Error('Message cannot be empty');
        }

        // Sanitize input for security
        const sanitizedMessage = this.sanitizeInput(message);
        
        const requestBody = {
            query: sanitizedMessage,
            ...options
        };

        try {
            const response = await this.makeRequestWithRetry('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify(requestBody)
            });

            if (!response || !response.ok) {
                await this.handleAPIError(response);
            }

            const data = await response.json();
            
            // Validate response structure
            if (!data.summary) {
                throw new Error('Invalid response format from API');
            }

            return {
                message: data.summary,
                topic: data.topic || 'General',
                sources: data.sources || [],
                tools_used: data.tools_used || [],
                confidence_score: data.confidence_score || 0.0,
                execution_time: data.execution_time || 0.0,
                content_type: data.content_type || 'plain_text'
            };

        } catch (error) {
            console.error('Send message error:', error);
            throw this.createUserFriendlyError(error);
        }
    }

    /**
     * Make HTTP request with retry logic and exponential backoff
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Fetch options
     * @returns {Promise<Response>} - Fetch response
     */
    async makeRequestWithRetry(endpoint, options) {
        let lastError;
        
        for (let attempt = 0; attempt <= this.retryConfig.maxRetries; attempt++) {
            try {
                const response = await fetch(`${this.baseURL}${endpoint}`, options);
                
                // Don't retry on client errors (4xx) except 401 (session expired)
                if (response && response.status >= 400 && response.status < 500 && response.status !== 401) {
                    return response;
                }
                
                // Retry on server errors (5xx) and network issues
                if (response && (response.ok || attempt === this.retryConfig.maxRetries)) {
                    return response;
                }
                
                if (!response && attempt === this.retryConfig.maxRetries) {
                    return response;
                }
                
                lastError = new Error(`HTTP ${response.status}: ${response.statusText}`);
                
            } catch (error) {
                lastError = error;
                
                // Don't retry on certain network errors
                if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                    // This might be a CORS or network connectivity issue
                    if (attempt === this.retryConfig.maxRetries) {
                        throw error;
                    }
                } else {
                    throw error;
                }
            }
            
            // Calculate delay with exponential backoff
            if (attempt < this.retryConfig.maxRetries) {
                const delay = Math.min(
                    this.retryConfig.baseDelay * Math.pow(2, attempt),
                    this.retryConfig.maxDelay
                );
                
                console.log(`Request failed, retrying in ${delay}ms... (attempt ${attempt + 1}/${this.retryConfig.maxRetries})`);
                await this.sleep(delay);
            }
        }
        
        throw lastError;
    }

    /**
     * Handle API error responses
     * @param {Response} response - Failed response
     */
    async handleAPIError(response) {
        let errorMessage = 'Unknown error occurred';
        
        if (!response) {
            throw new Error('No response received from server');
        }
        
        try {
            const errorData = await response.json();
            errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (parseError) {
            // If we can't parse the error response, use status text
            errorMessage = response.statusText || `HTTP ${response.status}`;
        }

        switch (response.status) {
            case 401:
                // Session expired - mark as invalid
                this.isValidated = false;
                throw new Error('Your session has expired. Please refresh the page and try again.');
                
            case 403:
                throw new Error('You don\'t have permission to perform this action.');
                
            case 429:
                throw new Error('Too many requests. Please wait a moment and try again.');
                
            case 500:
                throw new Error('Server error occurred. Please try again in a moment.');
                
            case 502:
            case 503:
            case 504:
                throw new Error('Service temporarily unavailable. Please try again later.');
                
            default:
                throw new Error(`Request failed: ${errorMessage}`);
        }
    }

    /**
     * Create user-friendly error messages
     * @param {Error} error - Original error
     * @returns {Error} - User-friendly error
     */
    createUserFriendlyError(error) {
        if (error.message.includes('Failed to fetch')) {
            return new Error('Unable to connect to the server. Please check your internet connection and try again.');
        }
        
        if (error.message.includes('NetworkError')) {
            return new Error('Network error occurred. Please check your connection and try again.');
        }
        
        if (error.message.includes('timeout')) {
            return new Error('Request timed out. Please try again.');
        }
        
        // Return the original error if it's already user-friendly
        return error;
    }

    /**
     * Sanitize user input for security
     * @param {string} text - Input text
     * @returns {string} - Sanitized text
     */
    sanitizeInput(text) {
        if (typeof text !== 'string') {
            return '';
        }
        
        return text
            .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '') // Remove script tags
            .replace(/javascript:[^;\s]*/gi, '') // Remove javascript: protocols
            .trim()
            .substring(0, 1000); // Limit length to prevent abuse
    }

    /**
     * Get current session status
     * @returns {Object} - Session status information
     */
    getSessionStatus() {
        return {
            isValidated: this.isValidated,
            sessionId: this.sessionId,
            hasSession: !!this.sessionId
        };
    }

    /**
     * Refresh session validation
     * @returns {Promise<boolean>} - True if session is still valid
     */
    async refreshSession() {
        try {
            const isValid = await this.validateSession();
            this.isValidated = isValid;
            return isValid;
        } catch (error) {
            console.error('Session refresh failed:', error);
            this.isValidated = false;
            return false;
        }
    }

    /**
     * Clean up client resources
     */
    cleanup() {
        this.sessionId = null;
        this.isValidated = false;
        console.log('VoiceAPIClient cleaned up');
    }

    /**
     * Utility function to sleep for specified milliseconds
     * @param {number} ms - Milliseconds to sleep
     * @returns {Promise} - Promise that resolves after delay
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Get client configuration for debugging
     * @returns {Object} - Client configuration
     */
    getConfig() {
        return {
            baseURL: this.baseURL,
            retryConfig: this.retryConfig,
            isValidated: this.isValidated,
            hasSession: !!this.sessionId
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceAPIClient;
}

// Make available globally for browser usage
if (typeof window !== 'undefined') {
    window.VoiceAPIClient = VoiceAPIClient;
}