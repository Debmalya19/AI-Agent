/**
 * Tests for VoiceVisualFeedback class
 * Tests the visual feedback and animation system functionality
 */

// Import the VoiceVisualFeedback class
const VoiceVisualFeedback = require('./voice-visual-feedback.js');

// Mock DOM elements for testing
function createMockDOM() {
    const container = document.createElement('div');
    container.id = 'voice-container';
    container.innerHTML = `
        <div id="mic-button" class="mic-button">
            <svg id="mic-icon"></svg>
        </div>
        <div id="audio-visualizer" class="audio-visualizer">
            ${Array.from({length: 15}, () => '<div class="visualizer-bar"></div>').join('')}
        </div>
        <div id="transcript-area" class="conversation-section">
            <div class="transcript-text"></div>
        </div>
        <div id="response-area" class="conversation-section">
            <div class="response-text"></div>
        </div>
        <div id="status-text">Tap to start talking</div>
        <div id="status-indicator"></div>
    `;
    document.body.appendChild(container);
    return container;
}

// Test suite
describe('VoiceVisualFeedback', () => {
    let container;
    let visualFeedback;
    
    beforeEach(() => {
        // Create mock DOM
        container = createMockDOM();
        
        // Initialize VoiceVisualFeedback
        visualFeedback = new VoiceVisualFeedback(container);
    });
    
    afterEach(() => {
        // Cleanup
        if (visualFeedback) {
            visualFeedback.cleanup();
        }
        if (container && container.parentNode) {
            container.parentNode.removeChild(container);
        }
    });
    
    test('should initialize correctly', () => {
        expect(visualFeedback).toBeDefined();
        expect(visualFeedback.container).toBe(container);
        expect(visualFeedback.currentState).toBe('idle');
    });
    
    test('should cache DOM elements correctly', () => {
        expect(visualFeedback.elements.micButton).toBeTruthy();
        expect(visualFeedback.elements.audioVisualizer).toBeTruthy();
        expect(visualFeedback.elements.statusText).toBeTruthy();
        expect(visualFeedback.elements.visualizerBars).toBeTruthy();
        expect(visualFeedback.elements.visualizerBars.length).toBe(15);
    });
    
    test('should show listening state correctly', () => {
        visualFeedback.showListening();
        
        expect(visualFeedback.getState()).toBe('listening');
        expect(visualFeedback.elements.micButton.classList.contains('listening')).toBe(true);
        expect(visualFeedback.elements.audioVisualizer.classList.contains('active')).toBe(true);
        expect(visualFeedback.elements.statusText.textContent).toBe('Listening...');
    });
    
    test('should show processing state correctly', () => {
        visualFeedback.showProcessing();
        
        expect(visualFeedback.getState()).toBe('processing');
        expect(visualFeedback.elements.micButton.classList.contains('processing')).toBe(true);
        expect(visualFeedback.elements.statusText.textContent).toBe('Processing...');
    });
    
    test('should show speaking state correctly', () => {
        const testText = 'This is a test response';
        visualFeedback.showSpeaking(testText);
        
        expect(visualFeedback.getState()).toBe('speaking');
        expect(visualFeedback.elements.micButton.classList.contains('speaking')).toBe(true);
        expect(visualFeedback.elements.audioVisualizer.classList.contains('active')).toBe(true);
        expect(visualFeedback.elements.statusText.textContent).toBe('Speaking...');
    });
    
    test('should show error state correctly', () => {
        const errorMessage = 'Test error message';
        visualFeedback.showError(errorMessage);
        
        expect(visualFeedback.getState()).toBe('error');
        expect(visualFeedback.elements.micButton.classList.contains('error')).toBe(true);
        expect(visualFeedback.elements.statusText.textContent).toBe(errorMessage);
    });
    
    test('should show idle state correctly', () => {
        // First set to another state
        visualFeedback.showListening();
        
        // Then show idle
        visualFeedback.showIdle();
        
        expect(visualFeedback.getState()).toBe('idle');
        expect(visualFeedback.elements.micButton.classList.contains('listening')).toBe(false);
        expect(visualFeedback.elements.audioVisualizer.classList.contains('active')).toBe(false);
        expect(visualFeedback.elements.statusText.textContent).toBe('Tap to start talking');
    });
    
    test('should show muted state correctly', () => {
        visualFeedback.showMuted();
        
        expect(visualFeedback.elements.micButton.classList.contains('muted')).toBe(true);
        expect(visualFeedback.elements.statusText.textContent).toBe('Microphone muted');
    });
    
    test('should display transcript correctly', () => {
        const testTranscript = 'This is a test transcript';
        visualFeedback.displayTranscript(testTranscript);
        
        expect(visualFeedback.elements.transcriptText.textContent).toBe(testTranscript);
        expect(visualFeedback.elements.transcriptArea.classList.contains('active')).toBe(true);
    });
    
    test('should display response correctly', () => {
        const testResponse = 'This is a test response';
        visualFeedback.displayResponse(testResponse);
        
        expect(visualFeedback.elements.responseText.textContent).toBe(testResponse);
        expect(visualFeedback.elements.responseArea.classList.contains('active')).toBe(true);
    });
    
    test('should clear transcript correctly', () => {
        // First add transcript
        visualFeedback.displayTranscript('Test transcript');
        
        // Then clear it
        visualFeedback.clearTranscript();
        
        expect(visualFeedback.elements.transcriptText.textContent).toBe('');
        expect(visualFeedback.elements.transcriptArea.classList.contains('active')).toBe(false);
    });
    
    test('should clear response correctly', () => {
        // First add response
        visualFeedback.displayResponse('Test response');
        
        // Then clear it
        visualFeedback.clearResponse();
        
        expect(visualFeedback.elements.responseText.textContent).toBe('');
        expect(visualFeedback.elements.responseArea.classList.contains('active')).toBe(false);
    });
    
    test('should start and stop visualizer animation', () => {
        // Mock setInterval and clearInterval
        const originalSetInterval = global.setInterval;
        const originalClearInterval = global.clearInterval;
        
        let intervalId = 1;
        const intervals = new Map();
        
        global.setInterval = jest.fn((callback, delay) => {
            intervals.set(intervalId, { callback, delay });
            return intervalId++;
        });
        
        global.clearInterval = jest.fn((id) => {
            intervals.delete(id);
        });
        
        // Start animation
        visualFeedback.startVisualizerAnimation('listening');
        expect(global.setInterval).toHaveBeenCalled();
        
        // Stop animation
        visualFeedback.stopVisualizerAnimation();
        expect(global.clearInterval).toHaveBeenCalled();
        
        // Restore original functions
        global.setInterval = originalSetInterval;
        global.clearInterval = originalClearInterval;
    });
    
    test('should update status text with correct styling', () => {
        visualFeedback.updateStatusText('Test message', 'listening');
        
        expect(visualFeedback.elements.statusText.textContent).toBe('Test message');
        expect(visualFeedback.elements.statusText.classList.contains('listening')).toBe(true);
    });
    
    test('should handle state transitions correctly', () => {
        // Test state transition
        visualFeedback.showListening();
        expect(visualFeedback.getState()).toBe('listening');
        
        visualFeedback.showProcessing();
        expect(visualFeedback.getState()).toBe('processing');
        
        visualFeedback.showSpeaking();
        expect(visualFeedback.getState()).toBe('speaking');
        
        visualFeedback.showIdle();
        expect(visualFeedback.getState()).toBe('idle');
    });
    
    test('should cleanup correctly', () => {
        // Start some animations
        visualFeedback.showListening();
        
        // Cleanup
        visualFeedback.cleanup();
        
        expect(visualFeedback.getState()).toBe('idle');
        expect(visualFeedback.elements.audioVisualizer.classList.contains('active')).toBe(false);
    });
    
    test('should handle missing elements gracefully', () => {
        // Create a container without required elements
        const emptyContainer = document.createElement('div');
        const emptyFeedback = new VoiceVisualFeedback(emptyContainer);
        
        // These should not throw errors
        expect(() => {
            emptyFeedback.showListening();
            emptyFeedback.showProcessing();
            emptyFeedback.showSpeaking();
            emptyFeedback.showError('Test error');
            emptyFeedback.displayTranscript('Test');
            emptyFeedback.displayResponse('Test');
        }).not.toThrow();
        
        emptyFeedback.cleanup();
    });
    
    test('should update animation settings correctly', () => {
        const newSettings = {
            visualizer: {
                bars: 20,
                minHeight: 2,
                maxHeight: 50
            }
        };
        
        visualFeedback.updateAnimationSettings(newSettings);
        const settings = visualFeedback.getAnimationSettings();
        
        expect(settings.visualizer.bars).toBe(20);
        expect(settings.visualizer.minHeight).toBe(2);
        expect(settings.visualizer.maxHeight).toBe(50);
    });
    
    test('should handle audio level updates', () => {
        visualFeedback.showListening();
        
        // This should not throw an error
        expect(() => {
            visualFeedback.updateAudioLevel(50);
            visualFeedback.updateAudioLevel(0);
            visualFeedback.updateAudioLevel(100);
        }).not.toThrow();
    });
});

// Run tests if in Node.js environment
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { createMockDOM };
}