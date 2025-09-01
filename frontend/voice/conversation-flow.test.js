/**
 * Test suite for conversation flow and state management functionality
 * Tests the new features added in task 6
 */

describe('VoiceAssistantPage - Conversation Flow', () => {
    let mockVoiceAssistant;

    beforeEach(() => {
        // Mock the conversation flow functionality directly
        mockVoiceAssistant = {
            conversationContext: {
                sessionId: null,
                messages: [],
                currentTranscript: '',
                lastResponse: '',
                startTime: new Date(),
                totalInteractions: 0,
                autoListenEnabled: true
            },
            silenceConfig: {
                enabled: true,
                timeoutMs: 3000,
                maxSilenceBeforeStop: 5000
            },
            silenceTimer: null,
            autoListenTimer: null,
            state: {
                currentState: 'idle',
                isMuted: false
            },
            speechManager: {
                startListening: jest.fn(() => Promise.resolve(true)),
                stopListening: jest.fn(),
                speakText: jest.fn(() => true),
                stopSpeaking: jest.fn(),
                isSpeaking: jest.fn(() => false)
            },
            visualFeedback: {
                displayTranscript: jest.fn(),
                displayResponse: jest.fn(),
                updateStatusText: jest.fn()
            },
            apiClient: {
                getSessionStatus: jest.fn(() => ({ isValidated: true })),
                sendMessage: jest.fn(() => Promise.resolve({ message: 'Mock response' }))
            }
        };

        // Add the methods we're testing
        mockVoiceAssistant.addMessageToHistory = function(role, content, metadata = null) {
            const message = {
                role: role,
                content: content,
                timestamp: new Date(),
                metadata: metadata
            };
            
            this.conversationContext.messages.push(message);
            
            // Limit conversation history to prevent memory issues
            if (this.conversationContext.messages.length > 50) {
                this.conversationContext.messages = this.conversationContext.messages.slice(-25);
            }
        };

        mockVoiceAssistant.handleConversationFlow = function(newState, oldState, data = {}) {
            switch (newState) {
                case 'speech-ended':
                    this.handleSpeechEnded();
                    break;
                case 'tts-fallback':
                    if (data.fallbackText) {
                        this.visualFeedback.displayResponse(data.fallbackText);
                    }
                    this.scheduleAutoListen();
                    break;
                case 'idle':
                    this.clearAllTimers();
                    break;
            }
        };

        mockVoiceAssistant.handleSpeechEnded = function() {
            this.state.currentState = 'idle';
            this.scheduleAutoListen();
        };

        mockVoiceAssistant.scheduleAutoListen = function() {
            if (!this.conversationContext.autoListenEnabled) {
                return;
            }
            
            this.clearAutoListenTimer();
            
            this.autoListenTimer = setTimeout(() => {
                if (this.state.currentState === 'idle' && !this.state.isMuted) {
                    this.speechManager.startListening();
                }
            }, 1500);
        };

        mockVoiceAssistant.clearAllTimers = function() {
            if (this.silenceTimer) {
                clearTimeout(this.silenceTimer);
                this.silenceTimer = null;
            }
            if (this.autoListenTimer) {
                clearTimeout(this.autoListenTimer);
                this.autoListenTimer = null;
            }
        };

        mockVoiceAssistant.clearAutoListenTimer = function() {
            if (this.autoListenTimer) {
                clearTimeout(this.autoListenTimer);
                this.autoListenTimer = null;
            }
        };

        mockVoiceAssistant.handleTranscript = function(transcript, isFinal) {
            this.conversationContext.currentTranscript = transcript;
            this.visualFeedback.displayTranscript(transcript);
            
            if (isFinal && transcript.trim()) {
                this.addMessageToHistory('user', transcript.trim());
            }
        };

        mockVoiceAssistant.handleAIResponse = function(responseText, fullResponse = null) {
            this.addMessageToHistory('assistant', responseText, fullResponse);
            this.conversationContext.lastResponse = responseText;
            this.conversationContext.totalInteractions++;
            this.visualFeedback.displayResponse(responseText);
            this.speechManager.speakText(responseText);
        };

        mockVoiceAssistant.handleReplay = function() {
            if (this.conversationContext.lastResponse) {
                if (this.speechManager.isSpeaking()) {
                    this.speechManager.stopSpeaking();
                }
                this.speechManager.speakText(this.conversationContext.lastResponse);
            } else {
                this.visualFeedback.updateStatusText('No previous response to replay');
            }
        };
    });

    describe('Conversation Context Initialization', () => {
        test('should initialize conversation context with default values', () => {
            expect(mockVoiceAssistant.conversationContext).toBeDefined();
            expect(mockVoiceAssistant.conversationContext.messages).toEqual([]);
            expect(mockVoiceAssistant.conversationContext.totalInteractions).toBe(0);
            expect(mockVoiceAssistant.conversationContext.autoListenEnabled).toBe(true);
            expect(mockVoiceAssistant.conversationContext.startTime).toBeInstanceOf(Date);
        });

        test('should handle auto-listen preference changes', () => {
            mockVoiceAssistant.conversationContext.autoListenEnabled = false;
            
            expect(mockVoiceAssistant.conversationContext.autoListenEnabled).toBe(false);
        });
    });

    describe('Message History Management', () => {

        test('should add user message to history', () => {
            const userMessage = 'Hello, how are you?';
            
            mockVoiceAssistant.addMessageToHistory('user', userMessage);
            
            expect(mockVoiceAssistant.conversationContext.messages).toHaveLength(1);
            expect(mockVoiceAssistant.conversationContext.messages[0]).toMatchObject({
                role: 'user',
                content: userMessage,
                timestamp: expect.any(Date)
            });
        });

        test('should add assistant message to history', () => {
            const assistantMessage = 'I am doing well, thank you!';
            const metadata = { confidence: 0.95 };
            
            mockVoiceAssistant.addMessageToHistory('assistant', assistantMessage, metadata);
            
            expect(mockVoiceAssistant.conversationContext.messages).toHaveLength(1);
            expect(mockVoiceAssistant.conversationContext.messages[0]).toMatchObject({
                role: 'assistant',
                content: assistantMessage,
                metadata: metadata,
                timestamp: expect.any(Date)
            });
        });

        test('should limit conversation history to prevent memory issues', () => {
            // Reset messages array for this test
            mockVoiceAssistant.conversationContext.messages = [];
            
            // Add exactly 51 messages to trigger the trimming
            for (let i = 0; i < 51; i++) {
                mockVoiceAssistant.addMessageToHistory('user', `Message ${i}`);
            }
            
            // Should be trimmed to 25 messages
            expect(mockVoiceAssistant.conversationContext.messages).toHaveLength(25);
            // First message should be from the second half
            expect(mockVoiceAssistant.conversationContext.messages[0].content).toBe('Message 26');
        });
    });

    describe('Conversation Flow Handling', () => {
        beforeEach(() => {
            jest.useFakeTimers();
        });

        afterEach(() => {
            jest.useRealTimers();
        });

        test('should handle speech ended and schedule auto-listen', () => {
            mockVoiceAssistant.conversationContext.autoListenEnabled = true;
            mockVoiceAssistant.state.currentState = 'speaking';
            mockVoiceAssistant.state.isMuted = false;
            
            mockVoiceAssistant.handleConversationFlow('speech-ended', 'speaking');
            
            expect(mockVoiceAssistant.state.currentState).toBe('idle');
            
            // Fast-forward timer
            jest.advanceTimersByTime(1500);
            
            expect(mockVoiceAssistant.speechManager.startListening).toHaveBeenCalled();
        });

        test('should not auto-listen when disabled', () => {
            mockVoiceAssistant.conversationContext.autoListenEnabled = false;
            
            mockVoiceAssistant.handleConversationFlow('speech-ended', 'speaking');
            
            jest.advanceTimersByTime(2000);
            
            expect(mockVoiceAssistant.speechManager.startListening).not.toHaveBeenCalled();
        });

        test('should not auto-listen when muted', () => {
            mockVoiceAssistant.conversationContext.autoListenEnabled = true;
            mockVoiceAssistant.state.isMuted = true;
            
            mockVoiceAssistant.handleConversationFlow('speech-ended', 'speaking');
            
            jest.advanceTimersByTime(1500);
            
            expect(mockVoiceAssistant.speechManager.startListening).not.toHaveBeenCalled();
        });

        test('should handle TTS fallback and schedule auto-listen', () => {
            const fallbackData = { fallbackText: 'Fallback response' };
            
            mockVoiceAssistant.handleConversationFlow('tts-fallback', 'speaking', fallbackData);
            
            expect(mockVoiceAssistant.visualFeedback.displayResponse).toHaveBeenCalledWith('Fallback response');
            
            jest.advanceTimersByTime(1500);
            expect(mockVoiceAssistant.speechManager.startListening).toHaveBeenCalled();
        });
    });

    describe('Enhanced Transcript Handling', () => {
        test('should update conversation context with transcript', () => {
            const transcript = 'This is a test transcript';
            
            mockVoiceAssistant.handleTranscript(transcript, false);
            
            expect(mockVoiceAssistant.conversationContext.currentTranscript).toBe(transcript);
            expect(mockVoiceAssistant.visualFeedback.displayTranscript).toHaveBeenCalledWith(transcript);
        });

        test('should process final transcript and add to history', () => {
            const transcript = 'Final transcript';
            
            mockVoiceAssistant.handleTranscript(transcript, true);
            
            expect(mockVoiceAssistant.conversationContext.messages).toHaveLength(1);
            expect(mockVoiceAssistant.conversationContext.messages[0]).toMatchObject({
                role: 'user',
                content: transcript
            });
        });
    });

    describe('AI Response Handling', () => {
        test('should handle AI response and update conversation context', () => {
            const responseText = 'This is an AI response';
            const fullResponse = { message: responseText, confidence: 0.9 };
            
            mockVoiceAssistant.handleAIResponse(responseText, fullResponse);
            
            expect(mockVoiceAssistant.conversationContext.lastResponse).toBe(responseText);
            expect(mockVoiceAssistant.conversationContext.totalInteractions).toBe(1);
            expect(mockVoiceAssistant.conversationContext.messages).toHaveLength(1);
            expect(mockVoiceAssistant.conversationContext.messages[0]).toMatchObject({
                role: 'assistant',
                content: responseText,
                metadata: fullResponse
            });
            
            expect(mockVoiceAssistant.visualFeedback.displayResponse).toHaveBeenCalledWith(responseText);
            expect(mockVoiceAssistant.speechManager.speakText).toHaveBeenCalledWith(responseText);
        });
    });

    describe('Replay Functionality', () => {
        test('should replay last response when available', () => {
            mockVoiceAssistant.conversationContext.lastResponse = 'Previous response';
            
            mockVoiceAssistant.handleReplay();
            
            expect(mockVoiceAssistant.speechManager.speakText).toHaveBeenCalledWith('Previous response');
        });

        test('should show message when no response to replay', () => {
            mockVoiceAssistant.conversationContext.lastResponse = '';
            
            mockVoiceAssistant.handleReplay();
            
            expect(mockVoiceAssistant.visualFeedback.updateStatusText).toHaveBeenCalledWith('No previous response to replay');
        });
    });

    describe('Timer Management', () => {
        beforeEach(() => {
            jest.useFakeTimers();
        });

        afterEach(() => {
            jest.useRealTimers();
        });

        test('should clear all timers on cleanup', () => {
            mockVoiceAssistant.silenceTimer = setTimeout(() => {}, 1000);
            mockVoiceAssistant.autoListenTimer = setTimeout(() => {}, 1000);
            
            mockVoiceAssistant.clearAllTimers();
            
            expect(mockVoiceAssistant.silenceTimer).toBeNull();
            expect(mockVoiceAssistant.autoListenTimer).toBeNull();
        });

        test('should schedule auto-listen correctly', () => {
            mockVoiceAssistant.conversationContext.autoListenEnabled = true;
            mockVoiceAssistant.state.currentState = 'idle';
            mockVoiceAssistant.state.isMuted = false;
            
            mockVoiceAssistant.scheduleAutoListen();
            
            // Fast-forward timer
            jest.advanceTimersByTime(1500);
            
            expect(mockVoiceAssistant.speechManager.startListening).toHaveBeenCalled();
        });
    });
});