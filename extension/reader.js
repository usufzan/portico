// Universal Reader - Article Display and Settings Management

class UniversalReader {
    constructor() {
        this.articleData = null;
        this.settings = {
            fontSize: 'medium',
            lineHeight: 'normal',
            theme: 'light',
            width: 'medium'
        };
        
        this.initializeElements();
        this.bindEvents();
        this.loadSettings();
        this.loadArticle();
    }

    // DOM Elements
    initializeElements() {
        // Header elements
        this.articleTitle = document.getElementById('articleTitle');
        this.articleAuthor = document.getElementById('articleAuthor');
        this.articleWordCount = document.getElementById('articleWordCount');
        this.articleReadingTime = document.getElementById('articleReadingTime');
        
        // Content elements
        this.loadingState = document.getElementById('loadingState');
        this.errorState = document.getElementById('errorState');
        this.articleContent = document.getElementById('articleContent');
        this.articleBody = document.getElementById('articleBody');
        
        // Error elements
        this.errorMessage = document.getElementById('errorMessage');
        
        // Buttons
        this.backButton = document.getElementById('backButton');
        this.downloadButton = document.getElementById('downloadButton');
        this.copyButton = document.getElementById('copyButton');
        this.settingsButton = document.getElementById('settingsButton');
        this.retryButton = document.getElementById('retryButton');
        this.closeButton = document.getElementById('closeButton');
        this.fullscreenButton = document.getElementById('fullscreenButton');
        
        // Modal elements
        this.settingsModal = document.getElementById('settingsModal');
        this.closeSettingsButton = document.getElementById('closeSettingsButton');
        this.saveSettingsButton = document.getElementById('saveSettingsButton');
        this.resetSettingsButton = document.getElementById('resetSettingsButton');
        
        // Settings form elements
        this.fontSizeSelect = document.getElementById('fontSize');
        this.lineHeightSelect = document.getElementById('lineHeight');
        this.themeSelect = document.getElementById('theme');
        this.widthSelect = document.getElementById('width');
    }

    // Event Binding
    bindEvents() {
        // Navigation buttons
        this.backButton.addEventListener('click', () => this.goBack());
        this.closeButton.addEventListener('click', () => this.closeTab());
        
        // Action buttons
        this.downloadButton.addEventListener('click', () => this.downloadArticle());
        this.copyButton.addEventListener('click', () => this.copyArticle());
        this.settingsButton.addEventListener('click', () => this.openSettings());
        this.fullscreenButton.addEventListener('click', () => this.toggleFullscreen());
        
        // Error handling
        this.retryButton.addEventListener('click', () => this.loadArticle());
        
        // Settings modal
        this.closeSettingsButton.addEventListener('click', () => this.closeSettings());
        this.saveSettingsButton.addEventListener('click', () => this.saveSettings());
        this.resetSettingsButton.addEventListener('click', () => this.resetSettings());
        
        // Modal backdrop
        this.settingsModal.addEventListener('click', (e) => {
            if (e.target === this.settingsModal) {
                this.closeSettings();
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }

    // Load article from storage
    async loadArticle() {
        try {
            this.showLoading();
            
            // Get article data from storage
            const result = await chrome.storage.local.get('currentArticle');
            
            if (!result.currentArticle) {
                throw new Error('No article data found');
            }
            
            this.articleData = result.currentArticle;
            this.displayArticle();
            
            // Clean up storage
            await chrome.storage.local.remove('currentArticle');
            
        } catch (error) {
            console.error('Error loading article:', error);
            this.showError('Failed to load article', error.message);
        }
    }

    // Display article content
    displayArticle() {
        try {
            // Update header
            this.articleTitle.textContent = this.articleData.title || 'Untitled';
            this.articleAuthor.textContent = this.articleData.metadata.author || 'Unknown';
            this.articleWordCount.textContent = `${this.articleData.metadata.word_count} words`;
            this.articleReadingTime.textContent = `${this.articleData.metadata.reading_time_minutes.toFixed(1)} min read`;
            
            // Display content
            const content = this.articleData.content.clean_html || this.articleData.content.markdown;
            
            if (this.articleData.content.clean_html) {
                // Display as HTML
                this.articleBody.innerHTML = content;
            } else {
                // Convert markdown to HTML (simple conversion)
                this.articleBody.innerHTML = this.markdownToHtml(content);
            }
            
            // Show content
            this.hideLoading();
            this.articleContent.style.display = 'block';
            
            // Apply settings
            this.applySettings();
            
        } catch (error) {
            console.error('Error displaying article:', error);
            this.showError('Failed to display article', error.message);
        }
    }

    // Simple markdown to HTML conversion
    markdownToHtml(markdown) {
        return markdown
            // Headers
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            // Bold
            .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.*)\*/gim, '<em>$1</em>')
            // Links
            .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2">$1</a>')
            // Code blocks
            .replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>')
            // Inline code
            .replace(/`([^`]+)`/gim, '<code>$1</code>')
            // Lists
            .replace(/^\* (.*$)/gim, '<li>$1</li>')
            .replace(/^- (.*$)/gim, '<li>$1</li>')
            // Paragraphs
            .replace(/\n\n/g, '</p><p>')
            .replace(/^(?!<[h|li|pre|ul|ol])(.*$)/gim, '<p>$1</p>')
            // Clean up
            .replace(/<p><\/p>/g, '')
            .replace(/<p>(<h[1-6]>.*<\/h[1-6]>)<\/p>/g, '$1')
            .replace(/<p>(<li>.*<\/li>)<\/p>/g, '<ul>$1</ul>')
            .replace(/<\/ul>\s*<ul>/g, '');
    }

    // Show loading state
    showLoading() {
        this.loadingState.style.display = 'flex';
        this.errorState.style.display = 'none';
        this.articleContent.style.display = 'none';
    }

    // Hide loading state
    hideLoading() {
        this.loadingState.style.display = 'none';
    }

    // Show error state
    showError(title, message) {
        this.hideLoading();
        this.errorState.style.display = 'flex';
        this.articleContent.style.display = 'none';
        
        this.errorMessage.textContent = message;
    }

    // Navigation
    goBack() {
        window.history.back();
    }

    closeTab() {
        window.close();
    }

    // Article actions
    async downloadArticle() {
        try {
            const markdown = this.articleData.content.markdown;
            const title = this.articleData.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
            
            const blob = new Blob([markdown], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `${title}.md`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            this.showFeedback('Article downloaded successfully!');
            
        } catch (error) {
            console.error('Error downloading article:', error);
            this.showFeedback('Failed to download article', 'error');
        }
    }

    async copyArticle() {
        try {
            const markdown = this.articleData.content.markdown;
            await navigator.clipboard.writeText(markdown);
            
            this.showFeedback('Article copied to clipboard!');
            
        } catch (error) {
            console.error('Error copying article:', error);
            this.showFeedback('Failed to copy article', 'error');
        }
    }

    // Settings management
    async loadSettings() {
        try {
            const result = await chrome.storage.sync.get([
                'fontSize', 'lineHeight', 'theme', 'width'
            ]);
            
            this.settings = {
                fontSize: result.fontSize || 'medium',
                lineHeight: result.lineHeight || 'normal',
                theme: result.theme || 'light',
                width: result.width || 'medium'
            };
            
            // Update form values
            this.fontSizeSelect.value = this.settings.fontSize;
            this.lineHeightSelect.value = this.settings.lineHeight;
            this.themeSelect.value = this.settings.theme;
            this.widthSelect.value = this.settings.width;
            
            this.applySettings();
            
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }

    async saveSettings() {
        try {
            const newSettings = {
                fontSize: this.fontSizeSelect.value,
                lineHeight: this.lineHeightSelect.value,
                theme: this.themeSelect.value,
                width: this.widthSelect.value
            };
            
            await chrome.storage.sync.set(newSettings);
            this.settings = newSettings;
            
            this.applySettings();
            this.closeSettings();
            
            this.showFeedback('Settings saved!');
            
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showFeedback('Failed to save settings', 'error');
        }
    }

    async resetSettings() {
        try {
            const defaultSettings = {
                fontSize: 'medium',
                lineHeight: 'normal',
                theme: 'light',
                width: 'medium'
            };
            
            await chrome.storage.sync.set(defaultSettings);
            this.settings = defaultSettings;
            
            // Update form values
            this.fontSizeSelect.value = defaultSettings.fontSize;
            this.lineHeightSelect.value = defaultSettings.lineHeight;
            this.themeSelect.value = defaultSettings.theme;
            this.widthSelect.value = defaultSettings.width;
            
            this.applySettings();
            
            this.showFeedback('Settings reset to defaults!');
            
        } catch (error) {
            console.error('Error resetting settings:', error);
            this.showFeedback('Failed to reset settings', 'error');
        }
    }

    // Apply settings to the page
    applySettings() {
        const container = document.querySelector('.reader-container');
        const contentWrapper = document.querySelector('.content-wrapper');
        
        // Remove existing classes
        container.className = 'reader-container';
        contentWrapper.className = 'content-wrapper';
        
        // Apply theme
        if (this.settings.theme !== 'light') {
            container.classList.add(`theme-${this.settings.theme}`);
        }
        
        // Apply font size
        const fontSizeMap = {
            small: '16px',
            medium: '18px',
            large: '20px',
            xlarge: '22px'
        };
        
        const articleBody = document.querySelector('.article-body');
        if (articleBody) {
            articleBody.style.fontSize = fontSizeMap[this.settings.fontSize];
        }
        
        // Apply line height
        const lineHeightMap = {
            tight: '1.4',
            normal: '1.8',
            relaxed: '2.2'
        };
        
        if (articleBody) {
            articleBody.style.lineHeight = lineHeightMap[this.settings.lineHeight];
        }
        
        // Apply content width
        const widthMap = {
            narrow: '600px',
            medium: '800px',
            wide: '1000px'
        };
        
        contentWrapper.style.maxWidth = widthMap[this.settings.width];
    }

    // Modal management
    openSettings() {
        this.settingsModal.style.display = 'flex';
    }

    closeSettings() {
        this.settingsModal.style.display = 'none';
    }

    // Fullscreen toggle
    toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
            this.fullscreenButton.textContent = '⛶';
        } else {
            document.exitFullscreen();
            this.fullscreenButton.textContent = '⛶';
        }
    }

    // Keyboard shortcuts
    handleKeyboard(e) {
        // Escape key closes modals
        if (e.key === 'Escape') {
            if (this.settingsModal.style.display === 'flex') {
                this.closeSettings();
            }
        }
        
        // Ctrl/Cmd + S saves settings
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            if (this.settingsModal.style.display === 'flex') {
                this.saveSettings();
            }
        }
        
        // Ctrl/Cmd + D downloads article
        if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
            e.preventDefault();
            this.downloadArticle();
        }
        
        // Ctrl/Cmd + C copies article
        if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
            e.preventDefault();
            this.copyArticle();
        }
        
        // F11 or F for fullscreen
        if (e.key === 'F11' || e.key === 'f') {
            e.preventDefault();
            this.toggleFullscreen();
        }
    }

    // Show feedback message
    showFeedback(message, type = 'success') {
        // Create feedback element
        const feedback = document.createElement('div');
        feedback.className = `feedback feedback-${type}`;
        feedback.textContent = message;
        
        // Style the feedback
        feedback.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 6px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        
        if (type === 'success') {
            feedback.style.background = '#10b981';
        } else {
            feedback.style.background = '#ef4444';
        }
        
        // Add to page
        document.body.appendChild(feedback);
        
        // Remove after 3 seconds
        setTimeout(() => {
            feedback.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (feedback.parentNode) {
                    feedback.parentNode.removeChild(feedback);
                }
            }, 300);
        }, 3000);
    }
}

// Add CSS animations for feedback
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Initialize reader when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new UniversalReader();
}); 