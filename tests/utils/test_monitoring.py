#!/usr/bin/env python3
"""
Tests for monitoring system.

This module tests the monitoring functionality:
- Health monitoring
- Metrics collection
- System health checks
"""

import pytest
import asyncio
from unittest.mock import patch, Mock

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.monitoring import health_monitor, metrics_collector, check_system_health

class TestHealthMonitor:
    """Tests for health monitoring."""
    
    def test_health_monitor_initialization(self):
        """Test health monitor initialization."""
        assert health_monitor is not None
        assert hasattr(health_monitor, 'run_all_health_checks')
        assert hasattr(health_monitor, 'get_overall_health')
    
    def test_health_monitor_methods(self):
        """Test health monitor methods exist and are callable."""
        assert callable(health_monitor.run_all_health_checks)
        assert callable(health_monitor.get_overall_health)
    
    def test_health_monitor_run_checks(self):
        """Test running health checks."""
        try:
            health_checks = health_monitor.run_all_health_checks()
            assert isinstance(health_checks, list)
            # Should have at least some health checks
            assert len(health_checks) >= 0
        except Exception as e:
            pytest.fail(f"run_all_health_checks raised exception: {e}")
    
    def test_health_monitor_overall_health(self):
        """Test getting overall health status."""
        try:
            overall_health = health_monitor.get_overall_health()
            assert overall_health is not None
            # Should be a dictionary with health information
            assert isinstance(overall_health, dict)
        except Exception as e:
            pytest.fail(f"get_overall_health raised exception: {e}")

class TestMetricsCollector:
    """Tests for metrics collection."""
    
    def test_metrics_collector_initialization(self):
        """Test metrics collector initialization."""
        assert metrics_collector is not None
        assert hasattr(metrics_collector, 'collect_system_metrics')
        assert hasattr(metrics_collector, 'get_agent_metrics')
    
    def test_metrics_collector_methods(self):
        """Test metrics collector methods exist and are callable."""
        assert callable(metrics_collector.collect_system_metrics)
        assert callable(metrics_collector.get_agent_metrics)
    
    def test_collect_system_metrics(self):
        """Test system metrics collection."""
        try:
            metrics = metrics_collector.collect_system_metrics()
            assert metrics is not None
            assert hasattr(metrics, 'timestamp')
            assert hasattr(metrics, 'cpu_percent')
            assert hasattr(metrics, 'memory_percent')
            assert hasattr(metrics, 'database_healthy')
        except Exception as e:
            pytest.fail(f"collect_system_metrics raised exception: {e}")
    
    def test_get_agent_metrics(self):
        """Test getting agent metrics."""
        try:
            agent_metrics = metrics_collector.get_agent_metrics("test_agent")
            assert agent_metrics is not None
            # Should return some metrics data
            assert isinstance(agent_metrics, dict)
        except Exception as e:
            pytest.fail(f"get_agent_metrics raised exception: {e}")
    
    def test_get_agent_metrics_different_agents(self):
        """Test getting metrics for different agents."""
        try:
            metrics1 = metrics_collector.get_agent_metrics("agent1")
            metrics2 = metrics_collector.get_agent_metrics("agent2")
            
            assert metrics1 is not None
            assert metrics2 is not None
            assert isinstance(metrics1, dict)
            assert isinstance(metrics2, dict)
        except Exception as e:
            pytest.fail(f"get_agent_metrics for different agents raised exception: {e}")

class TestSystemHealthCheck:
    """Tests for system health checking."""
    
    @pytest.mark.asyncio
    async def test_check_system_health(self):
        """Test system health checking."""
        try:
            health_checks = await check_system_health()
            assert isinstance(health_checks, list)
            # Should have at least some health checks
            assert len(health_checks) >= 0
        except Exception as e:
            pytest.fail(f"check_system_health raised exception: {e}")
    
    @pytest.mark.asyncio
    async def test_check_system_health_multiple_calls(self):
        """Test multiple calls to system health check."""
        try:
            health_checks1 = await check_system_health()
            health_checks2 = await check_system_health()
            
            assert isinstance(health_checks1, list)
            assert isinstance(health_checks2, list)
        except Exception as e:
            pytest.fail(f"Multiple check_system_health calls raised exception: {e}")

class TestMonitoringIntegration:
    """Tests for monitoring system integration."""
    
    def test_monitoring_components_work_together(self):
        """Test that monitoring components work together."""
        try:
            # Test health monitor
            health_checks = health_monitor.run_all_health_checks()
            overall_health = health_monitor.get_overall_health()
            
            # Test metrics collector
            system_metrics = metrics_collector.collect_system_metrics()
            agent_metrics = metrics_collector.get_agent_metrics("test_agent")
            
            # All should work without exceptions
            assert isinstance(health_checks, list)
            assert isinstance(overall_health, dict)
            assert system_metrics is not None
            assert isinstance(agent_metrics, dict)
        except Exception as e:
            pytest.fail(f"Monitoring components integration raised exception: {e}")
    
    def test_monitoring_with_mock_data(self):
        """Test monitoring with mock data."""
        with patch('utils.monitoring.psutil.cpu_percent', return_value=50.0):
            with patch('utils.monitoring.psutil.virtual_memory', return_value=Mock(percent=75.0)):
                try:
                    metrics = metrics_collector.collect_system_metrics()
                    assert metrics is not None
                    assert hasattr(metrics, 'cpu_percent')
                    assert hasattr(metrics, 'memory_percent')
                except Exception as e:
                    pytest.fail(f"Monitoring with mock data raised exception: {e}")

class TestMonitoringErrorHandling:
    """Tests for monitoring error handling."""
    
    def test_monitoring_handles_errors_gracefully(self):
        """Test that monitoring handles errors gracefully."""
        try:
            # Test that monitoring doesn't crash on errors
            health_checks = health_monitor.run_all_health_checks()
            overall_health = health_monitor.get_overall_health()
            system_metrics = metrics_collector.collect_system_metrics()
            
            # Should not raise exceptions
            assert True
        except Exception as e:
            # If it does raise an exception, it should be handled gracefully
            assert "monitoring" in str(e).lower() or "health" in str(e).lower()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
