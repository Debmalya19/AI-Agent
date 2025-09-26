/**
 * Session Manager Validation Script
 * Run this in Node.js to validate the session manager implementation
 */

// Mock browser APIs for Node.js testing
global.window = {
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
    parent: null
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

global.fetch = async () => {
    throw new Error('Network request not available in test environment');
};

global.CustomEvent = class CustomEvent {
    constructor(type, options) {
        this.type = type;
        this.detail = options?.detail;
    }
};

global.StorageEvent = class StorageEvent {
    constructor(type, options) {
        this.type = type;
        this.key = options?.key;
        this.newValue = options?.newValue;
        this.oldValue = options?.oldValue;
    }
};

// Load the SessionManager class
const fs = require('fs');
const path = require('path');

const sessionManagerCode = fs.readFileSync(
    path.join(__dirname, 'js', 'session-manager.js'), 
    'utf8'
);

// Execute the code to define the class
eval(sessionManagerCode);

// Make SessionManager available
const SessionManager = global.window.SessionManager;

// Test suite
class SessionManagerValidator {
    constructor() {
        this.tests = [];
        this.passed = 0;
        this.failed = 0;
    }

    test(name, testFn) {
        this.tests.push({ name, testFn });
    }

    async runTests() {
        console.log('🧪 Running Session Manager Validation Tests\n');

        for (const { name, testFn } of this.tests) {
            try {
                await testFn();
                console.log(`✅ ${name}`);
                this.passed++;
            } catch (error) {
                console.log(`❌ ${name}: ${error.message}`);
                this.failed++;
            }
        }

        console.log(`\n📊 Test Results: ${this.passed} passed, ${this.failed} failed`);
        
        if (this.failed === 0) {
            console.log('🎉 All tests passed! Session Manager implementation is valid.');
        } else {
            console.log('⚠️  Some tests failed. Please review the implementation.');
        }
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

// Create validator and define tests
const validator = new SessionManagerValidator();

validator.test('SessionManager can be instantiated', () => {
    const sessionManager = new SessionManager();
    validator.assertNotNull(sessionManager, 'SessionManager should be instantiated');
    validator.assert(typeof sessionManager.storeSession === 'function', 'storeSession method should exist');
    validator.assert(typeof sessionManager.getSessionToken === 'function', 'getSessionToken method should exist');
    validator.assert(typeof sessionManager.validateStoredSession === 'function', 'validateStoredSession method should exist');
    sessionManager.destroy();
});

validator.test('Session storage and retrieval works', async () => {
    // Enable debug mode for this test
    global.localStorage.setItem('admin_debug', 'true');
    
    const sessionManager = new SessionManager();
    
    const testSession = {
        token: 'test_token_123',
        user: { id: 1, username: 'testuser', email: 'test@example.com' },
        expires_at: new Date(Date.now() + 3600000).toISOString(),
        refresh_token: 'refresh_123'
    };

    try {
        console.log('Attempting to store session:', testSession);
        const stored = await sessionManager.storeSession(testSession);
        console.log('Storage result:', stored);
        
        // Debug: Check what's actually in storage
        console.log('localStorage data:', global.localStorage.data);
        console.log('sessionStorage data:', global.sessionStorage.data);
        
        validator.assert(stored, 'Session should be stored successfully');

        const retrievedToken = sessionManager.getSessionToken();
        console.log('Retrieved token:', retrievedToken);
        validator.assertEqual(retrievedToken, testSession.token, 'Retrieved token should match stored token');

        const retrievedUser = sessionManager.getStoredUser();
        console.log('Retrieved user:', retrievedUser);
        validator.assertNotNull(retrievedUser, 'Retrieved user should not be null');
        validator.assertEqual(retrievedUser.username, testSession.user.username, 'Retrieved username should match');
    } catch (error) {
        console.log('Storage error:', error);
        throw error;
    }

    sessionManager.destroy();
});

validator.test('Session validation works correctly', async () => {
    // Clear any existing session data first
    global.localStorage.data = {};
    global.sessionStorage.data = {};
    
    const sessionManager = new SessionManager();
    
    // Test with no session
    let isValid = sessionManager.validateStoredSession();
    validator.assert(!isValid, 'Should be invalid when no session exists');

    // Test with valid session
    const validSession = {
        token: 'valid_token_123',
        user: { id: 1, username: 'validuser' },
        expires_at: new Date(Date.now() + 3600000).toISOString()
    };

    await sessionManager.storeSession(validSession);
    isValid = sessionManager.validateStoredSession();
    validator.assert(isValid, 'Should be valid with proper session data');

    // Clear session before testing expired session
    sessionManager.clearSession();

    // Test with expired session
    const expiredSession = {
        token: 'expired_token_123',
        user: { id: 2, username: 'expireduser' },
        expires_at: new Date(Date.now() - 3600000).toISOString() // 1 hour ago
    };

    await sessionManager.storeSession(expiredSession);
    isValid = sessionManager.validateStoredSession();
    validator.assert(!isValid, 'Should be invalid with expired session');

    sessionManager.destroy();
});

validator.test('Multiple storage strategies work', async () => {
    const sessionManager = new SessionManager();
    
    const testSession = {
        token: 'multi_storage_token',
        user: { id: 3, username: 'multistorageuser' },
        expires_at: new Date(Date.now() + 3600000).toISOString()
    };

    // Test localStorage
    const localResult = await sessionManager.storeInLocalStorage(testSession);
    validator.assert(localResult, 'localStorage storage should succeed');

    // Test sessionStorage
    const sessionResult = await sessionManager.storeInSessionStorage(testSession);
    validator.assert(sessionResult, 'sessionStorage storage should succeed');

    // Verify data is in both storages
    const localToken = localStorage.getItem(sessionManager.tokenKey);
    const sessionToken = sessionStorage.getItem(sessionManager.tokenKey);
    
    validator.assertEqual(localToken, testSession.token, 'Token should be in localStorage');
    validator.assertEqual(sessionToken, testSession.token, 'Token should be in sessionStorage');

    sessionManager.destroy();
});

validator.test('Session recovery works', () => {
    const sessionManager = new SessionManager();
    
    // Set up session in localStorage only
    const testSession = {
        token: 'recovery_token_123',
        user: { id: 4, username: 'recoveryuser' },
        expires_at: new Date(Date.now() + 3600000).toISOString()
    };

    localStorage.setItem(sessionManager.tokenKey, testSession.token);
    localStorage.setItem(sessionManager.userKey, JSON.stringify(testSession.user));
    localStorage.setItem(sessionManager.expiryKey, testSession.expires_at);

    // Clear sessionStorage to simulate partial data loss
    sessionStorage.removeItem(sessionManager.tokenKey);
    sessionStorage.removeItem(sessionManager.userKey);

    // Test recovery
    const recovered = sessionManager.recoverFromAlternativeStorage();
    validator.assert(recovered, 'Session recovery should succeed');

    // Verify recovery worked
    const recoveredToken = sessionManager.getSessionToken();
    validator.assertEqual(recoveredToken, testSession.token, 'Recovered token should match original');

    sessionManager.destroy();
});

validator.test('Activity tracking works', () => {
    const sessionManager = new SessionManager();
    
    // Test activity update
    sessionManager.updateLastActivity();
    const lastActivity = sessionManager.getLastActivity();
    validator.assertNotNull(lastActivity, 'Last activity should be recorded');

    // Test inactivity detection (should not be inactive immediately)
    const isInactive = sessionManager.isSessionInactive();
    validator.assert(!isInactive, 'Should not be inactive immediately after activity');

    sessionManager.destroy();
});

validator.test('Session cleanup works', () => {
    const sessionManager = new SessionManager();
    
    // Store a session
    const testSession = {
        token: 'cleanup_token_123',
        user: { id: 5, username: 'cleanupuser' }
    };

    sessionManager.storeSession(testSession);
    
    // Verify session exists
    let token = sessionManager.getSessionToken();
    validator.assertNotNull(token, 'Token should exist before cleanup');

    // Clear session
    sessionManager.clearSession();
    
    // Verify session is cleared
    token = sessionManager.getSessionToken();
    validator.assert(!token, 'Token should be cleared after cleanup');

    const user = sessionManager.getStoredUser();
    validator.assert(!user, 'User should be cleared after cleanup');

    sessionManager.destroy();
});

validator.test('Authentication headers are generated correctly', () => {
    const sessionManager = new SessionManager();
    
    // Test without token
    let headers = sessionManager.getAuthHeaders();
    validator.assert(headers['Content-Type'] === 'application/json', 'Should have Content-Type header');
    validator.assert(!headers['Authorization'], 'Should not have Authorization header without token');

    // Test with token
    const testSession = {
        token: 'auth_header_token_123',
        user: { id: 6, username: 'authuser' }
    };

    sessionManager.storeSession(testSession);
    headers = sessionManager.getAuthHeaders();
    
    validator.assert(headers['Authorization'] === `Bearer ${testSession.token}`, 'Should have correct Authorization header');

    sessionManager.destroy();
});

validator.test('Diagnostics provide comprehensive information', () => {
    const sessionManager = new SessionManager();
    
    const diagnostics = sessionManager.getDiagnostics();
    
    validator.assertNotNull(diagnostics, 'Diagnostics should not be null');
    validator.assert(typeof diagnostics.hasToken === 'boolean', 'Should have hasToken boolean');
    validator.assert(typeof diagnostics.hasUser === 'boolean', 'Should have hasUser boolean');
    validator.assert(typeof diagnostics.isValid === 'boolean', 'Should have isValid boolean');
    validator.assertNotNull(diagnostics.storageAvailable, 'Should have storageAvailable info');
    validator.assertNotNull(diagnostics.settings, 'Should have settings info');

    sessionManager.destroy();
});

// Run all tests
validator.runTests().catch(console.error);