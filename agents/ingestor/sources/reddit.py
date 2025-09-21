"""
Reddit API client for collecting posts and comments.

This module provides functionality to fetch Reddit posts, comments, and discussions
for product feedback analysis using the Reddit API.
"""

import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import base64

from config.settings import config
from config.api_keys import api_keys

logger = logging.getLogger(__name__)

@dataclass
class RedditPost:
    """Reddit post data structure."""
    id: str
    title: str
    content: str
    author: str
    author_url: str
    url: str
    subreddit: str
    subreddit_url: str
    created_at: datetime
    score: int
    upvote_ratio: float
    num_comments: int
    is_self: bool  # True if text post, False if link post
    link_url: Optional[str]
    flair: Optional[str]
    awards: List[str]
    raw_metadata: Dict[str, Any]

@dataclass
class RedditComment:
    """Reddit comment data structure."""
    id: str
    content: str
    author: str
    author_url: str
    url: str
    parent_id: str
    post_id: str
    subreddit: str
    created_at: datetime
    score: int
    depth: int
    awards: List[str]
    is_submitter: bool
    raw_metadata: Dict[str, Any]

class RedditAPIClient:
    """Reddit API client with rate limiting and error handling."""
    
    def __init__(self):
        self.base_url = config.reddit.base_url
        self.client_id = api_keys.reddit_client_id
        self.client_secret = api_keys.reddit_client_secret
        self.user_agent = config.reddit.user_agent
        self.timeout = config.reddit.timeout
        self.max_retries = config.reddit.max_retries
        
        # Authentication
        self.access_token = None
        self.token_expires = None
        
        # Rate limiting
        self.rate_limit_remaining = 100
        self.rate_limit_reset = None
    
    async def authenticate(self) -> bool:
        """Authenticate with Reddit API using client credentials."""
        if self.access_token and self.token_expires and datetime.utcnow() < self.token_expires:
            return True
        
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "Authorization": f"Basic {auth_b64}",
                "User-Agent": self.user_agent,
                "Content-Type": "application/x-www-form-urlencoded"
            }
        ) as session:
            try:
                data = {"grant_type": "client_credentials"}
                async with session.post(f"{self.base_url}/api/v1/access_token", data=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        self.access_token = token_data["access_token"]
                        expires_in = token_data.get("expires_in", 3600)
                        self.token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 60)  # 1 minute buffer
                        logger.info("Reddit API authentication successful")
                        return True
                    else:
                        logger.error(f"Reddit API authentication failed: {response.status}")
                        return False
            except Exception as e:
                logger.error(f"Reddit API authentication error: {e}")
                return False
    
    async def search_posts(
        self,
        query: str,
        subreddit: Optional[str] = None,
        limit: int = 100,
        sort: str = "relevance",
        time_filter: str = "week"
    ) -> List[RedditPost]:
        """
        Search for Reddit posts.
        
        Args:
            query: Search query
            subreddit: Specific subreddit to search (optional)
            limit: Maximum number of results
            sort: Sort order (relevance, hot, top, new, comments)
            time_filter: Time filter (hour, day, week, month, year, all)
            
        Returns:
            List of RedditPost objects
        """
        if not await self.authenticate():
            return []
        
        posts = []
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": self.user_agent
            }
        ) as session:
            try:
                # Check rate limit
                await self._check_rate_limit()
                
                # Build search URL
                if subreddit:
                    url = f"{self.base_url}/r/{subreddit}/search.json"
                else:
                    url = f"{self.base_url}/search.json"
                
                params = {
                    "q": query,
                    "limit": min(100, limit),
                    "sort": sort,
                    "t": time_filter,
                    "restrict_sr": "true" if subreddit else "false"
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for post_data in data.get("data", {}).get("children", []):
                            post = self._parse_post(post_data["data"])
                            posts.append(post)
                            
                    elif response.status == 429:
                        logger.warning("Reddit API rate limit exceeded")
                        await self._wait_for_rate_limit_reset()
                    else:
                        logger.error(f"Reddit API error: {response.status}")
                        response.raise_for_status()
                        
            except Exception as e:
                logger.error(f"Error searching Reddit posts: {e}")
        
        logger.info(f"Fetched {len(posts)} Reddit posts for query: {query}")
        return posts
    
    async def get_subreddit_posts(
        self,
        subreddit: str,
        limit: int = 100,
        sort: str = "hot",
        time_filter: str = "week"
    ) -> List[RedditPost]:
        """
        Get posts from a specific subreddit.
        
        Args:
            subreddit: Subreddit name
            limit: Maximum number of results
            sort: Sort order (hot, new, rising, top)
            time_filter: Time filter for top posts
            
        Returns:
            List of RedditPost objects
        """
        if not await self.authenticate():
            return []
        
        posts = []
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": self.user_agent
            }
        ) as session:
            try:
                await self._check_rate_limit()
                
                url = f"{self.base_url}/r/{subreddit}/{sort}.json"
                params = {
                    "limit": min(100, limit),
                    "t": time_filter if sort == "top" else None
                }
                
                # Remove None values
                params = {k: v for k, v in params.items() if v is not None}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for post_data in data.get("data", {}).get("children", []):
                            post = self._parse_post(post_data["data"])
                            posts.append(post)
                            
                    elif response.status == 429:
                        logger.warning("Reddit API rate limit exceeded")
                        await self._wait_for_rate_limit_reset()
                    else:
                        logger.error(f"Reddit API error: {response.status}")
                        response.raise_for_status()
                        
            except Exception as e:
                logger.error(f"Error fetching subreddit posts: {e}")
        
        logger.info(f"Fetched {len(posts)} posts from r/{subreddit}")
        return posts
    
    async def get_post_comments(
        self,
        post_id: str,
        limit: int = 100
    ) -> List[RedditComment]:
        """
        Get comments for a specific post.
        
        Args:
            post_id: Reddit post ID
            limit: Maximum number of comments
            
        Returns:
            List of RedditComment objects
        """
        if not await self.authenticate():
            return []
        
        comments = []
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": self.user_agent
            }
        ) as session:
            try:
                await self._check_rate_limit()
                
                url = f"{self.base_url}/comments/{post_id}.json"
                params = {"limit": min(100, limit)}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Parse comments from the second item in the response
                        if len(data) > 1:
                            comments_data = data[1]["data"]["children"]
                            for comment_data in comments_data:
                                if comment_data["kind"] == "t1":  # Comment type
                                    comment = self._parse_comment(comment_data["data"], post_id)
                                    comments.append(comment)
                                    
                    elif response.status == 429:
                        logger.warning("Reddit API rate limit exceeded")
                        await self._wait_for_rate_limit_reset()
                    else:
                        logger.error(f"Reddit API error: {response.status}")
                        response.raise_for_status()
                        
            except Exception as e:
                logger.error(f"Error fetching post comments: {e}")
        
        logger.info(f"Fetched {len(comments)} comments for post {post_id}")
        return comments
    
    async def search_product_feedback(
        self,
        product_name: str,
        subreddits: Optional[List[str]] = None,
        limit: int = 200,
        days_back: int = 7
    ) -> List[RedditPost]:
        """
        Search for product feedback on Reddit.
        
        Args:
            product_name: Name of the product to search for
            subreddits: List of subreddits to search (optional)
            limit: Maximum number of results
            days_back: Number of days to look back
            
        Returns:
            List of RedditPost objects
        """
        all_posts = []
        
        # Default subreddits for product feedback
        if not subreddits:
            subreddits = [
                "productivity", "software", "technology", "programming",
                "webdev", "datascience", "machinelearning", "startups",
                "entrepreneur", "business", "marketing", "sales"
            ]
        
        # Build search queries
        queries = [
            f"{product_name} feedback",
            f"{product_name} review",
            f"{product_name} bug",
            f"{product_name} issue",
            f"{product_name} feature",
            f"{product_name} complaint",
            f"{product_name} problem",
            f"{product_name} experience"
        ]
        
        for subreddit in subreddits:
            for query in queries:
                try:
                    posts = await self.search_posts(
                        query=query,
                        subreddit=subreddit,
                        limit=limit // (len(subreddits) * len(queries)),
                        sort="relevance",
                        time_filter="week"
                    )
                    all_posts.extend(posts)
                    
                    # Small delay between requests
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"Error searching r/{subreddit} for '{query}': {e}")
                    continue
        
        # Remove duplicates based on post ID
        seen_ids = set()
        unique_posts = []
        for post in all_posts:
            if post.id not in seen_ids:
                seen_ids.add(post.id)
                unique_posts.append(post)
        
        logger.info(f"Fetched {len(unique_posts)} unique Reddit posts for {product_name}")
        return unique_posts
    
    def _parse_post(self, post_data: Dict[str, Any]) -> RedditPost:
        """Parse Reddit API response into RedditPost object."""
        return RedditPost(
            id=post_data["id"],
            title=post_data.get("title", ""),
            content=post_data.get("selftext", ""),
            author=post_data.get("author", "[deleted]"),
            author_url=f"https://reddit.com/u/{post_data.get('author', '')}" if post_data.get("author") != "[deleted]" else "",
            url=f"https://reddit.com{post_data.get('permalink', '')}",
            subreddit=post_data.get("subreddit", ""),
            subreddit_url=f"https://reddit.com/r/{post_data.get('subreddit', '')}",
            created_at=datetime.fromtimestamp(post_data["created_utc"]),
            score=post_data.get("score", 0),
            upvote_ratio=post_data.get("upvote_ratio", 0.0),
            num_comments=post_data.get("num_comments", 0),
            is_self=post_data.get("is_self", True),
            link_url=post_data.get("url") if not post_data.get("is_self") else None,
            flair=post_data.get("link_flair_text"),
            awards=[],  # Reddit API doesn't provide awards in basic requests
            raw_metadata={
                "domain": post_data.get("domain", ""),
                "is_original_content": post_data.get("is_original_content", False),
                "is_crosspostable": post_data.get("is_crosspostable", False),
                "is_reddit_media_domain": post_data.get("is_reddit_media_domain", False),
                "is_video": post_data.get("is_video", False),
                "over_18": post_data.get("over_18", False),
                "spoiler": post_data.get("spoiler", False),
                "stickied": post_data.get("stickied", False),
                "gilded": post_data.get("gilded", 0),
                "distinguished": post_data.get("distinguished"),
                "post_hint": post_data.get("post_hint"),
                "preview": post_data.get("preview", {}),
                "thumbnail": post_data.get("thumbnail", "")
            }
        )
    
    def _parse_comment(self, comment_data: Dict[str, Any], post_id: str) -> RedditComment:
        """Parse Reddit API response into RedditComment object."""
        return RedditComment(
            id=comment_data["id"],
            content=comment_data.get("body", ""),
            author=comment_data.get("author", "[deleted]"),
            author_url=f"https://reddit.com/u/{comment_data.get('author', '')}" if comment_data.get("author") != "[deleted]" else "",
            url=f"https://reddit.com{comment_data.get('permalink', '')}",
            parent_id=comment_data.get("parent_id", ""),
            post_id=post_id,
            subreddit=comment_data.get("subreddit", ""),
            created_at=datetime.fromtimestamp(comment_data["created_utc"]),
            score=comment_data.get("score", 0),
            depth=comment_data.get("depth", 0),
            awards=[],  # Reddit API doesn't provide awards in basic requests
            is_submitter=comment_data.get("is_submitter", False),
            raw_metadata={
                "gilded": comment_data.get("gilded", 0),
                "distinguished": comment_data.get("distinguished"),
                "stickied": comment_data.get("stickied", False),
                "collapsed": comment_data.get("collapsed", False),
                "is_submitter": comment_data.get("is_submitter", False),
                "link_id": comment_data.get("link_id", ""),
                "parent_id": comment_data.get("parent_id", "")
            }
        )
    
    async def _check_rate_limit(self):
        """Check if we're approaching rate limit."""
        if self.rate_limit_remaining < 10:  # Safety margin
            logger.warning("Approaching Reddit API rate limit")
            await self._wait_for_rate_limit_reset()
    
    async def _wait_for_rate_limit_reset(self):
        """Wait for rate limit to reset."""
        if self.rate_limit_reset:
            wait_time = self.rate_limit_reset - datetime.utcnow().timestamp()
            if wait_time > 0:
                logger.info(f"Waiting {wait_time:.0f} seconds for rate limit reset")
                await asyncio.sleep(wait_time)
    
    async def test_connection(self) -> bool:
        """Test Reddit API connection."""
        try:
            return await self.authenticate()
        except Exception as e:
            logger.error(f"Reddit API connection test failed: {e}")
            return False
