"""
GitHub API client for collecting issues and discussions.

This module provides functionality to fetch GitHub issues, discussions,
and pull requests for product feedback analysis.
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
class GitHubIssue:
    """GitHub issue data structure."""
    id: int
    number: int
    title: str
    body: str
    author: str
    author_url: str
    url: str
    created_at: datetime
    updated_at: datetime
    labels: List[str]
    state: str
    comments_count: int
    assignees: List[str]
    raw_metadata: Dict[str, Any]

class GitHubAPIClient:
    """GitHub API client with rate limiting and error handling."""
    
    def __init__(self):
        self.base_url = config.github.base_url
        self.token = api_keys.github_token
        self.timeout = config.github.timeout
        self.max_retries = config.github.max_retries
        self.rate_limit_per_minute = config.github.rate_limit_per_minute
        
        # Rate limiting
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = None
        
    async def fetch_issues(
        self, 
        owner: str, 
        repo: str, 
        since: Optional[datetime] = None,
        state: str = "all",
        labels: Optional[List[str]] = None
    ) -> List[GitHubIssue]:
        """
        Fetch GitHub issues for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            since: Only fetch issues updated since this date
            state: Issue state (open, closed, all)
            labels: Filter by labels
            
        Returns:
            List of GitHubIssue objects
        """
        issues = []
        page = 1
        per_page = 100
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Product-Feedback-Miner/1.0"
            }
        ) as session:
            
            while True:
                # Check rate limit
                await self._check_rate_limit()
                
                # Build URL with parameters
                url = f"{self.base_url}/repos/{owner}/{repo}/issues"
                params = {
                    "state": state,
                    "page": page,
                    "per_page": per_page,
                    "sort": "updated",
                    "direction": "desc"
                }
                
                if since:
                    params["since"] = since.isoformat()
                
                if labels:
                    params["labels"] = ",".join(labels)
                
                try:
                    async with session.get(url, params=params) as response:
                        # Update rate limit info
                        self.rate_limit_remaining = int(
                            response.headers.get("X-RateLimit-Remaining", 0)
                        )
                        self.rate_limit_reset = int(
                            response.headers.get("X-RateLimit-Reset", 0)
                        )
                        
                        if response.status == 200:
                            data = await response.json()
                            
                            if not data:  # No more issues
                                break
                            
                            for issue_data in data:
                                # Skip pull requests (they have pull_request field)
                                if "pull_request" in issue_data:
                                    continue
                                
                                issue = self._parse_issue(issue_data)
                                issues.append(issue)
                            
                            page += 1
                            
                        elif response.status == 403:
                            logger.warning("GitHub API rate limit exceeded")
                            await self._wait_for_rate_limit_reset()
                            continue
                            
                        else:
                            logger.error(f"GitHub API error: {response.status}")
                            response.raise_for_status()
                            
                except asyncio.TimeoutError:
                    logger.warning(f"GitHub API timeout for page {page}")
                    break
                except Exception as e:
                    logger.error(f"Error fetching GitHub issues: {e}")
                    break
        
        logger.info(f"Fetched {len(issues)} GitHub issues from {owner}/{repo}")
        return issues
    
    async def fetch_discussions(
        self, 
        owner: str, 
        repo: str, 
        since: Optional[datetime] = None
    ) -> List[GitHubIssue]:
        """
        Fetch GitHub discussions for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            since: Only fetch discussions updated since this date
            
        Returns:
            List of GitHubIssue objects (discussions)
        """
        discussions = []
        page = 1
        per_page = 100
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Product-Feedback-Miner/1.0"
            }
        ) as session:
            
            while True:
                await self._check_rate_limit()
                
                url = f"{self.base_url}/repos/{owner}/{repo}/discussions"
                params = {
                    "page": page,
                    "per_page": per_page,
                    "sort": "updated",
                    "direction": "desc"
                }
                
                if since:
                    params["since"] = since.isoformat()
                
                try:
                    async with session.get(url, params=params) as response:
                        self.rate_limit_remaining = int(
                            response.headers.get("X-RateLimit-Remaining", 0)
                        )
                        
                        if response.status == 200:
                            data = await response.json()
                            
                            if not data:
                                break
                            
                            for discussion_data in data:
                                discussion = self._parse_discussion(discussion_data)
                                discussions.append(discussion)
                            
                            page += 1
                            
                        elif response.status == 403:
                            logger.warning("GitHub API rate limit exceeded")
                            await self._wait_for_rate_limit_reset()
                            continue
                            
                        else:
                            logger.error(f"GitHub API error: {response.status}")
                            response.raise_for_status()
                            
                except Exception as e:
                    logger.error(f"Error fetching GitHub discussions: {e}")
                    break
        
        logger.info(f"Fetched {len(discussions)} GitHub discussions from {owner}/{repo}")
        return discussions
    
    def _parse_issue(self, issue_data: Dict[str, Any]) -> GitHubIssue:
        """Parse GitHub issue data into GitHubIssue object."""
        return GitHubIssue(
            id=issue_data["id"],
            number=issue_data["number"],
            title=issue_data["title"],
            body=issue_data["body"] or "",
            author=issue_data["user"]["login"],
            author_url=issue_data["user"]["html_url"],
            url=issue_data["html_url"],
            created_at=datetime.fromisoformat(
                issue_data["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                issue_data["updated_at"].replace("Z", "+00:00")
            ),
            labels=[label["name"] for label in issue_data["labels"]],
            state=issue_data["state"],
            comments_count=issue_data["comments"],
            assignees=[assignee["login"] for assignee in issue_data["assignees"]],
            raw_metadata={
                "milestone": issue_data.get("milestone"),
                "locked": issue_data.get("locked", False),
                "reactions": issue_data.get("reactions", {}),
                "node_id": issue_data.get("node_id")
            }
        )
    
    def _parse_discussion(self, discussion_data: Dict[str, Any]) -> GitHubIssue:
        """Parse GitHub discussion data into GitHubIssue object."""
        return GitHubIssue(
            id=discussion_data["id"],
            number=discussion_data["number"],
            title=discussion_data["title"],
            body=discussion_data["body"] or "",
            author=discussion_data["user"]["login"],
            author_url=discussion_data["user"]["html_url"],
            url=discussion_data["html_url"],
            created_at=datetime.fromisoformat(
                discussion_data["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                discussion_data["updated_at"].replace("Z", "+00:00")
            ),
            labels=[label["name"] for label in discussion_data["labels"]],
            state=discussion_data["state"],
            comments_count=discussion_data["comments"],
            assignees=[],  # Discussions don't have assignees
            raw_metadata={
                "category": discussion_data.get("category"),
                "answer_chosen_at": discussion_data.get("answer_chosen_at"),
                "answer_chosen_by": discussion_data.get("answer_chosen_by"),
                "node_id": discussion_data.get("node_id")
            }
        )
    
    async def _check_rate_limit(self):
        """Check if we're approaching rate limit."""
        if self.rate_limit_remaining < 100:  # Safety margin
            logger.warning("Approaching GitHub API rate limit")
            await self._wait_for_rate_limit_reset()
    
    async def _wait_for_rate_limit_reset(self):
        """Wait for rate limit to reset."""
        if self.rate_limit_reset:
            wait_time = self.rate_limit_reset - datetime.now().timestamp()
            if wait_time > 0:
                logger.info(f"Waiting {wait_time:.0f} seconds for rate limit reset")
                await asyncio.sleep(wait_time)
    
    async def test_connection(self) -> bool:
        """Test GitHub API connection."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Product-Feedback-Miner/1.0"
                }
            ) as session:
                async with session.get(f"{self.base_url}/user") as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"GitHub API connection test failed: {e}")
            return False
