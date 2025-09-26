/**
 * Enhanced Admin Authentication Service
 * Provides robust error handling, multiple request formats, and comprehensive session management
 */

class AdminAuthService {
    constructor() {
        this.baseURL = '/api/auth';
        this.sessionManager = new SessionManager();
        this.errorHandler = new AuthErrorHandler();
        this.connectivityChecker = new APIConnectivityChecker();
        
        // Configuration
        this.config = {
            timeout: 10000, // 10 seconds
            retryAttempts: 3,
            retryDelay: 1000, // 1 second
            debugMode: localStorage.getItem('admin_debug') === 'true'
        };
        
        // Request formats to try (for backend compatibility)
        this.requestFormats = [
            // Standard format
            (credentials) => ({
                email: credentials.email || credentials.username,
                password: credentials.password
            }),
            // Alternative format with username field
            (credentials) => ({
                username: credentials.username || credentials.email,
                email: credentials.email || credentials.username,
                password: credentials.password
            }),
            // Legacy format
            (credentials) => ({
                user: credentials.username || credentials.email,
                pass: credentials.password
            })
        ];
        
        this.log('AdminAuthService initialized', { debugMode: this.config.debugMode });
    }

    /**
     * Enhanced login method with multiple format attempts and robust error handling
     * @param {Object} credentials - Login credentials
     * @param {string} credentials.email - User email
     * @param {string} credentials.username - User username (alternative to email)
     * @param {string} credentials.password - User password
     * @returns {Promise<Object>} Login result with success status and user data
     */
    async login(credentials) {
        this.log('Login attempt started', { 
            email: credentials.email, 
            username: credentials.username,
            hasPassword: !!credentials.password 
        });

        // Validate input
        const validation = this.validateCredentials(credentials);
        if (!validation.valid) {
            return this.errorHandler.handleValidationError(validation.errors);
        }

        // Check connectivity first
        const connectivity = await this.connectivityChecker.checkAuthEndpoint();
        if (!connectivity.available) {
            return this.errorHandler.handleConnectivityError(connectivity);
        }

        // Try different request formats
        for (let i = 0; i < this.requestFormats.length; i++) {
            const formatFunction = this.requestFormats[i];
            const requestData = formatFunction(credentials);
            
            this.log(`Attempting login with format ${i + 1}`, requestData);
            
            try {
                const result = await this.attemptLogin(requestData, i + 1);
                if (result.success) {
                    this.log('Login successful', { format: i + 1, user: result.user?.username });
                    return result;
                }
            } catch (error) {
                this.log(`Login format ${i + 1} failed`, { error: error.message });
                
                // If this is the last format and it's a non-recoverable error, return it
                if (i === this.requestFormats.length - 1) {
                    return this.errorHandler.handleAuthError(error.status || 500, error);
                }
                
                // For recoverable errors, try next format
                if (this.isRecoverableError(error)) {
                    continue;
                } else {
                    return this.errorHandler.handleAuthError(error.status || 500, error);
                }
            }
        }

        // If all formats failed
        return this.errorHandler.handleAuthError(401, {
            message: 'All authentication formats failed',
            detail: 'Unable to authenticate with any supported request format'
        });
    }

    /**
     * Attempt login with specific request format
     * @param {Object} requestData - Formatted request data
     * @param {number} formatNumber - Format attempt number for logging
     * @returns {Promise<Object>} Login response
     */
    async attemptLogin(requestData, formatNumber) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

        try {
            const response = await fetch(`${this.baseURL}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Request-Format': `format-${formatNumber}`
                },
                credentials: 'include', // Important for cookies
                body: JSON.stringify(requestData),
                signal: controller.signal
            });

            clearTimeout(timeoutId);
            return await this.handleAuthResponse(response);
        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('Request timeout - please check your connection');
            }
            
            throw error;
        }
    }

    /**
     * Handle authentication response with comprehensive parsing
     * @param {Response} response - Fetch response object
     * @returns {Promise<Object>} Parsed authentication result
     */
    async handleAuthResponse(response) {
        let data;
        
        try {
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                // Handle non-JSON responses
                const text = await response.text();
                data = { message: text, success: false };
            }
        } catch (parseError) {
            this.log('Response parsing failed', { error: parseError.message });
            throw new Error('Invalid response format from server');
        }

        this.log('Auth response received', { 
            status: response.status, 
            success: data.success,
            hasToken: !!(data.token || data.access_token),
            hasUser: !!data.user
        });

        if (response.ok && (data.success || data.access_token || data.token)) {
            // Handle successful authentication
            const authResult = await this.processSuccessfulAuth(data, response);
            return authResult;
        } else {
            // Handle authentication failure
            const error = new Error(data.message || data.detail || 'Authentication failed');
            error.status = response.status;
            error.data = data;
            throw error;
        }
    }

    /**
     * Process successful authentication response
     * @param {Object} data - Response data
     * @param {Response} response - Original response object
     * @returns {Promise<Object>} Processed authentication result
     */
    async processSuccessfulAuth(data, response) {
        try {
            // Extract token from various possible locations
            const token = data.token || data.access_token || this.extractTokenFromCookies();
            
            // Extract user information
            const user = data.user || data.profile || {
                username: data.username,
                email: data.email,
                is_admin: data.is_admin || data.admin || false
            };

            // Store session information
            const sessionStored = await this.sessionManager.storeSession({
                token: token,
                user: user,
                expires_at: data.expires_at,
                refresh_token: data.refresh_token
            });

            if (!sessionStored) {
                this.log('Warning: Session storage failed', {});
                // Continue anyway, but log the issue
            }

            // Verify session was stored correctly
            const sessionValid = this.sessionManager.validateStoredSession();
            
            return {
                success: true,
                user: user,
                token: token,
                redirect_url: data.redirect_url || '/admin',
                session_valid: sessionValid,
                message: 'Login successful'
            };
        } catch (error) {
            this.log('Error processing successful auth', { error: error.message });
            throw new Error('Failed to process authentication response');
        }
    }

    /**
     * Logout with comprehensive cleanup
     * @returns {Promise<Object>} Logout result
     */
    async logout() {
        this.log('Logout initiated', {});
        
        try {
            // Attempt server-side logout
            const response = await fetch(`${this.baseURL}/logout`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.sessionManager.getSessionToken()}`
                },
                credentials: 'include'
            });

            // Always clear local session, regardless of server response
            this.sessionManager.clearSession();
            
            this.log('Logout completed', { serverResponse: response.ok });
            
            return {
                success: true,
                message: 'Logged out successfully'
            };
        } catch (error) {
            // Clear session even if server request fails
            this.sessionManager.clearSession();
            
            this.log('Logout error (session cleared anyway)', { error: error.message });
            
            return {
                success: true,
                message: 'Logged out (local session cleared)',
                warning: 'Server logout may have failed'
            };
        }
    }

    /**
     * Verify current session
     * @returns {Promise<Object>} Session verification result
     */
    async verifySession() {
        const token = this.sessionManager.getSessionToken();
        if (!token) {
            return { valid: false, reason: 'No token found' };
        }

        try {
            const response = await fetch(`${this.baseURL}/verify`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                return {
                    valid: true,
                    user: data.user,
                    expires_at: data.expires_at
                };
            } else {
                // Session invalid, clear it
                this.sessionManager.clearSession();
                return {
                    valid: false,
                    reason: 'Server rejected session'
                };
            }
        } catch (error) {
            this.log('Session verification failed', { error: error.message });
            return {
                valid: false,
                reason: 'Verification request failed',
                error: error.message
            };
        }
    }

    /**
     * Check if user is currently authenticated
     * @returns {boolean} Authentication status
     */
    isAuthenticated() {
        return this.sessionManager.validateStoredSession();
    }

    /**
     * Get current user information
     * @returns {Object|null} User data or null if not authenticated
     */
    getCurrentUser() {
        return this.sessionManager.getStoredUser();
    }

    /**
     * Validate login credentials
     * @param {Object} credentials - Credentials to validate
     * @returns {Object} Validation result
     */
    validateCredentials(credentials) {
        const errors = [];

        if (!credentials) {
            errors.push('Credentials are required');
            return { valid: false, errors };
        }

        // Must have either email or username
        if (!credentials.email && !credentials.username) {
            errors.push('Email or username is required');
        }

        // Email format validation if provided
        if (credentials.email && !this.isValidEmail(credentials.email)) {
            errors.push('Invalid email format');
        }

        // Password validation
        if (!credentials.password) {
            errors.push('Password is required');
        } else if (credentials.password.length < 1) {
            errors.push('Password cannot be empty');
        }

        return {
            valid: errors.length === 0,
            errors: errors
        };
    }

    /**
     * Check if an error is recoverable (should try next format)
     * @param {Error} error - Error to check
     * @returns {boolean} Whether error is recoverable
     */
    isRecoverableError(error) {
        const recoverableStatuses = [400, 422]; // Bad request, validation error
        const recoverableMessages = [
            'invalid request format',
            'unexpected field',
            'missing field',
            'validation error'
        ];

        if (recoverableStatuses.includes(error.status)) {
            return true;
        }

        const message = (error.message || '').toLowerCase();
        return recoverableMessages.some(msg => message.includes(msg));
    }

    /**
     * Extract token from cookies
     * @returns {string|null} Token from cookies
     */
    extractTokenFromCookies() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'session_token' || name === 'auth_token') {
                return value;
            }
        }
        return null;
    }

    /**
     * Validate email format
     * @param {string} email - Email to validate
     * @returns {boolean} Whether email is valid
     */
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    /**
     * Log debug information
     * @param {string} message - Log message
     * @param {Object} data - Additional data to log
     */
    log(message, data = {}) {
        if (this.config.debugMode) {
            console.log(`[AdminAuthService] ${message}`, data);
        }
    }
}

// Make available globally
window.AdminAuthService = AdminAuthService;