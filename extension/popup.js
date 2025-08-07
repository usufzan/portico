// Universal Web Scraper Extension - Popup Logic

class UniversalScraperPopup {
    constructor() {
        this.currentUrl = null;
        this.currentTier = null;
        this.whitelist = [];
        this.blacklist = [];
        this.authToken = null;
        this.userPreferences = null;
        //  this.apiBaseUrl = 'https://your-app.onrender.com'; // Replace with your actual URL
        this.apiBaseUrl = 'http://127.0.0.1:8000'; // Point to local backend
        
        this.initializeElements();
        this.bindEvents();
        this.initialize();
    }

    // DOM Elements
    initializeElements() {
        // Authentication elements
        this.authSection = document.getElementById('authSection');
        this.loginTab = document.getElementById('loginTab');
        this.registerTab = document.getElementById('registerTab');
        this.loginForm = document.getElementById('loginForm');
        this.registerForm = document.getElementById('registerForm');
        this.loginEmail = document.getElementById('loginEmail');
        this.loginPassword = document.getElementById('loginPassword');
        this.registerEmail = document.getElementById('registerEmail');
        this.registerPassword = document.getElementById('registerPassword');
        this.loginButton = document.getElementById('loginButton');
        this.registerButton = document.getElementById('registerButton');
        this.loginError = document.getElementById('loginError');
        this.registerError = document.getElementById('registerError');

        // Preferences elements
        this.preferencesSection = document.getElementById('preferencesSection');
        this.baseLanguage = document.getElementById('baseLanguage');
        this.targetLanguage = document.getElementById('targetLanguage');
        this.proficiencyLevel = document.getElementById('proficiencyLevel');
        this.savePreferencesButton = document.getElementById('savePreferencesButton');
        this.preferencesError = document.getElementById('preferencesError');

        // Main content elements
        this.mainContent = document.getElementById('mainContent');

        // Status elements
        this.statusDot = document.getElementById('statusDot');
        this.statusText = document.getElementById('statusText');
        this.apiStatus = document.getElementById('apiStatus');

        // Tier containers
        this.goldTier = document.getElementById('goldTier');
        this.silverTier = document.getElementById('silverTier');
        this.bronzeTier = document.getElementById('bronzeTier');
        this.loadingState = document.getElementById('loadingState');

        // Progress elements
        this.progressContainer = document.getElementById('progressContainer');
        this.progressText = document.getElementById('progressText');
        this.progressFill = document.getElementById('progressFill');
        this.progressStages = document.getElementById('progressStages');

        // Results elements
        this.resultsSummary = document.getElementById('resultsSummary');
        this.wordCount = document.getElementById('wordCount');
        this.readingTime = document.getElementById('readingTime');

        // Error elements
        this.errorState = document.getElementById('errorState');
        this.errorTitle = document.getElementById('errorTitle');
        this.errorMessage = document.getElementById('errorMessage');

        // Buttons
        this.adaptButton = document.getElementById('adaptButton');
        this.adaptButtonSilver = document.getElementById('adaptButtonSilver');
        this.requestSupportButton = document.getElementById('requestSupportButton');
        this.openReaderButton = document.getElementById('openReaderButton');
        this.downloadButton = document.getElementById('downloadButton');
        this.copyButton = document.getElementById('copyButton');
        this.retryButton = document.getElementById('retryButton');
        this.reportButton = document.getElementById('reportButton');

        // Data storage
        this.currentArticleData = document.getElementById('currentArticleData');
        this.currentUrlElement = document.getElementById('currentUrl');
    }

    // Event Binding
    bindEvents() {
        // Authentication events
        this.loginTab.addEventListener('click', () => this.switchToLogin());
        this.registerTab.addEventListener('click', () => this.switchToRegister());
        this.loginButton.addEventListener('click', () => this.handleLogin());
        this.registerButton.addEventListener('click', () => this.handleRegister());

        // Preferences events
        this.savePreferencesButton.addEventListener('click', () => this.saveUserPreferences());

        // Main functionality events
        this.adaptButton.addEventListener('click', () => this.startScraping());
        this.adaptButtonSilver.addEventListener('click', () => this.startScraping());
        this.requestSupportButton.addEventListener('click', () => this.requestSiteSupport());
        this.openReaderButton.addEventListener('click', () => this.openReader());
        this.downloadButton.addEventListener('click', () => this.downloadArticle());
        this.copyButton.addEventListener('click', () => this.copyArticle());
        this.retryButton.addEventListener('click', () => this.retryScraping());
        this.reportButton.addEventListener('click', () => this.reportIssue());

        // Footer events
        document.getElementById('historyLink').addEventListener('click', (e) => {
            e.preventDefault();
            chrome.runtime.openOptionsPage();
        });
        document.getElementById('settingsLink').addEventListener('click', (e) => {
            e.preventDefault();
            chrome.runtime.openOptionsPage();
        });
        document.getElementById('logoutLink').addEventListener('click', (e) => {
            e.preventDefault();
            this.handleLogout();
        });
    }

    // Initialization
    async initialize() {
        try {
            await this.loadCurrentTab();
            await this.checkAuthentication();
        } catch (error) {
            console.error('Initialization error:', error);
            this.showError('Failed to initialize extension', error.message);
        }
    }

    // Load current tab information
    async loadCurrentTab() {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            this.currentUrl = tab.url;
            this.currentUrlElement.textContent = this.currentUrl;
            
            // Send message to content script to analyze the page
            const response = await chrome.tabs.sendMessage(tab.id, { action: 'analyzePage' });
            this.pageAnalysis = response;
        } catch (error) {
            console.error('Error loading current tab:', error);
            throw error;
        }
    }

    // Load whitelist and blacklist
    async loadWhitelistAndBlacklist() {
        try {
            // Try to load from cache first
            const cached = await chrome.storage.local.get(['whitelist', 'blacklist']);
            
            if (cached.whitelist && cached.blacklist) {
                this.whitelist = cached.whitelist;
                this.blacklist = cached.blacklist;
            }

            // Fetch fresh data from server
            const [whitelistResponse, blacklistResponse] = await Promise.all([
                fetch(`${this.apiBaseUrl}/v1/whitelist`),
                fetch(`${this.apiBaseUrl}/v1/blacklist`)
            ]);

            if (whitelistResponse.ok) {
                const whitelistData = await whitelistResponse.json();
                this.whitelist = whitelistData.whitelist;
            }

            if (blacklistResponse.ok) {
                const blacklistData = await blacklistResponse.json();
                this.blacklist = blacklistData.blacklist;
            }

            // Cache the data
            await chrome.storage.local.set({
                whitelist: this.whitelist,
                blacklist: this.blacklist
            });

        } catch (error) {
            console.error('Error loading lists:', error);
            // Continue with cached data if available
        }
    }

    // Detect tier based on current URL and page analysis
    async detectTier() {
        if (!this.currentUrl) {
            this.showBronzeTier();
            return;
        }

        const domain = new URL(this.currentUrl).hostname.replace('www.', '');

        // Check blacklist first
        if (this.blacklist.includes(domain)) {
            this.showBronzeTier();
            return;
        }

        // Check whitelist
        if (this.whitelist.includes(domain)) {
            this.showGoldTier();
            return;
        }

        // Smart detection for silver tier
        if (this.pageAnalysis && this.pageAnalysis.score >= 5) {
            this.showSilverTier();
            return;
        }

        // Default to bronze
        this.showBronzeTier();
    }

    // Show different tiers
    showGoldTier() {
        this.hideAllTiers();
        this.goldTier.style.display = 'block';
        this.currentTier = 'gold';
        this.updateStatus('premium');
    }

    showSilverTier() {
        this.hideAllTiers();
        this.silverTier.style.display = 'block';
        this.currentTier = 'silver';
        this.updateStatus('detected');
    }

    showBronzeTier() {
        this.hideAllTiers();
        this.bronzeTier.style.display = 'block';
        this.currentTier = 'bronze';
        this.updateStatus('unsupported');
    }

    hideAllTiers() {
        this.goldTier.style.display = 'none';
        this.silverTier.style.display = 'none';
        this.bronzeTier.style.display = 'none';
        this.loadingState.style.display = 'none';
        this.progressContainer.style.display = 'none';
        this.resultsSummary.style.display = 'none';
        this.errorState.style.display = 'none';
    }

    // Update status indicator
    updateStatus(status) {
        this.statusDot.className = 'status-dot';
        
        switch (status) {
            case 'ready':
                this.statusText.textContent = 'Ready';
                this.statusDot.style.background = '#4ade80';
                break;
            case 'premium':
                this.statusText.textContent = 'Premium Support';
                this.statusDot.style.background = '#f59e0b';
                break;
            case 'detected':
                this.statusText.textContent = 'Smart Detection';
                this.statusDot.style.background = '#6b7280';
                break;
            case 'unsupported':
                this.statusText.textContent = 'Not Supported';
                this.statusDot.style.background = '#ef4444';
                break;
            case 'loading':
                this.statusText.textContent = 'Processing...';
                this.statusDot.classList.add('loading');
                break;
            case 'error':
                this.statusText.textContent = 'Error';
                this.statusDot.classList.add('error');
                break;
            case 'unauthenticated':
                this.statusText.textContent = 'Not Authenticated';
                this.statusDot.style.background = '#f59e0b';
                break;
            case 'setup_required':
                this.statusText.textContent = 'Setup Required';
                this.statusDot.style.background = '#6b7280';
                break;
        }
    }

    // Start scraping process
    async startScraping() {
        try {
            this.hideAllTiers();
            this.progressContainer.style.display = 'block';
            this.updateStatus('loading');
            
            // Show loading state on button
            const button = this.currentTier === 'gold' ? this.adaptButton : this.adaptButtonSilver;
            const loading = button.querySelector('.button-loading');
            loading.style.display = 'block';
            button.disabled = true;

            // Start SSE connection
            await this.startSSEConnection();

        } catch (error) {
            console.error('Scraping error:', error);
            this.showError('Failed to start scraping', error.message);
        }
    }

    // Start Server-Sent Events connection
    async startSSEConnection() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/scrape-stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${await this.getAuthToken()}`
                },
                body: JSON.stringify({ url: this.currentUrl })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.slice(6));
                        this.handleSSEEvent(data);
                    }
                }
            }

        } catch (error) {
            console.error('SSE connection error:', error);
            this.showError('Connection failed', error.message);
        }
    }

    // Handle SSE events
    handleSSEEvent(data) {
        console.log('SSE Event received:', data);
        
        switch (data.status) {
            case 'progress':
                console.log('Progress update:', data.message, `(${data.current_stage}/${data.total_stages})`);
                this.updateProgress(data);
                break;
            case 'complete':
                console.log('Scraping completed successfully:', data.data ? 'with data' : 'no data');
                this.handleSuccess(data);
                break;
            case 'error':
                console.error('Scraping error:', data.error || 'Unknown error');
                this.handleError(data);
                break;
            default:
                console.warn('Unknown SSE event status:', data.status);
        }
    }

    // Update progress display
    updateProgress(data) {
        const progress = (data.current_stage / data.total_stages) * 100;
        this.progressFill.style.width = `${progress}%`;
        this.progressText.textContent = data.message;

        // Update stages
        this.updateStages(data.current_stage, data.total_stages, data.stage);
    }

    // Update progress stages
    updateStages(currentStage, totalStages, currentStageName) {
        const stages = [
            'Initialization',
            'Fast Path',
            'Browser Setup',
            'Navigation',
            'Content Extraction',
            'Processing'
        ];

        this.progressStages.innerHTML = '';
        
        stages.forEach((stage, index) => {
            const stageElement = document.createElement('div');
            stageElement.className = 'stage-item';
            
            if (index + 1 < currentStage) {
                stageElement.classList.add('completed');
                stageElement.innerHTML = `✅ ${stage}`;
            } else if (index + 1 === currentStage) {
                stageElement.classList.add('current');
                stageElement.innerHTML = `🔄 ${stage}`;
            } else {
                stageElement.classList.add('pending');
                stageElement.innerHTML = `⏳ ${stage}`;
            }
            
            this.progressStages.appendChild(stageElement);
        });
    }

    // Handle successful scraping
    handleSuccess(data) {
        console.log('Handling success with data:', data);
        
        this.hideAllTiers();
        this.resultsSummary.style.display = 'block';
        
        // Validate data structure
        if (!data.data) {
            console.error('Success event missing data payload');
            this.showError('Scraping Error', 'Article was scraped but data is missing. Please try again.');
            return;
        }
        
        // Store article data
        this.currentArticleData.textContent = JSON.stringify(data.data);
        
        // Update metadata with error handling
        try {
            const metadata = data.data.metadata || {};
            this.wordCount.textContent = `${metadata.word_count || 0} words`;
            this.readingTime.textContent = `${(metadata.reading_time_minutes || 0).toFixed(1)} min read`;
        } catch (error) {
            console.error('Error updating metadata display:', error);
            this.wordCount.textContent = '0 words';
            this.readingTime.textContent = '0 min read';
        }
        
        this.updateStatus('ready');
        console.log('Success handling completed');
    }

    // Handle scraping error
    handleError(data) {
        this.hideAllTiers();
        this.errorState.style.display = 'block';
        
        this.errorTitle.textContent = 'Adaptation Failed';
        this.errorMessage.textContent = data.error || 'An unexpected error occurred';
        
        this.updateStatus('error');
    }

    // Show error state
    showError(title, message) {
        this.hideAllTiers();
        this.errorState.style.display = 'block';
        
        this.errorTitle.textContent = title;
        this.errorMessage.textContent = message;
        
        this.updateStatus('error');
    }

    // Open reader tab
    async openReader() {
        try {
            const articleData = JSON.parse(this.currentArticleData.textContent);
            
            // Store article data for reader
            await chrome.storage.local.set({ currentArticle: articleData });
            
            // Open reader tab
            await chrome.tabs.create({
                url: chrome.runtime.getURL('reader.html')
            });
            
            // Close popup
            window.close();
            
        } catch (error) {
            console.error('Error opening reader:', error);
            this.showError('Failed to open reader', error.message);
        }
    }

    // Download article as markdown
    async downloadArticle() {
        try {
            const articleData = JSON.parse(this.currentArticleData.textContent);
            const markdown = articleData.content.markdown;
            
            const blob = new Blob([markdown], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `${articleData.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.md`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
        } catch (error) {
            console.error('Error downloading article:', error);
            this.showError('Failed to download', error.message);
        }
    }

    // Copy article to clipboard
    async copyArticle() {
        try {
            const articleData = JSON.parse(this.currentArticleData.textContent);
            const markdown = articleData.content.markdown;
            
            await navigator.clipboard.writeText(markdown);
            
            // Show success feedback
            const button = this.copyButton;
            const originalText = button.textContent;
            button.textContent = '✅ Copied!';
            setTimeout(() => {
                button.textContent = originalText;
            }, 2000);
            
        } catch (error) {
            console.error('Error copying article:', error);
            this.showError('Failed to copy', error.message);
        }
    }

    // Request site support
    async requestSiteSupport() {
        try {
            const domain = new URL(this.currentUrl).hostname.replace('www.', '');
            
            const response = await fetch(`${this.apiBaseUrl}/v1/requests`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${await this.getAuthToken()}`
                },
                body: JSON.stringify({ requested_domain: domain })
            });

            if (response.ok) {
                // Show success feedback
                this.requestSupportButton.textContent = '✅ Requested!';
                setTimeout(() => {
                    this.requestSupportButton.textContent = 'Request Site Support';
                }, 3000);
            } else {
                throw new Error('Failed to submit request');
            }
            
        } catch (error) {
            console.error('Error requesting site support:', error);
            this.showError('Failed to submit request', error.message);
        }
    }

    // Retry scraping
    retryScraping() {
        this.startScraping();
    }

    // Report issue
    reportIssue() {
        // Open options page for issue reporting
        chrome.runtime.openOptionsPage();
    }

    // Authentication Methods
    async checkAuthentication() {
        try {
            // Check if we have a stored token
            const storedToken = await this.getStoredAuthToken();
            if (storedToken) {
                // Verify token is still valid
                const isValid = await this.verifyToken(storedToken);
                if (isValid) {
                    this.authToken = storedToken;
                    await this.loadUserPreferences();
                    this.showMainContent();
                } else {
                    this.showAuthentication();
                }
            } else {
                this.showAuthentication();
            }
        } catch (error) {
            console.error('Authentication check error:', error);
            this.showAuthentication();
        }
    }

    showAuthentication() {
        this.authSection.style.display = 'block';
        this.preferencesSection.style.display = 'none';
        this.mainContent.style.display = 'none';
        this.updateStatus('unauthenticated');
    }

    async showMainContent() {
        this.authSection.style.display = 'none';
        this.preferencesSection.style.display = 'none';
        this.mainContent.style.display = 'block';
        
        await this.loadWhitelistAndBlacklist();
        await this.detectTier();
        this.updateStatus('ready');
    }

    switchToLogin() {
        this.loginTab.classList.add('active');
        this.registerTab.classList.remove('active');
        this.loginForm.style.display = 'flex';
        this.registerForm.style.display = 'none';
        this.loginError.textContent = '';
        this.registerError.textContent = '';
    }

    switchToRegister() {
        this.registerTab.classList.add('active');
        this.loginTab.classList.remove('active');
        this.registerForm.style.display = 'flex';
        this.loginForm.style.display = 'none';
        this.loginError.textContent = '';
        this.registerError.textContent = '';
    }

    async handleLogin() {
        try {
            this.loginButton.disabled = true;
            this.loginButton.textContent = 'Logging in...';
            this.loginError.textContent = '';

            const email = this.loginEmail.value.trim();
            const password = this.loginPassword.value;

            if (!email || !password) {
                throw new Error('Please fill in all fields');
            }

            const response = await fetch(`${this.apiBaseUrl}/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Login failed');
            }

            const data = await response.json();
            this.authToken = data.access_token;
            await this.storeAuthToken(this.authToken);
            
            await this.loadUserPreferences();
            this.showMainContent();

        } catch (error) {
            console.error('Login error:', error);
            this.loginError.textContent = error.message;
        } finally {
            this.loginButton.disabled = false;
            this.loginButton.textContent = 'Login';
        }
    }

    async handleRegister() {
        try {
            this.registerButton.disabled = true;
            this.registerButton.textContent = 'Registering...';
            this.registerError.textContent = '';

            const email = this.registerEmail.value.trim();
            const password = this.registerPassword.value;

            if (!email || !password) {
                throw new Error('Please fill in all fields');
            }

            if (password.length < 6) {
                throw new Error('Password must be at least 6 characters');
            }

            const response = await fetch(`${this.apiBaseUrl}/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Registration failed');
            }

            // Auto-login after successful registration
            await this.handleLogin();

        } catch (error) {
            console.error('Registration error:', error);
            this.registerError.textContent = error.message;
        } finally {
            this.registerButton.disabled = false;
            this.registerButton.textContent = 'Register';
        }
    }

    // User Preferences Methods
    async loadUserPreferences() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/v1/preferences`, {
                headers: {
                    'Authorization': `Bearer ${this.authToken}`
                }
            });

            if (response.ok) {
                this.userPreferences = await response.json();
                this.populatePreferencesForm();
                // Show main content when preferences are successfully loaded
                this.showMainContent();
            } else if (response.status === 404) {
                // User doesn't have preferences set yet
                this.showPreferencesSetup();
            } else {
                throw new Error('Failed to load preferences');
            }
        } catch (error) {
            console.error('Error loading preferences:', error);
            this.showPreferencesSetup();
        }
    }

    showPreferencesSetup() {
        this.authSection.style.display = 'none';
        this.preferencesSection.style.display = 'block';
        this.mainContent.style.display = 'none';
        this.updateStatus('setup_required');
    }

    populatePreferencesForm() {
        if (this.userPreferences) {
            this.baseLanguage.value = this.userPreferences.base_language;
            this.targetLanguage.value = this.userPreferences.target_language;
            this.proficiencyLevel.value = this.userPreferences.proficiency_level;
        }
    }

    async saveUserPreferences() {
        try {
            this.savePreferencesButton.disabled = true;
            this.savePreferencesButton.textContent = 'Saving...';
            this.preferencesError.textContent = '';

            const preferences = {
                base_language: this.baseLanguage.value,
                target_language: this.targetLanguage.value,
                proficiency_level: this.proficiencyLevel.value
            };

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
            this.showMainContent();

        } catch (error) {
            console.error('Error saving preferences:', error);
            this.preferencesError.textContent = error.message;
        } finally {
            this.savePreferencesButton.disabled = false;
            this.savePreferencesButton.textContent = 'Save Preferences';
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

    async storeAuthToken(token) {
        return new Promise((resolve) => {
            chrome.storage.local.set({ authToken: token }, resolve);
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

    // Updated getAuthToken method
    async getAuthToken() {
        if (!this.authToken) {
            throw new Error('Not authenticated');
        }
        return this.authToken;
    }

    // Logout functionality
    async handleLogout() {
        try {
            // Clear stored token
            await this.clearStoredAuthToken();
            this.authToken = null;
            this.userPreferences = null;
            
            // Show authentication screen
            this.showAuthentication();
            
        } catch (error) {
            console.error('Logout error:', error);
        }
    }

    async clearStoredAuthToken() {
        return new Promise((resolve) => {
            chrome.storage.local.remove(['authToken'], resolve);
        });
    }
}

// Initialize popup when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new UniversalScraperPopup();
}); 