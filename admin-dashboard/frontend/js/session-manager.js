/**
 * Enhanced Session Manager
 * Handles session storage, validation, and recovery with multiple storage strategies
 */

class SessionManager {
    constructor() {
        this.tokenKey = 'admin_session_token';
        this.userKey = 'admin_user_data';
        this.expiryKey = 'admin_session_expiry';
        this.refreshTokenKey = 'admin_refresh_token';
        this.sessionIdKey = 'admin_session_id';
        this.lastActivityKey = 'admin_last_activity';
        
        // Storage strategies in order of preference
        this.storageStrategies = [
            'localStorage',
            'sessionStorage',
            'cookies'
        ];
        
        this.debugMode = localStorage.getItem('admin_debug') === 'true';
        
        // Session validation and recovery settings
        this.validationInterval = 30000; // 30 seconds
        this.maxInactivityTime = 30 * 60 * 1000; // 30 minutes
        this.sessionSyncInterval = 5000; // 5 seconds for cross-tab sync
        
        // Event listeners for session management
        this.eventListeners = [];
        this.validationTimer = null;
        this.syncTimer = null;
        
        // Initialize session management
        this.initializeSessionManagement();
        
        this.log('SessionManager initialized with enhanced features');
    }

    /**
     * Initialize session management features
     */
    initializeSessionManagement() {
        // Set up periodic session validation
        this.startSessionValidation();
        
        // Set up cross-tab session synchronization
        this.startSessionSync();
        
        // Set up activity tracking
        this.setupActivityTracking();
        
        // Set up storage event listeners for cross-tab communication
        this.setupStorageEventListeners();
        
        // Set up page visibility change handling
        this.setupVisibilityChangeHandling();
        
        // Clean up expired sessions on startup
        this.cleanupExpiredSessions();
    }

    /**
     * Start periodic session validation
     */
    startSessionValidation() {
        if (this.validationTimer) {
            clearInterval(this.validationTimer);
        }
        
        this.validationTimer = setInterval(() => {
            this.validateAndRecoverSession();
        }, this.validationInterval);
        
        this.log('Session validation timer started');
    }

    /**
     * Start cross-tab session synchronization
     */
    startSessionSync() {
        if (this.syncTimer) {
            clearInterval(this.syncTimer);
        }
        
        this.syncTimer = setInterval(() => {
            this.syncSessionAcrossTabs();
        }, this.sessionSyncInterval);
        
        this.log('Session sync timer started');
    }

    /**
     * Set up activity tracking to update last activity time
     */
    setupActivityTracking() {
        const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
        
        const updateActivity = () => {
            this.updateLastActivity();
        };
        
        activityEvents.forEach(event => {
            document.addEventListener(event, updateActivity, { passive: true });
            this.eventListeners.push({ event, handler: updateActivity });
        });
        
        this.log('Activity tracking set up');
    }

    /**
     * Set up storage event listeners for cross-tab communication
     */
    setupStorageEventListeners() {
        const storageHandler = (event) => {
            if (event.key === this.tokenKey || event.key === this.userKey || event.key === this.expiryKey) {
                this.log('Session data changed in another tab', { key: event.key });
                this.handleCrossTabSessionChange(event);
            }
        };
        
        window.addEventListener('storage', storageHandler);
        this.eventListeners.push({ event: 'storage', handler: storageHandler });
        
        this.log('Storage event listeners set up');
    }

    /**
     * Set up page visibility change handling
     */
    setupVisibilityChangeHandling() {
        const visibilityHandler = () => {
            if (!document.hidden) {
                // Page became visible, validate session
                this.log('Page became visible, validating session');
                this.validateAndRecoverSession();
            }
        };
        
        document.addEventListener('visibilitychange', visibilityHandler);
        this.eventListeners.push({ event: 'visibilitychange', handler: visibilityHandler });
        
        this.log('Visibility change handling set up');
    }

    /**
     * Update last activity timestamp
     */
    updateLastActivity() {
        const now = new Date().toISOString();
        try {
            if (localStorage) {
                localStorage.setItem(this.lastActivityKey, now);
            }
            if (sessionStorage) {
                sessionStorage.setItem(this.lastActivityKey, now);
            }
        } catch (e) {
            this.log('Failed to update last activity', { error: e.message });
        }
    }

    /**
     * Get last activity timestamp
     * @returns {Date|null} Last activity time
     */
    getLastActivity() {
        const lastActivity = this.getFromStorage('localStorage', this.lastActivityKey) ||
                           this.getFromStorage('sessionStorage', this.lastActivityKey);
        
        return lastActivity ? new Date(lastActivity) : null;
    }

    /**
     * Check if session has been inactive for too long
     * @returns {boolean} Whether session is inactive
     */
    isSessionInactive() {
        const lastActivity = this.getLastActivity();
        if (!lastActivity) return false;
        
        const now = new Date();
        const inactiveTime = now.getTime() - lastActivity.getTime();
        
        return inactiveTime > this.maxInactivityTime;
    }

    /**
     * Validate session and attempt recovery if needed
     * @returns {Promise<boolean>} Whether session is valid after validation/recovery
     */
    async validateAndRecoverSession() {
        this.log('Validating session');
        
        // Check if session exists and is not expired
        if (!this.validateStoredSession()) {
            this.log('Session validation failed, attempting recovery');
            return await this.attemptSessionRecovery();
        }
        
        // Check for inactivity
        if (this.isSessionInactive()) {
            this.log('Session inactive for too long, clearing session');
            this.clearSession();
            this.notifySessionExpired('inactivity');
            return false;
        }
        
        // Validate with backend if token exists
        const token = this.getSessionToken();
        if (token) {
            return await this.validateSessionWithBackend(token);
        }
        
        return true;
    }

    /**
     * Attempt to recover session using refresh token or other methods
     * @returns {Promise<boolean>} Whether recovery was successful
     */
    async attemptSessionRecovery() {
        this.log('Attempting session recovery');
        
        // Try to refresh session using refresh token
        const refreshSuccess = await this.refreshSession();
        if (refreshSuccess) {
            this.log('Session recovered using refresh token');
            return true;
        }
        
        // Try to recover from other storage locations
        const recoverySuccess = this.recoverFromAlternativeStorage();
        if (recoverySuccess) {
            this.log('Session recovered from alternative storage');
            return true;
        }
        
        this.log('Session recovery failed');
        this.notifySessionExpired('recovery_failed');
        return false;
    }

    /**
     * Try to recover session from alternative storage locations
     * @returns {boolean} Whether recovery was successful
     */
    recoverFromAlternativeStorage() {
        // Check if we have valid session data in any storage location
        const strategies = ['localStorage', 'sessionStorage', 'cookies'];
        
        for (const strategy of strategies) {
            let token, user, expiry;
            
            if (strategy === 'cookies') {
                token = this.getCookieValue(this.tokenKey);
                const userData = this.getCookieValue(this.userKey);
                try {
                    user = userData ? JSON.parse(decodeURIComponent(userData)) : null;
                } catch (e) {
                    continue;
                }
            } else {
                token = this.getFromStorage(strategy, this.tokenKey);
                const userData = this.getFromStorage(strategy, this.userKey);
                try {
                    user = userData ? JSON.parse(userData) : null;
                } catch (e) {
                    continue;
                }
                expiry = this.getFromStorage(strategy, this.expiryKey);
            }
            
            if (token && user) {
                // Check if not expired
                if (expiry) {
                    const expiryTime = new Date(expiry);
                    if (expiryTime <= new Date()) {
                        continue; // Skip expired session
                    }
                }
                
                // Restore session to all storage locations
                this.storeSession({
                    token: token,
                    user: user,
                    expires_at: expiry
                });
                
                this.log('Session recovered from', { strategy });
                return true;
            }
        }
        
        return false;
    }

    /**
     * Validate session with backend
     * @param {string} token - Session token to validate
     * @returns {Promise<boolean>} Whether session is valid
     */
    async validateSessionWithBackend(token) {
        try {
            const response = await fetch('/api/auth/validate', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.valid) {
                    this.log('Session validated with backend');
                    this.updateLastActivity();
                    return true;
                } else {
                    this.log('Session invalid according to backend');
                    this.clearSession();
                    this.notifySessionExpired('backend_validation_failed');
                    return false;
                }
            } else if (response.status === 401) {
                this.log('Session unauthorized, attempting refresh');
                return await this.refreshSession();
            } else {
                this.log('Session validation request failed', { status: response.status });
                return true; // Don't clear session on network errors
            }
        } catch (error) {
            this.log('Session validation error', { error: error.message });
            return true; // Don't clear session on network errors
        }
    }

    /**
     * Synchronize session across browser tabs
     */
    syncSessionAcrossTabs() {
        // Check if session data has changed in other tabs
        const currentSessionId = this.getFromStorage('localStorage', this.sessionIdKey);
        const storedSessionId = this.getFromStorage('sessionStorage', this.sessionIdKey);
        
        if (currentSessionId && currentSessionId !== storedSessionId) {
            this.log('Session changed in another tab, syncing');
            
            // Update session storage with localStorage data
            const token = this.getFromStorage('localStorage', this.tokenKey);
            const user = this.getFromStorage('localStorage', this.userKey);
            const expiry = this.getFromStorage('localStorage', this.expiryKey);
            
            if (token && user) {
                try {
                    sessionStorage.setItem(this.tokenKey, token);
                    sessionStorage.setItem(this.userKey, user);
                    sessionStorage.setItem(this.sessionIdKey, currentSessionId);
                    if (expiry) {
                        sessionStorage.setItem(this.expiryKey, expiry);
                    }
                    
                    this.log('Session synced across tabs');
                } catch (e) {
                    this.log('Failed to sync session across tabs', { error: e.message });
                }
            }
        }
    }

    /**
     * Handle session changes from other tabs
     * @param {StorageEvent} event - Storage event
     */
    handleCrossTabSessionChange(event) {
        if (event.newValue === null) {
            // Session was cleared in another tab
            this.log('Session cleared in another tab');
            this.clearSession();
            this.notifySessionExpired('cleared_in_other_tab');
        } else if (event.key === this.tokenKey && event.newValue) {
            // Session was updated in another tab
            this.log('Session updated in another tab');
            this.syncSessionAcrossTabs();
        }
    }

    /**
     * Clean up expired sessions from storage
     */
    cleanupExpiredSessions() {
        this.log('Cleaning up expired sessions');
        
        const expiry = this.getSessionExpiry();
        if (expiry) {
            const expiryTime = new Date(expiry);
            const now = new Date();
            
            if (expiryTime <= now) {
                this.log('Found expired session, cleaning up');
                this.clearSession();
            }
        }
        
        // Clean up old activity timestamps
        const lastActivity = this.getLastActivity();
        if (lastActivity && this.isSessionInactive()) {
            this.log('Found inactive session, cleaning up');
            this.clearSession();
        }
    }

    /**
     * Notify about session expiration
     * @param {string} reason - Reason for expiration
     */
    notifySessionExpired(reason) {
        this.log('Session expired', { reason });
        
        // Dispatch custom event for session expiration
        const event = new CustomEvent('sessionExpired', {
            detail: { reason: reason, timestamp: new Date().toISOString() }
        });
        window.dispatchEvent(event);
        
        // Also try to notify parent window if in iframe
        try {
            if (window.parent && window.parent !== window) {
                window.parent.postMessage({
                    type: 'sessionExpired',
                    reason: reason,
                    timestamp: new Date().toISOString()
                }, '*');
            }
        } catch (e) {
            // Ignore cross-origin errors
        }
    }

    /**
     * Destroy session manager and clean up resources
     */
    destroy() {
        this.log('Destroying session manager');
        
        // Clear timers
        if (this.validationTimer) {
            clearInterval(this.validationTimer);
            this.validationTimer = null;
        }
        
        if (this.syncTimer) {
            clearInterval(this.syncTimer);
            this.syncTimer = null;
        }
        
        // Remove event listeners
        this.eventListeners.forEach(({ event, handler }) => {
            if (event === 'storage' || event === 'visibilitychange') {
                window.removeEventListener(event, handler);
            } else {
                document.removeEventListener(event, handler);
            }
        });
        
        this.eventListeners = [];
        
        this.log('Session manager destroyed');
    }

    /**
     * Store session information using multiple storage strategies
     * @param {Object} authData - Authentication data
     * @param {string} authData.token - Session token
     * @param {Object} authData.user - User information
     * @param {string} authData.expires_at - Session expiry time
     * @param {string} authData.refresh_token - Refresh token
     * @returns {Promise<boolean>} Success status
     */
    async storeSession(authData) {
        this.log('Storing session', { 
            hasToken: !!authData.token, 
            hasUser: !!authData.user,
            hasExpiry: !!authData.expires_at
        });

        try {
            // Generate unique session ID for cross-tab synchronization
            const sessionId = this.generateSessionId();
            
            const sessionData = {
                token: authData.token,
                user: authData.user,
                expires_at: authData.expires_at,
                refresh_token: authData.refresh_token,
                session_id: sessionId,
                stored_at: new Date().toISOString()
            };

            // Store using multiple strategies for reliability
            const results = await Promise.allSettled([
                this.storeInLocalStorage(sessionData),
                this.storeInSessionStorage(sessionData),
                this.storeInCookies(sessionData),
                this.storeForBackwardCompatibility(sessionData)
            ]);

            // Check if at least one storage method succeeded
            const successCount = results.filter(result => result.status === 'fulfilled' && result.value).length;
            
            this.log('Session storage results', { 
                successCount, 
                totalAttempts: results.length,
                results: results.map(r => ({ status: r.status, value: r.value, reason: r.reason?.message })),
                sessionId: sessionId
            });

            if (successCount > 0) {
                // Update last activity
                this.updateLastActivity();
                
                // Verify storage worked by checking if we can retrieve the data
                const storedToken = this.getSessionToken();
                const storedUser = this.getStoredUser();
                const isValid = !!(storedToken && storedUser);
                
                this.log('Session storage verification', { 
                    hasStoredToken: !!storedToken, 
                    hasStoredUser: !!storedUser, 
                    isValid 
                });
                
                if (isValid) {
                    // Notify other tabs about session change
                    this.notifySessionChange('created', sessionId);
                }
                
                return isValid;
            } else {
                this.log('All storage methods failed', { results: results.map(r => r.reason?.message) });
                return false;
            }
        } catch (error) {
            this.log('Session storage error', { error: error.message });
            return false;
        }
    }

    /**
     * Generate unique session ID
     * @returns {string} Unique session ID
     */
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Notify other tabs about session changes
     * @param {string} action - Action type ('created', 'updated', 'cleared')
     * @param {string} sessionId - Session ID
     */
    notifySessionChange(action, sessionId) {
        try {
            // Use localStorage to communicate with other tabs
            const notification = {
                action: action,
                sessionId: sessionId,
                timestamp: new Date().toISOString()
            };
            
            localStorage.setItem('session_notification', JSON.stringify(notification));
            
            // Remove the notification after a short delay to trigger storage event
            setTimeout(() => {
                localStorage.removeItem('session_notification');
            }, 100);
            
            this.log('Session change notification sent', notification);
        } catch (e) {
            this.log('Failed to notify session change', { error: e.message });
        }
    }

    /**
     * Store session data in localStorage
     * @param {Object} sessionData - Session data to store
     * @returns {Promise<boolean>} Success status
     */
    async storeInLocalStorage(sessionData) {
        try {
            if (!localStorage || typeof localStorage.setItem !== 'function') {
                this.log('localStorage not available');
                return false;
            }

            // Only store non-empty values
            if (sessionData.token) {
                localStorage.setItem(this.tokenKey, sessionData.token);
            }
            if (sessionData.user) {
                localStorage.setItem(this.userKey, JSON.stringify(sessionData.user));
            }
            if (sessionData.expires_at) {
                localStorage.setItem(this.expiryKey, sessionData.expires_at);
            }
            if (sessionData.refresh_token) {
                localStorage.setItem(this.refreshTokenKey, sessionData.refresh_token);
            }
            if (sessionData.session_id) {
                localStorage.setItem(this.sessionIdKey, sessionData.session_id);
            }

            this.log('localStorage storage successful');
            return true;
        } catch (error) {
            this.log('localStorage storage failed', { error: error.message });
            return false;
        }
    }

    /**
     * Store session data in sessionStorage
     * @param {Object} sessionData - Session data to store
     * @returns {Promise<boolean>} Success status
     */
    async storeInSessionStorage(sessionData) {
        try {
            if (!sessionStorage || typeof sessionStorage.setItem !== 'function') {
                this.log('sessionStorage not available');
                return false;
            }

            // Only store non-empty values
            if (sessionData.token) {
                sessionStorage.setItem(this.tokenKey, sessionData.token);
            }
            if (sessionData.user) {
                sessionStorage.setItem(this.userKey, JSON.stringify(sessionData.user));
            }
            if (sessionData.expires_at) {
                sessionStorage.setItem(this.expiryKey, sessionData.expires_at);
            }
            if (sessionData.refresh_token) {
                sessionStorage.setItem(this.refreshTokenKey, sessionData.refresh_token);
            }
            if (sessionData.session_id) {
                sessionStorage.setItem(this.sessionIdKey, sessionData.session_id);
            }

            this.log('sessionStorage storage successful');
            return true;
        } catch (error) {
            this.log('sessionStorage storage failed', { error: error.message });
            return false;
        }
    }

    /**
     * Store session data in cookies
     * @param {Object} sessionData - Session data to store
     * @returns {Promise<boolean>} Success status
     */
    async storeInCookies(sessionData) {
        try {
            if (!navigator.cookieEnabled) {
                this.log('Cookies not enabled');
                return false;
            }

            const expiry = sessionData.expires_at ? 
                new Date(sessionData.expires_at).toUTCString() : 
                new Date(Date.now() + 24 * 60 * 60 * 1000).toUTCString(); // 24 hours default

            // Store token
            if (sessionData.token) {
                document.cookie = `${this.tokenKey}=${sessionData.token}; expires=${expiry}; path=/; SameSite=Strict`;
            }

            // Store user data (encoded)
            if (sessionData.user) {
                const encodedUser = encodeURIComponent(JSON.stringify(sessionData.user));
                document.cookie = `${this.userKey}=${encodedUser}; expires=${expiry}; path=/; SameSite=Strict`;
            }

            this.log('Cookie storage successful');
            return true;
        } catch (error) {
            this.log('Cookie storage failed', { error: error.message });
            return false;
        }
    }

    /**
     * Store session data for backward compatibility with legacy systems
     * @param {Object} sessionData - Session data to store
     * @returns {Promise<boolean>} Success status
     */
    async storeForBackwardCompatibility(sessionData) {
        try {
            if (!localStorage || typeof localStorage.setItem !== 'function') {
                this.log('localStorage not available for backward compatibility');
                return false;
            }

            // Store token with legacy key names for compatibility
            if (sessionData.token) {
                localStorage.setItem('authToken', sessionData.token);
            }
            
            if (sessionData.user) {
                localStorage.setItem('username', sessionData.user.username || sessionData.user.email || 'User');
                localStorage.setItem('userEmail', sessionData.user.email || '');
                localStorage.setItem('isAdmin', sessionData.user.is_admin ? 'true' : 'false');
            }

            this.log('Backward compatibility storage successful');
            return true;
        } catch (error) {
            this.log('Backward compatibility storage failed', { error: error.message });
            return false;
        }
    }

    /**
     * Get session token from any available storage
     * @returns {string|null} Session token
     */
    getSessionToken() {
        // Try localStorage first
        let token = this.getFromStorage('localStorage', this.tokenKey);
        if (token) return token;

        // Try sessionStorage
        token = this.getFromStorage('sessionStorage', this.tokenKey);
        if (token) return token;

        // Try cookies
        token = this.getCookieValue(this.tokenKey);
        if (token) return token;

        return null;
    }

    /**
     * Get stored user data
     * @returns {Object|null} User data
     */
    getStoredUser() {
        // Try localStorage first
        let userData = this.getFromStorage('localStorage', this.userKey);
        if (userData) {
            try {
                return JSON.parse(userData);
            } catch (e) {
                this.log('Failed to parse user data from localStorage', { error: e.message });
            }
        }

        // Try sessionStorage
        userData = this.getFromStorage('sessionStorage', this.userKey);
        if (userData) {
            try {
                return JSON.parse(userData);
            } catch (e) {
                this.log('Failed to parse user data from sessionStorage', { error: e.message });
            }
        }

        // Try cookies
        userData = this.getCookieValue(this.userKey);
        if (userData) {
            try {
                return JSON.parse(decodeURIComponent(userData));
            } catch (e) {
                this.log('Failed to parse user data from cookies', { error: e.message });
            }
        }

        return null;
    }

    /**
     * Get session expiry time
     * @returns {string|null} Expiry time
     */
    getSessionExpiry() {
        return this.getFromStorage('localStorage', this.expiryKey) ||
               this.getFromStorage('sessionStorage', this.expiryKey) ||
               null;
    }

    /**
     * Get refresh token
     * @returns {string|null} Refresh token
     */
    getRefreshToken() {
        return this.getFromStorage('localStorage', this.refreshTokenKey) ||
               this.getFromStorage('sessionStorage', this.refreshTokenKey) ||
               null;
    }

    /**
     * Validate that session is properly stored and not expired
     * @returns {boolean} Whether session is valid
     */
    validateStoredSession() {
        const token = this.getSessionToken();
        const user = this.getStoredUser();
        const expiry = this.getSessionExpiry();

        // Must have token and user
        if (!token || !user) {
            this.log('Session validation failed: missing token or user', { 
                hasToken: !!token, 
                hasUser: !!user 
            });
            return false;
        }

        // Check expiry if available
        if (expiry) {
            const expiryTime = new Date(expiry);
            const now = new Date();
            
            if (expiryTime <= now) {
                this.log('Session validation failed: expired', { 
                    expiry: expiry, 
                    now: now.toISOString() 
                });
                this.clearSession(); // Clean up expired session
                return false;
            }
        }

        this.log('Session validation successful', { 
            user: user.username || user.email,
            hasExpiry: !!expiry
        });
        
        return true;
    }

    /**
     * Clear session from all storage locations
     */
    clearSession() {
        this.log('Clearing session from all storage locations');

        const sessionId = this.getFromStorage('localStorage', this.sessionIdKey);

        // Clear localStorage
        try {
            if (localStorage) {
                localStorage.removeItem(this.tokenKey);
                localStorage.removeItem(this.userKey);
                localStorage.removeItem(this.expiryKey);
                localStorage.removeItem(this.refreshTokenKey);
                localStorage.removeItem(this.sessionIdKey);
                localStorage.removeItem(this.lastActivityKey);
                
                // Clear backward compatibility keys
                localStorage.removeItem('authToken');
                localStorage.removeItem('username');
                localStorage.removeItem('userEmail');
                localStorage.removeItem('isAdmin');
            }
        } catch (e) {
            this.log('Failed to clear localStorage', { error: e.message });
        }

        // Clear sessionStorage
        try {
            if (sessionStorage) {
                sessionStorage.removeItem(this.tokenKey);
                sessionStorage.removeItem(this.userKey);
                sessionStorage.removeItem(this.expiryKey);
                sessionStorage.removeItem(this.refreshTokenKey);
                sessionStorage.removeItem(this.sessionIdKey);
                sessionStorage.removeItem(this.lastActivityKey);
            }
        } catch (e) {
            this.log('Failed to clear sessionStorage', { error: e.message });
        }

        // Clear cookies
        try {
            const expiredDate = 'Thu, 01 Jan 1970 00:00:00 UTC';
            document.cookie = `${this.tokenKey}=; expires=${expiredDate}; path=/;`;
            document.cookie = `${this.userKey}=; expires=${expiredDate}; path=/;`;
            document.cookie = `${this.expiryKey}=; expires=${expiredDate}; path=/;`;
            document.cookie = `${this.refreshTokenKey}=; expires=${expiredDate}; path=/;`;
        } catch (e) {
            this.log('Failed to clear cookies', { error: e.message });
        }

        // Notify other tabs about session clearing
        if (sessionId) {
            this.notifySessionChange('cleared', sessionId);
        }

        this.log('Session cleared');
    }

    /**
     * Refresh session if refresh token is available
     * @returns {Promise<boolean>} Success status
     */
    async refreshSession() {
        const refreshToken = this.getRefreshToken();
        if (!refreshToken) {
            this.log('No refresh token available');
            return false;
        }

        try {
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${refreshToken}`
                },
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                const stored = await this.storeSession(data);
                
                this.log('Session refreshed successfully', { stored });
                return stored;
            } else {
                this.log('Session refresh failed', { status: response.status });
                this.clearSession(); // Clear invalid session
                return false;
            }
        } catch (error) {
            this.log('Session refresh error', { error: error.message });
            return false;
        }
    }

    /**
     * Get value from specific storage type
     * @param {string} storageType - Type of storage ('localStorage' or 'sessionStorage')
     * @param {string} key - Storage key
     * @returns {string|null} Stored value
     */
    getFromStorage(storageType, key) {
        try {
            const storage = storageType === 'localStorage' ? localStorage : sessionStorage;
            if (storage) {
                return storage.getItem(key);
            }
        } catch (e) {
            this.log(`Failed to read from ${storageType}`, { error: e.message });
        }
        return null;
    }

    /**
     * Get value from cookies
     * @param {string} name - Cookie name
     * @returns {string|null} Cookie value
     */
    getCookieValue(name) {
        try {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                const [cookieName, cookieValue] = cookie.trim().split('=');
                if (cookieName === name) {
                    return cookieValue;
                }
            }
        } catch (e) {
            this.log('Failed to read cookie', { error: e.message });
        }
        return null;
    }

    /**
     * Get session diagnostics for debugging
     * @returns {Object} Diagnostic information
     */
    getDiagnostics() {
        const lastActivity = this.getLastActivity();
        const sessionId = this.getFromStorage('localStorage', this.sessionIdKey);
        
        return {
            hasToken: !!this.getSessionToken(),
            hasUser: !!this.getStoredUser(),
            hasExpiry: !!this.getSessionExpiry(),
            hasRefreshToken: !!this.getRefreshToken(),
            hasSessionId: !!sessionId,
            isValid: this.validateStoredSession(),
            isInactive: this.isSessionInactive(),
            lastActivity: lastActivity ? lastActivity.toISOString() : null,
            sessionId: sessionId,
            storageAvailable: {
                localStorage: this.testStorageAvailability('localStorage'),
                sessionStorage: this.testStorageAvailability('sessionStorage'),
                cookies: navigator.cookieEnabled
            },
            timers: {
                validationRunning: !!this.validationTimer,
                syncRunning: !!this.syncTimer
            },
            eventListeners: this.eventListeners.length,
            user: this.getStoredUser(),
            expiry: this.getSessionExpiry(),
            settings: {
                validationInterval: this.validationInterval,
                maxInactivityTime: this.maxInactivityTime,
                sessionSyncInterval: this.sessionSyncInterval
            }
        };
    }

    /**
     * Get authentication headers for API calls
     * @returns {Object} Headers object with authentication
     */
    getAuthHeaders() {
        const token = this.getSessionToken();
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        return headers;
    }

    /**
     * Make authenticated API request
     * @param {string} url - Request URL
     * @param {Object} options - Fetch options
     * @returns {Promise<Response>} Fetch response
     */
    async authenticatedFetch(url, options = {}) {
        // Validate session before making request
        const isValid = await this.validateAndRecoverSession();
        if (!isValid) {
            throw new Error('No valid session available for authenticated request');
        }
        
        // Merge authentication headers
        const authHeaders = this.getAuthHeaders();
        const headers = { ...authHeaders, ...(options.headers || {}) };
        
        // Update last activity
        this.updateLastActivity();
        
        return fetch(url, {
            ...options,
            headers: headers,
            credentials: 'include'
        });
    }

    /**
     * Test if storage type is available
     * @param {string} storageType - Storage type to test
     * @returns {boolean} Availability status
     */
    testStorageAvailability(storageType) {
        try {
            const storage = storageType === 'localStorage' ? localStorage : sessionStorage;
            if (!storage || typeof storage.setItem !== 'function') return false;
            
            const testKey = '__test__';
            storage.setItem(testKey, 'test');
            storage.removeItem(testKey);
            return true;
        } catch (e) {
            return false;
        }
    }

    /**
     * Log debug information
     * @param {string} message - Log message
     * @param {Object} data - Additional data to log
     */
    log(message, data = {}) {
        if (this.debugMode) {
            console.log(`[SessionManager] ${message}`, data);
        }
    }
}

// Make available globally
window.SessionManager = SessionManager;