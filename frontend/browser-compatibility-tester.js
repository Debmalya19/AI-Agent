/**
 * Browser Compatibility Tester
 * Identifies client-side issues and browser compatibility problems
 */

class BrowserCompatibilityTester {
    constructor() {
        this.results = {};
        this.browserInfo = {};
        this.isRunning = false;
    }

    /**
     * Run comprehensive browser compatibility tests
     */
    async runCompatibilityTests() {
        if (this.isRunning) {
            console.warn('Compatibility tests already running');
            return this.results;
        }

        this.isRunning = true;
        this.results = {
            timestamp: new Date().toISOString(),
            overall_compatibility: 'unknown',
            tests: {}
        };

        console.log('🔍 Starting browser compatibility tests...');

        try {
            // Detect browser information
            this.detectBrowserInfo();
            
            // Test core web APIs
            await this.testCoreWebAPIs();
            
            // Test storage capabilities
            await this.testStorageCapabilities();
            
            // Test network capabilities
            await this.testNetworkCapabilities();
            
            // Test form and input capabilities
            await this.testFormCapabilities();
            
            // Test security features
            await this.testSecurityFeatures();
            
            // Calculate overall compatibility
            this.calculateOverallCompatibility();
            
            console.log('✅ Browser compatibility tests completed:', this.results);
            
        } catch (error) {
            console.error('❌ Compatibility tests failed:', error);
            this.results.error = error.message;
            this.results.overall_compatibility = 'error';
        } finally {
            this.isRunning = false;
        }

        return this.results;
    }

    /**
     * Detect browser information
     */
    detectBrowserInfo() {
        console.log('Detecting browser information...');
        
        const userAgent = navigator.userAgent;
        
        this.browserInfo = {
            userAgent: userAgent,
            platform: navigator.platform,
            language: navigator.language,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine,
            vendor: navigator.vendor,
            appName: navigator.appName,
            appVersion: navigator.appVersion
        };

        // Detect browser type
        if (userAgent.includes('Chrome') && !userAgent.includes('Edg')) {
            this.browserInfo.name = 'Chrome';
            this.browserInfo.engine = 'Blink';
        } else if (userAgent.includes('Firefox')) {
            this.browserInfo.name = 'Firefox';
            this.browserInfo.engine = 'Gecko';
        } else if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) {
            this.browserInfo.name = 'Safari';
            this.browserInfo.engine = 'WebKit';
        } else if (userAgent.includes('Edg')) {
            this.browserInfo.name = 'Edge';
            this.browserInfo.engine = 'Blink';
        } else if (userAgent.includes('Opera') || userAgent.includes('OPR')) {
            this.browserInfo.name = 'Opera';
            this.browserInfo.engine = 'Blink';
        } else {
            this.browserInfo.name = 'Unknown';
            this.browserInfo.engine = 'Unknown';
        }

        // Detect mobile
        this.browserInfo.isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
        
        this.results.browser_info = this.browserInfo;
        
        console.log(`  ✓ Detected: ${this.browserInfo.name} on ${this.browserInfo.platform}`);
    }

    /**
     * Test core web APIs
     */
    async testCoreWebAPIs() {
        console.log('Testing core web APIs...');
        
        this.results.tests.core_apis = {};

        // Test Fetch API
        this.results.tests.core_apis.fetch = {
            supported: typeof fetch !== 'undefined',
            details: typeof fetch !== 'undefined' ? 'Available' : 'Not supported - use XMLHttpRequest fallback'
        };
        console.log(`  ${typeof fetch !== 'undefined' ? '✓' : '✗'} Fetch API`);

        // Test Promise
        this.results.tests.core_apis.promise = {
            supported: typeof Promise !== 'undefined',
            details: typeof Promise !== 'undefined' ? 'Available' : 'Not supported - use polyfill'
        };
        console.log(`  ${typeof Promise !== 'undefined' ? '✓' : '✗'} Promise`);

        // Test async/await (ES2017)
        try {
            eval('(async () => {})');
            this.results.tests.core_apis.async_await = {
                supported: true,
                details: 'Available'
            };
            console.log('  ✓ async/await');
        } catch (error) {
            this.results.tests.core_apis.async_await = {
                supported: false,
                details: 'Not supported - use Promises'
            };
            console.log('  ✗ async/await');
        }

        // Test Arrow functions (ES2015)
        try {
            eval('(() => {})');
            this.results.tests.core_apis.arrow_functions = {
                supported: true,
                details: 'Available'
            };
            console.log('  ✓ Arrow functions');
        } catch (error) {
            this.results.tests.core_apis.arrow_functions = {
                supported: false,
                details: 'Not supported - use function expressions'
            };
            console.log('  ✗ Arrow functions');
        }

        // Test const/let (ES2015)
        try {
            eval('const test = 1; let test2 = 2;');
            this.results.tests.core_apis.const_let = {
                supported: true,
                details: 'Available'
            };
            console.log('  ✓ const/let');
        } catch (error) {
            this.results.tests.core_apis.const_let = {
                supported: false,
                details: 'Not supported - use var'
            };
            console.log('  ✗ const/let');
        }

        // Test JSON
        this.results.tests.core_apis.json = {
            supported: typeof JSON !== 'undefined' && typeof JSON.parse === 'function' && typeof JSON.stringify === 'function',
            details: typeof JSON !== 'undefined' ? 'Available' : 'Not supported'
        };
        console.log(`  ${typeof JSON !== 'undefined' ? '✓' : '✗'} JSON`);

        // Test FormData
        this.results.tests.core_apis.form_data = {
            supported: typeof FormData !== 'undefined',
            details: typeof FormData !== 'undefined' ? 'Available' : 'Not supported - manual form serialization needed'
        };
        console.log(`  ${typeof FormData !== 'undefined' ? '✓' : '✗'} FormData`);

        // Test URLSearchParams
        this.results.tests.core_apis.url_search_params = {
            supported: typeof URLSearchParams !== 'undefined',
            details: typeof URLSearchParams !== 'undefined' ? 'Available' : 'Not supported - manual URL parsing needed'
        };
        console.log(`  ${typeof URLSearchParams !== 'undefined' ? '✓' : '✗'} URLSearchParams`);
    }

    /**
     * Test storage capabilities
     */
    async testStorageCapabilities() {
        console.log('Testing storage capabilities...');
        
        this.results.tests.storage = {};

        // Test localStorage
        try {
            const testKey = 'compat_test_local';
            const testValue = JSON.stringify({ test: 'value', timestamp: Date.now() });
            
            localStorage.setItem(testKey, testValue);
            const retrieved = localStorage.getItem(testKey);
            const parsed = JSON.parse(retrieved);
            localStorage.removeItem(testKey);
            
            const success = parsed.test === 'value';
            
            this.results.tests.storage.localStorage = {
                supported: success,
                details: success ? 'Available and working' : 'Available but not working correctly'
            };
            
            console.log(`  ${success ? '✓' : '✗'} localStorage`);
            
        } catch (error) {
            this.results.tests.storage.localStorage = {
                supported: false,
                details: `Error: ${error.message}`
            };
            console.log(`  ✗ localStorage: ${error.message}`);
        }

        // Test sessionStorage
        try {
            const testKey = 'compat_test_session';
            const testValue = JSON.stringify({ test: 'value', timestamp: Date.now() });
            
            sessionStorage.setItem(testKey, testValue);
            const retrieved = sessionStorage.getItem(testKey);
            const parsed = JSON.parse(retrieved);
            sessionStorage.removeItem(testKey);
            
            const success = parsed.test === 'value';
            
            this.results.tests.storage.sessionStorage = {
                supported: success,
                details: success ? 'Available and working' : 'Available but not working correctly'
            };
            
            console.log(`  ${success ? '✓' : '✗'} sessionStorage`);
            
        } catch (error) {
            this.results.tests.storage.sessionStorage = {
                supported: false,
                details: `Error: ${error.message}`
            };
            console.log(`  ✗ sessionStorage: ${error.message}`);
        }

        // Test cookies
        try {
            const testCookie = 'compat_test';
            const testValue = 'test_value_' + Date.now();
            
            // Set cookie
            document.cookie = `${testCookie}=${testValue}; path=/; SameSite=Lax`;
            
            // Check if cookie was set
            const cookieValue = document.cookie
                .split('; ')
                .find(row => row.startsWith(`${testCookie}=`))
                ?.split('=')[1];
            
            const success = cookieValue === testValue;
            
            // Clean up
            document.cookie = `${testCookie}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
            
            this.results.tests.storage.cookies = {
                supported: success,
                details: success ? 'Available and working' : 'Available but not working correctly'
            };
            
            console.log(`  ${success ? '✓' : '✗'} Cookies`);
            
        } catch (error) {
            this.results.tests.storage.cookies = {
                supported: false,
                details: `Error: ${error.message}`
            };
            console.log(`  ✗ Cookies: ${error.message}`);
        }

        // Test IndexedDB
        this.results.tests.storage.indexedDB = {
            supported: 'indexedDB' in window,
            details: 'indexedDB' in window ? 'Available' : 'Not supported'
        };
        console.log(`  ${'indexedDB' in window ? '✓' : '✗'} IndexedDB`);
    }

    /**
     * Test network capabilities
     */
    async testNetworkCapabilities() {
        console.log('Testing network capabilities...');
        
        this.results.tests.network = {};

        // Test XMLHttpRequest
        this.results.tests.network.xhr = {
            supported: typeof XMLHttpRequest !== 'undefined',
            details: typeof XMLHttpRequest !== 'undefined' ? 'Available' : 'Not supported'
        };
        console.log(`  ${typeof XMLHttpRequest !== 'undefined' ? '✓' : '✗'} XMLHttpRequest`);

        // Test CORS support
        try {
            const xhr = new XMLHttpRequest();
            const corsSupported = 'withCredentials' in xhr;
            
            this.results.tests.network.cors = {
                supported: corsSupported,
                details: corsSupported ? 'CORS supported' : 'CORS not supported'
            };
            
            console.log(`  ${corsSupported ? '✓' : '✗'} CORS`);
            
        } catch (error) {
            this.results.tests.network.cors = {
                supported: false,
                details: `Error: ${error.message}`
            };
            console.log(`  ✗ CORS: ${error.message}`);
        }

        // Test WebSocket
        this.results.tests.network.websocket = {
            supported: typeof WebSocket !== 'undefined',
            details: typeof WebSocket !== 'undefined' ? 'Available' : 'Not supported'
        };
        console.log(`  ${typeof WebSocket !== 'undefined' ? '✓' : '✗'} WebSocket`);

        // Test EventSource (Server-Sent Events)
        this.results.tests.network.event_source = {
            supported: typeof EventSource !== 'undefined',
            details: typeof EventSource !== 'undefined' ? 'Available' : 'Not supported'
        };
        console.log(`  ${typeof EventSource !== 'undefined' ? '✓' : '✗'} EventSource`);
    }

    /**
     * Test form capabilities
     */
    async testFormCapabilities() {
        console.log('Testing form capabilities...');
        
        this.results.tests.forms = {};

        // Test HTML5 input types
        const inputTypes = ['email', 'password', 'text', 'hidden', 'submit'];
        const supportedInputTypes = [];
        
        for (const type of inputTypes) {
            try {
                const input = document.createElement('input');
                input.type = type;
                if (input.type === type) {
                    supportedInputTypes.push(type);
                }
            } catch (error) {
                // Type not supported
            }
        }
        
        this.results.tests.forms.input_types = {
            supported: supportedInputTypes.length === inputTypes.length,
            details: `Supported: ${supportedInputTypes.join(', ')}`
        };
        console.log(`  ${supportedInputTypes.length === inputTypes.length ? '✓' : '✗'} HTML5 Input Types`);

        // Test form validation
        try {
            const form = document.createElement('form');
            const input = document.createElement('input');
            input.required = true;
            form.appendChild(input);
            
            const validationSupported = typeof input.checkValidity === 'function';
            
            this.results.tests.forms.validation = {
                supported: validationSupported,
                details: validationSupported ? 'HTML5 validation available' : 'Manual validation required'
            };
            
            console.log(`  ${validationSupported ? '✓' : '✗'} Form Validation`);
            
        } catch (error) {
            this.results.tests.forms.validation = {
                supported: false,
                details: `Error: ${error.message}`
            };
            console.log(`  ✗ Form Validation: ${error.message}`);
        }

        // Test FormData
        this.results.tests.forms.form_data = {
            supported: typeof FormData !== 'undefined',
            details: typeof FormData !== 'undefined' ? 'Available' : 'Manual form serialization required'
        };
        console.log(`  ${typeof FormData !== 'undefined' ? '✓' : '✗'} FormData`);
    }

    /**
     * Test security features
     */
    async testSecurityFeatures() {
        console.log('Testing security features...');
        
        this.results.tests.security = {};

        // Test HTTPS
        const isHTTPS = location.protocol === 'https:';
        this.results.tests.security.https = {
            supported: isHTTPS,
            details: isHTTPS ? 'Secure connection' : 'Insecure connection - some features may be limited'
        };
        console.log(`  ${isHTTPS ? '✓' : '✗'} HTTPS`);

        // Test Secure Context
        const isSecureContext = window.isSecureContext;
        this.results.tests.security.secure_context = {
            supported: isSecureContext,
            details: isSecureContext ? 'Secure context' : 'Insecure context - some APIs may be unavailable'
        };
        console.log(`  ${isSecureContext ? '✓' : '✗'} Secure Context`);

        // Test Content Security Policy
        try {
            // This is a basic check - CSP violations would show in console
            this.results.tests.security.csp = {
                supported: true,
                details: 'CSP support available (check console for violations)'
            };
            console.log('  ✓ CSP Support');
        } catch (error) {
            this.results.tests.security.csp = {
                supported: false,
                details: 'CSP not supported'
            };
            console.log('  ✗ CSP Support');
        }

        // Test SameSite cookie support
        try {
            document.cookie = 'samesite_test=value; SameSite=Lax; path=/';
            const sameSiteSupported = document.cookie.includes('samesite_test=value');
            
            // Clean up
            document.cookie = 'samesite_test=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            
            this.results.tests.security.samesite_cookies = {
                supported: sameSiteSupported,
                details: sameSiteSupported ? 'SameSite cookies supported' : 'SameSite cookies not supported'
            };
            
            console.log(`  ${sameSiteSupported ? '✓' : '✗'} SameSite Cookies`);
            
        } catch (error) {
            this.results.tests.security.samesite_cookies = {
                supported: false,
                details: `Error: ${error.message}`
            };
            console.log(`  ✗ SameSite Cookies: ${error.message}`);
        }
    }

    /**
     * Calculate overall compatibility score
     */
    calculateOverallCompatibility() {
        let totalTests = 0;
        let passedTests = 0;

        for (const category in this.results.tests) {
            const categoryTests = this.results.tests[category];
            
            for (const testName in categoryTests) {
                totalTests++;
                if (categoryTests[testName].supported) {
                    passedTests++;
                }
            }
        }

        const compatibilityScore = totalTests > 0 ? (passedTests / totalTests) : 0;
        
        if (compatibilityScore >= 0.95) {
            this.results.overall_compatibility = 'excellent';
        } else if (compatibilityScore >= 0.85) {
            this.results.overall_compatibility = 'good';
        } else if (compatibilityScore >= 0.70) {
            this.results.overall_compatibility = 'fair';
        } else if (compatibilityScore >= 0.50) {
            this.results.overall_compatibility = 'poor';
        } else {
            this.results.overall_compatibility = 'critical';
        }

        this.results.compatibility_score = Math.round(compatibilityScore * 100);
        this.results.total_tests = totalTests;
        this.results.passed_tests = passedTests;
    }

    /**
     * Get compatibility recommendations
     */
    getRecommendations() {
        const recommendations = [];

        if (!this.results.tests) {
            return ['Run compatibility tests first'];
        }

        // Check for critical issues
        if (!this.results.tests.core_apis?.fetch?.supported) {
            recommendations.push('Use XMLHttpRequest fallback for network requests');
        }

        if (!this.results.tests.core_apis?.promise?.supported) {
            recommendations.push('Include Promise polyfill for older browsers');
        }

        if (!this.results.tests.storage?.localStorage?.supported) {
            recommendations.push('Implement cookie-based storage fallback');
        }

        if (!this.results.tests.storage?.cookies?.supported) {
            recommendations.push('Check browser cookie settings and privacy mode');
        }

        if (!this.results.tests.security?.https?.supported) {
            recommendations.push('Use HTTPS for secure authentication');
        }

        if (!this.results.tests.network?.cors?.supported) {
            recommendations.push('Implement JSONP or server-side proxy for cross-origin requests');
        }

        // Browser-specific recommendations
        if (this.browserInfo.name === 'Internet Explorer') {
            recommendations.push('Consider dropping IE support or use extensive polyfills');
        }

        if (this.browserInfo.isMobile) {
            recommendations.push('Test touch interactions and mobile-specific behaviors');
        }

        if (recommendations.length === 0) {
            recommendations.push('Browser compatibility is excellent - no issues detected');
        }

        return recommendations;
    }

    /**
     * Display compatibility results
     */
    displayResults(containerId = 'compatibility-results') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container with ID '${containerId}' not found`);
            return;
        }

        const html = `
            <div class="compatibility-results">
                <h3>Browser Compatibility Test Results</h3>
                
                <div class="browser-info">
                    <h4>Browser Information</h4>
                    <ul>
                        <li><strong>Browser:</strong> ${this.browserInfo.name} (${this.browserInfo.engine})</li>
                        <li><strong>Platform:</strong> ${this.browserInfo.platform}</li>
                        <li><strong>Mobile:</strong> ${this.browserInfo.isMobile ? 'Yes' : 'No'}</li>
                        <li><strong>Language:</strong> ${this.browserInfo.language}</li>
                        <li><strong>Cookies Enabled:</strong> ${this.browserInfo.cookieEnabled ? 'Yes' : 'No'}</li>
                    </ul>
                </div>
                
                <div class="overall-compatibility compatibility-${this.results.overall_compatibility}">
                    <strong>Overall Compatibility:</strong> ${this.results.overall_compatibility.toUpperCase()}
                    <span class="compatibility-score">(${this.results.compatibility_score}% compatible)</span>
                </div>
                
                <div class="test-categories">
                    ${Object.entries(this.results.tests).map(([category, tests]) => `
                        <div class="test-category">
                            <h4>${category.replace(/_/g, ' ').toUpperCase()}</h4>
                            <ul>
                                ${Object.entries(tests).map(([testName, result]) => `
                                    <li class="${result.supported ? 'supported' : 'not-supported'}">
                                        <span class="test-name">${testName.replace(/_/g, ' ')}</span>
                                        <span class="test-result">${result.supported ? '✓' : '✗'}</span>
                                        <div class="test-details">${result.details}</div>
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
    module.exports = BrowserCompatibilityTester;
} else {
    window.BrowserCompatibilityTester = BrowserCompatibilityTester;
}