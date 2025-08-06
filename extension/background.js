// Universal Web Scraper Extension - Background Service Worker

class BackgroundServiceWorker {
    constructor() {
        this.initialize();
    }

    initialize() {
        // Handle extension installation
        chrome.runtime.onInstalled.addListener((details) => {
            this.handleInstallation(details);
        });

        // Handle messages from popup and content scripts
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            this.handleMessage(request, sender, sendResponse);
            return true; // Keep message channel open for async responses
        });

        // Handle tab updates
        chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
            this.handleTabUpdate(tabId, changeInfo, tab);
        });

        // Handle extension icon clicks
        chrome.action.onClicked.addListener((tab) => {
            this.handleIconClick(tab);
        });

        // Initialize storage
        this.initializeStorage();
    }

    async handleInstallation(details) {
        console.log('Extension installed:', details.reason);

        if (details.reason === 'install') {
            // First time installation
            await this.setupDefaultSettings();
            await this.loadInitialData();
            
            // Open welcome page
            chrome.tabs.create({
                url: chrome.runtime.getURL('welcome.html')
            });
        } else if (details.reason === 'update') {
            // Extension updated
            await this.handleUpdate();
        }
    }

    async setupDefaultSettings() {
        const defaultSettings = {
            theme: 'light',
            language: 'en',
            downloadFormat: 'markdown',
            analyticsEnabled: false,
            autoDetect: true,
            historyLimit: 10,
            historyRetentionDays: 30
        };

        await chrome.storage.sync.set(defaultSettings);
        console.log('Default settings initialized');
    }

    async loadInitialData() {
        try {
            // const apiBaseUrl = 'https://your-app.onrender.com'; // Replace with actual URL
            const apiBaseUrl = 'http://127.0.0.1:8000'; // Point to local backend
            
            const [whitelistResponse, blacklistResponse] = await Promise.all([
                fetch(`${apiBaseUrl}/v1/whitelist`),
                fetch(`${apiBaseUrl}/v1/blacklist`)
            ]);

            if (whitelistResponse.ok) {
                const whitelistData = await whitelistResponse.json();
                await chrome.storage.local.set({ whitelist: whitelistData.whitelist });
            }

            if (blacklistResponse.ok) {
                const blacklistData = await blacklistResponse.json();
                await chrome.storage.local.set({ blacklist: blacklistData.blacklist });
            }

            console.log('Initial data loaded');
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    async handleUpdate() {
        // Handle extension updates
        console.log('Extension updated');
        
        // Check for breaking changes and migrate data if needed
        await this.migrateDataIfNeeded();
    }

    async migrateDataIfNeeded() {
        // Check if data migration is needed
        const version = await chrome.storage.local.get('version');
        
        if (!version.version || version.version < '1.0.0') {
            // Perform data migration
            await chrome.storage.local.set({ version: '1.0.0' });
            console.log('Data migration completed');
        }
    }

    async handleMessage(request, sender, sendResponse) {
        try {
            switch (request.action) {
                case 'getSettings':
                    const settings = await chrome.storage.sync.get();
                    sendResponse({ success: true, data: settings });
                    break;

                case 'updateSettings':
                    await chrome.storage.sync.set(request.settings);
                    sendResponse({ success: true });
                    break;

                case 'getHistory':
                    const history = await this.getHistory();
                    sendResponse({ success: true, data: history });
                    break;

                case 'addToHistory':
                    await this.addToHistory(request.article);
                    sendResponse({ success: true });
                    break;

                case 'clearHistory':
                    await this.clearHistory();
                    sendResponse({ success: true });
                    break;

                case 'getAnalytics':
                    if (request.enabled) {
                        const analytics = await this.getAnalytics();
                        sendResponse({ success: true, data: analytics });
                    } else {
                        sendResponse({ success: false, error: 'Analytics disabled' });
                    }
                    break;

                case 'logEvent':
                    if (request.enabled) {
                        await this.logEvent(request.event, request.data);
                        sendResponse({ success: true });
                    } else {
                        sendResponse({ success: false, error: 'Analytics disabled' });
                    }
                    break;

                case 'checkApiStatus':
                    const status = await this.checkApiStatus();
                    sendResponse({ success: true, data: status });
                    break;

                default:
                    sendResponse({ success: false, error: 'Unknown action' });
            }
        } catch (error) {
            console.error('Error handling message:', error);
            sendResponse({ success: false, error: error.message });
        }
    }

    async handleTabUpdate(tabId, changeInfo, tab) {
        // Update extension icon based on tab content
        if (changeInfo.status === 'complete' && tab.url) {
            await this.updateIconForTab(tab);
        }
    }

    async updateIconForTab(tab) {
        try {
            // Check if tab is supported
            const domain = new URL(tab.url).hostname.replace('www.', '');
            
            const { whitelist, blacklist } = await chrome.storage.local.get(['whitelist', 'blacklist']);
            
            let iconState = 'disabled';
            
            if (blacklist && blacklist.includes(domain)) {
                iconState = 'disabled';
            } else if (whitelist && whitelist.includes(domain)) {
                iconState = 'premium';
            } else {
                // Check if it's an article page
                const isArticle = await this.checkIfArticlePage(tab.id);
                iconState = isArticle ? 'detected' : 'disabled';
            }

            // Update icon (you would need different icon files for each state)
            await chrome.action.setIcon({
                path: {
                    16: `icons/icon16_${iconState}.png`,
                    32: `icons/icon32_${iconState}.png`,
                    48: `icons/icon48_${iconState}.png`,
                    128: `icons/icon128_${iconState}.png`
                },
                tabId: tab.id
            });

        } catch (error) {
            console.error('Error updating icon:', error);
        }
    }

    async checkIfArticlePage(tabId) {
        try {
            const response = await chrome.tabs.sendMessage(tabId, { action: 'analyzePage' });
            return response && response.score >= 5;
        } catch (error) {
            // Content script not available or error
            return false;
        }
    }

    async handleIconClick(tab) {
        // Open popup when icon is clicked
        // This is handled automatically by the manifest
    }

    async initializeStorage() {
        // Initialize storage with default values if not exists
        const { history, analytics } = await chrome.storage.local.get(['history', 'analytics']);
        
        if (!history) {
            await chrome.storage.local.set({ history: [] });
        }
        
        if (!analytics) {
            await chrome.storage.local.set({ analytics: [] });
        }
    }

    async getHistory() {
        const { history } = await chrome.storage.local.get('history');
        return history || [];
    }

    async addToHistory(article) {
        const { history } = await chrome.storage.local.get('history');
        const currentHistory = history || [];
        
        // Add timestamp
        article.timestamp = new Date().toISOString();
        
        // Add to beginning of history
        currentHistory.unshift(article);
        
        // Limit history size
        const settings = await chrome.storage.sync.get('historyLimit');
        const limit = settings.historyLimit || 10;
        
        if (currentHistory.length > limit) {
            currentHistory.splice(limit);
        }
        
        await chrome.storage.local.set({ history: currentHistory });
    }

    async clearHistory() {
        await chrome.storage.local.set({ history: [] });
    }

    async getAnalytics() {
        const { analytics } = await chrome.storage.local.get('analytics');
        return analytics || [];
    }

    async logEvent(event, data) {
        const { analytics } = await chrome.storage.local.get('analytics');
        const currentAnalytics = analytics || [];
        
        const eventLog = {
            event,
            data,
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent
        };
        
        currentAnalytics.push(eventLog);
        
        // Keep only last 100 events
        if (currentAnalytics.length > 100) {
            currentAnalytics.splice(0, currentAnalytics.length - 100);
        }
        
        await chrome.storage.local.set({ analytics: currentAnalytics });
    }

    async checkApiStatus() {
        try {
            const apiBaseUrl = 'https://your-app.onrender.com'; // Replace with actual URL
            const response = await fetch(`${apiBaseUrl}/health`);
            
            if (response.ok) {
                const data = await response.json();
                return {
                    status: 'connected',
                    responseTime: Date.now(),
                    version: data.version
                };
            } else {
                return {
                    status: 'error',
                    error: `HTTP ${response.status}`
                };
            }
        } catch (error) {
            return {
                status: 'offline',
                error: error.message
            };
        }
    }

    // Periodic tasks
    async performPeriodicTasks() {
        // Clean up old history entries
        await this.cleanupHistory();
        
        // Update whitelist/blacklist
        await this.updateLists();
        
        // Send analytics data (if enabled)
        await this.sendAnalytics();
    }

    async cleanupHistory() {
        const { history } = await chrome.storage.local.get('history');
        const settings = await chrome.storage.sync.get('historyRetentionDays');
        const retentionDays = settings.historyRetentionDays || 30;
        
        if (history && history.length > 0) {
            const cutoffDate = new Date();
            cutoffDate.setDate(cutoffDate.getDate() - retentionDays);
            
            const filteredHistory = history.filter(article => {
                const articleDate = new Date(article.timestamp);
                return articleDate > cutoffDate;
            });
            
            if (filteredHistory.length !== history.length) {
                await chrome.storage.local.set({ history: filteredHistory });
                console.log(`Cleaned up ${history.length - filteredHistory.length} old history entries`);
            }
        }
    }

    async updateLists() {
        try {
            const apiBaseUrl = 'https://your-app.onrender.com'; // Replace with actual URL
            
            const [whitelistResponse, blacklistResponse] = await Promise.all([
                fetch(`${apiBaseUrl}/v1/whitelist`),
                fetch(`${apiBaseUrl}/v1/blacklist`)
            ]);

            if (whitelistResponse.ok) {
                const whitelistData = await whitelistResponse.json();
                await chrome.storage.local.set({ whitelist: whitelistData.whitelist });
            }

            if (blacklistResponse.ok) {
                const blacklistData = await blacklistResponse.json();
                await chrome.storage.local.set({ blacklist: blacklistData.blacklist });
            }

            console.log('Lists updated successfully');
        } catch (error) {
            console.error('Error updating lists:', error);
        }
    }

    async sendAnalytics() {
        const settings = await chrome.storage.sync.get('analyticsEnabled');
        
        if (settings.analyticsEnabled) {
            const { analytics } = await chrome.storage.local.get('analytics');
            
            if (analytics && analytics.length > 0) {
                try {
                    const apiBaseUrl = 'https://your-app.onrender.com'; // Replace with actual URL
                    await fetch(`${apiBaseUrl}/v1/analytics`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ events: analytics })
                    });
                    
                    // Clear sent analytics
                    await chrome.storage.local.set({ analytics: [] });
                    console.log('Analytics sent successfully');
                } catch (error) {
                    console.error('Error sending analytics:', error);
                }
            }
        }
    }
}

// Initialize background service worker
new BackgroundServiceWorker();

// Set up periodic tasks (every 6 hours)
setInterval(() => {
    new BackgroundServiceWorker().performPeriodicTasks();
}, 6 * 60 * 60 * 1000); 