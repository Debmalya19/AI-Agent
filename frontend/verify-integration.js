/**
 * Verification script to check if chat.html has all required voice integration components
 */

const fs = require('fs');
const path = require('path');

console.log('Verifying voice integration in chat.html...\n');

try {
    const chatHtmlPath = path.join(__dirname, 'chat.html');
    const chatHtml = fs.readFileSync(chatHtmlPath, 'utf8');

    const checks = [
        {
            name: 'Voice module imports',
            test: () => {
                return chatHtml.includes('/static/voice-capabilities.js') &&
                       chatHtml.includes('/static/voice-settings.js') &&
                       chatHtml.includes('/static/voice-controller.js') &&
                       chatHtml.includes('/static/voice-ui.js');
            }
        },
        {
            name: 'Voice controls container',
            test: () => chatHtml.includes('voice-controls-container')
        },
        {
            name: 'Voice feedback area',
            test: () => chatHtml.includes('voice-feedback-area')
        },
        {
            name: 'Voice initialization function',
            test: () => chatHtml.includes('initializeVoiceFeatures')
        },
        {
            name: 'Voice event listeners setup',
            test: () => chatHtml.includes('setupVoiceEventListeners')
        },
        {
            name: 'Voice transcript handling',
            test: () => chatHtml.includes('handleVoiceTranscript')
        },
        {
            name: 'Voice error handling',
            test: () => chatHtml.includes('handleVoiceError')
        },
        {
            name: 'TTS controls for bot messages',
            test: () => chatHtml.includes('createTTSControls')
        },
        {
            name: 'Voice status display',
            test: () => chatHtml.includes('showVoiceStatus')
        },
        {
            name: 'Voice feedback clearing',
            test: () => chatHtml.includes('clearVoiceFeedback')
        },
        {
            name: 'Keyboard shortcuts for voice',
            test: () => chatHtml.includes('Ctrl+Shift+V')
        },
        {
            name: 'Voice CSS styles',
            test: () => {
                return chatHtml.includes('.voice-controls-container') &&
                       chatHtml.includes('.voice-mic-button') &&
                       chatHtml.includes('.voice-playback-controls');
            }
        },
        {
            name: 'Recommended questions voice integration',
            test: () => chatHtml.includes('Selected question:')
        },
        {
            name: 'Auto-play functionality',
            test: () => chatHtml.includes('autoPlayEnabled')
        },
        {
            name: 'Voice recording toggle',
            test: () => chatHtml.includes('toggleVoiceRecording')
        }
    ];

    let passed = 0;
    let failed = 0;

    checks.forEach(check => {
        try {
            if (check.test()) {
                console.log(`✅ ${check.name}`);
                passed++;
            } else {
                console.log(`❌ ${check.name}`);
                failed++;
            }
        } catch (error) {
            console.log(`❌ ${check.name} (Error: ${error.message})`);
            failed++;
        }
    });

    console.log(`\nVerification Results:`);
    console.log(`✅ Passed: ${passed}`);
    console.log(`❌ Failed: ${failed}`);
    console.log(`📊 Total: ${checks.length}`);

    if (failed === 0) {
        console.log('\n🎉 All voice integration components are present in chat.html!');
        console.log('The voice features should work correctly when loaded in a browser.');
    } else {
        console.log(`\n⚠️  ${failed} integration components are missing or incomplete.`);
    }

    // Check for potential issues
    console.log('\nChecking for potential issues...');
    
    const potentialIssues = [];
    
    if (!chatHtml.includes('voiceController = new VoiceController')) {
        potentialIssues.push('VoiceController instantiation may be missing');
    }
    
    if (!chatHtml.includes('voiceUI = new VoiceUI')) {
        potentialIssues.push('VoiceUI instantiation may be missing');
    }
    
    if (chatHtml.includes('console.log') && chatHtml.match(/console\.log/g).length > 5) {
        potentialIssues.push('Many console.log statements present (consider removing for production)');
    }

    if (potentialIssues.length > 0) {
        console.log('⚠️  Potential issues found:');
        potentialIssues.forEach(issue => console.log(`   - ${issue}`));
    } else {
        console.log('✅ No obvious issues detected');
    }

} catch (error) {
    console.error('❌ Verification failed:', error.message);
    process.exit(1);
}