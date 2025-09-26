/**
 * Admin Dashboard - Ticket Management
 * Handles ticket-related functionality
 */

// Ticket state
const ticketState = {
    currentTicket: null,
    tickets: [],
    filters: {
        status: 'all',
        priority: 'all',
        assignee: 'all',
        search: ''
    },
    pagination: {
        page: 1,
        limit: 10,
        total: 0
    },
    loading: false,
    searchTimeout: null
};

/**
 * Initialize ticket management
 */
function initTicketManagement() {
    console.log('Initializing ticket management...');
    
    // Wait for unifiedApi to be available
    if (typeof unifiedApi === 'undefined') {
        setTimeout(initTicketManagement, 100);
        return;
    }
    
    // Set up event listeners
    setupTicketEventListeners();
    
    // Load initial tickets
    loadTickets();
}

/**
 * Set up ticket event listeners
 */
function setupTicketEventListeners() {
    // Refresh button
    const refreshBtn = document.getElementById('btn-refresh-tickets');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            showLoadingState();
            loadTickets();
        });
    }
    
    // New ticket button
    const newTicketBtn = document.getElementById('btn-new-ticket');
    if (newTicketBtn) {
        newTicketBtn.addEventListener('click', showNewTicketModal);
    }
    
    // Filter dropdowns
    const statusFilter = document.getElementById('status-filter');
    const priorityFilter = document.getElementById('priority-filter');
    const assigneeFilter = document.getElementById('assignee-filter');
    
    if (statusFilter) {
        statusFilter.addEventListener('change', (e) => {
            ticketState.filters.status = e.target.value;
            ticketState.pagination.page = 1; // Reset to first page
            loadTickets();
        });
    }
    
    if (priorityFilter) {
        priorityFilter.addEventListener('change', (e) => {
            ticketState.filters.priority = e.target.value;
            ticketState.pagination.page = 1; // Reset to first page
            loadTickets();
        });
    }
    
    if (assigneeFilter) {
        assigneeFilter.addEventListener('change', (e) => {
            ticketState.filters.assignee = e.target.value;
            ticketState.pagination.page = 1; // Reset to first page
            loadTickets();
        });
    }
    
    // Search input with real-time filtering
    const searchInput = document.getElementById('ticket-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            ticketState.filters.search = e.target.value;
            ticketState.pagination.page = 1; // Reset to first page
            
            // Clear previous timeout
            if (ticketState.searchTimeout) {
                clearTimeout(ticketState.searchTimeout);
            }
            
            // Debounce search with 300ms delay
            ticketState.searchTimeout = setTimeout(() => {
                loadTickets();
            }, 300);
        });
    }
    
    // New ticket form submission
    const newTicketForm = document.getElementById('new-ticket-form');
    if (newTicketForm) {
        newTicketForm.addEventListener('submit', handleNewTicketSubmit);
    }
    
    // Edit ticket form submission
    const editTicketForm = document.getElementById('edit-ticket-form');
    if (editTicketForm) {
        editTicketForm.addEventListener('submit', handleEditTicketSubmit);
    }
}

/**
 * Load tickets with current filters and pagination
 */
async function loadTickets() {
    console.log('Loading tickets with filters:', ticketState.filters);
    
    // Set loading state
    ticketState.loading = true;
    
    // Check if unifiedApi is available
    if (typeof unifiedApi === 'undefined') {
        uiFeedback.showError('API not available');
        ticketState.loading = false;
        return;
    }
    
    // Prepare filter parameters
    const params = new URLSearchParams();
    if (ticketState.filters.status && ticketState.filters.status !== 'all') {
        params.append('status', ticketState.filters.status);
    }
    if (ticketState.filters.priority && ticketState.filters.priority !== 'all') {
        params.append('priority', ticketState.filters.priority);
    }
    if (ticketState.filters.search && ticketState.filters.search.trim()) {
        params.append('search', ticketState.filters.search.trim());
    }
    params.append('limit', ticketState.pagination.limit);
    params.append('skip', (ticketState.pagination.page - 1) * ticketState.pagination.limit);
    
    const queryString = params.toString();
    const endpoint = `/tickets/${queryString ? '?' + queryString : ''}`;
    
    try {
        // Show table skeleton loading
        uiFeedback.showTableSkeleton('#tickets-table-body', 5, 9);
        
        // Fetch tickets from API
        const response = await uiFeedback.handleApiRequest(
            () => unifiedApi.request(endpoint, {
                method: 'GET',
                headers: unifiedApi.getAuthHeader()
            }),
            null,
            'Loading tickets...'
        );
        
        console.log('Tickets response:', response);
        ticketState.loading = false;
        
        if (response && response.tickets) {
            ticketState.tickets = response.tickets;
            ticketState.pagination.total = response.total || response.tickets.length;
            
            renderTicketList();
            updatePagination();
            updateTicketStats();
        } else {
            // Show empty state
            uiFeedback.showEmptyState(
                '#tickets-table-body',
                'No tickets found',
                'There are no tickets matching your current filters.',
                'fas fa-ticket-alt',
                'Create New Ticket',
                showNewTicketModal
            );
        }
    } catch (error) {
        console.error('Error loading tickets:', error);
        ticketState.loading = false;
        
        // Show error state in table
        const tableBody = document.getElementById('tickets-table-body');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center py-4">
                        <i class="fas fa-exclamation-triangle display-4 text-danger mb-3"></i>
                        <p class="text-danger mb-3">Failed to load tickets</p>
                        <button class="btn btn-outline-primary" onclick="loadTickets()">
                            <i class="fas fa-redo me-1"></i> Retry
                        </button>
                    </td>
                </tr>
            `;
        }
    }
}

/**
 * Render ticket list
 */
function renderTicketList() {
    const tableBody = document.getElementById('tickets-table-body');
    if (!tableBody) return;
    
    // Clear table body
    tableBody.innerHTML = '';
    
    if (ticketState.tickets.length === 0) {
        showEmptyTickets();
        return;
    }
    
    // Create ticket rows
    ticketState.tickets.forEach(ticket => {
        const row = document.createElement('tr');
        row.className = 'ticket-row';
        row.innerHTML = `
            <td class="fw-bold">#${ticket.id}</td>
            <td>
                <div class="ticket-title">${escapeHtml(ticket.title || 'Untitled')}</div>
                <small class="text-muted">${escapeHtml(ticket.category || 'general')}</small>
            </td>
            <td>${escapeHtml(ticket.customer_name || 'Unknown')}</td>
            <td><span class="text-muted">Unassigned</span></td>
            <td><span class="badge bg-${getStatusBadgeClass(ticket.status)}">${capitalizeFirst(ticket.status || 'open')}</span></td>
            <td><span class="badge bg-${getPriorityBadgeClass(ticket.priority)}">${capitalizeFirst(ticket.priority || 'medium')}</span></td>
            <td>
                <small class="text-muted">${formatDate(ticket.created_at)}</small>
            </td>
            <td>
                <small class="text-muted">${formatDate(ticket.updated_at || ticket.created_at)}</small>
            </td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-outline-primary" onclick="viewTicket(${ticket.id})" title="View Ticket">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="editTicket(${ticket.id})" title="Edit Ticket">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteTicket(${ticket.id})" title="Delete Ticket">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        `;
        tableBody.appendChild(row);
    });
}



/**
 * Update pagination
 */
function updatePagination() {
    const paginationContainer = document.getElementById('tickets-pagination');
    const paginationInfo = document.querySelector('.pagination-info');
    
    // Update pagination info
    if (paginationInfo) {
        const start = ticketState.tickets.length > 0 ? (ticketState.pagination.page - 1) * ticketState.pagination.limit + 1 : 0;
        const end = Math.min(start + ticketState.tickets.length - 1, ticketState.pagination.total);
        paginationInfo.textContent = `Showing ${start} to ${end} of ${ticketState.pagination.total} tickets`;
    }
    
    // Update pagination controls
    if (paginationContainer) {
        const totalPages = Math.ceil(ticketState.pagination.total / ticketState.pagination.limit);
        const currentPage = ticketState.pagination.page;
        
        let paginationHTML = '';
        
        // Previous button
        paginationHTML += `
            <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'tabindex="-1"' : ''}>
                    <i class="bi bi-chevron-left"></i>
                </a>
            </li>
        `;
        
        // Page numbers
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);
        
        if (startPage > 1) {
            paginationHTML += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(1)">1</a></li>`;
            if (startPage > 2) {
                paginationHTML += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }
        
        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="changePage(${i})">${i}</a>
                </li>
            `;
        }
        
        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                paginationHTML += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
            paginationHTML += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(${totalPages})">${totalPages}</a></li>`;
        }
        
        // Next button
        paginationHTML += `
            <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="changePage(${currentPage + 1})" ${currentPage === totalPages ? 'tabindex="-1"' : ''}>
                    <i class="bi bi-chevron-right"></i>
                </a>
            </li>
        `;
        
        paginationContainer.innerHTML = paginationHTML;
    }
}

/**
 * Change page
 * @param {number} page - Page number
 */
function changePage(page) {
    if (page < 1 || page > Math.ceil(ticketState.pagination.total / ticketState.pagination.limit)) {
        return;
    }
    
    ticketState.pagination.page = page;
    loadTickets();
}

/**
 * Update ticket statistics
 */
function updateTicketStats() {
    // This could be used to update any ticket statistics displayed on the page
    console.log(`Loaded ${ticketState.tickets.length} tickets of ${ticketState.pagination.total} total`);
}



/**
 * Get status badge class
 * @param {string} status - Status value
 * @returns {string} Bootstrap badge class
 */
function getStatusBadgeClass(status) {
    if (!status) return 'secondary';
    
    switch (status.toLowerCase()) {
        case 'open':
            return 'success';
        case 'pending':
        case 'in_progress':
            return 'warning';
        case 'resolved':
            return 'info';
        case 'closed':
            return 'secondary';
        default:
            return 'primary';
    }
}

/**
 * Get priority badge class
 * @param {string} priority - Priority value
 * @returns {string} Bootstrap badge class
 */
function getPriorityBadgeClass(priority) {
    if (!priority) return 'secondary';
    
    switch (priority.toLowerCase()) {
        case 'low':
            return 'success';
        case 'medium':
            return 'primary';
        case 'high':
            return 'warning';
        case 'urgent':
        case 'critical':
            return 'danger';
        default:
            return 'secondary';
    }
}

/**
 * Format date
 * @param {string} dateString - Date string
 * @returns {string} Formatted date
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (error) {
        return 'Invalid Date';
    }
}

/**
 * Show new ticket modal
 */
function showNewTicketModal() {
    const modal = document.getElementById('new-ticket-modal');
    if (modal) {
        // Reset form
        const form = document.getElementById('new-ticket-form');
        if (form) {
            form.reset();
            clearFormErrors(form);
        }
        
        // Load customers for dropdown
        loadCustomersForDropdown();
        
        // Show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

/**
 * Handle new ticket form submission
 * @param {Event} e - Form submit event
 */
async function handleNewTicketSubmit(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    
    // Validate form
    if (!validateTicketForm(form)) {
        return;
    }
    
    // Prepare ticket data
    const ticketData = {
        title: formData.get('subject'),
        description: formData.get('description'),
        priority: formData.get('priority') || 'medium',
        category: formData.get('category') || 'general',
        customer_id: formData.get('customer') || null
    };
    
    // Handle form submission with loading state
    await uiFeedback.handleFormSubmit(form, async () => {
        // Create ticket
        const response = await unifiedApi.createTicket(ticketData);
        console.log('Ticket created:', response);
        
        // Hide modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('new-ticket-modal'));
        modal.hide();
        
        // Show success message
        uiFeedback.showSuccess('Ticket created successfully!');
        
        // Reload tickets
        loadTickets();
    }, 'Creating Ticket...');
}

/**
 * View ticket details
 * @param {number} ticketId - Ticket ID
 */
function viewTicket(ticketId) {
    // Find ticket in current list
    const ticket = ticketState.tickets.find(t => t.id === ticketId);
    if (!ticket) {
        showAlert('Ticket not found', 'danger');
        return;
    }
    
    // Show ticket details modal
    showTicketDetailsModal(ticket);
}

/**
 * Edit ticket
 * @param {number} ticketId - Ticket ID
 */
function editTicket(ticketId) {
    // Find ticket in current list
    const ticket = ticketState.tickets.find(t => t.id === ticketId);
    if (!ticket) {
        showAlert('Ticket not found', 'danger');
        return;
    }
    
    // Show edit ticket modal
    showEditTicketModal(ticket);
}

/**
 * Delete ticket
 * @param {number} ticketId - Ticket ID
 */
async function deleteTicket(ticketId) {
    // Find ticket in current list
    const ticket = ticketState.tickets.find(t => t.id === ticketId);
    if (!ticket) {
        uiFeedback.showError('Ticket not found');
        return;
    }
    
    // Confirm deletion
    if (confirm(`Are you sure you want to delete ticket #${ticketId} "${ticket.title}"?`)) {
        try {
            // Show loading state on the delete button
            const deleteBtn = document.querySelector(`button[onclick="deleteTicket(${ticketId})"]`);
            uiFeedback.showButtonLoading(deleteBtn, 'Deleting...');
            
            // Delete ticket (placeholder - would need API endpoint)
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Remove from local state
            ticketState.tickets = ticketState.tickets.filter(t => t.id !== ticketId);
            ticketState.pagination.total--;
            renderTicketList();
            updatePagination();
            
            uiFeedback.showSuccess('Ticket deleted successfully!');
        } catch (error) {
            console.error('Error deleting ticket:', error);
            uiFeedback.showError('Failed to delete ticket: ' + error.message);
        } finally {
            const deleteBtn = document.querySelector(`button[onclick="deleteTicket(${ticketId})"]`);
            if (deleteBtn) {
                uiFeedback.hideButtonLoading(deleteBtn);
            }
        }
    }
}

/**
 * Show ticket details modal
 * @param {Object} ticket - Ticket object
 */
function showTicketDetailsModal(ticket) {
    // Create or update ticket details modal
    let modal = document.getElementById('ticket-details-modal');
    if (!modal) {
        modal = createTicketDetailsModal();
        document.body.appendChild(modal);
    }
    
    // Populate modal with ticket data
    modal.querySelector('.modal-title').textContent = `Ticket #${ticket.id} - ${ticket.title}`;
    modal.querySelector('#ticket-details-content').innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6>Customer</h6>
                <p>${escapeHtml(ticket.customer_name || 'Unknown')}</p>
                
                <h6>Status</h6>
                <p><span class="badge bg-${getStatusBadgeClass(ticket.status)}">${capitalizeFirst(ticket.status || 'open')}</span></p>
                
                <h6>Priority</h6>
                <p><span class="badge bg-${getPriorityBadgeClass(ticket.priority)}">${capitalizeFirst(ticket.priority || 'medium')}</span></p>
            </div>
            <div class="col-md-6">
                <h6>Category</h6>
                <p>${capitalizeFirst(ticket.category || 'general')}</p>
                
                <h6>Created</h6>
                <p>${formatDate(ticket.created_at)}</p>
                
                <h6>Last Updated</h6>
                <p>${formatDate(ticket.updated_at || ticket.created_at)}</p>
            </div>
        </div>
        <div class="mt-3">
            <h6>Description</h6>
            <div class="border rounded p-3 bg-light">
                ${escapeHtml(ticket.description || 'No description provided').replace(/\n/g, '<br>')}
            </div>
        </div>
    `;
    
    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Show edit ticket modal
 * @param {Object} ticket - Ticket object
 */
function showEditTicketModal(ticket) {
    // For now, show an alert - full implementation would require edit modal
    alert(`Edit ticket functionality would be implemented here for ticket #${ticket.id}`);
}

/**
 * Load customers for dropdown
 */
async function loadCustomersForDropdown() {
    const customerSelect = document.getElementById('ticket-customer');
    if (!customerSelect) return;
    
    try {
        // Show loading option
        customerSelect.innerHTML = '<option value="">Loading customers...</option>';
        customerSelect.disabled = true;
        
        // Load users (customers)
        const response = await uiFeedback.handleApiRequest(
            () => unifiedApi.getUsers(),
            null,
            'Loading customers...'
        );
        
        if (response && response.users) {
            customerSelect.innerHTML = '<option value="" selected disabled>Select Customer</option>';
            
            response.users.forEach(user => {
                if (!user.is_admin) { // Only show non-admin users as customers
                    const option = document.createElement('option');
                    option.value = user.id;
                    option.textContent = `${user.full_name} (${user.email})`;
                    customerSelect.appendChild(option);
                }
            });
        }
    } catch (error) {
        console.error('Error loading customers:', error);
        customerSelect.innerHTML = '<option value="">Error loading customers</option>';
        uiFeedback.showError('Failed to load customers');
    } finally {
        customerSelect.disabled = false;
    }
}

/**
 * Validate ticket form
 * @param {HTMLFormElement} form - Form element
 * @returns {boolean} True if valid
 */
function validateTicketForm(form) {
    clearFormErrors(form);
    let isValid = true;
    
    // Validate subject
    const subject = form.querySelector('[name="subject"]');
    if (!subject.value.trim()) {
        showFieldError(subject, 'Subject is required');
        isValid = false;
    }
    
    // Validate description
    const description = form.querySelector('[name="description"]');
    if (!description.value.trim()) {
        showFieldError(description, 'Description is required');
        isValid = false;
    }
    
    return isValid;
}

/**
 * Show field error
 * @param {HTMLElement} field - Form field
 * @param {string} message - Error message
 */
function showFieldError(field, message) {
    field.classList.add('is-invalid');
    
    let feedback = field.parentNode.querySelector('.invalid-feedback');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        field.parentNode.appendChild(feedback);
    }
    feedback.textContent = message;
}

/**
 * Clear form errors
 * @param {HTMLFormElement} form - Form element
 */
function clearFormErrors(form) {
    form.querySelectorAll('.is-invalid').forEach(field => {
        field.classList.remove('is-invalid');
    });
    form.querySelectorAll('.invalid-feedback').forEach(feedback => {
        feedback.remove();
    });
}



/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Capitalize first letter
 * @param {string} str - String to capitalize
 * @returns {string} Capitalized string
 */
function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

/**
 * Create ticket details modal
 * @returns {HTMLElement} Modal element
 */
function createTicketDetailsModal() {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'ticket-details-modal';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Ticket Details</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div id="ticket-details-content"></div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    `;
    return modal;
}

// Initialize ticket management when the DOM is loaded
document.addEventListener('DOMContentLoaded', initTicketManagement);