/**
 * Voice Settings Class
 * Manages client-side voice settings with persistence and validation
 */

class VoiceSettings {
    constructor(storageKey = 'voice_settings') {
        this.storageKey = storageKey;
        this.settings = this.loadSync(); // Load synchronously first for immediate use
        this.listeners = new Set();
        this.initialized = false;
        this.initializationPromise = null;
    }

    /**
     * Get default voice settings
     * @returns {Object} Default settings object
     */
    getDefaults() {
        return {
            autoPlayEnabled: false,
            voiceName: 'default',
            speechRate: 1.0,
            speechPitch: 1.0,
            speechVolume: 1.0,
            language: 'en-US',
            microphoneSensitivity: 0.5,
            noiseCancellation: true,
            continuousRecognition: false,
            interimResults: true,
            maxAlternatives: 1,
            voiceInputEnabled: true,
            voiceOutputEnabled: true,
            visualFeedbackEnabled: true,
            keyboardShortcutsEnabled: true,
            autoStopTimeout: 3000, // ms of silence before stopping
            maxRecordingTime: 60000, // max recording time in ms
            lastUpdated: Date.now()
        };
    }

    /**
     * Load settings from backend API with fallback to localStorage and defaults
     * @returns {Object} Loaded settings
     */
    async load() {
        try {
            // First try to load from backend API
            const backendSettings = await this.loadFromBackend();
            if (backendSettings) {
                // Merge with defaults and save to localStorage for offline access
                const mergedSettings = { ...this.getDefaults(), ...backendSettings };
                this.saveToLocalStorage(mergedSettings);
                return mergedSettings;
            }
        } catch (error) {
            console.warn('Failed to load voice settings from backend, trying localStorage:', error);
        }

        try {
            // Fallback to localStorage
            const stored = localStorage.getItem(this.storageKey);
            if (stored) {
                const parsed = JSON.parse(stored);
                // Merge with defaults to ensure all properties exist
                return { ...this.getDefaults(), ...parsed };
            }
        } catch (error) {
            console.warn('Failed to load voice settings from localStorage:', error);
        }
        
        return this.getDefaults();
    }

    /**
     * Load settings from localStorage only (synchronous)
     * @returns {Object} Loaded settings
     */
    loadSync() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            if (stored) {
                const parsed = JSON.parse(stored);
                // Merge with defaults to ensure all properties exist
                return { ...this.getDefaults(), ...parsed };
            }
        } catch (error) {
            console.warn('Failed to load voice settings from localStorage:', error);
        }
        
        return this.getDefaults();
    }

    /**
     * Save settings to backend API and localStorage
     * @param {Object} settings - Settings to save (optional, uses current settings if not provided)
     * @returns {boolean} True if save was successful
     */
    async save(settings = null) {
        const toSave = settings || this.settings;
        toSave.lastUpdated = Date.now();
        
        if (settings) {
            this.settings = { ...this.settings, ...settings };
        }

        let backendSuccess = false;
        let localStorageSuccess = false;

        // Try to save to backend first
        try {
            backendSuccess = await this.saveToBackend(this.settings);
        } catch (error) {
            console.warn('Failed to save voice settings to backend:', error);
        }

        // Always save to localStorage as backup
        try {
            localStorageSuccess = this.saveToLocalStorage(this.settings);
        } catch (error) {
            console.error('Failed to save voice settings to localStorage:', error);
        }

        // Notify listeners if at least one save method succeeded
        if (backendSuccess || localStorageSuccess) {
            this.notifyListeners('save', this.settings);
            return true;
        }

        return false;
    }

    /**
     * Save settings to localStorage only (synchronous)
     * @param {Object} settings - Settings to save
     * @returns {boolean} True if save was successful
     */
    saveToLocalStorage(settings) {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(settings));
            return true;
        } catch (error) {
            console.error('Failed to save voice settings to localStorage:', error);
            return false;
        }
    }

    /**
     * Update specific settings
     * @param {Object} updates - Settings to update
     * @returns {Promise<boolean>} True if update was successful
     */
    async update(updates) {
        const validatedUpdates = this.validateSettings(updates);
        if (validatedUpdates.isValid) {
            this.settings = { ...this.settings, ...updates };
            return await this.save();
        } else {
            console.warn('Invalid settings update:', validatedUpdates.errors);
            this.notifyListeners('validation_error', validatedUpdates.errors);
            return false;
        }
    }

    /**
     * Get current settings
     * @returns {Object} Current settings
     */
    get() {
        return { ...this.settings };
    }

    /**
     * Get specific setting value
     * @param {string} key - Setting key
     * @returns {*} Setting value
     */
    getValue(key) {
        return this.settings[key];
    }

    /**
     * Set specific setting value
     * @param {string} key - Setting key
     * @param {*} value - Setting value
     * @returns {Promise<boolean>} True if set was successful
     */
    async setValue(key, value) {
        const update = { [key]: value };
        return await this.update(update);
    }

    /**
     * Validate settings object
     * @param {Object} settings - Settings to validate
     * @returns {Object} Validation result with isValid flag and errors array
     */
    validateSettings(settings) {
        const errors = [];
        
        // Validate speech rate
        if (settings.speechRate !== undefined) {
            if (typeof settings.speechRate !== 'number' || settings.speechRate < 0.1 || settings.speechRate > 3.0) {
                errors.push('Speech rate must be a number between 0.1 and 3.0');
            }
        }

        // Validate speech pitch
        if (settings.speechPitch !== undefined) {
            if (typeof settings.speechPitch !== 'number' || settings.speechPitch < 0.0 || settings.speechPitch > 2.0) {
                errors.push('Speech pitch must be a number between 0.0 and 2.0');
            }
        }

        // Validate speech volume
        if (settings.speechVolume !== undefined) {
            if (typeof settings.speechVolume !== 'number' || settings.speechVolume < 0.0 || settings.speechVolume > 1.0) {
                errors.push('Speech volume must be a number between 0.0 and 1.0');
            }
        }

        // Validate microphone sensitivity
        if (settings.microphoneSensitivity !== undefined) {
            if (typeof settings.microphoneSensitivity !== 'number' || settings.microphoneSensitivity < 0.0 || settings.microphoneSensitivity > 1.0) {
                errors.push('Microphone sensitivity must be a number between 0.0 and 1.0');
            }
        }

        // Validate language
        if (settings.language !== undefined) {
            if (typeof settings.language !== 'string' || !/^[a-z]{2}-[A-Z]{2}$/.test(settings.language)) {
                errors.push('Language must be in format "xx-XX" (e.g., "en-US")');
            }
        }

        // Validate boolean settings
        const booleanSettings = ['autoPlayEnabled', 'noiseCancellation', 'continuousRecognition', 
                                'interimResults', 'voiceInputEnabled', 'voiceOutputEnabled', 
                                'visualFeedbackEnabled', 'keyboardShortcutsEnabled'];
        
        booleanSettings.forEach(key => {
            if (settings[key] !== undefined && typeof settings[key] !== 'boolean') {
                errors.push(`${key} must be a boolean value`);
            }
        });

        // Validate timeout values
        if (settings.autoStopTimeout !== undefined) {
            if (typeof settings.autoStopTimeout !== 'number' || settings.autoStopTimeout < 1000 || settings.autoStopTimeout > 10000) {
                errors.push('Auto stop timeout must be between 1000 and 10000 milliseconds');
            }
        }

        if (settings.maxRecordingTime !== undefined) {
            if (typeof settings.maxRecordingTime !== 'number' || settings.maxRecordingTime < 5000 || settings.maxRecordingTime > 300000) {
                errors.push('Max recording time must be between 5000 and 300000 milliseconds');
            }
        }

        return {
            isValid: errors.length === 0,
            errors
        };
    }

    /**
     * Reset settings to defaults
     * @returns {Promise<boolean>} True if reset was successful
     */
    async reset() {
        this.settings = this.getDefaults();
        const success = await this.save();
        if (success) {
            this.notifyListeners('reset', this.settings);
        }
        return success;
    }

    /**
     * Export settings as JSON string
     * @returns {string} JSON string of current settings
     */
    export() {
        return JSON.stringify(this.settings, null, 2);
    }

    /**
     * Import settings from JSON string
     * @param {string} jsonString - JSON string of settings
     * @returns {Promise<boolean>} True if import was successful
     */
    async import(jsonString) {
        try {
            const imported = JSON.parse(jsonString);
            const validation = this.validateSettings(imported);
            
            if (validation.isValid) {
                this.settings = { ...this.getDefaults(), ...imported };
                const success = await this.save();
                if (success) {
                    this.notifyListeners('import', this.settings);
                }
                return success;
            } else {
                console.warn('Invalid settings import:', validation.errors);
                this.notifyListeners('validation_error', validation.errors);
                return false;
            }
        } catch (error) {
            console.error('Failed to import settings:', error);
            return false;
        }
    }

    /**
     * Add change listener
     * @param {Function} listener - Function to call when settings change
     */
    addListener(listener) {
        this.listeners.add(listener);
    }

    /**
     * Remove change listener
     * @param {Function} listener - Function to remove
     */
    removeListener(listener) {
        this.listeners.delete(listener);
    }

    /**
     * Notify all listeners of changes
     * @param {string} action - Action that triggered the change
     * @param {Object} settings - Current settings
     */
    notifyListeners(action, settings) {
        this.listeners.forEach(listener => {
            try {
                listener(action, settings);
            } catch (error) {
                console.error('Error in settings listener:', error);
            }
        });
    }

    /**
     * Get settings optimized for speech synthesis
     * @returns {Object} Settings object for SpeechSynthesisUtterance
     */
    getSpeechSynthesisSettings() {
        return {
            rate: this.settings.speechRate,
            pitch: this.settings.speechPitch,
            volume: this.settings.speechVolume,
            lang: this.settings.language,
            voice: this.settings.voiceName !== 'default' ? this.settings.voiceName : null
        };
    }

    /**
     * Get settings optimized for speech recognition
     * @returns {Object} Settings object for SpeechRecognition
     */
    getSpeechRecognitionSettings() {
        return {
            lang: this.settings.language,
            continuous: this.settings.continuousRecognition,
            interimResults: this.settings.interimResults,
            maxAlternatives: this.settings.maxAlternatives
        };
    }

    /**
     * Check if voice features are enabled
     * @returns {Object} Object with enabled feature flags
     */
    getEnabledFeatures() {
        return {
            voiceInput: this.settings.voiceInputEnabled,
            voiceOutput: this.settings.voiceOutputEnabled,
            autoPlay: this.settings.autoPlayEnabled,
            visualFeedback: this.settings.visualFeedbackEnabled,
            keyboardShortcuts: this.settings.keyboardShortcutsEnabled
        };
    }

    /**
     * Create a settings preset
     * @param {string} name - Preset name
     * @param {Object} settings - Settings for the preset
     */
    createPreset(name, settings = null) {
        const presets = this.getPresets();
        presets[name] = settings || this.settings;
        localStorage.setItem(`${this.storageKey}_presets`, JSON.stringify(presets));
    }

    /**
     * Load a settings preset
     * @param {string} name - Preset name
     * @returns {Promise<boolean>} True if preset was loaded successfully
     */
    async loadPreset(name) {
        const presets = this.getPresets();
        if (presets[name]) {
            this.settings = { ...this.getDefaults(), ...presets[name] };
            const success = await this.save();
            if (success) {
                this.notifyListeners('preset_loaded', this.settings);
            }
            return success;
        }
        return false;
    }

    /**
     * Get all available presets
     * @returns {Object} Object with preset names as keys
     */
    getPresets() {
        try {
            const stored = localStorage.getItem(`${this.storageKey}_presets`);
            return stored ? JSON.parse(stored) : {};
        } catch (error) {
            console.warn('Failed to load presets:', error);
            return {};
        }
    }

    /**
     * Delete a preset
     * @param {string} name - Preset name
     * @returns {boolean} True if preset was deleted
     */
    deletePreset(name) {
        const presets = this.getPresets();
        if (presets[name]) {
            delete presets[name];
            localStorage.setItem(`${this.storageKey}_presets`, JSON.stringify(presets));
            return true;
        }
        return false;
    }

    /**
     * Load settings from backend API
     * @returns {Object|null} Settings from backend or null if failed
     */
    async loadFromBackend() {
        try {
            const response = await fetch('/voice/settings', {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    console.warn('Voice settings: User not authenticated');
                    return null;
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success && data.settings) {
                // Convert backend format to frontend format
                return this.convertBackendToFrontend(data.settings);
            }

            return null;
        } catch (error) {
            console.error('Failed to load voice settings from backend:', error);
            throw error;
        }
    }

    /**
     * Save settings to backend API
     * @param {Object} settings - Settings to save
     * @returns {boolean} True if save was successful
     */
    async saveToBackend(settings) {
        try {
            // Convert frontend format to backend format
            const backendSettings = this.convertFrontendToBackend(settings);

            const response = await fetch('/voice/settings', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    settings: backendSettings
                })
            });

            if (!response.ok) {
                if (response.status === 401) {
                    console.warn('Voice settings: User not authenticated');
                    return false;
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            return data.success === true;
        } catch (error) {
            console.error('Failed to save voice settings to backend:', error);
            throw error;
        }
    }

    /**
     * Convert backend settings format to frontend format
     * @param {Object} backendSettings - Settings from backend API
     * @returns {Object} Frontend format settings
     */
    convertBackendToFrontend(backendSettings) {
        return {
            autoPlayEnabled: backendSettings.auto_play_enabled,
            voiceName: backendSettings.voice_name,
            speechRate: backendSettings.speech_rate,
            speechPitch: backendSettings.speech_pitch,
            speechVolume: backendSettings.speech_volume,
            language: backendSettings.language,
            microphoneSensitivity: backendSettings.microphone_sensitivity,
            noiseCancellation: backendSettings.noise_cancellation,
            // Keep frontend-only settings from defaults
            continuousRecognition: false,
            interimResults: true,
            maxAlternatives: 1,
            voiceInputEnabled: true,
            voiceOutputEnabled: true,
            visualFeedbackEnabled: true,
            keyboardShortcutsEnabled: true,
            autoStopTimeout: 3000,
            maxRecordingTime: 60000,
            lastUpdated: Date.now()
        };
    }

    /**
     * Convert frontend settings format to backend format
     * @param {Object} frontendSettings - Settings from frontend
     * @returns {Object} Backend format settings
     */
    convertFrontendToBackend(frontendSettings) {
        return {
            auto_play_enabled: frontendSettings.autoPlayEnabled,
            voice_name: frontendSettings.voiceName,
            speech_rate: frontendSettings.speechRate,
            speech_pitch: frontendSettings.speechPitch,
            speech_volume: frontendSettings.speechVolume,
            language: frontendSettings.language,
            microphone_sensitivity: frontendSettings.microphoneSensitivity,
            noise_cancellation: frontendSettings.noiseCancellation
        };
    }

    /**
     * Initialize voice settings for user login
     * @returns {boolean} True if initialization was successful
     */
    async initializeForUser() {
        try {
            // Load settings from backend
            this.settings = await this.load();
            
            // Notify listeners that settings are initialized
            this.notifyListeners('initialized', this.settings);
            
            console.log('Voice settings initialized for user');
            return true;
        } catch (error) {
            console.error('Failed to initialize voice settings for user:', error);
            
            // Fallback to defaults
            this.settings = this.getDefaults();
            this.notifyListeners('initialized', this.settings);
            
            return false;
        }
    }

    /**
     * Clean up voice settings on user logout
     */
    cleanupOnLogout() {
        try {
            // Clear sensitive data but keep basic preferences in localStorage
            const basicSettings = {
                speechRate: this.settings.speechRate,
                speechPitch: this.settings.speechPitch,
                speechVolume: this.settings.speechVolume,
                language: this.settings.language,
                visualFeedbackEnabled: this.settings.visualFeedbackEnabled,
                keyboardShortcutsEnabled: this.settings.keyboardShortcutsEnabled
            };

            // Save basic settings to localStorage
            localStorage.setItem(`${this.storageKey}_basic`, JSON.stringify(basicSettings));
            
            // Clear full settings
            localStorage.removeItem(this.storageKey);
            
            // Reset to defaults
            this.settings = this.getDefaults();
            
            // Apply basic settings if they exist
            if (basicSettings) {
                this.settings = { ...this.settings, ...basicSettings };
            }
            
            this.notifyListeners('logout_cleanup', this.settings);
            
            console.log('Voice settings cleaned up on logout');
        } catch (error) {
            console.error('Failed to cleanup voice settings on logout:', error);
        }
    }

    /**
     * Restore basic settings after logout cleanup
     */
    restoreBasicSettings() {
        try {
            const basicSettings = localStorage.getItem(`${this.storageKey}_basic`);
            if (basicSettings) {
                const parsed = JSON.parse(basicSettings);
                this.settings = { ...this.settings, ...parsed };
                localStorage.removeItem(`${this.storageKey}_basic`);
                return true;
            }
        } catch (error) {
            console.warn('Failed to restore basic voice settings:', error);
        }
        return false;
    }

    /**
     * Sync settings with backend (for periodic sync)
     * @returns {boolean} True if sync was successful
     */
    async syncWithBackend() {
        try {
            const backendSettings = await this.loadFromBackend();
            if (backendSettings) {
                // Check if backend settings are newer
                const backendTime = backendSettings.lastUpdated || 0;
                const localTime = this.settings.lastUpdated || 0;
                
                if (backendTime > localTime) {
                    // Backend is newer, update local settings
                    this.settings = { ...this.getDefaults(), ...backendSettings };
                    this.saveToLocalStorage(this.settings);
                    this.notifyListeners('synced_from_backend', this.settings);
                    console.log('Voice settings synced from backend');
                } else if (localTime > backendTime) {
                    // Local is newer, update backend
                    await this.saveToBackend(this.settings);
                    console.log('Voice settings synced to backend');
                }
                
                return true;
            }
        } catch (error) {
            console.warn('Failed to sync voice settings with backend:', error);
        }
        return false;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceSettings;
} else {
    window.VoiceSettings = VoiceSettings;
}