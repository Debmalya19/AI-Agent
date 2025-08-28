/**
 * Voice Feature Toggles for A/B Testing and Gradual Rollout
 * Manages feature flags, A/B testing, and gradual feature rollout
 */

class VoiceFeatureToggleManager {
    constructor(options = {}) {
        this.options = {
            userId: options.userId || 'anonymous',
            environment: options.environment || 'production',
            enableLocalOverrides: options.enableLocalOverrides !== false,
            enableRemoteConfig: options.enableRemoteConfig !== false,
            configEndpoint: options.configEndpoint || '/voice/config',
            refreshInterval: options.refreshInterval || 300000, // 5 minutes
            debugMode: options.debugMode || false,
            ...options
        };

        // Feature toggle state
        this.toggles = new Map();
        this.abTestVariants = new Map();
        this.rolloutPercentages = new Map();
        this.userGroups = new Set();

        // Configuration cache
        this.configCache = null;
        this.lastConfigFetch = 0;
        this.configRefreshInterval = null;

        // Event listeners
        this.listeners = new Map();

        this.initialize();
    }

    /**
     * Initialize feature toggle manager
     */
    async initialize() {
        this.log('Initializing voice feature toggle manager');

        // Load local overrides first
        if (this.options.enableLocalOverrides) {
            this.loadLocalOverrides();
        }

        // Fetch remote configuration
        if (this.options.enableRemoteConfig) {
            await this.fetchRemoteConfig();
            this.startConfigRefresh();
        }

        // Set up default toggles if none loaded
        if (this.toggles.size === 0) {
            this.setDefaultToggles();
        }

        this.log('Voice feature toggle manager initialized');
    }

    /**
     * Set default feature toggles
     */
    setDefaultToggles() {
        const defaultToggles = {
            'voice_input': { enabled: true, rollout: 100 },
            'voice_output': { enabled: true, rollout: 100 },
            'voice_settings': { enabled: true, rollout: 100 },
            'voice_analytics': { enabled: true, rollout: 100 },
            'error_handling': { enabled: true, rollout: 100 },
            'performance_tracking': { enabled: true, rollout: 100 },
            'lazy_loading': { enabled: true, rollout: 100 },
            'resource_monitoring': { enabled: true, rollout: 100 },
            'rate_limiting': { enabled: true, rollout: 100 },
            'ab_testing': { enabled: false, rollout: 0 },
            'advanced_tts': { enabled: false, rollout: 0 },
            'noise_cancellation': { enabled: false, rollout: 0 },
            'voice_shortcuts': { enabled: false, rollout: 0 },
            'multi_language': { enabled: false, rollout: 0 }
        };

        Object.entries(defaultToggles).forEach(([feature, config]) => {
            this.toggles.set(feature, {
                enabled: config.enabled,
                rolloutPercentage: config.rollout,
                userGroups: [],
                abTestVariant: null,
                conditions: {},
                metadata: { source: 'default' }
            });
        });

        this.log('Default feature toggles set');
    }

    /**
     * Load local overrides from localStorage
     */
    loadLocalOverrides() {
        try {
            const overrides = localStorage.getItem('voice_feature_overrides');
            if (overrides) {
                const parsed = JSON.parse(overrides);
                Object.entries(parsed).forEach(([feature, config]) => {
                    this.toggles.set(feature, {
                        ...config,
                        metadata: { source: 'local_override' }
                    });
                });
                this.log('Local overrides loaded:', Object.keys(parsed));
            }
        } catch (error) {
            this.log('Failed to load local overrides:', error);
        }
    }

    /**
     * Fetch remote configuration
     */
    async fetchRemoteConfig() {
        try {
            const response = await fetch(`${this.options.configEndpoint}?userId=${this.options.userId}`, {
                credentials: 'include',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const config = await response.json();
            this.processRemoteConfig(config);
            this.configCache = config;
            this.lastConfigFetch = Date.now();

            this.log('Remote configuration fetched successfully');

        } catch (error) {
            this.log('Failed to fetch remote configuration:', error);
        }
    }

    /**
     * Process remote configuration
     */
    processRemoteConfig(config) {
        // Update feature toggles
        if (config.featureToggles) {
            Object.entries(config.featureToggles).forEach(([feature, enabled]) => {
                const existing = this.toggles.get(feature) || {};
                this.toggles.set(feature, {
                    ...existing,
                    enabled,
                    metadata: { source: 'remote', lastUpdated: Date.now() }
                });
            });
        }

        // Update rollout percentages
        if (config.rolloutPercentages) {
            Object.entries(config.rolloutPercentages).forEach(([feature, percentage]) => {
                const existing = this.toggles.get(feature) || {};
                this.toggles.set(feature, {
                    ...existing,
                    rolloutPercentage: percentage
                });
                this.rolloutPercentages.set(feature, percentage);
            });
        }

        // Update A/B test configurations
        if (config.abTests) {
            Object.entries(config.abTests).forEach(([testName, testConfig]) => {
                this.configureABTest(testName, testConfig);
            });
        }

        // Update user groups
        if (config.userGroups) {
            this.userGroups = new Set(config.userGroups);
        }

        // Emit configuration update event
        this.emitEvent('configUpdated', { config, timestamp: Date.now() });
    }

    /**
     * Start configuration refresh interval
     */
    startConfigRefresh() {
        if (this.configRefreshInterval) return;

        this.configRefreshInterval = setInterval(async () => {
            await this.fetchRemoteConfig();
        }, this.options.refreshInterval);
    }

    /**
     * Check if a feature is enabled for the current user
     * @param {string} feature - Feature name
     * @param {Object} context - Additional context for evaluation
     * @returns {boolean} Whether feature is enabled
     */
    isFeatureEnabled(feature, context = {}) {
        const toggle = this.toggles.get(feature);
        if (!toggle) {
            this.log(`Unknown feature: ${feature}`);
            return false;
        }

        // Check if globally disabled
        if (!toggle.enabled) {
            return false;
        }

        // Check user group restrictions
        if (toggle.userGroups && toggle.userGroups.length > 0) {
            const hasRequiredGroup = toggle.userGroups.some(group => 
                this.userGroups.has(group)
            );
            if (!hasRequiredGroup) {
                return false;
            }
        }

        // Check rollout percentage
        if (toggle.rolloutPercentage < 100) {
            if (!this.isUserInRollout(feature, toggle.rolloutPercentage)) {
                return false;
            }
        }

        // Check additional conditions
        if (toggle.conditions && !this.evaluateConditions(toggle.conditions, context)) {
            return false;
        }

        return true;
    }

    /**
     * Check if user is in rollout percentage
     * @param {string} feature - Feature name
     * @param {number} percentage - Rollout percentage (0-100)
     * @returns {boolean} Whether user is in rollout
     */
    isUserInRollout(feature, percentage) {
        // Use consistent hash for user-based rollout
        const hash = this.hashString(`${this.options.userId}:${feature}`);
        const userPercentile = (hash % 100) + 1;
        return userPercentile <= percentage;
    }

    /**
     * Get A/B test variant for a feature
     * @param {string} testName - A/B test name
     * @param {Object} context - Additional context
     * @returns {string|null} Variant name or null
     */
    getABTestVariant(testName, context = {}) {
        if (!this.isFeatureEnabled('ab_testing')) {
            return null;
        }

        const testConfig = this.abTestVariants.get(testName);
        if (!testConfig) {
            return null;
        }

        // Check if user is in test
        if (!this.isUserInRollout(testName, testConfig.percentage)) {
            return null;
        }

        // Check test conditions
        if (testConfig.conditions && !this.evaluateConditions(testConfig.conditions, context)) {
            return null;
        }

        // Determine variant
        const hash = this.hashString(`${this.options.userId}:${testName}:variant`);
        const variantIndex = hash % testConfig.variants.length;
        const variant = testConfig.variants[variantIndex];

        // Track variant assignment
        this.trackABTestAssignment(testName, variant, context);

        return variant;
    }

    /**
     * Configure A/B test
     * @param {string} testName - Test name
     * @param {Object} config - Test configuration
     */
    configureABTest(testName, config) {
        this.abTestVariants.set(testName, {
            variants: config.variants || ['A', 'B'],
            percentage: config.percentage || 50,
            conditions: config.conditions || {},
            metadata: config.metadata || {}
        });

        this.log(`A/B test configured: ${testName}`, config);
    }

    /**
     * Evaluate conditions
     * @param {Object} conditions - Conditions to evaluate
     * @param {Object} context - Context for evaluation
     * @returns {boolean} Whether conditions are met
     */
    evaluateConditions(conditions, context) {
        try {
            // Browser conditions
            if (conditions.browsers) {
                const userAgent = navigator.userAgent.toLowerCase();
                const matchesBrowser = conditions.browsers.some(browser => 
                    userAgent.includes(browser.toLowerCase())
                );
                if (!matchesBrowser) return false;
            }

            // Platform conditions
            if (conditions.platforms) {
                const platform = navigator.platform.toLowerCase();
                const matchesPlatform = conditions.platforms.some(p => 
                    platform.includes(p.toLowerCase())
                );
                if (!matchesPlatform) return false;
            }

            // Time-based conditions
            if (conditions.timeRange) {
                const now = new Date();
                const start = new Date(conditions.timeRange.start);
                const end = new Date(conditions.timeRange.end);
                if (now < start || now > end) return false;
            }

            // Custom context conditions
            if (conditions.context) {
                for (const [key, expectedValue] of Object.entries(conditions.context)) {
                    if (context[key] !== expectedValue) return false;
                }
            }

            return true;

        } catch (error) {
            this.log('Error evaluating conditions:', error);
            return false;
        }
    }

    /**
     * Hash string for consistent user assignment
     * @param {string} str - String to hash
     * @returns {number} Hash value
     */
    hashString(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return Math.abs(hash);
    }

    /**
     * Track A/B test assignment
     * @param {string} testName - Test name
     * @param {string} variant - Assigned variant
     * @param {Object} context - Assignment context
     */
    trackABTestAssignment(testName, variant, context) {
        try {
            // Send assignment tracking
            fetch('/voice/analytics', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    type: 'ab_test_assignment',
                    testName,
                    variant,
                    userId: this.options.userId,
                    context,
                    timestamp: Date.now()
                }),
                credentials: 'include'
            }).catch(error => {
                this.log('Failed to track A/B test assignment:', error);
            });

        } catch (error) {
            this.log('Error tracking A/B test assignment:', error);
        }
    }

    /**
     * Override feature toggle locally
     * @param {string} feature - Feature name
     * @param {boolean} enabled - Whether feature is enabled
     * @param {Object} options - Additional options
     */
    overrideFeature(feature, enabled, options = {}) {
        if (!this.options.enableLocalOverrides) {
            this.log('Local overrides are disabled');
            return false;
        }

        const toggle = this.toggles.get(feature) || {};
        this.toggles.set(feature, {
            ...toggle,
            enabled,
            rolloutPercentage: enabled ? 100 : 0,
            ...options,
            metadata: { source: 'local_override', timestamp: Date.now() }
        });

        // Save to localStorage
        this.saveLocalOverrides();

        // Emit override event
        this.emitEvent('featureOverridden', { feature, enabled, options });

        this.log(`Feature ${feature} overridden: ${enabled}`);
        return true;
    }

    /**
     * Save local overrides to localStorage
     */
    saveLocalOverrides() {
        try {
            const overrides = {};
            this.toggles.forEach((config, feature) => {
                if (config.metadata?.source === 'local_override') {
                    overrides[feature] = config;
                }
            });

            localStorage.setItem('voice_feature_overrides', JSON.stringify(overrides));
        } catch (error) {
            this.log('Failed to save local overrides:', error);
        }
    }

    /**
     * Clear local overrides
     */
    clearLocalOverrides() {
        try {
            localStorage.removeItem('voice_feature_overrides');
            
            // Remove local overrides from toggles
            const toRemove = [];
            this.toggles.forEach((config, feature) => {
                if (config.metadata?.source === 'local_override') {
                    toRemove.push(feature);
                }
            });

            toRemove.forEach(feature => this.toggles.delete(feature));

            // Reload remote config
            if (this.options.enableRemoteConfig) {
                this.fetchRemoteConfig();
            }

            this.log('Local overrides cleared');
            this.emitEvent('overridesCleared', { timestamp: Date.now() });

        } catch (error) {
            this.log('Failed to clear local overrides:', error);
        }
    }

    /**
     * Get all feature states
     * @param {Object} context - Context for evaluation
     * @returns {Object} Feature states
     */
    getAllFeatureStates(context = {}) {
        const states = {};
        this.toggles.forEach((config, feature) => {
            states[feature] = {
                enabled: this.isFeatureEnabled(feature, context),
                config: {
                    rolloutPercentage: config.rolloutPercentage,
                    userGroups: config.userGroups,
                    conditions: config.conditions,
                    metadata: config.metadata
                }
            };
        });
        return states;
    }

    /**
     * Get A/B test states
     * @param {Object} context - Context for evaluation
     * @returns {Object} A/B test states
     */
    getAllABTestStates(context = {}) {
        const states = {};
        this.abTestVariants.forEach((config, testName) => {
            states[testName] = {
                variant: this.getABTestVariant(testName, context),
                config: config
            };
        });
        return states;
    }

    /**
     * Add event listener
     * @param {string} event - Event name
     * @param {Function} callback - Callback function
     */
    addEventListener(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);
    }

    /**
     * Remove event listener
     * @param {string} event - Event name
     * @param {Function} callback - Callback function
     */
    removeEventListener(event, callback) {
        const eventListeners = this.listeners.get(event);
        if (eventListeners) {
            eventListeners.delete(callback);
        }
    }

    /**
     * Emit event
     * @param {string} event - Event name
     * @param {Object} data - Event data
     */
    emitEvent(event, data) {
        const eventListeners = this.listeners.get(event);
        if (eventListeners) {
            eventListeners.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    this.log(`Error in event listener for ${event}:`, error);
                }
            });
        }

        // Also emit as DOM event
        try {
            const customEvent = new CustomEvent(`voiceFeatureToggle:${event}`, {
                detail: data
            });
            window.dispatchEvent(customEvent);
        } catch (error) {
            this.log('Failed to emit DOM event:', error);
        }
    }

    /**
     * Get debug information
     * @returns {Object} Debug information
     */
    getDebugInfo() {
        return {
            userId: this.options.userId,
            environment: this.options.environment,
            toggleCount: this.toggles.size,
            abTestCount: this.abTestVariants.size,
            userGroups: Array.from(this.userGroups),
            lastConfigFetch: this.lastConfigFetch,
            configCache: this.configCache
        };
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        if (this.configRefreshInterval) {
            clearInterval(this.configRefreshInterval);
            this.configRefreshInterval = null;
        }

        this.listeners.clear();
        this.log('Voice feature toggle manager cleaned up');
    }

    /**
     * Log messages with debug mode check
     */
    log(message, ...args) {
        if (this.options.debugMode) {
            console.log(`[VoiceFeatureToggleManager] ${message}`, ...args);
        }
    }
}

/**
 * Voice Feature Toggle Helper Functions
 */
class VoiceFeatureToggleHelper {
    /**
     * Create feature toggle manager with environment detection
     * @param {Object} options - Configuration options
     * @returns {VoiceFeatureToggleManager} Toggle manager instance
     */
    static createManager(options = {}) {
        // Detect environment
        const hostname = window.location.hostname;
        let environment = 'production';
        
        if (hostname.includes('localhost') || hostname.includes('127.0.0.1')) {
            environment = 'development';
        } else if (hostname.includes('staging') || hostname.includes('test')) {
            environment = 'staging';
        }

        // Get user ID from session or generate anonymous ID
        let userId = 'anonymous';
        try {
            const sessionData = sessionStorage.getItem('user_session');
            if (sessionData) {
                const parsed = JSON.parse(sessionData);
                userId = parsed.userId || parsed.id || 'anonymous';
            }
        } catch (error) {
            console.warn('Failed to get user ID from session:', error);
        }

        return new VoiceFeatureToggleManager({
            userId,
            environment,
            debugMode: environment === 'development',
            ...options
        });
    }

    /**
     * Create A/B test configuration
     * @param {string} testName - Test name
     * @param {Array} variants - Test variants
     * @param {number} percentage - Test percentage
     * @param {Object} conditions - Test conditions
     * @returns {Object} A/B test configuration
     */
    static createABTest(testName, variants = ['A', 'B'], percentage = 50, conditions = {}) {
        return {
            [testName]: {
                variants,
                percentage,
                conditions,
                metadata: {
                    created: Date.now(),
                    creator: 'VoiceFeatureToggleHelper'
                }
            }
        };
    }

    /**
     * Create rollout configuration
     * @param {Object} features - Features with rollout percentages
     * @returns {Object} Rollout configuration
     */
    static createRolloutConfig(features) {
        const config = {};
        Object.entries(features).forEach(([feature, percentage]) => {
            config[feature] = Math.max(0, Math.min(100, percentage));
        });
        return config;
    }
}

// Global toggle manager instance
let voiceToggleManager = null;

/**
 * Initialize voice feature toggle manager
 * @param {Object} options - Configuration options
 * @returns {VoiceFeatureToggleManager} Toggle manager instance
 */
function initializeVoiceFeatureToggles(options = {}) {
    if (!voiceToggleManager) {
        voiceToggleManager = VoiceFeatureToggleHelper.createManager(options);
    }
    return voiceToggleManager;
}

/**
 * Check if voice feature is enabled
 * @param {string} feature - Feature name
 * @param {Object} context - Additional context
 * @returns {boolean} Whether feature is enabled
 */
function isVoiceFeatureEnabled(feature, context = {}) {
    if (!voiceToggleManager) {
        initializeVoiceFeatureToggles();
    }
    return voiceToggleManager.isFeatureEnabled(feature, context);
}

/**
 * Get A/B test variant
 * @param {string} testName - Test name
 * @param {Object} context - Additional context
 * @returns {string|null} Variant name or null
 */
function getVoiceABTestVariant(testName, context = {}) {
    if (!voiceToggleManager) {
        initializeVoiceFeatureToggles();
    }
    return voiceToggleManager.getABTestVariant(testName, context);
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        VoiceFeatureToggleManager,
        VoiceFeatureToggleHelper,
        initializeVoiceFeatureToggles,
        isVoiceFeatureEnabled,
        getVoiceABTestVariant
    };
}