/**
 * Admin Dashboard - Settings Management
 * Handles settings configuration and management
 */

// DOM Elements
const settingsElements = {
    // Forms
    generalForm: document.getElementById('general-settings-form'),
    appearanceForm: document.getElementById('appearance-settings-form'),
    notificationsForm: document.getElementById('notifications-settings-form'),
    securityForm: document.getElementById('security-settings-form'),
    advancedForm: document.getElementById('advanced-settings-form'),
    
    // Search
    searchInput: document.getElementById('settings-search'),
    
    // Action buttons
    clearCacheBtn: document.getElementById('btn-clear-cache'),
    backupNowBtn: document.getElementById('btn-backup-now'),
    restoreBackupBtn: document.getElementById('btn-restore-backup'),
    resetSettingsBtn: document.getElementById('btn-reset-settings'),
    exportSettingsBtn: document.getElementById('btn-export-settings'),
    importSettingsBtn: document.getElementById('btn-import-settings'),
    exportSettingsCardBtn: document.getElementById('btn-export-settings-card'),
    importSettingsCardBtn: document.getElementById('btn-import-settings-card'),
    
    // Modal elements
    backupModal: document.getElementById('backup-modal'),
    restoreModal: document.getElementById('restore-modal'),
    resetModal: document.getElementById('reset-modal'),
    importModal: document.getElementById('import-modal'),
    confirmBackupBtn: document.getElementById('confirm-backup'),
    confirmRestoreBtn: document.getElementById('confirm-restore'),
    confirmResetBtn: document.getElementById('confirm-reset'),
    confirmImportBtn: document.getElementById('confirm-import'),
    backupFileInput: document.getElementById('backup-file'),
    settingsFileInput: document.getElementById('settings-file'),
    mergeSettingsCheckbox: document.getElementById('merge-settings'),
    confirmResetCheckbox: document.getElementById('confirm-reset-checkbox')
};

// Settings state
const settingsState = {
    general: {
        siteTitle: 'Admin Dashboard',
        siteDescription: 'Admin dashboard for managing support tickets and users',
        adminEmail: 'admin@example.com',
        timezone: 'UTC',
        dateFormat: 'MM/DD/YYYY'
    },
    appearance: {
        theme: 'light',
        primaryColor: '#0d6efd',
        sidebarPosition: 'left',
        fontSize: 'medium',
        showAnimations: true
    },
    notifications: {
        emailNotifications: true,
        notifyNewTicket: true,
        notifyTicketUpdate: true,
        notifyTicketComment: true,
        notifyUserRegister: false,
        notifySyncComplete: false,
        browserNotifications: true,
        notificationSound: 'default'
    },
    security: {
        sessionTimeout: 30,
        passwordPolicy: 'medium',
        forcePasswordChange: true,
        twoFactorAuth: false,
        logFailedAttempts: true,
        loginAttempts: 5
    },
    advanced: {
        logLevel: 'info',
        cacheLifetime: 60,
        enableApi: true,
        paginationLimit: 25,
        backupFrequency: 'weekly',
        maintenanceMode: false
    }
};

/**
 * Initialize settings management
 */
function initSettingsManagement() {
    // Load settings from API or localStorage
    loadSettings();
    
    // Set up event listeners
    setupSettingsEventListeners();
    
    // Set up real-time validation
    setupRealTimeValidation();
    
    // Initialize search functionality
    initializeSearch();
    
    // Set up keyboard shortcuts
    setupKeyboardShortcuts();
}

/**
 * Initialize search functionality
 */
function initializeSearch() {
    // Add debounced search
    let searchTimeout;
    if (settingsElements.searchInput) {
        settingsElements.searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(handleSettingsSearch, 300);
        });
        
        // Add search shortcuts
        settingsElements.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                settingsElements.searchInput.value = '';
                handleSettingsSearch();
            }
        });
    }
}

/**
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + S to save current tab
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            saveCurrentTabSettings();
        }
        
        // Ctrl/Cmd + E to export settings
        if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
            e.preventDefault();
            exportSettings();
        }
        
        // Ctrl/Cmd + F to focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault();
            if (settingsElements.searchInput) {
                settingsElements.searchInput.focus();
            }
        }
    });
}

/**
 * Save settings for currently active tab
 */
function saveCurrentTabSettings() {
    const activeTab = document.querySelector('#settings-tabs .nav-link.active');
    if (!activeTab) return;
    
    const tabId = activeTab.getAttribute('data-bs-target');
    
    switch (tabId) {
        case '#general':
            saveGeneralSettings();
            break;
        case '#appearance':
            saveAppearanceSettings();
            break;
        case '#notifications':
            saveNotificationSettings();
            break;
        case '#security':
            saveSecuritySettings();
            break;
        case '#advanced':
            saveAdvancedSettings();
            break;
    }
}

/**
 * Set up settings event listeners
 */
function setupSettingsEventListeners() {
    // General settings form
    if (settingsElements.generalForm) {
        settingsElements.generalForm.addEventListener('submit', (e) => {
            e.preventDefault();
            saveGeneralSettings();
        });
    }
    
    // Appearance settings form
    if (settingsElements.appearanceForm) {
        settingsElements.appearanceForm.addEventListener('submit', (e) => {
            e.preventDefault();
            saveAppearanceSettings();
        });
        
        // Theme change preview
        const themeSelect = document.getElementById('theme');
        if (themeSelect) {
            themeSelect.addEventListener('change', previewTheme);
        }
        
        // Color change preview
        const colorInput = document.getElementById('primary-color');
        if (colorInput) {
            colorInput.addEventListener('input', previewColor);
        }
    }
    
    // Notifications settings form
    if (settingsElements.notificationsForm) {
        settingsElements.notificationsForm.addEventListener('submit', (e) => {
            e.preventDefault();
            saveNotificationSettings();
        });
    }
    
    // Security settings form
    if (settingsElements.securityForm) {
        settingsElements.securityForm.addEventListener('submit', (e) => {
            e.preventDefault();
            saveSecuritySettings();
        });
    }
    
    // Advanced settings form
    if (settingsElements.advancedForm) {
        settingsElements.advancedForm.addEventListener('submit', (e) => {
            e.preventDefault();
            saveAdvancedSettings();
        });
    }
    
    // Clear cache button
    if (settingsElements.clearCacheBtn) {
        settingsElements.clearCacheBtn.addEventListener('click', clearCache);
    }
    
    // Backup now button
    if (settingsElements.backupNowBtn) {
        settingsElements.backupNowBtn.addEventListener('click', backupNow);
    }
    
    // Reset settings button
    if (settingsElements.resetSettingsBtn) {
        settingsElements.resetSettingsBtn.addEventListener('click', () => {
            const resetModal = new bootstrap.Modal(settingsElements.resetModal);
            resetModal.show();
        });
    }
    
    // Settings search
    if (settingsElements.searchInput) {
        settingsElements.searchInput.addEventListener('input', handleSettingsSearch);
    }
    
    // Restore backup button
    if (settingsElements.restoreBackupBtn) {
        settingsElements.restoreBackupBtn.addEventListener('click', () => {
            const restoreModal = new bootstrap.Modal(settingsElements.restoreModal);
            restoreModal.show();
        });
    }
    
    // Export settings buttons
    if (settingsElements.exportSettingsBtn) {
        settingsElements.exportSettingsBtn.addEventListener('click', exportSettings);
    }
    if (settingsElements.exportSettingsCardBtn) {
        settingsElements.exportSettingsCardBtn.addEventListener('click', exportSettings);
    }
    
    // Import settings buttons
    if (settingsElements.importSettingsBtn) {
        settingsElements.importSettingsBtn.addEventListener('click', () => {
            const importModal = new bootstrap.Modal(settingsElements.importModal);
            importModal.show();
        });
    }
    if (settingsElements.importSettingsCardBtn) {
        settingsElements.importSettingsCardBtn.addEventListener('click', () => {
            const importModal = new bootstrap.Modal(settingsElements.importModal);
            importModal.show();
        });
    }
    
    // Modal confirmation buttons
    if (settingsElements.confirmBackupBtn) {
        settingsElements.confirmBackupBtn.addEventListener('click', performBackup);
    }
    
    if (settingsElements.confirmRestoreBtn) {
        settingsElements.confirmRestoreBtn.addEventListener('click', performRestore);
    }
    
    if (settingsElements.confirmResetBtn) {
        settingsElements.confirmResetBtn.addEventListener('click', performReset);
    }
    
    if (settingsElements.confirmImportBtn) {
        settingsElements.confirmImportBtn.addEventListener('click', performImport);
    }
    
    // File input change handlers
    if (settingsElements.backupFileInput) {
        settingsElements.backupFileInput.addEventListener('change', (e) => {
            settingsElements.confirmRestoreBtn.disabled = !e.target.files.length;
        });
    }
    
    if (settingsElements.settingsFileInput) {
        settingsElements.settingsFileInput.addEventListener('change', (e) => {
            settingsElements.confirmImportBtn.disabled = !e.target.files.length;
        });
    }
    
    // Reset confirmation checkbox
    if (settingsElements.confirmResetCheckbox) {
        settingsElements.confirmResetCheckbox.addEventListener('change', (e) => {
            settingsElements.confirmResetBtn.disabled = !e.target.checked;
        });
    }
    
    // Update backup button to show modal
    if (settingsElements.backupNowBtn) {
        settingsElements.backupNowBtn.addEventListener('click', () => {
            const backupModal = new bootstrap.Modal(settingsElements.backupModal);
            backupModal.show();
        });
    }
}

/**
 * Load settings from API or localStorage
 */
function loadSettings() {
    // Try to load from localStorage first (for demo purposes)
    const savedSettings = localStorage.getItem('adminDashboardSettings');
    if (savedSettings) {
        try {
            const parsedSettings = JSON.parse(savedSettings);
            Object.assign(settingsState, parsedSettings);
        } catch (error) {
            console.error('Error parsing saved settings:', error);
        }
    }
    
    // In a real application, we would load from the API
    // api.getSettings()
    //     .then(response => {
    //         if (response.success) {
    //             Object.assign(settingsState, response.settings);
    //             updateSettingsForms();
    //         }
    //     })
    //     .catch(error => {
    //         console.error('Error loading settings:', error);
    //         showAlert('danger', 'Failed to load settings. Using defaults.');
    //     });
    
    // For demo, just update the forms with the current state
    updateSettingsForms();
    
    // Apply current settings
    applySettings();
}

/**
 * Update settings forms with current state
 */
function updateSettingsForms() {
    // General settings
    setFormValue('site-title', settingsState.general.siteTitle);
    setFormValue('site-description', settingsState.general.siteDescription);
    setFormValue('admin-email', settingsState.general.adminEmail);
    setFormValue('timezone', settingsState.general.timezone);
    setFormValue('date-format', settingsState.general.dateFormat);
    
    // Appearance settings
    setFormValue('theme', settingsState.appearance.theme);
    setFormValue('primary-color', settingsState.appearance.primaryColor);
    setFormValue('sidebar-position', settingsState.appearance.sidebarPosition);
    setFormValue('font-size', settingsState.appearance.fontSize);
    setFormValue('show-animations', settingsState.appearance.showAnimations);
    
    // Notifications settings
    setFormValue('email-notifications', settingsState.notifications.emailNotifications);
    setFormValue('notify-new-ticket', settingsState.notifications.notifyNewTicket);
    setFormValue('notify-ticket-update', settingsState.notifications.notifyTicketUpdate);
    setFormValue('notify-ticket-comment', settingsState.notifications.notifyTicketComment);
    setFormValue('notify-user-register', settingsState.notifications.notifyUserRegister);
    setFormValue('notify-sync-complete', settingsState.notifications.notifySyncComplete);
    setFormValue('browser-notifications', settingsState.notifications.browserNotifications);
    setFormValue('notification-sound', settingsState.notifications.notificationSound);
    
    // Security settings
    setFormValue('session-timeout', settingsState.security.sessionTimeout);
    setFormValue('password-policy', settingsState.security.passwordPolicy);
    setFormValue('force-password-change', settingsState.security.forcePasswordChange);
    setFormValue('two-factor-auth', settingsState.security.twoFactorAuth);
    setFormValue('log-failed-attempts', settingsState.security.logFailedAttempts);
    setFormValue('login-attempts', settingsState.security.loginAttempts);
    
    // Advanced settings
    setFormValue('log-level', settingsState.advanced.logLevel);
    setFormValue('cache-lifetime', settingsState.advanced.cacheLifetime);
    setFormValue('enable-api', settingsState.advanced.enableApi);
    setFormValue('pagination-limit', settingsState.advanced.paginationLimit);
    setFormValue('backup-frequency', settingsState.advanced.backupFrequency);
    setFormValue('maintenance-mode', settingsState.advanced.maintenanceMode);
}

/**
 * Set form value helper
 * @param {string} id - Element ID
 * @param {any} value - Value to set
 */
function setFormValue(id, value) {
    const element = document.getElementById(id);
    if (!element) return;
    
    if (element.type === 'checkbox') {
        element.checked = value;
    } else {
        element.value = value;
    }
}

/**
 * Get form value helper
 * @param {string} id - Element ID
 * @returns {any} - Form value
 */
function getFormValue(id) {
    const element = document.getElementById(id);
    if (!element) return null;
    
    if (element.type === 'checkbox') {
        return element.checked;
    } else if (element.type === 'number') {
        return parseInt(element.value, 10);
    } else {
        return element.value;
    }
}

/**
 * Apply current settings
 */
function applySettings() {
    // Apply theme
    applyTheme(settingsState.appearance.theme);
    
    // Apply primary color
    applyPrimaryColor(settingsState.appearance.primaryColor);
    
    // Apply font size
    applyFontSize(settingsState.appearance.fontSize);
    
    // Apply sidebar position
    applySidebarPosition(settingsState.appearance.sidebarPosition);
    
    // Apply animations
    applyAnimations(settingsState.appearance.showAnimations);
    
    // Update document title
    document.title = `${settingsState.general.siteTitle} - Settings`;
}

/**
 * Apply theme
 * @param {string} theme - Theme name
 */
function applyTheme(theme) {
    const body = document.body;
    
    // Remove existing theme classes
    body.classList.remove('theme-light', 'theme-dark');
    
    // Add new theme class
    if (theme === 'dark') {
        body.classList.add('theme-dark');
    } else if (theme === 'auto') {
        // Check system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            body.classList.add('theme-dark');
        } else {
            body.classList.add('theme-light');
        }
    } else {
        // Default to light
        body.classList.add('theme-light');
    }
}

/**
 * Apply primary color
 * @param {string} color - Color hex code
 */
function applyPrimaryColor(color) {
    // Create or update CSS variable
    document.documentElement.style.setProperty('--primary-color', color);
}

/**
 * Apply font size
 * @param {string} size - Font size (small, medium, large)
 */
function applyFontSize(size) {
    const html = document.documentElement;
    
    // Remove existing font size classes
    html.classList.remove('font-small', 'font-medium', 'font-large');
    
    // Add new font size class
    html.classList.add(`font-${size}`);
}

/**
 * Apply sidebar position
 * @param {string} position - Sidebar position (left, right)
 */
function applySidebarPosition(position) {
    const container = document.querySelector('.dashboard-container');
    if (!container) return;
    
    // Remove existing position classes
    container.classList.remove('sidebar-left', 'sidebar-right');
    
    // Add new position class
    container.classList.add(`sidebar-${position}`);
}

/**
 * Apply animations setting
 * @param {boolean} enabled - Whether animations are enabled
 */
function applyAnimations(enabled) {
    const body = document.body;
    
    if (enabled) {
        body.classList.remove('no-animations');
    } else {
        body.classList.add('no-animations');
    }
}

/**
 * Preview theme change
 */
function previewTheme() {
    const theme = document.getElementById('theme').value;
    applyTheme(theme);
}

/**
 * Preview color change
 */
function previewColor() {
    const color = document.getElementById('primary-color').value;
    applyPrimaryColor(color);
}

/**
 * Validate form inputs
 * @param {string} formType - Type of form to validate
 * @returns {boolean} - Whether form is valid
 */
function validateForm(formType) {
    let isValid = true;
    const errors = [];
    
    // Clear previous validation states
    clearValidationErrors(formType);
    
    switch (formType) {
        case 'general':
            const siteTitle = getFormValue('site-title');
            const siteDescription = getFormValue('site-description');
            const adminEmail = getFormValue('admin-email');
            
            if (!siteTitle || siteTitle.trim().length < 3) {
                errors.push('Site title must be at least 3 characters long');
                addValidationError('site-title', 'Site title is too short');
                isValid = false;
            }
            
            if (siteDescription && siteDescription.length > 500) {
                errors.push('Site description must be less than 500 characters');
                addValidationError('site-description', 'Description is too long');
                isValid = false;
            }
            
            if (!adminEmail || !isValidEmail(adminEmail)) {
                errors.push('Please enter a valid admin email address');
                addValidationError('admin-email', 'Invalid email format');
                isValid = false;
            }
            break;
            
        case 'security':
            const sessionTimeout = getFormValue('session-timeout');
            const loginAttempts = getFormValue('login-attempts');
            
            if (sessionTimeout < 5 || sessionTimeout > 1440) {
                errors.push('Session timeout must be between 5 and 1440 minutes');
                addValidationError('session-timeout', 'Must be between 5 and 1440 minutes');
                isValid = false;
            }
            
            if (loginAttempts < 1 || loginAttempts > 10) {
                errors.push('Login attempts must be between 1 and 10');
                addValidationError('login-attempts', 'Must be between 1 and 10');
                isValid = false;
            }
            break;
            
        case 'advanced':
            const cacheLifetime = getFormValue('cache-lifetime');
            const paginationLimit = getFormValue('pagination-limit');
            
            if (cacheLifetime < 0 || cacheLifetime > 1440) {
                errors.push('Cache lifetime must be between 0 and 1440 minutes');
                addValidationError('cache-lifetime', 'Must be between 0 and 1440 minutes');
                isValid = false;
            }
            
            if (paginationLimit < 5 || paginationLimit > 100) {
                errors.push('Items per page must be between 5 and 100');
                addValidationError('pagination-limit', 'Must be between 5 and 100');
                isValid = false;
            }
            break;
    }
    
    if (!isValid) {
        showAlert('danger', 'Please fix the validation errors below');
    }
    
    return isValid;
}

/**
 * Add validation error to form field
 * @param {string} fieldId - Field ID
 * @param {string} message - Error message
 */
function addValidationError(fieldId, message) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    field.classList.add('is-invalid');
    
    // Remove existing feedback
    const existingFeedback = field.parentNode.querySelector('.invalid-feedback');
    if (existingFeedback) {
        existingFeedback.remove();
    }
    
    // Add new feedback
    const feedback = document.createElement('div');
    feedback.className = 'invalid-feedback';
    feedback.textContent = message;
    field.parentNode.appendChild(feedback);
}

/**
 * Clear validation errors for form
 * @param {string} formType - Form type
 */
function clearValidationErrors(formType) {
    const formMap = {
        'general': 'general-settings-form',
        'appearance': 'appearance-settings-form',
        'notifications': 'notifications-settings-form',
        'security': 'security-settings-form',
        'advanced': 'advanced-settings-form'
    };
    
    const formId = formMap[formType];
    if (!formId) return;
    
    const form = document.getElementById(formId);
    if (!form) return;
    
    // Remove validation classes
    const invalidFields = form.querySelectorAll('.is-invalid');
    invalidFields.forEach(field => {
        field.classList.remove('is-invalid');
    });
    
    // Remove feedback messages
    const feedbacks = form.querySelectorAll('.invalid-feedback');
    feedbacks.forEach(feedback => {
        feedback.remove();
    });
}

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} - Whether email is valid
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Save general settings
 */
function saveGeneralSettings() {
    if (!validateForm('general')) {
        return;
    }
    
    // Show loading state
    const submitBtn = settingsElements.generalForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    showLoadingState(submitBtn, 'Saving...');
    
    // Update settings state
    settingsState.general = {
        siteTitle: getFormValue('site-title'),
        siteDescription: getFormValue('site-description'),
        adminEmail: getFormValue('admin-email'),
        timezone: getFormValue('timezone'),
        dateFormat: getFormValue('date-format')
    };
    
    // Simulate API delay
    setTimeout(() => {
        try {
            // Save settings
            saveSettings('general');
            
            // Apply settings
            applySettings();
            
            // Show success feedback
            showSuccessFeedback(submitBtn, 'Saved!');
            
            // Reset button state after delay
            setTimeout(() => {
                resetButtonState(submitBtn, originalText);
            }, 2000);
            
        } catch (error) {
            console.error('Error saving general settings:', error);
            showAlert('danger', 'Failed to save general settings. Please try again.');
            resetButtonState(submitBtn, originalText);
        }
    }, 1000);
}

/**
 * Save appearance settings
 */
function saveAppearanceSettings() {
    // Show loading state
    const submitBtn = settingsElements.appearanceForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    showLoadingState(submitBtn, 'Applying...');
    
    // Update settings state
    settingsState.appearance = {
        theme: getFormValue('theme'),
        primaryColor: getFormValue('primary-color'),
        sidebarPosition: getFormValue('sidebar-position'),
        fontSize: getFormValue('font-size'),
        showAnimations: getFormValue('show-animations')
    };
    
    // Simulate API delay
    setTimeout(() => {
        try {
            // Save settings
            saveSettings('appearance');
            
            // Apply settings
            applySettings();
            
            // Show success feedback
            showSuccessFeedback(submitBtn, 'Applied!');
            
            // Reset button state after delay
            setTimeout(() => {
                resetButtonState(submitBtn, originalText);
            }, 2000);
            
        } catch (error) {
            console.error('Error saving appearance settings:', error);
            showAlert('danger', 'Failed to save appearance settings. Please try again.');
            resetButtonState(submitBtn, originalText);
        }
    }, 800);
}

/**
 * Save notification settings
 */
function saveNotificationSettings() {
    // Show loading state
    const submitBtn = settingsElements.notificationsForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    showLoadingState(submitBtn, 'Saving...');
    
    // Update settings state
    settingsState.notifications = {
        emailNotifications: getFormValue('email-notifications'),
        notifyNewTicket: getFormValue('notify-new-ticket'),
        notifyTicketUpdate: getFormValue('notify-ticket-update'),
        notifyTicketComment: getFormValue('notify-ticket-comment'),
        notifyUserRegister: getFormValue('notify-user-register'),
        notifySyncComplete: getFormValue('notify-sync-complete'),
        browserNotifications: getFormValue('browser-notifications'),
        notificationSound: getFormValue('notification-sound')
    };
    
    // Simulate API delay
    setTimeout(() => {
        try {
            // Save settings
            saveSettings('notifications');
            
            // Request browser notification permission if enabled
            if (settingsState.notifications.browserNotifications) {
                requestNotificationPermission();
            }
            
            // Show success feedback
            showSuccessFeedback(submitBtn, 'Saved!');
            
            // Reset button state after delay
            setTimeout(() => {
                resetButtonState(submitBtn, originalText);
            }, 2000);
            
        } catch (error) {
            console.error('Error saving notification settings:', error);
            showAlert('danger', 'Failed to save notification settings. Please try again.');
            resetButtonState(submitBtn, originalText);
        }
    }, 1000);
}

/**
 * Save security settings
 */
function saveSecuritySettings() {
    if (!validateForm('security')) {
        return;
    }
    
    // Show loading state
    const submitBtn = settingsElements.securityForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
    
    // Update settings state
    settingsState.security = {
        sessionTimeout: getFormValue('session-timeout'),
        passwordPolicy: getFormValue('password-policy'),
        forcePasswordChange: getFormValue('force-password-change'),
        twoFactorAuth: getFormValue('two-factor-auth'),
        logFailedAttempts: getFormValue('log-failed-attempts'),
        loginAttempts: getFormValue('login-attempts')
    };
    
    // Simulate API delay
    setTimeout(() => {
        // Save settings
        saveSettings('security');
        
        // Update session timeout
        updateSessionTimeout();
        
        // Reset button state
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }, 1000);
}

/**
 * Save advanced settings
 */
function saveAdvancedSettings() {
    if (!validateForm('advanced')) {
        return;
    }
    
    // Show loading state
    const submitBtn = settingsElements.advancedForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
    
    // Update settings state
    settingsState.advanced = {
        logLevel: getFormValue('log-level'),
        cacheLifetime: getFormValue('cache-lifetime'),
        enableApi: getFormValue('enable-api'),
        paginationLimit: getFormValue('pagination-limit'),
        backupFrequency: getFormValue('backup-frequency'),
        maintenanceMode: getFormValue('maintenance-mode')
    };
    
    // Simulate API delay
    setTimeout(() => {
        // Save settings
        saveSettings('advanced');
        
        // Check if maintenance mode is enabled
        if (settingsState.advanced.maintenanceMode) {
            showMaintenanceModeWarning();
        }
        
        // Reset button state
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }, 1000);
}

/**
 * Save settings to API and localStorage
 * @param {string} section - Settings section
 */
function saveSettings(section) {
    // Save to localStorage (for demo purposes)
    localStorage.setItem('adminDashboardSettings', JSON.stringify(settingsState));
    
    // In a real application, we would save to the API
    // api.saveSettings(settingsState)
    //     .then(response => {
    //         if (response.success) {
    //             showAlert('success', `${section.charAt(0).toUpperCase() + section.slice(1)} settings saved successfully!`);
    //         } else {
    //             showAlert('danger', `Failed to save ${section} settings: ${response.message || 'Unknown error'}`);
    //         }
    //     })
    //     .catch(error => {
    //         console.error(`Error saving ${section} settings:`, error);
    //         showAlert('danger', `An error occurred while saving ${section} settings. Please try again.`);
    //     });
    
    // For demo, just show success message
    showAlert('success', `${section.charAt(0).toUpperCase() + section.slice(1)} settings saved successfully!`);
}

/**
 * Handle settings search
 */
function handleSettingsSearch() {
    const searchTerm = settingsElements.searchInput.value.toLowerCase().trim();
    const tabPanes = document.querySelectorAll('.tab-pane');
    const tabs = document.querySelectorAll('#settings-tabs .nav-link');
    
    // Clear previous highlights
    clearSearchHighlights();
    
    if (!searchTerm) {
        // Show all tabs and content
        tabs.forEach(tab => {
            tab.style.display = 'block';
            tab.classList.remove('search-match');
        });
        tabPanes.forEach(pane => {
            const formGroups = pane.querySelectorAll('.mb-3, .form-check, .card');
            formGroups.forEach(group => {
                group.style.display = 'block';
            });
        });
        return;
    }
    
    let hasVisibleContent = false;
    let matchingTabs = [];
    
    // Search through each tab pane
    tabPanes.forEach((pane, index) => {
        const formGroups = pane.querySelectorAll('.mb-3, .form-check, .card');
        let paneHasVisible = false;
        
        formGroups.forEach(group => {
            const labels = group.querySelectorAll('label, h6, p, .form-text');
            let groupText = '';
            labels.forEach(label => {
                groupText += ' ' + label.textContent.toLowerCase();
            });
            
            if (groupText.includes(searchTerm)) {
                group.style.display = 'block';
                paneHasVisible = true;
                hasVisibleContent = true;
                
                // Highlight matching text
                highlightSearchTerm(group, searchTerm);
            } else {
                group.style.display = 'none';
            }
        });
        
        // Show/hide corresponding tab
        const tab = tabs[index];
        if (tab) {
            if (paneHasVisible) {
                tab.style.display = 'block';
                tab.classList.add('search-match');
                matchingTabs.push(tab.textContent.trim());
            } else {
                tab.style.display = 'none';
                tab.classList.remove('search-match');
            }
        }
    });
    
    // Show message if no results found
    if (!hasVisibleContent) {
        showAlert('info', `No settings found matching "${searchTerm}". Try different keywords.`);
    } else {
        // Auto-switch to first matching tab if current tab is hidden
        const activeTab = document.querySelector('#settings-tabs .nav-link.active');
        if (activeTab && activeTab.style.display === 'none') {
            const firstVisibleTab = document.querySelector('#settings-tabs .nav-link[style*="block"]');
            if (firstVisibleTab) {
                firstVisibleTab.click();
            }
        }
    }
}

/**
 * Highlight search terms in elements
 * @param {Element} element - Element to search in
 * @param {string} searchTerm - Term to highlight
 */
function highlightSearchTerm(element, searchTerm) {
    const labels = element.querySelectorAll('label, h6, p:not(.text-muted), .form-text');
    labels.forEach(label => {
        const text = label.textContent;
        const regex = new RegExp(`(${searchTerm})`, 'gi');
        if (regex.test(text)) {
            label.innerHTML = text.replace(regex, '<span class="search-highlight">$1</span>');
        }
    });
}

/**
 * Clear search highlights
 */
function clearSearchHighlights() {
    const highlights = document.querySelectorAll('.search-highlight');
    highlights.forEach(highlight => {
        const parent = highlight.parentNode;
        parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
        parent.normalize();
    });
}

/**
 * Show loading state on button
 * @param {Element} button - Button element
 * @param {string} text - Loading text
 */
function showLoadingState(button, text = 'Loading...') {
    button.disabled = true;
    button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${text}`;
}

/**
 * Show success feedback on button
 * @param {Element} button - Button element
 * @param {string} text - Success text
 */
function showSuccessFeedback(button, text = 'Success!') {
    button.disabled = false;
    button.innerHTML = `<i class="bi bi-check-circle me-1"></i> ${text}`;
    button.classList.add('btn-success');
    button.classList.remove('btn-primary', 'btn-info', 'btn-warning', 'btn-danger');
}

/**
 * Reset button to original state
 * @param {Element} button - Button element
 * @param {string} originalText - Original button text
 */
function resetButtonState(button, originalText) {
    button.disabled = false;
    button.innerHTML = originalText;
    button.classList.remove('btn-success');
    button.classList.add('btn-primary');
}

/**
 * Add real-time form validation
 */
function setupRealTimeValidation() {
    // General form validation
    const siteTitle = document.getElementById('site-title');
    const adminEmail = document.getElementById('admin-email');
    
    if (siteTitle) {
        siteTitle.addEventListener('input', () => {
            validateField('site-title', (value) => {
                if (!value || value.trim().length < 3) {
                    return 'Site title must be at least 3 characters long';
                }
                return null;
            });
        });
    }
    
    if (adminEmail) {
        adminEmail.addEventListener('input', () => {
            validateField('admin-email', (value) => {
                if (!value || !isValidEmail(value)) {
                    return 'Please enter a valid email address';
                }
                return null;
            });
        });
    }
    
    // Security form validation
    const sessionTimeout = document.getElementById('session-timeout');
    const loginAttempts = document.getElementById('login-attempts');
    
    if (sessionTimeout) {
        sessionTimeout.addEventListener('input', () => {
            validateField('session-timeout', (value) => {
                const num = parseInt(value, 10);
                if (num < 5 || num > 1440) {
                    return 'Must be between 5 and 1440 minutes';
                }
                return null;
            });
        });
    }
    
    if (loginAttempts) {
        loginAttempts.addEventListener('input', () => {
            validateField('login-attempts', (value) => {
                const num = parseInt(value, 10);
                if (num < 1 || num > 10) {
                    return 'Must be between 1 and 10';
                }
                return null;
            });
        });
    }
}

/**
 * Validate individual field
 * @param {string} fieldId - Field ID
 * @param {Function} validator - Validation function
 */
function validateField(fieldId, validator) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    const value = field.value;
    const error = validator(value);
    
    // Remove existing validation state
    field.classList.remove('is-valid', 'is-invalid');
    const existingFeedback = field.parentNode.querySelector('.invalid-feedback, .valid-feedback');
    if (existingFeedback) {
        existingFeedback.remove();
    }
    
    if (error) {
        field.classList.add('is-invalid');
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        feedback.textContent = error;
        field.parentNode.appendChild(feedback);
    } else if (value) {
        field.classList.add('is-valid');
        const feedback = document.createElement('div');
        feedback.className = 'valid-feedback';
        feedback.textContent = 'Looks good!';
        field.parentNode.appendChild(feedback);
    }
}

/**
 * Export settings
 */
function exportSettings() {
    const exportData = {
        timestamp: new Date().toISOString(),
        version: '1.0',
        exportedBy: 'Admin Dashboard',
        settings: settingsState
    };
    
    const dataStr = JSON.stringify(exportData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `admin-dashboard-settings-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    
    showAlert('success', 'Settings exported successfully!');
}

/**
 * Perform import settings
 */
function performImport() {
    const file = settingsElements.settingsFileInput.files[0];
    if (!file) {
        showAlert('danger', 'Please select a settings file to import.');
        return;
    }
    
    // Show loading state
    settingsElements.confirmImportBtn.disabled = true;
    settingsElements.confirmImportBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Importing...';
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const importData = JSON.parse(e.target.result);
            
            // Validate import data structure
            if (!importData.settings) {
                throw new Error('Invalid settings file format - missing settings data');
            }
            
            if (!importData.version) {
                throw new Error('Invalid settings file format - missing version information');
            }
            
            const mergeSettings = settingsElements.mergeSettingsCheckbox.checked;
            
            if (mergeSettings) {
                // Merge with existing settings
                Object.keys(importData.settings).forEach(section => {
                    if (settingsState[section]) {
                        Object.assign(settingsState[section], importData.settings[section]);
                    } else {
                        settingsState[section] = importData.settings[section];
                    }
                });
            } else {
                // Replace all settings
                Object.assign(settingsState, importData.settings);
            }
            
            // Update forms with imported settings
            updateSettingsForms();
            
            // Apply imported settings
            applySettings();
            
            // Save to localStorage
            localStorage.setItem('adminDashboardSettings', JSON.stringify(settingsState));
            
            showAlert('success', `Settings imported successfully! ${mergeSettings ? 'Merged with existing settings.' : 'All settings replaced.'}`);
            
            // Close modal
            bootstrap.Modal.getInstance(settingsElements.importModal).hide();
            
        } catch (error) {
            console.error('Error importing settings:', error);
            showAlert('danger', `Failed to import settings: ${error.message}`);
        } finally {
            // Reset button state
            settingsElements.confirmImportBtn.disabled = false;
            settingsElements.confirmImportBtn.innerHTML = '<i class="bi bi-upload me-2"></i>Import Settings';
        }
    };
    
    reader.onerror = function() {
        showAlert('danger', 'Error reading the settings file. Please try again.');
        settingsElements.confirmImportBtn.disabled = false;
        settingsElements.confirmImportBtn.innerHTML = '<i class="bi bi-upload me-2"></i>Import Settings';
    };
    
    reader.readAsText(file);
}

/**
 * Perform backup
 */
function performBackup() {
    // Show loading state
    settingsElements.confirmBackupBtn.disabled = true;
    settingsElements.confirmBackupBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Creating...';
    
    // In a real application, we would call the API
    // api.createBackup()
    //     .then(response => {
    //         if (response.success) {
    //             // Trigger download
    //             const link = document.createElement('a');
    //             link.href = response.downloadUrl;
    //             link.download = response.filename;
    //             link.click();
    //             
    //             showAlert('success', 'Database backup created and downloaded successfully!');
    //         } else {
    //             showAlert('danger', `Failed to create backup: ${response.message || 'Unknown error'}`);
    //         }
    //     })
    //     .catch(error => {
    //         console.error('Error creating backup:', error);
    //         showAlert('danger', 'An error occurred while creating backup. Please try again.');
    //     })
    //     .finally(() => {
    //         // Reset button state and close modal
    //         settingsElements.confirmBackupBtn.disabled = false;
    //         settingsElements.confirmBackupBtn.innerHTML = '<i class="bi bi-download me-2"></i>Create Backup';
    //         bootstrap.Modal.getInstance(settingsElements.backupModal).hide();
    //     });
    
    // For demo, simulate API call with timeout
    setTimeout(() => {
        // Create a mock backup file
        const backupData = {
            timestamp: new Date().toISOString(),
            version: '1.0',
            database: 'mock_database_backup',
            settings: settingsState
        };
        
        const dataStr = JSON.stringify(backupData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `database-backup-${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        
        showAlert('success', 'Database backup created and downloaded successfully!');
        
        // Reset button state and close modal
        settingsElements.confirmBackupBtn.disabled = false;
        settingsElements.confirmBackupBtn.innerHTML = '<i class="bi bi-download me-2"></i>Create Backup';
        bootstrap.Modal.getInstance(settingsElements.backupModal).hide();
    }, 2000);
}

/**
 * Perform restore
 */
function performRestore() {
    const file = settingsElements.backupFileInput.files[0];
    if (!file) {
        showAlert('danger', 'Please select a backup file to restore.');
        return;
    }
    
    // Show loading state
    settingsElements.confirmRestoreBtn.disabled = true;
    settingsElements.confirmRestoreBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Restoring...';
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const backupData = JSON.parse(e.target.result);
            
            // Validate backup data structure
            if (!backupData.settings) {
                throw new Error('Invalid backup file format');
            }
            
            // In a real application, we would send this to the API
            // api.restoreBackup(backupData)
            //     .then(response => {
            //         if (response.success) {
            //             showAlert('success', 'Database restored successfully! Please refresh the page.');
            //         } else {
            //             showAlert('danger', `Failed to restore backup: ${response.message || 'Unknown error'}`);
            //         }
            //     })
            //     .catch(error => {
            //         console.error('Error restoring backup:', error);
            //         showAlert('danger', 'An error occurred while restoring backup. Please try again.');
            //     })
            //     .finally(() => {
            //         // Reset button state and close modal
            //         settingsElements.confirmRestoreBtn.disabled = false;
            //         settingsElements.confirmRestoreBtn.innerHTML = '<i class="bi bi-upload me-2"></i>Restore Backup';
            //         bootstrap.Modal.getInstance(settingsElements.restoreModal).hide();
            //     });
            
            // For demo, simulate restore
            setTimeout(() => {
                // Restore settings from backup
                Object.assign(settingsState, backupData.settings);
                updateSettingsForms();
                applySettings();
                
                showAlert('success', 'Settings restored successfully from backup!');
                
                // Reset button state and close modal
                settingsElements.confirmRestoreBtn.disabled = false;
                settingsElements.confirmRestoreBtn.innerHTML = '<i class="bi bi-upload me-2"></i>Restore Backup';
                bootstrap.Modal.getInstance(settingsElements.restoreModal).hide();
            }, 1500);
            
        } catch (error) {
            console.error('Error parsing backup file:', error);
            showAlert('danger', 'Invalid backup file format. Please select a valid backup file.');
            
            // Reset button state
            settingsElements.confirmRestoreBtn.disabled = false;
            settingsElements.confirmRestoreBtn.innerHTML = '<i class="bi bi-upload me-2"></i>Restore Backup';
        }
    };
    
    reader.readAsText(file);
}

/**
 * Perform reset
 */
function performReset() {
    // Show loading state
    settingsElements.confirmResetBtn.disabled = true;
    settingsElements.confirmResetBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Resetting...';
    
    // In a real application, we would call the API
    // api.resetSettings()
    //     .then(response => {
    //         if (response.success) {
    //             // Reset local settings state
    //             settingsState = response.settings;
    //             
    //             // Update forms
    //             updateSettingsForms();
    //             
    //             // Apply settings
    //             applySettings();
    //             
    //             showAlert('success', 'Settings reset to default values successfully!');
    //         } else {
    //             showAlert('danger', `Failed to reset settings: ${response.message || 'Unknown error'}`);
    //         }
    //     })
    //     .catch(error => {
    //         console.error('Error resetting settings:', error);
    //         showAlert('danger', 'An error occurred while resetting settings. Please try again.');
    //     })
    //     .finally(() => {
    //         // Reset button state and close modal
    //         settingsElements.confirmResetBtn.disabled = false;
    //         settingsElements.confirmResetBtn.innerHTML = '<i class="bi bi-arrow-counterclockwise me-2"></i>Reset to Default';
    //         bootstrap.Modal.getInstance(settingsElements.resetModal).hide();
    //     });
    
    // For demo, simulate API call with timeout
    setTimeout(() => {
        // Reset local settings
        localStorage.removeItem('adminDashboardSettings');
        
        // Reload page to reset all settings
        location.reload();
    }, 1500);
}

/**
 * Clear cache
 */
function clearCache() {
    // Show loading state
    settingsElements.clearCacheBtn.disabled = true;
    settingsElements.clearCacheBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Clearing...';
    
    // In a real application, we would call the API
    // api.clearCache()
    //     .then(response => {
    //         if (response.success) {
    //             showAlert('success', 'Cache cleared successfully!');
    //         } else {
    //             showAlert('danger', `Failed to clear cache: ${response.message || 'Unknown error'}`);
    //         }
    //     })
    //     .catch(error => {
    //         console.error('Error clearing cache:', error);
    //         showAlert('danger', 'An error occurred while clearing cache. Please try again.');
    //     })
    //     .finally(() => {
    //         // Reset button state
    //         settingsElements.clearCacheBtn.disabled = false;
    //         settingsElements.clearCacheBtn.innerHTML = '<i class="bi bi-trash me-2"></i> Clear Cache';
    //     });
    
    // For demo, simulate API call with timeout
    setTimeout(() => {
        showAlert('success', 'Cache cleared successfully!');
        
        // Reset button state
        settingsElements.clearCacheBtn.disabled = false;
        settingsElements.clearCacheBtn.innerHTML = '<i class="bi bi-trash me-2"></i> Clear Cache';
    }, 1500);
}





/**
 * Request notification permission
 */
function requestNotificationPermission() {
    if (!('Notification' in window)) {
        console.warn('This browser does not support desktop notifications');
        return;
    }
    
    if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
        Notification.requestPermission();
    }
}

/**
 * Update session timeout
 */
function updateSessionTimeout() {
    // In a real application, we would update the session timeout
    // For demo, just log the new timeout
    console.log(`Session timeout updated to ${settingsState.security.sessionTimeout} minutes`);
}

/**
 * Show maintenance mode warning
 */
function showMaintenanceModeWarning() {
    showAlert('warning', 'Maintenance mode is enabled. The system will be inaccessible to regular users.');
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

// Initialize settings management when the DOM is loaded
document.addEventListener('DOMContentLoaded', initSettingsManagement);
/**
 
* Request notification permission
 */
function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                showAlert('success', 'Browser notifications enabled successfully!');
            } else {
                showAlert('warning', 'Browser notifications permission denied. You can enable it in your browser settings.');
            }
        });
    }
}

/**
 * Update session timeout
 */
function updateSessionTimeout() {
    // In a real application, this would update the session timeout on the server
    console.log('Session timeout updated to:', settingsState.security.sessionTimeout, 'minutes');
}

/**
 * Show maintenance mode warning
 */
function showMaintenanceModeWarning() {
    showAlert('warning', 'Maintenance mode is now enabled. Users will see a maintenance message when accessing the site.');
}

/**
 * Clear cache
 */
function clearCache() {
    // Show loading state
    const btn = settingsElements.clearCacheBtn;
    const originalText = btn.innerHTML;
    showLoadingState(btn, 'Clearing...');
    
    // Simulate API call
    setTimeout(() => {
        try {
            // Clear localStorage cache
            const keysToKeep = ['adminDashboardSettings'];
            const allKeys = Object.keys(localStorage);
            allKeys.forEach(key => {
                if (!keysToKeep.includes(key)) {
                    localStorage.removeItem(key);
                }
            });
            
            showAlert('success', 'Cache cleared successfully!');
            showSuccessFeedback(btn, 'Cleared!');
            
            setTimeout(() => {
                resetButtonState(btn, originalText);
            }, 2000);
            
        } catch (error) {
            console.error('Error clearing cache:', error);
            showAlert('danger', 'Failed to clear cache. Please try again.');
            resetButtonState(btn, originalText);
        }
    }, 1500);
}

/**
 * Perform reset to default settings
 */
function performReset() {
    // Show loading state
    const btn = settingsElements.confirmResetBtn;
    const originalText = btn.innerHTML;
    showLoadingState(btn, 'Resetting...');
    
    setTimeout(() => {
        try {
            // Reset to default settings
            Object.assign(settingsState, {
                general: {
                    siteTitle: 'Admin Dashboard',
                    siteDescription: 'Admin dashboard for managing support tickets and users',
                    adminEmail: 'admin@example.com',
                    timezone: 'UTC',
                    dateFormat: 'MM/DD/YYYY'
                },
                appearance: {
                    theme: 'light',
                    primaryColor: '#0d6efd',
                    sidebarPosition: 'left',
                    fontSize: 'medium',
                    showAnimations: true
                },
                notifications: {
                    emailNotifications: true,
                    notifyNewTicket: true,
                    notifyTicketUpdate: true,
                    notifyTicketComment: true,
                    notifyUserRegister: false,
                    notifySyncComplete: false,
                    browserNotifications: true,
                    notificationSound: 'default'
                },
                security: {
                    sessionTimeout: 30,
                    passwordPolicy: 'medium',
                    forcePasswordChange: true,
                    twoFactorAuth: false,
                    logFailedAttempts: true,
                    loginAttempts: 5
                },
                advanced: {
                    logLevel: 'info',
                    cacheLifetime: 60,
                    enableApi: true,
                    paginationLimit: 25,
                    backupFrequency: 'weekly',
                    maintenanceMode: false
                }
            });
            
            // Update forms and apply settings
            updateSettingsForms();
            applySettings();
            
            // Save to localStorage
            localStorage.setItem('adminDashboardSettings', JSON.stringify(settingsState));
            
            showAlert('success', 'All settings have been reset to default values!');
            
            // Close modal
            bootstrap.Modal.getInstance(settingsElements.resetModal).hide();
            
            // Reset checkbox
            settingsElements.confirmResetCheckbox.checked = false;
            
        } catch (error) {
            console.error('Error resetting settings:', error);
            showAlert('danger', 'Failed to reset settings. Please try again.');
        } finally {
            resetButtonState(btn, originalText);
        }
    }, 2000);
}

// Initialize settings management when DOM is loaded
document.addEventListener('DOMContentLoaded', initSettingsManagement);