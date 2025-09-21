"""
Actioner Agent for Product Feedback Miner.

This agent creates tickets in Jira/GitHub for high-priority feedback,
manages ticket lifecycle, and provides escalation workflows.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import uuid

from agents.base.agent import BaseAgent, AgentResult, AgentContext
from agents.actioner.ticket_models import (
    TicketData, TicketResult, ActionerConfig, PlatformType,
    TicketTemplates, TicketFormatter, PriorityMapper
)
from agents.actioner.integrations.jira import JiraTicketManager
from agents.actioner.integrations.github import GitHubIssueManager
from database.models import (
    ProcessedDocument, PrioritizationScore, Cluster, 
    Ticket, TicketStatus as DBTicketStatus, PriorityLevel
)
from database import get_session

logger = logging.getLogger(__name__)

class ActionerAgent(BaseAgent):
    """
    Actioner Agent for creating and managing tickets from high-priority feedback.
    
    This agent:
    1. Identifies high-priority feedback items
    2. Creates tickets in Jira/GitHub
    3. Manages ticket lifecycle and status updates
    4. Provides escalation workflows
    5. Tracks resolution outcomes for learning
    """
    
    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        """Initialize Actioner Agent."""
        super().__init__("actioner", config_overrides)
        
        # Load configuration
        self.actioner_config = ActionerConfig(**self.config.get("actioner", {}))
        
        # Initialize platform managers
        self.platform_managers = {}
        self._initialize_platform_managers()
        
        # Rate limiting
        self.tickets_created_this_hour = 0
        self.tickets_created_today = 0
        self.last_hour_reset = datetime.utcnow()
        self.last_day_reset = datetime.utcnow()
    
    def _initialize_platform_managers(self):
        """Initialize platform-specific ticket managers."""
        try:
            # Initialize Jira manager if enabled
            if self.actioner_config.enable_jira:
                jira_config = self.config.get("jira", {})
                if jira_config.get("base_url") and jira_config.get("username") and jira_config.get("api_token"):
                    self.platform_managers[PlatformType.JIRA] = JiraTicketManager(
                        base_url=jira_config["base_url"],
                        username=jira_config["username"],
                        api_token=jira_config["api_token"]
                    )
                    logger.info("Jira ticket manager initialized")
                else:
                    logger.warning("Jira configuration incomplete, skipping Jira integration")
            
            # Initialize GitHub manager if enabled
            if self.actioner_config.enable_github:
                github_config = self.config.get("github", {})
                if github_config.get("token") and github_config.get("owner") and github_config.get("repo"):
                    self.platform_managers[PlatformType.GITHUB] = GitHubIssueManager(
                        token=github_config["token"],
                        owner=github_config["owner"],
                        repo=github_config["repo"]
                    )
                    logger.info("GitHub issue manager initialized")
                else:
                    logger.warning("GitHub configuration incomplete, skipping GitHub integration")
            
            if not self.platform_managers:
                logger.warning("No platform managers initialized - no tickets will be created")
        
        except Exception as e:
            logger.error(f"Error initializing platform managers: {e}")
    
    def get_input_dependencies(self) -> List[str]:
        """Get list of agent dependencies."""
        return ["classifier", "clusterer", "prioritizer"]
    
    async def process(self, context: AgentContext) -> AgentResult:
        """
        Main processing method for creating tickets from high-priority feedback.
        
        Args:
            context: Agent context with execution metadata
            
        Returns:
            AgentResult with processing statistics
        """
        start_time = datetime.utcnow()
        items_processed = 0
        items_successful = 0
        items_failed = 0
        error_messages = []
        
        try:
            self.logger.info("Starting Actioner Agent processing")
            
            # Reset rate limiting if needed
            self._reset_rate_limits()
            
            # Get high-priority feedback items
            high_priority_items = await self._get_high_priority_items()
            
            if not high_priority_items:
                self.logger.info("No high-priority items found for ticket creation")
                return AgentResult(
                    success=True,
                    items_processed=0,
                    items_successful=0,
                    items_failed=0,
                    execution_time=(datetime.utcnow() - start_time).total_seconds(),
                    metadata={"message": "No high-priority items found"}
                )
            
            self.logger.info(f"Found {len(high_priority_items)} high-priority items")
            
            # Process each high-priority item
            for item in high_priority_items:
                try:
                    items_processed += 1
                    
                    # Check rate limits
                    if not self._check_rate_limits():
                        self.logger.warning("Rate limit reached, stopping ticket creation")
                        break
                    
                    # Create ticket for this item
                    ticket_result = await self._create_ticket_for_item(item)
                    
                    if ticket_result.success:
                        items_successful += 1
                        self.tickets_created_this_hour += 1
                        self.tickets_created_today += 1
                        
                        # Store ticket record in database
                        await self._store_ticket_record(item, ticket_result)
                        
                        self.logger.info(f"Successfully created ticket {ticket_result.ticket_id} for item {item['document_id']}")
                    else:
                        items_failed += 1
                        error_messages.append(f"Failed to create ticket for item {item['document_id']}: {ticket_result.error_message}")
                        self.logger.error(f"Failed to create ticket for item {item['document_id']}: {ticket_result.error_message}")
                
                except Exception as e:
                    items_failed += 1
                    error_message = f"Error processing item {item.get('document_id', 'unknown')}: {str(e)}"
                    error_messages.append(error_message)
                    self.logger.error(error_message)
            
            # Update execution statistics
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.info(
                f"Actioner Agent completed: {items_successful}/{items_processed} tickets created successfully"
            )
            
            return AgentResult(
                success=items_failed == 0,
                items_processed=items_processed,
                items_successful=items_successful,
                items_failed=items_failed,
                execution_time=execution_time,
                error_message="; ".join(error_messages) if error_messages else None,
                metadata={
                    "tickets_created_this_hour": self.tickets_created_this_hour,
                    "tickets_created_today": self.tickets_created_today,
                    "rate_limit_reached": not self._check_rate_limits(),
                    "platforms_used": list(self.platform_managers.keys())
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error in Actioner Agent processing: {e}")
            return AgentResult(
                success=False,
                items_processed=items_processed,
                items_successful=items_successful,
                items_failed=items_failed,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                error_message=str(e)
            )
    
    async def _get_high_priority_items(self) -> List[Dict[str, Any]]:
        """Get high-priority feedback items that need tickets created."""
        try:
            with self.get_db_session() as session:
                # Query for high-priority items without existing tickets
                query = session.query(
                    ProcessedDocument,
                    PrioritizationScore,
                    Cluster
                ).join(
                    PrioritizationScore, ProcessedDocument.id == PrioritizationScore.document_id
                ).outerjoin(
                    Cluster, ProcessedDocument.cluster_id == Cluster.id
                ).outerjoin(
                    Ticket, ProcessedDocument.id == Ticket.document_id
                ).filter(
                    PrioritizationScore.priority_score >= self.actioner_config.priority_threshold,
                    Ticket.id.is_(None)  # No existing ticket
                ).order_by(
                    PrioritizationScore.priority_score.desc()
                ).limit(
                    self.actioner_config.max_tickets_per_day
                )
                
                items = []
                for doc, priority, cluster in query.all():
                    item = {
                        "document_id": str(doc.id),
                        "document": doc,
                        "priority": priority,
                        "cluster": cluster,
                        "feedback_data": {
                            "id": str(doc.id),
                            "title": doc.title,
                            "body": doc.content,
                            "feedback_type": doc.feedback_type.value if doc.feedback_type else "bug",
                            "component": doc.component,
                            "severity": doc.severity_score,
                            "author": doc.author,
                            "url": doc.source_url,
                            "timestamp": doc.created_at.isoformat() if doc.created_at else "",
                            "language": doc.language,
                            "source": doc.source_type.value if doc.source_type else "unknown"
                        },
                        "priority_data": {
                            "overall_score": priority.priority_score,
                            "severity_score": priority.severity_score,
                            "reach_score": priority.reach_score,
                            "recency_score": priority.recency_score,
                            "persona_score": priority.persona_weight,
                            "priority_level": priority.priority_level,
                            "is_revenue_critical": priority.is_revenue_critical,
                            "reasoning": self._generate_priority_reasoning(priority)
                        },
                        "cluster_data": {
                            "id": str(cluster.id) if cluster else None,
                            "title": cluster.title if cluster else None,
                            "size": cluster.member_count if cluster else 1,
                            "avg_severity": cluster.avg_severity if cluster else None
                        } if cluster else None
                    }
                    items.append(item)
                
                return items
        
        except Exception as e:
            self.logger.error(f"Error getting high-priority items: {e}")
            return []
    
    def _generate_priority_reasoning(self, priority: PrioritizationScore) -> List[str]:
        """Generate human-readable priority reasoning."""
        reasoning = []
        
        if priority.severity_score >= 0.8:
            reasoning.append("High severity impact")
        elif priority.severity_score >= 0.6:
            reasoning.append("Medium severity impact")
        
        if priority.reach_score >= 0.8:
            reasoning.append("Affects many users")
        elif priority.reach_score >= 0.6:
            reasoning.append("Moderate user impact")
        
        if priority.recency_score >= 0.8:
            reasoning.append("Recent feedback")
        
        if priority.persona_weight >= 0.8:
            reasoning.append("High-value user segment")
        
        if priority.is_revenue_critical:
            reasoning.append("Revenue-critical issue")
        
        if priority.revenue_impact_multiplier > 1.0:
            reasoning.append(f"Revenue impact: {priority.revenue_impact_multiplier:.1f}x")
        
        return reasoning
    
    async def _create_ticket_for_item(self, item: Dict[str, Any]) -> TicketResult:
        """Create a ticket for a high-priority item."""
        try:
            # Determine which platform to use
            platform = self._select_platform(item)
            
            if platform not in self.platform_managers:
                return TicketResult(
                    success=False,
                    platform=platform,
                    error_message=f"Platform {platform.value} not configured"
                )
            
            # Create ticket using the appropriate manager
            manager = self.platform_managers[platform]
            return await manager.create_issue_from_feedback(
                item["feedback_data"],
                item["priority_data"],
                item["cluster_data"]
            )
        
        except Exception as e:
            self.logger.error(f"Error creating ticket for item: {e}")
            return TicketResult(
                success=False,
                platform=PlatformType.JIRA,  # Default
                error_message=str(e)
            )
    
    def _select_platform(self, item: Dict[str, Any]) -> PlatformType:
        """Select the appropriate platform for ticket creation."""
        # Simple selection logic - can be enhanced with more sophisticated rules
        if PlatformType.JIRA in self.platform_managers and PlatformType.GITHUB in self.platform_managers:
            # Use Jira for high-priority items, GitHub for others
            if item["priority_data"]["overall_score"] >= 0.9:
                return PlatformType.JIRA
            else:
                return PlatformType.GITHUB
        elif PlatformType.JIRA in self.platform_managers:
            return PlatformType.JIRA
        elif PlatformType.GITHUB in self.platform_managers:
            return PlatformType.GITHUB
        else:
            raise ValueError("No platform managers available")
    
    async def _store_ticket_record(self, item: Dict[str, Any], ticket_result: TicketResult):
        """Store ticket record in the database."""
        try:
            with self.get_db_session() as session:
                # Create ticket record
                ticket = Ticket(
                    id=uuid.uuid4(),
                    source_document_id=item["document_id"],
                    platform=ticket_result.platform.value,
                    external_id=ticket_result.ticket_id,
                    external_url=ticket_result.ticket_url,
                    status=DBTicketStatus.OPEN,
                    priority=item["priority_data"]["priority_level"],
                    title=item["feedback_data"]["title"],
                    description=item["feedback_data"]["body"],
                    created_at=datetime.utcnow()
                )
                
                session.add(ticket)
                session.commit()
                
                self.logger.info(f"Stored ticket record for {ticket_result.ticket_id}")
        
        except Exception as e:
            self.logger.error(f"Error storing ticket record: {e}")
    
    def _check_rate_limits(self) -> bool:
        """Check if rate limits allow creating more tickets."""
        return (
            self.tickets_created_this_hour < self.actioner_config.max_tickets_per_hour and
            self.tickets_created_today < self.actioner_config.max_tickets_per_day
        )
    
    def _reset_rate_limits(self):
        """Reset rate limiting counters if needed."""
        now = datetime.utcnow()
        
        # Reset hourly counter
        if now - self.last_hour_reset >= timedelta(hours=1):
            self.tickets_created_this_hour = 0
            self.last_hour_reset = now
        
        # Reset daily counter
        if now - self.last_day_reset >= timedelta(days=1):
            self.tickets_created_today = 0
            self.last_day_reset = now
    
    async def test_platform_connections(self) -> Dict[str, bool]:
        """Test connections to all configured platforms."""
        results = {}
        
        for platform, manager in self.platform_managers.items():
            try:
                if hasattr(manager, 'test_connection'):
                    results[platform.value] = await manager.test_connection()
                else:
                    results[platform.value] = False
            except Exception as e:
                self.logger.error(f"Error testing {platform.value} connection: {e}")
                results[platform.value] = False
        
        return results
    
    async def get_ticket_statistics(self) -> Dict[str, Any]:
        """Get statistics about created tickets."""
        try:
            with self.get_db_session() as session:
                # Count tickets by platform
                platform_counts = {}
                for platform in PlatformType:
                    count = session.query(Ticket).filter(
                        Ticket.platform == platform.value
                    ).count()
                    platform_counts[platform.value] = count
                
                # Count tickets by status
                status_counts = {}
                for status in DBTicketStatus:
                    count = session.query(Ticket).filter(
                        Ticket.status == status
                    ).count()
                    status_counts[status.value] = count
                
                # Count tickets by priority
                priority_counts = {}
                for priority in PriorityLevel:
                    count = session.query(Ticket).filter(
                        Ticket.priority == priority.value
                    ).count()
                    priority_counts[priority.value] = count
                
                return {
                    "total_tickets": sum(platform_counts.values()),
                    "platform_breakdown": platform_counts,
                    "status_breakdown": status_counts,
                    "priority_breakdown": priority_counts,
                    "tickets_created_this_hour": self.tickets_created_this_hour,
                    "tickets_created_today": self.tickets_created_today,
                    "rate_limit_status": {
                        "hourly_remaining": max(0, self.actioner_config.max_tickets_per_hour - self.tickets_created_this_hour),
                        "daily_remaining": max(0, self.actioner_config.max_tickets_per_day - self.tickets_created_today)
                    }
                }
        
        except Exception as e:
            self.logger.error(f"Error getting ticket statistics: {e}")
            return {}
    
    async def update_ticket_status(self, ticket_id: str, status: str, platform: str) -> bool:
        """Update ticket status in the external platform."""
        try:
            platform_enum = PlatformType(platform)
            if platform_enum not in self.platform_managers:
                self.logger.error(f"Platform {platform} not configured")
                return False
            
            manager = self.platform_managers[platform_enum]
            
            # Map string status to enum
            from agents.actioner.ticket_models import TicketStatus
            status_enum = TicketStatus(status)
            
            # Update in external platform
            success = await manager.update_issue_status(ticket_id, status_enum)
            
            if success:
                # Update in database
                with self.get_db_session() as session:
                    ticket = session.query(Ticket).filter(
                        Ticket.external_id == ticket_id,
                        Ticket.platform == platform
                    ).first()
                    
                    if ticket:
                        ticket.status = DBTicketStatus(status)
                        session.commit()
                        self.logger.info(f"Updated ticket {ticket_id} status to {status}")
                        return True
                    else:
                        self.logger.warning(f"Ticket {ticket_id} not found in database")
                        return False
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error updating ticket status: {e}")
            return False
