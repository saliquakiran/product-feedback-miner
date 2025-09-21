"""
Tests for the Prioritizer Agent and related components.

This module contains unit tests and integration tests for the Prioritizer Agent,
scoring algorithms, business rules, and priority calculations.
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import uuid
import tempfile
import os
from pathlib import Path

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.prioritizer.agent import PrioritizerAgent
from agents.prioritizer.scoring import (
    ScoringWeights, BusinessRules, PriorityScore, PriorityLevel, UserSegment,
    SeverityScorer, ReachScorer, RecencyScorer, PersonaScorer,
    ClusterAmplifier, UrgencyDetector, BusinessRuleEngine, PriorityCalculator
)
from agents.base.agent import AgentContext, AgentResult
from database.models import ProcessedDocument, Cluster, ClusterMembership, PrioritizationScore, RawFeedback, SourceType, ProcessingStatus, FeedbackType
from config.settings import config

class TestScoringWeights:
    """Tests for ScoringWeights class."""
    
    def test_weights_initialization(self):
        """Test weights initialization."""
        weights = ScoringWeights()
        assert weights.severity == 0.35
        assert weights.reach == 0.25
        assert weights.recency == 0.20
        assert weights.persona == 0.20
    
    def test_weights_normalization(self):
        """Test weights normalization."""
        weights = ScoringWeights(severity=0.5, reach=0.3, recency=0.2, persona=0.1)
        weights.normalize()
        
        total = weights.severity + weights.reach + weights.recency + weights.persona
        assert abs(total - 1.0) < 1e-10
    
    def test_weights_custom_values(self):
        """Test weights with custom values."""
        weights = ScoringWeights(severity=0.4, reach=0.3, recency=0.2, persona=0.1)
        assert weights.severity == 0.4
        assert weights.reach == 0.3
        assert weights.recency == 0.2
        assert weights.persona == 0.1

class TestBusinessRules:
    """Tests for BusinessRules class."""
    
    def test_rules_initialization(self):
        """Test business rules initialization."""
        rules = BusinessRules()
        assert rules.cluster_amplification_factor == 0.1
        assert rules.urgency_boost_factor == 1.2
        assert rules.revenue_critical_boost == 1.15
        assert rules.max_priority_score == 1.0
        assert "authentication" in rules.revenue_critical_components
    
    def test_rules_custom_values(self):
        """Test business rules with custom values."""
        rules = BusinessRules(
            cluster_amplification_factor=0.2,
            urgency_boost_factor=1.5,
            revenue_critical_components=["custom1", "custom2"]
        )
        assert rules.cluster_amplification_factor == 0.2
        assert rules.urgency_boost_factor == 1.5
        assert rules.revenue_critical_components == ["custom1", "custom2"]

class TestSeverityScorer:
    """Tests for SeverityScorer class."""
    
    def test_severity_scores(self):
        """Test severity score calculation."""
        assert SeverityScorer.score("critical") == 1.0
        assert SeverityScorer.score("high") == 0.8
        assert SeverityScorer.score("medium") == 0.6
        assert SeverityScorer.score("low") == 0.4
        assert SeverityScorer.score("minimal") == 0.2
        assert SeverityScorer.score("unknown") == 0.2
    
    def test_severity_boost(self):
        """Test severity boost calculation."""
        # Security issues get higher priority
        assert SeverityScorer.get_severity_boost("bug", "security") == 1.2
        
        # Bug reports get higher priority than feature requests
        assert SeverityScorer.get_severity_boost("bug", "ui") == 1.1
        assert SeverityScorer.get_severity_boost("feature_request", "ui") == 0.9
        
        # Default boost
        assert SeverityScorer.get_severity_boost("other", "ui") == 1.0

class TestReachScorer:
    """Tests for ReachScorer class."""
    
    def test_reach_score_user_count(self):
        """Test reach score based on user count."""
        # Single user
        assert ReachScorer.score(1, "individual", "ui") == 0.1
        
        # Multiple users
        assert ReachScorer.score(50, "individual", "ui") == 0.5
        assert ReachScorer.score(100, "individual", "ui") == 0.7
        assert ReachScorer.score(500, "individual", "ui") == 0.8
        assert ReachScorer.score(1000, "individual", "ui") == 0.9
    
    def test_reach_score_user_segment(self):
        """Test reach score based on user segment."""
        # Enterprise users get higher multiplier
        enterprise_score = ReachScorer.score(10, "enterprise", "ui")
        individual_score = ReachScorer.score(10, "individual", "ui")
        assert enterprise_score > individual_score
    
    def test_reach_score_component(self):
        """Test reach score based on component."""
        # Critical components get higher multiplier
        critical_score = ReachScorer.score(10, "individual", "authentication")
        normal_score = ReachScorer.score(10, "individual", "ui")
        assert critical_score > normal_score

class TestRecencyScorer:
    """Test RecencyScorer class."""
    
    def test_recency_score_recent(self):
        """Test recency score for recent feedback."""
        recent_time = datetime.utcnow() - timedelta(hours=1)
        # Recent feedback should get high score (0.9 for 1 hour old)
        assert RecencyScorer.score(recent_time) == 0.9
    
    def test_recency_score_old(self):
        """Test recency score for old feedback."""
        old_time = datetime.utcnow() - timedelta(days=30)
        assert RecencyScorer.score(old_time) == 0.1
    
    def test_recency_score_decay(self):
        """Test recency score decay over time."""
        times = [
            datetime.utcnow() - timedelta(hours=1),
            datetime.utcnow() - timedelta(hours=24),
            datetime.utcnow() - timedelta(hours=72),
            datetime.utcnow() - timedelta(days=7),
            datetime.utcnow() - timedelta(days=30)
        ]
        
        scores = [RecencyScorer.score(t) for t in times]
        
        # Scores should be decreasing
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]
    
    def test_trend_boost(self):
        """Test trend boost calculation."""
        # No trend data
        assert RecencyScorer.get_trend_boost(None) == 1.0
        
        # Increasing frequency trend
        trend_data = {"frequency_trend": 0.8}
        assert RecencyScorer.get_trend_boost(trend_data) == 1.2
        
        # Moderate trend
        trend_data = {"frequency_trend": 0.3}
        assert RecencyScorer.get_trend_boost(trend_data) == 1.1
        
        # No trend
        trend_data = {"frequency_trend": 0.1}
        assert RecencyScorer.get_trend_boost(trend_data) == 1.0

class TestPersonaScorer:
    """Tests for PersonaScorer class."""
    
    def test_persona_score_segments(self):
        """Test persona score for different user segments."""
        assert PersonaScorer.score("enterprise") == 0.9
        assert PersonaScorer.score("professional") == 0.7
        assert PersonaScorer.score("individual") == 0.5
        assert PersonaScorer.score("trial") == 0.3
        assert PersonaScorer.score("unknown") == 0.4
    
    def test_persona_score_user_value(self):
        """Test persona score with user value."""
        # High-value customer
        high_value_score = PersonaScorer.score("individual", user_value=15000)
        normal_score = PersonaScorer.score("individual", user_value=100)
        assert high_value_score > normal_score
    
    def test_persona_score_feedback_quality(self):
        """Test persona score with feedback quality."""
        # High-quality feedback
        high_quality_score = PersonaScorer.score("individual", feedback_quality="high")
        low_quality_score = PersonaScorer.score("individual", feedback_quality="low")
        assert high_quality_score > low_quality_score

class TestClusterAmplifier:
    """Tests for ClusterAmplifier class."""
    
    def test_amplification_small_cluster(self):
        """Test amplification for small clusters."""
        # Below minimum size
        assert ClusterAmplifier.calculate_amplification(1) == 1.0
        assert ClusterAmplifier.calculate_amplification(2, min_size=3) == 1.0
    
    def test_amplification_large_cluster(self):
        """Test amplification for large clusters."""
        # Large cluster
        amplification = ClusterAmplifier.calculate_amplification(10)
        assert amplification > 1.0
        assert amplification == 1.9  # 1 + (10-1) * 0.1
    
    def test_amplification_with_quality(self):
        """Test amplification with cluster quality."""
        # High-quality cluster
        high_quality = ClusterAmplifier.calculate_amplification(5, cluster_quality=0.9)
        low_quality = ClusterAmplifier.calculate_amplification(5, cluster_quality=0.3)
        assert high_quality > low_quality
    
    def test_cluster_quality_calculation(self):
        """Test cluster quality calculation."""
        cluster_data = {
            "avg_similarity": 0.8,
            "temporal_coherence": 0.7,
            "user_diversity": 0.6
        }
        quality = ClusterAmplifier.get_cluster_quality(cluster_data)
        assert 0 <= quality <= 1
        assert abs(quality - 0.7) < 1e-10  # Average of the three factors

class TestUrgencyDetector:
    """Tests for UrgencyDetector class."""
    
    def test_urgency_detection_keywords(self):
        """Test urgency detection with keywords."""
        title = "Critical bug in login system"
        body = "This is urgent and blocking all users"
        
        is_urgent, indicators = UrgencyDetector.detect_urgency(title, body)
        assert is_urgent is True
        assert "critical" in indicators
        assert "urgent" in indicators
        assert "blocking" in indicators
    
    def test_urgency_detection_no_urgency(self):
        """Test urgency detection without urgency indicators."""
        title = "Feature request for new button"
        body = "It would be nice to have a new button"
        
        is_urgent, indicators = UrgencyDetector.detect_urgency(title, body)
        assert is_urgent is False
        assert len(indicators) == 0
    
    def test_urgency_boost_calculation(self):
        """Test urgency boost calculation."""
        # No indicators
        assert UrgencyDetector.get_urgency_boost([]) == 1.0
        
        # Single indicator
        boost1 = UrgencyDetector.get_urgency_boost(["urgent"])
        assert boost1 > 1.0
        
        # Multiple indicators
        boost2 = UrgencyDetector.get_urgency_boost(["urgent", "critical", "blocking"])
        assert boost2 > boost1
        
        # High-impact keywords
        boost3 = UrgencyDetector.get_urgency_boost(["critical", "emergency"])
        assert boost3 > boost1

class TestBusinessRuleEngine:
    """Tests for BusinessRuleEngine class."""
    
    def test_revenue_boost(self):
        """Test revenue boost application."""
        rules = BusinessRules()
        engine = BusinessRuleEngine(rules)
        
        # Revenue-critical component
        assert engine.apply_revenue_boost("authentication") == 1.15
        assert engine.apply_revenue_boost("payment") == 1.15
        
        # Non-critical component
        assert engine.apply_revenue_boost("ui") == 1.0
    
    def test_cluster_amplification(self):
        """Test cluster amplification application."""
        rules = BusinessRules()
        engine = BusinessRuleEngine(rules)
        
        # No cluster data
        assert engine.apply_cluster_amplification(None) == 1.0
        
        # Small cluster
        small_cluster = {"size": 1}
        assert engine.apply_cluster_amplification(small_cluster) == 1.0
        
        # Large cluster
        large_cluster = {"size": 10, "avg_similarity": 0.8}
        amplification = engine.apply_cluster_amplification(large_cluster)
        assert amplification > 1.0
    
    def test_urgency_boost(self):
        """Test urgency boost application."""
        rules = BusinessRules()
        engine = BusinessRuleEngine(rules)
        
        # No urgency indicators
        assert engine.apply_urgency_boost([]) == 1.0
        
        # With urgency indicators
        boost = engine.apply_urgency_boost(["urgent", "critical"])
        assert boost > 1.0

class TestPriorityCalculator:
    """Tests for PriorityCalculator class."""
    
    def test_calculator_initialization(self):
        """Test priority calculator initialization."""
        weights = ScoringWeights()
        rules = BusinessRules()
        calculator = PriorityCalculator(weights, rules)
        
        assert calculator.weights == weights
        assert calculator.rules == rules
        assert calculator.rule_engine is not None
    
    def test_priority_calculation_basic(self):
        """Test basic priority calculation."""
        weights = ScoringWeights()
        rules = BusinessRules()
        calculator = PriorityCalculator(weights, rules)
        
        feedback_data = {
            "title": "Test issue",
            "body": "Test description",
            "severity": "high",
            "component": "ui",
            "user_count": 10,
            "user_segment": "individual",
            "timestamp": datetime.utcnow(),
            "feedback_quality": "medium"
        }
        
        priority_score = calculator.calculate_priority(feedback_data)
        
        assert isinstance(priority_score, PriorityScore)
        assert 0 <= priority_score.final_score <= 1
        assert priority_score.priority_level in PriorityLevel
    
    def test_priority_calculation_with_cluster(self):
        """Test priority calculation with cluster data."""
        weights = ScoringWeights()
        rules = BusinessRules()
        calculator = PriorityCalculator(weights, rules)
        
        feedback_data = {
            "title": "Critical login issue",
            "body": "Users cannot log in. This is urgent!",
            "severity": "critical",
            "component": "authentication",
            "user_count": 100,
            "user_segment": "enterprise",
            "timestamp": datetime.utcnow(),
            "feedback_quality": "high"
        }
        
        cluster_data = {
            "size": 5,
            "avg_similarity": 0.8,
            "temporal_coherence": 0.7,
            "user_diversity": 0.6
        }
        
        priority_score = calculator.calculate_priority(feedback_data, cluster_data)
        
        assert priority_score.priority_level in [PriorityLevel.CRITICAL, PriorityLevel.HIGH]
        assert priority_score.cluster_amplification > 0.9  # Should be close to 1.0 or higher
        assert priority_score.urgency_boost > 1.0
        assert priority_score.revenue_boost > 1.0

class TestPrioritizerAgent:
    """Tests for PrioritizerAgent class."""
    
    def test_prioritizer_agent_initialization(self, prioritizer_agent):
        """Test PrioritizerAgent initialization."""
        assert prioritizer_agent.name == "prioritizer"
        assert prioritizer_agent.weights is not None
        assert prioritizer_agent.rules is not None
        assert prioritizer_agent.calculator is not None
    
    def test_get_input_dependencies(self, prioritizer_agent):
        """Test input dependencies."""
        deps = prioritizer_agent.get_input_dependencies()
        assert "classifier" in deps
        assert "clusterer" in deps
    
    def test_determine_user_segment(self, prioritizer_agent):
        """Test user segment determination."""
        # Test document with enterprise author
        doc = Mock()
        doc.author = "enterprise_user@company.com"
        segment = prioritizer_agent._determine_user_segment(doc)
        assert segment == UserSegment.ENTERPRISE
        
        # Test document with trial author
        doc.author = "trial_user@test.com"
        segment = prioritizer_agent._determine_user_segment(doc)
        assert segment == UserSegment.TRIAL
        
        # Test document with no author
        doc.author = None
        segment = prioritizer_agent._determine_user_segment(doc)
        assert segment == UserSegment.UNKNOWN
    
    def test_assess_feedback_quality(self, prioritizer_agent):
        """Test feedback quality assessment."""
        # High quality feedback
        doc = Mock()
        doc.body = "Steps to reproduce: 1. Click login 2. Enter credentials 3. See error. Expected: Should log in. Actual: Error message. Environment: Chrome 90, Windows 10"
        quality = prioritizer_agent._assess_feedback_quality(doc)
        assert quality == "high"
        
        # Low quality feedback
        doc.body = "bug"
        quality = prioritizer_agent._assess_feedback_quality(doc)
        assert quality == "low"
        
        # Medium quality feedback
        doc.body = "Login not working. Please fix. Steps to reproduce: 1. Go to login page 2. Enter credentials 3. Click login"
        quality = prioritizer_agent._assess_feedback_quality(doc)
        assert quality == "medium"
    
    def test_prepare_feedback_data(self, prioritizer_agent):
        """Test feedback data preparation."""
        doc = Mock()
        doc.id = "test_id"
        doc.title = "Test issue"
        doc.body = "Test description"
        doc.feedback_type = Mock()
        doc.feedback_type.value = "bug"
        doc.component = "ui"
        doc.timestamp = datetime.utcnow()
        doc.author = "test_user"
        
        cluster_data = {"size": 5, "id": "cluster_1"}
        
        feedback_data = prioritizer_agent._prepare_feedback_data(doc, cluster_data)
        
        assert feedback_data["id"] == "test_id"
        assert feedback_data["title"] == "Test issue"
        assert feedback_data["severity"] == "bug"
        assert feedback_data["component"] == "ui"
        assert feedback_data["cluster_size"] == 5
        assert feedback_data["cluster_id"] == "cluster_1"
    
    @pytest.mark.asyncio
    async def test_test_prioritization_system(self, prioritizer_agent):
        """Test prioritization system test."""
        result = await prioritizer_agent.test_prioritization_system()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_prioritization_stats(self, prioritizer_agent):
        """Test prioritization statistics retrieval."""
        with patch.object(prioritizer_agent, 'get_db_session') as mock_session:
            # Mock database queries
            mock_query = mock_session.return_value.__enter__.return_value.query
            mock_query.return_value.count.return_value = 10
            mock_query.return_value.all.return_value = [(0.8,)]
            
            # Mock the join query for component priorities
            mock_join_query = mock_query.return_value.join.return_value
            mock_join_query.all.return_value = [("ui", 0.8), ("api", 0.9)]
            
            stats = await prioritizer_agent.get_prioritization_stats()
            
            assert "total_scores" in stats
            assert "average_priority_score" in stats
            assert "priority_distribution" in stats
            assert "weights" in stats

@pytest.fixture
def prioritizer_agent():
    """Create PrioritizerAgent instance for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        return PrioritizerAgent({
            "prioritizer_batch_size": 10,
            "max_items_to_prioritize": 100,
            "enable_learning": False
        })

@pytest.fixture
def mock_documents():
    """Create mock documents for testing."""
    docs = []
    for i in range(5):
        doc = Mock()
        doc.id = f"doc_{i}"
        doc.title = f"Test Document {i}"
        doc.body = f"This is test content {i}"
        doc.feedback_type = Mock()
        doc.feedback_type.value = "bug"
        doc.component = "ui"
        doc.timestamp = datetime.utcnow()
        doc.author = f"user_{i}"
        docs.append(doc)
    return docs

class TestPrioritizerAgentIntegration:
    """Integration tests for PrioritizerAgent."""
    
    @pytest.mark.asyncio
    async def test_process_batch(self, prioritizer_agent, mock_documents):
        """Test batch processing."""
        with patch.object(prioritizer_agent, '_get_cluster_data') as mock_cluster:
            with patch.object(prioritizer_agent, '_store_priority_score') as mock_store:
                mock_cluster.return_value = {"size": 3, "id": "cluster_1"}
                mock_store.return_value = None
                
                result = await prioritizer_agent._process_batch(mock_documents)
                
                assert result["successful"] == len(mock_documents)
                assert result["failed"] == 0
                assert result["scores_created"] == len(mock_documents)
    
    @pytest.mark.asyncio
    async def test_process_batch_failure(self, prioritizer_agent, mock_documents):
        """Test batch processing with failure."""
        with patch.object(prioritizer_agent, '_get_cluster_data') as mock_cluster:
            mock_cluster.side_effect = Exception("Cluster data error")
            
            result = await prioritizer_agent._process_batch(mock_documents)
            
            assert result["successful"] == 0
            assert result["failed"] == len(mock_documents)
            assert result["scores_created"] == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
