#!/usr/bin/env python3
"""
Helper Proxy Example for OptimizedUniversalScraper

This script demonstrates how to use the helper proxy rotation feature
as an optional enhancement to improve success rates on some protected sites.
"""

import asyncio
import logging
from optimized_scraper import OptimizedUniversalScraper
from helper_proxy_manager import initialize_helper_proxy_manager, get_helper_proxy_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def example_helper_proxy_rotation():
    """Example: Using helper proxy rotation."""
    print("=== Helper Proxy Rotation Example ===")
    
    # Initialize the proxy manager first
    print("Initializing helper proxy manager...")
    proxy_manager = await initialize_helper_proxy_manager()
    
    # Get proxy statistics
    stats = proxy_manager.get_stats()
    print(f"Proxy Stats: {stats}")
    
    async with OptimizedUniversalScraper() as scraper:
        # Enable helper proxy rotation
        scraper.enable_helper_proxy_rotation()
        
        # Test URLs (these are the ones that were failing due to IP blocking)
        test_urls = [
            "https://www.dw.com/en/top-stories/s-9097",
            "https://www.dw.com/en/business/s-1431",
            "https://www.dw.com/en/culture/s-1441"
        ]
        
        for i, url in enumerate(test_urls, 1):
            print(f"\n--- Testing URL {i}: {url} ---")
            
            try:
                async for update in scraper.run(url):
                    print(f"  Status: {update.status}, Stage: {update.stage}, Message: {update.message}")
                    
                    if update.status == 'complete':
                        print(f"  ✅ SUCCESS! Article title: {update.data.get('title', 'No title')}")
                        print(f"  Word count: {update.data.get('metadata', {}).get('word_count', 'Unknown')}")
                        break
                    elif update.status == 'error':
                        print(f"  ❌ ERROR: {update.error}")
                        break
                        
            except Exception as e:
                print(f"  ❌ EXCEPTION: {e}")
            
            # Small delay between requests
            await asyncio.sleep(2)
        
        # Show final proxy statistics
        final_stats = proxy_manager.get_stats()
        print(f"\n=== Final Proxy Statistics ===")
        print(f"Working proxies: {final_stats['total_working']}")
        print(f"Failed proxies: {final_stats['total_failed']}")
        print(f"Average speed: {final_stats['avg_speed']:.2f}s")
        print(f"Top countries: {final_stats['top_countries']}")

async def example_proxy_refresh():
    """Example: Manually refreshing the proxy list."""
    print("\n=== Helper Proxy Refresh Example ===")
    
    proxy_manager = get_helper_proxy_manager()
    
    print("Refreshing helper proxy list...")
    working_proxies = await proxy_manager.refresh_proxies(force=True)
    
    print(f"Found {len(working_proxies)} working proxies:")
    for i, proxy in enumerate(working_proxies[:5], 1):  # Show first 5
        print(f"  {i}. {proxy.ip}:{proxy.port} ({proxy.country}) - Speed: {proxy.speed:.2f}s")

async def example_proxy_validation():
    """Example: Testing proxy validation."""
    print("\n=== Helper Proxy Validation Example ===")
    
    proxy_manager = get_helper_proxy_manager()
    
    # Get a random proxy
    proxy = proxy_manager.get_random_proxy()
    if proxy:
        print(f"Testing proxy: {proxy.ip}:{proxy.port}")
        
        # Test the proxy
        is_working = await proxy_manager.validate_proxy(proxy)
        print(f"Proxy working: {is_working}")
        if is_working:
            print(f"Speed: {proxy.speed:.2f}s")
    else:
        print("No working proxies available")

async def main():
    """Run all helper proxy examples."""
    print("Helper Proxy Usage Examples for OptimizedUniversalScraper")
    print("=" * 60)
    print("This demonstrates how to use helper proxies as an optional enhancement!")
    print("=" * 60)
    
    try:
        # Example 1: Helper proxy rotation with scraping
        await example_helper_proxy_rotation()
        
        # Example 2: Manual proxy refresh
        await example_proxy_refresh()
        
        # Example 3: Proxy validation
        await example_proxy_validation()
        
    except Exception as e:
        print(f"Error in main: {e}")
        logger.exception("Main execution failed")
    
    print("\n" + "=" * 60)
    print("Helper proxy examples completed!")
    print("\nKey Benefits:")
    print("✅ Optional enhancement - not critical for core functionality")
    print("✅ Automatic rotation - each request uses different IP")
    print("✅ Self-healing - automatically removes failed proxies")
    print("✅ Multiple sources - fetches from 4+ reliable providers")
    print("✅ Performance optimized - validates and ranks proxies")
    print("✅ Production ready - handles failures gracefully")

if __name__ == "__main__":
    asyncio.run(main())
