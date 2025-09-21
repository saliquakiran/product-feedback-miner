#!/usr/bin/env python3
"""
Tests for logging system.

This module tests the logging functionality:
- Logging setup and configuration
- Agent-specific loggers
- Execution logging
"""

import pytest
import logging
from unittest.mock import patch, Mock

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.logging import setup_logging, get_agent_logger, log_agent_execution

class TestLoggingSetup:
    """Tests for logging setup."""
    
    def test_setup_logging_default(self):
        """Test logging setup with default parameters."""
        logger = setup_logging()
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.level <= logging.INFO  # Should be INFO or lower
    
    def test_setup_logging_with_level(self):
        """Test logging setup with specific log level."""
        logger = setup_logging(log_level="DEBUG")
        assert logger is not None
        assert logger.level <= logging.DEBUG
    
    def test_setup_logging_with_file(self):
        """Test logging setup with file output."""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
        
        try:
            logger = setup_logging(log_level="INFO", log_file=log_file)
            assert logger is not None
            
            # Test that we can write to the log file
            logger.info("Test log message")
            
            # Check that the file was created and has content
            assert os.path.exists(log_file)
            with open(log_file, 'r') as f:
                content = f.read()
                assert "Test log message" in content
        finally:
            # Clean up
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_setup_logging_structured(self):
        """Test structured logging setup."""
        logger = setup_logging(log_level="INFO", structured=True)
        assert logger is not None
        
        # Test that we can log structured data
        logger.info("Test message", extra={"key": "value", "number": 42})
        assert True  # If no exception is raised, test passes

class TestAgentLogger:
    """Tests for agent-specific loggers."""
    
    def test_get_agent_logger(self):
        """Test agent logger creation."""
        agent_logger = get_agent_logger("test_agent", "exec_123")
        assert agent_logger is not None
        assert isinstance(agent_logger, logging.Logger)
        assert agent_logger.extra["agent_name"] == "test_agent"
        assert agent_logger.extra["execution_id"] == "exec_123"
    
    def test_get_agent_logger_different_agents(self):
        """Test that different agents get different loggers."""
        logger1 = get_agent_logger("agent1", "exec_1")
        logger2 = get_agent_logger("agent2", "exec_2")
        
        assert logger1.extra["agent_name"] == "agent1"
        assert logger2.extra["agent_name"] == "agent2"
        assert logger1.extra["execution_id"] == "exec_1"
        assert logger2.extra["execution_id"] == "exec_2"
    
    def test_agent_logger_logging(self):
        """Test that agent logger can log messages."""
        agent_logger = get_agent_logger("test_agent", "exec_123")
        
        # Test different log levels
        agent_logger.debug("Debug message")
        agent_logger.info("Info message")
        agent_logger.warning("Warning message")
        agent_logger.error("Error message")
        
        assert True  # If no exception is raised, test passes

class TestExecutionLogging:
    """Tests for execution logging."""
    
    def test_log_agent_execution_success(self):
        """Test logging successful agent execution."""
        logger = setup_logging(log_level="INFO")
        
        # Test that log_agent_execution doesn't raise exceptions
        try:
            log_agent_execution(
                logger, "test_agent", "exec_123", "completed",
                items_processed=10, items_successful=8, items_failed=2,
                duration_seconds=5.0
            )
            assert True  # No exception raised
        except Exception as e:
            pytest.fail(f"log_agent_execution raised exception: {e}")
    
    def test_log_agent_execution_failure(self):
        """Test logging failed agent execution."""
        logger = setup_logging(log_level="INFO")
        
        try:
            log_agent_execution(
                logger, "test_agent", "exec_123", "failed",
                items_processed=10, items_successful=5, items_failed=5,
                duration_seconds=3.0, error_message="Test error"
            )
            assert True  # No exception raised
        except Exception as e:
            pytest.fail(f"log_agent_execution raised exception: {e}")
    
    def test_log_agent_execution_running(self):
        """Test logging running agent execution."""
        logger = setup_logging(log_level="INFO")
        
        try:
            log_agent_execution(
                logger, "test_agent", "exec_123", "running",
                items_processed=5, items_successful=5, items_failed=0,
                duration_seconds=2.0
            )
            assert True  # No exception raised
        except Exception as e:
            pytest.fail(f"log_agent_execution raised exception: {e}")
    
    def test_log_agent_execution_minimal(self):
        """Test logging with minimal parameters."""
        logger = setup_logging(log_level="INFO")
        
        try:
            log_agent_execution(
                logger, "test_agent", "exec_123", "completed"
            )
            assert True  # No exception raised
        except Exception as e:
            pytest.fail(f"log_agent_execution raised exception: {e}")

class TestLoggingConfiguration:
    """Tests for logging configuration."""
    
    def test_logging_with_different_levels(self):
        """Test logging setup with different log levels."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in levels:
            logger = setup_logging(log_level=level)
            assert logger is not None
            assert logger.level <= getattr(logging, level)
    
    def test_logging_console_output(self):
        """Test that logging outputs to console."""
        logger = setup_logging(log_level="INFO")
        
        # Test that we can log without errors
        logger.info("Console test message")
        assert True  # If no exception is raised, test passes
    
    def test_logging_structured_output(self):
        """Test structured logging output."""
        logger = setup_logging(log_level="INFO", structured=True)
        
        # Test structured logging
        logger.info("Structured message", extra={
            "agent": "test_agent",
            "execution_id": "exec_123",
            "status": "running",
            "items_processed": 10
        })
        assert True  # If no exception is raised, test passes

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
