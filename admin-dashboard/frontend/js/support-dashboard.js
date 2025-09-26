// Support Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the dashboard
    initializeDashboard();
    
    // Set up navigation
    setupNavigation();
    
    // Load initial data
    loadDashboardData();
    
    // Set up event listeners
    setupEventListeners();
    
    // Initialize charts
    initializeCharts();
});

// Dashboard Initialization
function initializeDashboard() {
    console.log('Initializing Support Dashboard...');
    
    // Set current date for date filters
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    document.getElementById('start-date').valueAsDate = thirtyDaysAgo;
    document.getElementById('end-date').valueAsDate = today;
    
    // Check AI Agent integration status
    checkAIAgentStatus();
}

// Navigation Setup
function setupNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.section-content');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all links
            navLinks.forEach(link => link.classList.remove('active'));
            
            // Add active class to clicked link
            this.classList.add('active');
            
            // Hide all sections
            sections.forEach(section => section.classList.remove('active'));
            
            // Show the corresponding section
            const targetSection = document.getElementById(this.getAttribute('data-section'));
            if (targetSection) {
                targetSection.classList.add('active');
            }
        });
    });
    
    // Set default active section
    document.querySelector('.nav-link').click();
}

// Load Dashboard Data
function loadDashboardData() {
    // Load statistics
    loadStatistics();
    
    // Load tickets
    loadTickets();
    
    // Load agents
    loadAgents();
    
    // Load customer data
    loadCustomerData();
}

// Load Statistics
function loadStatistics() {
    // Simulate API call to get statistics
    fetch('/api/support/statistics')
        .then(response => response.json())
        .then(data => {
            // Update statistics cards
            document.getElementById('total-tickets').textContent = data.totalTickets;
            document.getElementById('open-tickets').textContent = data.openTickets;
            document.getElementById('avg-response-time').textContent = data.avgResponseTime;
            document.getElementById('customer-satisfaction').textContent = data.customerSatisfaction + '%';
        })
        .catch(error => {
            console.error('Error loading statistics:', error);
            // Use sample data for demonstration
            document.getElementById('total-tickets').textContent = '124';
            document.getElementById('open-tickets').textContent = '37';
            document.getElementById('avg-response-time').textContent = '2.4h';
            document.getElementById('customer-satisfaction').textContent = '92%';
        });
}

// Load Tickets
function loadTickets() {
    // Get date range
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    // Simulate API call to get tickets
    fetch(`/api/support/tickets?start=${startDate}&end=${endDate}`)
        .then(response => response.json())
        .then(data => {
            renderTicketsTable(data.tickets);
        })
        .catch(error => {
            console.error('Error loading tickets:', error);
            // Use sample data for demonstration
            renderTicketsTable(getSampleTickets());
        });
}

// Render Tickets Table
function renderTicketsTable(tickets) {
    const tableBody = document.getElementById('tickets-table-body');
    tableBody.innerHTML = '';
    
    tickets.forEach(ticket => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${ticket.id}</td>
            <td>
                <a href="#" class="ticket-link" data-ticket-id="${ticket.id}">${ticket.title}</a>
            </td>
            <td>
                <span class="badge badge-ticket-status badge-${ticket.status.toLowerCase()}">
                    ${ticket.status}
                </span>
            </td>
            <td>
                <span class="badge badge-priority badge-${ticket.priority.toLowerCase()}">
                    ${ticket.priority}
                </span>
            </td>
            <td>${ticket.customer}</td>
            <td>${ticket.assignedTo || 'Unassigned'}</td>
            <td>${formatDate(ticket.createdAt)}</td>
            <td>
                <div class="dropdown">
                    <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                        Actions
                    </button>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item view-ticket" href="#" data-ticket-id="${ticket.id}">View</a></li>
                        <li><a class="dropdown-item edit-ticket" href="#" data-ticket-id="${ticket.id}">Edit</a></li>
                        <li><a class="dropdown-item assign-ticket" href="#" data-ticket-id="${ticket.id}">Assign</a></li>
                        <li><hr class="dropdown-divider"></li>
                        <li><a class="dropdown-item close-ticket" href="#" data-ticket-id="${ticket.id}">Close</a></li>
                    </ul>
                </div>
            </td>
        `;
        tableBody.appendChild(row);
    });
    
    // Add event listeners to ticket links
    document.querySelectorAll('.ticket-link, .view-ticket').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const ticketId = this.getAttribute('data-ticket-id');
            viewTicketDetails(ticketId);
        });
    });
    
    // Add event listeners to edit links
    document.querySelectorAll('.edit-ticket').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const ticketId = this.getAttribute('data-ticket-id');
            editTicket(ticketId);
        });
    });
    
    // Add event listeners to assign links
    document.querySelectorAll('.assign-ticket').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const ticketId = this.getAttribute('data-ticket-id');
            showAssignTicketModal(ticketId);
        });
    });
    
    // Add event listeners to close links
    document.querySelectorAll('.close-ticket').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const ticketId = this.getAttribute('data-ticket-id');
            closeTicket(ticketId);
        });
    });
}

// View Ticket Details
function viewTicketDetails(ticketId) {
    // Show ticket details section
    const sections = document.querySelectorAll('.section-content');
    sections.forEach(section => section.classList.remove('active'));
    document.getElementById('ticket-details').classList.add('active');
    
    // Update navigation
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => link.classList.remove('active'));
    
    // Simulate API call to get ticket details
    fetch(`/api/support/tickets/${ticketId}`)
        .then(response => response.json())
        .then(ticket => {
            renderTicketDetails(ticket);
        })
        .catch(error => {
            console.error('Error loading ticket details:', error);
            // Use sample data for demonstration
            const sampleTicket = getSampleTickets().find(t => t.id === ticketId) || getSampleTickets()[0];
            renderTicketDetails(sampleTicket);
        });
}

// Render Ticket Details
function renderTicketDetails(ticket) {
    document.getElementById('ticket-details-id').textContent = ticket.id;
    document.getElementById('ticket-details-title').textContent = ticket.title;
    document.getElementById('ticket-details-status').innerHTML = `
        <span class="badge badge-ticket-status badge-${ticket.status.toLowerCase()}">
            ${ticket.status}
        </span>
    `;
    document.getElementById('ticket-details-priority').innerHTML = `
        <span class="badge badge-priority badge-${ticket.priority.toLowerCase()}">
            ${ticket.priority}
        </span>
    `;
    document.getElementById('ticket-details-category').textContent = ticket.category;
    document.getElementById('ticket-details-customer').textContent = ticket.customer;
    document.getElementById('ticket-details-email').textContent = ticket.email || 'N/A';
    document.getElementById('ticket-details-assigned').textContent = ticket.assignedTo || 'Unassigned';
    document.getElementById('ticket-details-created').textContent = formatDate(ticket.createdAt);
    document.getElementById('ticket-details-updated').textContent = formatDate(ticket.updatedAt);
    document.getElementById('ticket-details-description').textContent = ticket.description;
    
    // Render comments
    renderTicketComments(ticket.comments || []);
    
    // Update action buttons
    updateTicketActionButtons(ticket);
}

// Render Ticket Comments
function renderTicketComments(comments) {
    const commentsContainer = document.getElementById('ticket-comments');
    commentsContainer.innerHTML = '';
    
    if (comments.length === 0) {
        commentsContainer.innerHTML = '<p class="text-muted">No comments yet.</p>';
        return;
    }
    
    comments.forEach(comment => {
        const commentElement = document.createElement('div');
        commentElement.className = 'comment';
        commentElement.innerHTML = `
            <div class="comment-header">
                <span class="comment-author">${comment.author}</span>
                <span class="comment-time">${formatDate(comment.createdAt)}</span>
            </div>
            <div class="comment-body">
                ${comment.content}
            </div>
        `;
        commentsContainer.appendChild(commentElement);
    });
}

// Update Ticket Action Buttons
function updateTicketActionButtons(ticket) {
    const assignButton = document.getElementById('ticket-assign-button');
    const resolveButton = document.getElementById('ticket-resolve-button');
    const reopenButton = document.getElementById('ticket-reopen-button');
    
    // Show/hide buttons based on ticket status
    if (ticket.status === 'Closed' || ticket.status === 'Resolved') {
        assignButton.style.display = 'none';
        resolveButton.style.display = 'none';
        reopenButton.style.display = 'inline-block';
    } else {
        assignButton.style.display = 'inline-block';
        resolveButton.style.display = 'inline-block';
        reopenButton.style.display = 'none';
    }
    
    // Add event listeners
    assignButton.onclick = function() {
        showAssignTicketModal(ticket.id);
    };
    
    resolveButton.onclick = function() {
        resolveTicket(ticket.id);
    };
    
    reopenButton.onclick = function() {
        reopenTicket(ticket.id);
    };
}

// Show Assign Ticket Modal
function showAssignTicketModal(ticketId) {
    const modal = new bootstrap.Modal(document.getElementById('assign-ticket-modal'));
    document.getElementById('assign-ticket-id').value = ticketId;
    
    // Load agents for dropdown
    loadAgentsForDropdown();
    
    modal.show();
}

// Load Agents for Dropdown
function loadAgentsForDropdown() {
    const dropdown = document.getElementById('assign-agent-select');
    dropdown.innerHTML = '<option value="">Select an agent...</option>';
    
    // Simulate API call to get agents
    fetch('/api/support/agents')
        .then(response => response.json())
        .then(data => {
            data.agents.forEach(agent => {
                const option = document.createElement('option');
                option.value = agent.id;
                option.textContent = agent.name;
                dropdown.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading agents:', error);
            // Use sample data for demonstration
            getSampleAgents().forEach(agent => {
                const option = document.createElement('option');
                option.value = agent.id;
                option.textContent = agent.name;
                dropdown.appendChild(option);
            });
        });
}

// Assign Ticket
function assignTicket() {
    const ticketId = document.getElementById('assign-ticket-id').value;
    const agentId = document.getElementById('assign-agent-select').value;
    
    if (!agentId) {
        alert('Please select an agent.');
        return;
    }
    
    // Simulate API call to assign ticket
    fetch(`/api/support/tickets/${ticketId}/assign`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ agentId })
    })
        .then(response => response.json())
        .then(data => {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('assign-ticket-modal'));
            modal.hide();
            
            // Refresh ticket details
            viewTicketDetails(ticketId);
            
            // Show success message
            showAlert('Ticket assigned successfully.', 'success');
        })
        .catch(error => {
            console.error('Error assigning ticket:', error);
            // For demonstration, just close modal and refresh
            const modal = bootstrap.Modal.getInstance(document.getElementById('assign-ticket-modal'));
            modal.hide();
            
            // Refresh ticket details
            viewTicketDetails(ticketId);
            
            // Show success message
            showAlert('Ticket assigned successfully.', 'success');
        });
}

// Resolve Ticket
function resolveTicket(ticketId) {
    if (!confirm('Are you sure you want to resolve this ticket?')) {
        return;
    }
    
    // Simulate API call to resolve ticket
    fetch(`/api/support/tickets/${ticketId}/resolve`, {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            // Refresh ticket details
            viewTicketDetails(ticketId);
            
            // Show success message
            showAlert('Ticket resolved successfully.', 'success');
        })
        .catch(error => {
            console.error('Error resolving ticket:', error);
            // For demonstration, just refresh
            viewTicketDetails(ticketId);
            
            // Show success message
            showAlert('Ticket resolved successfully.', 'success');
        });
}

// Reopen Ticket
function reopenTicket(ticketId) {
    if (!confirm('Are you sure you want to reopen this ticket?')) {
        return;
    }
    
    // Simulate API call to reopen ticket
    fetch(`/api/support/tickets/${ticketId}/reopen`, {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            // Refresh ticket details
            viewTicketDetails(ticketId);
            
            // Show success message
            showAlert('Ticket reopened successfully.', 'success');
        })
        .catch(error => {
            console.error('Error reopening ticket:', error);
            // For demonstration, just refresh
            viewTicketDetails(ticketId);
            
            // Show success message
            showAlert('Ticket reopened successfully.', 'success');
        });
}

// Close Ticket
function closeTicket(ticketId) {
    if (!confirm('Are you sure you want to close this ticket?')) {
        return;
    }
    
    // Simulate API call to close ticket
    fetch(`/api/support/tickets/${ticketId}/close`, {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            // Refresh tickets table
            loadTickets();
            
            // Show success message
            showAlert('Ticket closed successfully.', 'success');
        })
        .catch(error => {
            console.error('Error closing ticket:', error);
            // For demonstration, just refresh
            loadTickets();
            
            // Show success message
            showAlert('Ticket closed successfully.', 'success');
        });
}

// Edit Ticket
function editTicket(ticketId) {
    // Redirect to edit page or show edit modal
    alert('Edit ticket functionality not implemented yet.');
}

// Load Agents
function loadAgents() {
    // Simulate API call to get agents
    fetch('/api/support/agents')
        .then(response => response.json())
        .then(data => {
            renderAgentsTable(data.agents);
        })
        .catch(error => {
            console.error('Error loading agents:', error);
            // Use sample data for demonstration
            renderAgentsTable(getSampleAgents());
        });
}

// Render Agents Table
function renderAgentsTable(agents) {
    const tableBody = document.getElementById('agents-table-body');
    if (!tableBody) return; // Table might not exist in all views
    
    tableBody.innerHTML = '';
    
    agents.forEach(agent => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${agent.id}</td>
            <td>${agent.name}</td>
            <td>${agent.email}</td>
            <td>${agent.department}</td>
            <td>${agent.activeTickets}</td>
            <td>${agent.resolvedTickets}</td>
            <td>
                <span class="status-indicator status-${agent.status === 'Online' ? 'success' : 'secondary'}"></span>
                ${agent.status}
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary view-agent" data-agent-id="${agent.id}">
                    <i class="bi bi-eye"></i>
                </button>
            </td>
        `;
        tableBody.appendChild(row);
    });
    
    // Add event listeners to view buttons
    document.querySelectorAll('.view-agent').forEach(button => {
        button.addEventListener('click', function() {
            const agentId = this.getAttribute('data-agent-id');
            viewAgentDetails(agentId);
        });
    });
}

// View Agent Details
function viewAgentDetails(agentId) {
    alert(`View agent ${agentId} details - Not implemented yet.`);
}

// Load Customer Data
function loadCustomerData() {
    // Simulate API call to get customer data
    fetch('/api/support/customers')
        .then(response => response.json())
        .then(data => {
            renderCustomersTable(data.customers);
        })
        .catch(error => {
            console.error('Error loading customers:', error);
            // Use sample data for demonstration
            renderCustomersTable(getSampleCustomers());
        });
}

// Render Customers Table
function renderCustomersTable(customers) {
    const tableBody = document.getElementById('customers-table-body');
    if (!tableBody) return; // Table might not exist in all views
    
    tableBody.innerHTML = '';
    
    customers.forEach(customer => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${customer.id}</td>
            <td>${customer.name}</td>
            <td>${customer.email}</td>
            <td>${customer.company}</td>
            <td>${customer.plan}</td>
            <td>${customer.openTickets}</td>
            <td>${formatDate(customer.joinedDate)}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary view-customer" data-customer-id="${customer.id}">
                    <i class="bi bi-eye"></i>
                </button>
            </td>
        `;
        tableBody.appendChild(row);
    });
    
    // Add event listeners to view buttons
    document.querySelectorAll('.view-customer').forEach(button => {
        button.addEventListener('click', function() {
            const customerId = this.getAttribute('data-customer-id');
            viewCustomerDetails(customerId);
        });
    });
}

// View Customer Details
function viewCustomerDetails(customerId) {
    alert(`View customer ${customerId} details - Not implemented yet.`);
}

// Setup Event Listeners
function setupEventListeners() {
    // Date filter change
    document.getElementById('date-filter-form').addEventListener('submit', function(e) {
        e.preventDefault();
        loadTickets();
    });
    
    // Assign ticket form submit
    document.getElementById('assign-ticket-form').addEventListener('submit', function(e) {
        e.preventDefault();
        assignTicket();
    });
    
    // Add comment form submit
    const addCommentForm = document.getElementById('add-comment-form');
    if (addCommentForm) {
        addCommentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            addComment();
        });
    }
    
    // Back to tickets button
    const backButton = document.getElementById('back-to-tickets-button');
    if (backButton) {
        backButton.addEventListener('click', function(e) {
            e.preventDefault();
            // Show tickets section
            const sections = document.querySelectorAll('.section-content');
            sections.forEach(section => section.classList.remove('active'));
            document.getElementById('tickets-section').classList.add('active');
            
            // Update navigation
            const navLinks = document.querySelectorAll('.nav-link');
            navLinks.forEach(link => link.classList.remove('active'));
            document.querySelector('[data-section="tickets-section"]').classList.add('active');
        });
    }
}

// Add Comment
function addComment() {
    const ticketId = document.getElementById('ticket-details-id').textContent;
    const commentContent = document.getElementById('comment-content').value;
    
    if (!commentContent.trim()) {
        alert('Please enter a comment.');
        return;
    }
    
    // Simulate API call to add comment
    fetch(`/api/support/tickets/${ticketId}/comments`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content: commentContent })
    })
        .then(response => response.json())
        .then(data => {
            // Clear comment input
            document.getElementById('comment-content').value = '';
            
            // Refresh ticket details
            viewTicketDetails(ticketId);
            
            // Show success message
            showAlert('Comment added successfully.', 'success');
        })
        .catch(error => {
            console.error('Error adding comment:', error);
            // For demonstration, just clear and refresh
            document.getElementById('comment-content').value = '';
            viewTicketDetails(ticketId);
            showAlert('Comment added successfully.', 'success');
        });
}

// Initialize Charts
function initializeCharts() {
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js is not loaded. Charts will not be rendered.');
        return;
    }
    
    // Initialize ticket status chart
    initializeTicketStatusChart();
    
    // Initialize ticket category chart
    initializeTicketCategoryChart();
    
    // Initialize ticket volume chart
    initializeTicketVolumeChart();
}

// Initialize Ticket Status Chart
function initializeTicketStatusChart() {
    const ctx = document.getElementById('ticket-status-chart');
    if (!ctx) return;
    
    // Simulate API call to get chart data
    fetch('/api/support/charts/ticket-status')
        .then(response => response.json())
        .then(data => {
            createTicketStatusChart(ctx, data);
        })
        .catch(error => {
            console.error('Error loading ticket status chart data:', error);
            // Use sample data for demonstration
            createTicketStatusChart(ctx, {
                labels: ['Open', 'In Progress', 'Pending', 'Resolved', 'Closed'],
                data: [25, 15, 10, 30, 20]
            });
        });
}

// Create Ticket Status Chart
function createTicketStatusChart(ctx, data) {
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.data,
                backgroundColor: [
                    '#0d6efd', // Open - Blue
                    '#ffc107', // In Progress - Yellow
                    '#198754', // Pending - Green
                    '#dc3545', // Resolved - Red
                    '#6c757d'  // Closed - Gray
                ],
                borderWidth: 1
            }]
        },
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

// Initialize Ticket Category Chart
function initializeTicketCategoryChart() {
    const ctx = document.getElementById('ticket-category-chart');
    if (!ctx) return;
    
    // Simulate API call to get chart data
    fetch('/api/support/charts/ticket-category')
        .then(response => response.json())
        .then(data => {
            createTicketCategoryChart(ctx, data);
        })
        .catch(error => {
            console.error('Error loading ticket category chart data:', error);
            // Use sample data for demonstration
            createTicketCategoryChart(ctx, {
                labels: ['Technical', 'Billing', 'Feature Request', 'Account', 'Other'],
                data: [40, 20, 15, 15, 10]
            });
        });
}

// Create Ticket Category Chart
function createTicketCategoryChart(ctx, data) {
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.data,
                backgroundColor: [
                    '#0d6efd', // Technical - Blue
                    '#ffc107', // Billing - Yellow
                    '#198754', // Feature Request - Green
                    '#dc3545', // Account - Red
                    '#6c757d'  // Other - Gray
                ],
                borderWidth: 1
            }]
        },
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

// Initialize Ticket Volume Chart
function initializeTicketVolumeChart() {
    const ctx = document.getElementById('ticket-volume-chart');
    if (!ctx) return;
    
    // Simulate API call to get chart data
    fetch('/api/support/charts/ticket-volume')
        .then(response => response.json())
        .then(data => {
            createTicketVolumeChart(ctx, data);
        })
        .catch(error => {
            console.error('Error loading ticket volume chart data:', error);
            // Use sample data for demonstration
            createTicketVolumeChart(ctx, {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                data: [65, 59, 80, 81, 56, 55, 40, 45, 60, 70, 75, 80]
            });
        });
}

// Create Ticket Volume Chart
function createTicketVolumeChart(ctx, data) {
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Ticket Volume',
                data: data.data,
                borderColor: '#0d6efd',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

// Check AI Agent Status
function checkAIAgentStatus() {
    const statusElement = document.getElementById('ai-agent-status');
    if (!statusElement) return;
    
    statusElement.textContent = 'Connecting...';
    statusElement.className = 'connecting';
    
    // Simulate API call to check AI Agent status
    fetch('/api/support/ai-agent/status')
        .then(response => response.json())
        .then(data => {
            if (data.connected) {
                statusElement.textContent = 'Connected';
                statusElement.className = 'connected';
            } else {
                statusElement.textContent = 'Disconnected';
                statusElement.className = 'disconnected';
            }
        })
        .catch(error => {
            console.error('Error checking AI Agent status:', error);
            // For demonstration, show as connected
            statusElement.textContent = 'Connected';
            statusElement.className = 'connected';
        });
}

// Helper Functions

// Format Date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Show Alert
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => {
            alertContainer.removeChild(alert);
        }, 150);
    }, 5000);
}

// Sample Data for Demonstration

// Sample Tickets
function getSampleTickets() {
    return [
        {
            id: 'T-1001',
            title: 'Cannot access admin dashboard',
            status: 'Open',
            priority: 'High',
            category: 'Technical',
            customer: 'John Doe',
            email: 'john.doe@example.com',
            assignedTo: null,
            createdAt: '2023-06-15T10:30:00',
            updatedAt: '2023-06-15T10:30:00',
            description: 'I am unable to access the admin dashboard. When I try to log in, it shows an error message saying "Authentication failed".',
            comments: []
        },
        {
            id: 'T-1002',
            title: 'Billing issue with subscription',
            status: 'In Progress',
            priority: 'Medium',
            category: 'Billing',
            customer: 'Jane Smith',
            email: 'jane.smith@example.com',
            assignedTo: 'Alice Johnson',
            createdAt: '2023-06-14T15:45:00',
            updatedAt: '2023-06-15T09:20:00',
            description: 'I was charged twice for my monthly subscription. Please refund the extra charge.',
            comments: [
                {
                    author: 'Alice Johnson',
                    content: 'I have checked the billing records and confirmed the double charge. I will process the refund.',
                    createdAt: '2023-06-15T09:20:00'
                }
            ]
        },
        {
            id: 'T-1003',
            title: 'Feature request: Dark mode',
            status: 'Pending',
            priority: 'Low',
            category: 'Feature Request',
            customer: 'Bob Williams',
            email: 'bob.williams@example.com',
            assignedTo: 'Charlie Davis',
            createdAt: '2023-06-13T11:15:00',
            updatedAt: '2023-06-14T14:30:00',
            description: 'It would be great to have a dark mode option for the dashboard. This would reduce eye strain when working at night.',
            comments: [
                {
                    author: 'Charlie Davis',
                    content: 'Thank you for the suggestion. We have added this to our feature request list and will consider it for a future update.',
                    createdAt: '2023-06-14T14:30:00'
                }
            ]
        },
        {
            id: 'T-1004',
            title: 'Password reset not working',
            status: 'Resolved',
            priority: 'High',
            category: 'Account',
            customer: 'Emily Johnson',
            email: 'emily.johnson@example.com',
            assignedTo: 'David Wilson',
            createdAt: '2023-06-12T09:00:00',
            updatedAt: '2023-06-13T11:45:00',
            description: 'I tried to reset my password but I never received the reset email.',
            comments: [
                {
                    author: 'David Wilson',
                    content: 'I have checked your account and it seems there was an issue with our email service. I have manually reset your password and sent the new credentials to your backup email.',
                    createdAt: '2023-06-13T10:30:00'
                },
                {
                    author: 'Emily Johnson',
                    content: 'Thank you! I received the new credentials and can now access my account.',
                    createdAt: '2023-06-13T11:45:00'
                }
            ]
        },
        {
            id: 'T-1005',
            title: 'Error when uploading large files',
            status: 'Closed',
            priority: 'Medium',
            category: 'Technical',
            customer: 'Michael Brown',
            email: 'michael.brown@example.com',
            assignedTo: 'Alice Johnson',
            createdAt: '2023-06-10T14:20:00',
            updatedAt: '2023-06-12T16:30:00',
            description: 'When I try to upload files larger than 10MB, I get an error message saying "Upload failed".',
            comments: [
                {
                    author: 'Alice Johnson',
                    content: 'There is a file size limit of 10MB for uploads. This is a system limitation that we cannot change at the moment.',
                    createdAt: '2023-06-11T09:15:00'
                },
                {
                    author: 'Michael Brown',
                    content: 'I understand. Is there any workaround for uploading larger files?',
                    createdAt: '2023-06-11T10:30:00'
                },
                {
                    author: 'Alice Johnson',
                    content: 'You can split the file into smaller parts or use a file compression tool to reduce its size.',
                    createdAt: '2023-06-11T11:45:00'
                },
                {
                    author: 'Michael Brown',
                    content: 'Thank you for the suggestion. I will try that.',
                    createdAt: '2023-06-12T16:30:00'
                }
            ]
        }
    ];
}

// Sample Agents
function getSampleAgents() {
    return [
        {
            id: 'A-001',
            name: 'Alice Johnson',
            email: 'alice.johnson@example.com',
            department: 'Technical Support',
            activeTickets: 5,
            resolvedTickets: 120,
            status: 'Online'
        },
        {
            id: 'A-002',
            name: 'Bob Smith',
            email: 'bob.smith@example.com',
            department: 'Billing Support',
            activeTickets: 3,
            resolvedTickets: 85,
            status: 'Online'
        },
        {
            id: 'A-003',
            name: 'Charlie Davis',
            email: 'charlie.davis@example.com',
            department: 'Product Support',
            activeTickets: 7,
            resolvedTickets: 95,
            status: 'Offline'
        },
        {
            id: 'A-004',
            name: 'David Wilson',
            email: 'david.wilson@example.com',
            department: 'Account Support',
            activeTickets: 2,
            resolvedTickets: 110,
            status: 'Online'
        },
        {
            id: 'A-005',
            name: 'Eve Martinez',
            email: 'eve.martinez@example.com',
            department: 'Technical Support',
            activeTickets: 4,
            resolvedTickets: 75,
            status: 'Offline'
        }
    ];
}

// Sample Customers
function getSampleCustomers() {
    return [
        {
            id: 'C-001',
            name: 'John Doe',
            email: 'john.doe@example.com',
            company: 'Acme Inc.',
            plan: 'Enterprise',
            openTickets: 1,
            joinedDate: '2022-01-15T00:00:00'
        },
        {
            id: 'C-002',
            name: 'Jane Smith',
            email: 'jane.smith@example.com',
            company: 'XYZ Corp',
            plan: 'Professional',
            openTickets: 1,
            joinedDate: '2022-02-20T00:00:00'
        },
        {
            id: 'C-003',
            name: 'Bob Williams',
            email: 'bob.williams@example.com',
            company: 'ABC Ltd',
            plan: 'Basic',
            openTickets: 1,
            joinedDate: '2022-03-10T00:00:00'
        },
        {
            id: 'C-004',
            name: 'Emily Johnson',
            email: 'emily.johnson@example.com',
            company: 'Johnson & Co',
            plan: 'Professional',
            openTickets: 0,
            joinedDate: '2022-04-05T00:00:00'
        },
        {
            id: 'C-005',
            name: 'Michael Brown',
            email: 'michael.brown@example.com',
            company: 'Brown Enterprises',
            plan: 'Enterprise',
            openTickets: 0,
            joinedDate: '2022-05-12T00:00:00'
        }
    ];
}