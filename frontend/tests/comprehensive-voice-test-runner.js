/**
 * Comprehensive Voice Test Runner
 * Runs all voice test suites including unit tests, integration tests, E2E tests, 
 * accessibility tests, and performance tests
 */

class ComprehensiveVoiceTestRunner {
    constructor() {
        this.testSuites = [];
        this.results = {
            total: 0,
            passed: 0,
            failed: 0,
            suites: [],
            startTime: null,
            endTime: null,
            duration: 0
        };
        this.performanceMetrics = [];
    }

    /**
     * Add a test suite to run
     * @param {string} name - Test suite name
     * @param {Function} testClass - Test class constructor
     * @param {string} category - Test category (unit, integration, e2e, accessibility, performance)
     */
    addTestSuite(name, testClass, category = 'unit') {
        this.testSuites.push({ name, testClass, category });
    }

    /**
     * Run all test suites
     */
    async runAllTests() {
        console.log('🧪 Starting Comprehensive Voice Feature Tests');
        console.log('=' .repeat(60));
        console.log(`Running ${this.testSuites.length} test suites...\n`);

        this.results.startTime = Date.now();

        // Group test suites by category
        const suitesByCategory = this.groupSuitesByCategory();

        // Run test suites in order: unit -> integration -> e2e -> accessibility -> performance
        const categoryOrder = ['unit', 'integration', 'e2e', 'accessibility', 'performance'];
        
        for (const category of categoryOrder) {
            if (suitesByCategory[category] && suitesByCategory[category].length > 0) {
                await this.runCategoryTests(category, suitesByCategory[category]);
            }
        }

        this.results.endTime = Date.now();
        this.results.duration = this.results.endTime - this.results.startTime;

        this.printConsolidatedResults();
        this.generateTestReport();
        
        return this.results;
    }

    /**
     * Group test suites by category
     */
    groupSuitesByCategory() {
        const grouped = {};
        this.testSuites.forEach(suite => {
            if (!grouped[suite.category]) {
                grouped[suite.category] = [];
            }
            grouped[suite.category].push(suite);
        });
        return grouped;
    }

    /**
     * Run tests for a specific category
     */
    async runCategoryTests(category, suites) {
        console.log(`\n📋 Running ${category.toUpperCase()} Tests`);
        console.log('-'.repeat(40));

        for (const suite of suites) {
            console.log(`\n🔍 ${suite.name}...`);
            
            try {
                const testInstance = new suite.testClass();
                await testInstance.runTests();
                
                const suiteResults = testInstance.printResults ? testInstance.printResults() : { passed: 0, failed: 0, total: 0 };
                
                // Collect performance metrics if available
                if (testInstance.performanceMetrics) {
                    this.performanceMetrics.push(...testInstance.performanceMetrics);
                }

                this.results.suites.push({
                    name: suite.name,
                    category: suite.category,
                    ...suiteResults
                });

                this.results.total += suiteResults.total;
                this.results.passed += suiteResults.passed;
                this.results.failed += suiteResults.failed;

                const status = suiteResults.failed === 0 ? '✅' : '❌';
                const rate = suiteResults.total > 0 
                    ? ((suiteResults.passed / suiteResults.total) * 100).toFixed(1)
                    : '0.0';
                console.log(`${status} ${suite.name}: ${suiteResults.passed}/${suiteResults.total} (${rate}%)`);

            } catch (error) {
                console.error(`❌ Error running ${suite.name}:`, error);
                this.results.suites.push({
                    name: suite.name,
                    category: suite.category,
                    total: 0,
                    passed: 0,
                    failed: 1,
                    error: error.message
                });
                this.results.failed += 1;
            }
        }
    }

    /**
     * Print consolidated test results
     */
    printConsolidatedResults() {
        console.log('\n' + '='.repeat(60));
        console.log('🏁 COMPREHENSIVE VOICE TEST RESULTS');
        console.log('='.repeat(60));

        // Overall summary
        console.log(`\n📊 Overall Summary:`);
        console.log(`   Total Tests: ${this.results.total}`);
        console.log(`   Passed: ${this.results.passed} ✅`);
        console.log(`   Failed: ${this.results.failed} ❌`);
        console.log(`   Duration: ${(this.results.duration / 1000).toFixed(2)}s`);
        
        const successRate = this.results.total > 0 
            ? ((this.results.passed / this.results.total) * 100).toFixed(1)
            : '0.0';
        console.log(`   Success Rate: ${successRate}%`);

        // Per-category breakdown
        console.log(`\n📋 Results by Category:`);
        const categories = ['unit', 'integration', 'e2e', 'accessibility', 'performance'];
        
        categories.forEach(category => {
            const categorySuites = this.results.suites.filter(s => s.category === category);
            if (categorySuites.length > 0) {
                const categoryTotal = categorySuites.reduce((sum, s) => sum + s.total, 0);
                const categoryPassed = categorySuites.reduce((sum, s) => sum + s.passed, 0);
                const categoryFailed = categorySuites.reduce((sum, s) => sum + s.failed, 0);
                const categoryRate = categoryTotal > 0 
                    ? ((categoryPassed / categoryTotal) * 100).toFixed(1)
                    : '0.0';
                
                const status = categoryFailed === 0 ? '✅' : '❌';
                console.log(`   ${status} ${category.toUpperCase()}: ${categoryPassed}/${categoryTotal} (${categoryRate}%)`);
                
                // Show individual suite results
                categorySuites.forEach(suite => {
                    const suiteStatus = suite.failed === 0 ? '  ✅' : '  ❌';
                    const suiteRate = suite.total > 0 
                        ? ((suite.passed / suite.total) * 100).toFixed(1)
                        : '0.0';
                    console.log(`     ${suiteStatus} ${suite.name}: ${suite.passed}/${suite.total} (${suiteRate}%)`);
                    
                    if (suite.error) {
                        console.log(`        Error: ${suite.error}`);
                    }
                });
            }
        });

        // Performance metrics summary
        if (this.performanceMetrics.length > 0) {
            console.log(`\n⚡ Performance Highlights:`);
            this.printPerformanceHighlights();
        }

        // Final status
        const overallStatus = this.results.failed === 0 ? 'PASSED' : 'FAILED';
        const statusIcon = this.results.failed === 0 ? '🎉' : '💥';
        
        console.log(`\n${statusIcon} Overall Status: ${overallStatus}`);
        
        if (this.results.failed > 0) {
            console.log(`\n⚠️  ${this.results.failed} test(s) failed. Review the results above for details.`);
        } else {
            console.log(`\n🎊 All tests passed! Voice features are working correctly.`);
        }
        
        console.log('='.repeat(60));
    }

    /**
     * Print performance highlights
     */
    printPerformanceHighlights() {
        // Group performance metrics by test type
        const metricsByType = {};
        this.performanceMetrics.forEach(metric => {
            if (!metricsByType[metric.test]) {
                metricsByType[metric.test] = [];
            }
            metricsByType[metric.test].push(metric);
        });

        // Show key performance metrics
        Object.keys(metricsByType).forEach(testType => {
            const metrics = metricsByType[testType];
            
            switch (testType) {
                case 'STT_Latency':
                    const avgLatency = metrics.reduce((sum, m) => sum + m.latency, 0) / metrics.length;
                    console.log(`   STT Average Latency: ${avgLatency.toFixed(2)}ms`);
                    break;
                    
                case 'TTS_Performance':
                    const avgRate = metrics.reduce((sum, m) => sum + m.rate, 0) / metrics.length;
                    console.log(`   TTS Average Rate: ${avgRate.toFixed(2)} chars/sec`);
                    break;
                    
                case 'Memory_Usage':
                    const maxMemory = Math.max(...metrics.map(m => m.peakMemory));
                    const totalLeak = metrics.reduce((sum, m) => sum + m.memoryLeak, 0);
                    console.log(`   Peak Memory: ${maxMemory}MB, Total Leak: ${totalLeak}MB`);
                    break;
                    
                case 'Concurrent_Operations':
                    const avgThroughput = metrics.reduce((sum, m) => sum + (m.operationCount / (m.totalTime / 1000)), 0) / metrics.length;
                    console.log(`   Concurrent Throughput: ${avgThroughput.toFixed(2)} ops/sec`);
                    break;
            }
        });
    }

    /**
     * Generate comprehensive test report
     */
    generateTestReport() {
        const timestamp = new Date().toISOString();
        const successRate = this.results.total > 0 
            ? ((this.results.passed / this.results.total) * 100).toFixed(1)
            : '0.0';

        const report = {
            timestamp: timestamp,
            summary: {
                total: this.results.total,
                passed: this.results.passed,
                failed: this.results.failed,
                successRate: parseFloat(successRate),
                duration: this.results.duration
            },
            suites: this.results.suites,
            performanceMetrics: this.performanceMetrics,
            recommendations: this.generateRecommendations()
        };

        // Store report for potential export
        this.testReport = report;
        
        return report;
    }

    /**
     * Generate recommendations based on test results
     */
    generateRecommendations() {
        const recommendations = [];

        // Check for failed tests
        const failedSuites = this.results.suites.filter(s => s.failed > 0);
        if (failedSuites.length > 0) {
            recommendations.push({
                type: 'error',
                message: `${failedSuites.length} test suite(s) have failures that need attention`,
                suites: failedSuites.map(s => s.name)
            });
        }

        // Check performance metrics
        const performanceIssues = this.checkPerformanceIssues();
        recommendations.push(...performanceIssues);

        // Check accessibility compliance
        const accessibilitySuites = this.results.suites.filter(s => s.category === 'accessibility');
        if (accessibilitySuites.length > 0) {
            const accessibilityFailures = accessibilitySuites.reduce((sum, s) => sum + s.failed, 0);
            if (accessibilityFailures > 0) {
                recommendations.push({
                    type: 'accessibility',
                    message: 'Accessibility issues detected that may affect users with disabilities',
                    priority: 'high'
                });
            }
        }

        // Check test coverage
        const categories = ['unit', 'integration', 'e2e', 'accessibility', 'performance'];
        const missingCategories = categories.filter(cat => 
            !this.results.suites.some(s => s.category === cat)
        );
        
        if (missingCategories.length > 0) {
            recommendations.push({
                type: 'coverage',
                message: `Missing test coverage for: ${missingCategories.join(', ')}`,
                priority: 'medium'
            });
        }

        return recommendations;
    }

    /**
     * Check for performance issues in metrics
     */
    checkPerformanceIssues() {
        const issues = [];

        // Check STT latency
        const sttMetrics = this.performanceMetrics.filter(m => m.test === 'STT_Latency');
        if (sttMetrics.length > 0) {
            const highLatency = sttMetrics.filter(m => m.latency > 1000);
            if (highLatency.length > 0) {
                issues.push({
                    type: 'performance',
                    message: 'High STT latency detected in some network conditions',
                    priority: 'medium'
                });
            }
        }

        // Check memory usage
        const memoryMetrics = this.performanceMetrics.filter(m => m.test === 'Memory_Usage');
        if (memoryMetrics.length > 0) {
            const memoryLeaks = memoryMetrics.filter(m => m.memoryLeak > 10);
            if (memoryLeaks.length > 0) {
                issues.push({
                    type: 'performance',
                    message: 'Memory leaks detected in voice operations',
                    priority: 'high'
                });
            }
        }

        return issues;
    }

    /**
     * Export test report as JSON
     */
    exportReport() {
        if (!this.testReport) {
            this.generateTestReport();
        }
        
        return JSON.stringify(this.testReport, null, 2);
    }

    /**
     * Generate HTML test report
     */
    generateHTMLReport() {
        if (!this.testReport) {
            this.generateTestReport();
        }

        const report = this.testReport;
        const successRate = report.summary.successRate;
        const statusClass = report.summary.failed === 0 ? 'success' : 'failure';

        return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comprehensive Voice Features Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .summary { background: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .summary.success { border-left: 5px solid #28a745; }
        .summary.failure { border-left: 5px solid #dc3545; }
        .category { margin-bottom: 20px; }
        .category h3 { color: #495057; border-bottom: 2px solid #dee2e6; padding-bottom: 5px; }
        .suite { margin-bottom: 10px; padding: 10px; border-radius: 3px; }
        .suite.passed { background: #d4edda; border-left: 4px solid #28a745; }
        .suite.failed { background: #f8d7da; border-left: 4px solid #dc3545; }
        .metrics { background: #e9ecef; padding: 15px; border-radius: 5px; margin-top: 20px; }
        .recommendations { background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 20px; }
        .timestamp { color: #6c757d; font-size: 0.9em; }
        .status { font-weight: bold; }
        .passed { color: #28a745; }
        .failed { color: #dc3545; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #dee2e6; }
        th { background-color: #f8f9fa; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Comprehensive Voice Features Test Report</h1>
            <p class="timestamp">Generated: ${report.timestamp}</p>
        </div>
        
        <div class="summary ${statusClass}">
            <h2>📊 Test Summary</h2>
            <table>
                <tr><td><strong>Total Tests:</strong></td><td>${report.summary.total}</td></tr>
                <tr><td><strong>Passed:</strong></td><td class="passed">${report.summary.passed}</td></tr>
                <tr><td><strong>Failed:</strong></td><td class="failed">${report.summary.failed}</td></tr>
                <tr><td><strong>Success Rate:</strong></td><td>${successRate}%</td></tr>
                <tr><td><strong>Duration:</strong></td><td>${(report.summary.duration / 1000).toFixed(2)}s</td></tr>
            </table>
            <p class="status">Status: <span class="${statusClass}">${report.summary.failed === 0 ? 'PASSED' : 'FAILED'}</span></p>
        </div>
        
        <h2>📋 Test Results by Category</h2>
        ${this.generateCategoryHTML(report.suites)}
        
        ${report.performanceMetrics.length > 0 ? `
        <div class="metrics">
            <h2>⚡ Performance Metrics</h2>
            ${this.generatePerformanceHTML(report.performanceMetrics)}
        </div>
        ` : ''}
        
        ${report.recommendations.length > 0 ? `
        <div class="recommendations">
            <h2>💡 Recommendations</h2>
            ${report.recommendations.map(rec => `
                <div class="recommendation">
                    <strong>${rec.type.toUpperCase()}:</strong> ${rec.message}
                    ${rec.priority ? `<em>(Priority: ${rec.priority})</em>` : ''}
                </div>
            `).join('')}
        </div>
        ` : ''}
    </div>
</body>
</html>`;
    }

    generateCategoryHTML(suites) {
        const categories = ['unit', 'integration', 'e2e', 'accessibility', 'performance'];
        
        return categories.map(category => {
            const categorySuites = suites.filter(s => s.category === category);
            if (categorySuites.length === 0) return '';
            
            return `
                <div class="category">
                    <h3>${category.toUpperCase()} Tests</h3>
                    ${categorySuites.map(suite => `
                        <div class="suite ${suite.failed === 0 ? 'passed' : 'failed'}">
                            <strong>${suite.name}</strong>: ${suite.passed}/${suite.total} 
                            (${suite.total > 0 ? ((suite.passed / suite.total) * 100).toFixed(1) : '0.0'}%)
                            ${suite.error ? `<br><em>Error: ${suite.error}</em>` : ''}
                        </div>
                    `).join('')}
                </div>
            `;
        }).join('');
    }

    generatePerformanceHTML(metrics) {
        // Group metrics by test type
        const metricsByType = {};
        metrics.forEach(metric => {
            if (!metricsByType[metric.test]) {
                metricsByType[metric.test] = [];
            }
            metricsByType[metric.test].push(metric);
        });

        return Object.keys(metricsByType).map(testType => {
            const testMetrics = metricsByType[testType];
            return `
                <h4>${testType}</h4>
                <table>
                    ${testMetrics.map(metric => {
                        const keys = Object.keys(metric).filter(k => k !== 'test');
                        return keys.map(key => `
                            <tr><td>${key}:</td><td>${JSON.stringify(metric[key])}</td></tr>
                        `).join('');
                    }).join('')}
                </table>
            `;
        }).join('');
    }
}

// Browser environment setup
if (typeof window !== 'undefined') {
    window.ComprehensiveVoiceTestRunner = ComprehensiveVoiceTestRunner;
    
    // Auto-run tests when page loads (if test classes are available)
    document.addEventListener('DOMContentLoaded', async () => {
        // Check if all test classes are available
        const testClasses = [
            'VoiceCapabilitiesTest',
            'VoiceSettingsTest', 
            'VoiceControllerTest',
            'VoiceUITest',
            'VoiceAccessibilityTest',
            'VoiceE2ETest',
            'VoicePerformanceTest'
        ];
        
        const availableClasses = testClasses.filter(className => window[className]);
        
        if (availableClasses.length > 0) {
            const runner = new ComprehensiveVoiceTestRunner();
            
            // Add available test suites
            if (window.VoiceCapabilitiesTest) {
                runner.addTestSuite('Voice Capabilities', window.VoiceCapabilitiesTest, 'unit');
            }
            if (window.VoiceSettingsTest) {
                runner.addTestSuite('Voice Settings', window.VoiceSettingsTest, 'unit');
            }
            if (window.VoiceControllerTest) {
                runner.addTestSuite('Voice Controller', window.VoiceControllerTest, 'unit');
            }
            if (window.VoiceUITest) {
                runner.addTestSuite('Voice UI', window.VoiceUITest, 'integration');
            }
            if (window.VoiceAccessibilityTest) {
                runner.addTestSuite('Voice Accessibility', window.VoiceAccessibilityTest, 'accessibility');
            }
            if (window.VoiceE2ETest) {
                runner.addTestSuite('Voice End-to-End', window.VoiceE2ETest, 'e2e');
            }
            if (window.VoicePerformanceTest) {
                runner.addTestSuite('Voice Performance', window.VoicePerformanceTest, 'performance');
            }
            
            const results = await runner.runAllTests();
            
            // Add results to page if there's a results container
            const resultsContainer = document.getElementById('test-results');
            if (resultsContainer) {
                resultsContainer.innerHTML = runner.generateHTMLReport();
            }
            
            // Store results globally for access
            window.comprehensiveTestResults = results;
        }
    });
}

// Node.js environment
if (typeof require !== 'undefined' && require.main === module) {
    async function runNodeTests() {
        const runner = new ComprehensiveVoiceTestRunner();
        
        // Add test suites (would need to require the test files)
        // This is a placeholder for Node.js execution
        console.log('Node.js execution not fully implemented. Use browser environment for complete testing.');
        
        const results = await runner.runAllTests();
        process.exit(results.failed > 0 ? 1 : 0);
    }
    
    runNodeTests().catch(error => {
        console.error('Comprehensive test runner error:', error);
        process.exit(1);
    });
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ComprehensiveVoiceTestRunner;
}