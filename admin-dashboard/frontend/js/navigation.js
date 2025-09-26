/**
 * Admin Dashboard - Navigation Management
 * Standardizes navigation and breadcrumbs across all pages
 */

class NavigationManager {
    constructor() {
        this.currentPage = this.getCurrentPageFromURL();
        this.searchTimeout = null;
        this.init();
    }

    /**
     * Initialize navigation system
     */
    init() {
        this.setupSidebarNavigation();
        this.setupBreadcrumbs();
        this.setupSearchFunctionality();
        this.setupUserDropdown();
        this.setupMobileToggle();
        this.updateActiveNavigation();
    }

    /**
     * Get current page from URL
     */
    getCurrentPageFromURL() {
        const path = window.location.pathname;
        const filename = path.split('/').pop();
        
        // Map filenames to page identifiers
        const pageMap = {
            'index.html': 'dashboard',
            'tickets.html': 'tickets',
            'users.html': 'users',
            'integration.html': 'integration',
            'settings.html': 'settings',
            'logs.html': 'logs'
        };
        
        return pageMap[filename] || 'dashboard';
    }

    /**
     * Setup sidebar navigation with consistent highlighting
     */
    setupSidebarNavigation() {
        const navLinks = document.querySelectorAll('.sidebar-nav a');
        
        navLinks.forEach(link => {
            // Remove existing click handlers
            link.removeEventListener('click', this.handleNavClick);
            
            // Add consistent click handler
            link.addEventListener('click', (e) => this.handleNavClick(e, link));
        });
    }

    /**
     * Handle navigation link clicks
     */
    handleNavClick(e, link) {
        // Don't prevent default - allow normal navigation
        // Just update active state for immediate feedback
        this.updateActiveState(link);
    }

    /**
     * Update active navigation state
     */
    updateActiveNavigation() {
        // Remove all active classes
        document.querySelectorAll('.sidebar-nav a').forEach(link => {
            link.classList.remove('active');
        });

        // Add active class to current page
        const currentNavLink = document.getElementById(`nav-${this.currentPage}`);
        if (currentNavLink) {
            currentNavLink.classList.add('active');
        }
    }

    /**
     * Update active state for a specific link
     */
    updateActiveState(activeLink) {
        // Remove active from all links
        document.querySelectorAll('.sidebar-nav a').forEach(link => {
            link.classList.remove('active');
        });
        
        // Add active to clicked link
        activeLink.classList.add('active');
    }

    /**
     * Setup breadcrumb navigation
     */
    setupBreadcrumbs() {
        const breadcrumbContainer = document.querySelector('.breadcrumb');
        if (!breadcrumbContainer) return;

        const breadcrumbs = this.getBreadcrumbsForPage(this.currentPage);
        this.renderBreadcrumbs(breadcrumbContainer, breadcrumbs);
    }

    /**
     * Get breadcrumbs for current page
     */
    getBreadcrumbsForPage(page) {
        const breadcrumbMap = {
            'dashboard': [
                { text: 'Home', link: null, active: true }
            ],
            'tickets': [
                { text: 'Home', link: 'index.html', active: false },
                { text: 'Support Tickets', link: null, active: true }
            ],
            'users': [
                { text: 'Home', link: 'index.html', active: false },
                { text: 'User Management', link: null, active: true }
            ],
            'integration': [
                { text: 'Home', link: 'index.html', active: false },
                { text: 'AI Integration', link: null, active: true }
            ],
            'settings': [
                { text: 'Home', link: 'index.html', active: false },
                { text: 'Settings', link: null, active: true }
            ],
            'logs': [
                { text: 'Home', link: 'index.html', active: false },
                { text: 'System Logs', link: null, active: true }
            ]
        };

        return breadcrumbMap[page] || breadcrumbMap['dashboard'];
    }

    /**
     * Render breadcrumbs
     */
    renderBreadcrumbs(container, breadcrumbs) {
        // Clear existing breadcrumbs
        container.innerHTML = '';

        breadcrumbs.forEach((crumb, index) => {
            if (crumb.link && !crumb.active) {
                // Create linked breadcrumb
                const link = document.createElement('a');
                link.href = crumb.link;
                link.textContent = crumb.text;
                link.className = 'breadcrumb-item';
                container.appendChild(link);
            } else {
                // Create active breadcrumb
                const span = document.createElement('span');
                span.textContent = crumb.text;
                span.className = crumb.active ? 'breadcrumb-item active' : 'breadcrumb-item';
                container.appendChild(span);
            }
        });
    }

    /**
     * Setup search functionality
     */
    setupSearchFunctionality() {
        // Global search in top navigation
        const globalSearch = document.querySelector('.top-nav .search-box input');
        if (globalSearch) {
            globalSearch.addEventListener('input', (e) => {
                this.handleGlobalSearch(e.target.value);
            });
            
            // Set appropriate placeholder based on page
            this.updateSearchPlaceholder(globalSearch);
        }

        // Page-specific search inputs
        const pageSearchInputs = [
            '#ticket-search',
            '#user-search',
            '#log-search',
            '#global-search',
            '#settings-search'
        ];

        pageSearchInputs.forEach(selector => {
            const input = document.querySelector(selector);
            if (input) {
                input.addEventListener('input', (e) => {
                    this.handlePageSearch(e.target.value, selector);
                });
            }
        });
    }

    /**
     * Update search placeholder based on current page
     */
    updateSearchPlaceholder(searchInput) {
        const placeholders = {
            'dashboard': 'Search dashboard...',
            'tickets': 'Search tickets...',
            'users': 'Search users...',
            'integration': 'Search integration...',
            'settings': 'Search settings...',
            'logs': 'Search logs...'
        };

        searchInput.placeholder = placeholders[this.currentPage] || 'Search...';
    }

    /**
     * Handle global search
     */
    handleGlobalSearch(query) {
        // Clear existing timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        // Debounce search
        this.searchTimeout = setTimeout(() => {
            this.performGlobalSearch(query);
        }, 300);
    }

    /**
     * Perform global search
     */
    performGlobalSearch(query) {
        // Delegate to page-specific search if available
        if (window.performPageSearch && typeof window.performPageSearch === 'function') {
            window.performPageSearch(query);
        } else {
            // Default search behavior
            console.log('Global search:', query);
        }
    }

    /**
     * Handle page-specific search
     */
    handlePageSearch(query, inputSelector) {
        // Clear existing timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        // Debounce search
        this.searchTimeout = setTimeout(() => {
            this.performPageSearch(query, inputSelector);
        }, 300);
    }

    /**
     * Perform page-specific search
     */
    performPageSearch(query, inputSelector) {
        // Delegate to page-specific search functions
        const searchFunctions = {
            '#ticket-search': 'searchTickets',
            '#user-search': 'searchUsers',
            '#log-search': 'searchLogs',
            '#settings-search': 'searchSettings'
        };

        const functionName = searchFunctions[inputSelector];
        if (functionName && window[functionName] && typeof window[functionName] === 'function') {
            window[functionName](query);
        }
    }

    /**
     * Setup user dropdown functionality
     */
    setupUserDropdown() {
        // Ensure consistent user dropdown across all pages
        const userDropdowns = document.querySelectorAll('#userDropdown, #dropdownMenuButton');
        
        userDropdowns.forEach(dropdown => {
            // Update user info if available
            this.updateUserInfo();
            
            // Setup logout handlers
            this.setupLogoutHandlers();
        });
    }

    /**
     * Update user information in dropdown
     */
    updateUserInfo() {
        const usernameElements = document.querySelectorAll('#username, #user-name');
        const userRoleElements = document.querySelectorAll('#user-role');
        
        // Get user info from various sources
        const username = this.getUserInfo('username') || 'Admin';
        const role = this.getUserInfo('role') || 'Administrator';
        
        usernameElements.forEach(el => {
            if (el) el.textContent = username;
        });
        
        userRoleElements.forEach(el => {
            if (el) el.textContent = role;
        });
    }

    /**
     * Get user info from storage or auth service
     */
    getUserInfo(key) {
        // Try multiple sources
        const sources = [
            () => localStorage.getItem(key),
            () => sessionStorage.getItem(key),
            () => window.adminAuthService?.getCurrentUser()?.[key],
            () => window.sessionManager?.getCurrentUser()?.[key]
        ];

        for (const source of sources) {
            try {
                const value = source();
                if (value) return value;
            } catch (e) {
                // Continue to next source
            }
        }

        return null;
    }

    /**
     * Setup logout handlers
     */
    setupLogoutHandlers() {
        const logoutButtons = document.querySelectorAll('#btn-logout, #nav-logout-dropdown, #dropdown-logout');
        
        logoutButtons.forEach(button => {
            button.removeEventListener('click', this.handleLogout);
            button.addEventListener('click', (e) => this.handleLogout(e));
        });
    }

    /**
     * Handle logout
     */
    handleLogout(e) {
        e.preventDefault();
        
        // Clear all authentication data
        localStorage.removeItem('authToken');
        localStorage.removeItem('admin_session_token');
        localStorage.removeItem('username');
        localStorage.removeItem('role');
        sessionStorage.clear();
        
        // Call auth service logout if available
        if (window.adminAuthService?.logout) {
            window.adminAuthService.logout();
        }
        
        if (window.sessionManager?.logout) {
            window.sessionManager.logout();
        }
        
        // Redirect to login or home
        window.location.href = 'index.html';
    }

    /**
     * Setup mobile sidebar toggle
     */
    setupMobileToggle() {
        const sidebarToggle = document.getElementById('sidebar-toggle');
        const sidebar = document.querySelector('.sidebar');
        
        if (sidebarToggle && sidebar) {
            sidebarToggle.addEventListener('click', () => {
                sidebar.classList.toggle('show');
            });
            
            // Close sidebar when clicking outside on mobile
            document.addEventListener('click', (e) => {
                if (window.innerWidth <= 992) {
                    if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                        sidebar.classList.remove('show');
                    }
                }
            });
        }
    }

    /**
     * Update page title
     */
    updatePageTitle(title) {
        const pageTitleElement = document.getElementById('page-title');
        if (pageTitleElement) {
            // Preserve icon if it exists
            const icon = pageTitleElement.querySelector('i');
            const iconHTML = icon ? icon.outerHTML + ' ' : '';
            pageTitleElement.innerHTML = iconHTML + title;
        }
        
        // Update document title
        document.title = `${title} - Admin Dashboard`;
    }

    /**
     * Show notification in top navigation
     */
    showNotification(message, type = 'info') {
        const notification = document.querySelector('.notification');
        if (notification) {
            // Update badge if needed
            const badge = notification.querySelector('.badge');
            if (badge) {
                const currentCount = parseInt(badge.textContent) || 0;
                badge.textContent = currentCount + 1;
            }
        }
        
        // Also show toast notification if available
        if (window.showToast && typeof window.showToast === 'function') {
            window.showToast(message, type);
        }
    }

    /**
     * Get navigation manager instance
     */
    static getInstance() {
        if (!window.navigationManager) {
            window.navigationManager = new NavigationManager();
        }
        return window.navigationManager;
    }
}

// Initialize navigation when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.navigationManager = NavigationManager.getInstance();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NavigationManager;
}