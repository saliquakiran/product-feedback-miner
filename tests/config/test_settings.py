#!/usr/bin/env python3
"""
Tests for configuration system.

This module tests the configuration loading and validation:
- Default configuration values
- Environment variable parsing
- Configuration dataclasses
"""

import pytest
import os
from unittest.mock import patch

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import load_config, AppConfig, DatabaseConfig, AgentConfig

class TestConfigurationLoading:
    """Tests for configuration loading."""
    
    def test_config_loading_with_defaults(self):
        """Test configuration loading with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()
            
            assert config.environment.value == "development"
            assert config.debug is False
            assert config.database.host == "localhost"
            assert config.database.port == 5432
            assert config.database.database == "product_feedback_miner"
    
    def test_config_loading_with_environment_variables(self):
        """Test configuration loading with environment variables."""
        env_vars = {
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "DATABASE_HOST": "prod-db.example.com",
            "DATABASE_PORT": "5433",
            "DATABASE_NAME": "prod_feedback_miner",
            "INGESTOR_INTERVAL_MINUTES": "5",
            "CLUSTERER_SIMILARITY_THRESHOLD": "0.9"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config()
            
            assert config.environment.value == "production"
            assert config.debug is True
            assert config.database.host == "prod-db.example.com"
            assert config.database.port == 5433
            assert config.agents.ingestor_interval_minutes == 5
            assert config.agents.clusterer_similarity_threshold == 0.9
    
    def test_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        test_cases = [
            ("true", True),
            ("false", False)
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"DEBUG": env_value}, clear=True):
                config = load_config()
                assert config.debug == expected

class TestDatabaseConfig:
    """Tests for DatabaseConfig dataclass."""
    
    def test_database_config_creation(self):
        """Test DatabaseConfig dataclass creation."""
        db_config = DatabaseConfig(
            host="test-host",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass",
            pool_size=20,
            max_overflow=30,
            echo=True
        )
        
        assert db_config.host == "test-host"
        assert db_config.port == 5432
        assert db_config.database == "test_db"
        assert db_config.username == "test_user"
        assert db_config.password == "test_pass"
        assert db_config.pool_size == 20
        assert db_config.max_overflow == 30
        assert db_config.echo is True
    
    def test_database_config_defaults(self):
        """Test DatabaseConfig with default values."""
        db_config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="user",
            password="pass"
        )
        
        assert db_config.pool_size == 10  # Default value
        assert db_config.max_overflow == 20  # Default value
        assert db_config.echo is False  # Default value

class TestAgentConfig:
    """Tests for AgentConfig dataclass."""
    
    def test_agent_config_creation(self):
        """Test AgentConfig dataclass creation."""
        agent_config = AgentConfig(
            ingestor_interval_minutes=15,
            ingestor_batch_size=200,
            clusterer_similarity_threshold=0.85,
            prioritizer_weights={
                "severity": 0.4,
                "reach": 0.3,
                "recency": 0.2,
                "persona_weight": 0.1
            }
        )
        
        assert agent_config.ingestor_interval_minutes == 15
        assert agent_config.ingestor_batch_size == 200
        assert agent_config.clusterer_similarity_threshold == 0.85
        assert agent_config.prioritizer_weights["severity"] == 0.4
        assert agent_config.prioritizer_weights["reach"] == 0.3
        assert agent_config.prioritizer_weights["recency"] == 0.2
        assert agent_config.prioritizer_weights["persona_weight"] == 0.1
    
    def test_agent_config_defaults(self):
        """Test AgentConfig with default values."""
        agent_config = AgentConfig()
        
        # Test that default values are set correctly
        assert agent_config.ingestor_interval_minutes == 10
        assert agent_config.ingestor_batch_size == 100
        assert agent_config.clusterer_similarity_threshold == 0.8

class TestAppConfig:
    """Tests for AppConfig dataclass."""
    
    def test_app_config_creation(self):
        """Test AppConfig dataclass creation."""
        from config.settings import Environment
        
        app_config = AppConfig(
            environment=Environment.DEVELOPMENT,
            debug=True,
            database=DatabaseConfig(
                host="localhost",
                port=5432,
                database="test_db",
                username="user",
                password="pass"
            )
        )
        
        assert app_config.environment == Environment.DEVELOPMENT
        assert app_config.debug is True
        assert app_config.database.host == "localhost"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
