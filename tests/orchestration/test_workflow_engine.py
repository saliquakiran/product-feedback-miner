"""
Tests for the Workflow Engine.

This module contains comprehensive unit and integration tests
for the Workflow Engine and its components.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import uuid

from orchestration.workflow import (
    WorkflowEngine, WorkflowStep, WorkflowExecution, WorkflowConfig,
    WorkflowStatus, AgentStatus
)
from orchestration.scheduler import (
    PipelineScheduler, ScheduleConfig, ScheduleType, JobStatus
)
from orchestration.state import (
    StateManager, StateData, StateType, StateStatus,
    PipelineState, AgentState
)
from agents.base.agent import AgentResult, AgentContext

class TestWorkflowEngine:
    """Test cases for WorkflowEngine class."""
    
    @pytest.fixture
    def workflow_engine(self):
        """Create WorkflowEngine instance for testing."""
        config = {
            "max_concurrent_agents": 2,
            "default_timeout": 60,
            "retry_delay": 5,
            "enable_parallel_execution": True,
            "enable_error_recovery": True,
            "enable_monitoring": True
        }
        return WorkflowEngine(config)
    
    @pytest.fixture
    def mock_agent_result(self):
        """Create mock agent result for testing."""
        return AgentResult(
            success=True,
            items_processed=10,
            items_successful=8,
            items_failed=2,
            execution_time=5.5,
            error_message=None,
            metadata={"test": "data"}
        )
    
    def test_initialization(self, workflow_engine):
        """Test WorkflowEngine initialization."""
        assert workflow_engine.config.max_concurrent_agents == 2
        assert workflow_engine.config.default_timeout == 60
        assert workflow_engine.config.retry_delay == 5
        assert workflow_engine.config.enable_parallel_execution is True
        assert workflow_engine.config.enable_error_recovery is True
        assert workflow_engine.config.enable_monitoring is True
        assert len(workflow_engine.agents) == 8
        assert len(workflow_engine.workflows) == 4
    
    def test_get_available_workflows(self, workflow_engine):
        """Test getting available workflows."""
        workflows = workflow_engine.get_available_workflows()
        
        assert "feedback_processing" in workflows
        assert "learning_improvement" in workflows
        assert "full_pipeline" in workflows
        assert "quick_processing" in workflows
        assert len(workflows) == 4
    
    def test_get_workflow_definition(self, workflow_engine):
        """Test getting workflow definition."""
        # Test existing workflow
        definition = workflow_engine.get_workflow_definition("feedback_processing")
        assert definition is not None
        assert len(definition) == 7
        assert definition[0].agent_name == "ingestor"
        assert definition[1].agent_name == "normalizer"
        assert definition[2].agent_name == "classifier"
        
        # Test non-existing workflow
        definition = workflow_engine.get_workflow_definition("nonexistent")
        assert definition is None
    
    @pytest.mark.asyncio
    async def test_execute_workflow_success(self, workflow_engine, mock_agent_result):
        """Test successful workflow execution."""
        # Mock agent instances
        mock_agent = Mock()
        mock_agent.process = AsyncMock(return_value=mock_agent_result)
        
        with patch.object(workflow_engine, '_get_agent_instance', return_value=mock_agent):
            # Execute quick processing workflow
            result = await workflow_engine.execute_workflow("quick_processing")
            
            assert result.status == WorkflowStatus.COMPLETED
            assert result.steps_completed == 5
            assert result.steps_failed == 0
            assert result.total_duration > 0
            assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_execute_workflow_failure(self, workflow_engine):
        """Test workflow execution with failure."""
        # Mock agent that fails
        mock_agent = Mock()
        mock_agent.process = AsyncMock(side_effect=Exception("Agent failed"))
        
        with patch.object(workflow_engine, '_get_agent_instance', return_value=mock_agent):
            # Execute quick processing workflow
            result = await workflow_engine.execute_workflow("quick_processing")
            
            assert result.status == WorkflowStatus.FAILED
            assert result.steps_completed == 0
            assert result.steps_failed > 0
            assert result.error_message is not None
    
    @pytest.mark.asyncio
    async def test_execute_workflow_timeout(self, workflow_engine):
        """Test workflow execution with timeout."""
        # Mock agent that takes too long
        mock_agent = Mock()
        mock_agent.process = AsyncMock(side_effect=asyncio.TimeoutError())
        
        with patch.object(workflow_engine, '_get_agent_instance', return_value=mock_agent):
            # Execute quick processing workflow
            result = await workflow_engine.execute_workflow("quick_processing")
            
            assert result.status == WorkflowStatus.FAILED
            assert result.steps_completed == 0
            assert result.steps_failed > 0
            assert "timeout" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_workflow_unknown(self, workflow_engine):
        """Test executing unknown workflow."""
        with pytest.raises(ValueError, match="Unknown workflow"):
            await workflow_engine.execute_workflow("unknown_workflow")
    
    @pytest.mark.asyncio
    async def test_get_workflow_status(self, workflow_engine, mock_agent_result):
        """Test getting workflow status."""
        # Mock agent instances
        mock_agent = Mock()
        mock_agent.process = AsyncMock(return_value=mock_agent_result)
        
        with patch.object(workflow_engine, '_get_agent_instance', return_value=mock_agent):
            # Execute workflow
            result = await workflow_engine.execute_workflow("quick_processing")
            execution_id = result.execution_id
            
            # Get status
            status = await workflow_engine.get_workflow_status(execution_id)
            
            assert status is not None
            assert status.execution_id == execution_id
            assert status.status == WorkflowStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_cancel_workflow(self, workflow_engine):
        """Test cancelling a workflow."""
        # Create a mock execution
        execution_id = str(uuid.uuid4())
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_name="test_workflow",
            status=WorkflowStatus.RUNNING
        )
        workflow_engine.active_executions[execution_id] = execution
        
        # Cancel workflow
        result = await workflow_engine.cancel_workflow(execution_id)
        
        assert result is True
        assert execution.status == WorkflowStatus.CANCELLED
        assert execution.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_workflow(self, workflow_engine):
        """Test cancelling a non-existent workflow."""
        result = await workflow_engine.cancel_workflow("nonexistent_id")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_workflow_metrics(self, workflow_engine, mock_agent_result):
        """Test getting workflow metrics."""
        # Mock agent instances
        mock_agent = Mock()
        mock_agent.process = AsyncMock(return_value=mock_agent_result)
        
        with patch.object(workflow_engine, '_get_agent_instance', return_value=mock_agent):
            # Execute a few workflows
            await workflow_engine.execute_workflow("quick_processing")
            await workflow_engine.execute_workflow("quick_processing")
            
            # Get metrics
            metrics = await workflow_engine.get_workflow_metrics()
            
            assert "total_executions" in metrics
            assert "successful_executions" in metrics
            assert "failed_executions" in metrics
            assert "success_rate" in metrics
            assert "average_duration" in metrics
            assert "active_executions" in metrics
            assert "workflows_available" in metrics
            
            assert metrics["total_executions"] >= 2
            assert metrics["successful_executions"] >= 2
            assert metrics["success_rate"] > 0
    
    @pytest.mark.asyncio
    async def test_get_agent_health(self, workflow_engine):
        """Test getting agent health status."""
        # Mock agent health check
        mock_agent = Mock()
        mock_agent.health_check = AsyncMock(return_value={"status": "healthy", "message": "OK"})
        
        with patch.object(workflow_engine, '_get_agent_instance', return_value=mock_agent):
            health = await workflow_engine.get_agent_health()
            
            assert len(health) == 8
            assert "ingestor" in health
            assert "normalizer" in health
            assert "classifier" in health
            assert "clusterer" in health
            assert "prioritizer" in health
            assert "actioner" in health
            assert "digestor" in health
            assert "feedback_loop" in health
            
            for agent_name, health_status in health.items():
                assert "status" in health_status
                assert "message" in health_status
    
    @pytest.mark.asyncio
    async def test_shutdown(self, workflow_engine):
        """Test workflow engine shutdown."""
        # Create a mock execution
        execution_id = str(uuid.uuid4())
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_name="test_workflow",
            status=WorkflowStatus.RUNNING
        )
        workflow_engine.active_executions[execution_id] = execution
        
        # Shutdown
        await workflow_engine.shutdown()
        
        # Check that active executions are cancelled
        assert execution.status == WorkflowStatus.CANCELLED

class TestPipelineScheduler:
    """Test cases for PipelineScheduler class."""
    
    @pytest.fixture
    def mock_workflow_engine(self):
        """Create mock workflow engine for testing."""
        mock_engine = Mock()
        mock_engine.execute_workflow = AsyncMock()
        mock_engine.cancel_workflow = AsyncMock(return_value=True)
        return mock_engine
    
    @pytest.fixture
    def scheduler(self, mock_workflow_engine):
        """Create PipelineScheduler instance for testing."""
        return PipelineScheduler(mock_workflow_engine)
    
    def test_initialization(self, scheduler):
        """Test PipelineScheduler initialization."""
        assert scheduler.workflow_engine is not None
        assert scheduler.is_running is False
        assert len(scheduler.scheduled_jobs) == 0
        assert len(scheduler.active_executions) == 0
        assert len(scheduler.execution_history) == 0
    
    @pytest.mark.asyncio
    async def test_start_stop(self, scheduler):
        """Test starting and stopping the scheduler."""
        # Start scheduler
        await scheduler.start()
        assert scheduler.is_running is True
        assert scheduler.scheduler_task is not None
        
        # Stop scheduler
        await scheduler.stop()
        assert scheduler.is_running is False
    
    @pytest.mark.asyncio
    async def test_create_scheduled_job(self, scheduler):
        """Test creating a scheduled job."""
        job_id = await scheduler.create_scheduled_job(
            name="Test Job",
            description="Test job description",
            workflow_name="quick_processing",
            schedule_type=ScheduleType.CRON,
            schedule_value="0 9 * * *",  # Daily at 9 AM
            timezone="UTC",
            enabled=True
        )
        
        assert job_id is not None
        assert job_id in scheduler.scheduled_jobs
        
        job_config = scheduler.scheduled_jobs[job_id]
        assert job_config.name == "Test Job"
        assert job_config.description == "Test job description"
        assert job_config.workflow_name == "quick_processing"
        assert job_config.schedule_type == ScheduleType.CRON
        assert job_config.schedule_value == "0 9 * * *"
        assert job_config.enabled is True
    
    @pytest.mark.asyncio
    async def test_update_scheduled_job(self, scheduler):
        """Test updating a scheduled job."""
        # Create job
        job_id = await scheduler.create_scheduled_job(
            name="Test Job",
            description="Test job description",
            workflow_name="quick_processing",
            schedule_type=ScheduleType.CRON,
            schedule_value="0 9 * * *"
        )
        
        # Update job
        result = await scheduler.update_scheduled_job(
            job_id,
            name="Updated Job",
            enabled=False
        )
        
        assert result is True
        
        job_config = scheduler.scheduled_jobs[job_id]
        assert job_config.name == "Updated Job"
        assert job_config.enabled is False
    
    @pytest.mark.asyncio
    async def test_delete_scheduled_job(self, scheduler):
        """Test deleting a scheduled job."""
        # Create job
        job_id = await scheduler.create_scheduled_job(
            name="Test Job",
            description="Test job description",
            workflow_name="quick_processing",
            schedule_type=ScheduleType.CRON,
            schedule_value="0 9 * * *"
        )
        
        # Delete job
        result = await scheduler.delete_scheduled_job(job_id)
        
        assert result is True
        assert job_id not in scheduler.scheduled_jobs
    
    @pytest.mark.asyncio
    async def test_run_job_manually(self, scheduler):
        """Test running a job manually."""
        # Create job
        job_id = await scheduler.create_scheduled_job(
            name="Test Job",
            description="Test job description",
            workflow_name="quick_processing",
            schedule_type=ScheduleType.MANUAL,
            schedule_value=""
        )
        
        # Run job manually
        execution_id = await scheduler.run_job_manually(job_id)
        
        assert execution_id is not None
        assert execution_id in scheduler.active_executions
        
        execution = scheduler.active_executions[execution_id]
        assert execution.job_id == job_id
        assert execution.workflow_name == "quick_processing"
        assert execution.status == JobStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_cancel_job_execution(self, scheduler):
        """Test cancelling a job execution."""
        # Create job
        job_id = await scheduler.create_scheduled_job(
            name="Test Job",
            description="Test job description",
            workflow_name="quick_processing",
            schedule_type=ScheduleType.MANUAL,
            schedule_value=""
        )
        
        # Run job manually
        execution_id = await scheduler.run_job_manually(job_id)
        
        # Cancel execution
        result = await scheduler.cancel_job_execution(execution_id)
        
        assert result is True
        assert execution_id not in scheduler.active_executions
        assert execution_id in [exec.execution_id for exec in scheduler.execution_history]
    
    @pytest.mark.asyncio
    async def test_get_job_status(self, scheduler):
        """Test getting job status."""
        # Create job
        job_id = await scheduler.create_scheduled_job(
            name="Test Job",
            description="Test job description",
            workflow_name="quick_processing",
            schedule_type=ScheduleType.CRON,
            schedule_value="0 9 * * *"
        )
        
        # Get status
        status = await scheduler.get_job_status(job_id)
        
        assert status is not None
        assert status["job_id"] == job_id
        assert status["name"] == "Test Job"
        assert status["workflow_name"] == "quick_processing"
        assert status["schedule_type"] == ScheduleType.CRON.value
        assert status["enabled"] is True
        assert "active_executions" in status
        assert "recent_executions" in status
    
    @pytest.mark.asyncio
    async def test_get_scheduler_metrics(self, scheduler):
        """Test getting scheduler metrics."""
        # Create a job
        await scheduler.create_scheduled_job(
            name="Test Job",
            description="Test job description",
            workflow_name="quick_processing",
            schedule_type=ScheduleType.CRON,
            schedule_value="0 9 * * *"
        )
        
        # Get metrics
        metrics = await scheduler.get_scheduler_metrics()
        
        assert "total_jobs" in metrics
        assert "enabled_jobs" in metrics
        assert "active_executions" in metrics
        assert "total_executions" in metrics
        assert "successful_executions" in metrics
        assert "success_rate" in metrics
        assert "scheduler_running" in metrics
        
        assert metrics["total_jobs"] >= 1
        assert metrics["enabled_jobs"] >= 1
        assert metrics["scheduler_running"] is False  # Not started in test

class TestStateManager:
    """Test cases for StateManager class."""
    
    @pytest.fixture
    def state_manager(self):
        """Create StateManager instance for testing."""
        config = {
            "default_ttl": 3600,
            "cleanup_interval": 300,
            "max_state_size": 1024 * 1024
        }
        return StateManager(config)
    
    @pytest.mark.asyncio
    async def test_set_get_state(self, state_manager):
        """Test setting and getting state."""
        # Set state
        result = await state_manager.set_state(
            key="test_key",
            value={"test": "data"},
            state_type=StateType.WORKFLOW,
            ttl=60
        )
        
        assert result is True
        
        # Get state
        value = await state_manager.get_state("test_key", StateType.WORKFLOW)
        
        assert value is not None
        assert value["test"] == "data"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_state(self, state_manager):
        """Test getting non-existent state."""
        value = await state_manager.get_state("nonexistent_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_delete_state(self, state_manager):
        """Test deleting state."""
        # Set state
        await state_manager.set_state(
            key="test_key",
            value={"test": "data"},
            state_type=StateType.WORKFLOW
        )
        
        # Delete state
        result = await state_manager.delete_state("test_key")
        
        assert result is True
        
        # Try to get deleted state
        value = await state_manager.get_state("test_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_list_states(self, state_manager):
        """Test listing states."""
        # Set multiple states
        await state_manager.set_state("key1", "value1", StateType.WORKFLOW)
        await state_manager.set_state("key2", "value2", StateType.AGENT)
        await state_manager.set_state("key3", "value3", StateType.WORKFLOW)
        
        # List all states
        all_keys = await state_manager.list_states()
        assert len(all_keys) == 3
        assert "key1" in all_keys
        assert "key2" in all_keys
        assert "key3" in all_keys
        
        # List by type
        workflow_keys = await state_manager.list_states(state_type=StateType.WORKFLOW)
        assert len(workflow_keys) == 2
        assert "key1" in workflow_keys
        assert "key3" in workflow_keys
        
        agent_keys = await state_manager.list_states(state_type=StateType.AGENT)
        assert len(agent_keys) == 1
        assert "key2" in agent_keys
    
    @pytest.mark.asyncio
    async def test_set_get_pipeline_state(self, state_manager):
        """Test setting and getting pipeline state."""
        # Set pipeline state
        result = await state_manager.set_pipeline_state(
            execution_id="test_execution",
            workflow_name="test_workflow",
            current_step="ingestor"
        )
        
        assert result is True
        
        # Get pipeline state
        state = await state_manager.get_pipeline_state("test_execution")
        
        assert state is not None
        assert state.execution_id == "test_execution"
        assert state.workflow_name == "test_workflow"
        assert state.current_step == "ingestor"
        assert state.status == "running"
    
    @pytest.mark.asyncio
    async def test_update_pipeline_state(self, state_manager):
        """Test updating pipeline state."""
        # Set initial state
        await state_manager.set_pipeline_state(
            execution_id="test_execution",
            workflow_name="test_workflow",
            current_step="ingestor"
        )
        
        # Update state
        result = await state_manager.update_pipeline_state(
            "test_execution",
            current_step="normalizer",
            completed_steps=["ingestor"],
            status="completed"
        )
        
        assert result is True
        
        # Get updated state
        state = await state_manager.get_pipeline_state("test_execution")
        assert state.current_step == "normalizer"
        assert "ingestor" in state.completed_steps
        assert state.status == "completed"
    
    @pytest.mark.asyncio
    async def test_set_get_agent_state(self, state_manager):
        """Test setting and getting agent state."""
        # Set agent state
        result = await state_manager.set_agent_state(
            agent_name="ingestor",
            execution_id="test_execution",
            status="running"
        )
        
        assert result is True
        
        # Get agent state
        state = await state_manager.get_agent_state("ingestor", "test_execution")
        
        assert state is not None
        assert state.agent_name == "ingestor"
        assert state.execution_id == "test_execution"
        assert state.status == "running"
    
    @pytest.mark.asyncio
    async def test_acquire_release_lock(self, state_manager):
        """Test acquiring and releasing locks."""
        # Acquire lock
        result = await state_manager.acquire_lock("test_lock", timeout=5)
        assert result is True
        
        # Try to acquire same lock (should fail)
        result = await state_manager.acquire_lock("test_lock", timeout=1)
        assert result is False
        
        # Release lock
        result = await state_manager.release_lock("test_lock")
        assert result is True
        
        # Try to acquire again (should succeed)
        result = await state_manager.acquire_lock("test_lock", timeout=5)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_state_metrics(self, state_manager):
        """Test getting state metrics."""
        # Set some states
        await state_manager.set_state("key1", "value1", StateType.WORKFLOW)
        await state_manager.set_state("key2", "value2", StateType.AGENT)
        
        # Get metrics
        metrics = await state_manager.get_state_metrics()
        
        assert "total_states" in metrics
        assert "active_states" in metrics
        assert "expired_states" in metrics
        assert "total_size_bytes" in metrics
        assert "total_size_mb" in metrics
        assert "type_counts" in metrics
        assert "pipeline_states" in metrics
        assert "agent_states" in metrics
        assert "active_locks" in metrics
        
        assert metrics["total_states"] >= 2
        assert metrics["active_states"] >= 2
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_states(self, state_manager):
        """Test cleaning up expired states."""
        # Set state with short TTL
        await state_manager.set_state(
            key="expired_key",
            value="expired_value",
            state_type=StateType.WORKFLOW,
            ttl=1  # 1 second
        )
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Clean up
        cleaned_count = await state_manager.cleanup_expired_states()
        
        assert cleaned_count >= 1
        
        # Check that state is gone
        value = await state_manager.get_state("expired_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_export_import_state(self, state_manager):
        """Test exporting and importing state."""
        # Set some states
        await state_manager.set_state("key1", "value1", StateType.WORKFLOW)
        await state_manager.set_state("key2", "value2", StateType.AGENT)
        
        # Export state
        export_data = await state_manager.export_state()
        
        assert "exported_at" in export_data
        assert "states" in export_data
        assert "pipeline_states" in export_data
        assert "agent_states" in export_data
        assert len(export_data["states"]) >= 2
        
        # Clear state
        state_manager.state_store.clear()
        
        # Import state
        result = await state_manager.import_state(export_data)
        
        assert result is True
        
        # Check that states are restored
        value1 = await state_manager.get_state("key1")
        value2 = await state_manager.get_state("key2")
        
        assert value1 == "value1"
        assert value2 == "value2"
    
    @pytest.mark.asyncio
    async def test_shutdown(self, state_manager):
        """Test state manager shutdown."""
        # Set some states
        await state_manager.set_state("key1", "value1", StateType.WORKFLOW)
        
        # Acquire a lock
        await state_manager.acquire_lock("test_lock")
        
        # Shutdown
        await state_manager.shutdown()
        
        # Check that lock is released
        result = await state_manager.acquire_lock("test_lock", timeout=1)
        assert result is True

