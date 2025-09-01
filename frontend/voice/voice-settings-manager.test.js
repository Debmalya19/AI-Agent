// Voice Settings Manager Tests
const VoiceSettingsManager = require('./voice-settings-manager.js');

describe('VoiceSettingsManager', () => {
    let settingsManager;
    let mockSpeechManager;
    let mockLocalStorage;
    
    beforeEach(() => {
        // Mock localStorage
        mockLocalStorage = {
            data: {},
            getItem: jest.fn((key) => mockLocalStorage.data[key] || null),
            setItem: jest.fn((key, value) => { mockLocalStorage.data[key] = value; }),
            removeItem: jest.fn((key) => { delete mockLocalStorage.data[key]; }),
            clear: jest.fn(() => { mockLocalStorage.data = {}; })
        };
        Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });
        
        // Mock speech synthesis
        global.speechSynthesis = {
            getVoices: jest.fn(() => [
                { name: 'Voice 1', lang: 'en-US', localService: true },
                { name: 'Voice 2', lang: 'en-GB', localService: false },
                { name: 'Voice 3', lang: 'es-ES', localService: true }
            ]),
            onvoiceschanged: null
        };
        
        // Mock speech manager
        mockSpeechManager = {
            updateLanguage: jest.fn(),
            updateTTSSettings: jest.fn(),
            updateInteractionSettings: jest.fn(),
            speakText: jest.fn()
        };
        
        // Mock DOM elements
        document.body.innerHTML = `
            <select id="language-select">
                <option value="en-US">English (US)</option>
                <option value="es-ES">Spanish</option>
                <option value="fr-FR">French</option>
            </select>
            <select id="voice-select"></select>
            <input type="range" id="speech-rate" min="0.5" max="2" step="0.1" value="1">
            <input type="range" id="speech-pitch" min="0.5" max="2" step="0.1" value="1">
            <input type="range" id="speech-volume" min="0" max="1" step="0.1" value="1">
            <input type="checkbox" id="auto-listen" checked>
            <input type="checkbox" id="push-to-talk">
            <button id="test-voice-btn">Test</button>
            <button id="reset-settings-btn">Reset</button>
            <button id="save-settings-btn">Save</button>
            <div class="range-container">
                <span class="range-value">1.0</span>
            </div>
        `;
        
        // Initialize settings manager
        settingsManager = new VoiceSettingsManager(mockSpeechManager);
    });
    
    afterEach(() => {
        jest.clearAllMocks();
    });
    
    describe('Initialization', () => {
        test('should initialize with default settings', () => {
            const settings = settingsManager.getSettings();
            
            expect(settings.language).toBe('en-US');
            expect(settings.speechRate).toBe(1.0);
            expect(settings.speechPitch).toBe(1.0);
            expect(settings.speechVolume).toBe(1.0);
            expect(settings.autoListen).toBe(true);
            expect(settings.pushToTalk).toBe(false);
        });
        
        test('should load settings from localStorage if available', () => {
            const savedSettings = {
                language: 'es-ES',
                speechRate: 1.5,
                autoListen: false
            };
            
            mockLocalStorage.data['voice-assistant-settings'] = JSON.stringify(savedSettings);
            
            const newSettingsManager = new VoiceSettingsManager(mockSpeechManager);
            const settings = newSettingsManager.getSettings();
            
            expect(settings.language).toBe('es-ES');
            expect(settings.speechRate).toBe(1.5);
            expect(settings.autoListen).toBe(false);
            // Should still have defaults for unspecified settings
            expect(settings.speechPitch).toBe(1.0);
        });
        
        test('should handle localStorage errors gracefully', () => {
            mockLocalStorage.getItem.mockImplementation(() => {
                throw new Error('localStorage error');
            });
            
            const newSettingsManager = new VoiceSettingsManager(mockSpeechManager);
            const settings = newSettingsManager.getSettings();
            
            // Should fall back to defaults
            expect(settings.language).toBe('en-US');
            expect(settings.speechRate).toBe(1.0);
        });
    });
    
    describe('Settings Management', () => {
        test('should update individual settings', () => {
            settingsManager.updateSetting('language', 'fr-FR');
            settingsManager.updateSetting('speechRate', 1.5);
            
            const settings = settingsManager.getSettings();
            expect(settings.language).toBe('fr-FR');
            expect(settings.speechRate).toBe(1.5);
        });
        
        test('should ignore invalid setting keys', () => {
            const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
            
            settingsManager.updateSetting('invalidKey', 'value');
            
            expect(consoleSpy).toHaveBeenCalledWith('Unknown setting key: invalidKey');
            consoleSpy.mockRestore();
        });
        
        test('should save settings to localStorage', () => {
            settingsManager.updateSetting('language', 'de-DE');
            settingsManager.updateSetting('speechRate', 0.8);
            
            const success = settingsManager.saveSettings();
            
            expect(success).toBe(true);
            expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
                'voice-assistant-settings',
                expect.stringContaining('"language":"de-DE"')
            );
            expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
                'voice-assistant-settings',
                expect.stringContaining('"speechRate":0.8')
            );
        });
        
        test('should handle localStorage save errors', () => {
            mockLocalStorage.setItem.mockImplementation(() => {
                throw new Error('localStorage save error');
            });
            
            const success = settingsManager.saveSettings();
            
            expect(success).toBe(false);
        });
        
        test('should reset to default settings', () => {
            // Change some settings
            settingsManager.updateSetting('language', 'ja-JP');
            settingsManager.updateSetting('speechRate', 2.0);
            settingsManager.updateSetting('autoListen', false);
            
            // Mock confirm dialog
            global.confirm = jest.fn(() => true);
            
            settingsManager.resetToDefaults();
            
            const settings = settingsManager.getSettings();
            expect(settings.language).toBe('en-US');
            expect(settings.speechRate).toBe(1.0);
            expect(settings.autoListen).toBe(true);
        });
        
        test('should not reset if user cancels confirmation', () => {
            settingsManager.updateSetting('language', 'ja-JP');
            
            // Mock confirm dialog to return false
            global.confirm = jest.fn(() => false);
            
            settingsManager.resetToDefaults();
            
            const settings = settingsManager.getSettings();
            expect(settings.language).toBe('ja-JP'); // Should remain unchanged
        });
    });
    
    describe('Voice Management', () => {
        test('should populate voice select with available voices', () => {
            const voiceSelect = document.getElementById('voice-select');
            
            settingsManager.populateVoiceSelect();
            
            expect(voiceSelect.children.length).toBeGreaterThan(1); // Default + voices
            expect(voiceSelect.children[0].value).toBe('default');
            expect(voiceSelect.children[0].textContent).toBe('Default Voice');
        });
        
        test('should get selected voice object', () => {
            settingsManager.updateSetting('voiceName', 'Voice 1');
            
            const selectedVoice = settingsManager.getSelectedVoice();
            
            expect(selectedVoice).toBeTruthy();
            expect(selectedVoice.name).toBe('Voice 1');
        });
        
        test('should return null for default voice', () => {
            settingsManager.updateSetting('voiceName', 'default');
            
            const selectedVoice = settingsManager.getSelectedVoice();
            
            expect(selectedVoice).toBeNull();
        });
        
        test('should return null for non-existent voice', () => {
            settingsManager.updateSetting('voiceName', 'Non-existent Voice');
            
            const selectedVoice = settingsManager.getSelectedVoice();
            
            expect(selectedVoice).toBeNull();
        });
    });
    
    describe('Interaction Mode', () => {
        test('should return correct auto-listen state', () => {
            settingsManager.updateSetting('autoListen', true);
            settingsManager.updateSetting('pushToTalk', false);
            
            expect(settingsManager.isAutoListenEnabled()).toBe(true);
        });
        
        test('should disable auto-listen when push-to-talk is enabled', () => {
            settingsManager.updateSetting('autoListen', true);
            settingsManager.updateSetting('pushToTalk', true);
            
            expect(settingsManager.isAutoListenEnabled()).toBe(false);
        });
        
        test('should return correct push-to-talk state', () => {
            settingsManager.updateSetting('pushToTalk', true);
            
            expect(settingsManager.isPushToTalkEnabled()).toBe(true);
        });
    });
    
    describe('Speech Manager Integration', () => {
        test('should apply settings to speech manager when saving', () => {
            settingsManager.updateSetting('language', 'fr-FR');
            settingsManager.updateSetting('speechRate', 1.2);
            settingsManager.updateSetting('autoListen', false);
            
            settingsManager.saveSettings();
            
            expect(mockSpeechManager.updateLanguage).toHaveBeenCalledWith('fr-FR');
            expect(mockSpeechManager.updateTTSSettings).toHaveBeenCalledWith(
                expect.objectContaining({
                    rate: 1.2
                })
            );
            expect(mockSpeechManager.updateInteractionSettings).toHaveBeenCalledWith(
                expect.objectContaining({
                    autoListen: false
                })
            );
        });
        
        test('should handle missing speech manager gracefully', () => {
            const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
            
            const settingsManagerWithoutSpeech = new VoiceSettingsManager(null);
            settingsManagerWithoutSpeech.saveSettings();
            
            expect(consoleSpy).toHaveBeenCalledWith('Speech manager not available to apply settings');
            consoleSpy.mockRestore();
        });
    });
    
    describe('Voice Testing', () => {
        test('should test voice settings with speech manager', () => {
            settingsManager.updateSetting('speechRate', 1.5);
            settingsManager.updateSetting('speechPitch', 0.8);
            
            settingsManager.testVoiceSettings();
            
            expect(mockSpeechManager.speakText).toHaveBeenCalledWith(
                expect.stringContaining('test of your voice settings'),
                expect.objectContaining({
                    rate: 1.5,
                    pitch: 0.8
                })
            );
        });
        
        test('should handle missing speech manager during test', () => {
            const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
            
            const settingsManagerWithoutSpeech = new VoiceSettingsManager(null);
            settingsManagerWithoutSpeech.testVoiceSettings();
            
            expect(consoleSpy).toHaveBeenCalledWith('Speech manager not available for testing');
            consoleSpy.mockRestore();
        });
    });
    
    describe('Language Support', () => {
        test('should return list of supported languages', () => {
            const languages = settingsManager.getLanguages();
            
            expect(Array.isArray(languages)).toBe(true);
            expect(languages.length).toBeGreaterThan(0);
            expect(languages[0]).toHaveProperty('code');
            expect(languages[0]).toHaveProperty('name');
        });
        
        test('should include common languages', () => {
            const languages = settingsManager.getLanguages();
            const languageCodes = languages.map(lang => lang.code);
            
            expect(languageCodes).toContain('en-US');
            expect(languageCodes).toContain('es-ES');
            expect(languageCodes).toContain('fr-FR');
            expect(languageCodes).toContain('de-DE');
        });
    });
    
    describe('UI Updates', () => {
        test('should update UI elements when settings change', () => {
            const languageSelect = document.getElementById('language-select');
            const speechRate = document.getElementById('speech-rate');
            const autoListen = document.getElementById('auto-listen');
            
            settingsManager.updateSetting('language', 'es-ES');
            settingsManager.updateSetting('speechRate', 1.3);
            settingsManager.updateSetting('autoListen', false);
            
            settingsManager.updateUI();
            
            expect(languageSelect.value).toBe('es-ES');
            expect(parseFloat(speechRate.value)).toBe(1.3);
            expect(autoListen.checked).toBe(false);
        });
        
        test('should update range value displays', () => {
            const rangeValue = document.querySelector('.range-value');
            
            settingsManager.updateRangeValue(rangeValue, 1.5, 'x');
            
            expect(rangeValue.textContent).toBe('1.5x');
        });
    });
});

// Test helper functions
function createMockElement(tag, attributes = {}) {
    const element = document.createElement(tag);
    Object.keys(attributes).forEach(key => {
        element.setAttribute(key, attributes[key]);
    });
    return element;
}

function createMockEvent(type, properties = {}) {
    const event = new Event(type);
    Object.keys(properties).forEach(key => {
        event[key] = properties[key];
    });
    return event;
}