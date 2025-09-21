#!/usr/bin/env python3
"""
Tests for Classifier Agent.

This module tests the Classifier Agent functionality including:
- Classification result parsing
- OpenAI API integration
- Batch processing
- Error handling
- Metrics tracking
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, Mock, AsyncMock
import json

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.classifier.agent import ClassifierAgent
from agents.classifier.models import (
    ClassificationResult, ClassificationMetrics, FeedbackType, 
    SeverityLevel, ComponentType, ClassificationRules
)

class TestClassificationResult:
    """Tests for ClassificationResult model."""
    
    def test_classification_result_creation(self):
        """Test ClassificationResult creation."""
        result = ClassificationResult(
            feedback_type=FeedbackType.BUG,
            severity_level=SeverityLevel.HIGH,
            component=ComponentType.API,
            type_confidence=0.9,
            severity_confidence=0.8,
            component_confidence=0.7,
            overall_confidence=0.8,
            keywords=["error", "api", "timeout"],
            sentiment="negative"
        )
        
        assert result.feedback_type == FeedbackType.BUG
        assert result.severity_level == SeverityLevel.HIGH
        assert result.component == ComponentType.API
        assert result.type_confidence == 0.9
        assert result.overall_confidence == 0.8
        assert "error" in result.keywords
        assert result.sentiment == "negative"
    
    def test_classification_result_to_dict(self):
        """Test ClassificationResult to_dict conversion."""
        result = ClassificationResult(
            feedback_type=FeedbackType.FEATURE_REQUEST,
            severity_level=SeverityLevel.MEDIUM,
            component=ComponentType.UI,
            type_confidence=0.8,
            severity_confidence=0.7,
            component_confidence=0.6,
            overall_confidence=0.7
        )
        
        data = result.to_dict()
        
        assert data['feedback_type'] == 'feature_request'
        assert data['severity_level'] == 'medium'
        assert data['component'] == 'ui'
        assert data['type_confidence'] == 0.8
        assert data['overall_confidence'] == 0.7
        assert 'classification_timestamp' in data
    
    def test_classification_result_from_dict(self):
        """Test ClassificationResult from_dict creation."""
        data = {
            'feedback_type': 'bug',
            'severity_level': 'high',
            'component': 'api',
            'type_confidence': 0.9,
            'severity_confidence': 0.8,
            'component_confidence': 0.7,
            'overall_confidence': 0.8,
            'keywords': ['error', 'crash'],
            'sentiment': 'negative',
            'urgency_indicators': ['urgent'],
            'classification_timestamp': '2023-01-01T00:00:00',
            'model_version': '1.0'
        }
        
        result = ClassificationResult.from_dict(data)
        
        assert result.feedback_type == FeedbackType.BUG
        assert result.severity_level == SeverityLevel.HIGH
        assert result.component == ComponentType.API
        assert result.keywords == ['error', 'crash']
        assert result.sentiment == 'negative'

class TestClassificationMetrics:
    """Tests for ClassificationMetrics model."""
    
    def test_metrics_initialization(self):
        """Test ClassificationMetrics initialization."""
        metrics = ClassificationMetrics()
        
        assert metrics.total_classified == 0
        assert metrics.successful_classifications == 0
        assert metrics.failed_classifications == 0
        assert metrics.average_confidence == 0.0
        assert metrics.get_success_rate() == 0.0
    
    def test_add_classification(self):
        """Test adding classification to metrics."""
        metrics = ClassificationMetrics()
        
        result = ClassificationResult(
            feedback_type=FeedbackType.BUG,
            severity_level=SeverityLevel.HIGH,
            component=ComponentType.API,
            type_confidence=0.9,
            severity_confidence=0.8,
            component_confidence=0.7,
            overall_confidence=0.8
        )
        
        metrics.add_classification(result, 100.0)
        
        assert metrics.total_classified == 1
        assert metrics.successful_classifications == 1
        assert metrics.failed_classifications == 0
        assert metrics.average_confidence == 0.8
        assert metrics.average_processing_time_ms == 100.0
        assert metrics.type_distribution['bug'] == 1
        assert metrics.severity_distribution['high'] == 1
        assert metrics.component_distribution['api'] == 1
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = ClassificationMetrics()
        
        # Add successful classification
        result1 = ClassificationResult(
            feedback_type=FeedbackType.BUG,
            severity_level=SeverityLevel.HIGH,
            component=ComponentType.API,
            type_confidence=0.9,
            severity_confidence=0.8,
            component_confidence=0.7,
            overall_confidence=0.8
        )
        metrics.add_classification(result1, 100.0)
        
        # Add failed classification (low confidence)
        result2 = ClassificationResult(
            feedback_type=FeedbackType.FEATURE_REQUEST,
            severity_level=SeverityLevel.MEDIUM,
            component=ComponentType.UI,
            type_confidence=0.3,
            severity_confidence=0.2,
            component_confidence=0.4,
            overall_confidence=0.3
        )
        metrics.add_classification(result2, 150.0)
        
        assert metrics.total_classified == 2
        assert metrics.successful_classifications == 1
        assert metrics.failed_classifications == 1
        assert metrics.get_success_rate() == 0.5

class TestClassificationRules:
    """Tests for ClassificationRules validation and adjustment."""
    
    def test_validate_classification_valid(self):
        """Test validation of valid classification."""
        result = ClassificationResult(
            feedback_type=FeedbackType.BUG,
            severity_level=SeverityLevel.HIGH,
            component=ComponentType.API,
            type_confidence=0.9,
            severity_confidence=0.8,
            component_confidence=0.7,
            overall_confidence=0.8
        )
        
        is_valid, errors = ClassificationRules.validate_classification(result)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_classification_invalid_confidence(self):
        """Test validation with invalid confidence scores."""
        result = ClassificationResult(
            feedback_type=FeedbackType.BUG,
            severity_level=SeverityLevel.HIGH,
            component=ComponentType.API,
            type_confidence=1.5,  # Invalid: > 1.0
            severity_confidence=0.8,
            component_confidence=0.7,
            overall_confidence=0.8
        )
        
        is_valid, errors = ClassificationRules.validate_classification(result)
        
        assert is_valid is False
        assert any("Type confidence must be between 0.0 and 1.0" in error for error in errors)
    
    def test_validate_classification_low_confidence(self):
        """Test validation with very low confidence."""
        result = ClassificationResult(
            feedback_type=FeedbackType.BUG,
            severity_level=SeverityLevel.HIGH,
            component=ComponentType.API,
            type_confidence=0.2,
            severity_confidence=0.1,
            component_confidence=0.3,
            overall_confidence=0.2
        )
        
        is_valid, errors = ClassificationRules.validate_classification(result)
        
        assert is_valid is False
        assert any("Overall confidence is very low" in error for error in errors)
    
    def test_adjust_classification_feature_request(self):
        """Test adjustment of feature request severity."""
        result = ClassificationResult(
            feedback_type=FeedbackType.FEATURE_REQUEST,
            severity_level=SeverityLevel.CRITICAL,  # Should be adjusted
            component=ComponentType.UI,
            type_confidence=0.9,
            severity_confidence=0.8,
            component_confidence=0.7,
            overall_confidence=0.8
        )
        
        adjusted = ClassificationRules.adjust_classification(result)
        
        assert adjusted.severity_level == SeverityLevel.MEDIUM
        assert adjusted.severity_confidence <= 0.7
    
    def test_adjust_classification_bug_minimal(self):
        """Test adjustment of bug with minimal severity."""
        result = ClassificationResult(
            feedback_type=FeedbackType.BUG,
            severity_level=SeverityLevel.MINIMAL,  # Should be adjusted
            component=ComponentType.API,
            type_confidence=0.9,
            severity_confidence=0.8,
            component_confidence=0.7,
            overall_confidence=0.8
        )
        
        adjusted = ClassificationRules.adjust_classification(result)
        
        assert adjusted.severity_level == SeverityLevel.LOW
        assert adjusted.severity_confidence <= 0.6

class TestClassifierAgent:
    """Tests for ClassifierAgent."""
    
    @pytest.fixture
    def classifier_agent(self):
        """Create ClassifierAgent instance for testing."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            return ClassifierAgent({
                "batch_size": 5,
                "confidence_threshold": 0.5,
                "enable_batch_processing": True,
                "model_name": "gpt-3.5-turbo",
                "max_tokens": 500,
                "temperature": 0.1
            })
    
    def test_classifier_agent_initialization(self, classifier_agent):
        """Test ClassifierAgent initialization."""
        assert classifier_agent.name == "classifier"
        assert classifier_agent.batch_size == 5
        assert classifier_agent.confidence_threshold == 0.5
        assert classifier_agent.model_name == "gpt-3.5-turbo"
        assert classifier_agent.temperature == 0.1
    
    def test_get_input_dependencies(self, classifier_agent):
        """Test input dependencies."""
        dependencies = classifier_agent.get_input_dependencies()
        assert dependencies == ["normalizer"]
    
    def test_convert_severity_to_score(self, classifier_agent):
        """Test severity to score conversion."""
        assert classifier_agent._convert_severity_to_score(SeverityLevel.CRITICAL) == 1.0
        assert classifier_agent._convert_severity_to_score(SeverityLevel.HIGH) == 0.8
        assert classifier_agent._convert_severity_to_score(SeverityLevel.MEDIUM) == 0.6
        assert classifier_agent._convert_severity_to_score(SeverityLevel.LOW) == 0.4
        assert classifier_agent._convert_severity_to_score(SeverityLevel.MINIMAL) == 0.2
    
    def test_parse_classification_result_valid(self, classifier_agent):
        """Test parsing valid classification result."""
        classification = {
            "feedback_type": "bug",
            "severity_level": "high",
            "component": "api",
            "type_confidence": 0.9,
            "severity_confidence": 0.8,
            "component_confidence": 0.7,
            "version": "1.2.3",
            "keywords": ["error", "timeout"],
            "sentiment": "negative",
            "urgency_indicators": ["urgent"]
        }
        
        document = {
            "id": "test_doc_1",
            "title": "API Error",
            "body": "API is timing out",
            "author": "test_user"
        }
        
        result = classifier_agent._parse_classification_result(classification, document)
        
        assert result is not None
        assert result.feedback_type == FeedbackType.BUG
        assert result.severity_level == SeverityLevel.HIGH
        assert result.component == ComponentType.API
        assert result.type_confidence == 0.9
        assert result.version == "1.2.3"
        assert "error" in result.keywords
        assert result.sentiment == "negative"
    
    def test_parse_classification_result_invalid(self, classifier_agent):
        """Test parsing invalid classification result."""
        classification = {
            "feedback_type": "invalid_type",  # Invalid enum value
            "severity_level": "high",
            "component": "api",
            "type_confidence": 0.9,
            "severity_confidence": 0.8,
            "component_confidence": 0.7
        }
        
        document = {
            "id": "test_doc_1",
            "title": "API Error",
            "body": "API is timing out",
            "author": "test_user"
        }
        
        result = classifier_agent._parse_classification_result(classification, document)
        
        assert result is None  # Should return None for invalid data
    
    @pytest.mark.asyncio
    async def test_classify_single_feedback(self, classifier_agent):
        """Test single feedback classification."""
        with patch.object(classifier_agent, '_classify_single_document') as mock_classify:
            mock_result = ClassificationResult(
                feedback_type=FeedbackType.BUG,
                severity_level=SeverityLevel.HIGH,
                component=ComponentType.API,
                type_confidence=0.9,
                severity_confidence=0.8,
                component_confidence=0.7,
                overall_confidence=0.8
            )
            mock_classify.return_value = mock_result
            
            result = await classifier_agent.classify_single_feedback(
                "API Error", "API is timing out", "test_user"
            )
            
            assert result is not None
            assert result.feedback_type == FeedbackType.BUG
            assert result.severity_level == SeverityLevel.HIGH
            mock_classify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_classification_stats(self, classifier_agent):
        """Test getting classification statistics."""
        # Add some test data to metrics
        result = ClassificationResult(
            feedback_type=FeedbackType.BUG,
            severity_level=SeverityLevel.HIGH,
            component=ComponentType.API,
            type_confidence=0.9,
            severity_confidence=0.8,
            component_confidence=0.7,
            overall_confidence=0.8
        )
        classifier_agent.metrics.add_classification(result, 100.0)
        
        stats = await classifier_agent.get_classification_stats()
        
        assert stats['total_classified'] == 1
        assert stats['successful_classifications'] == 1
        assert stats['success_rate'] == 1.0
        assert stats['average_confidence'] == 0.8
        assert stats['type_distribution']['bug'] == 1
    
    @pytest.mark.asyncio
    async def test_test_openai_connection_success(self, classifier_agent):
        """Test successful OpenAI connection test."""
        with patch.object(classifier_agent.openai_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "OK"
            mock_create.return_value = mock_response
            
            result = await classifier_agent.test_openai_connection()
            
            assert result is True
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_openai_connection_failure(self, classifier_agent):
        """Test failed OpenAI connection test."""
        with patch.object(classifier_agent.openai_client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = Exception("Connection failed")
            
            result = await classifier_agent.test_openai_connection()
            
            assert result is False

class TestClassifierAgentIntegration:
    """Integration tests for ClassifierAgent."""
    
    @pytest.mark.asyncio
    async def test_process_with_mock_openai(self):
        """Test full process with mocked OpenAI API."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            agent = ClassifierAgent({
                "batch_size": 2,
                "enable_batch_processing": True
            })
        
        # Mock database session
        mock_doc = Mock(
            id="doc_1",
            title="API Error",
            body="API is timing out",
            author="test_user",
            timestamp=datetime.utcnow(),
            url="https://example.com",
            language="en",
            word_count=10,
            raw_feedback_id="raw_1"
        )
        
        # Mock the _get_pending_documents method directly
        with patch.object(agent, '_get_pending_documents') as mock_get_docs:
            mock_get_docs.return_value = [{
                'id': 'doc_1',
                'title': 'API Error',
                'body': 'API is timing out',
                'author': 'test_user',
                'timestamp': datetime.utcnow(),
                'url': 'https://example.com',
                'language': 'en',
                'word_count': 10,
                'raw_feedback_id': 'raw_1'
            }]
            
            # Mock OpenAI response
            with patch.object(agent, '_classify_batch', new_callable=AsyncMock) as mock_classify:
                mock_result = ClassificationResult(
                    feedback_type=FeedbackType.BUG,
                    severity_level=SeverityLevel.HIGH,
                    component=ComponentType.API,
                    type_confidence=0.9,
                    severity_confidence=0.8,
                    component_confidence=0.7,
                    overall_confidence=0.8
                )
                mock_classify.return_value = [mock_result]
                
                # Mock store result
                with patch.object(agent, '_store_classification_result', new_callable=AsyncMock) as mock_store:
                    result = await agent.process(agent._create_default_context())
                    
                    assert result.success is True
                    assert result.items_processed == 1
                    assert result.items_successful == 1
                    assert result.items_failed == 0
                    mock_classify.assert_called_once()
                    mock_store.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
