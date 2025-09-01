// Voice Assistant - Simplified Functional Implementation
class VoiceAssistant {
    constructor() {
        this.state = {
            isListening: false,
            isSpeaking: false,
            isMuted: false,
            currentState: 'idle'
        };
        
        this.elements = {};
        this.recognition = null;
        this.synthesis = null;
        this.currentUtterance = null;
        this.apiClient = null;
        this.settingsManager = null;
        
        this.init();
    }
    
    init() {
        this.cacheElements();
        this.initSpeechRecognition();
        this.initSpeechSynthesis();
        this.initSettingsModal();
        this.bindEvents();
        this.updateUI();
        
        console.log('Voice Assistant initialized');
    }
    
    cacheElements() {
        this.elements = {
            container: document.getElementById('voice-container'),
            micButton: document.getElementById('mic-button'),
            micIcon: document.getElementById('mic-icon'),
            statusText: document.getElementById('status-text'),
            transcriptText: document.querySelector('.transcript-text'),
            responseText: document.querySelector('.response-text'),
            transcriptArea: document.getElementById('transcript-area'),
            responseArea: document.getElementById('response-area'),
            audioVisualizer: document.getElementById('audio-visualizer'),
            closeBtn: document.getElementById('close-btn'),
            settingsBtn: document.getElementById('settings-btn'),
            muteBtn: document.getElementById('mute-btn'),
            stopBtn: document.getElementById('stop-btn'),
            replayBtn: document.getElementById('replay-btn'),
            pulseRings: document.querySelectorAll('.pulse-ring')
        };
    }
    
    initSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            this.showError('Speech recognition not supported in this browser');
            return;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        
        this.recognition.onstart = () => {
            console.log('Speech recognition started');
            this.setState('listening');
        };
        
        this.recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            
            this.updateTranscript(transcript);
            
            if (event.results[event.results.length - 1].isFinal) {
                console.log('Final transcript:', transcript);
                this.processTranscript(transcript);
            }
        };
        
        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.handleSpeechError(event.error);
        };
        
        this.recognition.onend = () => {
            console.log('Speech recognition ended');
            if (this.state.currentState === 'listening') {
                this.setState('idle');
            }
        };
    }
    
    initSpeechSynthesis() {
        if (!('speechSynthesis' in window)) {
            this.showError('Text-to-speech not supported in this browser');
            return;
        }
        
        this.synthesis = window.speechSynthesis;
    }
    
    bindEvents() {
        // Microphone button
        this.elements.micButton.addEventListener('click', () => this.handleMicClick());
        
        // Control buttons
        this.elements.closeBtn.addEventListener('click', () => this.handleClose());
        this.elements.settingsBtn.addEventListener('click', () => this.handleSettings());
        this.elements.muteBtn.addEventListener('click', () => this.handleMute());
        this.elements.stopBtn.addEventListener('click', () => this.handleStop());
        this.elements.replayBtn.addEventListener('click', () => this.handleReplay());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeydown(e));
        
        // Window events
        window.addEventListener('beforeunload', () => this.cleanup());
    }
    
    handleMicClick() {
        if (this.state.isMuted) {
            this.showError('Microphone is muted');
            return;
        }
        
        if (this.state.currentState === 'idle') {
            this.startListening();
        } else if (this.state.currentState === 'listening') {
            this.stopListening();
        }
    }
    
    async startListening() {
        if (!this.recognition) {
            this.showError('Speech recognition not available');
            return;
        }
        
        try {
            this.recognition.start();
            this.setState('listening');
        } catch (error) {
            console.error('Error starting speech recognition:', error);
            this.showError('Could not start listening');
        }
    }
    
    stopListening() {
        if (this.recognition && this.state.isListening) {
            this.recognition.stop();
        }
        this.setState('idle');
    }
    
    async processTranscript(transcript) {
        if (!transcript.trim()) {
            this.setState('idle');
            return;
        }
        
        this.setState('processing');
        
        try {
            // Simulate API call - replace with actual API integration
            const response = await this.callAPI(transcript);
            this.displayResponse(response);
            this.speakResponse(response);
        } catch (error) {
            console.error('Error processing transcript:', error);
            this.showError('Failed to process your message');
            this.setState('idle');
        }
    }
    
    async callAPI(message) {
        try {
            // Initialize API client if not already done
            if (!this.apiClient) {
                this.apiClient = new VoiceAPIClient();
                const initialized = await this.apiClient.initialize();
                if (!initialized) {
                    throw new Error('Failed to initialize API client');
                }
            }
            
            // Send message to backend chat API
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    query: message
                })
            });
            
            if (!response.ok) {
                throw new Error(`API request failed: ${response.status}`);
            }
            
            const data = await response.json();
            return data.summary || data.message || 'I received your message but couldn\'t generate a proper response.';
            
        } catch (error) {
            console.error('API call error:', error);
            throw new Error('Failed to get response from AI assistant. Please try again.');
        }
    }
    
    displayResponse(response) {
        this.elements.responseText.textContent = response;
        this.elements.responseArea.classList.add('active');
        this.lastResponse = response;
    }
    
    speakResponse(text, options = {}) {
        if (!this.synthesis) {
            this.setState('idle');
            return;
        }
        
        // Stop any current speech
        this.synthesis.cancel();
        
        this.currentUtterance = new SpeechSynthesisUtterance(text);
        
        // Apply TTS settings if available
        if (this.ttsSettings) {
            this.currentUtterance.rate = this.ttsSettings.rate || 1.0;
            this.currentUtterance.pitch = this.ttsSettings.pitch || 1.0;
            this.currentUtterance.volume = this.ttsSettings.volume || 1.0;
            if (this.ttsSettings.voice) {
                this.currentUtterance.voice = this.ttsSettings.voice;
            }
        } else {
            // Use default values or options
            this.currentUtterance.rate = options.rate || 1.0;
            this.currentUtterance.pitch = options.pitch || 1.0;
            this.currentUtterance.volume = options.volume || 1.0;
            if (options.voice) {
                this.currentUtterance.voice = options.voice;
            }
        }
        
        this.currentUtterance.onstart = () => {
            this.setState('speaking');
        };
        
        this.currentUtterance.onend = () => {
            this.setState('idle');
        };
        
        this.currentUtterance.onerror = (event) => {
            console.error('Speech synthesis error:', event.error);
            this.setState('idle');
        };
        
        this.synthesis.speak(this.currentUtterance);
    }
    
    updateTranscript(transcript) {
        this.elements.transcriptText.textContent = transcript;
        this.elements.transcriptArea.classList.add('active');
    }
    
    setState(newState) {
        const oldState = this.state.currentState;
        this.state.currentState = newState;
        
        // Update individual state flags
        this.state.isListening = newState === 'listening';
        this.state.isSpeaking = newState === 'speaking';
        
        console.log(`State changed: ${oldState} -> ${newState}`);
        
        this.updateUI();
        this.updateVisualFeedback(newState);
    }
    
    updateUI() {
        const { micButton, statusText } = this.elements;
        const state = this.state.currentState;
        
        // Remove all state classes
        micButton.classList.remove('listening', 'processing', 'speaking', 'error', 'muted');
        statusText.classList.remove('listening', 'processing', 'speaking', 'error');
        
        // Add current state class
        if (state !== 'idle') {
            micButton.classList.add(state);
            statusText.classList.add(state);
        }
        
        // Add muted class if muted
        if (this.state.isMuted) {
            micButton.classList.add('muted');
        }
        
        // Update status text
        this.updateStatusText(state);
        
        // Update control buttons
        this.updateControlButtons();
    }
    
    updateStatusText(state) {
        const statusMessages = {
            idle: 'Tap to start talking',
            listening: 'Listening...',
            processing: 'Processing...',
            speaking: 'Speaking...',
            error: 'Error occurred'
        };
        
        if (this.state.isMuted) {
            this.elements.statusText.textContent = 'Microphone muted';
        } else {
            this.elements.statusText.textContent = statusMessages[state] || statusMessages.idle;
        }
    }
    
    updateControlButtons() {
        // Update mute button
        if (this.state.isMuted) {
            this.elements.muteBtn.classList.add('muted');
            this.elements.muteBtn.setAttribute('aria-label', 'Unmute microphone');
        } else {
            this.elements.muteBtn.classList.remove('muted');
            this.elements.muteBtn.setAttribute('aria-label', 'Mute microphone');
        }
        
        // Update stop button
        const isActive = this.state.isListening || this.state.isSpeaking;
        this.elements.stopBtn.classList.toggle('active', isActive);
        
        // Update replay button
        this.elements.replayBtn.disabled = !this.lastResponse;
    }
    
    updateVisualFeedback(state) {
        // Update audio visualizer
        if (state === 'listening' || state === 'speaking') {
            this.elements.audioVisualizer.classList.add('active');
            this.animateVisualizer(state === 'speaking');
        } else {
            this.elements.audioVisualizer.classList.remove('active');
        }
    }
    
    animateVisualizer(isSpeaking = false) {
        const bars = this.elements.audioVisualizer.querySelectorAll('.visualizer-bar');
        
        bars.forEach((bar, index) => {
            if (isSpeaking) {
                bar.classList.add('speaking');
            } else {
                bar.classList.remove('speaking');
            }
            
            // Animate bar heights
            const animate = () => {
                const height = Math.random() * 30 + 8;
                bar.style.height = `${height}px`;
            };
            
            if (this.state.isListening || this.state.isSpeaking) {
                animate();
                setTimeout(() => {
                    if (this.state.isListening || this.state.isSpeaking) {
                        requestAnimationFrame(() => this.animateVisualizer(isSpeaking));
                    }
                }, 100 + index * 20);
            }
        });
    }
    
    handleClose() {
        console.log('Closing voice assistant');
        this.cleanup();
        
        // Try to close the window or navigate back
        if (window.opener) {
            window.close();
        } else {
            // Fallback - could navigate to main chat
            window.history.back();
        }
    }
    
    handleSettings() {
        console.log('Settings clicked - opening settings modal');
        this.openSettingsModal();
    }
    
    handleMute() {
        this.state.isMuted = !this.state.isMuted;
        
        if (this.state.isMuted && this.state.isListening) {
            this.stopListening();
        }
        
        console.log(`Microphone ${this.state.isMuted ? 'muted' : 'unmuted'}`);
        this.updateUI();
    }
    
    handleStop() {
        console.log('Stop clicked');
        
        if (this.state.isListening) {
            this.stopListening();
        }
        
        if (this.state.isSpeaking && this.synthesis) {
            this.synthesis.cancel();
            this.setState('idle');
        }
    }
    
    handleReplay() {
        if (!this.lastResponse) {
            console.log('No response to replay');
            return;
        }
        
        console.log('Replaying last response');
        
        if (this.state.isSpeaking && this.synthesis) {
            this.synthesis.cancel();
        }
        
        this.speakResponse(this.lastResponse);
    }
    
    handleKeydown(e) {
        // Ignore if typing in input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        switch (e.key) {
            case ' ':
                e.preventDefault();
                this.handleMicClick();
                break;
            case 'Escape':
                e.preventDefault();
                this.handleStop();
                break;
            case 'm':
            case 'M':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    this.handleMute();
                }
                break;
        }
    }
    
    handleSpeechError(error) {
        console.error('Speech error:', error);
        
        let errorMessage = 'Speech recognition error';
        
        switch (error) {
            case 'no-speech':
                errorMessage = 'No speech detected';
                break;
            case 'audio-capture':
                errorMessage = 'Microphone not accessible';
                break;
            case 'not-allowed':
                errorMessage = 'Microphone permission denied';
                break;
            case 'network':
                errorMessage = 'Network error';
                break;
        }
        
        this.showError(errorMessage);
    }
    
    showError(message) {
        console.error('Error:', message);
        this.elements.statusText.textContent = message;
        this.elements.statusText.classList.add('error');
        this.elements.micButton.classList.add('error');
        
        setTimeout(() => {
            this.elements.statusText.classList.remove('error');
            this.elements.micButton.classList.remove('error');
            this.setState('idle');
        }, 3000);
    }
    
    initSettingsModal() {
        // Initialize settings manager when available
        if (typeof VoiceSettingsManager !== 'undefined') {
            this.settingsManager = new VoiceSettingsManager(this);
            console.log('Settings manager initialized');
        } else {
            console.warn('VoiceSettingsManager not available');
        }
        
        // Bind modal close events
        const modal = document.getElementById('settings-modal');
        const closeBtn = modal?.querySelector('.modal-close');
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeSettingsModal());
        }
        
        // Close modal when clicking outside
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeSettingsModal();
                }
            });
        }
    }
    
    openSettingsModal() {
        const modal = document.getElementById('settings-modal');
        if (modal) {
            modal.classList.remove('hidden');
            modal.setAttribute('aria-hidden', 'false');
            
            // Initialize settings manager if not already done
            if (!this.settingsManager && typeof VoiceSettingsManager !== 'undefined') {
                this.settingsManager = new VoiceSettingsManager(this);
            }
            
            console.log('Settings modal opened');
        }
    }
    
    closeSettingsModal() {
        const modal = document.getElementById('settings-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.setAttribute('aria-hidden', 'true');
            console.log('Settings modal closed');
        }
    }
    
    // Methods for settings manager integration
    updateLanguage(language) {
        if (this.recognition) {
            this.recognition.lang = language;
            console.log(`Speech recognition language updated to: ${language}`);
        }
    }
    
    updateTTSSettings(settings) {
        // Store TTS settings for use in speakResponse
        this.ttsSettings = settings;
        console.log('TTS settings updated:', settings);
    }
    
    updateInteractionSettings(settings) {
        // Store interaction settings
        this.interactionSettings = settings;
        console.log('Interaction settings updated:', settings);
    }
    
    speakText(text, options = {}) {
        // Use this method for settings testing
        this.speakResponse(text, options);
    }
    
    cleanup() {
        console.log('Cleaning up voice assistant');
        
        if (this.recognition) {
            this.recognition.stop();
        }
        
        if (this.synthesis) {
            this.synthesis.cancel();
        }
        
        if (this.settingsManager) {
            // Clean up settings manager if it has cleanup method
            if (typeof this.settingsManager.cleanup === 'function') {
                this.settingsManager.cleanup();
            }
        }
    }
}

// Initialize the voice assistant when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.voiceAssistant = new VoiceAssistant();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.hidden && window.voiceAssistant) {
        window.voiceAssistant.handleStop();
    }
});