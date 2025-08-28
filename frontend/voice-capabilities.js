/**
 * Voice Capabilities Detection Utility
 * Detects browser compatibility for voice features and provides fallback information
 */

class VoiceCapabilities {
    constructor() {
        this.capabilities = this.detectCapabilities();
    }

    /**
     * Detect all voice-related browser capabilities
     * @returns {Object} Object containing capability flags
     */
    detectCapabilities() {
        const capabilities = {
            speechRecognition: this.hasSpeechRecognition(),
            speechSynthesis: this.hasSpeechSynthesis(),
            mediaDevices: this.hasMediaDevices(),
            audioContext: this.hasAudioContext(),
            getUserMedia: this.hasGetUserMedia(),
            webkitSpeechRecognition: this.hasWebkitSpeechRecognition()
        };

        // Overall voice support
        capabilities.voiceInputSupported = capabilities.speechRecognition || capabilities.webkitSpeechRecognition;
        capabilities.voiceOutputSupported = capabilities.speechSynthesis;
        capabilities.fullVoiceSupported = capabilities.voiceInputSupported && capabilities.voiceOutputSupported;

        return capabilities;
    }

    /**
     * Check if Speech Recognition API is available
     * @returns {boolean}
     */
    hasSpeechRecognition() {
        return 'SpeechRecognition' in window;
    }

    /**
     * Check if WebKit Speech Recognition API is available
     * @returns {boolean}
     */
    hasWebkitSpeechRecognition() {
        return 'webkitSpeechRecognition' in window;
    }

    /**
     * Check if Speech Synthesis API is available
     * @returns {boolean}
     */
    hasSpeechSynthesis() {
        return 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
    }

    /**
     * Check if MediaDevices API is available
     * @returns {boolean}
     */
    hasMediaDevices() {
        return navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function';
    }

    /**
     * Check if getUserMedia is available (legacy check)
     * @returns {boolean}
     */
    hasGetUserMedia() {
        return !!(navigator.getUserMedia || navigator.webkitGetUserMedia || 
                 navigator.mozGetUserMedia || navigator.msGetUserMedia);
    }

    /**
     * Check if AudioContext is available
     * @returns {boolean}
     */
    hasAudioContext() {
        return 'AudioContext' in window || 'webkitAudioContext' in window;
    }

    /**
     * Get available speech synthesis voices
     * @returns {Promise<Array>} Array of available voices
     */
    async getAvailableVoices() {
        if (!this.capabilities.speechSynthesis) {
            return [];
        }

        return new Promise((resolve) => {
            let voices = speechSynthesis.getVoices();
            
            if (voices.length > 0) {
                resolve(voices);
            } else {
                // Some browsers load voices asynchronously
                speechSynthesis.addEventListener('voiceschanged', () => {
                    voices = speechSynthesis.getVoices();
                    resolve(voices);
                }, { once: true });
                
                // Fallback timeout
                setTimeout(() => resolve(speechSynthesis.getVoices()), 1000);
            }
        });
    }

    /**
     * Get supported speech recognition languages
     * @returns {Array} Array of supported language codes
     */
    getSupportedLanguages() {
        // Common languages supported by most browsers
        return [
            'en-US', 'en-GB', 'en-AU', 'en-CA', 'en-IN',
            'es-ES', 'es-MX', 'fr-FR', 'de-DE', 'it-IT',
            'pt-BR', 'ru-RU', 'ja-JP', 'ko-KR', 'zh-CN',
            'zh-TW', 'ar-SA', 'hi-IN', 'nl-NL', 'sv-SE'
        ];
    }

    /**
     * Test microphone access
     * @returns {Promise<boolean>} True if microphone access is granted
     */
    async testMicrophoneAccess() {
        if (!this.capabilities.mediaDevices) {
            return false;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            // Stop the stream immediately after testing
            stream.getTracks().forEach(track => track.stop());
            return true;
        } catch (error) {
            console.warn('Microphone access test failed:', error);
            return false;
        }
    }

    /**
     * Get browser-specific implementation
     * @returns {Object} Object with browser-specific constructors
     */
    getBrowserImplementation() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const SpeechGrammarList = window.SpeechGrammarList || window.webkitSpeechGrammarList;
        const SpeechRecognitionEvent = window.SpeechRecognitionEvent || window.webkitSpeechRecognitionEvent;

        return {
            SpeechRecognition,
            SpeechGrammarList,
            SpeechRecognitionEvent,
            SpeechSynthesisUtterance: window.SpeechSynthesisUtterance
        };
    }

    /**
     * Get capability report for debugging
     * @returns {Object} Detailed capability report
     */
    getCapabilityReport() {
        const userAgent = navigator.userAgent;
        const platform = navigator.platform;
        
        return {
            userAgent,
            platform,
            capabilities: this.capabilities,
            browserInfo: {
                isChrome: userAgent.includes('Chrome'),
                isFirefox: userAgent.includes('Firefox'),
                isSafari: userAgent.includes('Safari') && !userAgent.includes('Chrome'),
                isEdge: userAgent.includes('Edge'),
                isMobile: /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent)
            }
        };
    }

    /**
     * Get fallback message for unsupported features
     * @param {string} feature - Feature name ('stt', 'tts', 'microphone')
     * @returns {string} User-friendly fallback message
     */
    getFallbackMessage(feature) {
        const messages = {
            stt: 'Voice input is not supported in your browser. Please type your message instead.',
            tts: 'Voice output is not supported in your browser. Responses will be displayed as text only.',
            microphone: 'Microphone access is required for voice input. Please check your browser permissions.',
            general: 'Voice features are not fully supported in your browser. The chat will work in text-only mode.'
        };

        return messages[feature] || messages.general;
    }

    /**
     * Check if voice features should be enabled based on capabilities
     * @returns {Object} Recommendations for feature enablement
     */
    getFeatureRecommendations() {
        return {
            enableVoiceInput: this.capabilities.voiceInputSupported,
            enableVoiceOutput: this.capabilities.voiceOutputSupported,
            showVoiceControls: this.capabilities.fullVoiceSupported,
            requireMicrophoneTest: this.capabilities.voiceInputSupported,
            gracefulDegradation: !this.capabilities.fullVoiceSupported
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceCapabilities;
} else {
    window.VoiceCapabilities = VoiceCapabilities;
}