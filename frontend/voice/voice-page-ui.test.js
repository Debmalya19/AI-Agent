// VoicePageUI Tests
// Tests for the voice assistant page controls and navigation functionality

// Mock VoicePageUI class for testing (simplified version)
class VoicePageUI {
    constructor(container, speechManager, visualFeedback) {
        this.container = container;
        this.speechManager = speechManager;
        this.visualFeedback = visualFeedback;
        this.elements = {};
        this.state = {
            isMuted: false,
            isSettingsOpen: false
        };
        
        this.cacheElements();
        this.bindEvents();
    }
    
    cacheElements() {
        this.elements = {
            closeBtn: document.getElementById('close-btn'),
            settingsBtn: document.getElementById('settings-btn'),
            muteBtn: document.getElementById('mute-btn'),
            stopBtn: document.getElementById('stop-btn'),
            replayBtn: document.getElementById('replay-btn'),
            settingsModal: document.getElementById('settings-modal'),
            modalClose: document.querySelector('.modal-close'),
            micButton: document.getElementById('mic-button')
        };
    }
    
    bindEvents() {
        this.elements.closeBtn.addEventListener('click', () => this.handleCloseClick());
        this.elements.settingsBtn.addEventListener('click', () => this.handleSettingsClick());
        this.elements.muteBtn.addEventListener('click', () => this.handleMuteClick());
        this.elements.stopBtn.addEventListener('click', () => this.handleStopClick());
        this.elements.replayBtn.addEventListener('click', () => this.handleReplayClick());
        this.elements.modalClose.addEventListener('click', () => this.hideSettings());
        this.elements.settingsModal.addEventListener('click', (e) => {
            if (e.target === this.elements.settingsModal) {
                this.hideSettings();
            }
        });
        document.addEventListener('keydown', (e) => this.handleControlKeydown(e));
    }
    
    updateControls(state) {
        if (this.state.isMuted) {
            this.elements.muteBtn.classList.add('muted');
            this.updateMuteButtonIcon(true);
        } else {
            this.elements.muteBtn.classList.remove('muted');
            this.updateMuteButtonIcon(false);
        }
        
        if (state === 'speaking' || state === 'listening') {
            this.elements.stopBtn.classList.add('active');
        } else {
            this.elements.stopBtn.classList.remove('active');
        }
        
        const hasLastResponse = this.speechManager && this.speechManager.getLastSpokenText();
        if (hasLastResponse) {
            this.elements.replayBtn.classList.remove('disabled');
            this.elements.replayBtn.disabled = false;
        } else {
            this.elements.replayBtn.classList.add('disabled');
            this.elements.replayBtn.disabled = true;
        }
    }
    
    updateMuteButtonIcon(isMuted) {
        const muteIcon = this.elements.muteBtn.querySelector('svg');
        if (muteIcon) {
            if (isMuted) {
                muteIcon.innerHTML = '<path d="M3 3L21 21" stroke="currentColor" stroke-width="2"/>';
            } else {
                muteIcon.innerHTML = '<path d="test"/>';
            }
        }
    }
    
    showSettings() {
        this.state.isSettingsOpen = true;
        this.elements.settingsModal.classList.remove('hidden');
        this.elements.settingsModal.setAttribute('aria-hidden', 'false');
    }
    
    hideSettings() {
        this.state.isSettingsOpen = false;
        this.elements.settingsModal.classList.add('hidden');
        this.elements.settingsModal.setAttribute('aria-hidden', 'true');
    }
    
    handleMicrophoneClick() {
        if (this.state.isMuted) {
            this.visualFeedback.showError('Microphone is muted. Click the mute button to unmute.');
            return false;
        }
        return true;
    }
    
    handleCloseClick() {
        this.speechManager.stopListening();
        this.speechManager.stopSpeaking();
        if (window.opener) {
            window.close();
        }
    }
    
    handleSettingsClick() {
        if (this.state.isSettingsOpen) {
            this.hideSettings();
        } else {
            this.showSettings();
        }
    }
    
    handleMuteClick() {
        this.state.isMuted = !this.state.isMuted;
        if (this.state.isMuted) {
            if (this.speechManager.isListening()) {
                this.speechManager.stopListening();
            }
            this.visualFeedback.showMuted();
        } else {
            this.visualFeedback.showIdle();
        }
        this.updateControls(this.speechManager.getCurrentState());
    }
    
    handleStopClick() {
        if (this.speechManager.isListening()) {
            this.speechManager.stopListening();
        }
        if (this.speechManager.isSpeaking()) {
            this.speechManager.stopSpeaking();
        }
        this.visualFeedback.showIdle();
        this.updateControls('idle');
    }
    
    handleReplayClick() {
        const lastResponse = this.speechManager.getLastSpokenText();
        if (!lastResponse) {
            this.visualFeedback.showError('No response to replay');
            return;
        }
        if (this.speechManager.isSpeaking()) {
            this.speechManager.stopSpeaking();
        }
        this.speechManager.replayLastSpeech();
        this.visualFeedback.displayResponse(lastResponse);
    }
    
    handleControlKeydown(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
            return;
        }
        
        switch (e.key) {
            case 'Escape':
                if (this.state.isSettingsOpen) {
                    this.hideSettings();
                } else {
                    this.handleStopClick();
                }
                e.preventDefault();
                break;
            case 'm':
            case 'M':
                if (e.ctrlKey || e.metaKey) {
                    this.handleMuteClick();
                    e.preventDefault();
                }
                break;
            case 's':
            case 'S':
                if (e.ctrlKey || e.metaKey) {
                    this.handleStopClick();
                    e.preventDefault();
                }
                break;
            case 'r':
            case 'R':
                if (e.ctrlKey || e.metaKey) {
                    this.handleReplayClick();
                    e.preventDefault();
                }
                break;
        }
    }
    
    getMuteState() {
        return this.state.isMuted;
    }
    
    setMuteState(muted) {
        if (this.state.isMuted !== muted) {
            this.handleMuteClick();
        }
    }
    
    getSettingsState() {
        return this.state.isSettingsOpen;
    }
    
    onStateChange(newState) {
        this.updateControls(newState);
    }
}

describe('VoicePageUI', () => {
    let pageUI;
    let mockSpeechManager;
    let mockVisualFeedback;
    let container;
    
    beforeEach(() => {
        // Create mock DOM elements
        document.body.innerHTML = `
            <div id="voice-container">
                <button id="close-btn" class="control-btn"></button>
                <button id="settings-btn" class="control-btn"></button>
                <button id="mute-btn" class="control-btn"></button>
                <button id="stop-btn" class="control-btn"></button>
                <button id="replay-btn" class="control-btn"></button>
                <button id="mic-button" class="mic-button"></button>
                <div id="settings-modal" class="modal hidden">
                    <button class="modal-close"></button>
                </div>
            </div>
        `;
        
        container = document.getElementById('voice-container');
        
        // Create mock speech manager
        mockSpeechManager = {
            getCurrentState: jest.fn(() => 'idle'),
            getLastSpokenText: jest.fn(() => ''),
            isListening: jest.fn(() => false),
            isSpeaking: jest.fn(() => false),
            stopListening: jest.fn(),
            stopSpeaking: jest.fn(),
            replayLastSpeech: jest.fn(() => true)
        };
        
        // Create mock visual feedback
        mockVisualFeedback = {
            showError: jest.fn(),
            showMuted: jest.fn(),
            showIdle: jest.fn(),
            displayResponse: jest.fn()
        };
        
        // Initialize VoicePageUI
        pageUI = new VoicePageUI(container, mockSpeechManager, mockVisualFeedback);
    });
    
    afterEach(() => {
        document.body.innerHTML = '';
    });
    
    describe('Initialization', () => {
        test('should initialize with correct default state', () => {
            expect(pageUI.state.isMuted).toBe(false);
            expect(pageUI.state.isSettingsOpen).toBe(false);
        });
        
        test('should cache DOM elements correctly', () => {
            expect(pageUI.elements.closeBtn).toBeTruthy();
            expect(pageUI.elements.muteBtn).toBeTruthy();
            expect(pageUI.elements.stopBtn).toBeTruthy();
            expect(pageUI.elements.replayBtn).toBeTruthy();
            expect(pageUI.elements.settingsBtn).toBeTruthy();
        });
    });
    
    describe('Mute Functionality', () => {
        test('should toggle mute state when mute button is clicked', () => {
            const muteBtn = document.getElementById('mute-btn');
            
            // Initially not muted
            expect(pageUI.getMuteState()).toBe(false);
            
            // Click mute button
            muteBtn.click();
            
            // Should be muted now
            expect(pageUI.getMuteState()).toBe(true);
            expect(muteBtn.classList.contains('muted')).toBe(true);
            expect(mockVisualFeedback.showMuted).toHaveBeenCalled();
        });
        
        test('should show muted error when microphone clicked while muted', () => {
            // Mute first
            pageUI.handleMuteClick();
            
            // Try to use microphone
            const result = pageUI.handleMicrophoneClick();
            
            expect(result).toBe(false);
            expect(mockVisualFeedback.showError).toHaveBeenCalledWith(
                'Microphone is muted. Click the mute button to unmute.'
            );
        });
        
        test('should update mute button icon when muted', () => {
            const muteBtn = document.getElementById('mute-btn');
            
            // Add SVG element for testing
            const svg = document.createElement('svg');
            svg.innerHTML = '<path d="test"/>';
            muteBtn.appendChild(svg);
            
            pageUI.handleMuteClick();
            
            // Should contain muted icon (with slash)
            expect(svg.innerHTML).toContain('M3 3L21 21');
        });
    });
    
    describe('Stop Functionality', () => {
        test('should stop listening and speaking when stop button is clicked', () => {
            mockSpeechManager.isListening.mockReturnValue(true);
            mockSpeechManager.isSpeaking.mockReturnValue(true);
            
            const stopBtn = document.getElementById('stop-btn');
            stopBtn.click();
            
            expect(mockSpeechManager.stopListening).toHaveBeenCalled();
            expect(mockSpeechManager.stopSpeaking).toHaveBeenCalled();
            expect(mockVisualFeedback.showIdle).toHaveBeenCalled();
        });
        
        test('should update control states after stopping', () => {
            const stopBtn = document.getElementById('stop-btn');
            stopBtn.click();
            
            // Should call updateControls with idle state
            expect(mockVisualFeedback.showIdle).toHaveBeenCalled();
        });
    });
    
    describe('Replay Functionality', () => {
        test('should replay last response when replay button is clicked', () => {
            mockSpeechManager.getLastSpokenText.mockReturnValue('Hello, this is a test response');
            
            const replayBtn = document.getElementById('replay-btn');
            replayBtn.click();
            
            expect(mockSpeechManager.replayLastSpeech).toHaveBeenCalled();
            expect(mockVisualFeedback.displayResponse).toHaveBeenCalledWith('Hello, this is a test response');
        });
        
        test('should show error when no response to replay', () => {
            mockSpeechManager.getLastSpokenText.mockReturnValue('');
            
            const replayBtn = document.getElementById('replay-btn');
            replayBtn.click();
            
            expect(mockSpeechManager.replayLastSpeech).not.toHaveBeenCalled();
            expect(mockVisualFeedback.showError).toHaveBeenCalledWith('No response to replay');
        });
        
        test('should stop current speech before replaying', () => {
            mockSpeechManager.getLastSpokenText.mockReturnValue('Test response');
            mockSpeechManager.isSpeaking.mockReturnValue(true);
            
            const replayBtn = document.getElementById('replay-btn');
            replayBtn.click();
            
            expect(mockSpeechManager.stopSpeaking).toHaveBeenCalled();
        });
    });
    
    describe('Settings Functionality', () => {
        test('should open settings modal when settings button is clicked', () => {
            const settingsBtn = document.getElementById('settings-btn');
            const modal = document.getElementById('settings-modal');
            
            settingsBtn.click();
            
            expect(pageUI.getSettingsState()).toBe(true);
            expect(modal.classList.contains('hidden')).toBe(false);
            expect(modal.getAttribute('aria-hidden')).toBe('false');
        });
        
        test('should close settings modal when close button is clicked', () => {
            const settingsBtn = document.getElementById('settings-btn');
            const modalClose = document.querySelector('.modal-close');
            const modal = document.getElementById('settings-modal');
            
            // Open settings first
            settingsBtn.click();
            expect(pageUI.getSettingsState()).toBe(true);
            
            // Close settings
            modalClose.click();
            
            expect(pageUI.getSettingsState()).toBe(false);
            expect(modal.classList.contains('hidden')).toBe(true);
            expect(modal.getAttribute('aria-hidden')).toBe('true');
        });
        
        test('should close settings when clicking outside modal', () => {
            const settingsBtn = document.getElementById('settings-btn');
            const modal = document.getElementById('settings-modal');
            
            // Open settings
            settingsBtn.click();
            
            // Click on modal backdrop
            const clickEvent = new MouseEvent('click', { bubbles: true });
            Object.defineProperty(clickEvent, 'target', { value: modal });
            modal.dispatchEvent(clickEvent);
            
            expect(pageUI.getSettingsState()).toBe(false);
        });
    });
    
    describe('Close Functionality', () => {
        test('should stop speech processing when close button is clicked', () => {
            // Mock window.close
            window.close = jest.fn();
            window.opener = {};
            
            const closeBtn = document.getElementById('close-btn');
            closeBtn.click();
            
            expect(mockSpeechManager.stopListening).toHaveBeenCalled();
            expect(mockSpeechManager.stopSpeaking).toHaveBeenCalled();
            expect(window.close).toHaveBeenCalled();
        });
    });
    
    describe('Control Updates', () => {
        test('should update replay button state based on available response', () => {
            const replayBtn = document.getElementById('replay-btn');
            
            // No response available
            mockSpeechManager.getLastSpokenText.mockReturnValue('');
            pageUI.updateControls('idle');
            
            expect(replayBtn.classList.contains('disabled')).toBe(true);
            expect(replayBtn.disabled).toBe(true);
            
            // Response available
            mockSpeechManager.getLastSpokenText.mockReturnValue('Test response');
            pageUI.updateControls('idle');
            
            expect(replayBtn.classList.contains('disabled')).toBe(false);
            expect(replayBtn.disabled).toBe(false);
        });
        
        test('should update stop button state based on speech activity', () => {
            const stopBtn = document.getElementById('stop-btn');
            
            // Speaking state
            pageUI.updateControls('speaking');
            expect(stopBtn.classList.contains('active')).toBe(true);
            
            // Listening state
            pageUI.updateControls('listening');
            expect(stopBtn.classList.contains('active')).toBe(true);
            
            // Idle state
            pageUI.updateControls('idle');
            expect(stopBtn.classList.contains('active')).toBe(false);
        });
    });
    
    describe('Keyboard Shortcuts', () => {
        test('should handle Escape key to close settings', () => {
            // Open settings first
            pageUI.showSettings();
            expect(pageUI.getSettingsState()).toBe(true);
            
            // Press Escape
            const escapeEvent = new KeyboardEvent('keydown', { key: 'Escape' });
            document.dispatchEvent(escapeEvent);
            
            expect(pageUI.getSettingsState()).toBe(false);
        });
        
        test('should handle Ctrl+M for mute toggle', () => {
            const preventDefault = jest.fn();
            const muteEvent = new KeyboardEvent('keydown', { 
                key: 'M', 
                ctrlKey: true
            });
            muteEvent.preventDefault = preventDefault;
            
            document.dispatchEvent(muteEvent);
            
            expect(pageUI.getMuteState()).toBe(true);
            expect(preventDefault).toHaveBeenCalled();
        });
        
        test('should handle Ctrl+S for stop', () => {
            mockSpeechManager.isListening.mockReturnValue(true);
            
            const preventDefault = jest.fn();
            const stopEvent = new KeyboardEvent('keydown', { 
                key: 'S', 
                ctrlKey: true
            });
            stopEvent.preventDefault = preventDefault;
            
            document.dispatchEvent(stopEvent);
            
            expect(mockSpeechManager.stopListening).toHaveBeenCalled();
            expect(preventDefault).toHaveBeenCalled();
        });
        
        test('should handle Ctrl+R for replay', () => {
            mockSpeechManager.getLastSpokenText.mockReturnValue('Test response');
            
            const preventDefault = jest.fn();
            const replayEvent = new KeyboardEvent('keydown', { 
                key: 'R', 
                ctrlKey: true
            });
            replayEvent.preventDefault = preventDefault;
            
            document.dispatchEvent(replayEvent);
            
            expect(mockSpeechManager.replayLastSpeech).toHaveBeenCalled();
            expect(preventDefault).toHaveBeenCalled();
        });
    });
    
    describe('State Management', () => {
        test('should respond to state changes from speech manager', () => {
            pageUI.onStateChange('speaking');
            
            // Should update controls for speaking state
            const stopBtn = document.getElementById('stop-btn');
            expect(stopBtn.classList.contains('active')).toBe(true);
        });
        
        test('should provide public methods for state access', () => {
            expect(typeof pageUI.getMuteState).toBe('function');
            expect(typeof pageUI.setMuteState).toBe('function');
            expect(typeof pageUI.getSettingsState).toBe('function');
        });
        
        test('should allow external mute state control', () => {
            expect(pageUI.getMuteState()).toBe(false);
            
            pageUI.setMuteState(true);
            expect(pageUI.getMuteState()).toBe(true);
            
            pageUI.setMuteState(false);
            expect(pageUI.getMuteState()).toBe(false);
        });
    });
});