/**
 * Voice Analytics Client
 * Client-side performance tracking and analytics for voice features
 * 
 * This module provides:
 * - Client-side performance tracking for STT/TTS processing times
 * - Voice usage analytics collection (without storing audio content)
 * - Voice error logging and reporting system
 * - Voice feature adoption metrics and user engagement tracking
 * - Integration with existing memory layer and chat analytics
 */

class VoiceAnalytics {
    constructor(options = {}) {
        this.options = {
            enablePerformanceTracking: true,
            enableErrorTracking: true,
            enableUsageTracking: true,
            batchSize: 10,
            flushInterval: 30000, // 30 seconds
            maxRetries: 3,
            debugMode: false,
            ...options
        };
        
        // Analytics data buffers
        this.performanceBuffer = [];
        this.errorBuffer = [];
        this.usageBuffer = [];
        
        // Performance tracking
        this.performanceTimers = new Map();
        this.sessionMetrics = {
            sessionId: this.generateSessionId(),
            startTime: Date.now(),
            voiceInteractions: 0,
            sttUsage: 0,
            ttsUsage: 0,
            errors: 0,
            totalProcessingTime: 0
        };
        
        // Feature adoption tracking
        this.featureUsage = {
            voiceInput: false,
            voiceOutput: false,
            autoPlay: false,
            settingsChanged: false
        };
        
        // Error tracking
        this.errorPatterns = new Map();
        this.consecutiveErrors = 0;
        this.lastErrorTime = null;
        
        // Initialize
        this.initialize();
    }
    
    /**
     * Initialize the analytics system
     */
    initialize() {
        // Set up periodic flushing
        this.flushInterval = setInterval(() => {
            this.flushAnalytics();
        }, this.options.flushInterval);
        
        // Set up page unload handler to flush remaining data
        window.addEventListener('beforeunload', () => {
            this.flushAnalytics(true); // Synchronous flush on unload
        });
        
        // Set up visibility change handler
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.flushAnalytics();
            }
        });
        
        if (this.options.debugMode) {
            console.log('Voice Analytics initialized', this.sessionMetrics);
        }
    }
    
    /**
     * Start performance tracking for a voice operation
     * @param {string} operationType - Type of operation (stt_start, tts_start, etc.)
     * @param {Object} context - Additional context information
     * @returns {string} Timer ID for stopping the timer
     */
    startPerformanceTimer(operationType, context = {}) {
        if (!this.options.enablePerformanceTracking) return null;
        
        const timerId = `${operationType}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        this.performanceTimers.set(timerId, {
            operationType,
            startTime: performance.now(),
            startTimestamp: Date.now(),
            context: this.sanitizeContext(context)
        });
        
        if (this.options.debugMode) {
            console.log(`Performance timer started: ${timerId}`, operationType);
        }
        
        return timerId;
    }
    
    /**
     * Stop performance tracking and record metrics
     * @param {string} timerId - Timer ID from startPerformanceTimer
     * @param {Object} result - Operation result data
     */
    stopPerformanceTimer(timerId, result = {}) {
        if (!timerId || !this.performanceTimers.has(timerId)) return;
        
        const timer = this.performanceTimers.get(timerId);
        const endTime = performance.now();
        const duration = endTime - timer.startTime;
        
        // Record performance metrics
        const performanceData = {
            operationType: timer.operationType,
            duration: Math.round(duration),
            startTime: timer.startTimestamp,
            endTime: Date.now(),
            success: !result.error,
            textLength: result.textLength || null,
            accuracyScore: result.accuracyScore || null,
            context: {
                ...timer.context,
                ...this.sanitizeContext(result.context || {})
            }
        };
        
        this.recordPerformanceMetric(performanceData);
        this.performanceTimers.delete(timerId);
        
        // Update session metrics
        this.updateSessionMetrics(timer.operationType, duration, !result.error);
        
        if (this.options.debugMode) {
            console.log(`Performance timer stopped: ${timerId}`, performanceData);
        }
    }
    
    /**
     * Record a performance metric
     * @param {Object} performanceData - Performance data to record
     */
    recordPerformanceMetric(performanceData) {
        if (!this.options.enablePerformanceTracking) return;
        
        this.performanceBuffer.push({
            type: 'performance',
            timestamp: Date.now(),
            sessionId: this.sessionMetrics.sessionId,
            ...performanceData
        });
        
        this.checkBufferSize();
    }
    
    /**
     * Record a voice error for analytics
     * @param {string} errorType - Type of error (network, permission, audio, etc.)
     * @param {string} errorMessage - Error message
     * @param {Object} context - Error context
     * @param {string} recoveryAction - Action taken to recover
     */
    recordVoiceError(errorType, errorMessage, context = {}, recoveryAction = null) {
        if (!this.options.enableErrorTracking) return;
        
        const errorData = {
            type: 'error',
            timestamp: Date.now(),
            sessionId: this.sessionMetrics.sessionId,
            errorType,
            errorMessage: this.sanitizeErrorMessage(errorMessage),
            context: this.sanitizeContext(context),
            recoveryAction,
            consecutiveErrors: this.consecutiveErrors + 1,
            timeSinceLastError: this.lastErrorTime ? Date.now() - this.lastErrorTime : null
        };
        
        this.errorBuffer.push(errorData);
        
        // Update error tracking
        this.consecutiveErrors++;
        this.lastErrorTime = Date.now();
        this.sessionMetrics.errors++;
        
        // Track error patterns
        this.trackErrorPattern(errorType, errorMessage);
        
        this.checkBufferSize();
        
        if (this.options.debugMode) {
            console.log('Voice error recorded:', errorData);
        }
    }
    
    /**
     * Record feature adoption/usage
     * @param {string} featureType - Type of feature (voice_input, voice_output, auto_play, etc.)
     * @param {boolean} enabled - Whether feature was enabled or disabled
     * @param {Object} settingsData - Related settings data
     */
    recordFeatureAdoption(featureType, enabled, settingsData = {}) {
        if (!this.options.enableUsageTracking) return;
        
        const adoptionData = {
            type: 'feature_adoption',
            timestamp: Date.now(),
            sessionId: this.sessionMetrics.sessionId,
            featureType,
            enabled,
            settings: this.sanitizeContext(settingsData),
            sessionDuration: Date.now() - this.sessionMetrics.startTime
        };
        
        this.usageBuffer.push(adoptionData);
        
        // Update feature usage tracking
        if (this.featureUsage.hasOwnProperty(featureType)) {
            this.featureUsage[featureType] = enabled;
        }
        
        this.checkBufferSize();
        
        if (this.options.debugMode) {
            console.log('Feature adoption recorded:', adoptionData);
        }
    }
    
    /**
     * Record voice usage in chat context
     * @param {string} chatSessionId - Chat session ID
     * @param {Object} voiceMetrics - Voice metrics for the chat interaction
     */
    recordVoiceInChat(chatSessionId, voiceMetrics = {}) {
        if (!this.options.enableUsageTracking) return;
        
        const chatVoiceData = {
            type: 'voice_in_chat',
            timestamp: Date.now(),
            sessionId: this.sessionMetrics.sessionId,
            chatSessionId,
            voiceMetrics: this.sanitizeContext(voiceMetrics),
            totalVoiceInteractions: this.sessionMetrics.voiceInteractions
        };
        
        this.usageBuffer.push(chatVoiceData);
        this.checkBufferSize();
        
        if (this.options.debugMode) {
            console.log('Voice in chat recorded:', chatVoiceData);
        }
    }
    
    /**
     * Get current session analytics summary
     * @returns {Object} Session analytics summary
     */
    getSessionSummary() {
        const now = Date.now();
        const sessionDuration = now - this.sessionMetrics.startTime;
        
        return {
            sessionId: this.sessionMetrics.sessionId,
            sessionDuration,
            voiceInteractions: this.sessionMetrics.voiceInteractions,
            sttUsage: this.sessionMetrics.sttUsage,
            ttsUsage: this.sessionMetrics.ttsUsage,
            errors: this.sessionMetrics.errors,
            averageProcessingTime: this.sessionMetrics.voiceInteractions > 0 
                ? this.sessionMetrics.totalProcessingTime / this.sessionMetrics.voiceInteractions 
                : 0,
            errorRate: this.sessionMetrics.voiceInteractions > 0 
                ? this.sessionMetrics.errors / this.sessionMetrics.voiceInteractions 
                : 0,
            featureUsage: { ...this.featureUsage },
            consecutiveErrors: this.consecutiveErrors,
            bufferedEvents: this.performanceBuffer.length + this.errorBuffer.length + this.usageBuffer.length
        };
    }
    
    /**
     * Get error patterns analysis
     * @returns {Object} Error patterns summary
     */
    getErrorPatterns() {
        const patterns = {};
        
        for (const [pattern, data] of this.errorPatterns.entries()) {
            patterns[pattern] = {
                count: data.count,
                lastOccurrence: data.lastOccurrence,
                contexts: Array.from(data.contexts).slice(0, 5) // Top 5 contexts
            };
        }
        
        return patterns;
    }
    
    /**
     * Flush analytics data to backend
     * @param {boolean} synchronous - Whether to flush synchronously
     */
    async flushAnalytics(synchronous = false) {
        const allData = [
            ...this.performanceBuffer,
            ...this.errorBuffer,
            ...this.usageBuffer
        ];
        
        if (allData.length === 0) return;
        
        // Clear buffers
        this.performanceBuffer = [];
        this.errorBuffer = [];
        this.usageBuffer = [];
        
        const payload = {
            sessionSummary: this.getSessionSummary(),
            analyticsData: allData,
            timestamp: Date.now()
        };
        
        try {
            if (synchronous) {
                // Use sendBeacon for synchronous sending on page unload
                if (navigator.sendBeacon) {
                    const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
                    navigator.sendBeacon('/voice/analytics/batch', blob);
                } else {
                    // Fallback to synchronous XHR
                    const xhr = new XMLHttpRequest();
                    xhr.open('POST', '/voice/analytics/batch', false);
                    xhr.setRequestHeader('Content-Type', 'application/json');
                    xhr.send(JSON.stringify(payload));
                }
            } else {
                // Asynchronous sending
                await this.sendAnalyticsData(payload);
            }
            
            if (this.options.debugMode) {
                console.log('Analytics data flushed:', payload);
            }
            
        } catch (error) {
            console.error('Failed to flush analytics data:', error);
            
            // Re-add data to buffers for retry (with limit)
            if (allData.length < 100) { // Prevent infinite growth
                this.performanceBuffer.unshift(...allData.filter(d => d.type === 'performance'));
                this.errorBuffer.unshift(...allData.filter(d => d.type === 'error'));
                this.usageBuffer.unshift(...allData.filter(d => d.type === 'feature_adoption' || d.type === 'voice_in_chat'));
            }
        }
    }
    
    /**
     * Send analytics data to backend with retry logic
     * @param {Object} payload - Analytics payload
     */
    async sendAnalyticsData(payload, retryCount = 0) {
        try {
            const response = await fetch('/voice/analytics/batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (this.options.debugMode) {
                console.log('Analytics data sent successfully:', result);
            }
            
        } catch (error) {
            if (retryCount < this.options.maxRetries) {
                // Exponential backoff retry
                const delay = Math.pow(2, retryCount) * 1000;
                setTimeout(() => {
                    this.sendAnalyticsData(payload, retryCount + 1);
                }, delay);
            } else {
                throw error;
            }
        }
    }
    
    /**
     * Update session metrics
     * @param {string} operationType - Type of operation
     * @param {number} duration - Operation duration
     * @param {boolean} success - Whether operation was successful
     */
    updateSessionMetrics(operationType, duration, success) {
        this.sessionMetrics.voiceInteractions++;
        this.sessionMetrics.totalProcessingTime += duration;
        
        if (operationType.includes('stt')) {
            this.sessionMetrics.sttUsage++;
        } else if (operationType.includes('tts')) {
            this.sessionMetrics.ttsUsage++;
        }
        
        if (success) {
            this.consecutiveErrors = 0;
        }
    }
    
    /**
     * Track error patterns for analysis
     * @param {string} errorType - Type of error
     * @param {string} errorMessage - Error message
     */
    trackErrorPattern(errorType, errorMessage) {
        const pattern = `${errorType}:${this.categorizeError(errorMessage)}`;
        
        if (!this.errorPatterns.has(pattern)) {
            this.errorPatterns.set(pattern, {
                count: 0,
                lastOccurrence: null,
                contexts: new Set()
            });
        }
        
        const patternData = this.errorPatterns.get(pattern);
        patternData.count++;
        patternData.lastOccurrence = Date.now();
        
        // Add context information
        const context = this.getBrowserContext();
        patternData.contexts.add(`${context.browser}_${context.platform}`);
    }
    
    /**
     * Categorize error message for pattern analysis
     * @param {string} errorMessage - Error message
     * @returns {string} Error category
     */
    categorizeError(errorMessage) {
        if (!errorMessage) return 'unknown';
        
        const message = errorMessage.toLowerCase();
        
        if (message.includes('network') || message.includes('connection')) return 'network';
        if (message.includes('permission') || message.includes('not-allowed')) return 'permission';
        if (message.includes('audio') || message.includes('microphone')) return 'audio';
        if (message.includes('synthesis') || message.includes('voice')) return 'synthesis';
        if (message.includes('recognition') || message.includes('speech')) return 'recognition';
        
        return 'other';
    }
    
    /**
     * Check buffer sizes and flush if needed
     */
    checkBufferSize() {
        const totalBufferSize = this.performanceBuffer.length + this.errorBuffer.length + this.usageBuffer.length;
        
        if (totalBufferSize >= this.options.batchSize) {
            this.flushAnalytics();
        }
    }
    
    /**
     * Sanitize context data to remove sensitive information
     * @param {Object} context - Context data
     * @returns {Object} Sanitized context
     */
    sanitizeContext(context) {
        const sensitive = ['audio_data', 'raw_audio', 'microphone_data', 'speech_data', 'token', 'password'];
        const sanitized = {};
        
        for (const [key, value] of Object.entries(context)) {
            if (!sensitive.some(s => key.toLowerCase().includes(s))) {
                if (typeof value === 'object' && value !== null) {
                    sanitized[key] = this.sanitizeContext(value);
                } else {
                    sanitized[key] = value;
                }
            }
        }
        
        return sanitized;
    }
    
    /**
     * Sanitize error message to remove sensitive information
     * @param {string} errorMessage - Error message
     * @returns {string} Sanitized error message
     */
    sanitizeErrorMessage(errorMessage) {
        if (!errorMessage) return '';
        
        // Remove potential sensitive data patterns
        return errorMessage
            .replace(/token[=:]\s*[^\s]+/gi, 'token=***')
            .replace(/key[=:]\s*[^\s]+/gi, 'key=***')
            .replace(/password[=:]\s*[^\s]+/gi, 'password=***')
            .replace(/\b\d{4,}\b/g, '****'); // Remove long numbers
    }
    
    /**
     * Get browser context information
     * @returns {Object} Browser context
     */
    getBrowserContext() {
        return {
            browser: this.getBrowserName(),
            platform: navigator.platform,
            userAgent: navigator.userAgent.substring(0, 100), // Truncated for privacy
            language: navigator.language,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine,
            screenResolution: `${screen.width}x${screen.height}`,
            timestamp: Date.now()
        };
    }
    
    /**
     * Get browser name from user agent
     * @returns {string} Browser name
     */
    getBrowserName() {
        const ua = navigator.userAgent;
        
        if (ua.includes('Chrome')) return 'Chrome';
        if (ua.includes('Firefox')) return 'Firefox';
        if (ua.includes('Safari')) return 'Safari';
        if (ua.includes('Edge')) return 'Edge';
        if (ua.includes('Opera')) return 'Opera';
        
        return 'Unknown';
    }
    
    /**
     * Generate unique session ID
     * @returns {string} Session ID
     */
    generateSessionId() {
        return `voice_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Reset session metrics (for new session)
     */
    resetSession() {
        this.sessionMetrics = {
            sessionId: this.generateSessionId(),
            startTime: Date.now(),
            voiceInteractions: 0,
            sttUsage: 0,
            ttsUsage: 0,
            errors: 0,
            totalProcessingTime: 0
        };
        
        this.consecutiveErrors = 0;
        this.lastErrorTime = null;
        this.errorPatterns.clear();
        
        if (this.options.debugMode) {
            console.log('Voice analytics session reset:', this.sessionMetrics);
        }
    }
    
    /**
     * Destroy the analytics instance
     */
    destroy() {
        // Flush remaining data
        this.flushAnalytics(true);
        
        // Clear intervals
        if (this.flushInterval) {
            clearInterval(this.flushInterval);
        }
        
        // Clear buffers
        this.performanceBuffer = [];
        this.errorBuffer = [];
        this.usageBuffer = [];
        
        // Clear timers
        this.performanceTimers.clear();
        
        if (this.options.debugMode) {
            console.log('Voice analytics destroyed');
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceAnalytics;
} else {
    window.VoiceAnalytics = VoiceAnalytics;
}