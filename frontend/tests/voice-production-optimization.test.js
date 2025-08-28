/**
 * Voice Production Optimization Tests
 * Tests for lazy loading, performance monitoring, feature toggles, and resource management
 */

describe('Voice Production Optimization', () => {
    let mockVoiceLoader;
    let mockPerformanceMonitor;
    let mockFeatureToggleManager;
    let mockRedis;

    beforeEach(() => {
        // Reset DOM
        document.body.innerHTML = '';
        
        // Mock performance API
        global.performance = {
            now: jest.fn(() => Date.now()),
            mark: jest.fn(),
            measure: jest.fn(),
            memory: {
                usedJSHeapSize: 50 * 1024 * 1024, // 50MB
                totalJSHeapSize: 100 * 1024 * 1024, // 100MB
                jsHeapSizeLimit: 2 * 1024 * 1024 * 1024 // 2GB
            }
        };

        // Mock fetch
        global.fetch = jest.fn();

        // Mock localStorage
        global.localStorage = {
            getItem: jest.fn(),
            setItem: jest.fn(),
            removeItem: jest.fn()
        };

        // Mock Redis client
        mockRedis = {
            get: jest.fn(),
            set: jest.fn(),
            setex: jest.fn(),
            incr: jest.fn(),
            expire: jest.fn(),
            keys: jest.fn(),
            delete: jest.fn(),
            ping: jest.fn(),
            pipeline: jest.fn(() => ({
                zremrangebyscore: jest.fn(),
                zcard: jest.fn(),
                zadd: jest.fn(),
                expire: jest.fn(),
                execute: jest.fn(() => Promise.resolve([null, 5, null, null]))
            }))
        };
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('Voice Module Lazy Loading', () => {
        beforeEach(() => {
            // Load the voice loader module
            require('../voice-loader.js');
            mockVoiceLoader = new VoiceModuleLoader({
                debugMode: true,
                enableCaching: true
            });
        });

        test('should register voice modules correctly', () => {
            mockVoiceLoader.registerModules();
            
            expect(mockVoiceLoader.modules.size).toBeGreaterThan(0);
            expect(mockVoiceLoader.modules.has('voice-capabilities')).toBe(true);
            expect(mockVoiceLoader.modules.has('voice-controller')).toBe(true);
            expect(mockVoiceLoader.modules.has('voice-ui')).toBe(true);
        });

        test('should preload critical modules', async () => {
            mockVoiceLoader.registerModules();
            
            // Mock fetch for module loading
            global.fetch.mockResolvedValue({
                ok: true,
                text: () => Promise.resolve('console.log("module loaded");')
            });

            await mockVoiceLoader.preloadCriticalModules();
            
            expect(global.fetch).toHaveBeenCalled();
        });

        test('should load modules with dependencies in correct order', async () => {
            mockVoiceLoader.registerModules();
            
            global.fetch.mockResolvedValue({
                ok: true,
                text: () => Promise.resolve('console.log("module loaded");')
            });

            await mockVoiceLoader.loadModule('voice-ui');
            
            // Should load dependencies first
            expect(mockVoiceLoader.loadedModules.has('voice-controller')).toBe(true);
        });

        test('should cache loaded modules', async () => {
            mockVoiceLoader.registerModules();
            
            global.fetch.mockResolvedValue({
                ok: true,
                text: () => Promise.resolve('console.log("module loaded");')
            });

            // Load module twice
            await mockVoiceLoader.loadModule('voice-capabilities');
            await mockVoiceLoader.loadModule('voice-capabilities');
            
            // Should only fetch once due to caching
            expect(global.fetch).toHaveBeenCalledTimes(1);
        });

        test('should handle module loading failures gracefully', async () => {
            mockVoiceLoader.registerModules();
            
            global.fetch.mockRejectedValue(new Error('Network error'));

            await expect(mockVoiceLoader.loadModule('voice-capabilities')).rejects.toThrow();
            expect(mockVoiceLoader.failedModules.has('voice-capabilities')).toBe(true);
        });

        test('should retry failed module loads', async () => {
            mockVoiceLoader.registerModules();
            
            global.fetch
                .mockRejectedValueOnce(new Error('Network error'))
                .mockResolvedValue({
                    ok: true,
                    text: () => Promise.resolve('console.log("module loaded");')
                });

            await mockVoiceLoader.loadModule('voice-capabilities');
            
            expect(global.fetch).toHaveBeenCalledTimes(2);
        });

        test('should provide loading statistics', async () => {
            mockVoiceLoader.registerModules();
            
            global.fetch.mockResolvedValue({
                ok: true,
                text: () => Promise.resolve('console.log("module loaded");')
            });

            await mockVoiceLoader.loadModule('voice-capabilities');
            
            const stats = mockVoiceLoader.getLoadingStats();
            expect(stats.totalModules).toBeGreaterThan(0);
            expect(stats.loadedModules).toBe(1);
            expect(stats.averageLoadTime).toBeGreaterThan(0);
        });
    });

    describe('Voice Performance Monitor', () => {
        beforeEach(() => {
            require('../voice-performance-monitor.js');
            mockPerformanceMonitor = new VoicePerformanceMonitor({
                debugMode: true,
                maxConcurrentSessions: 5,
                memoryLimitMB: 50
            });
        });

        test('should check operation allowance based on limits', async () => {
            const allowed = await mockPerformanceMonitor.checkOperationAllowed('stt', 'user123');
            expect(allowed).toBe(true);
        });

        test('should deny operations when limits exceeded', async () => {
            // Simulate max sessions reached
            for (let i = 0; i < 6; i++) {
                mockPerformanceMonitor.startSession(`session${i}`, 'stt');
            }
            
            const allowed = await mockPerformanceMonitor.checkOperationAllowed('stt', 'user123');
            expect(allowed).toBe(false);
        });

        test('should track session lifecycle', () => {
            const sessionId = 'test-session';
            const session = mockPerformanceMonitor.startSession(sessionId, 'stt');
            
            expect(session.id).toBe(sessionId);
            expect(mockPerformanceMonitor.activeSessions.has(sessionId)).toBe(true);
            expect(mockPerformanceMonitor.metrics.sessionCount).toBe(1);
            
            mockPerformanceMonitor.endSession(sessionId);
            
            expect(mockPerformanceMonitor.activeSessions.has(sessionId)).toBe(false);
            expect(mockPerformanceMonitor.metrics.sessionCount).toBe(0);
        });

        test('should record performance metrics', () => {
            const sessionId = 'test-session';
            mockPerformanceMonitor.startSession(sessionId, 'stt');
            
            // Simulate some processing time
            setTimeout(() => {
                mockPerformanceMonitor.endSession(sessionId);
            }, 100);
            
            expect(mockPerformanceMonitor.metrics.sttProcessingTimes.length).toBe(1);
        });

        test('should record and categorize errors', () => {
            mockPerformanceMonitor.recordError('network_error', 'Connection failed');
            
            expect(mockPerformanceMonitor.metrics.errorCounts.get('network_error')).toBe(1);
        });

        test('should provide comprehensive metrics', () => {
            const sessionId = 'test-session';
            mockPerformanceMonitor.startSession(sessionId, 'stt');
            mockPerformanceMonitor.recordError('test_error', 'Test error');
            
            const metrics = mockPerformanceMonitor.getMetrics();
            
            expect(metrics.sessions.active).toBe(1);
            expect(metrics.errors.test_error).toBe(1);
            expect(metrics.performance).toBeDefined();
            expect(metrics.resources).toBeDefined();
        });

        test('should clean up stale resources', () => {
            const sessionId = 'stale-session';
            const session = mockPerformanceMonitor.startSession(sessionId, 'stt');
            
            // Mock stale session (older than threshold)
            session.startTime = performance.now() - 120000; // 2 minutes ago
            
            mockPerformanceMonitor.cleanupStaleResources();
            
            expect(mockPerformanceMonitor.activeSessions.has(sessionId)).toBe(false);
        });
    });

    describe('Voice Feature Toggle Manager', () => {
        beforeEach(() => {
            require('../voice-feature-toggles.js');
            mockFeatureToggleManager = new VoiceFeatureToggleManager({
                userId: 'test-user',
                debugMode: true,
                enableRemoteConfig: false
            });
        });

        test('should initialize with default toggles', () => {
            expect(mockFeatureToggleManager.toggles.size).toBeGreaterThan(0);
            expect(mockFeatureToggleManager.isFeatureEnabled('voice_input')).toBe(true);
            expect(mockFeatureToggleManager.isFeatureEnabled('voice_output')).toBe(true);
        });

        test('should respect rollout percentages', () => {
            // Set a feature to 0% rollout
            mockFeatureToggleManager.toggles.set('test_feature', {
                enabled: true,
                rolloutPercentage: 0,
                userGroups: [],
                conditions: {},
                metadata: {}
            });
            
            expect(mockFeatureToggleManager.isFeatureEnabled('test_feature')).toBe(false);
        });

        test('should handle user group restrictions', () => {
            mockFeatureToggleManager.userGroups.add('beta_testers');
            
            mockFeatureToggleManager.toggles.set('beta_feature', {
                enabled: true,
                rolloutPercentage: 100,
                userGroups: ['beta_testers'],
                conditions: {},
                metadata: {}
            });
            
            expect(mockFeatureToggleManager.isFeatureEnabled('beta_feature')).toBe(true);
            
            // Remove user from group
            mockFeatureToggleManager.userGroups.clear();
            expect(mockFeatureToggleManager.isFeatureEnabled('beta_feature')).toBe(false);
        });

        test('should evaluate conditions correctly', () => {
            const conditions = {
                browsers: ['chrome'],
                platforms: ['desktop']
            };
            
            // Mock navigator
            Object.defineProperty(navigator, 'userAgent', {
                value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                configurable: true
            });
            
            Object.defineProperty(navigator, 'platform', {
                value: 'Win32',
                configurable: true
            });
            
            const result = mockFeatureToggleManager.evaluateConditions(conditions, {});
            expect(result).toBe(true);
        });

        test('should configure and assign A/B test variants', () => {
            mockFeatureToggleManager.configureABTest('ui_test', {
                variants: ['A', 'B'],
                percentage: 100,
                conditions: {}
            });
            
            const variant = mockFeatureToggleManager.getABTestVariant('ui_test');
            expect(['A', 'B']).toContain(variant);
        });

        test('should handle local overrides', () => {
            const success = mockFeatureToggleManager.overrideFeature('test_feature', false);
            expect(success).toBe(true);
            expect(mockFeatureToggleManager.isFeatureEnabled('test_feature')).toBe(false);
        });

        test('should provide all feature states', () => {
            const states = mockFeatureToggleManager.getAllFeatureStates();
            expect(Object.keys(states).length).toBeGreaterThan(0);
            expect(states.voice_input).toBeDefined();
            expect(states.voice_input.enabled).toBeDefined();
            expect(states.voice_input.config).toBeDefined();
        });

        test('should emit events on configuration changes', (done) => {
            mockFeatureToggleManager.addEventListener('configUpdated', (data) => {
                expect(data.config).toBeDefined();
                done();
            });
            
            mockFeatureToggleManager.processRemoteConfig({
                featureToggles: { voice_input: false }
            });
        });
    });

    describe('Voice Rate Limiter', () => {
        let rateLimiter;

        beforeEach(() => {
            require('../voice-performance-monitor.js');
            rateLimiter = new VoiceRateLimiter({
                requestsPerMinute: 10,
                requestsPerHour: 100,
                burstLimit: 3,
                enabled: true
            });
        });

        test('should allow requests within limits', async () => {
            const allowed = await rateLimiter.checkLimit('stt', 'user123');
            expect(allowed).toBe(true);
        });

        test('should deny requests exceeding burst limit', async () => {
            // Make requests up to burst limit
            for (let i = 0; i < 3; i++) {
                await rateLimiter.checkLimit('stt', 'user123');
            }
            
            // Next request should be denied
            const allowed = await rateLimiter.checkLimit('stt', 'user123');
            expect(allowed).toBe(false);
        });

        test('should track different operation types separately', async () => {
            // Use up burst limit for STT
            for (let i = 0; i < 3; i++) {
                await rateLimiter.checkLimit('stt', 'user123');
            }
            
            // TTS should still be allowed
            const allowed = await rateLimiter.checkLimit('tts', 'user123');
            expect(allowed).toBe(true);
        });

        test('should provide current limits', () => {
            const limits = rateLimiter.getCurrentLimits();
            expect(limits.requestsPerMinute).toBe(10);
            expect(limits.requestsPerHour).toBe(100);
            expect(limits.burstLimit).toBe(3);
            expect(limits.enabled).toBe(true);
        });
    });

    describe('Voice Memory Monitor', () => {
        let memoryMonitor;

        beforeEach(() => {
            require('../voice-performance-monitor.js');
            memoryMonitor = new VoiceMemoryMonitor({
                limitMB: 50,
                checkInterval: 1000,
                enableCleanup: true
            });
        });

        test('should check memory availability', () => {
            const available = memoryMonitor.isMemoryAvailable();
            expect(typeof available).toBe('boolean');
        });

        test('should provide usage statistics', () => {
            memoryMonitor.checkMemoryUsage();
            const stats = memoryMonitor.getUsageStats();
            
            if (stats) {
                expect(stats.current).toBeDefined();
                expect(stats.limit).toBe(50);
                expect(stats.utilizationPercent).toBeDefined();
            }
        });

        test('should generate warnings for high usage', () => {
            // Mock high memory usage
            global.performance.memory.usedJSHeapSize = 90 * 1024 * 1024; // 90MB
            
            memoryMonitor.checkMemoryUsage();
            const warnings = memoryMonitor.getWarnings();
            
            expect(warnings.length).toBeGreaterThan(0);
            expect(warnings.some(w => w.includes('high') || w.includes('critical'))).toBe(true);
        });

        test('should start and stop monitoring', () => {
            memoryMonitor.start();
            expect(memoryMonitor.intervalId).toBeDefined();
            
            memoryMonitor.stop();
            expect(memoryMonitor.intervalId).toBeNull();
        });
    });

    describe('Integration Tests', () => {
        test('should integrate performance monitor with feature toggles', async () => {
            require('../voice-performance-monitor.js');
            require('../voice-feature-toggles.js');
            
            const performanceMonitor = new VoicePerformanceMonitor({
                debugMode: true,
                enableRateLimit: true
            });
            
            const toggleManager = new VoiceFeatureToggleManager({
                userId: 'test-user',
                debugMode: true
            });
            
            // Performance monitor should respect feature toggles
            const rateLimitEnabled = toggleManager.isFeatureEnabled('rate_limiting');
            expect(performanceMonitor.options.enableRateLimit).toBe(rateLimitEnabled);
        });

        test('should handle resource cleanup on page unload', () => {
            require('../voice-performance-monitor.js');
            
            const performanceMonitor = new VoicePerformanceMonitor({
                debugMode: true
            });
            
            const sessionId = 'test-session';
            performanceMonitor.startSession(sessionId, 'stt');
            
            // Simulate page unload
            const beforeUnloadEvent = new Event('beforeunload');
            window.dispatchEvent(beforeUnloadEvent);
            
            // Should clean up resources
            expect(performanceMonitor.activeSessions.size).toBe(0);
        });

        test('should adapt to system performance', async () => {
            require('../voice-performance-monitor.js');
            
            const performanceMonitor = new VoicePerformanceMonitor({
                debugMode: true,
                maxConcurrentSessions: 2
            });
            
            // Start sessions up to limit
            performanceMonitor.startSession('session1', 'stt');
            performanceMonitor.startSession('session2', 'stt');
            
            // Should deny new sessions
            const allowed = await performanceMonitor.checkOperationAllowed('stt', 'user123');
            expect(allowed).toBe(false);
        });
    });
});

// Test utilities
function createMockAudioContext() {
    return {
        state: 'running',
        close: jest.fn(),
        createMediaStreamSource: jest.fn(),
        createAnalyser: jest.fn(),
        createGain: jest.fn()
    };
}

function createMockSpeechRecognition() {
    return {
        start: jest.fn(),
        stop: jest.fn(),
        abort: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
    };
}

function createMockSpeechSynthesis() {
    return {
        speak: jest.fn(),
        cancel: jest.fn(),
        pause: jest.fn(),
        resume: jest.fn(),
        getVoices: jest.fn(() => []),
        speaking: false,
        paused: false
    };
}