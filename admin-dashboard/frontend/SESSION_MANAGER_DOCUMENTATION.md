# Enhanced Session Manager Documentation

## Overview

The Enhanced Session Manager is a robust JavaScript class designed to handle user authentication sessions with multiple storage strategies, automatic validation, recovery mechanisms, and cross-browser compatibility. It addresses the admin dashboard login issues by providing reliable session management with comprehensive error handling and debugging capabilities.

## Key Features

### 1. Multiple Storage Strategies
- **localStorage**: Persistent storage across browser sessions
- **sessionStorage**: Storage for current browser session only
- **Cookies**: HTTP cookie-based storage with expiration
- **Fallback Strategy**: Automatically uses available storage methods

### 2. Session Validation and Recovery
- **Periodic Validation**: Automatic session validation every 30 seconds
- **Backend Validation**: Validates sessions with server endpoints
- **Recovery Mechanisms**: Attempts to recover sessions from alternative storage
- **Expiration Handling**: Automatic cleanup of expired sessions

### 3. Cross-Tab Synchronization
- **Real-time Sync**: Sessions synchronized across browser tabs
- **Storage Events**: Listens for changes in other tabs
- **Session Notifications**: Custom events for session changes

### 4. Activity Tracking
- **User Activity**: Tracks mouse, keyboard, and touch events
- **Inactivity Detection**: Automatically detects inactive sessions
- **Configurable Timeouts**: Customizable inactivity thresholds

### 5. Enhanced Error Handling
- **Comprehensive Logging**: Detailed debug information
- **Error Categorization**: Different error types and handling
- **User-Friendly Messages**: Clear error messages for users

## API Reference

### Constructor

```javascript
const sessionManager = new SessionManager();
```

Creates a new session manager instance with default configuration.

### Core Methods

#### `storeSession(authData)`
Stores session data using multiple storage strategies.

**Parameters:**
- `authData` (Object): Authentication data
  - `token` (string): Session token
  - `user` (Object): User information
  - `expires_at` (string): Session expiration time (ISO string)
  - `refresh_token` (string, optional): Refresh token

**Returns:** `Promise<boolean>` - Success status

**Example:**
```javascript
const sessionData = {
    token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
    user: { id: 1, username: 'admin', email: 'admin@example.com' },
    expires_at: '2025-09-18T12:00:00.000Z',
    refresh_token: 'refresh_token_here'
};

const stored = await sessionManager.storeSession(sessionData);
if (stored) {
    console.log('Session stored successfully');
}
```

#### `getSessionToken()`
Retrieves the current session token from any available storage.

**Returns:** `string|null` - Session token or null if not found

**Example:**
```javascript
const token = sessionManager.getSessionToken();
if (token) {
    // Use token for API calls
}
```

#### `getStoredUser()`
Retrieves the stored user information.

**Returns:** `Object|null` - User data or null if not found

**Example:**
```javascript
const user = sessionManager.getStoredUser();
if (user) {
    console.log('Logged in as:', user.username);
}
```

#### `validateStoredSession()`
Validates the current session without backend communication.

**Returns:** `boolean` - Whether session is valid

**Example:**
```javascript
const isValid = sessionManager.validateStoredSession();
if (!isValid) {
    // Redirect to login
}
```

#### `validateAndRecoverSession()`
Validates session and attempts recovery if needed.

**Returns:** `Promise<boolean>` - Whether session is valid after validation/recovery

**Example:**
```javascript
const isValid = await sessionManager.validateAndRecoverSession();
if (!isValid) {
    // Session could not be recovered
}
```

#### `clearSession()`
Clears session data from all storage locations.

**Example:**
```javascript
sessionManager.clearSession();
// User is now logged out
```

#### `getAuthHeaders()`
Gets authentication headers for API requests.

**Returns:** `Object` - Headers object with authentication

**Example:**
```javascript
const headers = sessionManager.getAuthHeaders();
fetch('/api/protected', { headers });
```

#### `authenticatedFetch(url, options)`
Makes an authenticated API request with automatic session validation.

**Parameters:**
- `url` (string): Request URL
- `options` (Object, optional): Fetch options

**Returns:** `Promise<Response>` - Fetch response

**Example:**
```javascript
try {
    const response = await sessionManager.authenticatedFetch('/api/user/profile');
    const data = await response.json();
} catch (error) {
    console.error('Request failed:', error);
}
```

### Diagnostic Methods

#### `getDiagnostics()`
Returns comprehensive diagnostic information.

**Returns:** `Object` - Diagnostic data

**Example:**
```javascript
const diagnostics = sessionManager.getDiagnostics();
console.log('Session valid:', diagnostics.isValid);
console.log('Storage available:', diagnostics.storageAvailable);
```

### Configuration Methods

#### `destroy()`
Cleans up resources and stops all timers.

**Example:**
```javascript
// Clean up when component unmounts
sessionManager.destroy();
```

## Configuration Options

The session manager can be configured by modifying the constructor or instance properties:

```javascript
const sessionManager = new SessionManager();

// Modify validation interval (default: 30 seconds)
sessionManager.validationInterval = 60000; // 1 minute

// Modify inactivity timeout (default: 30 minutes)
sessionManager.maxInactivityTime = 60 * 60 * 1000; // 1 hour

// Modify sync interval (default: 5 seconds)
sessionManager.sessionSyncInterval = 10000; // 10 seconds
```

## Event Handling

The session manager dispatches custom events for important session changes:

### `sessionExpired` Event

Fired when a session expires or becomes invalid.

```javascript
window.addEventListener('sessionExpired', (event) => {
    console.log('Session expired:', event.detail.reason);
    // Redirect to login page
    window.location.href = '/login';
});
```

**Event Detail:**
- `reason` (string): Reason for expiration
  - `'inactivity'`: Session expired due to inactivity
  - `'backend_validation_failed'`: Backend rejected the session
  - `'recovery_failed'`: Session recovery attempts failed
  - `'cleared_in_other_tab'`: Session cleared in another tab

## Storage Event Handling

The session manager automatically handles storage events for cross-tab synchronization:

```javascript
// Storage events are handled automatically
// No manual setup required
```

## Error Handling

The session manager provides comprehensive error handling:

### Debug Mode

Enable debug mode for detailed logging:

```javascript
localStorage.setItem('admin_debug', 'true');
// or
sessionManager.debugMode = true;
```

### Error Categories

1. **Storage Errors**: Issues with localStorage, sessionStorage, or cookies
2. **Network Errors**: API communication failures
3. **Validation Errors**: Session validation failures
4. **Recovery Errors**: Session recovery failures

## Browser Compatibility

The session manager is compatible with:

- **Chrome**: 45+
- **Firefox**: 40+
- **Safari**: 10+
- **Edge**: 12+
- **Internet Explorer**: 11+ (with polyfills)

### Required Browser Features

- `localStorage` and `sessionStorage`
- `fetch` API (or polyfill)
- `CustomEvent` constructor
- `addEventListener` support

## Security Considerations

### Token Storage

- Tokens are stored in multiple locations for reliability
- Sensitive data is not logged in production mode
- Automatic cleanup of expired sessions

### Cross-Site Scripting (XSS) Protection

- Session data is properly escaped when stored
- No direct DOM manipulation with user data
- Secure cookie attributes when available

### Cross-Site Request Forgery (CSRF) Protection

- Tokens are included in request headers
- SameSite cookie attributes when supported
- Proper credential handling

## Performance Considerations

### Memory Usage

- Automatic cleanup of expired data
- Efficient event listener management
- Minimal storage footprint

### Network Usage

- Configurable validation intervals
- Efficient session refresh mechanisms
- Minimal API calls for validation

## Troubleshooting

### Common Issues

1. **Session Not Persisting**
   - Check if storage is available
   - Verify browser settings allow storage
   - Check for storage quota limits

2. **Cross-Tab Sync Not Working**
   - Ensure localStorage is available
   - Check for browser privacy settings
   - Verify storage events are supported

3. **Session Validation Failing**
   - Check network connectivity
   - Verify API endpoints are accessible
   - Check for CORS issues

### Debug Information

Use the diagnostic methods to troubleshoot issues:

```javascript
const diagnostics = sessionManager.getDiagnostics();
console.log('Diagnostics:', diagnostics);

// Check specific issues
if (!diagnostics.storageAvailable.localStorage) {
    console.error('localStorage not available');
}

if (!diagnostics.isValid) {
    console.error('Session is not valid');
}
```

## Integration Examples

### React Integration

```javascript
import { useEffect, useState } from 'react';

function useSessionManager() {
    const [sessionManager] = useState(() => new SessionManager());
    const [isValid, setIsValid] = useState(false);

    useEffect(() => {
        const checkSession = async () => {
            const valid = await sessionManager.validateAndRecoverSession();
            setIsValid(valid);
        };

        checkSession();

        const handleSessionExpired = () => {
            setIsValid(false);
        };

        window.addEventListener('sessionExpired', handleSessionExpired);

        return () => {
            window.removeEventListener('sessionExpired', handleSessionExpired);
            sessionManager.destroy();
        };
    }, [sessionManager]);

    return { sessionManager, isValid };
}
```

### Vue.js Integration

```javascript
export default {
    data() {
        return {
            sessionManager: null,
            isValid: false
        };
    },
    
    async created() {
        this.sessionManager = new SessionManager();
        this.isValid = await this.sessionManager.validateAndRecoverSession();
        
        window.addEventListener('sessionExpired', this.handleSessionExpired);
    },
    
    beforeDestroy() {
        window.removeEventListener('sessionExpired', this.handleSessionExpired);
        if (this.sessionManager) {
            this.sessionManager.destroy();
        }
    },
    
    methods: {
        handleSessionExpired() {
            this.isValid = false;
            this.$router.push('/login');
        }
    }
};
```

### Vanilla JavaScript Integration

```javascript
// Initialize session manager
const sessionManager = new SessionManager();

// Check session on page load
window.addEventListener('load', async () => {
    const isValid = await sessionManager.validateAndRecoverSession();
    if (!isValid) {
        window.location.href = '/login';
    }
});

// Handle session expiration
window.addEventListener('sessionExpired', (event) => {
    alert('Your session has expired. Please log in again.');
    window.location.href = '/login';
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    sessionManager.destroy();
});
```

## Testing

The session manager includes comprehensive test suites:

### Node.js Tests

Run the validation script:

```bash
node validate-session-manager.js
```

### Browser Tests

Open the browser test page:

```
test-session-manager-browser.html
```

### Test Coverage

- Basic session storage and retrieval
- Multiple storage strategy testing
- Session validation and expiration
- Cross-tab synchronization
- Activity tracking
- Error handling and recovery
- Browser compatibility

## Changelog

### Version 2.0.0 (Current)

- Added multiple storage strategies
- Implemented session validation and recovery
- Added cross-tab synchronization
- Enhanced activity tracking
- Improved error handling and debugging
- Added comprehensive test suite
- Enhanced browser compatibility

### Version 1.0.0 (Previous)

- Basic session storage
- Simple token management
- Limited error handling

## Support

For issues or questions regarding the Enhanced Session Manager:

1. Check the troubleshooting section
2. Review the diagnostic information
3. Enable debug mode for detailed logging
4. Check browser compatibility requirements
5. Verify API endpoint availability

## License

This session manager is part of the admin dashboard login fix implementation and follows the same licensing terms as the main project.