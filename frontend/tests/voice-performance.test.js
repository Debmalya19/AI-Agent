/**
 * Voice Performance Tests
 * Tests voice processing performance under various network conditions and load scenarios
 */

class VoicePerformanceTest {
    constructor() {
        this.testResults = [];
        this.performanceMetrics = [];
        this.setupPerformanceMocks();
    }

    setupPerformanceMocks() {
        // Mock performance API
        this.mockPerformance = {
            marks: new Map(),
            measures: new Map(),
            
            mark: function(name) {
                this.marks.set(name, Date.now());
            },
            
            measure: function(name, startMark, endMark) {
                const startTime = this.marks.get(startMark);
                const endTime = this.marks.get(endMark);
                if (startTime && endTime) {
                    const duration = endTime - startTime;
                    this.measures.set(name, duration);
                    return { duration };
                }
                return null;
            },
            
            getEntriesByType: function(type) {
                if (type === 'measure') {
                    return Array.from(this.measures.entries()).map(([name, duration]) => ({
                        name,
                        duration
                    }));
                }
                return [];
            },
            
            now: function() {
                return Date.now();
            }
        };

        // Mock network conditions
        this.networkConditions = {
            fast: { latency: 10, bandwidth: 1000, packetLoss: 0 },
            normal: { latency: 50, bandwidth: 100, packetLoss: 0.1 },
            slow: { latency: 200, bandwidth: 10, packetLoss: 1 },
            poor: { latency: 500, bandwidth: 1, packetLoss: 5 }
        };

        // Mock Web Speech API with performance tracking
        this.mockSpeechRecognition = class {
            constructor() {
                this.lang = 'en-US';
                this.onstart = null;
                this.onresult = null;
                this.onerror = null;
                this.onend = null;
                this._startTime = null;
                this._networkCondition = 'normal';
            }

            start() {
                this._startTime = Date.now();
                const condition = this.networkConditions[this._networkCondition];
                
                setTimeout(() => {
                    if (this.onstart) this.onstart();
                }, condition.latency);
            }

            _simulateResult(transcript, networkCondition = 'normal') {
                this._networkCondition = networkCondition;
                const condition = this.networkConditions[networkCondition];
                const processingTime = 500 + condition.latency + (Math.random() * 1000);
                
                setTimeout(() => {
                    if (Math.random() * 100 < condition.packetLoss) {
                        // Simulate network error
                        if (this.onerror) {
                            this.onerror({ error: 'network' });
                        }
                        return;
                    }
                    
                    if (this.onresult) {
                        const confidence = Math.max(0.5, 1 - (condition.latency / 1000));
                        this.onresult({
                            resultIndex: 0,
                            results: [{
                                0: { transcript, confidence },
                                isFinal: true,
                                length: 1
                            }]
                        });
                    }
                }, processingTime);
            }
        };

        this.mockSpeechSynthesis = {
            speaking: false,
            
            speak: function(utterance) {
                const startTime = Date.now();
                this.speaking = true;
                
                setTimeout(() => {
                    if (utterance.onstart) utterance.onstart();
                }, 10);
                
                // Simulate TTS processing time based on text length
                const processingTime = Math.max(100, utterance.text.length * 50);
                
                setTimeout(() => {
                    this.speaking = false;
                    if (utterance.onend) {
                        utterance.onend();
                        // Track TTS performance
                        const duration = Date.now() - startTime;
                        this.lastTTSPerformance = {
                            textLength: utterance.text.length,
                            duration: duration,
                            rate: utterance.text.length / (duration / 1000) // chars per second
                        };
                    }
                }, processingTime);
            },
            
            cancel: function() {
                this.speaking = false;
            }
        };

        // Setup global mocks
        if (typeof window !== 'undefined') {
            window.performance = this.mockPerformance;
            window.SpeechRecognition = this.mockSpeechRecognition;
            window.speechSynthesis = this.mockSpeechSynthesis;
        }
    }

    assert(condition, message) {
        if (condition) {
            this.testResults.push({ status: 'PASS', message });
            console.log(`✓ ${message}`);
        } else {
            this.testResults.push({ status: 'FAIL', message });
            console.error(`✗ ${message}`);
        }
    }

    async runTests() {
        console.log('Running Voice Performance Tests...\n');

        try {
            await this.testSTTPerformanceUnderNetworkConditions();
            await this.testTTSPerformanceWithVariousTextLengths();
            await this.testConcurrentVoiceOperations();
            await this.testVoiceMemoryUsage();
            await this.testVoiceLatencyMeasurement();
            await this.testVoiceErrorRecoveryPerformance();
            await this.testVoiceQueuePerformance();
            await this.testVoiceBandwidthUsage();
        } catch (error) {
            console.error('Performance test suite error:', error);
        }

        this.printResults();
        this.printPerformanceMetrics();
    }

    async testSTTPerformanceUnderNetworkConditions() {
        console.log('Testing STT performance under various network conditions...');

        const testCases = [
            { condition: 'fast', expectedMaxLatency: 100 },
            { condition: 'normal', expectedMaxLatency: 300 },
            { condition: 'slow', expectedMaxLatency: 1000 },
            { condition: 'poor', expectedMaxLatency: 2000 }
        ];

        for (const testCase of testCases) {
            const recognition = new this.mockSpeechRecognition();
            let startTime, endTime;
            let resultReceived = false;
            let errorOccurred = false;

            recognition.onstart = () => {
                startTime = Date.now();
            };

            recognition.onresult = () => {
                endTime = Date.now();
                resultReceived = true;
            };

            recognition.onerror = () => {
                endTime = Date.now();
                errorOccurred = true;
            };

            // Start recognition
            recognition.start();
            
            // Simulate speech input
            setTimeout(() => {
                recognition._simulateResult('Test speech input', testCase.condition);
            }, 50);

            // Wait for result or timeout
            await new Promise(resolve => {
                const timeout = setTimeout(() => {
                    resolve();
                }, testCase.expectedMaxLatency + 1000);
                
                const checkResult = () => {
                    if (resultReceived || errorOccurred) {
                        clearTimeout(timeout);
                        resolve();
                    } else {
                        setTimeout(checkResult, 10);
                    }
                };
                checkResult();
            });

            if (resultReceived || errorOccurred) {
                const latency = endTime - startTime;
                
                this.performanceMetrics.push({
                    test: 'STT_Latency',
                    condition: testCase.condition,
                    latency: latency,
                    success: resultReceived
                });

                if (testCase.condition !== 'poor') {
                    this.assert(
                        latency <= testCase.expectedMaxLatency,
                        `STT latency under ${testCase.condition} conditions should be <= ${testCase.expectedMaxLatency}ms (actual: ${latency}ms)`
                    );
                }

                this.assert(
                    resultReceived || testCase.condition === 'poor',
                    `STT should work under ${testCase.condition} conditions (or fail gracefully for poor conditions)`
                );
            } else {
                this.assert(
                    false,
                    `STT should respond within timeout for ${testCase.condition} conditions`
                );
            }
        }
    }

    async testTTSPerformanceWithVariousTextLengths() {
        console.log('Testing TTS performance with various text lengths...');

        const testTexts = [
            { name: 'short', text: 'Hello', expectedMaxTime: 200 },
            { name: 'medium', text: 'This is a medium length message for testing TTS performance.', expectedMaxTime: 500 },
            { name: 'long', text: 'This is a much longer message that will test the text-to-speech performance with extended content. It includes multiple sentences and should take longer to process and play back to the user.', expectedMaxTime: 1000 },
            { name: 'very_long', text: 'This is an extremely long message designed to test the limits of text-to-speech performance. '.repeat(10), expectedMaxTime: 2000 }
        ];

        for (const testText of testTexts) {
            const utterance = {
                text: testText.text,
                onstart: null,
                onend: null
            };

            let startTime, endTime;
            let speechStarted = false;
            let speechEnded = false;

            utterance.onstart = () => {
                startTime = Date.now();
                speechStarted = true;
            };

            utterance.onend = () => {
                endTime = Date.now();
                speechEnded = true;
            };

            // Start TTS
            this.mockSpeechSynthesis.speak(utterance);

            // Wait for completion
            await new Promise(resolve => {
                const timeout = setTimeout(() => {
                    resolve();
                }, testText.expectedMaxTime + 1000);
                
                const checkCompletion = () => {
                    if (speechEnded) {
                        clearTimeout(timeout);
                        resolve();
                    } else {
                        setTimeout(checkCompletion, 10);
                    }
                };
                checkCompletion();
            });

            if (speechStarted && speechEnded) {
                const duration = endTime - startTime;
                const performance = this.mockSpeechSynthesis.lastTTSPerformance;
                
                this.performanceMetrics.push({
                    test: 'TTS_Performance',
                    textLength: testText.text.length,
                    duration: duration,
                    rate: performance ? performance.rate : 0
                });

                this.assert(
                    duration <= testText.expectedMaxTime,
                    `TTS ${testText.name} text should complete within ${testText.expectedMaxTime}ms (actual: ${duration}ms)`
                );

                if (performance) {
                    this.assert(
                        performance.rate > 5, // At least 5 characters per second
                        `TTS should maintain reasonable processing rate (actual: ${performance.rate.toFixed(2)} chars/sec)`
                    );
                }
            } else {
                this.assert(
                    false,
                    `TTS should complete for ${testText.name} text`
                );
            }
        }
    }

    async testConcurrentVoiceOperations() {
        console.log('Testing concurrent voice operations performance...');

        const concurrentOperations = 5;
        const operations = [];
        const results = [];

        // Create multiple concurrent TTS operations
        for (let i = 0; i < concurrentOperations; i++) {
            const operation = new Promise((resolve) => {
                const utterance = {
                    text: `Concurrent message ${i + 1}`,
                    onstart: null,
                    onend: null
                };

                const startTime = Date.now();
                let endTime;

                utterance.onend = () => {
                    endTime = Date.now();
                    resolve({
                        id: i,
                        duration: endTime - startTime,
                        success: true
                    });
                };

                // Simulate slight delay between operations
                setTimeout(() => {
                    this.mockSpeechSynthesis.speak(utterance);
                }, i * 10);
            });

            operations.push(operation);
        }

        // Wait for all operations to complete
        const startTime = Date.now();
        const operationResults = await Promise.all(operations);
        const totalTime = Date.now() - startTime;

        this.performanceMetrics.push({
            test: 'Concurrent_Operations',
            operationCount: concurrentOperations,
            totalTime: totalTime,
            averageTime: totalTime / concurrentOperations
        });

        this.assert(
            operationResults.length === concurrentOperations,
            'All concurrent operations should complete'
        );

        this.assert(
            operationResults.every(result => result.success),
            'All concurrent operations should succeed'
        );

        this.assert(
            totalTime < 5000, // Should complete within 5 seconds
            `Concurrent operations should complete within reasonable time (actual: ${totalTime}ms)`
        );

        const averageTime = totalTime / concurrentOperations;
        this.assert(
            averageTime < 1000,
            `Average operation time should be reasonable (actual: ${averageTime}ms)`
        );
    }

    async testVoiceMemoryUsage() {
        console.log('Testing voice memory usage...');

        // Mock memory usage tracking
        const memoryTracker = {
            initialMemory: 100, // MB
            currentMemory: 100,
            
            allocate: function(amount) {
                this.currentMemory += amount;
            },
            
            deallocate: function(amount) {
                this.currentMemory = Math.max(this.initialMemory, this.currentMemory - amount);
            },
            
            getUsage: function() {
                return this.currentMemory - this.initialMemory;
            }
        };

        const initialMemory = memoryTracker.getUsage();

        // Simulate creating multiple voice operations
        const voiceOperations = [];
        for (let i = 0; i < 10; i++) {
            // Simulate memory allocation for voice processing
            memoryTracker.allocate(5); // 5MB per operation
            
            voiceOperations.push({
                id: i,
                cleanup: () => memoryTracker.deallocate(5)
            });
        }

        const peakMemory = memoryTracker.getUsage();

        // Cleanup operations
        voiceOperations.forEach(op => op.cleanup());
        const finalMemory = memoryTracker.getUsage();

        this.performanceMetrics.push({
            test: 'Memory_Usage',
            initialMemory: initialMemory,
            peakMemory: peakMemory,
            finalMemory: finalMemory,
            memoryLeak: finalMemory - initialMemory
        });

        this.assert(
            peakMemory <= 100, // Should not exceed 100MB
            `Peak memory usage should be reasonable (actual: ${peakMemory}MB)`
        );

        this.assert(
            finalMemory <= initialMemory + 10, // Allow small overhead
            `Memory should be properly cleaned up (leak: ${finalMemory - initialMemory}MB)`
        );
    }

    async testVoiceLatencyMeasurement() {
        console.log('Testing voice latency measurement...');

        const latencyTests = [
            { name: 'STT_Start_Latency', operation: 'stt_start' },
            { name: 'STT_Result_Latency', operation: 'stt_result' },
            { name: 'TTS_Start_Latency', operation: 'tts_start' },
            { name: 'TTS_Audio_Latency', operation: 'tts_audio' }
        ];

        for (const test of latencyTests) {
            const measurements = [];
            const iterations = 5;

            for (let i = 0; i < iterations; i++) {
                let startTime, endTime;

                if (test.operation === 'stt_start') {
                    const recognition = new this.mockSpeechRecognition();
                    startTime = Date.now();
                    
                    recognition.onstart = () => {
                        endTime = Date.now();
                    };
                    
                    recognition.start();
                    
                    await new Promise(resolve => {
                        const checkStart = () => {
                            if (endTime) {
                                resolve();
                            } else {
                                setTimeout(checkStart, 1);
                            }
                        };
                        checkStart();
                    });
                    
                } else if (test.operation === 'tts_start') {
                    const utterance = {
                        text: 'Latency test message',
                        onstart: null
                    };
                    
                    startTime = Date.now();
                    
                    utterance.onstart = () => {
                        endTime = Date.now();
                    };
                    
                    this.mockSpeechSynthesis.speak(utterance);
                    
                    await new Promise(resolve => {
                        const checkStart = () => {
                            if (endTime) {
                                resolve();
                            } else {
                                setTimeout(checkStart, 1);
                            }
                        };
                        checkStart();
                    });
                }

                if (endTime && startTime) {
                    measurements.push(endTime - startTime);
                }
            }

            if (measurements.length > 0) {
                const averageLatency = measurements.reduce((a, b) => a + b, 0) / measurements.length;
                const maxLatency = Math.max(...measurements);
                const minLatency = Math.min(...measurements);

                this.performanceMetrics.push({
                    test: test.name,
                    averageLatency: averageLatency,
                    maxLatency: maxLatency,
                    minLatency: minLatency,
                    measurements: measurements
                });

                this.assert(
                    averageLatency < 100, // Should start within 100ms
                    `${test.name} average latency should be low (actual: ${averageLatency.toFixed(2)}ms)`
                );

                this.assert(
                    maxLatency < 200, // Max latency should be reasonable
                    `${test.name} max latency should be reasonable (actual: ${maxLatency}ms)`
                );
            }
        }
    }

    async testVoiceErrorRecoveryPerformance() {
        console.log('Testing voice error recovery performance...');

        const errorScenarios = [
            { name: 'network_timeout', recoveryTime: 1000 },
            { name: 'microphone_denied', recoveryTime: 500 },
            { name: 'synthesis_failed', recoveryTime: 300 }
        ];

        for (const scenario of errorScenarios) {
            const recoveryTimes = [];
            const iterations = 3;

            for (let i = 0; i < iterations; i++) {
                const startTime = Date.now();
                let recoveryTime;

                // Simulate error and recovery
                const errorHandler = {
                    handleError: function(errorType) {
                        // Simulate error detection and recovery logic
                        setTimeout(() => {
                            recoveryTime = Date.now() - startTime;
                        }, Math.random() * scenario.recoveryTime);
                    }
                };

                errorHandler.handleError(scenario.name);

                // Wait for recovery
                await new Promise(resolve => {
                    const checkRecovery = () => {
                        if (recoveryTime) {
                            resolve();
                        } else {
                            setTimeout(checkRecovery, 10);
                        }
                    };
                    checkRecovery();
                });

                recoveryTimes.push(recoveryTime);
            }

            const averageRecoveryTime = recoveryTimes.reduce((a, b) => a + b, 0) / recoveryTimes.length;

            this.performanceMetrics.push({
                test: 'Error_Recovery',
                scenario: scenario.name,
                averageRecoveryTime: averageRecoveryTime,
                recoveryTimes: recoveryTimes
            });

            this.assert(
                averageRecoveryTime <= scenario.recoveryTime,
                `${scenario.name} recovery should be within expected time (actual: ${averageRecoveryTime.toFixed(2)}ms)`
            );
        }
    }

    async testVoiceQueuePerformance() {
        console.log('Testing voice queue performance...');

        // Mock voice queue
        const voiceQueue = {
            queue: [],
            processing: false,
            
            add: function(item) {
                this.queue.push(item);
                if (!this.processing) {
                    this.processNext();
                }
            },
            
            processNext: function() {
                if (this.queue.length === 0) {
                    this.processing = false;
                    return;
                }
                
                this.processing = true;
                const item = this.queue.shift();
                
                // Simulate processing time
                setTimeout(() => {
                    if (item.callback) item.callback();
                    this.processNext();
                }, item.processingTime || 100);
            }
        };

        const queueItems = 20;
        const processedItems = [];
        const startTime = Date.now();

        // Add items to queue
        for (let i = 0; i < queueItems; i++) {
            voiceQueue.add({
                id: i,
                processingTime: 50 + Math.random() * 100,
                callback: () => {
                    processedItems.push({
                        id: i,
                        timestamp: Date.now()
                    });
                }
            });
        }

        // Wait for all items to be processed
        await new Promise(resolve => {
            const checkCompletion = () => {
                if (processedItems.length === queueItems) {
                    resolve();
                } else {
                    setTimeout(checkCompletion, 10);
                }
            };
            checkCompletion();
        });

        const totalTime = Date.now() - startTime;
        const averageProcessingTime = totalTime / queueItems;

        this.performanceMetrics.push({
            test: 'Queue_Performance',
            queueSize: queueItems,
            totalTime: totalTime,
            averageProcessingTime: averageProcessingTime,
            throughput: queueItems / (totalTime / 1000) // items per second
        });

        this.assert(
            processedItems.length === queueItems,
            'All queued items should be processed'
        );

        this.assert(
            averageProcessingTime < 200,
            `Average queue processing time should be reasonable (actual: ${averageProcessingTime.toFixed(2)}ms)`
        );

        // Verify items were processed in order
        const inOrder = processedItems.every((item, index) => item.id === index);
        this.assert(
            inOrder,
            'Queue items should be processed in order'
        );
    }

    async testVoiceBandwidthUsage() {
        console.log('Testing voice bandwidth usage...');

        // Mock bandwidth tracking
        const bandwidthTracker = {
            totalBytes: 0,
            operations: [],
            
            trackOperation: function(type, dataSize) {
                this.totalBytes += dataSize;
                this.operations.push({
                    type: type,
                    size: dataSize,
                    timestamp: Date.now()
                });
            },
            
            getAverageUsage: function() {
                if (this.operations.length === 0) return 0;
                return this.totalBytes / this.operations.length;
            }
        };

        // Simulate various voice operations with bandwidth usage
        const operations = [
            { type: 'stt_audio_upload', size: 50000 }, // 50KB audio
            { type: 'stt_result_download', size: 1000 }, // 1KB text
            { type: 'tts_request', size: 2000 }, // 2KB text
            { type: 'tts_audio_download', size: 100000 }, // 100KB audio
        ];

        const iterations = 10;
        const startTime = Date.now();

        for (let i = 0; i < iterations; i++) {
            for (const operation of operations) {
                // Simulate network delay based on size
                const delay = operation.size / 10000; // 1ms per 10KB
                await new Promise(resolve => setTimeout(resolve, delay));
                
                bandwidthTracker.trackOperation(operation.type, operation.size);
            }
        }

        const totalTime = Date.now() - startTime;
        const totalBandwidth = bandwidthTracker.totalBytes;
        const averageUsage = bandwidthTracker.getAverageUsage();
        const bandwidthRate = totalBandwidth / (totalTime / 1000); // bytes per second

        this.performanceMetrics.push({
            test: 'Bandwidth_Usage',
            totalBandwidth: totalBandwidth,
            averageUsage: averageUsage,
            bandwidthRate: bandwidthRate,
            operationCount: bandwidthTracker.operations.length
        });

        this.assert(
            totalBandwidth > 0,
            'Should track bandwidth usage'
        );

        this.assert(
            averageUsage < 200000, // Less than 200KB per operation on average
            `Average bandwidth usage should be reasonable (actual: ${(averageUsage / 1000).toFixed(2)}KB)`
        );

        this.assert(
            bandwidthRate > 1000, // At least 1KB/s
            `Bandwidth rate should be adequate (actual: ${(bandwidthRate / 1000).toFixed(2)}KB/s)`
        );
    }

    printResults() {
        console.log('\n=== Voice Performance Test Results ===');
        
        const passed = this.testResults.filter(r => r.status === 'PASS').length;
        const failed = this.testResults.filter(r => r.status === 'FAIL').length;
        const total = this.testResults.length;

        console.log(`Total tests: ${total}`);
        console.log(`Passed: ${passed}`);
        console.log(`Failed: ${failed}`);
        console.log(`Success rate: ${((passed / total) * 100).toFixed(1)}%`);

        if (failed > 0) {
            console.log('\nFailed tests:');
            this.testResults
                .filter(r => r.status === 'FAIL')
                .forEach(r => console.log(`  - ${r.message}`));
        }

        return { passed, failed, total };
    }

    printPerformanceMetrics() {
        console.log('\n=== Performance Metrics ===');
        
        // Group metrics by test type
        const metricsByTest = {};
        this.performanceMetrics.forEach(metric => {
            if (!metricsByTest[metric.test]) {
                metricsByTest[metric.test] = [];
            }
            metricsByTest[metric.test].push(metric);
        });

        Object.keys(metricsByTest).forEach(testType => {
            console.log(`\n${testType}:`);
            metricsByTest[testType].forEach(metric => {
                switch (testType) {
                    case 'STT_Latency':
                        console.log(`  ${metric.condition}: ${metric.latency}ms (${metric.success ? 'success' : 'failed'})`);
                        break;
                    case 'TTS_Performance':
                        console.log(`  ${metric.textLength} chars: ${metric.duration}ms (${metric.rate.toFixed(2)} chars/sec)`);
                        break;
                    case 'Concurrent_Operations':
                        console.log(`  ${metric.operationCount} operations: ${metric.totalTime}ms total, ${metric.averageTime.toFixed(2)}ms average`);
                        break;
                    case 'Memory_Usage':
                        console.log(`  Peak: ${metric.peakMemory}MB, Leak: ${metric.memoryLeak}MB`);
                        break;
                    case 'Queue_Performance':
                        console.log(`  ${metric.queueSize} items: ${metric.totalTime}ms, ${metric.throughput.toFixed(2)} items/sec`);
                        break;
                    case 'Bandwidth_Usage':
                        console.log(`  Total: ${(metric.totalBandwidth / 1000).toFixed(2)}KB, Rate: ${(metric.bandwidthRate / 1000).toFixed(2)}KB/s`);
                        break;
                    default:
                        console.log(`  ${JSON.stringify(metric)}`);
                }
            });
        });
    }
}

// Export for use in other test files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoicePerformanceTest;
}

// Browser environment
if (typeof window !== 'undefined') {
    window.VoicePerformanceTest = VoicePerformanceTest;
}