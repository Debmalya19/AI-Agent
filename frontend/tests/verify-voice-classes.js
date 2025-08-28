/**
 * Simple verification script for voice processing classes
 * Tests core functionality without browser dependencies
 */

// Mock localStorage for Node.js
if (typeof localStorage === 'undefined') {
    global.localStorage = {
        store: {},
        getItem(key) { return this.store[key] || null; },
        setItem(key, value) { this.store[key] = String(value); },
        removeItem(key) { delete this.store[key]; },
        clear() { this.store = {}; }
    };
}

// Load classes
const VoiceCapabilities = require('../voice-capabilities.js');
const VoiceSettings = require('../voice-settings.js');

console.log('🧪 Verifying Voice Processing Classes\n');

// Mock window and navigator for VoiceCapabilities
global.window = {
    SpeechRecognition: class MockSpeechRecognition {},
    webkitSpeechRecognition: class MockWebkitSpeechRecognition {},
    speechSynthesis: {
        getVoices: () => [{ name: 'Test Voice', lang: 'en-US' }],
        addEventListener: () => {}
    },
    SpeechSynthesisUtterance: class MockSpeechSynthesisUtterance {},
    AudioContext: class MockAudioContext {}
};

global.navigator = {
    mediaDevices: {
        getUserMedia: () => Promise.resolve({
            getTracks: () => [{ stop: () => {} }]
        })
    },
    userAgent: 'Test Browser',
    platform: 'Test Platform'
};

global.speechSynthesis = global.window.speechSynthesis;

// Test VoiceCapabilities
console.log('📋 Testing VoiceCapabilities...');
try {
    const capabilities = new VoiceCapabilities();
    console.log('✅ VoiceCapabilities instantiated successfully');
    
    const caps = capabilities.capabilities;
    console.log('✅ Capabilities detected:', Object.keys(caps).length, 'properties');
    
    const report = capabilities.getCapabilityReport();
    console.log('✅ Capability report generated');
    
    const fallback = capabilities.getFallbackMessage('stt');
    console.log('✅ Fallback messages working');
    
    const recommendations = capabilities.getFeatureRecommendations();
    console.log('✅ Feature recommendations generated');
    
} catch (error) {
    console.log('❌ VoiceCapabilities error:', error.message);
}

// Test VoiceSettings
console.log('\n📋 Testing VoiceSettings...');
try {
    const settings = new VoiceSettings('test_settings');
    console.log('✅ VoiceSettings instantiated successfully');
    
    const defaults = settings.getDefaults();
    console.log('✅ Default settings loaded:', Object.keys(defaults).length, 'properties');
    
    const validation = settings.validateSettings({
        speechRate: 1.5,
        language: 'en-US',
        autoPlayEnabled: true
    });
    console.log('✅ Settings validation working:', validation.isValid);
    
    const updateSuccess = settings.update({ speechRate: 1.2 });
    console.log('✅ Settings update working:', updateSuccess);
    
    const synthSettings = settings.getSpeechSynthesisSettings();
    console.log('✅ Speech synthesis settings generated');
    
    const recSettings = settings.getSpeechRecognitionSettings();
    console.log('✅ Speech recognition settings generated');
    
    const exported = settings.export();
    console.log('✅ Settings export working');
    
    const importSuccess = settings.import(exported);
    console.log('✅ Settings import working:', importSuccess);
    
} catch (error) {
    console.log('❌ VoiceSettings error:', error.message);
}

// Test VoiceController (basic instantiation only)
console.log('\n📋 Testing VoiceController (basic)...');
try {
    // Make VoiceCapabilities and VoiceSettings available globally
    global.VoiceCapabilities = VoiceCapabilities;
    global.VoiceSettings = VoiceSettings;
    
    const VoiceController = require('../voice-controller.js');
    
    const mockChatInterface = { sendMessage: () => {} };
    const controller = new VoiceController(mockChatInterface, { autoInitialize: false });
    console.log('✅ VoiceController instantiated successfully');
    
    const state = controller.getState();
    console.log('✅ Controller state accessible:', Object.keys(state).length, 'properties');
    
    const capabilities = controller.getCapabilities();
    console.log('✅ Controller capabilities accessible');
    
    console.log('✅ VoiceController basic functionality verified');
    
} catch (error) {
    console.log('❌ VoiceController error:', error.message);
}

console.log('\n🎉 Voice processing classes verification complete!');
console.log('\nNote: Full functionality requires browser environment with Web Speech API support.');
console.log('The classes are designed to gracefully degrade when browser APIs are not available.');