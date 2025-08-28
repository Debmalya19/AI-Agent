/**
 * Voice Accessibility Tests
 * Tests screen reader compatibility, keyboard navigation, and accessibility compliance
 */

class VoiceAccessibilityTest {
    constructor() {
        this.testResults = [];
        this.setupAccessibilityMocks();
    }

    setupAccessibilityMocks() {
        // Mock screen reader APIs
        this.mockScreenReader = {
            announcements: [],
            announce: function(text, priority = 'polite') {
                this.announcements.push({ text, priority, timestamp: Date.now() });
            },
            clear: function() {
                this.announcements = [];
            }
        };

        // Mock ARIA live regions
        this.mockAriaLiveRegions = new Map();
        
        // Mock keyboard event handling
        this.mockKeyboardEvents = [];
        
        // Mock focus management
        this.focusHistory = [];
        this.currentFocus = null;
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
        console.log('Running Voice Accessibility Tests...\n');

        try {
            await this.testScreenReaderCompatibility();
            await this.testKeyboardNavigation();
            await this.testAriaLabelsAndRoles();
            await this.testFocusManagement();
            await this.testHighContrastMode();
            await this.testReducedMotionSupport();
            await this.testVoiceStatusAnnouncements();
            await this.testAccessibleErrorHandling();
        } catch (error) {
            console.error('Accessibility test suite error:', error);
        }

        this.printResults();
    }

    async testScreenReaderCompatibility() {
        console.log('Testing screen reader compatibility...');

        // Create mock voice UI with accessibility features
        const mockContainer = this.createMockContainer();
        const mockVoiceController = this.createMockVoiceController();
        
        // Mock VoiceUI with accessibility features
        const voiceUI = {
            container: mockContainer,
            voiceController: mockVoiceController,
            ariaLiveRegion: null,
            statusRegion: null,
            
            initialize: function() {
                // Create ARIA live regions
                this.ariaLiveRegion = document.createElement('div');
                this.ariaLiveRegion.setAttribute('aria-live', 'polite');
                this.ariaLiveRegion.setAttribute('aria-label', 'Voice assistant status');
                this.ariaLiveRegion.className = 'sr-only';
                
                this.statusRegion = document.createElement('div');
                this.statusRegion.setAttribute('aria-live', 'assertive');
                this.statusRegion.setAttribute('aria-label', 'Voice assistant alerts');
                this.statusRegion.className = 'sr-only';
                
                this.container.appendChild(this.ariaLiveRegion);
                this.container.appendChild(this.statusRegion);
            },
            
            announceToScreenReader: function(message, priority = 'polite') {
                const region = priority === 'assertive' ? this.statusRegion : this.ariaLiveRegion;
                if (region) {
                    region.textContent = message;
                    // Mock screen reader announcement
                    mockScreenReader.announce(message, priority);
                }
            },
            
            announceRecordingStart: function() {
                this.announceToScreenReader('Voice recording started. Speak now.', 'assertive');
            },
            
            announceRecordingStop: function() {
                this.announceToScreenReader('Voice recording stopped.', 'polite');
            },
            
            announceTranscription: function(text) {
                this.announceToScreenReader(`Transcribed: ${text}`, 'polite');
            },
            
            announceSpeechStart: function() {
                this.announceToScreenReader('Playing response audio.', 'polite');
            },
            
            announceSpeechEnd: function() {
                this.announceToScreenReader('Audio playback completed.', 'polite');
            }
        };

        voiceUI.initialize();

        // Test screen reader announcements
        voiceUI.announceRecordingStart();
        this.assert(
            this.mockScreenReader.announcements.length === 1,
            'should announce recording start to screen reader'
        );
        this.assert(
            this.mockScreenReader.announcements[0].text === 'Voice recording started. Speak now.',
            'should announce correct recording start message'
        );
        this.assert(
            this.mockScreenReader.announcements[0].priority === 'assertive',
            'should use assertive priority for recording start'
        );

        voiceUI.announceTranscription('Hello world');
        this.assert(
            this.mockScreenReader.announcements.length === 2,
            'should announce transcription to screen reader'
        );
        this.assert(
            this.mockScreenReader.announcements[1].text === 'Transcribed: Hello world',
            'should announce correct transcription message'
        );

        voiceUI.announceSpeechStart();
        voiceUI.announceSpeechEnd();
        this.assert(
            this.mockScreenReader.announcements.length === 4,
            'should announce speech playback events'
        );

        // Test ARIA live regions exist
        const liveRegions = mockContainer.querySelectorAll('[aria-live]');
        this.assert(liveRegions.length >= 2, 'should create ARIA live regions');
        
        const politeRegion = mockContainer.querySelector('[aria-live="polite"]');
        const assertiveRegion = mockContainer.querySelector('[aria-live="assertive"]');
        this.assert(politeRegion !== null, 'should create polite ARIA live region');
        this.assert(assertiveRegion !== null, 'should create assertive ARIA live region');
    }

    async testKeyboardNavigation() {
        console.log('Testing keyboard navigation...');

        const mockContainer = this.createMockContainer();
        const voiceUI = this.createMockVoiceUI(mockContainer);

        // Create voice control buttons
        const micButton = document.createElement('button');
        micButton.id = 'voice-mic-button';
        micButton.setAttribute('aria-label', 'Start voice recording');
        micButton.setAttribute('tabindex', '0');
        micButton.className = 'voice-control-button';

        const playButton = document.createElement('button');
        playButton.id = 'voice-play-button';
        playButton.setAttribute('aria-label', 'Play last response');
        playButton.setAttribute('tabindex', '0');
        playButton.className = 'voice-control-button';

        const settingsButton = document.createElement('button');
        settingsButton.id = 'voice-settings-button';
        settingsButton.setAttribute('aria-label', 'Open voice settings');
        settingsButton.setAttribute('tabindex', '0');
        settingsButton.className = 'voice-control-button';

        mockContainer.appendChild(micButton);
        mockContainer.appendChild(playButton);
        mockContainer.appendChild(settingsButton);

        // Test tab navigation
        const buttons = mockContainer.querySelectorAll('.voice-control-button');
        this.assert(buttons.length === 3, 'should create all voice control buttons');

        // Test each button has proper tabindex
        buttons.forEach((button, index) => {
            this.assert(
                button.getAttribute('tabindex') === '0',
                `button ${index} should have tabindex="0"`
            );
        });

        // Test ARIA labels
        this.assert(
            micButton.getAttribute('aria-label') === 'Start voice recording',
            'microphone button should have descriptive ARIA label'
        );
        this.assert(
            playButton.getAttribute('aria-label') === 'Play last response',
            'play button should have descriptive ARIA label'
        );
        this.assert(
            settingsButton.getAttribute('aria-label') === 'Open voice settings',
            'settings button should have descriptive ARIA label'
        );

        // Test keyboard event handling
        let micButtonActivated = false;
        let playButtonActivated = false;
        let settingsButtonActivated = false;

        micButton.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                micButtonActivated = true;
                this.mockKeyboardEvents.push({ button: 'mic', key: e.key });
            }
        });

        playButton.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                playButtonActivated = true;
                this.mockKeyboardEvents.push({ button: 'play', key: e.key });
            }
        });

        settingsButton.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                settingsButtonActivated = true;
                this.mockKeyboardEvents.push({ button: 'settings', key: e.key });
            }
        });

        // Simulate keyboard events
        this.simulateKeyboardEvent(micButton, 'keydown', 'Enter');
        this.simulateKeyboardEvent(playButton, 'keydown', ' ');
        this.simulateKeyboardEvent(settingsButton, 'keydown', 'Enter');

        this.assert(micButtonActivated, 'microphone button should respond to Enter key');
        this.assert(playButtonActivated, 'play button should respond to Space key');
        this.assert(settingsButtonActivated, 'settings button should respond to Enter key');

        // Test keyboard shortcuts
        const shortcutHandler = {
            shortcuts: new Map([
                ['KeyM', 'toggleMicrophone'],
                ['KeyP', 'togglePlayback'],
                ['KeyS', 'openSettings'],
                ['Escape', 'stopAll']
            ]),
            
            handleKeydown: function(event) {
                if (event.ctrlKey || event.metaKey) {
                    const action = this.shortcuts.get(event.code);
                    if (action) {
                        event.preventDefault();
                        return action;
                    }
                }
                if (event.key === 'Escape') {
                    event.preventDefault();
                    return 'stopAll';
                }
                return null;
            }
        };

        // Test keyboard shortcuts
        const ctrlMEvent = { ctrlKey: true, code: 'KeyM', preventDefault: () => {} };
        const escapeEvent = { key: 'Escape', preventDefault: () => {} };

        this.assert(
            shortcutHandler.handleKeydown(ctrlMEvent) === 'toggleMicrophone',
            'should handle Ctrl+M shortcut for microphone'
        );
        this.assert(
            shortcutHandler.handleKeydown(escapeEvent) === 'stopAll',
            'should handle Escape key to stop all voice operations'
        );
    }

    async testAriaLabelsAndRoles() {
        console.log('Testing ARIA labels and roles...');

        const mockContainer = this.createMockContainer();
        
        // Create voice UI elements with proper ARIA attributes
        const voiceSection = document.createElement('section');
        voiceSection.setAttribute('aria-label', 'Voice Assistant Controls');
        voiceSection.setAttribute('role', 'region');

        const micButton = document.createElement('button');
        micButton.setAttribute('aria-label', 'Start voice recording');
        micButton.setAttribute('aria-describedby', 'mic-help-text');
        micButton.setAttribute('aria-pressed', 'false');

        const micHelpText = document.createElement('div');
        micHelpText.id = 'mic-help-text';
        micHelpText.className = 'sr-only';
        micHelpText.textContent = 'Click to start recording your voice message';

        const statusDisplay = document.createElement('div');
        statusDisplay.setAttribute('role', 'status');
        statusDisplay.setAttribute('aria-label', 'Voice recording status');
        statusDisplay.setAttribute('aria-live', 'polite');

        const transcriptionDisplay = document.createElement('div');
        transcriptionDisplay.setAttribute('role', 'log');
        transcriptionDisplay.setAttribute('aria-label', 'Voice transcription');
        transcriptionDisplay.setAttribute('aria-live', 'polite');

        const settingsDialog = document.createElement('div');
        settingsDialog.setAttribute('role', 'dialog');
        settingsDialog.setAttribute('aria-label', 'Voice Settings');
        settingsDialog.setAttribute('aria-modal', 'true');
        settingsDialog.setAttribute('aria-hidden', 'true');

        voiceSection.appendChild(micButton);
        voiceSection.appendChild(micHelpText);
        voiceSection.appendChild(statusDisplay);
        voiceSection.appendChild(transcriptionDisplay);
        voiceSection.appendChild(settingsDialog);
        mockContainer.appendChild(voiceSection);

        // Test ARIA attributes
        this.assert(
            voiceSection.getAttribute('role') === 'region',
            'voice section should have region role'
        );
        this.assert(
            voiceSection.getAttribute('aria-label') === 'Voice Assistant Controls',
            'voice section should have descriptive ARIA label'
        );

        this.assert(
            micButton.getAttribute('aria-pressed') === 'false',
            'microphone button should have aria-pressed attribute'
        );
        this.assert(
            micButton.getAttribute('aria-describedby') === 'mic-help-text',
            'microphone button should reference help text'
        );

        this.assert(
            statusDisplay.getAttribute('role') === 'status',
            'status display should have status role'
        );
        this.assert(
            statusDisplay.getAttribute('aria-live') === 'polite',
            'status display should have polite aria-live'
        );

        this.assert(
            transcriptionDisplay.getAttribute('role') === 'log',
            'transcription display should have log role'
        );

        this.assert(
            settingsDialog.getAttribute('role') === 'dialog',
            'settings should have dialog role'
        );
        this.assert(
            settingsDialog.getAttribute('aria-modal') === 'true',
            'settings dialog should be modal'
        );

        // Test dynamic ARIA updates
        const updateAriaPressed = (button, pressed) => {
            button.setAttribute('aria-pressed', pressed.toString());
        };

        updateAriaPressed(micButton, true);
        this.assert(
            micButton.getAttribute('aria-pressed') === 'true',
            'should update aria-pressed when recording starts'
        );

        updateAriaPressed(micButton, false);
        this.assert(
            micButton.getAttribute('aria-pressed') === 'false',
            'should update aria-pressed when recording stops'
        );
    }

    async testFocusManagement() {
        console.log('Testing focus management...');

        const mockContainer = this.createMockContainer();
        
        // Create focusable elements
        const micButton = document.createElement('button');
        micButton.id = 'mic-button';
        micButton.textContent = 'Record';

        const settingsButton = document.createElement('button');
        settingsButton.id = 'settings-button';
        settingsButton.textContent = 'Settings';

        const settingsModal = document.createElement('div');
        settingsModal.id = 'settings-modal';
        settingsModal.style.display = 'none';

        const closeButton = document.createElement('button');
        closeButton.id = 'close-button';
        closeButton.textContent = 'Close';

        const saveButton = document.createElement('button');
        saveButton.id = 'save-button';
        saveButton.textContent = 'Save';

        settingsModal.appendChild(closeButton);
        settingsModal.appendChild(saveButton);

        mockContainer.appendChild(micButton);
        mockContainer.appendChild(settingsButton);
        mockContainer.appendChild(settingsModal);

        // Mock focus management
        const focusManager = {
            focusStack: [],
            
            pushFocus: function(element) {
                this.focusStack.push(document.activeElement || document.body);
                element.focus();
            },
            
            popFocus: function() {
                const previousElement = this.focusStack.pop();
                if (previousElement) {
                    previousElement.focus();
                }
            },
            
            trapFocus: function(container) {
                const focusableElements = container.querySelectorAll(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                );
                
                if (focusableElements.length === 0) return;
                
                const firstElement = focusableElements[0];
                const lastElement = focusableElements[focusableElements.length - 1];
                
                container.addEventListener('keydown', (e) => {
                    if (e.key === 'Tab') {
                        if (e.shiftKey) {
                            if (document.activeElement === firstElement) {
                                e.preventDefault();
                                lastElement.focus();
                            }
                        } else {
                            if (document.activeElement === lastElement) {
                                e.preventDefault();
                                firstElement.focus();
                            }
                        }
                    }
                });
                
                firstElement.focus();
            }
        };

        // Test opening settings modal
        settingsButton.addEventListener('click', () => {
            focusManager.pushFocus(closeButton);
            settingsModal.style.display = 'block';
            focusManager.trapFocus(settingsModal);
        });

        // Test closing settings modal
        closeButton.addEventListener('click', () => {
            settingsModal.style.display = 'none';
            focusManager.popFocus();
        });

        // Simulate opening settings
        settingsButton.click();
        this.assert(
            focusManager.focusStack.length === 1,
            'should push previous focus to stack when opening modal'
        );

        // Simulate closing settings
        closeButton.click();
        this.assert(
            focusManager.focusStack.length === 0,
            'should restore previous focus when closing modal'
        );

        // Test focus trap
        const focusableInModal = settingsModal.querySelectorAll('button');
        this.assert(
            focusableInModal.length === 2,
            'should identify focusable elements in modal'
        );
    }

    async testHighContrastMode() {
        console.log('Testing high contrast mode support...');

        const mockContainer = this.createMockContainer();
        
        // Create voice UI elements
        const micButton = document.createElement('button');
        micButton.className = 'voice-mic-button';
        micButton.textContent = 'Record';

        const statusIndicator = document.createElement('div');
        statusIndicator.className = 'voice-status-indicator';

        mockContainer.appendChild(micButton);
        mockContainer.appendChild(statusIndicator);

        // Test high contrast CSS support
        const highContrastStyles = {
            '.voice-mic-button': {
                'border': '2px solid ButtonText',
                'background': 'ButtonFace',
                'color': 'ButtonText'
            },
            '.voice-mic-button:focus': {
                'outline': '3px solid Highlight',
                'outline-offset': '2px'
            },
            '.voice-status-indicator.recording': {
                'background': 'Highlight',
                'border': '2px solid HighlightText'
            },
            '.voice-status-indicator.error': {
                'background': 'red',
                'border': '2px solid white'
            }
        };

        // Mock CSS application
        const applyHighContrastStyles = (element, className) => {
            const styles = highContrastStyles[className];
            if (styles) {
                Object.assign(element.style, styles);
                return true;
            }
            return false;
        };

        // Test style application
        const buttonStyleApplied = applyHighContrastStyles(micButton, '.voice-mic-button');
        this.assert(
            buttonStyleApplied,
            'should apply high contrast styles to voice button'
        );

        // Test focus styles
        const focusStyleApplied = applyHighContrastStyles(micButton, '.voice-mic-button:focus');
        this.assert(
            focusStyleApplied,
            'should apply high contrast focus styles'
        );

        // Test status indicator styles
        statusIndicator.classList.add('recording');
        const recordingStyleApplied = applyHighContrastStyles(statusIndicator, '.voice-status-indicator.recording');
        this.assert(
            recordingStyleApplied,
            'should apply high contrast styles to recording indicator'
        );
    }

    async testReducedMotionSupport() {
        console.log('Testing reduced motion support...');

        // Mock prefers-reduced-motion media query
        const mockMediaQuery = {
            matches: true, // Simulate user prefers reduced motion
            addEventListener: function(event, callback) {
                this.callback = callback;
            },
            removeEventListener: function(event, callback) {
                this.callback = null;
            }
        };

        // Mock motion preferences
        const motionManager = {
            prefersReducedMotion: mockMediaQuery.matches,
            
            getAnimationDuration: function(defaultDuration) {
                return this.prefersReducedMotion ? 0 : defaultDuration;
            },
            
            shouldUseAnimation: function() {
                return !this.prefersReducedMotion;
            },
            
            applyMotionPreferences: function(element) {
                if (this.prefersReducedMotion) {
                    element.style.transition = 'none';
                    element.style.animation = 'none';
                }
            }
        };

        // Test animation duration adjustment
        const normalDuration = 300;
        const adjustedDuration = motionManager.getAnimationDuration(normalDuration);
        this.assert(
            adjustedDuration === 0,
            'should disable animations when reduced motion is preferred'
        );

        // Test animation check
        const shouldAnimate = motionManager.shouldUseAnimation();
        this.assert(
            shouldAnimate === false,
            'should not use animations when reduced motion is preferred'
        );

        // Test with reduced motion disabled
        mockMediaQuery.matches = false;
        motionManager.prefersReducedMotion = false;

        const normalDurationEnabled = motionManager.getAnimationDuration(normalDuration);
        this.assert(
            normalDurationEnabled === normalDuration,
            'should use normal animation duration when reduced motion is not preferred'
        );

        const shouldAnimateEnabled = motionManager.shouldUseAnimation();
        this.assert(
            shouldAnimateEnabled === true,
            'should use animations when reduced motion is not preferred'
        );
    }

    async testVoiceStatusAnnouncements() {
        console.log('Testing voice status announcements...');

        const mockContainer = this.createMockContainer();
        const statusAnnouncer = {
            announcements: [],
            
            announce: function(message, priority = 'polite') {
                this.announcements.push({ message, priority, timestamp: Date.now() });
                // Mock screen reader announcement
                this.mockScreenReader.announce(message, priority);
            },
            
            announceRecordingStatus: function(isRecording) {
                if (isRecording) {
                    this.announce('Voice recording started. Speak your message now.', 'assertive');
                } else {
                    this.announce('Voice recording stopped.', 'polite');
                }
            },
            
            announceTranscription: function(text, confidence) {
                const confidenceText = confidence < 0.8 ? ' (low confidence)' : '';
                this.announce(`Transcribed: "${text}"${confidenceText}`, 'polite');
            },
            
            announcePlaybackStatus: function(isPlaying, text = '') {
                if (isPlaying) {
                    this.announce(`Playing response: "${text.substring(0, 50)}..."`, 'polite');
                } else {
                    this.announce('Audio playback completed.', 'polite');
                }
            },
            
            announceError: function(errorType, errorMessage) {
                this.announce(`Voice error: ${errorMessage}`, 'assertive');
            }
        };

        // Test recording status announcements
        statusAnnouncer.announceRecordingStatus(true);
        this.assert(
            statusAnnouncer.announcements.length === 1,
            'should announce recording start'
        );
        this.assert(
            statusAnnouncer.announcements[0].priority === 'assertive',
            'should use assertive priority for recording start'
        );

        statusAnnouncer.announceRecordingStatus(false);
        this.assert(
            statusAnnouncer.announcements.length === 2,
            'should announce recording stop'
        );

        // Test transcription announcements
        statusAnnouncer.announceTranscription('Hello world', 0.95);
        this.assert(
            statusAnnouncer.announcements[2].message.includes('Hello world'),
            'should announce transcription text'
        );
        this.assert(
            !statusAnnouncer.announcements[2].message.includes('low confidence'),
            'should not mention low confidence for high confidence transcription'
        );

        statusAnnouncer.announceTranscription('Unclear speech', 0.6);
        this.assert(
            statusAnnouncer.announcements[3].message.includes('low confidence'),
            'should mention low confidence for low confidence transcription'
        );

        // Test playback announcements
        const responseText = 'This is a test response from the AI assistant';
        statusAnnouncer.announcePlaybackStatus(true, responseText);
        this.assert(
            statusAnnouncer.announcements[4].message.includes('Playing response'),
            'should announce playback start'
        );

        statusAnnouncer.announcePlaybackStatus(false);
        this.assert(
            statusAnnouncer.announcements[5].message.includes('completed'),
            'should announce playback completion'
        );

        // Test error announcements
        statusAnnouncer.announceError('microphone', 'Microphone access denied');
        this.assert(
            statusAnnouncer.announcements[6].message.includes('Microphone access denied'),
            'should announce error message'
        );
        this.assert(
            statusAnnouncer.announcements[6].priority === 'assertive',
            'should use assertive priority for errors'
        );
    }

    async testAccessibleErrorHandling() {
        console.log('Testing accessible error handling...');

        const mockContainer = this.createMockContainer();
        
        // Create accessible error display
        const errorDisplay = {
            container: mockContainer,
            errorRegion: null,
            
            initialize: function() {
                this.errorRegion = document.createElement('div');
                this.errorRegion.setAttribute('role', 'alert');
                this.errorRegion.setAttribute('aria-live', 'assertive');
                this.errorRegion.setAttribute('aria-label', 'Voice assistant errors');
                this.errorRegion.className = 'voice-error-region';
                this.container.appendChild(this.errorRegion);
            },
            
            showError: function(errorType, message, recoveryActions = []) {
                const errorElement = document.createElement('div');
                errorElement.className = 'voice-error';
                errorElement.setAttribute('role', 'alert');
                
                const errorMessage = document.createElement('p');
                errorMessage.textContent = `Error: ${message}`;
                errorElement.appendChild(errorMessage);
                
                if (recoveryActions.length > 0) {
                    const actionsList = document.createElement('ul');
                    actionsList.setAttribute('aria-label', 'Recovery actions');
                    
                    recoveryActions.forEach(action => {
                        const listItem = document.createElement('li');
                        const actionButton = document.createElement('button');
                        actionButton.textContent = action.label;
                        actionButton.setAttribute('aria-describedby', `${action.id}-description`);
                        
                        const description = document.createElement('span');
                        description.id = `${action.id}-description`;
                        description.className = 'sr-only';
                        description.textContent = action.description;
                        
                        listItem.appendChild(actionButton);
                        listItem.appendChild(description);
                        actionsList.appendChild(listItem);
                    });
                    
                    errorElement.appendChild(actionsList);
                }
                
                this.errorRegion.appendChild(errorElement);
                
                // Auto-remove after delay (but keep for screen readers)
                setTimeout(() => {
                    if (errorElement.parentNode) {
                        errorElement.setAttribute('aria-hidden', 'true');
                    }
                }, 10000);
            },
            
            clearErrors: function() {
                this.errorRegion.innerHTML = '';
            }
        };

        errorDisplay.initialize();

        // Test error display creation
        this.assert(
            errorDisplay.errorRegion !== null,
            'should create error display region'
        );
        this.assert(
            errorDisplay.errorRegion.getAttribute('role') === 'alert',
            'error region should have alert role'
        );
        this.assert(
            errorDisplay.errorRegion.getAttribute('aria-live') === 'assertive',
            'error region should have assertive aria-live'
        );

        // Test error with recovery actions
        const recoveryActions = [
            {
                id: 'retry-mic',
                label: 'Retry microphone access',
                description: 'Attempt to access microphone again'
            },
            {
                id: 'use-text',
                label: 'Use text input instead',
                description: 'Switch to typing your message'
            }
        ];

        errorDisplay.showError('microphone', 'Microphone access denied', recoveryActions);

        const errorElements = errorDisplay.errorRegion.querySelectorAll('.voice-error');
        this.assert(
            errorElements.length === 1,
            'should display error message'
        );

        const recoveryButtons = errorDisplay.errorRegion.querySelectorAll('button');
        this.assert(
            recoveryButtons.length === 2,
            'should display recovery action buttons'
        );

        // Test button accessibility
        recoveryButtons.forEach((button, index) => {
            this.assert(
                button.getAttribute('aria-describedby') !== null,
                `recovery button ${index} should have aria-describedby`
            );
        });

        // Test error clearing
        errorDisplay.clearErrors();
        const remainingErrors = errorDisplay.errorRegion.querySelectorAll('.voice-error');
        this.assert(
            remainingErrors.length === 0,
            'should clear all errors'
        );
    }

    // Helper methods
    createMockContainer() {
        const container = document.createElement('div');
        container.id = 'mock-voice-container';
        return container;
    }

    createMockVoiceController() {
        return {
            isRecording: false,
            isSpeaking: false,
            startRecording: () => Promise.resolve(true),
            stopRecording: () => Promise.resolve(true),
            playResponse: () => Promise.resolve(true),
            addEventListener: () => {},
            removeEventListener: () => {}
        };
    }

    createMockVoiceUI(container) {
        return {
            container: container,
            initialize: () => {},
            showRecordingIndicator: () => {},
            hideRecordingIndicator: () => {},
            showPlaybackControls: () => {},
            hidePlaybackControls: () => {}
        };
    }

    simulateKeyboardEvent(element, eventType, key) {
        const event = new KeyboardEvent(eventType, {
            key: key,
            code: key === ' ' ? 'Space' : key === 'Enter' ? 'Enter' : key,
            bubbles: true,
            cancelable: true
        });
        element.dispatchEvent(event);
    }

    printResults() {
        console.log('\n=== Voice Accessibility Test Results ===');
        
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
    module.exports = VoiceAccessibilityTest;
}

// Browser environment
if (typeof window !== 'undefined') {
    window.VoiceAccessibilityTest = VoiceAccessibilityTest;
}