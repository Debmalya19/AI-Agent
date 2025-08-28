/**
 * Test suite for Voice Analytics Client
 * Tests client-side performance tracking and analytics functionality
 */

// Mock fetch for testing
global.fetch = jest.fn();
global.navigator = {
    sendBeacon: jest.fn(),
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    platform: 'Win32',
    language: 'en-US',
    cookieEnabled: true,
    onLine: true
};
global.screen = { width: 1920, height: 1080 };
global.performance = { now: jest.fn(() => 1000) };

// Import the class to test
const VoiceAnalytics = require('../voice-analytics.js');

describe('VoiceAnalytics', () => {
    let analytics;
    let mockFetch;

    beforeEach(() => {
        // Reset mocks
        jest.clearAllMocks();
        mockFetch = global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ success: true })
        });

        // Create analytics instance
        analytics = new VoiceAnalytics({
            debugMode: true,
            flushInterval: 1000, // Short interval for testing
            batchSize: 3 // Small batch size for testing
        });

        // Mock timers
        jest.useFakeTimers();
    });

    afterEach(() => {
        if (analytics) {
            analytics.destroy();
        }
        jest.useRealTimers();
    });

    describe('Initialization', () => {
        test('should initialize with default options', () => {
            const defaultAnalytics = new VoiceAnalytics();
            
            expect(defaultAnalytics.options.enablePerformanceTracking).toBe(true);
            expect(defaultAnalytics.options.enableErrorTracking).toBe(true);
            expect(defaultAnalytics.options.enableUsageTracking).toBe(true);
            expect(defaultAnalytics.sessionMetrics.sessionId).toBeDefined();
            
            defaultAnalytics.destroy();
        });

        test('should generate unique session ID', () => {
            const analytics1 = new VoiceAnalytics();
            const analytics2 = new VoiceAnalytics();
            
            expect(analytics1.sessionMetrics.sessionId).not.toBe(analytics2.sessionMetrics.sessionId);
            
            analytics1.destroy();
            analytics2.destroy();
        });
    });

    describe('Performance Tracking', () => {
        test('should start and stop performance timer', () => {
            const timerId = analytics.startPerformanceTimer('stt_start', {
                language: 'en-US'
            });
            
            expect(timerId).toBeDefined();
            expect(analytics.performanceTimers.has(timerId)).toBe(true);
            
            // Advance time
            performance.now.mockReturnValue(2500);
            
            analytics.stopPerformanceTimer(timerId, {
                textLength: 25,
                accuracyScore: 0.95
            });
            
            expect(analytics.performanceTimers.has(timerId)).toBe(false);
            expect(analytics.performanceBuffer.length).toBe(1);
            
            const performanceData = analytics.performanceBuffer[0];
            expect(performanceData.operationType).toBe('stt_start');
            expect(performanceData.duration).toBe(1500); // 2500 - 1000
            expect(performanceData.textLength).toBe(25);
            expect(performanceData.accuracyScore).toBe(0.95);
        });

        test('should handle invalid timer ID gracefully', () => {
            analytics.stopPerformanceTimer('invalid_timer_id');
            expect(analytics.performanceBuffer.length).toBe(0);
        });

        test('should update session metrics on performance tracking', () => {
            const timerId = analytics.startPerformanceTimer('stt_start');
            performance.now.mockReturnValue(2000);
            
            analytics.stopPerformanceTimer(timerId, { textLength: 20 });
            
            expect(analytics.sessionMetrics.voiceInteractions).toBe(1);
            expect(analytics.sessionMetrics.sttUsage).toBe(1);
            expect(analytics.sessionMetrics.totalProcessingTime).toBe(1000);
        });
    });

    describe('Error Tracking', () => {
        test('should record voice errors', () => {
            analytics.recordVoiceError(
                'network',
                'Connection timeout',
                { browser: 'Chrome' },
                'retry_with_delay'
            );
            
            expect(analytics.errorBuffer.length).toBe(1);
            expect(analytics.sessionMetrics.errors).toBe(1);
            expect(analytics.consecutiveErrors).toBe(1);
            
            const errorData = analytics.errorBuffer[0];
            expect(errorData.errorType).toBe('network');
            expect(errorData.errorMessage).toBe('Connection timeout');
            expect(errorData.recoveryAction).toBe('retry_with_delay');
            expect(errorData.consecutiveErrors).toBe(1);
        });

        test('should track error patterns', () => {
            analytics.recordVoiceError('network', 'Connection failed');
            analytics.recordVoiceError('network', 'Network timeout');
            analytics.recordVoiceError('permission', 'Microphone denied');
            
            const patterns = analytics.getErrorPatterns();
            expect(patterns['network:network']).toBeDefined();
            expect(patterns['network:network'].count).toBe(2);
            expect(patterns['permission:permission']).toBeDefined();
            expect(patterns['permission:permission'].count).toBe(1);
        });

        test('should categorize errors correctly', () => {
            const testCases = [
                ['Network connection failed', 'network'],
                ['Microphone permission denied', 'permission'],
                ['Audio capture error', 'audio'],
                ['Speech synthesis failed', 'synthesis'],
                ['Recognition error', 'recognition'],
                ['Unknown error', 'other']
            ];
            
            testCases.forEach(([message, expectedCategory]) => {
                const category = analytics.categorizeError(message);
                expect(category).toBe(expectedCategory);
            });
        });

        test('should sanitize error messages', () => {
            const sensitiveMessage = 'Error with token=abc123 and key=secret456';
            const sanitized = analytics.sanitizeErrorMessage(sensitiveMessage);
            
            expect(sanitized).not.toContain('abc123');
            expect(sanitized).not.toContain('secret456');
            expect(sanitized).toContain('token=***');
            expect(sanitized).toContain('key=***');
        });
    });

    describe('Feature Adoption Tracking', () => {
        test('should record feature adoption', () => {
            analytics.recordFeatureAdoption('voiceInput', true, {
                language: 'en-US',
                sensitivity: 0.7
            });
            
            expect(analytics.usageBuffer.length).toBe(1);
            expect(analytics.featureUsage.voiceInput).toBe(true);
            
            const adoptionData = analytics.usageBuffer[0];
            expect(adoptionData.featureType).toBe('voiceInput');
            expect(adoptionData.enabled).toBe(true);
            expect(adoptionData.settings.language).toBe('en-US');
        });

        test('should record voice in chat usage', () => {
            analytics.recordVoiceInChat('chat_session_123', {
                totalTime: 5000,
                interactions: 3
            });
            
            expect(analytics.usageBuffer.length).toBe(1);
            
            const chatData = analytics.usageBuffer[0];
            expect(chatData.type).toBe('voice_in_chat');
            expect(chatData.chatSessionId).toBe('chat_session_123');
            expect(chatData.voiceMetrics.totalTime).toBe(5000);
        });
    });

    describe('Data Sanitization', () => {
        test('should sanitize context data', () => {
            const sensitiveContext = {
                browser: 'Chrome',
                audio_data: 'sensitive_audio',
                raw_audio: new ArrayBuffer(1024),
                settings: {
                    volume: 0.8,
                    microphone_data: 'sensitive_mic_data'
                }
            };
            
            const sanitized = analytics.sanitizeContext(sensitiveContext);
            
            expect(sanitized.browser).toBe('Chrome');
            expect(sanitized.settings.volume).toBe(0.8);
            expect(sanitized.audio_data).toBeUndefined();
            expect(sanitized.raw_audio).toBeUndefined();
            expect(sanitized.settings.microphone_data).toBeUndefined();
        });
    });

    describe('Session Management', () => {
        test('should provide session summary', () => {
            // Add some test data
            analytics.recordVoiceError('network', 'Test error');
            analytics.recordFeatureAdoption('voiceInput', true);
            
            const summary = analytics.getSessionSummary();
            
            expect(summary.sessionId).toBeDefined();
            expect(summary.sessionDuration).toBeGreaterThan(0);
            expect(summary.errors).toBe(1);
            expect(summary.featureUsage.voiceInput).toBe(true);
            expect(summary.bufferedEvents).toBe(2);
        });

        test('should reset session correctly', () => {
            // Add some data
            analytics.recordVoiceError('test', 'error');
            analytics.consecutiveErrors = 5;
            
            const oldSessionId = analytics.sessionMetrics.sessionId;
            analytics.resetSession();
            
            expect(analytics.sessionMetrics.sessionId).not.toBe(oldSessionId);
            expect(analytics.consecutiveErrors).toBe(0);
            expect(analytics.errorPatterns.size).toBe(0);
        });
    });

    describe('Data Flushing', () => {
        test('should flush data when batch size is reached', () => {
            // Add data to reach batch size (3)
            analytics.recordVoiceError('test1', 'error1');
            analytics.recordVoiceError('test2', 'error2');
            analytics.recordFeatureAdoption('voiceInput', true);
            
            // Should trigger flush automatically
            expect(mockFetch).toHaveBeenCalledWith('/voice/analytics/batch', expect.objectContaining({
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            }));
        });

        test('should flush data on interval', async () => {
            analytics.recordVoiceError('test', 'error');
            
            // Advance timer to trigger interval flush
            jest.advanceTimersByTime(1000);
            
            // Wait for async flush
            await Promise.resolve();
            
            expect(mockFetch).toHaveBeenCalled();
        });

        test('should handle flush errors gracefully', async () => {
            mockFetch.mockRejectedValue(new Error('Network error'));
            
            analytics.recordVoiceError('test1', 'error1');
            analytics.recordVoiceError('test2', 'error2');
            analytics.recordFeatureAdoption('voiceInput', true);
            
            // Should not throw error
            await expect(analytics.flushAnalytics()).resolves.not.toThrow();
        });

        test('should use sendBeacon for synchronous flush', () => {
            analytics.recordVoiceError('test', 'error');
            
            analytics.flushAnalytics(true);
            
            expect(navigator.sendBeacon).toHaveBeenCalledWith(
                '/voice/analytics/batch',
                expect.any(Blob)
            );
        });
    });

    describe('Browser Context', () => {
        test('should get browser context information', () => {
            const context = analytics.getBrowserContext();
            
            expect(context.browser).toBeDefined();
            expect(context.platform).toBe('Win32');
            expect(context.language).toBe('en-US');
            expect(context.screenResolution).toBe('1920x1080');
            expect(context.timestamp).toBeDefined();
        });

        test('should detect browser name correctly', () => {
            const testCases = [
                ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36', 'Chrome'],
                ['Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0', 'Firefox'],
                ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15', 'Safari'],
                ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59', 'Edge']
            ];
            
            testCases.forEach(([userAgent, expectedBrowser]) => {
                // Temporarily change user agent
                const originalUA = navigator.userAgent;
                Object.defineProperty(navigator, 'userAgent', {
                    value: userAgent,
                    configurable: true
                });
                
                const browserName = analytics.getBrowserName();
                expect(browserName).toBe(expectedBrowser);
                
                // Restore original user agent
                Object.defineProperty(navigator, 'userAgent', {
                    value: originalUA,
                    configurable: true
                });
            });
        });
    });

    describe('Retry Logic', () => {
        test('should retry failed requests', async () => {
            // First call fails, second succeeds
            mockFetch
                .mockRejectedValueOnce(new Error('Network error'))
                .mockResolvedValueOnce({
                    ok: true,
                    json: () => Promise.resolve({ success: true })
                });
            
            const payload = { test: 'data' };
            
            // Should not throw error and should retry
            await expect(analytics.sendAnalyticsData(payload)).resolves.not.toThrow();
            
            expect(mockFetch).toHaveBeenCalledTimes(2);
        });

        test('should give up after max retries', async () => {
            mockFetch.mockRejectedValue(new Error('Persistent error'));
            
            const payload = { test: 'data' };
            
            await expect(analytics.sendAnalyticsData(payload)).rejects.toThrow('Persistent error');
            
            expect(mockFetch).toHaveBeenCalledTimes(4); // Initial + 3 retries
        });
    });

    describe('Cleanup', () => {
        test('should clean up resources on destroy', () => {
            const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
            
            analytics.destroy();
            
            expect(clearIntervalSpy).toHaveBeenCalled();
            expect(analytics.performanceBuffer.length).toBe(0);
            expect(analytics.errorBuffer.length).toBe(0);
            expect(analytics.usageBuffer.length).toBe(0);
            expect(analytics.performanceTimers.size).toBe(0);
        });
    });
});

describe('VoiceAnalytics Integration', () => {
    test('should integrate with voice controller', () => {
        const analytics = new VoiceAnalytics({ debugMode: true });
        
        // Simulate voice controller usage
        const timerId = analytics.startPerformanceTimer('stt_start');
        performance.now.mockReturnValue(2000);
        analytics.stopPerformanceTimer(timerId, { textLength: 30, accuracyScore: 0.9 });
        
        analytics.recordFeatureAdoption('voiceInput', true);
        analytics.recordVoiceInChat('chat_123', { interactions: 1 });
        
        const summary = analytics.getSessionSummary();
        expect(summary.voiceInteractions).toBe(1);
        expect(summary.sttUsage).toBe(1);
        expect(summary.featureUsage.voiceInput).toBe(true);
        
        analytics.destroy();
    });
});