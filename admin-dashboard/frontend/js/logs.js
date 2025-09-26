/**
 * Admin Dashboard - System Logs Management
 * Enhanced implementation with complete functionality for log viewing, filtering, 
 * searching, real-time updates, and export capabilities
 */

// DOM Elements
const logsElements = {
    // Main containers
    logViewer: document.getElementById('log-viewer'),
    alertContainer: document.getElementById('alert-container'),
    loadingSpinner: document.getElementById('loading-spinner'),
    
    // Statistics
    totalLogs: document.getElementById('total-logs'),
    errorLogs: document.getElementById('error-logs'),
    warningLogs: document.getElementById('warning-logs'),
    infoLogs: document.getElementById('info-logs'),
    
    // Filter controls
    logLevelFilter: document.getElementById('log-level-filter'),
    categoryFilter: document.getElementById('category-filter'),
    dateFromFilter: document.getElementById('date-from'),
    dateToFilter: document.getElementById('date-to'),
    logSearchInput: document.getElementById('log-search'),
    globalSearchInput: document.getElementById('global-search'),
    
    // Action buttons
    btnSearch: document.getElementById('btn-search'),
    btnClearFilters: document.getElementById('btn-clear-filters'),
    btnToggleRealtime: document.getElementById('btn-toggle-realtime'),
    btnRefreshLogs: document.getElementById('btn-refresh-logs'),
    btnAutoScroll: document.getElementById('btn-auto-scroll'),
    btnScrollTop: document.getElementById('btn-scroll-top'),
    btnScrollBottom: document.getElementById('btn-scroll-bottom'),
    btnClearLogs: document.getElementById('btn-clear-logs'),
    
    // Export buttons
    exportJson: document.getElementById('export-json'),
    exportCsv: document.getElementById('export-csv'),
    exportTxt: document.getElementById('export-txt'),
    
    // Real-time status
    realTimeStatus: document.getElementById('real-time-status'),
    
    // Pagination
    logCount: document.getElementById('log-count'),
    logPagination: document.getElementById('log-pagination'),
    prevPage: document.getElementById('prev-page'),
    nextPage: document.getElementById('next-page'),
    currentPage: document.getElementById('current-page'),
    
    // Modal
    clearLogsModal: document.getElementById('clearLogsModal'),
    confirmClearLogsBtn: document.getElementById('confirm-clear-logs-btn'),
    confirmClearLogsCheckbox: document.getElementById('confirm-clear-logs')
};

// Enhanced logs state management
const logsState = {
    logs: [],
    filteredLogs: [],
    currentPage: 1,
    logsPerPage: 50,
    totalPages: 1,
    isRealTimeActive: false,
    isAutoScrollEnabled: false,
    realTimeInterval: null,
    realTimePollingInterval: 5000, // 5 seconds
    searchTerm: '',
    lastLogTimestamp: null,
    isLoading: false,
    filters: {
        level: '',
        category: '',
        dateFrom: '',
        dateTo: ''
    },
    statistics: {
        total: 0,
        error: 0,
        warning: 0,
        info: 0,
        debug: 0
    },
    // Enhanced search and highlighting
    searchHighlightEnabled: true,
    caseSensitiveSearch: false,
    // Export settings
    exportFormats: ['json', 'csv', 'txt'],
    // WebSocket connection for real-time updates (if available)
    websocket: null,
    websocketUrl: null
};

/**
 * Initialize logs management
 */
function initLogsManagement() {
    console.log('Initializing logs management...');
    
    // Set up event listeners
    setupLogsEventListeners();
    
    // Load initial logs
    loadLogs();
    
    // Set up real-time updates (disabled by default)
    setupRealTimeUpdates();
    
    // Initialize search functionality
    setupSearchFunctionality();
    
    // Set default date filters (last 24 hours)
    setDefaultDateFilters();
    
    console.log('Logs management initialized successfully');
}

/**
 * Set up event listeners for logs functionality
 */
function setupLogsEventListeners() {
    // Filter controls
    logsElements.logLevelFilter?.addEventListener('change', applyFilters);
    logsElements.categoryFilter?.addEventListener('change', applyFilters);
    logsElements.dateFromFilter?.addEventListener('change', applyFilters);
    logsElements.dateToFilter?.addEventListener('change', applyFilters);
    
    // Search functionality
    logsElements.btnSearch?.addEventListener('click', performSearch);
    logsElements.logSearchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });
    logsElements.globalSearchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            logsElements.logSearchInput.value = e.target.value;
            performSearch();
        }
    });
    
    // Action buttons
    logsElements.btnClearFilters?.addEventListener('click', clearAllFilters);
    logsElements.btnToggleRealtime?.addEventListener('click', toggleRealTime);
    logsElements.btnRefreshLogs?.addEventListener('click', refreshLogs);
    logsElements.btnAutoScroll?.addEventListener('click', toggleAutoScroll);
    logsElements.btnScrollTop?.addEventListener('click', scrollToTop);
    logsElements.btnScrollBottom?.addEventListener('click', scrollToBottom);
    logsElements.btnClearLogs?.addEventListener('click', showClearLogsModal);
    
    // Export functionality
    logsElements.exportJson?.addEventListener('click', () => exportLogs('json'));
    logsElements.exportCsv?.addEventListener('click', () => exportLogs('csv'));
    logsElements.exportTxt?.addEventListener('click', () => exportLogs('txt'));
    
    // Pagination
    logsElements.prevPage?.addEventListener('click', (e) => {
        e.preventDefault();
        if (logsState.currentPage > 1) {
            logsState.currentPage--;
            renderLogs();
        }
    });
    
    logsElements.nextPage?.addEventListener('click', (e) => {
        e.preventDefault();
        if (logsState.currentPage < logsState.totalPages) {
            logsState.currentPage++;
            renderLogs();
        }
    });
    
    // Clear logs modal
    logsElements.confirmClearLogsCheckbox?.addEventListener('change', (e) => {
        logsElements.confirmClearLogsBtn.disabled = !e.target.checked;
    });
    
    logsElements.confirmClearLogsBtn?.addEventListener('click', confirmClearLogs);
}

/**
 * Load logs from the server with enhanced error handling and API integration
 */
async function loadLogs(showLoading = true) {
    if (logsState.isLoading) return;
    
    try {
        logsState.isLoading = true;
        if (showLoading) showLoadingState();
        
        // Build query parameters
        const params = new URLSearchParams({
            limit: logsState.logsPerPage.toString(),
            skip: ((logsState.currentPage - 1) * logsState.logsPerPage).toString()
        });
        
        // Add filters to query
        if (logsState.filters.level) params.append('level', logsState.filters.level);
        if (logsState.filters.category) params.append('category', logsState.filters.category);
        if (logsState.filters.dateFrom) params.append('since', logsState.filters.dateFrom);
        
        // Get authentication token
        const token = getAuthToken();
        if (!token) {
            throw new Error('Authentication token not found');
        }
        
        const response = await fetch(`/api/admin/logs?${params}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Authentication failed. Please log in again.');
            } else if (response.status === 403) {
                throw new Error('Access denied. Admin privileges required.');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            logsState.logs = data.logs || [];
            
            // Update last log timestamp for real-time updates
            if (logsState.logs.length > 0) {
                logsState.lastLogTimestamp = logsState.logs[0].timestamp;
            }
            
            // Apply current search filter
            applySearchFilter();
            
            // Update statistics
            updateStatistics();
            
            // Render logs
            renderLogs();
            
            if (showLoading) hideLoadingState();
            
        } else {
            throw new Error(data.message || 'Failed to load logs');
        }
        
    } catch (error) {
        console.error('Error loading logs:', error);
        
        if (showLoading) hideLoadingState();
        
        // Show appropriate error message
        if (error.message.includes('Authentication')) {
            showAlert('Authentication error. Please log in again.', 'danger');
            // Redirect to login if needed
            if (typeof redirectToLogin === 'function') {
                redirectToLogin();
            }
        } else if (error.message.includes('Access denied')) {
            showAlert('Access denied. Admin privileges required.', 'danger');
        } else {
            // Use sample data as fallback for demo purposes
            console.log('Using sample data as fallback');
            logsState.logs = generateSampleLogs();
            applySearchFilter();
            updateStatistics();
            renderLogs();
            if (showLoading) hideLoadingState();
            
            showAlert('Warning: Using sample log data. Could not connect to log service.', 'warning');
        }
    } finally {
        logsState.isLoading = false;
    }
}

/**
 * Generate sample logs for demonstration
 */
function generateSampleLogs() {
    const levels = ['error', 'warning', 'info', 'debug'];
    const categories = ['auth', 'api', 'database', 'integration', 'system'];
    const messages = [
        'User authentication successful',
        'Database connection established',
        'API request processed',
        'Integration sync completed',
        'System startup completed',
        'Failed login attempt detected',
        'Database query timeout',
        'API rate limit exceeded',
        'Integration connection failed',
        'System memory usage high',
        'User session expired',
        'Database backup completed',
        'API endpoint deprecated',
        'Integration data synchronized',
        'System maintenance scheduled'
    ];
    
    const logs = [];
    const now = new Date();
    
    for (let i = 0; i < 200; i++) {
        const timestamp = new Date(now.getTime() - (i * 60000 * Math.random() * 1440)); // Random time in last day
        const level = levels[Math.floor(Math.random() * levels.length)];
        const category = categories[Math.floor(Math.random() * categories.length)];
        const message = messages[Math.floor(Math.random() * messages.length)];
        
        logs.push({
            id: i + 1,
            timestamp: timestamp.toISOString(),
            level: level,
            category: category,
            message: `${message} - ID: ${i + 1}`,
            source: 'admin-dashboard',
            details: {
                userId: Math.floor(Math.random() * 1000),
                ip: `192.168.1.${Math.floor(Math.random() * 255)}`,
                userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        });
    }
    
    return logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
}

/**
 * Apply current filters to logs (enhanced with better filtering logic)
 */
function applyFilters() {
    // Update filters from form elements
    updateFiltersFromForm();
    
    // Reload logs with server-side filtering for better performance
    loadLogs();
}

/**
 * Apply search filter to already loaded logs (client-side)
 */
function applySearchFilter() {
    let filtered = [...logsState.logs];
    
    // Apply search filter
    if (logsState.searchTerm) {
        const searchTerm = logsState.caseSensitiveSearch ? 
            logsState.searchTerm : 
            logsState.searchTerm.toLowerCase();
            
        filtered = filtered.filter(log => {
            const message = logsState.caseSensitiveSearch ? 
                log.message : 
                log.message.toLowerCase();
            const category = logsState.caseSensitiveSearch ? 
                log.category : 
                log.category.toLowerCase();
            const level = logsState.caseSensitiveSearch ? 
                log.level : 
                log.level.toLowerCase();
            
            return message.includes(searchTerm) ||
                   category.includes(searchTerm) ||
                   level.includes(searchTerm) ||
                   (log.source && (logsState.caseSensitiveSearch ? 
                       log.source : 
                       log.source.toLowerCase()).includes(searchTerm));
        });
    }
    
    logsState.filteredLogs = filtered;
    logsState.currentPage = 1;
    logsState.totalPages = Math.ceil(filtered.length / logsState.logsPerPage);
    
    updateLogCount();
}

/**
 * Update filters from form elements
 */
function updateFiltersFromForm() {
    logsState.filters.level = logsElements.logLevelFilter?.value || '';
    logsState.filters.category = logsElements.categoryFilter?.value || '';
    logsState.filters.dateFrom = logsElements.dateFromFilter?.value || '';
    logsState.filters.dateTo = logsElements.dateToFilter?.value || '';
    logsState.searchTerm = logsElements.logSearchInput?.value || '';
}

/**
 * Render logs in the viewer
 */
function renderLogs() {
    if (!logsElements.logViewer) return;
    
    const startIndex = (logsState.currentPage - 1) * logsState.logsPerPage;
    const endIndex = startIndex + logsState.logsPerPage;
    const logsToShow = logsState.filteredLogs.slice(startIndex, endIndex);
    
    if (logsToShow.length === 0) {
        logsElements.logViewer.innerHTML = `
            <div class="text-center py-5 text-muted">
                <i class="bi bi-inbox display-1"></i>
                <h4>No logs found</h4>
                <p>Try adjusting your filters or search criteria.</p>
            </div>
        `;
        return;
    }
    
    const logsHtml = logsToShow.map(log => {
        const timestamp = new Date(log.timestamp).toLocaleString();
        const highlightedMessage = highlightSearchTerm(log.message, logsState.searchTerm);
        
        return `
            <div class="log-entry ${log.level}" data-log-id="${log.id}">
                <span class="log-timestamp">${timestamp}</span>
                <span class="log-level ${log.level}">[${log.level.toUpperCase()}]</span>
                <span class="log-category">[${log.category}]</span>
                <span class="log-message">${highlightedMessage}</span>
            </div>
        `;
    }).join('');
    
    logsElements.logViewer.innerHTML = logsHtml;
    
    // Update pagination
    updatePagination();
    
    // Auto-scroll to bottom if enabled
    if (logsState.isAutoScrollEnabled) {
        scrollToBottom();
    }
}

/**
 * Enhanced search term highlighting with better regex handling
 */
function highlightSearchTerm(message, searchTerm) {
    if (!searchTerm || !logsState.searchHighlightEnabled) return message;
    
    try {
        // Escape special regex characters
        const escapedTerm = searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const flags = logsState.caseSensitiveSearch ? 'g' : 'gi';
        const regex = new RegExp(`(${escapedTerm})`, flags);
        
        return message.replace(regex, '<span class="log-search-highlight">$1</span>');
    } catch (error) {
        console.warn('Error highlighting search term:', error);
        return message;
    }
}

/**
 * Update log count display
 */
function updateLogCount() {
    if (logsElements.logCount) {
        const total = logsState.filteredLogs.length;
        const start = (logsState.currentPage - 1) * logsState.logsPerPage + 1;
        const end = Math.min(start + logsState.logsPerPage - 1, total);
        
        if (total === 0) {
            logsElements.logCount.textContent = 'No entries found';
        } else {
            logsElements.logCount.textContent = `Showing ${start}-${end} of ${total} entries`;
        }
    }
}

/**
 * Update pagination controls
 */
function updatePagination() {
    if (!logsElements.logPagination) return;
    
    // Update current page display
    if (logsElements.currentPage) {
        logsElements.currentPage.textContent = logsState.currentPage;
    }
    
    // Update previous button
    if (logsElements.prevPage) {
        const prevItem = logsElements.prevPage.parentElement;
        if (logsState.currentPage <= 1) {
            prevItem.classList.add('disabled');
        } else {
            prevItem.classList.remove('disabled');
        }
    }
    
    // Update next button
    if (logsElements.nextPage) {
        const nextItem = logsElements.nextPage.parentElement;
        if (logsState.currentPage >= logsState.totalPages) {
            nextItem.classList.add('disabled');
        } else {
            nextItem.classList.remove('disabled');
        }
    }
}

/**
 * Update statistics display
 */
function updateStatistics() {
    const stats = {
        total: logsState.logs.length,
        error: logsState.logs.filter(log => log.level === 'error').length,
        warning: logsState.logs.filter(log => log.level === 'warning').length,
        info: logsState.logs.filter(log => log.level === 'info').length,
        debug: logsState.logs.filter(log => log.level === 'debug').length
    };
    
    logsState.statistics = stats;
    
    // Update DOM elements
    if (logsElements.totalLogs) logsElements.totalLogs.textContent = stats.total;
    if (logsElements.errorLogs) logsElements.errorLogs.textContent = stats.error;
    if (logsElements.warningLogs) logsElements.warningLogs.textContent = stats.warning;
    if (logsElements.infoLogs) logsElements.infoLogs.textContent = stats.info;
}

/**
 * Perform search
 */
function performSearch() {
    logsState.searchTerm = logsElements.logSearchInput?.value || '';
    
    // Update filters from form
    logsState.filters.level = logsElements.logLevelFilter?.value || '';
    logsState.filters.category = logsElements.categoryFilter?.value || '';
    logsState.filters.dateFrom = logsElements.dateFromFilter?.value || '';
    logsState.filters.dateTo = logsElements.dateToFilter?.value || '';
    
    applyFilters();
    renderLogs();
}

/**
 * Clear all filters
 */
function clearAllFilters() {
    // Reset form elements
    if (logsElements.logLevelFilter) logsElements.logLevelFilter.value = '';
    if (logsElements.categoryFilter) logsElements.categoryFilter.value = '';
    if (logsElements.dateFromFilter) logsElements.dateFromFilter.value = '';
    if (logsElements.dateToFilter) logsElements.dateToFilter.value = '';
    if (logsElements.logSearchInput) logsElements.logSearchInput.value = '';
    if (logsElements.globalSearchInput) logsElements.globalSearchInput.value = '';
    
    // Reset state
    logsState.searchTerm = '';
    logsState.filters = {
        level: '',
        category: '',
        dateFrom: '',
        dateTo: ''
    };
    
    // Apply filters and render
    applyFilters();
    renderLogs();
    
    showAlert('All filters cleared', 'success');
}

/**
 * Toggle real-time updates
 */
function toggleRealTime() {
    if (logsState.isRealTimeActive) {
        stopRealTime();
    } else {
        startRealTime();
    }
}

/**
 * Start real-time log updates with WebSocket fallback to polling
 */
function startRealTime() {
    logsState.isRealTimeActive = true;
    
    // Update UI
    if (logsElements.btnToggleRealtime) {
        logsElements.btnToggleRealtime.innerHTML = '<i class="bi bi-pause-circle"></i> Stop Real-time';
        logsElements.btnToggleRealtime.classList.remove('btn-outline-primary');
        logsElements.btnToggleRealtime.classList.add('btn-outline-danger');
    }
    
    if (logsElements.realTimeStatus) {
        logsElements.realTimeStatus.classList.remove('inactive');
        logsElements.realTimeStatus.classList.add('active');
        logsElements.realTimeStatus.querySelector('.status-text').textContent = 'Real-time: Connecting...';
    }
    
    // Try WebSocket first, fallback to polling
    const webSocketConnected = setupWebSocketConnection();
    
    if (!webSocketConnected) {
        // Fallback to polling
        console.log('Using polling for real-time updates');
        logsState.realTimeInterval = setInterval(fetchNewLogs, logsState.realTimePollingInterval);
        
        if (logsElements.realTimeStatus) {
            logsElements.realTimeStatus.querySelector('.status-text').textContent = 'Real-time: Polling';
        }
    }
    
    showAlert('Real-time log updates started', 'success');
}

/**
 * Stop real-time log updates (both WebSocket and polling)
 */
function stopRealTime() {
    logsState.isRealTimeActive = false;
    
    // Clear polling interval
    if (logsState.realTimeInterval) {
        clearInterval(logsState.realTimeInterval);
        logsState.realTimeInterval = null;
    }
    
    // Close WebSocket connection
    if (logsState.websocket) {
        logsState.websocket.close();
        logsState.websocket = null;
    }
    
    // Update UI
    if (logsElements.btnToggleRealtime) {
        logsElements.btnToggleRealtime.innerHTML = '<i class="bi bi-play-circle"></i> Start Real-time';
        logsElements.btnToggleRealtime.classList.remove('btn-outline-danger');
        logsElements.btnToggleRealtime.classList.add('btn-outline-primary');
    }
    
    if (logsElements.realTimeStatus) {
        logsElements.realTimeStatus.classList.remove('active');
        logsElements.realTimeStatus.classList.add('inactive');
        logsElements.realTimeStatus.querySelector('.status-text').textContent = 'Real-time: Off';
    }
    
    showAlert('Real-time log updates stopped', 'info');
}

/**
 * Enhanced real-time log fetching with better error handling
 */
async function fetchNewLogs() {
    if (logsState.isLoading) return;
    
    try {
        const lastLogTime = logsState.lastLogTimestamp || 
            (logsState.logs.length > 0 ? logsState.logs[0].timestamp : new Date().toISOString());
        
        const token = getAuthToken();
        if (!token) {
            console.warn('No auth token available for real-time updates');
            stopRealTime();
            return;
        }
        
        const response = await fetch(`/api/admin/logs/new?since=${encodeURIComponent(lastLogTime)}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.logs && data.logs.length > 0) {
                // Add new logs to the beginning of the array
                logsState.logs = [...data.logs, ...logsState.logs];
                
                // Update last log timestamp
                logsState.lastLogTimestamp = data.logs[0].timestamp;
                
                // Apply search filter and update display
                applySearchFilter();
                updateStatistics();
                renderLogs();
                
                // Show notification for new logs (less intrusive)
                console.log(`${data.logs.length} new log entries received`);
                
                // Update real-time indicator
                updateRealTimeIndicator(true);
            }
        } else if (response.status === 401) {
            console.warn('Authentication failed during real-time update');
            stopRealTime();
            showAlert('Real-time updates stopped: Authentication required', 'warning');
        }
    } catch (error) {
        console.error('Error fetching new logs:', error);
        // Update real-time indicator to show connection issues
        updateRealTimeIndicator(false);
    }
}

/**
 * Update real-time indicator status
 */
function updateRealTimeIndicator(isConnected) {
    if (logsElements.realTimeStatus) {
        const statusText = logsElements.realTimeStatus.querySelector('.status-text');
        if (isConnected) {
            logsElements.realTimeStatus.classList.remove('inactive');
            logsElements.realTimeStatus.classList.add('active');
            if (statusText) statusText.textContent = 'Real-time: Connected';
        } else {
            logsElements.realTimeStatus.classList.remove('active');
            logsElements.realTimeStatus.classList.add('inactive');
            if (statusText) statusText.textContent = 'Real-time: Connection Issues';
        }
    }
}

/**
 * Toggle auto-scroll functionality
 */
function toggleAutoScroll() {
    logsState.isAutoScrollEnabled = !logsState.isAutoScrollEnabled;
    
    if (logsElements.btnAutoScroll) {
        if (logsState.isAutoScrollEnabled) {
            logsElements.btnAutoScroll.innerHTML = '<i class="bi bi-arrow-down-circle-fill"></i> Auto-scroll: On';
            logsElements.btnAutoScroll.classList.remove('btn-outline-secondary');
            logsElements.btnAutoScroll.classList.add('btn-secondary');
            logsElements.btnAutoScroll.setAttribute('data-auto-scroll', 'true');
        } else {
            logsElements.btnAutoScroll.innerHTML = '<i class="bi bi-arrow-down-circle"></i> Auto-scroll: Off';
            logsElements.btnAutoScroll.classList.remove('btn-secondary');
            logsElements.btnAutoScroll.classList.add('btn-outline-secondary');
            logsElements.btnAutoScroll.setAttribute('data-auto-scroll', 'false');
        }
    }
}

/**
 * Scroll to top of log viewer
 */
function scrollToTop() {
    if (logsElements.logViewer) {
        logsElements.logViewer.scrollTop = 0;
    }
}

/**
 * Scroll to bottom of log viewer
 */
function scrollToBottom() {
    if (logsElements.logViewer) {
        logsElements.logViewer.scrollTop = logsElements.logViewer.scrollHeight;
    }
}

/**
 * Refresh logs
 */
function refreshLogs() {
    showAlert('Refreshing logs...', 'info');
    loadLogs();
}

/**
 * Show clear logs confirmation modal
 */
function showClearLogsModal() {
    const modal = new bootstrap.Modal(logsElements.clearLogsModal);
    modal.show();
}

/**
 * Confirm and execute log clearing with enhanced error handling
 */
async function confirmClearLogs() {
    try {
        const token = getAuthToken();
        if (!token) {
            throw new Error('Authentication token not found');
        }
        
        // Show loading state
        logsElements.confirmClearLogsBtn.disabled = true;
        logsElements.confirmClearLogsBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Clearing...';
        
        const response = await fetch('/api/admin/logs', {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.success) {
                // Clear local logs
                logsState.logs = [];
                logsState.filteredLogs = [];
                logsState.lastLogTimestamp = null;
                
                // Update display
                updateStatistics();
                renderLogs();
                
                // Hide modal
                const modal = bootstrap.Modal.getInstance(logsElements.clearLogsModal);
                modal.hide();
                
                // Reset modal state
                resetClearLogsModal();
                
                showAlert('All logs have been cleared successfully', 'success');
                
                // Log the action
                console.log('System logs cleared by admin user');
                
            } else {
                throw new Error(data.message || 'Failed to clear logs');
            }
        } else if (response.status === 401) {
            throw new Error('Authentication failed. Please log in again.');
        } else if (response.status === 403) {
            throw new Error('Access denied. Admin privileges required.');
        } else {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
    } catch (error) {
        console.error('Error clearing logs:', error);
        
        // Reset button state
        resetClearLogsModal();
        
        // Show appropriate error message
        if (error.message.includes('Authentication')) {
            showAlert('Authentication error. Please log in again.', 'danger');
        } else if (error.message.includes('Access denied')) {
            showAlert('Access denied. Admin privileges required.', 'danger');
        } else {
            showAlert(`Failed to clear logs: ${error.message}`, 'danger');
        }
    }
}

/**
 * Reset clear logs modal to initial state
 */
function resetClearLogsModal() {
    if (logsElements.confirmClearLogsCheckbox) {
        logsElements.confirmClearLogsCheckbox.checked = false;
    }
    if (logsElements.confirmClearLogsBtn) {
        logsElements.confirmClearLogsBtn.disabled = true;
        logsElements.confirmClearLogsBtn.innerHTML = 'Clear All Logs';
    }
}

/**
 * Enhanced log export functionality with multiple formats and better formatting
 */
function exportLogs(format) {
    const logsToExport = logsState.filteredLogs.length > 0 ? logsState.filteredLogs : logsState.logs;
    
    if (logsToExport.length === 0) {
        showAlert('No logs to export', 'warning');
        return;
    }
    
    try {
        let content = '';
        let filename = '';
        let mimeType = '';
        
        const timestamp = new Date().toISOString().split('T')[0];
        const timeStr = new Date().toTimeString().split(' ')[0].replace(/:/g, '-');
        
        switch (format.toLowerCase()) {
            case 'json':
                content = JSON.stringify({
                    exported_at: new Date().toISOString(),
                    total_logs: logsToExport.length,
                    filters_applied: logsState.filters,
                    search_term: logsState.searchTerm,
                    logs: logsToExport
                }, null, 2);
                filename = `system-logs-${timestamp}-${timeStr}.json`;
                mimeType = 'application/json';
                break;
                
            case 'csv':
                const headers = ['Timestamp', 'Level', 'Category', 'Message', 'Source', 'User ID', 'IP Address'];
                const csvRows = [headers.join(',')];
                
                logsToExport.forEach(log => {
                    const row = [
                        `"${log.timestamp}"`,
                        `"${log.level}"`,
                        `"${log.category}"`,
                        `"${log.message.replace(/"/g, '""')}"`,
                        `"${log.source || ''}"`,
                        `"${log.details?.userId || ''}"`,
                        `"${log.details?.ip || ''}"`
                    ];
                    csvRows.push(row.join(','));
                });
                
                content = csvRows.join('\n');
                filename = `system-logs-${timestamp}-${timeStr}.csv`;
                mimeType = 'text/csv';
                break;
                
            case 'txt':
                const header = `System Logs Export
Exported: ${new Date().toLocaleString()}
Total Logs: ${logsToExport.length}
Filters: ${JSON.stringify(logsState.filters)}
Search Term: ${logsState.searchTerm || 'None'}
${'='.repeat(80)}

`;
                
                const logEntries = logsToExport.map(log => {
                    const timestamp = new Date(log.timestamp).toLocaleString();
                    const details = log.details ? 
                        ` | User: ${log.details.userId || 'N/A'} | IP: ${log.details.ip || 'N/A'}` : '';
                    return `${timestamp} [${log.level.toUpperCase()}] [${log.category}] ${log.message}${details}`;
                }).join('\n');
                
                content = header + logEntries;
                filename = `system-logs-${timestamp}-${timeStr}.txt`;
                mimeType = 'text/plain';
                break;
                
            default:
                throw new Error(`Unsupported export format: ${format}`);
        }
        
        // Create and trigger download
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showAlert(`${logsToExport.length} logs exported as ${format.toUpperCase()} successfully`, 'success');
        
        // Log the export action
        console.log(`Logs exported: ${filename}, Format: ${format}, Count: ${logsToExport.length}`);
        
    } catch (error) {
        console.error('Export error:', error);
        showAlert(`Failed to export logs: ${error.message}`, 'danger');
    }
}

/**
 * Set default date filters (last 24 hours)
 */
function setDefaultDateFilters() {
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    
    if (logsElements.dateFromFilter) {
        logsElements.dateFromFilter.value = yesterday.toISOString().slice(0, 16);
    }
    
    if (logsElements.dateToFilter) {
        logsElements.dateToFilter.value = now.toISOString().slice(0, 16);
    }
}

/**
 * Setup real-time updates infrastructure
 */
function setupRealTimeUpdates() {
    // Real-time updates are disabled by default
    // They can be enabled by clicking the toggle button
}

/**
 * Setup search functionality
 */
function setupSearchFunctionality() {
    // Real-time search as user types (debounced)
    let searchTimeout;
    
    logsElements.logSearchInput?.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            logsState.searchTerm = e.target.value;
            applyFilters();
            renderLogs();
        }, 300);
    });
}

/**
 * Show loading state
 */
function showLoadingState() {
    if (logsElements.loadingSpinner) {
        logsElements.loadingSpinner.style.display = 'block';
    }
}

/**
 * Hide loading state
 */
function hideLoadingState() {
    if (logsElements.loadingSpinner) {
        logsElements.loadingSpinner.style.display = 'none';
    }
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    if (!logsElements.alertContainer) return;
    
    const alertId = 'alert-' + Date.now();
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert" id="${alertId}">
            <i class="bi bi-${getAlertIcon(type)}"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    logsElements.alertContainer.insertAdjacentHTML('beforeend', alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            const alert = new bootstrap.Alert(alertElement);
            alert.close();
        }
    }, 5000);
}

/**
 * Get appropriate icon for alert type
 */
function getAlertIcon(type) {
    const icons = {
        success: 'check-circle',
        danger: 'exclamation-triangle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    return icons[type] || 'info-circle';
}

/**
 * Get authentication token from various sources
 */
function getAuthToken() {
    // Try multiple sources for the token
    return localStorage.getItem('adminToken') || 
           localStorage.getItem('authToken') || 
           sessionStorage.getItem('adminToken') || 
           sessionStorage.getItem('authToken') ||
           getCookie('session_token');
}

/**
 * Get cookie value by name
 */
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

/**
 * Enhanced log level management with color coding
 */
function getLogLevelInfo(level) {
    const levelInfo = {
        error: { color: '#f44336', icon: 'exclamation-triangle', priority: 4 },
        warning: { color: '#ff9800', icon: 'exclamation-circle', priority: 3 },
        info: { color: '#2196f3', icon: 'info-circle', priority: 2 },
        debug: { color: '#9c27b0', icon: 'bug', priority: 1 }
    };
    return levelInfo[level?.toLowerCase()] || levelInfo.info;
}

/**
 * Format log timestamp for display
 */
function formatLogTimestamp(timestamp) {
    try {
        const date = new Date(timestamp);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    } catch (error) {
        return timestamp;
    }
}

/**
 * Debounce function for search input
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Enhanced WebSocket setup for real-time updates (if supported)
 */
function setupWebSocketConnection() {
    if (!window.WebSocket) {
        console.log('WebSocket not supported, using polling for real-time updates');
        return false;
    }
    
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/admin/logs`;
        
        logsState.websocket = new WebSocket(wsUrl);
        
        logsState.websocket.onopen = () => {
            console.log('WebSocket connection established for real-time logs');
            updateRealTimeIndicator(true);
        };
        
        logsState.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'new_log' && data.log) {
                    // Add new log to the beginning
                    logsState.logs.unshift(data.log);
                    logsState.lastLogTimestamp = data.log.timestamp;
                    
                    // Apply filters and update display
                    applySearchFilter();
                    updateStatistics();
                    renderLogs();
                }
            } catch (error) {
                console.error('Error processing WebSocket message:', error);
            }
        };
        
        logsState.websocket.onclose = () => {
            console.log('WebSocket connection closed');
            logsState.websocket = null;
            updateRealTimeIndicator(false);
        };
        
        logsState.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateRealTimeIndicator(false);
        };
        
        return true;
    } catch (error) {
        console.error('Failed to setup WebSocket:', error);
        return false;
    }
}

/**
 * Enhanced search functionality with advanced options
 */
function setupAdvancedSearch() {
    // Create debounced search function
    const debouncedSearch = debounce(() => {
        logsState.searchTerm = logsElements.logSearchInput?.value || '';
        applySearchFilter();
        renderLogs();
    }, 300);
    
    // Set up real-time search
    logsElements.logSearchInput?.addEventListener('input', debouncedSearch);
    
    // Set up global search synchronization
    logsElements.globalSearchInput?.addEventListener('input', (e) => {
        if (logsElements.logSearchInput) {
            logsElements.logSearchInput.value = e.target.value;
            debouncedSearch();
        }
    });
    
    // Add search options (case sensitivity, regex, etc.)
    const searchOptionsHtml = `
        <div class="search-options mt-2" style="font-size: 0.875rem;">
            <div class="form-check form-check-inline">
                <input class="form-check-input" type="checkbox" id="case-sensitive-search">
                <label class="form-check-label" for="case-sensitive-search">Case sensitive</label>
            </div>
            <div class="form-check form-check-inline">
                <input class="form-check-input" type="checkbox" id="highlight-search" checked>
                <label class="form-check-label" for="highlight-search">Highlight matches</label>
            </div>
        </div>
    `;
    
    // Add search options to the search input container
    const searchContainer = logsElements.logSearchInput?.parentElement?.parentElement;
    if (searchContainer && !searchContainer.querySelector('.search-options')) {
        searchContainer.insertAdjacentHTML('beforeend', searchOptionsHtml);
        
        // Set up search option event listeners
        document.getElementById('case-sensitive-search')?.addEventListener('change', (e) => {
            logsState.caseSensitiveSearch = e.target.checked;
            if (logsState.searchTerm) {
                applySearchFilter();
                renderLogs();
            }
        });
        
        document.getElementById('highlight-search')?.addEventListener('change', (e) => {
            logsState.searchHighlightEnabled = e.target.checked;
            if (logsState.searchTerm) {
                renderLogs();
            }
        });
    }
}

/**
 * Enhanced keyboard shortcuts for log management
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Only handle shortcuts when not typing in input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        switch (e.key) {
            case 'r':
            case 'R':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    refreshLogs();
                }
                break;
            case 'f':
            case 'F':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    logsElements.logSearchInput?.focus();
                }
                break;
            case 'Escape':
                clearAllFilters();
                break;
            case 'Home':
                scrollToTop();
                break;
            case 'End':
                scrollToBottom();
                break;
        }
    });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initLogsManagement();
    setupAdvancedSearch();
    setupKeyboardShortcuts();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (logsState.realTimeInterval) {
        clearInterval(logsState.realTimeInterval);
    }
    if (logsState.websocket) {
        logsState.websocket.close();
    }
});

// Export functions for external use
window.logsManagement = {
    loadLogs,
    exportLogs,
    clearAllFilters,
    toggleRealTime,
    refreshLogs,
    getLogStatistics: () => logsState.statistics,
    getCurrentLogs: () => logsState.filteredLogs.length > 0 ? logsState.filteredLogs : logsState.logs
};