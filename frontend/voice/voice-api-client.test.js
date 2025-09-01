/**
 * Tests for VoiceAPIClient
 * Tests backend integration, session validation, error handling, and security measures
 */

// Mock fetch for testing
global.fetch = jest.fn();

// Import the class
const VoiceAPIClient = require('./voice-api-client.js');

describe('VoiceAPIClient', () => {
    let client;
    
    beforeEach(() => {
        client = new VoiceAPIClient('http://localhost:8000');
        fetch.mockClear();
        console.log = jest.fn(); // Mock console.log
        console.error = jest.fn(); // Mock console.error
        console.warn = jest.fn(); // Mock console.warn
    });

    afterEach(() => {
        client.cleanup();
    });

    describe('Initialization', () => {
        test('should initialize with default configuration', () => {
            const newClient = new VoiceAPIClient();
            expect(newClient.baseURL).toBe('');
            expect(newClient.sessionId).toBeNull();
            expect(newClient.isValidated).toBe(false);
            expect(newClient.retryConfig.maxRetries).toBe(3);
        });

        test('should initialize with custom base URL', () => {
            const customClient = new VoiceAPIClient('https://api.example.com');
            expect(customClient.baseURL).toBe('https://api.example.com');
        });

        test('should initialize successfully with valid session', async () => {
            // Mock successful session validation
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ username: 'testuser', user_id: '123' })
            });

            const result = await client.initialize('valid-session-id');
            
            expect(result).toBe(true);
            expect(client.sessionId).toBe('valid-session-id');
            expect(client.isValidated).toBe(true);
            expect(fetch).toHaveBeenCalledWith('http://localhost:8000/me', {
                method: 'GET',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' }
            });
        });

        test('should fail initialization with invalid session', async () => {
            // Mock failed session validation
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 401
            });

            const result = await client.initialize('invalid-session-id');
            
            expect(result).toBe(false);
            expect(client.isValidated).toBe(false);
        });

        test('should handle network errors during initialization', async () => {
            // Mock network error
            fetch.mockRejectedValueOnce(new Error('Network error'));

            const result = await client.initialize('session-id');
            
            expect(result).toBe(false);
            expect(client.isValidated).toBe(false);
        });
    });

    describe('Session Validation', () => {
        test('should validate session successfully', async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ username: 'testuser' })
            });

            const result = await client.validateSession();
            
            expect(result).toBe(true);
            expect(fetch).toHaveBeenCalledWith('http://localhost:8000/me', {
                method: 'GET',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' }
            });
        });

        test('should handle expired session', async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 401
            });

            const result = await client.validateSession();
            
            expect(result).toBe(false);
        });

        test('should handle server errors during validation', async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 500
            });

            const result = await client.validateSession();
            
            expect(result).toBe(false);
        });

        test('should refresh session validation', async () => {
            // First call fails, second succeeds
            fetch
                .mockResolvedValueOnce({ ok: false, status: 401 })
                .mockResolvedValueOnce({ 
                    ok: true, 
                    json: async () => ({ username: 'testuser' }) 
                });

            client.isValidated = true;
            
            const result1 = await client.refreshSession();
            expect(result1).toBe(false);
            expect(client.isValidated).toBe(false);

            const result2 = await client.refreshSession();
            expect(result2).toBe(true);
            expect(client.isValidated).toBe(true);
        });
    });

    describe('Message Sending', () => {
        beforeEach(() => {
            client.isValidated = true;
            client.sessionId = 'test-session';
        });

        test('should send message successfully', async () => {
            const mockResponse = {
                summary: 'AI response message',
                topic: 'General Support',
                sources: ['knowledge_base'],
                tools_used: ['ContextRetriever'],
                confidence_score: 0.95,
                execution_time: 1.2,
                content_type: 'plain_text'
            };

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse
            });

            const result = await client.sendMessage('Hello, I need help');
            
            expect(result).toEqual({
                message: 'AI response message',
                topic: 'General Support',
                sources: ['knowledge_base'],
                tools_used: ['ContextRetriever'],
                confidence_score: 0.95,
                execution_time: 1.2,
                content_type: 'plain_text'
            });

            expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ query: 'Hello, I need help' })
            });
        });

        test('should reject empty messages', async () => {
            await expect(client.sendMessage('')).rejects.toThrow('Message cannot be empty');
            await expect(client.sendMessage('   ')).rejects.toThrow('Message cannot be empty');
            await expect(client.sendMessage(null)).rejects.toThrow('Message cannot be empty');
        });

        test('should reject when client not initialized', async () => {
            client.isValidated = false;
            
            await expect(client.sendMessage('test')).rejects.toThrow('Client not initialized or session invalid');
        });

        test('should sanitize malicious input', async () => {
            const maliciousInput = '<script>alert("xss")</script>Hello javascript:void(0)';
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ summary: 'Response' })
            });

            await client.sendMessage(maliciousInput);
            
            const callArgs = fetch.mock.calls[0][1];
            const body = JSON.parse(callArgs.body);
            
            expect(body.query).toBe('Hello');
            expect(body.query).not.toContain('<script>');
            expect(body.query).not.toContain('javascript:');
        });

        test('should handle long messages by truncating', async () => {
            const longMessage = 'a'.repeat(2000);
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ summary: 'Response' })
            });

            await client.sendMessage(longMessage);
            
            const callArgs = fetch.mock.calls[0][1];
            const body = JSON.parse(callArgs.body);
            
            expect(body.query.length).toBe(1000);
        });

        test('should handle API response with missing fields', async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ summary: 'Basic response' })
            });

            const result = await client.sendMessage('test');
            
            expect(result).toEqual({
                message: 'Basic response',
                topic: 'General',
                sources: [],
                tools_used: [],
                confidence_score: 0.0,
                execution_time: 0.0,
                content_type: 'plain_text'
            });
        });

        test('should handle invalid API response format', async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ invalid: 'response' })
            });

            await expect(client.sendMessage('test')).rejects.toThrow('Invalid response format from API');
        });
    });

    describe('Error Handling', () => {
        beforeEach(() => {
            client.isValidated = true;
        });

        test('should handle 401 unauthorized errors', async () => {
            // Mock all retry attempts to return 401
            fetch.mockResolvedValue({
                ok: false,
                status: 401,
                json: async () => ({ detail: 'Unauthorized' })
            });

            await expect(client.sendMessage('test')).rejects.toThrow('Your session has expired');
            expect(client.isValidated).toBe(false);
        }, 10000);

        test('should handle 403 forbidden errors', async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 403,
                json: async () => ({ detail: 'Forbidden' })
            });

            await expect(client.sendMessage('test')).rejects.toThrow('You don\'t have permission');
        });

        test('should handle 429 rate limit errors', async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 429,
                json: async () => ({ detail: 'Too many requests' })
            });

            await expect(client.sendMessage('test')).rejects.toThrow('Too many requests');
        });

        test('should handle 500 server errors', async () => {
            // Mock all retry attempts to return 500
            fetch.mockResolvedValue({
                ok: false,
                status: 500,
                json: async () => ({ detail: 'Internal server error' })
            });

            await expect(client.sendMessage('test')).rejects.toThrow('Server error occurred');
        }, 10000);

        test('should handle network connectivity errors', async () => {
            fetch.mockRejectedValueOnce(new Error('Failed to fetch'));

            await expect(client.sendMessage('test')).rejects.toThrow('Unable to connect to the server');
        });

        test('should handle timeout errors', async () => {
            fetch.mockRejectedValueOnce(new Error('Request timeout'));

            await expect(client.sendMessage('test')).rejects.toThrow('Request timed out');
        });
    });

    describe('Retry Logic', () => {
        beforeEach(() => {
            client.isValidated = true;
            // Speed up tests by reducing retry delays
            client.retryConfig.baseDelay = 10;
            client.retryConfig.maxDelay = 50;
        });

        test('should retry on server errors', async () => {
            fetch
                .mockResolvedValueOnce({ ok: false, status: 500 })
                .mockResolvedValueOnce({ ok: false, status: 502 })
                .mockResolvedValueOnce({ 
                    ok: true, 
                    json: async () => ({ summary: 'Success after retries' }) 
                });

            const result = await client.sendMessage('test');
            
            expect(result.message).toBe('Success after retries');
            expect(fetch).toHaveBeenCalledTimes(3);
        });

        test('should not retry on client errors (except 401)', async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 400,
                json: async () => ({ detail: 'Bad request' })
            });

            await expect(client.sendMessage('test')).rejects.toThrow();
            expect(fetch).toHaveBeenCalledTimes(1);
        });

        test('should retry on 401 errors', async () => {
            fetch
                .mockResolvedValueOnce({ ok: false, status: 401 })
                .mockResolvedValueOnce({ ok: false, status: 401 })
                .mockResolvedValueOnce({ ok: false, status: 401 })
                .mockResolvedValueOnce({ ok: false, status: 401 });

            await expect(client.sendMessage('test')).rejects.toThrow('Your session has expired');
            expect(fetch).toHaveBeenCalledTimes(4); // Initial + 3 retries
        });

        test('should give up after max retries', async () => {
            fetch.mockResolvedValue({ ok: false, status: 500 });

            await expect(client.sendMessage('test')).rejects.toThrow();
            expect(fetch).toHaveBeenCalledTimes(4); // Initial + 3 retries
        });
    });

    describe('Security', () => {
        test('should sanitize script tags', () => {
            const malicious = '<script>alert("xss")</script>Hello';
            const sanitized = client.sanitizeInput(malicious);
            expect(sanitized).toBe('Hello');
        });

        test('should sanitize javascript protocols', () => {
            const malicious = 'javascript:alert("xss") Hello';
            const sanitized = client.sanitizeInput(malicious);
            expect(sanitized).toBe('Hello');
        });

        test('should handle non-string input', () => {
            expect(client.sanitizeInput(null)).toBe('');
            expect(client.sanitizeInput(undefined)).toBe('');
            expect(client.sanitizeInput(123)).toBe('');
            expect(client.sanitizeInput({})).toBe('');
        });

        test('should limit input length', () => {
            const longInput = 'a'.repeat(2000);
            const sanitized = client.sanitizeInput(longInput);
            expect(sanitized.length).toBe(1000);
        });

        test('should trim whitespace', () => {
            const input = '   Hello World   ';
            const sanitized = client.sanitizeInput(input);
            expect(sanitized).toBe('Hello World');
        });
    });

    describe('Utility Methods', () => {
        test('should return session status', () => {
            client.sessionId = 'test-session';
            client.isValidated = true;
            
            const status = client.getSessionStatus();
            
            expect(status).toEqual({
                isValidated: true,
                sessionId: 'test-session',
                hasSession: true
            });
        });

        test('should return configuration', () => {
            const config = client.getConfig();
            
            expect(config).toHaveProperty('baseURL');
            expect(config).toHaveProperty('retryConfig');
            expect(config).toHaveProperty('isValidated');
            expect(config).toHaveProperty('hasSession');
        });

        test('should cleanup resources', () => {
            client.sessionId = 'test-session';
            client.isValidated = true;
            
            client.cleanup();
            
            expect(client.sessionId).toBeNull();
            expect(client.isValidated).toBe(false);
        });

        test('should sleep for specified duration', async () => {
            const start = Date.now();
            await client.sleep(50);
            const end = Date.now();
            
            expect(end - start).toBeGreaterThanOrEqual(45); // Allow some variance
        });
    });

    describe('Integration Scenarios', () => {
        test('should handle complete conversation flow', async () => {
            // Initialize
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ username: 'testuser' })
            });

            await client.initialize('session-123');
            expect(client.isValidated).toBe(true);

            // Send first message
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    summary: 'Hello! How can I help you today?',
                    topic: 'Greeting',
                    confidence_score: 0.9
                })
            });

            const response1 = await client.sendMessage('Hello');
            expect(response1.message).toBe('Hello! How can I help you today?');

            // Send follow-up message
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    summary: 'I can help you with billing questions.',
                    topic: 'Billing Support',
                    tools_used: ['SupportKnowledgeBase']
                })
            });

            const response2 = await client.sendMessage('I have a billing question');
            expect(response2.message).toBe('I can help you with billing questions.');
            expect(response2.tools_used).toContain('SupportKnowledgeBase');
        });

        test('should handle session expiration during conversation', async () => {
            client.isValidated = true;
            client.sessionId = 'expired-session';

            // First message succeeds
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ summary: 'First response' })
            });

            const response1 = await client.sendMessage('First message');
            expect(response1.message).toBe('First response');

            // Second message fails with session expired (4 times for retries)
            fetch.mockResolvedValue({
                ok: false,
                status: 401,
                json: async () => ({ detail: 'Session expired' })
            });

            await expect(client.sendMessage('Second message')).rejects.toThrow('Your session has expired');
            expect(client.isValidated).toBe(false);
        }, 10000);
    });
});