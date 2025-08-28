/**
 * Voice Error UI Class
 * Visual error indicators and recovery suggestions for voice failures
 */

class VoiceErrorUI {
    constructor(container, options = {}) {
        this.container = container;
        this.options = { ...this.getDefaultOptions(), ...options };
        
        // UI elements
        this.elements = {};
        this.currentError = null;
        this.isVisible = false;
        
        // Animation timers
        this.hideTimer = null;
        this.pulseTimer = null;
        
        this.initialize();
    }

    /**
     * Get default options
     * @returns {Object} Default options
     */
    getDefaultOptions() {
        return {
            position: 'top-right', // 'top-left', 'top-right', 'bottom-left', 'bottom-right', 'center'
            autoHide: true,
            autoHideDelay: 5000,
            showRecoveryActions: true,
            enableAnimations: true,
            maxWidth: '400px',
            zIndex: 10000,
            theme: 'auto' // 'light', 'dark', 'auto'
        };
    }

    /**
     * Initialize error UI
     */
    initialize() {
        this.createErrorContainer();
        this.addStyles();
        this.setupEventListeners();
    }

    /**
     * Create error container and elements
     */
    createErrorContainer() {
        // Main error container
        this.elements.errorContainer = this.createElement('div', {
            className: 'voice-error-container',
            'aria-live': 'assertive',
            'aria-atomic': 'true',
            role: 'alert'
        });

        // Error header
        this.elements.errorHeader = this.createElement('div', {
            className: 'voice-error-header'
        });

        // Error icon
        this.elements.errorIcon = this.createElement('div', {
            className: 'voice-error-icon',
            'aria-hidden': 'true'
        });

        // Error title
        this.elements.errorTitle = this.createElement('div', {
            className: 'voice-error-title'
        });

        // Close button
        this.elements.closeButton = this.createElement('button', {
            className: 'voice-error-close',
            type: 'button',
            'aria-label': 'Close error message',
            title: 'Close'
        });
        this.elements.closeButton.innerHTML = '×';
        this.elements.closeButton.addEventListener('click', () => this.hide());

        // Error content
        this.elements.errorContent = this.createElement('div', {
            className: 'voice-error-content'
        });

        // Error message
        this.elements.errorMessage = this.createElement('div', {
            className: 'voice-error-message'
        });

        // Recovery actions
        this.elements.recoveryActions = this.createElement('div', {
            className: 'voice-error-recovery'
        });

        // Progress indicator for retries
        this.elements.progressIndicator = this.createElement('div', {
            className: 'voice-error-progress',
            'aria-hidden': 'true'
        });

        // Assemble elements
        this.elements.errorHeader.appendChild(this.elements.errorIcon);
        this.elements.errorHeader.appendChild(this.elements.errorTitle);
        this.elements.errorHeader.appendChild(this.elements.closeButton);

        this.elements.errorContent.appendChild(this.elements.errorMessage);
        this.elements.errorContent.appendChild(this.elements.recoveryActions);
        this.elements.errorContent.appendChild(this.elements.progressIndicator);

        this.elements.errorContainer.appendChild(this.elements.errorHeader);
        this.elements.errorContainer.appendChild(this.elements.errorContent);

        // Add to container
        this.container.appendChild(this.elements.errorContainer);
    }

    /**
     * Show error with visual indicators and recovery options
     * @param {Object} errorInfo - Error information
     * @param {Object} recoveryOptions - Recovery options
     */
    show(errorInfo, recoveryOptions = {}) {
        this.currentError = errorInfo;
        
        // Update error content
        this.updateErrorContent(errorInfo, recoveryOptions);
        
        // Show container
        this.elements.errorContainer.classList.add('visible');
        this.elements.errorContainer.classList.add(`error-${errorInfo.severity || 'medium'}`);
        this.elements.errorContainer.classList.add(`error-type-${errorInfo.type || 'unknown'}`);
        
        this.isVisible = true;
        
        // Start animations if enabled
        if (this.options.enableAnimations) {
            this.startErrorAnimation(errorInfo.type);
        }
        
        // Auto-hide if enabled
        if (this.options.autoHide && errorInfo.severity !== 'critical') {
            this.scheduleAutoHide();
        }
        
        // Focus management for accessibility
        this.manageFocus();
    }

    /**
     * Update error content
     * @param {Object} errorInfo - Error information
     * @param {Object} recoveryOptions - Recovery options
     */
    updateErrorContent(errorInfo, recoveryOptions) {
        // Update icon
        this.updateErrorIcon(errorInfo.type, errorInfo.severity);
        
        // Update title
        this.elements.errorTitle.textContent = this.getErrorTitle(errorInfo.type);
        
        // Update message
        this.elements.errorMessage.textContent = errorInfo.userMessage || errorInfo.message;
        
        // Update recovery actions
        this.updateRecoveryActions(recoveryOptions);
        
        // Update progress indicator
        this.updateProgressIndicator(recoveryOptions);
    }

    /**
     * Update error icon based on type and severity
     * @param {string} type - Error type
     * @param {string} severity - Error severity
     */
    updateErrorIcon(type, severity) {
        const icons = {
            permission: `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 1c-4.97 0-9 4.03-9 9v7c0 1.66 1.34 3 3 3h3v-8H5v-2c0-3.87 3.13-7 7-7s7 3.13 7 7v2h-4v8h3c1.66 0 3-1.34 3-3v-7c0-4.97-4.03-9-9-9z"/>
                    <path d="M12 15c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2z"/>
                </svg>
            `,
            network: `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM11 17h2v2h-2v-2zm2-1.5V14h-2v1.5c0 .28-.22.5-.5.5s-.5-.22-.5-.5V14c0-.55.45-1 1-1h2c.55 0 1 .45 1 1v1.5c0 .28-.22.5-.5.5s-.5-.22-.5-.5z"/>
                </svg>
            `,
            audio: `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
                    <path d="M19 11h2v2h-2z"/>
                </svg>
            `,
            speech_recognition: `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
                </svg>
            `,
            speech_synthesis: `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
                </svg>
            `,
            browser_support: `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
            `,
            unknown: `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z"/>
                </svg>
            `
        };

        this.elements.errorIcon.innerHTML = icons[type] || icons.unknown;
    }

    /**
     * Get error title based on type
     * @param {string} type - Error type
     * @returns {string} Error title
     */
    getErrorTitle(type) {
        const titles = {
            permission: 'Microphone Access Required',
            network: 'Connection Issue',
            audio: 'Audio Input Problem',
            speech_recognition: 'Voice Recognition Failed',
            speech_synthesis: 'Audio Playback Failed',
            browser_support: 'Voice Features Unavailable',
            unknown: 'Voice Error'
        };

        return titles[type] || titles.unknown;
    }

    /**
     * Update recovery actions
     * @param {Object} recoveryOptions - Recovery options
     */
    updateRecoveryActions(recoveryOptions) {
        this.elements.recoveryActions.innerHTML = '';

        if (!this.options.showRecoveryActions || !recoveryOptions.recoveryActions) {
            return;
        }

        const actionsTitle = this.createElement('div', {
            className: 'recovery-actions-title'
        });
        actionsTitle.textContent = 'What you can do:';

        const actionsList = this.createElement('ul', {
            className: 'recovery-actions-list'
        });

        recoveryOptions.recoveryActions.forEach(action => {
            const listItem = this.createElement('li', {
                className: 'recovery-action-item'
            });
            listItem.textContent = action;
            actionsList.appendChild(listItem);
        });

        this.elements.recoveryActions.appendChild(actionsTitle);
        this.elements.recoveryActions.appendChild(actionsList);

        // Add action buttons if available
        if (recoveryOptions.actionButtons) {
            const buttonsContainer = this.createElement('div', {
                className: 'recovery-action-buttons'
            });

            recoveryOptions.actionButtons.forEach(button => {
                const actionButton = this.createElement('button', {
                    className: `recovery-action-button ${button.type || 'secondary'}`,
                    type: 'button'
                });
                actionButton.textContent = button.text;
                actionButton.addEventListener('click', button.action);
                buttonsContainer.appendChild(actionButton);
            });

            this.elements.recoveryActions.appendChild(buttonsContainer);
        }
    }

    /**
     * Update progress indicator for retries
     * @param {Object} recoveryOptions - Recovery options
     */
    updateProgressIndicator(recoveryOptions) {
        this.elements.progressIndicator.innerHTML = '';

        if (!recoveryOptions.showProgress) {
            return;
        }

        const progressBar = this.createElement('div', {
            className: 'progress-bar'
        });

        const progressFill = this.createElement('div', {
            className: 'progress-fill'
        });

        const progressText = this.createElement('div', {
            className: 'progress-text'
        });

        if (recoveryOptions.retryCount !== undefined && recoveryOptions.maxRetries !== undefined) {
            const progress = (recoveryOptions.retryCount / recoveryOptions.maxRetries) * 100;
            progressFill.style.width = `${progress}%`;
            progressText.textContent = `Retry ${recoveryOptions.retryCount} of ${recoveryOptions.maxRetries}`;
        } else if (recoveryOptions.progressText) {
            progressText.textContent = recoveryOptions.progressText;
        }

        progressBar.appendChild(progressFill);
        this.elements.progressIndicator.appendChild(progressBar);
        this.elements.progressIndicator.appendChild(progressText);
    }

    /**
     * Start error-specific animations
     * @param {string} errorType - Type of error
     */
    startErrorAnimation(errorType) {
        // Clear existing animations
        this.stopErrorAnimation();

        // Different animations for different error types
        switch (errorType) {
            case 'network':
                this.startPulseAnimation();
                break;
            case 'audio':
                this.startShakeAnimation();
                break;
            case 'permission':
                this.startBounceAnimation();
                break;
            default:
                this.startFadeAnimation();
                break;
        }
    }

    /**
     * Start pulse animation for network errors
     */
    startPulseAnimation() {
        this.elements.errorIcon.classList.add('pulse-animation');
        this.pulseTimer = setInterval(() => {
            this.elements.errorIcon.classList.toggle('pulse-active');
        }, 1000);
    }

    /**
     * Start shake animation for audio errors
     */
    startShakeAnimation() {
        this.elements.errorContainer.classList.add('shake-animation');
        setTimeout(() => {
            this.elements.errorContainer.classList.remove('shake-animation');
        }, 600);
    }

    /**
     * Start bounce animation for permission errors
     */
    startBounceAnimation() {
        this.elements.errorContainer.classList.add('bounce-animation');
        setTimeout(() => {
            this.elements.errorContainer.classList.remove('bounce-animation');
        }, 1000);
    }

    /**
     * Start fade animation for general errors
     */
    startFadeAnimation() {
        this.elements.errorContainer.classList.add('fade-in-animation');
    }

    /**
     * Stop all error animations
     */
    stopErrorAnimation() {
        if (this.pulseTimer) {
            clearInterval(this.pulseTimer);
            this.pulseTimer = null;
        }

        this.elements.errorIcon.classList.remove('pulse-animation', 'pulse-active');
        this.elements.errorContainer.classList.remove('shake-animation', 'bounce-animation', 'fade-in-animation');
    }

    /**
     * Schedule auto-hide
     */
    scheduleAutoHide() {
        if (this.hideTimer) {
            clearTimeout(this.hideTimer);
        }

        this.hideTimer = setTimeout(() => {
            this.hide();
        }, this.options.autoHideDelay);
    }

    /**
     * Cancel auto-hide
     */
    cancelAutoHide() {
        if (this.hideTimer) {
            clearTimeout(this.hideTimer);
            this.hideTimer = null;
        }
    }

    /**
     * Hide error UI
     */
    hide() {
        if (!this.isVisible) return;

        this.elements.errorContainer.classList.remove('visible');
        this.elements.errorContainer.classList.remove(
            'error-critical', 'error-high', 'error-medium', 'error-low'
        );
        this.elements.errorContainer.classList.remove(
            'error-type-permission', 'error-type-network', 'error-type-audio',
            'error-type-speech_recognition', 'error-type-speech_synthesis',
            'error-type-browser_support', 'error-type-unknown'
        );

        this.isVisible = false;
        this.currentError = null;

        this.stopErrorAnimation();
        this.cancelAutoHide();
    }

    /**
     * Show retry progress
     * @param {number} current - Current retry attempt
     * @param {number} max - Maximum retry attempts
     * @param {string} message - Progress message
     */
    showRetryProgress(current, max, message = '') {
        if (!this.isVisible) return;

        this.updateProgressIndicator({
            showProgress: true,
            retryCount: current,
            maxRetries: max,
            progressText: message
        });

        // Cancel auto-hide during retries
        this.cancelAutoHide();
    }

    /**
     * Show recovery success
     * @param {string} message - Success message
     */
    showRecoverySuccess(message) {
        if (!this.isVisible) return;

        this.elements.errorContainer.classList.add('recovery-success');
        this.elements.errorMessage.textContent = message;

        // Auto-hide after success
        setTimeout(() => {
            this.hide();
        }, 2000);
    }

    /**
     * Manage focus for accessibility
     */
    manageFocus() {
        // Focus the error container for screen readers
        this.elements.errorContainer.setAttribute('tabindex', '-1');
        this.elements.errorContainer.focus();

        // Remove tabindex after focus
        setTimeout(() => {
            this.elements.errorContainer.removeAttribute('tabindex');
        }, 100);
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Keyboard navigation
        this.elements.errorContainer.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hide();
            }
        });

        // Pause auto-hide on hover
        this.elements.errorContainer.addEventListener('mouseenter', () => {
            this.cancelAutoHide();
        });

        this.elements.errorContainer.addEventListener('mouseleave', () => {
            if (this.options.autoHide && this.currentError && this.currentError.severity !== 'critical') {
                this.scheduleAutoHide();
            }
        });
    }

    /**
     * Add CSS styles
     */
    addStyles() {
        if (document.getElementById('voice-error-ui-styles')) return;

        const styles = `
            .voice-error-container {
                position: fixed;
                ${this.getPositionStyles()}
                max-width: ${this.options.maxWidth};
                min-width: 300px;
                background: var(--error-bg, #fff);
                border: 1px solid var(--error-border, #e0e0e0);
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                z-index: ${this.options.zIndex};
                opacity: 0;
                transform: translateY(-10px);
                transition: all 0.3s ease;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 14px;
                line-height: 1.4;
            }

            .voice-error-container.visible {
                opacity: 1;
                transform: translateY(0);
            }

            .voice-error-container.error-critical {
                border-left: 4px solid #dc3545;
                background: #fff5f5;
            }

            .voice-error-container.error-high {
                border-left: 4px solid #fd7e14;
                background: #fff8f0;
            }

            .voice-error-container.error-medium {
                border-left: 4px solid #ffc107;
                background: #fffbf0;
            }

            .voice-error-container.error-low {
                border-left: 4px solid #17a2b8;
                background: #f0f9ff;
            }

            .voice-error-header {
                display: flex;
                align-items: center;
                padding: 12px 16px 8px;
                border-bottom: 1px solid var(--error-border, #e0e0e0);
            }

            .voice-error-icon {
                width: 24px;
                height: 24px;
                margin-right: 12px;
                flex-shrink: 0;
            }

            .voice-error-icon svg {
                width: 100%;
                height: 100%;
                color: var(--error-icon-color, #666);
            }

            .voice-error-container.error-critical .voice-error-icon svg {
                color: #dc3545;
            }

            .voice-error-container.error-high .voice-error-icon svg {
                color: #fd7e14;
            }

            .voice-error-container.error-medium .voice-error-icon svg {
                color: #ffc107;
            }

            .voice-error-container.error-low .voice-error-icon svg {
                color: #17a2b8;
            }

            .voice-error-title {
                flex: 1;
                font-weight: 600;
                color: var(--error-title-color, #333);
            }

            .voice-error-close {
                background: none;
                border: none;
                font-size: 20px;
                cursor: pointer;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: var(--error-close-color, #666);
                border-radius: 4px;
                transition: background-color 0.2s;
            }

            .voice-error-close:hover {
                background-color: var(--error-close-hover, #f0f0f0);
            }

            .voice-error-content {
                padding: 12px 16px 16px;
            }

            .voice-error-message {
                color: var(--error-message-color, #555);
                margin-bottom: 12px;
            }

            .voice-error-recovery {
                margin-top: 12px;
            }

            .recovery-actions-title {
                font-weight: 600;
                color: var(--error-title-color, #333);
                margin-bottom: 8px;
            }

            .recovery-actions-list {
                margin: 0;
                padding-left: 20px;
                color: var(--error-message-color, #555);
            }

            .recovery-action-item {
                margin-bottom: 4px;
            }

            .recovery-action-buttons {
                display: flex;
                gap: 8px;
                margin-top: 12px;
            }

            .recovery-action-button {
                padding: 6px 12px;
                border: 1px solid var(--button-border, #ddd);
                border-radius: 4px;
                background: var(--button-bg, #fff);
                color: var(--button-color, #333);
                cursor: pointer;
                font-size: 12px;
                transition: all 0.2s;
            }

            .recovery-action-button:hover {
                background: var(--button-hover-bg, #f8f9fa);
            }

            .recovery-action-button.primary {
                background: #007bff;
                color: white;
                border-color: #007bff;
            }

            .recovery-action-button.primary:hover {
                background: #0056b3;
                border-color: #0056b3;
            }

            .voice-error-progress {
                margin-top: 12px;
            }

            .progress-bar {
                width: 100%;
                height: 4px;
                background: var(--progress-bg, #e0e0e0);
                border-radius: 2px;
                overflow: hidden;
                margin-bottom: 4px;
            }

            .progress-fill {
                height: 100%;
                background: var(--progress-fill, #007bff);
                transition: width 0.3s ease;
            }

            .progress-text {
                font-size: 12px;
                color: var(--progress-text-color, #666);
                text-align: center;
            }

            .voice-error-container.recovery-success {
                border-left-color: #28a745;
                background: #f0fff4;
            }

            .voice-error-container.recovery-success .voice-error-icon svg {
                color: #28a745;
            }

            /* Animations */
            .pulse-animation.pulse-active {
                animation: pulse 1s ease-in-out;
            }

            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.1); }
                100% { transform: scale(1); }
            }

            .shake-animation {
                animation: shake 0.6s ease-in-out;
            }

            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
                20%, 40%, 60%, 80% { transform: translateX(5px); }
            }

            .bounce-animation {
                animation: bounce 1s ease-in-out;
            }

            @keyframes bounce {
                0%, 20%, 53%, 80%, 100% { transform: translateY(0); }
                40%, 43% { transform: translateY(-10px); }
                70% { transform: translateY(-5px); }
                90% { transform: translateY(-2px); }
            }

            .fade-in-animation {
                animation: fadeIn 0.3s ease-in-out;
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            /* Dark theme support */
            @media (prefers-color-scheme: dark) {
                .voice-error-container {
                    --error-bg: #2d3748;
                    --error-border: #4a5568;
                    --error-title-color: #f7fafc;
                    --error-message-color: #e2e8f0;
                    --error-close-color: #a0aec0;
                    --error-close-hover: #4a5568;
                    --button-bg: #4a5568;
                    --button-color: #f7fafc;
                    --button-border: #718096;
                    --button-hover-bg: #2d3748;
                    --progress-bg: #4a5568;
                    --progress-text-color: #a0aec0;
                }
            }

            /* Responsive design */
            @media (max-width: 480px) {
                .voice-error-container {
                    left: 16px !important;
                    right: 16px !important;
                    max-width: none;
                    min-width: auto;
                }
            }
        `;

        const styleSheet = document.createElement('style');
        styleSheet.id = 'voice-error-ui-styles';
        styleSheet.textContent = styles;
        document.head.appendChild(styleSheet);
    }

    /**
     * Get position styles based on options
     * @returns {string} CSS position styles
     */
    getPositionStyles() {
        const positions = {
            'top-left': 'top: 20px; left: 20px;',
            'top-right': 'top: 20px; right: 20px;',
            'bottom-left': 'bottom: 20px; left: 20px;',
            'bottom-right': 'bottom: 20px; right: 20px;',
            'center': 'top: 50%; left: 50%; transform: translate(-50%, -50%);'
        };

        return positions[this.options.position] || positions['top-right'];
    }

    /**
     * Create DOM element with attributes
     * @param {string} tag - HTML tag name
     * @param {Object} attributes - Element attributes
     * @returns {HTMLElement} Created element
     */
    createElement(tag, attributes = {}) {
        const element = document.createElement(tag);
        
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else {
                element.setAttribute(key, value);
            }
        });
        
        return element;
    }

    /**
     * Check if error UI is currently visible
     * @returns {boolean} Whether error UI is visible
     */
    isErrorVisible() {
        return this.isVisible;
    }

    /**
     * Get current error information
     * @returns {Object|null} Current error or null
     */
    getCurrentError() {
        return this.currentError;
    }

    /**
     * Update theme
     * @param {string} theme - Theme name ('light', 'dark', 'auto')
     */
    updateTheme(theme) {
        this.options.theme = theme;
        // Theme is handled via CSS custom properties and media queries
    }

    /**
     * Destroy error UI and clean up
     */
    destroy() {
        this.hide();
        this.stopErrorAnimation();
        this.cancelAutoHide();

        if (this.elements.errorContainer && this.elements.errorContainer.parentNode) {
            this.elements.errorContainer.parentNode.removeChild(this.elements.errorContainer);
        }

        // Remove styles if no other instances exist
        const styleSheet = document.getElementById('voice-error-ui-styles');
        if (styleSheet && !document.querySelector('.voice-error-container')) {
            styleSheet.remove();
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceErrorUI;
} else {
    window.VoiceErrorUI = VoiceErrorUI;
}