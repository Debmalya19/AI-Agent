/**
 * Unit Tests for VoiceController Class
 * Tests voice input/output functionality with mocked Web Speech API
 */

// Mock Web Speech API classes
class MockSpeechRecognition {
    constructor() {
        this.lang = 'en-US';
        this.continuous = false;
        this.interimResults = false;
        this.maxAlternatives = 1;
        this.onstart = null;
        this.onresult = null;
        this.onerror = null;
        this.onend = null;
        this.onspeechstart = null;
        this.onspeechend = null;
        this.onnomatch = null;
        this._isStarted = false;
    }

    start() {
        if (this._isStarted) {
            throw new Error('already started');
        }
        this._isStarted = true;
        setTimeout(() => {
            if (this.onstart) this.onstart();
        }, 10);
    }

    stop() {
        if (this._isStarted) {
            this._isStarted = false;
            setTimeout(() => {
                if (this.onend) this.onend();
            }, 10);
        }
    }

    // Test helper methods
    _simulateResult(transcript, isFinal = true, confidence = 0.9) {
        if (this.onresult) {
            const event = {
                resultIndex: 0,
                results: [{
                    0: { transcript, confidence },
                    isFinal,
                    length: 1
                }]
            };
            this.onresult(event);
        }
    }

    _simulateError(error) {
        if (this.onerror) {
            this.onerror({ error });
        }
    }
}

class MockSpeechSynthesisUtterance {
    constructor(text) {
        this.text = text;
        this.rate = 1;
        this.pitch = 1;
        this.volume = 1;
        this.lang = 'en-US';
        this.voice = null;
        this.onstart = null;
        this.onend = null;
        this.onerror = null;
        this.onpause = null;
        this.onresume = null;
    }
}

class MockSpeechSynthesis {
    constructor() {
        this.speaking = false;
        this.paused = false;
        this.pending = false;
        this._voices = [
            { name: 'Test Voice 1', lang: 'en-US', voiceURI: 'test1' },
            { name: 'Test Voice 2', lang: 'es-ES', voiceURI: 'test2' }
        ];
        this._currentUtterance = null;
    }

    speak(utterance) {
        this.speaking = true;
        this._currentUtterance = utterance;
        setTimeout(() => {
            if (utterance.onstart) utterance.onstart();
        }, 10);
        setTimeout(() => {
            this.speaking = false;
            this._currentUtterance = null;
            if (utterance.onend) utterance.onend();
        }, 100);
    }

    cancel() {
        if (this._currentUtterance) {
            this.speaking = false;
            this._currentUtterance = null;
        }
    }

    pause() {
        if (this.speaking) {
            this.paused = true;
            if (this._currentUtterance && this._currentUtterance.onpause) {
                this._currentUtterance.onpause();
            }
        }
    }

    resume() {
        if (this.paused) {
            this.paused = false;
            if (this._currentUtterance && this._currentUtterance.onresume) {
                this._currentUtterance.onresume();
            }
        }
    }

    getVoices() {
        return this._voices;
    }

    addEventListener() {}
}

// Mock classes for dependencies
class MockVoiceCapabilities {
    constructor() {
        this.capabilities = {
            speechRecognition: true,
            speechSynthesis: true,
            voiceInputSupported: true,
            voiceOutputSupported: true,
            fullVoiceSupported: true
        };
    }

    getCapabilityReport() {
        return {
            capabilities: this.capabilities,
            browserInfo: { isChrome: true, isMobile: false }
        };
    }

    getBrowserImplementation() {
        return {
            SpeechRecognition: MockSpeechRecognition,
            SpeechSynthesisUtterance: MockSpeechSynthesisUtterance
        };
    }

    async getAvailableVoices() {
        return [
            { name: 'Test Voice 1', lang: 'en-US', voiceURI: 'test1' },
            { name: 'Test Voice 2', lang: 'es-ES', voiceURI: 'test2' }
        ];
    }

    async testMicrophoneAccess() {
        return true;
    }

    getFallbackMessage(feature) {
        return `${feature} not supported`;
    }
}

class MockVoiceSettings {
    constructor() {
        this.settings = {
            speechRate: 1.0,
            speechPitch: 1.0,
            speechVolume: 1.0,
            language: 'en-US',
            voiceName: 'default',
            continuousRecognition: false,
            interimResults: true,
            maxAlternatives: 1,
            maxRecordingTime: 60000
        };
        this.listeners = new Set();
    }

    get() {
        return { ...this.settings };
    }

    getValue(key) {
        return this.settings[key];
    }

    update(updates) {
        Object.assign(this.settings, updates);
        return true;
    }

    getSpeechSynthesisSettings() {
        return {
            rate: this.settings.speechRate,
            pitch: this.settings.speechPitch,
            volume: this.settings.speechVolume,
            lang: this.settings.language,
            voice: this.settings.voiceName !== 'default' ? this.settings.voiceName : null
        };
    }

    getSpeechRecognitionSettings() {
        return {
            lang: this.settings.language,
            continuous: this.settings.continuousRecognition,
            interimResults: this.settings.interimResults,
            maxAlternatives: this.settings.maxAlternatives
        };
    }

    addListener(listener) {
        this.listeners.add(listener);
    }

    removeListener(listener) {
        this.listeners.delete(listener);
    }
}

// Test suite
class VoiceControllerTest {
    constructor() {
        this.testResults = [];
        this.setupMocks();
    }

    setupMocks() {
        // Mock global objects
        this.mockSpeechSynthesis = new MockSpeechSynthesis();
        
        if (typeof window === 'undefined') {
            global.window = {
                SpeechRecognition: MockSpeechRecognition,
                webkitSpeechRecognition: MockSpeechRecognition,
                speechSynthesis: this.mockSpeechSynthesis,
                SpeechSynthesisUtterance: MockSpeechSynthesisUtterance
            };
            global.VoiceCapabilities = MockVoiceCapabilities;
            global.VoiceSettings = MockVoiceSettings;
            global.speechSynthesis = this.mockSpeechSynthesis;
        } else {
            this.originalWindow = { ...window };
            window.SpeechRecognition = MockSpeechRecognition;
            window.webkitSpeechRecognition = MockSpeechRecognition;
            window.speechSynthesis = this.mockSpeechSynthesis;
            window.SpeechSynthesisUtterance = MockSpeechSynthesisUtterance;
            window.VoiceCapabilities = MockVoiceCapabilities;
            window.VoiceSettings = MockVoiceSettings;
        }
    }

    restoreMocks() {
        if (typeof window !== 'undefined' && this.originalWindow) {
            Object.assign(window, this.originalWindow);
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
        console.log('Running VoiceController Tests...\n');

        try {
            await this.testInitialization();
            await this.testVoiceRecording();
            await this.testSpeechSynthesis();
            await this.testEventHandling();
            await this.testErrorHandling();
            await this.testSettingsIntegration();
            await this.testStateManagement();
            await this.testQueueManagement();
        } catch (error) {
            console.error('Test suite error:', error);
        } finally {
            this.restoreMocks();
        }

        this.printResults();
    }

    async testInitialization() {
        console.log('Testing initialization...');
        
        const mockChatInterface = { sendMessage: () => {} };
        const controller = new VoiceController(mockChatInterface);

        // Wait for initialization
        await new Promise(resolve => setTimeout(resolve, 50));

        this.assert(controller.chatInterface === mockChatInterface, 'should store chat interface reference');
        this.assert(typeof controller.capabilities === 'object', 'should initialize capabilities');
        this.assert(typeof controller.settings === 'object', 'should initialize settings');
        this.assert(controller.isRecording === false, 'should initialize recording state as false');
        this.assert(controller.isSpeaking === false, 'should initialize speaking state as false');
        this.assert(Array.isArray(controller.speechQueue), 'should initialize speech queue');
        this.assert(controller.speechQueue.length === 0, 'speech queue should be empty initially');
    }

    async testVoiceRecording() {
        console.log('Testing voice recording...');
        
        const mockChatInterface = { sendMessage: () => {} };
        const controller = new VoiceController(mockChatInterface);
        
        // Wait for initialization
        await new Promise(resolve => setTimeout(resolve, 50));

        let recordingStarted = false;
        let recordingStopped = false;
        let finalResult = null;

        controller.addEventListener('recording_started', () => {
            recordingStarted = true;
        });

        controller.addEventListener('recording_stopped', () => {
            recordingStopped = true;
        });

        controller.addEventListener('final_result', (data) => {
            finalResult = data;
        });

        // Test start recording
        const startSuccess = await controller.startRecording();
        this.assert(startSuccess === true, 'startRecording should return true');
        
        // Wait for recording to start
        await new Promise(resolve => setTimeout(resolve, 20));
        this.assert(recordingStarted === true, 'should emit recording_started event');
        this.assert(controller.isRecording === true, 'should set isRecording to true');

        // Simulate speech result
        if (controller.recognition) {
            controller.recognition._simulateResult('Hello world', true, 0.9);
        }

        // Wait for result processing
        await new Promise(resolve => setTimeout(resolve, 20));
        this.assert(finalResult !== null, 'should receive final result');
        this.assert(finalResult.transcript === 'Hello world', 'should receive correct transcript');

        // Test stop recording
        controller.stopRecording();
        
        // Wait for recording to stop
        await new Promise(resolve => setTimeout(resolve, 20));
        this.assert(recordingStopped === true, 'should emit recording_stopped event');
        this.assert(controller.isRecording === false, 'should set isRecording to false');
    }

    async testSpeechSynthesis() {
        console.log('Testing speech synthesis...');
        
        const mockChatInterface = { sendMessage: () => {} };
        const controller = new VoiceController(mockChatInterface);
        
        // Wait for initialization
        await new Promise(resolve => setTimeout(resolve, 50));

        let speechStarted = false;
        let speechEnded = false;

        controller.addEventListener('speech_started', () => {
            speechStarted = true;
        });

        controller.addEventListener('speech_ended', () => {
            speechEnded = true;
        });

        // Test play response
        const playSuccess = await controller.playResponse('Hello, this is a test message');
        this.assert(playSuccess === true, 'playResponse should return true');

        // Wait for speech to start
        await new Promise(resolve => setTimeout(resolve, 20));
        this.assert(speechStarted === true, 'should emit speech_started event');
        this.assert(controller.isSpeaking === true, 'should set isSpeaking to true');

        // Wait for speech to end
        await new Promise(resolve => setTimeout(resolve, 120));
        this.assert(speechEnded === true, 'should emit speech_ended event');
        this.assert(controller.isSpeaking === false, 'should set isSpeaking to false');

        // Test playback controls
        await controller.playResponse('Another test message');
        await new Promise(resolve => setTimeout(resolve, 20));
        
        controller.pausePlayback();
        this.assert(this.mockSpeechSynthesis.paused === true, 'should pause speech synthesis');

        controller.resumePlayback();
        this.assert(this.mockSpeechSynthesis.paused === false, 'should resume speech synthesis');

        controller.stopPlayback();
        this.assert(this.mockSpeechSynthesis.speaking === false, 'should stop speech synthesis');
    }

    async testEventHandling() {
        console.log('Testing event handling...');
        
        const mockChatInterface = { sendMessage: () => {} };
        const controller = new VoiceController(mockChatInterface);
        
        // Wait for initialization
        await new Promise(resolve => setTimeout(resolve, 50));

        let eventReceived = false;
        let eventData = null;

        // Test addEventListener
        const testListener = (data) => {
            eventReceived = true;
            eventData = data;
        };

        controller.addEventListener('test_event', testListener);
        controller.emit('test_event', { message: 'test data' });

        this.assert(eventReceived === true, 'should call event listener');
        this.assert(eventData.message === 'test data', 'should pass correct event data');

        // Test removeEventListener
        eventReceived = false;
        controller.removeEventListener('test_event', testListener);
        controller.emit('test_event', { message: 'test data 2' });

        this.assert(eventReceived === false, 'should not call removed listener');
    }

    async testErrorHandling() {
        console.log('Testing error handling...');
        
        const mockChatInterface = { sendMessage: () => {} };
        const controller = new VoiceController(mockChatInterface);
        
        // Wait for initialization
        await new Promise(resolve => setTimeout(resolve, 50));

        let errorReceived = false;
        let errorData = null;

        controller.addEventListener('error', (data) => {
            errorReceived = true;
            errorData = data;
        });

        // Test recognition error
        if (controller.recognition) {
            controller.recognition._simulateError('no-speech');
        }

        await new Promise(resolve => setTimeout(resolve, 20));
        this.assert(errorReceived === true, 'should emit error event');
        this.assert(errorData.type === 'speech_recognition', 'should have correct error type');
        this.assert(errorData.error === 'no-speech', 'should have correct error code');

        // Test invalid text for synthesis
        errorReceived = false;
        const invalidSuccess = await controller.playResponse('');
        this.assert(invalidSuccess === false, 'should return false for empty text');

        const nullSuccess = await controller.playResponse(null);
        this.assert(nullSuccess === false, 'should return false for null text');
    }

    async testSettingsIntegration() {
        console.log('Testing settings integration...');
        
        const mockChatInterface = { sendMessage: () => {} };
        const controller = new VoiceController(mockChatInterface);
        
        // Wait for initialization
        await new Promise(resolve => setTimeout(resolve, 50));

        // Test settings update
        const updateSuccess = controller.updateSettings({
            speechRate: 1.5,
            language: 'es-ES'
        });

        this.assert(updateSuccess === true, 'updateSettings should return true');
        this.assert(controller.settings.getValue('speechRate') === 1.5, 'should update speech rate');
        this.assert(controller.settings.getValue('language') === 'es-ES', 'should update language');

        // Test recognition settings update
        if (controller.recognition) {
            this.assert(controller.recognition.lang === 'es-ES', 'should update recognition language');
        }
    }

    async testStateManagement() {
        console.log('Testing state management...');
        
        const mockChatInterface = { sendMessage: () => {} };
        const controller = new VoiceController(mockChatInterface);
        
        // Wait for initialization
        await new Promise(resolve => setTimeout(resolve, 50));

        // Test getState
        const initialState = controller.getState();
        this.assert(typeof initialState === 'object', 'getState should return object');
        this.assert(initialState.isRecording === false, 'should report correct recording state');
        this.assert(initialState.isSpeaking === false, 'should report correct speaking state');
        this.assert(initialState.queueLength === 0, 'should report correct queue length');
        this.assert(typeof initialState.capabilities === 'object', 'should include capabilities');
        this.assert(typeof initialState.settings === 'object', 'should include settings');

        // Test getCapabilities
        const capabilities = controller.getCapabilities();
        this.assert(typeof capabilities === 'object', 'getCapabilities should return object');
        this.assert(capabilities.voiceInputSupported === true, 'should report voice input support');

        // Test getAvailableVoices
        const voices = controller.getAvailableVoices();
        this.assert(Array.isArray(voices), 'getAvailableVoices should return array');
    }

    async testQueueManagement() {
        console.log('Testing queue management...');
        
        const mockChatInterface = { sendMessage: () => {} };
        const controller = new VoiceController(mockChatInterface);
        
        // Wait for initialization
        await new Promise(resolve => setTimeout(resolve, 50));

        let queuedCount = 0;
        controller.addEventListener('speech_queued', () => {
            queuedCount++;
        });

        // Start first speech
        await controller.playResponse('First message');
        await new Promise(resolve => setTimeout(resolve, 20));

        // Queue additional messages while speaking
        await controller.playResponse('Second message');
        await controller.playResponse('Third message');

        this.assert(queuedCount === 2, 'should queue messages while speaking');
        this.assert(controller.speechQueue.length === 2, 'should have correct queue length');

        // Wait for all messages to complete
        await new Promise(resolve => setTimeout(resolve, 400));
        this.assert(controller.speechQueue.length === 0, 'should empty queue after completion');
    }

    printResults() {
        console.log('\n=== VoiceController Test Results ===');
        
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
    // Load required classes
    const VoiceController = require('../voice-controller.js');
    
    const test = new VoiceControllerTest();
    test.runTests().then(() => {
        process.exit(test.testResults.some(r => r.status === 'FAIL') ? 1 : 0);
    });
} else if (typeof window !== 'undefined') {
    // Browser environment
    window.VoiceControllerTest = VoiceControllerTest;
}

// Export for use in other test files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceControllerTest;
}