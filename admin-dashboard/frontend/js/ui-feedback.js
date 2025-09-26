/**
 * UI Feedback System
 * Provides consistent loading states, error handling, and user feedback
 */

class UIFeedback {
    constructor() {
        this.toastContainer = null;
        this.init();
    }

    /**
     * Initialize the UI feedback system
     */
    init() {
        this.createToastContainer();
        this.setupGlobalErrorHandler();
    }

    /**
     * Create toast container if it doesn't exist
     */
    createToastContainer() {
        if (!document.querySelector('.toast-container')) {
            const container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        this.toastContainer = document.querySelector('.toast-container');
    }

    /**
     * Setup global error handler for unhandled errors
     */
    setupGlobalErrorHandler() {
        // Log errors to console but don't show user notifications for minor issues
        window.addEventListener('error', (event) => {
            console.error('Global error:', event.error);
            // Removed automatic error notifications to prevent false positives
        });

        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled promise rejection:', event.reason);
            // Removed automatic error notifications to prevent false positives
        });
    }

    /**
     * Show loading state on an element
     * @param {string|HTMLElement} element - Element selector or element
     * @param {string} message - Optional loading message
     */
    showLoading(element, message = 'Loading...') {
        const el = typeof element === 'string' ? document.querySelector(element) : element;
        if (!el) return;

        // Add position relative if not already positioned
        if (getComputedStyle(el).position === 'static') {
            el.style.position = 'relative';
        }

        // Remove existing loading overlay
        this.hideLoading(el);

        // Create loading overlay
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="d-flex flex-column align-items-center">
                <div class="loading-spinner mb-2"></div>
                <div class="text-muted">${message}</div>
            </div>
        `;
        
        el.appendChild(overlay);
    }

    /**
     * Hide loading state from an element
     * @param {string|HTMLElement} element - Element selector or element
     */
    hideLoading(element) {
        const el = typeof element === 'string' ? document.querySelector(element) : element;
        if (!el) return;

        const overlay = el.querySelector('.loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    /**
     * Show loading state on a button
     * @param {string|HTMLElement} button - Button selector or element
     * @param {string} text - Optional loading text
     */
    showButtonLoading(button, text = null) {
        const btn = typeof button === 'string' ? document.querySelector(button) : button;
        if (!btn) return;

        btn.disabled = true;
        btn.classList.add('loading');
        
        if (text) {
            btn.dataset.originalText = btn.textContent;
            btn.textContent = text;
        }
    }

    /**
     * Hide loading state from a button
     * @param {string|HTMLElement} button - Button selector or element
     */
    hideButtonLoading(button) {
        const btn = typeof button === 'string' ? document.querySelector(button) : button;
        if (!btn) return;

        btn.disabled = false;
        btn.classList.remove('loading');
        
        if (btn.dataset.originalText) {
            btn.textContent = btn.dataset.originalText;
            delete btn.dataset.originalText;
        }
    }

    /**
     * Show skeleton loading for tables
     * @param {string|HTMLElement} tableBody - Table body selector or element
     * @param {number} rows - Number of skeleton rows
     * @param {number} cols - Number of skeleton columns
     */
    showTableSkeleton(tableBody, rows = 5, cols = 4) {
        const tbody = typeof tableBody === 'string' ? document.querySelector(tableBody) : tableBody;
        if (!tbody) return;

        tbody.innerHTML = '';
        
        for (let i = 0; i < rows; i++) {
            const row = document.createElement('tr');
            for (let j = 0; j < cols; j++) {
                const cell = document.createElement('td');
                cell.innerHTML = '<div class="skeleton skeleton-text"></div>';
                row.appendChild(cell);
            }
            tbody.appendChild(row);
        }
    }

    /**
     * Show success message
     * @param {string} message - Success message
     * @param {string} title - Optional title
     * @param {number} duration - Duration in milliseconds (0 for persistent)
     */
    showSuccess(message, title = 'Success', duration = 5000) {
        this.showToast('success', title, message, duration);
    }

    /**
     * Show error message
     * @param {string} message - Error message
     * @param {string} title - Optional title
     * @param {number} duration - Duration in milliseconds (0 for persistent)
     */
    showError(message, title = 'Error', duration = 0) {
        this.showToast('danger', title, message, duration);
    }

    /**
     * Show warning message
     * @param {string} message - Warning message
     * @param {string} title - Optional title
     * @param {number} duration - Duration in milliseconds
     */
    showWarning(message, title = 'Warning', duration = 7000) {
        this.showToast('warning', title, message, duration);
    }

    /**
     * Show info message
     * @param {string} message - Info message
     * @param {string} title - Optional title
     * @param {number} duration - Duration in milliseconds
     */
    showInfo(message, title = 'Info', duration = 5000) {
        this.showToast('info', title, message, duration);
    }

    /**
     * Show toast notification
     * @param {string} type - Toast type (success, danger, warning, info)
     * @param {string} title - Toast title
     * @param {string} message - Toast message
     * @param {number} duration - Duration in milliseconds (0 for persistent)
     */
    showToast(type, title, message, duration = 5000) {
        const toastId = 'toast-' + Date.now();
        const iconMap = {
            success: 'fas fa-check-circle',
            danger: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-header">
                <i class="${iconMap[type]} toast-icon"></i>
                <strong class="toast-title">${title}</strong>
                <button type="button" class="toast-close" onclick="uiFeedback.hideToast('${toastId}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="toast-body">${message}</div>
        `;

        this.toastContainer.appendChild(toast);

        // Show toast with animation
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);

        // Auto-hide if duration is set
        if (duration > 0) {
            setTimeout(() => {
                this.hideToast(toastId);
            }, duration);
        }

        return toastId;
    }

    /**
     * Hide toast notification
     * @param {string} toastId - Toast ID
     */
    hideToast(toastId) {
        const toast = document.getElementById(toastId);
        if (toast) {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }
    }

    /**
     * Show alert in a container
     * @param {string|HTMLElement} container - Container selector or element
     * @param {string} type - Alert type (success, danger, warning, info)
     * @param {string} message - Alert message
     * @param {string} title - Optional title
     * @param {boolean} dismissible - Whether alert is dismissible
     */
    showAlert(container, type, message, title = null, dismissible = true) {
        const containerEl = typeof container === 'string' ? document.querySelector(container) : container;
        if (!containerEl) return;

        const iconMap = {
            success: 'fas fa-check-circle',
            danger: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        const alertId = 'alert-' + Date.now();
        const alert = document.createElement('div');
        alert.id = alertId;
        alert.className = `alert alert-${type} ${dismissible ? 'alert-dismissible' : ''}`;
        
        let alertContent = `
            <i class="${iconMap[type]} alert-icon"></i>
            <div class="alert-content">
                ${title ? `<div class="alert-title">${title}</div>` : ''}
                <div class="alert-message">${message}</div>
            </div>
        `;

        if (dismissible) {
            alertContent += `
                <button type="button" class="alert-close" onclick="uiFeedback.hideAlert('${alertId}')">
                    <i class="fas fa-times"></i>
                </button>
            `;
        }

        alert.innerHTML = alertContent;
        containerEl.insertBefore(alert, containerEl.firstChild);

        return alertId;
    }

    /**
     * Hide alert
     * @param {string} alertId - Alert ID
     */
    hideAlert(alertId) {
        const alert = document.getElementById(alertId);
        if (alert) {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => {
                alert.remove();
            }, 300);
        }
    }

    /**
     * Clear all alerts from a container
     * @param {string|HTMLElement} container - Container selector or element
     */
    clearAlerts(container) {
        const containerEl = typeof container === 'string' ? document.querySelector(container) : container;
        if (!containerEl) return;

        const alerts = containerEl.querySelectorAll('.alert');
        alerts.forEach(alert => {
            alert.remove();
        });
    }

    /**
     * Show empty state
     * @param {string|HTMLElement} container - Container selector or element
     * @param {string} title - Empty state title
     * @param {string} message - Empty state message
     * @param {string} icon - Optional icon class
     * @param {string} actionText - Optional action button text
     * @param {function} actionCallback - Optional action callback
     */
    showEmptyState(container, title, message, icon = 'fas fa-inbox', actionText = null, actionCallback = null) {
        const containerEl = typeof container === 'string' ? document.querySelector(container) : container;
        if (!containerEl) return;

        let emptyStateHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">
                    <i class="${icon}"></i>
                </div>
                <div class="empty-state-title">${title}</div>
                <div class="empty-state-message">${message}</div>
        `;

        if (actionText && actionCallback) {
            const actionId = 'empty-action-' + Date.now();
            emptyStateHTML += `
                <button id="${actionId}" class="btn btn-primary">
                    ${actionText}
                </button>
            `;
        }

        emptyStateHTML += '</div>';
        containerEl.innerHTML = emptyStateHTML;

        if (actionText && actionCallback) {
            const actionBtn = document.getElementById(actionId);
            if (actionBtn) {
                actionBtn.addEventListener('click', actionCallback);
            }
        }
    }

    /**
     * Show progress bar
     * @param {string|HTMLElement} container - Container selector or element
     * @param {number} progress - Progress percentage (0-100)
     * @param {string} label - Optional progress label
     * @param {boolean} animated - Whether to show animated stripes
     */
    showProgress(container, progress, label = null, animated = false) {
        const containerEl = typeof container === 'string' ? document.querySelector(container) : container;
        if (!containerEl) return;

        const progressHTML = `
            <div class="progress-container">
                ${label ? `<div class="progress-label mb-2">${label}</div>` : ''}
                <div class="progress">
                    <div class="progress-bar ${animated ? 'animated' : ''}" 
                         style="width: ${Math.min(100, Math.max(0, progress))}%">
                    </div>
                </div>
            </div>
        `;

        containerEl.innerHTML = progressHTML;
    }

    /**
     * Update progress bar
     * @param {string|HTMLElement} container - Container selector or element
     * @param {number} progress - Progress percentage (0-100)
     * @param {string} label - Optional new label
     */
    updateProgress(container, progress, label = null) {
        const containerEl = typeof container === 'string' ? document.querySelector(container) : container;
        if (!containerEl) return;

        const progressBar = containerEl.querySelector('.progress-bar');
        const progressLabel = containerEl.querySelector('.progress-label');

        if (progressBar) {
            progressBar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
        }

        if (label && progressLabel) {
            progressLabel.textContent = label;
        }
    }

    /**
     * Add hover effects to elements
     * @param {string} selector - Element selector
     */
    addHoverEffects(selector) {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            el.addEventListener('mouseenter', () => {
                el.style.transform = 'translateY(-2px)';
                el.style.boxShadow = 'var(--shadow-lg)';
            });

            el.addEventListener('mouseleave', () => {
                el.style.transform = '';
                el.style.boxShadow = '';
            });
        });
    }

    /**
     * Handle form submission with loading state
     * @param {HTMLFormElement} form - Form element
     * @param {function} submitHandler - Submit handler function
     * @param {string} loadingText - Loading button text
     */
    async handleFormSubmit(form, submitHandler, loadingText = 'Submitting...') {
        const submitBtn = form.querySelector('button[type="submit"]');
        
        try {
            this.showButtonLoading(submitBtn, loadingText);
            this.clearAlerts(form);
            
            await submitHandler();
            
        } catch (error) {
            console.error('Form submission error:', error);
            this.showAlert(form, 'danger', error.message || 'An error occurred while submitting the form.');
        } finally {
            this.hideButtonLoading(submitBtn);
        }
    }

    /**
     * Handle API request with loading state
     * @param {function} apiCall - API call function
     * @param {string|HTMLElement} loadingElement - Element to show loading on
     * @param {string} loadingMessage - Loading message
     */
    async handleApiRequest(apiCall, loadingElement = null, loadingMessage = 'Loading...') {
        try {
            if (loadingElement) {
                this.showLoading(loadingElement, loadingMessage);
            }

            const result = await apiCall();
            return result;

        } catch (error) {
            console.error('API request error:', error);
            
            // Show user-friendly error message
            let errorMessage = 'An unexpected error occurred. Please try again.';
            
            if (error.message) {
                errorMessage = error.message;
            } else if (error.status === 401) {
                errorMessage = 'You are not authorized to perform this action.';
            } else if (error.status === 403) {
                errorMessage = 'Access denied. You do not have permission to perform this action.';
            } else if (error.status === 404) {
                errorMessage = 'The requested resource was not found.';
            } else if (error.status >= 500) {
                errorMessage = 'Server error. Please try again later.';
            }

            this.showError(errorMessage);
            throw error;

        } finally {
            if (loadingElement) {
                this.hideLoading(loadingElement);
            }
        }
    }
}

// Create global instance
const uiFeedback = new UIFeedback();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UIFeedback;
}