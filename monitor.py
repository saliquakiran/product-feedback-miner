#!/usr/bin/env python3
"""
Monitoring script for Product Feedback Miner.

This script provides real-time monitoring capabilities for the
backend-only AI orchestration pipeline.
"""

import asyncio
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any

from orchestration.workflow import WorkflowEngine
from orchestration.scheduler import PipelineScheduler
from orchestration.state import StateManager
from database import get_session
from database.models import ProcessedDocument, Cluster, Ticket

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemMonitor:
    """System monitor for the Product Feedback Miner."""
    
    def __init__(self):
        self.workflow_engine = WorkflowEngine()
        self.scheduler = PipelineScheduler(self.workflow_engine)
        self.state_manager = StateManager()
        self.running = False
    
    async def start(self):
        """Start the monitoring system."""
        self.running = True
        logger.info("🔍 Starting system monitor...")
        
        # Start scheduler
        await self.scheduler.start()
        
        # Start state manager
        await self.state_manager.start_cleanup_task()
        
        logger.info("✅ System monitor started")
    
    async def stop(self):
        """Stop the monitoring system."""
        self.running = False
        logger.info("🛑 Stopping system monitor...")
        
        # Stop scheduler
        await self.scheduler.stop()
        
        # Stop state manager
        await self.state_manager.shutdown()
        
        logger.info("✅ System monitor stopped")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        try:
            # Get agent health
            agent_health = await self.workflow_engine.get_agent_health()
            healthy_agents = sum(1 for h in agent_health.values() if h["status"] == "healthy")
            total_agents = len(agent_health)
            
            # Get workflow metrics
            workflow_metrics = await self.workflow_engine.get_workflow_metrics()
            
            # Get scheduler metrics
            scheduler_metrics = await self.scheduler.get_scheduler_metrics()
            
            # Get state metrics
            state_metrics = await self.state_manager.get_state_metrics()
            
            # Get database metrics
            with get_session() as session:
                feedback_count = session.query(ProcessedDocument).count()
                cluster_count = session.query(Cluster).count()
                ticket_count = session.query(Ticket).count()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "healthy" if healthy_agents == total_agents else "degraded",
                "agents": {
                    "total": total_agents,
                    "healthy": healthy_agents,
                    "unhealthy": total_agents - healthy_agents,
                    "details": agent_health
                },
                "workflows": workflow_metrics,
                "scheduler": scheduler_metrics,
                "state": state_metrics,
                "database": {
                    "feedback_items": feedback_count,
                    "clusters": cluster_count,
                    "tickets": ticket_count
                }
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    async def print_status(self):
        """Print formatted system status."""
        status = await self.get_system_status()
        
        print("\n" + "="*60)
        print(f"🏥 Product Feedback Miner - System Status")
        print(f"⏰ {status['timestamp']}")
        print("="*60)
        
        # Overall status
        status_icon = "✅" if status["status"] == "healthy" else "⚠️" if status["status"] == "degraded" else "❌"
        print(f"{status_icon} Overall Status: {status['status'].upper()}")
        
        # Agent status
        agents = status["agents"]
        print(f"\n🤖 Agents: {agents['healthy']}/{agents['total']} healthy")
        for agent_name, health in agents["details"].items():
            agent_icon = "✅" if health["status"] == "healthy" else "❌"
            print(f"  {agent_icon} {agent_name}: {health['status']} - {health['message']}")
        
        # Database metrics
        db = status["database"]
        print(f"\n💾 Database:")
        print(f"  📝 Feedback items: {db['feedback_items']:,}")
        print(f"  🔗 Clusters: {db['clusters']:,}")
        print(f"  🎫 Tickets: {db['tickets']:,}")
        
        # Workflow metrics
        workflows = status["workflows"]
        if workflows:
            print(f"\n🔄 Workflows:")
            for key, value in workflows.items():
                print(f"  {key}: {value}")
        
        # Scheduler metrics
        scheduler = status["scheduler"]
        if scheduler:
            print(f"\n⏰ Scheduler:")
            for key, value in scheduler.items():
                print(f"  {key}: {value}")
        
        # State metrics
        state = status["state"]
        if state:
            print(f"\n🗄️ State Manager:")
            for key, value in state.items():
                print(f"  {key}: {value}")
        
        print("="*60)
    
    async def monitor_loop(self, interval: int = 30):
        """Run monitoring loop."""
        logger.info(f"🔄 Starting monitoring loop (interval: {interval}s)")
        
        try:
            while self.running:
                await self.print_status()
                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            logger.info("🛑 Monitoring interrupted by user")
        except Exception as e:
            logger.error(f"❌ Monitoring error: {e}")
        finally:
            await self.stop()

async def main():
    """Main monitoring function."""
    monitor = SystemMonitor()
    
    try:
        await monitor.start()
        await monitor.monitor_loop(interval=30)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        await monitor.stop()

if __name__ == "__main__":
    asyncio.run(main())

