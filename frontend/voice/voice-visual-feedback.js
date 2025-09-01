/**
 * VoiceVisualFeedback Class
 * Handles all visual feedback and animations for the voice assistant interface
 * Implements state-based UI updates, microphone animations, audio visualizer, and status indicators
 */

class VoiceVisualFeedback {
    constructor(container) {
        this.container = container;
        this.elements = {};
        this.animationFrameId = null;
        this.visualizerInterval = null;
        this.currentState = 'idle';
        
        // Animation settings
        this.animationSettings = {
            visualizer: {
                bars: 15,
                minHeight: 4,
                maxHeight: 44,
                animationSpeed: 100,
                speakingSpeed: 50
            },
            transitions: {
                duration: 300,
                easing: 'ease'
            }
        };
        
        this.initialize();
    }
    
    initialize() {
        this.cacheElements();
        this.setupAnimationStyles();
        console.log('VoiceVisualFeedback initialized');
    }
    
    cacheElements() {
        this.elements = {
            micButton: this.container.querySelector('#mic-button'),
            micIcon: this.container.querySelector('#mic-icon'),
            audioVisualizer: this.container.querySelector('#audio-visualizer'),
            visualizerBars: this.container.querySelectorAll('.visualizer-bar'),
            transcriptArea: this.container.querySelector('#transcript-area'),
            responseArea: this.container.querySelector('#response-area'),
            transcriptText: this.container.querySelector('#transcript-area .transcript-text'),
            responseText: this.container.querySelector('#response-area .response-text'),
            statusText: this.container.querySelector('#status-text'),
            statusIndicator: this.container.querySelector('#status-indicator')
        };
        
        // Validate required elements
        const requiredElements = ['micButton', 'audioVisualizer', 'statusText'];
        for (const elementName of requiredElements) {
            if (!this.elements[elementName]) {
                console.error(`Required element not found: ${elementName}`);
            }
        }
    }
    
    setupAnimationStyles() {
        // Ensure CSS custom properties are available for animations
        if (!document.documentElement.style.getPropertyValue('--listening-color')) {
            console.warn('CSS custom properties not found, using fallback colors');
        }
    }
    
    /**
     * Show listening state with pulsing animation
     */
    showListening() {
        this.setState('listening');
        this.updateMicrophoneState('listening');
        this.updateStatusText('Listening...', 'listening');
        this.showAudioVisualizer();
        this.startVisualizerAnimation('listening');
        
        console.log('Visual feedback: Showing listening state');
    }
    
    /**
     * Show processing state with rotating animation
     */
    showProcessing() {
        this.setState('processing');
        this.updateMicrophoneState('processing');
        this.updateStatusText('Processing...', 'processing');
        this.hideAudioVisualizer();
        this.stopVisualizerAnimation();
        
        console.log('Visual feedback: Showing processing state');
    }
    
    /**
     * Show speaking state with speaking animation
     * @param {string} text - The text being spoken (optional)
     */
    showSpeaking(text = '') {
        this.setState('speaking');
        this.updateMicrophoneState('speaking');
        this.updateStatusText('Speaking...', 'speaking');
        this.showAudioVisualizer();
        this.startVisualizerAnimation('speaking');
        
        if (text) {
            this.displayResponse(text);
        }
        
        console.log('Visual feedback: Showing speaking state');
    }
    
    /**
     * Show error state with shake animation
     * @param {string} message - Error message to display
     */
    showError(message) {
        this.setState('error');
        this.updateMicrophoneState('error');
        this.updateStatusText(message, 'error');
        this.hideAudioVisualizer();
        this.stopVisualizerAnimation();
        this.triggerShakeAnimation();
        
        // Auto-clear error state after 3 seconds
        setTimeout(() => {
            if (this.currentState === 'error') {
                this.showIdle();
            }
        }, 3000);
        
        console.log(`Visual feedback: Showing error state - ${message}`);
    }
    
    /**
     * Show idle state (default)
     */
    showIdle() {
        this.setState('idle');
        this.updateMicrophoneState('idle');
        this.updateStatusText('Tap to start talking', 'idle');
        this.hideAudioVisualizer();
        this.stopVisualizerAnimation();
        
        console.log('Visual feedback: Showing idle state');
    }
    
    /**
     * Show muted state
     */
    showMuted() {
        this.updateMicrophoneState('muted');
        this.updateStatusText('Microphone muted', 'muted');
        this.hideAudioVisualizer();
        this.stopVisualizerAnimation();
        
        console.log('Visual feedback: Showing muted state');
    }
    
    /**
     * Update microphone button state and animations
     * @param {string} state - The state to apply
     */
    updateMicrophoneState(state) {
        if (!this.elements.micButton) return;
        
        // Remove all state classes
        const stateClasses = ['listening', 'processing', 'speaking', 'error', 'muted', 'idle'];
        this.elements.micButton.classList.remove(...stateClasses);
        
        // Add new state class
        if (state !== 'idle') {
            this.elements.micButton.classList.add(state);
        }
        
        // Update icon color based on state
        this.updateMicrophoneIcon(state);
    }
    
    /**
     * Update microphone icon appearance
     * @param {string} state - The current state
     */
    updateMicrophoneIcon(state) {
        if (!this.elements.micIcon) return;
        
        // Icon color is handled by CSS, but we can add additional logic here if needed
        // For example, changing the icon itself for different states
        
        switch (state) {
            case 'muted':
                // Could change to a muted microphone icon
                break;
            case 'error':
                // Could change to an error icon temporarily
                break;
            default:
                // Keep default microphone icon
                break;
        }
    }
    
    /**
     * Animate microphone based on state
     * @param {string} state - The animation state
     */
    animateMicrophone(state) {
        this.updateMicrophoneState(state);
        
        // Additional animation logic can be added here
        // Most animations are handled by CSS classes
        
        if (state === 'error') {
            this.triggerShakeAnimation();
        }
    }
    
    /**
     * Trigger shake animation for error states
     */
    triggerShakeAnimation() {
        if (!this.elements.micButton) return;
        
        // Remove any existing shake animation
        this.elements.micButton.classList.remove('shake');
        
        // Force reflow to ensure class removal takes effect
        this.elements.micButton.offsetHeight;
        
        // Add shake animation
        this.elements.micButton.classList.add('shake');
        
        // Remove shake class after animation completes
        setTimeout(() => {
            this.elements.micButton.classList.remove('shake');
        }, 500);
    }
    
    /**
     * Show audio visualizer
     */
    showAudioVisualizer() {
        if (this.elements.audioVisualizer) {
            this.elements.audioVisualizer.classList.add('active');
        }
    }
    
    /**
     * Hide audio visualizer
     */
    hideAudioVisualizer() {
        if (this.elements.audioVisualizer) {
            this.elements.audioVisualizer.classList.remove('active');
        }
    }
    
    /**
     * Start visualizer animation
     * @param {string} mode - Animation mode ('listening' or 'speaking')
     */
    startVisualizerAnimation(mode = 'listening') {
        this.stopVisualizerAnimation();
        
        if (!this.elements.visualizerBars || this.elements.visualizerBars.length === 0) {
            console.warn('Visualizer bars not found');
            return;
        }
        
        const bars = Array.from(this.elements.visualizerBars);
        const settings = this.animationSettings.visualizer;
        
        if (mode === 'speaking') {
            this.startSpeakingAnimation(bars, settings);
        } else {
            this.startListeningAnimation(bars, settings);
        }
    }
    
    /**
     * Start listening animation (random heights)
     * @param {Array} bars - Visualizer bar elements
     * @param {Object} settings - Animation settings
     */
    startListeningAnimation(bars, settings) {
        // Remove speaking class from bars
        bars.forEach(bar => bar.classList.remove('speaking'));
        
        this.visualizerInterval = setInterval(() => {
            bars.forEach(bar => {
                const height = Math.random() * (settings.maxHeight - settings.minHeight) + settings.minHeight;
                bar.style.height = `${height}px`;
            });
        }, settings.animationSpeed);
    }
    
    /**
     * Start speaking animation (wave pattern)
     * @param {Array} bars - Visualizer bar elements
     * @param {Object} settings - Animation settings
     */
    startSpeakingAnimation(bars, settings) {
        // Add speaking class to bars
        bars.forEach(bar => bar.classList.add('speaking'));
        
        let time = 0;
        this.visualizerInterval = setInterval(() => {
            bars.forEach((bar, index) => {
                // Create a sine wave pattern
                const frequency = 0.02;
                const amplitude = (settings.maxHeight - settings.minHeight) / 2;
                const offset = settings.minHeight + amplitude;
                const phase = index * 0.5;
                
                const height = Math.sin(time * frequency + phase) * amplitude + offset;
                bar.style.height = `${Math.max(settings.minHeight, height)}px`;
            });
            time += settings.speakingSpeed;
        }, settings.speakingSpeed);
    }
    
    /**
     * Stop visualizer animation
     */
    stopVisualizerAnimation() {
        if (this.visualizerInterval) {
            clearInterval(this.visualizerInterval);
            this.visualizerInterval = null;
        }
        
        // Reset bars to minimum height
        if (this.elements.visualizerBars) {
            this.elements.visualizerBars.forEach(bar => {
                bar.style.height = `${this.animationSettings.visualizer.minHeight}px`;
                bar.classList.remove('speaking');
            });
        }
    }
    
    /**
     * Update status text with contextual messages
     * @param {string} text - Status message
     * @param {string} state - Current state for styling
     */
    updateStatusText(text, state = 'idle') {
        if (!this.elements.statusText) return;
        
        this.elements.statusText.textContent = text;
        
        // Remove all state classes
        const stateClasses = ['listening', 'processing', 'speaking', 'error', 'muted'];
        this.elements.statusText.classList.remove(...stateClasses);
        
        // Add new state class
        if (state !== 'idle') {
            this.elements.statusText.classList.add(state);
        }
    }
    
    /**
     * Display transcript text with animation
     * @param {string} text - Transcript text
     */
    displayTranscript(text) {
        if (!this.elements.transcriptText || !this.elements.transcriptArea) return;
        
        this.elements.transcriptText.textContent = text;
        
        // Add active class with animation
        if (!this.elements.transcriptArea.classList.contains('active')) {
            this.elements.transcriptArea.classList.add('active');
            this.triggerFadeInAnimation(this.elements.transcriptArea);
        }
        
        console.log(`Transcript displayed: ${text}`);
    }
    
    /**
     * Display response text with animation
     * @param {string} text - Response text
     */
    displayResponse(text) {
        if (!this.elements.responseText || !this.elements.responseArea) return;
        
        this.elements.responseText.textContent = text;
        
        // Add active class with animation
        if (!this.elements.responseArea.classList.contains('active')) {
            this.elements.responseArea.classList.add('active');
            this.triggerFadeInAnimation(this.elements.responseArea);
        }
        
        console.log(`Response displayed: ${text}`);
    }
    
    /**
     * Clear transcript display
     */
    clearTranscript() {
        if (this.elements.transcriptText) {
            this.elements.transcriptText.textContent = '';
        }
        if (this.elements.transcriptArea) {
            this.elements.transcriptArea.classList.remove('active');
        }
    }
    
    /**
     * Clear response display
     */
    clearResponse() {
        if (this.elements.responseText) {
            this.elements.responseText.textContent = '';
        }
        if (this.elements.responseArea) {
            this.elements.responseArea.classList.remove('active');
        }
    }
    
    /**
     * Clear all conversation displays
     */
    clearConversation() {
        this.clearTranscript();
        this.clearResponse();
    }
    
    /**
     * Trigger fade-in animation for elements
     * @param {HTMLElement} element - Element to animate
     */
    triggerFadeInAnimation(element) {
        if (!element) return;
        
        // Remove any existing animation
        element.classList.remove('fade-in-up');
        
        // Force reflow
        element.offsetHeight;
        
        // Add animation class
        element.classList.add('fade-in-up');
        
        // Remove animation class after completion
        setTimeout(() => {
            element.classList.remove('fade-in-up');
        }, this.animationSettings.transitions.duration);
    }
    
    /**
     * Add smooth transitions between states
     * @param {string} fromState - Previous state
     * @param {string} toState - New state
     */
    addSmoothTransition(fromState, toState) {
        // Add transition logic for smooth state changes
        console.log(`Transitioning from ${fromState} to ${toState}`);
        
        // Custom transition logic can be added here
        // For now, transitions are handled by CSS
    }
    
    /**
     * Set current state
     * @param {string} state - New state
     */
    setState(state) {
        const oldState = this.currentState;
        this.currentState = state;
        
        if (oldState !== state) {
            this.addSmoothTransition(oldState, state);
        }
    }
    
    /**
     * Get current state
     * @returns {string} Current state
     */
    getState() {
        return this.currentState;
    }
    
    /**
     * Update visual feedback based on audio levels (for future enhancement)
     * @param {number} audioLevel - Audio level (0-100)
     */
    updateAudioLevel(audioLevel) {
        // This method can be used to create more responsive visualizations
        // based on actual audio input levels
        
        if (this.currentState === 'listening' && this.elements.visualizerBars) {
            // Adjust visualizer based on audio level
            const intensity = Math.max(0.1, audioLevel / 100);
            const bars = Array.from(this.elements.visualizerBars);
            
            bars.forEach((bar, index) => {
                const baseHeight = this.animationSettings.visualizer.minHeight;
                const maxHeight = this.animationSettings.visualizer.maxHeight * intensity;
                const height = Math.random() * maxHeight + baseHeight;
                bar.style.height = `${height}px`;
            });
        }
    }
    
    /**
     * Cleanup method to stop all animations and reset state
     */
    cleanup() {
        console.log('Cleaning up VoiceVisualFeedback...');
        
        // Stop all animations
        this.stopVisualizerAnimation();
        
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        
        // Reset to idle state
        this.showIdle();
        
        // Clear conversation displays
        this.clearConversation();
        
        console.log('VoiceVisualFeedback cleanup complete');
    }
    
    /**
     * Update theme colors (for dynamic theming)
     * @param {Object} colors - Color configuration
     */
    updateTheme(colors) {
        if (!colors) return;
        
        const root = document.documentElement;
        
        if (colors.listening) {
            root.style.setProperty('--listening-color', colors.listening);
        }
        if (colors.processing) {
            root.style.setProperty('--processing-color', colors.processing);
        }
        if (colors.speaking) {
            root.style.setProperty('--speaking-color', colors.speaking);
        }
        if (colors.error) {
            root.style.setProperty('--error-color', colors.error);
        }
        
        console.log('Theme colors updated');
    }
    
    /**
     * Get animation settings
     * @returns {Object} Current animation settings
     */
    getAnimationSettings() {
        return { ...this.animationSettings };
    }
    
    /**
     * Update animation settings
     * @param {Object} settings - New animation settings
     */
    updateAnimationSettings(settings) {
        this.animationSettings = { ...this.animationSettings, ...settings };
        console.log('Animation settings updated');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceVisualFeedback;
}

// Make available globally
if (typeof window !== 'undefined') {
    window.VoiceVisualFeedback = VoiceVisualFeedback;
}