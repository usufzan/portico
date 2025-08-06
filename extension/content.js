// Universal Web Scraper Extension - Content Script
// Analyzes web pages for smart detection and tier classification

class PageAnalyzer {
    constructor() {
        this.score = 0;
        this.analysis = {};
        this.initialize();
    }

    initialize() {
        // Listen for messages from popup
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            if (request.action === 'analyzePage') {
                const analysis = this.analyzePage();
                sendResponse(analysis);
            }
        });
    }

    analyzePage() {
        this.score = 0;
        this.analysis = {
            score: 0,
            indicators: [],
            penalties: [],
            summary: ''
        };

        // High-value indicators
        this.checkArticleTag();
        this.checkHeadlineStructure();
        this.checkContentLength();
        this.checkParagraphCount();

        // Negative indicators
        this.checkLoginForms();
        this.checkSearchPages();
        this.checkSocialMedia();

        // Calculate final score
        this.analysis.score = Math.max(0, this.score);
        this.analysis.summary = this.generateSummary();

        return this.analysis;
    }

    // High-value indicators
    checkArticleTag() {
        const articleTags = document.querySelectorAll('article');
        if (articleTags.length > 0) {
            // Check if article has significant content
            let totalText = '';
            articleTags.forEach(article => {
                totalText += article.textContent || '';
            });
            
            if (totalText.trim().length > 500) {
                this.score += 3;
                this.analysis.indicators.push('article_tag_with_content');
            }
        }
    }

    checkHeadlineStructure() {
        const h1Tags = document.querySelectorAll('h1');
        if (h1Tags.length === 1) {
            const h1Text = h1Tags[0].textContent.trim();
            if (h1Text.length > 10 && h1Text.length < 200) {
                this.score += 2;
                this.analysis.indicators.push('single_prominent_h1');
            }
        }
    }

    checkContentLength() {
        const paragraphs = document.querySelectorAll('p');
        let totalWords = 0;
        
        paragraphs.forEach(p => {
            const text = p.textContent.trim();
            const words = text.split(/\s+/).filter(word => word.length > 0);
            totalWords += words.length;
        });

        if (totalWords > 250) {
            this.score += 2;
            this.analysis.indicators.push('significant_word_count');
        }

        this.analysis.wordCount = totalWords;
    }

    checkParagraphCount() {
        const paragraphs = document.querySelectorAll('p');
        if (paragraphs.length > 15) {
            this.score += 2;
            this.analysis.indicators.push('multiple_paragraphs');
        }
        this.analysis.paragraphCount = paragraphs.length;
    }

    // Negative indicators
    checkLoginForms() {
        const loginForms = document.querySelectorAll('form');
        let loginIndicators = 0;

        loginForms.forEach(form => {
            const inputs = form.querySelectorAll('input');
            inputs.forEach(input => {
                const type = input.type.toLowerCase();
                const name = input.name.toLowerCase();
                const placeholder = input.placeholder.toLowerCase();
                
                if (type === 'password' || 
                    name.includes('password') || 
                    name.includes('login') ||
                    name.includes('email') ||
                    placeholder.includes('password') ||
                    placeholder.includes('email')) {
                    loginIndicators++;
                }
            });
        });

        if (loginIndicators > 2) {
            this.score -= 4;
            this.analysis.penalties.push('login_forms_detected');
        }
    }

    checkSearchPages() {
        const url = window.location.href.toLowerCase();
        const searchTerms = ['search', 'login', 'category', 'tag', 'archive', 'author'];
        
        for (const term of searchTerms) {
            if (url.includes(term)) {
                this.score -= 4;
                this.analysis.penalties.push(`url_contains_${term}`);
                break;
            }
        }
    }

    checkSocialMedia() {
        const socialSelectors = [
            '.social-share',
            '.social-media',
            '.share-buttons',
            '[class*="social"]',
            '[id*="social"]'
        ];

        let socialElements = 0;
        socialSelectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            socialElements += elements.length;
        });

        if (socialElements > 5) {
            this.score -= 2;
            this.analysis.penalties.push('excessive_social_elements');
        }
    }

    generateSummary() {
        const indicators = this.analysis.indicators.length;
        const penalties = this.analysis.penalties.length;
        
        if (this.score >= 5) {
            return `Strong article indicators (${indicators} positive, ${penalties} negative)`;
        } else if (this.score >= 3) {
            return `Moderate article indicators (${indicators} positive, ${penalties} negative)`;
        } else if (this.score >= 1) {
            return `Weak article indicators (${indicators} positive, ${penalties} negative)`;
        } else {
            return `Not an article (${indicators} positive, ${penalties} negative)`;
        }
    }
}

// Initialize page analyzer when content script loads
new PageAnalyzer();

// Additional utility functions for the extension
class ContentScriptUtils {
    static getPageMetadata() {
        return {
            title: document.title,
            url: window.location.href,
            domain: window.location.hostname,
            description: this.getMetaDescription(),
            language: this.getPageLanguage(),
            wordCount: this.getWordCount(),
            paragraphCount: this.getParagraphCount()
        };
    }

    static getMetaDescription() {
        const metaDesc = document.querySelector('meta[name="description"]');
        return metaDesc ? metaDesc.getAttribute('content') : '';
    }

    static getPageLanguage() {
        const htmlLang = document.documentElement.lang;
        if (htmlLang) return htmlLang;

        const metaLang = document.querySelector('meta[http-equiv="content-language"]');
        return metaLang ? metaLang.getAttribute('content') : 'en';
    }

    static getWordCount() {
        const text = document.body.textContent || '';
        const words = text.trim().split(/\s+/).filter(word => word.length > 0);
        return words.length;
    }

    static getParagraphCount() {
        return document.querySelectorAll('p').length;
    }

    static isArticlePage() {
        // Quick check for common article indicators
        const hasArticleTag = document.querySelector('article') !== null;
        const hasSingleH1 = document.querySelectorAll('h1').length === 1;
        const hasMultipleParagraphs = document.querySelectorAll('p').length > 10;
        const hasSignificantContent = this.getWordCount() > 200;

        return hasArticleTag || (hasSingleH1 && hasMultipleParagraphs && hasSignificantContent);
    }

    static getArticleContent() {
        // Try to extract main content
        const selectors = [
            'article',
            '[role="main"]',
            '.post-content',
            '.article-content',
            '.entry-content',
            '.story-body',
            '.article-body'
        ];

        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element && element.textContent.trim().length > 500) {
                return {
                    element: selector,
                    text: element.textContent.trim(),
                    html: element.innerHTML
                };
            }
        }

        // Fallback to body content
        return {
            element: 'body',
            text: document.body.textContent.trim(),
            html: document.body.innerHTML
        };
    }
}

// Expose utility functions to popup
window.contentScriptUtils = ContentScriptUtils; 