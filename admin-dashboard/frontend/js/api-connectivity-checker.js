/**
 * API Connectivity Checker
 * Tests API endpoints and browser capabilities for authentication functionality
 */

class APIConnectivityChecker {
    constructor() {
        this.baseURL = '/api';
        this.debugMode = localStorage.getItem('admin_debug') === 'true';
        
        // Endpoints to test
        this.endpoints = {
            health: '/health',
            auth_login: '/api/auth/login',
            auth_verify: '/api/auth/verify',
            auth_logout: '/api/auth/logout',
            admin_dashboard: '/admin'
        };

        this.log('APIConnectivityChecker initialized');
    }

    /**
     * Run comprehensive connectivity diagnostics
     * @returns {Promise<Object>} Diagnostic results
     */
    async runDiagnostics() {
        this.log('Running connectivity diagnostics');

        const results = {
            timestamp: new Date().toISOString(),
            server_reachable: false,
            endpoints: {},
            browser_capabilities: {},
            network_info: {},
            overall_status: 'unknown'
        };

        try {
            // Test server connectivity
            results.server_reachable = await this.testServerConnectivity();
            
            // Test specific endpoints
            results.endpoints = await this.testEndpoints();
            
            // Test browser capabilities
            results.browser_capabilities = this.testBrowserCapabilities();
            
            // Get network information
            results.network_info = this.getNetworkInfo();
            
            // Determine overall status
            results.overall_status = this.determineOverallStatus(results);
            
            this.log('Diagnostics completed', results);
            
        } catch (error) {
            this.log('Diagnostics failed', { error: error.message });
            results.error = error.message;
            results.overall_status = 'error';
        }

        return results;
    }

    /**
     * Check if authentication endpoint is available
     * @returns {Promise<Object>} Auth endpoint status
     */
    async checkAuthEndpoint() {
        this.log('Checking auth endpoint availability');

        try {
            // Test with OPTIONS request first (CORS preflight)
            const optionsResponse = await fetch(`${this.baseURL}/auth/login`, {
                method: 'OPTIONS',
                headers: {
                    'Access-Control-Request-Method': 'POST',
                    'Access-Control-Request-Headers': 'Content-Type'
                }
            });

            const available = optionsResponse.status !== 404;
            
            this.log('Auth endpoint check completed', { 
                available, 
                status: optionsResponse.status 
            });

            return {
                available: available,
                status: optionsResponse.status,
                cors_enabled: optionsResponse.headers.get('Access-Control-Allow-Origin') !== null
            };
        } catch (error) {
            this.log('Auth endpoint check failed', { error: error.message });
            
            return {
                available: false,
                error: error.message,
                cors_enabled: false
            };
        }
    }

    /**
     * Test basic server connectivity
     * @returns {Promise<boolean>} Server reachability status
     */
    async testServerConnectivity() {
        const testUrls = [
            '/health',
            '/api/health',
            '/admin',
            '/'
        ];

        for (const url of testUrls) {
            try {
                const response = await fetch(url, {
                    method: 'GET',
                    cache: 'no-cache',
                    signal: AbortSignal.timeout(5000) // 5 second timeout
                });

                if (response.status < 500) {
                    this.log('Server connectivity confirmed', { url, status: response.status });
                    return true;
                }
            } catch (error) {
                this.log('Server connectivity test failed', { url, error: error.message });
                continue;
            }
        }

        return false;
    }

    /**
     * Test specific API endpoints
     * @returns {Promise<Object>} Endpoint test results
     */
    async testEndpoints() {
        const results = {};

        for (const [name, endpoint] of Object.entries(this.endpoints)) {
            try {
                const startTime = performance.now();
                
                const response = await fetch(endpoint, {
                    method: 'GET',
                    cache: 'no-cache',
                    signal: AbortSignal.timeout(5000)
                });

                const endTime = performance.now();
                const responseTime = Math.round(endTime - startTime);

                results[name] = {
                    available: response.status !== 404,
                    status: response.status,
                    response_time: responseTime,
                    content_type: response.headers.get('content-type')
                };

                this.log(`Endpoint test: ${name}`, results[name]);

            } catch (error) {
                results[name] = {
                    available: false,
                    error: error.message,
                    response_time: null
                };

                this.log(`Endpoint test failed: ${name}`, { error: error.message });
            }
        }

        return results;
    }

    /**
     * Test browser capabilities required for authentication
     * @returns {Object} Browser capability test results
     */
    testBrowserCapabilities() {
        const capabilities = {
            cookies_enabled: navigator.cookieEnabled,
            local_storage_available: this.testLocalStorage(),
            session_storage_available: this.testSessionStorage(),
            fetch_api_available: typeof fetch !== 'undefined',
            json_support: typeof JSON !== 'undefined',
            promises_support: typeof Promise !== 'undefined',
            abort_controller_support: typeof AbortController !== 'undefined',
            javascript_enabled: true // If this runs, JS is enabled
        };

        // Test cookie functionality
        capabilities.cookie_write_test = this.testCookieWrite();
        
        // Test form data support
        capabilities.form_data_support = typeof FormData !== 'undefined';
        
        // Test URL search params support
        capabilities.url_search_params_support = typeof URLSearchParams !== 'undefined';

        this.log('Browser capabilities tested', capabilities);
        
        return capabilities;
    }

    /**
     * Get network and browser information
     * @returns {Object} Network information
     */
    getNetworkInfo() {
        const info = {
            user_agent: navigator.userAgent,
            language: navigator.language,
            platform: navigator.platform,
            online: navigator.onLine,
            connection_type: null,
            effective_type: null
        };

        // Get connection information if available
        if ('connection' in navigator) {
            const connection = navigator.connection;
            info.connection_type = connection.type;
            info.effective_type = connection.effectiveType;
            info.downlink = connection.downlink;
            info.rtt = connection.rtt;
        }

        // Get timezone information
        try {
            info.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        } catch (e) {
            info.timezone = 'unknown';
        }

        return info;
    }

    /**
     * Test localStorage functionality
     * @returns {boolean} LocalStorage availability
     */
    testLocalStorage() {
        try {
            const testKey = '__connectivity_test__';
            localStorage.setItem(testKey, 'test');
            const value = localStorage.getItem(testKey);
            localStorage.removeItem(testKey);
            return value === 'test';
        } catch (e) {
            return false;
        }
    }

    /**
     * Test sessionStorage functionality
     * @returns {boolean} SessionStorage availability
     */
    testSessionStorage() {
        try {
            const testKey = '__connectivity_test__';
            sessionStorage.setItem(testKey, 'test');
            const value = sessionStorage.getItem(testKey);
            sessionStorage.removeItem(testKey);
            return value === 'test';
        } catch (e) {
            return false;
        }
    }

    /**
     * Test cookie write functionality
     * @returns {boolean} Cookie write capability
     */
    testCookieWrite() {
        try {
            const testName = '__connectivity_test__';
            const testValue = 'test';
            
            document.cookie = `${testName}=${testValue}; path=/; SameSite=Strict`;
            
            const cookies = document.cookie.split(';');
            const found = cookies.some(cookie => {
                const [name, value] = cookie.trim().split('=');
                return name === testName && value === testValue;
            });

            // Clean up
            document.cookie = `${testName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
            
            return found;
        } catch (e) {
            return false;
        }
    }

    /**
     * Determine overall connectivity status
     * @param {Object} results - Diagnostic results
     * @returns {string} Overall status
     */
    determineOverallStatus(results) {
        if (!results.server_reachable) {
            return 'server_unreachable';
        }

        if (!results.endpoints.auth_login?.available) {
            return 'auth_endpoint_unavailable';
        }

        if (!results.browser_capabilities.cookies_enabled || 
            !results.browser_capabilities.local_storage_available) {
            return 'browser_capabilities_insufficient';
        }

        if (!results.browser_capabilities.fetch_api_available) {
            return 'fetch_api_unavailable';
        }

        // Check if any critical endpoints are slow
        const authResponseTime = results.endpoints.auth_login?.response_time;
        if (authResponseTime && authResponseTime > 5000) {
            return 'slow_connection';
        }

        return 'healthy';
    }

    /**
     * Get connectivity recommendations based on status
     * @param {string} status - Overall connectivity status
     * @returns {Array} Array of recommendations
     */
    getRecommendations(status) {
        const recommendations = {
            'server_unreachable': [
                'Check your internet connection',
                'Verify the server is running',
                'Check if you\'re behind a firewall or proxy',
                'Try refreshing the page'
            ],
            'auth_endpoint_unavailable': [
                'Contact system administrator',
                'Check if the authentication service is running',
                'Verify API endpoint configuration'
            ],
            'browser_capabilities_insufficient': [
                'Enable cookies in your browser',
                'Enable JavaScript',
                'Update your browser to a newer version',
                'Try using a different browser'
            ],
            'fetch_api_unavailable': [
                'Update your browser to a newer version',
                'Use a modern browser (Chrome, Firefox, Safari, Edge)',
                'Enable JavaScript'
            ],
            'slow_connection': [
                'Check your internet connection speed',
                'Try again when network conditions improve',
                'Contact your network administrator'
            ],
            'healthy': [
                'All systems appear to be working correctly'
            ]
        };

        return recommendations[status] || ['Contact system administrator for assistance'];
    }

    /**
     * Generate connectivity report
     * @returns {Promise<Object>} Comprehensive connectivity report
     */
    async generateReport() {
        const diagnostics = await this.runDiagnostics();
        const recommendations = this.getRecommendations(diagnostics.overall_status);

        return {
            ...diagnostics,
            recommendations: recommendations,
            report_generated_at: new Date().toISOString()
        };
    }

    /**
     * Log debug information
     * @param {string} message - Log message
     * @param {Object} data - Additional data to log
     */
    log(message, data = {}) {
        if (this.debugMode) {
            console.log(`[APIConnectivityChecker] ${message}`, data);
        }
    }
}

// Make available globally
window.APIConnectivityChecker = APIConnectivityChecker;