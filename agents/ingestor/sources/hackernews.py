"""
Hacker News API client for collecting posts and comments.

This module provides functionality to fetch Hacker News posts and comments
for product feedback analysis.
"""

import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

from config.settings import config

logger = logging.getLogger(__name__)

@dataclass
class HackerNewsPost:
    """Hacker News post data structure."""
    id: int
    title: str
    text: str
    author: str
    url: str
    score: int
    time: datetime
    descendants: int  # Number of comments
    type: str  # story, comment, poll, etc.
    raw_metadata: Dict[str, Any]

class HackerNewsAPIClient:
    """Hacker News API client with rate limiting and error handling."""
    
    def __init__(self):
        self.base_url = config.hackernews.base_url
        self.timeout = config.hackernews.timeout
        self.max_retries = config.hackernews.max_retries
        
    async def fetch_top_stories(
        self, 
        limit: int = 100,
        min_score: int = 10
    ) -> List[HackerNewsPost]:
        """
        Fetch top Hacker News stories.
        
        Args:
            limit: Maximum number of stories to fetch
            min_score: Minimum score threshold
            
        Returns:
            List of HackerNewsPost objects
        """
        stories = []
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            try:
                # Get top story IDs
                async with session.get(f"{self.base_url}/topstories.json") as response:
                    if response.status == 200:
                        story_ids = await response.json()
                        
                        # Fetch story details
                        for story_id in story_ids[:limit]:
                            story = await self._fetch_story(session, story_id)
                            if story and story.score >= min_score:
                                stories.append(story)
                                
            except Exception as e:
                logger.error(f"Error fetching Hacker News top stories: {e}")
        
        logger.info(f"Fetched {len(stories)} Hacker News stories")
        return stories
    
    async def fetch_stories_by_keywords(
        self, 
        keywords: List[str],
        limit: int = 50,
        min_score: int = 5
    ) -> List[HackerNewsPost]:
        """
        Fetch Hacker News stories containing specific keywords.
        
        Args:
            keywords: List of keywords to search for
            limit: Maximum number of stories to fetch
            min_score: Minimum score threshold
            
        Returns:
            List of HackerNewsPost objects
        """
        stories = []
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            try:
                # Get new story IDs
                async with session.get(f"{self.base_url}/newstories.json") as response:
                    if response.status == 200:
                        story_ids = await response.json()
                        
                        # Fetch story details and filter by keywords
                        for story_id in story_ids[:limit * 2]:  # Fetch more to filter
                            story = await self._fetch_story(session, story_id)
                            if story and story.score >= min_score:
                                # Check if story contains any keywords
                                text_to_search = f"{story.title} {story.text}".lower()
                                if any(keyword.lower() in text_to_search for keyword in keywords):
                                    stories.append(story)
                                    
                                    if len(stories) >= limit:
                                        break
                                        
            except Exception as e:
                logger.error(f"Error fetching Hacker News stories by keywords: {e}")
        
        logger.info(f"Fetched {len(stories)} Hacker News stories matching keywords")
        return stories
    
    async def fetch_story_comments(
        self, 
        story_id: int,
        limit: int = 50
    ) -> List[HackerNewsPost]:
        """
        Fetch comments for a specific story.
        
        Args:
            story_id: ID of the story
            limit: Maximum number of comments to fetch
            
        Returns:
            List of HackerNewsPost objects (comments)
        """
        comments = []
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            try:
                # Get story details first
                story = await self._fetch_story(session, story_id)
                if not story:
                    return comments
                
                # Get comment IDs
                story_data = await self._fetch_item(session, story_id)
                if story_data and "kids" in story_data:
                    comment_ids = story_data["kids"][:limit]
                    
                    # Fetch comment details
                    for comment_id in comment_ids:
                        comment = await self._fetch_comment(session, comment_id)
                        if comment:
                            comments.append(comment)
                            
            except Exception as e:
                logger.error(f"Error fetching Hacker News comments: {e}")
        
        logger.info(f"Fetched {len(comments)} Hacker News comments for story {story_id}")
        return comments
    
    async def _fetch_story(self, session: aiohttp.ClientSession, story_id: int) -> Optional[HackerNewsPost]:
        """Fetch a single story by ID."""
        try:
            story_data = await self._fetch_item(session, story_id)
            if story_data and story_data.get("type") == "story":
                return self._parse_story(story_data)
        except Exception as e:
            logger.warning(f"Error fetching story {story_id}: {e}")
        return None
    
    async def _fetch_comment(self, session: aiohttp.ClientSession, comment_id: int) -> Optional[HackerNewsPost]:
        """Fetch a single comment by ID."""
        try:
            comment_data = await self._fetch_item(session, comment_id)
            if comment_data and comment_data.get("type") == "comment":
                return self._parse_comment(comment_data)
        except Exception as e:
            logger.warning(f"Error fetching comment {comment_id}: {e}")
        return None
    
    async def _fetch_item(self, session: aiohttp.ClientSession, item_id: int) -> Optional[Dict[str, Any]]:
        """Fetch an item by ID from Hacker News API."""
        try:
            async with session.get(f"{self.base_url}/item/{item_id}.json") as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    logger.warning(f"Item {item_id} not found")
                    return None
                else:
                    response.raise_for_status()
        except Exception as e:
            logger.warning(f"Error fetching item {item_id}: {e}")
        return None
    
    def _parse_story(self, story_data: Dict[str, Any]) -> HackerNewsPost:
        """Parse Hacker News story data into HackerNewsPost object."""
        return HackerNewsPost(
            id=story_data["id"],
            title=story_data.get("title", ""),
            text=story_data.get("text", ""),
            author=story_data.get("by", "unknown"),
            url=story_data.get("url", ""),
            score=story_data.get("score", 0),
            time=datetime.fromtimestamp(story_data["time"]),
            descendants=story_data.get("descendants", 0),
            type=story_data.get("type", "story"),
            raw_metadata={
                "kids": story_data.get("kids", []),
                "parent": story_data.get("parent"),
                "parts": story_data.get("parts", []),
                "deleted": story_data.get("deleted", False),
                "dead": story_data.get("dead", False)
            }
        )
    
    def _parse_comment(self, comment_data: Dict[str, Any]) -> HackerNewsPost:
        """Parse Hacker News comment data into HackerNewsPost object."""
        return HackerNewsPost(
            id=comment_data["id"],
            title="",  # Comments don't have titles
            text=comment_data.get("text", ""),
            author=comment_data.get("by", "unknown"),
            url="",  # Comments don't have URLs
            score=comment_data.get("score", 0),
            time=datetime.fromtimestamp(comment_data["time"]),
            descendants=comment_data.get("descendants", 0),
            type=comment_data.get("type", "comment"),
            raw_metadata={
                "kids": comment_data.get("kids", []),
                "parent": comment_data.get("parent"),
                "deleted": comment_data.get("deleted", False),
                "dead": comment_data.get("dead", False)
            }
        )
    
    async def test_connection(self) -> bool:
        """Test Hacker News API connection."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.get(f"{self.base_url}/topstories.json") as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Hacker News API connection test failed: {e}")
            return False
