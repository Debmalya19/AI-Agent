/**
 * Voice End-to-End Tests
 * Tests complete voice conversation flows from user input to AI response
 */

class VoiceE2ETest {
    constructor() {
        this.testResults = [];
        this.setupE2EMocks();
    }

    setupE2EMocks() {
        // Mock Web Speech API
        this.mockSpeechRecognition = class {
            constructor() {
                this.lang = 'en-US';
                this.continuous = false;
                this.interimResults = false;
                this.onstart = null;
                this.onresult = null;
                this.onerror = null;
                this.onend = null;
                this._isStarted = false;
            }

            start() {
                this._isStarted = true;
                setTimeout(() => {
                    if (this.onstart) this.onstart();
                }, 10);
            }

            stop() {
                this._isStarted = false;
                setTimeout(() => {
                    if (this.onend) this.onend();
                }, 10);
            }

            _simulateResult(transcript, confidence = 0.9) {
                if (this.onresult) {
                    const event = {
                        resultIndex: 0,
                        results: [{
                            0: { transcript, confidence },
                            isFinal: true,
                            length: 1
                        }]
                    };
                    this.onresult(event);
                }
            }
        };

        this.mockSpeechSynthesis = {
            speaking: false,
            paused: false,
            voices: [
                { name: 'Test Voice', lang: 'en-US', voiceURI: 'test-voice' }
            ],
            
            speak: function(utterance) {
                this.speaking = true;
                setTimeout(() => {
                    if (utterance.onstart) utterance.onstart();
                }, 10);
                setTimeout(() => {
                    this.speaking = false;
                    if (utterance.onend) utterance.onend();
                }, 100);
            },
            
            cancel: function() {
                this.speaking = false;
            },
            
            getVoices: function() {
                return this.voices;
            }
        };

        // Mock chat interface
        this.mockChatInterface = {
            messages: [],
            
            sendMessage: function(message) {
                this.messages.push({ type: 'user', content: message, timestamp: Date.now() });
                
                // Simulate AI response
                setTimeout(() => {
                    const responses = [
                        "I'd be happy to help you with that.",
                        "Let me look into that for you.",
                        "Here's what I found about your question.",
                        "I understand your concern. Let me assist you."
                    ];
                    const response = responses[Math.floor(Math.random() * responses.length)];
                    this.messages.push({ type: 'assistant', content: response, timestamp: Date.now() });
                    
                    // Trigger response event
                    if (this.onResponse) {
                        this.onResponse(response);
                    }
                }, 50);
            },
            
            onResponse: null
        };

        // Mock voice analytics
        this.mockAnalytics = {
            events: [],
            
            logEvent: function(eventType, data) {
                this.events.push({
                    type: eventType,
                    data: data,
                    timestamp: Date.now()
                });
            }
        };

        // Setup global mocks
        if (typeof window !== 'undefined') {
            window.SpeechRecognition = this.mockSpeechRecognition;
            window.webkitSpeechRecognition = this.mockSpeechRecognition;
            window.speechSynthesis = this.mockSpeechSynthesis;
            window.SpeechSynthesisUtterance = class {
                constructor(text) {
                    this.text = text;
                    this.rate = 1;
                    this.pitch = 1;
                    this.volume = 1;
                    this.onstart = null;
                    this.onend = null;
                }
            };
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
        console.log('Running Voice End-to-End Tests...\n');

        try {
            await this.testCompleteVoiceConversation();
            await this.testVoiceWithRecommendedQuestions();
            await this.testVoiceWithMultiToolResponse();
            await this.testVoiceErrorRecoveryFlow();
            await this.testVoiceSettingsPersistence();
            await this.testVoiceQueueManagement();
            await this.testVoiceInterruptionHandling();
            await this.testVoiceAccessibilityFlow();
        } catch (error) {
            console.error('E2E test suite error:', error);
        }

        this.printResults();
    }

    async testCompleteVoiceConversation() {
        console.log('Testing complete voice conversation flow...');

        // Create voice controller with mocked dependencies
        const voiceController = this.createMockVoiceController();
        
        let conversationSteps = [];
        
        // Step 1: User starts recording
        voiceController.addEventListener('recording_started', () => {
            conversationSteps.push('recording_started');
        });
        
        voiceController.addEventListener('recording_stopped', () => {
            conversationSteps.push('recording_stopped');
        });
        
        voiceController.addEventListener('final_result', (data) => {
            conversationSteps.push(`transcription: ${data.transcript}`);
            // Simulate sending message to chat
            this.mockChatInterface.sendMessage(data.transcript);
        });
        
        voiceController.addEventListener('speech_started', () => {
            conversationSteps.push('speech_started');
        });
        
        voiceController.addEventListener('speech_ended', () => {
            conversationSteps.push('speech_ended');
        });

        // Set up chat response handler
        this.mockChatInterface.onResponse = (response) => {
            conversationSteps.push(`ai_response: ${response}`);
            // Auto-play response if enabled
            if (voiceController.settings.getValue('autoPlayEnabled')) {
                voiceController.playResponse(response);
            }
        };

        // Enable auto-play
        voiceController.updateSettings({ autoPlayEnabled: true });

        // Start the conversation
        await voiceController.startRecording();
        await new Promise(resolve => setTimeout(resolve, 20));

        // Simulate user speech
        voiceController.recognition._simulateResult('Hello, I need help with my account');
        await new Promise(resolve => setTimeout(resolve, 100));

        // Stop recording
        voiceController.stopRecording();
        await new Promise(resolve => setTimeout(resolve, 200));

        // Verify conversation flow
        this.assert(
            conversationSteps.includes('recording_started'),
            'should start recording'
        );
        this.assert(
            conversationSteps.some(step => step.includes('transcription:')),
            'should transcribe user speech'
        );
        this.assert(
            conversationSteps.some(step => step.includes('ai_response:')),
            'should receive AI response'
        );
        this.assert(
            conversationSteps.includes('speech_started'),
            'should start playing AI response'
        );
        this.assert(
            conversationSteps.includes('speech_ended'),
            'should complete playing AI response'
        );

        // Verify message was sent to chat
        this.assert(
            this.mockChatInterface.messages.length >= 2,
            'should have user message and AI response in chat'
        );
        this.assert(
            this.mockChatInterface.messages[0].type === 'user',
            'first message should be from user'
        );
        this.assert(
            this.mockChatInterface.messages[1].type === 'assistant',
            'second message should be from assistant'
        );
    }

    async testVoiceWithRecommendedQuestions() {
        console.log('Testing voice with recommended questions...');

        const voiceController = this.createMockVoiceController();
        
        // Mock recommended questions
        const recommendedQuestions = [
            "How do I reset my password?",
            "What are your business hours?",
            "How can I contact support?"
        ];

        let questionReadAloud = null;
        let questionSent = null;

        // Mock recommended question handler
        const handleRecommendedQuestion = async (question) => {
            // Read question aloud first
            await voiceController.playResponse(`You selected: ${question}. Sending this question now.`);
            questionReadAloud = question;
            
            // Then send to chat
            this.mockChatInterface.sendMessage(question);
            questionSent = question;
        };

        // Test clicking recommended question
        const selectedQuestion = recommendedQuestions[0];
        await handleRecommendedQuestion(selectedQuestion);
        
        // Wait for processing
        await new Promise(resolve => setTimeout(resolve, 150));

        this.assert(
            questionReadAloud === selectedQuestion,
            'should read recommended question aloud'
        );
        this.assert(
            questionSent === selectedQuestion,
            'should send recommended question to chat'
        );
        this.assert(
            this.mockChatInterface.messages.some(msg => msg.content === selectedQuestion),
            'recommended question should appear in chat history'
        );
    }

    async testVoiceWithMultiToolResponse() {
        console.log('Testing voice with multi-tool response...');

        const voiceController = this.createMockVoiceController();
        
        // Mock multi-tool response
        const multiToolResponse = {
            text: "I've created a support ticket for you (Ticket #12345) and found your account information. Your account is active and your last login was yesterday.",
            tools_used: ['ticket_creation', 'account_lookup'],
            ticket_id: '12345'
        };

        let speechStarted = false;
        let speechCompleted = false;
        let fullResponseSpoken = false;

        voiceController.addEventListener('speech_started', () => {
            speechStarted = true;
        });

        voiceController.addEventListener('speech_ended', () => {
            speechCompleted = true;
        });

        // Mock chat interface to return multi-tool response
        this.mockChatInterface.onResponse = (response) => {
            // Simulate multi-tool response
            const enhancedResponse = `${multiToolResponse.text} I used ${multiToolResponse.tools_used.length} tools to help you.`;
            voiceController.playResponse(enhancedResponse);
            fullResponseSpoken = enhancedResponse;
        };

        // Simulate user asking for help
        this.mockChatInterface.sendMessage("I need help with my account and want to create a ticket");
        
        // Wait for response processing
        await new Promise(resolve => setTimeout(resolve, 200));

        this.assert(
            speechStarted,
            'should start speaking multi-tool response'
        );
        this.assert(
            speechCompleted,
            'should complete speaking multi-tool response'
        );
        this.assert(
            fullResponseSpoken && fullResponseSpoken.includes('Ticket #12345'),
            'should include ticket information in spoken response'
        );
        this.assert(
            fullResponseSpoken && fullResponseSpoken.includes('2 tools'),
            'should mention number of tools used'
        );
    }

    async testVoiceErrorRecoveryFlow() {
        console.log('Testing voice error recovery flow...');

        const voiceController = this.createMockVoiceController();
        
        let errorOccurred = false;
        let errorRecovered = false;
        let fallbackUsed = false;

        voiceController.addEventListener('error', (data) => {
            errorOccurred = true;
            
            // Simulate error recovery
            if (data.error === 'no-speech') {
                // Retry recording
                setTimeout(() => {
                    voiceController.startRecording().then(() => {
                        errorRecovered = true;
                    });
                }, 100);
            } else if (data.error === 'not-allowed') {
                // Fall back to text input
                fallbackUsed = true;
            }
        });

        // Test no-speech error and recovery
        await voiceController.startRecording();
        await new Promise(resolve => setTimeout(resolve, 20));
        
        // Simulate no-speech error
        voiceController.recognition._simulateError('no-speech');
        await new Promise(resolve => setTimeout(resolve, 150));

        this.assert(
            errorOccurred,
            'should detect no-speech error'
        );
        this.assert(
            errorRecovered,
            'should attempt error recovery'
        );

        // Test permission denied error
        errorOccurred = false;
        voiceController.recognition._simulateError('not-allowed');
        await new Promise(resolve => setTimeout(resolve, 50));

        this.assert(
            fallbackUsed,
            'should use fallback for permission denied error'
        );
    }

    async testVoiceSettingsPersistence() {
        console.log('Testing voice settings persistence...');

        const voiceController = this.createMockVoiceController();
        
        // Test initial settings
        const initialSettings = voiceController.settings.get();
        this.assert(
            typeof initialSettings === 'object',
            'should have initial settings'
        );

        // Update settings
        const newSettings = {
            speechRate: 1.5,
            language: 'en-GB',
            autoPlayEnabled: true,
            voiceName: 'en-GB-Standard-A'
        };

        const updateSuccess = voiceController.updateSettings(newSettings);
        this.assert(
            updateSuccess,
            'should successfully update settings'
        );

        // Verify settings were applied
        const updatedSettings = voiceController.settings.get();
        this.assert(
            updatedSettings.speechRate === 1.5,
            'should persist speech rate setting'
        );
        this.assert(
            updatedSettings.language === 'en-GB',
            'should persist language setting'
        );
        this.assert(
            updatedSettings.autoPlayEnabled === true,
            'should persist auto-play setting'
        );

        // Test settings affect voice operations
        await voiceController.startRecording();
        this.assert(
            voiceController.recognition.lang === 'en-GB',
            'should apply language setting to speech recognition'
        );

        // Test TTS settings
        const testUtterance = await voiceController.createUtterance('Test message');
        this.assert(
            testUtterance.rate === 1.5,
            'should apply speech rate to TTS'
        );
        this.assert(
            testUtterance.lang === 'en-GB',
            'should apply language to TTS'
        );
    }

    async testVoiceQueueManagement() {
        console.log('Testing voice queue management...');

        const voiceController = this.createMockVoiceController();
        
        let queuedMessages = [];
        let playbackOrder = [];

        voiceController.addEventListener('speech_queued', (data) => {
            queuedMessages.push(data.text);
        });

        voiceController.addEventListener('speech_started', (data) => {
            playbackOrder.push(data.text);
        });

        // Queue multiple messages rapidly
        const messages = [
            'First message',
            'Second message',
            'Third message'
        ];

        // Start first message
        await voiceController.playResponse(messages[0]);
        await new Promise(resolve => setTimeout(resolve, 20));

        // Queue additional messages while first is playing
        await voiceController.playResponse(messages[1]);
        await voiceController.playResponse(messages[2]);

        this.assert(
            queuedMessages.length === 2,
            'should queue messages while speaking'
        );
        this.assert(
            voiceController.speechQueue.length === 2,
            'should maintain correct queue length'
        );

        // Wait for all messages to complete
        await new Promise(resolve => setTimeout(resolve, 400));

        this.assert(
            playbackOrder.length === 3,
            'should play all queued messages'
        );
        this.assert(
            playbackOrder[0] === messages[0],
            'should play messages in correct order'
        );
        this.assert(
            voiceController.speechQueue.length === 0,
            'should empty queue after completion'
        );
    }

    async testVoiceInterruptionHandling() {
        console.log('Testing voice interruption handling...');

        const voiceController = this.createMockVoiceController();
        
        let speechInterrupted = false;
        let newRecordingStarted = false;

        voiceController.addEventListener('speech_interrupted', () => {
            speechInterrupted = true;
        });

        voiceController.addEventListener('recording_started', () => {
            newRecordingStarted = true;
        });

        // Start playing a response
        await voiceController.playResponse('This is a long response that will be interrupted');
        await new Promise(resolve => setTimeout(resolve, 20));

        this.assert(
            voiceController.isSpeaking,
            'should be speaking before interruption'
        );

        // Interrupt with new recording
        await voiceController.startRecording();
        await new Promise(resolve => setTimeout(resolve, 20));

        this.assert(
            speechInterrupted || !voiceController.isSpeaking,
            'should interrupt speech when starting new recording'
        );
        this.assert(
            newRecordingStarted,
            'should start new recording after interruption'
        );
        this.assert(
            voiceController.isRecording,
            'should be recording after interruption'
        );
    }

    async testVoiceAccessibilityFlow() {
        console.log('Testing voice accessibility flow...');

        const voiceController = this.createMockVoiceController();
        
        // Mock accessibility announcements
        const accessibilityAnnouncements = [];
        
        const mockAnnouncer = {
            announce: function(message, priority) {
                accessibilityAnnouncements.push({ message, priority });
            }
        };

        // Add accessibility event handlers
        voiceController.addEventListener('recording_started', () => {
            mockAnnouncer.announce('Voice recording started. Speak now.', 'assertive');
        });

        voiceController.addEventListener('final_result', (data) => {
            mockAnnouncer.announce(`Transcribed: ${data.transcript}`, 'polite');
        });

        voiceController.addEventListener('speech_started', (data) => {
            mockAnnouncer.announce('Playing response audio.', 'polite');
        });

        voiceController.addEventListener('error', (data) => {
            mockAnnouncer.announce(`Voice error: ${data.message}`, 'assertive');
        });

        // Test accessibility flow
        await voiceController.startRecording();
        await new Promise(resolve => setTimeout(resolve, 20));

        voiceController.recognition._simulateResult('Test accessibility message');
        await new Promise(resolve => setTimeout(resolve, 50));

        await voiceController.playResponse('This is the accessibility test response');
        await new Promise(resolve => setTimeout(resolve, 150));

        // Verify accessibility announcements
        this.assert(
            accessibilityAnnouncements.length >= 3,
            'should make accessibility announcements'
        );
        this.assert(
            accessibilityAnnouncements.some(a => a.message.includes('recording started')),
            'should announce recording start'
        );
        this.assert(
            accessibilityAnnouncements.some(a => a.message.includes('Transcribed:')),
            'should announce transcription'
        );
        this.assert(
            accessibilityAnnouncements.some(a => a.message.includes('Playing response')),
            'should announce response playback'
        );

        // Test error accessibility
        voiceController.recognition._simulateError('network');
        await new Promise(resolve => setTimeout(resolve, 20));

        this.assert(
            accessibilityAnnouncements.some(a => a.message.includes('Voice error')),
            'should announce errors accessibly'
        );
        this.assert(
            accessibilityAnnouncements.some(a => a.priority === 'assertive'),
            'should use assertive priority for important announcements'
        );
    }

    // Helper methods
    createMockVoiceController() {
        const controller = {
            isRecording: false,
            isSpeaking: false,
            speechQueue: [],
            recognition: null,
            currentUtterance: null,
            listeners: new Map(),
            
            settings: {
                data: {
                    speechRate: 1.0,
                    language: 'en-US',
                    autoPlayEnabled: false,
                    voiceName: 'default'
                },
                
                get: function() {
                    return { ...this.data };
                },
                
                getValue: function(key) {
                    return this.data[key];
                },
                
                update: function(updates) {
                    Object.assign(this.data, updates);
                    return true;
                }
            },

            addEventListener: function(event, callback) {
                if (!this.listeners.has(event)) {
                    this.listeners.set(event, []);
                }
                this.listeners.get(event).push(callback);
            },

            removeEventListener: function(event, callback) {
                if (this.listeners.has(event)) {
                    const callbacks = this.listeners.get(event);
                    const index = callbacks.indexOf(callback);
                    if (index > -1) {
                        callbacks.splice(index, 1);
                    }
                }
            },

            emit: function(event, data) {
                if (this.listeners.has(event)) {
                    this.listeners.get(event).forEach(callback => {
                        try {
                            callback(data);
                        } catch (error) {
                            console.error('Event callback error:', error);
                        }
                    });
                }
            },

            startRecording: async function() {
                if (this.isRecording) return false;
                
                this.recognition = new mockSpeechRecognition();
                this.recognition.lang = this.settings.getValue('language');
                
                this.recognition.onstart = () => {
                    this.isRecording = true;
                    this.emit('recording_started');
                };
                
                this.recognition.onresult = (event) => {
                    const result = event.results[0][0];
                    this.emit('final_result', {
                        transcript: result.transcript,
                        confidence: result.confidence
                    });
                };
                
                this.recognition.onerror = (event) => {
                    this.emit('error', {
                        type: 'speech_recognition',
                        error: event.error,
                        message: `Speech recognition error: ${event.error}`
                    });
                };
                
                this.recognition.onend = () => {
                    this.isRecording = false;
                    this.emit('recording_stopped');
                };

                this.recognition.start();
                return true;
            },

            stopRecording: function() {
                if (this.recognition && this.isRecording) {
                    this.recognition.stop();
                }
            },

            playResponse: async function(text) {
                if (!text || typeof text !== 'string') return false;
                
                if (this.isSpeaking) {
                    this.speechQueue.push(text);
                    this.emit('speech_queued', { text });
                    return true;
                }
                
                return this._playNow(text);
            },

            _playNow: async function(text) {
                this.isSpeaking = true;
                this.emit('speech_started', { text });
                
                // Simulate speech synthesis
                setTimeout(() => {
                    this.isSpeaking = false;
                    this.emit('speech_ended', { text });
                    
                    // Play next in queue
                    if (this.speechQueue.length > 0) {
                        const nextText = this.speechQueue.shift();
                        this._playNow(nextText);
                    }
                }, 100);
                
                return true;
            },

            updateSettings: function(updates) {
                return this.settings.update(updates);
            },

            createUtterance: async function(text) {
                const utterance = new window.SpeechSynthesisUtterance(text);
                utterance.rate = this.settings.getValue('speechRate');
                utterance.lang = this.settings.getValue('language');
                return utterance;
            }
        };

        // Add reference to mock speech recognition
        const mockSpeechRecognition = this.mockSpeechRecognition;
        
        return controller;
    }

    printResults() {
        console.log('\n=== Voice E2E Test Results ===');
        
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

// Export for use in other test files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceE2ETest;
}

// Browser environment
if (typeof window !== 'undefined') {
    window.VoiceE2ETest = VoiceE2ETest;
}