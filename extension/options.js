// Universal Scraper Extension - Options Page Logic

class UniversalScraperOptions {
    constructor() {
        this.apiBaseUrl = 'http://127.0.0.1:8000';
        this.authToken = null;
        this.userPreferences = null;
        
        this.initializeElements();
        this.bindEvents();
        this.initialize();
    }

    initializeElements() {
        // Authentication elements
        this.authStatus = document.getElementById('authStatus');
        this.statusDot = document.getElementById('statusDot');
        this.statusText = document.getElementById('statusText');
        this.authButton = document.getElementById('authButton');

        // Preferences elements
        this.preferencesSection = document.getElementById('preferencesSection');
        this.baseLanguage = document.getElementById('baseLanguage');
        this.targetLanguage = document.getElementById('targetLanguage');
        this.proficiencyLevel = document.getElementById('proficiencyLevel');
        this.savePreferencesButton = document.getElementById('savePreferencesButton');
        this.preferencesError = document.getElementById('preferencesError');
        this.status = document.getElementById('status');
    }

    bindEvents() {
        this.authButton.addEventListener('click', () => this.handleAuthButtonClick());
        this.savePreferencesButton.addEventListener('click', () => this.save_options());
    }

    async initialize() {
        try {
            await this.checkAuthentication();
        } catch (error) {
            console.error('Initialization error:', error);
            this.updateAuthStatus('error', 'Failed to initialize');
        }
    }

    // Authentication Methods
    async checkAuthentication() {
        try {
            const storedToken = await this.getStoredAuthToken();
            if (storedToken) {
                const isValid = await this.verifyToken(storedToken);
                if (isValid) {
                    this.authToken = storedToken;
                    await this.restore_options();
                    this.updateAuthStatus('authenticated', 'Authenticated');
                    this.showAuthenticatedSections();
                } else {
                    this.updateAuthStatus('unauthenticated', 'Token expired');
                    this.showUnauthenticatedSections();
                }
            } else {
                this.updateAuthStatus('unauthenticated', 'Not authenticated');
                this.showUnauthenticatedSections();
            }
        } catch (error) {
            console.error('Authentication check error:', error);
            this.updateAuthStatus('error', 'Authentication check failed');
            this.showUnauthenticatedSections();
        }
    }

    updateAuthStatus(status, message) {
        this.statusText.textContent = message;
        this.statusDot.className = 'status-dot';
        
        switch (status) {
            case 'authenticated':
                this.statusDot.classList.add('authenticated');
                this.authButton.style.display = 'none';
                break;
            case 'unauthenticated':
                this.statusDot.classList.add('unauthenticated');
                this.authButton.style.display = 'block';
                this.authButton.textContent = 'Login';
                break;
            case 'error':
                this.statusDot.style.background = '#ef4444';
                this.authButton.style.display = 'block';
                this.authButton.textContent = 'Retry';
                break;
        }
    }

    showAuthenticatedSections() {
        this.preferencesSection.style.display = 'block';
    }

    showUnauthenticatedSections() {
        this.preferencesSection.style.display = 'none';
    }

    handleAuthButtonClick() {
        // Open the popup for authentication
        chrome.runtime.sendMessage({ action: 'openPopup' });
    }

    // User Preferences Methods - save_options function
    async save_options() {
        try {
            this.savePreferencesButton.disabled = true;
            this.savePreferencesButton.textContent = 'Saving...';
            this.preferencesError.textContent = '';

            // Get values from the dropdowns
            const preferences = {
                base_language: this.baseLanguage.value,
                target_language: this.targetLanguage.value,
                proficiency_level: this.proficiencyLevel.value
            };

            // Send PUT request to backend
            const response = await fetch(`${this.apiBaseUrl}/api/v1/preferences`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.authToken}`
                },
                body: JSON.stringify(preferences)
            });

            if (!response.ok) {
                throw new Error('Failed to save preferences');
            }

            this.userPreferences = preferences;
            
            // Update status to let user know options were saved
            this.status.textContent = 'Preferences saved successfully!';
            setTimeout(() => {
                this.status.textContent = '';
            }, 2000);

        } catch (error) {
            console.error('Error saving preferences:', error);
            this.preferencesError.textContent = error.message;
        } finally {
            this.savePreferencesButton.disabled = false;
            this.savePreferencesButton.textContent = 'Save Preferences';
        }
    }

    // User Preferences Methods - restore_options function
    async restore_options() {
        try {
            // GET user's preferences from backend
            const response = await fetch(`${this.apiBaseUrl}/api/v1/preferences`, {
                headers: {
                    'Authorization': `Bearer ${this.authToken}`
                }
            });

            if (response.ok) {
                this.userPreferences = await response.json();
                this.populatePreferencesForm();
            } else if (response.status === 404) {
                // User doesn't have preferences set yet, use defaults
                this.userPreferences = {
                    base_language: 'en',
                    target_language: 'en',
                    proficiency_level: 'B1'
                };
                this.populatePreferencesForm();
            } else {
                throw new Error('Failed to load preferences');
            }
        } catch (error) {
            console.error('Error loading preferences:', error);
            // Use default values if loading fails
            this.userPreferences = {
                base_language: 'en',
                target_language: 'en',
                proficiency_level: 'B1'
            };
            this.populatePreferencesForm();
        }
    }

    populatePreferencesForm() {
        if (this.userPreferences) {
            this.baseLanguage.value = this.userPreferences.base_language;
            this.targetLanguage.value = this.userPreferences.target_language;
            this.proficiencyLevel.value = this.userPreferences.proficiency_level;
        }
    }

    // Token Management
    async getStoredAuthToken() {
        return new Promise((resolve) => {
            chrome.storage.local.get(['authToken'], (result) => {
                resolve(result.authToken || null);
            });
        });
    }

    async verifyToken(token) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/health`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            return response.ok;
        } catch (error) {
            return false;
        }
    }
}

// Initialize options page when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new UniversalScraperOptions();
});