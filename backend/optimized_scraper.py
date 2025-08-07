
import json
import asyncio
import logging
import random
from typing import Dict, Optional, AsyncGenerator, Any, List, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from urllib.parse import urlparse
from enum import Enum
import time

import requests
from bs4 import BeautifulSoup
from readability import Document
from markdownify import markdownify as md
from dateutil.parser import parse as parse_date
from playwright.async_api import async_playwright, Page, Browser, Playwright, Error as PlaywrightError, Route
from playwright_stealth import stealth
from helper_proxy_manager import get_helper_proxy_manager

# --- Constants and Data Models ---
UNKNOWN_AUTHOR = "Unknown"
DATE_NOT_APPLICABLE = "N/A"
MINIMUM_CONTENT_LENGTH = 250  # Characters
DECOY_PAGE_KEYWORDS = ["page not found", "page non trouvée", "enable javascript", "checking your browser"]

class ScrapingMethod(Enum):
    REQUESTS = "requests"
    PLAYWRIGHT = "playwright"

class WorkflowStage(Enum):
    INITIALIZATION = "initialization"
    FAST_PATH = "fast_path"
    ROBUST_PATH = "robust_path"
    NAVIGATION = "navigation"
    CONTENT_EXTRACTION = "content_extraction"
    METADATA_EXTRACTION = "metadata_extraction"
    VALIDATION = "validation"
    COMPLETION = "completion"

class ScraperError(Exception): pass
class NavigationError(ScraperError): pass
class ContentExtractionError(ScraperError): pass
class DecoyPageError(ContentExtractionError): pass
class ValidationError(ScraperError): pass

@dataclass
class Metadata:
    author: str = UNKNOWN_AUTHOR
    publication_date_utc: str = DATE_NOT_APPLICABLE
    author_found_by: Optional[str] = None
    date_found_by: Optional[str] = None
    word_count: int = 0
    reading_time_minutes: float = 0.0

@dataclass
class Article:
    url: str
    domain: str
    retrieval_date_utc: str
    title: str
    metadata: Metadata
    content: Dict[str, str] = field(default_factory=dict)
    scraped_with: str = "N/A"
    workflow_stages: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)

@dataclass
class WorkflowOutput:
    status: str
    stage: str
    total_stages: int
    current_stage: int
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)

# --- Main Scraper Class ---
class OptimizedUniversalScraper:
    """
    Optimized high-performance scraper with adaptive `requests` -> `playwright` strategy
    and consistent output structure.
    """
    
    def __init__(self, config: Optional[Dict] = None, logger: Optional[logging.Logger] = None):
        self.config = {
            "goto_timeout": 45000,
            "requests_timeout": 15,
            "user_agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            "cookie_consent_selectors": [
                'button#didomi-notice-agree-button', 
                'button[data-testid="uc-accept-all-button"]', 
                'button:has-text("Accept all")',
                '.accept-cookies',
                '#accept-cookies'
            ],
            "cookie_consent_timeout": 3000,
            "article_container_selectors": [
                "article", '[role="article"]', '.post-content', '.article-body', 
                '.story-body', '.article-content', '.t-content__body', 
                '.standard-article-body', '.entry-content', '.post-body'
            ],
            "junk_selectors": [
                '.related-links', '.ad-container', '.social-share', '.author-bio', 
                'figure.author', '.vjs-playlist', '.comments', '.sidebar',
                '.advertisement', '.ads', '.sponsored'
            ],
            "subtitle_selectors": [
                'p.intro', 'h2.article__summary', 'p.standfirst-lead', 
                '.c-article-header__standfirst', '.article-header__deck', 
                'p.e_d_9i', '.subtitle', '.deck'
            ],
            "blocked_resource_types": ["image", "stylesheet", "font", "media"],
            "blocked_domains": [
                "googletagmanager.com", "google-analytics.com", 
                "adservice.google.com", "chartbeat.com", "facebook.com",
                "twitter.com", "linkedin.com"
            ],
            "retry_attempts": 2,
            "retry_delay": 1.0,
            # Helper proxy configuration
            "helper_proxy_enabled": False,
            "helper_proxy_settings": {
                "server": None,  # e.g., "http://proxy.example.com:8080"
                "username": None,
                "password": None
            },
            "helper_proxy_rotation": {
                "enabled": False,
                "proxy_list": [],  # List of proxy dictionaries
                "current_index": 0
            }
        }
        if config:
            self.config.update(config)
        self.logger = logger or logging.getLogger(__name__)
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._start_time: float = 0.0

    async def __aenter__(self) -> "OptimizedUniversalScraper":
        self._start_time = time.time()
        self.logger.info("Initializing Playwright...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',  # Required for Docker/CI environments
                '--disable-dev-shm-usage',  # Prevents memory issues in containers
                '--disable-blink-features=AutomationControlled',  # Bypasses bot detection
                '--disable-extensions',  # Reduces memory usage and potential conflicts
                '--disable-images',  # Improves performance for text extraction
                '--no-first-run',  # Skips first-run setup dialogs
                '--disable-default-apps'  # Prevents default app installation
            ]
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self.logger.info("Scraper resources released.")

    async def scrape_single_url(self, url: str) -> Dict[str, Any]:
        """
        Convenience method for scraping a single URL with simplified output.
        Returns the final article data or raises an exception on error.
        """
        async for update in self.run(url):
            if update.status == 'complete':
                return update.data
            elif update.status == 'error':
                raise ScraperError(f"Scraping failed: {update.error}")
        
        raise ScraperError("Unexpected end of workflow")

    def _get_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics."""
        elapsed_time = time.time() - self._start_time
        return {
            "total_elapsed_time_seconds": elapsed_time,
            "timestamp": self._start_time
        }

    def _get_helper_proxy_settings(self) -> Optional[Dict[str, str]]:
        """Get current helper proxy settings for browser context."""
        if not self.config.get("helper_proxy_enabled", False):
            return None
        
        # Check if rotation is enabled (either boolean or dict with enabled=True)
        rotation_config = self.config.get("helper_proxy_rotation", False)
        if rotation_config:
            if isinstance(rotation_config, bool):
                # Use HelperProxyManager
                return self._get_helper_proxy()
            elif isinstance(rotation_config, dict) and rotation_config.get("enabled"):
                # Use custom proxy list
                proxy_list = rotation_config.get("proxy_list", [])
                if proxy_list:
                    current_index = rotation_config.get("current_index", 0)
                    proxy = proxy_list[current_index % len(proxy_list)]
                    # Rotate to next proxy
                    rotation_config["current_index"] = (current_index + 1) % len(proxy_list)
                    return proxy
        
        # Use single proxy settings
        proxy_settings = self.config.get("helper_proxy_settings", {})
        if proxy_settings.get("server"):
            return {
                "server": proxy_settings["server"],
                "username": proxy_settings.get("username"),
                "password": proxy_settings.get("password")
            }
        
        return None

    def enable_helper_proxy(self, server: str, username: Optional[str] = None, password: Optional[str] = None):
        """Enable single helper proxy configuration."""
        self.config["helper_proxy_enabled"] = True
        self.config["helper_proxy_settings"] = {
            "server": server,
            "username": username,
            "password": password
        }
        self.logger.info(f"Helper proxy enabled: {server}")

    def enable_helper_proxy_rotation(self, proxy_list: Optional[List[Dict[str, str]]] = None):
        """Enable helper proxy rotation. If proxy_list provided, uses custom list; otherwise uses HelperProxyManager."""
        self.config["helper_proxy_enabled"] = True
        
        if proxy_list:
            self.config["helper_proxy_rotation"] = {
                "enabled": True,
                "proxy_list": proxy_list,
                "current_index": 0
            }
            self.logger.info(f"Helper proxy rotation enabled with {len(proxy_list)} custom proxies")
        else:
            self.config["helper_proxy_rotation"] = True
            self.logger.info("Helper proxy rotation enabled using HelperProxyManager")

    def disable_helper_proxy(self):
        """Disable helper proxy usage."""
        self.config["helper_proxy_enabled"] = False
        self.logger.info("Helper proxy disabled")

    def _get_helper_proxy(self) -> Optional[Dict[str, str]]:
        """Get a helper proxy from the proxy manager."""
        if not self.config.get("helper_proxy_rotation", False):
            return None
        
        try:
            proxy_manager = get_helper_proxy_manager()
            proxy = proxy_manager.get_random_proxy()
            if proxy:
                return proxy_manager.get_proxy_dict(proxy)
        except Exception as e:
            self.logger.warning(f"Error getting helper proxy: {e}")
        
        return None

    def _create_workflow_output(
        self, 
        status: str, 
        stage: WorkflowStage, 
        current_stage: int, 
        total_stages: int,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> WorkflowOutput:
        """Create consistent workflow output structure."""
        return WorkflowOutput(
            status=status,
            stage=stage.value,
            total_stages=total_stages,
            current_stage=current_stage,
            message=message,
            data=data,
            error=error,
            performance_metrics=self._get_performance_metrics()
        )

    # --- The Main Orchestrator Method ---
    async def run(self, url: str) -> AsyncGenerator[WorkflowOutput, None]:
        """
        Executes the optimized adaptive scraping workflow with consistent output structure.
        """
        total_stages = 6
        current_stage = 0
        
        # Stage 0: Initialization
        current_stage += 1
        yield self._create_workflow_output(
            "progress", WorkflowStage.INITIALIZATION, current_stage, total_stages,
            "Initializing scraper and validating URL..."
        )
        
        # Validate URL
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValidationError("Invalid URL format")
        except Exception as e:
            yield self._create_workflow_output(
                "error", WorkflowStage.INITIALIZATION, current_stage, total_stages,
                "URL validation failed", error=str(e)
            )
            return

        # Stage 1: Fast Path Attempt
        current_stage += 1
        yield self._create_workflow_output(
            "progress", WorkflowStage.FAST_PATH, current_stage, total_stages,
            "Attempting fast scrape with requests..."
        )
        
        try:
            article_data = await self._run_fast_path(url)
            article_data.workflow_stages.append(WorkflowStage.FAST_PATH.value)
            article_data.performance_metrics = self._get_performance_metrics()
            
            yield self._create_workflow_output(
                "complete", WorkflowStage.COMPLETION, total_stages, total_stages,
                "Fast path successful", data=asdict(article_data)
            )
            self.logger.info(f"Success on Fast Path for {url}")
            return
            
        except Exception as e:
            self.logger.warning(f"Fast Path failed for {url}: {e}. Escalating to full browser...")
            yield self._create_workflow_output(
                "progress", WorkflowStage.FAST_PATH, current_stage, total_stages,
                f"Fast scrape failed, escalating to robust path...", error=str(e)
            )

        # Stage 2-5: Robust Path with Playwright
        async for update in self._run_robust_path(url, current_stage, total_stages):
            yield update

    async def _run_fast_path(self, url: str) -> Article:
        """Optimized fast path using requests with retry logic."""
        headers = {
            'User-Agent': self.config['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        for attempt in range(self.config['retry_attempts']):
            try:
                response = await asyncio.to_thread(
                    requests.get, url, headers=headers, timeout=self.config['requests_timeout']
                )
                response.raise_for_status()
                
                article = self._parse_html_content(url, response.text)
                article.scraped_with = ScrapingMethod.REQUESTS.value
                
                # Enhanced validation
                await self._validate_article(article)
                
                return article
                
            except requests.RequestException as e:
                if attempt == self.config['retry_attempts'] - 1:
                    raise NavigationError(f"Requests failed to fetch URL after {self.config['retry_attempts']} attempts: {e}") from e
                await asyncio.sleep(self.config['retry_delay'])

    async def _run_robust_path(self, url: str, start_stage: int, total_stages: int) -> AsyncGenerator[WorkflowOutput, None]:
        """Optimized robust path using Playwright with enhanced error handling."""
        if not self._browser:
            yield self._create_workflow_output(
                "error", WorkflowStage.ROBUST_PATH, start_stage, total_stages,
                "Browser not initialized", error="Browser initialization failed"
            )
            return
            
        context = None
        current_stage = start_stage
        
        try:
            # Stage 2: Browser Context Setup
            current_stage += 1
            yield self._create_workflow_output(
                "progress", WorkflowStage.ROBUST_PATH, current_stage, total_stages,
                "Creating optimized browser context..."
            )
            
            async def block_requests(route: Route):
                if (route.request.resource_type in self.config["blocked_resource_types"] or
                    any(domain in route.request.url for domain in self.config["blocked_domains"])):
                    await route.abort()
                else:
                    await route.continue_()
            
            # Get helper proxy settings if enabled
            proxy_settings = self._get_helper_proxy_settings()
            context_kwargs = {
                'user_agent': self.config['user_agent'],
                'viewport': {'width': 1920, 'height': 1080},
                # Add more realistic headers
                'extra_http_headers': {
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0'
                }
            }
            
            # Add helper proxy if configured
            if proxy_settings:
                context_kwargs['proxy'] = proxy_settings
                self.logger.info(f"Using helper proxy: {proxy_settings.get('server', 'Unknown')}")
            
            context = await self._browser.new_context(**context_kwargs)
            
            # Apply stealth settings to the entire browser context
            stealth_instance = stealth.Stealth()
            await stealth_instance.apply_stealth_async(context)
            
            await context.route("**/*", block_requests)
            page = await context.new_page()
            
            # Enhanced anti-detection
            await page.add_init_script("""
                // Hide webdriver property
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                
                // Mock permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Mock chrome runtime
                if (!window.chrome) {
                    window.chrome = {
                        runtime: {},
                        loadTimes: function() {},
                        csi: function() {},
                        app: {}
                    };
                }
                
                // Mock webkit
                if (!window.webkit) {
                    window.webkit = {
                        messageHandlers: {}
                    };
                }
                
                // Override toString to hide automation
                const originalFunction = Function.prototype.toString;
                Function.prototype.toString = function() {
                    if (this === Function.prototype.toString) return originalFunction.call(this);
                    if (this === window.navigator.permissions.query) return 'function query() { [native code] }';
                    return originalFunction.call(this);
                };
            """)
            
            # Stage 3: Navigation
            current_stage += 1
            yield self._create_workflow_output(
                "progress", WorkflowStage.NAVIGATION, current_stage, total_stages,
                "Navigating with full browser capabilities..."
            )
            
            await self._navigate_and_consent(page, url)
            
            # Stage 4: Content Extraction
            current_stage += 1
            yield self._create_workflow_output(
                "progress", WorkflowStage.CONTENT_EXTRACTION, current_stage, total_stages,
                "Extracting page content..."
            )
            
            raw_html = await page.content()
            
            # Stage 5: Content Processing
            current_stage += 1
            yield self._create_workflow_output(
                "progress", WorkflowStage.METADATA_EXTRACTION, current_stage, total_stages,
                "Processing content and extracting metadata..."
            )
            
            article_data = self._parse_html_content(url, raw_html)
            article_data.scraped_with = ScrapingMethod.PLAYWRIGHT.value
            article_data.workflow_stages = [stage.value for stage in WorkflowStage]
            
            # Enhanced validation
            await self._validate_article(article_data)
            
            # Stage 6: Completion
            yield self._create_workflow_output(
                "complete", WorkflowStage.COMPLETION, total_stages, total_stages,
                "Robust path completed successfully", data=asdict(article_data)
            )
            
        except ScraperError as e:
            self.logger.error(f"A scraper error occurred for {url}: {e}")
            yield self._create_workflow_output(
                "error", WorkflowStage.ROBUST_PATH, current_stage, total_stages,
                f"Scraper error: {type(e).__name__}", error=str(e)
            )
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred for {url}: {e}")
            yield self._create_workflow_output(
                "error", WorkflowStage.ROBUST_PATH, current_stage, total_stages,
                "Unexpected error occurred", error=str(e)
            )
        finally:
            if context:
                await context.close()

    async def _navigate_and_consent(self, page: Page, url: str):
        """Enhanced navigation with human-like behavior and better cookie consent handling."""
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=self.config['goto_timeout'])

            # Wait a random amount of time to mimic human behavior
            await page.wait_for_timeout(random.randint(1500, 3000))

            # Move the mouse to a random position to simulate user presence
            await page.mouse.move(random.randint(0, 100), random.randint(0, 100))

            # Give the page a moment to run initial scripts (e.g., for cookie banners)
            await page.wait_for_timeout(2000)

            # Handle cookie consent with multiple strategies
            consent_given = False
            for selector in self.config['cookie_consent_selectors']:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=1000):
                        # Add human-like delay before clicking
                        await page.wait_for_timeout(random.randint(500, 1500))
                        await element.click(timeout=self.config['cookie_consent_timeout'])
                        self.logger.info(f"Clicked cookie consent button with selector: {selector}")
                        consent_given = True
                        break # Exit loop once consent is given
                except PlaywrightError:
                    # Element not found or not visible, try next selector
                    continue

            # If we clicked a consent button, wait for the page to reload/settle
            if consent_given:
                self.logger.info("Waiting for page to settle after giving consent...")
                await page.wait_for_timeout(3000)

            # Simulate human scrolling behavior
            await page.mouse.wheel(0, random.randint(100, 300))
            await page.wait_for_timeout(random.randint(1000, 2000))

            # Final wait for the main content to be surely loaded
            await page.wait_for_load_state('networkidle', timeout=10000)

        except PlaywrightError as e:
            raise NavigationError(f"Playwright navigation failed for {url}: {e}") from e

    async def _validate_article(self, article: Article):
        """Enhanced article validation."""
        content_lower = article.content.get('markdown', '').lower()
        
        if len(content_lower) < MINIMUM_CONTENT_LENGTH:
            raise DecoyPageError(f"Content too short ({len(content_lower)} chars). Likely a block page.")
        
        if any(keyword in content_lower for keyword in DECOY_PAGE_KEYWORDS):
            raise DecoyPageError(f"Decoy page keyword found. Content likely blocked.")
        
        # Calculate word count and reading time
        words = content_lower.split()
        article.metadata.word_count = len(words)
        article.metadata.reading_time_minutes = max(1.0, len(words) / 200)  # Average reading speed

    def _parse_html_content(self, url: str, raw_html: str) -> Article:
        """Optimized HTML parsing with enhanced content extraction."""
        soup = BeautifulSoup(raw_html, 'html.parser')
        
        # Find article container with enhanced selectors
        article_container = None
        for selector in self.config['article_container_selectors']:
            if article_container := soup.select_one(selector):
                break
        
        if not article_container:
            # Fallback to readability
            doc = Document(raw_html)
            article_container = BeautifulSoup(doc.summary(), 'html.parser')
            if not article_container.find():
                raise ContentExtractionError("Could not extract content.")
        
        # Extract title with fallback strategy
        title_tag = article_container.find('h1')
        if not title_tag:
            title_tag = soup.find('h1')
        if not title_tag:
            title_tag = soup.title
        
        title = title_tag.get_text(strip=True) if title_tag else "Untitled"
        
        # Remove junk content
        for junk_selector in self.config['junk_selectors']:
            for element in article_container.select(junk_selector):
                element.decompose()
        
        # Extract subtitle
        subtitle_html = ""
        for selector in self.config['subtitle_selectors']:
            if subtitle_tag := soup.select_one(selector):
                subtitle_tag.wrap(soup.new_tag("div"))
                subtitle_html = str(subtitle_tag.parent)
                if container_subtitle := article_container.select_one(selector):
                    container_subtitle.decompose()
                break
        
        # Combine content
        cleaned_container_html = subtitle_html + str(article_container)
        markdown_content = md(cleaned_container_html, heading_style="ATX").strip()
        
        # Extract metadata
        metadata = self._extract_universal_metadata(soup)
        
        return Article(
            url=url,
            domain=urlparse(url).netloc,
            retrieval_date_utc=datetime.now(timezone.utc).isoformat(),
            title=title,
            metadata=metadata,
            content={'markdown': markdown_content, 'clean_html': cleaned_container_html}
        )

    def _extract_universal_metadata(self, soup: BeautifulSoup) -> Metadata:
        """Enhanced metadata extraction with multiple strategies."""
        metadata = Metadata()
        
        # Strategy 1: JSON-LD
        self._strategy_extract_from_json_ld(soup, metadata)
        
        # Strategy 2: Meta tags (if JSON-LD didn't find everything)
        if metadata.author == UNKNOWN_AUTHOR or metadata.publication_date_utc == DATE_NOT_APPLICABLE:
            self._strategy_extract_from_tags(soup, metadata)
        
        # Strategy 3: HTML attributes (fallback)
        if metadata.publication_date_utc == DATE_NOT_APPLICABLE:
            self._strategy_extract_from_attributes(soup, metadata)
        
        return metadata

    def _strategy_extract_from_json_ld(self, soup: BeautifulSoup, metadata: Metadata):
        """Extract metadata from JSON-LD structured data."""
        for tag in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(tag.string)
                if isinstance(data, list):
                    data = data[0]
                if '@graph' in data and isinstance(data['@graph'], list) and data['@graph']:
                    data = data['@graph'][0]
                
                # Extract author
                if metadata.author == UNKNOWN_AUTHOR and (author_data := data.get('author')):
                    name = self._extract_author_name(author_data)
                    if name:
                        metadata.author, metadata.author_found_by = name, 'json-ld'
                
                # Extract publication date
                if metadata.publication_date_utc == DATE_NOT_APPLICABLE and (pub_date := data.get('datePublished')):
                    metadata.publication_date_utc, metadata.date_found_by = parse_date(pub_date).isoformat(), 'json-ld'
                    
            except Exception:
                continue

    def _extract_author_name(self, author_data: Union[dict, list, str]) -> Optional[str]:
        """Extract author name from various data structures."""
        if isinstance(author_data, dict):
            return author_data.get('name')
        elif isinstance(author_data, list) and author_data:
            first = author_data[0]
            if isinstance(first, dict):
                return first.get('name')
            else:
                return str(first)
        elif isinstance(author_data, str):
            return author_data
        return None

    def _strategy_extract_from_tags(self, soup: BeautifulSoup, metadata: Metadata):
        """Extract metadata from HTML meta tags."""
        if metadata.author == UNKNOWN_AUTHOR:
            selectors = [
                "meta[name='author']", "meta[name='dc.creator']", 
                "meta[property='article:author']", "meta[property='og:author']"
            ]
            for selector in selectors:
                if (tag := soup.select_one(selector)) and (content := tag.get('content', '').strip()):
                    metadata.author, metadata.author_found_by = content, 'meta-tag'
                    break
        
        if metadata.publication_date_utc == DATE_NOT_APPLICABLE:
            selectors = [
                "meta[name='date']", "meta[name='dc.date']", 
                "meta[property='article:published_time']", "meta[property='og:published_time']",
                "meta[name='publish_date']", "meta[name='pubdate']"
            ]
            for selector in selectors:
                if (tag := soup.select_one(selector)) and (content := tag.get('content', '').strip()):
                    try:
                        metadata.publication_date_utc, metadata.date_found_by = parse_date(content).isoformat(), 'meta-tag'
                        break
                    except Exception:
                        continue

    def _strategy_extract_from_attributes(self, soup: BeautifulSoup, metadata: Metadata):
        """Extract metadata from HTML attributes."""
        if metadata.publication_date_utc == DATE_NOT_APPLICABLE:
            # Try time tags
            for tag in soup.find_all('time', datetime=True):
                try:
                    content = tag.get('datetime', '').strip()
                    if content:
                        metadata.publication_date_utc, metadata.date_found_by = parse_date(content).isoformat(), 'time-tag'
                        break
                except Exception:
                    continue

async def main():
    """Main function demonstrating the optimized scraper for single URL processing."""
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Single test URL
    target_url = "https://www.theguardian.com/world/2024/may/10/israel-rejects-un-vote-to-grant-palestine-new-rights-and-revive-statehood-bid"
    
    print("🚀 Optimized Universal Scraper - Single URL Mode")
    print(f"{'='*80}")
    
    # Method 1: Full workflow with progress tracking
    print(f"\n📋 Method 1: Full workflow tracking for: {target_url}")
    print("-" * 60)
    
    final_result = None
    try:
        async with OptimizedUniversalScraper() as scraper:
            async for update in scraper.run(target_url):
                if update.status == 'progress':
                    print(f"  [PROGRESS] Stage {update.current_stage}/{update.total_stages} - {update.stage}: {update.message}")
                elif update.status == 'complete':
                    print(f"\n✅ Workflow completed successfully!")
                    print(f"   Performance: {update.performance_metrics['total_elapsed_time_seconds']:.2f}s")
                    final_result = update.data
                elif update.status == 'error':
                    print(f"\n❌ Workflow failed: {update.error}")
                    break
    except Exception as e:
        print(f"\n❌ A critical error occurred during scraper setup: {e}")
    
    if final_result:
        print(f"\n📊 Final Results (Scraped using: {final_result.get('scraped_with')}):")
        print(f"   Title: {final_result.get('title', 'N/A')}")
        print(f"   Author: {final_result.get('metadata', {}).get('author', 'N/A')}")
        print(f"   Word Count: {final_result.get('metadata', {}).get('word_count', 0)}")
        print(f"   Reading Time: {final_result.get('metadata', {}).get('reading_time_minutes', 0):.1f} minutes")
        print(f"   Workflow Stages: {', '.join(final_result.get('workflow_stages', []))}")
    
    # Method 2: Simple single URL scraping
    print(f"\n\n📋 Method 2: Simple single URL scraping")
    print("-" * 60)
    
    try:
        async with OptimizedUniversalScraper() as scraper:
            result = await scraper.scrape_single_url(target_url)
            print(f"✅ Simple scraping completed!")
            print(f"   Title: {result.get('title', 'N/A')}")
            print(f"   Author: {result.get('metadata', {}).get('author', 'N/A')}")
            print(f"   Word Count: {result.get('metadata', {}).get('word_count', 0)}")
    except Exception as e:
        print(f"❌ Simple scraping failed: {e}")
    
    print(f"\n{'='*80}")
    return final_result

if __name__ == "__main__":
    asyncio.run(main()) 