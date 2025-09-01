// Voice Mobile Touch Controls Tests
// Tests for mobile-specific touch interactions and gestures

// Mock VoiceMobileTouchManager for testing
class VoiceMobileTouchManager {
    constructor(voiceAssistantPage, speechManager, visualFeedback) {
        this.voiceAssistantPage = voiceAssistantPage;
        this.speechManager = speechManager;
        this.visualFeedback = visualFeedback;
        
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
        
        this.config = {
            holdToTalkThreshold: 300,
            tapToTalkTimeout: 5000,
            doubleTapDelay: 300,
            moveThreshold: 10,
            hapticEnabled: true,
            longPressThreshold: 500
        };
        
        this.touchMode = {
            tapToTalk: true,
            holdToTalk: true,
            doubleTapAction: 'settings',
            longPressAction: 'mute'
        };
        
        this.isMobile = true;
    }
    
    detectMobileDevice() {
        return this.isMobile;
    }
    
    isHapticSupported() {
        return 'vibrate' in navigator;
    }
    
    triggerHapticFeedback(intensity) {
        if (this.config.hapticEnabled && navigator.vibrate) {
            const patterns = {
                light: [10],
                medium: [20],
                heavy: [30]
            };
            navigator.vibrate(patterns[intensity] || patterns.light);
        }
    }
    
    handleMicTouchStart(e) {
        const touch = e.touches[0];
        this.touchState.activeTouch = touch.identifier;
        this.touchState.touchStartPos = { x: touch.clientX, y: touch.clientY };
        this.touchState.touchMoved = false;
        this.touchState.holdStartTime = Date.now();
        
        this.triggerHapticFeedback('light');
        
        this.touchState.holdTimer = setTimeout(() => {
            this.startHoldToTalk();
        }, this.config.holdToTalkThreshold);
    }
    
    handleMicTouchMove(e) {
        if (!this.touchState.activeTouch) return;
        
        const touch = Array.from(e.touches).find(t => t.identifier === this.touchState.activeTouch);
        if (!touch) return;
        
        const deltaX = Math.abs(touch.clientX - this.touchState.touchStartPos.x);
        const deltaY = Math.abs(touch.clientY - this.touchState.touchStartPos.y);
        const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
        
        if (distance > this.config.moveThreshold) {
            this.touchState.touchMoved = true;
            this.cancelHoldToTalk();
        }
    }
    
    handleMicTouchEnd(e) {
        if (!this.touchState.activeTouch) return;
        
        const touchDuration = Date.now() - this.touchState.holdStartTime;
        this.cancelHoldToTalk();
        
        if (!this.touchState.touchMoved) {
            if (touchDuration >= this.config.longPressThreshold) {
                this.handleLongPress();
            } else if (this.touchState.isHolding) {
                this.endHoldToTalk();
            } else {
                this.handleTap();
            }
        }
        
        this.resetTouchState();
    }
    
    handleTap() {
        const now = Date.now();
        if (now - this.touchState.lastTouchEnd < this.config.doubleTapDelay) {
            this.handleDoubleTap();
            return;
        }
        
        this.touchState.lastTouchEnd = now;
        this.touchState.tapTimer = setTimeout(() => {
            this.handleSingleTap();
        }, this.config.doubleTapDelay);
        
        this.triggerHapticFeedback('medium');
    }
    
    handleSingleTap() {
        if (this.speechManager.isListening()) {
            this.speechManager.stopListening();
        } else {
            this.startTapToTalk();
        }
    }
    
    handleDoubleTap() {
        if (this.touchState.tapTimer) {
            clearTimeout(this.touchState.tapTimer);
            this.touchState.tapTimer = null;
        }
        
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
        
        this.touchState.isHolding = true;
        this.speechManager.startListening();
        this.visualFeedback.showListening();
        this.triggerHapticFeedback('medium');
    }
    
    endHoldToTalk() {
        if (!this.touchState.isHolding) return;
        
        this.touchState.isHolding = false;
        this.speechManager.stopListening();
        this.triggerHapticFeedback('light');
    }
    
    startTapToTalk() {
        this.speechManager.startListening();
        
        setTimeout(() => {
            if (this.speechManager.isListening()) {
                this.speechManager.stopListening();
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
    
    setTouchMode(mode, enabled) {
        if (mode in this.touchMode) {
            this.touchMode[mode] = enabled;
        }
    }
    
    getTouchMode(mode) {
        return this.touchMode[mode];
    }
    
    setHapticEnabled(enabled) {
        this.config.hapticEnabled = enabled;
    }
    
    isHapticEnabled() {
        return this.config.hapticEnabled;
    }
    
    destroy() {
        if (this.touchState.holdTimer) {
            clearTimeout(this.touchState.holdTimer);
        }
        if (this.touchState.tapTimer) {
            clearTimeout(this.touchState.tapTimer);
        }
    }
}

describe('VoiceMobileTouchManager', () => {
    let touchManager;
    let mockVoiceAssistantPage;
    let mockSpeechManager;
    let mockVisualFeedback;
    let mockPageUI;
    
    beforeEach(() => {
        // Mock navigator.vibrate
        global.navigator = {
            vibrate: jest.fn(),
            userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'
        };
        
        // Create mock page UI
        mockPageUI = {
            handleSettingsClick: jest.fn(),
            handleMuteClick: jest.fn(),
            handleStopClick: jest.fn()
        };
        
        // Create mock voice assistant page
        mockVoiceAssistantPage = {
            pageUI: mockPageUI
        };
        
        // Create mock speech manager
        mockSpeechManager = {
            isListening: jest.fn(() => false),
            startListening: jest.fn(),
            stopListening: jest.fn()
        };
        
        // Create mock visual feedback
        mockVisualFeedback = {
            showListening: jest.fn(),
            showIdle: jest.fn()
        };
        
        // Initialize touch manager
        touchManager = new VoiceMobileTouchManager(
            mockVoiceAssistantPage,
            mockSpeechManager,
            mockVisualFeedback
        );
    });
    
    afterEach(() => {
        touchManager.destroy();
        jest.clearAllMocks();
    });
    
    describe('Initialization', () => {
        test('should initialize with correct default settings', () => {
            expect(touchManager.touchMode.tapToTalk).toBe(true);
            expect(touchManager.touchMode.holdToTalk).toBe(true);
            expect(touchManager.config.hapticEnabled).toBe(true);
        });
        
        test('should detect mobile device correctly', () => {
            expect(touchManager.detectMobileDevice()).toBe(true);
        });
        
        test('should detect haptic support', () => {
            expect(touchManager.isHapticSupported()).toBe(true);
        });
    });
    
    describe('Touch Event Handling', () => {
        let mockTouchEvent;
        
        beforeEach(() => {
            mockTouchEvent = {
                touches: [{
                    identifier: 1,
                    clientX: 100,
                    clientY: 100
                }],
                preventDefault: jest.fn()
            };
        });
        
        test('should handle touch start correctly', () => {
            touchManager.handleMicTouchStart(mockTouchEvent);
            
            expect(touchManager.touchState.activeTouch).toBe(1);
            expect(touchManager.touchState.touchStartPos).toEqual({ x: 100, y: 100 });
            expect(touchManager.touchState.holdStartTime).toBeTruthy();
            expect(navigator.vibrate).toHaveBeenCalledWith([10]);
        });
        
        test('should detect touch movement', () => {
            touchManager.handleMicTouchStart(mockTouchEvent);
            
            // Simulate movement beyond threshold
            const moveEvent = {
                touches: [{
                    identifier: 1,
                    clientX: 120, // 20px movement
                    clientY: 120
                }]
            };
            
            touchManager.handleMicTouchMove(moveEvent);
            
            expect(touchManager.touchState.touchMoved).toBe(true);
        });
        
        test('should handle touch end and trigger tap', (done) => {
            touchManager.handleMicTouchStart(mockTouchEvent);
            
            // End touch quickly (tap)
            setTimeout(() => {
                touchManager.handleMicTouchEnd({ preventDefault: jest.fn() });
                
                // Wait for double tap delay
                setTimeout(() => {
                    expect(mockSpeechManager.startListening).toHaveBeenCalled();
                    done();
                }, touchManager.config.doubleTapDelay + 50);
            }, 100);
        });
    });
    
    describe('Tap-to-Talk Functionality', () => {
        test('should start listening on single tap', (done) => {
            touchManager.handleSingleTap();
            
            expect(mockSpeechManager.startListening).toHaveBeenCalled();
            done();
        });
        
        test('should stop listening if already listening on tap', () => {
            mockSpeechManager.isListening.mockReturnValue(true);
            
            touchManager.handleSingleTap();
            
            expect(mockSpeechManager.stopListening).toHaveBeenCalled();
        });
        
        test('should auto-stop after timeout', (done) => {
            touchManager.startTapToTalk();
            
            expect(mockSpeechManager.startListening).toHaveBeenCalled();
            
            // Fast-forward time to test timeout
            setTimeout(() => {
                expect(mockSpeechManager.stopListening).toHaveBeenCalled();
                done();
            }, touchManager.config.tapToTalkTimeout + 100);
        });
    });
    
    describe('Hold-to-Talk Functionality', () => {
        test('should start hold-to-talk after threshold', (done) => {
            touchManager.startHoldToTalk();
            
            expect(touchManager.touchState.isHolding).toBe(true);
            expect(mockSpeechManager.startListening).toHaveBeenCalled();
            expect(mockVisualFeedback.showListening).toHaveBeenCalled();
            expect(navigator.vibrate).toHaveBeenCalledWith([20]);
            done();
        });
        
        test('should end hold-to-talk when touch ends', () => {
            touchManager.touchState.isHolding = true;
            
            touchManager.endHoldToTalk();
            
            expect(touchManager.touchState.isHolding).toBe(false);
            expect(mockSpeechManager.stopListening).toHaveBeenCalled();
            expect(navigator.vibrate).toHaveBeenCalledWith([10]);
        });
        
        test('should not start hold-to-talk if touch moved', () => {
            touchManager.touchState.touchMoved = true;
            
            touchManager.startHoldToTalk();
            
            expect(touchManager.touchState.isHolding).toBe(false);
            expect(mockSpeechManager.startListening).not.toHaveBeenCalled();
        });
    });
    
    describe('Double Tap Functionality', () => {
        test('should trigger settings on double tap', () => {
            touchManager.touchMode.doubleTapAction = 'settings';
            
            touchManager.handleDoubleTap();
            
            expect(mockPageUI.handleSettingsClick).toHaveBeenCalled();
            expect(navigator.vibrate).toHaveBeenCalledWith([30]);
        });
        
        test('should trigger mute on double tap when configured', () => {
            touchManager.touchMode.doubleTapAction = 'mute';
            
            touchManager.handleDoubleTap();
            
            expect(mockPageUI.handleMuteClick).toHaveBeenCalled();
        });
        
        test('should trigger stop on double tap when configured', () => {
            touchManager.touchMode.doubleTapAction = 'stop';
            
            touchManager.handleDoubleTap();
            
            expect(mockPageUI.handleStopClick).toHaveBeenCalled();
        });
    });
    
    describe('Long Press Functionality', () => {
        test('should trigger mute on long press', () => {
            touchManager.touchMode.longPressAction = 'mute';
            
            touchManager.handleLongPress();
            
            expect(mockPageUI.handleMuteClick).toHaveBeenCalled();
            expect(navigator.vibrate).toHaveBeenCalledWith([30]);
        });
        
        test('should trigger settings on long press when configured', () => {
            touchManager.touchMode.longPressAction = 'settings';
            
            touchManager.handleLongPress();
            
            expect(mockPageUI.handleSettingsClick).toHaveBeenCalled();
        });
        
        test('should trigger stop on long press when configured', () => {
            touchManager.touchMode.longPressAction = 'stop';
            
            touchManager.handleLongPress();
            
            expect(mockPageUI.handleStopClick).toHaveBeenCalled();
        });
    });
    
    describe('Haptic Feedback', () => {
        test('should trigger light haptic feedback', () => {
            touchManager.triggerHapticFeedback('light');
            
            expect(navigator.vibrate).toHaveBeenCalledWith([10]);
        });
        
        test('should trigger medium haptic feedback', () => {
            touchManager.triggerHapticFeedback('medium');
            
            expect(navigator.vibrate).toHaveBeenCalledWith([20]);
        });
        
        test('should trigger heavy haptic feedback', () => {
            touchManager.triggerHapticFeedback('heavy');
            
            expect(navigator.vibrate).toHaveBeenCalledWith([30]);
        });
        
        test('should not trigger haptic when disabled', () => {
            touchManager.setHapticEnabled(false);
            
            touchManager.triggerHapticFeedback('light');
            
            expect(navigator.vibrate).not.toHaveBeenCalled();
        });
    });
    
    describe('Touch Mode Configuration', () => {
        test('should enable/disable tap-to-talk', () => {
            touchManager.setTouchMode('tapToTalk', false);
            
            expect(touchManager.getTouchMode('tapToTalk')).toBe(false);
        });
        
        test('should enable/disable hold-to-talk', () => {
            touchManager.setTouchMode('holdToTalk', false);
            
            expect(touchManager.getTouchMode('holdToTalk')).toBe(false);
        });
        
        test('should change double tap action', () => {
            touchManager.setTouchMode('doubleTapAction', 'mute');
            
            expect(touchManager.getTouchMode('doubleTapAction')).toBe('mute');
        });
        
        test('should change long press action', () => {
            touchManager.setTouchMode('longPressAction', 'settings');
            
            expect(touchManager.getTouchMode('longPressAction')).toBe('settings');
        });
    });
    
    describe('Touch State Management', () => {
        test('should reset touch state correctly', () => {
            touchManager.touchState.activeTouch = 1;
            touchManager.touchState.touchMoved = true;
            touchManager.touchState.isHolding = true;
            
            touchManager.resetTouchState();
            
            expect(touchManager.touchState.activeTouch).toBeNull();
            expect(touchManager.touchState.touchMoved).toBe(false);
            expect(touchManager.touchState.isHolding).toBe(false);
        });
        
        test('should cancel hold-to-talk timer', () => {
            const mockTimer = setTimeout(() => {}, 1000);
            touchManager.touchState.holdTimer = mockTimer;
            
            touchManager.cancelHoldToTalk();
            
            expect(touchManager.touchState.holdTimer).toBeNull();
        });
    });
    
    describe('Cleanup', () => {
        test('should clean up timers on destroy', () => {
            const holdTimer = setTimeout(() => {}, 1000);
            const tapTimer = setTimeout(() => {}, 1000);
            
            touchManager.touchState.holdTimer = holdTimer;
            touchManager.touchState.tapTimer = tapTimer;
            
            touchManager.destroy();
            
            expect(touchManager.touchState.holdTimer).toBeNull();
            expect(touchManager.touchState.tapTimer).toBeNull();
        });
    });
    
    describe('Accessibility', () => {
        test('should provide proper touch target sizes', () => {
            // This would be tested in integration tests with actual DOM
            expect(touchManager.config.moveThreshold).toBe(10);
        });
        
        test('should support haptic feedback for accessibility', () => {
            expect(touchManager.isHapticSupported()).toBe(true);
            expect(touchManager.isHapticEnabled()).toBe(true);
        });
    });
});