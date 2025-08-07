#!/usr/bin/env python3
"""
Example script demonstrating how to use proxy functionality with the OptimizedUniversalScraper.

This script shows different ways to configure proxies to bypass IP-based blocking.
"""

import asyncio
import logging
from optimized_scraper import OptimizedUniversalScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def example_single_proxy():
    """Example: Using a single proxy server."""
    print("=== Single Proxy Example ===")
    
    async with OptimizedUniversalScraper() as scraper:
        # Enable single proxy
        scraper.enable_proxy(
            server="http://proxy.example.com:8080",
            username="your-username",
            password="your-password"
        )
        
        # Test URL
        url = "https://example.com/article"
        
        try:
            async for update in scraper.run(url):
                print(f"Status: {update.status}, Stage: {update.stage}, Message: {update.message}")
                if update.status == 'complete':
                    print(f"Success! Article title: {update.data.get('title', 'No title')}")
                    break
                elif update.status == 'error':
                    print(f"Error: {update.error}")
                    break
        except Exception as e:
            print(f"Exception: {e}")

async def example_proxy_rotation():
    """Example: Using proxy rotation with multiple proxies."""
    print("\n=== Proxy Rotation Example ===")
    
    # List of proxies to rotate through
    proxy_list = [
        {
            "server": "http://proxy1.example.com:8080",
            "username": "user1",
            "password": "pass1"
        },
        {
            "server": "http://proxy2.example.com:8080", 
            "username": "user2",
            "password": "pass2"
        },
        {
            "server": "http://proxy3.example.com:8080",
            "username": "user3", 
            "password": "pass3"
        }
    ]
    
    async with OptimizedUniversalScraper() as scraper:
        # Enable proxy rotation
        scraper.enable_proxy_rotation(proxy_list)
        
        # Test multiple URLs (each will use a different proxy)
        urls = [
            "https://example.com/article1",
            "https://example.com/article2", 
            "https://example.com/article3"
        ]
        
        for i, url in enumerate(urls):
            print(f"\nScraping URL {i+1}: {url}")
            try:
                async for update in scraper.run(url):
                    print(f"  Status: {update.status}, Stage: {update.stage}")
                    if update.status == 'complete':
                        print(f"  Success! Article title: {update.data.get('title', 'No title')}")
                        break
                    elif update.status == 'error':
                        print(f"  Error: {update.error}")
                        break
            except Exception as e:
                print(f"  Exception: {e}")

async def example_no_proxy():
    """Example: Running without proxy (for comparison)."""
    print("\n=== No Proxy Example ===")
    
    async with OptimizedUniversalScraper() as scraper:
        # Ensure proxy is disabled
        scraper.disable_proxy()
        
        url = "https://example.com/article"
        
        try:
            async for update in scraper.run(url):
                print(f"Status: {update.status}, Stage: {update.stage}, Message: {update.message}")
                if update.status == 'complete':
                    print(f"Success! Article title: {update.data.get('title', 'No title')}")
                    break
                elif update.status == 'error':
                    print(f"Error: {update.error}")
                    break
        except Exception as e:
            print(f"Exception: {e}")

async def main():
    """Run all examples."""
    print("Proxy Usage Examples for OptimizedUniversalScraper")
    print("=" * 50)
    
    # Note: These examples use placeholder proxy credentials
    # Replace with actual proxy details for real usage
    
    # Example 1: Single proxy
    await example_single_proxy()
    
    # Example 2: Proxy rotation  
    await example_proxy_rotation()
    
    # Example 3: No proxy
    await example_no_proxy()
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nTo use with real proxies:")
    print("1. Replace proxy.example.com with your actual proxy server")
    print("2. Replace username/password with your actual credentials")
    print("3. For proxy rotation, add multiple proxy configurations")
    print("4. Test with a small number of requests first")

if __name__ == "__main__":
    asyncio.run(main())
