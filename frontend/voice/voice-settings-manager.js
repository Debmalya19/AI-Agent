// Voice Settings Manager - Handles user preferences and voice configuration
class VoiceSettingsManager {
    constructor(speechManager) {
        this.speechManager = speechManager;
        this.elements = {};
        this.settings = this.getDefaultSettings();
        this.availableVoices = [];
        
        this.initialize();
    }
    
    getDefaultSettings() {
        return {
            // Speech Recognition Settings
            language: 'en-US',
            
            // Text-to-Speech Settings
            voiceName: 'default',
            speechRate: 1.0,
            speechPitch: 1.0,
            speechVolume: 1.0,
            
            // Interaction Mode Settings
            autoListen: true,
            pushToTalk: false,
            
            // Advanced Settings
            silenceTimeout: 3000,
            maxRecordingTime: 30000
        };
    }
    
    initialize() {
        this.cacheElements();
        this.loadSettings();
        this.loadAvailableVoices();
        this.bindEvents();
        this.updateUI();
        
        console.log('VoiceSettingsManager initialized');
    }
    
    cacheElements() {
        this.elements = {
            // Speech Recognition
            languageSelect: document.getElementById('language-select'),
            
            // Text-to-Speech
            voiceSelect: document.getElementById('voice-select'),
            speechRate: document.getElementById('speech-rate'),
            speechPitch: document.getElementById('speech-pitch'),
            speechVolume: document.getElementById('speech-volume'),
            
            // Interaction Mode
            autoListen: document.getElementById('auto-listen'),
            pushToTalk: document.getElementById('push-to-talk'),
            
            // Actions
            testVoiceBtn: document.getElementById('test-voice-btn'),
            resetSettingsBtn: document.getElementById('reset-settings-btn'),
            saveSettingsBtn: document.getElementById('save-settings-btn'),
            
            // Range value displays
            rateValue: document.querySelector('#speech-rate + .range-container .range-value'),
            pitchValue: document.querySelector('#speech-pitch + .range-container .range-value'),
            volumeValue: document.querySelector('#speech-volume + .range-container .range-value')
        };
    }
    
    loadSettings() {
        try {
            const savedSettings = localStorage.getItem('voice-assistant-settings');
            if (savedSettings) {
                this.settings = { ...this.getDefaultSettings(), ...JSON.parse(savedSettings) };
                console.log('Settings loaded from localStorage:', this.settings);
            }
        } catch (error) {
            console.warn('Failed to load settings from localStorage:', error);
            this.settings = this.getDefaultSettings();
        }
    }
    
    saveSettings() {
        try {
            localStorage.setItem('voice-assistant-settings', JSON.stringify(this.settings));
            console.log('Settings saved to localStorage:', this.settings);
            
            // Apply settings to speech manager
            this.applySettingsToSpeechManager();
            
            // Show success feedback
            this.showSaveSuccess();
            
            return true;
        } catch (error) {
            console.error('Failed to save settings to localStorage:', error);
            this.showSaveError();
            return false;
        }
    }
    
    loadAvailableVoices() {
        if (!('speechSynthesis' in window)) {
            console.warn('Speech synthesis not supported');
            return;
        }
        
        const loadVoices = () => {
            this.availableVoices = speechSynthesis.getVoices();
            this.populateVoiceSelect();
            console.log('Available voices loaded:', this.availableVoices.length);
        };
        
        // Load voices immediately if available
        loadVoices();
        
        // Also listen for voices changed event (some browsers load voices asynchronously)
        if (speechSynthesis.onvoiceschanged !== undefined) {
            speechSynthesis.onvoiceschanged = loadVoices;
        }
    }
    
    populateVoiceSelect() {
        if (!this.elements.voiceSelect || this.availableVoices.length === 0) {
            return;
        }
        
        // Clear existing options
        this.elements.voiceSelect.innerHTML = '';
        
        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = 'default';
        defaultOption.textContent = 'Default Voice';
        this.elements.voiceSelect.appendChild(defaultOption);
        
        // Group voices by language
        const voicesByLang = {};
        this.availableVoices.forEach(voice => {
            const lang = voice.lang.split('-')[0]; // Get language code without region
            if (!voicesByLang[lang]) {
                voicesByLang[lang] = [];
            }
            voicesByLang[lang].push(voice);
        });
        
        // Add voices grouped by language
        Object.keys(voicesByLang).sort().forEach(lang => {
            const optgroup = document.createElement('optgroup');
            optgroup.label = this.getLanguageName(lang);
            
            voicesByLang[lang].forEach(voice => {
                const option = document.createElement('option');
                option.value = voice.name;
                option.textContent = `${voice.name} ${voice.localService ? '(Local)' : '(Remote)'}`;
                optgroup.appendChild(option);
            });
            
            this.elements.voiceSelect.appendChild(optgroup);
        });
    }
    
    getLanguageName(langCode) {
        const languageNames = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ru': 'Russian',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'nl': 'Dutch',
            'sv': 'Swedish',
            'da': 'Danish',
            'no': 'Norwegian',
            'fi': 'Finnish'
        };
        
        return languageNames[langCode] || langCode.toUpperCase();
    }
    
    bindEvents() {
        // Speech Recognition Settings
        if (this.elements.languageSelect) {
            this.elements.languageSelect.addEventListener('change', (e) => {
                this.settings.language = e.target.value;
                console.log('Language changed to:', this.settings.language);
            });
        }
        
        // Text-to-Speech Settings
        if (this.elements.voiceSelect) {
            this.elements.voiceSelect.addEventListener('change', (e) => {
                this.settings.voiceName = e.target.value;
                console.log('Voice changed to:', this.settings.voiceName);
            });
        }
        
        if (this.elements.speechRate) {
            this.elements.speechRate.addEventListener('input', (e) => {
                this.settings.speechRate = parseFloat(e.target.value);
                this.updateRangeValue(this.elements.rateValue, this.settings.speechRate, '');
            });
        }
        
        if (this.elements.speechPitch) {
            this.elements.speechPitch.addEventListener('input', (e) => {
                this.settings.speechPitch = parseFloat(e.target.value);
                this.updateRangeValue(this.elements.pitchValue, this.settings.speechPitch, '');
            });
        }
        
        if (this.elements.speechVolume) {
            this.elements.speechVolume.addEventListener('input', (e) => {
                this.settings.speechVolume = parseFloat(e.target.value);
                this.updateRangeValue(this.elements.volumeValue, this.settings.speechVolume * 100, '%');
            });
        }
        
        // Interaction Mode Settings
        if (this.elements.autoListen) {
            this.elements.autoListen.addEventListener('change', (e) => {
                this.settings.autoListen = e.target.checked;
                console.log('Auto-listen changed to:', this.settings.autoListen);
            });
        }
        
        if (this.elements.pushToTalk) {
            this.elements.pushToTalk.addEventListener('change', (e) => {
                this.settings.pushToTalk = e.target.checked;
                
                // If push-to-talk is enabled, disable auto-listen
                if (this.settings.pushToTalk) {
                    this.settings.autoListen = false;
                    if (this.elements.autoListen) {
                        this.elements.autoListen.checked = false;
                    }
                }
                
                console.log('Push-to-talk changed to:', this.settings.pushToTalk);
            });
        }
        
        // Action Buttons
        if (this.elements.testVoiceBtn) {
            this.elements.testVoiceBtn.addEventListener('click', () => this.testVoiceSettings());
        }
        
        if (this.elements.resetSettingsBtn) {
            this.elements.resetSettingsBtn.addEventListener('click', () => this.resetToDefaults());
        }
        
        if (this.elements.saveSettingsBtn) {
            this.elements.saveSettingsBtn.addEventListener('click', () => this.saveSettings());
        }
        
        // Checkbox label clicks
        document.querySelectorAll('.checkbox-label').forEach(label => {
            label.addEventListener('click', (e) => {
                const checkbox = e.target.parentElement.querySelector('input[type="checkbox"]');
                if (checkbox) {
                    checkbox.click();
                }
            });
        });
    }
    
    updateUI() {
        // Update Speech Recognition Settings
        if (this.elements.languageSelect) {
            this.elements.languageSelect.value = this.settings.language;
        }
        
        // Update Text-to-Speech Settings
        if (this.elements.voiceSelect) {
            this.elements.voiceSelect.value = this.settings.voiceName;
        }
        
        if (this.elements.speechRate) {
            this.elements.speechRate.value = this.settings.speechRate;
            this.updateRangeValue(this.elements.rateValue, this.settings.speechRate, '');
        }
        
        if (this.elements.speechPitch) {
            this.elements.speechPitch.value = this.settings.speechPitch;
            this.updateRangeValue(this.elements.pitchValue, this.settings.speechPitch, '');
        }
        
        if (this.elements.speechVolume) {
            this.elements.speechVolume.value = this.settings.speechVolume;
            this.updateRangeValue(this.elements.volumeValue, this.settings.speechVolume * 100, '%');
        }
        
        // Update Interaction Mode Settings
        if (this.elements.autoListen) {
            this.elements.autoListen.checked = this.settings.autoListen;
        }
        
        if (this.elements.pushToTalk) {
            this.elements.pushToTalk.checked = this.settings.pushToTalk;
        }
    }
    
    updateRangeValue(element, value, suffix) {
        if (element) {
            element.textContent = value.toFixed(1) + suffix;
        }
    }
    
    testVoiceSettings() {
        console.log('Testing voice settings...');
        
        if (!this.speechManager) {
            console.warn('Speech manager not available for testing');
            return;
        }
        
        // Create test message
        const testMessage = `Hello! This is a test of your voice settings. 
                           Speech rate is ${this.settings.speechRate}, 
                           pitch is ${this.settings.speechPitch}, 
                           and volume is ${Math.round(this.settings.speechVolume * 100)} percent.`;
        
        // Apply current settings temporarily for test
        const testOptions = {
            voice: this.getSelectedVoice(),
            rate: this.settings.speechRate,
            pitch: this.settings.speechPitch,
            volume: this.settings.speechVolume
        };
        
        // Speak test message
        this.speechManager.speakText(testMessage, testOptions);
        
        // Update button state during test
        this.elements.testVoiceBtn.disabled = true;
        this.elements.testVoiceBtn.textContent = 'Testing...';
        
        // Re-enable button after test
        setTimeout(() => {
            this.elements.testVoiceBtn.disabled = false;
            this.elements.testVoiceBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12Z" stroke="currentColor" stroke-width="2"/>
                    <path d="M10 8L14 12L10 16V8Z" fill="currentColor"/>
                </svg>
                Test Voice Settings
            `;
        }, 3000);
    }
    
    getSelectedVoice() {
        if (this.settings.voiceName === 'default') {
            return null; // Use browser default
        }
        
        return this.availableVoices.find(voice => voice.name === this.settings.voiceName) || null;
    }
    
    resetToDefaults() {
        console.log('Resetting settings to defaults...');
        
        if (confirm('Are you sure you want to reset all voice settings to their default values?')) {
            this.settings = this.getDefaultSettings();
            this.updateUI();
            
            // Show reset feedback
            this.showResetSuccess();
            
            console.log('Settings reset to defaults');
        }
    }
    
    applySettingsToSpeechManager() {
        if (!this.speechManager) {
            console.warn('Speech manager not available to apply settings');
            return;
        }
        
        // Apply speech recognition settings
        if (this.speechManager.updateLanguage) {
            this.speechManager.updateLanguage(this.settings.language);
        }
        
        // Apply text-to-speech settings
        if (this.speechManager.updateTTSSettings) {
            this.speechManager.updateTTSSettings({
                voice: this.getSelectedVoice(),
                rate: this.settings.speechRate,
                pitch: this.settings.speechPitch,
                volume: this.settings.speechVolume
            });
        }
        
        // Apply interaction mode settings
        if (this.speechManager.updateInteractionSettings) {
            this.speechManager.updateInteractionSettings({
                autoListen: this.settings.autoListen,
                pushToTalk: this.settings.pushToTalk,
                silenceTimeout: this.settings.silenceTimeout
            });
        }
        
        console.log('Settings applied to speech manager');
    }
    
    showSaveSuccess() {
        this.showTemporaryMessage(this.elements.saveSettingsBtn, 'Settings Saved!', 'success');
    }
    
    showSaveError() {
        this.showTemporaryMessage(this.elements.saveSettingsBtn, 'Save Failed', 'error');
    }
    
    showResetSuccess() {
        this.showTemporaryMessage(this.elements.resetSettingsBtn, 'Reset Complete!', 'success');
    }
    
    showTemporaryMessage(button, message, type) {
        if (!button) return;
        
        const originalText = button.innerHTML;
        const originalClass = button.className;
        
        button.innerHTML = message;
        button.className = `${originalClass} ${type}`;
        button.disabled = true;
        
        setTimeout(() => {
            button.innerHTML = originalText;
            button.className = originalClass;
            button.disabled = false;
        }, 2000);
    }
    
    // Public API methods
    
    getSettings() {
        return { ...this.settings };
    }
    
    updateSetting(key, value) {
        if (this.settings.hasOwnProperty(key)) {
            this.settings[key] = value;
            this.updateUI();
            console.log(`Setting ${key} updated to:`, value);
        } else {
            console.warn(`Unknown setting key: ${key}`);
        }
    }
    
    getLanguages() {
        return [
            { code: 'en-US', name: 'English (US)' },
            { code: 'en-GB', name: 'English (UK)' },
            { code: 'en-AU', name: 'English (Australia)' },
            { code: 'en-CA', name: 'English (Canada)' },
            { code: 'es-ES', name: 'Spanish (Spain)' },
            { code: 'es-MX', name: 'Spanish (Mexico)' },
            { code: 'fr-FR', name: 'French (France)' },
            { code: 'fr-CA', name: 'French (Canada)' },
            { code: 'de-DE', name: 'German' },
            { code: 'it-IT', name: 'Italian' },
            { code: 'pt-BR', name: 'Portuguese (Brazil)' },
            { code: 'pt-PT', name: 'Portuguese (Portugal)' },
            { code: 'ja-JP', name: 'Japanese' },
            { code: 'ko-KR', name: 'Korean' },
            { code: 'zh-CN', name: 'Chinese (Simplified)' },
            { code: 'zh-TW', name: 'Chinese (Traditional)' },
            { code: 'ru-RU', name: 'Russian' },
            { code: 'ar-SA', name: 'Arabic' },
            { code: 'hi-IN', name: 'Hindi' },
            { code: 'nl-NL', name: 'Dutch' },
            { code: 'sv-SE', name: 'Swedish' },
            { code: 'da-DK', name: 'Danish' },
            { code: 'no-NO', name: 'Norwegian' },
            { code: 'fi-FI', name: 'Finnish' }
        ];
    }
    
    getAvailableVoices() {
        return this.availableVoices;
    }
    
    isAutoListenEnabled() {
        return this.settings.autoListen && !this.settings.pushToTalk;
    }
    
    isPushToTalkEnabled() {
        return this.settings.pushToTalk;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceSettingsManager;
}