// D:\Django Internship\tprmsystem\main\static\js\auth_utils.js

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
        console.log('🔴 Logout initiated - stopping all monitoring...');
        
        try {
            // 🔥 CRITICAL: Stop all monitoring activities FIRST
            this.tokenExpiryManager.stopMonitoring();
            this.activityTracker.stopTracking();
            
            // Clear any pending refresh attempts
            if (this.tokenExpiryManager.refreshTimeout) {
                clearTimeout(this.tokenExpiryManager.refreshTimeout);
            }
            
            // Make logout API call
            const response = await fetch('/api/logout/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            console.log('✅ Logout API called successfully');

        } catch (error) {
            console.error('⚠️ Logout API error (continuing with cleanup):', error);
        } finally {
            // ALWAYS execute cleanup, even if API fails
            
            // Clear session storage
            sessionStorage.removeItem('user');
            
            // Clear any global auth cache (from lscript.js)
            if (window.authCache !== undefined) {
                window.authCache = null;
                window.cacheTime = 0;
            }
            
            // Final safety: clear all intervals (in case something was missed)
            if (this.tokenExpiryManager.checkInterval) {
                clearInterval(this.tokenExpiryManager.checkInterval);
                this.tokenExpiryManager.checkInterval = null;
            }
            
            // ✅ NEW: Remove storage event listener
            window.removeEventListener('storage', this._storageHandler);
            
            console.log('✅ All monitoring stopped, session cleared');
            
            // Redirect to home (this stops all JavaScript execution on this page)
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
                console.log('✅ Token refreshed successfully');
                const user = await this.getCurrentUser();
                if (!user) {
                    console.warn('⚠️ Refresh OK but user still unauthorized → logout');
                    this.logout();
                    return false;
                }
                
                // ✅ NEW: Reset activity timeout on successful refresh
                this.activityTracker.updateActivity();
                return true;
            } else {
                console.warn('⚠️ Token refresh failed → logout');
                this.logout();
                return false;
            }
        } catch (error) {
            console.error('❌ Token refresh error:', error);
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

        // ✅ NEW: Add timeout with AbortController
        const controller = new AbortController();
        const timeoutMs = 15000; // 15 seconds
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
        
        try {
            let response = await fetch(url, { ...options, signal: controller.signal });
            clearTimeout(timeoutId);

            // If token expired (401), try to refresh
            if (response.status === 401) {
                console.log('⚠️ Token expired (401), attempting refresh...');
                const refreshed = await this.refreshToken();
                
                if (refreshed) {
                    // Retry original request
                    const retryController = new AbortController();
                    const retryTimeoutId = setTimeout(() => retryController.abort(), timeoutMs);
                    
                    response = await fetch(url, { ...options, signal: retryController.signal });
                    clearTimeout(retryTimeoutId);
                } else {
                    throw new Error('Authentication failed - token refresh unsuccessful');
                }
            }

            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                console.error('❌ Request timeout after ' + timeoutMs + 'ms');
                throw new Error('Request timeout');
            } else {
                console.error('❌ API request failed:', error);
                throw error;
            }
        }
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
            console.error('❌ Get user error:', error);
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
            console.error('❌ Create member error:', error);
            return { success: false, error: error.message };
        }
    },

    // ✅ NEW: Storage event handler (stored as reference for cleanup)
    _storageHandler: null,

    // Token Expiry Manager
    tokenExpiryManager: {
        checkInterval: null,
        refreshTimeout: null,
        warningShown: false,
        isMonitoring: false,
        
        // Start monitoring token expiry
        startMonitoring() {
            // 🔥 Prevent multiple monitoring instances
            if (this.isMonitoring) {
                console.log('⚠️ Token monitoring already active, skipping...');
                return;
            }
            
            console.log('✅ Starting token expiry monitoring...');
            this.isMonitoring = true;
            
            // Check every 60 seconds
            this.checkInterval = setInterval(() => {
                // 🔥 Safety check: verify we should still be monitoring
                if (!AuthUtils.isAuthenticated()) {
                    console.log('⚠️ User not authenticated, stopping monitoring...');
                    this.stopMonitoring();
                    return;
                }
                this.checkTokenExpiry();
            }, 60000); // 60 seconds
            
            // Also check immediately
            this.checkTokenExpiry();
        },
        
        // Stop monitoring
        stopMonitoring() {
            console.log('🛑 Stopping token expiry monitoring...');
            
            if (this.checkInterval) {
                clearInterval(this.checkInterval);
                this.checkInterval = null;
            }
            
            if (this.refreshTimeout) {
                clearTimeout(this.refreshTimeout);
                this.refreshTimeout = null;
            }
            
            this.isMonitoring = false;
            this.warningShown = false;
            console.log('✅ Token monitoring stopped');
        },
        
        // Check if token is about to expire and handle inactivity
        async checkTokenExpiry() {
            // 🔥 Double-check authentication before making request
            if (!AuthUtils.isAuthenticated()) {
                this.stopMonitoring();
                return;
            }
            
            // ✅ NEW: Check inactivity (5+ minutes)
            if (!AuthUtils.activityTracker.isActive()) {
                console.log('⚠️ User inactive for 5+ minutes, logging out...');
                AuthUtils.logout();
                return;
            }
            
            try {
                const response = await fetch('/api/user/', {
                    credentials: 'same-origin',
                    signal: AbortSignal.timeout(5000) // 5 second timeout
                });
                
                if (response.status === 401) {
                    console.log('⚠️ Token expired, attempting refresh...');
                    // Token expired, try refresh
                    const refreshed = await AuthUtils.refreshToken();
                    if (!refreshed) {
                        this.stopMonitoring();
                        this.showSessionExpiredModal();
                    }
                } else if (response.ok) {
                    // Token still valid, auto-refresh every 30 mins to keep session alive
                    this.autoRefreshIfNeeded();
                }
            } catch (error) {
                if (error.name === 'AbortError') {
                    console.error('⚠️ Token check timeout');
                } else {
                    console.error('⚠️ Token expiry check failed:', error);
                }
                // Don't logout on network errors, just log it
            }
        },
        
        // Auto-refresh token every 30 minutes
        lastRefresh: Date.now(),
        async autoRefreshIfNeeded() {
            const now = Date.now();
            const thirtyMinutes = 30 * 60 * 1000;
            
            if (now - this.lastRefresh > thirtyMinutes) {
                console.log('🔄 Auto-refreshing token (30 min interval)...');
                const refreshed = await AuthUtils.refreshToken();
                if (refreshed) {
                    this.lastRefresh = now;
                    console.log('✅ Token auto-refreshed');
                }
            }
        },
        
        // Show session expired modal
        showSessionExpiredModal() {
            console.log('⚠️ Session expired, redirecting to login...');
            
            // ✅ NEW: Optional - show modal before redirect
            const message = 'Your session has expired. Please log in again.';
            alert(message); // Simple alert, can be replaced with fancy modal
            
            window.location.href = '/login/';
        },
        
        // Show expiry warning (5 minutes before expiry) - placeholder
        showExpiryWarning(minutesLeft) {
            // Placeholder for future implementation
        },
        
        // Continue session (refresh token)
        async continueSession() {
            const modal = document.getElementById('expiry-warning-modal');
            if (modal) modal.remove();
            this.warningShown = false;
            
            await AuthUtils.refreshToken();
        }
    },

    // Activity Tracker - track user activity for auto-logout after 5 min inactivity
    activityTracker: {
        lastActivity: Date.now(),
        activityTimeout: null,
        isTracking: false,
        handlers: {},
        INACTIVITY_TIMEOUT: 5 * 60 * 1000, // 5 minutes in milliseconds
        
        // Start tracking
        startTracking() {
            // 🔥 Prevent multiple tracking instances
            if (this.isTracking) {
                console.log('⚠️ Activity tracking already active, skipping...');
                return;
            }
            
            console.log('✅ Starting activity tracking...');
            this.isTracking = true;
            this.lastActivity = Date.now();
            
            // Create bound handlers (so we can remove them later)
            this.handlers.mousemove = () => this.updateActivity();
            this.handlers.keypress = () => this.updateActivity();
            this.handlers.click = () => this.updateActivity();
            this.handlers.scroll = () => this.updateActivity();
            this.handlers.touchmove = () => this.updateActivity(); // ✅ NEW: Mobile support
            
            // Track user activity
            document.addEventListener('mousemove', this.handlers.mousemove);
            document.addEventListener('keypress', this.handlers.keypress);
            document.addEventListener('click', this.handlers.click);
            document.addEventListener('scroll', this.handlers.scroll);
            document.addEventListener('touchmove', this.handlers.touchmove);
        },
        
        // Stop tracking method
        stopTracking() {
            console.log('🛑 Stopping activity tracking...');
            
            if (this.handlers.mousemove) {
                document.removeEventListener('mousemove', this.handlers.mousemove);
                document.removeEventListener('keypress', this.handlers.keypress);
                document.removeEventListener('click', this.handlers.click);
                document.removeEventListener('scroll', this.handlers.scroll);
                document.removeEventListener('touchmove', this.handlers.touchmove);
            }
            
            this.handlers = {};
            this.isTracking = false;
            console.log('✅ Activity tracking stopped');
        },
        
        // Update last activity timestamp
        updateActivity() {
            this.lastActivity = Date.now();
            // Optional: Reset warning if shown
            if (AuthUtils.tokenExpiryManager.warningShown) {
                AuthUtils.tokenExpiryManager.warningShown = false;
            }
        },
        
        // Check if user is active (within 5 minutes)
        isActive() {
            const timeSinceLastActivity = Date.now() - this.lastActivity;
            return timeSinceLastActivity < this.INACTIVITY_TIMEOUT;
        },
        
        // Get minutes since last activity (useful for debugging)
        getMinutesSinceActivity() {
            return Math.floor((Date.now() - this.lastActivity) / 1000 / 60);
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
        alert('❌ Access denied. Admin privileges required.');
        window.location.href = '/member/dashboard/';
    } else {
        AuthUtils.tokenExpiryManager.startMonitoring();
        AuthUtils.activityTracker.startTracking();
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔷 AuthUtils initialized');
    
    // If user is authenticated, start monitoring
    if (AuthUtils.isAuthenticated()) {
        console.log('✅ User authenticated, starting monitoring...');
        AuthUtils.tokenExpiryManager.startMonitoring();
        AuthUtils.activityTracker.startTracking();
    } else {
        console.log('ℹ️ User not authenticated, monitoring not started');
    }
});

// ✅ NEW: Setup storage event listener (for manual logout from other tabs)
AuthUtils._storageHandler = function(e) {
    if (e.key === 'user' && !e.newValue) {
        console.log('⚠️ User logged out from another tab, cleaning up...');
        AuthUtils.tokenExpiryManager.stopMonitoring();
        AuthUtils.activityTracker.stopTracking();
    }
};

window.addEventListener('storage', AuthUtils._storageHandler);

// ✅ NEW: Cleanup on page unload (better than beforeunload)
window.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('👀 Page hidden, pausing activity tracking...');
        AuthUtils.activityTracker.stopTracking();
    } else {
        console.log('👀 Page visible again, resuming activity tracking...');
        if (AuthUtils.isAuthenticated()) {
            AuthUtils.activityTracker.startTracking();
        }
    }
});

// ✅ NEW: Handle page reload/close gracefully
window.addEventListener('beforeunload', function() {
    if (AuthUtils.isAuthenticated()) {
        console.log('🔷 Page unloading, stopping monitoring...');
        AuthUtils.tokenExpiryManager.stopMonitoring();
        AuthUtils.activityTracker.stopTracking();
    }
});

console.log('✅ auth_utils.js loaded successfully');
