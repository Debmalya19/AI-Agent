document.addEventListener('DOMContentLoaded', () => {
    // Initialize dashboard
    initializeDashboard();
});

function initializeDashboard() {
    console.log('Initializing dashboard...');
    
    // Check authentication from multiple sources
    const authToken = localStorage.getItem('authToken');
    const adminToken = localStorage.getItem('admin_session_token');
    const sessionToken = sessionStorage.getItem('admin_session_token');
    
    console.log('Token check:', { authToken: !!authToken, adminToken: !!adminToken, sessionToken: !!sessionToken });
    
    const token = authToken || adminToken || sessionToken;
    
    if (!token) {
        console.log('No token found, checking AdminAuthService...');
        
        // Check if AdminAuthService is available and authenticated
        if (typeof AdminAuthService !== 'undefined' && window.adminAuthService) {
            console.log('AdminAuthService available, checking authentication...');
            
            if (window.adminAuthService.isAuthenticated()) {
                const user = window.adminAuthService.getCurrentUser();
                console.log('User authenticated via AdminAuthService:', user);
                
                if (user) {
                    // Update localStorage for compatibility
                    const sessionToken = window.adminAuthService.sessionManager.getSessionToken();
                    if (sessionToken) {
                        console.log('Updating localStorage with session token');
                        localStorage.setItem('authToken', sessionToken);
                        localStorage.setItem('username', user.username || user.email);
                        loadDashboardData();
                        setupNavigationHandlers();
                        return;
                    }
                }
            } else {
                console.log('AdminAuthService not authenticated');
            }
        } else {
            console.log('AdminAuthService not available');
        }
        
        // Show login modal if not authenticated
        console.log('Showing login modal...');
        showLoginModal();
        return;
    }

    console.log('Token found, loading dashboard data...');
    
    // Load dashboard data
    loadDashboardData();

    // Set up navigation handlers
    setupNavigationHandlers();
}

function showLoginModal() {
    const loginModalElement = document.getElementById('loginModal');
    if (loginModalElement) {
        const loginModal = new bootstrap.Modal(loginModalElement);
        loginModal.show();
    }
}

function setupNavigationHandlers() {
    // Navigation handlers
    const navDashboard = document.getElementById('nav-dashboard');
    if (navDashboard) {
        navDashboard.addEventListener('click', (e) => {
            e.preventDefault();
            showContent('dashboard');
        });
    }

    const navTickets = document.getElementById('nav-tickets');
    if (navTickets) {
        navTickets.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = 'tickets.html';
        });
    }

    const navUsers = document.getElementById('nav-users');
    if (navUsers) {
        navUsers.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = 'users.html';
        });
    }

    const navSettings = document.getElementById('nav-settings');
    if (navSettings) {
        navSettings.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = 'settings.html';
        });
    }

    const navIntegration = document.getElementById('nav-integration');
    if (navIntegration) {
        navIntegration.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = 'integration.html';
        });
    }

    // Refresh button
    const btnRefresh = document.getElementById('btn-refresh');
    if (btnRefresh) {
        btnRefresh.addEventListener('click', () => {
            loadDashboardData();
        });
    }

    // Export button (placeholder)
    const btnExport = document.getElementById('btn-export');
    if (btnExport) {
        btnExport.addEventListener('click', () => {
            alert('Export functionality not implemented yet.');
        });
    }
}

async function loadDashboardData() {
    try {
        // Check if unifiedApi is available
        if (typeof unifiedApi === 'undefined') {
            console.error('unifiedApi not available');
            return;
        }

        // Load ticket statistics
        try {
            const statsResponse = await unifiedApi.request('/tickets/stats', {
                method: 'GET',
                headers: unifiedApi.getAuthHeader()
            });

            if (statsResponse) {
                document.getElementById('total-tickets').textContent = statsResponse.total || 0;
                document.getElementById('open-tickets').textContent = statsResponse.by_status?.open || 0;
                document.getElementById('pending-tickets').textContent = statsResponse.by_status?.pending || 0;
                document.getElementById('urgent-tickets').textContent = statsResponse.by_priority?.urgent || statsResponse.by_priority?.critical || 0;
            }
        } catch (error) {
            console.error('Error loading ticket stats:', error);
        }

        // Load recent tickets
        try {
            const ticketsResponse = await unifiedApi.request('/tickets?limit=10', {
                method: 'GET',
                headers: unifiedApi.getAuthHeader()
            });

            const tbody = document.getElementById('recent-tickets-table');
            tbody.innerHTML = '';

            if (ticketsResponse.tickets && ticketsResponse.tickets.length > 0) {
                ticketsResponse.tickets.forEach(ticket => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${ticket.id}</td>
                        <td>${ticket.title}</td>
                        <td>${ticket.customer_name || 'N/A'}</td>
                        <td><span class="badge bg-${getStatusColor(ticket.status)}">${ticket.status}</span></td>
                        <td><span class="badge bg-${getPriorityColor(ticket.priority)}">${ticket.priority}</span></td>
                        <td>${new Date(ticket.created_at).toLocaleDateString()}</td>
                        <td>
                            <button class="btn btn-sm btn-outline-primary" onclick="viewTicket(${ticket.id})">View</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">No tickets found</td></tr>';
            }
        } catch (error) {
            console.error('Error loading tickets:', error);
            const tbody = document.getElementById('recent-tickets-table');
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Error loading tickets</td></tr>';
        }

    } catch (error) {
        console.error('Error loading dashboard data:', error);
        // Show error message
        const tbody = document.getElementById('recent-tickets-table');
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Error loading tickets</td></tr>';
    }
}

function getStatusColor(status) {
    const colors = {
        'open': 'success',
        'pending': 'warning',
        'closed': 'secondary',
        'resolved': 'info'
    };
    return colors[status.toLowerCase()] || 'secondary';
}

function getPriorityColor(priority) {
    const colors = {
        'low': 'secondary',
        'medium': 'primary',
        'high': 'warning',
        'urgent': 'danger'
    };
    return colors[priority.toLowerCase()] || 'secondary';
}

function viewTicket(ticketId) {
    // Navigate to tickets page with ticket ID
    window.location.href = `tickets.html?ticket=${ticketId}`;
}

function showContent(contentId) {
    // Hide all content sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.add('d-none');
    });

    // Show selected content
    const contentElement = document.getElementById(`content-${contentId}`);
    if (contentElement) {
        contentElement.classList.remove('d-none');
    }

    // Update page title
    const titles = {
        'dashboard': 'Dashboard'
    };
    document.getElementById('page-title').textContent = titles[contentId] || 'Dashboard';
}
