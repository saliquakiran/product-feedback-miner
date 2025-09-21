"""
Jira integration for the Actioner Agent.

This module provides functionality for creating and managing tickets
in Jira from high-priority feedback.
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

class JiraAPIClient:
    """Client for interacting with Jira API."""
    
    def __init__(self, base_url: str, username: str, api_token: str):
        """
        Initialize Jira API client.
        
        Args:
            base_url: Jira instance URL (e.g., https://company.atlassian.net)
            username: Jira username or email
            api_token: Jira API token
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.username, self.api_token),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def create_ticket(self, ticket_data: TicketData) -> TicketResult:
        """
        Create a ticket in Jira.
        
        Args:
            ticket_data: Ticket data to create
            
        Returns:
            TicketResult with creation status and details
        """
        try:
            # Prepare Jira ticket payload
            payload = self._prepare_ticket_payload(ticket_data)
            
            # Create ticket
            url = urljoin(self.base_url, '/rest/api/3/issue')
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 201:
                    result_data = await response.json()
                    
                    return TicketResult(
                        success=True,
                        ticket_id=result_data.get('key'),
                        ticket_url=f"{self.base_url}/browse/{result_data.get('key')}",
                        platform=ticket_data.platform,
                        created_at=datetime.utcnow(),
                        metadata={
                            'jira_id': result_data.get('id'),
                            'jira_key': result_data.get('key'),
                            'jira_url': f"{self.base_url}/browse/{result_data.get('key')}"
                        }
                    )
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create Jira ticket: {response.status} - {error_text}")
                    
                    return TicketResult(
                        success=False,
                        platform=ticket_data.platform,
                        error_message=f"Jira API error {response.status}: {error_text}"
                    )
        
        except Exception as e:
            logger.error(f"Error creating Jira ticket: {e}")
            return TicketResult(
                success=False,
                platform=ticket_data.platform,
                error_message=str(e)
            )
    
    def _prepare_ticket_payload(self, ticket_data: TicketData) -> Dict[str, Any]:
        """Prepare Jira API payload from ticket data."""
        # Map priority to Jira priority
        priority_map = {
            TicketPriority.LOWEST: "Lowest",
            TicketPriority.LOW: "Low", 
            TicketPriority.MEDIUM: "Medium",
            TicketPriority.HIGH: "High",
            TicketPriority.HIGHEST: "Highest",
            TicketPriority.CRITICAL: "Critical",
            TicketPriority.BLOCKER: "Blocker"
        }
        
        # Map ticket type to Jira issue type
        issue_type_map = {
            "bug": "Bug",
            "task": "Task",
            "story": "Story",
            "epic": "Epic",
            "subtask": "Sub-task",
            "issue": "Bug",
            "enhancement": "Story"
        }
        
        payload = {
            "fields": {
                "project": {
                    "key": "FEED"  # Default project key, should be configurable
                },
                "summary": ticket_data.title,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": ticket_data.description
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {
                    "name": issue_type_map.get(ticket_data.ticket_type.value, "Bug")
                },
                "priority": {
                    "name": priority_map.get(ticket_data.priority, "Medium")
                },
                "labels": ticket_data.labels
            }
        }
        
        # Add components if specified
        if ticket_data.components:
            payload["fields"]["components"] = [
                {"name": comp} for comp in ticket_data.components
            ]
        
        # Add assignee if specified
        if ticket_data.assignee:
            payload["fields"]["assignee"] = {
                "name": ticket_data.assignee
            }
        
        # Add reporter if specified
        if ticket_data.reporter:
            payload["fields"]["reporter"] = {
                "name": ticket_data.reporter
            }
        
        # Add due date if specified
        if ticket_data.due_date:
            payload["fields"]["duedate"] = ticket_data.due_date.strftime("%Y-%m-%d")
        
        # Add custom fields
        for field_id, value in ticket_data.custom_fields.items():
            if field_id in payload["fields"]:
                payload["fields"][field_id] = value
            else:
                # For custom fields, we need the field ID from Jira
                payload["fields"][f"customfield_{field_id}"] = value
        
        return payload
    
    async def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Get ticket details from Jira.
        
        Args:
            ticket_id: Jira ticket key (e.g., FEED-123)
            
        Returns:
            Ticket details or None if not found
        """
        try:
            url = urljoin(self.base_url, f'/rest/api/3/issue/{ticket_id}')
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Ticket {ticket_id} not found: {response.status}")
                    return None
        
        except Exception as e:
            logger.error(f"Error getting ticket {ticket_id}: {e}")
            return None
    
    async def update_ticket_status(self, ticket_id: str, status: TicketStatus) -> bool:
        """
        Update ticket status in Jira.
        
        Args:
            ticket_id: Jira ticket key
            status: New status
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get available transitions
            transitions_url = urljoin(self.base_url, f'/rest/api/3/issue/{ticket_id}/transitions')
            
            async with self.session.get(transitions_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to get transitions for {ticket_id}")
                    return False
                
                transitions_data = await response.json()
                
                # Find transition for the desired status
                target_transition = None
                for transition in transitions_data.get('transitions', []):
                    if transition['name'].lower() == status.value.replace('_', ' '):
                        target_transition = transition
                        break
                
                if not target_transition:
                    logger.warning(f"No transition found for status {status.value}")
                    return False
                
                # Execute transition
                transition_url = urljoin(self.base_url, f'/rest/api/3/issue/{ticket_id}/transitions')
                transition_payload = {
                    "transition": {
                        "id": target_transition['id']
                    }
                }
                
                async with self.session.post(transition_url, json=transition_payload) as transition_response:
                    if transition_response.status == 204:
                        logger.info(f"Successfully updated ticket {ticket_id} to {status.value}")
                        return True
                    else:
                        logger.error(f"Failed to update ticket {ticket_id} status: {transition_response.status}")
                        return False
        
        except Exception as e:
            logger.error(f"Error updating ticket {ticket_id} status: {e}")
            return False
    
    async def add_comment(self, ticket_id: str, comment: str) -> bool:
        """
        Add comment to Jira ticket.
        
        Args:
            ticket_id: Jira ticket key
            comment: Comment text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = urljoin(self.base_url, f'/rest/api/3/issue/{ticket_id}/comment')
            
            payload = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": comment
                                }
                            ]
                        }
                    ]
                }
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 201:
                    logger.info(f"Successfully added comment to ticket {ticket_id}")
                    return True
                else:
                    logger.error(f"Failed to add comment to ticket {ticket_id}: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Error adding comment to ticket {ticket_id}: {e}")
            return False
    
    async def search_tickets(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Search tickets using JQL.
        
        Args:
            jql: Jira Query Language query
            max_results: Maximum number of results
            
        Returns:
            List of ticket details
        """
        try:
            url = urljoin(self.base_url, '/rest/api/3/search')
            
            payload = {
                "jql": jql,
                "maxResults": max_results,
                "fields": ["key", "summary", "status", "priority", "assignee", "created", "updated"]
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('issues', [])
                else:
                    logger.error(f"Failed to search tickets: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Error searching tickets: {e}")
            return []
    
    async def test_connection(self) -> bool:
        """
        Test connection to Jira API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            url = urljoin(self.base_url, '/rest/api/3/myself')
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    user_data = await response.json()
                    logger.info(f"Successfully connected to Jira as {user_data.get('displayName', 'Unknown')}")
                    return True
                else:
                    logger.error(f"Failed to connect to Jira: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Error testing Jira connection: {e}")
            return False

class JiraTicketManager:
    """High-level manager for Jira ticket operations."""
    
    def __init__(self, base_url: str, username: str, api_token: str):
        """Initialize Jira ticket manager."""
        self.client = JiraAPIClient(base_url, username, api_token)
        self.base_url = base_url
        self.username = username
    
    async def create_ticket_from_feedback(
        self, 
        feedback_data: Dict[str, Any],
        priority_data: Dict[str, Any],
        cluster_data: Optional[Dict[str, Any]] = None
    ) -> TicketResult:
        """
        Create a Jira ticket from feedback data.
        
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
                template = TicketTemplates.get_bug_template(PlatformType.JIRA)
            elif feedback_type == "feature_request":
                template = TicketTemplates.get_feature_request_template(PlatformType.JIRA)
            elif feedback_type == "performance":
                template = TicketTemplates.get_performance_template(PlatformType.JIRA)
            else:
                template = TicketTemplates.get_bug_template(PlatformType.JIRA)
            
            # Format ticket data
            ticket_data = TicketFormatter.format_ticket_data(
                feedback_data, priority_data, cluster_data, template
            )
            
            # Create ticket
            async with self.client as client:
                return await client.create_ticket(ticket_data)
        
        except Exception as e:
            logger.error(f"Error creating Jira ticket from feedback: {e}")
            return TicketResult(
                success=False,
                platform=PlatformType.JIRA,
                error_message=str(e)
            )
    
    async def get_ticket_status(self, ticket_id: str) -> Optional[TicketStatus]:
        """
        Get current status of a ticket.
        
        Args:
            ticket_id: Jira ticket key
            
        Returns:
            Current ticket status or None if not found
        """
        try:
            async with self.client as client:
                ticket_data = await client.get_ticket(ticket_id)
                if ticket_data:
                    status_name = ticket_data['fields']['status']['name'].lower().replace(' ', '_')
                    return TicketStatus(status_name)
                return None
        
        except Exception as e:
            logger.error(f"Error getting ticket status for {ticket_id}: {e}")
            return None
    
    async def update_ticket_status(self, ticket_id: str, status: TicketStatus) -> bool:
        """
        Update ticket status.
        
        Args:
            ticket_id: Jira ticket key
            status: New status
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.client as client:
                return await client.update_ticket_status(ticket_id, status)
        
        except Exception as e:
            logger.error(f"Error updating ticket status for {ticket_id}: {e}")
            return False
    
    async def add_ticket_comment(self, ticket_id: str, comment: str) -> bool:
        """
        Add comment to ticket.
        
        Args:
            ticket_id: Jira ticket key
            comment: Comment text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.client as client:
                return await client.add_comment(ticket_id, comment)
        
        except Exception as e:
            logger.error(f"Error adding comment to ticket {ticket_id}: {e}")
            return False
    
    async def search_feedback_tickets(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Search for tickets created from feedback in the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of ticket details
        """
        try:
            # Create JQL query for feedback tickets
            jql = f"labels = 'feedback' AND created >= -{days}d ORDER BY created DESC"
            
            async with self.client as client:
                return await client.search_tickets(jql)
        
        except Exception as e:
            logger.error(f"Error searching feedback tickets: {e}")
            return []
    
    async def test_connection(self) -> bool:
        """Test connection to Jira."""
        try:
            async with self.client as client:
                return await client.test_connection()
        
        except Exception as e:
            logger.error(f"Error testing Jira connection: {e}")
            return False

