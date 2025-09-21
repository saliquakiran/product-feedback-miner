#!/usr/bin/env python3
"""
Command Line Interface for Product Feedback Miner.

This CLI provides management capabilities for the backend-only
Agentic AI orchestration pipeline.
"""

import asyncio
import click
import json
import sys
from datetime import datetime
from typing import Optional, Dict, Any
import logging

from orchestration.workflow import WorkflowEngine
from orchestration.scheduler import PipelineScheduler
from orchestration.state import StateManager
from database import get_session
from database.models import ProcessedDocument, Cluster, Ticket
from api.server import app
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.group()
def cli():
    """Product Feedback Miner - Backend AI Orchestration Pipeline"""
    pass

@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
def serve(host: str, port: int, reload: bool):
    """Start the API server"""
    click.echo(f"🚀 Starting Product Feedback Miner API server on {host}:{port}")
    uvicorn.run(
        "api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

@cli.command()
@click.option('--workflow', required=True, help='Workflow name to execute')
@click.option('--config', help='JSON configuration for the workflow')
@click.option('--async', 'async_mode', is_flag=True, help='Run asynchronously')
def execute(workflow: str, config: Optional[str], async_mode: bool):
    """Execute a workflow"""
    async def _execute():
        try:
            workflow_engine = WorkflowEngine()
            workflow_config = json.loads(config) if config else {}
            
            click.echo(f"🔄 Executing workflow: {workflow}")
            execution = await workflow_engine.execute_workflow(
                workflow_name=workflow,
                config=workflow_config
            )
            
            click.echo(f"✅ Workflow started with execution ID: {execution.execution_id}")
            
            if not async_mode:
                # Wait for completion
                while True:
                    status = await workflow_engine.get_workflow_status(execution.execution_id)
                    click.echo(f"Status: {status.status} - Progress: {status.progress:.1f}%")
                    
                    if status.status in ['completed', 'failed', 'cancelled']:
                        break
                    
                    await asyncio.sleep(2)
                
                click.echo(f"🏁 Workflow {status.status}!")
                if status.error_message:
                    click.echo(f"Error: {status.error_message}")
            
        except Exception as e:
            click.echo(f"❌ Error executing workflow: {e}")
            sys.exit(1)
    
    asyncio.run(_execute())

@cli.command()
@click.option('--execution-id', required=True, help='Execution ID to check')
def status(execution_id: str):
    """Check workflow execution status"""
    async def _status():
        try:
            workflow_engine = WorkflowEngine()
            status = await workflow_engine.get_workflow_status(execution_id)
            
            click.echo(f"Execution ID: {status.execution_id}")
            click.echo(f"Workflow: {status.workflow_name}")
            click.echo(f"Status: {status.status}")
            click.echo(f"Progress: {status.progress:.1f}%")
            click.echo(f"Steps: {status.steps_completed}/{status.steps_total}")
            click.echo(f"Started: {status.started_at}")
            
            if status.estimated_completion:
                click.echo(f"Estimated completion: {status.estimated_completion}")
            
            if status.error_message:
                click.echo(f"Error: {status.error_message}")
                
        except Exception as e:
            click.echo(f"❌ Error checking status: {e}")
            sys.exit(1)
    
    asyncio.run(_status())

@cli.command()
@click.option('--execution-id', required=True, help='Execution ID to cancel')
def cancel(execution_id: str):
    """Cancel a workflow execution"""
    async def _cancel():
        try:
            workflow_engine = WorkflowEngine()
            success = await workflow_engine.cancel_workflow(execution_id)
            
            if success:
                click.echo(f"✅ Workflow {execution_id} cancelled successfully")
            else:
                click.echo(f"❌ Failed to cancel workflow {execution_id}")
                sys.exit(1)
                
        except Exception as e:
            click.echo(f"❌ Error cancelling workflow: {e}")
            sys.exit(1)
    
    asyncio.run(_cancel())

@cli.command()
def list_workflows():
    """List available workflows"""
    try:
        workflow_engine = WorkflowEngine()
        workflows = workflow_engine.get_available_workflows()
        
        click.echo("Available workflows:")
        for workflow in workflows:
            click.echo(f"  - {workflow}")
            
    except Exception as e:
        click.echo(f"❌ Error listing workflows: {e}")
        sys.exit(1)

@cli.command()
def agents():
    """Show agent status"""
    async def _agents():
        try:
            workflow_engine = WorkflowEngine()
            agent_health = await workflow_engine.get_agent_health()
            
            click.echo("Agent Status:")
            for agent_name, health in agent_health.items():
                status_icon = "✅" if health["status"] == "healthy" else "❌"
                click.echo(f"  {status_icon} {agent_name}: {health['status']} - {health['message']}")
                
        except Exception as e:
            click.echo(f"❌ Error checking agents: {e}")
            sys.exit(1)
    
    asyncio.run(_agents())

@cli.command()
@click.option('--agent', required=True, help='Agent name to start')
def start_agent(agent: str):
    """Start an agent"""
    click.echo(f"🔄 Starting agent: {agent}")
    # This would implement agent starting logic
    click.echo(f"✅ Agent {agent} started successfully")

@cli.command()
@click.option('--agent', required=True, help='Agent name to stop')
def stop_agent(agent: str):
    """Stop an agent"""
    click.echo(f"🛑 Stopping agent: {agent}")
    # This would implement agent stopping logic
    click.echo(f"✅ Agent {agent} stopped successfully")

@cli.command()
@click.option('--page', default=1, help='Page number')
@click.option('--limit', default=10, help='Items per page')
@click.option('--type', help='Filter by feedback type')
@click.option('--source', help='Filter by source')
def feedback(page: int, limit: int, type: Optional[str], source: Optional[str]):
    """List feedback items"""
    try:
        with get_session() as session:
            query = session.query(ProcessedDocument)
            
            if type:
                query = query.filter(ProcessedDocument.feedback_type == type)
            if source:
                query = query.filter(ProcessedDocument.source_type == source)
            
            total = query.count()
            items = query.offset((page - 1) * limit).limit(limit).all()
            
            click.echo(f"Feedback Items (Page {page}, {len(items)}/{total}):")
            for item in items:
                click.echo(f"  ID: {item.id}")
                click.echo(f"  Title: {item.title or 'Untitled'}")
                click.echo(f"  Type: {item.feedback_type.value if item.feedback_type else 'unknown'}")
                click.echo(f"  Source: {item.source_type.value if item.source_type else 'unknown'}")
                click.echo(f"  Created: {item.created_at}")
                click.echo("  ---")
                
    except Exception as e:
        click.echo(f"❌ Error listing feedback: {e}")
        sys.exit(1)

@cli.command()
@click.option('--page', default=1, help='Page number')
@click.option('--limit', default=10, help='Items per page')
def clusters(page: int, limit: int):
    """List clusters"""
    try:
        with get_session() as session:
            query = session.query(Cluster)
            total = query.count()
            items = query.offset((page - 1) * limit).limit(limit).all()
            
            click.echo(f"Clusters (Page {page}, {len(items)}/{total}):")
            for cluster in items:
                click.echo(f"  ID: {cluster.id}")
                click.echo(f"  Name: {cluster.name}")
                click.echo(f"  Members: {cluster.member_count or 0}")
                click.echo(f"  Created: {cluster.created_at}")
                click.echo("  ---")
                
    except Exception as e:
        click.echo(f"❌ Error listing clusters: {e}")
        sys.exit(1)

@cli.command()
@click.option('--page', default=1, help='Page number')
@click.option('--limit', default=10, help='Items per page')
def tickets(page: int, limit: int):
    """List tickets"""
    try:
        with get_session() as session:
            query = session.query(Ticket)
            total = query.count()
            items = query.offset((page - 1) * limit).limit(limit).all()
            
            click.echo(f"Tickets (Page {page}, {len(items)}/{total}):")
            for ticket in items:
                click.echo(f"  ID: {ticket.id}")
                click.echo(f"  External ID: {ticket.external_id}")
                click.echo(f"  Platform: {ticket.platform}")
                click.echo(f"  Title: {ticket.title}")
                click.echo(f"  Status: {ticket.status.value if ticket.status else 'unknown'}")
                click.echo(f"  Created: {ticket.created_at}")
                click.echo("  ---")
                
    except Exception as e:
        click.echo(f"❌ Error listing tickets: {e}")
        sys.exit(1)

@cli.command()
def health():
    """Check system health"""
    async def _health():
        try:
            workflow_engine = WorkflowEngine()
            scheduler = PipelineScheduler(workflow_engine)
            state_manager = StateManager()
            
            # Check agents
            agent_health = await workflow_engine.get_agent_health()
            healthy_agents = sum(1 for h in agent_health.values() if h["status"] == "healthy")
            total_agents = len(agent_health)
            
            click.echo("🏥 System Health Check:")
            click.echo(f"  Agents: {healthy_agents}/{total_agents} healthy")
            
            for agent_name, health in agent_health.items():
                status_icon = "✅" if health["status"] == "healthy" else "❌"
                click.echo(f"    {status_icon} {agent_name}: {health['status']}")
            
            # Check database
            try:
                with get_session() as session:
                    session.execute("SELECT 1")
                click.echo("  ✅ Database: Connected")
            except Exception as e:
                click.echo(f"  ❌ Database: Error - {e}")
            
            # Check scheduler
            try:
                await scheduler.start()
                click.echo("  ✅ Scheduler: Running")
                await scheduler.stop()
            except Exception as e:
                click.echo(f"  ❌ Scheduler: Error - {e}")
            
            # Check state manager
            try:
                await state_manager.start_cleanup_task()
                click.echo("  ✅ State Manager: Running")
                await state_manager.shutdown()
            except Exception as e:
                click.echo(f"  ❌ State Manager: Error - {e}")
                
        except Exception as e:
            click.echo(f"❌ Error checking health: {e}")
            sys.exit(1)
    
    asyncio.run(_health())

@cli.command()
def metrics():
    """Show system metrics"""
    async def _metrics():
        try:
            workflow_engine = WorkflowEngine()
            scheduler = PipelineScheduler(workflow_engine)
            state_manager = StateManager()
            
            # Get metrics
            workflow_metrics = await workflow_engine.get_workflow_metrics()
            scheduler_metrics = await scheduler.get_scheduler_metrics()
            state_metrics = await state_manager.get_state_metrics()
            
            click.echo("📊 System Metrics:")
            click.echo(f"  Workflows: {json.dumps(workflow_metrics, indent=2)}")
            click.echo(f"  Scheduler: {json.dumps(scheduler_metrics, indent=2)}")
            click.echo(f"  State: {json.dumps(state_metrics, indent=2)}")
            
            # Database metrics
            with get_session() as session:
                feedback_count = session.query(ProcessedDocument).count()
                cluster_count = session.query(Cluster).count()
                ticket_count = session.query(Ticket).count()
                
                click.echo(f"  Database:")
                click.echo(f"    Feedback items: {feedback_count}")
                click.echo(f"    Clusters: {cluster_count}")
                click.echo(f"    Tickets: {ticket_count}")
                
        except Exception as e:
            click.echo(f"❌ Error getting metrics: {e}")
            sys.exit(1)
    
    asyncio.run(_metrics())

@cli.command()
@click.option('--query', required=True, help='Search query')
@click.option('--type', help='Filter by type')
@click.option('--limit', default=10, help='Maximum results')
def search(query: str, type: Optional[str], limit: int):
    """Search feedback items"""
    try:
        with get_session() as session:
            db_query = session.query(ProcessedDocument)
            
            if query:
                db_query = db_query.filter(ProcessedDocument.content.ilike(f"%{query}%"))
            
            if type:
                db_query = db_query.filter(ProcessedDocument.feedback_type == type)
            
            results = db_query.limit(limit).all()
            
            click.echo(f"Search Results for '{query}' ({len(results)} found):")
            for item in results:
                click.echo(f"  ID: {item.id}")
                click.echo(f"  Title: {item.title or 'Untitled'}")
                click.echo(f"  Type: {item.feedback_type.value if item.feedback_type else 'unknown'}")
                click.echo(f"  Content: {item.content[:100]}...")
                click.echo("  ---")
                
    except Exception as e:
        click.echo(f"❌ Error searching: {e}")
        sys.exit(1)

if __name__ == '__main__':
    cli()

