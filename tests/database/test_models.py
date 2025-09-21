#!/usr/bin/env python3
"""
Tests for database models.

This module tests all database models including:
- RawFeedback, ProcessedDocument, Cluster, ClusterMembership
- PrioritizationScore, Ticket, FeedbackLoopData, AgentExecution
- SystemConfig, DigestReport
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.models import (
    Base, RawFeedback, ProcessedDocument, Cluster, ClusterMembership,
    PrioritizationScore, Ticket, FeedbackLoopData, AgentExecution,
    SystemConfig, DigestReport, FeedbackType, PriorityLevel, SourceType,
    ProcessingStatus, TicketStatus
)

class TestRawFeedback:
    """Tests for RawFeedback model."""
    
    def test_raw_feedback_creation(self, test_session):
        """Test RawFeedback model creation and validation."""
        feedback = RawFeedback(
            source_type=SourceType.GITHUB_ISSUE,
            source_id="12345",
            url="https://github.com/user/repo/issues/123",
            title="Test Issue",
            content="This is a test issue",
            author="testuser",
            timestamp=datetime.utcnow(),
            raw_metadata={"labels": ["bug"], "assignee": "dev"}
        )
        
        test_session.add(feedback)
        test_session.commit()
        
        assert feedback.id is not None
        assert feedback.source_type == SourceType.GITHUB_ISSUE
        assert feedback.raw_metadata == {"labels": ["bug"], "assignee": "dev"}
        assert feedback.title == "Test Issue"
        assert feedback.author == "testuser"
    
    def test_raw_feedback_required_fields(self, test_session):
        """Test that required fields are properly validated."""
        # Test with minimal required fields
        feedback = RawFeedback(
            source_type=SourceType.GITHUB_ISSUE,
            source_id="12345",
            url="https://github.com/user/repo/issues/123",
            content="Test content",
            timestamp=datetime.utcnow()
        )
        
        test_session.add(feedback)
        test_session.commit()
        
        assert feedback.id is not None
        assert feedback.source_type == SourceType.GITHUB_ISSUE
        assert feedback.source_id == "12345"

class TestProcessedDocument:
    """Tests for ProcessedDocument model."""
    
    def test_processed_document_creation(self, test_session):
        """Test ProcessedDocument model creation."""
        # Create parent RawFeedback
        raw_feedback = RawFeedback(
            source_type=SourceType.GITHUB_ISSUE,
            source_id="12345",
            url="https://github.com/user/repo/issues/123",
            content="Test content",
            timestamp=datetime.utcnow()
        )
        test_session.add(raw_feedback)
        test_session.commit()
        
        # Create ProcessedDocument
        processed_doc = ProcessedDocument(
            raw_feedback_id=raw_feedback.id,
            title="Processed Test Issue",
            body="This is processed test content",
            author="testuser",
            timestamp=datetime.utcnow(),
            url="https://github.com/user/repo/issues/123",
            language="en",
            word_count=10
        )
        
        test_session.add(processed_doc)
        test_session.commit()
        
        assert processed_doc.id is not None
        assert processed_doc.raw_feedback_id == raw_feedback.id
        assert processed_doc.title == "Processed Test Issue"
        assert processed_doc.word_count == 10

class TestCluster:
    """Tests for Cluster model."""
    
    def test_cluster_creation(self, test_session):
        """Test Cluster model creation."""
        cluster = Cluster(
            name="Login Issues",
            description="Issues related to user login",
            centroid_embedding=[0.1, 0.2, 0.3],  # Mock embedding
            size=5,
            quality_score=0.85
        )
        
        test_session.add(cluster)
        test_session.commit()
        
        assert cluster.id is not None
        assert cluster.name == "Login Issues"
        assert cluster.size == 5
        assert cluster.quality_score == 0.85

class TestClusterMembership:
    """Tests for ClusterMembership model."""
    
    def test_cluster_membership_creation(self, test_session):
        """Test ClusterMembership model creation."""
        # Create test data
        raw_feedback = RawFeedback(
            source_type=SourceType.GITHUB_ISSUE,
            source_id="12345",
            url="https://github.com/user/repo/issues/123",
            content="Test content",
            timestamp=datetime.utcnow()
        )
        test_session.add(raw_feedback)
        test_session.commit()
        
        processed_doc = ProcessedDocument(
            raw_feedback_id=raw_feedback.id,
            title="Test Issue",
            body="Test content",
            author="testuser",
            timestamp=datetime.utcnow(),
            url="https://github.com/user/repo/issues/123"
        )
        test_session.add(processed_doc)
        test_session.commit()
        
        cluster = Cluster(
            name="Test Cluster",
            description="Test cluster",
            centroid_embedding=[0.1, 0.2, 0.3],
            size=1
        )
        test_session.add(cluster)
        test_session.commit()
        
        # Create membership
        membership = ClusterMembership(
            cluster_id=cluster.id,
            processed_document_id=processed_doc.id,
            similarity_score=0.95
        )
        
        test_session.add(membership)
        test_session.commit()
        
        assert membership.id is not None
        assert membership.cluster_id == cluster.id
        assert membership.processed_document_id == processed_doc.id
        assert membership.similarity_score == 0.95

class TestPrioritizationScore:
    """Tests for PrioritizationScore model."""
    
    def test_prioritization_score_creation(self, test_session):
        """Test PrioritizationScore model creation."""
        # Create test data
        raw_feedback = RawFeedback(
            source_type=SourceType.GITHUB_ISSUE,
            source_id="12345",
            url="https://github.com/user/repo/issues/123",
            content="Test content",
            timestamp=datetime.utcnow()
        )
        test_session.add(raw_feedback)
        test_session.commit()
        
        processed_doc = ProcessedDocument(
            raw_feedback_id=raw_feedback.id,
            title="Test Issue",
            body="Test content",
            author="testuser",
            timestamp=datetime.utcnow(),
            url="https://github.com/user/repo/issues/123"
        )
        test_session.add(processed_doc)
        test_session.commit()
        
        # Create prioritization score
        score = PrioritizationScore(
            processed_document_id=processed_doc.id,
            overall_score=0.85,
            severity_score=0.9,
            reach_score=0.8,
            recency_score=0.7,
            persona_weight=0.6,
            priority_level=PriorityLevel.HIGH,
            revenue_impact=0.75
        )
        
        test_session.add(score)
        test_session.commit()
        
        assert score.id is not None
        assert score.processed_document_id == processed_doc.id
        assert score.overall_score == 0.85
        assert score.priority_level == PriorityLevel.HIGH

class TestTicket:
    """Tests for Ticket model."""
    
    def test_ticket_creation(self, test_session):
        """Test Ticket model creation."""
        # Create test data
        raw_feedback = RawFeedback(
            source_type=SourceType.GITHUB_ISSUE,
            source_id="12345",
            url="https://github.com/user/repo/issues/123",
            content="Test content",
            timestamp=datetime.utcnow()
        )
        test_session.add(raw_feedback)
        test_session.commit()
        
        processed_doc = ProcessedDocument(
            raw_feedback_id=raw_feedback.id,
            title="Test Issue",
            body="Test content",
            author="testuser",
            timestamp=datetime.utcnow(),
            url="https://github.com/user/repo/issues/123"
        )
        test_session.add(processed_doc)
        test_session.commit()
        
        # Create ticket
        ticket = Ticket(
            processed_document_id=processed_doc.id,
            external_id="TICKET-123",
            external_url="https://jira.example.com/browse/TICKET-123",
            title="Fix login issue",
            description="Users cannot login with Google OAuth",
            status=TicketStatus.OPEN,
            priority=PriorityLevel.HIGH,
            assignee="dev-team"
        )
        
        test_session.add(ticket)
        test_session.commit()
        
        assert ticket.id is not None
        assert ticket.processed_document_id == processed_doc.id
        assert ticket.external_id == "TICKET-123"
        assert ticket.status == TicketStatus.OPEN

class TestAgentExecution:
    """Tests for AgentExecution model."""
    
    def test_agent_execution_creation(self, test_session):
        """Test AgentExecution model creation."""
        execution = AgentExecution(
            agent_name="test_agent",
            execution_id="exec_123",
            status="running",
            started_at=datetime.utcnow()
        )
        
        test_session.add(execution)
        test_session.commit()
        
        assert execution.id is not None
        assert execution.agent_name == "test_agent"
        assert execution.execution_id == "exec_123"
        assert execution.status == "running"

class TestSystemConfig:
    """Tests for SystemConfig model."""
    
    def test_system_config_creation(self, test_session):
        """Test SystemConfig model creation."""
        config = SystemConfig(
            key="test_setting",
            value="test_value",
            description="Test configuration setting"
        )
        
        test_session.add(config)
        test_session.commit()
        
        assert config.id is not None
        assert config.key == "test_setting"
        assert config.value == "test_value"

class TestDigestReport:
    """Tests for DigestReport model."""
    
    def test_digest_report_creation(self, test_session):
        """Test DigestReport model creation."""
        report = DigestReport(
            report_type="hourly",
            title="Hourly Feedback Summary",
            content="Summary of feedback received in the last hour",
            generated_at=datetime.utcnow(),
            metadata={"item_count": 10, "priority_items": 2}
        )
        
        test_session.add(report)
        test_session.commit()
        
        assert report.id is not None
        assert report.report_type == "hourly"
        assert report.title == "Hourly Feedback Summary"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
