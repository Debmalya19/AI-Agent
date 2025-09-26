/**
 * API Connectivity Checker
 * Tests frontend-backend communication and identifies connectivity issues
 */

class APIConnectivityChecker {
    constructor() {
        this.baseURL = window.location.origin;
        this.results = {};
        this.isRunning = false;
    }

    /**
     * Run comprehensive connectivity diagnostics
     */
    async runDiagnostics() {
        if (this.isRunning) {
            console.warn('Diagnostics already running');
            return this.results;
        }

        this.isRunning = true;
        this.results = {
            timestamp: new Date().toISOString(),
            overall_status: 'unknown',
            tests: {}
        };

        console.log('🔍 Starting API connectivity diagnostics...');

        try {
            // Test basic server connectivity
            await this.testServerConnectivity();
            
            // Test authentication endpoints
            await this.testAuthEndpoints();
            
            // Test browser capabilities
            await this.testBrowserCapabilities();
            
            // Test CORS and credentials
            await this.testCORSAndCredentials();
            
            // Calculate overall status
            this.calculateOverallStatus();
            
            console.log('✅ Diagnostics completed:', this.results);
            
        } catch (error) {
            console.error('❌ Diagnostics failed:', error);
            this.results.error = error.message;
            this.results.overall_status = 'error';
        } finally {
            this.isRunning = false;
        }

        return this.results;
    }

    /**
     * Test basic server connectivity
     */
    async testServerConnectivity() {
        console.log('Testing server connectivity...');
        
        const tests = [
            { name: 'health_check', url: '/health', method: 'GET' },
            { name: 'static_files', url: '/static/login.html', method: 'GET' },
            { name: 'api_base', url: '/api/debug/health', method: 'GET' }
        ];

        this.results.tests.server_connectivity = {};

        for (const test of tests) {
            try {
                const startTime = performance.now();
                
                const response = await fetch(`${this.baseURL}${test.url}`, {
                    method: test.method,
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    }
                });
                
                const endTime = performance.now();
                const responseTime = Math.round(endTime - startTime);

                this.results.tests.server_connectivity[test.name] = {
                    success: response.ok,
                    status_code: response.status,
                    response_time_ms: responseTime,
                    error: response.ok ? null : `HTTP ${response.status}`
                };

                console.log(`  ✓ ${test.name}: ${response.status} (${responseTime}ms)`);
                
            } catch (error) {
                this.results.tests.server_connectivity[test.name] = {
                    success: false,
                    status_code: null,
                    response_time_ms: null,
                    error: error.message
                };
                
                console.log(`  ✗ ${test.name}: ${error.message}`);
            }
        }
    }

    /**
     * Test authentication endpoints
     */
    async testAuthEndpoints() {
        console.log('Testing authentication endpoints...');
        
        const endpoints = [
            { name: 'auth_me', url: '/api/auth/me', method: 'GET' },
            { name: 'auth_verify', url: '/api/auth/verify', method: 'GET' },
            { name: 'debug_status', url: '/api/debug/status', method: 'GET' },
            { name: 'admin_auth_users', url: '/admin/auth/users', method: 'GET' }
        ];

        this.results.tests.auth_endpoints = {};

        for (const endpoint of endpoints) {
            try {
                const startTime = performance.now();
                
                const response = await fetch(`${this.baseURL}${endpoint.url}`, {
                    method: endpoint.method,
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include'
                });
                
                const endTime = performance.now();
                const responseTime = Math.round(endTime - startTime);

                // For auth endpoints, 401 is expected without authentication
                const isExpectedResponse = response.status === 401 || response.ok;

                this.results.tests.auth_endpoints[endpoint.name] = {
                    success: isExpectedResponse,
                    status_code: response.status,
                    response_time_ms: responseTime,
                    error: isExpectedResponse ? null : `Unexpected status: ${response.status}`,
                    endpoint_available: response.status !== 404
                };

                console.log(`  ${isExpectedResponse ? '✓' : '✗'} ${endpoint.name}: ${response.status} (${responseTime}ms)`);
                
            } catch (error) {
                this.results.tests.auth_endpoints[endpoint.name] = {
                    success: false,
                    status_code: null,
                    response_time_ms: null,
                    error: error.message,
                    endpoint_available: false
                };
                
                console.log(`  ✗ ${endpoint.name}: ${error.message}`);
            }
        }
    }

    /**
     * Test browser capabilities
     */
    async testBrowserCapabilities() {
        console.log('Testing browser capabilities...');
        
        this.results.tests.browser_capabilities = {};

        // Test localStorage
        try {
            const testKey = 'connectivity_test';
            const testValue = 'test_value';
            localStorage.setItem(testKey, testValue);
            const retrieved = localStorage.getItem(testKey);
            localStorage.removeItem(testKey);
            
            this.results.tests.browser_capabilities.localStorage = {
                supported: retrieved === testValue,
                error: retrieved === testValue ? null : 'Value mismatch'
            };
            
            console.log(`  ${retrieved === testValue ? '✓' : '✗'} localStorage`);
            
        } catch (error) {
            this.results.tests.browser_capabilities.localStorage = {
                supported: false,
                error: error.message
            };
            console.log(`  ✗ localStorage: ${error.message}`);
        }

        // Test sessionStorage
        try {
            const testKey = 'connectivity_test';
            const testValue = 'test_value';
            sessionStorage.setItem(testKey, testValue);
            const retrieved = sessionStorage.getItem(testKey);
            sessionStorage.removeItem(testKey);
            
            this.results.tests.browser_capabilities.sessionStorage = {
                supported: retrieved === testValue,
                error: retrieved === testValue ? null : 'Value mismatch'
            };
            
            console.log(`  ${retrieved === testValue ? '✓' : '✗'} sessionStorage`);
            
        } catch (error) {
            this.results.tests.browser_capabilities.sessionStorage = {
                supported: false,
                error: error.message
            };
            console.log(`  ✗ sessionStorage: ${error.message}`);
        }

        // Test cookies
        try {
            const testCookie = 'connectivity_test=test_value; path=/';
            document.cookie = testCookie;
            const cookieSupported = document.cookie.includes('connectivity_test=test_value');
            
            // Clean up
            document.cookie = 'connectivity_test=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            
            this.results.tests.browser_capabilities.cookies = {
                supported: cookieSupported,
                error: cookieSupported ? null : 'Cookie not set or retrieved'
            };
            
            console.log(`  ${cookieSupported ? '✓' : '✗'} cookies`);
            
        } catch (error) {
            this.results.tests.browser_capabilities.cookies = {
                supported: false,
                error: error.message
            };
            console.log(`  ✗ cookies: ${error.message}`);
        }

        // Test Fetch API
        this.results.tests.browser_capabilities.fetchAPI = {
            supported: typeof fetch !== 'undefined',
            error: typeof fetch !== 'undefined' ? null : 'Fetch API not available'
        };
        console.log(`  ${typeof fetch !== 'undefined' ? '✓' : '✗'} Fetch API`);

        // Test JSON parsing
        try {
            const testObj = { test: 'value' };
            const jsonString = JSON.stringify(testObj);
            const parsed = JSON.parse(jsonString);
            const jsonSupported = parsed.test === 'value';
            
            this.results.tests.browser_capabilities.jsonParsing = {
                supported: jsonSupported,
                error: jsonSupported ? null : 'JSON parsing failed'
            };
            
            console.log(`  ${jsonSupported ? '✓' : '✗'} JSON parsing`);
            
        } catch (error) {
            this.results.tests.browser_capabilities.jsonParsing = {
                supported: false,
                error: error.message
            };
            console.log(`  ✗ JSON parsing: ${error.message}`);
        }
    }

    /**
     * Test CORS and credentials handling
     */
    async testCORSAndCredentials() {
        console.log('Testing CORS and credentials...');
        
        this.results.tests.cors_credentials = {};

        // Test credentials: 'include'
        try {
            const response = await fetch(`${this.baseURL}/api/auth/me`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json'
                }
            });

            this.results.tests.cors_credentials.credentials_include = {
                success: true,
                status_code: response.status,
                error: null
            };
            
            console.log(`  ✓ credentials: 'include' - ${response.status}`);
            
        } catch (error) {
            this.results.tests.cors_credentials.credentials_include = {
                success: false,
                status_code: null,
                error: error.message
            };
            console.log(`  ✗ credentials: 'include' - ${error.message}`);
        }

        // Test CORS headers
        try {
            const response = await fetch(`${this.baseURL}/api/debug/status`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });

            const corsHeaders = {
                'access-control-allow-origin': response.headers.get('access-control-allow-origin'),
                'access-control-allow-credentials': response.headers.get('access-control-allow-credentials'),
                'access-control-allow-methods': response.headers.get('access-control-allow-methods')
            };

            this.results.tests.cors_credentials.cors_headers = {
                success: true,
                headers: corsHeaders,
                error: null
            };
            
            console.log(`  ✓ CORS headers retrieved`);
            
        } catch (error) {
            this.results.tests.cors_credentials.cors_headers = {
                success: false,
                headers: null,
                error: error.message
            };
            console.log(`  ✗ CORS headers: ${error.message}`);
        }
    }

    /**
     * Calculate overall diagnostic status
     */
    calculateOverallStatus() {
        let totalTests = 0;
        let passedTests = 0;

        for (const category in this.results.tests) {
            const categoryTests = this.results.tests[category];
            
            for (const testName in categoryTests) {
                totalTests++;
                if (categoryTests[testName].success || categoryTests[testName].supported) {
                    passedTests++;
                }
            }
        }

        const successRate = totalTests > 0 ? (passedTests / totalTests) : 0;
        
        if (successRate >= 0.9) {
            this.results.overall_status = 'excellent';
        } else if (successRate >= 0.7) {
            this.results.overall_status = 'good';
        } else if (successRate >= 0.5) {
            this.results.overall_status = 'fair';
        } else {
            this.results.overall_status = 'poor';
        }

        this.results.success_rate = Math.round(successRate * 100);
        this.results.total_tests = totalTests;
        this.results.passed_tests = passedTests;
    }

    /**
     * Get diagnostic recommendations based on results
     */
    getRecommendations() {
        const recommendations = [];

        if (!this.results.tests) {
            return ['Run diagnostics first'];
        }

        // Check server connectivity issues
        const serverTests = this.results.tests.server_connectivity || {};
        if (Object.values(serverTests).some(test => !test.success)) {
            recommendations.push('Server connectivity issues detected - check network connection');
        }

        // Check auth endpoint issues
        const authTests = this.results.tests.auth_endpoints || {};
        if (Object.values(authTests).some(test => !test.endpoint_available)) {
            recommendations.push('Authentication endpoints not available - check server configuration');
        }

        // Check browser capability issues
        const browserTests = this.results.tests.browser_capabilities || {};
        if (!browserTests.localStorage?.supported) {
            recommendations.push('localStorage not supported - use alternative storage method');
        }
        if (!browserTests.cookies?.supported) {
            recommendations.push('Cookies not supported - check browser settings');
        }

        // Check CORS issues
        const corsTests = this.results.tests.cors_credentials || {};
        if (!corsTests.credentials_include?.success) {
            recommendations.push('Credentials handling issues - check CORS configuration');
        }

        if (recommendations.length === 0) {
            recommendations.push('All connectivity tests passed - system appears healthy');
        }

        return recommendations;
    }

    /**
     * Display results in a formatted way
     */
    displayResults(containerId = 'diagnostic-results') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container with ID '${containerId}' not found`);
            return;
        }

        const html = `
            <div class="diagnostic-results">
                <h3>API Connectivity Diagnostic Results</h3>
                <div class="overall-status status-${this.results.overall_status}">
                    <strong>Overall Status:</strong> ${this.results.overall_status.toUpperCase()}
                    <span class="success-rate">(${this.results.success_rate}% success rate)</span>
                </div>
                
                <div class="test-categories">
                    ${Object.entries(this.results.tests).map(([category, tests]) => `
                        <div class="test-category">
                            <h4>${category.replace(/_/g, ' ').toUpperCase()}</h4>
                            <ul>
                                ${Object.entries(tests).map(([testName, result]) => `
                                    <li class="${result.success || result.supported ? 'success' : 'failure'}">
                                        <span class="test-name">${testName.replace(/_/g, ' ')}</span>
                                        <span class="test-result">
                                            ${result.success || result.supported ? '✓' : '✗'}
                                            ${result.status_code ? `(${result.status_code})` : ''}
                                            ${result.response_time_ms ? `${result.response_time_ms}ms` : ''}
                                        </span>
                                        ${result.error ? `<div class="error-detail">${result.error}</div>` : ''}
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    `).join('')}
                </div>
                
                <div class="recommendations">
                    <h4>Recommendations</h4>
                    <ul>
                        ${this.getRecommendations().map(rec => `<li>${rec}</li>`).join('')}
                    </ul>
                </div>
                
                <div class="timestamp">
                    <small>Test completed at: ${new Date(this.results.timestamp).toLocaleString()}</small>
                </div>
            </div>
        `;

        container.innerHTML = html;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = APIConnectivityChecker;
} else {
    window.APIConnectivityChecker = APIConnectivityChecker;
}