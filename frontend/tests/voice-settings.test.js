/**
 * Unit Tests for VoiceSettings Class
 * Tests settings management, validation, and persistence
 */

// Mock localStorage for testing
class MockLocalStorage {
    constructor() {
        this.store = {};
    }

    getItem(key) {
        return this.store[key] || null;
    }

    setItem(key, value) {
        this.store[key] = String(value);
    }

    removeItem(key) {
        delete this.store[key];
    }

    clear() {
        this.store = {};
    }
}

// Test suite
class VoiceSettingsTest {
    constructor() {
        this.testResults = [];
        this.setupMocks();
    }

    setupMocks() {
        // Mock localStorage
        this.mockStorage = new MockLocalStorage();
        
        if (typeof window === 'undefined') {
            global.localStorage = this.mockStorage;
        } else {
            this.originalLocalStorage = window.localStorage;
            window.localStorage = this.mockStorage;
        }
    }

    restoreMocks() {
        if (typeof window !== 'undefined' && this.originalLocalStorage) {
            window.localStorage = this.originalLocalStorage;
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
        console.log('Running VoiceSettings Tests...\n');

        try {
            this.testDefaultSettings();
            this.testSettingsLoad();
            this.testSettingsSave();
            this.testSettingsUpdate();
            this.testSettingsValidation();
            this.testSettingsReset();
            this.testSettingsExportImport();
            this.testSettingsListeners();
            this.testSettingsPresets();
            this.testSpecializedSettings();
        } catch (error) {
            console.error('Test suite error:', error);
        } finally {
            this.restoreMocks();
        }

        this.printResults();
    }

    testDefaultSettings() {
        console.log('Testing default settings...');
        
        const settings = new VoiceSettings('test_settings');
        const defaults = settings.getDefaults();

        this.assert(typeof defaults === 'object', 'getDefaults should return object');
        this.assert(typeof defaults.autoPlayEnabled === 'boolean', 'autoPlayEnabled should be boolean');
        this.assert(typeof defaults.voiceName === 'string', 'voiceName should be string');
        this.assert(typeof defaults.speechRate === 'number', 'speechRate should be number');
        this.assert(typeof defaults.speechPitch === 'number', 'speechPitch should be number');
        this.assert(typeof defaults.speechVolume === 'number', 'speechVolume should be number');
        this.assert(typeof defaults.language === 'string', 'language should be string');
        this.assert(typeof defaults.microphoneSensitivity === 'number', 'microphoneSensitivity should be number');
        this.assert(typeof defaults.noiseCancellation === 'boolean', 'noiseCancellation should be boolean');

        // Test default values
        this.assert(defaults.autoPlayEnabled === false, 'autoPlayEnabled should default to false');
        this.assert(defaults.speechRate === 1.0, 'speechRate should default to 1.0');
        this.assert(defaults.language === 'en-US', 'language should default to en-US');
    }

    testSettingsLoad() {
        console.log('Testing settings load...');
        
        // Test loading with no stored settings
        const settings1 = new VoiceSettings('test_load_empty');
        const loaded1 = settings1.get();
        
        this.assert(typeof loaded1 === 'object', 'load should return object');
        this.assert(loaded1.speechRate === 1.0, 'should load default speechRate');

        // Test loading with stored settings
        this.mockStorage.setItem('test_load_stored', JSON.stringify({
            speechRate: 1.5,
            language: 'es-ES',
            autoPlayEnabled: true
        }));

        const settings2 = new VoiceSettings('test_load_stored');
        const loaded2 = settings2.get();

        this.assert(loaded2.speechRate === 1.5, 'should load stored speechRate');
        this.assert(loaded2.language === 'es-ES', 'should load stored language');
        this.assert(loaded2.autoPlayEnabled === true, 'should load stored autoPlayEnabled');
        this.assert(loaded2.speechPitch === 1.0, 'should merge with defaults for missing values');
    }

    testSettingsSave() {
        console.log('Testing settings save...');
        
        const settings = new VoiceSettings('test_save');
        
        // Test saving current settings
        const success1 = settings.save();
        this.assert(success1 === true, 'save should return true on success');

        // Test saving specific settings
        const newSettings = { speechRate: 2.0, language: 'fr-FR' };
        const success2 = settings.save(newSettings);
        this.assert(success2 === true, 'save with settings should return true');

        // Verify settings were saved
        const stored = JSON.parse(this.mockStorage.getItem('test_save'));
        this.assert(stored.speechRate === 2.0, 'should save speechRate');
        this.assert(stored.language === 'fr-FR', 'should save language');
        this.assert(typeof stored.lastUpdated === 'number', 'should set lastUpdated');
    }

    testSettingsUpdate() {
        console.log('Testing settings update...');
        
        const settings = new VoiceSettings('test_update');
        
        // Test valid update
        const success1 = settings.update({ speechRate: 1.5 });
        this.assert(success1 === true, 'valid update should return true');
        this.assert(settings.getValue('speechRate') === 1.5, 'should update speechRate');

        // Test invalid update
        const success2 = settings.update({ speechRate: 5.0 }); // Invalid range
        this.assert(success2 === false, 'invalid update should return false');
        this.assert(settings.getValue('speechRate') === 1.5, 'should not update with invalid value');

        // Test setValue
        const success3 = settings.setValue('language', 'de-DE');
        this.assert(success3 === true, 'setValue should return true');
        this.assert(settings.getValue('language') === 'de-DE', 'should set language');
    }

    testSettingsValidation() {
        console.log('Testing settings validation...');
        
        const settings = new VoiceSettings('test_validation');

        // Test valid settings
        const valid = settings.validateSettings({
            speechRate: 1.5,
            speechPitch: 1.2,
            speechVolume: 0.8,
            language: 'en-US',
            autoPlayEnabled: true
        });

        this.assert(valid.isValid === true, 'valid settings should pass validation');
        this.assert(Array.isArray(valid.errors), 'should return errors array');
        this.assert(valid.errors.length === 0, 'valid settings should have no errors');

        // Test invalid settings
        const invalid = settings.validateSettings({
            speechRate: 5.0, // Too high
            speechPitch: -1.0, // Too low
            speechVolume: 2.0, // Too high
            language: 'invalid', // Wrong format
            autoPlayEnabled: 'yes' // Wrong type
        });

        this.assert(invalid.isValid === false, 'invalid settings should fail validation');
        this.assert(invalid.errors.length > 0, 'invalid settings should have errors');
        this.assert(invalid.errors.some(e => e.includes('Speech rate')), 'should validate speech rate');
        this.assert(invalid.errors.some(e => e.includes('Speech pitch')), 'should validate speech pitch');
        this.assert(invalid.errors.some(e => e.includes('Language')), 'should validate language format');
    }

    testSettingsReset() {
        console.log('Testing settings reset...');
        
        const settings = new VoiceSettings('test_reset');
        
        // Modify settings
        settings.update({ speechRate: 2.0, language: 'es-ES' });
        this.assert(settings.getValue('speechRate') === 2.0, 'should update before reset');

        // Reset settings
        const success = settings.reset();
        this.assert(success === true, 'reset should return true');
        this.assert(settings.getValue('speechRate') === 1.0, 'should reset speechRate to default');
        this.assert(settings.getValue('language') === 'en-US', 'should reset language to default');
    }

    testSettingsExportImport() {
        console.log('Testing settings export/import...');
        
        const settings = new VoiceSettings('test_export_import');
        
        // Set some custom settings
        settings.update({ speechRate: 1.8, language: 'fr-FR', autoPlayEnabled: true });

        // Test export
        const exported = settings.export();
        this.assert(typeof exported === 'string', 'export should return string');
        
        const parsed = JSON.parse(exported);
        this.assert(parsed.speechRate === 1.8, 'exported settings should include speechRate');
        this.assert(parsed.language === 'fr-FR', 'exported settings should include language');

        // Test import
        const importData = JSON.stringify({
            speechRate: 0.5,
            language: 'de-DE',
            speechVolume: 0.7
        });

        const success = settings.import(importData);
        this.assert(success === true, 'import should return true');
        this.assert(settings.getValue('speechRate') === 0.5, 'should import speechRate');
        this.assert(settings.getValue('language') === 'de-DE', 'should import language');
        this.assert(settings.getValue('speechVolume') === 0.7, 'should import speechVolume');

        // Test invalid import
        const invalidSuccess = settings.import('invalid json');
        this.assert(invalidSuccess === false, 'invalid import should return false');
    }

    testSettingsListeners() {
        console.log('Testing settings listeners...');
        
        const settings = new VoiceSettings('test_listeners');
        let listenerCalled = false;
        let listenerAction = null;
        let listenerSettings = null;

        // Add listener
        const listener = (action, settingsData) => {
            listenerCalled = true;
            listenerAction = action;
            listenerSettings = settingsData;
        };

        settings.addListener(listener);

        // Test listener on save
        settings.save();
        this.assert(listenerCalled === true, 'listener should be called on save');
        this.assert(listenerAction === 'save', 'listener should receive save action');
        this.assert(typeof listenerSettings === 'object', 'listener should receive settings');

        // Reset for next test
        listenerCalled = false;

        // Test listener on reset
        settings.reset();
        this.assert(listenerCalled === true, 'listener should be called on reset');
        this.assert(listenerAction === 'reset', 'listener should receive reset action');

        // Remove listener
        settings.removeListener(listener);
        listenerCalled = false;
        settings.save();
        this.assert(listenerCalled === false, 'removed listener should not be called');
    }

    testSettingsPresets() {
        console.log('Testing settings presets...');
        
        const settings = new VoiceSettings('test_presets');

        // Create preset
        settings.update({ speechRate: 1.5, language: 'es-ES' });
        settings.createPreset('spanish_fast');

        // Load preset
        settings.update({ speechRate: 0.5, language: 'en-US' }); // Change settings
        const success = settings.loadPreset('spanish_fast');
        
        this.assert(success === true, 'loadPreset should return true');
        this.assert(settings.getValue('speechRate') === 1.5, 'should load preset speechRate');
        this.assert(settings.getValue('language') === 'es-ES', 'should load preset language');

        // Get presets
        const presets = settings.getPresets();
        this.assert(typeof presets === 'object', 'getPresets should return object');
        this.assert(typeof presets.spanish_fast === 'object', 'should contain created preset');

        // Delete preset
        const deleteSuccess = settings.deletePreset('spanish_fast');
        this.assert(deleteSuccess === true, 'deletePreset should return true');
        
        const presetsAfterDelete = settings.getPresets();
        this.assert(presetsAfterDelete.spanish_fast === undefined, 'preset should be deleted');

        // Test loading non-existent preset
        const loadNonExistent = settings.loadPreset('non_existent');
        this.assert(loadNonExistent === false, 'loading non-existent preset should return false');
    }

    testSpecializedSettings() {
        console.log('Testing specialized settings...');
        
        const settings = new VoiceSettings('test_specialized');
        settings.update({
            speechRate: 1.5,
            speechPitch: 1.2,
            speechVolume: 0.8,
            language: 'fr-FR',
            voiceName: 'test-voice',
            continuousRecognition: true,
            interimResults: false,
            maxAlternatives: 3
        });

        // Test speech synthesis settings
        const synthSettings = settings.getSpeechSynthesisSettings();
        this.assert(synthSettings.rate === 1.5, 'should return correct rate');
        this.assert(synthSettings.pitch === 1.2, 'should return correct pitch');
        this.assert(synthSettings.volume === 0.8, 'should return correct volume');
        this.assert(synthSettings.lang === 'fr-FR', 'should return correct language');
        this.assert(synthSettings.voice === 'test-voice', 'should return correct voice');

        // Test speech recognition settings
        const recSettings = settings.getSpeechRecognitionSettings();
        this.assert(recSettings.lang === 'fr-FR', 'should return correct language');
        this.assert(recSettings.continuous === true, 'should return correct continuous setting');
        this.assert(recSettings.interimResults === false, 'should return correct interimResults setting');
        this.assert(recSettings.maxAlternatives === 3, 'should return correct maxAlternatives');

        // Test enabled features
        settings.update({
            voiceInputEnabled: true,
            voiceOutputEnabled: false,
            autoPlayEnabled: true,
            visualFeedbackEnabled: false,
            keyboardShortcutsEnabled: true
        });

        const enabledFeatures = settings.getEnabledFeatures();
        this.assert(enabledFeatures.voiceInput === true, 'should return correct voiceInput state');
        this.assert(enabledFeatures.voiceOutput === false, 'should return correct voiceOutput state');
        this.assert(enabledFeatures.autoPlay === true, 'should return correct autoPlay state');
        this.assert(enabledFeatures.visualFeedback === false, 'should return correct visualFeedback state');
        this.assert(enabledFeatures.keyboardShortcuts === true, 'should return correct keyboardShortcuts state');
    }

    printResults() {
        console.log('\n=== VoiceSettings Test Results ===');
        
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

// Run tests if this file is executed directly
if (typeof require !== 'undefined' && require.main === module) {
    // Load VoiceSettings class
    const VoiceSettings = require('../voice-settings.js');
    
    const test = new VoiceSettingsTest();
    test.runTests().then(() => {
        process.exit(test.testResults.some(r => r.status === 'FAIL') ? 1 : 0);
    });
} else if (typeof window !== 'undefined') {
    // Browser environment
    window.VoiceSettingsTest = VoiceSettingsTest;
}

// Export for use in other test files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceSettingsTest;
}