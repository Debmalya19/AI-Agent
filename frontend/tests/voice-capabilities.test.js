/**
 * Unit Tests for VoiceCapabilities Class
 * Tests browser compatibility detection and capability reporting
 */

// Mock Web Speech API for testing
class MockSpeechRecognition {
    constructor() {
        this.lang = 'en-US';
        this.continuous = false;
        this.interimResults = false;
    }
    start() {}
    stop() {}
}

class MockSpeechSynthesisUtterance {
    constructor(text) {
        this.text = text;
        this.rate = 1;
        this.pitch = 1;
        this.volume = 1;
    }
}

// Mock global objects for testing
const mockWindow = {
    SpeechRecognition: MockSpeechRecognition,
    webkitSpeechRecognition: MockSpeechRecognition,
    speechSynthesis: {
        getVoices: () => [
            { name: 'Test Voice 1', lang: 'en-US', voiceURI: 'test1' },
            { name: 'Test Voice 2', lang: 'es-ES', voiceURI: 'test2' }
        ],
        speak: () => {},
        cancel: () => {},
        pause: () => {},
        resume: () => {},
        addEventListener: () => {}
    },
    SpeechSynthesisUtterance: MockSpeechSynthesisUtterance,
    AudioContext: class MockAudioContext {},
    webkitAudioContext: class MockWebkitAudioContext {}
};

const mockNavigator = {
    mediaDevices: {
        getUserMedia: () => Promise.resolve({
            getTracks: () => [{ stop: () => {} }]
        })
    },
    getUserMedia: () => {},
    webkitGetUserMedia: () => {},
    mozGetUserMedia: () => {},
    msGetUserMedia: () => {},
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    platform: 'Win32'
};

// Test suite
class VoiceCapabilitiesTest {
    constructor() {
        this.testResults = [];
        this.setupMocks();
    }

    setupMocks() {
        // Set up global mocks
        if (typeof window === 'undefined') {
            // Node.js environment
            global.window = mockWindow;
            global.navigator = mockNavigator;
        } else {
            // Browser environment - backup original values
            this.originalWindow = {};
            this.originalNavigator = {};
            
            // Backup only the properties we're going to mock
            Object.keys(mockWindow).forEach(key => {
                this.originalWindow[key] = window[key];
                window[key] = mockWindow[key];
            });
            
            Object.keys(mockNavigator).forEach(key => {
                this.originalNavigator[key] = navigator[key];
                if (key !== 'userAgent' && key !== 'platform') {
                    try {
                        navigator[key] = mockNavigator[key];
                    } catch (e) {
                        // Some properties might be read-only, skip them
                    }
                }
            });
        }
    }

    restoreMocks() {
        if (typeof window !== 'undefined' && this.originalWindow) {
            // Restore original values
            Object.keys(this.originalWindow).forEach(key => {
                window[key] = this.originalWindow[key];
            });
            Object.keys(this.originalNavigator).forEach(key => {
                if (key !== 'userAgent' && key !== 'platform') {
                    try {
                        navigator[key] = this.originalNavigator[key];
                    } catch (e) {
                        // Some properties might be read-only, skip them
                    }
                }
            });
        }
    }

    assert(condition, message) {
        if (condition) {
            this.testResults.push({ status: 'PASS', message });
            console.log(`✓ ${message}`);
        } else {
            this.testResults.push({ status: 'FAIL', message });
            console.error(`✗ ${message}`);
        }
    }

    async runTests() {
        console.log('Running VoiceCapabilities Tests...\n');

        try {
            await this.testCapabilityDetection();
            await this.testVoiceRetrieval();
            await this.testMicrophoneAccess();
            await this.testBrowserImplementation();
            await this.testCapabilityReport();
            await this.testFallbackMessages();
            await this.testFeatureRecommendations();
        } catch (error) {
            console.error('Test suite error:', error);
        } finally {
            this.restoreMocks();
        }

        this.printResults();
    }

    async testCapabilityDetection() {
        console.log('Testing capability detection...');
        
        const capabilities = new VoiceCapabilities();
        const caps = capabilities.capabilities;

        this.assert(typeof caps === 'object', 'Capabilities should return an object');
        this.assert(typeof caps.speechRecognition === 'boolean', 'speechRecognition should be boolean');
        this.assert(typeof caps.speechSynthesis === 'boolean', 'speechSynthesis should be boolean');
        this.assert(typeof caps.mediaDevices === 'boolean', 'mediaDevices should be boolean');
        this.assert(typeof caps.audioContext === 'boolean', 'audioContext should be boolean');
        this.assert(typeof caps.voiceInputSupported === 'boolean', 'voiceInputSupported should be boolean');
        this.assert(typeof caps.voiceOutputSupported === 'boolean', 'voiceOutputSupported should be boolean');
        this.assert(typeof caps.fullVoiceSupported === 'boolean', 'fullVoiceSupported should be boolean');

        // Test with mocked environment
        this.assert(caps.speechRecognition === true, 'Should detect speech recognition');
        this.assert(caps.speechSynthesis === true, 'Should detect speech synthesis');
        this.assert(caps.voiceInputSupported === true, 'Should support voice input');
        this.assert(caps.voiceOutputSupported === true, 'Should support voice output');
        this.assert(caps.fullVoiceSupported === true, 'Should support full voice features');
    }

    async testVoiceRetrieval() {
        console.log('Testing voice retrieval...');
        
        const capabilities = new VoiceCapabilities();
        const voices = await capabilities.getAvailableVoices();

        this.assert(Array.isArray(voices), 'getAvailableVoices should return an array');
        this.assert(voices.length > 0, 'Should return available voices');
        this.assert(voices[0].name === 'Test Voice 1', 'Should return correct voice name');
        this.assert(voices[0].lang === 'en-US', 'Should return correct voice language');
    }

    async testMicrophoneAccess() {
        console.log('Testing microphone access...');
        
        const capabilities = new VoiceCapabilities();
        const hasAccess = await capabilities.testMicrophoneAccess();

        this.assert(typeof hasAccess === 'boolean', 'testMicrophoneAccess should return boolean');
        this.assert(hasAccess === true, 'Should have microphone access in mocked environment');
    }

    testBrowserImplementation() {
        console.log('Testing browser implementation...');
        
        const capabilities = new VoiceCapabilities();
        const impl = capabilities.getBrowserImplementation();

        this.assert(typeof impl === 'object', 'getBrowserImplementation should return object');
        this.assert(typeof impl.SpeechRecognition === 'function', 'Should return SpeechRecognition constructor');
        this.assert(typeof impl.SpeechSynthesisUtterance === 'function', 'Should return SpeechSynthesisUtterance constructor');
    }

    testCapabilityReport() {
        console.log('Testing capability report...');
        
        const capabilities = new VoiceCapabilities();
        const report = capabilities.getCapabilityReport();

        this.assert(typeof report === 'object', 'getCapabilityReport should return object');
        this.assert(typeof report.userAgent === 'string', 'Should include userAgent');
        this.assert(typeof report.platform === 'string', 'Should include platform');
        this.assert(typeof report.capabilities === 'object', 'Should include capabilities');
        this.assert(typeof report.browserInfo === 'object', 'Should include browserInfo');
        this.assert(typeof report.browserInfo.isChrome === 'boolean', 'Should detect Chrome');
        this.assert(typeof report.browserInfo.isMobile === 'boolean', 'Should detect mobile');
    }

    testFallbackMessages() {
        console.log('Testing fallback messages...');
        
        const capabilities = new VoiceCapabilities();
        
        const sttMessage = capabilities.getFallbackMessage('stt');
        const ttsMessage = capabilities.getFallbackMessage('tts');
        const micMessage = capabilities.getFallbackMessage('microphone');
        const generalMessage = capabilities.getFallbackMessage('unknown');

        this.assert(typeof sttMessage === 'string', 'STT fallback should be string');
        this.assert(sttMessage.length > 0, 'STT fallback should not be empty');
        this.assert(typeof ttsMessage === 'string', 'TTS fallback should be string');
        this.assert(ttsMessage.length > 0, 'TTS fallback should not be empty');
        this.assert(typeof micMessage === 'string', 'Microphone fallback should be string');
        this.assert(micMessage.length > 0, 'Microphone fallback should not be empty');
        this.assert(typeof generalMessage === 'string', 'General fallback should be string');
        this.assert(generalMessage.length > 0, 'General fallback should not be empty');
    }

    testFeatureRecommendations() {
        console.log('Testing feature recommendations...');
        
        const capabilities = new VoiceCapabilities();
        const recommendations = capabilities.getFeatureRecommendations();

        this.assert(typeof recommendations === 'object', 'getFeatureRecommendations should return object');
        this.assert(typeof recommendations.enableVoiceInput === 'boolean', 'Should recommend voice input');
        this.assert(typeof recommendations.enableVoiceOutput === 'boolean', 'Should recommend voice output');
        this.assert(typeof recommendations.showVoiceControls === 'boolean', 'Should recommend voice controls');
        this.assert(typeof recommendations.requireMicrophoneTest === 'boolean', 'Should recommend microphone test');
        this.assert(typeof recommendations.gracefulDegradation === 'boolean', 'Should recommend graceful degradation');

        // Test with mocked environment
        this.assert(recommendations.enableVoiceInput === true, 'Should enable voice input');
        this.assert(recommendations.enableVoiceOutput === true, 'Should enable voice output');
        this.assert(recommendations.showVoiceControls === true, 'Should show voice controls');
    }

    printResults() {
        console.log('\n=== VoiceCapabilities Test Results ===');
        
        const passed = this.testResults.filter(r => r.status === 'PASS').length;
        const failed = this.testResults.filter(r => r.status === 'FAIL').length;
        const total = this.testResults.length;

        console.log(`Total tests: ${total}`);
        console.log(`Passed: ${passed}`);
        console.log(`Failed: ${failed}`);
        console.log(`Success rate: ${((passed / total) * 100).toFixed(1)}%`);

        if (failed > 0) {
            console.log('\nFailed tests:');
            this.testResults
                .filter(r => r.status === 'FAIL')
                .forEach(r => console.log(`  - ${r.message}`));
        }

        return { passed, failed, total };
    }
}

// Run tests if this file is executed directly
if (typeof require !== 'undefined' && require.main === module) {
    // Load VoiceCapabilities class
    const VoiceCapabilities = require('../voice-capabilities.js');
    
    const test = new VoiceCapabilitiesTest();
    test.runTests().then(() => {
        process.exit(test.testResults.some(r => r.status === 'FAIL') ? 1 : 0);
    });
} else if (typeof window !== 'undefined') {
    // Browser environment
    window.VoiceCapabilitiesTest = VoiceCapabilitiesTest;
}

// Export for use in other test files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceCapabilitiesTest;
}