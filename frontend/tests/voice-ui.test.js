/**
 * Voice UI Tests
 * Tests for the VoiceUI class functionality
 */

// Mock VoiceController for testing
class MockVoiceController {
    constructor() {
        this.listeners = new Map();
        this.state = {
            isRecording: false,
            isSpeaking: false,
            queueLength: 0,
            capabilities: {
                voiceInputSupported: true,
                voiceOutputSupported: true,
                speechSynthesis: true,
                speechRecognition: true
            },
            settings: {
                autoPlayEnabled: false,
                voiceName: 'default',
                speechRate: 1.0,
                speechPitch: 1.0,
                speechVolume: 1.0,
                language: 'en-US',
                microphoneSensitivity: 0.5,
                noiseCancellation: true,
                visualFeedbackEnabled: true
            }
        };
        this.availableVoices = [
            { name: 'Default Voice', lang: 'en-US' },
            { name: 'Google US English', lang: 'en-US' },
            { name: 'Microsoft Zira', lang: 'en-US' }
        ];
        this.settings = {
            getDefaults: () => this.state.settings
        };
    }

    addEventListener(event, listener) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(listener);
    }

    removeEventListener(event, listener) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).delete(listener);
        }
    }

    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(listener => listener(data));
        }
    }

    getState() {
        return this.state;
    }

    getAvailableVoices() {
        return this.availableVoices;
    }

    async startRecording() {
        this.state.isRecording = true;
        this.emit('recording_started');
        return true;
    }

    stopRecording() {
        this.state.isRecording = false;
        this.emit('recording_stopped');
    }

    async playResponse(text) {
        this.state.isSpeaking = true;
        this.emit('speech_started', { text });
        return true;
    }

    pausePlayback() {
        this.emit('speech_paused');
    }

    resumePlayback() {
        this.emit('speech_resumed');
    }

    stopPlayback() {
        this.state.isSpeaking = false;
        this.emit('speech_ended', { text: '' });
    }

    updateSettings(settings) {
        this.state.settings = { ...this.state.settings, ...settings };
        this.emit('settings_changed', { settings: this.state.settings });
        return true;
    }
}

// Test suite
function runVoiceUITests() {
    console.log('Running Voice UI Tests...');

    // Test 1: VoiceUI Initialization
    test('VoiceUI should initialize correctly', () => {
        const container = document.createElement('div');
        const mockController = new MockVoiceController();
        
        const voiceUI = new VoiceUI(container, mockController);
        
        assert(voiceUI.isInitialized, 'VoiceUI should be initialized');
        assert(container.querySelector('.voice-controls-container'), 'Voice controls container should be created');
        assert(container.querySelector('.voice-mic-button'), 'Microphone button should be created');
        assert(container.querySelector('.voice-playback-controls'), 'Playback controls should be created');
        assert(container.querySelector('.voice-settings-button'), 'Settings button should be created');
        assert(container.querySelector('.voice-feedback-area'), 'Feedback area should be created');
        
        console.log('✓ VoiceUI initialization test passed');
    });

    // Test 2: Microphone Button Functionality
    test('Microphone button should toggle recording', async () => {
        const container = document.createElement('div');
        const mockController = new MockVoiceController();
        
        const voiceUI = new VoiceUI(container, mockController);
        const micButton = container.querySelector('.voice-mic-button');
        
        // Test start recording
        micButton.click();
        await new Promise(resolve => setTimeout(resolve, 10)); // Allow async operation
        
        assert(mockController.state.isRecording, 'Recording should be started');
        assert(micButton.classList.contains('recording'), 'Button should show recording state');
        
        // Test stop recording
        micButton.click();
        await new Promise(resolve => setTimeout(resolve, 10));
        
        assert(!mockController.state.isRecording, 'Recording should be stopped');
        assert(!micButton.classList.contains('recording'), 'Button should not show recording state');
        
        console.log('✓ Microphone button functionality test passed');
    });

    // Test 3: Settings Modal
    test('Settings modal should open and close', () => {
        const container = document.createElement('div');
        const mockController = new MockVoiceController();
        
        const voiceUI = new VoiceUI(container, mockController);
        const settingsButton = container.querySelector('.voice-settings-button');
        const modal = document.querySelector('.voice-settings-modal');
        const backdrop = document.querySelector('.voice-settings-backdrop');
        
        // Test open modal
        settingsButton.click();
        assert(voiceUI.settingsModalOpen, 'Settings modal should be open');
        assert(backdrop.style.display === 'flex', 'Modal backdrop should be visible');
        
        // Test close modal
        const closeButton = modal.querySelector('.voice-settings-close');
        closeButton.click();
        assert(!voiceUI.settingsModalOpen, 'Settings modal should be closed');
        assert(backdrop.style.display === 'none', 'Modal backdrop should be hidden');
        
        console.log('✓ Settings modal functionality test passed');
    });

    // Test 4: Visual Feedback
    test('Visual feedback should update correctly', () => {
        const container = document.createElement('div');
        const mockController = new MockVoiceController();
        
        const voiceUI = new VoiceUI(container, mockController);
        const statusText = container.querySelector('.voice-status-text');
        const visualIndicator = container.querySelector('.voice-visual-indicator');
        
        // Test recording state
        mockController.emit('recording_started');
        assert(statusText.textContent.includes('Listening'), 'Status should show listening');
        assert(visualIndicator.classList.contains('recording'), 'Visual indicator should show recording');
        
        // Test speech state
        mockController.emit('speech_started', { text: 'Test speech' });
        assert(visualIndicator.classList.contains('speaking'), 'Visual indicator should show speaking');
        
        console.log('✓ Visual feedback test passed');
    });

    // Test 5: Transcription Display
    test('Transcription should display correctly', () => {
        const container = document.createElement('div');
        const mockController = new MockVoiceController();
        
        const voiceUI = new VoiceUI(container, mockController);
        const transcriptDisplay = container.querySelector('.voice-transcript-display');
        
        // Test interim result
        mockController.emit('interim_result', { transcript: 'Hello world' });
        assert(transcriptDisplay.textContent === 'Hello world', 'Interim transcript should be displayed');
        assert(transcriptDisplay.classList.contains('interim'), 'Should show interim styling');
        
        // Test final result
        mockController.emit('final_result', { transcript: 'Hello world!', confidence: 0.9 });
        assert(transcriptDisplay.textContent === 'Hello world!', 'Final transcript should be displayed');
        assert(transcriptDisplay.classList.contains('final'), 'Should show final styling');
        
        console.log('✓ Transcription display test passed');
    });

    // Test 6: Error Handling
    test('Error states should be handled correctly', () => {
        const container = document.createElement('div');
        const mockController = new MockVoiceController();
        
        const voiceUI = new VoiceUI(container, mockController);
        const statusText = container.querySelector('.voice-status-text');
        
        // Test error display
        mockController.emit('error', { 
            type: 'speech_recognition', 
            message: 'Microphone access denied' 
        });
        
        assert(statusText.textContent.includes('Error'), 'Error should be displayed');
        assert(statusText.classList.contains('error'), 'Error styling should be applied');
        
        console.log('✓ Error handling test passed');
    });

    // Test 7: Keyboard Shortcuts
    test('Keyboard shortcuts should work', async () => {
        const container = document.createElement('div');
        const mockController = new MockVoiceController();
        
        const voiceUI = new VoiceUI(container, mockController);
        
        // Test Ctrl+Shift+V for recording
        const keyEvent = new KeyboardEvent('keydown', {
            key: 'V',
            ctrlKey: true,
            shiftKey: true
        });
        
        document.dispatchEvent(keyEvent);
        await new Promise(resolve => setTimeout(resolve, 10));
        
        assert(mockController.state.isRecording, 'Keyboard shortcut should start recording');
        
        console.log('✓ Keyboard shortcuts test passed');
    });

    // Test 8: Responsive Design
    test('UI should be responsive', () => {
        const container = document.createElement('div');
        const mockController = new MockVoiceController();
        
        const voiceUI = new VoiceUI(container, mockController);
        const controlsContainer = container.querySelector('.voice-controls-container');
        
        // Check if responsive classes exist in CSS
        const styles = document.getElementById('voice-ui-styles');
        assert(styles, 'Voice UI styles should be added');
        assert(styles.textContent.includes('@media'), 'Responsive styles should be included');
        
        console.log('✓ Responsive design test passed');
    });

    // Test 9: Accessibility Features
    test('Accessibility features should be present', () => {
        const container = document.createElement('div');
        const mockController = new MockVoiceController();
        
        const voiceUI = new VoiceUI(container, mockController);
        
        // Check ARIA labels
        const micButton = container.querySelector('.voice-mic-button');
        const feedbackArea = container.querySelector('.voice-feedback-area');
        const playbackControls = container.querySelector('.voice-playback-controls');
        
        assert(micButton.getAttribute('aria-label'), 'Microphone button should have aria-label');
        assert(micButton.getAttribute('aria-pressed'), 'Microphone button should have aria-pressed');
        assert(feedbackArea.getAttribute('aria-live'), 'Feedback area should have aria-live');
        assert(playbackControls.getAttribute('aria-label'), 'Playback controls should have aria-label');
        
        console.log('✓ Accessibility features test passed');
    });

    // Test 10: Settings Persistence
    test('Settings should be saved and loaded correctly', () => {
        const container = document.createElement('div');
        const mockController = new MockVoiceController();
        
        const voiceUI = new VoiceUI(container, mockController);
        
        // Open settings modal
        const settingsButton = container.querySelector('.voice-settings-button');
        settingsButton.click();
        
        // Change a setting
        const autoPlayToggle = document.querySelector('#voice-auto-play');
        autoPlayToggle.checked = true;
        
        const rateSlider = document.querySelector('#speech-rate');
        rateSlider.value = '1.5';
        
        // Save settings
        const saveButton = document.querySelector('.voice-settings-save');
        saveButton.click();
        
        // Check if settings were updated
        assert(mockController.state.settings.autoPlayEnabled, 'Auto-play should be enabled');
        assert(mockController.state.settings.speechRate === 1.5, 'Speech rate should be updated');
        
        console.log('✓ Settings persistence test passed');
    });

    console.log('\n🎉 All Voice UI tests passed!');
}

// Helper function for assertions
function assert(condition, message) {
    if (!condition) {
        throw new Error(`Assertion failed: ${message}`);
    }
}

// Helper function for test execution
function test(description, testFunction) {
    try {
        testFunction();
    } catch (error) {
        console.error(`❌ ${description}: ${error.message}`);
        throw error;
    }
}

// Export for use in test runner
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { runVoiceUITests, MockVoiceController };
} else {
    window.runVoiceUITests = runVoiceUITests;
    window.MockVoiceController = MockVoiceController;
}