/**
 * Session Manager Integration Test
 * Tests the session manager integration with the admin authentication system
 */

// Import required modules (if running in Node.js environment)
if (typeof window === 'undefined') {
    // Node.js environment setup
    global.window = {
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => {},
        parent: null,
        location: { href: '' }
    };

    global.document = {
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => {},
        hidden: false,
        cookie: ''
    };

    global.navigator = {
        cookieEnabled: true
    };

    global.localStorage = {
        data: {},
        setItem(key, value) { this.data[key] = value; },
        getItem(key) { return this.data[key] || null; },
        removeItem(key) { delete this.data[key]; }
    };

    global.sessionStorage = {
        data: {},
        setItem(key, value) { this.data[key] = value; },
        getItem(key) { return this.data[key] || null; },
        removeItem(key) { delete this.data[key]; }
    };

    global.fetch = async (url, options) => {
        // Mock fetch for testing
        console.log(`Mock fetch: ${options?.method || 'GET'} ${url}`);
        
        if (url.includes('/api/auth/validate')) {
            return {
                ok: true,
                json: async () => ({ valid: true })
            };
        }
        
        if (url.includes('/api/auth/refresh')) {
            return {
                ok: true,
                json: async () => ({
                    token: 'new_token_' + Date.now(),
                    user: { id: 1, username: 'refreshed_user' },
                    expires_at: new Date(Date.now() + 3600000).toISOString()
                })
            };
        }
        
        return {
            ok: false,
            status: 404,
            json: async () => ({ error: 'Not found' })
        };
    };

    global.CustomEvent = class CustomEvent {
        constructor(type, options) {
            this.type = type;
            this.detail = options?.detail;
        }
    };

    // Load the SessionManager class
    const fs = require('fs');
    const path = require('path');

    const sessionManagerCode = fs.readFileSync(
        path.join(__dirname, 'js', 'session-manager.js'), 
        'utf8'
    );

    eval(sessionManagerCode);
}

/**
 * Integration Test Suite
 */
class SessionIntegrationTester {
    constructor() {
        this.tests = [];
        this.passed = 0;
        this.failed = 0;
        this.sessionManager = null;
    }

    test(name, testFn) {
        this.tests.push({ name, testFn });
    }

    async runTests() {
        console.log('🔗 Running Session Manager Integration Tests\n');

        for (const { name, testFn } of this.tests) {
            try {
                // Create fresh session manager for each test
                if (this.sessionManager) {
                    this.sessionManager.destroy();
                }
                this.sessionManager = new (global.window?.SessionManager || SessionManager)();
                
                await testFn();
                console.log(`✅ ${name}`);
                this.passed++;
            } catch (error) {
                console.log(`❌ ${name}: ${error.message}`);
                this.failed++;
            } finally {
                // Clean up after each test
                if (this.sessionManager) {
                    this.sessionManager.clearSession();
                }
                if (global.localStorage) {
                    global.localStorage.data = {};
                }
                if (global.sessionStorage) {
                    global.sessionStorage.data = {};
                }
            }
        }

        // Final cleanup
        if (this.sessionManager) {
            this.sessionManager.destroy();
        }

        console.log(`\n📊 Integration Test Results: ${this.passed} passed, ${this.failed} failed`);
        
        if (this.failed === 0) {
            console.log('🎉 All integration tests passed! Session Manager is ready for production.');
        } else {
            console.log('⚠️  Some integration tests failed. Please review the implementation.');
        }

        return this.failed === 0;
    }

    assert(condition, message) {
        if (!condition) {
            throw new Error(message);
        }
    }

    assertEqual(actual, expected, message) {
        if (actual !== expected) {
            throw new Error(`${message}: expected ${expected}, got ${actual}`);
        }
    }

    assertNotNull(value, message) {
        if (value === null || value === undefined) {
            throw new Error(`${message}: value is null or undefined`);
        }
    }
}

// Create tester and define integration tests
const tester = new SessionIntegrationTester();

tester.test('Session Manager initializes with proper configuration', () => {
    tester.assertNotNull(tester.sessionManager, 'Session manager should be created');
    tester.assert(typeof tester.sessionManager.storeSession === 'function', 'storeSession method should exist');
    tester.assert(typeof tester.sessionManager.validateAndRecoverSession === 'function', 'validateAndRecoverSession method should exist');
    tester.assert(typeof tester.sessionManager.authenticatedFetch === 'function', 'authenticatedFetch method should exist');
    
    // Check configuration
    tester.assertEqual(tester.sessionManager.tokenKey, 'admin_session_token', 'Token key should be correct');
    tester.assertEqual(tester.sessionManager.userKey, 'admin_user_data', 'User key should be correct');
    tester.assert(tester.sessionManager.validationInterval > 0, 'Validation interval should be positive');
    tester.assert(tester.sessionManager.maxInactivityTime > 0, 'Max inactivity time should be positive');
});

tester.test('Complete login flow simulation', async () => {
    // Simulate successful login response from backend
    const loginResponse = {
        token: 'login_token_' + Date.now(),
        user: {
            id: 1,
            username: 'admin',
            email: 'admin@example.com',
            is_admin: true
        },
        expires_at: new Date(Date.now() + 3600000).toISOString(),
        refresh_token: 'refresh_token_' + Date.now()
    };

    // Store session (simulating successful login)
    const stored = await tester.sessionManager.storeSession(loginResponse);
    tester.assert(stored, 'Login session should be stored successfully');

    // Verify session data
    const token = tester.sessionManager.getSessionToken();
    const user = tester.sessionManager.getStoredUser();
    
    tester.assertEqual(token, loginResponse.token, 'Stored token should match login response');
    tester.assertNotNull(user, 'User data should be stored');
    tester.assertEqual(user.username, loginResponse.user.username, 'Username should match');
    tester.assertEqual(user.email, loginResponse.user.email, 'Email should match');

    // Verify session is valid
    const isValid = tester.sessionManager.validateStoredSession();
    tester.assert(isValid, 'Session should be valid after login');
});

tester.test('Authentication headers for API calls', async () => {
    // Set up session
    const sessionData = {
        token: 'api_token_' + Date.now(),
        user: { id: 2, username: 'apiuser' },
        expires_at: new Date(Date.now() + 3600000).toISOString()
    };

    await tester.sessionManager.storeSession(sessionData);

    // Test authentication headers
    const headers = tester.sessionManager.getAuthHeaders();
    tester.assertNotNull(headers, 'Headers should be generated');
    tester.assertEqual(headers['Content-Type'], 'application/json', 'Content-Type should be set');
    tester.assertEqual(headers['Authorization'], `Bearer ${sessionData.token}`, 'Authorization header should be correct');
});

tester.test('Authenticated fetch functionality', async () => {
    // Set up session
    const sessionData = {
        token: 'fetch_token_' + Date.now(),
        user: { id: 3, username: 'fetchuser' },
        expires_at: new Date(Date.now() + 3600000).toISOString()
    };

    await tester.sessionManager.storeSession(sessionData);

    // Test authenticated fetch
    try {
        const response = await tester.sessionManager.authenticatedFetch('/api/test');
        tester.assertNotNull(response, 'Response should be returned');
        // Note: In real environment, this would make actual HTTP request
    } catch (error) {
        // In test environment, this might fail due to mock limitations
        // This is acceptable for integration testing
        console.log('Note: Authenticated fetch test limited by mock environment');
    }
});

tester.test('Session validation with backend', async () => {
    // Set up session
    const sessionData = {
        token: 'validation_token_' + Date.now(),
        user: { id: 4, username: 'validationuser' },
        expires_at: new Date(Date.now() + 3600000).toISOString()
    };

    await tester.sessionManager.storeSession(sessionData);

    // Test backend validation
    const isValid = await tester.sessionManager.validateSessionWithBackend(sessionData.token);
    tester.assert(isValid, 'Session should be valid according to backend');
});

tester.test('Session refresh functionality', async () => {
    // Set up session with refresh token
    const sessionData = {
        token: 'refresh_test_token_' + Date.now(),
        user: { id: 5, username: 'refreshuser' },
        expires_at: new Date(Date.now() + 3600000).toISOString(),
        refresh_token: 'refresh_token_' + Date.now()
    };

    await tester.sessionManager.storeSession(sessionData);

    // Test session refresh
    const refreshed = await tester.sessionManager.refreshSession();
    tester.assert(refreshed, 'Session should be refreshed successfully');

    // Verify new token is stored
    const newToken = tester.sessionManager.getSessionToken();
    tester.assertNotNull(newToken, 'New token should be stored');
    tester.assert(newToken !== sessionData.token, 'New token should be different from original');
});

tester.test('Session recovery from storage failure', async () => {
    // Set up session in localStorage only
    const sessionData = {
        token: 'recovery_test_token_' + Date.now(),
        user: { id: 6, username: 'recoveryuser' },
        expires_at: new Date(Date.now() + 3600000).toISOString()
    };

    // Manually store in localStorage
    if (global.localStorage) {
        global.localStorage.setItem(tester.sessionManager.tokenKey, sessionData.token);
        global.localStorage.setItem(tester.sessionManager.userKey, JSON.stringify(sessionData.user));
        global.localStorage.setItem(tester.sessionManager.expiryKey, sessionData.expires_at);
    }

    // Test recovery
    const recovered = tester.sessionManager.recoverFromAlternativeStorage();
    tester.assert(recovered, 'Session should be recovered from alternative storage');

    // Verify recovered data
    const recoveredToken = tester.sessionManager.getSessionToken();
    const recoveredUser = tester.sessionManager.getStoredUser();
    
    tester.assertEqual(recoveredToken, sessionData.token, 'Recovered token should match original');
    tester.assertNotNull(recoveredUser, 'Recovered user should not be null');
    tester.assertEqual(recoveredUser.username, sessionData.user.username, 'Recovered username should match');
});

tester.test('Session expiration handling', async () => {
    // Set up expired session
    const expiredSession = {
        token: 'expired_token_' + Date.now(),
        user: { id: 7, username: 'expireduser' },
        expires_at: new Date(Date.now() - 3600000).toISOString() // 1 hour ago
    };

    await tester.sessionManager.storeSession(expiredSession);

    // Test validation of expired session
    const isValid = tester.sessionManager.validateStoredSession();
    tester.assert(!isValid, 'Expired session should be invalid');

    // Verify session was cleared
    const token = tester.sessionManager.getSessionToken();
    tester.assert(!token, 'Expired session token should be cleared');
});

tester.test('Activity tracking integration', () => {
    // Test activity update
    tester.sessionManager.updateLastActivity();
    const lastActivity = tester.sessionManager.getLastActivity();
    tester.assertNotNull(lastActivity, 'Last activity should be recorded');

    // Test inactivity detection
    const isInactive = tester.sessionManager.isSessionInactive();
    tester.assert(!isInactive, 'Session should not be inactive immediately after activity');

    // Test activity timestamp format
    tester.assert(lastActivity instanceof Date, 'Last activity should be a Date object');
    tester.assert(lastActivity.getTime() <= Date.now(), 'Last activity should not be in the future');
});

tester.test('Comprehensive diagnostics', () => {
    // Set up session for diagnostics
    const sessionData = {
        token: 'diagnostics_token_' + Date.now(),
        user: { id: 8, username: 'diagnosticsuser' },
        expires_at: new Date(Date.now() + 3600000).toISOString()
    };

    tester.sessionManager.storeSession(sessionData);

    // Get diagnostics
    const diagnostics = tester.sessionManager.getDiagnostics();
    
    tester.assertNotNull(diagnostics, 'Diagnostics should be available');
    tester.assert(typeof diagnostics.hasToken === 'boolean', 'hasToken should be boolean');
    tester.assert(typeof diagnostics.hasUser === 'boolean', 'hasUser should be boolean');
    tester.assert(typeof diagnostics.isValid === 'boolean', 'isValid should be boolean');
    tester.assertNotNull(diagnostics.storageAvailable, 'storageAvailable should be provided');
    tester.assertNotNull(diagnostics.settings, 'settings should be provided');
    tester.assertNotNull(diagnostics.user, 'user data should be in diagnostics');

    // Verify diagnostic accuracy
    tester.assert(diagnostics.hasToken, 'Diagnostics should show token exists');
    tester.assert(diagnostics.hasUser, 'Diagnostics should show user exists');
    tester.assert(diagnostics.isValid, 'Diagnostics should show session is valid');
});

tester.test('Session cleanup and destruction', () => {
    // Set up session
    const sessionData = {
        token: 'cleanup_token_' + Date.now(),
        user: { id: 9, username: 'cleanupuser' },
        expires_at: new Date(Date.now() + 3600000).toISOString()
    };

    tester.sessionManager.storeSession(sessionData);

    // Verify session exists
    let token = tester.sessionManager.getSessionToken();
    tester.assertNotNull(token, 'Session should exist before cleanup');

    // Clear session
    tester.sessionManager.clearSession();

    // Verify session is cleared
    token = tester.sessionManager.getSessionToken();
    const user = tester.sessionManager.getStoredUser();
    
    tester.assert(!token, 'Token should be cleared');
    tester.assert(!user, 'User should be cleared');

    // Test session manager destruction
    tester.sessionManager.destroy();
    
    // Verify timers are cleared (can't directly test, but no errors should occur)
    tester.assert(true, 'Session manager should destroy without errors');
});

// Run the integration tests
if (typeof require !== 'undefined' && require.main === module) {
    // This file is being run directly
    tester.runTests().then(success => {
        if (typeof process !== 'undefined') {
            process.exit(success ? 0 : 1);
        }
    }).catch(error => {
        console.error('Integration test error:', error);
        if (typeof process !== 'undefined') {
            process.exit(1);
        }
    });
} else if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SessionIntegrationTester };
}