/**
 * Voice Processing Tests Runner
 * Runs all voice-related unit tests and provides consolidated results
 */

// Test runner for browser environment
class VoiceTestRunner {
    constructor() {
        this.testSuites = [];
        this.results = {
            total: 0,
            passed: 0,
            failed: 0,
            suites: []
        };
    }

    /**
     * Add a test suite to run
     * @param {string} name - Test suite name
     * @param {Function} testClass - Test class constructor
     */
    addTestSuite(name, testClass) {
        this.testSuites.push({ name, testClass });
    }

    /**
     * Run all test suites
     */
    async runAllTests() {
        console.log('🧪 Starting Voice Processing Tests\n');
        console.log('=' .repeat(50));

        for (const suite of this.testSuites) {
            console.log(`\n📋 Running ${suite.name}...`);
            console.log('-'.repeat(30));

            try {
                const testInstance = new suite.testClass();
                await testInstance.runTests();
                
                const suiteResults = testInstance.printResults();
                this.results.suites.push({
                    name: suite.name,
                    ...suiteResults
                });

                this.results.total += suiteResults.total;
                this.results.passed += suiteResults.passed;
                this.results.failed += suiteResults.failed;

            } catch (error) {
                console.error(`❌ Error running ${suite.name}:`, error);
                this.results.suites.push({
                    name: suite.name,
                    total: 0,
                    passed: 0,
                    failed: 1,
                    error: error.message
                });
                this.results.failed += 1;
            }
        }

        this.printConsolidatedResults();
        return this.results;
    }

    /**
     * Print consolidated test results
     */
    printConsolidatedResults() {
        console.log('\n' + '='.repeat(50));
        console.log('🏁 CONSOLIDATED TEST RESULTS');
        console.log('='.repeat(50));

        // Overall summary
        console.log(`\n📊 Overall Summary:`);
        console.log(`   Total Tests: ${this.results.total}`);
        console.log(`   Passed: ${this.results.passed} ✅`);
        console.log(`   Failed: ${this.results.failed} ❌`);
        
        const successRate = this.results.total > 0 
            ? ((this.results.passed / this.results.total) * 100).toFixed(1)
            : '0.0';
        console.log(`   Success Rate: ${successRate}%`);

        // Per-suite breakdown
        console.log(`\n📋 Per-Suite Results:`);
        this.results.suites.forEach(suite => {
            const status = suite.failed === 0 ? '✅' : '❌';
            const rate = suite.total > 0 
                ? ((suite.passed / suite.total) * 100).toFixed(1)
                : '0.0';
            
            console.log(`   ${status} ${suite.name}: ${suite.passed}/${suite.total} (${rate}%)`);
            
            if (suite.error) {
                console.log(`      Error: ${suite.error}`);
            }
        });

        // Final status
        const overallStatus = this.results.failed === 0 ? 'PASSED' : 'FAILED';
        const statusIcon = this.results.failed === 0 ? '🎉' : '💥';
        
        console.log(`\n${statusIcon} Overall Status: ${overallStatus}`);
        console.log('='.repeat(50));
    }

    /**
     * Generate HTML test report
     */
    generateHTMLReport() {
        const timestamp = new Date().toISOString();
        const successRate = this.results.total > 0 
            ? ((this.results.passed / this.results.total) * 100).toFixed(1)
            : '0.0';

        return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice Processing Tests Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .summary { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .suite { margin-bottom: 15px; padding: 10px; border-left: 4px solid #007bff; background: #f8f9fa; }
        .suite.passed { border-left-color: #28a745; }
        .suite.failed { border-left-color: #dc3545; }
        .status { font-weight: bold; }
        .passed { color: #28a745; }
        .failed { color: #dc3545; }
        .timestamp { color: #6c757d; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Voice Processing Tests Report</h1>
            <p class="timestamp">Generated: ${timestamp}</p>
        </div>
        
        <div class="summary">
            <h2>📊 Overall Summary</h2>
            <p><strong>Total Tests:</strong> ${this.results.total}</p>
            <p><strong>Passed:</strong> <span class="passed">${this.results.passed}</span></p>
            <p><strong>Failed:</strong> <span class="failed">${this.results.failed}</span></p>
            <p><strong>Success Rate:</strong> ${successRate}%</p>
            <p class="status">Status: <span class="${this.results.failed === 0 ? 'passed' : 'failed'}">${this.results.failed === 0 ? 'PASSED' : 'FAILED'}</span></p>
        </div>
        
        <h2>📋 Test Suites</h2>
        ${this.results.suites.map(suite => `
            <div class="suite ${suite.failed === 0 ? 'passed' : 'failed'}">
                <h3>${suite.name}</h3>
                <p><strong>Tests:</strong> ${suite.passed}/${suite.total}</p>
                <p><strong>Success Rate:</strong> ${suite.total > 0 ? ((suite.passed / suite.total) * 100).toFixed(1) : '0.0'}%</p>
                ${suite.error ? `<p><strong>Error:</strong> ${suite.error}</p>` : ''}
            </div>
        `).join('')}
    </div>
</body>
</html>`;
    }
}

// Browser environment setup
if (typeof window !== 'undefined') {
    // Make test runner available globally
    window.VoiceTestRunner = VoiceTestRunner;
    
    // Auto-run tests when page loads (if test classes are available)
    document.addEventListener('DOMContentLoaded', async () => {
        if (window.VoiceCapabilitiesTest && window.VoiceSettingsTest && window.VoiceControllerTest) {
            const runner = new VoiceTestRunner();
            
            runner.addTestSuite('VoiceCapabilities', window.VoiceCapabilitiesTest);
            runner.addTestSuite('VoiceSettings', window.VoiceSettingsTest);
            runner.addTestSuite('VoiceController', window.VoiceControllerTest);
            
            const results = await runner.runAllTests();
            
            // Add results to page if there's a results container
            const resultsContainer = document.getElementById('test-results');
            if (resultsContainer) {
                resultsContainer.innerHTML = runner.generateHTMLReport();
            }
            
            // Store results globally for access
            window.testResults = results;
        }
    });
}

// Node.js environment
if (typeof require !== 'undefined' && require.main === module) {
    async function runNodeTests() {
        // Load voice processing classes first
        const VoiceCapabilities = require('../voice-capabilities.js');
        const VoiceSettings = require('../voice-settings.js');
        const VoiceController = require('../voice-controller.js');
        
        // Make them globally available for tests
        global.VoiceCapabilities = VoiceCapabilities;
        global.VoiceSettings = VoiceSettings;
        global.VoiceController = VoiceController;
        
        // Load test classes
        const VoiceCapabilitiesTest = require('./voice-capabilities.test.js');
        const VoiceSettingsTest = require('./voice-settings.test.js');
        const VoiceControllerTest = require('./voice-controller.test.js');
        
        const runner = new VoiceTestRunner();
        
        runner.addTestSuite('VoiceCapabilities', VoiceCapabilitiesTest);
        runner.addTestSuite('VoiceSettings', VoiceSettingsTest);
        runner.addTestSuite('VoiceController', VoiceControllerTest);
        
        const results = await runner.runAllTests();
        
        // Exit with appropriate code
        process.exit(results.failed > 0 ? 1 : 0);
    }
    
    runNodeTests().catch(error => {
        console.error('Test runner error:', error);
        process.exit(1);
    });
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceTestRunner;
}