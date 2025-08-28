/**
 * Voice Performance Monitor and Resource Manager
 * Monitors voice feature performance, manages resources, and implements rate limiting
 */

class VoicePerformanceMonitor {
    constructor(options = {}) {
        this.options = {
            maxConcurrentSessions: options.maxConcurrentSessions || 5,
            memoryLimitMB: options.memoryLimitMB || 50,
            maxRecordingDuration: options.maxRecordingDuration || 30000,
            maxTTSTextLength: options.maxTTSTextLength || 5000,
            performanceReportInterval: options.performanceReportInterval || 60000,
            enableResourceCleanup: options.enableResourceCleanup !== false,
            enableRateLimit: options.enableRateLimit !== false,
            debugMode: options.debugMode || false,
            ...options
        };

        // Performance tracking
        this.metrics = {
            sttProcessingTimes: [],
            ttsProcessingTimes: [],
            memoryUsage: [],
            errorCounts: new Map(),
            sessionCount: 0,
            totalRequests: 0,
            rateLimitHits: 0,
            resourceCleanups: 0
        };

        // Resource management
        this.activeSessions = new Map();
        this.audioContexts = new Set();
        this.speechSynthesisUtterances = new Set();
        this.recognitionInstances = new Set();

        // Rate limiting
        this.rateLimiter = new VoiceRateLimiter({
            requestsPerMinute: options.requestsPerMinute || 60,
            requestsPerHour: options.requestsPerHour || 1000,
            burstLimit: options.burstLimit || 10,
            enabled: this.options.enableRateLimit
        });

        // Memory monitor
        this.memoryMonitor = new VoiceMemoryMonitor({
            limitMB: this.options.memoryLimitMB,
            checkInterval: 30000,
            enableCleanup: this.options.enableResourceCleanup
        });

        // Performance reporting
        this.performanceReporter = new VoicePerformanceReporter({
            reportInterval: this.options.performanceReportInterval,
            enableReporting: options.enableReporting !== false
        });

        this.initialize();
    }

    /**
     * Initialize performance monitoring
     */
    initialize() {
        this.log('Initializing voice performance monitor');

        // Start memory monitoring
        this.memoryMonitor.start();

        // Start performance reporting
        this.performanceReporter.start();

        // Set up cleanup intervals
        if (this.options.enableResourceCleanup) {
            this.setupResourceCleanup();
        }

        // Monitor page visibility for resource management
        this.setupVisibilityHandling();

        this.log('Voice performance monitor initialized');
    }

    /**
     * Check if voice operation is allowed based on rate limits and resources
     * @param {string} operationType - Type of operation (stt, tts, etc.)
     * @param {string} userId - User identifier
     * @returns {Promise<boolean>} Whether operation is allowed
     */
    async checkOperationAllowed(operationType, userId = 'anonymous') {
        try {
            // Check rate limits
            if (!await this.rateLimiter.checkLimit(operationType, userId)) {
                this.metrics.rateLimitHits++;
                this.log(`Rate limit exceeded for ${operationType} by user ${userId}`);
                return false;
            }

            // Check concurrent sessions
            if (this.metrics.sessionCount >= this.options.maxConcurrentSessions) {
                this.log(`Max concurrent sessions reached: ${this.metrics.sessionCount}`);
                return false;
            }

            // Check memory usage
            if (!this.memoryMonitor.isMemoryAvailable()) {
                this.log('Memory limit reached, denying operation');
                return false;
            }

            // Check specific operation limits
            if (operationType === 'stt' && this.recognitionInstances.size >= 3) {
                this.log('Max speech recognition instances reached');
                return false;
            }

            if (operationType === 'tts' && this.speechSynthesisUtterances.size >= 5) {
                this.log('Max TTS utterances reached');
                return false;
            }

            return true;

        } catch (error) {
            this.log('Error checking operation allowance:', error);
            return false;
        }
    }

    /**
     * Start monitoring a voice session
     * @param {string} sessionId - Session identifier
     * @param {string} operationType - Type of operation
     * @param {Object} metadata - Additional session metadata
     */
    startSession(sessionId, operationType, metadata = {}) {
        const session = {
            id: sessionId,
            type: operationType,
            startTime: performance.now(),
            metadata,
            resources: new Set()
        };

        this.activeSessions.set(sessionId, session);
        this.metrics.sessionCount++;
        this.metrics.totalRequests++;

        this.log(`Started session ${sessionId} (${operationType})`);
        return session;
    }

    /**
     * End monitoring a voice session
     * @param {string} sessionId - Session identifier
     * @param {Object} result - Session result data
     */
    endSession(sessionId, result = {}) {
        const session = this.activeSessions.get(sessionId);
        if (!session) {
            this.log(`Session ${sessionId} not found`);
            return;
        }

        const duration = performance.now() - session.startTime;
        
        // Record performance metrics
        if (session.type === 'stt') {
            this.metrics.sttProcessingTimes.push(duration);
        } else if (session.type === 'tts') {
            this.metrics.ttsProcessingTimes.push(duration);
        }

        // Clean up session resources
        this.cleanupSessionResources(session);

        // Remove session
        this.activeSessions.delete(sessionId);
        this.metrics.sessionCount--;

        this.log(`Ended session ${sessionId} after ${duration.toFixed(2)}ms`);
    }

    /**
     * Register a resource for tracking
     * @param {string} sessionId - Session identifier
     * @param {string} resourceType - Type of resource
     * @param {Object} resource - Resource object
     */
    registerResource(sessionId, resourceType, resource) {
        const session = this.activeSessions.get(sessionId);
        if (session) {
            session.resources.add({ type: resourceType, resource });
        }

        // Track globally
        switch (resourceType) {
            case 'audioContext':
                this.audioContexts.add(resource);
                break;
            case 'speechSynthesis':
                this.speechSynthesisUtterances.add(resource);
                break;
            case 'speechRecognition':
                this.recognitionInstances.add(resource);
                break;
        }

        this.log(`Registered ${resourceType} for session ${sessionId}`);
    }

    /**
     * Record an error
     * @param {string} errorType - Type of error
     * @param {string} message - Error message
     * @param {Object} context - Error context
     */
    recordError(errorType, message, context = {}) {
        const count = this.metrics.errorCounts.get(errorType) || 0;
        this.metrics.errorCounts.set(errorType, count + 1);

        this.log(`Error recorded: ${errorType} - ${message}`, context);

        // Report critical errors immediately
        if (this.isCriticalError(errorType)) {
            this.performanceReporter.reportError(errorType, message, context);
        }
    }

    /**
     * Check if error is critical
     * @param {string} errorType - Error type
     * @returns {boolean} Whether error is critical
     */
    isCriticalError(errorType) {
        const criticalErrors = [
            'memory_exhausted',
            'rate_limit_exceeded',
            'resource_leak',
            'browser_crash'
        ];
        return criticalErrors.includes(errorType);
    }

    /**
     * Get current performance metrics
     * @returns {Object} Performance metrics
     */
    getMetrics() {
        return {
            sessions: {
                active: this.metrics.sessionCount,
                total: this.metrics.totalRequests
            },
            performance: {
                avgSTTTime: this.calculateAverage(this.metrics.sttProcessingTimes),
                avgTTSTime: this.calculateAverage(this.metrics.ttsProcessingTimes),
                p95STTTime: this.calculatePercentile(this.metrics.sttProcessingTimes, 95),
                p95TTSTime: this.calculatePercentile(this.metrics.ttsProcessingTimes, 95)
            },
            resources: {
                audioContexts: this.audioContexts.size,
                speechSynthesis: this.speechSynthesisUtterances.size,
                speechRecognition: this.recognitionInstances.size
            },
            errors: Object.fromEntries(this.metrics.errorCounts),
            rateLimiting: {
                hits: this.metrics.rateLimitHits,
                currentLimits: this.rateLimiter.getCurrentLimits()
            },
            memory: this.memoryMonitor.getUsageStats()
        };
    }

    /**
     * Calculate average of array
     * @param {number[]} values - Array of values
     * @returns {number} Average value
     */
    calculateAverage(values) {
        if (values.length === 0) return 0;
        return values.reduce((sum, val) => sum + val, 0) / values.length;
    }

    /**
     * Calculate percentile of array
     * @param {number[]} values - Array of values
     * @param {number} percentile - Percentile to calculate (0-100)
     * @returns {number} Percentile value
     */
    calculatePercentile(values, percentile) {
        if (values.length === 0) return 0;
        const sorted = [...values].sort((a, b) => a - b);
        const index = Math.ceil((percentile / 100) * sorted.length) - 1;
        return sorted[Math.max(0, index)];
    }

    /**
     * Clean up session resources
     * @param {Object} session - Session object
     */
    cleanupSessionResources(session) {
        session.resources.forEach(({ type, resource }) => {
            try {
                switch (type) {
                    case 'audioContext':
                        if (resource.state !== 'closed') {
                            resource.close();
                        }
                        this.audioContexts.delete(resource);
                        break;
                    case 'speechSynthesis':
                        speechSynthesis.cancel();
                        this.speechSynthesisUtterances.delete(resource);
                        break;
                    case 'speechRecognition':
                        resource.stop();
                        this.recognitionInstances.delete(resource);
                        break;
                }
            } catch (error) {
                this.log(`Error cleaning up ${type}:`, error);
            }
        });

        this.metrics.resourceCleanups++;
    }

    /**
     * Set up resource cleanup intervals
     */
    setupResourceCleanup() {
        // Clean up stale resources every 30 seconds
        setInterval(() => {
            this.cleanupStaleResources();
        }, 30000);

        // Deep cleanup every 5 minutes
        setInterval(() => {
            this.performDeepCleanup();
        }, 300000);
    }

    /**
     * Clean up stale resources
     */
    cleanupStaleResources() {
        const now = performance.now();
        const staleThreshold = 60000; // 1 minute

        // Clean up stale sessions
        for (const [sessionId, session] of this.activeSessions) {
            if (now - session.startTime > staleThreshold) {
                this.log(`Cleaning up stale session: ${sessionId}`);
                this.endSession(sessionId, { reason: 'stale_cleanup' });
            }
        }

        // Clean up orphaned audio contexts
        this.audioContexts.forEach(context => {
            if (context.state === 'closed') {
                this.audioContexts.delete(context);
            }
        });

        this.log('Stale resource cleanup completed');
    }

    /**
     * Perform deep cleanup
     */
    performDeepCleanup() {
        this.log('Performing deep cleanup');

        // Force garbage collection if available
        if (window.gc) {
            window.gc();
        }

        // Clear old metrics to prevent memory growth
        if (this.metrics.sttProcessingTimes.length > 1000) {
            this.metrics.sttProcessingTimes = this.metrics.sttProcessingTimes.slice(-500);
        }
        if (this.metrics.ttsProcessingTimes.length > 1000) {
            this.metrics.ttsProcessingTimes = this.metrics.ttsProcessingTimes.slice(-500);
        }

        // Clear old memory usage data
        this.memoryMonitor.clearOldData();

        this.log('Deep cleanup completed');
    }

    /**
     * Set up page visibility handling
     */
    setupVisibilityHandling() {
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.log('Page hidden, pausing voice operations');
                this.pauseAllOperations();
            } else {
                this.log('Page visible, resuming voice operations');
                this.resumeOperations();
            }
        });

        // Handle page unload
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }

    /**
     * Pause all voice operations
     */
    pauseAllOperations() {
        // Stop all speech synthesis
        if (speechSynthesis.speaking) {
            speechSynthesis.pause();
        }

        // Stop all speech recognition
        this.recognitionInstances.forEach(recognition => {
            try {
                recognition.stop();
            } catch (error) {
                this.log('Error stopping recognition:', error);
            }
        });
    }

    /**
     * Resume voice operations
     */
    resumeOperations() {
        // Resume speech synthesis if it was paused
        if (speechSynthesis.paused) {
            speechSynthesis.resume();
        }
    }

    /**
     * Get resource usage warnings
     * @returns {string[]} Array of warning messages
     */
    getResourceWarnings() {
        const warnings = [];

        if (this.metrics.sessionCount >= this.options.maxConcurrentSessions * 0.8) {
            warnings.push('Approaching maximum concurrent sessions');
        }

        if (this.audioContexts.size >= 5) {
            warnings.push('High number of audio contexts active');
        }

        if (this.metrics.rateLimitHits > 10) {
            warnings.push('Frequent rate limit hits detected');
        }

        const memoryWarnings = this.memoryMonitor.getWarnings();
        warnings.push(...memoryWarnings);

        return warnings;
    }

    /**
     * Cleanup all resources
     */
    cleanup() {
        this.log('Cleaning up voice performance monitor');

        // Stop all active sessions
        for (const sessionId of this.activeSessions.keys()) {
            this.endSession(sessionId, { reason: 'cleanup' });
        }

        // Clean up all resources
        this.audioContexts.forEach(context => {
            try {
                if (context.state !== 'closed') {
                    context.close();
                }
            } catch (error) {
                this.log('Error closing audio context:', error);
            }
        });

        this.recognitionInstances.forEach(recognition => {
            try {
                recognition.stop();
            } catch (error) {
                this.log('Error stopping recognition:', error);
            }
        });

        if (speechSynthesis.speaking) {
            speechSynthesis.cancel();
        }

        // Stop monitoring
        this.memoryMonitor.stop();
        this.performanceReporter.stop();

        this.log('Voice performance monitor cleanup completed');
    }

    /**
     * Log messages with debug mode check
     */
    log(message, ...args) {
        if (this.options.debugMode) {
            console.log(`[VoicePerformanceMonitor] ${message}`, ...args);
        }
    }
}

/**
 * Voice Rate Limiter
 */
class VoiceRateLimiter {
    constructor(options = {}) {
        this.options = {
            requestsPerMinute: options.requestsPerMinute || 60,
            requestsPerHour: options.requestsPerHour || 1000,
            burstLimit: options.burstLimit || 10,
            enabled: options.enabled !== false
        };

        this.requestCounts = new Map();
        this.burstCounts = new Map();
    }

    /**
     * Check if request is within rate limits
     * @param {string} operationType - Type of operation
     * @param {string} userId - User identifier
     * @returns {Promise<boolean>} Whether request is allowed
     */
    async checkLimit(operationType, userId) {
        if (!this.options.enabled) {
            return true;
        }

        const now = Date.now();
        const key = `${userId}:${operationType}`;

        // Check burst limit
        if (!this.checkBurstLimit(key, now)) {
            return false;
        }

        // Check minute limit
        if (!this.checkMinuteLimit(key, now)) {
            return false;
        }

        // Check hour limit
        if (!this.checkHourLimit(key, now)) {
            return false;
        }

        // Record the request
        this.recordRequest(key, now);
        return true;
    }

    /**
     * Check burst limit (requests in last 10 seconds)
     */
    checkBurstLimit(key, now) {
        const burstKey = `${key}:burst`;
        const requests = this.burstCounts.get(burstKey) || [];
        const recentRequests = requests.filter(time => now - time < 10000);
        
        this.burstCounts.set(burstKey, recentRequests);
        return recentRequests.length < this.options.burstLimit;
    }

    /**
     * Check minute limit
     */
    checkMinuteLimit(key, now) {
        const minuteKey = `${key}:minute`;
        const requests = this.requestCounts.get(minuteKey) || [];
        const recentRequests = requests.filter(time => now - time < 60000);
        
        this.requestCounts.set(minuteKey, recentRequests);
        return recentRequests.length < this.options.requestsPerMinute;
    }

    /**
     * Check hour limit
     */
    checkHourLimit(key, now) {
        const hourKey = `${key}:hour`;
        const requests = this.requestCounts.get(hourKey) || [];
        const recentRequests = requests.filter(time => now - time < 3600000);
        
        this.requestCounts.set(hourKey, recentRequests);
        return recentRequests.length < this.options.requestsPerHour;
    }

    /**
     * Record a request
     */
    recordRequest(key, now) {
        // Record for burst tracking
        const burstKey = `${key}:burst`;
        const burstRequests = this.burstCounts.get(burstKey) || [];
        burstRequests.push(now);
        this.burstCounts.set(burstKey, burstRequests);

        // Record for minute tracking
        const minuteKey = `${key}:minute`;
        const minuteRequests = this.requestCounts.get(minuteKey) || [];
        minuteRequests.push(now);
        this.requestCounts.set(minuteKey, minuteRequests);

        // Record for hour tracking
        const hourKey = `${key}:hour`;
        const hourRequests = this.requestCounts.get(hourKey) || [];
        hourRequests.push(now);
        this.requestCounts.set(hourKey, hourRequests);
    }

    /**
     * Get current rate limit status
     */
    getCurrentLimits() {
        return {
            requestsPerMinute: this.options.requestsPerMinute,
            requestsPerHour: this.options.requestsPerHour,
            burstLimit: this.options.burstLimit,
            enabled: this.options.enabled
        };
    }
}

/**
 * Voice Memory Monitor
 */
class VoiceMemoryMonitor {
    constructor(options = {}) {
        this.options = {
            limitMB: options.limitMB || 50,
            checkInterval: options.checkInterval || 30000,
            enableCleanup: options.enableCleanup !== false
        };

        this.usageHistory = [];
        this.intervalId = null;
    }

    /**
     * Start memory monitoring
     */
    start() {
        if (this.intervalId) return;

        this.intervalId = setInterval(() => {
            this.checkMemoryUsage();
        }, this.options.checkInterval);
    }

    /**
     * Stop memory monitoring
     */
    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    /**
     * Check current memory usage
     */
    checkMemoryUsage() {
        if (!performance.memory) {
            return;
        }

        const usage = {
            used: performance.memory.usedJSHeapSize / 1024 / 1024,
            total: performance.memory.totalJSHeapSize / 1024 / 1024,
            limit: performance.memory.jsHeapSizeLimit / 1024 / 1024,
            timestamp: Date.now()
        };

        this.usageHistory.push(usage);

        // Keep only last 100 measurements
        if (this.usageHistory.length > 100) {
            this.usageHistory = this.usageHistory.slice(-100);
        }

        // Check if cleanup is needed
        if (this.options.enableCleanup && usage.used > this.options.limitMB) {
            this.triggerCleanup();
        }
    }

    /**
     * Check if memory is available for new operations
     */
    isMemoryAvailable() {
        if (!performance.memory) {
            return true; // Assume available if can't measure
        }

        const currentUsage = performance.memory.usedJSHeapSize / 1024 / 1024;
        return currentUsage < this.options.limitMB;
    }

    /**
     * Get memory usage statistics
     */
    getUsageStats() {
        if (this.usageHistory.length === 0) {
            return null;
        }

        const latest = this.usageHistory[this.usageHistory.length - 1];
        const average = this.usageHistory.reduce((sum, usage) => sum + usage.used, 0) / this.usageHistory.length;

        return {
            current: latest.used,
            average: average,
            limit: this.options.limitMB,
            available: this.options.limitMB - latest.used,
            utilizationPercent: (latest.used / this.options.limitMB) * 100
        };
    }

    /**
     * Get memory warnings
     */
    getWarnings() {
        const warnings = [];
        const stats = this.getUsageStats();

        if (stats) {
            if (stats.utilizationPercent > 90) {
                warnings.push('Memory usage critical (>90%)');
            } else if (stats.utilizationPercent > 75) {
                warnings.push('Memory usage high (>75%)');
            }

            if (stats.available < 5) {
                warnings.push('Low memory available (<5MB)');
            }
        }

        return warnings;
    }

    /**
     * Trigger memory cleanup
     */
    triggerCleanup() {
        // Emit cleanup event
        const event = new CustomEvent('voiceMemoryCleanup', {
            detail: { usage: this.getUsageStats() }
        });
        window.dispatchEvent(event);
    }

    /**
     * Clear old usage data
     */
    clearOldData() {
        if (this.usageHistory.length > 50) {
            this.usageHistory = this.usageHistory.slice(-25);
        }
    }
}

/**
 * Voice Performance Reporter
 */
class VoicePerformanceReporter {
    constructor(options = {}) {
        this.options = {
            reportInterval: options.reportInterval || 60000,
            enableReporting: options.enableReporting !== false,
            endpoint: options.endpoint || '/voice/analytics'
        };

        this.reportQueue = [];
        this.intervalId = null;
    }

    /**
     * Start performance reporting
     */
    start() {
        if (!this.options.enableReporting || this.intervalId) return;

        this.intervalId = setInterval(() => {
            this.sendReport();
        }, this.options.reportInterval);
    }

    /**
     * Stop performance reporting
     */
    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }

        // Send final report
        if (this.reportQueue.length > 0) {
            this.sendReport();
        }
    }

    /**
     * Report an error immediately
     */
    reportError(errorType, message, context = {}) {
        const report = {
            type: 'error',
            errorType,
            message,
            context,
            timestamp: Date.now()
        };

        this.reportQueue.push(report);

        // Send immediately for critical errors
        if (this.isCriticalError(errorType)) {
            this.sendReport();
        }
    }

    /**
     * Add performance data to report queue
     */
    addPerformanceData(data) {
        const report = {
            type: 'performance',
            data,
            timestamp: Date.now()
        };

        this.reportQueue.push(report);
    }

    /**
     * Send queued reports
     */
    async sendReport() {
        if (this.reportQueue.length === 0) return;

        try {
            const reports = [...this.reportQueue];
            this.reportQueue = [];

            const response = await fetch(this.options.endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    reports,
                    timestamp: Date.now(),
                    userAgent: navigator.userAgent
                }),
                credentials: 'include'
            });

            if (!response.ok) {
                console.warn('Failed to send voice performance report:', response.status);
            }

        } catch (error) {
            console.warn('Error sending voice performance report:', error);
            // Re-queue reports for retry (keep only last 10)
            this.reportQueue = [...this.reportQueue.slice(-10), ...this.reportQueue];
        }
    }

    /**
     * Check if error is critical
     */
    isCriticalError(errorType) {
        const criticalErrors = [
            'memory_exhausted',
            'rate_limit_exceeded',
            'resource_leak',
            'browser_crash'
        ];
        return criticalErrors.includes(errorType);
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        VoicePerformanceMonitor,
        VoiceRateLimiter,
        VoiceMemoryMonitor,
        VoicePerformanceReporter
    };
}