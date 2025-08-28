# Comprehensive Voice Features Test Suite

This directory contains a comprehensive test suite for all voice assistant features, covering unit tests, integration tests, end-to-end tests, accessibility tests, and performance tests.

## Test Structure

### Backend Tests (Python)
- **Unit Tests**: Test individual voice models and API endpoints
- **Integration Tests**: Test voice features with database operations and full system integration
- **Performance Tests**: Test voice processing under various network conditions and load scenarios

### Frontend Tests (JavaScript)
- **Unit Tests**: Test voice JavaScript classes with mocked Web Speech API
- **End-to-End Tests**: Test complete voice conversation flows
- **Accessibility Tests**: Test screen reader compatibility and keyboard navigation
- **Performance Tests**: Test voice processing performance under various conditions

## Running Tests

### Backend Tests

#### Option 1: Run All Backend Tests
```bash
# From the ai-agent directory
python scripts/run_comprehensive_voice_tests.py
```

#### Option 2: Run Specific Test Categories
```bash
# Run only backend tests
python scripts/run_comprehensive_voice_tests.py --categories backend

# Run only integration tests
python scripts/run_comprehensive_voice_tests.py --categories integration

# Run only performance tests
python scripts/run_comprehensive_voice_tests.py --categories performance
```

#### Option 3: Run Individual Test Files
```bash
# Run specific test file
python -m pytest tests/test_comprehensive_voice_suite.py -v

# Run with coverage
python -m pytest tests/test_voice_api.py --cov=backend.voice_api

# Run performance tests only
python -m pytest tests/test_comprehensive_voice_suite.py -k "performance" -v
```

### Frontend Tests

#### Option 1: Browser-Based Test Runner (Recommended)
1. Start a local web server in the `ai-agent/frontend` directory:
   ```bash
   # Using Python
   cd ai-agent/frontend
   python -m http.server 8000
   
   # Or using Node.js
   npx http-server -p 8000
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:8000/tests/comprehensive-voice-tests.html
   ```

3. Click "Run All Tests" to execute the complete test suite

#### Option 2: Run Individual Test Suites
In the browser test interface, you can run specific test categories:
- **Unit Tests Only**: Tests individual voice classes
- **E2E Tests Only**: Tests complete conversation flows
- **Accessibility Tests**: Tests screen reader and keyboard navigation
- **Performance Tests**: Tests performance under various conditions

#### Option 3: Command Line (Node.js)
```bash
# From the ai-agent/frontend/tests directory
node run-voice-tests.js
```

## Test Categories

### 1. Unit Tests
Test individual components in isolation:
- `VoiceCapabilities` - Browser capability detection
- `VoiceSettings` - User preference management
- `VoiceController` - Core voice processing logic
- `VoiceUI` - User interface components
- Voice API endpoints
- Voice data models

### 2. Integration Tests
Test components working together:
- Voice API with database operations
- Voice settings persistence across sessions
- Voice analytics logging and retrieval
- Error handling and recovery flows

### 3. End-to-End Tests
Test complete user workflows:
- Complete voice conversation (STT → Chat → TTS)
- Voice with recommended questions
- Voice with multi-tool responses
- Voice error recovery scenarios
- Voice queue management
- Voice interruption handling

### 4. Accessibility Tests
Test compliance with accessibility standards:
- Screen reader compatibility
- Keyboard navigation
- ARIA labels and roles
- Focus management
- High contrast mode support
- Reduced motion support
- Voice status announcements

### 5. Performance Tests
Test performance under various conditions:
- STT latency under different network conditions
- TTS performance with various text lengths
- Concurrent voice operations
- Memory usage and leak detection
- Voice queue performance
- Bandwidth usage optimization

## Test Requirements Coverage

The test suite covers all requirements from the voice assistant specification:

### Requirement 1.1-1.6 (Voice Input)
- ✅ Voice recording start/stop
- ✅ Visual feedback during recording
- ✅ Speech-to-text conversion
- ✅ Transcription display and editing
- ✅ Message sending integration

### Requirement 2.1-2.6 (Voice Output)
- ✅ Text-to-speech playback
- ✅ Auto-play mode
- ✅ Playback controls
- ✅ Sequential response handling
- ✅ Audio interruption management

### Requirement 3.1-3.6 (Voice Settings)
- ✅ Settings CRUD operations
- ✅ Voice preference persistence
- ✅ Settings validation
- ✅ Graceful fallback modes

### Requirement 4.1-4.4 (Chat Integration)
- ✅ Recommended questions with voice
- ✅ Multi-tool response handling
- ✅ Session management integration
- ✅ Error notification systems

### Requirement 5.1-5.6 (Accessibility)
- ✅ Mobile device compatibility
- ✅ Browser compatibility detection
- ✅ Permission handling
- ✅ Visual accessibility indicators
- ✅ Alternative input methods
- ✅ Audio quality detection

### Requirement 6.1-6.6 (Analytics & Monitoring)
- ✅ Usage metrics logging
- ✅ Error tracking and reporting
- ✅ Performance monitoring
- ✅ Privacy compliance
- ✅ Resource management

## Test Data and Mocks

### Mock Web Speech API
The frontend tests use comprehensive mocks for:
- `SpeechRecognition` - Simulates speech input with configurable results
- `SpeechSynthesis` - Simulates text-to-speech with timing controls
- Network conditions - Simulates various latency and error scenarios

### Test Database
Backend tests use a separate SQLite test database:
- Automatically created and cleaned up
- Isolated from production data
- Supports concurrent test execution

### Mock Analytics
Performance tests include mock analytics to track:
- Processing times
- Memory usage
- Network bandwidth
- Error rates
- User interaction patterns

## Continuous Integration

### GitHub Actions Integration
Add this workflow to `.github/workflows/voice-tests.yml`:

```yaml
name: Voice Features Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run backend tests
        run: python scripts/run_comprehensive_voice_tests.py --categories backend integration
  
  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '16'
      - name: Install dependencies
        run: npm install -g http-server
      - name: Run frontend tests
        run: |
          cd ai-agent/frontend
          http-server -p 8000 &
          # Add headless browser testing here
```

## Performance Benchmarks

### Expected Performance Metrics
- **STT Latency**: < 300ms under normal network conditions
- **TTS Processing**: > 5 characters per second
- **Memory Usage**: < 100MB peak, < 10MB leak
- **Concurrent Operations**: > 5 operations per second
- **Error Recovery**: < 1 second for common errors

### Performance Monitoring
The test suite tracks and reports:
- Average response times
- Memory usage patterns
- Network bandwidth consumption
- Error rates and recovery times
- User interaction latencies

## Troubleshooting

### Common Issues

#### Backend Tests Failing
1. **Database Connection Issues**:
   ```bash
   # Ensure test database is writable
   chmod 755 tests/
   ```

2. **Import Errors**:
   ```bash
   # Ensure Python path includes project root
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

#### Frontend Tests Failing
1. **Web Speech API Not Available**:
   - Tests use mocks, but ensure browser supports the APIs
   - Use Chrome/Edge for best compatibility

2. **CORS Issues**:
   - Serve files from a local web server, not file:// protocol
   - Use `http-server` or similar tool

#### Performance Tests Inconsistent
1. **System Load**:
   - Run tests on a quiet system
   - Close unnecessary applications

2. **Network Conditions**:
   - Tests simulate network conditions
   - Actual network shouldn't affect results

### Debug Mode
Enable verbose output for debugging:

```bash
# Backend tests with verbose output
python scripts/run_comprehensive_voice_tests.py --verbose

# Frontend tests with debug logging
# Open browser console to see detailed logs
```

## Contributing

### Adding New Tests

#### Backend Tests
1. Create test file in `tests/` directory
2. Follow naming convention: `test_voice_*.py`
3. Use pytest fixtures for database setup
4. Include performance assertions where relevant

#### Frontend Tests
1. Create test file in `frontend/tests/` directory
2. Follow naming convention: `voice-*.test.js`
3. Use mock Web Speech API classes
4. Include accessibility checks

### Test Guidelines
- **Comprehensive Coverage**: Test both happy path and error scenarios
- **Performance Aware**: Include timing assertions for critical operations
- **Accessibility First**: Ensure all UI tests include accessibility checks
- **Mock External Dependencies**: Use mocks for Web APIs and network calls
- **Clean Up**: Properly clean up resources in test teardown

## Reporting Issues

When reporting test failures, include:
1. Test category (backend/frontend/integration/etc.)
2. Specific test file and function
3. Error message and stack trace
4. System information (OS, browser, Python version)
5. Steps to reproduce

## License

This test suite is part of the AI Agent Voice Assistant project and follows the same license terms.