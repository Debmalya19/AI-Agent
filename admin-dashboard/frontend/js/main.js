/**
 * Admin Dashboard - Main JavaScript
 * Handles initialization and navigation
 */

// Global state
const state = {
    currentSection: 'dashboard',
    isLoggedIn: false,
    user: null,
    integrationStatus: false
};

// DOM Elements
const elements = {
    // Navigation
    navLinks: document.querySelectorAll('#sidebar .nav-link'),
    pageTitle: document.getElementById('page-title'),
    username: document.getElementById('username'),
    
    // Content sections
    contentSections: document.querySelectorAll('.content-section'),
    dashboardSection: document.getElementById('content-dashboard'),
    integrationSection: document.getElementById('content-integration'),
    
    // Login modal
    loginModal: new bootstrap.Modal(document.getElementById('loginModal')),
    loginForm: document.getElementById('login-form'),
    loginError: document.getElementById('login-error'),
    
    // Buttons
    refreshButton: document.getElementById('btn-refresh'),
    exportButton: document.getElementById('btn-export'),
    syncNowButton: document.getElementById('btn-sync-now'),
    testConnectionButton: document.getElementById('btn-test-connection'),
    viewLogsButton: document.getElementById('btn-view-logs'),
    
    // Integration status
    integrationStatusIndicator: document.getElementById('integration-status-indicator'),
    integrationStatusText: document.getElementById('integration-status-text'),
    integrationStatusMessage: document.getElementById('integration-status-message'),
    usersSynced: document.getElementById('users-synced'),
    ticketsSynced: document.getElementById('tickets-synced'),
    lastSyncTime: document.getElementById('last-sync-time'),
    
    // Forms
    integrationConfigForm: document.getElementById('integration-config-form')
};

/**
 * Initialize the application
 */
function init() {
    // Wait for unifiedApi to be available
    if (typeof unifiedApi === 'undefined') {
        setTimeout(init, 100);
        return;
    }
    
    // Check authentication status
    checkAuthStatus();
    
    // Set up event listeners
    setupEventListeners();
    
    // Load initial data if authenticated
    if (unifiedApi.isAuthenticated()) {
        loadDashboardData();
        checkIntegrationStatus();
    }
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Navigation
    elements.navLinks.forEach(link => {
        link.addEventListener('click', handleNavigation);
    });
    
    // Login form
    elements.loginForm.addEventListener('submit', handleLogin);
    
    // Buttons
    elements.refreshButton.addEventListener('click', handleRefresh);
    elements.exportButton.addEventListener('click', handleExport);
    elements.syncNowButton.addEventListener('click', handleSyncNow);
    elements.testConnectionButton.addEventListener('click', handleTestConnection);
    elements.viewLogsButton.addEventListener('click', handleViewLogs);
    
    // Forms
    elements.integrationConfigForm.addEventListener('submit', handleSaveConfig);
    
    // Logout
    document.getElementById('nav-logout').addEventListener('click', handleLogout);
}

/**
 * Check authentication status
 */
function checkAuthStatus() {
    const token = localStorage.getItem('authToken');
    
    if (token && typeof unifiedApi !== 'undefined') {
        // Validate token with the server
        unifiedApi.verifySession()
            .then(response => {
                if (response.success) {
                    state.isLoggedIn = true;
                    state.user = response.user;
                    updateUserInfo();
                } else {
                    // Token is invalid
                    localStorage.removeItem('authToken');
                    localStorage.removeItem('username');
                    localStorage.removeItem('userEmail');
                    localStorage.removeItem('isAdmin');
                    showLoginModal();
                }
            })
            .catch(error => {
                console.error('Error checking auth status:', error);
                localStorage.removeItem('authToken');
                localStorage.removeItem('username');
                localStorage.removeItem('userEmail');
                localStorage.removeItem('isAdmin');
                showLoginModal();
            });
    } else {
        showLoginModal();
    }
}

/**
 * Show login modal
 */
function showLoginModal() {
    elements.loginModal.show();
}

/**
 * Handle login form submission
 */
function handleLogin(event) {
    event.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    if (typeof unifiedApi !== 'undefined') {
        unifiedApi.login(email, password)
            .then(response => {
                if (response.success) {
                    // Token is already saved by unifiedApi
                    state.isLoggedIn = true;
                    state.user = response.user;
                    
                    // Update UI
                    updateUserInfo();
                    elements.loginModal.hide();
                    
                    // Load dashboard data
                    loadDashboardData();
                } else {
                    // Show error
                    elements.loginError.textContent = response.message;
                    elements.loginError.classList.remove('d-none');
                }
            })
            .catch(error => {
                console.error('Login error:', error);
                elements.loginError.textContent = 'An error occurred. Please try again.';
                elements.loginError.classList.remove('d-none');
            });
    }
}

/**
 * Handle logout
 */
function handleLogout(event) {
    event.preventDefault();
    
    if (typeof unifiedApi !== 'undefined') {
        unifiedApi.logout()
            .then(() => {
                state.isLoggedIn = false;
                state.user = null;
                showLoginModal();
            })
            .catch(error => {
                console.error('Logout error:', error);
                // Clear storage anyway
                localStorage.removeItem('authToken');
                localStorage.removeItem('username');
                localStorage.removeItem('userEmail');
                localStorage.removeItem('isAdmin');
                state.isLoggedIn = false;
                state.user = null;
                showLoginModal();
            });
    } else {
        // Fallback logout
        localStorage.removeItem('authToken');
        localStorage.removeItem('username');
        localStorage.removeItem('userEmail');
        localStorage.removeItem('isAdmin');
        state.isLoggedIn = false;
        state.user = null;
        showLoginModal();
    }
}

/**
 * Update user information in the UI
 */
function updateUserInfo() {
    if (state.user) {
        elements.username.textContent = state.user.username;
    }
}

/**
 * Handle navigation
 */
function handleNavigation(event) {
    event.preventDefault();
    
    // Get the navigation target from the ID
    const navId = event.currentTarget.id;
    const section = navId.replace('nav-', '');
    
    // Update active navigation link
    elements.navLinks.forEach(link => {
        link.classList.remove('active');
    });
    event.currentTarget.classList.add('active');
    
    // Update page title
    elements.pageTitle.textContent = section.charAt(0).toUpperCase() + section.slice(1);
    
    // Show the corresponding section
    elements.contentSections.forEach(section => {
        section.classList.add('d-none');
    });
    
    const contentSection = document.getElementById(`content-${section}`);
    if (contentSection) {
        contentSection.classList.remove('d-none');
        state.currentSection = section;
        
        // Load section-specific data
        if (section === 'dashboard') {
            loadDashboardData();
        } else if (section === 'integration') {
            checkIntegrationStatus();
        }
    }
}

/**
 * Handle refresh button click
 */
function handleRefresh() {
    if (state.currentSection === 'dashboard') {
        loadDashboardData();
    } else if (state.currentSection === 'integration') {
        checkIntegrationStatus();
    }
}

/**
 * Handle export button click
 */
function handleExport() {
    alert('Export functionality would be implemented here.');
}

/**
 * Load dashboard data
 */
function loadDashboardData() {
    if (!state.isLoggedIn || typeof unifiedApi === 'undefined') return;
    
    // Get dashboard stats
    unifiedApi.getDashboardStats()
        .then(response => {
            if (response.success) {
                updateDashboardUI(response.stats);
            }
        })
        .catch(error => {
            console.error('Error loading dashboard data:', error);
        });
}

/**
 * Update dashboard UI with data
 */
function updateDashboardUI(stats) {
    // Update ticket counts
    document.getElementById('total-tickets').textContent = stats.tickets.total;
    document.getElementById('open-tickets').textContent = stats.tickets.open;
    document.getElementById('pending-tickets').textContent = stats.tickets.pending || 0;
    document.getElementById('urgent-tickets').textContent = stats.tickets.urgent || 0;
    
    // Update recent tickets table
    const recentTicketsTable = document.getElementById('recent-tickets-table');
    recentTicketsTable.innerHTML = '';
    
    if (stats.recent_tickets && stats.recent_tickets.length > 0) {
        stats.recent_tickets.forEach(ticket => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${ticket.id}</td>
                <td>${ticket.title}</td>
                <td>${ticket.customer_name || 'N/A'}</td>
                <td><span class="badge bg-${getStatusBadgeClass(ticket.status)}">${ticket.status}</span></td>
                <td><span class="badge bg-${getPriorityBadgeClass(ticket.priority)}">${ticket.priority}</span></td>
                <td>${formatDate(ticket.created_at)}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary btn-icon" onclick="viewTicket(${ticket.id})">
                        <i class="bi bi-eye"></i>
                    </button>
                </td>
            `;
            recentTicketsTable.appendChild(row);
        });
    } else {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="7" class="text-center">No recent tickets</td>';
        recentTicketsTable.appendChild(row);
    }
    
    // Update charts
    updateDashboardCharts(stats);
}

/**
 * Update dashboard charts
 */
function updateDashboardCharts(stats) {
    // Sample data for charts
    const activityData = {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [
            {
                label: 'New Tickets',
                data: [5, 8, 12, 7, 10, 4, 6],
                backgroundColor: 'rgba(13, 110, 253, 0.2)',
                borderColor: 'rgba(13, 110, 253, 1)',
                borderWidth: 2
            },
            {
                label: 'Resolved Tickets',
                data: [3, 5, 8, 4, 7, 3, 5],
                backgroundColor: 'rgba(40, 167, 69, 0.2)',
                borderColor: 'rgba(40, 167, 69, 1)',
                borderWidth: 2
            }
        ]
    };
    
    const categoryData = {
        labels: ['Technical', 'Billing', 'Feature Request', 'Bug', 'Other'],
        datasets: [{
            data: [12, 8, 5, 7, 3],
            backgroundColor: [
                'rgba(13, 110, 253, 0.7)',
                'rgba(220, 53, 69, 0.7)',
                'rgba(40, 167, 69, 0.7)',
                'rgba(255, 193, 7, 0.7)',
                'rgba(108, 117, 125, 0.7)'
            ],
            borderWidth: 1
        }]
    };
    
    // Create or update activity chart
    const activityCtx = document.getElementById('ticketActivityChart').getContext('2d');
    if (window.activityChart) {
        window.activityChart.data = activityData;
        window.activityChart.update();
    } else {
        window.activityChart = new Chart(activityCtx, {
            type: 'line',
            data: activityData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }
    
    // Create or update category chart
    const categoryCtx = document.getElementById('ticketCategoriesChart').getContext('2d');
    if (window.categoryChart) {
        window.categoryChart.data = categoryData;
        window.categoryChart.update();
    } else {
        window.categoryChart = new Chart(categoryCtx, {
            type: 'doughnut',
            data: categoryData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
}

/**
 * Check integration status
 */
function checkIntegrationStatus() {
    if (!state.isLoggedIn || typeof unifiedApi === 'undefined') return;
    
    unifiedApi.getIntegrationStatus()
        .then(response => {
            if (response.success) {
                updateIntegrationUI(response);
            }
        })
        .catch(error => {
            console.error('Error checking integration status:', error);
            showIntegrationError();
        });
}

/**
 * Update integration UI
 */
function updateIntegrationUI(data) {
    state.integrationStatus = data.ai_agent_backend_available;
    
    // Update status indicator
    elements.integrationStatusIndicator.className = 'status-indicator ' + 
        (state.integrationStatus ? 'online' : 'offline');
    
    // Update status text
    elements.integrationStatusText.textContent = state.integrationStatus ? 
        'Integration Active' : 'Integration Inactive';
    
    // Update status message
    elements.integrationStatusMessage.textContent = data.message;
    
    // Update sync button state
    elements.syncNowButton.disabled = !state.integrationStatus;
    
    // Sample data for demonstration
    elements.usersSynced.textContent = '24';
    elements.ticketsSynced.textContent = '156';
    elements.lastSyncTime.textContent = formatDate(new Date());
    
    // Update form fields
    document.getElementById('ai-agent-url').value = 'http://localhost:8000';
}

/**
 * Show integration error
 */
function showIntegrationError() {
    elements.integrationStatusIndicator.className = 'status-indicator offline';
    elements.integrationStatusText.textContent = 'Connection Error';
    elements.integrationStatusMessage.textContent = 'Unable to connect to the server. Please check your network connection and try again.';
    elements.syncNowButton.disabled = true;
}

/**
 * Handle sync now button click
 */
function handleSyncNow() {
    if (!state.integrationStatus) return;
    
    // Show loading state
    elements.syncNowButton.disabled = true;
    elements.syncNowButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Syncing...';
    
    unifiedApi.syncWithAIAgent()
        .then(response => {
            if (response.success) {
                // Update UI with sync results
                elements.usersSynced.textContent = response.sync_results.customers_synced;
                elements.ticketsSynced.textContent = response.sync_results.tickets_synced;
                elements.lastSyncTime.textContent = formatDate(new Date());
                
                // Show success message
                alert('Synchronization completed successfully!');
            } else {
                alert('Synchronization failed: ' + response.message);
            }
        })
        .catch(error => {
            console.error('Sync error:', error);
            alert('An error occurred during synchronization. Please try again.');
        })
        .finally(() => {
            // Reset button state
            elements.syncNowButton.disabled = false;
            elements.syncNowButton.innerHTML = '<i class="bi bi-arrow-repeat me-2"></i> Synchronize Now';
        });
}

/**
 * Handle test connection button click
 */
function handleTestConnection() {
    // Show loading state
    elements.testConnectionButton.disabled = true;
    elements.testConnectionButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Testing...';
    
    // Simulate API call
    setTimeout(() => {
        checkIntegrationStatus();
        
        // Reset button state
        elements.testConnectionButton.disabled = false;
        elements.testConnectionButton.innerHTML = '<i class="bi bi-lightning me-2"></i> Test Connection';
    }, 1500);
}

/**
 * Handle view logs button click
 */
function handleViewLogs() {
    alert('Integration logs would be displayed here.');
}

/**
 * Handle save config form submission
 */
function handleSaveConfig(event) {
    event.preventDefault();
    
    const url = document.getElementById('ai-agent-url').value;
    const interval = document.getElementById('sync-interval').value;
    const autoSync = document.getElementById('auto-sync').checked;
    
    // Simulate API call
    setTimeout(() => {
        alert('Configuration saved successfully!');
    }, 500);
}

/**
 * Get status badge class
 */
function getStatusBadgeClass(status) {
    switch (status.toUpperCase()) {
        case 'OPEN':
            return 'success';
        case 'PENDING':
            return 'warning';
        case 'RESOLVED':
            return 'secondary';
        default:
            return 'primary';
    }
}

/**
 * Get priority badge class
 */
function getPriorityBadgeClass(priority) {
    switch (priority.toUpperCase()) {
        case 'LOW':
            return 'success';
        case 'MEDIUM':
            return 'warning';
        case 'HIGH':
            return 'danger';
        default:
            return 'primary';
    }
}

/**
 * Format date
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * View ticket details
 */
function viewTicket(ticketId) {
    alert(`View ticket ${ticketId} details`);
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', init);