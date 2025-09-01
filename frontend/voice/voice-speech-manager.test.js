// Unit tests for VoiceSpeechManager
// Tests speech recognition functionality, error handling, and state management

// Mock Web Speech API
class MockSpeechRecognition {
    constructor() {
        this.continuous = false;
        this.interimResults = false;
        this.lang = 'en-US';
        this.maxAlternatives = 1;
        
        this.onstart = null;
        this.onresult = null;
        this.onerror = null;
        this.onend = null;
        this.onspeechstart = null;
        this.onspeechend = null;
        this.onnomatch = null;
        
        this.started = false;
    }
    
    start() {
        if (this.started) {
            throw new Error('Recognition already started');
        }
        this.started = true;
        setTimeout(() => {
            if (this.onstart) this.onstart();
        }, 10);
    }
    
    stop() {
        if (!this.started) return;
        this.started = false;
        setTimeout(() => {
            if (this.onend) this.onend();
        }, 10);
    }
    
    abort() {
        this.started = false;
        setTimeout(() => {
            if (this.onend) this.onend();
        }, 10);
    }
    
    // Test helper methods
    simulateResult(transcript, isFinal = true) {
        if (!this.started || !this.onresult) return;
        
        const mockEvent = {
            resultIndex: 0,
            results: [{
                0: { transcript },
                isFinal,
                length: 1
            }],
            length: 1
        };
        
        this.onresult(mockEvent);
    }
    
    simulateError(error, message = '') {
        if (!this.started || !this.onerror) return;
        
        const mockEvent = { error, message };
        this.onerror(mockEvent);
    }
    
    simulateSpeechStart() {
        if (this.onspeechstart) this.onspeechstart();
    }
    
    simulateSpeechEnd() {
        if (this.onspeechend) this.onspeechend();
    }
}

class MockSpeechSynthesisUtterance {
    constructor(text) {
        this.text = text;
        this.lang = 'en-US';
        this.rate = 1.0;
        this.pitch = 1.0;
        this.volume = 1.0;
        this.voice = null;
        
        this.onstart = null;
        this.onend = null;
        this.onerror = null;
    }
}

class MockSpeechSynthesis {
    constructor() {
        this.speaking = false;
        this.pending = false;
        this.paused = false;
        this.currentUtterance = null;
    }
    
    speak(utterance) {
        this.speaking = true;
        this.currentUtterance = utterance;
        
        setTimeout(() => {
            if (utterance.onstart) utterance.onstart();
        }, 10);
        
        setTimeout(() => {
            this.speaking = false;
            this.currentUtterance = null;
            if (utterance.onend) utterance.onend();
        }, 100);
    }
    
    cancel() {
        this.speaking = false;
        this.currentUtterance = null;
    }
    
    pause() {
        this.paused = true;
    }
    
    resume() {
        this.paused = false;
    }
}

// Mock navigator.mediaDevices
const mockMediaDevices = {
    getUserMedia: jest.fn()
};

// Mock navigator.permissions
const mockPermissions = {
    query: jest.fn()
};

// Setup global mocks before importing
global.window = {
    SpeechRecognition: MockSpeechRecognition,
    webkitSpeechRecognition: MockSpeechRecognition,
    SpeechSynthesisUtterance: MockSpeechSynthesisUtterance,
    speechSynthesis: new MockSpeechSynthesis(),
    location: {
        protocol: 'https:',
        hostname: 'localhost'
    }
};

global.navigator = {
    mediaDevices: mockMediaDevices,
    permissions: mockPermissions
};

// Mock console methods to reduce noise in tests
global.console = {
    ...console,
    log: jest.fn(),
    warn: jest.fn(),
    error: jest.fn()
};

// Import the class to test
const VoiceSpeechManager = require('./voice-speech-manager.js');

describe('VoiceSpeechManager', () => {
    let speechManager;
    let mockOnTranscript;
    let mockOnError;
    let mockOnStateChange;
    
    beforeEach(() => {
        // Reset mocks
        jest.clearAllMocks();
        mockMediaDevices.getUserMedia.mockResolvedValue({
            getTracks: () => [{ stop: jest.fn() }]
        });
        mockPermissions.query.mockResolvedValue({ state: 'granted' });
        
        // Reset global mocks
        global.window.speechSynthesis = new MockSpeechSynthesis();
        
        // Create mock callbacks
        mockOnTranscript = jest.fn();
        mockOnError = jest.fn();
        mockOnStateChange = jest.fn();
        
        // Create speech manager instance
        speechManager = new VoiceSpeechManager(mockOnTranscript, mockOnError, mockOnStateChange);
    });
    
    afterEach(() => {
        if (speechManager) {
            speechManager.cleanup();
        }
    });
    
    describe('Initialization', () => {
        test('should initialize successfully with valid environment', () => {
            expect(speechManager).toBeDefined();
            expect(speechManager.getCurrentState()).toBe('idle');
            expect(speechManager.recognition).toBeDefined();
        });
        
        test('should detect browser capabilities correctly', () => {
            const capabilities = speechManager.getCapabilities();
            
            expect(capabilities.speechRecognition).toBe(true);
            expect(capabilities.speechSynthesis).toBe(true);
            expect(capabilities.secureContext).toBe(true);
            expect(capabilities.supported).toBe(true);
        });
        
        test('should handle missing speech recognition API', () => {
            // Temporarily remove speech recognition
            const originalSR = global.window.SpeechRecognition;
            const originalWSR = global.window.webkitSpeechRecognition;
            delete global.window.SpeechRecognition;
            delete global.window.webkitSpeechRecognition;
            
            const manager = new VoiceSpeechManager(mockOnTranscript, mockOnError, mockOnStateChange);
            
            expect(mockOnError).toHaveBeenCalledWith(
                'speech-recognition-unavailable',
                expect.stringContaining('Speech recognition API not available')
            );
            
            // Restore
            global.window.SpeechRecognition = originalSR;
            global.window.webkitSpeechRecognition = originalWSR;
        });
        
        test('should handle insecure context', () => {
            // Temporarily change to insecure context
            const originalProtocol = global.window.location.protocol;
            global.window.location.protocol = 'http:';
            global.window.location.hostname = 'example.com';
            
            const manager = new VoiceSpeechManager(mockOnTranscript, mockOnError, mockOnStateChange);
            
            expect(mockOnError).toHaveBeenCalledWith(
                'insecure-context',
                'Speech recognition requires HTTPS or localhost'
            );
            
            // Restore
            global.window.location.protocol = originalProtocol;
            global.window.location.hostname = 'localhost';
        });
    });
    
    describe('Speech Recognition', () => {
        test('should start listening successfully', async () => {
            const result = await speechManager.startListening();
            
            expect(result).toBe(true);
            expect(speechManager.isListening()).toBe(true);
            expect(speechManager.getCurrentState()).toBe('listening');
            expect(mockOnStateChange).toHaveBeenCalledWith('listening', 'idle');
        });
        
        test('should handle microphone permission granted', async () => {
            mockPermissions.query.mockResolvedValue({ state: 'granted' });
            
            const result = await speechManager.startListening();
            
            expect(result).toBe(true);
            expect(mockMediaDevices.getUserMedia).not.toHaveBeenCalled(); // Should not request if already granted
        });
        
        test('should handle microphone permission denied', async () => {
            mockPermissions.query.mockResolvedValue({ state: 'denied' });
            
            const result = await speechManager.startListening();
            
            expect(result).toBe(false);
            expect(mockOnError).toHaveBeenCalledWith(
                'microphone-denied',
                expect.stringContaining('Microphone access denied')
            );
        });
        
        test('should request microphone permission when prompted', async () => {
            mockPermissions.query.mockResolvedValue({ state: 'prompt' });
            mockMediaDevices.getUserMedia.mockResolvedValue({
                getTracks: () => [{ stop: jest.fn() }]
            });
            
            const result = await speechManager.startListening();
            
            expect(result).toBe(true);
            expect(mockMediaDevices.getUserMedia).toHaveBeenCalledWith({ audio: true });
        });
        
        test('should handle microphone access failure', async () => {
            mockPermissions.query.mockResolvedValue({ state: 'prompt' });
            mockMediaDevices.getUserMedia.mockRejectedValue(new Error('NotAllowedError'));
            
            const result = await speechManager.startListening();
            
            expect(result).toBe(false);
            expect(mockOnError).toHaveBeenCalled();
        });
        
        test('should stop listening successfully', async () => {
            await speechManager.startListening();
            speechManager.stopListening();
            
            expect(speechManager.isListening()).toBe(false);
            expect(speechManager.getCurrentState()).toBe('idle');
        });
        
        test('should handle speech recognition results', async () => {
            await speechManager.startListening();
            
            // Simulate interim result
            speechManager.recognition.simulateResult('Hello', false);
            expect(mockOnTranscript).toHaveBeenCalledWith('Hello', false);
            
            // Simulate final result
            speechManager.recognition.simulateResult('Hello world', true);
            expect(mockOnTranscript).toHaveBeenCalledWith('Hello world', true);
        });
        
        test('should handle speech recognition errors', async () => {
            await speechManager.startListening();
            
            speechManager.recognition.simulateError('not-allowed');
            
            expect(mockOnError).toHaveBeenCalledWith(
                'not-allowed',
                expect.stringContaining('Microphone access denied')
            );
            expect(speechManager.getCurrentState()).toBe('error');
        });
        
        test('should handle no speech detected', async () => {
            await speechManager.startListening();
            
            speechManager.recognition.simulateError('no-speech');
            
            expect(mockOnError).toHaveBeenCalledWith(
                'no-speech',
                expect.stringContaining('No speech detected')
            );
        });
        
        test('should handle network errors', async () => {
            await speechManager.startListening();
            
            speechManager.recognition.simulateError('network');
            
            expect(mockOnError).toHaveBeenCalledWith(
                'network',
                expect.stringContaining('Network error')
            );
        });
        
        test('should prevent starting when already listening', async () => {
            await speechManager.startListening();
            const result = await speechManager.startListening();
            
            expect(result).toBe(false);
        });
        
        test('should handle maximum recording time', async () => {
            // Set short timeout for testing
            speechManager.updateConfig({ maxRecordingTime: 100 });
            
            await speechManager.startListening();
            
            // Wait for timeout
            await new Promise(resolve => setTimeout(resolve, 150));
            
            expect(mockOnError).toHaveBeenCalledWith(
                'max-recording-time',
                'Maximum recording time reached'
            );
        });
    });
    
    describe('Text-to-Speech', () => {
        test('should speak text successfully', () => {
            const result = speechManager.speakText('Hello world');
            
            expect(result).toBe(true);
            expect(speechManager.isSpeaking()).toBe(true);
            expect(speechManager.getCurrentState()).toBe('speaking');
        });
        
        test('should handle empty text', () => {
            const result = speechManager.speakText('');
            
            expect(result).toBe(false);
        });
        
        test('should handle invalid text type', () => {
            const result = speechManager.speakText(null);
            
            expect(result).toBe(false);
        });
        
        test('should configure speech options', () => {
            const options = {
                rate: 1.5,
                pitch: 0.8,
                volume: 0.9,
                lang: 'en-GB'
            };
            
            speechManager.speakText('Hello', options);
            
            const utterance = global.window.speechSynthesis.currentUtterance;
            expect(utterance.rate).toBe(1.5);
            expect(utterance.pitch).toBe(0.8);
            expect(utterance.volume).toBe(0.9);
            expect(utterance.lang).toBe('en-GB');
        });
        
        test('should stop speaking', () => {
            speechManager.speakText('Hello world');
            expect(speechManager.isSpeaking()).toBe(true);
            
            speechManager.stopSpeaking();
            expect(speechManager.isSpeaking()).toBe(false);
        });
        
        test('should handle synthesis unavailable', () => {
            // Temporarily remove synthesis
            const originalSynthesis = global.window.speechSynthesis;
            global.window.speechSynthesis = null;
            
            const manager = new VoiceSpeechManager(mockOnTranscript, mockOnError, mockOnStateChange);
            const result = manager.speakText('Hello');
            
            expect(result).toBe(false);
            expect(mockOnError).toHaveBeenCalledWith(
                'synthesis-unavailable',
                expect.stringContaining('Text-to-speech not available')
            );
            
            // Restore
            global.window.speechSynthesis = originalSynthesis;
        });
    });
    
    describe('State Management', () => {
        test('should change state correctly', () => {
            speechManager.setState('listening');
            
            expect(speechManager.getCurrentState()).toBe('listening');
            expect(mockOnStateChange).toHaveBeenCalledWith('listening', 'idle');
        });
        
        test('should not trigger callback for same state', () => {
            speechManager.setState('idle');
            
            expect(mockOnStateChange).not.toHaveBeenCalled();
        });
        
        test('should auto-recover from error state', async () => {
            speechManager.setState('error');
            
            // Wait for auto-recovery timeout
            await new Promise(resolve => setTimeout(resolve, 3100));
            
            expect(speechManager.getCurrentState()).toBe('idle');
        });
    });
    
    describe('Configuration', () => {
        test('should update configuration', () => {
            const newConfig = {
                language: 'es-ES',
                continuous: false,
                silenceTimeout: 5000
            };
            
            speechManager.updateConfig(newConfig);
            
            expect(speechManager.config.language).toBe('es-ES');
            expect(speechManager.config.continuous).toBe(false);
            expect(speechManager.config.silenceTimeout).toBe(5000);
            expect(speechManager.recognition.lang).toBe('es-ES');
            expect(speechManager.recognition.continuous).toBe(false);
        });
    });
    
    describe('Cleanup', () => {
        test('should cleanup properly', async () => {
            await speechManager.startListening();
            speechManager.speakText('Hello');
            
            speechManager.cleanup();
            
            expect(speechManager.getCurrentState()).toBe('idle');
            expect(speechManager.isListening()).toBe(false);
            expect(speechManager.isSpeaking()).toBe(false);
            expect(speechManager.recognition).toBe(null);
        });
    });
    
    describe('Error Handling', () => {
        test('should handle various speech recognition errors', async () => {
            await speechManager.startListening();
            
            const errorCases = [
                ['audio-capture', 'No microphone found'],
                ['service-not-allowed', 'Speech service not available'],
                ['bad-grammar', 'Speech recognition grammar error'],
                ['language-not-supported', 'Selected language not supported']
            ];
            
            for (const [errorCode, expectedMessage] of errorCases) {
                speechManager.recognition.simulateError(errorCode);
                expect(mockOnError).toHaveBeenCalledWith(
                    errorCode,
                    expect.stringContaining(expectedMessage)
                );
            }
        });
        
        test('should handle unknown errors gracefully', async () => {
            await speechManager.startListening();
            
            speechManager.recognition.simulateError('unknown-error');
            
            expect(mockOnError).toHaveBeenCalledWith(
                'unknown-error',
                expect.stringContaining('Speech recognition error: unknown-error')
            );
        });
    });
});

// Export for potential use in other test files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        MockSpeechRecognition,
        MockSpeechSynthesis,
        MockSpeechSynthesisUtterance
    };
}