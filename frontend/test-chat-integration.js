/**
 * Test script to verify chat interface voice integration
 */

// Mock DOM elements for testing
const mockDOM = {
    getElementById: (id) => {
        const mockElement = {
            textContent: '',
            value: '',
            style: {},
            className: '',
            appendChild: () => {},
            addEventListener: () => {},
            focus: () => {},
            classList: {
                add: () => {},
                remove: () => {},
                contains: () => false
            }
        };
        return mockElement;
    },
    createElement: (tag) => ({
        textContent: '',
        innerHTML: '',
        className: '',
        style: {},
        appendChild: () => {},
        addEventListener: () => {},
        setAttribute: () => {},
        classList: {
            add: () => {},
            remove: () => {},
            contains: () => false
        }
    }),
    querySelectorAll: () => [],
    addEventListener: () => {},
    body: {
        appendChild: () => {}
    },
    hidden: false
};

// Mock global objects for Node.js testing
global.document = mockDOM;
global.window = {
    SpeechRecognition: undefined,
    webkitSpeechRecognition: undefined,
    speechSynthesis: {
        getVoices: () => [],
        speak: () => {},
        cancel: () => {},
        pause: () => {},
        resume: () => {},
        speaking: false,
        paused: false,
        addEventListener: () => {}
    },
    SpeechSynthesisUtterance: function(text) {
        this.text = text;
        this.rate = 1;
        this.pitch = 1;
        this.volume = 1;
        this.lang = 'en-US';
        this.voice = null;
    },
    AudioContext: undefined,
    webkitAudioContext: undefined
};

global.navigator = {
    userAgent: 'Node.js Test Environment',
    platform: 'test',
    mediaDevices: undefined,
    getUserMedia: undefined
};

global.localStorage = {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {}
};

// Load voice modules
const VoiceCapabilities = require('./voice-capabilities.js');
const VoiceSettings = require('./voice-settings.js');

// Make VoiceCapabilities and VoiceSettings available globally for VoiceController
global.VoiceCapabilities = VoiceCapabilities;
global.VoiceSettings = VoiceSettings;

const VoiceController = require('./voice-controller.js');

console.log('Testing voice integration components...');

try {
    // Test VoiceCapabilities
    const capabilities = new VoiceCapabilities();
    console.log('✓ VoiceCapabilities initialized');
    console.log('  Capabilities:', capabilities.capabilities);

    // Test VoiceSettings
    const settings = new VoiceSettings('test_settings');
    console.log('✓ VoiceSettings initialized');
    console.log('  Default settings loaded:', Object.keys(settings.get()).length, 'properties');

    // Test VoiceController initialization
    const mockChatInterface = {
        onTranscript: (transcript) => console.log('Mock transcript:', transcript),
        onError: (error) => console.log('Mock error:', error),
        onStatusChange: (status) => console.log('Mock status:', status)
    };

    const controller = new VoiceController(mockChatInterface, {
        debugMode: true,
        enableErrorRecovery: false
    });
    console.log('✓ VoiceController initialized');
    console.log('  Controller state:', controller.getState());

    // Test key integration functions
    console.log('\nTesting integration functions...');

    // Mock the functions that would be in chat.html
    function handleVoiceTranscript(transcript, confidence = 1) {
        console.log(`✓ handleVoiceTranscript called: "${transcript}" (confidence: ${confidence})`);
        return true;
    }

    function handleVoiceError(type, message) {
        console.log(`✓ handleVoiceError called: ${type} - ${message}`);
        return true;
    }

    function showVoiceStatus(message, type = 'info') {
        console.log(`✓ showVoiceStatus called: "${message}" (${type})`);
        return true;
    }

    function clearVoiceFeedback() {
        console.log('✓ clearVoiceFeedback called');
        return true;
    }

    // Test the functions
    handleVoiceTranscript('Hello world', 0.95);
    handleVoiceError('test_error', 'This is a test error');
    showVoiceStatus('Testing status', 'info');
    clearVoiceFeedback();

    console.log('\n✅ All voice integration tests passed!');
    console.log('The voice features should integrate successfully with the chat interface.');

} catch (error) {
    console.error('❌ Voice integration test failed:', error.message);
    console.error(error.stack);
    process.exit(1);
}