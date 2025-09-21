"""
Tests for the Feedback Loop Agent.

This module contains comprehensive unit and integration tests
for the Feedback Loop Agent and its components.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import uuid

from agents.feedback_loop.agent import FeedbackLoopAgent
from agents.feedback_loop.learning import LearningEngine, LearningOutcome, PerformanceMetrics, WeightAdjustment
from agents.feedback_loop.metrics import MetricsCollector, SystemMetrics, ABTestManager, ABTestConfig, ABTestResult
from agents.base.agent import AgentContext
from database.models import (
    ProcessedDocument, PrioritizationScore, Ticket, Cluster,
    FeedbackType, SourceType, ProcessingStatus, PriorityLevel as DBPriorityLevel,
    TicketStatus
)

class TestFeedbackLoopAgent:
    """Test cases for FeedbackLoopAgent class."""
    
    @pytest.fixture
    def feedback_loop_agent(self):
        """Create FeedbackLoopAgent instance for testing."""
        config = {
            "feedback_loop": {
                "learning_rate": 0.1,
                "min_samples": 10,
                "analysis_window_days": 30,
                "enable_ab_testing": True,
                "enable_weight_adjustment": True
            }
        }
        return FeedbackLoopAgent(config)
    
    @pytest.fixture
    def mock_learning_outcomes(self):
        """Create mock learning outcomes for testing."""
        return [
            LearningOutcome(
                feedback_id="1",
                predicted_priority=0.8,
                actual_priority=0.7,
                resolution_time=24.0,
                resolution_quality=0.8,
                user_satisfaction=0.7,
                business_impact=0.6,
                classification_accuracy=0.9,
                clustering_accuracy=0.8,
                outcome_timestamp=datetime.utcnow()
            ),
            LearningOutcome(
                feedback_id="2",
                predicted_priority=0.6,
                actual_priority=0.8,
                resolution_time=48.0,
                resolution_quality=0.6,
                user_satisfaction=0.5,
                business_impact=0.7,
                classification_accuracy=0.8,
                clustering_accuracy=0.7,
                outcome_timestamp=datetime.utcnow()
            )
        ]
    
    @pytest.fixture
    def mock_performance_metrics(self):
        """Create mock performance metrics for testing."""
        return SystemMetrics(
            overall_accuracy=0.75,
            precision=0.8,
            recall=0.7,
            f1_score=0.75,
            classification_accuracy=0.85,
            clustering_accuracy=0.7,
            prioritization_accuracy=0.8,
            resolution_time_improvement=0.6,
            user_satisfaction=0.7,
            business_impact=0.65,
            processing_speed=0.8,
            error_rate=0.95,
            uptime=0.999,
            learning_rate=0.1,
            adaptation_speed=0.6,
            weight_stability=0.8,
            measurement_period=(datetime.utcnow() - timedelta(days=30), datetime.utcnow()),
            last_updated=datetime.utcnow()
        )
    
    def test_initialization(self, feedback_loop_agent):
        """Test FeedbackLoopAgent initialization."""
        assert feedback_loop_agent.name == "feedback_loop"
        assert feedback_loop_agent.learning_rate == 0.1
        assert feedback_loop_agent.min_samples == 10
        assert feedback_loop_agent.analysis_window_days == 30
        assert feedback_loop_agent.enable_ab_testing is True
        assert feedback_loop_agent.enable_weight_adjustment is True
        assert isinstance(feedback_loop_agent.learning_engine, LearningEngine)
        assert isinstance(feedback_loop_agent.metrics_collector, MetricsCollector)
        assert isinstance(feedback_loop_agent.ab_test_manager, ABTestManager)
    
    def test_get_input_dependencies(self, feedback_loop_agent):
        """Test input dependencies."""
        dependencies = feedback_loop_agent.get_input_dependencies()
        assert "classifier" in dependencies
        assert "clusterer" in dependencies
        assert "prioritizer" in dependencies
        assert "actioner" in dependencies
        assert "digestor" in dependencies
    
    @pytest.mark.asyncio
    async def test_analyze_resolution_outcomes(self, feedback_loop_agent):
        """Test resolution outcome analysis."""
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        with patch.object(feedback_loop_agent.learning_engine, 'analyze_outcomes') as mock_analyze:
            mock_analyze.return_value = [
                LearningOutcome(
                    feedback_id="1",
                    predicted_priority=0.8,
                    actual_priority=0.7,
                    resolution_time=24.0,
                    resolution_quality=0.8,
                    user_satisfaction=0.7,
                    business_impact=0.6,
                    classification_accuracy=0.9,
                    clustering_accuracy=0.8,
                    outcome_timestamp=datetime.utcnow()
                )
            ]
            
            outcomes = await feedback_loop_agent._analyze_resolution_outcomes(start_date, end_date)
            
            assert len(outcomes) == 1
            assert outcomes[0].feedback_id == "1"
            assert outcomes[0].predicted_priority == 0.8
            assert outcomes[0].actual_priority == 0.7
            mock_analyze.assert_called_once_with(start_date, end_date)
    
    @pytest.mark.asyncio
    async def test_calculate_performance_metrics(self, feedback_loop_agent):
        """Test performance metrics calculation."""
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        with patch.object(feedback_loop_agent.metrics_collector, 'collect_system_metrics') as mock_collect:
            mock_metrics = SystemMetrics(
                overall_accuracy=0.75,
                precision=0.8,
                recall=0.7,
                f1_score=0.75,
                classification_accuracy=0.85,
                clustering_accuracy=0.7,
                prioritization_accuracy=0.8,
                resolution_time_improvement=0.6,
                user_satisfaction=0.7,
                business_impact=0.65,
                processing_speed=0.8,
                error_rate=0.95,
                uptime=0.999,
                learning_rate=0.1,
                adaptation_speed=0.6,
                weight_stability=0.8,
                measurement_period=(start_date, end_date),
                last_updated=datetime.utcnow()
            )
            mock_collect.return_value = mock_metrics
            
            metrics = await feedback_loop_agent._calculate_performance_metrics(start_date, end_date)
            
            assert metrics is not None
            assert metrics.overall_accuracy == 0.75
            assert metrics.precision == 0.8
            assert metrics.recall == 0.7
            mock_collect.assert_called_once_with(start_date, end_date)
    
    @pytest.mark.asyncio
    async def test_generate_weight_adjustments(self, feedback_loop_agent, mock_learning_outcomes):
        """Test weight adjustment generation."""
        with patch.object(feedback_loop_agent.learning_engine, 'generate_weight_adjustments') as mock_generate:
            mock_adjustments = [
                WeightAdjustment(
                    component="severity",
                    old_weight=0.3,
                    new_weight=0.35,
                    adjustment_reason="Bias correction: 0.1",
                    confidence=0.8,
                    impact_score=0.5
                )
            ]
            mock_generate.return_value = mock_adjustments
            
            adjustments = await feedback_loop_agent._generate_weight_adjustments(mock_learning_outcomes)
            
            assert len(adjustments) == 1
            assert adjustments[0].component == "severity"
            assert adjustments[0].old_weight == 0.3
            assert adjustments[0].new_weight == 0.35
            mock_generate.assert_called_once_with(mock_learning_outcomes, feedback_loop_agent.current_weights)
    
    @pytest.mark.asyncio
    async def test_conduct_ab_tests(self, feedback_loop_agent):
        """Test A/B test conduction."""
        with patch.object(feedback_loop_agent.ab_test_manager, 'active_tests') as mock_tests:
            mock_tests.values.return_value = [
                ABTestConfig(
                    test_name="test1",
                    description="Test description",
                    control_group="control",
                    treatment_group="treatment",
                    traffic_split=0.5,
                    success_metric="accuracy",
                    minimum_effect_size=0.05,
                    confidence_level=0.95,
                    max_duration_days=30,
                    is_active=True,
                    created_at=datetime.utcnow() - timedelta(days=35)
                )
            ]
            
            with patch.object(feedback_loop_agent.ab_test_manager, 'analyze_ab_test') as mock_analyze:
                mock_result = ABTestResult(
                    test_name="test1",
                    control_metric=0.75,
                    treatment_metric=0.82,
                    effect_size=0.07,
                    confidence_interval=(0.70, 0.90),
                    p_value=0.05,
                    is_significant=True,
                    recommendation="Implement treatment",
                    sample_size=1000,
                    duration_days=35
                )
                mock_analyze.return_value = mock_result
                
                with patch.object(feedback_loop_agent.ab_test_manager, 'stop_ab_test') as mock_stop:
                    results = await feedback_loop_agent._conduct_ab_tests()
                    
                    assert len(results) == 1
                    assert results[0].test_name == "test1"
                    assert results[0].is_significant is True
                    mock_analyze.assert_called_once_with("test1")
                    mock_stop.assert_called_once_with("test1")
    
    @pytest.mark.asyncio
    async def test_update_system_configuration(self, feedback_loop_agent, mock_learning_outcomes, mock_performance_metrics):
        """Test system configuration updates."""
        with patch.object(feedback_loop_agent.learning_engine, 'generate_weight_adjustments') as mock_generate:
            mock_adjustments = [
                WeightAdjustment(
                    component="severity",
                    old_weight=0.3,
                    new_weight=0.35,
                    adjustment_reason="Bias correction: 0.1",
                    confidence=0.8,
                    impact_score=0.5
                )
            ]
            mock_generate.return_value = mock_adjustments
            
            updates = await feedback_loop_agent._update_system_configuration(
                mock_learning_outcomes, mock_performance_metrics
            )
            
            assert len(updates) >= 1
            assert updates[0]["type"] == "weight_adjustment"
            assert updates[0]["component"] == "severity"
            assert updates[0]["old_value"] == 0.3
            assert updates[0]["new_value"] == 0.35
    
    @pytest.mark.asyncio
    async def test_generate_recommendations(self, feedback_loop_agent, mock_learning_outcomes, mock_performance_metrics):
        """Test recommendation generation."""
        recommendations = await feedback_loop_agent._generate_recommendations(
            mock_learning_outcomes, mock_performance_metrics
        )
        
        assert len(recommendations) > 0
        
        # Check for specific recommendation types
        recommendation_types = [rec["type"] for rec in recommendations]
        assert "accuracy_improvement" in recommendation_types or "classification_improvement" in recommendation_types
    
    @pytest.mark.asyncio
    async def test_create_ab_test(self, feedback_loop_agent):
        """Test A/B test creation."""
        with patch.object(feedback_loop_agent.ab_test_manager, 'create_ab_test') as mock_create:
            mock_create.return_value = True
            
            result = await feedback_loop_agent.create_ab_test(
                test_name="test_accuracy",
                description="Test accuracy improvement",
                control_group="current_algorithm",
                treatment_group="new_algorithm",
                traffic_split=0.5
            )
            
            assert result is True
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_ab_test_results(self, feedback_loop_agent):
        """Test A/B test results retrieval."""
        with patch.object(feedback_loop_agent.ab_test_manager, 'analyze_ab_test') as mock_analyze:
            mock_result = ABTestResult(
                test_name="test1",
                control_metric=0.75,
                treatment_metric=0.82,
                effect_size=0.07,
                confidence_interval=(0.70, 0.90),
                p_value=0.05,
                is_significant=True,
                recommendation="Implement treatment",
                sample_size=1000,
                duration_days=30
            )
            mock_analyze.return_value = mock_result
            
            result = await feedback_loop_agent.get_ab_test_results("test1")
            
            assert result is not None
            assert result.test_name == "test1"
            assert result.is_significant is True
            mock_analyze.assert_called_once_with("test1")
    
    @pytest.mark.asyncio
    async def test_get_performance_metrics(self, feedback_loop_agent):
        """Test performance metrics retrieval."""
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        with patch.object(feedback_loop_agent.metrics_collector, 'collect_system_metrics') as mock_collect:
            mock_metrics = SystemMetrics(
                overall_accuracy=0.75,
                precision=0.8,
                recall=0.7,
                f1_score=0.75,
                classification_accuracy=0.85,
                clustering_accuracy=0.7,
                prioritization_accuracy=0.8,
                resolution_time_improvement=0.6,
                user_satisfaction=0.7,
                business_impact=0.65,
                processing_speed=0.8,
                error_rate=0.95,
                uptime=0.999,
                learning_rate=0.1,
                adaptation_speed=0.6,
                weight_stability=0.8,
                measurement_period=(start_date, end_date),
                last_updated=datetime.utcnow()
            )
            mock_collect.return_value = mock_metrics
            
            metrics = await feedback_loop_agent.get_performance_metrics(start_date, end_date)
            
            assert metrics is not None
            assert metrics.overall_accuracy == 0.75
            mock_collect.assert_called_once_with(start_date, end_date)
    
    @pytest.mark.asyncio
    async def test_get_learning_outcomes(self, feedback_loop_agent):
        """Test learning outcomes retrieval."""
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        with patch.object(feedback_loop_agent.learning_engine, 'analyze_outcomes') as mock_analyze:
            mock_outcomes = [
                LearningOutcome(
                    feedback_id="1",
                    predicted_priority=0.8,
                    actual_priority=0.7,
                    resolution_time=24.0,
                    resolution_quality=0.8,
                    user_satisfaction=0.7,
                    business_impact=0.6,
                    classification_accuracy=0.9,
                    clustering_accuracy=0.8,
                    outcome_timestamp=datetime.utcnow()
                )
            ]
            mock_analyze.return_value = mock_outcomes
            
            outcomes = await feedback_loop_agent.get_learning_outcomes(start_date, end_date)
            
            assert len(outcomes) == 1
            assert outcomes[0].feedback_id == "1"
            mock_analyze.assert_called_once_with(start_date, end_date)
    
    @pytest.mark.asyncio
    async def test_get_current_weights(self, feedback_loop_agent):
        """Test current weights retrieval."""
        weights = await feedback_loop_agent.get_current_weights()
        
        assert isinstance(weights, dict)
        assert "severity" in weights
        assert "reach" in weights
        assert "recency" in weights
        assert "persona" in weights
        assert "cluster_amplification" in weights
    
    @pytest.mark.asyncio
    async def test_update_weights(self, feedback_loop_agent):
        """Test weight updates."""
        new_weights = {
            "severity": 0.35,
            "reach": 0.25,
            "recency": 0.2,
            "persona": 0.15,
            "cluster_amplification": 0.05
        }
        
        result = await feedback_loop_agent.update_weights(new_weights)
        
        assert result is True
        assert feedback_loop_agent.current_weights["severity"] == 0.35
        assert feedback_loop_agent.current_weights["cluster_amplification"] == 0.05
    
    @pytest.mark.asyncio
    async def test_update_weights_invalid(self, feedback_loop_agent):
        """Test weight updates with invalid values."""
        invalid_weights = {
            "severity": -0.1,  # Invalid negative weight
            "reach": 3.0       # Invalid weight > 2
        }
        
        result = await feedback_loop_agent.update_weights(invalid_weights)
        
        assert result is False
        # Weights should not be updated
        assert feedback_loop_agent.current_weights["severity"] == 0.3
    
    @pytest.mark.asyncio
    async def test_get_improvement_recommendations(self, feedback_loop_agent):
        """Test improvement recommendations retrieval."""
        with patch.object(feedback_loop_agent, 'get_performance_metrics') as mock_metrics:
            mock_metrics.return_value = SystemMetrics(
                overall_accuracy=0.6,  # Low accuracy
                precision=0.8,
                recall=0.7,
                f1_score=0.75,
                classification_accuracy=0.85,
                clustering_accuracy=0.7,
                prioritization_accuracy=0.8,
                resolution_time_improvement=0.6,
                user_satisfaction=0.7,
                business_impact=0.65,
                processing_speed=0.8,
                error_rate=0.95,
                uptime=0.999,
                learning_rate=0.1,
                adaptation_speed=0.6,
                weight_stability=0.8,
                measurement_period=(datetime.utcnow() - timedelta(days=7), datetime.utcnow()),
                last_updated=datetime.utcnow()
            )
            
            with patch.object(feedback_loop_agent, 'get_learning_outcomes') as mock_outcomes:
                mock_outcomes.return_value = []
                
                recommendations = await feedback_loop_agent.get_improvement_recommendations()
                
                assert len(recommendations) > 0
                # Should have accuracy improvement recommendation due to low accuracy
                assert any(rec["type"] == "accuracy_improvement" for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_get_performance_trends(self, feedback_loop_agent):
        """Test performance trends retrieval."""
        # Add some mock performance history
        feedback_loop_agent.performance_history = [
            SystemMetrics(
                overall_accuracy=0.7,
                precision=0.75,
                recall=0.65,
                f1_score=0.7,
                classification_accuracy=0.8,
                clustering_accuracy=0.65,
                prioritization_accuracy=0.75,
                resolution_time_improvement=0.55,
                user_satisfaction=0.65,
                business_impact=0.6,
                processing_speed=0.75,
                error_rate=0.9,
                uptime=0.999,
                learning_rate=0.08,
                adaptation_speed=0.55,
                weight_stability=0.75,
                measurement_period=(datetime.utcnow() - timedelta(days=30), datetime.utcnow() - timedelta(days=15)),
                last_updated=datetime.utcnow() - timedelta(days=15)
            ),
            SystemMetrics(
                overall_accuracy=0.75,
                precision=0.8,
                recall=0.7,
                f1_score=0.75,
                classification_accuracy=0.85,
                clustering_accuracy=0.7,
                prioritization_accuracy=0.8,
                resolution_time_improvement=0.6,
                user_satisfaction=0.7,
                business_impact=0.65,
                processing_speed=0.8,
                error_rate=0.95,
                uptime=0.999,
                learning_rate=0.1,
                adaptation_speed=0.6,
                weight_stability=0.8,
                measurement_period=(datetime.utcnow() - timedelta(days=15), datetime.utcnow()),
                last_updated=datetime.utcnow()
            )
        ]
        
        trends = await feedback_loop_agent.get_performance_trends()
        
        assert "accuracy_trend" in trends
        assert "precision_trend" in trends
        assert "recall_trend" in trends
        assert "f1_trend" in trends
        assert trends["accuracy_trend"] == 0.05  # 0.75 - 0.7
        assert trends["precision_trend"] == 0.05  # 0.8 - 0.75

class TestLearningEngine:
    """Test cases for LearningEngine class."""
    
    @pytest.fixture
    def learning_engine(self):
        """Create LearningEngine instance for testing."""
        return LearningEngine()
    
    def test_initialization(self, learning_engine):
        """Test LearningEngine initialization."""
        assert learning_engine.learning_rate == 0.1
        assert learning_engine.min_samples == 10
        assert learning_engine.confidence_threshold == 0.7
    
    def test_calculate_actual_priority(self, learning_engine):
        """Test actual priority calculation."""
        # Mock ticket and feedback
        ticket = Mock()
        ticket.status = TicketStatus.CLOSED
        ticket.created_at = datetime.utcnow() - timedelta(hours=2)
        ticket.updated_at = datetime.utcnow()
        
        feedback = Mock()
        feedback.feedback_type = FeedbackType.BUG
        
        actual_priority = learning_engine._calculate_actual_priority(ticket, feedback)
        
        assert 0.0 <= actual_priority <= 1.0
        # Should be high priority for bug resolved quickly
        assert actual_priority > 0.7
    
    def test_calculate_resolution_time(self, learning_engine):
        """Test resolution time calculation."""
        ticket = Mock()
        ticket.status = TicketStatus.RESOLVED
        ticket.created_at = datetime.utcnow() - timedelta(hours=5)
        ticket.updated_at = datetime.utcnow()
        
        resolution_time = learning_engine._calculate_resolution_time(ticket)
        
        assert abs(resolution_time - 5.0) < 0.1
    
    def test_calculate_resolution_quality(self, learning_engine):
        """Test resolution quality calculation."""
        ticket = Mock()
        ticket.status = TicketStatus.CLOSED
        ticket.created_at = datetime.utcnow() - timedelta(hours=2)
        ticket.updated_at = datetime.utcnow()
        
        feedback = Mock()
        feedback.feedback_type = FeedbackType.BUG
        
        quality = learning_engine._calculate_resolution_quality(ticket, feedback)
        
        assert 0.0 <= quality <= 1.0
        # Should be high quality for bug resolved quickly
        assert quality > 0.7
    
    def test_calculate_business_impact(self, learning_engine):
        """Test business impact calculation."""
        ticket = Mock()
        ticket.status = TicketStatus.RESOLVED
        ticket.created_at = datetime.utcnow() - timedelta(hours=24)
        ticket.updated_at = datetime.utcnow()
        
        feedback = Mock()
        feedback.feedback_type = FeedbackType.BUG
        feedback.component = "authentication"
        
        impact = learning_engine._calculate_business_impact(ticket, feedback)
        
        assert 0.0 <= impact <= 1.0
        # Should be high impact for bug in critical component
        assert impact > 0.6

class TestMetricsCollector:
    """Test cases for MetricsCollector class."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create MetricsCollector instance for testing."""
        return MetricsCollector()
    
    def test_initialization(self, metrics_collector):
        """Test MetricsCollector initialization."""
        assert isinstance(metrics_collector.metrics_cache, dict)
        assert metrics_collector.cache_duration == timedelta(hours=1)
    
    def test_calculate_overall_accuracy(self, metrics_collector):
        """Test overall accuracy calculation."""
        # Mock documents and priority scores
        documents = [Mock() for _ in range(5)]
        priority_scores = [Mock() for _ in range(5)]
        for i, ps in enumerate(priority_scores):
            ps.priority_score = 0.7 + (i * 0.05)
        
        accuracy = metrics_collector._calculate_overall_accuracy(documents, priority_scores)
        
        assert 0.0 <= accuracy <= 1.0
        assert accuracy > 0.7  # Should be high for high priority scores
    
    def test_calculate_classification_accuracy(self, metrics_collector):
        """Test classification accuracy calculation."""
        documents = [
            Mock(feedback_type=FeedbackType.BUG),
            Mock(feedback_type=FeedbackType.FEATURE_REQUEST),
            Mock(feedback_type=None),  # Not classified
            Mock(feedback_type=FeedbackType.PERFORMANCE),
            Mock(feedback_type=FeedbackType.BUG)
        ]
        
        accuracy = metrics_collector._calculate_classification_accuracy(documents)
        
        assert accuracy == 0.8  # 4 out of 5 classified
    
    def test_calculate_processing_speed(self, metrics_collector):
        """Test processing speed calculation."""
        documents = [Mock() for _ in range(100)]
        start_date = datetime.utcnow() - timedelta(hours=2)
        end_date = datetime.utcnow()
        
        speed = metrics_collector._calculate_processing_speed(documents, start_date, end_date)
        
        assert 0.0 <= speed <= 1.0
        assert speed == 0.5  # 100 docs / 2 hours = 50 docs/hour, normalized to 0.5

class TestABTestManager:
    """Test cases for ABTestManager class."""
    
    @pytest.fixture
    def ab_test_manager(self):
        """Create ABTestManager instance for testing."""
        return ABTestManager()
    
    def test_initialization(self, ab_test_manager):
        """Test ABTestManager initialization."""
        assert isinstance(ab_test_manager.active_tests, dict)
    
    def test_create_ab_test(self, ab_test_manager):
        """Test A/B test creation."""
        config = ABTestConfig(
            test_name="test1",
            description="Test description",
            control_group="control",
            treatment_group="treatment",
            traffic_split=0.5,
            success_metric="accuracy",
            minimum_effect_size=0.05,
            confidence_level=0.95,
            max_duration_days=30
        )
        
        result = ab_test_manager.create_ab_test(config)
        
        assert result is True
        assert "test1" in ab_test_manager.active_tests
        assert ab_test_manager.active_tests["test1"].test_name == "test1"
    
    def test_get_test_group(self, ab_test_manager):
        """Test test group assignment."""
        config = ABTestConfig(
            test_name="test1",
            description="Test description",
            control_group="control",
            treatment_group="treatment",
            traffic_split=0.5,
            success_metric="accuracy",
            minimum_effect_size=0.05,
            confidence_level=0.95,
            max_duration_days=30
        )
        ab_test_manager.active_tests["test1"] = config
        
        # Test multiple users to see distribution
        groups = []
        for i in range(100):
            group = ab_test_manager.get_test_group("test1", f"user_{i}")
            groups.append(group)
        
        # Should have both control and treatment groups
        assert "control" in groups
        assert "treatment" in groups
    
    def test_stop_ab_test(self, ab_test_manager):
        """Test A/B test stopping."""
        config = ABTestConfig(
            test_name="test1",
            description="Test description",
            control_group="control",
            treatment_group="treatment",
            traffic_split=0.5,
            success_metric="accuracy",
            minimum_effect_size=0.05,
            confidence_level=0.95,
            max_duration_days=30,
            is_active=True
        )
        ab_test_manager.active_tests["test1"] = config
        
        result = ab_test_manager.stop_ab_test("test1")
        
        assert result is True
        assert ab_test_manager.active_tests["test1"].is_active is False
