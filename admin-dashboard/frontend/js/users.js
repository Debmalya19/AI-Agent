/**
 * Admin Dashboard - User Management
 * Enhanced user management with modern functionality
 */

// User state
const userState = {
    currentUser: null,
    users: [],
    filters: {
        role: 'all',
        status: 'all',
        search: '',
        dateRange: 'all'
    },
    pagination: {
        page: 1,
        limit: 25,
        total: 0
    },
    loading: false,
    error: null,
    sortBy: 'created_at',
    sortOrder: 'desc'
};

/**
 * Initialize user management
 */
function initUserManagement() {
    console.log('Initializing user management...');
    
    // Wait for unifiedApi to be available
    if (typeof unifiedApi === 'undefined') {
        setTimeout(initUserManagement, 100);
        return;
    }
    
    // Set up event listeners
    setupUserEventListeners();
    
    // Load initial users
    loadUsers();
}

/**
 * Set up user event listeners
 */
function setupUserEventListeners() {
    // Refresh button
    const refreshBtn = document.getElementById('btn-refresh-users');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            showLoadingState();
            loadUsers();
        });
    }
    
    // Export button
    const exportBtn = document.getElementById('btn-export-users');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportUsers);
    }
    
    // New user button
    const newUserBtn = document.getElementById('btn-new-user');
    if (newUserBtn) {
        newUserBtn.addEventListener('click', showNewUserModal);
    }
    
    // Filter dropdowns
    const roleFilter = document.getElementById('role-filter');
    const statusFilter = document.getElementById('status-filter');
    const dateFilter = document.getElementById('date-filter');
    const clearFiltersBtn = document.getElementById('btn-clear-filters');
    
    if (roleFilter) {
        roleFilter.addEventListener('change', (e) => {
            userState.filters.role = e.target.value;
            userState.pagination.page = 1; // Reset to first page
            loadUsers();
        });
    }
    
    if (statusFilter) {
        statusFilter.addEventListener('change', (e) => {
            userState.filters.status = e.target.value;
            userState.pagination.page = 1; // Reset to first page
            loadUsers();
        });
    }
    
    if (dateFilter) {
        dateFilter.addEventListener('change', (e) => {
            userState.filters.dateRange = e.target.value;
            userState.pagination.page = 1; // Reset to first page
            loadUsers();
        });
    }
    
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', () => {
            // Reset all filters
            userState.filters = {
                role: 'all',
                status: 'all',
                search: '',
                dateRange: 'all'
            };
            
            // Reset form elements
            if (roleFilter) roleFilter.value = 'all';
            if (statusFilter) statusFilter.value = 'all';
            if (dateFilter) dateFilter.value = 'all';
            if (searchInput) searchInput.value = '';
            
            // Reset pagination and reload
            userState.pagination.page = 1;
            loadUsers();
        });
    }
    
    // Search input with enhanced debouncing
    const searchInput = document.getElementById('user-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            userState.filters.search = e.target.value;
            userState.pagination.page = 1; // Reset to first page
            
            // Show search indicator
            if (e.target.value.length > 0) {
                e.target.classList.add('searching');
            } else {
                e.target.classList.remove('searching');
            }
            
            // Debounce search
            clearTimeout(window.userSearchTimeout);
            window.userSearchTimeout = setTimeout(() => {
                e.target.classList.remove('searching');
                loadUsers();
            }, 300);
        });
        
        // Clear search on escape
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                e.target.value = '';
                userState.filters.search = '';
                userState.pagination.page = 1;
                loadUsers();
            }
        });
    }
    
    // Modal event listeners
    setupModalEventListeners();
    
    // Table sorting
    setupTableSorting();
}

/**
 * Load users with current filters and pagination
 */
async function loadUsers() {
    console.log('Loading users...');
    
    userState.loading = true;
    userState.error = null;
    
    // Check if unifiedApi is available
    if (typeof unifiedApi === 'undefined') {
        uiFeedback.showError('API not available');
        return;
    }
    
    // Prepare filter parameters
    const params = new URLSearchParams();
    if (userState.filters.role && userState.filters.role !== 'all') {
        params.append('role', userState.filters.role);
    }
    if (userState.filters.status && userState.filters.status !== 'all') {
        params.append('status', userState.filters.status);
    }
    if (userState.filters.search) {
        params.append('search', userState.filters.search);
    }
    if (userState.filters.dateRange && userState.filters.dateRange !== 'all') {
        params.append('date_range', userState.filters.dateRange);
    }
    if (userState.sortBy) {
        params.append('sort_by', userState.sortBy);
        params.append('sort_order', userState.sortOrder);
    }
    params.append('limit', userState.pagination.limit);
    params.append('skip', (userState.pagination.page - 1) * userState.pagination.limit);
    
    const queryString = params.toString();
    const endpoint = `/admin/users${queryString ? '?' + queryString : ''}`;
    
    try {
        // Show table skeleton loading
        uiFeedback.showTableSkeleton('#users-table-body', 5, 7);
        
        // Fetch users from API
        const response = await uiFeedback.handleApiRequest(
            () => unifiedApi.request(endpoint, {
                method: 'GET',
                headers: unifiedApi.getAuthHeader()
            }),
            null,
            'Loading users...'
        );
        
        console.log('Users response:', response);
        userState.loading = false;
        
        if (response && response.users) {
            userState.users = response.users;
            userState.pagination.total = response.total || response.users.length;
            
            renderUserList();
            updateUserPagination();
            updateUserStats();
        } else {
            // Show empty state
            uiFeedback.showEmptyState(
                '#users-table-body',
                'No users found',
                'There are no users matching your current filters.',
                'fas fa-users',
                'Create New User',
                showNewUserModal
            );
        }
    } catch (error) {
        console.error('Error loading users:', error);
        userState.loading = false;
        userState.error = error.message;
        
        // Show error state in table
        const tableBody = document.getElementById('users-table-body');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4">
                        <i class="fas fa-exclamation-triangle display-4 text-danger mb-3"></i>
                        <p class="text-danger mb-3">Failed to load users</p>
                        <button class="btn btn-outline-primary" onclick="loadUsers()">
                            <i class="fas fa-redo me-1"></i> Retry
                        </button>
                    </td>
                </tr>
            `;
        }
    }
}

/**
 * Render user list with enhanced formatting
 */
function renderUserList() {
    const tableBody = document.getElementById('users-table-body');
    if (!tableBody) return;
    
    // Clear table body
    tableBody.innerHTML = '';
    
    if (userState.users.length === 0) {
        showEmptyUsers();
        return;
    }
    
    // Create user rows with enhanced styling
    userState.users.forEach((user, index) => {
        const row = document.createElement('tr');
        row.className = 'user-row';
        row.setAttribute('data-user-id', user.id);
        
        // Add hover effects and animations
        row.addEventListener('mouseenter', () => {
            row.style.backgroundColor = 'var(--bs-light)';
        });
        row.addEventListener('mouseleave', () => {
            row.style.backgroundColor = '';
        });
        
        const userAvatar = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.full_name || user.username)}&background=667eea&color=fff&size=32`;
        const lastLoginText = user.last_login ? formatRelativeTime(user.last_login) : 'Never';
        const lastLoginClass = user.last_login ? (isRecentLogin(user.last_login) ? 'text-success' : 'text-muted') : 'text-warning';
        
        row.innerHTML = `
            <td class="align-middle">
                <span class="badge bg-light text-dark">#${user.id}</span>
            </td>
            <td class="align-middle">
                <div class="d-flex align-items-center">
                    <img src="${userAvatar}" alt="Avatar" class="rounded-circle me-2" width="32" height="32">
                    <div>
                        <div class="fw-medium">${escapeHtml(user.full_name || user.username || 'Unknown')}</div>
                        <small class="text-muted">@${escapeHtml(user.username)}</small>
                    </div>
                </div>
            </td>
            <td class="align-middle">
                <div class="d-flex align-items-center">
                    <i class="bi bi-envelope me-1 text-muted"></i>
                    <span>${escapeHtml(user.email || 'N/A')}</span>
                </div>
            </td>
            <td class="align-middle">
                <span class="badge ${getRoleBadgeClass(user.role, user.is_admin)}">
                    <i class="${getRoleIcon(user.role, user.is_admin)} me-1"></i>
                    ${getUserRoleText(user.role, user.is_admin)}
                </span>
            </td>
            <td class="align-middle">
                <div class="d-flex align-items-center">
                    <div class="status-indicator ${user.is_active ? 'status-active' : 'status-inactive'} me-2"></div>
                    <span class="badge ${user.is_active ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'}">
                        ${user.is_active ? 'Active' : 'Inactive'}
                    </span>
                </div>
            </td>
            <td class="align-middle">
                <div class="text-nowrap">
                    <small class="text-muted">${formatDate(user.created_at)}</small>
                </div>
            </td>
            <td class="align-middle">
                <div class="text-nowrap ${lastLoginClass}">
                    <small>${lastLoginText}</small>
                </div>
            </td>
            <td class="align-middle">
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-outline-primary" onclick="viewUser(${user.id})" title="View Details">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="editUser(${user.id})" title="Edit User">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown" title="More Actions">
                            <i class="bi bi-three-dots"></i>
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="#" onclick="resetUserPassword(${user.id})">
                                <i class="bi bi-key me-2"></i>Reset Password
                            </a></li>
                            <li><a class="dropdown-item" href="#" onclick="toggleUserStatus(${user.id})">
                                <i class="bi bi-toggle-${user.is_active ? 'off' : 'on'} me-2"></i>
                                ${user.is_active ? 'Deactivate' : 'Activate'}
                            </a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item text-danger" href="#" onclick="deleteUser(${user.id})">
                                <i class="bi bi-trash me-2"></i>Delete User
                            </a></li>
                        </ul>
                    </div>
                </div>
            </td>
        `;
        
        // Add animation delay for staggered loading effect
        row.style.animationDelay = `${index * 50}ms`;
        row.classList.add('fade-in');
        
        tableBody.appendChild(row);
    });
}

/**
 * Show empty users state
 */
function showEmptyUsers() {
    const tableBody = document.getElementById('users-table-body');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-4">
                    <i class="bi bi-people display-4 text-muted"></i>
                    <p class="mt-2 text-muted">No users found</p>
                </td>
            </tr>
        `;
    }
}

/**
 * Load user details
 * @param {number} userId - User ID
 */
function loadUserDetails(userId) {
    if (!userElements.userDetails) return;
    
    // Show loading state
    userElements.userDetails.innerHTML = '<div class="text-center p-4"><div class="spinner-border" role="status"></div><p class="mt-2">Loading user details...</p></div>';
    
    // Show user details section
    document.getElementById('content-users-list').classList.add('d-none');
    document.getElementById('content-users-details').classList.remove('d-none');
    
    // Fetch user details from API
    unifiedApi.getUser(userId)
        .then(response => {
            if (response.success) {
                userState.currentUser = response.user;
                renderUserDetails(response.user);
            } else {
                showUserError('Failed to load user details');
            }
        })
        .catch(error => {
            console.error('Error loading user details:', error);
            showUserError('An error occurred while loading user details');
        });
}

/**
 * Render user details
 * @param {Object} user - User data
 */
function renderUserDetails(user) {
    if (!userElements.userDetails) return;
    
    // Create user details HTML
    userElements.userDetails.innerHTML = `
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <div>
                    <h5 class="mb-0">${user.full_name || user.username}</h5>
                    <p class="text-muted small mb-0">User ID: ${user.id}</p>
                </div>
                <div>
                    <button id="back-to-users" class="btn btn-sm btn-outline-secondary">
                        <i class="bi bi-arrow-left me-1"></i> Back to Users
                    </button>
                </div>
            </div>
            <div class="card-body">
                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <strong>Username:</strong>
                            <span class="ms-2">${user.username}</span>
                        </div>
                        <div class="mb-3">
                            <strong>Email:</strong>
                            <span class="ms-2">${user.email}</span>
                        </div>
                        <div class="mb-3">
                            <strong>Full Name:</strong>
                            <span class="ms-2">${user.full_name || '-'}</span>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <strong>Role:</strong>
                            <span class="badge ${user.is_admin ? 'bg-danger' : 'bg-primary'} ms-2">
                                ${user.is_admin ? 'Admin' : 'User'}
                            </span>
                        </div>
                        <div class="mb-3">
                            <strong>Created:</strong>
                            <span class="ms-2">${formatDate(user.created_at)}</span>
                        </div>
                        <div class="mb-3">
                            <strong>Last Login:</strong>
                            <span class="ms-2">${user.last_login ? formatDate(user.last_login) : 'Never'}</span>
                        </div>
                    </div>
                </div>
                
                <div class="mb-4">
                    <h6>Contact Information</h6>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <strong>Phone:</strong>
                                <span class="ms-2">${user.phone || '-'}</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="mb-4">
                    <h6>Integration Status</h6>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <strong>AI Agent Customer ID:</strong>
                                <span class="ms-2">${user.ai_agent_customer_id || 'Not synced'}</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="d-flex justify-content-between">
                    <div>
                        <button id="edit-user-btn" class="btn btn-outline-primary me-2">
                            <i class="bi bi-pencil me-1"></i> Edit User
                        </button>
                        <button id="reset-password-btn" class="btn btn-outline-secondary">
                            <i class="bi bi-key me-1"></i> Reset Password
                        </button>
                    </div>
                    <div>
                        <button id="delete-user-btn" class="btn btn-danger">
                            <i class="bi bi-trash me-1"></i> Delete User
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add event listeners
    document.getElementById('back-to-users').addEventListener('click', backToUserList);
    document.getElementById('edit-user-btn').addEventListener('click', () => showEditUserForm(user));
    document.getElementById('reset-password-btn').addEventListener('click', () => showResetPasswordModal(user.id));
    document.getElementById('delete-user-btn').addEventListener('click', () => confirmDeleteUser(user.id));
}

/**
 * Back to user list
 */
function backToUserList() {
    document.getElementById('content-users-list').classList.remove('d-none');
    document.getElementById('content-users-details').classList.add('d-none');
    userState.currentUser = null;
}

/**
 * Show new user form
 */
function showNewUserForm() {
    // Show user form modal
    const userFormModal = new bootstrap.Modal(document.getElementById('user-form-modal'));
    userFormModal.show();
    
    // Reset form
    const form = document.getElementById('user-form');
    if (form) {
        form.reset();
        form.dataset.mode = 'create';
        document.getElementById('user-form-title').textContent = 'Create New User';
        
        // Show password fields for new user
        document.getElementById('password-group').classList.remove('d-none');
    }
}

/**
 * Show edit user form
 * @param {Object} user - User data
 */
function showEditUserForm(user) {
    // Show user form modal
    const userFormModal = new bootstrap.Modal(document.getElementById('user-form-modal'));
    userFormModal.show();
    
    // Fill form with user data
    const form = document.getElementById('user-form');
    if (form) {
        form.dataset.mode = 'edit';
        form.dataset.userId = user.id;
        document.getElementById('user-form-title').textContent = 'Edit User';
        
        document.getElementById('username').value = user.username;
        document.getElementById('email').value = user.email;
        document.getElementById('full-name').value = user.full_name || '';
        document.getElementById('phone').value = user.phone || '';
        document.getElementById('is-admin').checked = user.is_admin;
        
        // Hide password fields for edit
        document.getElementById('password-group').classList.add('d-none');
    }
}

/**
 * Show reset password modal
 * @param {number} userId - User ID
 */
function showResetPasswordModal(userId) {
    // Show reset password modal
    const resetPasswordModal = new bootstrap.Modal(document.getElementById('reset-password-modal'));
    resetPasswordModal.show();
    
    // Set user ID
    document.getElementById('reset-password-user-id').value = userId;
    
    // Add event listener to form
    const form = document.getElementById('reset-password-form');
    form.addEventListener('submit', handleResetPasswordSubmit);
}

/**
 * Handle user form submission
 * @param {Event} event - Form submit event
 */
function handleUserSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const mode = form.dataset.mode;
    const userId = form.dataset.userId;
    
    // Get form data
    const userData = {
        username: document.getElementById('username').value,
        email: document.getElementById('email').value,
        full_name: document.getElementById('full-name').value,
        phone: document.getElementById('phone').value,
        is_admin: document.getElementById('is-admin').checked
    };
    
    // Add password for new user
    if (mode === 'create') {
        userData.password = document.getElementById('password').value;
    }
    
    // Create or update user
    let apiCall;
    if (mode === 'edit' && userId) {
        apiCall = unifiedApi.updateUser(userId, userData);
    } else {
        apiCall = unifiedApi.createUser(userData);
    }
    
    // Submit form
    apiCall
        .then(response => {
            if (response.success) {
                // Close modal
                bootstrap.Modal.getInstance(document.getElementById('user-form-modal')).hide();
                
                // Reload users or user details
                if (mode === 'edit' && userId) {
                    loadUserDetails(userId);
                } else {
                    loadUsers();
                }
                
                // Show success message
                showAlert('success', `User ${mode === 'edit' ? 'updated' : 'created'} successfully`);
            } else {
                showAlert('danger', response.message || `Failed to ${mode} user`);
            }
        })
        .catch(error => {
            console.error(`Error ${mode}ing user:`, error);
            showAlert('danger', `An error occurred while ${mode}ing the user`);
        });
}

/**
 * Handle reset password form submission
 * @param {Event} event - Form submit event
 */
function handleResetPasswordSubmit(event) {
    event.preventDefault();
    
    const userId = document.getElementById('reset-password-user-id').value;
    const newPassword = document.getElementById('new-password').value;
    
    // Reset password
    unifiedApi.resetPassword(userId, newPassword)
        .then(response => {
            if (response.success) {
                // Close modal
                bootstrap.Modal.getInstance(document.getElementById('reset-password-modal')).hide();
                
                // Show success message
                showAlert('success', 'Password reset successfully');
            } else {
                showAlert('danger', response.message || 'Failed to reset password');
            }
        })
        .catch(error => {
            console.error('Error resetting password:', error);
            showAlert('danger', 'An error occurred while resetting the password');
        });
}

/**
 * Confirm delete user
 * @param {number} userId - User ID
 */
function confirmDeleteUser(userId) {
    if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) return;
    
    // Delete user
    unifiedApi.deleteUser(userId)
        .then(response => {
            if (response.success) {
                // Go back to user list if viewing details
                if (userState.currentUser && userState.currentUser.id.toString() === userId.toString()) {
                    backToUserList();
                }
                
                // Reload users
                loadUsers();
                
                // Show success message
                showAlert('success', 'User deleted successfully');
            } else {
                showAlert('danger', response.message || 'Failed to delete user');
            }
        })
        .catch(error => {
            console.error('Error deleting user:', error);
            showAlert('danger', 'An error occurred while deleting the user');
        });
}

/**
 * Handle user filter change
 * @param {Event} event - Change event
 */
function handleUserFilterChange(event) {
    const { id, value } = event.target;
    
    switch (id) {
        case 'filter-role':
            userState.filters.role = value;
            break;
        case 'filter-status':
            userState.filters.status = value;
            break;
    }
}

/**
 * Handle user search change
 * @param {Event} event - Input event
 */
function handleUserSearchChange(event) {
    userState.filters.search = event.target.value;
}

/**
 * Handle user filter form submission
 * @param {Event} event - Form submit event
 */
function handleUserFilterSubmit(event) {
    event.preventDefault();
    
    // Reset pagination
    userState.pagination.page = 1;
    
    // Load users with filters
    loadUsers();
}

/**
 * Reset user filters
 */
function resetUserFilters() {
    // Reset filter form
    const filterForm = document.getElementById('user-filter-form');
    if (filterForm) filterForm.reset();
    
    // Reset filter state
    userState.filters = {
        role: '',
        status: '',
        search: ''
    };
    
    // Reset pagination
    userState.pagination.page = 1;
    
    // Load users
    loadUsers();
}



/**
 * Show user error
 * @param {string} message - Error message
 */
function showUserError(message) {
    const tableBody = document.getElementById('users-table-body');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-4">
                    <i class="bi bi-exclamation-triangle display-4 text-danger"></i>
                    <p class="mt-2 text-danger">${message}</p>
                    <button class="btn btn-outline-primary btn-sm" onclick="loadUsers()">
                        <i class="bi bi-arrow-repeat me-1"></i> Retry
                    </button>
                </td>
            </tr>
        `;
    }
}

/**
 * Get role badge class
 * @param {string} role - User role
 * @param {boolean} isAdmin - Is admin flag
 * @returns {string} Bootstrap badge class
 */
function getRoleBadgeClass(role, isAdmin) {
    if (isAdmin) return 'bg-danger';
    
    switch (role?.toLowerCase()) {
        case 'admin':
            return 'bg-danger';
        case 'support':
            return 'bg-warning';
        case 'user':
        case 'customer':
            return 'bg-primary';
        default:
            return 'bg-secondary';
    }
}

/**
 * Get user role text
 * @param {string} role - User role
 * @param {boolean} isAdmin - Is admin flag
 * @returns {string} Role text
 */
function getUserRoleText(role, isAdmin) {
    if (isAdmin) return 'Admin';
    
    switch (role?.toLowerCase()) {
        case 'admin':
            return 'Admin';
        case 'support':
            return 'Support';
        case 'user':
        case 'customer':
            return 'User';
        default:
            return 'User';
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
 * Show loading state
 */
function showLoadingState() {
    const tableBody = document.getElementById('users-table-body');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-5">
                    <div class="d-flex flex-column align-items-center">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="text-muted mb-0">Loading users...</p>
                    </div>
                </td>
            </tr>
        `;
    }
}

/**
 * Update user statistics display
 */
function updateUserStats() {
    // This would typically show user statistics in a dashboard card
    // For now, we'll update the pagination info which serves as basic stats
    console.log(`Loaded ${userState.users.length} users of ${userState.pagination.total} total`);
}

/**
 * Export users to CSV
 */
function exportUsers() {
    if (userState.users.length === 0) {
        showAlert('warning', 'No users to export');
        return;
    }
    
    // Create CSV content
    const headers = ['ID', 'Username', 'Email', 'Full Name', 'Role', 'Status', 'Created', 'Last Login'];
    const csvContent = [
        headers.join(','),
        ...userState.users.map(user => [
            user.id,
            `"${user.username || ''}"`,
            `"${user.email || ''}"`,
            `"${user.full_name || ''}"`,
            getUserRoleText(user.role, user.is_admin),
            user.is_active ? 'Active' : 'Inactive',
            user.created_at ? new Date(user.created_at).toISOString().split('T')[0] : '',
            user.last_login ? new Date(user.last_login).toISOString().split('T')[0] : 'Never'
        ].join(','))
    ].join('\n');
    
    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `users_export_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    showAlert('success', 'Users exported successfully');
}

/**
 * Show new user modal
 */
function showNewUserModal() {
    const modal = new bootstrap.Modal(document.getElementById('new-user-modal'));
    
    // Reset form
    const form = document.getElementById('new-user-form');
    if (form) {
        form.reset();
        // Clear any validation states
        form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
        form.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
    }
    
    modal.show();
}

/**
 * Setup table sorting functionality
 */
function setupTableSorting() {
    const tableHeaders = document.querySelectorAll('#users-table-body').parentElement.querySelectorAll('th[data-sort]');
    
    tableHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', () => {
            const sortBy = header.getAttribute('data-sort');
            
            // Toggle sort order if same column
            if (userState.sortBy === sortBy) {
                userState.sortOrder = userState.sortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                userState.sortBy = sortBy;
                userState.sortOrder = 'asc';
            }
            
            // Update header indicators
            tableHeaders.forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
            });
            header.classList.add(userState.sortOrder === 'asc' ? 'sort-asc' : 'sort-desc');
            
            // Reload users with new sorting
            loadUsers();
        });
    });
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
function formatRelativeTime(dateString) {
    if (!dateString) return 'Never';
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} min ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return formatDate(dateString);
    } catch (error) {
        return 'Invalid Date';
    }
}

/**
 * Check if login is recent (within 24 hours)
 */
function isRecentLogin(dateString) {
    if (!dateString) return false;
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffHours = (now - date) / (1000 * 60 * 60);
        return diffHours <= 24;
    } catch (error) {
        return false;
    }
}

/**
 * Get role icon
 */
function getRoleIcon(role, isAdmin) {
    if (isAdmin) return 'bi-shield-fill-check';
    
    switch (role?.toLowerCase()) {
        case 'admin':
            return 'bi-shield-fill-check';
        case 'support':
            return 'bi-headset';
        case 'user':
        case 'customer':
            return 'bi-person-fill';
        default:
            return 'bi-person';
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Setup modal event listeners
 */
function setupModalEventListeners() {
    // New user form submission
    const newUserForm = document.getElementById('new-user-form');
    if (newUserForm) {
        newUserForm.addEventListener('submit', handleNewUserSubmit);
    }
    
    // Edit user form submission
    const editUserForm = document.getElementById('edit-user-form');
    if (editUserForm) {
        editUserForm.addEventListener('submit', handleEditUserSubmit);
    }
    
    // Reset password form submission
    const resetPasswordForm = document.getElementById('reset-password-form');
    if (resetPasswordForm) {
        resetPasswordForm.addEventListener('submit', handleResetPasswordSubmit);
    }
    
    // Create user button
    const createUserBtn = document.getElementById('btn-create-user');
    if (createUserBtn) {
        createUserBtn.addEventListener('click', handleNewUserSubmit);
    }
    
    // Update user button
    const updateUserBtn = document.getElementById('btn-update-user');
    if (updateUserBtn) {
        updateUserBtn.addEventListener('click', handleEditUserSubmit);
    }
    
    // Reset password button
    const resetPasswordBtn = document.getElementById('btn-confirm-reset-password');
    if (resetPasswordBtn) {
        resetPasswordBtn.addEventListener('click', handleResetPasswordSubmit);
    }
    
    // Password confirmation validation
    const confirmPasswordField = document.getElementById('user-confirm-password');
    if (confirmPasswordField) {
        confirmPasswordField.addEventListener('input', validatePasswordMatch);
    }
    
    const editConfirmPasswordField = document.getElementById('reset-password-confirm');
    if (editConfirmPasswordField) {
        editConfirmPasswordField.addEventListener('input', validateResetPasswordMatch);
    }
}

/**
 * Setup table sorting
 */
function setupTableSorting() {
    const tableHeaders = document.querySelectorAll('th[data-sort]');
    tableHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', () => {
            const sortBy = header.getAttribute('data-sort');
            if (userState.sortBy === sortBy) {
                userState.sortOrder = userState.sortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                userState.sortBy = sortBy;
                userState.sortOrder = 'asc';
            }
            
            // Update sort indicators
            updateSortIndicators();
            loadUsers();
        });
    });
}

/**
 * Update sort indicators
 */

/**
 * View user details
 * @param {number} userId - User ID
 */
function viewUser(userId) {
    const user = userState.users.find(u => u.id === userId);
    if (!user) {
        showAlert('error', 'User not found');
        return;
    }
    
    // Populate view modal with user data
    document.getElementById('view-user-full-name').textContent = user.full_name || user.username || 'Unknown';
    document.getElementById('view-user-username').textContent = `@${user.username}`;
    document.getElementById('view-user-email').textContent = user.email || 'N/A';
    document.getElementById('view-user-phone').textContent = user.phone || 'Not provided';
    document.getElementById('view-user-created').textContent = formatDate(user.created_at);
    document.getElementById('view-user-last-login').textContent = user.last_login ? formatDate(user.last_login) : 'Never';
    document.getElementById('view-user-id').textContent = `#${user.id}`;
    document.getElementById('view-user-ai-agent-id').textContent = user.ai_agent_customer_id || 'Not synced';
    
    // Set status and role badges
    const statusBadge = document.getElementById('view-user-status');
    statusBadge.textContent = user.is_active ? 'Active' : 'Inactive';
    statusBadge.className = `badge ${user.is_active ? 'bg-success' : 'bg-secondary'}`;
    
    const roleBadge = document.getElementById('view-user-role');
    roleBadge.textContent = getUserRoleText(user.role, user.is_admin);
    roleBadge.className = `badge ${getRoleBadgeClass(user.role, user.is_admin)}`;
    
    // Update toggle status button
    const toggleBtn = document.getElementById('btn-toggle-status');
    const toggleText = document.getElementById('toggle-status-text');
    if (toggleBtn && toggleText) {
        toggleText.textContent = user.is_active ? 'Deactivate' : 'Activate';
        toggleBtn.onclick = () => toggleUserStatus(userId);
    }
    
    // Set up action buttons
    document.getElementById('btn-edit-user').onclick = () => editUser(userId);
    document.getElementById('btn-reset-password').onclick = () => resetUserPassword(userId);
    document.getElementById('btn-delete-user').onclick = () => deleteUser(userId);
    document.getElementById('btn-sync-user').onclick = () => syncUserWithAI(userId);
    
    // Load user activity
    loadUserActivity(userId);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('view-user-modal'));
    modal.show();
}

/**
 * Edit user
 * @param {number} userId - User ID
 */
function editUser(userId) {
    const user = userState.users.find(u => u.id === userId);
    if (!user) {
        showAlert('error', 'User not found');
        return;
    }
    
    // Close view modal if open
    const viewModal = bootstrap.Modal.getInstance(document.getElementById('view-user-modal'));
    if (viewModal) {
        viewModal.hide();
    }
    
    // Populate edit form
    document.getElementById('edit-user-id').value = user.id;
    document.getElementById('edit-user-username').value = user.username || '';
    document.getElementById('edit-user-email').value = user.email || '';
    document.getElementById('edit-user-full-name').value = user.full_name || '';
    document.getElementById('edit-user-phone').value = user.phone || '';
    document.getElementById('edit-user-role').value = user.is_admin ? 'admin' : (user.role || 'user');
    document.getElementById('edit-user-status').value = user.is_active ? 'active' : 'inactive';
    document.getElementById('edit-user-ai-agent-id').value = user.ai_agent_customer_id || '';
    
    // Clear any validation states
    const form = document.getElementById('edit-user-form');
    form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    form.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
    
    // Show edit modal
    const modal = new bootstrap.Modal(document.getElementById('edit-user-modal'));
    modal.show();
}

/**
 * Reset user password
 * @param {number} userId - User ID
 */
function resetUserPassword(userId) {
    const user = userState.users.find(u => u.id === userId);
    if (!user) {
        showAlert('error', 'User not found');
        return;
    }
    
    // Set user ID in hidden field
    document.getElementById('reset-password-user-id').value = userId;
    
    // Clear form
    const form = document.getElementById('reset-password-form');
    form.reset();
    form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    form.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('reset-password-modal'));
    modal.show();
}

/**
 * Toggle user status (active/inactive)
 * @param {number} userId - User ID
 */
function toggleUserStatus(userId) {
    const user = userState.users.find(u => u.id === userId);
    if (!user) {
        showAlert('error', 'User not found');
        return;
    }
    
    const newStatus = !user.is_active;
    const action = newStatus ? 'activate' : 'deactivate';
    
    if (!confirm(`Are you sure you want to ${action} this user?`)) {
        return;
    }
    
    // Show loading state
    showAlert('info', `${action === 'activate' ? 'Activating' : 'Deactivating'} user...`);
    
    // Update user status via API
    unifiedApi.request(`/admin/users/${userId}`, {
        method: 'PUT',
        headers: {
            ...unifiedApi.getAuthHeader(),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            is_active: newStatus
        })
    })
    .then(response => {
        if (response && response.success !== false) {
            // Update local state
            user.is_active = newStatus;
            
            // Refresh the table
            renderUserList();
            
            // Update view modal if open
            const viewModal = bootstrap.Modal.getInstance(document.getElementById('view-user-modal'));
            if (viewModal) {
                viewUser(userId);
            }
            
            showAlert('success', `User ${action}d successfully`);
        } else {
            showAlert('error', response?.message || `Failed to ${action} user`);
        }
    })
    .catch(error => {
        console.error(`Error ${action}ing user:`, error);
        showAlert('error', `An error occurred while ${action}ing the user`);
    });
}

/**
 * Delete user
 * @param {number} userId - User ID
 */
function deleteUser(userId) {
    const user = userState.users.find(u => u.id === userId);
    if (!user) {
        showAlert('error', 'User not found');
        return;
    }
    
    // Show confirmation modal
    const confirmModal = new bootstrap.Modal(document.getElementById('delete-user-modal'));
    
    // Set user info in modal
    document.getElementById('delete-user-name').textContent = user.full_name || user.username;
    document.getElementById('delete-user-confirm-id').value = userId;
    
    confirmModal.show();
}

/**
 * Sync user with AI Agent system
 * @param {number} userId - User ID
 */
function syncUserWithAI(userId) {
    const user = userState.users.find(u => u.id === userId);
    if (!user) {
        showAlert('error', 'User not found');
        return;
    }
    
    showAlert('info', 'Syncing user with AI Agent system...');
    
    // Sync user via API
    unifiedApi.request(`/admin/users/${userId}/sync`, {
        method: 'POST',
        headers: unifiedApi.getAuthHeader()
    })
    .then(response => {
        if (response && response.success !== false) {
            // Update user data
            if (response.ai_agent_customer_id) {
                user.ai_agent_customer_id = response.ai_agent_customer_id;
                
                // Update view modal if open
                document.getElementById('view-user-ai-agent-id').textContent = response.ai_agent_customer_id;
            }
            
            showAlert('success', 'User synced successfully');
        } else {
            showAlert('error', response?.message || 'Failed to sync user');
        }
    })
    .catch(error => {
        console.error('Error syncing user:', error);
        showAlert('error', 'An error occurred while syncing the user');
    });
}

/**
 * Load user activity timeline
 * @param {number} userId - User ID
 */
function loadUserActivity(userId) {
    const activityList = document.getElementById('user-activity-list');
    if (!activityList) return;
    
    // Show loading state
    activityList.innerHTML = `
        <div class="list-group-item text-center py-3">
            <div class="spinner-border spinner-border-sm" role="status"></div>
            <p class="mb-0 mt-2">Loading activity...</p>
        </div>
    `;
    
    // Load activity from API
    unifiedApi.request(`/admin/users/${userId}/activity`, {
        method: 'GET',
        headers: unifiedApi.getAuthHeader()
    })
    .then(response => {
        if (response && response.activities) {
            renderUserActivity(response.activities);
        } else {
            // Show empty state
            activityList.innerHTML = `
                <div class="list-group-item text-center py-3">
                    <i class="bi bi-clock-history text-muted"></i>
                    <p class="mb-0 mt-2 text-muted">No recent activity</p>
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('Error loading user activity:', error);
        activityList.innerHTML = `
            <div class="list-group-item text-center py-3">
                <i class="bi bi-exclamation-triangle text-warning"></i>
                <p class="mb-0 mt-2 text-muted">Failed to load activity</p>
            </div>
        `;
    });
}

/**
 * Render user activity timeline
 * @param {Array} activities - Activity data
 */
function renderUserActivity(activities) {
    const activityList = document.getElementById('user-activity-list');
    if (!activityList) return;
    
    if (activities.length === 0) {
        activityList.innerHTML = `
            <div class="list-group-item text-center py-3">
                <i class="bi bi-clock-history text-muted"></i>
                <p class="mb-0 mt-2 text-muted">No recent activity</p>
            </div>
        `;
        return;
    }
    
    activityList.innerHTML = activities.map(activity => `
        <div class="list-group-item">
            <div class="d-flex align-items-start">
                <div class="activity-icon me-3">
                    <i class="bi ${getActivityIcon(activity.type)} text-${getActivityColor(activity.type)}"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="activity-content">
                        <p class="mb-1">${escapeHtml(activity.description)}</p>
                        <small class="text-muted">${formatRelativeTime(activity.created_at)}</small>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Get activity icon based on type
 */
function getActivityIcon(type) {
    switch (type) {
        case 'login': return 'bi-box-arrow-in-right';
        case 'logout': return 'bi-box-arrow-right';
        case 'profile_update': return 'bi-person-gear';
        case 'password_change': return 'bi-key';
        case 'ticket_created': return 'bi-ticket-perforated';
        case 'ticket_updated': return 'bi-pencil-square';
        default: return 'bi-clock-history';
    }
}

/**
 * Get activity color based on type
 */
function getActivityColor(type) {
    switch (type) {
        case 'login': return 'success';
        case 'logout': return 'secondary';
        case 'profile_update': return 'info';
        case 'password_change': return 'warning';
        case 'ticket_created': return 'primary';
        case 'ticket_updated': return 'info';
        default: return 'muted';
    }
}

/**
 * Handle new user form submission
 */
function handleNewUserSubmit(event) {
    if (event) event.preventDefault();
    
    const form = document.getElementById('new-user-form');
    if (!form) return;
    
    // Validate form
    if (!validateUserForm(form)) return;
    
    // Get form data
    const formData = new FormData(form);
    const userData = {
        username: formData.get('username') || document.getElementById('user-username').value,
        email: formData.get('email') || document.getElementById('user-email').value,
        password: formData.get('password') || document.getElementById('user-password').value,
        full_name: formData.get('full_name') || document.getElementById('user-full-name').value,
        phone: formData.get('phone') || document.getElementById('user-phone').value,
        role: formData.get('role') || document.getElementById('user-role').value,
        is_active: (formData.get('status') || document.getElementById('user-status').value) === 'active',
        ai_agent_customer_id: formData.get('ai_agent_customer_id') || document.getElementById('user-ai-agent-id').value
    };
    
    // Show loading state
    const submitBtn = document.getElementById('btn-create-user');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Creating...';
    submitBtn.disabled = true;
    
    // Create user via API
    unifiedApi.request('/admin/users', {
        method: 'POST',
        headers: {
            ...unifiedApi.getAuthHeader(),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
    })
    .then(response => {
        if (response && response.success !== false) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('new-user-modal'));
            modal.hide();
            
            // Reload users
            loadUsers();
            
            showAlert('success', 'User created successfully');
        } else {
            showAlert('error', response?.message || 'Failed to create user');
        }
    })
    .catch(error => {
        console.error('Error creating user:', error);
        showAlert('error', 'An error occurred while creating the user');
    })
    .finally(() => {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

/**
 * Handle edit user form submission
 */
function handleEditUserSubmit(event) {
    if (event) event.preventDefault();
    
    const form = document.getElementById('edit-user-form');
    if (!form) return;
    
    const userId = document.getElementById('edit-user-id').value;
    if (!userId) return;
    
    // Validate form
    if (!validateUserForm(form, true)) return;
    
    // Get form data
    const userData = {
        username: document.getElementById('edit-user-username').value,
        email: document.getElementById('edit-user-email').value,
        full_name: document.getElementById('edit-user-full-name').value,
        phone: document.getElementById('edit-user-phone').value,
        role: document.getElementById('edit-user-role').value,
        is_active: document.getElementById('edit-user-status').value === 'active',
        ai_agent_customer_id: document.getElementById('edit-user-ai-agent-id').value
    };
    
    // Show loading state
    const submitBtn = document.getElementById('btn-update-user');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Updating...';
    submitBtn.disabled = true;
    
    // Update user via API
    unifiedApi.request(`/admin/users/${userId}`, {
        method: 'PUT',
        headers: {
            ...unifiedApi.getAuthHeader(),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
    })
    .then(response => {
        if (response && response.success !== false) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('edit-user-modal'));
            modal.hide();
            
            // Update local state
            const userIndex = userState.users.findIndex(u => u.id == userId);
            if (userIndex !== -1) {
                userState.users[userIndex] = { ...userState.users[userIndex], ...userData };
                renderUserList();
            }
            
            showAlert('success', 'User updated successfully');
        } else {
            showAlert('error', response?.message || 'Failed to update user');
        }
    })
    .catch(error => {
        console.error('Error updating user:', error);
        showAlert('error', 'An error occurred while updating the user');
    })
    .finally(() => {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

/**
 * Handle reset password form submission
 */
function handleResetPasswordSubmit(event) {
    if (event) event.preventDefault();
    
    const form = document.getElementById('reset-password-form');
    if (!form) return;
    
    const userId = document.getElementById('reset-password-user-id').value;
    const newPassword = document.getElementById('reset-password-new').value;
    const confirmPassword = document.getElementById('reset-password-confirm').value;
    const notifyUser = document.getElementById('reset-password-notify').checked;
    
    // Validate passwords match
    if (newPassword !== confirmPassword) {
        showAlert('error', 'Passwords do not match');
        return;
    }
    
    if (newPassword.length < 6) {
        showAlert('error', 'Password must be at least 6 characters long');
        return;
    }
    
    // Show loading state
    const submitBtn = document.getElementById('btn-confirm-reset-password');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Resetting...';
    submitBtn.disabled = true;
    
    // Reset password via API
    unifiedApi.request(`/admin/users/${userId}/reset-password`, {
        method: 'POST',
        headers: {
            ...unifiedApi.getAuthHeader(),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            new_password: newPassword,
            notify_user: notifyUser
        })
    })
    .then(response => {
        if (response && response.success !== false) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('reset-password-modal'));
            modal.hide();
            
            showAlert('success', 'Password reset successfully');
        } else {
            showAlert('error', response?.message || 'Failed to reset password');
        }
    })
    .catch(error => {
        console.error('Error resetting password:', error);
        showAlert('error', 'An error occurred while resetting the password');
    })
    .finally(() => {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

/**
 * Validate user form
 * @param {HTMLFormElement} form - Form element
 * @param {boolean} isEdit - Whether this is an edit form
 * @returns {boolean} Whether form is valid
 */
function validateUserForm(form, isEdit = false) {
    let isValid = true;
    
    // Clear previous validation states
    form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    form.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
    
    // Validate username
    const usernameField = form.querySelector('[id*="username"]');
    if (usernameField && !usernameField.value.trim()) {
        showFieldError(usernameField, 'Username is required');
        isValid = false;
    }
    
    // Validate email
    const emailField = form.querySelector('[id*="email"]');
    if (emailField) {
        const email = emailField.value.trim();
        if (!email) {
            showFieldError(emailField, 'Email is required');
            isValid = false;
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            showFieldError(emailField, 'Please enter a valid email address');
            isValid = false;
        }
    }
    
    // Validate password (only for new users)
    if (!isEdit) {
        const passwordField = form.querySelector('[id*="password"]:not([id*="confirm"])');
        const confirmPasswordField = form.querySelector('[id*="confirm-password"]');
        
        if (passwordField) {
            const password = passwordField.value;
            if (!password) {
                showFieldError(passwordField, 'Password is required');
                isValid = false;
            } else if (password.length < 6) {
                showFieldError(passwordField, 'Password must be at least 6 characters long');
                isValid = false;
            }
        }
        
        if (confirmPasswordField && passwordField) {
            if (confirmPasswordField.value !== passwordField.value) {
                showFieldError(confirmPasswordField, 'Passwords do not match');
                isValid = false;
            }
        }
    }
    
    return isValid;
}

/**
 * Show field validation error
 * @param {HTMLElement} field - Form field element
 * @param {string} message - Error message
 */
function showFieldError(field, message) {
    field.classList.add('is-invalid');
    
    const feedback = document.createElement('div');
    feedback.className = 'invalid-feedback';
    feedback.textContent = message;
    
    field.parentNode.appendChild(feedback);
}

/**
 * Validate password match in real-time
 */
function validatePasswordMatch() {
    const passwordField = document.getElementById('user-password') || document.getElementById('reset-password-new');
    const confirmField = document.getElementById('user-confirm-password') || document.getElementById('reset-password-confirm');
    
    if (!passwordField || !confirmField) return;
    
    const password = passwordField.value;
    const confirm = confirmField.value;
    
    // Clear previous validation
    confirmField.classList.remove('is-invalid', 'is-valid');
    const existingFeedback = confirmField.parentNode.querySelector('.invalid-feedback, .valid-feedback');
    if (existingFeedback) existingFeedback.remove();
    
    if (confirm.length > 0) {
        if (password === confirm) {
            confirmField.classList.add('is-valid');
            const feedback = document.createElement('div');
            feedback.className = 'valid-feedback';
            feedback.textContent = 'Passwords match';
            confirmField.parentNode.appendChild(feedback);
        } else {
            confirmField.classList.add('is-invalid');
            const feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            feedback.textContent = 'Passwords do not match';
            confirmField.parentNode.appendChild(feedback);
        }
    }
}

/**
 * Show alert message
 * @param {string} type - Alert type (success, error, warning, info)
 * @param {string} message - Alert message
 */
function showAlert(type, message) {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) {
        console.log(`${type.toUpperCase()}: ${message}`);
        return;
    }
    
    // Map error to danger for Bootstrap
    const alertType = type === 'error' ? 'danger' : type;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${alertType} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initUserManagement);
/**
 * Ha
ndle delete user confirmation
 */
function handleDeleteUserConfirmation() {
    const userId = document.getElementById('delete-user-confirm-id').value;
    if (!userId) return;
    
    const user = userState.users.find(u => u.id == userId);
    if (!user) {
        showAlert('error', 'User not found');
        return;
    }
    
    // Show loading state
    const submitBtn = document.getElementById('btn-confirm-delete-user');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Deleting...';
    submitBtn.disabled = true;
    
    // Delete user via API
    unifiedApi.request(`/admin/users/${userId}`, {
        method: 'DELETE',
        headers: unifiedApi.getAuthHeader()
    })
    .then(response => {
        if (response && response.success !== false) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('delete-user-modal'));
            modal.hide();
            
            // Remove user from local state
            userState.users = userState.users.filter(u => u.id != userId);
            
            // Refresh the table
            renderUserList();
            updateUserPagination();
            
            showAlert('success', 'User deleted successfully');
        } else {
            showAlert('error', response?.message || 'Failed to delete user');
        }
    })
    .catch(error => {
        console.error('Error deleting user:', error);
        showAlert('error', 'An error occurred while deleting the user');
    })
    .finally(() => {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

// Set up delete confirmation checkbox handler
document.addEventListener('DOMContentLoaded', function() {
    const deleteCheckbox = document.getElementById('delete-user-confirm-check');
    const deleteButton = document.getElementById('btn-confirm-delete-user');
    
    if (deleteCheckbox && deleteButton) {
        deleteCheckbox.addEventListener('change', function() {
            deleteButton.disabled = !this.checked;
        });
        
        deleteButton.addEventListener('click', handleDeleteUserConfirmation);
    }
});/**
 * 
Generate pagination controls
 */
function generatePagination() {
    const paginationContainer = document.getElementById('users-pagination');
    if (!paginationContainer) return;
    
    const totalPages = Math.ceil(userState.pagination.total / userState.pagination.limit);
    const currentPage = userState.pagination.page;
    
    if (totalPages <= 1) {
        paginationContainer.innerHTML = '';
        return;
    }
    
    let paginationHTML = '';
    
    // Previous button
    paginationHTML += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage - 1})" aria-label="Previous">
                <span aria-hidden="true">&laquo;</span>
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
            <a class="page-link" href="#" onclick="changePage(${currentPage + 1})" aria-label="Next">
                <span aria-hidden="true">&raquo;</span>
            </a>
        </li>
    `;
    
    paginationContainer.innerHTML = paginationHTML;
}

/**
 * Change page
 * @param {number} page - Page number
 */
function changePage(page) {
    if (page < 1 || page > Math.ceil(userState.pagination.total / userState.pagination.limit)) {
        return;
    }
    
    userState.pagination.page = page;
    loadUsers();
}

/**
 * Update pagination display
 */
function updateUserPagination() {
    const paginationStart = document.getElementById('pagination-start');
    const paginationEnd = document.getElementById('pagination-end');
    const paginationTotal = document.getElementById('pagination-total');
    
    if (paginationStart && paginationEnd && paginationTotal) {
        const start = (userState.pagination.page - 1) * userState.pagination.limit + 1;
        const end = Math.min(start + userState.users.length - 1, userState.pagination.total);
        
        paginationStart.textContent = userState.users.length > 0 ? start : 0;
        paginationEnd.textContent = userState.users.length > 0 ? end : 0;
        paginationTotal.textContent = userState.pagination.total;
    }
    
    // Generate pagination controls
    generatePagination();
} 

function updateSortIndicators() {
    // This function would update sort indicators in the table headers
    console.log('Sort indicators updated');
}

/**
 * View user details
 * @param {number} userId - User ID
 */
function viewUser(userId) {
    const user = userState.users.find(u => u.id === userId);
    if (!user) {
        showAlert('error', 'User not found');
        return;
    }
    
    // Populate view modal with user data
    document.getElementById('view-user-full-name').textContent = user.full_name || user.username || 'Unknown';
    document.getElementById('view-user-username').textContent = `@${user.username}`;
    document.getElementById('view-user-email').textContent = user.email || 'N/A';
    document.getElementById('view-user-phone').textContent = user.phone || 'Not provided';
    document.getElementById('view-user-created').textContent = formatDate(user.created_at);
    document.getElementById('view-user-last-login').textContent = user.last_login ? formatDate(user.last_login) : 'Never';
    document.getElementById('view-user-id').textContent = `#${user.id}`;
    document.getElementById('view-user-ai-agent-id').textContent = user.ai_agent_customer_id || 'Not synced';
    
    // Set status and role badges
    const statusBadge = document.getElementById('view-user-status');
    statusBadge.textContent = user.is_active ? 'Active' : 'Inactive';
    statusBadge.className = `badge ${user.is_active ? 'bg-success' : 'bg-secondary'}`;
    
    const roleBadge = document.getElementById('view-user-role');
    roleBadge.textContent = getUserRoleText(user.role, user.is_admin);
    roleBadge.className = `badge ${getRoleBadgeClass(user.role, user.is_admin)}`;
    
    // Load user activity
    loadUserActivity(userId);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('view-user-modal'));
    modal.show();
}

/**
 * Edit user
 * @param {number} userId - User ID
 */
function editUser(userId) {
    const user = userState.users.find(u => u.id === userId);
    if (!user) {
        showAlert('error', 'User not found');
        return;
    }
    
    // Close view modal if open
    const viewModal = bootstrap.Modal.getInstance(document.getElementById('view-user-modal'));
    if (viewModal) {
        viewModal.hide();
    }
    
    // Populate edit form
    document.getElementById('edit-user-id').value = user.id;
    document.getElementById('edit-user-username').value = user.username || '';
    document.getElementById('edit-user-email').value = user.email || '';
    document.getElementById('edit-user-full-name').value = user.full_name || '';
    document.getElementById('edit-user-phone').value = user.phone || '';
    document.getElementById('edit-user-role').value = user.is_admin ? 'admin' : (user.role || 'user');
    document.getElementById('edit-user-status').value = user.is_active ? 'active' : 'inactive';
    document.getElementById('edit-user-ai-agent-id').value = user.ai_agent_customer_id || '';
    
    // Show edit modal
    const modal = new bootstrap.Modal(document.getElementById('edit-user-modal'));
    modal.show();
}

/**
 * Load user activity timeline
 * @param {number} userId - User ID
 */
function loadUserActivity(userId) {
    const activityList = document.getElementById('user-activity-list');
    if (!activityList) return;
    
    // Show loading state
    activityList.innerHTML = `
        <div class="list-group-item text-center py-3">
            <div class="spinner-border spinner-border-sm" role="status"></div>
            <p class="mb-0 mt-2">Loading activity...</p>
        </div>
    `;
    
    // For now, show sample activity data
    setTimeout(() => {
        const sampleActivities = [
            {
                type: 'login',
                description: 'User logged in',
                created_at: new Date().toISOString()
            },
            {
                type: 'profile_update',
                description: 'Profile information updated',
                created_at: new Date(Date.now() - 86400000).toISOString()
            }
        ];
        renderUserActivity(sampleActivities);
    }, 1000);
}

/**
 * Render user activity timeline
 * @param {Array} activities - Activity data
 */
function renderUserActivity(activities) {
    const activityList = document.getElementById('user-activity-list');
    if (!activityList) return;
    
    if (activities.length === 0) {
        activityList.innerHTML = `
            <div class="list-group-item text-center py-3">
                <i class="bi bi-clock-history text-muted"></i>
                <p class="mb-0 mt-2 text-muted">No recent activity</p>
            </div>
        `;
        return;
    }
    
    activityList.innerHTML = activities.map(activity => `
        <div class="list-group-item">
            <div class="d-flex align-items-start">
                <div class="activity-icon me-3">
                    <i class="bi ${getActivityIcon(activity.type)} text-${getActivityColor(activity.type)}"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="activity-content">
                        <p class="mb-1">${escapeHtml(activity.description)}</p>
                        <small class="text-muted">${formatRelativeTime(activity.created_at)}</small>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Get activity icon based on type
 */
function getActivityIcon(type) {
    switch (type) {
        case 'login': return 'bi-box-arrow-in-right';
        case 'logout': return 'bi-box-arrow-right';
        case 'profile_update': return 'bi-person-gear';
        case 'password_change': return 'bi-key';
        case 'ticket_created': return 'bi-ticket-perforated';
        case 'ticket_updated': return 'bi-pencil-square';
        default: return 'bi-clock-history';
    }
}

/**
 * Get activity color based on type
 */
function getActivityColor(type) {
    switch (type) {
        case 'login': return 'success';
        case 'logout': return 'secondary';
        case 'profile_update': return 'info';
        case 'password_change': return 'warning';
        case 'ticket_created': return 'primary';
        case 'ticket_updated': return 'info';
        default: return 'muted';
    }
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
function formatRelativeTime(dateString) {
    if (!dateString) return 'Never';
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} min ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return formatDate(dateString);
    } catch (error) {
        return 'Invalid Date';
    }
}

/**
 * Check if login is recent (within 24 hours)
 */
function isRecentLogin(dateString) {
    if (!dateString) return false;
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffHours = (now - date) / (1000 * 60 * 60);
        return diffHours <= 24;
    } catch (error) {
        return false;
    }
}

/**
 * Get role icon
 */
function getRoleIcon(role, isAdmin) {
    if (isAdmin) return 'bi-shield-fill-check';
    
    switch (role?.toLowerCase()) {
        case 'admin':
            return 'bi-shield-fill-check';
        case 'support':
            return 'bi-headset';
        case 'user':
        case 'customer':
            return 'bi-person-fill';
        default:
            return 'bi-person';
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show alert message
 * @param {string} type - Alert type (success, error, warning, info)
 * @param {string} message - Alert message
 */
function showAlert(type, message) {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) {
        console.log(`${type.toUpperCase()}: ${message}`);
        return;
    }
    
    // Map error to danger for Bootstrap
    const alertType = type === 'error' ? 'danger' : type;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${alertType} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initUserManagement);