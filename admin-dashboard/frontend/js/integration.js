/**
 * Admin Dashboard - Integration Management
 * Handles integration with AI Agent backend
 */

// DOM Elements
const integrationElements = {
    statusIndicator: document.getElementById('integration-status-indicator'),
    statusText: document.getElementById('integration-status-text'),
    statusMessage: document.getElementById('integration-status-message'),
    connectionPulse: document.getElementById('connection-pulse'),
    connectionDetails: document.getElementById('connection-details'),
    lastCheckTime: document.getElementById('last-check-time'),
    usersSynced: document.getElementById('users-synced'),
    ticketsSynced: document.getElementById('tickets-synced'),
    lastSyncTime: document.getElementById('last-sync-time'),
    syncFrequency: document.getElementById('sync-frequency'),
    nextSyncTime: document.getElementById('next-sync-time'),
    syncStatusText: document.getElementById('sync-status-text'),
    usersTrend: document.getElementById('users-trend'),
    ticketsTrend: document.getElementById('tickets-trend'),
    syncProgress: document.getElementById('sync-progress'),
    progressBar: document.getElementById('progress-bar'),
    progressPercentage: document.getElementById('progress-percentage'),
    progressDetails: document.getElementById('progress-details'),
    syncNowButton: document.getElementById('btn-sync-now'),
    testConnectionButton: document.getElementById('btn-test-connection'),
    viewLogsButton: document.getElementById('btn-view-logs'),
    configForm: document.getElementById('integration-config-form'),
    configSavedIndicator: document.getElementById('config-saved-indicator'),
    validateUrlButton: document.getElementById('btn-validate-url'),
    resetConfigButton: document.getElementById('btn-reset-config'),
    exportConfigButton: document.getElementById('btn-export-config'),
    urlValidationFeedback: document.getElementById('url-validation-feedback')
};

// Integration state
const integrationState = {
    isConnected: false,
    lastSyncTime: null,
    lastCheckTime: null,
    syncInProgress: false,
    nextSyncTime: null,
    config: {
        aiAgentUrl: '',
        syncInterval: 60,
        autoSync: true,
        retryFailedSync: false,
        timeoutDuration: 30,
        maxRetries: 3
    },
    syncStats: {
        usersSynced: 0,
        ticketsSynced: 0,
        errors: 0,
        sessionUsersSynced: 0,
        sessionTicketsSynced: 0
    },
    logs: [],
    syncProgress: {
        current: 0,
        total: 0,
        stage: ''
    }
};

/**
 * Initialize integration management
 */
function initIntegrationManagement() {
    // Set up event listeners
    setupIntegrationEventListeners();
    
    // Load integration status
    checkIntegrationStatus();
    
    // Load integration config
    loadIntegrationConfig();
    
    // Set up auto-sync if enabled
    setupAutoSync();
}

/**
 * Set up integration event listeners
 */
function setupIntegrationEventListeners() {
    // Sync now button
    if (integrationElements.syncNowButton) {
        integrationElements.syncNowButton.addEventListener('click', handleSyncNow);
    }
    
    // Test connection button
    if (integrationElements.testConnectionButton) {
        integrationElements.testConnectionButton.addEventListener('click', handleTestConnection);
    }
    
    // View logs button
    if (integrationElements.viewLogsButton) {
        integrationElements.viewLogsButton.addEventListener('click', handleViewLogs);
    }
    
    // Config form
    if (integrationElements.configForm) {
        integrationElements.configForm.addEventListener('submit', handleSaveConfig);
    }
    
    // Validate URL button
    if (integrationElements.validateUrlButton) {
        integrationElements.validateUrlButton.addEventListener('click', handleValidateUrl);
    }
    
    // Reset config button
    if (integrationElements.resetConfigButton) {
        integrationElements.resetConfigButton.addEventListener('click', handleResetConfig);
    }
    
    // Export config button
    if (integrationElements.exportConfigButton) {
        integrationElements.exportConfigButton.addEventListener('click', handleExportConfig);
    }
    
    // Real-time form validation
    const urlInput = document.getElementById('ai-agent-url');
    if (urlInput) {
        urlInput.addEventListener('input', validateUrlInput);
        urlInput.addEventListener('blur', validateUrlInput);
    }
    
    const intervalInput = document.getElementById('sync-interval');
    if (intervalInput) {
        intervalInput.addEventListener('input', updateSyncFrequencyDisplay);
    }
}

/**
 * Check integration status
 */
async function checkIntegrationStatus() {
    try {
        // Show loading state
        updateStatusIndicator('loading');
        
        // Fetch integration status from API
        const response = await uiFeedback.handleApiRequest(
            () => unifiedApi.getIntegrationStatus(),
            null,
            'Checking integration status...'
        );
        
        if (response.success) {
            integrationState.isConnected = response.ai_agent_backend_available;
            updateIntegrationUI(response);
            
            // Add log entry
            addLogEntry('STATUS_CHECK', response.message);
        } else {
            showIntegrationError(response.message || 'Failed to check integration status');
        }
    } catch (error) {
        console.error('Error checking integration status:', error);
        showIntegrationError('An error occurred while checking integration status');
        
        // Add log entry
        addLogEntry('ERROR', 'Failed to check integration status: ' + error.message);
    }
}

/**
 * Update integration UI
 * @param {Object} data - Integration status data
 */
function updateIntegrationUI(data) {
    // Update status indicator
    updateStatusIndicator(integrationState.isConnected ? 'online' : 'offline');
    
    // Update connection pulse
    updateConnectionPulse(integrationState.isConnected);
    
    // Update status text
    if (integrationElements.statusText) {
        integrationElements.statusText.textContent = integrationState.isConnected ? 
            'Integration Active' : 'Integration Inactive';
    }
    
    // Update status message
    if (integrationElements.statusMessage) {
        integrationElements.statusMessage.textContent = data.message || '';
    }
    
    // Update last check time
    integrationState.lastCheckTime = new Date();
    updateLastCheckTime();
    
    // Show connection details
    if (integrationElements.connectionDetails) {
        integrationElements.connectionDetails.classList.remove('d-none');
    }
    
    // Update sync button state
    if (integrationElements.syncNowButton) {
        integrationElements.syncNowButton.disabled = !integrationState.isConnected || integrationState.syncInProgress;
    }
    
    // Update sync stats
    updateSyncStats();
    
    // Update next sync time
    updateNextSyncTime();
}

/**
 * Update status indicator
 * @param {string} status - Status (online, offline, loading)
 */
function updateStatusIndicator(status) {
    if (!integrationElements.statusIndicator) return;
    
    // Remove all status classes
    integrationElements.statusIndicator.classList.remove('online', 'offline', 'loading');
    
    // Add appropriate status class
    integrationElements.statusIndicator.classList.add(status);
}

/**
 * Update connection pulse indicator
 * @param {boolean} isConnected - Connection status
 */
function updateConnectionPulse(isConnected) {
    if (!integrationElements.connectionPulse) return;
    
    integrationElements.connectionPulse.classList.toggle('online', isConnected);
}

/**
 * Update last check time display
 */
function updateLastCheckTime() {
    if (integrationElements.lastCheckTime && integrationState.lastCheckTime) {
        integrationElements.lastCheckTime.textContent = formatDate(integrationState.lastCheckTime);
    }
}

/**
 * Update sync stats
 */
function updateSyncStats() {
    // Update users synced
    if (integrationElements.usersSynced) {
        integrationElements.usersSynced.textContent = integrationState.syncStats.usersSynced;
    }
    
    // Update tickets synced
    if (integrationElements.ticketsSynced) {
        integrationElements.ticketsSynced.textContent = integrationState.syncStats.ticketsSynced;
    }
    
    // Update session trends
    if (integrationElements.usersTrend) {
        integrationElements.usersTrend.textContent = `+${integrationState.syncStats.sessionUsersSynced}`;
    }
    
    if (integrationElements.ticketsTrend) {
        integrationElements.ticketsTrend.textContent = `+${integrationState.syncStats.sessionTicketsSynced}`;
    }
    
    // Update sync frequency display
    if (integrationElements.syncFrequency) {
        const interval = integrationState.config.syncInterval;
        if (interval >= 60) {
            const hours = Math.floor(interval / 60);
            const minutes = interval % 60;
            integrationElements.syncFrequency.textContent = minutes > 0 ? 
                `${hours}h ${minutes}m` : `${hours}h`;
        } else {
            integrationElements.syncFrequency.textContent = `${interval}m`;
        }
    }
    
    // Update last sync time
    if (integrationElements.lastSyncTime) {
        if (integrationState.lastSyncTime) {
            const timeAgo = getTimeAgo(integrationState.lastSyncTime);
            integrationElements.lastSyncTime.textContent = timeAgo;
        } else {
            integrationElements.lastSyncTime.textContent = 'Never';
        }
    }
    
    // Update sync status text
    if (integrationElements.syncStatusText) {
        if (integrationState.lastSyncTime) {
            const success = integrationState.syncStats.errors === 0;
            integrationElements.syncStatusText.innerHTML = success ? 
                '<i class="bi bi-check-circle me-1"></i>Last sync successful' :
                '<i class="bi bi-exclamation-triangle me-1"></i>Last sync had errors';
            integrationElements.syncStatusText.className = success ? 'text-success' : 'text-warning';
        } else {
            integrationElements.syncStatusText.innerHTML = '<i class="bi bi-info-circle me-1"></i>No sync performed';
            integrationElements.syncStatusText.className = 'text-muted';
        }
    }
}

/**
 * Update next sync time display
 */
function updateNextSyncTime() {
    if (!integrationElements.nextSyncTime) return;
    
    if (integrationState.config.autoSync && integrationState.isConnected) {
        const nextSync = new Date(Date.now() + (integrationState.config.syncInterval * 60 * 1000));
        integrationElements.nextSyncTime.textContent = getTimeAgo(nextSync, true);
    } else {
        integrationElements.nextSyncTime.textContent = '--';
    }
}

/**
 * Get time ago string
 * @param {Date} date - Date to compare
 * @param {boolean} future - Whether the date is in the future
 * @returns {string} Time ago string
 */
function getTimeAgo(date, future = false) {
    const now = new Date();
    const diffMs = future ? date - now : now - date;
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffDays > 0) {
        return future ? `in ${diffDays}d` : `${diffDays}d ago`;
    } else if (diffHours > 0) {
        return future ? `in ${diffHours}h` : `${diffHours}h ago`;
    } else if (diffMinutes > 0) {
        return future ? `in ${diffMinutes}m` : `${diffMinutes}m ago`;
    } else {
        return future ? 'soon' : 'just now';
    }
}

/**
 * Show integration error
 * @param {string} message - Error message
 */
function showIntegrationError(message) {
    // Update status indicator
    updateStatusIndicator('offline');
    
    // Update status text
    if (integrationElements.statusText) {
        integrationElements.statusText.textContent = 'Connection Error';
    }
    
    // Update status message
    if (integrationElements.statusMessage) {
        integrationElements.statusMessage.textContent = message || 'An error occurred';
    }
    
    // Disable sync button
    if (integrationElements.syncNowButton) {
        integrationElements.syncNowButton.disabled = true;
    }
    
    // Show alert
    showAlert('danger', message || 'Integration error');
}

/**
 * Handle sync now button click
 */
async function handleSyncNow() {
    if (!integrationState.isConnected || integrationState.syncInProgress) return;
    
    // Set sync in progress
    integrationState.syncInProgress = true;
    
    try {
        // Show loading state on button
        uiFeedback.showButtonLoading(integrationElements.syncNowButton, 'Syncing...');
        
        // Show sync progress
        showSyncProgress();
        
        // Add log entry
        addLogEntry('SYNC_START', 'Starting synchronization with AI Agent backend');
        
        // Simulate sync progress stages
        simulateSyncProgress();
        
        // Call sync API
        const response = await uiFeedback.handleApiRequest(
            () => unifiedApi.syncWithAIAgent(),
            null,
            'Synchronizing with AI Agent...'
        );
        
        if (response.success) {
            // Update sync stats
            const prevUsers = integrationState.syncStats.usersSynced;
            const prevTickets = integrationState.syncStats.ticketsSynced;
            
            integrationState.syncStats.usersSynced = response.sync_results.customers_synced || 0;
            integrationState.syncStats.ticketsSynced = response.sync_results.tickets_synced || 0;
            integrationState.lastSyncTime = new Date();
            
            // Update session stats
            integrationState.syncStats.sessionUsersSynced += Math.max(0, integrationState.syncStats.usersSynced - prevUsers);
            integrationState.syncStats.sessionTicketsSynced += Math.max(0, integrationState.syncStats.ticketsSynced - prevTickets);
            
            // Complete progress
            updateSyncProgress(100, 'Synchronization completed successfully!');
            
            // Update UI
            updateSyncStats();
            updateNextSyncTime();
            
            // Show success message
            uiFeedback.showSuccess('Synchronization completed successfully!');
            
            // Add log entry
            addLogEntry('SYNC_COMPLETE', `Sync completed: ${integrationState.syncStats.usersSynced} users and ${integrationState.syncStats.ticketsSynced} tickets synchronized`);
        } else {
            // Update progress with error
            updateSyncProgress(0, 'Synchronization failed');
            
            // Show error message
            uiFeedback.showError('Synchronization failed: ' + (response.message || 'Unknown error'));
            
            // Add log entry
            addLogEntry('SYNC_ERROR', 'Sync failed: ' + (response.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Sync error:', error);
        
        // Update progress with error
        updateSyncProgress(0, 'Synchronization error occurred');
        
        // Add log entry
        addLogEntry('SYNC_ERROR', 'Sync error: ' + error.message);
    } finally {
        // Reset sync in progress after delay
        setTimeout(() => {
            integrationState.syncInProgress = false;
            hideSyncProgress();
            
            // Reset button state
            uiFeedback.hideButtonLoading(integrationElements.syncNowButton);
            if (integrationElements.syncNowButton) {
                integrationElements.syncNowButton.disabled = !integrationState.isConnected;
            }
        }, 2000);
    }
}

/**
 * Show sync progress indicator
 */
function showSyncProgress() {
    if (integrationElements.syncProgress) {
        integrationElements.syncProgress.classList.remove('d-none');
        updateSyncProgress(0, 'Initializing synchronization...');
    }
}

/**
 * Hide sync progress indicator
 */
function hideSyncProgress() {
    if (integrationElements.syncProgress) {
        integrationElements.syncProgress.classList.add('d-none');
    }
}

/**
 * Update sync progress
 * @param {number} percentage - Progress percentage (0-100)
 * @param {string} message - Progress message
 */
function updateSyncProgress(percentage, message) {
    if (integrationElements.progressBar) {
        integrationElements.progressBar.style.width = `${percentage}%`;
        integrationElements.progressBar.setAttribute('aria-valuenow', percentage);
    }
    
    if (integrationElements.progressPercentage) {
        integrationElements.progressPercentage.textContent = `${percentage}%`;
    }
    
    if (integrationElements.progressDetails && message) {
        integrationElements.progressDetails.innerHTML = `<small class="text-muted">${message}</small>`;
    }
}

/**
 * Simulate sync progress stages
 */
function simulateSyncProgress() {
    const stages = [
        { percentage: 10, message: 'Connecting to AI Agent backend...' },
        { percentage: 25, message: 'Authenticating connection...' },
        { percentage: 40, message: 'Fetching user data...' },
        { percentage: 60, message: 'Synchronizing users...' },
        { percentage: 80, message: 'Synchronizing tickets...' },
        { percentage: 95, message: 'Finalizing synchronization...' }
    ];
    
    let currentStage = 0;
    
    const progressInterval = setInterval(() => {
        if (currentStage < stages.length && integrationState.syncInProgress) {
            const stage = stages[currentStage];
            updateSyncProgress(stage.percentage, stage.message);
            currentStage++;
        } else {
            clearInterval(progressInterval);
        }
    }, 800);
}

/**
 * Handle test connection button click
 */
function handleTestConnection() {
    // Disable button
    if (integrationElements.testConnectionButton) {
        integrationElements.testConnectionButton.disabled = true;
        integrationElements.testConnectionButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Testing...';
    }
    
    // Add log entry
    addLogEntry('TEST_CONNECTION', 'Testing connection to AI Agent backend');
    
    // Check integration status
    checkIntegrationStatus();
    
    // Reset button after delay
    setTimeout(() => {
        if (integrationElements.testConnectionButton) {
            integrationElements.testConnectionButton.disabled = false;
            integrationElements.testConnectionButton.innerHTML = '<i class="bi bi-lightning me-2"></i> Test Connection';
        }
    }, 1500);
}

/**
 * Handle view logs button click
 */
function handleViewLogs() {
    // Show logs modal
    const logsModal = new bootstrap.Modal(document.getElementById('integration-logs-modal'));
    logsModal.show();
    
    // Render logs
    renderIntegrationLogs();
}

/**
 * Render integration logs
 */
function renderIntegrationLogs() {
    const logsContainer = document.getElementById('integration-logs');
    if (!logsContainer) return;
    
    // Clear logs container
    logsContainer.innerHTML = '';
    
    if (integrationState.logs.length === 0) {
        logsContainer.innerHTML = '<div class="text-center p-4"><p>No logs available</p></div>';
        return;
    }
    
    // Create logs table
    const table = document.createElement('table');
    table.className = 'table table-sm';
    
    // Create table header
    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            <th>Time</th>
            <th>Type</th>
            <th>Message</th>
        </tr>
    `;
    table.appendChild(thead);
    
    // Create table body
    const tbody = document.createElement('tbody');
    
    // Add logs in reverse order (newest first)
    [...integrationState.logs].reverse().forEach(log => {
        const row = document.createElement('tr');
        
        // Add class based on log type
        if (log.type.includes('ERROR')) {
            row.className = 'table-danger';
        } else if (log.type.includes('WARN')) {
            row.className = 'table-warning';
        } else if (log.type.includes('SUCCESS') || log.type.includes('COMPLETE')) {
            row.className = 'table-success';
        }
        
        row.innerHTML = `
            <td>${formatDate(log.timestamp)}</td>
            <td>${log.type}</td>
            <td>${log.message}</td>
        `;
        
        tbody.appendChild(row);
    });
    
    table.appendChild(tbody);
    logsContainer.appendChild(table);
}

/**
 * Add log entry
 * @param {string} type - Log type
 * @param {string} message - Log message
 */
function addLogEntry(type, message) {
    // Add log entry
    integrationState.logs.push({
        timestamp: new Date(),
        type: type,
        message: message
    });
    
    // Limit logs to 100 entries
    if (integrationState.logs.length > 100) {
        integrationState.logs.shift();
    }
}

/**
 * Load integration config
 */
function loadIntegrationConfig() {
    // Fetch integration config from API
    unifiedApi.getIntegrationConfig()
        .then(response => {
            if (response.success) {
                // Update config state
                integrationState.config = {
                    aiAgentUrl: response.config.ai_agent_url || '',
                    syncInterval: response.config.sync_interval || 60,
                    autoSync: response.config.auto_sync !== false,
                    retryFailedSync: response.config.retry_failed_sync || false,
                    timeoutDuration: response.config.timeout_duration || 30,
                    maxRetries: response.config.max_retries || 3
                };
                
                // Update form fields
                updateConfigForm();
                
                // Add log entry
                addLogEntry('CONFIG_LOADED', 'Integration configuration loaded');
            }
        })
        .catch(error => {
            console.error('Error loading integration config:', error);
            
            // Add log entry
            addLogEntry('CONFIG_ERROR', 'Failed to load integration configuration: ' + error.message);
        });
}

/**
 * Update config form
 */
function updateConfigForm() {
    const urlInput = document.getElementById('ai-agent-url');
    const intervalInput = document.getElementById('sync-interval');
    const autoSyncInput = document.getElementById('auto-sync');
    const retryFailedSyncInput = document.getElementById('retry-failed-sync');
    const timeoutDurationInput = document.getElementById('timeout-duration');
    const maxRetriesInput = document.getElementById('max-retries');
    
    if (urlInput) urlInput.value = integrationState.config.aiAgentUrl;
    if (intervalInput) intervalInput.value = integrationState.config.syncInterval;
    if (autoSyncInput) autoSyncInput.checked = integrationState.config.autoSync;
    if (retryFailedSyncInput) retryFailedSyncInput.checked = integrationState.config.retryFailedSync;
    if (timeoutDurationInput) timeoutDurationInput.value = integrationState.config.timeoutDuration;
    if (maxRetriesInput) maxRetriesInput.value = integrationState.config.maxRetries;
    
    // Update sync frequency display
    updateSyncFrequencyDisplay();
}

/**
 * Handle save config form submission
 * @param {Event} event - Form submit event
 */
function handleSaveConfig(event) {
    event.preventDefault();
    
    // Get form values
    const aiAgentUrl = document.getElementById('ai-agent-url').value.trim();
    const syncInterval = parseInt(document.getElementById('sync-interval').value);
    const autoSync = document.getElementById('auto-sync').checked;
    const retryFailedSync = document.getElementById('retry-failed-sync').checked;
    const timeoutDuration = parseInt(document.getElementById('timeout-duration').value);
    const maxRetries = parseInt(document.getElementById('max-retries').value);
    
    // Validate form values
    if (!aiAgentUrl) {
        showAlert('danger', 'AI Agent URL is required');
        return;
    }
    
    try {
        new URL(aiAgentUrl);
    } catch (error) {
        showAlert('danger', 'Please enter a valid URL');
        return;
    }
    
    if (isNaN(syncInterval) || syncInterval < 1 || syncInterval > 1440) {
        showAlert('danger', 'Sync interval must be between 1 and 1440 minutes');
        return;
    }
    
    if (isNaN(timeoutDuration) || timeoutDuration < 5 || timeoutDuration > 300) {
        showAlert('danger', 'Timeout duration must be between 5 and 300 seconds');
        return;
    }
    
    if (isNaN(maxRetries) || maxRetries < 0 || maxRetries > 10) {
        showAlert('danger', 'Max retries must be between 0 and 10');
        return;
    }
    
    // Update config state
    integrationState.config = {
        aiAgentUrl,
        syncInterval,
        autoSync,
        retryFailedSync,
        timeoutDuration,
        maxRetries
    };
    
    // Save config to API
    unifiedApi.saveIntegrationConfig({
        ai_agent_url: aiAgentUrl,
        sync_interval: syncInterval,
        auto_sync: autoSync,
        retry_failed_sync: retryFailedSync,
        timeout_duration: timeoutDuration,
        max_retries: maxRetries
    })
        .then(response => {
            if (response.success) {
                // Show success message
                showAlert('success', 'Integration configuration saved successfully!');
                
                // Show saved indicator
                showConfigSavedIndicator();
                
                // Add log entry
                addLogEntry('CONFIG_SAVED', 'Integration configuration saved');
                
                // Update auto-sync
                setupAutoSync();
                
                // Update UI displays
                updateSyncStats();
                updateNextSyncTime();
            } else {
                // Show error message
                showAlert('danger', 'Failed to save configuration: ' + (response.message || 'Unknown error'));
                
                // Add log entry
                addLogEntry('CONFIG_ERROR', 'Failed to save configuration: ' + (response.message || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error saving integration config:', error);
            
            // Show error message
            showAlert('danger', 'An error occurred while saving configuration. Please try again.');
            
            // Add log entry
            addLogEntry('CONFIG_ERROR', 'Error saving configuration: ' + error.message);
        });
}

/**
 * Set up auto-sync
 */
function setupAutoSync() {
    // Clear existing auto-sync interval
    if (window.autoSyncInterval) {
        clearInterval(window.autoSyncInterval);
        window.autoSyncInterval = null;
    }
    
    // Set up new auto-sync interval if enabled
    if (integrationState.config.autoSync) {
        const intervalMs = integrationState.config.syncInterval * 60 * 1000; // Convert minutes to milliseconds
        
        window.autoSyncInterval = setInterval(() => {
            // Only sync if connected and not already syncing
            if (integrationState.isConnected && !integrationState.syncInProgress) {
                // Add log entry
                addLogEntry('AUTO_SYNC', 'Auto-sync triggered');
                
                // Trigger sync
                handleSyncNow();
            }
        }, intervalMs);
        
        // Add log entry
        addLogEntry('AUTO_SYNC_SETUP', `Auto-sync enabled with interval of ${integrationState.config.syncInterval} minutes`);
    } else {
        // Add log entry
        addLogEntry('AUTO_SYNC_DISABLED', 'Auto-sync disabled');
    }
}

/**
 * Show alert
 * @param {string} type - Alert type (success, danger, warning, info)
 * @param {string} message - Alert message
 */
function showAlert(type, message) {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }, 5000);
}

/**
 * Handle validate URL button click
 */
function handleValidateUrl() {
    const urlInput = document.getElementById('ai-agent-url');
    if (!urlInput) return;
    
    const url = urlInput.value.trim();
    if (!url) {
        showUrlValidationFeedback(false, 'URL is required');
        return;
    }
    
    // Disable button during validation
    if (integrationElements.validateUrlButton) {
        integrationElements.validateUrlButton.disabled = true;
        integrationElements.validateUrlButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    }
    
    // Simulate URL validation (in real implementation, this would make an API call)
    setTimeout(() => {
        try {
            new URL(url);
            showUrlValidationFeedback(true, 'URL format is valid');
        } catch (error) {
            showUrlValidationFeedback(false, 'Invalid URL format');
        }
        
        // Reset button
        if (integrationElements.validateUrlButton) {
            integrationElements.validateUrlButton.disabled = false;
            integrationElements.validateUrlButton.innerHTML = '<i class="bi bi-check-circle"></i>';
        }
    }, 1000);
}

/**
 * Show URL validation feedback
 * @param {boolean} isValid - Whether the URL is valid
 * @param {string} message - Validation message
 */
function showUrlValidationFeedback(isValid, message) {
    const urlInput = document.getElementById('ai-agent-url');
    if (!urlInput) return;
    
    // Update input classes
    urlInput.classList.remove('is-valid', 'is-invalid');
    urlInput.classList.add(isValid ? 'is-valid' : 'is-invalid');
    
    // Update feedback message
    if (integrationElements.urlValidationFeedback) {
        integrationElements.urlValidationFeedback.textContent = message;
        integrationElements.urlValidationFeedback.className = isValid ? 'valid-feedback' : 'invalid-feedback';
    }
}

/**
 * Validate URL input in real-time
 */
function validateUrlInput() {
    const urlInput = document.getElementById('ai-agent-url');
    if (!urlInput) return;
    
    const url = urlInput.value.trim();
    if (!url) {
        urlInput.classList.remove('is-valid', 'is-invalid');
        return;
    }
    
    try {
        new URL(url);
        urlInput.classList.remove('is-invalid');
        urlInput.classList.add('is-valid');
    } catch (error) {
        urlInput.classList.remove('is-valid');
        urlInput.classList.add('is-invalid');
    }
}

/**
 * Update sync frequency display
 */
function updateSyncFrequencyDisplay() {
    const intervalInput = document.getElementById('sync-interval');
    if (!intervalInput) return;
    
    const interval = parseInt(intervalInput.value);
    if (isNaN(interval)) return;
    
    // Update the config state
    integrationState.config.syncInterval = interval;
    
    // Update the display in stats
    updateSyncStats();
    updateNextSyncTime();
}

/**
 * Handle reset config button click
 */
function handleResetConfig() {
    if (!confirm('Are you sure you want to reset the configuration to default values?')) {
        return;
    }
    
    // Reset to default values
    integrationState.config = {
        aiAgentUrl: '',
        syncInterval: 60,
        autoSync: true,
        retryFailedSync: false,
        timeoutDuration: 30,
        maxRetries: 3
    };
    
    // Update form
    updateConfigForm();
    
    // Show success message
    showAlert('info', 'Configuration reset to default values');
    
    // Add log entry
    addLogEntry('CONFIG_RESET', 'Configuration reset to default values');
}

/**
 * Handle export config button click
 */
function handleExportConfig() {
    const config = {
        ...integrationState.config,
        exportedAt: new Date().toISOString(),
        version: '1.0'
    };
    
    const dataStr = JSON.stringify(config, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `integration-config-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    
    // Show success message
    showAlert('success', 'Configuration exported successfully');
    
    // Add log entry
    addLogEntry('CONFIG_EXPORT', 'Configuration exported to file');
}

/**
 * Show config saved indicator
 */
function showConfigSavedIndicator() {
    if (integrationElements.configSavedIndicator) {
        integrationElements.configSavedIndicator.classList.remove('d-none');
        
        // Hide after 3 seconds
        setTimeout(() => {
            integrationElements.configSavedIndicator.classList.add('d-none');
        }, 3000);
    }
}

// Initialize integration management when the DOM is loaded
document.addEventListener('DOMContentLoaded', initIntegrationManagement);