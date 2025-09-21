"""
Tests for the Digestor Agent.

This module contains comprehensive unit and integration tests
for the Digestor Agent and its components.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import uuid

from agents.digestor.agent import DigestorAgent
from agents.digestor.report_models import (
    ReportType, ReportFormat, NotificationChannel, PriorityLevel,
    ReportTemplates, ReportFormatter, DigestorConfig
)
from agents.digestor.analytics import FeedbackAnalytics, TrendData, ComponentAnalysis, ClusterAnalysis
from agents.digestor.notifications import NotificationManager
from agents.base.agent import AgentContext
from database.models import (
    ProcessedDocument, PrioritizationScore, Cluster, Ticket,
    FeedbackType, SourceType, ProcessingStatus, PriorityLevel as DBPriorityLevel,
    TicketStatus
)

class TestDigestorAgent:
    """Test cases for DigestorAgent class."""
    
    @pytest.fixture
    def digestor_agent(self):
        """Create DigestorAgent instance for testing."""
        config = {
            "digestor": {
                "enable_hourly_reports": True,
                "enable_daily_reports": True,
                "enable_weekly_reports": True,
                "enable_monthly_reports": True,
                "enable_notifications": True,
                "enable_trend_analysis": True,
                "default_format": "html",
                "report_retention_days": 30
            },
            "notifications": {
                "email": {
                    "smtp_server": "localhost",
                    "smtp_port": 587,
                    "username": "test@example.com",
                    "password": "test-password",
                    "from_email": "noreply@example.com"
                },
                "slack": {
                    "webhook_url": "https://hooks.slack.com/test",
                    "channel": "#test",
                    "username": "Test Bot"
                }
            },
            "report_storage_dir": tempfile.mkdtemp()
        }
        return DigestorAgent(config)
    
    @pytest.fixture
    def mock_feedback_data(self):
        """Create mock feedback data for testing."""
        return {
            "total_feedback": 100,
            "high_priority_count": 15,
            "tickets_created": 12,
            "resolution_rate": 85.5,
            "critical_count": 3,
            "critical_percentage": 3.0,
            "high_count": 12,
            "high_percentage": 12.0,
            "medium_count": 45,
            "medium_percentage": 45.0,
            "low_count": 40,
            "low_percentage": 40.0
        }
    
    def test_initialization(self, digestor_agent):
        """Test DigestorAgent initialization."""
        assert digestor_agent.name == "digestor"
        assert digestor_agent.digestor_config.enable_hourly_reports is True
        assert digestor_agent.digestor_config.enable_daily_reports is True
        assert digestor_agent.digestor_config.default_format == ReportFormat.HTML
        assert isinstance(digestor_agent.analytics, FeedbackAnalytics)
        assert isinstance(digestor_agent.notification_manager, NotificationManager)
    
    def test_get_input_dependencies(self, digestor_agent):
        """Test input dependencies."""
        dependencies = digestor_agent.get_input_dependencies()
        assert "classifier" in dependencies
        assert "clusterer" in dependencies
        assert "prioritizer" in dependencies
        assert "actioner" in dependencies
    
    def test_determine_report_types(self, digestor_agent):
        """Test report type determination."""
        # Mock current time for testing
        with patch('agents.digestor.agent.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 15, 9, 2)  # Monday 9:02 AM
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            report_types = digestor_agent._determine_report_types()
            
            # Should include daily report (9 AM on Monday)
            assert ReportType.DAILY in report_types
    
    def test_get_report_start_date(self, digestor_agent):
        """Test report start date calculation."""
        end_date = datetime(2024, 1, 15, 12, 0)
        
        # Test hourly
        start_date = digestor_agent._get_report_start_date(ReportType.HOURLY, end_date)
        assert start_date == datetime(2024, 1, 15, 11, 0)
        
        # Test daily
        start_date = digestor_agent._get_report_start_date(ReportType.DAILY, end_date)
        assert start_date == datetime(2024, 1, 14, 12, 0)
        
        # Test weekly
        start_date = digestor_agent._get_report_start_date(ReportType.WEEKLY, end_date)
        assert start_date == datetime(2024, 1, 8, 12, 0)
    
    def test_generate_summary(self, digestor_agent, mock_feedback_data):
        """Test summary generation."""
        # Test executive summary
        summary = digestor_agent._generate_summary(mock_feedback_data, ReportType.EXECUTIVE)
        assert "100 feedback items" in summary
        assert "15 high-priority issues" in summary
        
        # Test technical summary
        summary = digestor_agent._generate_summary(mock_feedback_data, ReportType.TECHNICAL)
        assert "Technical summary" in summary
        
        # Test hourly digest
        summary = digestor_agent._generate_summary(mock_feedback_data, ReportType.HOURLY)
        assert "Hourly digest" in summary
    
    @pytest.mark.asyncio
    async def test_save_report(self, digestor_agent):
        """Test report saving."""
        from agents.digestor.report_models import ReportData
        
        report_data = ReportData(
            title="Test Report",
            summary="Test summary",
            content={
                'formatted_content': '<html><body>Test content</body></html>',
                'raw_data': {},
                'template_used': 'Test Template',
                'format': 'html'
            }
        )
        
        report_path = await digestor_agent._save_report(report_data, ReportType.EXECUTIVE)
        
        assert report_path != ""
        assert os.path.exists(report_path)
        
        # Clean up
        os.remove(report_path)
    
    def test_get_report_recipients(self, digestor_agent):
        """Test report recipient determination."""
        # Test executive recipients
        recipients = digestor_agent._get_report_recipients(ReportType.EXECUTIVE)
        assert "executives@example.com" in recipients
        
        # Test technical recipients
        recipients = digestor_agent._get_report_recipients(ReportType.TECHNICAL)
        assert "dev-team@example.com" in recipients
        
        # Test default recipients
        recipients = digestor_agent._get_report_recipients(ReportType.HOURLY)
        assert "team@example.com" in recipients
    
    def test_format_trend_analysis(self, digestor_agent):
        """Test trend analysis formatting."""
        trends = [
            TrendData("Total Feedback", 100, 80, 25.0, "up", "high", "Feedback volume"),
            TrendData("High Priority", 15, 10, 50.0, "up", "high", "High priority items"),
            TrendData("Resolution Rate", 85, 90, -5.6, "down", "low", "Resolution efficiency")
        ]
        
        formatted = digestor_agent._format_trend_analysis(trends)
        
        assert "Total Feedback increased by 25.0%" in formatted
        assert "High Priority increased by 50.0%" in formatted
        assert "Resolution Rate decreased by 5.6%" in formatted
    
    def test_format_trend_summary(self, digestor_agent):
        """Test trend summary formatting."""
        trends = [
            TrendData("Total Feedback", 100, 80, 25.0, "up", "high", "Feedback volume"),
            TrendData("High Priority", 15, 10, 50.0, "up", "medium", "High priority items")
        ]
        
        summary = digestor_agent._format_trend_summary(trends)
        
        assert "2 significant trend(s) detected" in summary
    
    def test_format_component_breakdown(self, digestor_agent):
        """Test component breakdown formatting."""
        components = [
            ComponentAnalysis("auth", 25, 5, 0.8, None, ["Login issue"], 0.9),
            ComponentAnalysis("payment", 20, 3, 0.7, None, ["Payment error"], 0.8),
            ComponentAnalysis("ui", 15, 2, 0.6, None, ["UI bug"], 0.7)
        ]
        
        formatted = digestor_agent._format_component_breakdown(components)
        
        assert "auth: 25 items (5 high-priority)" in formatted
        assert "payment: 20 items (3 high-priority)" in formatted
        assert "ui: 15 items (2 high-priority)" in formatted

class TestReportModels:
    """Test cases for report models and utilities."""
    
    def test_report_templates(self):
        """Test report template creation."""
        # Test executive summary template
        exec_template = ReportTemplates.get_executive_summary_template()
        assert exec_template.name == "Executive Summary"
        assert exec_template.report_type == ReportType.EXECUTIVE
        assert exec_template.format == ReportFormat.HTML
        assert "total_feedback" in exec_template.variables
        assert "high_priority_count" in exec_template.variables
        
        # Test technical summary template
        tech_template = ReportTemplates.get_technical_summary_template()
        assert tech_template.name == "Technical Summary"
        assert tech_template.report_type == ReportType.TECHNICAL
        assert tech_template.format == ReportFormat.MARKDOWN
        
        # Test hourly digest template
        hourly_template = ReportTemplates.get_hourly_digest_template()
        assert hourly_template.name == "Hourly Digest"
        assert hourly_template.report_type == ReportType.HOURLY
        assert hourly_template.format == ReportFormat.TEXT
    
    def test_report_formatter(self):
        """Test report formatting."""
        template = ReportTemplates.get_executive_summary_template()
        data = {
            'total_feedback': 100,
            'high_priority_count': 15,
            'tickets_created': 12,
            'resolution_rate': 85.5,
            'key_insights': '<li>Test insight</li>',
            'critical_count': 3,
            'critical_percentage': 3.0,
            'high_count': 12,
            'high_percentage': 12.0,
            'medium_count': 45,
            'medium_percentage': 45.0,
            'low_count': 40,
            'low_percentage': 40.0,
            'top_components': '<li>auth: 25 items</li>',
            'trend_analysis': 'Positive trends detected',
            'critical_issues': '<li>Critical bug found</li>',
            'recommendations': '<li>Focus on auth component</li>',
            'start_date': '2024-01-01',
            'end_date': '2024-01-02',
            'generated_at': '2024-01-02 10:00:00 UTC'
        }
        
        formatted = ReportFormatter.format_report(template, data)
        
        assert "<html>" in formatted
        assert "100" in formatted
        assert "15" in formatted
        assert "Test insight" in formatted
    
    def test_notification_templates(self):
        """Test notification template creation."""
        from agents.digestor.report_models import NotificationTemplates
        
        # Test critical alert template
        critical_template = NotificationTemplates.get_critical_alert_template()
        assert "CRITICAL ALERT" in critical_template
        assert "{title}" in critical_template
        assert "{priority}" in critical_template
        
        # Test trend alert template
        trend_template = NotificationTemplates.get_trend_alert_template()
        assert "TREND ALERT" in trend_template
        assert "{trend_type}" in trend_template
        assert "{change_percentage}" in trend_template
        
        # Test daily summary template
        daily_template = NotificationTemplates.get_daily_summary_template()
        assert "Daily Feedback Summary" in daily_template
        assert "{total_feedback}" in daily_template

class TestFeedbackAnalytics:
    """Test cases for FeedbackAnalytics class."""
    
    @pytest.fixture
    def analytics(self):
        """Create FeedbackAnalytics instance for testing."""
        return FeedbackAnalytics()
    
    def test_calculate_trend(self, analytics):
        """Test trend calculation."""
        # Test increasing trend
        trend = analytics._calculate_trend("Test Metric", 100, 80, "Test description")
        assert trend.metric == "Test Metric"
        assert trend.current_value == 100
        assert trend.previous_value == 80
        assert trend.change_percentage == 25.0
        assert trend.trend_direction == "up"
        assert trend.significance == "medium"
        
        # Test decreasing trend
        trend = analytics._calculate_trend("Test Metric", 60, 80, "Test description")
        assert trend.change_percentage == -25.0
        assert trend.trend_direction == "down"
        
        # Test stable trend
        trend = analytics._calculate_trend("Test Metric", 80, 82, "Test description")
        assert abs(trend.change_percentage) < 5
        assert trend.trend_direction == "stable"
        assert trend.significance == "low"
    
    def test_generate_insights(self, analytics):
        """Test insight generation."""
        # Mock trends
        trends = [
            TrendData("High Priority Feedback", 20, 10, 100.0, "up", "high", "High priority items"),
            TrendData("Total Feedback", 100, 80, 25.0, "up", "medium", "Total feedback volume")
        ]
        
        # Mock components
        components = [
            ComponentAnalysis("auth", 25, 15, 0.8, None, ["Login issue"], 0.9),
            ComponentAnalysis("payment", 20, 5, 0.7, None, ["Payment error"], 0.8)
        ]
        
        # Mock cluster analysis
        cluster_analysis = ClusterAnalysis(
            total_clusters=5,
            avg_cluster_size=4.0,
            largest_cluster={'title': 'Auth Issues', 'size': 8},
            top_clusters=[],
            clustering_efficiency=20.0
        )
        
        insights = analytics._generate_recommendations(trends, components, cluster_analysis)
        
        assert len(insights) > 0
        assert any("High priority feedback is increasing" in insight for insight in insights)
        assert any("Focus on auth" in insight for insight in insights)

class TestNotificationManager:
    """Test cases for NotificationManager class."""
    
    @pytest.fixture
    def notification_manager(self):
        """Create NotificationManager instance for testing."""
        config = {
            "email": {
                "smtp_server": "localhost",
                "smtp_port": 587,
                "username": "test@example.com",
                "password": "test-password",
                "from_email": "noreply@example.com"
            },
            "slack": {
                "webhook_url": "https://hooks.slack.com/test",
                "channel": "#test",
                "username": "Test Bot"
            },
            "critical_alert_recipients": ["admin@example.com"],
            "trend_alert_recipients": ["analytics@example.com"],
            "daily_summary_recipients": ["team@example.com"]
        }
        return NotificationManager(config)
    
    def test_initialization(self, notification_manager):
        """Test NotificationManager initialization."""
        assert NotificationChannel.EMAIL in notification_manager.senders
        assert NotificationChannel.SLACK in notification_manager.senders
        assert NotificationChannel.CONSOLE in notification_manager.senders
    
    @pytest.mark.asyncio
    async def test_send_notification(self, notification_manager):
        """Test sending notifications."""
        # Mock the senders
        mock_email_sender = AsyncMock()
        mock_email_sender.send.return_value = True
        
        mock_slack_sender = AsyncMock()
        mock_slack_sender.send.return_value = True
        
        notification_manager.senders[NotificationChannel.EMAIL] = mock_email_sender
        notification_manager.senders[NotificationChannel.SLACK] = mock_slack_sender
        
        # Send notification
        results = await notification_manager.send_notification(
            "Test message",
            [NotificationChannel.EMAIL, NotificationChannel.SLACK],
            ["test@example.com"],
            PriorityLevel.MEDIUM
        )
        
        assert results[NotificationChannel.EMAIL] is True
        assert results[NotificationChannel.SLACK] is True
        
        # Verify senders were called
        mock_email_sender.send.assert_called_once()
        mock_slack_sender.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_critical_alert(self, notification_manager):
        """Test sending critical alert."""
        # Mock the senders
        mock_sender = AsyncMock()
        mock_sender.send.return_value = True
        
        notification_manager.senders = {
            NotificationChannel.EMAIL: mock_sender,
            NotificationChannel.SLACK: mock_sender
        }
        
        # Send critical alert
        results = await notification_manager.send_critical_alert(
            "Critical Bug",
            "System is down",
            "authentication",
            "High",
            ["Restart service", "Check logs"],
            ["Investigate root cause", "Implement fix"]
        )
        
        assert results[NotificationChannel.EMAIL] is True
        assert results[NotificationChannel.SLACK] is True
        
        # Verify critical alert template was used
        mock_sender.send.assert_called()
        call_args = mock_sender.send.call_args
        assert "CRITICAL ALERT" in call_args[0][0]
        assert "Critical Bug" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_send_trend_alert(self, notification_manager):
        """Test sending trend alert."""
        # Mock the senders
        mock_sender = AsyncMock()
        mock_sender.send.return_value = True
        
        notification_manager.senders = {
            NotificationChannel.SLACK: mock_sender,
            NotificationChannel.EMAIL: mock_sender
        }
        
        # Send trend alert
        results = await notification_manager.send_trend_alert(
            "High Priority Feedback",
            20,
            10,
            100.0,
            "High priority feedback has doubled",
            "Investigate the cause immediately"
        )
        
        assert results[NotificationChannel.SLACK] is True
        assert results[NotificationChannel.EMAIL] is True
        
        # Verify trend alert template was used
        mock_sender.send.assert_called()
        call_args = mock_sender.send.call_args
        assert "TREND ALERT" in call_args[0][0]
        assert "High Priority Feedback" in call_args[0][0]
        assert "100.0%" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_send_daily_summary(self, notification_manager):
        """Test sending daily summary."""
        # Mock the senders
        mock_sender = AsyncMock()
        mock_sender.send.return_value = True
        
        notification_manager.senders = {
            NotificationChannel.EMAIL: mock_sender,
            NotificationChannel.SLACK: mock_sender
        }
        
        # Send daily summary
        results = await notification_manager.send_daily_summary(
            "2024-01-15",
            100,
            15,
            12,
            8,
            ["Login issue", "Payment error"],
            ["Critical bug found"]
        )
        
        assert results[NotificationChannel.EMAIL] is True
        assert results[NotificationChannel.SLACK] is True
        
        # Verify daily summary template was used
        mock_sender.send.assert_called()
        call_args = mock_sender.send.call_args
        assert "Daily Feedback Summary" in call_args[0][0]
        assert "2024-01-15" in call_args[0][0]
        assert "100" in call_args[0][0]

class TestDigestorAgentIntegration:
    """Integration tests for Digestor Agent."""
    
    @pytest.fixture
    def digestor_agent(self):
        """Create DigestorAgent instance for integration testing."""
        config = {
            "digestor": {
                "enable_hourly_reports": True,
                "enable_daily_reports": True,
                "enable_notifications": True,
                "enable_trend_analysis": True,
                "default_format": "html"
            },
            "notifications": {
                "email": {
                    "smtp_server": "localhost",
                    "smtp_port": 587,
                    "username": "test@example.com",
                    "password": "test-password",
                    "from_email": "noreply@example.com"
                },
                "slack": {
                    "webhook_url": "https://hooks.slack.com/test",
                    "channel": "#test",
                    "username": "Test Bot"
                }
            },
            "report_storage_dir": tempfile.mkdtemp(),
            "executive_recipients": ["executives@example.com"],
            "technical_recipients": ["dev-team@example.com"],
            "default_recipients": ["team@example.com"]
        }
        return DigestorAgent(config)
    
    @pytest.mark.asyncio
    async def test_generate_executive_report(self, digestor_agent):
        """Test executive report generation."""
        # Mock database queries
        with patch.object(digestor_agent, 'get_db_session') as mock_session:
            # Mock query results
            mock_query = mock_session.return_value.__enter__.return_value.query.return_value
            mock_query.filter.return_value.count.return_value = 100
            mock_query.join.return_value.filter.return_value.count.return_value = 15
            mock_query.filter.return_value.count.return_value = 12
            
            # Mock priority distribution
            with patch.object(digestor_agent, '_get_priority_distribution') as mock_priority:
                mock_priority.return_value = {
                    'critical': 3, 'critical_percentage': 3.0,
                    'high': 12, 'high_percentage': 12.0,
                    'medium': 45, 'medium_percentage': 45.0,
                    'low': 40, 'low_percentage': 40.0
                }
                
                # Mock component analysis
                with patch.object(digestor_agent.analytics, 'analyze_components') as mock_components:
                    mock_components.return_value = [
                        ComponentAnalysis("auth", 25, 5, 0.8, None, ["Login issue"], 0.9)
                    ]
                    
                    # Mock trend analysis
                    with patch.object(digestor_agent.analytics, 'analyze_trends') as mock_trends:
                        mock_trends.return_value = [
                            TrendData("Total Feedback", 100, 80, 25.0, "up", "high", "Feedback volume")
                        ]
                        
                        # Mock critical issues
                        with patch.object(digestor_agent, '_get_critical_issues') as mock_critical:
                            mock_critical.return_value = ["Critical bug found"]
                            
                            # Mock insights
                            with patch.object(digestor_agent.analytics, 'generate_insights') as mock_insights:
                                mock_insights.return_value = ["Focus on auth component"]
                                
                                # Generate report
                                context = AgentContext(
                                    execution_id=str(uuid.uuid4()),
                                    config={},
                                    metadata={}
                                )
                                
                                report_data = await digestor_agent._generate_executive_data(
                                    datetime.utcnow() - timedelta(days=1),
                                    datetime.utcnow()
                                )
                                
                                assert report_data is not None
                                assert 'total_feedback' in report_data
                                assert 'high_priority_count' in report_data
                                assert 'tickets_created' in report_data
    
    @pytest.mark.asyncio
    async def test_generate_hourly_report(self, digestor_agent):
        """Test hourly report generation."""
        # Mock database queries
        with patch.object(digestor_agent, 'get_db_session') as mock_session:
            mock_query = mock_session.return_value.__enter__.return_value.query.return_value
            mock_query.filter.return_value.count.return_value = 10
            mock_query.join.return_value.filter.return_value.count.return_value = 3
            
            # Mock other methods
            with patch.object(digestor_agent, '_get_top_priorities') as mock_priorities:
                mock_priorities.return_value = ["Login issue", "Payment error"]
                
                with patch.object(digestor_agent, '_get_critical_alerts') as mock_alerts:
                    mock_alerts.return_value = ["Critical bug found"]
                    
                    with patch.object(digestor_agent.analytics, 'analyze_trends') as mock_trends:
                        mock_trends.return_value = [
                            TrendData("Total Feedback", 10, 8, 25.0, "up", "high", "Feedback volume")
                        ]
                        
                        with patch.object(digestor_agent.analytics, 'analyze_components') as mock_components:
                            mock_components.return_value = [
                                ComponentAnalysis("auth", 5, 2, 0.8, None, ["Login issue"], 0.9)
                            ]
                            
                            # Generate hourly report
                            context = AgentContext(
                                execution_id=str(uuid.uuid4()),
                                config={},
                                metadata={}
                            )
                            
                            report_data = await digestor_agent._generate_hourly_data(
                                datetime.utcnow() - timedelta(hours=1),
                                datetime.utcnow()
                            )
                            
                            assert report_data is not None
                            assert 'new_feedback_count' in report_data
                            assert 'high_priority_count' in report_data
                            assert 'tickets_created' in report_data
                            assert 'top_priorities' in report_data
    
    @pytest.mark.asyncio
    async def test_send_notifications(self, digestor_agent):
        """Test notification sending."""
        # Mock notification manager
        with patch.object(digestor_agent.notification_manager, 'send_notification') as mock_send:
            mock_send.return_value = {
                NotificationChannel.EMAIL: True,
                NotificationChannel.SLACK: True
            }
            
            # Create mock report data
            from agents.digestor.report_models import ReportData
            report_data = ReportData(
                title="Test Report",
                summary="Test summary",
                content={'formatted_content': '<html>Test</html>'},
                metadata={}
            )
            
            # Send notifications
            results = await digestor_agent._send_report_notifications(
                report_data, ReportType.EXECUTIVE, "/tmp/test.html"
            )
            
            assert results[NotificationChannel.EMAIL] is True
            assert results[NotificationChannel.SLACK] is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_old_reports(self, digestor_agent):
        """Test cleanup of old reports."""
        # Create a temporary report file
        test_file = os.path.join(digestor_agent.report_storage_dir, "test_old_report.html")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        # Mock file creation time to be old
        old_time = datetime.utcnow() - timedelta(days=35)
        os.utime(test_file, (old_time.timestamp(), old_time.timestamp()))
        
        # Run cleanup
        await digestor_agent._cleanup_old_reports()
        
        # File should be removed
        assert not os.path.exists(test_file)
    
    @pytest.mark.asyncio
    async def test_generate_custom_report(self, digestor_agent):
        """Test custom report generation."""
        # Mock the _generate_report method
        with patch.object(digestor_agent, '_generate_report') as mock_generate:
            from agents.digestor.report_models import ReportData
            mock_report = ReportData(
                title="Custom Report",
                summary="Custom summary",
                content={'formatted_content': '<html>Custom</html>'},
                metadata={}
            )
            mock_generate.return_value = mock_report
            
            # Generate custom report
            report = await digestor_agent.generate_custom_report(
                ReportType.EXECUTIVE,
                datetime.utcnow() - timedelta(days=1),
                datetime.utcnow()
            )
            
            assert report is not None
            assert report.title == "Custom Report"
            mock_generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_notifications(self, digestor_agent):
        """Test notification testing."""
        # Mock notification manager test_connections
        with patch.object(digestor_agent.notification_manager, 'test_connections') as mock_test:
            mock_test.return_value = {
                NotificationChannel.EMAIL: True,
                NotificationChannel.SLACK: False
            }
            
            results = await digestor_agent.test_notifications()
            
            assert results[NotificationChannel.EMAIL] is True
            assert results[NotificationChannel.SLACK] is False
            mock_test.assert_called_once()

