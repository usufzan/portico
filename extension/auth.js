// Shared authentication utilities for the Portico extension
// This eliminates duplicate auth logic between popup.js and options.js

class AuthManager {
    constructor() {
        this.apiBaseUrl = 'http://127.0.0.1:8000';
        this.authToken = null;
    }

    // Token management
    async getStoredAuthToken() {
        return new Promise((resolve) => {
            chrome.storage.local.get(['authToken'], (result) => {
                resolve(result.authToken || null);
            });
        });
    }

    async storeAuthToken(token) {
        return new Promise((resolve) => {
            chrome.storage.local.set({ authToken: token }, resolve);
        });
    }

    async clearStoredAuthToken() {
        return new Promise((resolve) => {
            chrome.storage.local.remove(['authToken'], resolve);
        });
    }

    // Token verification
    async verifyToken(token) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/v1/user/activity`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            return response.ok;
        } catch (error) {
            console.error('Token verification failed:', error);
            return false;
        }
    }

    // Authentication check
    async checkAuthentication() {
        const token = await this.getStoredAuthToken();
        if (!token) {
            return { authenticated: false, token: null };
        }

        const isValid = await this.verifyToken(token);
        if (!isValid) {
            await this.clearStoredAuthToken();
            return { authenticated: false, token: null };
        }

        this.authToken = token;
        return { authenticated: true, token };
    }

    // Login
    async login(email, password) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`
            });

            if (response.ok) {
                const data = await response.json();
                await this.storeAuthToken(data.access_token);
                this.authToken = data.access_token;
                return { success: true, message: 'Login successful' };
            } else {
                const error = await response.json();
                return { success: false, message: error.detail || 'Login failed' };
            }
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, message: 'Network error during login' };
        }
    }

    // Register
    async register(email, password) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password })
            });

            if (response.ok) {
                return { success: true, message: 'Registration successful' };
            } else {
                const error = await response.json();
                return { success: false, message: error.detail || 'Registration failed' };
            }
        } catch (error) {
            console.error('Registration error:', error);
            return { success: false, message: 'Network error during registration' };
        }
    }

    // Logout
    async logout() {
        await this.clearStoredAuthToken();
        this.authToken = null;
    }

    // Get authenticated request headers
    getAuthHeaders() {
        return {
            'Authorization': `Bearer ${this.authToken}`,
            'Content-Type': 'application/json'
        };
    }

    // Make authenticated API request
    async authenticatedRequest(url, options = {}) {
        if (!this.authToken) {
            throw new Error('No authentication token available');
        }

        const response = await fetch(`${this.apiBaseUrl}${url}`, {
            ...options,
            headers: {
                ...this.getAuthHeaders(),
                ...options.headers
            }
        });

        if (response.status === 401) {
            await this.logout();
            throw new Error('Authentication expired');
        }

        return response;
    }
}

// Export for use in other scripts
window.AuthManager = AuthManager;
