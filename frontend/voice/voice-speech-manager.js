// VoiceSpeechManager - Core speech recognition functionality
// Handles Web Speech API integration, error handling, and state management

class VoiceSpeechManager {
    constructor(onTranscript = null, onError = null, onStateChange = null) {
        // Callback functions
        this.onTranscript = onTranscript;
        this.onError = onError;
        this.onStateChange = onStateChange;
        
        // Speech recognition instance
        this.recognition = null;
        this.isRecognitionActive = false;
        this.isListening = false;
        
        // Speech synthesis instance
        this.synthesis = window.speechSynthesis;
        this.currentUtterance = null;
        this.isSpeaking = false;
        this.lastSpokenText = '';
        this.availableVoices = [];
        this.selectedVoice = null;
        
        // TTS Configuration
        this.ttsConfig = {
            rate: 1.0,
            pitch: 1.0,
            volume: 1.0,
            voice: null,
            autoPlay: true,
            fallbackToText: true
        };
        
        // Configuration
        this.config = {
            language: 'en-US',
            continuous: true,
            interimResults: true,
            maxAlternatives: 1,
            silenceTimeout: 3000,
            maxRecordingTime: 30000
        };
        
        // State management
        this.state = 'idle'; // idle, listening, processing, speaking, error
        this.lastTranscript = '';
        this.finalTranscript = '';
        
        // Timers
        this.silenceTimer = null;
        this.maxRecordingTimer = null;
        
        // Initialize
        this.initialize();
        
        // Load voices when available
        this.loadVoices();
    }
    
    initialize() {
        // Check browser compatibility
        const capabilities = this.getCapabilities();
        
        if (!capabilities.speechRecognition) {
            this.handleError('speech-recognition-unavailable', 'Speech recognition is not supported in this browser');
            return;
        }
        
        if (!capabilities.secureContext) {
            this.handleError('insecure-context', 'Speech recognition requires HTTPS or localhost');
            return;
        }
        
        // Initialize speech recognition
        this.initializeSpeechRecognition();
        
        console.log('VoiceSpeechManager initialized successfully');
    }
    
    initializeSpeechRecognition() {
        // Create speech recognition instance
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            this.handleError('speech-recognition-unavailable', 'Speech recognition API not available');
            return;
        }
        
        this.recognition = new SpeechRecognition();
        
        // Configure recognition
        this.recognition.continuous = this.config.continuous;
        this.recognition.interimResults = this.config.interimResults;
        this.recognition.lang = this.config.language;
        this.recognition.maxAlternatives = this.config.maxAlternatives;
        
        // Bind event handlers
        this.recognition.onstart = () => this.handleRecognitionStart();
        this.recognition.onresult = (event) => this.handleRecognitionResult(event);
        this.recognition.onerror = (event) => this.handleRecognitionError(event);
        this.recognition.onend = () => this.handleRecognitionEnd();
        this.recognition.onspeechstart = () => this.handleSpeechStart();
        this.recognition.onspeechend = () => this.handleSpeechEnd();
        this.recognition.onnomatch = () => this.handleNoMatch();
    }
    
    // Public methods
    
    async startListening() {
        if (this.isListening || this.state === 'listening') {
            console.warn('Already listening');
            return false;
        }
        
        if (!this.recognition) {
            this.handleError('recognition-not-initialized', 'Speech recognition not initialized');
            return false;
        }
        
        try {
            // Check microphone permissions
            const hasPermission = await this.checkMicrophonePermission();
            if (!hasPermission) {
                return false;
            }
            
            // Reset state
            this.lastTranscript = '';
            this.finalTranscript = '';
            this.clearTimers();
            
            // Start recognition
            this.recognition.start();
            this.isRecognitionActive = true;
            
            // Set maximum recording time
            this.maxRecordingTimer = setTimeout(() => {
                this.stopListening();
                this.handleError('max-recording-time', 'Maximum recording time reached');
            }, this.config.maxRecordingTime);
            
            return true;
            
        } catch (error) {
            this.handleError('start-listening-failed', `Failed to start listening: ${error.message}`);
            return false;
        }
    }
    
    stopListening() {
        if (!this.isListening && this.state !== 'listening') {
            console.warn('Not currently listening');
            return;
        }
        
        try {
            if (this.recognition && this.isRecognitionActive) {
                this.recognition.stop();
            }
            
            this.clearTimers();
            this.setState('idle');
            
        } catch (error) {
            console.error('Error stopping recognition:', error);
            this.handleError('stop-listening-failed', 'Failed to stop listening');
        }
    }
    
    speakText(text, options = {}) {
        if (!text || typeof text !== 'string') {
            console.warn('Invalid text provided for speech synthesis');
            return this.handleTTSFallback(text, 'Invalid text provided');
        }
        
        if (!this.synthesis) {
            return this.handleTTSFallback(text, 'Text-to-speech not available in this browser');
        }
        
        try {
            // Stop any current speech
            this.stopSpeaking();
            
            // Store the text for replay functionality
            this.lastSpokenText = text;
            
            // Create utterance
            this.currentUtterance = new SpeechSynthesisUtterance(text);
            
            // Configure utterance with enhanced options
            this.configureUtterance(this.currentUtterance, options);
            
            // Set event handlers with enhanced error handling
            this.setupUtteranceHandlers(this.currentUtterance, text);
            
            // Start speaking
            this.synthesis.speak(this.currentUtterance);
            
            return true;
            
        } catch (error) {
            console.error('Failed to speak text:', error);
            return this.handleTTSFallback(text, `Failed to speak text: ${error.message}`);
        }
    }
    
    configureUtterance(utterance, options = {}) {
        // Language configuration
        utterance.lang = options.lang || this.config.language;
        
        // Voice configuration - use selected voice or option voice
        if (options.voice) {
            utterance.voice = options.voice;
        } else if (this.selectedVoice) {
            utterance.voice = this.selectedVoice;
        } else if (this.ttsConfig.voice) {
            utterance.voice = this.ttsConfig.voice;
        }
        
        // Speech parameters with bounds checking
        utterance.rate = this.clampValue(options.rate || this.ttsConfig.rate, 0.1, 10);
        utterance.pitch = this.clampValue(options.pitch || this.ttsConfig.pitch, 0, 2);
        utterance.volume = this.clampValue(options.volume || this.ttsConfig.volume, 0, 1);
        
        console.log('TTS Configuration:', {
            lang: utterance.lang,
            voice: utterance.voice ? utterance.voice.name : 'default',
            rate: utterance.rate,
            pitch: utterance.pitch,
            volume: utterance.volume
        });
    }
    
    setupUtteranceHandlers(utterance, text) {
        utterance.onstart = () => {
            this.isSpeaking = true;
            this.setState('speaking');
            console.log('Started speaking:', text.substring(0, 50) + (text.length > 50 ? '...' : ''));
            
            // Notify state change for visual feedback
            if (this.onStateChange) {
                this.onStateChange('speaking', this.state, { text });
            }
        };
        
        utterance.onend = () => {
            this.isSpeaking = false;
            this.currentUtterance = null;
            this.setState('idle');
            console.log('Finished speaking');
            
            // Notify completion for automatic listening restart
            if (this.onStateChange) {
                this.onStateChange('speech-ended', 'speaking', { text });
            }
        };
        
        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event.error);
            this.isSpeaking = false;
            this.currentUtterance = null;
            
            // Handle different error types
            let errorMessage = 'Speech synthesis failed';
            let shouldFallback = true;
            
            switch (event.error) {
                case 'canceled':
                    errorMessage = 'Speech was interrupted';
                    shouldFallback = false;
                    break;
                case 'interrupted':
                    errorMessage = 'Speech was interrupted by another utterance';
                    shouldFallback = false;
                    break;
                case 'audio-busy':
                    errorMessage = 'Audio system is busy';
                    break;
                case 'audio-hardware':
                    errorMessage = 'Audio hardware error';
                    break;
                case 'network':
                    errorMessage = 'Network error during speech synthesis';
                    break;
                case 'synthesis-unavailable':
                    errorMessage = 'Speech synthesis service unavailable';
                    break;
                case 'synthesis-failed':
                    errorMessage = 'Speech synthesis failed';
                    break;
                case 'language-unavailable':
                    errorMessage = 'Selected language not available for speech synthesis';
                    break;
                case 'voice-unavailable':
                    errorMessage = 'Selected voice not available';
                    break;
                default:
                    errorMessage = `Speech synthesis error: ${event.error}`;
            }
            
            if (shouldFallback && this.ttsConfig.fallbackToText) {
                this.handleTTSFallback(text, errorMessage);
            } else {
                this.handleError('synthesis-failed', errorMessage);
            }
        };
        
        utterance.onpause = () => {
            console.log('Speech paused');
        };
        
        utterance.onresume = () => {
            console.log('Speech resumed');
        };
        
        utterance.onmark = (event) => {
            console.log('Speech mark:', event.name);
        };
    }
    
    handleTTSFallback(text, errorMessage) {
        console.warn('TTS fallback triggered:', errorMessage);
        
        // Notify about fallback with text display
        if (this.onStateChange) {
            this.onStateChange('tts-fallback', this.state, { 
                text, 
                error: errorMessage,
                fallbackText: text 
            });
        }
        
        // Set state to idle since we're not speaking
        this.setState('idle');
        
        return false;
    }
    
    stopSpeaking() {
        if (this.synthesis && this.synthesis.speaking) {
            this.synthesis.cancel();
        }
        
        if (this.currentUtterance) {
            this.currentUtterance = null;
        }
        
        this.isSpeaking = false;
        
        if (this.state === 'speaking') {
            this.setState('idle');
        }
        
        console.log('Speech stopped/interrupted');
    }
    
    pauseSpeaking() {
        if (this.synthesis && this.synthesis.speaking && !this.synthesis.paused) {
            this.synthesis.pause();
            console.log('Speech paused');
            return true;
        }
        return false;
    }
    
    resumeSpeaking() {
        if (this.synthesis && this.synthesis.paused) {
            this.synthesis.resume();
            console.log('Speech resumed');
            return true;
        }
        return false;
    }
    
    replayLastSpeech(options = {}) {
        if (!this.lastSpokenText) {
            console.warn('No previous speech to replay');
            return false;
        }
        
        console.log('Replaying last speech:', this.lastSpokenText.substring(0, 50) + '...');
        return this.speakText(this.lastSpokenText, options);
    }
    
    // State management
    
    setState(newState) {
        if (this.state !== newState) {
            const oldState = this.state;
            this.state = newState;
            
            console.log(`Speech manager state changed: ${oldState} -> ${newState}`);
            
            if (this.onStateChange) {
                this.onStateChange(newState, oldState);
            }
        }
    }
    
    // Voice Management
    
    loadVoices() {
        if (!this.synthesis) {
            console.warn('Speech synthesis not available for voice loading');
            return;
        }
        
        const loadVoicesImpl = () => {
            this.availableVoices = this.synthesis.getVoices();
            console.log(`Loaded ${this.availableVoices.length} voices`);
            
            // Set default voice if none selected
            if (!this.selectedVoice && this.availableVoices.length > 0) {
                // Try to find a good default voice for the current language
                const defaultVoice = this.findBestVoice(this.config.language);
                if (defaultVoice) {
                    this.selectedVoice = defaultVoice;
                    this.ttsConfig.voice = defaultVoice;
                    console.log('Selected default voice:', defaultVoice.name);
                }
            }
            
            // Notify about voice loading completion
            if (this.onStateChange) {
                this.onStateChange('voices-loaded', this.state, { 
                    voices: this.availableVoices,
                    selectedVoice: this.selectedVoice 
                });
            }
        };
        
        // Voices might not be loaded immediately
        if (this.availableVoices.length === 0) {
            // Try loading immediately
            loadVoicesImpl();
            
            // Also listen for voiceschanged event
            if (this.synthesis.onvoiceschanged !== undefined) {
                this.synthesis.onvoiceschanged = loadVoicesImpl;
            }
            
            // Fallback: try again after a short delay
            setTimeout(loadVoicesImpl, 100);
        }
    }
    
    findBestVoice(language) {
        if (!this.availableVoices.length) return null;
        
        const langCode = language.split('-')[0]; // e.g., 'en' from 'en-US'
        
        // First, try to find exact language match
        let voice = this.availableVoices.find(v => v.lang === language);
        
        // If not found, try language code match
        if (!voice) {
            voice = this.availableVoices.find(v => v.lang.startsWith(langCode));
        }
        
        // If still not found, try to find any English voice as fallback
        if (!voice && langCode !== 'en') {
            voice = this.availableVoices.find(v => v.lang.startsWith('en'));
        }
        
        // Last resort: use first available voice
        if (!voice) {
            voice = this.availableVoices[0];
        }
        
        return voice;
    }
    
    getAvailableVoices() {
        return this.availableVoices;
    }
    
    getVoicesByLanguage(language) {
        const langCode = language.split('-')[0];
        return this.availableVoices.filter(voice => 
            voice.lang === language || voice.lang.startsWith(langCode)
        );
    }
    
    setVoice(voice) {
        if (typeof voice === 'string') {
            // Find voice by name
            const foundVoice = this.availableVoices.find(v => v.name === voice);
            if (foundVoice) {
                this.selectedVoice = foundVoice;
                this.ttsConfig.voice = foundVoice;
                console.log('Voice set to:', foundVoice.name);
                return true;
            } else {
                console.warn('Voice not found:', voice);
                return false;
            }
        } else if (voice && voice.name) {
            // Voice object provided
            this.selectedVoice = voice;
            this.ttsConfig.voice = voice;
            console.log('Voice set to:', voice.name);
            return true;
        }
        
        return false;
    }
    
    // TTS Configuration Methods
    
    setTTSRate(rate) {
        this.ttsConfig.rate = this.clampValue(rate, 0.1, 10);
        console.log('TTS rate set to:', this.ttsConfig.rate);
    }
    
    setTTSPitch(pitch) {
        this.ttsConfig.pitch = this.clampValue(pitch, 0, 2);
        console.log('TTS pitch set to:', this.ttsConfig.pitch);
    }
    
    setTTSVolume(volume) {
        this.ttsConfig.volume = this.clampValue(volume, 0, 1);
        console.log('TTS volume set to:', this.ttsConfig.volume);
    }
    
    getTTSConfig() {
        return { ...this.ttsConfig };
    }
    
    updateTTSConfig(config) {
        if (config.rate !== undefined) this.setTTSRate(config.rate);
        if (config.pitch !== undefined) this.setTTSPitch(config.pitch);
        if (config.volume !== undefined) this.setTTSVolume(config.volume);
        if (config.voice !== undefined) this.setVoice(config.voice);
        if (config.autoPlay !== undefined) this.ttsConfig.autoPlay = config.autoPlay;
        if (config.fallbackToText !== undefined) this.ttsConfig.fallbackToText = config.fallbackToText;
        
        console.log('TTS configuration updated:', this.ttsConfig);
    }
    
    clampValue(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }
    
    // Getters
    
    isListening() {
        return this.isListening;
    }
    
    isSpeaking() {
        return this.isSpeaking;
    }
    
    getCurrentState() {
        return this.state;
    }
    
    getLastTranscript() {
        return this.finalTranscript || this.lastTranscript;
    }
    
    getLastSpokenText() {
        return this.lastSpokenText;
    }
    
    // Capability detection
    
    getCapabilities() {
        return {
            speechRecognition: this.hasSpeechRecognition(),
            speechSynthesis: this.hasSpeechSynthesis(),
            mediaDevices: this.hasMediaDevices(),
            secureContext: this.isSecureContext(),
            supported: this.isFullySupported()
        };
    }
    
    hasSpeechRecognition() {
        return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
    }
    
    hasSpeechSynthesis() {
        return 'speechSynthesis' in window;
    }
    
    hasMediaDevices() {
        return navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
    }
    
    isSecureContext() {
        return location.protocol === 'https:' || 
               location.hostname === 'localhost' || 
               location.hostname === '127.0.0.1';
    }
    
    isFullySupported() {
        return this.hasSpeechRecognition() && 
               this.hasSpeechSynthesis() && 
               this.hasMediaDevices() && 
               this.isSecureContext();
    }
    
    // Permission handling
    
    async checkMicrophonePermission() {
        if (!navigator.permissions) {
            // Fallback: try to access microphone directly
            return await this.requestMicrophoneAccess();
        }
        
        try {
            const permission = await navigator.permissions.query({ name: 'microphone' });
            
            switch (permission.state) {
                case 'granted':
                    return true;
                    
                case 'denied':
                    this.handleError('microphone-denied', 'Microphone access denied. Please allow microphone access in your browser settings.');
                    return false;
                    
                case 'prompt':
                    return await this.requestMicrophoneAccess();
                    
                default:
                    return await this.requestMicrophoneAccess();
            }
            
        } catch (error) {
            console.warn('Permission API not available, trying direct access:', error);
            return await this.requestMicrophoneAccess();
        }
    }
    
    async requestMicrophoneAccess() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Stop the stream immediately as we only needed permission
            stream.getTracks().forEach(track => track.stop());
            
            return true;
            
        } catch (error) {
            let errorMessage = 'Microphone access failed';
            
            switch (error.name) {
                case 'NotAllowedError':
                    errorMessage = 'Microphone access denied. Please allow microphone access and refresh the page.';
                    break;
                case 'NotFoundError':
                    errorMessage = 'No microphone found. Please connect a microphone and try again.';
                    break;
                case 'NotReadableError':
                    errorMessage = 'Microphone is being used by another application.';
                    break;
                case 'OverconstrainedError':
                    errorMessage = 'Microphone constraints could not be satisfied.';
                    break;
                default:
                    errorMessage = `Microphone error: ${error.message}`;
            }
            
            this.handleError('microphone-access-failed', errorMessage);
            return false;
        }
    }
    
    // Event handlers
    
    handleRecognitionStart() {
        this.isListening = true;
        this.setState('listening');
        console.log('Speech recognition started');
    }
    
    handleRecognitionResult(event) {
        let interimTranscript = '';
        let finalTranscript = '';
        
        // Process results
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            const transcript = result[0].transcript;
            
            if (result.isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }
        
        // Update transcripts
        if (finalTranscript) {
            this.finalTranscript += finalTranscript;
            this.lastTranscript = this.finalTranscript;
            
            // Clear silence timer since we got speech
            this.clearSilenceTimer();
            
            // Notify with final transcript
            if (this.onTranscript) {
                this.onTranscript(this.finalTranscript.trim(), true);
            }
            
            console.log('Final transcript:', this.finalTranscript);
            
        } else if (interimTranscript) {
            this.lastTranscript = this.finalTranscript + interimTranscript;
            
            // Notify with interim transcript
            if (this.onTranscript) {
                this.onTranscript(this.lastTranscript.trim(), false);
            }
        }
    }
    
    handleRecognitionError(event) {
        console.error('Speech recognition error:', event.error, event.message);
        
        let errorMessage = 'Speech recognition error';
        let errorCode = event.error;
        
        switch (event.error) {
            case 'not-allowed':
                errorMessage = 'Microphone access denied. Please allow microphone access and refresh the page.';
                break;
            case 'no-speech':
                errorMessage = 'No speech detected. Please try speaking again.';
                break;
            case 'audio-capture':
                errorMessage = 'No microphone found. Please connect a microphone and try again.';
                break;
            case 'network':
                errorMessage = 'Network error. Please check your connection and try again.';
                break;
            case 'service-not-allowed':
                errorMessage = 'Speech service not available. Please try again later.';
                break;
            case 'bad-grammar':
                errorMessage = 'Speech recognition grammar error.';
                break;
            case 'language-not-supported':
                errorMessage = 'Selected language not supported.';
                break;
            default:
                errorMessage = `Speech recognition error: ${event.error}`;
        }
        
        this.handleError(errorCode, errorMessage);
    }
    
    handleRecognitionEnd() {
        this.isListening = false;
        this.isRecognitionActive = false;
        this.clearTimers();
        
        if (this.state === 'listening') {
            this.setState('idle');
        }
        
        console.log('Speech recognition ended');
    }
    
    handleSpeechStart() {
        console.log('Speech detected');
        this.clearSilenceTimer();
    }
    
    handleSpeechEnd() {
        console.log('Speech ended');
        this.startSilenceTimer();
    }
    
    handleNoMatch() {
        console.log('No speech match found');
        this.handleError('no-match', 'Could not understand the speech. Please try again.');
    }
    
    // Timer management
    
    startSilenceTimer() {
        this.clearSilenceTimer();
        
        this.silenceTimer = setTimeout(() => {
            console.log('Silence timeout reached');
            this.stopListening();
        }, this.config.silenceTimeout);
    }
    
    clearSilenceTimer() {
        if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
            this.silenceTimer = null;
        }
    }
    
    clearTimers() {
        this.clearSilenceTimer();
        
        if (this.maxRecordingTimer) {
            clearTimeout(this.maxRecordingTimer);
            this.maxRecordingTimer = null;
        }
    }
    
    // Error handling
    
    handleError(errorCode, errorMessage) {
        this.setState('error');
        
        console.error(`Speech manager error [${errorCode}]:`, errorMessage);
        
        if (this.onError) {
            this.onError(errorCode, errorMessage);
        }
        
        // Auto-recover from certain errors
        setTimeout(() => {
            if (this.state === 'error') {
                this.setState('idle');
            }
        }, 3000);
    }
    
    // AI Response Integration
    
    async processAIResponse(responseText, options = {}) {
        if (!responseText || typeof responseText !== 'string') {
            console.warn('Invalid AI response text provided');
            return false;
        }
        
        console.log('Processing AI response for TTS:', responseText.substring(0, 100) + '...');
        
        // Set processing state
        this.setState('processing');
        
        try {
            // Clean up the response text for better speech
            const cleanedText = this.cleanTextForSpeech(responseText);
            
            // Automatically play if configured to do so
            if (this.ttsConfig.autoPlay) {
                const success = this.speakText(cleanedText, options);
                
                if (!success && this.ttsConfig.fallbackToText) {
                    // Fallback to text display
                    if (this.onStateChange) {
                        this.onStateChange('ai-response-fallback', 'processing', {
                            originalText: responseText,
                            cleanedText: cleanedText,
                            error: 'TTS failed, displaying text'
                        });
                    }
                }
                
                return success;
            } else {
                // Just store for manual playback
                this.lastSpokenText = cleanedText;
                this.setState('idle');
                
                if (this.onStateChange) {
                    this.onStateChange('ai-response-ready', 'processing', {
                        text: cleanedText,
                        autoPlay: false
                    });
                }
                
                return true;
            }
            
        } catch (error) {
            console.error('Error processing AI response:', error);
            this.handleError('ai-response-processing-failed', `Failed to process AI response: ${error.message}`);
            return false;
        }
    }
    
    cleanTextForSpeech(text) {
        return text
            // Remove markdown formatting
            .replace(/\*\*(.*?)\*\*/g, '$1') // Bold
            .replace(/\*(.*?)\*/g, '$1') // Italic
            .replace(/`(.*?)`/g, '$1') // Inline code
            .replace(/```[\s\S]*?```/g, '[code block]') // Code blocks
            .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // Links
            .replace(/#{1,6}\s+/g, '') // Headers
            .replace(/^\s*[-*+]\s+/gm, '') // List items
            .replace(/^\s*\d+\.\s+/gm, '') // Numbered lists
            
            // Clean up special characters and formatting
            .replace(/&nbsp;/g, ' ')
            .replace(/&amp;/g, 'and')
            .replace(/&lt;/g, 'less than')
            .replace(/&gt;/g, 'greater than')
            .replace(/&quot;/g, '"')
            .replace(/&#39;/g, "'")
            
            // Normalize whitespace
            .replace(/\s+/g, ' ')
            .trim();
    }
    
    // Configuration
    
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        
        // Update recognition settings if available
        if (this.recognition) {
            this.recognition.lang = this.config.language;
            this.recognition.continuous = this.config.continuous;
            this.recognition.interimResults = this.config.interimResults;
            this.recognition.maxAlternatives = this.config.maxAlternatives;
        }
        
        console.log('Speech manager configuration updated:', this.config);
    }
    
    // Cleanup
    
    cleanup() {
        console.log('Cleaning up VoiceSpeechManager...');
        
        // Stop any active processes
        this.stopListening();
        this.stopSpeaking();
        
        // Clear timers
        this.clearTimers();
        
        // Reset state
        this.setState('idle');
        
        // Clear TTS-related data
        this.lastSpokenText = '';
        this.availableVoices = [];
        this.selectedVoice = null;
        
        // Remove speech synthesis event handlers
        if (this.synthesis && this.synthesis.onvoiceschanged) {
            this.synthesis.onvoiceschanged = null;
        }
        
        // Clear references
        this.recognition = null;
        this.currentUtterance = null;
        this.onTranscript = null;
        this.onError = null;
        this.onStateChange = null;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceSpeechManager;
}

// Make available globally
window.VoiceSpeechManager = VoiceSpeechManager;