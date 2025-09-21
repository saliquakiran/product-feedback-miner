"""
Twitter/X API client for collecting tweets and mentions.

This module provides functionality to fetch tweets, mentions, and hashtags
for product feedback analysis using the Twitter API v2.
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
class TwitterPost:
    """Twitter/X post data structure."""
    id: str
    text: str
    author: str
    author_username: str
    author_url: str
    url: str
    created_at: datetime
    retweet_count: int
    like_count: int
    reply_count: int
    quote_count: int
    is_retweet: bool
    is_reply: bool
    hashtags: List[str]
    mentions: List[str]
    raw_metadata: Dict[str, Any]

class TwitterAPIClient:
    """Twitter/X API client with rate limiting and error handling."""
    
    def __init__(self):
        self.base_url = config.twitter.base_url
        self.bearer_token = api_keys.twitter_bearer_token
        self.timeout = config.twitter.timeout
        self.max_retries = config.twitter.max_retries
        self.rate_limit_per_minute = config.twitter.rate_limit_per_minute
        
        # Rate limiting
        self.rate_limit_remaining = 300
        self.rate_limit_reset = None
        
    async def search_tweets(
        self,
        query: str,
        max_results: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        include_retweets: bool = False
    ) -> List[TwitterPost]:
        """
        Search for tweets using Twitter API v2.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            start_time: Start time for tweets
            end_time: End time for tweets
            include_retweets: Whether to include retweets
            
        Returns:
            List of TwitterPost objects
        """
        tweets = []
        next_token = None
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json",
                "User-Agent": "Product-Feedback-Miner/1.0"
            }
        ) as session:
            
            while len(tweets) < max_results:
                # Check rate limit
                await self._check_rate_limit()
                
                # Build search parameters
                params = {
                    "query": query,
                    "max_results": min(100, max_results - len(tweets)),
                    "tweet.fields": "id,text,author_id,created_at,public_metrics,referenced_tweets,entities",
                    "user.fields": "id,username,name,url",
                    "expansions": "author_id"
                }
                
                if start_time:
                    params["start_time"] = start_time.isoformat() + "Z"
                if end_time:
                    params["end_time"] = end_time.isoformat() + "Z"
                if not include_retweets:
                    params["query"] += " -is:retweet"
                if next_token:
                    params["next_token"] = next_token
                
                try:
                    async with session.get(f"{self.base_url}/tweets/search/recent", params=params) as response:
                        # Update rate limit info
                        self.rate_limit_remaining = int(
                            response.headers.get("x-rate-limit-remaining", 0)
                        )
                        self.rate_limit_reset = int(
                            response.headers.get("x-rate-limit-reset", 0)
                        )
                        
                        if response.status == 200:
                            data = await response.json()
                            
                            # Get users data for author info
                            users = {user["id"]: user for user in data.get("includes", {}).get("users", [])}
                            
                            for tweet_data in data.get("data", []):
                                tweet = self._parse_tweet(tweet_data, users)
                                tweets.append(tweet)
                            
                            # Check if there are more results
                            next_token = data.get("meta", {}).get("next_token")
                            if not next_token:
                                break
                                
                        elif response.status == 429:
                            logger.warning("Twitter API rate limit exceeded")
                            await self._wait_for_rate_limit_reset()
                            continue
                            
                        else:
                            logger.error(f"Twitter API error: {response.status}")
                            response.raise_for_status()
                            
                except asyncio.TimeoutError:
                    logger.warning("Twitter API timeout")
                    break
                except Exception as e:
                    logger.error(f"Error fetching tweets: {e}")
                    break
        
        logger.info(f"Fetched {len(tweets)} tweets for query: {query}")
        return tweets
    
    async def search_product_mentions(
        self,
        product_name: str,
        max_results: int = 200,
        days_back: int = 7
    ) -> List[TwitterPost]:
        """
        Search for product mentions on Twitter.
        
        Args:
            product_name: Name of the product to search for
            max_results: Maximum number of results to return
            days_back: Number of days to look back
            
        Returns:
            List of TwitterPost objects
        """
        # Calculate date range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)
        
        # Build product-specific queries
        queries = [
            f"{product_name} feedback",
            f"{product_name} review",
            f"{product_name} bug",
            f"{product_name} issue",
            f"{product_name} feature",
            f"{product_name} complaint",
            f"{product_name} problem",
            f"#{product_name.lower().replace(' ', '')}",
            f"@{product_name.lower().replace(' ', '')}"
        ]
        
        all_tweets = []
        
        for query in queries:
            try:
                tweets = await self.search_tweets(
                    query=query,
                    max_results=max_results // len(queries),
                    start_time=start_time,
                    end_time=end_time,
                    include_retweets=False
                )
                all_tweets.extend(tweets)
                
                # Small delay between queries to be respectful
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"Error searching Twitter for query '{query}': {e}")
                continue
        
        # Remove duplicates based on tweet ID
        seen_ids = set()
        unique_tweets = []
        for tweet in all_tweets:
            if tweet.id not in seen_ids:
                seen_ids.add(tweet.id)
                unique_tweets.append(tweet)
        
        logger.info(f"Fetched {len(unique_tweets)} unique Twitter mentions for {product_name}")
        return unique_tweets
    
    async def get_tweet_metrics(
        self,
        tweet_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed metrics for a specific tweet.
        
        Args:
            tweet_id: ID of the tweet
            
        Returns:
            Tweet metrics or None if failed
        """
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json",
                "User-Agent": "Product-Feedback-Miner/1.0"
            }
        ) as session:
            try:
                params = {
                    "tweet.fields": "public_metrics,context_annotations"
                }
                
                async with session.get(
                    f"{self.base_url}/tweets/{tweet_id}",
                    params=params
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return data.get("data", {}).get("public_metrics", {})
                    else:
                        logger.warning(f"Error getting tweet metrics for {tweet_id}: {response.status}")
                        return None
                        
            except Exception as e:
                logger.error(f"Error getting tweet metrics for {tweet_id}: {e}")
                return None
    
    def _parse_tweet(self, tweet_data: Dict[str, Any], users: Dict[str, Dict[str, Any]]) -> TwitterPost:
        """Parse Twitter API response into TwitterPost object."""
        author_id = tweet_data.get("author_id", "")
        author_info = users.get(author_id, {})
        
        # Extract hashtags and mentions
        entities = tweet_data.get("entities", {})
        hashtags = [tag["tag"] for tag in entities.get("hashtags", [])]
        mentions = [mention["username"] for mention in entities.get("mentions", [])]
        
        # Check if it's a retweet or reply
        referenced_tweets = tweet_data.get("referenced_tweets", [])
        is_retweet = any(ref["type"] == "retweeted" for ref in referenced_tweets)
        is_reply = any(ref["type"] == "replied_to" for ref in referenced_tweets)
        
        # Get metrics
        metrics = tweet_data.get("public_metrics", {})
        
        return TwitterPost(
            id=tweet_data["id"],
            text=tweet_data["text"],
            author=author_info.get("name", "Unknown"),
            author_username=author_info.get("username", "unknown"),
            author_url=f"https://twitter.com/{author_info.get('username', '')}" if author_info.get("username") else "",
            url=f"https://twitter.com/{author_info.get('username', '')}/status/{tweet_data['id']}" if author_info.get("username") else "",
            created_at=datetime.fromisoformat(tweet_data["created_at"].replace("Z", "+00:00")),
            retweet_count=metrics.get("retweet_count", 0),
            like_count=metrics.get("like_count", 0),
            reply_count=metrics.get("reply_count", 0),
            quote_count=metrics.get("quote_count", 0),
            is_retweet=is_retweet,
            is_reply=is_reply,
            hashtags=hashtags,
            mentions=mentions,
            raw_metadata={
                "context_annotations": tweet_data.get("context_annotations", []),
                "referenced_tweets": referenced_tweets,
                "author_verified": author_info.get("verified", False),
                "author_followers": author_info.get("public_metrics", {}).get("followers_count", 0),
                "lang": tweet_data.get("lang", "en")
            }
        )
    
    async def _check_rate_limit(self):
        """Check if we're approaching rate limit."""
        if self.rate_limit_remaining < 50:  # Safety margin
            logger.warning("Approaching Twitter API rate limit")
            await self._wait_for_rate_limit_reset()
    
    async def _wait_for_rate_limit_reset(self):
        """Wait for rate limit to reset."""
        if self.rate_limit_reset:
            wait_time = self.rate_limit_reset - datetime.utcnow().timestamp()
            if wait_time > 0:
                logger.info(f"Waiting {wait_time:.0f} seconds for rate limit reset")
                await asyncio.sleep(wait_time)
    
    async def test_connection(self) -> bool:
        """Test Twitter API connection."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    "Authorization": f"Bearer {self.bearer_token}",
                    "Content-Type": "application/json",
                    "User-Agent": "Product-Feedback-Miner/1.0"
                }
            ) as session:
                async with session.get(f"{self.base_url}/tweets/search/recent?query=test&max_results=10") as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Twitter API connection test failed: {e}")
            return False
