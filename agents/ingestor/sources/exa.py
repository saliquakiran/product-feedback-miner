"""
Exa AI API client for collecting web content and search results.

This module provides functionality to fetch web content using Exa AI
for product feedback analysis.
"""

import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

from config.settings import config
from config.api_keys import api_keys

logger = logging.getLogger(__name__)

@dataclass
class ExaSearchResult:
    """Exa AI search result data structure."""
    id: str
    title: str
    url: str
    content: str
    author: str
    published_date: datetime
    score: float
    raw_metadata: Dict[str, Any]

class ExaAPIClient:
    """Exa AI API client with rate limiting and error handling."""
    
    def __init__(self):
        self.base_url = config.exa.base_url
        self.api_key = api_keys.exa_api_key
        self.timeout = config.exa.timeout
        self.max_retries = config.exa.max_retries
        self.rate_limit_per_minute = config.exa.rate_limit_per_minute
        
        # Rate limiting
        self.rate_limit_remaining = 60
        self.rate_limit_reset = None
        
    async def search_content(
        self,
        query: str,
        num_results: int = 20,
        start_published_date: Optional[datetime] = None,
        end_published_date: Optional[datetime] = None,
        site: Optional[str] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> List[ExaSearchResult]:
        """
        Search for content using Exa AI.
        
        Args:
            query: Search query
            num_results: Number of results to return
            start_published_date: Start date for published content
            end_published_date: End date for published content
            site: Specific site to search
            exclude_domains: Domains to exclude from search
            
        Returns:
            List of ExaSearchResult objects
        """
        results = []
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "Product-Feedback-Miner/1.0"
            }
        ) as session:
            try:
                # Check rate limit
                await self._check_rate_limit()
                
                # Build search parameters
                search_params = {
                    "query": query,
                    "numResults": num_results,
                    "type": "neural",
                    "useAutoprompt": True,
                    "includeDomains": [site] if site else None,
                    "excludeDomains": exclude_domains or [],
                    "startPublishedDate": start_published_date.isoformat() if start_published_date else None,
                    "endPublishedDate": end_published_date.isoformat() if end_published_date else None
                }
                
                # Remove None values
                search_params = {k: v for k, v in search_params.items() if v is not None}
                
                async with session.post(
                    f"{self.base_url}/search",
                    json=search_params
                ) as response:
                    
                    # Update rate limit info
                    self.rate_limit_remaining = int(
                        response.headers.get("X-RateLimit-Remaining", 0)
                    )
                    self.rate_limit_reset = int(
                        response.headers.get("X-RateLimit-Reset", 0)
                    )
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        for result_data in data.get("results", []):
                            result = self._parse_search_result(result_data)
                            results.append(result)
                            
                    elif response.status == 429:
                        logger.warning("Exa AI API rate limit exceeded")
                        await self._wait_for_rate_limit_reset()
                        return await self.search_content(
                            query, num_results, start_published_date, 
                            end_published_date, site, exclude_domains
                        )
                        
                    else:
                        logger.error(f"Exa AI API error: {response.status}")
                        response.raise_for_status()
                        
            except asyncio.TimeoutError:
                logger.warning("Exa AI API timeout")
            except Exception as e:
                logger.error(f"Error searching with Exa AI: {e}")
        
        logger.info(f"Fetched {len(results)} Exa AI search results for query: {query}")
        return results
    
    async def search_feedback_content(
        self,
        product_name: str,
        num_results: int = 30,
        days_back: int = 30
    ) -> List[ExaSearchResult]:
        """
        Search for product feedback content using Exa AI.
        
        Args:
            product_name: Name of the product to search for
            num_results: Number of results to return
            days_back: Number of days to look back
            
        Returns:
            List of ExaSearchResult objects
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Build feedback-specific queries (reduced set for better reliability)
        queries = [
            f"{product_name} feedback",
            f"{product_name} review",
            f"{product_name} issue",
            f"{product_name} bug report",
            f"{product_name} feature request"
        ]
        
        all_results = []
        
        for query in queries:
            try:
                results = await self.search_content(
                    query=query,
                    num_results=num_results // len(queries),
                    start_published_date=start_date,
                    end_published_date=end_date,
                    exclude_domains=[
                        "github.com",  # We get GitHub data separately
                        "hackernews.com",  # We get HN data separately
                        "reddit.com",  # Can be added later
                        "stackoverflow.com"  # Can be added later
                    ]
                )
                all_results.extend(results)
                
                # Longer delay between queries to respect rate limits
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.warning(f"Error searching for query '{query}': {e}")
                # Log more details for debugging
                if "400" in str(e):
                    logger.warning(f"400 error for query '{query}' - possible rate limit or invalid request format")
                continue
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        logger.info(f"Fetched {len(unique_results)} unique Exa AI feedback results for {product_name}")
        return unique_results
    
    async def get_content(
        self,
        url: str
    ) -> Optional[ExaSearchResult]:
        """
        Get full content for a specific URL.
        
        Args:
            url: URL to get content for
            
        Returns:
            ExaSearchResult object with full content
        """
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "Product-Feedback-Miner/1.0"
            }
        ) as session:
            try:
                await self._check_rate_limit()
                
                async with session.post(
                    f"{self.base_url}/contents",
                    json={"url": url}
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_content_result(data)
                    else:
                        logger.warning(f"Error getting content for {url}: {response.status}")
                        return None
                        
            except Exception as e:
                logger.error(f"Error getting content for {url}: {e}")
                return None
    
    def _parse_search_result(self, result_data: Dict[str, Any]) -> ExaSearchResult:
        """Parse Exa AI search result data into ExaSearchResult object."""
        return ExaSearchResult(
            id=result_data.get("id", ""),
            title=result_data.get("title", ""),
            url=result_data.get("url", ""),
            content=result_data.get("text", ""),
            author=result_data.get("author", ""),
            published_date=self._parse_date(
                result_data.get("publishedDate", datetime.now().isoformat())
            ),
            score=result_data.get("score", 0.0),
            raw_metadata={
                "domain": result_data.get("domain", ""),
                "language": result_data.get("language", ""),
                "type": result_data.get("type", ""),
                "publishedDate": result_data.get("publishedDate", ""),
                "title": result_data.get("title", ""),
                "url": result_data.get("url", ""),
                "text": result_data.get("text", ""),
                "author": result_data.get("author", ""),
                "score": result_data.get("score", 0.0)
            }
        )
    
    def _parse_content_result(self, content_data: Dict[str, Any]) -> ExaSearchResult:
        """Parse Exa AI content result data into ExaSearchResult object."""
        return ExaSearchResult(
            id=content_data.get("id", ""),
            title=content_data.get("title", ""),
            url=content_data.get("url", ""),
            content=content_data.get("text", ""),
            author=content_data.get("author", ""),
            published_date=self._parse_date(
                content_data.get("publishedDate", datetime.now().isoformat())
            ),
            score=content_data.get("score", 0.0),
            raw_metadata=content_data
        )
    
    def _parse_date(self, date_string: str) -> datetime:
        """Parse date string from Exa AI API, handling various formats."""
        try:
            # Handle ISO format with 'Z' suffix
            if date_string.endswith('Z'):
                date_string = date_string[:-1] + '+00:00'
            return datetime.fromisoformat(date_string)
        except ValueError:
            # Fallback to current time if parsing fails
            logger.warning(f"Failed to parse date '{date_string}', using current time")
            return datetime.now()
    
    async def _check_rate_limit(self):
        """Check if we're approaching rate limit."""
        if self.rate_limit_remaining < 10:  # Safety margin
            logger.warning("Approaching Exa AI API rate limit")
            await self._wait_for_rate_limit_reset()
    
    async def _wait_for_rate_limit_reset(self):
        """Wait for rate limit to reset."""
        if self.rate_limit_reset:
            wait_time = self.rate_limit_reset - datetime.now().timestamp()
            if wait_time > 0:
                logger.info(f"Waiting {wait_time:.0f} seconds for rate limit reset")
                await asyncio.sleep(wait_time)
    
    async def test_connection(self) -> bool:
        """Test Exa AI API connection."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "Product-Feedback-Miner/1.0"
                }
            ) as session:
                async with session.post(
                    f"{self.base_url}/search",
                    json={"query": "test", "numResults": 1}
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Exa AI API connection test failed: {e}")
            return False
