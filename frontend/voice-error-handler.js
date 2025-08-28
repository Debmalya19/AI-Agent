/**
 * Voice Error Handler Class
 * Comprehensive error handling and graceful degradation for voice features
 */

class VoiceErrorHandler {
    constructor(options = {}) {
        this.options = { ...this.getDefaultOptions(), ...options };
        
        // Error tracking
        this.errorHistory = [];
        this.retryAttempts = new Map();
        this.fallbackMode = false;
        
        // Network monitoring
        this.networkStatus = navigator.onLine;
        this.networkRetryCount = 0;
        this.maxNetworkRetries = 3;
        
        // Audio quality monitoring
        this.audioQualityIssues = 0;
        this.maxAudioQualityIssues = 3;
        
        // Event listeners
        this.listeners = new Map();
        
        this.initialize();
    }

    /**
     * Get default options
     * @returns {Object} Default options
     */
    getDefaultOptions() {
        return {
            enableRetry: true,
            maxRetryAttempts: 3,
            retryDelay: 2000,
            enableFallback: true,
            enableNetworkMonitoring: true,
            enableAudioQualityDetection: true,
            logErrors: true,
            showUserFriendlyMessages: true,
            debugMode: false
        };
    }

    /**
     * Initialize error handler
     */
    initialize() {
        this.setupNetworkMonitoring();
        this.setupErrorRecovery();
        this.log('Voice error handler initialized');
    }

    /**
     * Setup network monitoring
     */
    setupNetworkMonitoring() {
        if (!this.options.enableNetworkMonitoring) return;

        window.addEventListener('online', () => {
            this.networkStatus = true;
            this.networkRetryCount = 0;
            this.emit('network_restored');
            this.log('Network connection restored');
        });

        window.addEventListener('offline', () => {
            this.networkStatus = false;
            this.emit('network_lost');
            this.log('Network connection lost');
        });
    }

    /**
     * Setup error recovery mechanisms
     */
    setupErrorRecovery() {
        // Set up periodic cleanup of error history
        setInterval(() => {
            this.cleanupErrorHistory();
        }, 300000); // 5 minutes
    }

    /**
     * Handle voice-related errors with comprehensive recovery
     * @param {Object} error - Error object
     * @param {string} context - Context where error occurred
     * @returns {Object} Recovery action result
     */
    async handleError(error, context = 'unknown') {
        const errorInfo = this.analyzeError(error, context);
        this.logError(errorInfo);
        
        // Add to error history
        this.errorHistory.push({
            ...errorInfo,
            timestamp: Date.now()
        });

        // Determine recovery strategy
        const recoveryAction = await this.determineRecoveryAction(errorInfo);
        
        // Execute recovery
        const result = await this.executeRecovery(recoveryAction, errorInfo);
        
        // Emit error event with recovery info
        this.emit('error_handled', {
            error: errorInfo,
            recovery: recoveryAction,
            result: result
        });

        return result;
    }

    /**
     * Analyze error to determine type and severity
     * @param {Object} error - Error object
     * @param {string} context - Context where error occurred
     * @returns {Object} Analyzed error information
     */
    analyzeError(error, context) {
        const errorInfo = {
            type: this.categorizeError(error),
            severity: this.determineSeverity(error, context),
            message: this.extractErrorMessage(error),
            code: error.code || error.name || 'unknown',
            context: context,
            recoverable: this.isRecoverable(error),
            requiresFallback: this.requiresFallback(error),
            userMessage: this.generateUserMessage(error, context)
        };

        return errorInfo;
    }

    /**
     * Categorize error type
     * @param {Object} error - Error object
     * @returns {string} Error category
     */
    categorizeError(error) {
        const errorType = error.type || error.name || error.error || 'unknown';
        
        // Browser compatibility errors
        if (errorType.includes('not-allowed') || errorType.includes('permission')) {
            return 'permission';
        }
        
        // Network-related errors
        if (errorType.includes('network') || errorType.includes('connection') || 
            errorType.includes('timeout') || !navigator.onLine) {
            return 'network';
        }
        
        // Audio/microphone errors
        if (errorType.includes('audio-capture') || errorType.includes('microphone') ||
            errorType.includes('no-speech') || errorType.includes('audio')) {
            return 'audio';
        }
        
        // Speech recognition errors
        if (errorType.includes('speech') || errorType.includes('recognition') ||
            errorType.includes('language-not-supported')) {
            return 'speech_recognition';
        }
        
        // Speech synthesis errors
        if (errorType.includes('synthesis') || errorType.includes('voice') ||
            errorType.includes('utterance')) {
            return 'speech_synthesis';
        }
        
        // Browser support errors
        if (errorType.includes('not-supported') || errorType.includes('unavailable')) {
            return 'browser_support';
        }
        
        return 'unknown';
    }

    /**
     * Determine error severity
     * @param {Object} error - Error object
     * @param {string} context - Context where error occurred
     * @returns {string} Severity level
     */
    determineSeverity(error, context) {
        const errorType = this.categorizeError(error);
        
        // Critical errors that require immediate fallback
        if (errorType === 'browser_support' || errorType === 'permission') {
            return 'critical';
        }
        
        // High severity errors that may be recoverable
        if (errorType === 'network' || errorType === 'audio') {
            return 'high';
        }
        
        // Medium severity errors that are usually recoverable
        if (errorType === 'speech_recognition' || errorType === 'speech_synthesis') {
            return 'medium';
        }
        
        return 'low';
    }

    /**
     * Extract user-friendly error message
     * @param {Object} error - Error object
     * @returns {string} Error message
     */
    extractErrorMessage(error) {
        if (error.message) return error.message;
        if (error.error) return error.error;
        if (error.type) return error.type;
        return 'Unknown error occurred';
    }

    /**
     * Check if error is recoverable
     * @param {Object} error - Error object
     * @returns {boolean} Whether error is recoverable
     */
    isRecoverable(error) {
        const errorType = this.categorizeError(error);
        const nonRecoverableTypes = ['browser_support', 'permission'];
        return !nonRecoverableTypes.includes(errorType);
    }

    /**
     * Check if error requires fallback mode
     * @param {Object} error - Error object
     * @returns {boolean} Whether fallback is required
     */
    requiresFallback(error) {
        const errorType = this.categorizeError(error);
        const fallbackTypes = ['browser_support', 'permission', 'audio'];
        return fallbackTypes.includes(errorType);
    }

    /**
     * Generate user-friendly error message
     * @param {Object} error - Error object
     * @param {string} context - Context where error occurred
     * @returns {string} User-friendly message
     */
    generateUserMessage(error, context) {
        const errorType = this.categorizeError(error);
        
        const messages = {
            permission: 'Microphone access is required for voice input. Please check your browser permissions and try again.',
            network: 'Network connection issue detected. Please check your internet connection and try again.',
            audio: 'Audio input issue detected. Please check your microphone and try again.',
            speech_recognition: 'Voice recognition failed. Please speak clearly and try again, or use text input.',
            speech_synthesis: 'Audio playback failed. The response will be displayed as text instead.',
            browser_support: 'Voice features are not supported in your browser. Please use text input instead.',
            unknown: 'An unexpected error occurred. Please try again or use text input.'
        };

        return messages[errorType] || messages.unknown;
    }

    /**
     * Determine recovery action based on error analysis
     * @param {Object} errorInfo - Analyzed error information
     * @returns {Object} Recovery action plan
     */
    async determineRecoveryAction(errorInfo) {
        const { type, severity, recoverable, requiresFallback } = errorInfo;
        
        // Check retry attempts
        const retryKey = `${type}_${errorInfo.context}`;
        const currentRetries = this.retryAttempts.get(retryKey) || 0;
        
        const action = {
            type: 'none',
            delay: 0,
            fallback: false,
            userNotification: true,
            retryable: false
        };

        // Critical errors - immediate fallback
        if (severity === 'critical' || requiresFallback) {
            action.type = 'fallback';
            action.fallback = true;
            action.userNotification = true;
            return action;
        }

        // Network errors - retry with exponential backoff
        if (type === 'network' && this.networkRetryCount < this.maxNetworkRetries) {
            action.type = 'retry';
            action.delay = Math.pow(2, this.networkRetryCount) * 1000; // Exponential backoff
            action.retryable = true;
            this.networkRetryCount++;
            return action;
        }

        // Audio quality issues - retry with user guidance
        if (type === 'audio' && currentRetries < this.options.maxRetryAttempts) {
            action.type = 'retry_with_guidance';
            action.delay = this.options.retryDelay;
            action.retryable = true;
            action.guidance = 'Please ensure your microphone is working and speak clearly.';
            this.retryAttempts.set(retryKey, currentRetries + 1);
            return action;
        }

        // Speech recognition errors - retry with different settings
        if (type === 'speech_recognition' && currentRetries < this.options.maxRetryAttempts) {
            action.type = 'retry_with_adjustment';
            action.delay = this.options.retryDelay;
            action.retryable = true;
            action.adjustment = 'sensitivity';
            this.retryAttempts.set(retryKey, currentRetries + 1);
            return action;
        }

        // If all retries exhausted, fallback
        if (recoverable && this.options.enableFallback) {
            action.type = 'fallback';
            action.fallback = true;
            action.userNotification = true;
        }

        return action;
    }

    /**
     * Execute recovery action
     * @param {Object} recoveryAction - Recovery action plan
     * @param {Object} errorInfo - Error information
     * @returns {Object} Recovery result
     */
    async executeRecovery(recoveryAction, errorInfo) {
        const result = {
            success: false,
            action: recoveryAction.type,
            message: '',
            fallbackActivated: false
        };

        try {
            switch (recoveryAction.type) {
                case 'retry':
                    result = await this.executeRetry(recoveryAction, errorInfo);
                    break;
                    
                case 'retry_with_guidance':
                    result = await this.executeRetryWithGuidance(recoveryAction, errorInfo);
                    break;
                    
                case 'retry_with_adjustment':
                    result = await this.executeRetryWithAdjustment(recoveryAction, errorInfo);
                    break;
                    
                case 'fallback':
                    result = await this.executeFallback(recoveryAction, errorInfo);
                    break;
                    
                default:
                    result.message = errorInfo.userMessage;
                    break;
            }
        } catch (recoveryError) {
            this.log('Recovery execution failed:', recoveryError);
            result.message = 'Recovery failed. Please use text input.';
            result.fallbackActivated = true;
        }

        return result;
    }

    /**
     * Execute simple retry
     * @param {Object} recoveryAction - Recovery action
     * @param {Object} errorInfo - Error information
     * @returns {Object} Recovery result
     */
    async executeRetry(recoveryAction, errorInfo) {
        if (recoveryAction.delay > 0) {
            await this.delay(recoveryAction.delay);
        }

        return {
            success: true,
            action: 'retry',
            message: 'Retrying voice operation...',
            fallbackActivated: false
        };
    }

    /**
     * Execute retry with user guidance
     * @param {Object} recoveryAction - Recovery action
     * @param {Object} errorInfo - Error information
     * @returns {Object} Recovery result
     */
    async executeRetryWithGuidance(recoveryAction, errorInfo) {
        if (recoveryAction.delay > 0) {
            await this.delay(recoveryAction.delay);
        }

        return {
            success: true,
            action: 'retry_with_guidance',
            message: recoveryAction.guidance || 'Please try again with better audio conditions.',
            fallbackActivated: false
        };
    }

    /**
     * Execute retry with settings adjustment
     * @param {Object} recoveryAction - Recovery action
     * @param {Object} errorInfo - Error information
     * @returns {Object} Recovery result
     */
    async executeRetryWithAdjustment(recoveryAction, errorInfo) {
        if (recoveryAction.delay > 0) {
            await this.delay(recoveryAction.delay);
        }

        // Emit adjustment request
        this.emit('adjustment_needed', {
            type: recoveryAction.adjustment,
            context: errorInfo.context
        });

        return {
            success: true,
            action: 'retry_with_adjustment',
            message: 'Adjusting settings and retrying...',
            fallbackActivated: false
        };
    }

    /**
     * Execute fallback to text-only mode
     * @param {Object} recoveryAction - Recovery action
     * @param {Object} errorInfo - Error information
     * @returns {Object} Recovery result
     */
    async executeFallback(recoveryAction, errorInfo) {
        this.fallbackMode = true;
        
        this.emit('fallback_activated', {
            reason: errorInfo.type,
            message: errorInfo.userMessage
        });

        return {
            success: true,
            action: 'fallback',
            message: errorInfo.userMessage,
            fallbackActivated: true
        };
    }

    /**
     * Check browser compatibility and return detailed report
     * @returns {Object} Compatibility report
     */
    checkBrowserCompatibility() {
        const compatibility = {
            speechRecognition: {
                supported: 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window,
                implementation: null,
                issues: []
            },
            speechSynthesis: {
                supported: 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window,
                issues: []
            },
            mediaDevices: {
                supported: navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function',
                issues: []
            },
            overall: {
                compatible: false,
                fallbackRequired: false,
                recommendations: []
            }
        };

        // Check speech recognition implementation
        if (compatibility.speechRecognition.supported) {
            if ('SpeechRecognition' in window) {
                compatibility.speechRecognition.implementation = 'standard';
            } else if ('webkitSpeechRecognition' in window) {
                compatibility.speechRecognition.implementation = 'webkit';
            }
        } else {
            compatibility.speechRecognition.issues.push('Speech recognition not supported');
        }

        // Check for known browser issues
        const userAgent = navigator.userAgent.toLowerCase();
        
        if (userAgent.includes('firefox')) {
            compatibility.speechRecognition.issues.push('Firefox has limited speech recognition support');
            compatibility.overall.recommendations.push('Consider using Chrome or Edge for better voice support');
        }
        
        if (userAgent.includes('safari') && !userAgent.includes('chrome')) {
            compatibility.speechSynthesis.issues.push('Safari may have speech synthesis limitations');
            compatibility.overall.recommendations.push('Some voice features may be limited in Safari');
        }

        // Determine overall compatibility
        compatibility.overall.compatible = 
            compatibility.speechRecognition.supported && 
            compatibility.speechSynthesis.supported && 
            compatibility.mediaDevices.supported;

        compatibility.overall.fallbackRequired = !compatibility.overall.compatible;

        if (!compatibility.overall.compatible) {
            compatibility.overall.recommendations.push('Voice features will be disabled, text-only mode will be used');
        }

        return compatibility;
    }

    /**
     * Test microphone access with detailed error reporting
     * @returns {Object} Microphone test result
     */
    async testMicrophoneAccess() {
        const result = {
            hasAccess: false,
            error: null,
            errorType: null,
            userMessage: '',
            recoveryActions: []
        };

        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                result.error = 'MediaDevices API not supported';
                result.errorType = 'browser_support';
                result.userMessage = 'Your browser does not support microphone access. Please use text input.';
                result.recoveryActions = ['Use text input instead'];
                return result;
            }

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Test successful - clean up
            stream.getTracks().forEach(track => track.stop());
            
            result.hasAccess = true;
            result.userMessage = 'Microphone access granted';
            
        } catch (error) {
            result.error = error.message;
            
            switch (error.name) {
                case 'NotAllowedError':
                    result.errorType = 'permission';
                    result.userMessage = 'Microphone access denied. Please allow microphone access in your browser settings.';
                    result.recoveryActions = [
                        'Click the microphone icon in your browser address bar',
                        'Select "Allow" for microphone access',
                        'Refresh the page and try again'
                    ];
                    break;
                    
                case 'NotFoundError':
                    result.errorType = 'hardware';
                    result.userMessage = 'No microphone found. Please connect a microphone and try again.';
                    result.recoveryActions = [
                        'Connect a microphone to your device',
                        'Check your audio device settings',
                        'Use text input instead'
                    ];
                    break;
                    
                case 'NotReadableError':
                    result.errorType = 'hardware';
                    result.userMessage = 'Microphone is being used by another application.';
                    result.recoveryActions = [
                        'Close other applications using the microphone',
                        'Restart your browser',
                        'Use text input instead'
                    ];
                    break;
                    
                default:
                    result.errorType = 'unknown';
                    result.userMessage = 'Unable to access microphone. Please check your settings and try again.';
                    result.recoveryActions = [
                        'Check your browser permissions',
                        'Ensure your microphone is working',
                        'Use text input instead'
                    ];
                    break;
            }
        }

        return result;
    }

    /**
     * Detect audio quality issues
     * @param {Object} recognitionEvent - Speech recognition event
     * @returns {Object} Audio quality assessment
     */
    detectAudioQuality(recognitionEvent) {
        const assessment = {
            quality: 'good',
            confidence: 1.0,
            issues: [],
            recommendations: []
        };

        if (!recognitionEvent || !recognitionEvent.results) {
            assessment.quality = 'poor';
            assessment.confidence = 0;
            assessment.issues.push('No speech detected');
            assessment.recommendations.push('Speak louder and clearer');
            return assessment;
        }

        // Check confidence scores
        const results = recognitionEvent.results;
        let totalConfidence = 0;
        let resultCount = 0;

        for (let i = 0; i < results.length; i++) {
            if (results[i][0]) {
                totalConfidence += results[i][0].confidence || 0;
                resultCount++;
            }
        }

        if (resultCount > 0) {
            assessment.confidence = totalConfidence / resultCount;
        }

        // Assess quality based on confidence
        if (assessment.confidence < 0.3) {
            assessment.quality = 'poor';
            assessment.issues.push('Very low confidence in speech recognition');
            assessment.recommendations.push('Speak more clearly');
            assessment.recommendations.push('Reduce background noise');
            assessment.recommendations.push('Move closer to the microphone');
        } else if (assessment.confidence < 0.6) {
            assessment.quality = 'fair';
            assessment.issues.push('Low confidence in speech recognition');
            assessment.recommendations.push('Speak more clearly');
        }

        // Track quality issues
        if (assessment.quality !== 'good') {
            this.audioQualityIssues++;
            
            if (this.audioQualityIssues >= this.maxAudioQualityIssues) {
                assessment.recommendations.push('Consider using text input for better accuracy');
            }
        } else {
            // Reset counter on good quality
            this.audioQualityIssues = Math.max(0, this.audioQualityIssues - 1);
        }

        return assessment;
    }

    /**
     * Monitor network connectivity for voice API calls
     * @returns {Object} Network status
     */
    getNetworkStatus() {
        return {
            online: navigator.onLine,
            retryCount: this.networkRetryCount,
            maxRetries: this.maxNetworkRetries,
            canRetry: this.networkRetryCount < this.maxNetworkRetries
        };
    }

    /**
     * Log error for debugging and analytics
     * @param {Object} errorInfo - Error information
     */
    logError(errorInfo) {
        if (!this.options.logErrors) return;

        const logEntry = {
            timestamp: new Date().toISOString(),
            ...errorInfo
        };

        if (this.options.debugMode) {
            console.error('Voice Error:', logEntry);
        }

        // Send to analytics if available
        if (window.voiceAnalytics) {
            window.voiceAnalytics.logError(logEntry);
        }
    }

    /**
     * Clean up old error history
     */
    cleanupErrorHistory() {
        const fiveMinutesAgo = Date.now() - 300000;
        this.errorHistory = this.errorHistory.filter(error => error.timestamp > fiveMinutesAgo);
        
        // Clean up retry attempts
        this.retryAttempts.clear();
    }

    /**
     * Get error statistics
     * @returns {Object} Error statistics
     */
    getErrorStatistics() {
        const now = Date.now();
        const oneHourAgo = now - 3600000;
        
        const recentErrors = this.errorHistory.filter(error => error.timestamp > oneHourAgo);
        
        const stats = {
            totalErrors: this.errorHistory.length,
            recentErrors: recentErrors.length,
            errorsByType: {},
            errorsBySeverity: {},
            fallbackMode: this.fallbackMode,
            networkRetryCount: this.networkRetryCount,
            audioQualityIssues: this.audioQualityIssues
        };

        // Count errors by type and severity
        recentErrors.forEach(error => {
            stats.errorsByType[error.type] = (stats.errorsByType[error.type] || 0) + 1;
            stats.errorsBySeverity[error.severity] = (stats.errorsBySeverity[error.severity] || 0) + 1;
        });

        return stats;
    }

    /**
     * Reset error handler state
     */
    reset() {
        this.errorHistory = [];
        this.retryAttempts.clear();
        this.fallbackMode = false;
        this.networkRetryCount = 0;
        this.audioQualityIssues = 0;
        this.log('Voice error handler reset');
    }

    /**
     * Utility function for delays
     * @param {number} ms - Milliseconds to delay
     * @returns {Promise} Promise that resolves after delay
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Add event listener
     * @param {string} event - Event name
     * @param {Function} listener - Event listener function
     */
    addEventListener(event, listener) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(listener);
    }

    /**
     * Remove event listener
     * @param {string} event - Event name
     * @param {Function} listener - Event listener function
     */
    removeEventListener(event, listener) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).delete(listener);
        }
    }

    /**
     * Emit event to listeners
     * @param {string} event - Event name
     * @param {*} data - Event data
     */
    emit(event, data = null) {
        if (this.options.debugMode) {
            console.log(`VoiceErrorHandler event: ${event}`, data);
        }

        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(listener => {
                try {
                    listener(data);
                } catch (error) {
                    console.error(`Error in voice error handler listener for ${event}:`, error);
                }
            });
        }
    }

    /**
     * Log debug information
     * @param {...any} args - Arguments to log
     */
    log(...args) {
        if (this.options.debugMode) {
            console.log('[VoiceErrorHandler]', ...args);
        }
    }

    /**
     * Destroy error handler and clean up
     */
    destroy() {
        this.listeners.clear();
        this.errorHistory = [];
        this.retryAttempts.clear();
        
        // Remove network event listeners
        window.removeEventListener('online', this.handleNetworkOnline);
        window.removeEventListener('offline', this.handleNetworkOffline);
        
        this.log('Voice error handler destroyed');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceErrorHandler;
} else {
    window.VoiceErrorHandler = VoiceErrorHandler;
}