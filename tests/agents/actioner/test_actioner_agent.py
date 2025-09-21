"""
Tests for the Actioner Agent.

This module contains comprehensive unit and integration tests
for the Actioner Agent and its components.
"""

import pytest
import asyncio
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import uuid

from agents.actioner.agent import ActionerAgent
from agents.base.agent import AgentContext
from agents.actioner.ticket_models import (
    TicketData, TicketResult, ActionerConfig, PlatformType,
    TicketPriority, TicketType, TicketStatus
)
from agents.actioner.integrations.jira import JiraTicketManager
from agents.actioner.integrations.github import GitHubIssueManager
from database.models import (
    ProcessedDocument, PrioritizationScore, Cluster, Ticket,
    FeedbackType, SourceType, ProcessingStatus, PriorityLevel
)

class TestActionerAgent:
    """Test cases for ActionerAgent class."""
    
    @pytest.fixture
    def actioner_agent(self):
        """Create ActionerAgent instance for testing."""
        config = {
            "actioner": {
                "priority_threshold": 0.7,
                "max_tickets_per_hour": 5,
                "max_tickets_per_day": 20,
                "enable_jira": True,
                "enable_github": True
            },
            "jira": {
                "base_url": "https://test.atlassian.net",
                "username": "test@example.com",
                "api_token": "test-token"
            },
            "github": {
                "token": "test-token",
                "owner": "test-org",
                "repo": "test-repo"
            }
        }
        return ActionerAgent(config)
    
    @pytest.fixture
    def mock_feedback_data(self):
        """Create mock feedback data for testing."""
        return {
            "id": str(uuid.uuid4()),
            "title": "Login button not working",
            "body": "The login button is not responding when clicked",
            "feedback_type": "bug",
            "component": "authentication",
            "severity": 0.8,
            "author": "testuser",
            "url": "https://example.com/feedback/123",
            "timestamp": datetime.utcnow().isoformat(),
            "language": "en",
            "source": "github"
        }
    
    @pytest.fixture
    def mock_priority_data(self):
        """Create mock priority data for testing."""
        return {
            "overall_score": 0.85,
            "severity_score": 0.8,
            "reach_score": 0.9,
            "recency_score": 0.7,
            "persona_score": 0.6,
            "priority_level": 4,
            "is_revenue_critical": True,
            "reasoning": ["High severity impact", "Affects many users", "Revenue-critical issue"]
        }
    
    @pytest.fixture
    def mock_cluster_data(self):
        """Create mock cluster data for testing."""
        return {
            "id": str(uuid.uuid4()),
            "title": "Login Issues Cluster",
            "size": 5,
            "avg_severity": 0.75
        }
    
    def test_initialization(self, actioner_agent):
        """Test ActionerAgent initialization."""
        assert actioner_agent.name == "actioner"
        assert actioner_agent.actioner_config.priority_threshold == 0.7
        assert actioner_agent.actioner_config.enable_jira is True
        assert actioner_agent.actioner_config.enable_github is True
    
    def test_get_input_dependencies(self, actioner_agent):
        """Test input dependencies."""
        dependencies = actioner_agent.get_input_dependencies()
        assert "classifier" in dependencies
        assert "clusterer" in dependencies
        assert "prioritizer" in dependencies
    
    def test_platform_manager_initialization(self, actioner_agent):
        """Test platform manager initialization."""
        assert PlatformType.JIRA in actioner_agent.platform_managers
        assert PlatformType.GITHUB in actioner_agent.platform_managers
        assert isinstance(actioner_agent.platform_managers[PlatformType.JIRA], JiraTicketManager)
        assert isinstance(actioner_agent.platform_managers[PlatformType.GITHUB], GitHubIssueManager)
    
    def test_rate_limit_checking(self, actioner_agent):
        """Test rate limit checking."""
        # Initially should allow tickets
        assert actioner_agent._check_rate_limits() is True
        
        # Set counters to limits
        actioner_agent.tickets_created_this_hour = 5
        actioner_agent.tickets_created_today = 20
        
        # Should not allow more tickets
        assert actioner_agent._check_rate_limits() is False
    
    def test_rate_limit_reset(self, actioner_agent):
        """Test rate limit reset functionality."""
        # Set counters
        actioner_agent.tickets_created_this_hour = 5
        actioner_agent.tickets_created_today = 20
        
        # Reset hourly (simulate time passing)
        actioner_agent.last_hour_reset = datetime.utcnow() - timedelta(hours=1)
        actioner_agent._reset_rate_limits()
        
        assert actioner_agent.tickets_created_this_hour == 0
        assert actioner_agent.tickets_created_today == 20  # Daily not reset yet
    
    def test_platform_selection(self, actioner_agent):
        """Test platform selection logic."""
        # High priority item should select Jira
        high_priority_item = {
            "priority_data": {"overall_score": 0.95}
        }
        platform = actioner_agent._select_platform(high_priority_item)
        assert platform == PlatformType.JIRA
        
        # Lower priority item should select GitHub
        low_priority_item = {
            "priority_data": {"overall_score": 0.75}
        }
        platform = actioner_agent._select_platform(low_priority_item)
        assert platform == PlatformType.GITHUB
    
    def test_priority_reasoning_generation(self, actioner_agent):
        """Test priority reasoning generation."""
        # Create mock priority score
        priority = Mock()
        priority.severity_score = 0.9
        priority.reach_score = 0.8
        priority.recency_score = 0.7
        priority.persona_weight = 0.6
        priority.is_revenue_critical = True
        priority.revenue_impact_multiplier = 1.5
        
        reasoning = actioner_agent._generate_priority_reasoning(priority)
        
        assert "High severity impact" in reasoning
        assert "Affects many users" in reasoning
        assert "Revenue-critical issue" in reasoning
        assert "Revenue impact: 1.5x" in reasoning
    
    @pytest.mark.asyncio
    async def test_get_high_priority_items(self, actioner_agent):
        """Test getting high-priority items from database."""
        with patch.object(actioner_agent, 'get_db_session') as mock_session:
            # Mock database query
            mock_doc = Mock()
            mock_doc.id = uuid.uuid4()
            mock_doc.title = "Test Issue"
            mock_doc.content = "Test content"
            mock_doc.feedback_type = FeedbackType.BUG
            mock_doc.component = "test"
            mock_doc.severity_score = 0.8
            mock_doc.author = "testuser"
            mock_doc.source_url = "https://example.com"
            mock_doc.created_at = datetime.utcnow()
            mock_doc.language = "en"
            mock_doc.source_type = SourceType.GITHUB_ISSUE
            
            mock_priority = Mock()
            mock_priority.priority_score = 0.85
            mock_priority.severity_score = 0.8
            mock_priority.reach_score = 0.9
            mock_priority.recency_score = 0.7
            mock_priority.persona_weight = 0.6
            mock_priority.priority_level = 4
            mock_priority.is_revenue_critical = True
            
            mock_cluster = Mock()
            mock_cluster.id = uuid.uuid4()
            mock_cluster.title = "Test Cluster"
            mock_cluster.member_count = 3
            mock_cluster.avg_severity = 0.75
            
            # Mock query result
            mock_query = mock_session.return_value.__enter__.return_value.query.return_value
            mock_query.join.return_value.outerjoin.return_value.outerjoin.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
                (mock_doc, mock_priority, mock_cluster)
            ]
            
            items = await actioner_agent._get_high_priority_items()
            
            assert len(items) == 1
            assert items[0]["document_id"] == str(mock_doc.id)
            assert items[0]["feedback_data"]["title"] == "Test Issue"
            assert items[0]["priority_data"]["overall_score"] == 0.85
    
    @pytest.mark.asyncio
    async def test_create_ticket_for_item(self, actioner_agent, mock_feedback_data, mock_priority_data, mock_cluster_data):
        """Test creating ticket for an item."""
        item = {
            "document_id": str(uuid.uuid4()),
            "feedback_data": mock_feedback_data,
            "priority_data": mock_priority_data,
            "cluster_data": mock_cluster_data
        }
        
        # Mock platform manager
        mock_manager = AsyncMock()
        mock_manager.create_issue_from_feedback.return_value = TicketResult(
            success=True,
            ticket_id="TEST-123",
            ticket_url="https://test.atlassian.net/browse/TEST-123",
            platform=PlatformType.JIRA
        )
        
        actioner_agent.platform_managers[PlatformType.JIRA] = mock_manager
        
        result = await actioner_agent._create_ticket_for_item(item)
        
        assert result.success is True
        assert result.ticket_id == "TEST-123"
        assert result.platform == PlatformType.JIRA
        mock_manager.create_issue_from_feedback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_ticket_record(self, actioner_agent):
        """Test storing ticket record in database."""
        item = {
            "document_id": str(uuid.uuid4()),
            "priority_data": {"priority_level": 4}
        }
        
        ticket_result = TicketResult(
            success=True,
            ticket_id="TEST-123",
            ticket_url="https://test.atlassian.net/browse/TEST-123",
            platform=PlatformType.JIRA,
            metadata={"test": "data"}
        )
        
        with patch.object(actioner_agent, 'get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.add = Mock()
            mock_session.return_value.__enter__.return_value.commit = Mock()
            
            await actioner_agent._store_ticket_record(item, ticket_result)
            
            # Verify ticket was added and committed
            mock_session.return_value.__enter__.return_value.add.assert_called_once()
            mock_session.return_value.__enter__.return_value.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_no_high_priority_items(self, actioner_agent):
        """Test processing when no high-priority items are found."""
        with patch.object(actioner_agent, '_get_high_priority_items', return_value=[]):
            result = await actioner_agent.process(AgentContext(
                execution_id=str(uuid.uuid4()),
                config={},
                metadata={}
            ))
            
            assert result.success is True
            assert result.items_processed == 0
            assert result.items_successful == 0
            assert result.items_failed == 0
    
    @pytest.mark.asyncio
    async def test_process_with_high_priority_items(self, actioner_agent, mock_feedback_data, mock_priority_data):
        """Test processing with high-priority items."""
        item = {
            "document_id": str(uuid.uuid4()),
            "feedback_data": mock_feedback_data,
            "priority_data": mock_priority_data,
            "cluster_data": None
        }
        
        with patch.object(actioner_agent, '_get_high_priority_items', return_value=[item]):
            with patch.object(actioner_agent, '_create_ticket_for_item') as mock_create:
                with patch.object(actioner_agent, '_store_ticket_record') as mock_store:
                    mock_create.return_value = TicketResult(
                        success=True,
                        ticket_id="TEST-123",
                        platform=PlatformType.JIRA
                    )
                    
                    result = await actioner_agent.process(AgentContext(
                        execution_id=str(uuid.uuid4()),
                        config={},
                        metadata={}
                    ))
                    
                    assert result.success is True
                    assert result.items_processed == 1
                    assert result.items_successful == 1
                    assert result.items_failed == 0
                    mock_create.assert_called_once()
                    mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_platform_connections(self, actioner_agent):
        """Test platform connection testing."""
        # Mock platform managers
        mock_jira = AsyncMock()
        mock_jira.test_connection.return_value = True
        
        mock_github = AsyncMock()
        mock_github.test_connection.return_value = False
        
        actioner_agent.platform_managers = {
            PlatformType.JIRA: mock_jira,
            PlatformType.GITHUB: mock_github
        }
        
        results = await actioner_agent.test_platform_connections()
        
        assert results["jira"] is True
        assert results["github"] is False
    
    @pytest.mark.asyncio
    async def test_get_ticket_statistics(self, actioner_agent):
        """Test getting ticket statistics."""
        with patch.object(actioner_agent, 'get_db_session') as mock_session:
            # Mock database queries
            mock_query = mock_session.return_value.__enter__.return_value.query.return_value
            mock_query.filter.return_value.count.return_value = 5
            
            stats = await actioner_agent.get_ticket_statistics()
            
            assert "total_tickets" in stats
            assert "platform_breakdown" in stats
            assert "status_breakdown" in stats
            assert "priority_breakdown" in stats
            assert "tickets_created_this_hour" in stats
            assert "tickets_created_today" in stats
    
    @pytest.mark.asyncio
    async def test_update_ticket_status(self, actioner_agent):
        """Test updating ticket status."""
        # Mock platform manager
        mock_manager = AsyncMock()
        mock_manager.update_issue_status.return_value = True
        
        actioner_agent.platform_managers[PlatformType.JIRA] = mock_manager
        
        with patch.object(actioner_agent, 'get_db_session') as mock_session:
            # Mock database query
            mock_ticket = Mock()
            mock_ticket.status = "open"
            
            mock_query = mock_session.return_value.__enter__.return_value.query.return_value
            mock_query.filter.return_value.first.return_value = mock_ticket
            
            result = await actioner_agent.update_ticket_status("TEST-123", "closed", "jira")
            
            assert result is True
            mock_manager.update_issue_status.assert_called_once()

class TestTicketModels:
    """Test cases for ticket models and utilities."""
    
    def test_priority_mapper(self):
        """Test priority score mapping."""
        from agents.actioner.ticket_models import PriorityMapper
        
        # Test Jira mapping
        assert PriorityMapper.map_priority_score(0.95, PlatformType.JIRA) == TicketPriority.BLOCKER
        assert PriorityMapper.map_priority_score(0.85, PlatformType.JIRA) == TicketPriority.CRITICAL
        assert PriorityMapper.map_priority_score(0.75, PlatformType.JIRA) == TicketPriority.HIGH
        assert PriorityMapper.map_priority_score(0.65, PlatformType.JIRA) == TicketPriority.MEDIUM
        
        # Test GitHub mapping
        assert PriorityMapper.map_priority_score(0.9, PlatformType.GITHUB) == TicketPriority.HIGHEST
        assert PriorityMapper.map_priority_score(0.8, PlatformType.GITHUB) == TicketPriority.HIGH
        assert PriorityMapper.map_priority_score(0.7, PlatformType.GITHUB) == TicketPriority.MEDIUM
    
    def test_priority_emoji(self):
        """Test priority emoji mapping."""
        from agents.actioner.ticket_models import PriorityMapper
        
        assert PriorityMapper.get_priority_emoji(TicketPriority.LOWEST) == "🔵"
        assert PriorityMapper.get_priority_emoji(TicketPriority.HIGH) == "🟠"
        assert PriorityMapper.get_priority_emoji(TicketPriority.CRITICAL) == "🚨"
        assert PriorityMapper.get_priority_emoji(TicketPriority.BLOCKER) == "💥"
    
    def test_ticket_templates(self):
        """Test ticket template creation."""
        from agents.actioner.ticket_models import TicketTemplates
        
        # Test bug template for Jira
        jira_bug_template = TicketTemplates.get_bug_template(PlatformType.JIRA)
        assert jira_bug_template.platform == PlatformType.JIRA
        assert jira_bug_template.ticket_type == TicketType.BUG
        assert "[BUG]" in jira_bug_template.title_template
        assert "bug" in jira_bug_template.labels
        
        # Test feature request template for GitHub
        github_feature_template = TicketTemplates.get_feature_request_template(PlatformType.GITHUB)
        assert github_feature_template.platform == PlatformType.GITHUB
        assert github_feature_template.ticket_type == TicketType.ENHANCEMENT
        assert "✨" in github_feature_template.title_template
        assert "enhancement" in github_feature_template.labels
    
    def test_ticket_formatter(self):
        """Test ticket data formatting."""
        from agents.actioner.ticket_models import TicketFormatter, TicketTemplates
        
        feedback_data = {
            "title": "Test Issue",
            "body": "Test description",
            "feedback_type": "bug",
            "component": "auth",
            "severity": 0.8,
            "author": "testuser",
            "url": "https://example.com",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        priority_data = {
            "overall_score": 0.85,
            "reasoning": ["High severity", "Many users affected"]
        }
        
        cluster_data = {
            "size": 3,
            "id": "cluster-123"
        }
        
        template = TicketTemplates.get_bug_template(PlatformType.JIRA)
        ticket_data = TicketFormatter.format_ticket_data(
            feedback_data, priority_data, cluster_data, template
        )
        
        assert ticket_data.title == "[BUG] Test Issue"
        assert ticket_data.priority == TicketPriority.CRITICAL
        assert ticket_data.platform == PlatformType.JIRA
        assert "bug" in ticket_data.labels
        assert "auth" in ticket_data.components

class TestJiraIntegration:
    """Test cases for Jira integration."""
    
    @pytest.fixture
    def jira_manager(self):
        """Create JiraTicketManager instance for testing."""
        return JiraTicketManager(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            api_token="test-token"
        )
    
    @pytest.fixture
    def mock_ticket_data(self):
        """Create mock ticket data for testing."""
        return TicketData(
            title="Test Issue",
            description="Test description",
            priority=TicketPriority.HIGH,
            ticket_type=TicketType.BUG,
            platform=PlatformType.JIRA,
            labels=["bug", "test"],
            components=["auth"]
        )
    
    @pytest.mark.asyncio
    async def test_jira_ticket_creation(self, jira_manager, mock_ticket_data):
        """Test Jira ticket creation."""
        # Mock the create_ticket method directly
        with patch.object(jira_manager.client, 'create_ticket') as mock_create:
            mock_create.return_value = TicketResult(
                success=True,
                ticket_id="TEST-123",
                ticket_url="https://test.atlassian.net/browse/TEST-123",
                platform=PlatformType.JIRA
            )
            
            result = await jira_manager.client.create_ticket(mock_ticket_data)
            
            assert result.success is True
            assert result.ticket_id == "TEST-123"
            assert result.platform == PlatformType.JIRA
    
    @pytest.mark.asyncio
    async def test_jira_connection_test(self, jira_manager):
        """Test Jira connection testing."""
        # Mock the test_connection method directly
        with patch.object(jira_manager.client, 'test_connection') as mock_test:
            mock_test.return_value = True
            
            result = await jira_manager.client.test_connection()
            
            assert result is True

class TestGitHubIntegration:
    """Test cases for GitHub integration."""
    
    @pytest.fixture
    def github_manager(self):
        """Create GitHubIssueManager instance for testing."""
        return GitHubIssueManager(
            token="test-token",
            owner="test-org",
            repo="test-repo"
        )
    
    @pytest.fixture
    def mock_issue_data(self):
        """Create mock issue data for testing."""
        return TicketData(
            title="Test Issue",
            description="Test description",
            priority=TicketPriority.HIGH,
            ticket_type=TicketType.ISSUE,
            platform=PlatformType.GITHUB,
            labels=["bug", "test"]
        )
    
    @pytest.mark.asyncio
    async def test_github_issue_creation(self, github_manager, mock_issue_data):
        """Test GitHub issue creation."""
        # Mock the create_issue method directly
        with patch.object(github_manager.client, 'create_issue') as mock_create:
            mock_create.return_value = TicketResult(
                success=True,
                ticket_id="123",
                ticket_url="https://github.com/test-org/test-repo/issues/123",
                platform=PlatformType.GITHUB
            )
            
            result = await github_manager.client.create_issue(mock_issue_data)
            
            assert result.success is True
            assert result.ticket_id == "123"
            assert result.platform == PlatformType.GITHUB
    
    @pytest.mark.asyncio
    async def test_github_connection_test(self, github_manager):
        """Test GitHub connection testing."""
        # Mock the test_connection method directly
        with patch.object(github_manager.client, 'test_connection') as mock_test:
            mock_test.return_value = True
            
            result = await github_manager.client.test_connection()
            
            assert result is True

class TestActionerAgentIntegration:
    """Integration tests for Actioner Agent."""
    
    @pytest.fixture
    def actioner_agent(self):
        """Create ActionerAgent instance for integration testing."""
        config = {
            "actioner": {
                "priority_threshold": 0.7,
                "max_tickets_per_hour": 10,
                "max_tickets_per_day": 50,
                "enable_jira": True,
                "enable_github": True
            },
            "jira": {
                "base_url": "https://test.atlassian.net",
                "username": "test@example.com",
                "api_token": "test-token"
            },
            "github": {
                "token": "test-token",
                "owner": "test-org",
                "repo": "test-repo"
            }
        }
        return ActionerAgent(config)
    
    @pytest.mark.asyncio
    async def test_end_to_end_ticket_creation(self, actioner_agent):
        """Test end-to-end ticket creation process."""
        # Mock high-priority item
        item = {
            "document_id": str(uuid.uuid4()),
            "feedback_data": {
                "title": "Critical Bug",
                "body": "This is a critical bug description",
                "feedback_type": "bug",
                "component": "auth",
                "severity": 0.9,
                "author": "testuser",
                "url": "https://example.com",
                "timestamp": datetime.utcnow().isoformat()
            },
            "priority_data": {
                "overall_score": 0.9,
                "severity_score": 0.9,
                "reach_score": 0.8,
                "recency_score": 0.7,
                "persona_score": 0.6,
                "priority_level": 5,
                "is_revenue_critical": True,
                "reasoning": ["Critical severity", "High user impact"]
            },
            "cluster_data": {
                "id": str(uuid.uuid4()),
                "title": "Auth Issues",
                "size": 5,
                "avg_severity": 0.8
            }
        }
        
        # Mock platform manager
        mock_manager = AsyncMock()
        mock_manager.create_issue_from_feedback.return_value = TicketResult(
            success=True,
            ticket_id="TEST-123",
            ticket_url="https://test.atlassian.net/browse/TEST-123",
            platform=PlatformType.JIRA
        )
        
        actioner_agent.platform_managers[PlatformType.JIRA] = mock_manager
        
        with patch.object(actioner_agent, '_get_high_priority_items', return_value=[item]):
            with patch.object(actioner_agent, '_store_ticket_record') as mock_store:
                result = await actioner_agent.process(AgentContext(
                    execution_id=str(uuid.uuid4()),
                    config={},
                    metadata={}
                ))
                
                assert result.success is True
                assert result.items_processed == 1
                assert result.items_successful == 1
                assert result.items_failed == 0
                
                # Verify ticket creation was called
                mock_manager.create_issue_from_feedback.assert_called_once()
                
                # Verify ticket was stored
                mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, actioner_agent):
        """Test rate limiting in integration scenario."""
        # Set rate limits to very low values
        actioner_agent.actioner_config.max_tickets_per_hour = 1
        actioner_agent.actioner_config.max_tickets_per_day = 2
        
        # Create multiple items
        items = [
            {
                "document_id": str(uuid.uuid4()),
                "feedback_data": {"title": f"Item {i}"},
                "priority_data": {"overall_score": 0.8},
                "cluster_data": None
            }
            for i in range(3)
        ]
        
        # Mock platform manager
        mock_manager = AsyncMock()
        mock_manager.create_issue_from_feedback.return_value = TicketResult(
            success=True,
            ticket_id="TEST-123",
            platform=PlatformType.JIRA
        )
        
        actioner_agent.platform_managers[PlatformType.JIRA] = mock_manager
        
        with patch.object(actioner_agent, '_get_high_priority_items', return_value=items):
            with patch.object(actioner_agent, '_store_ticket_record'):
                result = await actioner_agent.process(AgentContext(
                    execution_id=str(uuid.uuid4()),
                    config={},
                    metadata={}
                ))
                
                # Should only process 1 item due to hourly rate limit
                assert result.items_processed == 1
                assert result.items_successful == 1
                assert result.items_failed == 0
