/**
 * Voice Controller Class
 * Main controller for voice input/output using Web Speech API
 */

class VoiceController {
    constructor(chatInterface, options = {}) {
        this.chatInterface = chatInterface;
        this.options = { ...this.getDefaultOptions(), ...options };
        
        // Initialize components
        this.capabilities = new VoiceCapabilities();
        this.settings = new VoiceSettings(options.storageKey);
        this.errorHandler = new VoiceErrorHandler({
            enableRetry: this.options.enableErrorRecovery,
            debugMode: this.options.debugMode
        });
        
        // Initialize analytics
        this.analytics = new VoiceAnalytics({
            enablePerformanceTracking: true,
            enableErrorTracking: true,
            enableUsageTracking: true,
            debugMode: this.options.debugMode
        });
        
        // State management
        this.isRecording = false;
        this.isSpeaking = false;
        this.currentRecognition = null;
        this.currentUtterance = null;
        this.speechQueue = [];
        this.fallbackMode = false;
        
        // Error tracking
        this.consecutiveErrors = 0;
        this.maxConsecutiveErrors = 3;
        
        // Performance tracking
        this.currentTimers = new Map();
        
        // Event listeners
        this.listeners = new Map();
        
        // Initialize if capabilities allow
        this.initialize();
    }

    /**
     * Get default options
     * @returns {Object} Default options
     */
    getDefaultOptions() {
        return {
            storageKey: 'voice_settings',
            autoInitialize: true,
            enableErrorRecovery: true,
            debugMode: false
        };
    }

    /**
     * Initialize the voice controller
     */
    async initialize() {
        try {
            // Check browser compatibility first
            const compatibilityReport = this.errorHandler.checkBrowserCompatibility();
            
            if (!compatibilityReport.overall.compatible) {
                this.fallbackMode = true;
                this.emit('fallback_required', {
                    reason: 'browser_compatibility',
                    report: compatibilityReport
                });
                return;
            }

            // Check capabilities
            const report = this.capabilities.getCapabilityReport();
            if (this.options.debugMode) {
                console.log('Voice capabilities:', report);
            }

            // Test microphone access if voice input is supported
            if (this.capabilities.capabilities.voiceInputSupported) {
                const micTest = await this.errorHandler.testMicrophoneAccess();
                if (!micTest.hasAccess) {
                    this.emit('microphone_access_denied', micTest);
                    // Continue initialization but disable voice input
                    this.capabilities.capabilities.voiceInputSupported = false;
                }
            }

            // Set up speech recognition if supported
            if (this.capabilities.capabilities.voiceInputSupported) {
                this.setupSpeechRecognition();
            }

            // Set up speech synthesis if supported
            if (this.capabilities.capabilities.voiceOutputSupported) {
                await this.setupSpeechSynthesis();
            }

            // Set up error handler listeners
            this.setupErrorHandlerListeners();

            // Listen for settings changes
            this.settings.addListener((action, settings) => {
                this.onSettingsChange(action, settings);
            });

            this.emit('initialized', {
                capabilities: this.capabilities.capabilities,
                settings: this.settings.get(),
                fallbackMode: this.fallbackMode
            });

        } catch (error) {
            console.error('Voice controller initialization failed:', error);
            const recoveryResult = await this.errorHandler.handleError(error, 'initialization');
            
            if (recoveryResult.fallbackActivated) {
                this.fallbackMode = true;
            }
            
            this.emit('error', { 
                type: 'initialization', 
                error,
                recovery: recoveryResult
            });
        }
    }

    /**
     * Set up speech recognition
     */
    setupSpeechRecognition() {
        const { SpeechRecognition } = this.capabilities.getBrowserImplementation();
        
        if (!SpeechRecognition) {
            console.warn('Speech recognition not available');
            return;
        }

        // Create recognition instance
        this.recognition = new SpeechRecognition();
        
        // Configure recognition
        this.updateRecognitionSettings();
        
        // Set up event handlers
        this.recognition.onstart = () => {
            this.isRecording = true;
            this.emit('recording_started');
        };

        this.recognition.onresult = (event) => {
            this.handleRecognitionResult(event);
        };

        this.recognition.onerror = (event) => {
            this.handleRecognitionError(event);
        };

        this.recognition.onend = () => {
            this.isRecording = false;
            this.currentRecognition = null;
            this.emit('recording_stopped');
        };

        this.recognition.onspeechstart = () => {
            this.emit('speech_detected');
        };

        this.recognition.onspeechend = () => {
            this.emit('speech_ended');
        };

        this.recognition.onnomatch = () => {
            this.emit('no_match');
        };
    }

    /**
     * Set up speech synthesis
     */
    async setupSpeechSynthesis() {
        if (!this.capabilities.capabilities.speechSynthesis) {
            console.warn('Speech synthesis not available');
            return;
        }

        // Load available voices
        this.availableVoices = await this.capabilities.getAvailableVoices();
        
        // Set up synthesis event handlers
        if ('speechSynthesis' in window) {
            speechSynthesis.addEventListener('voiceschanged', () => {
                this.capabilities.getAvailableVoices().then(voices => {
                    this.availableVoices = voices;
                    this.emit('voices_updated', voices);
                });
            });
        }
    }

    /**
     * Start voice recording
     * @returns {Promise<boolean>} True if recording started successfully
     */
    async startRecording() {
        // Check if in fallback mode
        if (this.fallbackMode) {
            this.emit('fallback_message', {
                message: 'Voice input is not available. Please use text input.'
            });
            return false;
        }

        if (!this.capabilities.capabilities.voiceInputSupported) {
            const error = { type: 'not_supported', message: 'Speech recognition not supported' };
            const recoveryResult = await this.errorHandler.handleError(error, 'start_recording');
            
            // Record analytics for unsupported feature
            this.analytics.recordVoiceError(
                'not_supported',
                'Speech recognition not supported',
                { capabilities: this.capabilities.capabilities }
            );
            
            this.emit('error', { 
                type: 'not_supported', 
                message: this.capabilities.getFallbackMessage('stt'),
                recovery: recoveryResult
            });
            return false;
        }

        if (this.isRecording) {
            console.warn('Already recording');
            return false;
        }

        try {
            // Start performance tracking
            const timerId = this.analytics.startPerformanceTimer('stt_start', {
                settings: this.settings.getSpeechRecognitionSettings(),
                capabilities: this.capabilities.capabilities
            });
            this.currentTimers.set('stt_start', timerId);

            // Test microphone access with enhanced error handling
            const micTest = await this.errorHandler.testMicrophoneAccess();
            if (!micTest.hasAccess) {
                // Record analytics for microphone access error
                this.analytics.recordVoiceError(
                    'permission',
                    'Microphone access denied',
                    { micTest }
                );
                
                this.emit('microphone_error', micTest);
                return false;
            }

            // Update recognition settings
            this.updateRecognitionSettings();
            
            // Start recognition
            this.currentRecognition = this.recognition;
            this.recognition.start();
            
            // Set timeout for max recording time
            const maxTime = this.settings.getValue('maxRecordingTime') || 30000;
            this.recordingTimeout = setTimeout(() => {
                this.stopRecording();
                this.emit('recording_timeout');
            }, maxTime);

            // Reset consecutive errors on successful start
            this.consecutiveErrors = 0;

            // Record feature adoption
            this.analytics.recordFeatureAdoption('voiceInput', true, {
                settings: this.settings.getSpeechRecognitionSettings()
            });

            return true;

        } catch (error) {
            console.error('Failed to start recording:', error);
            this.consecutiveErrors++;
            
            // Stop performance timer with error
            const timerId = this.currentTimers.get('stt_start');
            if (timerId) {
                this.analytics.stopPerformanceTimer(timerId, { 
                    error: true, 
                    context: { error: error.message } 
                });
                this.currentTimers.delete('stt_start');
            }
            
            // Record analytics for recording start error
            this.analytics.recordVoiceError(
                'audio',
                error.message || 'Failed to start recording',
                { consecutiveErrors: this.consecutiveErrors }
            );
            
            const recoveryResult = await this.errorHandler.handleError(error, 'start_recording');
            
            // Check if we should enter fallback mode
            if (this.consecutiveErrors >= this.maxConsecutiveErrors || recoveryResult.fallbackActivated) {
                this.fallbackMode = true;
                this.emit('fallback_activated', {
                    reason: 'consecutive_errors',
                    errorCount: this.consecutiveErrors
                });
            }
            
            this.emit('error', { 
                type: 'recording_start', 
                error,
                recovery: recoveryResult
            });
            return false;
        }
    }

    /**
     * Stop voice recording
     */
    stopRecording() {
        if (!this.isRecording || !this.currentRecognition) {
            return;
        }

        try {
            this.currentRecognition.stop();
            
            if (this.recordingTimeout) {
                clearTimeout(this.recordingTimeout);
                this.recordingTimeout = null;
            }
        } catch (error) {
            console.error('Failed to stop recording:', error);
            this.emit('error', { type: 'recording_stop', error });
        }
    }

    /**
     * Play text as speech
     * @param {string} text - Text to speak
     * @param {Object} options - Speech options
     * @returns {Promise<boolean>} True if speech started successfully
     */
    async playResponse(text, options = {}) {
        if (!this.capabilities.capabilities.voiceOutputSupported) {
            // Record analytics for unsupported TTS
            this.analytics.recordVoiceError(
                'not_supported',
                'Speech synthesis not supported',
                { capabilities: this.capabilities.capabilities }
            );
            
            this.emit('error', { 
                type: 'not_supported', 
                message: this.capabilities.getFallbackMessage('tts') 
            });
            return false;
        }

        if (!text || typeof text !== 'string') {
            console.warn('Invalid text for speech synthesis');
            return false;
        }

        try {
            // Start performance tracking for TTS
            const timerId = this.analytics.startPerformanceTimer('tts_start', {
                textLength: text.length,
                settings: this.settings.getSpeechSynthesisSettings(),
                options
            });
            this.currentTimers.set('tts_start', timerId);

            const utterance = this.createUtterance(text, options);
            
            // Add to queue or play immediately
            if (this.isSpeaking) {
                this.speechQueue.push(utterance);
                this.emit('speech_queued', { text, queueLength: this.speechQueue.length });
            } else {
                this.speakUtterance(utterance);
            }

            // Record feature adoption
            this.analytics.recordFeatureAdoption('voiceOutput', true, {
                textLength: text.length,
                settings: this.settings.getSpeechSynthesisSettings()
            });

            return true;

        } catch (error) {
            console.error('Failed to play response:', error);
            
            // Stop performance timer with error
            const timerId = this.currentTimers.get('tts_start');
            if (timerId) {
                this.analytics.stopPerformanceTimer(timerId, { 
                    error: true, 
                    context: { error: error.message } 
                });
                this.currentTimers.delete('tts_start');
            }
            
            // Record analytics for TTS error
            this.analytics.recordVoiceError(
                'synthesis',
                error.message || 'Failed to play response',
                { textLength: text.length }
            );
            
            this.emit('error', { type: 'speech_synthesis', error });
            return false;
        }
    }

    /**
     * Create speech synthesis utterance
     * @param {string} text - Text to speak
     * @param {Object} options - Speech options
     * @returns {SpeechSynthesisUtterance} Configured utterance
     */
    createUtterance(text, options = {}) {
        const utterance = new SpeechSynthesisUtterance(text);
        
        // Apply settings
        const synthSettings = this.settings.getSpeechSynthesisSettings();
        const finalOptions = { ...synthSettings, ...options };
        
        utterance.rate = finalOptions.rate;
        utterance.pitch = finalOptions.pitch;
        utterance.volume = finalOptions.volume;
        utterance.lang = finalOptions.lang;
        
        // Set voice if specified and available
        if (finalOptions.voice && this.availableVoices) {
            const voice = this.availableVoices.find(v => 
                v.name === finalOptions.voice || v.voiceURI === finalOptions.voice
            );
            if (voice) {
                utterance.voice = voice;
            }
        }

        // Set up event handlers
        utterance.onstart = () => {
            this.isSpeaking = true;
            this.currentUtterance = utterance;
            this.emit('speech_started', { text });
        };

        utterance.onend = () => {
            this.isSpeaking = false;
            this.currentUtterance = null;
            
            // Stop performance timer with success
            const timerId = this.currentTimers.get('tts_start');
            if (timerId) {
                this.analytics.stopPerformanceTimer(timerId, {
                    textLength: text.length,
                    context: { completed: true }
                });
                this.currentTimers.delete('tts_start');
            }
            
            this.emit('speech_ended', { text });
            
            // Play next in queue
            this.playNextInQueue();
        };

        utterance.onerror = (event) => {
            this.isSpeaking = false;
            this.currentUtterance = null;
            
            // Stop performance timer with error
            const timerId = this.currentTimers.get('tts_start');
            if (timerId) {
                this.analytics.stopPerformanceTimer(timerId, { 
                    error: true, 
                    context: { 
                        errorType: event.error,
                        textLength: text.length 
                    } 
                });
                this.currentTimers.delete('tts_start');
            }
            
            // Record analytics for TTS error
            this.analytics.recordVoiceError(
                'synthesis',
                `TTS error: ${event.error}`,
                { textLength: text.length, errorType: event.error }
            );
            
            this.emit('error', { type: 'speech_synthesis', error: event.error, text });
            
            // Continue with queue on error
            this.playNextInQueue();
        };

        utterance.onpause = () => {
            this.emit('speech_paused', { text });
        };

        utterance.onresume = () => {
            this.emit('speech_resumed', { text });
        };

        return utterance;
    }

    /**
     * Speak an utterance
     * @param {SpeechSynthesisUtterance} utterance - Utterance to speak
     */
    speakUtterance(utterance) {
        speechSynthesis.speak(utterance);
    }

    /**
     * Play next utterance in queue
     */
    playNextInQueue() {
        if (this.speechQueue.length > 0) {
            const nextUtterance = this.speechQueue.shift();
            this.speakUtterance(nextUtterance);
        }
    }

    /**
     * Pause speech playback
     */
    pausePlayback() {
        if (this.isSpeaking && speechSynthesis.speaking) {
            speechSynthesis.pause();
            this.emit('playback_paused');
        }
    }

    /**
     * Resume speech playback
     */
    resumePlayback() {
        if (speechSynthesis.paused) {
            speechSynthesis.resume();
            this.emit('playback_resumed');
        }
    }

    /**
     * Stop speech playback
     */
    stopPlayback() {
        if (this.isSpeaking || speechSynthesis.speaking) {
            speechSynthesis.cancel();
            this.speechQueue = [];
            this.isSpeaking = false;
            this.currentUtterance = null;
            this.emit('playback_stopped');
        }
    }

    /**
     * Update voice settings
     * @param {Object} settings - New settings
     * @returns {boolean} True if update was successful
     */
    updateSettings(settings) {
        const success = this.settings.update(settings);
        if (success) {
            this.updateRecognitionSettings();
            
            // Record settings change analytics
            this.analytics.recordFeatureAdoption('settingsChanged', true, settings);
        }
        return success;
    }

    /**
     * Update speech recognition settings
     */
    updateRecognitionSettings() {
        if (!this.recognition) return;

        const recSettings = this.settings.getSpeechRecognitionSettings();
        
        this.recognition.lang = recSettings.lang;
        this.recognition.continuous = recSettings.continuous;
        this.recognition.interimResults = recSettings.interimResults;
        this.recognition.maxAlternatives = recSettings.maxAlternatives;
    }

    /**
     * Handle recognition result
     * @param {SpeechRecognitionEvent} event - Recognition event
     */
    handleRecognitionResult(event) {
        let finalTranscript = '';
        let interimTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            const transcript = result[0].transcript;

            if (result.isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }

        // Emit interim results if enabled
        if (interimTranscript && this.settings.getValue('interimResults')) {
            this.emit('interim_result', { transcript: interimTranscript });
        }

        // Emit final result and record analytics
        if (finalTranscript) {
            const confidence = event.results[event.results.length - 1][0].confidence;
            
            // Stop performance timer with success
            const timerId = this.currentTimers.get('stt_start');
            if (timerId) {
                this.analytics.stopPerformanceTimer(timerId, {
                    textLength: finalTranscript.length,
                    accuracyScore: confidence,
                    context: { transcript: finalTranscript.substring(0, 50) } // First 50 chars for context
                });
                this.currentTimers.delete('stt_start');
            }
            
            this.emit('final_result', { 
                transcript: finalTranscript.trim(),
                confidence: confidence
            });
        }
    }

    /**
     * Handle recognition error
     * @param {SpeechRecognitionErrorEvent} event - Error event
     */
    async handleRecognitionError(event) {
        this.isRecording = false;
        this.currentRecognition = null;
        this.consecutiveErrors++;

        // Stop performance timer with error
        const timerId = this.currentTimers.get('stt_start');
        if (timerId) {
            this.analytics.stopPerformanceTimer(timerId, { 
                error: true, 
                context: { 
                    errorType: event.error,
                    errorMessage: event.message 
                } 
            });
            this.currentTimers.delete('stt_start');
        }

        const error = {
            type: 'speech_recognition',
            error: event.error,
            message: event.message || `Speech recognition error: ${event.error}`
        };

        // Record analytics for recognition error
        this.analytics.recordVoiceError(
            'recognition',
            error.message,
            {
                errorType: event.error,
                consecutiveErrors: this.consecutiveErrors,
                hasResults: event.results && event.results.length > 0
            },
            null // No recovery action yet
        );

        // Use error handler for comprehensive error handling
        const recoveryResult = await this.errorHandler.handleError(error, 'speech_recognition');
        
        // Check audio quality if we have recognition results
        if (event.results && event.results.length > 0) {
            const qualityAssessment = this.errorHandler.detectAudioQuality(event);
            this.emit('audio_quality_assessment', qualityAssessment);
        }

        // Handle specific error types with enhanced recovery
        switch (event.error) {
            case 'network':
                this.handleNetworkError(recoveryResult);
                break;
                
            case 'no-speech':
                this.handleNoSpeechError(recoveryResult);
                break;
                
            case 'audio-capture':
            case 'not-allowed':
                this.handlePermissionError(recoveryResult);
                break;
                
            default:
                this.handleGenericError(error, recoveryResult);
                break;
        }

        // Check if we should enter fallback mode
        if (this.consecutiveErrors >= this.maxConsecutiveErrors || recoveryResult.fallbackActivated) {
            this.fallbackMode = true;
            this.emit('fallback_activated', {
                reason: 'recognition_errors',
                errorCount: this.consecutiveErrors,
                lastError: event.error
            });
        }

        this.emit('error', { 
            type: 'speech_recognition', 
            error: event.error, 
            message: error.message,
            recovery: recoveryResult
        });
    }

    /**
     * Handle settings change
     * @param {string} action - Action that triggered the change
     * @param {Object} settings - New settings
     */
    onSettingsChange(action, settings) {
        this.updateRecognitionSettings();
        this.emit('settings_changed', { action, settings });
    }

    /**
     * Get current capabilities
     * @returns {Object} Current capabilities
     */
    getCapabilities() {
        return this.capabilities.capabilities;
    }

    /**
     * Get available voices
     * @returns {Array} Available voices
     */
    getAvailableVoices() {
        return this.availableVoices || [];
    }

    /**
     * Get current state
     * @returns {Object} Current state
     */
    getState() {
        return {
            isRecording: this.isRecording,
            isSpeaking: this.isSpeaking,
            queueLength: this.speechQueue.length,
            capabilities: this.capabilities.capabilities,
            settings: this.settings.get()
        };
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
            console.log(`VoiceController event: ${event}`, data);
        }

        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(listener => {
                try {
                    listener(data);
                } catch (error) {
                    console.error(`Error in voice controller listener for ${event}:`, error);
                }
            });
        }
    }

    /**
     * Setup error handler listeners
     */
    setupErrorHandlerListeners() {
        this.errorHandler.addEventListener('fallback_activated', (data) => {
            this.fallbackMode = true;
            this.emit('fallback_activated', data);
        });

        this.errorHandler.addEventListener('network_restored', () => {
            this.consecutiveErrors = 0;
            this.emit('network_restored');
        });

        this.errorHandler.addEventListener('adjustment_needed', (data) => {
            this.handleSettingsAdjustment(data);
        });
    }

    /**
     * Handle network errors with retry logic
     * @param {Object} recoveryResult - Recovery result from error handler
     */
    handleNetworkError(recoveryResult) {
        if (recoveryResult.action === 'retry') {
            this.emit('network_retry', {
                attempt: this.errorHandler.networkRetryCount,
                maxAttempts: this.errorHandler.maxNetworkRetries
            });
            
            // Attempt retry after delay
            setTimeout(() => {
                if (!this.isRecording && !this.fallbackMode) {
                    this.startRecording();
                }
            }, recoveryResult.delay || 2000);
        }
    }

    /**
     * Handle no speech detected errors
     * @param {Object} recoveryResult - Recovery result from error handler
     */
    handleNoSpeechError(recoveryResult) {
        this.emit('no_speech_guidance', {
            message: 'No speech detected. Please speak clearly into your microphone.',
            suggestions: [
                'Ensure your microphone is not muted',
                'Speak louder and more clearly',
                'Check your microphone settings'
            ]
        });
    }

    /**
     * Handle permission errors
     * @param {Object} recoveryResult - Recovery result from error handler
     */
    handlePermissionError(recoveryResult) {
        this.emit('permission_error', {
            message: recoveryResult.message,
            recoveryActions: [
                'Click the microphone icon in your browser address bar',
                'Select "Allow" for microphone access',
                'Refresh the page and try again',
                'Use text input as an alternative'
            ]
        });
    }

    /**
     * Handle generic errors
     * @param {Object} error - Original error
     * @param {Object} recoveryResult - Recovery result from error handler
     */
    handleGenericError(error, recoveryResult) {
        if (recoveryResult.action === 'retry_with_guidance') {
            this.emit('retry_with_guidance', {
                message: recoveryResult.message,
                guidance: recoveryResult.guidance
            });
        }
    }

    /**
     * Handle settings adjustment requests
     * @param {Object} adjustmentData - Adjustment data
     */
    handleSettingsAdjustment(adjustmentData) {
        if (adjustmentData.type === 'sensitivity') {
            // Adjust microphone sensitivity
            const currentSettings = this.settings.get();
            const newSensitivity = Math.min(1.0, currentSettings.microphoneSensitivity + 0.1);
            
            this.settings.update({ microphoneSensitivity: newSensitivity });
            this.emit('settings_adjusted', {
                type: 'sensitivity',
                oldValue: currentSettings.microphoneSensitivity,
                newValue: newSensitivity
            });
        }
    }

    /**
     * Check if voice features are available (not in fallback mode)
     * @returns {boolean} True if voice features are available
     */
    isVoiceAvailable() {
        return !this.fallbackMode && (
            this.capabilities.capabilities.voiceInputSupported || 
            this.capabilities.capabilities.voiceOutputSupported
        );
    }

    /**
     * Get comprehensive error statistics
     * @returns {Object} Error statistics
     */
    getErrorStatistics() {
        return {
            ...this.errorHandler.getErrorStatistics(),
            consecutiveErrors: this.consecutiveErrors,
            fallbackMode: this.fallbackMode
        };
    }

    /**
     * Reset error state and attempt to restore voice functionality
     * @returns {Promise<boolean>} True if voice functionality was restored
     */
    async resetErrorState() {
        this.consecutiveErrors = 0;
        this.errorHandler.reset();
        
        // Test if we can exit fallback mode
        if (this.fallbackMode) {
            const compatibilityReport = this.errorHandler.checkBrowserCompatibility();
            const micTest = await this.errorHandler.testMicrophoneAccess();
            
            if (compatibilityReport.overall.compatible && micTest.hasAccess) {
                this.fallbackMode = false;
                this.emit('voice_restored');
                return true;
            }
        }
        
        return false;
    }

    /**
     * Force fallback mode
     * @param {string} reason - Reason for forcing fallback
     */
    forceFallbackMode(reason = 'manual') {
        this.fallbackMode = true;
        this.stopRecording();
        this.stopPlayback();
        
        this.emit('fallback_activated', {
            reason: reason,
            forced: true
        });
    }

    /**
     * Destroy the voice controller and clean up resources
     */
    destroy() {
        // Stop any ongoing operations
        this.stopRecording();
        this.stopPlayback();

        // Clear timeouts
        if (this.recordingTimeout) {
            clearTimeout(this.recordingTimeout);
        }

        // Clear performance timers
        this.currentTimers.clear();

        // Clear listeners
        this.listeners.clear();

        // Remove settings listener
        this.settings.removeListener(this.onSettingsChange);

        // Destroy error handler
        if (this.errorHandler) {
            this.errorHandler.destroy();
        }

        // Destroy analytics
        if (this.analytics) {
            this.analytics.destroy();
        }

        this.emit('destroyed');
    }

    /**
     * Get analytics summary for integration with chat analytics
     * @returns {Object} Analytics summary
     */
    getAnalyticsSummary() {
        if (!this.analytics) return null;
        
        return this.analytics.getSessionSummary();
    }

    /**
     * Record voice usage in chat context
     * @param {string} chatSessionId - Chat session ID
     */
    recordVoiceInChat(chatSessionId) {
        if (!this.analytics) return;
        
        const voiceMetrics = this.getAnalyticsSummary();
        this.analytics.recordVoiceInChat(chatSessionId, voiceMetrics);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceController;
} else {
    window.VoiceController = VoiceController;
}