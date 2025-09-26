document.addEventListener('DOMContentLoaded', () => {
    // Initialize enhanced authentication service
    let adminAuthService = null;
    let loginSuccessful = false;
    
    // Load required dependencies
    const loadDependencies = async () => {
        const dependencies = [
            'js/session-manager.js',
            'js/auth-error-handler.js',
            'js/api-connectivity-checker.js',
            'js/admin-auth-service.js'
        ];

        for (const dep of dependencies) {
            if (!document.querySelector(`script[src="${dep}"]`)) {
                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = dep;
                    script.onload = resolve;
                    script.onerror = reject;
                    document.head.appendChild(script);
                });
            }
        }

        // Initialize the enhanced auth service
        adminAuthService = new AdminAuthService();
    };

    // Load dependencies and initialize
    loadDependencies().then(() => {
        console.log('Enhanced authentication service loaded');
        // Make adminAuthService globally available
        window.adminAuthService = adminAuthService;
        initializeAuthHandlers();
    }).catch(error => {
        console.error('Failed to load authentication dependencies:', error);
        // Fallback to basic authentication
        initializeBasicAuth();
    });

    function initializeAuthHandlers() {
        const loginForm = document.getElementById('login-form');
        const loginError = document.getElementById('login-error');
        
        // Handle both modal and standalone login forms
        let loginModal = null;
        const loginModalElement = document.getElementById('loginModal') || document.getElementById('login-modal');
        if (loginModalElement) {
            loginModal = new bootstrap.Modal(loginModalElement);
        }

        if (loginForm) {
            loginForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                // Clear previous errors
                clearErrorDisplays();

                const emailField = document.getElementById('email') || document.getElementById('login-email');
                const passwordField = document.getElementById('password') || document.getElementById('login-password');
                
                const credentials = {
                    email: emailField ? emailField.value.trim() : '',
                    username: emailField ? emailField.value.trim() : '', // Support both email and username
                    password: passwordField ? passwordField.value : ''
                };

                // Show loading state
                showLoadingState(true);

                try {
                    let result;
                    
                    // Try enhanced authentication service first
                    if (adminAuthService) {
                        console.log('Using AdminAuthService for login');
                        result = await adminAuthService.login(credentials);
                    } else {
                        console.log('AdminAuthService not available, using direct fetch');
                        // Fallback to direct fetch
                        result = await directLogin(credentials);
                    }

                    if (result.success) {
                        console.log('Login successful, processing...');
                        loginSuccessful = true;
                        
                        // Update UI with user information
                        updateUserInterface(result.user);

                        // Close login modal if it exists
                        if (loginModal) {
                            loginModal.hide();
                        }

                        // Redirect to dashboard
                        handleSuccessfulLogin(result.redirect_url);
                    } else {
                        // Error is already handled by the error handler
                        console.error('Login failed:', result.error || result.message);
                        displayFallbackError(result.message || result.error || 'Login failed');
                    }
                } catch (error) {
                    // Fallback error handling
                    displayFallbackError(error.message || 'An unexpected error occurred during login.');
                    console.error('Login error:', error);
                } finally {
                    showLoadingState(false);
                }
            });
        }

        // Initialize session checking
        initializeSessionManagement();
    }

    function initializeBasicAuth() {
        // Fallback to original authentication logic
        console.warn('Using fallback authentication');
        
        // Load unified API if not already loaded
        if (typeof unifiedApi === 'undefined') {
            const script = document.createElement('script');
            script.src = 'js/unified_api.js';
            document.head.appendChild(script);
        }

        const loginForm = document.getElementById('login-form');
        const loginError = document.getElementById('login-error');
        
        if (loginForm) {
            loginForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                if (loginError) {
                    loginError.classList.add('d-none');
                    loginError.textContent = '';
                }

                const emailField = document.getElementById('email') || document.getElementById('login-email');
                const passwordField = document.getElementById('password') || document.getElementById('login-password');
                
                const email = emailField ? emailField.value.trim() : '';
                const password = passwordField ? passwordField.value : '';

                if (!email || !password) {
                    if (loginError) {
                        loginError.textContent = 'Please enter both email and password.';
                        loginError.classList.remove('d-none');
                    }
                    return;
                }

                try {
                    // Use unified API for login
                    const data = await unifiedApi.login(email, password);

                    if (data.success) {
                        updateUserInterface(data.user);
                        handleSuccessfulLogin('/admin');
                    } else {
                        throw new Error(data.message || 'Login failed');
                    }
                } catch (error) {
                    displayFallbackError(error.message || 'An error occurred during login. Please try again.');
                    console.error('Login error:', error);
                }
            });
        }
    }

    function initializeSessionManagement() {
        // Check if user is already logged in
        if (adminAuthService && adminAuthService.isAuthenticated()) {
            const user = adminAuthService.getCurrentUser();
            if (user) {
                updateUserInterface(user);
                
                // Verify session is still valid
                adminAuthService.verifySession().then(result => {
                    if (!result.valid) {
                        console.log('Session invalid, clearing...');
                        adminAuthService.sessionManager.clearSession();
                        // Optionally redirect to login
                    }
                }).catch(error => {
                    console.error('Session verification failed:', error);
                });
            }
        } else {
            // Fallback session check
            const storedUsername = localStorage.getItem('username');
            if (storedUsername) {
                const usernameElements = document.querySelectorAll('#username, #user-name');
                usernameElements.forEach(el => {
                    if (el) el.textContent = storedUsername;
                });
            }
        }
    }

    // Logout handlers
    const logoutElements = document.querySelectorAll('#nav-logout, #btn-logout, #dropdown-logout');
    logoutElements.forEach(logoutElement => {
        if (logoutElement) {
            logoutElement.addEventListener('click', async (e) => {
                e.preventDefault();
                
                try {
                    if (adminAuthService) {
                        await adminAuthService.logout();
                    } else if (typeof unifiedApi !== 'undefined') {
                        await unifiedApi.logout();
                    } else {
                        // Fallback logout
                        clearAllStoredData();
                    }
                } catch (error) {
                    console.error('Logout error:', error);
                    // Clear storage anyway
                    clearAllStoredData();
                }
                
                window.location.href = '/admin';
            });
        }
    });

    // Utility functions
    function updateUserInterface(user) {
        if (!user) return;
        
        const usernameElements = document.querySelectorAll('#username, #user-name');
        usernameElements.forEach(el => {
            if (el) el.textContent = user.username || user.email || 'User';
        });

        // Update any admin-specific UI elements
        if (user.is_admin) {
            document.body.classList.add('admin-user');
        }
    }

    function handleSuccessfulLogin(redirectUrl) {
        console.log('Handling successful login...');
        
        // Update dashboard authentication state first
        updateDashboardAuthState();

        // Hide login modal if it exists
        const loginModalElement = document.getElementById('loginModal') || document.getElementById('login-modal');
        if (loginModalElement) {
            const loginModal = bootstrap.Modal.getInstance(loginModalElement);
            if (loginModal) {
                loginModal.hide();
            }
            
            // Force hide modal immediately
            loginModalElement.style.display = 'none';
            loginModalElement.classList.remove('show');
            document.body.classList.remove('modal-open');
            
            // Remove backdrop
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) {
                backdrop.remove();
            }
        }

        // If we're already on the admin page, show the dashboard content instead of reloading
        if (window.location.pathname.includes('index.html') || window.location.pathname === '/') {
            console.log('Already on admin page, showing dashboard content...');
            
            // Show dashboard content and hide login modal
            showDashboardContent();
            
            // Trigger dashboard load without page refresh
            setTimeout(() => {
                if (typeof loadDashboardData === 'function') {
                    loadDashboardData();
                } else if (typeof initializeDashboard === 'function') {
                    initializeDashboard();
                }
            }, 200);
        } else {
            window.location.href = redirectUrl || '/admin';
        }
    }

    function clearErrorDisplays() {
        const errorElements = [
            document.getElementById('login-error'),
            document.getElementById('auth-error'),
            ...document.querySelectorAll('.alert-danger'),
            ...document.querySelectorAll('.error-message'),
            ...document.querySelectorAll('.auth-error-display')
        ];

        errorElements.forEach(element => {
            if (element) {
                element.classList.add('d-none');
                element.style.display = 'none';
                element.textContent = '';
            }
        });
    }

    function displayFallbackError(message) {
        const loginError = document.getElementById('login-error');
        if (loginError) {
            loginError.textContent = message;
            loginError.classList.remove('d-none');
            loginError.style.display = 'block';
        } else {
            // Create error display if none exists
            console.error('Login Error:', message);
            alert(message); // Fallback alert
        }
    }

    function showLoadingState(loading) {
        const submitButton = document.querySelector('#login-form button[type="submit"]');
        const emailField = document.getElementById('email') || document.getElementById('login-email');
        const passwordField = document.getElementById('password') || document.getElementById('login-password');

        if (submitButton) {
            if (loading) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Logging in...';
            } else {
                submitButton.disabled = false;
                submitButton.innerHTML = 'Login';
            }
        }

        if (emailField) emailField.disabled = loading;
        if (passwordField) passwordField.disabled = loading;
    }

    function updateDashboardAuthState() {
        // Ensure compatibility between different token storage systems
        const sessionToken = adminAuthService ? adminAuthService.sessionManager.getSessionToken() : null;
        const user = adminAuthService ? adminAuthService.getCurrentUser() : null;
        
        if (sessionToken && user) {
            // Store token in the format expected by dashboard.js
            localStorage.setItem('authToken', sessionToken);
            localStorage.setItem('username', user.username || user.email);
            localStorage.setItem('userEmail', user.email);
            localStorage.setItem('isAdmin', user.is_admin ? 'true' : 'false');
        }
    }

    function showDashboardContent() {
        // Hide login modal using Bootstrap modal methods
        const loginModalElement = document.getElementById('loginModal');
        if (loginModalElement) {
            // Try to get existing modal instance
            let loginModal = bootstrap.Modal.getInstance(loginModalElement);
            if (loginModal) {
                loginModal.hide();
            } else {
                // Create new modal instance and hide it
                loginModal = new bootstrap.Modal(loginModalElement);
                loginModal.hide();
            }
            
            // Force hide the modal element and backdrop
            setTimeout(() => {
                loginModalElement.style.display = 'none';
                loginModalElement.classList.remove('show');
                loginModalElement.setAttribute('aria-hidden', 'true');
                loginModalElement.removeAttribute('aria-modal');
                
                document.body.classList.remove('modal-open');
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';
                
                // Remove any remaining backdrops
                const backdrops = document.querySelectorAll('.modal-backdrop');
                backdrops.forEach(backdrop => backdrop.remove());
            }, 100);
        }

        // Show main dashboard content
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.querySelector('main');
        
        if (sidebar) {
            sidebar.style.display = 'block';
        }
        if (mainContent) {
            mainContent.style.display = 'block';
        }

        // Trigger dashboard initialization if available
        if (typeof initializeDashboard === 'function') {
            initializeDashboard();
        }
    }

    async function directLogin(credentials) {
        console.log('Performing direct login...');
        
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    email: credentials.email,
                    password: credentials.password
                })
            });
            
            console.log('Direct login response status:', response.status);
            
            if (response.ok) {
                const data = await response.json();
                console.log('Direct login response data:', data);
                
                if (data.success && data.user) {
                    // Store tokens directly (even if using cookie-based auth)
                    const token = data.token || data.access_token || 'session_cookie_auth';
                    const user = data.user || {};
                    
                    localStorage.setItem('authToken', token);
                    localStorage.setItem('admin_session_token', token);
                    localStorage.setItem('username', user.username || user.email || 'admin');
                    localStorage.setItem('userEmail', user.email || credentials.email);
                    localStorage.setItem('isAdmin', user.is_admin ? 'true' : 'false');
                    
                    return {
                        success: true,
                        user: user,
                        token: token,
                        redirect_url: data.redirect_url || '/admin'
                    };
                } else {
                    return {
                        success: false,
                        message: data.message || 'Login failed - invalid response'
                    };
                }
            } else {
                const errorText = await response.text();
                return {
                    success: false,
                    message: `Login failed: ${response.status} - ${errorText}`
                };
            }
        } catch (error) {
            console.error('Direct login error:', error);
            return {
                success: false,
                message: `Login error: ${error.message}`
            };
        }
    }

    function clearAllStoredData() {
        const keys = ['authToken', 'username', 'userEmail', 'isAdmin', 'admin_session_token', 'admin_user_data'];
        keys.forEach(key => {
            localStorage.removeItem(key);
            sessionStorage.removeItem(key);
        });

        // Clear cookies
        document.cookie = 'session_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    }

    // Add Register button below login form submit button if it doesn't exist
    const loginForm = document.getElementById('login-form');
    if (loginForm && !document.querySelector('.register-link')) {
        const registerButton = document.createElement('button');
        registerButton.type = 'button';
        registerButton.className = 'btn btn-link mt-2 register-link';
        registerButton.textContent = 'Register as Admin';
        registerButton.addEventListener('click', () => {
            window.location.href = 'register.html';
        });
        loginForm.appendChild(registerButton);
    }

    // Auto-show login modal if not authenticated and on admin pages
    setTimeout(() => {
        const loginModalElement = document.getElementById('loginModal') || document.getElementById('login-modal');
        if (loginModalElement && window.location.pathname.startsWith('/admin')) {
            // Check multiple authentication sources
            const hasAuthToken = localStorage.getItem('authToken') || localStorage.getItem('admin_session_token');
            const isAuthenticated = adminAuthService ? 
                adminAuthService.isAuthenticated() : 
                (typeof unifiedApi !== 'undefined' ? unifiedApi.isAuthenticated() : false);
            
            // Only show modal if definitely not authenticated and login hasn't been successful
            if (!hasAuthToken && !isAuthenticated && !loginSuccessful) {
                const loginModal = new bootstrap.Modal(loginModalElement);
                loginModal.show();
            }
        }
    }, 500);

    // Enable debug mode with URL parameter
    if (window.location.search.includes('debug=true')) {
        localStorage.setItem('admin_debug', 'true');
        console.log('Debug mode enabled for admin authentication');
    }
});
