#!/usr/bin/env python3
"""
Example script demonstrating the Workflow Engine functionality.

This script shows how to:
1. Initialize the Workflow Engine and its components
2. Execute different types of workflows
3. Manage scheduled jobs and automation
4. Handle state management and coordination
5. Monitor workflow health and performance
6. Handle errors and recovery

Run this script to see the Workflow Engine in action.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import uuid

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestration.workflow import WorkflowEngine, WorkflowStatus, WorkflowConfig
from orchestration.scheduler import PipelineScheduler, ScheduleType, JobStatus
from orchestration.state import StateManager, StateType, StateStatus

async def main():
    """Main example function."""
    print("🔄 Workflow Engine Example")
    print("=" * 50)
    
    # Configuration for the Workflow Engine
    workflow_config = {
        "max_concurrent_agents": 3,
        "default_timeout": 300,  # 5 minutes
        "retry_delay": 30,  # 30 seconds
        "enable_parallel_execution": True,
        "enable_error_recovery": True,
        "enable_monitoring": True,
        "log_level": "INFO",
        "save_execution_history": True
    }
    
    # Initialize the Workflow Engine
    print("🔄 Initializing Workflow Engine...")
    workflow_engine = WorkflowEngine(workflow_config)
    
    print(f"✅ Workflow Engine initialized")
    print(f"📊 Max concurrent agents: {workflow_engine.config.max_concurrent_agents}")
    print(f"⏱️ Default timeout: {workflow_engine.config.default_timeout}s")
    print(f"🔄 Retry delay: {workflow_engine.config.retry_delay}s")
    print(f"🚀 Parallel execution: {workflow_engine.config.enable_parallel_execution}")
    print(f"🛡️ Error recovery: {workflow_engine.config.enable_error_recovery}")
    print()
    
    # Show available workflows
    print("📋 Available workflows:")
    workflows = workflow_engine.get_available_workflows()
    for i, workflow_name in enumerate(workflows, 1):
        definition = workflow_engine.get_workflow_definition(workflow_name)
        step_count = len(definition) if definition else 0
        print(f"  {i}. {workflow_name} ({step_count} steps)")
    print()
    
    # Demonstrate workflow execution
    print("🚀 Demonstrating workflow execution...")
    
    # Show workflow definitions
    print("📋 Workflow Definitions:")
    for workflow_name in workflows:
        definition = workflow_engine.get_workflow_definition(workflow_name)
        if definition:
            print(f"\n  🔄 {workflow_name}:")
            for i, step in enumerate(definition, 1):
                deps = f" (depends on: {', '.join(step.dependencies)})" if step.dependencies else ""
                timeout = f" (timeout: {step.timeout}s)" if step.timeout else ""
                print(f"    {i}. {step.agent_name}{deps}{timeout}")
    print()
    
    # Demonstrate state management
    print("💾 Demonstrating state management...")
    
    # Initialize state manager
    state_config = {
        "default_ttl": 3600,  # 1 hour
        "cleanup_interval": 300,  # 5 minutes
        "max_state_size": 10 * 1024 * 1024  # 10MB
    }
    state_manager = StateManager(state_config)
    
    print(f"✅ State Manager initialized")
    print(f"⏰ Default TTL: {state_config['default_ttl']}s")
    print(f"🧹 Cleanup interval: {state_config['cleanup_interval']}s")
    print(f"📦 Max state size: {state_config['max_state_size'] / (1024*1024):.1f}MB")
    print()
    
    # Demonstrate state operations
    print("💾 State Operations:")
    
    # Set some states
    await state_manager.set_state(
        key="workflow_config",
        value={"max_concurrent": 3, "timeout": 300},
        state_type=StateType.WORKFLOW,
        ttl=3600
    )
    
    await state_manager.set_state(
        key="agent_status",
        value={"ingestor": "running", "classifier": "completed"},
        state_type=StateType.AGENT,
        ttl=1800
    )
    
    await state_manager.set_state(
        key="pipeline_metrics",
        value={"total_processed": 1000, "success_rate": 0.95},
        state_type=StateType.PIPELINE,
        ttl=7200
    )
    
    print("  ✅ Set 3 states with different types and TTLs")
    
    # Get states
    workflow_config = await state_manager.get_state("workflow_config", StateType.WORKFLOW)
    agent_status = await state_manager.get_state("agent_status", StateType.AGENT)
    pipeline_metrics = await state_manager.get_state("pipeline_metrics", StateType.PIPELINE)
    
    print(f"  📊 Workflow config: {workflow_config}")
    print(f"  🤖 Agent status: {agent_status}")
    print(f"  📈 Pipeline metrics: {pipeline_metrics}")
    
    # List states
    all_states = await state_manager.list_states()
    workflow_states = await state_manager.list_states(state_type=StateType.WORKFLOW)
    agent_states = await state_manager.list_states(state_type=StateType.AGENT)
    
    print(f"  📋 Total states: {len(all_states)}")
    print(f"  🔄 Workflow states: {len(workflow_states)}")
    print(f"  🤖 Agent states: {len(agent_states)}")
    print()
    
    # Demonstrate pipeline state management
    print("🔄 Pipeline State Management:")
    
    # Set pipeline state
    await state_manager.set_pipeline_state(
        execution_id="demo_execution_001",
        workflow_name="feedback_processing",
        current_step="classifier",
        completed_steps=["ingestor", "normalizer"],
        failed_steps=[],
        step_results={
            "ingestor": {"items_processed": 100, "success": True},
            "normalizer": {"items_processed": 95, "success": True}
        },
        data_flow={
            "raw_feedback": 100,
            "processed_feedback": 95,
            "classified_feedback": 0
        },
        status="running"
    )
    
    print("  ✅ Set pipeline state for demo execution")
    
    # Get pipeline state
    pipeline_state = await state_manager.get_pipeline_state("demo_execution_001")
    if pipeline_state:
        print(f"  📊 Execution ID: {pipeline_state.execution_id}")
        print(f"  🔄 Workflow: {pipeline_state.workflow_name}")
        print(f"  📍 Current step: {pipeline_state.current_step}")
        print(f"  ✅ Completed steps: {pipeline_state.completed_steps}")
        print(f"  ❌ Failed steps: {pipeline_state.failed_steps}")
        print(f"  📈 Data flow: {pipeline_state.data_flow}")
        print(f"  🎯 Status: {pipeline_state.status}")
    
    # Update pipeline state
    await state_manager.update_pipeline_state(
        "demo_execution_001",
        current_step="clusterer",
        completed_steps=["ingestor", "normalizer", "classifier"],
        step_results={
            "ingestor": {"items_processed": 100, "success": True},
            "normalizer": {"items_processed": 95, "success": True},
            "classifier": {"items_processed": 90, "success": True}
        },
        data_flow={
            "raw_feedback": 100,
            "processed_feedback": 95,
            "classified_feedback": 90,
            "clustered_feedback": 0
        }
    )
    
    print("  ✅ Updated pipeline state")
    print()
    
    # Demonstrate agent state management
    print("🤖 Agent State Management:")
    
    # Set agent states
    await state_manager.set_agent_state(
        agent_name="ingestor",
        execution_id="demo_execution_001",
        status="completed",
        input_data={"sources": ["github", "hackernews"]},
        output_data={"items_processed": 100, "items_successful": 100},
        processing_metrics={"execution_time": 45.2, "memory_usage": "128MB"}
    )
    
    await state_manager.set_agent_state(
        agent_name="classifier",
        execution_id="demo_execution_001",
        status="running",
        input_data={"processed_documents": 95},
        output_data={},
        processing_metrics={"execution_time": 0, "memory_usage": "64MB"}
    )
    
    print("  ✅ Set agent states for ingestor and classifier")
    
    # Get agent states
    ingestor_state = await state_manager.get_agent_state("ingestor", "demo_execution_001")
    classifier_state = await state_manager.get_agent_state("classifier", "demo_execution_001")
    
    if ingestor_state:
        print(f"  📊 Ingestor: {ingestor_state.status}")
        print(f"    • Input: {ingestor_state.input_data}")
        print(f"    • Output: {ingestor_state.output_data}")
        print(f"    • Metrics: {ingestor_state.processing_metrics}")
    
    if classifier_state:
        print(f"  📊 Classifier: {classifier_state.status}")
        print(f"    • Input: {classifier_state.input_data}")
        print(f"    • Output: {classifier_state.output_data}")
        print(f"    • Metrics: {classifier_state.processing_metrics}")
    print()
    
    # Demonstrate lock management
    print("🔒 Lock Management:")
    
    # Acquire locks
    lock1_acquired = await state_manager.acquire_lock("critical_section_1", timeout=5)
    lock2_acquired = await state_manager.acquire_lock("critical_section_2", timeout=5)
    lock1_duplicate = await state_manager.acquire_lock("critical_section_1", timeout=1)
    
    print(f"  🔒 Lock 1 acquired: {lock1_acquired}")
    print(f"  🔒 Lock 2 acquired: {lock2_acquired}")
    print(f"  🔒 Lock 1 duplicate: {lock1_duplicate} (should be False)")
    
    # Release locks
    lock1_released = await state_manager.release_lock("critical_section_1")
    lock2_released = await state_manager.release_lock("critical_section_2")
    
    print(f"  🔓 Lock 1 released: {lock1_released}")
    print(f"  🔓 Lock 2 released: {lock2_released}")
    print()
    
    # Demonstrate scheduler
    print("⏰ Pipeline Scheduler:")
    
    # Initialize scheduler
    scheduler = PipelineScheduler(workflow_engine)
    
    print(f"  ✅ Scheduler initialized")
    print(f"  📊 Scheduled jobs: {len(scheduler.scheduled_jobs)}")
    print(f"  🚀 Active executions: {len(scheduler.active_executions)}")
    print(f"  📈 Execution history: {len(scheduler.execution_history)}")
    print()
    
    # Create scheduled jobs
    print("📅 Creating scheduled jobs:")
    
    # Daily feedback processing job
    daily_job_id = await scheduler.create_scheduled_job(
        name="Daily Feedback Processing",
        description="Process all feedback daily at 9 AM",
        workflow_name="feedback_processing",
        schedule_type=ScheduleType.CRON,
        schedule_value="0 9 * * *",  # Daily at 9 AM
        timezone="UTC",
        enabled=True,
        max_concurrent=1,
        timeout=1800,  # 30 minutes
        config={"priority": "high", "notifications": True}
    )
    
    print(f"  ✅ Daily job created: {daily_job_id}")
    
    # Hourly quick processing job
    hourly_job_id = await scheduler.create_scheduled_job(
        name="Hourly Quick Processing",
        description="Quick processing every hour",
        workflow_name="quick_processing",
        schedule_type=ScheduleType.INTERVAL,
        schedule_value="1h",  # Every hour
        timezone="UTC",
        enabled=True,
        max_concurrent=2,
        timeout=600,  # 10 minutes
        config={"priority": "medium", "notifications": False}
    )
    
    print(f"  ✅ Hourly job created: {hourly_job_id}")
    
    # One-time learning job
    learning_job_id = await scheduler.create_scheduled_job(
        name="Weekly Learning Update",
        description="Update learning models weekly",
        workflow_name="learning_improvement",
        schedule_type=ScheduleType.CRON,
        schedule_value="0 2 * * 0",  # Weekly on Sunday at 2 AM
        timezone="UTC",
        enabled=True,
        max_concurrent=1,
        timeout=3600,  # 1 hour
        config={"priority": "low", "notifications": True}
    )
    
    print(f"  ✅ Learning job created: {learning_job_id}")
    print()
    
    # Show job status
    print("📊 Job Status:")
    
    for job_id, job_name in [
        (daily_job_id, "Daily Feedback Processing"),
        (hourly_job_id, "Hourly Quick Processing"),
        (learning_job_id, "Weekly Learning Update")
    ]:
        status = await scheduler.get_job_status(job_id)
        if status:
            print(f"  📋 {job_name}:")
            print(f"    • Status: {'Enabled' if status['enabled'] else 'Disabled'}")
            print(f"    • Schedule: {status['schedule_type']} - {status['schedule_value']}")
            print(f"    • Workflow: {status['workflow_name']}")
            print(f"    • Active executions: {status['active_executions']}")
            print(f"    • Recent executions: {len(status['recent_executions'])}")
    print()
    
    # Demonstrate manual job execution
    print("🚀 Manual Job Execution:")
    
    # Run daily job manually
    execution_id = await scheduler.run_job_manually(daily_job_id)
    print(f"  ✅ Started manual execution: {execution_id}")
    
    # Show execution status
    execution = scheduler.active_executions.get(execution_id)
    if execution:
        print(f"  📊 Execution details:")
        print(f"    • Job ID: {execution.job_id}")
        print(f"    • Workflow: {execution.workflow_name}")
        print(f"    • Status: {execution.status}")
        print(f"    • Started: {execution.started_at}")
    print()
    
    # Demonstrate workflow health monitoring
    print("🏥 Workflow Health Monitoring:")
    
    # Get agent health
    agent_health = await workflow_engine.get_agent_health()
    print(f"  🤖 Agent Health Status:")
    for agent_name, health in agent_health.items():
        status_emoji = "✅" if health["status"] == "healthy" else "❌"
        print(f"    {status_emoji} {agent_name}: {health['status']} - {health['message']}")
    print()
    
    # Get workflow metrics
    workflow_metrics = await workflow_engine.get_workflow_metrics()
    print(f"  📊 Workflow Metrics:")
    print(f"    • Total executions: {workflow_metrics['total_executions']}")
    print(f"    • Successful executions: {workflow_metrics['successful_executions']}")
    print(f"    • Failed executions: {workflow_metrics['failed_executions']}")
    print(f"    • Success rate: {workflow_metrics['success_rate']:.1%}")
    print(f"    • Average duration: {workflow_metrics['average_duration']:.2f}s")
    print(f"    • Active executions: {workflow_metrics['active_executions']}")
    print()
    
    # Get scheduler metrics
    scheduler_metrics = await scheduler.get_scheduler_metrics()
    print(f"  ⏰ Scheduler Metrics:")
    print(f"    • Total jobs: {scheduler_metrics['total_jobs']}")
    print(f"    • Enabled jobs: {scheduler_metrics['enabled_jobs']}")
    print(f"    • Active executions: {scheduler_metrics['active_executions']}")
    print(f"    • Total executions: {scheduler_metrics['total_executions']}")
    print(f"    • Success rate: {scheduler_metrics['success_rate']:.1%}")
    print(f"    • Scheduler running: {scheduler_metrics['scheduler_running']}")
    print()
    
    # Get state metrics
    state_metrics = await state_manager.get_state_metrics()
    print(f"  💾 State Metrics:")
    print(f"    • Total states: {state_metrics['total_states']}")
    print(f"    • Active states: {state_metrics['active_states']}")
    print(f"    • Expired states: {state_metrics['expired_states']}")
    print(f"    • Total size: {state_metrics['total_size_mb']:.2f}MB")
    print(f"    • Pipeline states: {state_metrics['pipeline_states']}")
    print(f"    • Agent states: {state_metrics['agent_states']}")
    print(f"    • Active locks: {state_metrics['active_locks']}")
    print()
    
    # Demonstrate error handling and recovery
    print("🛡️ Error Handling and Recovery:")
    
    # Show retry configuration
    print(f"  🔄 Retry configuration:")
    print(f"    • Retry delay: {workflow_engine.config.retry_delay}s")
    print(f"    • Error recovery: {workflow_engine.config.enable_error_recovery}")
    print(f"    • Parallel execution: {workflow_engine.config.enable_parallel_execution}")
    print()
    
    # Show job update capabilities
    print("📝 Job Management:")
    
    # Update a job
    update_result = await scheduler.update_scheduled_job(
        daily_job_id,
        name="Daily Feedback Processing (Updated)",
        description="Updated description with better error handling",
        enabled=False  # Disable for demo
    )
    
    print(f"  ✅ Job update result: {update_result}")
    
    # Show updated job status
    updated_status = await scheduler.get_job_status(daily_job_id)
    if updated_status:
        print(f"  📊 Updated job status:")
        print(f"    • Name: {updated_status['name']}")
        print(f"    • Description: {updated_status['description']}")
        print(f"    • Enabled: {updated_status['enabled']}")
    print()
    
    # Demonstrate state export/import
    print("💾 State Export/Import:")
    
    # Export state
    export_data = await state_manager.export_state()
    print(f"  ✅ State exported:")
    print(f"    • States: {len(export_data['states'])}")
    print(f"    • Pipeline states: {len(export_data['pipeline_states'])}")
    print(f"    • Agent states: {len(export_data['agent_states'])}")
    print(f"    • Exported at: {export_data['exported_at']}")
    
    # Import state (simulate)
    print(f"  📥 State import capability: Available")
    print()
    
    # Demonstrate cleanup
    print("🧹 Cleanup Operations:")
    
    # Cleanup expired states
    cleaned_count = await state_manager.cleanup_expired_states()
    print(f"  🧹 Cleaned up {cleaned_count} expired states")
    
    # Show final metrics
    final_metrics = await state_manager.get_state_metrics()
    print(f"  📊 Final state metrics:")
    print(f"    • Total states: {final_metrics['total_states']}")
    print(f"    • Active states: {final_metrics['active_states']}")
    print(f"    • Expired states: {final_metrics['expired_states']}")
    print()
    
    # Demonstrate shutdown
    print("🔄 Shutdown Operations:")
    
    # Cancel active executions
    if execution_id in scheduler.active_executions:
        cancel_result = await scheduler.cancel_job_execution(execution_id)
        print(f"  🛑 Cancelled execution: {cancel_result}")
    
    # Shutdown components
    await scheduler.stop()
    print(f"  🛑 Scheduler stopped")
    
    await state_manager.shutdown()
    print(f"  🛑 State manager shutdown")
    
    await workflow_engine.shutdown()
    print(f"  🛑 Workflow engine shutdown")
    print()
    
    print("✅ Workflow Engine example completed!")
    print()
    print("💡 Key capabilities demonstrated:")
    print("  1. 🔄 Workflow orchestration and execution")
    print("  2. ⏰ Automated scheduling with cron and intervals")
    print("  3. 💾 Comprehensive state management")
    print("  4. 🤖 Agent coordination and health monitoring")
    print("  5. 🛡️ Error handling and recovery")
    print("  6. 📊 Performance monitoring and metrics")
    print("  7. 🔒 Concurrency control with locks")
    print("  8. 🧹 Automatic cleanup and maintenance")
    print()
    print("🚀 Next steps:")
    print("  1. Configure your specific workflows and schedules")
    print("  2. Set up monitoring and alerting")
    print("  3. Implement custom error handling strategies")
    print("  4. Scale the system based on your needs")
    print("  5. Monitor performance and optimize as needed")

if __name__ == "__main__":
    # Run the example
    asyncio.run(main())

