/**
 * Enhanced Authentication Error Handler
 * Provides comprehensive error categorization, user-friendly messages, and debugging support
 */

class AuthErrorHandler {
    constructor() {
        this.debugMode = localStorage.getItem('admin_debug') === 'true';
        
        // Error categories for classification
        this.errorCategories = {
            'FRONTEND': ['network_error', 'javascript_error', 'browser_compatibility', 'timeout'],
            'COMMUNICATION': ['endpoint_not_found', 'invalid_request_format', 'response_parsing_error', 'cors_error'],
            'AUTHENTICATION': ['invalid_credentials', 'user_not_found', 'account_disabled', 'account_locked'],
            'SESSION': ['token_invalid', 'session_expired', 'storage_error', 'session_conflict'],
            'BACKEND': ['database_error', 'server_error', 'configuration_error', 'service_unavailable']
        };

        // User-friendly error messages
        this.userMessages = {
            'invalid_credentials': 'Invalid email or password. Please check your credentials and try again.',
            'user_not_found': 'No account found with this email address.',
            'account_disabled': 'Your account has been disabled. Please contact support.',
            'account_locked': 'Your account has been temporarily locked due to multiple failed login attempts.',
            'network_error': 'Unable to connect to the server. Please check your internet connection.',
            'timeout': 'The request timed out. Please try again.',
            'server_error': 'A server error occurred. Please try again later.',
            'session_expired': 'Your session has expired. Please log in again.',
            'token_invalid': 'Your session is no longer valid. Please log in again.',
            'endpoint_not_found': 'Authentication service is not available. Please contact support.',
            'invalid_request_format': 'There was a problem with your request. Please try again.',
            'browser_compatibility': 'Your browser may not be fully supported. Please try updating your browser.',
            'storage_error': 'Unable to save login information. Please check your browser settings.',
            'cors_error': 'Cross-origin request blocked. Please contact support.',
            'service_unavailable': 'The authentication service is temporarily unavailable.',
            'validation_error': 'Please check your input and try again.'
        };

        // Suggested actions for each error type
        this.suggestedActions = {
            'invalid_credentials': [
                'Verify your email and password are correct',
                'Check if Caps Lock is enabled',
                'Try using username instead of email if available',
                'Use the "Forgot Password" link if available'
            ],
            'network_error': [
                'Check your internet connection',
                'Refresh the page and try again',
                'Try again in a few minutes',
                'Contact support if the problem persists'
            ],
            'session_expired': [
                'Log in again to create a new session',
                'Clear browser data if issues persist',
                'Check if cookies are enabled in your browser'
            ],
            'account_locked': [
                'Wait 15 minutes before trying again',
                'Contact support to unlock your account',
                'Use the "Forgot Password" link to reset your password'
            ],
            'browser_compatibility': [
                'Update your browser to the latest version',
                'Try using a different browser (Chrome, Firefox, Safari)',
                'Enable JavaScript in your browser',
                'Clear browser cache and cookies'
            ],
            'server_error': [
                'Try again in a few minutes',
                'Refresh the page',
                'Contact support if the problem continues'
            ]
        };

        this.log('AuthErrorHandler initialized');
    }

    /**
     * Handle authentication errors with comprehensive categorization
     * @param {number} status - HTTP status code
     * @param {Object} errorData - Error data from response
     * @returns {Object} Formatted error response
     */
    handleAuthError(status, errorData) {
        const errorType = this.categorizeError(status, errorData);
        const category = this.getErrorCategory(errorType);
        
        const errorResponse = {
            success: false,
            error: {
                type: errorType,
                category: category,
                status: status,
                message: this.getUserMessage(errorType),
                technical_message: errorData?.message || errorData?.detail || 'Unknown error',
                suggested_actions: this.getSuggestedActions(errorType),
                timestamp: new Date().toISOString(),
                debug_info: this.debugMode ? this.getDebugInfo(status, errorData) : null
            }
        };

        // Log error for debugging
        this.logError(errorResponse.error);

        // Display error to user
        this.displayError(errorResponse.error);

        // Send to debug endpoint if in debug mode
        if (this.debugMode) {
            this.sendToDebugEndpoint(errorResponse.error);
        }

        return errorResponse;
    }

    /**
     * Handle validation errors
     * @param {Array} validationErrors - Array of validation error messages
     * @returns {Object} Formatted validation error response
     */
    handleValidationError(validationErrors) {
        const errorResponse = {
            success: false,
            error: {
                type: 'validation_error',
                category: 'FRONTEND',
                status: 400,
                message: 'Please correct the following errors:',
                validation_errors: validationErrors,
                suggested_actions: ['Check your input and try again'],
                timestamp: new Date().toISOString()
            }
        };

        this.logError(errorResponse.error);
        this.displayValidationErrors(validationErrors);

        return errorResponse;
    }

    /**
     * Handle network/connectivity errors
     * @param {Object} connectivityInfo - Connectivity check results
     * @returns {Object} Formatted connectivity error response
     */
    handleConnectivityError(connectivityInfo) {
        const errorType = connectivityInfo.serverReachable ? 'endpoint_not_found' : 'network_error';
        
        const errorResponse = {
            success: false,
            error: {
                type: errorType,
                category: 'COMMUNICATION',
                status: 0,
                message: this.getUserMessage(errorType),
                connectivity_info: connectivityInfo,
                suggested_actions: this.getSuggestedActions(errorType),
                timestamp: new Date().toISOString()
            }
        };

        this.logError(errorResponse.error);
        this.displayError(errorResponse.error);

        return errorResponse;
    }

    /**
     * Handle network errors (fetch failures, timeouts, etc.)
     * @param {Error} error - Network error object
     * @returns {Object} Formatted network error response
     */
    handleNetworkError(error) {
        let errorType = 'network_error';
        
        if (error.name === 'AbortError' || error.message.includes('timeout')) {
            errorType = 'timeout';
        } else if (error.message.includes('CORS')) {
            errorType = 'cors_error';
        }

        const errorResponse = {
            success: false,
            error: {
                type: errorType,
                category: 'FRONTEND',
                status: 0,
                message: this.getUserMessage(errorType),
                technical_message: error.message,
                suggested_actions: this.getSuggestedActions(errorType),
                timestamp: new Date().toISOString(),
                debug_info: this.debugMode ? {
                    error_name: error.name,
                    error_stack: error.stack
                } : null
            }
        };

        this.logError(errorResponse.error);
        this.displayError(errorResponse.error);

        return errorResponse;
    }

    /**
     * Categorize error based on status code and error data
     * @param {number} status - HTTP status code
     * @param {Object} errorData - Error data from response
     * @returns {string} Error type
     */
    categorizeError(status, errorData) {
        const message = (errorData?.message || errorData?.detail || '').toLowerCase();

        // Status code based categorization
        switch (status) {
            case 400:
                if (message.includes('validation') || message.includes('invalid format')) {
                    return 'invalid_request_format';
                }
                return 'validation_error';
            
            case 401:
                if (message.includes('invalid') || message.includes('incorrect')) {
                    return 'invalid_credentials';
                } else if (message.includes('expired')) {
                    return 'session_expired';
                } else if (message.includes('token')) {
                    return 'token_invalid';
                }
                return 'invalid_credentials';
            
            case 403:
                if (message.includes('disabled')) {
                    return 'account_disabled';
                } else if (message.includes('locked')) {
                    return 'account_locked';
                }
                return 'account_disabled';
            
            case 404:
                if (message.includes('user') || message.includes('account')) {
                    return 'user_not_found';
                }
                return 'endpoint_not_found';
            
            case 422:
                return 'validation_error';
            
            case 429:
                return 'account_locked';
            
            case 500:
            case 502:
            case 503:
                return 'server_error';
            
            case 504:
                return 'timeout';
            
            default:
                return 'server_error';
        }
    }

    /**
     * Get error category for error type
     * @param {string} errorType - Error type
     * @returns {string} Error category
     */
    getErrorCategory(errorType) {
        for (const [category, types] of Object.entries(this.errorCategories)) {
            if (types.includes(errorType)) {
                return category;
            }
        }
        return 'UNKNOWN';
    }

    /**
     * Get user-friendly message for error type
     * @param {string} errorType - Error type
     * @returns {string} User-friendly message
     */
    getUserMessage(errorType) {
        return this.userMessages[errorType] || 'An unexpected error occurred. Please try again.';
    }

    /**
     * Get suggested actions for error type
     * @param {string} errorType - Error type
     * @returns {Array} Array of suggested actions
     */
    getSuggestedActions(errorType) {
        return this.suggestedActions[errorType] || ['Contact system administrator for assistance'];
    }

    /**
     * Get debug information for error
     * @param {number} status - HTTP status code
     * @param {Object} errorData - Error data
     * @returns {Object} Debug information
     */
    getDebugInfo(status, errorData) {
        return {
            status_code: status,
            response_data: errorData,
            user_agent: navigator.userAgent,
            url: window.location.href,
            timestamp: new Date().toISOString(),
            local_storage_available: this.testLocalStorage(),
            cookies_enabled: navigator.cookieEnabled,
            session_storage_available: this.testSessionStorage()
        };
    }

    /**
     * Display error message to user
     * @param {Object} error - Error object
     */
    displayError(error) {
        // Try to find error display elements
        const errorElements = [
            document.getElementById('login-error'),
            document.getElementById('auth-error'),
            document.querySelector('.alert-danger'),
            document.querySelector('.error-message')
        ].filter(el => el !== null);

        if (errorElements.length > 0) {
            errorElements.forEach(element => {
                element.textContent = error.message;
                element.classList.remove('d-none', 'hidden');
                element.style.display = 'block';
            });
        } else {
            // Fallback: create error display
            this.createErrorDisplay(error);
        }

        // Also show in console for debugging
        console.error('Authentication Error:', error);
    }

    /**
     * Display validation errors
     * @param {Array} validationErrors - Array of validation errors
     */
    displayValidationErrors(validationErrors) {
        const errorMessage = validationErrors.join(', ');
        this.displayError({ message: errorMessage });
    }

    /**
     * Create error display element if none exists
     * @param {Object} error - Error object
     */
    createErrorDisplay(error) {
        // Find a suitable container
        const containers = [
            document.getElementById('login-form'),
            document.querySelector('.modal-body'),
            document.querySelector('main'),
            document.body
        ].filter(el => el !== null);

        if (containers.length > 0) {
            const container = containers[0];
            
            // Remove existing error displays
            const existingErrors = container.querySelectorAll('.auth-error-display');
            existingErrors.forEach(el => el.remove());

            // Create new error display
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger auth-error-display';
            errorDiv.innerHTML = `
                <strong>Error:</strong> ${error.message}
                ${error.suggested_actions ? `
                    <ul class="mt-2 mb-0">
                        ${error.suggested_actions.map(action => `<li>${action}</li>`).join('')}
                    </ul>
                ` : ''}
            `;

            container.insertBefore(errorDiv, container.firstChild);
        }
    }

    /**
     * Log error for debugging
     * @param {Object} error - Error object
     */
    logError(error) {
        const logData = {
            timestamp: error.timestamp,
            type: error.type,
            category: error.category,
            status: error.status,
            message: error.technical_message || error.message,
            debug_info: error.debug_info
        };

        console.error('[AuthErrorHandler]', logData);

        // Store in local storage for debugging (keep last 10 errors)
        try {
            const errorLog = JSON.parse(localStorage.getItem('auth_error_log') || '[]');
            errorLog.unshift(logData);
            errorLog.splice(10); // Keep only last 10 errors
            localStorage.setItem('auth_error_log', JSON.stringify(errorLog));
        } catch (e) {
            console.warn('Failed to store error in local storage:', e);
        }
    }

    /**
     * Send error to debug endpoint
     * @param {Object} error - Error object
     */
    async sendToDebugEndpoint(error) {
        try {
            await fetch('/api/debug/auth-error', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(error)
            });
        } catch (e) {
            console.warn('Failed to send error to debug endpoint:', e);
        }
    }

    /**
     * Test localStorage availability
     * @returns {boolean} Whether localStorage is available
     */
    testLocalStorage() {
        try {
            localStorage.setItem('__test__', 'test');
            localStorage.removeItem('__test__');
            return true;
        } catch (e) {
            return false;
        }
    }

    /**
     * Test sessionStorage availability
     * @returns {boolean} Whether sessionStorage is available
     */
    testSessionStorage() {
        try {
            sessionStorage.setItem('__test__', 'test');
            sessionStorage.removeItem('__test__');
            return true;
        } catch (e) {
            return false;
        }
    }

    /**
     * Get error statistics for debugging
     * @returns {Object} Error statistics
     */
    getErrorStatistics() {
        try {
            const errorLog = JSON.parse(localStorage.getItem('auth_error_log') || '[]');
            const stats = {
                total_errors: errorLog.length,
                by_category: {},
                by_type: {},
                recent_errors: errorLog.slice(0, 5)
            };

            errorLog.forEach(error => {
                stats.by_category[error.category] = (stats.by_category[error.category] || 0) + 1;
                stats.by_type[error.type] = (stats.by_type[error.type] || 0) + 1;
            });

            return stats;
        } catch (e) {
            return { error: 'Failed to get error statistics' };
        }
    }

    /**
     * Clear error log
     */
    clearErrorLog() {
        try {
            localStorage.removeItem('auth_error_log');
            this.log('Error log cleared');
        } catch (e) {
            console.warn('Failed to clear error log:', e);
        }
    }

    /**
     * Log debug information
     * @param {string} message - Log message
     * @param {Object} data - Additional data to log
     */
    log(message, data = {}) {
        if (this.debugMode) {
            console.log(`[AuthErrorHandler] ${message}`, data);
        }
    }
}

// Make available globally
window.AuthErrorHandler = AuthErrorHandler;