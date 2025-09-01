// Enhanced TTS functionality tests for VoiceSpeechManager
// Tests voice selection, speech controls, error handling, and AI response processing

const VoiceSpeechManager = require('./voice-speech-manager.js');

describe('VoiceSpeechManager - TTS Functionality', () => {
    let speechManager;
    let mockSynthesis;
    let mockUtterance;
    let mockVoices;
    
    beforeEach(() => {
        // Mock SpeechSynthesisUtterance
        mockUtterance = {
            text: '',
            lang: '',
            voice: null,
            rate: 1,
            pitch: 1,
            volume: 1,
            onstart: null,
            onend: null,
            onerror: null,
            onpause: null,
            onresume: null,
            onmark: null
        };
        
        global.SpeechSynthesisUtterance = jest.fn(() => mockUtterance);
        
        // Mock voices
        mockVoices = [
            { name: 'Voice 1', lang: 'en-US', default: true, localService: true, voiceURI: 'voice1' },
            { name: 'Voice 2', lang: 'en-GB', default: false, localService: true, voiceURI: 'voice2' },
            { name: 'Voice 3', lang: 'es-ES', default: false, localService: true, voiceURI: 'voice3' }
        ];
        
        // Mock speechSynthesis
        mockSynthesis = {
            speak: jest.fn(),
            cancel: jest.fn(),
            pause: jest.fn(),
            resume: jest.fn(),
            getVoices: jest.fn(() => mockVoices),
            speaking: false,
            paused: false,
            pending: false,
            onvoiceschanged: null
        };
        
        global.speechSynthesis = mockSynthesis;
        window.speechSynthesis = mockSynthesis;
        
        // Mock other required APIs
        global.webkitSpeechRecognition = jest.fn();
        global.navigator = {
            mediaDevices: { getUserMedia: jest.fn() },
            permissions: { query: jest.fn() }
        };
        
        // Mock location properties directly
        global.location = { protocol: 'https:', hostname: 'localhost' };
        
        speechManager = new VoiceSpeechManager();
    });
    
    afterEach(() => {
        if (speechManager) {
            speechManager.cleanup();
        }
        jest.clearAllMocks();
    });
    
    describe('Voice Management', () => {
        test('should load available voices', () => {
            speechManager.loadVoices();
            
            expect(speechManager.getAvailableVoices()).toEqual(mockVoices);
            expect(speechManager.getAvailableVoices().length).toBe(3);
        });
        
        test('should find best voice for language', () => {
            speechManager.loadVoices();
            
            const bestVoice = speechManager.findBestVoice('en-US');
            expect(bestVoice.name).toBe('Voice 1');
            expect(bestVoice.lang).toBe('en-US');
        });
        
        test('should find fallback voice for unsupported language', () => {
            speechManager.loadVoices();
            
            const fallbackVoice = speechManager.findBestVoice('fr-FR');
            expect(fallbackVoice.name).toBe('Voice 1'); // Should fallback to English
        });
        
        test('should set voice by name', () => {
            speechManager.loadVoices();
            
            const success = speechManager.setVoice('Voice 2');
            expect(success).toBe(true);
            expect(speechManager.selectedVoice.name).toBe('Voice 2');
        });
        
        test('should set voice by object', () => {
            speechManager.loadVoices();
            
            const voice = mockVoices[1];
            const success = speechManager.setVoice(voice);
            expect(success).toBe(true);
            expect(speechManager.selectedVoice).toBe(voice);
        });
        
        test('should return false for invalid voice name', () => {
            speechManager.loadVoices();
            
            const success = speechManager.setVoice('Invalid Voice');
            expect(success).toBe(false);
        });
        
        test('should get voices by language', () => {
            speechManager.loadVoices();
            
            const enVoices = speechManager.getVoicesByLanguage('en-US');
            expect(enVoices.length).toBe(2); // en-US and en-GB
            
            const esVoices = speechManager.getVoicesByLanguage('es-ES');
            expect(esVoices.length).toBe(1);
        });
    });
    
    describe('TTS Configuration', () => {
        test('should set TTS rate within bounds', () => {
            speechManager.setTTSRate(1.5);
            expect(speechManager.getTTSConfig().rate).toBe(1.5);
            
            // Test bounds
            speechManager.setTTSRate(15); // Above max
            expect(speechManager.getTTSConfig().rate).toBe(10);
            
            speechManager.setTTSRate(0.05); // Below min
            expect(speechManager.getTTSConfig().rate).toBe(0.1);
        });
        
        test('should set TTS pitch within bounds', () => {
            speechManager.setTTSPitch(1.2);
            expect(speechManager.getTTSConfig().pitch).toBe(1.2);
            
            // Test bounds
            speechManager.setTTSPitch(5); // Above max
            expect(speechManager.getTTSConfig().pitch).toBe(2);
            
            speechManager.setTTSPitch(-1); // Below min
            expect(speechManager.getTTSConfig().pitch).toBe(0);
        });
        
        test('should set TTS volume within bounds', () => {
            speechManager.setTTSVolume(0.8);
            expect(speechManager.getTTSConfig().volume).toBe(0.8);
            
            // Test bounds
            speechManager.setTTSVolume(2); // Above max
            expect(speechManager.getTTSConfig().volume).toBe(1);
            
            speechManager.setTTSVolume(-0.5); // Below min
            expect(speechManager.getTTSConfig().volume).toBe(0);
        });
        
        test('should update TTS configuration', () => {
            const newConfig = {
                rate: 1.2,
                pitch: 0.8,
                volume: 0.9,
                autoPlay: false,
                fallbackToText: false
            };
            
            speechManager.updateTTSConfig(newConfig);
            const config = speechManager.getTTSConfig();
            
            expect(config.rate).toBe(1.2);
            expect(config.pitch).toBe(0.8);
            expect(config.volume).toBe(0.9);
            expect(config.autoPlay).toBe(false);
            expect(config.fallbackToText).toBe(false);
        });
    });
    
    describe('Speech Synthesis', () => {
        test('should speak text with default settings', () => {
            const success = speechManager.speakText('Hello world');
            
            expect(success).toBe(true);
            expect(mockSynthesis.speak).toHaveBeenCalled();
            expect(mockUtterance.text).toBe('Hello world');
            expect(speechManager.getLastSpokenText()).toBe('Hello world');
        });
        
        test('should configure utterance with custom options', () => {
            speechManager.loadVoices();
            const voice = mockVoices[1];
            
            speechManager.speakText('Test', {
                voice: voice,
                rate: 1.5,
                pitch: 0.8,
                volume: 0.7
            });
            
            expect(mockUtterance.voice).toBe(voice);
            expect(mockUtterance.rate).toBe(1.5);
            expect(mockUtterance.pitch).toBe(0.8);
            expect(mockUtterance.volume).toBe(0.7);
        });
        
        test('should handle speech start event', () => {
            const onStateChange = jest.fn();
            speechManager.onStateChange = onStateChange;
            
            speechManager.speakText('Test');
            
            // Simulate speech start
            mockUtterance.onstart();
            
            expect(speechManager.isSpeaking()).toBe(true);
            expect(speechManager.getCurrentState()).toBe('speaking');
            expect(onStateChange).toHaveBeenCalledWith('speaking', expect.any(String), expect.any(Object));
        });
        
        test('should handle speech end event', () => {
            const onStateChange = jest.fn();
            speechManager.onStateChange = onStateChange;
            
            speechManager.speakText('Test');
            mockUtterance.onstart();
            mockUtterance.onend();
            
            expect(speechManager.isSpeaking()).toBe(false);
            expect(speechManager.getCurrentState()).toBe('idle');
            expect(onStateChange).toHaveBeenCalledWith('speech-ended', 'speaking', expect.any(Object));
        });
        
        test('should handle speech error with fallback', () => {
            const onStateChange = jest.fn();
            speechManager.onStateChange = onStateChange;
            
            speechManager.speakText('Test');
            
            // Simulate error
            mockUtterance.onerror({ error: 'synthesis-failed' });
            
            expect(speechManager.isSpeaking()).toBe(false);
            expect(onStateChange).toHaveBeenCalledWith('tts-fallback', expect.any(String), expect.objectContaining({
                text: 'Test',
                error: 'Speech synthesis failed'
            }));
        });
        
        test('should not fallback for canceled speech', () => {
            const onStateChange = jest.fn();
            speechManager.onStateChange = onStateChange;
            
            speechManager.speakText('Test');
            
            // Simulate cancellation
            mockUtterance.onerror({ error: 'canceled' });
            
            expect(onStateChange).not.toHaveBeenCalledWith('tts-fallback', expect.any(String), expect.any(Object));
        });
        
        test('should stop speaking', () => {
            mockSynthesis.speaking = true;
            speechManager.speakText('Test');
            
            speechManager.stopSpeaking();
            
            expect(mockSynthesis.cancel).toHaveBeenCalled();
            expect(speechManager.isSpeaking()).toBe(false);
        });
        
        test('should pause and resume speaking', () => {
            mockSynthesis.speaking = true;
            speechManager.speakText('Test');
            
            const pauseSuccess = speechManager.pauseSpeaking();
            expect(pauseSuccess).toBe(true);
            expect(mockSynthesis.pause).toHaveBeenCalled();
            
            mockSynthesis.paused = true;
            const resumeSuccess = speechManager.resumeSpeaking();
            expect(resumeSuccess).toBe(true);
            expect(mockSynthesis.resume).toHaveBeenCalled();
        });
        
        test('should replay last speech', () => {
            speechManager.speakText('Original text');
            mockSynthesis.speak.mockClear();
            
            const success = speechManager.replayLastSpeech();
            
            expect(success).toBe(true);
            expect(mockSynthesis.speak).toHaveBeenCalled();
            expect(mockUtterance.text).toBe('Original text');
        });
        
        test('should return false when no text to replay', () => {
            const success = speechManager.replayLastSpeech();
            expect(success).toBe(false);
        });
    });
    
    describe('AI Response Processing', () => {
        test('should process AI response with auto-play', async () => {
            const onStateChange = jest.fn();
            speechManager.onStateChange = onStateChange;
            
            const response = 'This is an AI response with **bold** and *italic* text.';
            const success = await speechManager.processAIResponse(response);
            
            expect(success).toBe(true);
            expect(mockSynthesis.speak).toHaveBeenCalled();
            expect(mockUtterance.text).toBe('This is an AI response with bold and italic text.');
            expect(onStateChange).toHaveBeenCalledWith('processing', expect.any(String), expect.any(Object));
        });
        
        test('should clean markdown from AI response', async () => {
            const response = `
# Header
This is **bold** and *italic* text.
- List item 1
- List item 2
1. Numbered item
\`inline code\`
\`\`\`
code block
\`\`\`
[Link text](http://example.com)
            `.trim();
            
            await speechManager.processAIResponse(response);
            
            const cleanedText = mockUtterance.text;
            expect(cleanedText).not.toContain('**');
            expect(cleanedText).not.toContain('*');
            expect(cleanedText).not.toContain('#');
            expect(cleanedText).not.toContain('```');
            expect(cleanedText).not.toContain('[');
            expect(cleanedText).toContain('bold');
            expect(cleanedText).toContain('italic');
            expect(cleanedText).toContain('Link text');
        });
        
        test('should store response without auto-play when disabled', async () => {
            speechManager.updateTTSConfig({ autoPlay: false });
            const onStateChange = jest.fn();
            speechManager.onStateChange = onStateChange;
            
            const response = 'Test response';
            const success = await speechManager.processAIResponse(response);
            
            expect(success).toBe(true);
            expect(mockSynthesis.speak).not.toHaveBeenCalled();
            expect(speechManager.getLastSpokenText()).toBe('Test response');
            expect(onStateChange).toHaveBeenCalledWith('ai-response-ready', 'processing', expect.objectContaining({
                text: 'Test response',
                autoPlay: false
            }));
        });
        
        test('should handle invalid AI response', async () => {
            const success = await speechManager.processAIResponse('');
            expect(success).toBe(false);
            
            const success2 = await speechManager.processAIResponse(null);
            expect(success2).toBe(false);
        });
    });
    
    describe('Error Handling', () => {
        test('should handle synthesis unavailable', () => {
            // Remove synthesis support
            delete window.speechSynthesis;
            speechManager.synthesis = null;
            
            const success = speechManager.speakText('Test');
            expect(success).toBe(false);
        });
        
        test('should handle invalid text input', () => {
            const success1 = speechManager.speakText('');
            const success2 = speechManager.speakText(null);
            const success3 = speechManager.speakText(123);
            
            expect(success1).toBe(false);
            expect(success2).toBe(false);
            expect(success3).toBe(false);
        });
        
        test('should handle different error types appropriately', () => {
            const onStateChange = jest.fn();
            speechManager.onStateChange = onStateChange;
            
            speechManager.speakText('Test');
            
            // Test different error types
            const errorTypes = [
                'canceled',
                'interrupted', 
                'audio-busy',
                'network',
                'synthesis-unavailable',
                'language-unavailable'
            ];
            
            errorTypes.forEach(errorType => {
                onStateChange.mockClear();
                mockUtterance.onerror({ error: errorType });
                
                if (errorType === 'canceled' || errorType === 'interrupted') {
                    // Should not trigger fallback
                    expect(onStateChange).not.toHaveBeenCalledWith('tts-fallback', expect.any(String), expect.any(Object));
                } else {
                    // Should trigger fallback
                    expect(onStateChange).toHaveBeenCalledWith('tts-fallback', expect.any(String), expect.objectContaining({
                        error: expect.stringContaining(errorType === 'audio-busy' ? 'Audio system is busy' : '')
                    }));
                }
            });
        });
    });
    
    describe('Cleanup', () => {
        test('should cleanup TTS resources', () => {
            speechManager.loadVoices();
            speechManager.speakText('Test');
            
            expect(speechManager.getAvailableVoices().length).toBeGreaterThan(0);
            expect(speechManager.getLastSpokenText()).toBe('Test');
            
            speechManager.cleanup();
            
            expect(speechManager.getAvailableVoices().length).toBe(0);
            expect(speechManager.getLastSpokenText()).toBe('');
            expect(speechManager.selectedVoice).toBeNull();
        });
    });
});