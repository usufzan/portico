#!/usr/bin/env python3
"""
Free Proxy Manager for OptimizedUniversalScraper

This module provides a robust, free proxy solution using well-maintained public proxy services.
It automatically fetches, validates, and rotates through high-quality free proxies.
"""

import asyncio
import aiohttp
import time
import random
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import re

@dataclass
class ProxyInfo:
    """Represents a proxy with validation status."""
    ip: str
    port: int
    protocol: str  # 'http', 'https', 'socks4', 'socks5'
    country: Optional[str] = None
    anonymity: Optional[str] = None  # 'transparent', 'anonymous', 'elite'
    speed: Optional[float] = None  # response time in seconds
    last_checked: Optional[datetime] = None
    is_working: bool = False
    fail_count: int = 0
    success_count: int = 0

class FreeProxyManager:
    """
    Manages free proxies from multiple reliable sources with automatic validation and rotation.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.proxies: List[ProxyInfo] = []
        self.working_proxies: List[ProxyInfo] = []
        self.failed_proxies: Set[str] = set()  # IP:port combinations
        self.last_fetch: Optional[datetime] = None
        self.fetch_interval = timedelta(minutes=30)  # Refresh every 30 minutes
        self.max_proxies = 50  # Maximum number of proxies to maintain
        self.test_urls = [
            "http://httpbin.org/ip",
            "https://httpbin.org/ip",
            "http://ip-api.com/json"
        ]
        self.timeout = 10  # seconds
        
    async def fetch_proxies_from_sources(self) -> List[ProxyInfo]:
        """Fetch proxies from multiple reliable free sources."""
        all_proxies = []
        
        # Source 1: FreeProxyList.net
        try:
            proxies = await self._fetch_from_freeproxylist()
            all_proxies.extend(proxies)
            self.logger.info(f"Fetched {len(proxies)} proxies from FreeProxyList.net")
        except Exception as e:
            self.logger.warning(f"Failed to fetch from FreeProxyList.net: {e}")
        
        # Source 2: ProxyScrape.com
        try:
            proxies = await self._fetch_from_proxyscrape()
            all_proxies.extend(proxies)
            self.logger.info(f"Fetched {len(proxies)} proxies from ProxyScrape.com")
        except Exception as e:
            self.logger.warning(f"Failed to fetch from ProxyScrape.com: {e}")
        
        # Source 3: Geonode Free Proxy List
        try:
            proxies = await self._fetch_from_geonode()
            all_proxies.extend(proxies)
            self.logger.info(f"Fetched {len(proxies)} proxies from Geonode")
        except Exception as e:
            self.logger.warning(f"Failed to fetch from Geonode: {e}")
        
        # Source 4: ProxyNova
        try:
            proxies = await self._fetch_from_proxynova()
            all_proxies.extend(proxies)
            self.logger.info(f"Fetched {len(proxies)} proxies from ProxyNova")
        except Exception as e:
            self.logger.warning(f"Failed to fetch from ProxyNova: {e}")
        
        # Remove duplicates
        unique_proxies = self._remove_duplicates(all_proxies)
        self.logger.info(f"Total unique proxies fetched: {len(unique_proxies)}")
        
        return unique_proxies
    
    async def _fetch_from_freeproxylist(self) -> List[ProxyInfo]:
        """Fetch proxies from FreeProxyList.net."""
        url = "https://free-proxy-list.net/"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=self.timeout) as response:
                if response.status == 200:
                    html = await response.text()
                    # Extract proxies from the table
                    proxy_pattern = r'<tr><td>(\d+\.\d+\.\d+\.\d+)</td><td>(\d+)</td><td>([A-Z]{2})</td><td>([^<]+)</td><td>([^<]+)</td>'
                    matches = re.findall(proxy_pattern, html)
                    
                    proxies = []
                    for match in matches:
                        ip, port, country, anonymity, https = match
                        protocol = 'https' if https.strip() == 'yes' else 'http'
                        proxies.append(ProxyInfo(
                            ip=ip,
                            port=int(port),
                            protocol=protocol,
                            country=country,
                            anonymity=anonymity.strip()
                        ))
                    return proxies
        return []
    
    async def _fetch_from_proxyscrape(self) -> List[ProxyInfo]:
        """Fetch proxies from ProxyScrape.com."""
        urls = [
            "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
            "https://api.proxyscrape.com/v2/?request=get&protocol=https&timeout=10000&country=all&ssl=all&anonymity=all"
        ]
        
        all_proxies = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.get(url, timeout=self.timeout) as response:
                        if response.status == 200:
                            text = await response.text()
                            lines = text.strip().split('\n')
                            
                            for line in lines:
                                if ':' in line:
                                    ip, port = line.split(':')
                                    try:
                                        all_proxies.append(ProxyInfo(
                                            ip=ip.strip(),
                                            port=int(port.strip()),
                                            protocol='http' if 'http' in url else 'https'
                                        ))
                                    except ValueError:
                                        continue
                except Exception as e:
                    self.logger.warning(f"Error fetching from {url}: {e}")
        
        return all_proxies
    
    async def _fetch_from_geonode(self) -> List[ProxyInfo]:
        """Fetch proxies from Geonode Free Proxy List."""
        url = "https://proxylist.geonode.com/api/proxy-list?limit=100&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps&anonymityLevel=elite&country=US"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=self.timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        proxies = []
                        
                        for item in data.get('data', []):
                            try:
                                proxies.append(ProxyInfo(
                                    ip=item['ip'],
                                    port=int(item['port']),
                                    protocol=item.get('protocol', 'http'),
                                    country=item.get('country'),
                                    anonymity=item.get('anonymityLevel')
                                ))
                            except (KeyError, ValueError):
                                continue
                        
                        return proxies
            except Exception as e:
                self.logger.warning(f"Error fetching from Geonode: {e}")
        
        return []
    
    async def _fetch_from_proxynova(self) -> List[ProxyInfo]:
        """Fetch proxies from ProxyNova."""
        url = "https://www.proxynova.com/proxy-server-list/"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=self.timeout) as response:
                    if response.status == 200:
                        html = await response.text()
                        # Extract proxies from the table
                        proxy_pattern = r'<tr><td>(\d+\.\d+\.\d+\.\d+)</td><td>(\d+)</td><td>([A-Z]{2})</td><td>([^<]+)</td>'
                        matches = re.findall(proxy_pattern, html)
                        
                        proxies = []
                        for match in matches:
                            ip, port, country, anonymity = match
                            proxies.append(ProxyInfo(
                                ip=ip,
                                port=int(port),
                                protocol='http',
                                country=country,
                                anonymity=anonymity.strip()
                            ))
                        return proxies
            except Exception as e:
                self.logger.warning(f"Error fetching from ProxyNova: {e}")
        
        return []
    
    def _remove_duplicates(self, proxies: List[ProxyInfo]) -> List[ProxyInfo]:
        """Remove duplicate proxies based on IP:port combination."""
        seen = set()
        unique_proxies = []
        
        for proxy in proxies:
            key = f"{proxy.ip}:{proxy.port}"
            if key not in seen:
                seen.add(key)
                unique_proxies.append(proxy)
        
        return unique_proxies
    
    async def validate_proxy(self, proxy: ProxyInfo) -> bool:
        """Test if a proxy is working."""
        if f"{proxy.ip}:{proxy.port}" in self.failed_proxies:
            return False
        
        test_url = random.choice(self.test_urls)
        proxy_url = f"{proxy.protocol}://{proxy.ip}:{proxy.port}"
        
        try:
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    test_url,
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                ) as response:
                    if response.status == 200:
                        proxy.speed = time.time() - start_time
                        proxy.is_working = True
                        proxy.success_count += 1
                        proxy.last_checked = datetime.now()
                        return True
        except Exception as e:
            proxy.fail_count += 1
            proxy.is_working = False
            proxy.last_checked = datetime.now()
            
            # If proxy fails multiple times, add to failed set
            if proxy.fail_count >= 3:
                self.failed_proxies.add(f"{proxy.ip}:{proxy.port}")
        
        return False
    
    async def validate_proxies(self, proxies: List[ProxyInfo], max_concurrent: int = 10) -> List[ProxyInfo]:
        """Validate multiple proxies concurrently."""
        working_proxies = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def validate_single(proxy: ProxyInfo):
            async with semaphore:
                if await self.validate_proxy(proxy):
                    working_proxies.append(proxy)
        
        # Create tasks for all proxies
        tasks = [validate_single(proxy) for proxy in proxies]
        
        # Run validation with progress updates
        total = len(tasks)
        completed = 0
        
        for task in asyncio.as_completed(tasks):
            await task
            completed += 1
            if completed % 10 == 0 or completed == total:
                self.logger.info(f"Validated {completed}/{total} proxies. Working: {len(working_proxies)}")
        
        return working_proxies
    
    async def refresh_proxies(self, force: bool = False) -> List[ProxyInfo]:
        """Refresh the proxy list."""
        if not force and self.last_fetch and datetime.now() - self.last_fetch < self.fetch_interval:
            self.logger.info("Using cached proxies")
            return self.working_proxies
        
        self.logger.info("Fetching fresh proxies...")
        
        # Fetch new proxies
        new_proxies = await self.fetch_proxies_from_sources()
        
        if not new_proxies:
            self.logger.warning("No proxies fetched, using existing working proxies")
            return self.working_proxies
        
        # Validate new proxies
        self.logger.info(f"Validating {len(new_proxies)} proxies...")
        working_new = await self.validate_proxies(new_proxies)
        
        # Combine with existing working proxies
        all_working = self.working_proxies + working_new
        all_working = self._remove_duplicates(all_working)
        
        # Sort by success rate and speed
        all_working.sort(key=lambda p: (p.success_count, -p.speed if p.speed else 0), reverse=True)
        
        # Keep only the best proxies
        self.working_proxies = all_working[:self.max_proxies]
        self.last_fetch = datetime.now()
        
        self.logger.info(f"Proxy refresh complete. {len(self.working_proxies)} working proxies available")
        return self.working_proxies
    
    def get_random_proxy(self) -> Optional[ProxyInfo]:
        """Get a random working proxy."""
        if not self.working_proxies:
            return None
        
        # Weight by success rate
        weights = [proxy.success_count + 1 for proxy in self.working_proxies]
        return random.choices(self.working_proxies, weights=weights)[0]
    
    def get_proxy_dict(self, proxy: ProxyInfo) -> Dict[str, str]:
        """Convert ProxyInfo to dictionary format for Playwright."""
        return {
            "server": f"{proxy.protocol}://{proxy.ip}:{proxy.port}"
        }
    
    def get_stats(self) -> Dict:
        """Get proxy statistics."""
        return {
            "total_working": len(self.working_proxies),
            "total_failed": len(self.failed_proxies),
            "last_fetch": self.last_fetch.isoformat() if self.last_fetch else None,
            "avg_speed": sum(p.speed for p in self.working_proxies if p.speed) / len(self.working_proxies) if self.working_proxies else 0,
            "top_countries": self._get_top_countries()
        }
    
    def _get_top_countries(self) -> List[str]:
        """Get top countries by proxy count."""
        countries = {}
        for proxy in self.working_proxies:
            if proxy.country:
                countries[proxy.country] = countries.get(proxy.country, 0) + 1
        
        return sorted(countries.items(), key=lambda x: x[1], reverse=True)[:5]

# Global proxy manager instance
_proxy_manager: Optional[FreeProxyManager] = None

def get_proxy_manager() -> FreeProxyManager:
    """Get the global proxy manager instance."""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = FreeProxyManager()
    return _proxy_manager

async def initialize_proxy_manager():
    """Initialize the global proxy manager."""
    manager = get_proxy_manager()
    await manager.refresh_proxies(force=True)
    return manager
