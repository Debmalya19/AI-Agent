/**
 * Voice Module Lazy Loader
 * Implements lazy loading for voice JavaScript modules to reduce initial page load
 */

class VoiceModuleLoader {
    constructor(options = {}) {
        this.options = {
            baseUrl: options.baseUrl || '',
            enableCaching: options.enableCaching !== false,
            enableCompression: options.enableCompression !== false,
            loadTimeout: options.loadTimeout || 10000,
            retryAttempts: options.retryAttempts || 3,
            debugMode: options.debugMode || false,
            ...options
        };

        // Module registry
        this.modules = new Map();
        this.loadingPromises = new Map();
        this.loadedModules = new Set();
        this.failedModules = new Set();

        // Performance tracking
        this.loadTimes = new Map();
        this.cacheHits = 0;
        this.cacheMisses = 0;

        // Initialize cache if enabled
        if (this.options.enableCaching) {
            this.initializeCache();
        }

        this.log('VoiceModuleLoader initialized', this.options);
    }

    /**
     * Initialize module cache
     */
    initializeCache() {
        try {
            // Check for cache API support
            if ('caches' in window) {
                this.cacheAPI = true;
                this.cacheName = 'voice-modules-v1';
            } else {
                // Fallback to memory cache
                this.memoryCache = new Map();
            }
        } catch (error) {
            this.log('Cache initialization failed, using memory fallback', error);
            this.memoryCache = new Map();
        }
    }

    /**
     * Register voice modules for lazy loading
     */
    registerModules() {
        const modules = {
            'voice-capabilities': {
                url: 'voice-capabilities.js',
                dependencies: [],
                priority: 'high',
                preload: true
            },
            'voice-settings': {
                url: 'voice-settings.js',
                dependencies: [],
                priority: 'high',
                preload: true
            },
            'voice-controller': {
                url: 'voice-controller.js',
                dependencies: ['voice-capabilities', 'voice-settings'],
                priority: 'critical',
                preload: false
            },
            'voice-ui': {
                url: 'voice-ui.js',
                dependencies: ['voice-controller'],
                priority: 'medium',
                preload: false
            },
            'voice-analytics': {
                url: 'voice-analytics.js',
                dependencies: [],
                priority: 'low',
                preload: false
            },
            'voice-error-handler': {
                url: 'voice-error-handler.js',
                dependencies: [],
                priority: 'medium',
                preload: false
            }
        };

        // Register each module
        Object.entries(modules).forEach(([name, config]) => {
            this.modules.set(name, {
                ...config,
                loaded: false,
                loading: false,
                error: null,
                loadTime: null
            });
        });

        this.log('Registered modules:', Array.from(this.modules.keys()));
    }

    /**
     * Preload high-priority modules
     */
    async preloadCriticalModules() {
        const criticalModules = Array.from(this.modules.entries())
            .filter(([name, config]) => config.preload || config.priority === 'critical')
            .sort(([, a], [, b]) => this.getPriorityWeight(a.priority) - this.getPriorityWeight(b.priority));

        this.log('Preloading critical modules:', criticalModules.map(([name]) => name));

        const preloadPromises = criticalModules.map(([name]) =>
            this.loadModule(name, { background: true })
        );

        try {
            await Promise.allSettled(preloadPromises);
            this.log('Critical modules preloaded');
        } catch (error) {
            this.log('Some critical modules failed to preload', error);
        }
    }

    /**
     * Get priority weight for sorting
     */
    getPriorityWeight(priority) {
        const weights = {
            'critical': 1,
            'high': 2,
            'medium': 3,
            'low': 4
        };
        return weights[priority] || 5;
    }

    /**
     * Load a voice module with dependencies
     * @param {string} moduleName - Name of the module to load
     * @param {Object} options - Loading options
     * @returns {Promise} Promise that resolves when module is loaded
     */
    async loadModule(moduleName, options = {}) {
        // Check if already loaded
        if (this.loadedModules.has(moduleName)) {
            this.cacheHits++;
            return this.modules.get(moduleName);
        }

        // Check if currently loading
        if (this.loadingPromises.has(moduleName)) {
            return this.loadingPromises.get(moduleName);
        }

        // Check if previously failed and should retry
        if (this.failedModules.has(moduleName) && !options.retry) {
            throw new Error(`Module ${moduleName} previously failed to load`);
        }

        const moduleConfig = this.modules.get(moduleName);
        if (!moduleConfig) {
            throw new Error(`Unknown module: ${moduleName}`);
        }

        // Create loading promise
        const loadingPromise = this.loadModuleWithDependencies(moduleName, options);
        this.loadingPromises.set(moduleName, loadingPromise);

        try {
            const result = await loadingPromise;
            this.loadedModules.add(moduleName);
            this.failedModules.delete(moduleName);
            this.loadingPromises.delete(moduleName);
            this.cacheMisses++;
            return result;
        } catch (error) {
            this.failedModules.add(moduleName);
            this.loadingPromises.delete(moduleName);
            throw error;
        }
    }

    /**
     * Load module with its dependencies
     */
    async loadModuleWithDependencies(moduleName, options = {}) {
        const moduleConfig = this.modules.get(moduleName);
        const startTime = performance.now();

        try {
            // Load dependencies first
            if (moduleConfig.dependencies && moduleConfig.dependencies.length > 0) {
                this.log(`Loading dependencies for ${moduleName}:`, moduleConfig.dependencies);

                const dependencyPromises = moduleConfig.dependencies.map(dep =>
                    this.loadModule(dep, { ...options, background: true })
                );

                await Promise.all(dependencyPromises);
            }

            // Load the module itself
            this.log(`Loading module: ${moduleName}`);
            moduleConfig.loading = true;

            const moduleContent = await this.fetchModule(moduleConfig.url, options);
            await this.executeModule(moduleName, moduleContent, options);

            // Record load time
            const loadTime = performance.now() - startTime;
            moduleConfig.loadTime = loadTime;
            this.loadTimes.set(moduleName, loadTime);

            moduleConfig.loaded = true;
            moduleConfig.loading = false;
            moduleConfig.error = null;

            this.log(`Module ${moduleName} loaded successfully in ${loadTime.toFixed(2)}ms`);

            // Emit load event
            this.emitEvent('moduleLoaded', {
                moduleName,
                loadTime,
                dependencies: moduleConfig.dependencies
            });

            return moduleConfig;

        } catch (error) {
            const loadTime = performance.now() - startTime;
            moduleConfig.loading = false;
            moduleConfig.error = error;

            this.log(`Module ${moduleName} failed to load after ${loadTime.toFixed(2)}ms:`, error);

            // Emit error event
            this.emitEvent('moduleError', {
                moduleName,
                error,
                loadTime
            });

            throw error;
        }
    }

    /**
     * Fetch module content with caching
     */
    async fetchModule(url, options = {}) {
        const fullUrl = this.options.baseUrl + url;

        // Try cache first
        if (this.options.enableCaching) {
            const cached = await this.getCachedModule(fullUrl);
            if (cached) {
                this.log(`Cache hit for ${url}`);
                return cached;
            }
        }

        // Fetch with timeout and retry logic
        let lastError;
        for (let attempt = 1; attempt <= this.options.retryAttempts; attempt++) {
            try {
                this.log(`Fetching ${url} (attempt ${attempt})`);

                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), this.options.loadTimeout);

                const response = await fetch(fullUrl, {
                    signal: controller.signal,
                    cache: 'default',
                    headers: this.options.enableCompression ? {
                        'Accept-Encoding': 'gzip, deflate, br'
                    } : {}
                });

                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const content = await response.text();

                // Cache the content
                if (this.options.enableCaching) {
                    await this.cacheModule(fullUrl, content);
                }

                return content;

            } catch (error) {
                lastError = error;
                this.log(`Fetch attempt ${attempt} failed for ${url}:`, error);

                if (attempt < this.options.retryAttempts) {
                    // Exponential backoff
                    const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }

        throw new Error(`Failed to fetch ${url} after ${this.options.retryAttempts} attempts: ${lastError.message}`);
    }

    /**
     * Execute module content safely with performance monitoring
     */
    async executeModule(moduleName, content, options = {}) {
        try {
            const startTime = performance.now();

            // Check if module should be executed based on feature toggles
            if (window.isVoiceFeatureEnabled && !window.isVoiceFeatureEnabled('lazy_loading')) {
                throw new Error('Lazy loading is disabled');
            }

            // Create isolated scope for module execution
            const moduleScope = {
                console: options.background ? { log: () => { }, warn: () => { }, error: () => { } } : console,
                window,
                document,
                // Add performance monitoring
                performance: {
                    ...performance,
                    mark: (name) => performance.mark(`voice-module-${moduleName}-${name}`),
                    measure: (name, start, end) => performance.measure(`voice-module-${moduleName}-${name}`, start, end)
                }
            };

            // Wrap content with performance monitoring
            const wrappedContent = `
                (function(moduleScope) {
                    try {
                        moduleScope.performance.mark('execution-start');
                        with(moduleScope) {
                            ${content}
                        }
                        moduleScope.performance.mark('execution-end');
                        moduleScope.performance.measure('execution-time', 'execution-start', 'execution-end');
                    } catch (error) {
                        console.error('Module execution error:', error);
                        throw error;
                    }
                })(arguments[0]);
            `;

            // Execute the module
            const script = document.createElement('script');
            script.textContent = wrappedContent;
            script.setAttribute('data-module', moduleName);
            script.setAttribute('data-load-time', Date.now().toString());

            // Add to head temporarily for execution
            document.head.appendChild(script);

            // Remove script element after execution with memory cleanup
            setTimeout(() => {
                if (script.parentNode) {
                    script.parentNode.removeChild(script);
                }
                // Trigger garbage collection hint
                if (window.gc) {
                    window.gc();
                }
            }, 0);

            const executionTime = performance.now() - startTime;
            this.log(`Module ${moduleName} executed in ${executionTime.toFixed(2)}ms`);

            // Report performance metrics
            if (window.voicePerformanceMonitor) {
                window.voicePerformanceMonitor.recordModuleExecution(moduleName, executionTime);
            }

        } catch (error) {
            throw new Error(`Failed to execute module ${moduleName}: ${error.message}`);
        }
    }

    /**
     * Get cached module content
     */
    async getCachedModule(url) {
        try {
            if (this.cacheAPI) {
                const cache = await caches.open(this.cacheName);
                const response = await cache.match(url);
                if (response) {
                    return await response.text();
                }
            } else if (this.memoryCache) {
                return this.memoryCache.get(url);
            }
        } catch (error) {
            this.log('Cache retrieval failed:', error);
        }
        return null;
    }

    /**
     * Cache module content
     */
    async cacheModule(url, content) {
        try {
            if (this.cacheAPI) {
                const cache = await caches.open(this.cacheName);
                const response = new Response(content, {
                    headers: { 'Content-Type': 'application/javascript' }
                });
                await cache.put(url, response);
            } else if (this.memoryCache) {
                this.memoryCache.set(url, content);
            }
        } catch (error) {
            this.log('Cache storage failed:', error);
        }
    }

    /**
     * Load voice features on demand
     */
    async loadVoiceFeatures(features = []) {
        const featureModules = {
            'input': ['voice-capabilities', 'voice-settings', 'voice-controller'],
            'output': ['voice-capabilities', 'voice-settings', 'voice-controller'],
            'ui': ['voice-ui'],
            'analytics': ['voice-analytics'],
            'error-handling': ['voice-error-handler']
        };

        const modulesToLoad = new Set();

        // Determine which modules to load based on requested features
        features.forEach(feature => {
            if (featureModules[feature]) {
                featureModules[feature].forEach(module => modulesToLoad.add(module));
            }
        });

        // If no specific features requested, load all
        if (modulesToLoad.size === 0) {
            Array.from(this.modules.keys()).forEach(module => modulesToLoad.add(module));
        }

        this.log('Loading voice features:', Array.from(modulesToLoad));

        // Load modules in parallel
        const loadPromises = Array.from(modulesToLoad).map(module =>
            this.loadModule(module).catch(error => {
                this.log(`Failed to load ${module}:`, error);
                return null; // Don't fail entire load for one module
            })
        );

        const results = await Promise.allSettled(loadPromises);
        const successful = results.filter(r => r.status === 'fulfilled' && r.value).length;
        const failed = results.length - successful;

        this.log(`Voice features loaded: ${successful} successful, ${failed} failed`);

        // Emit completion event
        this.emitEvent('featuresLoaded', {
            requested: features,
            successful,
            failed,
            loadedModules: Array.from(this.loadedModules)
        });

        return {
            successful,
            failed,
            loadedModules: Array.from(this.loadedModules)
        };
    }

    /**
     * Check if voice features are available
     */
    areVoiceFeaturesLoaded() {
        const coreModules = ['voice-capabilities', 'voice-settings', 'voice-controller'];
        return coreModules.every(module => this.loadedModules.has(module));
    }

    /**
     * Get loading statistics
     */
    getLoadingStats() {
        return {
            totalModules: this.modules.size,
            loadedModules: this.loadedModules.size,
            failedModules: this.failedModules.size,
            cacheHits: this.cacheHits,
            cacheMisses: this.cacheMisses,
            averageLoadTime: this.getAverageLoadTime(),
            loadTimes: Object.fromEntries(this.loadTimes)
        };
    }

    /**
     * Get average load time
     */
    getAverageLoadTime() {
        if (this.loadTimes.size === 0) return 0;
        const total = Array.from(this.loadTimes.values()).reduce((sum, time) => sum + time, 0);
        return total / this.loadTimes.size;
    }

    /**
     * Clear cache
     */
    async clearCache() {
        try {
            if (this.cacheAPI) {
                await caches.delete(this.cacheName);
            } else if (this.memoryCache) {
                this.memoryCache.clear();
            }
            this.log('Cache cleared');
        } catch (error) {
            this.log('Failed to clear cache:', error);
        }
    }

    /**
     * Emit custom events
     */
    emitEvent(eventName, data) {
        try {
            const event = new CustomEvent(`voiceLoader:${eventName}`, {
                detail: data
            });
            window.dispatchEvent(event);
        } catch (error) {
            this.log('Failed to emit event:', error);
        }
    }

    /**
     * Log messages with debug mode check
     */
    log(message, ...args) {
        if (this.options.debugMode) {
            console.log(`[VoiceLoader] ${message}`, ...args);
        }
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.loadingPromises.clear();
        if (this.memoryCache) {
            this.memoryCache.clear();
        }
        this.log('VoiceModuleLoader cleaned up');
    }
}

// Global loader instance
let voiceLoader = null;

/**
 * Initialize voice module loader
 */
function initializeVoiceLoader(options = {}) {
    if (!voiceLoader) {
        voiceLoader = new VoiceModuleLoader(options);
        voiceLoader.registerModules();
    }
    return voiceLoader;
}

/**
 * Load voice features on demand
 */
async function loadVoiceFeatures(features = [], options = {}) {
    const loader = initializeVoiceLoader(options);

    // Preload critical modules first if not already done
    if (!loader.areVoiceFeaturesLoaded()) {
        await loader.preloadCriticalModules();
    }

    return await loader.loadVoiceFeatures(features);
}

/**
 * Check if voice features are ready
 */
function areVoiceFeaturesReady() {
    return voiceLoader ? voiceLoader.areVoiceFeaturesLoaded() : false;
}

/**
 * Get voice loader statistics
 */
function getVoiceLoaderStats() {
    return voiceLoader ? voiceLoader.getLoadingStats() : null;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        VoiceModuleLoader,
        initializeVoiceLoader,
        loadVoiceFeatures,
        areVoiceFeaturesReady,
        getVoiceLoaderStats
    };
}