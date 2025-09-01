// Voice Mobile Touch Controls
// Handles mobile-specific touch interactions for the voice assistant

class VoiceMobileTouchManager {
    constructor(voiceAssistantPage, speechManager, visualFeedback) {
        this.voiceAssistantPage = voiceAssistantPage;
        this.speechManager = speechManager;
        this.visualFeedback = visualFeedback;
        
        // Touch state management
        this.touchState = {
            isHolding: false,
            holdStartTime: null,
            holdTimer: null,
            tapTimer: null,
            lastTouchEnd: 0,
            touchStartPos: { x: 0, y: 0 },
            touchMoved: false,
            activeTouch: null
        };
        
        // Touch configuration
        this.config = {
            holdToTalkThreshold: 300, // ms to hold before starting hold-to-talk
            tapToTalkTimeout: 5000, // ms to auto-stop after tap-to-talk
            doubleTapDelay: 300, // ms between taps for double tap
            moveThreshold: 10, // px movement threshold to cancel tap
            hapticEnabled: this.isHapticSupported(),
            longPressThreshold: 500 // ms for long press detection
        };
        
        // Touch mode settings
        this.touchMode = {
            tapToTalk: true, // Single tap toggles listening
            holdToTalk: true, // Hold to talk while pressed
            doubleTapAction: 'settings', // 'settings', 'mute', 'stop'
            longPressAction: 'mute' // 'mute', 'settings', 'stop'
        };
        
        // Load settings from localStorage
        this.loadTouchSettings();
        
        // Initialize touch controls
        this.initialize();
        
        console.log('VoiceMobileTouchManager initialized with haptic support:', this.config.hapticEnabled);
    }
    
    initialize() {
        // Detect mobile device
        this.isMobile = this.detectMobileDevice();
        
        if (this.isMobile) {
            this.setupMobileTouchControls();
            this.optimizeForMobile();
        }
        
        // Always setup touch events for tablets and touch-enabled desktops
        this.setupTouchEvents();
        
        // Setup orientation change handling
        this.setupOrientationHandling();
        
        console.log('Touch controls initialized for mobile:', this.isMobile);
    }
    
    detectMobileDevice() {
        // Comprehensive mobile detection
        const userAgent = navigator.userAgent.toLowerCase();
        const isMobileUA = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent);
        const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        const isSmallScreen = window.innerWidth <= 768;
        
        return isMobileUA || (isTouchDevice && isSmallScreen);
    }
    
    isHapticSupported() {
        // Check for haptic feedback support
        return 'vibrate' in navigator || 
               ('hapticFeedback' in navigator) ||
               (window.DeviceMotionEvent && typeof DeviceMotionEvent.requestPermission === 'function');
    }
    
    loadTouchSettings() {
        // Load touch preferences from localStorage
        const savedSettings = localStorage.getItem('voice-assistant-touch-settings');
        if (savedSettings) {
            try {
                const settings = JSON.parse(savedSettings);
                this.touchMode = { ...this.touchMode, ...settings.touchMode };
                this.config = { ...this.config, ...settings.config };
            } catch (e) {
                console.warn('Failed to load touch settings:', e);
            }
        }
    }
    
    saveTouchSettings() {
        // Save touch preferences to localStorage
        const settings = {
            touchMode: this.touchMode,
            config: {
                hapticEnabled: this.config.hapticEnabled,
                holdToTalkThreshold: this.config.holdToTalkThreshold,
                tapToTalkTimeout: this.config.tapToTalkTimeout
            }
        };
        
        localStorage.setItem('voice-assistant-touch-settings', JSON.stringify(settings));
    }
    
    setupMobileTouchControls() {
        // Add mobile-specific CSS classes
        document.body.classList.add('mobile-device');
        
        // Optimize touch targets for mobile
        this.optimizeTouchTargets();
        
        // Add mobile-specific UI elements
        this.addMobileUI();
        
        // Prevent default touch behaviors that interfere with voice controls
        this.preventDefaultTouchBehaviors();
    }
    
    optimizeTouchTargets() {
        // Ensure all touch targets meet minimum size requirements (44px)
        const touchTargets = document.querySelectorAll('.control-btn, #mic-button');
        
        touchTargets.forEach(target => {
            const rect = target.getBoundingClientRect();
            if (rect.width < 44 || rect.height < 44) {
                target.style.minWidth = '44px';
                target.style.minHeight = '44px';
                target.classList.add('touch-optimized');
            }
        });
    }
    
    addMobileUI() {
        // Add mobile-specific UI indicators
        const container = document.getElementById('voice-container');
        
        // Add touch mode indicator
        const touchIndicator = document.createElement('div');
        touchIndicator.id = 'touch-mode-indicator';
        touchIndicator.className = 'touch-indicator';
        touchIndicator.innerHTML = `
            <div class="touch-hint">
                <span class="touch-hint-text">Tap to talk • Hold for continuous</span>
            </div>
        `;
        
        // Insert after the header
        const header = document.getElementById('voice-header');
        if (header && header.nextSibling) {
            container.insertBefore(touchIndicator, header.nextSibling);
        }
        
        // Add haptic feedback toggle if supported
        if (this.config.hapticEnabled) {
            this.addHapticToggle();
        }
    }
    
    addHapticToggle() {
        // Add haptic feedback toggle to settings
        const settingsModal = document.getElementById('settings-modal');
        const modalBody = settingsModal?.querySelector('.modal-body');
        
        if (modalBody) {
            const hapticSection = document.createElement('div');
            hapticSection.className = 'settings-section';
            hapticSection.innerHTML = `
                <h3>Touch Feedback</h3>
                <div class="setting-group">
                    <label for="haptic-feedback">Haptic feedback:</label>
                    <div class="checkbox-container">
                        <input type="checkbox" id="haptic-feedback" ${this.config.hapticEnabled ? 'checked' : ''}>
                        <span class="checkbox-label">Vibrate on touch interactions</span>
                    </div>
                </div>
            `;
            
            modalBody.appendChild(hapticSection);
            
            // Bind haptic toggle event
            const hapticToggle = document.getElementById('haptic-feedback');
            hapticToggle?.addEventListener('change', (e) => {
                this.config.hapticEnabled = e.target.checked;
                this.saveTouchSettings();
            });
        }
    }
    
    preventDefaultTouchBehaviors() {
        // Prevent zoom on double tap for the microphone button
        const micButton = document.getElementById('mic-button');
        if (micButton) {
            micButton.style.touchAction = 'manipulation';
        }
        
        // Prevent pull-to-refresh on the main container
        const container = document.getElementById('voice-container');
        if (container) {
            container.style.overscrollBehavior = 'none';
        }
        
        // Prevent context menu on long press for control elements
        const controls = document.querySelectorAll('.control-btn, #mic-button');
        controls.forEach(control => {
            control.addEventListener('contextmenu', (e) => {
                e.preventDefault();
            });
        });
    }
    
    setupTouchEvents() {
        // Setup touch events for the microphone button
        const micButton = document.getElementById('mic-button');
        if (micButton) {
            this.setupMicrophoneTouchEvents(micButton);
        }
        
        // Setup touch events for control buttons
        this.setupControlButtonTouchEvents();
        
        // Setup global touch event handlers
        this.setupGlobalTouchEvents();
    }
    
    setupMicrophoneTouchEvents(micButton) {
        // Touch start - begin touch interaction
        micButton.addEventListener('touchstart', (e) => {
            this.handleMicTouchStart(e);
        }, { passive: false });
        
        // Touch move - track movement to detect swipes/drags
        micButton.addEventListener('touchmove', (e) => {
            this.handleMicTouchMove(e);
        }, { passive: false });
        
        // Touch end - complete touch interaction
        micButton.addEventListener('touchend', (e) => {
            this.handleMicTouchEnd(e);
        }, { passive: false });
        
        // Touch cancel - handle interrupted touches
        micButton.addEventListener('touchcancel', (e) => {
            this.handleMicTouchCancel(e);
        }, { passive: false });
        
        console.log('Microphone touch events setup complete');
    }
    
    setupControlButtonTouchEvents() {
        // Enhanced touch events for control buttons
        const controlButtons = document.querySelectorAll('.control-btn');
        
        controlButtons.forEach(button => {
            // Add touch feedback
            button.addEventListener('touchstart', (e) => {
                this.handleControlTouchStart(e, button);
            }, { passive: true });
            
            button.addEventListener('touchend', (e) => {
                this.handleControlTouchEnd(e, button);
            }, { passive: true });
            
            button.addEventListener('touchcancel', (e) => {
                this.handleControlTouchCancel(e, button);
            }, { passive: true });
        });
    }
    
    setupGlobalTouchEvents() {
        // Handle global touch events for gesture recognition
        document.addEventListener('touchstart', (e) => {
            this.handleGlobalTouchStart(e);
        }, { passive: true });
        
        document.addEventListener('touchmove', (e) => {
            this.handleGlobalTouchMove(e);
        }, { passive: true });
        
        document.addEventListener('touchend', (e) => {
            this.handleGlobalTouchEnd(e);
        }, { passive: true });
    }
    
    setupOrientationHandling() {
        // Handle orientation changes
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.handleOrientationChange();
            }, 100);
        });
        
        // Handle resize events for responsive adjustments
        window.addEventListener('resize', () => {
            this.handleResize();
        });
    }
    
    // Microphone touch event handlers
    handleMicTouchStart(e) {
        e.preventDefault();
        
        const touch = e.touches[0];
        this.touchState.activeTouch = touch.identifier;
        this.touchState.touchStartPos = { x: touch.clientX, y: touch.clientY };
        this.touchState.touchMoved = false;
        this.touchState.holdStartTime = Date.now();
        
        // Provide immediate haptic feedback
        this.triggerHapticFeedback('light');
        
        // Add visual feedback for touch
        const micButton = e.currentTarget;
        micButton.classList.add('touch-active');
        
        // Start hold-to-talk timer
        this.touchState.holdTimer = setTimeout(() => {
            this.startHoldToTalk();
        }, this.config.holdToTalkThreshold);
        
        console.log('Microphone touch started');
    }
    
    handleMicTouchMove(e) {
        if (!this.touchState.activeTouch) return;
        
        const touch = Array.from(e.touches).find(t => t.identifier === this.touchState.activeTouch);
        if (!touch) return;
        
        // Calculate movement distance
        const deltaX = Math.abs(touch.clientX - this.touchState.touchStartPos.x);
        const deltaY = Math.abs(touch.clientY - this.touchState.touchStartPos.y);
        const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
        
        // If moved beyond threshold, cancel tap/hold
        if (distance > this.config.moveThreshold) {
            this.touchState.touchMoved = true;
            this.cancelHoldToTalk();
            
            // Remove visual feedback
            const micButton = e.currentTarget;
            micButton.classList.remove('touch-active');
        }
    }
    
    handleMicTouchEnd(e) {
        e.preventDefault();
        
        const micButton = e.currentTarget;
        micButton.classList.remove('touch-active');
        
        if (!this.touchState.activeTouch) return;
        
        const touchDuration = Date.now() - this.touchState.holdStartTime;
        
        // Clear hold timer
        this.cancelHoldToTalk();
        
        // Handle different touch patterns
        if (!this.touchState.touchMoved) {
            if (touchDuration >= this.config.longPressThreshold) {
                this.handleLongPress();
            } else if (this.touchState.isHolding) {
                this.endHoldToTalk();
            } else {
                this.handleTap();
            }
        }
        
        // Reset touch state
        this.resetTouchState();
        
        console.log('Microphone touch ended, duration:', touchDuration);
    }
    
    handleMicTouchCancel(e) {
        console.log('Microphone touch cancelled');
        
        // Clean up any active states
        this.cancelHoldToTalk();
        this.endHoldToTalk();
        
        // Remove visual feedback
        const micButton = e.currentTarget;
        micButton.classList.remove('touch-active');
        
        // Reset touch state
        this.resetTouchState();
    }
    
    // Control button touch handlers
    handleControlTouchStart(e, button) {
        button.classList.add('touch-active');
        this.triggerHapticFeedback('light');
    }
    
    handleControlTouchEnd(e, button) {
        button.classList.remove('touch-active');
        
        // Add a small delay to show the touch feedback
        setTimeout(() => {
            button.classList.add('touch-feedback');
            setTimeout(() => {
                button.classList.remove('touch-feedback');
            }, 150);
        }, 50);
    }
    
    handleControlTouchCancel(e, button) {
        button.classList.remove('touch-active');
    }
    
    // Global touch handlers for gestures
    handleGlobalTouchStart(e) {
        // Track global touch patterns for potential gestures
        if (e.touches.length === 2) {
            // Two-finger touch - could be used for special actions
            this.handleTwoFingerTouch(e);
        }
    }
    
    handleGlobalTouchMove(e) {
        // Handle global touch movements
        if (e.touches.length === 2) {
            // Two-finger gesture handling
            this.handleTwoFingerGesture(e);
        }
    }
    
    handleGlobalTouchEnd(e) {
        // Clean up global touch state
    }
    
    // Touch interaction handlers
    handleTap() {
        console.log('Tap detected on microphone');
        
        if (!this.touchMode.tapToTalk) return;
        
        // Check for double tap
        const now = Date.now();
        if (now - this.touchState.lastTouchEnd < this.config.doubleTapDelay) {
            this.handleDoubleTap();
            return;
        }
        
        this.touchState.lastTouchEnd = now;
        
        // Set timer to handle single tap after double tap delay
        this.touchState.tapTimer = setTimeout(() => {
            this.handleSingleTap();
        }, this.config.doubleTapDelay);
        
        this.triggerHapticFeedback('medium');
    }
    
    handleSingleTap() {
        console.log('Single tap - toggle listening');
        
        // Toggle listening state
        if (this.speechManager.isListening()) {
            this.speechManager.stopListening();
        } else {
            this.startTapToTalk();
        }
    }
    
    handleDoubleTap() {
        console.log('Double tap detected');
        
        // Clear single tap timer
        if (this.touchState.tapTimer) {
            clearTimeout(this.touchState.tapTimer);
            this.touchState.tapTimer = null;
        }
        
        // Execute double tap action
        switch (this.touchMode.doubleTapAction) {
            case 'settings':
                this.voiceAssistantPage.pageUI?.handleSettingsClick();
                break;
            case 'mute':
                this.voiceAssistantPage.pageUI?.handleMuteClick();
                break;
            case 'stop':
                this.voiceAssistantPage.pageUI?.handleStopClick();
                break;
        }
        
        this.triggerHapticFeedback('heavy');
    }
    
    handleLongPress() {
        console.log('Long press detected');
        
        // Execute long press action
        switch (this.touchMode.longPressAction) {
            case 'mute':
                this.voiceAssistantPage.pageUI?.handleMuteClick();
                break;
            case 'settings':
                this.voiceAssistantPage.pageUI?.handleSettingsClick();
                break;
            case 'stop':
                this.voiceAssistantPage.pageUI?.handleStopClick();
                break;
        }
        
        this.triggerHapticFeedback('heavy');
    }
    
    startHoldToTalk() {
        if (!this.touchMode.holdToTalk || this.touchState.touchMoved) return;
        
        console.log('Starting hold-to-talk');
        
        this.touchState.isHolding = true;
        
        // Start listening
        this.speechManager.startListening();
        
        // Update visual feedback
        if (this.visualFeedback) {
            this.visualFeedback.showListening();
            this.updateTouchHint('Release to stop talking');
        }
        
        this.triggerHapticFeedback('medium');
    }
    
    endHoldToTalk() {
        if (!this.touchState.isHolding) return;
        
        console.log('Ending hold-to-talk');
        
        this.touchState.isHolding = false;
        
        // Stop listening
        this.speechManager.stopListening();
        
        // Update visual feedback
        this.updateTouchHint('Tap to talk • Hold for continuous');
        
        this.triggerHapticFeedback('light');
    }
    
    startTapToTalk() {
        console.log('Starting tap-to-talk');
        
        // Start listening
        this.speechManager.startListening();
        
        // Update visual feedback
        this.updateTouchHint('Listening... Tap again to stop');
        
        // Auto-stop after timeout
        setTimeout(() => {
            if (this.speechManager.isListening()) {
                this.speechManager.stopListening();
                this.updateTouchHint('Tap to talk • Hold for continuous');
            }
        }, this.config.tapToTalkTimeout);
    }
    
    cancelHoldToTalk() {
        if (this.touchState.holdTimer) {
            clearTimeout(this.touchState.holdTimer);
            this.touchState.holdTimer = null;
        }
    }
    
    resetTouchState() {
        this.touchState.activeTouch = null;
        this.touchState.touchMoved = false;
        this.touchState.holdStartTime = null;
        this.touchState.isHolding = false;
    }
    
    // Gesture handlers
    handleTwoFingerTouch(e) {
        // Two-finger touch could be used for special actions
        console.log('Two-finger touch detected');
    }
    
    handleTwoFingerGesture(e) {
        // Handle two-finger gestures (pinch, rotate, etc.)
    }
    
    // Haptic feedback
    triggerHapticFeedback(intensity = 'light') {
        if (!this.config.hapticEnabled) return;
        
        try {
            if (navigator.vibrate) {
                const patterns = {
                    light: [10],
                    medium: [20],
                    heavy: [30],
                    double: [10, 50, 20]
                };
                
                navigator.vibrate(patterns[intensity] || patterns.light);
            }
        } catch (e) {
            console.warn('Haptic feedback failed:', e);
        }
    }
    
    // UI updates
    updateTouchHint(text) {
        const hintElement = document.querySelector('.touch-hint-text');
        if (hintElement) {
            hintElement.textContent = text;
        }
    }
    
    optimizeForMobile() {
        // Add mobile-specific optimizations
        const container = document.getElementById('voice-container');
        if (container) {
            container.classList.add('mobile-optimized');
        }
        
        // Adjust microphone button size for mobile
        const micButton = document.getElementById('mic-button');
        if (micButton && window.innerWidth <= 480) {
            micButton.classList.add('mobile-size');
        }
        
        // Optimize control layout for mobile
        const controls = document.getElementById('voice-controls');
        if (controls && window.innerWidth <= 480) {
            controls.classList.add('mobile-layout');
        }
    }
    
    handleOrientationChange() {
        console.log('Orientation changed');
        
        // Re-optimize for new orientation
        setTimeout(() => {
            this.optimizeForMobile();
            this.optimizeTouchTargets();
        }, 200);
    }
    
    handleResize() {
        // Handle responsive adjustments
        const isMobileSize = window.innerWidth <= 768;
        
        if (isMobileSize && !document.body.classList.contains('mobile-device')) {
            this.setupMobileTouchControls();
        } else if (!isMobileSize && document.body.classList.contains('mobile-device')) {
            document.body.classList.remove('mobile-device');
        }
    }
    
    // Public API
    setTouchMode(mode, enabled) {
        if (mode in this.touchMode) {
            this.touchMode[mode] = enabled;
            this.saveTouchSettings();
            console.log(`Touch mode ${mode} set to:`, enabled);
        }
    }
    
    getTouchMode(mode) {
        return this.touchMode[mode];
    }
    
    setHapticEnabled(enabled) {
        this.config.hapticEnabled = enabled && this.isHapticSupported();
        this.saveTouchSettings();
    }
    
    isHapticEnabled() {
        return this.config.hapticEnabled;
    }
    
    // Cleanup
    destroy() {
        // Clean up timers
        if (this.touchState.holdTimer) {
            clearTimeout(this.touchState.holdTimer);
        }
        if (this.touchState.tapTimer) {
            clearTimeout(this.touchState.tapTimer);
        }
        
        // Remove event listeners would go here if needed
        console.log('VoiceMobileTouchManager destroyed');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceMobileTouchManager;
}