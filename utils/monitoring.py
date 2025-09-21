"""
Monitoring and metrics collection for Product Feedback Miner.

This module provides health checks, performance metrics, and alerting
capabilities for the agent pipeline.
"""

import time
import psutil
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from database import get_session, health_check as db_health_check
from database.models import AgentExecution, SystemConfig
from config.settings import config
from config.api_keys import api_keys

logger = logging.getLogger(__name__)

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheck:
    """Health check result for a component."""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: float
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None

@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    active_connections: int
    database_healthy: bool

@dataclass
class AgentMetrics:
    """Agent performance metrics."""
    agent_name: str
    executions_last_hour: int
    avg_execution_time: float
    success_rate: float
    items_processed_last_hour: int
    last_execution: Optional[datetime]
    error_count_last_hour: int

class HealthMonitor:
    """Monitors system and component health."""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.health_checks: List[HealthCheck] = []
    
    async def check_database_health(self) -> HealthCheck:
        """Check database connectivity and performance."""
        start_time = time.time()
        
        try:
            # Test basic connectivity
            is_healthy = db_health_check()
            
            if not is_healthy:
                return HealthCheck(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message="Database connection failed",
                    response_time_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.utcnow()
                )
            
            # Test query performance
            query_start = time.time()
            with get_session() as session:
                session.execute("SELECT 1")
            query_time = (time.time() - query_start) * 1000
            
            status = HealthStatus.HEALTHY
            message = f"Database healthy (query time: {query_time:.2f}ms)"
            
            if query_time > 1000:  # Slow query
                status = HealthStatus.DEGRADED
                message = f"Database slow (query time: {query_time:.2f}ms)"
            
            return HealthCheck(
                name="database",
                status=status,
                message=message,
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.utcnow(),
                details={"query_time_ms": query_time}
            )
            
        except Exception as e:
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.utcnow()
            )
    
    async def check_api_health(self, api_name: str, test_func) -> HealthCheck:
        """Check external API health."""
        start_time = time.time()
        
        try:
            await test_func()
            return HealthCheck(
                name=f"api_{api_name}",
                status=HealthStatus.HEALTHY,
                message=f"{api_name} API is healthy",
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            return HealthCheck(
                name=f"api_{api_name}",
                status=HealthStatus.UNHEALTHY,
                message=f"{api_name} API error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.utcnow()
            )
    
    async def check_agent_health(self, agent_name: str) -> HealthCheck:
        """Check agent health based on recent executions."""
        start_time = time.time()
        
        try:
            with get_session() as session:
                # Get recent executions (last hour)
                since = datetime.utcnow() - timedelta(hours=1)
                recent_executions = session.query(AgentExecution).filter(
                    AgentExecution.agent_name == agent_name,
                    AgentExecution.started_at >= since
                ).all()
                
                if not recent_executions:
                    return HealthCheck(
                        name=f"agent_{agent_name}",
                        status=HealthStatus.UNKNOWN,
                        message=f"No recent executions for {agent_name}",
                        response_time_ms=(time.time() - start_time) * 1000,
                        timestamp=datetime.utcnow()
                    )
                
                # Calculate health metrics
                total_executions = len(recent_executions)
                successful_executions = len([e for e in recent_executions if e.status == "completed"])
                failed_executions = len([e for e in recent_executions if e.status == "failed"])
                
                success_rate = successful_executions / total_executions if total_executions > 0 else 0
                
                if success_rate >= 0.9:
                    status = HealthStatus.HEALTHY
                    message = f"{agent_name} healthy (success rate: {success_rate:.1%})"
                elif success_rate >= 0.7:
                    status = HealthStatus.DEGRADED
                    message = f"{agent_name} degraded (success rate: {success_rate:.1%})"
                else:
                    status = HealthStatus.UNHEALTHY
                    message = f"{agent_name} unhealthy (success rate: {success_rate:.1%})"
                
                return HealthCheck(
                    name=f"agent_{agent_name}",
                    status=status,
                    message=message,
                    response_time_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.utcnow(),
                    details={
                        "total_executions": total_executions,
                        "successful_executions": successful_executions,
                        "failed_executions": failed_executions,
                        "success_rate": success_rate
                    }
                )
                
        except Exception as e:
            return HealthCheck(
                name=f"agent_{agent_name}",
                status=HealthStatus.UNHEALTHY,
                message=f"Agent health check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.utcnow()
            )
    
    async def run_all_health_checks(self) -> List[HealthCheck]:
        """Run all health checks and return results."""
        checks = []
        
        # Database health check
        checks.append(await self.check_database_health())
        
        # API health checks (if configured)
        if config.exa.api_key:
            # Add Exa API health check
            async def test_exa():
                # This would be a simple test call to Exa
                pass
            checks.append(await self.check_api_health("exa", test_exa))
        
        if config.github.token:
            # Add GitHub API health check
            async def test_github():
                # This would be a simple test call to GitHub
                pass
            checks.append(await self.check_api_health("github", test_github))
        
        # Agent health checks
        agent_names = ["ingestor", "normalizer", "classifier", "clusterer", "prioritizer", "actioner", "digestor", "feedback_loop"]
        for agent_name in agent_names:
            checks.append(await self.check_agent_health(agent_name))
        
        self.health_checks = checks
        return checks
    
    def get_overall_health(self) -> HealthStatus:
        """Get overall system health status."""
        if not self.health_checks:
            return HealthStatus.UNKNOWN
        
        statuses = [check.status for check in self.health_checks]
        
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

class MetricsCollector:
    """Collects and stores system and agent metrics."""
    
    def __init__(self):
        self.metrics_history: List[SystemMetrics] = []
        self.max_history_size = 1000
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system performance metrics."""
        try:
            # CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Database connections (approximate)
            active_connections = 0
            try:
                with get_session() as session:
                    result = session.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                    active_connections = result.scalar() or 0
            except:
                pass
            
            metrics = SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                disk_usage_percent=disk.percent,
                active_connections=active_connections,
                database_healthy=db_health_check()
            )
            
            # Store in history
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history.pop(0)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                disk_usage_percent=0.0,
                active_connections=0,
                database_healthy=False
            )
    
    def get_agent_metrics(self, agent_name: str, hours: int = 1) -> AgentMetrics:
        """Get metrics for a specific agent."""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            with get_session() as session:
                executions = session.query(AgentExecution).filter(
                    AgentExecution.agent_name == agent_name,
                    AgentExecution.started_at >= since
                ).all()
                
                if not executions:
                    return AgentMetrics(
                        agent_name=agent_name,
                        executions_last_hour=0,
                        avg_execution_time=0.0,
                        success_rate=0.0,
                        items_processed_last_hour=0,
                        last_execution=None,
                        error_count_last_hour=0
                    )
                
                # Calculate metrics
                total_executions = len(executions)
                successful_executions = [e for e in executions if e.status == "completed"]
                failed_executions = [e for e in executions if e.status == "failed"]
                
                avg_execution_time = sum(e.duration_seconds or 0 for e in successful_executions) / len(successful_executions) if successful_executions else 0.0
                success_rate = len(successful_executions) / total_executions if total_executions > 0 else 0.0
                items_processed = sum(e.items_processed or 0 for e in executions)
                last_execution = max(e.started_at for e in executions)
                
                return AgentMetrics(
                    agent_name=agent_name,
                    executions_last_hour=total_executions,
                    avg_execution_time=avg_execution_time,
                    success_rate=success_rate,
                    items_processed_last_hour=items_processed,
                    last_execution=last_execution,
                    error_count_last_hour=len(failed_executions)
                )
                
        except Exception as e:
            logger.error(f"Failed to get agent metrics for {agent_name}: {e}")
            return AgentMetrics(
                agent_name=agent_name,
                executions_last_hour=0,
                avg_execution_time=0.0,
                success_rate=0.0,
                items_processed_last_hour=0,
                last_execution=None,
                error_count_last_hour=0
            )

class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self):
        self.alert_history: List[Dict[str, Any]] = []
        self.alert_cooldown = 300  # 5 minutes
    
    def should_alert(self, alert_type: str, severity: str = "high") -> bool:
        """Check if an alert should be sent based on cooldown and history."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.alert_cooldown)
        
        # Check if we've sent this alert recently
        recent_alerts = [
            alert for alert in self.alert_history
            if alert["type"] == alert_type and alert["timestamp"] > cutoff
        ]
        
        return len(recent_alerts) == 0
    
    def send_alert(self, alert_type: str, message: str, severity: str = "high", details: Dict[str, Any] = None):
        """Send an alert notification."""
        if not self.should_alert(alert_type, severity):
            return
        
        alert = {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.utcnow(),
            "details": details or {}
        }
        
        self.alert_history.append(alert)
        
        # Log the alert
        logger.error(f"ALERT [{severity.upper()}] {alert_type}: {message}", extra=alert)
        
        # Send to external systems (Slack, email, etc.)
        # This would integrate with the notification systems
        self._send_external_alert(alert)
    
    def _send_external_alert(self, alert: Dict[str, Any]):
        """Send alert to external notification systems."""
        # TODO: Implement Slack, email, or other notification methods
        pass

# Global instances
health_monitor = HealthMonitor()
metrics_collector = MetricsCollector()
alert_manager = AlertManager()

# Convenience functions
async def check_system_health() -> List[HealthCheck]:
    """Check overall system health."""
    return await health_monitor.run_all_health_checks()

def collect_metrics() -> SystemMetrics:
    """Collect current system metrics."""
    return metrics_collector.collect_system_metrics()

def get_agent_metrics(agent_name: str, hours: int = 1) -> AgentMetrics:
    """Get metrics for a specific agent."""
    return metrics_collector.get_agent_metrics(agent_name, hours)

def send_alert(alert_type: str, message: str, severity: str = "high", details: Dict[str, Any] = None):
    """Send an alert notification."""
    alert_manager.send_alert(alert_type, message, severity, details)
