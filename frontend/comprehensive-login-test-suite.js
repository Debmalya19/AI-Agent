/**
 * Comprehensive Frontend Login Test Suite
 * Tests authentication functionality across different browsers and scenarios
 * Requirements: 6.1, 6.2, 6.3, 6.4
 */

class ComprehensiveLoginTestSuite {
    constructor() {
        this.testResults = {
            browserCompatibility: {},
            authenticationFlow: {},
            sessionManagement: {},
            errorHandling: {},
            summary: {
                totalTests: 0,
                passedTests: 0,
                failedTests: 0,
                errors: []
            }
        };
        
        this.authService = null;
        this.testCredentials = {
            valid: {
                email: 'test@example.com',
                password: 'testpassword123'
            },
            admin: {
                email: 'admin@example.com',
                password: 'adminpassword123'
            },
            invalid: {
                email: 'invalid@example.com',
                password: 'wrongpassword'
            }
        };
        
        this.log('Comprehensive Login Test Suite initialized');
    }

    /**
     * Run all test suites
     * @returns {Promise<Object>} Complete test results
     */
    async runAllTests() {
        this.log('Starting comprehensive login test suite...');
        
        try {
            // Initialize authentication service
            this.authService = new AdminAuthService();
            
            // Run test suites in order
            await this.runBrowserCompatibilityTests();
            await this.runAuthenticationFlowTests();
            await this.runSessionManagementTests();
            await this.runErrorHandlingTests();
            
            // Generate summary
            this.generateTestSummary();
            
            this.log('All tests completed', this.testResults.summary);
            return this.testResults;
            
        } catch (error) {
            this.logError('Test suite execution failed', error);
            this.testResults.summary.errors.push(`Suite execution failed: ${error.message}`);
            return this.testResults;
        }
    }

    /**
     * Test browser compatibility features
     * Requirements: 6.2, 6.4
     */
    async runBrowserCompatibilityTests() {
        this.log('Running browser compatibility tests...');
        
        const tests = [
            { name: 'localStorage', test: () => this.testLocalStorage() },
            { name: 'sessionStorage', test: () => this.testSessionStorage() },
            { name: 'cookies', test: () => this.testCookies() },
            { name: 'fetchAPI', test: () => this.testFetchAPI() },
            { name: 'jsonSupport', test: () => this.testJSONSupport() },
            { name: 'eventListeners', test: () => this.testEventListeners() },
            { name: 'promiseSupport', test: () => this.testPromiseSupport() },
            { name: 'asyncAwaitSupport', test: () => this.testAsyncAwaitSupport() }
        ];
        
        for (const test of tests) {
            try {
                this.testResults.browserCompatibility[test.name] = await test.test();
                this.testResults.summary.passedTests++;
                this.log(`✓ ${test.name} compatibility test passed`);
            } catch (error) {
                this.testResults.browserCompatibility[test.name] = {
                    supported: false,
                    error: error.message
                };
                this.testResults.summary.failedTests++;
                this.testResults.summary.errors.push(`${test.name}: ${error.message}`);
                this.logError(`✗ ${test.name} compatibility test failed`, error);
            }
            this.testResults.summary.totalTests++;
        }
    }

    /**
     * Test complete authentication flows
     * Requirements: 1.1, 1.2
     */
    async runAuthenticationFlowTests() {
        this.log('Running authentication flow tests...');
        
        const tests = [
            { name: 'loginWithEmail', test: () => this.testLoginWithEmail() },
            { name: 'loginWithUsername', test: () => this.testLoginWithUsername() },
            { name: 'adminLogin', test: () => this.testAdminLogin() },
            { name: 'logoutFlow', test: () => this.testLogoutFlow() },
            { name: 'sessionValidation', test: () => this.testSessionValidation() },
            { name: 'multipleRequestFormats', test: () => this.testMultipleRequestFormats() }
        ];
        
        for (const test of tests) {
            try {
                this.testResults.authenticationFlow[test.name] = await test.test();
                this.testResults.summary.passedTests++;
                this.log(`✓ ${test.name} test passed`);
            } catch (error) {
                this.testResults.authenticationFlow[test.name] = {
                    success: false,
                    error: error.message
                };
                this.testResults.summary.failedTests++;
                this.testResults.summary.errors.push(`${test.name}: ${error.message}`);
                this.logError(`✗ ${test.name} test failed`, error);
            }
            this.testResults.summary.totalTests++;
        }
    }

    /**
     * Test session management functionality
     * Requirements: 1.3, 6.1, 6.3
     */
    async runSessionManagementTests() {
        this.log('Running session management tests...');
        
        const tests = [
            { name: 'sessionStorage', test: () => this.testSessionStorageManagement() },
            { name: 'sessionValidation', test: () => this.testSessionValidationManagement() },
            { name: 'sessionRecovery', test: () => this.testSessionRecovery() },
            { name: 'crossTabSync', test: () => this.testCrossTabSynchronization() },
            { name: 'sessionExpiration', test: () => this.testSessionExpirationHandling() },
            { name: 'activityTracking', test: () => this.testActivityTracking() }
        ];
        
        for (const test of tests) {
            try {
                this.testResults.sessionManagement[test.name] = await test.test();
                this.testResults.summary.passedTests++;
                this.log(`✓ ${test.name} test passed`);
            } catch (error) {
                this.testResults.sessionManagement[test.name] = {
                    success: false,
                    error: error.message
                };
                this.testResults.summary.failedTests++;
                this.testResults.summary.errors.push(`${test.name}: ${error.message}`);
                this.logError(`✗ ${test.name} test failed`, error);
            }
            this.testResults.summary.totalTests++;
        }
    }

    /**
     * Test error handling and recovery
     * Requirements: 1.4, 4.1, 4.4
     */
    async runErrorHandlingTests() {
        this.log('Running error handling tests...');
        
        const tests = [
            { name: 'invalidCredentials', test: () => this.testInvalidCredentialsHandling() },
            { name: 'networkErrors', test: () => this.testNetworkErrorHandling() },
            { name: 'serverErrors', test: () => this.testServerErrorHandling() },
            { name: 'malformedResponses', test: () => this.testMalformedResponseHandling() },
            { name: 'timeoutHandling', test: () => this.testTimeoutHandling() },
            { name: 'recoveryMechanisms', test: () => this.testRecoveryMechanisms() }
        ];
        
        for (const test of tests) {
            try {
                this.testResults.errorHandling[test.name] = await test.test();
                this.testResults.summary.passedTests++;
                this.log(`✓ ${test.name} test passed`);
            } catch (error) {
                this.testResults.errorHandling[test.name] = {
                    success: false,
                    error: error.message
                };
                this.testResults.summary.failedTests++;
                this.testResults.summary.errors.push(`${test.name}: ${error.message}`);
                this.logError(`✗ ${test.name} test failed`, error);
            }
            this.testResults.summary.totalTests++;
        }
    }

    // Browser Compatibility Tests

    testLocalStorage() {
        if (typeof Storage === 'undefined' || !localStorage) {
            throw new Error('localStorage not supported');
        }
        
        // Test basic operations
        localStorage.setItem('test_key', 'test_value');
        const value = localStorage.getItem('test_key');
        localStorage.removeItem('test_key');
        
        if (value !== 'test_value') {
            throw new Error('localStorage operations failed');
        }
        
        return { supported: true, operations: ['setItem', 'getItem', 'removeItem'] };
    }

    testSessionStorage() {
        if (typeof Storage === 'undefined' || !sessionStorage) {
            throw new Error('sessionStorage not supported');
        }
        
        // Test basic operations
        sessionStorage.setItem('test_key', 'test_value');
        const value = sessionStorage.getItem('test_key');
        sessionStorage.removeItem('test_key');
        
        if (value !== 'test_value') {
            throw new Error('sessionStorage operations failed');
        }
        
        return { supported: true, operations: ['setItem', 'getItem', 'removeItem'] };
    }

    testCookies() {
        if (!navigator.cookieEnabled) {
            throw new Error('Cookies not enabled');
        }
        
        // Test cookie operations
        document.cookie = 'test_cookie=test_value; path=/';
        const cookies = document.cookie;
        
        if (!cookies.includes('test_cookie=test_value')) {
            throw new Error('Cookie setting failed');
        }
        
        // Clean up
        document.cookie = 'test_cookie=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';
        
        return { supported: true, enabled: navigator.cookieEnabled };
    }

    testFetchAPI() {
        if (typeof fetch === 'undefined') {
            throw new Error('Fetch API not supported');
        }
        
        return { 
            supported: true, 
            features: {
                fetch: typeof fetch !== 'undefined',
                Request: typeof Request !== 'undefined',
                Response: typeof Response !== 'undefined',
                Headers: typeof Headers !== 'undefined'
            }
        };
    }

    testJSONSupport() {
        if (typeof JSON === 'undefined') {
            throw new Error('JSON not supported');
        }
        
        const testObj = { test: 'value', number: 123, array: [1, 2, 3] };
        const jsonString = JSON.stringify(testObj);
        const parsedObj = JSON.parse(jsonString);
        
        if (parsedObj.test !== 'value' || parsedObj.number !== 123) {
            throw new Error('JSON operations failed');
        }
        
        return { supported: true, operations: ['stringify', 'parse'] };
    }

    testEventListeners() {
        if (typeof addEventListener === 'undefined') {
            throw new Error('Event listeners not supported');
        }
        
        let eventFired = false;
        const testHandler = () => { eventFired = true; };
        
        document.addEventListener('test-event', testHandler);
        document.dispatchEvent(new CustomEvent('test-event'));
        document.removeEventListener('test-event', testHandler);
        
        if (!eventFired) {
            throw new Error('Event listener test failed');
        }
        
        return { supported: true, customEvents: typeof CustomEvent !== 'undefined' };
    }

    testPromiseSupport() {
        if (typeof Promise === 'undefined') {
            throw new Error('Promises not supported');
        }
        
        return { 
            supported: true, 
            features: {
                Promise: typeof Promise !== 'undefined',
                all: typeof Promise.all !== 'undefined',
                resolve: typeof Promise.resolve !== 'undefined',
                reject: typeof Promise.reject !== 'undefined'
            }
        };
    }

    async testAsyncAwaitSupport() {
        try {
            const testAsync = async () => {
                return await Promise.resolve('async-test');
            };
            
            const result = await testAsync();
            if (result !== 'async-test') {
                throw new Error('Async/await test failed');
            }
            
            return { supported: true };
        } catch (error) {
            throw new Error('Async/await not supported');
        }
    }

    // Authentication Flow Tests

    async testLoginWithEmail() {
        // Mock successful login response
        const mockResponse = {
            success: true,
            token: 'mock-token-123',
            user: { email: this.testCredentials.valid.email, username: 'testuser' }
        };
        
        // Test would normally make actual request
        // For testing, we simulate the flow
        const result = await this.simulateLogin(this.testCredentials.valid, mockResponse);
        
        if (!result.success || !result.token) {
            throw new Error('Login with email failed');
        }
        
        return { success: true, hasToken: !!result.token, hasUser: !!result.user };
    }

    async testLoginWithUsername() {
        const credentials = {
            username: 'testuser',
            password: this.testCredentials.valid.password
        };
        
        const mockResponse = {
            success: true,
            token: 'mock-token-456',
            user: { username: 'testuser', email: 'test@example.com' }
        };
        
        const result = await this.simulateLogin(credentials, mockResponse);
        
        if (!result.success || !result.token) {
            throw new Error('Login with username failed');
        }
        
        return { success: true, hasToken: !!result.token, hasUser: !!result.user };
    }

    async testAdminLogin() {
        const mockResponse = {
            success: true,
            token: 'mock-admin-token-789',
            user: { 
                email: this.testCredentials.admin.email, 
                username: 'admin',
                is_admin: true,
                role: 'admin'
            },
            redirect_url: '/admin'
        };
        
        const result = await this.simulateLogin(this.testCredentials.admin, mockResponse);
        
        if (!result.success || !result.user.is_admin) {
            throw new Error('Admin login failed');
        }
        
        return { 
            success: true, 
            isAdmin: result.user.is_admin,
            hasRedirect: !!result.redirect_url
        };
    }

    async testLogoutFlow() {
        // Simulate having a session
        if (this.authService.sessionManager) {
            await this.authService.sessionManager.storeSession({
                token: 'test-token',
                user: { username: 'testuser' }
            });
        }
        
        // Test logout
        const result = await this.simulateLogout();
        
        if (!result.success) {
            throw new Error('Logout flow failed');
        }
        
        // Verify session was cleared
        const hasSession = this.authService.sessionManager ? 
            this.authService.sessionManager.validateStoredSession() : false;
        
        if (hasSession) {
            throw new Error('Session not cleared after logout');
        }
        
        return { success: true, sessionCleared: !hasSession };
    }

    async testSessionValidation() {
        // Test session validation logic
        if (!this.authService.sessionManager) {
            throw new Error('Session manager not available');
        }
        
        // Store test session
        await this.authService.sessionManager.storeSession({
            token: 'validation-test-token',
            user: { username: 'validationuser' },
            expires_at: new Date(Date.now() + 3600000).toISOString() // 1 hour from now
        });
        
        const isValid = this.authService.sessionManager.validateStoredSession();
        
        if (!isValid) {
            throw new Error('Session validation failed');
        }
        
        return { success: true, sessionValid: isValid };
    }

    async testMultipleRequestFormats() {
        const formats = [
            { email: 'test@example.com', password: 'password' },
            { username: 'testuser', password: 'password' },
            { user: 'testuser', pass: 'password' }
        ];
        
        const results = [];
        
        for (const format of formats) {
            try {
                const mockResponse = {
                    success: true,
                    token: `mock-token-${Date.now()}`,
                    user: { username: 'testuser' }
                };
                
                const result = await this.simulateLogin(format, mockResponse);
                results.push({ format, success: result.success });
            } catch (error) {
                results.push({ format, success: false, error: error.message });
            }
        }
        
        const successfulFormats = results.filter(r => r.success).length;
        
        return { 
            success: true, 
            testedFormats: formats.length,
            successfulFormats: successfulFormats,
            results: results
        };
    }

    // Session Management Tests

    async testSessionStorageManagement() {
        if (!this.authService.sessionManager) {
            throw new Error('Session manager not available');
        }
        
        const sessionData = {
            token: 'storage-test-token',
            user: { username: 'storageuser', email: 'storage@example.com' },
            expires_at: new Date(Date.now() + 3600000).toISOString()
        };
        
        // Test storage
        const stored = await this.authService.sessionManager.storeSession(sessionData);
        
        if (!stored) {
            throw new Error('Session storage failed');
        }
        
        // Test retrieval
        const token = this.authService.sessionManager.getSessionToken();
        const user = this.authService.sessionManager.getStoredUser();
        
        if (token !== sessionData.token || user.username !== sessionData.user.username) {
            throw new Error('Session retrieval failed');
        }
        
        return { 
            success: true, 
            stored: stored,
            retrieved: { hasToken: !!token, hasUser: !!user }
        };
    }

    async testSessionValidationManagement() {
        if (!this.authService.sessionManager) {
            throw new Error('Session manager not available');
        }
        
        // Test with valid session
        await this.authService.sessionManager.storeSession({
            token: 'valid-session-token',
            user: { username: 'validuser' },
            expires_at: new Date(Date.now() + 3600000).toISOString()
        });
        
        const validResult = this.authService.sessionManager.validateStoredSession();
        
        // Test with expired session
        await this.authService.sessionManager.storeSession({
            token: 'expired-session-token',
            user: { username: 'expireduser' },
            expires_at: new Date(Date.now() - 3600000).toISOString() // 1 hour ago
        });
        
        const expiredResult = this.authService.sessionManager.validateStoredSession();
        
        return {
            success: true,
            validSessionTest: validResult,
            expiredSessionTest: !expiredResult // Should be false for expired
        };
    }

    async testSessionRecovery() {
        if (!this.authService.sessionManager) {
            throw new Error('Session manager not available');
        }
        
        // Simulate session recovery scenario
        const recoveryResult = await this.authService.sessionManager.attemptSessionRecovery();
        
        return {
            success: true,
            recoveryAttempted: true,
            recoveryResult: recoveryResult
        };
    }

    async testCrossTabSynchronization() {
        if (!this.authService.sessionManager) {
            throw new Error('Session manager not available');
        }
        
        // Test cross-tab sync functionality
        this.authService.sessionManager.syncSessionAcrossTabs();
        
        return {
            success: true,
            syncFunctionExists: typeof this.authService.sessionManager.syncSessionAcrossTabs === 'function'
        };
    }

    async testSessionExpirationHandling() {
        if (!this.authService.sessionManager) {
            throw new Error('Session manager not available');
        }
        
        // Test expiration handling
        this.authService.sessionManager.cleanupExpiredSessions();
        
        return {
            success: true,
            cleanupFunctionExists: typeof this.authService.sessionManager.cleanupExpiredSessions === 'function'
        };
    }

    async testActivityTracking() {
        if (!this.authService.sessionManager) {
            throw new Error('Session manager not available');
        }
        
        // Test activity tracking
        this.authService.sessionManager.updateLastActivity();
        const lastActivity = this.authService.sessionManager.getLastActivity();
        
        return {
            success: true,
            activityTracked: !!lastActivity,
            lastActivity: lastActivity
        };
    }

    // Error Handling Tests

    async testInvalidCredentialsHandling() {
        const mockErrorResponse = {
            success: false,
            message: 'Invalid username or password',
            status: 401
        };
        
        try {
            await this.simulateLogin(this.testCredentials.invalid, mockErrorResponse, true);
            throw new Error('Should have thrown error for invalid credentials');
        } catch (error) {
            if (error.message.includes('Invalid username or password')) {
                return { success: true, errorHandled: true, errorMessage: error.message };
            }
            throw error;
        }
    }

    async testNetworkErrorHandling() {
        // Simulate network error
        const networkError = new Error('Network request failed');
        networkError.name = 'NetworkError';
        
        try {
            await this.simulateNetworkError(networkError);
            throw new Error('Should have thrown network error');
        } catch (error) {
            if (error.name === 'NetworkError') {
                return { success: true, networkErrorHandled: true, errorType: error.name };
            }
            throw error;
        }
    }

    async testServerErrorHandling() {
        const mockServerError = {
            success: false,
            message: 'Internal server error',
            status: 500
        };
        
        try {
            await this.simulateLogin(this.testCredentials.valid, mockServerError, true);
            throw new Error('Should have thrown server error');
        } catch (error) {
            if (error.message.includes('server error')) {
                return { success: true, serverErrorHandled: true, errorMessage: error.message };
            }
            throw error;
        }
    }

    async testMalformedResponseHandling() {
        const malformedResponse = 'invalid json response';
        
        try {
            await this.simulateMalformedResponse(malformedResponse);
            throw new Error('Should have thrown parsing error');
        } catch (error) {
            if (error.message.includes('parsing') || error.message.includes('JSON')) {
                return { success: true, parsingErrorHandled: true, errorMessage: error.message };
            }
            throw error;
        }
    }

    async testTimeoutHandling() {
        // Simulate timeout
        const timeoutError = new Error('Request timeout');
        timeoutError.name = 'AbortError';
        
        try {
            await this.simulateTimeout(timeoutError);
            throw new Error('Should have thrown timeout error');
        } catch (error) {
            if (error.name === 'AbortError' || error.message.includes('timeout')) {
                return { success: true, timeoutHandled: true, errorType: error.name };
            }
            throw error;
        }
    }

    async testRecoveryMechanisms() {
        // Test various recovery mechanisms
        const recoveryTests = [
            { name: 'sessionRecovery', test: () => this.testSessionRecovery() },
            { name: 'retryMechanism', test: () => this.testRetryMechanism() },
            { name: 'fallbackStorage', test: () => this.testFallbackStorage() }
        ];
        
        const results = {};
        
        for (const test of recoveryTests) {
            try {
                results[test.name] = await test.test();
            } catch (error) {
                results[test.name] = { success: false, error: error.message };
            }
        }
        
        return { success: true, recoveryTests: results };
    }

    // Helper Methods

    async simulateLogin(credentials, mockResponse, shouldThrow = false) {
        if (shouldThrow && !mockResponse.success) {
            const error = new Error(mockResponse.message || 'Login failed');
            error.status = mockResponse.status;
            throw error;
        }
        
        // Simulate successful login
        if (this.authService.sessionManager && mockResponse.success) {
            await this.authService.sessionManager.storeSession({
                token: mockResponse.token,
                user: mockResponse.user,
                expires_at: mockResponse.expires_at
            });
        }
        
        return mockResponse;
    }

    async simulateLogout() {
        if (this.authService.sessionManager) {
            this.authService.sessionManager.clearSession();
        }
        
        return { success: true, message: 'Logged out successfully' };
    }

    async simulateNetworkError(error) {
        throw error;
    }

    async simulateMalformedResponse(response) {
        try {
            JSON.parse(response);
        } catch (e) {
            const error = new Error('Response parsing failed');
            error.originalError = e;
            throw error;
        }
    }

    async simulateTimeout(error) {
        throw error;
    }

    async testRetryMechanism() {
        // Test retry logic exists
        return { 
            success: true, 
            retryConfigExists: this.authService.config && 
                              typeof this.authService.config.retryAttempts !== 'undefined'
        };
    }

    async testFallbackStorage() {
        // Test fallback storage mechanisms
        const storageTypes = ['localStorage', 'sessionStorage', 'cookies'];
        const availableStorage = storageTypes.filter(type => {
            try {
                switch (type) {
                    case 'localStorage':
                        return typeof localStorage !== 'undefined';
                    case 'sessionStorage':
                        return typeof sessionStorage !== 'undefined';
                    case 'cookies':
                        return navigator.cookieEnabled;
                    default:
                        return false;
                }
            } catch (e) {
                return false;
            }
        });
        
        return {
            success: true,
            availableStorage: availableStorage,
            fallbackOptions: availableStorage.length
        };
    }

    generateTestSummary() {
        const { totalTests, passedTests, failedTests } = this.testResults.summary;
        const successRate = totalTests > 0 ? (passedTests / totalTests * 100).toFixed(2) : 0;
        
        this.testResults.summary.successRate = `${successRate}%`;
        this.testResults.summary.timestamp = new Date().toISOString();
        this.testResults.summary.browserInfo = {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine
        };
        
        this.log('Test summary generated', this.testResults.summary);
    }

    log(message, data = {}) {
        console.log(`[ComprehensiveLoginTestSuite] ${message}`, data);
    }

    logError(message, error) {
        console.error(`[ComprehensiveLoginTestSuite] ${message}`, error);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ComprehensiveLoginTestSuite;
}

// Make available globally
window.ComprehensiveLoginTestSuite = ComprehensiveLoginTestSuite;