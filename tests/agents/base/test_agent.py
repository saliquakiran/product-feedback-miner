#!/usr/bin/env python3
"""
Tests for BaseAgent framework.

This module tests the BaseAgent abstract class and its functionality:
- Agent initialization and configuration
- Retry logic with exponential backoff
- Input validation and output preparation
- Context creation and execution tracking
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, Mock

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.base.agent import BaseAgent, AgentResult, AgentContext, AgentError

class ConcreteTestAgent(BaseAgent):
    """Concrete implementation for testing BaseAgent."""
    
    def __init__(self, name="test_agent", config_overrides=None):
        super().__init__(name, config_overrides)
        self.process_called = False
        self.process_result = None
        self.should_fail = False
    
    async def process(self, context: AgentContext) -> AgentResult:
        self.process_called = True
        if self.should_fail:
            raise Exception("Test failure")
        return self.process_result or AgentResult(success=True, items_processed=1)
    
    def get_input_dependencies(self):
        return ["ingestor", "normalizer"]

class TestBaseAgentInitialization:
    """Tests for BaseAgent initialization."""
    
    def test_agent_initialization(self):
        """Test BaseAgent initialization with default config."""
        agent = ConcreteTestAgent("test_agent")
        
        assert agent.name == "test_agent"
        assert agent.config["max_retries"] == 3
        assert agent.config["timeout"] == 300
        assert agent.config["batch_size"] == 10
        assert agent.config["retry_delay"] == 1.0
        assert agent.config["max_retry_delay"] == 60.0
    
    def test_agent_initialization_with_custom_name(self):
        """Test BaseAgent initialization with custom name."""
        agent = ConcreteTestAgent("custom_agent")
        
        assert agent.name == "custom_agent"
        assert agent.get_output_type() == "custom_agent_output"
    
    def test_config_merge(self):
        """Test configuration merging with overrides."""
        config_overrides = {
            "batch_size": 100,
            "max_retries": 5,
            "new_setting": "value"
        }
        
        agent = ConcreteTestAgent("test_agent", config_overrides)
        
        assert agent.config["batch_size"] == 100
        assert agent.config["max_retries"] == 5
        assert agent.config["new_setting"] == "value"
        assert agent.config["timeout"] == 300  # Default value preserved
    
    def test_config_merge_partial(self):
        """Test configuration merging with partial overrides."""
        config_overrides = {
            "batch_size": 50
        }
        
        agent = ConcreteTestAgent("test_agent", config_overrides)
        
        assert agent.config["batch_size"] == 50
        assert agent.config["max_retries"] == 3  # Default value
        assert agent.config["timeout"] == 300  # Default value

class TestBaseAgentMethods:
    """Tests for BaseAgent methods."""
    
    def test_get_output_type(self):
        """Test get_output_type method."""
        agent = ConcreteTestAgent("test_agent")
        assert agent.get_output_type() == "test_agent_output"
    
    def test_get_input_dependencies(self):
        """Test get_input_dependencies method."""
        agent = ConcreteTestAgent("test_agent")
        assert agent.get_input_dependencies() == ["ingestor", "normalizer"]
    
    def test_create_default_context(self):
        """Test _create_default_context method."""
        agent = ConcreteTestAgent("test_agent")
        context = agent._create_default_context()
        
        assert context.agent_name == "test_agent"
        assert isinstance(context.execution_id, str)
        assert isinstance(context.started_at, datetime)
        assert context.config == agent.config
        assert context.items_processed == 0
        assert context.items_successful == 0
        assert context.items_failed == 0
    
    def test_validate_input_default(self):
        """Test default validate_input method."""
        agent = ConcreteTestAgent("test_agent")
        assert agent.validate_input("valid_data") is True
        assert agent.validate_input(None) is False
        assert agent.validate_input("") is True  # Empty string is valid
        assert agent.validate_input(0) is True  # Zero is valid
    
    def test_prepare_output_default(self):
        """Test default prepare_output method."""
        agent = ConcreteTestAgent("test_agent")
        data = {"key": "value", "number": 42}
        result = agent.prepare_output(data)
        assert result == data
    
    def test_prepare_output_with_none(self):
        """Test prepare_output with None input."""
        agent = ConcreteTestAgent("test_agent")
        result = agent.prepare_output(None)
        assert result is None

class TestBaseAgentRetryLogic:
    """Tests for BaseAgent retry logic."""
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self):
        """Test retry logic with successful function."""
        agent = ConcreteTestAgent("test_agent")
        
        async def success_func():
            return "success"
        
        result = await agent.retry_with_backoff(success_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_failure(self):
        """Test retry logic with failing function."""
        agent = ConcreteTestAgent("test_agent")
        
        async def failing_func():
            raise Exception("Permanent failure")
        
        with pytest.raises(Exception, match="Permanent failure"):
            await agent.retry_with_backoff(failing_func, max_retries=2)
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_eventual_success(self):
        """Test retry logic with eventual success."""
        agent = ConcreteTestAgent("test_agent")
        call_count = 0
        
        async def eventually_successful_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await agent.retry_with_backoff(eventually_successful_func, max_retries=3)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_custom_delay(self):
        """Test retry logic with custom delay settings."""
        agent = ConcreteTestAgent("test_agent")
        call_count = 0
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Temporary failure")
        
        with pytest.raises(Exception, match="Temporary failure"):
            await agent.retry_with_backoff(
                failing_func, 
                max_retries=2, 
                base_delay=0.1,  # Very short delay for testing
                max_delay=0.2
            )
        
        assert call_count == 3  # Initial call + 2 retries

class TestAgentContext:
    """Tests for AgentContext dataclass."""
    
    def test_agent_context_creation(self):
        """Test AgentContext creation."""
        config = {"test": "value"}
        context = AgentContext(
            agent_name="test_agent",
            execution_id="exec_123",
            started_at=datetime.utcnow(),
            config=config,
            items_processed=5,
            items_successful=4,
            items_failed=1
        )
        
        assert context.agent_name == "test_agent"
        assert context.execution_id == "exec_123"
        assert isinstance(context.started_at, datetime)
        assert context.config == config
        assert context.items_processed == 5
        assert context.items_successful == 4
        assert context.items_failed == 1
    
    def test_agent_context_defaults(self):
        """Test AgentContext with default values."""
        context = AgentContext(
            agent_name="test_agent",
            execution_id="exec_123",
            started_at=datetime.utcnow()
        )
        
        assert context.config == {}
        assert context.items_processed == 0
        assert context.items_successful == 0
        assert context.items_failed == 0

class TestAgentResult:
    """Tests for AgentResult dataclass."""
    
    def test_agent_result_creation(self):
        """Test AgentResult creation."""
        result = AgentResult(
            success=True,
            items_processed=10,
            items_successful=8,
            items_failed=2,
            output_data={"key": "value"},
            error_message="Test error"
        )
        
        assert result.success is True
        assert result.items_processed == 10
        assert result.items_successful == 8
        assert result.items_failed == 2
        assert result.output_data == {"key": "value"}
        assert result.error_message == "Test error"
    
    def test_agent_result_defaults(self):
        """Test AgentResult with default values."""
        result = AgentResult(success=True)
        
        assert result.success is True
        assert result.items_processed == 0
        assert result.items_successful == 0
        assert result.items_failed == 0
        assert result.output_data is None
        assert result.error_message is None

class TestBaseAgentErrorHandling:
    """Tests for BaseAgent error handling."""
    
    def test_agent_error_creation(self):
        """Test AgentError exception creation."""
        error = AgentError("Test error message")
        assert str(error) == "Test error message"
    
    def test_agent_error_with_details(self):
        """Test AgentError with additional details."""
        error = AgentError("Test error", details={"key": "value"})
        assert str(error) == "Test error"
        assert hasattr(error, 'details')

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
