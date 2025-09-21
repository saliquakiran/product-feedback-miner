#!/usr/bin/env python3
"""
Backend Orchestration Example for Product Feedback Miner.

This script demonstrates how to use the backend-only AI orchestration
pipeline programmatically.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

from orchestration.workflow import WorkflowEngine
from orchestration.scheduler import PipelineScheduler
from orchestration.state import StateManager
from database import get_session
from database.models import ProcessedDocument

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demonstrate_workflow_execution():
    """Demonstrate workflow execution."""
    print("🔄 Demonstrating Workflow Execution")
    print("=" * 50)
    
    # Initialize workflow engine
    workflow_engine = WorkflowEngine()
    
    # List available workflows
    workflows = workflow_engine.get_available_workflows()
    print(f"Available workflows: {workflows}")
    
    # Execute a workflow
    print("\n🚀 Executing 'quick_processing' workflow...")
    execution = await workflow_engine.execute_workflow(
        workflow_name="quick_processing",
        config={
            "test_mode": True,
            "max_items": 5,
            "debug": True
        }
    )
    
    print(f"✅ Workflow started with execution ID: {execution.execution_id}")
    
    # Monitor execution
    print("\n📊 Monitoring execution progress...")
    while True:
        status = await workflow_engine.get_workflow_status(execution.execution_id)
        print(f"Status: {status.status} - Progress: {status.progress:.1f}% - Steps: {status.steps_completed}/{status.steps_total}")
        
        if status.status in ['completed', 'failed', 'cancelled']:
            break
        
        await asyncio.sleep(2)
    
    print(f"🏁 Workflow {status.status}!")
    if status.error_message:
        print(f"Error: {status.error_message}")

async def demonstrate_agent_management():
    """Demonstrate agent management."""
    print("\n🤖 Demonstrating Agent Management")
    print("=" * 50)
    
    # Initialize workflow engine
    workflow_engine = WorkflowEngine()
    
    # Get agent health
    agent_health = await workflow_engine.get_agent_health()
    print("Agent Health Status:")
    for agent_name, health in agent_health.items():
        status_icon = "✅" if health["status"] == "healthy" else "❌"
        print(f"  {status_icon} {agent_name}: {health['status']} - {health['message']}")
    
    # Get workflow metrics
    metrics = await workflow_engine.get_workflow_metrics()
    print(f"\nWorkflow Metrics: {json.dumps(metrics, indent=2)}")

async def demonstrate_scheduler():
    """Demonstrate scheduler functionality."""
    print("\n⏰ Demonstrating Scheduler")
    print("=" * 50)
    
    # Initialize scheduler
    workflow_engine = WorkflowEngine()
    scheduler = PipelineScheduler(workflow_engine)
    
    try:
        # Start scheduler
        await scheduler.start()
        print("✅ Scheduler started")
        
        # Get scheduler metrics
        metrics = await scheduler.get_scheduler_metrics()
        print(f"Scheduler Metrics: {json.dumps(metrics, indent=2)}")
        
        # Create a scheduled job (example)
        print("\n📅 Creating scheduled job...")
        job_config = {
            "name": "Daily Feedback Processing",
            "description": "Process feedback daily at 9 AM",
            "workflow_name": "feedback_processing",
            "schedule_type": "cron",
            "schedule_value": "0 9 * * *",
            "timezone": "UTC",
            "enabled": True,
            "config": {"max_items": 100}
        }
        
        # This would create a job in a real implementation
        print(f"Job configuration: {json.dumps(job_config, indent=2)}")
        
    finally:
        # Stop scheduler
        await scheduler.stop()
        print("✅ Scheduler stopped")

async def demonstrate_state_management():
    """Demonstrate state management."""
    print("\n🗄️ Demonstrating State Management")
    print("=" * 50)
    
    # Initialize state manager
    state_manager = StateManager()
    
    try:
        # Start state manager
        await state_manager.start_cleanup_task()
        print("✅ State manager started")
        
        # Store some state
        print("\n💾 Storing pipeline state...")
        pipeline_state = {
            "current_step": "classifier",
            "processed_items": 42,
            "errors": [],
            "metadata": {"start_time": datetime.utcnow().isoformat()}
        }
        
        await state_manager.store_state(
            state_type="pipeline",
            state_id="demo_pipeline_123",
            state_data=pipeline_state,
            ttl=3600
        )
        print("✅ Pipeline state stored")
        
        # Retrieve state
        print("\n📖 Retrieving pipeline state...")
        retrieved_state = await state_manager.get_state("pipeline", "demo_pipeline_123")
        if retrieved_state:
            print(f"Retrieved state: {json.dumps(retrieved_state.data, indent=2)}")
        else:
            print("❌ State not found")
        
        # Get state metrics
        metrics = await state_manager.get_state_metrics()
        print(f"\nState Manager Metrics: {json.dumps(metrics, indent=2)}")
        
    finally:
        # Shutdown state manager
        await state_manager.shutdown()
        print("✅ State manager stopped")

async def demonstrate_database_operations():
    """Demonstrate database operations."""
    print("\n💾 Demonstrating Database Operations")
    print("=" * 50)
    
    try:
        with get_session() as session:
            # Count feedback items
            feedback_count = session.query(ProcessedDocument).count()
            print(f"Total feedback items: {feedback_count}")
            
            # Get recent feedback
            recent_feedback = session.query(ProcessedDocument).order_by(
                ProcessedDocument.created_at.desc()
            ).limit(5).all()
            
            print(f"\nRecent feedback items ({len(recent_feedback)}):")
            for item in recent_feedback:
                print(f"  ID: {item.id}")
                print(f"  Title: {item.title or 'Untitled'}")
                print(f"  Type: {item.feedback_type.value if item.feedback_type else 'unknown'}")
                print(f"  Created: {item.created_at}")
                print("  ---")
                
    except Exception as e:
        print(f"❌ Database error: {e}")

async def demonstrate_api_integration():
    """Demonstrate API integration."""
    print("\n🌐 Demonstrating API Integration")
    print("=" * 50)
    
    # This would demonstrate how to use the API programmatically
    print("API endpoints available:")
    print("  GET  /health - System health check")
    print("  GET  /metrics - System metrics")
    print("  POST /workflows/execute - Execute workflow")
    print("  GET  /workflows/{id}/status - Get workflow status")
    print("  GET  /agents/status - Get agent status")
    print("  GET  /feedback - List feedback items")
    print("  POST /api/v1/search - Search feedback")
    
    print("\nExample API usage:")
    print("  curl http://localhost:8000/health")
    print("  curl -X POST http://localhost:8000/workflows/execute \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"workflow_name\": \"quick_processing\"}'")

async def main():
    """Main demonstration function."""
    print("🚀 Product Feedback Miner - Backend Orchestration Demo")
    print("=" * 60)
    print("This demo shows how to use the backend-only AI orchestration pipeline")
    print("=" * 60)
    
    try:
        # Demonstrate workflow execution
        await demonstrate_workflow_execution()
        
        # Demonstrate agent management
        await demonstrate_agent_management()
        
        # Demonstrate scheduler
        await demonstrate_scheduler()
        
        # Demonstrate state management
        await demonstrate_state_management()
        
        # Demonstrate database operations
        await demonstrate_database_operations()
        
        # Demonstrate API integration
        await demonstrate_api_integration()
        
        print("\n✅ Demo completed successfully!")
        print("\nNext steps:")
        print("  1. Start the API server: python cli.py serve")
        print("  2. Run monitoring: python monitor.py")
        print("  3. Execute workflows: python cli.py execute --workflow quick_processing")
        print("  4. Check system health: python cli.py health")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        logger.exception("Demo error")

if __name__ == "__main__":
    asyncio.run(main())

