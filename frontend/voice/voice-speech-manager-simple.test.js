// Simplified unit tests for VoiceSpeechManager core functionality
// Tests the main methods and error handling without complex mocking

describe('VoiceSpeechManager Core Functionality', () => {
    // Mock the Web Speech API
    const mockRecognition = {
        start: jest.fn(),
        stop: jest.fn(),
        abort: jest.fn(),
        continuous: false,
        interimResults: false,
        lang: 'en-US',
        maxAlternatives: 1,
        onstart: null,
        onresult: null,
        onerror: null,
        onend: null,
        onspeechstart: null,
        onspeechend: null,
        onnomatch: null
    };
    
    const mockSynthesis = {
        speak: jest.fn(),
        cancel: jest.fn(),
        pause: jest.fn(),
        resume: jest.fn(),
        speaking: false,
        pending: false,
        paused: false
    };
    
    const mockUtterance = {
        text: '',
        lang: 'en-US',
        rate: 1.0,
        pitch: 1.0,
        volume: 1.0,
        voice: null,
        onstart: null,
        onend: null,
        onerror: null
    };
    
    // Mock global objects
    global.window = {
        SpeechRecognition: jest.fn(() => mockRecognition),
        webkitSpeechRecognition: jest.fn(() => mockRecognition),
        SpeechSynthesisUtterance: jest.fn(() => mockUtterance),
        speechSynthesis: mockSynthesis,
        location: {
            protocol: 'https:',
            hostname: 'localhost'
        }
    };
    
    global.navigator = {
        mediaDevices: {
            getUserMedia: jest.fn().mockResolvedValue({
                getTracks: () => [{ stop: jest.fn() }]
            })
        },
        permissions: {
            query: jest.fn().mockResolvedValue({ state: 'granted' })
        }
    };
    
    // Import after mocking
    const VoiceSpeechManager = require('./voice-speech-manager.js');
    
    let speechManager;
    let mockOnTranscript;
    let mockOnError;
    let mockOnStateChange;
    
    beforeEach(() => {
        jest.clearAllMocks();
        
        mockOnTranscript = jest.fn();
        mockOnError = jest.fn();
        mockOnStateChange = jest.fn();
        
        speechManager = new VoiceSpeechManager(mockOnTranscript, mockOnError, mockOnStateChange);
    });
    
    afterEach(() => {
        if (speechManager) {
            speechManager.cleanup();
        }
    });
    
    test('should create instance with callbacks', () => {
        expect(speechManager).toBeDefined();
        expect(speechManager.onTranscript).toBe(mockOnTranscript);
        expect(speechManager.onError).toBe(mockOnError);
        expect(speechManager.onStateChange).toBe(mockOnStateChange);
    });
    
    test('should detect speech recognition capability', () => {
        expect(speechManager.hasSpeechRecognition()).toBe(true);
    });
    
    test('should detect speech synthesis capability', () => {
        expect(speechManager.hasSpeechSynthesis()).toBe(true);
    });
    
    test('should detect secure context', () => {
        expect(speechManager.isSecureContext()).toBe(true);
    });
    
    test('should detect media devices capability', () => {
        expect(speechManager.hasMediaDevices()).toBe(true);
    });
    
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
    });
    
    test('should handle state changes', () => {
        speechManager.setState('listening');
        expect(mockOnStateChange).toHaveBeenCalledWith('listening', expect.any(String));
        
        speechManager.setState('speaking');
        expect(mockOnStateChange).toHaveBeenCalledWith('speaking', 'listening');
    });
    
    test('should not trigger state change callback for same state', () => {
        const currentState = speechManager.getCurrentState();
        speechManager.setState(currentState);
        expect(mockOnStateChange).not.toHaveBeenCalled();
    });
    
    test('should handle transcript callback', () => {
        speechManager.handleTranscript('Hello world', true);
        expect(mockOnTranscript).toHaveBeenCalledWith('Hello world', true);
    });
    
    test('should handle error callback', () => {
        speechManager.handleError('test-error', 'Test error message');
        expect(mockOnError).toHaveBeenCalledWith('test-error', 'Test error message');
    });
    
    test('should validate text input for speech synthesis', () => {
        // Valid text
        expect(speechManager.speakText('Hello')).toBe(true);
        
        // Invalid inputs
        expect(speechManager.speakText('')).toBe(false);
        expect(speechManager.speakText(null)).toBe(false);
        expect(speechManager.speakText(undefined)).toBe(false);
    });
    
    test('should handle speech synthesis configuration', () => {
        const options = {
            rate: 1.5,
            pitch: 0.8,
            volume: 0.9,
            lang: 'en-GB'
        };
        
        speechManager.speakText('Hello', options);
        
        expect(global.window.SpeechSynthesisUtterance).toHaveBeenCalledWith('Hello');
        expect(mockSynthesis.speak).toHaveBeenCalled();
    });
    
    test('should stop speech synthesis', () => {
        speechManager.speakText('Hello world');
        speechManager.stopSpeaking();
        
        expect(mockSynthesis.cancel).toHaveBeenCalled();
    });
    
    test('should handle recognition result processing', () => {
        const mockEvent = {
            resultIndex: 0,
            results: [{
                0: { transcript: 'Hello world' },
                isFinal: true,
                length: 1
            }],
            length: 1
        };
        
        speechManager.handleRecognitionResult(mockEvent);
        expect(mockOnTranscript).toHaveBeenCalledWith('Hello world', true);
    });
    
    test('should handle interim recognition results', () => {
        const mockEvent = {
            resultIndex: 0,
            results: [{
                0: { transcript: 'Hello' },
                isFinal: false,
                length: 1
            }],
            length: 1
        };
        
        speechManager.handleRecognitionResult(mockEvent);
        expect(mockOnTranscript).toHaveBeenCalledWith('Hello', false);
    });
    
    test('should handle recognition errors', () => {
        const mockEvent = {
            error: 'not-allowed',
            message: 'Permission denied'
        };
        
        speechManager.handleRecognitionError(mockEvent);
        expect(mockOnError).toHaveBeenCalledWith(
            'not-allowed',
            expect.stringContaining('Microphone access denied')
        );
    });
    
    test('should handle various error types', () => {
        const errorCases = [
            ['no-speech', 'No speech detected'],
            ['audio-capture', 'No microphone found'],
            ['network', 'Network error'],
            ['service-not-allowed', 'Speech service not available']
        ];
        
        errorCases.forEach(([errorCode, expectedMessage]) => {
            const mockEvent = { error: errorCode, message: '' };
            speechManager.handleRecognitionError(mockEvent);
            expect(mockOnError).toHaveBeenCalledWith(
                errorCode,
                expect.stringContaining(expectedMessage)
            );
        });
    });
    
    test('should cleanup properly', () => {
        speechManager.cleanup();
        
        expect(speechManager.getCurrentState()).toBe('idle');
        expect(speechManager.recognition).toBe(null);
        expect(speechManager.currentUtterance).toBe(null);
    });
    
    test('should handle microphone permission states', async () => {
        // Test granted permission
        global.navigator.permissions.query.mockResolvedValue({ state: 'granted' });
        const result1 = await speechManager.checkMicrophonePermission();
        expect(result1).toBe(true);
        
        // Test denied permission
        global.navigator.permissions.query.mockResolvedValue({ state: 'denied' });
        const result2 = await speechManager.checkMicrophonePermission();
        expect(result2).toBe(false);
        expect(mockOnError).toHaveBeenCalledWith(
            'microphone-denied',
            expect.stringContaining('Microphone access denied')
        );
    });
    
    test('should handle microphone access errors', async () => {
        global.navigator.permissions.query.mockResolvedValue({ state: 'prompt' });
        global.navigator.mediaDevices.getUserMedia.mockRejectedValue(
            new Error('NotAllowedError')
        );
        
        const result = await speechManager.requestMicrophoneAccess();
        expect(result).toBe(false);
        expect(mockOnError).toHaveBeenCalled();
    });
    
    test('should handle missing permissions API', async () => {
        // Temporarily remove permissions API
        const originalPermissions = global.navigator.permissions;
        delete global.navigator.permissions;
        
        const result = await speechManager.checkMicrophonePermission();
        expect(result).toBe(true); // Should fallback to direct access
        
        // Restore
        global.navigator.permissions = originalPermissions;
    });
    
    test('should handle timer management', () => {
        // Test silence timer
        speechManager.startSilenceTimer();
        expect(speechManager.silenceTimer).toBeDefined();
        
        speechManager.clearSilenceTimer();
        expect(speechManager.silenceTimer).toBe(null);
        
        // Test clearing all timers
        speechManager.startSilenceTimer();
        speechManager.clearTimers();
        expect(speechManager.silenceTimer).toBe(null);
        expect(speechManager.maxRecordingTimer).toBe(null);
    });
});

// Test error handling for different browser environments
describe('VoiceSpeechManager Browser Compatibility', () => {
    test('should handle missing speech recognition', () => {
        // Mock environment without speech recognition
        global.window = {
            location: { protocol: 'https:', hostname: 'localhost' }
        };
        
        const VoiceSpeechManager = require('./voice-speech-manager.js');
        const mockOnError = jest.fn();
        
        const manager = new VoiceSpeechManager(null, mockOnError, null);
        
        expect(manager.hasSpeechRecognition()).toBe(false);
        expect(mockOnError).toHaveBeenCalledWith(
            'speech-recognition-unavailable',
            expect.stringContaining('Speech recognition is not supported')
        );
    });
    
    test('should handle insecure context', () => {
        // Mock insecure context
        global.window = {
            SpeechRecognition: jest.fn(),
            location: { protocol: 'http:', hostname: 'example.com' }
        };
        
        const VoiceSpeechManager = require('./voice-speech-manager.js');
        const mockOnError = jest.fn();
        
        const manager = new VoiceSpeechManager(null, mockOnError, null);
        
        expect(manager.isSecureContext()).toBe(false);
        expect(mockOnError).toHaveBeenCalledWith(
            'insecure-context',
            'Speech recognition requires HTTPS or localhost'
        );
    });
});