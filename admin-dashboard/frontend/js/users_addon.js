/**
 * Additional functions for users.js
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