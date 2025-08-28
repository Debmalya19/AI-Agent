/**
 * Voice Analytics Integration Example
 * 
 * This example demonstrates how to integrate voice analytics with the existing
 * chat system and voice controller for comprehensive performance monitoring.
 */

class VoiceAnalyticsIntegration {
    constructor(chatInterface, voiceController) {
        this.chatInterface = chatInterface;
        this.voiceController = voiceController;
        
        // Initialize analytics if voice controller has it
        this.analytics = voiceController.analytics;
        
        // Set up integration
        this.setupChatIntegration();
        this.setupVoiceControllerIntegration();
        this.setupPerformanceMonitoring();
    }
    
    /**
     * Set up integration with chat interface
     */
    setupChatIntegration() {
        if (!this.chatInterface || !this.analytics) return;
        
        // Track when voice is used in chat context
        this.chatInterface.addEventListener('message_sent', (event) => {
            if (event.voiceUsed) {
                const voiceMetrics = this.voiceController.getAnalyticsSummary();
                this.analytics.recordVoiceInChat(event.sessionId, voiceMetrics);
            }
        });
        
        // Track chat session analytics
        this.chatInterface.addEventListener('session_start', (event) => {
            this.currentChatSession = event.sessionId;
        });
        
        this.chatInterface.addEventListener('session_end', (event) => {
            if (this.currentChatSession) {
                this.flushChatSessionAnalytics(this.currentChatSession);
            }
        });
    }
    
    /**
     * Set up integration with voice controller events
     */
    setupVoiceControllerIntegration() {
        if (!this.voiceController || !this.analytics) return;
        
        // Track voice feature usage
        this.voiceController.addEventListener('recording_started', () => {
            this.analytics.recordFeatureAdoption('voiceInput', true, {
                timestamp: Date.now(),
                context: 'user_initiated'
            });
        });
        
        this.voiceController.addEventListener('speech_started', (event) => {
            this.analytics.recordFeatureAdoption('voiceOutput', true, {
                textLength: event.text?.length || 0,
                timestamp: Date.now()
            });
        });
        
        // Track settings changes
        this.voiceController.addEventListener('settings_changed', (event) => {
            this.analytics.recordFeatureAdoption('settingsChanged', true, event.settings);
        });
        
        // Track fallback activation
        this.voiceController.addEventListener('fallback_activated', (event) => {
            this.analytics.recordVoiceError(
                'fallback',
                `Voice fallback activated: ${event.reason}`,
                {
                    reason: event.reason,
                    errorCount: event.errorCount,
                    lastError: event.lastError
                },
                'fallback_to_text'
            );
        });
        
        // Track voice restoration
        this.voiceController.addEventListener('voice_restored', () => {
            this.analytics.recordFeatureAdoption('voiceRestored', true, {
                timestamp: Date.now(),
                previousErrors: this.voiceController.getErrorStatistics()
            });
        });
    }
    
    /**
     * Set up performance monitoring
     */
    setupPerformanceMonitoring() {
        if (!this.analytics) return;
        
        // Monitor overall system performance
        this.performanceMonitor = setInterval(() => {
            this.collectSystemPerformanceMetrics();
        }, 60000); // Every minute
        
        // Monitor memory usage
        if ('memory' in performance) {
            this.memoryMonitor = setInterval(() => {
                this.collectMemoryMetrics();
            }, 30000); // Every 30 seconds
        }
    }
    
    /**
     * Collect system performance metrics
     */
    collectSystemPerformanceMetrics() {
        const metrics = {
            timestamp: Date.now(),
            connectionType: navigator.connection?.effectiveType || 'unknown',
            onlineStatus: navigator.onLine,
            deviceMemory: navigator.deviceMemory || 'unknown',
            hardwareConcurrency: navigator.hardwareConcurrency || 'unknown'
        };
        
        // Record as performance context
        this.analytics.recordPerformanceMetric({
            operationType: 'system_performance',
            duration: 0,
            context: metrics
        });
    }
    
    /**
     * Collect memory usage metrics
     */
    collectMemoryMetrics() {
        if (!('memory' in performance)) return;
        
        const memoryInfo = performance.memory;
        const metrics = {
            timestamp: Date.now(),
            usedJSHeapSize: memoryInfo.usedJSHeapSize,
            totalJSHeapSize: memoryInfo.totalJSHeapSize,
            jsHeapSizeLimit: memoryInfo.jsHeapSizeLimit,
            memoryPressure: memoryInfo.usedJSHeapSize / memoryInfo.jsHeapSizeLimit
        };
        
        // Record memory metrics
        this.analytics.recordPerformanceMetric({
            operationType: 'memory_usage',
            duration: 0,
            context: metrics
        });
        
        // Alert if memory usage is high
        if (metrics.memoryPressure > 0.8) {
            console.warn('High memory usage detected:', metrics);
            this.analytics.recordVoiceError(
                'performance',
                'High memory usage detected',
                metrics,
                'memory_cleanup_suggested'
            );
        }
    }
    
    /**
     * Flush chat session analytics
     */
    flushChatSessionAnalytics(sessionId) {
        if (!this.analytics) return;
        
        const sessionSummary = this.analytics.getSessionSummary();
        const voiceMetrics = {
            sessionId,
            voiceInteractions: sessionSummary.voiceInteractions,
            sttUsage: sessionSummary.sttUsage,
            ttsUsage: sessionSummary.ttsUsage,
            errors: sessionSummary.errors,
            averageProcessingTime: sessionSummary.averageProcessingTime,
            errorRate: sessionSummary.errorRate,
            featureUsage: sessionSummary.featureUsage
        };
        
        this.analytics.recordVoiceInChat(sessionId, voiceMetrics);
    }
    
    /**
     * Get comprehensive analytics report
     */
    async getAnalyticsReport(days = 30) {
        if (!this.analytics) return null;
        
        try {
            const response = await fetch(`/voice/analytics/report?days=${days}`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return data.report;
            
        } catch (error) {
            console.error('Failed to get analytics report:', error);
            return null;
        }
    }
    
    /**
     * Get performance metrics
     */
    async getPerformanceMetrics(days = 30) {
        try {
            const response = await fetch(`/voice/analytics/performance?days=${days}`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return data.metrics;
            
        } catch (error) {
            console.error('Failed to get performance metrics:', error);
            return null;
        }
    }
    
    /**
     * Get error analysis
     */
    async getErrorAnalysis(days = 30) {
        try {
            const response = await fetch(`/voice/analytics/errors?days=${days}`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return data.error_analysis;
            
        } catch (error) {
            console.error('Failed to get error analysis:', error);
            return null;
        }
    }
    
    /**
     * Display analytics dashboard
     */
    async displayAnalyticsDashboard(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        try {
            // Get all analytics data
            const [report, performance, errors] = await Promise.all([
                this.getAnalyticsReport(),
                this.getPerformanceMetrics(),
                this.getErrorAnalysis()
            ]);
            
            // Create dashboard HTML
            const dashboardHTML = this.createDashboardHTML(report, performance, errors);
            container.innerHTML = dashboardHTML;
            
            // Add interactivity
            this.setupDashboardInteractivity(container);
            
        } catch (error) {
            console.error('Failed to display analytics dashboard:', error);
            container.innerHTML = '<p>Failed to load analytics dashboard</p>';
        }
    }
    
    /**
     * Create dashboard HTML
     */
    createDashboardHTML(report, performance, errors) {
        return `
            <div class="voice-analytics-dashboard">
                <h2>Voice Analytics Dashboard</h2>
                
                <div class="analytics-summary">
                    <h3>Usage Summary</h3>
                    ${report ? `
                        <div class="metric">
                            <span class="label">Total Voice Interactions:</span>
                            <span class="value">${report.total_voice_interactions}</span>
                        </div>
                        <div class="metric">
                            <span class="label">STT Usage:</span>
                            <span class="value">${report.stt_usage_count}</span>
                        </div>
                        <div class="metric">
                            <span class="label">TTS Usage:</span>
                            <span class="value">${report.tts_usage_count}</span>
                        </div>
                        <div class="metric">
                            <span class="label">Average STT Time:</span>
                            <span class="value">${Math.round(report.avg_stt_processing_time)}ms</span>
                        </div>
                        <div class="metric">
                            <span class="label">Average TTS Time:</span>
                            <span class="value">${Math.round(report.avg_tts_processing_time)}ms</span>
                        </div>
                        <div class="metric">
                            <span class="label">Error Count:</span>
                            <span class="value">${report.voice_error_count}</span>
                        </div>
                        <div class="metric">
                            <span class="label">Engagement Score:</span>
                            <span class="value">${(report.engagement_score * 100).toFixed(1)}%</span>
                        </div>
                    ` : '<p>No usage data available</p>'}
                </div>
                
                <div class="performance-metrics">
                    <h3>Performance Metrics</h3>
                    ${performance && performance.length > 0 ? `
                        <div class="metrics-grid">
                            ${performance.map(metric => `
                                <div class="performance-card">
                                    <h4>${metric.feature_type}</h4>
                                    <div class="metric">
                                        <span class="label">Success Rate:</span>
                                        <span class="value">${(metric.success_rate * 100).toFixed(1)}%</span>
                                    </div>
                                    <div class="metric">
                                        <span class="label">Avg Time:</span>
                                        <span class="value">${Math.round(metric.avg_processing_time)}ms</span>
                                    </div>
                                    <div class="metric">
                                        <span class="label">Usage Count:</span>
                                        <span class="value">${metric.usage_count}</span>
                                    </div>
                                    <div class="metric">
                                        <span class="label">Trend:</span>
                                        <span class="value trend-${metric.trend}">${metric.trend}</span>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<p>No performance data available</p>'}
                </div>
                
                <div class="error-analysis">
                    <h3>Error Analysis</h3>
                    ${errors && errors.length > 0 ? `
                        <div class="error-list">
                            ${errors.map(error => `
                                <div class="error-card">
                                    <h4>${error.error_type}</h4>
                                    <div class="metric">
                                        <span class="label">Frequency:</span>
                                        <span class="value">${error.frequency}</span>
                                    </div>
                                    <div class="metric">
                                        <span class="label">Avg Recovery Time:</span>
                                        <span class="value">${Math.round(error.avg_recovery_time)}ms</span>
                                    </div>
                                    <div class="suggested-fixes">
                                        <h5>Suggested Fixes:</h5>
                                        <ul>
                                            ${error.suggested_fixes.map(fix => `<li>${fix}</li>`).join('')}
                                        </ul>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<p>No error data available</p>'}
                </div>
            </div>
        `;
    }
    
    /**
     * Set up dashboard interactivity
     */
    setupDashboardInteractivity(container) {
        // Add click handlers for expandable sections
        const cards = container.querySelectorAll('.performance-card, .error-card');
        cards.forEach(card => {
            card.addEventListener('click', () => {
                card.classList.toggle('expanded');
            });
        });
        
        // Add refresh button
        const refreshButton = document.createElement('button');
        refreshButton.textContent = 'Refresh Data';
        refreshButton.className = 'refresh-button';
        refreshButton.addEventListener('click', () => {
            this.displayAnalyticsDashboard(container.id);
        });
        
        container.insertBefore(refreshButton, container.firstChild);
    }
    
    /**
     * Clean up resources
     */
    destroy() {
        if (this.performanceMonitor) {
            clearInterval(this.performanceMonitor);
        }
        
        if (this.memoryMonitor) {
            clearInterval(this.memoryMonitor);
        }
        
        // Remove event listeners
        if (this.chatInterface) {
            this.chatInterface.removeEventListener('message_sent');
            this.chatInterface.removeEventListener('session_start');
            this.chatInterface.removeEventListener('session_end');
        }
        
        if (this.voiceController) {
            this.voiceController.removeEventListener('recording_started');
            this.voiceController.removeEventListener('speech_started');
            this.voiceController.removeEventListener('settings_changed');
            this.voiceController.removeEventListener('fallback_activated');
            this.voiceController.removeEventListener('voice_restored');
        }
    }
}

// Usage example
/*
// Initialize the integration
const chatInterface = new ChatInterface();
const voiceController = new VoiceController(chatInterface);
const analyticsIntegration = new VoiceAnalyticsIntegration(chatInterface, voiceController);

// Display analytics dashboard
analyticsIntegration.displayAnalyticsDashboard('analytics-container');

// Get specific reports
analyticsIntegration.getAnalyticsReport(7).then(report => {
    console.log('Weekly voice analytics report:', report);
});

analyticsIntegration.getPerformanceMetrics(30).then(metrics => {
    console.log('Monthly performance metrics:', metrics);
});

analyticsIntegration.getErrorAnalysis(14).then(errors => {
    console.log('Bi-weekly error analysis:', errors);
});
*/

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceAnalyticsIntegration;
} else {
    window.VoiceAnalyticsIntegration = VoiceAnalyticsIntegration;
}