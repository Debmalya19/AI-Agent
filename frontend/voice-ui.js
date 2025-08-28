/**
 * Voice UI Class
 * Handles all voice-related user interface components and interactions
 */

// Import VoiceErrorUI if available
let VoiceErrorUI;
if (typeof require !== 'undefined') {
    try {
        VoiceErrorUI = require('./voice-error-ui.js');
    } catch (e) {
        // Fallback if module not available
        VoiceErrorUI = class {
            constructor() {}
            show() {}
            showRetryProgress() {}
            hide() {}
        };
    }
} else if (window.VoiceErrorUI) {
    VoiceErrorUI = window.VoiceErrorUI;
} else {
    // Fallback implementation
    VoiceErrorUI = class {
        constructor() {}
        show() {}
        showRetryProgress() {}
        hide() {}
    };
}

class VoiceUI {
    constructor(container, voiceController, options = {}) {
        this.container = container;
        this.voiceController = voiceController;
        this.options = { ...this.getDefaultOptions(), ...options };

        // UI state
        this.isInitialized = false;
        this.isRecording = false;
        this.isPlaying = false;
        this.settingsModalOpen = false;
        this.fallbackMode = false;

        // UI elements
        this.elements = {};

        // Error UI
        this.errorUI = new VoiceErrorUI(container, {
            position: this.options.errorPosition || 'top-right',
            showRecoveryActions: true
        });

        // Initialize UI
        this.initialize();
    }

    /**
     * Get default options
     * @returns {Object} Default options
     */
    getDefaultOptions() {
        return {
            showMicrophoneButton: true,
            showPlaybackControls: true,
            showSettingsButton: true,
            showVisualFeedback: true,
            enableKeyboardShortcuts: true,
            position: 'inline', // 'inline', 'floating', 'sidebar'
            theme: 'auto', // 'light', 'dark', 'auto'
            compactMode: false,
            debugMode: false,
            errorPosition: 'top-right',
            showErrorRecovery: true,
            enableFallbackMode: true
        };
    }

    /**
     * Initialize the voice UI
     */
    initialize() {
        try {
            this.createVoiceControls();
            this.createSettingsModal();
            this.setupEventListeners();
            this.setupKeyboardShortcuts();
            this.updateUIState();

            this.isInitialized = true;
            this.log('Voice UI initialized');

        } catch (error) {
            console.error('Failed to initialize Voice UI:', error);
        }
    }

    /**
     * Create main voice control elements
     */
    createVoiceControls() {
        // Create voice controls container
        this.elements.voiceContainer = this.createElement('div', {
            className: 'voice-controls-container',
            'aria-label': 'Voice controls'
        });

        // Create microphone button
        if (this.options.showMicrophoneButton) {
            this.elements.micButton = this.createMicrophoneButton();
            this.elements.voiceContainer.appendChild(this.elements.micButton);
        }

        // Create playback controls
        if (this.options.showPlaybackControls) {
            this.elements.playbackControls = this.createPlaybackControls();
            this.elements.voiceContainer.appendChild(this.elements.playbackControls);
        }

        // Create auto-play toggle button
        this.elements.autoPlayToggle = this.createAutoPlayToggle();
        this.elements.voiceContainer.appendChild(this.elements.autoPlayToggle);

        // Create settings button
        if (this.options.showSettingsButton) {
            this.elements.settingsButton = this.createSettingsButton();
            this.elements.voiceContainer.appendChild(this.elements.settingsButton);
        }

        // Create visual feedback area
        if (this.options.showVisualFeedback) {
            this.elements.feedbackArea = this.createFeedbackArea();
            this.elements.voiceContainer.appendChild(this.elements.feedbackArea);
        }

        // Add styles
        this.addVoiceControlStyles();

        // Insert into container
        this.container.appendChild(this.elements.voiceContainer);
    }

    /**
     * Create microphone button
     * @returns {HTMLElement} Microphone button element
     */
    createMicrophoneButton() {
        const button = this.createElement('button', {
            className: 'voice-mic-button',
            type: 'button',
            'aria-label': 'Start voice recording',
            'aria-pressed': 'false',
            title: 'Click to start voice recording (Ctrl+Shift+V)'
        });

        // Microphone icon
        button.innerHTML = `
            <svg class="mic-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
            <span class="mic-text">Voice</span>
        `;

        // Recording indicator
        const indicator = this.createElement('div', {
            className: 'recording-indicator',
            'aria-hidden': 'true'
        });
        button.appendChild(indicator);

        // Click handler
        button.addEventListener('click', () => this.toggleRecording());

        return button;
    }

    /**
     * Create playback controls
     * @returns {HTMLElement} Playback controls container
     */
    createPlaybackControls() {
        const container = this.createElement('div', {
            className: 'voice-playback-controls',
            'aria-label': 'Audio playback controls'
        });

        // Play/Pause button
        this.elements.playPauseButton = this.createElement('button', {
            className: 'voice-play-pause-button',
            type: 'button',
            'aria-label': 'Play/Pause audio',
            title: 'Play or pause audio response'
        });

        this.elements.playPauseButton.innerHTML = `
            <svg class="play-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M8 5v14l11-7z"/>
            </svg>
            <svg class="pause-icon" viewBox="0 0 24 24" aria-hidden="true" style="display: none;">
                <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
            </svg>
        `;

        // Stop button
        this.elements.stopButton = this.createElement('button', {
            className: 'voice-stop-button',
            type: 'button',
            'aria-label': 'Stop audio',
            title: 'Stop audio playback'
        });

        this.elements.stopButton.innerHTML = `
            <svg class="stop-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6h12v12H6z"/>
            </svg>
        `;

        // Volume control
        this.elements.volumeControl = this.createElement('input', {
            type: 'range',
            className: 'voice-volume-control',
            min: '0',
            max: '1',
            step: '0.1',
            value: '1',
            'aria-label': 'Audio volume',
            title: 'Adjust audio volume'
        });

        // Event listeners
        this.elements.playPauseButton.addEventListener('click', () => this.togglePlayback());
        this.elements.stopButton.addEventListener('click', () => this.stopPlayback());
        this.elements.volumeControl.addEventListener('input', (e) => this.updateVolume(e.target.value));

        // Add elements to container
        container.appendChild(this.elements.playPauseButton);
        container.appendChild(this.elements.stopButton);
        container.appendChild(this.elements.volumeControl);

        return container;
    }

    /**
     * Create auto-play toggle button
     * @returns {HTMLElement} Auto-play toggle button element
     */
    createAutoPlayToggle() {
        const button = this.createElement('button', {
            className: 'voice-autoplay-toggle',
            type: 'button',
            'aria-label': 'Toggle auto-play',
            'aria-pressed': 'false',
            title: 'Toggle automatic playback of responses'
        });

        button.innerHTML = `
            <svg class="autoplay-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/>
            </svg>
            <span class="autoplay-text">Auto</span>
        `;

        button.addEventListener('click', () => this.toggleAutoPlay());

        return button;
    }

    /**
     * Create settings button
     * @returns {HTMLElement} Settings button element
     */
    createSettingsButton() {
        const button = this.createElement('button', {
            className: 'voice-settings-button',
            type: 'button',
            'aria-label': 'Voice settings',
            title: 'Open voice settings'
        });

        button.innerHTML = `
            <svg class="settings-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.82,11.69,4.82,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.43-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/>
            </svg>
        `;

        button.addEventListener('click', () => this.toggleSettingsModal());

        return button;
    }

    /**
     * Create visual feedback area
     * @returns {HTMLElement} Feedback area element
     */
    createFeedbackArea() {
        const container = this.createElement('div', {
            className: 'voice-feedback-area',
            'aria-live': 'polite',
            'aria-label': 'Voice status'
        });

        // Status text
        this.elements.statusText = this.createElement('div', {
            className: 'voice-status-text'
        });

        // Visual waveform/indicator
        this.elements.visualIndicator = this.createElement('div', {
            className: 'voice-visual-indicator',
            'aria-hidden': 'true'
        });

        // Create waveform bars
        for (let i = 0; i < 5; i++) {
            const bar = this.createElement('div', {
                className: 'waveform-bar'
            });
            this.elements.visualIndicator.appendChild(bar);
        }

        // Transcript display
        this.elements.transcriptDisplay = this.createElement('div', {
            className: 'voice-transcript-display',
            'aria-label': 'Voice transcript'
        });

        container.appendChild(this.elements.statusText);
        container.appendChild(this.elements.visualIndicator);
        container.appendChild(this.elements.transcriptDisplay);

        return container;
    }

    /**
     * Create settings modal
     */
    createSettingsModal() {
        // Modal backdrop
        this.elements.modalBackdrop = this.createElement('div', {
            className: 'voice-settings-backdrop',
            'aria-hidden': 'true'
        });

        // Modal container
        this.elements.settingsModal = this.createElement('div', {
            className: 'voice-settings-modal',
            role: 'dialog',
            'aria-labelledby': 'voice-settings-title',
            'aria-modal': 'true'
        });

        // Modal header
        const header = this.createElement('div', {
            className: 'voice-settings-header'
        });

        const title = this.createElement('h2', {
            id: 'voice-settings-title',
            className: 'voice-settings-title'
        });
        title.textContent = 'Voice Settings';

        const closeButton = this.createElement('button', {
            className: 'voice-settings-close',
            type: 'button',
            'aria-label': 'Close settings'
        });
        closeButton.innerHTML = '×';
        closeButton.addEventListener('click', () => this.closeSettingsModal());

        header.appendChild(title);
        header.appendChild(closeButton);

        // Modal content
        const content = this.createElement('div', {
            className: 'voice-settings-content'
        });

        content.appendChild(this.createSettingsForm());

        // Modal footer
        const footer = this.createElement('div', {
            className: 'voice-settings-footer'
        });

        const saveButton = this.createElement('button', {
            className: 'voice-settings-save',
            type: 'button'
        });
        saveButton.textContent = 'Save Settings';
        saveButton.addEventListener('click', () => this.saveSettings());

        const resetButton = this.createElement('button', {
            className: 'voice-settings-reset',
            type: 'button'
        });
        resetButton.textContent = 'Reset to Defaults';
        resetButton.addEventListener('click', () => this.resetSettings());

        footer.appendChild(resetButton);
        footer.appendChild(saveButton);

        // Assemble modal
        this.elements.settingsModal.appendChild(header);
        this.elements.settingsModal.appendChild(content);
        this.elements.settingsModal.appendChild(footer);

        // Add backdrop click handler
        this.elements.modalBackdrop.addEventListener('click', (e) => {
            if (e.target === this.elements.modalBackdrop) {
                this.closeSettingsModal();
            }
        });

        // Add to document
        document.body.appendChild(this.elements.modalBackdrop);
        this.elements.modalBackdrop.appendChild(this.elements.settingsModal);

        // Add modal styles
        this.addSettingsModalStyles();
    }

    /**
     * Create settings form
     * @returns {HTMLElement} Settings form element
     */
    createSettingsForm() {
        const form = this.createElement('form', {
            className: 'voice-settings-form'
        });

        // Get current settings
        const settings = this.voiceController ? this.voiceController.getState().settings : {};

        // Auto-play setting
        const autoPlayGroup = this.createSettingGroup(
            'Auto-play Responses',
            'Automatically play AI responses as speech'
        );

        this.elements.autoPlayCheckbox = this.createElement('input', {
            type: 'checkbox',
            id: 'voice-auto-play',
            checked: settings.autoPlayEnabled || false
        });

        const autoPlayLabel = this.createElement('label', {
            htmlFor: 'voice-auto-play'
        });
        autoPlayLabel.textContent = 'Enable auto-play';

        autoPlayGroup.appendChild(this.elements.autoPlayCheckbox);
        autoPlayGroup.appendChild(autoPlayLabel);

        // Voice selection
        const voiceGroup = this.createSettingGroup(
            'Voice Selection',
            'Choose the voice for text-to-speech'
        );

        this.elements.voiceSelect = this.createElement('select', {
            id: 'voice-selection',
            'aria-label': 'Select voice'
        });

        this.populateVoiceOptions();
        voiceGroup.appendChild(this.elements.voiceSelect);

        // Add all groups to form
        form.appendChild(autoPlayGroup);
        form.appendChild(voiceGroup);

        return form;
    }

    /**
     * Create a setting group container
     * @param {string} title - Group title
     * @param {string} description - Group description
     * @returns {HTMLElement} Setting group element
     */
    createSettingGroup(title, description) {
        const group = this.createElement('div', {
            className: 'voice-setting-group'
        });

        const titleEl = this.createElement('h3', {
            className: 'setting-title'
        });
        titleEl.textContent = title;

        const descEl = this.createElement('p', {
            className: 'setting-description'
        });
        descEl.textContent = description;

        const controlsEl = this.createElement('div', {
            className: 'setting-controls'
        });

        group.appendChild(titleEl);
        group.appendChild(descEl);
        group.appendChild(controlsEl);

        return controlsEl; // Return controls container for adding inputs
    }

    /**
     * Populate voice selection options
     */
    populateVoiceOptions() {
        if (!this.elements.voiceSelect) return;

        const voices = this.voiceController ? this.voiceController.getAvailableVoices() : [];
        const currentSettings = this.voiceController ? this.voiceController.getState().settings : {};

        // Clear existing options
        this.elements.voiceSelect.innerHTML = '';

        // Add default option
        const defaultOption = this.createElement('option', {
            value: 'default'
        });
        defaultOption.textContent = 'Default Voice';
        this.elements.voiceSelect.appendChild(defaultOption);

        // Add available voices
        voices.forEach(voice => {
            const option = this.createElement('option', {
                value: voice.name
            });
            option.textContent = `${voice.name} (${voice.lang})`;

            if (voice.name === currentSettings.voiceName) {
                option.selected = true;
            }

            this.elements.voiceSelect.appendChild(option);
        });
    }    /**

     * Setup event listeners for voice controller events
     */
    setupEventListeners() {
        if (!this.voiceController) return;

        // Recording events
        this.voiceController.addEventListener('recording_started', () => {
            this.onRecordingStarted();
        });

        this.voiceController.addEventListener('recording_stopped', () => {
            this.onRecordingStopped();
        });

        this.voiceController.addEventListener('speech_detected', () => {
            this.onSpeechDetected();
        });

        this.voiceController.addEventListener('speech_ended', () => {
            this.onSpeechEnded();
        });

        this.voiceController.addEventListener('interim_result', (data) => {
            this.onInterimResult(data.transcript);
        });

        this.voiceController.addEventListener('final_result', (data) => {
            this.onFinalResult(data.transcript, data.confidence);
        });

        // Playback events
        this.voiceController.addEventListener('speech_started', (data) => {
            this.onSpeechStarted(data.text);
        });

        this.voiceController.addEventListener('speech_ended', (data) => {
            this.onSpeechEnded(data.text);
        });

        this.voiceController.addEventListener('speech_paused', () => {
            this.onSpeechPaused();
        });

        this.voiceController.addEventListener('speech_resumed', () => {
            this.onSpeechResumed();
        });

        // Error events
        this.voiceController.addEventListener('error', (data) => {
            this.onVoiceError(data);
        });

        // Enhanced error handling events
        this.voiceController.addEventListener('fallback_activated', (data) => {
            this.onFallbackActivated(data);
        });

        this.voiceController.addEventListener('fallback_required', (data) => {
            this.onFallbackRequired(data);
        });

        this.voiceController.addEventListener('microphone_access_denied', (data) => {
            this.onMicrophoneAccessDenied(data);
        });

        this.voiceController.addEventListener('microphone_error', (data) => {
            this.onMicrophoneError(data);
        });

        this.voiceController.addEventListener('network_retry', (data) => {
            this.onNetworkRetry(data);
        });

        this.voiceController.addEventListener('network_restored', () => {
            this.onNetworkRestored();
        });

        this.voiceController.addEventListener('no_speech_guidance', (data) => {
            this.onNoSpeechGuidance(data);
        });

        this.voiceController.addEventListener('permission_error', (data) => {
            this.onPermissionError(data);
        });

        this.voiceController.addEventListener('retry_with_guidance', (data) => {
            this.onRetryWithGuidance(data);
        });

        this.voiceController.addEventListener('audio_quality_assessment', (data) => {
            this.onAudioQualityAssessment(data);
        });

        this.voiceController.addEventListener('voice_restored', () => {
            this.onVoiceRestored();
        });

        this.voiceController.addEventListener('fallback_message', (data) => {
            this.onFallbackMessage(data);
        });

        // Settings events
        this.voiceController.addEventListener('settings_changed', (data) => {
            this.onSettingsChanged(data.settings);
        });

        // Listen for external settings changes (from VoiceSettings class)
        if (window.voiceSettings) {
            window.voiceSettings.addListener((action, settings) => {
                this.onExternalSettingsChanged(action, settings);
            });
        }
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        if (!this.options.enableKeyboardShortcuts) return;

        this.keydownHandler = (e) => {
            // Ctrl+Shift+V - Toggle recording
            if (e.ctrlKey && e.shiftKey && e.key === 'V') {
                e.preventDefault();
                this.toggleRecording();
            }

            // Ctrl+Shift+P - Toggle playback
            if (e.ctrlKey && e.shiftKey && e.key === 'P') {
                e.preventDefault();
                this.togglePlayback();
            }

            // Ctrl+Shift+S - Stop all voice activity
            if (e.ctrlKey && e.shiftKey && e.key === 'S') {
                e.preventDefault();
                this.stopAllVoiceActivity();
            }

            // Escape - Close settings modal
            if (e.key === 'Escape' && this.settingsModalOpen) {
                e.preventDefault();
                this.closeSettingsModal();
            }
        };

        document.addEventListener('keydown', this.keydownHandler);
    }

    /**
     * Toggle voice recording
     */
    async toggleRecording() {
        if (this.isRecording) {
            this.voiceController.stopRecording();
        } else {
            const success = await this.voiceController.startRecording();
            if (!success) {
                this.showErrorState('Failed to start recording');
            }
        }
    }

    /**
     * Toggle audio playback
     */
    togglePlayback() {
        if (this.isPlaying) {
            this.voiceController.pausePlayback();
        } else {
            this.voiceController.resumePlayback();
        }
    }

    /**
     * Stop audio playback
     */
    stopPlayback() {
        this.voiceController.stopPlayback();
    }

    /**
     * Stop all voice activity
     */
    stopAllVoiceActivity() {
        this.voiceController.stopRecording();
        this.voiceController.stopPlayback();
    }

    /**
     * Toggle auto-play mode
     */
    async toggleAutoPlay() {
        try {
            // Get current settings from voice controller or external settings manager
            let currentSettings;
            if (window.voiceSettings) {
                currentSettings = window.voiceSettings.get();
            } else {
                currentSettings = this.voiceController.getState().settings;
            }

            // Toggle auto-play
            const newAutoPlayState = !currentSettings.autoPlayEnabled;

            // Update settings
            if (window.voiceSettings) {
                await window.voiceSettings.setValue('autoPlayEnabled', newAutoPlayState);
            } else {
                const newSettings = { ...currentSettings, autoPlayEnabled: newAutoPlayState };
                this.voiceController.updateSettings(newSettings);
            }

            // Update UI
            this.updateAutoPlayButton(newAutoPlayState);

            // Show feedback
            const message = newAutoPlayState ? 'Auto-play enabled' : 'Auto-play disabled';
            this.showStatusMessage(message, 'info');

        } catch (error) {
            console.error('Failed to toggle auto-play:', error);
            this.showStatusMessage('Failed to toggle auto-play', 'error');
        }
    }

    /**
     * Update auto-play button state
     * @param {boolean} enabled - Whether auto-play is enabled
     */
    updateAutoPlayButton(enabled) {
        if (!this.elements.autoPlayToggle) return;

        this.elements.autoPlayToggle.setAttribute('aria-pressed', enabled.toString());
        this.elements.autoPlayToggle.classList.toggle('active', enabled);

        const title = enabled ? 'Disable automatic playback' : 'Enable automatic playback';
        this.elements.autoPlayToggle.setAttribute('title', title);
    }

    /**
     * Update volume
     * @param {string} volume - Volume value (0-1)
     */
    updateVolume(volume) {
        if (!this.voiceController) return;
        
        const settings = this.voiceController.getState().settings;
        settings.speechVolume = parseFloat(volume);
        this.voiceController.updateSettings(settings);
    }

    /**
     * Toggle settings modal
     */
    toggleSettingsModal() {
        if (this.settingsModalOpen) {
            this.closeSettingsModal();
        } else {
            this.openSettingsModal();
        }
    }

    /**
     * Open settings modal
     */
    openSettingsModal() {
        this.elements.modalBackdrop.style.display = 'flex';
        this.settingsModalOpen = true;

        // Focus management
        this.elements.settingsModal.focus();

        // Update form with current settings
        this.updateSettingsForm();

        // Announce to screen readers
        this.announceToScreenReader('Voice settings dialog opened');
    }

    /**
     * Close settings modal
     */
    closeSettingsModal() {
        this.elements.modalBackdrop.style.display = 'none';
        this.settingsModalOpen = false;

        // Return focus to settings button
        if (this.elements.settingsButton) {
            this.elements.settingsButton.focus();
        }

        // Announce to screen readers
        this.announceToScreenReader('Voice settings dialog closed');
    }

    /**
     * Update settings form with current values
     */
    updateSettingsForm() {
        if (!this.voiceController) return;
        
        const settings = this.voiceController.getState().settings;

        if (this.elements.autoPlayCheckbox) {
            this.elements.autoPlayCheckbox.checked = settings.autoPlayEnabled;
        }

        // Update voice select
        this.populateVoiceOptions();
        if (this.elements.voiceSelect) {
            this.elements.voiceSelect.value = settings.voiceName || 'default';
        }
    }

    /**
     * Save settings from form
     */
    saveSettings() {
        const newSettings = {
            autoPlayEnabled: this.elements.autoPlayCheckbox?.checked || false,
            voiceName: this.elements.voiceSelect?.value || 'default'
        };

        const success = this.voiceController.updateSettings(newSettings);

        if (success) {
            this.showSuccessMessage('Settings saved successfully');
            this.closeSettingsModal();
        } else {
            this.showErrorMessage('Failed to save settings');
        }
    }

    /**
     * Reset settings to defaults
     */
    async resetSettings() {
        try {
            if (window.voiceSettings) {
                await window.voiceSettings.reset();
                this.showSuccessMessage('Settings reset to defaults');
                this.updateSettingsForm();
            } else {
                // Fallback to voice controller reset
                const defaultSettings = {
                    autoPlayEnabled: false,
                    voiceName: 'default',
                    speechRate: 1.0,
                    speechPitch: 1.0,
                    speechVolume: 1.0,
                    language: 'en-US',
                    microphoneSensitivity: 0.5,
                    noiseCancellation: true,
                    visualFeedbackEnabled: true
                };

                const success = this.voiceController.updateSettings(defaultSettings);
                if (success) {
                    this.showSuccessMessage('Settings reset to defaults');
                    this.updateSettingsForm();
                } else {
                    this.showErrorMessage('Failed to reset settings');
                }
            }
        } catch (error) {
            console.error('Failed to reset settings:', error);
            this.showErrorMessage('Failed to reset settings');
        }
    }

    /**
     * Handle external settings changes (from VoiceSettings class)
     * @param {string} action - The action that triggered the change
     * @param {Object} settings - The updated settings
     */
    onExternalSettingsChanged(action, settings) {
        // Update auto-play button state
        this.updateAutoPlayButton(settings.autoPlayEnabled);

        // Update settings form if modal is open
        if (this.settingsModalOpen) {
            this.updateSettingsForm();
        }
    }

    /**
     * Show status message
     * @param {string} message - Message to show
     * @param {string} type - Message type (info, success, error, warning)
     */
    showStatusMessage(message, type = 'info') {
        if (this.elements.statusText) {
            this.elements.statusText.textContent = message;
            this.elements.feedbackArea.className = `voice-feedback-area visible ${type}`;

            // Auto-hide after 3 seconds
            setTimeout(() => {
                this.clearStatusMessage();
            }, 3000);
        }
    }

    /**
     * Clear status message
     */
    clearStatusMessage() {
        if (this.elements.statusText) {
            this.elements.statusText.textContent = '';
            this.elements.feedbackArea.className = 'voice-feedback-area';
        }
    }

    /**
     * Show success message
     * @param {string} message - Success message
     */
    showSuccessMessage(message) {
        this.showStatusMessage(message, 'success');
    }

    /**
     * Show error message
     * @param {string} message - Error message
     */
    showErrorMessage(message) {
        this.showStatusMessage(message, 'error');
    }

    /**
     * Show error state
     * @param {string} message - Error message to display
     */
    showErrorState(message) {
        this.showStatusMessage(message, 'error');

        // Also show in transcript area
        if (this.elements.transcriptDisplay) {
            this.elements.transcriptDisplay.textContent = `Error: ${message}`;
            this.elements.transcriptDisplay.style.fontStyle = 'italic';
            this.elements.transcriptDisplay.style.color = '#f44336';
        }
    }

    /**
     * Update UI state based on current settings and controller state
     */
    updateUIState() {
        if (!this.voiceController) return;

        const state = this.voiceController.getState();
        const settings = window.voiceSettings ? window.voiceSettings.get() : state.settings;

        // Update auto-play button
        this.updateAutoPlayButton(settings.autoPlayEnabled);

        // Update recording button state
        this.isRecording = state.isRecording;
        if (this.elements.micButton) {
            this.elements.micButton.classList.toggle('recording', this.isRecording);
            this.elements.micButton.setAttribute('aria-pressed', this.isRecording.toString());
        }

        // Update playback controls
        this.isPlaying = state.isPlaying;
        if (this.elements.playPauseButton) {
            const playIcon = this.elements.playPauseButton.querySelector('.play-icon');
            const pauseIcon = this.elements.playPauseButton.querySelector('.pause-icon');

            if (this.isPlaying) {
                playIcon.style.display = 'none';
                pauseIcon.style.display = 'block';
            } else {
                playIcon.style.display = 'block';
                pauseIcon.style.display = 'none';
            }
        }

        // Update volume control
        if (this.elements.volumeControl) {
            this.elements.volumeControl.value = settings.speechVolume;
        }
    }  
  /**
     * Voice controller event handlers
     */
    onRecordingStarted() {
        this.isRecording = true;
        this.updateUIState();
        this.showStatusMessage('Listening...', 'recording');
    }

    onRecordingStopped() {
        this.isRecording = false;
        this.updateUIState();
        this.showStatusMessage('Processing...', 'processing');
    }

    onSpeechDetected() {
        this.showStatusMessage('Speech detected', 'info');
    }

    onSpeechEnded() {
        // Will be handled by final result
    }

    onInterimResult(transcript) {
        if (this.elements.transcriptDisplay) {
            this.elements.transcriptDisplay.textContent = `Listening: ${transcript}`;
            this.elements.transcriptDisplay.style.fontStyle = 'italic';
        }
    }

    onFinalResult(transcript, confidence) {
        if (this.elements.transcriptDisplay) {
            const confidenceText = confidence < 0.8 ? ` (${Math.round(confidence * 100)}%)` : '';
            this.elements.transcriptDisplay.textContent = `Recognized: ${transcript}${confidenceText}`;
            this.elements.transcriptDisplay.style.fontStyle = 'normal';
        }
        this.showStatusMessage('Voice input ready', 'success');
    }

    onSpeechStarted(text) {
        this.isPlaying = true;
        this.updateUIState();
        this.showStatusMessage('Playing response...', 'info');
    }

    onSpeechEnded(text) {
        this.isPlaying = false;
        this.updateUIState();
        this.clearStatusMessage();
    }

    onSpeechPaused() {
        this.isPlaying = false;
        this.updateUIState();
        this.showStatusMessage('Playback paused', 'info');
    }

    onSpeechResumed() {
        this.isPlaying = true;
        this.updateUIState();
        this.showStatusMessage('Playback resumed', 'info');
    }

    onVoiceError(data) {
        const errorMessages = {
            'not_supported': 'Voice features not supported',
            'microphone_access': 'Microphone access denied',
            'network': 'Network error during voice processing',
            'speech_recognition': 'Speech recognition failed',
            'speech_synthesis': 'Text-to-speech failed'
        };

        const message = errorMessages[data.type] || data.message || 'Voice error occurred';
        this.showStatusMessage(message, 'error');
    }

    onSettingsChanged(settings) {
        this.updateUIState();
    }

    /**
     * Enhanced error handling event handlers
     */
    onFallbackActivated(data) {
        this.fallbackMode = true;
        this.showStatusMessage('Voice features unavailable, using text input', 'warning');
        
        // Switch to text input mode
        this.switchToTextInput();
    }

    onFallbackRequired(data) {
        this.showStatusMessage('Voice features not supported, please use text input', 'warning');
        this.switchToTextInput();
    }

    onMicrophoneAccessDenied(data) {
        this.showErrorState('Microphone access denied. Please allow microphone access and try again.');
    }

    onMicrophoneError(data) {
        this.showErrorState(`Microphone error: ${data.message}`);
    }

    onNetworkRetry(data) {
        this.showStatusMessage(`Network issue, retrying... (${data.attempt}/${data.maxAttempts})`, 'warning');
    }

    onNetworkRestored() {
        this.showStatusMessage('Network connection restored', 'success');
    }

    onNoSpeechGuidance(data) {
        this.showStatusMessage('No speech detected. Please speak clearly into your microphone.', 'info');
    }

    onPermissionError(data) {
        this.showErrorState(`Permission error: ${data.message}`);
    }

    onRetryWithGuidance(data) {
        this.showStatusMessage(data.guidance, 'info');
    }

    onAudioQualityAssessment(data) {
        if (data.quality === 'poor') {
            this.showStatusMessage('Audio quality is poor. Please check your microphone.', 'warning');
        }
    }

    onVoiceRestored() {
        this.fallbackMode = false;
        this.showStatusMessage('Voice features restored', 'success');
    }

    onFallbackMessage(data) {
        this.showStatusMessage(data.message, 'info');
    }

    /**
     * Switch to text input mode
     */
    switchToTextInput() {
        // Emit event for parent component to handle
        this.container.dispatchEvent(new CustomEvent('voice-fallback-requested', {
            detail: {
                reason: 'Voice features unavailable',
                fallbackMode: true
            }
        }));
    }

    /**
     * Utility methods
     */
    createElement(tag, attributes = {}) {
        const element = document.createElement(tag);

        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'htmlFor') {
                element.htmlFor = value;
            } else {
                element.setAttribute(key, value);
            }
        });

        return element;
    }

    announceToScreenReader(message) {
        // Create temporary element for screen reader announcement
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.style.position = 'absolute';
        announcement.style.left = '-10000px';
        announcement.style.width = '1px';
        announcement.style.height = '1px';
        announcement.style.overflow = 'hidden';

        document.body.appendChild(announcement);
        announcement.textContent = message;

        // Remove after announcement
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
    }

    log(message) {
        if (this.options.debugMode) {
            console.log(`[VoiceUI] ${message}`);
        }
    } 
   /**
     * Add voice control styles
     */
    addVoiceControlStyles() {
        const voiceStyles = `
            .voice-controls-container {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 10px;
                background: rgba(0, 0, 0, 0.05);
                border-radius: 8px;
                margin: 10px 0;
            }

            .voice-mic-button {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 50%;
                width: 48px;
                height: 48px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s ease;
                position: relative;
                color: rgba(255, 255, 255, 0.9);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }

            .voice-mic-button:hover {
                background: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.3);
                transform: scale(1.05);
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
            }

            .voice-mic-button:disabled {
                background: rgba(128, 128, 128, 0.1);
                border-color: rgba(128, 128, 128, 0.2);
                color: rgba(128, 128, 128, 0.5);
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }

            .voice-mic-button.recording {
                background: rgba(244, 67, 54, 0.2);
                border-color: rgba(244, 67, 54, 0.4);
                color: rgba(244, 67, 54, 0.9);
                animation: pulse 1.5s infinite;
                box-shadow: 0 0 20px rgba(244, 67, 54, 0.3);
            }

            .voice-mic-button svg {
                width: 20px;
                height: 20px;
                fill: currentColor;
            }

            .voice-mic-button .mic-text {
                display: none;
                font-size: 10px;
                position: absolute;
                bottom: -15px;
                left: 50%;
                transform: translateX(-50%);
                font-weight: bold;
            }

            .recording-indicator {
                position: absolute;
                top: -2px;
                right: -2px;
                width: 12px;
                height: 12px;
                background: rgba(244, 67, 54, 0.9);
                border: 2px solid rgba(255, 255, 255, 0.8);
                border-radius: 50%;
                opacity: 0;
                transition: opacity 0.3s ease;
                box-shadow: 0 0 8px rgba(244, 67, 54, 0.5);
            }

            .voice-mic-button.recording .recording-indicator {
                opacity: 1;
                animation: blink 1s infinite;
            }

            .voice-playback-controls {
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .voice-play-pause-button,
            .voice-stop-button {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s ease;
            }

            .voice-play-pause-button:hover,
            .voice-stop-button:hover {
                background: rgba(255, 255, 255, 0.2);
            }

            .voice-play-pause-button svg,
            .voice-stop-button svg {
                width: 16px;
                height: 16px;
                fill: #333;
            }

            .voice-volume-control {
                width: 60px;
            }

            .voice-autoplay-toggle {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s ease;
                position: relative;
            }

            .voice-autoplay-toggle:hover {
                background: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.5);
            }

            .voice-autoplay-toggle.active {
                background: #4CAF50;
                border-color: #66BB6A;
            }

            .voice-autoplay-toggle svg {
                width: 14px;
                height: 14px;
                fill: #333;
            }

            .voice-autoplay-toggle.active svg {
                fill: white;
            }

            .voice-settings-button {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s ease;
            }

            .voice-settings-button:hover {
                background: rgba(255, 255, 255, 0.2);
            }

            .voice-settings-button svg {
                width: 16px;
                height: 16px;
                fill: #333;
            }

            .voice-feedback-area {
                flex: 1;
                padding: 10px;
                min-height: 40px;
                display: flex;
                flex-direction: column;
                gap: 5px;
            }

            .voice-feedback-area.visible {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }

            .voice-feedback-area.success {
                background: rgba(76, 175, 80, 0.1);
                border-left: 3px solid #4CAF50;
            }

            .voice-feedback-area.error {
                background: rgba(244, 67, 54, 0.1);
                border-left: 3px solid #f44336;
            }

            .voice-feedback-area.warning {
                background: rgba(255, 193, 7, 0.1);
                border-left: 3px solid #FFC107;
            }

            .voice-status-text {
                font-size: 14px;
                color: #333;
                font-weight: 500;
            }

            .voice-visual-indicator {
                display: flex;
                align-items: center;
                gap: 2px;
                height: 20px;
            }

            .waveform-bar {
                width: 3px;
                height: 20%;
                background: #2575fc;
                border-radius: 1px;
                transition: height 0.2s ease;
            }

            .voice-visual-indicator.recording .waveform-bar,
            .voice-visual-indicator.speaking .waveform-bar {
                animation: waveform 0.5s infinite alternate;
            }

            .voice-transcript-display {
                font-size: 12px;
                color: #666;
                font-style: italic;
                min-height: 16px;
            }

            @keyframes pulse {
                0% { 
                    box-shadow: 0 0 20px rgba(244, 67, 54, 0.3), 0 0 0 0 rgba(244, 67, 54, 0.7);
                }
                70% { 
                    box-shadow: 0 0 25px rgba(244, 67, 54, 0.4), 0 0 0 10px rgba(244, 67, 54, 0);
                }
                100% { 
                    box-shadow: 0 0 20px rgba(244, 67, 54, 0.3), 0 0 0 0 rgba(244, 67, 54, 0);
                }
            }

            @keyframes blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0; }
            }

            @keyframes waveform {
                0% { height: 20%; }
                100% { height: 80%; }
            }

            @media (max-width: 768px) {
                .voice-controls-container {
                    flex-wrap: wrap;
                    gap: 8px;
                }
                
                .voice-mic-button .mic-text,
                .voice-autoplay-toggle .autoplay-text {
                    display: block;
                }
            }
        `;

        // Add styles to document
        if (!document.getElementById('voice-ui-styles')) {
            const styleSheet = document.createElement('style');
            styleSheet.id = 'voice-ui-styles';
            styleSheet.textContent = voiceStyles;
            document.head.appendChild(styleSheet);
        }
    }

    /**
     * Add settings modal styles
     */
    addSettingsModalStyles() {
        const modalStyles = `
            .voice-settings-backdrop {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: none;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            }

            .voice-settings-modal {
                background: white;
                border-radius: 8px;
                max-width: 500px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            }

            .voice-settings-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px;
                border-bottom: 1px solid #eee;
            }

            .voice-settings-title {
                margin: 0;
                font-size: 1.5rem;
                color: #333;
            }

            .voice-settings-close {
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: #666;
                padding: 0;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .voice-settings-content {
                padding: 20px;
            }

            .voice-setting-group {
                margin-bottom: 20px;
            }

            .setting-title {
                margin: 0 0 5px 0;
                font-size: 1.1rem;
                color: #333;
            }

            .setting-description {
                margin: 0 0 10px 0;
                font-size: 0.9rem;
                color: #666;
            }

            .setting-controls {
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .setting-controls input[type="range"] {
                flex: 1;
            }

            .setting-controls select {
                flex: 1;
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }

            .slider-value {
                min-width: 40px;
                text-align: right;
                font-weight: bold;
                color: #333;
            }

            .voice-settings-footer {
                display: flex;
                justify-content: space-between;
                padding: 20px;
                border-top: 1px solid #eee;
            }

            .voice-settings-save,
            .voice-settings-reset {
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-weight: bold;
            }

            .voice-settings-save {
                background: #2575fc;
                color: white;
            }

            .voice-settings-save:hover {
                background: #1e5bb8;
            }

            .voice-settings-reset {
                background: #f5f5f5;
                color: #333;
            }

            .voice-settings-reset:hover {
                background: #e0e0e0;
            }
        `;

        // Add styles to document
        if (!document.getElementById('voice-settings-modal-styles')) {
            const styleSheet = document.createElement('style');
            styleSheet.id = 'voice-settings-modal-styles';
            styleSheet.textContent = modalStyles;
            document.head.appendChild(styleSheet);
        }
    }

    /**
     * Destroy the voice UI and clean up resources
     */
    destroy() {
        // Remove event listeners
        if (this.keydownHandler) {
            document.removeEventListener('keydown', this.keydownHandler);
        }

        // Remove UI elements
        if (this.elements.voiceContainer && this.elements.voiceContainer.parentNode) {
            this.elements.voiceContainer.parentNode.removeChild(this.elements.voiceContainer);
        }

        if (this.elements.modalBackdrop && this.elements.modalBackdrop.parentNode) {
            this.elements.modalBackdrop.parentNode.removeChild(this.elements.modalBackdrop);
        }

        // Clear references
        this.elements = {};
        this.voiceController = null;
        this.container = null;

        this.log('Voice UI destroyed');
    }

    /**
     * Get current UI state
     * @returns {Object} Current UI state
     */
    getState() {
        return {
            isInitialized: this.isInitialized,
            isRecording: this.isRecording,
            isPlaying: this.isPlaying,
            settingsModalOpen: this.settingsModalOpen,
            fallbackMode: this.fallbackMode
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceUI;
} else {
    window.VoiceUI = VoiceUI;
}