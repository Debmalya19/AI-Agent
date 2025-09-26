/**
 * Diagnostic Test Runner
 * Frontend utility for testing all diagnostic tools and endpoints
 */

class DiagnosticTestRunner {
    constructor() {
        this.baseURL = window.location.origin;
        this.results = {};
        this.isRunning = false;
    }

    /**
     * Run all diagnostic tests
     */
    async runAllTests() {
        if (this.isRunning) {
            console.warn('Tests already running');
            return this.results;
        }

        this.isRunning = true;
        this.results = {
            timestamp: new Date().toISOString(),
            tests: {},
            summary: {}
        };

        console.log('🚀 Starting comprehensive diagnostic test suite...');

        try {
            // Define all tests
            const tests = [
                { name: 'health_check', func: this.testHealthCheck.bind(this) },
                { name: 'system_status', func: this.testSystemStatus.bind(this) },
                { name: 'admin_users', func: this.testAdminUsers.bind(this) },
                { name: 'sessions', func: this.testSessions.bind(this) },
                { name: 'login_test', func: this.testLogin.bind(this) },
                { name: 'api_connectivity', func: this.testAPIConnectivity.bind(this) },
                { name: 'browser_compatibility', func: this.testBrowserCompatibility.bind(this) },
                { name: 'error_logging', func: this.testErrorLogging.bind(this) },
                { name: 'error_simulation', func: this.testErrorSimulation.bind(this) },
                { name: 'recent_errors', func: this.testRecentErrors.bind(this) },
                { name: 'error_statistics', func: this.testErrorStatistics.bind(this) }
            ];

            let passed = 0;
            const total = tests.length;

            // Run each test
            for (const test of tests) {
                console.log(`🔍 Testing ${test.name}...`);
                
                try {
                    const result = await test.func();
                    this.results.tests[test.name] = result;
                    
                    if (result.success) {
                        passed++;
                        console.log(`  ✅ ${test.name} passed`);
                    } else {
                        console.log(`  ❌ ${test.name} failed: ${result.error}`);
                    }
                } catch (error) {
                    this.results.tests[test.name] = {
                        success: false,
                        error: error.message,
                        timestamp: new Date().toISOString()
                    };
                    console.log(`  ❌ ${test.name} crashed: ${error.message}`);
                }
            }

            // Calculate summary
            this.results.summary = {
                total_tests: total,
                passed_tests: passed,
                failed_tests: total - passed,
                success_rate: Math.round((passed / total) * 100),
                overall_status: passed === total ? 'excellent' : passed >= total * 0.8 ? 'good' : 'needs_attention'
            };

            console.log('📊 Test Summary:');
            console.log(`  ✅ Passed: ${passed}/${total}`);
            console.log(`  📈 Success Rate: ${this.results.summary.success_rate}%`);
            console.log(`  🎯 Overall Status: ${this.results.summary.overall_status}`);

        } catch (error) {
            console.error('❌ Test suite failed:', error);
            this.results.error = error.message;
        } finally {
            this.isRunning = false;
        }

        return this.results;
    }

    /**
     * Test health check endpoint
     */
    async testHealthCheck() {
        try {
            const response = await fetch(`${this.baseURL}/api/debug/health`);
            const data = await response.json();

            return {
                success: response.ok,
                status_code: response.status,
                data: data,
                error: response.ok ? null : `HTTP ${response.status}`,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Test system status endpoint
     */
    async testSystemStatus() {
        try {
            const response = await fetch(`${this.baseURL}/api/debug/status`);
            const data = await response.json();

            return {
                success: response.ok && data.status === 'healthy',
                status_code: response.status,
                data: data,
                error: response.ok ? (data.status !== 'healthy' ? `System status: ${data.status}` : null) : `HTTP ${response.status}`,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Test admin users endpoint
     */
    async testAdminUsers() {
        try {
            const response = await fetch(`${this.baseURL}/api/debug/admin-users`);
            const data = await response.json();

            return {
                success: response.ok,
                status_code: response.status,
                data: data,
                admin_count: data.total_count || 0,
                error: response.ok ? null : `HTTP ${response.status}`,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Test sessions endpoint
     */
    async testSessions() {
        try {
            const response = await fetch(`${this.baseURL}/api/debug/sessions?hours=24`);
            const data = await response.json();

            return {
                success: response.ok,
                status_code: response.status,
                data: data,
                session_count: data.total_count || 0,
                error: response.ok ? null : `HTTP ${response.status}`,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Test login functionality
     */
    async testLogin() {
        try {
            const testCredentials = {
                email: 'test@example.com',
                username: 'test_user',
                password: 'test_password'
            };

            const response = await fetch(`${this.baseURL}/api/debug/test-login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(testCredentials)
            });

            const data = await response.json();

            return {
                success: response.ok,
                status_code: response.status,
                data: data,
                login_success: data.success || false,
                error: response.ok ? null : `HTTP ${response.status}`,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Test API connectivity
     */
    async testAPIConnectivity() {
        try {
            const response = await fetch(`${this.baseURL}/api/debug/connectivity`);
            const data = await response.json();

            return {
                success: response.ok,
                status_code: response.status,
                data: data,
                connectivity_status: data.overall_status || 'unknown',
                error: response.ok ? null : `HTTP ${response.status}`,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Test browser compatibility
     */
    async testBrowserCompatibility() {
        try {
            const response = await fetch(`${this.baseURL}/api/debug/browser-compatibility`);
            const data = await response.json();

            return {
                success: response.ok,
                status_code: response.status,
                data: data,
                browser_info: data.browser_info || {},
                error: response.ok ? null : `HTTP ${response.status}`,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Test error logging
     */
    async testErrorLogging() {
        try {
            const testError = {
                category: 'frontend',
                severity: 'low',
                message: 'Test error from diagnostic test runner',
                details: {
                    test_type: 'frontend_diagnostic_test',
                    timestamp: new Date().toISOString(),
                    user_agent: navigator.userAgent
                }
            };

            const response = await fetch(`${this.baseURL}/api/debug/log-error`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(testError)
            });

            const data = await response.json();

            return {
                success: response.ok && data.success,
                status_code: response.status,
                data: data,
                error: response.ok ? (data.success ? null : 'Error logging failed') : `HTTP ${response.status}`,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Test error simulation
     */
    async testErrorSimulation() {
        try {
            const response = await fetch(`${this.baseURL}/api/debug/simulate-error`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });

            const data = await response.json();

            return {
                success: response.ok && data.success,
                status_code: response.status,
                data: data,
                error: response.ok ? (data.success ? null : 'Error simulation failed') : `HTTP ${response.status}`,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Test recent errors endpoint
     */
    async testRecentErrors() {
        try {
            const response = await fetch(`${this.baseURL}/api/debug/recent-errors?hours=24&limit=10`);
            const data = await response.json();

            return {
                success: response.ok,
                status_code: response.status,
                data: data,
                error_count: data.total_count || 0,
                error: response.ok ? null : `HTTP ${response.status}`,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Test error statistics endpoint
     */
    async testErrorStatistics() {
        try {
            const response = await fetch(`${this.baseURL}/api/debug/error-statistics?hours=24`);
            const data = await response.json();

            return {
                success: response.ok,
                status_code: response.status,
                data: data,
                total_errors: data.total_errors || 0,
                error: response.ok ? null : `HTTP ${response.status}`,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Generate a detailed report
     */
    generateReport() {
        if (!this.results.tests) {
            return 'No test results available. Run tests first.';
        }

        let report = '🔧 Diagnostic Tools Test Report\n';
        report += '=' * 50 + '\n\n';

        // Summary
        report += '📊 SUMMARY\n';
        report += '-' * 20 + '\n';
        if (this.results.summary) {
            report += `Total Tests: ${this.results.summary.total_tests}\n`;
            report += `Passed: ${this.results.summary.passed_tests}\n`;
            report += `Failed: ${this.results.summary.failed_tests}\n`;
            report += `Success Rate: ${this.results.summary.success_rate}%\n`;
            report += `Overall Status: ${this.results.summary.overall_status}\n\n`;
        }

        // Individual test results
        report += '📋 DETAILED RESULTS\n';
        report += '-' * 20 + '\n';

        for (const [testName, result] of Object.entries(this.results.tests)) {
            const status = result.success ? '✅ PASS' : '❌ FAIL';
            report += `${status} ${testName.replace(/_/g, ' ').toUpperCase()}\n`;
            
            if (result.error) {
                report += `  Error: ${result.error}\n`;
            }
            
            if (result.data) {
                // Add relevant data points
                if (result.admin_count !== undefined) {
                    report += `  Admin Users: ${result.admin_count}\n`;
                }
                if (result.session_count !== undefined) {
                    report += `  Sessions: ${result.session_count}\n`;
                }
                if (result.connectivity_status) {
                    report += `  Connectivity: ${result.connectivity_status}\n`;
                }
                if (result.total_errors !== undefined) {
                    report += `  Total Errors: ${result.total_errors}\n`;
                }
            }
            
            report += '\n';
        }

        report += `Generated at: ${new Date().toLocaleString()}\n`;

        return report;
    }

    /**
     * Export results as JSON
     */
    exportResults() {
        const blob = new Blob([JSON.stringify(this.results, null, 2)], {
            type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `diagnostic-test-results-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    /**
     * Display results in console with formatting
     */
    displayResults() {
        console.log('🔧 Diagnostic Tools Test Results');
        console.log('=' * 50);

        if (this.results.summary) {
            console.log('📊 Summary:');
            console.log(`  Total Tests: ${this.results.summary.total_tests}`);
            console.log(`  Passed: ${this.results.summary.passed_tests}`);
            console.log(`  Failed: ${this.results.summary.failed_tests}`);
            console.log(`  Success Rate: ${this.results.summary.success_rate}%`);
            console.log(`  Overall Status: ${this.results.summary.overall_status}`);
            console.log('');
        }

        console.log('📋 Individual Results:');
        for (const [testName, result] of Object.entries(this.results.tests)) {
            const status = result.success ? '✅' : '❌';
            console.log(`  ${status} ${testName}: ${result.success ? 'PASS' : 'FAIL'}`);
            
            if (result.error) {
                console.log(`    Error: ${result.error}`);
            }
        }

        console.log('');
        console.log(`Generated at: ${new Date(this.results.timestamp).toLocaleString()}`);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DiagnosticTestRunner;
} else {
    window.DiagnosticTestRunner = DiagnosticTestRunner;
}

// Auto-initialize if in browser
if (typeof window !== 'undefined') {
    window.diagnosticTestRunner = new DiagnosticTestRunner();
    
    // Add global convenience functions
    window.runDiagnosticTests = () => window.diagnosticTestRunner.runAllTests();
    window.showDiagnosticResults = () => window.diagnosticTestRunner.displayResults();
    window.exportDiagnosticResults = () => window.diagnosticTestRunner.exportResults();
}