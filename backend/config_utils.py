#!/usr/bin/env python3
"""
Shared Configuration Utilities

Centralizes common configuration logic and reduces duplication across the application.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class ScraperConfig:
    """Centralized scraper configuration with sensible defaults."""
    
    # Core settings
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Performance settings
    headless: bool = True
    disable_images: bool = True
    disable_javascript: bool = False
    
    # Helper proxy settings
    helper_proxy_enabled: bool = False
    helper_proxy_rotation: bool = False
    
    # Browser arguments (minimal set)
    browser_args: list = field(default_factory=lambda: [
        '--no-sandbox',  # Required for Docker/CI environments
        '--disable-dev-shm-usage',  # Prevents memory issues in containers
        '--disable-blink-features=AutomationControlled',  # Bypasses bot detection
        '--disable-extensions',  # Reduces memory usage
        '--disable-images',  # Improves performance for text extraction
        '--no-first-run',  # Skips first-run setup dialogs
        '--disable-default-apps'  # Prevents default app installation
    ])
    
    # HTTP headers for realistic requests
    http_headers: Dict[str, str] = field(default_factory=lambda: {
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    })

def get_default_config() -> Dict[str, Any]:
    """Get default configuration dictionary."""
    config = ScraperConfig()
    return {
        "user_agent": config.user_agent,
        "timeout_seconds": config.timeout_seconds,
        "max_retries": config.max_retries,
        "retry_delay": config.retry_delay,
        "headless": config.headless,
        "disable_images": config.disable_images,
        "disable_javascript": config.disable_javascript,
        "helper_proxy_enabled": config.helper_proxy_enabled,
        "helper_proxy_rotation": config.helper_proxy_rotation,
        "browser_args": config.browser_args,
        "http_headers": config.http_headers
    }

def merge_configs(base_config: Dict[str, Any], override_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Merge configurations with sensible defaults."""
    if override_config is None:
        return base_config
    
    merged = base_config.copy()
    for key, value in override_config.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    
    return merged

def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration values."""
    required_fields = ["user_agent", "timeout_seconds", "max_retries"]
    
    for field in required_fields:
        if field not in config:
            return False
    
    if config["timeout_seconds"] <= 0:
        return False
    
    if config["max_retries"] < 0:
        return False
    
    return True
