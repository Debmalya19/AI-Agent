/**
 * Admin Dashboard - API Service
 * Handles all communication with the backend API
 */

const API_BASE_URL = '/api';

const api = {
    /**
     * Get the authorization header
     * @returns {Object} Headers object with Authorization
     */
    getAuthHeader() {
        const token = localStorage.getItem('token');
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
            const response = await fetch(url, options);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'API request failed');
            }
            
            return data;
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    },

    /**
     * Login user
     * @param {string} email - User email
     * @param {string} password - User password
     * @returns {Promise} Promise with login response
     */
    async login(email, password) {
        return this.request('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
    },

    /**
     * Register new user
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
        const queryParams = new URLSearchParams(filters).toString();
        const endpoint = `/support/tickets${queryParams ? '?' + queryParams : ''}`;
        
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
        return this.request(`/support/tickets/${ticketId}`, {
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
        return this.request('/support/tickets', {
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
        return this.request(`/support/tickets/${ticketId}`, {
            method: 'PUT',
            headers: this.getAuthHeader(),
            body: JSON.stringify(ticketData)
        });
    },

    /**
     * Add comment to ticket
     * @param {number} ticketId - Ticket ID
     * @param {string} comment - Comment text
     * @returns {Promise} Promise with comment data
     */
    async addTicketComment(ticketId, comment) {
        return this.request(`/support/tickets/${ticketId}/comments`, {
            method: 'POST',
            headers: this.getAuthHeader(),
            body: JSON.stringify({ comment })
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
     * Get customer satisfaction ratings
     * @param {Object} filters - Optional filters
     * @returns {Promise} Promise with satisfaction ratings
     */
    async getCustomerSatisfaction(filters = {}) {
        const queryParams = new URLSearchParams(filters).toString();
        const endpoint = `/admin/satisfaction${queryParams ? '?' + queryParams : ''}`;
        
        return this.request(endpoint, {
            method: 'GET',
            headers: this.getAuthHeader()
        });
    }
};