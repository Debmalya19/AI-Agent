/**
 * Simple Authentication Fix
 * Direct approach to handle login without complex dependencies
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('Simple auth fix loaded');
    
    // Override the existing login form handler
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        // Remove existing event listeners by cloning the element
        const newLoginForm = loginForm.cloneNode(true);
        loginForm.parentNode.replaceChild(newLoginForm, loginForm);
        
        // Add our simple login handler
        newLoginForm.addEventListener('submit', handleSimpleLogin);
        console.log('Simple login handler attached');
    }
});

async function handleSimpleLogin(e) {
    e.preventDefault();
    console.log('Simple login handler triggered');
    
    const emailField = document.getElementById('email');
    const passwordField = document.getElementById('password');
    const loginError = document.getElementById('login-error');
    const submitButton = e.target.querySelector('button[type="submit"]');
    
    // Clear previous errors
    if (loginError) {
        loginError.classList.add('d-none');
        loginError.textContent = '';
    }
    
    const email = emailField ? emailField.value.trim() : '';
    const password = passwordField ? passwordField.value : '';
    
    if (!email || !password) {
        showError('Please enter both email and password.');
        return;
    }
    
    // Show loading state
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Logging in...';
    }
    
    try {
        console.log('Sending login request...');
        
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                email: email,
                password: password
            })
        });
        
        console.log('Login response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('Login response data:', data);
            
            if (data.success && data.user) {
                console.log('Login successful, processing...');
                
                // Store authentication data
                const token = data.token || data.access_token || 'session_cookie_auth';
                const user = data.user || {};
                
                // Store tokens (even if using cookie-based auth)
                localStorage.setItem('authToken', token);
                localStorage.setItem('admin_session_token', token);
                localStorage.setItem('username', user.username || user.email || 'admin');
                localStorage.setItem('userEmail', user.email || email);
                localStorage.setItem('isAdmin', user.is_admin ? 'true' : 'false');
                
                console.log('Authentication data stored, hiding modal...');
                
                // Hide the login modal immediately
                hideLoginModal();
                
                // Update UI
                updateUserInterface(user);
                
                // Show dashboard content
                showDashboardContent();
                
                console.log('Login process completed');
                
            } else {
                console.error('Login failed: Invalid response');
                showError(data.message || 'Login failed - invalid response');
            }
        } else {
            const errorText = await response.text();
            console.error('Login request failed:', errorText);
            showError(`Login failed: ${response.status} - ${errorText}`);
        }
        
    } catch (error) {
        console.error('Login error:', error);
        showError(`Login error: ${error.message}`);
    } finally {
        // Reset loading state
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = 'Login';
        }
    }
}

function hideLoginModal() {
    console.log('Hiding login modal...');
    
    const loginModalElement = document.getElementById('loginModal');
    if (loginModalElement) {
        // Try Bootstrap modal methods first
        try {
            const loginModal = bootstrap.Modal.getInstance(loginModalElement);
            if (loginModal) {
                loginModal.hide();
                console.log('Modal hidden using Bootstrap instance');
            }
        } catch (e) {
            console.log('Bootstrap modal instance not found, using direct methods');
        }
        
        // Force hide using direct DOM manipulation
        loginModalElement.style.display = 'none';
        loginModalElement.classList.remove('show');
        loginModalElement.setAttribute('aria-hidden', 'true');
        loginModalElement.removeAttribute('aria-modal');
        
        // Clean up modal state
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
        
        // Remove backdrop
        const backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach(backdrop => {
            backdrop.remove();
            console.log('Backdrop removed');
        });
        
        console.log('Modal hidden using direct DOM manipulation');
    }
}

function showDashboardContent() {
    console.log('Showing dashboard content...');
    
    // Ensure modal is hidden
    hideLoginModal();
    
    // Show main content areas
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('main');
    const dashboardContent = document.getElementById('content-dashboard');
    
    if (sidebar) {
        sidebar.style.display = 'block';
        console.log('Sidebar shown');
    }
    
    if (mainContent) {
        mainContent.style.display = 'block';
        console.log('Main content shown');
    }
    
    if (dashboardContent) {
        dashboardContent.classList.remove('d-none');
        console.log('Dashboard content shown');
    }
    
    // Load dashboard data if function exists
    setTimeout(() => {
        if (typeof loadDashboardData === 'function') {
            console.log('Loading dashboard data...');
            loadDashboardData();
        } else if (typeof initializeDashboard === 'function') {
            console.log('Initializing dashboard...');
            initializeDashboard();
        } else {
            console.log('No dashboard initialization function found');
        }
    }, 100);
}

function updateUserInterface(user) {
    console.log('Updating user interface...', user);
    
    const usernameElements = document.querySelectorAll('#username, #user-name');
    const displayName = user.username || user.email || 'Admin User';
    
    usernameElements.forEach(el => {
        if (el) {
            el.textContent = displayName;
            console.log('Username updated:', displayName);
        }
    });
    
    // Update admin-specific UI elements
    if (user.is_admin) {
        document.body.classList.add('admin-user');
        console.log('Admin user class added');
    }
}

function showError(message) {
    console.error('Login error:', message);
    
    const loginError = document.getElementById('login-error');
    if (loginError) {
        loginError.textContent = message;
        loginError.classList.remove('d-none');
        loginError.style.display = 'block';
    } else {
        // Fallback to alert if no error element
        alert(message);
    }
}

// Export functions for global access
window.hideLoginModal = hideLoginModal;
window.showDashboardContent = showDashboardContent;
window.handleSimpleLogin = handleSimpleLogin;

console.log('Simple auth fix script loaded successfully');