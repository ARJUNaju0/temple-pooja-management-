// D:\Django Internship\tprmsystem\main\static\js\auth_utils.js
// Auth utility functions for JWT with HttpOnly Cookies

const AuthUtils = {
    // Get user data from sessionStorage (tokens are in HttpOnly cookies)
    getUser() {
        const userStr = sessionStorage.getItem('user');
        return userStr ? JSON.parse(userStr) : null;
    },

    // Check if user is authenticated
    isAuthenticated() {
        return !!this.getUser();
    },

    // Check if user is admin/staff
    isAdmin() {
        const user = this.getUser();
        return user && (user.is_staff || user.is_superuser);
    },

    // Logout - call API to blacklist token and clear cookies
    async logout() {
        try {
            const response = await fetch('/api/logout/', {
                method: 'POST',
                credentials: 'same-origin',  // Include cookies
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            // Clear session storage
            sessionStorage.removeItem('user');

            // Redirect to home
            window.location.href = '/';
        } catch (error) {
            console.error('Logout error:', error);
            // Still clear session and redirect
            sessionStorage.removeItem('user');
            window.location.href = '/';
        }
    },

    // Refresh access token
   async refreshToken() {
            try {
                const response = await fetch('/api/refresh/', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' }
                });

                if (response.ok) {
                    console.log('Token refreshed successfully');
                    const user = await this.getCurrentUser();
                    if (!user) {
                        console.warn('Refresh OK but user still unauthorized → logout');
                        this.logout();
                        return false;
                    }
                    return true;
                } else {
                    this.logout();
                    return false;
                }
            } catch (error) {
                console.error('Token refresh error:', error);
                this.logout();
                return false;
            }
    },  
    // Make authenticated API request
    async apiRequest(url, options = {}) {
        // Ensure credentials are included (for cookies)
        options.credentials = 'same-origin';
        
        // Add headers
        options.headers = {
            ...options.headers,
            'Content-Type': 'application/json',
        };

        let response = await fetch(url, options);

        // If token expired (401), try to refresh
        if (response.status === 401) {
            const refreshed = await this.refreshToken();
            
            if (refreshed) {
                // Retry original request
                response = await fetch(url, options);
            } else {
                throw new Error('Authentication failed');
            }
        }

        return response;
    },

    // Get current user info from API
    async getCurrentUser() {
        try {
            const response = await this.apiRequest('/api/user/');
            if (response.ok) {
                const user = await response.json();
                sessionStorage.setItem('user', JSON.stringify(user));
                return user;
            }
            return null;
        } catch (error) {
            console.error('Get user error:', error);
            return null;
        }
    },

    // Admin function: Create new member
    async createMember(memberData) {
        try {
            const response = await this.apiRequest('/api/members/create/', {
                method: 'POST',
                body: JSON.stringify(memberData)
            });

            const data = await response.json();
            return { success: response.ok, data };
        } catch (error) {
            console.error('Create member error:', error);
            return { success: false, error: error.message };
        }
    },

    // Token Expiry Manager
    tokenExpiryManager: {
        checkInterval: null,
        warningShown: false,
        
        // Start monitoring token expiry
        startMonitoring() {
            // Check every minute
            this.checkInterval = setInterval(() => {
                this.checkTokenExpiry();
            }, 60000); // 60 seconds
            
            // Also check immediately
            this.checkTokenExpiry();
        },
        
        // Stop monitoring
        stopMonitoring() {
            if (this.checkInterval) {
                clearInterval(this.checkInterval);
                this.checkInterval = null;
            }
        },
        
        // Check if token is about to expire
        async checkTokenExpiry() {
            // Tokens are in cookies, we can't read expiry directly
            // Instead, make a lightweight API call to check if still valid
            try {
                const response = await fetch('/api/user/', {
                    credentials: 'same-origin'
                });
                
                if (response.status === 401) {
                    // Token expired, try refresh
                    const refreshed = await AuthUtils.refreshToken();
                    if (!refreshed) {
                        this.showSessionExpiredModal();
                    }
                } else if (response.ok) {
                    // Token still valid, auto-refresh every 30 mins to keep session alive
                    this.autoRefreshIfNeeded();
                }
            } catch (error) {
                console.error('Token expiry check failed:', error);
            }
        },
        
        // Auto-refresh token every 30 minutes
        lastRefresh: Date.now(),
        async autoRefreshIfNeeded() {
            const now = Date.now();
            const thirtyMinutes = 30 * 60 * 1000;
            
            if (now - this.lastRefresh > thirtyMinutes) {
                const refreshed = await AuthUtils.refreshToken();
                if (refreshed) {
                    this.lastRefresh = now;
                    console.log('Token auto-refreshed');
                }
            }
        },
        
        // Show session expired modal
        showSessionExpiredModal() {
            window.location.href = '/login/';
        },
        
        // Show expiry warning (5 minutes before expiry)
        showExpiryWarning(minutesLeft) {
        },
        
        // Continue session (refresh token)
        async continueSession() {
            const modal = document.getElementById('expiry-warning-modal');
            if (modal) modal.remove();
            this.warningShown = false;
            
            await AuthUtils.refreshToken();
        }
    },

    // Activity Tracker - track user activity for auto-refresh
    activityTracker: {
        lastActivity: Date.now(),
        activityTimeout: null,
        
        // Start tracking
        startTracking() {
            // Track mouse movement
            document.addEventListener('mousemove', () => this.updateActivity());
            document.addEventListener('keypress', () => this.updateActivity());
            document.addEventListener('click', () => this.updateActivity());
            document.addEventListener('scroll', () => this.updateActivity());
        },
        
        // Update last activity timestamp
        updateActivity() {
            this.lastActivity = Date.now();
        },
        
        // Check if user is active
        isActive() {
            const fiveMinutes = 5 * 60 * 1000;
            return (Date.now() - this.lastActivity) < fiveMinutes;
        }
    }
};

// Auto-redirect to login if not authenticated (use on protected pages)
function requireAuth() {
    if (!AuthUtils.isAuthenticated()) {
        sessionStorage.setItem('return_url', window.location.pathname);
        window.location.href = '/login/';
    } else {
        // Start monitoring token expiry
        AuthUtils.tokenExpiryManager.startMonitoring();
        AuthUtils.activityTracker.startTracking();
    }
}

// Auto-redirect non-admin users (use on admin-only pages)
function requireAdmin() {
    if (!AuthUtils.isAuthenticated()) {
        window.location.href = '/login/';
    } else if (!AuthUtils.isAdmin()) {
        alert('Access denied. Admin privileges required.');
        window.location.href = '/member/dashboard/';
    } else {
        AuthUtils.tokenExpiryManager.startMonitoring();
        AuthUtils.activityTracker.startTracking();
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // If user is authenticated, start monitoring
    if (AuthUtils.isAuthenticated()) {
        AuthUtils.tokenExpiryManager.startMonitoring();
        AuthUtils.activityTracker.startTracking();
    }
});