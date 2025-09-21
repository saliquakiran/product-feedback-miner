"""
GitHub integration for the Actioner Agent.

This module provides functionality for creating and managing issues
in GitHub from high-priority feedback.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import aiohttp
import json
from urllib.parse import urljoin

from agents.actioner.ticket_models import TicketData, TicketResult, TicketStatus, TicketPriority
from config.api_keys import api_keys

logger = logging.getLogger(__name__)

class GitHubAPIClient:
    """Client for interacting with GitHub API."""
    
    def __init__(self, token: str, owner: str, repo: str):
        """
        Initialize GitHub API client.
        
        Args:
            token: GitHub personal access token
            owner: Repository owner (username or organization)
            repo: Repository name
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base_url = "https://api.github.com"
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Product-Feedback-Miner/1.0'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def create_issue(self, ticket_data: TicketData) -> TicketResult:
        """
        Create an issue in GitHub.
        
        Args:
            ticket_data: Ticket data to create
            
        Returns:
            TicketResult with creation status and details
        """
        try:
            # Prepare GitHub issue payload
            payload = self._prepare_issue_payload(ticket_data)
            
            # Create issue
            url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues"
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 201:
                    result_data = await response.json()
                    
                    return TicketResult(
                        success=True,
                        ticket_id=str(result_data.get('number')),
                        ticket_url=result_data.get('html_url'),
                        platform=ticket_data.platform,
                        created_at=datetime.fromisoformat(result_data.get('created_at').replace('Z', '+00:00')),
                        metadata={
                            'github_id': result_data.get('id'),
                            'github_number': result_data.get('number'),
                            'github_url': result_data.get('html_url'),
                            'github_api_url': result_data.get('url')
                        }
                    )
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create GitHub issue: {response.status} - {error_text}")
                    
                    return TicketResult(
                        success=False,
                        platform=ticket_data.platform,
                        error_message=f"GitHub API error {response.status}: {error_text}"
                    )
        
        except Exception as e:
            logger.error(f"Error creating GitHub issue: {e}")
            return TicketResult(
                success=False,
                platform=ticket_data.platform,
                error_message=str(e)
            )
    
    def _prepare_issue_payload(self, ticket_data: TicketData) -> Dict[str, Any]:
        """Prepare GitHub API payload from ticket data."""
        payload = {
            "title": ticket_data.title,
            "body": ticket_data.description,
            "labels": ticket_data.labels,
            "assignees": [ticket_data.assignee] if ticket_data.assignee else []
        }
        
        # Add milestone if specified in custom fields
        if "milestone" in ticket_data.custom_fields:
            payload["milestone"] = ticket_data.custom_fields["milestone"]
        
        return payload
    
    async def get_issue(self, issue_number: int) -> Optional[Dict[str, Any]]:
        """
        Get issue details from GitHub.
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Issue details or None if not found
        """
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{issue_number}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Issue #{issue_number} not found: {response.status}")
                    return None
        
        except Exception as e:
            logger.error(f"Error getting issue #{issue_number}: {e}")
            return None
    
    async def update_issue_status(self, issue_number: int, status: TicketStatus) -> bool:
        """
        Update issue status in GitHub.
        
        Args:
            issue_number: GitHub issue number
            status: New status (open/closed)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{issue_number}"
            
            # Map status to GitHub state
            state = "closed" if status in [TicketStatus.CLOSED, TicketStatus.RESOLVED] else "open"
            
            payload = {"state": state}
            
            async with self.session.patch(url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Successfully updated issue #{issue_number} to {state}")
                    return True
                else:
                    logger.error(f"Failed to update issue #{issue_number} status: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Error updating issue #{issue_number} status: {e}")
            return False
    
    async def add_comment(self, issue_number: int, comment: str) -> bool:
        """
        Add comment to GitHub issue.
        
        Args:
            issue_number: GitHub issue number
            comment: Comment text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments"
            
            payload = {"body": comment}
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 201:
                    logger.info(f"Successfully added comment to issue #{issue_number}")
                    return True
                else:
                    logger.error(f"Failed to add comment to issue #{issue_number}: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Error adding comment to issue #{issue_number}: {e}")
            return False
    
    async def search_issues(self, query: str, state: str = "all") -> List[Dict[str, Any]]:
        """
        Search issues using GitHub search API.
        
        Args:
            query: Search query
            state: Issue state (open, closed, all)
            
        Returns:
            List of issue details
        """
        try:
            # GitHub search API requires different format
            search_query = f"repo:{self.owner}/{self.repo} {query} state:{state}"
            url = f"{self.base_url}/search/issues"
            
            params = {
                "q": search_query,
                "sort": "created",
                "order": "desc",
                "per_page": 100
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('items', [])
                else:
                    logger.error(f"Failed to search issues: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Error searching issues: {e}")
            return []
    
    async def test_connection(self) -> bool:
        """
        Test connection to GitHub API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            url = f"{self.base_url}/user"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    user_data = await response.json()
                    logger.info(f"Successfully connected to GitHub as {user_data.get('login', 'Unknown')}")
                    return True
                else:
                    logger.error(f"Failed to connect to GitHub: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Error testing GitHub connection: {e}")
            return False

class GitHubIssueManager:
    """High-level manager for GitHub issue operations."""
    
    def __init__(self, token: str, owner: str, repo: str):
        """Initialize GitHub issue manager."""
        self.client = GitHubAPIClient(token, owner, repo)
        self.owner = owner
        self.repo = repo
    
    async def create_issue_from_feedback(
        self, 
        feedback_data: Dict[str, Any],
        priority_data: Dict[str, Any],
        cluster_data: Optional[Dict[str, Any]] = None
    ) -> TicketResult:
        """
        Create a GitHub issue from feedback data.
        
        Args:
            feedback_data: Processed feedback data
            priority_data: Priority scoring data
            cluster_data: Optional cluster data
            
        Returns:
            TicketResult with creation status
        """
        try:
            # Format ticket data
            from agents.actioner.ticket_models import TicketFormatter, TicketTemplates, PlatformType
            
            # Determine template based on feedback type
            feedback_type = feedback_data.get("feedback_type", "bug")
            if feedback_type == "bug":
                template = TicketTemplates.get_bug_template(PlatformType.GITHUB)
            elif feedback_type == "feature_request":
                template = TicketTemplates.get_feature_request_template(PlatformType.GITHUB)
            elif feedback_type == "performance":
                template = TicketTemplates.get_performance_template(PlatformType.GITHUB)
            else:
                template = TicketTemplates.get_bug_template(PlatformType.GITHUB)
            
            # Format ticket data
            ticket_data = TicketFormatter.format_ticket_data(
                feedback_data, priority_data, cluster_data, template
            )
            
            # Create issue
            async with self.client as client:
                return await client.create_issue(ticket_data)
        
        except Exception as e:
            logger.error(f"Error creating GitHub issue from feedback: {e}")
            return TicketResult(
                success=False,
                platform=PlatformType.GITHUB,
                error_message=str(e)
            )
    
    async def get_issue_status(self, issue_number: int) -> Optional[TicketStatus]:
        """
        Get current status of an issue.
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Current issue status or None if not found
        """
        try:
            async with self.client as client:
                issue_data = await client.get_issue(issue_number)
                if issue_data:
                    state = issue_data['state']
                    return TicketStatus.OPEN if state == 'open' else TicketStatus.CLOSED
                return None
        
        except Exception as e:
            logger.error(f"Error getting issue status for #{issue_number}: {e}")
            return None
    
    async def update_issue_status(self, issue_number: int, status: TicketStatus) -> bool:
        """
        Update issue status.
        
        Args:
            issue_number: GitHub issue number
            status: New status
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.client as client:
                return await client.update_issue_status(issue_number, status)
        
        except Exception as e:
            logger.error(f"Error updating issue status for #{issue_number}: {e}")
            return False
    
    async def add_issue_comment(self, issue_number: int, comment: str) -> bool:
        """
        Add comment to issue.
        
        Args:
            issue_number: GitHub issue number
            comment: Comment text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.client as client:
                return await client.add_comment(issue_number, comment)
        
        except Exception as e:
            logger.error(f"Error adding comment to issue #{issue_number}: {e}")
            return False
    
    async def search_feedback_issues(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Search for issues created from feedback in the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of issue details
        """
        try:
            # Create search query for feedback issues
            query = f"label:feedback created:>={datetime.utcnow() - timedelta(days=days):%Y-%m-%d}"
            
            async with self.client as client:
                return await client.search_issues(query)
        
        except Exception as e:
            logger.error(f"Error searching feedback issues: {e}")
            return []
    
    async def get_issue_by_label(self, label: str, state: str = "open") -> List[Dict[str, Any]]:
        """
        Get issues by label.
        
        Args:
            label: Label to search for
            state: Issue state (open, closed, all)
            
        Returns:
            List of issue details
        """
        try:
            query = f"label:{label}"
            
            async with self.client as client:
                return await client.search_issues(query, state)
        
        except Exception as e:
            logger.error(f"Error getting issues by label {label}: {e}")
            return []
    
    async def test_connection(self) -> bool:
        """Test connection to GitHub."""
        try:
            async with self.client as client:
                return await client.test_connection()
        
        except Exception as e:
            logger.error(f"Error testing GitHub connection: {e}")
            return False

