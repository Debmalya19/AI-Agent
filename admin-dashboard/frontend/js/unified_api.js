/**
 * Unified Admin Dashboard API Service
 * Updated to work with the unified FastAPI backend
 */

const API_BASE_URL = '/api';

const unifiedApi = {
    /**
     * Get token from cookies
     * @returns {string|null} Token from cookies
     */
    getTokenFromCookies() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'session_token') {
                return value;
            }
        }
        return null;
    },

    /**
     * Get the authorization header
     * @returns {Object} Headers object with Authorization
     */
    getAuthHeader() {
        const token = localStorage.getItem('authToken') || this.getTokenFromCookies();
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        };
    },

    /**
     * Make an API request
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Fetch options
     * @returns {Promise} Promise with response data
     */
    async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        
        try {
            const response = await fetch(url, {
                credentials: 'include', // Include cookies for session management
                ...options
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                // Handle authentication errors
                if (response.status === 401) {
                    this.handleAuthError();
                }
                throw new Error(data.detail || data.message || 'API request failed');
            }
            
            return data;
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    },

    /**
     * Handle authentication errors
     */
    handleAuthError() {
        localStorage.removeItem('authToken');
        localStorage.removeItem('username');
        // Redirect to login or show login modal
        if (window.location.pathname !== '/admin') {
            window.location.href = '/admin';
        }
    },

    /**
     * Login user
     * @param {string} email - User email
     * @param {string} password - User password
     * @returns {Promise} Promise with login response
     */
    async login(email, password) {
        const response = await this.request('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        // Store user info (token is handled via cookies)
        if (response.success) {
            // Check if token is in response or cookies
            const token = response.token || this.getTokenFromCookies();
            if (token) {
                localStorage.setItem('authToken', token);
            }
            localStorage.setItem('username', response.user.username);
            localStorage.setItem('userEmail', response.user.email);
            localStorage.setItem('isAdmin', response.user.is_admin);
        }
        
        return response;
    },

    /**
     * Logout user
     * @returns {Promise} Promise with logout response
     */
    async logout() {
        try {
            const response = await this.request('/auth/logout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            // Clear local storage
            localStorage.removeItem('authToken');
            localStorage.removeItem('username');
            localStorage.removeItem('userEmail');
            localStorage.removeItem('isAdmin');
            
            return response;
        } catch (error) {
            // Clear local storage even if request fails
            localStorage.removeItem('authToken');
            localStorage.removeItem('username');
            localStorage.removeItem('userEmail');
            localStorage.removeItem('isAdmin');
            throw error;
        }
    },

    /**
     * Register new admin user
     * @param {Object} userData - User registration data
     * @returns {Promise} Promise with registration response
     */
    async register(userData) {
        return this.request('/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });
    },

    /**
     * Get user profile
     * @returns {Promise} Promise with user profile data
     */
    async getProfile() {
        return this.request('/auth/profile', {
            method: 'GET',
            headers: this.getAuthHeader()
        });
    },

    /**
     * Update user profile
     * @param {Object} profileData - Updated profile data
     * @returns {Promise} Promise with updated profile
     */
    async updateProfile(profileData) {
        return this.request('/auth/profile', {
            method: 'PUT',
            headers: this.getAuthHeader(),
            body: JSON.stringify(profileData)
        });
    },

    /**
     * Verify session
     * @returns {Promise} Promise with session verification
     */
    async verifySession() {
        return this.request('/auth/verify', {
            method: 'GET',
            headers: this.getAuthHeader()
        });
    },

    /**
     * Get dashboard statistics
     * @returns {Promise} Promise with dashboard stats
     */
    async getDashboardStats() {
        return this.request('/admin/dashboard', {
            method: 'GET',
            headers: this.getAuthHeader()
        });
    },

    /**
     * Get all tickets
     * @param {Object} filters - Optional filters
     * @returns {Promise} Promise with tickets data
     */
    async getTickets(filters = {}) {
        const queryParams = new URLSearchParams();
        Object.keys(filters).forEach(key => {
            if (filters[key] && filters[key] !== 'all') {
                queryParams.append(key, filters[key]);
            }
        });
        
        const endpoint = `/tickets/${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
        
        return this.request(endpoint, {
            method: 'GET',
            headers: this.getAuthHeader()
        });
    },

    /**
     * Get ticket by ID
     * @param {number} ticketId - Ticket ID
     * @returns {Promise} Promise with ticket data
     */
    async getTicket(ticketId) {
        return this.request(`/tickets/${ticketId}`, {
            method: 'GET',
            headers: this.getAuthHeader()
        });
    },

    /**
     * Create new ticket
     * @param {Object} ticketData - Ticket data
     * @returns {Promise} Promise with created ticket
     */
    async createTicket(ticketData) {
        return this.request('/tickets/', {
            method: 'POST',
            headers: this.getAuthHeader(),
            body: JSON.stringify(ticketData)
        });
    },

    /**
     * Update ticket
     * @param {number} ticketId - Ticket ID
     * @param {Object} ticketData - Updated ticket data
     * @returns {Promise} Promise with updated ticket
     */
    async updateTicket(ticketId, ticketData) {
        return this.request(`/tickets/${ticketId}`, {
            method: 'PUT',
            headers: this.getAuthHeader(),
            body: JSON.stringify(ticketData)
        });
    },

    /**
     * Add comment to ticket
     * @param {number} ticketId - Ticket ID
     * @param {string} comment - Comment text
     * @param {boolean} isInternal - Whether comment is internal
     * @returns {Promise} Promise with comment data
     */
    async addTicketComment(ticketId, comment, isInternal = false) {
        return this.request(`/tickets/${ticketId}/comments`, {
            method: 'POST',
            headers: this.getAuthHeader(),
            body: JSON.stringify({ 
                comment: comment,
                is_internal: isInternal
            })
        });
    },

    /**
     * Get all users (admin only)
     * @returns {Promise} Promise with users data
     */
    async getUsers() {
        return this.request('/admin/users', {
            method: 'GET',
            headers: this.getAuthHeader()
        });
    },

    /**
     * Get integration status
     * @returns {Promise} Promise with integration status
     */
    async getIntegrationStatus() {
        return this.request('/admin/integration/status', {
            method: 'GET',
            headers: this.getAuthHeader()
        });
    },

    /**
     * Sync with AI Agent backend
     * @returns {Promise} Promise with sync results
     */
    async syncWithAIAgent() {
        return this.request('/admin/integration/sync', {
            method: 'POST',
            headers: this.getAuthHeader()
        });
    },

    /**
     * Get performance metrics
     * @param {Object} filters - Optional filters
     * @returns {Promise} Promise with performance metrics
     */
    async getPerformanceMetrics(filters = {}) {
        const queryParams = new URLSearchParams(filters).toString();
        const endpoint = `/admin/metrics${queryParams ? '?' + queryParams : ''}`;
        
        return this.request(endpoint, {
            method: 'GET',
            headers: this.getAuthHeader()
        });
    },

    /**
     * Check if user is authenticated
     * @returns {boolean} True if user appears to be authenticated
     */
    isAuthenticated() {
        return !!(localStorage.getItem('authToken') || this.getTokenFromCookies());
    },

    /**
     * Check if user is admin
     * @returns {boolean} True if user is admin
     */
    isAdmin() {
        return localStorage.getItem('isAdmin') === 'true';
    },

    /**
     * Get current username
     * @returns {string} Current username or null
     */
    getCurrentUsername() {
        return localStorage.getItem('username');
    },

    /**
     * Get integration configuration
     * @returns {Promise} Promise with integration config
     */
    async getIntegrationConfig() {
        return this.request('/admin/integration/config', {
            method: 'GET',
            headers: this.getAuthHeader()
        });
    },

    /**
     * Save integration configuration
     * @param {Object} config - Integration configuration
     * @returns {Promise} Promise with save result
     */
    async saveIntegrationConfig(config) {
        return this.request('/admin/integration/config', {
            method: 'POST',
            headers: {
                ...this.getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
    },

    /**
     * Get user by ID
     * @param {string} userId - User ID
     * @returns {Promise} Promise with user data
     */
    async getUser(userId) {
        return this.request(`/admin/users/${userId}`, {
            method: 'GET',
            headers: this.getAuthHeader()
        });
    },

    /**
     * Update user
     * @param {string} userId - User ID
     * @param {Object} userData - User data to update
     * @returns {Promise} Promise with update result
     */
    async updateUser(userId, userData) {
        return this.request(`/admin/users/${userId}`, {
            method: 'PUT',
            headers: {
                ...this.getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(userData)
        });
    },

    /**
     * Create user
     * @param {Object} userData - User data
     * @returns {Promise} Promise with create result
     */
    async createUser(userData) {
        return this.request('/admin/users', {
            method: 'POST',
            headers: {
                ...this.getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(userData)
        });
    },

    /**
     * Reset user password
     * @param {string} userId - User ID
     * @param {string} newPassword - New password
     * @returns {Promise} Promise with reset result
     */
    async resetPassword(userId, newPassword) {
        return this.request(`/admin/users/${userId}/reset-password`, {
            method: 'POST',
            headers: {
                ...this.getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ password: newPassword })
        });
    },

    /**
     * Delete user
     * @param {string} userId - User ID
     * @returns {Promise} Promise with delete result
     */
    async deleteUser(userId) {
        return this.request(`/admin/users/${userId}`, {
            method: 'DELETE',
            headers: this.getAuthHeader()
        });
    }
};

// Make it available globally for backward compatibility
window.unifiedApi = unifiedApi;